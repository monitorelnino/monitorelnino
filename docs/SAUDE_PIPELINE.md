# Saúde do pipeline

Gerado por `scripts/gerar_saude_pipeline.py` a partir de `data/saude_pipeline.json`, que os
jobs escrevem com `scripts/saude_pipeline.py --rodar`. Item 2 do handover de desacoplamento
(27/09/2026). **Arquivo derivado: não se edita à mão.**

Duas classes, e a diferença importa. **Essencial** (`recalcular_mare.py`, `gerar_*.py`): se
erra, o site publica um estado que não corresponde ao dado — reprova o portão. **Coletor**:
fonte fora do ar é rotina, e uma falha isolada não é defeito do pipeline; erro em duas
rodadas seguidas vira alerta, porque aí não é a fonte, é o coletor.

Janela: 2026-11-13 a 2026-11-20 (1512 execução(ões) registrada(s), 7 dias de histórico).

## Alertas

- coletar_datasus_dbc.py: erro em 2 rodadas seguidas — [lacuna declarada] ftp://ftp.datasus.gov.br/dissemin/publicos/SINAN/DADOS/ (malaria): TimeoutError: timed out; o arquivo anterior fica
- consultar_querido_diario.py: erro em 3 rodadas seguidas — portas tentadas: api.queridodiario.org.br: HTTPError HTTP Error 503: Service Unavailable | queridodiario.ok.org.br: HTTPError HTTP Error 503: Service Unavailable | api.queridodiario.ok.org.br: URLError <urlopen error [SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] ssl/tls alert handshake fail
- python3: erro em 2 rodadas seguidas — SyntaxError: unterminated string literal (detected at line 1)
- verificar_links.py: erro em 2 rodadas seguidas — erro: https://xanxere.sc.gov.br/uploads/sites/92/2025/05/PLANO-DE-CONTINGENCIA-XXE.pdf

## Cobertura em 15 dias

cobertura 15d: 4918/5571 com verificação real até 2026-11-20 · por canal: web 216 · QD 527 · consorciado 1693 · DOE 4798

## Última execução de cada script

| script | papel | última execução | duração | itens | status | erro |
|---|---|---|---|---:|---|---|
| `gerar_blog.py` | essencial | 2026-11-15 06:14 | 0 s | — | ok | — |
| `gerar_contadores_financiamento.py` | essencial | 2026-11-15 06:19 | 0 s | — | ok | — |
| `gerar_dados_abertos.py` | essencial | 2026-11-15 06:14 | 0 s | — | ok | — |
| `gerar_feeds.py` | essencial | 2026-11-15 06:14 | 1 s | — | ok | — |
| `gerar_monitor_saude.py` | essencial | 2026-11-16 19:53 | 1 s | — | ok | — |
| `gerar_mortalidade_comparada.py` | essencial | 2026-11-19 07:26 | 1 s | — | ok | — |
| `gerar_painel.py` | essencial | 2026-11-15 06:14 | 1 s | — | ok | — |
| `gerar_prioritarios.py` | essencial | 2026-11-15 06:19 | 0 s | — | ok | — |
| `gerar_resposta.py` | essencial | 2026-11-15 06:19 | 1 s | — | ok | — |
| `gerar_saude_municipio.py` | essencial | 2026-11-19 01:36 | 1 s | — | ok | — |
| `gerar_selos.py` | essencial | 2026-11-15 06:14 | 1 s | — | ok | — |
| `recalcular_mare.py` | essencial | 2026-11-20 05:28 | 5 s | — | ok | — |
| `analisar_decretos.py` | coletor | 2026-11-15 05:56 | 1126 s | — | ok | — |
| `aplicar_promocoes_do_juiz.py` | coletor | 2026-11-20 04:04 | 46 s | 0 | ok | — |
| `atualizar.py` | coletor | 2026-11-15 04:04 | 8099 s | 150 | ok | — |
| `atualizar_boletins.py` | coletor | 2026-11-15 04:04 | 2 s | — | ok | — |
| `atualizar_instrumentos_estaduais.py` | coletor | 2026-11-15 05:45 | 84 s | — | **erro** | código de saída 1 |
| `atualizar_populacao.py` | coletor | 2026-11-15 03:33 | 1 s | — | ok | — |
| `atualizar_recursos.py` | coletor | 2026-11-15 05:56 | 1 s | — | **erro** | código de saída 1 |
| `atualizar_transferencias.py` | coletor | 2026-11-15 06:14 | 2 s | — | **erro** | código de saída 1 |
| `bash scripts/verificar_derivados.sh --idempotencia` | coletor | 2026-11-15 06:17 | 170 s | — | ok | — |
| `buscar_financiamento_preventivo.py` | coletor | 2026-11-20 05:21 | 1 s | — | ok | — |
| `buscar_protocolo_calor.py` | coletor | 2026-11-17 01:18 | 16 s | 41 | ok | — |
| `classificar_planos_municipais.py` | coletor | 2026-11-14 01:18 | 1 s | — | ok | — |
| `classificar_saude_no_plano.py` | coletor | 2026-11-19 01:36 | 1 s | — | ok | — |
| `coletar_arboviroses_sinan.py` | coletor | 2026-11-19 01:34 | 48 s | — | ok | — |
| `coletar_boletim_df_arboviroses.py` | coletor | 2026-11-19 01:31 | 211 s | — | ok | — |
| `coletar_boletim_ms_dengue.py` | coletor | 2026-11-19 01:30 | 21 s | — | ok | — |
| `coletar_boletim_pb_arboviroses.py` | coletor | 2026-11-19 01:34 | 3 s | — | ok | — |
| `coletar_boletim_pe_arboviroses.py` | coletor | 2026-11-19 01:34 | 4 s | — | ok | — |
| `coletar_cadastro_prioritarios.py` | coletor | 2026-11-14 01:13 | 29 s | — | ok | — |
| `coletar_cobertura_qd.py` | coletor | 2026-11-14 01:18 | 2027 s | — | ok | — |
| `coletar_datasus_dbc.py` | coletor | 2026-11-19 07:16 | 206 s | — | **erro** (2 seguidas) | [lacuna declarada] ftp://ftp.datasus.gov.br/dissemin/publicos/SINAN/DADOS/ (malaria): TimeoutError: timed out; o arquivo |
| `coletar_dda.py` | coletor | 2026-11-19 01:29 | 57 s | — | ok | — |
| `coletar_declarado_nacional.py` | coletor | 2026-11-15 04:21 | 28 s | — | ok | — |
| `coletar_desfechos_saude.py` | coletor | 2026-11-19 01:22 | 463 s | — | ok | — |
| `coletar_diarios_consorciados.py` | coletor | 2026-11-19 01:15 | 2562 s | 82 | ok | — |
| `coletar_diarios_municipais.py` | coletor | 2026-11-19 01:15 | 2 s | 0 | ok | — |
| `coletar_doe.py` | coletor | 2026-11-19 01:58 | 1853 s | — | ok | — |
| `coletar_edicoes_doe.py` | coletor | 2026-11-20 01:55 | 4801 s | — | **erro** | interrompido pelo prazo do elo |
| `coletar_espin.py` | coletor | 2026-11-20 03:15 | 304 s | — | ok | — |
| `coletar_execucao_mps.py` | coletor | 2026-11-15 05:44 | 22 s | — | ok | — |
| `coletar_financiamento.py` | coletor | 2026-11-15 05:44 | 1 s | — | ok | — |
| `coletar_mapbiomas.py` | coletor | 2026-11-17 18:04 | 2 s | — | ok | — |
| `coletar_normais_inmet.py` | coletor | 2026-11-14 01:13 | 3 s | — | ok | — |
| `coletar_obitos.py` | coletor | 2026-11-19 07:22 | 5 s | — | ok | — |
| `coletar_obitos_registro_civil.py` | coletor | 2026-11-19 01:35 | 41 s | — | ok | — |
| `coletar_pab_brasil.py` | coletor | 2026-11-14 01:14 | 7 s | — | ok | — |
| `coletar_planos_arboviroses.py` | coletor | 2026-11-19 08:10 | 1409 s | — | **erro** | interrompido pelo prazo do elo |
| `coletar_prioritarios_mma.py` | coletor | 2026-11-14 01:13 | 3 s | — | ok | — |
| `coletar_projecao_cil.py` | coletor | 2026-11-19 07:26 | 4 s | — | ok | — |
| `coletar_recursos_resposta.py` | coletor | 2026-11-19 02:48 | 51 s | — | ok | — |
| `coletar_s2id.py` | coletor | 2026-11-19 02:29 | 1163 s | — | ok | — |
| `coletar_saude.py` | coletor | 2026-11-19 01:13 | 75 s | — | ok | — |
| `coletar_saude_estadual.py` | coletor | 2026-11-18 03:00 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `coletar_semiarido_sudene.py` | coletor | 2026-11-14 01:13 | 2 s | — | ok | — |
| `coletar_sg_esus.py` | coletor | 2026-11-19 02:01 | 9 s | — | ok | — |
| `coletar_siconfi_182.py` | coletor | 2026-11-15 05:42 | 1 s | — | ok | — |
| `coletar_sih.py` | coletor | 2026-11-19 07:26 | 2672 s | — | ok | — |
| `coletar_sim.py` | coletor | 2026-11-19 07:22 | 204 s | — | **erro** | TimeoutError: timed out |
| `coletar_sinais_risco.py` | coletor | 2026-11-19 01:13 | 97 s | — | ok | — |
| `coletar_sisab.py` | coletor | 2026-11-19 07:20 | 167 s | — | ok | — |
| `coletar_srag_gripe.py` | coletor | 2026-11-15 05:35 | 144 s | — | ok | — |
| `coletar_srag_sivep.py` | coletor | 2026-11-19 02:00 | 32 s | — | ok | — |
| `coletar_transferegov.py` | coletor | 2026-11-15 05:44 | 2 s | — | ok | — |
| `coletar_transferencias_municipais.py` | coletor | 2026-11-19 01:14 | 62 s | — | ok | — |
| `conferir_emergencias_estaduais.py` | coletor | 2026-11-19 01:15 | 0 s | — | ok | — |
| `consultar_querido_diario.py` | coletor | 2026-11-19 01:15 | 2 s | — | **erro** (3 seguidas) | portas tentadas: api.queridodiario.org.br: HTTPError HTTP Error 503: Service Unavailable \| queridodiario.ok.org.br: HTT |
| `descobrir_dominios.py` | coletor | 2026-11-15 01:51 | 5561 s | — | **erro** | interrompido pelo prazo do elo |
| `descobrir_planos.py` | coletor | 2026-11-20 05:07 | 589 s | — | ok | — |
| `desfechos_sus.py` | coletor | 2026-11-19 07:22 | 1 s | — | ok | — |
| `detectar_marcos_federais.py` | coletor | 2026-11-20 05:07 | 2 s | — | ok | — |
| `julgar_e_aplicar_descobertas.py` | coletor | 2026-11-19 08:45 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `julgar_filas.py` | coletor | 2026-11-20 03:26 | 2278 s | — | ok | — |
| `julgar_saude.py` | coletor | 2026-11-18 20:58 | 3850 s | — | ok | — |
| `julgar_saude_municipal.py` | coletor | 2026-11-16 05:40 | 8409 s | — | ok | — |
| `ler_planos_arboviroses.py` | coletor | 2026-11-19 08:34 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `monitorar_atos_resposta.py` | coletor | 2026-11-20 05:04 | 151 s | 25333 | ok | — |
| `monitorar_busca_web.py` | coletor | 2026-11-20 05:17 | 240 s | — | ok | — |
| `monitorar_imprensa_regional.py` | coletor | 2026-11-20 04:55 | 457 s | 40 | ok | — |
| `monitorar_imprensa_saude.py` | coletor | 2026-11-20 05:02 | 102 s | 27 | ok | — |
| `monitorar_politica_por_inteiro.py` | coletor | 2026-11-20 05:07 | 2 s | 19244 | ok | — |
| `monitorar_sinais_federais.py` | coletor | 2026-11-20 05:07 | 4 s | 10 | ok | — |
| `node scripts/verificar_acessibilidade.js` | coletor | 2026-11-15 06:16 | 2 s | — | ok | — |
| `node scripts/verificar_estrutura.js` | coletor | 2026-11-15 06:14 | 2 s | — | ok | — |
| `node scripts/verificar_runtime.js` | coletor | 2026-11-15 06:16 | 5 s | — | ok | — |
| `node scripts/verificar_runtime_financiamento.js` | coletor | 2026-11-15 06:16 | 5 s | — | ok | — |
| `node scripts/verificar_runtime_mapas.js` | coletor | 2026-11-15 06:16 | 4 s | — | ok | — |
| `node scripts/verificar_runtime_saude.js` | coletor | 2026-11-15 06:16 | 2 s | — | ok | — |
| `node scripts/verificar_runtime_sinais.js` | coletor | 2026-11-15 06:16 | 2 s | — | ok | — |
| `node scripts/verificar_texto_publico.js` | coletor | 2026-11-15 06:16 | 38 s | — | ok | — |
| `preencher_fallback_estatico.py` | coletor | 2026-11-15 06:19 | 0 s | — | ok | — |
| `preservar_evidencias.py` | coletor | 2026-11-20 04:49 | 48 s | — | ok | — |
| `processar_contribuicoes.py` | coletor | 2026-11-19 07:32 | 1 s | — | ok | — |
| `python3` | coletor | 2026-11-15 16:10 | 0 s | — | **erro** (2 seguidas) | SyntaxError: unterminated string literal (detected at line 1) |
| `reconferir_instrumentos_federais.py` | coletor | 2026-11-19 08:34 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `revisar_pistas.py` | coletor | 2026-11-19 07:32 | 1391 s | — | ok | — |
| `scripts/amostra_auditoria_semanal.py` | coletor | 2026-11-19 08:45 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/busca_dirigida_do_ato.py` | coletor | 2026-11-20 05:21 | 52 s | — | ok | — |
| `scripts/corrigir_atribuicao_por_dominio.py` | coletor | 2026-11-19 07:32 | 1 s | — | ok | — |
| `scripts/fechar_saude.py` | coletor | 2026-11-18 03:00 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/pistas.py` | coletor | 2026-11-15 10:00 | 252 s | — | ok | — |
| `scripts/preservar_textos_integrais.py` | coletor | 2026-11-20 04:50 | 2 s | — | ok | — |
| `scripts/proveniencia_estadual.py` | coletor | 2026-11-20 03:20 | 1 s | — | ok | — |
| `scripts/reavaliar_fontes_suspensas.py` | coletor | 2026-11-20 05:12 | 810 s | — | ok | — |
| `scripts/remediar_segredos_evidencias.py` | coletor | 2026-11-18 12:52 | 165 s | — | ok | — |
| `scripts/sondar_boletim_infogripe.py` | coletor | 2026-11-14 01:14 | 99 s | — | ok | — |
| `scripts/sondar_credenciais.py` | coletor | 2026-11-19 01:15 | 2 s | — | ok | — |
| `scripts/triar_fila.py` | coletor | 2026-11-20 03:26 | 1 s | — | ok | — |
| `scripts/verificar_esquema_de_pista.py` | coletor | 2026-11-20 04:05 | 2 s | — | ok | — |
| `scripts/verificar_funil.py` | coletor | 2026-11-15 03:39 | 0 s | — | ok | — |
| `scripts/verificar_leituras_paradas.py` | coletor | 2026-11-20 04:05 | 3 s | — | ok | — |
| `seguir_pistas.py` | coletor | 2026-11-20 05:21 | 13 s | — | ok | — |
| `sondar_repositorios_estaduais.py` | coletor | 2026-11-19 02:02 | 0 s | — | ok | — |
| `triar_confianca_pistas.py` | coletor | 2026-11-20 05:22 | 2 s | — | ok | — |
| `verificar_consistencia.py` | coletor | 2026-11-15 06:14 | 6 s | — | ok | — |
| `verificar_contribuicoes.py` | coletor | 2026-11-15 05:45 | 1 s | — | ok | — |
| `verificar_evidencias.py` | coletor | 2026-11-15 06:15 | 66 s | — | ok | — |
| `verificar_financiamento.py` | coletor | 2026-11-15 06:15 | 1 s | — | ok | — |
| `verificar_links.py` | coletor | 2026-11-17 01:36 | 187 s | — | **erro** (2 seguidas) | erro: https://xanxere.sc.gov.br/uploads/sites/92/2025/05/PLANO-DE-CONTINGENCIA-XXE.pdf |
| `verificar_painel.py` | coletor | 2026-11-15 06:15 | 1 s | — | ok | — |
| `verificar_pista_imprensa.py` | coletor | 2026-11-20 05:22 | 129 s | — | ok | — |
| `verificar_saude.py` | coletor | 2026-11-15 06:15 | 1 s | — | ok | — |
| `verificar_sinais.py` | coletor | 2026-11-15 06:15 | 1 s | — | ok | — |
| `verificar_vigencia.py` | coletor | 2026-11-15 05:56 | 0 s | — | ok | — |
