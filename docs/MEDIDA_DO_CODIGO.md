# Medida do código

Gerado por `python3 scripts/medir_codigo.py --gravar`. Linha de base da consolidação (meta: ≤ 50 mil linhas de .py/.js, mesma proteção).

- **100.423 linhas** em **317 arquivos** .py/.js; **37 workflows**.
- **67 comandos de portão**: dados/portão 19, paginas/autoteste 2, paginas/portão 46.
- **154 nomes de função** definidos em mais de um arquivo.

## Por pasta

| pasta | linhas |
|---|---:|
| `(raiz)` | 55172 |
| `scripts` | 38016 |
| `assets` | 6522 |
| `arquivo` | 445 |
| `.claude` | 268 |

## Os 25 maiores

| arquivo | linhas |
|---|---:|
| `coletar_sinais_risco.py` | 3186 |
| `coletores_base.py` | 2236 |
| `juiz.py` | 1787 |
| `verificar_pista_imprensa.py` | 1703 |
| `coletar_doe.py` | 1627 |
| `julgar_saude.py` | 1363 |
| `assets/js/monitor-de-riscos.js` | 1318 |
| `scripts/verificar_regras_de_dado.py` | 1294 |
| `scripts/ensaio_da_noite.py` | 1272 |
| `assets/js/index.js` | 1249 |
| `coletar_painel_am.py` | 1135 |
| `scripts/unir_conflito_de_rodada.py` | 1089 |
| `coletar_edicoes_doe.py` | 1078 |
| `julgar_e_aplicar_descobertas.py` | 1067 |
| `recalcular_mare.py` | 1049 |
| `coletar_diarios_consorciados.py` | 1040 |
| `gerar_imprensa_semana.py` | 1032 |
| `descobrir_planos.py` | 852 |
| `gerar_pacote_blog.py` | 827 |
| `julgar_filas.py` | 794 |
| `scripts/verificar_repositorio.py` | 770 |
| `scripts/pistas.py` | 768 |
| `coletar_s2id.py` | 763 |
| `scripts/gerar_topo_das_paginas.py` | 708 |
| `coletar_saude_estadual.py` | 702 |

## Funções de mesmo nome em arquivos distintos (as 40 mais repetidas)

| função | arquivos | onde |
|---|---:|---|
| `coletar` | 28 | `buscar_protocolo_calor.py`, `coletar_boletim_df_arboviroses.py`, `coletar_boletim_ms_dengue.py`, `coletar_boletim_pb_arboviroses.py` … |
| `problemas` | 19 | `coletar_cadastro_prioritarios.py`, `coletar_normais_inmet.py`, `coletar_prioritarios_mma.py`, `coletar_semiarido_sudene.py` … |
| `self_test` | 15 | `atualizar_marcos_severidade.py`, `classificador_natureza.py`, `detectar_marcos_federais.py`, `gerar_dados_abertos.py` … |
| `gerar` | 13 | `classificar_planos_municipais.py`, `gerar_blog.py`, `gerar_card_municipios.py`, `gerar_contadores_financiamento.py` … |
| `montar` | 12 | `buscar_protocolo_calor.py`, `desfechos_sus.py`, `gerar_card_municipios.py`, `gerar_erros_localizacao.py` … |
| `classificar` | 10 | `classificador_natureza.py`, `classificar_planos_municipais.py`, `classificar_saude_no_plano.py`, `coletar_desfechos_saude.py` … |
| `_get` | 9 | `consultar_querido_diario.py`, `detectar_marcos_federais.py`, `monitorar_imprensa_regional.py`, `monitorar_imprensa_saude.py` … |
| `registrar` | 9 | `descobrir_planos.py`, `funil.py`, `gerar_lai.py`, `monitorar_imprensa_regional.py` … |
| `sondar` | 9 | `coletar_datasus_dbc.py`, `coletar_obitos.py`, `coletar_sg_esus.py`, `coletar_sih.py` … |
| `normalizar` | 8 | `classificar_pista_civil.py`, `classificar_planos_municipais.py`, `coletar_normais_inmet.py`, `coletar_sinais_risco.py` … |
| `__load` | 7 | `arquivo/pesquisadores/pesquisadores.js`, `assets/js/defesa-civil.js`, `assets/js/financiamento.js`, `assets/js/index.js` … |
| `carregar` | 7 | `aplicar_revisao.py`, `scripts/testar_fixtures_localizacao.py`, `scripts/testar_ordem_prioridade_ufs.py`, `scripts/validar_dicionario.py` … |
| `_norm` | 6 | `coletar_boletim_pe_arboviroses.py`, `coletar_painel_am.py`, `coletar_s2id.py`, `scripts/municipio_do_dominio.py` … |
| `_plano` | 6 | `classificar_saude_no_plano.py`, `coletar_dda.py`, `coletar_srag_gripe.py`, `coletar_transferegov.py` … |
| `aplicar` | 6 | `julgar_saude.py`, `scripts/aplicar_edicoes.py`, `scripts/incorporar_respostas_lai.py`, `scripts/migrar_sobras_do_doe.py` … |
| `agregar` | 5 | `coletar_datasus_dbc.py`, `coletar_execucao_mps.py`, `coletar_sih.py`, `coletar_sim.py` … |
| `carregar_fila` | 5 | `descobrir_planos.py`, `monitorar_imprensa_regional.py`, `monitorar_imprensa_saude.py`, `monitorar_sinais_federais.py` … |
| `medir` | 5 | `scripts/cobertura_docstrings.py`, `scripts/diagnostico_fontes_saude.py`, `scripts/medir_codigo.py`, `scripts/medir_revocacao_das_consultas.py` … |
| `norm` | 5 | `atualizar_instrumentos_estaduais.py`, `converter_contribuicao.py`, `processar_contribuicoes.py`, `scripts/fila_do_juiz_querido_diario.py` … |
| `relatorio` | 5 | `coletar_cobertura_qd.py`, `scripts/busca_dirigida_do_ato.py`, `scripts/fechar_saude.py`, `scripts/medir_codigo.py` … |
| `__init` | 4 | `assets/js/defesa-civil.js`, `assets/js/financiamento.js`, `assets/js/index.js`, `assets/js/monitor-de-riscos.js` |
| `_git` | 4 | `scripts/commit_do_elo.py`, `scripts/verificar_idempotencia_dos_derivados.py`, `scripts/verificar_repositorio.py`, `scripts/verificar_tamanho_dos_dados.py` |
| `_sem_acento` | 4 | `revisar_pistas.py`, `scripts/pistas.py`, `scripts/validar_dicionario.py`, `scripts/vocabulario.py` |
| `baixar` | 4 | `scripts/diagnosticar_fontes_sinais.py`, `scripts/sondar_munic_ibge.py`, `scripts/sondar_portal_fogo_saude.py`, `scripts/sondar_transferegov.py` |
| `data_br` | 4 | `coletar_transferegov.py`, `gerar_resposta.py`, `scripts/cruzar_ocp_com_atos.py`, `scripts/gerar_mudancas.py` |
| `decidir` | 4 | `coletar_saude_estadual.py`, `coletar_sg_esus.py`, `monitorar_busca_web.py`, `scripts/limpar_fila_de_pistas.py` |
| `faixa` | 4 | `gerar_dados_abertos.py`, `gerar_monitor_saude.py`, `gerar_selos.py`, `robustez_saude.py` |
| `fundir` | 4 | `coletar_prioritarios_mma.py`, `coletar_recursos_resposta.py`, `coletar_semiarido_sudene.py`, `coletar_transferencias_municipais.py` |
| `j` | 4 | `aplicar_c10_imprensa.py`, `gerar_painel.py`, `migrar_v224_verificacao.py`, `scripts/verificar_robustez_atualizacao.py` |
| `numero` | 4 | `coletar_execucao_mps.py`, `coletar_transferegov.py`, `scripts/cruzar_ocp_com_atos.py`, `scripts/ingerir_ocp_midr.py` |
| `parse_texto` | 4 | `coletar_boletim_df_arboviroses.py`, `coletar_boletim_ms_dengue.py`, `coletar_boletim_pb_arboviroses.py`, `coletar_boletim_pe_arboviroses.py` |
| `renderizar` | 4 | `coletar_painel_am.py`, `gerar_feeds.py`, `scripts/_inline_js.js`, `scripts/renderizar_figura.py` |
| `tabela` | 4 | `assets/js/financiamento.js`, `gerar_pdf_indice.py`, `scripts/gerar_saude_pipeline.py`, `scripts/medir_revocacao_das_consultas.py` |
| `w` | 4 | `aplicar_c10_imprensa.py`, `gerar_painel.py`, `migrar_v224_verificacao.py`, `scripts/verificar_robustez_atualizacao.py` |
| `_data` | 3 | `gerar_financiamento_semana.py`, `scripts/verificar_frescor.py`, `scripts/verificar_regras_de_dado.py` |
| `_host` | 3 | `buscar_planos_fontes_abertas.py`, `gerar_card_municipios.py`, `triar_confianca_pistas.py` |
| `_iso` | 3 | `coletar_sinais_risco.py`, `gerar_dados_abertos.py`, `scripts/checagem_pre_noite.py` |
| `_levanta` | 3 | `buscar_planos_fontes_abertas.py`, `coletar_transferencias_municipais.py`, `scripts/testar_busca_dou.py` |
| `_n` | 3 | `coletar_boletim_df_arboviroses.py`, `coletar_boletim_pb_arboviroses.py`, `coletar_boletim_pe_arboviroses.py` |
| `avaliar` | 3 | `scripts/checagem_pre_noite.py`, `scripts/testar_fixtures_localizacao.py`, `scripts/verificar_fila_nao_humana.py` |
