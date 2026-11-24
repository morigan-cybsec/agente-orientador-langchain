# Fase 2 — ferramentas determinísticas e regras

O mesmo agente, mas com uma regra simples: **o LLM não calcula nem inventa dados**. Tudo que pode ser calculado vira ferramenta em Python; o LLM decide qual ferramenta chamar e redige a resposta.

```bash
python -m orientador          # fase 2 é o padrão
```

O código desta fase é o pacote principal, em [`orientador/`](../../orientador/).

## O que mudou em relação à fase 1

| Problema na fase 1 | Correção na fase 2 |
|---|---|
| "uni camp" não acha a UNICAMP | busca tolerante (`dados.py`): normaliza acento, caixa e espaço, e usa `difflib` para erro de digitação |
| LLM compara "de cabeça" | `comparar_estudantes` / `comparar_universidades`: valores, líder, diferença e o que têm em comum, em Python |
| LLM recomenda "de cabeça" | `ranquear_universidades`: score 0–100 por regra fixa (desempenho, área, idioma, preferência) |
| ingresso respondido sem fonte | `consultar_guias_admissao`: RAG nos guias de cada universidade |
| modelo não sabe quem é o usuário | regras de domínio no prompt: usuário é da equipe, alunos ainda no ensino médio |
| empate virava vencedor, "contexto" na resposta, lista quando pediam texto | regras de resposta no prompt, medidas pelo script de verificação |
| nada fica registrado | `conversas/` com `.md` normal e `_debug.md`, e `consultar_historico` para lembrar conversas anteriores |

## O que ainda depende do LLM

- **qual ferramenta chamar** (e com quais argumentos);
- **o texto final**.

É exatamente o que o [script de verificação](../../scripts/verificar_variacao.py) mede: quantos caminhos de ferramentas diferentes o agente tomou para a mesma pergunta e quantas respostas diferentes saíram. Relatórios em [`docs/verificacoes/`](../../docs/verificacoes/) (`fase2_*.md`).

## Problema conhecido

Pedido de lista ("Pode listar…") veio em texto corrido em 1 de 10 execuções com `claude-haiku-5-5` e em 6 de 10 com `gemini-3.5-flash-lite`: o formato depende só do prompt (e do modelo). Registrado no README principal e como teste `xfail` em `tests/test_integracao.py`.

Próxima: [fase 3](../fase3_seguranca/).
