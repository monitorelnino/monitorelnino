# Saúde do pipeline

Gerado por `scripts/gerar_saude_pipeline.py` a partir de `data/saude_pipeline.json`, que os
jobs escrevem com `scripts/saude_pipeline.py --rodar`. Item 2 do handover de desacoplamento
(27/09/2026). **Arquivo derivado: não se edita à mão.**

Duas classes, e a diferença importa. **Essencial** (`recalcular_mare.py`, `gerar_*.py`): se
erra, o site publica um estado que não corresponde ao dado — reprova o portão. **Coletor**:
fonte fora do ar é rotina, e uma falha isolada não é defeito do pipeline; erro em duas
rodadas seguidas vira alerta, porque aí não é a fonte, é o coletor.

Janela: 2026-10-25 a 2026-11-01 (1155 execução(ões) registrada(s), 7 dias de histórico).

## Alertas

- coletar_sih.py: erro em 6 rodadas seguidas — SIH: nenhum arquivo lido (0 na fila, 0 falha(s)); os arquivos anteriores ficam
- verificar_links.py: erro em 2 rodadas seguidas — erro: HTTPSConnectionPool(host='www.defesacivil.sc.gov.br', port=443): Max retries exceeded with url: /2026/08/14/chuva-forte-deixa-danos-em-municipios-de-santa-catarina-e-risco-de-temporais-segue-alto-ate-sabado/ (Caused by ConnectTimeoutError(<HTTPSConnection(host='www.defesacivil.sc.gov.br', port

## Cobertura em 15 dias

cobertura 15d: 4984/5571 com verificação real até 2026-11-01 · por canal: web 1012 · QD 527 · consorciado 1713 · DOE 4677

## Última execução de cada script

| script | papel | última execução | duração | itens | status | erro |
|---|---|---|---|---:|---|---|
| `gerar_monitor_saude.py` | essencial | 2026-10-31 01:57 | 0 s | — | ok | — |
| `gerar_mortalidade_comparada.py` | essencial | 2026-10-30 01:28 | 1 s | — | ok | — |
| `gerar_saude_municipio.py` | essencial | 2026-10-31 01:43 | 1 s | — | ok | — |
| `recalcular_mare.py` | essencial | 2026-11-01 07:30 | 4 s | — | ok | — |
| `aplicar_promocoes_do_juiz.py` | coletor | 2026-11-01 07:13 | 1 s | — | ok | — |
| `atualizar.py` | coletor | 2026-10-31 01:55 | 103 s | — | ok | — |
| `atualizar_populacao.py` | coletor | 2026-10-31 01:14 | 1 s | — | ok | — |
| `buscar_planos_fontes_abertas.py` | coletor | 2026-10-28 23:21 | 718 s | — | ok | — |
| `buscar_protocolo_calor.py` | coletor | 2026-10-31 01:21 | 18 s | 4 | ok | — |
| `classificar_planos_municipais.py` | coletor | 2026-10-31 01:20 | 1 s | — | ok | — |
| `classificar_saude_no_plano.py` | coletor | 2026-10-31 01:43 | 3 s | — | ok | — |
| `coletar_arboviroses_sinan.py` | coletor | 2026-10-31 01:41 | 62 s | — | ok | — |
| `coletar_boletim_df_arboviroses.py` | coletor | 2026-10-31 01:31 | 385 s | — | ok | — |
| `coletar_boletim_ms_dengue.py` | coletor | 2026-10-31 01:31 | 21 s | — | ok | — |
| `coletar_boletim_pb_arboviroses.py` | coletor | 2026-10-31 01:38 | 197 s | — | ok | — |
| `coletar_boletim_pe_arboviroses.py` | coletor | 2026-10-31 01:38 | 7 s | — | ok | — |
| `coletar_cadastro_prioritarios.py` | coletor | 2026-10-31 01:13 | 34 s | — | ok | — |
| `coletar_cobertura_qd.py` | coletor | 2026-11-01 01:20 | 7495 s | — | **erro** | interrompido pelo prazo do elo |
| `coletar_datasus_dbc.py` | coletor | 2026-10-30 01:14 | 39 s | — | ok | — |
| `coletar_dda.py` | coletor | 2026-10-31 01:30 | 57 s | — | ok | — |
| `coletar_desfechos_saude.py` | coletor | 2026-10-31 01:22 | 471 s | — | ok | — |
| `coletar_diarios_consorciados.py` | coletor | 2026-10-31 01:22 | 3969 s | 45 | ok | — |
| `coletar_diarios_municipais.py` | coletor | 2026-10-31 01:22 | 2 s | 0 | ok | — |
| `coletar_doe.py` | coletor | 2026-11-01 02:28 | 2762 s | — | ok | — |
| `coletar_edicoes_doe.py` | coletor | 2026-10-30 17:16 | 326 s | — | ok | — |
| `coletar_espin.py` | coletor | 2026-10-31 01:13 | 480 s | — | ok | — |
| `coletar_normais_inmet.py` | coletor | 2026-10-31 01:14 | 4 s | — | ok | — |
| `coletar_obitos.py` | coletor | 2026-10-30 01:17 | 19 s | — | ok | — |
| `coletar_obitos_registro_civil.py` | coletor | 2026-10-31 01:42 | 28 s | — | ok | — |
| `coletar_planos_arboviroses.py` | coletor | 2026-10-30 01:28 | 1355 s | — | ok | — |
| `coletar_prioritarios_mma.py` | coletor | 2026-10-31 01:14 | 4 s | — | ok | — |
| `coletar_recursos_resposta.py` | coletor | 2026-11-01 03:28 | 13 s | — | ok | — |
| `coletar_s2id.py` | coletor | 2026-11-01 03:14 | 837 s | — | ok | — |
| `coletar_saude.py` | coletor | 2026-10-31 01:13 | 99 s | — | ok | — |
| `coletar_saude_estadual.py` | coletor | 2026-10-27 02:25 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `coletar_semiarido_sudene.py` | coletor | 2026-10-31 01:14 | 3 s | — | ok | — |
| `coletar_sg_esus.py` | coletor | 2026-11-01 03:36 | 10 s | — | ok | — |
| `coletar_sih.py` | coletor | 2026-10-30 01:28 | 4 s | — | **erro** (6 seguidas) | SIH: nenhum arquivo lido (0 na fila, 0 falha(s)); os arquivos anteriores ficam |
| `coletar_sim.py` | coletor | 2026-10-30 01:18 | 627 s | — | ok | — |
| `coletar_sinais_risco.py` | coletor | 2026-10-31 01:55 | 103 s | — | ok | — |
| `coletar_sisab.py` | coletor | 2026-10-30 01:15 | 154 s | — | ok | — |
| `coletar_srag_gripe.py` | coletor | 2026-10-31 01:15 | 282 s | — | ok | — |
| `coletar_srag_sivep.py` | coletor | 2026-11-01 03:35 | 36 s | — | ok | — |
| `coletar_transferencias_municipais.py` | coletor | 2026-10-31 01:14 | 36 s | — | ok | — |
| `consultar_querido_diario.py` | coletor | 2026-10-31 01:17 | 299 s | — | **erro** | portas tentadas: api.queridodiario.org.br: HTTPError HTTP Error 520: <none> \| queridodiario.ok.org.br: HTTPError HTTP E |
| `descobrir_dominios.py` | coletor | 2026-11-01 03:25 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `descobrir_planos.py` | coletor | 2026-11-01 05:15 | 488 s | — | ok | — |
| `desfechos_sus.py` | coletor | 2026-10-30 01:17 | 1 s | — | ok | — |
| `detectar_marcos_federais.py` | coletor | 2026-11-01 05:15 | 32 s | — | ok | — |
| `julgar_e_aplicar_descobertas.py` | coletor | 2026-11-01 06:59 | 861 s | — | ok | — |
| `julgar_filas.py` | coletor | 2026-11-01 05:44 | 4503 s | — | **erro** | interrompido pelo prazo do elo |
| `julgar_saude.py` | coletor | 2026-10-27 01:13 | 4321 s | — | **erro** | interrompido pelo prazo do elo |
| `ler_planos_arboviroses.py` | coletor | 2026-10-30 01:51 | 4 s | — | ok | — |
| `monitorar_atos_resposta.py` | coletor | 2026-11-01 05:05 | 546 s | 17549 | ok | — |
| `monitorar_busca_web.py` | coletor | 2026-11-01 05:23 | 256 s | — | ok | — |
| `monitorar_imprensa_regional.py` | coletor | 2026-11-01 04:59 | 249 s | 40 | ok | — |
| `monitorar_imprensa_saude.py` | coletor | 2026-11-01 05:04 | 103 s | 27 | ok | — |
| `monitorar_politica_por_inteiro.py` | coletor | 2026-11-01 05:14 | 3 s | 17549 | ok | — |
| `monitorar_redes_oficiais.py` | coletor | 2026-10-26 07:34 | 1012 s | — | ok | — |
| `monitorar_sinais_federais.py` | coletor | 2026-11-01 05:14 | 4 s | 10 | ok | — |
| `preservar_evidencias.py` | coletor | 2026-11-01 07:21 | 1 s | — | ok | — |
| `processar_contribuicoes.py` | coletor | 2026-10-31 01:14 | 2 s | — | ok | — |
| `python3` | coletor | 2026-10-31 21:20 | 4049 s | — | ok | — |
| `revisar_pistas.py` | coletor | 2026-11-01 05:38 | 367 s | — | ok | — |
| `scripts/amostra_auditoria_semanal.py` | coletor | 2026-11-01 07:13 | 1 s | — | ok | — |
| `scripts/corrigir_atribuicao_por_dominio.py` | coletor | 2026-11-01 05:37 | 57 s | — | ok | — |
| `scripts/fechar_saude.py` | coletor | 2026-10-27 02:25 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/preservar_textos_integrais.py` | coletor | 2026-11-01 07:21 | 2 s | — | ok | — |
| `scripts/reavaliar_fontes_suspensas.py` | coletor | 2026-11-01 05:14 | 721 s | — | ok | — |
| `scripts/rejulgar_decisoes_do_juiz.py` | coletor | 2026-10-30 06:06 | 3455 s | — | ok | — |
| `scripts/sondar_boletim_infogripe.py` | coletor | 2026-10-31 01:14 | 90 s | — | ok | — |
| `scripts/sondar_rotas_doe.py` | coletor | 2026-10-28 21:49 | 92 s | — | ok | — |
| `scripts/triar_fila.py` | coletor | 2026-11-01 03:42 | 2 s | — | ok | — |
| `scripts/verificar_esquema_de_pista.py` | coletor | 2026-11-01 04:00 | 2 s | — | ok | — |
| `scripts/verificar_funil.py` | coletor | 2026-10-31 01:20 | 1 s | — | **erro** | ✗ FUNIL: a contagem da rodada se contradiz ou a etapa não funcionou: |
| `seguir_pistas.py` | coletor | 2026-11-01 05:27 | 108 s | — | ok | — |
| `triar_confianca_pistas.py` | coletor | 2026-11-01 05:29 | 4 s | — | ok | — |
| `verificar_links.py` | coletor | 2026-10-31 01:33 | 194 s | — | **erro** (2 seguidas) | erro: HTTPSConnectionPool(host='www.defesacivil.sc.gov.br', port=443): Max retries exceeded with url: /2026/08/14/chuva- |
| `verificar_pista_imprensa.py` | coletor | 2026-11-01 05:29 | 27 s | — | ok | — |
