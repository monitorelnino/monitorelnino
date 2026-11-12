# Saúde do pipeline

Gerado por `scripts/gerar_saude_pipeline.py` a partir de `data/saude_pipeline.json`, que os
jobs escrevem com `scripts/saude_pipeline.py --rodar`. Item 2 do handover de desacoplamento
(27/09/2026). **Arquivo derivado: não se edita à mão.**

Duas classes, e a diferença importa. **Essencial** (`recalcular_mare.py`, `gerar_*.py`): se
erra, o site publica um estado que não corresponde ao dado — reprova o portão. **Coletor**:
fonte fora do ar é rotina, e uma falha isolada não é defeito do pipeline; erro em duas
rodadas seguidas vira alerta, porque aí não é a fonte, é o coletor.

Janela: 2026-11-05 a 2026-11-12 (1340 execução(ões) registrada(s), 7 dias de histórico).

## Alertas

- consultar_querido_diario.py: erro em 5 rodadas seguidas — portas tentadas: api.queridodiario.org.br: HTTPError HTTP Error 503: Service Unavailable | queridodiario.ok.org.br: HTTPError HTTP Error 503: Service Unavailable | api.queridodiario.ok.org.br: URLError <urlopen error [SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] ssl/tls alert handshake fail

## Cobertura em 15 dias

cobertura 15d: 5031/5571 com verificação real até 2026-11-12 · por canal: web 224 · QD 527 · consorciado 1701 · DOE 4937

## Última execução de cada script

| script | papel | última execução | duração | itens | status | erro |
|---|---|---|---|---:|---|---|
| `gerar_contadores_financiamento.py` | essencial | 2026-11-11 07:52 | 1 s | — | ok | — |
| `gerar_monitor_saude.py` | essencial | 2026-11-11 07:39 | 0 s | — | ok | — |
| `gerar_mortalidade_comparada.py` | essencial | 2026-11-12 07:19 | 1 s | — | ok | — |
| `gerar_saude_municipio.py` | essencial | 2026-11-11 01:54 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `recalcular_mare.py` | essencial | 2026-11-12 07:49 | 4 s | — | ok | — |
| `aplicar_promocoes_do_juiz.py` | coletor | 2026-11-12 07:32 | 1 s | — | ok | — |
| `atualizar.py` | coletor | 2026-11-11 07:39 | 0 s | — | ok | — |
| `atualizar_populacao.py` | coletor | 2026-11-11 07:15 | 0 s | — | ok | — |
| `buscar_protocolo_calor.py` | coletor | 2026-11-10 01:21 | 19 s | 13 | ok | — |
| `classificar_planos_municipais.py` | coletor | 2026-11-07 01:19 | 1 s | — | ok | — |
| `classificar_saude_no_plano.py` | coletor | 2026-11-11 01:54 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `coletar_arboviroses_sinan.py` | coletor | 2026-11-11 01:38 | 40 s | — | ok | — |
| `coletar_boletim_df_arboviroses.py` | coletor | 2026-11-11 01:33 | 284 s | — | ok | — |
| `coletar_boletim_ms_dengue.py` | coletor | 2026-11-11 01:33 | 19 s | — | ok | — |
| `coletar_boletim_pb_arboviroses.py` | coletor | 2026-11-11 01:38 | 4 s | — | ok | — |
| `coletar_boletim_pe_arboviroses.py` | coletor | 2026-11-11 01:38 | 6 s | — | ok | — |
| `coletar_cadastro_prioritarios.py` | coletor | 2026-11-07 01:14 | 28 s | — | ok | — |
| `coletar_cobertura_qd.py` | coletor | 2026-11-08 01:19 | 7542 s | — | **erro** | interrompido pelo prazo do elo |
| `coletar_datasus_dbc.py` | coletor | 2026-11-12 07:14 | 42 s | — | ok | — |
| `coletar_dda.py` | coletor | 2026-11-11 01:32 | 58 s | — | ok | — |
| `coletar_desfechos_saude.py` | coletor | 2026-11-11 01:24 | 476 s | — | ok | — |
| `coletar_diarios_consorciados.py` | coletor | 2026-11-11 01:20 | 3396 s | 42 | ok | — |
| `coletar_diarios_municipais.py` | coletor | 2026-11-11 01:19 | 2 s | 0 | ok | — |
| `coletar_doe.py` | coletor | 2026-11-12 02:16 | 3702 s | — | ok | — |
| `coletar_edicoes_doe.py` | coletor | 2026-11-11 01:57 | 4801 s | — | **erro** | interrompido pelo prazo do elo |
| `coletar_espin.py` | coletor | 2026-11-11 03:17 | 720 s | — | ok | — |
| `coletar_execucao_mps.py` | coletor | 2026-11-11 07:52 | 34 s | — | ok | — |
| `coletar_financiamento.py` | coletor | 2026-11-11 07:52 | 2 s | 0 | ok | — |
| `coletar_fns.py` | coletor | 2026-11-09 20:35 | 25 s | — | ok | — |
| `coletar_normais_inmet.py` | coletor | 2026-11-07 01:15 | 18 s | — | ok | — |
| `coletar_obitos.py` | coletor | 2026-11-12 07:19 | 4 s | — | ok | — |
| `coletar_obitos_registro_civil.py` | coletor | 2026-11-11 01:39 | 922 s | — | **erro** | interrompido pelo prazo do elo |
| `coletar_planos_arboviroses.py` | coletor | 2026-11-12 07:19 | 1176 s | — | ok | — |
| `coletar_prioritarios_mma.py` | coletor | 2026-11-07 01:15 | 2 s | — | ok | — |
| `coletar_projecao_cil.py` | coletor | 2026-11-12 07:19 | 2 s | — | ok | — |
| `coletar_recursos_resposta.py` | coletor | 2026-11-12 03:36 | 52 s | — | ok | — |
| `coletar_s2id.py` | coletor | 2026-11-12 03:18 | 1119 s | — | ok | — |
| `coletar_saude.py` | coletor | 2026-11-11 01:15 | 76 s | — | ok | — |
| `coletar_saude_estadual.py` | coletor | 2026-11-11 03:09 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `coletar_semiarido_sudene.py` | coletor | 2026-11-07 01:15 | 3 s | — | ok | — |
| `coletar_sg_esus.py` | coletor | 2026-11-12 03:45 | 10 s | — | ok | — |
| `coletar_siconfi_182.py` | coletor | 2026-11-11 07:53 | 1 s | 5571 | ok | — |
| `coletar_sih.py` | coletor | 2026-11-12 07:19 | 5 s | — | sem novidade | — |
| `coletar_sim.py` | coletor | 2026-11-12 07:19 | 8 s | — | sem novidade | — |
| `coletar_sinais_risco.py` | coletor | 2026-11-12 07:38 | 115 s | — | ok | — |
| `coletar_sisab.py` | coletor | 2026-11-12 07:15 | 205 s | — | ok | — |
| `coletar_srag_gripe.py` | coletor | 2026-11-07 01:17 | 144 s | — | ok | — |
| `coletar_srag_sivep.py` | coletor | 2026-11-12 03:44 | 38 s | — | ok | — |
| `coletar_transferegov.py` | coletor | 2026-11-11 07:52 | 2 s | — | ok | — |
| `coletar_transferencias_municipais.py` | coletor | 2026-11-12 07:40 | 76 s | — | ok | — |
| `consultar_querido_diario.py` | coletor | 2026-11-11 01:19 | 3 s | — | **erro** (5 seguidas) | portas tentadas: api.queridodiario.org.br: HTTPError HTTP Error 503: Service Unavailable \| queridodiario.ok.org.br: HTT |
| `descobrir_dominios.py` | coletor | 2026-11-08 03:25 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `descobrir_planos.py` | coletor | 2026-11-12 06:59 | 551 s | — | ok | — |
| `desfechos_sus.py` | coletor | 2026-11-12 07:19 | 1 s | — | ok | — |
| `detectar_marcos_federais.py` | coletor | 2026-11-12 06:58 | 32 s | — | ok | — |
| `julgar_e_aplicar_descobertas.py` | coletor | 2026-11-12 07:32 | 2 s | — | ok | — |
| `julgar_filas.py` | coletor | 2026-11-12 07:32 | 33 s | — | ok | — |
| `julgar_saude.py` | coletor | 2026-11-11 01:59 | 4184 s | — | **erro** | interrompido pelo prazo do elo |
| `ler_planos_arboviroses.py` | coletor | 2026-11-12 07:39 | 5 s | — | ok | — |
| `monitorar_atos_resposta.py` | coletor | 2026-11-12 06:56 | 101 s | 24652 | ok | — |
| `monitorar_busca_web.py` | coletor | 2026-11-12 07:08 | 243 s | — | ok | — |
| `monitorar_imprensa_regional.py` | coletor | 2026-11-12 06:41 | 817 s | 40 | ok | — |
| `monitorar_imprensa_saude.py` | coletor | 2026-11-12 06:55 | 103 s | 27 | ok | — |
| `monitorar_politica_por_inteiro.py` | coletor | 2026-11-12 06:58 | 3 s | 18721 | ok | — |
| `monitorar_sinais_federais.py` | coletor | 2026-11-12 06:58 | 5 s | 10 | ok | — |
| `preservar_evidencias.py` | coletor | 2026-11-12 06:25 | 60 s | — | ok | — |
| `processar_contribuicoes.py` | coletor | 2026-11-11 07:15 | 1 s | — | ok | — |
| `python3` | coletor | 2026-11-08 13:24 | 152 s | — | ok | — |
| `reconferir_instrumentos_federais.py` | coletor | 2026-11-12 07:39 | 3 s | — | ok | — |
| `revisar_pistas.py` | coletor | 2026-11-12 07:23 | 536 s | — | ok | — |
| `scripts/amostra_auditoria_semanal.py` | coletor | 2026-11-12 07:32 | 1 s | — | ok | — |
| `scripts/corrigir_atribuicao_por_dominio.py` | coletor | 2026-11-12 07:23 | 1 s | — | ok | — |
| `scripts/diagnostico_fontes_saude.py` | coletor | 2026-11-07 19:03 | 372 s | — | ok | — |
| `scripts/fechar_saude.py` | coletor | 2026-11-11 03:09 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/pistas_capitais_09_11.py` | coletor | 2026-11-09 19:06 | 2 s | — | ok | — |
| `scripts/preservar_textos_integrais.py` | coletor | 2026-11-12 06:26 | 3 s | — | ok | — |
| `scripts/proveniencia_estadual.py` | coletor | 2026-11-11 03:29 | 1 s | — | ok | — |
| `scripts/reavaliar_fontes_suspensas.py` | coletor | 2026-11-12 05:07 | 1092 s | — | ok | — |
| `scripts/sondar_boletim_infogripe.py` | coletor | 2026-11-07 01:15 | 97 s | — | ok | — |
| `scripts/sondar_credenciais.py` | coletor | 2026-11-12 07:41 | 2 s | — | ok | — |
| `scripts/triar_fila.py` | coletor | 2026-11-12 03:51 | 2 s | — | ok | — |
| `scripts/verificar_esquema_de_pista.py` | coletor | 2026-11-12 04:02 | 2 s | — | ok | — |
| `scripts/verificar_funil.py` | coletor | 2026-11-11 07:21 | 1 s | — | ok | — |
| `seguir_pistas.py` | coletor | 2026-11-12 07:12 | 195 s | — | ok | — |
| `triar_confianca_pistas.py` | coletor | 2026-11-12 07:15 | 3 s | — | ok | — |
| `verificar_links.py` | coletor | 2026-11-10 01:39 | 180 s | — | **erro** | interrompido pelo prazo do elo |
| `verificar_pista_imprensa.py` | coletor | 2026-11-12 07:15 | 4 s | — | ok | — |
