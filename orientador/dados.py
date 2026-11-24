"""Leitura dos CSVs e busca de estudantes/universidades por nome."""

from __future__ import annotations

import csv
import difflib
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path

from orientador.config import DIR_DADOS

DISCIPLINAS = (
    "matematica", "fisica", "quimica", "biologia", "computacao",
    "portugues", "historia", "filosofia",
)


def normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", sem_acento.lower())


def _lista(valor: str) -> list[str]:
    return [v.strip() for v in valor.split(";") if v.strip()]


@dataclass
class Estudante:
    usuario: str
    nome: str
    ano_conclusao: int
    notas: dict[str, float]
    projetos: float
    atividades_sociais: float
    publicacoes: float
    idiomas: dict[str, float]
    areas_interesse: list[str]
    paises_preferidos: list[str]
    universidades_preferidas: list[str]

    def para_dict(self) -> dict:
        return asdict(self)


@dataclass
class Universidade:
    sigla: str
    nome: str
    pais: str
    idioma_ensino: str
    proficiencia_minima: float
    nota_corte: float
    areas: list[str]
    cursos_destaque: list[str]
    perfil_desejado: list[str]
    apelidos: list[str] = field(default_factory=list)

    def para_dict(self) -> dict:
        return asdict(self)


@dataclass
class Base:
    estudantes: list[Estudante]
    universidades: list[Universidade]

    @staticmethod
    def _resolver(nome: str, indice: dict[str, object], corte: float):
        chave = normalizar(nome)
        if not chave:
            return None
        if chave in indice:
            return indice[chave]
        proximos = difflib.get_close_matches(chave, indice.keys(), n=1, cutoff=corte)
        return indice[proximos[0]] if proximos else None

    def estudante(self, nome: str) -> Estudante | None:
        indice = {}
        for e in self.estudantes:
            indice[normalizar(e.usuario)] = e
            indice[normalizar(e.nome)] = e
        return self._resolver(nome, indice, corte=0.8)

    def universidade(self, nome: str) -> Universidade | None:
        indice = {}
        for u in self.universidades:
            for alias in (u.sigla, u.nome, *u.apelidos):
                indice[normalizar(alias)] = u
        return self._resolver(nome, indice, corte=0.75)


def _ler_estudantes(caminho: Path) -> list[Estudante]:
    with caminho.open(encoding="utf-8") as f:
        return [
            Estudante(
                usuario=l["usuario"],
                nome=l["nome"],
                ano_conclusao=int(l["ano_conclusao"]),
                notas={d: float(l[d]) for d in DISCIPLINAS},
                projetos=float(l["projetos"]),
                atividades_sociais=float(l["atividades_sociais"]),
                publicacoes=float(l["publicacoes"]),
                idiomas={
                    "português": 10.0,
                    "inglês": float(l["ingles"]),
                    "espanhol": float(l["espanhol"]),
                    "alemão": float(l["alemao"]),
                },
                areas_interesse=_lista(l["areas_interesse"]),
                paises_preferidos=_lista(l["paises_preferidos"]),
                universidades_preferidas=_lista(l["universidades_preferidas"]),
            )
            for l in csv.DictReader(f)
        ]


def _ler_universidades(caminho: Path) -> list[Universidade]:
    with caminho.open(encoding="utf-8") as f:
        return [
            Universidade(
                sigla=l["sigla"],
                nome=l["nome"],
                pais=l["pais"],
                idioma_ensino=l["idioma_ensino"],
                proficiencia_minima=float(l["proficiencia_minima"]),
                nota_corte=float(l["nota_corte"]),
                areas=_lista(l["areas"]),
                cursos_destaque=_lista(l["cursos_destaque"]),
                perfil_desejado=_lista(l["perfil_desejado"]),
                apelidos=_lista(l["apelidos"]),
            )
            for l in csv.DictReader(f)
        ]


@lru_cache(maxsize=4)
def carregar_base(diretorio: Path = DIR_DADOS) -> Base:
    diretorio = Path(diretorio)
    return Base(
        estudantes=_ler_estudantes(diretorio / "estudantes.csv"),
        universidades=_ler_universidades(diretorio / "universidades.csv"),
    )
