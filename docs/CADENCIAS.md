# Cadências declaradas dos coletores

Fonte única de verdade da **cadência esperada** de cada coletor. Item 7 do handover da rodada 2
(editoria, 30/09/2026), depois da certificação que encontrou coletores sem execução conhecida e
outros rodando fora da janela.

`scripts/verificar_cadencia_coletores.py` lê esta tabela e `data/saude_pipeline.json` e marca
**atrasado** quem passou de **1,1 × a cadência** sem execução bem-sucedida. O fator existe para um
atraso de minutos não virar alarme: um coletor diário só fica atrasado depois de 26,4 horas.

**Regra de ouro:** coletor que não está nesta tabela **não pode ser certificado**. A certificação diz
"rodou quando devia"; sem cadência declarada não há "devia". Coletor novo entra aqui no mesmo PR que
o cria.

O formato de cada linha é fixo e lido por máquina:

| coletor | cadência | janela | onde roda | o que ele responde |
|---|---|---|---|---|

- **cadência**: `diaria`, `semanal`, `mensal`, `por_documento` (só reprocessa quando o documento
  muda) ou `sob_demanda` (só por botão; nunca fica atrasado).
- **janela**: horário previsto, em UTC.

## Noturnos — diários, descoberta, evidências, juiz, sinais

| coletor | cadência | janela | onde roda | o que ele responde |
|---|---|---|---|---|
| `consultar_querido_diario.py` | diaria | 00:05 UTC | noturno_diarios | diários municipais no acervo do Querido Diário |
| `coletar_diarios_municipais.py` | diaria | 00:05 UTC | noturno_diarios | diários municipais fora do Querido Diário |
| `coletar_diarios_consorciados.py` | diaria | 00:05 UTC | noturno_diarios | diários de consórcio intermunicipal |
| `coletar_doe.py` | diaria | 00:05 UTC | noturno_diarios | diários oficiais dos estados |
| `coletar_s2id.py` | diaria | 00:05 UTC | noturno_diarios | reconhecimentos federais no S2iD |
| `descobrir_planos.py` | diaria | encadeado | noturno_descoberta | busca web por planos municipais |
| `seguir_pistas.py` | diaria | encadeado | noturno_descoberta | pistas até o documento |
| `coletar_saude_estadual.py` | diaria | encadeado | noturno_saude_estadual | planos de saúde dos 27 estados pelos quatro canais: busca aberta, fontes declaradas, páginas de CIEVS/sala de situação/COE e diário oficial do estado com os termos da saúde |
| `coletar_transferencias_municipais.py` | mensal | 05 do mês, 03:00 UTC | semanal_sinais_e_links | transferências da União a cada município, por mês e por rota |
| `triar_confianca_pistas.py` | diaria | encadeado | noturno_descoberta | confiança de cada pista |
| `preservar_evidencias.py` | diaria | encadeado | noturno_evidencias | cópia e hash dos documentos |
| `scripts/preservar_textos_integrais.py` | diaria | encadeado | noturno_evidencias | texto integral dos atos |
| `julgar_e_aplicar_descobertas.py` | diaria | encadeado | noturno_juiz | julgamento automático das pistas |
| `julgar_filas.py` | diaria | encadeado | noturno_juiz | filas pendentes do juiz |
| `aplicar_promocoes_do_juiz.py` | diaria | encadeado | noturno_juiz | aplicação das promoções aprovadas |
| `revisar_pistas.py` | diaria | encadeado | noturno_juiz | revisão das pistas julgadas |
| `coletar_sinais_risco.py` | diaria | 08:00 UTC (rede de segurança) | noturno_sinais | focos, avisos, temperatura, ar, seca |
| `monitorar_sinais_federais.py` | diaria | encadeado | noturno_sinais | sinais e boletins federais |
| `detectar_marcos_federais.py` | diaria | encadeado | noturno_sinais | marcos federais do ciclo |
| `monitorar_atos_resposta.py` | diaria | encadeado | noturno_sinais | decretos de emergência e calamidade |

## Busca web e imprensa

| coletor | cadência | janela | onde roda | o que ele responde |
|---|---|---|---|---|
| `monitorar_imprensa_regional.py` | diaria | encadeado | busca_web_noite | imprensa regional |
| `monitorar_imprensa_saude.py` | diaria | encadeado | busca_web_noite | imprensa de saúde |
| `monitorar_politica_por_inteiro.py` | diaria | encadeado | busca_web_noite | catálogo do Política por Inteiro |
| `monitorar_redes_oficiais.py` | diaria | encadeado | busca_web_noite | perfis oficiais dos entes |
| `verificar_pista_imprensa.py` | diaria | encadeado | busca_web_noite | veículo de imprensa é veículo mesmo |
| `scripts/busca_dirigida_do_ato.py` | diaria | encadeado | busca_web_noite | busca dirigida do ato citado |

## Semanais

| coletor | cadência | janela | onde roda | o que ele responde |
|---|---|---|---|---|
| `coletar_cobertura_qd.py` | semanal | dom 07:30 UTC | semanal_sinais_e_links | cobertura do acervo do Querido Diário |
| `coletar_semiarido_sudene.py` | semanal | dom 07:30 UTC | semanal_sinais_e_links | delimitação do Semiárido |
| `coletar_prioritarios_mma.py` | semanal | dom 07:30 UTC | semanal_sinais_e_links | prioritários do MMA |
| `coletar_srag_sivep.py` | semanal | dom 07:30 UTC | semanal_sinais_e_links | SRAG pelo SIVEP-Gripe |
| `coletar_arboviroses_sinan.py` | semanal | dom 07:30 UTC | semanal_sinais_e_links | dengue e chikungunya pelo SINAN |
| `coletar_obitos_registro_civil.py` | semanal | dom 07:30 UTC | semanal_sinais_e_links | óbitos em cartório por UF e mês |
| `scripts/sondar_boletim_infogripe.py` | semanal | dom 07:30 UTC | semanal_sinais_e_links | acesso ao InfoGripe voltou? |
| `descobrir_dominios.py` | semanal | dom 07:30 UTC | semanal_sinais_e_links | domínio oficial de cada ente |
| `coletar_painel_am.py` | semanal | dom 07:30 UTC | semanal_sinais_e_links | painel amostral |
| `scripts/amostra_auditoria_semanal.py` | semanal | dom 03:10 UTC | atualizar | amostra de auditoria humana |
| `coletar_financiamento.py` | semanal | dom 03:10 UTC | atualizar | transferências e execução orçamentária |
| `saude_opendatasus.py` | semanal | dom 03:10 UTC | atualizar | dengue, SRAG e DDA pelo OpenDataSUS |
| `verificar_prazos_legais.py` | semanal | dom 03:10 UTC | atualizar | prazos legais do ciclo |

## Por documento — só reprocessam quando o documento muda

| coletor | cadência | janela | onde roda | o que ele responde |
|---|---|---|---|---|
| `coletar_cadastro_prioritarios.py` | por_documento | dom 07:30 UTC | semanal_sinais_e_links | cadastro da Casa Civil, por nota técnica |
| `coletar_normais_inmet.py` | por_documento | dom 07:30 UTC | semanal_sinais_e_links | normal climatológica 1991–2020 das capitais |

## Sob demanda — nunca ficam atrasados

| coletor | cadência | janela | onde roda | o que ele responde |
|---|---|---|---|---|
| `scripts/medir_revocacao_das_consultas.py` | sob_demanda | — | medir_revocacao | revocação da busca |
| `scripts/diagnosticar_fontes_sinais.py` | sob_demanda | — | diagnostico_sinais | diagnóstico das fontes de sinais |
| `scripts/configurar_notificacao_formulario.py` | sob_demanda | — | notificacao_formulario | notificação do formulário |
