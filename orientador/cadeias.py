"""Cadeias LCEL: prompt | modelo | parser."""

from __future__ import annotations

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from orientador.schemas import Classificacao, PerfilAcademico

REGRAS = (
    "Regras do domínio:\n"
    "- Quem usa esta ferramenta é um funcionário da equipe de orientação (uso interno). "
    "Ele NÃO é aluno. Fale com ele de forma profissional e refira-se aos alunos em "
    "terceira pessoa.\n"
    "- Os estudantes estão no ensino médio e ainda NÃO estudam em nenhuma universidade. "
    "Eles estão escolhendo para onde se candidatar.\n"
    "- universidades_preferidas e paises_preferidos são desejos do estudante, não matrícula.\n"
    "- Notas, projetos, atividades sociais, publicações e idiomas vão de 0 a 10.\n"
    "- ano_conclusao é o ano em que o estudante termina o ensino médio.\n"
    "- nota_corte e proficiencia_minima da universidade também vão de 0 a 10.\n"
)

PROMPT_CLASSIFICACAO = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Você classifica pedidos feitos por um funcionário da equipe de orientação "
            "acadêmica, que analisa alunos e universidades. Extraia a intenção e os nomes citados na última pergunta. "
            "Se ela se referir a algo da conversa (ela, ele, as duas, essa faculdade), "
            "use o histórico para descobrir os nomes. "
            "Se a mensagem só corrige um nome da pergunta anterior, marque corrige_anterior "
            "e informe apenas o nome novo. "
            "Não corrija nomes: copie como o usuário escreveu.",
        ),
        ("placeholder", "{historico}"),
        ("human", "{pergunta}"),
    ]
)

PROMPT_PERFIL = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Você é uma consultora de carreira. Monte o perfil acadêmico do estudante "
            "com base APENAS nos dados fornecidos. Seja direta.\n\n" + REGRAS,
        ),
        ("human", "Dados do estudante:\n{dados_estudante}"),
    ]
)

PROMPT_RESPOSTA = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Você auxilia a equipe de orientação a analisar alunos e universidades. "
            "Responda em português usando "
            "SOMENTE os dados disponíveis abaixo. Não mencione 'contexto', 'dados fornecidos' "
            "nem o sistema: fale "
            "direto com o usuário.\n" + REGRAS + "\n"
            "Formato pedido: {formato}. Se for 'texto': texto corrido e curto (2 a 5 frases), "
            "sem listas nem negrito. Se for 'lista': tópicos curtos, um item por linha. "
            "Em ambos, não despeje todos os dados nem todos os números: o usuário já viu o "
            "processamento.\n"
            "Quando houver 'comparacao', compare pelos campos em que mais diferem (veja "
            "'lider' e 'diferenca') e pelo que têm em comum, sem repetir a ficha inteira. "
            "Em 'conjuntos', 'de_cada' é a lista completa de cada um; 'exclusivos' vazio "
            "significa que tudo dele está em comum, não que ele não tem preferência.\n"
            "'historico_trechos' são registros de conversas anteriores (o nome é a data): use "
            "para dizer o que foi discutido e quando. Notas e dados de alunos valem sempre "
            "pelas fichas, nunca pelo histórico.\n"
            "Se algum nome não foi encontrado ('nao_encontrados'), avise em uma frase e "
            "responda normalmente com o que foi encontrado.\n"
            "Ao recomendar, diga o resultado e o motivo principal; quando houver "
            "ranking, o motivo vem dos componentes do score (desempenho, afinidade, idioma, "
            "preferência) — não invente outra nota. Quando 'lider' for 'empate', diga que "
            "empatam; não aponte um vencedor. Se a informação não estiver nos dados, "
            "diga isso. Nomes na pergunta "
            "podem ter erro de digitação ou ser referências (ela, as duas): 'nomes_resolvidos' "
            "mostra a qual estudante ou universidade cada um corresponde.\n\n"
            "Dados disponíveis:\n{contexto}",
        ),
        ("placeholder", "{historico}"),
        ("human", "{pergunta}"),
    ]
)


def cadeia_classificacao(modelo):
    return PROMPT_CLASSIFICACAO | modelo.with_structured_output(Classificacao)


def cadeia_perfil(modelo):
    return PROMPT_PERFIL | modelo.with_structured_output(PerfilAcademico)


def cadeia_resposta(modelo):
    return PROMPT_RESPOSTA | modelo | StrOutputParser()
