---
name: regras-do-site
description: As regras que o site do MARÉ já tem, reunidas num lugar, para quem vai tocar página, texto público, figura, mapa, cartão, legenda ou dado exibido. Use SEMPRE antes de criar ou alterar qualquer HTML, CSS, script de página, figura, título, legenda, nota, fonte, tooltip, cartão ou texto que o leitor encontre no site — inclusive numa correção de uma frase, inclusive quando o pedido parecer pequeno. Use também ao escrever ou revisar texto do blog, ao mexer em tipografia, paleta ou componente visual, e ao decidir como um número aparece na página. Esta skill não cria regra nenhuma: ela aponta para os documentos que decidem e resume o que o portão `verificar_conformidade.py` já reprova.
---

# Regras do site do MARÉ

Esta skill é um **índice de primeira ordem**, não uma fonte. Nada aqui é regra nova: tudo vem de
documentos que já existem no repositório, e onde esta página e o documento divergirem, **vence o
documento**. O propósito é economizar a releitura de cinco arquivos para descobrir que a decisão já
estava tomada — e evitar o erro oposto, que é decidir sozinho o que a editoria já decidiu.

Quem reprova de verdade é **`scripts/verificar_conformidade.py`**, portão bloqueante em todo PR que
toque página, estilo, script de página, figura, texto público ou dado exibido. As regras verificáveis
por máquina estão extraídas em **`layout/regras.json`**. Exceção só por `layout/excecoes.json`, com
regra, página, motivo, data e quem decidiu — **exceção sem registro é vermelho**.

## Por onde começar, pela tarefa

| vou mexer em… | leia aqui |
|---|---|
| cartão de número | **Componentes** · **Números** · **A ausência** · **Vocabulário** |
| figura, mapa, legenda | **Figura** · **Componentes** · **Acessibilidade** |
| prosa de página, título, nota | **Vocabulário** · **A ausência** · a regra de 03/10 |
| CSS, token, fonte | **Tipografia** · **Cor** |
| texto do blog | **Blog** |
| qualquer um dos acima | a **hierarquia**, e o contrato da página |

## A ausência, que é o caso mais comum do site

Esta é a decisão que o site toma mais vezes, e ela **já está fechada** — em quatro lugares, não num.

- **Quatro estados distintos, e nenhum deles é zero nem travessão**: zero medido · ausência de dado ·
  dado indisponível · dado não coletado (`CLAUDE.md`, regras editoriais;
  `layout/regras.json/numeros.sem_dado_nunca_e_zero`). No cartão, **travessão e vazio reprovam**, e o
  portão confere o cartão **renderizado**.
- **As três classes de ausência têm nome** (`METODOLOGIA.md` §42.3, no caso do financiamento):
  `sem_lancamento_182` (entregou e não lançou ali) · `sem_declaracao` (não entregou o exercício) ·
  `sem_coleta` (o Monitor ainda não consultou). Nenhuma tem valor por habitante, e a mediana
  publicada sai **só de quem tem lançamento** — incluir ausência como zero rebaixaria a mediana com
  não-dado. O desenho é o modelo para qualquer outra série: nomear a classe, não fundir no zero.
- **"Não tem" e "não achamos" são coisas diferentes**, e é aqui que o cartão erra mais:
  - a lacuna é **nossa** (alcance de busca) → teto público **"não localizamos até o corte"**, nunca
    "não existe";
  - a lacuna é **deles**, declarada formalmente pelo órgão competente em resposta a pedido de acesso →
    entra em **`data/ausencia_declarada.json`** (§201), com órgão, data e ponteiro para o registro
    interno. **É o único caso em que o site pode dizer que não existe**, e a promoção ao site é
    decisão da editoria (R7).
- **Valor real pequeno não é zero** (§42.3): o dado guarda as casas que tem e a exibição diz "menos
  de R$ 0,01". Arredondar para zero o que existe é o mesmo erro, só mais difícil de ver.
- **Proporção sobre o total não é comparação construída.** O que a página não constrói é **razão
  entre etapas** e **ranking ordinal** (`layout/regras.json/dados_na_pagina`, nota). Um cartão com
  "4.112 de 5.569" mostra a cobertura da série, e o leitor compara. Na dúvida sobre um caso novo,
  vale a `METODOLOGIA.md` — e o subagente `auditor-de-lacuna` revisa o diff contra estas regras.

## A hierarquia, que decide todo empate

```
AI_EDITORIAL_NARRATIVE_GOVERNANCE.md   (editorial e narrativa)
AI_VISUAL_ART_DIRECTION.md             (direção de arte)
  >  METODOLOGIA.md                    (travas de PROVA: limite de fato, não de estilo)
  >  CLAUDE.md                         (§ Design, § 3 Paleta, § 4 Tipografia, regras editoriais)
  >  layout/contratos/<pagina>.json    (o layout de cada página)
  >  handovers                         (o pedido da rodada)
```

Em três palavras: **prova, depois narrativa, depois estética.** A `METODOLOGIA.md` decide o que pode
ser afirmado; a governança editorial decide por que, onde e como se diz; a direção de arte decide com
que forma aparece. Quando o estilo pede o que a prova não sustenta, vence a prova.

**Se um handover contrariar uma regra, a regra vence**: aplica-se a regra, registra-se a divergência
em uma linha (no contrato, no código ou no relatório) e segue-se — sem perguntar.

## Antes de mexer

1. Ler as regras aplicáveis: os dois documentos `AI_*`, o `§ Design`/Paleta/Tipografia do
   `CLAUDE.md` e **o contrato da página** em `layout/contratos/<pagina>.json`.
2. Mudança de **layout** começa pelo **contrato**. Mudança de **regra** começa pelo
   **documento-fonte** e por `layout/regras.json`.
3. No PR, anexar a lista de conformidade que o portão imprime.
4. Consultar o `CODEMAP.md` antes de explorar: ele diz que arquivo afeta que tela, consome que dado e
   é coberto por que portão. Ler só o que ele lista para o que a tarefa toca.

## Checklist de conformidade

**Componentes e layout**
- Elementos equivalentes usam o **mesmo componente, classe e token**. Nada de ajuste manual de pixel.
- Números em `.cartao-numero`, dentro de `.grade-numeros--3`. Figura em `.cartao-mapa`, dentro de
  `.grade-figuras--3`.
- Seção **sem caixa** e **sem numeração**. Última linha da grade pode ficar incompleta.
- Figura larga (`.cartao-mapa--largo`) só para **diagrama**, no máximo **uma por página**, com as
  exigências que `layout/regras.json` lista em `componentes.figura_larga`.
- Nenhum elemento passa de **40% da largura** fora dos casos previstos no contrato.

**Tipografia** (`CLAUDE.md` §4; `layout/regras.json/tipografia`)
- Escala fixa: **12 · 14 · 16 · 18 · 22 · 28 · 36 · 48 px**. Nenhum valor literal fora dela — use a
  variável (`var(--fs-small)` e companhia).
- Display é **Fraunces peso 300**, com itálico para ênfase. **Nunca bold no display.**
- Corpo em **Archivo**. Legenda, dado, crédito em **Archivo Narrow versalete**
  (`text-transform: uppercase`, `letter-spacing` ≥ 1 px, `font-variant-numeric: tabular-nums`).

**Cor** (`CLAUDE.md` §3; `assets/tokens.css`)
- Hexadecimal **só** em `assets/tokens.css` e `assets/mapas.js`. Em qualquer outro lugar, token.
- **Fundo branco** — desvio declarado e reafirmado pela editoria; não reverter para escuro nem osso
  por fidelidade à marca.
- Bioluz e sintético são **acento**, um por vez, em dose pequena. Argila e âmbar são **calor**: linha,
  detalhe, hover — nunca fundo de área grande.
- **Cor nunca sozinha**: ela não é o único portador da informação, e não introduz julgamento que o
  dado não sustenta (direção de arte §10).
- Proibido: verde eco saturado, prata, cromado, neon, gradiente arco-íris, ícone de folha.

**Figura** (governança §11 a §14)
- **Quatro funções separadas**, nunca fundidas: `titulo` · `legenda` · `nota_metodologica` · `fonte`.
- Título obrigatório. Fonte obrigatória, com data de atualização. Numerada a partir de 1.
- A legenda **não repete o título** e é curta (governança §13). O teto que a máquina cobra são
  **180 caracteres**, de `layout/regras.json` → `figura.legenda_maxima_caracteres`.
- Legenda, título de figura, tooltip e cartão **só descrevem** — variável, período, território,
  unidade, fato. Interpretação vive no texto narrativo, e o portão 19
  (`verificar_legendas.js`) reprova juízo ali.
- Toda mídia é rotulada (`alt`, `aria-label` ou equivalente).

**Números** (`layout/regras.json/numeros`)
- Formato **pt-BR**. População em milhões com **uma casa**.
- Zero por extenso no cartão. **Travessão no cartão é proibido.**
- **Zero medido, ausência de dado, dado indisponível e dado não coletado são quatro coisas
  distintas**, e nenhuma delas é travessão nem vazio. O portão confere o cartão **renderizado**.

**Dado na página** (`layout/regras.json/dados_na_pagina`)
- **Estados em mapa. Municípios em lista com busca.**
- **Comparação construída é proibida**: razão entre etapas e ranking ordinal são comparações nossas.
  A página mostra as etapas; quem compara é o leitor.
- Nada escrito à mão que dependa do dado — se depende, é gerado.

**Vocabulário** (`layout/regras.json/vocabulario_proibido`)
- Proibidas no site inteiro, entre outras: `dados abertos`, `base de dados`, `código-fonte`,
  `repositório público`, `licença de dados`, `CC BY`, `não distribuído`, `FIGURA`, `desastre`,
  `defeso`, `corte de`, `Corte da edição`, `mês lido`, `meses lidos`, `subfunção`. A lista fechada
  está no JSON, com as proibições por página.
- `apenas` e `somente` não acompanham número. Linguagem de dever (`é obrigatório`, `deve publicar`,
  `tem o dever de`) não entra.

**Regra editorial que atravessa tudo** (editoria, 03/10/2026)
- **Dizemos o que disponibilizamos; nunca o que não disponibilizamos.** Onde couber: "A metodologia é
  pública." Ponto. **Nenhuma frase** sobre código, base de dados ou licença de dados. A página da
  **metodologia** é o único material técnico público.
- Teto público de ausência: **"não localizamos até o corte"** — nunca "não existe".
- Nunca inventar dado: ausência é **lacuna declarada**, com fonte.
- Nenhum nome de autor parlamentar no site.
- Texto explicativo vai direto ao que se vê: sem instrução de uso, sem nota interna.

**Acessibilidade** (direção de arte §23: criatividade visual nunca compromete contraste,
legibilidade, daltonismo ou leitura em tela pequena. Os números vêm de onde indicado)
- Contraste **AA**, 4.5:1 no texto corrido (`CLAUDE.md` §3 Paleta).
- Alvo de toque **44 px** no celular, exceto link em meio a parágrafo; largura de celular **390 px**;
  **sem rolagem horizontal**; texto invisível proibido; mídia rotulada
  (`layout/regras.json/acessibilidade`).

**Blog** (`layout/regras.json/blog`; regra 2 da editoria, 03/10/2026)
- O blog conta **acontecimentos do ciclo, em prosa** — não decisões, método, correções nem
  funcionamento do site (isso vive na metodologia e em `mudancas.html`).
- **Texto corrido**: sem tópicos, sem listas, sem cartões no meio do texto.
- Escrito por pessoa. O Code **não escreve, não edita e não aprova** texto do blog, e publica só o que
  estiver em `robo-registro/blog/` com `aprovado: sim`. O guia de redação é **da central** e vive no
  repositório privado da editoria — não há cópia local, e o Code não o edita.

## Rodar o portão

```bash
python3 scripts/quais_portoes.py --comando     # diz quais portões a mudança pode afetar
python3 scripts/verificar_conformidade.py      # o que reprova em conformidade
```

`scripts/quais_portoes.py` usa o mesmo critério da CI: PR que só toca texto de página não roda portão
de dado, e vice-versa. Na dúvida, `python3 scripts/portoes_locais.py tudo`. **Nada sobe com portão
vermelho.** Para a suíte inteira sem gastar contexto, o subagente `portoes-runner` devolve só o
veredito e as falhas.

## O que só a editoria decide (governança §29)

Redefinir metodologia · mudar o significado de um indicador · eliminar evidência substantiva ·
introduzir interpretação científica nova · mudar o objetivo do projeto · criar conclusão não
sustentada · alterar fato ou fonte · mudar pesos, créditos ou componentes do índice (exige versão
maior, `METODOLOGIA.md` §12) · alterar `data/publicacao.json`.

**Ordem, agrupamento, remoção de redundância, posição de nota, transição, correção gramatical e
responsividade o Claude decide sozinho** — e decide, não pergunta.

## Onde está cada decisão

| assunto | fonte |
|---|---|
| editorial, narrativa, figura | `AI_EDITORIAL_NARRATIVE_GOVERNANCE.md` |
| estética, composição, cor, forma | `AI_VISUAL_ART_DIRECTION.md` (§25: não se maquia componente por componente) |
| o que pode ser afirmado | `METODOLOGIA.md` |
| design, paleta, tipografia, regras editoriais | `CLAUDE.md` |
| o layout de cada página | `layout/contratos/<pagina>.json` |
| o que a máquina reprova | `layout/regras.json` + `scripts/verificar_conformidade.py` |
| exceção registrada | `layout/excecoes.json` |
| voz e texto público | `docs/VOZ_EDITORIAL.md`, `docs/GUIA_DO_EDITOR.md` (o mais restritivo prevalece) |
| redação do blog | guia da central, no repositório privado — sem cópia local |
| como a mudança entra no site | `docs/PROTOCOLO_ATUALIZACAO.md` §3 |
| que arquivo afeta que tela | `CODEMAP.md` |

**Nota sobre a voz de marca.** O `CLAUDE.md` tem uma seção de marca pessoal com voz provocadora e
poética. Ela **não se aplica ao conteúdo público do site**: ali vence a governança editorial, que
exige voz clara, sóbria e não promocional (§16) e proíbe dramatização e metáfora excessiva (§24). A
voz de marca vale para material de apresentação que não seja conteúdo do índice.
