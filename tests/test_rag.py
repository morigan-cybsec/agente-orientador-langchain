from orientador.rag import carregar_guias


def test_um_guia_por_universidade(base):
    guias = carregar_guias()
    assert {g.metadata["universidade"] for g in guias} == {u.sigla for u in base.universidades}


def test_indice_tem_pedacos(indice):
    assert indice.total_pedacos >= 12


def test_filtro_por_universidade(indice):
    docs = indice.buscar("como funciona o ingresso?", universidades=["MIT"], k=3)
    assert docs and all(d.metadata["universidade"] == "MIT" for d in docs)


def test_filtro_multiplo(indice):
    docs = indice.buscar("dicas", universidades=["USP", "UBA"], k=10)
    assert {d.metadata["universidade"] for d in docs} <= {"USP", "UBA"}


def test_k_respeitado(indice):
    assert len(indice.buscar("vestibular", k=2)) == 2
