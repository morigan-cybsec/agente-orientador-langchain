"""Ferramentas do agente (@tool).

Com parse_docstring=True, o resumo vira a descrição da ferramenta e a seção
Args vira a descrição de cada argumento — é isso que o modelo lê para decidir
quando e como chamar cada uma.
"""

from __future__ import annotations

import json

from langchain_core.tools import tool

from orientador import comparacao, compatibilidade
from orientador.cadeias import cadeia_perfil
from orientador.dados import Base


def _json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)


def criar_ferramentas(base: Base, modelo, obter_indice, obter_indice_historico=None) -> list:
    gerador_perfil = cadeia_perfil(modelo)

    def _nao_encontrado(tipo: str, nome: str, opcoes: list[str]) -> str:
        return _json({"erro": f"{tipo} '{nome}' não encontrado", "opcoes": opcoes})

    @tool(parse_docstring=True)
    def dados_estudante(nome: str) -> str:
        """Busca a ficha de UM estudante: notas, idiomas, interesses e preferências.

        Use quando a pergunta pedir os dados de um estudante. Para dois ou mais, prefira
        comparar_estudantes. Retorna JSON com a ficha, ou {"erro", "opcoes"} se não achar.

        Args:
            nome: Nome do estudante, como o usuário escreveu (aceita erro de digitação).
        """
        e = base.estudante(nome)
        if not e:
            return _nao_encontrado("estudante", nome, [x.nome for x in base.estudantes])
        return _json(e.para_dict())

    @tool(parse_docstring=True)
    def dados_universidade(nome: str) -> str:
        """Busca a ficha de UMA universidade: país, idioma, nota de corte, áreas e perfil desejado.

        Retorna JSON com a ficha, ou {"erro", "opcoes"} se não achar.

        Args:
            nome: Sigla, nome completo ou apelido da universidade (aceita erro de digitação).
        """
        u = base.universidade(nome)
        if not u:
            return _nao_encontrado("universidade", nome, [x.sigla for x in base.universidades])
        return _json(u.para_dict())

    @tool(parse_docstring=True)
    def listar_universidades() -> str:
        """Lista todas as universidades cadastradas.

        Use para saber quais opções existem antes de buscar ou comparar.
        Retorna JSON com sigla, país e idioma de cada uma.
        """
        return _json([{"sigla": u.sigla, "pais": u.pais, "idioma": u.idioma_ensino} for u in base.universidades])

    @tool(parse_docstring=True)
    def comparar_estudantes(nomes: list[str]) -> str:
        """Compara as fichas de dois ou mais estudantes campo a campo.

        Para cada nota, idioma e atividade, retorna os valores, quem lidera e a diferença;
        para interesses, países e universidades preferidas, a lista de cada um, o que têm
        em comum e o que é exclusivo de cada um. Use quando pedirem para comparar estudantes.

        Args:
            nomes: Nomes dos estudantes a comparar (mínimo 2).
        """
        fichas = [e for e in (base.estudante(n) for n in nomes) if e]
        if len(fichas) < 2:
            return _json({"erro": "preciso de pelo menos 2 estudantes encontrados", "opcoes": [x.nome for x in base.estudantes]})
        return _json(comparacao.comparar_estudantes(fichas))

    @tool(parse_docstring=True)
    def comparar_universidades(nomes: list[str]) -> str:
        """Compara as fichas de duas ou mais universidades campo a campo.

        Retorna país, idioma, nota de corte e proficiência mínima de cada uma, quem é mais
        exigente, e as áreas e perfis em comum ou exclusivos.

        Args:
            nomes: Siglas ou nomes das universidades a comparar (mínimo 2).
        """
        fichas = [u for u in (base.universidade(n) for n in nomes) if u]
        if len(fichas) < 2:
            return _json({"erro": "preciso de pelo menos 2 universidades encontradas", "opcoes": [x.sigla for x in base.universidades]})
        return _json(comparacao.comparar_universidades(fichas))

    @tool(parse_docstring=True)
    def ranquear_universidades(estudante: str, universidades: list[str] | None = None) -> str:
        """Calcula o score de compatibilidade (0 a 100) de um estudante com universidades.

        O score é fixo por regra: desempenho 35, afinidade de área 25, idioma 20,
        preferência 20. Use SEMPRE esta ferramenta para recomendar; nunca invente notas.
        Retorna a lista ordenada com score, componentes e motivos.

        Args:
            estudante: Nome do estudante.
            universidades: Restringe a comparação a estas universidades. Se vazio, ranqueia todas e devolve as 5 melhores.
        """
        e = base.estudante(estudante)
        if not e:
            return _nao_encontrado("estudante", estudante, [x.nome for x in base.estudantes])
        if universidades:
            candidatas = [u for u in (base.universidade(n) for n in universidades) if u]
            top = None
        else:
            candidatas, top = base.universidades, 5
        return _json([c.para_dict() for c in compatibilidade.ranquear(e, candidatas, top)])

    @tool(parse_docstring=True)
    def perfil_academico(estudante: str) -> str:
        """Gera o perfil acadêmico de um estudante a partir da ficha dele.

        Busca a ficha sozinha. Retorna JSON com pontos fortes, pontos de atenção,
        áreas recomendadas e um resumo.

        Args:
            estudante: Nome do estudante.
        """
        e = base.estudante(estudante)
        if not e:
            return _nao_encontrado("estudante", estudante, [x.nome for x in base.estudantes])
        perfil = gerador_perfil.invoke({"dados_estudante": _json(e.para_dict())})
        return _json(perfil.model_dump())

    @tool(parse_docstring=True)
    def consultar_guias_admissao(pergunta: str, universidade: str | None = None) -> str:
        """Busca trechos dos guias de admissão: formas de ingresso, o que pesa e dicas.

        Retorna JSON com até 3 trechos e a universidade de cada um.

        Args:
            pergunta: O que se quer saber sobre o ingresso.
            universidade: Filtra os guias de uma universidade específica.
        """
        alvo = None
        if universidade:
            u = base.universidade(universidade)
            alvo = [u.sigla] if u else None
        docs = obter_indice().buscar(pergunta, universidades=alvo, k=3)
        return _json([{"universidade": d.metadata["universidade"], "trecho": d.page_content} for d in docs])

    @tool(parse_docstring=True)
    def consultar_historico(pergunta: str) -> str:
        """Busca trechos de conversas anteriores registradas em conversas/.

        Serve para lembrar o que já foi discutido e quando. Dados de alunos devem vir
        das fichas, não daqui. Retorna JSON com até 4 trechos e a data da conversa.

        Args:
            pergunta: O que se quer lembrar das conversas anteriores.
        """
        if obter_indice_historico is None:
            return _json({"erro": "histórico indisponível"})
        docs = obter_indice_historico().buscar(pergunta, k=4)
        return _json([{"conversa": d.metadata["conversa"], "trecho": d.page_content} for d in docs])

    return [
        dados_estudante,
        dados_universidade,
        listar_universidades,
        comparar_estudantes,
        comparar_universidades,
        ranquear_universidades,
        perfil_academico,
        consultar_guias_admissao,
        consultar_historico,
    ]
