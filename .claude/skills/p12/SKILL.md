---
name: p12
description: Resolve o portão 12 (derivados obsoletos) — regenera a cadeia canônica, comita os derivados e o manifesto, e reconfere. Use quando verificar_derivados.sh reprovar.
disable-model-invocation: false
---

# Portão 12 — derivado obsoleto

Sequência fixa. Ela reprovou **cinco vezes numa só sessão** (23/09/2026) e é sempre a mesma;
está aqui para não ser redescoberta toda vez.

```bash
bash scripts/verificar_derivados.sh          # 1. ver o que está obsoleto
git add -A                                   # 2. os derivados regenerados + o manifesto
git commit -m "..."                          # 3. mensagem no padrão do projeto
bash scripts/verificar_derivados.sh          # 4. tem de fechar verde
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
