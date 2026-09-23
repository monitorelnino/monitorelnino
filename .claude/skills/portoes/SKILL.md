---
name: portoes
description: Roda os portões locais do projeto na ordem canônica, derivada de portoes.yml, parando no primeiro vermelho. Use antes de todo push e PR. Aceita `paginas`, `dados` ou `tudo`.
disable-model-invocation: false
---

# Portões locais

Roda `python3 scripts/portoes_locais.py $ARGUMENTS` (padrão: `tudo`).

## Por que passar por aqui, e não rodar os portões à mão

A lista de portões **não vive num documento** — vive em `.github/workflows/portoes.yml`, que
é o único lugar que reprova de verdade. O script deriva dela. Rodar um subconjunto escolhido
a olho foi o que custou um ciclo de CI em 23/09/2026: `verificar_seguranca.js` ficou de fora
e reprovou no CI por uma Action sem SHA fixado.

Hoje o workflow roda **46 comandos**, contra 19 listados no CLAUDE.md e 19 numerados no
PROTOCOLO §3.3. Essas listas descrevem o conjunto; não o definem.

## Grupos

| argumento | o que roda |
|---|---|
| `paginas` | os que rodam sempre no CI (estrutura, runtime, acessibilidade, segurança, legendas…) |
| `dados`   | os condicionados a `dado_mudou` (consistência, índice, evidências, derivados, autotestes dos coletores) |
| `tudo`    | os dois, na ordem do workflow — o padrão |

Rode `dados` sempre que tocar `data/`, um `*.py` de coleta ou dependências. Na dúvida, `tudo`.

## Leitura da saída

Uma linha por portão, com o veredito e o tempo. Só o que reprova mostra saída completa, e o
script para ali — portão vermelho invalida o que vem depois.

`--listar` mostra a lista sem rodar. `--verboso` mostra tudo (raro; custa contexto).

## Depois

Verde não é licença para publicar: o portão 12 exige árvore limpa, então confira
`git status` antes do push. Se o 12 reprovar, use `/p12`.
