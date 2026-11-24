from langgraph.checkpoint.memory import InMemorySaver

from orientador.grafo import construir_grafo
from orientador.schemas import Classificacao as C


def _rodar(app, pergunta, thread="t1"):
    cfg = {"configurable": {"thread_id": thread}}
    estado = app.invoke({"messages": [("user", pergunta)]}, cfg)
    return estado


def _app(modelo, base, indice, memoria=False):
    return construir_grafo(modelo, base, indice, checkpointer=InMemorySaver() if memoria else None)


def test_dados_universidade_com_erro_de_digitacao(modelo_com, base, indice):
    m = modelo_com({"uNicomP": C(intencao="dados", universidades=["uNicomP"])})
    e = _rodar(_app(m, base, indice), "Quais os dados da uNicomP?")
    assert [u["sigla"] for u in e["universidades"]] == ["UNICAMP"]
    assert e["messages"][-1].content == "ok"


def test_dados_de_dois_estudantes(modelo_com, base, indice):
    m = modelo_com({"Ana e da Bianca": C(intencao="dados", estudantes=["Ana", "Bianca"])})
    e = _rodar(_app(m, base, indice), "Quais os dados de Ana e da Bianca?")
    assert [x["usuario"] for x in e["estudantes"]] == ["ana", "bianca"]


def test_recomendar_sem_estudante_pede_esclarecimento(modelo_com, base, indice):
    m = modelo_com({"qual faculdade": C(intencao="recomendar")})
    e = _rodar(_app(m, base, indice), "qual faculdade você recomenda?")
    assert "Estudantes cadastrados" in e["messages"][-1].content
    assert "texto" not in m.chamadas


def test_estudante_inexistente_pede_esclarecimento(modelo_com, base, indice):
    m = modelo_com({"Zé": C(intencao="perfil", estudantes=["Zé"])})
    e = _rodar(_app(m, base, indice), "perfil do Zé")
    assert "Não encontrei: Zé" in e["messages"][-1].content


def test_perfil_usa_cadeia_estruturada(modelo_com, base, indice):
    m = modelo_com({"perfil acadêmico": C(intencao="perfil", estudantes=["Ana"])})
    e = _rodar(_app(m, base, indice), "Crie um perfil acadêmico para a Ana!")
    assert e["perfil"]["resumo"] == "perfil gerado pelo modelo falso"
    assert m.chamadas == ["Classificacao", "PerfilAcademico", "texto"]


def test_recomendar_ranqueia_e_consulta_guias(modelo_com, base, indice):
    m = modelo_com({"mais chance": C(intencao="recomendar", estudantes=["Ana"])})
    e = _rodar(_app(m, base, indice), "Quais faculdades a Ana tem mais chance de entrar?")
    assert len(e["ranking"]) == 5
    top3 = {r["universidade"] for r in e["ranking"][:3]}
    assert e["trechos"] and all(t.split("]")[0][1:] in top3 for t in e["trechos"])


def test_comparar_restringe_as_citadas(modelo_com, base, indice):
    m = modelo_com({"USP e UFRJ": C(intencao="recomendar", estudantes=["Ana"], universidades=["USP", "UFRJ"])})
    e = _rodar(_app(m, base, indice), "Dentre USP e UFRJ, qual você recomenda para a Ana?")
    assert {r["universidade"] for r in e["ranking"]} == {"USP", "UFRJ"}


def test_admissao_filtra_guia_da_universidade(modelo_com, base, indice):
    m = modelo_com({"ingresso": C(intencao="admissao", universidades=["UBA"])})
    e = _rodar(_app(m, base, indice), "Como é o ingresso na UBA?")
    assert e["trechos"] and all(t.startswith("[UBA]") for t in e["trechos"])


def test_memoria_lembra_estudante_entre_turnos(modelo_com, base, indice):
    m = modelo_com({
        "perfil": C(intencao="perfil", estudantes=["Bianca"]),
        "e qual faculdade": C(intencao="recomendar"),
    })
    app = _app(m, base, indice, memoria=True)
    _rodar(app, "faça o perfil da Bianca")
    e = _rodar(app, "e qual faculdade combina com ela?")
    assert e["estudante_atual"]["usuario"] == "bianca"
    assert e["ranking"]


def test_perfil_em_cache_nao_chama_llm_de_novo(modelo_com, base, indice):
    m = modelo_com({"perfil": C(intencao="perfil", estudantes=["Ana"])})
    app = _app(m, base, indice, memoria=True)
    _rodar(app, "perfil da Ana")
    _rodar(app, "de novo o perfil da Ana")
    assert m.chamadas.count("PerfilAcademico") == 1


def test_troca_de_estudante_invalida_perfil(modelo_com, base, indice):
    m = modelo_com({
        "Ana": C(intencao="perfil", estudantes=["Ana"]),
        "Marcos": C(intencao="perfil", estudantes=["Marcos"]),
    })
    app = _app(m, base, indice, memoria=True)
    _rodar(app, "perfil da Ana")
    _rodar(app, "perfil do Marcos")
    assert m.chamadas.count("PerfilAcademico") == 2


def test_fora_de_escopo_vai_direto_ao_redator(modelo_com, base, indice):
    m = modelo_com({})
    _rodar(_app(m, base, indice), "qual a capital da França?")
    assert m.chamadas == ["Classificacao", "texto"]


def test_threads_isoladas(modelo_com, base, indice):
    m = modelo_com({"perfil": C(intencao="perfil", estudantes=["Ana"]), "recomenda": C(intencao="recomendar")})
    app = _app(m, base, indice, memoria=True)
    _rodar(app, "perfil da Ana", thread="a")
    e = _rodar(app, "o que recomenda?", thread="b")
    assert "Estudantes cadastrados" in e["messages"][-1].content


def test_classificador_recebe_historico(modelo_com, base, indice):
    vistos = []
    m = modelo_com({"dados de Ana e da Bianca": C(intencao="dados", estudantes=["Ana", "Bianca"])})
    original = m.roteiro["Classificacao"]
    m.roteiro["Classificacao"] = lambda t: (vistos.append(t), original(t))[1]
    app = _app(m, base, indice, memoria=True)
    _rodar(app, "Quais os dados de Ana e da Bianca?")
    _rodar(app, "Compare as duas")
    assert "Quais os dados de Ana e da Bianca?" in vistos[-1]


def test_ranking_de_dois_estudantes(modelo_com, base, indice):
    m = modelo_com({"Compare": C(intencao="recomendar", estudantes=["Ana", "Bianca"])})
    e = _rodar(_app(m, base, indice), "Compare as duas")
    assert {r["estudante"] for r in e["ranking"]} == {"Ana", "Bianca"}
    assert len(e["ranking"]) == 6


def test_nomes_resolvidos_vao_para_o_contexto(modelo_com, base, indice):
    m = modelo_com({"uni comp": C(intencao="dados", universidades=["uni comp"])})
    e = _rodar(_app(m, base, indice), "Quais os dados da uni comp?")
    assert e["nomes_resolvidos"] == {"uni comp": "UNICAMP"}


def test_comparar_estudantes_so_busca_dados(modelo_com, base, indice):
    m = modelo_com({"Compare": C(intencao="comparar", estudantes=["Ana", "Bianca"])})
    e = _rodar(_app(m, base, indice), "Compare a Ana com a Bianca")
    assert [x["nome"] for x in e["estudantes"]] == ["Ana", "Bianca"]
    assert e["ranking"] == [] and e["trechos"] == []
    assert m.chamadas == ["Classificacao", "texto"]


def test_comparar_universidades(modelo_com, base, indice):
    m = modelo_com({"USP": C(intencao="comparar", universidades=["USP", "uni camp"])})
    e = _rodar(_app(m, base, indice), "Compare USP e uni camp")
    assert [u["sigla"] for u in e["universidades"]] == ["USP", "UNICAMP"]
    assert e["ranking"] == []


def test_nos_executados_em_ordem(modelo_com, base, indice):
    m = modelo_com({"Compare": C(intencao="comparar", estudantes=["Ana", "Bianca"])})
    app = _app(m, base, indice)
    nos = [no for passo in app.stream({"messages": [("user", "Compare as duas")]}, stream_mode="updates") for no in passo]
    assert nos == ["classificar", "buscar_dados", "comparar_fichas", "responder"]


def test_formato_lista_vai_para_o_estado(modelo_com, base, indice):
    m = modelo_com({"listar": C(intencao="comparar", estudantes=["Ana", "Gabriel"], formato="lista")})
    e = _rodar(_app(m, base, indice), "pode listar as diferenças")
    assert e["formato"] == "lista"


def test_formato_padrao_texto(modelo_com, base, indice):
    m = modelo_com({"dados": C(intencao="dados", estudantes=["Ana"])})
    assert _rodar(_app(m, base, indice), "dados da Ana")["formato"] == "texto"


def test_prompt_do_redator_recebe_formato():
    from orientador.cadeias import PROMPT_RESPOSTA

    msgs = PROMPT_RESPOSTA.format_messages(contexto="{}", historico=[], pergunta="x", formato="lista")
    assert "Formato pedido: lista" in msgs[0].content


def test_correcao_troca_nome_nao_encontrado_e_mantem_intencao(modelo_com, base, indice):
    m = modelo_com({
        "com o José": C(intencao="comparar", estudantes=["Ana", "Bianca", "José"]),
        "referindo ao gabriel": C(intencao="dados", estudantes=["gabriel"], corrige_anterior=True),
    })
    app = _app(m, base, indice, memoria=True)
    _rodar(app, "E essas duas com o José")
    e = _rodar(app, "estava me referindo ao gabriel")
    assert e["intencao"] == "comparar"
    assert e["correcao"] is True
    assert [x["nome"] for x in e["estudantes"]] == ["Ana", "Bianca", "Gabriel"]
    assert e["comparacao"]["comparados"] == ["Ana", "Bianca", "Gabriel"]


def test_regras_dizem_que_usuario_e_funcionario():
    from orientador.cadeias import PROMPT_RESPOSTA

    msgs = PROMPT_RESPOSTA.format_messages(contexto="{}", historico=[], pergunta="x", formato="texto")
    assert "NÃO é aluno" in msgs[0].content


def test_comparar_sem_nomes_pede_esclarecimento(modelo_com, base, indice):
    m = modelo_com({"diferenças": C(intencao="comparar", formato="lista")})
    e = _rodar(_app(m, base, indice), "pode listar as diferenças")
    assert "preciso de pelo menos 2" in e["messages"][-1].content
    assert m.chamadas == ["Classificacao"]


def test_comparar_com_um_so_pede_esclarecimento(modelo_com, base, indice):
    m = modelo_com({"Compare": C(intencao="comparar", estudantes=["Ana", "Zé"])})
    e = _rodar(_app(m, base, indice), "Compare Ana e Zé")
    texto = e["messages"][-1].content
    assert "Não encontrei: Zé" in texto and "preciso de pelo menos 2" in texto


def test_prompt_nao_usa_rotulo_contexto():
    from orientador.cadeias import PROMPT_RESPOSTA

    msgs = PROMPT_RESPOSTA.format_messages(contexto="{}", historico=[], pergunta="x", formato="texto")
    assert "Contexto:" not in msgs[0].content and "Dados disponíveis:" in msgs[0].content
