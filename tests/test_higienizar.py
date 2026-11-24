import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("higienizar", Path("scripts/higienizar.py"))
h = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(h)


def test_remove_caminhos_windows_e_usuario():
    texto = (
        "rootdir: C:\\Users\\morga\\code\\Studies\\orientador-academico\n"
        "python: C:\\Users\\morga\\code\\Studies\\orientador-academico\\.venv\\Scripts\\python.exe\n"
        "cache em C:\\Users\\morga\\AppData\\Local\\x\n"
        "usuário morga rodou"
    )
    limpo = h.higienizar(
        texto,
        raiz=Path("C:\\Users\\morga\\code\\Studies\\orientador-academico"),
        home=Path("C:\\Users\\morga"),
        usuario="morga",
    )
    assert "morga" not in limpo
    assert "rootdir: <repo>" in limpo
    assert "<repo>\\.venv\\Scripts\\python.exe" in limpo
    assert "~\\AppData" in limpo
    assert "usuário <usuario> rodou" in limpo


def test_nao_troca_parte_de_palavra():
    assert h.higienizar("morgana", raiz=Path("/x"), home=Path("/y"), usuario="morga") == "morgana"
