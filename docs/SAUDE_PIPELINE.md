# Saúde do pipeline

Gerado por `scripts/gerar_saude_pipeline.py` a partir de `data/saude_pipeline.json`, que os
jobs escrevem com `scripts/saude_pipeline.py --rodar`. Item 2 do handover de desacoplamento
(27/09/2026). **Arquivo derivado: não se edita à mão.**

Duas classes, e a diferença importa. **Essencial** (`recalcular_mare.py`, `gerar_*.py`): se
erra, o site publica um estado que não corresponde ao dado — reprova o portão. **Coletor**:
fonte fora do ar é rotina, e uma falha isolada não é defeito do pipeline; erro em duas
rodadas seguidas vira alerta, porque aí não é a fonte, é o coletor.

Janela: 2026-10-06 a 2026-10-13 (806 execução(ões) registrada(s), 7 dias de histórico).

## Alertas

- consultar_querido_diario.py: erro em 3 rodadas seguidas — urllib.error.URLError: <urlopen error [SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] sslv3 alert handshake failure (_ssl.c:1010)>
- descobrir_dominios.py: erro em 2 rodadas seguidas — interrompido pelo prazo do elo
- monitorar_imprensa_saude.py: erro em 18 rodadas seguidas — KeyError: 'hash'
- monitorar_politica_por_inteiro.py: erro em 19 rodadas seguidas — NameError: name 'ler' is not defined. Did you mean: 'len'?
- verificar_links.py: erro em 3 rodadas seguidas — erro: HTTPSConnectionPool(host='www.defesacivil.sc.gov.br', port=443): Max retries exceeded with url: /2026/08/14/chuva-forte-deixa-danos-em-municipios-de-santa-catarina-e-risco-de-temporais-segue-alto-ate-sabado/ (Caused by ConnectTimeoutError(<HTTPSConnection(host='www.defesacivil.sc.gov.br', port

## Última execução de cada script

| script | papel | última execução | duração | itens | status | erro |
|---|---|---|---|---:|---|---|
| `recalcular_mare.py` | essencial | 2026-10-13 16:52 | 2 s | — | ok | — |
| `aplicar_promocoes_do_juiz.py` | coletor | 2026-10-13 04:16 | 1 s | — | ok | — |
| `buscar_protocolo_calor.py` | coletor | 2026-10-12 07:33 | 11 s | 3 | ok | — |
| `classificar_planos_municipais.py` | coletor | 2026-10-13 06:56 | 1 s | — | ok | — |
| `classificar_saude_no_plano.py` | coletor | 2026-10-12 01:30 | 0 s | — | ok | — |
| `coletar_arboviroses_sinan.py` | coletor | 2026-10-12 01:28 | 40 s | — | ok | — |
| `coletar_boletim_df_arboviroses.py` | coletor | 2026-10-12 01:23 | 301 s | — | ok | — |
| `coletar_boletim_ms_dengue.py` | coletor | 2026-10-12 01:23 | 16 s | — | ok | — |
| `coletar_boletim_pb_arboviroses.py` | coletor | 2026-10-12 01:28 | 4 s | — | ok | — |
| `coletar_boletim_pe_arboviroses.py` | coletor | 2026-10-12 01:28 | 6 s | — | ok | — |
| `coletar_cadastro_prioritarios.py` | coletor | 2026-10-13 06:52 | 31 s | — | ok | — |
| `coletar_cobertura_qd.py` | coletor | 2026-10-13 06:56 | 2134 s | — | ok | — |
| `coletar_dda.py` | coletor | 2026-10-12 01:22 | 56 s | — | ok | — |
| `coletar_desfechos_saude.py` | coletor | 2026-10-12 01:15 | 405 s | — | ok | — |
| `coletar_diarios_consorciados.py` | coletor | 2026-10-12 01:33 | 1872 s | 34 | ok | — |
| `coletar_diarios_municipais.py` | coletor | 2026-10-12 01:28 | 299 s | 50 | ok | — |
| `coletar_doe.py` | coletor | 2026-10-12 02:04 | 841 s | — | ok | — |
| `coletar_espin.py` | coletor | 2026-10-12 07:31 | 97 s | — | ok | — |
| `coletar_execucao_mps.py` | coletor | 2026-10-12 07:51 | 16 s | — | ok | — |
| `coletar_normais_inmet.py` | coletor | 2026-10-13 06:52 | 4 s | — | ok | — |
| `coletar_obitos_registro_civil.py` | coletor | 2026-10-12 01:29 | 92 s | — | ok | — |
| `coletar_prioritarios_mma.py` | coletor | 2026-10-13 06:52 | 4 s | — | ok | — |
| `coletar_recursos_resposta.py` | coletor | 2026-10-12 02:32 | 8 s | — | ok | — |
| `coletar_s2id.py` | coletor | 2026-10-12 02:18 | 871 s | — | ok | — |
| `coletar_saude.py` | coletor | 2026-10-12 01:02 | 370 s | — | ok | — |
| `coletar_semiarido_sudene.py` | coletor | 2026-10-13 06:52 | 3 s | — | ok | — |
| `coletar_sg_esus.py` | coletor | 2026-10-11 03:37 | 8 s | — | ok | — |
| `coletar_siconfi_182.py` | coletor | 2026-10-12 07:51 | 1 s | 5571 | ok | — |
| `coletar_sinais_risco.py` | coletor | 2026-10-13 07:32 | 1998 s | — | ok | — |
| `coletar_srag_gripe.py` | coletor | 2026-10-13 06:54 | 144 s | — | ok | — |
| `coletar_srag_sivep.py` | coletor | 2026-10-11 03:36 | 34 s | — | ok | — |
| `coletar_transferegov.py` | coletor | 2026-10-12 07:50 | 36 s | — | ok | — |
| `coletar_transferencias_municipais.py` | coletor | 2026-10-12 01:03 | 39 s | — | ok | — |
| `consultar_querido_diario.py` | coletor | 2026-10-12 01:03 | 898 s | — | **erro** (3 seguidas) | urllib.error.URLError: <urlopen error [SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] sslv3 alert handshake failure (_ssl.c:1010)> |
| `descobrir_dominios.py` | coletor | 2026-10-13 08:05 | 3546 s | — | **erro** (2 seguidas) | interrompido pelo prazo do elo |
| `descobrir_planos.py` | coletor | 2026-10-13 08:34 | 1205 s | 42 | ok | — |
| `detectar_marcos_federais.py` | coletor | 2026-10-13 08:34 | 2 s | 0 | ok | — |
| `julgar_e_aplicar_descobertas.py` | coletor | 2026-10-13 04:06 | 638 s | — | ok | — |
| `julgar_filas.py` | coletor | 2026-10-13 04:03 | 134 s | — | ok | — |
| `monitorar_atos_resposta.py` | coletor | 2026-10-13 08:32 | 101 s | 3488 | ok | — |
| `monitorar_busca_web.py` | coletor | 2026-10-13 09:39 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `monitorar_imprensa_regional.py` | coletor | 2026-10-13 08:30 | 128 s | 40 | ok | — |
| `monitorar_imprensa_saude.py` | coletor | 2026-10-13 08:32 | 0 s | — | **erro** (18 seguidas) | KeyError: 'hash' |
| `monitorar_politica_por_inteiro.py` | coletor | 2026-10-13 08:34 | 3 s | 3488 | **erro** (19 seguidas) | NameError: name 'ler' is not defined. Did you mean: 'len'? |
| `monitorar_redes_oficiais.py` | coletor | 2026-10-13 08:54 | 1149 s | — | **erro** | interrompido pelo prazo do elo |
| `monitorar_sinais_federais.py` | coletor | 2026-10-13 08:34 | 4 s | 10 | ok | — |
| `motores_busca.py` | coletor | 2026-10-13 09:39 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `preservar_evidencias.py` | coletor | 2026-10-13 03:56 | 46 s | — | ok | — |
| `revisar_pistas.py` | coletor | 2026-10-13 09:39 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/amostra_auditoria_semanal.py` | coletor | 2026-10-13 04:16 | 1 s | — | ok | — |
| `scripts/corrigir_atribuicao_por_dominio.py` | coletor | 2026-10-13 04:03 | 13 s | — | ok | — |
| `scripts/preservar_textos_integrais.py` | coletor | 2026-10-13 03:56 | 2 s | — | ok | — |
| `scripts/sondar_boletim_infogripe.py` | coletor | 2026-10-13 06:52 | 86 s | — | ok | — |
| `scripts/triar_fila.py` | coletor | 2026-10-12 02:36 | 2 s | — | ok | — |
| `scripts/verificar_esquema_de_pista.py` | coletor | 2026-10-13 03:07 | 3 s | — | ok | — |
| `seguir_pistas.py` | coletor | 2026-10-13 09:13 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `triar_confianca_pistas.py` | coletor | 2026-10-13 09:13 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `verificar_links.py` | coletor | 2026-10-12 07:33 | 163 s | — | **erro** (3 seguidas) | erro: HTTPSConnectionPool(host='www.defesacivil.sc.gov.br', port=443): Max retries exceeded with url: /2026/08/14/chuva- |
| `verificar_pista_imprensa.py` | coletor | 2026-10-13 09:13 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
