# Saúde do pipeline

Gerado por `scripts/gerar_saude_pipeline.py` a partir de `data/saude_pipeline.json`, que os
jobs escrevem com `scripts/saude_pipeline.py --rodar`. Item 2 do handover de desacoplamento
(27/09/2026). **Arquivo derivado: não se edita à mão.**

Duas classes, e a diferença importa. **Essencial** (`recalcular_mare.py`, `gerar_*.py`): se
erra, o site publica um estado que não corresponde ao dado — reprova o portão. **Coletor**:
fonte fora do ar é rotina, e uma falha isolada não é defeito do pipeline; erro em duas
rodadas seguidas vira alerta, porque aí não é a fonte, é o coletor.

Janela: 2026-10-04 a 2026-10-11 (633 execução(ões) registrada(s), 7 dias de histórico).

## Alertas

- monitorar_imprensa_saude.py: erro em 15 rodadas seguidas — KeyError: 'hash'
- monitorar_politica_por_inteiro.py: erro em 12 rodadas seguidas — NameError: name 'ler' is not defined. Did you mean: 'len'?

## Última execução de cada script

| script | papel | última execução | duração | itens | status | erro |
|---|---|---|---|---:|---|---|
| `recalcular_mare.py` | essencial | 2026-10-11 08:01 | 4 s | — | ok | — |
| `aplicar_promocoes_do_juiz.py` | coletor | 2026-10-11 07:08 | 30 s | 1 | ok | — |
| `coletar_diarios_consorciados.py` | coletor | 2026-10-10 01:44 | 3148 s | 34 | ok | — |
| `coletar_diarios_municipais.py` | coletor | 2026-10-10 01:36 | 425 s | 50 | ok | — |
| `coletar_doe.py` | coletor | 2026-10-10 02:36 | 846 s | — | ok | — |
| `coletar_espin.py` | coletor | 2026-10-10 01:12 | 92 s | — | ok | — |
| `coletar_recursos_resposta.py` | coletor | 2026-10-11 03:07 | 9 s | — | ok | — |
| `coletar_s2id.py` | coletor | 2026-10-11 02:50 | 1030 s | — | ok | — |
| `coletar_sg_esus.py` | coletor | 2026-10-11 03:37 | 8 s | — | ok | — |
| `coletar_sinais_risco.py` | coletor | 2026-10-10 01:12 | 69 s | — | ok | — |
| `coletar_srag_sivep.py` | coletor | 2026-10-11 03:36 | 34 s | — | ok | — |
| `consultar_querido_diario.py` | coletor | 2026-10-10 01:13 | 32 s | — | **erro** | urllib.error.URLError: <urlopen error [SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] sslv3 alert handshake failure (_ssl.c:1010)> |
| `descobrir_planos.py` | coletor | 2026-10-11 07:20 | 884 s | 42 | ok | — |
| `detectar_marcos_federais.py` | coletor | 2026-10-11 07:20 | 1 s | 0 | ok | — |
| `julgar_e_aplicar_descobertas.py` | coletor | 2026-10-11 06:58 | 632 s | — | ok | — |
| `julgar_filas.py` | coletor | 2026-10-11 06:42 | 935 s | — | ok | — |
| `monitorar_atos_resposta.py` | coletor | 2026-10-11 07:17 | 166 s | 3442 | ok | — |
| `monitorar_imprensa_regional.py` | coletor | 2026-10-11 07:15 | 125 s | 40 | ok | — |
| `monitorar_imprensa_saude.py` | coletor | 2026-10-11 07:17 | 1 s | — | **erro** (15 seguidas) | KeyError: 'hash' |
| `monitorar_politica_por_inteiro.py` | coletor | 2026-10-11 07:20 | 2 s | 3442 | **erro** (12 seguidas) | NameError: name 'ler' is not defined. Did you mean: 'len'? |
| `monitorar_redes_oficiais.py` | coletor | 2026-10-11 07:35 | 1254 s | — | ok | — |
| `monitorar_sinais_federais.py` | coletor | 2026-10-11 07:20 | 4 s | 10 | ok | — |
| `preservar_evidencias.py` | coletor | 2026-10-11 06:11 | 1501 s | — | ok | — |
| `revisar_pistas.py` | coletor | 2026-10-11 06:42 | 1 s | — | ok | — |
| `scripts/amostra_auditoria_semanal.py` | coletor | 2026-10-11 07:09 | 0 s | — | ok | — |
| `scripts/corrigir_atribuicao_por_dominio.py` | coletor | 2026-10-11 06:42 | 7 s | — | ok | — |
| `scripts/preservar_textos_integrais.py` | coletor | 2026-10-11 06:36 | 1 s | — | ok | — |
| `scripts/triar_fila.py` | coletor | 2026-10-11 03:41 | 2 s | — | ok | — |
| `scripts/verificar_esquema_de_pista.py` | coletor | 2026-10-11 04:01 | 3 s | — | ok | — |
| `seguir_pistas.py` | coletor | 2026-10-11 07:56 | 37 s | — | ok | — |
| `triar_confianca_pistas.py` | coletor | 2026-10-11 07:56 | 3 s | — | ok | — |
| `verificar_links.py` | coletor | 2026-10-10 01:14 | 208 s | — | **erro** | erro: HTTPSConnectionPool(host='www.defesacivil.sc.gov.br', port=443): Max retries exceeded with url: /2026/08/14/chuva- |
| `verificar_pista_imprensa.py` | coletor | 2026-10-11 07:56 | 81 s | — | ok | — |
