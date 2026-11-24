import json

from langchain_core.messages import AIMessage, ToolMessage

from orientador.agente import construir_agente
from orientador.ferramentas import criar_ferramentas
from orientador.modelo_falso import ModeloFalso
from tests.conftest import perfil_fake


def _tools(base, indice):
    m = ModeloFalso.criar(roteiro={"PerfilAcademico": perfil_fake})
    return {t.name: t for t in criar_ferramentas(base, m, lambda: indice)}


def test_ferramenta_dados_universidade_tolerante(base, indice):
    out = json.loads(_tools(base, indice)["dados_universidade"].invoke({"nome": "uni camp"}))
    assert out["sigla"] == "UNICAMP"


def test_ferramenta_nao_encontrado_lista_opcoes(base, indice):
    out = json.loads(_tools(base, indice)["dados_estudante"].invoke({"nome": "Zé"}))
    assert "erro" in out and "Ana" in out["opcoes"]


def test_ferramenta_ranking_compara_lista(base, indice):
    out = json.loads(
        _tools(base, indice)["ranquear_universidades"].invoke(
            {"estudante": "ana", "universidades": ["USP", "uni camp"]}
        )
    )
    assert {r["universidade"] for r in out} == {"USP", "UNICAMP"}


def test_ferramenta_perfil_busca_dados_sozinha(base, indice):
    out = json.loads(_tools(base, indice)["perfil_academico"].invoke({"estudante": "Ana"}))
    assert out["resumo"] == "perfil gerado pelo modelo falso"


def test_ferramenta_guias_filtra(base, indice):
    out = json.loads(
        _tools(base, indice)["consultar_guias_admissao"].invoke({"pergunta": "ingresso", "universidade": "MIT"})
    )
    assert out and all(t["universidade"] == "MIT" for t in out)


def test_loop_do_agente_chama_ferramenta_e_responde(base, indice):
    roteiro = [
        AIMessage("", tool_calls=[{"name": "ranquear_universidades", "args": {"estudante": "Marcos"}, "id": "c1"}]),
        AIMessage("A UBC lidera o ranking do Marcos."),
    ]
    m = ModeloFalso(messages=iter(roteiro))
    agente = construir_agente(modelo=m, base=base, indice=indice)
    estado = agente.invoke({"messages": [("user", "qual faculdade pro Marcos?")]})

    tool_msgs = [x for x in estado["messages"] if isinstance(x, ToolMessage)]
    assert len(tool_msgs) == 1
    assert json.loads(tool_msgs[0].content)[0]["universidade"] == "UBC"
    assert estado["messages"][-1].content == "A UBC lidera o ranking do Marcos."


def test_trace_do_agente_descreve_resultado_das_ferramentas(base, indice):
    from orientador.cli import _descrever

    roteiro = [
        AIMessage("", tool_calls=[{"name": "comparar_estudantes", "args": {"nomes": ["Ana", "Bianca"]}, "id": "c1"}]),
        AIMessage("Bianca vai melhor em exatas."),
    ]
    agente = construir_agente(modelo=ModeloFalso(messages=iter(roteiro)), base=base, indice=indice)
    linhas = []
    for passo in agente.stream({"messages": [("user", "compare")]}, stream_mode="updates"):
        for no, saida in passo.items():
            linhas += _descrever(no, saida)
    assert linhas[0] == "o modelo decidiu chamar comparar_estudantes(nomes=['Ana', 'Bianca'])"
    assert "  comparei as fichas: Ana, Bianca" in linhas
    assert linhas[-1] == "redigindo a resposta"


def test_ferramenta_historico(base, indice):
    from langchain_core.documents import Document
    from langchain_core.embeddings import DeterministicFakeEmbedding

    from orientador.rag import IndiceGuias

    hist = IndiceGuias(DeterministicFakeEmbedding(size=8), [Document(page_content="Comparamos Ana e Bianca", metadata={"conversa": "2026-11-20_100000"})])
    m = ModeloFalso.criar(roteiro={"PerfilAcademico": perfil_fake})
    tools = {t.name: t for t in criar_ferramentas(base, m, lambda: indice, lambda: hist)}
    out = json.loads(tools["consultar_historico"].invoke({"pergunta": "Ana"}))
    assert out == [{"conversa": "2026-11-20_100000", "trecho": "Comparamos Ana e Bianca"}]
