import pytest

from orientador.dados import normalizar


@pytest.mark.parametrize(
    "entrada, sigla",
    [
        ("USP", "USP"),
        ("uNiCAmP", "UNICAMP"),
        ("uni camp", "UNICAMP"),
        ("uNicomP", "UNICAMP"),
        ("Universidade de São Paulo", "USP"),
        ("universidade de sao paulo", "USP"),
        ("Technical University of Munich", "TUM"),
        ("u of t", "Toronto"),
        ("Imperial College", "Imperial"),
    ],
)
def test_universidade_encontrada(base, entrada, sigla):
    assert base.universidade(entrada).sigla == sigla


@pytest.mark.parametrize("entrada", ["Harvard", "", "   ", "xyz"])
def test_universidade_inexistente(base, entrada):
    assert base.universidade(entrada) is None


@pytest.mark.parametrize(
    "entrada, usuario",
    [("Ana", "ana"), ("ANA", "ana"), ("joão", "joao"), ("Joao", "joao"), ("Bianka", "bianca")],
)
def test_estudante_encontrado(base, entrada, usuario):
    assert base.estudante(entrada).usuario == usuario


def test_estudante_inexistente(base):
    assert base.estudante("Zé Ninguém") is None


def test_normalizar():
    assert normalizar("Uni Camp!") == "unicamp"
    assert normalizar("Técnica") == "tecnica"


def test_base_carregada(base):
    assert len(base.estudantes) == 25
    assert len(base.universidades) == 12
    ana = base.estudante("ana")
    assert ana.notas["biologia"] == 8.5
    assert ana.universidades_preferidas == ["UNICAMP", "TUM"]
