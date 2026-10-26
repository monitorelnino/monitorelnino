# Saúde do pipeline

Gerado por `scripts/gerar_saude_pipeline.py` a partir de `data/saude_pipeline.json`, que os
jobs escrevem com `scripts/saude_pipeline.py --rodar`. Item 2 do handover de desacoplamento
(27/09/2026). **Arquivo derivado: não se edita à mão.**

Duas classes, e a diferença importa. **Essencial** (`recalcular_mare.py`, `gerar_*.py`): se
erra, o site publica um estado que não corresponde ao dado — reprova o portão. **Coletor**:
fonte fora do ar é rotina, e uma falha isolada não é defeito do pipeline; erro em duas
rodadas seguidas vira alerta, porque aí não é a fonte, é o coletor.

Janela: 2026-10-17 a 2026-10-26 (2050 execução(ões) registrada(s), 7 dias de histórico).

## Alertas

- coletar_sih.py: erro em 2 rodadas seguidas — SIH: nenhum arquivo lido (0 na fila, 0 falha(s)); os arquivos anteriores ficam
- coletar_sim.py: erro em 3 rodadas seguidas — SIM: nenhum arquivo lido (0 na fila, 0 falha(s)); os arquivos anteriores ficam
- consultar_querido_diario.py: erro em 9 rodadas seguidas — urllib.error.URLError: <urlopen error [SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] sslv3 alert handshake failure (_ssl.c:1010)>
- descobrir_dominios.py: erro em 3 rodadas seguidas — interrompido pelo prazo do elo
- verificar_links.py: erro em 11 rodadas seguidas — erro: HTTPSConnectionPool(host='www.defesacivil.sc.gov.br', port=443): Max retries exceeded with url: /2026/08/14/chuva-forte-deixa-danos-em-municipios-de-santa-catarina-e-risco-de-temporais-segue-alto-ate-sabado/ (Caused by ConnectTimeoutError(<HTTPSConnection(host='www.defesacivil.sc.gov.br', port

## Cobertura em 15 dias

cobertura 15d: 5055/5571 com verificação real até 2026-10-25 · por canal: web 1715 · QD 527 · consorciado 1668 · DOE 4175

## Última execução de cada script

| script | papel | última execução | duração | itens | status | erro |
|---|---|---|---|---:|---|---|
| `gerar_monitor_saude.py` | essencial | 2026-10-17 02:14 | 1 s | — | ok | — |
| `gerar_saude_municipio.py` | essencial | 2026-10-17 02:25 | 1 s | — | ok | — |
| `recalcular_mare.py` | essencial | 2026-10-17 02:10 | 4 s | — | ok | — |
| `aplicar_promocoes_do_juiz.py` | coletor | 2026-10-17 02:57 | 40 s | 1 | ok | — |
| `atualizar.py` | coletor | 2026-10-17 02:13 | 99 s | — | ok | — |
| `atualizar_populacao.py` | coletor | 2026-10-17 02:24 | 0 s | — | ok | — |
| `buscar_planos_fontes_abertas.py` | coletor | 2026-10-25 17:51 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `buscar_protocolo_calor.py` | coletor | 2026-10-17 01:58 | 13 s | 3 | ok | — |
| `classificar_planos_municipais.py` | coletor | 2026-10-17 01:39 | 1 s | — | ok | — |
| `classificar_saude_no_plano.py` | coletor | 2026-10-17 02:25 | 1 s | — | ok | — |
| `coletar_arboviroses_sinan.py` | coletor | 2026-10-17 02:21 | 60 s | — | ok | — |
| `coletar_boletim_df_arboviroses.py` | coletor | 2026-10-17 02:15 | 352 s | — | ok | — |
| `coletar_boletim_ms_dengue.py` | coletor | 2026-10-17 02:15 | 17 s | — | ok | — |
| `coletar_boletim_pb_arboviroses.py` | coletor | 2026-10-17 02:21 | 2 s | — | ok | — |
| `coletar_boletim_pe_arboviroses.py` | coletor | 2026-10-17 02:21 | 7 s | — | ok | — |
| `coletar_cadastro_prioritarios.py` | coletor | 2026-10-17 01:35 | 29 s | — | ok | — |
| `coletar_cobertura_qd.py` | coletor | 2026-10-17 01:39 | 4619 s | — | ok | — |
| `coletar_datasus_dbc.py` | coletor | 2026-10-25 01:48 | 38 s | — | ok | — |
| `coletar_dda.py` | coletor | 2026-10-17 02:14 | 54 s | — | ok | — |
| `coletar_desfechos_saude.py` | coletor | 2026-10-17 02:08 | 360 s | — | ok | — |
| `coletar_diarios_consorciados.py` | coletor | 2026-10-17 01:41 | 2704 s | 44 | ok | — |
| `coletar_diarios_municipais.py` | coletor | 2026-10-17 01:41 | 3 s | 0 | ok | — |
| `coletar_doe.py` | coletor | 2026-10-17 02:18 | 2538 s | — | ok | — |
| `coletar_edicoes_doe.py` | coletor | 2026-10-21 04:14 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `coletar_espin.py` | coletor | 2026-10-17 01:56 | 124 s | — | ok | — |
| `coletar_normais_inmet.py` | coletor | 2026-10-17 01:36 | 3 s | — | ok | — |
| `coletar_obitos.py` | coletor | 2026-10-25 01:50 | 9 s | — | ok | — |
| `coletar_obitos_registro_civil.py` | coletor | 2026-10-17 02:22 | 144 s | — | ok | — |
| `coletar_orientacoes_oficiais.py` | coletor | 2026-10-19 18:05 | 25 s | 6 | ok | — |
| `coletar_planos_arboviroses.py` | coletor | 2026-10-25 01:51 | 763 s | — | ok | — |
| `coletar_prioritarios_mma.py` | coletor | 2026-10-17 01:35 | 3 s | — | ok | — |
| `coletar_recursos_resposta.py` | coletor | 2026-10-17 03:18 | 15 s | — | ok | — |
| `coletar_s2id.py` | coletor | 2026-10-17 03:00 | 1084 s | — | ok | — |
| `coletar_saude.py` | coletor | 2026-10-17 02:01 | 76 s | — | ok | — |
| `coletar_saude_estadual.py` | coletor | 2026-10-21 04:14 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `coletar_semiarido_sudene.py` | coletor | 2026-10-17 01:36 | 2 s | — | ok | — |
| `coletar_sg_esus.py` | coletor | 2026-10-17 02:35 | 8 s | — | ok | — |
| `coletar_siconfi_182.py` | coletor | 2026-10-22 09:20 | 1 s | 5571 | ok | — |
| `coletar_sih.py` | coletor | 2026-10-25 01:51 | 5 s | — | **erro** (2 seguidas) | SIH: nenhum arquivo lido (0 na fila, 0 falha(s)); os arquivos anteriores ficam |
| `coletar_sim.py` | coletor | 2026-10-25 01:50 | 7 s | — | **erro** (3 seguidas) | SIM: nenhum arquivo lido (0 na fila, 0 falha(s)); os arquivos anteriores ficam |
| `coletar_sinais_risco.py` | coletor | 2026-10-17 02:13 | 98 s | — | ok | — |
| `coletar_sisab.py` | coletor | 2026-10-25 01:49 | 102 s | — | ok | — |
| `coletar_srag_gripe.py` | coletor | 2026-10-17 01:37 | 144 s | — | ok | — |
| `coletar_srag_sivep.py` | coletor | 2026-10-17 02:35 | 44 s | — | ok | — |
| `coletar_transferegov.py` | coletor | 2026-10-22 09:19 | 36 s | — | ok | — |
| `coletar_transferencias_municipais.py` | coletor | 2026-10-17 01:36 | 53 s | — | ok | — |
| `consultar_querido_diario.py` | coletor | 2026-10-17 01:35 | 305 s | — | **erro** (9 seguidas) | urllib.error.URLError: <urlopen error [SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] sslv3 alert handshake failure (_ssl.c:1010)> |
| `descobrir_dominios.py` | coletor | 2026-10-25 01:43 | 6141 s | — | **erro** (3 seguidas) | interrompido pelo prazo do elo |
| `descobrir_planos.py` | coletor | 2026-10-17 02:41 | 555 s | 42 | ok | — |
| `desfechos_sus.py` | coletor | 2026-10-25 01:50 | 1 s | — | ok | — |
| `detectar_marcos_federais.py` | coletor | 2026-10-17 02:51 | 1 s | 0 | ok | — |
| `julgar_e_aplicar_descobertas.py` | coletor | 2026-10-17 02:03 | 598 s | — | ok | — |
| `julgar_filas.py` | coletor | 2026-10-17 02:35 | 1310 s | — | ok | — |
| `julgar_saude.py` | coletor | 2026-10-21 03:05 | 2328 s | — | ok | — |
| `ler_planos_arboviroses.py` | coletor | 2026-10-25 02:03 | 5 s | — | ok | — |
| `monitorar_atos_resposta.py` | coletor | 2026-10-17 02:51 | 451 s | 8458 | ok | — |
| `monitorar_busca_web.py` | coletor | 2026-10-17 02:24 | 673 s | 83 | ok | — |
| `monitorar_imprensa_regional.py` | coletor | 2026-10-17 02:35 | 256 s | 40 | ok | — |
| `monitorar_imprensa_saude.py` | coletor | 2026-10-17 02:40 | 106 s | 27 | ok | — |
| `monitorar_politica_por_inteiro.py` | coletor | 2026-10-17 02:58 | 5 s | 8458 | ok | — |
| `monitorar_redes_oficiais.py` | coletor | 2026-10-17 07:02 | 1231 s | — | ok | — |
| `monitorar_sinais_federais.py` | coletor | 2026-10-17 02:24 | 5 s | 10 | ok | — |
| `preservar_evidencias.py` | coletor | 2026-10-17 02:20 | 1 s | — | ok | — |
| `processar_contribuicoes.py` | coletor | 2026-10-17 02:24 | 1 s | — | ok | — |
| `python3` | coletor | 2026-10-24 21:16 | 4721 s | — | ok | — |
| `revisar_pistas.py` | coletor | 2026-10-17 08:51 | 1036 s | — | ok | — |
| `scripts/amostra_auditoria_semanal.py` | coletor | 2026-10-17 09:23 | 1 s | — | ok | — |
| `scripts/corrigir_atribuicao_por_dominio.py` | coletor | 2026-10-17 08:51 | 12 s | — | ok | — |
| `scripts/fechar_saude.py` | coletor | 2026-10-21 04:14 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/preservar_textos_integrais.py` | coletor | 2026-10-17 02:20 | 2 s | — | ok | — |
| `scripts/reavaliar_fontes_suspensas.py` | coletor | 2026-10-17 01:58 | 659 s | — | ok | — |
| `scripts/sondar_boletim_infogripe.py` | coletor | 2026-10-17 01:36 | 88 s | — | ok | — |
| `scripts/triar_fila.py` | coletor | 2026-10-17 02:35 | 2 s | — | ok | — |
| `scripts/verificar_esquema_de_pista.py` | coletor | 2026-10-17 02:57 | 12 s | — | ok | — |
| `scripts/verificar_funil.py` | coletor | 2026-10-17 02:35 | 1 s | — | ok | — |
| `seguir_pistas.py` | coletor | 2026-10-17 07:22 | 48 s | — | ok | — |
| `sonda_url_doe.py` | coletor | 2026-10-20 18:03 | 202 s | — | ok | — |
| `triar_confianca_pistas.py` | coletor | 2026-10-17 07:23 | 5 s | — | ok | — |
| `verificar_links.py` | coletor | 2026-10-17 02:09 | 296 s | — | **erro** (11 seguidas) | erro: HTTPSConnectionPool(host='www.defesacivil.sc.gov.br', port=443): Max retries exceeded with url: /2026/08/14/chuva- |
| `verificar_pista_imprensa.py` | coletor | 2026-10-17 07:23 | 191 s | — | ok | — |
