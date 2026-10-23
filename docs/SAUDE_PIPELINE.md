# Saúde do pipeline

Gerado por `scripts/gerar_saude_pipeline.py` a partir de `data/saude_pipeline.json`, que os
jobs escrevem com `scripts/saude_pipeline.py --rodar`. Item 2 do handover de desacoplamento
(27/09/2026). **Arquivo derivado: não se edita à mão.**

Duas classes, e a diferença importa. **Essencial** (`recalcular_mare.py`, `gerar_*.py`): se
erra, o site publica um estado que não corresponde ao dado — reprova o portão. **Coletor**:
fonte fora do ar é rotina, e uma falha isolada não é defeito do pipeline; erro em duas
rodadas seguidas vira alerta, porque aí não é a fonte, é o coletor.

Janela: 2026-10-16 a 2026-10-23 (986 execução(ões) registrada(s), 7 dias de histórico).

## Alertas

- coletar_sih.py: erro em 2 rodadas seguidas — SIH: nenhum arquivo lido (0 na fila, 0 falha(s)); os arquivos anteriores ficam
- consultar_querido_diario.py: erro em 5 rodadas seguidas — urllib.error.URLError: <urlopen error [SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] sslv3 alert handshake failure (_ssl.c:1010)>
- descobrir_dominios.py: erro em 2 rodadas seguidas — interrompido pelo prazo do elo
- verificar_links.py: erro em 2 rodadas seguidas — erro: HTTPSConnectionPool(host='www.defesacivil.sc.gov.br', port=443): Max retries exceeded with url: /2026/08/14/chuva-forte-deixa-danos-em-municipios-de-santa-catarina-e-risco-de-temporais-segue-alto-ate-sabado/ (Caused by ConnectTimeoutError(<HTTPSConnection(host='www.defesacivil.sc.gov.br', port
- verificar_pista_imprensa.py: erro em 4 rodadas seguidas — interrompido pelo prazo do elo

## Cobertura em 15 dias

cobertura 15d: 5055/5571 com verificação real até 2026-10-22 · por canal: web 1553 · QD 527 · consorciado 1668 · DOE 4175

## Última execução de cada script

| script | papel | última execução | duração | itens | status | erro |
|---|---|---|---|---:|---|---|
| `gerar_monitor_saude.py` | essencial | 2026-10-18 08:41 | 1 s | — | ok | — |
| `gerar_saude_municipio.py` | essencial | 2026-10-22 01:33 | 0 s | — | ok | — |
| `recalcular_mare.py` | essencial | 2026-10-23 19:35 | 3 s | — | ok | — |
| `aplicar_promocoes_do_juiz.py` | coletor | 2026-10-22 08:49 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `atualizar.py` | coletor | 2026-10-18 08:39 | 87 s | — | ok | — |
| `atualizar_populacao.py` | coletor | 2026-10-18 08:00 | 1 s | — | ok | — |
| `buscar_planos_fontes_abertas.py` | coletor | 2026-10-23 06:30 | 8710 s | — | ok | — |
| `buscar_protocolo_calor.py` | coletor | 2026-10-17 01:58 | 13 s | 3 | ok | — |
| `classificar_planos_municipais.py` | coletor | 2026-10-18 03:56 | 1 s | — | ok | — |
| `classificar_saude_no_plano.py` | coletor | 2026-10-22 01:33 | 0 s | — | ok | — |
| `coletar_arboviroses_sinan.py` | coletor | 2026-10-22 01:32 | 13 s | — | ok | — |
| `coletar_boletim_df_arboviroses.py` | coletor | 2026-10-22 01:22 | 267 s | — | ok | — |
| `coletar_boletim_ms_dengue.py` | coletor | 2026-10-22 01:21 | 15 s | — | ok | — |
| `coletar_boletim_pb_arboviroses.py` | coletor | 2026-10-22 01:29 | 194 s | — | ok | — |
| `coletar_boletim_pe_arboviroses.py` | coletor | 2026-10-22 01:26 | 164 s | — | ok | — |
| `coletar_cadastro_prioritarios.py` | coletor | 2026-10-18 03:51 | 34 s | — | ok | — |
| `coletar_cobertura_qd.py` | coletor | 2026-10-18 03:56 | 6883 s | — | ok | — |
| `coletar_datasus_dbc.py` | coletor | 2026-10-22 01:09 | 42 s | — | ok | — |
| `coletar_dda.py` | coletor | 2026-10-22 01:21 | 55 s | — | ok | — |
| `coletar_desfechos_saude.py` | coletor | 2026-10-22 01:15 | 358 s | — | ok | — |
| `coletar_diarios_consorciados.py` | coletor | 2026-10-21 01:12 | 3935 s | 61 | ok | — |
| `coletar_diarios_municipais.py` | coletor | 2026-10-21 01:10 | 95 s | 1 | ok | — |
| `coletar_doe.py` | coletor | 2026-10-22 02:17 | 2541 s | — | ok | — |
| `coletar_edicoes_doe.py` | coletor | 2026-10-21 04:14 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `coletar_espin.py` | coletor | 2026-10-17 01:56 | 124 s | — | ok | — |
| `coletar_normais_inmet.py` | coletor | 2026-10-18 03:52 | 4 s | — | ok | — |
| `coletar_obitos.py` | coletor | 2026-10-22 01:11 | 17 s | — | ok | — |
| `coletar_obitos_registro_civil.py` | coletor | 2026-10-22 01:32 | 42 s | — | ok | — |
| `coletar_orientacoes_oficiais.py` | coletor | 2026-10-19 18:05 | 25 s | 6 | ok | — |
| `coletar_planos_arboviroses.py` | coletor | 2026-10-22 01:12 | 1450 s | — | ok | — |
| `coletar_prioritarios_mma.py` | coletor | 2026-10-18 03:52 | 4 s | — | ok | — |
| `coletar_recursos_resposta.py` | coletor | 2026-10-22 03:20 | 89 s | — | ok | — |
| `coletar_s2id.py` | coletor | 2026-10-22 03:00 | 1229 s | — | ok | — |
| `coletar_saude.py` | coletor | 2026-10-22 01:08 | 65 s | — | ok | — |
| `coletar_saude_estadual.py` | coletor | 2026-10-21 04:14 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `coletar_semiarido_sudene.py` | coletor | 2026-10-18 03:52 | 3 s | — | ok | — |
| `coletar_sg_esus.py` | coletor | 2026-10-18 03:26 | 10 s | — | ok | — |
| `coletar_siconfi_182.py` | coletor | 2026-10-22 09:20 | 1 s | 5571 | ok | — |
| `coletar_sih.py` | coletor | 2026-10-22 01:12 | 6 s | — | **erro** (2 seguidas) | SIH: nenhum arquivo lido (0 na fila, 0 falha(s)); os arquivos anteriores ficam |
| `coletar_sinais_risco.py` | coletor | 2026-10-23 09:27 | 90 s | — | ok | — |
| `coletar_sisab.py` | coletor | 2026-10-22 01:10 | 105 s | — | ok | — |
| `coletar_srag_gripe.py` | coletor | 2026-10-18 03:53 | 146 s | — | ok | — |
| `coletar_srag_sivep.py` | coletor | 2026-10-18 03:25 | 39 s | — | ok | — |
| `coletar_transferegov.py` | coletor | 2026-10-22 09:19 | 36 s | — | ok | — |
| `coletar_transferencias_municipais.py` | coletor | 2026-10-23 09:29 | 54 s | — | ok | — |
| `consultar_querido_diario.py` | coletor | 2026-10-21 01:05 | 316 s | — | **erro** (5 seguidas) | urllib.error.URLError: <urlopen error [SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] sslv3 alert handshake failure (_ssl.c:1010)> |
| `descobrir_dominios.py` | coletor | 2026-10-18 05:50 | 823 s | — | **erro** (2 seguidas) | interrompido pelo prazo do elo |
| `descobrir_planos.py` | coletor | 2026-10-23 07:07 | 476 s | 42 | ok | — |
| `desfechos_sus.py` | coletor | 2026-10-22 01:11 | 0 s | — | ok | — |
| `detectar_marcos_federais.py` | coletor | 2026-10-23 07:07 | 1 s | 0 | ok | — |
| `julgar_e_aplicar_descobertas.py` | coletor | 2026-10-22 08:45 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `julgar_filas.py` | coletor | 2026-10-22 08:49 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `julgar_saude.py` | coletor | 2026-10-21 03:05 | 2328 s | — | ok | — |
| `monitorar_atos_resposta.py` | coletor | 2026-10-23 07:04 | 196 s | 16494 | ok | — |
| `monitorar_busca_web.py` | coletor | 2026-10-22 08:49 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `monitorar_imprensa_regional.py` | coletor | 2026-10-23 06:55 | 428 s | 40 | ok | — |
| `monitorar_imprensa_saude.py` | coletor | 2026-10-23 07:02 | 103 s | 27 | ok | — |
| `monitorar_politica_por_inteiro.py` | coletor | 2026-10-23 07:07 | 4 s | 16494 | ok | — |
| `monitorar_redes_oficiais.py` | coletor | 2026-10-23 07:15 | 1163 s | — | ok | — |
| `monitorar_sinais_federais.py` | coletor | 2026-10-23 07:07 | 4 s | 10 | ok | — |
| `preservar_evidencias.py` | coletor | 2026-10-23 08:05 | 1 s | — | ok | — |
| `processar_contribuicoes.py` | coletor | 2026-10-18 08:00 | 1 s | — | ok | — |
| `python3` | coletor | 2026-10-23 13:52 | 30 s | 13 | ok | — |
| `revisar_pistas.py` | coletor | 2026-10-22 08:28 | 825 s | — | ok | — |
| `scripts/amostra_auditoria_semanal.py` | coletor | 2026-10-22 08:45 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/corrigir_atribuicao_por_dominio.py` | coletor | 2026-10-22 08:27 | 68 s | — | ok | — |
| `scripts/fechar_saude.py` | coletor | 2026-10-21 04:14 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/preservar_textos_integrais.py` | coletor | 2026-10-23 08:06 | 2 s | — | ok | — |
| `scripts/reavaliar_fontes_suspensas.py` | coletor | 2026-10-17 01:58 | 659 s | — | ok | — |
| `scripts/sondar_boletim_infogripe.py` | coletor | 2026-10-18 03:52 | 84 s | — | ok | — |
| `scripts/triar_fila.py` | coletor | 2026-10-22 08:49 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/verificar_esquema_de_pista.py` | coletor | 2026-10-22 08:49 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/verificar_funil.py` | coletor | 2026-10-18 08:12 | 1 s | — | ok | — |
| `seguir_pistas.py` | coletor | 2026-10-23 07:34 | 48 s | — | ok | — |
| `sonda_url_doe.py` | coletor | 2026-10-20 18:03 | 202 s | — | ok | — |
| `triar_confianca_pistas.py` | coletor | 2026-10-23 07:35 | 4 s | — | ok | — |
| `verificar_links.py` | coletor | 2026-10-17 02:09 | 296 s | — | **erro** (2 seguidas) | erro: HTTPSConnectionPool(host='www.defesacivil.sc.gov.br', port=443): Max retries exceeded with url: /2026/08/14/chuva- |
| `verificar_pista_imprensa.py` | coletor | 2026-10-23 07:35 | 111 s | — | **erro** (4 seguidas) | interrompido pelo prazo do elo |
