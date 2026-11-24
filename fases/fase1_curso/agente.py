"""Fase 1: o agente como no curso, atualizado para LangChain 1.x.

Mesmas 4 ferramentas do curso, com o mesmo comportamento:
  - busca por igualdade exata (nome em minúsculo == valor do CSV);
  - perfil_academico só formata os dados que o próprio agente buscou antes;
  - nenhuma regra de domínio, nenhuma ferramenta de comparação ou ranking:
    o LLM compara e recomenda "de cabeça".
É o ponto de partida que a fase 2 corrige.
"""

from __future__ import annotations

import csv
import json

from langchain.agents import create_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from orientador.config import DIR_DADOS

PROMPT_AGENTE = "Você é um assistente que ajuda com estudantes e universidades. Use as ferramentas disponíveis."


def _ler(arquivo: str) -> list[dict]:
    with (DIR_DADOS / arquivo).open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


class PerfilAcademico(BaseModel):
    nome: str = Field(description="nome do estudante")
    ano_de_conclusao: int = Field(description="ano de conclusão")
    resumo: str = Field(description="resumo das principais características do estudante")


def criar_ferramentas(modelo) -> list:
    prompt_perfil = ChatPromptTemplate.from_messages([
        ("system", "Persona: você é uma consultora de carreira. Formate o estudante para seu perfil acadêmico."),
        ("human", "{dados}"),
    ])
    cadeia_perfil = prompt_perfil | modelo.with_structured_output(PerfilAcademico)

    @tool
    def dados_de_estudante(nome: str) -> str:
        """Extrai o histórico e as preferências de um estudante. Passe o nome do estudante."""
        alvo = nome.lower().strip()
        achados = [l for l in _ler("estudantes.csv") if l["usuario"] == alvo]
        return json.dumps(achados[0] if achados else {}, ensure_ascii=False)

    @tool
    def dados_de_universidade(nome: str) -> str:
        """Extrai os dados de uma universidade. Passe o nome da universidade."""
        alvo = nome.lower().strip()
        achados = [l for l in _ler("universidades.csv") if l["sigla"].lower() == alvo]
        return json.dumps(achados[0] if achados else {}, ensure_ascii=False)

    @tool
    def todas_universidades() -> str:
        """Carrega os dados de todas as universidades. Não precisa de parâmetro."""
        return json.dumps(_ler("universidades.csv"), ensure_ascii=False)

    @tool
    def perfil_academico(dados_do_estudante: str) -> str:
        """Cria um perfil acadêmico de um estudante. Requer como entrada todos os dados do
        estudante: busque os dados antes de chamar esta ferramenta."""
        return json.dumps(cadeia_perfil.invoke({"dados": dados_do_estudante}).model_dump(), ensure_ascii=False)

    return [dados_de_estudante, dados_de_universidade, todas_universidades, perfil_academico]


def construir_agente(modelo=None, checkpointer=None):
    if modelo is None:
        from orientador.config import carregar_modelo

        modelo = carregar_modelo()
    return create_agent(modelo, tools=criar_ferramentas(modelo), system_prompt=PROMPT_AGENTE, checkpointer=checkpointer)
