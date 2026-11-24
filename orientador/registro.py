"""Registro das sessões em conversas/: um .md normal e um _debug.md por sessão.

O _debug.md é preenchido por um callback handler (BaseCallbackHandler), que o
LangChain chama a cada prompt enviado e a cada resposta recebida do modelo.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import get_buffer_string


class RegistroDebug(BaseCallbackHandler):
    def __init__(self, caminho: Path):
        self.caminho = caminho

    def _escrever(self, texto: str) -> None:
        with self.caminho.open("a", encoding="utf-8") as f:
            f.write(texto)

    def on_chat_model_start(self, serialized, messages, *, metadata=None, **kwargs):
        no = (metadata or {}).get("langgraph_node", "?")
        prompt = "\n\n".join(get_buffer_string(m) for m in messages)
        self._escrever(f"\n#### LLM chamado no nó `{no}`\n\nPrompt enviado:\n\n```text\n{prompt}\n```\n")

    def on_llm_end(self, response, **kwargs):
        geracao = response.generations[0][0]
        texto = geracao.text
        uso = getattr(getattr(geracao, "message", None), "usage_metadata", None) or {}
        tokens = f"{uso.get('input_tokens', '?')} de entrada, {uso.get('output_tokens', '?')} de saída"
        self._escrever(f"\nResposta bruta ({tokens}):\n\n```text\n{texto}\n```\n")


class Registro:
    def __init__(self, pasta: Path, cabecalho: str):
        pasta.mkdir(parents=True, exist_ok=True)
        nome = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        self.normal = pasta / f"{nome}.md"
        self.debug = pasta / f"{nome}_debug.md"
        self.cabecalho = f"# Conversa {nome}\n\n{cabecalho}\n"
        self.turnos = 0
        self.handler = RegistroDebug(self.debug)

    def _anexar(self, caminho: Path, texto: str) -> None:
        if not caminho.exists():
            caminho.write_text(self.cabecalho, encoding="utf-8")
        with caminho.open("a", encoding="utf-8") as f:
            f.write(texto)

    def inicio_turno(self, pergunta: str) -> None:
        self.turnos += 1
        self._anexar(self.debug, f"\n---\n\n## Turno {self.turnos}: {pergunta}\n")

    def no_executado(self, no: str, saida: dict) -> None:
        dados = json.dumps(saida, ensure_ascii=False, indent=1, default=str)
        self._anexar(self.debug, f"\n### Nó `{no}` (saída)\n\n```json\n{dados}\n```\n")

    def fim_turno(self, pergunta: str, linhas: list[str], resposta: str) -> None:
        processamento = "\n".join(f"· {l}" for l in linhas) or "-"
        texto = (
            f"\n---\n\n## Turno {self.turnos}\n\n**Pergunta:** {pergunta}\n\n"
            f"**Processamento:**\n\n```text\n{processamento}\n```\n\n**Resposta:**\n\n{resposta}\n"
        )
        self._anexar(self.normal, texto)
        self._anexar(self.debug, f"\n### Resposta final\n\n{resposta}\n")
