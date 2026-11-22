# Saúde do pipeline

Gerado por `scripts/gerar_saude_pipeline.py` a partir de `data/saude_pipeline.json`, que os
jobs escrevem com `scripts/saude_pipeline.py --rodar`. Item 2 do handover de desacoplamento
(27/09/2026). **Arquivo derivado: não se edita à mão.**

Duas classes, e a diferença importa. **Essencial** (`recalcular_mare.py`, `gerar_*.py`): se
erra, o site publica um estado que não corresponde ao dado — reprova o portão. **Coletor**:
fonte fora do ar é rotina, e uma falha isolada não é defeito do pipeline; erro em duas
rodadas seguidas vira alerta, porque aí não é a fonte, é o coletor.

Janela: 2026-11-15 a 2026-11-22 (1677 execução(ões) registrada(s), 7 dias de histórico).

## Alertas

- atualizar_instrumentos_estaduais.py: erro em 2 rodadas seguidas — código de saída 1
- atualizar_recursos.py: erro em 2 rodadas seguidas — código de saída 1
- descobrir_dominios.py: erro em 2 rodadas seguidas — interrompido pelo prazo do elo
- python3: erro em 2 rodadas seguidas — SyntaxError: unterminated string literal (detected at line 1)
- verificar_links.py: erro em 2 rodadas seguidas — erro: https://xanxere.sc.gov.br/uploads/sites/92/2025/05/PLANO-DE-CONTINGENCIA-XXE.pdf

## Cobertura em 15 dias

cobertura 15d: 4918/5571 com verificação real até 2026-11-22 · por canal: web 224 · QD 527 · consorciado 1681 · DOE 4798

## Última execução de cada script

| script | papel | última execução | duração | itens | status | erro |
|---|---|---|---|---:|---|---|
| `gerar_blog.py` | essencial | 2026-11-15 06:14 | 0 s | — | ok | — |
| `gerar_contadores_financiamento.py` | essencial | 2026-11-22 07:29 | 1 s | — | ok | — |
| `gerar_dados_abertos.py` | essencial | 2026-11-22 07:27 | 1 s | — | ok | — |
| `gerar_feeds.py` | essencial | 2026-11-22 07:27 | 2 s | — | ok | — |
| `gerar_monitor_saude.py` | essencial | 2026-11-22 07:29 | 1 s | — | ok | — |
| `gerar_mortalidade_comparada.py` | essencial | 2026-11-22 07:25 | 1 s | — | ok | — |
| `gerar_painel.py` | essencial | 2026-11-22 07:27 | 1 s | — | ok | — |
| `gerar_prioritarios.py` | essencial | 2026-11-22 07:29 | 0 s | — | ok | — |
| `gerar_resposta.py` | essencial | 2026-11-22 07:29 | 1 s | — | ok | — |
| `gerar_saude_municipio.py` | essencial | 2026-11-21 01:34 | 1 s | — | ok | — |
| `gerar_selos.py` | essencial | 2026-11-22 07:27 | 1 s | — | ok | — |
| `recalcular_mare.py` | essencial | 2026-11-22 09:09 | 4 s | — | ok | — |
| `analisar_decretos.py` | coletor | 2026-11-22 06:54 | 501 s | — | ok | — |
| `aplicar_promocoes_do_juiz.py` | coletor | 2026-11-22 08:58 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `atualizar.py` | coletor | 2026-11-22 04:10 | 11930 s | 147 | ok | — |
| `atualizar_boletins.py` | coletor | 2026-11-22 04:10 | 21 s | — | ok | — |
| `atualizar_instrumentos_estaduais.py` | coletor | 2026-11-22 06:35 | 82 s | — | **erro** (2 seguidas) | código de saída 1 |
| `atualizar_populacao.py` | coletor | 2026-11-22 03:31 | 1 s | — | ok | — |
| `atualizar_recursos.py` | coletor | 2026-11-22 06:54 | 2 s | — | **erro** (2 seguidas) | código de saída 1 |
| `atualizar_transferencias.py` | coletor | 2026-11-22 07:02 | 1476 s | — | ok | — |
| `bash scripts/verificar_derivados.sh --idempotencia` | coletor | 2026-11-22 07:28 | 74 s | — | ok | — |
| `buscar_financiamento_preventivo.py` | coletor | 2026-11-22 08:53 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `buscar_protocolo_calor.py` | coletor | 2026-11-21 01:18 | 12 s | 41 | ok | — |
| `classificar_planos_municipais.py` | coletor | 2026-11-21 01:18 | 1 s | — | ok | — |
| `classificar_saude_no_plano.py` | coletor | 2026-11-21 01:34 | 1 s | — | ok | — |
| `coletar_arboviroses_sinan.py` | coletor | 2026-11-21 01:32 | 58 s | — | ok | — |
| `coletar_boletim_df_arboviroses.py` | coletor | 2026-11-21 01:26 | 380 s | — | ok | — |
| `coletar_boletim_ms_dengue.py` | coletor | 2026-11-21 01:25 | 25 s | — | ok | — |
| `coletar_boletim_pb_arboviroses.py` | coletor | 2026-11-21 01:32 | 3 s | — | ok | — |
| `coletar_boletim_pe_arboviroses.py` | coletor | 2026-11-21 01:32 | 6 s | — | ok | — |
| `coletar_cadastro_prioritarios.py` | coletor | 2026-11-21 01:12 | 63 s | — | **erro** | urllib.error.URLError: <urlopen error [Errno 104] Connection reset by peer> |
| `coletar_cobertura_qd.py` | coletor | 2026-11-21 01:18 | 2277 s | — | ok | — |
| `coletar_datasus_dbc.py` | coletor | 2026-11-22 07:12 | 38 s | — | ok | — |
| `coletar_dda.py` | coletor | 2026-11-21 01:24 | 55 s | — | ok | — |
| `coletar_declarado_nacional.py` | coletor | 2026-11-22 04:32 | 73 s | — | ok | — |
| `coletar_desfechos_saude.py` | coletor | 2026-11-21 01:19 | 353 s | — | ok | — |
| `coletar_diarios_consorciados.py` | coletor | 2026-11-22 05:28 | 2294 s | — | ok | — |
| `coletar_diarios_municipais.py` | coletor | 2026-11-22 05:02 | 1516 s | — | ok | — |
| `coletar_doe.py` | coletor | 2026-11-22 04:33 | 1735 s | — | ok | — |
| `coletar_edicoes_doe.py` | coletor | 2026-11-22 08:51 | 6 s | — | ok | — |
| `coletar_espin.py` | coletor | 2026-11-22 06:26 | 546 s | — | ok | — |
| `coletar_execucao_mps.py` | coletor | 2026-11-22 06:35 | 26 s | — | ok | — |
| `coletar_financiamento.py` | coletor | 2026-11-22 06:35 | 2 s | — | ok | — |
| `coletar_mapbiomas.py` | coletor | 2026-11-17 18:04 | 2 s | — | ok | — |
| `coletar_normais_inmet.py` | coletor | 2026-11-21 01:13 | 4 s | — | ok | — |
| `coletar_obitos.py` | coletor | 2026-11-22 07:15 | 4 s | — | ok | — |
| `coletar_obitos_registro_civil.py` | coletor | 2026-11-21 01:33 | 35 s | — | ok | — |
| `coletar_pab_brasil.py` | coletor | 2026-11-21 01:13 | 37 s | — | **erro** | urllib.error.URLError: <urlopen error [Errno 104] Connection reset by peer> |
| `coletar_planos_arboviroses.py` | coletor | 2026-11-22 08:06 | 1503 s | — | ok | — |
| `coletar_prioritarios_mma.py` | coletor | 2026-11-21 01:13 | 3 s | — | ok | — |
| `coletar_projecao_cil.py` | coletor | 2026-11-22 07:25 | 2 s | — | ok | — |
| `coletar_recursos_resposta.py` | coletor | 2026-11-21 02:39 | 39 s | — | ok | — |
| `coletar_s2id.py` | coletor | 2026-11-22 04:11 | 1284 s | — | ok | — |
| `coletar_saude.py` | coletor | 2026-11-21 01:11 | 79 s | — | ok | — |
| `coletar_saude_estadual.py` | coletor | 2026-11-18 03:00 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `coletar_semiarido_sudene.py` | coletor | 2026-11-21 01:13 | 3 s | — | ok | — |
| `coletar_sg_esus.py` | coletor | 2026-11-21 02:10 | 10 s | — | ok | — |
| `coletar_siconfi_182.py` | coletor | 2026-11-22 06:35 | 0 s | — | ok | — |
| `coletar_sih.py` | coletor | 2026-11-22 07:25 | 2417 s | — | ok | — |
| `coletar_sim.py` | coletor | 2026-11-22 07:15 | 613 s | — | ok | — |
| `coletar_sinais_risco.py` | coletor | 2026-11-22 08:48 | 117 s | — | ok | — |
| `coletar_sisab.py` | coletor | 2026-11-22 07:13 | 142 s | — | ok | — |
| `coletar_srag_gripe.py` | coletor | 2026-11-22 06:23 | 144 s | — | ok | — |
| `coletar_srag_sivep.py` | coletor | 2026-11-21 02:09 | 38 s | — | ok | — |
| `coletar_transferegov.py` | coletor | 2026-11-22 06:35 | 2 s | — | ok | — |
| `coletar_transferencias_municipais.py` | coletor | 2026-11-22 08:50 | 49 s | — | ok | — |
| `conferir_emergencias_estaduais.py` | coletor | 2026-11-22 08:51 | 1 s | — | ok | — |
| `consultar_querido_diario.py` | coletor | 2026-11-22 06:37 | 1019 s | — | ok | — |
| `descobrir_dominios.py` | coletor | 2026-11-22 01:56 | 5326 s | — | **erro** (2 seguidas) | interrompido pelo prazo do elo |
| `descobrir_planos.py` | coletor | 2026-11-22 08:53 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `desfechos_sus.py` | coletor | 2026-11-22 07:15 | 1 s | — | ok | — |
| `detectar_marcos_federais.py` | coletor | 2026-11-22 08:53 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `julgar_e_aplicar_descobertas.py` | coletor | 2026-11-22 08:45 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `julgar_filas.py` | coletor | 2026-11-22 08:58 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `julgar_saude.py` | coletor | 2026-11-18 20:58 | 3850 s | — | ok | — |
| `julgar_saude_municipal.py` | coletor | 2026-11-16 05:40 | 8409 s | — | ok | — |
| `ler_planos_arboviroses.py` | coletor | 2026-11-22 08:31 | 3 s | — | ok | — |
| `monitorar_atos_resposta.py` | coletor | 2026-11-22 08:53 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `monitorar_busca_web.py` | coletor | 2026-11-22 08:53 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `monitorar_imprensa_regional.py` | coletor | 2026-11-22 08:53 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `monitorar_imprensa_saude.py` | coletor | 2026-11-22 08:53 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `monitorar_politica_por_inteiro.py` | coletor | 2026-11-22 08:53 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `monitorar_sinais_federais.py` | coletor | 2026-11-22 08:53 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `node scripts/verificar_acessibilidade.js` | coletor | 2026-11-22 07:28 | 2 s | — | ok | — |
| `node scripts/verificar_estrutura.js` | coletor | 2026-11-22 07:27 | 4 s | — | ok | — |
| `node scripts/verificar_runtime.js` | coletor | 2026-11-22 07:27 | 6 s | — | ok | — |
| `node scripts/verificar_runtime_financiamento.js` | coletor | 2026-11-22 07:27 | 6 s | — | ok | — |
| `node scripts/verificar_runtime_mapas.js` | coletor | 2026-11-22 07:27 | 4 s | — | ok | — |
| `node scripts/verificar_runtime_saude.js` | coletor | 2026-11-22 07:27 | 4 s | — | ok | — |
| `node scripts/verificar_runtime_sinais.js` | coletor | 2026-11-22 07:27 | 3 s | — | ok | — |
| `node scripts/verificar_texto_publico.js` | coletor | 2026-11-22 07:28 | 26 s | — | ok | — |
| `preencher_fallback_estatico.py` | coletor | 2026-11-22 07:29 | 1 s | — | ok | — |
| `preservar_evidencias.py` | coletor | 2026-11-22 08:48 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `processar_contribuicoes.py` | coletor | 2026-11-22 08:34 | 1 s | — | ok | — |
| `python3` | coletor | 2026-11-15 16:10 | 0 s | — | **erro** (2 seguidas) | SyntaxError: unterminated string literal (detected at line 1) |
| `reconferir_instrumentos_federais.py` | coletor | 2026-11-22 08:31 | 32 s | — | ok | — |
| `revisar_pistas.py` | coletor | 2026-11-22 08:34 | 607 s | — | **erro** | interrompido pelo prazo do elo |
| `scripts/amostra_auditoria_semanal.py` | coletor | 2026-11-22 08:45 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/busca_dirigida_do_ato.py` | coletor | 2026-11-22 08:53 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/corrigir_atribuicao_por_dominio.py` | coletor | 2026-11-22 08:34 | 1 s | — | ok | — |
| `scripts/fechar_saude.py` | coletor | 2026-11-18 03:00 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/pistas.py` | coletor | 2026-11-15 10:00 | 252 s | — | ok | — |
| `scripts/preservar_textos_integrais.py` | coletor | 2026-11-22 08:48 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/proveniencia_estadual.py` | coletor | 2026-11-20 03:20 | 1 s | — | ok | — |
| `scripts/reavaliar_fontes_suspensas.py` | coletor | 2026-11-22 05:11 | 856 s | — | ok | — |
| `scripts/remediar_segredos_evidencias.py` | coletor | 2026-11-18 12:52 | 165 s | — | ok | — |
| `scripts/sondar_boletim_infogripe.py` | coletor | 2026-11-21 01:14 | 104 s | — | ok | — |
| `scripts/sondar_credenciais.py` | coletor | 2026-11-22 08:50 | 1 s | — | ok | — |
| `scripts/triar_fila.py` | coletor | 2026-11-22 08:58 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/verificar_esquema_de_pista.py` | coletor | 2026-11-22 08:58 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/verificar_funil.py` | coletor | 2026-11-22 03:37 | 0 s | — | ok | — |
| `scripts/verificar_leituras_paradas.py` | coletor | 2026-11-22 08:58 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `seguir_pistas.py` | coletor | 2026-11-22 08:53 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `sondar_repositorios_estaduais.py` | coletor | 2026-11-22 02:11 | 3076 s | — | **erro** | interrompido pelo prazo do elo |
| `triar_confianca_pistas.py` | coletor | 2026-11-22 08:53 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `verificar_consistencia.py` | coletor | 2026-11-22 07:27 | 8 s | — | ok | — |
| `verificar_contribuicoes.py` | coletor | 2026-11-22 06:35 | 1 s | — | ok | — |
| `verificar_evidencias.py` | coletor | 2026-11-22 07:27 | 6 s | — | ok | — |
| `verificar_financiamento.py` | coletor | 2026-11-22 07:27 | 1 s | — | ok | — |
| `verificar_links.py` | coletor | 2026-11-21 01:31 | 450 s | — | **erro** (2 seguidas) | erro: https://xanxere.sc.gov.br/uploads/sites/92/2025/05/PLANO-DE-CONTINGENCIA-XXE.pdf |
| `verificar_painel.py` | coletor | 2026-11-22 07:27 | 0 s | — | ok | — |
| `verificar_pista_imprensa.py` | coletor | 2026-11-22 08:53 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `verificar_saude.py` | coletor | 2026-11-22 07:27 | 0 s | — | ok | — |
| `verificar_sinais.py` | coletor | 2026-11-22 07:27 | 0 s | — | ok | — |
| `verificar_vigencia.py` | coletor | 2026-11-22 06:54 | 1 s | — | ok | — |
