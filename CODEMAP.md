# CODEMAP · o que cada arquivo afeta

**Gerado por `scripts/gerar_codemap.py` — não editar à mão.** O portão de frescor reprova se ele estiver desatualizado.

Serve a uma pergunta só: **por onde começar a ler** quando um pedido chega. Antes de explorar o repositório, consulte esta tabela e leia apenas o que ela lista para o que a tarefa toca.

**O que ele não é:** análise de dependência completa. Não segue `import` transitivo nem chamada dinâmica — é um índice de primeira ordem, tirado dos `fetch(...)`, dos `gravar(...)` e das listas de páginas dos portões. Para "por onde começo", basta; para "nada mais pode ser afetado", quem responde é o portão de runtime.

**Regra de página: contrato + componentes** (editoria, 02/10/2026). A forma de uma página não vive no HTML: vive em `layout/contratos/<pagina>.json`, que declara seções, ordem, cartões, grades e texto proibido. O HTML e o JavaScript se conformam ao contrato, e `scripts/verificar_layout.py` reprova a divergência — nenhum PR de página com contrato é mesclado com ele vermelho. Cartão de número é `.cartao-numero` em `.grade-numeros--3`; figura é `.cartao-mapa` em `.grade-figuras--3`; nada de ajuste de pixel por cartão.

Atualizado em 09/10/2026.

**A coluna `importado por`** (05/10/2026) diz quantos arquivos do repositório importam aquele — é a resposta curta para "o que a minha mudança alcança". Ela não substitui o portão de runtime, mas evita a surpresa: `coletores_base.py` tem 169 importadores, e os dois acidentes de isolamento de 02 e 05/10 custaram 907 atos e seis execuções de log por mexer ali sem ver esse número.

| arquivo | telas que afeta | dados que usa | portões que o cobrem | importado por | toca o índice? |
|---|---|---|---|---|---|
| `blog.html` | blog.html | `blog/posts.json`, `publicacao.json` | `verificar_acessibilidade.js`, `verificar_estrutura.js`, `verificar_fichas_semanticas.js`, `verificar_figuras.js`, `verificar_legendas.js`, `verificar_vocabulario_publico.js`, `verificar_voz_editorial.js` | — | não |
| `defesa-civil.html` | defesa-civil.html | `Desde.json`, `Município.json`, `Nível.json`, `Tipo.json`, `UF.json`, `alertas/vigentes.json` (+27) | `verificar_acessibilidade.js`, `verificar_estrutura.js`, `verificar_fichas_semanticas.js`, `verificar_figuras.js`, `verificar_legendas.js`, `verificar_publicado_navegador.js`, `verificar_vocabulario_publico.js`, `verificar_voz_editorial.js` | — | não |
| `financiamento.html` | financiamento.html | `AC.json`, `AL.json`, `AM.json`, `AP.json`, `BA.json`, `CE.json` (+54) | `verificar_acessibilidade.js`, `verificar_ancoras_internas.py`, `verificar_estrutura.js`, `verificar_fichas_semanticas.js`, `verificar_figuras.js`, `verificar_legendas.js`, `verificar_publicado_navegador.js`, `verificar_vocabulario_publico.js`, `verificar_voz_editorial.js` | — | não |
| `imprensa.html` | imprensa.html | `cadencia_publicacao.json`, `meta.json`, `monitor_saude.json`, `publicacao.json` | `verificar_acessibilidade.js`, `verificar_estrutura.js`, `verificar_fichas_semanticas.js`, `verificar_figuras.js`, `verificar_legendas.js`, `verificar_vocabulario_publico.js`, `verificar_voz_editorial.js` | — | não |
| `index.html` | index.html | `atos_resposta.json`, `chuvas.json`, `cobertura_qd.json`, `consist.json`, `enquadramento_card.json`, `estados.json` (+25) | `verificar_acessibilidade.js`, `verificar_estrutura.js`, `verificar_fichas_semanticas.js`, `verificar_figuras.js`, `verificar_legendas.js`, `verificar_publicado_navegador.js`, `verificar_vocabulario_publico.js`, `verificar_voz_editorial.js` | — | não |
| `indice-de-conteudo.html` | indice-de-conteudo.html | — | — | — | não |
| `monitor-de-riscos.html` | monitor-de-riscos.html | `AC.json`, `AL.json`, `AM.json`, `AP.json`, `BA.json`, `CE.json` (+62) | `verificar_acessibilidade.js`, `verificar_estrutura.js`, `verificar_fichas_semanticas.js`, `verificar_figuras.js`, `verificar_legendas.js`, `verificar_vocabulario_publico.js`, `verificar_voz_editorial.js` | — | não |
| `mudancas.html` | mudancas.html | `blog/posts.json`, `publicacao.json` | — | — | não |
| `obrigado.html` | obrigado.html | `publicacao.json` | `verificar_acessibilidade.js`, `verificar_estrutura.js`, `verificar_legendas.js`, `verificar_vocabulario_publico.js`, `verificar_voz_editorial.js` | — | não |
| `prefeituras.html` | prefeituras.html | `publicacao.json` | `verificar_acessibilidade.js`, `verificar_ancoras_internas.py`, `verificar_estrutura.js`, `verificar_fichas_semanticas.js`, `verificar_legendas.js`, `verificar_publicado_navegador.js`, `verificar_vocabulario_publico.js`, `verificar_voz_editorial.js` | — | não |
| `proteja-se.html` | proteja-se.html | `alertas/vigentes.json`, `contatos_uf.json`, `publicacao.json`, `saude_sinais.json`, `sinais_risco.json` | `verificar_acessibilidade.js`, `verificar_estrutura.js`, `verificar_fichas_semanticas.js`, `verificar_figuras.js`, `verificar_legendas.js`, `verificar_vocabulario_publico.js`, `verificar_voz_editorial.js` | — | não |
| `saude.html` | saude.html | `AC.json`, `AL.json`, `AM.json`, `AP.json`, `BA.json`, `CE.json` (+57) | `verificar_acessibilidade.js`, `verificar_estrutura.js`, `verificar_fichas_semanticas.js`, `verificar_figuras.js`, `verificar_legendas.js`, `verificar_publicado_navegador.js`, `verificar_vocabulario_publico.js`, `verificar_voz_editorial.js` | — | não |
| `assets/acesso.js` | blog.html, defesa-civil.html, financiamento.html, imprensa.html, index.html, monitor-de-riscos.html, mudancas.html, obrigado.html, prefeituras.html, proteja-se.html, saude.html | `publicacao.json` | `verificar_acessibilidade.js`, `verificar_ancoras_internas.py`, `verificar_estrutura.js`, `verificar_fichas_semanticas.js`, `verificar_figuras.js`, `verificar_legendas.js`, `verificar_publicado_navegador.js`, `verificar_vocabulario_publico.js`, `verificar_voz_editorial.js` | — | não |
| `assets/js/blog.js` | blog.html, mudancas.html | `blog/posts.json` | `verificar_acessibilidade.js`, `verificar_estrutura.js`, `verificar_fichas_semanticas.js`, `verificar_figuras.js`, `verificar_legendas.js`, `verificar_vocabulario_publico.js`, `verificar_voz_editorial.js` | — | não |
| `assets/catalogo.js` | blog.html, defesa-civil.html, financiamento.html, imprensa.html, monitor-de-riscos.html, mudancas.html | — | `verificar_acessibilidade.js`, `verificar_ancoras_internas.py`, `verificar_estrutura.js`, `verificar_fichas_semanticas.js`, `verificar_figuras.js`, `verificar_legendas.js`, `verificar_publicado_navegador.js`, `verificar_vocabulario_publico.js`, `verificar_voz_editorial.js` | — | não |
| `assets/colunas.js` | blog.html, defesa-civil.html, financiamento.html, imprensa.html, index.html, monitor-de-riscos.html, mudancas.html, obrigado.html, prefeituras.html, proteja-se.html, saude.html | — | `verificar_acessibilidade.js`, `verificar_ancoras_internas.py`, `verificar_estrutura.js`, `verificar_fichas_semanticas.js`, `verificar_figuras.js`, `verificar_legendas.js`, `verificar_publicado_navegador.js`, `verificar_vocabulario_publico.js`, `verificar_voz_editorial.js` | — | não |
| `assets/js/defesa-civil.js` | defesa-civil.html | `Desde.json`, `Município.json`, `Nível.json`, `Tipo.json`, `UF.json`, `alertas/vigentes.json` (+26) | `verificar_acessibilidade.js`, `verificar_estrutura.js`, `verificar_fichas_semanticas.js`, `verificar_figuras.js`, `verificar_legendas.js`, `verificar_publicado_navegador.js`, `verificar_vocabulario_publico.js`, `verificar_voz_editorial.js` | — | não |
| `assets/js/financiamento.js` | financiamento.html | `atos_resposta.json`, `financiamento/caminhos.json`, `financiamento/compromissos_federais.json`, `financiamento/consultas.json`, `financiamento/contadores_uf.json`, `financiamento/emendas.json` (+16) | `verificar_acessibilidade.js`, `verificar_ancoras_internas.py`, `verificar_estrutura.js`, `verificar_fichas_semanticas.js`, `verificar_figuras.js`, `verificar_legendas.js`, `verificar_publicado_navegador.js`, `verificar_vocabulario_publico.js`, `verificar_voz_editorial.js` | — | não |
| `assets/js/grade-estados.js` | index.html, saude.html | — | `verificar_acessibilidade.js`, `verificar_estrutura.js`, `verificar_fichas_semanticas.js`, `verificar_figuras.js`, `verificar_legendas.js`, `verificar_publicado_navegador.js`, `verificar_vocabulario_publico.js`, `verificar_voz_editorial.js` | — | não |
| `assets/js/imprensa.js` | imprensa.html | `cadencia_publicacao.json`, `meta.json`, `monitor_saude.json` | `verificar_acessibilidade.js`, `verificar_estrutura.js`, `verificar_fichas_semanticas.js`, `verificar_figuras.js`, `verificar_legendas.js`, `verificar_vocabulario_publico.js`, `verificar_voz_editorial.js` | — | não |
| `assets/js/index.js` | index.html | `atos_resposta.json`, `chuvas.json`, `cobertura_qd.json`, `consist.json`, `enquadramento_card.json`, `estados.json` (+24) | `verificar_acessibilidade.js`, `verificar_estrutura.js`, `verificar_fichas_semanticas.js`, `verificar_figuras.js`, `verificar_legendas.js`, `verificar_publicado_navegador.js`, `verificar_vocabulario_publico.js`, `verificar_voz_editorial.js` | — | não |
| `assets/mapas.js` | blog.html, defesa-civil.html, financiamento.html, index.html, monitor-de-riscos.html, mudancas.html, proteja-se.html, saude.html | — | `verificar_acessibilidade.js`, `verificar_ancoras_internas.py`, `verificar_estrutura.js`, `verificar_fichas_semanticas.js`, `verificar_figuras.js`, `verificar_legendas.js`, `verificar_publicado_navegador.js`, `verificar_vocabulario_publico.js`, `verificar_voz_editorial.js` | — | não |
| `assets/js/monitor-de-riscos.js` | monitor-de-riscos.html | `AC.json`, `AL.json`, `AM.json`, `AP.json`, `BA.json`, `CE.json` (+45) | `verificar_acessibilidade.js`, `verificar_estrutura.js`, `verificar_fichas_semanticas.js`, `verificar_figuras.js`, `verificar_legendas.js`, `verificar_vocabulario_publico.js`, `verificar_voz_editorial.js` | — | não |
| `assets/js/obrigado.js` | obrigado.html | — | `verificar_acessibilidade.js`, `verificar_estrutura.js`, `verificar_legendas.js`, `verificar_vocabulario_publico.js`, `verificar_voz_editorial.js` | — | não |
| `assets/js/prefeituras.js` | prefeituras.html | — | `verificar_acessibilidade.js`, `verificar_ancoras_internas.py`, `verificar_estrutura.js`, `verificar_fichas_semanticas.js`, `verificar_legendas.js`, `verificar_publicado_navegador.js`, `verificar_vocabulario_publico.js`, `verificar_voz_editorial.js` | — | não |
| `assets/js/proteja-se.js` | proteja-se.html | `alertas/vigentes.json`, `contatos_uf.json`, `saude_sinais.json`, `sinais_risco.json` | `verificar_acessibilidade.js`, `verificar_estrutura.js`, `verificar_fichas_semanticas.js`, `verificar_figuras.js`, `verificar_legendas.js`, `verificar_vocabulario_publico.js`, `verificar_voz_editorial.js` | — | não |
| `assets/js/proveniencia.js` | financiamento.html, monitor-de-riscos.html, saude.html | `AC.json`, `AL.json`, `AM.json`, `AP.json`, `BA.json`, `CE.json` (+36) | `verificar_acessibilidade.js`, `verificar_ancoras_internas.py`, `verificar_estrutura.js`, `verificar_fichas_semanticas.js`, `verificar_figuras.js`, `verificar_legendas.js`, `verificar_publicado_navegador.js`, `verificar_vocabulario_publico.js`, `verificar_voz_editorial.js` | — | não |
| `assets/js/saude.js` | saude.html | `AC.json`, `AL.json`, `AM.json`, `AP.json`, `BA.json`, `CE.json` (+42) | `verificar_acessibilidade.js`, `verificar_estrutura.js`, `verificar_fichas_semanticas.js`, `verificar_figuras.js`, `verificar_legendas.js`, `verificar_publicado_navegador.js`, `verificar_vocabulario_publico.js`, `verificar_voz_editorial.js` | — | não |
| `_p3.py` | — | — | — | — | não |
| `_p4.py` | — | — | — | — | não |
| `_p5.py` | — | — | — | — | não |
| `analisar_decretos.py` | — | — | — | — | não |
| `analise_sensibilidade.py` | — | — | — | 2 | não |
| `aplicar_c10_imprensa.py` | — | — | — | — | não |
| `aplicar_promocoes_do_juiz.py` | — | — | — | 1 | SIM |
| `aplicar_revisao.py` | — | — | — | — | não |
| `atualizar.py` | — | — | — | — | não |
| `atualizar_boletins.py` | — | `boletins.json` | — | — | não |
| `atualizar_instrumentos_estaduais.py` | — | — | — | — | não |
| `atualizar_marcos_severidade.py` | — | — | — | — | não |
| `atualizar_populacao.py` | — | `populacao_censo2022.json` | — | — | não |
| `atualizar_recursos.py` | — | — | — | — | não |
| `atualizar_transferencias.py` | — | `transferencias_api_raw.json`, `transferencias_revisar.json` | — | — | não |
| `buscar_financiamento_preventivo.py` | — | — | — | — | não |
| `classificador_natureza.py` | — | — | — | 4 | não |
| `classificar_pista_civil.py` | — | `pistas_imprensa.json` | — | 5 | não |
| `classificar_planos_municipais.py` | — | `escada_municipal_revisar.json` | — | — | não |
| `classificar_saude_no_plano.py` | — | `saude_no_plano_auto.json`, `saude_no_plano_revisar.json` | — | — | não |
| `coletar_arboviroses_sinan.py` | — | `saude_desfechos/arboviroses_sinan_agregados.json` | — | — | não |
| `coletar_boletim_df_arboviroses.py` | — | `saude_desfechos/ses_df_arboviroses.json` | — | — | não |
| `coletar_boletim_ms_dengue.py` | — | `saude_desfechos/ses_ms_dengue.json` | — | — | não |
| `coletar_boletim_pb_arboviroses.py` | — | `saude_desfechos/ses_pb_arboviroses.json` | — | — | não |
| `coletar_boletim_pe_arboviroses.py` | — | `saude_desfechos/ses_pe_arboviroses.json` | — | — | não |
| `coletar_cadastro_prioritarios.py` | — | `cadastro_prioritarios_federal.json` | — | — | não |
| `coletar_cobertura_qd.py` | — | `cobertura_qd.json` | — | — | não |
| `coletar_dda.py` | — | `saude_desfechos/dda_cache.json`, `saude_desfechos/dda_serie.json`, `saude_desfechos/dda_serie_painel.json` | — | — | não |
| `coletar_declarado_nacional.py` | — | `declarado_nacional.json`, `fontes_consultadas.json`, `fontes_declarado.json` | — | — | não |
| `coletar_desfechos_saude.py` | — | — | — | — | não |
| `coletar_diarios_consorciados.py` | — | `atos_resposta.json` | — | — | não |
| `coletar_diarios_municipais.py` | — | `atos_resposta.json`, `cobertura_qd.json`, `verificacao_municipal.json` | — | 5 | não |
| `coletar_doe.py` | — | `atos_resposta.json`, `estados.json`, `fontes_doe.json`, `indice.json`, `monitor_saude.json`, `municipios.json` (+1) | — | 2 | não |
| `coletar_edicoes_doe.py` | — | `doe_ocorrencias.json` | — | 1 | não |
| `coletar_espin.py` | — | `espin_revisar.json`, `saude_sinais.json` | — | — | não |
| `coletar_execucao_mps.py` | — | `financiamento/mps_2026.json` | — | — | não |
| `coletar_financiamento.py` | — | `compromissos_federais.json`, `consultas.json`, `emendas.json`, `financiamento_uf.json`, `por_uf.json`, `recursos_uf.json` (+2) | — | — | não |
| `coletar_normais_inmet.py` | — | `normais_capitais.json` | — | — | não |
| `coletar_obitos_registro_civil.py` | — | `saude_desfechos/obitos_registro_civil.json` | — | — | não |
| `coletar_painel_am.py` | — | `pistas_painel_am.json` | — | — | não |
| `coletar_prioritarios_mma.py` | — | `enquadramento_federal.json` | — | — | não |
| `coletar_recursos_resposta.py` | — | `estados.json`, `indice.json`, `monitor_saude.json`, `municipios.json`, `resposta/recursos_liberados.json`, `saude_uf.json` | — | — | não |
| `coletar_s2id.py` | — | `atos_resposta.json` | — | — | não |
| `coletar_saude.py` | — | `saude_federal.json`, `saude_sinais.json`, `saude_uf.json` | — | — | não |
| `coletar_saude_estadual.py` | — | `pistas_imprensa_saude.json`, `saude_desfechos/fontes_uf.json` | — | 1 | não |
| `coletar_semiarido_sudene.py` | — | `enquadramento_federal.json` | — | — | não |
| `coletar_sg_esus.py` | — | `estados.json`, `indice.json`, `monitor_saude.json`, `municipios.json`, `saude_desfechos/sindrome_gripal_serie.json`, `saude_uf.json` | — | — | não |
| `coletar_siconfi_182.py` | — | `despesa_182.json` | — | 1 | não |
| `coletar_sinais_risco.py` | — | — | — | 1 | não |
| `coletar_srag_gripe.py` | — | `saude_desfechos/infogripe_diagnostico.json` | — | 3 | não |
| `coletar_srag_sivep.py` | — | `saude_desfechos/srag_serie.json`, `saude_desfechos/srag_sivep_agregados.json` | — | — | não |
| `coletar_transferegov.py` | — | `financiamento/consultas.json`, `financiamento/por_uf.json`, `financiamento/programas_faf_2026.json`, `financiamento/serie_nacional.json`, `transferegov_el_nino_revisar.json` | — | — | não |
| `coletar_transferencias_municipais.py` | — | `estados.json`, `indice.json`, `monitor_saude.json`, `municipios.json`, `saude_uf.json`, `transferencias_uniao.json` | — | — | não |
| `coletores_base.py` | — | `atos_resposta.json`, `calendario/fontes_suspensas.json`, `evidencias.json`, `fontes_consultadas.json`, `log_buscas.json`, `robots_registro.json` (+1) | — | **177** | não |
| `consultar_querido_diario.py` | — | `pistas_querido_diario.json` | — | 1 | não |
| `converter_contribuicao.py` | — | — | — | — | SIM |
| `descobrir_dominios.py` | — | `dominios_oficiais.json` | — | — | não |
| `descobrir_planos.py` | — | — | — | 2 | não |
| `detectar_marcos_federais.py` | — | `marcos_federais_saude.json`, `saude_uf.json` | — | — | não |
| `funil.py` | — | — | — | 11 | não |
| `gerar_blog.py` | — | — | — | — | não |
| `gerar_card_municipios.py` | — | `municipios_card.json` | — | — | não |
| `gerar_cobertura_declarada.py` | — | `cobertura_declarada_uf.json` | — | — | não |
| `gerar_contadores_financiamento.py` | — | `financiamento/contadores_uf.json` | — | — | não |
| `gerar_dados_abertos.py` | — | — | — | — | não |
| `gerar_erros_localizacao.py` | — | `erros_localizacao.json` | — | — | não |
| `gerar_feeds.py` | — | — | — | — | não |
| `gerar_financiamento_semana.py` | — | `financiamento/semana.json` | — | — | não |
| `gerar_imprensa_semana.py` | — | `semana.json` | — | 1 | não |
| `gerar_lai.py` | — | — | — | — | não |
| `gerar_monitor_saude.py` | — | `monitor_saude.json` | — | 5 | não |
| `gerar_monitor_saude_v04.py` | — | `monitor_saude_v04.json` | — | — | não |
| `gerar_pacote_blog.py` | — | `financiamento/caminhos.json` | — | — | não |
| `gerar_painel.py` | — | `agregados.json`, `atos_resposta.json`, `fichas.json`, `lista.json`, `municipios.json`, `verificacao_municipal.json` | — | — | não |
| `gerar_pdf_indice.py` | — | — | — | — | não |
| `gerar_pdf_metodologia.py` | — | — | — | — | não |
| `gerar_prioritarios.py` | — | `municipios_prioritarios.json` | — | — | não |
| `gerar_resposta.py` | — | `resposta/municipios.json`, `resposta/municipios_decretados.json`, `resposta/por_uf.json`, `resposta/serie_semanal.json` | — | 1 | SIM |
| `gerar_selos.py` | — | — | — | 1 | não |
| `juiz.py` | — | — | — | 9 | SIM |
| `julgar_e_aplicar_descobertas.py` | — | `atos_resposta.json`, `consist.json`, `decretos_historico_uf.json`, `estados.json`, `indice.json`, `municipios.json` (+2) | — | 4 | não |
| `julgar_filas.py` | — | `pistas_descobertas.json`, `pistas_doe.json`, `pistas_imprensa.json`, `pistas_querido_diario.json`, `pistas_revisao.json`, `promocoes_automaticas.json` | — | 1 | não |
| `julgar_saude.py` | — | `pistas_imprensa_saude.json`, `saude_uf.json` | — | 1 | não |
| `ler_caixa_lai.py` | — | — | — | — | não |
| `migrar_saude_instrumentos.py` | — | — | — | 4 | não |
| `migrar_v224_verificacao.py` | — | `citacao_incompleta.json`, `erratas_v224.json`, `log_buscas.json`, `municipios.json`, `pontos_mapa.json` | — | — | não |
| `monitorar_atos_resposta.py` | — | — | — | — | não |
| `monitorar_busca_web.py` | — | `busca_web_espera.json`, `busca_web_estado.json` | — | 4 | não |
| `monitorar_imprensa_regional.py` | — | — | — | 5 | não |
| `monitorar_imprensa_saude.py` | — | — | — | — | não |
| `monitorar_politica_por_inteiro.py` | — | — | — | — | não |
| `monitorar_redes_oficiais.py` | — | — | — | — | não |
| `monitorar_sinais_federais.py` | — | — | — | 1 | não |
| `motores_busca.py` | — | `busca_web_motores.json` | — | 4 | não |
| `pagina_completa.py` | — | — | — | 6 | não |
| `preencher_fallback_estatico.py` | — | — | — | — | não |
| `preservar_evidencias.py` | — | `evidencias.json`, `municipios.json` | — | 6 | não |
| `processar_contribuicoes.py` | — | — | — | — | não |
| `recalcular_mare.py` | — | — | — | 7 | SIM |
| `registrar_saude_central.py` | — | `saude_uf.json` | — | — | não |
| `revisar_pistas.py` | — | `pistas_imprensa.json` | — | — | não |
| `robustez_saude.py` | — | — | — | — | não |
| `saude_opendatasus.py` | — | — | — | 2 | não |
| `scripts/commit_do_elo.py` | — | `inventado.json`, `municipios.json`, `novo.json`, `pistas_imprensa.json`, `pistas_revisao.json`, `publicacao.json` | — | 1 | não |
| `scripts/consolidar_noite.py` | — | `focos_pontos.json`, `historico_mudancas.json`, `inventado.json`, `log_buscas.json`, `painel_da_noite.json`, `pistas_imprensa.json` (+2) | — | — | não |
| `scripts/contar_filas_humanas.py` | — | `decretos_conteudo_revisar.json`, `pistas_descobertas.json`, `pistas_imprensa.json`, `pistas_imprensa_saude.json`, `saude_no_plano_revisar.json` | — | — | não |
| `scripts/corrigir_atribuicao_por_dominio.py` | — | `pistas_descobertas.json`, `pistas_doe.json`, `pistas_imprensa.json`, `pistas_querido_diario.json`, `pistas_revisao.json` | — | — | não |
| `scripts/deduplicar_fila_de_pistas.py` | — | `pistas_descobertas.json`, `pistas_doe.json`, `pistas_imprensa.json`, `pistas_rejeitadas.json`, `pistas_sinais.json` | — | — | não |
| `scripts/diagnosticar_querido_diario.py` | — | `atos_resposta.json`, `municipios_ibge_referencia.json` | — | — | não |
| `scripts/ensaio_da_noite.py` | — | `pistas_imprensa.json` | — | — | não |
| `scripts/fechar_saude.py` | — | `saude_troca_v04.json` | — | — | não |
| `scripts/fila_do_juiz_querido_diario.py` | — | `fila_qd_169.json` | — | — | não |
| `scripts/gerar_boletim.py` | — | `blog/boletim_mais_recente.json` | — | — | não |
| `scripts/gerar_cadencia_de_publicacao.py` | — | `cadencia_publicacao.json` | — | — | não |
| `scripts/gerar_codemap.py` | — | `a.json`, `b.json`, `c.json`, `cobertura_qd.json`, `geo_uf.json`, `indice.json` (+2) | — | — | não |
| `scripts/gerar_enquadramento_card.py` | — | `enquadramento_card.json` | — | — | não |
| `scripts/gerar_manifesto.py` | — | `painel_da_noite.json`, `saude_pipeline.json`, `transferencias_api_raw.json` | — | — | não |
| `scripts/gerar_prioridade_municipios.py` | — | `prioridade_municipios.json` | — | — | não |
| `scripts/gerar_resumo_do_log.py` | — | `log_buscas_resumo.json` | — | — | não |
| `scripts/gerar_topo_das_paginas.py` | — | `resposta/topo_defesa_civil.json`, `saude_desfechos/topo_saude.json`, `topo_monitor_riscos.json` | — | — | não |
| `scripts/incorporar_lai_am_ro.py` | — | `notas_lai.json` | — | — | não |
| `scripts/incorporar_respostas_lai.py` | — | `atos_resposta.json`, `estados.json`, `notas_lai.json` | — | — | não |
| `scripts/ingerir_ocp_midr.py` | — | `ocp_2026.json` | — | — | não |
| `scripts/limpar_fila_de_pistas.py` | — | `pistas_imprensa.json` | — | 2 | não |
| `scripts/medir_ciclo_de_mudanca.py` | — | `indice.json`, `saude_pipeline.json` | — | — | não |
| `scripts/migrar_pistas_para_o_esquema.py` | — | `pistas_descobertas.json`, `pistas_doe.json`, `pistas_imprensa.json`, `pistas_querido_diario.json`, `pistas_revisao.json` | — | — | não |
| `scripts/migrar_sobras_do_doe.py` | — | `pistas_doe.json` | — | — | não |
| `scripts/orcamento_da_noite.py` | — | `cursor_da_noite.json` | — | — | não |
| `scripts/ordem_de_coleta.py` | — | `cursor_de_coleta.json` | — | — | não |
| `scripts/painel_da_noite.py` | — | `painel_da_noite.json` | — | 2 | não |
| `scripts/pistas.py` | — | `pistas_imprensa.json`, `pistas_rejeitadas.json` | — | 13 | não |
| `scripts/preservar_textos_integrais.py` | — | `evidencias.json` | — | — | não |
| `scripts/quais_portoes.py` | — | `indice.json` | — | — | não |
| `scripts/reaplicar_noite.py` | — | `evidencias.json`, `funil/2026-10-08.json`, `historico_mudancas.json`, `log_buscas.json`, `municipios.json`, `painel_da_noite.json` (+4) | — | 1 | não |
| `scripts/reavaliar_fontes_suspensas.py` | — | `calendario/fontes_suspensas.json` | — | — | não |
| `scripts/registrar_faixas.py` | — | `historico_faixas.json` | — | 1 | não |
| `scripts/remediar_cpf_evidencias.py` | — | `evidencias.json` | — | — | não |
| `scripts/remediar_segredos_evidencias.py` | — | `evidencias.json` | — | 1 | não |
| `scripts/saude_pipeline.py` | — | `saude_pipeline.json` | — | 1 | não |
| `scripts/sondar_dda_zenodo.py` | — | `saude_desfechos/completude.json`, `saude_desfechos/serie_painel.json` | — | — | não |
| `scripts/sondar_rotas_doe.py` | — | `fontes_doe.json` | — | — | não |
| `scripts/testar_escrita_atomica.py` | — | `w.json`, `x.json`, `y.json`, `z.json` | — | — | não |
| `scripts/testar_reposicao_dominio.py` | — | `publicacao.json` | — | — | não |
| `scripts/tipo_de_evento_dos_atos.py` | — | `atos_resposta.json` | — | — | não |
| `scripts/triar_fila.py` | — | `pistas_imprensa.json` | — | — | não |
| `scripts/unir_conflito_de_rodada.py` | — | `fontes_consultadas.json`, `funil/2026-10-05.json`, `funil/x.json`, `historico_mudancas.json`, `log_buscas.json`, `log_buscas/2026-10.json` (+12) | — | 3 | não |
| `seguir_pistas.py` | — | — | — | — | não |
| `sondar_paineis.py` | — | `pistas_paineis.json` | — | — | não |
| `triar_confianca_pistas.py` | — | `pistas_imprensa.json`, `pistas_revisao.json` | — | — | não |
| `trocar_para_v04.py` | — | — | — | — | não |
| `verificar_consistencia.py` | — | — | — | — | não |
| `verificar_contribuicoes.py` | — | — | — | — | não |
| `verificar_evidencias.py` | — | — | — | — | não |
| `verificar_financiamento.py` | — | `financiamento/x.json` | — | — | não |
| `verificar_links.py` | — | — | — | — | não |
| `verificar_painel.py` | — | `painel/lista.json` | — | — | não |
| `verificar_pista_imprensa.py` | — | `veiculos_imprensa.json` | — | 1 | não |
| `verificar_recorrencia_uf.py` | — | — | — | 1 | não |
| `verificar_resposta.py` | — | — | — | — | não |
| `verificar_saude.py` | — | — | — | — | não |
| `verificar_sinais.py` | — | — | — | — | não |
| `verificar_vigencia.py` | — | `municipios.json` | — | — | não |
