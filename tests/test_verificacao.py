import importlib.util
from itertools import cycle
from pathlib import Path

from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver

from orientador.agente import construir_agente
from orientador.modelo_falso import ModeloFalso

_spec = importlib.util.spec_from_file_location("verificar_variacao", Path("scripts/verificar_variacao.py"))
vv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vv)


def _chamada(nome, args, id_):
    return AIMessage("", tool_calls=[{"name": nome, "args": args, "id": id_}])


def test_relatorio_do_agente_mostra_variacao_e_falhas(base, indice):
    roteiro = [
        _chamada("ranquear_universidades", {"estudante": "Gabriel"}, "1"),
        AIMessage("USP e ITA empatam no topo."),
        _chamada("ranquear_universidades", {"estudante": "gabriel"}, "2"),
        AIMessage("Pelo contexto, recomendo a USP."),
    ]
    agente = construir_agente(modelo=ModeloFalso(messages=cycle(roteiro)), base=base, indice=indice,
                              checkpointer=InMemorySaver())
    caso = next(c for c in vv.CASOS if c["pergunta"].startswith("Qual faculdade"))
    resultados = vv.verificar(agente, 2, "2", [caso])
    e1, e2 = resultados[0]["execucoes"]

    assert e1["ferramentas"] == e2["ferramentas"] == ["ranquear_universidades"]
    assert e1["assinatura"] == e2["assinatura"]  # mesma ferramenta, nome com caixa diferente: mesmo resultado
    assert all(ok for ok, _ in e1["checagens"])
    falhas = [n for ok, n in e2["checagens"] if not ok]
    assert "não menciona 'contexto'" in falhas and "reconhece o empate" in falhas

    texto = vv.relatorio(resultados, 2, "2", "modelo falso")
    assert "| Qual faculdade combina mais com o Gabriel? | 5/8 | 1 | 2 de 2 | 1 |" in texto


def test_fase1_nao_tem_ferramenta_de_comparacao():
    caso = next(c for c in vv.CASOS if c["pergunta"].startswith("Compare"))
    ok, nome = caso["checagens"][0]("qualquer", ["dados_de_estudante"], "1")
    assert not ok and "fase 1 não tem" in nome


def test_cota_esgotada_para_a_execucao():
    class AppSemCota:
        chamadas = 0

        def invoke(self, *a, **k):
            AppSemCota.chamadas += 1
            raise RuntimeError("429 RESOURCE_EXHAUSTED: You exceeded your current quota")

    resultados = vv.verificar(AppSemCota(), 10, "2")
    assert AppSemCota.chamadas == 1 and len(resultados) == 1
    texto = vv.relatorio(resultados, 10, "2", "x")
    assert "0/0 checagens OK · 1 execuções perdidas por erro de API" in texto
