# Changelog · Monitor El Niño Brasil / Índice MARÉ

Formato inspirado em [Keep a Changelog](https://keepachangelog.com/pt-BR/).
Cada entrada aqui é um resumo escaneável; a justificativa completa, com
fundamentação teórica e dados de impacto, vive em `METODOLOGIA.md` (a fonte
de verdade), datada seção a seção. Convenção deste projeto: mudança que
altera pesos, créditos ou componentes do índice exige **versão maior**
(regra de governança registrada em `METODOLOGIA.md` §12); expansão de
documentação, novos portões de verificação e reconhecimentos editoriais
não pontuados permanecem na versão corrente.

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

## §55 · Saúde: títulos-fato do dado (auditoria editorial 14/09, onda E2 §2.10) · 15/09/2026

Nenhuma alteração de método. Classe **conteúdo**.

- MARÉ · Saúde: "Saúde: {n} estados com plano para o ciclo, {n} com o de todo ano, {n} em elaboração, {n} não verificados" (do `saude_uf.json`); mapa de status com a mesma contagem; contador "Emergências sanitárias declaradas no ciclo: {n}" com "nenhuma localizada até {corte}" quando zero; dengue/chikungunya: "{n} municípios em alerta laranja ou vermelho na semana SE {n} de 2026 (painel amostral)", recalculado ao trocar a doença. Interpretação fixa do InfoDengue ("o Monitor não atribui casos ao El Niño") fora da figura, no bloco "O que se observa" (portão 19). Títulos calculados após o carregamento; sem dado, o título original permanece. Runtime confere contra o dado; títulos dentro do teto de 100 caracteres do portão 19.

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

## §82 · Consolidação estrutural: duplicações de código e documentação achadas em auditoria · 17/09/2026

A pedido da editoria, depois de uma auditoria de código (não só do CHANGELOG) que apontou onde
o site duplica lógica e texto em vez de ter uma fonte única. Classe **manutenção** — nenhuma
mudança visível de conteúdo ou de método.

- **`desenharMapa()` unificado**: `financiamento.js`, `saude.js` e `sinais-de-risco.js`
  reimplementavam a própria versão da função, apesar do cabeçalho de `assets/mapas.js` já
  declarar que nenhuma página deveria fazer isso. Agora existe uma única `MonitorMapas.desenharMapa()`
  em `assets/mapas.js`; as três páginas só passam o próprio contexto para ela.
- **Portão de estrutura ganhou dentes**: `scripts/verificar_estrutura.js` agora falha de verdade
  se alguma página redefinir `desenharMapa`/`siglas`/`showTip`/`legenda` localmente — antes a
  regra só existia como comentário, sem checagem. No caminho, o comentário também citava um nome
  errado (`addSiglas`, que nunca foi o nome exportado — é `siglas`); corrigido. Mesclado sem
  atrito com a checagem de string-partida-por-tag do §81, adicionada em paralelo.
- **Arquivo órfão removido**: `assets/js/para-gestores.js` não era carregado por nenhuma página
  desde a renomeação de Prefeituras para Para gestores (PR #240, 15/09) — sobrou sem uso.
- **Regra de voz editorial consolidada num só documento**: `docs/GUIA_DO_EDITOR.md` e
  `docs/VOZ_EDITORIAL.md` descreviam parcialmente a mesma regra, de formas diferentes.
  `docs/VOZ_EDITORIAL.md` passa a ser o único documento canônico (léxico avaliativo/causal/teto
  probatório, antes só no guia, foi incorporado lá); o guia agora só aponta para ele.
- **`docs/AUDITORIA_CODIGO.md` sinalizado como desatualizado**: a seção de escopo ainda descrevia
  o pacote de 27/08/2026 (três páginas); corrigida a contagem de páginas e adicionado aviso de que
  o restante do documento precisa de uma auditoria completa própria — não é este PR.

Suíte de portões (todos, incluindo os dois de tom) verde; cadeia de derivados regenerada em
árvore limpa; `recalcular_mare.py --check` reproduz a média nacional bit a bit (43.6, inalterada).

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

## §55 · Correções da editoria de 15/09: nomes das páginas, página inicial, uma só arte de barra, resposta como índice, MARÉ · Saúde v0.3, coletores de sinais · 15/09/2026

Classe **método (peso zero) + estrutura de página + coletores**. Constantes do motor do MARÉ inalteradas (congelamento C25 mantido; `recalcular_mare.py --check` reproduz a média nacional). Metodologia §39, §32.4 e §31 (v0.3).

- **Nomes**: MARÉ Legal · Monitor de risco · MARÉ Saúde · Para prefeitos (arquivos e URLs iguais; `<title>`, Open Graph, JSON-LD e `<h1>` acompanham; portão de estrutura com a nova ordem canônica).
- **Página inicial**: subtítulo único com contagem e corte vindos dos dados; saem título-fato, botão "Consultar seu município", nota do período eleitoral, os três cartões e o bloco "O que o período eleitoral escondeu"; "O que vem" → **Calendário** em colunas (data · marco · fonte; marcos do ciclo + prazos legais em curso); o gráfico **risco projetado × estágio do arcabouço** mudou do Monitor de risco para o fim da inicial (Chart.js volta à inicial; a página de risco linka para cá; Defesa civil idem).
- **Resposta vira índice** (§32.4): 100 × fração da população em município sob decreto (`indice` em `data/resposta/por_uf.json`, recomputado pelo portão); pílula com nº e % de municípios; cartões de estado e ficha do estado com a mesma barra; a barra empilhada de tons sai (tons seguem como texto).
- **Uma arte para toda barra**: dois degradês em `tokens.css` (`--degrade-indice`, `--degrade-resposta`); medidores, micro-barras e barras por UF da Saúde com o mesmo trilho, degradê e corrente animada; `prefers-reduced-motion` respeitado.
- **MARÉ · Saúde v0.3** (§31): terceiro componente **cobertura populacional sanitária** (população em município cujo plano localizado trata a saúde × crédito municipal do MARÉ × degrau/5 de `saude_no_plano`; plano sem leitura = 0 e contado). **Errata de efeito**: média das 17 verificadas 44,0 → 31,8 (AM 84,1 · GO 50,0 · ES 39,6 · PE 31,6 · 10 UFs em 28,3 · DF/PB/PR/SE 21,7 · RJ 21,3). Tabela e tooltip da Saúde ganham a coluna; portão (m) exige a média dos três.
- **Monitor de risco**: ONI logo abaixo de "Situação atual", com leitura descritiva na figura e interpretação/projeção no parágrafo do painel; **coletores corrigidos** após sonda com rede real — INMET (nomes por extenso e geocodes), Monitor de Secas (RPC de dados tabulares, frações cumulativas → exclusivas, categoria mediana no mapa), zero-fill para CEMADEN/INMET/INPE. Primeira coleta completa dos quatro mapas em 15/09/2026 (dado real neste PR).
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
## §52 · Legendas neutras: auditoria de todas as figuras e portão 19 (regra editorial permanente da editoria, 15/09) · 15/09/2026

Nenhuma alteração de método, dado, cálculo ou fonte. Classe **texto/editorial + portão**. A editoria fixou uma regra permanente: legenda, título auxiliar, subtítulo, item de legenda, crédito, tooltip e cartão com número **descrevem** (variável, período, território, unidade, fato principal) e **nunca** avaliam, dramatizam, interpretam ou atribuem causa; interpretação vive no texto narrativo, fora da figura.

- Auditoria das 48 figuras e 30 cartões das 11 páginas, renderizadas com dados. Reescritos só os textos que enquadravam ou avaliavam: títulos "O vão da prova: …" → "Municípios com plano, declarado × documentado (PR · SC · RS)"; "Municípios prioritários — quem já publicou, quem ainda não" → "…: com e sem instrumento localizado" (subtítulo idem, "sem ato localizado"); "A rede do dinheiro: …" → "Rotas do dinheiro público até o município: …"; "Índice ONI: a série que define o fenômeno" → "Índice ONI (Oceanic Niño Index), série desde 1950".
- **Errata de contagem:** o título do catálogo de desfechos dizia "4 coletados, 16 no backlog" (número digitado); o dado tem 5 coletados desde 14/09 (DDA). O título deixa de carregar contagem; o texto da seção passa a ler o número do dado (`#nDesfechosColetados`). A nota do gatilho "emergência · decretos" carregava "4,2%" digitado; sai (o valor vivo já era exibido).
- Teto probatório dentro da figura: legenda "Sem instrumento ainda" → "Sem instrumento localizado"; tooltip "JÁ TEM instrumento localizado / … ainda" → "instrumento localizado / nenhum instrumento localizado até o corte"; rótulo do cruzamento risco × plano "Sem instrumento estadual" → "Instrumento estadual não localizado".
- Notas internas que estavam em texto público, reescritas em registro público: "não inventar", "a arquivar", "(§15)", "sessão de 02/09", "coletor a escrever", "adaptador ANA pendente", "a verificar: … descobrir a API nova", "a coletar", "a filtrar" (`data/saude_federal.json` e o semeador `coletar_saude.py`, `data/saude_sinais.json`, `data/saude_desfechos/catalogo.json` e `gatilhos.json`, exemplos da rota 7 em `financiamento.js`, item do Calendário). A linha do Carro-Pipa deixa de mencionar pedido de LAI (registro privado; só contagens agregadas, se a editoria confirmar).
- "O que se espera" da MP 1.384 (`data/marcos_prazos.json` → `prazos_uf.json` regenerado; `pesquisadores.js`) sai da apreciação "a maior parte do crédito ainda não foi empenhada" para a mesma forma neutra da MP 1.367: "a MP caduca: o que já foi empenhado permanece, o restante do crédito cai" — o número vive na legenda da figura.
- Home: a frase "o plano publicado antes decide o que acontece nas primeiras horas" (§2.15 do handover de 14/09) sai da nota do contador (elemento de dado) e vai para a linha narrativa logo abaixo; a nota guarda os dois fatos legais (art. 73, VI, *a*; "o decreto de emergência é a porta legal do recurso"). Nada foi apagado; `verificar_runtime_resposta.js` segue exigindo o art. 73 no contador.
- **Novo portão 19 — `scripts/verificar_legendas.js`** (em `portoes.yml`, protocolo §3.3 e Guia do Editor): nas 11 páginas renderizadas, para toda `.figura` (título, subtítulo, `.figura-leitura`, itens de legenda, crédito, resumos, rótulos de lacuna na mídia), cartões-indicador da home e strings de `showTip` dos scripts: léxico avaliativo e alarmista, aberturas interpretativas, conectivos causais, "não existe / não tem plano / sem plano|instrumento|ato" sem "localizado", ênfase em caixa alta, título > 100 caracteres, leitura > 2 frases ou > 240 caracteres. Lista de exceções para termos técnicos ("síndrome respiratória aguda grave", "janela crítica", "nível 3 (alerta)"). Teste negativo feito em três frentes (título, item de legenda, tooltip), restauração verde. Suíte passa a 19 portões.
- Consequência para a onda E3 (visualizações) do handover de 14/09: as "interpretações" com juízo previstas para dentro das figuras ("o sistema funcionando", "o recurso chegando para improvisar") passam a viver no texto narrativo da seção; os títulos-fato com número do dado seguem como planejado (Regra 2 do handover já os exigia sem adjetivo e sem causa).
## §51 · Errata: URL da evidência de Ouro Branco/AL restaurada ao caminho informado pela API do Querido Diário (portão 6) · 15/09/2026

Nenhuma alteração de método; nenhum número do índice muda. Classe **dados** (PROTOCOLO §3.2), correção de registro anterior — errata da entrada de 10/09/2026. Preparada em 14/09 (ramo ficou em `ramos_pendentes/` por bloqueio de rede) e refeita sobre a `main` de 15/09.

- **O que estava errado.** Em 10/09/2026 a URL do Decreto Municipal nº 021/2026 de Ouro Branco/AL foi trocada de `data.queridodiario.ok.org.br/2700000/…` para `…/2706109/…`, na hipótese de que `2700000` era um erro de digitação do código IBGE. A hipótese não se sustenta: a resposta da API do Querido Diário preservada em 03/09/2026 (`evidencias/d1fe5dd2…json`, busca por `territory_ids=2706109`) informa, para essa mesma edição (nº 2849, 15/07/2026), `url` sob o caminho `2700000/…d36309fe….pdf` e `txt_url` sob `2706109/…a34fb862….txt`. O Diário Oficial dos Municípios do Estado de Alagoas (AMA) é uma edição estadual única, e o Querido Diário guarda o PDF sob o identificador agregado.
- **Sintoma.** Desde a troca, `preservar_evidencias.py` registrou `HTTPError` na URL `2706109/….pdf` em todas as rodadas (11, 12 e 14/09 — `data/log_buscas.json`, executor `robo`, rede irrestrita do runner). Antes de 10/09 a URL original nunca chegou a ser tentada pelo robô. É o único registro pontuável sem evidência preservada; o portão 6 (`verificar_evidencias.py`) é bloqueante desde 15/09/2026 — e por isso derruba a Action "Portões" de todo PR até a evidência ser preservada.
- **Correção.** URL restaurada para o caminho informado pela própria API (`2700000/…`), aplicada por `aplicar_revisao.py` (ação `atualizar`, demais campos idênticos); derivados regenerados (`dados-abertos/municipios.csv`, manifesto). `corte` de `data/meta.json` mantido, como no precedente de 10/09 (correção de registro, não dado novo). A preservação do binário continua a cargo de `preservar_evidencias.py` na rodada automática seguinte ao merge — a rede do ambiente de edição não alcança o Querido Diário, e a Action `ler_documento` do registro privado recusou o disparo nesta sessão (HTTP 500).
- **Se a rodada seguinte ainda registrar `HTTPError`** na URL restaurada, a hipótese restante é que o arquivo foi removido ou renomeado no armazenamento do Querido Diário; nesse caso a evidência deve ser buscada na fonte primária (Diário Oficial dos Municípios da AMA, ed. 2849) ou no Wayback, e a decisão volta à editoria.

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
## §43 · MARÉ · Saúde v0.2: régua do índice principal, duas camadas de objeto, medidor idêntico ao da home · 14/09/2026

Nenhuma alteração de método do índice principal (peso zero mantido e provado por `verificar_saude.py`). Classe **medida separada (v0.x)** + **código** + **página**. Decisão editorial de Patricia em 14/09/2026 ("construa o MARÉ Saúde da forma como você sugeriu e faça uma representação gráfica igual ao do MARÉ principal"). Fundamentação e errata de efeito em `METODOLOGIA.md` §31 (v0.2).

- `gerar_monitor_saude.py`: régua de antecipação com as âncoras do §5.2 (antes de 29/06 → 100; até 29/07 → 60; até 30/09 → 50; depois ou sem data → 30; recorrente 2025/26 que cobre o risco → 40; anterior → 20; ELAB → 20); campo `camada` (`ciclo` | `adaptacao`) — plano decenal nunca pontua; `versao: 0.2`; nove autotestes (dois novos: âncoras; plano decenal).
- Efeito (17 UFs verificadas): GO 100 → 75,0; 14 UFs recorrentes 45 → 42,5; AM 100; média das verificadas 49,0 → 44,0; nenhuma faixa muda.
- `saude.html`: medidor com a mesma anatomia do índice principal (`.gauge-zone`, marcas 25/50/70, badge de faixa), alvo = média das UFs verificadas, legenda "não é um número nacional" com contagem das não verificadas; linha de versão "0.2 · dois sub-elementos · não comparável ao MARÉ".
- `assets/js/saude.js`: preenche e anima o medidor a partir de `data/monitor_saude.json` (mesmo padrão do `index.js`).
- `scripts/verificar_runtime_saude.js`: teste novo (alvo = média; legenda; contagem; três marcas; badge). Teste negativo executado: legenda trocada → ✗ e exit 1; restaurada → verde.
- Portões: `verificar_saude.py` ✓ · `verificar_consistencia.py` ✓ · `recalcular_mare.py --check` ✓ (43,6 inalterado) · `verificar_estrutura.js` ✓ · `verificar_runtime_saude.js` ✓. `METODOLOGIA.pdf` regenerado.

## §42-b · Verificador reconhece o "Netlify HUD" · 14/09/2026

Com `skip_processing` ligado, o 2º ensaio (15h56 UTC) mostrou que a divergência restante não era pós-processamento: o Netlify **injeta** `<script async src="/.netlify/scripts/hud?variant=public">` em todas as páginas ao servir (recurso de painel, "Netlify HUD") e reserializa um atributo com aspas simples. `verificar_publicado.js` passa a reconhecer essa injeção pelo nome, compará-la à parte (páginas idênticas ao manifesto depois de removê-la) e reportá-la como achado próprio: aviso no ensaio, **bloqueante no lançamento**. Desligar é ação no painel do Netlify (não há como pelo repositório).

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

## §36 · por que os coletores estaduais não baixaram, medido e corrigido · 11/09/2026

Nenhuma alteração de método; nenhum número muda. Classe **código** (PROTOCOLO §3.2). Peso zero.

Na primeira rodada real os quatro coletores (MS, DF, PE, PB) declararam lacuna. A suposição inicial — bloqueio geográfico ao runner — foi **medida e descartada** por `scripts/diagnostico_fontes_saude.py` (dois User-Agents por alvo, com controles). O UA não influi em nenhum caso. As causas são quatro, distintas:

- **MS — erro do coletor.** A listagem responde 200 do runner; o que falhava era procurar um **permalink de post** que a listagem não usa. Verificado em navegador real: os PDFs estão expostos direto, em `/wp-content/uploads/<ano>/<mês>/Boletim-Epidemiologico-Dengue-–-Semana-NN-–-AAAA.pdf` (separador é travessão U+2013), e a **SE 34/2026 está publicada**. A série não foi interrompida, como se supunha. Passa a raspar a listagem, com o permalink como segundo caminho.
- **PE — erro do coletor.** Listagem e PDF respondem 200. O coletor pediu a **SE 35**, anunciada na listagem antes de o arquivo existir, levou `HTTPError` e desistiu sem tentar a SE 34, que estava no ar. Agora desce a lista das edições mais recentes até uma responder com PDF, e **registra** que houve edição anunciada sem arquivo — fato da fonte, não erro silencioso.
- **PB — risco sério evitado.** Responde 200, mas com `text/html`: um interstício que só entrega o PDF depois do cookie. Pior: no acesso público, a URL `...no-03_2026.pdf` serviu o boletim **"Nº 05 — 20.04.2023"**. O padrão de URL é inferido, não publicado — o nome do arquivo **não garante a edição**. Sem guarda, uma rodada gravaria dado de 2023 como leitura corrente. Passa a valer o ano lido **dentro** do documento: divergir do ano corrente é recusa, com autoteste dedicado.
- **DF (e SP) — obstáculo real de rede.** `_ssl.c:993: handshake timed out`, ~45 s, idêntico com os dois UAs, enquanto o Querido Diário responde 200 do mesmo runner. Não é parser, não é UA: esses dois portais não completam TLS com o runner. Fica declarado; nenhum ajuste de código resolve.

O desenho defensivo se confirmou: nas quatro fontes, o desfecho foi lacuna auditável — em nenhum momento entrou dado parcial ou de ano errado.

## §36 · três coletores estaduais corrigidos pelo que a 1ª rodada real mostrou (MS, PE, PB) · 11/09/2026

Nenhuma alteração de método; nenhum número muda. Classe **código** (PROTOCOLO §3.2). Peso zero.

Na primeira rodada real, os quatro coletores declararam lacuna. A hipótese inicial — bloqueio geográfico ao runner — foi **medida e descartada** por `scripts/diagnostico_fontes_saude.py`: MS, PE e PB respondem **HTTP 200** do runner, e o User-Agent não altera nada. As causas eram três, distintas:

- **MS — a fonte parou.** Permalink correto, listagem 200, mas o último boletim publicado é o da **SE 25 (10/07/2026)**; a semana corrente é a ~37. O recuo de 3 semanas tornava isso indistinguível de erro do coletor. Agora recua até 14 semanas e **declara a defasagem** quando o boletim mais recente é antigo. Interrupção da publicação é achado do §36, como BA e CE.
- **PE — edição anunciada antes de existir.** A listagem já trazia a **SE 35**, cujo PDF ainda não estava no ar (o da SE 34 baixa normalmente). O coletor pedia só a mais recente e falhava. Agora tenta as 4 mais recentes em ordem decrescente e registra as anunciadas sem arquivo.
- **PB — interstício HTML.** O portal responde 200 com `text/html` (página de espera do Plone, `Pragma: no-cache`) no lugar do arquivo. O coletor recusava corretamente o que não começa com `%PDF`; agora **segue o destino declarado** nessa página (meta refresh, `window.location` ou link `.pdf`) — e continua sem adivinhar URL alguma.
- **DF e SP — obstáculo real de rede**, não corrigível por parser: *timeout* de handshake TLS (~45 s), idêntico com os dois User-Agents. O Querido Diário responde 200 no mesmo runner, o que descarta rede ruim. Fica registrado para decisão editorial.

Três autotestes novos, um por correção. Nenhum coletor publicou dado parcial em nenhum momento: o desenho defensivo entregou lacuna auditável, que foi o que permitiu diagnosticar.

## Correção · evidências de texto preservadas à mão colidiam com `preservar_evidencias --ler` · 11/09/2026

Nenhuma alteração de método; nenhum número muda. Classe **código + dado** (PROTOCOLO §3.2). **Achado por ensaio** (`workflow_dispatch` com `ensaio=true`), antes de qualquer publicação — é exatamente o que o modo ensaio existe para pegar.

- **Sintoma.** Portão 6 vermelho na rodada real com "conteúdo não bate com o hash" para a evidência de Itajaí/SC. Invisível localmente: sem rede, nenhum PDF é rebaixado e o hash bate.
- **Causa-raiz.** As três evidências criadas manualmente em 10/09 (Itajaí/SC, São Gonçalo/RJ e o plano estadual de SP) registraram `arquivo: evidencias/<h>.txt` com `h` = sha256 **do texto** que foi redigido a partir do PDF. Mas a convenção do projeto é outra: `evidencias/<h>.txt` é o texto extraído do documento cujo **binário** tem hash `h`. Como a URL de origem termina em `.pdf` e o item não tinha `texto_arquivo`, `preservar_evidencias.py --ler` elegia o item como alvo, rebaixava o PDF e regravava `evidencias/<h>.txt` sob o mesmo nome — o conteúdo deixava de bater com a chave e o portão fechava o job **antes do commit**.
- **Consequência já ocorrida:** foi isto que derrubou a rodada agendada de **10/09 às 21h** (39,5 min, falha no passo de relatório após o portão) e o ensaio de 11/09. Em ambas, os dados foram coletados mas **não foram gravados**.
- **Correção.** Os três itens ganham `texto_arquivo`, `texto_hash` e a marca **`texto_manual: true`**, com a convenção explicada na própria nota do item. `preservar_evidencias.py`: `--ler` exclui explicitamente itens `texto_manual` (não reextrai) e `--reconferir` os pula (comparar com o hash do binário divergiria sempre e publicaria **evento falso** de "documento-fonte alterado" no feed).
- **Teste negativo permanente** em `verificar_evidencias.py`: item com `arquivo` `.txt` + URL `.pdf` **sem** `texto_manual` é erro de integridade. Verificado nos dois sentidos — reintroduzindo a falha o portão fica vermelho; com a correção, verde.

## §36 · SP — quarto instrumento estadual de governança do ciclo, lido na íntegra · 10/09/2026

Nenhuma alteração de método (§12.5); nenhum número do índice muda. Classe **dado** (PROTOCOLO §3.2). Peso zero.

- **Localizado e lido:** Plano Estadual de Preparação e Resposta em Saúde para o Fenômeno El Niño 2026-2027 (SES-SP, 31/08/2026, 43 páginas). Preservado como evidência com hash; registrado em `instrumentos.json` e `fontes_uf.json`.
- **Placar de instrumentos de governança do ciclo: 3 → 4 de 27** (RJ, SC, MT, SP). SP é o **primeiro plano de contingência de saúde** do ciclo — os outros são comitê/decreto (RJ, SC) ou Sala de Situação (MT).
- **Conteúdo verificável:** estágios mobilização/alerta/emergência + desmobilização/recuperação; 11 de 17 regiões de saúde prioritárias para arboviroses; 7 áreas prioritárias para chuvas extremas; CIEVS 24h; continuidade de cuidado nomeada para diálise, oncologia, oxigenoterapia domiciliar e gestantes.
- **Regra de robots.txt confirmada pela segunda vez no dia:** o portal recusa robô, mas o PDF é público e abre no navegador — lido por navegação real. Bloqueio a robô não é evidência de indisponibilidade ao cidadão.
- **Cautela registrada:** um recurso do CVE-SP devolveu `Blocked country: [Brazil]` em acesso automatizado; o runner da Action pode ver conteúdo diferente do navegador local.
- **Coletor de desfecho de SP não escrito**, com motivo declarado: os dados abertos por município/SE do CVE estavam marcados "atualizados em abril/2026", defasados frente ao boletim semanal. Conferir a fonte corrente antes de codar.

## §36 · quarto coletor estadual (PB, por Região de Saúde) e dois estados sem fonte coletável (BA, CE) · 10/09/2026

Nenhuma alteração de método (§12.5); nenhum número muda. Classe **código + dado** (PROTOCOLO §3.2). Peso zero; nunca lido pelo motor.

- **Novo — PB:** `coletar_boletim_pb_arboviroses.py` lê o Boletim de Arboviroses Urbanas da SES-PB. Quadro 01 em texto com as **16 Regiões de Saúde** (população, prováveis de dengue/chik/zika/Oropouche, 5 incidências) + Fluxograma por agravo. Íntegra conferida no nº 03/2026 (SE 08). Portão (t). Melhor formato depois de MS.
- **Correção de registro (PB):** a numeração é sequencial e **irregular** (nº 02 ≈ SE 05, nº 03 = SE 08) — não acompanha a SE; e o padrão de URL real não é `no_01_2026.pdf`, como suposto em 09/09. O coletor tenta números decrescentes e lê a SE do texto.
- **Divergência da fonte registrada, não corrigida:** no nº 03 o texto corrido diz 739 prováveis de arboviroses e o Quadro 01 totaliza 738. Publicado o do Quadro (auditável linha a linha), com a divergência anotada em `divergencia_fonte`.
- **BA — SEM FONTE COLETÁVEL:** boletins de arboviroses da SESAB param na **SE 24/2021**; os números de 2026 só aparecem em notícias, sem documento periódico. DTHA é anual, não série.
- **CE — SEM FONTE COLETÁVEL DE DESFECHO:** repositório ativo, mas sem série regular de arboviroses; o item recente (25/02/2026) é **entomológico** (vetor), não desfecho. DDA/DTHA de 2018 e 2022.
- Ambos marcados em `fontes_uf.json` com data e motivo da verificação, para a próxima sessão não repetir a busca. Ausência de publicação periódica é achado do §36, não falha da coleta.

## §36 · terceiro coletor estadual: arboviroses em PE (CIEVS-PE) — só totais estaduais, tabela municipal é imagem · 10/09/2026

Nenhuma alteração de método (§12.5); nenhum número muda. Classe **código + dado** (PROTOCOLO §3.2). Peso zero; nunca lido pelo motor.

- **Novo:** `coletar_boletim_pe_arboviroses.py` lê o Informe Epidemiológico semanal do CIEVS-PE (dengue, chikungunya, Zika; óbitos por arboviroses; LIRAa). Íntegra conferida no informe "SE 01 a 34" (captado 31/08, publicado 03/09/2026). Grava `data/saude_desfechos/ses_pe_arboviroses.json`; ligado em `atualizar.py` após o de DF.
- **Limitação declarada (a primeira estrutural desta frente):** o informe é PDF-infográfico e a **Tabela 1 por município é imagem** — não lida por máquina. O coletor entrega **só totais estaduais**; a granularidade municipal de PE fica no painel Power BI, não automatizável. Registrado em `fontes_uf.json` e no campo `escopo` do arquivo de dados. O documento de transferência esperava "parecido com MS"; não é.
- **Parser para infográfico:** página como unidade; só números adjacentes ao rótulo; escolha por identidade `notificados = prováveis + descartados` (fechou nos 3 agravos); recusa se não fechar de forma única. Rótulos sensíveis a maiúsculas (legendas de gráfico são minúsculas e enganavam a leitura).
- **Portão (s)** em `verificar_saude.py`: motor não referencia; ressalva presente; `escopo = totais_estaduais`; identidade fecha em cada leitura; `confirmados ≤ prováveis`.
- **Risco assumido e contido:** parser afinado contra a extração do `web_fetch`; o runner usa `pdfplumber`. Se a ordem interna diferir, o resultado é lacuna com amostra do texto extraído (diagnosticável na próxima sessão), nunca número mal associado. Primeira leitura real: próxima rodada da Action.
- **Catálogo:** `dengue` e `chik` ganham o CIEVS-PE como fonte (totais estaduais); não há id próprio para Zika no catálogo (fica dentro de arboviroses).

## §36 · segundo coletor estadual de desfechos: arboviroses no DF (SES-DF), com correção de registro · 10/09/2026

Nenhuma alteração de método (§12.5); nenhum número muda. Classe **código + dado** (PROTOCOLO §3.2). Peso zero; nunca lido pelo motor.

- **Novo:** `coletar_boletim_df_arboviroses.py` lê o Informativo Epidemiológico semanal da SES-DF (dengue, chikungunya, Zika, febre amarela; por Região de Saúde). Íntegra conferida no Nº 34 (SE 34/2026, extraído em 31/08, publicado em 03/09/2026). Grava `data/saude_desfechos/ses_df_arboviroses.json`; ligado em `atualizar.py` logo após o coletor de MS.
- **Portão (r)** em `verificar_saude.py`: motor não referencia o arquivo; ressalva de não-atribuição presente; cada leitura tem as 7 Regiões de Saúde, soma fecha com o N declarado, IBGE = 5300108.
- **Correção de registro** em `fontes_uf.json`: a fonte do DF é **semanal**, não "mensal (última sexta-feira do mês)" como anotado em 09/09 — o texto mensal na página é resíduo de 2022. A confusão vinha de a página ser truncada pela busca automática antes do painel de 2026; navegador real mostrou 34 informes semanais em 2026.
- **Catálogo:** `chik` passa de *candidato* a *coletado*; `dengue` ganha a SES-DF como fonte (ao lado de InfoDengue e SES-MS).
- **Defensivo:** recusa (e declara lacuna) se faltar região ou se a soma das regiões não fechar com o N — 11 autotestes contra o texto real, 2 deles de recusa. Fica FORA do escopo: série histórica (o informe traz só o acumulado do ano; a série é construída daqui em diante).

## Portão 6 · São Gonçalo/RJ resolvido com o documento real (correção sobre a entrada anterior) · 10/09/2026

Nenhuma alteração de método; nenhum número muda. Classe **dado** (PROTOCOLO §3.2).

A entrada anterior deste CHANGELOG (mesma data) registrava São Gonçalo/RJ como bloqueado por `robots.txt`, com um pedido de LAI preparado como saída. Antes de enviá-lo, a editoria pediu para não usar bloqueio de robô como motivo do pedido — a LAI não exige justificativa, e citar isso seria enganoso se o documento já estivesse público. Verificação humana confirmou: **o PDF do PLAMCON estava, e sempre esteve, disponível para download direto** em `pmsg.rj.gov.br` (domínio distinto do bloqueado); a página descritiva em `saogoncalo.rj.gov.br` só não linkava para lá de forma óbvia.

- **Correção.** Localizado e preservado o PLAMCON 2025/2026 completo (aprovado 16/12/2025, válido até 30/11/2026), navegação real via extensão Claude para Chrome — não fetch automatizado. `url`, `documento`, `data`, `fonte` e `hash_evidencia` atualizados no registro; texto de 107 páginas preservado em `evidencias/`.
- **Sem LAI enviada.** O rascunho preparado para a Ouvidoria de São Gonçalo foi descartado sem envio.
- **Lição registrada:** antes de qualquer pedido de LAI motivado por "acesso automatizado bloqueado", verificar por navegação humana real se o documento já está público — um bloqueio ao robô não é o mesmo que o documento estar indisponível ao cidadão, e a LAI é para o segundo caso.

## Portão 6 · evidência de 3 registros investigada (§2.5 do redesenho, decisão da editoria 10/09/2026) · em publicação (PR)

Nenhuma alteração de método; nenhum número muda. Classe **código + dado** (PROTOCOLO §3.2). A editoria autorizou duas saídas para os 3 registros sem evidência preservada apontados no portão 6 (bloqueante a partir de 15/09/2026): localizar o documento em outra fonte oficial, ou gravar snapshot no Wayback. Resultado, registro a registro:

- **Itajaí/SC — resolvido.** A URL registrada (`www.defesacivil.sc.gov.br`) era a home da Defesa Civil **estadual**, não um documento — não existia evidência possível de preservar ali. Localizado o documento correto: Plano de Contingência de Desastres do próprio município, publicado pela COMPDEC de Itajaí (versão 17, alterado 22/12/2025), em `defesacivil.itajai.sc.gov.br`. Texto preservado em `evidencias/<hash>.txt` (seções estruturais e a tabela de subfases de alerta por estação de monitoramento na íntegra; a relação nominal de contatos de agentes públicos e o detalhamento por secretaria — repetitivo e extenso — resumidos, para não reproduzir em massa dados de contato pessoal; documento completo de 68 páginas segue publicado na fonte). `documento`, `fonte`, `url` e `hash_evidencia` atualizados no registro.
- **Ouro Branco/AL — causa-raiz corrigida, evidência pendente da próxima rodada.** A URL apontava para o território `2700000` no armazenamento do Querido Diário — não é o código IBGE de Ouro Branco/AL (**2706109**, confirmado em `municipios_ibge_referencia.json`); provavelmente um erro de digitação na coleta original que nunca resolveria, independente de qualquer novo download. URL corrigida para o território correto. A rede deste ambiente de edição não alcança `data.queridodiario.ok.org.br` (só GitHub/PyPI/TSE) para baixar e preservar o binário agora; `preservar_evidencias.py` deve resolver isso sozinho na próxima rodada automática, com a URL já corrigida.
- **São Gonçalo/RJ — parcialmente resolvido, bloqueio de robots.txt.** A URL registrada era uma notícia sobre o plano, não o plano; corrigida para a página dedicada (`saogoncalo.rj.gov.br/defesa-civil-2/plano-de-contingencia/`). O domínio da prefeitura recusa acesso automatizado (`robots.txt`), e este projeto não contorna `robots.txt` (regra permanente, `TRANSFERENCIA_ROTINA_JULGAMENTO_DE_PISTAS.md`) — nem eu (fora do sandbox) nem `preservar_evidencias.py` conseguem baixar o documento por esse caminho. Sem Wayback disponível para a página no momento da checagem. Este registro segue sem evidência preservada; candidato a pedido de LAI, ou aguardar novo esforço de Wayback antes de 15/09.

## Correção · carimbo `gerado_em` dos derivados após a rodada automática · 10/09/2026

Nenhuma alteração de método; nenhum número muda. Classe **código** (PROTOCOLO §3.2). Rotina diária: portão 12 (`verificar_derivados.sh`) ficava vermelho na `main` a cada rodada que avançava `data/meta.json.atualizado_em`, exigindo regeneração manual (como em `dfc7940`, `229d28c`).

- **Causa-raiz.** Em `atualizar.py`, `gerar_monitor_saude.py`, `gerar_resposta.py` e `gerar_contadores_financiamento.py` carimbam `gerado_em` com o `atualizado_em` de `data/meta.json` (data determinística, para o portão 12 reproduzir byte a byte), mas rodavam **antes** de `meta["atualizado_em"] = hoje` ser gravado. Toda rodada que avançava a data deixava esses derivados um dia atrás.
- **Correção.** `atualizar.py` reexecuta os três geradores logo após gravar `data/meta.json` (idempotente: função pura dos dados da rodada; só o carimbo muda). PDFs e manifesto continuam selados depois, no workflow.
- **Teste.** `bash scripts/verificar_derivados.sh` em árvore limpa não altera nenhum arquivo de dados — só o hash de `atualizar.py` no manifesto, refletindo esta mudança.

## 10/09/2026 — Texto integral em TODAS as buscas (extensão do PR #114)

- A preservação do documento inteiro no momento da coleta, criada no PR #114 para o
  coletor municipal, passa a valer em **todos os canais de descoberta**: `coletar_doe.py`
  (braço Querido Diário dos DOEs), `consultar_querido_diario.py` (varredura ad hoc — cada
  achado ganha evidência própria: `.json` do registro + `.txt` integral) e os três vigias
  de imprensa via `registrar()` compartilhado (`monitorar_imprensa_regional.py`,
  `monitorar_atos_resposta.py`, `monitorar_politica_por_inteiro.py`), que agora preservam
  a própria página no ato do registro (proteção contra link rot e portais que bloqueiem
  acesso automatizado depois).
- `scripts/preservar_textos_integrais.py` ganha **recuperação por URL indexada**: evidência
  com arquivo perdido (caso Serra/ES, 03/09) é re-buscada; `.json` só é restaurado se o
  sha256 bater com o hash original — divergência vira nota declarada no índice e o texto
  integral é preservado a partir da resposta atual, com URLs de origem no arquivo.
- Nada muda em pista, registro, categoria ou nota; a regra de prova segue idêntica.

## 10/09/2026 — Julgamento de pistas, lote 1: Ouro Branco/AL promovido a `plano`

- **Lidas:** 1 pista (cobrindo 2 cópias relogadas do mesmo achado, `hash` único).
  **Promovidas:** 1. Ouro Branco/AL sobe de `decreto` para **`plano`** — Decreto Municipal
  nº 021, de 10/07/2026, lido **na íntegra** (texto integral preservado em `evidencias/`):
  institui o PLACOM, Plano de Contingência Municipal para Estiagem e Seca, **elaborado**
  pela Coordenadoria Municipal de Proteção e Defesa Civil, com competências, Gabinete de
  Crise e revisão bienal. O registro anterior (`decreto`) apoiava-se em fonte secundária e
  citava o Decreto 22 — que é a **declaração de emergência**, não ato preventivo; a leitura
  integral corrige a base documental do registro. Ressalva anotada: o conteúdo do PLACOM
  não está impresso no diário; o ato que o institui, sim, com número e data.
- **Efeito na nota:** nenhum. AL segue 12 atos / 102 municípios (11,76%); composição muda
  de 1 `plano` + 11 `decreto` para 2 `plano` + 10 `decreto`. Sem errata, portanto.
- **Mapa de transparência (resposta, peso zero):** entra o Decreto Municipal nº 022, de
  10/07/2026 — Situação de Emergência por Estiagem em Ouro Branco/AL (S2iD
  AL-F-2706109-14110-20260708; reconhecimento federal em 27/07/2026). Achado pela
  leitura do texto integral: o excerto da API só trazia o PLACOM — exatamente a cegueira
  que a mudança de 10/09 (evidência com texto integral) elimina.
- Julgamento humano registrado nas duas cópias da pista em `data/pistas_imprensa.json`.

## 10/09/2026 — Evidência passa a incluir o texto integral da edição (infraestrutura)

- **O que muda:** toda pista de diário municipal (Querido Diário) passa a preservar,
  além do excerto da API, o **texto integral da edição** em `evidencias/<hash>.txt`,
  baixado no momento da coleta — o único momento garantidamente sem bloqueio de
  acesso (portais municipais podem recusar acesso automatizado depois; caso real:
  Ouro Branco/AL, 10/09). Novo `preservar_texto_integral()` em `coletores_base.py`,
  chamado por `coletar_diarios_municipais.py`.
- **Backfill:** `scripts/preservar_textos_integrais.py` + Action manual
  "Preservar textos integrais das evidências" completam as evidências já na fila
  (32 edições únicas cobrindo as 78 pistas de diário). Idempotente; só toca
  `evidencias/` e `data/evidencias.json`.
- **Caderno de pistas:** `scripts/caderno_de_pistas.py` entra no repositório
  (antes só na rotina de transferência), com três correções: mostra o nome real do
  arquivo de evidência (não assume `.html`), sinaliza se o texto integral existe,
  deduplica achados relogados (mesmo `hash_evidencia`) e exclui pistas C10 por
  padrão (§5 da rotina de julgamento — só entram com `--origem` explícito).
- **O que NÃO muda:** nenhuma pista, registro, categoria ou nota. A regra de prova
  (documento primário lido por humano) segue idêntica; isto só garante que o
  documento esteja sempre ao alcance de quem julga.

## v3.1.2 — paleta semântica única de figuras e mapas · 09/09/2026 · em publicação (PR)

Nenhuma alteração de método; nenhum número muda. Classe **design + código** (PROTOCOLO §3.2). Pedido da editoria (09/09/2026): "figuras e mapas em páginas distintas têm esquemas de cores distintas" — reconferir e corrigir.

### Correção: PDFs deixam de depender da versão do zlib do ambiente (10/09/2026)
- O portão de derivados falhou pela primeira vez nesta sessão — não por conteúdo, por
  **infraestrutura**: `METODOLOGIA.pdf` e `MARE_Indice_Documentacao.pdf` saíam com hash diferente
  no sandbox de edição e no runner do CI, mesmo com reportlab e pypdf idênticos nos dois. Causa
  identificada: compressão interna (FlateDecode) sensível à versão do zlib do sistema.
- Corrigido: `pageCompression=0` (sem depender do zlib do sistema; PDFs maiores, sem compactação)
  e `invariant=1` (fingerprint interno fixo) em `gerar_pdf_metodologia.py` e `gerar_pdf_indice.py`.
  Verificado por `--idempotencia` e três regenerações seguidas com hash estável.

### Coletor real: dengue por município a partir do boletim da SES-MS (10/09/2026)
- **Primeira fonte estadual efetivamente coletada** (não só catalogada): `coletar_boletim_ms_dengue.py`
  (7 autotestes, validado contra o texto real do boletim de SE 30/2026) lê o boletim semanal da
  SES-MS — tabela completa por município (IBGE, casos, população, incidência), totais estaduais e
  data de referência. Defensivo: localiza o post da semana por permalink, extrai o PDF de dentro da
  página, recusa publicar se vierem menos de 70 dos 79 municípios. Constrói a própria série semanal
  a partir de agora (a SES só dá o instantâneo + total anual). `data/saude_desfechos/ses_ms_dengue.json`;
  portão (q). Não pôde rodar de verdade neste ambiente (rede restrita); roda na rotina semanal.
- Catálogo: `dengue` ganha a segunda fonte (InfoDengue + boletim MS). `fontes_uf.json`: MS marcado
  como "coletor ativo".
- Levantamento de 8 estados com boletim/painel confirmado (SP, MG, CE, BA, DF, PB, PE, MS) — base
  para repetir o coletor, um parser por estado, já que cada SES publica num formato próprio.

### Varredura das 26 portarias estaduais restantes (10/09/2026)
- **Três instrumentos novos localizados, com data e número onde existe:** RJ (Comitê Estadual +
  Sala de Situação do El Niño, decreto de 03/07/2026, com câmara técnica de Saúde) e SC (Decreto
  nº 1.530/2026, "estado de alerta climático", com gatilhos numéricos que citam a saúde) — ambos
  liderados pela Defesa Civil, não pela Secretaria de Saúde. MT permanece o único liderado pela
  própria SES. `data/saude_desfechos/instrumentos.json`: 3 de 27 estaduais localizados.
- Nenhum instrumento novo achado para os outros 23 estados apesar da busca; para ES, registrado
  reforço operacional sem decreto/portaria nova (tentativa documentada, não achado).
- **Trilha nova e distinta registrada:** `planos_adaptasus` — status dos 27 Planos Estaduais de
  Adaptação do Setor Saúde às Mudanças Climáticas (AdaptaSUS, medida de médio prazo, não o ciclo
  2026/2027): BA/PA/PI concluído · MG/MA/RJ/MS em elaboração · demais 20 em fase inicial — fonte
  única (declaração ministerial na COP30, 30/06/2026), a confirmar estado a estado.

### Sala Nacional de Emergências Climáticas em Saúde localizada (09/09/2026)
- Preenchida a lacuna do §36: a peça de "governança federativa" do Plano El Niño é a **Portaria
  GM/MS nº 6.918/2025**, que institui a Sala de Situação Nacional de Emergências Climáticas em
  Saúde (COBRADE, DVSAT/SVSA, relatórios mensais, transferência ao DEMSP em calamidade de larga
  escala). Página institucional lida; DOU original não encontrado, só espelho de terceiro (registrado
  como tal, nunca como a fonte oficial).
- Dois "painéis de indicadores" da própria página do MS registrados com honestidade sobre o que são:
  **Seca na Amazônia** (Fiocruz) é agregador de links, não fonte própria; **VigiAr** é Power BI —
  mesma classe de obstáculo do Painel de Arboviroses (§9): não é fonte de máquina.

### O que foi encontrado (11 páginas, legendas lidas num Chromium real)
- **Faixas do MARÉ**: "Consolidado" era Musgo na pílula da inicial e Sintético no mapa de prontidão sanitária (Saúde); os selos em `selos/` ainda usavam a paleta anterior à v3 (`#C69B72`, `#6B6A44`, `#35566B`).
- **Status do instrumento estadual**: "Vigente, sem menção ao ciclo" era Âmbar na Defesa civil e Mineral na Saúde; "Em elaboração" e "Não localizado" alternavam entre Âmbar/Argila e Argila/Cinza conforme a página.
- **Famílias de risco**: "Chuvas" era Musgo nos Sinais de risco e Sintético na Saúde e na folha de estilo (`--chuva`); "Seca" alternava Âmbar, Argila e Mineral; "Fogo" Argila ou Âmbar.
- **Rampas contínuas de perigo** (avisos INMET, focos INPE, alertas CEMADEN): verde (Musgo) nos Sinais de risco, enquanto tudo o que é perigo/resposta no resto do site é quente (Argila).
- **Ordinais de intensidade** (dengue 1–4, calor 1–3+, seca S1–S4, quartis de MPs): quatro escalas diferentes para a mesma ideia "do brando ao grave"; o mapa de dengue do painel usava Bioluz/Âmbar/Argila/Vazio e a tabela por UF outra sequência.
- **Rotas do dinheiro** (Financiamento): as oito cores vinham do JSON com a paleta pré-v3 (`#35566B`, `#A65F3F`, `#C69B72`, `#87855C`, `#647A7E`, `#4F7D48`) — únicas figuras do site fora da paleta da marca.
- **Séries por ano**: 2024/2025/2026 com cores trocadas entre o gráfico semanal e o acumulado.
- Bug lateral: `MonitorMapas.cor('muted-token')` (nome inexistente) deixava três textos do diagrama de rotas sem cor válida.

### O que mudou
- **`MonitorMapas.PALETA`** (assets/mapas.js) passa a ser o único mapa conceito → cor: `faixas` (+ `faixasTexto`, `faixaDe`, `faixaRotulo`), `status`, `categorias`, `verificacao`, `risco` (= tríade `--chuva/--seca/--fogo` da folha), `consistencia`, `enso`, `preparacao`/`resposta`/`defeso`, `rampaPerigo` (quente) e `rampaPreparo` (verde), `ordinal4` (Mineral → Âmbar → Âmbar-escuro → Argila), `anos`, `rotas` (oito cores da marca, por família da chave de acesso), `chaves`, `temas`, `serie`.
- Todos os scripts de página (index, defesa-civil, sinais-de-risco, saude, financiamento, pesquisadores) leem cores de dado só da PALETA. A cor das rotas no JSON (`data/financiamento/rotas.json`) vira informativa: a página aplica `PALETA.rotas[id]`; `coletar_financiamento.py` grava as mesmas cores na próxima coleta.
- `gerar_selos.py` usa as cores de `PALETA.faixas` (Argila · Âmbar · Sintético · Musgo); 28 selos regenerados.
- Rótulos dos níveis de dengue do painel unificados com a tabela por UF ("nível 1 (baixa atividade)" … "nível 4 (emergência)").

### Portões
- **Portão 1 (`verificar_estrutura.js`)**: nos scripts de página, hex cru é proibido; `MonitorMapas.cor()` só aceita nomes existentes na paleta e só cores estruturais (traço, fundo, tinta, ausência de dado) — toda cor de dado tem de vir de `PALETA.*`; os blocos da PALETA são obrigatórios; a tríade de risco de `tokens.css` e a de `mapas.js` têm de ser a mesma cor. Testes negativos feitos.
- `verificar_consistencia.py` (nomes das faixas) lê `PALETA.faixaRotulo`; `verificar_runtime_financiamento.js` confere cartões, rede e série nas cores de `PALETA.rotas`, oito e distintas.

### Para decisão editorial (colisões dentro de uma mesma legenda, mantidas como estavam)
- Defesa civil, mapa municipal: "Plano em elaboração" e "Estrutura de coordenação" partilham Âmbar; "Decreto de emergência" e "Nenhum ato localizado" partilham Argila. A paleta tem só sete cores de dado distinguíveis; separar exige uma cor nova ou textura.

## Varredura integral concluída e correção de workflow · 09/09/2026

**Varredura municipal — encerrada.** A rodada de 08–09/09 (execução manual com `finalizar_varredura_hoje`, janela intensiva estendida até 10/09) consultou 2.765 municípios num só ciclo, fechando a varredura aberta em 03/09: 2.852 execuções no log (2.765 DOM, 46 DOU, 28 repositórios estaduais, 10 sítios municipais, 3 órgãos estaduais). Resultado: 83 achados com excerto para a fila humana, 81 municípios cobertos sem menção, 34 registros e 20 pistas; 2.128 municípios sem cobertura no Querido Diário — lacuna de fonte, declarada, não de consulta.
- **Restam 440 municípios sem diário consultado** (SP 188, PR 186, SE 39, RR 15, RN 11, AC 1), todos por erro de consulta na rodada (506 execuções com erro, concentradas nas mesmas UFs) — provável limite de taxa do provedor sob carga. Serão retomados nas rodadas de 09 e 10/09, ainda dentro da janela intensiva. No painel dos 313, 27 municípios seguem nessa condição.
- **Evidências:** a correção IRI→URI (PR #108) fez efeito — o portão 6 caiu de 71 para 3 registros sem evidência preservada.

## Correção de workflow · manifesto selado após os PDFs · 08/09/2026 · (ramo `edicao/2026-09-08-manifesto-no-workflow`)

- **Causa-raiz do portão 12 vermelho em dias de cadência:** em `atualizar.yml`, a etapa que regenera os PDFs roda mesmo quando `atualizar.py` encerra sem coletar, e o commit entrava sem regenerar `docs/MANIFEST_SHA256.txt`. O sintoma foi eliminado em 08/09 (PR #107: o PDF passou a ser determinístico); esta correção fecha a causa: `scripts/gerar_manifesto.py` roda sempre após a etapa dos PDFs, antes do commit, como manda o próprio cabeçalho do manifesto (portões → PDFs → manifesto).
- Nenhuma página, dado ou número muda.

## Errata e correção · evidências do ES · 08/09/2026 · em publicação (ramo `edicao/2026-09-08-evidencias-es-url`)

- **Achado da rotina diária:** 71 de 90 registros pontuáveis com URL estavam sem evidência preservada, 69 deles do repositório estadual do ES (`defesacivil.es.gov.br`). O log de buscas mostra a causa: **`UnicodeEncodeError` no nosso próprio cliente HTTP** (`coletores_base.buscar`) — as 69 URLs trazem "Contingência" com o "ê" cru no caminho, e `http.client` só envia ASCII. O sítio do ES não bloqueou nada; a lacuna era nossa.
- **Correção:** `coletores_base.url_ascii()` converte IRI → URI (percent-encoding do que sobrou fora do ASCII, preservando os escapes existentes) antes de toda requisição; `verificar_evidencias.py` ganha teste permanente (URL de exemplo do ES; URL já codificada intacta; toda URL de `municipios.json` ASCII após a conversão). Reproduzido e provado com servidor local: antes, `UnicodeEncodeError`; depois, download normal.
- **Errata de prazo, declarada:** o portão 6 passaria a bloquear em 10/09/2026, mas a primeira rodada do robô com a correção é **segunda 14/09** (fora da semana intensiva o robô só publica às segundas). Bloqueio adiado para **15/09/2026** — a regra continua a mesma; só a data de vigência muda, pelo motivo acima. Registrado aqui e em `docs/PROTOCOLO_ATUALIZACAO.md` §3.3.
- Restam 2 registros com `URLError` na Action (Itajaí/SC: a URL é a página inicial da Defesa Civil de SC, não um documento; São Gonçalo/RJ): se a rodada de 14/09 não os preservar, entram como pista para a editoria (documento a localizar ou snapshot no Wayback), não como mudança de regra.
- Como antecipar (opcional, sem tocar no código): definir as variáveis de repositório `INTENSIVO_DE` e `INTENSIVO_ATE` como `2026-09-10` faz a rodada de quinta publicar como dia intensivo; depois apagar as duas.


## Correção · data impressa no PDF do índice e manifesto obsoleto · 08/09/2026 · em publicação (mesmo lote da v3.1.2)

- **Achado (rotina diária):** o portão 12 (`scripts/verificar_derivados.sh`) ficou vermelho na `main` após o commit automático de 08/09 (`54dd91f`): `MARE_Indice_Documentacao.pdf` mudou (só a frase "gerado programaticamente em dd/mm/aaaa", que lia o relógio da máquina) e `docs/MANIFEST_SHA256.txt` não foi regenerado, porque `atualizar.py` encerra por cadência fora da semana intensiva e a etapa do workflow que regenera o PDF roda mesmo assim.
- **Correção mecânica:** `gerar_pdf_indice.py` passa a imprimir a data de `atualizado_em` de `data/meta.json` (a última atualização publicada dos dados), não o dia da geração — o PDF volta a ser função só dos dados publicados (R1 da auditoria de 29/08/2026), e o manifesto deixa de envelhecer nos dias sem atualização. PDF e manifesto regenerados. Sem mudança de método, de dado ou de número; a frase mantém a redação.

## v3.1.1 — auditoria de consistência visual e estrutural · 07/09/2026 · publicada em 08/09/2026 (PR #105, `d0c1e84`, endereço reservado)

Nenhuma alteração de método; nenhum número muda. Classe **design + código** (PROTOCOLO §3.2). Pedido da editoria: "nenhum elemento equivalente pode ter estilo próprio" — corrigir todas as inconsistências existentes antes de qualquer solução visual nova.

### Coletor de SRAG e síndrome gripal (09/09/2026)
- `coletar_srag_gripe.py` (6 autotestes): série InfoGripe (Fiocruz/FGV) nacional e por UF, leitura
  **defensiva** de colunas (por padrão, não por nome fixo — o formato não pôde ser conferido fora da
  rotina; falha alto em vez de adivinhar). Mesmo tratamento do §35: canal endêmico 2019–2025, 4 SE
  vazadas, ressalva de não-atribuição. Grava `data/saude_desfechos/srag_serie.json`; portão (p).
- Catálogo (§36): `srag` e `sg` passam de candidato a **coletado**. Card novo em Saúde: "SRAG por
  semana · Brasil, sobre o canal endêmico". Na rotina; primeira coleta real na próxima rodada.

### Estrutura de informação dos desfechos em saúde: instrumentos, catálogo, gatilhos, fontes por UF (09/09/2026)
- **O instrumento localizado e lido na íntegra:** Plano de Contingência para Emergências em Saúde
  Pública por Seca e Estiagem (MS/SVSA/DEMSP, 1ª ed. 2026, 92 pp., ISBN 978-85-334-2936-9) — Quadro 2
  (efeitos sobre a saúde), Quadro 5 (cenários e indicadores por estágio, com gatilhos numéricos),
  relatórios quinzenais de DDA/desnutrição/respiratórios, SSClima, dashboards com dados dos estados.
  Espelho estadual localizado: Sala de Situação em Saúde e Clima da SES-MT (DOE 13/08/2026, 40
  municípios, até 31/05/2027). Não localizados: documento integral do Plano El Niño (apresentado em
  26/08), portaria do painel de especialistas, plano federal de inundação (2019).
- **Quatro arquivos em `data/saude_desfechos/`**, peso zero, nunca lidos pelo motor (portão (o)):
  `instrumentos.json` (5 federais + 27 vagas estaduais), `catalogo.json` (20 desfechos com sistema,
  periodicidade, fonte aberta e status: 1 coletado, 18 candidatos, 1 sem fonte), `gatilhos.json`
  (17 gatilhos do Quadro 5 com o que o Monitor computa: o de decretos lê o contador — 4,3% vs
  limiar 8%), `fontes_uf.json` (onde cada SES publica; semeado com 17 instrumentos verificados).
- **Saúde:** seção "O que o plano nacional manda acompanhar" — catálogo e gatilhos renderizados dos
  JSONs, valor atual ao lado do limiar, sem semáforo próprio (o Monitor não declara estágio).
  Metodologia §36 com a ordem de construção: portarias estaduais → coletores (InfoGripe, Sivep-DDA,
  SIH por CID, Painel de Calor) → canal endêmico e ressalva para cada desfecho → gatilhos na página.

### O que foi encontrado (medido num Chromium real, 11 páginas × 3 larguras, antes da correção)
- **17 tamanhos de fonte computados** em uso (10,4 · 12 · 12,5 · 13,5 · 15 · 17 · 18 · 19 · 23 · 24 · 28 · 30 · 33 · 38 · 44 · 46 · 52 px) para oito papéis tipográficos.
- Famílias equivalentes com estilos divergentes no desktop: H2 (4 estilos), título de figura (3), crédito de figura (3), `.hint` (9), `.note` (5), versalete (5), painel (2), cartão (3), navegação (2); no celular, ainda mais.
- **47 créditos de figura em oito formatos** ("Fonte: X · 07/09/2026", "consultado em", "busca de", "corte", "carga", "Fontes:", com explicações anexas, e um vazio).
- **16 pares de figuras lado a lado** com subtítulo ou mídia em posição vertical diferente (1 a 20 px), por `max-width` inline (560/640 px) e alturas de canvas inline (220/230 px).
- **326 linhas de CSS local só em `index.html`** (redefinindo `body`, `h1`, `h2` com `!important`, `.wrap`, rodapé, tabela, botão) e mais 257 em outras dez páginas; **212 atributos `style=`** nas páginas (46 só na inicial), incluindo `font-size:12.5px`, `font-size:13.5px`, `font-size:15px` em texto.
- Numeração: seção **"0 · MARÉ · Saúde"**; gráficos da Defesa civil numerados 1, 2, 4, 5, 6 (sem 3); mapas "1, 1b, 2…"; em Sinais, mapas e gráficos recomeçavam do 1 na mesma página; `cartaoCiclo0` como id.
- Estrutura: `<main class="wrap">` dentro de `<div class="wrap">` (Saúde, Financiamento, Imprensa — conteúdo 48 px mais estreito que nas demais); acordeão "Registros e fontes" aninhado dentro do acordeão "Log" em Pesquisadores; `<li>` soltos numa `<div class="kit-grid">`; `</body></html>` e o bloco VLibras duplicados em Pesquisadores e Calendário; créditos de `#boxFontesMonit` e `#boxConsultas` chamados do script de Financiamento para figuras que vivem em Pesquisadores (nunca renderizavam); link "mapa 4 do monitor" de Proteja-se apontando para a inicial, onde não há mapas; kicker do masthead com texto diferente na inicial.

### Design system (assets/tokens.css — fonte única)
- **Tipografia (8 degraus, cada um com a própria entrelinha):** display 48 · h1 36 · h2 28 · h3 22 · h4 18 · corpo 16 · small 14 · caption 12. Fraunces peso regular para títulos (nunca bold), Archivo para corpo, Archivo Narrow para dado/versalete. Letter-spacing em dois tokens (`--ls-caps` .06em, `--ls-caps-largo` .14em).
- **Espaçamento (9 degraus):** 4 · 8 · 12 · 16 · 24 · 32 · 48 · 64 · 96, com papéis nomeados (`--esp-secao`, `--esp-painel`, `--esp-figura`, `--esp-grade`, `--esp-titulo`, `--esp-figura-legenda`).
- **Grade:** 1180 px, 12 colunas, gap 24, margens 24 (16 no celular); pontos de quebra 1020 e 640 (os únicos).
- **Figuras:** mapa sempre `aspect-ratio 480/460`; gráfico 260 px (340 px em largura total); tabela rolável até 480 px; diagrama das MPs 300 px.
- Cores: sem mudança (tema técnico de 05/09); dois tokens novos para o tooltip e a sombra.

### Componentes globais (assets/base.css — folha única, 510 linhas; todo CSS de página eliminado)
- **`.figura`** — componente único de figura científica: `<figure class="figura figura--mapa|--grafico|--tabela|--diagrama|--barras|--indicador [figura--largo]">` com `.figura-cat` (opcional) · `.figura-titulo` · `.figura-sub` (período · variável · unidade) · `.figura-midia` · `.map-legend` · `.figura-leitura` (opcional) · `.figura-pe` (crédito `.fonte-figura` + `.figura-num`). Título e subtítulo reservam duas linhas, por isso mídia, legenda e crédito ficam na mesma altura em figuras vizinhas; o pé é ancorado embaixo. **Todas as 51 figuras do site** (Defesa civil 15 · Saúde 13 · Financiamento 13 · Sinais 9 · Pesquisadores 1) usam essa estrutura; o contador e os prazos da inicial usam o mesmo crédito.
- **`.cartao`** — cartão de texto/indicador/documento (substitui `.card`, `.chart-box` usado como cartão, `.kpi`, `.tr-card`, `.export-box`), com variantes de acento por modificador.
- **`.panel`** com acentos por modificador (`panel--acento-teal|rust|ink|link|musgo`, `panel--destaque`) em vez de `style="border-top:…"`.
- **`.grade-figuras`** (2 colunas ≥ 1021 px, 1 abaixo) e **`.grade-cartoes`** substituem `.maps-grid`/`.charts-grid`/`.kit-grid`.
- Medidor, contador, mosaico de estados, cartões de estado/cidade, relógios de prazo, barras por UF, situação atual, fichas do Proteja-se, checklist, acordeões, formulários, botões, tabelas, rodapé: cada um com uma única regra, tokenizada.
- Utilitários mínimos (`u-mt-*`, `u-mb-*`, `u-muted`, `u-rust`, `nowrap`, `dado`) só com tokens, para as poucas exceções de ritmo.

### Créditos, legendas e numeração
- **Formato único de crédito**, gerado só por `MonitorMapas.credito(id, {fontes, data, url})`: "Fonte: órgão · documento · Atualização: dd/mm/aaaa" ou "… · Atualização: sem coleta até o corte". Texto livre é recusado pela função (lança erro). Todos os 60+ pontos de chamada nos seis scripts foram convertidos; datas normalizadas (aceita dd/mm/aaaa com hora e aaaa-mm-dd).
- Toda figura passou a ter crédito — os 11 mapas e gráficos de antecipação da Defesa civil não tinham nenhum.
- **Legenda:** um estilo (`.map-legend`), inclusive a escala contínua, que tinha `font-size:12.5px` inline no motor de mapas.
- **Numeração automática, índice + 1:** `assets/colunas.js` escreve "Figura N" em toda `.figura` e "N · " nos H2 das páginas de dados (`body.pagina-dados`: Defesa civil, Sinais, Saúde, Financiamento, Imprensa, Calendário) na ordem do documento. Nenhum número fica escrito à mão no HTML (portão 1 bloqueia). Ids internos `cartaoCiclo1…4`.
- Motor de gráficos e mapas: fonte dos rótulos em 12 px (era 11,5 e 11); textos do diagrama de rotas em 12/14 (eram 10,5 · 11 · 12,5 · 13); relógio de prazo em 28/12.

### Exceções eliminadas
- 11 blocos `<style>` de página (583 linhas), incluindo as regras `h2{font-size:28px !important}`, `h3{19px !important}`, `.hint{15px !important}`, `.note{13.5px !important}`, `h1{font-weight:500 !important}`, `#meuCard h4{margin:18px 0 8px !important; font-size:17px !important}` da inicial.
- 197 atributos `style=` de tipografia, espaçamento, cor e largura (restam 15 na inicial, todos posicionais e dirigidos por dado: `left:25%`, `--galvo`, `width:0%`).
- `max-width:560px`/`640px` em três mapas; `height:230px`/`220px` em dois gráficos; `margin-top:6px` num crédito; `font-size:15px` no botão "×"; `font-size:12.5px` em rodapés e notas; `flex:1 1 460px`, `line-height:0` e `display:block; text-decoration:none` inline em logotipos.
- Tamanhos 12,5 · 13,5 · 15 · 17 · 19 · 23 · 38 · 52 · 44 · `clamp(...)` — todos mapeados para a escala.

### Portões
- **Novo portão 18 — `scripts/verificar_consistencia_visual.js`** (Playwright, 1366 · 900 · 390 px): falha se uma família de elementos equivalentes tiver mais de um estilo computado, se algum `font-size` computado estiver fora da escala, se figuras lado a lado tiverem largura, altura ou posição de título/subtítulo/mídia diferentes, se algum crédito fugir do formato único, se a numeração não for 1, 2, 3… ou se houver rolagem horizontal. Teste negativo executado (token `--fs-h3` alterado para 21 px → acusado; restaurado → verde).
- **Portão 1 (`verificar_estrutura.js`) endurecido:** escala nova; proíbe `<style>` na página, tipografia/espaçamento em `style=` (HTML e HTML gerado por script), classes legadas (`map-box`, `chart-box`, `map-card-h`, `card`, `kpi`…), numeração à mão em títulos, `font-size` em px e espaçamento fora dos tokens em `base.css`; exige a estrutura completa de `.figura`. Teste negativo executado (h1 com `font-size:15px` → acusado).
- `verificar_figuras.js` (formato único de crédito, nove páginas), `verificar_runtime_*`, `verificar_saude.py`, `verificar_financiamento.py`, `verificar_palavras.js` atualizados para o componente. `verificar_financiamento.py` deixa de exigir em Financiamento créditos de figuras que vivem em Pesquisadores.
- `portoes.yml` não foi tocado (o token da sessão não tem escopo `workflow`): o portão 18 entra no CI quando o token clássico for usado; até lá roda localmente (`npm run verificar:visual`).
- **08/09/2026 — regra de merge:** por decisão escrita da editoria, Claude passa a fazer o merge dos PRs que abre, condicionado aos 18 portões locais e à Action "Portões" verdes; lançamento e reversão do domínio seguem com a editoria (PROTOCOLO §3.1 e §5 atualizados).
- **08/09/2026:** resolvido — o portão 18 entrou no `portoes.yml` (passo próprio, após o portão móvel, no mesmo Chromium), com token fine-grained que passou a ter a permissão Workflows.

### Páginas revisadas
As 11: index · defesa-civil · sinais-de-risco · saude · financiamento · proteja-se · pesquisadores · envie-dados · imprensa · calendario-eleitoral · obrigado — masthead, navegação e rodapé gerados do mesmo molde; 24 portões verdes, portão móvel (390 px) verde, portão 18 verde nas três larguras.

### Rebase sobre a main (PR #104, "Envie um plano ou decreto")
- O ramo foi construído sobre `825bd24` e reaplicado sobre a `main` já com o PR #104: a navegação das 11 páginas mantém a ordem e o CTA "Envie um plano ou decreto" (último item), `envie-dados.html` mantém título, metadados e âncoras do #104, e `verificar_estrutura.js` continua exigindo essa ordem.
- Para a navegação continuar numa linha só no desktop (regra da editoria de 03/09) com o CTA mais longo, o ajuste do #104 (`letter-spacing:.02em`, separadores com margem 2 px) entra pelo sistema de tokens: novo token `--ls-nav: .02em` em `tokens.css`, aplicado só a `.mainnav a/span`, e separadores sem margem própria (o espaçamento vem do `gap` da grade). Medido em Chromium a 1366 px: 1083 px necessários para 1132 px disponíveis, altura da navegação 36 px nas 11 páginas.

### O que ainda não pôde ser padronizado (declarado)
- Numeração e créditos dependem de JavaScript (como todo o conteúdo do site, que é carregado de `data/`); sem JS a figura fica sem "Figura N".
- O kicker do masthead ganhou o mesmo texto em todas as páginas ("… · Uma publicação Futura Evidence Lab"); se a editoria preferir a versão curta na inicial, é uma linha em `index.html`.
- Cores de dado em `style="background:…"` nas legendas e barras continuam inline por serem dirigidas pelo dado (a paleta vem de `MonitorMapas.cor`, nunca de hex solto — portão 1).

## v3.1 — "edição narrativa" · 06/09/2026 · fechada (documentos de transferência REDESENHO_NARRATIVO_MARE_v3_1 e INSTRUCOES_diarios_defeso_LAI)

Nenhuma alteração de método (§12.5); tudo o que entrou tem peso zero. Nove PRs na ordem do §16, mais o PR-N0 (instruções complementares, com precedência) e o N0b (diagnóstico). Média nacional inalterada: 43,6 (v3.0, corte 31/08/2026).

### Correção: data impressa no PDF do índice e manifesto obsoleto (08/09/2026, rotina diária)
- **Achado:** o portão 12 (`scripts/verificar_derivados.sh`) ficou vermelho na `main` após o
  commit automático de 08/09 (`54dd91f`): `MARE_Indice_Documentacao.pdf` mudou (só a frase
  "gerado programaticamente em dd/mm/aaaa", que lia o relógio da máquina) e
  `docs/MANIFEST_SHA256.txt` não foi regenerado, porque `atualizar.py` encerra por cadência
  fora da semana intensiva e a etapa do workflow que regenera o PDF roda mesmo assim.
- **Correção mecânica:** `gerar_pdf_indice.py` passa a imprimir a data de `atualizado_em`
  de `data/meta.json` (a última atualização publicada dos dados), não o dia da geração — o
  PDF volta a ser função só dos dados publicados (R1 da auditoria de 29/08/2026), e o
  manifesto deixa de envelhecer nos dias sem atualização. PDF e manifesto regenerados.
- **Sem mudança** de método, de dado ou de número; a frase mantém a redação.

### Nome do envio: "Envie um plano ou decreto" (07/09/2026, escolha da editoria)
- O CTA passa a nomear o que se entrega, e não a ação genérica: serve ao gestor ("meu plano") e ao
  cidadão ("o decreto que vi no diário"), sem possessivo que exclua um dos dois. Título da página,
  descrição e dados estruturados refeitos; as duas portas viram "Sou gestor: como publicar" e
  "Encontrei um plano ou decreto: enviar".
- Com o rótulo mais longo, o botão passa a **fechar a barra**, em linha própria: as nove seções
  cabem numa linha na ordem da editoria (O monitor · Risco climático · Proteja-se · Defesa civil ·
  Saúde · Financiamento · Pesquisadores · Imprensa) e a ação fica visualmente separada delas.
  Densidade da barra ajustada em telas ≥ 1021 px.

### Navegação, fusão Gestores→Enviar dados e Pesquisadores sob demanda (07/09/2026, pedido da editoria)
- **Ordem da barra:** O monitor · Risco climático · **Proteja-se** · Defesa civil · Saúde ·
  Financiamento · **+ Enviar dados** · Pesquisadores · Imprensa.
- **O CTA deixa de parecer "sempre marcado":** era o mesmo Musgo sólido do indicador de página
  atual. Agora é contorno (preenche no hover e quando a página está aberta). Ganhou o "+" para
  marcar que é ação, não seção.
- **"Para gestores" fundiu-se em "Enviar dados"** (redirecionamento 301): a página abre com duas
  portas — "Sou gestor público" e "Quero enviar um documento" — e o checklist de publicação e a
  base legal viraram acordeões dentro da seção do gestor, antes do formulário, que serve aos dois
  públicos. Título e descrição refeitos para as duas intenções de busca.
- **Pesquisadores reconfigurada:** só Metodologia e Dados abertos ficam visíveis; log de
  verificação, painel amostral, fontes dos sinais, fontes do financiamento, como usar e código
  viraram sete acordeões fechados. Link com âncora abre sozinho o acordeão que contém o alvo.
- Portões atualizados (ordem canônica, listas de páginas, orçamento de palavras da página fundida).

### Relógios de prazo, e-mails e o que "verificado" quer dizer (07/09/2026, pedido da editoria)
- **"Prazos em curso" vira relógios:** anel SVG que esvazia da data-base ao vencimento (Âmbar; Argila
  abaixo de 30 %; Mineral apagado quando transcorrido), dias no centro, e para cada prazo **"O que se
  espera"** — texto curado em `marcos_prazos.json` (ADPF 743: decisão do relator sobre as correções;
  MPs: caducam se não votadas, o empenhado fica). Mesmo desenho nas MPs do Financiamento.
  Renderizador compartilhado `MonitorMapas.relogio()`.
- **E-mails:** contato@futuraevidencelab.com.br nos rodapés e contatos gerais;
  imprensa@futuraevidencelab.com.br na página de Imprensa.
- **Verificação municipal, dito com clareza:** os 5.571 municípios passaram pelas fontes nacionais
  (DOU/SEDEC, MUNIC/ICM); o que varia é a consulta ao próprio diário oficial (2.807 até agora). O
  quinto número da inicial passa a ser "municípios cujo diário ainda não foi consultado" (2.764), e
  a face dos cartões diz "diário consultado: X de N" — em vez de "0 verificados além do nacional".
  `verificacao_resumo.json` ganha a varredura por UF.

### SEO (07/09/2026, pedido da editoria: referência nacional, fácil de encontrar)
- **Cada página:** título único e descritivo (com "El Niño 2026/2027" e o tema), descrição única
  (70–170 caracteres), canônica em monitorelnino.com.br, Open Graph e Twitter Card com um **cartão
  social** de 1200×630 (logo, título, três números), `robots` "index, follow".
- **Dados estruturados (JSON-LD):** WebPage em todas as páginas; na inicial, `Dataset` (índice MARÉ,
  CC BY 4.0, CSV e datapackage como distribuições, cobertura temporal do ciclo) e `WebSite`, com a
  organização (Futura Evidence Lab).
- **`sitemap.xml`** (12 páginas + metodologia, documentação e datapackage) e **`robots.txt`** do
  domínio (com a linha Sitemap; `data/` e `evidencias/` fora do índice). A **prévia** passa a sair
  sempre com `X-Robots-Tag: noindex` e robots de bloqueio, para nunca competir com o domínio.
- **Portão `verificar_seo.js`** na suíte: títulos e descrições únicos e no tamanho, canônica, OG,
  Twitter, JSON-LD válido, um `<h1>`, sitemap completo, robots com sitemap, cartão presente.
- **Pendente da editoria:** Google Search Console (verificação por DNS ou meta tag) e, no lançamento,
  trocar o `Disallow: /` da cortina.

### Inicial: "Como ler o MARÉ" num bloco só; bloco pós-eleitoral oculto até ter dado (07/09/2026)
- Saem as três notas empilhadas (nota baixa · período eleitoral · o que mede). Fica um bloco: as três
  frases (o que mede · o que não mede · o teto da afirmação, que absorve "por que a nota baixa
  importa") e uma linha do período eleitoral com os links "o que a lei deixa aberto" e "metodologia".
- "O que o período eleitoral escondeu" deixa de ocupar a inicial vazio: aparece em 26/10, com dado.
  Inicial em 671 palavras.

### Padrão de figuras, situação atual e vocabulário (07/09/2026; documento de UX da editoria)
- **Toda figura de dado** nas cinco páginas de dados passa a ter: título; **subtítulo padronizado**
  (período · variável · unidade, uma linha, Archivo Narrow); legenda no padrão da casa; **crédito no
  formato único** "Fonte(s): … · dd/mm/aaaa" (ou "sem coleta"). 50 subtítulos escritos; 9 créditos
  ganharam data. Portão de figuras ampliado (título obrigatório, um subtítulo ≤ 140 caracteres,
  crédito começando por "Fonte" e datado).
- **Dimensões equivalentes por classe:** gráficos em 260 px (padrão) ou 340 px (`.h-alta`, para
  dispersões), nada inline; mapas sempre 480×460.
- **Nível 1 no Risco climático — "Situação atual":** estado do ENOS, intensidade (escala do CPC
  sobre o ONI observado; projeção do Boletim nº 3), tendência (variação do ONI em dois trimestres),
  indicador principal, probabilidade, última atualização por fonte, e o diagnóstico em três frases
  com **observação, interpretação e projeção separadas** — tudo calculado dos dados.
- **Vocabulário:** ENOS (El Niño–Oscilação Sul) e TSM em todo o site; decimais com vírgula.
- Os subtítulos não contam como prosa no portão de palavras (são metadados de figura).

### Primeira série real de desfechos e primeira fila R7 (07/09/2026, rodada de 17h50)
- **Desfechos:** 313 de 313 municípios do painel com série InfoDengue 2019–2026; última SE
  disponível 34/2026; últimas 4 vazadas → última consolidada SE 30. Painel na SE 30: 1.560 casos
  notificados contra mediana de 1.202 e p90 de 2.334 no canal endêmico — dentro do canal no
  agregado, mas **64 municípios acima do p90** (epidêmicos na própria escala), concentrados em AC,
  AL, AM, AP. Acumulado do painel: 2024 813.940 · 2025 261.457 · 2026 89.468 (até a SE 34).
- **Leitura contínua:** 7 PDFs de planos ganharam texto por página; 7 pré-classificações na fila
  R7 (5 "riscos do ciclo", 2 "resposta"). Correção do classificador: "2026/2027" sozinho era
  rótulo de temporada, não risco do ciclo (falso positivo em Afonso Cláudio). A fila marca
  **divergência** com leitura humana confirmada: Recife — humana 3, automática 5 ("ondas de
  calor" na p. 24, em texto sem espaços que a leitura humana não achou). Fica para a sessão semanal.
- Fóssil da galeria no `git add` do robô corrigido (a rodada das 17h não tinha comitado).

### Rotina: fóssil `mapas-e-graficos.html` no `git add` do robô (07/09/2026)
- A rodada de 17h coletou os 313 municípios do InfoDengue e não comitou: o passo de commit ainda
  listava `mapas-e-graficos.html` (hoje `defesa-civil.html`) e o `git add` abortava. Corrigido.

### Leitura contínua de saúde nos planos (§10.1, 07/09/2026)
- `preservar_evidencias.py --ler`: texto por página dos PDFs de planos (pypdf, pdfplumber de reserva),
  `evidencias/<sha256>.txt` + hash, cópia do binário só até 5 MB; 401/403 → "acesso recusado" (LAI).
  Os oito PDFs sem cópia desde 03/09 entram primeiro. Na rotina (40 por rodada).
- `classificar_saude_no_plano.py` (6 autotestes): degraus 1/2/3/5 por regra com página citada, 4
  nunca automático; saída "leitura automática" + fila R7 (`saude_no_plano_revisar.json`).
- Portão (n) ampliado: confirmada só com `revisado_por` e data; degrau 4 só confirmado; motor não lê.

### Desfechos em saúde, saúde no defeso e `saude_no_plano` (07/09/2026; instruções §8–§10)
- **§8 — terceira coluna, "o que aconteceu":** `coletar_desfechos_saude.py` (5 autotestes) lê o
  InfoDengue `alertcity` 2019–2026 para os 313 municípios do painel amostral e calcula o canal
  endêmico (mediana/p75/p90 das mesmas SE de 2019–2025, 2024 à parte), vaza as últimas 4 SE e guarda o
  nowcasting como faixa; grava `data/saude_desfechos/*`. Saúde ganha a seção 3 com barras semanais
  sobre o canal, escada do acumulado 2026 × 2025 × 2024 e mapa de nível por município. Ressalva "o
  Monitor não atribui casos ao El Niño" em toda superfície; portão (d) em `verificar_saude.py`;
  peso zero. Metodologia §35. A primeira coleta real roda na rotina (a rede deste ambiente bloqueia).
- **§9 — saúde na medida do defeso:** detector ganha o padrão "defeso" (título/URL) e o campo
  `setor` por fonte; registradas à mão o Painel das Arboviroses do MS em edição "(DEFESO)" e o painel
  da SES-MG indisponível; Calendário mostra as contagens por setor e a linha do painel federal; §24.
- **§10 — `saude_no_plano`:** `data/saude_no_plano.json` com as duas leituras (Afonso Cláudio/ES = 2
  resposta; Recife/PE = 3 vigilância pós-desastre), padrão observado e pendências (SC, GO, MT, SE,
  Manaus); portão (n). A exibição no cartão e no cruzamento entra com as leituras estaduais.

### Navegação, Financiamento primeiro-com-o-El-Niño, gráficos vazios e a pergunta do defeso (07/09/2026, pedido da editoria)
- **Três quebras de página que o jsdom não pegava** (Financiamento: `tblConsultas` órfão após a
  migração para Pesquisadores; Pesquisadores: constante usada antes de declarar, `MonitorMapas` e
  `CAMADA_ROTULO` ausentes) — eram a causa dos gráficos "zerados" no Financiamento. Corrigidas; o
  portão móvel (Chromium real) agora falha em qualquer banner "Erro ao carregar os dados"; e um
  portão novo em `verificar_estrutura.js` bloqueia JS que escreve em id inexistente sem guarda.
- **Navegação:** "Sinais" vira **"Risco climático"** (título da página também); **Saúde antes de
  Defesa civil**; o Calendário sai da barra (segue publicado e alcançável por links).
- **Financiamento:** seção 1 passa a ser **"O dinheiro do El Niño: como e onde está chegando"** —
  barras de prazo das MPs, rota por órgão com a parcela paga, e dois cartões novos: mapa e barras do
  **valor pago por UF da unidade gestora** (96% nas sedes nacionais; PA, MT, RO e GO à frente).
- **Gráficos vazios populados pelo que existe:** prognóstico trimestral SON/2026 (leitura humana do
  Boletim nº 3 do Painel: chuva abaixo da normal no Norte, Nordeste e centro-norte, acima no Sul;
  calor em quase todo o País) e a probabilidade de El Niño (> 90% para SON, CPC/NOAA via CPTEC; 100%
  de permanência até início de 2027, Boletim nº 3) exibidos como leitura declarada até o plume ser
  coletado — sonda de endpoints do IRI/CPC adicionada ao diagnóstico. O que segue vazio e por quê:
  R$/hab. por rota (rotas 1–4, 6, 7 sem coleta por UF — TransfereGov fundo a fundo e especiais são
  os próximos coletores); Calendário bloco 4 (só a partir de 26/10).
- **§24:** registrada a pergunta-guia da editoria — "o período eleitoral prejudicou a resposta do
  Brasil?" — e a lista do que fica guardado para respondê-la (dispositivos, fontes suspensas com datas,
  log com o flag do defeso, série de decretos com a faixa, prazos das MPs, registros de reabertura).

### Inicial: o nome do MARÉ vai para o título (07/09/2026, pedido da editoria)
- O título do herói passa a ser "MARÉ · Medida de Antecipação e Resposta ao El Niño 2026/2027";
  "Como o Brasil está se preparando" vira a primeira frase do lide. Os rótulos das duas metades
  ficam curtos: "Antecipação · o índice · média dos 27 estados · corte" e "Resposta · o contador
  · municípios sob decreto · corte".

### Inicial: índice primeiro, contador depois (07/09/2026, pedido da editoria)
- As duas metades deixam de ficar lado a lado: primeiro o índice (medidor, régua do ciclo e a
  descrição do MARÉ), depois o contador, cada um sob um selo ("1 · Antecipação · o índice",
  "2 · Resposta · o contador"). O nome completo — MARÉ · Medida de Antecipação e Resposta ao El
  Niño — aparece no título dos dois, com a metade em destaque. O bloco pós-eleitoral linka o
  Calendário (já existe). Inicial em 797 palavras (teto 800).

### Navegação simples e contador com a anatomia do medidor (07/09/2026, pedido da editoria)
- Os rótulos de grupo saíram da barra de navegação (confundiam mais do que orientavam); ficou
  uma linha simples na ordem do §6, com separadores finos entre os grupos e o botão "Enviar dados"
  no fim. A barra quebra linha em qualquer largura (não estoura a 1024 px nem a 390 px).
- O contador de resposta ganhou exatamente a anatomia do medidor: número grande, denominador
  (/ 5.571), selo (% dos municípios), rótulo à direita, barra com marcas (10 · 25 · 50%) e extremos,
  traço da fração da população na própria barra — em Argila, sem gradiente nem brilho. O medidor
  permanece como está. A miniatura semanal saiu daqui (segue em Defesa civil).

### PR-N9 — Metodologia e versão (06/09/2026)
- Cabeçalho da Metodologia declara a **v3.1 "edição narrativa"** (nenhuma alteração de método);
  **§12.5** registra E13–E23 e C15–C25 e a trava da Errata C25; **§34** traz o inventário narrativo
  (as doze páginas, a pergunta de cada uma, o ato que avança, palavras estáticas antes/depois, os
  três testes). §§ 24, 26, 29, 32 e 33 já escritas nos PRs anteriores.
- Fósseis removidos: "mapas-e-graficos" no README, LEIA-ME e comentários; "8 páginas" → 12.
  Versão nos rodapés das doze páginas, no "como citar" e nos PDFs: MARÉ v3.1. CHANGELOG fechado.
- **Pendências declaradas ao fechar (§17 e não-feitos):** conferência do inciso 166-A (transferência
  especial no defeso; linha "a confirmar"); SICs das 27 secretarias de saúde e envio dos pedidos de LAI
  (só com "sim" da editoria); adaptadores dos 26 DOEs e dos diários consorciados; axe-core (§14.4); oito páginas acima da meta de palavras do §7 (abaixo do teto).

### PR-N8 — Segurança (06/09/2026; §14.4–14.10)
- **CSP sem `'unsafe-inline'` em `script-src`:** todos os scripts inline das doze páginas foram
  extraídos para `assets/js/<página>.js` (um por página, ordem preservada, `defer`); o único handler
  inline (`onclick`) virou listener; `cdnjs` saiu da CSP.
- **Bibliotecas em `assets/vendor/`** (Chart.js 4.5.1, d3 7.9.0, jsPDF 2.5.1, do npm, versões
  fixadas, hash no manifesto) no lugar do CDN — sem dependência externa além do VLibras.
- **VLibras nas doze páginas** (faltava em três). Medida de leitura de 68 caracteres nos
  parágrafos corridos (§14.10).
- **Portão `scripts/verificar_seguranca.js`** (na suíte): nenhum `<script>` inline nem handler
  `on*=`; CSP fechada; nenhum script externo além do VLibras; todo `innerHTML =` em `assets/js/`
  escapa (`esc()` ou o sanitizador global da inicial); Actions fixadas por SHA. Nove pontos de
  `innerHTML` sem escape foram corrigidos (datalists, tabelas, listas de fontes, feed).
- **Proteção da `main` conferida pela API:** ruleset ativo (PR obrigatório, check `portoes`
  obrigatório, sem force-push nem exclusão; bypass só da deploy key do robô) — registrado no
  `PROTOCOLO_ATUALIZACAO.md`. LGPD: regra de retenção das submissões escrita (§14.9).
- **Portão móvel** (`scripts/verificar_movel.js`, na suíte): cada página a 390 px num Chromium real
  (Playwright), sem rolagem horizontal nem erro de JS, com capturas; quatro páginas estouravam a
  largura (dispersão, tabela de contadores, barras de prazo, tabela do log) e foram corrigidas no
  `base.css`. Não feito: axe-core (§14.4).
- Portões em Python e em Node passaram a ler a página com o script embutido (`pagina_completa.py`,
  `scripts/_inline_js.js`), para inspecionar o JS que agora vive fora do HTML.

### PR-N7 — Saúde em duas metades e contadores do financiamento (06/09/2026)
- **Saúde (E17):** seção 0 vira "MARÉ · Saúde — antecipação e resposta": à esquerda o Monitor
  Saúde (mesmas faixas), à direita o contador de emergências sanitárias — **zero em 2026**, exibido
  como dado (ESPIN: nenhuma; decretos estaduais por arboviroses: nenhum; busca de 05/09; coleta do
  DOU pendente). "Para você" sai (fica em Proteja-se, com os mesmos dados). Metodologia §33.
- **Financiamento (E18):** `gerar_contadores_financiamento.py` → `contadores_uf.json`, quatro
  contadores por UF com lacunas declaradas célula a célula (r5 por habitante nos 27; preventivo
  localizado só no RS; período, resposta, razão e represado "sem coleta / não disponível"). Seção 3b
  na página. MPs fundidas aos compromissos federais; painel amostral só com o agregado.

### PR-N6 — Cortes e Pesquisadores completo (06/09/2026)
- **Sai da vista, fica nos dados ou em Pesquisadores:** "As oito fontes" e "o que esta página
  é/não faz" de Sinais (viram uma linha com a declaração de peso zero); "Fontes e consultas" de
  Financiamento; "Como usar o site e os dados" de Imprensa; "Onde acompanhar em tempo real" de
  Proteja-se (duplicava Sinais); a tabela "conta / conta em parte / não conta" de Gestores (vira
  três frases na inicial + link ao Calendário + nota de que nenhum pedido de LAI foi enviado);
  Enviar dados fica com três frases de regra e o formulário.
- **Pesquisadores completo** (§9): metodologia e versões; dados abertos, feeds e selos; log com
  totais, por UF/nível e por canal na última rodada; painel amostral; registros e fontes (da
  inicial) + fontes dos sinais + fontes e consultas do financiamento + como usar o site (de
  Imprensa), com os renderizadores migrados; código e replicação.
- **Imprensa:** release de 502 → 171 palavras, com os dois números lidos ao vivo (média MARÉ e
  faixa; municípios sob decreto e fração da população) e a frase citável; entra "O que mudou esta
  semana", lido do feed nacional (últimos sete dias).
- **Portão de palavras estáticas** (`scripts/verificar_palavras.js`, na suíte): meta do §7 por
  página (avisa) e teto (bloqueia). Hoje: oito páginas acima da meta, nenhuma acima do teto —
  o aperto até a meta segue nos próximos PRs, sem perder informação.

### PR-N5 — Calendário eleitoral (06/09/2026)
- **Bloco 1 conferido inciso a inciso:** nove dispositivos (Lei 9.504, art. 73, V, VI a/b/c, VII,
  § 10; LRF arts. 21 parágrafo único, 42, 65) em `data/calendario/dispositivos.json`, cada um com o
  trecho lido, a fonte (transcrição do MPC/AM para o art. 73; publicação original da Câmara para a
  LRF) e a data. A íntegra no Planalto bloqueia leitura automatizada — registrado; o art. 65 foi
  conferido no caput e no início do inciso I, e a linha diz isso.
- **Bloco 2** (o que não é suspenso) com a base legal por item; **bloco 3** com as duas medidas
  separadas (fontes suspensas × municípios sem diário indexado) lidas dos dados; **bloco 4** vazio de
  propósito até 26/10.
- **Portão anticontrafactual** `scripts/verificar_calendario.js` (na suíte): nenhuma expressão
  "teria/poderia ter/se não fosse" na página nem no JSON; todo dispositivo com trecho e fonte.

### PR-N4 — Página inicial e navegação (06/09/2026)
- **Navegação em grupos** (§6) nas doze páginas: O ciclo (Sinais · Calendário) · Antecipação e
  resposta (Defesa civil · Saúde) · O dinheiro (Financiamento) · Para você (Proteja-se · Gestores ·
  Imprensa · Pesquisadores) · botão "Enviar dados". Ordem canônica nova no portão de estrutura.
- **Duas páginas nascem:** `pesquisadores.html` ("tudo o que prova o resto": metodologia, dados
  abertos, log e cobertura, a seção "Registros e fontes" e a tabela de auditoria que saíram da
  inicial, código e replicação) e `calendario-eleitoral.html` (E20: blocos 1–4 com o buraco à
  vista — a tabela de dispositivos "a confirmar" até a conferência inciso a inciso do PR-N5).
- **Inicial na ordem do §4:** uma frase de abertura; medidor + contador; "Como ler" em três
  frases (o que mede, o que não mede, o teto da afirmação); 27 cartões com **cinco campos na
  face** (antecipação, resposta, nível de verificação da UF, instrumento estadual, capital);
  Encontre sua cidade; Prazos em curso; **A história em cinco números** (anunciado · publicado ·
  decretado · chegou · não sabemos, cada um linkando à sua página, todos calculados dos dados);
  bloco pós-eleitoral visível e vazio. Palavras estáticas: 1.664 → ~700.
- Portões ajustados (páginas novas na suíte; cinco números no lugar dos KPIs; tabela de auditoria
  verificada em Pesquisadores). Vocabulário público: Pesquisadores pode citar arquivos e caminhos.

### PR-N3 — Contador de resposta e página Defesa civil (06/09/2026)
- **A outra metade do MARÉ** (E13): `gerar_resposta.py` produz `data/resposta/{por_uf, serie_semanal,
  municipios, municipios_decretados, quadrantes}.json` a partir de `atos_resposta.json` (245
  eventos) e do S2iD; hoje **231 municípios sob decreto (4,1%) · 2,9% da população · primeiro
  decreto em 06/07/2026**; 220 reconhecidos pela União, 11 decretados sem reconhecimento; RS com
  74 de 497 municípios (15% da população). Fatias de evento observado todas "em classificação" (C16).
- **Superfícies:** contador nacional ao lado do medidor (mesma altura, miniatura semanal com a faixa
  do defeso, frase C18); segunda barra (Argila) nos 27 cartões de estado com o traço da população
  (C15); barra empilhada por tons no cartão expandido; "Decreto no ciclo" no cartão da cidade.
- **`defesa-civil.html`** absorve `mapas-e-graficos.html` (301 no `netlify.toml`; navegação
  "Defesa civil" nas dez páginas): seções 1–2 = antecipação (mapas e leituras, sem "Como o dinheiro
  chega" — C21), seção 3 = resposta com a **dispersão antecipação × resposta** (C20), a série
  semanal e a tabela decretado × reconhecido por UF.
- **Portões:** `verificar_resposta.py` (a–g, com o teste de estresse: apagar `data/resposta/`
  não muda uma nota) e `scripts/verificar_runtime_resposta.js`; Metodologia §32.

### PR-N0b — Diagnóstico do Querido Diário concluído (06/09/2026)
- Resultado conhecido (Cerrito/RS): um território por chamada → 3 diários e 3 excertos; **20 territórios
  em lote → 0, com e sem palavra-chave**. Cobertura real confirmada (Porto Alegre 10.000 edições;
  Curitiba 9.138). Aspas, `OR`, `published_since` e `size` funcionam. Causa única dos 5.331 zeros de
  03/09: a consulta em lote. Registrado na §26; request/response em `robo-registro/leituras/`.

### PR-N0 — Canal de diários, detector de defeso e canal LAI (06/09/2026; instruções complementares, com precedência)
- **Diagnóstico do Querido Diário com resultado conhecido** (`scripts/diagnosticar_querido_diario.py`,
  na Action, request/response integrais em `robo-registro/leituras/`): um território vs lote,
  aspas/OR, `published_since`, `size`, docs da API. Hipótese principal: o varredor em lote
  (`territory_ids` com dezenas de códigos) é a origem dos 8.165 zeros uniformes de 03/09 — o coletor
  de 03/09 (um território por vez) obteve excertos. O varredor em lote fica **suspenso** na rotina.
- **Três decisões distintas** no canal DOM: `sem_cobertura_qd` / `coberto_sem_mencao` / `com_excerto`
  (+ `registro`, `erro`), com teste de cobertura por território em cache (`data/cobertura_qd.json`) e
  espelho `cobertura_qd`/`data_teste_cobertura` em `verificacao_municipal.json`. Rótulo público no
  cartão da cidade: "diário não indexado — verificação por outro canal pendente". Teste de estresse:
  100 municípios com resposta vazia → 100 `coberto_sem_mencao`, zero "nada localizado".
- **Detector de página de defeso** em `coletores_base.buscar()`: padrões normalizados (período
  eleitoral, conduta vedada, Lei 9.504, indisponível + contexto eleitoral…), só em sítios públicos
  (não em APIs); registro em `data/calendario/fontes_suspensas.json` (primeira/última detecção, hash,
  amostra) e propagação automática de `fonte_suspensa_defeso` ao log. Autoteste com fixture no
  espírito da página da SUDEC/BA (a captura real substitui a fixture ao ser arquivada); na suíte do PR.
- **Portões §1.6** em `verificar_consistencia.py`: log DOM só com as decisões do §1.2 a partir da
  primeira rodada após a mudança; `municipal_completo` sem cobertura e sem bateria completa bloqueado;
  execução de sítio público sem `fonte_suspensa_defeso` booleano bloqueada.
- **Metodologia:** §24 ganha a correção conceitual (diário oficial não é publicidade; o defeso esconde
  a divulgação e o documento); §26 a nota de cobertura real; §29 o pré-registro do canal LAI, escrito
  antes de qualquer envio. `data/lai_pedidos.json` não existe e não existirá (decisão de 03/09): a lista
  de destinatários das Defesas Civis foi gravada só em `robo-registro/notas/lai/destinatarios.json`.
- **Não feito, por exigir a editoria:** envio dos pedidos (mensagem a mensagem, com "sim" explícito);
  SICs das 27 secretarias de saúde (a localizar um a um com URL); adaptadores dos 26 DOEs e dos
  diários consorciados (§1.3–1.4) — trabalho de dias, iniciado após o diagnóstico.

### PR-N2 — Tokens e portões de design (06/09/2026)
- **Escala tipográfica** de dez degraus em `tokens.css` (12 · 12,5 · 13,5 · 15 · 17 · 19 · 23 ·
  28 · 38 · 52 px); 48 tamanhos fora da escala ajustados para o degrau mais próximo nas dez
  páginas e no `base.css`. O medidor do MARÉ (18/44 px) fica como está (E14) e é a única exceção.
- **Hex proibido fora de `tokens.css` e `mapas.js`:** 296 cores em hex nas páginas viraram
  `var(--nome)` (CSS e estilo inline) ou `MonitorMapas.cor('nome')` (valores concretos para o
  canvas); paleta nomeada da marca nos tokens e no `COR` do `mapas.js`.
- **Dois breakpoints** (640 e 1020 px): 420/760/880 normalizados; grids já eram auto-fit/minmax.
- **Portões** em `verificar_estrutura.js`: font-size fora da escala, hex solto e breakpoint fora
  de 640/1020 bloqueiam a publicação (negativos provados). Pendente do §14.3: teste a 390 px com
  captura de tela exige navegador (Playwright), que este ambiente não tem — registrado.

### PR-N1 — Andaime e errata (06/09/2026)
- **Errata C25 (Metodologia §10.3 e §24):** a regra C6 (nenhuma alteração de nota no defeso)
  foi declarada em 02/09 e excepcionada em 04/09 pela v3.0, por decisão editorial escrita e
  motivada; desde 05/09 vale sem exceção até 25/10. A frase da página inicial foi reescrita
  para dizer isso. **Portão de congelamento:** hash das constantes do motor (escada, créditos,
  ESTADOS, ESTRUTURA, peso) em `data/congelamento_defeso.json`; `verificar_consistencia.py`
  falha se mudarem dentro do intervalo (negativo provado).
- **Datas de edição só via `meta.json`:** os literais "25/08/2026", "26/08/2026" e "27/08/2026"
  (última verificação, corte do medidor, corte da régua, rodapé) viram placeholders preenchidos
  pelo JavaScript a partir de `meta.corte`/`meta.atualizado_em`; a régua do ciclo calcula o fim
  pelo corte real. **Portão de datas literais** de edição no HTML (negativo provado).
- Andaime removido: ponteiro "na página de mapas e gráficos" (reescrito para Sinais e
  Financiamento); campo "Sinal do ato" no cartão da cidade (C24; a doutrina fica); KPIs deixam
  de apontar para a galeria. O bloco "O que o período eleitoral escondeu" passa a ficar
  **visível e vazio de propósito**, com a linha que explica o vazio e o link para o Calendário.

## v3.0 — 04/09/2026 · Componente estadual em dois sub-elementos

- **Regra (Metodologia §30):** componente estadual = média (1/2, 1/2) de *estrutura de
  coordenação* e *instrumento operacional*, cada um na escada 100/65/45/35/0. Estrutura julgada
  pela função do ato (plano que institui níveis de mobilização conta como estrutura nova);
  estrutura permanente sem ato do ciclo = 0. Pesos iguais por sensibilidade (30/70–50/50 sem
  troca de faixa) e pelo padrão da casa.
- **Município:** oitava categoria `estrutura` (comitê/gabinete nomeado para o ciclo ou COMPDEC
  ativada por ato), crédito 0,45; COMPDEC genérica não conta.
- **Reclassificação uniforme das 27 UFs** (tabela na metodologia): AL parcial→insuficiente,
  AP insuficiente→crítico; SC e MT mantidos pela regra da função (SC: níveis do plano; MT: Sala
  de Situação Central do Decreto 2.015/2026, IOMAT). Média 45,9 → 43,6.
- **Bateria v3:** AL e AC passam a *em elaboração* no instrumento operacional (plano nomeado,
  não publicado). RR e BA ficam como pistas (atos ainda não localizados no DOE).
- `data/estados.json`: campos `estrutura` e `instrumentos`; `indice.json`: `estrutura_status`,
  `estado_estrutura`, `operacional_status`, `estado_operacional`.
- Site: cartão do estado mostra os dois sub-elementos e a média; legendas e seletor com a
  categoria `estrutura`; rodapés em v3.0.

## [2.3] — em publicação (sessão de construção de 02/09/2026; corte de dados 31/08/2026; média nacional 47,1 inalterada)

**Designação (decisão editorial de 02/09/2026):** o redesenho da verificação — níveis,
defeso, fontes nacionais e estaduais, página de saúde — recebe o número **v2.3**. O
motor de cálculo é idêntico ao da v2.2.3 (nenhum peso, crédito, componente ou régua
mudou; regra C6 do defeso). A reserva antes atribuída à v2.3 (fator de alinhamento
com κ, população real na camada declarada, anexo MARÉ×ICM) passa a **v2.4**
(METODOLOGIA §12.4.4 e §13). Nos registros abaixo, "v2.2.4" nomeia o documento de
redesenho de 02/09/2026 que orientou a construção. **Primeira atualização (dia 0 da
semana intensiva): domingo, 06/09/2026, às 6h de Brasília.**

### Carimbo de cache nos assets (05/09/2026)
- `/assets/*` fica 24 h no cache do navegador (netlify.toml); a página, revalidada, seguia
  apontando para o mesmo nome de arquivo — e o leitor via o tema velho mesmo atualizando.
  `scripts/carimbar_assets.py` reescreve cada `assets/x.css|js|svg` com `?v=<8 hex do sha256
  do conteúdo>` (determinístico; 55 referências em 10 páginas), na cadeia de derivados antes do
  manifesto. Portão de estrutura aceita o carimbo.


### Tema técnico, 2ª passada: superfícies frias e caixinhas dos estados (05/09/2026)
- As superfícies secundárias saem do osso-claro (terra) para mineral-claríssimo (#F0F4F3) e as
  linhas de Areia para mineral-claro (#C5CFCE); Areia fica reservada aos trilhos das barras de
  prazo. Links em Sintético-escuro; versaletes (selo/kicker) em Sintético; Bioluz declarado como
  acento positivo. "Sem dado" nos mapas em cinza frio. Gradiente de identidade das dez páginas
  vira fio Musgo de 2px; títulos Fraunces em peso 400.
- Cartões dos estados na página inicial recuperam a caixa: fundo branco, borda mineral-claro,
  hover em Sintético (haviam ficado sem borda sobre o fundo branco).
- Medidor do MARÉ e barras dos cartões (o indicador) preservados.


### Tema técnico sobre fundo branco (05/09/2026, decisão editorial)
- `assets/tokens.css` reescrito: base branca e osso-claro (#F4F1EA) para trilhos e faixas;
  tinta Vazio; verde Musgo como cor de ação (links, botões, "novo"); terracota Argila/Âmbar
  como calor de dado; Sintético e Mineral como frios; Areia como linha; cantos de 6px;
  números tabulares. Sem gradiente, sem brilho — a linha de identidade vira um fio Musgo.
  **O medidor do MARÉ permanece como estava** (bloco `.gauge` preservado).
- Logotipo "FUTURA" (positivo, para fundo branco) no masthead e no rodapé das 10 páginas, no
  lugar da assinatura em SVG inline (`assets/futura-positivo.svg`, sem o manifesto c2pa).
- Paleta compartilhada dos mapas (`assets/mapas.js`) e todas as cores inline das páginas
  remapeadas para a marca: novo = Musgo, readequado = Sintético, vigente = Mineral, em
  elaboração = Âmbar, não localizado = Argila, não verificado = cinza quente; faixas
  inicial/construção/consolidado/avançado = Argila/Âmbar/Sintético/Musgo; risco seca = Âmbar,
  chuvas = Sintético, multi = Musgo. Contraste AA verificado pelo portão de acessibilidade.


### Bateria estadual de saúde — bloco 4 (05/09/2026): 17 de 27 verificadas
- PA → VIG (plano em execução contínua, notícia oficial da SESPA, 02/2025; documento a
  localizar); PB → VIG (PDF oficial de 15/02/2024). Federal: Plano de Contingência Nacional
  para Dengue, Chikungunya e Zika (MS, 2025) como cartão.
- Emergências sanitárias de 2026: busca manual não localizou ESPIN nem decreto estadual por
  arboviroses em 2026 (achados são de 2024 e 2025); contexto de queda de 73% da dengue
  (MS, 22/07). Logado; coleta automática do DOU segue pendente.
- Pendentes de busca individual: AC, RR, AP, TO, RO, AL, RN, PI, MA (e o estadual de MT).


### Bateria estadual de saúde — bloco 3 (05/09/2026): 15 de 27 verificadas; dois "novos"
- **GO → NOVO (100):** Plano de Emergências em Saúde Pública de Goiás para o El Niño 2026-2027,
  Nota Informativa nº 1/2026 – SES/SUVISA/SUVEPI/GESP/V-21845 (27/08/2026), listada no portal
  oficial da SES-GO. **AM → NOVO (100):** Plano de Contingência para Emergências em Saúde Pública
  Relacionadas a Eventos Climáticos Sazonais de Seca e Estiagem (SES-AM/FVS-RCP, 08/06/2026, cinco
  estágios operacionais). São os dois primeiros estados "avançados" no Monitor Saúde.
- RJ → ELAB (plano em atualização, ata da SES-RJ de 12/2025; última edição publicada 2018/2019);
  ES → VIG (plano sem data no portal oficial). MT com pista (CIRs aprovam planos municipais
  2025/2026; estadual não localizado).
- Federal: cartão do alerta do MS a estados e municípios (22/07/2026) adicionado.
- Pendentes: PA, TO, RO, AC, RR, AP, AL, PB, RN, PI, MA (e o estadual de MT).


### Monitor Saúde v0.1 no topo da página de Saúde (05/09/2026, decisão editorial — Metodologia §31)
- Medida separada do MARÉ, mesma gramática, peso zero no índice. Prontidão sanitária por UF
  verificada = média (1/2, 1/2) de instrumento operacional (escada da §9) e antecipação (régua
  ancorada na janela crítica out/2026–mar/2027 declarada pelo MS em 26/08/2026: edição 2026/2027
  antes de 01/10 = 100; 2025/2026 = 45; anterior = 20; nenhuma = 0). UF não verificada não recebe
  número. Sem número nacional enquanto houver UF não verificada.
- Hoje: 11 UFs verificadas, todas em "em construção" (planos sazonais 2025/2026 = 45; DF e PR,
  com edições antigas, 32,5). 16 UFs em cinza. GO, se o plano El Niño 2026-2027 for localizado
  em fonte oficial, iria a 100 ("avançado") — o primeiro do país.
- `gerar_monitor_saude.py` (7 autotestes) na cadeia de derivados e na rotina; mapa + barras +
  tabela alternativa no topo de `saude.html`; portão `verificar_saude.py` (m) com teste negativo;
  runtime da página confere 27 UFs, legenda e barras.


### Bateria estadual de saúde — bloco 2 (05/09/2026)
- Mais quatro UFs com plano localizado em fonte oficial (VIG): CE (2025/2026, 01/07/2025),
  PE (2025/2026, 22/01/2025), PR (2024/2025; página oficial de dengue suspensa pelo defeso —
  nota factual), DF (edição de 12/2023 — a mais recente localizada). Total: 11 de 27.
- **Achado de outra natureza — GO:** a SES-GO apresentou em 27/08/2026 um Plano de
  Emergências em Saúde Pública para o El Niño 2026-2027 (calor, fumaça, arboviroses) e a Nota
  Informativa nº 1/2026 às prefeituras. Candidato a **NOVO** (instrumento do ciclo), registrado
  como pista até o documento oficial. RN também como pista (COE-dengue antecipado, imprensa).
- **Federal:** o Plano de Preparação e Resposta a Emergências em Saúde Pública associadas ao
  El Niño 2026-2027 foi apresentado ao Conass em 26/08/2026 (notícia oficial do MS) — cartão
  federal passa de "anunciado" a **localizado**, com os cinco eixos e a janela crítica declarada.
- Pendentes de busca individual: PB, RN, PI, MA, AL, RJ, ES, MT, TO, PA, AM, AC, RO, RR, AP.


### Bateria estadual de saúde — bloco 1 (05/09/2026)
- Sete UFs com plano estadual de contingência de arboviroses localizado em fonte oficial e
  registrado como **vigente-recorrente** (plano sazonal anual, sem citação ao ciclo El Niño):
  BA (atualização 2025-2026, 05/2025), SP (2025/2026, 15/01/2025), MS (2025-2026, 08/10/2025),
  MG (PEC-ARBO, Resolução SES/MG nº 10.440, 17/09/2025 — ato com número e data), SC (2025/2026,
  08/09/2025), RS (2024-2025 v2 publicado; edição 2025/2026 apresentada em 10/2025, PDF não
  listado) e SE (sem data de edição). Buscas logadas (canal `orgao_estadual`); sete UFs do
  Nordeste logadas como pendentes de busca individual.


### Saúde: série semanal de dengue 2024–2026 pelo InfoDengue (05/09/2026)
- O Painel de Arboviroses do MS é Tableau sem API; a série passa a vir do InfoDengue
  (Fiocruz/FGV), que já coletamos para as capitais: o coletor pede a janela 2024–2026 de
  cada capital e soma as 27 por semana epidemiológica. Rótulo e crédito dizem "soma das 27
  capitais — não é o total nacional". Autoteste da soma. O gráfico desenha 2026 em Argila,
  2025 em Âmbar, 2024 em Mineral; padrão de gráficos da casa aplicado.


### Execução das ações das MPs, pelos arquivos mensais abertos (05/09/2026)
- Quatro sondas da API do Portal mostraram: `por-orgao` devolve o orçamento inteiro do
  órgão (não a MP); `plano-orcamentario` é catálogo sem valores; `movimentacao-liquida`
  está vazio para 2026. O caminho certo é o arquivo mensal aberto "Execução da Despesa"
  (sem chave), que traz órgão, ação, unidade gestora (com a UF no nome) e os valores.
- Ações confirmadas no arquivo de 08/2026: Ibama 214M e 214N; ICMBio 214P; Conab 2130;
  MDS 2792 e 2798. `coletar_execucao_mps.py` soma empenhado/liquidado/pago desde o mês
  de cada MP e o pago por UF (destino), gravando em `mps_2026.json`; 6 autotestes.
- **Limite declarado na própria legenda:** o arquivo não separa a fonte do dinheiro — o
  que se mostra é a execução das ações reforçadas pela MP (inclui a dotação ordinária),
  um teto, nunca "a execução do crédito".


### Rota do dinheiro das MPs no topo da página de finanças (05/09/2026)
- Nova seção 0, antes de todo o conteúdo: barras de prazo das MPs 1.367 (R$ 337,5 mi,
  incêndios; Ibama 194,4 mi + ICMBio 143,1 mi) e 1.384 (R$ 925 mi, alimentos; Conab 849 mi
  em estoques + MDS ~76 mi em cestas), e o fluxo MP → órgão executor → uso declarado, com
  larguras proporcionais ao valor. Dotações das notas oficiais (Agência Gov, Câmara, Conab)
  e do Congresso; `data/financiamento/mps_2026.json`.
- Execução (empenhado/liquidado/pago) e destino (brigadas por estado, estoques por armazém,
  cestas por município) declarados como "sem coleta até o corte"; a parcela paga aparece
  dentro do bloco do órgão quando coletada. Sonda da API de despesas (que aceita a chave)
  preparada para preencher isso.
- Só título, legenda e crédito de uma linha (portão de figuras ✓).


### ADPF 743 no cartão dos dez estados intimados (05/09/2026)
- Campo `adpf743` em `estados.json` para AC, AM, AP, MA, MT, MS, PA, RO, RR, TO: intimação
  (25/05/2026, nota oficial do STF), decisão de 26/06/2026 — MT e PA homologados (nota oficial
  do STF; CNN/Correio), AC/AM/AP/MA/MS com 30 dias para corrigir orçamento, equipes e metas
  (imprensa), RO/RR/TO listados na trilha do CAR (Correio). Resultado após 25/07 não localizado;
  íntegra da decisão a arquivar. Proveniência declarada no registro; **nenhum efeito na nota**.
- Cartão do estado ganha a linha "ADPF 743 (STF)" com o selo do status e as datas.


### "Prazos em curso" vira barras que esvaziam (05/09/2026, pedido da editoria)
- A caixa deixa de ser lista de texto e passa a mostrar, para cada marco datado, uma
  barra que esvazia da data-base ao vencimento: trilho em Areia, tempo restante em Âmbar,
  abaixo de 30% em Argila (urgente), transcorrido em Mineral apagado. Título em Fraunces
  leve, metadados em Archivo Narrow, datas nas pontas. Acessível (`progressbar` com
  percentual restante). Sem parágrafo explicativo: título, barras e crédito de uma linha.
- O vigia de prazos passa a emitir `data_base` (início do prazo) em `prazos_uf.json`;
  marco sem data-base não vira barra. Portão de runtime ajustado (conta barras, confere
  largura 0–100% e marcação de vencido).


### Página inicial: dois painéis removidos (04/09/2026, pedido da editoria)
- Saíram os painéis "Proteja-se" (chamada para a página de proteção) e "Ajude a completar o
  mapa" (chamada para o formulário). As páginas continuam no menu; só a chamada na inicial saiu.


### TransfereGov: primeira coleta real e duas correções (04/09/2026)
- Série semanal 2026 da rota r5 preenchida: R$ 6,7 bi assinados com municípios em 28
  semanas; pico de R$ 573 mi na última semana de junho, véspera do defeso (04/07). A carga
  da fonte é de 17/07, então o gráfico cobre só o início do defeso — a data vai no crédito.
- Correções após ler o resultado: os CSVs são **UTF-8** (lidos como latin-1 na 1ª rodada);
  e a fila El Niño excluía mal — "Rancho Queimado" e "Mato Queimado" entravam por "queimad"
  no NOME do município; agora o nome é removido do objeto antes das palavras-chave
  (autoteste negativo). Fila a ser regerada na próxima rodada.


### Transferências sem chave: coletor do TransfereGov (04/09/2026)
- A chave do Portal da Transparência autentica, mas os endpoints de transferências
  respondem 403 (exigem emissão via gov.br Prata/Ouro). Caminho escolhido pela editoria:
  **TransfereGov — Dados Abertos**, sem chave. Sondado com rede real: repositório de CSVs
  do módulo Discricionárias e Legais (`repositorio.dados.gov.br/seges/detru`, 59 arquivos;
  carga de 17/07/2026) e API PostgREST pública (fundo a fundo, especiais, TED).
- `coletar_transferegov.py`: cruza `siconv_proposta` (município, IBGE, objeto) com
  `siconv_convenio` (assinatura, valores) e produz a **série semanal 2026 da rota r5**
  (voluntárias a municípios, por data de assinatura), `r5.valor_2026` por UF, a fila de
  revisão humana `transferegov_el_nino_revisar.json` (instrumentos cujo objeto cita o
  ciclo — nada publicado como "recurso do El Niño" sem leitura) e a proveniência em
  `financiamento/consultas.json` (URL, hash, bytes). Programas fundo a fundo 2026 que
  citam defesa civil em `financiamento/programas_faf_2026.json`.
- 7 autotestes (parsers e agregações, com negativo). Sem rede: lacuna declarada, nada muda.
  As demais rotas seguem em 0 com status declarado até coleta própria.


### Figuras só com título, legenda e crédito (04/09/2026, decisão editorial definitiva)
- Mapas e gráficos passam a trazer apenas título, legenda e um crédito de uma linha
  ("Fonte: … · data" ou "· sem coleta até o corte"). Saíram todas as notas, dicas,
  parágrafos de "como ler", "por que está vazio" e explicações de uso, estáticos ou
  escritos pelo JavaScript, nas cinco páginas com figuras (43 cartões limpos).
- Dados que moravam em notas viraram itens de legenda (totais do mapa de repasses,
  "nenhum alerta vigente" do CEMADEN, listas de UF por quadrante). Alternativas em tabela
  ou em texto (acessibilidade) ficam como `<details>` fechado, com resumo neutro ("Ver em tabela").
- **Novo portão `scripts/verificar_figuras.js`** na suíte do PR: renderiza as cinco páginas e
  bloqueia qualquer `<p>`, `.note`, `.hint` ou `<details>` sem tabela dentro de cartão de
  figura, mais de um crédito por cartão, crédito com mais de 160 caracteres ou com
  linguagem de explicação. Os portões antigos que exigiam "1 parágrafo por cartão"
  foram invertidos para "zero".


### Sinais de risco: seis das oito fontes coletando (04/09/2026)
- Primeira coleta real com os endpoints novos: **INPE** trouxe 3.500+ focos em 23 UFs
  (AM 1.553, PA 871, MT 249); **Monitor de Secas (ANA)** coletado (mapas até 31/07/2026);
  **CEMADEN** respondeu com `totalFeatures=0` — camada correta, **nenhum alerta vigente**
  no momento da consulta.
- A página passa a distinguir as duas coisas: quando a fonte responde e a resposta é
  "nenhum alerta", o texto diz exatamente isso, em vez de "não localizamos coleta"
  (que significaria falha nossa, e não ausência de alerta declarada pela fonte).
- Seguem em lacuna declarada: IRI (probabilidades ENSO) e CPTEC (prognóstico trimestral,
  que sempre foi de leitura humana).


### Endpoints reais das fontes de sinais de risco (04/09/2026)
- Três das cinco fontes que nunca coletaram estavam apontando para endereços que
  não existem mais. Descobertos por diagnóstico com rede real (cinco rodadas):
  - **INPE (focos):** `dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/diario/Brasil/`,
    arquivos `focos_diario_br_AAAAMMDD.csv`; o coletor escolhe o mais recente do índice.
  - **CEMADEN (alertas):** GeoServer `gsc.cemaden.gov.br/geoserver/cemaden_dev`, camada
    `alertas_vigentes_siaden` via WFS/GeoJSON (o JSON antigo responde 404).
  - **Monitor de Secas (ANA):** API `apimsbr.ana.gov.br/rpc/v1/<recurso>` (o catálogo
    antigo responde 404); arquivos no bucket `ana-monitor-secas-files`.
- Parsers novos com 6 autotestes (3 negativos). O IRI (probabilidades ENSO) segue
  sem endpoint localizado — lacuna declarada, como antes.


### Cartório estadual: passada nas 23 UFs restantes (03/09/2026)
- Todas as 27 UFs revisitadas hoje (4 na passada anterior + 23 agora), com três
  buscas dirigidas logadas por UF (camada 3 — não substitui a bateria negativa
  completa do §4.1.3).
- **Mudança material localizada — RR:** em 02/09/2026 o governo criou o
  **Gabinete Integrado da Operação El Niño 2026-2027** (19 órgãos, Casa Civil +
  Defesa Civil), junto com decreto de situação de emergência por estiagem
  (180 dias). O gabinete é ato ex-ante nomeado e é **candidato a elevar RR de VIG
  para NOVO**; o decreto de SE é resposta (0 pontos). Registrado como pista até a
  citação completa no DOE-RR — nenhuma nota mudou.
- Pistas menores: SP (plano de contingência para estiagem apresentado ao Conselho
  Estadual de Mudanças Climáticas em 24/07, sem número/data) e PI (declaração do
  secretário de que já existe plano, sem documento). VIG mantido nos dois.
- Demais 20 UFs: nenhum instrumento novo ou revisão publicada localizada; status
  mantido.


### Cartório estadual (passada de 03/09) e alertas de saúde no Proteja-se
- Passada dirigida nos quatro estados mais sensíveis do cartório: PB (LAC mantido —
  único achado é plano fiscal da Seplag, fora do objeto), RN (LAC mantido — imprensa
  registra articulação sem documento nomeado; decreto de SE por seca = resposta),
  BA (ELAB confirmado — comitê para o Plano Estadual El Niño 2026/2027; ato de
  criação a localizar no DOE-BA), PE (ELAB mantido; achado para a camada de
  financiamento: Lei nº 19.240/2026 institui o FUNDPRA e Decreto nº 60.732/2026 o
  regulamenta — registrado como pista, status `nao_verificado` mantido até leitura
  da íntegra). Descoberta municipal por imprensa: PLANCON 2026 de Pindamonhangaba/SP
  (Decreto nº 7.087, 16/06/2026) — pista, a confirmar em fonte oficial. Cinco buscas
  logadas (executor `claude`).
- Proteja-se: novo bloco "Alertas de saúde do momento" — espelho da página de Saúde
  (dengue nas capitais em nível 2+, avisos de calor do INMET, emergências sanitárias),
  lendo os MESMOS arquivos e regras, com lacuna declarada em qualquer falha de carga.


### Limpeza da superfície pública (03/09/2026, pedido da editoria)
- Removido o painel "Contador público da verificação" da página inicial
  (os números continuam nos dados abertos, `verificacao_resumo.json`); o
  contador de varredura segue na cortina do domínio.
- Removidas todas as menções a pedidos de acesso à informação (LAI) da parte
  visível: cartão da cidade, página de Saúde. O registro de LAI vive no
  repositório privado.
- Removidos comentários internos visíveis (datas de decisão, números de
  seção, versões, nomes de scripts) das páginas inicial, Saúde e Financiamento;
  os links para a metodologia permanecem, sem numeração de seção.
- Mapa 1b (nível de verificação): a linha de contagens que vazava para a tela
  (a classe `sr-only` não existia nessa página) foi removida; o crédito de
  fonte passa para DEPOIS do mapa, fora do parágrafo inicial.
- Portão de runtime ajustado (dois testes do painel removido).


### Duas regras novas do teste do objeto para pistas municipais (03/09/2026, decisão editorial)
- **Autoridade:** só ato do Executivo institui plano para o componente pontuado.
  Conselho de saúde aprovando plano de desastres → camada observada de saúde
  (Quissamã/RJ); câmara/colegiado sem decreto → "executivo pendente".
- **Família de risco:** plano cujo risco está fora das três famílias do ciclo
  (frio/baixas temperaturas/geada; epidemia/arboviroses/gripe) fica visível como
  "fora do objeto", nunca pontua, nunca é apagado (Itapevi/SP).
- Regra declarada na METODOLOGIA §5.2.1 antes de beneficiar qualquer ente;
  codificada em `classificar_pista_civil.py` (campos `autoridade`, `objeto`,
  `destino`), com 14 autotestes incluindo os dois casos reais; reaplicada às 41
  pistas de hoje (6 candidatas ao componente pontuado, 2 camada saúde, 2 fora do
  objeto, 1 executivo pendente, 30 para leitura humana).


### Triagem das pistas de plano de contingência (03/09/2026, autorização escrita)
- `classificar_pista_civil.py`: heurística que classifica cada pista da
  varredura (origem `querido_diario`) em `candidato_forte`,
  `falso_positivo_provavel` ou `indefinido` — só para ORDENAR a fila de
  revisão humana, nunca para decidir sozinha nem promover a registro.
  Calibrada contra as 41 pistas reais da 1ª varredura integral: 14 fortes,
  13 prováveis falsos positivos, 14 indefinidos (ficam na dúvida, por
  desenho — regra "na dúvida, não classifica").
- Conectada em `coletar_diarios_municipais.py`: toda pista nova já sai com
  o campo `triagem`. As 41 pistas de hoje foram reclassificadas
  retroativamente.
- Sinal forte: ato que institui/aprova o plano ("fica instituído",
  "institui o PLACOM/PLANCON", decreto que aprova, câmara que aprova).
  Sinal fraco: cláusula padrão sem relação com defesa civil (TI/backup,
  termo de referência, matriz de risco genérica de licitação, transporte
  escolar, síndrome gripal, sandbox regulatório).


### Encerrar a varredura hoje, sob pedido (03/09/2026, autorização escrita)
- Novo botão manual no Actions ("finalizar_varredura_hoje"): consulta TODOS os
  municípios ainda pendentes numa rodada só, em vez do ritmo por dias restantes.
  `coletar_diarios_municipais.py --tudo`; a pausa de cortesia entre consultas
  continua valendo. Não altera `INTENSIVO_DE`/`INTENSIVO_ATE` nem a cadência
  normal das próximas rodadas — é um botão de uma vez só, não uma mudança de regra.


### Contador que se move em primeiro lugar (03/09/2026, decisão editorial)
- Pedido da editoria: "não faz sentido um contador que não se move na frente".
  No painel "Contador público da verificação" (site completo), a linha da
  varredura dos diários municipais — a que sobe a cada rodada, 2×/dia — passou
  a vir PRIMEIRO, em destaque (negrito), com percentual junto ao número.
- A linha de níveis de verificação (nacional/estadual/completo), que fica
  parada até a bateria completa pós-defeso, ganhou uma frase explicando por
  que ela não se move agora — não foi escondida, só contextualizada.


### Correção: contador da cortina nunca disparava (03/09/2026)
- Bug na 1ª versão: `HOUVE_ALTERACAO` era calculado checando `git diff --cached`
  DEPOIS do commit já feito — o staged vira commit, o diff some, a variável
  sempre dava "0". A etapa "Atualizar contador da cortina pública" saía
  sempre `skipped`, mesmo com commit real (confirmado na execução das 15h06:
  commit `2d10fa7` na main, contador não publicado). Corrigido: uma única
  decisão if/else antes do commit, sem checar o diff de novo depois.
  Número de hoje (2.278/5.571) publicado manualmente enquanto o conserto
  não entrava, para não deixar a cortina desatualizada.


### Contador real na cortina pública (03/09/2026, autorização escrita)
- O robô publica, a cada rodada que gerar mudança, um contador operacional
  (`progresso.json`) no ramo `publico` — quantos municípios já foram
  consultados na varredura dos diários oficiais, sobre 5.571. A cortina
  "Em atualização" no domínio passa a mostrar esse número em vez da barra
  puramente decorativa; se o arquivo não carregar, volta ao modo indeterminado.
  Nunca dado do índice, nunca afirmação sobre existência de plano. Script:
  `scripts/atualizar_contador_cortina.py`; publica só quando os números mudam.


### Correção: rebase do robô falhava por arquivo sujo fora do escopo (03/09/2026)
- A 1ª execução real com o rebase (introduzido mais cedo hoje) falhou: `docs/pip-audit-resultado.json`
  fica modificado a cada rodada mas fora da lista de arquivos do commit automático; isso deixava o
  checkout raso do runner (depth=1) com alteração não commitada, e o `git rebase` recusava com
  "cannot rebase: you have unstaged changes". Corrigido descartando essas modificações (`git checkout --
  .`) antes do rebase, e aprofundando o fetch (depth=50) para o merge-base ter história suficiente.
  Reproduzido e confirmado localmente antes e depois do fix.

### Janela da varredura integral encurtada de 10/09 para 06/09 (03/09/2026, autorização escrita)
- Com duas rodadas por dia, cada lote se recalcula sozinho (pendentes ÷ dias de calendário
  restantes) — projeção com os números reais desta tarde (688 consultados na 1ª rodada de
  hoje) mostra convergência completa até a manhã de 06/09, com a rodada da tarde de 06/09
  como folga/reforço. `INTENSIVO_ATE` alterado de `2026-09-10` para `2026-09-06` (variável
  do repositório, GitHub Actions). `INTENSIVO_DE` inalterado (2026-09-03).

### Robô: duas rodadas diárias durante a semana intensiva (03/09/2026, autorização escrita)
- Segundo gatilho de cron às 18h Brasília, além do já existente às 06h — só durante
  03–10/09/2026, para acelerar a varredura integral dos 5.571 municípios. Cadência normal
  (segunda-feira) e fora da janela intensiva não muda: rodadas extras encerram sem coletar.

### Reconhecimentos federais: pasta nova do MIDR (03/09/2026, autorização escrita)
- A pasta `/noticias/RSS` (que o rodapé do sítio do MIDR ainda aponta) passou a exigir login;
  a 1ª rodada real leu uma página de login e registrou "0 notícias". Agora o coletor lê o RSS
  de `/noticias-midr` e, se a resposta não for XML, a **listagem HTML** da pasta (2 páginas);
  resposta sem estrutura vira lacuna declarada ("endpoint a verificar"), nunca "0 notícias".

### Varredura integral dos diários municipais até 10/09 (03/09/2026, autorização escrita da editoria)
- Semana intensiva passa de "lote rotativo com teto de 7 × 150" para **varredura integral**:
  cada rodada diária consulta, no Querido Diário, os próximos municípios ainda não
  consultados na janela (`INTENSIVO_DE`..`INTENSIVO_ATE`), com tamanho recalculado a cada
  dia para cobrir os 5.571 até a data-fim (mínimo `TAMANHO_LOTE`, teto 1.500/rodada).
  Pausa de 0,25 s entre consultas e nova tentativa em HTTP 429. Consulta não é verificação (§4.1.2).
- Contador público ganha a linha "Varredura dos diários oficiais municipais" (consultados de 5.571,
  com/sem menção, datas), com portão de runtime que exige o número do arquivo e proíbe
  afirmação de existência/inexistência de plano.
- `coletar_saude.py`: tentativa sem rede **não rebaixa** uma coleta válida do InfoDengue
  (03/09: a rodada das 08h36 falhou por rede e apagara o status "coletado" das 6h);
  a página de Saúde diz "nova consulta em dd/mm falhou; dados da última coleta válida".
  Correção do autoteste, que semeava por cima dos dados reais (agora restaura byte a byte).
- `coletar_financiamento.py`: erro do Portal da Transparência loga o **código HTTP**
  (401/403 chave · 429 limite · 5xx Portal); em 429 espera 60 s; em 401/403 interrompe a rodada.

### Endpoint certo dos reconhecimentos federais + prévia com senha (03/09/2026)
- **DOU/S2iD, corrigido pela fonte oficial:** o MIDR publica cada lote de reconhecimentos
  como notícia com os links diretos das portarias no DOU (número e data no endereço) e
  mantém RSS. O coletor passa a ir do RSS às notícias e das notícias às páginas das
  portarias (municípios nomeados), com casamento IBGE tolerante a acento/apóstrofo —
  provado por fixture da notícia real de 25/05/2026 (18 de 18 municípios). A consulta
  textual do DOU vira complementar e nunca confere nível. S2iD, MUNIC e ICM seguem
  "a verificar".
- **Prévia com senha (decisão da editoria):** Basic-Auth do Netlify em todas as rotas dos
  deploys do `main`, gerado no deploy a partir de segredo (nunca no repositório público);
  mais um véu no navegador (`assets/acesso.js`, hash SHA-256, ativo só em *.netlify.app).
  Limite declarado: o Basic-Auth exige plano Pro; o véu não é segurança. A cortina do
  domínio não muda.

### Primeira atualização real (03/09/2026, 11h06 UTC) — e a correção que ela exigiu
- **Rodou de ponta a ponta e comitou** (dia 0 antecipado para 03/09; semana intensiva até
  10/09): 3 fontes de sinais coletadas (Painel El Niño, INMET, NOAA/ONI), InfoDengue nas
  27 capitais, 47 evidências preservadas, 149 diários municipais consultados, pistas e
  atos novos; 16 portões verdes; publicado no endereço reservado.
- **Erro grave pego na leitura do relatório:** a busca no DOU voltou **0 itens** porque a
  página veio sem a estrutura de resultados — e o coletor marcou os 5.571 municípios como
  "verificados em fontes nacionais". Leitura vazia não é verificação. Corrigido: só conta
  como consulta nacional se a estrutura de resultados estiver presente (senão, lacuna
  declarada, "parser/endpoint a verificar"); a marcação indevida foi revertida (5.571 → 0;
  os 149 consultados no Querido Diário voltam a "ainda não verificado", como manda a regra:
  diário municipal não eleva nível). O feed que recebera 5.571 eventos de uma vez passa a
  agregar por estado e nível; os 5.571 eventos foram removidos do histórico.
- **Evidências preservadas mas não comitadas:** a rotina gravou 47 cópias em `evidencias/`
  na máquina do robô, mas o passo de commit não incluía a pasta — o índice apontava
  para arquivos inexistentes (o portão 6 acusou "integridade violada"). Corrigido: o
  commit inclui `evidencias/` e o manifesto; as 42 cópias perdidas ficam marcadas "a
  re-preservar" e o preservador as rebaixa na próxima rodada (com comparação de hash);
  o portão 6 só aceita evidência com cópia ou snapshot.
- **Dump bruto da API do Portal (8,9 MB)** sai do repositório público (regenerado a cada
  rodada; fora do manifesto). O CSV de transferências a revisar continua.

### Preparação para o lançamento oficial (03/09/2026, a pedido da editoria)
- **Ordem narrativa das páginas:** O monitor → Sinais de risco → Mapas → Financiamento →
  Saúde → Proteja-se → Gestores → Enviar dados → Imprensa (risco anunciado → o que foi
  publicado → o detalhe → o dinheiro → o setor → o cidadão → o gestor → contribuir →
  imprensa). Portão 1 atualizado.
- **Muitos acessos simultâneos:** o site é estático na CDN do Netlify (escala por padrão;
  brotli automático). Cabeçalhos de cache por caminho (HTML sempre revalidado; dados JSON
  5 min com revalidação em segundo plano; folhas/módulo 1 dia; selos, feeds, dados
  abertos e PDFs 10–60 min). Os três JSON mais pesados foram compactados sem mudar
  conteúdo (referência IBGE 597→467 KB; malha 289→120 KB). Peso medido da página
  inicial: ≈300 KB comprimidos. Limites do plano gratuito a acompanhar no lançamento:
  100 GB/mês de tráfego (≈330 mil visitas à inicial) e **100 envios/mês no formulário**
  (Netlify Forms) — acima disso o formulário para de aceitar sem aviso.
- **Release reescrito** com a componente narrativa da editoria: a nota baixa é evidência
  de preparação não tornada pública — o Monitor busca nos canais que a lei define como o
  lugar da preparação (Lei 12.608/2012; LAI), e o que não está lá não cumpriu o rito nem
  pode ser conferido ou cobrado. Mantido o teto: sobre a existência do plano, "não
  localizamos até o corte". A mesma componente entrou em "Como ler o MARÉ" (inicial),
  no cartão "Como ler uma nota" e na FAQ da página de imprensa.
- **Rede do dinheiro em três níveis:** sim, há conexão financeira União → estado nas
  mesmas rotas — FPE (CF art. 159, I, a), fundo a fundo aos fundos estaduais (SUS/SUAS/
  FUNDEB), defesa civil (Lei 12.340/2010, art. 1º: estados e municípios), emergência
  setorial, convênios e transferências especiais (art. 166-A). O diagrama ganhou o ramo
  União → Estado por rota, o estado alimenta a rota estadual e repassa cotas ao
  município; cada rota traz a base legal do nível estadual no tooltip.

### Navegação em uma linha — segunda correção (03/09/2026)
- A editoria ainda via duas linhas: o `index.html` mantinha cópia própria das regras da
  navegação e do masthead (vencia a folha base) e a barra dividia a linha com o logotipo.
  Removidas todas as regras de núcleo duplicadas do index (a isenção do portão 1 para o
  index acabou); a navegação ganha a linha inteira abaixo do logotipo no desktop; rótulos
  encurtados sem perda de sentido — "Mapas", "Enviar dados", "Gestores" — para caber
  com folga mesmo em fonte substituta (≈840px com Archivo Narrow; ≈970px com fonte
  larga; 1.140 disponíveis). Confirmado em captura.

### Verificação geral antes da primeira atualização (03/09/2026, a pedido da editoria)
- **Navegação em uma linha no desktop:** fonte condensada 12,5px, espaçamento .05em,
  pastilhas mais estreitas, sem quebra acima de 1020px (≈1.050px de 1.140 disponíveis);
  abaixo disso volta a quebrar.
- **Padrão único de gráficos** (`MonitorMapas.padraoGraficos`): tipografia, cores, grade e
  tooltip iguais em todos os Chart.js; o portão 1 proíbe `Chart.defaults` local e exige a
  chamada em toda página com gráfico. Gráfico 1 (rosca) virou **barras horizontais**
  (contagem compara-se por comprimento; soma 27 explícita) e o rótulo "Sem plano" virou
  "Nenhum localizado" (teto da afirmação).
- **Cartão 1b** com nota curta como os demais (as contagens ficam no contador público e
  no tooltip; crédito de figura mantido).
- **Portão 17 `verificar_robustez_atualizacao.py`** (CI): cópia perturbada em 6 famílias —
  9 planos municipais novos, 155 municípios com nível de verificação maior (log v2), 3
  reconhecimentos federais, 2 UFs com instrumento de saúde, série de financiamento em 8
  rotas, avisos INMET — derivados regenerados e **todos os runtimes verdes** (média 45,9 →
  46,0 na cópia). Primeira rodada pegou uma fragilidade real do padrão de gráficos
  (defaults sem `elements`), corrigida. A tentativa de mudar status estadual à mão foi
  bloqueada pelo portão de consistência — como deve ser: o canal legítimo é a revisão.
- **Acessibilidade:** ids duplicados e links internos/âncoras quebrados passam a ser
  bloqueantes.

### Linha narrativa pública, página para jornalistas e LAI fora do site (03/09/2026, a pedido da editoria)
- **Registro de pedidos de LAI nunca no site:** seção e tabela removidas de Para
  gestores; registro e os 55 textos saíram do repositório público para o privado
  (`robo-registro/notas/lai/`); o site diz apenas, sem contagens, que a verificação de
  um estado depende de resposta a pedido de acesso à informação (lista de UFs em
  `data/ufs_dependentes_de_lai.json`, alimentada pelo levantamento).
- **Portão 16 `verificar_vocabulario_publico.js`:** lê o texto visível renderizado das
  10 páginas e bloqueia jargão interno (nomes de arquivo/script, caminhos de dados,
  códigos de decisão E/C, "portão", "robô", números de PR, códigos de auditoria,
  "documento de redesenho", "sessão", marcadores TODO, "pedidos de acesso à informação
  enviados"). Primeira passada: 18 ocorrências em 5 páginas, todas reescritas na
  linha pública (fonte por nome, não por arquivo; regras sem código).
- **`imprensa.html` — Para jornalistas** (10ª página, no menu e no rodapé de todas):
  release com números lidos ao vivo, o que o índice mede e não mede, régua e teto da
  afirmação, como citar (texto, referência, licença CC BY 4.0, imagens), como usar
  (consulta, dados abertos, feeds, selos, metodologia, cadência), FAQ na linha do site
  e contato imprensa@monitorelnino.com.br. Padrão de design da folha base.
- Suíte: **16 portões**.

### Achados do ensaio da rotina (03/09/2026)
- **O ensaio funcionou como instrumento:** a rotina rodou de ponta a ponta com rede
  real (3 de 8 fontes de sinais coletadas; 18 evidências preservadas; coletores
  gravaram dados) e falhou no portão certo — o derivado de verificação estava
  obsoleto porque **o índice nunca era recomputado dentro da rotina**. Agora
  `recalcular_mare.py --write` (relógio no corte) roda depois de TODOS os coletores e
  antes dos portões; as fichas do painel vêm depois dele.
- **Coletores legados** (Querido Diário, recursos, vigência, decretos) rodavam no
  workflow DEPOIS dos portões: passaram para dentro do orquestrador, antes dos
  derivados. O PDF do passo final usa o relógio do corte.
- **Portão 12 dentro da rotina:** modo `--idempotencia` (a árvore está suja com dados
  novos): uma segunda regeneração não pode mudar nada. O modo `git` continua no CI.

### Correções da revisão da editoria (03/09/2026)
- **Medidor do herói dessincronizado (causa raiz):** a barra e o contador animado liam
  `data-alvo="47.1"` gravado no HTML — a rotina só regravava o número, não o alvo, e
  a animação sobrescrevia o 45,9 com 47,1. Agora o alvo vem do índice na carga; o motor
  regrava o fallback estático em `--write` e o `--check` bloqueia se ele divergir; o
  runtime testa barra = número = média.
- **Motor único de mapas (`assets/mapas.js`)**: projeção, coroplético por UF, siglas das
  27 UFs em todo mapa, camadas de pontos (inclusive densas), legenda canônica
  (discreta e contínua), tooltip e crédito de figura — usados por index, mapas,
  sinais, saúde e financiamento. Portão 1 exige o módulo em página com mapa e proíbe
  helpers e legendas locais; os quatro runtimes de mapa verificam siglas em todos os
  mapas e o formato canônico de todas as legendas (o mapa 1b e a escala do mapa
  "natureza" foram os primeiros pegos).
- **Financiamento, bloco 1: rede em vez de cartões** (decisão de design delegada):
  origem → rota → município, traço por chave (contínuo regra · tracejado decreto ·
  pontilhado discricionária · duplo direta), realce ao passar o mouse, base legal no
  tooltip; os cartões continuam em texto dobrável. Legenda da série pelo módulo.
- **Cadência declarada nas superfícies:** Saúde diz que não é tempo real (diária na
  semana intensiva, semanal depois) e mostra o estado de cada fonte; o mapa de atos
  de resposta mostra o último evento e a rotina de coleta (DOU/S2iD e diários).
- **Erro meu, corrigido em minutos:** o passo de relatório do `atualizar.yml` ficou com
  duas chaves `env` — o pyyaml aceita, o GitHub recusa o arquivo inteiro (o ensaio
  acusou 422). Corrigido; nasce `scripts/validar_workflows.py` (detecta chave
  duplicada), chamado pelo portão 1 e pela checagem de PR, com teste negativo.
- **Ensaio da rotina:** `atualizar.yml` ganha o botão "ensaio" (roda tudo como dia
  da semana intensiva, sem comitar nem publicar) e grava o relatório completo da
  execução no repositório privado em toda rodada — a execução manual de 02/09
  falhou sem deixar diagnóstico legível; isso não se repete.

### §3.8-bis — hash dos documentos-fonte reconferido toda rodada (E8) — 02/09/2026, noite
- `preservar_evidencias.py --reconferir`: a rotina rebaixa cada documento citado com hash
  preservado e compara; hash diferente vira entrada no log, marca em `evidencias.json` e
  **evento no feed** (`documento_alterado`) — a categoria só muda por julgamento humano.
  A Action `ler_documento` do repositório privado continua sendo a leitura integral sob
  demanda; a preservação e a reconferência semanal rodam no orquestrador.

### PR-D2 — "Por onde o dinheiro chega" (financiamento.html; E9, E10, E12; §7.8) — 02/09/2026, noite
- **Página completa, oito blocos:** as sete rotas + estadual (ordem e cores fixas, chave de
  acesso, base legal, o que o decreto destranca; absorve "rotas sem decretar" e "o caminho
  do recurso de resposta"); série semanal 2026 por rota com a **faixa do defeso sempre
  desenhada** (lacuna declarada até a primeira coleta); fundo a fundo estadual preventivo
  por UF (RS localizado — Prepara RS como precedente, E12) e coroplético R$/hab. com
  seletor de rota (aguardando coleta); resposta por decreto (mapa migrado: repasses do
  Prepara RS e reconhecimentos federais; tabela por UF); painel amostral; programas
  permanentes (Carro-Pipa: lista não pública, declarado); compromissos federais com
  execução a coletar e o gráfico por área migrado; fontes e consultas reproduzíveis.
- **`coletar_financiamento.py`**: semeia `data/financiamento/` (rotas, por_uf — convergência
  de financiamento_uf/recursos_uf/transferencias com fonte por campo —, compromissos, série,
  emendas, consultas); adaptador Portal da Transparência (60 req/min; chave só no robô);
  **autor de emenda descartado na coleta** (E10, provado por fixture); Tesouro/FNS/FNAS/
  Transferegov/MDS `a_verificar` (§15). 6 autotestes ✓.
- **Portões 13 e 14:** `verificar_financiamento.py` (sem chave, créditos, reconciliação,
  nada imputado, resposta separada, **teste de estresse: pasta inteira apagada → índice
  bit a bit igual**, faixa do defeso, E10; 7 negativos acusados) e
  `verificar_runtime_financiamento.js` (20 verificações).
- **Migrações (E9):** mapa 7, gráfico 3 e "Como o dinheiro chega" saem de
  mapas-e-graficos.html (fica cartão de link); a linha de financiamento do cartão da UF
  vira link; o bloco de rotas de Para gestores vira link. METODOLOGIA §28 com o modelo.

### PR-D3 — Painel amostral estratificado (E11; §10-bis) — 02/09/2026, noite
- **Lista arquivada com hash:** Anexo I da NT 1/2023 (1.942 municípios geo-hidrológicos)
  extraído pela máquina da leitura registrada no repositório privado (Action
  `ler_documento`, E8); Anexo II (preliminar) arquivado à parte, fora dos estratos.
  Demais marcadores declarados indisponíveis até serem arquivados.
- **`gerar_painel.py --sortear --semente 20260902`**: 313 municípios (12 por UF; **DF = 1,
  exceção declarada** — o documento previa 324), sem capitais, porte proporcional, mínimo
  2 no marcador dominante e 1 controle, Ponte Serrada/SC incluído; lista imutável
  (hash publicado na METODOLOGIA §28-bis e nos dados abertos); fichas com fonte e data;
  agregados região × porte × risco. Reverificação semanal no orquestrador.
- **Portão 15 `verificar_painel.py`** (5 negativos acusados); bloco 5 da página de
  financiamento renderiza o painel; `dados-abertos/painel_amostral.csv`.
- Suíte: **15 portões**.

### Governança (decisões delegadas à sessão em 02/09/2026, à noite — fecha AUD-06, AUD-11, AUD-15, AUD-21, AUD-22)
- **Proteção da `main` (AUD-06):** ruleset no GitHub — nenhum push direto humano,
  mudanças só por pull request, **checagem obrigatória** "Portões (pull request)"
  (workflow novo `portoes.yml`: os 12 portões + autotestes em árvore limpa a cada
  PR), sem apagar nem forçar; **exceção única para o robô**, via deploy key. `publico` protegido contra apagamento e force-push.
- **Commits do robô (AUD-21) — parcial:** `scripts/comitar_via_api.py` (commit
  assinado pela API) está pronto, mas em repositório de **usuário** o GitHub não
  aceita a Action como exceção do ruleset; o robô publica por **deploy key** (push
  SSH, segredo `ROBO_DEPLOY_KEY`), sem "Verified". Para ter proteção **e** assinatura,
  converter a conta `monitorelnino` em organização (decisão da editoria).
  `persist-credentials: false` no checkout (AUD-11); Actions pinadas por SHA.
- **Licença dos dados (AUD-15):** **CC BY 4.0** para dados, dados abertos, feeds,
  selos e METODOLOGIA; código segue MIT. LICENSE, `datapackage.json`, CITATION.cff e
  guia de dados abertos alinhados.
- **Proteção provada (02/09/2026, noite):** antes do ruleset existir, um push de teste
  meu entrou na `main` (arquivo `_teste.txt`, removido neste PR) — exatamente o risco
  que o AUD-06 apontava. Depois do ruleset: push humano direto **recusado** (GH013);
  push do robô por deploy key **aceito** (commit vazio de teste `2ede830`, mantido no
  histórico como prova).
- **Tag e release (AUD-22):** `v2.3` anotada no commit desta edição, com release no
  GitHub. DOI: fica para quando a editoria vincular o repositório ao Zenodo (exige
  conta institucional); registrado como pendência.

### Resposta à auditoria técnica externa (Manus AI, commit `3f049a6`, 02/09/2026)
Auditoria anônima com 25 achados (1 crítico, 7 altos, 12 médios, 5 baixos). Estado de
cada um após este commit:
- **AUD-01 (crítico) — domínio serve a cortina "Em atualização":** intencional e agora
  declarado no protocolo (§2 e §7): o lançamento é decisão da editoria. Corrigido o
  *soft 404*: fora da raiz a cortina responde **404 real** e cabeçalhos de segurança
  (ramo `publico`).
- **AUD-02 (alta) — XSS persistente pelo campo `numero_data`:** validação estrita por
  esquema e tamanho no processador; **escape de todo texto dos dados na carga do
  index** (antes de qualquer `innerHTML`) e URLs só `https://`; **teste negativo**
  executado (marcação injetada rende como texto, `javascript:` descartado).
  **Autoaplicação de contribuições SUSPENSA** (`AUTOAPLICAR = False`) até os testes
  negativos rodarem no CI. CSP, HSTS e Permissions-Policy no `netlify.toml` (AUD-12),
  com a limitação declarada de `'unsafe-inline'` para os scripts inline do site.
- **AUD-03 (alta) — SSRF/envenenamento por validação de host contornável:**
  `host_oficial()` com `urlsplit`, só `https`, sem credenciais, allowlist exata de
  diários municipais, resolução DNS com rejeição de IP privado/loopback/link-local/
  reservado (IPv4/IPv6), revalidação de cada redirecionamento, limite de 8 MB e MIME
  aceito. Os cinco payloads da auditoria são rejeitados (provado).
- **AUD-04 (alta) — derivados obsoletos com portões verdes:** **portão 12**
  `scripts/verificar_derivados.sh` regenera a cadeia canônica em árvore limpa com o
  relógio no corte e exige `git diff --exit-code` (teste negativo com PDF obsoleto
  comitado: bloqueia). Suíte: 12 portões.
- **AUD-05 (alta) — documentação contraditória:** estado do lançamento, número de
  páginas (9) e de portões (12) alinhados no protocolo; inventários antigos ficam
  para revisão documental completa (pendente).
- **AUD-06 (alta) — ramos desprotegidos:** pendente de decisão da editoria (proteger
  `main` exige exceção para o robô que comita dados; proposta: ruleset com bypass
  para a Action e revisão obrigatória para humanos).
- **AUD-07 (alta) — auditor UX não portátil:** substituído pelo portão 11
  (`verificar_acessibilidade.js`, portátil e bloqueante) e pelas regiões roláveis
  focáveis (AUD-13: `tabindex`, `role`, rótulo); a saída do VLibras sem `alt` é do
  widget de terceiro — decisão documental pendente.
- **AUD-08 (alta) — 0/97 evidências, 145/149 citações na fila:** já declarado e
  cronometrado (portão 6 bloqueante a partir de 10/09; fila até 25/10); a Action
  `ler_documento` do repositório privado passa a preservar as evidências (integração
  pendente, §3.8-bis).
- **AUD-09 — manifesto omite 124 arquivos:** manifesto ampliado (dados abertos,
  feeds, selos, CSS, LAI, CITATION: **259 arquivos**) e exclusões declaradas.
- **AUD-10 — `datapackage.json` inválido:** `created` em ISO 8601 (corte mantido em
  campo próprio).
- **AUD-11/AUD-18 — suprimentos:** `pypdf` fixado em `requirements.txt`; workflow com
  `npm ci` e Node 22; `engines.node >=22.14`. Pinar Actions por SHA e isolar o push:
  pendentes.
- **AUD-14 — dois 404 no ES:** URLs oficiais atuais de Afonso Cláudio e São Mateus.
- **AUD-17 — auditor de PDFs com 14 falsos positivos:** conhece `nao_verificado`.
- **AUD-20 — governança aberta:** `SECURITY.md` e `CONTRIBUTING.md` criados.
- **AUD-15 (licença dos dados), AUD-21 (assinatura de commits), AUD-22 (tag/release/
  DOI), AUD-19 (CEMADEN em http), AUD-23, AUD-25:** pendentes, os três primeiros por
  decisão da editoria.
- Correção de dado apontada pela auditoria: uma entrada do log (pista de PE) tinha
  `nivel="estadual"` indevido e elevava Cabo de Santo Agostinho; corrigida para `null`.

### Alinhamento ao documento ampliado (E8–E12) e correção C10 (02/09/2026, à noite)
- **Correção de dado C10 (aplicada no defeso por ser correção, não método):** os 12
  registros pontuáveis apoiados apenas em imprensa (canal `imprensa`) foram
  rebaixados a pista (`nao_verificado`), com citação preservada em
  `data/pistas_imprensa.json` e errata em `data/erratas_v224.json`. **Efeito:**
  AC −14,6 · AP −9,1 · PA −2,4 · SP −2,2 · MG −1,7 · SC −1,3; **média nacional
  47,1 → 45,9.** Script auditável e idempotente `aplicar_c10_imprensa.py`. PDFs,
  dados abertos, medidor e METODOLOGIA (§5.5, §24) atualizados; 19 eventos no feed.
- **Nove páginas (C4 atualizada por E9):** `financiamento.html` nasce como
  placeholder no padrão, "Financiamento" entre Saúde e Proteja-se; portões 1 e
  11 cobrem nove páginas.
- **E10 (neutralidade permanente):** portão no `verificar_consistencia.py` que
  bloqueia qualquer campo de autor de emenda em `data/` (teste negativo
  acusado); regra registrada no §24.
- **C12:** cartão do estado diz quando o instrumento foi publicado dentro do
  período eleitoral (ato oficial, não publicidade).
- **Feeds (§7.2):** tipos novos `verificacao_ampliada`, `decreto_reconhecido`,
  `instrumento_saude`; texto correto para o rebaixamento C10.
- **Rodapé de fontes** ampliado com as fontes incorporadas na v2.3.
- **Rótulos:** a permanência da nota do defeso passa de "E8" a **E13** (E8 é,
  no documento ampliado, "nenhum download manual — Action `ler_documento`").
- Pendentes, na ordem do documento: PR-D2 (financiamento completo, §7.8),
  PR-D3 (painel amostral, §10-bis), integração da Action `ler_documento` ao
  portão de evidências (§3.8-bis).

### Harmonização de design, acessibilidade e responsividade (02/09/2026, a pedido da editoria)
- **`assets/base.css`**: folha base única com os componentes compartilhados das 8
  páginas (tipografia, masthead e navegação, painéis, cartões de mapa/gráfico,
  legendas, tooltip, tabelas, botões, rodapé), foco visível, alvo de toque
  ≥40px no celular, skip-link, pontos de quebra canônicos (1020/880/640/420),
  reduced-motion e impressão. As 7 páginas secundárias perderam 30–66 regras
  duplicadas cada; ficam só os estilos próprios. O index importa a base e mantém
  o herói.
- **Causa do "fora do padrão" das páginas novas:** mapas, sinais e saúde
  herdaram a classe do masthead compacto sem a regra (título gigante). A regra
  agora vive na base e vale para todas as secundárias. Contorno dos mapas e
  legendas unificados.
- **Portão 1 ampliado**: exige `base.css` e proíbe página redefinir o núcleo
  (teste negativo acusado). **Portão 11 novo `verificar_acessibilidade.js`**:
  idioma, viewport, skip-link, um h1, ordem de títulos, alt, rótulos de
  formulário (dois defeitos reais corrigidos no index), SVG rotulados,
  aria-current, sem tabindex positivo, tabelas com cabeçalho, rel=noopener,
  contraste AA calculado dos pares de tokens (todos passam), pontos de quebra
  e foco visível na base. Suíte: 11 portões.
- Limite declarado: a captura de tela desta sessão não executa grid CSS; a
  conferência visual em celular e tablet é da editoria na prévia.
### Nota de dependência de LAI (02/09/2026, decisão editorial)
- O contador público, o cartão da cidade e a página de Saúde dizem, com números,
  quando a informação atualizada depende de resposta a pedido de acesso à
  informação (`verificacao_resumo.json` → `lai`); a UF fica "pendente, não
  presumida" até a resposta. Antes do envio, a editoria verifica o que já é
  público sem LAI e filtra os pedidos ao que faltar.

### PR-F — Pedidos de acesso à informação (02/09/2026; §12, C13)
- **`gerar_lai.py`**: 27 pedidos às defesas civis estaduais (modelo do §12),
  27 às secretarias estaduais de saúde (variante saúde) e 1 ao CMNE/MIDR pela
  relação nominal da Operação Carro-Pipa (C13) — 55 textos em `docs/lai/`,
  registro público `data/lai_pedidos.json` com status `a_enviar` e protocolo
  nulo. O envio é humano (Fala.BR exige pessoa física); `--registrar` grava
  protocolo, data e prazos (20 + 10 dias). A tabela em Para gestores exibe os
  55 com o estado de envio. Autoteste (3 casos) ✓.

### PR-E — Metodologia, protocolo, guia e versão v2.2.4 (02/09/2026)
- **METODOLOGIA.md**: seções novas §24 (defeso: fatos, consequências, regra C6,
  memória E13), §25 (níveis de verificação e "não verificado"), §26 (fontes
  incorporadas e disciplina dos coletores), §27 (saúde, peso zero), §28
  (fundamentação normativa, cláusula de neutralidade; Lei 14.750/2023 fica "a
  verificar antes de citar"), §29 (pré-registro da recontagem pós-defeso) e
  adendo §12.4.4 (candidatos declarados com vigência ≥ 26/10/2026).
  **Fósseis corrigidos** (§11.2 do doc de redesenho): "4 componentes",
  "Dirichlet(1,1,1,1)", "25%", escala 1,0/0,7/0,4, exemplo do AM, ordem
  histórico/vigente em §5.3; também em README e DOCUMENTACAO_TECNICA. Portão
  de fósseis no `verificar_consistencia.py`. Cabeçalho v2.2.4, corte 31/08.
- **Versão v2.2.4** nas superfícies vivas (rodapés das 8 páginas, PDFs,
  motor, CITATION.cff/datapackage, LEIA-ME); menções históricas à v2.2.3
  preservadas. Média nacional inalterada (47,1): nenhuma regra de nota mudou.
- **PROTOCOLO §3.3**: dez portões; pista A diária na semana intensiva.
  **GUIA DO EDITOR §4a**: o que fazer em cada dia da semana intensiva.
- **SBOM**: adendo — módulos novos usam só a biblioteca padrão; nenhuma
  dependência adicionada. PDFs e dados abertos regenerados; manifesto 130.

### PR-D — Página "Saúde e El Niño" (02/09/2026; E2, C1–C3)
- **`saude.html` completa**, no motor de mapas da página de sinais: cartões da
  camada federal (6, com estatuto "localizado" ou "anunciado, não localizado até
  o corte"; um único link, a página oficial do MS sobre dengue, verificada em
  02/09), mapa de status do instrumento estadual de saúde (6 classes), mapa de
  risco sanitário projetado (derivado dos boletins, sem projeção nova), dengue
  nas capitais (InfoDengue com crédito; MS como fonte primária do número), calor
  (reuso INMET), emergências sanitárias (resposta, peso zero), cruzamento
  **defesa civil × saúde** em quadrantes (soma 27 provada), série de dengue como
  lacuna declarada, camada do cidadão com orientações do MS reproduzidas.
- **`coletar_saude.py`**: as 27 UFs nascem **NAO_VERIFICADO** (C1) — a bateria
  estadual é executada e logada na semana intensiva; adaptador InfoDengue com
  parser provado por fixture.
- **`data/saude_uf.json` · `saude_federal.json` · `saude_sinais.json`**; feed
  `feeds/saude.xml`; dados abertos `saude_uf.csv` e `verificacao_municipal.csv`
  (datapackage atualizado).
- **Portão 5 `verificar_saude.py`** (8 provas, 6 testes negativos acusando) e
  **portão 10 `verificar_runtime_saude.js`** (21 verificações, incluindo o gesto
  do tooltip); ambos no orquestrador. A suíte passa a ter 10 portões.
- Feeds: rótulo humano para "ainda não verificado" e resumo correto da
  reclassificação (14 eventos de 02/09/2026 regenerados após correção do texto).

### PR-C — Coletores da Pista A, evidência preservada e cadência intensiva (02/09/2026)
- **`coletores_base.py`**: disciplina comum — nada inventado (lacuna declarada),
  descoberta ≠ registro, log v2 por consulta, preservação de evidência com
  sha256 (`evidencias/`, índice `data/evidencias.json`, Wayback acima de 5 MB) e
  **livro de fontes consultadas** (`data/fontes_consultadas.json`), único insumo
  dos coletores para o nível de verificação — que continua derivado pelo motor.
- **Quatro coletores** com `--autoteste` (fixtures + testes negativos, 17 casos):
  `coletar_s2id.py` (DOU/SEDEC; S2iD `a_verificar`), `coletar_doe.py` (27 DOEs por
  config `fontes_doe.json`, todas `a_verificar` até a Action confirmar; adaptador
  Querido Diário), `coletar_declarado_nacional.py` (MUNIC/ICM `a_verificar`;
  parsers CSV provados) e `coletar_diarios_municipais.py` (Querido Diário por
  lotes; prioridade = proxy declarado; NUNCA eleva a `municipal_completo`).
  Teste de ponta a ponta sem rede: 100% lacunas declaradas, zero travamentos.
- **Camada declarada nacional (C5)**: `recalcular_mare.py --simular-declarado-nacional`
  grava `data/simulacao_declarado_nacional.json` (27 notas antes/depois); provado
  com 60 declarações sintéticas na BA (24,0 → 25,2 só na simulação; índice
  intacto). Hoje idêntico (0 declarações coletadas).
- **Portão 6 `verificar_evidencias.py`**: aviso até 09/09 (97 de 97 registros
  pontuáveis com URL ainda sem evidência), bloqueante a partir de 10/09/2026;
  `preservar_evidencias.py` (idempotente, roda na Action) fecha essa lacuna.
- **Cadência (E4/§13)**: cron diário adicional; `atualizar.py` checa
  `INTENSIVO_ATE` ANTES de qualquer coleta (fora do período e não sendo segunda,
  encerra sem tocar em nada); lote rotativo D1–D7. Variáveis de repositório
  criadas: `INTENSIVO_ATE=2026-09-12` (provisório; ajustar ao dia 0 real),
  `TAMANHO_LOTE=150`.

### PR-B — Verificação por níveis, "não verificado" e regras de prova (02/09/2026)
- **Categoria `nao_verificado`** (crédito 0,0; cor `--neutro`) em motor, portões,
  legenda, seletor e cartões. **Errata pública** (`data/erratas_v224.json`): os
  14 registros `nao_localizado` foram reclassificados `nao_verificado` porque o
  log não contém bateria municipal completa para nenhum deles (regra §2.1);
  efeito nas notas: nenhum (0,0 → 0,0). `pontos_mapa.json` sincronizado.
- **`data/log_buscas.json` migrado ao esquema v2** (15 execuções preservadas;
  campos estruturais null, não imputados; alvo original em `alvo_v1`).
- **`data/verificacao_municipal.json`** (5.571 municípios) e
  **`data/verificacao_resumo.json`** como ARTEFATOS DERIVADOS regravados por
  `recalcular_mare.py --write` e conferidos bit a bit no `--check`.
- **`data/citacao_incompleta.json`**: fila pública com 145 registros pontuáveis
  sem número formal de ato, com data fora do padrão ou sem URL; prazo de
  saneamento 25/10/2026; saída da pontuação em 26/10/2026 por regra declarada
  em 02/09/2026 (C11). Contagem sai de consulta ao dado, não do documento.
- **`index.html`**: contador público da verificação no herói (níveis, fontes
  suspensas pelo defeso, fila de citação); cartão da cidade com TRÊS mensagens
  distintas (não verificado / nada localizado após verificação completa /
  demais), corrigindo a violação do corolário §3.1; frase de escopo sem
  "5.571 municípios cadastrados"; nota do defeso em "Como ler o MARÉ"; bloco
  "O que o período eleitoral escondeu" oculto por data até 26/10/2026 (C14).
- **Formulário**: tipo "plano de contingência de saúde" (nunca automatizável).
- **Dicionário**: grupos `saude`, `programas_permanentes`, `rotas_sem_decreto`
  com origem declarada (§2.4).
- **Portões**: consistência valida log v2, proíbe `nao_localizado` sem bateria
  completa e exige os grupos novos; runtime testa a linguagem ("não localizamos"
  proibido para município não verificado) e a paridade contador↔arquivo; motor
  confere os dois derivados. **Cinco testes negativos executados** — o quarto
  revelou fraqueza real (resumo mentiroso passava) e levou à paridade do resumo
  no `--check` antes de ser aprovado.
- **Decisão editorial E13 (02/09/2026; rotulada E8 até a sessão paralela ocupar esse número):** a nota do defeso é PERMANENTE — após
  25/10 muda de tempo verbal e vira memória do site (index, financiamento, PDF).
- **Mapa "Nível de verificação municipal"** (§7.3): os 5.571 na página de mapas,
  camada padrão em traçado único (5.571 nós individuais atrasavam os demais
  mapas — pego pelo portão de runtime), classe "fonte suspensa (defeso)" (C8),
  crédito de figura embutido no parágrafo único do cartão.
- **Financiamento (C9):** caixa permanente da suspensão legal 04/07–25/10, com
  detalhe dobrável; transferências de emergência do período tratadas como
  resposta. Faixa sombreada entra quando a série de transferências existir.
- **Para gestores (§7.4):** bloco "O que um município pode acessar sem
  decretar" (6 rotas com base legal e cláusula de neutralidade), tabela de
  pedidos de LAI (lê data/lai_pedidos.json, criado vazio) e item de saúde no
  checklist de publicação.
- **PDFs:** documentação do índice regenerada com nota do defeso e contador
  (determinística, SOURCE_DATE_EPOCH = corte); PDF do cidadão com linha de
  nível de verificação.

### PR-A — Sinais de risco + harmonização de design (02/09/2026)
- **Página "Sinais oficiais de risco" incorporada** (PR #3 rebased): peso zero,
  coletor de 3 camadas, `verificar_sinais.py` e runtime próprio. 7 de 8 fontes
  aguardam primeira coleta real pela Action (limitação de rede da sessão,
  declarada no PR #3).
- **`assets/tokens.css`** — fonte única dos tokens de design das 8 páginas;
  blocos `:root` inline removidos de todas. Novo token `--neutro` (#64645C,
  decisão C7) para "ainda não verificado", contraste AA verificado por cálculo
  (4,81:1 sobre `--bg`; 5,29:1 sobre `--surface`).
- **Navegação canônica (decisão C4)** nas 8 páginas: O monitor · Mapas e
  gráficos · Sinais de risco · Saúde · Proteja-se · Enviar documento · Para
  gestores; `obrigado.html` com a nav completa sem item ativo.
- **`saude.html` (placeholder, decisão E2)** — nav e cabeçalho padrão, aviso de
  peso zero; conteúdo entra no PR-D.
- **Portão `verificar_estrutura.js` estendido**: 8 páginas; exige
  `assets/tokens.css`, proíbe `:root` inline, verifica a ordem canônica da nav
  e o item ativo. Três testes negativos executados (nav fora de ordem, `:root`
  inline, link ausente) — todos acusados e restaurados.
- **`publicar_previa.yml` generalizado**: workflow_dispatch em qualquer ramo
  publica prévia no alias do ramo — é a prévia de PR do protocolo, já que o
  site não é ligado ao GitHub.

## [2.2.3] — em publicação (corte de dados 31/08/2026)

### Added (01/09/2026 — página de sinais oficiais de risco)
- **`sinais-de-risco.html`** — sétima página do site: o que CEMADEN/INPE, ANA,
  INMET, CEMADEN e NOAA/IRI publicaram sobre o ciclo 2026/2027, por estado, com
  órgão, documento e data em cada valor. Cinco mapas (tipo de risco projetado,
  seca observada, avisos meteorológicos, focos ativos, alertas vigentes), quatro
  gráficos (série ONI, probabilidades por trimestre, estados por tipo de risco e
  o cruzamento tipo de risco × estágio do arcabouço público), quatro cartões de
  estado do ciclo e a tabela das oito fontes. Origem: pergunta editorial de
  Patricia a partir de um site homônimo que publica previsão de impacto própria.
- **Peso zero estrutural.** Nada da página entra no índice MARÉ. `verificar_sinais.py`
  falha se qualquer chave de sinal aparecer em `recalcular_mare.py` ou em
  `data/indice.json` — o portão que impede a deriva, não a promessa de não derivar.
- **`coletar_sinais_risco.py`** — coletor das três camadas (ciclo · observado ·
  ENOS), com adaptador por fonte, `--semear` (a partir do que já é verificado no
  repositório) e `--autoteste` (22 provas de parser, classificação e guardas, sem
  rede). Falha de rede não interrompe o pipeline: a fonte volta a ser lacuna declarada.
- **Dois portões novos, ambos bloqueantes:** `verificar_sinais.py` (estrutura,
  proveniência de todo valor, peso zero, linguagem, lacuna honesta) e
  `scripts/verificar_runtime_sinais.js` (29 verificações no DOM renderizado,
  incluindo o gesto do usuário no tooltip e o crédito de fonte figura a figura).
  A suíte canônica passa de cinco para **sete** portões.
- **Vocabulário de tipo de risco** (estiagem · chuvas · incêndios · misto · sem
  sinal), lista fechada: classifica *risco de quê*, nunca *quão grave*. Escala de
  severidade continua sendo só a da fonte oficial.
- Documentação: `METODOLOGIA.md` §23 (com a fronteira, as oito fontes e os riscos
  que a própria página cria) e `docs/PROTOCOLO_ATUALIZACAO.md` atualizados para sete
  portões. **Pendência declarada:** o comentário de `.github/workflows/atualizar.yml`
  ainda enumera cinco portões — o token da sessão não tem escopo `workflow`. É só
  comentário: a Action roda `atualizar.py`, que já executa os sete.
- **Revisão de texto e UX (01/09/2026, após revisão editorial).** A página passou a
  seguir a gramática das demais: títulos de figura numerados (`1 · …`), notas que
  descrevem a codificação visual e não a definição do dado, H2 curtos e alinhados aos
  da página irmã ("Mapas geográficos", "Gráficos analíticos"), `details` explicativo
  em cada mapa ainda vazio ("Por que este mapa ainda está vazio", que some sozinho
  quando a fonte entrar) e em como ler o gráfico do cruzamento. CSS próprio da página
  para o estado de lacuna e foco visível por teclado nos mapas; hierarquia de títulos
  sem saltos de nível (H1→H2→H3). Auditoria medida em navegador: sem transbordo
  horizontal, sem texto abaixo de 12px, sem SVG sem rótulo acessível.
- **Estado na publicação:** 1 das 8 fontes coletada (camada do ciclo, já verificada
  no repositório); as outras 7 entram na primeira rodada semanal com rede aberta e,
  até lá, aparecem como lacuna declarada — nenhum valor estimado.

### Added (01/09/2026 — site já publicado; governança de atualização)
- **`docs/PROTOCOLO_ATUALIZACAO.md`** — como uma mudança entra no site em
  produção: duas pistas (A, automática semanal, escopo restrito a dados;
  B, editorial, via ramo + pull request + prévia Netlify + merge pela
  editoria), classes de mudança com portões e regra de versão, rollback,
  emergência, acessos. Clique de merge reservado à editoria.
- **`docs/GUIA_DO_EDITOR.md`** — a mesma rotina em linguagem simples, sem
  comandos: passo a passo do PR, rotina de segunda-feira (aba Actions),
  botão de desfazer no Netlify, o que continua reservado ao julgamento humano.
- **Fase de testes:** ramo órfão `publico` (página em branco + noindex) para
  servir o domínio até o lançamento; `main` publicado como branch deploy
  reservado. Documentado no protocolo §7 e no guia §7.
- **Publicação via GitHub Actions** (01/09/2026, tarde): constatado que o
  site no Netlify não estava ligado ao GitHub (versão no ar era de 27/08).
  Criados `publicar_dominio.yml` (ramo `publico` → produção, página em branco)
  e `publicar_previa.yml` (`main` → endereço reservado). Relatórios do robô no
  repositório privado `robo-registro`. Protocolo §7 e guia §7 reescritos.
- Documentação apenas: nenhum dado, escore ou regra do índice mudou.
  Manifesto regenerado para incluir os dois arquivos.

### Added (as sete sugestões aprovadas por Patricia, implementadas em 31/08/2026)
1. **VLibras** (tradução para Libras, plugin oficial gov.br) nas seis páginas,
   antes de `</body>` conforme o fabricante, com guarda: sem rede, nenhum erro.
   Sem SRI — o gov.br atualiza o arquivo no lugar (exceção documentada).
2. **Caixa "Prazos em curso"** na página inicial, lendo `data/prazos_uf.json`:
   hoje MP 1.367 (12/10), MP 1.384 (11/10) e a ADPF 743 com prazo transcorrido.
   Marcos ganharam `titulo_curto` e `status_curto` curados. Portão: itens
   renderizados = marcos elegíveis.
3. **Pedido de informação pronto (Lei 12.527)** — `textoPedidoAcesso()` monta o
   texto conforme a situação real (cidade sem plano, plano antigo, só decreto,
   coberta pelo estado; estado sem plano), com campos de identificação em
   branco. No cartão da cidade, no detalhe do estado (com botão copiar) e como
   7ª seção do PDF. Portões: presença nos dois lugares, Lei citada, e **nunca
   afirma inexistência**.
4. **Selos SVG embutíveis** (`gerar_selos.py`): 27 UFs + nacional, 360×92,
   fontes de sistema, pares de cor AA idênticos ao site, "preparação
   demonstrável publicamente". Bloco no detalhe do estado com código copiável;
   link direto `#UF`. **Bug meu, achado e corrigido**: o portão selo×índice
   revertia toda mudança legítima do julgamento automático — `recalcular_mare.py
   --write` agora regrava os selos (selo é função pura do índice). E2E provado.
5. **Feeds Atom** (`gerar_feeds.py`): fotografia do banco → diffs → eventos
   append-only em `data/historico_mudancas.json` → `feeds/brasil.xml` + 27 por
   UF. E2E: RN pelo pipeline emite "instrumento estadual" e "MARÉ 10,9 → 74,3".
   Link no `<head>` e no detalhe de cada estado. Portão: 28 feeds bem formados.
6. **Dados abertos citáveis** (`gerar_dados_abertos.py`): 5 CSVs,
   `datapackage.json` (Frictionless), `CITATION.cff`, `docs/DADOS_ABERTOS.md`
   com esquema e roteiro do DOI. Bloco "Dados abertos e feeds" no painel de
   fontes. **Nada inventado**: DOI e URL do repositório ficam como placeholder
   comentado. Portão: linhas dos CSVs = registros dos JSON.
   **Pendente de Patricia**: licença dos dados (recomendação CC BY 4.0).
7. **`para-gestores.html`** — checklist de publicação em 7 itens, tabela do que
   conta/conta em parte/não conta, base legal em 3 parágrafos, "depois de
   publicar". Sexta página do site, na navegação das demais, registrada nos
   portões e na auditoria de UX. Tabela corrigida para o celular (estourava 5px).
- **Pipeline**: os três geradores rodam antes dos portões em `atualizar.py`; o
  commit da Action inclui `selos/`, `feeds/` e `dados-abertos/`. Auditoria axe:
  **0 violações em 18 combinações** (6 páginas × 3 viewports). Auditoria dos
  5.598 PDFs refeita com a 7ª seção: 0 problemas.

### Added (documentos localizados, MP 1.384 promovida, MP 1.383 descoberta, guia de instalação)
- **MP nº 1.384/2026 — localizada em fonte oficial** (página do Congresso
  Nacional): R$ 924.985.960,00 em favor do MDA e do MDS, DOU de 13/08/2026,
  deliberação de 13/08 a 11/10/2026, sem emendas. Os números fecham com a
  nota do MDS (estoques 850 + cestas 65 + PAA 13 = R$ 928 mi): é o
  instrumento legal da parte de alimentos do plano de R$ 1,335 bi.
  Promovida a marco `legal_mp1384_deliberacao_2026` (vence 11/10/2026);
  incluída em "Registros federais" (contador 13 → 14, corretamente: é ato
  federal) e na METODOLOGIA (parágrafo do financiamento).
- **Portaria MDS nº 1.207 — fatos confirmados, link do DOU não**: duas
  fontes secundárias (uma "conferida com a publicação oficial") dão data
  (17/08), publicação (18/08), coordenação (representante do Comitê no
  Gabinete do Ministro; secretaria executiva SNAS), reuniões semanais,
  caráter temporário até o 1º semestre de 2027. O texto no DOU não está
  indexado em busca. Pista marcada `pronta_para_promocao_falta_link_DOU` —
  o vigia de DOU da Action (termo "El Niño") deve localizá-lo.
- **MP nº 1.383/2026 — descoberta no caminho** (Agência Senado e Agência
  Câmara): R$ 360 mi ao MIDR para resposta (socorro, assistência
  humanitária), DOU 13/08; a Câmara informa ser a 10ª MP de desastres de
  2026, somando R$ 3,2 bi. É o dinheiro do "caminho do recurso" (Lei 12.340
  → SEDEC → CPDC). Pista registrada para triagem.
- **Guia de instalação** (`docs/COMO_RODAR_E_PENDENCIAS.md`): tabela dos
  vigias com destino de rede, credencial e comportamento em falha; roteiro
  da primeira execução do vigia da Política Por Inteiro (o que fazer se
  vier pista de manutenção: DevTools → Network → ajustar
  `PADROES_FONTE_DADOS`); cortesia recomendada à Talanoa. A pendência
  "conciliação fina com o catálogo Talanoa" (listada desde sessões
  anteriores — daí Patricia achar que já estava em uso) passou de tarefa a
  mecanismo. README: seção "Atualização automática" reescrita (dizia 8
  etapas; são 21).

### Added (duas pistas promovidas: marco da MP 1.367 e painel da Política Por Inteiro como fonte)
- **MP nº 1.367/2026 → marco legal `legal_mp1367_deliberacao_senado_2026`**
  (decisão de Patricia, 31/08). Status apurado na página oficial do Congresso
  (dados de 27/08): CMO aprovou 07/07; Câmara aprovou 15/07 (MPV 1.367-A);
  Senado "aguardando leitura" desde 17/07; prazo de deliberação retificado
  para 13/08 e **prorrogado por 60 dias (ATCN nº 73/2026): vence em
  12/10/2026**. Cadastrado com data-base 13/08 + 60 dias, sem mexer no cômputo
  do vigia; fontes: DOU 15/06 e página do CN. O marco judicial da ADPF 743
  ganhou o campo `instrumento_cumprimento` apontando para a MP. Vocabulário
  de destinatários do registro ampliado com `UNIAO` (prazo cujo destinatário
  é o Senado não cruza com o banco por UF; recebe data e status). Self-test
  do vigia de prazos verde; `prazos_uf.json` regravado.
- **Painel El Niño 2026/2027 da Política Por Inteiro (Instituto Talanoa) →
  fonte de descoberta** (Patricia: "achei que já estivéssemos fazendo isso" —
  não estávamos; as fontes eram DOU, STF, imprensa regional e repositórios
  estaduais). Novo `monitorar_politica_por_inteiro.py`: o painel carrega os
  atos por JavaScript (a página vem vazia), então o vigia descobre em tempo de
  execução a fonte de dados referenciada (JSON/CSV/planilha/wp-json), lê,
  normaliza por nomes de campo heurísticos, classifica no vocabulário do
  orquestrador (C-estado-amplo/UF · D-municipio-prioritario/Nome/UF ·
  resposta/UF · federal), descarta município já no banco e enfileira em
  `pistas_imprensa.json` / `pistas_sinais.json` com a trava absoluta. Pista com
  link oficial segue o julgamento automático normal; pista cujo link é só o
  painel cai na fila humana. Se não conseguir ler o painel, registra UMA pista
  de manutenção (deduplicada) e não derruba a atualização. Self-test com
  fixture cobre normalização, alvos, dedup, descoberta de fonte, JSON/CSV e a
  garantia de banco intocado (hash antes/depois). Etapa nova no workflow
  (21 etapas), antes do julgamento. METODOLOGIA §4.1.1.1 declara a classe
  "agregador terceiro = pista, nunca registro". Crédito público na seção de
  fontes do índice — como nota, fora da lista de programas federais (o
  primeiro rascunho entrou na lista e teria inflado o contador de 13 para 14;
  o portão de KPI não acusa isso, o olho sim).
- Pendentes, à espera de documento: Portaria MDS nº 1.207 (DOU) e MP nº
  1.384/2026 (texto e valor).

### Fixed (registros federais: da página genérica ao documento; nota oficial do MDS lida)
- Patricia enviou a nota oficial do MDS (29/07/2026, atualizada 31/07) sobre
  o plano de R$ 1,335 bi. Lida na íntegra. O projeto já a tinha como fonte,
  e a METODOLOGIA já trazia a composição (R$ 998 mi + R$ 337 mi da MP nº
  1.367/2026) — mas a lista "Registros federais" do índice tinha três itens
  fracos: **"Sala de Situação Nacional El Niño (Casa Civil + MIDR)"** com
  atribuição sem fonte em lugar nenhum do projeto (a nota oficial diz "reúne
  24 ministérios e instituições", sem nomear coordenador) e link genérico
  `gov.br/mdr`; a MP 1.367 linkando `in.gov.br` genérico; o Painel El Niño
  linkando `gov.br/mdr`. Corrigido com links de documento, todos verificados
  por busca/leitura nesta sessão: nota oficial do MDS; página da MP no
  Congresso Nacional (texto, R$ 337.483.432,00, CMO aprovou 07/07, prazo de
  deliberação 13/08 — status a apurar, prazo legal §15; a MP declara cumprir
  as ADPFs 743 e 760 do STF, vínculo direto com o marco judicial já curado);
  Boletim nº 2 do Painel (INPE, 31/07). Nome corrigido para "Sala de
  Situação do El Niño · 24 ministérios e instituições".
- **Correção de uma suposição minha** registrada mais cedo hoje: eu havia
  anotado que a MP 1.384/2026 (EXM de 11/08) poderia ser o instrumento do
  plano de R$ 1,335 bi. A nota oficial mostra que o crédito do plano é a MP
  1.367 (12/06); a 1.384 é um segundo crédito, posterior, para estoques e
  alimentação emergencial — pista corrigida em `pistas_sinais.json`, com a
  página da MP 1.367 acrescentada como quarta pista.
- **Recomendação federal aproveitada no PDF do cidadão**: a nota diz que o
  planejamento "prevê a atualização dos planos de contingência, com
  identificação de áreas de risco e fortalecimento das estruturas locais de
  resposta" — citada na seção "O que ainda falta — e o que cobrar", com
  fonte, como compromisso público a cobrar do estado e da prefeitura.
  Auditoria completa dos 5.598 PDFs refeita (ok).

### Added (comitê federal, fontes e links — três perguntas de Patricia, três respostas)
- **"Você verificou o comitê de crise federal?"** Não tinha; verifiquei por
  busca web em 31/08. Não há "comitê de crise" com esse nome; há dois atos
  que o projeto não tinha: (1) **Portaria MDS nº 1.207** (17/08, DOU 18/08)
  — Gabinete Extraordinário de proteção social para o El Niño 2026-2027, no
  Comitê Permanente de Calamidades do MDS, reuniões semanais; confirmada em
  duas fontes secundárias (uma "conferida com a publicação oficial"), DOU
  ainda a localizar; (2) **EXM nº 1823/2026 → MP nº 1.384/2026** (11/08),
  crédito extraordinário para o El Niño (estoques, alimentação emergencial),
  em fonte primária (planalto.gov.br) — candidata a instrumento legal do
  "plano federal de R$ 1,335 bi" que o site cita. Mais um agregador terceiro,
  o painel El Niño da Política Por Inteiro/Talanoa, útil como fonte de
  pistas. As três entraram em `data/pistas_sinais.json` como
  `pendente_triagem` — promoção a marco (§15) é ato humano. Nenhum Boletim
  nº 3 localizado até o corte (`boletins.json` correto em 2). O PDF do
  cidadão ganhou o link oficial do Boletim nº 2 (INPE), o vigente.
- **"Você atualizou as fontes de dados?"** Parcialmente, e digo o que não:
  nesta sessão os dados só mudaram pelo que foi confirmado em busca web
  (os 5 decretos de SC de 30/08) e por correções; não houve passada de
  descoberta contra a web a partir daqui — o sandbox não alcança gov.br,
  DOU nem prefeituras. A descoberta de verdade é a Action semanal (hoje é
  segunda; a fila de sinais estava vazia, sinal de que a última passada não
  viu a portaria de 18/08 ou não rodou — conferir no histórico da Action).
- **"Você conferiu todos os links?"** Não — e não podia daqui. Pior: o
  `verificar_links.py` existia mas **não rodava em lugar nenhum**, cobria
  só 4 páginas e não via as URLs em constantes JS (27 portais estaduais,
  diários oficiais, guias, links do PDF) nem estados.json. Corrigido: escopo
  ampliado para 188 URLs (47 href das 5 páginas + 37 de JS/estados + 104
  do banco municipal) e **ligado ao workflow semanal** como etapa
  informativa (`continue-on-error`), com `::warning::` e artefato
  `links_relatorio.txt` de 30 dias. Link quebrado nunca é removido
  automaticamente — decisão humana, regra de ouro. A primeira rodada real
  acontece na próxima execução da Action.

### Changed (quarta nomenclatura das faixas: estágio inicial · em construção · consolidado · avançado)
- Patricia escolheu, entre famílias alternativas (visibilidade, construção,
  mar/navegação, viagem, farol), a nomenclatura de estágio, pelo critério de
  **compreensão imediata pelo cidadão**: 0–25 *estágio inicial* · 25–50 *em
  construção* · 50–70 *consolidado* · 70–100 *avançado*. Cortes numéricos
  intocados. Trocado em todos os lugares onde o nome aparece: pílula do
  medidor, régua (25/50/70 e "0 · estágio inicial"), "Como ler o MARÉ",
  frase do PDF do cidadão ("está em 67,4/100 (consolidado)"), PDF do índice
  (`gerar_pdf_indice.py`), METODOLOGIA.md e texto-fonte da tese.
- **Duas coisas que o inventário revelou antes de trocar**, registradas na
  METODOLOGIA como parte da decisão: (1) a família "estágio" já havia sido
  usada e aposentada em 27/08 ("metáfora de processo que o índice não
  mede"); a quarta renomeação reverte isso conscientemente e responde à
  objeção explicitando o objeto — é o estágio do *arcabouço público
  publicado*, não da capacidade nem do processo interno; (2) a METODOLOGIA
  estava **divergente do site** havia dias (dizia "inicial · em
  desenvolvimento · em consolidação · avançado" enquanto o site mostrava
  "ponto de partida · caminho aberto…") e o §5.5 ainda dizia "média
  nacional 40,2" — está em 47,1. §5.5 atualizado com a trajetória auditável
  (40,2 → 45,2 → 46,8 → 47,0 → 47,1, cada passo já no CHANGELOG).
- **Portão novo (9) em `verificar_consistencia.py`**: os quatro nomes
  precisam aparecer idênticos na pílula, na frase do PDF, na régua, no
  "Como ler", na METODOLOGIA e no gerador do PDF do índice; e nenhum nome
  aposentado pode sobrar no site. Teria acusado a divergência acima no dia
  em que surgiu. Testado nos dois sentidos.
- METODOLOGIA.pdf e MARE_Indice_Documentacao.pdf regenerados; auditoria
  completa dos 5.598 PDFs do cidadão refeita (ok). **Pendente**: o
  `.docx` da tese não regenera — as figuras (fig1–fig4) foram produzidas
  fora do repositório em 27/08 e não estão em /tmp; o texto-fonte
  (`gerar_tese.js`) está atualizado, inclusive o histórico das quatro
  nomenclaturas, para quando as figuras forem regeradas. A tese segue como
  fotografia datada (41,1, n=254, corte 26/08).

### Changed (lede do herói: de estilo inline a classe responsiva)
- Patricia perguntou por que o parágrafo de abertura ("Em 29 de junho de
  2026, o Boletim nº 1…") tem aquele tamanho. É um *lede* — abertura
  editorial em Fraunces 19px (degrau h3 da escala), único no site. O que
  estava errado: estilo inline (fora do sistema de classes), `max-width:
  820px` dando ~86 caracteres por linha no desktop (faixa ideal 60–75), e
  nenhuma redução no celular — 12 linhas de ~30 caracteres em 375px.
  Agora `.hero-lede`: `max-width:68ch` (68 c/l no desktop), 17px abaixo de
  640px. Medido depois: 6 linhas no desktop; no celular ainda 11 — porque o
  parágrafo faz dois trabalhos (notícia + missão) e é longo para um lede;
  isso é editorial, ficou como proposta para Patricia — **aprovada e
  implementada**: o lede ficou só com a notícia ("…confirmou o fenômeno para
  o ciclo 2026/2027: estiagem na Amazônia e no Nordeste, chuvas extremas no
  Sul"), e a frase da missão desceu para um parágrafo normal (Archivo 15px,
  em `--ink`). Medido: lede de 12 para 5 linhas no celular, de 6 para 3 no
  desktop. Nenhuma palavra de conteúdo perdida.

### Fixed (auditoria de design, acessibilidade e responsividade — por código, não por olho)
- Patricia pediu verificação **via código** de alinhamento e padronização, com
  autocrítica sobre tamanhos, responsividade e boas práticas. Ferramentas:
  análise estática do CSS das 5 páginas (cores, variáveis, pilhas de fonte,
  escala tipográfica, identidade do masthead), axe-core (WCAG 2.1 AA + boas
  práticas) e medição em navegador real em 3 viewports (375/768/1280). Estado
  final: **0 violações axe nas 15 combinações página×viewport**; nenhum
  overflow horizontal; nenhum texto <12px em HTML; 1 `<h1>` por página;
  ordem de títulos sem pulos; `<main>` em todas. Tudo abaixo estava errado
  antes e foi corrigido:
  - **Formulário inutilizável no celular**: `select`/`input` de envie-dados
    estouravam 345px além da tela em 375px (largura intrínseca das opções;
    o grid não deixava encolher). `min-width:0; width:100%` nos campos.
  - **Contraste**: a pílula "Caminho aberto" (claro sobre tan) tinha 2,24:1;
    o terracota #A65F3F como texto pequeno falha sobre todos os fundos do
    site (3,6–4,3). Pílulas agora usam pares calculados (ferrugem/claro 6,45;
    tan/escuro 6,65; oliva escurecido #6B6A44/claro 4,94; azul/claro 6,91);
    rótulos pequenos em terracota (`.export-box .k`, `.capital-box .k`,
    seções do PDF) viraram ferrugem #7C4A34 (5,5–6,5).
  - **aria-label proibido** em 11 spans da linha do tempo (index) e 81
    `<path>` dos mapas: elementos sem papel não podem ter nome acessível —
    `role="img"` adicionado. Idem na `.strip` do herói (HTML estático).
  - **Fontes**: pilhas de fallback inconsistentes — 9 regras com `'Archivo
    Narrow',monospace` (Courier se o Google Fonts falhar, como falha neste
    ambiente), 5 com `'Fraunces',sans-serif`, uma sem fallback. Unificadas:
    Fraunces→Georgia/Times/serif; Archivo→system-ui/-apple-system/Segoe UI;
    Archivo Narrow→Arial Narrow/Arial. Dentro de strings JS o banner de erro
    usa pilha sem aspas (a primeira tentativa quebrou a sintaxe de 2 páginas
    — pego pelos portões).
  - **Tipografia**: 9,5/10,5/11px no medidor e nas peças da grade → 12px;
    10px na impressão do proteja-se → 12px. Siglas dos mapas 9,5→11 (unidade
    SVG; ficam pequenas por escala do mapa — cue secundária, o nome acessível
    está no `aria-label`).
  - **Consistência que eu mesma quebrei**: `.site-title` da página de mapas
    em `clamp(28px…38px)` contra `clamp(33px…46px)` nas outras quatro.
    Igualado. `h4` direto sob `h2` nos 15 cartões (pulo de nível) → `h3`.
  - **Um h1 por página**: nas 4 secundárias o título do site virou `<p
    class="site-title">` (mesmo estilo); o h1 é o título da página (a de
    mapas ganhou o dela). `<main id="conteudo">` + skip link nas 4;
    `meta description` nas 3 que não tinham.
  - **Celular**: barra de âncoras do proteja-se era rolagem horizontal
    escondida → quebra linha; URLs longas dos portais → `overflow-wrap:
    anywhere`; `<summary>` de 22px → alvo ≥24px. `prefers-reduced-motion`
    respeitado nas 5. CSS morto removido (`.verdict`, variáveis --green/
    --slate/--teal/--violet).
  **Portão permanente** (7) em `verificar_estrutura.js`: 1 h1, `<main>`,
  description, skip link, pilhas de fonte, nada <12px (CSS e inline),
  `.site-title` idêntico, reduced-motion, aria-label sem role. Ferramentas
  manuais: `scripts/auditar_ux.js` (axe + viewports).
  **Não feito, e por quê**: 22 cores aparecem numa página só (tints de
  gradiente no index, fundos dos grupos de risco no proteja-se). São
  derivações da paleta, não desvios — mas o ideal seria expressá-las como
  variáveis. Fica como recomendação: refatoração de tema, não correção.

### Added (auditoria completa dos PDFs — todos os 27 estados e 5.571 municípios)
- Patricia perguntou se eu estava satisfeita com a qualidade dos PDFs de
  *todos* os estados e municípios. Não estava: tinha visto 32 de 5.598. Nova
  ferramenta `scripts/auditar_pdfs.py` (com `auditar_pdfs_geracao.js` e
  `auditar_pdfs_conteudo.js`): gera em memória, em navegador real com jsPDF,
  os 27 relatórios estaduais e os 5.571 municipais do IBGE e confere cada um.
  Resultado: **5.598 gerados, zero exceções, zero problemas** — 6 seções em
  todos, nenhum `undefined`/`NaN`/campo vazio/decimal com ponto, nenhum
  caractere fora do WinAnsi (o que o helvetica do jsPDF sabe desenhar),
  2 páginas em 5.584 e 3 em 14, nenhum título mais largo que a página (o
  mais longo, "Vila Bela da Santíssima Trindade · MT", cabe). Conteúdo
  conferido contra os dados: os 265 registros municipais aparecem com
  categoria, documento e fonte; as 5 emergências aparecem; os 27 estados
  com a frase de status certa, documento, capital e recurso preventivo
  quando há. Antes disso, checagem de integridade: as 265 grafias de
  `municipios.json`, as 5 de `atos_resposta.json` e as 27 capitais batem
  com a lista do IBGE (senão o cartão diria "nada localizado" com registro
  existente); nenhum homônimo dentro da mesma UF; `PORTAIS_UF` e `EMAILS`
  cobrem as 27 UFs.
- **Ajuste real achado no caminho**: o relatório do DF dizia "Municípios do
  estado com algum ato localizado: 0 de 1 (0%)" — sem sentido, o único
  município é Brasília, já descrita na linha da capital. Linha suprimida
  para o DF.
- A auditoria não roda no CI (precisa de navegador e jsPDF locais); é
  ferramenta manual, a rodar a cada mudança no gerador de PDF.

### Fixed (PDFs do cidadão: prova de atualização e dois furos fechados)
- Patricia pediu para checar se os PDFs se atualizam. Prova por medição:
  gerei PDFs de RN, Sorocaba/SP, Biguaçu/SC e Chapecó/SC, apliquei três
  mudanças reais pelo pipeline automático (RN ganha plano estadual, Sorocaba
  ganha plano municipal, Chapecó decreta emergência), regenerei e comparei
  o texto. RN: "sem plano estadual" → "plano estadual novo … Decreto Estadual
  nº 12.345", MARÉ 10,9 → 74,3, a linha "cobrar plano estadual" some.
  Sorocaba: "nenhum plano localizado" → "Plano preventivo — Plano de
  Contingência …", cobertura de SP 7 → 8. Média nacional 47,1 → 49,5 em
  todos. Tudo restaurado depois (não são dados reais).

  **Dois furos reais no PDF e no cartão, achados no "antes"**:
  1. **Biguaçu/SC** dizia "nenhum plano ou decreto localizado" — mas
     Biguaçu decretou emergência em 30/08 e está no mapa 6. Causa:
     `index.html` não carregava `atos_resposta.json` (só a página de mapas
     carregava). Corrigido: index.html volta a carregar o arquivo; nova
     `emergenciasDoMunicipio()`; cartão e PDF mostram "decretou situação de
     emergência em DATA (causa) — ato de resposta, não conta para o índice",
     tanto para cidade com registro quanto sem registro em municipios.json
     (o portão pegou esse segundo ramo faltando, na primeira tentativa).
     Chapecó, decretando emergência pelo pipeline, agora aparece no PDF —
     prova de que atualizações de `atos_resposta.json` também chegam lá.
  2. **Chapecó/SC** saía como "Nada localizado — — (—). Fonte: —." — o
     template imprimia campos vazios do registro `nao_localizado`. Agora:
     "verificado individualmente — nenhum plano ou decreto localizado…", e
     "o que cobrar" trata `nao_localizado` como ausência. Quando há
     emergência, a frase vira "nenhum plano preventivo localizado", para não
     contradizer a linha do decreto logo abaixo.
  No caminho, um erro meu de escopo (`emergs` declarada num bloco e usada
  noutro — o PDF municipal travava sem mensagem) foi pego pelo teste de
  ponta a ponta e corrigido. Portão de runtime ampliado: index.html carrega
  atos_resposta; o gerador mostra emergências; o cartão de Biguaçu exibe o
  decreto de 30/08. Os 30 PDFs do sorteio (+ Biguaçu e Chapecó) regenerados
  e verificados automaticamente: 6 seções, sem campos vazios, sem defeitos.

### Changed (relatórios em PDF refeitos para o cidadão, template único)
- Patricia, ao conferir a amostra de 30 PDFs: "esses PDFs são para usuários,
  não para auditores". Tinha razão — o relatório estadual abria com um
  parágrafo sobre "não publicar posição ordinal", trazia "componentes (pesos
  iguais de 1/3)", "peso aritmético = fração populacional" e "camada
  declarada (fonte: TCE-RS…)"; e o municipal seguia outra estrutura. Eram
  dois anexos de metodologia, cada um de um jeito.

  **Um único gerador, `gerarRelatorioCidadao(uf, municipio)`**, usado pelos
  dois botões (o estadual e o municipal viram wrappers), na ordem do que
  importa para quem mora lá: (1) *Em emergência, ligue* — 199/193/192, SMS
  40199, Defesa Civil Alerta, órgão estadual com portal e e-mail (PB e RN:
  telefone, já que não têm portal); (2) *Risco projetado para o estado
  neste ciclo* (Boletins nº 1 e 2); (3) *O que já existe* — plano estadual
  em linguagem humana com nome e data, recurso preventivo se houver, o ato
  da cidade (ou da capital, no relatório estadual) com fonte, cobertura do
  estado numa frase, MARÉ numa linha só, em faixa; (4) *O que ainda falta —
  e o que cobrar*, derivado da situação real (estado sem plano, plano em
  elaboração, plano da cidade desatualizado, só decreto reativo, coberto
  pelo estado "cobertura operacional, o dever municipal continua — Lei
  12.608, art. 8º", como pedir pelo e-SIC); (5) *Como se proteger* — os
  guias Antes/Durante/Depois só dos riscos projetados para aquele estado;
  (6) *Links úteis* — só URLs já verificadas no projeto (a do Painel El
  Niño que eu tinha escrito de memória foi trocada pela do CEMADEN, já
  verificada; nenhum link inventado).
  Fora do PDF: metodologia, componentes, confiança, camada declarada,
  pendências — continuam em METODOLOGIA.pdf. `PORTAIS_UF` (27 portais)
  extraído de proteja-se.html para o index. Os 30 PDFs do sorteio
  regenerados: 6 seções em todos, 2-3 páginas, sem decimal com ponto, sem
  `tel:` exposto, sem `undefined`.

  **Portão permanente** em `verificar_runtime.js`: as 6 seções existem na
  ordem; nenhuma das frases de auditor no gerador; estado e município usam
  o mesmo gerador.

### Fixed (relatórios em PDF — bug de produção achado em amostra de conferência)
- Patricia pediu uma amostra aleatória de PDFs (10 estados, 20 municípios;
  semente 20260831, sorteio em `pdfs_conferencia/00-sorteio.json`). Ao gerar
  pelo caminho real do usuário (clique no estado → clique no botão), num
  navegador de verdade com jsPDF: **o botão "Baixar relatório do estado
  (PDF)" não funcionava** — `gerarPDFEstado is not defined`, nenhum
  download. Causa: `onclick` inline (escopo global) chamando função
  declarada dentro de `__init()` (escopo local). O botão municipal
  funcionava porque usa listener no mesmo escopo. Corrigido com o mesmo
  padrão de delegação (`id="btnPDFEstado" data-uf`, listener em `#detail`).
  O portão de runtime nunca clicava nos botões de PDF — agora clica nos
  dois e exige zero erros (testado nos dois sentidos).
- Nos 30 PDFs gerados, mais dois defeitos: (1) o subtítulo do PDF municipal
  ("MARÉ · Medida de Antecipação e Resposta ao El Niño · Relatório da
  consulta · Corte dos dados…") estourava a margem direita, cortando "Gerado
  em" — encurtado para o mesmo padrão compacto do PDF estadual; (2) decimais
  com ponto em três lugares do cartão municipal (e, por cópia, do PDF):
  "12.9 pontos acima", "38.67%", "100.0%" → vírgula. Varredura automática
  nos 30 PDFs regenerados: nenhum decimal com ponto, nenhum cabeçalho cortado.

### Changed (parágrafos dos mapas 5, 6 e 7 reescritos no padrão dos mapas 1 a 4)
- Patricia pediu que o parágrafo de cada mapa descrevesse **o que se vê no
  mapa**, direto e elegante, no mesmo padrão dos mapas 1 a 4. Relendo esses
  quatro, o padrão é claro: uma frase sobre o que o mapa mostra + como ler
  as cores (ex.: "quanto mais escuro, maior o percentual"; "hachura = nenhum
  ato identificado"; "Cores distinguem o tipo de ato (passe o mouse)") —
  nunca ressalva metodológica. Os mapas 5 e 6 estavam cheios de metodologia
  no parágrafo visível (proxy, "não é a lista oficial", Correção B §5.6,
  "nunca não existe").

  **Reescritos os três** nesse espírito — mapa 5: "N municípios prioritários
  do Cadastro Nacional de Suscetíveis: N já têm instrumento localizado (ponto
  cheio); os demais aparecem tracejados"; mapa 6: "N cidades que decretaram
  situação de emergência ou calamidade pública, localizadas em fontes
  oficiais até o corte. Passe o mouse para ver data e causa"; mapa 7:
  "Repasses estaduais confirmados (Prepara RS) em azul, com tamanho
  proporcional ao valor; municípios habilitados a recurso federal de
  resposta em ocre. Passe o mouse para ver faixa e valor". Toda a ressalva
  metodológica foi para o `<details>` de cada cartão (o mapa 6 ganhou um,
  "Por que estes decretos não entram no índice" — a Correção B continua a um
  clique, não sumiu). Nenhum `id` dinâmico se perdeu; protocolo canônico
  completo verde.

### Fixed (quinta rodada: 2 parágrafos nos mapas 5 e 6, contra 1 em todo o resto)
- Patricia apontou o exemplo concreto: o mapa 5 tinha dois `<p class="note">`
  separados antes do mapa, enquanto os mapas 1 a 4 têm só um. Contei os
  parágrafos visíveis (fora de `<details>`) nos 15 cartões da página inteira
  (7 mapas + 6 gráficos + 2 painéis de financiamento): mapas 5 e 6 eram os
  únicos com 2; todo o resto já tinha exatamente 1. Fundidos os dois
  parágrafos de cada um num só, preservando as duas informações (a
  aproximação metodológica e a contagem publicada/tracejado) e os `id`
  usados pelo JavaScript (`countPrioritariosTotal`, `countPrioritariosPublicados`,
  `countAtosResposta`) — só uma redundância numérica foi removida ao fundir
  (o "2.095" fixo no texto e o `countPrioritariosTotal` calculado eram o
  mesmo número dito duas vezes).

  **Portão novo, permanente**: `scripts/verificar_runtime_mapas.js` conta os
  parágrafos visíveis de cada cartão de mapa ou gráfico e reprova qualquer
  um que não tenha exatamente 1 — a regra que já valia implicitamente para
  13 dos 15 cartões agora é regra escrita, testada nos dois sentidos.

### Fixed (texto de legenda encurtado em todos os 7 mapas — não só 5, 6, 7)
- **Quarta rodada sobre o mesmo tema, escopo diferente desta vez**: Patricia
  pediu para comparar diretamente as legendas dos mapas 1 a 5 (compactas,
  ~2 linhas) contra o que vinha depois (muito mais extensas) e aplicar o
  mesmo raciocínio em todo lugar. Medindo caractere por caractere de cada
  item de legenda da página inteira: variavam de **5 a 63 caracteres** —
  o mapa 3 já usava rótulos curtos e diretos ("misto", "só decretos
  reativos"), enquanto o mapa 1 tinha itens como "Ato verificado, mas não é
  de El Niño (saúde/alagamento)" (55) e o mapa 6 tinha uma frase de 63
  caracteres inteira.

  **Reescritos todos os rótulos de legenda dos 7 mapas** para nomes de
  categoria diretos, cortando o aposto explicativo entre parênteses (esse
  detalhe continua disponível no tooltip ao passar o mouse, que tem espaço
  de sobra) — ex.: "Plano preventivo publicado (contorno claro)" → "Plano
  publicado"; "Ato verificado, mas não é de El Niño (saúde/alagamento)" →
  "Não é El Niño"; "Decreto de emergência/calamidade pública (registro, não
  pontua)" → "Decreto de emergência" (a ressalva "não pontua" já está no
  parágrafo de introdução do cartão, não precisa repetir na legenda).
  Resultado: item mais longo da página caiu de 63 para **34 caracteres**;
  legendas de vários itens (mapas 1, 5) agora cabem 2 por linha, como as
  legendas mais compactas já cabiam.

  **Portão novo, permanente**: `scripts/verificar_runtime_mapas.js` reprova
  qualquer item de legenda com mais de 40 caracteres. Testado nos dois
  sentidos.

### Fixed (a inconsistência de verdade: ícone de legenda quase invisível no mapa 5)
- **Terceira rodada sobre o mesmo problema** — a correção anterior (altura dos
  cartões) resolveu a desproporção geral, mas Patricia pediu explicitamente
  para comparar as legendas dos mapas 1, 2... contra as dos mapas 5, 6, 7,
  cartão a cartão. Capturei cada um dos 7 cartões individualmente (D3 real,
  não simulação) e comparei lado a lado — aí apareceu o problema de verdade.

  **O mapa 5 tem uma categoria ("Prioritário sem instrumento localizado
  ainda") com um ícone de legenda que não seguia o padrão de nenhum outro
  mapa**: `background:#E4DBC6` (quase idêntico ao bege de fundo do próprio
  cartão, #F5F1E8) com `border:1.5px dashed #A65F3F` — visualmente quase
  invisível, só um contorno tracejado fraco. Os mapas 3 e 4 já tinham
  **exatamente essa mesma categoria semântica** ("sem atos identificados",
  "sem instrumento estadual") resolvida com um padrão diferente e consistente
  entre si: hachura de listras diagonais (`repeating-linear-gradient`),
  sempre bem visível. O mapa 5 era o único caso na página inteira usando
  preenchimento quase invisível + borda tracejada em vez da hachura já
  estabelecida — confirmado por busca no arquivo inteiro, não impressão.

  **Corrigido**: o ícone do mapa 5 agora usa a mesma hachura diagonal já
  usada nos mapas 3 e 4, com a cor #A65F3F (a mesma já usada no contorno
  daquela categoria, para consistência interna do próprio mapa 5).

  **Portão novo, permanente**: `scripts/verificar_runtime_mapas.js` reprova
  qualquer ícone de legenda de mapa que use borda tracejada — o padrão
  correto para "sem dado" é sempre hachura, nunca contorno tracejado sobre
  preenchimento apagado. Testado nos dois sentidos.

### Fixed (a causa real das "legendas gigantescas" nos mapas 5, 6 e 7)
- **Correção anterior (siglas, opacidade, alinhamento) não resolveu o problema
  de verdade** — Patricia apontou que as legendas continuavam gigantescas e
  sem sentido depois daquela correção. Desta vez, em vez de inspecionar só o
  código, gerei uma captura de tela renderizada de verdade (D3 e Chart.js
  reais, embutidos localmente para contornar o bloqueio de CDN deste
  ambiente) e medi a altura real de cada cartão no navegador — não só
  contei elementos.

  **Causa raiz encontrada por medição, não suposição**: os cartões 1-3 têm
  697px de altura; os cartões 5 e 6 (herdados de painéis largos antes da
  reorganização) tinham **917px**, e o cartão 7 chegava a **1257px** — quase
  o dobro. O motivo: os parágrafos de introdução desses três cartões tinham
  até **704 caracteres** (mapa 5), contra 76-146 caracteres nos mapas 1-3.
  Textos que faziam sentido num painel largo viravam paredes de texto numa
  coluna de ~330px, empurrando o mapa e a legenda para muito mais baixo do
  que nos outros cartões — por isso a legenda "parecia" gigantesca e fora de
  contexto: não era o tamanho do ícone da legenda, era a distância e o
  desequilíbrio até chegar nela.

  **Correção**: textos de introdução dos mapas 5, 6 e 7 reduzidos para a
  mesma ordem de grandeza dos demais cartões (206, 259 e 208 caracteres,
  respectivamente — a informação essencial preservada, a explicação de
  metodologia detalhada movida para dentro de `<details>`, mesmo padrão já
  usado no mapa 4 desde a reorganização). Alturas depois da correção: 697px
  (mapas 1-3), 707px (mapas 4-6), 620px (mapa 7) — as sete cartas agora
  ficam visualmente equilibradas, e a legenda de cada mapa aparece logo
  depois do mapa, como nos mapas de referência.

  **Portão novo, permanente**: `scripts/verificar_estrutura.js` agora mede o
  texto visível (fora de `<details>`) de todo cartão de mapa/gráfico e
  reprova se passar de 320 caracteres — limite calibrado no maior cartão
  legítimo já existente na página (290 caracteres), não um número arbitrário.
  Testado nos dois sentidos: inseri um parágrafo de teste de propósito, o
  portão acusou; removi, voltou a passar.

### Fixed (harmonização visual dos mapas 5, 6 e 7)
- **Legendas fora do padrão** (achado de Patricia, 31/08/2026, ao conferir o
  grid recém-reorganizado): os mapas 5 (municípios prioritários), 6 (cidades
  que decretaram emergência) e 7 (transferências e repasses) — os três que
  vieram de painéis avulsos antes da reorganização — divergiam do padrão
  visual estabelecido pelos mapas 1-4. Auditoria feita lendo o código de
  desenho de cada mapa, não por impressão visual:
  - **Siglas de UF ausentes em 2 dos 7 mapas.** Mapas 1, 2, 3, 4 e 7 já
    tinham as 27 siglas desenhadas sobre os estados (`addSiglas()`); os
    mapas 5 e 6 nunca receberam essa chamada — confirmado contando os
    elementos `<text>` de cada mapa renderizado (27 em cinco deles, 0 nos
    outros dois). Corrigido: `addSiglas()` chamada também para os mapas 5 e 6.
  - **Legenda do mapa 7 centralizada**, enquanto as outras seis ficam
    alinhadas à esquerda (`justify-content:center` inline, único caso na
    página). Removido — agora as sete legendas seguem o mesmo alinhamento.
  - **Opacidade reduzida nos pontos dos mapas 5, 6 e 7** (`opacity`/
    `fill-opacity` entre 0.6 e 0.9), efeito que os mapas de referência (1-4)
    nunca usam — lá a distinção visual vem só de cor, contorno e traço
    tracejado, sempre em opacidade total. Removida a redução de opacidade
    nos três mapas; traços (`stroke-width`) também nivelados aos valores já
    usados nos mapas de referência (1 para pontos simples, 1.6 para os
    pontos de maior destaque em cada mapa).
  - **Cores conferidas contra a paleta inteira da página** (contagem de
    todos os valores hexadecimais usados): os mapas 5, 6 e 7 já usavam só
    cores do sistema "Futurismo Regenerativo" já estabelecido — nenhuma cor
    nova foi introduzida por eles; o problema era estrutural (siglas,
    alinhamento, opacidade), não a paleta em si.

  **Portão novo, permanente**, em `scripts/verificar_runtime_mapas.js`: (1)
  confere que os 7 mapas têm exatamente 27 siglas cada; (2) confere que
  nenhuma legenda sobrescreve o alinhamento padrão. Testado nos dois
  sentidos (removi uma chamada de sigla de propósito, o portão acusou;
  restaurei, voltou a passar). Protocolo canônico completo rodado depois —
  tudo verde, nenhum dado mudou, só a apresentação visual dos três mapas.

### Changed (mapas-e-graficos.html — grid único, agrupado por tema)
- **Reorganização visual completa** (pedido de Patricia, 31/08/2026): "todos
  os mapas e gráficos precisam estar lado a lado, com harmonização de padrão
  visual e agrupados por tema". Antes, a página tinha 5 painéis soltos —
  4 mapas num grid, 6 gráficos noutro, e **3 mapas órfãos** (municípios
  prioritários, cidades que decretaram emergência, mapa de transferências)
  cada um sozinho no seu próprio painel, sem nenhum grid, quebrando o
  "lado a lado". `.map-box` e `.chart-box` já eram visualmente idênticos no
  CSS (mesmo fundo, borda, padding) — o problema era estrutural, não de
  estilo.

  **Duas seções temáticas agora, cada uma um grid único:**
  - **"Mapas geográficos"** — os 7 mapas juntos, lado a lado (verificação
    municipal, cobertura, natureza dos atos, risco×instrumento, municípios
    prioritários, cidades que decretaram emergência, transferências e
    repasses), renumerados 1–7 em sequência narrativa.
  - **"Gráficos analíticos"** — os 6 gráficos juntos (renomeada de "Análises:
    antecipação, tipo de resposta e lacunas de documentação" para nome mais
    direto). No processo, corrigido um texto que dizia "cinco leituras
    cruzadas" quando são seis gráficos — imprecisão antiga, só ficou visível
    ao reagrupar tudo num único lugar.
  - **"Como o dinheiro chega"** — painel de contexto compacto (2 cartões de
    texto: o caminho do recurso federal, onde monitorar cada etapa), separado
    do mapa de transferências (que se juntou ao grid de mapas como item 7) —
    não é mapa nem gráfico, então não precisa estar no mesmo grid, mas
    manteve o mesmo estilo de cartão para continuidade visual.

  Grid mudou de `repeat(2,1fr)` fixo para `repeat(auto-fit, minmax(330px,
  1fr))` — 3 colunas em tela cheia, encolhendo com harmonia até 1 coluna em
  telas pequenas, em vez de sempre exatamente 2. `.charts-grid` e `.maps-grid`
  usam agora a mesma regra.

  **Todos os `id` usados pelo JavaScript preservados exatamente** (nenhum
  mapa, gráfico, contador ou legenda precisou de ajuste de código — só a
  casca HTML ao redor mudou) — confirmado por varredura antes de mexer, não
  por sorte. `#financiamento` (usado por um link cruzado a partir de
  `index.html`) migrou do antigo painel grande para o h2 do novo painel
  "Como o dinheiro chega". Testado com o protocolo canônico completo,
  incluindo `verificar_runtime_mapas.js` (as mesmas contagens exatas de
  antes: 265 pontos, 27 UFs em cada mapa de estado, 2.095 municípios
  prioritários, 103 atos de resposta) — nenhum dado mudou, só o arranjo.

### Changed (ordem da navegação)
- **"Mapas e gráficos" reordenada para logo após "O monitor"** (pedido de
  Patricia, 31/08/2026) em vez de ficar depois de "Proteja-se" — ordem
  atualizada nas 5 páginas: O monitor · Mapas e gráficos · Proteja-se ·
  Enviar documento. Protocolo canônico completo rodado depois da mudança.

Natureza da versão: acatamento integral da auditoria externa de 29/08/2026
(itens C1–C9), **fim do ranking ordinal como produto público** (§13) e
**errata de dados da revisão de natureza** (§16). Motor de cálculo intocado
em toda a versão; a errata de dados (§16) corrigiu classificações de
entrada de AC, AM e PE e levou a média nacional de 41,1 para **40,2** —
reproduzida bit a bit pelos portões após a correção. A designação v2.3 segue reservada ao
fator de alinhamento risco-plano (roadmap).

### Changed (design — mapas e gráficos em página própria)
- **Nova página `mapas-e-graficos.html`** (pedido de Patricia, 31/08/2026):
  todos os mapas e gráficos saíram da página inicial e ganharam página
  dedicada, coerente com o sistema de design já estabelecido (mesmo
  masthead/rodapé/navegação das outras páginas secundárias). Nenhum dado
  mudou — só o lugar onde vivem no site. Migrados: os 4 mapas de
  categoria/cobertura/natureza/risco×instrumento (+ tabela risco×instrumento),
  os 6 gráficos de análise, o painel de financiamento e transferências
  (+ mapa de repasses), o mapa de municípios prioritários e o mapa de cidades
  que decretaram emergência (de ontem). `index.html` ficou com o essencial:
  herói, medidor, grade de estados por região, "Encontre sua cidade",
  registros e fontes (incluindo a tabela de auditoria municipal).

  **Harmonização, não só corte**: como nenhum mapa/gráfico ficou na página
  inicial, ela deixou de carregar D3 e Chart.js do CDN — nenhuma linha do
  JavaScript restante usa qualquer um dos dois (confirmado por varredura, não
  suposição); só jsPDF continua (os relatórios em PDF ficam lá). O aviso de
  erro que checava "Chart.js/D3 não carregaram" foi ajustado para checar
  jsPDF. CSS morto (`.charts-grid`, `.chart-box`, `.maps-grid`, `.map-box`,
  `.map-legend`, `.uf-path` e variantes — nada disso tem mais elemento
  correspondente em `index.html`) removido do `<style>` da página inicial.

  **`CONSIST` deixou de ser JavaScript embutido e virou `data/consist.json`**
  — antes vivia como literal dentro do HTML (primeiro em `index.html`, depois
  seria duplicado se cada página precisasse da sua própria cópia); agora é
  JSON de verdade, buscado por fetch tanto por `index.html` (cartão de
  cidade, que mostra o risco projetado do estado) quanto por
  `mapas-e-graficos.html` (mapa e tabela de risco×instrumento). `AREAS`
  permaneceu como literal JavaScript, mas mudou de arquivo (agora vive em
  `mapas-e-graficos.html`).

  **Achado real durante a extração, não hipotético — testado de ponta a
  ponta contra o banco real (RN), não só inspeção de código**: sobrou, no
  bloco movido, uma declaração antiga `const CONSIST = {...}` com dados
  obsoletos (embutida antes da extração para `consist.json`), que **sombreava
  silenciosamente** a versão nova buscada via fetch — a tabela renderizava
  normalmente, mas com números desatualizados, sem erro nenhum aparente. Só
  apareceu ao aplicar uma UF de teste e comparar a contagem renderizada
  contra o `consist.json` real no disco. Removida a declaração morta;
  reconfirmado com o mesmo teste que a aplicação automática de ontem
  (`julgar_e_aplicar_descobertas.py`) funciona de ponta a ponta com a nova
  arquitetura de duas páginas, incluindo rollback real se algum portão
  falhar. Também achados e corrigidos, na mesma varredura: 3 links âncora
  quebrados em `index.html` (`#riscoinstrumento`, `#financiamento` no texto
  do herói, `#mapCobertura` em 2 cartões de KPI) apontando para seções que
  se mudaram — sem nenhum portão que os pegasse antes.

  **Dois portões novos, permanentes**: (1) checagem de âncoras internas em
  `scripts/verificar_estrutura.js` — todo `href="#algo"` precisa ter um
  `id="algo"` na mesma página, testada nos dois sentidos; teria pego os 3
  links quebrados acima sozinha, sem precisar de varredura manual. (2)
  `scripts/verificar_runtime_mapas.js` — mesmo padrão de
  `scripts/verificar_runtime.js` (jsdom + D3 real, Chart simulado), cobrindo
  os 7 mapas e a tabela da página nova; os testes que antes viviam em
  `verificar_runtime.js` e checavam mapas/gráficos migraram para cá, já que
  os elementos que checavam não existem mais em `index.html`. Os dois
  portões novos conectados ao `atualizar.py` e à função `rodar_portoes()` de
  `julgar_e_aplicar_descobertas.py`. `verificar_consistencia.py` também
  atualizado: a checagem de `CONSIST`/`AREAS` agora lê `data/consist.json` e
  `mapas-e-graficos.html` em vez de `index.html`. Navegação atualizada nas 5
  páginas. Escopo do commit automático da Action (`.github/workflows/
  atualizar.yml`) ampliado para incluir `mapas-e-graficos.html`. Protocolo
  canônico completo rodado ao final — tudo verde, média nacional inalterada
  (47,1), porque isso foi só reorganização, nenhum dado mudou.

### Added (mapa de atos de resposta)
- **Mapa "Cidades que decretaram emergência"** (index.html, painel final antes
  do rodapé — pedido de Patricia, 31/08/2026, motivado pelo temporal de
  granizo em Santa Catarina de 30/08/2026). Mostra decretos de situação de
  emergência/calamidade pública — **atos de resposta, que nunca pontuam no
  índice** (Correção B) — como um registro de transparência à parte, com
  aviso explícito na própria tela (não só na metodologia).

  Confirmado por busca antes de qualquer coisa ser construída (não se partiu
  do relato como dado): Defesa Civil de Santa Catarina (fonte oficial) +
  múltiplas reportagens confirmam 5 municípios — Florianópolis, Biguaçu, Bom
  Jesus, Ipuaçu e Quilombo — decretaram emergência em 30/08/2026 por chuva
  intensa com granizo (mais de mil residências afetadas no total). Número de
  decreto localizado apenas para Biguaçu (285-A/2026, fonte de imprensa —
  ainda não confirmado contra o Diário Oficial do Município); os demais
  registrados como "número exato não localizado até o corte", nunca como
  "não existe".

  **Decisão de arquitetura:** novo arquivo dedicado `data/atos_resposta.json`,
  não uma extensão de `municipios.json`. Um ato de resposta é um EVENTO
  datado (uma cidade pode decretar emergência várias vezes por ano, por
  eventos diferentes); `municipios.json` representa o STATUS ATUAL de
  preparação de cada cidade (um registro por cidade). Achado que confirmou a
  decisão: Florianópolis já tinha um registro ex-ante em `municipios.json`
  (`plano_elaboracao`) sem nenhuma relação com este decreto — as duas coisas
  coexistem sem conflito porque vivem em arquivos diferentes.

  O mapa mostra a união de dois universos: os eventos novos de
  `atos_resposta.json` e os registros históricos já existentes em
  `municipios.json` (categoria `decreto`, majoritariamente PB, 98 registros
  antigos) — panorama nacional completo, não só os 5 novos de SC. Validado
  com 3 checagens novas no portão de runtime (contador bate com a soma real
  das duas fontes; um círculo por evento no mapa, nem mais nem menos; os 5
  municípios de SC estão presentes) e uma checagem estrutural no portão de
  consistência (canal válido, coordenadas dentro do território brasileiro,
  sem eventos duplicados) — testada nos dois sentidos, positivo e negativo.

### Added (rotina de busca automática de atos de resposta)
- **`monitorar_atos_resposta.py`** — vigia de imprensa nacional por novos
  decretos de emergência, reaproveitando a infraestrutura já existente de
  `monitorar_imprensa_regional.py` (mesma fila de pistas, mesma trava
  absoluta de fonte oficial, mesma deduplicação) em vez de duplicá-la.
  Diferença deliberada: varre as 27 UFs em rodízio simples, sem priorização
  — um temporal pode acontecer em qualquer lugar, diferente da busca de
  instrumentos ex-ante, que prioriza UFs sem plano ainda. Cursor próprio
  (`data/resposta_cursor.json`), isolado do cursor de imprensa, testado para
  não interferir um no outro.

  **`julgar_e_aplicar_descobertas.py` estendido**: atos classificados como
  RESPOSTA deixam de ser só descartados — agora, quando a fonte é oficial,
  o município é identificável no texto (busca pelo nome de cada município da
  UF-alvo na referência do IBGE — a busca varre a UF inteira, não sabe de
  antemão qual cidade) e o evento não é duplicata, aplicam automaticamente
  em `data/atos_resposta.json`, com causa extraída por palavra-chave
  (granizo/estiagem/enchente/deslizamento/vendaval/etc., nunca inventada — se
  nada bater, fica "não especificada no texto"). Barra de citação mais
  branda que a de ex-ante: número do decreto ausente não bloqueia a
  aplicação (o registro de transparência tolera "número não localizado",
  diferente do que pontua, que exige citação completa). Testado de ponta a
  ponta contra o banco real (Chapecó/SC, desfeito após validar — não é dado
  real): aplicou corretamente na primeira tentativa depois de um ajuste de
  formatação de texto (citação duplicada "nº Decreto nº X").

  Conectado ao workflow semanal (`.github/workflows/atualizar.yml`), logo
  depois da vigia de imprensa existente e antes do julgamento automático —
  validado com YAML sintaticamente correto (aprendendo com o erro de sintaxe
  encontrado na sessão anterior, testado antes de dar como pronto desta vez).

### Fixed (dados dinâmicos)
- **Os 5 cartões de estatística do topo eram texto fixo, não calculado**
  (achado de Patricia, 31/08/2026): "14 Programas federais", "27 Registros
  estaduais", "7 Estados sem plano", "27 Capitais verificadas", "728
  Municípios em estados sem plano" estavam digitados à mão no HTML. Conferido
  contra o banco real no momento da correção: "7 estados sem plano" já
  estava desatualizado em 5 (o real era 2 — PB, RN, após as reclassificações
  de AP/PA/AL/SE/DF/PE desta sessão); "14 programas federais" também estava
  errado — a lista real tinha 13 itens, não 14, um erro que já existia antes
  desta sessão e não tinha sido percebido. Os 5 cartões agora são calculados
  em `__init()` a partir de `MARE`/`DATA`/`MUN_REF` a cada carregamento —
  nunca mais escritos à mão. Portão de runtime ganhou 5 checagens novas que
  comparam o valor renderizado contra `data/indice.json` lido de forma
  independente (não circular); validado com teste negativo real (quebrei o
  cálculo de propósito, o portão barrou com código de saída 1; restaurado,
  passou com código 0).

### Added (julgamento automático — primeira fase)
- **Início da automação do julgamento ex-ante × resposta** (pedido de Patricia,
  31/08/2026: "o índice precisa se atualizar sozinho a cada novo decreto
  encontrado, sem passar por verificação manual"). Três módulos novos,
  construídos e testados nesta sessão, não só especificados:
  - `classificador_natureza.py` — aplica o teste do objeto (§5.2.1) ao texto
    de um ato. **Validado contra 235 registros reais da base** (125 planos +
    98 decretos de resposta já confirmados por verificação humana, além dos
    12 casos de calibração manual): 0 erros, com a parcela sem confiança
    suficiente caindo em DÚVIDA (nunca aprova nem rejeita por engano). Achou
    e corrigiu, no processo, um bug pré-existente na base (um decreto de SE
    citado no repositório com número interno truncado).
  - `verificar_recorrencia_uf.py` — só para decretos ESTADUAIS (27 UFs,
    universo pequeno; municipal fica de fora por ora — decisão explícita de
    Patricia, custo de escala diferente). Compara um decreto candidato contra
    `data/decretos_historico_uf.json` (semente inicial: DF real, achado do
    §18 addendum) para detectar reedição do mesmo instrumento ano a ano, sem
    confundir com decretos genuinamente novos que citam um antecessor
    (testado com o Acre como caso de controle).
  - `julgar_e_aplicar_descobertas.py` — orquestrador que liga pistas de
    descoberta (imprensa/Querido Diário/sinais federais) ao julgamento e à
    aplicação direta no banco quando confiante. A trava de fonte oficial
    já existente (`.gov.br`/`.leg.br`/Diário Oficial) não mudou — o que muda
    é que, satisfeita essa trava, o julgamento que antes exigia um humano
    agora é automático quando o classificador está confiante e a citação
    (número + data) está completa; cai para a fila humana em qualquer outro
    caso, exatamente como hoje.

  **Testado de ponta a ponta contra o banco real** (não só com fixtures) —
  processo que achou e corrigiu 6 bugs reais antes de qualquer coisa ir ao
  ar: (1) a checagem de portões rodava antes de recalcular o índice, sempre
  reprovando; (2) uma reversão rotulada "revertida" não desfazia nada em
  disco de fato — corrigido para rollback real (backup dos arquivos mutáveis
  antes de aplicar, restauração byte a byte se qualquer portão falhar); (3)
  `recalcular_mare.py` tem um dicionário `ESTADOS` embutido no próprio código
  Python, separado de `estados.json` — escrever só no JSON deixava o motor
  de cálculo e a exibição dessincronizados, sem nenhum portão acusando (até
  este teste); (4) caminho municipal sem lat/lon (nunca inventa coordenada —
  busca na referência do IBGE, cai pra fila humana se o município não
  constar); (5) esquecia de espelhar em `pontos_mapa.json` (o mapa lê daqui,
  não de `municipios.json`); (6) a extração de data pegava um ano solto
  ("2026" de "ciclo 2026/2027") em vez da data completa mais adiante no texto
  ("15/08/2026") — corrigido para sempre preferir a data completa, esteja
  onde estiver no texto.

  **Escopo final desta sessão — os dois caminhos funcionam de ponta a ponta**,
  testados com casos reais completos (Sorocaba/SP no municipal; RN no
  estadual — os dois desfeitos após validar, não são dados reais).

  O caminho ESTADUAL só ficou seguro depois de uma segunda rodada de achados,
  todos no mesmo teste de ponta a ponta com um estado real (RN): (7)
  `index.html` mantinha **duas cópias manuais** dos mesmos 27 registros de
  risco×instrumento — o objeto `CONSIST` (que já alimenta gráficos) e uma
  tabela HTML inteira digitada à mão, com contagens fixas por categoria. As
  duas já tinham divergido de verdade: **Pernambuco aparecia duas vezes na
  tabela**, em categorias diferentes, um bug que já estava ao vivo no site
  antes desta sessão. Resolvido eliminando a cópia — a tabela agora é gerada
  em runtime direto de `CONSIST` (`renderTabelaConsistencia()`), o mesmo
  padrão da correção dos 5 cartões de estatística; drift entre os dois deixa
  de ser possível por construção. A checagem estática de HTML bruto que
  existia em `verificar_consistencia.py` foi removida (não fazia mais
  sentido: não há mais duas cópias para comparar) e substituída por duas
  checagens no portão de runtime, que renderiza a página de verdade e
  confere a tabela já populada (testadas nos dois sentidos, positivo e
  negativo). (8) Depois de eliminar a duplicação, faltava `aplicar_estadual`
  de fato escrever em `CONSIST`/`AREAS` quando uma UF muda de categoria —
  implementado com uma regra deliberadamente conservadora: só credita
  "cobre o risco projetado" (COBRE) quando o texto do decreto menciona a
  mesma palavra-chave de risco já registrada para aquela UF; caso contrário,
  crédito parcial (PARCIAL), nunca o nível mais alto sem evidência textual
  direta. `AREAS` (agrupamento temático por risco, usado num gráfico) só
  recebe a UF nos grupos cujo tema bate com o risco já declarado — nunca
  inventa um risco novo. (9) O número fixo do medidor principal ("47,1", o
  texto mostrado antes do JavaScript carregar) não acompanhava a média
  nacional recalculada — mesmo padrão dos KPIs estáticos corrigidos
  anteriormente; `atualizar_gauge_estatico()` mantém os dois sincronizados a
  cada aplicação. Com os nove achados corrigidos, o teste real com RN
  produziu `"decisao": "APLICADA"` — os quatro arquivos (estados.json,
  `recalcular_mare.py`, índice, `index.html`) ficaram consistentes entre si,
  confirmado pelo protocolo canônico completo, incluindo reprodutibilidade
  bit a bit do índice. Nenhum dado real foi alterado por este trabalho —
  banco conferido byte a byte contra o estado anterior ao final da sessão.

  **Conectado à rotina semanal** (`.github/workflows/atualizar.yml`): nova
  etapa "Julgar e aplicar descobertas com fonte oficial e citação completa"
  roda logo depois da vigia de imprensa, antes do `atualizar.py` geral —
  degrada graciosamente (não falha o job) se não houver pista pendente ou se
  a rede para domínios oficiais estiver indisponível. Escopo do commit
  automático ampliado de `data/` para incluir também `index.html` e
  `recalcular_mare.py` — os dois únicos arquivos fora de `data/` que a
  automação pode tocar, e só através das funções testadas e protegidas por
  rollback deste módulo, nunca edição livre. O aviso final da Action (antes
  restrito a `instrumentos_revisar.json`) passou a contar também pistas de
  imprensa que ficaram pendentes de revisão humana, tornando visível no log
  da Action quanto ainda depende de alguém olhar.

### Fixed (integridade de conteúdo)
- **Nome de arquivo inventado no cabeçalho do site** (achado de Patricia,
  31/08/2026): o herói da página inicial dizia "Fonte: BD_El_Nino_2026_2027_
  Brasil.xlsx" — esse arquivo não existe em lugar nenhum do projeto, nunca
  existiu (confirmado por busca no repositório inteiro). Para uma plataforma
  cujo argumento central é "fontes primárias, sem invenção", uma fonte
  fictícia no próprio cabeçalho era uma falha de integridade grave, ainda que
  pequena em texto. Substituída por um link honesto para a seção real de
  fontes verificadas (`#fontes`, que já lista cada registro com origem e
  data). Enquanto investigava, achados dois problemas do mesmo tipo bem perto
  dali: a data "Última verificação" no herói e "Última atualização" no
  rodapé (`#metaAtualizado`, que já tinha `id` mas nunca tinha sido ligada a
  nada) eram texto fixo — a segunda desatualizada em relação ao `meta.json`
  real. `data/meta.json` também estava parado em 26-27/08, de antes de toda
  a sessão de hoje — atualizado para 31/08/2026 (corte e última atualização
  reais desta edição). Os três pontos agora são calculados a partir de
  `META`/`MARE`/`MUN_REF` a cada carregamento. 3 checagens novas no portão de
  runtime, incluindo uma que varre o conteúdo renderizado (excluindo
  `<script>`/`<style>`, para não acusar falso-positivo no comentário que
  documenta a própria correção) atrás de qualquer nome de arquivo inventado;
  validada com teste negativo real (reintroduzi o nome falso de propósito, o
  portão bloqueou com código de saída 1; restaurado, passou com código 0).

### Changed (tipografia — sistema de design)
- **Escala tipográfica consolidada nas 4 páginas** (a pedido de Patricia, que
  apontou o exemplo exato do painel "Como o Brasil está se preparando..."):
  a página inicial sozinha usava **26 tamanhos de fonte distintos**; um
  sistema profissional usa tipicamente 6-10. Consolidados em dois níveis
  disciplinados — "rótulo" (todo texto pequeno em versalete/Archivo Narrow:
  eyebrows, badges, cabeçalhos de coluna) unificado em 12,5px; "apoio" (texto
  secundário: rodapé, notas, metadados de cartão) unificado em 13,5px —
  aplicados em ~35 seletores que estavam soltos em 11/11,5/12/13/14px sem
  motivo, nas 4 páginas. Corrigidos também dois conflitos reais (mesmo
  elemento, tamanho diferente por página, mesmo padrão do achado de cores de
  ontem): `h3` global era 19px na inicial mas 16,5px nas outras 3 — unificado
  em 19px; `#meuCard h4` e `#detail h4` (mesmo papel, cabeçalho de cartão)
  eram 20px e 16,5px por uma regra que sobrescrevia a outra sem necessidade —
  unificados em 17px, com uma regra limpa em vez de duas conflitantes.
  Removidas 2 regras CSS mortas (`.panel h2` a 16px e `.hero h2` a 26px, que
  o `h2{27px !important}` global sempre sobrescrevia — nunca renderizavam,
  só confundiam quem lesse o código). Resolvida uma colisão real de nome:
  `.sub` servia para duas coisas diferentes (o parágrafo de abertura da
  página E uma etiqueta pequena ao lado do nome de uma capital) — a segunda
  declaração, por vir depois no CSS, vencia para as duas, fazendo a etiqueta
  pequena renderizar do mesmo tamanho do parágrafo. Separadas em `.site-sub`
  (parágrafo) e `.sub` (etiqueta discreta, 13,5px/muted).

- **Redesenho do bloco do medidor principal** (o trecho exato citado por
  Patricia): a faixa atual ("Caminho aberto") era uma palavra colorida solta
  dentro de uma frase corrida, seguida por uma lista repetindo os mesmos
  limiares que a barra logo abaixo já mostra visualmente (0-25, 25-50...).
  Virou um selo (badge) compacto e discreto; a lista redundante foi removida
  e os nomes das 4 faixas passaram a rotular os próprios marcos da barra
  (25/50/70), tornando a barra autoexplicativa sem repetir texto.

- **Bug real encontrado durante a reconstrução do medidor**: a barra de
  progresso principal do herói (o "47,1/100" do topo, o elemento mais visível
  do site) nunca preenchia — `animarGauges()` era chamada só com escopo
  `#regions`, e o medidor do herói fica fora dessa seção, então a função
  nunca o alcançava; a barra ficava sempre visualmente vazia (largura 0),
  descoberto ao inspecionar `getComputedStyle` durante o teste visual, não
  por leitura de código. Corrigido para `animarGauges(document.body)`. Além
  disso, os rótulos de nome de faixa nos marcos da barra estavam sendo
  cortados silenciosamente por `overflow:hidden` no elemento pai (necessário
  para as bordas arredondadas do preenchimento) — reestruturado: a linha do
  marco continua dentro da barra, o texto do nome passou para uma fileira
  própria logo abaixo, fora da área de corte. Validado com Playwright
  (Chromium headless) antes e depois — não só inspeção de código.

- **2 checagens novas no portão de runtime**, permanentes: a barra do
  medidor principal precisa de fato preencher (`style.width` diferente de
  vazio/0%); os 5 KPIs do topo continuam batendo com o banco a cada
  atualização futura (ver seção "Fixed (dados dinâmicos)" acima).

### Changed
- **Fim do ranking ordinal como produto público** (§13, 29/08/2026):
  `rank_mediano`/`rank_p5`/`rank_p95` saem de `data/indice.json` e migram
  para `data/robustez_mc.json` (selado e conferido pelo portão 2); o PDF
  estadual deixa de exibir posição; a Documentação do Índice ganha o anexo
  de robustez §5.8 (rank mediano sempre acompanhado do intervalo p5–p95 —
  recomendação da auditoria acatada na forma forte). Produto público por
  UF: nota, faixa interpretativa e confiança da verificação. Fundamento,
  precedente (ICM/SEDEC) e desambiguação do campo `confianca` no §13.
- `recalcular_mare.py`: `calcular()` devolve também a robustez MC; `--write`
  grava `data/robustez_mc.json`; `--check` confere 27×7 campos do índice
  E a reprodução integral da robustez.
- Manifesto de selagem passa a ser gerado por script versionado
  (`scripts/gerar_manifesto.py`), **incluindo os dois PDFs publicados** na
  selagem, com escopo declarado no cabeçalho do próprio manifesto (C7,
  saída forte do relatório). Ordem canônica: portões → PDFs → manifesto.

### Added
- Etapas semanais de `pip-audit` e `npm audit` na Action (informativas,
  `continue-on-error`; artefatos em `docs/*-audit-resultado.json`) — C4.
- Flag `--limpar` em `verificar_contribuicoes.py`: apaga
  `fila_contribuicoes/` ao final da triagem local (LGPD; obrigatória em
  execução fora do CI, documentada na docstring) — C5.
- Aviso de privacidade resumido junto ao campo de e-mail do formulário,
  remetendo a `docs/LGPD_PRIVACIDADE.md` e ao canal de exclusão — C6.
- `scripts/cobertura_docstrings.py`: critério de contagem fixado (toda
  FunctionDef/AsyncFunctionDef via AST); número publicado passa a ser
  produzido pelo script — C9. Cobertura elevada a **135/135 funções e 28/28
  módulos** (seis docstrings faltantes escritas e dois scripts novos já
  documentados nesta versão; conferir sempre pela saída do script).
- **Prazos federais e vigia de sinais** (METODOLOGIA §15, 29/08/2026):
  registro curado `data/marcos_prazos.json` (marcos legais da Lei
  14.750/2023, judiciais da ADPF 743 e técnicos), rotina
  `verificar_prazos_legais.py` (cruza marcos computáveis com o banco →
  `data/prazos_uf.json`; marcador editorial, nunca pontuação; `--simular`
  experimental como semente v3) e rotina `monitorar_sinais_federais.py`
  (vigia DOU + ADPF 743 → `data/pistas_sinais.json`, descoberta para
  triagem humana, nunca classificação; self-test offline com garantia
  estrutural de não-escrita nos arquivos curados). Ambas na Action
  semanal como etapas informativas. Pista de primeira ordem registrada
  para a fila humana: plano do PA homologado pelo STF com PA em LAC no
  banco; decisão de vocabulário ("autos judiciais públicos" como canal)
  reservada à editoria.
- **Regra do Distrito Federal** (METODOLOGIA §14, registro ex-ante de
  29/08/2026): fundamento jurídico verificado (Lei 12.608 art. 2º; CF
  arts. 32 §1º e 23; autodeclaração da SUBSIDEC/DF) de que o dever do DF
  é no mínimo o de um estado; regra do ato único declarada com o caso
  dormente (um instrumento distrital preencherá os dois componentes por
  acumulação constitucional de competências — não é dupla contagem);
  duas pistas de verificação registradas para a bateria do DF.
- `gerar_tese.js` inventariado em `docs/AUDITORIA_CODIGO.md` §2 e
  `DOCUMENTACAO_TECNICA.md` como ferramenta de sessão (dep. `docx` via
  `npm install --no-save`, deliberadamente fora de `package.json`) — C8.

### Security
- **Subresource Integrity nas 4 tags de CDN** (Chart.js 4.5.1, D3 7.9.0,
  jsPDF 2.5.1 ×2), com `crossorigin="anonymous"` e
  `referrerpolicy="no-referrer"` — C1. Hashes SHA-384 calculados pela
  auditoria de 29/08/2026 a partir dos arquivos servidos pelo CDN naquela
  data; **conferência obrigatória em prévia de navegador antes do deploy**
  (ambiente de edição sem acesso ao CDN; hash inválido quebra em silêncio
  no build, mas ruidosamente no console do navegador).
- Fontes do Google (Fraunces, Archivo, Archivo Narrow) **declaradas no SBOM**
  como dependência externa sem SRI possível (CSS varia por User-Agent) —
  C2, alternativa mínima do relatório; o self-host permanece recomendado e
  registrado como pendência de deploy (requer baixar os .woff2, sem acesso
  neste ambiente de edição).

### Changed (design)
- **Harmonização visual das 4 páginas** (31/08/2026, a partir do documento de
  marca pessoal de Patricia — "Futurismo Regenerativo", paleta Osso/Abissal/
  Areia/Argila/Sintético). Achado: o `index.html` já tinha recebido essa
  paleta; as outras 3 páginas (proteja-se, envie-dados, obrigado) ainda
  usavam um azul de sistema (#35566B) fora da família de cores, aplicado a
  botões, links, foco de acessibilidade e bordas de destaque. Substituído em
  todas as 4 páginas por `--link:#465D6E` (Sintético escurecido para 5,54:1
  de contraste sobre Osso, acima do mínimo AA de 4,5:1) para links/foco, e
  `var(--ink)` (Abissal) para botões de ação — mesmo padrão já usado no item
  ativo do menu. **Preservado sem alteração**: o gradiente terracota→azul do
  medidor 0–100 e toda a paleta de codificação de dados em mapas/gráficos
  (são codificação semântica de dado, não decoração). Também unificados os 3
  cartões de estatística neutros (14/27/27) em Abissal, mantendo terracota
  apenas nos 2 que representam lacunas (7 estados sem plano; 728 municípios),
  criando um sistema de duas cores com significado em vez de 5 tons soltos.
  Corrigido também: `obrigado.html` tinha versão desatualizada no rodapé
  (v2.1 → v2.2.3), logo do rodapé sem link clicável (inconsistente com as
  outras 3 páginas) e uma linha "Uma publicação Futura Evidence Lab"
  duplicada. Validado com screenshots reais (Playwright/Chromium headless)
  antes e depois, não apenas inspeção de código. Nenhuma mudança de dado ou
  cálculo — protocolo canônico completo rodado ao final, média nacional
  inalterada (47,1).

- **Segunda passada de harmonização, por inspeção de código** (a pedido de
  Patricia): `Chart.defaults.borderColor` usava um azul órfão (#24405F,
  nem o antigo #35566B nem a paleta nova) — trocado para o equivalente de
  `var(--ink)`. `Chart.defaults.color` (texto de todos os gráficos) usava um
  quarto tom escuro não documentado (#3D4A42) — trocado pelo mesmo tom de
  `--muted` já usado no resto do site. Os dois banners de erro (falha de
  rede/CDN) usavam `font-family:sans-serif` genérico em vez de Archivo —
  corrigido (e um erro de sintaxe JS que essa correção introduziu, por aspas
  simples aninhadas, foi pego pelo próprio portão de runtime e corrigido
  antes de seguir — exemplo do portão funcionando como pretendido). A
  legenda de faixas do índice ("Ponto de partida/Caminho aberto/Avanço
  consistente/Referência nacional") tinha uma cor terracota isolada
  (#B0724F) fora da paleta nomeada — trocada por #C69B72, já usada na mesma
  posição do gradiente do medidor 0–100. Mapas SVG (D3) já usavam Archivo
  Narrow corretamente — nenhuma mudança necessária ali.

### Added
- **Mapa de municípios prioritários** (METODOLOGIA §21, index.html, painel final
  antes do rodapé): distingue, entre os municípios do Cadastro Nacional de
  Municípios Suscetíveis (Nota Técnica 1/2025/SADJ-VI/SEPAC/CC/PR), quais já
  têm instrumento localizado e quais não. Lista nominal oficial (2.095
  municípios) exige login no MDR e não é acessível publicamente — o mapa usa
  proxy documentado (N municípios de maior população por UF, N = contagem
  oficial da UF), rotulado como tal na página. `data/cadastro_prioritarios.json`
  registra as contagens oficiais e a limitação. Computado inteiramente no
  navegador (sem novo fetch); MUN_LATLON retido como variável global.
  Validado no portão de runtime real: 2.095 pontos, batendo com o total oficial.

### Fixed (dados)
- **Busca municipal dirigida por população nas UFs mais prioritárias**
  (METODOLOGIA §21): Guarulhos, Campinas, São Gonçalo, São Bernardo do Campo,
  Duque de Caxias e Nova Iguaçu adicionados como "plano" (instrumentos reais,
  datados, fontes oficiais); Jaboatão dos Guararapes buscado e descartado (só
  ato de resposta localizado). Cobertura nominal 254→260. Média nacional
  46,8→46,9→**47,0**.
- **Segunda passada nas UFs em lacuna** (METODOLOGIA §20, 31/08/2026): PE
  LAC→ELAB (PEAR-PE, plano em elaboração desde 05/2025, conclusão prevista
  fim de 2026: 8,8→23,8); AP LAC→VIG (PPCDAP + Comitê de Estiagem/Incêndios,
  recorrentes que cobrem o risco projetado, mesma regra de recorrência
  ponderada do §18: 9,1→37,4). PB e RN mantidos LAC — bateria negativa
  confirmada pela 3ª vez independente. Média nacional 45,2 → **46,8**.
- **Bateria dirigida das 8 UFs em LAC via imprensa nacional** (METODOLOGIA §18,
  30/08/2026): quatro reclassificações — PA (LAC→READ, 5,7→34,1), AL (LAC→NOVO,
  13,5→53,5), SE (LAC→NOVO, 20,0→60,0) e **DF** (LAC→VIG, 13,3→38,3, **primeira
  aplicação real da Regra do DF do §14**: o mesmo instrumento credita instrumento
  estadual E cobertura populacional por acumulação constitucional de
  competências — `data/municipios.json`, registro Brasília, categoria
  `coberto_estadual`). Duas baterias negativas confirmadas e mantidas em LAC
  (PB, RN — "articulação" noticiada sem documento publicado não qualifica) mais
  a reconfirmação do padrão de AP (só ato de resposta). Achado metodológico
  central: o decreto do DF (48.599/2026) é **anual recorrente** (idêntico a
  2021/2023/2025) — classificado VIG/antecipação 40 (categoria "estrutura
  permanente/recorrente" da régua §5.2.1), não NOVO/antecipação 100, para não
  confundir papelada de calendário com antecipação dedicada ao ciclo. Média
  nacional 40,2 → 45,2 → 45,0 → **45,2** (duas rodadas de correção no mesmo
  dia, ambas por questionamento direto de Patricia: primeiro DF 40→30,
  alinhado cegamente a RJ/ES/MG/SP; depois a régua de recorrência passou a
  variar por cobertura do risco projetado — CONSIST=COBRE→40 [DF, SP],
  NEUTRO→30 [RJ, ES], DIFERE→20 [MG] — porque decreto recorrente pode
  refletir avaliação deliberada de suficiência, não ausência de reflexão;
  a régua §5.2.1 é atualizada para declarar a regra). Pendências declaradas: decretos exatos de AL e SE
  a confirmar em fonte primária. Todas as buscas em `data/log_buscas.json`.

### Added
- **Dicionário de busca consolidado** (`data/dicionario_busca.json`, METODOLOGIA
  §17): fonte única de verdade dos cinco grupos do vocabulário de recuperação
  (§4.1.1a), com origem e data por termo. `scripts/validar_dicionario.py`
  prova estrutura, precisão por regressão (contra os casos reais AC/AM/MS/PE
  do §16 — zero falsos positivos/negativos) e cobertura de variantes
  acento/hífen. O portão de natureza (`verificar_consistencia.py`) passou a
  importar `get_sinalizadores_resposta()` deste módulo, substituindo a regex
  solta anterior — fonte única entre documentação e código.
- **Vigia de imprensa nacional** (`monitorar_imprensa_regional.py`, §17):
  busca em portais de notícia via Google News RSS por instrumentos ainda não
  registrados, priorizada em três camadas (UFs LAC → capitais → demais
  estados em busca ampla), com cursor persistido para cobrir o universo ao
  longo das execuções semanais. **Trava absoluta de três camadas** contra
  entrada não autorizada no banco: estrutural (self-test veda qualquer
  escrita em estados.json/municipios.json/indice.json), de campo (toda
  pista nasce com `documento_oficial_confirmado: null` e `promovivel:
  false`, sem caminho de código que altere isso) e de processo (promoção
  exige passagem manual por `data/log_buscas.json`). Etapa informativa da
  Action, com limite alto (rede aberta lá; bloqueada no ambiente de edição,
  onde degrada graciosamente por design).

### Fixed
- **R1 da segunda auditoria (29/08/2026): PDFs bit-deterministicos.**
  `gerar_pdf_indice.py` e `gerar_pdf_metodologia.py` fixam
  `SOURCE_DATE_EPOCH` a partir da data de corte dos dados
  (`data/meta.json`), lida nativamente pelo reportlab ≥4 — os PDFs
  deixam de embutir metadados do relógio da máquina e passam a ser
  função determinística apenas dos dados publicados. Verificado: dois
  builds consecutivos produzem hash SHA-256 idêntico (controle
  positivo: alterar o conteúdo ainda muda o hash — o determinismo não
  mascara divergência real). `scripts/gerar_manifesto.py --check`
  passou a regenerar os dois PDFs e provar o determinismo a cada
  execução, antes de conferir o restante da selagem — validado por
  teste negativo real (fixador desativado propositalmente, guard
  acusou o hash divergente exato, restaurado). Resolve a limitação de
  auditabilidade identificada pela segunda auditoria: um auditor
  externo agora pode regenerar os PDFs e conferir a selagem sem
  precisar regravar o manifesto.
- `__pycache__/` removido do pacote publicado (vazamento de
  empacotamento — já coberto por `.gitignore`, mas escapava do `zip`
  manual); alinhado ao padrão de limpeza do restante do pacote.
- **Errata de dados — revisão de natureza dos instrumentos (METODOLOGIA
  §16, 29/08/2026)**: AC pontuava ato de resposta (Decreto 11.932,
  emergência SINPDEC) — base corrigida para o Decreto 11.899/Gabinete de
  Crise Hídrica (READ, antecipação 100): 58,0 → 69,6; AM (emergência
  climática preventiva, ex-ante sustentado) com data corrigida para
  01/06/2026: antecipação 60 → 100, 70,8 → 84,1 (nova maior nota); PE
  (Decreto 60.960 é Situação de Emergência SINPDEC) reclassificado LAC:
  58,8 → 8,8, com segunda rodada de bateria negativa obrigatória
  pré-publicação; MS e PA sustentados. Média nacional 41,1 → 40,2.
  Buscas e decisões em data/log_buscas.json; figuras, tabela
  risco×instrumento e gauge sincronizados (portão de figuras acusou e
  guiou cada superfície).
- **Portão de natureza dos instrumentos** em `verificar_consistencia.py`
  (bloqueante): campo `natureza_doc` obrigatório em `data/estados.json`,
  status pontuável exige natureza ex-ante, léxico de emergência exige
  `justificativa_ex_ante` (teste do objeto declarado). Validado por
  teste negativo real (quebra proposital acusada e restaurada).
- Portão de runtime (`scripts/verificar_runtime.js`) passou a escutar
  `unhandledrejection` — a classe exata do bug do `timelineData` órfão.
  Validado por teste negativo em 29/08/2026: `ReferenceError` assíncrono
  proposital acusado com mensagem e linha exatas (dupla cobertura: listener
  + crash ruidoso do Node ≥15), depois restaurado com portão verde — C3.
- Divergência de contagem de docstrings (85/87 declarado × 85/91 medido
  pela auditoria) resolvida na raiz: o critério agora é o do script — C9.

## [2.2.2] — em publicação (corte de dados 26/08/2026)

Natureza da versão: expansão metodológica sem alteração do motor de
cálculo — os 270 campos do índice publicado são idênticos, campo a campo,
ao início e ao fim de toda a série de mudanças abaixo (verificado pelo
portão `recalcular_mare.py --check` a cada etapa). Média nacional
corrente: **41,1/100**.

### Added
- Ancoragem da avaliação risco×instrumento na **COBRADE** (Classificação e
  Codificação Brasileira de Desastres), substituindo a hierarquia editorial
  anterior por taxonomia oficial citável (grupo Seca 1.4.1 e códigos).
- **Vigência automática** dos decretos (`verificar_vigencia.py`): parser de
  datas brasileiras imperfeitas, campo `vigencia` (ativo / prazo típico
  vencido / indeterminada), roda em toda atualização, nunca expira registro
  por conta própria.
- **Governança automatizada de julgamento**: seis regras objetivas
  (`processar_contribuicoes.py`, R1-R6) que roteiam contribuições do
  formulário para conversão automática, fila editorial ou recusa, com a
  reserva de julgamento humano para planos e capitais (R7).
- **Leitura de conteúdo dos decretos** (`analisar_decretos.py`): três
  dicionários versionados (desregulação, proteção, antecipação com
  limiares observacionais) que geram marcador editorial, nunca pontuação.
- **Refinamento do teste do objeto para fenômenos de instalação lenta**:
  o critério de gatilho antecipatório passou a aceitar limiar em índice
  observacional oficial (Monitor de Secas, avisos Inmet por cor, Risco de
  Fogo/INPE), além do gatilho de previsão original, generalizado às três
  famílias COBRADE do ciclo.
- **Reconhecimento editorial do financiamento preventivo estadual** (o
  caso Prepara RS/RS): visível no card do estado e no relatório em PDF,
  explicitamente não pontuado nesta versão, com a bateria negativa de
  financiamento construída (`buscar_financiamento_preventivo.py` +
  `data/financiamento_uf.json`) como pré-requisito da promoção a
  subcritério na v3.
- **Registro comparado de cinco desenhos institucionais** internacionais
  para ação mais rápida em desastres, como elementos para o debate
  público (cláusula de neutralidade explícita).
- **Portão de consistência de figuras** (seção 8 de
  `verificar_consistencia.py`): todo mapa e gráfico do site é conferido
  contra os dados e a classificação canônica a cada execução; validado por
  teste negativo documentado.
- Campo de **espécie jurídica** (`especie`: lei, decreto, portaria,
  resolução) no registro municipal.
- Integração da **API do Querido Diário** ao pipeline (descoberta de
  pistas, nunca classificação automática).
- Este pacote de auditoria: `CHANGELOG.md`, `LICENSE`,
  `.env.example`, `package.json`, `netlify.toml`,
  `docs/LGPD_PRIVACIDADE.md`, `docs/SBOM.md` (+ CycloneDX JSON),
  cobertura de docstrings de função em 85 das 87 funções do código Python.

### Changed
- **Reestruturação populacional**: os antigos componentes "capital" e
  "cobertura municipal" foram fundidos num único componente de cobertura
  populacional ponderado pelo Censo 2022 (`atualizar_populacao.py`, com
  três validações bloqueantes).
- **Faixas interpretativas renomeadas pela terceira vez** (cortes
  numéricos intocados): de "inicial/em desenvolvimento/em
  consolidação/avançado" para "ponto de partida/caminho aberto/avanço
  consistente/referência nacional" — decisão editorial de convite à
  publicação; histórico completo das três nomenclaturas preservado em
  `METODOLOGIA.md` para auditoria.
- Vocabulário do índice corrigido de "resposta institucional" (fóssil
  contraditório com a Correção B) para "arcabouço público da preparação"
  em todas as superfícies (site, PDFs, metodologia).
- Seção "Financiamento e transferências" do site reconstruída no padrão
  visual das demais seções (grade `charts-grid`), com as figuras 3 e 4
  fundidas em um único mapa interativo (faixa por hover).
- `requirements.txt`: versões travadas em vez de faixas `>=`, para
  reprodutibilidade auditável (ver `docs/SBOM.md`).

### Fixed
- Bug crítico de runtime: remoção de uma figura deixou `timelineData`
  órfã, consumida ainda pela faixa temporal do herói; o `ReferenceError`
  era engolido pelo fluxo assíncrono do carregador, derrubando
  silenciosamente tudo que vinha depois no script (mapa de transferências
  sem círculos, card de consulta incompleto). Localizado por bisseção com
  marcadores no DOM; corrigido religando a faixa aos dados vivos.
- Contagem fóssil de municípios ("165") no `aria-label` do mapa de pontos,
  desatualizada desde antes do banco chegar a 254 registros.
- Duplicata da integração do Querido Diário (criada em tentativa anterior
  da mesma sessão), detectada por discrepância de nomes e unificada.

### Removed
- Figura da timeline de reatividade (redundante com a faixa temporal do
  herói após a reconstrução).
- Gráfico de barras de faixas de repasse do Prepara RS (informação
  absorvida pelo mapa de transferências, que já mostra faixa e valor por
  hover).

## [2.2.1] e anteriores

Resumo; ver `METODOLOGIA.md` §12 para a narrativa completa, incluindo o
teste de estresse formal (27 decretos simulados simultaneamente, deslocamento
aceito apenas se exatamente zero) que validou cada correção abaixo.

- **Correção B** (26/08/2026) — exclusão integral dos atos de resposta da
  pontuação em todos os componentes; decreto permanece no banco como
  registro de transparência, nunca pontua. Efeito medido: média nacional
  47,5 → 46,2, com o maior deslocamento concentrado em quatro estados cuja
  cobertura dependia fortemente de decreto.
- **Nomenclatura MARÉ finalizada** (25/08/2026) — histórico: IPEN
  (descartado por colisão com o Instituto de Pesquisas Energéticas e
  Nucleares) → IPREN (provisório) → MARÉ (definitivo).
- **Protocolo declarado × documentado** — desconto de 50% sobre o crédito
  de cobertura declarada a órgão de controle sem documento localizado.
- Índice original (v2.1): três componentes distintos (instrumento
  estadual, capital, cobertura municipal), primeira nomenclatura de faixas
  (crítico/insuficiente/parcial/avançado).

## Roadmap declarado

- **v2.3** (versão maior; altera pontuação): fator de alinhamento
  risco-plano com confiabilidade inter-avaliadores (κ de
  Cohen/Krippendorff) — condicionado a κ ≥ 0,6-0,7; população real na
  camada declarada, usando as listas nominais de PR/SC/RS; anexo
  comparativo MARÉ×ICM.
- **v3**: promoção do instrumento de financiamento preventivo a
  subcritério do componente de instrumento estadual, condicionada à
  bateria negativa completa nas 27 UFs.

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
