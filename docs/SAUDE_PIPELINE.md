# Saúde do pipeline

Gerado por `scripts/gerar_saude_pipeline.py` a partir de `data/saude_pipeline.json`, que os
jobs escrevem com `scripts/saude_pipeline.py --rodar`. Item 2 do handover de desacoplamento
(27/09/2026). **Arquivo derivado: não se edita à mão.**

Duas classes, e a diferença importa. **Essencial** (`recalcular_mare.py`, `gerar_*.py`): se
erra, o site publica um estado que não corresponde ao dado — reprova o portão. **Coletor**:
fonte fora do ar é rotina, e uma falha isolada não é defeito do pipeline; erro em duas
rodadas seguidas vira alerta, porque aí não é a fonte, é o coletor.

Janela: 2026-11-19 a 2026-11-26 (1551 execução(ões) registrada(s), 7 dias de histórico).

## Alertas

- buscar_planos_fontes_abertas.py: erro em 7 rodadas seguidas — interrompido pelo prazo do elo
- coletar_cadastro_prioritarios.py: erro em 3 rodadas seguidas — X nt2_2025: URLError: <urlopen error [Errno 104] Connection reset by peer> — nada foi gravado
- coletar_pab_brasil.py: erro em 2 rodadas seguidas — urllib.error.URLError: <urlopen error [Errno 104] Connection reset by peer>
- consultar_querido_diario.py: erro em 4 rodadas seguidas — portas tentadas: api.queridodiario.org.br: HTTPError HTTP Error 503: Service Unavailable | queridodiario.ok.org.br: HTTPError HTTP Error 503: Service Unavailable | api.queridodiario.ok.org.br: URLError <urlopen error [SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] ssl/tls alert handshake fail
- verificar_links.py: erro em 3 rodadas seguidas — interrompido pelo prazo do elo

## Cobertura em 15 dias

cobertura 15d: 5031/5571 com verificação real até 2026-11-25 · por canal: web 216 · QD 527 · consorciado 1699 · DOE 4937

## Última execução de cada script

| script | papel | última execução | duração | itens | status | erro |
|---|---|---|---|---:|---|---|
| `gerar_contadores_financiamento.py` | essencial | 2026-11-22 07:29 | 1 s | — | ok | — |
| `gerar_dados_abertos.py` | essencial | 2026-11-22 07:27 | 1 s | — | ok | — |
| `gerar_feeds.py` | essencial | 2026-11-22 07:27 | 2 s | — | ok | — |
| `gerar_monitor_saude.py` | essencial | 2026-11-22 07:29 | 1 s | — | ok | — |
| `gerar_mortalidade_comparada.py` | essencial | 2026-11-25 07:16 | 1 s | — | ok | — |
| `gerar_painel.py` | essencial | 2026-11-22 07:27 | 1 s | — | ok | — |
| `gerar_prioritarios.py` | essencial | 2026-11-22 07:29 | 0 s | — | ok | — |
| `gerar_resposta.py` | essencial | 2026-11-22 07:29 | 1 s | — | ok | — |
| `gerar_saude_municipio.py` | essencial | 2026-11-25 01:37 | 1 s | — | ok | — |
| `gerar_selos.py` | essencial | 2026-11-22 07:27 | 1 s | — | ok | — |
| `recalcular_mare.py` | essencial | 2026-11-26 07:21 | 5 s | — | ok | — |
| `analisar_decretos.py` | coletor | 2026-11-22 06:54 | 501 s | — | ok | — |
| `aplicar_promocoes_do_juiz.py` | coletor | 2026-11-26 06:14 | 318 s | 0 | ok | — |
| `atualizar.py` | coletor | 2026-11-22 04:10 | 11930 s | 147 | ok | — |
| `atualizar_boletins.py` | coletor | 2026-11-22 04:10 | 21 s | — | ok | — |
| `atualizar_instrumentos_estaduais.py` | coletor | 2026-11-22 06:35 | 82 s | — | **erro** | código de saída 1 |
| `atualizar_populacao.py` | coletor | 2026-11-22 03:31 | 1 s | — | ok | — |
| `atualizar_recursos.py` | coletor | 2026-11-22 06:54 | 2 s | — | **erro** | código de saída 1 |
| `atualizar_transferencias.py` | coletor | 2026-11-22 07:02 | 1476 s | — | ok | — |
| `bash scripts/verificar_derivados.sh --idempotencia` | coletor | 2026-11-22 07:28 | 74 s | — | ok | — |
| `buscar_financiamento_preventivo.py` | coletor | 2026-11-26 07:07 | 0 s | — | ok | — |
| `buscar_planos_fontes_abertas.py` | coletor | 2026-11-25 11:46 | 7203 s | — | **erro** (7 seguidas) | interrompido pelo prazo do elo |
| `buscar_protocolo_calor.py` | coletor | 2026-11-24 02:01 | 58 s | 41 | ok | — |
| `classificar_planos_municipais.py` | coletor | 2026-11-24 05:24 | 1 s | — | ok | — |
| `classificar_saude_no_plano.py` | coletor | 2026-11-25 01:37 | 2 s | — | ok | — |
| `coletar_arboviroses_sinan.py` | coletor | 2026-11-25 01:35 | 60 s | — | ok | — |
| `coletar_boletim_df_arboviroses.py` | coletor | 2026-11-25 01:29 | 380 s | — | ok | — |
| `coletar_boletim_ms_dengue.py` | coletor | 2026-11-25 01:28 | 43 s | — | ok | — |
| `coletar_boletim_pb_arboviroses.py` | coletor | 2026-11-25 01:35 | 4 s | — | ok | — |
| `coletar_boletim_pe_arboviroses.py` | coletor | 2026-11-25 01:35 | 7 s | — | ok | — |
| `coletar_cadastro_prioritarios.py` | coletor | 2026-11-24 09:20 | 62 s | — | **erro** (3 seguidas) | X nt2_2025: URLError: <urlopen error [Errno 104] Connection reset by peer> — nada foi gravado |
| `coletar_cobertura_qd.py` | coletor | 2026-11-24 05:24 | 7587 s | — | **erro** | interrompido pelo prazo do elo |
| `coletar_datasus_dbc.py` | coletor | 2026-11-25 07:13 | 38 s | — | ok | — |
| `coletar_dda.py` | coletor | 2026-11-25 01:27 | 56 s | — | ok | — |
| `coletar_declarado_nacional.py` | coletor | 2026-11-22 04:32 | 73 s | — | ok | — |
| `coletar_desfechos_saude.py` | coletor | 2026-11-25 01:21 | 409 s | — | ok | — |
| `coletar_diarios_consorciados.py` | coletor | 2026-11-25 01:13 | 2280 s | 74 | ok | — |
| `coletar_diarios_municipais.py` | coletor | 2026-11-25 01:13 | 2 s | 0 | ok | — |
| `coletar_doe.py` | coletor | 2026-11-25 01:51 | 1572 s | — | ok | — |
| `coletar_edicoes_doe.py` | coletor | 2026-11-25 01:15 | 141 s | — | ok | — |
| `coletar_espin.py` | coletor | 2026-11-25 04:21 | 271 s | — | ok | — |
| `coletar_execucao_mps.py` | coletor | 2026-11-22 06:35 | 26 s | — | ok | — |
| `coletar_financiamento.py` | coletor | 2026-11-22 06:35 | 2 s | — | ok | — |
| `coletar_mapbiomas.py` | coletor | 2026-11-24 19:59 | 1 s | — | ok | — |
| `coletar_normais_inmet.py` | coletor | 2026-11-24 05:19 | 4 s | — | ok | — |
| `coletar_obitos.py` | coletor | 2026-11-25 07:16 | 4 s | — | ok | — |
| `coletar_obitos_registro_civil.py` | coletor | 2026-11-25 01:36 | 27 s | — | ok | — |
| `coletar_pab_brasil.py` | coletor | 2026-11-24 05:19 | 36 s | — | **erro** (2 seguidas) | urllib.error.URLError: <urlopen error [Errno 104] Connection reset by peer> |
| `coletar_planos_arboviroses.py` | coletor | 2026-11-25 07:22 | 959 s | — | ok | — |
| `coletar_prioritarios_mma.py` | coletor | 2026-11-24 05:19 | 3 s | — | ok | — |
| `coletar_projecao_cil.py` | coletor | 2026-11-25 07:16 | 3 s | — | ok | — |
| `coletar_recursos_resposta.py` | coletor | 2026-11-25 02:21 | 220 s | — | ok | — |
| `coletar_s2id.py` | coletor | 2026-11-25 02:17 | 250 s | — | ok | — |
| `coletar_saude.py` | coletor | 2026-11-25 01:12 | 82 s | — | ok | — |
| `coletar_saude_estadual.py` | coletor | 2026-11-25 04:00 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `coletar_semiarido_sudene.py` | coletor | 2026-11-24 05:19 | 2 s | — | ok | — |
| `coletar_sg_esus.py` | coletor | 2026-11-25 02:11 | 12 s | — | ok | — |
| `coletar_siconfi_182.py` | coletor | 2026-11-22 06:35 | 0 s | — | ok | — |
| `coletar_sih.py` | coletor | 2026-11-25 07:16 | 328 s | — | ok | — |
| `coletar_sim.py` | coletor | 2026-11-25 07:16 | 8 s | — | sem novidade | — |
| `coletar_sinais_risco.py` | coletor | 2026-11-25 01:12 | 138 s | — | ok | — |
| `coletar_sisab.py` | coletor | 2026-11-25 07:13 | 144 s | — | ok | — |
| `coletar_srag_gripe.py` | coletor | 2026-11-24 05:22 | 144 s | — | ok | — |
| `coletar_srag_sivep.py` | coletor | 2026-11-25 02:10 | 41 s | — | ok | — |
| `coletar_transferegov.py` | coletor | 2026-11-22 06:35 | 2 s | — | ok | — |
| `coletar_transferencias_municipais.py` | coletor | 2026-11-25 01:14 | 41 s | — | ok | — |
| `conferir_emergencias_estaduais.py` | coletor | 2026-11-25 01:17 | 1 s | — | ok | — |
| `consultar_querido_diario.py` | coletor | 2026-11-25 01:13 | 2 s | — | **erro** (4 seguidas) | portas tentadas: api.queridodiario.org.br: HTTPError HTTP Error 503: Service Unavailable \| queridodiario.ok.org.br: HTT |
| `descobrir_dominios.py` | coletor | 2026-11-24 07:31 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `descobrir_planos.py` | coletor | 2026-11-26 06:55 | 448 s | — | ok | — |
| `desfechos_sus.py` | coletor | 2026-11-25 07:16 | 0 s | — | ok | — |
| `detectar_marcos_federais.py` | coletor | 2026-11-26 06:55 | 11 s | — | ok | — |
| `juiz.py` | coletor | 2026-11-24 15:45 | 14401 s | — | **erro** | interrompido pelo prazo do elo |
| `julgar_e_aplicar_descobertas.py` | coletor | 2026-11-26 06:11 | 215 s | — | ok | — |
| `julgar_filas.py` | coletor | 2026-11-26 04:56 | 4504 s | — | **erro** | interrompido pelo prazo do elo |
| `julgar_saude.py` | coletor | 2026-11-25 02:48 | 4136 s | — | ok | — |
| `ler_planos_arboviroses.py` | coletor | 2026-11-25 07:37 | 4 s | — | ok | — |
| `monitorar_atos_resposta.py` | coletor | 2026-11-26 06:52 | 183 s | 25552 | ok | — |
| `monitorar_busca_web.py` | coletor | 2026-11-26 07:03 | 250 s | — | ok | — |
| `monitorar_imprensa_regional.py` | coletor | 2026-11-26 06:39 | 657 s | 40 | ok | — |
| `monitorar_imprensa_saude.py` | coletor | 2026-11-26 06:50 | 101 s | 27 | ok | — |
| `monitorar_politica_por_inteiro.py` | coletor | 2026-11-26 06:55 | 4 s | 19457 | ok | — |
| `monitorar_sinais_federais.py` | coletor | 2026-11-26 06:55 | 9 s | 10 | ok | — |
| `node scripts/verificar_acessibilidade.js` | coletor | 2026-11-22 07:28 | 2 s | — | ok | — |
| `node scripts/verificar_estrutura.js` | coletor | 2026-11-22 07:27 | 4 s | — | ok | — |
| `node scripts/verificar_runtime.js` | coletor | 2026-11-22 07:27 | 6 s | — | ok | — |
| `node scripts/verificar_runtime_financiamento.js` | coletor | 2026-11-22 07:27 | 6 s | — | ok | — |
| `node scripts/verificar_runtime_mapas.js` | coletor | 2026-11-22 07:27 | 4 s | — | ok | — |
| `node scripts/verificar_runtime_saude.js` | coletor | 2026-11-22 07:27 | 4 s | — | ok | — |
| `node scripts/verificar_runtime_sinais.js` | coletor | 2026-11-22 07:27 | 3 s | — | ok | — |
| `node scripts/verificar_texto_publico.js` | coletor | 2026-11-22 07:28 | 26 s | — | ok | — |
| `preencher_fallback_estatico.py` | coletor | 2026-11-22 07:29 | 1 s | — | ok | — |
| `preservar_evidencias.py` | coletor | 2026-11-26 06:34 | 55 s | — | ok | — |
| `processar_contribuicoes.py` | coletor | 2026-11-26 04:37 | 1 s | — | ok | — |
| `reconferir_instrumentos_federais.py` | coletor | 2026-11-25 07:38 | 32 s | — | ok | — |
| `revisar_pistas.py` | coletor | 2026-11-26 04:37 | 1130 s | — | ok | — |
| `scripts/amostra_auditoria_semanal.py` | coletor | 2026-11-26 06:20 | 1 s | — | ok | — |
| `scripts/busca_dirigida_do_ato.py` | coletor | 2026-11-26 07:07 | 58 s | — | ok | — |
| `scripts/corrigir_atribuicao_por_dominio.py` | coletor | 2026-11-26 04:37 | 1 s | — | ok | — |
| `scripts/fechar_saude.py` | coletor | 2026-11-25 04:00 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/preservar_textos_integrais.py` | coletor | 2026-11-26 06:35 | 2 s | — | ok | — |
| `scripts/proveniencia_estadual.py` | coletor | 2026-11-25 04:26 | 1 s | — | ok | — |
| `scripts/reavaliar_fontes_suspensas.py` | coletor | 2026-11-26 05:12 | 788 s | — | ok | — |
| `scripts/sondar_boletim_infogripe.py` | coletor | 2026-11-24 05:20 | 109 s | — | ok | — |
| `scripts/sondar_credenciais.py` | coletor | 2026-11-25 01:15 | 1 s | — | ok | — |
| `scripts/triar_fila.py` | coletor | 2026-11-25 02:09 | 2 s | — | ok | — |
| `scripts/verificar_esquema_de_pista.py` | coletor | 2026-11-25 02:41 | 3 s | — | ok | — |
| `scripts/verificar_funil.py` | coletor | 2026-11-22 03:37 | 0 s | — | ok | — |
| `scripts/verificar_leituras_paradas.py` | coletor | 2026-11-25 02:41 | 3 s | — | ok | — |
| `seguir_pistas.py` | coletor | 2026-11-26 07:08 | 361 s | — | ok | — |
| `sondar_repositorios_estaduais.py` | coletor | 2026-11-25 02:10 | 0 s | — | ok | — |
| `triar_confianca_pistas.py` | coletor | 2026-11-26 07:14 | 2 s | — | ok | — |
| `verificar_consistencia.py` | coletor | 2026-11-22 07:27 | 8 s | — | ok | — |
| `verificar_contribuicoes.py` | coletor | 2026-11-22 06:35 | 1 s | — | ok | — |
| `verificar_evidencias.py` | coletor | 2026-11-22 07:27 | 6 s | — | ok | — |
| `verificar_financiamento.py` | coletor | 2026-11-22 07:27 | 1 s | — | ok | — |
| `verificar_links.py` | coletor | 2026-11-24 02:16 | 209 s | — | **erro** (3 seguidas) | interrompido pelo prazo do elo |
| `verificar_painel.py` | coletor | 2026-11-22 07:27 | 0 s | — | ok | — |
| `verificar_pista_imprensa.py` | coletor | 2026-11-26 07:14 | 129 s | — | ok | — |
| `verificar_saude.py` | coletor | 2026-11-22 07:27 | 0 s | — | ok | — |
| `verificar_sinais.py` | coletor | 2026-11-22 07:27 | 0 s | — | ok | — |
| `verificar_vigencia.py` | coletor | 2026-11-22 06:54 | 1 s | — | ok | — |
