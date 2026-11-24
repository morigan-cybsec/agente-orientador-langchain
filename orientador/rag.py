"""RAG: split -> embeddings -> vector store -> busca, com filtro por metadata."""

from __future__ import annotations

from pathlib import Path

from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter

from orientador.config import DIR_CONVERSAS, DIR_DADOS
from orientador.dados import normalizar


def carregar_guias(diretorio: Path = DIR_DADOS / "guias") -> list[Document]:
    return [
        Document(page_content=arq.read_text(encoding="utf-8"), metadata={"universidade": arq.stem})
        for arq in sorted(Path(diretorio).glob("*.md"))
    ]


def carregar_conversas(diretorio: Path = DIR_CONVERSAS, ignorar: Path | None = None) -> list[Document]:
    """Conversas anteriores (só os .md normais; os _debug.md ficam de fora)."""
    return [
        Document(page_content=arq.read_text(encoding="utf-8"), metadata={"conversa": arq.stem})
        for arq in sorted(Path(diretorio).glob("*.md"))
        if not arq.stem.endswith("_debug") and arq != ignorar
    ]


class IndiceGuias:
    def __init__(self, embeddings, documentos: list[Document] | None = None):
        pedacos = RecursiveCharacterTextSplitter(
            chunk_size=600, chunk_overlap=80
        ).split_documents(documentos if documentos is not None else carregar_guias())
        self.total_pedacos = len(pedacos)
        self._pedacos = pedacos
        self._store = (
            InMemoryVectorStore.from_documents(pedacos, embeddings) if embeddings and pedacos else None
        )

    def buscar(
        self, pergunta: str, universidades: list[str] | None = None, k: int = 3
    ) -> list[Document]:
        alvo = set(universidades) if universidades else None
        filtro = (lambda d: d.metadata.get("universidade") in alvo) if alvo else None
        if self._store is not None:
            return self._store.similarity_search(pergunta, k=k, filter=filtro)
        return self._buscar_por_palavras(pergunta, filtro, k)

    def _buscar_por_palavras(self, pergunta, filtro, k):
        # sem embeddings (ex.: só chave da Anthropic): conta palavras da pergunta em cada pedaço
        termos = {normalizar(t) for t in pergunta.split() if len(normalizar(t)) > 3}
        candidatos = [d for d in self._pedacos if filtro is None or filtro(d)]
        pontuar = lambda d: sum(normalizar(t) in termos for t in d.page_content.split())
        return sorted(candidatos, key=pontuar, reverse=True)[:k]


def construir_indice() -> IndiceGuias:
    from orientador.config import carregar_embeddings

    return IndiceGuias(carregar_embeddings())


def construir_indice_historico() -> IndiceGuias:
    from orientador.config import carregar_embeddings

    return IndiceGuias(carregar_embeddings(), carregar_conversas())
