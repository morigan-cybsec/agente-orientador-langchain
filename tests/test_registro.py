from langchain_core.documents import Document
from langchain_core.embeddings import DeterministicFakeEmbedding
from langgraph.checkpoint.memory import InMemorySaver

from orientador.cli import perguntar
from orientador.grafo import construir_grafo
from orientador.rag import IndiceGuias, carregar_conversas
from orientador.registro import Registro
from orientador.schemas import Classificacao as C


def test_sessao_gera_md_normal_e_debug(tmp_path, modelo_com, base, indice):
    m = modelo_com({"Compare": C(intencao="comparar", estudantes=["Ana", "Bianca"])}, respostas=("Ana e Bianca diferem.",))
    app = construir_grafo(m, base, indice, InMemorySaver())
    reg = Registro(tmp_path, "modo teste")
    perguntar(app, "Compare a Ana com a Bianca", "t", mostrar_passos=False, registro=reg)

    normal = reg.normal.read_text(encoding="utf-8")
    assert "**Pergunta:** Compare a Ana com a Bianca" in normal
    assert "· comparei as fichas: Ana, Bianca" in normal
    assert "Ana e Bianca diferem." in normal
    assert "Prompt enviado" not in normal

    debug = reg.debug.read_text(encoding="utf-8")
    assert "### Nó `comparar_fichas` (saída)" in debug
    assert "#### LLM chamado no nó `responder`" in debug
    assert "Dados disponíveis:" in debug


def test_sem_turnos_nao_cria_arquivos(tmp_path):
    reg = Registro(tmp_path, "x")
    assert not reg.normal.exists() and not reg.debug.exists()


def test_rag_de_conversas_ignora_debug(tmp_path):
    (tmp_path / "2026-11-20_100000.md").write_text("Comparamos Ana e Bianca", encoding="utf-8")
    (tmp_path / "2026-11-20_100000_debug.md").write_text("prompt enorme", encoding="utf-8")
    docs = carregar_conversas(tmp_path)
    assert [d.metadata["conversa"] for d in docs] == ["2026-11-20_100000"]


def test_intencao_historico_consulta_conversas(modelo_com, base, indice):
    conversas = IndiceGuias(
        DeterministicFakeEmbedding(size=16),
        [Document(page_content="Comparamos Ana e Bianca; Bianca lidera em exatas.", metadata={"conversa": "2026-11-20_100000"})],
    )
    m = modelo_com({"já vimos": C(intencao="historico", estudantes=["Ana"])})
    app = construir_grafo(m, base, indice, InMemorySaver(), indice_historico=conversas)
    e = app.invoke({"messages": [("user", "o que já vimos sobre a Ana?")]}, {"configurable": {"thread_id": "h"}})
    assert e["historico_trechos"] == ["[2026-11-20_100000] Comparamos Ana e Bianca; Bianca lidera em exatas."]


def test_historico_vazio_nao_quebra(modelo_com, base, indice):
    vazio = IndiceGuias(DeterministicFakeEmbedding(size=16), [])
    m = modelo_com({"já vimos": C(intencao="historico")})
    app = construir_grafo(m, base, indice, InMemorySaver(), indice_historico=vazio)
    e = app.invoke({"messages": [("user", "o que já vimos?")]}, {"configurable": {"thread_id": "h"}})
    assert e["historico_trechos"] == []
