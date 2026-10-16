# Medida do código

Gerado por `python3 scripts/medir_codigo.py --gravar`. Linha de base da consolidação (meta: ≤ 50 mil linhas de .py/.js, mesma proteção).

- **99.239 linhas** em **343 arquivos** .py/.js; **33 workflows**.
- **272 comandos de portão**: dados/autoteste 76, dados/portão 40, paginas/autoteste 82, paginas/portão 74.
- **150 nomes de função** definidos em mais de um arquivo.

## Por pasta

| pasta | linhas |
|---|---:|
| `(raiz)` | 49175 |
| `scripts` | 40970 |
| `assets` | 8381 |
| `arquivo` | 445 |
| `.claude` | 268 |

## Os 25 maiores

| arquivo | linhas |
|---|---:|
| `coletar_sinais_risco.py` | 2557 |
| `coletores_base.py` | 2133 |
| `verificar_pista_imprensa.py` | 1706 |
| `juiz.py` | 1422 |
| `assets/js/financiamento.js` | 1420 |
| `assets/js/monitor-de-riscos.js` | 1377 |
| `coletar_doe.py` | 1322 |
| `assets/js/saude.js` | 1321 |
| `assets/js/index.js` | 1298 |
| `scripts/ensaio_da_noite.py` | 1172 |
| `gerar_imprensa_semana.py` | 1157 |
| `coletar_painel_am.py` | 1135 |
| `julgar_saude.py` | 1042 |
| `coletar_diarios_consorciados.py` | 1040 |
| `recalcular_mare.py` | 1037 |
| `scripts/unir_conflito_de_rodada.py` | 1019 |
| `julgar_e_aplicar_descobertas.py` | 1011 |
| `gerar_pacote_blog.py` | 830 |
| `coletar_edicoes_doe.py` | 766 |
| `julgar_filas.py` | 766 |
| `coletar_s2id.py` | 762 |
| `assets/js/defesa-civil.js` | 738 |
| `coletar_saude_estadual.py` | 738 |
| `scripts/pistas.py` | 701 |
| `coletar_diarios_municipais.py` | 659 |

## Funções de mesmo nome em arquivos distintos (as 40 mais repetidas)

| função | arquivos | onde |
|---|---:|---|
| `problemas` | 40 | `coletar_cadastro_prioritarios.py`, `coletar_normais_inmet.py`, `coletar_prioritarios_mma.py`, `coletar_semiarido_sudene.py` … |
| `coletar` | 22 | `buscar_protocolo_calor.py`, `coletar_boletim_df_arboviroses.py`, `coletar_boletim_ms_dengue.py`, `coletar_boletim_pb_arboviroses.py` … |
| `self_test` | 15 | `atualizar_marcos_severidade.py`, `classificador_natureza.py`, `detectar_marcos_federais.py`, `gerar_dados_abertos.py` … |
| `gerar` | 12 | `classificar_planos_municipais.py`, `gerar_blog.py`, `gerar_card_municipios.py`, `gerar_contadores_financiamento.py` … |
| `classificar` | 11 | `classificador_natureza.py`, `classificar_planos_municipais.py`, `classificar_saude_no_plano.py`, `coletar_desfechos_saude.py` … |
| `montar` | 11 | `buscar_protocolo_calor.py`, `gerar_card_municipios.py`, `gerar_erros_localizacao.py`, `gerar_financiamento_semana.py` … |
| `_get` | 9 | `consultar_querido_diario.py`, `detectar_marcos_federais.py`, `monitorar_imprensa_regional.py`, `monitorar_imprensa_saude.py` … |
| `registrar` | 9 | `descobrir_planos.py`, `funil.py`, `gerar_lai.py`, `monitorar_imprensa_regional.py` … |
| `conferir` | 8 | `scripts/gerar_saude_pipeline.py`, `scripts/verificar_ancoras_internas.py`, `scripts/verificar_ausencia_declarada.py`, `scripts/verificar_cliente_identificado.py` … |
| `normalizar` | 8 | `classificar_pista_civil.py`, `classificar_planos_municipais.py`, `coletar_normais_inmet.py`, `coletar_sinais_risco.py` … |
| `__load` | 7 | `arquivo/pesquisadores/pesquisadores.js`, `assets/js/defesa-civil.js`, `assets/js/financiamento.js`, `assets/js/index.js` … |
| `carregar` | 7 | `aplicar_revisao.py`, `scripts/testar_fixtures_localizacao.py`, `scripts/testar_ordem_prioridade_ufs.py`, `scripts/validar_dicionario.py` … |
| `renderizar` | 7 | `coletar_painel_am.py`, `gerar_feeds.py`, `scripts/renderizar_figura.py`, `scripts/verificar_fichas_semanticas.js` … |
| `_norm` | 6 | `coletar_boletim_pe_arboviroses.py`, `coletar_painel_am.py`, `coletar_s2id.py`, `scripts/municipio_do_dominio.py` … |
| `_plano` | 6 | `classificar_saude_no_plano.py`, `coletar_dda.py`, `coletar_srag_gripe.py`, `coletar_transferegov.py` … |
| `__init` | 5 | `assets/js/defesa-civil.js`, `assets/js/financiamento.js`, `assets/js/index.js`, `assets/js/monitor-de-riscos.js` … |
| `aplicar` | 5 | `julgar_saude.py`, `scripts/aplicar_edicoes.py`, `scripts/incorporar_respostas_lai.py`, `scripts/migrar_sobras_do_doe.py` … |
| `carregar_fila` | 5 | `descobrir_planos.py`, `monitorar_imprensa_regional.py`, `monitorar_imprensa_saude.py`, `monitorar_sinais_federais.py` … |
| `medir` | 5 | `scripts/cobertura_docstrings.py`, `scripts/diagnostico_fontes_saude.py`, `scripts/medir_codigo.py`, `scripts/medir_revocacao_das_consultas.py` … |
| `norm` | 5 | `atualizar_instrumentos_estaduais.py`, `converter_contribuicao.py`, `processar_contribuicoes.py`, `scripts/fila_do_juiz_querido_diario.py` … |
| `relatorio` | 5 | `coletar_cobertura_qd.py`, `scripts/busca_dirigida_do_ato.py`, `scripts/fechar_saude.py`, `scripts/medir_codigo.py` … |
| `sondar` | 5 | `coletar_sg_esus.py`, `coletar_srag_gripe.py`, `scripts/sondar_enso_probabilidades.py`, `scripts/sondar_munic_ibge.py` … |
| `_levanta` | 4 | `coletar_doe.py`, `coletar_sg_esus.py`, `coletar_transferencias_municipais.py`, `scripts/testar_busca_dou.py` |
| `baixar` | 4 | `scripts/diagnosticar_fontes_sinais.py`, `scripts/sondar_munic_ibge.py`, `scripts/sondar_portal_fogo_saude.py`, `scripts/sondar_transferegov.py` |
| `data_br` | 4 | `coletar_transferegov.py`, `gerar_resposta.py`, `scripts/cruzar_ocp_com_atos.py`, `scripts/gerar_mudancas.py` |
| `decidir` | 4 | `coletar_saude_estadual.py`, `coletar_sg_esus.py`, `monitorar_busca_web.py`, `scripts/limpar_fila_de_pistas.py` |
| `faixa` | 4 | `gerar_dados_abertos.py`, `gerar_monitor_saude.py`, `gerar_selos.py`, `robustez_saude.py` |
| `fonte_do_coletor` | 4 | `coletar_doe.py`, `coletar_recursos_resposta.py`, `coletar_saude_estadual.py`, `coletar_sg_esus.py` |
| `fundir` | 4 | `coletar_prioritarios_mma.py`, `coletar_recursos_resposta.py`, `coletar_semiarido_sudene.py`, `coletar_transferencias_municipais.py` |
| `j` | 4 | `aplicar_c10_imprensa.py`, `gerar_painel.py`, `migrar_v224_verificacao.py`, `scripts/verificar_robustez_atualizacao.py` |
| `numero` | 4 | `coletar_execucao_mps.py`, `coletar_transferegov.py`, `scripts/cruzar_ocp_com_atos.py`, `scripts/ingerir_ocp_midr.py` |
| `parse_texto` | 4 | `coletar_boletim_df_arboviroses.py`, `coletar_boletim_ms_dengue.py`, `coletar_boletim_pb_arboviroses.py`, `coletar_boletim_pe_arboviroses.py` |
| `w` | 4 | `aplicar_c10_imprensa.py`, `gerar_painel.py`, `migrar_v224_verificacao.py`, `scripts/verificar_robustez_atualizacao.py` |
| `_contexto_tls` | 3 | `coletar_sinais_risco.py`, `scripts/sondar_credenciais.py`, `scripts/sondar_munic_ibge.py` |
| `_git` | 3 | `scripts/commit_do_elo.py`, `scripts/verificar_idempotencia_dos_derivados.py`, `scripts/verificar_tamanho_dos_dados.py` |
| `_hash` | 3 | `monitorar_imprensa_regional.py`, `monitorar_imprensa_saude.py`, `monitorar_sinais_federais.py` |
| `_n` | 3 | `coletar_boletim_df_arboviroses.py`, `coletar_boletim_pb_arboviroses.py`, `coletar_boletim_pe_arboviroses.py` |
| `_sem_acento` | 3 | `revisar_pistas.py`, `scripts/pistas.py`, `scripts/validar_dicionario.py` |
| `avaliar` | 3 | `scripts/checagem_pre_noite.py`, `scripts/testar_fixtures_localizacao.py`, `scripts/verificar_fila_nao_humana.py` |
| `carregar_cursor` | 3 | `monitorar_atos_resposta.py`, `monitorar_imprensa_regional.py`, `monitorar_imprensa_saude.py` |
