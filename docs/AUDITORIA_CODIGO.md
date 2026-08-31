# Protocolo de Auditoria de Código e Plataforma · Monitor El Niño Brasil
Versão do índice: MARÉ v2.2.2 · Corte dos dados: 26/08/2026 · Última atualização: 27/08/2026
Pacote: `monitorelnino-corrigido-27-08-2026.zip` · Manifesto de integridade: `docs/MANIFEST_SHA256.txt`

Este documento é o ponto de entrada para uma auditoria de código profissional
do repositório. Os demais documentos de apoio, todos em `docs/`, são:
`AUDITORIA_METODOLOGIA.md` (o que o índice mede e por quê),
`COMO_RODAR_E_PENDENCIAS.md` (instalação, execução, deploy),
`LGPD_PRIVACIDADE.md` (o único ponto de coleta de dado pessoal),
`SBOM.md` + `sbom-python.cdx.json` + `sbom-node.cdx.json` (inventário de
dependências e auditoria de vulnerabilidades), e `CHANGELOG.md`,
na raiz do repositório, com o histórico de versões.

## 1. Escopo e arquitetura

Plataforma estática (HTML/CSS/JS) servida diretamente de arquivos, sem
backend próprio e sem passo de build: as três páginas (`index.html`,
`proteja-se.html`, `envie-dados.html`, mais `obrigado.html` de retorno do
formulário) buscam `data/*.json` (14 arquivos) em runtime via `fetch`.
Bibliotecas de terceiros (D3, Chart.js, jsPDF) são carregadas pelo
navegador do visitante via CDN (`cdnjs.cloudflare.com`), fora do escopo do
SBOM deste repositório — ver `docs/SBOM.md`, seção de dependências diretas.

O pipeline de dados é Python 3 (quatro dependências externas, todas
travadas em versão exata em `requirements.txt`; ver `docs/SBOM.md`) mais
dois portões em Node.js (`jsdom`, `d3`, listados em `package.json`),
executado pela Action semanal do GitHub (`.github/workflows/atualizar.yml`,
segundas 09h UTC, e sob demanda) e localmente por qualquer editor. O
formulário público usa Netlify Forms com detecção de ambiente (o envio real
só é habilitado no domínio publicado, nunca em prévia local).

## 2. Inventário completo de componentes

### 2.1 Orquestração e motor
| Script | Função | Escreve no banco público? |
|---|---|---|
| `atualizar.py` | Orquestrador: executa as oito etapas do pipeline canônico em ordem, com portões obrigatórios bloqueantes e etapas de rede tolerantes a falha. | indiretamente, via as etapas que chama |
| `recalcular_mare.py` | Motor do índice: calcula os três componentes por estado e agrega com elemento geométrico e piso. `--check` recalcula em memória e compara campo a campo contra o publicado (portão 2), sem gravar. | sim (`data/indice.json`), só sem `--check` |

### 2.2 Portões de verificação (bloqueantes)
| Script | O que confere |
|---|---|
| `verificar_consistencia.py` | Portão 1. Paridades entre `municipios`↔`pontos_mapa`↔`percentual_uf`↔`indice`, esquemas de campo, vocabulário controlado de canais, claims numéricas do texto do site. **Seção 8 (27/08/2026):** todo mapa e gráfico do site é conferido contra os dados e a classificação canônica — `CONSIST` (27 UFs, SEM↔LAC, categoria×instrumento coerentes), união das áreas temáticas versus estados com instrumento, tabela estática versus `CONSIST`, contagens em texto/`aria-label` versus o banco; validada por teste negativo documentado (quebra proposital detectada e restaurada durante o desenvolvimento). |
| `scripts/verificar_estrutura.js` | Portão 3. Árvore HTML das quatro páginas: balanceamento de tags fora de `<script>`, ausência de elementos órfãos, masthead/rodapé presentes e consistentes. |
| `scripts/verificar_runtime.js` | Portão 4. Executa `index.html` num navegador simulado (jsdom + d3 reais, Chart.js simulado) e valida a renderização dos mapas, a tabela de auditoria e o fluxo completo de consulta municipal com os dados reais. **Limitação documentada no próprio código:** não escuta `unhandledrejection`, então uma exceção assíncrona pode ser engolida silenciosamente (foi exatamente a causa de um bug corrigido nesta sessão — ver `CHANGELOG.md`, Fixed). |
| `recalcular_mare.py --check` | Portão 2, ver 2.1. |

### 2.3 Aquisição de dados (rede tolerante a falha; nunca publica dado não confirmado)
| Script | Fonte | Grava direto no banco público? |
|---|---|---|
| `atualizar_boletins.py` | Páginas oficiais CEMADEN/INPE | não — só `data/boletins.json` |
| `atualizar_populacao.py` | Censo 2022, API SIDRA/IBGE | sim, sob 3 validações bloqueantes (5 sentinelas + total exato) |
| `atualizar_recursos.py` | PIB per capita, API SIDRA/IBGE | sim, sob 4 sentinelas; falha-segura |
| `atualizar_transferencias.py` | Portal da Transparência (requer `PORTAL_TRANSPARENCIA_API_KEY`) | sim, com limitador de taxa |
| `atualizar_instrumentos_estaduais.py` | Repositórios estaduais estruturados (parser por UF) | **não** — só `data/instrumentos_revisar.json`, para aprovação humana via `aplicar_revisao.py` |
| `atualizar_marcos_severidade.py` | Monitor de Secas, catálogo aberto CKAN/ANA (descoberta dinâmica de recurso) | não — motor de classificação testável por `self_test`, sem depender de rede |
| `consultar_querido_diario.py` | API do Querido Diário (Open Knowledge Brasil) | não — só pistas para fila humana |
| `buscar_financiamento_preventivo.py` | Valida `data/financiamento_uf.json` e imprime gabaritos de busca por UF | não (ferramenta de apoio à sessão de verificação) |

### 2.4 Leitura e classificação (marcador editorial, nunca pontuação)
| Script | Função |
|---|---|
| `analisar_decretos.py` | Aplica três dicionários versionados (desregulação, proteção, antecipação com limiares observacionais) ao texto dos decretos do banco. |
| `verificar_vigencia.py` | Classifica cada decreto em ativo / prazo típico vencido / indeterminado, por parser de datas brasileiras imperfeitas; roda a cada atualização. |

### 2.5 Funil de contribuições públicas (único ponto de julgamento humano permanente)
| Script | Papel |
|---|---|
| `verificar_contribuicoes.py` | Lê submissões via API do Netlify, aplica triagem de completude, grava fila fora do versionamento (ver `docs/LGPD_PRIVACIDADE.md`). |
| `processar_contribuicoes.py` | Aplica as regras R1-R6 (campos, casamento IBGE exato, tipo automatizável, domínio oficial, coerência do documento, não-regressão); reserva R7 (planos e capitais) para julgamento humano. |
| `converter_contribuicao.py` | Converte item aprovado da fila para o formato do banco público — sem e-mail nem qualquer dado de contato. |
| `aplicar_revisao.py` | Aplica revisão humana de propostas (de contribuições ou de `atualizar_instrumentos_estaduais.py`) ao banco, recalcula o índice e roda os portões. |

### 2.6 Saída e auditoria de robustez
| Script | Função |
|---|---|
| `gerar_pdf_indice.py` | Monta o PDF de documentação do índice, computando os números ao vivo a partir da bateria de sensibilidade — nenhum valor digitado à mão. |
| `gerar_pdf_metodologia.py` | Monta o PDF da metodologia a partir do texto vivo de `METODOLOGIA.md`. |
| `analise_sensibilidade.py` | Bateria de robustez (agregação linear×geométrica, piso, descontos, pesos, Monte Carlo, casos de borda), seguindo o Handbook OCDE/JRC; importada por `gerar_pdf_indice.py`. |
| `verificar_links.py` | Verifica todos os links externos (marcação + banco); nunca remove link automaticamente, só reporta. `--self-test` roda a lógica sem rede (limitação de ambiente declarada no próprio módulo). |
| `scripts/sincronizar_single_file.py` | Ferramenta de conveniência para a prévia single-file de revisão em chat; **não integra o pacote publicado** e não é chamada por `atualizar.py`. |
| `scripts/validar_dicionario.py` | Fonte única de verdade do vocabulário de recuperação (`data/dicionario_busca.json`); expõe `get_sinalizadores_resposta()`, importado pelo portão de natureza. `--self-test` roda 3 testes: estrutura, precisão por regressão (casos reais AC/AM/MS/PE) e variantes acento/hífen. |
| `monitorar_imprensa_regional.py` | Vigia de imprensa nacional (Google News RSS) por instrumentos não registrados, em três camadas priorizadas (LAC → capitais → demais estados), cursor persistido. **Trava absoluta**: nunca escreve em estados/municipios/indice; toda pista nasce não-confirmada e não-promovível; self-test valida a garantia por inspeção do próprio código-fonte. Etapa informativa da Action. |
| Portão de segredos (dentro de `verificar_consistencia.py`, C10, 30/08/2026) | Bloqueia se `.env.example` vier preenchido, se `.gitignore` não cobrir `.env`, ou se um `.env` real existir no pacote. Nunca imprime o valor do segredo. Validado por teste negativo real. |
| `verificar_prazos_legais.py` | Cruza os marcos federais curados (`data/marcos_prazos.json`) com o banco por UF e grava `data/prazos_uf.json` — **marcador editorial, nunca pontuação** (METODOLOGIA §15); `--simular` gera quadro experimental não publicável (semente v3). Etapa informativa da Action. |
| `monitorar_sinais_federais.py` | Vigia DOU e ADPF 743 e grava pistas em `data/pistas_sinais.json` para triagem humana — **descoberta, nunca classificação** (METODOLOGIA §15); `--self-test` offline valida parsers, dedup e a garantia de não-escrita nos arquivos curados. Etapa informativa da Action. |
| `gerar_tese.js` | Ferramenta de sessão (C8, auditoria 29/08/2026): gera o DOCX da tese metodológica a partir do código vivo. **Não integra o pipeline** nem a selagem (escopo declarado em `scripts/gerar_manifesto.py`); depende do pacote npm `docx`, instalado sob demanda na sessão de escrita (`npm install --no-save docx`), deliberadamente fora de `package.json` — mesmo estatuto de `scripts/sincronizar_single_file.py`. |

## 3. Protocolo de verificação (obrigatório antes de qualquer publicação)

Ordem canônica: `verificar_vigencia.py` → `recalcular_mare.py --write` →
portões 1-4 → regeneração dos PDFs → selagem. Critério de aprovação: os
quatro portões verdes e a média nacional reproduzida bit a bit. Toda edição
programática de arquivo de texto usa verificação de substituição (assert
de que o alvo existe antes de substituir) e escrita em estágios — regra
nascida de um incidente documentado (duplicata de integração detectada por
discrepância de nomes e unificada). Cada portão foi validado por pelo
menos um teste negativo real (quebra proposital, confirmação de que o
portão acusa, restauração) durante o desenvolvimento, não apenas
declarado como existente.

## 4. Segurança, segredos e superfície de ataque

**Segredos.** O repositório não contém segredo algum: `PORTAL_TRANSPARENCIA_API_KEY`,
`NETLIFY_AUTH_TOKEN` e `NETLIFY_SITE_ID` vivem exclusivamente em GitHub
Secrets (produção) ou `.env` local não versionado (`.env.example` documenta
os três, sem valores). Ausência de qualquer uma delas faz a etapa
correspondente ser pulada com aviso — nunca falha silenciosa, nunca
publicação com dado não confirmado.

**Superfície de rede.** O pipeline só fala com APIs declaradas e nomeadas
(IBGE/SIDRA, Querido Diário, Portal da Transparência, catálogo CKAN da
ANA, páginas institucionais CEMADEN/INPE, API do Netlify). Todas as
chamadas HTTP usam `User-Agent` identificado e timeout explícito.

**Entrada não confiável (o formulário público).** É o único canal de
entrada de dado externo não controlado pela equipe. Mitigações em
profundidade: honeypot antispam nativo do Netlify (`bot-field`); validação
de domínio oficial da fonte citada (R4); casamento exato (não
aproximado) do município contra a malha IBGE, com nome ambíguo sempre
recusado, nunca adivinhado (R2); regra de não-regressão contra duplicata
mais fraca (R6); e, estruturalmente, nenhuma contribuição altera o banco
sem passar por pelo menos uma das seis regras automáticas ou pela
revisão humana R7. O conteúdo do formulário nunca é interpolado em
HTML sem escape do lado do site (os campos são exibidos pelo Netlify em
seu próprio painel, não renderizados de volta no site público).

**Cadeia de suprimentos.** Ver `docs/SBOM.md`: quatro dependências Python e
duas Node diretas, todas com versão travada; `pip-audit` e `npm audit`
não encontraram vulnerabilidade conhecida em 27/08/2026. Bibliotecas
carregadas via CDN pelo navegador do visitante (D3, Chart.js, jsPDF) ainda
não têm hash de integridade (Subresource Integrity) nas tags `<script>` —
pendência declarada na seção 6.

**Dado pessoal.** Tratado em documento dedicado: `docs/LGPD_PRIVACIDADE.md`.
Resumo: um único campo opcional (e-mail de contato) em todo o sistema é
dado pessoal identificável, nunca chega ao banco público (verificado por
inspeção de código e por ausência no banco publicado), e sua retenção
fora do Netlify é efêmera quando a triagem roda em CI.

## 5. Reprodutibilidade

Qualquer auditor reproduz o índice publicado com
`python3 recalcular_mare.py --check` sobre o `data/` do pacote. A
metodologia (seção Monte Carlo) documenta os dez mil sorteios de pesos, e
`analise_sensibilidade.py` os executa de forma independente e
reproduzível, alimentando ao vivo o PDF de documentação do índice — nenhum
número do PDF é digitado à mão. Integridade byte a byte de todo artefato
publicado: `docs/MANIFEST_SHA256.txt` (hash SHA-256 de cada arquivo).
Ambiente: Python 3.12, Node.js ≥18, dependências travadas (`requirements.txt`,
`package.json`/`package-lock.json`) e auditadas (`docs/SBOM.md`).

**Determinismo dos PDFs selados (R1 da segunda auditoria, 29/08/2026, corrigido).**
Até esta correção, `gerar_pdf_indice.py`/`gerar_pdf_metodologia.py` produziam
hash diferente a cada execução mesmo sem qualquer mudança de dados, porque o
reportlab embute metadados de data/ID a partir do relógio da máquina — a
selagem só era verificável por quem recebia o pacote pronto, nunca por quem
regenerava os PDFs, o que a segunda auditoria identificou corretamente como
limitação de auditabilidade. Corrigido fixando `SOURCE_DATE_EPOCH` a partir
da própria data de corte dos dados (`data/meta.json`), lida nativamente pelo
reportlab ≥4: os PDFs passaram a ser **função determinística dos dados
publicados**, não do instante de geração. `scripts/gerar_manifesto.py --check`
prova isso a cada execução — regenera os dois PDFs e falha ruidosamente se o
hash mudar sem mudança de dados — validado por teste negativo real (quebra
proposital do fixador acusada com hash divergente exato, restaurada). Um
auditor externo agora pode rodar `gerar_pdf_*.py` seguido de
`gerar_manifesto.py --check` livremente: a conferência fecha sem precisar
regravar o manifesto, salvo se os dados de fato mudaram.

## 6. Qualidade de código e cobertura de documentação interna

135 das 135 funções e 28 dos 28 módulos Python têm docstring — número
produzido, desde 29/08/2026 (C9 da auditoria externa), por
`scripts/cobertura_docstrings.py`, que fixa o critério de contagem
(toda FunctionDef/AsyncFunctionDef encontrada por `ast.walk`, funções
aninhadas e métodos incluídos; lambdas fora por gramática). A
divergência anterior (85/87 declarado × 85/91 medido pela auditoria)
era de critério, não de substância, e foi resolvida na raiz: o número
publicado aqui deve sempre reproduzir a saída do script.

## 7. Limitações conhecidas e pendências (declaradas)

Ver `docs/COMO_RODAR_E_PENDENCIAS.md`, seção Pendências, para a lista
consolidada e categorizada (bloqueio duro, qualidade pré-lançamento,
primeira produção, melhorias técnicas, versões futuras). As pendências de
segurança e privacidade específicas estão nas seções 4-5 de
`docs/LGPD_PRIVACIDADE.md` e na seção 4 (SBOM) e "Pendências declaradas"
de `docs/SBOM.md`.
