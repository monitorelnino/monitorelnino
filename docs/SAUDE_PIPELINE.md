# Saúde do pipeline

Gerado por `scripts/gerar_saude_pipeline.py` a partir de `data/saude_pipeline.json`, que os
jobs escrevem com `scripts/saude_pipeline.py --rodar`. Item 2 do handover de desacoplamento
(27/09/2026). **Arquivo derivado: não se edita à mão.**

Duas classes, e a diferença importa. **Essencial** (`recalcular_mare.py`, `gerar_*.py`): se
erra, o site publica um estado que não corresponde ao dado — reprova o portão. **Coletor**:
fonte fora do ar é rotina, e uma falha isolada não é defeito do pipeline; erro em duas
rodadas seguidas vira alerta, porque aí não é a fonte, é o coletor.

Janela: 2026-10-21 a 2026-10-28 (1012 execução(ões) registrada(s), 7 dias de histórico).

## Alertas

- coletar_sih.py: erro em 4 rodadas seguidas — SIH: nenhum arquivo lido (0 na fila, 0 falha(s)); os arquivos anteriores ficam
- coletar_sim.py: erro em 5 rodadas seguidas — SIM: nenhum arquivo lido (0 na fila, 0 falha(s)); os arquivos anteriores ficam
- julgar_filas.py: erro em 3 rodadas seguidas — interrompido pelo prazo do elo
- verificar_links.py: erro em 2 rodadas seguidas — erro: HTTPSConnectionPool(host='www.defesacivil.sc.gov.br', port=443): Max retries exceeded with url: /2026/08/14/chuva-forte-deixa-danos-em-municipios-de-santa-catarina-e-risco-de-temporais-segue-alto-ate-sabado/ (Caused by ConnectTimeoutError(<HTTPSConnection(host='www.defesacivil.sc.gov.br', port

## Cobertura em 15 dias

cobertura 15d: 5055/5571 com verificação real até 2026-10-25 · por canal: web 1715 · QD 527 · consorciado 1668 · DOE 4175

## Última execução de cada script

| script | papel | última execução | duração | itens | status | erro |
|---|---|---|---|---:|---|---|
| `gerar_monitor_saude.py` | essencial | 2026-10-24 02:02 | 0 s | — | ok | — |
| `gerar_saude_municipio.py` | essencial | 2026-10-27 01:41 | 1 s | — | ok | — |
| `recalcular_mare.py` | essencial | 2026-10-28 09:56 | 3 s | — | ok | — |
| `aplicar_promocoes_do_juiz.py` | coletor | 2026-10-26 08:45 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `atualizar.py` | coletor | 2026-10-25 08:45 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `atualizar_populacao.py` | coletor | 2026-10-25 08:23 | 1 s | — | ok | — |
| `buscar_planos_fontes_abertas.py` | coletor | 2026-10-27 02:47 | 125 s | — | ok | — |
| `buscar_protocolo_calor.py` | coletor | 2026-10-27 01:19 | 16 s | 3 | ok | — |
| `classificar_planos_municipais.py` | coletor | 2026-10-24 01:24 | 1 s | — | ok | — |
| `classificar_saude_no_plano.py` | coletor | 2026-10-27 01:41 | 1 s | — | ok | — |
| `coletar_arboviroses_sinan.py` | coletor | 2026-10-27 01:40 | 14 s | — | ok | — |
| `coletar_boletim_df_arboviroses.py` | coletor | 2026-10-27 01:27 | 537 s | — | ok | — |
| `coletar_boletim_ms_dengue.py` | coletor | 2026-10-27 01:27 | 17 s | — | ok | — |
| `coletar_boletim_pb_arboviroses.py` | coletor | 2026-10-27 01:37 | 193 s | — | ok | — |
| `coletar_boletim_pe_arboviroses.py` | coletor | 2026-10-27 01:36 | 67 s | — | ok | — |
| `coletar_cadastro_prioritarios.py` | coletor | 2026-10-24 01:12 | 30 s | — | ok | — |
| `coletar_cobertura_qd.py` | coletor | 2026-10-24 01:24 | 1106 s | — | ok | — |
| `coletar_datasus_dbc.py` | coletor | 2026-10-27 01:13 | 38 s | — | ok | — |
| `coletar_dda.py` | coletor | 2026-10-27 01:26 | 55 s | — | ok | — |
| `coletar_desfechos_saude.py` | coletor | 2026-10-27 01:20 | 362 s | — | ok | — |
| `coletar_diarios_consorciados.py` | coletor | 2026-10-21 01:12 | 3935 s | 61 | ok | — |
| `coletar_diarios_municipais.py` | coletor | 2026-10-21 01:10 | 95 s | 1 | ok | — |
| `coletar_doe.py` | coletor | 2026-10-22 02:17 | 2541 s | — | ok | — |
| `coletar_edicoes_doe.py` | coletor | 2026-10-27 02:25 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `coletar_espin.py` | coletor | 2026-10-27 01:13 | 322 s | — | ok | — |
| `coletar_normais_inmet.py` | coletor | 2026-10-24 01:18 | 3 s | — | ok | — |
| `coletar_obitos.py` | coletor | 2026-10-27 01:16 | 4 s | — | ok | — |
| `coletar_obitos_registro_civil.py` | coletor | 2026-10-27 01:41 | 37 s | — | ok | — |
| `coletar_planos_arboviroses.py` | coletor | 2026-10-27 01:17 | 939 s | — | ok | — |
| `coletar_prioritarios_mma.py` | coletor | 2026-10-24 01:13 | 310 s | — | **erro** | urllib.error.HTTPError: HTTP Error 502: Bad Gateway |
| `coletar_recursos_resposta.py` | coletor | 2026-10-22 03:20 | 89 s | — | ok | — |
| `coletar_s2id.py` | coletor | 2026-10-22 03:00 | 1229 s | — | ok | — |
| `coletar_saude.py` | coletor | 2026-10-27 01:12 | 88 s | — | ok | — |
| `coletar_saude_estadual.py` | coletor | 2026-10-27 02:25 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `coletar_semiarido_sudene.py` | coletor | 2026-10-24 01:18 | 2 s | — | ok | — |
| `coletar_sg_esus.py` | coletor | 2026-10-24 01:12 | 7 s | — | **erro** | return opener.open(url, data, timeout) |
| `coletar_siconfi_182.py` | coletor | 2026-10-22 09:20 | 1 s | 5571 | ok | — |
| `coletar_sih.py` | coletor | 2026-10-27 01:16 | 5 s | — | **erro** (4 seguidas) | SIH: nenhum arquivo lido (0 na fila, 0 falha(s)); os arquivos anteriores ficam |
| `coletar_sim.py` | coletor | 2026-10-27 01:16 | 8 s | — | **erro** (5 seguidas) | SIM: nenhum arquivo lido (0 na fila, 0 falha(s)); os arquivos anteriores ficam |
| `coletar_sinais_risco.py` | coletor | 2026-10-27 01:13 | 100 s | — | ok | — |
| `coletar_sisab.py` | coletor | 2026-10-27 01:14 | 138 s | — | ok | — |
| `coletar_srag_gripe.py` | coletor | 2026-10-24 01:19 | 282 s | — | ok | — |
| `coletar_srag_sivep.py` | coletor | 2026-10-24 01:12 | 8 s | — | ok | — |
| `coletar_transferegov.py` | coletor | 2026-10-22 09:19 | 36 s | — | ok | — |
| `coletar_transferencias_municipais.py` | coletor | 2026-10-27 01:15 | 59 s | — | ok | — |
| `consultar_querido_diario.py` | coletor | 2026-10-21 01:05 | 316 s | — | **erro** | urllib.error.URLError: <urlopen error [SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] sslv3 alert handshake failure (_ssl.c:1010)> |
| `descobrir_dominios.py` | coletor | 2026-10-25 01:43 | 6141 s | — | **erro** | interrompido pelo prazo do elo |
| `descobrir_planos.py` | coletor | 2026-10-28 08:13 | 487 s | 42 | ok | — |
| `desfechos_sus.py` | coletor | 2026-10-27 01:16 | 0 s | — | ok | — |
| `detectar_marcos_federais.py` | coletor | 2026-10-28 08:13 | 1 s | 0 | ok | — |
| `julgar_e_aplicar_descobertas.py` | coletor | 2026-10-26 08:45 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `julgar_filas.py` | coletor | 2026-10-26 08:26 | 1108 s | — | **erro** (3 seguidas) | interrompido pelo prazo do elo |
| `julgar_saude.py` | coletor | 2026-10-27 01:13 | 4321 s | — | **erro** | interrompido pelo prazo do elo |
| `ler_planos_arboviroses.py` | coletor | 2026-10-27 01:32 | 4 s | — | ok | — |
| `monitorar_atos_resposta.py` | coletor | 2026-10-28 07:53 | 1202 s | 16592 | ok | — |
| `monitorar_busca_web.py` | coletor | 2026-10-28 08:21 | 247 s | — | ok | — |
| `monitorar_imprensa_regional.py` | coletor | 2026-10-28 07:46 | 308 s | 40 | ok | — |
| `monitorar_imprensa_saude.py` | coletor | 2026-10-28 07:51 | 105 s | 27 | ok | — |
| `monitorar_politica_por_inteiro.py` | coletor | 2026-10-28 08:13 | 4 s | 16592 | ok | — |
| `monitorar_redes_oficiais.py` | coletor | 2026-10-26 07:34 | 1012 s | — | ok | — |
| `monitorar_sinais_federais.py` | coletor | 2026-10-28 08:13 | 5 s | 10 | ok | — |
| `preservar_evidencias.py` | coletor | 2026-10-28 08:49 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `processar_contribuicoes.py` | coletor | 2026-10-25 08:23 | 1 s | — | ok | — |
| `python3` | coletor | 2026-10-26 22:34 | 33 s | — | ok | — |
| `revisar_pistas.py` | coletor | 2026-10-26 08:03 | 1374 s | — | ok | — |
| `scripts/amostra_auditoria_semanal.py` | coletor | 2026-10-26 08:45 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/corrigir_atribuicao_por_dominio.py` | coletor | 2026-10-26 08:02 | 61 s | — | ok | — |
| `scripts/fechar_saude.py` | coletor | 2026-10-27 02:25 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/preservar_textos_integrais.py` | coletor | 2026-10-28 08:49 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/reavaliar_fontes_suspensas.py` | coletor | 2026-10-27 01:19 | 718 s | — | ok | — |
| `scripts/rejulgar_decisoes_do_juiz.py` | coletor | 2026-10-27 21:48 | 5905 s | — | ok | — |
| `scripts/sondar_boletim_infogripe.py` | coletor | 2026-10-24 01:18 | 84 s | — | ok | — |
| `scripts/triar_fila.py` | coletor | 2026-10-22 08:49 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/verificar_esquema_de_pista.py` | coletor | 2026-10-22 08:49 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/verificar_funil.py` | coletor | 2026-10-25 08:35 | 0 s | — | ok | — |
| `seguir_pistas.py` | coletor | 2026-10-28 08:26 | 16 s | — | ok | — |
| `triar_confianca_pistas.py` | coletor | 2026-10-28 08:26 | 3 s | — | ok | — |
| `verificar_links.py` | coletor | 2026-10-27 01:31 | 226 s | — | **erro** (2 seguidas) | erro: HTTPSConnectionPool(host='www.defesacivil.sc.gov.br', port=443): Max retries exceeded with url: /2026/08/14/chuva- |
| `verificar_pista_imprensa.py` | coletor | 2026-10-28 08:26 | 111 s | — | **erro** | interrompido pelo prazo do elo |
