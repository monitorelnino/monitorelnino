# CODEMAP · o que cada arquivo afeta

**Gerado por `scripts/gerar_codemap.py` — não editar à mão.** O portão de frescor reprova se ele estiver desatualizado.

Serve a uma pergunta só: **por onde começar a ler** quando um pedido chega. Antes de explorar o repositório, consulte esta tabela e leia apenas o que ela lista para o que a tarefa toca.

**O que ele não é:** análise de dependência completa. Não segue `import` transitivo nem chamada dinâmica — é um índice de primeira ordem, tirado dos `fetch(...)`, dos `gravar(...)` e das listas de páginas dos portões. Para "por onde começo", basta; para "nada mais pode ser afetado", quem responde é o portão de runtime.

Atualizado em 01/10/2026.

| arquivo | telas que afeta | dados que usa | portões que o cobrem | toca o índice? |
|---|---|---|---|---|
| `blog.html` | blog.html | `blog/posts.json`, `estados.json`, `indice.json`, `meta.json`, `monitor_saude.json`, `municipios.json` (+3) | `verificar_acessibilidade.js`, `verificar_estrutura.js`, `verificar_fichas_semanticas.js`, `verificar_figuras.js`, `verificar_legendas.js`, `verificar_vocabulario_publico.js`, `verificar_voz_editorial.js` | não |
| `defesa-civil.html` | defesa-civil.html | `alertas/vigentes.json`, `cadastro_prioritarios_federal.json`, `geo_uf.json`, `meta.json`, `municipios_ibge_referencia.json`, `plano.json` (+9) | `verificar_acessibilidade.js`, `verificar_estrutura.js`, `verificar_fichas_semanticas.js`, `verificar_figuras.js`, `verificar_legendas.js`, `verificar_publicado_navegador.js`, `verificar_vocabulario_publico.js`, `verificar_voz_editorial.js` | não |
| `financiamento.html` | financiamento.html | `AC.json`, `AL.json`, `AM.json`, `AP.json`, `BA.json`, `CE.json` (+54) | `verificar_acessibilidade.js`, `verificar_ancoras_internas.py`, `verificar_estrutura.js`, `verificar_fichas_semanticas.js`, `verificar_figuras.js`, `verificar_legendas.js`, `verificar_publicado_navegador.js`, `verificar_vocabulario_publico.js`, `verificar_voz_editorial.js` | não |
| `imprensa.html` | imprensa.html | `calendario/dispositivos.json`, `imprensa/semana.json`, `indice.json`, `meta.json`, `monitor_saude.json`, `percentual_uf.json` (+2) | `verificar_acessibilidade.js`, `verificar_estrutura.js`, `verificar_fichas_semanticas.js`, `verificar_figuras.js`, `verificar_legendas.js`, `verificar_vocabulario_publico.js`, `verificar_voz_editorial.js` | não |
| `index.html` | index.html | `atos_resposta.json`, `chuvas.json`, `cobertura_qd.json`, `consist.json`, `enquadramento_card.json`, `estados.json` (+25) | `verificar_acessibilidade.js`, `verificar_estrutura.js`, `verificar_fichas_semanticas.js`, `verificar_figuras.js`, `verificar_legendas.js`, `verificar_publicado_navegador.js`, `verificar_vocabulario_publico.js`, `verificar_voz_editorial.js` | não |
| `monitor-de-riscos.html` | monitor-de-riscos.html | `.cartao-mapa-boletim.json`, `.figura-sub.json`, `.figura-titulo.json`, `AC.json`, `AL.json`, `AM.json` (+65) | `verificar_acessibilidade.js`, `verificar_estrutura.js`, `verificar_fichas_semanticas.js`, `verificar_figuras.js`, `verificar_legendas.js`, `verificar_vocabulario_publico.js`, `verificar_voz_editorial.js` | não |
| `obrigado.html` | obrigado.html | `publicacao.json` | `verificar_acessibilidade.js`, `verificar_estrutura.js`, `verificar_legendas.js`, `verificar_vocabulario_publico.js`, `verificar_voz_editorial.js` | não |
| `prefeituras.html` | prefeituras.html | `publicacao.json` | `verificar_acessibilidade.js`, `verificar_ancoras_internas.py`, `verificar_estrutura.js`, `verificar_fichas_semanticas.js`, `verificar_legendas.js`, `verificar_publicado_navegador.js`, `verificar_vocabulario_publico.js`, `verificar_voz_editorial.js` | não |
| `proteja-se.html` | proteja-se.html | `alertas/vigentes.json`, `contatos_uf.json`, `publicacao.json`, `saude_sinais.json`, `sinais_risco.json` | `verificar_acessibilidade.js`, `verificar_estrutura.js`, `verificar_fichas_semanticas.js`, `verificar_figuras.js`, `verificar_legendas.js`, `verificar_vocabulario_publico.js`, `verificar_voz_editorial.js` | não |
| `saude.html` | saude.html | `AC.json`, `AL.json`, `AM.json`, `AP.json`, `BA.json`, `CE.json` (+58) | `verificar_acessibilidade.js`, `verificar_estrutura.js`, `verificar_fichas_semanticas.js`, `verificar_figuras.js`, `verificar_legendas.js`, `verificar_publicado_navegador.js`, `verificar_vocabulario_publico.js`, `verificar_voz_editorial.js` | não |
| `assets/js/acesso.js` | blog.html, defesa-civil.html, financiamento.html, imprensa.html, index.html, monitor-de-riscos.html, obrigado.html, prefeituras.html, proteja-se.html, saude.html | `publicacao.json` | `verificar_acessibilidade.js`, `verificar_ancoras_internas.py`, `verificar_estrutura.js`, `verificar_fichas_semanticas.js`, `verificar_figuras.js`, `verificar_legendas.js`, `verificar_publicado_navegador.js`, `verificar_vocabulario_publico.js`, `verificar_voz_editorial.js` | não |
| `assets/js/blog.js` | blog.html | `blog/posts.json`, `estados.json`, `indice.json`, `meta.json`, `monitor_saude.json`, `municipios.json` (+2) | `verificar_acessibilidade.js`, `verificar_estrutura.js`, `verificar_fichas_semanticas.js`, `verificar_figuras.js`, `verificar_legendas.js`, `verificar_vocabulario_publico.js`, `verificar_voz_editorial.js` | não |
| `assets/js/colunas.js` | blog.html, defesa-civil.html, financiamento.html, imprensa.html, index.html, monitor-de-riscos.html, obrigado.html, prefeituras.html, proteja-se.html, saude.html | — | `verificar_acessibilidade.js`, `verificar_ancoras_internas.py`, `verificar_estrutura.js`, `verificar_fichas_semanticas.js`, `verificar_figuras.js`, `verificar_legendas.js`, `verificar_publicado_navegador.js`, `verificar_vocabulario_publico.js`, `verificar_voz_editorial.js` | não |
| `assets/js/defesa-civil.js` | defesa-civil.html | `alertas/vigentes.json`, `cadastro_prioritarios_federal.json`, `geo_uf.json`, `meta.json`, `municipios_ibge_referencia.json`, `plano.json` (+8) | `verificar_acessibilidade.js`, `verificar_estrutura.js`, `verificar_fichas_semanticas.js`, `verificar_figuras.js`, `verificar_legendas.js`, `verificar_publicado_navegador.js`, `verificar_vocabulario_publico.js`, `verificar_voz_editorial.js` | não |
| `assets/js/financiamento.js` | financiamento.html | `atos_resposta.json`, `declarado_nacional.json`, `financiamento/compromissos_federais.json`, `financiamento/consultas.json`, `financiamento/contadores_uf.json`, `financiamento/emendas.json` (+16) | `verificar_acessibilidade.js`, `verificar_ancoras_internas.py`, `verificar_estrutura.js`, `verificar_fichas_semanticas.js`, `verificar_figuras.js`, `verificar_legendas.js`, `verificar_publicado_navegador.js`, `verificar_vocabulario_publico.js`, `verificar_voz_editorial.js` | não |
| `assets/js/imprensa.js` | imprensa.html | `calendario/dispositivos.json`, `imprensa/semana.json`, `indice.json`, `meta.json`, `monitor_saude.json`, `percentual_uf.json` (+1) | `verificar_acessibilidade.js`, `verificar_estrutura.js`, `verificar_fichas_semanticas.js`, `verificar_figuras.js`, `verificar_legendas.js`, `verificar_vocabulario_publico.js`, `verificar_voz_editorial.js` | não |
| `assets/js/index.js` | index.html | `atos_resposta.json`, `chuvas.json`, `cobertura_qd.json`, `consist.json`, `enquadramento_card.json`, `estados.json` (+24) | `verificar_acessibilidade.js`, `verificar_estrutura.js`, `verificar_fichas_semanticas.js`, `verificar_figuras.js`, `verificar_legendas.js`, `verificar_publicado_navegador.js`, `verificar_vocabulario_publico.js`, `verificar_voz_editorial.js` | não |
| `assets/js/mapas.js` | blog.html, defesa-civil.html, financiamento.html, index.html, monitor-de-riscos.html, proteja-se.html, saude.html | — | `verificar_acessibilidade.js`, `verificar_ancoras_internas.py`, `verificar_estrutura.js`, `verificar_fichas_semanticas.js`, `verificar_figuras.js`, `verificar_legendas.js`, `verificar_publicado_navegador.js`, `verificar_vocabulario_publico.js`, `verificar_voz_editorial.js` | não |
| `assets/js/monitor-de-riscos.js` | monitor-de-riscos.html | `.cartao-mapa-boletim.json`, `.figura-sub.json`, `.figura-titulo.json`, `AC.json`, `AL.json`, `AM.json` (+48) | `verificar_acessibilidade.js`, `verificar_estrutura.js`, `verificar_fichas_semanticas.js`, `verificar_figuras.js`, `verificar_legendas.js`, `verificar_vocabulario_publico.js`, `verificar_voz_editorial.js` | não |
| `assets/js/obrigado.js` | obrigado.html | — | `verificar_acessibilidade.js`, `verificar_estrutura.js`, `verificar_legendas.js`, `verificar_vocabulario_publico.js`, `verificar_voz_editorial.js` | não |
| `assets/js/prefeituras.js` | prefeituras.html | — | `verificar_acessibilidade.js`, `verificar_ancoras_internas.py`, `verificar_estrutura.js`, `verificar_fichas_semanticas.js`, `verificar_legendas.js`, `verificar_publicado_navegador.js`, `verificar_vocabulario_publico.js`, `verificar_voz_editorial.js` | não |
| `assets/js/proteja-se.js` | proteja-se.html | `alertas/vigentes.json`, `contatos_uf.json`, `saude_sinais.json`, `sinais_risco.json` | `verificar_acessibilidade.js`, `verificar_estrutura.js`, `verificar_fichas_semanticas.js`, `verificar_figuras.js`, `verificar_legendas.js`, `verificar_vocabulario_publico.js`, `verificar_voz_editorial.js` | não |
| `assets/js/proveniencia.js` | financiamento.html, monitor-de-riscos.html, saude.html | `AC.json`, `AL.json`, `AM.json`, `AP.json`, `BA.json`, `CE.json` (+36) | `verificar_acessibilidade.js`, `verificar_ancoras_internas.py`, `verificar_estrutura.js`, `verificar_fichas_semanticas.js`, `verificar_figuras.js`, `verificar_legendas.js`, `verificar_publicado_navegador.js`, `verificar_vocabulario_publico.js`, `verificar_voz_editorial.js` | não |
| `assets/js/saude.js` | saude.html | `AC.json`, `AL.json`, `AM.json`, `AP.json`, `BA.json`, `CE.json` (+42) | `verificar_acessibilidade.js`, `verificar_estrutura.js`, `verificar_fichas_semanticas.js`, `verificar_figuras.js`, `verificar_legendas.js`, `verificar_publicado_navegador.js`, `verificar_vocabulario_publico.js`, `verificar_voz_editorial.js` | não |
| `analisar_decretos.py` | — | — | — | não |
| `analise_sensibilidade.py` | — | — | — | não |
| `aplicar_c10_imprensa.py` | — | — | — | não |
| `aplicar_promocoes_do_juiz.py` | — | — | — | SIM |
| `aplicar_revisao.py` | — | — | — | não |
| `atualizar.py` | — | — | — | não |
| `atualizar_boletins.py` | — | `boletins.json` | — | não |
| `atualizar_instrumentos_estaduais.py` | — | — | — | não |
| `atualizar_marcos_severidade.py` | — | — | — | não |
| `atualizar_populacao.py` | — | `populacao_censo2022.json` | — | não |
| `atualizar_recursos.py` | — | — | — | não |
| `atualizar_transferencias.py` | — | `transferencias_api_raw.json`, `transferencias_revisar.json` | — | não |
| `buscar_financiamento_preventivo.py` | — | — | — | não |
| `classificador_natureza.py` | — | — | — | não |
| `classificar_pista_civil.py` | — | `pistas_imprensa.json` | — | não |
| `classificar_planos_municipais.py` | — | `escada_municipal_revisar.json` | — | não |
| `classificar_saude_no_plano.py` | — | `saude_no_plano_auto.json`, `saude_no_plano_revisar.json` | — | não |
| `coletar_arboviroses_sinan.py` | — | — | — | não |
| `coletar_boletim_df_arboviroses.py` | — | `saude_desfechos/ses_df_arboviroses.json` | — | não |
| `coletar_boletim_ms_dengue.py` | — | `saude_desfechos/ses_ms_dengue.json` | — | não |
| `coletar_boletim_pb_arboviroses.py` | — | `saude_desfechos/ses_pb_arboviroses.json` | — | não |
| `coletar_boletim_pe_arboviroses.py` | — | `saude_desfechos/ses_pe_arboviroses.json` | — | não |
| `coletar_cadastro_prioritarios.py` | — | `cadastro_prioritarios_federal.json` | — | não |
| `coletar_cobertura_qd.py` | — | `cobertura_qd.json` | — | não |
| `coletar_dda.py` | — | `saude_desfechos/dda_serie.json` | — | não |
| `coletar_declarado_nacional.py` | — | `declarado_nacional.json`, `fontes_consultadas.json`, `fontes_declarado.json` | — | não |
| `coletar_desfechos_saude.py` | — | — | — | não |
| `coletar_diarios_consorciados.py` | — | `atos_resposta.json`, `pistas_imprensa.json` | — | não |
| `coletar_diarios_municipais.py` | — | `atos_resposta.json`, `cobertura_qd.json`, `pistas_imprensa.json`, `verificacao_municipal.json` | — | não |
| `coletar_doe.py` | — | `atos_resposta.json`, `fontes_doe.json`, `pistas_doe.json` | — | não |
| `coletar_espin.py` | — | `espin_revisar.json`, `saude_sinais.json` | — | não |
| `coletar_execucao_mps.py` | — | `financiamento/mps_2026.json` | — | não |
| `coletar_financiamento.py` | — | `financiamento_uf.json`, `recursos_uf.json` | — | não |
| `coletar_normais_inmet.py` | — | `normais_capitais.json` | — | não |
| `coletar_obitos_registro_civil.py` | — | `saude_desfechos/obitos_registro_civil.json` | — | não |
| `coletar_painel_am.py` | — | — | — | não |
| `coletar_prioritarios_mma.py` | — | `enquadramento_federal.json` | — | não |
| `coletar_s2id.py` | — | `atos_resposta.json` | — | não |
| `coletar_saude.py` | — | `saude_federal.json`, `saude_sinais.json`, `saude_uf.json` | — | não |
| `coletar_saude_estadual.py` | — | — | — | não |
| `coletar_semiarido_sudene.py` | — | `enquadramento_federal.json` | — | não |
| `coletar_sg_esus.py` | — | `saude_desfechos/sindrome_gripal_serie.json` | — | não |
| `coletar_siconfi_182.py` | — | `despesa_182.json` | — | não |
| `coletar_sinais_risco.py` | — | — | — | não |
| `coletar_srag_gripe.py` | — | `saude_desfechos/infogripe_diagnostico.json` | — | não |
| `coletar_srag_sivep.py` | — | `saude_desfechos/srag_serie.json` | — | não |
| `coletar_transferegov.py` | — | `financiamento/consultas.json`, `financiamento/por_uf.json`, `financiamento/programas_faf_2026.json`, `financiamento/serie_nacional.json`, `transferegov_el_nino_revisar.json` | — | não |
| `coletar_transferencias_municipais.py` | — | `transferencias_uniao.json` | — | não |
| `coletores_base.py` | — | `calendario/fontes_suspensas.json`, `evidencias.json`, `fontes_consultadas.json` | — | não |
| `consultar_querido_diario.py` | — | `pistas_querido_diario.json` | — | não |
| `converter_contribuicao.py` | — | — | — | SIM |
| `descobrir_dominios.py` | — | `dominios_oficiais.json` | — | não |
| `descobrir_planos.py` | — | `pistas_descobertas.json` | — | não |
| `detectar_marcos_federais.py` | — | `marcos_federais_saude.json`, `saude_uf.json` | — | não |
| `funil.py` | — | — | — | não |
| `gerar_blog.py` | — | — | — | não |
| `gerar_card_municipios.py` | — | `municipios_card.json` | — | não |
| `gerar_cobertura_declarada.py` | — | `cobertura_declarada_uf.json` | — | não |
| `gerar_contadores_financiamento.py` | — | `financiamento/contadores_uf.json` | — | não |
| `gerar_dados_abertos.py` | — | — | — | não |
| `gerar_erros_localizacao.py` | — | `erros_localizacao.json` | — | não |
| `gerar_feeds.py` | — | — | — | não |
| `gerar_imprensa_semana.py` | — | `semana.json` | — | não |
| `gerar_lai.py` | — | — | — | não |
| `gerar_monitor_saude.py` | — | `monitor_saude.json` | — | não |
| `gerar_monitor_saude_v04.py` | — | `monitor_saude_v04.json` | — | não |
| `gerar_painel.py` | — | `atos_resposta.json`, `municipios.json`, `verificacao_municipal.json` | — | não |
| `gerar_pdf_indice.py` | — | — | — | não |
| `gerar_pdf_metodologia.py` | — | — | — | não |
| `gerar_prioritarios.py` | — | `municipios_prioritarios.json` | — | não |
| `gerar_resposta.py` | — | `resposta/municipios.json`, `resposta/municipios_decretados.json`, `resposta/por_uf.json`, `resposta/serie_semanal.json` | — | SIM |
| `gerar_selos.py` | — | — | — | não |
| `juiz.py` | — | — | — | SIM |
| `julgar_e_aplicar_descobertas.py` | — | — | — | não |
| `julgar_filas.py` | — | — | — | não |
| `julgar_saude.py` | — | — | — | não |
| `migrar_saude_instrumentos.py` | — | — | — | não |
| `migrar_v224_verificacao.py` | — | `citacao_incompleta.json`, `erratas_v224.json`, `log_buscas.json`, `municipios.json`, `pontos_mapa.json` | — | não |
| `monitorar_atos_resposta.py` | — | — | — | não |
| `monitorar_busca_web.py` | — | `busca_web_espera.json`, `busca_web_estado.json`, `pistas_imprensa.json` | — | não |
| `monitorar_imprensa_regional.py` | — | — | — | não |
| `monitorar_imprensa_saude.py` | — | — | — | não |
| `monitorar_politica_por_inteiro.py` | — | `pistas_imprensa.json`, `pistas_sinais.json` | — | não |
| `monitorar_redes_oficiais.py` | — | `pistas_imprensa.json` | — | não |
| `monitorar_sinais_federais.py` | — | — | — | não |
| `motores_busca.py` | — | `busca_web_motores.json` | — | não |
| `pagina_completa.py` | — | — | — | não |
| `preencher_fallback_estatico.py` | — | — | — | não |
| `preservar_evidencias.py` | — | `evidencias.json`, `municipios.json` | — | não |
| `processar_contribuicoes.py` | — | — | — | não |
| `recalcular_mare.py` | — | — | — | SIM |
| `revisar_pistas.py` | — | `pistas_imprensa.json` | — | não |
| `saude_opendatasus.py` | — | — | — | não |
| `seguir_pistas.py` | — | `pistas_imprensa.json` | — | não |
| `sondar_paineis.py` | — | — | — | não |
| `triar_confianca_pistas.py` | — | `pistas_imprensa.json`, `pistas_revisao.json` | — | não |
| `verificar_consistencia.py` | — | — | — | não |
| `verificar_contribuicoes.py` | — | — | — | não |
| `verificar_evidencias.py` | — | — | — | não |
| `verificar_financiamento.py` | — | `financiamento/x.json` | — | não |
| `verificar_links.py` | — | — | — | não |
| `verificar_painel.py` | — | `painel/lista.json` | — | não |
| `verificar_pista_imprensa.py` | — | `veiculos_imprensa.json` | — | não |
| `verificar_recorrencia_uf.py` | — | — | — | não |
| `verificar_resposta.py` | — | — | — | não |
| `verificar_saude.py` | — | — | — | não |
| `verificar_sinais.py` | — | — | — | não |
| `verificar_vigencia.py` | — | `municipios.json` | — | não |
