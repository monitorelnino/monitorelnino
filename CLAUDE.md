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
é o único lugar que reprova de verdade — hoje são 61 comandos (`--listar` confere). Este arquivo e o PROTOCOLO
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

---

# Marca pessoal · Futurismo regenerativo encarnado

> Acrescentado em 23/09/2026 a pedido da editoria. O conteúdo acima (governança
> do MARÉ) permanece íntegro; esta seção rege **design, edição e conteúdo**.
> Não muda a arquitetura do código.
>
> **DESVIO DECLARADO — o fundo deste site é BRANCO.** A Seção 3 abaixo manda
> "base sempre escura (vazio/abissal) ou osso". Aqui não vale: o fundo branco é
> decisão editorial de 05/09/2026, reafirmada pela editoria em 23/09/2026, e
> está registrada em `assets/tokens.css`. **Não reverter `--bg` para escuro nem
> para osso** por fidelidade à marca — a editoria já decidiu, e decidiu contra.
> Todo o resto da Seção 3 (paleta, papéis das cores, proibições) vale integral.

---

## 1. Pedido de instalação das skills

Antes de editar qualquer página, componente ou texto deste site:

1. Crie a skill de marca em `.claude/skills/marca-pessoal/SKILL.md` (o conteúdo está na Seção 6). Ela é a fonte de verdade visual e de tom deste projeto.
2. Verifique se existe uma skill ou plugin de design de interface instalado (por exemplo `frontend-design`, do marketplace oficial de plugins do Claude Code; use `/plugin` para conferir e instalar). Se existir, use-a para composição, hierarquia e acabamento, **sempre subordinada à `marca-pessoal`**: ela nunca substitui paleta, fontes ou tom daqui, e é proibido cair no visual genérico de IA (gradientes roxos, fontes padrão, cards idênticos).
3. Para gráficos e painéis, use a paleta da Seção 3 como paleta de séries. Sem skill de dataviz disponível, siga as regras da Seção 6.
4. Para conferir o resultado, rode o site localmente e verifique em 375px e em desktop (Playwright ou o navegador disponível), comparando com o checklist da skill.
5. Se algo acima não estiver disponível, siga este arquivo diretamente e avise o que faltou.

## 2. Tese (uma frase para guiar toda decisão)

A marca não fala de sustentabilidade, fala de regeneração: restaurar e co-evoluir, deixar o sistema mais vivo do que se encontrou. O futurismo é **encarnado** (corpo, presença, matéria) e **sintético no sentido de síntese** (o híbrido onde não se distingue o que cresceu do que foi fabricado).

- Slogan pessoal: **O futuro começa como ideia.** / *The future begins as an idea.*
- Frase-manifesto: *O futuro não se prevê. Cultiva-se.* / *The future is not foreseen. It is cultivated.*
- Slogan da Futura Evidence Lab (organização parente): **Imaginar não basta.** A pessoa abre, a Futura cobra.

Personalidade em quatro palavras: **Magnetismo, Provocação, Vitalidade, Espírito.** ("Sedução" foi substituída por magnetismo de propósito: presença que se impõe pela contenção.)

Regra de ouro: **nenhuma imagem bela sem substância; nenhum dado sem beleza.** Toda seção do site que for só bonita precisa de um dado, fonte, tese ou referência. Toda seção só informativa precisa da marca.

---

## 3. Paleta (tokens)

```css
:root {
  /* bases */
  --vazio:    #0E0F0D;
  --abissal:  #15201A;
  --musgo:    #2E3D30;
  --osso:     #EDE6D8;
  --areia:    #D6C4AC;
  /* calor (nunca protagonista) */
  --argila:   #7C4A34;
  --ambar:    #C9814B;
  /* acentos (um por vez, em pequena dose) */
  --bioluz:    #A8C99A;  /* o vivo */
  --sintetico: #5E7C93;  /* o fabricado */
  --mineral:   #8FA5A8;  /* apoio frio */
}
```

Regras de uso:

- **Base sempre escura (vazio/abissal) ou osso.** Eles dominam a página.
  · **Exceção permanente deste site (23/09/2026):** o MARÉ usa fundo **branco**,
  por decisão editorial de 05/09/2026 reafirmada em 23/09/2026. Ver o desvio
  declarado no alto desta seção. O tema técnico sobre branco é o padrão do site.
- Argila e âmbar entram como calor: linhas, detalhes, hover. Nunca como fundo de área grande.
- **Bioluz e sintético são acentos.** Um por vez, em pequena dose: o detalhe que "acende" (link, ponto, sublinhado, número em destaque). Nunca preencher áreas grandes.
- A tensão bioluz × sintético é a marca em duas cores: o híbrido.
- **Proibido:** verde eco-óbvio saturado, prata futurista, cromado, neon, gradientes arco-íris, ícones de folha.
- Modo escuro é o padrão da identidade. O modo claro usa fundo osso, texto vazio, mesmos acentos. Conferir contraste mínimo AA (4.5:1 no texto corrido).

---

## 4. Tipografia

- **Display:** Fraunces, **peso leve (300)**, com itálico. Nunca bold. Títulos, frases-manifesto, assinatura.
- **Texto:** Archivo. **Legendas, dados, créditos:** Archivo Narrow em versaletes espaçados (`letter-spacing: .12em; text-transform: uppercase`) com números tabulares (`font-variant-numeric: tabular-nums`). É o registro de "espécime de laboratório".
- Fallbacks: `Georgia, 'Playfair Display', serif` no lugar de Fraunces; `Inter, 'Segoe UI', sans-serif` no lugar de Archivo.

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@400;500&family=Archivo+Narrow:wght@400;500&family=Fraunces:ital,opsz,wght@0,9..144,300;1,9..144,300&display=swap" rel="stylesheet">
```

```css
:root {
  --font-display: 'Fraunces', Georgia, 'Playfair Display', serif;
  --font-text: 'Archivo', Inter, 'Segoe UI', sans-serif;
  --font-spec: 'Archivo Narrow', 'Archivo', sans-serif;
}
h1, h2, h3 { font-family: var(--font-display); font-weight: 300; }
.spec { font-family: var(--font-spec); text-transform: uppercase; letter-spacing: .12em; font-variant-numeric: tabular-nums; }
```

---

## 5. Direção de imagem, voz e conteúdo

**Imagem:** retratos com luz dramática e encenação (aura), matéria orgânica com toque resinoso/sintético, texturas táteis e foscas. Nada metálico, nada de banco de imagens genérico. Legenda de imagem sempre com fonte ou tese, em Archivo Narrow.

**Corpo como marca:** presença e contenção. Uma peça-manifesto por composição, todo o resto quieto. Gastar a ousadia em um só lugar da página.

**Tom de voz:** provocador, poético, espirituoso e vivo. A voz seduz a mente antes do olhar.

> **SUBORDINAÇÃO DECLARADA (24/09/2026).** Este parágrafo **não se aplica ao conteúdo público do
> site**. A `AI_EDITORIAL_NARRATIVE_GOVERNANCE.md` é a fonte de verdade editorial e tem precedência
> declarada: ela exige voz **clara, segura, precisa, sóbria e não promocional** (§16), proíbe
> dramatização, frase de impacto e metáfora excessiva (§24), e proíbe dizer ao leitor o que pensar
> (§20). Onde as duas colidem, **vence a governança** — e o portão 19 (`verificar_legendas.js`) já
> reprova juízo e interpretação em texto de figura, de modo que a colisão nem chega ao ar.
>
> Onde esta voz **vale**: material de marca e apresentação que não seja conteúdo público do índice.
> Onde ela **não vale**: título, legenda, nota, fonte, tooltip, cartão, prosa de página — tudo o que
> o leitor encontra no site. A razão é do próprio sistema de marca, no fim da Seção 7: *"dúvida entre
> mais bonito e mais rigoroso: escolher o que preserva o rigor visível"*. Num monitor de evidências,
> o rigor visível **é** o produto.

| Faz | Não faz |
|---|---|
| Afirma teses com elegância e lastro | Opina sem fundamentar |
| Provoca com ideias contraintuitivas | Polêmica vazia ou choque fácil |
| Junta metáfora orgânica e precisão científica | Escolhe entre poesia OU dado |
| Ironia inteligente, humor sofisticado | Humor raso, sarcasmo cínico |
| Bilíngue PT/EN quando amplia alcance | Bilíngue decorativo |

**Pilares de conteúdo** (toda seção nova do site deve servir a um): Tese, Artefato ("achados do futuro" legendados como espécimes de 2075), Bastidor do rigor (o dado por trás da beleza) e Presença.

**Relação com a Futura Evidence Lab:** parentesco visual (família terrosa, rigor tipográfico, mão orgânica), sem ser gêmea. A marca pessoal é a voz autoral e mais emocional; a Futura é a organização e mais evidência. Não copiar o layout de uma na outra.

---

## 6. Conteúdo da skill local: `.claude/skills/marca-pessoal/SKILL.md`

Instalada em 23/09/2026. Ver o arquivo; o checklist dele é obrigatório antes de entregar
qualquer edição de design, layout ou texto.

---

## 7. Como o Claude deve trabalhar neste repositório

- Pedidos de "editar o site" ou "melhorar o design" são tratados como **edição e elevação**, não criação do zero: primeiro auditar o que existe, podar o desalinhado, manter o que carrega credibilidade, depois produzir.
- Ao terminar, dizer em duas linhas o que mudou e apontar qualquer trecho que ainda quebra a marca.
- Dúvida entre "mais bonito" e "mais rigoroso": escolher o que preserva o rigor visível. O risco da marca é parecer estética demais e perder credibilidade.
