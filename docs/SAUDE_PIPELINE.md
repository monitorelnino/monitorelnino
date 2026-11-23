# Saúde do pipeline

Gerado por `scripts/gerar_saude_pipeline.py` a partir de `data/saude_pipeline.json`, que os
jobs escrevem com `scripts/saude_pipeline.py --rodar`. Item 2 do handover de desacoplamento
(27/09/2026). **Arquivo derivado: não se edita à mão.**

Duas classes, e a diferença importa. **Essencial** (`recalcular_mare.py`, `gerar_*.py`): se
erra, o site publica um estado que não corresponde ao dado — reprova o portão. **Coletor**:
fonte fora do ar é rotina, e uma falha isolada não é defeito do pipeline; erro em duas
rodadas seguidas vira alerta, porque aí não é a fonte, é o coletor.

Janela: 2026-11-16 a 2026-11-23 (1572 execução(ões) registrada(s), 7 dias de histórico).

## Alertas

- sondar_repositorios_estaduais.py: erro em 2 rodadas seguidas — interrompido pelo prazo do elo
- verificar_links.py: erro em 2 rodadas seguidas — erro: https://xanxere.sc.gov.br/uploads/sites/92/2025/05/PLANO-DE-CONTINGENCIA-XXE.pdf

## Cobertura em 15 dias

cobertura 15d: 5031/5571 com verificação real até 2026-11-23 · por canal: web 216 · QD 527 · consorciado 1681 · DOE 4937

## Última execução de cada script

| script | papel | última execução | duração | itens | status | erro |
|---|---|---|---|---:|---|---|
| `gerar_contadores_financiamento.py` | essencial | 2026-11-22 07:29 | 1 s | — | ok | — |
| `gerar_dados_abertos.py` | essencial | 2026-11-22 07:27 | 1 s | — | ok | — |
| `gerar_feeds.py` | essencial | 2026-11-22 07:27 | 2 s | — | ok | — |
| `gerar_monitor_saude.py` | essencial | 2026-11-22 07:29 | 1 s | — | ok | — |
| `gerar_mortalidade_comparada.py` | essencial | 2026-11-23 07:27 | 1 s | — | ok | — |
| `gerar_painel.py` | essencial | 2026-11-22 07:27 | 1 s | — | ok | — |
| `gerar_prioritarios.py` | essencial | 2026-11-22 07:29 | 0 s | — | ok | — |
| `gerar_resposta.py` | essencial | 2026-11-22 07:29 | 1 s | — | ok | — |
| `gerar_saude_municipio.py` | essencial | 2026-11-22 01:37 | 1 s | — | ok | — |
| `gerar_selos.py` | essencial | 2026-11-22 07:27 | 1 s | — | ok | — |
| `recalcular_mare.py` | essencial | 2026-11-23 09:20 | 6 s | — | ok | — |
| `analisar_decretos.py` | coletor | 2026-11-22 06:54 | 501 s | — | ok | — |
| `aplicar_promocoes_do_juiz.py` | coletor | 2026-11-23 08:55 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `atualizar.py` | coletor | 2026-11-22 04:10 | 11930 s | 147 | ok | — |
| `atualizar_boletins.py` | coletor | 2026-11-22 04:10 | 21 s | — | ok | — |
| `atualizar_instrumentos_estaduais.py` | coletor | 2026-11-22 06:35 | 82 s | — | **erro** | código de saída 1 |
| `atualizar_populacao.py` | coletor | 2026-11-22 03:31 | 1 s | — | ok | — |
| `atualizar_recursos.py` | coletor | 2026-11-22 06:54 | 2 s | — | **erro** | código de saída 1 |
| `atualizar_transferencias.py` | coletor | 2026-11-22 07:02 | 1476 s | — | ok | — |
| `bash scripts/verificar_derivados.sh --idempotencia` | coletor | 2026-11-22 07:28 | 74 s | — | ok | — |
| `buscar_financiamento_preventivo.py` | coletor | 2026-11-23 05:43 | 1 s | — | ok | — |
| `buscar_planos_fontes_abertas.py` | coletor | 2026-11-22 18:49 | 31 s | — | ok | — |
| `buscar_protocolo_calor.py` | coletor | 2026-11-21 01:18 | 12 s | 41 | ok | — |
| `classificar_planos_municipais.py` | coletor | 2026-11-21 01:18 | 1 s | — | ok | — |
| `classificar_saude_no_plano.py` | coletor | 2026-11-22 01:37 | 0 s | — | ok | — |
| `coletar_arboviroses_sinan.py` | coletor | 2026-11-22 01:36 | 38 s | — | ok | — |
| `coletar_boletim_df_arboviroses.py` | coletor | 2026-11-22 01:27 | 362 s | — | ok | — |
| `coletar_boletim_ms_dengue.py` | coletor | 2026-11-22 01:27 | 23 s | — | ok | — |
| `coletar_boletim_pb_arboviroses.py` | coletor | 2026-11-22 01:36 | 3 s | — | ok | — |
| `coletar_boletim_pe_arboviroses.py` | coletor | 2026-11-22 01:33 | 131 s | — | ok | — |
| `coletar_cadastro_prioritarios.py` | coletor | 2026-11-21 01:12 | 63 s | — | **erro** | urllib.error.URLError: <urlopen error [Errno 104] Connection reset by peer> |
| `coletar_cobertura_qd.py` | coletor | 2026-11-21 01:18 | 2277 s | — | ok | — |
| `coletar_datasus_dbc.py` | coletor | 2026-11-23 07:13 | 38 s | — | ok | — |
| `coletar_dda.py` | coletor | 2026-11-22 01:26 | 55 s | — | ok | — |
| `coletar_declarado_nacional.py` | coletor | 2026-11-22 04:32 | 73 s | — | ok | — |
| `coletar_desfechos_saude.py` | coletor | 2026-11-22 01:19 | 401 s | — | ok | — |
| `coletar_diarios_consorciados.py` | coletor | 2026-11-22 02:21 | 1939 s | 46 | ok | — |
| `coletar_diarios_municipais.py` | coletor | 2026-11-22 01:23 | 3430 s | 250 | ok | — |
| `coletar_doe.py` | coletor | 2026-11-23 02:53 | 1742 s | — | ok | — |
| `coletar_edicoes_doe.py` | coletor | 2026-11-23 08:56 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `coletar_espin.py` | coletor | 2026-11-23 03:14 | 272 s | — | ok | — |
| `coletar_execucao_mps.py` | coletor | 2026-11-22 06:35 | 26 s | — | ok | — |
| `coletar_financiamento.py` | coletor | 2026-11-22 06:35 | 2 s | — | ok | — |
| `coletar_mapbiomas.py` | coletor | 2026-11-17 18:04 | 2 s | — | ok | — |
| `coletar_normais_inmet.py` | coletor | 2026-11-21 01:13 | 4 s | — | ok | — |
| `coletar_obitos.py` | coletor | 2026-11-23 07:16 | 4 s | — | ok | — |
| `coletar_obitos_registro_civil.py` | coletor | 2026-11-22 01:36 | 39 s | — | ok | — |
| `coletar_pab_brasil.py` | coletor | 2026-11-21 01:13 | 37 s | — | **erro** | urllib.error.URLError: <urlopen error [Errno 104] Connection reset by peer> |
| `coletar_planos_arboviroses.py` | coletor | 2026-11-23 08:07 | 480 s | — | ok | — |
| `coletar_prioritarios_mma.py` | coletor | 2026-11-21 01:13 | 3 s | — | ok | — |
| `coletar_projecao_cil.py` | coletor | 2026-11-23 07:27 | 1 s | — | ok | — |
| `coletar_recursos_resposta.py` | coletor | 2026-11-23 03:47 | 51 s | — | ok | — |
| `coletar_s2id.py` | coletor | 2026-11-23 03:22 | 1523 s | — | ok | — |
| `coletar_saude.py` | coletor | 2026-11-22 01:12 | 66 s | — | ok | — |
| `coletar_saude_estadual.py` | coletor | 2026-11-18 03:00 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `coletar_semiarido_sudene.py` | coletor | 2026-11-21 01:13 | 3 s | — | ok | — |
| `coletar_sg_esus.py` | coletor | 2026-11-22 01:59 | 10 s | — | ok | — |
| `coletar_siconfi_182.py` | coletor | 2026-11-22 06:35 | 0 s | — | ok | — |
| `coletar_sih.py` | coletor | 2026-11-23 07:27 | 2410 s | — | ok | — |
| `coletar_sim.py` | coletor | 2026-11-23 07:16 | 617 s | — | ok | — |
| `coletar_sinais_risco.py` | coletor | 2026-11-23 08:56 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `coletar_sisab.py` | coletor | 2026-11-23 07:14 | 145 s | — | ok | — |
| `coletar_srag_gripe.py` | coletor | 2026-11-22 06:23 | 144 s | — | ok | — |
| `coletar_srag_sivep.py` | coletor | 2026-11-22 01:59 | 35 s | — | ok | — |
| `coletar_transferegov.py` | coletor | 2026-11-22 06:35 | 2 s | — | ok | — |
| `coletar_transferencias_municipais.py` | coletor | 2026-11-23 08:56 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `conferir_emergencias_estaduais.py` | coletor | 2026-11-23 08:56 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `consultar_querido_diario.py` | coletor | 2026-11-22 01:13 | 598 s | 54 | ok | — |
| `descobrir_dominios.py` | coletor | 2026-11-22 01:56 | 5326 s | — | **erro** | interrompido pelo prazo do elo |
| `descobrir_planos.py` | coletor | 2026-11-23 05:30 | 511 s | — | ok | — |
| `desfechos_sus.py` | coletor | 2026-11-23 07:16 | 1 s | — | ok | — |
| `detectar_marcos_federais.py` | coletor | 2026-11-23 05:30 | 1 s | — | ok | — |
| `julgar_e_aplicar_descobertas.py` | coletor | 2026-11-23 08:55 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `julgar_filas.py` | coletor | 2026-11-23 08:55 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `julgar_saude.py` | coletor | 2026-11-18 20:58 | 3850 s | — | ok | — |
| `julgar_saude_municipal.py` | coletor | 2026-11-16 05:40 | 8409 s | — | ok | — |
| `ler_planos_arboviroses.py` | coletor | 2026-11-23 08:15 | 3 s | — | ok | — |
| `monitorar_atos_resposta.py` | coletor | 2026-11-23 05:27 | 152 s | 25412 | ok | — |
| `monitorar_busca_web.py` | coletor | 2026-11-23 05:39 | 245 s | — | ok | — |
| `monitorar_imprensa_regional.py` | coletor | 2026-11-23 05:06 | 1160 s | 40 | ok | — |
| `monitorar_imprensa_saude.py` | coletor | 2026-11-23 05:26 | 101 s | 27 | ok | — |
| `monitorar_politica_por_inteiro.py` | coletor | 2026-11-23 05:30 | 4 s | 19318 | ok | — |
| `monitorar_sinais_federais.py` | coletor | 2026-11-23 05:30 | 4 s | 10 | ok | — |
| `node scripts/verificar_acessibilidade.js` | coletor | 2026-11-22 07:28 | 2 s | — | ok | — |
| `node scripts/verificar_estrutura.js` | coletor | 2026-11-22 07:27 | 4 s | — | ok | — |
| `node scripts/verificar_runtime.js` | coletor | 2026-11-22 07:27 | 6 s | — | ok | — |
| `node scripts/verificar_runtime_financiamento.js` | coletor | 2026-11-22 07:27 | 6 s | — | ok | — |
| `node scripts/verificar_runtime_mapas.js` | coletor | 2026-11-22 07:27 | 4 s | — | ok | — |
| `node scripts/verificar_runtime_saude.js` | coletor | 2026-11-22 07:27 | 4 s | — | ok | — |
| `node scripts/verificar_runtime_sinais.js` | coletor | 2026-11-22 07:27 | 3 s | — | ok | — |
| `node scripts/verificar_texto_publico.js` | coletor | 2026-11-22 07:28 | 26 s | — | ok | — |
| `preencher_fallback_estatico.py` | coletor | 2026-11-22 07:29 | 1 s | — | ok | — |
| `preservar_evidencias.py` | coletor | 2026-11-23 07:30 | 115 s | — | ok | — |
| `processar_contribuicoes.py` | coletor | 2026-11-23 08:55 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `reconferir_instrumentos_federais.py` | coletor | 2026-11-23 08:15 | 32 s | — | ok | — |
| `revisar_pistas.py` | coletor | 2026-11-23 08:55 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/amostra_auditoria_semanal.py` | coletor | 2026-11-23 08:55 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/busca_dirigida_do_ato.py` | coletor | 2026-11-23 05:43 | 58 s | — | ok | — |
| `scripts/corrigir_atribuicao_por_dominio.py` | coletor | 2026-11-23 08:55 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/fechar_saude.py` | coletor | 2026-11-18 03:00 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/preservar_textos_integrais.py` | coletor | 2026-11-23 07:32 | 2 s | — | ok | — |
| `scripts/proveniencia_estadual.py` | coletor | 2026-11-23 03:18 | 1 s | — | ok | — |
| `scripts/reavaliar_fontes_suspensas.py` | coletor | 2026-11-23 05:08 | 786 s | — | ok | — |
| `scripts/remediar_segredos_evidencias.py` | coletor | 2026-11-18 12:52 | 165 s | — | ok | — |
| `scripts/sondar_boletim_infogripe.py` | coletor | 2026-11-21 01:14 | 104 s | — | ok | — |
| `scripts/sondar_credenciais.py` | coletor | 2026-11-23 08:56 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/triar_fila.py` | coletor | 2026-11-22 01:56 | 2 s | — | ok | — |
| `scripts/verificar_esquema_de_pista.py` | coletor | 2026-11-22 02:24 | 3 s | — | ok | — |
| `scripts/verificar_funil.py` | coletor | 2026-11-22 03:37 | 0 s | — | ok | — |
| `scripts/verificar_leituras_paradas.py` | coletor | 2026-11-22 02:25 | 2 s | — | ok | — |
| `seguir_pistas.py` | coletor | 2026-11-23 05:44 | 18 s | — | ok | — |
| `sondar_repositorios_estaduais.py` | coletor | 2026-11-22 01:59 | 3098 s | — | **erro** (2 seguidas) | interrompido pelo prazo do elo |
| `triar_confianca_pistas.py` | coletor | 2026-11-23 05:44 | 2 s | — | ok | — |
| `verificar_consistencia.py` | coletor | 2026-11-22 07:27 | 8 s | — | ok | — |
| `verificar_contribuicoes.py` | coletor | 2026-11-22 06:35 | 1 s | — | ok | — |
| `verificar_evidencias.py` | coletor | 2026-11-22 07:27 | 6 s | — | ok | — |
| `verificar_financiamento.py` | coletor | 2026-11-22 07:27 | 1 s | — | ok | — |
| `verificar_links.py` | coletor | 2026-11-21 01:31 | 450 s | — | **erro** (2 seguidas) | erro: https://xanxere.sc.gov.br/uploads/sites/92/2025/05/PLANO-DE-CONTINGENCIA-XXE.pdf |
| `verificar_painel.py` | coletor | 2026-11-22 07:27 | 0 s | — | ok | — |
| `verificar_pista_imprensa.py` | coletor | 2026-11-23 05:44 | 132 s | — | ok | — |
| `verificar_saude.py` | coletor | 2026-11-22 07:27 | 0 s | — | ok | — |
| `verificar_sinais.py` | coletor | 2026-11-22 07:27 | 0 s | — | ok | — |
| `verificar_vigencia.py` | coletor | 2026-11-22 06:54 | 1 s | — | ok | — |
