# `caveman` neste repositório — procedência e subordinação

Leitura obrigatória junto com o `SKILL.md` ao lado.

## Procedência

| item | valor |
|---|---|
| origem | [`JuliusBrussee/caveman`](https://github.com/JuliusBrussee/caveman) |
| versão fixada | `v2.7.0` |
| arquivo copiado | `plugins/caveman/skills/caveman/SKILL.md` |
| sha256 do original | `0bf09a0a9a017d00…` (16 primeiros dígitos) |
| instalado em | 27/09/2026, a pedido da editoria |
| escopo | **do projeto**, não global — o que o `INSTALL.md` de lá chama de instalação sem `-g` |

**O que NÃO foi instalado:** nenhum binário, nenhum hook, nenhum proxy, nenhuma telemetria,
nenhuma alteração global. Só o arquivo de texto. O `curl … | bash` do projeto de origem instala
hooks, presets de subagente, badge de statusline e detecta todos os agentes da máquina; nada
disso entrou. O proxy — a parte que comprime o que o agente **lê** — foi deliberadamente deixado
de fora (ver "O proxy" abaixo).

O corpo do `SKILL.md` é **verbatim**. A única adição é o aviso de três linhas logo depois do
frontmatter, apontando para este arquivo. Ao atualizar de upstream: conferir o sha256, recopiar o
corpo, reinserir o aviso.

## Ordem de precedência

```
METODOLOGIA.md                        prova — o que pode ser afirmado
AI_EDITORIAL_NARRATIVE_GOVERNANCE.md  narrativa — por que, onde e como se diz
AI_VISUAL_ART_DIRECTION.md            estética — com que forma aparece
CLAUDE.md                             modo de trabalho
caveman                               registro de fala, e nada mais
```

Esta skill governa **como a frase é dita na conversa com a editoria**. Ela não governa o que pode
ser afirmado, nem o que entra no site, nem o que é verificado antes de ser dito.

## As colisões com o `CLAUDE.md`, nomeadas

Onde houver colisão, **vence o `CLAUDE.md`**.

### 1. Plano, suposição e resumo permanecem

A seção *Tool calls* da skill manda: *"No preamble, plan, or progress note before or between
calls."*

O `CLAUDE.md` exige o contrário, em três pontos distintos:

- "**Declarar a suposição antes de implementar**, e perguntar quando houver dúvida real."
- "Transformar a tarefa em critério verificável e iterar até verificar: para tarefa de vários
  passos, **declarar o plano no formato `passo → verificação`**."
- "Ao concluir: **resumo curto** — o que foi feito, mudanças importantes, verificações realizadas,
  o que ficou sem solução."

Os três **permanecem**. A compressão se aplica à prosa deles, nunca à existência deles. Plano de
uma linha é plano; plano ausente é descumprimento.

### 2. Cortar hedging não autoriza afirmar o não medido

A skill manda derrubar *hedging*. O `CLAUDE.md` manda "verificar cada informação antes de
apresentá-la como fato" e que "suposição não verificada nunca é apresentada como dado".

Incerteza **medida** se declara — curta, mas inteira. "Não medi" é fato, não hedging. Em
27/09/2026 esta distinção custou duas correções públicas na mesma noite: uma afirmação de que o
`KeyError` derrubava a rodada (derrubava três passos), e uma de que a coleta "terminou por si"
(foi truncada no teto, e o `continue-on-error` mascarou como sucesso). Nos dois casos o erro foi
afirmar sem medir, e comprimir não teria ajudado — teria escondido.

### 3. Tabela de medição é substância

A skill proíbe *"decorative tables"*. Tabela que carrega medição — tempo medido, contagem de
fila, resultado de portão, soma de tetos — **é a prova**, não enfeite, e fica.

### 4. Texto público do site não é tocado

Título, legenda, nota, fonte, tooltip, cartão e prosa de página seguem a
`AI_EDITORIAL_NARRATIVE_GOVERNANCE.md`, e o portão 19 (`verificar_legendas.js`) reprova quem
desviar. A própria skill concorda: a seção *Boundaries* manda **prosa normal** em commit,
documentação, texto de PR, comentário de código e arquivo de memória.

## O que a skill traz e que serve a este projeto

- **Auto-Clarity**: ela abandona o modo comprimido em aviso de segurança, em confirmação de ação
  irreversível, em sequência de vários passos cuja ordem possa ser lida errado, e quando a própria
  compressão criaria ambiguidade.
- **Nunca descarta** `não`, `nunca`, `no`, `só`, `exceto` — inverter sentido é pior que qualquer
  token economizado.
- **Número, unidade, código, nome de API, comando e mensagem de erro exatos**, sempre.
- **Preserva o idioma dominante** — *"compress the style, not the language"*. Foi a condição que a
  editoria pôs ao instalar: respostas em português do Brasil, mais curtas.
- **Proíbe abreviação inventada** (`cfg`, `impl`, `req`) e seta (`→`), porque medidamente não
  economizam token e custam leitura.

## O proxy, deixado de fora

O projeto de origem tem três partes: a **skill** (comprime o que o agente diz), o **proxy**
(comprime o que o agente lê — logs, saída de teste, JSON, diffs) e o **middleware** (para código
próprio). Só a skill entrou.

O proxy resolve um problema real deste repositório: `data/log_buscas.json` tem 20,7 MB em uma
linha, `data/fontes_consultadas.json` tem 12 MB, e a suíte de portões despeja centenas de linhas.

Mas ele cria, na leitura, exatamente a classe de risco que o §§246 a 248 consertaram na gravação:
**conteúdo encurtado que se parece com conteúdo inteiro**. O `METODOLOGIA.md` exige que recusa
servida com `200` seja tratada como recusa, e `coletores_base.detectar_muro_de_robo` existe para
pegar muro de robô que parece conteúdo. Um resumo da resposta de uma fonte apagaria os sinais que
essa detecção usa — e prova falsa entraria no índice.

Se a editoria quiser o proxy, o caminho defensável é: **nunca na leitura de evidência**, só em log
e saída de teste, e com a leitura do original obrigatória antes de qualquer afirmação pública.
Decisão dela, não daqui.

## Desligar

`stop caveman` ou `normal mode`. Intensidade: `/caveman lite|full|ultra`.
