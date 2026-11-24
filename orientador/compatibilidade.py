"""Score de compatibilidade estudante x universidade (0-100)."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from orientador.dados import Estudante, Universidade, normalizar

PESOS = {"desempenho": 35, "afinidade": 25, "idioma": 20, "preferencia": 20}

DISCIPLINAS_POR_AREA = {
    "Exatas": ["matematica", "fisica"],
    "Computação": ["computacao", "matematica"],
    "Engenharia": ["matematica", "fisica"],
    "Saúde": ["biologia", "quimica"],
    "Biológicas": ["biologia", "quimica"],
    "Humanas": ["portugues", "historia", "filosofia"],
    "Negócios": ["matematica", "portugues"],
}


@dataclass
class Compatibilidade:
    universidade: str
    score: float
    componentes: dict[str, float]
    motivos: list[str]

    def para_dict(self) -> dict:
        return asdict(self)


def _areas_relevantes(est: Estudante, uni: Universidade) -> list[str]:
    comuns = [a for a in est.areas_interesse if a in uni.areas]
    return comuns or uni.areas


def media_nas_areas(est: Estudante, areas: list[str]) -> float:
    disciplinas = {d for a in areas for d in DISCIPLINAS_POR_AREA.get(a, [])}
    if not disciplinas:
        return sum(est.notas.values()) / len(est.notas)
    return sum(est.notas[d] for d in disciplinas) / len(disciplinas)


def calcular(est: Estudante, uni: Universidade) -> Compatibilidade:
    motivos: list[str] = []

    areas = _areas_relevantes(est, uni)
    media = media_nas_areas(est, areas)
    fator_desempenho = min(1.0, media / uni.nota_corte) ** 2
    motivos.append(
        f"média {media:.1f} nas disciplinas de {', '.join(areas)} vs. corte {uni.nota_corte:.1f}"
    )

    if est.areas_interesse:
        comuns = [a for a in est.areas_interesse if a in uni.areas]
        fator_afinidade = len(comuns) / len(est.areas_interesse)
        motivos.append(
            f"áreas em comum: {', '.join(comuns)}" if comuns else "nenhuma área de interesse em comum"
        )
    else:
        fator_afinidade = 0.5

    nivel = est.idiomas.get(uni.idioma_ensino, 0.0)
    if uni.proficiencia_minima <= 0:
        fator_idioma = 1.0
    else:
        fator_idioma = min(1.0, nivel / uni.proficiencia_minima)
        if fator_idioma < 1:
            motivos.append(
                f"{uni.idioma_ensino} {nivel:.1f} abaixo do mínimo {uni.proficiencia_minima:.1f}"
            )

    fator_pref = 0.0
    if uni.pais in est.paises_preferidos:
        fator_pref += 0.5
        motivos.append(f"{uni.pais} está entre os países preferidos")
    if normalizar(uni.sigla) in {normalizar(u) for u in est.universidades_preferidas}:
        fator_pref += 0.5
        motivos.append("está na lista de universidades preferidas")

    componentes = {
        "desempenho": round(PESOS["desempenho"] * fator_desempenho, 1),
        "afinidade": round(PESOS["afinidade"] * fator_afinidade, 1),
        "idioma": round(PESOS["idioma"] * fator_idioma, 1),
        "preferencia": round(PESOS["preferencia"] * fator_pref, 1),
    }
    return Compatibilidade(
        universidade=uni.sigla,
        score=round(sum(componentes.values()), 1),
        componentes=componentes,
        motivos=motivos,
    )


def ranquear(
    est: Estudante, universidades: list[Universidade], top: int | None = 5
) -> list[Compatibilidade]:
    resultado = sorted((calcular(est, u) for u in universidades), key=lambda c: c.score, reverse=True)
    return resultado[:top] if top else resultado
