"""Agente (fase 2) com create_agent: o modelo escolhe as ferramentas; o retorno é um grafo LangGraph compilado."""

from __future__ import annotations

from langchain.agents import create_agent

from orientador.cadeias import REGRAS
from orientador.dados import carregar_base
from orientador.ferramentas import criar_ferramentas

PROMPT_AGENTE = (
    "Você auxilia a equipe de orientação a analisar alunos e universidades. Responda em português.\n\n"
    "Ferramentas — use sempre; nunca invente notas, scores, comparações ou regras de ingresso:\n"
    "- dados de um aluno ou universidade: dados_estudante / dados_universidade;\n"
    "- comparar dois ou mais: comparar_estudantes / comparar_universidades (não compare de cabeça);\n"
    "- indicar faculdades para um aluno: ranquear_universidades, explicando pelos componentes do score;\n"
    "- ingresso e processo seletivo: consultar_guias_admissao;\n"
    "- conversas anteriores: consultar_historico (lembra o que foi discutido; dados de alunos valem "
    "sempre pelas fichas, nunca pelo histórico).\n"
    "Se faltar o nome de quem analisar, ou se alguém não for encontrado, diga isso e peça o nome; não chute.\n\n"
    "Resposta:\n"
    "- por padrão, texto corrido e curto (2 a 5 frases), sem listas nem negrito; lista só quando "
    "pedirem (liste, tópicos, itens). Não despeje a ficha inteira;\n"
    "- quando 'lider' for 'empate', diga que empatam; não aponte vencedor;\n"
    "- nas comparações, 'de_cada' é a lista completa de cada um; 'exclusivos' vazio não significa "
    "que a pessoa não tem preferência;\n"
    "- não mencione ferramentas, JSON, 'contexto' ou o sistema.\n\n" + REGRAS
)


def construir_agente(modelo=None, base=None, indice=None, checkpointer=None, indice_historico=None):
    if modelo is None:
        from orientador.config import carregar_modelo

        modelo = carregar_modelo()
    base = base or carregar_base()

    cache = {"construir_indice": indice, "construir_indice_historico": indice_historico}

    def _preguicoso(fabrica: str):
        def obter():
            if cache[fabrica] is None:  # só gera embeddings quando a ferramenta é usada
                from orientador import rag

                cache[fabrica] = getattr(rag, fabrica)()
            return cache[fabrica]

        return obter

    return create_agent(
        modelo,
        tools=criar_ferramentas(
            base, modelo, _preguicoso("construir_indice"), _preguicoso("construir_indice_historico")
        ),
        system_prompt=PROMPT_AGENTE,
        checkpointer=checkpointer,
    )
