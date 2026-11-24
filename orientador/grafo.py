"""StateGraph: classificar -> buscar_dados -> (esclarecer | comparar_fichas | gerar_perfil | ranquear | consultar_guias | consultar_historico | responder) -> END."""

from __future__ import annotations

import json
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from orientador import comparacao, compatibilidade
from orientador.cadeias import cadeia_classificacao, cadeia_perfil, cadeia_resposta
from orientador.dados import Base, carregar_base

INTENCOES_COM_ESTUDANTE = {"perfil", "recomendar"}


class Estado(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    # mantidos pelo checkpointer entre turnos
    estudante_atual: dict | None
    perfil: dict | None
    intencao: str
    formato: str
    correcao: bool
    citados: dict[str, list[str]]
    estudantes: list[dict]
    universidades: list[dict]
    nao_encontrados: list[str]
    nomes_resolvidos: dict[str, str]
    ranking: list[dict]
    comparacao: dict
    trechos: list[str]
    historico_trechos: list[str]


class _IndicePreguicoso:
    """Só gera embeddings na primeira vez que o índice é usado."""

    def __init__(self, indice, fabrica: str):
        self._indice = indice
        self._fabrica = fabrica

    def get(self):
        if self._indice is None:
            from orientador import rag

            self._indice = getattr(rag, self._fabrica)()
        return self._indice


def _ultima_pergunta(estado: Estado) -> str:
    for msg in reversed(estado.get("messages", [])):
        if isinstance(msg, HumanMessage):
            return msg.content
    return ""


def construir_grafo(modelo=None, base: Base | None = None, indice=None, checkpointer=None, indice_historico=None):
    if modelo is None:
        from orientador.config import carregar_modelo

        modelo = carregar_modelo()
    base = base or carregar_base()
    indice_rag = _IndicePreguicoso(indice, "construir_indice")
    indice_conversas = _IndicePreguicoso(indice_historico, "construir_indice_historico")

    classificador = cadeia_classificacao(modelo)
    gerador_perfil = cadeia_perfil(modelo)
    redator = cadeia_resposta(modelo)

    # nós
    def classificar(estado: Estado) -> dict:
        cls = classificador.invoke(
            {"pergunta": _ultima_pergunta(estado), "historico": estado["messages"][:-1][-6:]}
        )
        intencao = cls.intencao
        citados = {"estudantes": cls.estudantes, "universidades": cls.universidades}
        if cls.corrige_anterior and estado.get("citados"):
            # correção: mantém intenção e nomes da pergunta anterior, menos os não encontrados
            descartar = set(estado.get("nao_encontrados") or [])
            for tipo in citados:
                anteriores = [n for n in estado["citados"][tipo] if n not in descartar]
                citados[tipo] = list(dict.fromkeys(anteriores + citados[tipo]))
            intencao = estado["intencao"]
        return {
            "intencao": intencao,
            "formato": cls.formato,
            "correcao": bool(cls.corrige_anterior and estado.get("citados")),
            "citados": citados,
            "ranking": [],
            "comparacao": {},
            "trechos": [],
            "historico_trechos": [],
        }

    def buscar_dados(estado: Estado) -> dict:
        estudantes, universidades, nao_encontrados, resolvidos = [], [], [], {}
        for nome in estado["citados"]["estudantes"]:
            e = base.estudante(nome)
            if e and e.para_dict() not in estudantes:
                estudantes.append(e.para_dict())
                resolvidos[nome] = e.nome
            elif not e:
                nao_encontrados.append(nome)
        for nome in estado["citados"]["universidades"]:
            u = base.universidade(nome)
            if u and u.para_dict() not in universidades:
                universidades.append(u.para_dict())
                resolvidos[nome] = u.sigla
            elif not u:
                nao_encontrados.append(nome)

        atualizacao: dict = {
            "estudantes": estudantes,
            "universidades": universidades,
            "nao_encontrados": nao_encontrados,
            "nomes_resolvidos": resolvidos,
        }
        if estudantes:
            novo = estudantes[0]
            anterior = estado.get("estudante_atual")
            atualizacao["estudante_atual"] = novo
            if not anterior or anterior["usuario"] != novo["usuario"]:
                atualizacao["perfil"] = None
        return atualizacao

    def rota(estado: Estado) -> Literal[
        "esclarecer", "comparar_fichas", "gerar_perfil", "ranquear", "consultar_guias",
        "consultar_historico", "responder",
    ]:
        intencao = estado["intencao"]
        if intencao in INTENCOES_COM_ESTUDANTE and not estado.get("estudante_atual"):
            return "esclarecer"
        if intencao == "comparar" and len(estado["estudantes"]) < 2 and len(estado["universidades"]) < 2:
            return "esclarecer"
        if intencao in ("dados", "comparar") and estado["nao_encontrados"] and not (
            estado["estudantes"] or estado["universidades"]
        ):
            return "esclarecer"
        return {
            "comparar": "comparar_fichas",
            "perfil": "gerar_perfil",
            "recomendar": "ranquear",
            "admissao": "consultar_guias",
            "historico": "consultar_historico",
        }.get(intencao, "responder")

    def esclarecer(estado: Estado) -> dict:
        partes = []
        if estado.get("nao_encontrados"):
            partes.append(f"Não encontrei: {', '.join(estado['nao_encontrados'])}.")
        if estado["intencao"] == "comparar":
            partes.append("Para comparar, preciso de pelo menos 2 estudantes ou 2 universidades.")
        elif not estado.get("nao_encontrados"):
            partes.append("Para isso preciso saber de qual estudante estamos falando.")
        partes.append("Estudantes cadastrados: " + ", ".join(e.nome for e in base.estudantes) + ".")
        return {"messages": [AIMessage(" ".join(partes))]}

    def comparar_fichas(estado: Estado) -> dict:
        if len(estado["estudantes"]) >= 2:
            fichas = [base.estudante(e["usuario"]) for e in estado["estudantes"]]
            return {"comparacao": comparacao.comparar_estudantes(fichas)}
        if len(estado["universidades"]) >= 2:
            fichas = [base.universidade(u["sigla"]) for u in estado["universidades"]]
            return {"comparacao": comparacao.comparar_universidades(fichas)}
        return {"comparacao": {}}

    def gerar_perfil(estado: Estado) -> dict:
        if estado.get("perfil"):
            return {}
        dados = json.dumps(estado["estudante_atual"], ensure_ascii=False)
        perfil = gerador_perfil.invoke({"dados_estudante": dados})
        return {"perfil": perfil.model_dump()}

    def ranquear(estado: Estado) -> dict:
        alvos = estado["estudantes"] or [estado["estudante_atual"]]
        if estado["universidades"]:
            candidatas = [base.universidade(u["sigla"]) for u in estado["universidades"]]
            top = None
        else:
            candidatas, top = base.universidades, (5 if len(alvos) == 1 else 3)
        ranking = []
        for alvo in alvos:
            est = base.estudante(alvo["usuario"])
            for c in compatibilidade.ranquear(est, candidatas, top):
                ranking.append({"estudante": est.nome, **c.para_dict()})
        return {"ranking": ranking}

    def consultar_guias(estado: Estado) -> dict:
        if estado.get("ranking"):
            alvo = list(dict.fromkeys(r["universidade"] for r in estado["ranking"]))[:3]
        else:
            alvo = [u["sigla"] for u in estado.get("universidades", [])] or None
        docs = indice_rag.get().buscar(_ultima_pergunta(estado), universidades=alvo, k=4)
        return {"trechos": [f"[{d.metadata['universidade']}] {d.page_content}" for d in docs]}

    def consultar_historico(estado: Estado) -> dict:
        docs = indice_conversas.get().buscar(_ultima_pergunta(estado), k=4)
        return {"historico_trechos": [f"[{d.metadata['conversa']}] {d.page_content}" for d in docs]}

    def responder(estado: Estado) -> dict:
        contexto = {
            chave: estado.get(chave)
            for chave in (
                "estudantes", "estudante_atual", "universidades", "perfil",
                "ranking", "comparacao", "trechos", "historico_trechos",
                "nao_encontrados", "nomes_resolvidos",
            )
            if estado.get(chave)
        }
        if contexto.get("estudantes") or estado["intencao"] not in INTENCOES_COM_ESTUDANTE:
            contexto.pop("estudante_atual", None)
        if contexto.get("comparacao"):
            contexto.pop("estudantes", None)
            contexto.pop("universidades", None)
            contexto.pop("estudante_atual", None)
        if estado["intencao"] == "dados" and not estado.get("estudantes") and not estado.get("universidades"):
            contexto["estudantes_cadastrados"] = [e.nome for e in base.estudantes]
            contexto["universidades_cadastradas"] = [u.sigla for u in base.universidades]
        historico = estado["messages"][:-1][-6:]
        texto = redator.invoke(
            {
                "contexto": json.dumps(contexto, ensure_ascii=False, separators=(",", ":")),
                "historico": historico,
                "pergunta": _ultima_pergunta(estado),
                "formato": estado.get("formato", "texto"),
            }
        )
        return {"messages": [AIMessage(texto)]}

    # arestas; add_conditional_edges usa o retorno de `rota` como nome do próximo nó
    grafo = StateGraph(Estado)
    grafo.add_node("classificar", classificar)
    grafo.add_node("buscar_dados", buscar_dados)
    grafo.add_node("esclarecer", esclarecer)
    grafo.add_node("comparar_fichas", comparar_fichas)
    grafo.add_node("gerar_perfil", gerar_perfil)
    grafo.add_node("ranquear", ranquear)
    grafo.add_node("consultar_guias", consultar_guias)
    grafo.add_node("consultar_historico", consultar_historico)
    grafo.add_node("responder", responder)

    grafo.add_edge(START, "classificar")
    grafo.add_edge("classificar", "buscar_dados")
    grafo.add_conditional_edges("buscar_dados", rota)
    grafo.add_edge("esclarecer", END)
    grafo.add_edge("comparar_fichas", "responder")
    grafo.add_edge("gerar_perfil", "responder")
    grafo.add_edge("ranquear", "consultar_guias")
    grafo.add_edge("consultar_guias", "responder")
    grafo.add_edge("consultar_historico", "responder")
    grafo.add_edge("responder", END)

    return grafo.compile(checkpointer=checkpointer)
