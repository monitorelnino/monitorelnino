# Documentação Técnica — Monitor El Niño Brasil

**Público-alvo:** auditores externos, revisores técnicos e futuros mantenedores. Este documento descreve como o código funciona e como reproduzir, do zero, cada número publicado. Ele complementa — e nunca substitui — dois documentos irmãos: o **METODOLOGIA.md** (o *porquê* de cada regra: fundamentos, calibrações, errata) e o **README.md** (guia editorial: como publicar e como editar dados). Regra de leitura: se este documento e o código divergirem, **o código é a verdade** e a divergência é um defeito a reportar; se este documento e o METODOLOGIA.md divergirem sobre uma regra, o METODOLOGIA.md prevalece.

Versão de referência: pacote de 27/08/2026, metodologia MARÉ v2.3 (reestruturação populacional; régua de antecipação formalizada — §5.2.1, sem mudança numérica) com Correção B, corte de dados 26/08/2026.

---

## 1. Arquitetura em uma página

A plataforma é um **site estático sem backend e sem banco de dados próprio**. Três decisões estruturais explicam tudo o mais:

**(i) JSON versionado como contrato e como registro público.** Os dez arquivos em `data/` são simultaneamente a fonte que o site consome em tempo real (via `fetch`) e o registro auditável da edição: todo dado publicado tem um commit, uma data e um diff. Não existe estado publicado fora do Git.

**(ii) Estado transitório vive em sistemas de terceiros, nunca no repositório.** Submissões de leitores ficam nos servidores do Netlify Forms (puxadas por API); dados de financiamento vêm da API do Portal da Transparência; boletins, do Painel El Niño. O repositório só recebe o retrato destilado, datado e despersonalizado — a fila humana local (`fila_contribuicoes/`) está no `.gitignore` por conter e-mails de contato.

**(iii) Nada publica sem passar por quatro portões bloqueantes.** Toda mutação de dados — automática ou humana — converge para o mesmo funil: recálculo canônico → verificação de estrutura → verificação de consistência → verificação de runtime. Falha em qualquer portão interrompe o job de CI antes do commit; o estado publicado anterior permanece intacto.

Linguagens: Python 3.12 (pipeline; única dependência de cálculo é NumPy), JavaScript em dois papéis (D3.js no navegador; Node+jsdom nos portões de teste), HTML/CSS sem framework, YAML (CI) e JSON (dados).

---

## 2. Inventário de arquivos

### 2.1 Páginas (4)
| Arquivo | Papel |
|---|---|
| `index.html` | Página principal: gauge do MARÉ, 5 mapas D3, tabela de auditoria (248 linhas), consulta municipal, detalhe por estado com relatório PDF próprio (gerarPDFEstado: veredito+faixa, componentes, capital, cobertura, cobranças), consulta com população Censo 2022 e relatório PDF municipal (gerarPDF, via card). `proteja-se.html`: guia exportável em PDF (gerarPDFGuia, mesma identidade) + quadro de descoberta dos três relatórios. Busca `data/*.json` em runtime (10 arquivos, incl. populacao_censo2022). O único valor de dados fixo no HTML é o veredito do herói (`gaugeNum`/`data-alvo`), cuja paridade com a média recomputada é imposta pelo portão de consistência (§8). |
| `proteja-se.html` | Orientação à população por risco e o diretório "Quem chamar" (27 UFs). |
| `envie-dados.html` | Formulário de contribuição (Netlify Forms, `data-netlify="true"`). A constante `ehProducao` só ativa o envio real em `monitorelnino.com.br` e `*.netlify.app`. |
| `obrigado.html` | Confirmação pós-envio. |

### 2.2 Dados (`data/`, 10 arquivos)
| Arquivo | Forma | Conteúdo |
|---|---|---|
| `municipios.json` | lista, 248 itens | Registros municipais verificados. Campos: `nome, uf, categoria, documento, data, fonte, url, canal, lat, lon`. `categoria` pertence ao vocabulário controlado de 7 valores (README §Vocabulário); `canal` ao vocabulário de canais. |
| `pontos_mapa.json` | lista, 248 itens | Projeção cartográfica de `municipios.json`: `nome, uf, categoria, lat, lon, fase`. Mantido em paridade 1:1 pelo portão de consistência. |
| `indice.json` | objeto, 27 UFs | O MARÉ. Por UF: `estado, cobertura_pop, antecipacao` (componentes v2.2), `total` (média linear), `total_geo` (geométrica piso 5), `rank_mediano, rank_p5, rank_p95` (Monte Carlo), `confianca, status_estadual, metodo`. **Arquivo derivado: nunca editar à mão** — regravado exclusivamente por `recalcular_mare.py --write`. |
| `percentual_uf.json` | objeto, 27 UFs | Estatística de cobertura bruta: `total, com_ato, pct, n_plano, n_decreto` — **derivados** da mesma contagem do índice (fonte única, §5.3) — mais os campos de levantamento externo preservados: `declarado_plano, declarado_antigo, fonte_declarada`. |
| `estados.json` | objeto | `regions` (5 regiões) e `ufs` (27 itens: `uf, nome, regiao, status, orgao, doc, data, capital`). |
| `transferencias.json` | objeto | `meta`, `programas`, `repasses_rs` (lista geocodificada: `municipio, uf, valor, faixa, lat, lon`; soma conferida pelo portão), `fontes_monitoramento`. |
| `municipios_ibge_referencia.json` | lista, 5.571 | Malha oficial IBGE: os 5.570 municípios do Censo 2022 (Fernando de Noronha/PE incluído) + Boa Esperança do Norte/MT (instalado em 2025, pós-Censo; peso populacional 0 — METODOLOGIA §12.4.3). Denominadores e coordenadas oficiais; casamento de nomes é exato pela grafia oficial IBGE (o motor falha em não-casamento). |
| `geo_uf.json` | objeto | Geometria das 27 UFs para os mapas. Não editar. |
| `meta.json` | objeto | `corte` (data dos dados) e `atualizado_em` (última execução). |
| `boletins.json` | objeto | `ultimo_boletim` — sentinela do vigia de boletins do Painel El Niño. |

### 2.3 Pipeline Python (raiz, 15 scripts) e portões JS (`scripts/`)
| Script | Papel | Muda dados publicados? |
|---|---|---|
| `atualizar.py` | Orquestrador da atualização semanal (ordem completa no §6). | indireto (meta.json) |
| `recalcular_mare.py` | **Motor canônico do índice** (§5). `--check` reproduz e compara; `--write` regrava `indice.json` + `percentual_uf.json`. | sim (`--write`) |
| `processar_contribuicoes.py` | Triagem automática de contribuições, regras R1–R7 (§7.2). | sim, restrito |
| `verificar_contribuicoes.py` | Gera a fila humana local (`fila_contribuicoes/`) a partir do Netlify. | não |
| `converter_contribuicao.py` | Converte item aprovado da fila humana para `data/instrumentos_revisar.json` (categoria = decisão humana obrigatória, `--categoria`). | não (só a fila de revisão) |
| `aplicar_revisao.py` | Aplica `instrumentos_revisar.json` ao banco, recalcula (`--write`) e roda os portões. Ponto único de aplicação humana. | sim |
| `atualizar_instrumentos_estaduais.py` | Camada 1 do Protocolo de Busca: varre repositórios estaduais estruturados. **Nunca escreve no banco** — só propõe em `instrumentos_revisar.json`. | não |
| `atualizar_transferencias.py` | API do Portal da Transparência (requer `PORTAL_TRANSPARENCIA_API_KEY`; rate limiter 60/min; trata HTTP 429). | sim (transferencias.json) |
| `atualizar_boletins.py` | Vigia de novos boletins (tolerante a falha de rede). | sim (boletins.json) |
| `buscar_querido_diario.py` | Descoberta (camada 2) via API do Querido Diário/OKBR: varre capitais (ou `--uf XX`) × dicionário de recuperação e deposita candidatos com trecho+URL do diário na fila humana; três salvaguardas na docstring; falha-suave. | sim (instrumentos_revisar.json, log_querido_diario.json) |
| `atualizar_populacao.py` | Censo 2022 IBGE com validação dual-apuração (5.570 exatos; 5 sentinelas casando TODAS com uma mesma apuração oficial; total EXATO dessa apuração). Arquivo vigente: 1ª apuração (CD2022, planilha oficial IBGE), ingerida por `--de-arquivo` em 27/08/2026; em produção o SIDRA serve a 2ª apuração e o arquivo se atualiza sob o mesmo contrato. `--check` revalida. | sim (data/populacao_censo2022.json — NO PACOTE, validado) |
| `atualizar_marcos_severidade.py` | Motor das 3 zonas (§12.3 da Metodologia) + descoberta CKAN/ANA. `marcos_severidade.json` **ainda não é consumido pelo índice** (integração §12.5 é futura). Self-test embutido: 24 casos. | não (arquivo ainda não consumido) |
| `analise_sensibilidade.py` | Bateria reproduzível da auditoria de robustez do índice (§5 do PDF do índice): agregação, piso, descontos, esquemas de peso, contribuição efetiva, camadas, Monte Carlo, bordas. Primeira execução: auditoria de 27/08/2026. | não |
| `consultar_querido_diario.py` | Camada 2 automatizada: API pública do Querido Diário (OKBR) → pistas p/ fila humana; testa cobertura antes de interpretar; nunca escreve no banco (R7) | sim (data/pistas_querido_diario.json) |
| `verificar_vigencia.py` | Ciclo de vida dos atos: sinaliza decretos acima de 180d e datas ilegíveis p/ julgamento humano; nunca expira sozinho (melhoria PPI 27/08) | sim (data/vigencia_revisar.json) |
| `analisar_decretos.py` | Leitura de conteúdo dos decretos (§4.1.4): varre textos por dicionários de desregulação/proteção → fila humana; marcador editorial, jamais pontuação | sim (data/decretos_conteudo_revisar.json) |
| `gerar_pdf_metodologia.py` | Renderiza METODOLOGIA.pdf do METODOLOGIA.md vivo (substitui o antigo gerar_pdf_puro.py, ausente do repositório — A8 encerrado em 27/08/2026); regenerado pela Action a cada execução | sim (METODOLOGIA.pdf) |
| `gerar_pdf_indice.py` | Gera `MARE_Indice_Documentacao.pdf` **computando todos os números ao vivo** de `data/` + `analise_sensibilidade.py` — o PDF do índice não contém valor digitado à mão e não pode divergir da base. Roda também na Action semanal, após os portões: o PDF publicado se regenera sozinho a cada atualização de dados. | não |
| `verificar_consistencia.py` | Portão 2 — invariantes dos dados (§8). | não |
| `verificar_links.py` | Auditoria de URLs do banco (paralela, `concurrent.futures`). | não |
| `scripts/verificar_estrutura.js` | Portão 1 — árvore HTML das 4 páginas (jsdom). | não |
| `scripts/verificar_runtime.js` | Portão 4 — site executado em navegador simulado: 12 checagens (mapas, tabela, seletor, tooltip). | não |
| `scripts/sincronizar_single_file.py` | Utilitário da prévia single-file de revisão em chat — **fora do pacote publicado**; nunca roda em CI. | não |
| `gerar_tese.js` | Ferramenta de sessão: gera o DOCX da tese a partir do código vivo (dep. `docx` via `npm install --no-save docx`) — fora do pipeline, da selagem e do CI (C8). | não |

### 2.4 CI e configuração
`.github/workflows/atualizar.yml` (cron segundas 09:00 UTC + disparo manual) · `requirements.txt` (`requests`, `numpy`, `openpyxl`, `reportlab`) · `.gitignore` (inclui `fila_contribuicoes/` — dados pessoais nunca entram no Git).

---

## 3. Fluxo de dados (visão de conjunto)

```
 Leitores ──formulário──▶ Netlify Forms ──API──▶ processar_contribuicoes (R1–R7)
                                          │            │ decreto ñ-capital: escreve + recalcula
                                          │            └ plano/capital: fica p/ fila humana
                                          └──API──▶ verificar_contribuicoes ─▶ fila_contribuicoes/ (local)
                                                       └ humano ─▶ converter_contribuicao ─▶ instrumentos_revisar.json
 Repositórios estaduais ─▶ atualizar_instrumentos_estaduais ─▶ instrumentos_revisar.json ─┐
                                                                                          ▼
                                                                            aplicar_revisao (humano)
                                                                                          │
 Portal Transparência ─▶ atualizar_transferencias ─▶ transferencias.json                  ▼
 Painel El Niño ───────▶ atualizar_boletins ───────▶ boletins.json          municipios/pontos_mapa.json
                                                                                          │
                                              recalcular_mare --write ◀───────────────────┘
                                                        │
                                     indice.json + percentual_uf.json (derivados)
                                                        │
                            PORTÕES 1–4 (estrutura · consistência · --check · runtime)
                                                        │ todos verdes
                                              git commit data/ ─▶ site publicado (fetch em runtime)
```

Invariante central: **todo caminho que muda `municipios.json` termina em `recalcular_mare.py --write` seguido dos quatro portões** — seja o caminho automático (contribuição neutra), seja o humano (`aplicar_revisao.py`).

---

## 4. Convenções transversais

- **Casamento de nomes:** `norm()` (NFD → ASCII → caixa única → espaços colapsados) contra a malha IBGE; casamento é exato-normalizado. Nome que não casa é recusado, nunca aproximado — a grafia oficial do IBGE é a que entra no banco.
- **Datas:** `DD/MM/AAAA` em todos os campos de dados.
- **Ausência ≠ negação:** `nao_localizado` registra "verificado e não encontrado em fonte pública", com data; jamais "o município não tem".
- **Vocabulários controlados:** `categoria` (7 valores) e `canal` são fechados; valor fora do vocabulário é defeito (o portão de runtime já bloqueou um caso real: `site_prefeitura` vs `site_municipal`).
- **Tolerância a falha externa ≠ silêncio:** etapas de rede não-bloqueantes que falham são reportadas como "verificação INCOMPLETA nesta rodada", nunca como "sem novidades".

---

## 5. O motor de cálculo (`recalcular_mare.py`)

### 5.1 Constantes normativas (mapeamento código ↔ metodologia)
| Constante | Valores | Metodologia |
|---|---|---|
| `PESO_DOC` | `plano: 1,0 · plano_antigo: 0,7` — **decreto ausente por regra estrutural** (Correção B): `k in PESO_DOC` exclui decreto de peso, contagem documentada e excedente de agregado em todos os pontos, sem lista de exceções | §5.3, §12.4.1 |
| `ESTADO_SCORE` | `NOVO 100 · READ 65 · VIG 45 · ELAB 35 · LAC 0` | §5.1 |
| `CAP_SCORE` | `plano 100 · plano_antigo 60 · plano_elaboracao 45 · coberto_estadual 30 · nao_el_nino 10 · nao_localizado 0` (categoria fora da tabela — ex.: decreto — vale 0) | §5.2 |
| `AGREGADOS` | `RO: (38, "plano")` — agregados tipo decreto (PB 146, RN 166) excluídos pela Correção B; seguem no banco e em `percentual_uf.json` como transparência | §5.3, §12.4.1 |
| `ESTADOS` | 27 triplas `(status, antecipação, confiança)` — insumos de julgamento da verificação, datados no Livro-Razão | §5.1–§5.4 |

### 5.2 Cadeia de cálculo, por função
1. `calcular()` carrega o Censo validado, junta banco↔malha pela grafia oficial (falha em não-casamento), computa população e mediana por UF, conta registros por UF×categoria e identifica a categoria da capital (exibição editorial).
2. **Cobertura populacional (v2.2):** `w = Σ pop_mun·CRED_POP[cat]` `+ excedente_agregado()·mediana_UF·CRED_POP[tipo]` `+ max(declarado_plano − documentados, 0)·mediana_UF·0,5 + declarado_antigo·mediana_UF·0,3`; `cobertura_pop = min(100, 100·w/pop_UF)`. CRED_POP: plano 1,0 · plano_antigo 0,6 · plano_elaboracao 0,45 · coberto_estadual 0,3 · nao_localizado 0 · nao_el_nino 0 (desvio declarado; METODOLOGIA §12.4.3).
3. `excedente_agregado(uf, contagem)` desconta do agregado apenas os municípios já nomeados **da mesma categoria** do agregado (o termo cruzado decreto×plano foi removido pela Correção B — defeito exposto pelo teste de estresse §12.1, ver §9).
4. `derivar_percentual_uf()` deriva `total/com_ato/n_plano/n_decreto/pct` **da mesma contagem** usada no escore (fonte única — as duas métricas não podem divergir), preservando os campos de levantamento externo (`declarado_*`, `fonte_declarada`) que não são deriváveis.
5. **Agregações:** `total` = média aritmética dos 3 componentes; `total_geo` = `exp(mean(log(max(componente, 5))))` — piso 5 resolve o problema clássico do zero na média geométrica.
6. **Incerteza:** 10.000 vetores de pesos ~ Dirichlet(1,1,1), **semente fixa 42** (`np.random.default_rng(42)` — o Monte Carlo é determinístico e reproduzível bit a bit); `rank_mediano/p5/p95` derivam da distribuição de posições.
7. `--check` recomputa tudo e compara com `indice.json` campo a campo (27×10), devolvendo código ≠ 0 em divergência; `--write` regrava `indice.json` **e** `percentual_uf.json`.

---

## 6. A atualização semanal (`atualizar.py` via `.github/workflows/atualizar.yml`)

Ordem exata e caráter de cada etapa:

1. `pip install -r requirements.txt` e `npm install jsdom d3@7` — Node vem **antes** do Python de propósito: os portões JS são chamados de dentro de `atualizar.py`.
2. **População Censo 2022** — primeira execução busca e valida (3 validações bloqueantes); nas seguintes, `--check` revalida. Falha para o job: o índice nunca incorpora componente populacional não confirmado.
3. **`processar_contribuicoes.py`** — triagem R1–R7 (§7.2). Sem os secrets do Netlify, avisa e segue.
4. **`atualizar.py`**, que executa em sequência: `atualizar_boletins.py` (tolerante a falha) → `verificar_contribuicoes.py` → descarte de proposta antiga e `atualizar_instrumentos_estaduais.py` (não-bloqueante, mas falha = "verificação INCOMPLETA", visível no log) → `atualizar_transferencias.py` (se houver chave) → **os quatro portões, bloqueantes** (§8) → carimbo de `meta.json` (e novo `corte` se as transferências mudaram, detectado por hash SHA-256).
5. Aviso `::warning::` se `instrumentos_revisar.json` tem propostas aguardando revisão humana (nunca aplicadas automaticamente).
6. **Regeneração do PDF do índice** (`gerar_pdf_indice.py`) — depois dos portões, o artefato público de documentação do cálculo é recomputado dos dados vigentes.
7. `git add data/ MARE_Indice_Documentacao.pdf` + commit + push — escopo do commit automático: os dados e o único artefato de documentação computado deles. Páginas, scripts e metodologia seguem fora do alcance da automação.

---

## 7. Canais de entrada de dados

### 7.1 Descoberta automática (Camada 1)
`atualizar_instrumentos_estaduais.py` varre repositórios estaduais estruturados (SISDC-PR e equivalentes) por município novo/atualizado e **apenas propõe** em `instrumentos_revisar.json`. Aplicação é sempre humana, via `aplicar_revisao.py`, que mescla, recalcula e roda os portões.

### 7.2 Contribuições de leitores — regras R1–R7 (`processar_contribuicoes.py`)
| Regra | Critério | Destino em falha |
|---|---|---|
| R1 | Campos completos; UF real; URL `https://` | recusa (log) |
| R2 | Município casa exato-normalizado com a malha IBGE | recusa |
| R3 | Tipo automatizável: `plano` ou `decreto` (demais: análise editorial) | recusa |
| **R7** | **Reserva de julgamento humano (27/08/2026):** tipo `plano` (move o índice) ou município-capital (o maior município da UF — a maior alavanca populacional individual da cobertura, v2.2) **nunca** são auto-aplicados; manutenção de nao_localizado/LAC de alto impacto exige bateria negativa registrada (METODOLOGIA §4.1.2). Funil de contribuições: 7 tipos no formulário; plano/decreto seguem os caminhos existentes (R7/auto); demais tipos RESERVADOS à fila humana (R3 corrigida 27/08 — antes recusa terminal); categoria final sempre por --categoria humano; erro de tipo do usuário é inócuo por desenho. Anatomia da divergência Talanoa×MARÉ documentada na METODOLOGIA (5 eixos + crosswalk das taxonomias + predições falseáveis). Canal de pistas por sessão: Monitor do El Niño (Talanoa/PPI) — conciliação registro a registro obrigatória pré-publicação; íntegras Portaria 260/2022 + 3.646/2022 na mesma fila. Fila de campo da próxima rodada: bateria dos 54 entes + extração das listas nominais PR/SC/RS + leitura de conteúdo dos 92 decretos do banco (sinal do ato, §4.1.4) + conciliação registro a registro com o Monitor do El Niño (PPI/Talanoa) + síntese editorial semanal na Action (recall §4.1.1d-iii; habilita população real na camada declarada em v2.3) | **reservada** — sem marcação; permanece visível na fila humana até julgamento |
| R4 | Domínio oficial: `*.gov.br/.leg.br/.jus.br/.mp.br/.def.br` ou Diário consorciado | recusa |
| R5 | Documento acessível (HTTP 200) e coerente: menciona o município e contém vocabulário do tipo declarado | recusa |
| R6 | Não-regressão: registro existente igual ou mais forte (`FORCA`) barra o envio | recusa |

Consequência estrutural da R7: **o caminho automático fica restrito, por construção, a decretos de não-capitais** — registros de transparência que, pela Correção B, não pontuam em componente algum. Após qualquer aplicação, o script roda `recalcular_mare.py --write` (regravando o `percentual_uf.json` derivado) e os portões conferem que a média nacional exibida no site permaneceu idêntica — **prova mecânica, a cada rodada, de que o caminho automático segue neutro ao escore**; regressão futura trava a publicação inteira. Recusas ficam em `data/contribuicoes_recusadas.json` (motivo, sem dados pessoais); IDs processados em `data/contribuicoes_processadas.json` (idempotência). Itens reservados pela R7 não recebem marcação: reaparecem a cada rodada até o julgamento humano e, uma vez aplicados via `aplicar_revisao.py`, a R6 os encerra como duplicata.

### 7.3 Fluxo humano
`verificar_contribuicoes.py` (fila local com checklist `.md`) → decisão de categoria **sempre humana**, após leitura do documento (`converter_contribuicao.py --categoria`, sem valor padrão, por regra de ouro) → `aplicar_revisao.py` (mescla + `--write` + portões). Canal A (descoberta automática) e Canal B (leitores) convergem para o mesmo ponto único de aplicação.

---

## 8. Os quatro portões (todos bloqueantes; falha = nada publica)

| # | Comando | O que prova |
|---|---|---|
| 1 | `node scripts/verificar_estrutura.js` | Árvore HTML íntegra, contêineres/masthead/rodapé consistentes nas 4 páginas; tags balanceadas. |
| 2 | `python3 verificar_consistencia.py` | Invariantes dos dados: paridade `municipios`↔`pontos_mapa` (248↔248); `percentual_uf` idêntico ao derivado da base (mesma função do motor — fonte única); `total` de cada UF = média dos 3 componentes; soma dos repasses RS = 32.300.000 e todos geocodificados; **veredito do herói (`gaugeNum`) = média nacional recomputada**; ausência de nomes de projeto antigos; termos obrigatórios no README. |
| 3 | `python3 recalcular_mare.py --check` | Os 27×10 campos de `indice.json` reproduzem-se exatamente a partir dos dados brutos (média nacional 40,7). |
| 4 | `node scripts/verificar_runtime.js` | O site executa num navegador simulado (jsdom+D3): zero erros de runtime; 5 mapas com as contagens corretas; tabela de 248 linhas; seletor, consulta municipal, detalhe de estado e tooltips funcionais. |

---

## 9. Testes adversariais e self-tests

- **Teste de estresse §12.1 (critério de aceitação da Correção B):** 27 decretos simulados, um por UF, devem deslocar o MARÉ em **exatamente zero décimos**. A primeira execução real deste teste (26/08/2026) expôs o termo cruzado residual em `excedente_agregado()`; corrigido, o teste passa com Δ = 0 em todas as casas decimais. Reexecutado de forma independente na auditoria de 27/08/2026 (implementação própria do auditor): mesmo resultado.
- **Self-test do motor de zonas** (`atualizar_marcos_severidade.py`): 24 casos — as três zonas, a guarda legal "decreto é SEMPRE resposta, independentemente de datas" (IN MDR nº 2/2016; casos adversariais: decreto anterior ao monitor; decreto sem marco algum), as quatro escalas de patamar, a navegação CKAN contra fixture local, e a guarda de contrato "não-decreto sem data levanta `ValueError` nomeado".
- **Teste funcional R1–R7** (auditoria 27/08/2026): quatro submissões sintéticas com Netlify e rede simulados — plano→reservada; capital→reservada; decreto não-capital→aprovada com índice provadamente idêntico e portões verdes na base mutada; domínio não-oficial→recusada R4.
- **Validações-sentinela de população** (`atualizar_populacao.py`): contagem exata de municípios, total nacional ±0,1%, cinco municípios nominais conferidos valor a valor — o desenho existe porque a primeira fonte candidata (projeções RIPSA rotuladas "2022") foi **rejeitada** por essas mesmas sentinelas.

---

## 10. Roteiro de reprodução para auditoria independente

Requisitos: Python 3.12+, Node 20+. Na raiz do pacote:

```bash
pip install -r requirements.txt
npm install --no-save jsdom d3@7

# 1. O índice publicado reproduz-se a partir dos dados brutos?
python3 recalcular_mare.py --check
#   esperado: "✓ MARÉ REPRODUZIDO — 27 estados × 11 campos idênticos · média nacional 45.7"

# 2. Invariantes dos dados
python3 verificar_consistencia.py
#   esperado: "✓ CONSISTENTE" (o aviso sobre "prévia single-file" é normal fora da sessão de edição)

# 3. Estrutura e runtime do site
node scripts/verificar_estrutura.js     # esperado: "✓ ESTRUTURA OK ... 4 página(s)"
node scripts/verificar_runtime.js       # esperado: "✓ RUNTIME OK" com 12 checagens

# 4. Self-test do motor de zonas (24 casos)
python3 - <<'PY'
import importlib.util, sys
s = importlib.util.spec_from_file_location("ms", "atualizar_marcos_severidade.py")
m = importlib.util.module_from_spec(s); s.loader.exec_module(m); sys.exit(m.self_test())
PY

# 5. Teste de estresse §12.1 — recomenda-se REIMPLEMENTAR de forma independente:
#    injete 1 registro {"uf": UF, "nome": "<sintético>", "categoria": "decreto"} por UF
#    numa cópia de data/municipios.json, rode calcular() antes e depois, e verifique
#    Δ = 0 em TODOS os campos de TODAS as UFs. (Reproduzir o teste com código próprio,
#    e não com o script do pacote, é parte do valor probatório.)

# 6. Determinismo do Monte Carlo: rode o passo 1 duas vezes; os intervalos rank_p5/p95
#    devem ser idênticos (semente fixa 42).

# 7. Site completo em execução local:
npx serve   # ou python3 -m http.server — abrir por duplo clique NÃO funciona (fetch bloqueado)
```

Verificações documentais recomendadas: cruzar as constantes do §5.1 contra o METODOLOGIA.md §5; conferir uma amostra dos 248 registros contra as URLs oficiais em `municipios.json` (o `verificar_links.py` automatiza o teste de acessibilidade das URLs; o julgamento de conteúdo é humano); conferir o Livro-Razão de Verificação (documento de rastreabilidade da edição, distribuído com ela).

---

## 11. Segredos e variáveis de ambiente

| Variável | Usada por | Sem ela |
|---|---|---|
| `PORTAL_TRANSPARENCIA_API_KEY` | `atualizar_transferencias.py` | etapa pulada com aviso e instrução de cadastro (gratuito) |
| `NETLIFY_AUTH_TOKEN` + `NETLIFY_SITE_ID` | `processar_contribuicoes.py`, `verificar_contribuicoes.py` | processamento de contribuições pulado com aviso |

Nenhum segredo aparece no código ou no repositório; em CI vivem em GitHub Secrets. Nenhuma dessas ausências compromete os portões: o pacote é auditável integralmente offline.

---

## 12. Limitações conhecidas e estado das pendências (27/08/2026)

1. **`METODOLOGIA.pdf` defasado e sem gerador no repositório:** o script `gerar_pdf_puro.py` não está incluído; o PDF distribuído neste pacote reflete a versão anterior do texto (média 46,2) e **não deve ser publicado** até regeneração a partir do MD corrigido. O MD é a versão normativa. *Contraste deliberado:* o PDF do **índice** (`MARE_Indice_Documentacao.pdf`) já nasce com gerador versionado no repositório (`gerar_pdf_indice.py`) e é computado ao vivo dos dados — regenerá-lo é um comando, e ele não pode envelhecer como o METODOLOGIA.pdf envelheceu.
2. **`marcos_severidade.json` ainda não é consumido pelo índice** — o motor das 3 zonas está construído e testado, mas a integração ao cálculo (§12.5 da Metodologia) é etapa futura, condicionada a simulação e autorização editorial.
3. **Componente populacional pendente de primeira execução** — `atualizar_populacao.py` roda no primeiro deploy; o componente só entra no índice publicado após simulação before/after autorizada.
4. **Fontes declaradas** (`declarado_*` em `percentual_uf.json`) vêm de levantamentos externos de TCEs/sistemas estaduais e não são deriváveis do banco — a atualização delas é editorial, com fonte nomeada.
5. **Auto-relato residual:** o componente `antecipacao` e o `status` estadual são julgamentos de verificação documental externa (não auto-relato dos entes), mas escala e cortes são escolhas normativas declaradas — ver METODOLOGIA §5 e a revisão v2.1→v2.2 em curso.

## 13. Histórico técnico mínimo (para contextualizar diffs)

- **25/08/2026 — v2.0→v2.1:** camada declarada com desconto de 50%; agregados tipados; regra do excedente.
- **26/08/2026 — Correção B:** decreto (peso individual e agregados PB/RN) excluído da pontuação por regra estrutural em `PESO_DOC`/`AGREGADOS`; termo cruzado de `excedente_agregado()` removido (exposto pelo teste de estresse §12.1); guarda legal em `classificar_zona()`; campanha de verificação de capitais (Belém, Porto Alegre, Rio Branco reclassificadas); média nacional 47,5 → 46,2 → 45,7; `percentual_uf.json` passa a ser derivado (fonte única).
- **27/08/2026 — auditoria pré-publicação:** `numpy` no requirements; **regra R7** e recálculo derivado no caminho automático de contribuições; manchete da METODOLOGIA atualizada aos valores vigentes; anotação dos agregados PB/RN no §5.3; guarda de contrato de data em `classificar_zona()`; fallback CSS neutralizado. Relatório completo: `Relatorio_Auditoria_Pre-Publicacao_27-08-2026.md` (distribuído com a edição).
