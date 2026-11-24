"""Roda as mesmas perguntas várias vezes no agente e mede o quanto o resultado varia.

    python scripts/verificar_variacao.py --fase 2            # 10 execuções por pergunta
    python scripts/verificar_variacao.py --fase 1 --vezes 5

Cada execução usa uma conversa nova (sem histórico). O relatório separa:
  - o que as ferramentas devolvem (Python): deve ser idêntico entre execuções;
  - o que vem do LLM (quais ferramentas chamar, o texto): pode variar;
  - checagens automáticas de erros já observados neste projeto.
O resultado vai para docs/verificacoes/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

MARCADORES_LISTA = ("-", "*", "•")


def _sem_contexto(r, ferramentas):
    return "contexto" not in r.lower(), "não menciona 'contexto'"


def _em_lista(r, ferramentas):
    return any(l.strip().startswith(MARCADORES_LISTA) for l in r.splitlines()), "veio em lista"


def _em_texto(r, ferramentas):
    return not any(l.strip().startswith(MARCADORES_LISTA) for l in r.splitlines()), "veio em texto corrido"


def _cita(*termos):
    def checar(r, ferramentas):
        return all(t.lower() in r.lower() for t in termos), f"cita {', '.join(termos)}"
    return checar


def _cita_um_de(*termos):
    def checar(r, ferramentas):
        return any(t.lower() in r.lower() for t in termos), f"cita {' ou '.join(termos)}"
    return checar


def _empate(r, ferramentas):
    """Empate pode vir dito de várias formas; o erro é apontar um vencedor único."""
    formas = ("empat", "ambas", "ambos", "mesma pontuação", "mesmo score", "igual")
    return any(f in r.lower() for f in formas), "reconhece o empate"


def _usou(fase1: str | None, fase2: str):
    """Confere se o agente chamou a ferramenta certa (o nome muda entre as fases)."""
    def checar(r, ferramentas, fase="2"):
        esperada = fase2 if fase == "2" else fase1
        if esperada is None:
            return False, "existe ferramenta para isso (fase 1 não tem)"
        return esperada in ferramentas, f"usou {esperada}"
    checar.por_fase = True
    return checar


CASOS = [
    {
        "pergunta": "Quais os dados da uni comp?",
        "checagens": [_usou("dados_de_universidade", "dados_universidade"), _sem_contexto, _em_texto,
                      _cita_um_de("UNICAMP", "Universidade Estadual de Campinas")],
    },
    {
        "pergunta": "Compare a Ana com a Bianca",
        "checagens": [_usou(None, "comparar_estudantes"), _sem_contexto, _em_texto],
    },
    {
        "pergunta": "Pode listar as diferenças entre a Bianca e o Gabriel?",
        "checagens": [_usou(None, "comparar_estudantes"), _sem_contexto, _em_lista,
                      _empate],  # matemática 9.5 x 9.5
    },
    {
        "pergunta": "Qual faculdade combina mais com o Gabriel?",
        "checagens": [_usou(None, "ranquear_universidades"), _sem_contexto,
                      _cita("USP", "ITA"), _empate],  # USP e ITA com 100
    },
    {
        "pergunta": "Como funciona o ingresso no ITA?",
        "checagens": [_usou(None, "consultar_guias_admissao"), _sem_contexto, _cita("vestibular")],
    },
]


class CotaEsgotada(Exception):
    """A cota do provedor acabou (ex.: limite diário): não adianta tentar de novo."""


def _invocar(app, pergunta: str, tentativas: int = 3):
    for tentativa in range(tentativas):
        try:
            return app.invoke(
                {"messages": [("user", pergunta)]},
                {"configurable": {"thread_id": str(uuid.uuid4())}},
            )
        except Exception as erro:  # 429/503: espera e tenta de novo
            if "quota" in str(erro).lower():
                raise CotaEsgotada(str(erro).splitlines()[0][:200]) from erro
            temporario = any(c in str(erro) for c in ("429", "503", "RESOURCE_EXHAUSTED", "UNAVAILABLE"))
            if not temporario or tentativa == tentativas - 1:
                raise
            time.sleep(15 * (tentativa + 1))


def executar(app, caso: dict, fase: str) -> dict:
    estado = _invocar(app, caso["pergunta"])
    mensagens = estado["messages"]
    resposta = mensagens[-1].text
    chamadas = [c["name"] for m in mensagens for c in (getattr(m, "tool_calls", None) or [])]
    resultados = sorted((m.name, str(m.content)) for m in mensagens if m.type == "tool")
    assinatura = hashlib.sha1(json.dumps(resultados, ensure_ascii=False).encode()).hexdigest()[:8]
    checagens = []
    for c in caso["checagens"]:
        checagens.append(c(resposta, chamadas, fase) if getattr(c, "por_fase", False) else c(resposta, chamadas))
    return {"ferramentas": chamadas, "assinatura": assinatura, "resposta": resposta, "checagens": checagens}


def verificar(app, vezes: int, fase: str = "2", casos=CASOS, pausa: float = 0) -> list[dict]:
    resultados = []
    for caso in casos:
        execucoes = []
        for i in range(vezes):
            print(f"  {caso['pergunta']}  [{i + 1}/{vezes}]", flush=True)
            try:
                execucoes.append(executar(app, caso, fase))
            except CotaEsgotada as erro:
                print(f"\nCota do provedor esgotada; parando aqui.\n  {erro}")
                execucoes.append({"erro": f"cota esgotada: {erro}"})
                resultados.append({"caso": caso, "execucoes": execucoes})
                return resultados
            except Exception as erro:
                execucoes.append({"erro": f"{type(erro).__name__}: {str(erro).splitlines()[0][:200]}"})
            time.sleep(pausa)
        resultados.append({"caso": caso, "execucoes": execucoes})
    return resultados


def relatorio(resultados: list[dict], vezes: int, fase: str, descricao: str) -> str:
    linhas = [
        f"# Verificação de variação — fase {fase} — {datetime.now():%Y-%m-%d %H:%M}",
        "",
        f"- {descricao}",
        f"- {vezes} execuções por pergunta, cada uma numa conversa nova",
        "",
        "Mesma pergunta, mesmo código, mesmos dados. A assinatura é um hash do que as ferramentas "
        "(Python) devolveram; o resto — quais ferramentas chamar e o texto — é decisão do LLM, e é "
        "aí que os erros aparecem.",
        "",
        "## Resumo",
        "",
        "| Pergunta | Checagens OK | Caminhos de ferramentas | Respostas diferentes | Assinaturas |",
        "|---|---|---|---|---|",
    ]
    total_ok = total = total_erros = 0
    for r in resultados:
        ok_exec = [e for e in r["execucoes"] if "erro" not in e]
        checks = [c for e in ok_exec for c in e["checagens"]]
        passou = sum(1 for ok, _ in checks if ok)
        erros = len(r["execucoes"]) - len(ok_exec)
        total_ok += passou
        total += len(checks)
        total_erros += erros
        caminhos = len({" → ".join(e["ferramentas"]) for e in ok_exec})
        linhas.append(
            f"| {r['caso']['pergunta']} | {passou}/{len(checks)}"
            + (f" ({erros} erro de API)" if erros else "")
            + f" | {caminhos} | {len({e['resposta'] for e in ok_exec})} de {len(ok_exec)}"
            + f" | {len({e['assinatura'] for e in ok_exec})} |"
        )
    linhas += [
        "",
        f"**Total: {total_ok}/{total} checagens OK"
        + (f" · {total_erros} execuções perdidas por erro de API (fora da conta).**" if total_erros else ".**"),
        "",
        "*Caminhos de ferramentas*: quantas sequências diferentes de chamadas o agente fez. "
        "*Assinaturas*: quantos resultados diferentes as ferramentas devolveram; mais de 1 significa "
        "que o agente chamou ferramentas diferentes ou com argumentos diferentes.",
        "",
    ]
    for r in resultados:
        linhas += ["---", "", f"## {r['caso']['pergunta']}", ""]
        for i, e in enumerate(r["execucoes"], 1):
            if "erro" in e:
                linhas += [f"### Execução {i} — erro", "", f"`{e['erro']}`", ""]
                continue
            falhas = [nome for ok, nome in e["checagens"] if not ok]
            status = "OK" if not falhas else "FALHOU: " + "; ".join(falhas)
            caminho = " → ".join(e["ferramentas"]) or "nenhuma ferramenta"
            linhas += [f"### Execução {i} — {status}", "", f"ferramentas: `{caminho}` · assinatura `{e['assinatura']}`", "", e["resposta"], ""]
    return "\n".join(linhas)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--fase", choices=["1", "2"], default="2")
    parser.add_argument("--vezes", type=int, default=10)
    parser.add_argument("--pausa", type=float, default=0, help="segundos entre execuções (limite de requisições)")
    args = parser.parse_args()

    from langgraph.checkpoint.memory import InMemorySaver

    from orientador.config import descricao, verificar_chave

    if erro := verificar_chave():
        print(erro, file=sys.stderr)
        return 1

    if args.fase == "1":
        from fases.fase1_curso.agente import construir_agente
    else:
        from orientador.agente import construir_agente
    app = construir_agente(checkpointer=InMemorySaver())
    print(f"fase {args.fase} · {descricao()} · {args.vezes} execuções por pergunta")
    resultados = verificar(app, args.vezes, args.fase, pausa=args.pausa)

    destino = RAIZ / "docs" / "verificacoes" / f"fase{args.fase}_{datetime.now():%Y-%m-%d_%H%M}.md"
    destino.parent.mkdir(parents=True, exist_ok=True)
    texto = relatorio(resultados, args.vezes, args.fase, descricao())
    destino.write_text(texto, encoding="utf-8")
    total = next(l for l in texto.splitlines() if l.startswith("**Total"))
    print(f"\n{total.strip('*')}\nRelatório salvo em {destino.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
