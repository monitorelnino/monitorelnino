# Changelog · Monitor El Niño Brasil / Índice MARÉ

Formato inspirado em [Keep a Changelog](https://keepachangelog.com/pt-BR/).
Cada entrada aqui é um resumo escaneável; a justificativa completa, com
fundamentação teórica e dados de impacto, vive em `METODOLOGIA.md` (a fonte
de verdade), datada seção a seção. Convenção deste projeto: mudança que
altera pesos, créditos ou componentes do índice exige **versão maior**
(regra de governança registrada em `METODOLOGIA.md` §12); expansão de
documentação, novos portões de verificação e reconhecimentos editoriais
não pontuados permanecem na versão corrente.

## [2.2.4] — em publicação (sessão de construção de 02/09/2026; corte de dados 31/08/2026; média nacional 47,1 inalterada)

### PR-E — Metodologia, protocolo, guia e versão v2.2.4 (02/09/2026)
- **METODOLOGIA.md**: seções novas §24 (defeso: fatos, consequências, regra C6,
  memória E8), §25 (níveis de verificação e "não verificado"), §26 (fontes
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
- **Decisão editorial E8 (02/09/2026):** a nota do defeso é PERMANENTE — após
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
