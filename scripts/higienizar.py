"""Remove caminhos locais e o nome de usuário dos registros antes de subir para o git.

    python scripts/higienizar.py            # higieniza docs/**/*.md no lugar
    python scripts/higienizar.py --checar   # só lista o que ainda tem dado local (sai com erro se tiver)

Troca a pasta do repositório por <repo>, a pasta do usuário por ~ e o nome de
usuário por <usuario>. registrar_testes.py já grava higienizado.
"""

from __future__ import annotations

import argparse
import getpass
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def _variantes(caminho: Path) -> list[str]:
    texto = str(caminho)
    return sorted({texto, texto.replace("\\", "/"), texto.replace("/", "\\")}, key=len, reverse=True)


def higienizar(texto: str, raiz: Path = RAIZ, home: Path = Path.home(), usuario: str | None = None) -> str:
    for variante in _variantes(raiz):
        texto = texto.replace(variante, "<repo>")
    for variante in _variantes(home):
        texto = texto.replace(variante, "~")
    usuario = usuario or getpass.getuser()
    if usuario and len(usuario) > 2:
        texto = re.sub(rf"(?i)(?<![\w]){re.escape(usuario)}(?![\w])", "<usuario>", texto)
    return texto


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checar", action="store_true")
    args = parser.parse_args()
    pendentes = []
    for arq in sorted((RAIZ / "docs").rglob("*.md")):
        original = arq.read_text(encoding="utf-8")
        limpo = higienizar(original)
        if limpo != original:
            pendentes.append(arq.relative_to(RAIZ))
            if not args.checar:
                arq.write_text(limpo, encoding="utf-8")
    acao = "com dados locais" if args.checar else "higienizados"
    print(f"{len(pendentes)} arquivo(s) {acao}" + "".join(f"\n  {p}" for p in pendentes))
    return 1 if (args.checar and pendentes) else 0


if __name__ == "__main__":
    sys.exit(main())
