import json

from fases.fase1_curso.agente import criar_ferramentas
from orientador.modelo_falso import ModeloFalso


def _tools():
    return {t.name: t for t in criar_ferramentas(ModeloFalso.criar())}


def test_fase1_busca_exata_como_no_curso():
    t = _tools()
    assert json.loads(t["dados_de_universidade"].invoke({"nome": "UNICAMP"}))["sigla"] == "UNICAMP"
    assert json.loads(t["dados_de_universidade"].invoke({"nome": "uni camp"})) == {}  # o problema do curso
    assert json.loads(t["dados_de_estudante"].invoke({"nome": "Ana"}))["nome"] == "Ana"
    assert json.loads(t["dados_de_estudante"].invoke({"nome": "Bianka"})) == {}


def test_fase1_tem_so_as_4_ferramentas_do_curso():
    assert set(_tools()) == {"dados_de_estudante", "dados_de_universidade", "todas_universidades", "perfil_academico"}
