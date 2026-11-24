"""Uso:
    python -m orientador
    python -m orientador --modo agente
    python -m orientador -p "pergunta"
    python -m orientador --silencioso       # esconde os passos, mostra só a resposta
    python -m orientador --debug            # mostra tudo: prompts, chamadas e respostas brutas
    python -m orientador --diagrama
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid

from langgraph.checkpoint.memory import InMemorySaver


def _construir(modo: str, fase: str = "2"):
    if fase == "1":
        from fases.fase1_curso.agente import construir_agente as construir_fase1

        return construir_fase1(checkpointer=InMemorySaver())
    if modo == "agente":
        from orientador.agente import construir_agente

        return construir_agente(checkpointer=InMemorySaver())
    from orientador.grafo import construir_grafo

    return construir_grafo(checkpointer=InMemorySaver())


CINZA, CIANO, VERMELHO, RESET = "\033[90m", "\033[36m", "\033[31m", "\033[0m"


def _cores_ativas() -> bool:
    if os.getenv("NO_COLOR") or not sys.stdout.isatty():
        return False
    if os.name == "nt":
        os.system("")  # liga as sequências ANSI no console do Windows
    return True


def _pintar(texto: str, cor: str) -> str:
    return f"{cor}{texto}{RESET}" if _COR else texto


_COR = False


def _lista(itens, chave):
    return ", ".join(str(i[chave]) for i in itens) or "-"


def _descrever(no: str, saida: dict) -> list[str]:
    """Traduz a atualização de estado de um nó (stream_mode="updates") em linhas legíveis."""
    saida = saida or {}
    if no == "classificar":
        citados = saida["citados"]["estudantes"] + saida["citados"]["universidades"]
        linha = f"entendi a intenção: {saida['intencao']}" + (f" ({', '.join(citados)})" if citados else "")
        linha += " · formato: lista" if saida.get("formato") == "lista" else ""
        return [linha + (" · corrigindo a pergunta anterior" if saida.get("correcao") else "")]
    if no == "buscar_dados":
        linhas = []
        if saida.get("estudantes"):
            linhas.append(f"busquei estudantes: {_lista(saida['estudantes'], 'nome')}")
        if saida.get("universidades"):
            linhas.append(f"busquei universidades: {_lista(saida['universidades'], 'sigla')}")
        trocas = {k: v for k, v in (saida.get("nomes_resolvidos") or {}).items() if k != v}
        if trocas:
            linhas.append("interpretei: " + ", ".join(f"'{k}' → {v}" for k, v in trocas.items()))
        if saida.get("nao_encontrados"):
            linhas.append(f"não encontrei: {', '.join(saida['nao_encontrados'])}")
        return linhas
    if no == "esclarecer":
        return ["falta informação: vou pedir esclarecimento"]
    if no == "comparar_fichas":
        comp = saida.get("comparacao") or {}
        if not comp:
            return ["comparação: preciso de pelo menos 2 estudantes ou 2 universidades"]
        linhas = [f"comparei as fichas: {', '.join(comp['comparados'])}"]
        if comp.get("media_geral"):
            linhas.append("média geral: " + ", ".join(f"{k} {v}" for k, v in comp["media_geral"].items()))
        for n in sorted(comp["numericos"], key=lambda n: n["diferenca"], reverse=True)[:4]:
            valores = " × ".join(f"{k} {v}" for k, v in n["valores"].items())
            linhas.append(f"  {n['campo']}: {valores} (lidera: {n['lider']})")
        for c in comp["conjuntos"]:
            linhas.append(f"  {c['campo']} em comum: {', '.join(c['em_comum']) or 'nenhum'}")
        return linhas
    if no == "gerar_perfil":
        if not saida.get("perfil"):
            return ["perfil já está na memória da conversa"]
        return [f"perfil gerado: pontos fortes: {'; '.join(saida['perfil']['pontos_fortes'])}"]
    if no == "ranquear":
        linhas = ["ranking calculado:"]
        varios = len({r.get("estudante") for r in saida["ranking"]}) > 1
        for r in saida["ranking"]:
            c = r["componentes"]
            quem = f"{r['estudante']:<7}" if varios else ""
            linhas.append(
                f"  {quem}{r['universidade']:<9} {r['score']:5.1f}  (desempenho {c['desempenho']}, "
                f"área {c['afinidade']}, idioma {c['idioma']}, preferência {c['preferencia']})"
            )
        return linhas
    if no == "consultar_guias":
        fontes = sorted({t.split("]")[0][1:] for t in saida.get("trechos", [])})
        return [f"consultei os guias de admissão: {', '.join(fontes) or 'nenhum trecho'}"]
    if no == "consultar_historico":
        fontes = sorted({t.split("]")[0][1:] for t in saida.get("historico_trechos", [])})
        return [f"consultei o histórico: {', '.join(fontes) or 'nenhuma conversa anterior'}"]
    if no == "responder":
        return ["redigindo a resposta"]
    # modo agente: nós "model" (decide) e "tools" (executa) do create_agent
    linhas = []
    for msg in saida.get("messages", []):
        for chamada in getattr(msg, "tool_calls", None) or []:
            args = ", ".join(f"{k}={v!r}" for k, v in chamada["args"].items())
            linhas.append(f"o modelo decidiu chamar {chamada['name']}({args})")
        if msg.type == "tool":
            linhas += ["  " + l for l in _descrever_ferramenta(msg.name, msg.content)]
        elif msg.type == "ai" and not getattr(msg, "tool_calls", None):
            linhas.append("redigindo a resposta")
    return linhas


def _descrever_ferramenta(nome: str, conteudo) -> list[str]:
    try:
        dados = json.loads(conteudo)
    except (TypeError, ValueError):
        return [f"{nome}: {str(conteudo)[:150]}"]
    if isinstance(dados, dict) and "erro" in dados:
        return [f"{nome}: {dados['erro']}"]
    if nome.startswith("comparar_"):
        return _descrever("comparar_fichas", {"comparacao": dados})
    if nome == "ranquear_universidades":
        return _descrever("ranquear", {"ranking": dados})
    if nome == "dados_estudante":
        return [f"ficha encontrada: {dados.get('nome')}"]
    if nome == "dados_universidade":
        return [f"ficha encontrada: {dados.get('sigla')}"]
    if nome == "consultar_guias_admissao":
        return [f"guias consultados: {', '.join(sorted({t['universidade'] for t in dados})) or 'nenhum'}"]
    if nome == "consultar_historico":
        return [f"histórico consultado: {', '.join(sorted({t['conversa'] for t in dados})) or 'nenhuma conversa'}"]
    if nome == "perfil_academico":
        return [f"perfil gerado: pontos fortes: {'; '.join(dados.get('pontos_fortes', []))}"]
    return [f"{nome}: {str(conteudo)[:150]}"]


def perguntar(app, pergunta: str, thread_id: str, mostrar_passos: bool = True, registro=None) -> str:
    config = {"configurable": {"thread_id": thread_id}}
    if registro:
        config["callbacks"] = [registro.handler]
        registro.inicio_turno(pergunta)
    entrada = {"messages": [("user", pergunta)]}
    linhas_turno = []
    for passo in app.stream(entrada, config, stream_mode="updates"):
        for no, saida in passo.items():
            linhas = _descrever(no, saida)
            linhas_turno += linhas
            if registro:
                registro.no_executado(no, saida)
            if mostrar_passos:
                for linha in linhas:
                    print(_pintar(f"  · {linha}", CINZA))
    resposta = app.get_state(config).values["messages"][-1].text
    if registro:
        registro.fim_turno(pergunta, linhas_turno, resposta)
    return resposta


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(prog="orientador", description="Estudante x universidade com LangChain e LangGraph")
    parser.add_argument("--modo", choices=["agente", "grafo"], default="agente",
                        help="agente (padrão) ou grafo (orquestrador em Python, base do próximo repo)")
    parser.add_argument("--fase", choices=["1", "2"], default="2",
                        help="1 = agente como no curso; 2 = agente com ferramentas e regras (padrão)")
    parser.add_argument("-p", "--pergunta", help="faz uma pergunta e sai")
    parser.add_argument("--silencioso", action="store_true", help="esconde os passos intermediários")
    parser.add_argument("--debug", action="store_true", help="mostra prompts, chamadas e respostas brutas (set_debug)")
    parser.add_argument("--sem-registro", action="store_true", help="não grava a conversa em conversas/")
    parser.add_argument("--diagrama", action="store_true", help="imprime o grafo em Mermaid e sai")
    args = parser.parse_args(argv)

    if args.diagrama:
        from orientador.modelo_falso import ModeloFalso

        if args.modo == "grafo":
            from orientador.grafo import construir_grafo

            app = construir_grafo(modelo=ModeloFalso.criar())
        else:
            from orientador.agente import construir_agente

            app = construir_agente(modelo=ModeloFalso.criar())
        print(app.get_graph().draw_mermaid())
        return 0

    from orientador.config import descricao, verificar_chave

    if erro := verificar_chave():
        print(erro, file=sys.stderr)
        return 1

    global _COR
    _COR = _cores_ativas()
    if args.debug:
        from langchain_core.globals import set_debug

        set_debug(True)

    app = _construir(args.modo, args.fase)
    thread_id = str(uuid.uuid4())
    registro = None
    if not args.sem_registro:
        from orientador.config import DIR_CONVERSAS
        from orientador.registro import Registro

        registro = Registro(DIR_CONVERSAS, f"fase {args.fase} · modo {args.modo} · {descricao()}")

    if args.pergunta:
        print(perguntar(app, args.pergunta, thread_id, not args.silencioso, registro))
        return 0

    print(_pintar(f"fase {args.fase} · modo {args.modo} · {descricao()} · 'sair' para encerrar", CIANO))
    if registro:
        print(_pintar(f"registrando em {registro.normal.relative_to(registro.normal.parent.parent)} (+ _debug.md)", CINZA))
    while True:
        try:
            pergunta = input(_pintar("\n> ", CIANO)).strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not pergunta or pergunta.lower() in {"sair", "exit", "quit"}:
            break
        try:
            print()
            resposta = perguntar(app, pergunta, thread_id, not args.silencioso, registro)
            print("\n" + resposta)
        except Exception as erro:  # erro da API do provedor (chave, crédito, limite)
            print(_pintar(f"\n[erro] {type(erro).__name__}: {str(erro).splitlines()[0][:300]}", VERMELHO))
    return 0
