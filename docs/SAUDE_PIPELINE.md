# Saúde do pipeline

Gerado por `scripts/gerar_saude_pipeline.py` a partir de `data/saude_pipeline.json`, que os
jobs escrevem com `scripts/saude_pipeline.py --rodar`. Item 2 do handover de desacoplamento
(27/09/2026). **Arquivo derivado: não se edita à mão.**

Duas classes, e a diferença importa. **Essencial** (`recalcular_mare.py`, `gerar_*.py`): se
erra, o site publica um estado que não corresponde ao dado — reprova o portão. **Coletor**:
fonte fora do ar é rotina, e uma falha isolada não é defeito do pipeline; erro em duas
rodadas seguidas vira alerta, porque aí não é a fonte, é o coletor.

Janela: 2026-11-06 a 2026-11-13 (1422 execução(ões) registrada(s), 7 dias de histórico).

## Alertas

- consultar_querido_diario.py: erro em 6 rodadas seguidas — portas tentadas: api.queridodiario.org.br: TimeoutError The read operation timed out | queridodiario.ok.org.br: HTTPError HTTP Error 520: <none> | api.queridodiario.ok.org.br: URLError <urlopen error [SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] ssl/tls alert handshake fail

## Cobertura em 15 dias

cobertura 15d: 5031/5571 com verificação real até 2026-11-13 · por canal: web 240 · QD 527 · consorciado 1695 · DOE 4937

## Última execução de cada script

| script | papel | última execução | duração | itens | status | erro |
|---|---|---|---|---:|---|---|
| `gerar_contadores_financiamento.py` | essencial | 2026-11-11 07:52 | 1 s | — | ok | — |
| `gerar_monitor_saude.py` | essencial | 2026-11-11 07:39 | 0 s | — | ok | — |
| `gerar_mortalidade_comparada.py` | essencial | 2026-11-13 07:17 | 0 s | — | ok | — |
| `gerar_saude_municipio.py` | essencial | 2026-11-12 01:37 | 0 s | — | ok | — |
| `recalcular_mare.py` | essencial | 2026-11-13 01:13 | 4 s | — | ok | — |
| `aplicar_promocoes_do_juiz.py` | coletor | 2026-11-13 08:57 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `atualizar.py` | coletor | 2026-11-11 07:39 | 0 s | — | ok | — |
| `atualizar_populacao.py` | coletor | 2026-11-11 07:15 | 0 s | — | ok | — |
| `buscar_protocolo_calor.py` | coletor | 2026-11-10 01:21 | 19 s | 13 | ok | — |
| `classificar_planos_municipais.py` | coletor | 2026-11-07 01:19 | 1 s | — | ok | — |
| `classificar_saude_no_plano.py` | coletor | 2026-11-12 01:37 | 2 s | — | ok | — |
| `coletar_arboviroses_sinan.py` | coletor | 2026-11-12 01:36 | 54 s | — | ok | — |
| `coletar_boletim_df_arboviroses.py` | coletor | 2026-11-12 01:31 | 278 s | — | ok | — |
| `coletar_boletim_ms_dengue.py` | coletor | 2026-11-12 01:31 | 20 s | — | ok | — |
| `coletar_boletim_pb_arboviroses.py` | coletor | 2026-11-12 01:36 | 3 s | — | ok | — |
| `coletar_boletim_pe_arboviroses.py` | coletor | 2026-11-12 01:36 | 6 s | — | ok | — |
| `coletar_cadastro_prioritarios.py` | coletor | 2026-11-07 01:14 | 28 s | — | ok | — |
| `coletar_cobertura_qd.py` | coletor | 2026-11-08 01:19 | 7542 s | — | **erro** | interrompido pelo prazo do elo |
| `coletar_datasus_dbc.py` | coletor | 2026-11-13 07:13 | 42 s | — | ok | — |
| `coletar_dda.py` | coletor | 2026-11-12 01:30 | 57 s | — | ok | — |
| `coletar_desfechos_saude.py` | coletor | 2026-11-12 01:22 | 459 s | — | ok | — |
| `coletar_diarios_consorciados.py` | coletor | 2026-11-12 01:20 | 2764 s | 55 | ok | — |
| `coletar_diarios_municipais.py` | coletor | 2026-11-12 01:20 | 2 s | 0 | ok | — |
| `coletar_doe.py` | coletor | 2026-11-12 02:06 | 1644 s | — | ok | — |
| `coletar_edicoes_doe.py` | coletor | 2026-11-13 03:11 | 2624 s | — | ok | — |
| `coletar_espin.py` | coletor | 2026-11-13 03:55 | 251 s | — | ok | — |
| `coletar_execucao_mps.py` | coletor | 2026-11-11 07:52 | 34 s | — | ok | — |
| `coletar_financiamento.py` | coletor | 2026-11-11 07:52 | 2 s | 0 | ok | — |
| `coletar_fns.py` | coletor | 2026-11-09 20:35 | 25 s | — | ok | — |
| `coletar_normais_inmet.py` | coletor | 2026-11-07 01:15 | 18 s | — | ok | — |
| `coletar_obitos.py` | coletor | 2026-11-13 07:16 | 4 s | — | ok | — |
| `coletar_obitos_registro_civil.py` | coletor | 2026-11-12 01:37 | 33 s | — | ok | — |
| `coletar_pab_brasil.py` | coletor | 2026-11-13 15:56 | 119 s | — | ok | — |
| `coletar_planos_arboviroses.py` | coletor | 2026-11-13 07:17 | 1529 s | — | ok | — |
| `coletar_prioritarios_mma.py` | coletor | 2026-11-07 01:15 | 2 s | — | ok | — |
| `coletar_projecao_cil.py` | coletor | 2026-11-13 07:17 | 3 s | — | ok | — |
| `coletar_recursos_resposta.py` | coletor | 2026-11-12 02:53 | 50 s | — | ok | — |
| `coletar_s2id.py` | coletor | 2026-11-12 02:33 | 1190 s | — | ok | — |
| `coletar_saude.py` | coletor | 2026-11-12 01:13 | 86 s | — | ok | — |
| `coletar_saude_estadual.py` | coletor | 2026-11-11 03:09 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `coletar_semiarido_sudene.py` | coletor | 2026-11-07 01:15 | 3 s | — | ok | — |
| `coletar_sg_esus.py` | coletor | 2026-11-13 03:03 | 11 s | — | ok | — |
| `coletar_siconfi_182.py` | coletor | 2026-11-11 07:53 | 1 s | 5571 | ok | — |
| `coletar_sih.py` | coletor | 2026-11-13 07:17 | 6 s | — | sem novidade | — |
| `coletar_sim.py` | coletor | 2026-11-13 07:16 | 8 s | — | sem novidade | — |
| `coletar_sinais_risco.py` | coletor | 2026-11-13 20:03 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `coletar_sisab.py` | coletor | 2026-11-13 07:14 | 160 s | — | ok | — |
| `coletar_srag_gripe.py` | coletor | 2026-11-07 01:17 | 144 s | — | ok | — |
| `coletar_srag_sivep.py` | coletor | 2026-11-13 03:03 | 43 s | — | ok | — |
| `coletar_transferegov.py` | coletor | 2026-11-11 07:52 | 2 s | — | ok | — |
| `coletar_transferencias_municipais.py` | coletor | 2026-11-13 08:26 | 61 s | — | ok | — |
| `consultar_querido_diario.py` | coletor | 2026-11-12 01:17 | 137 s | — | **erro** (6 seguidas) | portas tentadas: api.queridodiario.org.br: TimeoutError The read operation timed out \| queridodiario.ok.org.br: HTTPErr |
| `descobrir_dominios.py` | coletor | 2026-11-08 03:25 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `descobrir_planos.py` | coletor | 2026-11-13 08:45 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `desfechos_sus.py` | coletor | 2026-11-13 07:16 | 0 s | — | ok | — |
| `detectar_marcos_federais.py` | coletor | 2026-11-13 08:45 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `julgar_e_aplicar_descobertas.py` | coletor | 2026-11-13 08:57 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `julgar_filas.py` | coletor | 2026-11-13 14:38 | 343 s | — | ok | — |
| `julgar_saude.py` | coletor | 2026-11-11 01:59 | 4184 s | — | **erro** | interrompido pelo prazo do elo |
| `ler_planos_arboviroses.py` | coletor | 2026-11-13 07:42 | 4 s | — | ok | — |
| `monitorar_atos_resposta.py` | coletor | 2026-11-13 08:45 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `monitorar_busca_web.py` | coletor | 2026-11-13 08:45 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `monitorar_imprensa_regional.py` | coletor | 2026-11-13 08:43 | 70 s | 18873 | **erro** | interrompido pelo prazo do elo |
| `monitorar_imprensa_saude.py` | coletor | 2026-11-13 08:45 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `monitorar_politica_por_inteiro.py` | coletor | 2026-11-13 08:45 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `monitorar_sinais_federais.py` | coletor | 2026-11-13 08:45 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `preservar_evidencias.py` | coletor | 2026-11-13 08:27 | 52 s | — | ok | — |
| `processar_contribuicoes.py` | coletor | 2026-11-11 07:15 | 1 s | — | ok | — |
| `python3` | coletor | 2026-11-08 13:24 | 152 s | — | ok | — |
| `reconferir_instrumentos_federais.py` | coletor | 2026-11-13 07:42 | 1 s | — | ok | — |
| `revisar_pistas.py` | coletor | 2026-11-13 08:57 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/amostra_auditoria_semanal.py` | coletor | 2026-11-13 08:57 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/corrigir_atribuicao_por_dominio.py` | coletor | 2026-11-13 08:57 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/diagnostico_fontes_saude.py` | coletor | 2026-11-07 19:03 | 372 s | — | ok | — |
| `scripts/fechar_saude.py` | coletor | 2026-11-11 03:09 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/pistas_capitais_09_11.py` | coletor | 2026-11-09 19:06 | 2 s | — | ok | — |
| `scripts/preservar_textos_integrais.py` | coletor | 2026-11-13 08:28 | 2 s | — | ok | — |
| `scripts/proveniencia_estadual.py` | coletor | 2026-11-13 03:59 | 1 s | — | ok | — |
| `scripts/reavaliar_fontes_suspensas.py` | coletor | 2026-11-13 05:14 | 1047 s | — | ok | — |
| `scripts/sondar_boletim_infogripe.py` | coletor | 2026-11-07 01:15 | 97 s | — | ok | — |
| `scripts/sondar_credenciais.py` | coletor | 2026-11-13 08:27 | 3 s | — | ok | — |
| `scripts/triar_fila.py` | coletor | 2026-11-13 08:50 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/verificar_esquema_de_pista.py` | coletor | 2026-11-13 08:50 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/verificar_funil.py` | coletor | 2026-11-11 07:21 | 1 s | — | ok | — |
| `seguir_pistas.py` | coletor | 2026-11-13 08:45 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `sondar_repositorios_estaduais.py` | coletor | 2026-11-13 14:58 | 3116 s | — | ok | — |
| `triar_confianca_pistas.py` | coletor | 2026-11-13 08:45 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `verificar_links.py` | coletor | 2026-11-10 01:39 | 180 s | — | **erro** | interrompido pelo prazo do elo |
| `verificar_pista_imprensa.py` | coletor | 2026-11-13 08:45 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
