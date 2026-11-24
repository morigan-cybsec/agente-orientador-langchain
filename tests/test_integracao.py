"""Testes com o modelo real: pytest -m integracao (requer chave no .env).

Conferem o que é verificável numa resposta de agente: quais ferramentas ele
decidiu chamar e o que elas devolveram. O texto final não é testado aqui
(varia a cada execução; isso é papel do scripts/verificar_variacao.py).
"""

import json

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from orientador.config import verificar_chave

pytestmark = [
    pytest.mark.integracao,
    pytest.mark.skipif(verificar_chave() is not None, reason="sem chave de API configurada"),
]


@pytest.fixture(scope="module")
def agente():
    from orientador.agente import construir_agente

    return construir_agente(checkpointer=InMemorySaver())


def _rodar(app, pergunta, thread):
    return app.invoke({"messages": [("user", pergunta)]}, {"configurable": {"thread_id": thread}})


def _chamadas(estado):
    return [c for m in estado["messages"] for c in (getattr(m, "tool_calls", None) or [])]


def _resultados(estado, ferramenta):
    return [json.loads(m.content) for m in estado["messages"] if m.type == "tool" and m.name == ferramenta]


@pytest.mark.parametrize("pergunta", ["Quais os dados da USP?", "Quais os dados da uNi CAmP?", "Quais os dados da uNicomP?"])
def test_dados_universidade(agente, pergunta):
    e = _rodar(agente, pergunta, f"dados-{pergunta}")
    fichas = _resultados(e, "dados_universidade")
    assert fichas and "sigla" in fichas[-1]
    assert e["messages"][-1].text.strip()


def test_comparar_estudantes_usa_ferramenta(agente):
    e = _rodar(agente, "Compare a Ana com a Bianca", "comp")
    comparacoes = _resultados(e, "comparar_estudantes")
    assert comparacoes and comparacoes[-1]["comparados"] == ["Ana", "Bianca"]


def test_recomendar_usa_ranking(agente):
    e = _rodar(agente, "Qual faculdade combina mais com o Gabriel?", "rank")
    rankings = _resultados(e, "ranquear_universidades")
    assert rankings and {r["universidade"] for r in rankings[-1][:2]} == {"USP", "ITA"}


def test_admissao_usa_guias(agente):
    e = _rodar(agente, "Como funciona o ingresso na UBA?", "rag")
    trechos = _resultados(e, "consultar_guias_admissao")
    assert trechos and any(t["universidade"] == "UBA" for t in trechos[-1])


def test_memoria_entre_perguntas(agente):
    _rodar(agente, "Quais os dados do Marcos?", "mem")
    e = _rodar(agente, "E quais faculdades combinam mais com ele?", "mem")
    chamadas = [c for c in _chamadas(e) if c["name"] == "ranquear_universidades"]
    assert chamadas and "marcos" in chamadas[-1]["args"]["estudante"].lower()


@pytest.mark.xfail(
    strict=False,
    reason="problema conhecido: pedido de lista às vezes vem em texto corrido (1/10 no Haiku, "
    "6/10 no Gemini flash-lite; docs/verificacoes/fase2_*). Ver README, Problemas conhecidos.",
)
def test_pedido_de_lista_vem_em_lista(agente):
    e = _rodar(agente, "Pode listar as diferenças entre a Bianca e o Gabriel?", "lista")
    linhas = e["messages"][-1].text.splitlines()
    assert any(l.strip().startswith(("-", "*", "•")) for l in linhas)
