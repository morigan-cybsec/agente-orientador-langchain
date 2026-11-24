from orientador import compatibilidade
from orientador.compatibilidade import PESOS, calcular


def test_score_entre_0_e_100(base):
    for e in base.estudantes:
        for u in base.universidades:
            c = calcular(e, u)
            assert 0 <= c.score <= 100
            assert abs(c.score - sum(c.componentes.values())) < 0.2


def test_componentes_respeitam_pesos(base):
    c = calcular(base.estudante("sofia"), base.universidade("MIT"))
    for nome, pontos in c.componentes.items():
        assert pontos <= PESOS[nome]


def test_idioma_penaliza_quem_nao_fala_alemao(base):
    c = calcular(base.estudante("ana"), base.universidade("TUM"))
    assert c.componentes["idioma"] == 0
    assert any("alemão" in m for m in c.motivos)


def test_universidade_em_portugues_nao_penaliza_idioma(base):
    c = calcular(base.estudante("pedro"), base.universidade("USP"))
    assert c.componentes["idioma"] == PESOS["idioma"]


def test_preferencia_declarada_soma_pontos(base):
    bianca = base.estudante("bianca")
    pref = calcular(bianca, base.universidade("UNICAMP")).componentes["preferencia"]
    sem = calcular(bianca, base.universidade("UBA")).componentes["preferencia"]
    assert pref == PESOS["preferencia"]
    assert sem == 0


def test_desempenho_abaixo_do_corte_reduz_score(base):
    ita = base.universidade("ITA")
    sofia = calcular(base.estudante("sofia"), ita).componentes["desempenho"]
    pedro = calcular(base.estudante("pedro"), ita).componentes["desempenho"]
    assert sofia > pedro


def test_ranking_ordenado_e_limitado(base):
    r = compatibilidade.ranquear(base.estudante("marcos"), base.universidades, top=5)
    assert len(r) == 5
    assert [c.score for c in r] == sorted((c.score for c in r), reverse=True)


def test_ranking_marcos_coerente(base):
    r = compatibilidade.ranquear(base.estudante("marcos"), base.universidades, top=3)
    assert r[0].universidade == "UBC"
