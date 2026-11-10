# Medida do código

Gerado por `python3 scripts/medir_codigo.py --gravar`. Linha de base da consolidação (meta: ≤ 50 mil linhas de .py/.js, mesma proteção).

- **101.535 linhas** em **299 arquivos** .py/.js; **38 workflows**.
- **66 comandos de portão**: dados/portão 19, paginas/autoteste 2, paginas/portão 45.
- **158 nomes de função** definidos em mais de um arquivo.

## Por pasta

| pasta | linhas |
|---|---:|
| `(raiz)` | 58041 |
| `scripts` | 36374 |
| `assets` | 6548 |
| `arquivo` | 304 |
| `.claude` | 268 |

## Os 25 maiores

| arquivo | linhas |
|---|---:|
| `coletar_sinais_risco.py` | 3344 |
| `coletores_base.py` | 2276 |
| `juiz.py` | 1976 |
| `coletar_doe.py` | 1717 |
| `verificar_pista_imprensa.py` | 1705 |
| `julgar_saude.py` | 1518 |
| `scripts/verificar_regras_de_dado.py` | 1365 |
| `assets/js/monitor-de-riscos.js` | 1331 |
| `scripts/unir_conflito_de_rodada.py` | 1318 |
| `scripts/ensaio_da_noite.py` | 1274 |
| `coletar_edicoes_doe.py` | 1264 |
| `descobrir_planos.py` | 1251 |
| `assets/js/index.js` | 1236 |
| `coletar_painel_am.py` | 1135 |
| `gerar_imprensa_semana.py` | 1116 |
| `julgar_e_aplicar_descobertas.py` | 1069 |
| `recalcular_mare.py` | 1064 |
| `coletar_diarios_consorciados.py` | 1040 |
| `gerar_pacote_blog.py` | 913 |
| `julgar_filas.py` | 857 |
| `scripts/pistas.py` | 782 |
| `scripts/verificar_repositorio.py` | 772 |
| `coletar_s2id.py` | 762 |
| `monitorar_busca_web.py` | 755 |
| `buscar_planos_fontes_abertas.py` | 753 |

## Funções de mesmo nome em arquivos distintos (as 40 mais repetidas)

| função | arquivos | onde |
|---|---:|---|
| `coletar` | 28 | `buscar_protocolo_calor.py`, `coletar_boletim_df_arboviroses.py`, `coletar_boletim_ms_dengue.py`, `coletar_boletim_pb_arboviroses.py` … |
| `problemas` | 18 | `coletar_cadastro_prioritarios.py`, `coletar_normais_inmet.py`, `coletar_prioritarios_mma.py`, `coletar_risco_base.py` … |
| `self_test` | 15 | `atualizar_marcos_severidade.py`, `classificador_natureza.py`, `detectar_marcos_federais.py`, `gerar_dados_abertos.py` … |
| `gerar` | 14 | `classificar_planos_municipais.py`, `gerar_blog.py`, `gerar_card_municipios.py`, `gerar_contadores_financiamento.py` … |
| `montar` | 12 | `buscar_protocolo_calor.py`, `desfechos_sus.py`, `gerar_card_municipios.py`, `gerar_financiamento_semana.py` … |
| `classificar` | 11 | `classificador_natureza.py`, `classificar_planos_municipais.py`, `classificar_saude_no_plano.py`, `coletar_desfechos_saude.py` … |
| `registrar` | 9 | `descobrir_planos.py`, `funil.py`, `gerar_lai.py`, `monitorar_imprensa_regional.py` … |
| `normalizar` | 8 | `classificar_pista_civil.py`, `classificar_planos_municipais.py`, `coletar_normais_inmet.py`, `coletar_sinais_risco.py` … |
| `sondar` | 8 | `coletar_datasus_dbc.py`, `coletar_obitos.py`, `coletar_sg_esus.py`, `coletar_sih.py` … |
| `__load` | 7 | `arquivo/pesquisadores/pesquisadores.js`, `assets/js/defesa-civil.js`, `assets/js/financiamento.js`, `assets/js/index.js` … |
| `_get` | 7 | `consultar_querido_diario.py`, `detectar_marcos_federais.py`, `monitorar_imprensa_regional.py`, `monitorar_imprensa_saude.py` … |
| `_norm` | 6 | `coletar_boletim_pe_arboviroses.py`, `coletar_painel_am.py`, `coletar_s2id.py`, `scripts/municipio_do_dominio.py` … |
| `_plano` | 6 | `classificar_saude_no_plano.py`, `coletar_dda.py`, `coletar_srag_gripe.py`, `coletar_transferegov.py` … |
| `carregar` | 6 | `aplicar_revisao.py`, `scripts/testar_ordem_prioridade_ufs.py`, `scripts/validar_dicionario.py`, `verificar_financiamento.py` … |
| `_data` | 5 | `gerar_financiamento_semana.py`, `scripts/janela_de_deploy.py`, `scripts/verificar_frescor.py`, `scripts/verificar_regras_de_dado.py` … |
| `agregar` | 5 | `coletar_datasus_dbc.py`, `coletar_execucao_mps.py`, `coletar_sih.py`, `coletar_sim.py` … |
| `carregar_fila` | 5 | `descobrir_planos.py`, `monitorar_imprensa_regional.py`, `monitorar_imprensa_saude.py`, `monitorar_sinais_federais.py` … |
| `decidir` | 5 | `coletar_saude_estadual.py`, `coletar_sg_esus.py`, `monitorar_busca_web.py`, `scripts/janela_de_deploy.py` … |
| `medir` | 5 | `scripts/cobertura_docstrings.py`, `scripts/diagnostico_fontes_saude.py`, `scripts/medir_codigo.py`, `scripts/medir_revocacao_das_consultas.py` … |
| `norm` | 5 | `atualizar_instrumentos_estaduais.py`, `converter_contribuicao.py`, `processar_contribuicoes.py`, `scripts/fila_do_juiz_querido_diario.py` … |
| `relatorio` | 5 | `coletar_cobertura_qd.py`, `scripts/busca_dirigida_do_ato.py`, `scripts/fechar_saude.py`, `scripts/medir_codigo.py` … |
| `__init` | 4 | `assets/js/defesa-civil.js`, `assets/js/financiamento.js`, `assets/js/index.js`, `assets/js/monitor-de-riscos.js` |
| `_git` | 4 | `scripts/commit_do_elo.py`, `scripts/verificar_idempotencia_dos_derivados.py`, `scripts/verificar_repositorio.py`, `scripts/verificar_tamanho_dos_dados.py` |
| `_host` | 4 | `buscar_planos_fontes_abertas.py`, `gerar_card_municipios.py`, `scripts/municipio_do_dominio.py`, `triar_confianca_pistas.py` |
| `_sem_acento` | 4 | `revisar_pistas.py`, `scripts/pistas.py`, `scripts/validar_dicionario.py`, `scripts/vocabulario.py` |
| `aplicar` | 4 | `julgar_saude.py`, `scripts/aplicar_edicoes.py`, `scripts/provar_mutacoes_dos_portoes.py`, `scripts/tipo_de_evento_dos_atos.py` |
| `conferir` | 4 | `reconferir_instrumentos_federais.py`, `scripts/gerar_saude_pipeline.py`, `scripts/verificar_funil.py`, `scripts/verificar_texto_blog.py` |
| `data_br` | 4 | `coletar_transferegov.py`, `gerar_resposta.py`, `scripts/cruzar_ocp_com_atos.py`, `scripts/gerar_mudancas.py` |
| `faixa` | 4 | `gerar_dados_abertos.py`, `gerar_monitor_saude.py`, `gerar_selos.py`, `robustez_saude.py` |
| `fundir` | 4 | `coletar_prioritarios_mma.py`, `coletar_recursos_resposta.py`, `coletar_semiarido_sudene.py`, `coletar_transferencias_municipais.py` |
| `numero` | 4 | `coletar_execucao_mps.py`, `coletar_transferegov.py`, `scripts/cruzar_ocp_com_atos.py`, `scripts/ingerir_ocp_midr.py` |
| `parse_texto` | 4 | `coletar_boletim_df_arboviroses.py`, `coletar_boletim_ms_dengue.py`, `coletar_boletim_pb_arboviroses.py`, `coletar_boletim_pe_arboviroses.py` |
| `renderizar` | 4 | `coletar_painel_am.py`, `gerar_feeds.py`, `scripts/_inline_js.js`, `scripts/renderizar_figura.py` |
| `semear` | 4 | `coletar_financiamento.py`, `coletar_saude.py`, `coletar_sinais_risco.py`, `scripts/semear_candidatos_de_plano.py` |
| `tabela` | 4 | `assets/js/financiamento.js`, `gerar_pdf_indice.py`, `scripts/gerar_saude_pipeline.py`, `scripts/medir_revocacao_das_consultas.py` |
| `_iso` | 3 | `coletar_sinais_risco.py`, `gerar_dados_abertos.py`, `scripts/checagem_pre_noite.py` |
| `_levanta` | 3 | `buscar_planos_fontes_abertas.py`, `coletar_transferencias_municipais.py`, `scripts/testar_busca_dou.py` |
| `_n` | 3 | `coletar_boletim_df_arboviroses.py`, `coletar_boletim_pb_arboviroses.py`, `coletar_boletim_pe_arboviroses.py` |
| `checar` | 3 | `verificar_financiamento.py`, `verificar_painel.py`, `verificar_saude.py` |
| `classificar_tipo` | 3 | `coletar_sinais_risco.py`, `migrar_saude_instrumentos.py`, `scripts/pistas.py` |
