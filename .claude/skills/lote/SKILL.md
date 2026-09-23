---
name: lote
description: Conduz uma mudança do ramo ao merge no padrão do projeto — ramo, portões, commit, push, PR, espera do CI, merge. Use para levar um trabalho pronto até a main.
disable-model-invocation: true
---

# Levar um lote até a `main`

Fluxo do PROTOCOLO §3.1, com o que a prática acrescentou.

## 1. Partir da `main` atual

```bash
git fetch origin main && git checkout -b edicao/AAAA-MM-DD-tema origin/main
```

Nome sem prefixo `claude/`. Data no nome, tema em palavras.

## 2. Trabalhar, depois `/portoes tudo`

Nada sobe com portão vermelho. Se o 12 reprovar, `/p12`. Se suspeitar que a falha não é sua,
`/e-da-main`.

## 3. Commit

A mensagem do projeto tem forma: `§NNN` quando há seção, o **motivo**, o **achado** quando
houve um, e **o que não foi feito**. Commit que só descreve o diff não serve — o diff já
está ali. O que não está é por que a mudança é assim, e o que se descobriu no caminho.

Achado negativo vale tanto quanto positivo: "rodei duas vezes e o resultado é inconclusivo,
não negativo" é informação, e some se não for escrita.

## 4. Push e PR

```bash
git push -u origin edicao/AAAA-MM-DD-tema
```

Confira que chegou (`git fetch` + `git merge-base --is-ancestor HEAD origin/<ramo>`). No
corpo do PR, resuma as entradas do CHANGELOG e **declare o que ficou pendente e por quê** —
o corpo vira registro permanente, então mantenha-o verdadeiro até o merge.

## 5. Esperar o CI

O `portoes.yml` dispara em `pull_request` com base `main`. Reapontar a base de um PR **não**
dispara CI (só `opened`/`synchronize`/`reopened`); nesse caso dispare à mão pelo
`workflow_dispatch` do próprio `portoes.yml`.

## 6. Merge

Com os portões e a Action verdes, Claude mescla (PROTOCOLO §3.1/§5). O domínio segue com a
editoria — republicar, lançar ou reverter exige a palavra dela.

**Merge commit, nunca squash**, salvo pedido explícito.
