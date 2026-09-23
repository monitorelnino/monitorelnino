---
name: e-da-main
description: Responde se uma falha de portão é do ramo atual ou já existia na main, usando um worktree limpo de origin/main. Use antes de assumir a culpa por um portão vermelho.
disable-model-invocation: false
---

# É meu, ou já estava vermelho na `main`?

Pergunta que apareceu **quatro vezes** numa só sessão (23/09/2026) — e nas quatro a falha já
estava na `main`. Vale sempre perguntar antes de reescrever código que não tem defeito.

```bash
git fetch -q origin main
git worktree add -q /tmp/wt-main origin/main
ln -sfn "$PWD/node_modules" /tmp/wt-main/node_modules   # evita npm ci de novo
(cd /tmp/wt-main && <o portão em questão>)
git worktree remove --force /tmp/wt-main
```

`$ARGUMENTS` é o portão a rodar, por exemplo `bash scripts/verificar_derivados.sh` ou
`python3 verificar_evidencias.py`.

## O que fazer com a resposta

**Já estava vermelho na `main`.** Ainda é para consertar — uma `main` vermelha trava a
publicação de todo mundo. Mas **diga isso no commit e no PR**: muda quem causou o quê, e
evita que a próxima pessoa procure defeito no lugar errado.

**Só no ramo.** É seu. Corrija na origem, não no sintoma.

## Casos reais que isto pegou

- Portão 12 vermelho por carimbo `gerado_em` obsoleto — era da `main`.
- Portão 6 bloqueante com Votuporanga/SP sem `hash_evidencia` — era da `main`, aplicado pela
  rodada automática daquela manhã.
- CI vermelho do PR #351 — era o mesmo portão 12 da `main`, não da sonda que o PR trazia.

## Limpeza

Remova o worktree sempre, inclusive quando o portão reprovar. Worktree esquecido confunde
`git status` na sessão seguinte.
