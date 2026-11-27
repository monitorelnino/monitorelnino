---
name: p12
description: Resolve o portão 12 (derivados obsoletos) — diz onde ele tolera (PR, cópia de trabalho) e onde reprova (main selada, elo), e o que consertar. Use quando verificar_derivados.sh reprovar.
disable-model-invocation: false
---

# Portão 12 — derivado obsoleto

Desde o handover do selo (25–26/11/2026) o selo (manifesto, `mudancas.html`, `CODEMAP.md`) é do
publicador. No PR e na cópia de trabalho o portão 12 regenera a cadeia e só reprova se um gerador
quebrar: derivado defasado sai como aviso, e não se commita selo no PR. Ele reprova de verdade em
dois lugares: no push da `main` já selada e nos elos da noite, onde derivado velho é defeito do elo.

```bash
bash scripts/verificar_derivados.sh          # regenera; erro = gerador quebrado, conserte-o
python3 scripts/selo_da_main.py --autoteste  # onde se tolera e onde se reprova
```

## O que NÃO fazer

Não edite o derivado à mão para "consertar" o diff — há hook que bloqueia, e com razão: o
arquivo é função dos dados, e o portão 12 desfaria a edição na rodada seguinte.

## Antes de assumir a culpa

Carimbo `gerado_em` obsoleto em `data/municipios_card.json` já deixou a **`main` vermelha**
sozinho, sem nenhum commit de ramo envolvido. Antes de tratar como seu, confira com
`/e-da-main verificar_derivados.sh`. Se já estava vermelho lá, corrija mesmo assim — mas
diga isso no commit, porque muda quem causou o quê.

## Cadeia canônica

`scripts/verificar_derivados.sh` regenera índice → selos → feeds → dados abertos → PDFs →
manifesto, com o relógio fixado no corte, e exige `git diff --exit-code`. O `--idempotencia`
(AUD-04) confere que uma segunda regeneração não altera nada.
