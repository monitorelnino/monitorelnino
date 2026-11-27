# Medida do código

Gerado por `python3 scripts/medir_codigo.py --gravar`. Linha de base da consolidação (meta: ≤ 50 mil linhas de .py/.js, mesma proteção).

- **107.942 linhas** em **306 arquivos** .py/.js; **42 workflows**.
- **65 comandos de portão**: dados/portão 19, paginas/autoteste 2, paginas/portão 44.
- **163 nomes de função** definidos em mais de um arquivo.

## Por pasta

| pasta | linhas |
|---|---:|
| `(raiz)` | 62807 |
| `scripts` | 38146 |
| `assets` | 6721 |
| `.claude` | 268 |

## Os 25 maiores

| arquivo | linhas |
|---|---:|
| `coletar_sinais_risco.py` | 3252 |
| `juiz.py` | 2666 |
| `coletores_base.py` | 2555 |
| `verificar_pista_imprensa.py` | 1705 |
| `coletar_doe.py` | 1661 |
| `julgar_saude.py` | 1602 |
| `scripts/unir_conflito_de_rodada.py` | 1515 |
| `scripts/ensaio_da_noite.py` | 1450 |
| `assets/js/monitor-de-riscos.js` | 1443 |
| `descobrir_planos.py` | 1416 |
| `scripts/verificar_regras_de_dado.py` | 1400 |
| `coletar_edicoes_doe.py` | 1372 |
| `julgar_e_aplicar_descobertas.py` | 1354 |
| `assets/js/index.js` | 1250 |
| `coletar_painel_am.py` | 1154 |
| `gerar_imprensa_semana.py` | 1116 |
| `recalcular_mare.py` | 1086 |
| `coletar_diarios_consorciados.py` | 1040 |
| `julgar_filas.py` | 1040 |
| `aplicar_promocoes_do_juiz.py` | 1027 |
| `gerar_pacote_blog.py` | 913 |
| `coletar_s2id.py` | 876 |
| `scripts/pistas.py` | 867 |
| `assets/js/saude.js` | 785 |
| `buscar_planos_fontes_abertas.py` | 783 |

## Funções de mesmo nome em arquivos distintos (as 40 mais repetidas)

| função | arquivos | onde |
|---|---:|---|
| `coletar` | 28 | `buscar_protocolo_calor.py`, `coletar_boletim_df_arboviroses.py`, `coletar_boletim_ms_dengue.py`, `coletar_boletim_pb_arboviroses.py` … |
| `problemas` | 20 | `coletar_cadastro_prioritarios.py`, `coletar_normais_inmet.py`, `coletar_pab_brasil.py`, `coletar_prioritarios_mma.py` … |
| `self_test` | 14 | `classificador_natureza.py`, `detectar_marcos_federais.py`, `gerar_dados_abertos.py`, `gerar_feeds.py` … |
| `gerar` | 13 | `classificar_planos_municipais.py`, `gerar_card_municipios.py`, `gerar_contadores_financiamento.py`, `gerar_dados_abertos.py` … |
| `montar` | 12 | `buscar_protocolo_calor.py`, `desfechos_sus.py`, `gerar_card_municipios.py`, `gerar_financiamento_semana.py` … |
| `classificar` | 11 | `classificador_natureza.py`, `classificar_planos_municipais.py`, `classificar_saude_no_plano.py`, `coletar_desfechos_saude.py` … |
| `registrar` | 9 | `descobrir_planos.py`, `funil.py`, `gerar_lai.py`, `monitorar_imprensa_regional.py` … |
| `normalizar` | 8 | `classificar_pista_civil.py`, `classificar_planos_municipais.py`, `coletar_normais_inmet.py`, `coletar_sinais_risco.py` … |
| `sondar` | 8 | `coletar_datasus_dbc.py`, `coletar_obitos.py`, `coletar_sg_esus.py`, `coletar_sih.py` … |
| `_get` | 7 | `consultar_querido_diario.py`, `detectar_marcos_federais.py`, `monitorar_imprensa_regional.py`, `monitorar_imprensa_saude.py` … |
| `__load` | 6 | `assets/js/defesa-civil.js`, `assets/js/financiamento.js`, `assets/js/index.js`, `assets/js/monitor-de-riscos.js` … |
| `_data` | 6 | `gerar_financiamento_semana.py`, `scripts/janela_de_deploy.py`, `scripts/verificar_frescor.py`, `scripts/verificar_leituras_paradas.py` … |
| `_norm` | 6 | `coletar_boletim_pe_arboviroses.py`, `coletar_painel_am.py`, `coletar_s2id.py`, `scripts/municipio_do_dominio.py` … |
| `_plano` | 6 | `classificar_saude_no_plano.py`, `coletar_dda.py`, `coletar_srag_gripe.py`, `coletar_transferegov.py` … |
| `carregar` | 6 | `aplicar_revisao.py`, `scripts/testar_ordem_prioridade_ufs.py`, `scripts/validar_dicionario.py`, `verificar_financiamento.py` … |
| `decidir` | 6 | `buscar_financiamento_preventivo.py`, `coletar_saude_estadual.py`, `coletar_sg_esus.py`, `monitorar_busca_web.py` … |
| `_host` | 5 | `buscar_planos_fontes_abertas.py`, `gerar_card_municipios.py`, `scripts/municipio_do_dominio.py`, `scripts/ponte_brasil.py` … |
| `agregar` | 5 | `coletar_datasus_dbc.py`, `coletar_execucao_mps.py`, `coletar_sih.py`, `coletar_sim.py` … |
| `avisar` | 5 | `conferir_emergencias_estaduais.py`, `scripts/avisos.py`, `scripts/checagem_pre_noite.py`, `scripts/selo_da_main.py` … |
| `carregar_fila` | 5 | `descobrir_planos.py`, `monitorar_imprensa_regional.py`, `monitorar_imprensa_saude.py`, `monitorar_sinais_federais.py` … |
| `fundir` | 5 | `coletar_pab_brasil.py`, `coletar_prioritarios_mma.py`, `coletar_recursos_resposta.py`, `coletar_semiarido_sudene.py` … |
| `medir` | 5 | `scripts/cobertura_docstrings.py`, `scripts/diagnostico_fontes_saude.py`, `scripts/medir_codigo.py`, `scripts/medir_revocacao_das_consultas.py` … |
| `norm` | 5 | `atualizar_instrumentos_estaduais.py`, `converter_contribuicao.py`, `processar_contribuicoes.py`, `scripts/fila_do_juiz_querido_diario.py` … |
| `relatorio` | 5 | `coletar_cobertura_qd.py`, `scripts/busca_dirigida_do_ato.py`, `scripts/fechar_saude.py`, `scripts/medir_codigo.py` … |
| `__init` | 4 | `assets/js/defesa-civil.js`, `assets/js/financiamento.js`, `assets/js/index.js`, `assets/js/monitor-de-riscos.js` |
| `_git` | 4 | `scripts/commit_do_elo.py`, `scripts/verificar_idempotencia_dos_derivados.py`, `scripts/verificar_repositorio.py`, `scripts/verificar_tamanho_dos_dados.py` |
| `_levanta` | 4 | `buscar_planos_fontes_abertas.py`, `coletar_pab_brasil.py`, `coletar_transferencias_municipais.py`, `scripts/testar_busca_dou.py` |
| `_sem_acento` | 4 | `revisar_pistas.py`, `scripts/pistas.py`, `scripts/validar_dicionario.py`, `scripts/vocabulario.py` |
| `conferir` | 4 | `reconferir_instrumentos_federais.py`, `scripts/gerar_saude_pipeline.py`, `scripts/verificar_funil.py`, `scripts/verificar_texto_blog.py` |
| `data_br` | 4 | `coletar_transferegov.py`, `gerar_resposta.py`, `scripts/cruzar_ocp_com_atos.py`, `scripts/gerar_mudancas.py` |
| `faixa` | 4 | `gerar_dados_abertos.py`, `gerar_monitor_saude.py`, `gerar_selos.py`, `robustez_saude.py` |
| `numero` | 4 | `coletar_execucao_mps.py`, `coletar_transferegov.py`, `scripts/cruzar_ocp_com_atos.py`, `scripts/ingerir_ocp_midr.py` |
| `parse_texto` | 4 | `coletar_boletim_df_arboviroses.py`, `coletar_boletim_ms_dengue.py`, `coletar_boletim_pb_arboviroses.py`, `coletar_boletim_pe_arboviroses.py` |
| `renderizar` | 4 | `coletar_painel_am.py`, `gerar_feeds.py`, `scripts/_inline_js.js`, `scripts/renderizar_figura.py` |
| `semear` | 4 | `coletar_financiamento.py`, `coletar_saude.py`, `coletar_sinais_risco.py`, `scripts/semear_candidatos_de_plano.py` |
| `tabela` | 4 | `assets/js/financiamento.js`, `gerar_pdf_indice.py`, `scripts/gerar_saude_pipeline.py`, `scripts/medir_revocacao_das_consultas.py` |
| `_iso` | 3 | `coletar_sinais_risco.py`, `gerar_dados_abertos.py`, `scripts/checagem_pre_noite.py` |
| `_n` | 3 | `coletar_boletim_df_arboviroses.py`, `coletar_boletim_pb_arboviroses.py`, `coletar_boletim_pe_arboviroses.py` |
| `aplicar` | 3 | `julgar_saude.py`, `scripts/aplicar_edicoes.py`, `scripts/provar_mutacoes_dos_portoes.py` |
| `checar` | 3 | `verificar_financiamento.py`, `verificar_painel.py`, `verificar_saude.py` |
