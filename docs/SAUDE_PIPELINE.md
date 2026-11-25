# Saúde do pipeline

Gerado por `scripts/gerar_saude_pipeline.py` a partir de `data/saude_pipeline.json`, que os
jobs escrevem com `scripts/saude_pipeline.py --rodar`. Item 2 do handover de desacoplamento
(27/09/2026). **Arquivo derivado: não se edita à mão.**

Duas classes, e a diferença importa. **Essencial** (`recalcular_mare.py`, `gerar_*.py`): se
erra, o site publica um estado que não corresponde ao dado — reprova o portão. **Coletor**:
fonte fora do ar é rotina, e uma falha isolada não é defeito do pipeline; erro em duas
rodadas seguidas vira alerta, porque aí não é a fonte, é o coletor.

Janela: 2026-11-18 a 2026-11-25 (1639 execução(ões) registrada(s), 7 dias de histórico).

## Alertas

- buscar_planos_fontes_abertas.py: erro em 4 rodadas seguidas — interrompido pelo prazo do elo
- coletar_cadastro_prioritarios.py: erro em 3 rodadas seguidas — X nt2_2025: URLError: <urlopen error [Errno 104] Connection reset by peer> — nada foi gravado
- coletar_pab_brasil.py: erro em 2 rodadas seguidas — urllib.error.URLError: <urlopen error [Errno 104] Connection reset by peer>
- consultar_querido_diario.py: erro em 3 rodadas seguidas — portas tentadas: api.queridodiario.org.br: HTTPError HTTP Error 520: <none> | queridodiario.ok.org.br: HTTPError HTTP Error 520: <none> | api.queridodiario.ok.org.br: URLError <urlopen error [SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] ssl/tls alert handshake fail
- monitorar_imprensa_regional.py: erro em 3 rodadas seguidas — interrompido pelo prazo do elo
- verificar_links.py: erro em 3 rodadas seguidas — interrompido pelo prazo do elo

## Cobertura em 15 dias

cobertura 15d: 5031/5571 com verificação real até 2026-11-25 · por canal: web 208 · QD 527 · consorciado 1699 · DOE 4937

## Última execução de cada script

| script | papel | última execução | duração | itens | status | erro |
|---|---|---|---|---:|---|---|
| `gerar_contadores_financiamento.py` | essencial | 2026-11-22 07:29 | 1 s | — | ok | — |
| `gerar_dados_abertos.py` | essencial | 2026-11-22 07:27 | 1 s | — | ok | — |
| `gerar_feeds.py` | essencial | 2026-11-22 07:27 | 2 s | — | ok | — |
| `gerar_monitor_saude.py` | essencial | 2026-11-22 07:29 | 1 s | — | ok | — |
| `gerar_mortalidade_comparada.py` | essencial | 2026-11-24 07:15 | 1 s | — | ok | — |
| `gerar_painel.py` | essencial | 2026-11-22 07:27 | 1 s | — | ok | — |
| `gerar_prioritarios.py` | essencial | 2026-11-22 07:29 | 0 s | — | ok | — |
| `gerar_resposta.py` | essencial | 2026-11-22 07:29 | 1 s | — | ok | — |
| `gerar_saude_municipio.py` | essencial | 2026-11-24 01:55 | 1 s | — | ok | — |
| `gerar_selos.py` | essencial | 2026-11-22 07:27 | 1 s | — | ok | — |
| `recalcular_mare.py` | essencial | 2026-11-25 07:14 | 5 s | — | ok | — |
| `analisar_decretos.py` | coletor | 2026-11-22 06:54 | 501 s | — | ok | — |
| `aplicar_promocoes_do_juiz.py` | coletor | 2026-11-24 02:21 | 2 s | 0 | ok | — |
| `atualizar.py` | coletor | 2026-11-22 04:10 | 11930 s | 147 | ok | — |
| `atualizar_boletins.py` | coletor | 2026-11-22 04:10 | 21 s | — | ok | — |
| `atualizar_instrumentos_estaduais.py` | coletor | 2026-11-22 06:35 | 82 s | — | **erro** | código de saída 1 |
| `atualizar_populacao.py` | coletor | 2026-11-22 03:31 | 1 s | — | ok | — |
| `atualizar_recursos.py` | coletor | 2026-11-22 06:54 | 2 s | — | **erro** | código de saída 1 |
| `atualizar_transferencias.py` | coletor | 2026-11-22 07:02 | 1476 s | — | ok | — |
| `bash scripts/verificar_derivados.sh --idempotencia` | coletor | 2026-11-22 07:28 | 74 s | — | ok | — |
| `buscar_financiamento_preventivo.py` | coletor | 2026-11-25 07:11 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `buscar_planos_fontes_abertas.py` | coletor | 2026-11-24 17:04 | 7188 s | — | **erro** (4 seguidas) | interrompido pelo prazo do elo |
| `buscar_protocolo_calor.py` | coletor | 2026-11-24 02:01 | 58 s | 41 | ok | — |
| `classificar_planos_municipais.py` | coletor | 2026-11-24 05:24 | 1 s | — | ok | — |
| `classificar_saude_no_plano.py` | coletor | 2026-11-24 01:55 | 1 s | — | ok | — |
| `coletar_arboviroses_sinan.py` | coletor | 2026-11-24 01:54 | 41 s | — | ok | — |
| `coletar_boletim_df_arboviroses.py` | coletor | 2026-11-24 01:51 | 182 s | — | ok | — |
| `coletar_boletim_ms_dengue.py` | coletor | 2026-11-24 01:51 | 20 s | — | ok | — |
| `coletar_boletim_pb_arboviroses.py` | coletor | 2026-11-24 01:54 | 2 s | — | ok | — |
| `coletar_boletim_pe_arboviroses.py` | coletor | 2026-11-24 01:54 | 3 s | — | ok | — |
| `coletar_cadastro_prioritarios.py` | coletor | 2026-11-24 09:20 | 62 s | — | **erro** (3 seguidas) | X nt2_2025: URLError: <urlopen error [Errno 104] Connection reset by peer> — nada foi gravado |
| `coletar_cobertura_qd.py` | coletor | 2026-11-24 05:24 | 7587 s | — | **erro** | interrompido pelo prazo do elo |
| `coletar_datasus_dbc.py` | coletor | 2026-11-24 07:09 | 40 s | — | ok | — |
| `coletar_dda.py` | coletor | 2026-11-24 01:51 | 1 s | — | ok | — |
| `coletar_declarado_nacional.py` | coletor | 2026-11-22 04:32 | 73 s | — | ok | — |
| `coletar_desfechos_saude.py` | coletor | 2026-11-24 01:45 | 326 s | — | ok | — |
| `coletar_diarios_consorciados.py` | coletor | 2026-11-25 03:13 | 3007 s | 74 | ok | — |
| `coletar_diarios_municipais.py` | coletor | 2026-11-25 03:13 | 2 s | 0 | ok | — |
| `coletar_doe.py` | coletor | 2026-11-25 04:03 | 1484 s | — | ok | — |
| `coletar_edicoes_doe.py` | coletor | 2026-11-25 03:01 | 4801 s | — | **erro** | interrompido pelo prazo do elo |
| `coletar_espin.py` | coletor | 2026-11-25 04:21 | 271 s | — | ok | — |
| `coletar_execucao_mps.py` | coletor | 2026-11-22 06:35 | 26 s | — | ok | — |
| `coletar_financiamento.py` | coletor | 2026-11-22 06:35 | 2 s | — | ok | — |
| `coletar_mapbiomas.py` | coletor | 2026-11-24 19:59 | 1 s | — | ok | — |
| `coletar_normais_inmet.py` | coletor | 2026-11-24 05:19 | 4 s | — | ok | — |
| `coletar_obitos.py` | coletor | 2026-11-24 07:12 | 3 s | — | ok | — |
| `coletar_obitos_registro_civil.py` | coletor | 2026-11-24 01:55 | 18 s | — | ok | — |
| `coletar_pab_brasil.py` | coletor | 2026-11-24 05:19 | 36 s | — | **erro** (2 seguidas) | urllib.error.URLError: <urlopen error [Errno 104] Connection reset by peer> |
| `coletar_planos_arboviroses.py` | coletor | 2026-11-24 07:55 | 1502 s | — | ok | — |
| `coletar_prioritarios_mma.py` | coletor | 2026-11-24 05:19 | 3 s | — | ok | — |
| `coletar_projecao_cil.py` | coletor | 2026-11-24 07:15 | 3 s | — | ok | — |
| `coletar_recursos_resposta.py` | coletor | 2026-11-25 04:30 | 40 s | — | **erro** | urllib.error.HTTPError: HTTP Error 502: Bad Gateway |
| `coletar_s2id.py` | coletor | 2026-11-25 04:28 | 103 s | — | ok | — |
| `coletar_saude.py` | coletor | 2026-11-24 01:39 | 55 s | — | ok | — |
| `coletar_saude_estadual.py` | coletor | 2026-11-25 04:00 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `coletar_semiarido_sudene.py` | coletor | 2026-11-24 05:19 | 2 s | — | ok | — |
| `coletar_sg_esus.py` | coletor | 2026-11-24 01:47 | 9 s | — | ok | — |
| `coletar_siconfi_182.py` | coletor | 2026-11-22 06:35 | 0 s | — | ok | — |
| `coletar_sih.py` | coletor | 2026-11-24 07:15 | 2421 s | — | ok | — |
| `coletar_sim.py` | coletor | 2026-11-24 07:12 | 153 s | — | ok | — |
| `coletar_sinais_risco.py` | coletor | 2026-11-24 01:23 | 176 s | — | ok | — |
| `coletar_sisab.py` | coletor | 2026-11-24 07:10 | 144 s | — | ok | — |
| `coletar_srag_gripe.py` | coletor | 2026-11-24 05:22 | 144 s | — | ok | — |
| `coletar_srag_sivep.py` | coletor | 2026-11-24 01:47 | 38 s | — | ok | — |
| `coletar_transferegov.py` | coletor | 2026-11-22 06:35 | 2 s | — | ok | — |
| `coletar_transferencias_municipais.py` | coletor | 2026-11-24 01:26 | 74 s | — | ok | — |
| `conferir_emergencias_estaduais.py` | coletor | 2026-11-24 01:28 | 1 s | — | ok | — |
| `consultar_querido_diario.py` | coletor | 2026-11-25 03:12 | 63 s | — | **erro** (3 seguidas) | portas tentadas: api.queridodiario.org.br: HTTPError HTTP Error 520: <none> \| queridodiario.ok.org.br: HTTPError HTTP E |
| `descobrir_dominios.py` | coletor | 2026-11-24 07:31 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `descobrir_planos.py` | coletor | 2026-11-25 07:11 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `desfechos_sus.py` | coletor | 2026-11-24 07:12 | 1 s | — | ok | — |
| `detectar_marcos_federais.py` | coletor | 2026-11-25 07:11 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `juiz.py` | coletor | 2026-11-24 15:45 | 14401 s | — | **erro** | interrompido pelo prazo do elo |
| `julgar_e_aplicar_descobertas.py` | coletor | 2026-11-24 08:57 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `julgar_filas.py` | coletor | 2026-11-24 01:59 | 1340 s | — | ok | — |
| `julgar_saude.py` | coletor | 2026-11-25 02:48 | 4136 s | — | ok | — |
| `ler_planos_arboviroses.py` | coletor | 2026-11-24 08:20 | 4 s | — | ok | — |
| `monitorar_atos_resposta.py` | coletor | 2026-11-25 07:11 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `monitorar_busca_web.py` | coletor | 2026-11-25 07:11 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `monitorar_imprensa_regional.py` | coletor | 2026-11-25 06:29 | 2502 s | 19393 | **erro** (3 seguidas) | interrompido pelo prazo do elo |
| `monitorar_imprensa_saude.py` | coletor | 2026-11-25 07:11 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `monitorar_politica_por_inteiro.py` | coletor | 2026-11-25 07:11 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `monitorar_sinais_federais.py` | coletor | 2026-11-25 07:11 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `node scripts/verificar_acessibilidade.js` | coletor | 2026-11-22 07:28 | 2 s | — | ok | — |
| `node scripts/verificar_estrutura.js` | coletor | 2026-11-22 07:27 | 4 s | — | ok | — |
| `node scripts/verificar_runtime.js` | coletor | 2026-11-22 07:27 | 6 s | — | ok | — |
| `node scripts/verificar_runtime_financiamento.js` | coletor | 2026-11-22 07:27 | 6 s | — | ok | — |
| `node scripts/verificar_runtime_mapas.js` | coletor | 2026-11-22 07:27 | 4 s | — | ok | — |
| `node scripts/verificar_runtime_saude.js` | coletor | 2026-11-22 07:27 | 4 s | — | ok | — |
| `node scripts/verificar_runtime_sinais.js` | coletor | 2026-11-22 07:27 | 3 s | — | ok | — |
| `node scripts/verificar_texto_publico.js` | coletor | 2026-11-22 07:28 | 26 s | — | ok | — |
| `preencher_fallback_estatico.py` | coletor | 2026-11-22 07:29 | 1 s | — | ok | — |
| `preservar_evidencias.py` | coletor | 2026-11-25 06:22 | 119 s | — | ok | — |
| `processar_contribuicoes.py` | coletor | 2026-11-24 08:57 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `reconferir_instrumentos_federais.py` | coletor | 2026-11-24 08:20 | 32 s | — | ok | — |
| `revisar_pistas.py` | coletor | 2026-11-24 08:57 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/amostra_auditoria_semanal.py` | coletor | 2026-11-24 08:57 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/busca_dirigida_do_ato.py` | coletor | 2026-11-25 07:11 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/corrigir_atribuicao_por_dominio.py` | coletor | 2026-11-24 08:57 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/fechar_saude.py` | coletor | 2026-11-25 04:00 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/preservar_textos_integrais.py` | coletor | 2026-11-25 06:24 | 2 s | — | ok | — |
| `scripts/proveniencia_estadual.py` | coletor | 2026-11-25 04:26 | 1 s | — | ok | — |
| `scripts/reavaliar_fontes_suspensas.py` | coletor | 2026-11-25 05:09 | 793 s | — | ok | — |
| `scripts/remediar_segredos_evidencias.py` | coletor | 2026-11-18 12:52 | 165 s | — | ok | — |
| `scripts/sondar_boletim_infogripe.py` | coletor | 2026-11-24 05:20 | 109 s | — | ok | — |
| `scripts/sondar_credenciais.py` | coletor | 2026-11-24 01:27 | 2 s | — | ok | — |
| `scripts/triar_fila.py` | coletor | 2026-11-24 01:59 | 2 s | — | ok | — |
| `scripts/verificar_esquema_de_pista.py` | coletor | 2026-11-24 02:21 | 3 s | — | ok | — |
| `scripts/verificar_funil.py` | coletor | 2026-11-22 03:37 | 0 s | — | ok | — |
| `scripts/verificar_leituras_paradas.py` | coletor | 2026-11-24 02:21 | 2 s | — | ok | — |
| `seguir_pistas.py` | coletor | 2026-11-25 07:11 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `sondar_repositorios_estaduais.py` | coletor | 2026-11-24 02:12 | 1 s | — | ok | — |
| `triar_confianca_pistas.py` | coletor | 2026-11-25 07:11 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `verificar_consistencia.py` | coletor | 2026-11-22 07:27 | 8 s | — | ok | — |
| `verificar_contribuicoes.py` | coletor | 2026-11-22 06:35 | 1 s | — | ok | — |
| `verificar_evidencias.py` | coletor | 2026-11-22 07:27 | 6 s | — | ok | — |
| `verificar_financiamento.py` | coletor | 2026-11-22 07:27 | 1 s | — | ok | — |
| `verificar_links.py` | coletor | 2026-11-24 02:16 | 209 s | — | **erro** (3 seguidas) | interrompido pelo prazo do elo |
| `verificar_painel.py` | coletor | 2026-11-22 07:27 | 0 s | — | ok | — |
| `verificar_pista_imprensa.py` | coletor | 2026-11-25 07:11 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `verificar_saude.py` | coletor | 2026-11-22 07:27 | 0 s | — | ok | — |
| `verificar_sinais.py` | coletor | 2026-11-22 07:27 | 0 s | — | ok | — |
| `verificar_vigencia.py` | coletor | 2026-11-22 06:54 | 1 s | — | ok | — |
