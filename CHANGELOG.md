# Changelog · Monitor El Niño Brasil / Índice MARÉ

Formato inspirado em [Keep a Changelog](https://keepachangelog.com/pt-BR/).
Cada entrada aqui é um resumo escaneável; a justificativa completa, com
fundamentação teórica e dados de impacto, vive em `METODOLOGIA.md` (a fonte
de verdade), datada seção a seção. Convenção deste projeto: mudança que
altera pesos, créditos ou componentes do índice exige **versão maior**
(regra de governança registrada em `METODOLOGIA.md` §12); expansão de
documentação, novos portões de verificação e reconhecimentos editoriais
não pontuados permanecem na versão corrente.

## §319 · Regras do ciclo no CLAUDE.md, e a medição que dirá se elas funcionaram · 30/09/2026

Classe **processo**. Itens 6, 7 e 8 do handover de otimização.

**As sete regras** entraram no `CLAUDE.md`, numa seção própria: não reexplorar quando o CODEMAP
responde · não regenerar derivado em PR de página · não rodar portão que a mudança não afeta · não
escrever CHANGELOG longo · não tirar captura à mão · **não abrir PR para uma frase** (entra no
próximo de página, ou junta-se a outros pequenos; exceção: "publica isso agora") · não redigir
educação.

**A medição (item 8)** lê os PRs mesclados pela API e grava em `data/saude_pipeline.json`: minutos do
primeiro commit ao merge, por tipo de PR, e rodadas de CI. Usa **mediana, não média** — um PR que
dormiu esperando a editoria não é um ciclo de oito horas, e a média deixaria esse caso mandar no
número.

**A primeira medição é desconfortável, e fica registrada como saiu:** página **53,7 min** (meta 20),
coletor **64,8 min** (meta 15), misto 86,7 min. O único número já dentro da meta é o das rodadas de
CI: **mediana 1, nenhum PR com mais de uma**. Ou seja, os 12 PRs medidos são de **antes** dos itens
1 a 5 valerem — esta é a linha de base contra a qual a próxima rodada vai ser comparada, não um
resultado deles. 18 casos de autoteste.

## §315 · A cobertura do Querido Diário, conferida município a município · 30/09/2026

Classe **método e prova**. Primeira passagem completa da rotina do §312, rodada até o fim.

**5.571 municípios, 4.292 consultados nesta passagem**, os demais já cobertos (que não se
reconsultam, porque edição indexada não desaparece). **Resultado: nada mudou** — 527 indexados
antes, 527 depois, nenhum passou a indexado, nenhum deixou de ser. O retrato antigo estava certo; o
que faltava era **saber que ainda estava**, e agora 4.292 municípios carregam a data da conferência
em vez de um carimbo de três semanas atrás.

**754 consultas falharam (13,5%)** e, como a rotina manda, **preservaram o valor e o carimbo
anteriores** em vez de virar ausência. Elas voltam à fila na próxima rodada semanal.

**Os três "indefinidos" acabaram, e por uma razão que vale registrar.** Eram municípios cuja marca
no log é ilegível; a sondagem do acervo, agora, **sabe** a resposta. Marca de log que ninguém
consegue ler não é prova de nada — a sondagem é. `recalcular_mare.py` passou a preferir a cobertura
nesse caso, e **só nesse**: cobertura `true` com log ilegível significa "indexado e não lido", que
não é `sem_cobertura_qd` e segue indefinido. O contador independente aprendeu a mesma regra **lendo
a fonte**, não copiando o código do produtor, que é o que mantém a recontagem independente.

Números publicados: 260 com menção · 200 lidos sem menção · 67 sem edição na janela · **5.044 sem
diário indexado** · **0 indefinidos** · 527 indexados. Nenhum peso, crédito ou régua mudou.

## §314 · O portão 12 saiu do caminho dos PRs — e passou a cobrar na `main` · 30/09/2026

Classe **processo**. Item 2 do handover de otimização.

O manifesto sela o hash de **todo** arquivo versionado, então qualquer mudança o deixa obsoleto.
Cobrar isso dentro do PR forçava "regenerar + commitar + esperar a CI de novo" em quase toda
entrega, e o manifesto commitado no ramo conflitava com o do `main` a cada união — aconteceu em
praticamente todos os PRs de 29 e 30/09.

**No PR**, o portão 12 passa a conferir que a cadeia inteira **regenera sem erro** (`--pode-regenerar`):
falha se um gerador quebrar, que é o defeito que o PR pode introduzir. **Na `main`**, ele roda como
sempre rodou, com comparação estrita contra o git.

Para isso a suíte passou a rodar também **no push para a `main`**, e não só em PR. Sem essa linha,
tirar a cobrança do PR a tiraria do projeto inteiro — o que **não** é o que o item 2 pede, e seria
trocar um custo por um buraco. Derivado obsoleto continua sendo bloqueio; o que mudou é **onde** se
cobra, não **se** se cobra.

## §313 · CODEMAP: o mapa que evita reexplorar o repositório a cada pedido · 30/09/2026

Classe **processo**. Item 1 do handover de otimização do ciclo de mudança.

O custo maior de cada pedido não é rodar portão: é **descobrir de novo o que a mudança toca**. São
99 scripts Python na raiz, 36 portões e dez páginas; achar "quem lê `data/municipios.json`" por
busca custa minutos, toda vez, e o achado se perde no fim da sessão.

`CODEMAP.md` responde de uma vez: **123 arquivos**, cada um com as telas que afeta, os dados que
usa, os portões que o cobrem e se toca o índice. É **gerado do próprio código** — dos `fetch(...)`,
dos `gravar(...)` e das listas de páginas dos portões — porque mapa escrito à mão envelhece em
silêncio, e **mapa que mente é pior que mapa nenhum**: manda ler o arquivo errado com a confiança de
quem conferiu. Um portão reprova quando ele envelhece; a suíte vai a **125**.

**Três coisas que o gerador só acertou depois de medir contra o repositório real.** (a) `index.js`
não escreve o nome de cada arquivo: monta `fetch('data/' + f + '.json')` sobre uma lista — sem ler
esse idioma, o mapa dizia "—" justamente na página mais carregada do site. (b) O `src` dos scripts
leva `?v=hash` de cache-busting, e exigir o fecho de aspas logo após o `.js` fazia o mapa não achar
script nenhum. (c) Nem todo script da página vive em `assets/js/` — `acesso.js`, `mapas.js` e
`colunas.js` estão em `assets/`. Agora a linha de `index.html` lista os **30** dados que ele consome.

**O que o mapa não promete**, e está escrito nele: não é análise de dependência: não segue `import`
transitivo nem chamada dinâmica. Para "por onde começo a ler", basta; para "nada mais pode ser
afetado", quem responde é o portão de runtime. A regra de consultar antes de explorar entrou no
`CLAUDE.md`. 28 casos de autoteste.

## §311 · Formulário mínimo: o site deixou de coletar dado pessoal · 30/09/2026

Classe **página pública** e **privacidade**. Design "C" escolhido pela editoria.

**O formulário ficou compacto e sem etapas.** Sem numeração, sem borda de *fieldset*, sem a coluna
lateral fixa: quatro campos sempre visíveis (estado, município, tipo do documento, link em fonte
oficial) e os opcionais — número do ato e observações — atrás de um `<details>` fechado. O painel usa
o mesmo espaçamento dos outros da página, como a editoria pediu.

**O campo de e-mail saiu do HTML, e com ele o último dado pessoal do site.** Não virou opcional nem
escondido: sumiu. A interface passou a dizer isso ao leitor, com a frase que a editoria fixou
palavra por palavra: *"Não pedimos seu nome nem contato, só as informações sobre o documento. A
conferência é feita pela nossa equipe."*

**As três dependências foram atrás, não só o campo.** `verificar_contribuicoes.py` **continua lendo**
`email_contato` — de propósito: submissões antigas ainda o têm, e deixar de ler quebraria o
histórico; nas novas ele chega vazio. `docs/LGPD_PRIVACIDADE.md` **não foi apagado**: continua como
registro de auditoria do que existiu e passou a declarar, datado, que **o formulário não coleta
nenhum dado pessoal** desde 30/09/2026, valendo o fluxo descrito só para o que foi enviado antes.
`obrigado.html` foi conferido e não promete contato de volta.

**O campo de município também nasce desabilitado aqui**, como no cartão da cidade: digitar município
antes do estado mandava um nome que a lista não podia validar.

**A notificação por e-mail não é código do repositório, e a tentativa foi até onde dá.** Ela vive na
conta do Netlify e exige o `NETLIFY_AUTH_TOKEN`, que **só existe como segredo do GitHub**. Então
entrou um workflow por botão (`notificacao_formulario.yml`) e o script que ele chama: confere se já
existe notificação para o formulário, **não duplica** se existir, cria se faltar, e **falha com o
erro exato** se a API recusar — porque o caminho manual só serve se a editoria souber que precisa
fazer. O destino é conferido contra o endereço confirmado, `monitorelnino@gmail.com`: houve
divergência de grafia no pedido original, e notificação para caixa errada é pior que nenhuma —
parece configurada e não chega. 11 casos de autoteste.

**Um defeito do próprio portão 19, exposto pela frase da editoria.** A checagem de ênfase
("só/única/nunca/sempre") lia o texto **cru**, sem passar pelas exceções declaradas que a checagem
irmã já usava: o mesmo portão lia o mesmo texto de duas maneiras. Agora as duas passam pela mesma
lista, e a frase de privacidade entrou nela **inteira** — não a palavra "só", que se alargaria para
todo o site. Mudar a frase faz o portão voltar a reprovar, que é o comportamento certo.

## §312 · Cobertura do Querido Diário: a fonte estava errada, e a rotina não existia · 30/09/2026

Classe **método e prova**. Item 6 da fila viva, achado pelo exemplo de Abatiá/PR.

**O retrato envelhecia sem avisar.** `data/cobertura_qd.json` guardava o resultado de uma busca de
edições **com janela de data**, carimbada no dia do teste: em 30/09 o arquivo ainda trazia 1.859
municípios testados em 09/09 e 2.362 em 12/09. Isso mistura duas coisas diferentes — município sem
diário no Querido Diário e município com diário que não publicou naquela janela — e o acervo do
projeto **cresce**, de modo que o "não" de três semanas atrás pode ser um "sim" hoje.

**Uma ideia foi testada e descartada antes de virar dado publicado.** O diretório oficial
(`/api/cities/`) traz o nível de cada município e responderia o país inteiro em **uma** requisição.
A conferência derrubou: dos 17 municípios que o nível rebaixaria, **16 têm edição indexada de fato**
— Areal/RJ com 3.426 edições em nível 1, Comendador Levy Gasparian/RJ com 3.471 em nível **0**, São
Paulo com 20 em nível 1. O nível descreve o estágio do projeto de raspagem, não a existência do
acervo; publicá-lo teria apagado cobertura real de dezesseis municípios. O nível ficou gravado como
informação (`nivel_qd`) e **não decide nada**.

**O veredito é a pergunta direta ao acervo:** existe alguma edição para este município, **sem janela
de data**. Uma consulta por município, o que só se faz porque a resposta **não precisa ser refeita
para quem já está coberto** — edição indexada não desaparece. A rotina semanal reconsulta só os
`false`, que é onde o acervo cresce, e por isso fica mais barata a cada semana.

**Três travas que a própria execução exigiu.** (a) **Falha não vira ausência**: consulta que erra
preserva o valor anterior e o carimbo antigo, e registra a falha — API fora do ar não é diário
inexistente. (b) **Universo curto não escreve**: a primeira execução usou `municipios.json` (os 267
registros pontuáveis) como se fosse o país, varreu 267 e declarou 5.304 "ausentes do diretório";
agora o universo vem de `verificacao_municipal.json` e menos de 5.000 códigos levanta erro. (c)
**Progresso que só existe na memória não é progresso**: a varredura seguinte rodou horas, travou numa
requisição pendurada e **não escreveu nada** — o trabalho de milhares de consultas evaporou. Passou a
gravar a cada 100 municípios, e retomar é reler o arquivo.

**Abatiá/PR, conferida nominalmente:** o acervo devolve **zero edições** — o município de fato não
tem diário indexado. O valor de 09/09 estava certo; o que faltava era **saber que ainda estava**.
Essa é a diferença que a rotina passa a garantir.

**A primeira passagem completa roda no ciclo semanal**, onde a rede é rápida e o job tem teto
próprio. Localmente, o ritmo medido (com cerca de um terço de tempos esgotados) daria mais de dez
horas, e ficou registrado em vez de disfarçado. 45 casos de autoteste.

## §310 · O cartão do município ficou mínimo: quatro coisas, nada mais · 30/09/2026

Classe **página pública**. Decisão de design da editoria — redesenho do conteúdo, não outro ajuste
incremental sobre o §304.

**O que o cartão mostra agora, e só isto:** se o plano foi localizado; o **risco do estado**, no
mesmo componente da ficha (`riscoBox()`, reaproveitado, não duplicado); o **link do documento**
quando há; e o **convite ao formulário** quando não há.

**O que saiu:** botão de PDF, contatos de emergência, alerta por SMS, órgão estadual e e-mail, link
de financiamento, diretório do MIDR, decreto de emergência do município, nível de verificação,
status do diário oficial, população, vigência, conteúdo do decreto, canal da fonte, guias de
proteção por risco, aviso do FGTS, formulário de correção e todo o bloco "o que fazer e o que
cobrar". O cartão respondia a perguntas que ninguém fez ali, e a que importa — *minha cidade tem
plano?* — se perdia no meio.

**O mapeamento de categoria está declarado, não espalhado.** Encontrado: `plano`, `plano_novo`,
`plano_readaptado`, `plano_recorrente`, `plano_antigo`; `coberto_estadual` entra como encontrado,
com uma palavra a mais dizendo que o plano é do estado. Não encontrado: `nao_localizado`,
`nao_verificado`, `plano_elaboracao`, `nao_el_nino` e **`decreto`** — decreto de emergência é
resposta, não preparação, e a metodologia nunca os confundiu. Quem revisar a regra lê duas listas,
não um emaranhado de condições.

**Uma trava de prova venceu o desenho, e está certo que tenha vencido.** A primeira versão dizia "não
localizamos" para todo município sem plano — inclusive para os que **ninguém procurou**, que são a
maioria dos 5.571. O portão de linguagem (§6, v2.2.4) reprovou, e com razão: afirmar busca que não
houve é exatamente o que o teto público de ausência proíbe. Agora "não localizamos até o corte" sai
só onde a busca ocorreu (`nao_localizado`); o padrão é "ainda não verificamos com todas as fontes".

**O campo de município nasce desabilitado** e só abre quando há estado — mesmo padrão de
`prefeituras.html`. Com isso, o ramo de nome ambíguo em mais de um estado deixa de ocorrer pelo
caminho normal; ficou uma frase mínima para quem digitar sem usar a lista.

**Título e texto do painel acompanharam o corte:** prometiam decreto, nível de verificação e "o que
fazer", que saíram. Promessa que o cartão não cumpre é defeito, mesmo quando o cartão está certo.

**O gerador do relatório não foi tocado** — sumiu a chamada a ele neste cartão, e um portão novo
cobra as duas coisas: que o botão não volte e que `gerarRelatorioCidadao()` continue no código.
Três verificações que cobravam contatos, PDF e decreto no cartão passaram a cobrar a ausência deles
e a presença do cartão novo.

Nenhum peso, crédito, régua ou categoria do índice mudou.

## §305 · A frase-resumo de preparação saiu da página inicial · 30/09/2026

Classe **página pública**. Item 4 da fila viva.

"N estados com plano para o ciclo; N com plano de todo ano; N sem plano localizado. Por região: X
concentra os planos feitos para o ciclo (N de N)." saiu de baixo dos dois medidores: o bloco que a
preenchia em `assets/js/index.js` e o `<p id="resumoPreparacao">` em `index.html`. É a segunda
mudança de casa da frase — ela veio de `defesa-civil.html` em 18/09 — e agora ela não se recria em
nenhum outro lugar sem pedido novo.

`verificar_runtime.js` **cobrava a existência** do texto, com as três contagens somando 27. Passou a
cobrar a ausência: portão que cobra o que foi removido reprova por estar certo, e portão que não
cobra a remoção deixa ela ser desfeita sem ninguém ver.

> **Nota sobre o item 5 da mesma fila.** Ele foi entregue pelo §304 (#453) enquanto este trabalho
> corria noutro ramo: a inicial já não abre nada ao escolher só o estado. A versão que eu tinha em
> ramo próprio removia também o bloco `if (ufFinal){...}` inteiro, como o handover pedia no passo 2,
> e foi **descartada** em favor do que já está na `main` — refazer decisão recém-mesclada para
> ganhar a diferença entre os dois desenhos custaria mais do que vale. Fica registrado que, no
> desenho em vigor, o retrato estadual continua sendo montado **quando há município**, e que os
> contatos de emergência e o botão de PDF seguem nele.

Nenhum peso, crédito, régua ou categoria mudou.

## §309 · O calendário saiu de vez do código — as três telas, não uma · 30/09/2026

Classe **página pública**. Decisão da editoria de 30/09/2026 à noite, **mais forte que a anterior**:
não é arquivar, é apagar. O §306 (PR #455), que implementava o arquivamento, foi **fechado sem
mesclar** — corrigir o que ele fazia seria consertar a resposta a uma pergunta que mudou.

**Eram três telas, não uma.** A página do calendário eleitoral (`calendario-eleitoral.html` e o JS
dela), o painel "Calendário" da inicial (bloco `#prazos` e a função `calendario()` de `index.js`, 87
linhas) e o calendário compacto da página de imprensa. As três saíram, e com elas o que só elas
consumiam: `data/marcos_ciclo.json`, `data/prazos_uf.json`, `data/calendario/dispositivos.json`, o
gerador `verificar_prazos_legais.py`, as chamadas dele em dois workflows e o portão
`scripts/verificar_calendario.js`. A suíte vai de 124 a **121**.

**O conhecimento migrou antes de o código sumir.** Os quatro marcos do ciclo — 1º turno 04/10;
fim do período eleitoral 25/10; o que o Monitor publica em 26/10; janela crítica do El Niño
01/10/2026–31/03/2027 — estão na `METODOLOGIA.md` §24, como texto fixo e datado, com a fonte de cada
linha. **A tabela de dispositivos da Lei 9.504 não foi duplicada, e isso foi conferido antes de
apagar:** o §24 já trata da mesma norma, com trecho e fonte, desde 02/09/2026, e repetir a mesma lei
em dois lugares do mesmo documento cria duas versões que envelhecem em ritmos diferentes. Uma nota
interna em `robo-registro/notas/` guarda o porquê, o que havia e onde cada coisa foi parar, com o
JSON dos dispositivos preservado ao lado.

**O que NÃO saiu, e é a parte que importa.** O **motor do defeso** continua inteiro: `DEFESO` e
`FRASE_C18` em `gerar_resposta.py`, os lotes de `atualizar.py`, `PADROES_DEFESO` em
`coletores_base.py`, e os outros dezessete scripts que consultam o período eleitoral para decidir o
que coletar e como ler fonte fora do ar. Isso nunca foi calendário — é o que faz o §24 funcionar, e
é o que vai liberar, em 26/10, a publicação do que o período eleitoral escondeu. Ficou também a
faixa do período eleitoral no gráfico de financiamento: anotação de data num gráfico de outro
assunto, não uma tela de calendário.

**Os portões acompanharam a remoção, e duas travas novas nasceram dela.** Nove verificações do painel
da home saíram de `verificar_runtime.js` — não foram afrouxadas, deixaram de existir junto com o que
mediam — e a ordem da home passou a terminar no formulário. No lugar entraram duas que cobram o
oposto: **nenhuma tela de calendário voltou à home** e **nenhum link para a página apagada
reapareceu**. Sem elas, um `revert` distraído devolveria link morto ao ar sem ninguém ver.

Quatro links foram removidos com as frases reescritas (inicial, imprensa, financiamento,
prefeituras), mais a entrada do `sitemap.xml`. Nenhum peso, crédito, régua ou categoria mudou.

## §307 · Os sinais físicos tinham virado semanais sem ninguém decidir isso · 30/09/2026

Classe **defeito de cadência**. Item 1 da fila viva — e, dentro dele, o item **2b**, que era o único
que faltava: focos por ponto, card do INMET, grade de três e a saída do quadro de fontes já tinham
entrado no §294.

**O que a decisão dizia.** Em 29/09/2026 a editoria determinou que os sinais físicos do Monitor de
riscos — avisos do INMET, focos do INPE, seca, temperatura, ar — são diários na fonte e **nenhum
deles pode cair na cadência semanal**, com a razão escrita: "sem isso, o card de avisos e o mapa de
focos ficam bonitos e desatualizados, que é pior do que o quadro que está saindo". O handover mandava
**confirmar** que os dois entravam nas quatro coletas diárias do `atualizar.yml`.

**A conferência derrubou a premissa.** Não há mais quatro coletas diárias: o desacoplamento do item
1b tirou o `schedule` diário do monólito e o deixou só no domingo. `coletar_sinais_risco.py` ficou
vivo apenas no `semanal_sinais_e_links.yml`, que roda **domingo às 4h30**. Ninguém decidiu isso: foi
efeito colateral de outra mudança, e não havia nada que reprovasse. A própria página mostrava o
resultado — as cinco figuras carimbavam "atualização: 26/09/2026" em 30/09. Um aviso de perigo do
INMET com sete dias de atraso não é sinal, é arquivo, e o card diria "em vigor" sobre aviso que
expirou na terça.

**O conserto.** `noturno_sinais.yml` roda `coletar_sinais_risco.py` todo dia às 5h de Brasília, dentro
da janela noturna e pouco antes do publicador que a fecha, de modo que o site publicado de manhã
leve o sinal da noite. O publicador passou a escutá-lo. O clima municipal (5.570 municípios,
temperatura e ar) **não** veio junto: ele tem teto diário de localidade no Open-Meteo, alterna a
variável por rodada e continua onde essa lógica mora.

**A trava.** `scripts/verificar_cadencia_sinais.py` exige que **algum** workflow com cron diário
chame o coletor. Ele trava a propriedade, não o arranjo: se a coleta mudar de arquivo amanhã, o
portão continua valendo. Sem ele, a mesma regressão volta do mesmo jeito — de lado, sem decisão, sem
aviso. 16 casos de autoteste.

Nenhum dado do índice muda: sinal físico tem peso zero.

## §308 · Cabeçalho da inicial em duas colunas: logo e título à esquerda, descrição à direita · 30/09/2026

Classe **página pública**. Item 2 da fila viva — opção **B** das três que a editoria viu.

O cabeçalho empilhava o logo e, abaixo, uma grade de duas colunas de peso igual com título e
descrição lado a lado. Agora são duas colunas: à esquerda o logo com o título **logo abaixo dele**,
como um bloco só; à direita a descrição, **centrada verticalmente** em relação a esse bloco.

**O logo não mudou, e isso foi conferido, não suposto.** O `<svg>` inteiro — `viewBox`, as linhas da
régua, o `<text>` "MARÉ", o `<path>` da onda e o gradiente `mareLogoAgua` — é **idêntico caractere a
caractere** ao de antes (1.174 caracteres, comparados contra a versão anterior); a única diferença no
diff daquela linha é a indentação, porque o `<h1>` passou a viver dentro da coluna. A onda faz parte
do desenho e não foi separada, recortada nem duplicada.

**CSS:** a coluna da marca recebe `minmax(0,540px)` e o resto vai para a descrição, com o mesmo
token de `column-gap` que a abertura já usava; `align-items` passou de `start` a `center`, que é o
que centra a descrição no bloco logo+título; o título ganhou `margin-top: var(--sp-4)` e perdeu o
`max-width:14ch`, que existia para a antiga coluna estreita. **Nenhum token novo de cor ou
tipografia** — só `--fs-*`, `--sp-*`, `--font-titulo`, `--ink` e `--muted`, todos já em uso.

Em telas estreitas as duas colunas empilham, como a abertura já fazia: logo e título acima,
descrição abaixo. Conferido a 390 px — o logo não ultrapassa a largura da tela e não há rolagem
horizontal. `masthead--mini` (páginas internas) **não foi tocado**, e o resto do masthead — kicker,
nav, `mast-body`, `.grad-line` — segue onde estava. Nenhum texto mudou.

Portões verdes, inclusive consistência visual e o de telas pequenas. Capturas em desktop, tablet e
mobile no PR.

## §304 · Erro estrutural: escolher só o estado não abre mais nada em "Sua cidade" · 30/09/2026

Classe **defeito** e **método e prova**. Decisão da editoria de 30/09/2026, implementada diretamente (fora do fluxo do Claude Code).

No painel "Sua cidade" da inicial, escolher o estado sozinho, sem digitar o município, já abria um
cartão com o retrato do estado — medidor do MARÉ e a lista de status (instrumento operacional,
estrutura de coordenação, cobertura documentada). Isso duplicava a ficha do estado (janela de
detalhe da grade "O MARÉ Legal por estado", que já mostra os três) e ficava desatualizado por
viver em dois lugares.

Correção: `renderMinha()` agora exige sempre o município para mostrar qualquer coisa (antes, `uf`
sozinho já bastava). O retrato do estado — medidor e lista de status — saiu de vez. O que não
duplicava a ficha continua: contatos de emergência, alerta por SMS, contato do órgão estadual, o
link de financiamento, o botão de baixar o relatório em PDF, os guias de proteção por risco, o
aviso do Saque Calamidade do FGTS e o formulário de correção — nada disso existe na ficha, e nada
foi removido. `STATUS_HUMANO_ESTR`, que só alimentava o trecho removido, saiu como código morto.

`assets/js/index.js`. Portões locais (os mesmos 17 do §303, incluindo os testes específicos de
"PDF do cidadão" e "resumo de preparação") rodados e verdes antes do commit.

## §303 · Cartões de estado: mais compactos, sem risco na frente, sem ponto de capital · 30/09/2026

Classe **design**. Decisão da editoria de 30/09/2026, implementada diretamente (fora do fluxo do Claude Code).

A grade "O MARÉ Legal por estado" tinha ficado grande demais para a informação que carrega. Quatro
mudanças, todas de apresentação — nenhuma nota, peso ou dado muda:

- A frase explicativa sob o título saiu; o título "O MARÉ Legal por estado" já basta.
- A grade ficou mais compacta (padding e espaçamento menores, largura máxima menor).
- O risco projetado do estado (entrado no cartão em 27/09) saiu da frente do cartão e passou a
  viver só na ficha (janela de detalhe), num bloco destacado com acento de cor por família de risco
  (chuva/seca/fogo), os componentes como etiquetas e a fonte do Painel El Niño.
- O ponto de "capital verificada" no canto do cartão saiu, com a linha correspondente da legenda.

`index.html`, `assets/js/index.js`, `assets/base.css`. Portões locais (estrutura, runtime e as
variantes, acessibilidade, vocabulário público, voz editorial, figuras, fichas semânticas,
legendas, palavras, segurança, SEO) rodados e verdes antes do commit.

## §302 · Falso negativo se trata como falso negativo: nenhuma exceção por domínio no código · 30/09/2026

Classe **método e prova**. Decisão da editoria de 30/09/2026 sobre a pendência aberta no §301.

`abcdoabc.com.br` é jornal de verdade — o expediente se declara portal de notícias — e não passa
pelos sinais de entrada no que a sonda consegue abrir. A editoria decidiu: **tratar como falso
negativo conhecido, sem exceção nomeada.**

Duas coisas entram por causa disso. A primeira é o registro no próprio veículo, em
`data/veiculos_imprensa.json`, com data, sinal que falhou, motivo e a decisão — falso negativo
anotado é dívida visível; falso negativo esquecido é só um número errado que ninguém sabe explicar
depois. A segunda é um **canário que proíbe a exceção**: ele lê o código-fonte das sete funções do
caminho de decisão e reprova se aparecer qualquer domínio literal. No dia em que alguém quiser
salvar um veículo escrevendo o nome dele dentro da regra, o autoteste reprova antes do CI.

A razão de a trava valer mais que o conserto: exceção por domínio faria a regra parar de ser regra, e
é a regra que permite a entrada ser automática. Um critério com lista de salvados não é critério —
é a lista de salvados com um critério em volta.

Autoteste: **113 casos** (20 canários), sem rede e sem escrita.

## §301 · A lista de veículos aceita só imprensa — sítio institucional com expediente não é veículo · 30/09/2026

Classe **método e prova**. Decisão da editoria de 30/09/2026, a partir do caso que a própria entrada
automática produziu na víspera.

**O caso.** `ceivap.org.br` entrou em `data/veiculos_imprensa.json` cumprindo os quatro sinais do
§299: HTTPS, página de expediente, nome localizável e matérias na fila. Não é imprensa — é o
**CEIVAP, Comitê de Integração da Bacia Hidrográfica do Rio Paraíba do Sul**, órgão colegiado do
sistema de recursos hídricos, e os nove itens eram PDFs de **Planos Municipais de Saneamento
Básico** hospedados no sítio dele. O defeito não estava em nenhum dos quatro sinais: estava no que
eles não perguntavam. Sítio institucional tem HTTPS, tem expediente e publica documento.

**Dois sinais novos, obrigatórios.** (1) **Identidade jornalística** no expediente — jornal, portal de
notícias, rádio, TV, agência de notícias, redação, editor-chefe. (2) **Vitrine datada ou cargo de
redação**: capa com ao menos três marcas de tempo (data por extenso, data numérica, `<time
datetime>`, o "há 2 horas" das capas, ou três itens de feed) **ou** cargo de redação nomeado no
expediente. E uma **exclusão por padrão**: órgão público, comitê de bacia, agência reguladora,
associação, consórcio, ONG, universidade e empresa não entram.

**Institucional não é bloqueado — é encaminhado.** O domínio institucional vai para
`data/dominios_institucionais.json`, que **não é lista de bloqueio**: quem está nela é fonte oficial,
e o caminho dela é o juiz, com documento primário. Tratar as duas listas como uma jogaria fonte
oficial no lixo, que é o oposto do que o método quer.

**Dois ajustes que a medição contra os sítios reais impôs**, e que valem registro porque a primeira
versão da regra reprovava o caso típico. (a) O termo institucional passou a ser lido **só na
autodescrição do expediente**: varrendo a página inteira, "Secretaria de" numa manchete transformava
jornal em instituição, e quatro veículos caíram assim, `horacampinas.com.br` entre eles. Jornal fala
de órgão público todo dia; o que distingue o sítio institucional é ele **dizer que é um**.
(b) Exigir capa datada sozinha expulsava `plantaoguaruja.com.br` e `abcdoabc.com.br`, que são
jornais com diretor e editor-chefe no expediente e capa renderizada por JavaScript —
**critério que derruba o caso típico está medindo a própria implementação, não o mundo**. Daí o cargo
de redação como alternativa de igual peso.

**Reavaliação dos 11 listados, com a regra nova.** Entram 8: `horacampinas.com.br`,
`vale360news.com.br`, `plantaoguaruja.com.br`, `ndmais.com.br`, `canoinhasonline.com.br`,
`nsctotal.com.br`, `upiara.com.br`, `portaldoholanda.com.br`. **Saíram 2**, para a lista
institucional: `ceivap.org.br` (ordem da editoria) e `encontrasantoandre.com.br` — guia de cidade,
cuja página institucional lista bairros, cidades vizinhas e pontos turísticos, sem termo
jornalístico e sem cargo de redação. `abcdoabc.com.br` **fica**: é jornal de verdade, e cai apenas
porque a sonda não achou marca de tempo nem cargo no que conseguiu abrir. Remover veículo real por
limitação da sonda seria perder prova para preservar a regra; está registrado como falso negativo
conhecido do sinal.

**As nove pistas de PMSB** ficaram `fora_do_objeto` — saneamento básico não é risco do ciclo. Nenhuma
foi apagada: cada uma guarda motivo e data, porque descarte silencioso impede conferir a decisão
depois.

Autoteste: **111 casos** (20 canários), sem rede e sem escrita. O canário que a editoria pediu está
escrito com esse nome: *"sítio institucional com expediente não é veículo"*.

## §300 · O portão de paridade reprovava a `main` porque dois contadores mediam universos diferentes · 29/09/2026

Classe **defeito de prova**. Falha **pré-existente na `main`**, encontrada porque bloqueava o merge
do §299: `verificar_paridade_cobertura_qd.py` reprovava com "não indexados divergem:
cobertura_qd.json conta 5041 e verificacao_resumo.json declara 5021".

**Nenhum dos dois números estava errado; eles respondiam a perguntas diferentes.**
`data/cobertura_qd.json` fala dos **5.571 municípios que existem**: 527 com diário indexado, 5.041
sem, 3 indefinidos. O resumo da varredura classificava apenas os **5.551 com linha de log**. A
diferença de 20 é exatamente de municípios que **não têm diário indexado e, por isso mesmo, nunca
foram consultados** — não havia linha de log a classificar, e eles caíam fora da conta.

O estado deles não é indefinido: a cobertura diz `false`, e `false` é `sem_cobertura_qd`.
`recalcular_mare.py` passou a preencher o estado desses municípios pela cobertura, de modo que as
cinco classes somam o **total** (5.571) e não os consultados. `consultados` continua publicado e
continua verificado, como o que sempre foi: quantos têm linha de log. O contador independente
(`scripts/testar_contador_varredura.py`, §280) foi alinhado à mesma verdade **sem copiar o código do
produtor** — ele soma os não consultados pela própria cobertura, que é o único arquivo que sabe
deles, e a independência da recontagem se mantém.

Números publicados depois da correção: com menção **260** · lidos sem menção **200** · sem edição na
janela **67** · sem diário indexado **5.041** · indefinidos **3** · total **5.571** · indexados **527**.
Nenhum peso, crédito, régua ou categoria mudou; o que mudou foi o universo de uma contagem que
declarava menos municípios do que o país tem.

## §299 · Verificador de imprensa, fase 1: agregador resolvido, data em escada, lista que cresce por critério e limiar com intervalo · 29/09/2026

Classe **método e prova**. Itens 1 a 5 do bloco "29/09/2026 (noite) — Verificador de imprensa,
fase 1". A fase 2 continua sem rodar.

**Item 1 — o link do agregador é caminho, não fonte.** `resolver_redirecionamento()` tenta duas
rotas, nesta ordem: redirecionamento HTTP servido pela própria fonte e URL embutida no link
(formato antigo do Google News, em base64 no caminho). O formato em uso hoje é opaco: o blob
decodifica sem trazer URL nenhuma, não há redirecionamento HTTP, e o domínio do veículo não
aparece em nenhum lugar dos 585 KB da página. O endereço só chega por um endpoint interno não
documentado do próprio site — e **ele não é usado, por escolha registrada no código**: usá-lo
seria fazer engenharia reversa de API privada, não ler documento público. Sem as duas rotas, a
pista recebe `redirecionamento_nao_resolvido`, visível na fila. O monitor de imprensa passou a
guardar `veiculo_dominio` do atributo `<source url>` do RSS, que antes era descartado.

**Item 2 — data em escada.** `data_de_publicacao()` devolve `(data, degrau)` e tenta, na ordem:
`datePublished` do JSON-LD, `article:published_time`, `<time datetime>` e data visível nos
primeiros 600 caracteres do corpo. O B4 passou a dizer de onde a data veio; data longe da cabeça
da matéria, mês inexistente e dia impossível não viram data.

**Item 3 — a lista de veículos cresce por critério medido, não por leitura humana de cada
domínio.** Um domínio entra quando cumpre **todos**: HTTPS; página de expediente com nome do
veículo ou CNPJ localizável; ao menos 2 matérias distintas na fila (distintas por título —
sindicação não conta duas vezes); e não estar em `data/dominios_bloqueados.json` (15 agregadores
e fazendas de conteúdo). A entrada grava a data e cada sinal que a justificou, para veto da
editoria em uma linha. Teto de 15 domínios avaliados por noite.

**Defeito que o item expôs, e que ele mesmo corrigiu.** A primeira rodada terminou com 5.425
pistas na fila e **zero lidas**: a sonda de `/expediente` em domínio desconhecido dá 404 na maior
parte das vezes, e essas recusas esperadas, contadas no orçamento da verificação, disparavam o
disjuntor de 25% antes da primeira matéria. Sonda de descoberta e leitura de matéria passaram a
ter orçamentos separados.

**Segundo defeito exposto pelo item 1, no mesmo lugar.** A resolução do link passou a ser tentada
para **toda** pista da fila, antes do critério B5 — uma requisição de rede por pista, 5.425 por
noite, para depois descartar a quase totalidade por "veículo não listado", que é decisão que nunca
precisou de rede. A rodada de medição estourou 28 minutos sem imprimir o funil. O `<source url>` do
feed já diz de quem é a matéria: quando ele diz e o domínio não está na lista, a recusa sai sem
rede, e só o que pode ser lido é resolvido. **O que se decide sem rede, decide-se sem rede** — e o
custo de esquecer isso não aparece no autoteste, que é offline por construção; aparece no relógio.

**Item 4 — o limiar tem n e intervalo, não só proporção.** A amostra humana abre com **20**
exibíveis (mais 10 recusadas), e a exibição só liga com precisão observada de no mínimo 95% **e**
limite inferior do intervalo de Wilson a 95% de no mínimo 80%. A razão de exigir os dois está no
próprio número: "19 de 20 = 95%" tem limite inferior de **76,4%** e **não passa**; "38 de 40 =
95%" passa. O relatório escreve a regra por extenso antes da leitura, para que ela não se ajuste
ao resultado, e `--veredito <corretas> <n>` devolve a frase com o n e o intervalo. Se depois de 14
noites a fila não tiver 20 exibíveis, o que vale é o relato da composição da fila e da causa
dominante — não uma amostra menor.

**Item 5 — o funil da noite.** `--funil` escreve fila, lidas, inacessíveis, não lidas por
orçamento, exibíveis, entradas automáticas e cada motivo de recusa com o seu número, e o resumo
do job do coletor noturno passou a publicá-lo nas noites em que o verificador roda. Sem o funil,
"0 exibíveis" chegaria à editoria sem a causa ao lado.

**Mais três defeitos que a medição real expôs, e que o autoteste offline não poderia ter
mostrado.** (a) O disjuntor do orçamento contava **404 como recusa de acesso**: a página de
expediente que não existe naquele caminho é ausência, não barreira, e tratar as duas como a mesma
coisa desligava a sonda depois de dois domínios — 149 candidatos, 13 nunca avaliados. Passou a
haver `eh_recusa_de_acesso()`, que reconhece 401, 403, 429 e 451, e a sonda **para naquele domínio**
na primeira recusa real, em vez de insistir nos outros três caminhos. (b) Os candidatos do topo da
fila não eram veículos: um repositório de dados e um host de armazenamento, que responderam 403 em
tudo. Quatro domínios assim entraram em `data/dominios_bloqueados.json`, que vai a 19.
(c) **Sítio de ente público não é veículo de imprensa** — e entrou. `gov.br` passou por uma fresta
(o domínio **nu** não termina em `.gov.br`) e `prefeitura.poa.br` passou por não ter sufixo de
governo nenhum. `eh_dominio_de_ente()` fecha as duas: sufixo oficial, inclusive nu, e palavra de
ente no nome. Deixar isso passar confundiria *imprensa descobre* com *documento registra*, que é a
distinção em que o método inteiro se apoia. As duas entradas indevidas foram removidas e o
autoteste passou a reprovar a presença de qualquer domínio de ente na lista de veículos — foi esse
canário que as encontrou.

**Funil medido na noite de 29/09/2026** (`--limite 25`): fila **5.587** · lidas **25** ·
inacessíveis **1** · não lidas por orçamento **4.875** · **exibíveis 0** (limiar da amostra: 20).
Recusas: `veiculo_nao_listado` 679 · `sem_data` 13 · `sem_https` 7 · `ente_nao_confirmado` 3 ·
`genero_nao_noticia` 3 · `natureza_duvidosa` 3 · `recusada_pelo_juiz` 2 · `fora_do_ciclo` 1 ·
`inacessivel` 1. Entradas automáticas: **6** de 88 candidatos (`ndmais.com.br`,
`canoinhasonline.com.br`, `nsctotal.com.br`, `ceivap.org.br`, `upiara.com.br`,
`portaldoholanda.com.br`). Sobre a resolução de agregador, o número é o resultado: **150
tentativas, 150 falhas**; o formato em uso do Google News não redireciona e não carrega a URL do
veículo. Por isso o teto caiu a 20 por noite — sonda, não varredura.

> `ceivap.org.br` é comitê de bacia, não jornal, e cumpriu os quatro sinais. **É caso de veto da
> editoria**, exatamente o que o item 3 previu ao exigir que a entrada gravasse data e sinais e
> fosse revista semanalmente. Não se inventou critério novo para expulsá-lo: critério escrito para
> derrubar um caso conhecido deixa de ser critério.

Autoteste: **89 casos** (20 canários), sem rede e sem escrita.

## §295 · Verificador da fonte das pistas de imprensa, em modo sombra · 29/09/2026

Classe **método e prova**. Bloco 2 do handover consolidado de 29/09/2026 (seções A, B, D, E, F do
handover do cartão, mais a seção G do consolidado). **Nada muda no cartão, nada muda no índice:**
fase 1 é sombra.

### O que o verificador faz, e o que ele se recusa a fazer

Cada pista de imprensa passa por seis critérios obrigatórios, na ordem, e **para no primeiro que
falha** — não há nota média. Ele lê o **corpo** da página, nunca o título nem o trecho de busca;
abaixo de 300 caracteres de texto corrido a pista é `texto_insuficiente`, que é como paywall, página
só com título e JS que não renderiza caem fora sem precisar de navegador.

| critério | o que ele impede |
|---|---|
| B1 · cidade certa | homônimo, nome de rua, matéria regional que cita a cidade sem ação própria |
| B2 · preparação | decreto pós-enchente narrado como prevenção, balanço de danos |
| B3 · risco do ciclo | plano de dengue, comitê de outra coisa, licença ambiental |
| B4 · ciclo atual e notícia | matéria de 2023, página sem data, coluna, patrocinado, sátira |
| B5 · veículo e página original | agregador, blog, sindicação em dez domínios, HTTP sem TLS |
| B6 · não duplica | município já com registro, pista já recusada por critério pelo juiz |

Nenhum modelo de linguagem decide exibição. Cada decisão grava URL, hash do corpo lido, data da
leitura, versão do verificador e **o trecho que satisfez ou reprovou cada critério** — é esse trecho
que permite conferir a decisão, e foi a falta dele que tornou ilegíveis as promoções falsas do §286.

**Vinte canários**, um por falha nomeada no handover. Três deles vieram de casos reais desta semana:
a licença ambiental de Alagoinhas e o "Comitê Gestor do Programa Sandbox" de Apucarana, que
enganaram o juiz em 28/09, e a recusa **técnica** do juiz, que mantém a pista viva enquanto a recusa
por critério a tira.

### Seção G · o orçamento que evita a recusa das fontes

`OrcamentoDeRequisicoes`, em `coletores_base.py`, é um limitador **compartilhado**: 40 páginas por
host por noite, 600 no total, disjuntor que desliga o host acima de 25% de recusa e encerra a rodada
se a noite inteira passar disso. Ele não substitui o `Crawl-delay` do robots — acrescenta o que o
robots não diz: **quantas páginas**. O que não couber espera a noite seguinte e fica
`nao_lido_esta_noite`, que **não** é recusa da fonte nem ausência de pista.

O piso de oito tentativas antes de desligar um host existe por uma razão: uma recusa em uma leitura
é 100% de recusa, e desligar por isso seria desligar por ruído.

**Um escritor por campo** (seção G1): o verificador escreve **só** `verificacao_fonte`. Os três
noturnos que escrevem em `data/pistas_*.json` passaram a compartilhar o grupo de concorrência
`noturno`, com `cancel-in-progress: false` — se dois se cruzarem, o segundo espera; nunca cancela
nem escreve por cima.

### A medição da fase 1, e por que a amostra 40+20 não existe

Rodado sobre a fila real, **2.674 pistas**:

| resultado | n |
|---|---|
| veículo não listado | **2.656** |
| sem HTTPS | 12 |
| ente não confirmado | 3 |
| recusada pelo juiz | 2 |
| fora do ciclo | 1 |
| **exibíveis** | **0** |

Só **6 páginas foram efetivamente lidas**: o critério B5 é decidido sem rede, e não se gasta
requisição para descobrir que o domínio não está na lista.

**A amostra de 40 exibíveis + 20 recusadas não pode ser sorteada: não há exibível nenhum.** A causa
não é defeito do verificador — é a regra funcionando como foi escrita. A lista de veículos começa,
por determinação do handover, com os domínios que **já geraram registro confirmado** no banco: são
**cinco**, e eles aparecem em pouquíssimas pistas da fila.

A composição da fila explica o resto, e é o dado que importa para a decisão:

| origem | n | % |
|---|---|---|
| agregador (Google News) | 1.495 | 55% |
| oficial ou diário (não é imprensa) | 558 | 20% |
| domínio de imprensa em potencial | 488 | 18% |
| rede social | 133 | 4% |

**Mais da metade da fila é link de redirecionamento do Google News** — que não é a matéria, é o
caminho até ela. Mesmo com a lista de veículos ampliada, essas 1.495 não viram pista exibível sem
antes resolver o redirecionamento para a URL original.

### E se a lista de veículos fosse ampliada? Também não daria 40

A pergunta óbvia é se basta crescer a lista. Medi, sem mudar regra nenhuma: sorteei 120 pistas de
domínio de imprensa (semente 42), li **107 páginas** dentro do orçamento e rodei os seis critérios
**fingindo que todo domínio estava listado**. Passariam todos os critérios: **1**.

| por que as outras caíram | n |
|---|---|
| sem data de publicação nos metadados | 39 |
| ente não confirmado (B1) | 35 |
| fora do ciclo (antes de 29/06/2026 ou futura) | 22 |
| inacessível | 13 |
| gênero não é notícia | 7 |
| texto insuficiente · recusada pelo juiz · já tem registro | 3 |

A ~1% de aproveitamento, 40 exibíveis exigiriam ler cerca de **4.000 páginas** — seis noites inteiras
de orçamento, e a fila só tem **488** pistas de domínio de imprensa no total. **A amostra de 40 é
inalcançável com esta fila, por aritmética, não por defeito.** O maior motivo isolado é a ausência de
data em metadados, que é decisão de quem publica a página, não coisa que o verificador possa
contornar sem afrouxar o B4 — e afrouxar o B4 é como matéria de 2015 volta.

O relatório de amostra diz isso por escrito quando a amostra sai incompleta, em vez de completar com
recusadas — completar mediria outra coisa.

Dois portões novos (122).
## §298 · O publicador regenerava os PDFs e não os commitava · 29/09/2026

Classe **infraestrutura da rodada**. Achado na primeira publicação depois do bloco 1. **Nenhum peso,
régua ou categoria muda.**

O publicador reprovou no portão 12 com **um** arquivo obsoleto: `MARE_Indice_Documentacao.pdf`.

A cadeia canônica regenera os dois PDFs da raiz — o do índice e o da metodologia —, e o `git add` do
publicador listava `data/`, `dados-abertos/`, `feeds/`, `selos/`, `docs/` e `*.html`. **A raiz não
estava lá.** O PDF era regenerado, ficava sem commit, e o portão 12 — que roda logo depois, sobre
árvore que deveria estar limpa — via a diferença e reprovava.

É a mesma família do §297, no mesmo dia: **o `git add` que não inclui o que a própria rotina
produz**. Lá era `evidencias/`, aqui é `*.pdf`. Dois lugares, uma causa — a lista de caminhos do
commit foi escrita quando a rotina produzia menos coisas, e cresceu sem ela.

## §297 · O §270 de novo, por outro caminho: o `git add` do noturno não incluía `evidencias/` · 29/09/2026

Classe **prova**. Segundo defeito da `main` achado enquanto o PR do bloco 1 esperava CI. **Nenhum
peso, régua ou categoria muda; os 93 registros pontuáveis continuam todos com prova.**

### O defeito

`verificar_evidencias.py` reprovou com **216 itens apontando arquivo que não existe**, todos de hoje,
de quatro coletores: `coletar_s2id` (195), `coletar_diarios_consorciados` (15), `coletar_doe` (5) e
`coletar_diarios_municipais` (1).

A causa está no `git add` do workflow reutilizável dos coletores:

```
git add -A data/ dados-abertos/ feeds/ selos/ docs/MANIFEST_SHA256.txt docs/FILA_PISTAS.md
```

**`evidencias/` não está na lista.** Todo coletor que chama `preservar_evidencia` grava o binário em
`evidencias/` e o registro em `data/evidencias.json`; o índice ia para a `main` no commit da noite, e
o arquivo ficava no runner. O índice passava a **afirmar cópia preservada que não existe** — que é o
defeito mais grave que este projeto pode ter.

### Por que o §275 não pegou isto

O §270 tinha a mesma consequência por outra causa: uma regra de `.gitignore` descartava o binário. O
§275 consertou o `.gitignore` e **não olhou o `git add`**. Os dois caminhos levam ao mesmo lugar, e o
portão só reprova quando o índice chega à `main` — o que acontecia no mesmo commit, todas as noites,
sem ninguém ver porque a `main` só é conferida quando um PR abre.

A lição, escrita para a próxima vez: **consertar a causa que se achou não prova que era a única**.
Quando o sintoma é "o índice afirma arquivo que não existe", vale perguntar por quantos caminhos um
arquivo pode deixar de chegar ao repositório.

### O conserto

`evidencias/` entrou no `git add` dos dois pontos do `_coletor.yml`.

Os já perdidos não se recuperam: foram produzidos no runner e descartados com ele. Viraram **lacuna
declarada** por `scripts/declarar_evidencia_perdida.py`, com o motivo e a data — hash, URL de origem
e tamanho ficam, e é pela URL que a re-preservação acha o que buscar.

**O número cresceu enquanto o conserto esperava CI**, e isso mede o defeito melhor que qualquer
descrição: eram **216** às 11h e **2.680** no fim da tarde, porque cada rodada noturna acrescentava
índice sem arquivo. **7.614 itens no índice, antes e depois da declaração** — nenhum item foi
apagado. Os 93 registros pontuáveis continuam todos com prova em disco.

### Um defeito dentro do conserto

O script que declara a perda só olhava o campo `arquivo`. Um item cujo binário estava no disco e cujo
**texto integral** havia sumido continuava afirmando texto preservado inexistente — a mesma mentira,
menor. Agora ele declara os dois campos, e a idempotência passou a ser **por campo**, não por item:
pular o item inteiro porque o binário já estava declarado deixava a segunda afirmação de pé.

## §296 · A chave de deduplicação olhava um nome e o registro gravava outro · 29/09/2026

Classe **correção de dado publicado**. Achado enquanto o PR do bloco 1 esperava CI: a `main` estava
**vermelha** no portão de consistência, e não por causa daquele PR. **Nenhum peso, régua ou categoria
muda.**

### O defeito

`data/atos_resposta.json` tinha **14 eventos duplicados** — mesmo município, mesma data, mesma causa,
e o mesmo `hash_evidencia`. Duplicatas idênticas, não registros parecidos.

A causa está numa linha de `coletar_diarios_consorciados.py`: a chave que decide se o ato já existe
era montada com o nome **extraído do PDF** (`d["municipio"]`), e o registro era gravado com o nome da
**referência do IBGE** (`ref["nome"]`). Quando os dois diferem — acentuação, caixa, "CORACAO DE
JESUS" contra "Coração de Jesus" —, a chave nunca casa com o que já está no arquivo, e o **mesmo ato
entra de novo a cada rodada**.

A correção é de uma linha e de ordem: resolve-se a referência primeiro e a chave passa a ser a do
registro. **Comparar pelo que se grava** — se a chave e o registro não falam do mesmo nome, a
deduplicação não deduplica nada.

Os 14 foram removidos mantendo um de cada: 862 eventos para 848. Nenhum dado se perdeu, porque as
cópias eram idênticas até o hash da evidência.

### A trava

Autoteste novo sobre o código do laço: a chave tem de sair de `ref["nome"]`, não pode sair de
`d["municipio"]`, e a referência tem de ser resolvida **antes** da chave. É trava estrutural porque
exercitar o laço de verdade exigiria rede e banco — e a regra aqui é de forma, não de comportamento
de rede.

## §294 · Focos por posição, avisos do INMET, grade de três e a fonte junto da figura · 29/09/2026

Classe **texto público** e **coleta**. Bloco 1 do handover consolidado de 29/09/2026. **Peso zero:**
são sinais físicos, e nenhuma nota, régua ou categoria do índice muda. **Não mesclar sem o "vai"** —
muda página.

### 1 · Focos de calor: onde o fogo está, não em que estado ele está

O mapa era coroplético por UF: o estado inteiro pintado pela contagem. O CSV do INPE traz latitude e
longitude **de cada foco**, e pintar a UF jogava fora justamente a informação que importa — um foco
no oeste da Bahia e outro no litoral viravam a mesma mancha.

Agora é um ponto por célula de 0,1° (~11 km). O agrupamento é de desenho e foi medido sobre o dia
real, 28/09, com **26.873 focos**:

| passo | células |
|---|---|
| 0,05° | 4.195 |
| **0,1°** | **3.315** |
| 0,25° | 2.238 |
| 0,5° | 1.251 |

0,1° guarda o desenho do arco do desmatamento e do cerrado baiano, cabe em ~110 KB e desenha. O
agrupamento é feito no **coletor**, não no navegador: mandar quatro megabytes de CSV para o leitor
agrupar seria pior. **Não há escala de intensidade** — o CSV traz `frp`, e a editoria foi explícita
em não introduzir escala que o dado não sustente foco a foco; o ponto diz quantos focos há na
célula, e nada mais.

A contagem por UF **não saiu**: continua na lista, que é o que serve a leitor de tela e a quem quer
o número exato. E passou a vir do **mesmo arquivo** dos pontos — mapa e lista de rodadas diferentes
discordando na mesma figura é defeito que ninguém percebe até alguém somar.

### 2 · Card de avisos do INMET

Contagem de avisos ativos por grau e por fenômeno, mapa por UF e lista. O grau e o nome do fenômeno
são os que o INMET escreve, sem tradução para escala própria (§23.3).

**Corpo vazio servido com 200 é recusa, não ausência de aviso** — a lição que a página de Saúde
pagou em 24/09. O coletor já falha alto nesse caso; o card agora diz "a fonte não respondeu" e
**nunca desenha zero**. Resposta válida com lista vazia tem texto próprio, e os dois não se
confundem.

A linha do topo mudou junto: os avisos do INMET passam a estar aqui, e a Defesa civil segue com os
alertas do CEMADEN por município.

### 4 · Cinco cartões em grade de três

Classe `.grade-figuras--3`, que já existia. Terceira linha com dois cartões, como em outras páginas.
A página **encurtou**: de 5.438 para 3.482 px em 1366 px de largura, com cinco cartões em vez de
quatro. Em 768 px e 390 px a grade colapsa para coluna única pelo sistema existente — conferido nas
capturas, não suposto.

### 3 · A fonte pertence à figura

A seção "Fontes dos sinais de risco" saiu. A tabela de três camadas obrigava o leitor a sair da
figura, procurar a linha e voltar. Cada cartão passou a trazer **órgão · o que o dado é · data da
última consulta**, no mesmo componente de crédito que a inicial e a Saúde já usam — e a **situação**
só aparece quando não é "coletado": dizer "coletado" em toda linha seria ruído, e calar quando a
fonte falhou seria esconder.

O preenchimento da tabela removida saiu de `proveniencia.js` junto: guardado por um `if` que nunca
mais seria verdadeiro, viraria código morto.

### Dois defeitos que o dado e os portões expuseram

**O arquivo do INPE do dia corrente nasce vazio.** Medido: 29/09 com 0 focos às 9h, 28/09 com
26.873. Tratar isso como recusa daria falha declarada toda manhã; tratar como zero diria "nenhum
foco no Brasil" onde só faltava o arquivo encher. Cai para o dia anterior, uma vez, e o nome do
arquivo — que vai para a figura — diz de que dia é o dado.

**O mapa de pontos ficou sem o contorno do país.** Ao trocar o coroplético pelos pontos, esqueci o
mapa base: os focos flutuavam sem Brasil. Quem pegou foi o portão de runtime, que exige os 27
estados desenhados — e estava certo em exigir. O padrão da página já era esse nos mapas de capital:
base neutro, pontos por cima.

**E o resumo do card do INMET era um segundo subtítulo.** Pus a contagem por grau e por fenômeno num
`figura-sub` próprio; o portão de figuras admite **um** subtítulo por cartão, e tem razão — dois
viram parágrafo, e cartão não é texto corrido. O resumo passou para a **legenda**, que é onde
contagem por categoria pertence. Pegou na CI, não aqui.

Sete travas novas no autoteste do coletor.

## §293 · Óbitos pelo Registro Civil, e o estado real de cada um dos vinte desfechos · 29/09/2026

Classe **método e coleta**. Itens 3 a 7 do bloco "fontes primárias". **Peso zero, sem nota, sem
faixa** — nenhuma régua do índice muda.

### Item 5 — óbitos, e um erro que só a conferência pegou

A API do Portal da Transparência do Registro Civil responde aberta, e a primeira versão deste
coletor pediu **semanas** e escreveu uma série semanal. Os números saíram errados de um jeito que
passaria por normal numa leitura rápida: semanas diferentes do mesmo mês devolviam o **mesmo** total,
e 96.348 óbitos numa semana é cerca de três vezes o que o país registra.

A medição explicou: qualquer intervalo dentro de agosto devolve **agosto inteiro** (123.642), e um
intervalo de 15/08 a 15/09 devolve a soma dos dois meses (219.990). **A API agrega por mês**, e a
data escolhe quais meses entram, não o recorte. A série passou a ser mensal — pedir semana e publicar
o número do mês seria inventar granularidade que a fonte não tem.

Com a correção, 14 meses lidos: de 107.927 a 139.525 registros por mês, com o corrente declarado
incompleto. É sinal precoce **sem causa**; o SIM, que tem causa básica, é outra perna e continua
pendente de coletor.

### Itens 3, 4, 6 e 7 — o que não dá para coletar, dito com o teste que mostrou

O bloco manda marcar "não coletável por máquina" em vez de esconder. Conferido fonte a fonte em
29/09:

| desfecho | o que se achou |
|---|---|
| síndrome gripal (item 4) | os bancos do e-SUS Notifica **param em 2024**, e a API OpenSearch responde **401** |
| DDA (item 3) | MDDA/SIVEP-DDA só por TabNet; no portal, só o módulo indígena |
| malária (item 6) | zero conjuntos no portal; só BI público e TabNet |
| leptospirose e DTHA (item 6) | só TabNet; no portal, apenas indicador agregado da RIPSA |
| internações: IRA, cardio, renal, pele, saúde mental, ICSAP, calor, fumaça (item 7) | SIH/SUS por TabNet ou `.dbc` no FTP (formato proprietário comprimido); no portal, só agregados da RIPSA |
| desnutrição (item 7) | SISVAN publica CSV por ano, mas o último é **2023** — três anos de defasagem |

O catálogo passou a ter **vocabulário declarado** de estado de coleta, com `nao_coletavel_por_maquina`
e `fonte_desatualizada` separados de `nao_coletado`: as três coisas são diferentes, e colapsá-las
esconderia qual delas tem conserto.

### O retrato honesto dos vinte

**3 coletados** (dengue, chikungunya e óbitos), **1 não coletado** (SRAG, que passa a ter coletor e
roda no próximo semanal), **2 com fonte desatualizada** (síndrome gripal e desnutrição) e **14 não
coletáveis por máquina**. Era isso o tempo todo; o que mudou é que agora está escrito.

Um portão novo (121); 13 casos offline no coletor de óbitos.

## §292 · Dengue e chikungunya passam a contar pela primária, e o InfoDengue fica com o alerta · 29/09/2026

Classe **método e coleta**. Item 2 do bloco "fontes primárias". **Peso zero, sem nota, sem faixa** —
nenhuma régua do índice muda.

### A divisão de trabalho, dita com clareza

As contagens vinham do **InfoDengue**, que é produto **derivado** do SINAN: ele estima casos
prováveis e calcula nível de alerta a partir da mesma notificação que o SINAN publica. A regra da
decisão é primária quando existir, derivado só para o que a primária não dá. Então:

- **SINAN (novo):** a contagem, por UF de residência e semana epidemiológica de primeiros sintomas.
- **InfoDengue (onde já estava):** o **nível de alerta**, que é interpretação da série e não existe
  no banco primário. Ele não passa a contar nada, e continua na rodada.

### Conta-se notificação, e o arquivo diz isso

Cada linha do banco é uma **notificação**. Parte será descartada pela investigação
(`CLASSI_FIN = 5`) e parte ainda não tem classificação fechada. Contar só as confirmadas daria um
número menor e mais velho — a classificação demora. Contar notificação é o que o Ministério publica
como série corrente; o que não se pode é **chamar notificação de caso confirmado**, e a ressalva no
`_governanca` do arquivo diz exatamente o que foi contado.

### Uma peça comum, para não haver duas cópias

`saude_opendatasus.py` reúne o que o coletor de SRAG e o de arboviroses fazem igual: descoberta de
recurso por ano, leitura em fluxo, leitura de CSV dentro de `.zip` (o SINAN publica assim),
resolução de UF — **por sigla no SIVEP-Gripe, por código numérico no SINAN** — e agregação por UF ×
semana. O coletor de SRAG foi reescrito para usar a peça comum em vez da cópia dele.

O que **não** mora lá é regra de desfecho: quais colunas, o que conta e o que não conta. Esconder
isso numa função genérica seria fingir que SRAG e dengue se contam do mesmo jeito.

### Medido sobre dado real

30.000 linhas do banco de 2026: 21 UFs, 35 semanas, **zero linhas descartadas**. O zip de um ano tem
14,7 MB e o CSV de dentro, 127 MB — que nunca vira texto na memória.

### O catálogo, conferido contra o disco

A varredura do §291 achou outro caso do mesmo defeito: `sg` (síndrome gripal) declarava **"coletado"
com `sg_serie.json` inexistente** — a fonte era o mesmo InfoGripe que caiu. Está declarado como não
coletado, que é o que ele é. Cada desfecho já coletado passou a nomear o `arquivo` que o comprova, e
o portão confere os dois lados.

Dois portões novos (120); 23 casos offline na peça comum e 9 no coletor.

## §291 · SRAG passa do InfoGripe para a fonte primária, o SIVEP-Gripe · 29/09/2026

Classe **método e coleta**. Bloco 4 · Doenças respiratórias (decisão da central, 29/09/2026).
**Peso zero, sem nota, sem faixa** — como todo o MARÉ Saúde. Nenhuma régua do índice muda.

### Por que a troca

O bloco aparecia sem coleta, e a causa estava registrada: o repositório do InfoGripe no GitLab da
Fiocruz **passou a exigir autenticação**, e o outro host não responde desde 09/09. Login é recusa
que se respeita (§170), e `coletar_srag_gripe.py` fazia o certo — falhava alto e declarava lacuna,
sem inventar.

A substituição é para a **origem**: o Sivep-Gripe é o sistema oficial de registro de SRAG, e o
Ministério da Saúde publica o banco completo por ano epidemiológico, com atualização semanal. A
hierarquia de fontes da metodologia já prefere a primária; o InfoGripe era o atalho.

### O que muda no dado, dito ao leitor

O InfoGripe trazia **estimativa de dados recentes**. O Sivep-Gripe traz **contagem como está no
sistema**, sem estimativa. As últimas semanas aparecem menores do que ficarão — notificação e
laboratório chegam depois —, e por isso as últimas 4 SE seguem marcadas como incompletas. O que
deixou de existir é a estimativa: onde se dizia "provavelmente serão N", agora se diz "até agora são
N, e este número ainda sobe". A ressalva de não-atribuição continua.

### Microdado não se guarda

Cada ano do banco tem ~250 MB com sexo, idade, raça, município e comorbidades — e são oito anos.
Nada disso entra no repositório: `coletar_srag_sivep.py` lê **em fluxo** e guarda só o agregado por
UF de residência e semana epidemiológica. `coletores_base.buscar_em_fluxo()` é a porta nova, com as
mesmas travas da porta de sempre — cliente identificado, robots respeitado com rastro, e **muro de
robô testado no primeiro pedaço**, porque uma página de bloqueio servida com 200 seria lida como CSV
e viraria linha zerada se ninguém olhasse.

Linha sem UF ou sem semana legível **não é contada nem adivinhada**: na conferência sobre dado real,
10 de 20.000.

### Ano congelado se lê uma vez

O portal declara 2019–2024 "congelados" e só o corrente "vivo". O agregado dos congelados fica em
cache com o nome do arquivo de origem, e só é relido quando esse nome muda. Sem isso, o canal
endêmico custaria ~1,5 GB de rede por semana para produzir o mesmo número.

### O InfoGripe vira sonda, e não escreve mais

`coletar_srag_gripe.py` deixa de coletar por padrão: o modo padrão passa a ser **sondar** e registrar
o diagnóstico. A coleta só roda com `--coletar`, avisando que sobrescreveria a primária por uma
derivada. **Duas fontes gravando o mesmo arquivo é como se perde a procedência.** Se o acesso à
Fiocruz voltar, a sonda avisa — retomar o InfoGripe como complementar é decisão da editoria.

O bloco 4 pediu para manter `sondar_boletim_infogripe.py`.

> **ERRATA (29/09/2026, mesmo dia).** Escrevi aqui que esse arquivo "não existe no repositório".
> **Ele existe**, em `scripts/sondar_boletim_infogripe.py`, e estava ligado ao
> `diagnostico_sinais.yml`, que roda por botão. Procurei na raiz, não achei, e concluí demais do que
> não achei — que é exatamente o erro que este projeto passa o dia inteiro impedindo em dado
> público. A sonda entrou no semanal, como o bloco pedia, ao lado da sonda do próprio coletor: uma
> olha o boletim em PDF, a outra olha os endpoints do CSV no GitLab. Nenhuma das duas escreve série.

### Um defeito que a troca expôs

O catálogo do §36 declarava `srag` como **"coletado" desde 09/09 com `srag_serie.json`
inexistente**: a fonte caiu e a declaração ficou para trás. O portão passou a exigir, para todo
desfecho com `arquivo` declarado, que "coletado" tenha arquivo em disco — e que arquivo em disco
tenha "coletado". Estado de coleta que não olha o dado é promessa, não registro.

Dois portões novos (118); 20 casos offline no coletor novo.

## §290 · A busca dirigida estava escrita e não estava ligada · 28/09/2026

Classe **método e coleta**. Conclusão do bloco das 17:20. **Nenhuma nota muda, nenhum peso muda:**
a busca dirigida não afrouxa critério nenhum — ela entrega um documento melhor para o juiz julgar,
com as mesmas etapas.

### A correção de uma afirmação minha

O §288 descreveu as três rotas como se elas executassem. Não executavam: o módulo tinha as
consultas, os identificadores e a fila de revisita, mas **nenhuma rota de rede e nenhum chamador**.
Rodar o noturno naquele estado produziria "zero das 176 viraram promoção" — e o zero não seria do
mundo, seria do código não ligado. Fica registrado porque o erro é do tipo que se esconde bem: o
portão do autoteste passava, e o número sairia com cara de medição.

### O que foi ligado

`procurar()` executa as três rotas e para na primeira que devolve fonte oficial:

1. **Querido Diário**, pelo território — e **só** quando o código IBGE é conhecido: sem ele não há
   território a consultar, e chutar o código consultaria o diário de outro município.
2. **Sítio oficial**, com `site:gov.br` mais a consulta específica. É o que se pode afirmar sem
   conhecer o domínio do município: a lista de domínios oficiais cobre os **estados**, não os 5.571
   municípios, e montar `prefeitura<nome>.<uf>.gov.br` erraria na maioria.
3. **Cascata aberta**, string por string, da mais específica para a menos.

Toda consulta passa pelo **ritmo da rodada** e pelo **disjuntor por motor de origem** — a busca
dirigida some no mesmo limite de taxa que qualquer outra, e não há caminho de rede novo a manter.
Motor mudo devolve lista vazia: **ausência de resposta não vira ausência de ato**, a recusa original
fica e a pista volta pela fila de reprocessamento.

No juiz, a recusa por `sem_documento_primario` ou `citacao_incompleta` aciona a busca; achando
documento, o veredito é refeito **sobre ele**, guardando qual era a recusa original.

### O teto caiu, e é proposital

De 250 para 150 no codebook: cada recusa por falta de documento passa a custar até quatro consultas
de rede com 3 s de ritmo entre elas, e a noite anterior mostrou que **74% das recusas são desse
tipo**. O noturno do juiz ganhou `precisa_searxng` — ligar o coletor sem a instância que ele
consulta produziria lacuna toda noite com cara de "fonte fora do ar", que foi o erro do §278.

Seis travas novas no juiz de filas (48 casos) e treze na busca dirigida (34 casos), todas offline.

## §289 · O caminho do juiz até o banco, aberto — e a primeira promoção não entrou · 28/09/2026

Classe **método e prova**. Item 1 do bloco das 19:50 (decisão da central). **Nenhum peso, régua ou
categoria muda, e o banco não mudou:** a única promoção viva era duplicata, e a duplicata não entra.

### O que faltava

O juiz gravava `promove: true` em `data/promocoes_automaticas.json` e **nada lia aquele campo**.
Quem aplicava no banco era `julgar_e_aplicar_descobertas.py`, que só olha pistas de imprensa com
status `pendente_confirmacao_documento`. O veredito do codebook morria no arquivo — era o achado que
levei à editoria, e a resposta foi que isto não é decisão nova: é a Etapa 7 do handover, decidida em
27/09.

`aplicar_promocoes_do_juiz.py` faz a sequência com a rede de proteção que já existia, testada desde
31/08/2026: **backup em memória → aplica → recalcula → suíte de portões**; portão vermelho restaura
os bytes originais e devolve a decisão com o erro escrito. O caminho antigo continua, como legado.

### Duas travas que o §286 tornou obrigatórias

Aplica **só** vereditos do codebook em vigor e não superados. A regra frouxa de objeto ex-ante
promoveu quatro registros falsos de cinco; eles continuam no arquivo, marcados, e esta trava é o que
impede que voltem pelo caminho novo.

E a `categoria` vem **do veredito**, não é fixa. O caminho antigo gravava sempre `"plano"`: um
`plano_antigo` entraria como plano novo, mudando o que o índice conta — defeito que só apareceu
porque a primeira promoção real era, justamente, `plano_antigo`.

### A primeira aplicação, e por que ela não aconteceu

Sobrou **uma** promoção viva: Serra/ES, `plano_antigo`, ato de 30/12/2025. O banco já tem Serra —
`plano`, PLANCON edição 2025, pelo repositório estadual da CEPDEC/ES. Duplicar registro é pior que
não aplicar, e o registro existente é o mais forte: a revisão humana decide se há atualização.

A recusa ficou escrita na decisão (`nao_aplicado`, com data e motivo), porque aplicação que não
acontece também precisa dizer por quê.

**Total de planos: 111 — inalterado. `atualizado_em`: 28/09/2026.**

Um portão novo (116), com 13 casos offline.
## §288 · Procurar o ato antes de recusar por falta dele · 28/09/2026

Classe **método e coleta**. Bloco das 17:20 de 28/09/2026 (decisão da central). **Nenhuma nota muda,
nenhum peso muda:** nada aqui promove — a busca dirigida devolve candidato a documento, e quem julga
continua sendo o juiz, pelas mesmas etapas.

### O gargalo, medido

Das 250 decisões da primeira passada, **176 pararam na Etapa 0** por `sem_documento_primario`. Dos
171 com URL, **34 eram Instagram**, 4 Facebook, o resto portais de imprensa. O juiz está certo em
recusar: notícia não é ato. O que faltava era **procurar o ato** antes de encerrar — a notícia diz
que ele existe, e diz onde procurar.

### As três rotas

1. **Querido Diário**, pelo território e pelo número/data extraídos da pista.
2. **Sítio oficial do município**, pelos domínios já conhecidos, procurando o título do ato.
3. **Cascata da busca web**, com string específica — `"{município}" "{tipo} nº {número}"` e
   `"{município}" "{nome do plano}"` —, sob o **mesmo ritmo e o mesmo disjuntor** da rodada. Não há
   caminho de rede novo a manter.

Achou → o juiz segue das etapas 1 a 7 sobre o documento encontrado. Não achou → a recusa fica, e a
pista passa a dizer **onde se procurou e quando**: recusa que não diz onde procurou não é
conferível.

### O que a medição diz sobre as rotas

Sobre as 207 recusas elegíveis (Etapa 0 e citação incompleta): **170 têm consulta dirigida**
possível, 172 trazem nome de plano — e apenas **1** traz número de ato. A notícia quase nunca cita o
número, e é por isso que a rota do nome do plano carrega o peso, com o nome do município entre
aspas fazendo a precisão.

**Um erro meu, achado na medição.** A captura do nome do plano ia até quatro palavras adiante e
produzia consulta que não casaria nada: *"Plano de contingência preventivo estruturado pela
Secretaria"* é frase de jornalista, não nome de ato. Duas palavras, e sem os adjetivos de redação.

### A fila de reprocessamento

**O ato pode ser publicado depois da notícia** — e uma recusa definitiva perderia exatamente esse
caso, que é o mais comum quando a imprensa noticia o anúncio. A pista não achada volta a cada 7
dias, e cada passagem fica no histórico, com as fontes tentadas.

Um portão novo (117), com 18 casos offline.

## §287 · Recusa por causa técnica deixa de ser permanente, com back-off e histórico · 28/09/2026

Classe **método e coleta**. Item 2 do bloco das 19:50 (decisão da central). **Nenhuma nota muda,
nenhum peso muda.**

### Duas coisas com o mesmo nome

A Etapa 0 chamava de `sem_documento_primario` três situações diferentes: a pista sem URL, a URL que
não é fonte oficial, e **o documento que não respondeu**. As duas primeiras são estáveis — a URL é o
que é. A terceira é uma noite ruim de rede, e tratá-la como as outras apaga pista por 403 de uma
hora. "Documento não obtido" ganhou motivo próprio: `documento_inacessivel`.

Com ele, a recusa passa a ter **classe**, e é a classe que decide o destino:

| classe | o que é | destino |
|---|---|---|
| `tecnica` | `documento_inacessivel`, `texto_nao_extraivel` — não conseguimos ler | volta pelo back-off |
| `criterio` | documento lido e reprovado nas etapas 1–6, ou URL que não é fonte oficial | recusa estável |

### O back-off, e o fim dele

1, 3 e depois 7 dias. Sem a espera, a mesma fonte fora do ar seria consultada toda noite, o teto da
rodada seria gasto com ela, e as pistas nunca tentadas ficariam para trás. Na **quinta** tentativa
sem leitura a pista vira `inacessivel_persistente`: sai da fila e **continua no registro**, porque
fonte que ninguém consegue ler é um fato sobre a fonte — some do processo, não do arquivo.

Um erro meu de índice, achado pelo autoteste: a primeira versão indexava o back-off pelo número de
tentativas e **pulava o 1 dia inteiro**, começando em 3. A trava agora exige a sequência exata.

### Toda tentativa fica escrita

`juiz_tentativas` guarda data, classe, motivo e versão do codebook de cada passada. É por esse
histórico que se distingue uma fonte fora do ar há uma noite de outra fora do ar há um mês — e a
pista adiada **não** recebe `juiz`, porque receber a tiraria da fila para sempre.

Catorze travas novas no autoteste (42 casos), todas sem rede e sem escrita.

## §286 · "Institui" solto promoveu quatro registros falsos de cinco · 28/09/2026

Classe **método e prova**. Pré-requisito do item 1 do bloco das 19:50 — abrir o caminho do juiz até
o banco antes disto publicaria os quatro. **Codebook sobe para 1.1.** Nenhum peso, régua ou
categoria muda.

### Os cinco, conferidos um a um contra a prova preservada

A editoria mandou aplicar as cinco promoções da primeira passada. Antes de aplicar, reli a evidência
de cada uma no disco. Quatro não se sustentam:

| município | o que havia nos 20.000 caracteres julgados |
|---|---|
| Salto/SP | **nenhuma** ocorrência de termo de plano |
| Apucarana/PR | **nenhuma**; o objeto casou em "Comitê Gestor do Programa **Sandbox**" |
| Goiânia/GO | **nenhuma**; e a data extraída foi **21/08/1959** |
| Alagoinhas/BA | uma: "Plano de Contingência / PGR" numa **condicionante de licença ambiental** de estabelecimento privado — obrigação imposta a um licenciado, não plano do município |
| Serra/ES | verdadeiro: "Art. 1º Fica instituído o **Plano Municipal de Proteção e Defesa Civil (PMPDEC)**" |

### A causa

`RE_OBJETO_EX_ANTE` era **uma alternância só**, e entre as alternativas estava o verbo solto
`institu[ií]`. Numa edição inteira de diário — vinte mil caracteres, dezenas de atos — sempre há um
"institui" em algum lugar, e quase sempre um "comitê gestor" de outra coisa. O gatilho, por sua vez,
casa em qualquer menção a previsão ou ao período chuvoso, que todo diário tem. Somados, os três
testes cumulativos da Etapa 4 passavam sobre um jornal inteiro.

A Etapa 4 passa a exigir **duas** coisas, e perto uma da outra: o **verbo** que cria ou atualiza e o
**instrumento** nomeado, a menos de 300 caracteres um do outro. "Institui" sozinho não diz o que foi
instituído; "plano de contingência" sozinho pode ser exigência feita a terceiro. Em Serra os dois
são vizinhos imediatos, e é por isso que ele sobrevive.

O trecho registrado passou a ser o **par**, e não o primeiro casamento solto: os `trecho` das quatro
promoções falsas traziam cabeçalho de diário e até texto invertido (`ogidóc o emrofni e…`) — ninguém
conseguiria conferir a decisão por eles, que é o que um registro de decisão existe para permitir.

### O que a medição mostrou

Sobre as 42 decisões com prova no disco: **4 promoções caem, 1 permanece, 37 recusas permanecem, e
nenhuma recusa vira promoção**. A regra só aperta. As outras 208 decisões são recusas de Etapa 0 —
documento nunca lido, nada preservado.

### O mecanismo que não funcionava, e sem o qual nada disso alcançaria o passado

`pendente()` dizia, no comentário, "já julgada por **esta** versão do codebook", e o código não
olhava versão nenhuma: qualquer julgamento anterior tirava a pista da fila **para sempre**. Ficava
sem efeito o único mecanismo que faz um critério novo alcançar o que o critério velho já decidiu.
Agora a comparação é com a versão em vigor — que é o que o comentário sempre disse.

### As decisões erradas ficam no arquivo

`scripts/rejulgar_decisoes_do_juiz.py` relê a prova do disco (**sem rede**), rejulga com o codebook
em vigor e **acrescenta** o veredito novo; a decisão antiga recebe `superada_por` e permanece.
Apagar o erro tiraria da auditoria amostral semanal exatamente o caso que ela precisa ver. Depois de
rodar: 250 decisões mantidas, 42 acrescentadas, **uma única promoção viva** — Serra/ES,
`plano_antigo`.

Dois canários novos, com a forma exata dos dois modos de falha (12 canários), e um portão novo
(115).

## §285 · O carimbo da data de atualização ficou para trás no desacoplamento · 28/09/2026

Classe **infraestrutura da rodada**. Quarta e última camada do item 1 do bloco "Frescor do site".
**Nenhuma nota muda.**

Com o publicador enfim verde, o dado de 28/09 foi publicado — e o rodapé continuou dizendo
**25/09**. A causa é do mesmo tipo das outras três: `meta.atualizado_em` só era carimbado por
`atualizar.py`, a rotina semanal monolítica. O desacoplamento (§266, §267) moveu a coleta para os
noturnos e a publicação para o `publicar_dados.yml`, e **o carimbo ficou para trás**. Enquanto a
rodada semanal ainda rodava, ninguém viu; quando ela deixou de ser o caminho normal, o site passou a
declarar a data da última vez em que aquela rotina rodou.

`scripts/frescor.py --carimbar` entrou no publicador, **antes** de recalcular — os geradores de
derivado carimbam `gerado_em` a partir dessa data, e depois ficariam um dia atrás, que é o defeito
que o §? de 10/09 já havia pago uma vez.

**A data vem do repositório, não do relógio:** é a do commit mais recente que tocou `data/`. Rodada
sem dado novo não avança nada — carimbar hoje numa rodada sem coleta diria que o site foi
atualizado quando não foi, que é o mesmo erro do item 4 visto do outro lado. `corte` nunca é tocado:
ele é decisão editorial sobre até quando o dado vale, e não tem relação com quando a rodada
publicou.

Rodado local, e idempotente na segunda vez:

```
OK CARIMBO — data/meta.json passa a declarar 28/09/2026, a data do último dado que chegou à main
OK FRESCOR — site em dia: publicado em 28/09/2026, último dado em 28/09/2026
OK CARIMBO — nada a mudar; data/meta.json já declara 28/09/2026 e não há dado mais novo
```

Cinco travas novas no autoteste do frescor (17 casos).

## §284 · O publicador não tinha navegador para os portões de página · 28/09/2026

Classe **infraestrutura da rodada**. Terceira camada do item 1 do bloco "Frescor do site".
**Nenhuma nota muda.**

O §282 fez o publicador chegar à suíte de portões; o conserto do log do aplicador fez a suíte chegar
ao fim. Aí apareceu a camada seguinte: a suíte inclui dois portões que rodam em **Chromium real**
(móvel a 390 px e consistência visual), e o publicador nunca os instalava — `portoes.yml` instala o
navegador antes deles, `publicar_dados.yml` não. Ele nunca tinha chegado tão longe para notar.

O passo de instalação entrou. A alternativa seria rodar só o perfil `dados`, e ela foi recusada:
escolher subconjunto de portões a olho já custou um ciclo de CI em 23/09, e **"não consegui rodar o
portão" não é verde**.

O teto do passo subiu de 12 para 20 min, e a meta declarada de "menos de 10 min" saiu do cabeçalho.
Ela foi medida sobre um publicador que morria no portão 12 antes de rodar a suíte inteira — era meta
de uma rodada que não acontecia. **Publicar rápido nunca valeu mais do que publicar conferido.**

## §283 · Toda coleta que muda dado termina em publicação, e o atraso passa a aparecer · 28/09/2026

Classe **infraestrutura da rodada** e **mostrador**. Itens 2, 3 e 4 do bloco "Frescor do site"
(decisão da central, 28/09/2026, tarde). **Nenhuma nota muda, nenhum peso muda, nenhum texto
editorial muda.**

### O que o §282 consertou, e o que faltava

O §282 consertou as causas: o juiz que não aplicava e o publicador que morria do próprio trabalho.
Faltava o que impede a próxima parada de durar três dias. Entre 25/09 e 28/09 a coleta rodou todas
as noites, o publicador falhou duas vezes por dia, e nada disse. **Defeito que se anuncia custa uma
correção; defeito silencioso custou três dias de dado.**

### Item 2 — o contrato

`publicar_dados.yml` passa a ser disparado por `workflow_run` ao término, **com sucesso**, de
qualquer coletor ou juiz que commita dado: os quatro noturnos, o semanal de sinais, a cadência da
busca web, a atualização semanal e a preservação de textos. Os horários fixos continuam — 06h e 22h
são compromisso público declarado em `obrigado.html` e na METODOLOGIA, e cobrem a noite em que
nenhum coletor rodou.

O `cancel-in-progress: true` do grupo faz o trabalho pesado: uma noite com cinco coletores não gera
cinco publicações — a mais nova substitui a mais velha e publica o que todas commitaram. Publicação
cancelada por uma mais nova não é dado não publicado, e o texto do workflow diz isso, para que
ninguém leia o cancelamento como falha.

### Item 3 — o vigia

`scripts/frescor.py` compara o `atualizado_em` do `data/meta.json` **servido pelo domínio** com o
último commit de dado na `main` — uma ponta de cada lado do deploy. `verificar_publicado.yml` ganhou
o passo, **sem** `continue-on-error`: atraso silencioso foi o defeito, e vigia que não reprova é
silêncio com outro nome.

**A granularidade está declarada, não escondida.** `atualizado_em` é data, não instante, então o
limite de 24 h da decisão é aplicado onde ele existe: reprova acima de **um dia** de diferença. Um
dia pode ser uma hora ou quarenta e sete, e reprovar ali daria alarme falso toda manhã seguinte a
uma noite que commitou tarde; dois dias é uma publicação inteira perdida. Rodado hoje sobre o estado
real, ele diz: *dado novo não publicado desde 25/09/2026 (3 dias de atraso)*.

O mesmo script escreve a linha de frescor no resumo do job do publicador, com `if: always()` — a
linha aparece justamente quando o publicador falha, que é quando ela importa.

### O defeito que a primeira noite de verdade expôs

Com o juiz aplicando e com teto, o aplicador rodou até o fim e **commitou** — e aí apareceu o que
nunca tinha aparecido: ele escrevia no log por uma **porta própria**. Um dicionário com `data`,
`canal`, `alvo`, `decisao` e `motivo`, gravado direto no monólito `data/log_buscas.json`, sem
`strings`, sem `executor` e sem `nivel`. `verificar_consistencia.py` reprovou 150 linhas de uma vez,
duas faltas cada, e o publicador parou ali — corretamente.

Duas coisas erradas na mesma função. A de esquema, acima. E a da porta: o §269 migrou o log para
JSONL, e quem escreve no monólito escreve num arquivo que ninguém mais alimenta. **Duas portas
gravando o mesmo log é como se perde registro** — é o §229 um nível acima.

`registrar_log` passou a chamar `log_busca`, com o vocabulário fechado e o mapeamento declarado:
`APLICADA` → registro, `FILA_HUMANA` → pista, `DESCARTADA` → consultado sem achado, `REVERTIDA` →
erro. "Nada localizado" **não** entra: aquele valor é da bateria municipal completa (§2.1), e usá-lo
afirmaria ausência de plano a partir de uma pista só. O território sai do `alvo`, que é o único
lugar onde ele existe na pista de imprensa — e alvo sem UF reconhecível fica sem território, em vez
de inventá-lo.

As 150 execuções já gravadas foram **convertidas, não apagadas**:
`scripts/corrigir_log_do_aplicador.py` as reescreve no esquema v2 preservando alvo, motivo e data, e
recusa gravar se o total do log mudar. Antes e depois: **51.400 execuções**.

### Item 4 — o mostrador

O rodapé da página inicial mostrava "Última atualização", que é a data da **publicação**. Sozinha,
ela não distingue "nada foi coletado desde então" de "foi coletado e não publicado" — e foi a
segunda que aconteceu. Agora, ao lado: **"Última coleta: 28/09/2026 · última publicação:
25/09/2026"**, das datas que já existem em `data/saude_pipeline.json` e `data/meta.json`, com
`ultima_rodada_log` do resumo como segunda fonte.

Sem as duas pontas, a linha fica oculta: não se afirma meia data. É mostrador, não interpretação —
descreve o que está nos arquivos, sem juízo e sem instrução de uso.

Dois portões novos (114): o autoteste do frescor e o do conserto do log do aplicador.

## §282 · O juiz nunca promoveu nada, e o publicador morria do próprio trabalho · 28/09/2026

Classe **infraestrutura da rodada**. Item 1 do bloco "Frescor do site" (decisão da central,
28/09/2026, tarde). **Nenhuma nota muda, nenhum peso muda.**

### O fato que a editoria mediu, e a causa

Nada do que foi coletado desde **25/09** chegou ao site: `data/meta.json` marcava 25/09, o banco
seguia com 267 registros e 111 planos, `data/promocoes_automaticas.json` não existia. Não era um
defeito, eram quatro, em dois workflows.

**No juiz.** `noturno_juiz.yml` rodava `julgar_filas.py --relatorio`. Sem `--aplicar`, o script
imprime o veredito e **não escreve** — nem na fila, nem no registro de decisões, nem no log. Mesmo
que a noite terminasse, ela não deixava traço; era por isso que o arquivo de promoções não existia.
Nenhum dos dois julgadores tinha teto, e a fila de imprensa tem **1.495** pendentes de documento e
cerca de **1.174** pendentes de codebook, cada uma com busca na rede: o job de 90 min foi
**cancelado** às 12h08 de 28/09, e como o `_coletor.yml` só commita ao final, a noite inteira de
trabalho foi perdida sem rastro. O aplicador rodava **antes** do juiz de codebook, de modo que
buscava documento de pista que o codebook descartaria.

**No publicador.** O passo "Regenerar a cadeia canônica" chamava `verificar_derivados.sh` no modo
`git`, que exige árvore limpa **depois** de regenerar. É o único modo que nunca pode valer ali: o
publicador existe para pôr os derivados em dia depois de a coleta commitar dado novo, então ele
regenerava, encontrava a diferença que ele mesmo acabara de produzir, e reprovava. As duas execuções
de 28/09 (04h14 e 09h07) morreram assim. **O publicador falhava precisamente porque tinha trabalho a
fazer** — e o efeito é o pior possível num monitor de evidências: silêncio que parece normalidade.

### O que mudou

- `julgar_filas.py --aplicar --limite 250` e `julgar_e_aplicar_descobertas.py --limite 150`, nesta
  ordem: o codebook julga primeiro, porque ele só **aperta** o critério. Teto que termina e commita
  vale mais que fila inteira que não chega ao fim, e o que sobra fica declarado na saída.
- `--limite` novo no aplicador, com recusa de zero e de negativo, e a saída dizendo quantas ficaram
  para a próxima — fila declarada não é lacuna de coleta.
- No publicador, `--idempotencia` no lugar do modo `git`: regenera e exige que uma **segunda**
  regeneração não altere nada, que é a propriedade de verdade. O portão 12 no modo `git` continua
  valendo onde faz sentido — na suíte, **depois** do commit local, quando a árvore está limpa.
- Ordem nova no publicador: commit local, suíte inteira, e só então o push. Nada sobe sem a suíte; o
  push está condicionado a ela.

### O defeito que ligar o `--aplicar` teria exposto

`--aplicar` gravava recusa **permanente** na pista, e `pendente()` nunca mais a devolveria à fila.
Mas o veredito de recusa não distingue "lemos e não serve" de "não conseguimos ler": um 403 de uma
hora, um portal fora do ar, uma falha de rede apagariam a pista para sempre. Ligado sobre 1.174
pistas numa noite ruim, isso queimaria a fila em silêncio.

O veredito passou a carregar `leu_documento`, e a aplicação virou função pura (`aplicar_no_objeto`)
com três saídas: **promovida**, **recusada** e **adiada**. Adiada não recebe `juiz` — se recebesse,
`pendente()` a consideraria julgada — e volta à fila na próxima rodada. É a distinção de sempre, um
nível abaixo: entre "a fonte não tem" e "não conseguimos ler o que a fonte tem". Sete travas novas no
autoteste (27 casos).

### O que este PR não faz, e é da editoria

O juiz de codebook promove no **veredito** e escreve em `promocoes_automaticas.json`; quem aplica no
banco é `julgar_e_aplicar_descobertas.py`, e ele só olha pistas de imprensa com status
`pendente_confirmacao_documento`. **Um veredito `promove: true` do codebook não tem hoje caminho até
o banco** — nada lê aquele campo para promover. Não abri esse caminho aqui: criá-lo muda o que entra
no índice, e isso é decisão da editoria. Fica registrado como pedido separado.

## §281 · "Imprensa" é canal de descoberta, e o rótulo passa a dizer isso · 28/09/2026

Classe **texto público**. Defeito 6 do relatório da auditoria do funil, item 3 do bloco de decisões da
editoria de 28/09/2026. **Nenhuma nota muda, nenhum cálculo muda:** é rótulo.

### O que o leitor via

Treze registros de `municipios.json` têm `canal: "imprensa"`. A página mostrava "· via imprensa" ao
lado de uma fonte descrita como oficial — em Rio Branco/AC, por exemplo, "Prefeitura de Rio Branco
(oficial)" —, e a tabela de procedência mostrava o código cru na coluna de canal. Nada ali dizia que
aquele canal é de **descoberta**: a matéria serve para achar o documento, e a prova continua sendo o
ato na fonte oficial (§5.2.1).

O rótulo passou a ser **"imprensa (descoberta)"** nos dois lugares. Os outros canais são de registro
— diário oficial, repositório estadual, site do município —, e para eles o código já diz o que é.

### Por que só o rótulo

Nenhum dos treze pontua: doze são `nao_verificado` e um é `decreto`, que não entra no índice por
regra. O valor gravado não muda — `imprensa` continua sendo a chave no dado e no vocabulário fechado
de canais, porque renomear a chave quebraria o vocabulário e o histórico do log sem melhorar nada
para quem lê.

### A trava

`scripts/verificar_rotulo_canal_descoberta.py` reprova quando uma página atribui ao canal de
descoberta um rótulo sem a palavra "descoberta", e reprova também se um dos arquivos de rótulo
desaparecer — portão que fica verde olhando para o vazio não é portão. Dois portões novos (111).

## §280 · O número público de menções era 347 e é 260 · 28/09/2026

Classe **correção de dado publicado**. Defeito 1 do relatório da auditoria do funil, item 3 do bloco
de decisões da editoria de 28/09/2026. **Nenhum peso, régua ou categoria muda**, e o índice não se
move: a conta corrigida é um contador de cobertura.

### O que estava errado

`data/verificacao_resumo.json` declarava **347** municípios com menção ao tema no diário municipal.
São **260**. Os 87 registros de diferença são execuções com a decisão `sem_edicao_no_periodo` —
diário indexado, **nenhuma edição dentro da janela**. Nesses municípios não houve o que ler, e o
site os contava como tendo menção.

A causa não é aritmética, é de definição. `com_mencao` era definida por **exclusão**: contava como
menção todo resultado que **não** começasse por um de três prefixos conhecidos. Uma definição assim
não erra uma vez — ela erra a cada decisão nova que alguém criar, porque toda string que o código
não conhece cai no lado que **afirma**. `sem_edicao_no_periodo` foi criada pelo §194, quatro dias
antes, e entrou nessa conta sem que ninguém escrevesse uma linha a respeito.

A classificação passou a ser **positiva**, com cinco estados e um balde honesto:

| estado | o que se sabe |
|---|---|
| `sem_cobertura_qd` | 5.041 · não há diário indexado; nada foi nem pode ser lido |
| `sem_edicao_no_periodo` | 56 · indexado, nenhuma edição na janela; não houve o que ler |
| `coberto_sem_mencao` | 211 · indexado e lido; nenhum excerto com os termos |
| `com_mencao` | 260 · a consulta com os termos devolveu edição |
| `cobertura_indefinida` | 3 · teste de cobertura falhou, **ou** string desconhecida |

`indexados` continua **527** — a repartição mudou, o alcance da varredura não. `sem_mencao` segue
valendo só para diário efetivamente lido (211), porque "não indexado" e "sem edição na janela" não
são leitura negativa: tratá-los como leitura afirmaria ausência de plano onde há ausência de fonte
(§4.1.2).

### A regra nova está ancorada em outro arquivo, não na minha leitura

`com_mencao` = 260 é **exatamente** o número de municípios com execução `com_excerto` (242) ou
`registro` (22) no canal DOM do log. Dois arquivos de origens diferentes, produzidos por caminhos
diferentes, dão o mesmo número — e essa igualdade é agora um portão, não uma coincidência anotada.

### O erro que eu quase publiquei no lugar do que estava lá

A primeira versão desta correção baixava `com_mencao` para **57**. Eu havia tratado a string
`0 decreto(s), 0 pista(s)` — 243 municípios — como "diário lido, nada encontrado". Fui ler o ramo do
coletor que grava essa string e ela significa o oposto: só é escrita **depois** de a consulta com os
termos devolver edição, e o zero é dos atos *classificados*, não dos excertos. No log, esses
municípios são `com_excerto`. Chamá-los de "lido sem menção" teria trocado um erro por outro, na
direção contrária, com 243 municípios em vez de 87 — e eu estava a um commit de fazer isso apoiado
numa medição que eu mesmo havia feito e lido errado.

O que me pegou: a medição estava certa e a **interpretação** do campo, não. A reconciliação contra o
log foi o que denunciou — a contagem não fechava com o que o log dizia, e foi essa discordância que
me mandou ler o coletor. É por isso que ela ficou como portão.

### O portão que já existia e passou verde sobre este defeito

`scripts/testar_contador_varredura.py` nasceu no §121 para impedir exatamente esta família de erro,
e ficou verde durante oito dias sobre 347. Ele conferia a **assinatura** do defeito antigo
(`com_mencao == consultados`, o caso extremo) em vez da propriedade. Reescrito, ele agora:

1. recomputa os cinco estados por conta própria e exige que o resumo publicado concorde — dois
   códigos independentes, um número;
2. reconcilia `com_mencao` contra o log, e reprova município contado como menção sem execução
   `com_excerto` nem `registro`;
3. recusa `not m.startswith` no código-fonte da classificação, com a razão escrita: definição por
   exclusão volta a engolir a próxima decisão nova.

`scripts/verificar_paridade_cobertura_qd.py` somava a partição dos indexados em **duas** parcelas.
São três. O autoteste dele passou a encenar o defeito: `347 + 180 = 527` fechava a soma e agora
reprova, porque fechar a soma nunca provou que as parcelas estavam certas.

### A terceira lista

A mesma decisão `sem_edicao_no_periodo` já ficou fora de duas listas antes — as duas estão no
comentário do coletor, e o incidente está no §213: a varredura nacional morreu no primeiro município
daquele tipo e ficou parada um dia. O §45 da metodologia foi escrito por causa disso, sobre
vocabulário fechado. Esta é a terceira lista, e ela não era um vocabulário: era uma **contagem**. Daí
o §45.1, que estende a regra — contagem definida por exclusão é vocabulário aberto com outro nome, e
o lado de fora nunca pode ser o lado que afirma.

Dois autotestes novos no workflow (107 portões).
## §279 · Cadência para os três coletores de CI, e um defeito que não existia · 28/09/2026

Classe **infraestrutura da rodada**. Item 5 do bloco de decisões da editoria de 28/09/2026.
**Nenhuma nota muda.**

### Os três que só rodavam na CI

`descobrir_dominios.py`, `coletar_espin.py` e `classificar_planos_municipais.py` produzem dado que a
rodada **usa** — `dominios_oficiais.json` alimenta `descobrir_planos.py`, `saude_sinais.json` alimenta a
camada observada de saúde —, e rodavam só quando um PR abria. O efeito era dado envelhecendo sem ninguém
notar: a última busca ativa de domínio registrada era de **23/09**.

Entraram no `semanal_sinais_e_links.yml`, domingo 4h30 de Brasília, dentro da janela noturna. Semanal é a
cadência que eles pedem: domínio oficial e ESPIN não mudam por dia. O teto do job subiu de 120 para 150
min por causa dos três.

### O "defeito 4" da auditoria do funil não existia, e o erro era meu

O item 5 pedia investigar e consertar a causa do erro de 05/09 no canal `motor_de_busca`. Investiguei, e
o que achei foi uma conclusão errada minha, escrita no relatório do funil: **aquele canal não tem script
produtor nenhum.** Uma busca no repositório inteiro mostra que só `gerar_cobertura_declarada.py` o
menciona, e apenas para **mapeá-lo** em `busca_web`.

As 78 execuções são de **busca manual de sessão editorial** — bateria estadual de saúde, reclassificações,
emergências sanitárias —, e as 44 com decisão `erro` são registros honestos de busca que não localizou
nada. O canal não morreu: as sessões manuais pararam, e o equivalente automático é a camada 4
(`busca_web`), que roda.

Não havia defeito a consertar; havia um diagnóstico meu a corrigir, e o relatório em
`notas/preprint/funil/RELATORIO_2026-09-27.md` foi corrigido no privado. A lição de método fica escrita
junto: **canal parado no log só é defeito quando existe produtor esperado** — antes de chamar de defeito,
procurar quem deveria escrever.

### Uma dependência que eu quase inventei de novo

Ao acrescentar os três, escrevi `precisa_searxng: true` no workflow supondo que `descobrir_dominios.py`
consultasse o metabuscador. Fui conferir antes de deixar: **ele não consulta nada disso** — testa padrões
de domínio declarados (`defesacivil.{uf}.gov.br` e afins) direto por HTTP e decide pela resposta e pelo
título. A linha saiu. Era o quarto erro do mesmo tipo em dois dias, e o único que não chegou a subir.
## §278 · Redes sociais entram como descoberta, e só como descoberta · 28/09/2026

Classe **método e coleta**. Item 2 do bloco de decisões da editoria de 28/09/2026. **Nenhuma nota
muda:** nada aqui pontua, e nada aqui pode virar fonte de registro.

### As três condições, e onde cada uma é imposta

A editoria aprovou redes sociais como canal de descoberta com três condições. Cada uma virou código, não
promessa:

**1. Só perfil oficial, verificado pelo domínio.** O perfil entra apenas quando um domínio oficial do
próprio ente (`*.gov.br`) **linka para ele**. Sem selo de API, sem lista de handles digitada à mão, sem
inferência por nome parecido: se o site oficial não aponta o perfil, o perfil não existe para o Monitor.
Link de compartilhamento (`sharer`, `intent`, `watch`) é descartado — ele aparece em quase toda página e
não é conta institucional.

**2. A pista exige documento primário em fonte oficial no juiz.** Post de rede social **não passa a
Etapa 0**: nenhum domínio de rede social está em `PADROES_FONTE_PROVAVEL_OFICIAL`, e há autoteste nos
dois lados — no coletor e no portão — provando isso. A pista serve para acionar o seguimento (§159), que
procura o ato na fonte oficial.

**3. Rede social nunca é fonte de registro nem aparece como fonte no site.**
`scripts/verificar_rede_social_nao_e_fonte.py` reprova se um registro de `municipios.json`,
`estados.json` ou `atos_resposta.json` tiver rede social em `url`, `fonte`, `canal` ou `documento`, e se
uma página pública citar rede social **no crédito de figura ou depois de "Fonte:"**. Menção em prosa não
é alvo: o que não pode é rede social ocupar o lugar onde o leitor lê de onde veio o dado.

### Sem chave, e reusando o que já existe

A consulta vai pela instância efêmera do SearXNG que a rodada já sobe, restrita ao perfil confirmado
(`site:<rede> "<perfil>" "<termo>"`). Isso cumpre o que a decisão pediu — **o mesmo disjuntor por motor
de origem e os mesmos contadores** — sem um segundo caminho de rede a manter, e sem API paga, que o
repositório proíbe.

### O alcance é declarado, não escondido

Só é possível confirmar perfil onde já conhecemos o domínio oficial: **47 alvos estaduais** com domínio
em `data/dominios_oficiais.json` e **90 registros municipais** com URL `.gov.br` em
`data/municipios.json`. Para os outros municípios o coletor **não gera pista**, e dizer isso é parte do
método — ausência de cobertura não é ausência de plano.

### Dois defeitos meus, achados antes de subir

**O portão olhava só o domínio.** O autoteste que eu mesmo escrevi reprovou em três casos e mostrou o
buraco: fonte escrita à mão não traz domínio — "Instagram da Prefeitura", "post no Facebook". Era
exatamente a forma mais provável de a rede social virar fonte. O portão passou a casar também o **nome**
da plataforma, com fronteira de palavra; `x` sozinho ficou de fora, porque uma letra casaria em qualquer
texto.

**O noturno de descoberta não subia o SearXNG.** Eu liguei o coletor a um workflow sem a instância que
ele consulta — e o efeito seria pior que uma falha: lacuna a cada noite, com cara de "fonte fora do ar".
O workflow reutilizável ganhou `precisa_searxng`, e a descoberta pede a instância. `seguir_pistas.py`,
que já rodava ali, dependia dela pelo mesmo motivo e estava no mesmo escuro.

É o terceiro erro do mesmo tipo em dois dias — ligar uma peça sem conferir se a dependência dela está no
lugar. O padrão que me pegou nos três: **antes de ligar, listar o que a peça precisa e onde isso existe.**

Três portões novos (109).

## §277 · O Querido Diário volta ao funil, pelo juiz · 28/09/2026

Classe **método e coleta**. Item 1 do bloco de decisões da editoria de 28/09/2026. **Nenhuma nota
muda:** nada aqui promove nada — a fila existe para o juiz julgar.

### A suspensão cai, mas o que a causou é consertado primeiro

A suspensão de 06/09/2026 tinha causa nomeada: a consulta **em lote** (`territory_ids` com vírgulas)
devolveu **8.165 zeros uniformes** em 03/09, e o diagnóstico de resultado conhecido mostrou que **um
território por chamada** devolve 3 diários e 3 excertos onde o lote devolvia 0 (caso Cerrito/RS).
Reativar o coletor como estava reproduziria o defeito. A função mudou de nome junto com o
comportamento — `_lote` deixou de existir, e no lugar está `_por_territorio` —, para que ninguém a
chame por engano.

`consultar_querido_diario.py` volta à rodada, e a regra que substitui a suspensão é explícita: **toda
pista do QD passa pelas etapas 0 a 7 do juiz e nunca entra direto no banco.** A fila
`pistas_querido_diario.json` entrou na lista de `julgar_filas.py`.

### A primeira fila: os 169

São os municípios em que a varredura do diário reconheceu excerto com termo do dicionário e que **não
estão no banco nem em fila nenhuma** — o achado do item C da auditoria do funil.
`scripts/fila_do_juiz_querido_diario.py` os lista em `data/fila_qd_169.json`, ordenados por UF e nome
para ser reproduzível, e o noturno consulta 40 por noite com
`consultar_querido_diario.py --alvos data/fila_qd_169.json --limite 40`. Distribuição: SP 57, AL 24,
BA 22, SE 12, MG 12, PR 11, RJ 11, RS 9, MS 5, e um cada em CE, GO, MT, PA, PE, TO.

### O erro que a medição pegou antes de eu confiar nele

A primeira versão da fila montava **pistas** a partir da evidência já preservada de cada município: o
índice guarda, sob o `hash_evidencia` da execução, o registro da edição com a URL do PDF, a do texto e
um excerto. Escrevi as 168 pistas e fui medir o que o juiz faria com elas. O juiz recusou todas, e ao
olhar o motivo o defeito apareceu: **o excerto preservado não é a menção ao plano.** A preservação
manteve uma gazeta por consulta e o primeiro excerto dela — que nos casos examinados falava de hectares
de um evento, de adjudicação de licitação e de objetivos pedagógicos de escola.

As 168 pistas foram descartadas, e o arquivo guarda o motivo por escrito. A fila passou a ser de
**alvos**, e a pista vem de consulta nova, por município e por termo de plano: aí o excerto aponta a
menção. É a diferença entre "achei este município" e "achei esta menção".

### O recorte do ato, que é o que faltava no juiz

A pista do QD aponta a **edição** do diário — nos casos medidos, 3.663 e 20.000 caracteres com dezenas
de atos. O juiz lido sobre a edição inteira cai em `natureza_duvidosa`, e **corretamente**: não há um ato
a julgar, há muitos. Mas o documento primário do §5.2.1 é o **ato**, não a edição.

`recortar_ato()` isola o ato que contém o excerto: do cabeçalho de ato imediatamente anterior até o
cabeçalho seguinte. A busca do excerto tolera quebra de linha e caixa — o excerto do QD vem com as
quebras dele e o diário usa outra caixa —, com um mapa de posições de volta ao texto original, porque é
no original que o recorte é feito. Sem excerto, sem cabeçalho antes dele, ou recorte abaixo de 200
caracteres, **devolve o texto inteiro**: na dúvida o juiz lê tudo e provavelmente recusa, que é o erro
tolerado pelo codebook.

Dito com clareza, porque é o efeito que importa: o recorte **torna possível promover** onde a edição
inteira mascarava o ato. Ele não afrouxa critério nenhum — as seis etapas continuam valendo sobre o
texto do ato —, mas muda o que passa. Cinco travas novas no autoteste do juiz (13 no total, com os dez
canários).

Dois portões novos (106).

## §276 · Os três runs vermelhos da primeira noite · 28/09/2026

Classe **infraestrutura da rodada**. Item 7 do bloco de decisões da editoria de 28/09/2026 (manhã).
**Nenhuma nota muda.** Dois dos três defeitos são meus, dos PRs de ontem.

### A — diários noturnos cancelados aos 90 minutos

`coletar_diarios_consorciados.py --desde 2026-06-29` consumiu **87 dos 90 minutos** do teto e o job foi
cancelado a segundos do fim. A data fixa era minha, e o erro é de tipo conhecido: **data fixa em YAML
envelhece**. Escrita em 28/09, ela mandava revarrer três meses **a cada noite**, e a cada semana
pioraria.

O orquestrador antigo nunca fez isso: `atualizar.py` sempre passou uma **janela corrida de oito dias**,
que é o que faz sentido para um coletor que roda todas as noites — a janela cobre o atraso de publicação
do diário, não o histórico. O coletor ganhou `--desde-dias N`, contado do corte editorial para trás,
com `--desde` explícito mantendo precedência para reprocessar período nomeado à mão. Recusa `0`,
negativo e não-número, e o autoteste cobre os quatro casos de recusa mais a precedência.

### B — auditoria semanal de segurança falhando depois de passar

A auditoria rodava com sucesso e o job reprovava **depois dela**, no passo posterior do
`setup-python`: `Cache folder path is retrieved for pip but doesn't exist on disk`. Causa: o §267 pôs
`cache: pip` em todos os workflows com Python, e este **não instala dependência nenhuma** — roda com a
biblioteca padrão. Sem instalação, não há cache para salvar, e o passo posterior falha.

É exatamente a razão pela qual, no §267, deixei `publicar_previa` e `publicar_dominio_ensaio` fora do
cache de **npm** — e que não apliquei ao **pip**. `auditoria_seguranca.yml` e `medir_revocacao.yml`
perderam o `cache: pip`.

### C — Publicar dados

Os dois runs pararam em "Regenerar a cadeia canônica de derivados", e os dois estavam certos: a `main`
tinha derivado genuinamente obsoleto entre o §272 e o §275 — o painel na cadeia (§273) e o relatório da
execução no manifesto (§274). Com os dois consertos na `main`, a cadeia regenera sem diferença. A
confirmação de um run verde de ponta a ponta fica registrada depois que o §274 entrar.

### O padrão que atravessa A e B

Os dois defeitos nasceram de **generalizar uma regra sem olhar quem ela atinge**: pus uma data onde
precisava de janela, e pus cache onde não havia instalação. No mesmo dia eu já havia cometido o mesmo
tipo de erro no §270, ao ignorar binário de evidência cobrindo um só dos caminhos que preservam. A
correção de método é a mesma nos três: **antes de aplicar uma regra a um conjunto, listar o conjunto.**

## §275 · A regra que ignorava binário de evidência custou 1.496 páginas de prova · 28/09/2026

Classe **método e coleta**. Reversão do §270, no mesmo dia em que ele entrou. **Nenhuma nota muda, e
os 93 registros pontuáveis continuam com prova preservada** — mas isto é o defeito mais grave desta
sequência, e fica registrado como tal.

### O que aconteceu

O §270 pôs em `.gitignore` as extensões de binário sob `evidencias/`, com a publicação do lote mensal
de Release como substituta. Na **primeira noite** com a regra no ar,
`monitorar_imprensa_regional.py` preservou **1.496 páginas HTML**, indexou as 1.496 em
`data/evidencias.json` — e o git ignorou os arquivos. O índice passou a **afirmar cópia preservada que
não existia**, e `verificar_evidencias.py` reprovou a `main`.

### O erro foi de escopo, e eu o descrevi sem cumpri-lo

No próprio §270 eu escrevi que ignorar sem publicar o lote "faria a prova desaparecer com o runner", e
liguei o job de publicação ao `noturno_evidencias.yml`. Mas **qualquer** coletor que chama
`preservar_evidencia` produz binário: imprensa regional, imprensa de saúde, diários, o juiz. Cobri um
caminho e tranquei todos.

### O que foi feito

**A regra voltou atrás.** O binário é versionado de novo. `scripts/empacotar_evidencias.py`, o job de
publicação do lote e o portão do binário novo continuam no lugar — o portão passou a ser
**informativo**, e o cabeçalho dele diz por quê. A trava só volta quando a publicação do lote cobrir
todo caminho que preserva **e** `verificar_evidencias.py` souber aceitar "está no lote do mês" como
cópia preservada.

**As 1.496 viraram lacuna declarada.** `scripts/declarar_evidencia_perdida.py` moveu o caminho para
`arquivo_perdido`, zerou `arquivo` e escreveu a nota com o motivo e a data, seguindo a convenção que o
índice já usava desde 03/09/2026. **Nenhum item foi apagado:** hash, URL de origem, data e tamanho
ficam, porque é por eles que a re-preservação acha o que buscar e é a URL que permite a qualquer pessoa
conferir a fonte. O script não baixa nada e não marca nada como preservado — ele troca uma afirmação
falsa por uma lacuna declarada, que é o que a METODOLOGIA exige.

Índice: 4.932 itens antes e depois. `verificar_evidencias.py`: **93 de 93 registros pontuáveis com
evidência preservada**. As 1.496 eram pistas de imprensa — descoberta, nunca registro que pontua.

### O que isto ensina, e que vale mais que o conserto

Afirmação de prova sem prova é o pior defeito possível neste projeto, e ele não veio de pressa nem de
descuido de digitação: veio de eu ter **descrito o risco com precisão e implementado a proteção pela
metade**. A regra de ouro a tirar daqui é de ordem, não de intenção: **nunca desligar o caminho antigo
de preservação antes de o novo cobrir todos os produtores** — e, quando a substituição for de prova,
conferir que a prova chegou ao novo lugar antes de tirá-la do antigo.

## §274 · O manifesto não sela relatório de execução · 28/09/2026

Classe **infraestrutura da rodada**. Correção do §266, achada pela **segunda** execução do
`publicar_dados.yml`. **Nenhuma nota muda.**

### O defeito

O §273 tirou o painel de saúde da cadeia canônica, e a execução seguinte reprovou de novo no portão 12
— agora por uma linha a mais no manifesto. O manifesto é gerado por glob sobre `data/*.json`, e
`data/saude_pipeline.json` passou a existir: é ele que cada passo da rodada preenche com a sua linha de
saúde. O passo que recalcula o índice escreve a linha, e a regeneração seguinte encontra o manifesto
diferente do commitado.

### A razão de fundo, que é a que importa

Não é só um problema de ordem de passos. **O manifesto sela prova** — o dado, as páginas, os derivados
publicados, as evidências. **Quanto tempo um script levou não é prova de nada sobre o índice.** Selar o
relatório da execução confunde as duas coisas, e o sintoma (portão 12 vermelho toda rodada) é o aviso.

Saem do manifesto, declarados em `FORA`:

- `data/saude_pipeline.json` — relatório da execução em curso;
- `docs/SAUDE_PIPELINE.md` — o painel que o resume, e por uma segunda razão: desde o §273 ele é gerado
  **depois** dos portões e **antes** do commit, então selá-lo deixaria o manifesto obsoleto na rodada
  seguinte, com o painel mudando no commit e o manifesto sem acompanhar.

`data/log_buscas_resumo.json` **continua selado**, e a distinção é a mesma do §273: ele é função do log
**commitado**, não da execução em curso.

### Sobre as duas correções seguidas

O §266 entrou com um erro de classificação — tratei relatório de execução como derivado de dado — e ele
produziu dois sintomas em duas execuções: primeiro o painel na cadeia, depois o seu insumo no manifesto.
Os dois só apareceram porque o pipeline passou a rodar desacoplado, na ordem de verdade. A suíte local e
o CI do PR não os encontrariam: em nenhum dos dois existe um passo anterior da mesma execução
escrevendo o arquivo.
## §273 · O painel de saúde sai da cadeia canônica · 28/09/2026

Classe **infraestrutura da rodada**. Correção do §266, achada pela **primeira execução real** do
`publicar_dados.yml`. **Nenhuma nota muda.**

### O defeito, e por que o portão estava certo

Pus `docs/SAUDE_PIPELINE.md` na cadeia canônica de derivados. Na primeira execução do publicador, o
portão 12 reprovou: a regeneração alterava o painel e o manifesto.

A razão é estrutural, não um carimbo desatualizado. O portão 12 cobra que **regenerar não altere nada
versionado** — e isso só pode valer para derivado que é função do **dado commitado**. O painel é
relatório da **execução em curso**: o passo que recalcula o índice grava a própria linha de saúde, e a
regeneração seguinte encontra o painel legitimamente diferente do commitado. Derivado que muda durante a
própria rodada não cabe naquele invariante.

### A correção

O painel sai da cadeia (e da constante `CADEIA_DERIVADOS` do orquestrador, que tem de ser idêntica) e
passa a ser gerado **depois dos portões e antes do commit**, nos dois workflows que commitam:
`publicar_dados.yml` e `_coletor.yml`. Ele continua versionado e continua sendo o painel que a editoria
abre — só deixa de ser cobrado por uma regra que não se aplica a ele.

`data/log_buscas_resumo.json` **fica** na cadeia, e a diferença importa: ele é função do log
commitado, não da execução em curso. O publicador não escreve no log de buscas.

### O que isto diz sobre o §266

A revisão do §266 passou nos portões locais e no CI do PR porque em nenhum dos dois o painel havia sido
escrito por um passo anterior da mesma execução — o defeito só aparece quando o pipeline roda de
verdade, na ordem de verdade. É o argumento a favor de ter desacoplado: a primeira execução do
publicador novo encontrou, em cinco minutos, um defeito que a suíte não encontraria.

**O domínio foi republicado nessa mesma execução** e está conferido: `HTTP/1.1 401` com
`Www-Authenticate: Basic`. O passo de reposição tem `if: always()` justamente para isso — falha em
passo anterior não deixa o domínio no ar errado.

## §272 · Os horários da janela deixam de colidir no mesmo minuto · 28/09/2026

Classe **infraestrutura da rodada**. Correção do §265, achada por auditoria dos próprios horários que
eu acabara de instalar. **Nenhuma nota muda.**

### O defeito

Quatro pares de workflows caíam no **mesmo minuto**: `publicar_dados` às 22h00 e 06h00 em ponto, junto
com a rodada da busca web (que roda às 22h, 0h, 2h, 4h e 6h); a rodada completa de domingo às 0h00,
junto com a busca web; e o semanal de sinais e links às 4h00, também junto.

Colisão no mesmo minuto **não cancela nada** — os grupos de concorrência são separados, e foi o §148
que os separou de propósito. Por isso ela nunca apareceria como falha: apareceria como rodada lenta e
como conflito de push, porque põe o publicador **lendo enquanto a busca commita** — exatamente o cenário
de "main em movimento" que o laço de rebase-e-push do item 1a existe para sobreviver. Fazer o laço
trabalhar por descuido de agenda é desperdiçar a rede de proteção.

### A correção

Só os **minutos** mudam: `publicar_dados` às 22h05 e 06h05, semanal às 4h30, rodada completa de domingo
às 0h10. **As horas não mudam, e isso é deliberado:** 06h e 22h são compromisso público, declarado em
`obrigado.html` e na METODOLOGIA, e o dia de domingo é o que o portão
`scripts/testar_cadencia_publicacao.py` cobra contra a frase pública.

### O portão

`scripts/validar_workflows.py` passa a reprovar dois workflows agendados no mesmo minuto do mesmo dia.
Ele cobra o minuto e deixa a hora livre. Conferido com uma colisão injetada: reprova nomeando os dois
arquivos, e volta a passar quando ela sai.

## §271 · Poda: um órfão para o arquivo, e a consolidação que não se faz · 28/09/2026

Classe **infraestrutura da rodada**. Item 6 do handover de desacoplamento (27/09/2026), que dependia
do item A da auditoria do funil. **Nenhuma nota muda.**

### O único órfão de verdade

`scripts/caderno_de_pistas.py` é o único arquivo do repositório que se menciona a si mesmo e a mais
ninguém: nenhum workflow o chama, nenhum script o importa, e a saída é um `.md` não versionado na raiz.
Era material de trabalho de uma sessão que passou — a leitura assistida das pistas hoje é
`revisar_pistas.py --preparar --relatorio` (§153) e, desde 27/09, o juiz automático (§262).

Foi para `arquivo/scripts/`, **não apagado**: a rotina de julgamento §5 que ele descreve continua
valendo, e o formato pode servir de referência. O cabeçalho dele agora diz por que está ali.

### Um que PARECIA órfão e não é

`gerar_lai.py` não é chamado por workflow nenhum da rodada, e só a CI o testa. É **por desenho**: o
pedido de LAI é redigido quando a editoria decide pedir, não a cada rodada. O cabeçalho passou a dizer
isso, porque a ausência de chamador, sozinha, não distingue "esquecido" de "acionado por pessoa" — e a
auditoria precisou de leitura à mão para separar os dois. Esse é o limite declarado do mapa automático.

### A consolidação dos `gerar_*.py` NÃO foi feita, e a razão é positiva

O item pede consolidá-los num só ponto de entrada "se o ganho for real". **Não é:** o ponto de entrada
único já existe e é `scripts/verificar_derivados.sh`, a cadeia canônica que o portão 12 cobra. Criar um
segundo ponto de entrada criaria uma segunda lista a manter em sincronia — e o invariante do §163
existe justamente porque duas listas divergiram e deixaram o portão 12 vermelho na `main`. Consolidar
aqui trocaria uma cadeia conferida por portão por duas listas a conciliar.

### O que fica para a editoria

`descobrir_dominios.py`, `coletar_espin.py` e `classificar_planos_municipais.py` produzem dado que a
rodada usa (`dominios_oficiais.json`, `saude_sinais.json`) e **só rodam na CI** — a última busca ativa
de domínio registrada é de 23/09. Não são órfãos: são coletores sem cadência. Colocá-los numa rodada
noturna é decisão de produto (quanto o dado deles precisa envelhecer antes de importar), e está
registrada como pendência no relatório do funil.
## §270 · Evidência: o binário sai do git, o texto fica · 28/09/2026

Classe **infraestrutura da rodada**. Item 3 do handover de desacoplamento (27/09/2026).
**Nenhuma nota muda, e nenhuma prova é perdida.**

### O que foi medido

`evidencias/` tem **1,5 GB em 3.755 arquivos**; o pack do git passa de **1 GB**. A separação que decide
o item: **1,25 GB são binários** — 1,0 GB de PDF (619 arquivos) e 254 MB de HTML — contra **10,9 MB de
texto extraído** (101 de texto, 6 de OCR). Presentes no disco e indexados: 2.772 binários, 1.255 MB,
todos de setembro.

### A regra

**O texto continua no git.** É insumo do pipeline — `preservar_evidencias.py --ler`,
`scripts/preservar_textos_integrais.py` e a classificação de saúde leem o texto, não o binário —, e o
§10.1 já dizia "a cópia do binário só até 5 MB, o texto sempre".

**O binário novo não entra.** Vai para o ativo de Release do mês (`evidencias-AAAA-MM.zip`, com
`INDICE.tsv` dentro: hash, arquivo, URL de origem, data, tamanho, origem), e o índice
`data/evidencias.json` continua no git com tudo isso.

### Release, e por quê

O handover deixou a escolha ao Code — ativo de Release ou repositório separado. **Release**, e a razão é
medida: nenhum script da rodada precisa do binário num checkout; o que eles leem é o texto, que fica.
Repositório separado só se justificaria se precisassem. Release dá URL estável, ativo de até 2 GB, sem
clone e sem custo.

### A ordem importa: upload antes do ignore

Ignorar binário novo no git **sem** publicar o lote faria a prova desaparecer com o runner. Por isso o
`noturno_evidencias.yml` ganhou um job que monta o lote do mês e o publica como ativo **antes de o job
terminar**, com `--clobber` porque o lote é cumulativo, não incremental. O `.gitignore` só é seguro
porque esse passo existe.

`scripts/empacotar_evidencias.py` confere que o **sha256 de cada arquivo bate com a chave do índice**
antes de empacotar: hash que não bate fica fora do pacote e é acusado. Ele **não publica sozinho** —
imprime o comando, e publicar exige credencial.

### O que NÃO foi feito, e por que depende da editoria

Duas coisas ficam esperando a palavra dela, e são as duas que dariam o ganho de peso:

1. **Remover da árvore os 1,25 GB já commitados.** É o que faria o clone raso caber no critério de
   aceite do item ("< 1 min"): clone raso não baixa histórico, mas baixa a árvore atual. A remoção é
   reversível pelo histórico, mas apagar 1,25 GB de prova preservada é ação que não se toma sozinho —
   e o caminho seguro é: publicar o lote de setembro como Release, conferir que ele está lá, e só então
   remover.
2. **Reescrever o histórico** para encolher o pack de 1 GB. O próprio handover proíbe fazer agora:
   é irreversível, exige decisão da editoria e clone novo em todas as máquinas. Fica anotado como opção
   para depois do lançamento.

Três portões novos (97 no total). O portão do binário roda contra `origin/main`, não contra o índice:
é o diff do PR que interessa.

## §269 · O log de buscas em JSONL mensal · 28/09/2026

Classe **infraestrutura da rodada**. Item 4 do handover de desacoplamento (27/09/2026).
**Nenhuma nota muda:** `recalcular_mare.py --check` reproduz os 27 estados × 7 campos idênticos,
média 46,6, lendo o log pela porta nova.

### O que foi medido

`data/log_buscas.json`: **30,8 MB** num único JSON, **50.849 execuções**, lido **e regravado inteiro**
a cada execução registrada — por vários coletores, a cada rodada. Além do tempo, o risco: erro de
escrita no meio põe em risco o arquivo todo, e foi assim que `fontes_consultadas.json` se corrompeu em
21/09 (368.019 para 166.961 linhas).

### Uma linha por execução

Cada execução vira uma linha em `data/log_buscas/AAAA-MM.jsonl`. **Append puro:** o arquivo do mês
cresce no fim e nada antes é reescrito. `ler_log()` concatena os meses — e o monólito antigo, enquanto
existir — e devolve a **mesma forma de antes**, então nenhum dos oito leitores precisou mudar de
lógica, só de porta.

O monólito **não foi apagado**: ficou com `execucoes: []`, um campo `migrado_para` e 280 bytes.
Apagá-lo quebraria quem ainda o abre direto, e a porta única já o soma enquanto ele existir.

### A migração foi conferida, não confiada

`scripts/migrar_log_para_jsonl.py` só esvazia o monólito **depois** de conferir paridade de contagem,
e a conferência é condição: se não fechar, nada é tocado. Medido: **50.849 antes, 50.849 depois**. A
ordem dentro de cada mês é a do arquivo original — o log é append-only e "a última execução deste
canal" é pergunta real, que reordenar responderia errado.

### O portão que o formato novo exige

Com o log fatiado, **perder um arquivo de mês passaria sem ruído**: o JSON continuaria válido, só
menor. `scripts/verificar_paridade_log.py` guarda uma marca d'água (maior total já visto, e por mês) e
reprova se a contagem encolher — no total **ou em qualquer mês**, porque o total pode crescer enquanto
um mês perde linhas. Linha inválida também reprova: `ler_log()` a ignora para não estourar, mas linha
perdida é dado perdido. É o mesmo defeito de 23/09, quando uma união por conteúdo produziu um log
menor que cada um dos lados e apagou quase 3.000 execuções sem aviso.

### A página parava de baixar 30 MB

`defesa-civil.html` mostrava dois números — total de execuções e divisão por canal da última rodada —
e para isso o navegador do leitor baixava o log **inteiro**. Agora lê `data/log_buscas_resumo.json`,
derivado, com 376 bytes. Os números são os mesmos. O link público passa a apontar o resumo e o texto
diz onde está o registro completo: arquivos mensais em `data/log_buscas/`, no formato `AAAA-MM.jsonl`.

O resumo é derivado, e derivado novo na cadeia obriga a mexer em **duas** listas: a de
`scripts/verificar_derivados.sh` e a constante `CADEIA_DERIVADOS` de
`julgar_e_aplicar_descobertas.py`, que o juiz usa para regenerar antes de aplicar. Mexi só na primeira
e o autoteste do orquestrador reprovou — é o invariante do §163, que existe porque essa divergência
deixou o portão 12 vermelho na `main` em 22/09/2026. Cometi o mesmo esquecimento nos dois PRs do dia
que acrescentam derivado.

`scripts/testar_lote_de_escrita.py` também precisou mudar de porta, e eu esqueci: ele contava
gravações espiando `gravar()` e conferia a contagem abrindo o monólito, então cinco dos seus casos
reprovaram no CI. O cofre do teste passou a espiar **também** `acrescentar_ao_log()`, registrando com o
mesmo nome de sempre, e a contagem sai de `ler_log()`. Os testes continuam fazendo a pergunta de
sempre — "quantas gravações do log aconteceram" e "quantas execuções o log tem" — sem saber do formato.

Quatro portões novos (96 no total): autoteste da migração, do resumo, do portão de paridade, e o
portão de paridade rodando de verdade.
## §268 · Disjuntor por motor de origem da busca web · 28/09/2026

Classe **método e coleta**. Item 7b do handover
`notas/HANDOVER_juiz_automatico_e_busca_web_27-09-2026.md` (decisão da central, 28/09/2026).
**Nenhuma nota muda.**

### Por que não bastava reduzir as consultas

O §264 cortou de nove strings para três e pôs ritmo, e ao fazê-lo eu disse uma coisa que continuava
verdadeira: **nenhum motor de origem foi desligado, porque desligar sem saber qual barrou é
adivinhação.** A central respondeu com a regra que transforma isso em medição.

### A regra

- **Sentinela.** No início de cada rodada, uma consulta fixa **por motor** —
  `"Brasil" "defesa civil" plano de contingência`. Qualquer motor em funcionamento responde; sentinela
  vazia é motor mudo. Ela não nomeia município nenhum, e é isso que a torna interpretável: "vazio"
  aqui nunca pode ser lido como "o município não tem plano".
- **Contagem.** Por motor, durante a rodada: 429, CAPTCHA, timeout e corpo vazio. Quem não respondeu
  vem no campo `unresponsive_engines` da própria resposta do SearXNG.
- **Queda.** Mais de **50%** de falhas numa rodada, **ou** sentinela muda em **duas** rodadas
  seguidas: **24 h desligado**, e volta sozinho com nova sentinela. O teto é "acima de 50%", não "a
  partir de" — e há caso de teste para exatamente 50%.
- **Piso de dois.** Nunca se desligam todos. Se as quedas levariam a menos de dois ativos, as de menor
  taxa de falha são poupadas, **e o fato de terem sido poupadas fica escrito no estado**. Com menos de
  dois ativos a rodada encerra registrando `motor_sem_resposta`: afirmar "não localizamos" tendo
  perguntado a um motor só seria declarar ausência sem ter perguntado.

### Desligar sem desligar em disco

O desligamento é por **requisição** — o parâmetro `engines` da consulta —, não por edição de
`scripts/searxng_settings.yml`. Nada fica desligado em disco, a volta depois de 24 h é automática, e
um autoteste inspeciona a URL montada para provar que o parâmetro é enviado: sem ele o disjuntor
decidiria e o SearXNG continuaria consultando todos.

A lista de ativos e desligados, com o motivo de cada queda, fica em `data/busca_web_motores.json` e no
resumo do job da cadência. **O `docs/MANIFEST_SHA256.txt` não recebeu nada:** ele é selo de hash, não
quadro de situação, e enfiar estado mutável ali quebraria o que ele serve para provar.

Dezenove casos de autoteste no disjuntor e um novo no coletor; um portão novo (92).

## §267 · Ambiente reprodutível e mais rápido · 28/09/2026

Classe **infraestrutura da rodada**. Item 5 do handover de desacoplamento (27/09/2026).
**Nenhuma nota muda.**

Três das quatro exigências do item já estavam cumpridas, e vale dizer quais para não parecer que
foram feitas agora: `requirements.txt` tem **versões travadas** desde 27/08/2026, com a razão de cada
travamento escrita ao lado e documentada em `docs/SBOM.md`; a versão do Python está **fixada em
3.12** em todos os workflows; e o `apt` instala só o que o OCR precisa — `tesseract-ocr` e
`tesseract-ocr-por`, nada além.

O que faltava era o **cache**. `actions/setup-python` e `actions/setup-node` sabem cachear pip e npm a
partir do lockfile, e nenhum workflow pedia isso: cada job baixava as onze dependências Python e o
`node_modules` inteiro de novo. Agora os oito jobs com Python e os cinco que rodam `npm ci` pedem o
cache.

**Dois workflows ficaram de fora do cache de npm, de propósito:** `publicar_previa.yml` e
`publicar_dominio_ensaio.yml` não instalam dependência nenhuma — usam `npx --yes netlify-cli@17`, que
baixa a ferramenta na hora. Cache ali não economizaria nada, e pedir cache onde não há instalação é
enfeite de configuração.

### Um portão contra o erro que eu cometi duas vezes hoje

`git add -A` marca o caminho como **resolvido** mesmo quando o conteúdo ainda tem `<<<<<<<`,
`=======` e `>>>>>>>`, e `git commit` então aceita sem reclamar. O `CHANGELOG.md` subiu assim **duas
vezes** em 28/09/2026, nas duas uniões de ramo que atravessavam vários PRs. Não é distração que se
corrige prometendo atenção: é ausência de verificação.

`scripts/verificar_marcadores_de_conflito.py` varre os arquivos **rastreados pelo git** e acusa
caminho e linha. Ele procura a abertura e o fechamento, não o `=======` sozinho — esse aparece em
texto legítimo (sublinhado de título em Markdown, régua em docstring), e portão que acusa texto
legítimo deixa de ser lido. Entra como **primeiro** portão de página: é barato e evita que tudo o que
vem depois analise um arquivo que nem está resolvido.

Meta do item: instalação abaixo de 1 min por job. Ela **não está medida** — o cache só produz efeito a
partir da segunda execução, e a comparação antes/depois entra em `notas/ESTADO_ATUAL.md` quando as
próximas rodadas noturnas tiverem número.
## §266 · Painel de saúde do pipeline · 28/09/2026

Classe **infraestrutura da rodada**. Item 2 do handover de desacoplamento (27/09/2026).
**Nenhuma nota muda:** o painel mede o pipeline, não pontua nada.

O §265 fez cada script gravar a sua linha de saúde. Aqui essas linhas viram
`docs/SAUDE_PIPELINE.md`, arquivo **derivado** (entra na cadeia canônica, antes do manifesto, e não
se edita à mão): uma linha por script com a última execução, duração, itens, status e o resumo do
erro — mais o histórico de sete dias que `data/saude_pipeline.json` guarda.

### Duas classes, porque a diferença importa

**Essencial** — `recalcular_mare.py` e os `gerar_*.py`: se um deles erra, o site publica um estado
que não corresponde ao dado. O portão **reprova**.

**Coletor** — todo o resto: fonte fora do ar é rotina, e uma falha isolada não é defeito do
pipeline. Erro em **duas rodadas seguidas** vira **alerta**, porque aí não é a fonte, é o coletor. A
sequência zera no primeiro sucesso: falhas alternadas não alertam, e isso é deliberado — alerta que
dispara por intermitência de fonte deixa de ser lido.

O painel é derivado, e derivado novo na cadeia obriga a mexer em **duas** listas: a de
`scripts/verificar_derivados.sh` e a constante `CADEIA_DERIVADOS` de
`julgar_e_aplicar_descobertas.py`, que o juiz usa para regenerar antes de aplicar. Eu mexi só na
primeira, e o autoteste do orquestrador reprovou — é exatamente o invariante do §163, criado porque a
divergência entre as duas deixou o portão 12 vermelho na `main` em 22/09/2026.

Dezessete casos de autoteste, entre eles os que separam as duas classes (`regerar_algo.py` **não** é
essencial: `gerar` tem de começar o nome), o que confere que a sequência de erros zera no sucesso, e
o que garante que `itens` nulo apareça como travessão e nunca como zero — no painel como no dado,
"não medido" e "zero" são coisas diferentes.

## §265 · O pipeline desacoplado, e a rodada só na janela noturna · 28/09/2026

Classe **infraestrutura da rodada**. Handover
`notas/HANDOVER_desacoplar_pipeline_e_emagrecer_repositorio_27-09-2026.md`, itens 1, 1a e 1b
(repositório privado). Cadência aprovada pela editoria em 27/09/2026 (noite). **Nenhuma nota muda.**

### O que foi medido

`atualizar.yml`, 789 linhas, quatro execuções por dia: **mediana de 92 min, máximo de 240**; de 12
execuções medidas, **sete canceladas, duas com falha, uma com sucesso**. A causa é aritmética: a
cadência era de 6 h e a duração de 1,5 a 4 h, então execuções se sobrepunham — e execução pendente é
cancelada quando a seguinte chega. Um job monolítico com cerca de trinta scripts em sequência também
tem a propriedade de que uma fonte lenta derruba tudo o que vem depois dela.

### Jobs independentes

Cada coletor passa a ter job próprio, teto curto, `continue-on-error` por script, a sua saída e a sua
**linha de saúde**. O workflow reutilizável `_coletor.yml` carrega a parte comum:

| workflow | hora (Brasília) | o que roda |
|---|---|---|
| `noturno_diarios.yml` | 22h30 | diários municipais, consorciados, DOE, S2iD |
| `noturno_descoberta.yml` | 23h30 | imprensa, agregadores, sítios oficiais, triagem |
| `noturno_evidencias.yml` | 1h | baixar, ler texto e OCR, em lotes pequenos |
| `noturno_juiz.yml` | 3h | preparar pistas, aplicar descobertas, juiz, amostra semanal |
| `semanal_sinais_e_links.yml` | domingo 4h | clima municipal e verificação de links |
| `publicar_dados.yml` | 6h e 22h | recalcular, derivados, portões, publicar |

**Concorrência por papel:** coletor usa fila (`cancel-in-progress: false`) porque coleta
interrompida perde o que já achou; o publicador é o único que cancela o anterior, porque publicar
duas vezes o mesmo estado não tem valor. **Nenhum job espera pelo término de outro**: "depois dos
diários" é por horário, não por dependência. O que não chegou fica com a data anterior, declarada.

`atualizar.yml` **não foi apagado**: perdeu as quatro execuções diárias e ficou com o semanal de
domingo (que o item 1b mantém) e o disparo manual, para reprocessar um dia inteiro ou investigar. O
monólito continua reversível — foi o `schedule` que saiu, não o arquivo.

### Item 1a: a rodada não falhava na coleta, falhava no commit

Diagnóstico adicional da central: o run 36338485886 passou por **todas** as etapas de coleta e perdeu
tudo no passo 37, depois de 3h45 — entre o início e o commit entraram três PRs e duas rodadas de
busca web na `main`. Por isso o commit de cada job é um **laço de rebase-e-push**, com até cinco
tentativas e espera crescente; conflito em arquivo de dado gerado se resolve **regenerando** depois
do rebase, nunca à mão. Se as cinco falharem, o job grava as saídas como artefato e falha com uma
mensagem única: `commit perdido para main em movimento`.

### Item 1b: janela noturna, regime permanente

Coleta e commit automáticos **só entre 22h e 6h de Brasília**. A busca web passa de 12 rodadas por
dia a qualquer hora para 5 dentro da janela (1, 3, 5, 7 e 9 UTC), 150 municípios cada: 750 por noite,
ciclo completo a cada ~7,5 dias. Entre 6h e 22h não há commit automático na `main`.

O registro é obrigatório porque cadência é compromisso público: `METODOLOGIA.md` recebeu o regime
datado, com a ordem declarada da fila de re-varredura, e `obrigado.html` diz ao leitor a janela e as
duas publicações diárias. A frase que o portão `testar_cadencia_publicacao.py` cobra — o domingo da
duas publicações diárias. A primeira versão dessa frase levou a página a 166 palavras e o portão
`verificar_palavras.js` reprovou (teto 160) — reescrita mais curta, 151 palavras, sem perder a janela,
os horários nem a data da decisão. A frase que o portão `testar_cadencia_publicacao.py` cobra — o domingo da
atualização completa — continua valendo e continua verdadeira.

### Uma linha de saúde por script

`scripts/saude_pipeline.py --rodar <script>` cronometra, captura a saída, conta os itens que o
próprio script relatou, resume a linha decisiva do erro e devolve o **mesmo** código de saída. Sete
dias de histórico em `data/saude_pipeline.json`. `itens` nulo é "não medido", nunca zero. É sobre
estas linhas que o painel do item 2 será construído.

### Um erro meu no caminho, porque ele quase apagou o registro

Ao inserir esta seção, um script de edição avaliou `open(arquivo, "w")` **antes** de montar o texto a
escrever, e a expressão do texto levantou exceção: o `CHANGELOG.md` foi truncado a zero byte e o
arquivo vazio entrou num commit. Recuperado do commit anterior, íntegro, com as 4.972 linhas. A lição
é de método, e vale para toda edição programática de arquivo grande: **montar o conteúdo inteiro
primeiro, abrir para escrita depois** — e o `assert` de âncora, que o PROTOCOLO já exige, precisa vir
antes de qualquer abertura em modo de escrita.
## §264 · Busca web: ritmo, não volume · 27/09/2026

Classe **método e coleta**. Decisão da central de 27/09/2026 (noite), handover
`notas/HANDOVER_juiz_automatico_e_busca_web_27-09-2026.md`, PR 1c — resposta ao alerta que o §261
produziu. **Nenhuma nota muda.**

### O que foi medido

A primeira rodada com o leque de nove strings do §261 devolveu **139 de 150 consultas sem resposta
do motor (93%)**. A causa não são as strings: nove consultas por município sobre 150 municípios em
poucos minutos somam cerca de 1.350 requisições, que a instância efêmera repassa aos motores de
origem — e o runner do GitHub compartilha endereço. É limite de taxa.

### O que muda

- **Cascata com parada precoce.** As strings rodam em ordem e param na primeira que devolve pista.
  Sem pista, a cascata vai até o fim — é o caso da maioria, e é por isso que o conjunto da rodada
  encolheu.
- **Três strings na rodada**, provisórias até a medição: `"plano de contingência"` ·
  `"período chuvoso" OR estiagem OR seca plano` ·
  `PLANCON OR "plano de ação" OR "plano de enfrentamento"`. O leque de nove passa a viver em
  `CONSULTAS_MEDICAO` e **não roda na rodada**.
- **Ritmo:** 3 s com jitter de ±1 s entre consultas; back-off exponencial de 10 s, 30 s e 90 s ao
  primeiro 429, CAPTCHA ou **corpo vazio** — corpo vazio conta porque recusa servida com 200 é
  recusa (§186, §187). O back-off volta a zero quando o motor responde.
- **Sonda** nos primeiros 20 municípios: acima de 25% de mudo, pausa de 10 min e retoma; acima de
  novo, a rodada encerra, o restante do lote recebe `motor_sem_resposta` com linha declarada no log,
  e o lote volta ao **topo** da fila da rodada seguinte.
- **Prioridade da fila:** município que ficou com motor mudo volta primeiro. Deixá-lo esperar a
  volta inteira do ciclo trataria "não perguntamos" como "não achamos". Os **139** da rodada de 93%
  já estão marcados em `data/busca_web_espera.json`.
- **Instância** (`scripts/searxng_settings.yml`): `request_timeout` explícito de 6 s
  (`max_request_timeout` 12 s) e pool declarado. O limitador interno continua desligado, agora com a
  razão escrita: ele protege instância pública de abuso, e esta é local e efêmera — ligado, barraria
  a rodada sem que nenhum motor de origem tivesse reclamado. O limite que importa é o dos motores, e
  esse se respeita no cliente.
- **Evidência para a escolha de motores.** Desligar motor exige saber qual barrou, e o log do
  contêiner morria com o job. A cadência passa a publicar no resumo do job quais motores devolveram
  429, CAPTCHA ou timeout. **Nenhum motor foi desligado neste PR** — fazê-lo agora seria adivinhação.

### A medição sai de job próprio

`.github/workflows/medir_revocacao.yml` (`workflow_dispatch`, instância dedicada, 5 s entre
consultas, teto de 120 min) roda o leque de nove sobre 60 municípios — os 30 da amostra manual do
item D e 30 com plano já registrado — e publica revocação por string como artefato e no resumo do
job. Critério de adoção declarado: **conjunto mínimo que recupere ao menos 95%** do que o leque
recupera. A troca do provisório pelo definitivo vem por PR, com o número no CHANGELOG.

`PAUSA_ENTRE_CONSULTAS` saiu: era o órfão que esta mudança criou. Quatro autotestes novos (17 no
total no coletor): cascata e leque separados, ritmo e back-off, os três sinais de limite de taxa, e
uma trava de unidade para a pausa da sonda — 10 ali seriam 10 segundos, não 10 minutos.

## §263 · Instrumentação do funil: a rodada conta por etapa · 27/09/2026

Classe **método e coleta**. Decisão editorial de 27/09/2026, handovers
`HANDOVER_juiz_automatico_e_busca_web_27-09-2026.md` (PR 3) e
`HANDOVER_auditoria_funil_de_coleta_27-09-2026.md` (item B), repositório privado.
**Nenhuma nota muda:** contagem mede o funil, não pontua.

### O que a auditoria mediu e que este PR conserta

A pergunta da editoria — "os coletores estão de fato encontrando os planos?" — não tinha como ser
respondida sem abrir o código, e duas cegueiras mostraram por quê:

- **`descobrir_planos.py` está agendado quatro vezes ao dia e tinha UMA execução em todo o
  `log_buscas.json`** — e essa única era de uma triagem autorizada à mão em 19/09. O coletor rodava
  e não registrava o que fazia. Agora registra: contagem por etapa e uma linha no log por execução,
  com alvos consultados, achados inéditos e o tamanho da fila acumulada.
- **`motor_de_busca` parou em 05/09, e as três últimas execuções são `erro`.** O canal morreu e
  ninguém foi avisado. O alerta do portão do funil sobre etapa com histórico que devolve zero
  (§261) é o que passa a avisar; a causa do erro fica como pedido separado.

### As etapas instrumentadas

`funil.registrar(...)` entra em cinco coletores, com os contadores que cada um já calculava:

| etapa | contagens |
|---|---|
| `querido_diario` | entradas, com cobertura, UFs varridas |
| `diario_municipal` | consultados, lacunas, decretos novos, pistas |
| `diario_consorciado` | fontes, pistas, decretos novos, bloqueadas, fora do ar |
| `doe` | UFs consultadas, UFs com resultado |
| `descobrir_planos` | alvos consultados, achados novos, fila acumulada |
| `busca_web` | (§261) consultas, com resultado bruto, motor sem resposta, pistas, cobertos, espera, lacunas, brutos por string |
| `juiz` | (§262) pistas recebidas, com documento, promovidas, recusas por critério |

### O portão dos autotestes isolados pegou a contagem

O primeiro CI do §263 reprovou em `verificar_autotestes_isolados.py` (§220, §228): os autotestes de
`coletar_diarios_municipais.py` e `coletar_diarios_consorciados.py` chegam ao fim do caminho
principal, e a contagem do funil acabava escrita em `data/funil/<data>.json`. Autoteste offline não
toca em `data/`, nem por um contador.

A guarda ficou numa porta só — `funil.registrar` não escreve quando o processo roda com
`--autoteste` **e** o destino é o `data/` do repositório —, em vez de um mock por autoteste: cinco
coletores estão instrumentados hoje e qualquer outro herda a proteção. A primeira versão da guarda
olhava só o modo e barrava também o autoteste do próprio `funil.py`, que escreve num diretório
temporário; a condição correta é o destino, e o autoteste agora cobra as duas coisas (no
temporário a escrita tem de acontecer; em `data/`, não).

A conferência passa a rodar **dentro da rodada**, não só na CI do PR, com `continue-on-error`: a
contradição aparece no log da rodada sem impedir o commit dos dados já coletados — o portão do PR é
que reprova de verdade. Soma dos tetos por passo: 253 min, dentro do teto de 300 do job.

### O portão media a saúde da rodada e reprovava todo PR

A primeira rodada com o conjunto de nove consultas mediu **139 de 150 consultas (93%) sem resposta
do motor**. O portão do funil fez o que devia — a rodada não conta como verificação da camada 4 —,
mas o arquivo `data/funil/<data>.json` é commitado pela rodada, e o portão roda também na CI de todo
PR. Resultado: um PR que não toca na busca web herdava a reprovação de uma rodada passada, e ficava
impedido de subir justamente o conserto.

O portão passa a ter dois modos. Em `--modo rodada`, o teto de 25% é **falha**: ali a mensagem
significa "esta rodada não conta", e é a rodada que precisa saber. No modo `pr` (padrão), é
**alerta**. O que reprova nos dois é **contradição na contagem** — mais cobertos sem menção do que
consultas com resultado bruto, ou mais promoções do que pistas com documento: contradição é defeito
do código que conta, não notícia sobre o motor.

**O 93% continua sendo um fato a decidir, e é da editoria.** Nove consultas por município em vez de
uma multiplicaram por nove o número de requisições à instância efêmera do SearXNG, e a hipótese
mais provável é limite de taxa do próprio metabuscador. Não mexi no conjunto de consultas por
iniciativa própria: adotar o **conjunto mínimo que recupere o máximo** era, no handover, uma decisão
que depende da medição de revocação — e essa medição é exatamente o que o motor mudo impede. Fica
como pedido separado, com três caminhos possíveis (espaçar as consultas, reduzir o lote, ou rodar a
medição num job próprio com a instância dedicada) para a editoria escolher.

### O que a auditoria achou e NÃO entra aqui

Um PR por defeito, como o handover pede. Ficam como pedido separado, listados em
`notas/preprint/funil/RELATORIO_2026-09-27.md`:

- **169 de 242 municípios (70%) com excerto reconhecido no diário não estão em lugar nenhum do
  funil** — nem no banco, nem em fila. É o achado de maior efeito sobre a cobertura, e é reparo de
  dado: reprocessar os 169 do log para a fila e deixar o juiz decidir.
- O `com_mencao` publicado (347) não é reproduzível a partir do log (400 execuções `com_excerto`,
  242 municípios distintos): três contagens com o mesmo nome, nenhuma documentada.
- `data/pistas_querido_diario.json` é declarada por `consultar_querido_diario.py`, **não existe** e
  nenhum outro arquivo do repositório a menciona.
- `scripts/caderno_de_pistas.py` é órfão (só ele mesmo se menciona no repositório inteiro).
- `dominios_oficiais` e `saude_sinais` só se atualizam quando a CI roda os coletores.

**Uma preocupação do §158 NÃO se confirmou:** dos 13 registros com canal `imprensa`, 12 são
`nao_verificado` e o único categorizado é um decreto, que pontua zero. Nenhum registro pontuável do
banco tem a imprensa como canal.

**Erro de método corrigido no próprio relatório:** a primeira reconciliação juntava as menções ao
banco pelo código IBGE e dava "0 registros". `data/municipios.json` **não tem código IBGE** — cada
registro é identificado por nome e UF. Refeita a junção, 35 dos 242 estão no banco, e o número do
achado caiu de 190 para 169.

## §262 · Juiz automático regrado da fila de pistas · 27/09/2026

Classe **método e coleta**. Decisão editorial de 27/09/2026, handover
`notas/HANDOVER_juiz_automatico_e_busca_web_27-09-2026.md` (PR 2), repositório privado.
**Nenhuma nota muda neste PR:** o juiz é entregue com os canários e o relatório; a aplicação sobre
as filas antigas roda depois, sob auditoria.

### O problema

627 das 675 pistas aguardavam leitura humana para promoção (R7). O funil descobre mais rápido do
que a editoria lê — e "descobriu mas não promoveu" é indistinguível de "não existe" para quem olha
o índice.

### R7 revisada

Promover a registro passa a ser decisão do **juiz automático** quando todos os critérios do
codebook passam **no documento primário**; falhou um, a pista fica, com o motivo visível; a
editoria audita amostra semanal e reverte por errata. A frase do §5.2.1 — "nenhuma promoção ocorre
sem leitura do documento primário" — continua verdadeira: a leitura é do juiz, no documento, nunca
no título ou na notícia.

**Falso positivo é pior que falso negativo.** Um plano não creditado se corrige na rodada seguinte;
um ato de resposta pontuado como preparação contamina o índice publicado. Nenhum modelo de
linguagem decide: `juiz.py` é regra versionada (`CODEBOOK_VERSAO = "1.0 (27/09/2026)"`).

### As oito etapas

0. documento primário em fonte oficial, preservado com hash, texto extraível
1. identidade do ente (é ela que impede o diário consorciado de creditar o município errado)
2. citação completa (§3.2), com a exceção do plano técnico sem número — data obrigatória sempre
3. autoridade do Executivo; colegiado é `executivo_pendente`
4. natureza, com o teste do objeto em três partes cumulativas
5. família de risco do ciclo, pela exposição do próprio município
6. categoria e data (§3, §5.3) — **sem tocar em peso, régua ou escada de créditos** (§12)
7. aplicar com rede de proteção — vive em `julgar_e_aplicar_descobertas.py`, que já a tinha
8. auditoria amostral semanal, em planilha cega

As etapas 0 a 6 são funções **puras** sobre o texto: é por isso que o juiz é testável sem rede.

### Quatro defeitos que os canários pegaram antes de qualquer promoção

Os dez canários — um documento por desfecho — não passaram de primeira, e o que eles acharam era
grave:

- **`RE_DECLARA_ANORMALIDADE` casava dentro de "não declara situação de emergência".** A negação
  precede a declaração; sem excluí-la, o juiz lia um plano preventivo como ato de resposta. Pego
  pelo canário `plano_readaptado`.
- **Multirrisco engolia o fora do objeto.** Um plano de geada diz "plano de contingência
  municipal" e caía na família multirrisco, que é a de menor especificidade — seria promovido.
  Agora família específica vence, e sem família específica o risco fora do objeto decide. O caso
  Salvador (03/09/2026) continua travado: plano multirrisco que lista arbovirose entre os riscos
  não é plano de arbovirose.
- **`citacao_completa` recebia "numero data" e reprovava tudo.** Ela exige o tipo do ato junto do
  número; a citação precisa ser remontada. Todos os dez canários reprovavam por isso.
- **Ano solto passava por data.** `extrair_data` devolve o ano quando não há data completa, e
  "versão 2026" não situa o ato no ciclo (§5.3). Agora só `dd/mm/aaaa` vale na Etapa 2.

### Dois consertos no classificador de natureza, ambos falso negativo

Também achados por canário, e ambos na direção segura (nada que pontuava deixa de pontuar):

- **A comparação por substring não via o disclaimer quebrado em duas linhas.** Diário oficial vem
  com quebra de linha, e "não configurando / situação de emergência" não casava com a forma de uma
  linha só. Normalizar o espaço em branco antes de comparar conserta isso para **todos** os sinais
  de uma vez, em vez de multiplicar variantes no dicionário.
- **Flexões do disclaimer preventivo** entraram no dicionário com origem e data.

Regressão conferida contra os registros reais: 122 planos, 108 reconhecidos, 14 em dúvida,
**0 erros**; 97 decretos de resposta, 56 rejeitados, 41 em dúvida, **0 falsos positivos** — os
mesmos números de antes.

### O juiz como barreira adicional, não como substituto

`julgar_e_aplicar_descobertas.py` continua decidindo e aplicando pelo caminho que tem testado
desde 31/08/2026. O juiz entra no caminho municipal como barreira **adicional**: só pode recusar o
que aquele caminho já aprovou. As etapas que ele acrescenta ali — identidade do ente, autoridade
do Executivo, família de risco — são exatamente as que faltavam, e as três derrubam falso positivo.

**Escopo declarado:** a unificação completa dos dois caminhos num só não entra neste PR. O
orquestrador antigo identifica a pista por `alvo` (rótulos estadual/municipal), não por município
mais UF; reescrevê-lo agora quebraria cinco fixtures e mexeria na máquina de rollback sem que o
relatório das filas já tenha mostrado quais formas de pista chegam lá. Fica como pedido separado.

### Duas portas gravando a mesma prova

A primeira versão preservava o texto julgado com `preservar_evidencia(..., ext="txt")`. O portão 26
(`verificar_evidencias.py`) reprovou, e a razão é séria: evidência de texto cuja URL termina em
`.pdf`, sem `texto_manual: true`, **seria sobrescrita** por `preservar_evidencias.py --ler`, que é
a porta canônica e guarda o binário. Duas portas gravando a mesma chave é como se perde prova.

O juiz deixa de preservar: ele calcula o hash do texto que julgou, para identificar no registro o
que leu, e a preservação continua com quem já a faz. Os 45 arquivos que a execução de teste havia
escrito saíram do commit.

Na mesma execução apareceu um segundo defeito: `--relatorio` escrevia enquanto imprimia "nada
escrito". O modo relatório passa a não preservar, não marcar a pista em memória e não gravar
arquivo de fila, com travas de autoteste sobre o código de `main()` para que a guarda não
desapareça em silêncio.

### Registro, amostra e contagem

Toda decisão vai para `data/promocoes_automaticas.json` com a pista, o documento (hash e URL), os
critérios 1 a 6 **com o trecho que satisfez cada um**, categoria, data e versão do codebook.
`scripts/amostra_auditoria_semanal.py` sorteia 10% das promoções e 10% das recusas (mínimo dez) em
planilha **cega** — os trechos, sem a decisão do juiz — com o gabarito em arquivo irmão, aberto
depois do preenchimento. Sem isso a auditoria mediria concordância com um rótulo já visto, que é
outra coisa, e é o E1 do preprint que depende dela. A amostra é reprodutível pela data.

`julgar_filas.py` roda o juiz sobre as quatro filas e conta por critério de recusa, alimentando a
etapa `juiz` de `data/funil/<data>.json`.

Três portões novos (88 no total): 10 canários mais 8 travas no juiz, 16 casos no executor das
filas, 14 na amostra semanal.

## §261 · Busca web: zero resultado não é ausência · 27/09/2026

Classe **método e coleta**. Decisão editorial de 27/09/2026, handover
`notas/HANDOVER_juiz_automatico_e_busca_web_27-09-2026.md` (PR 1), repositório privado.
**Nenhuma nota muda:** a camada 4 produz pista, nunca registro — e a correção retroativa mexe
só no log, não no banco.

### O defeito, medido

A camada 4 tinha duas decisões: `pista` quando algum resultado passava a peneira,
`coberto_sem_mencao` quando nenhum passava — **inclusive quando o motor não devolvia resultado
nenhum**. Medido no `data/log_buscas.json` de 21 a 27/09: das consultas da busca web, **5.329
voltaram com zero resultado bruto e receberam `coberto_sem_mencao`**, que é afirmação de
ausência. O motor mudo entrava no registro como cobertura.

### As quatro decisões

`decidir(n_brutos, n_pistas, rodadas_sem_pista)` é função pura, e por isso testável sem rede:

- `motor_sem_resposta` — zero resultado bruto em todas as strings, timeout, erro HTTP, instância
  que não subiu. A consulta **não conta como verificação** do município.
- `nao_localizado_ate_o_momento` — houve resultado bruto e nenhuma pista, primeira rodada nessa
  situação.
- `coberto_sem_mencao` — resultado bruto e nenhuma pista em **duas** rodadas. Só aqui a ausência
  é afirmável, e no teto do §3.2.
- `pista` — algum resultado passou a peneira.

O estado de espera por município vive em `data/busca_web_espera.json`; uma pista o zera.

### Nove consultas, e a peneira que aceita o trecho

Oito strings novas mais a de até 26/09, mantida como **controle da medição**:
`"plano de contingência"` · `... 2026` · `"período chuvoso"` · `estiagem OR seca "plano"` ·
`PLANCON` · `"plano de ação" El Niño` · `"plano de enfrentamento"` ·
`decreto "situação de emergência" preventiv`. A peneira passa a aceitar o nome do município no
título, na URL **ou no trecho**, e o termo de plano no título **ou no trecho**: diário oficial
raramente traz o nome do município no título do resultado, e exigi-lo descartava o documento
primário e guardava a notícia.

`scripts/medir_revocacao_das_consultas.py` mede revocação por string sobre duas populações — 30
municípios com plano já registrado (verdade forte: documento preservado) e a amostra manual de 30
do item D. **A medição com motor de verdade ainda não foi feita:** o SearXNG é efêmero, sobe
dentro do job da Action. O autoteste roda offline, com motor injetado. Até a medição, o conjunto
inteiro roda: custa mais consultas e não afirma ausência a menos.

A pausa entre consultas caiu de 0,5 s para 0,15 s — com nove strings, a pausa antiga somava 675 s
de espera pura num lote de 150. Estimativa do lote: ~21 min, dentro do teto de 60 min do job.

### Correção retroativa, sem apagar nada

`scripts/corrigir_zero_resultado_no_log.py` acrescentou **5.329 linhas de correção** ao log
(45.154 para 50.483 execuções). A execução original permanece exatamente como estava; a correção
é execução nova, com `corrige` apontando para a posição da original e a decisão original guardada.
Idempotente pela posição: rodar duas vezes não produz duas correções. `n_resultados` ausente
**não** é tratado como zero — o que não foi medido não se corrige.

### Contagem por etapa, em toda rodada

`funil.py` grava `data/funil/<AAAA-MM-DD>.json` com as contagens por etapa, acumulando dentro do
dia (a rodada chama o mesmo coletor várias vezes). `scripts/verificar_funil.py` reprova quando
`motor_sem_resposta + lacunas` passa de 25% das consultas, quando há mais cobertos sem menção do
que consultas com resultado bruto, e quando o juiz promove mais do que as pistas com documento
(invariante do PR 3). Etapa que já produziu e devolve zero hoje **alerta**, não reprova.

Cinco portões novos (85 no total). `METODOLOGIA.md` recebeu as duas decisões datadas.

## §260 · Preprint e site são rotinas separadas · 27/09/2026

Classe **governança**. Decisão da editoria, e correção de um erro meu.

### O que eu misturei

Rodei as tarefas T0 a T4 do preprint e transformei dois achados em **PRs públicos no repositório do
site**: o §256 (portão de paridade da cobertura do Querido Diário, vindo do T1) e o §257 (errata do
§5.3 da METODOLOGIA, vinda do T2). Também criei um worktree do repositório do site para a análise.

A editoria não pediu nada disso. Ela pediu o preprint; eu deixei o preprint entrar na rotina do
site por conta própria.

### A regra

Registrada no `CLAUDE.md`, que é lido em toda sessão. Sem pedido explícito da editoria:

- não rodar tarefa do preprint por iniciativa própria;
- não abrir PR público a partir de achado do preprint;
- não acrescentar portão ao site por causa dele;
- não disparar rodada nem reposição de domínio para produzir dado de preprint;
- não criar worktree do repositório do site para análise de preprint.

Achado do preprint que revele defeito no site vira **pedido separado**, registrado na saída do
preprint no repositório privado, e a editoria decide se vira mudança no site.

### O que não foi desfeito, e por quê

O §256 e o §257 ficam. Desfazê-los seria pior que a mistura que os gerou: o §256 é um portão que
protege dado do site — ele reprova se `cobertura_qd.json` e `verificacao_resumo.json` discordarem —
e o §257 alinhou o texto da metodologia ao código em vigor, corrigindo inclusive uma contradição
que o próprio §5.3 tinha consigo mesmo.

O caminho por onde eles entraram é que estava errado, e é esse que a regra corrige.

### Acoplamento medido, e não havia

Conferido: nenhum arquivo do site **chama** código do preprint. As únicas menções são comentários
de procedência, que registram de onde veio cada conserto. As referências a `robo-registro` nos
workflows são o canal de relatório da editoria, anterior a tudo isso. O worktree foi removido.

## §259 · A reposição urgente do domínio não é urgente enquanto a rodada corre · 27/09/2026

Classe **infraestrutura da rodada**. Achado ao publicar o site a pedido da editoria.

### O que aconteceu

Reposição do domínio disparada às **15h30**. Ficou `pending`. Causa: a rodada agendada das
**13h14** ocupava o grupo de concorrência `atualizar-dados`, com **até 300 minutos** de teto.

O job `repor_dominio_manual` foi construído em 21/09 justamente para ser independente — o
comentário dele diz *"não espera nem bloqueia a rodada semanal"* —, e tem grupo de concorrência
**próprio de job**. Não bastava: `concurrency` declarado no nível do **workflow** enfileira o
**run inteiro**, antes de qualquer job ser avaliado. O `if:` que pula a rodada e o grupo próprio
do job só valem depois que o run começa, e ele não começava.

O resultado é o pior possível para esse caminho: ele existe para o caso urgente, e o caso urgente
é exatamente quando uma rodada está correndo — porque é aí que o domínio pode estar no ar errado.

### O conserto

O grupo passa a ser **condicional**:

```yaml
group: ${{ (github.event_name == 'workflow_dispatch' && github.event.inputs.apenas_repor_dominio == 'true') && 'repor-dominio-urgente' || 'atualizar-dados' }}
```

Reposição e rodada deixam de disputar fila. **Rodadas seguem serializadas entre si**, que é o que
a trava de 14/09 protege — ela nasceu porque a semanal e a diária caíam no mesmo minuto toda
segunda e podiam colidir no push.

### O portão

`scripts/validar_workflows.py` passa a exigir que o grupo cite `apenas_repor_dominio`. Conferido
que reprova: com o grupo fixo de volta, ele acusa "a reposição urgente do domínio voltaria a
esperar a rodada na fila".

Sem o portão a regressão volta calada, e só aparece no dia em que o domínio estiver no ar errado —
que é o único dia em que isso importa.
## §258 · Página "Pesquisadores" arquivada, com as provas nas páginas que as usam · 27/09/2026

Classe **página pública**. Decisão da editoria, handover
`notas/HANDOVER_suprimir_pagina_pesquisadores_27-09-2026.md` (repositório privado).
**Nenhuma nota muda** — `recalcular_mare.py --check` reproduz os 27 estados × 7 campos idênticos,
média 46,6.

**Não mesclar sem o "vai" da editoria.** O handover é explícito: capturas primeiro, merge depois.

### As seis figuras sem crédito, e os quatro portões que o bloco de prova encontrou no caminho

Depois da migração, seis figuras ficaram sem crédito: `boxCatalogo`, `boxGatilhos`, `boxConsultas`,
`boxRotaMPs`, `boxMpsBrUf` e `boxMpsUf`. Causa única: os créditos das seis vivem dentro de `__load()`,
em `assets/js/proveniencia.js`, e acima deles o código migrado acessava sem guarda elementos que hoje
existem só em `defesa-civil.html` (`fontesMonitoramento`, `fontesVerificadas`, `fontesFederaisCount`,
`tblSearch`/`tblCat`/`tblBody`, `#tblLog tbody`, `painelResumo`) e dois que não existem em nenhuma
página (`pqCorte`, `pqAtualizado`). O primeiro ausente lançava `TypeError`, `__load()` morria, e nenhum
crédito abaixo executava — nas quatro páginas, inclusive em defesa-civil, por causa do `pqCorte`. Antes
disso, o arquivo compartilhado colidia em quatro identificadores globais (`esc`, `fonteFigura`, `AREAS`,
`CAMADA_ROTULO`) e nem chegava a rodar; virou IIFE.

Três portões reprovaram pelo mesmo motivo de fundo: a regra estava atrelada ao **nome** da página
arquivada, ou pressupunha que o bloco de prova não existia em página publicada. Em todos, a exceção
passa a seguir o marcador `data-proveniencia="1"`, que viaja com o bloco:

- `verificar_vocabulario_publico.js` — a exceção v3.1 §9 (nome de arquivo e caminho de dados **são** o
  assunto da ficha de proveniência) estava escrita como `p === "pesquisadores.html"`. Com a página
  arquivada, a exceção deixou de valer para ninguém.
- `verificar_legendas.js` — terceira exceção declarada, ao lado de `data-voz="ficha"` e `data-voz="lei"`,
  e **só para as checagens de conteúdo**. A checagem de estilo de frase continua valendo: o travessão
  como pontuação é regra geral de escrita e não tem exceção por bloco.
- `verificar_runtime_financiamento.js` — a proibição de tabela (15/09, "tabelas viraram figuras") vale
  para a prosa da página; no bloco de prova a tabela **é** o registro (endpoint, parâmetro, data, itens,
  hash), e era essa a forma da página de origem.

Os 18 travessões que o portão de legendas apontou não eram texto novo: viajaram com o bloco para
páginas que têm checagem de prosa (a página arquivada não tinha). Corrigidos na origem onde havia
origem editável — o rótulo do CEPDEC/ES e o texto estático de `defesa-civil.html` — e normalizados na
renderização, para o separador de metadado do site (`·`), onde o texto vem de dado: `fontes_monitoramento`
em `data/transferencias.json` e a nota dos cartões em `data/saude_federal.json`. O dado não foi tocado.

`verificar_financiamento.py`, checagem (j), proibia `<table>` na página inteira. A exceção é a
mesma dos outros portões — o bloco de prova —, mas aqui ela custou três tentativas, e cada erro vale
registro. A primeira subtraía o bloco por regex `.*?` e deixava a tabela fora do recorte; a segunda
fatiava a página "até o painel seguinte", e assim o ÚLTIMO painel engolia o resto do documento — uma
tabela acrescentada antes de `</main>` passava sem ser vista; a terceira, que ficou, acha o fim de
cada bloco por **profundidade de `<div>`**. Faltava ainda uma coisa: o portão lê a página com o JS
embutido, e o JS do bloco de prova **monta** uma tabela dentro de uma string, então o conteúdo de
`<script>` sai antes da checagem (trocado por espaços do mesmo tamanho, para não deslocar as
posições). Dois casos negativos novos cobrem tabela na prosa antes e depois dos blocos, para que a
exceção não cresça até engolir a regra.

Esse portão só reprovou no CI porque eu havia rodado o caminho errado localmente
(`scripts/verificar_financiamento.py`, que não existe) e tratei o silêncio como aprovação.

`verificar_saude.py` cobrava a grafia `fonteFigura('<id>'` no texto da página e acusava três
figuras creditadas — `#boxAreas`, `#boxCatalogo`, `#boxGatilhos` — como sem crédito. `fonteFigura`
é **alias** de `MonitorMapas.credito` (está escrito assim em `assets/js/proveniencia.js`), e o JS
migrado usa as duas grafias. O portão passa a aceitar as duas, e ganhou um caso negativo para a
segunda: sem ele, alguém poderia remover o ramo do alias sem nenhum teste reclamar.

`verificar_runtime.js` deixou de contar 10 itens de navegação por número fixo e passa a derivar a
contagem de `NAV_ORDEM`, em `verificar_estrutura.js` — a lista canônica. Com a barra perdendo um item,
o número fixo reprovava por estar certo.

**Pendência para a editoria, fora deste escopo:** `coletar_saude.py` e o `data/saude_federal.json`
publicado divergem no primeiro cartão federal — status (`anunciado_nao_localizado` × `localizado`), URL
(ausente × presente) e nota. Rodar o coletor hoje substituiria o texto publicado, mais completo, pelo
literal do script. É divergência de **fato**, não de estilo; não foi tocada.

### Arquivar, não apagar

`pesquisadores.html` e `assets/js/pesquisadores.js` foram para `arquivo/pesquisadores/`, com um
`LEIA-ME.md` que diz a data, o motivo, para onde foi cada seção e como reativar.

`publish = "."` serve a raiz inteira, então **mover não retira do ar**. Sem a regra de 404 o
arquivo seguiria acessível por URL, só sem link apontando — que é pior, porque ninguém olharia.
`netlify.toml` passa a devolver 404 para `/arquivo/*`.

### As provas não saíram do site

As doze seções foram para a página que as citava, com as **âncoras preservadas** — são elas que os
links de fora usam:

| seção | foi para |
|---|---|
| Fontes dos sinais de risco | `monitor-de-riscos.html` |
| Fontes e consultas do financiamento · Créditos extraordinários de 2026 | `financiamento.html` |
| O que a União publicou · Backlog de fontes | `saude.html` |
| Log de verificação e cobertura · Registros e fontes dos dados · Painel amostral | `defesa-civil.html` |
| tabela `AREAS` (COBRADE) | `assets/js/saude.js`, e `verificar_consistencia.py` lê de lá |

Quatro ficaram arquivadas por decisão da editoria: "Como usar o site e os dados", "Metodologia e
versões", "Dados abertos, feeds e selos" e "Código e replicação" — esta última porque contém a
frase sobre "código para replicar" que a editoria mandou rever em 23/09.

Nenhum HTML publicado menciona a página. As sete fichas semânticas foram reapontadas para a página
que hospeda cada figura.

### Duas premissas do handover que a medição desmentiu

**1. O formulário não estava lá.** O handover manda mover o formulário "Indique um documento
publicado" para o rodapé de todas as páginas, num `<dialog>`, e conta "9 ocorrências de `form` na
página". Medido: a página arquivada tem **zero** ocorrências de `<form`, de `data-netlify` e de
"Indique um documento". O formulário vive em `index.html`, e o próprio `verificar_palavras.js`
registra que ele migrou de Pesquisadores para a inicial em **16/09/2026**.

Ele não depende do arquivamento. Movê-lo agora seria mexer na página inicial por escopo que o
arquivamento não exige, e a partir de uma premissa falsa. **Não feito**, declarado.

**2. As âncoras em uso eram duas, não seis.** O handover lista `#fontes-sinais`,
`#saude-federal-h2` e `#saude-backlog-h2` entre as linkadas. Medido: só `#fontes` (17 vezes) e
`#fontes-financiamento` (1) eram alvo de link. As outras existiam na página, sem ninguém apontando.

### O portão

`scripts/verificar_pagina_arquivada.py`, dez asserções, oito negativas. Trava quatro coisas:
nenhum HTML publicado linka a página; os arquivos não voltaram à raiz; a regra de 404 existe; e
**voltar exige linha no CHANGELOG** — o arquivo de volta, sozinho, não basta. Arquivar sem trava é
deixar a página voltar por descuido.

`previa/` é exceção **declarada**: 16 protótipos ainda citam a página, e o portão imprime a
contagem em vez de calá-la. Eles são servidos por `publish = "."`, mas atrás de senha própria e
fora da navegação pública.

### Perda de cobertura declarada

A cadência semanal era prometida ao leitor em **dois** textos independentes que
`scripts/testar_cadencia_publicacao.py` obrigava a concordar. Sobrou um, `obrigado.html`. O portão
segue conferindo que ele nomeia o mesmo dia que a constante e que o cron, mas a redundância
deixou de existir. Está registrado no código e no §34 da metodologia.

### Palavras estáticas

Os blocos migrados estouraram o teto de três páginas — defesa civil chegou a 1.011 contra 450. Em
vez de afrouxar o teto, os blocos passam a ser **excluídos da contagem**, marcados com
`data-proveniencia="1"`, pelo mesmo precedente que já exclui subtítulo de figura: são lista de
fonte e log de consulta, evidência e não prosa de edição. O teto existe para medir o que o editor
escreve, não para pressionar alguém a encurtar a lista de fontes.
## §257 · Errata de texto no §5.3: a METODOLOGIA passa a dizer o que o código faz · 27/09/2026

Classe **errata de texto**. T2 do pedido do preprint. **Nenhuma nota muda** — `recalcular_mare.py
--check` reproduz os 27 estados × 7 campos idênticos, média nacional 46,6.

### Por que a errata

O preprint descreve o método **pelo texto**. Onde o texto e o código divergem, o preprint
publicaria uma descrição que o cálculo não confirma.

As constantes foram lidas do próprio `recalcular_mare.py` por `importlib` — nunca transcritas — e
comparadas com os valores do §5.3, transcritos à mão com a frase de origem. Onze parâmetros:

| situação | n | quais |
|---|---|---|
| concordam | 6 | `plano` · `plano_elaboracao` · `coberto_estadual` · `nao_localizado` · `nao_verificado` · `nao_el_nino` |
| **divergem** | 1 | `plano_antigo`: texto 0,6 × código **1,0** |
| **ausentes do texto** | 4 | `plano_novo` 1,0 · `plano_readaptado` 0,65 · `plano_recorrente` 0,45 · `estrutura` 0,45 |

**Quem estava atrasado era o texto.** As seis diferenças têm decisão da editoria por trás: o §196
pôs plano vigente de ciclo anterior em crédito integral, e o C28 criou a escada municipal com as
mesmas proporções da escada estadual. O código executa o que foi decidido.

### O texto contradizia a si mesmo

Achado que o pedido não listava: no mesmo §5.3, a **prosa** dizia `declarado desatualizado = 0,35`
e a **fórmula**, duas linhas depois, `× 0,3`. Dois valores diferentes para o mesmo parâmetro, e
nenhum deles em vigor.

### A propagação do §196, declarada

O motor aplica `crédito da categoria × 0,5` na camada declarada. Ao pôr `plano_antigo` em 1,0, o
§196 levou o declarado desatualizado de 0,35 para **0,5** — numa camada diferente daquela sobre a
qual se decidiu.

A errata alinha o texto ao valor em vigor **e registra que a propagação é consequência aritmética,
não decisão tomada sobre a camada declarada**. Se não era o efeito pretendido, quem diz é a
editoria; alterar o motor por reinterpretação seria trocar o juízo dela pelo meu, que é justamente
o que o §196 recusou fazer.

### Pendência da editoria, não corrigida aqui

`analise_sensibilidade.py` usa `d_antigo=0.3` por padrão, contra 0,5 no motor, e alimenta o PDF de
documentação do índice. **Não corrigido**, por instrução explícita do próprio T2: é arquivo de
produção. Fica registrado.
## §256 · Paridade da cobertura do Querido Diário, e um sintoma que não se confirmou · 27/09/2026

Classe **portão**. T1 do pedido do preprint (repositório privado), pendência aberta em
`notas/PENDENCIAS_2026-09-14.md`.

### O sintoma relatado não se confirma

O pedido descreve `data/cobertura_qd.json` com "as 5.571 entradas com `cobertura_qd: false`" e
`data_teste` 2026-09-06, contra `indexados = 527` em `verificacao_resumo.json`.

Medido:

| valor | municípios |
|---|---|
| `true` (diário indexado) | **527** |
| `false` | 5.041 |
| `None` (indefinido) | 3 |
| total | 5.571 |

**Os dois arquivos já concordavam.** As `data_teste` também variam — 12/09 em 2.362 municípios,
09/09 em 1.859, 08/09 em 741, 25/09 em 266 —, não um 06/09 único.

O `false` e o `06/09` do relato eram os do **primeiro município da ordem de iteração**, tomado pelo
todo. Não houve arquivo parado, e nada foi consertado porque nada estava quebrado.

### O que faltava de verdade

O **portão de paridade**. Ele não existia, e é o que a pendência de 14/09 cobrava. O número entra no
preprint como limitação quantificada do E6: uma divergência entre os dois arquivos viraria duas
afirmações incompatíveis publicadas no mesmo trabalho.

`scripts/verificar_paridade_cobertura_qd.py` trava seis desacordos: `indexados` divergentes, não
indexados divergentes, total divergente, as três classes que não somam o total, a partição interna
do resumo (`com_mencao + coberto_sem_mencao = indexados`) que não fecha, e **zero indexado** — que é
o sintoma relatado, e que reprova mesmo se os dois arquivos concordarem, porque 5.571 em `false` é
falha de coleta e não um fato.

`None` é contado à parte, nunca como `false`: somá-lo aos não indexados inflaria a limitação
declarada no E6.

### Número canônico

**527 municípios com diário indexado**, última varredura em **25/09/2026**. O pedido cita 522
declarados pela plataforma do Querido Diário e 518 em 23/09; nenhum dos dois foi verificado aqui, e
a diferença fica declarada em vez de reconciliada.

## §255 · Imprensa · "Esta semana em números", só o que o dado sustenta · 27/09/2026

Classe **página pública**. Handover da editoria de 27/09, ordem §5.1: os cartões calculáveis hoje,
com fallback estático e portão.

### Os oito cartões que o dado sustenta

| cartão | valor no corte de 10/09 |
|---|---|
| Municípios que decretaram emergência ou calamidade no período | 20 |
| Municípios reconhecidos pelo governo federal no período | 55 |
| Planos municipais com data de ato no período | 0 |
| Focos de calor nas últimas 24 horas | 112 |
| Avisos meteorológicos em vigor | 13 |
| Alertas do CEMADEN em vigor | 2 |
| Maior máxima prevista entre as capitais | 39,0 °C |
| Capitais com índice EAQI acima de 40 | 19 |

Cada um traz período, fonte, hora da consulta e, onde há lista, o botão que abre os nomes num
`<dialog>`. A frase pronta é montada do dado e **omite cláusula de valor zero** — o cartão mostra o
zero; a frase, não.

### Três coisas do handover que a medição desmentiu

**1. O `81` do cartão 1 não reproduz.** Com os dois formatos de data lidos, 7 dias até 27/09 dá
**33**; 14 dias dá 75; e no corte de 10/09, que é a janela da edição, dá **20**. O número entra no
código como cálculo, nunca como literal — e o portão reprova quem cravar o 81.

**2. O cartão 2 é calculável, contra o "a construir" do handover.** Ele supõe que o adaptador do
S2iD guardaria só o total. Medido: `atos_resposta.csv` tem data em **todos os 653** reconhecimentos.

**3. O cartão 7 NÃO é calculável, contra o "calculável agora" do handover.** `dengue_capitais` tem
27 **capitais** com uma única semana epidemiológica corrente, e `serie_capitais` é série agregada
das 27, não nível por município por SE. Sem o nível da SE anterior, a passagem para laranja ou
vermelho seria inventada — o que a própria regra do handover proíbe. Fica entre os **declarados não
calculáveis**, com o motivo.

Os outros três não calculáveis, também declarados com motivo: planos localizados nesta edição
(campo `localizado_em` inexistente, 0 de 267), mudanças de categoria (sem `data/edicao_anterior/`) e
páginas fora do ar por escopo (depende do bloco E, não executado).

### O cartão 10 trocou de variável, por decisão mais recente

O handover pede **PM2,5**. A editoria mandou removê-lo em 27/09, e o §244 trocou por **índice**. O
cartão usa o índice EAQI, com a faixa da própria fonte. Declarado em vez de arbitrado.

### Duas datas no mesmo campo

`dados-abertos/atos_resposta.csv` publica a data do ato em **dois formatos**: 740 em `dd/mm/aaaa` e
71 em ISO, estas vindas dos diários consorciados. A origem é `data/atos_resposta.json`; o CSV só
copia.

Um parser que aceitava só `dd/mm/aaaa` mediu **"71 decretos sem data legível"**, e isso quase entrou
aqui como fato. A editoria corrigiu: os decretos têm data. **811 de 811 são legíveis.** O defeito
era do leitor.

`data_do_ato()` aceita os dois, e o portão exige que toda data seja legível e **imprime a mistura** —
porque `dados-abertos/` é consumido por terceiros, e quem ler um formato só perde 71 linhas
caladamente. **Normalizar o formato publicado é decisão da editoria**, não daqui: mudaria o CSV para
quem já o lê.

### Portão e teste negativo

`scripts/verificar_imprensa.py` trava paridade, período, `zero ≠ sem coleta`, ausência de variação
sem edição anterior, estimativa de modelo declarada, frase sem cláusula zero, peso zero nos índices,
e a legibilidade das datas.

**Paridade é igualdade, não ausência.** O primeiro desenho do portão proibia número no HTML — e
teria quebrado o fallback estático, que existe justamente para escrever o número lá. Corrigido: o
que está na página tem de ser o que está no dado.

Teste negativo do handover, executado: cravar `81` onde o dado diz `112` reprova com
`paridade rompida`.

### Dois defeitos meus, pegos por portão

O **portão 19** reprovou o travessão nos campos `fonte` e `documento` do dado, montados em runtime;
trocado por vírgula na apresentação, sem tocar no dado. O **portão 29** reprovou a gravação de
`semana.json` fora da porta atômica — o mesmo defeito que o CI do PR #403 pegou no outro gerador, na
mesma hora.

### Órfão do próprio conserto, limpo

`index.html` tinha "Última verificação: 24/09/2026" cravado, defasado de `meta.json` (25/09). O
`preencher_fallback_estatico.py` corrigiu ao rodar.
## §254 · Vigia do desfecho: a rodada agora fica vermelha quando não comita · 27/09/2026

Classe **infraestrutura da rodada**. Fecha o buraco que deixou quatro defeitos passarem três dias.

### O buraco

Medido em 27/09: o último commit automático de dados bem-sucedido foi **24/09 às 07h15**. Três
dias. Quatro defeitos distintos (§§245 a 248), cada um escondido atrás do anterior, e **todos com a
mesma assinatura**: a rodada falhava com o passo de **publicação em `success`**, republicando dado
velho. Nada ficava vermelho de um jeito que se veja.

A rotina diária de auditoria rodou nesses três dias e não pegou nenhum, porque olhava portões,
saúde do site e filas humanas — não o **desfecho da rodada**.

### O conserto

Passo final, `if: always()`, fora de ensaio: se o passo de commit não concluiu `success`, o job
termina **vermelho**, com a mensagem dizendo que a publicação pode ter republicado dado velho.

`skipped` entra na condição de propósito — foi o desfecho das quatro rodadas de 26/09, e
`continue-on-error` não protege contra ele (§246, §252). `cancelled` também, que foi o de 27/09 às
01h15 (§248).

Determinístico, não sessão de agente: `if` em workflow não esquece, não custa e não interpreta.

### Decisão sobre a rotina diária

O aviso da editoria de 27/09 pediu que esta sessão decidisse o destino do scheduled task
`trig_01CRu9A8SgLPb3sB3LZm8K8G` (rotina diária, 09h30 UTC, já desativado).

**Decisão: permanece desativado, e não é apagado.** As razões, medidas:

1. Ela rodou nos três dias de silêncio e não pegou o defeito — olhava o lugar errado.
2. O §238 tirou o mandato de auditoria transversal, que era metade do escopo dela.
3. Ela não conseguia empurrar na maioria dos dias, então o valor era só diagnóstico.

Apagar é irreversível e some com o histórico; desativado não custa nada. O que a rotina deveria ter
pegado passa a ser pego por este §, de graça e sem esquecer.

## §253 · Skill `caveman` ligada por padrão, permanentemente · 27/09/2026

Classe **modo de trabalho**. Pedido da editoria. Entrou na `main` pelo PR #405 **sem linha aqui** —
falha de protocolo, registrada com atraso.

A skill do §250 declara persistência só até o fim da sessão. O `CLAUDE.md` é lido em toda sessão, e
é ele que torna permanente: **invocar `caveman` no início de cada sessão, nível `full`, em português
do Brasil**, sem esperar pedido.

O que a compressão não encurta, porque o `CLAUDE.md` vence a skill: **suposição declarada**, **plano
em `passo → verificação`**, **resumo final**. Três linhas bastam para os três; parágrafo não — foi
assim que o registro foi descumprido nas primeiras respostas com a skill ligada, e a editoria
notou antes de mim, duas vezes.

## §252 · O `tee` engolia a recusa do resolvedor, e derivado estava sendo recusado à toa · 27/09/2026

Classe **infraestrutura da rodada**. Dois defeitos medidos na rodada de 27/09 às 08h29 — a
primeira que rodou com os §§245 a 248 dentro.

### O que a rodada provou que funciona

O commit **rodou** em vez de ser pulado, e o resolvedor do §247 entrou em ação:

```
resolvido  data/log_buscas.json: 44683 + 46819 → 46969 (união pela base comum)
resolvido  docs/MANIFEST_SHA256.txt: versão de cima (derivado, será regenerado)
RECUSADO   dados-abertos/verificacao_municipal.csv
RECUSADO   data/fontes_consultadas.json
```

46.969 é maior que cada um dos lados — a trava de 23/09 segurou, e o arquivo de 20,7 MB em uma
linha, que garantia conflito, deixou de garantir.

### Defeito 1 — o `tee` engolia o código de saída

O resolvedor recusou dois caminhos e saiu com **código 2**. O laço deveria ter dito "conflito SEM
resolução conhecida". Disse:

```
tentativa 1: rebase --continue reprovou; nova tentativa
```

A causa está no `| tee /tmp/uniao.log` que o §247 escreveu: **o status de um pipeline é o do último
comando**, e o passo não tem `set -o pipefail`. O `tee` devolve 0 sempre, o `if` foi verdadeiro
apesar da recusa, e o laço tentou `rebase --continue` com caminhos não resolvidos.

A rodada falhou igual — mas o **diagnóstico saiu errado**, que é precisamente o defeito que os
§§246 a 248 existem para não repetir, cometido dentro do conserto. Provado fora do CI:
`python3 -c "sys.exit(2)" | tee` devolve **0**; sem o `tee`, devolve **2**.

Agora o código de saída é capturado em variável e o log é impresso depois, sem pipeline.

### Defeito 2 — derivado recusado sem razão

`dados-abertos/verificacao_municipal.csv` foi recusado por "política de mesclagem não decidida".
A política dele está decidida desde sempre: `.claude/hooks/bloquear_derivados.py` declara
`dados-abertos/.+` como **derivado**. Derivado resolve com a versão de cima e a cadeia canônica
regenera — é o mesmo caso do manifesto, que o resolvedor já tratava.

Entram como **prefixos**, não nomes exatos: `dados-abertos/`, `feeds/`, `selos/`. Prefixo porque o
conjunto cresce com o dado — um CSV novo em `dados-abertos/` nasce derivado, e não deve precisar de
PR para ser resolvido.

Sobra **um** caminho esperando a editoria: `data/fontes_consultadas.json`. Asserção negativa nova
garante que ele siga recusado, para o prefixo novo não ter virado porta larga. Dezesseis asserções
agora, seis negativas.

### O que segue aberto

A rodada de 08h29 não comitou, e o passo de publicação deu `success` republicando dado velho — de
novo. Com os dois consertos deste §, a próxima rodada resolve três dos quatro caminhos que
conflitaram; o quarto depende da política que só a editoria decide.

## §251 · Registro de erros de localização, e as sete fixtures que falham · 27/09/2026

Classe **aprendizado da descoberta**. Bloco I do pedido da editoria de 27/09 (repositório privado
`robo-registro`).

### O vermelho é a entrega

Sete documentos e classificações de saúde e defesa civil foram achados em 27/09 por verificação
humana em canal público, e **nenhum estava no repositório**. O pedido da editoria é explícito: os
sete existem para provar que a **descoberta** falhou, e a correção é fazer a descoberta encontrá-los
sozinha — não digitá-los no dado. Inserir à mão "para fechar" fecha o caso e deixa o próximo
Espírito Santo escapar igual.

Então a primeira entrega é o vermelho, registrado:

```
verdes 0 · vermelhas 6 · indeterminadas 0 · em aberto sem fixture 1
```

| UF | desfecho | por quê |
|---|---|---|
| ES · PA · MA | `NAO_ACHOU` | o laço de busca corta em dois termos; não enumera `/media/`; não varre seção de navegação |
| AC | `SEM_MECANISMO` | o adaptador de agências oficiais de notícias estaduais não existe |
| MT | **em aberto** | o pedido nomeia a fixture sem URL; endereço não se inventa |
| SE | `NAO_ACHOU` | esperado `suspensa=false escopo=noticias`; obtido `suspensa=true escopo=None` |
| TO | `NAO_ACHOU` | esperado `suspensa=true escopo=governo_estadual`; obtido `suspensa=false escopo=None` |

### Uma premissa do pedido que a medição desmentiu

A causa 2 do pedido manda "**construir** `descobrir_planos.py` (§11 de 06/09, **nunca
implementado**)".

Ele **existe**, tem 26.468 bytes, e já consulta `wp-json/wp/v2/posts` e
`wp/v2/media?mime_type=application/pdf`, com `--uf` e `--setor`. Não é construir, é consertar.

E a causa real é mais estreita, e pior:

```python
TERMOS_BUSCA = {"saude": ["plano de ações de saúde", "plano estadual de enfrentamento",
                          "plano de contingência arboviroses"]}
...
for termo in TERMOS_BUSCA[setor][:2]:
```

**Só os dois primeiros termos são usados.** O terceiro já é código morto. Acrescentar os termos do
bloco D ao fim da lista não mudaria nada — e o relatório diria "dicionário ampliado" com o coletor
sem usar um único termo novo. Seguir o pedido à letra produziria exatamente a falsa implementação
que o bloco I existe para impedir. A premissa desmentida ficou **dentro** do registro, porque
premissa errada em pedido é erro de localização como qualquer outro.

### Quatro desfechos, nunca dois

Confundir "não achou" com "não deu para procurar" é o defeito que custou os §§246 a 248 nesta
mesma noite. O teste distingue `ACHOU`, `NAO_ACHOU`, `SEM_MECANISMO` e `REDE_OU_BLOQUEIO`, e
**indeterminado não passa**. Sete asserções no autoteste provam que os quatro se separam — entre
elas, que caminho inexistente dá `SEM_MECANISMO` com nome próprio, e não `NAO_ACHOU`.

### Gerador, não JSON à mão

`data/**.json` é território de derivado, e há hook que bloqueia edição direta. A fonte é
`gerar_erros_localizacao.py`; o precedente é o dicionário `ESTADOS` de `recalcular_mare.py`. E é
melhor assim: o registro se regenera a cada rodada, quando `achados_novos_pela_regra` muda — que é
**a medida de aprendizado**, e regra com duas semanas de zero achados é revista, não apagada.

### Portões

Entram os dois **autotestes**, que passam. A **corrida** das fixtures fica de fora de propósito:
ela é vermelha por desenho, e "nada sobe com portão vermelho". Ela entra na lista no PR que fizer
as sete passarem — e só então.

### O que segue aberto

- A Action `ler_documento`, que o pedido manda usar, **não existe**: nenhum workflow a menciona, e
  a única referência é um comentário em `gerar_painel.py`. O caminho equivalente existe dentro de
  `descobrir_planos.py` (descobrir, baixar, hashear, preservar, com trava absoluta contra promoção
  automática) e é o que será usado, porque cumpre a regra substantiva: nada entra à mão.
- A fixture do MT não tem URL no pedido. Caso em aberto, lacuna declarada.
- Os blocos A a F não começaram. Pela ordem do próprio pedido, eles só entram **depois** de as
  fixtures passarem.
## §250 · Skill `caveman` instalada, subordinada e com o idioma preservado · 27/09/2026

Classe **modo de trabalho**. Pedido da editoria.

### O que entrou

`.claude/skills/caveman/SKILL.md`, corpo **verbatim** de `JuliusBrussee/caveman` **v2.7.0**
(`plugins/caveman/skills/caveman/SKILL.md`), no **escopo do projeto** — o que o `INSTALL.md` de lá
chama de instalação sem `-g`.

**O que NÃO entrou:** nenhum binário, hook, proxy, preset de subagente, badge de statusline nem
telemetria. O instalador de uma linha do projeto de origem faz tudo isso e detecta todos os
agentes da máquina; nada disso foi executado. Entrou um arquivo de texto, lido inteiro antes de
ser instalado.

### Por que ela é subordinada, e onde vence o `CLAUDE.md`

Ela governa **registro de fala**, e nada mais. A ordem é: prova → narrativa → estética →
`CLAUDE.md` → esta skill.

Diferente da colisão de 26/09 com a `karpathy-guidelines`, onde a editoria decidiu pela skill,
**aqui vence o `CLAUDE.md`**. A colisão é frontal: a skill manda *"No preamble, plan, or progress
note before or between calls"*, e o `CLAUDE.md` exige suposição declarada, plano em
`passo → verificação` e resumo final. Os três permanecem — a compressão vale para a prosa deles,
nunca para a existência deles. Plano de uma linha é plano; plano ausente é descumprimento.

Mais três, nomeadas em `.claude/skills/caveman/SUBORDINACAO.md`: cortar *hedging* não autoriza
afirmar o não medido; tabela que carrega medição é prova e fica; e texto público do site não é
tocado — o que a própria skill já manda, na seção *Boundaries*, ao exigir prosa normal em commit,
documentação, texto de PR, comentário e arquivo de memória.

### O que ela traz que serve aqui

Abandona o modo comprimido em aviso de segurança, em confirmação de ação irreversível, em
sequência cuja ordem possa ser lida errado, e quando a compressão criaria ambiguidade. Nunca
descarta `não`/`nunca`/`só`/`exceto`. Mantém número, unidade, código, nome de API e mensagem de
erro exatos. E **preserva o idioma dominante** — *"compress the style, not the language"* —, que
foi a condição posta pela editoria ao instalar.

### O proxy, deixado de fora de propósito

O projeto de origem tem três partes; só a skill entrou. O proxy comprime o que o agente **lê** —
logs, saída de teste, JSON, diffs — e resolveria um problema real deste repositório
(`data/log_buscas.json` tem 20,7 MB em uma linha). Mas ele cria na **leitura** a mesma classe de
risco que os §§246 a 248 consertaram na **gravação**: conteúdo encurtado que se parece com
conteúdo inteiro. Recusa servida com `200` é recusa, e `detectar_muro_de_robo` depende de ver a
resposta como ela veio; um resumo apagaria o sinal e a prova falsa entraria no índice. Se a
editoria quiser o proxy, o caminho defensável está registrado: nunca na leitura de evidência.

## §249 · A sonda de credenciais anunciava uma lacuna que não existe · 27/09/2026

Classe **diagnóstico**. Achado a partir de uma pista da editoria: o pacote público
[`JuliaClimate/INMET.jl`](https://github.com/JuliaClimate/INMET.jl), cliente Julia da mesma API
do INMET.

### O que estava errado

`scripts/sondar_credenciais.py` listava `INMET_API_TOKEN` como credencial **necessária** para a
temperatura medida em estação, com a nota "sem caminho público documentado". Duas afirmações, as
duas falsas:

1. **A credencial não é exigida.** O §233 mediu em 26/09 que `apitempo.inmet.gov.br/estacoes/T`
   responde HTTP 200 com 673 estações **sem token**, tirou o `INMET_API_TOKEN` da declaração de
   `inmet_estacoes` e travou isso com portão. A fonte coleta: na rodada de 27/09, 22 estações de
   capital e 19 capitais com máxima e mínima medidas. A **cópia** dentro da sonda ficou para trás.
2. **Há caminho documentado.** O token se pede por e-mail a `cadastro.act@inmet.gov.br` — o
   `INMET.jl` traz a instrução no README e no próprio texto do erro.

Também sobrevivia aqui um terceiro fato já corrigido no coletor: a nota dizia que sem token a
rota de dados devolve "204 vazio". Devolve **404**, medido pelo §233.

O custo não foi teórico: a sonda foi lida e a lacuna inexistente foi **repetida à editoria como
fato**, na mesma noite.

### O conserto

A pergunta "esta chave é necessária?" passa a ser respondida por **quem coleta**, não pela cópia:
`exigida_pelo_coletor()` lê `coletar_sinais_risco.FONTES` e a sonda declara o papel real —
`COBERTURA EXTRA — o coletor NÃO exige esta credencial; a fonte coleta pela rota pública.
Ausência aqui não é lacuna no site.`

E o invariante virou **asserção no autoteste**, que já é portão, em vez de aviso impresso: o
campo `opcional` da tabela tem de casar com o que o coletor declara, fonte por fonte. Conferido
que reprova — trocando `opcional` para `False`, o autoteste sai com código 1. Aviso impresso
ninguém lê; foi um deles que sustentou o erro por um dia.

### O que o token abriria, se um dia a editoria o pedir

Medido no código do `INMET.jl`, e é cobertura que hoje não temos:

| rota | o que dá | token? |
|---|---|---|
| `/estacoes/T` e `/estacoes/M` | lista de estações automáticas e manuais | **não** — é a nossa |
| `/token/estacao/diaria/{de}/{ate}/{estacao}/{token}` | série histórica por estação | sim |
| `/token/estacao/dados/{data}/{hora}/{token}` | **todas** as ~600 automáticas numa requisição | sim |

Hoje medimos só capitais, por `/condicao/capitais/{data}`. A terceira rota daria temperatura
medida fora das capitais em **uma** requisição, em vez de um laço por estação.

## §248 · O teto do job era menor que a soma dos tetos dos passos · 27/09/2026

Classe **infraestrutura da rodada**. Quarto defeito da mesma noite, e o que de fato impedia o
commit.

### O que a rodada de controle mostrou

Com os §§245 a 247 dentro, a rodada disparada às 04h47 fez: os cinco passos de descoberta
`success` (o `KeyError` do §245 não voltou), a coleta pesada `success`, o relatório `success` — e
o **commit `skipped`** de novo. Terminou `cancelled`. O passo de publicação deu `success` e
republicou o dado velho, como nas anteriores.

O culpado não foi nenhuma fonte. Foi uma conta.

| teto declarado | minutos |
|---|---|
| Tesseract | 5 |
| clima municipal | 50 |
| coleta pesada | 90 |
| preservar evidência | 20 |
| texto dos PDFs | 25 |
| OCR | 30 |
| **soma dos tetos por passo** | **220** |
| **teto do job** | **180** |

Com 220 contra 180, o job é cortado sempre que os passos correm perto dos seus tetos. Foi o que
houve: job iniciado 04h47, cortado às 07h47 no passo "Ler o texto dos PDFs preservados", que saiu
**`cancelled`**. E aqui está a parte que o §246 não alcançava: **`continue-on-error` não protege
contra cancelamento** — ele cobre `failure`. Todo passo depois do cancelado é pulado, incluindo o
commit.

### Duas correções e uma medição desmentida

Teto do job: 180 → **300**. Cobre os 250 minutos de tetos declarados (já com a coleta em 120) com
50 de folga para os cerca de quinze passos sem teto próprio, e segue longe das 6 horas que o
GitHub daria por omissão. O comentário antigo dizia "a rodada leva 75–105 min"; **deixou de ser
verdade**: a de hoje gastou 70 minutos antes da coleta e 90 na coleta.

Teto da coleta pesada: 90 → **120**. O 90 que o §247 instalou **truncou** a coleta — o passo
começou 05h57 e o seguinte começou 07h27, exatamente no teto. Eu havia lido aquilo como "terminou
por si", porque a conclusão vinha `success`: **`continue-on-error` converte o resultado em sucesso
na conclusão que a API mostra**. Truncamento silencioso mascarado de sucesso é o defeito que esta
sequência toda existe para não repetir, e ele me pegou dentro do próprio conserto.

### O portão

Portão **72**, `scripts/verificar_tetos_da_rodada.py`, com sete asserções (quatro negativas). O
invariante: **soma dos tetos por passo ≤ teto do job**, mais a exigência de que todo job com
passos tenha teto próprio. Ele não promete que a rodada caiba — promete que ela **não está
condenada por construção**. Conferido que reprova o estado de ontem: com job 180 e coleta 90, diz
"a soma dos tetos por passo (220 min) passa do teto do job (180 min)".

### O que segue aberto

O commit dos dados continua **atrás de cerca de 75 minutos de enriquecimento opcional** — checagem
de links, texto de PDF, OCR. Cada minuto ali é um minuto em que um cancelamento custa a rodada
inteira. Comitar antes desses passos, e deixá-los comitar o que acrescentam depois, tira o produto
do caminho do risco. É mudança na ordem de gravação do pipeline, e vai à editoria em vez de ser
arbitrada aqui.

## §247 · A rodada aprende a resolver o conflito, e para de comer o próprio orçamento · 27/09/2026

Classe **infraestrutura da rodada**. Fecha o segundo e o terceiro defeitos abertos no §246.

### Repetir não resolve conflito

O laço de commit da rodada fazia, na falha do rebase: abortar, dormir, repetir — seis vezes.
Repetir reaplica **exatamente o mesmo conteúdo sobre a mesma `main`** e conflita igual. Medido:
seis tentativas, seis conflitos idênticos, nos mesmos seis arquivos, nas rodadas de 24 e 25/09.
A repetição só resolve o caso de **push recusado**, que é outro ramo do laço.

`scripts/unir_conflito_de_rodada.py` resolve **duas classes e recusa todo o resto**:

- **log que só cresce** (`data/log_buscas.json`, `data/historico_mudancas.json`): união pela
  **base comum** — `base + nossos_novos + deles_novos`. Antes de unir, confere que os dois lados
  realmente começam com a base, item a item; se não começarem, o arquivo não se comportou como
  append-only e o script **recusa em vez de adivinhar**. Depois, confere que o total é maior ou
  igual a cada lado.
- **arquivo regenerável** (`docs/MANIFEST_SHA256.txt`, `docs/FILA_PISTAS.md`,
  `data/pistas_revisao.json`): resolve com a versão de cima e é **nomeado** na saída, para que o
  laço regenere a cadeia canônica e emende o commit — senão o portão 12 reprovaria na `main`
  depois do push.

`data/pistas_imprensa.json` e `data/fontes_consultadas.json` seguem **recusados de propósito**,
esperando a editoria: os dois lados alteram os mesmos registros, e escolher qual vence é política
de mesclagem com risco de perda silenciosa de evidência.

### O autoteste que passou com o defeito dentro

Portão **71**, treze asserções, cinco negativas. Ele monta repositórios git de verdade e provoca
conflitos de verdade.

A asserção que mais importa quase não existiu. Ao restaurar o defeito de 23/09 de propósito — a
dedução por **conteúdo** —, **o autoteste passou**: nenhum dos casos tinha item idêntico nos dois
lados, que é justamente o cenário do estrago. Execuções idênticas no log v2 são **tentativas
reais distintas e contam**; uma dedução por conteúdo colapsa as duas e apaga uma sem aviso. Com o
caso acrescentado, o autoteste reprova pelo motivo certo. A primeira montagem dele também estava
errada: com os dois lados escrevendo conteúdo idêntico, o git mescla limpo e não há conflito
nenhum para resolver.

### O passo que comia o orçamento do job

Terceiro defeito. "Atualizar dados" era o único passo pesado **sem teto próprio**, e por isso
consumia os 180 minutos do job inteiro. Medido: a rodada de 27/09 às 01h15 ficou **3 horas**
nele e foi cortada ainda ali — os passos 27 a 39, **incluindo o commit e a publicação**, nunca
rodaram. As de 26/09 às 13h14 e 19h07, idem.

Teto de 90 minutos, com o `continue-on-error` que já existia: a coleta longa é truncada, a falha
fica visível **naquele passo**, e a rodada segue e comita o que coletou. Coleta truncada com
commit é melhor que coleta completa sem commit — e o perigo era que a segunda **se parecia com
sucesso**.

## §246 · Um relatório de diagnóstico estava pulando o commit dos dados · 27/09/2026

Classe **infraestrutura da rodada**. Achado ao preparar a rodada cuidadosa pedida pela editoria.

### O sintoma

A editoria disse, em 27/09, que o monitor de riscos estava desatualizado. Estava: **o último
commit automático de dados bem-sucedido foi em 24/09 às 07h15**. Três dias.

Pior que parado: as rodadas *pareciam* rodar. O passo de publicação dava `success` em todas
elas — o domínio era republicado, com o dado velho.

### A causa

Medido nas rodadas agendadas:

| rodada | relatório | commit |
|---|---|---|
| 26/09 01h14 · 07h13 · 13h14 · 19h07 | `failure` | **`skipped`** |
| 24/09 13h17 → 25/09 19h07 | `success` | **`failure`** |
| 24/09 07h15 e antes | `success` | `success` |

**São dois defeitos sobrepostos.** Este § conserta o primeiro.

O passo "Relatório da execução no repositório privado" clona um repositório privado com
`ROBO_TOKEN`. Desde 26/09 o clone falha. O passo não tinha `continue-on-error`, e o `if:` do
passo de commit é `github.event.inputs.ensaio != 'true'` — sem função de status. **Quando o `if:`
não traz uma função de status, o GitHub soma o `success()` implícito**: "todos os passos
anteriores passaram". O relatório reprovando fazia o `success()` cair, e o commit dos dados
saía `skipped`.

Um relatório de diagnóstico barrando o produto é inversão de prioridade. Ele segue reprovando —
a falha continua visível no passo, que é onde ela deve estar — mas deixa de levar a rodada com
ela.

O que ele **não** conserta: o `ROBO_TOKEN` em si. O clone do repositório privado continua
falhando, e isso é credencial — decisão da editoria, não minha.

### O segundo defeito, medido e não consertado aqui

Nas rodadas de 24 e 25/09 o commit reprovou por conta própria: **seis tentativas de rebase, seis
conflitos idênticos**. Os arquivos: `data/log_buscas.json`, `data/fontes_consultadas.json`,
`data/pistas_imprensa.json`, `data/pistas_revisao.json`, `docs/FILA_PISTAS.md`,
`docs/MANIFEST_SHA256.txt`.

A causa estrutural está medida: **`data/log_buscas.json` tem 20,7 MB em uma única linha** — zero
quebras. Qualquer mudança dos dois lados é conflito textual garantido, porque não há linha para
o git casar. E `busca_web_cadencia.yml` commita esse arquivo **a cada 2 horas**, enquanto a
rodada leva mais que isso. O laço de rebase aborta e repete com o mesmo conteúdo, então conflita
igual nas seis tentativas: a repetição só serve para o caso de *push recusado*, nunca para
conflito.

A resolução correta para `log_buscas.json` está documentada (união pela base comum, nunca
dedução por conteúdo). Para `data/pistas_imprensa.json` e `data/fontes_consultadas.json` **não
está**: os dois lados alteram os mesmos registros, e escolher qual vence é política de mesclagem
com risco de perda silenciosa de evidência — o estrago que o projeto já sofreu uma vez, em
23/09. Levado à editoria em vez de arbitrado.

## §245 · A fila de pistas aguenta dois produtores no mesmo arquivo · 27/09/2026

Classe **coleta**. Preparo da rodada de atualização.

O ensaio da rodada mostrou `KeyError: 'hash'` **três vezes**, nos três passos que gravam pista
de descoberta em imprensa. A causa: `data/pistas_imprensa.json` tem **dois produtores**. O monitor de imprensa
grava pistas com `alvo`, `titulo`, `url` e `hash`; a esteira de triagem grava outros 638 registros,
com `id`, `municipio` e `documento` — e **sem** `hash`, porque a identidade deles é outra.

`registrar()` montava o conjunto de vistos exigindo `hash` de todos e quebrava na primeira pista
alheia. Os três passos têm `continue-on-error: true`, então a rodada **não** morria: ela seguia e
commitava. O que morria eram os três passos de **descoberta** — instrumentos novos na imprensa
nacional, atos de resposta, e o painel da Política Por Inteiro — calados, a cada rodada. Perda
silenciosa de cobertura é pior que rodada vermelha: rodada vermelha se vê. A dedução passa a usar só quem tem `hash`, e a função anota quantos registros de outro
produtor ficaram fora dela. Nada se perde, e nada de outro esquema é reescrito por este monitor.

Portão novo (**70**): `scripts/testar_fila_de_pistas.py`, cinco asserções, offline, sem tocar em
`data/`. Conferido que ele **sabe reprovar**: com a linha antiga restaurada, o `KeyError` derruba
as duas primeiras — asserção que não sabe reprovar não vale nada.

## §244 · Cabeçalho novo, duas fontes trocadas por órgão competente, figuras reescritas · 27/09/2026

Classe **design e coleta**.

### O cabeçalho da página principal

Pedido da editoria, com o site da Futura Evidence Lab como referência. O que fazia o topo parecer
institucional não era cor nem moldura: era **escala e ar**. A marca era um logotipo de canto ao
lado de um título do mesmo tamanho, tudo apertado e separado por filete, e a descrição corria
1132px — cerca de **110 caracteres por linha**, contra os 45 a 75 da medida confortável.

Agora a marca é o elemento dominante (620px), o nome é declaração em Fraunces no topo da escala, e
a descrição ocupa coluna estreita ao lado. A separação é por espaço, não por filete. Foram
tomados os **princípios** da referência, não a composição: o `CLAUDE.md` diz que as duas marcas têm
parentesco visual "sem ser gêmea" e proíbe copiar o leiaute de uma na outra.

O nome por extenso fica **só na página principal**; as outras doze ficam com o logotipo, e o texto
invisível voltou ao nome completo — sem isso o cabeçalho delas se anunciaria ao leitor de tela
apenas como "MARÉ ·".

### O menu como uma peça só

A editoria pediu que os dez botões fossem tratados como uma peça única, com o degradê
atravessando todos. Agora o degradê vive **na barra**: não há emenda porque não há dois pintados.
Os botões esticam para preencher a linha — com largura de conteúdo sobrava cor no fim.

**A faixa morta de luminosidade, que foi o limite real.** Com texto escuro o contraste só atinge
4,5:1 quando o fundo tem L≥0,201; com texto branco, quando tem L≤0,183. Entre 0,183 e 0,201
**nenhum dos dois passa**, e o arco do índice atravessa essa faixa duas vezes, debaixo de botão.
Por isso o arco inteiro desceu para o registro escuro: aí o texto branco passa em qualquer
posição, inclusive se um rótulo mudar de tamanho. Medido: 4,69:1 em 1280px, 4,72:1 em 768px,
4,70:1 em 375px. Abaixo de 1020px o eixo vira vertical, senão o degradê se repetiria em cada linha.

Com isso **somem as dez regras `:nth-child` de cor** — e some a lista escrita à mão que envelhecia
a cada item novo no menu. O portão que a vigiava virou outro: confere que a cor vem de um degradê
e que nenhuma regra por posição voltou.

### Duas fontes trocadas por órgão competente

**Temperatura.** Vinha do Open-Meteo, que roda modelos europeus e americanos. O **INMET** publica
previsão própria para as 27 capitais em JSON aberto, sem chave — e já era a fonte dos avisos e das
estações neste mesmo site. As 27 UFs passam a ter máxima, mínima e resumo do tempo do instituto
oficial brasileiro. Critério declarado no dado: maior máxima e menor mínima entre manhã, tarde e noite.

**Qualidade do ar.** A página mostrava PM2,5; passa a mostrar **índice**, que é o que interessa a
quem lê. O índice vem **pronto da fonte** e nunca é calculado aqui: calculá-lo faria dele uma
afirmação do Monitor, e ele precisa ser evidência de terceiro. Não existe índice nacional aberto
— conferido: o Qualiar do MMA não resolve (HTTP 000), o QUALAR da CETESB cobre só São Paulo, o
WAQI exige token. A escala é a europeia, e o texto de apoio diz isso.

### Os mapas param de afirmar o que o dado não diz

Temperatura e ar eram medidos **na capital** e pintavam o **estado inteiro**. A medição de Rio
Branco colorindo todo o Acre afirma visualmente uma cobertura estadual que o dado não tem — o que
a direção de arte §10 proíbe. Agora são **pontos nas capitais** sobre contorno neutro.

### As oito figuras

A editoria apontou que as legendas não seguiam critério. A governança §13 exige legenda
**autossuficiente**, e três falhavam: a do RONI dizia "a mesma anomalia do ONI", a da Anomalia
dizia "sem a suavização do ONI e do RONI". Quem lê uma figura não deveria precisar ter lido as
outras. Reescritas, cada uma se explica sozinha.

As quatro figuras de mapa **não tinham texto de leitura nenhum**; ganharam. A de focos explica que
foco de calor não equivale a incêndio — o título continua preciso porque chamá-lo de incêndio
afirmaria mais do que o satélite sustenta. A de seca declara a cadência mensal: a fonte é
consultada todo dia, e o mapa mais recente que ela publica é o do mês anterior.

O portão 19 reprovou três vezes até as legendas caberem em **2 frases e 240 caracteres**, que é o
limite da §13. Ele conta a descrição **somada à leitura dinâmica do valor** — a descrição teve de
virar uma frase só.

### O risco projetado muda de lugar

O mapa saiu do monitor de riscos e o dado foi para o **cartão de cada estado** na página inicial,
que é onde o leitor procura o próprio estado. No cartão vai o vocabulário fechado (estiagem,
incêndios, chuvas); a frase inteira do boletim fica na janela de detalhe.

### O teto de palavras da inicial

A página estava a poucas palavras do teto editorial e estourou. Cortei **só o que eu havia
acrescentado**, e enxuguei a frase do boletim preservando todos os fatos — painel federal, data,
projeções por região, obrigação legal. Página em 947 de 950.

### Portões

Doze checagens novas nos autotestes de coleta, seis delas negativas. Em `verificar_runtime_sinais.js`,
as checagens do mapa removido foram **substituídas**, não apagadas: agora exigem que ele não volte,
e que temperatura e ar desenhem ponto e não pintura por UF. O portão de fichas semânticas pegou a
ficha órfã da figura removida — fazendo exatamente o que existe para fazer.

## §243 · O relatório em PDF sai do detalhe do estado · 26/09/2026

Classe **produto**. Pedido da editoria: *"remova de todos os cartões estaduais a opção de baixar o
PDF. Isso não será mais necessário."*

**A distinção que precisou ser feita antes de mexer.** O site tem **dois** botões de PDF, e eles não
são a mesma coisa: `#btnPDFEstado`, na janela de detalhe do estado, e `#btnPDF`, no cartão da cidade
("Encontre sua cidade"). O pedido nomeia os cartões **estaduais**, então saiu só o primeiro. O
municipal continua onde estava; se a editoria quiser tirá-lo também, é pedido separado.

**O que saiu junto, por ter ficado órfão da própria remoção.** `gerarPDFEstado(uf)` existia só para
esse botão, e o ouvinte delegado em `#detail` existia só para alcançá-la. Os dois foram removidos.
`gerarRelatorioCidadao` **fica**: é o gerador que o cartão da cidade usa.

**Portões.** Duas checagens descreviam o mundo antigo e foram **atualizadas, não apagadas**: uma
clicava nos dois botões e exigia que ambos respondessem (agora exerce só o municipal); a outra exigia
que "estado e município usassem o mesmo gerador" (agora confere que o municipal continua ligado a
ele). Duas checagens novas garantem que o botão não volte em silêncio — uma no DOM, outra no
código-fonte — e as duas foram provadas reintroduzindo o botão de propósito.

O comentário do bug de 31/08/2026 (`"gerarPDFEstado is not defined"`, caçado porque o portão não
clicava no botão) foi preservado no arquivo do portão: a lição — checagem que não exercita o
caminho não vê o defeito — vale independentemente do botão ter saído.

## §242 · O calendário vira linha do tempo; o formulário, três etapas · 26/09/2026

Classe **design**. Nenhum dado, número ou fonte mudou.

### O calendário

Pedido da editoria: *"é preciso criar alguma forma gráfica para representar o que significa cada uma
dessas datas, como se elas já tivessem passado, como se tivessem ainda correndo"*.

A tabela não transmitia tempo nenhum. "Em 15 dias" era texto perdido no meio de uma frase, e a
janela crítica do El Niño — seis meses — aparecia como dois números separados por travessão.

O dado já sustentava a resposta, e foi isso que destravou: **prazo tem `data_base` e `vencimento`**,
ou seja, é intervalo, não ponto. Intervalo se desenha.

- **Um eixo de tempo só, compartilhado por todas as faixas.** Mesma escala, logo as durações ficam
  comparáveis entre si — o que a tabela não permitia.
- **Uma linha vertical de HOJE** atravessando todas as faixas na mesma posição. É ela que faz "já
  passou" e "ainda corre" serem visíveis sem ler texto.
- **Prazo vira barra**: parte decorrida cheia, trilho claro é o que falta.
- **Data única vira ponto**, vazado enquanto não chega.
- **Três estados, não dois.** A janela do El Niño ainda não começou, então não diz "0 de 181 dias":
  diz "começa em 5 dias · dura 181 dias".

**Uma decisão de propósito:** o degradê das barras do índice **não** é reaproveitado aqui. Naquela
arte ele significa "valor de 0 a 100", e usá-lo para tempo criaria ambiguidade entre duas grandezas
diferentes. A barra de tempo é lisa, em mineral e sintético.

### O formulário

Pedido: *"está muito corporativo"*. A pesquisa de usabilidade de formulário converge em três pontos,
e os três se aplicavam: coluna única, agrupamento lógico, e dizer o destino antes do envio.

A grade `1fr 1fr` punha estado e município lado a lado e depois quebrava para largura inteira sem
razão — era daí que vinha o ar genérico. Agora: **três etapas numeradas** (Onde, O documento, Você),
coluna única com medida de leitura, e o par estado/município mantido lado a lado, que é a exceção
que a própria pesquisa reconhece. O número da etapa vem de contador CSS, não escrito à mão.

O aviso **"o que acontece depois"** fica ao lado em tela larga, acompanhando a rolagem, e ocupa a
metade do painel que sobrava vazia. Quem decide clicar precisa saber o destino antes, não depois.

**Nenhum campo entrou, saiu ou mudou de nome.** O que o Monitor coleta é decisão da editoria
(governança §29); ordem, agrupamento e remoção de redundância, não.

### O cabeçalho e o menu

Pedidos da editoria, no mesmo turno: a descrição ocupava só parte da largura e colava no menu sem
separação; a gradação estava discreta demais; e a página corrente devia ir a **branco**, fora do ramo.

- Descrição em largura inteira (1132px, a mesma do parágrafo abaixo), e o menu ganhou uma linha
  acima que o separa do texto.
- Tinta dos botões de 32% para **60%**. Medido: o pior contraste de texto cai de 11,5:1 para 6,6:1,
  ainda bem acima do mínimo AA.
- A página corrente sai da terracota e vai a **branco**, com borda e texto em `--ink` (18,5:1).
  É inversão: entre dez botões de tinta, o único branco é o que se destaca, e não gasta mais uma cor.
  Isso substitui a decisão do §241, tomada horas antes.

### O teto de palavras, que foi o limite real

A página inicial já estava a **6 palavras** do teto editorial (944 de 950). Os dois acréscimos que a
pesquisa recomendava custavam 43. Não cabiam.

Cortei **só o que eu mesmo acrescentei**, sem tocar no texto da editoria: dentro da etapa 2 havia uma
dica que repetia quase palavra por palavra o texto de apoio da seção (remoção de redundância é do
§29), e o aviso de destino encolheu de 45 para 13 palavras — ficou mais curto e mais forte.
Página em **948 de 950**. Fica registrado: qualquer texto novo nessa página agora exige cortar outro.

### Portões

Duas checagens de calendário descreviam o formato antigo e foram **substituídas, não afrouxadas**: o
rótulo do prazo passou de "em 15 dias" para "44 de 59 dias" (diz quanto já correu, e não só quanto
falta), e a ordenação passou a ser pelo vencimento, não pelo início — numa linha do tempo o que
interessa é o que vence primeiro, e a chave virou a última data do texto.

Três checagens novas, todas provadas quebrando de propósito:

- cada linha tem barra (intervalo) ou ponto (data única);
- a linha de hoje está na **mesma posição** em todas as faixas — sem isso a escala não é comum e as
  durações deixam de ser comparáveis, que é a razão de existir do eixo único;
- toda barra declara quanto do prazo já correu.

**Três defeitos meus, pegos pelos portões antes de subir.** Pontos de quebra de 900px e 560px, quando
o projeto só admite 640 e 1020 (`verificar_estrutura.js`); margem de −5px, fora da escala de
espaçamento; e uma regra órfã do desenho de tabela (`white-space:nowrap` na data) que ficou abaixo do
bloco que substituí e causava **rolagem horizontal em 375px**. Conferido depois: sem rolagem em
1280, 768 e 375.

## §241 · Os estados viram grade territorial; o menu ganha gradação · 26/09/2026

Classe **design**. Nenhum dado, número ou fonte mudou.

### Os 27 estados: a região deixa de mandar na geometria

O §239 trocou cartão por linha alinhada para matar o quadrante vazio. Consertava a geometria e
custava caro: virava tabela institucional, que a direção de arte §1 proíbe. **A editoria recusou, e
com razão** — eu tinha juntado duas coisas que não são a mesma, "coluna por região" e "cartão", e
joguei fora a presença de cada estado junto com o defeito.

Tentativa seguinte: cartão de volta, região em faixa horizontal. Resolvia, mas ainda deixava um
cartão órfão por faixa e não dava panorama nenhum.

O que resolve é **trocar o critério de arranjo**. Enquanto a contagem por região definir a
geometria, o desequilíbrio volta em qualquer forma. Agora o arranjo é **geográfico**: cada estado
ocupa a posição aproximada dele no país, numa grade de ladrilhos — o padrão que NYT, Washington
Post, The Economist, Guardian e FiveThirtyEight usam para territórios de tamanho muito desigual.
A grade é a **`br_states_grid1` do pacote `geofacet`**, publicada e buscada da fonte; nenhuma
posição foi estimada aqui. A `br_states_grid2`, mais densa, foi testada e descartada: não lê como o
Brasil (o Nordeste cai na mesma fileira do Amazonas).

**Por que ladrilho e não a forma real de cada estado**, que a editoria perguntou. Medido na
geometria que o próprio site já usa (`data/geo_uf.json`): o Amazonas tem **271×** a área do Distrito
Federal, e num mapa de 760px — o maior que cabe na página — o cartão **não caberia em 16 dos 27
estados**; o DF fica com 17×10px, onde não cabe nem a sigla. E há razão mais séria que espaço: num
mapa de área fiel, cinco pontos de diferença no Amazonas gritam e os mesmos cinco pontos no DF
somem. O índice é ponderado por **população coberta**, que não tem relação com área — um mapa fiel à
área contaria visualmente o que o indicador não sustenta, o que a direção de arte §10 proíbe.

Foi prototipada também uma versão com a **silhueta real** de cada UF dentro do ladrilho (forma
verdadeira, escala normalizada; desvio de proporção medido em 0,00%). A editoria recusou por
poluição visual, e o julgamento está certo: a forma do país já vem do arranjo das células, e repetir
dentro de cada uma competia com o dado.

**A célula mostra sigla, nome por extenso, nota e as duas barras.** O nome veio por pedido da
editoria e sai de `DATA.ufs[].nome`, a mesma fonte que a janela de detalhe já usava — nenhuma
segunda lista de nomes entrou no repositório.

| | antes (§238) | linha (§239) | grade territorial |
|---|---|---|---|
| painel em 1280px | ~1500px | 1291px | **972px** |
| colunas raggeadas | 5 (9·7·4·4·3) | — | — |
| quadrante vazio | ~950px | não | não |
| panorama nacional | nenhum | nenhum | sim |

**O que saiu da célula, e o que isso obrigou a fazer.** Os três campos de texto (diários,
instrumento estadual, capital) não cabem em 140px e passaram para a janela de detalhe. Ao conferir,
descobri que **"diários municipais consultados" não existia no detalhe** — tirá-lo da face sem mais
nada apagaria o alcance da varredura da interface inteira. Ele foi acrescentado ao detalhe no mesmo
commit. Instrumento e capital já estavam lá.

**Tela pequena** (direção de arte §24, recompor e não comprimir): medido em 375px, uma grade
geográfica de seis colunas dá célula de 54px, nove nomes quebram e "Pernambuco" é cortado. Abaixo de
1020px a grade sai e as células voltam a três colunas, e a duas abaixo de 640px. Como a ordem do DOM
é decrescente pelo índice, no celular a lista sai **ordenada por nota** — que é a leitura útil onde
não há mapa.

### O menu: gradação do vermelho ao azul

Pedido da editoria: os botões do menu formam, da esquerda para a direita, uma gradação entre
vermelho e azul, como a barra do índice. Sem efeito nenhum, só cor.

Nenhum matiz novo entrou: o ramo é o próprio **`--degrade-resposta` lido ao contrário** (ele já vai
de frio a quente), amostrado em dez pontos — argila → âmbar → sintético. Termina no sintético e não
no mineral porque o mineral é claro demais: como borda ele mediria **2,6:1** sobre branco, abaixo do
mínimo de 3:1 da WCAG 1.4.11.

**O botão não é preenchido, e isso foi medição e não gosto.** Com a cor cheia no fundo e texto
branco, **oito dos dez botões reprovariam** o mínimo AA — o âmbar dá 3,1:1 e até o sintético, o mais
escuro do lado frio, dá 4,39:1. Ficou cor cheia na **borda**, uma tinta de 32% dela no **fundo**, e
texto em `--ink`: pior borda em **3,16:1**, pior texto em **11,5:1**.

A página corrente segue em terracota preenchida — entre botões de tinta clara, ela se destaca
sozinha. O botão de ação ("Para gestores") perdeu a cor própria e guarda o peso de chamada só pela
borda mais grossa, para a gradação não ter buraco no meio.

Dois detalhes que custaram uma volta cada. A ordem das regras importa: `:nth-child` empata alto na
especificidade, e os seletores de estado (hover, botão de ação, página corrente) precisaram repetir
`> :is(a, span)` para vencer o ramo. E dar **negrito** ao botão de ação criou um segundo estilo na
família "navegação" e deixou `verificar_consistencia_visual.js` vermelho — o peso voltou ao dos
demais. O mesmo portão pegou a legenda nova como `<p>` de corpo de painel; ela passou a usar
`.legend`, o componente que o site já tinha.

### Portões

`verificar_runtime.js` ganhou três checagens, todas provadas nos dois sentidos:

- as 27 células têm sigla e nome por extenso (tirar o nome → vermelho);
- cada uma tem posição na grade e não há duas no mesmo lugar (pôr RS e PR na mesma célula → vermelho);
- os dez botões do menu estão **exatamente** nas posições que o `:nth-child` de `base.css` pinta — a
  checagem lê o DOM e a folha e compara (item novo no menu → vermelho; posição errada na folha →
  vermelho). Lista escrita à mão envelhece calada, e este projeto já viu esse defeito três vezes
  (§213, §222, §226).

A checagem antiga exigia "cinco campos visíveis na face do cartão". Ela não descreve mais o que o
site faz, e foi substituída em vez de contornada.

### O que segue pendente

### O cabeçalho: a editoria escolheu a opção C

O §239 deixou o cabeçalho com **três** parágrafos — o de orientação, novo, mais os dois que já
existiam — e a decisão de fundir ficou com a editoria. Foram montadas três páginas inteiras e
navegáveis para a escolha; ela escolheu **C**.

O boletim de 29 de junho e a obrigação legal **sobem para o parágrafo de abertura**, que passa a
dizer de uma vez o que o site é e por que ele existe. O segundo parágrafo fica só com o método do
índice e recebe, no fim, a frase do teto de ausência. **Nenhum fato, número ou fonte saiu**: o painel
federal, a data, as projeções por região, a obrigação legal, a ponderação por população, o segundo
índice e o teto de ausência estão todos lá. O cabeçalho foi de 618px para **578px** em 1280px — a
troca nunca foi de tamanho, foi de ordem de leitura.

### O que segue pendente

A grade ainda **não é uma figura no padrão do projeto** — sem numeração, fonte e data de
atualização, como o quadro de estados também não era antes. Fica nomeado, não consertado de
passagem.

## §240 · A linha do estado passa a ser alcançável por teclado · 26/09/2026

Classe **acessibilidade**.

Achado ao conferir, a pedido da editoria, se a linha do estado continuava clicável depois do §239.
Continuava — e o mesmo teste mostrou que **nunca foi alcançável por teclado**. A linha é uma `<div>`
com ouvinte de clique, sem `role` e sem `tabindex`: quem navega por Tab não abria o detalhe de
estado nenhum, na página inicial nem no MARÉ · Saúde. O defeito é **anterior** à troca de cartão por
linha; a troca só o deixou visível.

`role="button"`, `tabIndex = 0`, Enter e Espaço acionando como qualquer botão, e `aria-label` vindo
do mesmo texto do `title` — sem ele o leitor de tela anunciaria a linha inteira campo a campo.

O `:focus-visible` global desenha o contorno 2px **para fora**, e numa linha de 31px que ocupa a
largura inteira ele sangra na linha vizinha e lê como dois filetes soltos. Desenhado para dentro
(`outline-offset:-2px`) e com o mesmo realce do hover, o alvo do teclado ficou tão evidente quanto o
do mouse.

**Por que a checagem entrou no portão que já existia, e não num novo.** `verificar_runtime.js` já
clicava em SC e exigia que o detalhe abrisse — e passava verde com o defeito no ar. A checagem do
teclado fica ao lado dela, de propósito: é o mesmo comportamento, visto pelo outro dispositivo de
entrada. O mesmo em `verificar_runtime_saude.js`. As duas foram provadas nos dois sentidos: tirar o
`tabIndex` deixa a primeira vermelha, e tirar o acionamento no `keydown` deixa as outras duas.

Detalhe de implementação do portão: jsdom não implementa `dialog.close()`, e a própria página já
contorna isso (`if (typeof dlg.showModal === 'function') ... else dlg.open = true`). A checagem
fecha o diálogo com `open = false` pela mesma razão.

Verificado também fora do jsdom, em navegador de verdade: na inicial o Tab chega à primeira linha no
16º passo e na de saúde no 211º (a página tem mais alvos antes), e Enter e Espaço abrem o detalhe
nas duas, em 1280px e em 375px.

**Uma armadilha para a próxima vez.** O `verificar_consistencia.py` confere equilíbrio de tags
contando `<div` contra `</div>` na página **com o JS embutido** (`pagina_completa.ler_pagina`). O
primeiro comentário que escrevi aqui dizia, em prosa, que a linha "sempre foi uma ‹div› com ouvinte
de clique" — e o literal dentro do comentário entrou na contagem e reprovou o portão, sem que
nenhuma tag de verdade estivesse aberta. A contagem é de texto, não de árvore: **não escreva nome de
tag por extenso em comentário de `assets/js/*.js`.**

## §239 · O cabeçalho ganha nome e os 27 estados deixam de ser 27 cartões · 26/09/2026

Classe **design**. Seis pedidos da editoria sobre a página inicial, aplicados no laço de design do
§237. Nenhum dado, nenhum número e nenhuma fonte mudaram.

**Menu: a página corrente passa a terracota.** Era musgo — a mesma cor do botão "Para gestores" e do
botão primário do site. Duas funções na mesma cor. A terracota é o acento único do sistema de marca e
não tem outro papel. Branco sobre `#C04430` mede **5,1:1**, acima do mínimo AA para texto normal.
A regra vale em **todas** as páginas, e não só na inicial: é o mesmo componente, e o `CLAUDE.md` pede
o mesmo token para o mesmo papel.

**Logotipo de 320px para 420px — e o nome do site sai de dentro do SVG.** O descritor
"· MONITOR DE ANTECIPAÇÃO E RESPOSTA AO EL NIÑO" era desenhado a 9,5px do `viewBox` e chegava à tela a
**7,6px**: abaixo do piso de 12px da escala do próprio site, e ilegível. Agora é texto de verdade, em
Fraunces 300 no tamanho `--fs-h2`, selecionável e pesquisável. O `.sr-only` do `<h1>` encolheu para
"MARÉ ·" porque o nome deixou de ser invisível — senão o leitor de tela o ouviria duas vezes.

Isso **atravessou as 12 páginas**, e de propósito: o descritor estava dentro do SVG, e mexer nele só
na inicial partiria a marca em duas versões. Nas onze páginas secundárias o logotipo é exibido a
210px, o que levava o mesmo descritor a **5px de altura** — lá ele era ainda menos legível, e era o
único lugar onde o nome completo do site aparecia. Agora é o mesmo texto, no mesmo lugar, em
`--fs-h4`. Junto, o `viewBox` foi de `0 0 400 152` para `0 0 400 116`: sem o descritor sobravam 36
unidades vazias abaixo da linha d'água, que apareciam como um vão entre o logotipo e o que vem
depois. Nenhum traço da marca foi alterado.

**Parágrafo de orientação no cabeçalho.** Diz o que o site verifica, o que esta página mede, o que as
outras acompanham, e que registro sem localização até o corte é declarado como tal. Escrito contra os
§§16, 18, 20 e 21 da governança: sem metadiscurso, sem palavra de juízo, sem prosa de IA.

**Campos de formulário em osso.** O fundo era `--surface-2` (`#F0F4F3`), um mineral-claríssimo que
sobre branco lê como o cinza padrão de navegador. Passa a `--campo` (`#EDE6D8`), o osso da marca —
a única base clara que o sistema autoriza — com borda quente da mesma família. Texto secundário
sobre ele mede **5,0:1**. Zebra de tabela e trilho de barra **não** mudaram: continuam em
`--surface-2`, que é o que eles são.

**Os estados: a região deixa de ser coluna e o cartão vira linha.** O pedido foi "grande e pesada e
com uma estética sem harmonia, porque muitas regiões têm muitos estados e outras têm poucos". A causa
é geométrica e foi medida: uma **coluna por região**, com 9 ladrilhos no Nordeste contra 3 no Sul,
numa grade de **1365px** de altura em que toda coluna herda a altura da mais longa — sobrava um
quadrante inteiro vazio embaixo à direita. Enquanto o número de estados por região definir a
geometria, nenhum ajuste de espaçamento resolve.

A região virou **faixa horizontal**: o desequilíbrio 9×3 passa a ser diferença de comprimento de
faixa, que é informação, e não buraco de leiaute. E o cartão virou **linha**, porque a direção de arte
§6 diz que cartão não é unidade narrativa e só se usa quando a informação é mesmo modular: 27 estados
de uma mesma série não são 27 módulos. Alinhadas, as barras do índice passaram a ser **comparáveis
entre estados**, o que 27 cartões soltos não permitiam; e dentro da faixa a ordem é decrescente pelo
índice, não alfabética — em ordem alfabética o leitor tinha 27 valores e nenhuma leitura. Estado sem
índice vai para o fim da faixa, sem posição inventada para quem não tem número.

Duas barras lado a lado sem rótulo dependeriam só de posição para dizer o que são, o que a direção de
arte §23 proíbe: entrou um cabeçalho de colunas que **descreve** a variável e a unidade e nada mais,
como manda o portão 19. Abaixo de 1020px a linha se abre em duas e o cabeçalho sai, porque apontaria
para o lugar errado — por isso o primeiro campo voltou a se descrever sozinho ("diários: 62 de 62"),
já que no celular não há coluna nomeada e leitor de tela nunca teve uma.

O que **não** mudou: a face de três campos continua visível em todo estado, o marcador de capital
continua lá, o detalhe continua abrindo em janela ao clique, e nenhuma cor nova entrou.

| | antes | depois |
|---|---|---|
| altura da grade dos estados | 1365px | 1291px (painel) |
| altura da linha/cartão | 139px | 31px |
| colunas raggeadas | 5 (9·7·4·4·3) | nenhuma |
| barras comparáveis entre estados | não | sim |

**O que fica para a editoria decidir.** O cabeçalho agora tem **três** parágrafos: o novo, de
orientação, e os dois `.site-sub` que já existiam. Eles não se contradizem, mas o primeiro
`.site-sub` (o boletim de 29 de junho) cobre parte do mesmo terreno. Não apaguei texto que ninguém
pediu para apagar; se a editoria quiser fundir, é um pedido separado.

## §238 · O regime de trabalho muda: a skill vence nas duas colisões · 26/09/2026

Classe **regra de trabalho**.

O §236 instalou a `karpathy-guidelines` subordinada, com duas colisões nomeadas, e registrou que
nelas vencia o repositório. A editoria leu as duas escritas e decidiu o contrário, no mesmo dia:
**vence a skill**. O `CLAUDE.md` foi alterado, e o bloco de precedência dentro da própria skill foi
invertido para não ficar dizendo o contrário do que vale.

**O que muda, em concreto.** Antes: execução silenciosa, sem pedir confirmação para decisão técnica
de rotina, e mandato permanente para *"avaliar todo o código de todos os coletores e implementar
todas as soluções que você conhece"*. Agora: declarar a suposição antes de implementar e **parar e
perguntar diante de dúvida real**; apresentar as leituras quando há mais de uma em vez de escolher
calado; e **escopo é o que foi pedido** — código morto pré-existente e defeito fora do escopo se
**mencionam**, não se consertam de passagem. Órfão que a própria mudança criou continua sendo
limpo. E toda tarefa de vários passos passa a declarar o plano no formato `passo → verificação`.

**O que a troca custa, registrado porque ela tem custo.** Os §§226 a 235 nasceram do mandato
anterior e são transversais por definição: a política de espera saindo de um coletor para os
dezesseis, 75 datas em UTC migradas em 41 arquivos, 33 escritas de JSON levadas à porta atômica, 23
arquivos passando a um cliente só, o muro de robô que o detector não via. Sob a regra nova, nenhum
deles teria acontecido sem pedido específico. As **137 barreiras do inventário do §230** seguem
medidas e nomeadas no arquivo, e nenhuma será atacada sem que a editoria peça.

As três fontes de verdade não entram nessa troca: `METODOLOGIA.md`,
`AI_EDITORIAL_NARRATIVE_GOVERNANCE.md` e `AI_VISUAL_ART_DIRECTION.md` são limite de prova e de
governança, e continuam acima de qualquer skill.

## §237 · Laço de design: ver em cinco segundos o que levava quatro minutos e meio · 26/09/2026

Classe **rotina de trabalho**.

Pedido da editoria: uma rotina rápida para mudança de fonte, cor, forma de botão e texto, que não
precisasse atravessar partes do código que não servem a esse propósito, e que deixasse ver o
resultado depressa.

**O que já existia, medido antes de construir qualquer coisa.** A trilha `paginas` do
`portoes_locais.py` já rodava 23 dos 69 portões; cronometrada portão a portão, são **4min25**, com
sete portões respondendo por 216 dos 265 segundos. E mudança de fonte, cor ou forma toca apenas
`assets/tokens.css` e `assets/base.css` — **nada em `data/`, nada na cadeia de derivados**.

**O que estava lá e não funcionava.** `scripts/auditar_ux.js` — 12 páginas × 3 janelas (375, 768,
1280), rolagem horizontal, elemento mais largo que a tela, texto abaixo de 12 px, alvo de toque,
títulos, ids, alt, lang — apontava para **caminhos de sessões antigas** (`/tmp/index_pdf_test.html`,
`/home/claude/audit/pacote/…`, `/mnt/user-data/outputs/…`) que não existem em máquina nenhuma. Ele
rodava e não auditava nada. Segunda razão do abandono: usava `@axe-core/playwright`, **que nunca foi
declarado no `package.json`**.

Agora a lista de páginas é **derivada** dos `*.html` da raiz, como `validar_workflows.py` já fazia —
página nova entra sozinha. O axe ficou **opcional**, e o relatório diz quando ele não está
instalado: não acrescentei dependência que ninguém pediu, e o contraste, que é o que mais importa
numa troca de cor, já é conferido por `verificar_acessibilidade.js`. E ele passou a **gravar
captura** em 375 px e 1280 px, porque a pergunta da editoria é "como ficou", e relatório de axe-core
não responde isso. As páginas são servidas por HTTP e não abertas por `file://`: elas buscam
`data/*.json` ao vivo, e em `file://` o navegador recusa esse fetch — a auditoria mediria uma página
sem dado nenhum. Página que não carrega **interrompe** em vez de virar relatório limpo.

**Os perfis, e por que o assunto é declarado e não escolhido.** O `portoes_locais.py` deriva a
trilha da condição `if: dado_mudou` do próprio CI, e o docstring dele diz por quê: *"é a mesma
divisão que o CI faz, e por isso não inventa uma terceira semântica"*. O assunto segue a mesma
disciplina — fica numa linha `# assunto: cor texto rapido` acima de cada comando, dentro do
`portoes.yml`, que é o único lugar que reprova de verdade. O `CLAUDE.md` registra que subconjunto
escolhido a olho custou um ciclo de CI em 23/09/2026.

E `validar_workflows.py` passou a **reprovar portão de página sem assunto declarado** — o defeito
que este projeto já viu três vezes (§213, §222, §226) é a lista que envelhece: portão novo entra,
ninguém o declara, e o perfil segue verde sem nunca rodá-lo. Verificado nos dois sentidos: tirar um
`# assunto:` deixa o portão vermelho.

**Os tempos, medidos:**

| comando | portões | tempo |
|---|---|---|
| `cor --rapido` / `texto --rapido` | 6 | **5 s** |
| `cor` | 16 | 2min23 |
| `texto` | 17 | 2min08 |
| `paginas` | 23 | 4min25 |
| `tudo` | 69 | a suíte inteira |

O atalho `/design` encadeia a sequência, e as capturas saem em `previa/`, ignorada pelo git: são
para olhar, não para guardar. Provado ponta a ponta com uma troca real de `--link` no `tokens.css`,
revertida depois.

**O que o laço não é, e está impresso no próprio rodapé dele.** Perfil parcial não libera nada:
roda só o que aquele tipo de mudança toca, e o que a mudança não deveria tocar segue sem conferência
até a suíte inteira rodar. Antes do PR, `tudo`.

**Um limite honesto.** Os portões conferem contraste, token e componente; **não** conferem os papéis
da paleta — "argila e âmbar nunca como fundo de área grande", "bioluz e sintético um por vez". Na
prova de ponta a ponta, trocar `--link` por argila passou nos seis portões rápidos, porque o
contraste fecha, e mesmo assim é uma cor de calor virando protagonista. O `AI_VISUAL_ART_DIRECTION.md`
§25 continua sendo leitura humana, e o laço rápido não substitui o checklist da marca.

## §236 · A skill de conduta de código entra subordinada, e com duas colisões nomeadas · 26/09/2026

Classe **regra de trabalho**.

A editoria pediu a instalação da skill `karpathy-guidelines`
(<https://github.com/multica-ai/andrej-karpathy-skills>). Ela entrou em
`.claude/skills/karpathy-guidelines/SKILL.md` como **cópia**, e não como plugin de marketplace:
cópia aparece no diff e não cria dependência de terceiro na cadeia de execução. O corpo é **literal
da origem, conferido byte a byte** (2.224 caracteres, commit `2c60614`), com um bloco do projeto
antes dele — procedência e precedência —, para que a comparação com a fonte continue possível.

**Licença, pelo que existe e pelo que não existe.** O frontmatter da skill e o `plugin.json` da
origem declaram MIT; **o repositório não tem arquivo `LICENSE`** — a API do GitHub devolve 404 e
`license: null`. Como este repositório é público, fica registrado assim.

**O conteúdo foi lido inteiro antes de instalar**, e é benigno: quatro seções de conduta para
escrever código, sem rede, sem credencial e sem nada que contorne portão. Duas delas, porém, colidem
de frente com regras deste repositório, e nas duas **vence o repositório**:

- **"If uncertain, ask. If something is unclear, stop."** O `CLAUDE.md` manda o oposto — execução
  silenciosa, sem pedir confirmação para decisão técnica de rotina — e lista as únicas seis razões
  para interromper. A editoria reafirmou isso como instrução permanente. Do resto da seção fica o
  que não colide e é bom: declarar a suposição em vez de esconder, e dizer quando há caminho mais
  simples.
- **"Don't refactor things that aren't broken."** Boa regra geral, e o oposto do que a editoria
  pediu aqui: *"avalie todo o código de todos os coletores e implemente todas as soluções que você
  conhece"*. Os §§226 a 235 são trabalho transversal por definição — a política de espera saindo de
  um coletor para os dezesseis, 75 datas em UTC em 41 arquivos, 33 escritas levadas à porta
  atômica, 23 arquivos passando a um cliente só. Sob leitura literal dessa regra, **nenhum deles
  existiria**, e os defeitos que corrigiram seguiriam em produção. O que a seção mantém intacto:
  não mexer em estilo alheio, não apagar código morto pré-existente sem pedir, e limpar só o órfão
  que a própria mudança criou.

As outras duas seções reforçam o projeto. "Defina critério verificável e itere até verificar" é
literalmente o que os portões são: 69 comandos que reprovam de verdade, e nada sobe com portão
vermelho.

## §235 · O conserto do §228 estava certo no princípio e errado no byte · 26/09/2026

Classe **correção de fato**. Decisões tomadas por autorização da editoria em 26/09/2026, e um defeito meu do mesmo dia, encontrado ao executá-las.

**O defeito.** Quando o §228 unificou o cliente, dezoito chamadas passaram a mandar propósito **acentuado** no `User-Agent` — "verificação de links", "população IBGE", "execução das MPs". Cabeçalho HTTP é ASCII (RFC 7230 §3.2.4). Medido no mesmo dia: `defesacivil.es.gov.br` responde **HTTP 400 em 0,4 s** ao pedido com acento e **200 com o PDF** ao mesmo pedido sem ele. O acento agora sai por transliteração — "verificacao de links" —, e não o propósito, que quem lê o log da fonte entende igual. O portão do §228 passou a conferir o resultado de `ua_de` para **cada propósito literal do repositório**, e foi verificado ao contrário: tirar a transliteração o deixa vermelho em dezesseis chamadas.

**O que esse defeito quase me fez reportar.** A reverificação do banco dizia **75 links quebrados de 107**. Depois do conserto, e de o verificador passar a confirmar cada falha com o cliente que de fato coleta, o número verdadeiro é **1**. Setenta e dois daqueles "quebrados" eram defeito meu. Se o relatório tivesse ido para a editoria, ela teria agido sobre um erro meu — e o próprio módulo avisa, na docstring, que muito `.gov.br` recusa robô sem estar fora do ar.

O verificador ganhou duas classificações que faltavam, porque as três coisas são diferentes: **`BLOQUEADO`** (200 com muro de robô — recusa, não link morto), **`TLS_INCOMPLETO`** (o servidor não serve a cadeia completa; `pmsg.rj.gov.br` não é documento morto) e `QUEBRADO` para o que de fato não existe mais. E o caminho rápido do HEAD saiu: decidia pelo status **sem corpo para inspecionar**.

**A reserva de arquivo contornava o muro de robô.** Achado ao executar a preservação: um `MuroDeRobo` caía no `except Exception` de `buscar_com_procedencia` e a função devolvia "captura do Wayback" — dava a volta por fora num "não" explícito. Pior: antes de ler a captura, **pedia ao archive.org para salvar a URL**, empurrando o endereço do host a um terceiro logo depois de ser recusada por ele. O comentário de `RECUSAS_EXPLICITAS` já dizia a regra — a reserva é para a conexão que nem vira conversa HTTP, "em que não há recusa a respeitar porque não houve resposta". Faltava a linha que a faz valer.

**Decisão 1 — os cinco registros de Santa Catarina.** Bom Retiro, Guaramirim, Schroeder, Major Vieira e Timbó Grande citavam uma notícia da Defesa Civil estadual que nomeava seus decretos. Medido antes de decidir: a URL devolve **404** pelos dois clientes; a API do WordPress do próprio órgão lista **48 notícias de 02/07/2026 e nenhuma** nomeia decretos — a página foi **removida**, não movida; e o Wayback **não tem captura**. Os registros **ficam**: um humano os verificou contra fonte primária em 27/08/2026, e apagá-los apagaria um fato verificado — o teto do projeto é "não localizamos até o corte", nunca "não existe". O que sai é o **link**: oferecer 404 ao leitor é pior do que não oferecer link, e `url` nulo já é estado suportado em 110 dos 267 registros. O endereço morto fica em `url_indisponivel`, com data e motivo, para a próxima sessão não repetir a busca. Nenhum dos cinco pontua (`categoria=decreto`, peso zero): a nota nacional não se move.

**Decisão 2 — a camada de saúde estadual estava só como link.** O que eu havia listado como "um registro a revisar" eram **dezenove**: 19 das 27 UFs tinham documento e URL com `hash_evidencia` nulo — verificadas por pessoa, com data e log, e sem cópia guardada. Enquanto isso é verdade, o projeto não pode reverificar o que afirma, e documento que sai do ar leva a prova com ele. A rodada preservou **16 de 19**; as três restantes ficaram com o motivo medido no próprio registro: Paraíba (muro de robô), Paraná (HTTP 403) e Santa Catarina (404 direto **e** no arquivo — essa também perdeu o link, pela mesma regra dos cinco de SC).

**E um erro meu dentro dessa decisão, corrigido na mesma sessão.** A preservação gravou `hash_evidencia` nas dezesseis sem olhar **o que** tinha sido preservado. Cinco vieram em PDF — esses são o documento. Onze vieram em HTML porque a URL do registro **não aponta para o documento**: aponta para notícia (`piauihoje.com`, `rondoniagora.com`, `cnnbrasil.com.br`) ou para página de listagem do órgão. Guardar isso em `hash_evidencia`, com `procedencia_do_documento` ao lado, faz uma notícia parecer o plano preservado — pior do que não preservar. O que é documento ficou em `hash_evidencia`; o que é página citada ficou em `hash_pagina_citada`, com `evidencia_e` dizendo qual das duas coisas é. Nada foi apagado e nenhum status mudou: a correção é de nome, não de fato.

**O que isso revelou, e que NÃO é meu para decidir.** Piauí, Rondônia e São Paulo têm o registro estadual de saúde apoiado em **imprensa** — as URLs são de veículos jornalísticos. A regra **C10** do projeto (02/09/2026) rebaixou registros municipais nessa exata situação a pista, com errata pública, porque imprensa não é documento primário. Se C10 vale para a camada de saúde é decisão da editoria: ela toca o significado de um indicador, e a governança reserva isso a quem edita. Fica nomeado aqui, com as três UFs e as três URLs, para ser decidido e não esquecido.

**E o token do INMET não existe.** A editoria enviou o que supunha ser a chave: é uma página de notícia do próprio INMET que diz o contrário — *"os dados coletados pelo Inmet são públicos e podem ser acessados gratuitamente e, em tempo real"*. Seguindo os endereços que ela indica, a série histórica por estação — a única coisa que o token ainda serviria depois do §233 — está em **27 ZIPs anuais públicos** em `portal.inmet.gov.br/uploads/dadoshistoricos/`. Medido: o de 2026 tem **64 MB e 639 CSVs de estação**, de 01/01 a 31/08/2026, com máxima e mínima horárias, precipitação, umidade, radiação e vento, e metadados de estação em cada arquivo. Não há credencial a pedir, e o item sai da lista de ação humana. Construir coletor sobre essa série é escopo novo, e por isso não foi feito sem pedido.

## §234 · Três módulos que existiam e ninguém chamava · 26/09/2026

Classe **rotina de coleta**.

Um grep em `atualizar.py` e em todos os workflows encontrou três módulos que existem, têm autoteste próprio e **não eram invocados por nada** — nem no pipeline, nem na lista de autotestes do portão. Código que passa por revisão, entra no repositório e nunca roda é pior do que código ausente: ele dá a impressão de que o problema está resolvido.

**`coletar_espin.py`** foi escrito no §209 exatamente para resolver o que o próprio cabeçalho dele descreve: *"uma ESPIN declarada em novembro passaria despercebida até alguém procurar"*. Fora do pipeline, isso continuava sendo verdade — o `data/saude_sinais.json` mostrava `espin: "coletado"` como resultado de **uma execução manual única**. Entra na rotina diária; custa duas consultas ao DOU.

A rodada de 26/09 leu **26 resultados e nenhuma declaração**, e gravou `nenhuma_declaracao_localizada` com a janela (29/06 a 26/09), as duas strings buscadas e peso nenhum no índice. Isso é "procuramos e não há", que é resultado — diferente de "não procuramos". A fila de revisão humana não foi criada porque não havia nada a revisar, e não criar arquivo vazio é o comportamento certo.

**`coletar_siconfi_182.py`** está completo para o exercício de 2025 (5.571 municípios), também por execução manual. O próximo exercício da DCA não entraria sozinho. Entra na rotina com `--lote 300`: enquanto não houver pendente, a chamada é barata e não faz nada; quando o exercício virar, ele preenche em lotes por conta própria.

**`buscar_financiamento_preventivo.py`** é o caso diferente, e por isso **não** entra na rotina automatizada: ele é auxílio humano — imprime os quatro gabaritos de busca padronizados de uma UF para quem vai conduzir a sessão de verificação, e a regra de promoção a `ausente_verificado` exige os quatro executados e registrados. Automatizá-lo seria transformar a bateria numa varredura, que é o oposto do que ela é. Entra como **portão**, com `--check`, para que a estrutura de `data/financiamento_uf.json` e o vocabulário de status continuem válidos. O placar hoje: 1 UF `localizado`, 26 `nao_verificado` — e `nao_verificado` não é ausência, é ausência de verificação.

A suíte vai a **69 portões**.

## §233 · A fonte estava travada por uma chave que a rota dela não pede · 26/09/2026

Classe **correção de fato**.

A camada de MEDIÇÃO de temperatura estava vazia nas 27 capitais, e a página mostrava só a estimativa de modelo — justamente a distinção que o projeto declara manter. O motivo registrado era credencial ausente. **A rota que a fonte usa não pede credencial nenhuma.**

Medido em 26/09/2026: `https://apitempo.inmet.gov.br/estacoes/T` responde **HTTP 200 com 262.904 bytes e 673 estações, sem token**, e é tudo o que `parse_estacoes_inmet` consome. A fonte declarava `INMET_API_TOKEN`, e `coletar_fonte` levantava `CredencialAusente` **antes de tocar a rede**. A seleção de estação nunca rodou por falta de uma chave que ninguém pediu.

**Dois diagnósticos errados estavam escritos ao lado, e foram conferidos.** O comentário afirmava que sem token a rota de dados devolve "204 com corpo vazio" — devolve **404** (`/estacao/diaria/2026-09-24/2026-09-25/A001`). E o papel declarado prometia "máxima e mínima **medidas** na estação automática da capital", coisa que o adaptador não fazia: ele só escolhia a estação mais próxima de cada capital, e nunca leu temperatura alguma. Promessa no `papel` que o código não cumpre é pior do que lacuna declarada, porque ninguém vai procurar o que já parece entregue.

**A promessa passou a ser cumprida**, por uma rota pública que o repositório não usava em lugar nenhum: `/condicao/capitais/<data>` — 200, 28 registros, sem token, com máxima, mínima, umidade mínima e precipitação máxima por capital. A rodada de 26/09 gravou **22 estações de capital e 21 capitais com máxima e mínima medidas**.

**Três sutilezas da fonte que o leitor trata explicitamente, porque medi cada uma.**

- Os nomes vêm em maiúsculas e sem acento — **menos "MACEIÓ", que vem acentuado**. A fonte é inconsistente consigo mesma, e só normalizar os dois lados resolve.
- **Brasília aparece duas vezes** (28 registros para 27 capitais). Nos dados de 26/09 as duas linhas são idênticas e a duplicata é inofensiva; se algum dia divergirem, a capital é **recusada** — duas medições diferentes para o mesmo dia e o mesmo lugar não se resolvem escolhendo uma.
- **Seis das 28 linhas traziam `*` em vez de número.** Isso é "não divulgado", nunca zero, e a capital não entra. E quando o valor vem como `29.6*`, o número entra com a marca registrada como marca: **o que o asterisco significa não está declarado em nenhum lugar da resposta, e eu não vou afirmar.** Quem publicar o número publica a marca junto.

**Um registro que se contradizia.** O arquivo gravou, na mesma entrada, `status: "coletado"` **e** `motivo: "INMET_API_TOKEN ausente — camada de medição fica em lacuna declarada"`. A causa é `dict.update`, que mescla: o motivo de uma rodada anterior sobrevivia à coleta bem-sucedida. Registro que se contradiz é pior do que registro ausente — quem lesse o `motivo` concluiria o oposto do que a coleta fez. Fonte que voltou a coletar não carrega mais o motivo de quando não coletava, nem o campo de credencial que deixou de exigir.

**`normalizar_nome` subiu para `coletores_base`.** Ela vivia só no coletor de diários consorciados, e importar aquele módulo por causa dela traria o Playwright junto. Copiá-la seria a cópia que envelhece do §213 — numa função de **casar nome**, onde divergir significa um município casar num coletor e não casar no outro.

Nove travas novas, offline, incluindo as três sutilezas acima e a que impede o retorno do defeito: a lista de fontes que exigem credencial passou a ser **derivada** de quem declara credencial, em vez de escrita à mão. O teste antigo tinha `inmet_estacoes` fixo no código e **provava o defeito** — exigia que a fonte recusasse por falta de uma chave que a rota não pede.

**Para a editoria:** o token do INMET continua sendo ação humana (sem caminho público de cadastro; é pedido à Central de Serviços), mas **não é mais necessário** para catalogar a estação nem para a máxima e a mínima medidas das capitais. Ele serviria para a série histórica por estação, que é outra coisa.

## §232 · O muro que não dizia nada, e a permissão tirada de uma recusa · 26/09/2026

Classe **conformidade com a política de acesso**. É o §186 e o §187 pela terceira vez, e desta vez o detector estava cego.

**O que foi medido.** Em `paraiba.pb.gov.br`, `/`, a pasta de vigilância em saúde e **até o `/robots.txt`** devolvem a mesma página de 47 a 51 kB com **HTTP 200**: um desafio JavaScript do F5/Shape (BIG-IP ASM), cuja carga hexadecimal decodifica para *"Oops....something went wrong....your support id is: %DOSL7.challenge.support_id%"*. O host inteiro está atrás do muro.

**Por que passou.** `detectar_muro_de_robo` varre o **texto declarativo** da página — e essa regra foi conquistada no §182, quando casar em atributo de HTML marcou um portal inteiro como suspenso por causa de um `alt="banner periodo eleitoral"`. O desafio do F5 **não diz nada**: não há "pardon our interruption", não há "you have been blocked", é só JavaScript ofuscado. As duas coisas são verdadeiras ao mesmo tempo, e a saída não foi afrouxar a régua — foi distinguir as famílias. Marcas que vivem no **código** da página (`window["bobcmn"]`, `/TSPD/`, `TSPD_101`) passam a ser casadas no corpo cru, e só elas: são identificadores de produto, não palavras de língua, e nenhum documento público brasileiro as contém. Um texto que menciona "proteção TSPD" em prosa continua não casando.

**O efeito pior não era falhar — era concluir.** `robots_de()` leu os 51 kB de desafio como se fossem um `robots.txt` e concluiu **"permite"**: tirou permissão de uma recusa e registrou isso como o que o sítio declara. Agora muro no lugar do robots é **"indeterminado"** — o sítio não declarou regra nenhuma, ele não deixou ler a declaração.

**A recusa da Paraíba ganhou o nome certo.** O coletor de boletins da PB chamava a página de "página de espera do Plone" e de "interstício (cookie)", e procurava dentro dela um destino que não existe — porque não há destino, há desafio. O log registrava *"nenhum boletim nº 01–6 de 2026 respondeu com PDF"*. Agora registra *"bloqueio de acesso do host: muro de robô … desafio de robô no código da página"*, e **para de tentar os seis números** contra um muro que cobre o host inteiro. Nomear a recusa errado é o erro que custou treze dias de abstenção indevida no §187; aqui custava uma lacuna com o nome de outra coisa.

**E a conferência de links dizia "OK" sobre documento que ninguém abre.** `verificar_links.py` classificava por status: 200 → OK. Um host que serve muro com 200 aparecia como link vivo e conferido — e `data/saude_uf.json` guarda um plano da PB apontando exatamente para lá, com `hash_evidencia` nulo. A conferência de links existe para achar o que morreu; ela estava dizendo que estava vivo.

Entrou a classificação **`BLOQUEADO`**, contada à parte: não é link morto e não é link conferido, é recusa. E o **caminho rápido do HEAD saiu**: ele decidia pelo status **sem corpo para inspecionar**, e um host que serve muro com 200 responde 200 ao HEAD também. Quem mostrou isso foi o autoteste desta própria função, escrito antes da correção — com o muro injetado, ela classificava OK. Agora a leitura é um GET por link, com **leitura parcial de 60 kB** (o mesmo teto do detector): um PDF de dez megabytes não é baixado inteiro para se saber que o link está de pé.

Seis travas novas, todas offline: o desafio sem texto declarativo **é** recusa; prosa que só cita o produto **não** é; muro no lugar do robots não vira permissão; e o verificador de links classifica `BLOQUEADO` e o relatório conta a recusa à parte sem chamá-la de quebrado.

**O que fica para a editoria.** O desafio JavaScript **não se resolve**: é recusa e se respeita. Os boletins de arboviroses da Paraíba — as 16 Regiões de Saúde, o melhor formato tabular depois do Mato Grosso do Sul — seguem inacessíveis por via automatizada. O caminho que resta é pedido pela LAI ou contato institucional com a SES-PB. E há um registro a revisar: o plano da PB em `data/saude_uf.json` foi verificado por pessoa em 05/09 e **nunca preservado** (`hash_evidencia` nulo); hoje aquele endereço está atrás do muro.

## §231 · O primeiro diário oficial ESTADUAL que o Monitor leu · 26/09/2026

Classe **cobertura de coleta**. Em quase dois meses de operação, o projeto nunca havia lido um diário oficial de estado: as 27 UFs de `data/fontes_doe.json` estavam com adaptador nulo, e o §194 já tinha medido que o Querido Diário **não indexa** diário estadual — os territórios de dois dígitos devolvem zero. O único adaptador implementado era justamente o que não podia funcionar.

**Cinco estados passaram a ser lidos, e um sexto tem caminho declarado.** AP, ES, GO, MT e PR rodam o mesmo sistema, com três rotas públicas sem autenticação. Tudo abaixo foi medido contra produção, nada suposto:

- `/apifront/portal/edicoes/edicoes_from_data/AAAA-MM-DD.json` — as edições do dia. Quando não há edição, responde `{"erro": true, "msg": "Edição não existente!"}`, que é resposta **correta** e não falha.
- `/busca/busca/buscar/query/<pagina>/di:…/df:…/?q="termo"` — resposta Elasticsearch crua com `hits.total` e, por acerto, **`_source.conteudo` = o texto integral da página que casou**, mais data, página, total de páginas e os identificadores. É essa rota que torna a coleta viável: não se baixa um PDF de dez megabytes por acerto para depois procurar dentro dele.
- `/portal/edicoes/download/<diario_id>` — o PDF da edição, para citação e conferência humana.

**Duas medições que custaram a primeira sonda, e que ficam registradas para ninguém repetir.** A página da busca é indexada em **zero** e entrega dez por vez: pedir `/query/1/` numa UF com menos de dez acertos devolve `hits.total = 7` com `hits.hits = []` — total declarado, lista vazia. Foi exatamente isso que fez GO, ES, AP e MT parecerem sem resultado na primeira tentativa, e é um engano que se parece com ausência de dado. E o identificador do download é `diario_id`, não `pdf_id`: o segundo devolve 28 kB de HTML, o primeiro devolve o PDF de verdade.

**O termo de busca nunca podia casar.** O primeiro termo da lista era `"homologa a situação de emergência"`, com um artigo que o ato estadual real não tem — medido no DOE-PR de 15/09/2026: *"Homologa situação de emergência no Município de Palmeira"*. Termo que não pode casar é pior do que termo ausente: produz "nada localizado" com aparência de busca feita.

**E o padrão de extração também não podia.** O antigo exigia "município de X" na mesma frase do número do decreto. As duas formas reais, lidas no documento, são outras: *"Homologa o Decreto Municipal nº 235, de 15 de setembro de 2026, exarado pelo Prefeito de Boa Vista da Aparecida"* e *"Homologa situação de emergência no Município de Palmeira"*.

**Um defeito que a primeira varredura real revelou, e que só ela revelaria.** O ato estadual diz a mesma coisa **duas vezes** — a ementa, sem o número do decreto municipal, e o dispositivo, com ele. Contar as duas produziu 54 atos registrados **e 54 pistas dos mesmos municípios**, com o motivo "sem número do decreto": fila de revisão humana cheia de trabalho já feito. A chave passou a ser o município, e entre duas leituras do mesmo ato fica a que traz o número. As pistas caíram de 58 para **7** — e essas sete são legítimas, de atos que aparecem só na forma da ementa.

**O que entrou.** **54 homologações estaduais de decretos municipais de emergência**, todas do Paraná, cada uma com município casado ao código IBGE, número do decreto municipal, data, a URL do PDF da edição e **o número da página** — a diferença entre "está nesta edição de 104 páginas" e "está na página 11". Em 49 delas entrou também o número do decreto **estadual** que homologou. E **881 municípios** passaram a ter consulta a diário estadual registrada no livro de fontes: PR 399, GO 246, MT 142, ES 78, AP 16.

Um registro foi conferido contra a fonte por desconfiança legítima: Ivaiporã aparece com "Decreto municipal nº 15.450", numeração que parece de decreto estadual. O documento diz exatamente isso — *"Decreto Municipal nº 15.450, de 21 de setembro de 2026, exarado pelo Prefeito de Ivaiporã"*. A extração está certa; o município numera assim.

**O Amazonas fica fora, e por decisão.** Ele roda a mesma plataforma — as rotas de edição e de download respondem —, mas a de **busca devolve 404**: a busca dele é outro aplicativo. Registrá-lo como `apifront` produziria doze lacunas falsas por dia, sobre um fato que não muda. Ele vive em `APIFRONT_SEM_BUSCA`, com o que foi medido e o caminho que resta: varrer as edições por data e ler o PDF de cada uma. É trabalho a fazer, não fonte bloqueada, e a distinção importa.

Treze autotestes offline travam o adaptador, incluindo os dois enganos acima: **total declarado com lista vazia LEVANTA** (§210 outra vez) e uma página que menciona "situação de emergência" em regra administrativa — a do IAT no DOE-PR de 01/07/2026 — **não** casa nenhum padrão e corretamente não produz registro.

## §230 · Cento e trinta e sete barreiras medidas, e as primeiras derrubadas · 26/09/2026

Classe **desbloqueio de coleta**.

A editoria mandou parar de publicar lacuna e passar a resolver: *"sempre que voce encontrar uma barreira, voce deve aplicar todas as solucoes que voce conhece para solucionar, e só me retornar com pedidos que realmente dependam de acao humana"*. O primeiro passo foi levantar o inventário de verdade, com seis varreduras de lentes diferentes — catálogos de fontes, código, log de buscas, cobertura municipal, diários estaduais, saúde e risco. Resultado: **137 barreiras distintas**, 62 de gravidade alta, cada uma com sintoma medido e não suposto.

O levantamento consumiu o teto semanal de agentes, e a fase de resolução automática parou. As correções abaixo foram feitas à mão, a partir do inventário.

**1. `buscar()` não descomprimia gzip, e ninguém sabia.** Medido: `diariooficial.to.gov.br` responde `Content-Encoding: gzip` **mesmo sem o pedido negociar compressão**. O cliente devolvia 2.966 bytes de gzip cru que, descomprimidos, são 16.386 bytes de HTML. É a família do §186 e do §187 — resposta com 200 que parece conteúdo e não é — com um agravante: `detectar_muro_de_robo` e `detectar_defeso` passavam a olhar ruído binário, e `preservar_evidencia` gravaria o blob comprimido com extensão `.html`. Depois do conserto, o Tocantins entrega os 16.389 bytes de HTML real. A função confere a marca do formato além do cabeçalho: servidor que declara gzip e manda texto existe, e descomprimir às cegas quebraria o que hoje chega bom.

**2. Noventa e sete decretos parados por dois defeitos nossos, um deles com o rótulo errado.** `analisar_decretos.py` roda todo dia no ciclo e não produzia um único marcador de conteúdo. Duas causas:

- O endereço do Querido Diário era `api.queridodiario.ok.org.br`, que **não serve mais TLS** (`SSLV3_ALERT_HANDSHAKE_FAILURE`, medido hoje). O resto do projeto migrou para o host vigente em 21/09; este arquivo ficou atrás, e a fila registrava 59 dos 97 itens como `erro_rede: SSLV3_...`. Agora o endereço não é copiado: usa-se o consultor de `coletar_diarios_municipais`, que já traz host vigente, domínio de reserva e a espera do §226.
- **Um defeito de Python**: `for g in gazettes` e, dentro do laço, `a, p, g, rf = _varrer(ex)` — a gazeta era sobrescrita pela lista de termos, e duas linhas abaixo `g.get("date")` era chamado sobre uma lista. `AttributeError` em todo excerto com achado. E o `except Exception` único gravava isso como **`erro_rede`**: defeito nosso lançado na conta da fonte, que é precisamente o que o CLAUDE.md proíbe. Agora erro de rede e erro interno têm nomes distintos, e quem lê a fila sabe de quem é a culpa.

A docstring também prometia tentar "(a) a URL do registro; (b) o Querido Diário". A perna (a) nunca existiu no código. Prometer o que não se faz é pior do que declarar a lacuna, e a promessa saiu.

**3. O informe de Pernambuco voltou a ser legível — dois terços dele.** A listagem do CIEVS-PE responde 200 e traz o informe da SE 36 em PDF de 4 MB, íntegro. O que travava era o nosso leitor: em 24/09 a fonte passou a compor os cartões do topo com os três valores numa linha e os três rótulos na seguinte, e a regra de adjacência não alcança esse arranjo — antes de "Casos descartados" vem "Casos prováveis", não um número. O pareamento agora aceita a linha de cima, **condicionado** a haver tantos números quanto rótulos, e quem decide continua sendo a identidade contábil que já existia: só vale a combinação em que notificados = prováveis + descartados. Nos números reais fecha: 47.418 = 22.900 + 24.518.

Dengue e chikungunya passaram a ser lidos. **Zika não, e fica declarado.** Na página dele os rótulos vêm entrelaçados em duas linhas ("Casos … Casos / Casos confirmados + descartados confirmados") e a identidade contábil **não desempata** prováveis de descartados, porque a soma é comutativa: `1.235 = 118 + 1.117` fecha nas duas ordens. Ler por posição de coluna exigiria as coordenadas do PDF, e adivinhar trocaria dois números numa página pública. Na dúvida, o classificador não classifica.

**4. Correções menores encontradas ao medir.** `analisar_decretos.py` gravava a fila com `json.dump(open(...))` — escapou do portão do §229 porque as duas chamadas estavam em linhas diferentes. O portão foi reescrito para ler por **árvore sintática** em vez de por linha, e achou **mais nove**: o cursor de rodízio de três monitores (truncá-lo faz a próxima rodada recomeçar do zero), as duas filas do `consultar_querido_diario`, o PIB per capita das 27 UFs e a fila de contribuições. Todas migraram, e as datas em UTC que apareceram no caminho foram com elas.

**Inventário para a editoria: o que ficou, e por quê.** Das 137 barreiras, as de maior volume seguem abertas com diagnóstico medido e caminho conhecido:

- **Seis diários oficiais estaduais colhíveis hoje** (AP, AM, ES, GO, MT, PR — 943 municípios): rodam a mesma plataforma, com três rotas públicas sem autenticação já testadas ao vivo. Falta escrever o adaptador. É o maior ganho pendente.
- **As 27 UFs de `fontes_doe.json` com adaptador nulo**, mais sete defeitos de código no caminho direto do `coletar_doe.py` — teto de 20 kB num documento de 510 mil caracteres, não lê PDF, ignora a janela de data, termo de busca com um artigo a mais que o decreto real não tem.
- **InfoGripe**: o repositório da Fiocruz passou a responder 200 com tela de login do GitLab. Bloqueio de acesso real, que se respeita.
- **Dezoito UFs sem fonte de boletim de arboviroses localizada**, nunca procuradas.
- **SES-PB**: a recusa está **nomeada errado** no código — é muro de robô F5 servido com 200, não "PDF não respondeu". Corrigir o nome é pré-requisito para tratar o caso.
- **Três coletores órfãos** (`coletar_espin.py`, `coletar_siconfi_182.py`, `buscar_financiamento_preventivo.py`): existem, têm autoteste, e não são invocados por nada.
- **`inmet_estacoes`** está travada por uma credencial que a rota usada por ela **não exige**.

## §229 · A escrita atômica de 21/09 nunca saiu de uma função · 26/09/2026

Classe **integridade de dado**.

Em 21/09/2026 um processo interrompido no meio de uma gravação deixou `data/fontes_consultadas.json` truncado — 368.019 linhas viraram 166.961, JSON inválido. A correção entrou em `coletores_base.gravar()`: temporário ao lado, `os.replace()` no fim. Cinco dias depois, uma auditoria contou **trinta e três escritas de JSON direto no destino** espalhadas pelo projeto, todas fora daquela porta.

**O que estava exposto, em ordem de dor.** `data/historico_mudancas.json` e `data/log_buscas.json` — os **dois arquivos append-only** do projeto, aqueles que a regra de merge por base comum existe para proteger. Truncar um deles é o pior caso possível, porque o que se perde não aparece em nenhum lugar: o próprio registro do que existiu é ele. `data/municipios.json`, o banco, gravado direto por **quatro portas diferentes** (`processar_contribuicoes.py`, `verificar_vigencia.py`, `julgar_e_aplicar_descobertas.py` e `aplicar_c10_imprensa.py`), três delas no ciclo diário. `data/indice.json`, que é o produto — um JSON truncado ali é o site inteiro sem número. E mais `atos_resposta.json`, `estados.json`, `prazos_uf.json`, `meta.json`, as quatro filas de revisão humana e o histórico de recorrência por UF.

**Por que ficaram de fora, e a lição de projeto.** Não foi descuido: `gravar()` pedia o **nome relativo a `data/`**, e quem já tinha o caminho montado — a maioria — achava mais curto abrir o arquivo. O atrito da interface era o motivo. Daí `gravar_em(caminho, obj)`, que aceita o caminho pronto: a migração passou a ser local e mecânica, e as trinta e três chamadas entraram.

**Um erro meu no caminho, que vale registrar porque é instrutivo.** A primeira tentativa de migração usou expressão regular multilinha e comeu um `with open(...) as f: json.dump(resumo, f)` em `recalcular_mare.py`, deixando `json.dump(novo)` — **sintaticamente válido, e que não grava nada**. O arquivo compilava. Se tivesse passado, o `indice.json` deixaria de ser regravado silenciosamente. Transformação automática que compila não é transformação correta: a segunda passada exigiu o casamento da linha inteira, e nada foi gravado sem `ast.parse` antes.

**O portão** é uma trava nova em `scripts/testar_escrita_atomica.py`: nenhuma escrita de JSON fora de `gravar`/`gravar_em`, com uma lista curta de exceções **com motivo declarado** — a própria porta, o gerador que escreve no repositório privado da editoria, os três derivados que o portão 12 confere byte a byte, e o arquivo de teste que escreve fixture. Crescer nessa lista é decisão, não descuido. Verificado nos dois sentidos: reintroduzir uma escrita direta em `municipios.json` deixa o portão vermelho.

## §228 · Vinte e uma identidades, seis delas disfarçadas · 26/09/2026

Classe **conformidade com a política de acesso**. Achado de auditoria, e o mais grave da sessão: não é robustez, é uma regra do `CLAUDE.md` sendo violada por código em produção.

**O que foi medido.** O repositório enviava **vinte e uma strings de `User-Agent` diferentes**, uma por arquivo. Seis começavam com o token de navegador; **duas eram o agente completo de um Chrome no Windows**. Entre os seis, `julgar_e_aplicar_descobertas.py` e `seguir_pistas.py`, que rodam no ciclo.

**Por que isso não é detalhe técnico.** O `CLAUDE.md` diz, sem exceção: *nunca disfarçar o cliente*. Trazer o nome do projeto entre parênteses não desfaz o disfarce — o primeiro token é uma identidade de navegador, e a razão pela qual alguém escreve `Mozilla/5.0` é passar por filtro que recusa robô, o que é contornar recusa. É a mesma família do §186 e do §187: nomear a recusa errado, ou fazer com que ela não aconteça, produz prova obtida por um caminho que o projeto declarou não usar.

Dois casos vinham com a decisão escrita no próprio código, e é isso que os torna instrutivos:

- `verificar_links.py` **justificava** o agente em formato de navegador na docstring: muitos `.gov.br` devolviam 403 a HEAD com agente de robô e 200 a GET com agente de navegador. A observação trocava **duas variáveis ao mesmo tempo** — o método e a identidade — e atribuía o ganho às duas. Só a primeira metade fica: tentar GET onde HEAD não é implementado é usar o protocolo. Trocar a identidade é contornar recusa. Se um portal recusa o Monitor identificado, a recusa **é** o resultado da verificação.
- `scripts/diagnostico_fontes_saude.py` pedia cada alvo **duas vezes**, uma com cada identidade, "para separar bloqueio por IP de bloqueio por agente". A intenção de diagnóstico é boa; o meio não é. E a resposta não mudaria conduta nenhuma: diante de bloqueio por agente o projeto respeita e declara a lacuna, igual ao bloqueio por IP. Saber que o sítio entregaria o documento a um navegador só serviria para tentar passar por um.

**O segundo defeito, no mesmo lugar: a cópia que envelhece.** É o §213 e o §222 outra vez. Mudar o endereço de contato no `UA` canônico de `coletores_base` não mudava nada nos outros vinte arquivos. E aqui a cópia tem consequência direta: a política de robots (§185) avalia `can_fetch` contra `UA` e grava o cliente no rastro de `data/robots_registro.json`. **Módulo que enviava outra string era medido contra a regra de um agente e registrado como outro.**

**O conserto.** Um `ua_de(proposito)` em `coletores_base`: mesma identidade, propósito declarado entre colchetes. Distinguir uma sonda de um coletor nos registros da fonte é objetivo legítimo, e é o que a função serve — quem recebe o pedido continua sabendo quem somos, e passa a saber por que estamos ali. As vinte e uma strings viraram uma, em **vinte e três arquivos**.

**Três pedidos não identificavam cliente nenhum.** `atualizar_recursos.py` pedia o SIDRA do IBGE com o agente padrão da biblioteca. `atualizar_marcos_severidade.py`, o mesmo. E `atualizar_transferencias.py` levava a **chave de API** no cabeçalho e não levava o cliente: um pedido autenticado de agente anônimo. Os dois últimos só apareceram porque o portão novo foi ampliado para ler também as chamadas via `requests`, e o terceiro porque o portão os leu por AST em vez de por `grep`.

**O portão** (`scripts/verificar_cliente_identificado.py`, 66º da suíte) confere quatro coisas: nenhum valor de `User-Agent` é string literal fora de `coletores_base`; nenhuma string **de código** traz token de navegador; o `UA` canônico começa com o nome do projeto; e todo módulo que faz pedido cru identifica o cliente. A leitura é por AST de propósito, para que docstring e comentário possam contar esta história sem reprovar o portão. Verificado nos dois sentidos: reintroduzir um disfarce o deixa vermelho.

**E um furo de cobertura, encontrado ao medir isto.** `scripts/verificar_autotestes_isolados.py` roda **todos** os autotestes do projeto e, até aqui, imprimia os vermelhos e devolvia **zero**, com a nota "reportado pelos portões próprios". Medição: dos trinta e tantos módulos com autoteste, **vinte e um não têm portão próprio** — entre eles `coletar_espin`, `coletar_sinais_risco`, `coletar_dda`, `coletar_transferegov` e os quatro boletins estaduais. Para esses, autoteste vermelho aparecia no log e nada reprovava. Como este é o único portão que os alcança todos, autoteste vermelho passou a ser portão vermelho. Todos os trinta e tantos estavam verdes quando a trava entrou — a mudança não esconde dívida.

**Para a editoria, com franqueza:** parte da coleta feita até hoje por `verificar_links.py`, `seguir_pistas.py`, `julgar_e_aplicar_descobertas.py` e as duas sondas de diagnóstico saiu com o cliente em formato de navegador. O código está corrigido; o que já entrou no banco por esse caminho é pergunta editorial, não técnica, e fica registrada aqui.

A suíte vai a **66 portões**.

## §227 · A data de todos os coletores vinha do runner, e a reserva de arquivo nunca foi usada onde mais fazia falta · 26/09/2026

Classe **correção de fato**.

Três achados de uma auditoria dos dezesseis coletores, todos da mesma família do §226: uma regra certa, escrita num lugar, que não alcançava a porta por onde todo mundo passa.

**1. O `hoje()` compartilhado datava em UTC.** O projeto tem `hoje_editorial()`, que converte para o fuso da redação, e tem um portão que exige seu uso — os dois viviam em `atualizar.py`, e o portão conferia `atualizar.py`. Enquanto isso, o `hoje()` de `coletores_base.py` — chamado pelos dezesseis coletores, **vinte e nove vezes só nos `coletar_*.py`** — devolvia `date.today()`: a data do runner, que roda em UTC. A rodada de sábado 22h40 em Brasília já é domingo em UTC, e o carimbo `consultado_em` de cada fonte saía datado de um dia que no Brasil ainda não tinha começado.

O fuso e a função sobem para `coletores_base`, e `atualizar.py` passa a importá-los em vez de mantê-los. O portão de cadência foi ampliado para cobrir o helper compartilhado, e a prova usa **relógio injetado**, não o de agora: 27/09/2026 01h30 UTC é 26/09 22h30 em Brasília. Um teste sem relógio falso só pegaria a regressão nas três horas do dia em que os dois fusos discordam — ou seja, quase nunca, que é exatamente como o defeito durou. A trava foi verificada revertendo o código de propósito: o portão reprova.

**1-bis. E as outras setenta e cinco.** Consertar o `hoje()` compartilhado não bastava: uma contagem no mesmo dia encontrou **75 chamadas diretas a `date.today()` em 41 arquivos da raiz**, contornando o helper. Vinte e duas delas gravavam data **dentro de `data/`** — `registrado_em`, `consultado_em`, `coletado_em`, `atualizado_em`, `gerado_em`, `ocr_em`, `decidido_em` —, que é exatamente o que o leitor lê como "quando isto foi visto". Todas migraram para `hoje_editorial()`, uma troca de tipo idêntico (as duas devolvem `date`), e o portão de cadência passou a proibir `date.today()` na raiz inteira, não só no `atualizar.py`. A trava vale para todos porque o defeito nunca esteve num arquivo: esteve na ausência de um lugar único.

**E um erro meu na migração, registrado porque a lição é sobre o limite dos autotestes.** A troca deixou o prefixo em nove arquivos que escreviam `_dt.date.today()` com `import datetime as _dt`, produzindo `_dt.hoje_editorial()` — atributo que não existe. O código **compilava**, e **todos os trinta e tantos autotestes passaram**: os nove estavam no ramo `except` de um `_hoje()` que só é alcançado quando o `meta.json` não pode ser lido. Quem mostrou foi o portão de consistência, rodando o pipeline de verdade. `compileall` vê sintaxe; nome resolvido dentro de função só aparece na execução, e execução só acontece no caminho que alguém percorre.

A primeira trava que escrevi para isso tentava **chamar** cada `_hoje()`. Verifiquei, e ela não pegava nada — pelo mesmo motivo que os autotestes não pegaram: o ramo quebrado não está no caminho feliz. A trava que ficou é estática e diz o que importa: `hoje_editorial` se chama pelo nome, e só `coletores_base` pode prefixá-lo. Essa, testada nos dois sentidos, reprova.

Duas coisas a mais apareceram nessa passagem. `coletores_base.registrar_fonte_suspensa` — que grava `primeira_deteccao` e `ultima_deteccao` de uma fonte em defeso, datas de que um prazo legal depende — datava pelo runner **e** escrevia direto no destino, sem a escrita atômica de 21/09. As duas foram corrigidas.

**2. A reserva de arquivo existia e não era usada onde mais fazia falta.** `preservar_evidencias.py` — o coletor que lê os PDFs de plano de contingência — chamava `buscar()` direto. Em 24/09, **105 leituras de PDF** falharam com `URLError` num único dia, nos sítios de defesa civil de Sergipe e do Amazonas. Testados em 26/09, sem nenhuma mudança de código, os três documentos da amostra responderam na hora: 5,8 MB, 642 kB e 7,7 MB de PDF válido. Não era fonte fora do ar — era uma tarde ruim de rede tratada como ausência de documento.

Documento que existe e que o sítio momentaneamente não entrega é precisamente o caso da reserva do Wayback, no projeto desde 12/09. O coletor passa a usar `buscar_com_procedencia`, que a usa **dizendo por onde o conteúdo veio** — obrigatório aqui, porque plano lido no sítio do órgão e plano lido numa captura provam coisas diferentes. A procedência vai ao banco de evidências e, quando não é a fonte direta, ao log. A reserva **não** se aplica a recusa explícita (401, 402, 403, 429, 451): ali a fonte disse não, e não se dá a volta por fora.

O `buscar()` compartilhado também passa a repetir erro de conexão — reset, TLS incompleto, DNS mudo, tempo esgotado. **Uma** repetição curta, e não duas como no 5xx, por uma razão de custo: host realmente fora do ar paga a espera em cada url de uma varredura, e uma varredura tem milhares. Cinco segundos por url morta é aceitável; vinte, não.

**3. A lacuna guardava a classe da exceção, não o motivo.** As 128 falhas de leitura de PDF foram escritas apenas como `URLError`, sem dizer se foi DNS, TLS, reset ou tempo esgotado — e sem isso não havia como distinguir fonte caída de rede tropeçada, que é a distinção que decide se vale insistir. Agora a lacuna guarda a mensagem.

**Uma correção ao diagnóstico anterior, para o registro.** As outras 71 falhas de leitura de PDF vinham com `UnicodeEncodeError`, e à primeira vista pareciam um defeito aberto do nosso cliente. São **todas de 07/09/2026**, véspera do conserto do `url_ascii` (08/09): estão fechadas há dezenove dias. O `url_ascii` foi reconferido contra a URL real do repositório do Espírito Santo, com `Contingência` cru misturado a `%C3%81` já codificado, e preserva o escape existente sem duplicá-lo.

A suíte segue em 65 portões; dois deles ganharam travas novas.

## §226 · A lição dos 63 municípios estava aplicada em um coletor de dezesseis · 26/09/2026

Classe **robustez de coleta**.

Em 25/09 uma varredura nacional mediu o que ninguém tinha medido: **63 dos 505 primeiros municípios** viraram lacuna declarada por `HTTP 503 Service Unavailable` — 12 %, e nenhum deles bloqueio de acesso. Indisponibilidade temporária é a fonte dizendo "tente mais tarde", e a resposta certa a isso é tentar mais tarde. A correção foi escrita no mesmo dia, com as esperas certas e o cuidado certo — **e ficou dentro de `coletar_diarios_municipais.py`**.

Os outros quinze coletores continuaram chamando `buscar()` direto e desistindo na primeira tentativa. É o defeito de escopo do §213 (o vocabulário do log em três arquivos) e do §222 (os canais em dois), agora numa regra de rede em vez de num vocabulário: a lição aprendida num lugar não alcança os outros quinze porque ninguém a moveu para onde ela vale.

**A política sobe para `coletores_base`, e `buscar()` passa a aplicá-la.** Dezesseis coletores ganham a espera sem que uma única linha de chamada mude em nenhum deles — a correção entra pela porta por onde todos já pedem rede. Quem mocka `buscar` num autoteste continua funcionando, porque o mock substitui a função inteira. A tentativa única segue disponível como `buscar_uma_vez`, para sonda e diagnóstico que precisam do status cru sem gastar repetições.

**As duas metades da regra são igualmente travadas.** Repetir onde repetir ajuda — 429 e 5xx. E **nunca repetir onde a fonte disse não**: 401, 403 e 451 sobem na primeira tentativa, sem espera, porque bloqueio de acesso real se respeita, sempre; muro de robô servido com 200 (§186) também não repete, porque ali não houve erro, houve recusa. Um portão novo (`scripts/testar_espera_de_rede.py`, dez travas, sem rede) existe sobretudo para a segunda metade: uma política de repetição escrita sem cuidado vira insistência contra quem recusou.

**O coletor de transferências do Portal da Transparência era o único do pipeline que pedia rede sem passar por aqui** — `requests` direto, sem espera, sem escrita atômica e sem autoteste. Três defeitos, todos da mesma família, corrigidos juntos:

- **Erro transitório virava ausência de repasse.** Qualquer código fora de 200 e 429 imprimia um aviso e abandonava o município. Hoje mesmo o endpoint de convênios devolveu `HTTP 504` na sonda de credenciais — gateway, não recusa — e, com o código antigo, aquele município entraria no arquivo como "nada encontrado". Zero e ausência de dado são coisas distintas, e a função confundia as duas.
- **O 429 repetia para sempre**: `continue` sem consumir tentativa, laço infinito diante de um limite de taxa persistente.
- **Desistir era silencioso.** Um `print` não é rastro: não entra no log de buscas nem na contagem de lacunas. Agora desistir **declara** a lacuna, com o código HTTP e o município.

O coletor ganhou autoteste (cinco travas) e portão, e seus dois arquivos passaram a escrita atômica — eles escreviam direto no destino, e este é o script que roda depois de milhares de requisições, que é exatamente quando uma Action é cancelada por tempo.

**Dois testes antigos foram reescritos.** `scripts/testar_robots.py` provava a política do §185 lendo o **texto-fonte** da função `buscar` com `ast`. Quando `buscar` passou a envolver `buscar_uma_vez`, os dois reprovaram sem que nada tivesse quebrado — terceiro caso do mesmo padrão nesta base. Agora provam comportamento: com a rede falsa, o muro **levanta**, o robots é consultado, o relógio do host é marcado e o acesso contra o robots deixa rastro com o cliente identificado.

A suíte vai a **65 portões**.

## §225 · O canal consorciado ia de sete estados a quinze, e a lista estava a um `<select>` de distância · 26/09/2026

Classe **cobertura de coleta**.

O coletor de diários consorciados dizia, no próprio cabeçalho, que descobrir o slug de cada estado na plataforma SIGPub "exige abrir o site e ler o link real, tarefa ainda não feita para os estados ausentes daqui". Eram sete UFs. A tarefa foi feita, e o resultado são **quinze**.

**Por que a lista estava incompleta.** O seletor de estados da página inicial da plataforma usa caminhos **relativos** (`/aam/`, `/famep/`), não URLs absolutas. Uma varredura por `href="https://www.diariomunicipal.com.br/<slug>"` — o jeito natural de procurar — acha parte das entidades e perde as outras. A lista autoritativa é o `<select>`: 21 UFs mais duas prefeituras avulsas.

**Nove UFs novas, cada uma com prova.** PE, AM, PA, RO, RJ, SP, RR, PB e AL entraram depois de o nome da entidade ser lido na própria página e o calendário ser testado com token real em 24 e 25/09/2026. O comentário de cada linha registra quantas edições a fonte devolveu nesses dois dias: é prova de que o canal entrega, não promessa de que deveria. Slug inventado não dá 404 — a plataforma devolve a própria página inicial, 90.958 bytes sem `calendar__token`, e foi assim que vinte e nove palpites de sigla se descartaram numa rodada, sem nenhum entrar no código.

**O que a varredura retroativa colheu.** Doze UFs varridas de 01 a 26/09/2026 — as nove novas mais Paraná, Rio Grande do Sul e Rio Grande do Norte, que estavam declaradas pendentes no §223. **333 dias com edição lidos, zero erro de fonte, 124 pistas e 71 atos municipais.** O banco de atos saiu de 7 registros do canal consorciado, todos de Minas, para **71 em nove estados**: PR 19, RS 17, AM 11, MG 7, AL 5, RN 5, PB 4, RR 2, PE 1. O Paraná respondeu por 77 das 124 pistas. Pará, São Paulo e Rio de Janeiro leram 78 edições somadas e não produziram ato — leitura feita, ausência declarada, que é resultado e não falha.

Cada registro traz município, código IBGE, número do decreto, a URL do PDF de origem e o hash da evidência. O canal é `DOM-consorciado`, distinto de `DOM` de propósito: a atribuição do município é heurística de proximidade no PDF consorciado, e quem lê o dado precisa saber disso.

**A correção de um rótulo errado, que é o achado mais importante daqui.** Em 25/09 os dois slugs da Bahia foram declarados "fonte fora do ar" porque respondiam ao calendário com `{"error":"Ocorreu um erro inesperado!"}` em toda data testada. O rótulo estava errado. A última edição de cada uma dessas entidades, lida na página, é de **2013** (AMURC), **2015** (AMM-MT), **2020** (APPM, Piauí), **2020** (MS) e **2009** (AMURCES, Sergipe): são **arquivos históricos** de associações que saíram da plataforma, e o `error` nas datas recentes é resposta correta — não há edição naquele dia porque não há mais edição nenhuma. Fonte fora do ar é falha; publicação encerrada é fato. Confundir as duas é do mesmo tipo que chamar geobloqueio de `robots.txt`, erro que já custou treze dias de abstenção indevida (§187).

As cinco passam a viver em `SIGPUB_ENCERRADO`, com a data da última edição declarada, fora do varrimento ativo — e cada linha delas passa a ser o que realmente é: uma UF cujo diário **corrente** está em outro lugar. Isso é lacuna de descoberta, trabalho a fazer, e não bloqueio de acesso, que seria trabalho impossível.

**O que a plataforma não cobre.** `/ma/` está no seletor dela e cai na própria página inicial: link morto do lado da fonte. AC, AP, ES, SC e TO não aparecem no seletor. As seis ficam em `SIGPUB_SEM_CANAL`, com o motivo observado — não o suposto.

Um autoteste novo (o vigésimo do coletor) exige que as 27 UFs estejam **todas** classificadas, que nenhuma esteja em duas gavetas ao mesmo tempo e que nenhum slug de arquivo histórico volte ao varrimento ativo. O DF é a única ausência legítima: não tem município. A lista saltou de sete para quinze numa rodada, e o modo de errar é sempre o mesmo — uma UF nova entra e ninguém a tira da gaveta antiga, e então o varrimento declara lacuna diária de uma fonte que entrega.

**Credenciais.** A sonda do §224 respondeu: a chave do **OpenAQ é aceita** (HTTP 200). A do Portal da Transparência está presente e o endpoint devolveu **504** — erro da fonte, não recusa de chave, distinção que importa porque o 403 das rodadas anteriores era recusa de verdade. O token do INMET segue **ausente**, sem caminho público de cadastro: é pedido à Central de Serviços, e é ação humana.

## §223 · O canal destravado entra na rotina, com a janela certa · 25/09/2026

Classe **rotina de coleta**.

O canal dos diários consorciados estava escrito desde 22/09 e **fora do pipeline** — nem em `atualizar.yml`, nem nos portões —, porque a fonte bloqueava e rodá-lo não produzia nada. Destravado (§217), ele passa a ser o único caminho para a maioria dos 5.041 municípios sem diário indexado no Querido Diário, e ficar fora da rotina seria deixar o conserto na gaveta.

**A janela é curta de propósito: oito dias.** Uma edição consorciada é um PDF de vários megabytes e leva cerca de dois minutos entre baixar e ler; varrer o ciclo inteiro são horas por estado — medido. Isso é trabalho de rodada dedicada, não de cadência diária. A rotina precisa do que é novo desde ontem; o retroativo se faz uma vez.

**O que foi varrido nesta sessão, e o que ficou.** Minas Gerais, Goiás e Ceará fecharam o ciclo inteiro: **19 pistas e 7 decretos** (MG 11 pistas, CE 5, GO 3). Paraná, Rio Grande do Sul e Rio Grande do Norte não começaram, por tempo; a Bahia não tem o que varrer enquanto as duas fontes dela seguirem fora do ar (§217). O retroativo desses quatro fica declarado como **pendente**, e não como varrido — a rotina diária, de janela curta, não o cobre.

O autoteste do coletor entrou na lista de portões, onde não estava.

## §222 · Terceira cópia do mesmo vocabulário, e ela só falhou quando a fonte voltou · 25/09/2026

Classe **correção de verificação**. Nenhum número muda; sete atos deixam de reprovar o portão.

O canal dos diários consorciados escreve `DOM-consorciado` como canal do ato. O portão de consistência mantinha a **própria cópia** da lista de canais válidos, e esse valor não estava nela — os sete decretos de Minas Gerais reprovaram assim que entraram no banco.

**É a terceira cópia do mesmo tipo de vocabulário a envelhecer em um dia** (§213 foram duas: a do `log_busca` e a do portão). E o padrão de quando ela falha é o que vale registrar: o coletor existia desde 22/09 e **nunca tinha produzido dado**, porque a fonte estava bloqueada. A cópia desatualizada ficou invisível enquanto o canal estava parado — é o mesmo fenômeno do §212, onde consertar a leitura foi o que expôs o custo de escrever.

O conjunto passou a ser declarado em `coletores_base` e importado por quem confere. E `DOM` e `DOM-consorciado` ficam **propositalmente distintos**: no primeiro o diário é do próprio município; no segundo é de uma associação, e a atribuição do município é heurística de proximidade dentro do PDF. Mesma origem legal, força probatória diferente — quem lê o dado precisa saber qual dos dois é.

O autoteste do coletor passou a provar que o canal que ele escreve cabe no vocabulário, para que a próxima invenção reprove em quem a inventou, e não no CI.

## §221 · A página de Saúde pesava 10 MB, e um terço era formatação · 25/09/2026

Classe **desempenho e integridade de escrita**. Nenhum dado muda de valor.

**Medido nas doze páginas**, com o cache aquecido: nenhuma passa de 3 segundos, nenhuma tem erro de execução, nenhuma rola na horizontal em 375 px. As leituras de 9 e 10 segundos que apareceram na primeira medição eram artefato da página medida primeiro — vale registrar, porque é o tipo de número que vira decisão errada se não for repetido.

A exceção real era o **peso**: a página de Saúde baixava **10,2 MB**, quase tudo em quatro séries semanais por município. Duas causas, e nenhuma delas é dado:

**Uma população escrita 37 vezes.** Cada semana de cada município repetia o campo `pop`, que já está um nível acima, no próprio município, e que a página não lê de dentro da semana — **11.579 repetições** por arquivo. Não é dado perdido ao sair: é o mesmo número, escrito 37 vezes.

**E a indentação.** Ela existe para o diff do robô ficar legível, e vale para quase todo o `data/`. Nos arquivos que o navegador baixa **por completo** ela custa 38% do peso. A decisão já tinha sido tomada uma vez, para o clima municipal; passou a valer para as seis séries de saúde, por uma porta comum — `gravar(..., compacto=True)`.

Resultado: **10,2 MB → 6,8 MB**, um terço a menos, em 2,3 segundos e sem erro. O que ficou de fora de propósito: carregar a chikungunya só quando o leitor chega ao painel dela economizaria mais 3 MB, mas muda o comportamento da página e é decisão de editoria, não de desempenho.

### E o arquivo de clima era o único grande sem escrita atômica

Ao unificar a porta, apareceu o motivo pelo qual ela precisava existir: `coletar_sinais_risco` **nunca foi migrado** depois da corrupção de 21/09/2026 — os quatro arquivos dele, entre eles o de clima, escreviam direto no destino, sem temporário e sem `os.replace()`. O de clima é o maior de todos e é regravado dezenas de vezes numa varredura nacional: era o mais exposto de `data/` a uma interrupção no meio da escrita, e o único que ainda estava assim. Agora escreve como o resto, com a espera do cadeado do Windows inclusive.

## §220 · O autoteste que escrevia no livro-razão, e o portão que faltava para vê-lo · 25/09/2026

Classe **infraestrutura de verificação**. Oito linhas indevidas removidas do log; nenhum número público muda.

**O achado, e ele é meu.** Ao conferir a varredura dos diários consorciados, apareceram no log de buscas **oito execuções de uma fonte chamada "teste"** — uma fonte que não existe, numa consulta que nunca aconteceu. Foram escritas pelo **autoteste** deste coletor, rodado várias vezes nesta sessão.

A causa é específica e vale guardar: o autoteste mockava a rede, os arquivos e o livro de fontes, e **não** mockava `registrar_lacuna` — que chama `log_busca`, que grava. Ninguém percebeu porque o autoteste ficou verde. Autoteste prova o que o autor lembrou de provar.

As oito foram removidas. Isso **não** é deduplicar o log, que continua proibido e por bom motivo: é desfazer uma escrita que não devia ter acontecido, num livro cuja função é registrar tentativas reais.

**A regra existia; faltava quem conferisse.** Vários coletores declaram "nunca toca dado real", e as travas estruturais deles procuram `open(...)` e `gravar(...)` no próprio fonte — e não enxergam a escrita que acontece três chamadas abaixo, dentro de `coletores_base`. Só a execução mostra. O portão novo roda os **51 autotestes** do projeto e compara `data/` antes e depois.

**Ele já provou o valor duas vezes.** Achou um autoteste **vermelho que nenhum portão existente rodava** (`monitorar_busca_web.py`), quebrado pelo próprio §213: era o mesmo teste-por-texto do vocabulário, num segundo arquivo. E encontrou três autotestes que regravam arquivos com conteúdo idêntico.

**A calibragem é parte do achado.** A primeira versão comparava tamanho e carimbo, e acusou esses três de "alterar dado" — acusação falsa: o conteúdo era o mesmo byte. Portão que grita sem motivo ensina a ignorar portão. Ficou assim: regravar idêntico é **aviso** e vale mockar; **alterar** conteúdo reprova. O caso que originou o portão cai no segundo grupo, porque acrescentou linhas.

## §219 · O mesmo defeito, procurado de propósito: quatro achados em quem lê planilha · 25/09/2026

Classe **correção de coleta**. Nenhum número público muda hoje; o que muda é o que aconteceria quando uma fonte trocasse de layout.

Depois de o mesmo padrão aparecer quatro vezes num dia — fonte que não responde o que devia, e o arquivo registrando isso como se ela tivesse dito "não há" —, valia procurá-lo de propósito nos coletores que ainda não tinham sido tocados. Quatro achados, todos reais, todos da mesma família. E um descarte que também vale registrar.

**Base nacional lida pela metade virava "ok".** `coletar_declarado_nacional` lê MUNIC e ICM, que cobrem os 5.570 municípios. Os parsers devolvem dicionário vazio quando a aba muda de nome ou a coluna do IBGE some — e não havia **nenhum piso**: com zero municípios casados, o coletor gravava `status: "ok"` e decisão `registro` no log. Uma troca de layout do IBGE seria invisível. Agora há piso de sanidade, folgado de propósito: ele separa "quebrou" de "veio menos", e abaixo dele é lacuna declarada com a aba e a coluna a reverificar.

**Execução zero que não era execução zero.** `coletar_execucao_mps` e `coletar_transferegov` filtram por nomes de coluna do Portal e do TransfereGov. Renomeada uma coluna, nenhuma linha casa, todo total fica `0,00` — e a única guarda existente conferia se o arquivo **baixou**, não se alguma linha casou. O site passaria a dizer que as medidas provisórias não executaram nada e que não houve repasse nenhum. Agora, nenhum casamento é leitura quebrada: lacuna declarada, e o que já estava gravado **não é sobrescrito**.

**Ausência de valor virava R$ 0,00.** Em `coletar_financiamento`, o valor de uma transferência era `float(valor or valorLiberado or 0)`. Isso apaga a distinção que é a regra central deste projeto: uma transferência de R$ 0,00 e uma resposta **sem** o campo de valor viravam o mesmo número. Agora valor ausente é `null` com marca própria, e zero continua sendo zero — travado por teste nos três casos: ausente, zero e ilegível.

**Falha de formato sem rastro.** No `coletar_siconfi_182`, o galho de erro de rede declarava a lacuna; o galho que dispara quando a fonte devolve algo que não é o JSON esperado — página de erro disfarçada de 200, corpo truncado — só somava um contador local e seguia. Justamente a classe de erro que originou o §210 era a única sem registro no log.

**O que NÃO é achado, e por que vale dizer.** `coletar_painel_am` já implementa a lição inteira: recusa a leitura quando metade dos itens não casa com o IBGE, e só deduz um município por eliminação quando sobra exatamente um de cada lado. Os coletores de boletim estadual já têm piso mínimo e levantam em toda mudança estrutural. Eles são a referência de onde o remédio veio — não o problema.

## §218 · A fila não parava por ser difícil; parava por estar fora de ordem · 25/09/2026

Classe **infraestrutura editorial**. Nenhum dado muda, nenhum item é promovido.

A promoção ao banco é sempre humana (R7), e as filas somam **848 itens sem julgamento**, espalhados por sete arquivos com sete formatos. Lidos como JSON cru, o custo não está em decidir — está em achar as decisões que importam no meio das que se descartam em dois segundos.

A triagem que separa isso **já existia nos dados** e não estava sendo usada para ordenar: das 485 pistas pendentes, **88 estão em confiança A** e 27 são candidatos fortes, contra 230 em B/indefinido. `scripts/preparar_fila_revisao.py` junta as sete filas, ordena por quanto cada item merece a atenção e mostra o **trecho** — que é o que permite descartar sem abrir o documento. Medido no próprio material: o trecho de maior confiança da fila é texto genérico da Lei 12.608, e some da fila em um olhar.

O que ele **não** faz é o ponto: não promove, não classifica, não decide e não escreve no banco. Só ordena e apresenta o que já estava lá. Falso positivo provável vai para o fim e **não é excluído** — a máquina palpita, a pessoa decide.

O relatório sai **fora do repositório**, porque fila de revisão é material de trabalho da editoria e este repositório é público.

Seis casos no autoteste, e um deles rendeu uma lição própria: a trava estrutural reprovou por causa da **prosa que a explicava** — a frase que citava os nomes das funções proibidas casava com o padrão que as procura. Travas que leem código-fonte cru confundem a menção com a chamada. Esta passou a olhar só o código, com o tokenizador do próprio Python.

## §217 · O canal que faltava para 90% do país estava destravado, e ninguém tinha voltado a tentar · 25/09/2026

Classe **coleta**. Peso zero: tudo o que sai daqui é pista, e pista não entra no banco sem leitura humana (R7).

**O problema, que já estava diagnosticado.** Dos 5.571 municípios, **5.041 não têm diário indexado no Querido Diário** — e a causa foi verificada em 22/09 contra o código-fonte do próprio QD, não suposta: a raspagem é feita site a site, e a plataforma SIGPub (`diariomunicipal.com.br`), usada pelas associações municipais de pelo menos MG, GO, BA, CE, PR, RS e RN, tem **um único raspador** em todo o país, o de Alagoas. É por isso que AL lidera a cobertura com 94% enquanto MG, PI, SC, GO, AC e MT ficam entre 0,4% e 2,5%. Não é ausência de plano: é lacuna de raspagem.

**O que bloqueava.** O widget de calendário do SIGPub exige um token preenchido por JavaScript. Duas rodadas de investigação, em 20 e 21/09, concluíram que nem um Chromium real o obtinha: o console acusava `requestStorageAccess: Permission denied`, e o token vinha como placeholder. O motor de PDF → texto → atribuição de município ficou pronto e testado, esperando.

**Medido hoje: o token vem real.** A mesma configuração headless que o script já usava devolve o valor verdadeiro, e um POST de calendário com ele responde com a edição do dia, número e link do PDF. O que mudou entre 21 e 25/09 não dá para afirmar daqui — o que dá para afirmar é o que foi medido: não há bloqueio. **Sete das nove fontes entregam.**

Vale registrar o método, porque ele se repete: a conclusão anterior não estava errada por preguiça — estava datada. Bloqueio de fonte tem prazo de validade, e reverificar é barato perto de tratar como impossível o que já não é.

### O primeiro estado varrido, e o que ele trouxe

**Minas Gerais, ciclo inteiro: 86 dias com edição, zero erros, 11 pistas e 7 decretos novos.** São decretos municipais de situação de emergência — Teófilo Otoni, Bocaiúva, Diamantina, Bonfinópolis de Minas, Conquista, Cláudio e Coração de Jesus — em municípios cujo diário **nunca esteve indexado no Querido Diário**. Eles existiam, publicados, e o Monitor não tinha por onde vê-los.

É a medida do que o canal vale: um estado, e sete atos que nenhum outro canal do projeto alcançava.

### Duas medições que mudaram o desenho da varredura

**O extrator estava na ordem errada para este uso.** O coletor tentava `pdfplumber` primeiro e `pypdf` como reserva — ordem herdada dos coletores de boletim de saúde, onde a geometria importa porque é preciso ler número dentro de tabela. Aqui não importa: o que se faz com o texto é casar expressão regular. Medido num PDF de 5 MB e 44 páginas: **3,8 s contra 2,0 s**, e os diários consorciados chegam a 7 MB. Numa varredura de quase noventa dias vezes sete fontes, isso é diferença de horas. A ordem foi invertida; a reserva e o critério de troca continuam, porque texto curto demais significa PDF que o primeiro leitor não soube abrir.

**E ela gravava só no fim.** Medido: cerca de duas horas por fonte, sete fontes. Uma interrupção na última hora jogaria fora todas as anteriores — a mesma lição do §212, agora aplicada ao que se coleta, e não ao que se registra. Passou a gravar a cada fonte concluída, e a varredura roda fonte a fonte para que cada uma feche sozinha.

### E o mesmo defeito do dia, pela quarta vez

Ao rodar a Bahia, o coletor disse **"0 dia(s) com edição, 0 erro(s)"**. Os dois slugs baianos respondem `200` com `{"error":"Ocorreu um erro inesperado!"}` em **toda** data testada, inclusive dias úteis — fonte inteira fora do ar, relatada como ausência de publicação.

**Só que o conserto óbvio estava errado, e medir antes evitou trocar um defeito por outro.** Tratar esse `error` como lacuna criaria uma lacuna falsa a cada fim de semana: medido contra produção, o **mesmo corpo** volta para sábado (19/09), domingo (20/09) e Natal, enquanto segunda e terça entregam a edição. Ou seja, `error` é como esta fonte diz "não houve edição neste dia", e a leitura original estava certa.

O sinal de fonte quebrada não está no dia — está em **errar todos os dias úteis**. Ficou assim: `error` segue sendo dia sem edição; corpo que não dá para ler **levanta**, porque aí a forma mudou e devolver vazio esconderia isso; e fonte sem nenhuma edição em cinco dias úteis é declarada **fora do ar**, com o nome certo. Os dois slugs da Bahia foram reconferidos na página inicial da plataforma e continuam sendo aqueles: não é curadoria desatualizada, é a fonte que não está entregando.

## §216 · O livro guardava doze registros para cinco consultas, e isso apagava a varredura · 25/09/2026

Classe **correção de coleta**. Nenhum número público muda; o que muda é o site saber o que já consultou.

**A pergunta que revelou.** Terminada a varredura, a conferência foi direta: cada município foi consultado ao menos uma vez? O **log** — que é o livro-razão, só cresce e nunca se deduplica — diz que sim, **5.571 códigos IBGE distintos** com consulta ao diário dentro do ciclo. Mas o **livro de fontes consultadas**, que é de onde o coletor tira a fila de pendentes, dizia que **1.896 continuavam pendentes**. Dois arquivos, duas respostas.

**Quem estava errado era o livro, e por um detalhe de desenho.** Ele guarda, por município, as últimas **doze entradas** — uma janela, não um histórico. Medido: das doze, apenas **cinco ou seis eram consultas distintas**; havia **38.434 entradas repetidas** no arquivo inteiro. A causa é boa e vira defeito na escala: `coletar_s2id` marca os 5.571 municípios a cada rodada, e roda mais de uma vez por dia, então quatro marcações idênticas de "DOU/SEDEC (via MIDR) em 24/09" ocupavam quatro das doze vagas — e empurravam para fora justamente a consulta ao diário municipal, feita uma vez só.

**O conserto.** A janela passa a guardar as doze consultas **distintas** (fonte, dia), ficando com a entrada mais recente de cada par. Não é dedupe de conteúdo — é a distinção entre dois arquivos com perguntas diferentes, e ela merece ficar escrita:

- o **log** responde *quantas tentativas houve*. Duas execuções iguais em dias diferentes são duas tentativas reais e contam; deduplicar ali já apagou quase 3.000 execuções em 23/09, e continua proibido.
- o **livro** responde *que fontes foram consultadas, e quando*. A mesma fonte no mesmo dia, repetida, não acrescenta resposta nenhuma — só gasta vaga.

Refeito o arquivo com a regra nova, a janela passou a cobrir de 11/09 a 25/09 no lugar de só 23/09 a 25/09, e as duas respostas voltaram a bater: **5.571 de 5.571 com o diário municipal consultado no ciclo, zero pendentes**.

Quatro casos no autoteste, um deles o contraste que dá sentido à regra: o log continua **não** deduplicando.

## §215 · A quebra de linha vinha da fonte, e a normalização estava no lugar errado · 25/09/2026

Classe **integridade de evidência**. Nenhum número muda.

O §177 (23/09) estabeleceu que **cópia preservada em CRLF é cópia que depende da máquina que a produziu**, e nasceu do OCR — o Tesseract do Windows devolve CRLF. O conserto de então foi fixar o modo de escrita.

A varredura nacional mostrou o outro caminho: **dois diários municipais vieram da fonte com CRLF solto**, 8 e 16 quebras entre mais de cem mil LF. O modo de escrita não pega isso — ele traduz a quebra que **nós** escrevemos, não a que já veio dentro do texto. O portão de evidências reprovou, com razão.

A normalização passou para a **entrada**, onde o texto é lido. Isso é legítimo porque a cópia preservada é **transcrição, não arquivo byte a byte** — já redigimos CPF dela, por dever legal —, então padronizar a quebra de linha está dentro do mesmo contrato, e é o que torna a cópia independente da máquina. Cinco cópias já em disco foram normalizadas e tiveram o hash **reselado no índice**, de modo que a conferência de integridade continua batendo.

## §214 · 503 não é bloqueio nem limite: é "tente mais tarde", e a resposta certa é tentar mais tarde · 25/09/2026

Classe **correção de coleta**. Peso zero; o que muda é quanta coisa a varredura consegue ler.

**Medido na varredura nacional, com ela rodando:** dos 505 primeiros municípios, **63 viraram lacuna por `HTTP 503 Service Unavailable`** — 12 %. O projeto já separa bem as recusas que se respeitam sem insistir (403, 401, captcha, login) e o limite de taxa (429, que manda esperar). O 503 não é nenhum dos dois: é o servidor dizendo que está fora **agora**.

**E a defesa que existia não servia para isto.** Diante de 5xx, o coletor trocava para o domínio de reserva do Querido Diário. Essa reserva foi criada em 21/09 para cobrir **troca de endereço** — e o endereço antigo serve o **mesmo serviço**. Se a produção está fora, a reserva está fora junto: a tentativa era gasta sem chance de sucesso, e o município virava lacuna.

**O conserto.** 503 (e 5xx em geral) passa a ser tratado como o que é: duas novas tentativas, com 5 e 15 segundos de espera, antes de recorrer à reserva ou declarar a lacuna. 429 segue com a espera longa que a fonte pede. **4xx continua subindo na hora** — consulta errada não melhora com repetição, e repetir dobraria a carga sobre uma API pública mantida por um projeto sem fins lucrativos.

**Medido depois, com o conserto rodando:** a varredura terminou com **204 municípios** em lacuna por 503; a passagem seguinte, com a espera, leu **os 204, com zero lacunas** — e encontrou mais um decreto. Nenhum se perdera: no caminho de erro o coletor **não** marca a fonte como consultada, então quem cai em 503 continua na fila. Quatro casos no autoteste, com relógio injetado: 503 que passa na terceira tentativa espera 5 e 15; 503 permanente desiste depois dessas duas, sem laço infinito; 404 sobe sem espera nenhuma; 429 espera os 30 segundos, uma vez.

## §213 · A varredura dos diários municipais estava morrendo havia um dia, por uma palavra · 25/09/2026

Classe **correção de coleta**. Nenhum número público muda; o que muda é a varredura voltar a andar.

**O que aconteceu.** O §194, de 24/09, criou uma decisão nova para o log: `sem_edicao_no_periodo` — o município tem diário indexado, mas **nenhuma edição dentro da janela**, que é diferente de "indexado e sem menção" e diferente de "não indexado". A distinção está certa e é exatamente o tipo de coisa que este projeto separa. Só que o vocabulário de decisões do log é **fechado**, por um `assert`, e a palavra nova não foi acrescentada lá.

Resultado: desde 24/09 a varredura dos diários municipais **morria com `AssertionError` no primeiro município indexado sem edição na janela**. Morrer é melhor do que gravar errado — o `assert` fez o trabalho dele —, mas a varredura ficou parada um dia inteiro e a fila de pendentes cresceu de 2.965 para **3.428** sem que isso aparecesse como problema de vocabulário.

**O conserto não é acrescentar a palavra.** Acrescentá-la é uma linha; o que importa é por que ninguém viu. O vocabulário era uma tupla anônima dentro do `assert`, visível só para quem abrisse a função — então o coletor que **inventa** uma decisão não tinha como conferir se ela cabia. Agora a lista é a constante `DECISOES_LOG`, e o autoteste do coletor dos diários prova que **toda** decisão que ele pode produzir cabe nela. Inventar decisão nova sem registrá-la passa a reprovar no portão, não em produção.

**E a palavra tinha ficado de fora de DUAS listas, não de uma.** A segunda apareceu depois, quando a suíte inteira rodou: o portão `verificar_consistencia.py` mantinha a **própria cópia** do conjunto de decisões válidas para o canal dos diários, e reprovou **86 execuções legítimas** — pelo mesmo motivo, em outro lugar. Cópia de vocabulário é isso: envelhece em silêncio e só se manifesta quando a decisão nova aparece no dado.

Agora o conjunto do canal é declarado **onde as decisões são produzidas**, no próprio coletor, e importado por quem confere. As duas listas não podem mais divergir, e o autoteste do coletor prova que tudo o que ele pode produzir cabe nos dois conjuntos — o do canal e o do log.

Dois testes a mais no lado do log: que toda decisão do vocabulário é de fato aceita, e — o que dá sentido a ele ser fechado — que decisão fora dele reprova. E um terceiro achado de passagem: o teste que guardava `consultado sem achado` lia o **texto** da função procurando a palavra, e reprovou quando a lista virou constante, sem nada ter mudado de comportamento. Teste de texto quebra em refatoração; ele passou a testar o que importa, chamando a função.

## §212 · O livro de fontes tinha o mesmo defeito do log, e ele é o arquivo que já foi corrompido · 25/09/2026

Classe **infraestrutura de coleta**. Nenhum número público muda.

**O que apareceu ao preparar a varredura dos diários municipais.** O §209 resolveu, para o log de buscas, a escrita repetida a cada município: 20 MB lidos e regravados por consulta. O livro de fontes consultadas — `fontes_consultadas.json`, 12 MB — continuava exatamente como estava, e é chamado uma vez por município pelos mesmos coletores. Nos **2.965 municípios pendentes** de hoje, são cerca de 71 GB de entrada e saída só nele, e 2.965 janelas em que uma interrupção deixa o arquivo pela metade.

Não é hipótese: **esse é o arquivo que foi corrompido assim em 21/09/2026**, quando um coletor foi interrompido no meio de uma gravação e o JSON voltou com 166.961 linhas no lugar de 368.019. A escrita atômica resolveu o arquivo truncado; a frequência da escrita ficou de pé.

**E ele apareceu antes disso, medido, numa rodada que parecia travada.** O `coletar_s2id` ficou **53 minutos** com a CPU em 100% sem escrever nada, e a primeira suspeita — rede — estava errada. Cronometrado por partes: a varredura do DOU leva 29 segundos em 7 requisições; abrir um ato leva cerca de 1 segundo; os parsers da tabela rodam em milissegundos. O tempo estava no laço final: cada município reconhecido chama `marcar_fato_municipal`, que lê e regrava o livro de 12 MB, e cada município que não casa com a referência do IBGE chama `log_busca`, que faz o mesmo com o log de 20 MB. São mais de 600 municípios em 136 portarias — horas de serialização de JSON para gravar algumas centenas de campos.

É um defeito que só aparece quando a fonte volta a funcionar: enquanto o canal do DOU lia zero (§210), esse laço nunca rodava. Consertar a leitura expôs o custo de escrever.

**O conserto é o mesmo, e agora é simétrico.** O livro ganhou lote opcional, igual ao do log: sem abrir lote, nada muda para nenhum coletor existente; com lote, o livro é carregado uma vez, mutado em memória e descarregado de 250 em 250. A varredura dos diários municipais abre os dois lotes e os fecha num `finally` — porque perder 2.900 registros por causa de um Ctrl-C seria pior do que a entrada e saída que o lote evita — e grava parcial a cada 250 municípios, de modo que o que já foi lido conte mesmo se a rodada não terminar.

**E um terceiro arquivo, com um erro de data junto.** O teste de cobertura do Querido Diário é cacheado por janela — mas gravava assim mesmo, a cada município: `cobertura_qd.json` (418 kB) e, pior, `verificacao_municipal.json` (2 MB), lido e regravado inteiro. São cerca de **13 GB de entrada e saída na varredura para não mudar nada**. Agora só grava quem mudou.

Ao arrumar apareceu um erro que a escrita cega escondia: o espelho público carimbava `data_teste_cobertura` com a data de **hoje** mesmo quando o resultado veio do cache — isto é, quando o teste tinha sido feito dias antes. Afirmava uma verificação que não houve. A data que vai ao espelho passou a ser a do **teste**, e não a da rodada.

Os lotes entraram em `coletar_s2id`, `coletar_diarios_municipais` e `coletar_doe` — este último por antecipação, porque hoje nenhum DOE tem adaptador confirmado e o laço nem chega ao município; o dia em que chegar não é o dia de descobrir isto com 27 UFs na fila.

Nove casos no autoteste, em `data/` temporário, para os dois lotes: sem lote é uma gravação por chamada (o comportamento antigo intacto); com lote nada é gravado até fechar e tudo chega; o teto descarrega no caminho e nada se perde; fechar duas vezes não duplica; e a regra de fundo do livro — **nível de verificação nunca rebaixa** — continua valendo com o lote aberto. São 61 portões.

## §211 · A segunda rodada do clima municipal mostrava previsão de ontem com a data de hoje · 25/09/2026

Classe **correção de coleta**. Peso zero: sinal de risco não entra na nota.

**O defeito.** O coletor de clima municipal decide o que pedir com uma pergunta só: *este município já tem o valor?* Na primeira varredura isso basta. Na segunda, no dia seguinte, ele pulava quem já tinha leitura — e mesmo assim carimbava o arquivo inteiro com `gerado_em` de hoje. O mapa diria "coleta de 25/09" mostrando, para a maioria dos municípios, a previsão de 24/09.

O comentário do próprio código dizia *"município já lido **hoje** não é pedido de novo"*. A intenção estava escrita; o "hoje" é que não existia em lugar nenhum.

**Por que isso não se resolve pedindo tudo de novo.** O teto diário do plano gratuito do Open-Meteo conta por localidade: 5.570 municípios × 2 variáveis são 11.140, acima dos 10 mil do dia. Renovar as duas no mesmo dia é impossível por construção — a rotina diária alterna a variável pelo dia, e o arquivo, portanto, **sempre** terá leituras de dias diferentes. O que não pode é isso ficar implícito.

**O conserto.** Cada leitura passa a carregar a data em que foi feita (`lido_tempo`, `lido_ar`), e o coletor passa a distinguir duas rodadas que antes eram uma só: **renovar** (o padrão — precisa ler quem não tem o valor *ou* cujo valor é de outro dia) e **preencher** (`--preencher` — só quem nunca teve leitura, para fechar a cobertura nacional sem gastar o teto renovando o que já está lido). O resumo conta por data, e a linha-fato da página passou a dizer de quando é cada variável em vez de deixar a data da coleta passar por data de tudo.

Cinco casos no autoteste, sobre a função que decide: município sem leitura entra nas duas rodadas; leitura de ontem é renovada na rodada diária e **não** é refeita na de preenchimento; leitura de hoje não é pedida de novo; e leitura sem carimbo conta como a renovar — porque ausência de data não é prova de atualidade.

## §210 · O DOU trocou de formato, e dois coletores passaram a ler zero sem dizer nada · 24/09/2026

Classe **correção de coleta**. Peso zero: nada aqui muda nota. O que muda é o que o site consegue ver.

**O que aconteceu.** A página de consulta do Diário Oficial da União trocou o transporte do resultado da busca. Ele vinha num `<input ... value="{json}">` e passou a vir num `<script type="application/json">`. Dois coletores — `coletar_s2id` e o `coletar_espin` escrito hoje — tinham, cada um, a **cópia** do mesmo regex do `<input>`; os dois passaram a devolver **lista vazia** para qualquer consulta.

**O silêncio é o defeito, não a troca.** Mudança de formato de fonte é rotina, e o projeto tem guarda para ela: o `coletar_s2id` testava `"jsonArray" in texto` antes de confiar na leitura. Só que essa string **continua na página** — está dentro do próprio `<script>` e no JavaScript ao lado. A guarda passava, o parser devolvia `[]`, e o coletor registrava a consulta como bem-sucedida com zero achados. Medido em 24/09, com a janela do ciclo: a consulta de reconhecimentos tem **132 resultados reais** e o coletor lia **0**.

Zero dessa forma é a pior coisa que este projeto pode publicar: tem a cara de "procuramos e não há" e é, na verdade, "não conseguimos procurar". Continuavam entrando reconhecimentos pelo canal principal, que é o RSS do MIDR — o canal do DOU é o segundo —, mas o segundo estava desligado e ninguém sabia.

**O conserto não é o regex novo.** O leitor da consulta do DOU passou a ser **um só**, em `coletores_base`, lido pelos dois coletores; e ele **levanta** quando a página não traz a estrutura de resultados, em vez de devolver lista vazia. A diferença entre "a fonte respondeu e não há" e "a fonte respondeu e não entendi" deixou de ser uma linha de guarda que alguém precisa lembrar de escrever, e passou a ser impossível de confundir: uma devolve `[]`, a outra estoura.

### Três coisas que a leitura correta mostrou

**A busca não pagina, e entrega no máximo 50.** `delta=50` traz 50; `delta=100` volta a 20; `start` é ignorado. Ler os 50 mais recentes de 132 e não dizer nada seria apresentar recorte como varredura — então a consulta virou varredura por **janela**: quando o total que a página declara é maior do que o que ela entrega, a janela é partida ao meio, recursivamente, até caber. Dia único que ainda estoure volta declarado como leitura parcial, e o coletor registra a lacuna.

**A data vai em dd-mm-aaaa.** Com `aaaa-mm-dd` a página responde `200`, normalmente, e devolve **outra janela** — 3 resultados no lugar de 132. Formato errado aqui não dá erro: dá número menor. Ficou travado em teste, porque é o tipo de coisa que se conserta uma vez e se reintroduz na próxima.

**O trecho da busca não é o ato.** O que a consulta devolve é um excerto de ≈235 caracteres, com o termo embrulhado em marcação de destaque, que **nunca** chega ao município e frequentemente corta o verbo do ato. Quem precisa do conteúdo abre o ato. E o ato moderno não diz mais "Município de X - UF" em prosa: traz uma **tabela** (UF · Município · Desastre · Decreto · Data · Processo), que é dado melhor do que a prosa — vem com o número e a data do decreto **municipal**, que agora entram em campo próprio, sem mudar o significado de nenhum campo que o banco já usava.

E o rótulo do ato deixou de ser afirmação nossa. Quem reconhece situação de emergência de município é a SEDEC (Lei 12.608; Decreto 10.593, art. 20), e a busca **declara o órgão** de cada resultado — então "Portaria SEDEC/MIDR nº N" passou a ser o que a fonte diz, e ato de outro órgão que apenas casa com a mesma expressão não vira reconhecimento federal. Órgão que a fonte não declarou continua sendo lido: silêncio da fonte não é filtro.

**A rodada completa, com o canal consertado: 618 reconhecimentos lidos e ZERO novos.** É a melhor notícia possível, e vale explicar por quê. O canal principal é o RSS do MIDR, que chega antes; o canal do DOU é o segundo. Os dois são independentes — um lê a notícia do ministério, o outro lê o ato publicado — e, varrendo o ciclo inteiro, concordam inteiramente: tudo o que o DOU reconhece já estava no banco. O canal desligado não estava escondendo reconhecimento nenhum; estava deixando de **confirmar**.

**Mas o ato traz o que a notícia não tem**, e descartar isso seria jogar dado fora por causa do que já sabíamos: o número e a data do decreto **municipal** e a classe do desastre, que estão na tabela do ato e não no texto da notícia. O acréscimo é aditivo e usa a mesma chave que já serve para deduplicar — preenche campo ausente, nunca sobrescreve campo existente —, e isso ficou travado em teste.

### A fonte que tinha ficha no catálogo e não tinha código

**ESPIN — emergência em saúde pública declarada — estava em `aguardando_primeira_coleta` desde 02/09.** O zero que a página mostrava veio de busca manual de 05/09. Zero conferido à mão é dado; o que ele não faz é durar. Uma declaração publicada em novembro passaria despercebida até alguém lembrar de procurar de novo.

`coletar_espin.py` busca no DOU pelo vocabulário do **próprio ato** e **classifica pelo que o texto diz que é**: declaração, prorrogação, encerramento ou menção de passagem. Nada entra no banco por conta própria — a promoção é humana (R7) —, e a classificação serve para separar o que vale a leitura de quem: a declaração vai à frente da fila, prorrogação e encerramento vão atrás, porque prorrogar uma emergência que o banco não tem descreveria um estado que o site não conhece. Menção de passagem — a resolução da Anvisa que cita a expressão, e que a primeira rodada real encontrou — não é ato e não entra em lugar nenhum.

Duas decisões foram **medidas**, não escolhidas de cabeça. Os termos: a expressão por extenso devolve 2 resultados na janela do ciclo, a forma curta devolve 26 — e a sigla "ESPIN", com ou sem aspas, devolve 37 atos sem relação nenhuma, porque o buscador do DOU não a trata como sigla; ficou de fora, porque ruído não é cobertura. E quais atos abrir: **ESPIN é declarada pelo Ministro da Saúde** (Decreto 7.616/2011, art. 2º), e o órgão vem declarado pela própria busca — então só os atos dele são abertos por inteiro. Órgão ausente é lido, nunca descartado: silêncio da fonte não pode virar filtro.

**E a revisão do coletor achou quatro coisas que o autor não veria.** Vale registrar porque são todas do mesmo tipo — não erro de conta, e sim silêncio.

**Falha de leitura virava ausência.** Quando a rede falhava ao abrir um ato, os dois coletores caíam para o excerto (ESPIN) ou descartavam o resultado (S2iD), sem registro. Uma rodada com rede ruim se pareceria, no arquivo, com "procuramos e não há". Agora o ato que não pôde ser aberto entra em `nao_lidos`, muda a situação do registro para `leitura_incompleta` e vira lacuna declarada com o endereço do ato.

**O classificador não tinha "não sei".** Ele devolvia sempre declara, prorroga, encerra ou menciona — nunca a dúvida, contra a regra do projeto de que na dúvida o classificador não classifica. Agora há `incerto`, e ele aparece em três situações: dois verbos em trechos diferentes do mesmo ato, ato que não pôde ser aberto, e verbo que aparece só no excerto de um ato que não foi aberto. O caso inverso também ficou travado: *"declara o encerramento"* é uma frase só, não duas decisões, e continua sendo encerramento — o casamento mais específico absorve o que se sobrepõe a ele.

**Classificação automática chegava ao texto público.** O cartão de emergências sanitárias contava `declaracoes` do coletor, ou seja, ia ao ar o que uma expressão regular decidiu sozinha. Peso zero no índice não é a mesma coisa que dispensa de revisão: o contador do cartão passou a vir **só do banco**, que é humano, e o que o coletor acha vai para `data/espin_revisar.json`, a fila de leitura do projeto (R7). Enquanto houver ato na fila, o cartão diz que há ato localizado **em conferência** — que é o fato — e não que há emergência registrada.

**E faltava o ritmo de dois segundos.** Estreitar a janela multiplica as consultas ao mesmo host, e depois abre-se um ato por resultado: era a hora de ir mais devagar, não mais rápido. O §11 do projeto passou a valer no canal do DOU, com a primeira consulta de cada varredura sem espera e as seguintes com ela — travado em teste, inclusive a contagem das esperas.

O cartão de "Emergências sanitárias declaradas" deixou de dizer "coleta em andamento" — frase que serve para quem não procurou — e passou a dizer qual dos três estados é o caso: não procuramos, procuramos e não há (com a janela e a data), ou há.

### E um cadeado do Windows que derrubou a rodada

No meio da varredura, `coletar_s2id` morreu com `PermissionError` ao substituir `data/evidencias.json`: no Windows, `os.replace()` falha quando **outro** processo tem o destino aberto, e o indexador do sistema abre os JSON grandes de `data/` sozinho, por um instante. A escrita atômica de 21/09 continua igual; ganhou uma espera curta e algumas tentativas. O que ela **não** faz é engolir o erro — falta de permissão de verdade tem de aparecer —, e o temporário não fica órfão ao lado do arquivo bom.

Dois portões novos guardam o conjunto — o leitor do DOU e a escrita de `data/` —, e os autotestes dos dois coletores passaram de 11 e 16 para 16 e 21 casos, com trava estrutural que confere a via que eles de fato usam para escrever. São 60 portões.

## §209 · A rodada nacional: os 5.571 municípios, e o que cada fonte aceitou dar · 24/09/2026

Classe **coleta**. Peso zero em tudo o que entra; nenhuma nota muda.

**O pedido.** Popular o site com pelo menos uma rodada de todos os municípios, em cada caso, e fazer rodar todos os coletores de saúde, de financiamento e de risco. O que segue é o resultado, com o que cada fonte aceitou dar e o que recusou — porque numa varredura nacional o que **não** vem é tão informativo quanto o que vem.

### O que impedia varrer o país, e foi resolvido

**O log de buscas era lido e gravado a cada município.** `log_busca` lê e regrava `data/log_buscas.json` — 16 MB — a cada chamada. Correto para um coletor de dezenas de municípios; para 5.570, são cerca de 180 GB de entrada e saída, e 5.570 janelas em que uma interrupção deixa o arquivo pela metade. É a mesma armadilha que corrompeu `fontes_consultadas.json` em 21/09. Agora `coletores_base` tem **lote opcional**: sem abrir lote nada muda para nenhum coletor existente; com lote, as execuções ficam em memória e descarregam de 250 em 250 — teto que limita a E/S e também o que se perderia numa interrupção.

**E a varredura levaria seis horas.** Medido contra o Tesouro: um trabalhador dá 60 chamadas por minuto, oito dão 522, sem um erro. Seis foi o meio-termo escolhido — corta a varredura para vinte minutos sem tratar a fonte como se fosse nossa. Paraleliza-se **só a rede**: tudo o que muta estado continua numa thread só, em ordem, porque trocar seis horas por uma corrida de dados no livro de buscas seria um mau negócio.

### Dinheiro próprio do município: a varredura completa

**Os 5.571 municípios consultados no SICONFI.** 1.497 com lançamento na subfunção 182, **3.998 que entregaram a declaração e não lançaram nada ali**, e 76 sem declaração. Mediana de **R$ 8,50 por habitante** entre os que lançaram.

A distribuição é extrema e o extremo é **real**: de menos de um centavo por habitante a **R$ 2.209,50**. Os seis maiores são municípios minúsculos do **Rio Grande do Sul** — Canudos do Vale liquidou R$ 3,66 milhões para 1.656 habitantes. Não é erro de vírgula nem de população: é o que a fonte declara, e conferi um por um.

**Dois defeitos que só a escala nacional produziu.** Com 27 capitais o mapa funcionava; com 5.571 ele quebrou de duas maneiras. Os **5.564 círculos com tratador de mouse** faziam a página levar 14 segundos para abrir — viraram camadas densas por classe, e agora são 5,5 segundos. E a **escala contínua de 0 ao máximo** punha 99 % do país na mesma cor: virou classe por quantil, com a legenda dizendo os limites (até R$ 1,16 · R$ 1,16 a R$ 4,48 · R$ 4,48 a R$ 13,96 · R$ 13,96 a R$ 40,05 · acima de R$ 40,05). A lista por extenso, de 5.571 entradas, passou a ser montada **quando o leitor abre**, não no carregamento: continua completa, muda só o momento em que é construída.

### Clima municipal: o teto que conta por localidade

`data/clima_municipios.json` guarda temperatura e PM2,5 por município, compacto. Duas coisas medidas com rede, e as duas mudaram o desenho:

**O plano gratuito do Open-Meteo conta por LOCALIDADE, não por chamada.** Um pedido com 100 coordenadas gasta 100 do teto diário de 10 mil — e 5.570 municípios × 2 variáveis são 11.140. **Não cabem no mesmo dia.** Por isso as variáveis passam a ser coletadas em rodadas separadas, alternando pelo dia na rotina diária, e o coletor **retoma**: município já lido não é pedido de novo.

**E varrer em rajada é recusado.** A primeira tentativa trouxe HTTP 429 em 39 de 56 lotes e uma coleta pela metade — que o resumo teria mostrado como se fosse cobertura. Agora há pausa entre lotes e espera crescente no 429. Limite de taxa é regra da fonte: aqui isso significa esperar, não insistir mais rápido.

Os dois mapas do Monitor de riscos ganharam seletor **capitais / todos os municípios**, cada camada com sua legenda, e uma linha-fato dizendo a cobertura de cada variável — sem ela, um mapa com 5.570 pontos e outro com 1.700 pareceriam a mesma coisa.

### O que as fontes recusaram, e o que isso significa

**Probabilidades ENSO (IRI):** o arquivo tabular dá **404**; o host novo que serve os gráficos responde **403** em tudo que não seja a imagem publicada; a QuickLook e a discussão do CPC não trazem tabela no HTML. 403 é bloqueio de acesso real e não se insiste. O parser segue provado por fixture, esperando a tabela voltar.

**Painel de arboviroses do MS:** o portal de dados mudou de endereço e o que publica sobre dengue é **microdado do Sinan** — 83 arquivos —, não a série semanal do painel. Agregar microdado produziria número **nosso**, que pode divergir do painel oficial: é projeto próprio e decisão da editoria, não coleta. A página segue com o InfoDengue, creditado como modelo.

**Painel de excesso de calor do MS:** responde, e recusa, e responde de novo. Medido no mesmo dia: **5.573 municípios** numa consulta, e `200` com corpo vazio em outra, minutos depois. É limite de taxa, não bloqueio — então a descoberta ganhou espera crescente, para a fonte não ficar eternamente em "aguardando primeira coleta" por causa de uma janela de minutos.

### O índice de resposta aparecia com escala em dois lugares e sem escala no terceiro

**O cartão do leitor — o que abre quando alguém digita a própria cidade — não tinha a barra de resposta.** A grade de estados tem, a ficha do estado tem, e as duas usam a rampa fria→quente (Mineral → Argila) que a resposta tem por definição. No cartão, a mesma grandeza aparecia só como número de decretos em texto corrido, ao lado da barra do MARÉ, que é outra rampa e outra coisa. Quem consulta a própria cidade — o leitor mais provável do site — via a metade que não tem escala.

Agora o cartão traz a mesma barra, com a mesma arte e os mesmos números da ficha do estado. Os dois índices nunca se somam (C17), e o relatório em PDF, que é gerado por esse cartão, passou a dizer a mesma coisa que ele.

**E ao pôr os dois lado a lado apareceu uma contradição aparente.** Em Pernambuco o cartão diz "0 decreto(s) reativo(s)" numa linha e "3 de 185 municípios" na barra logo acima. Os dois números estão certos e são de **cadastros diferentes**: a cobertura documentada conta atos de planejamento localizados no banco do Monitor; o índice de resposta conta decretos de emergência no registro federal (S2iD) e nos diários. O cartão passou a dizer isso, em vez de deixar o leitor concluir que um dos dois está errado.

### O que já estava feito, e vale registrar

A varredura municipal de planos **já cobria os 5.571** em nível nacional. O que faltava era a profundidade: o diário municipal consultado, município a município, dentro da janela do ciclo.

**Isso fechou em 25/09: 5.571 de 5.571, zero pendentes.** Foram 3.631 consultas nesta rodada, e o resultado diz mais sobre a cobertura do país do que sobre o Monitor: **3.093 municípios não têm diário indexado** no Querido Diário — não há onde procurar, e isso é lacuna declarada, nunca "nada localizado"; 86 têm diário indexado sem nenhuma edição dentro da janela; 67 têm edições e nenhuma menção aos termos; **167 trouxeram menção**, que vai à fila de leitura humana; e 14 viraram registro de decreto.

## §208 · O que faltava para a credencial chegar, e a variável de fundo que a MUNIC não tem · 24/09/2026

Classe **infraestrutura e verificação de fonte**. Nenhum número público muda.

### O item 1: cadastrar o segredo não ligava nada

A camada de medição do §206 ficou escrita e desligada, esperando credencial. Ao preparar o caminho para a editoria, apareceu o que faltava do meu lado: **nenhum workflow declarava `OPENAQ_API_KEY` nem `INMET_API_TOKEN`**. Cadastrar o segredo no GitHub não faria diferença — o valor não chegaria ao coletor, e a fonte continuaria em `aguardando_credencial` sem ninguém entender por quê. Os dois passaram a ser declarados no passo que roda o `atualizar.py`.

**E uma sonda para não descobrir isso em seis horas.** `scripts/sondar_credenciais.py` responde, em segundos e sob disparo manual, se a credencial chegou ao passo e se a fonte a aceita. Ela preserva a distinção que importa: `ausente` (não há segredo), `recusada` (401, 403, ou 200 com corpo vazio ou "CHAVE INVÁLIDA!" — recusa servida com 200 é recusa), `erro_da_fonte` e `aceita`. Confundir os quatro é o que faz alguém procurar problema no lugar errado. Ela **nunca imprime a credencial**: só o tamanho e os quatro últimos caracteres, que bastam para distinguir "colei a chave errada" de "não colei chave nenhuma" num log público. Treze casos no autoteste, entre eles a prova de que a chave do OpenAQ viaja em cabeçalho e o token do INMET no caminho, e de que nenhum dos dois aparece no relatório.

**As duas credenciais não são a mesma tarefa, e isso estava implícito.** O **OpenAQ** é autoatendimento, conferido na documentação dele: cadastro em `explore.openaq.org/register`, chave em `explore.openaq.org/account`, cabeçalho `X-API-Key`. O **INMET** não tem caminho público documentado para o token: o portal dele não publica manual de API, e o que a carta de serviços oferece para dado de estação é o **BDMEP**, que é aplicativo de descarga com login, não API por requisição. Ou seja, o OpenAQ é questão de minutos; o token do INMET é pedido institucional sem prazo publicado. A sonda diz isso na própria saída, em vez de deixar a diferença escondida.

### O item 2: a MUNIC não tem variável de fundo, e há duas melhores

A camada B supunha que a MUNIC pudesse declarar a existência de fundo municipal de defesa civil. **Não declara.** Medido com o arquivo à vista: das quinze menções a "fundo" no dicionário da MUNIC 2020, todas são de **habitação** (`MHAB16`), **transporte** (`MTRA16`) e **meio ambiente** — nenhuma de defesa civil. E a MUNIC 2024 não tem o bloco de gestão de riscos: as dez abas dela incluem "Evento climático RS", que é restrito a um estado e não serve a indicador nacional.

As duas variáveis mais próximas do que a camada B quer são melhores do que a pergunta original, porque falam de dinheiro e não de estrutura: **`Mgrd225`** — "Há previsão de recursos para ações de proteção e defesa civil na Lei Orçamentária Anual" — e **`Mgrd226`** — "Há outras fontes de recursos para ações de proteção e defesa civil". Ficam **registradas e não coletadas**: publicá-las cria indicador público novo, o que é decisão da editoria (governança §29). O registro em `data/fontes_declarado.json` existe para que a decisão não tenha de refazer a verificação.

### Dois defeitos achados no caminho

**A sonda da MUNIC dizia não rodar fora da Action, e a razão estava errada.** A docstring afirmava que o ambiente de edição respondia `403 host_not_allowed` para os domínios do IBGE. O que ele responde é `CERTIFICATE_VERIFY_FAILED` — a loja de certificados desta máquina Windows não completa a cadeia do `ftp.ibge.gov.br`. Mesmo defeito e mesma correção do `gsc.cemaden.gov.br` no §206: verificar contra o pacote de raízes do `certifi`. Com isso a sonda roda localmente, e foi ela que respondeu o item 2 sem gastar um ciclo de CI. **Nomear a recusa errado custou, aqui, a impressão de que a pergunta não tinha resposta acessível** — a mesma classe de erro que o `CLAUDE.md` registra a respeito de geobloqueio chamado de `robots.txt`.

**A mesma docstring mandava investigar problema já resolvido.** Ela dizia que `declarado_nacional.json` estava vazio desde 02/09 porque a fonte tinha `url: null`. Isso foi resolvido em 20–21/09: a fonte está `ok`, a coluna conferida contra o arquivo, e a camada declarada cobre os **5.570 municípios**, ativada na nota em 21/09. A docstring ficou três dias velha e me pôs a caçar um problema morto; corrigida.

### A editoria aprovou publicar, e a pergunta dela achou fonte melhor

Autorizada a publicação, a editoria perguntou se a MUNIC 2020 era mesmo a mais atual. **Não era**, e a pergunta evitou que eu usasse a pior fonte. O **ICM da Sedec/MIDR** tem, entre suas vinte variáveis, a **número 11 — "Dotação orçamentária (LOA) para proteção e Defesa Civil"**, que pergunta a mesma coisa e é melhor em três sentidos medidos: base de **2026** contra 2020; **binária e sem vazio** nos 5.570, contra cinco valores na MUNIC (`Sim` 968, `Não` 3.265, `-` 1.229, `Recusa` 90, `Não informou` 18 — **24 % do país sem resposta utilizável**); e vem da autoridade de defesa civil, não de um censo de gestão. Ainda por cima o projeto **já baixava** esse arquivo, para a variável 8 do plano de contingência.

**Confirmação cruzada, que é o que dá confiança na troca:** os **968** municípios que disseram "sim" à MUNIC em 2020 têm **todos** 1 na variável 11 do ICM 2026 — nenhuma discordância nesse sentido. As duas perguntam a mesma coisa; uma pergunta melhor.

Medido no arquivo: **2.040 municípios declaram previsão de recursos na LOA; 3.530 declaram não haver.** A figura do dinheiro próprio ganhou seletor de camada — despesa liquidada (o que gastou) e dotação declarada (o que disse que previu) —, com texto-fato e crédito trocando **junto** com a camada, porque fonte errada ao lado de número certo é proveniência falsa.

**Nenhuma fonte centralizada responde "existe fundo".** Nem MUNIC, nem ICM, nem SICONFI: os anexos alternativos do Tesouro vêm vazios e o caminho dos dados abertos do CNPJ não responde no endereço público. Existência de fundo continua dependendo da lei municipal, que é o que os termos do dicionário do §207 servem para achar.

**A trava do peso zero, porque estrutural não basta.** A dotação declarada mora no **mesmo registro por município** que a camada declarada de plano, que pontua a 50 %. Hoje o motor lê apenas dois campos, por nome, então o campo novo não entra — mas isso deixa de valer no dia em que alguém trocar a leitura por "qualquer campo que diga sim". `verificar_financiamento.py` passou a injetar a dotação num município **sem** plano declarado e a exigir que a contagem por UF não mude nem um município. Provado nos dois sentidos: com o motor sabotado de propósito, a trava reprova.

### Três defeitos de código achados por causa disso

**Um mapa inteiro que nunca chegou ao leitor.** Na Defesa civil, escolher "Nível de verificação · todos os 5.571 municípios" **não fazia nada** — e "Natureza · decreto reativo × plano preventivo" também não. A causa: `svg.hidden = false`. Em elemento **SVG**, `hidden` não é propriedade refletida: a atribuição cria uma propriedade JS comum e o **atributo permanece**, e é o atributo que a folha do navegador usa para esconder. Medido: depois do evento, `svg.hidden` era `false`, o atributo continuava lá e o `display` continuava `none`. Quatro camadas de mapa, publicadas e inalcançáveis. Corrigido com `toggleAttribute`, que mexe no atributo e serve para SVG e para HTML.

**E nenhum portão via.** Os de runtime conferem que o SVG tem as 27 UFs desenhadas — não que a escolha do leitor muda o que aparece. `verificar_consistencia_visual.js` passou a percorrer cada `select.seletor`, escolher cada opção e exigir que o conjunto de elementos visíveis **mude**. A invariante é estreita de propósito: vale só para seletor cuja figura tem dois ou mais SVG/canvas, porque seletor que redesenha o mesmo canvas (o comparador da Saúde) ou troca texto (contatos no Proteja-se) muda conteúdo, não camada — exigir troca deles seria acusar comportamento correto. Provado que pega: com o defeito reposto, o portão reprova os dois seletores.

**`pontosDensos` apagava a camada anterior.** Ela remove `path.densos` a cada chamada, então duas camadas densas no mesmo mapa deixavam só a última — em silêncio. Foi o que aconteceu com as três classes de dotação: sobraram 2.040 pontos e desapareceram 3.530, sem erro nenhum. Ganhou parâmetro de classe opcional; sem ele, o comportamento é o de antes e nenhuma página existente muda.

**E o mesmo defeito de certificado, pela terceira vez — agora resolvido no lugar certo.** O `buscar()` de `coletores_base.py` é a função compartilhada por todos os coletores e não usava o `certifi`: a MUNIC falhava com `CERTIFICATE_VERIFY_FAILED` mesmo depois de eu corrigir a sonda. Corrigido lá, uma vez, para todos. As duas fontes da camada declarada passaram a coletar nesta máquina.

**Um quarto defeito, achado ao rodar a suíte, e este é de segurança de dado.** O autoteste do `gerar_painel.py` falhou uma vez com erro transitório de E/S do Windows sobre `data/painel/lista.json` — e a **restauração abortou no primeiro arquivo**, sem tentar os seguintes. A lista **imutável** do painel amostral e os agregados ficaram com `sorteado_em` e `lista_publicada_em` trocados de 02/09 para a data de hoje, e o autoteste reportou apenas "3 falhas", sem dizer que havia mexido em dado publicado. A falha em si não se reproduz em árvore limpa e não vem desta edição (a `main` passa), mas a fragilidade é real: agora cada arquivo é restaurado à parte, com segunda tentativa, e o que não voltar é **nomeado** num erro que manda conferir com `git status`. Mutação de dado publicado não pode sair como falha genérica.

**Teste.** Portão novo (`sondar_credenciais.py --autoteste`), agora 58 na lista canônica. Dois casos novos no coletor da camada declarada (a variável 11 lida à parte da 8, e coluna não pedida que não vira "nao"), a trava do peso zero provada nos dois sentidos, e o portão do seletor provado nos dois sentidos. Estrutura, segurança, figuras, palavras, consistência visual e a sonda da MUNIC verdes.

## §207 · O dinheiro próprio do município: a camada que existe para todos · 24/09/2026

Classe **coleta e páginas**. Peso zero nos dois índices, provado por portão e pelo teste de estresse que apaga a pasta inteira e confere que nenhuma nota muda.

**A precisão de desenho que o pedido delegou.** O saldo do Fundo Municipal de Proteção e Defesa Civil não é dado centralizado: existe só no portal ou na lei orçamentária de cada município, e muitos não têm fundo. Existe, porém, um dado irmão **centralizado para os 5.570**: a despesa na subfunção **06.182 (Defesa Civil)**, que todo município declara ao SICONFI. É por ela que a camada A começa, e é ela que faz o mapa nascer completo enquanto as camadas B e C crescem por amostragem.

**As quatro verificações que o pedido mandou fazer antes, respondidas.** O anexo é o `DCA-Anexo I-E`; a subfunção vem no campo `conta`, como "06.182 - Defesa Civil"; as colunas são empenhada, liquidada, paga e as duas de restos a pagar, e a **liquidada** é a publicada. Não existe consulta em lote — `id_ente` tem de ser o código IBGE exato, e consulta sem ele devolve zero itens —, então são 5.570 chamadas, o que cabe na cadência anual da DCA. O piloto das 27 capitais foi feito antes de generalizar, como o pedido exige.

**O que o piloto das capitais mostrou.** Dezenove capitais com lançamento, sete que entregaram a declaração e **não lançaram nada na subfunção 182**, e uma sem declaração. Mediana de **R$ 1,19 por habitante**. Rio Branco no topo, com R$ 40,93; Belo Horizonte com R$ 13,62; São Paulo com R$ 4,13.

**Três classes de ausência, porque são três coisas diferentes.** `sem_lancamento_182` é o município que entregou a DCA e não lançou nada ali — e isso **não é** ausência de gasto em defesa civil, porque muitos lançam defesa civil em drenagem (17.512), urbanismo (15.451) ou segurança (06.181). `sem_declaracao` é quem não entregou o exercício. `sem_coleta` é quem o Monitor ainda não consultou. Nenhuma das três tem valor por habitante, e o portão reprova se alguma tiver.

**Dois defeitos que o piloto produziu, e que só apareceram porque houve piloto.**

Curitiba liquidou R$ 2.467,02 para 1,77 milhão de habitantes. Arredondado a duas casas, isso virava **R$ 0,00 por habitante** — um valor real apresentado como zero, no mapa e na legenda do mínimo. O dado passou a guardar seis casas, e a exibição diz **"menos de R$ 0,01"**: arredondar para zero um valor que existe é o mesmo erro de fundo das três classes de ausência, só que mais difícil de ver.

E Brasília aparecia como "não entregou". O Distrito Federal **não entrega DCA municipal porque não é município**: declara como estado. Chamar isso de falta de entrega imputaria a ele uma falha que não existe, e o registro passou a carregar a nota da natureza federativa.

**A ressalva que a legenda é obrigada a dizer.** "**Inclui preparação e resposta**" — porque a subfunção 182 soma as duas coisas e a fonte não as separa. Um município que gastou tudo socorrendo uma enchente aparece igual a um que gastou tudo em plano e treinamento. A ressalva está declarada no dado, exigida na página, e o portão reprova se sair de qualquer um dos dois.

**A alternativa em lista não é tabela.** A página de Financiamento não tem tabelas por decisão de 15/09/2026, com portão próprio; a lista da figura é uma lista de definição. Vale registrar que o portão reprovou uma vez por casar a palavra "tabela" dentro de um **comentário** do código, e a correção certa foi reescrever o comentário, não afrouxar o portão.

**Portão.** `verificar_financiamento.py` ganhou a bateria (i): todo registro com fonte, exercício, data e hash; população **sempre** do Censo 2022, nunca a estimativa que o próprio SICONFI devolve; fórmula do R$/hab declarada no dado; conferência de que o valor publicado bate com a fórmula; e a trava central — nenhuma classe de ausência com valor por habitante. Três testes negativos novos: forçar zero num município sem lançamento, trocar a população pela do SICONFI e retirar a ressalva da página. Os arquivos de `municipios/` entraram na varredura de chave de API e de campo de autor, como os demais da pasta.

**O cartão da cidade, a metodologia e os créditos.** O cartão de cada município ganhou uma linha de peso zero com a despesa na subfunção 182 — e três travas: a linha traz a ressalva e o peso declarado, a classe de ausência **nunca vira zero**, e despesa sozinha **não cria cartão** de município que não tinha nada a dizer. A `METODOLOGIA.md` ganhou a **§42**, com as três camadas, as duas limitações da subfunção, as classes de ausência, a exceção federativa do DF e a forma da fonte. Os Pesquisadores passaram a creditar SICONFI/Tesouro e o Censo 2022/IBGE.

**O começo da camada B, feito do jeito que não adivinha.** O dicionário de busca ganhou o grupo **`financiamento_municipal`**, com os oito jeitos de a lei do fundo se escrever — "fundo municipal de proteção e defesa civil", FUMPDEC, FUMDEC, FUNDEC, FMPDC, "fica instituído o fundo". É vocabulário de **recuperação**: serve para achar o ato, nunca para classificá-lo, e o registro segue exigindo número, data e URL da lei.

Quanto à MUNIC, a verificação 7.2 do pedido já tinha resposta parcial no repositório, da sonda de 22/09: o bloco de gestão de riscos e desastres existe nas edições de **2017 e 2020**, não na de 2024 — cuja lista de oito temas não o inclui, e cujo bloco de evento climático é restrito ao Rio Grande do Sul. Ou seja, **a edição mais recente pode não ser a edição certa**, e escolher muda o ano de referência do que o site afirma: é decisão da editoria. A sonda passou a procurar também coluna de **fundo**, para que a próxima rodada da Action responda se ela existe — em vez de eu supor. Ela não roda aqui: os domínios do IBGE respondem 403 no ambiente de edição.

**O que fica declarado.** A camada **C** (quanto há no fundo, por amostragem, capitais primeiro) segue aberta, e com ela o seletor de camadas do mapa. Da camada **B** falta a escolha editorial da edição da MUNIC e a descoberta das leis. A varredura dos 5.570 também: esta rodada cobre as 27 capitais, com fila própria e prioridade baixa, sem disputar com a rotina dos planos.

## §206 · Temperatura, qualidade do ar e os alertas onde eles pertencem · 24/09/2026

Classe **coleta e páginas**. Peso zero em tudo o que entra: nenhum número novo toca nota do MARÉ Legal nem do MARÉ Saúde, e o portão prova isso.

**O que a editoria pediu.** Trazer temperatura, qualidade do ar e alertas climáticos de plataformas públicas, sem construir nada do zero, e organizar pela linha narrativa já fixada: alerta vai para Defesa civil, fenômeno vai para Monitor de riscos, exposição sanitária vai para Saúde.

**Duas fontes novas, ambas sem chave.** `open_meteo_tempo` (Forecast do Open-Meteo, modelos ECMWF, DWD e NOAA) e `open_meteo_ar` (Copernicus CAMS via Open-Meteo), nas 27 capitais, por código IBGE. Três coisas que a sonda com rede real ensinou e que o código registra: várias coordenadas numa chamada devolvem uma **lista posicional**, o lat/lon que volta é o do **nó da grade** e não o pedido (casar por índice, nunca por coordenada), e o ar vem só em série horária — **a média diária é cálculo nosso**, e o dado diz isso.

**As duas naturezas, declaradas no dado.** `estimativa de modelo` e `medição` são rótulos que viajam com o valor, não com a figura, para que nenhuma página possa exibir um sem o outro. A linha de referência de PM2,5 da OMS, 15 µg/m³ de média diária, também está **no dado** — nenhuma página guarda número de referência.

**Hora, não só data.** `consultado_em` das fontes de cadência sub-diária passa a ter `hh:mm` no fuso da redação. Sem isso não havia como distinguir um retrato de quinze minutos de um de vinte e três horas, que é exatamente a diferença que a regra das 36 horas precisa ver. A cadência de quatro vezes por dia já existia e já comitava (`atualizar.yml` às 1, 7, 13 e 19 UTC): o que faltava era a hora.

**A granularidade municipal dos avisos já vinha na resposta, e era jogada fora.** Cada aviso do INMET traz o tipo (`descricao`), a severidade, o início e o fim com hora, e **a lista completa de municípios com código IBGE** — tudo isso era agregado em "total por UF" e descartado. `data/alertas/vigentes.json` passa a guardar por município: 1.177 municípios sob aviso ou alerta na primeira coleta. O hexadecimal que o INMET manda em `aviso_cor` **não é gravado**: cor só vive em `assets/tokens.css`, e o grau do órgão entrou na paleta semântica única, porque a mesma severidade aparece em mais de uma página.

**Um erro de contagem que a camada do CEMADEN embutia.** A camada se chama `alertas_vigentes_siaden` mas devolve também os **encerramentos**, com `nivel` igual a "Cessar" — 17 dos 29 registros da primeira consulta. "Cessar" não é grau de severidade, é o fim de um alerta: contá-lo como alerta em vigor teria publicado 1.192 municípios onde havia 1.177. Os encerramentos ficam registrados à parte, porque alerta encerrado hoje é informação, não ausência de dado.

**Uma falha que parecia fonte fora do ar e era ambiente.** O CEMADEN vinha morrendo com `CERTIFICATE_VERIFY_FAILED`: a loja de certificados desta máquina não completa a cadeia do `gsc.cemaden.gov.br`. Passou a verificar contra o pacote de raízes do `certifi`, que é o mesmo em qualquer máquina. Não afrouxa verificação nenhuma — fonte que recusa de verdade continua recusando. `certifi` era dependência transitiva e agora está declarado e travado, pela mesma regra do `pypdfium2`: a versão do pacote de raízes decide **quais fontes a coleta consegue verificar**.

**Onde cada coisa ficou.** O Monitor de riscos perdeu os dois mapas de alerta e ganhou temperatura e PM2,5 por capital, com alternativa em lista; os alertas viraram uma linha-fato com contagem e link. A Defesa civil ganhou o painel **"Alertas em vigor"**, com mapa por município, gráfico por tipo, lista por UF e o cruzamento com os decretos — e os decretos ganharam bloco próprio, logo depois, para que alerta e decreto fiquem na mesma dobra.

**Dois defeitos achados no navegador, não no código.** Casar município por **nome** deixou os 12 municípios do CEMADEN fora do mapa, em silêncio, porque o CEMADEN escreve em caixa alta: passou a casar por código IBGE, que não tem grafia. E o cruzamento decreto × alerta desenhava **193 pontos e dizia "193 municípios"** — eram 193 eventos sobre 170 municípios, porque um município pode ter mais de um decreto no ciclo. Os dois só apareceram porque a página foi aberta e medida.

**O portão de sinais aprendeu que os sinais não vivem numa página só.** Ele exigia que toda fonte catalogada fosse creditada em `monitor-de-riscos.html`. A invariante não afrouxou — toda fonte continua tendo de ser creditada em alguma página de sinal —, mas a lista de páginas agora existe em vez de ser uma só implícita.

**Teste.** Vinte e oito casos novos no autoteste do coletor, entre eles os quatro achados acima virados em trava: casamento posicional (fixture com coordenada trocada de propósito), "Cessar" não conta como alerta em vigor, hexadecimal não é gravado, e ausência nunca vira zero em nenhum dos dois adaptadores. Estrutura, figuras, legendas, acessibilidade, runtime de sinais, móvel a 390 px e consistência visual verdes.

**A Saúde ganhou calor de saúde, e com ele o pior defeito desta rodada.** O painel "Calor" da `saude.html` mostrava **contagem de avisos do INMET** — que é alerta, não dado de saúde. Ao trocá-lo pela classe de excesso de calor que o próprio MS publica por município, a leitura do código antigo revelou que ele lia `a.lista` e `a.avisos` dentro de `avisos_inmet`, **campos que o agregado por UF nunca teve**. O filtro devolvia sempre lista vazia: o mapa pintava **zero nos 27 estados todos os dias**, em qualquer dia, inclusive com aviso de calor em vigor, e o cartão do Proteja-se dizia "Nenhum aviso de calor vigente" pela mesma razão. Zero silencioso é o pior defeito possível numa figura de risco, porque parece informação. As duas páginas foram corrigidas.

**O painel do MS existe, e recusa.** O dado por município está lá (classe, índice EHF, máxima, previsão a quatro dias), mas não há API: o endereço é função interna do aplicativo, com o caminho carimbado pelo build. O coletor **descobre o endereço a cada rodada e o valida por conteúdo**, não por nome minificado, que também muda a cada build. Medido em 24/09: depois de uma rajada de consultas o endereço passou a responder **HTTP 200 com corpo vazio**, oito vezes em oito, e também no navegador — não é discriminação de cliente. Corpo vazio com 200 é **recusa** (§186, §187), nunca "nenhum município em excesso de calor": sobe como falha, entra como lacuna declarada, e a seção diz ao leitor por que não há número.

**A camada de medição entra pronta e parada, e a razão está declarada.** As duas fontes que trariam *medição* ao lado da estimativa exigem credencial, medido hoje: o **OpenAQ v3 recusa com HTTP 401** sem chave, e o endpoint de dados das **estações do INMET passou a exigir token** — a rota sem token devolve 204 com corpo vazio e a rota com token responde "CHAVE INVÁLIDA!". Bloqueio de acesso real se respeita, sempre.

Os dois adaptadores estão escritos, provados e desligados: a fonte ganha o status próprio **`aguardando_credencial`**, que não é falha de rede nem ausência de dado, e as figuras de temperatura e de ar dizem na legenda "medição: aguardando credencial da fonte", sem desenhar ponto nenhum. A credencial vem do ambiente, nunca do repositório, que é público — e a URL registrada no livro de consultas nunca a carrega, porque ela viaja em cabeçalho justamente para não ficar gravada em arquivo público. **Para ligar a camada, a editoria precisa de duas credenciais gratuitas: `OPENAQ_API_KEY` e `INMET_API_TOKEN`, como segredos da Action.**

Duas coisas que a sonda das estações desmentiu, e que ficam registradas para ninguém repetir: o campo **`FL_CAPITAL` do INMET não serve** para achar capital (vale "N" em 561 estações, nulo em 112, "S" em nenhuma), e **casar por nome de cidade perde cinco capitais**, porque a estação se chama "SAO PAULO - MIRANTE" ou "BELO HORIZONTE - PAMPULHA" e Fortaleza não tem estação com o nome da cidade. A escolha passou a ser por coordenada, com teto de raio, exigindo `CD_SITUACAO` igual a "Operante" — estação em pane devolveria série vazia que pareceria ausência de calor.

**Créditos e metodologia.** A tabela de fontes dos Pesquisadores é gerada do catálogo, então as quatro fontes novas entram sozinhas; passou a mostrar a **licença** (CC BY 4.0 do Open-Meteo e do OpenAQ, com o crédito na forma que eles exigem), a **natureza** do dado e a distinguir "aguardando credencial" de "não localizamos coleta". O `METODOLOGIA.md` ganhou a **§41**, com as duas naturezas, a linha da OMS, o vocabulário do órgão, a regra das 36 horas, as fontes com credencial e o zero silencioso corrigido.

**O que fica declarado.** O `MonitorAr` do MMA está em `monitorar.mma.gov.br`, não no caminho que o pedido trazia — não citado até estar conferido. `data/resposta/quadrantes.json` responde 404 desde antes desta rodada; a página já o trata como nulo. Os 313 municípios do painel e os 5.571 seguem fora da coleta de temperatura e ar: esta rodada cobre as 27 capitais, e ampliar é a segunda fase que o próprio pedido previu.

## §205 · As quatro decisões da direção de arte, e a primeira correção que elas produziram · 24/09/2026

Classe **direção de arte**. O §192 instalou a constituição visual e mediu a auditoria; parou nos passos 1 a 5 do §25, porque os passos seguintes dependiam de quatro pontos em que a constituição contradizia decisão viva do projeto. A editoria delegou as quatro. Aqui estão, com a razão de cada uma.

**1. Fundo branco: fica.** O §1 da constituição lista "excesso de branco" entre o que a seriedade não precisa. A decisão é manter — e a razão vem da própria constituição, no §23: num produto cujo conteúdo é dado, a base branca dá a **maior folga de contraste** às cores que carregam significado, e legibilidade tem precedência sobre preferência de base. O desvio está declarado dentro do documento, com a instrução de não reverter `--bg`. O que a personalidade busca aqui é ritmo, composição e hierarquia — não inversão de fundo.

**2. Paleta: nenhum matiz novo.** O §11 pede profundidade mineral e cita ametista e magenta. A decisão é **não acrescentar matiz**, e ela se apoia no §9 da mesma constituição: *cada cor deve possuir função*, e *não introduza uma nova cor apenas porque ela fica bonita naquela seção*. Aqui toda cor é semântica — chuva, seca, fogo, status do instrumento, ausência de dado. Ametista não tem o que significar, e inventar significado para justificar a cor é o caminho errado. A paleta **já é mineral**: musgo, argila, âmbar, sintético, mineral, bioluz, areia. Profundidade vem pelo §12, luminosidade e transparência dentro da família. Vale ainda a trava do sistema de marca — dez hexes nomeados, e hex fora de `tokens.css` reprova em portão.

**3. Card como arquitetura: decisão tomada, implementação com protótipo.** O §6 afirma que *card não é unidade narrativa* e o §19 marca a grade repetitiva de três colunas como estética de template. A auditoria do §192 mediu: `border-radius` de 6px em **38 de 38** figuras, sombra em 38 de 38, cinco larguras distintas, nenhuma figura ocupando a viewport. A decisão é **acolher a crítica e não executá-la às cegas**: o componente único nasceu de uma auditoria datada de 07/09 e é sustentado por dois portões, e o próprio §19 diz que esses padrões não são proibidos — o problema é usá-los como arquitetura automática. Sair disso é adotar as famílias de composição do §21, o que é desenho, não ajuste de token, e o `CLAUDE.md` exige protótipo à vista da editoria antes de qualquer merge visual. Fica como a próxima rodada, com capturas.

**4. Papéis tipográficos: corrigido agora, e a auditoria achou um defeito real.** O §13 pede diferenciação clara entre título, legenda, nota e fonte. Medido no `base.css`: **`.figura-sub` e `.fonte-figura` eram tipograficamente idênticas** — mesma família, mesmo tamanho, mesma entrelinha, mesma cor. O §11 da governança editorial exige quatro funções separadas e **proíbe comprimi-las**; pela forma, o leitor não distinguia a legenda do crédito.

A correção segue o §14, que diz que hierarquia não é só tamanho: a legenda passa a **peso médio**, a fonte fica em regular. Mesma cor, mesmo tamanho, peso diferente — o que preserva a escala fixa de oito degraus e **não toca em contraste**, já que cor e tamanho não mudam. É a menor intervenção que resolve a confusão, e é o tipo de coisa que só aparece quando se mede em vez de olhar.

**O que fica declarado.** Os passos 9 a 11 do §25 — redesenhar páginas representativas, validar, propagar — dependem da decisão 3 e de protótipo mostrado. A dívida da lista canônica de categorias, aberta no §202, segue aberta. E o teste de personalidade do §26 só faz sentido depois do redesenho, não antes.
## §204 · O sistema de marca entra, com a voz subordinada à governança editorial · 24/09/2026

Classe **design e governança**. Nenhum número muda. Nenhum texto público foi reescrito.

**O que entra.** O sistema de marca pessoal — paleta, tipografia, regras visuais — passa a viver no `CLAUDE.md`, com a skill `marca-pessoal` instalada. A auditoria mostrou que **a marca já estava aqui**: o `tokens.css` declarava, hex por hex, os dez valores da paleta, e as três famílias tipográficas já eram Fraunces, Archivo e Archivo Narrow. O trabalho foi de edição e elevação, não de recriação — como o próprio sistema de marca manda.

**O que mudou de fato, e é pouco de propósito.** O display estava em **Fraunces 400** e o peso 300 nem era carregado; passa a 300 em todas as dezoito regras, com o itálico 300 no carregamento. O versalete de dado vai de `.06em` a **`.12em`**. Dois pontos de bold no display que o carregamento novo teria quebrado: o cartão em canvas do Proteja-se desenhava Fraunces 600, e o número do selo nos mapas não declarava peso. E `--bioluz`, que a marca define como metade da sua tensão característica, estava **declarado e sem uso em lugar nenhum** — entra na seleção de texto, e só ali: é o detalhe que acende sem preencher área grande, e é interface pura, sem significado de dado.

**Um defeito de contraste que a varredura da marca encontrou.** `.kicker`, `.selo`, `.figura-cat` e `.prazo-espera .k` usavam sintético puro em texto de 12px: **4,39:1**, abaixo do AA de 4,5 que a própria marca manda conferir. Passam ao sintético escurecido que o site já usava como cor de texto — 5,60:1, mesma família, nenhum hex novo. Defeito pré-existente, achado por olhar com a régua certa.

**O fundo continua branco, e isso é desvio declarado.** A Seção 3 do sistema de marca manda "base sempre escura ou osso". A editoria decidiu em 05/09/2026, e reafirmou em 24/09, que o fundo deste site é branco. O desvio está anotado em dois lugares do `CLAUDE.md` — no alto da seção e na própria regra — com a instrução explícita de **não reverter `--bg`** por fidelidade à marca.

**A voz entra subordinada, e essa é a condição.** O sistema de marca pede voz "provocadora, poética, espirituosa". A `AI_EDITORIAL_NARRATIVE_GOVERNANCE.md`, instalada no §189 com precedência declarada, pede o oposto para conteúdo público: **clara, precisa, sóbria**, não promocional (§16), sem dramatização nem frase de impacto (§24), sem dizer ao leitor o que pensar (§20).

As duas ficam, com a fronteira escrita nos dois arquivos: a voz da marca vale para material de marca; **título, legenda, nota, fonte, tooltip, cartão e prosa de página seguem a governança, sempre**. Não é concessão — é o que o próprio sistema de marca decide no fim da sua Seção 7: *"dúvida entre mais bonito e mais rigoroso: escolher o que preserva o rigor visível"*. Num monitor de evidências, o rigor visível **é** o produto. E o portão 19 já reprovava juízo em texto de figura, de modo que a colisão nem chegaria ao ar — o que muda é que agora ninguém precisa descobrir isso por tentativa.

**O que segue fora.** Nenhuma peça-manifesto foi acrescentada e nenhum slogan entrou no site: o rodapé é da Futura Evidence Lab, e o próprio sistema de marca proíbe copiar uma identidade na outra. Nenhuma imagem foi inventada. Nenhum marcador `[PREENCHER]` ficou pendente, porque nenhum bloco sem substância foi criado.

**Teste.** Portões de estrutura, móvel e consistência visual verdes; contraste medido com zero elementos reprovando em `index` e `saude`; overflow horizontal zero em 1280px e em 375px.

## §203 · A leitura dos 82, e os quatro defeitos que a exigência de citar denunciou · 24/09/2026

Classe **coleta e instrumento**. Nada aplicado: `classificar_planos_municipais.py` escreve um arquivo de revisão, e a promoção é R7.

**O que foi feito.** Dos 122 planos municipais no banco, **82 têm texto preservado**. Cada um foi lido por um classificador que propõe a classe da escada do §202 e **é obrigado a citar o trecho que sustenta a proposta**. Resultado: **8 propostas e 74 abstenções**.

Oito de oitenta e dois parece pouco. É o número honesto, e chegar a ele custou quatro correções — todas descobertas pela mesma exigência, a de citar.

**Defeito 1: o sinal vinha da prosa do corpo.** A primeira versão varria o texto inteiro. Vitória saiu como "recorrente" por uma frase sobre óbitos *"computados todos os anos, no período chuvoso"*, e três PLANCONs capixabas saíram como "readaptado" por *"manter registro **atualizado** sobre danos humanos"* — uma instrução **dentro** do plano, não prova de que o plano foi atualizado. O tipo de um instrumento se declara no título e na abertura, não numa linha da página 40. É a régua do §182 (texto declarativo) e a do §180 (o ato tem de se apresentar como tal). Passou a ler só a **zona de identidade**.

**Defeito 2: o robô classificava a própria descrição.** A correção anterior incluiu na zona de identidade o campo `documento` do banco — e **71 de 82** viraram "readaptado", porque esse campo diz "PLANCON edição 2025". Só que esse rótulo foi escrito **pelo Monitor**, não pelo documento. O robô concordava consigo mesmo e chamava isso de evidência. O campo saiu da pontuação e ficou só como contexto para o humano.

**Defeito 3: o ano do ciclo alimentava duas classes ao mesmo tempo.** "2026/2027" pontuava para *novo* e era exigido por *readaptado*, então "atualização do plano para 2026/2027" empatava consigo mesma e caía em abstenção. Quem distingue criar de atualizar é o **verbo**, não o ano — o ano passou a valer pouco, e "El Niño" e "ENOS", muito.

**Defeito 4, o pior: `enos\b` casava dentro de "m<u>enos</u>".** Sem limite de palavra à esquerda, a sigla pegava qualquer palavra terminada em "enos" — menos, terrenos, plenos. Foi assim que um parágrafo sobre ocupação de moradia em Afonso Cláudio recebeu três pontos de "dedicado ao El Niño". Sigla curta sem âncora pega pedaço de palavra comum, e **o erro só apareceu porque a proposta é obrigada a citar**: a citação não tinha nada a ver com El Niño, e foi isso que denunciou.

**Uma correção de método, no meio do caminho.** A citação guardava o **primeiro** sinal que casava, não o mais forte — de modo que o revisor podia conferir uma frase fraca enquanto o ponto vinha de outra. Citação que não corresponde ao que pesou é pior do que citação nenhuma: faz o humano conferir a frase errada e concordar com uma conclusão que ninguém verificou. Passou a mostrar o sinal de maior peso.

**A régua de abstenção.** Sinal ausente, ou duas classes com força parecida (margem menor que 2), devolvem `indeterminado` — e `indeterminado` **mantém o registro onde está, valendo 1,00**. O robô não classifica no escuro, e "não sei" nunca vira nota. Das 82 leituras, 74 terminaram assim, e isso não é falha do instrumento: é ele funcionando.

**O que as 8 propostas dizem.** Cinco `plano_readaptado` e três `plano_recorrente`, todas no Espírito Santo — que é onde há repositório estadual e, portanto, onde há documento preservado para ler. As três recorrentes se sustentam em texto do próprio documento: *"sendo revisado anualmente"* em Castelo e Santa Leopoldina, e *"PMPDC — Vitória-ES Verão 2024/2025"* em Vitória. Nenhuma foi aplicada.

**Onze casos no autoteste**, entre eles os quatro defeitos acima virados em trava: prosa de corpo não classifica, rótulo do banco não pontua, "menos" não casa com ENOS, e abstenção não inventa citação.

**O limite, declarado.** Sobram **40 planos sem texto preservado** — para esses não há o que ler, e nenhuma proposta é possível sem antes extrair o documento. E o classificador continua sendo um proponente: ele lê a abertura, não o plano inteiro, e um documento cujo título diz "verão" mas cujo corpo institui resposta ao El Niño existe. Por isso cada proposta carrega a citação e a classe concorrente — para que a leitura humana confira a **evidência**, e não a conclusão.

## §202 · A escada dos estados chega ao município · 24/09/2026

Classe **governança com efeito em nota** — mas de efeito **zero na aplicação**, e isso é o ponto.

**A assimetria que existia.** O componente estadual distinguia, desde a v3.0, o que o instrumento **é**: `NOVO` 100 para o criado para o ciclo, `READ` 65 para o preexistente reativado por ato datado, `VIG` 45 para a ativação recorrente anual — plano de verão, operação sazonal que mobiliza o sistema todo ano, com ou sem El Niño. No município não havia nada disso: existia `plano`, e pronto. Um Plano de Contingência escrito para o El Niño 2026/2027 valia exatamente o mesmo que uma Operação Chuva que roda desde sempre.

**A emenda.** `CRED_POP` ganha `plano_novo` 1,00 · `plano_readaptado` 0,65 · `plano_recorrente` 0,45 — as mesmas proporções da escada estadual, porque consistência aqui é aplicar a mesma régua a objetos diferentes, não inventar uma segunda. Registrada como **C28** na corrente de erratas do congelamento, pelo mesmo instrumento do §196: decisão da editoria emendando o C6, não errata.

**Duas decisões de desenho, declaradas porque mudam o que o número significa.**

A primeira: **`plano` continua valendo 1,00** e passa a significar *localizado, tipo não determinado*. Não se desconta município porque **nós** ainda não lemos o documento dele. É a regra da casa desde a v2.2.4 §2.1 — ausência de verificação não é ausência de documento —, e ela vale aqui com força: lacuna nossa não pode virar nota deles.

A segunda: **`plano_antigo` fica em 1,00**. O §196, de hoje de manhã, decidiu que plano vigente de ciclo anterior conta integral. Sob a escada, ele cairia para 0,45. Reverter uma decisão da editoria por reinterpretação, no mesmo dia, seria trocar o juízo dela pelo meu — então ele só se move com o documento na mão mostrando que é rotina recorrente, e aí vira `plano_recorrente`, com a prova junto.

**Efeito medido: nenhum.** Média nacional 46,57 antes e depois; nenhuma UF muda; nenhum registro foi reclassificado. A escada foi **instalada**, não aplicada.

**A consequência, dita antes de acontecer.** Esta escada tende a **baixar** o índice conforme os documentos forem lidos, não a subir. Dos 122 planos municipais no banco, **82 têm texto extraído** — dá para classificar lendo, que é como se faz aqui. Quando um "Plano Preventivo de Chuvas de Verão" for lido e classificado como recorrente, ele cai de 1,00 para 0,45. É o resultado correto: rotina sazonal anual não é resposta ao El Niño. E chega aos poucos, na velocidade da leitura, cada passo por R7.

**O vocabulário estava duplicado em dez lugares.** Acrescentar três categorias exigiu tocar o motor, a correção C10, as categorias aceitas de contribuição pública, o rótulo humano dos feeds, a paleta dos mapas e quatro arquivos de interface — porque não existe uma lista canônica de categorias, existem dez cópias. Todas foram ligadas nesta entrada; a lista única fica declarada como dívida, e é o tipo de coisa que o §30 da direção de arte chama de corrigir na origem.

**Uma trava que aprendeu a distinguir vazio de esquecido.** O portão do congelamento exigia `efeito_por_uf` preenchido em toda errata — e reprovou esta, cujo efeito é genuinamente zero UF. Mas `{}` vazio significa duas coisas opostas: *nenhuma UF foi afetada* e *ninguém preencheu*. O portão passou a aceitar o vazio **apenas quando o efeito nacional corrobora** com `ufs_afetadas = 0` explícito; sem a corroboração, continua reprovando. Verificado ao vivo nos dois sentidos.
## §201 · Ausência declarada pelo órgão: a distinção que faltava, e a resposta do MT na fila humana · 24/09/2026

Classe **esquema de dados e ingestão de evidência**. Nenhum número muda. Nada entra no banco: a resposta de LAI vai para arquivo de revisão, e a promoção é R7.

**A distinção, que vale para todos os estados.** O teto público de ausência é a espinha dorsal deste projeto: nunca se diz "não existe", diz-se "não localizamos até o corte". A regra protege contra negar a existência de um documento que talvez só não tenhamos encontrado. Mas ela cobrava um preço que ficou visível agora: quando o **órgão competente declara formalmente que o instrumento não existe**, o Monitor era obrigado a relatar isso com a mesma frase tímida de quando a busca apenas falhou. **As duas coisas não são a mesma.** Uma é lacuna nossa, de alcance. A outra é lacuna deles, confirmada na fonte.

`data/ausencia_declarada.json` passa a guardar a segunda, com órgão, data, canal, escopo e o ponteiro para o registro interno — **nunca o texto da resposta**, que por regra editorial não entra neste repositório. O portão `scripts/verificar_ausencia_declarada.py` (o **56º**) impede que o arquivo vire porta dos fundos para afirmar inexistência sem lastro: exige fonte nomeada e data em todo item, exige que cada um declare o **efeito no índice** explicitamente, recusa UF fora das 27 e escopo repetido, e limita o tamanho do resumo — porque aqui se guarda o fato, não a carta. Seis casos no autoteste, cinco deles negativos.

**Efeito no índice: nenhum, nos dois casos registrados.** Quem não tem instrumento já contava zero. O que muda é o que o Monitor pode afirmar, e com que fonte.

**Mato Grosso, e uma leitura que quase saiu errada.** A Defesa Civil de MT declarou que **não existe plano estadual de contingência**. Lido depressa, isso parece contradizer a classificação de MT, que é `NOVO`. Não contradiz: o instrumento pelo qual MT é classificado é o **Plano de Combate a Incêndios do 2º semestre de 2026 (Decreto 2.015/2026)**, com a Sala de Situação Central como estrutura. A declaração é sobre um documento **diferente** do que pontua, e está registrada com essa ressalva no próprio item.

**O que veio do MT, e para onde foi.** `data/mt_lai_revisar.json`, arquivo de revisão para leitura humana, com quatro blocos: 6 municípios com plano vigente **declarado pelo estado** (sem número nem data do ato — o órgão remete o endereço a cada município, então é declaração, não documento); 8 com plano em elaboração e data prevista, que **não pontuam**; a ausência declarada do plano estadual; e 3 decretos homologados, com número e data.

**O cruzamento do item 4 deu achado.** MT tem **zero** eventos de resposta no banco — está entre as oito UFs sem nenhum (AP, DF, ES, MT, PA, RJ, RR, TO). Os três atos que o estado homologou não vieram pelo S2iD. A divergência entre a homologação estadual e o que o S2iD indexa é achado, não erro a silenciar. E há uma distinção de publicação que vale registrar: **o decreto é ato público** — número, data e município podem ser publicados; a carta da LAI, não.

**A ressalva de cobertura, e uma divergência de denominador.** Seis planos é número baixo, e a hipótese mais provável é que o estado conheça apenas os planos que lhe foram comunicados — a própria resposta remete o endereço de cada plano ao município. Fica registrado como **declaração estadual com cobertura possivelmente parcial**, e o complemento **não** vira "municípios sem plano". Anotada também uma divergência que apareceu na conferência: `municipios_ibge_referencia.json` traz **142** municípios em MT, sem nome nem código repetido, e o handover fala em **141**, que é o número publicado pelo IBGE. Nenhum dos dois é usado como verdade até a conferência; proporção em texto público fica suspensa.

**Reverificação com data.** `data/reverificar.json` guarda os 8 municípios em elaboração com a data a partir da qual voltar a olhar. O limite está escrito no próprio arquivo: **ainda não há consumidor automático** — é lista de trabalho legível por máquina, para a data não se perder num documento de handover. Ligar a um coletor é trabalho declarado e não feito.

**O pedido de LAI ganhou recorte.** Goiás recusou pedido por genérico, invocando o art. 11 da Lei estadual 18.025/2013. Os dois modelos passam a trazer delimitação **temporal** (atos vigentes ou editados entre 29/06/2026 e 31/12/2027) e **espacial** (âmbito estadual e municípios da UF), com a UF interpolada e não literal — travado por autoteste. Sem o recorte, a negativa vem sem chegar ao mérito e o prazo da LAI se perde inteiro.

**Uma mensagem que mentia.** O gerador anunciava "56 pedidos gerados em `docs/lai/`" enquanto escrevia no registro privado, fora deste repositório. Agora anuncia o diretório real. O texto dos pedidos nunca esteve no repositório público, e a mensagem sugeria que estivesse.

## §200 · O peso que contradizia a regra nova, no canto onde ninguém olha · 24/09/2026

Classe **coerência interna**. Nenhuma nota muda, nenhuma média muda.

**O achado.** Conferindo a `main` depois do merge do §196, apareceram **dois** valores para a mesma coisa no motor: `CRED_POP["plano_antigo"] = 1.0`, que é o crédito de verdade, e `PESO_DOC["plano_antigo"] = 0.7`, quatro dezenas de linhas acima.

**Por que passou despercebido.** No `recalcular_mare.py` o `PESO_DOC` é usado só como **conjunto de pertinência** — `sum(v for k, v in c.items() if k in PESO_DOC)`, onde o `v` vem do contador e não do dicionário. Os valores não entram na conta, e o próprio comentário do arquivo diz isso. Mas o `analise_sensibilidade.py` **usa os valores**, em `sum(rm.PESO_DOC[k] * v ...)`, para calcular `teto_ativo` — a checagem de quais UFs estourariam o teto de 100% de cobertura. Com 0,7 onde o crédito real é 1,0, essa checagem **subestimava**.

**Efeito medido:** nenhum. `teto_ativo` continua vazio antes e depois, e as 27 notas são idênticas. A correção não muda o que o site publica — muda o que o código afirma.

**Por que corrigir mesmo assim.** Um número escrito no motor que contradiz a regra vigente é uma armadilha datada: a próxima sessão lê `plano_antigo: 0.7`, conclui que plano anterior vale menos, e decide alguma coisa a partir disso. Vale igual desde o §196, e agora está escrito igual nos dois lugares, com o motivo ao lado.

## §199 · A ficha da Base dos Dados não substitui a fonte, mas entregou o host que faltava · 24/09/2026

Classe **investigação de fonte**. Nenhum dado novo entra; o que entra é uma sonda de diagnóstico e o registro do que foi medido.

**O que a editoria trouxe.** A ficha do InfoGripe na Base dos Dados, com o conjunto `736ad69a…`.

**Por que ela não resolve o problema do §198, dito sem rodeio.** A própria ficha declara: *"estes dados não passaram pela metodologia de tratamento da Base dos Dados"*; **possui dados estruturados: não**; **tem API: não**; e a **cobertura temporal é 2010–2020**. É uma entrada de catálogo que aponta para a fonte original — não uma tabela tratada e consultável. O MARÉ precisa da série **semanal de 2026** com canal endêmico; 2010–2020 não cobre o ciclo, e sem API nem estrutura não há de onde ler.

**O que ela entregou de valioso.** O botão "Acessar fonte original" aponta para **`info.gripe.fiocruz.br`** — com ponto entre `info` e `gripe`. O §198 havia testado `infogripe.fiocruz.br`, sem o ponto: **hosts diferentes**, e o certo não tinha sido tentado. O achado é da editoria, não meu.

**E o que a medição fez com ele.** `info.gripe.fiocruz.br` resolve em DNS (157.86.198.43) e **não responde** desta máquina: tempo de conexão esgotado, inclusive com um **navegador real** — o que exclui problema de cliente, de cabeçalho ou de TLS. Junto com `infogripe.fiocruz.br` e `gitlab.procc.fiocruz.br`, são três hosts da Fiocruz inalcançáveis daqui, em três sub-redes distintas, enquanto `gitlab.fiocruz.br` e `www.fiocruz.br` respondem normalmente. Não dá para concluir daqui se o serviço está fora do ar ou se a rota é que não fecha.

**A saída, que é usar o CI como instrumento.** Quando todos os CSV falham, a rodada passa a **sondar o sítio oficial** e a registrar no diagnóstico o que ele respondeu — status, tamanho, se é tela de login, e os primeiros caracteres. É **diagnóstico, nunca coleta**: a sonda não tenta interpretar nada como dado, e o autoteste trava isso, conferindo que o que ela devolve não carrega mais do que tamanho, veredito de login e início do conteúdo. O runner roda em outra rede; se ele alcançar o host, a próxima rodada agendada nos diz — e aí o caminho do CSV vira uma pergunta respondível. Fazer o CI descobrir o que a máquina de edição não alcança é barato. Chutar um caminho de CSV seria inventar, e o §6 proíbe.

## §198 · O InfoGripe fechou: a fonte de SRAG e síndrome gripal passou a exigir login · 24/09/2026

Classe **correção de coletor e de diagnóstico**. Nenhum número muda: as duas séries já estavam em lacuna declarada, e continuam.

**O sintoma.** O diagnóstico do coletor, gerado em 23/09, dizia que o host respondeu e que o cabeçalho da planilha era `['<!DOCTYPE html>']`. Lido assim, parece defeito de *parser* — CSV que veio malformado. Não era.

**O que foi medido em 24/09, host a host.** `gitlab.fiocruz.br` responde **HTTP 200 com a tela de login do GitLab** (`devise-layout-html`, a classe que o Devise põe no `<html>` da página de entrada), e a API do projeto, em `/api/v4/projects/marcelo.gomes%2Finfogripe`, responde **404**. `gitlab.procc.fiocruz.br` e `infogripe.fiocruz.br` estão inacessíveis, com tempo de conexão esgotado. **O repositório do InfoGripe deixou de ser público.** Não é endereço que mudou: é autenticação que passou a ser exigida — e login é recusa que se respeita (§170), como o muro de robô do §186. Não se contorna autenticação.

**A correção.** `parece_pagina_de_login()` reconhece a tela de entrada antes de o coletor tentar ler o conteúdo como planilha, e a rodada passa a registrar *"repositório passou a exigir autenticação"* em vez de um cabeçalho estranho. A diferença importa para quem vier depois: um diagnóstico manda caçar defeito de código; o outro manda procurar fonte nova ou abrir pedido de acesso. Cinco casos no autoteste, incluindo os dois que **não** podem disparar — CSV legítimo e HTML que não é login.

**Diferença de ambiente, declarada.** Numa máquina Windows o `gitlab.fiocruz.br` nem chega a responder: o servidor manda cadeia TLS incompleta (*"unable to get local issuer certificate"*) e o repositório de raízes do sistema não a fecha sozinho. O runner do CI, com o repositório de raízes do Linux, alcança o host e recebe a tela de login. Rodando local, o coletor registra falha de rede; rodando no CI, registra a recusa. As duas são verdade, e o diagnóstico grava qual delas ocorreu — o que evita que a próxima sessão ache que uma das duas está errada.

**O que o leitor vê, e por que está certo.** `srag_serie.json` e `sg_serie.json` **não existem**, e a página de saúde trata ausência de arquivo como lacuna declarada. O site não mostra dado velho: mostra que não tem. É a regra funcionando — mas agora com a causa nomeada, em vez de silêncio.

**O que fica declarado e não feito.** Procurar fonte pública equivalente. O SIVEP-Gripe no OpenDataSUS é microdado, uma esteira inteiramente diferente da série semanal com canal endêmico que estas duas figuras usam — não é substituição de URL, é coletor novo. Fica como trabalho nomeado, não como pendência escondida.

## §197 · A descoberta renderizada dos repositórios estaduais: dois estados guardam o plano municipal atrás de login · 24/09/2026

Classe **coleta**. Nenhum número muda; um documento estadual entra preservado e um candidato a reclassificação entra na fila R7.

**Por que renderizar.** O §195 sondou 23 UFs nos três caminhos que SE e ES usam e registrou o resultado com o limite à vista: aquilo provava ausência *nos caminhos sondados*, não ausência de repositório. O §164 já havia ensinado que evidência atrás de JavaScript é invisível para busca textual. As 21 UFs sem parser tiveram então a página inicial aberta em **navegador real**, com a navegação lida em busca de seção de planos municipais.

**Três candidatos, e os três dizem coisas diferentes.**

**Pará — o achado que muda o diagnóstico.** `plancon.defesacivilpa.com.br` é o **SISTEMA PLANCON** do CBMPA com a CEPDEC: *"Gestão municipal de planos de contingência — cadastro, revisão, aprovação e exportação"*. E fica **atrás de login**. Os planos municipais do Pará existem, são geridos pelo estado, e não são públicos. É exatamente o desenho do SISDC do Paraná, que o §186 já havia encontrado. **Dois estados guardando plano municipal atrás de autenticação é padrão, não acaso** — e padrão muda a estratégia: o caminho para essa cobertura é pedido de LAI, decisão da editoria, não raspagem. Login é recusa que se respeita (§170), e ela foi respeitada.

**Rio de Janeiro — instrumento estadual, não repositório municipal.** A seção "Para Municípios" reúne 38 PDFs, e a leitura mostrou que são **do estado**: o *Plano de Contingências do Estado do Rio de Janeiro 2025/2026* (PLACON) e os planos setoriais de CGE, DRM, GSI, INEA e PGE. O PLACON foi preservado com hash (45 MB). O índice registra RJ hoje como `VIG`, e um plano estadual datado de 2025/2026 com anexos setoriais é matéria de reclassificação — que é **R7, da editoria**, não automática. Entra na fila.

**Paraná** confirmou o que já se sabia, agora por navegador: sistema, não repositório.

**As outras dezoito não têm seção de planos municipais na navegação.** Isso agora é uma afirmação mais forte que a do §195 — foi lido o que o navegador monta, não o que um caminho adivinhado devolve —, e continua sendo o que é: ausência no que foi examinado. Repositório em página interna não linkada da home escapa.

**O saldo do pedido "estenda às outras UFs".** Ele não produziu parsers novos, e é importante dizer por quê em vez de registrar um número vazio: das 25 UFs com domínio resolvido, **duas** publicam repositório de planos municipais (SE e ES, que já tinham parser), **duas** o mantêm em sistema fechado (PR e PA), **uma** publica instrumento estadual na seção dos municípios (RJ) e as demais não publicam repositório onde foi procurado. O canal não cresce por engenharia — cresce por LAI, ou não cresce.

## §196 · Plano vigente é plano vigente: a emenda ao C6 e o fim do eixo "antes e depois" · 24/09/2026

Classe **governança com efeito em nota**. Duas UFs mudam, nenhuma troca de faixa, e a média nacional vai de **46,43 a 46,57**.

**A decisão da editoria.** A régua da cobertura municipal deixa de perguntar **quando** o plano foi publicado e passa a perguntar se ele **existe e está vigente**. `CRED_POP["plano_antigo"]` vai de **0,6 para 1,0**. O boletim de 29/06/2026 abre o ciclo — não transforma um plano de contingência em vigor em meio plano. E a expectativa declarada, de que instrumento publicado depois do boletim tenha sido adaptado ao risco do ciclo, é outra coisa, que o índice **não mede hoje** e que fica registrada como tal, não como suposição embutida no número.

O tipo do instrumento — novo do ciclo, readaptado, vigente-recorrente — continua distinguido no banco e visível no site. Ele passa a ser **descrição**, e deixa de ser **desconto**.

**Efeito declarado, medido antes de aplicar:**

| | antes | depois |
|---|---|---|
| RS · cobertura populacional | 28,5 | 30,6 |
| RS · nota | 64,5 | **65,2** |
| SE · cobertura populacional | 54,3 | 63,1 |
| SE · nota | 61,4 | **64,4** |
| média nacional | 46,43 | **46,57** |

**Nenhuma outra UF muda; nenhuma troca de faixa.** Só duas se mexem porque apenas onze municípios estão hoje na categoria — o que também diz o tamanho real do ganho: ele virá da coleta, não da régua.

**Sobre o instrumento, porque isso importa mais que o número.** Isto **não é errata**. A Errata C26, de 23/09, diz em letra de forma que *nenhuma errata autoriza mudança de regra*, e continua valendo. O que aconteceu aqui é a editoria **emendando a própria regra**, que é prerrogativa dela e de mais ninguém. A corrente de hashes do congelamento foi usada para tornar a mudança **auditável** — entrada **C27**, com motivo, UFs afetadas, efeito em pontos e os hashes anterior e novo encadeados —, e não para disfarçar mudança de regra de correção de dado. Um projeto que confunde as duas coisas perde o direito de dizer que congelou alguma coisa.

**O vocabulário público, que era onde o "antes e depois" de fato morava.** A mesma categoria era descrita de **três formas** no site, duas delas contraditórias: "Plano de ciclos anteriores ainda vigente" na inicial, "Plano desatualizado" em Pesquisadores e em três arquivos de JavaScript, "plano de edição anterior localizado" em Prefeituras. Um plano vigente não é um plano desatualizado. Os seis rótulos passam a dizer **"Plano vigente, de ciclo anterior"**.

## §195 · O vocabulário do plano vigente, e o mapa de repositórios estendido às 27 UFs · 24/09/2026

Classe **correção de texto público e de cobertura de fonte**. Nenhum número muda nesta entrada.

**Onde o "antes e depois" realmente morava.** A mesma categoria — plano de ciclo anterior ainda em vigor — era descrita de **três formas** no site, duas delas incompatíveis entre si: *"Plano de ciclos anteriores ainda vigente"* na inicial, *"Plano desatualizado"* em Pesquisadores e em três arquivos de JavaScript, *"plano de edição anterior localizado"* em Prefeituras. Um plano vigente não é um plano desatualizado, e o leitor que passasse por duas páginas via o projeto se contradizer sobre o mesmo dado. Os seis rótulos passam a dizer **"Plano vigente, de ciclo anterior"** — em `index.html`, `pesquisadores.html`, `defesa-civil.js`, `index.js`, `pesquisadores.js` e `prefeituras.js`. É o §22 da governança editorial aplicado onde ele mais importa: o mesmo conceito, o mesmo nome, em todo o site.

**O canal que mais rende, e o que a sondagem achou.** O repositório estadual de PLANCONs tinha parser para **duas** UFs — SE e ES — e sozinho já deu **84 planos municipais**, o dobro do que o canal inteiro de diários municipais produziu (41). A editoria pediu estender às outras.

As 23 UFs restantes foram sondadas nos três caminhos que SE e ES usam (`/planos-de-contigencia`, com a grafia sem o segundo "n" que ambos adotam; `/planos-de-contingencia`; `/plancon`), com o cliente identificado e o `robots.txt` respeitado (§185). **Seis responderam, e nenhuma é repositório de planos municipais:**

- **MS** entrega 293 kB sob o título "Planos de Contingência (PLANCON)" — e não lista um único plano municipal: só a Comissão Estadual e botões de compartilhamento. Página informativa, não repositório.
- **MG, TO e PI** respondem sob aviso de período eleitoral — o padrão que o §182 já havia isolado: o que está suspenso é a seção, não o sítio. Ficam para reconferir depois de 25/10.
- **SP** devolve a página institucional; **AL**, 349 bytes vazios.

As outras treze (AC, BA, CE, DF, GO, MA, MT, PA, PB, PE, RJ, RN, RR) não responderam em nenhum dos três caminhos.

**O limite, escrito junto com o achado.** Isso prova ausência **nos caminhos sondados**, não ausência de repositório. Repositório sob outro endereço, ou atrás de JavaScript, escapa desta sonda — e o §164 já ensinou a esta casa que evidência atrás de JavaScript é invisível para busca textual. A descoberta renderizada é o passo seguinte, e fica declarada como pendente e não como concluída. É a mesma distinção do §194, aplicada agora ao que o próprio Monitor ainda não procurou direito.

---

## §194 · A coleta volta a rodar de duas em duas horas, e o log passa a dizer a verdade sobre a fonte · 24/09/2026

Classe **operação e honestidade de registro**. Nenhum número do índice muda.

**Por que a coleta parava.** Três causas, todas medidas:

1. **Fila alheia.** `busca_web_cadencia.yml` dividia o grupo de concorrência `atualizar-dados` com o `atualizar.yml`, que leva de **1h43 a 2h43** por execução. Enquanto ele rodava, a busca de 2h ficava na fila — e execução pendente é cancelada quando a seguinte chega. A coleta parava por atividade que não era dela. Agora ela tem grupo próprio e não espera por ninguém; as outras esteiras seguem rodando e visíveis.
2. **O freio de mão.** A regra de fase caía para 4×/dia assim que `ciclos_completos` chegava a 1 — e chegou em 24/09. A busca passou a **pular oito das doze rodadas do dia**, silenciosamente, porque pular conta como execução bem-sucedida. `ciclos_completos` continua sendo gravado e continua servindo de relatório de cobertura; o que ele não faz mais é decidir se a rodada acontece.
3. **Rodada perdida no push.** Era uma tentativa só de `rebase` e `push`: se a `main` andasse no intervalo, a rodada inteira era descartada. Agora são seis tentativas com espera crescente, **nos dois workflows** — porque separar os grupos significa que os dois passam a commitar em paralelo, e a proteção tem de estar no push, não na fila.

**Os termos, de três para nove.** Cada acréscimo veio do **nome real** de um plano já no banco, nunca de palpite: `PLANCON`, `PLAMCON`, `PLACON`, "plano operacional", "plano preventivo", "plano de enfrentamento". Medido contra os 134 planos conhecidos, `"plano de ação"` casava com **zero** deles. Conferido na API que o analisador do Querido Diário resolve plural — `"planos de contingência"` devolve o mesmo que `"plano de contingência"` —, então a lista não precisa das flexões. O limite, e a razão de não alargar mais (§186): termo genérico enche a fila humana de ruído, e fila com ruído gasta o tempo de quem deveria julgar documento.

**O diário estadual: a rota que nunca poderia funcionar.** `coletar_doe.py` registrava, a cada rodada, "adaptador não confirmado" para as 27 UFs: **2.479 lacunas idênticas desde 03/09**, um terço de todos os erros do log, sobre um fato que não muda de duas em duas horas. A lacuna é real e continua declarada — uma vez por dia, não a cada rodada. E fica registrado o que foi **medido** em 24/09: o Querido Diário **não indexa diário estadual**. Consultados os territórios de SE, ES, SP, RJ e MG, todos devolvem zero, enquanto Aracaju devolve 4.582. O adaptador `querido_diario` dessa rota nunca poderia funcionar; confirmar um DOE exige adaptador direto, sítio a sítio. Registrado para ninguém repetir a tentativa achando que é questão de configuração. O host, de quebra, ainda era o antigo — o que responde 302 a cada chamada desde 21/09.

**O achado mais sério, e é de honestidade.** O teste de cobertura pergunta se o município tem diário indexado **alguma vez**, sem recorte de data. Medido em 24/09: **Manaus** tem 7.517 edições no Querido Diário e a mais recente é de **02/08/2016**; **São Paulo** tem 20, a mais recente de 07/02/2025; **Aracaju**, 4.582, a mais recente de 01/04/2025. Nenhum deles tem **uma única edição dentro do ciclo**.

Pelo critério antigo, os três saíam no log como *"indexado; nenhuma menção aos termos no período"* — frase que faz crer que houve edição e que nela não se falou do assunto. Não houve edição. O registro passa a ter **três estados** onde tinha dois: `sem_cobertura_qd` (não indexado), **`sem_edicao_no_periodo`** (indexado, mas sem nenhuma edição na janela) e `coberto_sem_mencao` (indexado, com edições, nenhuma menção). É a diferença entre *"procuramos e não há"* e *"não havia onde procurar"* — a distinção que este projeto não pode perder, e que estava sendo apagada 71 vezes por rodada.

## §193 · O carimbo que virava a data em UTC e deixava o portão 12 vermelho sem culpa de ninguém · 24/09/2026

Classe **correção de reprodutibilidade**. Nenhum dado muda, nenhum número do índice muda. O que muda é a cadeia de derivados deixar de depender do relógio da parede.

**O sintoma.** O CI do PR #370 reprovou no portão 12 com dois arquivos obsoletos — `data/municipios_card.json` e o manifesto — enquanto os mesmos portões estavam verdes na máquina local. Reprovação que não se reproduz é sempre suspeita de ambiente, e era.

**A causa.** `scripts/verificar_derivados.sh` fixa `SOURCE_DATE_EPOCH` no corte da edição, justamente para a cadeia inteira ser reproduzível. `gerar_card_municipios.py` escapava: carimbava `gerado_em` com `date.today()`. Enquanto a data local e a do runner coincidem, o defeito é invisível. O CI rodou às **01:21 UTC de 24/09/2026**, com o Brasil ainda em 23/09 — o runner regenerou com o dia seguinte, o portão viu diferença e acusou derivado obsoleto num ramo que não tinha nada a ver com carimbo de data.

**O tamanho do defeito.** Ele não era do ramo. Ele pega **qualquer ramo, e a própria `main`**, em toda janela entre a meia-noite UTC e a meia-noite local — três horas por dia, todo dia. O `/p12` do projeto já registrava o sintoma ("carimbo `gerado_em` obsoleto em `data/municipios_card.json` já deixou a `main` vermelha sozinho"), sem a causa. Agora a causa está no código, com o motivo escrito ao lado.

**A correção, na origem.** `data_de_geracao()` lê `SOURCE_DATE_EPOCH` quando ele existe e só cai em `date.today()` quando não existe — o mesmo padrão que `gerar_pdf_indice.py` e `gerar_pdf_metodologia.py` já usavam. Rodando pela cadeia canônica, o carimbo passa a ser o corte (`2026-09-10`), determinístico em qualquer fuso e em qualquer hora. O campo não é lido por nenhuma página: a busca por município em `prefeituras.js` consome os cartões, não o carimbo.
**O defeito estava em dois lugares, e o segundo derrubou o CI de novo.** Corrigido o carimbo do card, a rodada seguinte reprovou outra vez no portão 12 — agora com **uma única linha** do manifesto, e nenhum arquivo alterado. A linha era a primeira dele: *"selado em 23/09/2026"*. O `scripts/gerar_manifesto.py` fixa `SOURCE_DATE_EPOCH` no corte justamente para os PDFs saírem bit-determinísticos, e o cabeçalho dele escapava pelo mesmo `date.today()`. Manifesto que depende de quando roda não é selo, é carimbo de hora. O sintoma foi didático: nenhum arquivo mudando e o manifesto mudando é a assinatura de um carimbo no próprio manifesto.

**A correção, na origem, nos dois.** `data_de_geracao()` e o selo do manifesto leem `SOURCE_DATE_EPOCH` quando ele existe e só caem em `date.today()` quando não existe — o mesmo padrão que `gerar_pdf_indice.py` e `gerar_pdf_metodologia.py` já usavam. Rodando pela cadeia canônica, os dois passam a carregar o corte (`2026-09-10`), determinísticos em qualquer fuso e em qualquer hora. O campo não é lido por nenhuma página: a busca por município em `prefeituras.js` consome os cartões, não o carimbo.

**Trava.** Autoteste no próprio gerador, que já é portão: com `SOURCE_DATE_EPOCH` posto, a data sai dele — conferido em dois epochs distintos —; sem ele, cai no dia de hoje. Os epochs são calculados no teste, não digitados: a primeira versão trazia dois números mágicos, e os dois estavam um dia adiantados.

**Teste.** Autoteste do gerador verde; cadeia canônica regenerada em árvore limpa sem diferença.

## §192 · A constituição visual entra como fonte de verdade, e a auditoria mede o que ela acusa · 23/09/2026

Classe **governança de design**. Nenhum pixel do site mudou nesta entrada, e isso é deliberado: o §25 da própria constituição proíbe maquiagem componente por componente e manda observar o site inteiro antes de tocar em qualquer coisa. Esta entrada faz os passos 1 a 5 desse processo e para onde ele manda parar.

**O que entrou.** `AI_VISUAL_ART_DIRECTION.md`, na raiz, ao lado da metodologia e da governança editorial. O projeto passa a ter **três fontes de verdade**, e a ordem entre elas ficou escrita no `CLAUDE.md`: a `METODOLOGIA` decide **o que pode ser afirmado**; a governança editorial decide **por que, onde e como** aquilo é dito; a direção de arte decide **com que forma** aquilo aparece. Prova, depois narrativa, depois estética — e é a própria direção de arte que estabelece esse limite, no §23 (criatividade nunca compromete contraste, legibilidade, daltonismo ou leitura em tela pequena) e no §10 (cor não introduz julgamento que o dado não sustenta).

### A auditoria, com número

As dez páginas foram abertas em navegador real e medidas. O que a constituição acusa no §19 — "estética de template" — está medido, não suposto:

| medida | resultado |
|---|---|
| `border-radius` das figuras | **6 px em 38 de 38** — uniformidade total |
| sombra | **presente em 38 de 38** |
| larguras distintas para 38 figuras | **cinco**; a mais comum cobre 15 delas |
| ritmo dominante das seções | figura + um parágrafo, repetido |
| figura que ocupe a viewport | **nenhuma**: a maior tem 1.132 px num `--grade-max` de 1.180 px |
| cartões em sequência | um painel do financiamento tem **dez**; outro tem cinco |
| `.figura-cat`, o degrau de categoria do componente | **vazio nas 38** |

Três leituras que a tabela sustenta. **A largura não é decisão de composição:** ela é consequência da coluna da grade, e por isso só existem cinco. **Não há momento imersivo** — o §6 pede que uma visualização possa ocupar grande parte da tela, e nenhuma ocupa. **O ritmo é o que o §4 nomeia**: a sequência título/texto/gráfico repetida, mais visível em `monitor-de-riscos`, `defesa-civil`, `saude` e `financiamento`, onde quase toda seção tem a mesma forma.

Uma ressalva de honestidade: a uniformidade medida **não é acidente nem desleixo**. Ela é o resultado de uma decisão registrada — a auditoria de consistência de 07/09/2026, que criou o componente único de figura e a escala fixa, e a travou por dois portões. O site é uniforme porque foi construído para ser. A constituição visual agora pede o oposto em vários pontos, e essa é a matéria das decisões abaixo, não um defeito a corrigir em silêncio.

### Quatro colisões que exigem decisão da editoria

O §25 manda reconstruir a direção global antes de redesenhar. Não dá para fazer isso sem resolver quatro pontos em que a constituição contradiz uma decisão viva do projeto — três delas tomadas nesta mesma semana.

1. **Fundo branco.** O §1 lista "excesso de branco" e "cinza institucional" entre o que a seriedade não precisa. A editoria determinou em 05/09/2026, e **reafirmou em 23/09/2026**, que o fundo deste site é branco. A determinação prevalece; o desvio está declarado no `CLAUDE.md`. O que a constituição ainda permite sem tocar nisso é profundidade por **campo de cor, linha e espaço**, não por inversão de base.

2. **Paleta.** O §11 pede profundidade mineral — ametistas, magentas escuros, turquesas. O sistema de marca instalado em 23/09 fixa **dez hexes**, e `assets/tokens.css` proíbe hex fora dele, com portão. As duas coisas não cabem juntas: ou a paleta da marca ganha uma extensão declarada (tons profundos derivados dos dez, com função semântica atribuída, como o §9 exige), ou o §11 fica limitado ao que os dez permitem.

3. **Card e componente único.** O §6 afirma que **card não é unidade narrativa** e o §19 marca "gráfico dentro de caixa branca" e "grade repetitiva de três colunas" como template. A arquitetura do site é exatamente essa, por decisão de 07/09, e `verificar_figuras.js` e `verificar_consistencia_visual.js` a mantêm. Sair dela é reescrever os dois portões — possível, mas é mudança de arquitetura visual, não ajuste.

4. **Escala tipográfica.** O §13 pede diferenciação entre título narrativo, título de seção, título de visualização, corpo, legenda, nota, fonte e número destacado. A escala fixa de oito degraus cobre os tamanhos, mas **os papéis não estão todos distintos** — e o §14 lembra que hierarquia não é só tamanho: peso, largura, posição, espaço e ritmo também constroem. Aqui há caminho sem quebrar a escala, usando peso e espaço, e é o único dos quatro pontos que não exige decisão para começar.

### O que já dá para fazer sem decisão nenhuma

Três coisas, todas dentro do sistema existente e sem tocar em portão: preencher `.figura-cat`, que é um degrau de hierarquia que o componente já tem e ninguém usa; diferenciar os papéis tipográficos por **peso e espaço** em vez de tamanho (§14); e aplicar as **famílias de composição** do §21 ao que já existe, começando por onde a narrativa pede — a página de riscos abre em contexto nacional e deveria abrir em composição ampla, e a busca por município é uma família AÇÃO que hoje tem a mesma forma de tudo mais.

Nenhuma dessas foi feita nesta entrada. O §25 só libera redesenhar no passo 9, depois de a direção global estar reconstruída, e a direção global depende dos quatro pontos acima.

**Teste.** Nenhuma mudança visual; portões de estrutura, figuras, legendas, palavras, fichas semânticas e consistência visual verdes, como antes.

## §191 · A calibração propagada para as páginas restantes · 23/09/2026

Classe **revisão editorial**. Nenhum número muda, nenhuma figura nasce ou morre. O §34 só libera propagar depois da calibração validada; o §190 fez a calibração no MARÉ · Saúde, e esta entrada leva a **lógica** — não as frases — às outras páginas. O §13 é explícito: consistência é aplicar a mesma regra a objetos diferentes, não repetir o mesmo texto.

**Base de evidência.** As seis páginas com figura foram abertas em navegador real e inventariadas renderizadas, não no HTML: **26 figuras** com título, legenda, nota de leitura e presença de seletor. A calibração tinha ensinado que nesta casa o texto do HTML é só o que se vê sem JavaScript — os títulos-fato são escritos por cima, em tempo de execução —, e auditar o arquivo teria deixado passar de novo o que passou antes.

**Doze correções, todas das classes que a calibração isolou:**

*Metadiscurso (§18).* A nota da anomalia mensal abria com "**Este gráfico mostra**", que está nominalmente na lista do §18. O conteúdo e a autossuficiência que a editoria pediu em 17/09 ficam intactos; o sujeito passa a ser a medida, como já era nas notas do ONI e do RONI, e não o gráfico.

*Legenda que descrevia o seletor (§13, §21).* Duas figuras da defesa civil traziam "plano localizado, **ou** até onde a verificação chegou" e "% de municípios com ato, **ou** natureza predominante" — a legenda enumerando as opções do `<select>` logo abaixo, que já as nomeia. Mesmo defeito que a saúde tinha, mesma solução: a legenda diz o invariante da figura, o controle diz o recorte.

*Legenda que repetia o título (§13).* Sete casos, entre os avisos do INMET, os alertas do CEMADEN, as rotas do dinheiro, a série de transferências, os prioritários da defesa civil, as áreas COBRADE e o gráfico do RS. Em cada um a legenda passou a carregar o que o título não diz — origem da lista, unidade, classificação, referência da anomalia — em vez de reescrevê-lo.

*Forma no lugar do objeto (§12).* "Tipo de risco projetado para o ciclo — **mapa e contagem de estados**" descrevia o layout da figura. O título nomeia o objeto; a forma o leitor vê.

*Título nomeado pela figura vizinha (§7).* "**Detalhe geográfico** · valor pago por UF" em Pesquisadores. O §7 proíbe nomear uma figura pela anterior, e "detalhe" só significa algo para quem leu a de cima. Virou "Valor pago das MPs por UF da unidade gestora", que se sustenta sozinho — o teste do §32.10.

**Um erro meu no meio do caminho.** Ao tirar a duplicação entre legenda e nota do gráfico de anomalia, escrevi uma legenda que repetia o título inteiro. A auditoria automática da rodada seguinte pegou, e a legenda passou a dar a referência que faltava (desvio em relação à média climatológica do mês). Fica registrado porque a lição é a do §21: economia de texto não é cortar, é trocar repetição por informação.

**O que foi auditado e não mudou.** Os títulos de cartão — 33 deles, em Prefeituras, Financiamento, Pesquisadores e Imprensa — entram no escopo do §5 e foram lidos um a um: identificam objeto, sem metadiscurso e sem juízo. A numeração das oito rotas do dinheiro é identificador, não significado, que é o que o §28 pede. Nada a corrigir, e isso também é resultado.

**Auditoria final, automatizada e repetível.** Ao fim, as 26 figuras foram reinventariadas renderizadas e passadas por quatro testes: legenda que repete o título, legenda que descreve o seletor, metadiscurso na legenda ou na nota, e título duplicado na mesma página. **Zero ocorrências.**

**O que continua em aberto.** As seções "Onde cada estado está" e "O que cada estado publicou", na saúde, seguem anotadas como suspeita de redundância (§10) — examinar isso é decidir se uma figura sai, e remoção de evidência substantiva é decisão da editoria pelo §29, não minha. A dívida do §35 (ficha semântica por figura) segue declarada. E a ordem narrativa das páginas (§8, §36 passo 7) não foi mexida: esta entrada revisou texto, não sequência.

**O que estava em aberto e foi fechado nesta mesma entrada.**

*A suspeita de redundância era outra coisa.* Examinadas, "Onde cada estado está" e "O que cada estado publicou" **não são redundantes**: a primeira é o cartão por estado — a camada de territorialização em que o leitor acha o seu (§26) —; a segunda é o panorama agregado, com os três mapas. Mesmo dado, funções narrativas distintas, e o §10 as classifica em papéis diferentes. O defeito real era **a ordem** — e aqui cabe precisão, porque a primeira formulação desta entrada dizia "específico antes do geral" e isso está errado: os dois painéis são de **escala estadual**. O que os separa é a função. `#estadual` responde "o que cada estado publicou" no agregado, e `#estados` deixa o leitor achar o seu — o passo BRASIL → ESTADO do §26. A resposta agregada passa a vir antes da busca individual. Os dois painéis foram trocados; **nenhuma figura saiu**, e nenhuma evidência foi eliminada, o que teria exigido decisão da editoria pelo §29. A decisão editorial registrada em 2089 — cada desfecho em seção própria **antes dos estados** — continua valendo e segue asserida por portão; o que nunca foi decisão registrada era a ordem interna dos dois painéis, que o portão apenas fixava por inércia.

*A pendência do §22 que eu havia adiado.* "Última semana consolidada", "última semana disponível" e "última semana epidemiológica" conviviam na mesma tela. Lidos o dado e o código, a diferença é **real**: o mapa municipal lê a série consolidada do InfoDengue, com as quatro últimas semanas vazadas, e o mapa das capitais lê outra fonte, em que cada capital carrega a própria semana. Uniformizar teria apagado uma distinção de método. As duas expressões ficam, e a ficha semântica de cada figura agora registra por quê.

*Seis legendas da saúde que a varredura anterior não alcançou*, porque a página não estava no lote auditado — duas delas repetiam o título por causa da própria calibração do §190.

**A dívida do §35, paga.** `docs/fichas_semanticas.json` passa a guardar, para cada uma das **38 figuras** do site, a ficha que o §35 pede: pergunta que responde, dimensão da preparação, universo, unidade de análise, território, período, variável, denominador, fonte, metodologia, **conclusões permitidas e não permitidas**, função narrativa e ação relacionada. Onde não foi possível estabelecer um campo com segurança, ele é `null` — o §6 proíbe transformar incerteza interna em afirmação, e isso vale também para a memória interna.

Ficha sem portão envelhece em silêncio, então ela ganhou um: `scripts/verificar_fichas_semanticas.js` (o **55º** do repositório) renderiza as onze páginas e reprova figura sem ficha, ficha órfã, campo obrigatório vazio e — porque o §35 diz que a ficha é memória interna e o §27 proíbe renderizar bastidor — qualquer texto de ficha que vaze para a interface. O portão não julga o conteúdo da ficha: isso é leitura humana, e o §29 reserva à editoria o que muda significado.

**Teste.** Portões de legendas, figuras, palavras, estrutura, fichas semânticas e os três de runtime (saúde, mapas, financiamento) verdes; 38 figuras com ficha completa.

## §190 · Teste de calibração da governança editorial no MARÉ · Saúde · 23/09/2026

Classe **revisão editorial**. Nenhum número do índice muda, nenhuma figura foi criada ou removida. O §34 da governança exige, antes de propagar qualquer lógica ao site, calibrar numa seção com pelo menos três visualizações e **escolher uma difícil, não a mais fácil**. A escolhida foi a página de Saúde: doze figuras e cinco seções irmãs por doença — a configuração em que legenda por fórmula e título herdado da figura vizinha são mais prováveis.

**Sete defeitos no texto estático.** Dois títulos **idênticos** ("Nível de alerta por município · última semana consolidada") distinguiam dengue de chikungunya apenas por um token no fim da legenda. As legendas dessas figuras eram molde com sufixo — exatamente o que o §13 chama de "parecer gerada por fórmula". Duas legendas descreviam **as três opções do seletor** ("semanal … ou acumulado anual") em vez da figura, fazendo o trabalho que o próprio controle já faz. A legenda do status repetia o título duas vezes na mesma frase. E o risco sanitário trazia "(derivado)" no título **e** na legenda.

**Um defeito de indicador.** O mapa de prontidão se chamava "Antecipação por estado". O código é explícito (`saude.js`, Metodologia §31): *prontidão = média de instrumento, cobertura populacional sanitária e antecipação*. O título nomeava **um dos três componentes como se fosse o indicador** — o §3 proíbe transformar variável isolada em conceito mais amplo, e aqui era o inverso, o conceito reduzido a uma parte. A legenda, o `aria-label` e o código já diziam *prontidão*; o título era o único fora. Agrava que a `METODOLOGIA` (E17) usa "antecipação" também para **a metade da página** (antecipação × resposta): a mesma palavra com dois sentidos na mesma tela, que é o §22.

**Dois defeitos que só a renderização mostrou** — e é para isso que o §34 tem um passo 9. Os títulos desta página são **títulos-fato calculados do dado** (regra de 15/09), escritos por JavaScript por cima do HTML. Lidos no navegador:

- o título-fato do mapa de **prontidão** contava estados por **status de instrumento** — o objeto da figura seguinte —, saindo quase idêntico ao dela. É o §32.8 em estado puro: texto herdado da figura vizinha.
- o título dizia "**1 municípios** em alerta" para chikungunya. Concordância, que o §29 autoriza corrigir sem consulta.

**Um erro meu, registrado porque importa.** A primeira correção do título-fato derivou a contagem de verificados de um campo que não existe em `saude_uf.json`, e a página renderizou "**Prontidão sanitária por estado: 0 de 27 estados verificados**" — número falso num texto público. A validação renderizada pegou antes de qualquer commit. A contagem passou a vir do agregado autoritativo (`monitor_saude.json` → `resumo.verificadas`, hoje **20 de 27**), com o motivo escrito no código para ninguém repetir o atalho. O §6 diz que incerteza interna nunca vira afirmação pública; aqui ela quase virou, e o que a barrou foi olhar o resultado renderizado, não o diff.

**O portão foi atualizado, não afrouxado.** `verificar_runtime_saude.js` exigia que o título do mapa trouxesse as contagens de status. O princípio que ele guarda — *título-fato vem do dado, nunca digitado* — continua idêntico; o que mudou é qual fato e sobre qual objeto. A asserção agora confere a contagem de verificados contra `monitor_saude.json`, **passou a cobrir também o título do status** (que antes ninguém verificava) e ficou imune ao singular, que teria virado falha latente na primeira vez que a dengue marcasse um só município.

**Correção de um registro do §189.** Aquela entrada disse que a nota metodológica "não tem lugar próprio" no componente de figura. Está errado: `.figura-leitura` existe no componente desde 07/09 e é a quarta função que o §11 pede. O defeito real é outro, e menor: ela é usada em **três figuras, todas em `monitor-de-riscos.html`**, e em nenhuma das outras onze páginas. Slot subutilizado, não ausente.

**O que esta entrada não faz.** Não propaga nada. O §34 só libera propagar depois da calibração validada, e a propagação para as outras onze páginas é trabalho próprio, com o mesmo protocolo: ler dado e código de cada figura antes de escrever, e validar renderizado. As seções "Onde cada estado está" e "O que cada estado publicou" ficam anotadas como suspeita de redundância (§10) ainda não examinada.

**Teste.** Portões de legendas, figuras, palavras, estrutura, consistência visual e runtime de saúde verdes; doze figuras sem título duplicado; overflow horizontal 0.

## §189 · A governança editorial e narrativa vira documento canônico, com precedência declarada · 23/09/2026

Classe **governança**. Nenhum número do índice muda e nenhum texto público foi reescrito nesta entrada. O que muda é qual documento decide, e em que ordem, quando se vai escrever para o leitor.

**O que entrou.** `AI_EDITORIAL_NARRATIVE_GOVERNANCE.md`, na raiz, ao lado da `METODOLOGIA.md`. Ele declara a pergunta central do site — *qual é o estado de preparação do Brasil diante do risco analisado?* — e a sequência que a responde: **pergunta → contexto → evidências → dimensões da preparação → síntese → ação**. E fixa a hierarquia de decisão: a narrativa decide **por quê e onde**, a semântica decide **o quê**, o editorial decide **como**; nenhuma camada substitui a anterior.

**A regra de precedência, escrita para não ficar ambígua.** O documento se declara acima de padrão local e de hábito anterior de geração. No `CLAUDE.md` isso ficou combinado assim: a `METODOLOGIA.md` decide **o que pode ser afirmado** (prova, lacuna declarada, teto de ausência, o que pontua); a governança decide **por que, onde e como** aquilo é dito. As duas não competem — uma é limite de fato, a outra é ordem da informação. Quando o estilo pedir o que a prova não sustenta, vence a prova, e a própria governança diz isso no §6 e no §15.

**O que o site já cumpre, e não foi mexido.** O portão 19 (`verificar_legendas.js`, regra de 15/09) já reprova juízo, interpretação e causa não demonstrada em texto de figura — é o §13, o §15 e o §20 da governança, já em código. A `docs/VOZ_EDITORIAL.md` (16/09) já proíbe metadiscurso e explicação da política editorial na legenda — §18. O componente de figura já separa **categoria, título, legenda e fonte**, com formato único de crédito. E o teto público de ausência ("não localizamos até o corte", nunca "não existe") é literalmente o §15.

**As duas lacunas reais, declaradas e não resolvidas aqui:**

1. **Nota metodológica não tem lugar próprio.** O §11 manda manter quatro funções separadas — título, legenda, **nota metodológica** e fonte — e proíbe comprimi-las num bloco só. O componente tem três: `.figura-cat`, `.figura-titulo`, `.figura-sub` e `.fonte-figura`. Hoje a ressalva metodológica vive na ficha "Como ler" ou numa nota "O que a figura não diz", por página, não por figura. Falta decidir se ela vira slot do componente.
2. **Não existe ficha semântica por figura (§35).** O documento pede, para cada visualização, uma ficha interna com universo, unidade de análise, território, período, variável, denominador, fonte, metodologia, conclusões permitidas e não permitidas, função narrativa e ação relacionada — memória semântica que impede uma alteração futura de perder o significado da figura. O projeto não tem nada equivalente. É trabalho de porte, e fica declarado como dívida, não como pendência escondida.

**Um conflito que precisa de decisão.** O ramo `marca-pessoal`, ainda não mesclado, acrescenta ao `CLAUDE.md` um sistema de marca cuja seção de voz pede tom "provocador, poético, espirituoso e vivo". A governança editorial pede o oposto para conteúdo público: voz "clara, segura, precisa, **sóbria**", não promocional (§16), sem metáfora excessiva nem frase de impacto (§24), sem dizer ao leitor o que pensar (§20). Pela precedência agora declarada, **a governança vence no conteúdo público** — a marca segue mandando em paleta, tipografia e sistema visual. Se o ramo da marca for mesclado, a seção de voz dele precisa entrar já subordinada, e não como regra concorrente.

**O que esta entrada não faz.** Não revisa título, legenda ou texto de nenhuma página. O §36 da governança descreve uma ordem de execução para revisão geral do site, e o §34 exige um teste de calibração numa seção difícil antes de propagar qualquer lógica ao restante — nada disso foi feito aqui, e fazer sem pedido seria exatamente o "patchwork" que o §30 proíbe.

## §188 · Errata pública ao C6: a classificação por UF é dado, e o Paraná foi reclassificado dentro do defeso · 23/09/2026

Classe **governança com efeito em nota** — a primeira desta série que muda um número publicado. O Paraná vai de **67,4 para 73,3** e troca de faixa. Nenhum peso, crédito, componente, faixa ou régua foi tocado.

**A pergunta que a editoria fez, e que estava certa.** "Se pode mudar o plano dentro do defeso, não entendi essa regra." A dúvida apontava para uma contradição real, e a verificação a confirmou: desde 06/09 o `data/municipios.json` mudou em **16 commits** — a nota muda todo dia pelo lado municipal —, enquanto `ESTADOS` e `ESTRUTURA` não mudaram uma vez (`git log -L` não devolve nenhum commit). Não era disciplina: era trava.

**O defeito, nomeado.** O C6 diz, desde 02/09, que o Monitor não aplica mudança de **regra** que altere notas até 25/10, e que **publica correção de dado que viole regra de prova, com errata e efeito declarado em pontos por UF** — foi assim que o C10 rebaixou registros de imprensa sem documento primário, derrubando a média de 47,1 para 45,9 dentro do defeso. A Errata C25, de 06/09, trancou por hash as constantes do motor, e nesse hash entraram `ESTADOS` e `ESTRUTURA`: a **classificação por UF**, que é dado, não regra. O resultado é que a correção autorizada no papel ficou **impossível em código** — qualquer reclassificação, com quanta prova houvesse, reprovava no portão. A regra escrita e a trava implementada diziam coisas diferentes, e a trava vencia. O pior dos dois mundos, outra vez: a disciplina existia no lugar errado.

**A correção é de procedimento, não de aperto.** A classificação por UF volta a ser corrigível dentro do defeso, e **só** por errata pública encadeada: `data/congelamento_defeso.json` ganha uma lista `erratas`, cada entrada com código, data, motivo, UF, efeito em pontos e os hashes **anterior e novo**. `verificar_consistencia.py` confere a corrente inteira e reprova se ela se romper, se faltar campo obrigatório, ou se alguém trocar o hash sem errata — os três casos foram testados ao vivo antes de seguir, e os três reprovam. Trava que passa e não morde é enfeite. **Mudança de regra continua proibida até 25/10, e nenhuma errata a autoriza.**

**Por que o Paraná muda, com a prova.** Os dois eixos do PR receberam `READ` do **mesmo julgamento do mesmo documento** em 04/09/2026 — e os eixos perguntam coisas diferentes: a estrutura pergunta se um órgão foi criado ou acionado para o ciclo; o instrumento pergunta se ele é **novo** para o ciclo. A confusão entre as duas perguntas é a causa do erro, e ela só apareceu quando o documento foi lido.

O §186 preservou as Notas Técnicas Conjuntas nº 03, 04 e 05/2026, e o §187 extraiu o texto das três. O que elas dizem:

- a página da Coordenadoria declara que Defesa Civil e SIMEPAR "mantêm monitoramento contínuo ... **para o biênio 2026/2027**" e que as notas são "emitidas **mensalmente**" — série instituída para o ciclo, não readaptação de instrumento preexistente;
- a nº 05, de **14 de agosto de 2026**, não para na análise: fixa **gatilhos operacionais atrelados aos Avisos BGR** — "prever **obrigatoriamente** nos Planos de Contingência" a restrição de público sob Aviso Laranja e o **cancelamento** do evento sob Aviso Vermelho, antes do início do evento meteorológico —, endereçados a atores identificados (gestores municipais e NARDCs), com exigências técnicas nomeadas (ABNT NBR 6123, SPDA, ART/RRT).

Pela régua do §30, que julga pela **função** do ato e não pelo nome, o instrumento operacional do PR é `NOVO`. A **estrutura permanece `READ`**: as notas acionam CEGERD e NARDCs, e não criam órgão. É a mesma assimetria já registrada no AM em 04/09 — instrumento `NOVO` pelo decreto preventivo do ciclo, estrutura `READ` pelo sistema permanente mobilizado —, e é ela que sustenta a consistência entre as duas UFs.

**Efeito declarado, medido antes e depois:**

| | antes | depois |
|---|---|---|
| PR · componente estadual | 65,0 | 82,5 |
| PR · nota | 67,4 | **73,3** |
| PR · faixa | consolidado | **avançado** |
| PR · leitura geométrica | 62,4 | 67,5 |
| média nacional linear | 46,21 | 46,43 |
| média nacional geométrica | 40,33 | 40,52 |

**Nenhuma outra UF muda** — a conferência foi campo a campo nos 27 registros do índice. Sem mudança de versão maior: como no C10, isto é correção de dado, não de motor (`METODOLOGIA` §12).

**O que esta entrada não faz.** Não promove nada por conta própria: o PCO no SISDC segue como via de cobertura municipal a investigar, com o limite declarado de que sistema de coordenador não é publicação ao cidadão; e as capitais e municípios do PR não foram reavaliados aqui. Corrigir para cima é o mesmo dever que corrigir para baixo — a assimetria do §5.0 vale contra o erro, não a favor dele.

**Teste.** Três casos de burla verificados ao vivo contra a corrente de erratas (corrente rompida, campo obrigatório ausente, hash trocado sem errata), todos reprovando. `verificar_consistencia` verde, `recalcular_mare --write` com média 46,4, derivados regenerados pela cadeia canônica e portão 12 verde.

## §187 · O plano de saúde de SP estava no banco desde 10/09, e a procedência dizia "robots" onde era geobloqueio · 23/09/2026

Classe **correção de registro e de instrumento**. Nenhum número do índice muda e nada é promovido. O que muda é a qualidade da prova de um estado, um padrão de busca que escondia host inteiro, e um detector que não reconhecia uma recusa.

**A pergunta da editoria.** Recebido o endereço do *Plano Estadual de Preparação e Resposta em Saúde para o Fenômeno El Niño 2026-2027* (SES-SP), a pergunta foi: por que a varredura não achou? A resposta não é ausência — é **recall**, e o mais desconfortável é que a busca tinha, no próprio banco, uma instrução para não tentar.

**O documento já estava registrado.** `data/saude_desfechos/fontes_uf.json` traz a URL exata como `url_instrumento` de SP desde **10/09/2026**, com a leitura de que o plano "substitui o Plano de Contingência das Arboviroses 2025/2026 como instrumento de referência do ciclo". E `data/evidencias.json` guardava dele uma **transcrição manual de 9,7 kB** (`41e391c6…`), com a convenção declarada: a chave é o sha256 do **texto**, porque o binário não havia sido baixado.

**A primeira hipótese era errada, e a medição a derrubou.** Suspeitei do padrão de domínio: `descobrir_dominios.PADROES["saude"]` não gerava `portal.saude.{uf}.gov.br`, e o §184 havia fechado SP em `saude.sp.gov.br`. Medido: as três grafias — `saude.sp.gov.br`, `www.saude.sp.gov.br` e `portal.saude.sp.gov.br` — servem **o mesmo documento, com o mesmo sha256** (`a5473b26…`, 1.368.655 bytes), sob o host que o §184 já tinha escolhido. **O padrão não foi a causa.** Ele foi acrescentado de todo modo, como alargamento de alcance e não como correção de defeito, e a entrada registra a diferença porque confundir as duas coisas é como se aprende a lição errada.

**As causas reais, medidas:**

1. **A busca não consulta o próprio banco.** `descobrir_dominios` e `descobrir_planos` procuram por palpite de domínio e por link em página renderizada, e **nunca conferem as URLs que o projeto já registrou** em `data/saude_desfechos/fontes_uf.json` e `data/evidencias.json`. O plano estava nos dois. Uma varredura que ignora o que já foi achado pode registrar "consultado sem achado" sobre documento que o projeto lê desde 10/09 — e foi exatamente isso. É a causa de fundo, e a mais fácil de subestimar, porque não se parece com um defeito de rede nem de parser.
2. **Caminho fundo, não linkado.** O PDF está sob `/resources/cve-centro-de-vigilancia-epidemiologica/areas-de-vigilancia/central/`, e nenhuma das páginas que o canal renderizado do §185 visitou aponta para ele. Descoberta por link não alcança documento que não é linkado de onde se entra.
3. **A nota de procedência dizia para não tentar** — "portal.saude.sp.gov.br recusa acesso automatizado por `robots.txt`".

**E essa justificativa não se sustenta.** Medido em 23/09: `portal.saude.sp.gov.br/robots.txt` devolve **404** — não existe arquivo, nada está proibido. A única captura arquivada daquele caminho (Wayback, 29/04/2026) **não é um `robots.txt`**: é uma página `Connection denied by Geolocation`, servida com **HTTP 200**. O que barrou a leitura automatizada em 10/09 foi **geobloqueio de WAF**, não robots.

O diagnóstico correto já estava escrito — em `METODOLOGIA.md` §11, a própria entrada de 10/09 registra que "num acesso automatizado a outro recurso do CVE-SP a resposta foi `Blocked country: [Brazil]`". **Os dois registros do projeto discordavam entre si**, um dizendo geolocalização e outro dizendo robots, e a varredura de 23/09 não leu nenhum dos dois. Uma recusa mal nomeada virou regra de abstenção por treze dias.

**O detector do §186 não pegava esse caso.** `detectar_muro_de_robo` devolvia `None` para a página de geobloqueio: a lista de marcas tinha Imperva, Cloudflare e Akamai, e não tinha muro de país. É a mesma classe e o mesmo perigo do §186 — o servidor respondeu não, e a resposta **parece conteúdo**: uma página de 1,5 kB entraria no índice de evidências como se fosse o documento. `"connection denied by geolocation"` entra em `MARCAS_DE_MURO`.

**Cautela operacional que fica declarada.** O filtro é por país, e o *runner* da Action **não roda no Brasil**. Este acesso de 23/09 partiu de máquina no Brasil e funcionou; a captura de um rastreador fora do país foi negada. Então documento de SP acessível daqui pode ser inacessível no CI, e vice-versa — divergência de ambiente que nenhum coletor deve tratar como ausência de plano.

**O que ficou preservado.** O **binário** do plano: 43 páginas, 1.368.655 bytes, `a5473b26…`, com texto extraído do próprio documento (78.771 caracteres, sem CR) e hash dos dois. A cadeia de SP na saúde deixa de ser transcrição à mão e passa a ser binário + texto, ambos verificáveis. Os dois itens ficam cruzados no índice, e o de 10/09 guarda a retificação da sua própria procedência — o erro fica no registro, não apagado.

**Um apontamento de imprensa onde havia documento.** Em `data/saude_uf.json`, o instrumento de SP para o El Niño apontava para matéria da **CNN Brasil**, com `hash_evidencia: null`, enquanto o oficial já estava em `fontes_uf.json`. Trocado pelo documento, com o hash do binário; a notícia fica em `url_noticia`. **O status não muda por esta correção**: continua `NOVO`, e reclassificar é R7.

**Sergipe: o OCR entregou o ato.** A Resolução CES/SE nº 08/2024 é publicada num arquivo que o nome promete como resolução e que é, de fato, a **página 7 do Diário Oficial de Sergipe nº 29.393 de 07/05/2024** — digitalizada, zero caracteres extraíveis, com matéria de outros órgãos na mesma página. O OCR do §177 devolveu 9.007 caracteres legíveis, e neles o ato **se apresenta como tal** (régua do §180): o Plenário do Conselho Estadual de Saúde, na 275ª Reunião Ordinária de 06/05/2024, invocando as Leis 8.080/1990, 8.142/1990 e a Lei Estadual 6.300/2007, "Resolve **APROVAR** o Plano Estadual de Saúde 2024-2027", com homologação do Secretário de Estado da Saúde. O limite do §156 e do §177 fica escrito no registro: **texto de OCR é cópia legível, nunca entrada de classificador nem de juízo** — e este traz ruído visível (lê "08/2074" onde o original diz 08/2024). Quem decide se o registro de SE vira `documentado` é a editoria, lendo o documento.

**Instrumento de leitura.** `preservar_evidencias.py --ler|--ocr --alvo <trecho-da-url>` restringe a fila a um documento: esperar a vez de um alvo específico gastava rede relendo dezenas já lidos.

**O que fica em aberto, declarado.** A causa 1 não foi corrigida nesta entrada: fazer a busca conferir as URLs já registradas no banco antes de concluir é mudança de arquitetura da descoberta, não remendo, e entra como dívida nomeada. Enquanto ela não existir, **nenhuma rodada de descoberta pode ser lida como prova de ausência** — só como prova de que aquele canal não achou.

**Teste.** Um caso novo em `descobrir_dominios --autoteste` (as grafias com `portal.` estão nos padrões, antes do palpite genérico `www.{uf}`) e o **15º** em `scripts/testar_robots.py` (geobloqueio com 200 é recusa). Autotestes de robots e de domínios verdes; consistência, `recalcular_mare --check`, evidências, escrita portável e portão 12 verdes.

## §186 · A releitura de PR, SP e SE: o que apareceu, e o muro de robô que devolvia bloqueio com HTTP 200 · 23/09/2026

Classe **coleta e correção de leitura**. Nenhum número do índice muda e nada é promovido — tudo entra na fila R7. O que muda é o que está preservado, e uma prova falsa que o projeto poderia ter registrado sem perceber.

**O que esta entrada foi buscar.** O §182 mostrou que MT, SP, PR e SE eram tratados como fonte suspensa por defeso quando o que estava suspenso era a seção de notícias. Com os domínios corrigidos pelo §184 e a política de `robots.txt` do §185, os quatro voltaram à fila de leitura. MT saiu no §185; aqui estão os outros três.

### Paraná: o instrumento estadual está sendo mantido mensalmente, e ninguém tinha lido

A Coordenadoria Estadual da Defesa Civil do PR tem **uma seção "El Niño" na navegação principal** e uma página dedicada — *Notas Técnica Conjunta El Niño Oscilação Sul-ENOS 2026* — que reúne notas **mensais** produzidas com o SIMEPAR para o biênio 2026/2027, com análise climática, projeção de precipitação, avaliação de risco e recomendação preventiva. Preservadas três, com hash: **nº 03/2026** (846 kB, 6 páginas), **nº 04/2026** (1,3 MB, 7 páginas) e **nº 05/2026** (2,5 MB, 10 páginas), todas assinadas por dois meteorologistas com registro no CREA e pelo chefe do CEGERD.

O índice registra, para o PR, a "Nota Técnica Conjunta nº 01/2026". A leitura mostra que o instrumento **não é peça única de janeiro: é série mensal em curso**, e a nº 05 é de agosto de 2026 — dentro do ciclo pela régua do §5.2. Isso é matéria de reclassificação pela editoria, não de promoção automática: o que a máquina fez foi preservar e enfileirar.

Segundo achado, e ele explica um vazio do índice: o PR mantém o **Plano de Contingência online (PCO)**, ferramenta hospedada no SISDC (Sistema Informatizado de Defesa Civil do Paraná) para que o Coordenador Municipal elabore o PLANCON do seu município, invocando o art. 8º, XI da Lei 12.608. **Nove dos dez registros pontuáveis do PR não têm URL de documento** — e a razão provável é que os planos municipais vivem dentro desse sistema, não em PDF no sítio. Fica declarado como via de cobertura a investigar, com o limite óbvio: sistema de coordenador não é publicação ao cidadão.

Na saúde, o PR publica o Plano Estadual de Saúde em série (2008-2011 até 2020-2023), com a edição **2024-2027** servida pelo documentador oficial do estado.

### Sergipe: o plano de saúde com o ato que o aprova — e o plano de defesa civil que segue sem URL

Preservados, com hash: o **Plano Estadual de Saúde 2024-2027** (192 páginas, 2,5 MB, datado de novembro de 2023) e a **Resolução nº 08/2024 do Conselho Estadual de Saúde, que o aprova**. A resolução é **escaneada, sem camada de texto** — exatamente o caso que o §177 resolveu: entra na fila do OCR, e é o ato que a régua do §180 procura. Também na fila: as Programações Anuais de Saúde de 2021 a 2026 e as resoluções que as aprovam.

Na defesa civil, a página de legislação institucional traz decretos e portarias do órgão (medalha de mérito, edital de voluntariado, acordo com a UFS), mas **não o Plano de Contingência Estadual** que o índice registra para SE ("Sergipe Resiliente: El Niño 2026/27", Cegec, 04/08/2026). Ele continua **sem URL** — lacuna declarada, agora com a busca documentada: o sítio foi lido, renderizado, e o documento não está publicado ali.

### São Paulo: bloqueio de robô devolvido como se fosse página

O portal de SP entregou **107 kB de HTML** por HTTP na primeira leitura, no endereço final `/sec_defesa_civil`. Duas coisas apareceram depois:

- **sob navegador automatizado, a página vem vazia** — título em branco, zero links; há um script de detecção de robô ofuscado no `<head>`;
- **depois de alguns pedidos, o HTTP passou a devolver "Pardon Our Interruption" com HTTP 200** — o muro do Imperva.

Pela doutrina do §170, isso é **recusa**: o servidor respondeu não, e recusa se respeita. Não se disfarça cliente, não se troca de rota, não se insiste em laço. SP fica como lacuna declarada com o motivo escrito — e nenhum documento de SP foi lido nesta rodada.

**E aqui estava o defeito grave.** Um `403` o projeto já sabia tratar. Um muro com **200** é pior, porque *parece conteúdo*: sem detector, aquela página de 6 kB entraria em `data/evidencias.json` como documento preservado, e o índice passaria a citar como plano de SP uma tela de bloqueio. Seria **prova falsa** — o pior defeito possível num projeto cujo valor é a prova. `detectar_muro_de_robo()` reconhece as assinaturas conhecidas (Imperva, Cloudflare, Akamai) no texto declarativo da página, e `buscar()` levanta `MuroDeRobo` **antes de qualquer preservação**. Só olha resposta pequena e nunca PDF: muro é página curta, e varrer documento grande acharia falso positivo em quem cita o assunto.

### Duas correções de instrumento que a rodada real exigiu

**O renderizador desistia cedo.** `networkidle` nunca chega em sítio com conexão longa aberta — analytics, chat, *polling* —, e SP estourava 60 s assim. A espera passou a ser em cascata: `networkidle` (25 s) → `load` → `domcontentloaded`, registrando qual condição serviu. Foi assim que o portal de SP finalmente respondeu 200 ao navegador (ainda que em branco, pelo muro).

**O filtro de link do §185 era largo e sujou a fila humana.** Aceitava `emerg`, `portaria`, `decreto` e `document`, e a primeira rodada registrou "Acionar Corpo de Bombeiros", "Portaria de Nomeação COMPDEC — Modelo", "Rede Estadual de Radioamadores" e até a âncora de compartilhamento "Mais…". Fila de triagem com ruído é pior que fila curta: gasta o tempo humano que deveria julgar documento. Agora o termo é de plano (`plano`, `PLANCON`, `contingência`, `nota técnica`, `El Niño`, `ENOS`, seca, estiagem, incêndio, queimada, arbovirose, dengue), com teto de 25 links por página e exclusão de navegação, âncora e compartilhamento.

**A primeira versão do aperto errou para o outro lado**, e o erro ficou registrado porque importa: a purga levou junto a **"Resolução de Aprovação do PES 2024-2027"** de SE — que é precisamente o ato que o §180 procura para decidir se um registro é `documentado`. O filtro passou a aceitar ato **acompanhado** de verbo de aprovação ou de nome de plano (`Resolução … aprova o PES`), e a recusar ato solto (`Portaria nº 575 – SARGSUS`, `Portaria de Nomeação`). `--limpar-ruido` tirou **20 itens** da fila; ela ficou com 37, dos quais 22 vindos do canal renderizado.

**Teste.** Catorze casos no autoteste do `robots` (`scripts/testar_robots.py`), bloqueante: os onze do §185 mais os três do muro — muro é recusa, muro não acusa PDF nem resposta grande, e `buscar()` levanta antes de preservar. Dois casos novos no autoteste de `descobrir_planos`, com os links reais das três UFs nos dois sentidos, incluindo o ato de aprovação. Consistência, `recalcular_mare --check`, evidências, escrita portável e portão 12 verdes.

## §185 · `robots.txt` é pedido, não tranca: a regra decidida, escrita em código e com rastro público · 23/09/2026

Classe **decisão de política de coleta**, com efeito imediato na cobertura. Nenhum número do índice muda. O que muda é o Monitor passar a **ler** o que um sítio oficial publica atrás de um `robots.txt` restritivo — e a deixar registro de cada vez que faz isso.

**Como a questão apareceu.** A releitura das fontes que o §182 mostrou falsamente suspensas parou no primeiro alvo: `defesacivil.mt.gov.br` publica um `robots.txt` que libera Googlebot e Bingbot e **proíbe todos os demais** (`User-agent: *` / `Disallow: /`, `Crawl-delay: 30`). E uma varredura no repositório mostrou coisa pior: a instrução de trabalho dizia "não contornar `robots.txt`" e **nenhuma linha de código lia o arquivo**. A regra escrita e o comportamento real divergiam desde sempre — o pior dos dois mundos, porque a disciplina existia só no papel.

**O aprofundamento que a editoria pediu.** A conclusão, com as fontes:

- **A norma do protocolo é explícita.** RFC 9309, § 1.3: as regras do `robots.txt` "não são uma forma de autorização de acesso"; § 3: o protocolo "não substitui medidas válidas de segurança de conteúdo". É um **pedido** publicado pelo sítio. A diretiva `Crawl-delay`, usada pelo MT, nem consta da RFC — é extensão informal.
- **Não é crime.** O art. 154-A do Código Penal (Lei 12.737/2012) exige "violação indevida de mecanismo de segurança". `robots.txt` não é mecanismo de segurança, pela própria RFC. Ler página pública que o servidor entrega a quem pede não é invasão.
- **Não há entrave autoral.** Lei 9.610/98, art. 8º, IV: atos oficiais, leis e decretos **não são objeto de proteção**. PLANCON e decreto estadual são exatamente esse caso.
- **Não há norma nem precedente brasileiro** que torne o `robots.txt` vinculante; a doutrina registra a lacuna, e chama o bloqueio de dado público por robots de "óbice desnecessário de acesso a dados que, em sua origem, são públicos" (Igor Rocha, *Conjur*, 2023).
- **A LAI legitima o propósito, sem licenciar nada.** O art. 8º, § 3º, III obriga o **órgão** a "possibilitar o acesso automatizado por sistemas externos em formatos abertos, estruturados e legíveis por máquina". É dever do Estado sobre o que ele publica, e seu descumprimento se cobra pelos canais da própria LAI — *não* é autorização para rastrear. Fica registrada a correção de uma leitura anterior desta sessão, que esticou o dispositivo além do que ele diz.
- **O que morde de verdade é a LGPD**, e é onde o projeto já se disciplina: a ANPD trata raspagem como tratamento de dados (Nota Técnica 19/2023) e admite legítimo interesse quando o dado é público, sem expectativa de privacidade e com impacto minimizado (NT 12/2025). Nesta mesma sessão o Monitor redigiu CPF antes do hash (§175) e **recusou preservar** o catálogo telefônico de servidores da SES-SC (§181).
- **Precedente do campo.** O Querido Diário, da Open Knowledge Brasil — de onde este projeto lê o texto integral dos diários municipais —, roda com `ROBOTSTXT_OBEY = False` e cliente identificado.

**A decisão da editoria, em quatro partes.** O Monitor **lê** o `robots.txt` de cada sítio antes do primeiro acesso; **respeita** o `Crawl-delay` que ele pede; **acessa** documento público mesmo onde o arquivo pede que robôs não entrem, com o cliente **identificado** (`MonitorElNinoBrasil/2.2.4`, com endereço e contato — nunca disfarçado de navegador comum nem de Googlebot); e **deixa rastro** de cada acesso desse tipo em `data/robots_registro.json`, com URL, horário em UTC, origem e cliente, publicado como o resto de `data/`. O que **não muda**: `401`, `403`, `429`, `451`, captcha e login continuam sendo recusa que se respeita (§170) — `robots.txt` é pedido, aquilo é tranca.

**O tamanho medido da decisão.** Nos 46 domínios oficiais identificados pelo §184: **40 permitem** o cliente do Monitor, **5 não têm** `robots.txt` (AM bombeiros, ES nos dois setores, SP saúde, CE saúde) e **um** proíbe — o do MT. A política decide, hoje, um estado; o que ela decide de verdade é o princípio, e é por isso que está escrita.

**O que a leitura do MT encontrou — e nenhuma rodada anterior podia ver.** O portal é Liferay e responde, em texto, "este site precisa que o seu navegador tenha JAVASCRIPT ativo": o conteúdo existe, os links existem, e o cliente HTTP recebe o esqueleto. Renderizada com navegador real, a página **Planejamento Estratégico 2026** da Superintendência de Proteção e Defesa Civil de MT declara, entre outras metas: "Suporte para a elaboração de **20 Planos de Contingência (PLANCON)**" municipais; 20 mapeamentos de áreas suscetíveis a risco geo-hidrológico; Protocolo Operacional Padrão de emissão de alertas; dois simulados de desastre hidrológico; e "**Lançamento do inédito Plano Estadual de Defesa Civil de Mato Grosso**".

Duas consequências, nenhuma delas automática: o Plano Estadual de Defesa Civil de MT é anunciado como **a lançar** — é instrumento em elaboração, distinto do "Plano de Combate a Incêndios 2º sem. 2026 (Decreto 2.015/2026)" que o índice já registra, e não pontua sem o ato publicado e lido no documento (§156, §180); e os 20 PLANCONs são **intenção declarada**, pista de cobertura futura, não plano existente. O achado entra na fila de triagem humana com a evidência preservada, `promovivel: false` — promoção segue sendo R7.

**Canal 2 da descoberta, que a falha de camada exigia.** `descobrir_planos.py --renderizar` renderiza uma página com navegador real (`scripts/renderizar_pagina.js`, cliente identificado), preserva o texto visível como evidência e registra na mesma fila do canal 1 a página e cada link candidato. Era necessário porque o canal 1 é a API do WordPress e ela não responde em boa parte dos portais: na releitura de 23/09, os oito alvos de MT, SP, PR e SE devolveram **404, 410, JSON inválido ou 401** — perda de recall por camada, nunca ausência de plano. O `401` de SE é recusa e segue respeitado.

**Onde o rastro quase ficou incompleto.** O navegador não passa por `buscar()`, então os acessos do renderizador — justamente os que contrariam o pedido do sítio — não estavam sendo registrados. Corrigido no próprio canal, e travado por autoteste que lê o código-fonte e reprova se a chamada ao rastro desaparecer.

**Registrado em três lugares, que agora dizem a mesma coisa:** `CLAUDE.md` (regra de trabalho), `METODOLOGIA.md` §11 (a régua, com os dispositivos e o precedente) e `coletores_base.buscar()` (o comportamento). Antes desta entrada eram três respostas diferentes para a mesma pergunta.

**Teste.** Onze casos no autoteste novo (`scripts/testar_robots.py`), todos sem rede, bloqueantes em `portoes.yml` — o repositório vai a **54 portões**: grupo `*` contra grupo com o nosso nome (RFC 9309 § 2.2.1), `4xx` como ausência de restrição (§ 2.3.1), leitura uma vez por host, `Crawl-delay` respeitado e com teto de 60 s, rastro com URL/data/origem/cliente, rotação nos 200 últimos com a contagem total preservada, cliente nunca disfarçado, e dois testes que leem o código-fonte de `buscar()` e do canal renderizado. Verificação ao vivo no MT: o segundo acesso ao mesmo host esperou **28,4 s** do pedido de 30 s, e os quatro acessos ficaram no registro. Autotestes dos coletores que passam por `buscar()` verdes; consistência, `recalcular_mare --check`, evidências, escrita portável e portão 12 verdes.

## §184 · O endereço do órgão deixa de ser palpite: busca ativa nas 27 UFs, com trilha e confiança declaradas · 23/09/2026

Classe **correção de instrumentação**. Nenhum número do índice muda. Muda de onde a coleta vai buscar documento em 20 dos 54 alvos — e o que o projeto diz quando não acha.

**O que estava errado.** `dominio_para()` chutava `defesacivil.<uf>.gov.br` e `saude.<uf>.gov.br`, com sete correções feitas à mão no §179. A editoria apontou o caso do PR em 23/09, e ele é o tipo do erro: o chute pode falhar por razões que nada têm a ver com existir ou não plano. São três, todas medidas hoje: o subdomínio **não existe** (a Defesa Civil da PB fica sob o Corpo de Bombeiros), **existe só com `www.`**, ou **responde sendo outra coisa**. Cada uma vira lacuna falsa — ausência de busca publicada como ausência de plano, que é exatamente o que o §11 proíbe confundir.

**A busca ativa.** `descobrir_dominios.py` testa até dez padrões declarados por UF e setor (`defesacivil`, `www.defesacivil`, `cbm`, `bombeiros`, `cedec`, `sedec`, portal do estado; e para saúde `saude`, `ses`, `sesa`, `sesau`, `sus`) e **só aceita quem se identifica como a instituição procurada**: identidade no `<title>` é confiança **alta**, no corpo é **média**, e quem responde sem se identificar **não é escolhido** — endereço que responde sem se nomear daria aparência de busca feita. A trilha inteira fica gravada em `data/dominios_oficiais.json`, inclusive os candidatos que falharam: saber que `cbm.<uf>.gov.br` não existe é informação, não ruído. Disciplina do §11 mantida: cliente identificado, uma requisição por domínio a cada 2 s, e `403` anotado como recusa que não se contorna (§170).

**Resultado: 54 alvos, 47 com domínio identificado** — 29 com identidade no título, 18 no corpo — e **7 sem domínio**, cada um com o motivo em vocabulário que distingue o que é diferente. **Vinte diferem do palpite:**

- **15 só por causa do `www.`** — AL e MA (saúde), CE (os dois setores), DF, MS (os dois), PA, PE (os dois), PI, RN (os dois), TO. É o caso que a editoria apontou, multiplicado por quinze.
- **5 são outro órgão ou o portal do estado:** a defesa civil de **GO**, **PB**, **TO** responde em `bombeiros.<uf>.gov.br`, e a de **AM** e **RR** em `cbm.<uf>.gov.br` — Corpo de Bombeiros, que é onde a defesa civil estadual costuma morar.

**A ordem de prova, declarada em código.** `dominio_para()` resolve nesta sequência: identidade no título (a prova mais forte) → curadoria humana do §179 → identidade no corpo → palpite, **agora explicitamente por último**. A busca ativa confirmou 11 das 13 curadorias manuais, **corrigiu uma** (PE defesa civil: a curadoria apontava o portal do estado, `www.pe.gov.br`; existe `www.defesacivil.pe.gov.br`, que se nomeia no título) e não alcançou uma (RO saúde: `sesau.ro.gov.br` não resolveu no DNS hoje, e a curadoria segue valendo por ser mais forte que o palpite).

**As sete lacunas, nomeadas pelo motivo — e nenhuma é "não tem plano".** AP (os dois setores) e parte de RJ, RO, PB: **certificado TLS que não valida**, que é achado sobre o sítio do estado e não se contorna; AM saúde: DNS inexistente em seis candidatos e **404** nos dois que resolvem; RJ, RO e PB: o portal do estado responde mas não se nomeia como a secretaria. Antes desta entrada, os sete apareceriam como "nenhum candidato respondeu se identificando" — frase que escondia quatro situações distintas.

**Dois defeitos meus, achados na primeira execução real e consertados aqui.**

*O primeiro estava latente no §181, já mesclado.* Ao fazer a sonda de camada registrar o silêncio, usei a decisão `"nada localizado"` — valor **reservado à bateria municipal completa**: `recalcular_mare.py` o lê para elevar o nível de verificação do município, `verificar_consistencia.py` reprova se ele aparecer sem `nivel="municipal_completo"`, e o `assert` de `log_busca()` derruba a chamada. Nunca havia rodado porque só dispara em execução com rede — e derrubou a varredura no quinto alvo. O vocabulário ganha **`"consultado sem achado"`**, para a sonda de UF registrar que olhou sem entrar pela porta da verificação municipal. Três casos novos no portão do vocabulário, incluindo uma varredura que reprova se **qualquer** script voltar a logar `"nada localizado"` sem o nível.

*O segundo era a régua de identidade.* A marca `"secretaria de estado da saude"` não casou com o título real da SES-MG — **"Home | Secretaria De Estado De Saúde De Minas Gerais"** —, porque o órgão escreve "de saúde", não "da saúde". Uma preposição derrubou a identificação de um domínio que responde e se nomeia, e MG entrou como lacuna falsa. As marcas passam a ser expressões (`secretaria[^.]{0,30}\bsaude\b`), e o caso real da SES-MG virou teste.

**Teste.** Nove casos no autoteste do script, todos offline com rede injetada: ordem de prova, identidade no título e no corpo, parada no primeiro de confiança alta, página que não se identifica, `403` como recusa, motivo separando TLS de ausência, e a preposição da SES-MG. Autoteste bloqueante em `portoes.yml` — o repositório vai a 53 portões. Consistência, `recalcular_mare --check`, evidências, escrita portável e portão 12 verdes.

## §183 · O que o defeso eleitoral veda, conferido na norma: propaganda, não dado · 23/09/2026

Classe **registro metodológico**. Nenhum número, nenhuma página e nenhum texto público mudam. Muda a régua com que o Monitor interpreta um sítio oficial que sai do ar citando o período eleitoral — e essa régua vinha sendo aplicada sem estar escrita.

**Por que a pergunta surgiu.** O §182 mostrou que, das 31 fontes que o projeto tratava como suspensas por defeso, 22 não estavam: cinco suspendiam apenas **notícia institucional** e 17 não declaravam suspensão alguma. A editoria formulou a dúvida certa: o defeso suspende defesa civil e saúde? A resposta não podia ser inferência — tinha de vir da norma.

**O que a norma diz.** A **Lei 9.504/97, art. 73, VI, "b"** veda ao agente público *autorizar publicidade institucional* de atos, programas, obras, serviços e campanhas nos três meses anteriores ao pleito, ressalvados os produtos e serviços com concorrência no mercado e a grave e urgente necessidade pública **reconhecida previamente** pela Justiça Eleitoral. É restrição de **propaganda**.

**O que a norma preserva expressamente.** A **Resolução TSE nº 23.735/2024, art. 15, §§ 2º, 3º e 4º** estabelece que manter páginas na internet para cumprir os deveres do **art. 48-A da LC 101/2000** (transparência fiscal), dos **arts. 8º e 10 da Lei 12.527/2011** (LAI — divulgação de informação de interesse coletivo independentemente de requerimento) e do **art. 29, § 2º, da Lei 14.129/2021** **não configura publicidade institucional vedada**. O que se exige é *adequar* a página: retirar nome, símbolo, slogan e elemento de enaltecimento pessoal ou governamental. A jurisprudência acompanha — TSE, **AgR-REspe nº 18241** (26/09/2017): conteúdo antigo e meramente informativo no sítio oficial não é conduta vedada; **AgR-RO nº 187415** (29/05/2018, rel. Rosa Weber): o exame é caso a caso, nunca em abstrato.

**A síntese, que é a régua:** a norma manda tirar a **propaganda**, não o **dado**.

**Consequência operacional, e é ela que entra no método.** Sítio que retira do ar PLANCON, plano estadual de saúde ou portal de transparência citando o período eleitoral **não está cumprindo exigência legal — está excedendo-a**, e o dever da LAI continua valendo. Então o Monitor: (a) registra o fato observado — o sítio declara o próprio conteúdo indisponível —, com evidência e data; (b) classifica isso como **lacuna de transparência declarada**, nunca como impedimento legal à publicação; (c) distingue o escopo do que o próprio sítio declara (§182), porque suspensão de notícia institucional não fecha o canal de documento. O excesso de cautela tem casos documentados fora do ciclo do El Niño — Ibama, INPE, Arquivo Nacional, Agência Brasil — e é matéria jornalística do próprio Monitor, não pressuposto do método.

**Onde isto vive.** `METODOLOGIA.md` §24 (período eleitoral), com os dispositivos citados e a consequência escrita. **Nenhuma frase pública foi alterada nesta entrada**: como a régua toca o que o site afirma sobre estados, a redação ao leitor é decisão da editoria, e fica aguardando sua palavra.

**O que ficou pendente, nomeado.** A releitura das fontes que estavam falsamente suspensas — MT, SP, PR e SE, defesa civil e saúde — porque, se o canal de documento estava aberto, havia plano alcançável que o Monitor não estava lendo.

## §182 · "Fonte suspensa por defeso" era, em 22 de 31 casos, coisa nenhuma — o detector casava em atributo de imagem e não distinguia notícia de serviço · 23/09/2026

Classe **correção de leitura com efeito no material público**. Nenhum número do índice muda. Muda quantas fontes o Monitor declara suspensas: de **31 para 9**.

**Como isto apareceu.** A sonda de camada do §181 bateu em 27 portais estaduais e o detector de defeso (PR-N0 §1.5) marcou **27 fontes como suspensas** numa única rodada. Número alto o bastante para desconfiar — e o número **é publicado**: `gerar_pdf_indice.py` imprime "Fontes suspensas por defeso na última rodada: N" no PDF do índice, e quatro páginas do site leem o arquivo.

**Primeiro defeito: o padrão casava em atributo.** A detecção rodava sobre o HTML cru. Em `saude.pi.gov.br`, o que casou foi `alt="banner periodo eleitoral"` — o texto alternativo de uma **imagem** de banner do Detran. A página estava no ar, servindo conteúdo, e foi marcada como suspensa. Agora a busca ocorre no **texto declarativo**: texto visível, `<title>` e `<meta name="description">` — que é onde os avisos reais moram (`<title>Suspensão Temporária | Período Eleitoral 2026</title>` no MA; `<meta description>` "em função do período eleitoral, esta página está indisponível" no MG). Atributo de imagem, classe de CSS e endereço de link ficam fora.

**Segundo defeito, e o mais grave: o detector não distinguia notícia de serviço.** Nas palavras dos próprios sítios, em 23/09:

- **MT:** "em cumprimento à legislação eleitoral, o Governo de Mato Grosso suspende, a partir deste sábado (4.7), a exibição das **notícias institucionais** publicadas neste portal";
- **SP:** "os conteúdos **desta seção de notícias** ficarão indisponíveis de 4 de julho de 2026 até o final da eleição";
- **PR** (defesa civil e saúde): cada item da lista de notícias foi trocado por "conteúdo indisponível devido ao período eleitoral" — a lista de notícias, não o portal;
- **MA:** "Suspensão Temporária | Período Eleitoral 2026" **no título da página** — aí sim, o sítio inteiro.

O que a Lei 9.504/97 restringe é **publicidade institucional**, e é isso que os estados dizem estar suspendendo. Chamar de "fonte suspensa" um portal que tirou do ar a seção de notícias esconde que o plano de contingência continua servido — e transforma uma restrição de propaganda em lacuna de transparência que ninguém declarou. `classificar_defeso()` passa a devolver o **escopo**: `sitio`, `noticias` ou nenhum. Só `sitio` fecha o canal que o Monitor usa.

**Terceiro defeito, este meu, e pego antes de virar dado.** A primeira versão do script de reavaliação decidia pela evidência preservada — que é **truncada** nas primeiras 20 mil letras do corpo servido. Em `defesacivil.pr.gov.br` o aviso aparece depois desse corte: a evidência não trazia o padrão, e o script **reabriu a fonte como se estivesse no ar**. Não achar numa cópia truncada não é prova de ausência. A régua ficou assim: casou na evidência → segue suspensa; não casou e a evidência está **inteira** → reaberta; não casou e a evidência está **truncada**, ou não existe → **inconclusivo, e inconclusivo nunca reabre sozinho**; com `--refazer-busca`, a fonte decide e a procedência da decisão fica gravada (`evidência preservada` ou `nova busca em <data>`). Falha de rede mantém o estado, pela regra do §170: ausência de resposta não é prova de nada.

**O resultado, item por item.** Das 31 fontes registradas como suspensas: **9 continuam** (8 porque o sítio declara o próprio conteúdo indisponível — MA, MG em três caminhos, BA, SE em dois, mais o painel nacional em "edição de defeso" — e 1 mantida por não responder à nova busca, com o motivo escrito); **5 eram suspensão de notícia institucional** (PR defesa civil, PR saúde, MT saúde, SP saúde, SE saúde) e o canal de documento delas está aberto; **17 não traziam declaração nenhuma** — casamento em atributo, banner ou menção de calendário. Cada registro guarda o escopo, a data da reavaliação e a procedência da decisão; **nenhum foi apagado**, porque a detecção aconteceu e isso é parte do histórico.

**O que isto abre, e fica declarado como pendência.** Se o que se suspende é publicidade institucional, então o PLANCON e o plano de saúde de MT, SP, PR e SE estavam alcançáveis enquanto o Monitor os tratava como fonte suspensa. A releitura dessas fontes é o passo seguinte — junto com a conferência na legislação (Lei 9.504/97 art. 73, VI, "b" e as resoluções do TSE para 2026) de até onde vai a restrição, que é decisão de redação e não de código, e por isso não entra nesta entrada.

**Teste.** Portão do detector de defeso (bloqueante desde a v2.2.4) com **13 casos**, oito deles com texto real das páginas de 23/09: atributo de imagem, título, descrição, texto visível, classe de CSS, notícia institucional em duas redações e sítio inteiro. Autoteste do script de reavaliação com as quatro situações da régua, inclusive a que meu próprio erro produziu (truncada não reabre). Evidências, consistência, `recalcular_mare --check`, escrita portável e portão 12 verdes.

## §181 · A receita do AM aplicada às outras UFs: os oito painéis abertos um por um, e a sonda que ficava muda quando não achava · 23/09/2026

Classe **coleta e correção de instrumentação**. Nenhum número do índice muda e nenhum registro novo entra no banco. O que este lote entrega é uma **resposta medida** a uma pergunta que estava aberta, e o conserto do instrumento que tornava a resposta ilegível.

**A pergunta.** O §180 documentou 51 planos municipais do AM a partir de um painel Power BI. A pergunta imediata da editoria: existem painéis assim em outras UFs, publicando o que o do AM publica?

**A sonda, rodada de dentro do Brasil.** 27 UFs × 2 setores × 3 páginas, com o intervalo de 2 s por domínio que o §11 fixa: **248 execuções**, 13 pistas, **uma pista nova** — um PDF no Google Drive da Defesa Civil do AC. O catálogo passou de 7 para 8 painéis.

**Os oito abertos em navegador real, um por um.** A sonda diz que existe uma camada; só a abertura diz o que há dentro:

| UF | setor | o que é | traz planos municipais |
|---|---|---|---|
| **AM** | defesa civil | tabela dos 62 municípios com ano e link do documento | **sim** (coletado no §180) |
| MG | defesa civil | boletim informativo: meteorologia, série histórica, indicadores de seca | não |
| ES | defesa civil | "Relatório de Voluntários (Público) — CEPDEC" | não |
| RJ | defesa civil | dashboards operacionais: serviço 24h, notificações por tipo, GRAC, S2iD | não |
| GO | saúde | painel de apresentação e cronograma | não |
| SC | saúde | catálogo telefônico interno da secretaria (293 linhas) | não |
| PR | saúde | formulário "Notifique Aqui CIEVS/PR" — canal de entrada | não |
| AC | defesa civil | PDF de uma página: siglas das divisões internas do CEPDC | não |

**O painel do AM é, por ora, único.** Não há mais nada a agregar desta camada — e isso é resultado, não frustração: a hipótese "deve haver vários painéis como o do AM" foi testada e não se sustentou. Cada verificação fica registrada na fila (`status: verificado_em_navegador`, com `conteudo`, `traz_planos_municipais`, `coletar` e o motivo), para a próxima sessão não reabrir os mesmos oito e redescobrir o boletim meteorológico de MG.

**O caso de SC merece nome próprio.** O painel de saúde de SC é um **catálogo telefônico de servidores** — local, andar, superintendência, setor, nome, ramal. São dados pessoais sem nenhuma relação com o que o Monitor mede: preservá-los violaria a minimização (LGPD art. 6º, III), que é a mesma fundamentação da redação de CPF de 12/09. A renderização de teste foi apagada do disco e nada dela foi comitado. Na fila, o item fica `coletar: false` com o motivo escrito — declarado, para ninguém tentar de novo por descuido.

**O defeito do instrumento — e ele enganou a própria leitura desta rodada.** A sonda registrava **achado** e **falha**, e ficava **muda quando consultava e não encontrava nada**. Consequência prática, acontecida aqui: ao ler o log da rodada, a primeira conclusão foi "20 das 27 UFs não responderam" — falsa, porque o sucesso sem achado não deixava rastro, e só as falhas apareciam. "Consultei e não havia painel" e "nunca consultei" eram indistinguíveis, que é justamente a confusão que o projeto proíbe entre ausência de dado e dado não coletado.

**Além disso, toda falha se chamava "acesso recusado"**, e isso mentia nas duas direções. Das 235 falhas da rodada: **80 eram HTTP 404** nos caminhos adivinhados (`/planos`, `/defesa-civil`) — caminho que não existe não é fonte que recusa —, **140 eram falha de conexão** (DNS, TLS, reset), e **3 eram 403**, o único caso em que o servidor de fato respondeu não. A distinção é a que o §170 fixou: recusa se respeita; ausência de resposta não é recusa.

**O conserto.** `classificar_falha()` separa os quatro casos (404/410 → nada localizado, com o motivo; 401/402/403/429/451 → acesso recusado; 5xx → erro de servidor; sem resposta → erro declarado como tal). A sonda passa a registrar `nada localizado` quando consultou e não achou, com quantas páginas consultou. E `anotar_verificacao()` grava na fila o que a abertura mostrou, com vocabulário fechado: `traz_planos_municipais` é `true`, `false` ou `null`, e `coletar: false` **exige motivo escrito**. A anotação é triagem, nunca promoção: `promovivel` e `documento_oficial_confirmado` continuam intocados (R7).

**Sete casos negativos novos** no autoteste da sonda (que já é portão bloqueante desde o §164), entre eles os quatro tipos de falha e a recusa de anotar "não coletar" sem motivo.

**O que este lote não entrega, dito com clareza:** nenhum plano municipal novo, nenhum registro pontuável novo, nenhuma UF nova documentada. O caminho que sobra para ampliar cobertura não é painel — é o que o §179 já nomeou: curadoria de domínio por UF, e pedido de LAI onde o documento não está publicado.

**Teste.** Autoteste da sonda verde com os sete casos novos; portão de evidências, consistência, `recalcular_mare --check` e escrita portável verdes; portão 12 em árvore limpa.

## §180 · Os 51 planos do AM lidos de dentro do Brasil — e o ato que o coletor achava que estava lendo · 23/09/2026

Classe **coleta e correção de leitura**. Nenhum número do índice muda e nada é promovido: a fila do painel do AM é R7, promoção humana. O que muda é o que está preservado (51 documentos que não existiam no repositório) e o que o coletor aceita chamar de "ato do plano".

**O que o §170 deixou em aberto.** A rodada de 23/09 leu os 62 municípios do painel e **nenhum documento abriu**: `Connection reset by peer` nas 62 tentativas, com o painel Power BI respondendo normalmente no mesmo runner. O §170 registrou a distinção que decide este caso: um `403` é o servidor dizendo **não**, e não se contorna; **reset de conexão é ausência de resposta, em que não há recusa a respeitar**.

**A rodada feita daqui.** A sessão de 23/09 roda numa máquina no Brasil. Mesmo endereço, mesmo User-Agent do projeto, mesmo código: o renderizador abriu o painel (62 linhas, 51 com link) e `www.defesacivil.am.gov.br` entregou os documentos — o PLANCON de Tabatinga, 18,83 MB, em 2,1 s. **51 de 51 documentos abriram, todos como `fonte direta`**, nenhum por captura de arquivo. A rota era o problema, não o servidor.

**E aí a leitura mostrou o defeito que o fixture escondia.** A primeira rodada devolveu **16 itens `documentado`** — e os 16 estavam errados. `ler_ato` pegava a primeira ocorrência de "⟨tipo⟩ nº ⟨n⟩ de ⟨data⟩" no documento, e todo PLANCON do modelo estadual traz, na seção de demografia, **"Ato de Criação: Lei Estadual Nº 96 DE 19 de dezembro de 1955"**. Treze dos dezesseis "atos" eram anteriores a 2015: 1874, 1881, 1897, 1938, 1955 duas vezes, 1956, 1974, 1975, 1982, 2008, 2012, 2013. Nenhum foi promovido — `promovivel` nasce `false` e o §156 exige ato do ciclo lido no documento —, mas a fila publicaria a lei de criação do município como se fosse o ato do plano, e quem revisa confiaria no campo.

**Três armadilhas, não uma.** Filtrar contexto de criação derrubou 13 e deixou 3, cada um de um tipo diferente — e os três também estavam errados:

- **Coari:** "RAIMUNDO … Coordenador Municipal de Proteção e Defesa Civil / Decreto n° 143-PMC-GP, de 01 de setembro de 2023" — o ato que **nomeia o coordenador**, colado na assinatura dele.
- **Rio Preto da Eva:** "Portaria n° 007 de 06 de Janeiro de 2026", mesma estrutura de assinatura.
- **Manicoré:** "Lei nº 14.750, de 12 de dezembro de 2023 – Atualiza a PNPDEC" — **citação numa lista de fundamentação legal**, com "plano de contingência" na mesma frase, que é justamente o que um filtro de vizinhança não distingue.

**A régua final.** O ato tem de **se apresentar como o ato do plano**: verbo instituidor (`institui`, `fica instituído`, `aprova`, `homologa`, `adota`) **e** palavra do plano (`plano de contingência`, `PLANCON`, `plano municipal de contingência`) na oração do ato ou na ementa seguinte, **sem** marcador de citação legal (`atualiza a`, `Política Nacional`, `PNPDEC`, `SINPDEC`, `transferências de recursos`, `lei federal`…). Fora disso o item fica `declarado` — que é a resposta honesta quando o documento não diz qual ato o instituiu. Some-se o piso de plausibilidade: ato anterior a 2015 não institui plano deste ciclo.

Detalhe de implementação que custou uma rodada: a janela de contexto precisa estar **ancorada no casamento**. Contada do início da fatia, ela cortava antes da ementa quando havia ponto no meio de um número — `População: 25.172` quebrava a leitura do decreto seguinte.

**Segundo defeito, no ano declarado.** As 62 linhas vinham com `ano_do_plano: null`. A célula da coluna **Plano** chega do Power BI com o rótulo de interface `Formatação Condicional Adicional`, e o casamento de coluna por substring de `"ano"` batia nela antes de chegar em `"ano do plano"` — porque **"plano" contém "ano"**. A limpeza do rótulo passou para antes do casamento, o casamento ficou estrito e o ano sai por expressão de quatro dígitos. De tabela: célula que é **só** o rótulo passa a ser ausência, não texto — eram 53 das 62 linhas na coluna Calha, que herdam o grupo visualmente. Com isso o painel volta a declarar o que declara: **42 municípios com plano de 2026**, 6 de 2024, 2 de 2025 e 1 de 2023.

**O resultado, medido e sem enfeite.** 62 linhas; **51 documentos preservados como prova, todos da fonte direta** (23 com cópia binária no repositório, 52,1 MB; os demais acima do teto de 5 MB, com hash e texto); **zero `documentado`**, porque nenhum dos 51 declara no próprio corpo o ato que o instituiu na forma que a régua exige; **51 `declarado`** com o ano do painel; 11 sem plano declarado; **zero promovível**. O estado declara; o documento, como está publicado, não prova o ato — e é isso que a fila registra.

**Nove casos novos no autoteste do coletor** — sete negativos e dois positivos, quase todos com texto real dos documentos do AM (48 casos no total): ato de criação do município, portaria e decreto de nomeação do coordenador, citação da PNPDEC, Lei 12.608/2012 citada de passagem, ato que institui, ato que aprova o PLANCON, o ano sobrevivendo ao rótulo, e o ato do plano preferido mesmo vindo depois do de criação. Um teste antigo foi corrigido junto, e a razão fica escrita: `"Portaria nº 12/2026, de 30 de 06 de 2026"` sozinha passava — era esse contrato frouxo que deixava a nomeação virar ato do plano.

**Teste.** Suíte completa de portões rodada nesta máquina, agora com Node e Chromium instalados (só o portão 17 fica de fora, por exigir privilégio de link simbólico que o Windows não concede). Portão de evidências verde com os 51 itens novos íntegros; portão 12 em árvore limpa; autotestes dos coletores verdes.

## §179 · O registro que faltava: duas mudanças mescladas sem entrada, e a curadoria de domínios da defesa civil · 23/09/2026

Classe **correção do registro público**. Nenhum código de produção muda aqui além de uma referência errada em comentário; o que muda é o `CHANGELOG.md` passar a conter o que a `main` já contém.

**A auditoria.** Cruzando os **150** títulos `## §N` do `CHANGELOG.md` com os números citados nas mensagens de commit da `main`, aparecem duas mudanças mescladas **sem entrada nenhuma**:

1. **§171 — rodada completa sob demanda** (PR #358, `8220dcf`). Código na `main`, portão fixando as quatro propriedades, e o `CHANGELOG` pulando de §172 para §170. A entrada foi escrita agora, no lugar cronológico, a partir do código mesclado (conferido: `FORCAR_RODADA_COMPLETA` em `atualizar.py:168`, a entrada `rodada_completa_agora` e o teto em `atualizar.yml`, as quatro asserções em `scripts/testar_cadencia_publicacao.py`).
2. **A curadoria de domínios da defesa civil** (`7104d42`), que a mensagem do commit numerou como "§164" — número que na mesma leva já pertencia a outra entrada. Ficou sem entrada própria e com o comentário do código citando uma seção que fala de outra coisa. Passa a ser esta.

**A curadoria, que é o conteúdo perdido.** Segundo o registro da rodada de 23/09/2026 (mensagem de `7104d42`), na primeira rodada real da sonda de camada **13 das 27 UFs não responderam a nada**, porque o palpite `defesacivil.<uf>.gov.br` estava errado para elas — a lacuna de curadoria que a própria docstring de `descobrir_planos.py` declara. Sondados seis padrões por UF, **sete** responderam HTTP 200 e entraram em `DOMINIOS_CONHECIDOS`, conferidos um a um: **AL**, **CE**, **MS**, **PB** (a Defesa Civil fica sob o Corpo de Bombeiros), **PE** e **PI** (sem domínio próprio: portal do estado) e **SP**. Seguem **sem domínio localizado**, como lacuna declarada e nunca como ausência de plano: **AP, DF, RN, RO e TO** — e **SE**, que responde mas recusa o robô. O comentário no código passa a citar §179.

**No mesmo commit, uma correção de segurança pega pelo CI.** `coletar_painel_am.yml` usava `actions/upload-artifact@v4` sem fixar por SHA, e o projeto exige SHA em toda Action (`scripts/verificar_seguranca.js`). Foi fixado no mesmo SHA que `atualizar.yml` já usava — conferido hoje: `ea165f8d…`.

**Os outros buracos da numeração, conferidos.** Além de §160 (aplicado em ramo próprio hoje) e §171, a sequência não tem §113, §114 e §115 — e **nenhum commit do repositório cita esses três números**. São números pulados, não trabalho perdido. Fica registrado para a próxima auditoria não caçá-los.

**Por que isto não vira portão.** A regra óbvia — "a numeração não pode ter buraco" — brigaria com o fluxo de PRs paralelos: enquanto um ramo carrega o §178 e outro o §179, cada um vê um buraco que não é seu, e o portão fecharia vermelho nos dois. Em vez de porta, fica a **conferência**, de uma linha, para rodar quando se quiser auditar o registro:

```
python3 -c "import re;from pathlib import Path;n=[int(x) for x in re.findall(r'^## §(\d+)',Path('CHANGELOG.md').read_text(encoding='utf-8'),re.M)];print('buracos:',sorted(set(range(min(n),max(n)+1))-set(n)))"
```

**Teste.** Portão 12 em árvore limpa (o `CHANGELOG.md` entra no manifesto), consistência e workflows verdes.


## §178 · A escrita portável deixa de depender de atenção: 78 sítios corrigidos e um portão que impede a volta · 23/09/2026

Classe **encanamento com efeito na auditabilidade**. Nenhum dado, número ou página muda — no runner (Linux) o comportamento é idêntico byte a byte. O que muda é quem pode reproduzir o que o robô publica.

**A série que estava aberta.** O §163 corrigiu 30 chamadas em oito arquivos e nomeou o resto: escrita em modo texto sem `newline="
"` faz o Python traduzir cada `
` para `
` no Windows. O arquivo sai em CRLF, o hash deixa de bater com o selado em `docs/MANIFEST_SHA256.txt` e o derivado regenerado fora da Action não é o mesmo arquivo. O defeito é **invisível no runner** e só aparece na máquina de quem tenta reproduzir — que é exatamente quando o repositório precisa ser auditável.

**O tamanho do que faltava, medido.** **78 sítios em 39 arquivos**: `data/municipios.json` (`verificar_vigencia.py`), `data/meta.json` (`atualizar.py`), as filas de pista (`monitorar_imprensa_regional.py`, `monitorar_imprensa_saude.py`, `monitorar_sinais_federais.py`, `monitorar_atos_resposta.py`, `monitorar_politica_por_inteiro.py`), os modelos de pedido de LAI, `docs/FILA_PISTAS.md`, os dez sítios do juiz, o índice de evidências na remediação de CPF, as páginas de reserva estática e o resto. Corrigidos por varredura sobre a **árvore sintática** — `ast`, não expressão regular sobre a linha, que confunde comentário e docstring com código —, um a um, e cada arquivo recompilado depois.

**A correção que importa é a porta, não a varredura.** `scripts/verificar_escrita_portavel.py` é portão **sempre bloqueante** (roda no bloco que não depende de o dado ter mudado, porque o defeito entra por `*.py`): recusa `open(..., "w"/"a"/"x")` e `write_text(...)` sem `newline` — e também `csv.writer`/`csv.DictWriter` sem `lineterminator`, cujo padrão do módulo é CRLF em **qualquer** sistema. Distingue modo binário, leitura, comentário e docstring. Exceção justificada se declara na própria linha (`# escrita-nao-portavel-ok: <motivo>`) — não há nenhuma hoje. Autoteste com 17 casos nas duas direções, rodado antes da varredura do repositório.

**Testado nas duas direções.** Portão verde sobre os 121 arquivos Python do repositório. Depois, tirando de propósito o `newline` de uma linha (`atualizar.py:336`, o que grava `data/meta.json`), o portão fecha vermelho apontando arquivo e linha; restaurada, verde.

**Teste.** Os 31 portões de dado verdes (o 17 não roda nesta máquina: exige privilégio de link simbólico no Windows), incluindo os autotestes dos oito coletores, do juiz, das sondas e das três rotinas de evidência tocadas aqui; portão 12 em árvore limpa; workflows válidos. O repositório passa a ter **51 portões**.


## §177 · OCR do PLANCON escaneado: a cópia legível que faltava, e a regra que vem com ela · 23/09/2026

Classe **prova preservada**. Nenhum número do índice muda, e nenhuma leitura de máquina passa a usar OCR — o contrário: a separação entre "cópia preservada" e "insumo de julgamento" vira regra travada em portão.

**A lacuna que isto fecha.** O §174 deixou quatro registros pontuáveis em `LACUNA_DECLARADA`, bloqueante a partir de 31/10/2026: Anchieta, Itaguaçu, São José do Calçado e Venda Nova do Imigrante, todos do ES. O PLANCON de cada um tem de 10 a 19 MB — acima do teto de cópia de 5 MB —, é **escaneado** (cada página é uma imagem), a extração de texto devolve **zero caractere** e o Wayback não tem snapshot. Não é prova fraca: é prova nenhuma.

**O recurso.** `preservar_evidencias.py --ocr` rasteriza a 200 DPI com `pypdfium2` e passa cada página pelo Tesseract, gravando `evidencias/<sha256>.ocr.txt` — com marcador `=== página N (OCR) ===`, CPF redigido **antes** do hash e o hash registrado em `ocr_hash`, ao lado de `ocr_paginas`, `ocr_caracteres`, `ocr_em` e `ocr_motor`, que guarda a versão do Tesseract, o modelo e o DPI que produziram aquele texto. A fila é idempotente por construção: só entra quem foi lido e não tinha texto (`caracteres` abaixo do piso de 200), e sai ao ganhar OCR.

**A regra que vem com o recurso, e é a parte que importa.** O texto de OCR é **cópia preservada e legível por gente — nunca insumo do classificador nem do juiz**. O ato que pontua no índice tem de ser lido no próprio documento (§156); OCR erra caractere, e erro de leitura não pode virar degrau publicado nem nota. A separação é **estrutural**, não recomendação: (1) o OCR mora em campo próprio e em arquivo próprio, nunca em `texto_arquivo`; (2) `classificar_saude_no_plano.py` passa a ler por `texto_para_leitura_automatica()`, que recusa `ocr_arquivo` e recusa até um `texto_arquivo` que aponte para `.ocr.txt`, com autoteste que reprova se OCR entrar por ali; (3) o portão 6 recusa item em que `ocr_arquivo` e `texto_arquivo` sejam o mesmo arquivo; (4) o juiz nunca leu campo de evidência — ele busca o documento na URL —, então continua fora por desenho. O motor do índice não lê nenhum dos dois. Registrado em `METODOLOGIA.md` §10.1 como peça 4 da leitura contínua.

**Medido aqui, não prometido.** PLANCON de São José do Calçado: 13,5 MB baixados em 4 s, hash idêntico ao registrado; duas páginas rasterizadas em 2 s; OCR em 1,3 s e 1,6 s, devolvendo 223 e 375 caracteres — a primeira página traz "PREFEITURA MUNICIPAL DE SÃO JOSÉ DO CALÇADO · DEFESA CIVIL · PLANO DE CONTINGÊNCIA" e a segunda o coordenador da COMPDEC. **Com o modelo em inglês**, o único instalado nesta máquina: por isso o texto sai com acento trocado ("Administragao", "sAO JOSE DO CALCADO"). É exatamente a razão de a cadência instalar `tesseract-ocr-por`, e de o portão cobrar essa instalação.

**A cópia foi produzida, e a lacuna fechou.** Com o modelo português instalado nesta máquina (decisão da editoria de 23/09), a rodada real preservou **cinco** cópias legíveis: Anchieta (68 páginas, 94.089 caracteres), Itaguaçu (78, 102.678), São José do Calçado (14, 15.027), Venda Nova do Imigrante (70, 106.040) — as quatro da lacuna declarada — e **Sooretama/ES** (13, 19.983), um quinto PLANCON escaneado que não estava na lista porque tem cópia binária (2,8 MB, abaixo do teto), mas cuja leitura também devolvia zero caractere: tinha prova, não tinha texto. O portão 6 passa a fechar **93 de 93 registros pontuáveis com prova preservada, zero em lacuna declarada**, e `LACUNA_DECLARADA` fica **vazia de propósito** — o mecanismo continua de pé para a próxima lacuna que precise ser declarada. O passo na cadência segue valendo para o que vier depois: roda após a leitura, com teto de 30 min. Nenhum pacote Python novo — `pypdfium2` e `Pillow` já vinham com `pdfplumber`; passam a ser declarados e travados em `requirements.txt`, porque a versão do rasterizador decide o pixel e o pixel decide o texto que fica preservado.

**O defeito que a primeira rodada real achou — no nosso lado.** As cinco cópias saíram em **CRLF**. O Tesseract do Windows devolve as quebras de linha em `''' + CR + NL + '''` no próprio stdout, e `newline="''' + NL + '''"` na gravação **não alcança isso**: ele traduz o que o Python escreve, não o `''' + CR + '''` que já vem dentro do texto. A cópia preservada ficaria diferente byte a byte da que o runner produz — a série do §163 outra vez, agora no conteúdo e não na escrita. Corrigido na origem (`ocr_pagina` normaliza), com defesa em profundidade em `gravar_ocr`, caso novo no autoteste (página com CRLF tem de sair em LF) e **regra nova no portão 6**: cópia preservada em CRLF reprova, nos três campos de texto, com ou sem hash registrado. Medido antes de escrever a regra: dos **249** arquivos preservados, só esses cinco tinham CRLF. Os cinco foram apagados e regravados pelo código corrigido — a diferença de contagem prova o conserto (Anchieta caiu de 97.368 para 94.089 caracteres, exatamente os 3.279 `''' + CR + '''` que o arquivo tinha).

**A trava, na mesma linha do §164 e do §174.** `checar_preservacao_na_cadencia()` passa a exigir, além de `preservar_evidencias.py` e do `--ler`, a chamada `--ocr` e a instalação do modelo português. Testado nas duas direções: com o passo trocado por `echo`, o portão fecha vermelho dizendo o que falta; restaurado, verde.

**Teste.** Portão 6 verde com os autotestes novos (prova por OCR com piso de caracteres, integridade do `.ocr.txt`, CRLF na cópia preservada, OCR que não ocupa o lugar da camada de texto) e **93 de 93 pontuáveis com prova**; autoteste do OCR sem rede e sem Tesseract, bloqueante em `portoes.yml`; autoteste da leitura automática de saúde com o caso do OCR; workflows válidos com teto em todo job; portão 12 em árvore limpa; `pip install -r requirements.txt` com os pins novos. Amostra conferida à mão: a página 2 do PLANCON de São José do Calçado lê "PREFEITURA MUNICIPAL DE SÃO JOSÉ DO CALÇADO … COORDENADORIA MUNICIPAL DE PROTEÇÃO E DEFESA CIVIL (COMPDEC) … DECRETO nº 7.717/2024" — com acentuação correta, que é o que o modelo inglês não entregava.


## §176 · O texto integral do diário oficial não guardava hash nenhum — e quatro itens prometiam um arquivo que não existia · 23/09/2026

Classe **correção de segurança do dado**. Nenhum número do índice muda. Fecha a lacuna que o §175 deixou nomeada.

**O que estava aberto.** O §175 passou a exigir `sha256(texto_arquivo) == texto_hash`. Mas a outra família de texto preservado — `texto_integral`, a edição inteira do diário oficial que o julgamento humano lê offline (decisão de 10/09) — não registrava hash de espécie alguma: **148 itens**, zero hashes. A integridade deles se apoiava no `.json` da resposta da API, cuja chave o portão confere; o texto em si, que é o que alguém abre para ler, não tinha com o que ser comparado.

**E quatro deles prometiam um arquivo que não existe.** `texto_integral` gravado em 12/09/2026, apontando para um `.txt` que **nunca entrou no commit da rodada** — conferido no histórico: `git log --all` não conhece nenhum desses quatro caminhos. O índice afirmava preservar o que não estava em disco, e nada acusava.

**Por que nada os procurava.** A fila da autocura (`scripts/preservar_textos_integrais.py`, que roda em toda rodada desde 10/09) saía só de `data/pistas_imprensa.json`, e só de pista com `origem == querido_diario`: 33 evidências de diário, todas com texto. Evidência preservada por `coletar_diarios_municipais.py` que **não gerou pista** ficava fora do alcance da rotina que existe justamente para completá-la. Quem tinha o defeito era invisível para quem o consertaria.

**O conserto, em quatro pontos.** (1) `preservar_texto_integral()` registra `texto_integral_hash` ao gravar — e também quando o arquivo **já existe**, curando o índice de quem foi preservado antes desta regra, sem mexer na data nem na origem da preservação original. (2) A fila da autocura passa a incluir o que o **índice** diz ter e o disco não tem, venha de pista ou não. (3) `selar_hashes()` preenche o hash ausente e **não resela divergência em silêncio**: arquivo que mudou depois de selado vira aviso e trava no portão, porque reselar apagaria o registro de que mudou (a mudança legítima conhecida — a redação de CPF — recalcula o hash na própria rotina, §175). (4) O portão 6 confere as duas famílias, e arquivo prometido pelo índice e ausente do disco reprova **mesmo sem hash registrado**.

**Rodado aqui.** Os quatro textos foram recuperados a partir do `.json` preservado (as URLs de edição do Querido Diário continuam no ar): 2,4 MB, 553 kB, 108 kB e 103 kB. Dois deles trouxeram CPF na edição e saíram redigidos na preservação, 2 em cada, com a redação registrada no log v2 — o defeito de 12/09 não republicou dado pessoal, porque a causa raiz já estava corrigida desde então. E **144 hashes** foram selados, fechando os 148. Como a autocura já está pendurada na cadência, a selagem e a recuperação passam a acontecer sozinhas a cada rodada.

**Teste.** Portão 6 vermelho antes do conserto, nomeando os quatro pelo hash, e verde depois (89 de 93 pontuáveis com prova, 4 em lacuna declarada do §174, 2.059 itens íntegros). Dois autotestes negativos novos e bloqueantes em `portoes.yml` (agora 30 portões de dado, 49 no total). Portão 12 em árvore limpa; log `data/log_buscas.json` cresceu de 26.774 para 26.776 execuções, append-only conferido.


## §175 · O hash do texto preservado não era conferido — e a rotina de redação de CPF o deixava para trás · 23/09/2026

Classe **correção de segurança do dado**. Nenhum número do índice muda; um item do banco passa a ter o hash que descreve o arquivo que está publicado.

**O achado.** O §174 tornou o texto extraído do PDF prova preservada — é o que sustenta 29 registros pontuáveis acima do teto de cópia de 5 MB. Mas o portão 6 conferia integridade só da **cópia binária** (`sha256(arquivo) == chave`); o `texto_hash` nunca era comparado com o arquivo em disco. Prova que ninguém confere não é prova verificável.

**Quem o quebrava.** `scripts/remediar_cpf_evidencias.py`, a remediação de 12/09/2026 que apagou 1.018 CPFs de 69 arquivos já publicados, regrava o `.txt` e **não recalculava** `texto_hash`. **Exposição medida:** 68 itens do banco carregam a nota de redação; desses, **um só** tem `texto_hash` — Maricá/RJ — e era exatamente o divergente. Os outros 67 são texto integral de diário oficial, que não registra hash próprio (ver a lacuna registrada abaixo).

**Três defeitos no mesmo caminho, além do hash.** `tamanho` descreve o arquivo apontado por `arquivo`; o código o sobrescrevia com o comprimento de **qualquer** arquivo regravado — inclusive o texto, que é outro arquivo do mesmo item. A escrita do `.txt` e a do próprio `data/evidencias.json` saíam sem `newline="\n"` (a série do §163): rodar a remediação no Windows regravaria toda a evidência em CRLF, mudando byte a byte o que os hashes selam. O índice passa a ser gravado por `gravar()`, que é atômico desde 21/09.

**O conserto, nas duas pontas.** No portão: `integridade_texto()` exige `sha256(texto_arquivo) == texto_hash` em todo item que registra os dois, com autoteste negativo permanente (hash trocado reprova, texto ausente reprova, item só com cópia binária passa). Na rotina: recalcula `texto_hash` e recontagem de `caracteres` quando o regravado é o texto do item, e `tamanho` só quando o regravado é o `arquivo`. Autoteste novo e bloqueante em `portoes.yml`, com as quatro regras.

**O passado, consertado pela própria rotina.** `reindexar_textos()` não toca no arquivo: o `.txt` publicado, já redigido, é a verdade — o índice é que estava atrasado. Rodado aqui, reindexou **um** item: Maricá/RJ, `texto_hash` `49e7cbf5…` → `b302f484…`. A contagem de caracteres não mudou (609.285) porque `[CPF REDIGIDO]` tem exatamente os 14 caracteres do padrão `NNN.NNN.NNN-NN` — coincidência do desenho da redação, não garantia; por isso a contagem é refeita a partir do arquivo, e não presumida.

**Lacuna registrada, com número.** Os **148** itens que guardam `texto_integral` (edição inteira de diário oficial) não registram hash nenhum desse texto — a integridade deles se apoia no `.json` da resposta da API, cuja chave o portão confere (147 dos 148). Quatro desses itens apontam para um `.txt` que **não está em disco**. Fica nomeado para a correção seguinte, que precisa de campo novo no índice e de reindexação dos 148.

**Teste.** Portão 6 verde, agora com a integridade do texto (89 de 93 pontuáveis com prova, 4 em lacuna declarada, 2.059 itens íntegros) — e vermelho, conferido antes do conserto, apontando o item de Maricá pelo nome. Os 29 portões de dado do executor local verdes, incluindo o portão 12 em árvore limpa e o autoteste novo. Os portões `.js` ficam com o CI.


## §174 · "Tentativa falhou" contava como prova preservada — e cinco registros pontuáveis viviam só disso · 23/09/2026

Classe **correção de segurança do dado**. Nenhum número do índice muda; muda o que o portão aceita como prova, e quatro registros passam a aparecer como lacuna declarada.

**O achado.** Ao pendurar a leitura de PDFs (§10.1) na cadência — a pendência que o §164 deixou declarada —, a conferência do resultado descobriu o buraco. A condição do portão era `item["arquivo"] or item["wayback"]`. E `preservar_evidencia()` grava em `wayback` a **string** `"tentativa falhou (HTTPError)"` quando o pedido de snapshot não vai. String não vazia é verdadeira em Python: a anotação de que a preservação falhou passou a valer como preservação.

**O tamanho real da exposição, medido e não estimado.** 40 itens do índice têm a anotação de falha no lugar do snapshot, e 34 registros pontuáveis dependem de um deles — são os documentos acima do teto de cópia de 5 MB (mediana de 13 MB, um de 70 MB), em que a cópia binária é pulada por desenho. Mas **29 desses 34 têm o texto extraído do PDF**, que é cópia preservada de verdade: o portão só não olhava para ele. Os que viviam **exclusivamente** da string de falha, sem nenhuma prova de espécie alguma, eram **5**.

**O conserto.** `prova_preservada()` só aceita prova de verdade: a cópia binária, o **texto extraído** com conteúdo (`texto_arquivo` com pelo menos 200 caracteres — o mesmo piso que `ler_pdfs()` já usa para decidir se a extração serviu), ou um endereço de snapshot que comece com `http`. Teste negativo permanente junto, rodado a cada execução: as três formas de `"tentativa falhou (...)"`, o `.txt` vazio e o `.txt` de 199 caracteres reprovam; cópia, texto com conteúdo e URL de snapshot passam.

**A leitura entra na cadência.** `preservar_evidencias.py --ler` também não estava em workflow nenhum — e continua fora dele na `main`: o passo de autocura de textos integrais (10/09) só completa pista do Querido Diário, não extrai texto de PDF preservado. Agora roda logo depois da preservação, com teto de 25 min, e o portão exige a presença das **duas** chamadas. Rodada aqui, extraiu os dois textos que o §164 deixou pendentes: Feira de Santana/BA (57 páginas) e Lagarto/SE (28) — e foi o de Lagarto que tirou o quinto registro da lista dos sem prova. O de Feira de Santana chegou à `main` em 23/09 por execução à mão, com o mesmo `texto_hash` (`96e46439…`) que a leitura daqui produziu; então deste lote entra só o de Lagarto.

**Quatro sem prova nenhuma — lacuna declarada e datada.** Anchieta, Itaguaçu, São José do Calçado e Venda Nova do Imigrante, todos do ES: PLANCON de 10 a 19 MB, **escaneado**, sem camada de texto (cada página é uma imagem de 2409×3406 px), leitura devolve zero caractere, e o Wayback **não tem snapshot** — consultado pela API de disponibilidade, não só tentado. Não têm cópia binária, nem texto, nem snapshot. Em vez de escondê-los atrás de um arquivo vazio, entram em `LACUNA_DECLARADA` no próprio portão: aparecem como aviso nomeado em toda execução e **bloqueiam a partir de 31/10/2026**. A chave é o hash do documento — represervado, o hash muda e a exceção cai sozinha. O portão também avisa quando uma lacuna declarada já foi resolvida, para a lista não apodrecer.

*As quatro lacunas declaradas aqui foram fechadas no §177, do mesmo lote — a contagem citada abaixo e no teste é a do momento desta entrada.*

**Caminho para fechar a lacuna: OCR, testado antes de prometido.** Os quatro são escaneados a ~300 DPI, que é o caso fácil. Teste real com o PLANCON de São José do Calçado: renderizando a 200 DPI com `pypdfium2` (já é dependência, via pdfplumber) e passando por Tesseract, a página 1 devolve "PREFEITURA MUNICIPAL DE SÃO JOSÉ DO CALÇADO — DEFESA CIVIL — PLANO DE CONTINGÊNCIA" e a página 2 traz o ato instituidor, "DECRETO n° 7.717/2024" — e isso **com o modelo em inglês**, usado só para provar legibilidade. 2,0 s por página; as 230 páginas dos quatro sairiam em cerca de 8 minutos. Nenhuma dependência Python nova; no runner, uma linha de `apt-get` para `tesseract-ocr` e `tesseract-ocr-por`. Fica para correção própria, com a regra que ela vai exigir: **texto de OCR é cópia preservada e legível, marcada como tal — nunca insumo do classificador nem do juiz**, que exigem o ato lido no documento (§156).

**Mais um defeito de escrita da série do §163.** `gravar_texto()` gravava o `.txt` sem `newline="\n"`: no Windows o arquivo saía em CRLF enquanto o `texto_hash` registrado era calculado sobre a string com `\n` — o hash não batia com o arquivo em disco. Corrigido; conferido que agora `sha256(arquivo) == texto_hash` nos dois textos novos.

**Registrado, sem mexer.** Maricá/RJ tem `texto_hash` desatualizado desde a redação de CPF de 12/09/2026 (`scripts/remediar_cpf_evidencias.py` regravou o texto sem recalcular o hash). É o único item do índice nessa condição. O conserto pertence à rotina de redação, não a este portão.

**Teste.** Portão de evidências verde, com as pré-condições novas e os autotestes da regra de prova: 89 de 93 registros pontuáveis com prova preservada, 4 em lacuna declarada, 2.059 itens íntegros. Portão 12 verde (cadeia canônica idempotente) e manifesto reselado; workflows válidos, com teto de tempo em todo job (§172); consistência, `recalcular_mare --check` (46,2 — a média nacional subiu de 45,2 para 46,2 na `main` entre 22 e 23/09, por dado novo, não por este lote), sinais, saúde, financiamento, painel, resposta, os cinco testes de regressão e os treze autotestes de coletor e do juiz verdes. Os portões `.js` ficam com o CI — não há Node nesta máquina.

**Sobre a numeração.** O achado e o conserto são de 22/09/2026 e foram escritos como §165; entre uma sessão e outra a `main` avançou até o §173 e o número foi ocupado por outro trabalho. A entrada foi renumerada para §174 e o conserto reaplicado sobre a `main` de 23/09, com os portões rodados de novo por inteiro nesta base.

## §173 · A página de Saúde servia número velho a quem não roda JavaScript · 23/09/2026

**Como apareceu.** A rodada completa de 23/09 terminou verde nos 35 passos, e o portão 12 fechou **vermelho** na `main` logo depois: o manifesto trazia, para `saude.html`, o hash de um arquivo **que não existe no repositório**.

**A causa.** O passo de commit da rodada tinha uma lista fechada de caminhos, e ela nomeava só `index.html` e `defesa-civil.html`. Mas `preencher_fallback_estatico.py` — obrigatório no pipeline — reescreve também `saude.html` e `financiamento.html`, e `carimbar_assets.py` reescreve as 12 páginas. Tudo isso era **descartado no `git add`**, enquanto o manifesto, esse sim commitado, guardava o hash da versão nova.

**O dano real não era o portão.** O conteúdo estático é o que o leitor **sem JavaScript** vê, e o que o `aria-label` da barra de progresso anuncia ao leitor de tela. Medido na `main` de hoje:

| campo em `saude.html` | no ar | valor real |
|---|---|---|
| MARÉ Saúde | 31,8 | **32,5** |
| estados verificados | 17 | **20** |
| estados não verificados | 10 | **7** |
| secretarias com plano do ciclo | 2 | **4** |

Duas rodadas automáticas descartaram a correção dessa página. O mecanismo, porém, não era de duas rodadas: repetiria em todas.

**Silencioso por construção.** Descartar uma mudança no `git add` não produz erro nenhum — a rodada fica verde, o site fica errado.

**A correção.** `*.html` no lugar da lista nomeada, nos **três** workflows que regeneram o manifesto (a rodada de atualização, a busca web de cadência e o painel do AM) — as duas últimas tinham exatamente a mesma falta. O glob cobre as páginas de hoje e as de amanhã.

**O portão.** `validar_workflows.py` passa a cobrar que todo workflow que reescreve página commite as páginas. A cobrança vale **só** para quem roda `carimbar_assets`, `preencher_fallback_estatico` ou `gerar_manifesto`: `preservar_evidencias.yml` caiu como falso positivo na primeira versão da regra, e portão que cobra o que não se aplica acaba desligado.

---

## §172 · Teto de tempo por etapa e por job: a fonte pendurada deixa de segurar a fila · 23/09/2026

**Achado real.** A rodada diária de 23/09 ficou **45+ minutos** no passo do pipeline. Fora do dia de publicação esse passo executa só dois scripts antes de encerrar na trava de cadência, e um deles não toca a rede — logo o tempo estava num único coletor que não respondia. *Registro honesto:* não consegui ler os logs (a API devolveu 404 durante a execução e depois do cancelamento), então a atribuição ao coletor é **inferência pelo caminho do código**, não leitura do log.

**Três camadas faltavam ao mesmo tempo:** `subprocess.run` sem `timeout`; o passo do workflow sem `timeout-minutes`; e o **job** sem `timeout-minutes`, herdando as **seis horas** de padrão do GitHub. Com a trava de concorrência do workflow de atualização (`cancel-in-progress: false`), isso vira a fila parada o dia inteiro — e nada reprova, porque **um job pendurado não é um job vermelho**. Só foi notado porque alguém foi olhar.

**Teto por etapa é a correção principal**, não o teto do job: a fonte lenta mata a etapa dela e a rodada segue, que é a disciplina que o pipeline já declara — nenhum coletor é bloqueante, fonte fora do ar é lacuna declarada. Sem isso a única saída era matar a rodada inteira e perder junto tudo o que ela já havia coletado. 45 min nas etapas pesadas do dia de publicação, 15 min nos coletores diários que nunca pontuam.

**Teto por job é rede de segurança** para o que o teto por etapa não alcança: neto que sobrevive ao filho morto, travamento fora de um subprocesso. 180 min na rodada completa, que leva 75–105.

**O portão passa a exigir teto em todo job de todo workflow** — eram **cinco** sem teto no repositório, não um. Recusa também `timeout-minutes >= 360`, que é declarar o padrão e chamá-lo de teto.

---

## §171 · Rodada completa sob demanda: destrava declarada, só pelo botão, sem virar atalho · 23/09/2026

Classe **encanamento operacional**; nenhum dado, número ou página muda. *Entrada escrita a posteriori em 23/09/2026: a mudança foi mesclada (PR #358) sem registro no `CHANGELOG.md` — ver §179.*

**O pedido.** A editoria quis antecipar uma rodada de atualização **completa** fora do domingo, para ver o pipeline inteiro rodar antes da cadência.

**Por que o que existia não servia.** O *ensaio* roda tudo e **não comita** — serve para olhar o pipeline, não para publicar uma edição. E publicar fora do dia exigiria mexer em `INTENSIVO_DE`/`INTENSIVO_ATE`, que são variáveis do repositório e valem **também para os crons**: uma edição fora de hora viraria uma semana inteira de rodadas completas, e ninguém lembraria de desfazer.

**A destrava, declarada e efêmera.** `FORCAR_RODADA_COMPLETA` só é acionada pelo botão manual — vem de `github.event.inputs.rodada_completa_agora`, e um cron não tem `event.inputs`, então nenhuma rodada agendada a alcança. Sai no log da rodada, dizendo que hoje não é o dia de publicação e que a edição levará a data de hoje. Não toca `INTENSIVO_DE`/`ATE` nem `data/publicacao.json` — o regime do domínio não muda. E não suprime o commit, ao contrário do ensaio.

**Por que a forma importa.** A cadência semanal é compromisso público: `obrigado.html` e `pesquisadores.html` dizem ao leitor quando o banco muda. Por isso a destrava é decisão tomada **a cada disparo**, nunca herdada de uma configuração esquecida.

**Trava.** O portão de cadência (`scripts/testar_cadencia_publicacao.py`) fixa as quatro propriedades e reprova se qualquer uma cair: destrava ausente do código, entrada ausente do workflow, destrava solta de cron, ou destrava acrescentada à condição do commit — que a transformaria em ensaio disfarçado. Testado nos dois sentidos.


## §170 · Os planos do AM pela reserva de arquivo, com procedência declarada — e a recusa que não se contorna · 23/09/2026

**O problema.** A rodada de 23/09 leu os 62 municípios do painel, e **nenhum** documento abriu: `Connection reset by peer` nas 62 tentativas. O painel Power BI respondia normalmente no mesmo runner, o que localiza o problema — quem recusa não é a Microsoft, é o hospedeiro dos planos.

**A solução já existia no projeto.** `buscar_com_reserva_wayback` foi criada em 12/09 para exatamente este sintoma: portais estaduais que não completam conexão com o runner do Actions, enquanto o arquivo público responde. Três coletores já a usam (DF, PE, listagem do DF). O coletor do AM ficou de fora.

**Mas a reserva, como estava, não distinguia duas coisas muito diferentes.**

*Primeira:* um plano lido na fonte e um plano lido numa captura de arquivo **provam coisas diferentes** — o primeiro é o documento como está hoje, o segundo como estava quando alguém o arquivou. `buscar_com_procedencia` passa a devolver `(bytes, procedencia)`, e o item guarda qual dos dois foi. Ato legível numa captura ainda vira `documentado`, mas com a observação em letra de forma: *o documento é o arquivado, não necessariamente o vigente*. Sem esse campo, as duas leituras viravam a mesma coisa no banco. `buscar_com_reserva_wayback` continua existindo, agora como fachada — nenhum dos três coletores muda de comportamento.

*Segunda, e mais séria:* o `CLAUDE.md` proíbe contornar bloqueio de acesso de fonte, e a reserva antiga **caía no arquivo para qualquer erro**, inclusive `403`. Um 403 não é falha: é o servidor respondendo **não**. Ir buscar a mesma página numa captura seria dar a volta por fora.

Agora `401`, `402`, `403`, `429` e `451` propagam sem reserva. A reserva vale para o caso oposto — reset de conexão, handshake TLS incompleto, DNS mudo —, em que **não houve resposta e portanto não há recusa a respeitar**. `404` e `5xx` seguem usando a reserva: página que sumiu ou servidor com defeito é exatamente o que um arquivo serve para resolver. Isto corrige, de tabela, a mesma falta nos três coletores que já usavam a reserva.

**O resumo passa a contar procedência.** Um lote em que tudo veio de arquivo diz algo sobre a fonte, não sobre os municípios — e espalhado item a item, esse fato ficava invisível.

**O que continua valendo.** Nada entra no banco sem promoção humana (R7). Ano no painel não prova antecipação. Camada `documentado` segue exigindo ato com número e data lidos do próprio documento.

---

## §169 · Procedência do painel do AM sem registro de LAI no repositório público · 23/09/2026

**Regra que estava sendo violada.** `data/pistas_paineis.json` gravava, no repositório **público**, o registro de uma resposta a pedido de acesso à informação, com o endereço da ouvidoria do órgão junto. O `CLAUDE.md` é explícito: pedidos e respostas de LAI vivem no repositório privado da editoria, nunca aqui.

**O que muda.** O campo continua existindo e continua dizendo quem indicou e quando — a procedência não se perde. Sai o que a regra protege: o registro de que houve LAI e o endereço da ouvidoria. O texto passa a apontar para onde o detalhe vive.

**Por que não apagar o campo.** Procedência é o que separa uma URL achada por varredura de uma URL indicada pelo órgão, e essa diferença importa para quem audita o dado. Apagar resolveria a regra criando um buraco.

**Limite desta correção, declarado.** Isto corrige a `main`; **não** apaga a string do histórico do git, que é público e onde ela permanece nos commits anteriores. Reescrever histórico de ramo público é ação destrutiva e não se faz sem decisão da editoria.

---


## §168 · A rodada real do painel do AM: 62 de 62 municípios lidos, e a eliminação que faltava no caminho principal · 23/09/2026

**A verificação que faltava.** As correções do §165 (etiqueta de interface do Power BI colada ao nome; rolagem que nunca acontecia) passavam no autoteste offline, mas não tinham sido postas contra o painel real. Rodada manual com `commitar: false`, que não escreve nada no repositório:

| | antes | depois |
|---|---|---|
| linhas lidas | 20 de 62 | **62 de 62** |
| declarado | 19 | **51** |
| sem plano declarado | 1 | **11** |
| sem código IBGE | **20** | **1** |
| itens na fila | 82 | 63 |

Os 51/11 reproduzem exatamente a divisão da leitura humana de 22/09 — duas leituras independentes, mesmo resultado. Isso é corroboração, não coincidência.

**O que a rodada real ainda revelou: a eliminação não valia no caminho principal.** Mesmo com os 62 lidos, sobrou **um** município sem código IBGE — "Careiro Castanho" no painel contra "Careiro" no IBGE. A regra de casamento por eliminação existia desde o §165, tinha dois casos de teste, e **só era chamada no caminho da semeadura**. Quando a rodada renderizada virou o caminho principal, a regra ficou para trás sem que nada acusasse: dois caminhos de código, um deles com a correção.

Ligada agora nas duas origens, com a mesma trava: só dispara quando sobra **um** nome sem par de cada lado. Dois casos novos fixam os dois lados da regra — a dedução acontece na grade completa, e **não** acontece em leitura parcial, onde 61 códigos sem par tornariam qualquer dedução um chute.

**Em aberto, declarado e sem eufemismo.** Os 62 documentos responderam `Connection reset by peer` ao runner do GitHub, um a um. **Nenhum ato foi lido; a rodada não produziu um único `documentado`.** Isso é lacuna declarada: não sabemos se o portal recusa o runner, se recusa endereços fora do Brasil, ou se estava fora do ar. O que o painel prova continua sendo o que ele sempre provou — que o estado **declara** o plano —, e ano no painel não prova antecipação. A camada `documentado` do AM segue vazia, e é assim que deve aparecer enquanto for verdade.

---

## §167 · Automações do projeto: os portões passam a ter fonte única, e as regras viram portas · 23/09/2026

Classe **encanamento**; nenhum dado, número ou página muda. Lote saído de falhas desta mesma sessão, não de catálogo.

**O achado que motiva tudo: havia três listas de portões, e nenhuma estava certa.** O `CLAUDE.md` listava 19 comandos, o `PROTOCOLO §3.3` numerava 19 **outros**, e o `portoes.yml` — o único que reprova de verdade — roda **47**. A divergência era maior do que qualquer um dos documentos sugeria. Rodar um subconjunto coerente com uma das listas custou um ciclo de CI hoje: `verificar_seguranca.js` ficou de fora e reprovou lá por uma Action sem SHA fixado.

**A correção não é escrever a lista uma quarta vez — é parar de escrevê-la.** `scripts/portoes_locais.py` deriva do workflow e roda o que ele roda, na ordem dele; portão novo no CI passa a valer localmente sem ninguém copiar. Saída de uma linha por portão, com o vermelho mostrando tudo e parando ali: a suíte em modo verboso são centenas de linhas de `✓` que não informam nada e custam contexto caro.

**Quatro hooks, cada um nascido de um erro real.** `bloquear_segredos` (chaves e credenciais, por `Read` **e** por `Bash`, porque ler por shell contornaria o bloqueio de `Read`); `bloquear_leitura_pesada` (`Read` acima de 1 MB em `data/`, `dados-abertos/` e `evidencias/` — os dois maiores somam 26 MB e um `Read` estoura a sessão sozinho); `bloquear_derivados` (a regra do CLAUDE.md vira porta); `autoteste_do_coletor` (roda o autoteste do script recém-editado — nasce do achado do §165, em que um autoteste sujava `data/` a cada execução do portão).

**Correção de premissa sobre o token.** Este repositório **não tem arquivo de token**: os segredos da operação são GitHub Actions secrets, fora da árvore. Proteger um arquivo inexistente daria falsa segurança, então o hook mira o que existe.

**O hook mordeu quem o escreveu.** Ao comitar este lote, `bloquear_segredos` recusou o próprio commit que o introduzia — a mensagem citava um caminho protegido ao explicar a regra, e ele leu isso como operando. Falso positivo real; corrigido para que corpos de heredoc e valores de `-m` sejam tratados como texto, não operando. Nove casos de teste nas duas direções. Um controle que atrapalha sem proteger acaba desligado, que é o pior desfecho possível.

**Também entram** cinco skills (`/portoes`, `/p12`, `/merge-main`, `/e-da-main`, `/lote`) e quatro subagentes (`portoes-runner`, que mantém a saída verde fora do contexto principal; `diagnosticador-de-ci`; `revisor-de-trava`; `auditor-de-lacuna`). O `CLAUDE.md` deixa de listar portões e ganha a tabela dos arquivos que nunca entram em contexto e a regra do merge de log append-only.

**Teste.** Os 47 portões verdes, rodados pelo próprio executor novo, com árvore limpa. Nenhum MCP novo, nada pago, nenhum segredo tocado.

## §166 · Cobertura declarada por UF e por canal: estrutura pronta, texto público com a editoria · 23/09/2026

Classe **encanamento**; nenhuma página lê o arquivo ainda.

**O problema.** O site afirma "não localizamos até o corte" sem dizer **onde** se procurou. O caso do painel do AM (§165) mostrou que a frase valia menos do que parecia. Afirmação de ausência sem escopo declarado é afirmação que o leitor não pode auditar.

**Feito.** `gerar_cobertura_declarada.py` **deriva** de `data/log_buscas.json` quais canais foram verificados em cada UF e quando — sem criar um segundo lugar onde a verdade mora. Regra central, travada em teste: **erro de acesso é tentativa, nunca verificação**; senão a nota de rodapé repetiria, com mais detalhe, o erro que ela corrige. Canal nunca visto aparece como não verificado em vez de sumir do relatório.

**O ponto cego, quantificado.** Sobre 24.610 execuções reais: **nenhuma UF passa de 3 dos 7 canais**, e `painel`, `portal_transparencia` e `lai` estão verificados em **zero** UFs.

**Parado antes de publicar, como pede a transferência.** `nota_publica` nasce `null` de propósito: a redação da nota na ficha de cada estado é decisão da editoria. O canal `lai` existe no esquema mas guarda só data e status — jamais texto ou registro de pedido.

## §165 · Painel do AM: o coletor, os 62 municípios e a distinção entre declarado e documentado · 23/09/2026

Classe **código + dado de fila**; **nenhuma nota do MARÉ muda** — conferido antes e depois, 0 UFs com diferença em `indice.json`.

**O caso.** Em 22/09 a Ouvidoria da Defesa Civil do AM respondeu a um pedido de LAI sem enviar a lista: indicou um painel Power BI, com os 62 municípios, ano do plano e link do documento. Público, provavelmente antigo, nunca alcançado por nenhuma rodada — a tabela é montada em JavaScript depois do carregamento.

**Feito.** `scripts/renderizar_painel_am.js` renderiza e extrai a grade em bruto; `coletar_painel_am.py` casa nome com código IBGE, baixa o documento de cada link, preserva a evidência e lê **do próprio documento** o número e a data do ato. A rodada renderizada mora em workflow manual, porque exige navegador e saída de rede que a sessão de desenvolvimento pode não ter.

**A regra que dá sentido ao coletor.** A tabela do painel é **declaração do estado**: traz o ano, não o ato. Camada `declarado`. Só vira `documentado` o município cujo link abriu e cujo ato teve número e data lidos do documento. **Ano 2026 não prova antecipação** — a régua separa antes e depois de 29/06/2026 pela data do **ato**, e há teste que fixa isso.

**Incorporação.** 62 municípios do AM na fila a partir da leitura humana de 22/09: 51 declarados, 11 sem plano, **0 documentados** — zero é o ponto, não falha, porque a leitura humana não capturou os links. Os 62 sobem de nível de verificação `nacional` para `estadual` sem mover nota nenhuma.

**Casamento por eliminação.** O painel escreve "Careiro Castanho", nome popular; o IBGE registra "Careiro". Existe também "Careiro da Várzea", município distinto — por isso um apelido não podia virar alias solto: errar aqui move a nota de um terceiro. A regra só dispara quando sobra **um** nome sem par de cada lado; com dois ou mais, todos seguem lacuna declarada.

**Achado da primeira rodada real, e a correção do diagnóstico.** O render leu 20 linhas de 62 e **nenhuma** casou com o IBGE. A primeira leitura disso foi que o extrator pegava a grade errada — o Power BI desenha vários visuais, e o código fazia `querySelector`. O log da rodada desmente: a grade escolhida era a certa (`Seleção de Linha · Índice · Calha · Município · Plano · Ano do Plano`, `aria-rowcount=63`). Eram **dois defeitos independentes**, e nenhum deles era esse.

1. **Etiqueta de interface colada ao nome.** O painel devolveu `Atalaia do Norte Formatação Condicional Adicional` — o Power BI cola o rótulo do recurso de formatação no texto acessível da célula. As 20 linhas falharam o casamento por isso: o dado estava lá, quem não leu foi o coletor. `limpar_rotulo_powerbi` recorta a etiqueta **só do fim** e **só da lista declarada**: um corte por heurística mutilaria São Paulo de Olivença e Santo Antônio do Içá, que têm quatro palavras. Rótulo novo que aparecer vira lacuna declarada, não nome recortado errado. As 20 linhas reais viraram caso de regressão.
2. **A rolagem nunca aconteceu.** `page.mouse.wheel` era chamado sem mover o cursor, isto é, em (0,0) — fora da grade. O Power BI só rola o visual sob o ponteiro, então a roda caía no vazio e a leitura parava nas 20 primeiras linhas. O aviso de "leitura parcial" saiu certo e a causa era outra. Agora são três estratégias (`scrollTop` no contêiner que de fato rola, roda **com o ponteiro sobre a grade**, evento sintético), e a que funcionou fica no diagnóstico — rolagem que parar de funcionar precisa ser visível. De quebra, `aria-rowcount` conta o cabeçalho (63 para 62 municípios), e a parada por contagem só dispara descontando-o.

**O que resistiu ao diagnóstico errado.** A porta de qualidade do coletor: leitura em que quase nada casa com o IBGE, ou parcial demais, vira lacuna declarada e nunca item de fila. Sem ela, as 20 linhas tinham ido para a triagem humana parecendo dado — foi exatamente o que a rodada de 23/09 produziu (fila de 82 itens, 20 sem código IBGE) antes da porta existir. A escolha de grade por pontuação fica como endurecimento: não era a causa, mas o `querySelector` era frágil de verdade.

**Ainda em aberto.** Os documentos do painel responderam `Connection reset by peer` ao runner do GitHub em todas as tentativas — nenhum ato foi lido, e por isso a rodada não produziu um único `documentado`. Isso é lacuna declarada, não ausência de plano: não sabemos se o portal bloqueia o runner ou se estava fora do ar.

## §164 · A cadência passa a preservar a evidência sozinha — e o portão confere que ela continua fazendo isso · 22/09/2026

Classe **encanamento**; nenhum dado, número ou página muda. Fecha a pendência declarada no §162.

**A lacuna.** `preservar_evidencias.py` existe desde a v2.2.4 (§3.8) e **não era chamado por nenhum workflow** — nem a cadência, nem os portões. Enquanto o registro pontuável nascia de sessão humana, isso passava: quem aplicava rodava o script. Desde o §158, o juiz aplica município sozinho, e o §162 foi a consequência: Feira de Santana/BA entrou no banco como `plano` sem `hash_evidencia`, e `verificar_evidencias.py` — bloqueante desde 15/09 — deixou a `main` vermelha até alguém notar. O portão estava certo; faltava o passo que o mantém verde.

**Feito.** Passo novo em `atualizar.yml`, **depois do juiz e depois de todo passo que pode criar registro pontuável** (coletores, `aplicar_revisao`), e antes da sincronização de derivados e do commit — ao lado da autocura de textos integrais de 10/09. Roda `preservar_evidencias.py --limite 20`, com `timeout-minutes: 20` e `continue-on-error`, porque o script já trata falha de rede como lacuna declarada e a rodada seguinte tenta de novo. É idempotente por construção: registro que já tem hash e cópia é pulado. O commit da rodada já inclui `evidencias/` e `data/`.

**Trava, para não voltar a depender de atenção humana.** `verificar_evidencias.py` ganha teste negativo permanente: o próprio portão confere que a cadência chama o script, e reprova com o motivo escrito se a chamada sumir. Testado nos quatro casos — passo presente (passa), passo trocado por outro, chamada comentada em `run: #` e chamada comentada dentro de bloco `run: |` (os três acusam). Sem isso, tirar o passo seria silencioso: o portão só acusaria na próxima aplicação automática, que é exatamente o atraso que se quer eliminar.

**Lacuna que continua declarada.** A extração de texto dos PDFs (§10.1, `preservar_evidencias.py --ler`) também não está em workflow nenhum, e dois itens seguem sem texto extraído: o decreto de Feira de Santana e o Plancon de SE preservado em 03/09. Não entra aqui porque é outra rotina, com outro custo de rede — fica nomeada para a decisão da editoria.

**Teste.** Portão de evidências verde, com a pré-condição nova. Portão 12 verde em árvore limpa, workflows válidos, consistência, `recalcular_mare --check` (45,2) e o restante do bloco de dado e coleta verdes. Os portões `.js` ficam com o CI — não há Node nesta máquina.

## §163 · O portão 12 estava vermelho na `main`: a cadeia de derivados do juiz era curta demais, e agora é a mesma do portão — travada em teste · 22/09/2026

Classe **correção de encanamento com efeito no registro público**. Nenhum número do índice muda: a média nacional segue 45,2 e a Bahia já estava em 20,0 em `data/estados.json`. O que estava errado era o **histórico**, que não registrava a mudança já publicada.

**O achado.** Ao rodar a suíte completa para o §162, `scripts/verificar_derivados.sh` (portão 12) fechou vermelho. Teste controlado antes de acusar a própria mudança: árvore separada em `origin/main` puro (`39b0047`), cadeia regenerada, **mesmos 9 arquivos, mesmos números** — o vermelho é anterior ao §162 e não vem dele.

**Causa raiz: a mesma lista curta, escrita duas vezes.** `sincronizar_derivados()` do juiz (§158) regenerava `recalcular_mare --write`, `gerar_dados_abertos` e `gerar_card_municipios`. O passo "Sincronizar índice antes do commit" de `atualizar.yml` regenerava exatamente esses três. Mas `gerar_prioritarios`, `gerar_feeds`, `gerar_monitor_saude`, `gerar_resposta`, `gerar_contadores_financiamento`, `carimbar_assets` e `gerar_blog` rodam **antes** do juiz, dentro de `atualizar.py`, e nunca mais depois. Quando o juiz aplicava um município — Feira de Santana/BA, na rodada de 22/09 —, esses derivados ficavam parados: `data/historico_mudancas.json` sem os eventos "plano preventivo localizado" e "Bahia: MARÉ 18,6 → 20,0", `data/municipios_prioritarios.json` com `publicados: 170` e o município como `publicado: false`, `feeds/BA.xml` e `feeds/brasil.xml` sem as entradas, mais `dados-abertos/`, os dois PDFs e o manifesto. Um leitor via a nota nova no site e um histórico que não a explicava.

**Conserto, com a lista num lugar só.** A cadeia do juiz passa a ser a **cadeia canônica inteira** (`CADEIA_DERIVADOS`, 13 passos), e o mesmo vale para o passo de sincronização da cadência. A fonte de verdade continua sendo `scripts/verificar_derivados.sh` — o que o portão 12 cobra. Para a lista não divergir de novo em silêncio, o `--self-test` do juiz ganha o **cenário 6**: lê a sequência do próprio `.sh` e exige igualdade; a lista antiga, de três passos, reprova. O self-test do juiz entra em `portoes.yml` como portão bloqueante (não estava).

**Portabilidade, sem a qual nada disto podia ser feito fora do runner.** Regenerar a cadeia numa máquina Windows produzia lixo, por dois defeitos invisíveis no Linux: escrita em modo texto sem `newline="\n"` (o Python traduz `\n` para `\r\n` e o derivado sai em CRLF, com hash diferente do selado) e `str(Path.relative_to(...))`, que grava `evidencias\<hash>.pdf` — no Linux, nome de arquivo inexistente, e o portão de evidências vermelho. Corrigidas **30 chamadas** em oito arquivos (`coletores_base.py`, `recalcular_mare.py`, `gerar_feeds.py`, `gerar_dados_abertos.py`, `gerar_blog.py`, `gerar_selos.py`, `scripts/carimbar_assets.py`, `scripts/gerar_manifesto.py`). **Prova:** com só essas correções aplicadas sobre `origin/main`, a cadeia regenerada no Windows difere, **byte a byte**, apenas nos 9 arquivos genuinamente atrasados — todo o resto do repositório sai idêntico ao que o runner produz.

**Terceiro defeito, achado pelo próprio portão 12 no CI — e o mais sério dos três.** A primeira tentativa deste PR fechou vermelho em exatamente três arquivos: os dois PDFs e o manifesto. Comparados byte a byte, **64 bytes** de 515.385 diferiam, e o primeiro dizia tudo: `/CreationDate (D:20260910000000+00'00')` contra `D:20260910030000`. Três horas — o fuso de Brasília. `gerar_pdf_indice.py` e `gerar_pdf_metodologia.py` sempre calcularam o `SOURCE_DATE_EPOCH` certo, com `tzinfo=timezone.utc`, mas usam `os.environ.setdefault`: quem chama manda. E **todos os seis chamadores** — `scripts/verificar_derivados.sh`, `sincronizar_derivados()` do juiz, `atualizar.py`, os dois passos de `atualizar.yml` e `busca_web_cadencia.yml` — calculavam `datetime(aa, mm, dd).timestamp()`, hora **local**. No runner, que é UTC, local e UTC coincidem e o defeito nunca apareceu; fora dele, o "PDF bit-determinístico" da v2.2.3 (R1 da 2ª auditoria) valia só dentro do mesmo fuso. Os seis passam a fixar `tzinfo=timezone.utc`, como os geradores. **Prova:** regenerados aqui, em UTC−3, os dois PDFs saem **idênticos byte a byte** aos de `origin/main`, que vieram do runner. Nenhum valor muda no CI — em UTC, o cálculo antigo e o novo dão o mesmo número; a correção é compatível para trás por construção. (Fica registrado, sem mexer: o `SOURCE_DATE_EPOCH` fixo de `scripts/verificar_robustez_atualizacao.py`, `1787886000`, é meia-noite de Brasília, não de UTC — é constante de teste, não entra em derivado publicado.)

**Teste.** Portão 12 verde em árvore limpa, e os dois PDFs regenerados aqui idênticos byte a byte aos do runner. Self-test do juiz 6/6, com o teste negativo do próprio cenário 6. Consistência, `recalcular_mare --check` (45,2), sinais, saúde, evidências, financiamento, painel, resposta, detector de defeso, workflows e manifesto (`--check`, PDFs bit-determinísticos inclusive) verdes. Os portões `.js` não rodaram nesta máquina — não há Node instalado; ficam com o CI.

## §162 · A prova de Feira de Santana/BA, que o juiz aplicou sem preservar: portão de evidências volta ao verde · 22/09/2026

Classe **correção de integridade da prova**. Nenhum campo de julgamento tocado; média nacional inalterada: 45,2.

**O portão estava vermelho na `main`.** `verificar_evidencias.py`, bloqueante desde 15/09/2026, acusava `1 de 92 registro(s) pontuável(is) com URL sem evidência preservada — Feira de Santana/BA`. O registro entrou em `data/municipios.json` na rodada automática de 22/09 às 20:20 UTC (`e19fcdd`) como `plano`, canal `DOM`, com a URL do diário no Querido Diário — e **sem `hash_evidencia`**. É o outro lado do §158: o juiz passou a aplicar o município sozinho, mas a preservação da prova ficou de fora do caminho.

**Por que não se resolvia sozinho.** `preservar_evidencias.py` existe desde a v2.2.4 (§3.8) e não é chamado por **nenhum** dos workflows — nem a cadência, nem os portões. Enquanto ninguém o rodasse à mão, o vermelho ficava; e como o portão só roda quando o PR mexe em dado, o próximo PR de dado é que iria descobrir.

**Feito.** `preservar_evidencias.py` baixou o documento (3,0 MB), guardou a cópia em `evidencias/b4c95d43…pdf`, indexou em `data/evidencias.json` (url, origem, data de preservação, tamanho) e gravou o `hash_evidencia` no registro. É a única edição programática permitida em `municipios.json` fora de `aplicar_revisao.py`, justamente porque não altera julgamento: categoria, documento, data, fonte e canal seguem como o juiz os deixou. O portão fecha em `✓ EVIDÊNCIAS OK — 92 registro(s) pontuável(is) com URL, todos com evidência preservada; 1960 item(ns) íntegro(s)`.

**Lacuna declarada.** A extração de texto do PDF (§10.1, `preservar_evidencias.py --ler`) **não** foi feita: 93 dos 95 itens com URL de PDF têm o texto extraído, e os dois que faltam são este e o Plancon de SE preservado em 03/09. Rodar `--ler` aqui arrastaria o item de SE junto, que é outro assunto. `--ler` também não está em workflow nenhum.

**Nota de procedência.** Gerado numa máquina Windows, com dois artefatos corrigidos à mão porque os utilitários de escrita não são portáveis: `coletores_base.gravar()` abre o arquivo em modo texto e escreveu `data/*.json` inteiros em CRLF, e `preservar_evidencia()` gravou `"arquivo"` com barra invertida (`evidencias\…`), que no runner Linux viraria "arquivo ausente" e deixaria o portão vermelho de novo. Os dois consertos de verdade — `newline="\n"` na escrita e `as_posix()` no caminho, mais os cerca de 25 scripts que escrevem JSON sem passar por `gravar()` — ficam para correção própria.

## §161 · Três marcadores de conflito de merge saem do `CHANGELOG.md`: o que cada um escondia, conferido commit a commit · 22/09/2026

Classe **correção de higiene do repositório**; nenhum dado, página, método ou número do índice muda. Média nacional inalterada: 45,1.

**O que estava lá.** O `CHANGELOG.md` da `main` trazia, commitadas, três linhas de marcador de conflito no estilo diff3 — `||||||| parent of 842060a…`, `…95a5754…` e `…8fcd4fd…`, imediatamente antes dos títulos de §156, §153 e §150. Sem `<<<<<<<`, sem `=======` e sem `>>>>>>>`: resolução parcial de conflito de *cherry-pick* (o rótulo "parent of" é o que o git escreve na base com `merge.conflictStyle=diff3`), em que as três outras linhas foram apagadas à mão e a da base escapou. Documento de auditoria pública — o `README` aponta para ele como histórico de versões —, então o conteúdo ao redor foi conferido antes de apagar qualquer linha.

**De onde veio cada marcador, e por que nada se perdeu.** `git log -S` localiza o commit que introduziu cada linha: **a183c28** (§152, decisão 3 do teste do objeto), **326bf8a** (§155, card do município) e **101fd65** (§158, o juiz sincroniza os derivados). Os três commits são **adição pura** ao `CHANGELOG.md` — 17, 11 e 11 linhas inseridas, **zero removidas** —, cada um com a seção nova mais o marcador solto. Nenhum texto foi perdido e nenhum foi duplicado: a numeração corre contínua de §159 a §140, sem lacuna nem seção repetida, e o texto de cada seção bate com o do commit que a introduziu. A resposta à pergunta "que texto deveria estar ali?" é, nos três casos, **nenhum**: a linha nunca cobriu conteúdo.

**O que foi feito.** As três linhas removidas, e só elas — o diff é de 3 remoções. Entre §151 e §150 não se acrescentou a linha em branco que falta: ela já faltava antes do marcador (estado de `a183c28^`), é resíduo antigo compartilhado com outros sete títulos do arquivo e corrigi-la aqui misturaria restauração com reformatação. Manifesto regravado para selar o arquivo.

**Conferência.** Nenhum outro arquivo versionado carrega marcador de conflito; as sequências de `<` e `>` em `evidencias/*.txt` são separadores do documento-fonte copiado, fora da selagem por definição. Nenhum portão lê o corpo do `CHANGELOG.md` (as duas citações em `scripts/verificar_runtime.js` e `scripts/verificar_publicado.js` são comentário e caminho de arquivo), e a mudança não toca `data/`, `*.py`, workflows nem dependências — o bloco "dado e coleta" de `portoes.yml` não é acionado.

## §160 · Cadência do robô: quatro rodadas por dia, a cada 6 horas · 22/09/2026

Classe **encanamento operacional**; nenhum dado, número ou página muda. Decisão editorial de 22/09/2026, escrita naquele dia e aplicada agora — o número §160 estava reservado para ela.

**O que muda.** As duas rodadas diárias (09h e 21h UTC, decididas na v2.2.4 E4 e em 03/09/2026) passam a ser **quatro, a cada 6 horas**: 01h, 07h, 13h e 19h UTC — 22h, 04h, 10h e 16h de Brasília. Os quatro horários são deslocados da rodada semanal de domingo (03h UTC) para não caírem no mesmo minuto dela; a trava de concorrência do workflow já faz a segunda esperar a primeira, e evitar a colisão poupa a fila.

**Por quê.** Acelerar a varredura integral dos 5.571 municípios enquanto `INTENSIVO_DE`/`INTENSIVO_ATE` estiverem ativas. O motivo continua de pé quando esta entrada é aplicada: o contador da varredura mede **2.741 municípios consultados** (119 com menção, 179 lidos sem menção, 2.440 sem diário indexado, 3 indefinidos) — pouco mais da metade. A cadência é **mantida depois da semana intensiva**, até nova instrução da editoria.

**O que não muda.** A regra de cadência de `atualizar.py`: fora da semana intensiva, a execução que não cai no dia de publicação **encerra sem comitar**. O compromisso público com o leitor continua sendo o domingo (`obrigado.html` e `pesquisadores.html` prometem o mesmo dia, e o portão de cadência confere). Mais rodadas significam mais consulta e mais preservação de evidência, não mais publicação.

**Interação com os tetos de tempo do §172.** Cada rodada tem teto de 180 min por job e tetos por etapa; com 6 horas de intervalo, nem a rodada mais longa (75–105 min, mais o OCR do §177) alcança a seguinte.

**Teste.** Workflows válidos com teto em todo job; portão de cadência verde (dia de publicação medido no fuso da redação, cron semanal no dia certo em Brasília, promessa pública igual nas duas páginas); portão 12 em árvore limpa. `docs/PROTOCOLO_ATUALIZACAO.md` passa a descrever a cadência nova — era o único lugar que ainda dizia "duas rodadas por dia".


## §159 · Da notícia ao documento: cada pista de imprensa é seguida até candidatos a ato oficial, que passam pelo mesmo portão e juiz · 22/09/2026

Classe **método + código** (`seguir_pistas.py`). Decisão editorial de 22/09/2026: notícia nunca pontua; é pista de que o plano existe — a máquina deve ir atrás do ato.

**Por que três rotas e não só o Querido Diário.** Contagem real: das 172 pistas de imprensa pendentes (A/B), só **33, em 19 municípios, têm diário indexado no QD** (518 municípios cobertos, `data/cobertura_qd.json`). O QD resolve ~20%; o resto exige outras rotas. E a API do QD estava fora do ar (503 nos dois domínios) no momento do teste — a cascata não pode depender de uma rota só.

**As rotas, da mais precisa à mais ampla.** (1) **Links da própria notícia**: jornal local costuma linkar o decreto ou o PDF; entram os links para host oficial que sejam PDF, diário, ou cujo endereço/texto fale em decreto, lei, portaria, plano, PLANCON. (2) **Querido Diário** por código IBGE, edições desde 01/10/2025 com os termos do plano — só para municípios com cobertura. (3) **Busca no domínio oficial** via o SearXNG efêmero da cadência: "{município}" UF decreto "plano de contingência", só resultados em host oficial. Até 4 candidatos por rota.

**Sem caminho paralelo.** Cada candidato vira uma **pista nova** (`origem: seguimento_*`, `pista_origem` = id da notícia) e segue o caminho já testado: triagem → `revisar_pistas --preparar` (candidatos da cascata primeiro, sem filtro de nível — o título costuma ser nome de arquivo) → portão automático do §156 (ato publicado de 2026, lido no próprio diário/PDF) → juiz com derivados e rollback (§158). A notícia de origem **nunca muda de status**: continua pendente e visível no card até o documento aparecer. O card não rotula documento oficial candidato como "publicação na imprensa". Rota indisponível fica registrada no `seguimento` da notícia e é refeita; notícia já seguida é refeita depois de 7 dias.

**Teste.** Autoteste hermético 7/7 (link oficial vira pista ligada à origem; não segue fonte oficial nem nível C; nunca altera o status da notícia; QD só com cobertura e falha sem quebrar; edição do QD vira candidato; busca aceita só host oficial; sem duplicar, refaz após 7 dias). Autotestes de `revisar_pistas.py` e `gerar_card_municipios.py` verdes. O teste com rede real acontece na cadência (sites de imprensa e o buscador não estão na rede do ambiente de edição).

## §158 · O juiz sincroniza os derivados antes dos portões (toda aplicação automática municipal era revertida) e grava a proveniência certa — Feira de Santana/BA aplicada ponta a ponta · 22/09/2026

Classe **correção de encanamento com efeito no índice**. Achado na cadência #7, a primeira com `npm ci`, foco e portão.

**O que aconteceu.** O portão do §156 fez exatamente o calibrado: de 30 documentos, entregou ao juiz só Serra/ES (já no banco — o juiz não duplica) e Feira de Santana/BA. O juiz aplicou Feira de Santana e **reverteu de novo**. Motivo real, lido no log: `✗ dados abertos: municipios.csv tem 265 linha(s), JSON tem 266`. O juiz ia de `municipios.json` direto aos portões, sem regenerar os derivados; `verificar_consistencia.py` reprovava, com razão. **Toda aplicação automática municipal estava condenada a ser revertida** — desde 31/08, o `npm ci` ausente só escondia isso.

**Consertos.** (1) `sincronizar_derivados()` — antes dos portões, o juiz regenera o que o workflow regenera depois da coleta (`recalcular_mare.py --write`, `gerar_dados_abertos.py`, `gerar_card_municipios.py`), com o mesmo `SOURCE_DATE_EPOCH`. (2) O backup passa a cobrir `data/`, `dados-abertos/` e `selos/` inteiros (a sincronização regrava o selo SVG de cada estado), e a reversão apaga arquivos criados depois do backup — reversão continua sendo reversão de verdade. (3) **Proveniência**: `aplicar_municipal` gravava `canal: "imprensa"` fixo; no teste, um ato lido no diário oficial sairia rotulado como vindo de jornal — o oposto da regra de 22/09. Agora o canal vem do endereço (`DOM` via Querido Diário ou diário municipal; `DOU`; `site_municipal`), a fonte diz o que é ("Diário Oficial do Município (via Querido Diário) — ato lido e classificado automaticamente"), e o documento guarda cabeçalho + ementa do ato, não 200 caracteres crus.

**Teste real, local, com rede.** Feira de Santana pelo caminho completo (download do PDF → foco → portão → juiz → sincronização → portões): **APLICADA, portões verdes**; registro `plano`, `DECRETO Nº 14.665 DE 21 DE AGOSTO DE 2026 Institui o Plano de Contingência do Município de Feira de Santana`, canal `DOM`. Cobertura populacional da BA: **18,3 → 22,6**. Reversão testada: aplicar + sincronizar alterou 15 arquivos; restaurar deixou a árvore limpa. A aplicação local foi desfeita — quem aplica é a cadência, com log.

## §157 · `CLAUDE.md`: as regras de trabalho num arquivo lido automaticamente pelo Claude Code · 22/09/2026

Classe **documentação de processo**; nenhum dado, página ou método muda.

A editoria passa a poder trabalhar pelo Claude Code, com o repositório numa pasta local permanente. O `CLAUDE.md` na raiz reúne o que antes estava espalhado em handouts de sessão: fluxo de mudança (PROTOCOLO §3.1), limites do merge automático (protótipo mostrado antes, publicação do domínio só com a palavra da editoria), lista de portões na ordem de `portoes.yml`, regras editoriais que o código não pode violar, regras de design e o que nunca entra no repositório público. Os documentos canônicos continuam prevalecendo; o arquivo só aponta para eles. Manifesto regravado para selar o arquivo novo.

## §156 · Portão da aplicação automática: o juiz só pontua sozinho com o ato publicado de 2026 lido no próprio documento — e cinco erros reais que ele teria cometido · 22/09/2026

Classe **correção de segurança do dado + método declarado**. METODOLOGIA §40 ganha o parágrafo "Quando a máquina pontua sozinha".

**O que a primeira rodada com PDF mostrou (cadência #6).** O juiz leu os diários, classificou e **aplicou 6 pistas** — todas revertidas pelos portões, mas por acaso: faltava `npm ci` no workflow de cadência e `verificar_estrutura.js` quebrou (`MODULE_NOT_FOUND`). Conferidas uma a uma, **5 das 6 eram erradas**: lei municipal de 2021 (Guaraniaçu/PR, duas), "Lei 17 · 2026" e "Portaria 4.609 · 2026" com ano solto (Antônio Olinto/PR, Alagoinhas/BA), PDF de 2024 sem número (Nova Iguaçu/RJ). Na preparação local apareceram mais: a Lei federal 14.133/2021 (licitações) citada em edital, lida como o ato (Sátiro Dias/BA, Itapirapuã Paulista/SP), e decreto de 2021 (Andradina/SP). Consertar só o `npm` teria transformado esses erros em registros.

**Três causas e três consertos.** (1) **Diário inteiro em vez do ato**: um diário tem dezenas de atos; classificar o documento todo dava DUVIDA e extraía o número do primeiro ato da edição (e "4574", nº de lei, como ano). `focar()` recorta a janela do ato da pista — âncora no número citado no trecho, recuo até o cabeçalho do próprio ato, normalização que preserva posições; o juiz recebe o texto focado. (2) **Ano implausível**: `RE_DATA_ANO_SOLTO` passa a aceitar só 19xx/20xx. (3) **Portão cumulativo antes do juiz** (`portao_automatico`): fonte oficial; ato publicado (diário ou PDF — notícia em portal oficial não é o ato); natureza ex-ante; data completa, válida, de 2026 e não futura; número que não seja lei federal citada (só leis são checadas contra a lista — "Decreto nº 101" municipal não é a LC 101); texto articulado; teste do objeto (Executivo, família do ciclo, pelo município); município nomeado no ato; nenhum alerta ativo da triagem de confiança (homônimo de outra UF etc.). Qualquer falha → fila humana com o motivo gravado em `preparacao.portao_automatico`.

**Mais.** `npm ci` no workflow de cadência (os portões do juiz rodam em Node). Revertida por portão deixa de ser decisão final: continua pendente e é refeita. Preparação versionada (`PREP_VERSAO=2`): as 60 pistas preparadas pela versão sem foco são refeitas uma vez.

**Resultado com documentos reais** (40 pistas: Querido Diário A/B + as 6 revertidas, sem aplicar): o portão entrega ao juiz **2** — Serra/ES (Decreto nº 6.823, 05/07/2026; já no banco, o juiz não duplica) e **Feira de Santana/BA (Decreto nº 14.665, 21/08/2026, institui o Plano de Contingência)**. As 5 erradas: todas barradas. Barradas por motivo: 21 natureza DUVIDA, 5 sem texto articulado, 3 objeto indefinido, 3 resposta, 2 camada de saúde, 2 atos de 2021, 2 data incompleta. A precisão é o requisito; o recall do classificador sobre planos reais em DUVIDA é a próxima frente.

**Teste.** Autoteste de `revisar_pistas.py` com os casos reais (lei federal citada, ato de 2021, notícia em portal, município não nomeado, frio fora do objeto, decreto nº 101, homônimo, data inválida/futura, preparação antiga refeita uma só vez). Self-tests do classificador (97 decretos reais, 0 falsos positivos) e do juiz verdes.

## §155 · Card do município: tag de prioritário, situação no MARÉ, "publicação na imprensa encontrada" (peso zero, com link) e como pedir o documento ao gestor · 22/09/2026

Classe **produto + método**, três decisões editoriais de 22/09/2026: imprensa não pontua (nem "em elaboração"); entra no card como link; o card estimula o leitor a pedir o documento ao gestor público e diz como. Mais: tag de prioritário em cada município.

**Dado novo — `data/municipios_card.json`** (`gerar_card_municipios.py`, na cadeia canônica de derivados e nos dois workflows de coleta). Um objeto por código IBGE, só para municípios com algo a dizer: `prioritario` (aproximação populacional do Cadastro Nacional — o mesmo proxy de `gerar_prioritarios.py`), categoria no MARÉ (`municipios.json`; ausente = nada localizado), documento/url/data quando há registro, e `imprensa`: até 3 pistas pendentes de nível A/B (título, url, data, veículo), mais novas primeiro. Pistas C e rejeitadas ficam fora; a pista NUNCA vira categoria — peso zero por construção, coberto por teste. Quando o documento oficial aparece e o juiz aplica, a categoria sobe e a pista fica como proveniência. Hoje: 2.173 municípios (2.095 prioritários; 265 com registro; 117 com pista de imprensa), 382 KB, carregado só na primeira consulta.

**A consulta de `prefeituras.html` virou o card.** Antes: só os prioritários eram consultáveis, resposta sim/não. Agora: todos os 5.571 (referência IBGE); tag **prioritário**; "No MARÉ: …" com o documento linkado; a lista de publicações na imprensa, rotulada "pista — não pontua no MARÉ sem o documento oficial"; e, sempre que não há documento do tipo plano (nada localizado, não verificado, só decreto de emergência, ato de outro risco), o bloco **"Peça o documento ao gestor público"**: qualquer pessoa pode pedir sem justificar (LAI, Lei 12.527/2011), pelo e-SIC ou ouvidoria da prefeitura, ou pelo Fala.BR; texto pronto do pedido (plano vigente + ato instituinte, número e data); prazo de 20 dias; e-mail do MARÉ para reenviar o que receber. A mesma tag entra no tooltip do mapa de verificação em `defesa-civil.html`.

**Teste.** Autoteste do gerador 7/7 (prioritário sozinho entra; sem nada não entra; imprensa só A/B pendentes; imprensa nunca vira categoria; proveniência mantida). Card testado com Chromium real (Playwright) em quatro casos: Palotina/PR (prioritário, sem plano, 3 pistas de imprensa, convite a pedir), Salvador/BA (prioritário, plano localizado com link, sem convite), Acrelândia/AC (prioritário, só decreto de emergência → convite a pedir), grafia inexistente. Zero erros de JavaScript. Portões de vocabulário, voz, legendas, segurança, estrutura, acessibilidade e runtime verdes; cadeia de derivados idempotente.

## §154 · O juiz passa a ler PDF e datas por extenso — o diário oficial deixa de ser invisível (teste real: Feira de Santana/BA) · 22/09/2026

Classe **encanamento que destrava método**. Decisão editorial de 22/09/2026 (metodologia sem intervenção humana para o caso claro): a máquina nunca pontua sem documento oficial verificado; para isso precisa conseguir LER o documento oficial.

**Brecha 1 — PDF.** `buscar_texto()` do juiz (`julgar_e_aplicar_descobertas.py`) extraía só HTML por regex. Contagem real: **41 de 41** pistas do Querido Diário e 24 da busca web são PDF — invisíveis ao juiz, que devolvia texto de bytes binários ou nada. Agora detecta PDF por magic bytes (`%PDF-`), Content-Type ou extensão (servidores municipais mentem no tipo) e extrai com `pdfplumber` (já dependência; preserva espaçamento de palavras, ao contrário do pypdf nos PDFs-infográfico — nota em requirements.txt). Até 40 páginas / 60 mil caracteres; PDF só-imagem (escaneado sem OCR) vira "não obtido", nunca texto inventado.

**Brecha 2 — data por extenso.** `classificador_natureza.extrair_data()` lia "DE 21 DE AGOSTO DE 2026" como "2026". O portão de citação já aceitava ano solto (não bloqueava), mas o registro público sairia "ato 14.665, 2026". Agora: numérica completa > por extenso (normalizada para dd/mm/aaaa, com "1º") > ano solto.

**Brecha 3 — data da edição vs. data do ato** (achada no teste real): a primeira data do diário é a da EDIÇÃO ("DATA 22/08/2026"), que vem antes do decreto. `extrair_numero_e_data()` prefere a data na janela de 90 caracteres logo após o número do ato; cai para a busca global só sem data ali.

**Teste real, não fixture.** `data.queridodiario.ok.org.br` está na rede permitida: baixado o diário de Feira de Santana/BA (edição 3605), lido como PDF, extraído "DECRETO Nº 14.665" / "21/08/2026", classificado EX_ANTE ("nomeia instrumento conhecido: plano de contingência, sem dano relatado"), citação completa. É o primeiro plano municipal da fila que o juiz consegue aplicar sozinho — na próxima rodada de cadência.

**Teste.** Self-test do classificador (97 decretos de resposta reais, 0 falsos positivos) verde, com os casos novos de data; self-test do juiz 5/5; leitor de PDF testado com PDF real gerado em memória. Nota inalterada até a rodada aplicar.

## §153 · Fila de revisão humana das pistas: leitura assistida, decisões registradas, homônimos · 22/09/2026

Classe **fluxo editorial + código** (`revisar_pistas.py`), a pedido direto ("vamos à fila de pistas").

**Lacuna estrutural encontrada.** O caminho testado de promoção (`julgar_e_aplicar_descobertas.py`: busca o documento, classifica ex-ante/resposta, extrai número e data, aplica com backup + portões + rollback) só consumia pistas do vigia de imprensa (`status == pendente_confirmacao_documento`, campos `alvo` e `fonte_provavel_oficial`). As pistas da busca web e do Querido Diário — a maioria da fila — nunca entravam nele, mesmo as de nível A com decreto nº e data. Duas esteiras disjuntas.

**O que foi construído — um adaptador, não um juiz novo.** (1) `--preparar` (roda nas rodadas de coleta, com rede): para toda pista pendente de nível A ou B, busca o texto da URL, extrai número/data, classifica natureza e grava em `preparacao` na própria pista; fonte oficial delega ao juiz com o esquema que ele espera — pode aplicar sozinho, como já faz para o vigia; fonte não oficial só recebe leitura assistida. Nunca rebaixa, nunca descarta. (2) `--aceitar ID --ato --data` / `--rejeitar ID --motivo` / `--adiar ID`: decisão humana gravada em `decisao_humana` na pista; aceitar promove pelo mesmo `aplicar_municipal()` (backup + portões + rollback); a rejeição é da pista, não do município. (3) `--relatorio` → `docs/FILA_PISTAS.md`, legível, por município, com número/data/natureza pré-extraídos; decididas ao fim, nunca fora. Ids estáveis (sha1 ibge|url|trecho) gravados na triagem.

**Falso positivo real achado no próprio relatório, nível A.** "Candeias/MG" com URL `prefeitura.candeias.ba.gov.br` — homônimos: a busca por Candeias MG devolveu a prefeitura da Bahia. Regra nova na triagem de confiança: UF no host oficial divergente da UF da pista → alerta `uf_divergente_na_url`, nível C. Pegou 3 na fila (Candeias MG, Caxias MA, Santa Rosa RS). Alerta informativo `ano_anterior_ao_ciclo` (URL/título de 2025 sem 2026) — não rebaixa: pode ser `plano_antigo` (0,6), decisão humana.

**Complemento do mesmo dia — citação pelo trecho, sem rede.** O relatório real mostrava Feira de Santana/BA (nível A) como "citação não extraída" apesar de o trecho trazer "DECRETO Nº 14.665 DE 21 DE AGOSTO DE 2026": a extração só rodava em `--preparar` (rede), e as pistas do Querido Diário são PDFs, que o buscador de texto do juiz (feito para HTML) não lê. Agora número/data são extraídos também do título+trecho da própria pista (`citacao_do_trecho`), rotulados "(do trecho)" no relatório; em `--preparar`, o documento manda e o trecho completa o que faltar; documento não obtido guarda a citação do trecho em vez de nada. Pendência declarada: o parser de data compartilhado (`classificador_natureza.extrair_data`) lê só o ano em "21 DE AGOSTO DE 2026" — não alterado aqui porque governa o portão de citação do juiz. Cadência: `--limite 30` por rodada e timeout 60 min, porque `--preparar` pode acionar os portões para pistas de fonte oficial.

**Teste.** Autoteste hermético 9/9 (citação do trecho, caso Feira de Santana; ids estáveis; preparar só A/B e nunca descarta; oficial delega, não oficial não; documento não obtido não quebra; rejeitar/adiar só registram; aceitar exige citação; aceitar aplica e desfaz se portão falhar; relatório). Triagem de confiança 11/11 com o caso Candeias. Portão de autotestes inclui os dois. Consistência, MARÉ (45,1) e idempotência verdes.

## §152 · Decisão 3 do teste do objeto: plano municipal é julgado pelo risco do município, nunca pelo alerta da UF (caso Salvador) — registro ex-ante, sem mudança de nota · 22/09/2026

Classe **decisão metodológica ex-ante + trava em teste**. Média nacional inalterada: 45,1.

**Origem.** Pergunta editorial direta: "um plano é um plano; em nível municipal ele tem que estar adequado ao município, não ao alerta estadual — Salvador tem plano de enchente e está correto, mesmo a Bahia tendo alerta de seca".

**O que a investigação mostrou.** O índice **já pratica a regra**: Salvador consta em `data/municipios.json` como `plano` (1,0), "Operação Chuva 2026 / PPDC (Codesal)", sem nenhum desconto pelo alerta estadual de estiagem. Os únicos `nao_el_nino` do banco são 4 municípios do AP com portaria de doença viral — epidemia, corretamente fora do ciclo. O teste do objeto municipal (`classificar_objeto(trecho)`, §5.2.1) aceita qualquer das três famílias do ciclo e não recebe a UF como insumo; a triagem de confiança de §150 idem. A tabela risco×instrumento (`consist.json`, CONSIST) compara instrumento **estadual** com risco **estadual** — legítima nessa escala, e só nela. O fator de alinhamento (Correção A, f_A) **não está no motor** — é candidato v2.3/v2.4.

**Por que ainda assim mudar.** Dois riscos reais: (1) a metodologia não dizia isso explicitamente, e quem revisa a fila pode aplicar a regra estadual por engano — a própria editoria leu assim; (2) o candidato v2.4 "alinhamento ao risco no crédito municipal (mesmo fator f_A)" estava descrito de forma que, implementado contra o alerta da UF, criaria exatamente o erro de Salvador.

**Feito.** METODOLOGIA §5.2.1 ganha a "Decisão 3 — escala do julgamento", com o caso Salvador e a regra: família julgada pela exposição do município; CONSIST nunca cruza com município; regra imposta na assinatura das funções. §26 (candidatos v2.4) recebe a restrição ex-ante: alinhamento municipal só contra exposição do próprio município (suscetibilidade geo-hidrológica por município do Cemaden; Semiárido/SUDENE; Risco de Fogo/INPE por área; exposição costeira), nunca contra a UF. A regra virou caso de teste nas duas camadas de triagem (`classificar_pista_civil.py` t15, `triar_confianca_pistas.py`): plano de chuvas/enchentes em Salvador/BA → `objeto=el_nino`, nível A — para que nenhuma mudança futura a reabra em silêncio.

**Registro honesto.** Não houve mudança de número porque não havia erro no dado; houve mudança de método declarado, no lugar certo e antes de qualquer implementação que pudesse beneficiar ou prejudicar um ente.

**Teste.** Autotestes das duas triagens verdes (15/15 e 10/10). `recalcular_mare.py --check`: 45,1, inalterado. Vocabulário público, consistência e idempotência dos derivados verdes.

## §151 · Blog do MARÉ entra na barra de navegação, antes de Imprensa; quadros com a mesma borda superior, uma cor por eixo · 22/09/2026

Classe **decisão editorial aplicada**. Depois de ver o protótipo (§149) nas capturas, a editoria aprovou a página e pediu: (1) publicá-la na barra, **antes de Imprensa** — rótulo "Blog", ordem canônica dos portões atualizada (as exceções de "página fora da barra" para `blog.html` em estrutura e acessibilidade saem); (2) manter as bordas com cor nos quatro quadros, mas **no mesmo formato**: borda superior de 3 px em todos, uma cor por eixo (musgo · antecipação, sintético · saúde, argila · resposta, seca · sinais físicos), com os modificadores `--acento-*-topo` em `base.css`. Nome final, assinatura dos textos e o texto de exemplo seguem em aberto. **Adendo (mesmo dia):** rótulo na barra passa de "Blog" para **"Blog do MARÉ"** (pedido da editoria; URL segue `blog.html`).
## §150 · Metodologia de triagem das pistas: nível de confiança A/B/C, fila por município, regra contra falsos negativos · 22/09/2026

Classe **método editorial + código**, a pedido direto ("as pistas, nós vamos decidir se entram ou não, construindo uma metodologia; cuidado com falsos negativos"). Seção pública nova: METODOLOGIA §40.

**Diagnóstico.** 172 pistas na fila, 112 delas da busca web; 124 em "indefinido" na triagem textual existente (`classificar_pista_civil.py`) — que é boa, mas calibrada para linguagem de diário oficial ("fica instituído", "decreto nº"). Manchete real de imprensa ("Marília prepara plano de contingência…") não tem essa linguagem e caía toda em "indefinido", sem ordenação nenhuma entre as centenas que a cadência de 2h vai trazer.

**O que foi construído — `triar_confianca_pistas.py`.** Camada complementar (não substitui a textual), só sinais literais, todos gravados na pista (`sinais`, `alertas`, `pontos_confianca`, `nivel_confianca`): fonte (host oficial > imprensa > desconhecido); onde o município aparece (título > URL > início do trecho > só no trecho); onde o termo de plano aparece; impressão digital de ato formal; família de risco do ciclo; triagem textual como sinal a mais. Alertas que rebaixam para C sem descartar: risco errado no título; município citado de passagem numa lista. Saída: `data/pistas_revisao.json` (derivado, regenerado a cada rodada) — pistas agrupadas por município, municípios ordenados pelo melhor nível. Roda nos dois workflows de coleta, antes do commit; autoteste no portão. A busca web passa a guardar o `titulo` do resultado (sinal mais forte; até agora se perdia).

**Regra contra falsos negativos, e o que ela custou.** A camada NUNCA descarta: C fica no fim, visível. Calibrando contra as 172 pistas reais, três falsos negativos genuínos apareceram e viraram regra + caso de teste: (1) risco errado só conta no **título** (plano real de chuvas cita dengue de passagem no trecho); (2) comparação de nomes **sem acento** — "Petrópolis" não casava com "petropolis" na URL e um plano real do g1 estava em C; (3) nome no **início do trecho** (posição de manchete) conta, salvo em lista de municípios — corrigido depois de uma regressão pega pelo próprio teste (numa lista, "Ipixuna" caía nos primeiros 70 caracteres e ganhava o bônus). Parei de calibrar aí: mais ajuste em 172 amostras seria ajustar ruído; a revisão humana é o calibrador daqui em diante.

**Resultado na fila atual.** A=18, B=107, C=47 em 111 municípios. Petrópolis: 5 pistas, todas B (antes: C). Caso Anita Garibaldi/Ipixuna: C com alerta, protegido por teste.

**Teste.** Autoteste 8/8 (réplicas dos casos reais de §141-§143 + os três falsos negativos da calibração). Portões de consistência, MARÉ, vocabulário verdes. Cadeia de derivados idempotente. `validar_workflows` verde nos três workflows tocados.

## §149 · Blog do MARÉ (protótipo): página nova fora da barra, quatro quadros de situação e textos em Markdown · 22/09/2026

Classe **página nova, decisão editorial em curso** (nome final, lugar na navegação e assinatura dos textos ainda por decisão da editoria; nada do índice muda).

**O que entra.** `blog.html`, publicada fora da barra de navegação como o Calendário, em dois blocos. (1) *Situação do monitoramento*: quatro quadros — MARÉ Legal, MARÉ Saúde, Defesa civil, Sinais físicos — lidos dos **mesmos arquivos** das páginas correspondentes (`indice`, `estados`, `municipios`, `monitor_saude`, `resposta/por_uf`, `sinais_risco`), sem nenhum número próprio; cada quadro tem crédito no formato único com a data da **sua** fonte, porque as cadências diferem (índices semanais; alertas, avisos e sinais diários). Os quadros substituem a ideia de um "post de status" automático: o pulso da rotina fica nos números, o fluxo de textos fica só para a voz editorial. (2) *Textos*: lista gerada de `data/blog/posts.json`.

**Textos como dado.** Um Markdown por texto em `blog/posts/AAAA-MM-DD-slug.md`, com cabeçalho (titulo · data · categoria `analise`|`diario` · autor · resumo). `gerar_blog.py` gera a página de cada texto (`blog/<slug>.html`, masthead e rodapé copiados de `blog.html` com caminhos reescritos para `../`), o índice e o feed Atom `feeds/blog.xml`; `--check` entra na cadeia do Portão 12 (`verificar_derivados.sh`, depois do carimbo de assets) e a geração entra em `atualizar.py` depois dos dados abertos. Dependência nova travada: `Markdown==3.10.2` (BSD). Um texto de exemplo, "O que este espaço acompanha", assinado provisoriamente pela editoria.

**Componentes.** Só em `base.css`, com tokens: `.grade-cartoes--4` (4 → 2 → 1 colunas nos breakpoints 1020/640), `.cartao--status` (mesmo `.gauge-head/.gnum` da inicial) com `.status-dl`, `.blog-lista` e a prosa de `.post`. Nenhum estilo inline, nenhum hex.

**Portões.** Página registrada em estrutura (exceção de item ativo, como o Calendário), acessibilidade, figuras, legendas, vocabulário, voz editorial, palavras (meta 250 · teto 300), SEO e sitemap; cabeçalho de cache `must-revalidate` para `/blog/*` no `netlify.toml`. Suíte de página completa verde, inclusive móvel (390 px) e consistência visual (1366 · 900 · 390) em Chromium real; `gerar_blog.py --autoteste` verde.

**Fica com a editoria.** Nome da página, entrada (ou não) na barra, assinatura dos textos e o próprio texto de exemplo.
## §148 · Cadência automática da busca web (2h em 2h até cobrir todos os municípios, depois 4x/dia); causa raiz do run #117 corrigida; site fica no ar atrás de senha durante a rodada · 22/09/2026

Classe **infraestrutura**, quatro mudanças relacionadas, a pedido editorial direto depois dos testes de 21/09.

**1. Cadência nova — `busca_web_cadencia.yml`.** Workflow próprio, enxuto: só busca web (150 municípios, prioritários primeiro — §143) + sincronização do índice + derivados + commit + reposição do domínio. Não roda o pipeline inteiro (o `atualizar.yml` segue semanal + diário para as outras fontes — rodar tudo a cada 2h martelaria fontes que não mudam nesse ritmo). Cron `0 */2 * * *`; o próprio job decide a fase lendo `ciclos_completos` em `data/busca_web_estado.json` (novo campo, gravado por `proximo_lote_automatico()`): **fase 1** (0 ciclos) roda a cada 2h; **fase 2** (≥1 ciclo — todos os 5.571 já tentados pelo menos uma vez) roda só em 00/06/12/18 UTC, 4x/dia, até a editoria mandar parar. Com 150 por rodada são 38 lotes: fase 1 cobre o Brasil inteiro em ~3 dias. Mesmo grupo de concorrência do `atualizar.yml` — nunca duas rodadas commitando ao mesmo tempo. `workflow_dispatch` com `forcar=true` ignora a regra de fase (teste).

**2. Causa raiz do run #117 (falha em "Commit das alterações de dados").** `workflow_dispatch` e `schedule` fixam `head_sha` no momento do disparo. `#117` foi disparado enquanto `#112` ainda rodava (fila do concurrency), partiu de um `main` antigo; `#112` commitou `busca_web_estado.json`, `#117` mudou o mesmo arquivo, e o rebase antes do push deu conflito real — a rodada se perdeu. O mecanismo de rebase (03/09) cobria PR editorial no meio da rodada (arquivos diferentes), não uma rodada anterior do próprio robô tocando o MESMO arquivo de estado. Com cadência de 2h isso viraria rotina. Solução estrutural, nos dois workflows: passo "Partir do main atual" logo após o checkout — `fetch` + `reset --hard` no `main` real, agora, não no SHA fixado.

**3. Site no ar durante a rodada (pedido: "para mim ele precisa estar visível").** Em modo `senha` não existe leitor anônimo — quem não tem a senha recebe o pedido de login, não vê página nenhuma. Publicar a cortina "em atualização" no início da rodada só tirava o site de quem TEM a senha por 75-105 min, sem proteger ninguém a mais. Agora, em modo `senha`, o passo da cortina é pulado: o site anterior (completo e consistente — o deploy do fim é atômico) fica no ar atrás de senha a rodada inteira, e a versão nova entra no passo final. Mais seguro, inclusive: o domínio nunca fica sem Basic-Auth. A cortina continua valendo nos modos `cortina` e `aberto`, onde leitor existe. (A nota do `publicacao.json` fala em "véu no navegador"; esse JS não existe mais no código — a proteção real hoje é só o Basic-Auth do Netlify.)

**4. Contador de ciclos.** `busca_web_estado.json` ganha `total_lotes` e `ciclos_completos`; autoteste da rotação cobre a virada de ciclo.

**Ainda não feito, próximo passo**: a metodologia de triagem das pistas (pedido editorial da mesma mensagem — "cuidado com falsos negativos") — merece PR próprio e seção na METODOLOGIA.

**Teste.** Autoteste `monitorar_busca_web.py` 8/8. `validar_workflows.py`, `testar_reposicao_dominio.py`, `testar_cadencia_publicacao.py` verdes. O workflow novo só aceita `workflow_dispatch` depois de existir em `main` — teste real com `forcar=true` logo após o merge.

## §147 · Causa raiz real de "os mapas não aparecem": cache-busting nunca rodou em §145/§146 — corrigido; texto de #resposta removido por completo · 21/09/2026

Classe **bug real de processo, achado em produção** — mais importante que o conteúdo em si.

**O que a pessoa via.** Depois de duas rodadas de correção (§145, §146), publicadas e confirmadas por teste local com Chromium real, o site em produção continuava sem mostrar os mapas, e o texto de `#interpDepois` continuava mostrando o placeholder "—" em vez do valor calculado.

**Causa raiz — não era o código, era o processo.** `/assets/*` tem `Cache-Control: max-age=86400` (netlify.toml) — 24h de cache no navegador. `scripts/carimbar_assets.py` existe exatamente para isso: reescreve `?v=<hash>` em cada referência a asset toda vez que o conteúdo muda, forçando o navegador a buscar de novo. Editei `assets/js/defesa-civil.js` duas vezes hoje (§145, §146) e rodei `gerar_manifesto.py` nas duas — mas nunca `carimbar_assets.py`. Confirmado o descompasso: o HTML apontava para `?v=8b21b8da`, mas o hash real do arquivo já era outro. Navegadores que já tinham visitado a página continuavam servindo o JavaScript de ANTES de qualquer mudança de hoje — código que tenta manipular elementos removidos (`chartDonut`, `chartCapitals`), o tipo de erro que trava a execução do script antes de chegar no código que desenha os mapas. Meus testes locais (Playwright contra servidor limpo, sem cache) nunca reproduziriam isso — não havia cache para reproduzir.

**Corrigido.** `carimbar_assets.py` rodado — hash agora bate com o conteúdo real (confirmado por conferência direta: sha256 do arquivo = hash na URL). `/*.html` tem `max-age=0, must-revalidate` (sem cache) — um recarregamento normal da página já basta, não precisa de cache limpo manualmente.

**Texto removido, pedido direto.** O bloco `#resposta` que sobrou depois de §146 (frase C18 + interpDepois) foi identificado como sobrando e removido por completo. Os dois portões que verificavam esse texto especificamente em `defesa-civil.html` foram ajustados: `verificar_runtime_resposta.js` mantém a checagem da frase C18 na home (onde ela já também vivia — não desaparece do site, só sai desta página); `verificar_runtime_mapas.js` teve o teste (g), específico de `interpDepois`, removido.

**Teste.** Suíte completa de derivados confirmada idempotente (`verificar_derivados.sh --idempotencia`) — incluindo, desta vez, o carimbamento de assets. Reconfirmação visual com Chromium real: 4 mapas com conteúdo SVG, 0 erros de JavaScript, 1 painel só, `#resposta`/`#interpDepois` ausentes.

## §146 · Defesa civil: removido o painel "Decretos de emergência" que sobrou vazio depois do mapa subir · 21/09/2026

Classe **correção de página, mesmo dia**. Achado real ao testar §145 na prática: a página numera painéis automaticamente ("1 · ", "2 · " — `assets/colunas.js`, pelo índice na página), e o segundo painel apareceu como "2 · Decretos de emergência" sem nenhum elemento visual — só texto, já que o mapa tinha subido pra grade principal. Pedido direto: esse quadro tem que sair.

**Primeira tentativa removeu texto protegido por portão — pego antes de mesclar.** O painel continha duas informações que `verificar_runtime_resposta.js` e `verificar_runtime_mapas.js` verificam explicitamente: a frase legal sobre transferências voluntárias suspensas durante o defeso eleitoral (regra C18), e um fato calculado dinamicamente (`interpDepois`: primeiro decreto do ciclo e quantos decretos caíram no período eleitoral). Remover o painel inteiro quebrou os dois portões — não é texto decorativo, é conteúdo com proteção deliberada.

**Correção**: o texto voltou para a página, mas fora de qualquer `.panel` (não gera numeração, não aparece como "quadro") e fora de qualquer `.figure` (regra própria do site: nenhum parágrafo solto dentro de cartão de mapa/gráfico). Um `<div id="resposta">` simples, sem classe `panel`, carrega as mesmas duas frases de antes — satisfaz os portões sem recriar a aparência de painel vazio.

**Testado de ponta a ponta, não só o código — duas vezes.** Servida a página localmente e verificada com Chromium real (Playwright, não jsdom): antes da correção final, confirmação visual de 1 painel só e os 4 mapas com conteúdo SVG real; depois de restaurar o texto, reconfirmado que `#resposta` existe com o texto certo mas não é `.panel` (não aparece numerado), sem nenhum erro de JavaScript.

**Teste.** Os dois portões que pegaram o problema (`verificar_runtime_mapas.js`, `verificar_runtime_resposta.js`) voltaram a passar. Suíte completa de estrutura, figuras e consistência verde.

## §145 · Defesa civil: 4 mapas juntos no topo, removida a seção "Ver mais" (dois gráficos de status) · 21/09/2026

Classe **edição de página, pontual**. Pedido editorial direto.

**O que mudou.** O mapa "Cidades que decretaram emergência" (antes sozinho, mais abaixo, num painel próprio) subiu para a primeira grade de figuras, junto aos outros três mapas (Verificação municipal, Cobertura e natureza, Municípios prioritários) — agora 4 mapas juntos, 2×2. A seção `<details>` "Ver mais: status geral (27 UFs) e status das capitais", que escondia dois gráficos (donut de status estadual, barras de status das capitais), foi removida por completo.

**O que ficou.** O texto explicativo sobre decretos de emergência (desde quando conta, regra de transferências suspensas 04/07–25/10, link para o calendário eleitoral) continua na página, no mesmo painel de antes — só sem a grade que continha apenas o mapa, que já subiu. Um trecho do texto ("a tabela abaixo agrega...") referenciava algo que não existe mais nessa posição — corrigido para "o mapa acima", refletindo a nova estrutura.

**Limpeza no JS** (`assets/js/defesa-civil.js`): removidas as duas chamadas `new Chart(...)` (donut, capitais) cujos elementos não existem mais na página, e as 7 variáveis que ficaram sem uso depois disso (`UFS_POR_STATUS`, `CAP_POR_STATUS`, `quebraLinhas`, `PALETTE`, `LABELS`, `STATUS_ORDER` — órfãs pela remoção; `STATUS_LABEL` já estava órfã antes, achada ao limpar essa área). Removidas as duas entradas correspondentes na lista de créditos/fontes. `MonitorMapas.padraoGraficos(window.Chart)` mantida — configura padrões possivelmente compartilhados com outros scripts da mesma página, sem custo real em mantê-la mesmo sem uso local direto.

**Teste.** Varredura em todo o projeto confirma zero referências residuais aos elementos removidos. Sintaxe JS válida. Portões de estrutura, runtime, acessibilidade, figuras, legendas, vocabulário, voz editorial, SEO, palavras e segurança — todos verdes.

## §144 · Busca web já roda 2x/dia via cadência existente (achado, não construído); lote aumentado de 60 para 150 · 21/09/2026

Classe **achado de infraestrutura já existente + ajuste de velocidade**. Pedido editorial: "temos que rodar mais de uma vez por semana, precisamos começar agora".

**Achado.** `atualizar.yml` já tem dois crons diários (09h e 21h UTC) além do semanal — construídos em setembro para a "semana intensiva" de coleta de diários municipais, controlada por `INTENSIVO_ATE`/`INTENSIVO_DE`. Os steps de busca web (subir SearXNG + `monitorar_busca_web.py`) ficam fora dessa lógica condicional — rodam incondicionalmente em todo disparo do workflow, scheduled ou manual. Confirmado no histórico real: o run `#96` (cron das 21h de hoje) já rodou a busca web com sucesso. Ou seja, **a busca web já roda 2x/dia — 14x por semana — sem precisar de nenhum workflow novo.** `concurrency: group: atualizar-dados, cancel-in-progress: false` já garante que disparos concorrentes esperam na fila em vez de se cancelar ou colidir.

**Ajuste.** Tamanho do lote por rodada aumentado de 60 para 150 — dentro da faixa já testada com segurança (200 municípios, 494s, zero falhas, §143). Com 2x/dia, isso dá até 300 municípios/dia — os 2.095 prioritários (já na frente da fila desde §143) cobertos em pouco mais de uma semana, ante os ~35 dias que a conta de 60/semana única sugeria.

**Nota**: o estado real de hoje (`data/busca_web_estado.json`) mostra só um avanço de lote persistido apesar de várias execuções ao longo do dia — provavelmente porque nem toda ação de hoje foi um disparo completo do `atualizar.yml` real (vários foram testes isolados via `diagnostico_sinais.yml`, ou rodadas em modo ensaio, que não persistem avanço). Não investigado a fundo; comportamento do mecanismo de rotação em si (fila FIFO via concurrency) está correto por desenho.

## §143 · Busca web: priorização por município prioritário (93 → ~35 semanas); investigação da peneira testada em escala e revertida por segurança · 21/09/2026

Classe **melhoria de velocidade confirmada + tentativa de melhoria de precisão testada e revertida**. Documentado com honestidade — nem tudo que foi tentado funcionou.

**Origem.** Pergunta editorial direta: "93 semanas é tempo demais, e por que Marília/SP — que sabemos ter um plano — não aparece nas buscas? O dicionário está bom?"

**Confirmado, com teste ao vivo real.** Marília estava na posição 3.421/5.571 (lote 58) — nunca tinha sido tentada, não é falha de algoritmo. Testando a query real contra o SearXNG: o sistema **encontra e aceita corretamente** a notícia real sobre o plano de Marília (fonte local, título já dizia "Marília prepara plano de contingência"). O algoritmo funciona para o caso principal.

**Implementado e mantido — priorização.** `ordem_prioridade()` tratava os 5.571 municípios igualmente dentro do ranking por UF/população. Os 2.095 municípios prioritários (mesmo proxy populacional já usado no resto do site, `data/municipios_prioritarios.json`) agora vêm todos primeiro, partição estável (mesma ordem relativa preservada nos dois grupos). Ciclo dos que mais importam: ~93 → ~35 semanas. Cobertura total inalterada — ninguém é descartado, só reordenado.

**Tentado e revertido — expandir a peneira para o trecho do resultado, não só o título.** Um resultado real da busca de Marília (fonte oficial do Governo de SP) foi rejeitado porque só o TRECHO, não o título, mencionava o plano — motivou uma primeira correção (aceitar termo de plano também no trecho) e depois uma segunda, mais ampla (aceitar também o nome do município no trecho). Testado em escala real (200 municípios, depois 30 com amostra de conteúdo inspecionada): a versão ampla gerou ruído grave — documentos extensos (relatórios estaduais, PDFs com tabela de muitos municípios) onde nome e termo aparecem no mesmo texto longo sem relação real entre si. Caso real: um documento sobre "MUNICÍPIO DE ANITA GARIBALDI/SC" foi rotulado como pista de Ipixuna/AM só porque "Ipixuna" aparecia em algum lugar da mesma tabela. Uma correção intermediária (restringir de volta o nome do município a título/URL, manter só o termo de plano no trecho) foi tentada e testada de novo contra os mesmos 30 municípios — **resultado quase idêntico, o ruído não veio de onde eu tinha diagnosticado**: os documentos problemáticos já tinham o nome do município genuinamente no título (por serem listas/tabelas), não só no trecho. Revertido por completo para o critério original (só título, para os dois lados) — testado, preciso, e o único que já rodou em produção sem sinal de ruído.

**Por que parar aqui.** Resolver isso direito (por exemplo, exigir proximidade entre os dois termos dentro do texto, ou filtrar por tipo de fonte) é trabalho novo, não um ajuste rápido — e arriscar a qualidade da fila por uma melhoria de recall não testada o suficiente é pior do que manter o critério mais estrito, que já é comprovadamente preciso.

**Teste.** `monitorar_busca_web.py --autoteste`: 7/7, incluindo o novo caso de priorização (partição estável, sem perda de cobertura). Suíte de consistência verde. Dois ciclos de teste em escala real via Action, com amostra de conteúdo inspecionada manualmente — não só a contagem.

## §142 · Busca web (SearXNG): rotação real de lotes — sem isto, a rodada semanal batia sempre nos mesmos 60 primeiros municípios, para sempre · 21/09/2026

Classe **correção de lacuna conhecida** — já registrada como pendência na entrega original (§140): "atualmente só lote 1 (60 municípios). Cobrir os 5.571 ao longo de semanas exige configuração de rotação." Corrigida no mesmo dia, a pedido direto (pergunta editorial: "por que 60 municípios apenas?").

**O problema real.** `atualizar.yml` chamava `monitorar_busca_web.py --lote 1 --tamanho 60` — fixo. Toda segunda-feira, pra sempre, a busca tentaria os mesmos 60 municípios de maior prioridade, nunca avançando para os outros 5.511.

**Correção.** `proximo_lote_automatico()`: estado mínimo persistido em `data/busca_web_estado.json` (só o número do próximo lote). Quando `--lote` não é passado explicitamente na chamada (novo padrão em `atualizar.yml`: `--tamanho 60`, sem `--lote`), o script lê o estado, usa o lote indicado, grava o próximo, com volta ao 1 depois do último — cobertura cíclica. Uma chamada manual com `--lote N` explícito (para teste, como as duas rodadas de diagnóstico de hoje) continua funcionando exatamente igual e **não mexe no estado da rotação automática** — testar não atrapalha o progresso real.

**Números reais**: 5.571 municípios ÷ 60 por rodada = 93 lotes — a cobertura completa leva cerca de 93 semanas (quase 2 anos) para passar por todos pelo menos uma vez. Isto é uma limitação conhecida e aceita do próprio uso de busca de terceiros sem chave (§140: motores de busca por trás do SearXNG já demonstraram bloqueio por volume — CAPTCHA do DuckDuckGo visto na primeira rodada de teste real), não algo que dê para acelerar sem risco de perder a fonte inteira por bloqueio.

**Teste.** Novo caso no autoteste hermético (mock de `ler`/`gravar`, mesmo padrão já usado em `coletar_diarios_municipais.py`): rotação avança 1→2→3 e volta a 1 com `total_lotes=3`. 6/6 casos verdes. Suíte de consistência verde.

**Achado adicional, ao testar este PR.** `main` estava com `data/verificacao_municipal.json` divergente do que `recalcular_mare.py --check` recomputava — confirmado num clone limpo, então pré-existente, não causado por esta mudança. Causa: a rodada real de hoje (busca web tocando 60 municípios, `marcar_fonte_consultada()` atualizando `fontes_consultadas.json`) mudou um dos quatro arquivos-fonte do derivado (`municipios.json`, `log_buscas.json`, `municipios_ibge_referencia.json`, `fontes_consultadas.json`) em algum ponto entre o `--write` interno de `atualizar.py` e o commit final do workflow, sem um `--write` final capturando essa mudança — a linha exata não foi isolada com certeza. Corrigido de duas formas: (1) `main` sincronizado agora (`--write` rodado, `--check` verde); (2) proteção estrutural — novo step "Sincronizar índice antes do commit" roda `--write`+`--check` logo antes do commit, sempre, para qualquer step futuro que também toque esses quatro arquivos.

## §141 · SearXNG testado de ponta a ponta contra uma Action real — bug real achado e corrigido (uso errado de referencia_ibge()) · 21/09/2026

Classe **correção de bug, achada só ao testar com rede real** (não hermético — o autoteste não pega isso, já que não bate na função de verdade contra dado real).

**Teste real.** Dois disparos isolados contra `diagnostico_sinais.yml` (workflow já existente, não um novo — `workflow_dispatch` não fica visível pra disparo em arquivo que só existe fora de `main`). Primeiro disparo: SearXNG subiu corretamente via Docker (worker iniciado, respondendo em `/search?format=json` em menos de 30s), mas o coletor quebrou: `KeyError: 'codigo_ibge'`.

**Causa raiz.** `coletores_base.referencia_ibge()` já retorna a tupla `(por_cod, por_nome)` pronta — não uma lista crua de registros. `monitorar_busca_web.py` tratava o retorno como se fosse a lista, tentando reconstruir `por_cod` por cima de um dict que já era `por_cod`, iterando sobre as CHAVES (strings de 7 dígitos) como se fossem registros. `coletar_diarios_municipais.py` usa a função corretamente (`por_cod, _ = referencia_ibge()`) — bastava seguir o mesmo padrão.

**Segundo disparo, mesmo teste**: funcionou de ponta a ponta — 1 município consultado, 0 lacunas, 2 pistas novas na fila. Os avisos no log do Docker (engines `ahmia`/`torch` falhando ao carregar, `duckduckgo` com CAPTCHA, `wikidata` com timeout) são o comportamento normal de um metabuscador tentando vários motores ao mesmo tempo — o resultado final confirma que o conjunto funciona o suficiente para produzir pistas reais.

**Teste.** Autoteste hermético (5/5) continua verde — não pegou este bug porque não chama `referencia_ibge()` contra dado real, só testa a peneira/vocabulário/dedup isoladamente; é exatamente por isso que o teste via Action real, além do autoteste, continua necessário para qualquer coletor novo. Suíte de consistência verde. `docs/MANIFEST_SHA256.txt` regenerado. Workflow de diagnóstico temporário usado para o teste será revertido (nunca mesclado a `main`).

## §140 · Busca web aberta (SearXNG efêmero) finalmente entregue — trabalho testado numa sessão anterior nunca tinha chegado ao repositório; rotina diária separada descontinuada, absorvida no relatório semanal · 21/09/2026

Classe **código + processo**, duas correções na mesma entrada.

**Achado real (parte 1).** Uma sessão anterior descreveu o SearXNG (metabuscador open-source efêmero, sem chave) como "pronto e testado" — mas verificação direta mostrou que `monitorar_busca_web.py` e `scripts/searxng_settings.yml` nunca chegaram a `main`: só existia um commit de diagnóstico (`350135e`), não o código final. Reconstruído do zero a partir da especificação já validada antes (query `"{município}" {UF} "plano de contingência" El Niño 2026`, peneira local por nome do município + termo de plano no título, dedup por (ibge, url, trecho) — mesmo padrão §132), reaproveitando `ordem_prioridade()` de `coletar_diarios_municipais.py` em vez de duplicá-la. Alimenta a mesma fila (`data/pistas_imprensa.json`, `origem: "busca_web"`) que os demais coletores de pista — revisão humana num lugar só.

**Bug evitado desta vez.** Antes de escrever o coletor, li o vocabulário real de `decisao` direto do código-fonte de `log_busca()` (`coletores_base.py`) em vez de reconstruir de memória — a sessão anterior tinha descoberto, só depois de rodar contra uma Action de verdade, que `"sem_mencao"` era rejeitado (o vocabulário exige `"coberto_sem_mencao"`). Usado o termo certo desde a primeira versão; autoteste novo (`t4_vocabulario...`) lê o vocabulário aceito via `inspect.getsource()`, não copia à mão, para que uma mudança futura no vocabulário quebre o teste em vez de quebrar em produção.

**Integração no pipeline.** `atualizar.yml`: SearXNG sobe via Docker logo antes dos vigias de imprensa, espera até 60s por `/search?format=json` responder, roda 60 municípios por rodada; se a instância não subir a tempo, o passo seguinte é pulado (não falha a rodada inteira por uma fonte de descoberta).

**Achado real (parte 2), sem relação com o SearXNG.** Ao investigar a numeração do CHANGELOG para esta entrada, descoberto que a prática de "rotina diária" (sessões manuais separadas, verificando portões e filas fora da Action) nunca teve definição formal no repositório — só é citada retroativamente em várias entradas antigas do CHANGELOG. Isso já tinha causado uma colisão real: os números §137/§138 desta sessão foram reaproveitados para outras mudanças (ativação da camada declarada, correção de arredondamento) porque o SearXNG/portões-condicionais originalmente previstos para esses números nunca chegaram a ser escritos no CHANGELOG. Decisão editorial (21/09/2026): a rotina diária separada é **descontinuada** — o que ela cobria de único (contagem das filas humanas, branches sem commit há mais de 14 dias) passa a fazer parte do relatório semanal automático (`atualizar.yml`), sempre, sem depender de uma sessão manual rodar à parte. Novo script `scripts/contar_filas_humanas.py` (achado ao testar: um fallback genérico inicial contava as CHAVES de cada dict, não os itens da lista — cada arquivo de fila usa uma chave diferente: `pistas`, `itens`, `fila`; corrigido para o nome real de cada uma).

**Teste.** `monitorar_busca_web.py --autoteste`: 5/5, hermético (peneira `relevante()`, vocabulário real, dedup). Suíte de estrutura, consistência, MARÉ e sinais verde. `scripts/contar_filas_humanas.py` testado contra os dados reais: 60/27/15/93/97, batendo com os números já conhecidos desta sessão. `docs/MANIFEST_SHA256.txt` regenerado.

## §139 · LAI ao SEDEC/MDR sobre o Cadastro Nacional de Municípios; base legal completa da obrigação de Plano de Contingência documentada na METODOLOGIA · 21/09/2026

Classe **transparência + documentação pública**. Nenhuma mudança de dado ou de nota.

**Origem.** Continuação direta da conversa sobre por que o desconto de 50% existe: pedido de registrar a base legal completa na metodologia pública e de tentar obter, via LAI, a lista real de municípios com a obrigação formal de Plano de Contingência.

**LAI gerada** (`gerar_lai.py`, novo modelo `MODELO_CADASTRO_NACIONAL`, mesmo padrão federal já usado para o pedido do Carro-Pipa): solicita à SEDEC/MDR a relação nominal dos municípios inscritos no Cadastro Nacional de Municípios com Áreas Suscetíveis (Decreto 10.692/2021), a publicação anual prevista no próprio decreto (não localizada até hoje), e se os planos existentes já passaram pela prestação de contas em audiência pública exigida por lei. Texto publicado no repositório privado, pronto para envio humano via Fala.BR (mesma regra de todo pedido de LAI do projeto — exige pessoa física identificada). Total de pedidos do projeto: 55 → 56.

**METODOLOGIA.md** ganha dois parágrafos novos dentro do item já existente sobre a camada declarada (C5): a distinção legal entre o dever geral (Lei 12.608/2012, arts. 2º e 8º — todo município) e a obrigação específica do documento formal (art. 3º-A, §2º — só municípios inscritos no cadastro do Decreto 10.692/2021, com atualização bienal e audiência pública anual exigidas pela Lei 14.750/2023); e a declaração explícita de que os "2.095 municípios prioritários" já usados pelo projeto (base Cemaden) são um proxy da população de risco, não uma confirmação de quem de fato completou a inscrição formal — corrigível quando a LAI responder.

**Teste.** `gerar_lai.py --autoteste`: 4 casos (56 textos, 56 registros, citação correta da lei em cada modelo, e novo caso específico confirmando que o pedido do Cadastro Nacional cita o Decreto 10.692 e a Lei 14.750 corretamente). Suíte de estrutura e consistência verde. PDF da metodologia e MANIFEST regenerados.

## §138 · Achado real pelo Portão 17: média nacional divergia entre "valores crus" e "valores publicados" — corrigido para a fonte mais defensável · 21/09/2026

Classe **correção de bug, achado só porque a nota mudou de verdade pela primeira vez**. Não altera o valor de hoje (45,1 nos dois métodos, coincidência dos dados atuais) — corrige a fórmula para não divergir quando a nota variar de novo.

**Como foi achado.** Testando §137 (ativação da camada declarada) antes de mesclar, o Portão 17 (robustez a atualização de dados, que perturba uma cópia do repositório e roda a cadeia inteira) falhou: `verificar_consistencia.py` viu `gaugeNum` (45,1) ≠ média recalculada (45,2) no cenário perturbado. Investigado a fundo, não era o `gaugeNum` que estava errado.

**Causa raiz.** `recalcular_mare.py` tinha DOIS métodos de calcular a média nacional coexistindo, nunca sincronizados: `calcular()` retornava `lin.mean()` — a média dos 27 valores **crus, antes do arredondamento individual por UF**; `verificar_consistencia.py` recalculava, de forma independente, a média dos 27 valores **já arredondados e publicados** (`sum(v["total"] ...)/27`). As duas contas podem divergir por erro de arredondamento acumulado — ficaram coincidentemente iguais a sessão inteira porque a nota nunca tinha mudado de verdade; a perturbação do teste (ou a ativação real de §137) foi a primeira mudança grande o bastante para expor a divergência.

**Por que isso importa.** Se alguém soma os 27 números da tabela pública do site e divide por 27, o resultado deve bater com o número do medidor principal — sem isso, o projeto fica exposto a exatamente o tipo de "conta não fecha" que sua própria disciplina de consistência existe para evitar.

**Correção.** `calcular()` agora retorna a média calculada a partir de `saida` (os totais já arredondados por UF) — mesma fonte que `verificar_consistencia.py` já usava. Uma linha, sem mudança de fórmula nos componentes individuais.

**Teste.** Portão 17 completo, do zero: 19/19 passos verdes (antes: `verificar_consistencia.py` falhava no cenário perturbado). Cadeia de derivados regenerada e confirmada idempotente. `--check` e suíte de consistência verdes com o dado real de hoje (45,1, inalterado). `docs/MANIFEST_SHA256.txt` regenerado.

## §137 · Camada declarada nacional (MUNIC/ICM) ativada na nota pública — antecipada de 26/10 para 21/09/2026, por decisão editorial explícita · 21/09/2026

Classe **mudança de regra editorial, com efeito real e imediato na nota pública**. Média nacional: **43,6 → 45,1**.

**Origem.** Depois de entender a regra (declarar ≠ publicar, desconto de 50%, trava até 26/10/2026) e a base legal por trás dela (Lei 12.608/2012: obrigação de Plano de Contingência vale para municípios no cadastro de risco, com exigência de atualização periódica e prestação de contas em audiência pública — que uma marcação de "sim" no censo não verifica), pedido editorial direto: aplicar isso permanentemente, em toda atualização, desde já.

**O que mudou.** `recalcular_mare.py`: a camada declarada nacional (MUNIC/ICM), antes só acessível via `--simular-declarado-nacional` (modo separado, sem tocar `indice.json`), passou a ser parte incondicional de `calcular()` — chamada padrão de `--write`/`--check`, sem flag nenhuma. O modo de simulação foi removido do código (não fazia mais sentido manter uma distinção entre "simulado" e "real" quando os dois viram a mesma coisa). `atualizar.py` não chama mais a simulação separadamente — o `--write` de sempre já cobre. `data/simulacao_declarado_nacional.json` removido (redundante: o que ele mostrava como "depois" é agora o valor real).

**Fórmula inalterada.** Mesmo desconto de 50%, mesma regra conservadora (usa o maior entre a declaração ao tribunal de contas e a declaração nacional MUNIC/ICM, nunca soma os dois). A única mudança é a data de vigência — antecipada de 26/10/2026 para hoje.

**Governança atualizada em três lugares**: `data/declarado_nacional.json` (`_governanca`, `vigencia_na_nota` → 21/09/2026), `METODOLOGIA.md` (§26, documentação pública), `coletar_declarado_nacional.py` (docstring). Também corrigido ali um erro pequeno e não relacionado: o docstring citava `icm_faixa` como campo produzido — nunca foi implementado (o parser real só extrai `icm_var8_plano_contingencia`); comentário agora reflete o comportamento real.

**Teste.** `recalcular_mare.py --write` rodado de verdade: 45,1. `--check` reproduz. Suíte completa (consistência, estrutura, runtime) verde. `docs/MANIFEST_SHA256.txt` regenerado.

## §136 · SIGPub: tentativa real de destravar via Storage Access API (Playwright 1.63, grantPermissions) — bloqueio confirmado, não é mais questão de esforço · 21/09/2026

Classe **investigação técnica, resultado negativo documentado**. Nenhum dado produzido, nenhuma alteração de nota.

**Origem.** Pedido direto: reconsiderar se o bloqueio de §130 (`requestStorageAccess: Permission denied`) era genuinamente intransponível ou só falta de esforço, independente de custo computacional.

**Ação real, não suposição.** `playwright` atualizado de 1.56.0 para 1.63.0 (verificado no changelog do pacote: `'storage-access'` só é concedível via `context.grantPermissions()` a partir da 1.59). `scripts/obter_token_sigpub.js` passou a conceder essa permissão explicitamente antes de navegar, complementar ao clique real (CDP) já tentado em §130.

**Resultado, testado contra produção real (não simulado):** `grantPermissions(['storage-access'])` retornou sucesso — mas o console da página continuou mostrando `requestStorageAccess: Permission denied`. A concessão de permissão do Playwright não satisfaz o que o navegador real exige internamente (o mecanismo provavelmente checa ativação transitória do usuário como condição separada, não só o estado da permissão — consistente com a especificação do Storage Access API).

**Conclusão.** Duas abordagens reais testadas (clique via CDP em §130; concessão de permissão aqui), nenhuma funcionou. Isto não é mais um caso de "não tentamos o suficiente" — é um mecanismo de segurança do navegador funcionando como projetado contra automação. Desbloquear exigiria intervenção no nível do binário do Chromium, fora do escopo razoável deste projeto. Mantido documentado para não repetir a tentativa.

**Teste.** `coletar_diarios_consorciados.py --autoteste` (14 casos) e suíte completa verdes — a dependência atualizada não quebrou nada em uso (visual, coletores). `docs/MANIFEST_SHA256.txt` regenerado.

## §135 · ICM/SEDEC: fonte real encontrada, esquema confirmado por download, coletor reescrito — 5.570 municípios coletados de verdade · 21/09/2026

Classe **código + fonte nova**. Não altera `data/indice.json` (camada declarada travada até 26/10/2026, §3.9) — `--check` confirma média inalterada.

**Origem.** Pedido direto: inventário completo de fontes possíveis para a camada declarada, regardless de custo computacional. ICM tinha `url: null` desde sempre — nunca verificado de fato.

**Achado.** Página oficial `gov.br/mdr/.../icm` lista as 20 variáveis do indicador; variável 8 é literalmente "Plano de Contingência". A mesma página disponibiliza `base_completa_icm_082026.xlsx` — todos os municípios, sem chave de API, atualizada 28/04/2026. Esquema real (inspecionado por download, não suposto): linha 1 é título da planilha, linha 2 é cabeçalho (`Código IBGE`, `UF`, `Município`, colunas numeradas `1`–`20`, `Soma`), valores das variáveis vêm como **inteiro 0/1**, não texto.

**Achado dentro do achado:** o normalizador de sim/não existente (`normalizar_sim_nao`) faz `str(v or "")` — `0 or ""` vira string vazia em Python (0 é falsy), então um valor inteiro `0` cairia silenciosamente em "NA" em vez de "não". Criado `normalizar_binario_icm()` dedicado, com teste de regressão específico para esse caso.

**Coletor reescrito.** `parse_icm_csv` (nunca funcionaria — ICM não distribui CSV) → `parse_icm_xlsx`, pulando a linha de título, casando coluna por nome/número. `fontes_declarado.json` ganha URL, aba, colunas reais.

**Teste real de ponta a ponta**, via Action antes de mesclar (não só autoteste): `coletar_declarado_nacional.py` rodado contra as duas fontes reais juntas — MUNIC 5.570 municípios, **ICM 5.570 municípios, var8 = 2.573 sim / 2.997 não**. Autoteste: 8 casos, incluindo o caso do inteiro 0 falsy e a prova de que a linha de título nunca é lida como cabeçalho. Suíte completa verde. `docs/MANIFEST_SHA256.txt` regenerado.

## §134 · Defeito estrutural de §120 eliminado: cortina "em atualização" publicada explicitamente no início da rodada, sem corrida com o passo final de reposição · 21/09/2026

Classe **correção de infraestrutura, sem alteração de dado ou nota**. Origem: domínio ficou aberto de novo mesmo após a correção de §133 (run #89 falhou); pedido editorial de tornar o ciclo cortina↔senha confiável.

O mecanismo antigo tinha dois deploys de produção competindo: push no ramo `publico` (auto-deploy do Netlify) em paralelo com o passo final, que esperava com `sleep(120)` a corrida terminar antes de sobrescrever. Frágil por desenho — exatamente o que falhou hoje.

Corrigido de vez: novo passo "Colocar 'em atualização' no domínio", logo no início do job `atualizar`, publica a cortina (conteúdo do ramo `publico`, buscado por `git fetch` autenticado com `GITHUB_TOKEN`) direto via `netlify-cli`, sem depender do gatilho do ramo. O passo final de reposição, inalterado em lógica, perdeu o `sleep(120)` — não há mais corrida para esperar. Pula em modo `ensaio`. Nunca bloqueia a rodada (`continue-on-error`).

`scripts/testar_reposicao_dominio.py` reescrito para verificar a arquitetura nova (passo inicial existe, vem antes do final, final roda com `if: always()`) em vez da antiga (checagem de `sleep`).

**Teste.** Portão verde, `validar_workflows.py` verde, sintaxe bash do step novo verificada isoladamente. Suíte completa (consistência, MARÉ reproduzido) verde. `docs/MANIFEST_SHA256.txt` regenerado.

## §133 · URGENTE: guarda booleana de apenas_repor_dominio nunca funcionou (comparação com literal `true` falha contra input de workflow_dispatch); portão de ordem dava falso positivo · 21/09/2026

Classe **correção de bug de infraestrutura, sem alteração de dado ou nota**.

**Origem.** Pedido editorial urgente: repor a senha do domínio, e fazer o ciclo cortina ("em atualização") ↔ senha funcionar de verdade nas rodadas.

**Achado 1 — a guarda do job `repor_dominio_manual` (criado mais cedo hoje) nunca isolou o disparo urgente da rodada semanal inteira.** `if: inputs.apenas_repor_dominio == true` compara o input contra o literal booleano `true`; inputs de `workflow_dispatch` frequentemente chegam como string, e a comparação string-contra-booleano do motor de expressões do GitHub Actions nunca bate (confirmado contra relato de terceiros e um caso idêntico documentado no próprio GitHub Actions runner). Evidência real: o run #87 (dispatch com `apenas_repor_dominio`) disparou os DOIS jobs — o `repor_dominio_manual` E a rodada `atualizar` inteira — quando só o primeiro deveria rodar. Corrigido: `if: inputs.apenas_repor_dominio` (contexto de verdade direto, sem comparação — padrão documentado do próprio GitHub Actions).

**Achado 2 — o portão `testar_reposicao_dominio.py` dava falso positivo depois do achado 1 ser corrigido no código, mas antes de o próprio portão ser ajustado.** Ele busca a primeira ocorrência de "Repor o site completo no domínio" no ARQUIVO INTEIRO — e o novo job `repor_dominio_manual` (criado mais cedo hoje, antes do job `atualizar:` no arquivo) tem um passo com o mesmo nome. A ordem DENTRO do job semanal real sempre esteve correta (cortina antes, reposição depois, com espera de 120s) — o portão só não sabia disso porque comparava contra a ocorrência errada. Corrigido: a busca agora é restrita ao corpo do job `atualizar:`.

**O que isso não explica sozinho.** O run #87, mesmo com o defeito da guarda, teve o passo de reposição (dentro do job `atualizar`, `if: always()`) e o job `repor_dominio_manual` bem-sucedidos — os dois deveriam ter deixado o domínio em modo senha. Não tenho como verificar o estado ao vivo do domínio a partir deste ambiente (fora da lista de acesso da rede) — pedido à editoria: confirmar em janela anônima depois deste PR.

**Ação imediata.** Cancelado o run #88 (rodando com o código com o defeito da guarda, potencialmente disparando a rodada semanal inteira por engano) e redisparado `apenas_repor_dominio=true` assim que este PR mesclar, agora isolado corretamente ao job rápido.

**Teste.** `scripts/testar_reposicao_dominio.py` roda verde. `scripts/validar_workflows.py` confirma YAML válido.

## §132 · Revisão da fila de pistas: bug real de deduplicação achado e corrigido em dois coletores; fila real cai de 113 para 60 pistas únicas · 21/09/2026

Classe **correção de bug + limpeza de dado**. Nenhuma pista foi promovida a registro — promoção continua exclusivamente humana, por desenho do sistema (`monitorar_imprensa_regional.py`: "nada entra sem ser documento oficial", três camadas independentes). Esta seção corrige o pipeline que ALIMENTA a fila, não decide o que está nela.

**Origem.** Pedido direto de revisar a fila de pistas e corrigir o que fosse necessário.

**Achado.** `coletar_diarios_municipais.py` anexava pista com `pistas["pistas"].append(...)` sem nenhuma deduplicação — diferente de `atos_resposta.json`, que já tinha proteção (`vistos`) desde sempre. Toda rodada que tocasse uma data já coberta por uma rodada anterior duplicava a mesma menção na fila. Verificado por varredura sistemática da fila real: **53 de 113 pistas eram duplicatas exatas** (mesmo ibge/município + url + trecho) — quase metade.

**Achado mais sério dentro do achado:** três cópias da mesma pista de Ouro Branco/AL (decreto 021/2026). Duas já tinham sido revisadas e aplicadas por Patricia em 10/09/2026 (`julgamento_humano` preenchido). A terceira cópia foi **registrada em 12/09 — dois dias DEPOIS da revisão** — e ficaria na fila parecendo pendente, quando o fato já tinha sido julgado. Isso teria custado tempo de revisão real em cima de uma decisão já tomada.

**Correção no código (fonte do bug).** `coletar_diarios_municipais.py`: `vistos_pistas` — mesmo padrão já usado para `atos_resposta.json` — checa `(ibge, url, trecho)` antes de anexar. `coletar_diarios_consorciados.py` (§129/§130): tinha o mesmo bug, ainda não manifestado porque o canal está bloqueado — corrigido preventivamente antes de entrar em produção. Confirmado que os OUTROS dois produtores de pista (`monitorar_imprensa_regional.py`, `monitorar_imprensa_saude.py`) já tinham dedup correta desde a origem (`vistos = {p["hash"] for p in fila["pistas"]}`) — o bug era isolado aos dois coletores de diário.

**Correção no dado.** Deduplicação real da fila: para cada grupo de duplicatas, mantida a entrada com `julgamento_humano` preenchido quando existir (nunca a mais recente por padrão — a revisão humana tem prioridade sobre a data de registro); nos 52 grupos restantes (sem revisão em nenhuma cópia), mantida a mais antiga. Verificado programaticamente que nenhuma remoção descartou um `julgamento_humano` que a entrada mantida não tivesse — comparação campo a campo antes de aplicar. **113 → 60 pistas.**

**O que NÃO foi tocado, por desenho.** As 12 entradas `rebaixamento C10` (correção de 02/09/2026: registro apoiado só em imprensa, sem documento primário, rebaixado a pista) — estado correto, não é bug. 6 pistas sem `municipio` (nível estadual, `categoria_candidata` começando com `estadual_`) — estrutura esperada. 5 pistas `rebaixamento C10` sem `url` — natureza da categoria (documento primário ainda não localizado). Nenhuma pista foi promovida, nenhum `julgamento_humano` foi criado ou alterado.

**Teste.** Dois testes de regressão novos, ambos rodando o fluxo real (não uma simulação da lógica) com rede/arquivos mockados: `coletar_diarios_municipais.py` (`t9`) roda `coletar_lote` duas vezes sobre o mesmo achado, confirma 1 pista nas duas rodadas; `coletar_diarios_consorciados.py` (`t15`) mesmo padrão para `coletar()`. Ambos hermético — verificado que `data/log_buscas.json` e outros arquivos reais não são tocados pelo autoteste. `docs/MANIFEST_SHA256.txt` regenerado.

## §131 · Corrupção real de dados achada e corrigida rodando a coleta MUNIC pela primeira vez; camada declarada nacional populada (5.570 municípios); simulação real do índice · 21/09/2026

Classe **correção de bug + dado real coletado**. Não altera `data/indice.json` (a camada declarada segue travada até 26/10/2026, §3.9) — resultado verificado por `--check` reproduzindo a mesma média 43,6 de antes.

**Origem.** Pedido direto: "existe um sistema de coleta saudável, que esgota as possibilidades?" A resposta é não (inventário completo abaixo, sem invenção). Pedido de teste real hoje: rodar a coleta MUNIC (§128, nunca executada contra a rede desde a correção do parser) e ver se o índice se modifica.

**Inventário do que existe de fato, camada por camada do protocolo (não suposto — cada linha verificada nesta sessão):**
- Camada 1 (bases estruturadas): S2iD/DOU funciona. MUNIC — corrigida aqui. ICM/SEDEC — nunca conectada, URL segue `null`.
- Camada 2 (diários): DOE funciona. Querido Diário funciona, mas alcança 351 de 5.571 municípios (6,3%) com diário indexado. Diários consorciados (SIGPub, §129-§130): construído, testado, bloqueado por `requestStorageAccess`.
- Camada 3 (sites de prefeitura, roteiro fixo): não existe nenhum coletor.
- Camada 4 (busca web aberta): não existe coletor automatizado.
- Camada 5 (LAI): `gerar_lai.py` só gera o texto do pedido; envio e resposta são manuais.
- Camada 6 (imprensa): `monitorar_imprensa_regional.py` e `monitorar_imprensa_saude.py` existem e rodam toda semana via `atualizar.yml` — funcionando de verdade.

**Achado adicional, fora do escopo da pergunta original mas com impacto direto no teste pedido:** a fila de pistas (`pistas_imprensa.json`) tinha 113 pistas esperando revisão, zero promovidas — o gargalo do sistema hoje não é achar pistas, é revisá-las.

**Bug 1 — `gravar()` não era atômica** (`coletores_base.py`). Escrevia direto no arquivo final; qualquer interrupção no meio (timeout, Action cancelada) deixava JSON truncado e inválido. Reproduzido de verdade: rodar `coletar_declarado_nacional.py` sob `timeout 200` corrompeu `data/fontes_consultadas.json` (368.019 → 166.961 linhas, `JSONDecodeError`). Corrigido: escreve em arquivo temporário no mesmo diretório e substitui via `os.replace()` — atômico em POSIX, o arquivo final é sempre a versão antiga completa ou a nova completa, nunca uma mistura truncada. Afeta todo coletor do projeto (função compartilhada), risco real dado que rodadas longas (35-90 min documentadas) e cancelamentos de Action aconteceram várias vezes nesta mesma sessão.

**Bug 2 — causa raiz da interrupção que expôs o Bug 1** (`coletar_declarado_nacional.py`). `marcar_fato_municipal()` faz uma leitura + escrita completa de `fontes_consultadas.json` a cada chamada — correto para `coletar_doe.py`/`coletar_s2id.py` (dezenas de municípios com decreto), mas o coletor MUNIC chama isso até 5.570 vezes na mesma rodada. Corrigido com `marcar_fato_municipal_em_memoria()`: uma leitura antes do loop, atualização em memória, uma escrita no final — mesmo resultado, 5.570× menos I/O. Rodada completa: **de indeterminado (matava por timeout) para 8 segundos.**

**Resultado real da coleta, rodada até o fim pela primeira vez:** MUNIC/IBGE 2020 — 5.570 municípios casados com a referência IBGE. `Mgrd184` (plano de contingência geral): 1.407 sim / 4.054 não / 109 NA. ICM/SEDEC: lacuna declarada (URL segue não confirmada — pendência editorial, não bug).

**Simulação real do efeito no índice** (`recalcular_mare.py --simular-declarado-nacional`, gravada em `data/simulacao_declarado_nacional.json`): média nacional **43,6 → 45,1** (+1,5). UFs com maior variação: DF +16,6 (1 município, alto peso individual), PE +2,7 (69 municípios), RJ +2,6 (73 municípios), AM +2,4 (25 municípios). 4 de 27 UFs sem nenhuma mudança. MG é quem mais contribui em volume: 204 municípios, +1,3.

**Derivados regenerados.** `data/fontes_consultadas.json` ganhou `plano_declarado_munic` para 5.461 municípios. `recalcular_mare.py --write` regenerou `verificacao_municipal.json` a partir disso (nível de verificação, não a nota — nota pública confirmada inalterada em 43,6 por `--check` logo depois). `docs/MANIFEST_SHA256.txt` regenerado.

**Teste.** `coletar_declarado_nacional.py --autoteste`: 6 casos, 1 novo (`marcar_fato_municipal_em_memoria` preserva registro existente e cria novo corretamente). Suíte completa verde: consistência, evidências, estrutura, legendas, MARÉ reproduzido.

## §130 · Diários consorciados: navegador real (Playwright/Chromium) implementado e testado contra produção — bloqueio persiste, causa mais específica agora documentada · 21/09/2026

Classe **investigação + código, ainda sem ativação em produção**. Continuação direta do §129, a pedido explícito de "desbloquear o que for preciso" (20-21/09/2026).

**O que foi pedido e o que foi entregue.** §129 identificou que o token do calendário SIGPub é preenchido por JavaScript e ficou bloqueado ali. Pedido explícito de prosseguir: implementar o navegador headless. Feito — `scripts/obter_token_sigpub.js` abre a página num Chromium real via Playwright (`package.json` já tinha `playwright` como devDependency, usado pelos portões visuais §14.3/§18 — não é dependência nova) e `obter_token_via_navegador()` em `coletar_diarios_consorciados.py` chama esse script, injeta os cookies da sessão do navegador no cookiejar HTTP e segue o resto do fluxo (POST do calendário, download do PDF) sem precisar de navegador de novo. `coletar_fonte()` tenta o caminho HTTP simples primeiro — mais barato — e só escala para o navegador quando o HTTP devolve o placeholder conhecido.

**Achado real, testado contra produção duas vezes (não suposto):** mesmo com Chromium de verdade, o token continua vindo como placeholder. Console do navegador mostra um único erro: `requestStorageAccess: Permission denied` — API que exige ativação transitória de usuário (gesto real), que automação headless não tem por padrão. Nenhuma requisição de rede relacionada a token/csrf apareceu durante o carregamento — o mecanismo não busca de um endpoint, é calculado (ou bloqueado) no cliente. Testado clique real via protocolo do Chrome (`page.mouse.click`, que o Chromium trata como confiável, diferente de `element.click()` via JS) logo após a navegação — não resolveu; o controller provavelmente já tenta e falha durante o carregamento inicial, antes do script recuperar controle para clicar.

**Por que parei aqui.** Resolver de fato exigiria (a) a flag exata do Chromium que libera `requestStorageAccess` em automação — não inventei um nome sem verificar a documentação real; ou (b) interceptar via protocolo do Chrome antes da navegação terminar, uma camada de engenharia mais profunda que o normal do Playwright. Dado o pedido de terminar a rotina, não abri mais essa frente sem verificação.

**O que fica pronto, mesmo sem resolver o bloqueio:** a ponte com o navegador existe e funciona mecanicamente (autoteste `t13` prova isso com mock — token e cookies do navegador chegam corretamente no fluxo HTTP); a política de dois níveis (HTTP barato primeiro) está certa e testada (`t14`); os diagnósticos por fonte agora incluem tentativas, tempo, requisições relevantes e console completo — quem retomar isso não repete a investigação do zero. O motor de PDF → texto → atribuição de município (§129) continua intacto e testado.

**Teste.** Autoteste hermético, 14 casos (3 novos desde §129: `t12` bloqueio total, `t13` navegador sucede e injeta cookies corretamente, `t14` caminho barato pula o navegador quando desnecessário). `docs/MANIFEST_SHA256.txt` regenerado. `diagnostico_sinais.yml` sem mudança líquida — os steps de teste desta investigação foram usados só em disparos manuais do branch de trabalho, nunca mesclados ao pipeline semanal.

## §129 · Diários consorciados (SIGPub/associações estaduais): fonte de alto potencial mapeada, motor construído e testado, coleta automatizada BLOQUEADA por token JS · 20/09/2026

Classe **investigação + código, sem ativação em produção**. Não entra em `portoes.yml` nem `atualizar.yml` — não produz dado nenhum hoje, só lacunas declaradas de bloqueio.

**Origem.** Pedido editorial de aprofundar a busca por planos de contingência municipais, com ceticismo justificado sobre a fração pequena de municípios com plano encontrado (153 de 5.571 até aqui). Investigação, não suposição: por que a cobertura do Querido Diário é tão desigual por UF (AL 94,1% vs. MG/PI/SC/GO/AC/MT entre 0% e 2,5%)?

**Achado 1 — causa real da desigualdade, verificada no código-fonte aberto do QD** (`okfn-brasil/querido-diario`): existe uma plataforma nacional, SIGPub (`diariomunicipal.com.br`, Vox Tecnologia), usada por associações/federações municipais de pelo menos MG, CE, PR, RS, RN, GO e BA (confirmado por navegação real, não suposto para os demais estados). O QD só tem UM raspador integrado a essa plataforma em todo o país — Alagoas — e é justamente AL quem lidera a cobertura. Não é ausência de plano; é lacuna de raspagem.

**Achado 2 — evidência de planos reais não capturados.** Busca aberta trouxe, só de setembro/2026, cinco municípios com atividade documentada de plano de contingência para El Niño (Belo Horizonte/MG, Vila Velha/ES, Palotina/PR, Cabo Frio/RJ, Erechim/RS) — nenhum necessariamente no banco ainda.

**Construído.** `coletar_diarios_consorciados.py`: reproduz o mecanismo real do SIGPub (widget de calendário → JSON → PDF cobrindo todos os municípios da associação naquela data), copiado do próprio raspador-base do QD (`gazette/spiders/base/sigpub.py`) — a "Busca Avançada" por palavra-chave tem ReCaptcha (nota do próprio QD), não é caminho viável. Extrai texto do PDF (pdfplumber), localiza decreto/plano, atribui por proximidade ao cabeçalho de entidade mais próximo ("PREFEITURA DE X", "MUNICÍPIO DE X") contra a referência IBGE da UF. Nunca classifica sozinho: toda saída é pista (nível `nao_verificado`), nunca registro; quando nenhum cabeçalho é localizado, a pista fica em nível UF em vez de descartada. Só entram os 7 estados com slug **verificado por navegação real** (MG, GO×2, BA×2, CE, PR, RS, RN) — nenhum slug foi suposto para os demais.

**Achado 3 — bloqueio real, verificado duas vezes contra produção.** O token do widget de calendário (`id="calendar__token"`) é preenchido por JavaScript no navegador (`data-controller="csrf-protection"`, um controller Stimulus). O HTML servido traz só um placeholder estático — a string literal `"csrf-token"` — sem `<meta name="csrf-token">` nem outra fonte estática de onde copiar o valor real. Verificado byte a byte contra o HTML real de produção (amm-mg), com sessão de cookies persistente (afastando a hipótese de token inválido por falta de sessão) e checagem de todos os 11 arquivos JS referenciados pela página em busca de um mini-endpoint alternativo — nenhum encontrado. Todo POST feito com o placeholder volta `{"error":"Ocorreu um erro inesperado!"}`.

**Decisão** (22/09/2026, autonomia decisória — pedido explícito de terminar a rotina sem abrir mais uma dependência nova a depurar): NÃO implementar navegador headless (Selenium/Playwright) agora — é uma dependência de infraestrutura nova e desproporcional ao pedido de fechar a rotina. `coletar_fonte()` detecta o placeholder e para ANTES de gastar qualquer requisição de calendário (testado: `t12`, mocka a rede e confirma zero POSTs). O motor de PDF → texto → atribuição de município fica pronto e testado (13 casos, incluindo ponta a ponta com PDF sintético) para quando uma fonte de token funcional existir — desbloquear exige só trocar a aquisição do token, não reescrever o resto.

**Teste.** Autoteste hermético — achado e corrigido nesta sessão: a primeira versão do teste de bloqueio chamava `coletar_fonte()` de verdade, que gravava uma lacuna real em `data/log_buscas.json` a cada rodada de `--autoteste`; corrigido mockando `registrar_lacuna` também, não só a rede. `docs/MANIFEST_SHA256.txt` regenerado.

## §128 · MUNIC/IBGE: coletor lia CSV inexistente e coluna errada; edição e campo reais confirmados por download · 20/09/2026

Classe **código**. Não altera pesos, créditos, componentes ou régua; a camada declarada nacional continua sem entrar na nota (vigência 26/10/2026, §3.9).

**O que a sonda §126 deixou pendente.** `coletar_declarado_nacional.py` chamava `parse_munic_csv()` (`csv.DictReader`) contra uma URL nunca preenchida (`url: null`), e o nome de coluna registrado, `MGRD_PlanoContingencia`, nunca foi conferido contra arquivo — só suposto. A sonda §126 mostrou que a MUNIC distribui `.xlsx`, não CSV, mas rodava num contêiner sem acesso a `ftp.ibge.gov.br` (fora da allowlist do sandbox de edição), então não conseguiu ler o cabeçalho real na sessão em que foi escrita.

**Descoberta desta sessão: os domínios do IBGE (`ftp.ibge.gov.br`, `servicodados.ibge.gov.br`, `www.ibge.gov.br`) respondem diretamente no sandbox de edição** — testado e confirmado (HTTP 200 nos três). Os handouts anteriores registravam bloqueio; não procede mais (ou nunca procedeu para este conjunto de domínios). Isso elimina a necessidade de disparar a Action para diagnósticos deste tipo.

**O que o download real mostrou.**
1. A MUNIC roda módulos temáticos **rotativos**: cada edição cobre um conjunto diferente de temas. `Gestão de riscos e de desastres` só apareceu, entre 2017–2024, nas edições **2017 e 2020** — não em 2019, 2021, 2023 ou 2024. As "colunas de risco" que a sonda §126 via nessas quatro edições eram falso-positivo: vinham das abas `Recursos humanos`/`Recursos para gestão`/`Gestão migratória` (a função de leitura só verificava as 3 primeiras abas do arquivo; a aba de risco, quando existe, normalmente vem depois).
2. A edição mais recente com o bloco é, portanto, **2020** — não por escolha editorial, mas porque é a única disponível no recorte temporal considerado.
3. Dentro da aba `Gestão de riscos`, o dicionário de variáveis (aba `Dicionário` do próprio arquivo) mostra que a coluna do plano de contingência é **`Mgrd184`** ("Plano de Contingência", item 6.6 Gerenciamento de riscos) — não `MGRD_PlanoContingencia`, que nunca existiu. Existe também `Mgrd05` ("possui Plano de Contingência e/ou Preservação para a seca", item 6.1), campo distinto e mais específico ao padrão de impacto do El Niño no Nordeste.

**Correção.** `parse_munic_csv()` → `parse_munic_xlsx()` (openpyxl, aba nomeada explicitamente, não posicional). `data/fontes_declarado.json` ganha a URL real, `edicao: 2020`, `aba: "Gestão de riscos"` e as duas colunas confirmadas. O coletor grava `munic_plano_contingencia` (de `Mgrd184`, campo usado na simulação de nota) e `munic_plano_contingencia_seca` (de `Mgrd05`, registrado em paralelo, sem entrar na simulação — usar ou não como sinal específico de seca é decisão da editoria).

**Teste.** Autoteste com fixture `.xlsx` (não mais CSV): parser confirma cabeçalho por nome de coluna, ignora código IBGE inválido, dois casos negativos novos (aba inexistente → vazio, sem exceção; coluna do plano ausente → casa por IBGE sem o campo). Rodado também contra o arquivo `.xlsx` real da MUNIC 2020: **5.570 de 5.571 municípios casados** com a referência IBGE; `Mgrd184`: 1.407 "sim" / 4.054 "não" / 109 "NA"; `Mgrd05`: 1.230 "sim" / 3.814 "não" — distribuição plausível, sem outliers. `docs/MANIFEST_SHA256.txt` regenerado.

## §127 · Autotestes das sondas de ENSO (IRI) e MUNIC (IBGE) ligados ao portão de regressão · 20/09/2026

Classe **código**. Não altera pesos, créditos, componentes ou régua.

Os dois autotestes existentes — `sondar_enso_probabilidades.py --autoteste` (§125) e
`sondar_munic_ibge.py --autoteste` (§126) — passam a rodar no bloco **Portões de regressão
(testes negativos dedicados)** de `portoes.yml`. Não foram incluídos nos PRs originais para
evitar conflito com o §123, que criou o bloco. Ambos verdes na `main` atual.

`pip install openpyxl==3.1.5 --break-system-packages -q` foi adicionado antes da sonda
MUNIC: o workflow `portoes.yml` não instala `requirements.txt` (usa só a biblioteca padrão
para todo o resto), mas a sonda MUNIC chama `openpyxl` no autoteste quando a biblioteca está
presente e o pula (com aviso) se não estiver — o portão precisa da instalação explícita para
que o caso de xlsx seja efetivamente testado e não silenciosamente omitido.
## §126 · Sonda da MUNIC/IBGE: qual edição traz o bloco de riscos e o nome real das colunas · 22/09/2026

Classe **diagnóstico** — não toca dados, pesos, créditos, componentes ou régua. Cria
`scripts/sondar_munic_ibge.py` e adiciona a sonda ao workflow `diagnostico_sinais.yml`
(autorização permanente de 20/09/2026).

**Por que esta sonda existe.** `data/declarado_nacional.json` está zerado
(`"municipios": {}`) desde 02/09/2026, porque `data/fontes_declarado.json` tem `url: null`
e `status: "a_verificar"` para MUNIC e ICM. Esse canal entrará na nota em 26/10/2026 e é o
único que consultaria os 5.570 municípios de forma direta — a varredura pelo Querido Diário
cobre ~9,5% do país, por limite de acervo. Os nomes de coluna em `fontes_declarado.json`
(`MGRD_PlanoContingencia`, `CodMun`) eram suposições, nunca conferidas contra o arquivo real.

**O que a sonda faz.** Lista as edições disponíveis no FTP-HTTP do IBGE, identifica a
subpasta da base (`Base_de_Dados` ou `Tabelas_de_Resultados`), baixa o arquivo de dados
(`.xlsx` ou `.csv`) e classifica as colunas em: chave do município, plano de contingência
e contexto de risco/desastre. Imprime quais edições têm o bloco — e com quais nomes reais —
para que a escolha da edição seja decisão editorial com o arquivo à vista.

**Por que a edição mais recente pode não ser a certa.** A MUNIC 2024 (21ª edição) anuncia
oito temas; gestão de riscos e desastres **não está entre eles**. O bloco existe na 2017 e
na 2020. A sonda confirma isso, em vez de supor. Não foi decidido aqui qual edição usar —
essa decisão muda o ano de referência do que o site afirma e é registrada como pendência.

**O que a 1ª execução real revelou.** Dois defeitos de parsing, corrigidos nos testes
negativos do autoteste: (1) suplementos com ano no nome (e.g., `Saneamento_Basico_2017/`)
eram tomados por edições da pesquisa; (2) a sonda não descia em `Base_de_Dados`, só em
`Tabelas_de_Resultados`. Ambos foram observados no diretório real e tornaram os testes
negativos. Adicionalmente: a base é `.xlsx`, não CSV — suporte adicionado com `openpyxl`,
incluindo lógica de pulo de linhas de título antes do cabeçalho real (formato padrão do IBGE).

**Autoteste.** Roda sem rede; cobre listagem de diretório, extração de cabeçalho (CSV e xlsx),
classificação de colunas (incluindo variações de grafia e o caso negativo da MUNIC 2024 que
não tem o bloco), e os dois defeitos de parsing acima. `docs/MANIFEST_SHA256.txt` regenerado.

## §125 · Por que a fonte do IRI está em branco: o arquivo saiu do ar, a fonte não · 22/09/2026

**Diagnóstico.** `iri_plume` é a única das dez fontes de sinais em
`aguardando_primeira_coleta`. A causa não era rede: o relatório
`2026-09-15_153058_enso_probabilidades.txt` (sonda rodada na Action, com rede aberta)
mostra **HTTP 404** nas três variantes do arquivo tabular
`iri.columbia.edu/~forecast/ensofcst/Data/ensofcst_*`, enquanto as páginas públicas do IRI
respondem 200. A fonte segue publicando o Quick Look mensal; o que saiu do ar foi o arquivo
de dados.

**O que NÃO mudou.** O endpoint do coletor continua o mesmo e a fonte continua aparecendo no
site como lacuna declarada. Trocar o endpoint exigiria escrever um parser de HTML sem ter o
HTML real em mãos — `iri.columbia.edu` está fora da allowlist do contêiner e não há amostra
preservada em `evidencias/`. Afirmar que um parser não testado funciona é exatamente o erro
que a sessão de 21/09 registrou. Nenhum peso, crédito, componente ou régua foi tocado;
nenhum dado foi imputado.

**O que mudou.** `scripts/sondar_enso_probabilidades.py` passa a procurar a **tabela** de
probabilidades, e não o percentual solto. A sonda antiga só casava `El Niño … N%`, formato
que o Quick Look não usa: por isso reportava `percentuais vistos: []` numa página que
responde 200 — resultado indistinguível de uma página sem os dados. Agora ela limpa a
marcação, procura linhas `RÓTULO nina neutro nino` (o mesmo formato que `parse_plume_iri()`
já lê) e imprime o trecho em volta do primeiro acerto. A próxima execução na Action dirá,
com HTML real, se a tabela está na página e em que forma — e só então o endpoint pode ser
corrigido com parser testado contra evidência.

**Guardas, cada uma com teste negativo verificado.** `--autoteste` roda sem rede e cobre:
tag vira espaço e não string vazia (sem isso `<td>MJJ</td><td>5</td>` colaria em `MJJ5`); só
rótulo de trimestre real conta (`PDF 10 20 70` é ignorado); os três números têm de somar
perto de 100; e cada um tem de estar em 0–100. As quatro foram revertidas uma a uma e o
autoteste ficou **vermelho** em cada reversão.

**Código morto removido.** A primeira versão tinha dois caminhos redundantes inserindo espaço
entre células — por isso quebrar qualquer um isoladamente deixava o teste verde, embora o
defeito fosse real. Sobrou um caminho, com o caso negativo que de fato o cobre.

## §124 · Querido Diário mudou de domínio; e o relatório da rodada escondia as falhas de coleta · 21/09/2026

Classe **código**. Nenhuma nota muda; nenhum peso, crédito, componente ou régua tocado; nenhum dado de `data/*.json` editado. Média nacional segue 43,6.

**1. O Querido Diário migrou de endereço.** `coletar_diarios_municipais.py` chamava `queridodiario.ok.org.br/api/gazettes`. Esse host **ainda resolve, mas não serve mais a API**: responde `302` para `api.queridodiario.org.br` a cada chamada — verificado nesta data e coerente com a configuração de produção publicada pelo próprio projeto. A coleta não estava quebrada, porque `urllib` segue redirecionamento por padrão; mas cada uma das 5.571 consultas da varredura pagava uma viagem extra, e a varredura inteira dependia de um redirect que pode ser desligado sem aviso.

**Correção.** O coletor passa a chamar o domínio de produção direto, com o antigo como **reserva**: falha de rede ou 5xx no domínio novo faz a consulta ser repetida no antigo antes de virar lacuna. 4xx **não** aciona a reserva — 404 significa consulta errada, não host caído; repetir só dobraria a carga sobre uma API pública que pede moderação (referência de 60 requisições/minuto) e mascararia o defeito. Teste negativo cobre os três caminhos.

**2. O relatório da rodada tornava invisível qualquer falha de coleta.** Dois defeitos somados, e a evidência é concreta: a fonte `iri_plume` (probabilidades ENSO do IRI/Columbia) está em `aguardando_primeira_coleta` **desde sempre** e ninguém viu, porque:

- **Buffer.** `atualizar.py` imprimia `=== etapa ===` sem `flush`. Fora de um terminal o stdout do Python é bufferizado em blocos, mas os subprocessos escrevem direto no descritor — os cabeçalhos saíam todos juntos no fim da rodada, separados da saída que cada etapa produziu. No relatório de 20/09, as 20 etapas de coleta aparecem enfileiradas e **vazias**, embora `coletar_sinais_risco.py` imprima uma linha obrigatória logo na entrada.
- **Truncamento.** O relatório guardava apenas as últimas 220 linhas do log, que são invariavelmente as dos portões finais. Todo `[aviso]` emitido durante a coleta, no começo da rodada, caía fora do arquivo.

O coletor de sinais **já registrava** a falha corretamente (`[aviso] <fonte>: rede indisponível — registro anterior mantido`) e nunca derrubou o pipeline, como manda o desenho. O defeito era só de observabilidade — e bastou para uma fonte ficar meses sem coletar sem ninguém notar.

**Correção.** `flush=True` nos cabeçalhos e um `sys.stdout.flush()` após cada subprocesso, religando cada etapa à sua saída; etapa não obrigatória que falha passa a imprimir um `[aviso]` com o código de saída, em vez de seguir em silêncio. No relatório, um bloco novo — **avisos e erros da rodada (todos)** — vem **antes** do trecho truncado e varre o log inteiro por `[aviso]`, `[erro]`, `Traceback` e recusas de resposta, mais a contagem de etapas executadas.

**O que isto não resolve.** Por que o endpoint do IRI falha continua **não diagnosticado**: `iri.columbia.edu` está fora da allowlist do contêiner, então não foi possível testar daqui. A página pública da fonte está ativa. A próxima rodada dirá, agora que o aviso chega ao relatório. Nenhum texto público mudou: a fonte já aparece como lacuna declarada, que é o comportamento correto.

Edição de `.github/workflows/atualizar.yml` sob a autorização permanente registrada pela editoria em 20/09/2026. `validar_workflows.py` verde.

## §123 · Piauí no fim da fila da varredura por omissão na lista de prioridade; cinco portões escritos que não bloqueavam nada · 21/09/2026

Dois achados da rotina, ambos de classe **código**. Nenhuma nota muda; nenhum peso, crédito, componente ou régua tocado; nenhum dado de `data/*.json` editado.

**1. A fila da varredura tinha uma UF em posição acidental.** `data/cadastro_prioritarios.json` traz duas estruturas: `por_uf`, com os 27 estados e o percentual de municípios no Cadastro Nacional de Municípios Suscetíveis, e `ordem_prioridade_uf_por_percentual`, a lista curada que decide em que UF a varredura de diários entra primeiro. A lista tem 26 entradas: **PI está em `por_uf` com pct 21,0 e ficou fora da ordem**. `ordem_prioridade()` resolvia a ausência com um rank fixo (99), o que punha o Piauí atrás de todos os 26 estados nomeados — inclusive de GO (10,2%) e TO (12,9%), ambos com percentual menor. Efeito medido: dos 3.180 municípios já consultados na varredura (57% do país), **nenhum dos 224 municípios do Piauí**. Não houve perda de dado — a varredura é integral e chegará lá —, mas a posição era consequência de implementação, não de método, e não aparecia em lugar nenhum: a Action rodava verde.

**Correção.** UFs presentes em `por_uf` e ausentes da lista curada passam a entrar **logo após** as nomeadas, entre si por percentual decrescente do próprio cadastro. A lista curada não é reordenada: nenhuma das 26 UFs que ela nomeia muda de posição. A posição definitiva do Piauí dentro da lista curada **não** foi decidida aqui — a lista vigente não é monotônica em percentual (DF 100% aparece em 6º, MT 28,4% antes de MS 41,8%), logo o critério é misto e a inserção é decisão editorial, registrada como pendência no relatório do dia.

**Portão.** `scripts/testar_ordem_prioridade_ufs.py` exige que a fila seja **total e determinística**: as 27 UFs do cadastro presentes, cada uma num bloco contíguo (bloco partido denuncia rank empatado entre estados), duas execuções sobre o mesmo dado idênticas, e uma UF omitida da lista curada posicionada pelo percentual. O teste negativo usa duas ausentes em ordem de inserção **inversa** ao percentual — com o rank fixo antigo o empate se resolvia pela ordem de iteração do dicionário e passaria despercebido. Conferido que o portão fica vermelho sem a correção e verde com ela. O autoteste de `coletar_diarios_municipais.py` ganhou o mesmo caso (9/9).

**2. Cinco portões existiam sem estar ligados a nenhum workflow.** `testar_cadencia_publicacao.py` (§117), `testar_contador_varredura.py` (§121), `testar_nivel_log_buscas.py`, `testar_reposicao_dominio.py` (§120) e o portão novo acima estavam escritos e verdes, mas fora de `portoes.yml` — nenhum deles bloqueava pull request. O §117 descrevia o de cadência como "portão novo" que "exige que o código, o cron do workflow e o texto público nomeiem o mesmo dia"; ele nunca foi executado automaticamente. Os cinco entram agora num passo próprio, **Portões de regressão (testes negativos dedicados)**. Os cinco rodam verdes na `main` atual — a ligação não muda o veredito de nenhum PR existente, só passa a travar a regressão que cada um descreve.

Edição de `.github/workflows/portoes.yml` feita sob a autorização permanente registrada pela editoria em 20/09/2026. `validar_workflows.py` verde.

## §122 · `--autoteste` de `coletar_financiamento.py` e `gerar_painel.py` sobrescrevia dados reais sem restaurar · 21/09/2026

Achado ao rodar a suíte completa de portões localmente (rotina diária, fora da Action — checkout descartável). Nenhuma alteração de método; nenhuma nota muda. Classe **código** (PROTOCOLO §3.2).

**Causa-raiz.** `coletar_financiamento.py --autoteste` chama `semear()`, que escreve os seis registros de exemplo direto em `data/financiamento/*.json` (registros reais da página `financiamento.html`); `gerar_painel.py --autoteste` chama `sortear()` e `fichas()`, que escrevem em `data/painel/lista.json` (a lista **imutável** do painel amostral publicado, E11), `fichas.json` e `agregados.json`. Nenhum dos dois restaurava os arquivos depois do teste. Na Action (`portoes.yml`), isso é inofensivo — cada execução usa um checkout novo, descartado ao final. Rodando localmente sobre o clone de trabalho (exatamente o que a rotina diária faz para validar a `main`), o efeito é apagar dado real. **`coletar_saude.py` já tinha o mesmo bug, corrigido em 03/09/2026** (comentário no próprio código: "autoteste NUNCA toca os dados reais"); esta correção aplica o mesmo padrão aos outros dois coletores que faltavam.

**Correção.** Em ambos, o teste que semeia dados agora faz backup dos arquivos reais antes (bytes, se existirem) e restaura no `finally`, tenha o teste passado ou não — mesmo padrão de `coletar_saude.py`. Cada arquivo ganhou um teste negativo novo que confere, ao final da suíte do próprio script, que o arquivo real ficou byte a byte igual ao que era antes de `--autoteste` rodar.

**Teste.** 7/7 testes em cada script; confirmado que `git status` não mostra nenhum arquivo de `data/` alterado após os dois `--autoteste`. `docs/MANIFEST_SHA256.txt` regenerado. Nenhum arquivo de `.github/workflows/` tocado.

## §121 · O contador da varredura media outra coisa: "não indexado" contado como "com menção" · 20/09/2026

Classe **código**; nenhuma nota muda; média nacional segue 43,6, reproduzida bit a bit. Nada do que o público vê estava errado — o defeito era interno, e é registrado aqui porque corrompia o instrumento usado para julgar a cobertura da varredura.

**O defeito.** `recalcular_mare.py` classificava como "sem menção" o município cujo resultado começasse com `"sem edições"`. `coletar_diarios_municipais.py` nunca gravou essa string. Os prefixos reais são `sem_cobertura_qd:`, `coberto_sem_mencao:` e `cobertura a confirmar`. Consequência: `sem_mencao` era sempre 0 e `com_mencao` sempre igualava `consultados` — 3.180, quando o número real de municípios com menção localizada era **153**. A suíte ficava verde: nada falhava, a conta apenas media outra coisa.

**Alcance.** O erro ficava em `data/verificacao_resumo.json`. A cortina do domínio publica apenas `consultados`/`total` ("3.180 municípios consultados nos diários oficiais (57%) — consultar não é verificar"), afirmação correta e já ressalvada; `com_mencao` nunca chegou ao público.

**Correção.** Classificação pelos quatro estados que o coletor de fato grava, agora publicados separadamente em `varredura_diarios`: `com_mencao` 153, `coberto_sem_mencao` 198, `sem_cobertura_qd` 2.824, `cobertura_indefinida` 5 — soma 3.180, igual a `consultados`. `indexados` (153 + 198 = 351) passa a existir como campo próprio.

**A distinção que não pode ser perdida.** `sem_mencao` passa a valer só para diário efetivamente lido, e nunca inclui os não indexados. Onde não há diário indexado não há o que ler: somar os dois faria o projeto afirmar ausência de plano onde existe apenas ausência de fonte — o que §4.1.2 proíbe e o que a linguagem-teto do projeto ("não localizamos até o corte", nunca "não existe") existe para impedir.

**Portão.** `scripts/testar_contador_varredura.py` rejeita a volta da string fantasma no código (ignorando comentários, que a citam de propósito), exige os quatro campos, exige que as classes somem `consultados`, e trava as duas assinaturas do defeito: `com_mencao == consultados` e `sem_mencao` absorvendo os não indexados. Três testes negativos.

**O que isto NÃO estabelece.** Os 2.824 "sem diário indexado" vêm do mesmo teste de cobertura cuja confiabilidade está em aberto (`data/cobertura_qd.json`, janela de 29/06/2026). É o que o repositório registra, não uma medição confirmada contra a API viva do Querido Diário — pendência aberta, ver handout.

## §120 · A rodada semanal derrubava o modo senha do domínio · 20/09/2026

Defeito estrutural, anterior às mudanças de hoje, encontrado porque o domínio passou sete horas servindo a cortina "Em atualização" no lugar do site completo. Classe **código**; nenhuma nota muda; nenhum dado de `data/*.json` tocado.

**Por que ninguém via.** O ramo `publico` carrega um workflow próprio, `publicar_dominio.yml`, que dispara **a cada push naquele ramo** e faz deploy de PRODUÇÃO. O passo final da rodada semanal empurra o contador da cortina para lá. Logo, toda rodada republicava a cortina por cima do site completo e derrubava o modo senha declarado em `data/publicacao.json` (`dominio: "senha"`, decisão da editoria de 14/09). A Action ficava verde do começo ao fim — do ponto de vista dela nada falhou; os dois workflows estão certos isoladamente, e o defeito só existe na interação entre eles. Desde 14/09 toda rodada repetia isso, e o domínio só voltava ao ar quando alguém republicava à mão.

**Correção.** Passo final em `atualizar.yml`: lê `data/publicacao.json` e, quando o modo for `senha`, republica a `main` no domínio com Basic-Auth (segredo `PREVIA_BASIC_AUTH`) e `noindex`. Vem depois do push da cortina e espera 120 s o deploy dela assentar — sem a espera, os dois deploys de produção correm e o vencedor é sorteio. Se um segredo faltar, avisa e sai sem publicar, em vez de deixar o domínio num estado indefinido. Em modo `cortina` não faz nada, que já é o estado correto.

**Efeito colateral desejado.** A cortina continua aparecendo durante a rodada, como a editoria pediu — o que muda é que ela deixa de ser o estado final.

**Portão.** `scripts/testar_reposicao_dominio.py` exige o passo de reposição, que ele consulte a declaração em vez de fixar o modo no workflow, que venha depois do push da cortina, que espere pelo menos 60 s, e que a credencial venha de segredo e nunca literal (o repositório é público). Três testes negativos.

**Nota sobre o acesso.** O login e a senha do domínio são o Basic-Auth do segredo `PREVIA_BASIC_AUTH` mais o véu de navegador em `assets/acesso.js` — nada a ver com os controles de acesso do Netlify (senha de visitante ou SSO de equipe), que permanecem como estavam: sem senha de visitante, SSO só em não-produção.

## §119 · Cadência semanal ajustada para domingo, 0h de Brasília · 20/09/2026

Decisão da editoria, no mesmo dia do §117. Substitui o sábado 22h40 por **domingo à 0h de Brasília** (cron `0 3 * * 0` = 03h UTC). Classe **código**; nenhuma nota muda; nenhum peso, crédito ou régua tocado.

**Por que é melhor que o sábado 22h40.** A rodada leva 75–105 min. Começando às 22h40 de sábado, terminava por volta de 00h05 de domingo — cruzava a virada do dia toda semana, o que exigiu o §118 para que a edição não fosse datada com o dia seguinte. Começando à 0h de domingo, ela termina por volta de 01h20 do **mesmo** domingo: a edição inteira, da coleta ao carimbo, acontece dentro de um único dia civil. A correção do §118 permanece — é a garantia estrutural de que nenhuma data do pipeline volte a vir de UTC — mas deixa de ser exercitada toda semana.

**Fuso.** Meia-noite de Brasília é 03h UTC do mesmo dia, então o campo de dia da semana do cron (0 = domingo) coincide com o domingo brasileiro. Sem a coincidência, valeria a regra do §117: o portão de cadência decide pelo dia em `America/Sao_Paulo`, nunca pelo do runner.

**Texto público e documentação** atualizados junto — `obrigado.html` (promessa a quem envia documento), `pesquisadores.html`, `METODOLOGIA.md`, `PROTOCOLO_ATUALIZACAO.md`, `GUIA_DO_EDITOR.md`, `README.md`, `INSTALACAO_E_AUDITORIA.md`, `DOCUMENTACAO_TECNICA.md`, `AUDITORIA_CODIGO.md`, `COMO_RODAR_E_PENDENCIAS.md`. O portão `testar_cadencia_publicacao.py` bloqueia se algum deles divergir.

## §118 · Data da edição no fuso da redação — a rodada de sábado carimbava domingo · 20/09/2026

Defeito introduzido pelo §117 e detectado na primeira rodada de sábado, antes de completar um ciclo. Classe **código**; nenhuma nota muda; nenhum peso, crédito ou régua tocado.

**O que acontecia.** A rodada semanal começa às 22h40 de sábado em Brasília, que é 01h40 de **domingo** em UTC, e leva 75–105 min — cruza a virada do dia toda semana. `atualizar.py` calculava a data da edição com `datetime.date.today()`, que no runner é UTC: a rodada de sábado 19/09 carimbou `atualizado_em: 20/09/2026`, um domingo. O site declara publicar aos sábados e dataria domingo em todas as semanas seguintes. O mesmo valor alimenta `corte` quando as transferências mudam.

**Correção.** A data da edição passa a vir de `hoje_editorial()`, fixada no início da rodada: a edição inteira leva a data do dia em que foi publicada, não a do minuto em que a última etapa terminou. O contador de lote da varredura intensiva (D1..D7) tinha o mesmo defeito — em UTC a rodada noturna adiantaria o lote em um dia — e foi corrigido junto.

**Portão.** `testar_cadencia_publicacao.py` passa a rejeitar qualquer `datetime.date.today()` fora de comentário em `atualizar.py`: no fuso do runner, toda data do pipeline erra o dia na janela noturna. Teste negativo cobre a regressão.

**Pendência de uma semana.** `data/meta.json` ficou com `atualizado_em: 20/09/2026` (domingo) da rodada já publicada. Não foi editado à mão — `data/*.json` é escrito só pelo pipeline. A rodada de sábado 26/09 grava a data correta.

## §117 · Cadência semanal passa de segunda-feira para sábado, 22h40 de Brasília · 20/09/2026

Decisão da editoria, tomada e autorizada em sessão de 20/09/2026 — incluindo autorização explícita e permanente para editar `.github/workflows/` quando o pedido exigir (a restrição anterior era de protocolo, não de escopo do token: o push com alteração de workflow passou de primeira). Nenhuma alteração de método; **nenhuma nota muda**; nenhum peso, crédito, componente ou régua tocado; congelamento do defeso (C6, Errata C25) intacto. Classe **código**.

**O que mudou.** A rodada completa semanal — a que recoleta todas as fontes, recalcula o MARÉ, regenera PDFs, selos, feeds e dados abertos, e publica — deixa de acontecer às segundas-feiras às 09h UTC e passa a acontecer aos **sábados, 22h40 de Brasília**. As execuções diárias (sinais de risco, derivado de saúde) continuam inalteradas.

**Armadilha de fuso, resolvida antes de publicar.** O runner do GitHub roda em UTC, e sábado 22h40 de Brasília é **domingo 01h40 em UTC**. O portão de cadência usava `datetime.date.today().weekday()`, que no runner é UTC: com `DIA_PUBLICACAO = 5` (sábado) a rodada teria caído na **sexta-feira à noite** para o leitor brasileiro. A cadência passa a ser medida em `America/Sao_Paulo` (`hoje_editorial()`), o fuso do leitor e do texto público, e o cron semanal é `40 1 * * 0` — domingo em UTC, sábado no Brasil.

**Guarda contra rodada duplicada.** O cron diário das 09h UTC também cai no dia de publicação (06h de Brasília). Sem guarda, o sábado teria duas rodadas completas de 75–105 min com 16 horas de intervalo e dois commits para a mesma edição. `ja_publicou_hoje()` compara `data/meta.json` com a data editorial e encerra a segunda. A cadência anterior já tinha a mesma duplicidade às segundas, contida só por `concurrency`; esta guarda a elimina de fato.

**Texto público alinhado.** `obrigado.html` prometia a quem envia documento que ele entraria no ar "normalmente na segunda-feira", e `pesquisadores.html` declarava a cadência do banco como segundas. Ambos passam a dizer sábado — o dia é compromisso declarado ao leitor, não detalhe interno. `METODOLOGIA.md` (cadência E4 e ficha/reverificação do §29), `PROTOCOLO_ATUALIZACAO.md`, `GUIA_DO_EDITOR.md`, `README.md`, `INSTALACAO_E_AUDITORIA.md`, `DOCUMENTACAO_TECNICA.md`, `AUDITORIA_CODIGO.md` e `COMO_RODAR_E_PENDENCIAS.md` atualizados. A série semanal permanece comparável: o intervalo entre observações continua de sete dias.

**Portão novo.** `scripts/testar_cadencia_publicacao.py` exige que o código, o cron do workflow e o texto público nomeiem o mesmo dia, e que a medição seja feita no fuso da redação. Quatro testes negativos (texto público divergente; literal no lugar da constante; cron em sábado UTC, que é sexta no Brasil; medição em UTC). O portão pegou um erro real de conversão de cron durante a própria implementação.

## §116 · Filtro de UF em `monitorar_imprensa_saude.py` — rejeita atribuição cruzada de RSS nacional · 20/09/2026

Bug detectado em 19/09 (§112) e corrigido nesta rotina. Nenhuma alteração de método; **nenhuma nota muda**; nenhum dado de `data/*.json` tocado. Classe **código** (PROTOCOLO §3.2).

**Causa-raiz.** O Google News RSS devolve resultado de cobertura nacional para queries por UF, e o coletor registrava todos os itens como pistas da UF-alvo sem verificar se a notícia mencionava de fato aquele estado. No lote de 19/09, 20 das 25 pistas coletadas não mencionavam a UF-alvo: "Secretaria de Saúde de Cuiabá divulga Plano de Contingência" ficou fichada como pista de AC, AP, CE, DF, MS, RO e SE. Aplicar qualquer uma creditaria a um estado um instrumento que é de outro (falsa atribuição, risco de distorção do índice de saúde no próximo ciclo em que a camada de saúde ganhar peso).

**Correção.** Nova função `_menciona_uf_alvo(titulo, url, uf)` filtra cada item do RSS antes do registro. Âncoras verificadas: nome do estado (com acento, evitando confundir a preposição "para" com o estado "Pará"), capital estadual, padrão `SES-{UF}` e domínio `.uf.gov.br`. A filtragem ocorre no loop principal, antes de chamar `registrar()`. Contador de `[FILTRADAS]` adicionado ao relatório de execução.

**Testes.** 13 casos adicionados ao `--self-test`: aceitam pistas que mencionam estado/capital/SES, rejeitam atribuições cruzadas (Cuiabá → AC, Bahia → CE, MS → SP), e verificam explicitamente que a preposição "para" (sem acento) não aciona o filtro do estado "Pará". Todos os 30 portões da suíte: verdes no ramo, incluindo `verificar_derivados.sh` (árvore limpa após commit) e `--idempotencia`. Nenhum arquivo de `.github/workflows/` tocado.

**Pistas existentes em `data/pistas_imprensa_saude.json`.** As 19 pistas de atribuição cruzada do lote de 19/09 permanecem na fila em `pendente_confirmacao_documento` — inofensivas (a trava absoluta impede aplicação sem documento oficial) e úteis para a triagem humana confirmar a eliminação. As 6 pistas de Bahia (4 com título correto, 2 cruzadas) aguardam busca manual do documento primário da SES-BA.

## §112 · Triagem das filas de descoberta automática, e um defeito no monitor de imprensa de saúde · 19/09/2026
Triagem das duas filas criadas pela rodada de 19/09. Nenhuma alteração de método; **nenhuma nota muda**; nenhum instrumento aplicado além do de MG (§111). Classe **conteúdo**.

**`pistas_descobertas.json` — 13 restantes, nenhuma aplicada.** Onze fora do escopo do índice (plano de comunicação institucional, POP de coleta de amostra, manual de sistema, tutorial de painel do fundo estadual, Plano Diretor de Regionalização revisão 2023, boletim de campanha, diligência administrativa, guia de vigilância de Covid-19 e influenza, demonstrativos orçamentários). As três intituladas "Plano Estadual de Contingência para Enfrentamento aos Vírus Respiratórios" foram **abertas e conferidas**: são de "Minas Gerais – 2025", sazonais recorrentes, não específicas do ciclo El Niño nem do ciclo corrente. Cada item carrega agora a razão da não aplicação.

**`pistas_imprensa_saude.json` — 25 pistas, nenhuma aplicada, e um defeito localizado.** Nenhuma das 25 é `fonte_provavel_oficial` (são veículos de imprensa e sites de prefeitura, não domínio oficial de secretaria estadual), então nenhuma passa no portão de fonte do projeto. Além disso, **20 das 25 não mencionam a UF-alvo**: a consulta é por UF, mas o feed RSS do Google News devolve resultado de alcance nacional e o coletor o atribui à UF consultada. "Secretaria de Saúde de Cuiabá divulga Plano de Contingência" está fichada como pista de AC, AP, CE, DF, MS, RO e SE. Aplicar qualquer uma creditaria a um estado um instrumento que é de outro — risco de falsa atribuição, registrado item a item. **A correção do coletor fica para decisão da editoria** (exigir menção à UF-alvo no título ou no corpo antes de fichar, ou rebaixar o campo `alvo` a "consulta de origem" em vez de atribuição).

**Pista quente, não aplicada: Bahia.** Quatro veículos independentes noticiam que a Bahia preparou a rede estadual de saúde para o El Niño, enquanto a BA consta no índice **só com o plano recorrente de arboviroses** (`VIG`, `recorrente_arboviroses`). O padrão que leva o nome da Bahia pode estar subaplicado na própria Bahia. Não aplicado por ora: falta o documento primário da SES-BA em domínio oficial — imprensa sozinha não passa no portão de fonte, e o precedente de SP (§109) foi decisão humana registrada, não regra.

## §111 · Minas Gerais: plano específico do ciclo localizado pela descoberta automática · 19/09/2026

Primeiro achado aplicado vindo do fluxo de **descoberta automática via API WordPress** (§11), e não de busca manual. Nenhuma alteração de método. Classe **conteúdo**.

**O §109 (18/09) registrou MG sem achado** — "só atividade federal genérica e o planejamento anual de saúde". A rodada automática de 19/09 encontrou, no portal oficial `saude.mg.gov.br`, o **"Plano de Enfrentamento ao El Niño do Estado de Minas Gerais: Preparação, Monitoramento e Resposta do Setor Saúde"** (SES-MG / Subsecretaria de Vigilância em Saúde, 127 páginas, publicado em 08/09/2026).

**Triagem feita sobre o documento primário, não sobre notícia a respeito dele.** O PDF foi preservado pelo robô (`hash_evidencia`) e conferido nesta sessão: quadros datados "Minas Gerais, 2026/2027" (ciclo corrente); seis estágios operacionais por cor (normalidade, mobilização, alerta, situação de emergência, crise) para os cenários de período chuvoso e de seca/estiagem, cada um com cenário, indicadores, ações e setores responsáveis; e estrutura de ativação e desativação de COE. Evidência mais forte que a do padrão Bahia aplicado em SP (§109), que se apoiou em seis fontes de imprensa com `hash_evidencia` nulo.

**Aplicado sem apagar o instrumento anterior**, como em SP: o plano recorrente de arboviroses (PEC-ARBO, Resolução SES/MG nº 10.440, 17/09/2025) permanece em `instrumentos[]`; o novo entra como segundo item, `tipo: especifico_ciclo`. `melhor_instrumento()` promoveu sozinho — MG passa de `VIG` para `NOVO` e a faixa do estado sobe de "em construção" para "consolidado". Índice de saúde: média das verificadas 31,3 → 32,4.

**Nota do MARÉ inalterada** (média nacional 43,6, reproduzida bit a bit por `recalcular_mare.py --check`): a camada de saúde é peso zero e nunca é lida pelo motor do índice.

As duas entradas correspondentes em `data/pistas_descobertas.json` saem de `pendente_confirmacao_documento` para aplicadas; decisão registrada em `data/log_buscas.json` (`nivel: "estadual"`).

## Correção · `nivel` fora do vocabulário derrubava a rodada completa ao preservar diário com CPF · 19/09/2026

Achado do **ensaio da rodada antecipada** (`workflow_dispatch` com `ensaio=1`, execução #83): o portão obrigatório `verificar_consistencia.py` caiu com `log_buscas[22208]: nivel inválido: municipal`, interrompendo `atualizar.py` antes do commit. Nenhuma alteração de método; nenhuma nota muda. Classe **código** (PROTOCOLO §3.2).

- **Causa-raiz.** `coletores_base.py` registra em `log_buscas.json` a redação de dados pessoais feita no texto integral de um documento preservado (`redigir_dados_pessoais()`, LGPD art. 6º, III, introduzida em 12/09/2026). Essa chamada passava `nivel="municipal"` — valor que **nunca existiu** no vocabulário controlado do portão (`_NIVEIS = {None, "nacional", "estadual", "municipal_completo"}`). Bug latente: só dispara quando o documento preservado contém CPF a redigir, e por isso não aparece nos portões rodados sobre o dado já commitado — só numa coleta fresca.
- **Impacto evitado.** A rodada de **segunda 21/09, 09h UTC** roda a mesma varredura municipal e teria falhado do mesmo modo, sem publicar. As rodadas completas de 14–15/09 (#66, #68, #69, #71–#74) falharam com assinatura compatível.
- **Correção.** `nivel=None` — o valor honesto para um registro que documenta uma redação, não uma busca territorial, e que não tem município/UF estruturados no ponto da chamada. **Não** se usou `municipal_completo`: esse valor tem sentido próprio no §2.1 (bateria municipal completa) e o portão exige `municipio` e `uf` junto dele. O vocabulário controlado **não** foi afrouxado para acomodar o bug.
- **Teste negativo.** `scripts/testar_nivel_log_buscas.py`, novo: confere por AST que nenhuma chamada de `log_busca()` em `coletores_base.py` passa nível fora do vocabulário, que a chamada da redação usa `nivel=None`, e que `_NIVEIS` não foi ampliado. Reintroduzindo `nivel="municipal"`, duas das três verificações falham.
## Correção · `data/monitor_saude.json` (focos_24h) ficava atrás da coleta diária de sinais · 18/09/2026

Achado da rotina diária: portão 12 (`scripts/verificar_derivados.sh`) vermelho na `main` (`7fda5a9`). Nenhuma alteração de método; nenhuma nota muda (peso zero, como sempre — Monitor Saúde nunca é lido por `recalcular_mare.py`). Classe **código** (PROTOCOLO §3.2).

- **Causa-raiz.** Em 17/09/2026 (§87) `coletar_sinais_risco.py` passou a rodar incondicionalmente todo dia, antes do corte de cadência semanal do índice — para que ONI, avisos do INMET e focos do INPE em `data/sinais_risco.json` deixassem de esperar até segunda-feira. `gerar_monitor_saude.py`, que copia `focos_24h` por UF de `sinais_risco.json` para `data/monitor_saude.json` (campo lido pela página `saude.html`), continuou só no bloco semanal, depois do corte de cadência — então nos dias 17 e 18/09 o robô atualizou o sinal bruto mas não o derivado, que ficou parado com os focos de 31/08.
- **Correção.** `gerar_monitor_saude.py` passa a rodar também logo após `coletar_sinais_risco.py`, incondicionalmente, todo dia — chamada idempotente (mesma função pura já usada no bloco semanal, provada por `--idempotencia`). `data/monitor_saude.json` e `docs/MANIFEST_SHA256.txt` regenerados nesta correção para a `main` ficar verde já hoje.
- **Teste.** `scripts/verificar_derivados.sh` (árvore limpa, com a correção) e `--idempotencia` (segunda regeneração não altera nada) verdes. Nenhum arquivo de `.github/workflows/` tocado.

## §110 · Gatilho de reverificação por marco federal (handover ponto cego saúde, §3.5 — fecha o handover) · 18/09/2026

Último item do handover, prioridade média por definição da própria editoria: não fecha a lacuna de hoje, mas evita a próxima defasagem de duas semanas — o mecanismo que faltava para o sistema perguntar sozinho "algo mudou desde a última verificação?" depois de um marco como a Assembleia do Conass que motivou boa parte das descobertas de hoje.

`detectar_marcos_federais.py`, novo: lê o feed RSS do Ministério da Saúde (`gov.br/saude`, Plone — RSS padrão em `<pasta>/RSS`), filtra por palavras-chave de marco relevante (Conass, coletiva, oficina, El Niño, AdaptaSUS), e compara contra `data/marcos_federais_saude.json` (marcos já processados). Marco novo → as 27 UFs de `saude_uf.json` recebem `requer_reverificacao: true` e `motivo_reverificacao`, sinalizadores internos até a rotina semanal confirmar ou atualizar cada UF.

**Semeados os três marcos já identificados nesta sessão** (lançamento do AdaptaSUS em junho, apresentação às secretarias estaduais em agosto, coletiva de imprensa em setembro) como já processados, sem marcar as UFs — a resserragem manual desta mesma sessão (§105–109) já fez esse trabalho; o gatilho não deveria repeti-lo.

**Erro cometido e corrigido antes de publicar**: o primeiro portão de segurança que escrevi (garantindo que os sinalizadores nunca vazam ao índice público) testava o parâmetro errado — `indice` em `verificar_saude.py` é `data/indice.json` (o índice de defesa civil), não `data/monitor_saude.json` (saúde). O teste negativo com o arquivo errado "passou" mesmo com um vazamento injetado de propósito — um alarme falso de segurança. Corrigido para usar `_ms`, a variável que o próprio arquivo já carrega de `monitor_saude.json`; o teste negativo, refeito contra o arquivo certo, pegou o vazamento como devia.

Suíte inteira verde (21 verificações, mais o self-test do novo script); derivados regenerados em árvore limpa.

---

**Isto fecha o handover do ponto cego de saúde por inteiro**: os cinco itens de código (§101–104, §110), a resserragem manual das 10 UFs nunca verificadas (§105–108), e o início da segunda passada nas UFs já verificadas — a intenção original por trás de todo o handover (§109, e mais rodadas registradas só no privado). Pistas ainda pendentes: Mato Grosso (ambígua) e Roraima (missão federal em curso).

## §109 · Padrão Bahia confirmado em São Paulo — primeiro achado da segunda passada · 18/09/2026

A intenção original do handover ponto cego saúde, ainda não feita até aqui: procurar, nas UFs já verificadas, um instrumento mais específico do que o registrado — exatamente o que aconteceu com a Bahia. Primeiro achado desse tipo.

**São Paulo tinha só o plano recorrente de arboviroses registrado** (15/01/2025). Achado: "Plano Estadual de Preparação e Resposta em Saúde para o Fenômeno El Niño", lançado pela SES-SP em 31/08/2026, cobrindo quatro cenários — chuvas extremas/enchentes/deslizamentos, ondas de calor/queimadas, arboviroses e um quarto eixo — não só arboviroses. Confirmado em seis fontes de imprensa independentes.

**Aplicado sem apagar o instrumento anterior**: o plano recorrente de 2025 continua na lista `instrumentos[]`; o novo entra como segundo item. `melhor_instrumento()` (escrito no §102) escolheu automaticamente o mais forte — a primeira vez que esse mecanismo roda com dois instrumentos reais da mesma UF, confirmando que a lógica funciona como projetado. SP passa de `VIG` para `NOVO`; a faixa do estado sobe de "em construção" para "consolidado".

**Minas Gerais**, buscado com o mesmo critério, não teve achado — só atividade federal genérica e o planejamento anual de saúde (documento diferente de um plano de contingência). Status mantido.

Suíte inteira verde (21 verificações); derivados regenerados em árvore limpa. Registro completo no privado, `notas/lai/respostas/SP_saude_padrao_bahia_2026-09-18.md` — inclui a lista de UFs que ainda faltam nessa segunda passada.

## §108 · Resserragem manual de saúde, rodada 4: Rondônia verificado — fecha as 10 UFs nunca verificadas · 18/09/2026

Última rodada da priorização original do handover ponto cego saúde (§3.6): as 10 UFs que nunca tinham sido verificadas foram todas tocadas ao longo de quatro rodadas nesta sessão.

**Rondônia: instrumento específico do ciclo localizado.** "Plano Operacional Integrado de Contingência Climática em Saúde", da Sesau, confirmado em oito fontes de imprensa independentes com texto quase idêntico (nota oficial, ~03/09/2026) — considera explicitamente a experiência de 2024 (menor cota do Rio Madeira, recorde de queimadas) e o novo ciclo do El Niño 2026-2027. Uma das fontes precisa: o plano está "concluído" mas "em processo de validação e discussão com os municípios" — por isso `data/saude_uf.json` registra RO como `ELAB`, não `NOVO`. Índice de saúde: 19 → 20 de 27 UFs verificadas.

**Roraima: pista em andamento, não aplicada.** Uma missão do Ministério da Saúde está em Roraima nestes dias para apoiar a elaboração de um plano diante da seca e do El Niño — recente e conjunta demais com o federal para render um documento próprio da Sesau-RR já nomeado e publicável com confiança. Fica para reverificar em 2-3 semanas.

**Tocantins**: único documento estadual encontrado cobre dados até 2020/2021 — versão claramente desatualizada de um plano recorrente, sem sinal de atualização para o ciclo atual.

**Cobertura final das 10 UFs nunca verificadas**: 3 achados aplicados (AL, PI, RO), 6 buscadas sem achado sólido o bastante para aplicar (AC, AP, MA, RN, RR, TO), 1 pista ambígua não confirmada de uma UF já verificada (MT, rodada 2) — tabela completa no registro privado, `notas/lai/respostas/RO_RR_TO_saude_resserragem_2026-09-18.md`.

Suíte inteira verde (21 verificações); derivados regenerados em árvore limpa.

## §107 · Resserragem manual de saúde, rodada 3: RN verificado, sem achado sólido o bastante · 18/09/2026

Continuação do handover ponto cego saúde (§3.6). Rio Grande do Norte buscado a fundo — o estado claramente já usa um "plano de contingência para as arboviroses" (foi a base para abrir o 1º Centro de Operações de Emergência em Saúde do Brasil, em janeiro/2025), mas nenhuma fonte encontrada traz data de publicação, número do ato ou link direto, nem confirma se é a versão vigente para o ciclo 2026/2027. `status` mantido `NAO_VERIFICADO`; `data_verificacao` registrada, para a próxima rodada ir direto à fonte oficial em vez de repetir a mesma busca.

Registro completo no privado, `notas/lai/respostas/RN_saude_resserragem_2026-09-18.md`.

Suíte relevante verde; nenhuma mudança no índice de saúde nesta rodada (só o registro de auditoria).

## §106 · Resserragem manual de saúde, rodada 2: Piauí verificado (handover ponto cego saúde, §3.6) · 18/09/2026

Segunda rodada da resserragem manual (MT, PI verificados nesta vez; RN, RO, RR, TO seguem pendentes).

**Piauí: instrumento específico do ciclo localizado.** "Plano de contingência para o enfrentamento do fenômeno El Niño", coordenado com o ADAPTASUS-PI, em fase final de elaboração — confirmado em três fontes independentes, nenhuma com data de conclusão ou link do documento ainda. `data/saude_uf.json` atualizado: PI passa de `NAO_VERIFICADO` para `ELAB` (não `NOVO`: o próprio coordenador do plano descreve como "fase final", não publicado). Índice de saúde: 18 → 19 de 27 UFs verificadas.

**Mato Grosso: pista achada, não aplicada.** Duas fontes descrevem uma "Sala de Situação em Saúde" da SES-MT — uma de agosto de 2026, citando explicitamente "El Niño 2026-2027" e uma portaria no Diário Oficial; outra, da própria SES-MT, com descrição quase idêntica mas datada de outubro de 2024, sem menção nominal ao ciclo atual. Sem acesso direto ao Diário Oficial do Estado (o site da matéria de 2026 bloqueou o fetch), não foi possível confirmar se é a mesma estrutura reativada ou algo novo — por isso o status de MT não mudou; a pista fica registrada para confirmação na próxima rodada, com o teste de robustez em mente: não aplicar sem confirmação de fonte primária, mesmo com boa evidência secundária.

Registro completo de cada busca no repositório privado, `notas/lai/respostas/PI_MT_saude_resserragem_2026-09-18.md`.

Suíte inteira verde (21 verificações); derivados regenerados em árvore limpa.

## §105 · Resserragem manual de saúde: Alagoas verificada (handover ponto cego saúde, §3.6) · 18/09/2026

Início da resserragem manual das 10 UFs de saúde nunca verificadas, priorizadas pelo handover. Nesta rodada: AC, AL, AP, MA (6 UFs — MT, PI, RN, RO, RR, TO — seguem para a próxima).

**Alagoas: instrumento novo localizado e aplicado.** "Plano de Enfrentamento das Arboviroses 2026", lançado pela Sesau em 10/02/2026, confirmado em três fontes independentes. `data/saude_uf.json` atualizado: AL passa de `NAO_VERIFICADO` para `VIG`, tipo `recorrente_arboviroses`, mesmo padrão da maioria das UFs já verificadas. Índice de saúde passa de 17 para 18 de 27 UFs verificadas (média das verificadas: 31,8 → 31,6 — a nota mais baixa de AL puxa a média um pouco, o índice não filtra pra cima).

**AC, AP, MA: busca real, sem instrumento específico publicado** — status mantido `NAO_VERIFICADO`, mas `data_verificacao` registrada (18/09/2026), para a próxima rodada não repetir a mesma busca sem necessidade. Achado lateral em MA: o portal da SES está com publicações suspensas desde 04/07/2026 por período eleitoral (aviso explícito na própria página) — mesmo padrão que o detector `fonte_suspensa_defeso` já existente no projeto reconhece automaticamente.

Registro completo de cada busca (fontes, datas, o que foi e não foi encontrado) no repositório privado, `notas/lai/respostas/AL_saude_resserragem_2026-09-18.md`.

Suíte inteira verde (21 verificações); derivados regenerados em árvore limpa; conferido visualmente na página de saúde, sem erro de JavaScript.

## §104 · Descoberta automática de planos via API WordPress (handover ponto cego saúde, §3.4) · 18/09/2026

`descobrir_planos.py`, novo — a fonte 1 de 6 especificadas em `INSTRUCOES_diarios_defeso_LAI_06-09-2026.md` §11 ("achar o plano de SC e todos os demais, sem verificação humana"), decisão editorial de 07/09/2026, ainda não implementada até hoje. Estendida desde o início a saúde (o handover que motivou esta rodada é exatamente sobre esse ponto cego não coberto pela decisão original).

**Mecanismo**: consulta a API WordPress padrão dos sítios oficiais (`/wp-json/wp/v2/media?search=...&mime_type=application/pdf`) — muitos sítios estaduais são WordPress; onde não são, a API simplesmente não responde como esperado e o alvo não produz achado (perda de recall, nunca invenção). Reaproveita a infraestrutura já madura de `coletores_base.py` (cliente HTTP com detecção automática de página de defeso, preservação de evidência com hash, índice único `data/evidencias.json`) em vez de duplicá-la.

**Mesma trava absoluta dos monitores de imprensa** (§101–103): nunca escreve em nenhum dos cinco arquivos que alimentam o índice; todo achado nasce com `documento_oficial_confirmado: null` e `promovivel: false`; fila própria (`data/pistas_descobertas.json`) para triagem humana — promoção a instrumento pontuável é sempre manual (regra R7).

**Lista de domínios**: declarada como incompleta desde a primeira versão — alguns confirmados nesta sessão (`saude.ba.gov.br`, achado no caso Bahia), os demais usam o padrão mais comum como primeira tentativa (`saude.<uf>.gov.br` / `defesacivil.<uf>.gov.br`), precisando de curadoria contínua. Um domínio errado só reduz recall, nunca produz um resultado inventado.

**Erro de teste corrigido antes de publicar**: o primeiro autoteste tentava simular (`mock.patch`) uma resposta de rede, mas usava o nome do módulo como string fixa (`"descobrir_planos.buscar"`) — que não bate quando o script roda diretamente (o Python o chama `__main__`, não `descobrir_planos`, nesse caso). Dois testes rodaram contra a rede de verdade em vez do mock; um deles só "passou" por coincidência (a falha de rede real também caiu no mesmo caminho de tratamento de erro que o teste esperava). Corrigido para resolver o nome do módulo em tempo de execução (`__name__`).

Registrado na Pista A, logo após os dois monitores de imprensa. Self-test completo (domínio conhecido e padrão de fallback, parsing do wp-json isolando só PDFs, tolerância a falha de rede, deduplicação, trava absoluta por inspeção do código-fonte) verde. Nenhum arquivo público alterado.

## §103 · Monitor de imprensa dedicado à saúde (handover ponto cego saúde, §3.3) · 18/09/2026

`monitorar_imprensa_saude.py`, novo, espelhando `monitorar_imprensa_regional.py` (defesa civil) — mesma trava absoluta (nenhuma pista entra no banco sem confirmação humana em documento primário: três camadas independentes de garantia, verificadas por self-test), mesmo mecanismo de busca (Google News RSS, sem chave de API), mesma fila (`data/pistas_imprensa_saude.json`, cursor próprio em `data/imprensa_saude_cursor.json`, isolados dos de defesa civil).

**Diferença deliberada**: os termos de busca são os do dicionário ampliado no §101 (achado do caso Bahia — nomes que espelham o programa federal do MS, não mais só "arboviroses"), combinados a "secretaria de saúde"/"Sesab"/"Ses&lt;UF&gt;". Priorização em três camadas: UFs nunca verificadas primeiro, depois as com verificação anterior a setembro de 2026, depois as demais em busca ampla (para pescar o próprio padrão Bahia: UF já com instrumento registrado, mas um mais específico ainda não descoberto).

**Erro cometido e corrigido antes de publicar**: a primeira versão da priorização comparava datas no formato `dd/mm/aaaa` como texto puro — o que não ordena por data real, já que o dia vem primeiro (`"05/09/2026" > "01/09/2026"` como string, mas isso não significa o que parece). Corrigido para comparar por `aaaa-mm` depois de decompor a data; o self-test que pegou o erro original foi mantido, com um caso adicional para não deixar essa classe de bug repetir.

Registrado na Pista A (`atualizar.yml`), logo após a vigia de imprensa de defesa civil, mesmo padrão (`continue-on-error: true`, informativa, nunca bloqueante).

Self-test completo (parser RSS, heurística de fonte provável, deduplicação, trava absoluta por inspeção do próprio código-fonte, priorização em camadas, cursor) verde. Nenhum arquivo público (HTML/JS/CSS) alterado — só um coletor novo e o workflow que o agenda.

## §102 · saude_uf.json migrado para instrumentos[]; LAI da Bahia enviada · 18/09/2026

Handover da editoria, §3.2 e conclusão do §4.

**LAI da Bahia enviada.** Localizei o canal oficial (Ouvidoria da Sesab, confirmado em duas fontes independentes do governo do estado) e enviei o pedido específico sobre o "Plano de Ações de Saúde para o Enfrentamento ao El Niño 2026/2027" (R$ 30,5 mi), pedindo também a data de envio ao Ministério da Saúde. Entregue sem bounce; registrado no repositório privado.

**Esquema de saúde migrado para `instrumentos: []`**, mesmo padrão de `data/estados.json` (defesa civil), pedido no handover. Achado ao investigar antes de escrever: defesa civil não tem, de fato, uma função "escolher o melhor entre N instrumentos" para reaproveitar — o campo de topo de cada UF ali é um espelho fixo de um tipo específico (`instrumento_operacional`), confirmado nas 27 UFs; não existia nada para reusar. Para saúde, com três tipos formando uma escala de força real (documento específico do ciclo > plano recorrente de arboviroses > só uma estrutura de coordenação), a lógica de escolha é nova: `melhor_instrumento()`, em `migrar_saude_instrumentos.py`.

**Migração testada e provada sem regressão**: o autoteste do script de migração roda a migração contra o dado real antes de gravar, e recusa gravar se qualquer valor de topo mudaria — passou. Depois de aplicada, o gerador do índice (`gerar_monitor_saude.py`) foi atualizado para calcular os campos de topo a partir de `instrumentos[]` a cada rodada, em vez de lê-los direto (assim uma futura LAI ou pista de imprensa aplicada só na lista já vale no índice na rodada seguinte, sem precisar reescrever o topo à mão). Comparação campo a campo entre a saída de antes e de depois da mudança inteira: nenhuma diferença.

**Portão novo** em `verificar_saude.py` (item "u"): cada UF precisa de ao menos um item em `instrumentos`, e o status/doc do topo não pode divergir do melhor item em silêncio. Teste negativo executado (status do topo divergindo do instrumento) e revertido com segurança.

**Achado no CI, corrigido**: o portão 17 (robustez a atualização de dados) simula uma "cópia perturbada" do repositório para provar que uma atualização real de dados não quebra o site — e sua simulação para saúde escrevia só nos campos de topo de duas UFs, sem saber que agora precisa manter `instrumentos[]` sincronizado; o próprio portão novo do item anterior pegou a divergência. Corrigido para a perturbação também inserir o item na lista e recomputar o topo do melhor instrumento, como a rotina real passa a fazer. No caminho, um erro de processo: o trabalho desta rodada foi commitado por engano direto em `main` local (esqueci de entrar na branch de feature antes de editar) — corrigido sem `git checkout` destrutivo, movendo o commit para a branch certa e devolvendo `main` local ao estado publicado.

Suíte inteira verde (22 verificações, incluindo o portão de robustez); derivados regenerados em árvore limpa; conferido visualmente na página de saúde, sem erro de JavaScript. Restante do handover (monitor de imprensa dedicado, descoberta automática via wp-json, resserragem manual das 26 UFs restantes, gatilho por marco federal) segue em rodadas futuras, na ordem que a editoria definiu.

## §101 · Ponto cego do dicionário de busca em saúde fechado (achado via handover, caso Bahia) · 18/09/2026

Handover da editoria: uma matéria de imprensa (18/09) revelou que o "Plano de Ações de Saúde para o Enfrentamento ao El Niño 2026/2027" da Sesab (R$ 30,5 mi, enviado ao MS em agosto, confirmado em oito veículos independentes) não estava em `data/saude_uf.json` — a Bahia seguia classificada pelo plano recorrente de arboviroses (2025), verificado em 05/09/2026, sem o documento mais específico e mais forte do ciclo.

**Causa confirmada em código**: `data/dicionario_busca.json`, grupo `saude`, não tinha os termos que os estados passaram a usar depois de 02/09/2026 — o padrão de nome espelha o que o próprio Ministério da Saúde deu ao seu programa federal, e é mais recente que o dicionário.

**Corrigido nesta rodada**: seis termos novos acrescentados ao grupo `saude` do dicionário, cada um com a origem registrada (achado de 18/09/2026, caso Bahia). Isso é o primeiro de seis itens de um handover maior (schema de `instrumentos: []` para saúde, monitor de imprensa dedicado, descoberta automática via wp-json, reverificação por marco federal, resserragem manual dos 27 estados) — os demais seguem em andamento, não cabem numa única rodada.

**Apuração do caso Bahia em si**: busca direta pelo PDF (3 tentativas: busca geral, busca restrita ao domínio oficial, leitura da matéria original) não localizou um link público direto ao documento integral — só cobertura de imprensa, ainda que de fontes robustas (o próprio site oficial do estado, bahia.ba, entre outras). Rascunho de pedido LAI específico preparado (registro privado, `notas/lai/textos/BA_saude.txt`), pedindo o documento integral e a data de envio ao MS — aguardando aprovação para envio. Reverificado também `estados.json` BA (defesa civil): o comitê para o "Plano Estadual de Ações de Enfrentamento aos Impactos do El Niño 2026/2027" (`estrutura_coordenacao`, LAC desde 04/09) segue sem ato publicado no DOE-BA em nenhuma cobertura encontrada — status mantido, nenhuma mudança de dado aplicada sem fonte primária.

O achado da imprensa sobre "52% dos estados" enviaram plano ao MS não foi tratado como fato confirmado (nota oficial do MS não cita o percentual; só duas matérias, mesma origem aparente, o mencionam) — registrado como não confirmado no registro privado, não entra em nenhuma superfície pública.

Suíte relevante verde; nenhum arquivo público (HTML/JS/CSS) alterado nesta rodada — só o dicionário de busca interno, usado pelos coletores.

## §100 · Resumo de preparação migra para a home; "Antes/Depois" vira "Preparação publicada/Decretos de emergência" · 18/09/2026

Pedido direto da editoria, em `defesa-civil.html` e `index.html`.

**Gráfico "Status dos planos estaduais, por região" removido** de `defesa-civil.html`, com o resumo que ele gerava ("N estados com plano para o ciclo; M com plano de todo ano; P sem plano localizado" e "Por região: X concentra os planos feitos para o ciclo") migrado para a home, como um parágrafo abaixo dos dois medidores (índice MARÉ Legal + contador de decretos) — mesmo cálculo, mesma fonte (`data/estados.json`), que a home já carregava para outra finalidade.

**Tabela "Decretado × reconhecido, por estado" removida** por inteiro (estava dentro de um acordeão "Ver mais").

**Linguagem "Antes"/"Depois" trocada por "Preparação publicada"/"Decretos de emergência"** — nos dois `<h2>` de `defesa-civil.html` (que também tinham travessão, corrigido de quebra), no hint do topo da página, nas meta descriptions (4 lugares), e nos dois selos da home.

**Mapas reorganizados de três para duas colunas** ("dois a dois") no painel de preparação.

**Dois erros cometidos e corrigidos no próprio trabalho**: ao remover o bloco da tabela no JS, uma chave de fechamento de função foi apagada por engano — sintaxe quebrada, achada e corrigida antes de publicar. E o portão de segurança passou a reclamar de uma função auxiliar (`interp`, já existente, não escrita nesta rodada) por `innerHTML` sem `esc()` nas proximidades — não por uma falha nova, mas porque a única chamada que "mascarava" o alarme (por estar fisicamente perto o bastante do texto) foi removida junto com o gráfico; a chamada remanescente já tinha dado seguro (campo `esc()`-ado), documentado o contrato de segurança da função ao lado da definição para o portão (e qualquer leitor humano) reconhecer.

Dois portões atualizados para refletir a mudança sem perder cobertura: `verificar_runtime_resposta.js` (cobertura de 27 UFs passa a checar o dado, não o elemento removido) e `verificar_runtime.js` (novo teste do resumo na home, mesma regra que existia em `defesa-civil.html`).

Suíte inteira verde (21 verificações); derivados regenerados em árvore limpa; conferido visualmente em ambas as páginas.

## §99 · Dicas por risco na imagem, logo antes do menu, descrição da página atualizada · 18/09/2026

Três correções diretas da editoria, sobre o trabalho do §96–98.

**Imagem para compartilhar ganha as dicas, não só os telefones.** Três dicas por risco (chuva, incêndio, estiagem), em bullet points, com um traço colorido por família — mesma cor da ficha correspondente na página. As dicas são o texto das próprias fichas já publicadas, as mais urgentes de cada uma ("durante"/"sinais de alerta"), não reescritas. A imagem cresceu de ~110 KB para ~180 KB e de 1080×1180 para 1080×~1570px (a altura real do conteúdo, calculada depois de desenhar, para não sobrar nem faltar espaço) — segue bem abaixo do que o WhatsApp recomprime.

**Logotipo do MARÉ volta para o topo do cabeçalho, antes do menu** — vivia depois da navegação (entre o menu e a faixa "2026/2027 · Monitoramento..."); passa a ser o primeiro elemento do cabeçalho, nas 11 páginas.

**Descrição de `proteja-se.html` atualizada** — a antiga descrevia a página de antes da rodada §92–98 (tinha até um travessão, contra a regra do §3) e não mencionava telefone de emergência, PDF nem imagem para baixar. Trocada nos quatro lugares que carregam essa descrição (`<title>`, meta description, Open Graph, Twitter, JSON-LD) — a primeira versão passou do teto de 170 caracteres do portão de SEO, encurtada.

Suíte inteira verde (21 verificações); derivados regenerados em árvore limpa; conferido visualmente e com a imagem real gerada.

## §98 · Imagem para compartilhar por WhatsApp; PDF e imagem ganham o logotipo do MARÉ · 18/09/2026

Pedido direto da editoria ("isso é fundamental").

**Achado ao abrir o gerador de PDF antes de mexer**: ele usava o logotipo do Futura (não o do MARÉ) como imagem de cabeçalho e como marca d'água diagonal em toda página. Trocado pelo novo logotipo (a mesma imagem usada no site, rasterizada uma vez a 900×342px para caber no PDF sem pesar); a marca d'água passou a dizer "MARÉ", não mais "FUTURA · EVIDENCE LAB" — o Futura segue creditado no rodapé de cada página do PDF, no mesmo tamanho discreto que já tinha, espelhando o tratamento que o próprio site já dá a ele desde o §96.

**Botão novo, "Baixar imagem para compartilhar", ao lado do de PDF** (contorno em vez de preenchido, para o PDF continuar sendo a ação principal). Gera uma imagem JPEG única — 1080×1180, quase quadrada, dentro do que o WhatsApp aceita como foto sem recomprimir agressivamente — com o logotipo do MARÉ, título, e os cinco números de emergência em caixas coloridas (mesma paleta dos cartões da página e do PDF). Desenhada em `<canvas>`, não em HTML: o PDF já usava esse tipo de desenho para as caixas de emergência, e um `<canvas>` consegue herdar as fontes da própria marca (Fraunces, Archivo) que um `<img>` não conseguiria.

Testado de ponta a ponta de verdade (clique no botão, captura do arquivo baixado, não só o código): ~110 KB, 1080×1180px, sem espaço sobrando — a primeira versão tinha uma altura de canvas maior que o conteúdo real; ajustada.

**Achado no meio do trabalho**: as cores do canvas, em hex, bateram de frente com o portão que proíbe hex fora da paleta — convertidas para `rgb()`, o mesmo formato que o gerador de PDF já usava para evitar esse problema (arrays de RGB, não hex).

Suíte inteira verde (21 verificações); derivados regenerados em árvore limpa; conferido visualmente e com a imagem real gerada.

## §97 · "Leve estas informações com você" volta a ser o título; ficha da Defesa Civil ao lado do seletor · 18/09/2026

Pedido direto da editoria.

**Título do bloco único volta a ser "Leve estas informações com você"**, formatado com o mesmo destaque que "Proteja-se" tinha (tamanho do `<h1>` da página) — o selo separado saiu, já que agora é o único título do bloco, não um rótulo acima de outro título. Texto do parágrafo reescrito: o que o guia cobre (o que fazer, como se proteger, telefones de emergência) e os formatos de uso (salvar, imprimir, enviar por e-mail, compartilhar em grupos de WhatsApp), mantendo o link para o relatório do estado/município na página principal.

**Cartões da Defesa Civil por estado deixam de aparecer todos de uma vez.** A grade dos 27 estados ("Ver todos os estados") passa a vir fechada por padrão — só quem quiser navegar por todos os estados a abre manualmente. A ficha do estado escolhido no seletor passa a aparecer ao lado dele (grid de duas colunas), não abaixo em largura total; um aviso discreto ocupa o espaço à direita antes de qualquer escolha, para o espaço não parecer quebrado. Em telas estreitas, as duas colunas empilham como antes.

Suíte inteira verde (21 verificações); derivados regenerados em árvore limpa; conferido visualmente nos dois estados (vazio e com estado escolhido).

## §96 · Logotipo oficial do MARÉ substitui o texto no cabeçalho; Futura sai do topo, fica só no rodapé · 18/09/2026

Pedido direto da editoria, com arquivo de logotipo em vetor (4 variantes: completo/compacto × fundo claro/escuro).

**Achado ao abrir o arquivo antes de usar**: as duas versões "completo" traziam o nome antigo — "MEDIDA de Antecipação e Resposta", de antes da renomeação desta mesma sessão (§79) para "Monitor". Corrigido nas duas variantes antes de qualquer publicação; conferido visualmente com as fontes reais (Fraunces + Archivo Narrow) que o texto mais longo ainda cabe sem cortar.

**Logotipo (versão completa, fundo claro) substitui "MARÉ" + subtítulo em texto**, nas 11 páginas. Embutido direto no HTML (não como `<img>`) — imagem carregada por `src` não herda as fontes da própria página, e o logotipo depende delas. O `<h1>`/`<p>` que carregava o título continua existindo por semântica e acessibilidade (texto em `.sr-only` para leitor de tela); visualmente mostra o SVG. Tamanho maior na home, menor nas páginas internas (`.masthead--mini`).

**Logotipo do Futura sai do topo de todas as páginas** — a cópia do rodapé, que já existia, agora é a única. Achado no meio do trabalho: a remoção inicial usou o padrão de link do cabeçalho da home (link externo, `target="_blank"`) em todas as páginas, mas nas páginas internas é o RODAPÉ que usa esse padrão (o cabeçalho ali já era um link interno mais simples, "voltar para a home") — a primeira rodada apagou o logotipo errado (rodapé) nas 10 páginas internas. Comparado contra a árvore original arquivo por arquivo para achar exatamente essa troca; rodapé restaurado, cabeçalho corrigido nas 10 páginas.

**Portão novo**: o logotipo é marca fixa — cores e tipografia deliberadas do desenho, não conteúdo — e colidia com três checagens que proíbem tipografia solta e hex fora da paleta em qualquer lugar da página. Adicionada uma exceção documentada e escopada (`data-marca-fixa`, mesmo padrão de `data-voz="ficha"` já usado no projeto), não um desligamento geral de portão.

Suíte inteira verde (21 verificações); derivados regenerados em árvore limpa; conferido visualmente em duas páginas (home e uma interna), com tipos MIME corretos, sem erro de JavaScript.

## §95 · "Leve estas informações" e "Como se proteger" viram um bloco só, chamado Proteja-se · 17/09/2026

Pedido direto da editoria.

**As duas seções (painel do PDF + título dos guias) viram um bloco único**, sem moldura, formatado como o próprio cabeçalho da página (selo + título grande, no mesmo tamanho do `<h1>` "Proteja-se: orientações oficiais e alertas" + texto): selo "Leve estas informações com você", título "Proteja-se", um parágrafo cobrindo os dois assuntos (o guia em PDF e o que vem a seguir), e o botão de baixar centralizado abaixo do texto — não mais lado a lado dentro de um painel com borda. O `<h2 id="como-se-proteger">` que separava as duas seções saiu; os três acordeões de cenário passam a vir direto abaixo do bloco único.

**Portão de consistência visual pegou a mudança corretamente** (h2 com dois tamanhos diferentes) — exceção adicionada ao seletor da família "h2 (seção)", mesmo padrão já usado para excluir `.ficha h2` (que também varia de propósito), com comentário explicando que é deliberado, não drift.

**Gerador de PDF corrigido**: ele lia o título e a descrição da seção removida (`#como-se-proteger`) para escrever a primeira página do PDF; sem esse elemento, ficaria mudo. Texto fixado diretamente no gerador — o PDF é um documento à parte da página viva e não precisa espelhar o HTML linha a linha.

**Geração de PDF testada de ponta a ponta de novo** (jsPDF real, PDF de verdade lido de volta): título, os cinco números de emergência e as três fichas completas aparecem; contatos da Defesa Civil, alertas de saúde e FGTS Calamidade continuam fora do escopo, como já estava.

Suíte inteira verde (21 verificações); derivados regenerados em árvore limpa; conferido visualmente.

## §94 · Guias de cenário ganham cor e ícone também fechados, não só abertos · 17/09/2026

Ao conferir o pedido do §93 (já publicado quando esta sessão começou — feito em paralelo, achado ao investigar), sobrou uma lacuna real: as três fichas de cenário (chuvas/incêndios/estiagem) ficaram com visual elaborado quando abertas, mas no estado fechado — o que a maioria vê primeiro, antes de clicar — continuavam como qualquer acordeão genérico do site: linha fina, "+", sem cor. A maior parte de uma visita nunca chega a abrir os três.

Resumo de cada acordeão ganhou: o mesmo ícone e a mesma cor de risco que a ficha já usa por dentro (chuva/seca/fogo, nada novo inventado), fundo branco, sombra, cantos arredondados — e quando aberto, o resumo colorido e a ficha branca se encaixam como um bloco só (cantos que se completam, sem borda dupla no meio). Os acordeões genéricos do site (contatos, "Ver em tabela") não foram tocados — a mudança é restrita à classe nova, não ao seletor geral de acordeão.

Suíte inteira verde (21 verificações); derivados regenerados em árvore limpa; conferido visualmente fechado, aberto e em mobile.

## §93 · Proteja-se: guias sobem na página, fichas e contatos redesenhados, PDF reescopado · 17/09/2026

Pedido direto da editoria, quatro frentes na mesma página.

**"Como se proteger em cada cenário" agora vem logo após "Leve estas informações com você".** Na prática, "Defesa Civil do seu estado" (que ficava entre as duas) desceu para depois dos guias — mesmo efeito visual, sem duplicar as três fichas de orientação. O subnav já refletia essa ordem.

**Fichas de chuvas/incêndios/estiagem redesenhadas** — fundo cinza uniforme virou fundo branco com borda superior colorida por risco (reaproveita `--chuva`/`--seca`/`--fogo`, já usadas no selo e no h2 de cada ficha), sombra própria. O quadro "Sinais de alerta" dentro de cada ficha ganhou a mesma borda esquerda colorida, para não ficar branco dentro de um card que também é branco agora.

**Cartões de "Defesa Civil do seu estado" (as 27 UFs) redesenhados** — mesma lógica: borda superior colorida (musgo), sombra própria.

**Botão de baixar o PDF, redesenhado** — ganhou ícone, corpo maior, sombra e elevação no hover; a seção virou texto + botão lado a lado, para a ação mais importante não ficar perdida como um link discreto entre parágrafos.

**PDF: escopo corrigido e cores atualizadas.** Achado real: o gerador varria TODO o conteúdo textual da página (h2/h3/p/li), então o PDF incluía os 27 cartões de contato estadual da Defesa Civil, "Alertas de saúde" e "Direitos ao FGTS Calamidade" — nada disso é telefone de emergência nem dica de proteção. Escopo restrito ao título "Como se proteger" e ao conteúdo dentro das três fichas; o resto fica de fora. Os números de emergência, que o PDF nunca tinha incluído (a barra é feita de `<a><b><span>`, uma estrutura que o antigo varredor de h2/h3/p/li não lia), agora são desenhados à mão como caixas coloridas, mesma paleta dos cartões da página. Os títulos de cada ficha no PDF também passam a usar a cor do risco correspondente (antes, todos saíam na mesma cor, uma inconsistência com a página). Geração real testada de ponta a ponta (jsPDF real rodando em navegador simulado, PDF de verdade lido de volta): confirmado que os 27 contatos, alertas de saúde e direitos não aparecem mais, e que as três fichas completas aparecem no PDF gerado.

Suíte inteira verde (21 verificações); derivados regenerados em árvore limpa; conferido visualmente e a geração de PDF testada de ponta a ponta.

## §92 · Proteja-se: risco por estado sai (já mora no mapa de riscos), cartões de emergência redesenhados · 17/09/2026

Pedido direto da editoria.

**"Qual é o risco projetado no seu estado" removida por inteiro.** O mesmo mapa já mora em monitor-de-riscos.html; manter os dois era redundância, não reforço. Achado ao remover: o seletor dessa seção também abria o guia certo (chuvas/fogo/seca) e preenchia o cartão de "Defesa Civil do seu estado" automaticamente — comportamento preservado redirecionando o preenchimento automático para o seletor de contato, que já existia separadamente; o auto-abrir-guia por estado não tinha substituto direto e foi embora com a seção (os guias continuam abertos manualmente, como acordeões). Dois portões que dependiam do seletor removido, ajustados; um teste novo cobre o comportamento equivalente pelo seletor que ficou.

**Cartões de emergência (193/192/199/190/40199) redesenhados** — estavam com fundo cinza uniforme, sem hierarquia visual, "sem vida". Agora: fundo branco de verdade, borda superior grossa e colorida por número (mesmo sistema de acento que o site já usa em painel--acento-* e cartao--acento-*, uma cor por natureza do número: Bombeiros em terracota, SAMU em âmbar, Defesa Civil em azul, Polícia Militar em preto, SMS em verde), sombra própria e elevação ao passar o mouse.

**Achado no caminho, maior que o pedido**: `proteja-se.html` nunca esteve na lista de páginas cobertas pelo portão de travessão e voz editorial (`verificar_legendas.js`) — a página inteira ficou fora dessa rede de segurança desde que a regra existe, mesmo já coberta pelos outros portões de voz. Adicionada à lista; 10 violações reais apareceram (a maioria travessão, revertido em toda parte; três fichas de orientação oficial e o bloco de direitos ao FGTS Calamidade marcados com o mesmo atributo que o resto do site usa para reprodução oficial, isentando ênfase/interrogação legítimas de instrução — "beba apenas água tratada", "água entrando em casa?" — sem isentar o travessão, que é regra de estilo, não de conteúdo).

Suíte inteira verde (21 verificações); derivados regenerados em árvore limpa; conferido visualmente, sem erro de JavaScript.

## §91 · RONI e anomalia mensal ganham o mesmo fundo preto do ONI (achado: CSS preso a um id só) · 17/09/2026

Patricia notou que RONI e a anomalia mensal não pareciam iguais ao ONI, apesar do código já compartilhar cor e animação entre os três desde o §88. Causa real: o fundo preto vinha de uma regra CSS por id (`#wrapOni{background:#000;...}`), que por definição só vale para aquele elemento — nunca se aplicou aos outros dois, que ficavam com fundo branco por trás das mesmas barras vermelhas e azuis.

Regra trocada de seletor de id para uma classe (`.grafico-preto`), aplicada nos três wrappers (`#wrapOni`, `#wrapRoni`, `#wrapAnomalia`). A animação já era, de fato, igual nos três desde o §88 (mesma função `opcoesGraficoAnom` já compartilhada) — não havia nada a corrigir ali, só o fundo.

Suíte inteira verde; derivados regenerados em árvore limpa; conferido visualmente, os três agora idênticos em design.

## §90 · ONI, RONI e anomalia mensal lado a lado, num grid só, mesmo design · 17/09/2026

Pedido direto da editoria: os três gráficos viviam em dois blocos (ONI e RONI juntos, anomalia mensal sozinha embaixo, largura cheia). Unificados num único `grade-figuras--3` (classe que já existia no site, "lado a lado quando cabem três") — os três em uma linha só, cada um a um terço da largura. A classe `figura--largo` saiu da anomalia (forçava largura total, incompatível com caber em um terço). Os três já compartilhavam a mesma paleta e as mesmas opções de gráfico desde o §88; a diferença agora é só de disposição.

Suíte inteira verde; derivados regenerados em árvore limpa; conferido visualmente, os três lado a lado.

## §89 · A nota de cada gráfico volta para debaixo dele mesmo, não uma nota só no fim dos três · 17/09/2026

Correção direta: o §88 tinha juntado a explicação dos três gráficos (ONI, RONI, anomalia mensal) numa nota só, depois dos três. Cada um precisa da sua própria nota, logo abaixo de si — não uma nota comum ao final.

Removida a nota combinada. As três notas que já existiam (`oniLeitura`, `roniLeitura`, `anomaliaLeitura`, uma dentro de cada `<figure>`, no mesmo padrão de sempre) passam a carregar sozinhas a explicação inteira de cada gráfico — reforçadas para não depender de o leitor ter lido as outras duas antes. A do RONI ganhou a frase sobre ser a medida oficial da NOAA desde agosto de 2026 (que estava só na nota combinada); a da anomalia mensal ganhou a frase que faltava dizendo o que ela mede.

Duas notas passaram do teto de 240 caracteres e do limite de duas frases que o portão de legendas já aplicava — encurtadas mantendo o essencial.

Suíte inteira verde; derivados regenerados em árvore limpa; conferido visualmente, cada nota no card certo.

## §88 · RONI ao lado do ONI, mais o gráfico de anomalia mensal, com nota explicando os três · 17/09/2026

Patricia perguntou se o ONI estava mesmo em +1,8 °C, achando que deveria estar mais alto. Fui checar direto na NOAA. A resposta tinha duas partes: o número está certo (confirmado em três produtos oficiais independentes: PSL, `oni.ascii.txt` do CPC e a tabela ERSSTv6 do CPC), mas a NOAA trocou de índice oficial em agosto de 2026 — o **RONI** (Relative Oceanic Niño Index) substituiu o ONI clássico como métrica de classificação, e para o mesmo trimestre (JJA/2026) o RONI está em +1,4 °C, mais baixo, não mais alto (ele desconta o aquecimento médio de todo o oceano tropical). Pedido resultante: os dois lado a lado, mais um terceiro gráfico com a anomalia mensal (sem a suavização de três meses que ONI e RONI aplicam), e uma nota explicando os três para um leitor leigo.

**Coleta nova, de verdade, não só exibição.** `coletar_sinais_risco.py` ganhou `parse_roni()` (mesmo padrão de `parse_oni()`, arquivo com uma coluna a menos) e `parse_nino34_mensal()` (lê a 5ª coluna do arquivo de anomalia detendenciada do CPC, não a 3ª). Duas fontes novas catalogadas (`noaa_roni`, `noaa_nino34_mensal`), com endpoint automático (`RONI.ascii.txt` e `detrend.nino34.ascii.txt`, ambos confirmados como arquivos reais e correntes do CPC) — a rotina diária (já corrigida no §87 para rodar todo dia) busca os dois automaticamente daqui em diante. `data/sinais_risco.json` semeado agora com a série real: RONI completo desde 1950 (919 pontos), anomalia mensal dos últimos ~4 anos.

**Layout**: ONI primeiro, RONI ao lado (mesma linha, mesma família visual: fundo preto, vermelho acima de zero, azul abaixo, transição por opacidade, animação ligada — as três figuras compartilham a mesma paleta e as mesmas opções de gráfico agora, um só lugar no código em vez de três). Achado no caminho: a classe `figura--largo` força largura total e brigava com "lado a lado" — as duas figuras perderam essa classe (a de anomalia, que é para ficar sozinha, manteve). Anomalia mensal em terceiro, abaixo dos dois, largura cheia.

**Nota explicativa, para leitor leigo**, logo abaixo dos três: o que os três medem (a mesma coisa, a temperatura do mar na região Niño 3.4), a diferença entre ONI e RONI em uma frase, que a NOAA trocou de índice oficial em agosto de 2026, e o que o terceiro gráfico mostra que os outros dois não mostram (o dado cru, sem suavização).

Autoteste do coletor cobrindo os dois parsers novos (inclusive negativo: cabeçalho não vira ponto de série). Um ajuste de portão no caminho: a nota usava "por isso", que o portão de voz trata como causalidade não demonstrada — reescrita sem perder o sentido. Suíte inteira verde (21 verificações); cadeia de derivados regenerada em árvore limpa; conferido visualmente, sem erro de JavaScript.

## §87 · Monitor de riscos: coleta diária de verdade, textos coerentes, fontes linkadas, riscos mistos decompostos · 17/09/2026

Pedido direto da editoria, a rodada mais densa desta página até agora.

**Achado ao checar a frequência de atualização (pedido explícito): a coleta que alimenta esta página inteira só rodava às segundas-feiras.** `coletar_sinais_risco.py` (ONI, avisos do INMET, focos do INPE, alertas do CEMADEN) vivia depois do portão de cadência semanal do índice — mesmo o próprio módulo já se declarando "peso zero, nunca pontua, independente do índice". A chamada, em `atualizar.py`, sai de dentro do portão e passa a rodar todo dia, incondicional.

**"O que esta página não diz" removido** — as duas declarações de conformidade que ele carregava (sinais reproduzidos dos órgãos; não entram na nota) são exigidas por portão (`verificar_sinais.py`); integradas à frase principal da página, não perdidas.

**Frase principal reescrita, com link real em cada órgão** (NOAA, CEMADEN, INPE, ANA, INMET), cada um apontando para a mesma URL que o próprio coletor já usa como fonte daquele dado especificamente — não a home genérica de cada órgão.

**"Situação atual" parou de ser fragmentos juntados por "·" e virou prosa.** A causa: a frase vinha de raspar o `textContent` de outros campos já renderizados, sem conectivo nenhum. Reescrita a partir dos dados diretamente — e por sorte um campo já existente (`prognostico.enso.leitura`) já trazia a mesma informação como narrativa coerente e pronta, só não estava sendo usada aqui. Uma segunda função, antiga e esquecida, que reconstruía a versão fragmentada num evento de `load` separado, foi removida — ela teria desfeito a correção assim que a página carregasse.

**Removidos**: a linha "Última atualização" abaixo da Figura 1 (voltando atrás do pedido da sessão anterior, a pedido desta), e o aviso "Probabilidade por trimestre: sem coleta até o corte".

**Redundância na linha de fontes resolvida**: o crédito do ONI aparecia duas vezes na mesma tela (a Figura 1 já credita); tirada a repetição.

**Riscos mistos, decompostos.** A barra "Misto" só informava uma contagem sem dizer do quê. `classificar_tipo()`, em `coletar_sinais_risco.py`, já detectava os riscos individuais antes de colapsar em "misto" — só não expunha essa lista. Nova função `componentes_de_risco()` expõe os componentes (ex.: Acre vira `estiagem + incêndios`, não só `misto`); novo campo `componentes` em `data/sinais_risco.json`, populado rodando `--semear` uma vez. O gráfico de tipos de risco recontou: um estado com risco misto agora soma em CADA risco que o compõe, não numa barra à parte — a soma das barras pode passar de 27, de propósito. O mapa não mudou (mesma cor "misto"); o texto ao passar o mouse nele passou a nomear os riscos que compõem o misto daquele estado, em vez de só repetir a categoria.

**Dois portões novos**: autoteste do coletor cobrindo `componentes_de_risco()` (inclusive a concordância entre `len(componentes) > 1` e `tipo == "misto"`), e um teste de integridade em `verificar_sinais.py` sobre o dado real gerado (todo "misto" com pelo menos 2 componentes; todo tipo único com exatamente 1; nenhum componente fora do vocabulário). Teste negativo executado (componente incompleto num estado misto) e revertido com segurança.

**Mapas reordenados**: avisos meteorológicos e alertas do CEMADEN agora vêm antes de seca e fogo, como pedido; legenda do painel ajustada; um travessão encontrado no título de um dos cartões, corrigido no caminho.

Suíte inteira verde (21 verificações); cadeia de derivados regenerada em árvore limpa; conferido visualmente, sem erro de JavaScript.

## §86 · "Monitor de risco" vira "Monitor de riscos"; sinais-de-risco.html vira monitor-de-riscos.html · 17/09/2026

Pedido direto da editoria: o endereço da página (`sinais-de-risco.html`) e o nome exibido (`Monitor de risco`) estavam divergentes; os dois passam a se chamar "Monitor de riscos".

Renomeados os dois arquivos por trás da página (`sinais-de-risco.html` → `monitor-de-riscos.html`; `assets/js/sinais-de-risco.js` → `assets/js/monitor-de-riscos.js`, mesmo padrão de nome usado pelas demais páginas do site). Atualizado em cada um dos onze links de navegação do site, no `<h1>`, título, meta tags (canônica, Open Graph, Twitter, JSON-LD), `sitemap.xml`, e nos geradores e portões que citavam o nome de arquivo ou o rótulo antigos (nove scripts de portão, três geradores Python).

Redirecionamento 301 adicionado em `netlify.toml` (`/sinais-de-risco.html` e `/sinais-de-risco` → `/monitor-de-riscos.html`), no mesmo padrão já usado para as renomeações anteriores do site (`mapas-e-graficos.html`, `para-gestores.html`), para quem tiver o endereço antigo salvo ou linkado.

Varredura final, sem tags, confirmou que não sobrou nenhuma menção ao nome ou ao endereço antigos fora dos comentários que documentam a própria mudança e do redirecionamento (que precisa citar o endereço antigo para funcionar).

Suíte inteira verde de primeira (21 verificações); cadeia de derivados regenerada em árvore limpa; conferido visualmente na URL nova, sem erro de JavaScript.

## §85 · Monitor de risco: "Última atualização" sai da grade, ONI explicado, mapas de fogo e CEMADEN sem clique · 17/09/2026

Pedido direto da editoria, cinco partes.

**"Última atualização" sai da grade de "Situação atual"** e passa a viver abaixo da Figura 1 (o ONI), fora da moldura da figura (regra estrutural do site: uma `<figure>` só carrega título, legenda e crédito — o texto novo mora logo depois dela), em letra menor (`.note`).

**A observação da Figura 1 explica o que é o ONI**, não só o número do trimestre: "O ONI mede a anomalia da temperatura do mar na região Niño 3.4: valores acima de zero indicam El Niño, abaixo indicam La Niña." antes dos números do dado. No caminho, dois ajustes por causa dos portões: a frase original ("valores positivos/negativos") disparava o léxico avaliativo do portão de voz (que trata "positivo/negativo" como juízo, não como sinal matemático) — reescrita para "acima de zero / abaixo de zero"; e o texto passou de 243 para 206 caracteres, dentro do teto de 240 que o portão de legendas já impunha.

**Mapas de foco de calor (INPE) e alertas do CEMADEN saem do "Ver mais"** — a página tinha os dois atrás de um `<details>`/clique; agora ficam na mesma grade dos outros dois mapas ("Seca observada" e "Avisos meteorológicos"), os quatro visíveis de uma vez.

**Conferido, não alterado — mapas e cores já estavam corretos.** Os cinco mapas da página têm dado real nos 27 estados na fonte (`data/sinais_risco.json`); o que parece "vazio" em alguns estados é o extremo baixo da escala de cor (0 focos, 0 alertas), não a cor distinta de "sem coleta até o corte" — nenhum estado cai nessa categoria hoje. As cores de todos os gráficos (exceto o ONI, que é deliberadamente vermelho/azul/preto para imitar os sites oficiais, pedido de sessão anterior) já vêm de `MonitorMapas.PALETA`, a paleta semântica única do site.

Suíte inteira verde (21 verificações) depois dos dois ajustes; cadeia de derivados regenerada em árvore limpa; conferido visualmente, sem erro de JavaScript.

## §84 · Gráfico do ONI no padrão dos sites oficiais: fundo preto, vermelho e azul com transição · 17/09/2026

Pedido direto da editoria: o gráfico da série ONI, no Monitor de risco, virou uma linha única numa cor só, sem contraste com El Niño (vermelho) e La Niña (azul), sem lembrar o padrão que os sites oficiais (NOAA/CPC) usam.

Reescrito: virou gráfico de barras (uma por trimestre), fundo preto (`#wrapOni`, escopado só a essa figura — o resto do site continua claro), vermelho acima da média e azul abaixo, com a opacidade de cada barra crescendo com a intensidade da anomalia — mais transparente perto de zero, mais saturada nos picos. É a mesma lógica de transição contínua por valor que os medidores do MARÉ já usam (o degradê da barra de progresso), adaptada de "largura de uma barra só" para "opacidade de cada barra de uma série". Animação ligada nesta figura especificamente (as demais da página não animam, por padrão de performance) para dar o movimento pedido.

Cores e leitura do parágrafo abaixo do gráfico não mudaram. Suíte inteira verde (20 verificações); cadeia de derivados regenerada em árvore limpa; conferido visualmente, sem erro de JavaScript.

## §83 · Calendário vai para o fim da home; ponderação populacional citada na abertura; frase solta some do medidor; ficha explica o índice de resposta · 17/09/2026

Pedido direto da editoria, quatro partes.

**Calendário e "Indique um documento publicado" trocam de lugar.** Calendário passa a ser a última seção de `<main>`. Portão de ordem da home atualizado para a sequência nova.

**Abertura**: "Cada plano encontrado soma ao índice abaixo" perde o "abaixo" e ganha "com ponderação pela população coberta" — conferido contra `recalcular_mare.py`: cobertura populacional é de fato um dos três componentes de peso igual do índice (instrumento estadual, cobertura populacional, antecipação), não uma explicação nova.

**A frase "5 estados publicaram plano feito para este ciclo. 16 mantêm o plano de todo ano. 2 sem plano localizado." sai do medidor "Antes"** — HTML e a lógica JS que a calculava, removidos (as três variáveis não eram usadas em mais nenhum lugar).

**Ficha "Como ler o MARÉ Legal": a seção "O índice de resposta" ganha a explicação direta do número** — "O número vai de 0 a 100 e é a parcela da população nos municípios sob decreto de emergência desde 29 de junho", no mesmo padrão explícito que a seção da antecipação já tinha ("A nota vai de 0 a 100, em quatro faixas..."). Antes, a seção dizia o que o índice contava, mas não dizia explicitamente o que o número em si significa.

Suíte inteira verde de primeira (21 verificações); cadeia de derivados regenerada em árvore limpa; conferido visualmente, sem erro de JavaScript.

## §82 · Limpeza da home: cruzamento removido, glabels e contador de tempo saem, legendas descritivas, fontes do calendário com link · 17/09/2026

Pedido direto da editoria, com nove partes.

**Removida a figura "Risco projetado × o que cada estado publicou"** (painel inteiro) da home. Rastreei as três outras páginas que dependiam dela: `defesa-civil.html` tinha um card resumo apontando para lá (removido, estático + JS); `proteja-se.html` tinha um link para lá dentro de uma frase (reescrita sem o link); `assets/js/sinais-de-risco.js` tinha um resto de código morto de uma migração de 15/09 (removido).

**"como ler o MARÉ" → "como ler o MARÉ Legal"**, em todo lugar (link, `<h2>` da ficha, `aria-label`). Conferido em Saúde: já dizia "MARÉ Saúde" em todo lugar equivalente.

**Os dois glabels dos medidores removidos** ("Antecipação · o índice do MARÉ Legal / média.../ corte..." e o da Resposta) — o corte passa a aparecer uma única vez, no cabeçalho.

**O parágrafo de interpretação e o contador de tempo saíram do medidor "Depois".** A frase sobre a suspensão eleitoral de transferências (exigência de conformidade já estabelecida no site, "frase C18") não podia simplesmente sumir da home — movida para a ficha "Como ler o MARÉ Legal", na seção "O índice de resposta", onde a informação continua acessível.

**Três legendas reescritas** para descrever o que o leitor encontra: "Sua cidade" (o que a busca retorna: documento, data e fonte se houver plano; decreto se houver; nível de verificação se não), "Onde cada estado está" → **"O MARÉ Legal por estado"** (o que cada cartão mostra), "Calendário" (idem, com o link de volta para `calendario-eleitoral.html` reintroduzido — tinha sumido junto com o parágrafo removido do medidor "Depois", e um portão já cobria essa porta).

**As fontes do calendário viram link de verdade.** Descoberta no caminho: dois dos quatro prazos que aparecem na tabela (as MPs 1.367 e 1.384) já tinham URL de fonte registrada em `data/marcos_prazos.json` — só nunca eram usadas pela função que desenha a tabela. Completei os dois que faltavam (as duas entradas da ADPF 743, com o link oficial de acompanhamento processual do STF) e reescrevi a função em `assets/js/index.js` para virar link sempre que houver URL, texto puro quando não houver. Os quatro marcos fixos (`data/marcos_ciclo.json`) ganharam URL pela primeira vez: TSE, Planalto (Lei 9.504/1997) e o Boletim nº 1 do Painel El Niño no INMET.

**Achado no caminho: erro factual no calendário.** "Primeiro turno das eleições municipais" em 04/10/2026 estava errado — 2026 é ano de eleição geral (presidente, governadores, senadores, deputados), não municipal. Corrigido.

**Referências metodológicas usam "MARÉ Legal"/"MARÉ Saúde", não "MARÉ" solto**, conforme já valia no resto do site (proteja-se.html corrigido no mesmo lote).

Cinco portões quebraram no caminho — todos por dependerem de elementos ou textos que este pedido removeu ou renomeou de propósito (o link "como ler o MARÉ", a própria figura de cruzamento, o card resumo em Defesa Civil, a ordem de painéis da home, as listas do fallback estático §78) — todos corrigidos para refletir a nova realidade da página, não revertidos. Suíte inteira verde (21 verificações); cadeia de derivados regenerada em árvore limpa; conferido visualmente em tela cheia, sem erro de JavaScript.

## §81 · "Medida de Antecipação" sobrevivia em 10 das 11 páginas; confirmado direto no domínio publicado; portão novo · 17/09/2026

Patricia disse, pela segunda vez, que não via o marcador temporal nem os ajustes de linguagem nas demais páginas. Da primeira vez, verifiquei só localmente e assumi que estava tudo certo — dessa vez fui direto ao domínio publicado buscar prova, e a prova encontrou um erro real.

**Como confirmei**: sem acesso de rede direto a monitorelnino.com.br daqui, usei o mecanismo que já existe (`verificar_publicado.yml`, que tem a senha do domínio como segredo do GitHub Actions) para buscar o HTML publicado de verdade e procurar pelos textos específicos. Descoberta: o marcador temporal **está** publicado, correto, nas duas páginas (home e Saúde) — mas `saude.html` ainda trazia **"Medida de Antecipação"** no subtítulo do cabeçalho.

**A causa**: o §79 (busca e substituição do nome) usava correspondência de string simples — e o subtítulo do masthead é `<p class="mast-sub">Medida de Antecipação e Resposta ao <em>El Niño</em></p>`, com uma tag `<em>` bem no meio da frase. Uma busca simples não vê a string como o leitor vê; só achei e corrigi esse padrão na home, quando reescrevi aquele trecho por inteiro no §4 — nunca apliquei a mesma correção, com essa mesma tag, às outras 10 páginas, que compartilham o mesmo masthead. Uma varredura sem remover as tags primeiro não pega esse tipo de erro; foi assim que passou pelas minhas checagens de antes.

**Corrigido**: as 10 páginas restantes. Conferência final, ampla, removendo tags antes de buscar, em três frentes (nome antigo, "MARÉ · Defesa civil", "aviso federal", travessão no cabeçalho) — nada mais sobrou.

**Portão novo, em `verificar_estrutura.js`**: para toda página do pacote, remove as tags e confere que "Medida de Antecipação" e "MARÉ · Defesa civil" não sobrevivem — pega exatamente esse tipo de erro (string partida por tag), que uma busca ingênua deixa passar. Teste negativo executado (reintroduzido o padrão exato que causou o bug) e revertido com segurança.

Lição registrada: quando alguém relata, pela segunda vez, que não vê uma mudança que eu já verifiquei, o próximo passo é ir buscar prova direto na fonte, não checar de novo do mesmo jeito e confiar de novo.

## §80 · Paridade de Saúde com a home: medidor "Depois" compacto e contador de tempo · 17/09/2026

Patricia perguntou por que não via o marcador temporal nem as mudanças da Saúde depois do §79. Conferido: o handover de identidade (§79) tinha o §4, com o texto exato do contador de tempo e do medidor compacto, escrito só para `index.html` ("A página inicial, texto completo e definitivo") — não pedia essas duas peças para `saude.html`, e por isso não foram implementadas lá. A instrução "os dois têm a mesma anatomia" do §2 falava do nome (MARÉ Legal / MARÉ Saúde), não das duas peças visuais novas.

Como o princípio de paridade é real e a página de Saúde já espelha a home em quase tudo (dois medidores, mesma estrutura), levei as duas peças novas para lá agora:

- Selos "1 · Antecipação · o índice" / "2 · Resposta · o índice" viram "Antes: preparação publicada" / "Depois: emergências declaradas", no mesmo padrão da home.
- Medidor de resposta sanitária ganha a variante `.gauge-zone--compacta`; rótulo "Resposta, um índice separado. Não soma ao de antecipação."
- Contador de tempo (variante Leve, mesma da home): "Semana {n} desde a publicação do primeiro boletim. {n} secretarias de saúde publicaram plano feito para este ciclo desde então" — calculado de `monitor_saude.json`, não escrito à mão. A semana sai 10 na Saúde e 11 na home porque os cortes das duas fontes são datas diferentes (05/09 e 10/09); não é inconsistência, é o corte de cada fonte.
- Fallback estático (§78) estendido aos dois campos novos (`ctSemanaSaude`, `ctNovoSaude`), e o portão que evita "—" no HTML sem JavaScript passa a cobrir os dois.

Sobre o marcador temporal não aparecer na home: verifiquei o elemento (`#contadorTempo`) na árvore local — está presente, visível, com o texto correto, sem erro de JavaScript. Não consegui inspecionar o domínio publicado diretamente (fora da lista de rede permitida); se ainda não aparecer depois de um recarregamento forçado (Ctrl+Shift+R), pode ser cache do navegador — aviso se persistir.

Suíte de portões verde de primeira depois da mudança; cadeia de derivados regenerada em árvore limpa.

## §79 · Nome vira Monitor, MARÉ Legal restaurado, travessão sai da prosa; home reescrita por inteiro · 16/09/2026

Handover de identidade e linguagem, que **substitui** a decisão D1 de §76 (que tinha removido "MARÉ Legal") e **estende** `docs/VOZ_EDITORIAL.md` com um quarto hábito a evitar.

**§1 — o nome por extenso.** "Medida de Antecipação e Resposta ao El Niño" vira "Monitor de Antecipação e Resposta ao El Niño" — 64 ocorrências em 11 páginas, JS, seis geradores Python, `CITATION.cff`. Em `METODOLOGIA.md`, só as seções de definição corrente mudaram; o "Complemento de 15/09/2026", que registra uma troca de nome anterior, ficou intacto — é histórico datado, não definição viva — e ganhou uma linha nova no próprio "Histórico de nomenclatura" registrando a mudança de hoje.

**§2 — MARÉ Legal volta a existir.** Reverte só o D1 de §76; as demais reescritas daquele handover (fichas, glossário, remoções de lei e de LAI) continuam valendo. O portão de voz (`verificar_legendas.js`) parou de proibir e passa a **exigir** o termo na navegação e "MARÉ Saúde" no h1 da Saúde.

**§3 — travessão sai da prosa.** Quarto hábito documentado em `docs/VOZ_EDITORIAL.md`: nenhuma prosa do site usa "—" como pontuação de frase (vírgula, ponto ou duas frases, no lugar). Não afeta "·" nem o hífen sem espaço em intervalos ("2019–2025") ou palavras compostas. 41 ocorrências corrigidas em todo o site — a maior parte em templates JS compartilhados por várias páginas (a lista "O que a lei deixa aberto", usada em três páginas ao mesmo tempo, valia 14 sozinha) e no conjunto de Financiamento (12, incluindo dois escondidos dentro de dados, não de template: `assets/js/financiamento.js` e `data/calendario/dispositivos.json`). Onde o travessão morava no PRÓPRIO dado gerado (`data/saude_sinais.json`), corrigido também na fonte (`coletar_saude.py`), para não voltar na próxima coleta. Portão estendido: cobre `figcaption`/`dd` além do que já verificava, e vale mesmo dentro de ficha/bloco legal (que só ficam de fora das checagens de conteúdo, não das de estilo de frase). Teste negativo executado dentro de uma ficha e revertido.

**§4 — a home, reescrita por inteiro:**
- Abertura em dois parágrafos com o texto exato do handover; no caminho, achei e corrigi uma última menção a "Medida" que tinha escapado do §1 por estar quebrada por uma tag `<em>` no meio.
- Medidor "Antes": rótulo "o índice do MARÉ Legal"; uma função JavaScript **órfã** (`interpAntecipacao`) que já existia no código mas não tinha elemento correspondente no HTML, e por isso nunca executava, ganhou o elemento e o texto exato do handover (três números: plano feito para o ciclo, mantêm o plano de todo ano, sem plano localizado).
- Medidor "Depois": variante compacta nova (`.gauge-zone--compacta`, em `assets/base.css`) — mesma largura do medidor de cima, número e barra menores, sem marcações de faixa. Texto e interpretação reescritos.
- Contador de tempo, componente novo: "Semana {n} desde a publicação do primeiro boletim. {n} estados publicaram plano feito para este ciclo desde então", calculado de `meta.json` e `indice.json`, sem número escrito à mão. Variante **Leve** é a que foi ao ar; protótipo da variante **Média** (número da semana em corpo maior) foi construído, testado e comparado por screenshot, não ficou no ar. A variante "Com traço" (miniatura de série semanal) fica de fora por ora — reconstruir o histórico a partir do feed é trabalho de dados que não confirmei ser viável nesta rodada.
- Ficha "Como ler o MARÉ Legal": "O contador de decretos" renomeado para "O índice de resposta" (nome do handover); a lista de órgãos que publicam os boletins (Inmet, Cemaden, Inpe, ANA, SGB, Sedec) entrou no fim da ficha, onde não estava.
- Rodapé com o nome completo atualizado.

**§5 — propagação.** "Aviso federal"/"aviso" em referência ao Boletim nº 1 corrigido para "boletim"/"primeiro boletim" em Saúde e Imprensa, além da home.

Dois portões quebraram no caminho por dependerem de texto exato que mudou hoje — a ordem canônica da navegação (`verificar_estrutura.js` ainda citava "MARÉ · Defesa civil") e um teste de maiúscula em financiamento — os dois corrigidos. Suíte inteira verde (21 verificações); cadeia de derivados regenerada em árvore limpa; screenshots de desktop e 390px conferidos visualmente.

## §78 · Fallback estático completo: medidor de resposta e datas de corte sem JavaScript · 16/09/2026, prioridade crítica

Handover urgente: o medidor de **antecipação** de `index.html` era preenchido no HTML estático a cada rodada (`recalcular_mare.py`), mas o medidor de **resposta**, o corte no cabeçalho, a data de última verificação e uma das duas datas do rodapé não eram — ficavam `—`, ou pior, com uma data velha (`26/08/2026`, hardcoded, um mês desatualizada). Qualquer leitor sem JavaScript, leitor de tela ou indexador recebia isso. Verificado antes de corrigir: achado confirmado, lendo `main` sem JS.

**`preencher_fallback_estatico.py`** (novo): lê os mesmos arquivos que `assets/js/*.js` já lê em runtime (`data/resposta/por_uf.json`, `data/monitor_saude.json`, `data/saude_uf.json`, `data/financiamento/rotas_preventivas.json`, `data/meta.json`) e escreve os mesmos números e frases no HTML estático, com a mesma fórmula — não reinventa texto. Preenche 8 campos em `index.html` (medidor de resposta completo: número, barra, selo, `aria-label`, interpretação; corte do herói; as duas datas do rodapé, incluindo a remoção do `26/08/2026` fixo), 9 em `saude.html` (os dois medidores, antecipação e resposta sanitária, por inteiro) e 2 em `financiamento.html`. Idempotente — testado rodando duas vezes seguidas, hash idêntico na segunda. Chamado por `atualizar.py` como último passo antes da regeneração dos PDFs.

**Defesa civil e Calendário eleitoral**: conferidos e não têm campo equivalente no cabeçalho (usam mapas e tabelas para a resposta nacional, não medidor; nenhum "corte" solto no masthead) — nada para corrigir nessas duas.

**Portão novo, em `verificar_runtime.js`**: lê o arquivo bruto, sem jsdom nem JavaScript — os testes de runtime existentes conferem o DOM *depois* que o JS já rodou, o que não prova nada sobre o fallback estático (o próprio JS já teria sobrescrito um "—" àquela altura). Confere, nas três páginas: nenhum campo de dado com "—"/vazio/`null`; os grupos de datas que representam o mesmo corte são iguais entre si; `respFill` não fica em zero a menos que o índice de resposta seja mesmo zero. Teste negativo executado (forçar `respNum` de volta a "—", confirmar que o portão barra) e revertido com segurança.

Suíte inteira de portões verde (20 verificações); cadeia de derivados regenerada em árvore limpa.

## §77 · Fichas "Como ler" saem de duas colunas quebradas ao meio; parágrafos reordenados para leitura humana · 16/09/2026

A pedido da editoria: as fichas ("Como ler o MARÉ", "Como ler o MARÉ · Saúde", "Como ler as rotas", "Como ler o dinheiro preventivo") tinham parágrafos longos o bastante para acionar o colunamento automático (`assets/colunas.js`, regra de 07/09: texto com 320+ caracteres vira duas colunas em telas largas) — e uma frase quebrada ao meio entre duas colunas atrapalha a leitura, ainda mais numa ficha que existe para explicar o site.

**Duas correções, não uma só:**
- `assets/colunas.js` não aplica mais a regra dentro de `dialog` nem de `[data-voz="ficha"]` — as fichas ficam sempre em coluna única, qualquer que seja o tamanho do texto.
- Os parágrafos mais densos foram reordenados, não só encurtados: "O que o índice conta" (home) e "O que conta" (Saúde) viraram dois parágrafos curtos cada, um por ideia. Os dois glossários de Financiamento ("Chaves de acesso", "Termos" e as "Três chaves de preparação") viraram listas de definição (`<dl class="lista-definicao">`) — um termo, uma explicação, sem disputar linha com os vizinhos.

Nenhum conteúdo mudou; só a ordem e a moldura. Suíte de portões inteira verde; cadeia de derivados regenerada em árvore limpa.

## §76 · A voz editorial fora das legendas: fichas, subtítulos, aberturas e notas em todo o site · 16/09/2026

A regra de `docs/VOZ_EDITORIAL.md` valia para legendas de figura; o handover de 16/09 a estende ao resto da prosa das páginas de dados. Três decisões da editoria, por delegação:

- **D1 — "MARÉ Legal" sai.** O índice principal passa a ser **"MARÉ · Defesa civil"** na barra, nos títulos e nos cartões ("Legal" é marca jurídica, contra a decisão de 15/09 de tirar linguagem jurídica da comunicação). 21 ocorrências em 17 arquivos — HTML, JS, dois portões, o gerador da saúde e METODOLOGIA; o CHANGELOG fica como histórico.
- **D2 — A frase de identidade** ("verificação independente, em fontes oficiais…") aparece **uma vez**, no masthead da home. Saiu do subtítulo da saúde e do rodapé das 11 páginas.
- **D3 — Traço vazio em frase corrida** vira "sem coleta até {corte}" com a data real.

**Fichas reescritas por inteiro** (home e saúde) no texto do handover: descrevem o que o índice conta, o que não conta, o contador de decretos, o que é "sem plano localizado" e "ainda não verificado". Antes de escrever a da saúde, conferi o gerador na `main`: é a v0.3, com três componentes de pesos iguais — texto e código dizem a mesma coisa.

**Subtítulos, aberturas e notas** reescritos em home, Monitor de risco, Defesa civil, Saúde, Financiamento, Calendário e Pesquisadores. Saem: "a única porta aberta", "A única rota do país", "A faixa sombreada é a lei, não a inação", "Único estado com fundo", "Só a primeira é atribuível à lei", "peso zero" fora das fichas, artigos de lei na narrativa, o "carregando…" e as menções a pedidos de LAI (decisão de 03/09: LAI não aparece no site).

**Glossário de tela aplicado** (~40 substituições, quase todas em Saúde): "canal endêmico" → "faixa esperada para a época"; "painel amostral (313 municípios)" → "313 municípios acompanhados"; "última SE" → "última semana consolidada"; "escada da §7/§9" → "categoria do plano"; "instrumento ex-ante" → "plano publicado"; "arcabouço público" → "o que estados e municípios publicaram antes". Pesquisadores mantém os termos técnicos (é a página de provas).

**Portão de voz estendido** (`verificar_legendas.js`): sai de "legendas" e passa a percorrer toda a prosa das 7 páginas de dados — `p`, `li`, `dd`, `summary` e o conteúdo das fichas/dialogs —, com sete checagens do texto corrido (ênfase "só/única/nunca/sempre", interrogação, artigo de lei, "denuncia/expõe", o site falando de si, processo narrado, traço vazio) mais o glossário. Duas exceções declaradas no HTML: `data-voz="ficha"` (onde a ressalva metodológica mora) e `data-voz="lei"` (blocos cujo conteúdo É a lei: FAQ da Imprensa, blocos legais do Calendário, rotas do fogo). Cobertura passa de 987 para 1.055 textos. Os três testes negativos do handover foram executados e restaurados.

**Quatro portões pediam as frases que o handover mandou tirar** e foram atualizados para a redação nova, preservando o que cada um protegia: os dois de sinais (agora exigem "reproduzidos dos órgãos" e "não entram na nota"), o da resposta (a frase do defeso continua obrigatória, sem citar o dispositivo) e o do fogo (a lacuna continua declarada, agora com a data do corte). A metadescrição da saúde foi encurtada para caber no limite de SEO.

## §75 · "O que mudou" sai da Imprensa · 16/09/2026

A pedido da editoria: a seção "O que mudou desde [data]" (lista do feed nacional, `listaMudou`) saiu da página. Código morto correspondente removido de `assets/js/imprensa.js` — a leitura de `feeds/brasil.xml` e o cálculo de `relDataAnterior` (que só alimentavam essa seção).

## §74 · Imprensa reconstruída na voz descritiva; portão de voz cobre a prosa da página; duas correções de atualização · 16/09/2026

A pedido do handover de 16/09: a página estava tecnicamente correta mas editorialmente errada — abria com juízo, explicava a política do site, avisava o leitor sobre o que não concluir. Reconstruída ponto a ponto na regra de `docs/VOZ_EDITORIAL.md`.

**Release**: quatro parágrafos, todos os números lidos do dado (nenhuma contagem escrita à mão, além de 27, 5.571, 29 de junho e 26 de outubro), sem adjetivo, sem "só/apenas", sem interrogação, sem artigo de lei, sem frase que explique o site. Campo vazio omite a frase inteira, nunca imprime "—".

**Campos novos em `assets/js/imprensa.js`**: `relReconhecidos`, `relPrimeiroDecreto`, `relPopMilhoes`, `relSuspensas` (`calendario/fontes_suspensas.json`), `relDataAnterior` (sete dias antes do corte — proxy declarado, não há registro do corte anterior). `relQ1`/`relQ3` (estados com índice ≥ 50 ou < 50, e mais de 5% dos municípios sob decreto) **ficam como contagem agregada, nunca nomeando qual estado** — o handover original media índice × decreto por UF como o `resposta/quadrantes.json` já removido em §73; mantive o espírito (o cruzamento) sob a regra que já vale para o resto do site (§73): sem posição nomeada.

**Estrutura**: "O que mudou" retitulado com a data da edição anterior; "O que o MARÉ mostra" (capacidade, sem "inédito"/"pela primeira vez"); "Como ler" com uma linha e link para a ficha da home (a lista antiga de ressalvas saiu — mora na ficha); FAQ reduzido a seis perguntas de fato sobre a lei (única parte da página onde citar artigo é o próprio conteúdo); "Como citar" simplificado a uma frase-modelo + licença; "Calendário" compacto (`marcos_ciclo.json`); "O que a lei deixa aberto" em duas colunas — não suspenso e suspenso, este último novo, lido de `dispositivos.json` (itens sem descrição de bloqueio na fonte ficam de fora da lista, não aparecem como traço vazio).

**Duas correções de atualização encontradas na conferência:**
- O `aria-label` do medidor do herói (`index.html`) já era reescrito por `recalcular_mare.py` desde 03/09 — o handover estava desatualizado nesse ponto. Reforcei mesmo assim: `verificar_runtime.js` ganha um teste de paridade entre `aria-label` e `data-alvo`.
- `data/marcos_ciclo.json` citava "Monitor El Niño Brasil" (nome anterior à troca de marca de 06/09, §56) num campo `fonte`; corrigido para "MARÉ".

**Portão novo — `verificar_legendas.js`, prosa da Imprensa**: a mesma regra das legendas (léxico avaliativo, interpretativo, causal, teto probatório) mais quatro checagens da prosa corrida — "só/apenas" como juízo, interrogação, artigo de lei fora do FAQ e da nota do defeso, "denuncia/expõe". Teste negativo executado e restaurado. No caminho, um bug real: a checagem de "só/apenas" usava `\b`, que não reconhece fronteira de palavra em "só" (o "ó" não é `\w` em regex JavaScript sem a flag Unicode) — nunca teria pego o próprio caso que a motivou; corrigido.

Pendente para a rodada seguinte (explicitamente adiado pelo handover): cartão social por página (§2.2).

## §73 · Removida toda comparação/ranking entre municípios e estados — nota, saúde, resposta e financiamento · 16/09/2026

A pedido da editoria, no MARÉ Legal e em qualquer outra página que comparasse um município ou estado contra outro ou contra uma média: o índice mede o que cada um publicou, sozinho — nunca a posição que ocupa frente aos demais.

**MARÉ Legal (assets/js/index.js):**
- Removida a frase "X pontos acima/abaixo da média nacional (Y/100)" do card de busca de cidade, e a equivalente no relatório em PDF baixável.
- Removido o traço e o rótulo que marcavam a média nacional em cima da barra de **todo** medidor do site (`miniGauge()`, usado no herói, no detalhe do estado, na busca de cidade e no índice de resposta) — CSS morto (`.gauge-avg`, `.marca-media`) também removido.
- Removido o cálculo de posição no ranking e dos estados vizinhos (`ORDEM_MARE`), nunca renderizado mas presente no código.
- O cartão "Brasil (média nacional)", que ocupava o lugar do detalhe do estado antes do clique, virou só a instrução — sem nota nacional na mesma coluna onde um estado é mostrado.
- Quatro mensagens de resultado vazio ("X pontos abaixo/acima", "não significa que X") reescritas como afirmações diretas (ver §72).

**Defesa civil:**
- O título do mapa de decretos não nomeia mais o estado com a maior fração de municípios sob decreto.
- A tabela "Decretado × reconhecido, por estado" passa a ordem alfabética (era por número de municípios sob decreto).
- Removido o trecho de texto ("quadrante crítico") que cruzava a nota do índice com a fração sob decreto para nomear estados especificamente.
- `data/resposta/quadrantes.json` parou de ser gerado — existia só para essas duas comparações (e para um gráfico de dispersão já removido em 15/09, §59); `gerar_resposta.py` limpo.

**Imprensa:**
- O release não nomeia mais os dois estados com maior e os dois com menor nota ("As notas vão de X a Y"); cálculo removido de `imprensa.js`.
- FAQ "Há ranking?": resposta reescrita — "Não. Cada estado mostra a própria nota e os próprios componentes; não há lista por posição nem comparação entre estados."

**Pesquisadores e Financiamento:**
- Removido o gráfico de barras "Pago por UF" (rotulado "ranking por UF da unidade gestora") em Pesquisadores — o mapa geográfico ao lado mostra o mesmo dado sem ordenar por posição.
- Removido código morto em `financiamento.js` e `saude.js` que também ordenava estados por valor (decretos, prontidão sanitária) sem nunca renderizar — mesmo tipo de comparação, mesmo risco latente.

**Documentação técnica (`MARE_Indice_Documentacao.pdf`):** o anexo de robustez (§5.8) tinha uma tabela UF a UF com "rank mediano" e intervalo — mesmo rotulada "não é produto público", ainda seria uma posição extraível de um PDF público. Substituída por um achado agregado (amplitude média e máxima da posição sob perturbação, nenhuma UF nomeada), que sustenta a mesma conclusão metodológica (a v2.2.3 não publica ordinal) sem expor posição de nenhum estado.

Peso e cálculo do índice inalterados; nada muda na nota de nenhum estado ou município. Escopo é onde e como essas notas são mostradas.

## §72 · Voz editorial revisada no site inteiro: legendas descrevem, não corrigem o leitor; regra fixada em docs/VOZ_EDITORIAL.md · 16/09/2026

A pedido da editoria, na sequência do §71: a mesma pergunta feita sobre uma legenda específica ("por que isso está aqui?") aplicada ao site inteiro — HTML e JavaScript.

**O padrão corrigido, em três formas:** (1) legendas que explicavam a política editorial do site ("achar os planos é tarefa do Monitor, não das prefeituras") em vez do conteúdo; (2) avisos preventivos sobre o que o leitor não deve concluir, repetidos em cada legenda ("peso zero; o Monitor não atribui casos ao El Niño", 5× em saude.html); (3) "nunca"/"sempre" usados como ênfase retórica onde a frase já era clara sem eles.

**Imprensa** — reescrita ponto a ponto: hero, release, os 7 cartões do FAQ, frase citável, contato. Nenhuma resposta abre negando ("Não.") antes de informar; cada uma diz o fato direto.

**MARÉ Legal e MARÉ Saúde** — fichas "Como ler" e "O que mede" com a mesma ressalva dita uma vez, não repetida; a legenda do formulário "Indique um documento publicado" reescrita sem a frase de divisão de responsabilidade. Nos dois lados (MARÉ Legal e MARÉ Saúde), "as duas [antecipação e resposta] nunca se combinam num número" vira "mostradas separadamente" — mesma informação, sem tom de regra.

**JavaScript** — quatro mensagens de resultado vazio (busca por cidade, município prioritário) que diziam "isso não significa que X" viram afirmações diretas do que foi ou não publicado, sem a moldura de correção.

**Defesa civil, Para gestores, Pesquisadores, Proteja-se** — cada trecho identificado reescrito; a exceção documentada é instrução de segurança/ação nessas duas primeiras páginas, que é o conteúdo delas, não o vício.

**Fica documentado e verificado automaticamente:**
- `docs/VOZ_EDITORIAL.md` — a regra, os três hábitos a evitar, exemplos antes/depois, a exceção de Proteja-se/Para gestores, e o teste de uma frase antes de publicar. Linkado em Pesquisadores.
- `scripts/verificar_voz_editorial.js` — portão novo: se a mesma ressalva aparecer 3+ vezes nas legendas/notas de uma página, o portão bloqueia e aponta onde consolidar. Ligado ao workflow de PR.

## §71 · "Indique um documento publicado" migra para o fim do MARÉ Legal, com legenda que diz para que serve · 16/09/2026

Nenhuma alteração de método. Classe **estrutura de página** (pedido da editoria).

- O formulário sai de Pesquisadores e vira a última seção da página inicial (depois de "Risco projetado × estágio do arcabouço público", antes do rodapé) — mecanismo (Netlify Forms, lista de municípios por UF, degradação em prévia local) migrado inteiro, sem reescrever.
- **Legenda reescrita** para dizer com clareza o que o campo é e quando usá-lo: "Sabe de um município ou estado que tem plano publicado e o Monitor ainda não encontrou? Envie o documento oficial — com número, data e endereço em sítio público ou diário oficial — e ele entra na fila de verificação (...). Achar os planos publicados é tarefa do Monitor, não das prefeituras — mas qualquer pessoa pode ajudar a encontrar um que ainda esteja fora do nosso radar."
- Para gestores aponta para o novo endereço (`index.html#formulario`); portão de ordem da home (`verificar_runtime.js`) passa a exigir "indique um documento" como a última seção, depois do cruzamento risco × estágio. Teto de palavras da inicial: 950.

## §70 · Três portais estaduais corrigidos com evidência, não deixados como "decisão humana pendente" · 15/09/2026

Continuação do §69: a rodada de `verificar_links.py` sinalizou ~35 portais e documentos possivelmente quebrados; checar cada um contra uma fonte independente (diretório oficial do MIDR, busca) mostrou que a maioria é bloqueio de robô em site vivo (.gov.br devolve 403/erro de SSL/timeout a tráfego automatizado com frequência, confirmado comparando com sondas anteriores desta sessão que alcançaram os mesmos domínios). Três, porém, tinham evidência real — corrigidos em `data/contatos_uf.json` (fonte única; propaga a Proteja-se, Pesquisadores e ao mapa da inicial):

- **RR**: `bombeiros.rr.gov.br` estava fora do ar — um resultado de busca mostra o domínio devolvendo conteúdo alheio (spam), sinal de domínio expirado. A Defesa Civil de Roraima está hoje no site do Corpo de Bombeiros Militar: `cbm.rr.gov.br`.
- **PA**: o diretório oficial do MIDR nunca listou portal para o Pará; a URL usada (`defesacivil.pa.gov.br`) não existe. A Defesa Civil estadual está hospedada no site do Corpo de Bombeiros: `bombeiros.pa.gov.br/defesacivil/`.
- **MS**: `defesacivil.ms.gov.br` voltou a responder — revertida a URL alternativa (`ms.gov.br/Geral/defesa-civil/`) usada quando o domínio original falhava numa checagem anterior.

Erratas também: `assets/js/index.js` tinha um bug pré-existente na formatação do `tel:` de fallback (não removia parênteses/espaços do telefone quando a UF não tem portal — hoje só o RN).

**Mudança de critério, a pedido da editoria**: `verificar_links.py` não trata mais "link quebrado" como decisão automaticamente parada para revisão humana — o padrão agora é buscar confirmação independente e decidir; a intervenção humana continua reservada para os casos em que a evidência disponível não permite uma decisão segura.

## §69 · Auditoria editorial de Pesquisadores e Para gestores: dado inventado removido, duas listas de portais viram uma, verificador de links corrigido · 15/09/2026

Mesma pergunta feita para a Imprensa (§67–§68) — ordem, qualidade, links, atualidade — agora em Pesquisadores e em Para gestores.

**Pesquisadores — três achados de conteúdo:**
- **Errata: dado inventado.** O gráfico "Plano federal El Niño 2026/2027 por área" somava R$ 17,75 bi em quatro áreas digitadas direto no JavaScript, sem arquivo de origem — 13× o valor de todo o plano federal (R$ 1,335 bi) citado em qualquer outro lugar do site. Removido; os compromissos verificados, com fonte por linha, seguem em Financiamento.
- **Duas listas de portais das Defesas Civis, uma desatualizada.** A lista fixa em Pesquisadores dizia que AC, AM, PA, PB, RN e SP não tinham portal — defasada desde a correção de `contatos_uf.json` em Proteja-se (§57), que hoje só deixa o RN sem portal. Pesquisadores passa a ler o mesmo arquivo; as duas páginas nunca mais podem divergir do mesmo diretório oficial.
- **Reordenada** para começar pela orientação: "Como usar o site e os dados" sai do acordeão no fim da página e vira a primeira seção, visível; metodologia, dados abertos e código ficam agrupados logo depois; o material de referência mais denso (log de verificação, fontes, painel amostral) segue como estava.

**Para gestores:** auditoria não encontrou pendência — ordem (caminho → conteúdo do plano → recursos → período eleitoral → prioritários), links internos e atualidade conferem.

**`verificar_links.py` — dois bugs de cobertura corrigidos** (o portão só roda com rede real, fora do sandbox de edição; não fazia parte da pergunta de conteúdo, mas é o que sustenta a resposta a "os links funcionam"):
- Checava só 5 das 11 páginas — Saúde, Financiamento, Pesquisadores, Imprensa, Monitor de risco e Calendário eleitoral nunca tiveram os links externos verificados.
- A extração de URLs em JavaScript (portais, diários, guias) procurava `<script>` inline; a refatoração de CSP de 06/09/2026 moveu todo o JS para arquivos externos — a extração vinha devolvendo zero URLs, sem ninguém perceber, porque nada distinguia "nenhuma achada" de "nenhuma quebrada".
- User-Agent do verificador trocado por um formato educado (`Mozilla/5.0 (compatible; …)`) e GET como segunda tentativa: o formato anterior disparava bloqueio de robô (403/erro de SSL) em vários `.gov.br` que respondem normalmente a um navegador — confirmado comparando com uma sonda anterior desta mesma sessão.
- Rodada de verificação real, pós-correção: a maioria dos links confere; um punhado de portais estaduais e documentos municipais específicos segue instável entre rodadas (timeout ou erro de SSL, típico de servidores estaduais pequenos) — inclusive um caso com falha de DNS persistente (bombeiros.rr.gov.br). Regra do projeto: link nunca é removido automaticamente, decisão humana; a lista completa fica no relatório da rodada, para revisão.

## §68 · Imprensa: release jornalístico com os achados da edição, o período eleitoral em números, entregas e razões para abrir o Monitor; texto corrido, sem caixa · 15/09/2026

Nenhuma alteração de método. Classe **texto + estética** (pedido da editoria).

- **Release** reescrito a partir da notícia, não do projeto: título-fato ("Só N dos 27 estados publicaram um plano feito para o ciclo — e a lei eleitoral fechou a torneira…"), subtítulo com dimensão, e blocos "o que aconteceu", "o que o país aprende", "o período eleitoral tem impacto — e é medível", "o que a União prometeu", "como é feito", frase citável e serviço. Todos os números vêm do dado, ao vivo: média e faixa; estados por status (com siglas) e extremos da régua; planos municipais e diários varridos; MARÉ Saúde; transferências voluntárias antes do defeso (R$ bi) e nas semanas seguintes (R$ mi), data da última carga do TransfereGov; decretados, reconhecidos, primeiro decreto; pago das MPs.
- **O que se aprende com o Monitor — e o que ele entrega**: quatro cartões — cinco achados da edição (do dado), o período eleitoral em números, as entregas página a página, por que abrir o Monitor (leitor, gestor, jornalista, pesquisador). Substitui "O que o MARÉ traz de novo".
- **Estética**: sai a caixa azul de citação; o release é texto corrido em coluna única, com título e subtítulo próprios (`.release`, `.release-titulo`, `.release-sub`). Teto de palavras: 2.300.

## §67 · Imprensa reformulada: release da edição, o que o MARÉ traz de novo, FAQ na ordem do site · 15/09/2026

Nenhuma alteração de método. Classe **texto** (pedido da editoria).

- **Release** reescrito para a edição 2026/2027 — pela primeira vez a preparação pública para um El Niño anunciado tem medida independente, verificável e aberta; dois números que nunca se somam; todo o país um a um; período eleitoral na conta; MARÉ Saúde e Financiamento. Números lidos ao vivo do dado: média e faixa, estados com plano do ciclo, planos municipais localizados, municípios sob decreto e reconhecidos, MARÉ Saúde e UFs verificadas, corte. Frase citável nova. Lê-se em coluna única.
- **O que o MARÉ traz de novo**: quatro cartões (mede o que é conferível; dois números, nunca um; todo o país, um a um; reproduzível e aberto).
- **Perguntas frequentes na ordem do site**: um cartão por página — MARÉ Legal, Monitor de risco, Proteja-se, Defesa civil, MARÉ Saúde, Financiamento (com "o que a lei deixa aberto", do dado), Para gestores e Pesquisadores — explicando pouco a pouco; substitui os cartões "Mede / Não mede / Como ler / Teto" e a lista única de perguntas. Como citar, O que mudou e Contato mantidos. Teto de palavras: 1.700.

## §66 · "Para prefeitos" vira "Para gestores": o caminho até o plano publicado, o que o plano precisa conter, como pedir recursos; o formulário de indicação migra para Pesquisadores · 15/09/2026

Nenhuma alteração de método. Classe **estrutura de página + texto** (pedido da editoria: orientar o gestor na decisão; achar planos é tarefa do Monitor, não atribuição legal do município).

- Nome da página e do menu: **Para gestores** (prefeitos, secretários, coordenadores de proteção e defesa civil). Some o pedido para "enviar o plano ao Monitor".
- **O caminho até o plano publicado**: seis passos gráficos — ler o risco projetado; elaborar/atualizar o plano (Lei 12.608, art. 8º, XI); aprovar por ato numerado; publicar em endereço estável (dever legal, a lei eleitoral não suspende); manter o cadastro no S2iD; pedir o recurso pela rota certa.
- **O que o plano precisa conter**: conteúdo mínimo da Lei 12.340/2010 (art. 3º-A) e o que o Monitor verifica no documento (número/data/ato, menção ao ciclo ou ao risco, endereço estável, coordenador, saúde no plano), em duas listas de verificação.
- **Como pedir recursos**: antes do dano (regra, plano, PNMIF, estadual, direta) e depois do dano (decreto → S2iD → reconhecimento → pedido → CPDC; emergência setorial do SUS), com chips de chave e links para as rotas, o dinheiro preventivo por setor e a Defesa Civil do estado.
- Mantidos: "O que ainda é possível no período eleitoral" (do dado) e "Descubra se seu município é prioritário".
- O formulário "Envie um documento" (Netlify, `contribuicao`) migra para Pesquisadores como **"Indique um documento publicado"** — qualquer pessoa pode indicar; JS migra junto. Teto de palavras da página: 950.

## §65 · Financiamento: figura "Dinheiro para se preparar, por setor" (saúde · fogo · seca), com glifos de chave, nó de ausência e ficha · 15/09/2026

Executa o handover editorial "Dinheiro preventivo por setor" (§2.20). Nenhuma alteração de método (peso zero; portão impede o motor de ler o dado). Classe **figura + dado + ficha + portões**.

- Novo `data/financiamento/preventivo_setores.json`: 12 rotas em três faixas (saúde 3, fogo 4, seca 5) com origem (União · Estado · Fundos e doações), destino (Município · Pessoas · Obras e serviços), chave (regra · decreto · discricionária · direta), glifos (plano · risco · calendário · obra · crédito), base legal, situação no período eleitoral, objeto; as rotas do fogo reusam fonte e hash de `rotas_preventivas.json`; as demais ficam "fonte a verificar" até a leitura documental (sem fonte/hash inventados). Nó de ausência da seca: "(nenhuma) rota ao município ligada a plano e a nível de risco".
- Figura `#boxPreventivoSetor`: rede D3 com a gramática de `#boxRede` (traço = chave, glifos na aresta, tooltip com base legal e defeso, realce, teclado), título-fato do dado, alternativa acessível em lista de definição ("Ver em lista"), sem tabela. Paleta: `PALETA.setores`.
- Ficha "Como ler o dinheiro preventivo" (três chaves, três destinos, saúde, fogo, seca, o que a figura não diz), no mesmo popup das fichas da página. Os três mapas por setor entram quando os coletores tiverem dado (nota na página).
- Portões: `verificar_financiamento.py` (i)–(m) — campos obrigatórios por rota, chave/objeto válidos, fonte+hash quando verificada, zero `<table>`, `<dl>` presente, nó de ausência com enunciado restrito, motor não lê o arquivo; runtime — nós, ausência sem aresta, glifos na legenda, tooltip, lista, título-fato, ficha.
- METODOLOGIA §38-bis; FAQ da Imprensa ("Há dinheiro federal para se preparar sem decretar?"); Prefeituras aponta para a figura. Tetos de palavras: Financiamento 1.600, Imprensa 1.100.
- **Correção de portão pré-existente**: em `verificar_financiamento.py`, `checar()` relia o motor do disco e ignorava o texto injetado — o teste negativo "motor lendo financiamento" nunca acusava; passa a usar o parâmetro.

## §64 · Figuras lado a lado: grade de três colunas na Saúde e na Defesa civil; SRAG e SG em figuras próprias · 15/09/2026

Nenhuma alteração de método. Classe **estrutura de página** (pedido da editoria: otimizar o espaço, mapas e gráficos lado a lado).

- Nova grade `grade-figuras--3` (três colunas; uma no celular), com reserva de três linhas para título e subtítulo para que as três figuras alinhem.
- MARÉ Saúde: Dengue com as três figuras numa linha (mapa do painel, capitais, comparador); Chikungunya com mapa e comparador lado a lado; **Doenças respiratórias sem seletor: SRAG e síndrome gripal em figuras próprias, lado a lado** (mesmo renderizador, lacuna declarada quando a fonte não responde); "O que cada estado publicou" com os três mapas numa linha. Seletores dos comparadores passam para baixo da legenda (mídias alinhadas).
- Defesa civil: "Status dos planos estaduais" em largura total e os três mapas (verificação, cobertura/natureza, prioritários) numa linha; seletores de camada abaixo da legenda.
- Financiamento já estava no padrão (gráfico largo + dois mapas lado a lado); Monitor de risco idem (dois mapas lado a lado).

## §63 · Financiamento: cortes da editoria, gráfico dos compromissos no padrão, documento interno das rotas · 15/09/2026

Nenhuma alteração de método (peso zero). Classe **estrutura de página**.

- Saem: o painel "Por estado" inteiro (mapa de R$/hab. da rota 5, mapa de repasses/habilitação, barras de resposta por decreto), o mapa "Fundo a fundo estadual preventivo, por estado" (o gráfico do RS fica) e o mapa "Rota preventiva do fogo: área declarada · requereu · recebeu" — depende de resposta do MMA a pedido de acesso à informação; uma nota diz que o mapa entra quando ela vier; os cartões das rotas do fogo ficam.
- Gráfico "Compromissos federais para o ciclo" (título encurtado) na paleta de série das demais páginas, rótulos curtos; sai a nota sobre a execução do Portal. Texto de "As rotas do dinheiro" reduzido ao pedido pela editoria.
- Documento interno `notas/FINANCIAMENTO_rotas_do_dinheiro_interno.md` (robo-registro, anexo ao arcabouço legal): as oito rotas com base legal e o que o decreto destranca, a rota do fogo (PNMIF), o caminho antes/agora/depois, MPs e compromissos com execução, o caso do RS e a fila de pedidos.

## §62 · Financiamento elucidativo: rastreio dos compromissos, rotas em ficha com glossário, caminho antes/agora/depois, PNMIF como rota, o caso do RS, tabelas viram figuras · 15/09/2026

Nenhuma alteração de método (peso zero). Classe **estrutura de página + visualização** (pedido da editoria).

- **Rastreio dos compromissos federais**: gráfico "anunciado × empenhado × pago" para as duas MPs (1.367 incêndios; 1.384 alimentos, com execução lida dos arquivos mensais do Portal) e os cinco compromissos verificados (sem série de execução ainda: só a barra do anunciado, declarados "aguardando coleta"); dois mapas "onde o pagamento chegou" (valor pago por UF da unidade gestora, unidade nacional à parte). Atualiza a cada rodada com a carga do Portal.
- **Como ler as rotas** vira ficha em popup ao lado do diagrama: as cinco chaves de acesso definidas (regra · decreto · discricionária · direta · estadual), glossário (S2iD, FIDE, CPDC, ESPIN, FNMA, PNMIF, TransfereGov, MP), os oito cartões de rota com base legal e o que o decreto destranca, e a **rota preventiva do fogo (PNMIF)** como nona entrada (Lei 14.944/2024 + Lei 15.143/2025, FNMA art. 3º-A; edital FNMA/FDD; Fundo Amazônia).
- **O caminho do município: antes, agora e depois** — três cartões (antes de 04/07 · período eleitoral/início da janela do El Niño · depois de 25/10) com chips de chave por rota; substitui a tabela de coexistência, o "caminho da rota 3" e o "sem decretar".
- **Rota preventiva do fogo (PNMIF)** com seção própria: mapa em três camadas e um cartão por rota (quem pode, o que precisa, o que paga, valores, situação no defeso) no lugar da tabela.
- **O caso do Rio Grande do Sul**: gráfico "repasse preventivo (Prepara RS, 138 municípios, R$ 32,3 mi) × sob decreto × reconhecidos" ao lado do mapa do fundo a fundo; lacuna declarada — a aplicação município a município não está publicada na fonte, e a relação entra na fila de LAI à Defesa Civil do RS.
- Tabelas restantes viram figuras: R$/hab. da rota 5 vira mapa coroplético; resposta por decreto vira barras por UF (reconhecidos × sem reconhecimento); a tabela de compromissos sai (gráfico acima). Teto de palavras da página passa a 1.300 (ficha e caminho são texto estático).

## §61 · Errata: dengue nas capitais aparecia sem pontos (coordenadas ausentes); Pesquisadores aponta o MARÉ Saúde · 15/09/2026

- **Errata**: o mapa "Dengue nas capitais" projetava os 27 pontos em (0,0) — o registro das capitais traz código IBGE, não latitude/longitude — e ficava vazio. As coordenadas passam a vir da malha IBGE já carregada; pontos com tooltip (capital, nível, SE, fonte). Portão de runtime da Saúde exige os 27 pontos dentro do mapa.
- Pesquisadores › Metodologia ganha a linha do MARÉ Saúde (ficha na página; cálculo em METODOLOGIA §31).

## §60 · MARÉ Saúde espelha o MARÉ Legal: dois medidores, ficha "Como ler", uma seção por desfecho, cartões por estado · 15/09/2026

Classe **estrutura de página + método (peso zero)**. Metodologia §31 (ficha "Como ler o MARÉ Saúde"); FAQ da Imprensa ganha a pergunta "O que é o MARÉ Saúde?".

- Cabeçalho da página com a mesma definição da inicial, aplicada à saúde; sai o texto "Antecipação (o que os estados publicaram antes)…".
- **Dois medidores no topo**, na arte única: antecipação (média das UFs verificadas) e **resposta sanitária como índice** (`resposta` em `monitor_saude.json`: 100 × população dos estados com emergência sanitária declarada — ESPIN ou decreto estadual — sobre a população do país; hoje 0,0, com "0 emergências" na pílula). Sai a figura "Emergências sanitárias declaradas no ciclo" (era só um contador em cartão).
- **Ficha "Como ler o MARÉ Saúde"** em popup, com os mesmos campos da ficha da inicial (o que mede · o que não mede · teto da afirmação · resposta · o que o índice é).
- **Cada desfecho em seção própria, antes dos estados** — Dengue (mapa do painel, capitais, comparador semanal/acumulado/por capitais), Chikungunya (mapa e comparador próprios), Calor, Doenças respiratórias (SRAG/SG), Doenças diarreicas — nenhum em acordeão, sem seletor de doença; `renderDesfechos` parametrizada por contêiner.
- **Onde cada estado está**: 27 cartões como na inicial (micro-barra do índice no degradê único, barra de resposta, face com plano · cobertura · dengue na capital); clique abre o detalhe em janela (instrumento, componentes, resposta, risco projetado, dengue na capital). Sai o seletor "Escolha um estado" com os quatro cartões.
- Mapas de antecipação, status do instrumento e risco sanitário projetado seguem em "O que cada estado publicou", todos visíveis. Teto de palavras da página passa a 900 (a ficha e as cinco seções entram no texto estático).

## §59 · Defesa civil: três figuras a menos, errata do título-fato, municípios prioritários com fonte única e busca em Para prefeitos · 15/09/2026

Classe **estrutura de página + errata + fonte única**. Método inalterado; C20 (dispersão como única leitura conjunta) revogada — METODOLOGIA §32.5.

- Saem "Municípios com plano, declarado × documentado (PR · SC · RS)", "Antecipação × resposta · 27 estados" e "Municípios com primeiro decreto, por semana"; os fatos dos seus títulos vão ao parágrafo narrativo do "Depois". Texto do "Antes" reduzido ao que a seção mostra.
- **Errata**: o título "5.571 cidades passaram pelo registro federal; … 0 planos municipais localizados" somava um campo inexistente em `consist.json`; passa a somar `n_plano` de `percentual_uf.json` (157).
- Municípios prioritários: explicação abaixo do mapa (o que são; a lista do Cadastro é aproximação por população, não a oficial); `gerar_prioritarios.py` grava `data/municipios_prioritarios.json` (cadeia de derivados e rotina de atualização), lido pelo mapa e pela nova busca **"Descubra se seu município é prioritário"** em Para prefeitos (estado → município → está ou não na aproximação; com ou sem instrumento localizado).
- A tabela "Decretado × reconhecido" no "Ver mais" passa a ocupar a largura toda do painel.
- **Correção de dois bugs pré-existentes** achados ao testar: os títulos-fato de Defesa civil (§54) eram calculados antes de os dados chegarem (IIFE no carregamento) e nunca mudavam do texto original; e o portão que os checava fazia a contagem final antes desses testes, então nunca bloqueava. Agora os títulos são calculados ao fim de `__init()`, o portão cobre todos os testes, e os títulos foram encurtados ao teto de 100 caracteres da regra de legendas ("sem plano localizado", nunca "localizável").

## §58 · Proteja-se: cada número de emergência diz para que serve; a seção do órgão estadual deixa de se chamar "Quem chamar" · 15/09/2026

Nenhuma alteração de método. Classe **texto/serviço ao leitor** (correção da editoria: o cartão do órgão estadual não é número de socorro).

- Barra de emergência: sob cada número, a situação que ele atende — 193 Bombeiros (incêndio, resgate, afogamento, desabamento, pessoa presa ou ilhada) · 192 SAMU (emergência médica) · 199 Defesa Civil (risco antes do dano: rachadura, encosta, alagamento subindo, árvore ou poste prestes a cair, vistoria e abrigo) · 190 Polícia Militar (segurança das pessoas e do patrimônio) · 40199 alertas por SMS. A nota explica que o 199 aciona a Defesa Civil do município.
- A seção "Quem chamar no seu estado" passa a **"Defesa Civil do seu estado: para que serve e como falar"**: coordena as Defesas Civis municipais, informa alertas, boletins, planos, abrigos, ajuda humanitária e decretos, recebe pedidos de informação; não é socorro imediato — com a instrução explícita de ligar 199/193/192 em risco. Plantão 24 h continua no cartão onde o diretório o lista.

## §57 · Proteja-se humanizado com contatos oficiais por estado; cartão social com o nome novo; subtítulo em largura total · 15/09/2026

Nenhuma alteração de método. Classe **serviço ao leitor + arte + estrutura de página**.

- **Quem chamar no seu estado**: novo `data/contatos_uf.json` com os 27 órgãos estaduais de Defesa Civil — telefones, plantão 24 h, e-mail, expediente e portal — transcritos do diretório oficial do MIDR ("Defesa Civil nos Estados", atualizado pelo órgão em 11/09/2024, consultado em 15/09/2026). Cartão por estado (seletor em destaque + grade dos 27), telefones tocáveis (`tel:`), fonte no pé. Portais testados do runner: 17 com resposta 200; MS (endereço sem DNS) passa ao portal oficial do estado, PE e RR às formas com www do diretório, PB ganha a página oficial do governo, RJ passa a defesacivil.rj.gov.br; AM, DF, PA, RO, SC e TO não respondem ao runner fora do Brasil (bloqueio, não erro de endereço) e ficam como estão; RN segue sem portal dedicado. A lista de portais do cartão da cidade (inicial) passa a espelhar o mesmo arquivo.
- **Barra de emergência** com os cinco números nacionais (190 · 192 · 193 · 199 · 40199), tocáveis, numa só cor; o código de cores da página fica só com as três famílias de risco (chuvas · estiagem/calor · incêndios), nos mesmos tons do índice; saem as cores por região. Portão de runtime cobre os 27 cartões, o telefone de cada UF contra o dado e a barra.
- **Cartão social** (Open Graph/Twitter) regenerado por `scripts/gerar_cartao_social.js` com o nome MARÉ · Medida de Antecipação e Resposta ao El Niño e números lidos dos dados.
- **Cabeçalho**: subtítulo em largura total; o bloco "Fonte · UFs · Última verificação" desce para a linha seguinte.

## §56 · Nome do site, textos explicativos objetivos e em largura total, cortes na inicial, Monitor de risco reordenado · 15/09/2026

Nenhuma alteração de método. Classe **nome/texto/estrutura de página** (decisões da editoria, 15/09).

- **Nome**: o site passa a se chamar **MARÉ · Medida de Antecipação e Resposta ao El Niño** em todo lugar onde antes dizia "Monitor El Niño Brasil" — cabeçalho (h1 "MARÉ"), títulos, Open Graph, JSON-LD, rodapé, créditos de figura, PDFs, feeds Atom, dados abertos (datapackage/CITATION), selos e pedidos de LAI. Domínio, repositório e nomes de arquivo inalterados. O cartão social (`assets/social/card-monitor-el-nino.png`) ainda traz a arte antiga — pendência de arte.
- **Inicial**: saem a linha do tempo do herói, a linha de interpretação do medidor (contagens por categoria), a frase do art. 73 e o crédito da resposta (ambos passam para a ficha "Como ler o MARÉ", onde o portão os exige), a nota de escopo do índice de resposta e o complemento "— e o que sustenta a nota" do título dos estados.
- **Textos explicativos** (`.hint` e parágrafos de painel) em todas as páginas: largura total do painel (a medida de leitura de 68ch fica só na citação) e reescrita objetiva — descrevem o que a figura mostra, sem comentário sobre o site, instrução de uso ("clique", "passe o mouse") nem nota interna (as menções a migrações de 13/09 e à "proposta de enxugamento" saem do texto público).
- **Monitor de risco**: ordem 1 · Situação atual (ONI e prognóstico) · 2 · O risco projetado, estado a estado · 3 · O que está acontecendo agora; o gráfico "Estados por tipo de risco projetado" entra no mesmo quadro do mapa (figura dupla `.figura--dupla`: mapa e gráfico lado a lado, uma legenda, um crédito); o painel "Gráficos" deixa de existir.

## §55 · Saúde: títulos-fato do dado (auditoria editorial 14/09, onda E2 §2.10) · 15/09/2026

Nenhuma alteração de método. Classe **conteúdo**.

- MARÉ · Saúde: "Saúde: {n} estados com plano para o ciclo, {n} com o de todo ano, {n} em elaboração, {n} não verificados" (do `saude_uf.json`); mapa de status com a mesma contagem; contador "Emergências sanitárias declaradas no ciclo: {n}" com "nenhuma localizada até {corte}" quando zero; dengue/chikungunya: "{n} municípios em alerta laranja ou vermelho na semana SE {n} de 2026 (painel amostral)", recalculado ao trocar a doença. Interpretação fixa do InfoDengue ("o Monitor não atribui casos ao El Niño") fora da figura, no bloco "O que se observa" (portão 19). Títulos calculados após o carregamento; sem dado, o título original permanece. Runtime confere contra o dado; títulos dentro do teto de 100 caracteres do portão 19.

## §54 · Defesa civil: títulos-fato e interpretações do dado (auditoria editorial 14/09, onda E2 §2.9) · 15/09/2026

Nenhuma alteração de método. Classe **conteúdo**. Abre a onda E2 (narrativa).

- H1 "Defesa civil" com o subtítulo "Antes e depois, estado a estado e cidade a cidade". Seis figuras ganham **título-fato calculado dos dados carregados** (nunca digitado): (a) estados por categoria do plano (as três contagens somam 27); (b) o vão da prova — nos estados com camada declarada, municípios que declaram ter plano × que publicaram o documento; (c) verificação — 5.571 pelo registro federal, os consultados no diário oficial, planos municipais localizados; (e) dispersão — quantos estados têm índice abaixo de 50 e mais de 5% dos municípios sob decreto, e onde; (f) mapa — nº de municípios com decreto e o estado com maior fração; (g) semana — data do primeiro decreto e quantos caíram dentro do período eleitoral.
- As **interpretações** ("Por região: … concentra os planos feitos para o ciclo"; "Acima de 50 e mais de 5%: …; o que a figura não mostra: se houve dano") ficam no texto dos blocos, fora das figuras, como manda a regra das legendas neutras (portão 19). Sem dado, o título original permanece. Runtime de mapas confere cada título contra o dado.

## §53 · Risco climático na ordem da narrativa (auditoria editorial 14/09, onda E1 §1.10) · 15/09/2026

Nenhuma alteração de método. Classe **estrutura de página**. Fecha a onda E1.

- Ordem nova: (1) **O risco projetado, estado a estado** — o mapa do tipo de risco primeiro, largo; (2) **Situação atual** com uma linha destacada composta dos campos do painel ("El Niño {intensidade} · probabilidade {p} · tendência: {t}", nunca digitada) e o ONI como miniatura; (3) **O que está acontecendo agora** — seca observada e avisos vigentes na face, focos de calor e alertas do Cemaden no expandido; (4) **Risco projetado × plano do estado** — o cruzamento, com "estados por tipo de risco" no expandido. Nada apagado.

## §52 · Proteja-se: escolha o estado, e o guia do seu risco se abre (auditoria editorial 14/09, onda E1 §1.9) · 15/09/2026

Nenhuma alteração de método. Classe **estrutura de página**. (PR #223, mesclado em 15/09; a entrada ficou de fora do PR por engano e entra aqui.)

- Seletor de estado no bloco "Qual é o risco projetado no seu estado" — a lista vem de `data/sinais_risco.json`. Ao escolher, a página mostra a classificação da UF com a fonte e **abre o guia correspondente** (chuvas, incêndios/fumaça, estiagem/calor; "misto" abre mais de um; "sem sinal elevado" não abre nenhum e diz isso). Os três guias viraram acordeões fechados por padrão; a impressão em PDF continua lendo todos. Runtime próprio da página.

## §51 · O dinheiro volta para Financiamento; quarta porta para o calendário (auditoria editorial 14/09, onda E1 §1.7 e §1.6) · 15/09/2026

Nenhuma alteração de método. Classe **estrutura de página**.

- Financiamento ganha o bloco **"O que a União prometeu — e o que pagou"** (antes de "Por estado"): título-fato do dado (nº de compromissos verificados; R$ transferidos a municípios em 2026 até a última semana da série), a série semanal por rota como **miniatura** com a faixa do período eleitoral, e a tabela de compromissos verificados. A faixa vem com a **quarta porta** ("a faixa sombreada é a lei, não a inação… a única porta aberta é o decreto — por que há páginas fora do ar →").
- Em Pesquisadores fica só o gráfico do plano federal por área (valores anunciados), com a nota de que o resto voltou. Renderizadores movidos de `pesquisadores.js` para `financiamento.js` sem mudança de lógica; runtime cobre título, tabela, faixa e porta.
## §50 · CSP sem 'self' em script-src: a injeção do Netlify deixa de executar; canário em navegador real contra o domínio · 14/09/2026

Nenhuma alteração de método. Classe **segurança/infra**.

- A API do Netlify prova que o Heads-up Display configurável já está desligado (`hud_enabled = false`, nenhum snippet), e mesmo assim `/.netlify/scripts/hud?variant=public` é injetado em toda página servida. Com `script-src 'self'`, esse script de terceiro executava. `netlify.toml` passa a permitir só `https://monitorelnino.com.br/assets/`, `https://*.netlify.app/assets/` (onde vivem todos os nossos scripts) e o VLibras — o navegador recusa a injeção. O texto continua no HTML (o verificador já o reconhece); o código não roda.
- `scripts/verificar_publicado_navegador.js` (Playwright, contra o domínio, com a credencial): nossos scripts executam sob a CSP servida, nenhuma violação de CSP fora da injeção do Netlify, sem erro de JS, medidor da home preenchido. Passo novo no `verificar_publicado.yml`, com relatório no repositório privado.

## §49 · Domínio com senha, não com página de rosto (decisão da editoria, 14/09) · 14/09/2026

Nenhuma alteração de método. Classe **infra/publicação**.

- `data/publicacao.json` ganha `dominio: "senha"`: o domínio passa a servir o site completo atrás da **mesma senha da prévia** — Basic-Auth no servidor (segredo `PREVIA_BASIC_AUTH`, o mesmo do `publicar_previa.yml`) e véu no navegador (`assets/acesso.js`, que agora ativa no domínio quando a flag diz "senha"; nunca em localhost nem nos portões). Continua `noindex`.
- `publicar_dominio_ensaio.yml`: input `senha` (padrão true) grava o cabeçalho `Basic-Auth` só nesse deploy; o segredo é mascarado no relatório. `verificar_publicado.js` envia a credencial (env) e, em modo senha, **exige** que a home sem credencial responda 401 — se o plano do Netlify ignorar o cabeçalho, a verificação falha, de propósito.
- Voltar à página de rosto continua sendo o "Run workflow" do `publicar_dominio.yml` no ramo `publico`.

## §48 · Rota preventiva do fogo: dimensão `objeto` nas rotas, rotas preventivas com prova, bloco em Financiamento (handover de 14/09) · 14/09/2026

Nenhuma nota muda (peso zero provado por portão). Classe **dados + conteúdo**. Passos 1 e 2 do handover "Rota preventiva do fogo"; os coletores (áreas declaradas no DOU, transferências no Portal) são o passo 3.

- `data/financiamento/rotas.json`: cada rota ganha `objeto` (preventivo | resposta | livre) — a rota classifica a natureza jurídica; o objeto, o que o dinheiro paga. Enquanto os fluxos não trazem objeto próprio, vale o padrão da rota; as exceções nominais do fogo vivem em `rotas_preventivas.json`.
- `data/financiamento/rotas_preventivas.json`: cinco linhas (edital FNMA/FDD 2025; transferência direta do FNMA — Lei 15.143/2025, art. 16 → Lei 7.797, art. 3º-A; brigadas federais; Fundo Amazônia; Lei 15.143, art. 2º como resposta), cada uma com lei, artigo, condições, quem pode, o que paga, situação no período eleitoral (**em verificação**), fonte e hash do conteúdo. `url: null` onde o endereço ainda vai ser conferido (§7 do handover); nada foi inventado para preencher.
- Financiamento, bloco **"Dinheiro preventivo que existe — e para quem"** antes de "Por estado": título-fato calculado do dado (elegíveis e contemplados do edital; Fundo Amazônia; frase "não existe rota equivalente para seca nem para chuva" só enquanto o dado só tiver incêndio), interpretação fixa (ADPF 743), tabela das rotas em linguagem da tela e o **mapa em três camadas declarando a lacuna** até os coletores existirem. "Sem decretar" ganha a linha do fogo com a base legal.
- METODOLOGIA §28 (acréscimo: não há rota federal **regular**; a exceção é setorial, com a base legal) e §38 novo (as três condições, o que conta e o que não conta, as três camadas e por que "requereu" é sempre parcial, situação no defeso em verificação). Portão de financiamento: (f) objeto válido em toda rota; (g) toda linha preventiva com lei/artigo/fonte/hash e hash conferido; riscos declarados = riscos das linhas; (h) motor do índice nunca lê os dados do fogo. Runtime cobre título, tabela, lacuna e créditos. Teto de palavras de Financiamento 720 → 820 (a auditoria devolve o dinheiro a esta página).
## §47 · Saúde aberta pelas duas metades, 11 → 5 figuras na face (auditoria editorial 14/09, onda E1 §1.5) · 14/09/2026

Nenhuma alteração de método. Classe **estrutura de página**.

- Ordem nova: (1) **MARÉ · Saúde** — as duas metades (medidor v0.2 + prontidão por estado; emergências sanitárias, a metade "depois", visível mesmo em zero); (2) **O que cada estado publicou** — o filtro "Escolha um estado" virou o cabeçalho desta seção (perfil de cartões logo abaixo), mapa de status e tabela das 27 UFs; risco sanitário derivado no expandido; (3) **O que se observa** — dengue por nível de alerta (mapa, com o seletor Dengue | Chikungunya) e avisos de calor; (4) expandido **"outros desfechos"**: casos no painel amostral, respiratórias (SRAG | SG), diarreicas (DDA) e dengue nas capitais. Texto de abertura reescrito para a nova ordem, com o corte da edição.
- Nada apagado: quatro figuras foram para o expandido; os seletores e os testes de runtime seguem cobrindo todas.

## §46 · Defesa civil: "Antes" e "Depois", 12 → 8 figuras na face (auditoria editorial 14/09, onda E1 §1.4) · 14/09/2026

Nenhuma alteração de método. Classe **estrutura de página**.

- Dois blocos, na ordem da narrativa. **Antes — o que foi publicado:** status dos planos estaduais por região (absorve o "status geral" como leitura principal) · o vão da prova (declarado × documentado) · verificação municipal · cobertura e natureza por UF · municípios prioritários; abaixo, o resumo risco × plano do estado (link para o cruzamento completo em Risco) e um expandido "Ver mais" com o status geral (rosca) e o status das capitais. **Depois — o que foi decretado:** dispersão antecipação × resposta (primeira), mapa das cidades que decretaram (veio do bloco Antes), primeiro decreto por semana; expandido "Ver mais" com decretado × reconhecido (tabela).
- **Áreas COBRADE** saíram de Defesa civil e viraram tabela de prova em Pesquisadores (`#boxAreas`; o portão de consistência passou a conferir a união das áreas lá). Registro: a lista de UFs por área é constante no código, não dado em `data/` — candidata a migrar para o registro estadual.
- Contagem na face: 8 (a Parte 4 lista 7 e o Anexo A mantém o mapa de cobertura/natureza; ficou o Anexo, por preservar informação — a editoria decide se o mapa de cobertura vai ao expandido). Nada foi apagado: o que saiu da face está no expandido ou em Pesquisadores.
- `assets/colunas.js`: figura dentro de um `<details>` fechado não consome número; ao abrir, renumera na ordem do documento (o Portão 18 exige sequência contínua no que está visível).

## §45 · Prefeituras: a página do gestor, e a barra na ordem final (auditoria editorial 14/09, onda E1 §1.2 e §1.8; §2.15) · 14/09/2026

Nenhuma alteração de método. Classe **conteúdo/estrutura de página**.

- `envie-dados.html` → **`prefeituras.html`** (redirecionamentos 301 de `/envie-dados.html`, `/envie-dados`, `/para-gestores*`); `assets/js/envie-dados.js` → `prefeituras.js`; sitemap, canônica, Open Graph e portões atualizados. Barra de navegação nas 11 páginas na ordem final: **O monitor · Risco climático · Proteja-se · Defesa civil · Saúde · Financiamento · Prefeituras · Imprensa · Pesquisadores** (o portão de estrutura passa a exigir exatamente isso).
- Página com um só público (o gestor) e quatro blocos, ~530 palavras estáticas (antes 1.101 e dois públicos): **O que conta** (três frases, com a de §2.15 sobre decreto de alerta/mobilização × decreto de emergência); **Como publicar** (três passos + base legal em uma linha); **O que ainda é possível no período eleitoral** (lista vinda de `data/calendario/dispositivos.json`, o mesmo dado do calendário e da nota da Imprensa; porta "por que há páginas fora do ar →" e link "Sem decretar" para Financiamento); **Envie um documento** (o mesmo formulário Netlify, com a regra de conferência em duas frases). O checklist de sete itens e a base legal longa saíram da face (a metodologia e o calendário os guardam).

## §44 · Home na espinha narrativa (auditoria editorial 14/09, onda E1 §1.3, §1.6 e o texto de §2.1–§2.4, §2.7, §2.8) · 14/09/2026

Nenhuma alteração de método; nenhum número muda. Classe **conteúdo/estrutura de página**.

- Ordem nova da home: cabeçalho com **título-fato** ("Anunciado em 29 de junho: o que o poder público publicou antes — e decretou depois"; linha com nº de municípios verificados e corte, do dado) → régua → os dois medidores, cada um com **uma frase de interpretação calculada do dado** (estados por categoria do plano: feito para o ciclo / de todo ano / sem plano localizável; municípios, milhões de pessoas, primeiro decreto, aceitos pelo governo federal) → **três números** (anunciado · chegou por habitante · ainda não sabemos; "publicado" e "decretado" saíram porque são os medidores) → **Sua cidade** em painel próprio, na primeira dobra → 27 cartões ("Onde cada estado está — e o que sustenta a nota") → **"O que vem"** (marcos fixos do ciclo em `data/marcos_ciclo.json`, só os futuros, nunca vazio; mais os prazos do vigia) → "O que o período eleitoral escondeu", visível com a linha fixa de §2.8.
- Parágrafo do método ("arcabouço público…") saiu da tela e foi para a ficha "Como ler o MARÉ" (§2.2). Frase de contextualização do decreto sob o art. 73 (§2.15).
- Portas para o calendário (§1.6): no contador, na nota do período eleitoral e no bloco "escondeu" — sempre "por que há páginas fora do ar →"; o antigo atalho "o que a lei deixa aberto" continua fora da home.
- Runtime da home cobre título-fato, interpretações (contagens somam 27), três números, ordem das seções, "O que vem" não vazio e as três portas. Bateria completa verde, Portão 18 incluído.

## §43 · Pré-condição de publicação: noindex em todo deploy até o lançamento (auditoria editorial 14/09, §1.1) · 14/09/2026

Nenhuma alteração de método. Classe **infra/conteúdo**. Onda E1 da `AUDITORIA_EDITORIAL_e_HANDOVER_14-09-2026.md`, item 1.1 (crítico).

- `data/publicacao.json` (`indexar: false`, decidido pela editoria em 14/09) é a única flag de lançamento. Enquanto for `false`: as 11 páginas levam `<meta name="robots" content="noindex, nofollow">` (antes: `index, follow`); todo deploy (prévia e ensaio) já leva `X-Robots-Tag: noindex` e `robots.txt` de bloqueio; `verificar_seo.js` bloqueia página sem o meta; `verificar_publicado.js` **falha** se o noindex (cabeçalho **e** meta) faltar em qualquer página servida — o workflow diário passa a usar esse modo por padrão. Mudar a flag para `true` inverte as exigências (o portão passa a bloquear qualquer noindex remanescente).
## §42 · Netlify sem pós-processamento: o servido é byte a byte o mesclado · 14/09/2026

Nenhuma alteração de método. Classe **infra**. No 1º ensaio de publicação (15h25 UTC), `verificar_publicado.js` provou que o Netlify reescrevia o HTML ao servir (Pretty URLs; aspas de atributos `"`→`'`), e 8 páginas deixavam de bater com `MANIFEST_SHA256.txt`. Em vez de normalizar cada reescrita, `netlify.toml` passa a declarar `[build.processing] skip_processing = true` — o site já é estático e otimizado no repositório; servir exatamente o que foi mesclado é o que a verificação de integridade exige. Vale para prévia, ensaio e lançamento.

## §41 · Ensaio de publicação no domínio (noindex, por botão) e verificador do site publicado · 14/09/2026

Nenhuma alteração de método nem de conteúdo. Classe **infraestrutura** (PROTOCOLO §7, complemento). Pedido de Patricia: "exercício de publicar o site" com volta à cortina quando quiser.

- `publicar_dominio_ensaio.yml`: `workflow_dispatch` na `main`, confirmação digitada, deploy de produção do retrato da `main` com `X-Robots-Tag: noindex` + `robots.txt` de bloqueio só nesse deploy; nunca por push (a rodada semanal segue só na prévia). Reversão: `publicar_dominio.yml` do ramo `publico` por botão, ou "Publish deploy" da cortina no Netlify.
- `scripts/verificar_publicado.js`: camada pós-deploy que faltava — roda contra o domínio real: 200 em toda página do sitemap, CSP/HSTS/nosniff, `noindex` presente (ensaio) ou ausente (lançamento), sem mixed content, **SHA-256 de cada arquivo servido = `MANIFEST_SHA256.txt`**, canários (`meta.json` com data de edição; `indice.json` com 27 UFs). Sem dependências além do Node 20. Roda no próprio workflow do ensaio; falha só relata (no ensaio).

## §40 · "Como ler o MARÉ" vira ficha popup; "O que a lei deixa aberto" vira nota para a imprensa · 14/09/2026

Nenhuma alteração de método; nenhum número muda. Classe **conteúdo/estrutura de página** — pedidos editoriais de Patricia em 13/09/2026, executados com o "vai" de 14/09.

- Home: os dois grupos de atalhos `.hero-links` ("Índice por estado", "Encontre sua cidade", "Resposta por estado", "O que a lei deixa aberto") saíram. Logo abaixo da barra do índice entra um único link, "como ler o MARÉ", que abre o texto de leitura como ficha no **mesmo `<dialog>`** do detalhe do estado (fecha por ×, fundo ou Esc). O texto vive oculto em `#comoler`; a nota do período eleitoral e o bloco pós-defeso ficam onde estavam.
- "O que a lei deixa aberto" deixa de ser referido na página principal e passa a ser **nota para a imprensa** em `imprensa.html` (mesma fonte `data/calendario/dispositivos.json`, campo `nao_suspenso`, mesmo desenho de linha do calendário; a página do calendário continua publicada, fora da barra). Trecho encurtado para caber no teto de palavras da página.
- Runtime da home cobre: sem `.hero-links`, link no lugar certo, clique abre a ficha, × fecha, nenhuma referência ao calendário na home. Bateria local completa verde, Portão 18 incluído.

## §39 · Doenças diarreicas agudas (DDA): coletor, figura e correção do catálogo · 14/09/2026

Nenhuma alteração de método; nenhum número do índice muda (peso zero, §31/§35). Classe **código** (PROTOCOLO §3.2), item 1 do §5 das instruções de 14/09.

- **A fonte do catálogo não existia.** Sondagem no runner (relatório `dda_opendatasus`): o OpenDataSUS deixou de ser CKAN (`/api/3/…` devolve HTML) e não hospeda o Sivep-DDA. O catálogo dizia "OpenDataSUS (Sivep-DDA)" sem prova — corrigido para o que é verdade; a entrada de leptospirose ganhou a mesma ressalva (a verificar).
- **Fonte real, com proveniência:** resposta do Ministério da Saúde a pedido LAI (processo 25072.030308202612) redistribuída no Zenodo por Raphael Saldanha (Fiocruz / Observatório de Clima e Saúde), CC BY 4.0, com MD5 publicado, codebook e manifesto — histórico 2008–2024 (registro 20752238) e preliminar 2025–2026 (registro 20752301, atualização mensal). Formato verificado no runner (relatório `dda_zenodo`): CSV, 26 colunas, agregado semanal por município (IBGE de 6 dígitos), 291 dos 313 municípios do painel presentes, semanas 1–23 de 2026.
- `coletar_dda.py`: segue `links.latest` de cada registro, confere o MD5 de cada arquivo (diferente = lacuna, nunca dado), localiza colunas por padrão e falha alto se um papel obrigatório não casar; casos = soma das cinco faixas etárias (atendimentos em unidades sentinela, e o rótulo do eixo diz isso); série BR + 27 UFs e série do painel (`dda_serie.json`, `dda_serie_painel.json`); canal endêmico 2019–2025 e últimas 4 semanas do ano corrente vazadas como "parciais" — a fonte não publica nowcasting, e a legenda nunca usa a palavra. Anos históricos reaproveitados enquanto o MD5 não muda. Autoteste com 8 casos.
- `saude.html`: figura "Diarreicas agudas por semana · Brasil" no mesmo componente da respiratória; `assets/js/saude.js` ganhou um renderizador único de série nacional (SRAG/SG e DDA são configurações dele — nada duplicado), com o crédito de cada figura ainda declarado literalmente (o portão de saúde procura o literal).
- Primeira leitura real no runner (14/09, 11h56 UTC): 8 anos com MD5 ok, BR + 27 UFs, 308/313 municípios do painel; ordem de grandeza de 150–230 mil atendimentos sentinela/semana. Ela mostrou que o arquivo público saía com 3,5 MB por carregar o cache histórico — corrigido na mesma data: cache em `dda_cache.json` (não baixado pela página) e `dda_serie.json`/`dda_serie_painel.json` só com 2025–2026 mais o canal endêmico.
- `atualizar.py` chama o coletor após o SRAG. `diagnostico_sinais.yml` ganha um passo que roda o coletor isolado, sem commit, para conferir a primeira leitura real. Runtime de saúde cobre a figura nos dois estados (sem arquivo → lacuna declarada visível; com arquivo → canvas). Bateria local completa verde, Portão 18 incluído.

## §38 · Trava de concorrência na rodada de atualização · 14/09/2026

Nenhuma alteração de método; nenhum número do índice muda. Classe **código** (PROTOCOLO §3.2), correção de risco operacional.

- `.github/workflows/atualizar.yml` tinha dois `cron` que caem no mesmo minuto toda segunda-feira: a rodada SEMANAL (`0 9 * * 1`) e a primeira rodada DIÁRIA (`0 9 * * *`, 06h Brasília). Sem trava, os dois jobs corriam em paralelo e podiam commitar/dar push ao mesmo tempo — risco real de colisão, observado em produção às 09h15–09h17 UTC de 14/09/2026 (dois runs `schedule` simultâneos, `run_id` 34826940245 e 34827134682).
- Adicionado bloco `concurrency` (`group: atualizar-dados`, `cancel-in-progress: false`): qualquer sobreposição futura (segunda-feira ou não) faz o segundo run esperar o primeiro terminar, em vez de rodar em paralelo ou cancelar um commit válido.
- Portões `verificar_estrutura.js` e `verificar_robustez_atualizacao.py` verdes; mudança isolada ao workflow, sem tocar dados ou site publicado.

## §37 · Fundamento jurídico da publicação, ADPF 743 e padrão de conteúdo do ciclo · 07/09/2026, rebaseado e mesclado em 13/09/2026

Nenhuma alteração de método (§12.5); nenhum número do índice muda. Classe **conteúdo de metodologia** — decisão editorial, não correção mecânica. Conteúdo escrito e aprovado para leitura em 07/09/2026 (PR #96); a PR original ficou presa a uma base anterior à reescrita de histórico de segurança de 13/09/2026 (ver §LGPD abaixo) e divergiu 498 arquivos da `main` atual. Em vez de reabrir aquele diff, os três commits de conteúdo foram recuperados por cherry-pick sobre a `main` corrente, num ramo novo; a PR #96 original foi fechada sem merge.

- **Por que o objeto é a publicação.** Publicidade como condição de eficácia do ato administrativo (CF art. 37, *caput*); um plano não publicado não vincula nem pode ser cobrado — por isso o índice conta o instrumento **publicado**, não o "plano existente" (§5.0).
- **Base legal com prazo e prestação de contas.** Lei 12.608/2012 art. 8º VI/XI; Lei 12.527/2011 art. 8º (transparência ativa); consequência para a régua de antecipação (§24): publicar o ato é dever, não publicidade.
- **ADPF 743.** Despacho de 25/05/2026 (Min. Flávio Dino) intima União e dez estados da Amazônia Legal/Pantanal a informar preparação para o 2º semestre de 2026; marca factual `adpf743_intimado`, peso zero.
- **Nota Técnica CNM nº 12/2026** como checklist de leitura de conteúdo (`conteudo_ciclo`, peso zero, mesma governança do §35); Decreto SC nº 1.530/2026 como exemplo de limiar observacional.
- A numeração final é **§37** (o §36 já estava ocupado, desde 09/09/2026, pela estrutura de informação dos desfechos em saúde) — resolvida automaticamente pelo merge de três vias no cherry-pick, sem edição manual de número.

## §36 · MS entrega série de verdade; DF, PE e PB — três causas diferentes, documentadas até o fim · 12/09/2026

Nenhuma alteração de método; nenhum número do índice muda. Classe **código** (PROTOCOLO §3.2). Sessão de investigação profunda pedida pela editoria ("encontrar uma solução para os estados que estão dando erro"), com medição real no runner em cada etapa — nenhuma correção sem prova contra dado real.

**MS — resolvido, com prova em produção.** `extract_tables()` do pdfplumber (grade da própria tabela, não texto por posição) recupera 74 dos 79 municípios contra o PDF real da SE 34/2026 — o texto corrido só achava 35, porque a segunda metade da tabela cai numa página com gráfico ao lado e a extração por posição intercala as colunas fora de ordem. `data/saude_desfechos/ses_ms_dengue.json` foi gravado de verdade numa rodada de teste isolada: primeira vez que qualquer um dos quatro coletores de saúde produz série publicável.

**DF — solução correta, esgotada pelo próprio ritmo de teste do dia.** Medido no runner: `saude.df.gov.br` nunca completa o handshake TLS (`_ssl.c:993`, timeout). `web.archive.org`, um CDN global, respondeu 200 em ~1s no mesmo runner — não é bloqueio geral de rede, é aquele site específico. Implementado `buscar_com_reserva_wayback()` em `coletores_base.py`: pede ao archive.org para capturar a página agora (rede própria dele) e lê a captura mais recente. Funcionou isolado na primeira medição; nas rodadas seguintes, hoje, passou a devolver **"Connection refused"** — sinal de limite de taxa do próprio archive.org, quase certamente por eu ter acionado `/save/` e `/web/` repetidas vezes ao longo do dia depurando. Em uso semanal normal (uma vez), esse risco é muito menor. Arquitetura mantida; próxima sessão deve confirmar com um único disparo, não em rajada.

**PE — avançou, não fechou.** O layout mudou de rótulos curtos ("Notificados") para rótulos longos ("Casos notificados") entre as edições usadas nos autotestes e a mais nova; o parser foi generalizado para aceitar 2, 3 ou 4 colunas por linha (`_pareados()`) e rótulos partidos entre linhas — dengue e chikungunya's notificados/prováveis/descartados extraem certo agora. Só "Casos confirmados" da dengue continua sem número adjacente no texto extraído. Confirmação externa (duas reportagens independentes citando o mesmo boletim) dá o valor real — **11.241** — provando que o número existe no PDF, só mais longe do rótulo do que a janela de busca alcança; alargada de 40 para 200 caracteres, sem resolver. Não travado no código o valor específico (quebraria toda semana). Fica para sessão com acesso à página completa.

**PB — sem solução por este método, e não é falha de coleta.** O portal devolve o boletim **"Nº 05 — 20.04.2023"** para qualquer número de URL tentado que não exista — confirmado duas vezes, em rodadas diferentes. Adivinhar número não serve para achar o boletim corrente ali. Reduzido de 24 para 6 tentativas (mesmo resultado, ~8 min mais rápido por rodada). Precisa de um mecanismo de descoberta diferente (listagem real, não inferência de padrão de URL) — não encontrado nesta sessão.

Em nenhum momento, em nenhuma das dezenas de tentativas de hoje, um número errado, parcial ou de ano incorreto foi publicado. Todas as falhas conhecidas viraram lacuna auditável.

## Figura "SRAG por semana · Brasil" — lacuna passa a ser declarada na própria figura · 11/09/2026

Nenhuma alteração de método; nenhum número muda. Classe **código** (PROTOCOLO §3.2). Peso zero.

- **Sintoma relatado pela editoria:** a figura não aparecia no site. Causa: `data/saude_desfechos/srag_serie.json` **nunca foi criado**. `coletar_srag_gripe.py` roda em toda atualização, mas registra `URLError` desde **09/09** (três rodadas). Sem o arquivo, o JS saía no início e deixava só a moldura do cartão — sem gráfico e **sem dizer nada a quem lê**, o pior desfecho para um índice que se propõe auditável.
- **Fonte fora do ar, não erro do coletor.** Verificado em navegador no Brasil: `gitlab.procc.fiocruz.br` (host do CSV canônico do InfoGripe, `serie_temporal_com_estimativas_recentes.csv`) devolve `ERR_CONNECTION_TIMED_OUT`. Não é bloqueio ao runner: não responde de lugar nenhum.
- **Pista de migração, ainda não confirmada:** o InfoGripe aparece agora em `gitlab.fiocruz.br/marcelo.gomes/infogripe`, mas esse host **exige login** — não serve para coleta anônima. Por isso a URL **não** foi trocada às cegas; quatro endereços (host antigo e novo, raiz e CSV) entraram na sonda `scripts/diagnostico_fontes_saude.py` para medir antes de decidir.
- **Correção visível agora:** a ausência de série é **declarada dentro da figura** ("Série ainda não coletada — lacuna declarada", com a razão), no mesmo padrão já usado em `financiamento.js`. A mensagem vai na mídia, não como parágrafo no cartão, porque o portão de figuras só admite título, legenda e crédito.

