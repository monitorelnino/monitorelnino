# Saúde do pipeline

Gerado por `scripts/gerar_saude_pipeline.py` a partir de `data/saude_pipeline.json`, que os
jobs escrevem com `scripts/saude_pipeline.py --rodar`. Item 2 do handover de desacoplamento
(27/09/2026). **Arquivo derivado: não se edita à mão.**

Duas classes, e a diferença importa. **Essencial** (`recalcular_mare.py`, `gerar_*.py`): se
erra, o site publica um estado que não corresponde ao dado — reprova o portão. **Coletor**:
fonte fora do ar é rotina, e uma falha isolada não é defeito do pipeline; erro em duas
rodadas seguidas vira alerta, porque aí não é a fonte, é o coletor.

Janela: 2026-11-08 a 2026-11-15 (1273 execução(ões) registrada(s), 7 dias de histórico).

## Alertas

- verificar_links.py: erro em 2 rodadas seguidas — erro: https://xanxere.sc.gov.br/uploads/sites/92/2025/05/PLANO-DE-CONTINGENCIA-XXE.pdf

## Cobertura em 15 dias

cobertura 15d: 4918/5571 com verificação real até 2026-11-15 · por canal: web 232 · QD 527 · consorciado 1685 · DOE 4798

## Última execução de cada script

| script | papel | última execução | duração | itens | status | erro |
|---|---|---|---|---:|---|---|
| `gerar_contadores_financiamento.py` | essencial | 2026-11-11 07:52 | 1 s | — | ok | — |
| `gerar_monitor_saude.py` | essencial | 2026-11-11 07:39 | 0 s | — | ok | — |
| `gerar_mortalidade_comparada.py` | essencial | 2026-11-14 07:18 | 0 s | — | ok | — |
| `gerar_saude_municipio.py` | essencial | 2026-11-14 01:39 | 1 s | — | ok | — |
| `recalcular_mare.py` | essencial | 2026-11-15 04:08 | 4 s | — | ok | — |
| `aplicar_promocoes_do_juiz.py` | coletor | 2026-11-14 02:09 | 2 s | — | ok | — |
| `atualizar.py` | coletor | 2026-11-11 07:39 | 0 s | — | ok | — |
| `atualizar_populacao.py` | coletor | 2026-11-11 07:15 | 0 s | — | ok | — |
| `buscar_protocolo_calor.py` | coletor | 2026-11-14 01:19 | 12 s | 24 | ok | — |
| `classificar_planos_municipais.py` | coletor | 2026-11-14 01:18 | 1 s | — | ok | — |
| `classificar_saude_no_plano.py` | coletor | 2026-11-14 01:39 | 1 s | — | ok | — |
| `coletar_arboviroses_sinan.py` | coletor | 2026-11-14 01:37 | 49 s | — | ok | — |
| `coletar_boletim_df_arboviroses.py` | coletor | 2026-11-14 01:31 | 319 s | — | ok | — |
| `coletar_boletim_ms_dengue.py` | coletor | 2026-11-14 01:31 | 17 s | — | ok | — |
| `coletar_boletim_pb_arboviroses.py` | coletor | 2026-11-14 01:37 | 3 s | — | ok | — |
| `coletar_boletim_pe_arboviroses.py` | coletor | 2026-11-14 01:37 | 13 s | — | ok | — |
| `coletar_cadastro_prioritarios.py` | coletor | 2026-11-14 01:13 | 29 s | — | ok | — |
| `coletar_cobertura_qd.py` | coletor | 2026-11-14 01:18 | 2027 s | — | ok | — |
| `coletar_datasus_dbc.py` | coletor | 2026-11-14 07:15 | 46 s | — | ok | — |
| `coletar_dda.py` | coletor | 2026-11-14 01:30 | 56 s | — | ok | — |
| `coletar_desfechos_saude.py` | coletor | 2026-11-14 01:23 | 446 s | — | ok | — |
| `coletar_diarios_consorciados.py` | coletor | 2026-11-14 01:50 | 3018 s | 53 | ok | — |
| `coletar_diarios_municipais.py` | coletor | 2026-11-14 01:29 | 1283 s | 250 | ok | — |
| `coletar_doe.py` | coletor | 2026-11-15 02:40 | 1350 s | — | ok | — |
| `coletar_edicoes_doe.py` | coletor | 2026-11-13 03:11 | 2624 s | — | ok | — |
| `coletar_espin.py` | coletor | 2026-11-14 01:14 | 332 s | — | ok | — |
| `coletar_execucao_mps.py` | coletor | 2026-11-11 07:52 | 34 s | — | ok | — |
| `coletar_financiamento.py` | coletor | 2026-11-11 07:52 | 2 s | 0 | ok | — |
| `coletar_fns.py` | coletor | 2026-11-09 20:35 | 25 s | — | ok | — |
| `coletar_normais_inmet.py` | coletor | 2026-11-14 01:13 | 3 s | — | ok | — |
| `coletar_obitos.py` | coletor | 2026-11-14 07:18 | 5 s | — | ok | — |
| `coletar_obitos_registro_civil.py` | coletor | 2026-11-14 01:38 | 48 s | — | ok | — |
| `coletar_pab_brasil.py` | coletor | 2026-11-14 01:14 | 7 s | — | ok | — |
| `coletar_planos_arboviroses.py` | coletor | 2026-11-14 07:18 | 1501 s | — | ok | — |
| `coletar_prioritarios_mma.py` | coletor | 2026-11-14 01:13 | 3 s | — | ok | — |
| `coletar_projecao_cil.py` | coletor | 2026-11-14 07:18 | 2 s | — | ok | — |
| `coletar_recursos_resposta.py` | coletor | 2026-11-15 03:20 | 59 s | — | ok | — |
| `coletar_s2id.py` | coletor | 2026-11-15 03:03 | 1059 s | — | ok | — |
| `coletar_saude.py` | coletor | 2026-11-14 01:14 | 79 s | — | ok | — |
| `coletar_saude_estadual.py` | coletor | 2026-11-11 03:09 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `coletar_semiarido_sudene.py` | coletor | 2026-11-14 01:13 | 2 s | — | ok | — |
| `coletar_sg_esus.py` | coletor | 2026-11-14 02:13 | 9 s | — | ok | — |
| `coletar_siconfi_182.py` | coletor | 2026-11-11 07:53 | 1 s | 5571 | ok | — |
| `coletar_sih.py` | coletor | 2026-11-14 07:18 | 6 s | — | sem novidade | — |
| `coletar_sim.py` | coletor | 2026-11-14 07:18 | 9 s | — | sem novidade | — |
| `coletar_sinais_risco.py` | coletor | 2026-11-14 01:12 | 101 s | — | ok | — |
| `coletar_sisab.py` | coletor | 2026-11-14 07:15 | 137 s | — | ok | — |
| `coletar_srag_gripe.py` | coletor | 2026-11-14 01:15 | 144 s | — | ok | — |
| `coletar_srag_sivep.py` | coletor | 2026-11-14 02:12 | 29 s | — | ok | — |
| `coletar_transferegov.py` | coletor | 2026-11-11 07:52 | 2 s | — | ok | — |
| `coletar_transferencias_municipais.py` | coletor | 2026-11-14 01:14 | 66 s | — | ok | — |
| `conferir_emergencias_estaduais.py` | coletor | 2026-11-14 18:50 | 6 s | — | ok | — |
| `consultar_querido_diario.py` | coletor | 2026-11-14 01:16 | 739 s | 41 | ok | — |
| `descobrir_dominios.py` | coletor | 2026-11-15 01:51 | 5561 s | — | **erro** | interrompido pelo prazo do elo |
| `descobrir_planos.py` | coletor | 2026-11-15 03:43 | 492 s | — | ok | — |
| `desfechos_sus.py` | coletor | 2026-11-14 07:18 | 1 s | — | ok | — |
| `detectar_marcos_federais.py` | coletor | 2026-11-15 03:43 | 1 s | — | ok | — |
| `julgar_e_aplicar_descobertas.py` | coletor | 2026-11-14 07:52 | 2 s | — | ok | — |
| `julgar_filas.py` | coletor | 2026-11-14 02:06 | 186 s | — | ok | — |
| `julgar_saude.py` | coletor | 2026-11-11 01:59 | 4184 s | — | **erro** | interrompido pelo prazo do elo |
| `ler_planos_arboviroses.py` | coletor | 2026-11-14 07:43 | 4 s | — | ok | — |
| `monitorar_atos_resposta.py` | coletor | 2026-11-15 03:41 | 102 s | 25016 | ok | — |
| `monitorar_busca_web.py` | coletor | 2026-11-15 03:51 | 252 s | — | ok | — |
| `monitorar_imprensa_regional.py` | coletor | 2026-11-15 03:29 | 615 s | 40 | ok | — |
| `monitorar_imprensa_saude.py` | coletor | 2026-11-15 03:39 | 107 s | 27 | ok | — |
| `monitorar_politica_por_inteiro.py` | coletor | 2026-11-15 03:43 | 4 s | 19033 | ok | — |
| `monitorar_sinais_federais.py` | coletor | 2026-11-15 03:43 | 4 s | 10 | ok | — |
| `preservar_evidencias.py` | coletor | 2026-11-14 08:02 | 4 s | — | ok | — |
| `processar_contribuicoes.py` | coletor | 2026-11-11 07:15 | 1 s | — | ok | — |
| `python3` | coletor | 2026-11-08 13:24 | 152 s | — | ok | — |
| `reconferir_instrumentos_federais.py` | coletor | 2026-11-14 07:43 | 1 s | — | ok | — |
| `revisar_pistas.py` | coletor | 2026-11-14 07:41 | 628 s | — | ok | — |
| `scripts/amostra_auditoria_semanal.py` | coletor | 2026-11-14 07:52 | 1 s | — | ok | — |
| `scripts/corrigir_atribuicao_por_dominio.py` | coletor | 2026-11-14 07:41 | 1 s | — | ok | — |
| `scripts/fechar_saude.py` | coletor | 2026-11-11 03:09 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/pistas_capitais_09_11.py` | coletor | 2026-11-09 19:06 | 2 s | — | ok | — |
| `scripts/preservar_textos_integrais.py` | coletor | 2026-11-14 08:02 | 2 s | — | ok | — |
| `scripts/proveniencia_estadual.py` | coletor | 2026-11-13 03:59 | 1 s | — | ok | — |
| `scripts/reavaliar_fontes_suspensas.py` | coletor | 2026-11-14 01:19 | 1137 s | — | ok | — |
| `scripts/sondar_boletim_infogripe.py` | coletor | 2026-11-14 01:14 | 99 s | — | ok | — |
| `scripts/sondar_credenciais.py` | coletor | 2026-11-14 01:15 | 2 s | — | ok | — |
| `scripts/triar_fila.py` | coletor | 2026-11-14 02:06 | 1 s | — | ok | — |
| `scripts/verificar_esquema_de_pista.py` | coletor | 2026-11-14 02:09 | 2 s | — | ok | — |
| `scripts/verificar_funil.py` | coletor | 2026-11-11 07:21 | 1 s | — | ok | — |
| `seguir_pistas.py` | coletor | 2026-11-15 03:55 | 408 s | — | ok | — |
| `sondar_repositorios_estaduais.py` | coletor | 2026-11-14 02:12 | 1552 s | — | ok | — |
| `triar_confianca_pistas.py` | coletor | 2026-11-15 04:02 | 3 s | — | ok | — |
| `verificar_links.py` | coletor | 2026-11-14 01:38 | 187 s | — | **erro** (2 seguidas) | erro: https://xanxere.sc.gov.br/uploads/sites/92/2025/05/PLANO-DE-CONTINGENCIA-XXE.pdf |
| `verificar_pista_imprensa.py` | coletor | 2026-11-15 04:02 | 3 s | — | ok | — |
