---
name: design
description: Laço rápido para mudança de fonte, cor, forma de botão ou texto público — captura em 375px e desktop, e só os portões do assunto tocado. Use para editar tokens.css, base.css ou texto de página. Não substitui a suíte antes do PR.
disable-model-invocation: false
---

# Laço de design

Para o que muda **aparência ou texto** e não muda dado: fonte, cor, espaçamento, forma de botão,
título, legenda, nota. Esse tipo de mudança toca `assets/tokens.css`, `assets/base.css` e o HTML da
página — **nada em `data/`, nada na cadeia de derivados**.

## A sequência

```bash
# 1. servidor local (uma vez por sessão; as páginas buscam data/*.json ao vivo)
python3 -m http.server 8788 --bind 127.0.0.1

# 2. edite assets/tokens.css ou assets/base.css

# 3. veja: captura em 375 px e 1280 px, mais a medição de rolagem, texto miúdo e alvo de toque
node scripts/auditar_ux.js index            # uma página
node scripts/auditar_ux.js                  # as doze

# 4. enquanto itera (5 s)
python3 scripts/portoes_locais.py cor --rapido

# 5. antes de mostrar à editoria
python3 scripts/portoes_locais.py cor       # 2min23   (ou `texto`, 2min08)

# 6. antes do PR — sempre
python3 scripts/portoes_locais.py tudo
bash scripts/verificar_derivados.sh
```

As capturas saem em `previa/`, que é ignorada pelo git: são para olhar, não para guardar.

## Os tempos, medidos em 26/09/2026

| comando | portões | tempo |
|---|---|---|
| `cor --rapido` / `texto --rapido` | 6 | **5 s** |
| `cor` | 16 | 2min23 |
| `texto` | 17 | 2min08 |
| `paginas` | 23 | 4min25 |
| `tudo` | 69 | a suíte inteira |

## De onde vem o assunto de cada portão

Do próprio `.github/workflows/portoes.yml`, numa linha `# assunto: ...` acima do comando — a mesma
disciplina da trilha, que é derivada da condição do CI. **Não é lista escolhida a olho**: o
`CLAUDE.md` registra que subconjunto escolhido assim custou um ciclo de CI em 23/09/2026, e
`scripts/validar_workflows.py` reprova portão de página que não declare assunto, para que portão
novo não fique fora dos perfis em silêncio.

Portão novo de página → declare `# assunto: cor`, `texto` ou os dois, e `rapido` se responder em
até 2 s.

## O que o laço rápido NÃO é

Ele não libera nada. `cor` e `texto` rodam só o que o seu tipo de mudança toca; o que a mudança
**não** deveria tocar continua sem ser conferido até a suíte inteira rodar. Nada sobe com portão
vermelho, e o perfil parcial imprime esse lembrete ao terminar.

## As regras que continuam valendo

- **`AI_VISUAL_ART_DIRECTION.md` §25 é vinculante:** não se maquia componente por componente —
  observa-se o site inteiro, reconstrói-se a direção, e só então se propaga. Por isso
  `auditar_ux.js` sem argumento roda as doze páginas: o laço rápido serve para iterar, não para
  retocar um botão isolado e parar.
- Hexadecimal só em `assets/tokens.css` e `assets/mapas.js`.
- Escala tipográfica fixa: 12 · 14 · 16 · 18 · 22 · 28 · 36 · 48 px.
- Elementos equivalentes usam o mesmo componente, classe e token; nada de ajuste manual de pixel.
- O checklist da `marca-pessoal` vale antes de entregar — contraste AA, 375 px sem rolagem
  horizontal, Fraunces 300 no display, nunca bold.

## Quando isto não serve

Mudança que mexe em número, série ou fonte de dado não é design: vai pela rotina normal
(`portoes_locais.py dados` ou `tudo`, mais a regeneração de derivados). O sinal é simples — se o
diff toca `data/`, saia daqui.

## Nota sobre o axe-core

`auditar_ux.js` usa `@axe-core/playwright` **se ele estiver instalado**, e diz no relatório quando
não está. Não é dependência declarada do projeto. Para ligar: `npm i -D @axe-core/playwright`. O
contraste, que é o que mais importa numa troca de cor, já é conferido por
`scripts/verificar_acessibilidade.js`, que está no perfil `cor --rapido`.
