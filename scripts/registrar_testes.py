"""Roda o pytest e salva o resultado em docs/testes/.

    python scripts/registrar_testes.py
    python scripts/registrar_testes.py --integracao
"""

from __future__ import annotations

import argparse
import os
import platform
import re
import subprocess
import sys
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PACOTES = ["langchain", "langchain-core", "langgraph", "langchain-openai", "langchain-text-splitters", "pytest"]


def _versao(pacote: str) -> str:
    try:
        return version(pacote)
    except PackageNotFoundError:
        return "não instalado"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--integracao", action="store_true")
    args = parser.parse_args()

    sys.path.insert(0, str(RAIZ))
    from orientador.config import PROVEDORES, descricao, provedor_ativo  # carrega o .env

    suite = "integracao" if args.integracao else "offline"
    cmd = [sys.executable, "-m", "pytest", "-v", "-rs", "-p", "no:cacheprovider"]
    if args.integracao:
        cmd += ["-m", "integracao"]

    inicio = datetime.now()
    proc = subprocess.run(
        cmd, cwd=RAIZ, capture_output=True, text=True, encoding="utf-8", errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    duracao = (datetime.now() - inicio).total_seconds()
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from higienizar import higienizar

    saida = higienizar(proc.stdout + proc.stderr)
    resumo = next((l.strip("= ") for l in reversed(saida.splitlines()) if re.search(r"passed|failed|skipped|error", l)), "?")
    status = "✅ passou" if proc.returncode == 0 else "❌ falhou"

    destino = RAIZ / "docs" / "testes" / f"{inicio:%Y-%m-%d_%H%M}_{suite}.md"
    destino.parent.mkdir(parents=True, exist_ok=True)
    linhas_env = [
        f"- SO: {platform.system()} {platform.release()}",
        f"- Python: {platform.python_version()}",
        *(f"- {p}: {_versao(p)}" for p in PACOTES),
    ]
    if args.integracao:
        linhas_env += [
            f"- Provedor: {provedor_ativo()} ({descricao()})",
            f"- Embeddings: {os.getenv('ORIENTADOR_EMBEDDINGS') or (PROVEDORES[provedor_ativo()][2] if provedor_ativo() else '-') or 'busca por palavras'}",
        ]
    destino.write_text(
        "\n".join(
            [
                f"# Registro de testes — {suite}",
                "",
                f"- Data: {inicio:%Y-%m-%d %H:%M}",
                f"- Resultado: {status} — {resumo}",
                f"- Duração: {duracao:.1f}s",
                *linhas_env,
                "",
                "## Saída do pytest",
                "",
                "```text",
                saida.strip(),
                "```",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"{status} — {resumo}\nRegistro salvo em {destino.relative_to(RAIZ)}")
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
