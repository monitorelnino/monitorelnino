# Saúde do pipeline

Gerado por `scripts/gerar_saude_pipeline.py` a partir de `data/saude_pipeline.json`, que os
jobs escrevem com `scripts/saude_pipeline.py --rodar`. Item 2 do handover de desacoplamento
(27/09/2026). **Arquivo derivado: não se edita à mão.**

Duas classes, e a diferença importa. **Essencial** (`recalcular_mare.py`, `gerar_*.py`): se
erra, o site publica um estado que não corresponde ao dado — reprova o portão. **Coletor**:
fonte fora do ar é rotina, e uma falha isolada não é defeito do pipeline; erro em duas
rodadas seguidas vira alerta, porque aí não é a fonte, é o coletor.

Janela: 2026-11-03 a 2026-11-10 (1398 execução(ões) registrada(s), 7 dias de histórico).

## Alertas

- consultar_querido_diario.py: erro em 3 rodadas seguidas — portas tentadas: api.queridodiario.org.br: TimeoutError The read operation timed out | queridodiario.ok.org.br: TimeoutError The read operation timed out | api.queridodiario.ok.org.br: URLError <urlopen error [SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] ssl/tls alert handshake fail

## Cobertura em 15 dias

cobertura 15d: 5031/5571 com verificação real até 2026-11-10 · por canal: web 192 · QD 527 · consorciado 1690 · DOE 4937

## Última execução de cada script

| script | papel | última execução | duração | itens | status | erro |
|---|---|---|---|---:|---|---|
| `gerar_monitor_saude.py` | essencial | 2026-11-07 01:45 | 0 s | — | ok | — |
| `gerar_mortalidade_comparada.py` | essencial | 2026-11-10 07:40 | 1 s | — | ok | — |
| `gerar_saude_municipio.py` | essencial | 2026-11-09 01:34 | 1 s | — | ok | — |
| `recalcular_mare.py` | essencial | 2026-11-10 23:01 | 3 s | — | ok | — |
| `aplicar_promocoes_do_juiz.py` | coletor | 2026-11-10 16:19 | 2 s | — | ok | — |
| `atualizar.py` | coletor | 2026-11-07 01:43 | 104 s | — | ok | — |
| `atualizar_populacao.py` | coletor | 2026-11-07 01:15 | 1 s | — | ok | — |
| `buscar_protocolo_calor.py` | coletor | 2026-11-07 01:28 | 91 s | 4 | ok | — |
| `classificar_planos_municipais.py` | coletor | 2026-11-07 01:19 | 1 s | — | ok | — |
| `classificar_saude_no_plano.py` | coletor | 2026-11-09 01:34 | 2 s | — | ok | — |
| `coletar_arboviroses_sinan.py` | coletor | 2026-11-09 01:33 | 58 s | — | ok | — |
| `coletar_boletim_df_arboviroses.py` | coletor | 2026-11-09 01:27 | 327 s | — | ok | — |
| `coletar_boletim_ms_dengue.py` | coletor | 2026-11-09 01:27 | 18 s | — | ok | — |
| `coletar_boletim_pb_arboviroses.py` | coletor | 2026-11-09 01:33 | 3 s | — | ok | — |
| `coletar_boletim_pe_arboviroses.py` | coletor | 2026-11-09 01:33 | 6 s | — | ok | — |
| `coletar_cadastro_prioritarios.py` | coletor | 2026-11-07 01:14 | 28 s | — | ok | — |
| `coletar_cobertura_qd.py` | coletor | 2026-11-08 01:19 | 7542 s | — | **erro** | interrompido pelo prazo do elo |
| `coletar_datasus_dbc.py` | coletor | 2026-11-10 07:37 | 42 s | — | ok | — |
| `coletar_dda.py` | coletor | 2026-11-09 01:26 | 54 s | — | ok | — |
| `coletar_desfechos_saude.py` | coletor | 2026-11-09 01:21 | 347 s | — | ok | — |
| `coletar_diarios_consorciados.py` | coletor | 2026-11-09 01:23 | 2203 s | 28 | ok | — |
| `coletar_diarios_municipais.py` | coletor | 2026-11-09 01:23 | 2 s | 0 | ok | — |
| `coletar_doe.py` | coletor | 2026-11-09 01:59 | 3178 s | — | ok | — |
| `coletar_edicoes_doe.py` | coletor | 2026-11-09 02:54 | 4801 s | — | **erro** | interrompido pelo prazo do elo |
| `coletar_espin.py` | coletor | 2026-11-09 04:14 | 417 s | — | ok | — |
| `coletar_fns.py` | coletor | 2026-11-09 20:35 | 25 s | — | ok | — |
| `coletar_normais_inmet.py` | coletor | 2026-11-07 01:15 | 18 s | — | ok | — |
| `coletar_obitos.py` | coletor | 2026-11-10 07:39 | 9 s | — | ok | — |
| `coletar_obitos_registro_civil.py` | coletor | 2026-11-09 01:34 | 21 s | — | ok | — |
| `coletar_planos_arboviroses.py` | coletor | 2026-11-10 07:40 | 672 s | — | ok | — |
| `coletar_prioritarios_mma.py` | coletor | 2026-11-07 01:15 | 2 s | — | ok | — |
| `coletar_projecao_cil.py` | coletor | 2026-11-10 07:40 | 2 s | — | ok | — |
| `coletar_recursos_resposta.py` | coletor | 2026-11-10 03:09 | 48 s | — | ok | — |
| `coletar_s2id.py` | coletor | 2026-11-10 02:52 | 1001 s | — | ok | — |
| `coletar_saude.py` | coletor | 2026-11-09 01:13 | 78 s | — | ok | — |
| `coletar_saude_estadual.py` | coletor | 2026-11-03 02:26 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `coletar_semiarido_sudene.py` | coletor | 2026-11-07 01:15 | 3 s | — | ok | — |
| `coletar_sg_esus.py` | coletor | 2026-11-10 03:16 | 9 s | — | ok | — |
| `coletar_sih.py` | coletor | 2026-11-10 07:40 | 6 s | — | sem novidade | — |
| `coletar_sim.py` | coletor | 2026-11-10 07:40 | 8 s | — | sem novidade | — |
| `coletar_sinais_risco.py` | coletor | 2026-11-10 20:03 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `coletar_sisab.py` | coletor | 2026-11-10 07:37 | 132 s | — | ok | — |
| `coletar_srag_gripe.py` | coletor | 2026-11-07 01:17 | 144 s | — | ok | — |
| `coletar_srag_sivep.py` | coletor | 2026-11-10 03:15 | 32 s | — | ok | — |
| `coletar_transferencias_municipais.py` | coletor | 2026-11-10 08:42 | 80 s | — | ok | — |
| `consultar_querido_diario.py` | coletor | 2026-11-09 01:18 | 251 s | — | **erro** (3 seguidas) | portas tentadas: api.queridodiario.org.br: TimeoutError The read operation timed out \| queridodiario.ok.org.br: Timeout |
| `descobrir_dominios.py` | coletor | 2026-11-08 03:25 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `descobrir_planos.py` | coletor | 2026-11-10 07:00 | 440 s | — | ok | — |
| `desfechos_sus.py` | coletor | 2026-11-10 07:39 | 0 s | — | ok | — |
| `detectar_marcos_federais.py` | coletor | 2026-11-10 07:00 | 3 s | 0 | ok | — |
| `julgar_e_aplicar_descobertas.py` | coletor | 2026-11-10 08:26 | 487 s | — | ok | — |
| `julgar_filas.py` | coletor | 2026-11-10 15:59 | 1240 s | — | ok | — |
| `julgar_saude.py` | coletor | 2026-11-03 01:15 | 4291 s | — | **erro** | interrompido pelo prazo do elo |
| `ler_planos_arboviroses.py` | coletor | 2026-11-10 07:51 | 3 s | — | ok | — |
| `monitorar_atos_resposta.py` | coletor | 2026-11-10 06:57 | 214 s | 18667 | ok | — |
| `monitorar_busca_web.py` | coletor | 2026-11-10 08:42 | 1 s | — | ok | — |
| `monitorar_imprensa_regional.py` | coletor | 2026-11-10 06:50 | 294 s | 40 | ok | — |
| `monitorar_imprensa_saude.py` | coletor | 2026-11-10 06:55 | 103 s | 27 | ok | — |
| `monitorar_politica_por_inteiro.py` | coletor | 2026-11-10 07:00 | 4 s | 18667 | ok | — |
| `monitorar_sinais_federais.py` | coletor | 2026-11-10 07:00 | 4 s | 10 | ok | — |
| `preservar_evidencias.py` | coletor | 2026-11-10 08:43 | 2 s | — | ok | — |
| `processar_contribuicoes.py` | coletor | 2026-11-07 01:15 | 1 s | — | ok | — |
| `python3` | coletor | 2026-11-08 13:24 | 152 s | — | ok | — |
| `reconferir_instrumentos_federais.py` | coletor | 2026-11-10 07:51 | 0 s | — | ok | — |
| `revisar_pistas.py` | coletor | 2026-11-10 08:19 | 381 s | — | ok | — |
| `scripts/amostra_auditoria_semanal.py` | coletor | 2026-11-10 08:34 | 1 s | — | ok | — |
| `scripts/corrigir_atribuicao_por_dominio.py` | coletor | 2026-11-10 08:17 | 69 s | — | ok | — |
| `scripts/diagnostico_fontes_saude.py` | coletor | 2026-11-07 19:03 | 372 s | — | ok | — |
| `scripts/fechar_saude.py` | coletor | 2026-11-03 02:26 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/pistas_capitais_09_11.py` | coletor | 2026-11-09 19:06 | 2 s | — | ok | — |
| `scripts/preservar_textos_integrais.py` | coletor | 2026-11-10 08:43 | 3 s | — | ok | — |
| `scripts/proveniencia_estadual.py` | coletor | 2026-11-09 04:21 | 1 s | — | ok | — |
| `scripts/reavaliar_fontes_suspensas.py` | coletor | 2026-11-10 05:14 | 1121 s | — | ok | — |
| `scripts/sondar_boletim_infogripe.py` | coletor | 2026-11-07 01:15 | 97 s | — | ok | — |
| `scripts/sondar_credenciais.py` | coletor | 2026-11-10 08:43 | 2 s | — | ok | — |
| `scripts/triar_fila.py` | coletor | 2026-11-10 08:59 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/verificar_esquema_de_pista.py` | coletor | 2026-11-10 08:59 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/verificar_funil.py` | coletor | 2026-11-07 01:21 | 0 s | — | **erro** | ✗ FUNIL: a contagem da rodada se contradiz ou a etapa não funcionou: |
| `seguir_pistas.py` | coletor | 2026-11-10 10:31 | 69 s | — | ok | — |
| `triar_confianca_pistas.py` | coletor | 2026-11-10 07:14 | 3 s | — | ok | — |
| `verificar_links.py` | coletor | 2026-11-07 01:44 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `verificar_pista_imprensa.py` | coletor | 2026-11-10 07:14 | 20 s | — | ok | — |
