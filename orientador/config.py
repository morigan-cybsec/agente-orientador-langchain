"""Modelo e embeddings via init_chat_model / init_embeddings (string "provedor:modelo")."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

RAIZ = Path(__file__).resolve().parent.parent
DIR_DADOS = Path(os.getenv("ORIENTADOR_DADOS", RAIZ / "dados"))
DIR_CONVERSAS = Path(os.getenv("ORIENTADOR_CONVERSAS", RAIZ / "conversas"))

# nome: (variáveis aceitas para a chave, modelo de chat, modelo de embeddings ou None)
PROVEDORES = {
    "openai": (("OPENAI_API_KEY",), "openai:gpt-4o-mini", "openai:text-embedding-3-small"),
    "gemini": (("GOOGLE_API_KEY", "GEMINI_API_KEY"), "google_genai:gemini-3.8-flash", "google_genai:gemini-embedding-001"),
    "anthropic": (("ANTHROPIC_API_KEY",), "anthropic:claude-haiku-5-5", None),
}


def _tem_chave(provedor: str) -> bool:
    for var in PROVEDORES[provedor][0]:
        valor = os.getenv(var, "").strip()
        if valor and not valor.endswith("..."):
            return True
    return False


def provedor_ativo() -> str | None:
    escolhido = os.getenv("ORIENTADOR_PROVEDOR", "").strip().lower()
    if escolhido:
        return escolhido if escolhido in PROVEDORES else None
    return next((p for p in PROVEDORES if _tem_chave(p)), None)


def carregar_modelo(nome: str | None = None):
    from langchain.chat_models import init_chat_model

    nome = nome or os.getenv("ORIENTADOR_MODELO") or PROVEDORES[provedor_ativo()][1]
    extras = {}
    if os.getenv("ORIENTADOR_TEMPERATURA"):  # alguns modelos (ex.: Gemini flash-lite) não aceitam
        extras["temperature"] = float(os.getenv("ORIENTADOR_TEMPERATURA"))
    return init_chat_model(nome, **extras)


def carregar_embeddings(nome: str | None = None):
    """Retorna None quando nenhum provedor com chave oferece embeddings; o RAG usa busca por palavras."""
    from langchain.embeddings import init_embeddings

    nome = nome or os.getenv("ORIENTADOR_EMBEDDINGS")
    if not nome:
        candidatos = [provedor_ativo()] + [p for p in PROVEDORES if p != provedor_ativo()]
        nome = next((PROVEDORES[p][2] for p in candidatos if p and PROVEDORES[p][2] and _tem_chave(p)), None)
    return init_embeddings(nome) if nome else None


def descricao() -> str:
    p = provedor_ativo()
    modelo = os.getenv("ORIENTADOR_MODELO") or (PROVEDORES[p][1] if p else "?")
    return f"modelo {modelo}"


def verificar_chave() -> str | None:
    escolhido = os.getenv("ORIENTADOR_PROVEDOR", "").strip().lower()
    if escolhido and escolhido not in PROVEDORES:
        return f"ORIENTADOR_PROVEDOR inválido: {escolhido}. Use: {', '.join(PROVEDORES)}."
    p = provedor_ativo()
    if p is None:
        return "Nenhuma chave encontrada no .env. Preencha OPENAI_API_KEY, GOOGLE_API_KEY ou ANTHROPIC_API_KEY."
    if not _tem_chave(p):
        return f"Provedor {p} escolhido, mas {' / '.join(PROVEDORES[p][0])} está vazia no .env."
    return None
