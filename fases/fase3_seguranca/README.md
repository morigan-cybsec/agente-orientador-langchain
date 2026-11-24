# Fase 3 — segurança (próximo repositório)

**Próximo repositório:** [link em breve](#)

Esta fase não está neste repo. Lá, o mesmo projeto ganha:

- **ferramentas destrutivas** (excluir aluno, alterar nota, apagar histórico);
- **cargos** com permissões e limites do que cada usuário pode consultar ou alterar;
- a demonstração em duas etapas: primeiro um usuário **quebrando o prompt** e fazendo o agente acionar essas ferramentas; depois a versão corrigida, com proteção de prompt e **confirmação humana** (human-in-the-loop), em que isso não acontece tão fácil;
- o **orquestrador em Python** ([`orientador/grafo.py`](../../orientador/grafo.py), já presente aqui): em vez de o LLM escolher a próxima ferramenta, o caminho é decidido por código, e só um caminho fixo e com aprovação humana leva a uma ação irreversível.

Para ver o orquestrador funcionando já nesta versão:

```bash
python -m orientador --modo grafo
python -m orientador --modo grafo --diagrama
```
