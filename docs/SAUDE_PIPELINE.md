# Saúde do pipeline

Gerado por `scripts/gerar_saude_pipeline.py` a partir de `data/saude_pipeline.json`, que os
jobs escrevem com `scripts/saude_pipeline.py --rodar`. Item 2 do handover de desacoplamento
(27/09/2026). **Arquivo derivado: não se edita à mão.**

Duas classes, e a diferença importa. **Essencial** (`recalcular_mare.py`, `gerar_*.py`): se
erra, o site publica um estado que não corresponde ao dado — reprova o portão. **Coletor**:
fonte fora do ar é rotina, e uma falha isolada não é defeito do pipeline; erro em duas
rodadas seguidas vira alerta, porque aí não é a fonte, é o coletor.

Janela: 2026-11-10 a 2026-11-17 (1428 execução(ões) registrada(s), 7 dias de histórico).

## Alertas

- julgar_filas.py: erro em 2 rodadas seguidas — interrompido pelo prazo do elo
- python3: erro em 2 rodadas seguidas — SyntaxError: unterminated string literal (detected at line 1)
- verificar_links.py: erro em 2 rodadas seguidas — erro: https://xanxere.sc.gov.br/uploads/sites/92/2025/05/PLANO-DE-CONTINGENCIA-XXE.pdf

## Cobertura em 15 dias

cobertura 15d: 4918/5571 com verificação real até 2026-11-16 · por canal: web 256 · QD 527 · consorciado 1691 · DOE 4798

## Última execução de cada script

| script | papel | última execução | duração | itens | status | erro |
|---|---|---|---|---:|---|---|
| `gerar_blog.py` | essencial | 2026-11-15 06:14 | 0 s | — | ok | — |
| `gerar_contadores_financiamento.py` | essencial | 2026-11-15 06:19 | 0 s | — | ok | — |
| `gerar_dados_abertos.py` | essencial | 2026-11-15 06:14 | 0 s | — | ok | — |
| `gerar_feeds.py` | essencial | 2026-11-15 06:14 | 1 s | — | ok | — |
| `gerar_monitor_saude.py` | essencial | 2026-11-15 06:19 | 1 s | — | ok | — |
| `gerar_mortalidade_comparada.py` | essencial | 2026-11-16 07:19 | 0 s | — | ok | — |
| `gerar_painel.py` | essencial | 2026-11-15 06:14 | 1 s | — | ok | — |
| `gerar_prioritarios.py` | essencial | 2026-11-15 06:19 | 0 s | — | ok | — |
| `gerar_resposta.py` | essencial | 2026-11-15 06:19 | 1 s | — | ok | — |
| `gerar_saude_municipio.py` | essencial | 2026-11-16 01:36 | 0 s | — | ok | — |
| `gerar_selos.py` | essencial | 2026-11-15 06:14 | 1 s | — | ok | — |
| `recalcular_mare.py` | essencial | 2026-11-17 04:59 | 6 s | — | ok | — |
| `analisar_decretos.py` | coletor | 2026-11-15 05:56 | 1126 s | — | ok | — |
| `aplicar_promocoes_do_juiz.py` | coletor | 2026-11-17 04:45 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `atualizar.py` | coletor | 2026-11-15 04:04 | 8099 s | 150 | ok | — |
| `atualizar_boletins.py` | coletor | 2026-11-15 04:04 | 2 s | — | ok | — |
| `atualizar_instrumentos_estaduais.py` | coletor | 2026-11-15 05:45 | 84 s | — | **erro** | código de saída 1 |
| `atualizar_populacao.py` | coletor | 2026-11-15 03:33 | 1 s | — | ok | — |
| `atualizar_recursos.py` | coletor | 2026-11-15 05:56 | 1 s | — | **erro** | código de saída 1 |
| `atualizar_transferencias.py` | coletor | 2026-11-15 06:14 | 2 s | — | **erro** | código de saída 1 |
| `bash scripts/verificar_derivados.sh --idempotencia` | coletor | 2026-11-15 06:17 | 170 s | — | ok | — |
| `buscar_financiamento_preventivo.py` | coletor | 2026-11-17 03:47 | 314 s | — | ok | — |
| `buscar_protocolo_calor.py` | coletor | 2026-11-14 01:19 | 12 s | 24 | ok | — |
| `classificar_planos_municipais.py` | coletor | 2026-11-14 01:18 | 1 s | — | ok | — |
| `classificar_saude_no_plano.py` | coletor | 2026-11-16 01:36 | 1 s | — | ok | — |
| `coletar_arboviroses_sinan.py` | coletor | 2026-11-16 01:35 | 39 s | — | ok | — |
| `coletar_boletim_df_arboviroses.py` | coletor | 2026-11-16 01:30 | 295 s | — | ok | — |
| `coletar_boletim_ms_dengue.py` | coletor | 2026-11-16 01:29 | 16 s | — | ok | — |
| `coletar_boletim_pb_arboviroses.py` | coletor | 2026-11-16 01:35 | 3 s | — | ok | — |
| `coletar_boletim_pe_arboviroses.py` | coletor | 2026-11-16 01:35 | 6 s | — | ok | — |
| `coletar_cadastro_prioritarios.py` | coletor | 2026-11-14 01:13 | 29 s | — | ok | — |
| `coletar_cobertura_qd.py` | coletor | 2026-11-14 01:18 | 2027 s | — | ok | — |
| `coletar_datasus_dbc.py` | coletor | 2026-11-16 07:15 | 41 s | — | ok | — |
| `coletar_dda.py` | coletor | 2026-11-16 01:28 | 56 s | — | ok | — |
| `coletar_declarado_nacional.py` | coletor | 2026-11-15 04:21 | 28 s | — | ok | — |
| `coletar_desfechos_saude.py` | coletor | 2026-11-16 01:21 | 446 s | — | ok | — |
| `coletar_diarios_consorciados.py` | coletor | 2026-11-16 01:29 | 2702 s | 64 | ok | — |
| `coletar_diarios_municipais.py` | coletor | 2026-11-16 01:29 | 2 s | 0 | ok | — |
| `coletar_doe.py` | coletor | 2026-11-16 02:14 | 1562 s | — | ok | — |
| `coletar_edicoes_doe.py` | coletor | 2026-11-16 01:16 | 602 s | — | **erro** | interrompido pelo prazo do elo |
| `coletar_espin.py` | coletor | 2026-11-16 03:23 | 219 s | — | ok | — |
| `coletar_execucao_mps.py` | coletor | 2026-11-15 05:44 | 22 s | — | ok | — |
| `coletar_financiamento.py` | coletor | 2026-11-15 05:44 | 1 s | — | ok | — |
| `coletar_normais_inmet.py` | coletor | 2026-11-14 01:13 | 3 s | — | ok | — |
| `coletar_obitos.py` | coletor | 2026-11-16 07:19 | 4 s | — | ok | — |
| `coletar_obitos_registro_civil.py` | coletor | 2026-11-16 01:35 | 42 s | — | ok | — |
| `coletar_pab_brasil.py` | coletor | 2026-11-14 01:14 | 7 s | — | ok | — |
| `coletar_planos_arboviroses.py` | coletor | 2026-11-16 07:19 | 1526 s | — | ok | — |
| `coletar_prioritarios_mma.py` | coletor | 2026-11-14 01:13 | 3 s | — | ok | — |
| `coletar_projecao_cil.py` | coletor | 2026-11-16 07:19 | 2 s | — | ok | — |
| `coletar_recursos_resposta.py` | coletor | 2026-11-16 02:58 | 41 s | — | ok | — |
| `coletar_s2id.py` | coletor | 2026-11-16 02:40 | 1080 s | — | ok | — |
| `coletar_saude.py` | coletor | 2026-11-16 01:12 | 75 s | — | ok | — |
| `coletar_saude_estadual.py` | coletor | 2026-11-11 03:09 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `coletar_semiarido_sudene.py` | coletor | 2026-11-14 01:13 | 2 s | — | ok | — |
| `coletar_sg_esus.py` | coletor | 2026-11-16 02:39 | 10 s | — | ok | — |
| `coletar_siconfi_182.py` | coletor | 2026-11-15 05:42 | 1 s | — | ok | — |
| `coletar_sih.py` | coletor | 2026-11-16 07:19 | 5 s | — | sem novidade | — |
| `coletar_sim.py` | coletor | 2026-11-16 07:19 | 8 s | — | sem novidade | — |
| `coletar_sinais_risco.py` | coletor | 2026-11-16 01:12 | 141 s | — | ok | — |
| `coletar_sisab.py` | coletor | 2026-11-16 07:16 | 156 s | — | ok | — |
| `coletar_srag_gripe.py` | coletor | 2026-11-15 05:35 | 144 s | — | ok | — |
| `coletar_srag_sivep.py` | coletor | 2026-11-16 02:39 | 36 s | — | ok | — |
| `coletar_transferegov.py` | coletor | 2026-11-15 05:44 | 2 s | — | ok | — |
| `coletar_transferencias_municipais.py` | coletor | 2026-11-16 01:15 | 67 s | — | ok | — |
| `conferir_emergencias_estaduais.py` | coletor | 2026-11-16 01:26 | 1 s | — | ok | — |
| `consultar_querido_diario.py` | coletor | 2026-11-16 01:14 | 850 s | 36 | ok | — |
| `descobrir_dominios.py` | coletor | 2026-11-15 01:51 | 5561 s | — | **erro** | interrompido pelo prazo do elo |
| `descobrir_planos.py` | coletor | 2026-11-17 03:35 | 438 s | — | ok | — |
| `desfechos_sus.py` | coletor | 2026-11-16 07:19 | 1 s | — | ok | — |
| `detectar_marcos_federais.py` | coletor | 2026-11-17 03:35 | 2 s | — | ok | — |
| `julgar_e_aplicar_descobertas.py` | coletor | 2026-11-16 08:58 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `julgar_filas.py` | coletor | 2026-11-17 04:04 | 2454 s | — | **erro** (2 seguidas) | interrompido pelo prazo do elo |
| `julgar_saude.py` | coletor | 2026-11-15 23:26 | 892 s | — | ok | — |
| `julgar_saude_municipal.py` | coletor | 2026-11-16 05:40 | 8409 s | — | ok | — |
| `ler_planos_arboviroses.py` | coletor | 2026-11-16 07:44 | 4 s | — | ok | — |
| `monitorar_atos_resposta.py` | coletor | 2026-11-17 03:32 | 174 s | 25141 | ok | — |
| `monitorar_busca_web.py` | coletor | 2026-11-17 03:43 | 245 s | — | ok | — |
| `monitorar_imprensa_regional.py` | coletor | 2026-11-17 03:21 | 580 s | 40 | ok | — |
| `monitorar_imprensa_saude.py` | coletor | 2026-11-17 03:31 | 90 s | 27 | ok | — |
| `monitorar_politica_por_inteiro.py` | coletor | 2026-11-17 03:35 | 3 s | 19117 | ok | — |
| `monitorar_sinais_federais.py` | coletor | 2026-11-17 03:35 | 7 s | 10 | ok | — |
| `node scripts/verificar_acessibilidade.js` | coletor | 2026-11-15 06:16 | 2 s | — | ok | — |
| `node scripts/verificar_estrutura.js` | coletor | 2026-11-15 06:14 | 2 s | — | ok | — |
| `node scripts/verificar_runtime.js` | coletor | 2026-11-15 06:16 | 5 s | — | ok | — |
| `node scripts/verificar_runtime_financiamento.js` | coletor | 2026-11-15 06:16 | 5 s | — | ok | — |
| `node scripts/verificar_runtime_mapas.js` | coletor | 2026-11-15 06:16 | 4 s | — | ok | — |
| `node scripts/verificar_runtime_saude.js` | coletor | 2026-11-15 06:16 | 2 s | — | ok | — |
| `node scripts/verificar_runtime_sinais.js` | coletor | 2026-11-15 06:16 | 2 s | — | ok | — |
| `node scripts/verificar_texto_publico.js` | coletor | 2026-11-15 06:16 | 38 s | — | ok | — |
| `preencher_fallback_estatico.py` | coletor | 2026-11-15 06:19 | 0 s | — | ok | — |
| `preservar_evidencias.py` | coletor | 2026-11-17 04:52 | 5 s | — | ok | — |
| `processar_contribuicoes.py` | coletor | 2026-11-16 08:58 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `python3` | coletor | 2026-11-15 16:10 | 0 s | — | **erro** (2 seguidas) | SyntaxError: unterminated string literal (detected at line 1) |
| `reconferir_instrumentos_federais.py` | coletor | 2026-11-16 07:44 | 1 s | — | ok | — |
| `revisar_pistas.py` | coletor | 2026-11-16 08:58 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/amostra_auditoria_semanal.py` | coletor | 2026-11-16 08:58 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/corrigir_atribuicao_por_dominio.py` | coletor | 2026-11-16 08:58 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/fechar_saude.py` | coletor | 2026-11-11 03:09 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/pistas.py` | coletor | 2026-11-15 10:00 | 252 s | — | ok | — |
| `scripts/preservar_textos_integrais.py` | coletor | 2026-11-17 04:52 | 2 s | — | ok | — |
| `scripts/proveniencia_estadual.py` | coletor | 2026-11-16 03:26 | 0 s | — | ok | — |
| `scripts/reavaliar_fontes_suspensas.py` | coletor | 2026-11-16 05:13 | 1111 s | — | ok | — |
| `scripts/sondar_boletim_infogripe.py` | coletor | 2026-11-14 01:14 | 99 s | — | ok | — |
| `scripts/sondar_credenciais.py` | coletor | 2026-11-16 01:16 | 2 s | — | ok | — |
| `scripts/triar_fila.py` | coletor | 2026-11-17 04:04 | 2 s | — | ok | — |
| `scripts/verificar_esquema_de_pista.py` | coletor | 2026-11-17 04:45 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/verificar_funil.py` | coletor | 2026-11-15 03:39 | 0 s | — | ok | — |
| `scripts/verificar_leituras_paradas.py` | coletor | 2026-11-17 04:45 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `seguir_pistas.py` | coletor | 2026-11-17 03:52 | 372 s | — | ok | — |
| `sondar_repositorios_estaduais.py` | coletor | 2026-11-16 02:39 | 1 s | — | ok | — |
| `triar_confianca_pistas.py` | coletor | 2026-11-17 03:58 | 2 s | — | ok | — |
| `verificar_consistencia.py` | coletor | 2026-11-15 06:14 | 6 s | — | ok | — |
| `verificar_contribuicoes.py` | coletor | 2026-11-15 05:45 | 1 s | — | ok | — |
| `verificar_evidencias.py` | coletor | 2026-11-15 06:15 | 66 s | — | ok | — |
| `verificar_financiamento.py` | coletor | 2026-11-15 06:15 | 1 s | — | ok | — |
| `verificar_links.py` | coletor | 2026-11-14 01:38 | 187 s | — | **erro** (2 seguidas) | erro: https://xanxere.sc.gov.br/uploads/sites/92/2025/05/PLANO-DE-CONTINGENCIA-XXE.pdf |
| `verificar_painel.py` | coletor | 2026-11-15 06:15 | 1 s | — | ok | — |
| `verificar_pista_imprensa.py` | coletor | 2026-11-17 03:58 | 8 s | — | ok | — |
| `verificar_saude.py` | coletor | 2026-11-15 06:15 | 1 s | — | ok | — |
| `verificar_sinais.py` | coletor | 2026-11-15 06:15 | 1 s | — | ok | — |
| `verificar_vigencia.py` | coletor | 2026-11-15 05:56 | 0 s | — | ok | — |
