"""Schemas Pydantic usados com with_structured_output."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Intencao = Literal["dados", "comparar", "perfil", "recomendar", "admissao", "historico", "outro"]


class Classificacao(BaseModel):
    intencao: Intencao = Field(
        description=(
            "dados: pedir dados de um ou mais estudantes ou universidades; "
            "comparar: comparar estudantes entre si ou universidades entre si; "
            "perfil: criar/analisar o perfil acadêmico de um estudante; "
            "recomendar: indicar ou ranquear universidades para um estudante; "
            "admissao: dúvida sobre processo seletivo/ingresso de uma universidade; "
            "historico: pergunta sobre conversas ou sessões anteriores (o que já foi visto, "
            "comparado ou recomendado antes); "
            "outro: qualquer coisa fora desses temas."
        )
    )
    estudantes: list[str] = Field(
        default_factory=list,
        description="Nomes de estudantes citados, exatamente como escritos. Vazio se nenhum.",
    )
    universidades: list[str] = Field(
        default_factory=list,
        description="Universidades citadas, exatamente como escritas (mesmo com erro). Vazio se nenhuma.",
    )
    corrige_anterior: bool = Field(
        default=False,
        description=(
            "true quando a mensagem só corrige ou troca um nome da pergunta anterior "
            "(ex.: 'me referia ao Gabriel', 'quis dizer USP'). Nesse caso, coloque em "
            "estudantes/universidades apenas o nome novo."
        ),
    )
    formato: Literal["texto", "lista"] = Field(
        default="texto",
        description="lista: quando o usuário pede lista, tópicos, itens ou 'listar'; texto: nos demais casos.",
    )


class PerfilAcademico(BaseModel):
    nome: str = Field(description="Nome do estudante")
    ano_conclusao: int = Field(description="Ano de conclusão do ensino médio")
    pontos_fortes: list[str] = Field(description="Até 4 pontos fortes, baseados nas notas e atividades")
    pontos_de_atencao: list[str] = Field(description="Até 3 pontos a desenvolver")
    areas_recomendadas: list[str] = Field(description="Áreas de estudo mais coerentes com o histórico")
    resumo: str = Field(
        description="Parágrafo curto destacando o que torna o estudante um candidato único"
    )
