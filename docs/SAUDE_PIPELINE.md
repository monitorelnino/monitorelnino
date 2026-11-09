# Saúde do pipeline

Gerado por `scripts/gerar_saude_pipeline.py` a partir de `data/saude_pipeline.json`, que os
jobs escrevem com `scripts/saude_pipeline.py --rodar`. Item 2 do handover de desacoplamento
(27/09/2026). **Arquivo derivado: não se edita à mão.**

Duas classes, e a diferença importa. **Essencial** (`recalcular_mare.py`, `gerar_*.py`): se
erra, o site publica um estado que não corresponde ao dado — reprova o portão. **Coletor**:
fonte fora do ar é rotina, e uma falha isolada não é defeito do pipeline; erro em duas
rodadas seguidas vira alerta, porque aí não é a fonte, é o coletor.

Janela: 2026-11-02 a 2026-11-09 (1361 execução(ões) registrada(s), 7 dias de histórico).

## Alertas

- coletar_sih.py: erro em 8 rodadas seguidas — SIH: nenhum arquivo lido (0 na fila, 0 falha(s)); os arquivos anteriores ficam
- coletar_sim.py: erro em 5 rodadas seguidas — SIM: nenhum arquivo lido (0 na fila, 0 falha(s)); os arquivos anteriores ficam
- consultar_querido_diario.py: erro em 2 rodadas seguidas — portas tentadas: api.queridodiario.org.br: HTTPError HTTP Error 520: <none> | queridodiario.ok.org.br: HTTPError HTTP Error 520: <none> | api.queridodiario.ok.org.br: URLError <urlopen error [SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] ssl/tls alert handshake fail

## Cobertura em 15 dias

cobertura 15d: 5031/5571 com verificação real até 2026-11-09 · por canal: web 176 · QD 527 · consorciado 1675 · DOE 4937

## Última execução de cada script

| script | papel | última execução | duração | itens | status | erro |
|---|---|---|---|---:|---|---|
| `gerar_monitor_saude.py` | essencial | 2026-11-07 01:45 | 0 s | — | ok | — |
| `gerar_mortalidade_comparada.py` | essencial | 2026-11-09 07:17 | 0 s | — | ok | — |
| `gerar_saude_municipio.py` | essencial | 2026-11-08 01:39 | 1 s | — | ok | — |
| `recalcular_mare.py` | essencial | 2026-11-09 17:37 | 4 s | — | ok | — |
| `aplicar_promocoes_do_juiz.py` | coletor | 2026-11-09 10:23 | 1 s | — | ok | — |
| `atualizar.py` | coletor | 2026-11-07 01:43 | 104 s | — | ok | — |
| `atualizar_populacao.py` | coletor | 2026-11-07 01:15 | 1 s | — | ok | — |
| `buscar_planos_fontes_abertas.py` | coletor | 2026-11-02 21:10 | 80 s | — | ok | — |
| `buscar_protocolo_calor.py` | coletor | 2026-11-07 01:28 | 91 s | 4 | ok | — |
| `classificar_planos_municipais.py` | coletor | 2026-11-07 01:19 | 1 s | — | ok | — |
| `classificar_saude_no_plano.py` | coletor | 2026-11-08 01:39 | 1 s | — | ok | — |
| `coletar_arboviroses_sinan.py` | coletor | 2026-11-08 01:38 | 38 s | — | ok | — |
| `coletar_boletim_df_arboviroses.py` | coletor | 2026-11-08 01:32 | 356 s | — | ok | — |
| `coletar_boletim_ms_dengue.py` | coletor | 2026-11-08 01:32 | 24 s | — | ok | — |
| `coletar_boletim_pb_arboviroses.py` | coletor | 2026-11-08 01:38 | 4 s | — | ok | — |
| `coletar_boletim_pe_arboviroses.py` | coletor | 2026-11-08 01:38 | 7 s | — | ok | — |
| `coletar_cadastro_prioritarios.py` | coletor | 2026-11-07 01:14 | 28 s | — | ok | — |
| `coletar_cobertura_qd.py` | coletor | 2026-11-08 01:19 | 7542 s | — | **erro** | interrompido pelo prazo do elo |
| `coletar_datasus_dbc.py` | coletor | 2026-11-09 07:15 | 42 s | — | ok | — |
| `coletar_dda.py` | coletor | 2026-11-08 01:31 | 56 s | — | ok | — |
| `coletar_desfechos_saude.py` | coletor | 2026-11-08 01:23 | 454 s | — | ok | — |
| `coletar_diarios_consorciados.py` | coletor | 2026-11-08 01:18 | 1578 s | 24 | ok | — |
| `coletar_diarios_municipais.py` | coletor | 2026-11-08 01:18 | 2 s | 0 | ok | — |
| `coletar_doe.py` | coletor | 2026-11-08 01:45 | 2441 s | — | ok | — |
| `coletar_edicoes_doe.py` | coletor | 2026-11-09 02:54 | 4801 s | — | **erro** | interrompido pelo prazo do elo |
| `coletar_espin.py` | coletor | 2026-11-09 04:14 | 417 s | — | ok | — |
| `coletar_normais_inmet.py` | coletor | 2026-11-07 01:15 | 18 s | — | ok | — |
| `coletar_obitos.py` | coletor | 2026-11-09 07:17 | 5 s | — | ok | — |
| `coletar_obitos_registro_civil.py` | coletor | 2026-11-08 01:39 | 20 s | — | ok | — |
| `coletar_planos_arboviroses.py` | coletor | 2026-11-09 07:17 | 1513 s | — | ok | — |
| `coletar_prioritarios_mma.py` | coletor | 2026-11-07 01:15 | 2 s | — | ok | — |
| `coletar_projecao_cil.py` | coletor | 2026-11-09 07:17 | 2 s | — | ok | — |
| `coletar_recursos_resposta.py` | coletor | 2026-11-08 02:40 | 34 s | — | ok | — |
| `coletar_s2id.py` | coletor | 2026-11-08 02:25 | 892 s | — | ok | — |
| `coletar_saude.py` | coletor | 2026-11-08 01:14 | 73 s | — | ok | — |
| `coletar_saude_estadual.py` | coletor | 2026-11-03 02:26 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `coletar_semiarido_sudene.py` | coletor | 2026-11-07 01:15 | 3 s | — | ok | — |
| `coletar_sg_esus.py` | coletor | 2026-11-08 02:48 | 9 s | — | ok | — |
| `coletar_sih.py` | coletor | 2026-11-09 07:17 | 6 s | — | **erro** (8 seguidas) | SIH: nenhum arquivo lido (0 na fila, 0 falha(s)); os arquivos anteriores ficam |
| `coletar_sim.py` | coletor | 2026-11-09 07:17 | 8 s | — | **erro** (5 seguidas) | SIM: nenhum arquivo lido (0 na fila, 0 falha(s)); os arquivos anteriores ficam |
| `coletar_sinais_risco.py` | coletor | 2026-11-09 16:48 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `coletar_sisab.py` | coletor | 2026-11-09 07:15 | 112 s | — | ok | — |
| `coletar_srag_gripe.py` | coletor | 2026-11-07 01:17 | 144 s | — | ok | — |
| `coletar_srag_sivep.py` | coletor | 2026-11-08 02:48 | 37 s | — | ok | — |
| `coletar_transferencias_municipais.py` | coletor | 2026-11-09 08:57 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `consultar_querido_diario.py` | coletor | 2026-11-08 01:17 | 64 s | — | **erro** (2 seguidas) | portas tentadas: api.queridodiario.org.br: HTTPError HTTP Error 520: <none> \| queridodiario.ok.org.br: HTTPError HTTP E |
| `descobrir_dominios.py` | coletor | 2026-11-08 03:25 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `descobrir_planos.py` | coletor | 2026-11-09 08:59 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `desfechos_sus.py` | coletor | 2026-11-09 07:17 | 1 s | — | ok | — |
| `detectar_marcos_federais.py` | coletor | 2026-11-09 08:59 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `julgar_e_aplicar_descobertas.py` | coletor | 2026-11-09 08:51 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `julgar_filas.py` | coletor | 2026-11-09 10:00 | 1392 s | — | ok | — |
| `julgar_saude.py` | coletor | 2026-11-03 01:15 | 4291 s | — | **erro** | interrompido pelo prazo do elo |
| `ler_planos_arboviroses.py` | coletor | 2026-11-09 07:43 | 4 s | — | ok | — |
| `monitorar_atos_resposta.py` | coletor | 2026-11-09 08:59 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `monitorar_busca_web.py` | coletor | 2026-11-09 08:59 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `monitorar_imprensa_regional.py` | coletor | 2026-11-09 08:59 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `monitorar_imprensa_saude.py` | coletor | 2026-11-09 08:59 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `monitorar_politica_por_inteiro.py` | coletor | 2026-11-09 08:59 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `monitorar_sinais_federais.py` | coletor | 2026-11-09 08:59 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `preservar_evidencias.py` | coletor | 2026-11-09 07:46 | 2 s | — | ok | — |
| `processar_contribuicoes.py` | coletor | 2026-11-07 01:15 | 1 s | — | ok | — |
| `python3` | coletor | 2026-11-08 13:24 | 152 s | — | ok | — |
| `reconferir_instrumentos_federais.py` | coletor | 2026-11-09 07:43 | 1 s | — | ok | — |
| `revisar_pistas.py` | coletor | 2026-11-09 08:51 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/amostra_auditoria_semanal.py` | coletor | 2026-11-09 08:51 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/corrigir_atribuicao_por_dominio.py` | coletor | 2026-11-09 08:51 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/diagnostico_fontes_saude.py` | coletor | 2026-11-07 19:03 | 372 s | — | ok | — |
| `scripts/fechar_saude.py` | coletor | 2026-11-03 02:26 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/preservar_textos_integrais.py` | coletor | 2026-11-09 07:46 | 3 s | — | ok | — |
| `scripts/proveniencia_estadual.py` | coletor | 2026-11-09 04:21 | 1 s | — | ok | — |
| `scripts/reavaliar_fontes_suspensas.py` | coletor | 2026-11-09 05:14 | 1112 s | — | ok | — |
| `scripts/sondar_boletim_infogripe.py` | coletor | 2026-11-07 01:15 | 97 s | — | ok | — |
| `scripts/sondar_credenciais.py` | coletor | 2026-11-09 08:57 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/triar_fila.py` | coletor | 2026-11-09 04:27 | 1 s | — | ok | — |
| `scripts/verificar_esquema_de_pista.py` | coletor | 2026-11-09 04:46 | 2 s | — | ok | — |
| `scripts/verificar_funil.py` | coletor | 2026-11-07 01:21 | 0 s | — | **erro** | ✗ FUNIL: a contagem da rodada se contradiz ou a etapa não funcionou: |
| `seguir_pistas.py` | coletor | 2026-11-09 11:58 | 28 s | — | ok | — |
| `triar_confianca_pistas.py` | coletor | 2026-11-09 08:59 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `verificar_links.py` | coletor | 2026-11-07 01:44 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `verificar_pista_imprensa.py` | coletor | 2026-11-09 08:59 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
