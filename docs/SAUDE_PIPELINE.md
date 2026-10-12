# Saúde do pipeline

Gerado por `scripts/gerar_saude_pipeline.py` a partir de `data/saude_pipeline.json`, que os
jobs escrevem com `scripts/saude_pipeline.py --rodar`. Item 2 do handover de desacoplamento
(27/09/2026). **Arquivo derivado: não se edita à mão.**

Duas classes, e a diferença importa. **Essencial** (`recalcular_mare.py`, `gerar_*.py`): se
erra, o site publica um estado que não corresponde ao dado — reprova o portão. **Coletor**:
fonte fora do ar é rotina, e uma falha isolada não é defeito do pipeline; erro em duas
rodadas seguidas vira alerta, porque aí não é a fonte, é o coletor.

Janela: 2026-10-05 a 2026-10-12 (749 execução(ões) registrada(s), 7 dias de histórico).

## Alertas

- consultar_querido_diario.py: erro em 2 rodadas seguidas — urllib.error.URLError: <urlopen error [SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] sslv3 alert handshake failure (_ssl.c:1010)>
- monitorar_imprensa_saude.py: erro em 18 rodadas seguidas — KeyError: 'hash'
- monitorar_politica_por_inteiro.py: erro em 16 rodadas seguidas — NameError: name 'ler' is not defined. Did you mean: 'len'?
- monitorar_redes_oficiais.py: erro em 3 rodadas seguidas — interrompido pelo prazo do elo
- verificar_links.py: erro em 3 rodadas seguidas — erro: HTTPSConnectionPool(host='www.defesacivil.sc.gov.br', port=443): Max retries exceeded with url: /2026/08/14/chuva-forte-deixa-danos-em-municipios-de-santa-catarina-e-risco-de-temporais-segue-alto-ate-sabado/ (Caused by ConnectTimeoutError(<HTTPSConnection(host='www.defesacivil.sc.gov.br', port

## Última execução de cada script

| script | papel | última execução | duração | itens | status | erro |
|---|---|---|---|---:|---|---|
| `recalcular_mare.py` | essencial | 2026-10-12 09:51 | 2 s | — | ok | — |
| `aplicar_promocoes_do_juiz.py` | coletor | 2026-10-12 09:14 | 0 s | — | ok | — |
| `buscar_protocolo_calor.py` | coletor | 2026-10-12 07:33 | 11 s | 3 | ok | — |
| `classificar_planos_municipais.py` | coletor | 2026-10-12 05:24 | 0 s | — | ok | — |
| `classificar_saude_no_plano.py` | coletor | 2026-10-11 01:43 | 1 s | — | ok | — |
| `coletar_arboviroses_sinan.py` | coletor | 2026-10-11 01:42 | 60 s | — | ok | — |
| `coletar_boletim_df_arboviroses.py` | coletor | 2026-10-11 01:31 | 446 s | — | ok | — |
| `coletar_boletim_ms_dengue.py` | coletor | 2026-10-11 01:31 | 20 s | — | ok | — |
| `coletar_boletim_pb_arboviroses.py` | coletor | 2026-10-11 01:38 | 193 s | — | ok | — |
| `coletar_boletim_pe_arboviroses.py` | coletor | 2026-10-11 01:38 | 8 s | — | ok | — |
| `coletar_cadastro_prioritarios.py` | coletor | 2026-10-12 07:42 | 29 s | — | ok | — |
| `coletar_cobertura_qd.py` | coletor | 2026-10-12 05:24 | 2562 s | — | ok | — |
| `coletar_dda.py` | coletor | 2026-10-11 01:30 | 54 s | — | ok | — |
| `coletar_desfechos_saude.py` | coletor | 2026-10-11 01:23 | 414 s | — | ok | — |
| `coletar_diarios_consorciados.py` | coletor | 2026-10-11 01:49 | 2028 s | 34 | ok | — |
| `coletar_diarios_municipais.py` | coletor | 2026-10-11 01:47 | 109 s | 50 | ok | — |
| `coletar_doe.py` | coletor | 2026-10-11 02:22 | 841 s | — | ok | — |
| `coletar_espin.py` | coletor | 2026-10-12 07:31 | 97 s | — | ok | — |
| `coletar_execucao_mps.py` | coletor | 2026-10-12 07:51 | 16 s | — | ok | — |
| `coletar_normais_inmet.py` | coletor | 2026-10-12 05:08 | 291 s | — | **erro** | urllib.error.URLError: <urlopen error [Errno 110] Connection timed out> |
| `coletar_obitos_registro_civil.py` | coletor | 2026-10-11 01:43 | 35 s | — | ok | — |
| `coletar_prioritarios_mma.py` | coletor | 2026-10-12 07:43 | 2 s | — | ok | — |
| `coletar_recursos_resposta.py` | coletor | 2026-10-11 02:52 | 9 s | — | ok | — |
| `coletar_s2id.py` | coletor | 2026-10-11 02:36 | 916 s | — | ok | — |
| `coletar_saude.py` | coletor | 2026-10-11 01:12 | 196 s | — | ok | — |
| `coletar_semiarido_sudene.py` | coletor | 2026-10-12 07:43 | 4 s | — | ok | — |
| `coletar_sg_esus.py` | coletor | 2026-10-11 03:37 | 8 s | — | ok | — |
| `coletar_siconfi_182.py` | coletor | 2026-10-12 07:51 | 1 s | 5571 | ok | — |
| `coletar_sinais_risco.py` | coletor | 2026-10-12 06:07 | 2538 s | — | ok | — |
| `coletar_srag_gripe.py` | coletor | 2026-10-12 05:19 | 282 s | — | ok | — |
| `coletar_srag_sivep.py` | coletor | 2026-10-11 03:36 | 34 s | — | ok | — |
| `coletar_transferegov.py` | coletor | 2026-10-12 07:50 | 36 s | — | ok | — |
| `coletar_transferencias_municipais.py` | coletor | 2026-10-12 05:21 | 67 s | — | ok | — |
| `consultar_querido_diario.py` | coletor | 2026-10-11 01:14 | 781 s | — | **erro** (2 seguidas) | urllib.error.URLError: <urlopen error [SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] sslv3 alert handshake failure (_ssl.c:1010)> |
| `descobrir_dominios.py` | coletor | 2026-10-12 06:49 | 1682 s | — | **erro** | interrompido pelo prazo do elo |
| `descobrir_planos.py` | coletor | 2026-10-12 08:11 | 900 s | 42 | ok | — |
| `detectar_marcos_federais.py` | coletor | 2026-10-12 08:11 | 1 s | 0 | ok | — |
| `julgar_e_aplicar_descobertas.py` | coletor | 2026-10-12 08:55 | 1148 s | — | ok | — |
| `julgar_filas.py` | coletor | 2026-10-12 08:54 | 28 s | — | ok | — |
| `monitorar_atos_resposta.py` | coletor | 2026-10-12 08:09 | 80 s | 3478 | ok | — |
| `monitorar_imprensa_regional.py` | coletor | 2026-10-12 08:08 | 104 s | 40 | ok | — |
| `monitorar_imprensa_saude.py` | coletor | 2026-10-12 08:09 | 1 s | — | **erro** (18 seguidas) | KeyError: 'hash' |
| `monitorar_politica_por_inteiro.py` | coletor | 2026-10-12 08:11 | 4 s | 3478 | **erro** (16 seguidas) | NameError: name 'ler' is not defined. Did you mean: 'len'? |
| `monitorar_redes_oficiais.py` | coletor | 2026-10-12 08:26 | 1456 s | — | **erro** (3 seguidas) | interrompido pelo prazo do elo |
| `monitorar_sinais_federais.py` | coletor | 2026-10-12 08:11 | 4 s | 10 | ok | — |
| `preservar_evidencias.py` | coletor | 2026-10-12 04:57 | 1 s | — | ok | — |
| `revisar_pistas.py` | coletor | 2026-10-12 08:54 | 2 s | — | ok | — |
| `scripts/amostra_auditoria_semanal.py` | coletor | 2026-10-12 09:14 | 0 s | — | ok | — |
| `scripts/corrigir_atribuicao_por_dominio.py` | coletor | 2026-10-12 08:54 | 12 s | — | ok | — |
| `scripts/preservar_textos_integrais.py` | coletor | 2026-10-12 04:58 | 2 s | — | ok | — |
| `scripts/sondar_boletim_infogripe.py` | coletor | 2026-10-12 05:13 | 366 s | — | ok | — |
| `scripts/triar_fila.py` | coletor | 2026-10-11 02:55 | 1 s | — | ok | — |
| `scripts/verificar_esquema_de_pista.py` | coletor | 2026-10-12 03:18 | 1 s | — | ok | — |
| `seguir_pistas.py` | coletor | 2026-10-12 08:50 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `triar_confianca_pistas.py` | coletor | 2026-10-12 08:50 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `verificar_links.py` | coletor | 2026-10-12 07:33 | 163 s | — | **erro** (3 seguidas) | erro: HTTPSConnectionPool(host='www.defesacivil.sc.gov.br', port=443): Max retries exceeded with url: /2026/08/14/chuva- |
| `verificar_pista_imprensa.py` | coletor | 2026-10-12 08:50 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
