# Saúde do pipeline

Gerado por `scripts/gerar_saude_pipeline.py` a partir de `data/saude_pipeline.json`, que os
jobs escrevem com `scripts/saude_pipeline.py --rodar`. Item 2 do handover de desacoplamento
(27/09/2026). **Arquivo derivado: não se edita à mão.**

Duas classes, e a diferença importa. **Essencial** (`recalcular_mare.py`, `gerar_*.py`): se
erra, o site publica um estado que não corresponde ao dado — reprova o portão. **Coletor**:
fonte fora do ar é rotina, e uma falha isolada não é defeito do pipeline; erro em duas
rodadas seguidas vira alerta, porque aí não é a fonte, é o coletor.

Janela: 2026-11-04 a 2026-11-11 (1306 execução(ões) registrada(s), 7 dias de histórico).

## Alertas

- consultar_querido_diario.py: erro em 4 rodadas seguidas — portas tentadas: api.queridodiario.org.br: HTTPError HTTP Error 520: <none> | queridodiario.ok.org.br: HTTPError HTTP Error 520: <none> | api.queridodiario.ok.org.br: URLError <urlopen error [SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] ssl/tls alert handshake fail

## Cobertura em 15 dias

cobertura 15d: 5031/5571 com verificação real até 2026-11-11 · por canal: web 200 · QD 527 · consorciado 1698 · DOE 4937

## Última execução de cada script

| script | papel | última execução | duração | itens | status | erro |
|---|---|---|---|---:|---|---|
| `gerar_monitor_saude.py` | essencial | 2026-11-07 01:45 | 0 s | — | ok | — |
| `gerar_mortalidade_comparada.py` | essencial | 2026-11-10 07:40 | 1 s | — | ok | — |
| `gerar_saude_municipio.py` | essencial | 2026-11-10 01:35 | 0 s | — | ok | — |
| `recalcular_mare.py` | essencial | 2026-11-11 06:08 | 4 s | — | ok | — |
| `aplicar_promocoes_do_juiz.py` | coletor | 2026-11-11 05:44 | 2 s | — | ok | — |
| `atualizar.py` | coletor | 2026-11-07 01:43 | 104 s | — | ok | — |
| `atualizar_populacao.py` | coletor | 2026-11-07 01:15 | 1 s | — | ok | — |
| `buscar_protocolo_calor.py` | coletor | 2026-11-10 01:21 | 19 s | 13 | ok | — |
| `classificar_planos_municipais.py` | coletor | 2026-11-07 01:19 | 1 s | — | ok | — |
| `classificar_saude_no_plano.py` | coletor | 2026-11-10 01:35 | 1 s | — | ok | — |
| `coletar_arboviroses_sinan.py` | coletor | 2026-11-10 01:33 | 55 s | — | ok | — |
| `coletar_boletim_df_arboviroses.py` | coletor | 2026-11-10 01:26 | 454 s | — | ok | — |
| `coletar_boletim_ms_dengue.py` | coletor | 2026-11-10 01:25 | 17 s | — | ok | — |
| `coletar_boletim_pb_arboviroses.py` | coletor | 2026-11-10 01:33 | 3 s | — | ok | — |
| `coletar_boletim_pe_arboviroses.py` | coletor | 2026-11-10 01:33 | 6 s | — | ok | — |
| `coletar_cadastro_prioritarios.py` | coletor | 2026-11-07 01:14 | 28 s | — | ok | — |
| `coletar_cobertura_qd.py` | coletor | 2026-11-08 01:19 | 7542 s | — | **erro** | interrompido pelo prazo do elo |
| `coletar_datasus_dbc.py` | coletor | 2026-11-10 07:37 | 42 s | — | ok | — |
| `coletar_dda.py` | coletor | 2026-11-10 01:25 | 54 s | — | ok | — |
| `coletar_desfechos_saude.py` | coletor | 2026-11-10 01:19 | 350 s | — | ok | — |
| `coletar_diarios_consorciados.py` | coletor | 2026-11-10 01:18 | 2777 s | 34 | ok | — |
| `coletar_diarios_municipais.py` | coletor | 2026-11-10 01:18 | 2 s | 0 | ok | — |
| `coletar_doe.py` | coletor | 2026-11-11 02:04 | 3535 s | — | ok | — |
| `coletar_edicoes_doe.py` | coletor | 2026-11-11 01:57 | 4801 s | — | **erro** | interrompido pelo prazo do elo |
| `coletar_espin.py` | coletor | 2026-11-11 03:17 | 720 s | — | ok | — |
| `coletar_fns.py` | coletor | 2026-11-09 20:35 | 25 s | — | ok | — |
| `coletar_normais_inmet.py` | coletor | 2026-11-07 01:15 | 18 s | — | ok | — |
| `coletar_obitos.py` | coletor | 2026-11-10 07:39 | 9 s | — | ok | — |
| `coletar_obitos_registro_civil.py` | coletor | 2026-11-10 01:34 | 19 s | — | ok | — |
| `coletar_planos_arboviroses.py` | coletor | 2026-11-10 07:40 | 672 s | — | ok | — |
| `coletar_prioritarios_mma.py` | coletor | 2026-11-07 01:15 | 2 s | — | ok | — |
| `coletar_projecao_cil.py` | coletor | 2026-11-10 07:40 | 2 s | — | ok | — |
| `coletar_recursos_resposta.py` | coletor | 2026-11-11 03:22 | 80 s | — | ok | — |
| `coletar_s2id.py` | coletor | 2026-11-11 03:03 | 1167 s | — | ok | — |
| `coletar_saude.py` | coletor | 2026-11-10 01:11 | 97 s | — | ok | — |
| `coletar_saude_estadual.py` | coletor | 2026-11-11 03:09 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `coletar_semiarido_sudene.py` | coletor | 2026-11-07 01:15 | 3 s | — | ok | — |
| `coletar_sg_esus.py` | coletor | 2026-11-10 01:59 | 9 s | — | ok | — |
| `coletar_sih.py` | coletor | 2026-11-10 07:40 | 6 s | — | sem novidade | — |
| `coletar_sim.py` | coletor | 2026-11-10 07:40 | 8 s | — | sem novidade | — |
| `coletar_sinais_risco.py` | coletor | 2026-11-10 01:13 | 130 s | — | ok | — |
| `coletar_sisab.py` | coletor | 2026-11-10 07:37 | 132 s | — | ok | — |
| `coletar_srag_gripe.py` | coletor | 2026-11-07 01:17 | 144 s | — | ok | — |
| `coletar_srag_sivep.py` | coletor | 2026-11-10 01:59 | 35 s | — | ok | — |
| `coletar_transferencias_municipais.py` | coletor | 2026-11-10 01:15 | 80 s | — | ok | — |
| `consultar_querido_diario.py` | coletor | 2026-11-10 01:16 | 64 s | — | **erro** (4 seguidas) | portas tentadas: api.queridodiario.org.br: HTTPError HTTP Error 520: <none> \| queridodiario.ok.org.br: HTTPError HTTP E |
| `descobrir_dominios.py` | coletor | 2026-11-08 03:25 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `descobrir_planos.py` | coletor | 2026-11-11 04:35 | 541 s | 42 | ok | — |
| `desfechos_sus.py` | coletor | 2026-11-10 07:39 | 0 s | — | ok | — |
| `detectar_marcos_federais.py` | coletor | 2026-11-11 04:35 | 2 s | 0 | ok | — |
| `julgar_e_aplicar_descobertas.py` | coletor | 2026-11-11 05:38 | 342 s | — | ok | — |
| `julgar_filas.py` | coletor | 2026-11-11 05:02 | 2157 s | — | ok | — |
| `julgar_saude.py` | coletor | 2026-11-11 01:59 | 4184 s | — | **erro** | interrompido pelo prazo do elo |
| `ler_planos_arboviroses.py` | coletor | 2026-11-10 07:51 | 3 s | — | ok | — |
| `monitorar_atos_resposta.py` | coletor | 2026-11-11 04:34 | 49 s | 25399 | ok | — |
| `monitorar_busca_web.py` | coletor | 2026-11-11 04:44 | 239 s | — | ok | — |
| `monitorar_imprensa_regional.py` | coletor | 2026-11-11 04:27 | 356 s | 40 | ok | — |
| `monitorar_imprensa_saude.py` | coletor | 2026-11-11 04:33 | 105 s | 27 | ok | — |
| `monitorar_politica_por_inteiro.py` | coletor | 2026-11-11 04:35 | 4 s | 18676 | ok | — |
| `monitorar_sinais_federais.py` | coletor | 2026-11-11 04:35 | 4 s | 10 | ok | — |
| `preservar_evidencias.py` | coletor | 2026-11-11 05:54 | 47 s | — | ok | — |
| `processar_contribuicoes.py` | coletor | 2026-11-07 01:15 | 1 s | — | ok | — |
| `python3` | coletor | 2026-11-08 13:24 | 152 s | — | ok | — |
| `reconferir_instrumentos_federais.py` | coletor | 2026-11-10 07:51 | 0 s | — | ok | — |
| `revisar_pistas.py` | coletor | 2026-11-11 04:57 | 311 s | — | ok | — |
| `scripts/amostra_auditoria_semanal.py` | coletor | 2026-11-11 05:44 | 1 s | — | ok | — |
| `scripts/corrigir_atribuicao_por_dominio.py` | coletor | 2026-11-11 04:57 | 2 s | — | ok | — |
| `scripts/diagnostico_fontes_saude.py` | coletor | 2026-11-07 19:03 | 372 s | — | ok | — |
| `scripts/fechar_saude.py` | coletor | 2026-11-11 03:09 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/pistas_capitais_09_11.py` | coletor | 2026-11-09 19:06 | 2 s | — | ok | — |
| `scripts/preservar_textos_integrais.py` | coletor | 2026-11-11 05:55 | 3 s | — | ok | — |
| `scripts/proveniencia_estadual.py` | coletor | 2026-11-11 03:29 | 1 s | — | ok | — |
| `scripts/reavaliar_fontes_suspensas.py` | coletor | 2026-11-11 05:13 | 1051 s | — | ok | — |
| `scripts/sondar_boletim_infogripe.py` | coletor | 2026-11-07 01:15 | 97 s | — | ok | — |
| `scripts/sondar_credenciais.py` | coletor | 2026-11-10 01:17 | 2 s | — | ok | — |
| `scripts/triar_fila.py` | coletor | 2026-11-10 01:58 | 2 s | — | ok | — |
| `scripts/verificar_esquema_de_pista.py` | coletor | 2026-11-10 02:02 | 2 s | — | ok | — |
| `scripts/verificar_funil.py` | coletor | 2026-11-07 01:21 | 0 s | — | **erro** | ✗ FUNIL: a contagem da rodada se contradiz ou a etapa não funcionou: |
| `seguir_pistas.py` | coletor | 2026-11-11 04:48 | 100 s | — | ok | — |
| `triar_confianca_pistas.py` | coletor | 2026-11-11 04:50 | 3 s | — | ok | — |
| `verificar_links.py` | coletor | 2026-11-10 01:39 | 180 s | — | **erro** | interrompido pelo prazo do elo |
| `verificar_pista_imprensa.py` | coletor | 2026-11-11 04:50 | 3 s | — | ok | — |
