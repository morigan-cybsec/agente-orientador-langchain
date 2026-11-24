# Fase 1 — o agente do curso

O agente como ensinado no curso da Alura, só atualizado para LangChain 1.x (`create_agent` no lugar de `AgentExecutor`).

```bash
python -m orientador --fase 1
```

## Ferramentas

| Ferramenta | O que faz |
|---|---|
| `dados_de_estudante` | busca a ficha por **igualdade exata** do nome em minúsculo |
| `dados_de_universidade` | busca por igualdade exata da sigla em minúsculo |
| `todas_universidades` | devolve o CSV inteiro |
| `perfil_academico` | o LLM formata a ficha que o agente buscou antes |

## O que dá errado (e por quê)

- **"uni camp" não acha a UNICAMP**: a busca é exata, sem normalização.
- **Comparar e recomendar "de cabeça"**: não existe ferramenta de comparação nem de ranking; o LLM lê as fichas e decide sozinho quem é melhor, e pode errar a conta ou ignorar um empate.
- **Sem regras de domínio**: o modelo não sabe que quem usa é a equipe de orientação, nem que os alunos ainda não estão em universidade nenhuma.
- **Sem guias de admissão**: perguntado sobre ingresso, o modelo responde com o que lembra do treinamento, sem fonte.

O relatório de verificação desta fase fica em [`docs/verificacoes/`](../../docs/verificacoes/) (`fase1_*.md`).

Próxima: [fase 2](../fase2_ferramentas/).
