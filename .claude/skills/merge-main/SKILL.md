---
name: merge-main
description: Traz a main para o ramo, resolvendo conflito de log append-only pela base comum, regenera derivados e roda os portões de dado. Use quando a main avançar durante o trabalho.
disable-model-invocation: false
---

# Mesclar a `main` no ramo

A `main` avança sozinha várias vezes por dia (cadência da busca web a cada 2h). Mesclar é
rotina; o perigo está num detalhe.

```bash
git fetch origin main && git merge origin/main --no-edit
```

## A regra que evita perda silenciosa de dado

`data/log_buscas.json` e `data/historico_mudancas.json` **só crescem**. Quando os dois lados
acrescentam, o merge conflita — e a resolução intuitiva está errada.

**Nunca deduplique por conteúdo.** Execuções idênticas no log v2 são tentativas reais
distintas e contam. Em 23/09/2026 uma união por conteúdo produziu um log **menor** que cada
um dos lados (22.089 contra 24.899 e 25.210): quase 3.000 execuções apagadas sem aviso.

O certo é unir pela **base comum**:

```python
base = merge-base de HEAD e MERGE_HEAD
uniao = A[:n] + A[n:] + B[n:]     # n = tamanho da lista na base
```

Confira sempre que o total final é **maior ou igual** a cada lado. Se for menor, refaça.

## Derivados e manifesto

`dados-abertos/*`, `feeds/*` e `docs/MANIFEST_SHA256.txt` são derivados: resolva com a versão
da `main` e regenere pela cadeia canônica; não tente casar linha a linha.

## Depois

`/portoes dados` e, se o 12 reclamar, `/p12`.
