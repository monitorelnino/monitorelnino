# CLAUDE.md · instruções para o Claude Code neste repositório

Lido automaticamente pelo Claude Code ao abrir o projeto. Resume as regras de
trabalho; os documentos canônicos citados abaixo prevalecem em caso de dúvida.

> # HIERARQUIA DAS REGRAS (editoria, 02/10/2026 — conformidade permanente)
>
> ```
> AI_EDITORIAL_NARRATIVE_GOVERNANCE.md   (editorial e narrativa)
> AI_VISUAL_ART_DIRECTION.md             (direção de arte)
>   >  METODOLOGIA.md                    (travas de PROVA: limite de fato, não de estilo)
>   >  CLAUDE.md                         (§ Design, § 3 Paleta, § 4 Tipografia, regras editoriais)
>   >  layout/contratos/<pagina>.json    (o layout de cada página)
>   >  handovers                         (o pedido da rodada)
> ```
>
> **Se um handover contrariar uma regra, a regra vence**: aplica-se a regra, registra-se a
> divergência em uma linha (no contrato, no código ou no relatório) e segue-se — sem perguntar.
>
> As regras verificáveis por máquina estão extraídas em **`layout/regras.json`**, e quem reprova é
> **`scripts/verificar_conformidade.py`**, portão bloqueante em todo PR que toque página, estilo,
> script de página, figura, texto público ou dado exibido. Exceção só por `layout/excecoes.json`,
> com regra, página, motivo, data e quem decidiu — exceção sem registro é vermelho.
>
> **Antes de mexer:** (1) ler as regras aplicáveis — os dois documentos `AI_*`, o § Design/Paleta/
> Tipografia e o contrato da página; (2) mudança de LAYOUT começa pelo **contrato**, mudança de
> REGRA começa pelo **documento-fonte** e por `regras.json`; (3) no PR, anexar a lista de
> conformidade que o portão imprime; (4) handover contra regra → aplica a regra e registra.

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

## Idioma e modo de trabalho — AUTONOMIA DECISÓRIA RESPONSÁVEL (regime vigente, editoria, 27/09/2026, noite)

> # LEI PERMANENTE
> **(reforçada pela editoria em 30/09/2026)**
>
> ## Toda rodada, todo handover, sem exceção: **rápido, limpo, eficiente, sem narrar progresso, sem pedir confirmação fora das paradas listadas abaixo, sem elucubração.**
>
> **Isto não precisa ser lembrado a cada pedido — vale sempre, por padrão, em todo handover,
> existente ou futuro.** Não substitui o que vem abaixo (decide sozinho · para e pergunta ·
> relatório de até 6 linhas): **reforça** o mesmo princípio e declara que ele é permanente e não
> precisa ser reinvocado.
>
> **Na prática, três consequências que a editoria nomeou:**
> - **Execução em lote, não uma pergunta por vez.** Lista de itens se executa inteira, na ordem
>   dada, sem parar entre um item e outro para relatar ou pedir confirmação. Relatório só ao fim de
>   cada entrega (PR aberto) ou de tudo — nunca a cada passo intermediário.
> - **Conflito de merge não é parada.** Resolve-se sozinho, pela regra de união pela base comum.
> - **Portão vermelho não é parada.** Diagnostica-se e corrige-se sozinho; só vira pergunta se o
>   impedimento persistir **depois** de diagnóstico razoável — condição que já está na lista abaixo.

Responder à editoria em português do Brasil. Estilo de fala: o *output style* `caveman`
(`.claude/output-styles/caveman.md`), ligado por `outputStyle` em `.claude/settings.json`
— permanente, em toda sessão, sem invocar skill. Desligar só a pedido da editoria, por PR.

**Comportamento padrão: analisar → decidir → implementar → testar → verificar → corrigir → continuar.**
Não transferir à editoria decisões que um engenheiro competente toma sozinho. Não narrar o
que está fazendo. Não pedir permissão. Não apresentar listas de opções para que ela escolha
o que o código pode escolher. Ausência de especificação significa "use o melhor padrão
profissional aplicável"; entre duas soluções, a mais simples, mais reversível e mais coerente
com o que já existe.

**Decide sozinho (nunca pergunta):** estrutura, nomes, organização de arquivos, refatoração
necessária ao pedido, tratamento de erro, retry, timeout, cache, validação, normalização,
estados vazios e de carregamento, responsividade, acessibilidade, layout e espaçamento
dentro do sistema de design, escolha entre bibliotecas já compatíveis, correção de bug,
prevenção de crash, melhoria óbvia de segurança, proteção contra API instável, ordem de
execução de tarefas, e **todo defeito que o pedido em curso expõe** (corrige, testa,
registra no CHANGELOG — não pede autorização). Antes de perguntar, o teste: "existe decisão
razoável, segura, reversível e coerente que eu possa tomar sozinho?" Se sim, não pergunta.

**Para e pergunta (só isto):** credencial ou conta que não existe; exclusão irreversível de
dado; mudança de regra, peso, régua ou categoria do índice; alteração material de texto
público editorial, institucional ou científico; licença e distribuição de código; risco jurídico
ou de privacidade que dependa de autorização; conflito real entre requisitos; impedimento
técnico que persista após diagnóstico razoável. Pergunta em **uma linha**, com a
recomendação já feita e o que acontece se não houver resposta.

**Ao concluir:** relatório de até 6 linhas — o que mudou · verificação executada (portões,
CI, testes, números com fonte) · o que ficou sem solução · o que só a editoria decide.
Nada de plano em prosa antes de agir; o plano vive no branch, nos commits e nos testes.

**Verificar cada informação antes de apresentá-la como fato;** suposição não verificada
nunca é apresentada como dado. Autonomia não é impulsividade: quanto maior o impacto e
menor a reversibilidade, maior a certeza exigida — e mudança incremental, com rollback.

> **Publicação de página (30/09/2026, revoga a regra de 22/09):** a editoria removeu a
> trava do "vai" para publicar. Merge com portões verdes já autoriza publicar e republicar
> o domínio, sempre no regime vigente de "cortina" (senha + `noindex`) — é ambiente fechado
> ao público, não uma página ao vivo. Segue exigindo capturas no PR, para a editoria ver a
> mudança (antes ou depois de publicada, não importa mais a ordem), mas não espera resposta
> para publicar. Isso vale para todo PR que só muda a página dentro da cortina; não se
> aplica a alterar a própria configuração de cortina/senha/noindex, remover o domínio da
> lista de indexação bloqueada, nem a nenhuma das outras paradas desta lista.

> **Histórico de regimes.** 26/09 (§238): a skill `karpathy-guidelines` impôs "declarar
> suposição e perguntar na dúvida" e "apresentar leituras em vez de escolher". 27/09 (§250,
> §253): skill `caveman` ligada por invocação a cada sessão. **27/09, noite: a editoria
> revogou o regime de 26/09** — o código conversava demais e pedia decisões que sabia tomar.
> Nas colisões, **vence este CLAUDE.md**: `karpathy-guidelines` continua valendo para
> qualidade de código (escopo, simplicidade, nada de mudança gratuita), não para a
> interação; `caveman` deixa de ser skill invocada e passa a *output style* permanente.
> `.claude/skills/caveman/SUBORDINACAO.md` fica como histórico.
>
> **05/10/2026 — a mesma colisão, agora com o Superpowers.** A editoria mandou desativar **só** a
> skill `brainstorming` do Superpowers e manter as demais: ela entrevista antes de agir, o que
> contraria a regra de não perguntar. O interruptor por skill não existe no plugin gerenciado — ele
> se desativa no `/plugin` da máquina da editoria, e é isso que falta fazer. Até lá vale a
> subordinação, pela mesma razão e com a mesma força do caso `karpathy-guidelines`: **se
> `brainstorming` carregar, este `CLAUDE.md` vence** e o trabalho segue sem entrevista — analisar,
> decidir, implementar, testar, verificar, corrigir, continuar. As outras skills do Superpowers
> (`systematic-debugging` e companhia) continuam valendo para qualidade de trabalho, não para a
> interação. Mesma regra para `Grill Me`, caso seja instalada algum dia.

## Preprint e site são rotinas SEPARADAS (editoria, 27/09/2026, §260)

O trabalho do preprint — as tarefas T0 a T11 do
`notas/PEDIDO_UNICO_CLAUDE_CODE_preprint.md`, no repositório privado — **não é rotina do site**.
As duas só se tocam quando a editoria disser que se tocam.

**O que não fazer, sem pedido explícito dela:**

- não rodar tarefa do preprint (T0–T11) por iniciativa própria, nem "aproveitar" que já se está no
  repositório;
- não abrir PR no repositório público a partir de achado do preprint;
- não acrescentar portão ao site por causa do preprint;
- não disparar rodada de atualização nem reposição de domínio para produzir dado de preprint;
- não criar worktree do repositório do site para análise de preprint — o clone do privado vive no
  rascunho da sessão, fora daqui.

**Onde o preprint vive:** `robo-registro/preprint/` (scripts e saídas) e `robo-registro/notas/`
(pedidos, estado, fichas). Nada dele entra no repositório público.

**Se uma tarefa do preprint encontrar defeito no site**, o caminho é: registrar o achado na saída
do preprint, no privado, e **levar à editoria como pedido separado**. Ela decide se vira mudança no
site. Foi assim que o §256 e o §257 deveriam ter nascido, e não nasceram — os dois vieram do T1 e
do T2 e viraram PR público direto, o que misturou as duas rotinas. Ficam como estão, porque
desfazê-los seria pior: o §256 é um portão que protege dado do site, e o §257 alinhou o texto da
metodologia ao código em vigor. Mas o caminho está corrigido daqui em diante.

**Quando a editoria pedir dado do preprint pela rodada**, ela diz. Até lá, a rodada serve ao site.

## Quem commita, mescla e publica (editoria, 30/09/2026)

**A central (chat) não commita, não mescla e não publica no repositório do site.** Todo código e
toda publicação passam exclusivamente pelo Code, a partir de handover; a central escreve o handover
e mais nada. A regra nasceu de três mudanças publicadas fora do fluxo (#451, #452, #453) — que
ficam como estão, revisadas e confirmadas, e não se repetem.

## Antes de explorar: o CODEMAP (30/09/2026)

`CODEMAP.md`, na raiz, diz **que arquivo afeta que tela, consome que dado e é coberto por que
portão**. Consultar antes de qualquer tarefa e **ler só o que ele lista** para o que a tarefa toca —
não reexplorar o repositório quando o mapa já responde. Ele é gerado por
`scripts/gerar_codemap.py`, nunca editado à mão, e um portão reprova quando envelhece.

O mapa é índice de primeira ordem, não análise de dependência: para "por onde começo a ler", basta;
para "nada mais pode ser afetado", quem responde continua sendo o portão de runtime.

## Fluxo de mudança (PROTOCOLO §3.1)

1. Partir da `main` atualizada; ramo `edicao/AAAA-MM-DD-tema`.
2. Editar com verificação de âncora antes de cada substituição.
3. Rodar os portões locais; nada sobe com portão vermelho.
4. Registrar no `CHANGELOG.md` — **entrada nova: `## AAAA-MM-DD · #PR · título`, no máximo 80
   palavras** (o quê · por quê numa frase · onde). Fundamentação longa vai para a
   `METODOLOGIA.md`. Sem `§` sequencial: ele colidia entre ramos abertos no mesmo dia.
   O histórico fica como está e, se cabível, em `METODOLOGIA.md`.
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

## O que NÃO se faz mais (itens 6 e 7 do handover de otimização, 30/09/2026)

Cada PR paga cerca de dez minutos de custo fixo — abrir, esperar a fila, mesclar. As regras abaixo
existem para não pagar isso à toa, e nenhuma delas afrouxa verificação:

- **Não reexplorar o repositório** quando o `CODEMAP.md` responde.
- **Não regenerar derivado dentro de PR de página**: o portão 12 no PR só confere que a cadeia
  regenera; quem sela o manifesto é o push para a `main`.
- **Não rodar portão que a mudança não pode afetar** — `scripts/quais_portoes.py` diz quais são.
- **Não escrever CHANGELOG longo**: 80 palavras, chave por data e PR. Fundamentação vai para a
  `METODOLOGIA.md`.
- **Não tirar captura à mão**: os portões de navegador as sobem como artefato do run.
- **Não abrir PR para uma frase.** Pedido pequeno de texto entra no próximo PR de página da fila, ou
  se junta a outros pequenos num só "ajustes de texto de dd/mm". **Exceção:** quando a editoria
  disser "publica isso agora".
- **Não redigir educação**: sem preâmbulo, sem ressalva de cortesia, sem explicar o óbvio. Só o
  relatório de até 6 linhas ao fim.

## Portões

**Antes do commit, rode só o que a mudança pode afetar:** `python3 scripts/quais_portoes.py` diz
quais são, pelo mesmo critério que a CI usa (`--comando` imprime a linha pronta). PR que só toca
`.py` de coletor não abre navegador; PR que só toca texto de página não roda portão de dado.


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

| arquivo | tamanho (medido em 05/10/2026) |
|---|---|
| `evidencias/` | **~4,1 GB** |
| `data/log_buscas/*.jsonl` | **~31 MB** no total, um arquivo por mês |
| `data/pistas_imprensa.json` | **~26 MB** |
| `data/fontes_consultadas.json` | ~12 MB |
| `data/financiamento/municipios/transferencias_uniao.json` | ~5 MB, e cresce todo mês |
| `data/verificacao_municipal.json` | ~3 MB |
| `data/log_buscas.json` | ~1 MB (o volume migrou para `data/log_buscas/`) |

Consulte sempre agregando (`python3 -c "import json,collections; ..."`), nunca com `Read`.
Um Read nos três primeiros estoura a sessão sozinho. Há hook que bloqueia acima de 1 MB em
`data/`, `dados-abertos/` e `evidencias/`.

**A tabela foi remedida em 05/10/2026, e três linhas estavam erradas de um jeito que importava.**
`evidencias/` figurava como ~380 MB e tem **4,1 GB** — dez vezes mais, no arquivo que a tabela existe
para proteger. `data/log_buscas.json` figurava como ~14 MB e tem **1 MB**: o volume migrou para
`data/log_buscas/*.jsonl`, que **não estava na tabela** e soma 31 MB. E `data/pistas_imprensa.json`,
com **26 MB**, também não estava — um `Read` nele estoura a sessão sozinho, e ele é tocado toda noite.
Números de tamanho envelhecem por rotina, como o de transferências já avisava; quem os citar
(inclusive a skill `noite-e-coletores`) cita **esta** tabela, e quem a vir defasada remede.

O de transferências entrou em 01/10/2026, a pedido da editoria: ele guarda nove meses de 2026 para
os 5.569 municípios, e **acumula um mês por mês, indefinidamente**. Entra aqui por trajetória, não
por tamanho de hoje — é o único da tabela que cresce por rotina, e esperar que ele incomode seria
descobri-lo numa sessão estourada.

## A corrente noturna: seis regras permanentes (editoria, 05/10/2026)

Nasceram da noite de 04→05/10, em que quatro defeitos se somaram: a publicação reprovou **oito
vezes** (21:23→03:57 BRT) e o site ficou com dado de 04/10; o elo dos diários foi **cancelado** dois
minutos depois de começar e a guarda contou aquilo como noite aberta, de modo que **ninguém refez a
coleta**; a busca web perdeu **114 minutos** de trabalho em conflito de rebase; e o pacote do blog
falhou por usar uma credencial que não alcança o repositório privado. Cada regra abaixo tem um portão
que a reprova — regra sem portão volta a ser esquecimento.

1. **Nenhum coletor grava pista fora de `scripts/pistas.py`.** A fila tem uma porta: ela normaliza
   para `schemas/pista.json`, classifica o `tipo`, valida e **recusa com motivo** em
   `data/pistas_rejeitadas.json`. Entrada de pista nova vai por `gravar`, `gravar_lote` (uma escrita
   por rodada) ou `sincronizar` (varredura longa, com salvamento parcial). Operação sobre a fila
   inteira — limpeza, triagem, união de conflito — declara-se em `MANUTENCAO`, por escrito.
   Portão: `scripts/verificar_escritor_de_pista.py`.

2. **Um escritor por arquivo, ou uma resolução declarada.** `config/escritores.json` diz, para cada
   arquivo compartilhado da corrente, quem pode commitá-lo. Quando vários elos commitam o mesmo
   arquivo, a corrida tem de estar **resolvida** — uma classe de
   `scripts/unir_conflito_de_rodada.py` — ou o arquivo declara `pendente` dizendo o que falta
   decidir. Portão: `scripts/verificar_escritores.py`.

3. **Cancelado e pulado nunca contam como feito.** A guarda "esta noite já abriu?" conta só o run
   que **trabalhou**: `in_progress`, ou `success`/`failure` com o marcador
   `data/noite/<noite>/<elo>.feito` que o elo grava **depois dos comandos e antes do commit**. Elo
   que coletou e perdeu o push trabalhou — refazê-lo duplicaria lote e commit. Elo cancelado antes
   de coletar não trabalhou, e a reserva refaz. Quem decide é `painel_da_noite.trabalhou`.

4. **Nenhum script cancela run de outro.** Conferido por varredura: não há `gh run cancel` nem
   chamada de cancelamento na árvore. Grupo de concorrência é fila, nunca cancelamento —
   `cancel-in-progress: false` em todo elo; só o publicador cancela o anterior, porque publicar duas
   vezes o mesmo estado não tem valor.

5. **O portão de esquema quarentena; ele não bloqueia a publicação.** Pista fora do esquema sai da
   fila ativa pela mão do próprio portão, marcada e contável por coletor, e a publicação segue.
   Bloqueio só quando a quarentena **falha** — aí o dado malformado seguiria a caminho do juiz.
   Parar o site inteiro por sobra de coletor é desproporcional; deixar sobra ir ao índice, não.

6. **Toda mudança na corrente noturna passa pelo ensaio da noite.** `scripts/ensaio_da_noite.py` e
   `.github/workflows/ensaio_da_noite.yml` rodam a noite em miniatura, de dia, em repositório
   temporário, e reprovam quando qualquer uma das quatro causas volta: conflito entre elos que perde
   pista, disparo duplicado que duplica trabalho, elo cancelado que não é refeito, pista fora do
   esquema que para a publicação. **Mudança na corrente sem ensaio verde não entra.**

## A corrente noturna, parte 3: o que mudou em 06/10/2026

As seis regras acima continuam. Estas sete saíram das **cinco causas confirmadas** pela editoria no
código e nos logs — não de suposição:

7. **Commit pelo ajudante, só dos próprios arquivos, no ramo em que roda.**
   `scripts/commit_do_elo.py` põe no índice só o que `config/escritores.json` dá ao elo.
   `git add -A`, `git add .` e `git add <pasta>/` são **proibidos** em qualquer workflow desta
   árvore, e `HEAD:main` escrito à mão também — empurra-se para o ramo em que o workflow roda.
   Portão: `scripts/verificar_commit_do_elo.py`.

8. **Nenhuma fusão de três vias em arquivo compartilhado pelos elos.** O elo guarda as próprias
   saídas fora do repositório, e a cada tentativa parte do ramo mais novo e reaplica só elas —
   arquivo de dono único por cópia, fila pela porta (`pistas.sincronizar`). O laço antigo refundia
   o que já fora fundido, e `data/pistas_imprensa.json` foi de 28 MB a 187,53 MB num único run.
   `scripts/unir_conflito_de_rodada.py` fica para uso manual.

9. **Trava de 50 MB e 20%.** Nenhum arquivo versionado passa de 50 MB — metade do limite do
   GitHub, porque quando o GitHub recusa a coleta da noite já se perdeu — e nenhum cresce mais de
   20% numa execução. Portão: `scripts/verificar_tamanho_dos_dados.py`, e a mesma trava roda antes
   do push de cada elo.

10. **O publicador regenera os derivados antes de conferir**, e o **CODEMAP fica fora** do
    publicador de dados: ele é documentação de código, e como cada commit de dado muda o que o mapa
    conta, cobrá-lo ali reprovava toda publicação. Quem o cobra é o portão de PR.

11. **Na `main`, coleta só dentro da janela** (01:00–09:00 UTC, 22h–06h de Brasília). `cron` certo
    não impede disparo manual, cadeia de `workflow_run` nem reexecução de run antigo — a guarda é
    `scripts/guarda_da_janela.py`, e ela para em SUCESSO. De dia a coleta roda no ramo `ensaio`. O
    publicador é a exceção única, quando a editoria chama.

12. **Ensaio REAL isolado, obrigatório para qualquer mudança na corrente.** O ensaio em miniatura
    prova os mecanismos e não passa pelo passo de commit real de cada elo — que é onde a noite se
    perdeu. `scripts/ensaio_real_da_noite.py` dispara os workflows de verdade no ramo `ensaio`, com
    elos em paralelo e conflito plantado, e recusa rodar fora dele.

13. **Trabalho que o push perdeu volta.** O elo grava `data/noite/<noite>/<elo>.pendente`, o
    artefato leva as saídas, e o elo seguinte reaplica o que tem política declarada. O que não tem
    continua pendente e **nomeado** — reaplicar sem política apagaria dado.

**Nunca unir arquivo que só cresce por conteúdo.** Vale para log e para fila: une-se pela **base
comum** (`base + nossos_novos + deles_novos`), e o total final é maior ou igual a cada lado. Em
23/09/2026 uma união por conteúdo produziu um log menor que cada lado e apagou quase 3.000
execuções. Nas filas de pista a política é a da porta: acréscimo dos dois lados entra, campo que só
um lado tocou entra, **mesmo campo com valores diferentes é recusado** em vez de adivinhado.

## Log append-only: merge pela base comum

`data/log_buscas.json` e `data/historico_mudancas.json` só crescem. Quando os dois lados
acrescentam e o merge conflita, **nunca deduplique por conteúdo**: execuções idênticas no
log v2 são tentativas reais distintas e contam. Una pela base comum
(`base + nossos_novos + deles_novos`) e confira que o total final é **maior ou igual** a cada
lado. Em 23/09/2026 uma união por conteúdo produziu um log menor que cada lado — quase 3.000
execuções apagadas sem aviso. Use `/merge-main`.

## Duas regras editoriais que valem para todo o site (editoria, 03/10/2026)

**1. Dizemos o que disponibilizamos; nunca o que não disponibilizamos.** Onde couber: "A
metodologia é pública." Ponto. Mapas e gráficos podem ser reproduzidos com crédito. Recortes,
cruzamentos e gráficos sob medida pelo e-mail da imprensa. **Nenhuma frase** sobre código, base de
dados ou licença de dados — nem "não distribuído", nem "CC BY" aplicada a dados, nem "dados
abertos". A página da **metodologia** é o único material técnico público.

Saíram do site: a página de dados abertos e todos os links para ela, as planilhas de edição e de
números, os arquivos de consultas (endereços, hashes) e as tabelas de auditoria. Eles continuam no
repositório e nas notas — internos.

**2. Blog = acontecimentos do ciclo, em prosa.** O blog não trata de decisões, método, correções
nem funcionamento do site: isso vive na metodologia e em `mudancas.html`. Cada texto conta uma
condição do ciclo como história de fatos — onde, quando, quanto, quem, com fonte —, em **texto
corrido, sem tópicos, sem listas e sem cartões no meio do texto**. Escrito por pessoa: a central
redige, a editoria aprova, e o Code publica só o que estiver em `robo-registro/blog/` com
`aprovado: sim`. Nada gerado automaticamente vai ao ar como texto do blog.

## Blog: pacote, aprovação e verificador (editoria, 04/10/2026)

**Texto do blog só existe com três coisas: pacote da semana, aprovação da editoria e verificador
verde.** Dois textos por semana, em prosa — *Legal e financiamento* (pacote de domingo, texto na
segunda) e *Saúde* (pacote de quarta, texto na quinta); *Acontecimento* só quando algo grande
ocorrer. A etiqueta *Boletim* saiu.

- **O Code não escreve, não edita e não aprova texto do blog.** `robo-registro/blog/*.md` é
  território da central; o guia dela é `blog/GUIA_DE_REDACAO.md`, que o Code não edita.
- **`gerar_pacote_blog.py`** produz o pacote da semana em `robo-registro/blog/pacotes/`: só
  contagens, somas, listas alfabéticas, datas e documentos, cada fato com fonte, URL e data de
  consulta. Nenhum ranking, nenhuma razão entre números. Dado com mais de nove dias vira lacuna
  declarada, não fato.
- **O pacote gerado pelo workflow fica no ARTEFATO do run** (editoria, 05/10/2026). O
  `pacote_do_blog.yml` não empurra nada ao `robo-registro`: a pergunta foi feita — levar o pacote ao
  privado, ou deixá-lo no artefato? — e a editoria escolheu o artefato. Não é limitação técnica
  contornada: `ROBO_TOKEN` já alcança o privado e o push sairia de graça. Para ter o pacote em
  `robo-registro/blog/pacotes/`, roda-se o gerador à mão, que é o caminho normal da central. O
  artefato expira em 90 dias; pacote não baixado se regera pelo mesmo comando, com os mesmos dados,
  porque o gerador é função do corte e não do run.
- **`scripts/verificar_texto_blog.py`** roda antes de publicar: todo número e toda data do corpo
  tem de estar no pacote. Texto reprovado **não vai ao ar e não bloqueia o site**. Se o texto está
  certo e o número não está no pacote, **o pacote está incompleto** — corrige-se o gerador, nunca
  o texto.

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
