import json

from orientador import comparacao
from orientador.cli import _descrever
from orientador.ferramentas import criar_ferramentas
from orientador.modelo_falso import ModeloFalso


def test_compara_estudantes_campo_a_campo(base):
    c = comparacao.comparar_estudantes([base.estudante("Ana"), base.estudante("Bianca")])
    mat = next(n for n in c["numericos"] if n["campo"] == "matematica")
    assert mat == {"campo": "matematica", "valores": {"Ana": 4.5, "Bianca": 9.5}, "lider": "Bianca", "diferenca": 5.0}
    unis = next(x for x in c["conjuntos"] if x["campo"] == "universidades_preferidas")
    assert unis["em_comum"] == ["UNICAMP"]
    assert unis["exclusivos"] == {"Ana": ["TUM"], "Bianca": ["MIT"]}
    assert unis["de_cada"] == {"Ana": ["TUM", "UNICAMP"], "Bianca": ["MIT", "UNICAMP"]}


def test_empate(base):
    c = comparacao.comparar_estudantes([base.estudante("Ana"), base.estudante("Bianca")])
    portugues_lingua = next(n for n in c["numericos"] if n["campo"] == "alemão")
    assert portugues_lingua["lider"] == "empate" and portugues_lingua["diferenca"] == 0


def test_compara_tres_estudantes(base):
    c = comparacao.comparar_estudantes([base.estudante(n) for n in ("Ana", "Bianca", "Marcos")])
    assert c["comparados"] == ["Ana", "Bianca", "Marcos"]
    assert len(c["media_geral"]) == 3


def test_compara_universidades(base):
    c = comparacao.comparar_universidades([base.universidade("USP"), base.universidade("MIT")])
    corte = next(n for n in c["numericos"] if n["campo"] == "nota_corte")
    assert corte["lider"] == "MIT"
    assert c["idioma_ensino"] == {"USP": "português", "MIT": "inglês"}


def test_ferramenta_comparar_precisa_de_dois(base, indice):
    tools = {t.name: t for t in criar_ferramentas(base, ModeloFalso.criar(), lambda: indice)}
    assert "erro" in json.loads(tools["comparar_estudantes"].invoke({"nomes": ["Ana", "Zé"]}))
    ok = json.loads(tools["comparar_estudantes"].invoke({"nomes": ["Ana", "Bianka"]}))
    assert ok["comparados"] == ["Ana", "Bianca"]


def test_ferramentas_tem_descricao_dos_argumentos(base, indice):
    for t in criar_ferramentas(base, ModeloFalso.criar(), lambda: indice):
        assert t.description
        for nome, schema in t.args.items():
            assert schema.get("description"), f"{t.name}.{nome} sem descrição"


def test_trace_da_comparacao(base):
    comp = comparacao.comparar_estudantes([base.estudante("Ana"), base.estudante("Bianca")])
    linhas = _descrever("comparar_fichas", {"comparacao": comp})
    assert linhas[0] == "comparei as fichas: Ana, Bianca"
    assert any("matematica: Ana 4.5 × Bianca 9.5 (lidera: Bianca)" in l for l in linhas)
