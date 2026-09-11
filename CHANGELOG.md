# Changelog · Monitor El Niño Brasil / Índice MARÉ

Formato inspirado em [Keep a Changelog](https://keepachangelog.com/pt-BR/).
Cada entrada aqui é um resumo escaneável; a justificativa completa, com
fundamentação teórica e dados de impacto, vive em `METODOLOGIA.md` (a fonte
de verdade), datada seção a seção. Convenção deste projeto: mudança que
altera pesos, créditos ou componentes do índice exige **versão maior**
(regra de governança registrada em `METODOLOGIA.md` §12); expansão de
documentação, novos portões de verificação e reconhecimentos editoriais
não pontuados permanecem na versão corrente.

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
