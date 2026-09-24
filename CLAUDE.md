# CLAUDE.md · instruções para o Claude Code neste repositório

Lido automaticamente pelo Claude Code ao abrir o projeto. Resume as regras de
trabalho; os documentos canônicos citados abaixo prevalecem em caso de dúvida.

## O projeto

MARÉ · Medida de Antecipação e Resposta ao El Niño (monitorelnino.com.br),
iniciativa de jornalismo de dados de interesse público da Futura Evidence Lab.
Site estático (HTML + JSON em `data/`), pipeline de coleta em Python/Node,
publicado pelo Netlify a partir da raiz do repositório (`netlify.toml`).

Documentos canônicos:
- **`AI_EDITORIAL_NARRATIVE_GOVERNANCE.md` — fonte de verdade EDITORIAL e NARRATIVA.**
  Leitura obrigatória **antes** de criar, alterar, reorganizar ou revisar qualquer
  conteúdo público: página, seção, título, legenda, nota, figura, mapa, tabela,
  cartão, indicador ou chamada. Ele declara precedência sobre padrão local e
  hábito anterior de geração; onde divergir de outro documento, ele ganha —
  exceto nas travas de prova do `METODOLOGIA.md`, que são limite de fato e não
  de estilo (ver abaixo).
- **`AI_VISUAL_ART_DIRECTION.md` — fonte de verdade de ESTÉTICA e DIREÇÃO DE ARTE.**
  Governa composição, ritmo, cor, tipografia, forma da visualização e experiência
  visual. Leitura obrigatória antes de mexer em layout, componente visual, paleta
  ou gráfico. O §25 dele é vinculante: **não se maquia componente por componente**
  — observa-se o site inteiro, reconstrói-se a direção, e só então se propaga.
- `docs/PROTOCOLO_ATUALIZACAO.md` — como toda mudança entra no site (pista B, §3).
- `METODOLOGIA.md` — fonte de verdade do método; `CHANGELOG.md` — resumo por §.
- `docs/GUIA_DO_EDITOR.md` e `docs/VOZ_EDITORIAL.md` — texto público e voz, hoje
  subordinados à governança editorial acima; onde eles forem mais restritivos,
  o mais restritivo prevalece (os dois proíbem juízo em legenda; a governança
  também).
- `.github/workflows/portoes.yml` — lista canônica dos portões.

## Idioma e modo de trabalho

- Responder à editoria em português do Brasil.
- Execução silenciosa: não narrar passos intermediários nem pedir confirmação
  para decisões técnicas rotineiras (bugs, implementação, testes, refatoração).
  Ao concluir: resumo curto — o que foi feito, mudanças importantes,
  verificações realizadas, o que ficou sem solução.
- Interromper só para: credencial ausente, ação destrutiva ou irreversível,
  risco de perda de dado, decisão de produto não inferível, conflito real entre
  requisitos, ou impedimento técnico após diagnóstico razoável.
- Verificar cada informação antes de apresentá-la como fato; suposição não
  verificada nunca é apresentada como dado.
- Pendência que Claude consegue resolver é resolvida, não listada.

## Fluxo de mudança (PROTOCOLO §3.1)

1. Partir da `main` atualizada; ramo `edicao/AAAA-MM-DD-tema`.
2. Editar com verificação de âncora antes de cada substituição.
3. Rodar os portões locais; nada sobe com portão vermelho.
4. Registrar no `CHANGELOG.md` (próximo §) e, se cabível, em `METODOLOGIA.md`.
5. Regenerar derivados quando dado ou página mudar (`bash scripts/verificar_derivados.sh`
   regenera a cadeia canônica e o manifesto; arquivo derivado não se edita à mão).
6. Push, conferir que chegou (`git fetch` + `git merge-base --is-ancestor HEAD origin/<ramo>`),
   abrir PR, aguardar a Action "Portões" verde, fazer merge.

Limites do merge automático:
- Protótipo de página ou de recurso: mostrar à editoria (capturas ou prévia)
  **antes** de mesclar. "Montar o protótipo" não autoriza merge nem publicação.
- Republicar o domínio, lançá-lo ou revertê-lo exige a palavra da editoria
  ("siga pra publicação"). Regime atual do domínio: senha + `noindex`.
- `data/publicacao.json` (indexação e regime do domínio) só muda por decisão da editoria.
- Alterar `.github/workflows/` é permitido quando o pedido exigir.

## Portões

```
python3 scripts/portoes_locais.py tudo        # ou: paginas | dados
```

A lista de portões **não vive aqui**. Ela é derivada de `.github/workflows/portoes.yml`, que
é o único lugar que reprova de verdade — hoje são 47 comandos (`--listar` confere). Este arquivo e o PROTOCOLO
§3.3 *descrevem* o conjunto; não o definem. Rodar um subconjunto escolhido a olho custou um
ciclo de CI em 23/09/2026 (`verificar_seguranca.js` ficou de fora e reprovou lá por uma
Action sem SHA fixado).

Use `dados` sempre que tocar `data/`, um `*.py` de coleta ou dependências; na dúvida, `tudo`.
`--listar` mostra a lista sem rodar. Nada sobe com portão vermelho.

Atalhos: `/portoes`, `/p12` (derivado obsoleto), `/e-da-main` (a falha é minha ou já estava
na `main`?), `/merge-main`, `/lote`. Para a suíte inteira sem gastar contexto, o subagente
`portoes-runner` devolve só o veredito e as falhas.

### Portão 12 — derivado obsoleto

Sequência fixa: `bash scripts/verificar_derivados.sh` → `git add -A` → commit → rodar de
novo. Arquivo derivado **não se edita à mão** (há hook que bloqueia). Antes de assumir a
culpa, confira com `/e-da-main`: carimbo obsoleto já deixou a `main` vermelha sozinho.

## Arquivos que nunca entram em contexto

| arquivo | tamanho |
|---|---|
| `data/log_buscas.json` | ~14 MB |
| `data/fontes_consultadas.json` | ~12 MB |
| `data/verificacao_municipal.json` | ~2 MB |
| `evidencias/` | ~380 MB |

Consulte sempre agregando (`python3 -c "import json,collections; ..."`), nunca com `Read`.
Um Read nos dois primeiros estoura a sessão sozinho. Há hook que bloqueia acima de 1 MB em
`data/`, `dados-abertos/` e `evidencias/`.

## Log append-only: merge pela base comum

`data/log_buscas.json` e `data/historico_mudancas.json` só crescem. Quando os dois lados
acrescentam e o merge conflita, **nunca deduplique por conteúdo**: execuções idênticas no
log v2 são tentativas reais distintas e contam. Una pela base comum
(`base + nossos_novos + deles_novos`) e confira que o total final é **maior ou igual** a cada
lado. Em 23/09/2026 uma união por conteúdo produziu um log menor que cada lado — quase 3.000
execuções apagadas sem aviso. Use `/merge-main`.

## Regras editoriais que o código não pode violar

- Nunca inventar dado. Ausência é "lacuna declarada", com fonte.
- Teto público de ausência: "não localizamos até o corte" — nunca "não existe".
- Zero, ausência de dado, dado indisponível e dado não coletado são coisas distintas.
- Decreto (`categoria=decreto`) não pontua no índice; fica no banco para transparência.
- Na dúvida, o classificador não classifica; contribuição pública vai à revisão humana.
- Legendas, títulos de figura, tooltips e cartões só descrevem (variável,
  período, território, unidade, fato) — interpretação vive no texto narrativo (portão 19).
- Texto explicativo: direto ao que se vê, sem instrução de uso e sem nota interna.
- Nenhum nome de autor parlamentar no site.
- Mudança de pesos, créditos ou componentes do índice exige versão maior (METODOLOGIA §12).

**Como as três fontes de verdade se combinam.** A `METODOLOGIA.md` decide **o que pode ser
afirmado**; a `AI_EDITORIAL_NARRATIVE_GOVERNANCE.md` decide **por que, onde e como** aquilo é
dito; a `AI_VISUAL_ART_DIRECTION.md` decide **com que forma** aquilo aparece. A ordem de
precedência quando colidem é essa mesma: prova, depois narrativa, depois estética — e é a
própria direção de arte que diz, no §23, que criatividade visual nunca compromete contraste,
legibilidade, daltonismo ou leitura em tela pequena, e no §10 que cor não introduz julgamento
que o dado não sustenta.

**Como a metodologia e a governança editorial se combinam.** A `METODOLOGIA.md` decide **o que
pode ser afirmado** (prova, lacuna declarada, teto de ausência, o que pontua); a
`AI_EDITORIAL_NARRATIVE_GOVERNANCE.md` decide **por que, onde e como** aquilo é
dito ao leitor. Elas não competem: a primeira é limite de fato, a segunda é ordem
da informação. Quando uma regra de estilo pedir algo que a prova não sustenta,
vence a prova — e a governança diz o mesmo, no §6 (incerteza interna nunca vira
afirmação pública) e no §15 (não transformar "não encontrado" em "não existe").

**Decisão que exige a editoria** (governança §29): redefinir metodologia, mudar o
significado de um indicador, eliminar evidência substantiva, introduzir nova
interpretação científica, mudar o objetivo do projeto, criar conclusão não
sustentada ou alterar fato ou fonte. Ordem, agrupamento, remoção de redundância,
posição de nota, transição, correção gramatical e responsividade o Claude decide
sozinho.

## Design

- Cor em hexadecimal só em `assets/tokens.css` e `assets/mapas.js`.
- Escala tipográfica fixa: 12 · 14 · 16 · 18 · 22 · 28 · 36 · 48 px.
- Elementos equivalentes usam o mesmo componente, classe e token; nada de
  ajuste manual de pixel. Toda figura usa o componente padrão de figura,
  numerada a partir de 1, com fonte e data de atualização.

## Segurança e o que não entra neste repositório

- Repositório público. Nunca commitar token, chave, senha ou `.env` preenchido;
  o acesso ao GitHub vem do login local, não de arquivo.
- Material privado (pedidos e respostas de LAI, notas jurídicas, notas internas,
  diagnósticos) vive no repositório privado da editoria, nunca aqui.
- O código será aberto: nenhuma API ou produto pago dependurado no código,
  nem atrás de chave configurável.
- `robots.txt` é pedido, não tranca (RFC 9309 §1.3; §185): o Monitor o lê, respeita o
  `Crawl-delay` e acessa documento público mesmo onde ele pede que robôs não entrem — com o
  cliente identificado e rastro em `data/robots_registro.json`. Nunca disfarçar o cliente.
- Bloqueio de acesso real (`401`, `403`, `429`, `451`, captcha, login) se respeita, sempre.
- Recusa servida com `200` é recusa (§186, §187): muro de robô (Imperva, Cloudflare, Akamai)
  e geobloqueio de WAF parecem conteúdo e entrariam no índice como prova falsa.
  `coletores_base.detectar_muro_de_robo` levanta antes de preservar. Nunca nomeie a recusa
  errado: chamar geobloqueio de `robots.txt` já custou treze dias de abstenção indevida.
