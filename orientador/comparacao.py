"""Comparação campo a campo entre fichas (estudantes ou universidades)."""

from __future__ import annotations

from orientador.dados import DISCIPLINAS, Estudante, Universidade


def _numerico(campo: str, valores: dict[str, float]) -> dict:
    maior = max(valores.values())
    menor = min(valores.values())
    lideres = [nome for nome, v in valores.items() if v == maior]
    return {
        "campo": campo,
        "valores": valores,
        "lider": lideres[0] if len(lideres) == 1 else "empate",
        "diferenca": round(maior - menor, 1),
    }


def _conjuntos(campo: str, listas: dict[str, list[str]]) -> dict:
    conjuntos = {nome: set(v) for nome, v in listas.items()}
    comuns = set.intersection(*conjuntos.values())
    return {
        "campo": campo,
        "de_cada": {nome: sorted(c) for nome, c in conjuntos.items()},
        "em_comum": sorted(comuns),
        "exclusivos": {nome: sorted(c - comuns) for nome, c in conjuntos.items()},
    }


def comparar_estudantes(estudantes: list[Estudante]) -> dict:
    nomes = [e.nome for e in estudantes]
    numericos = [_numerico(d, {e.nome: e.notas[d] for e in estudantes}) for d in DISCIPLINAS]
    numericos += [
        _numerico(campo, {e.nome: getattr(e, campo) for e in estudantes})
        for campo in ("projetos", "atividades_sociais", "publicacoes")
    ]
    numericos += [
        _numerico(idioma, {e.nome: e.idiomas[idioma] for e in estudantes})
        for idioma in ("inglês", "espanhol", "alemão")
    ]
    medias = {e.nome: round(sum(e.notas.values()) / len(e.notas), 1) for e in estudantes}
    return {
        "tipo": "estudantes",
        "comparados": nomes,
        "media_geral": medias,
        "numericos": numericos,
        "conjuntos": [
            _conjuntos("areas_interesse", {e.nome: e.areas_interesse for e in estudantes}),
            _conjuntos("paises_preferidos", {e.nome: e.paises_preferidos for e in estudantes}),
            _conjuntos("universidades_preferidas", {e.nome: e.universidades_preferidas for e in estudantes}),
        ],
    }


def comparar_universidades(universidades: list[Universidade]) -> dict:
    return {
        "tipo": "universidades",
        "comparados": [u.sigla for u in universidades],
        "pais": {u.sigla: u.pais for u in universidades},
        "idioma_ensino": {u.sigla: u.idioma_ensino for u in universidades},
        "numericos": [
            _numerico("nota_corte", {u.sigla: u.nota_corte for u in universidades}),
            _numerico("proficiencia_minima", {u.sigla: u.proficiencia_minima for u in universidades}),
        ],
        "conjuntos": [
            _conjuntos("areas", {u.sigla: u.areas for u in universidades}),
            _conjuntos("perfil_desejado", {u.sigla: u.perfil_desejado for u in universidades}),
        ],
    }
