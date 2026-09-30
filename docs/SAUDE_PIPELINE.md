# Saúde do pipeline

Gerado por `scripts/gerar_saude_pipeline.py` a partir de `data/saude_pipeline.json`, que os
jobs escrevem com `scripts/saude_pipeline.py --rodar`. Item 2 do handover de desacoplamento
(27/09/2026). **Arquivo derivado: não se edita à mão.**

Duas classes, e a diferença importa. **Essencial** (`recalcular_mare.py`, `gerar_*.py`): se
erra, o site publica um estado que não corresponde ao dado — reprova o portão. **Coletor**:
fonte fora do ar é rotina, e uma falha isolada não é defeito do pipeline; erro em duas
rodadas seguidas vira alerta, porque aí não é a fonte, é o coletor.

Janela: 2026-09-28 a 2026-09-30 (74 execução(ões) registrada(s), 7 dias de histórico).

## Alertas

- monitorar_redes_oficiais.py: erro em 2 rodadas seguidas — AttributeError: 'list' object has no attribute 'get'

## Última execução de cada script

| script | papel | última execução | duração | itens | status | erro |
|---|---|---|---|---:|---|---|
| `recalcular_mare.py` | essencial | 2026-09-30 15:48 | 3 s | — | ok | — |
| `aplicar_promocoes_do_juiz.py` | coletor | 2026-09-30 11:56 | 0 s | — | ok | — |
| `coletar_diarios_consorciados.py` | coletor | 2026-09-29 07:39 | 1987 s | 2 | ok | — |
| `coletar_diarios_municipais.py` | coletor | 2026-09-29 07:09 | 1809 s | 140 | ok | — |
| `coletar_doe.py` | coletor | 2026-09-29 08:13 | 61 s | — | ok | — |
| `coletar_s2id.py` | coletor | 2026-09-29 08:14 | 746 s | — | ok | — |
| `coletar_sinais_risco.py` | coletor | 2026-09-30 14:27 | 62 s | — | ok | — |
| `consultar_querido_diario.py` | coletor | 2026-09-29 07:09 | 1 s | — | **erro** | urllib.error.URLError: <urlopen error [SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] sslv3 alert handshake failure (_ssl.c:1010)> |
| `descobrir_planos.py` | coletor | 2026-09-30 09:11 | 910 s | 41 | ok | — |
| `detectar_marcos_federais.py` | coletor | 2026-09-30 09:11 | 2 s | 0 | ok | — |
| `julgar_e_aplicar_descobertas.py` | coletor | 2026-09-30 11:56 | 1 s | — | ok | — |
| `julgar_filas.py` | coletor | 2026-09-30 11:35 | 1266 s | — | ok | — |
| `monitorar_atos_resposta.py` | coletor | 2026-09-30 09:00 | 679 s | 1285 | ok | — |
| `monitorar_imprensa_regional.py` | coletor | 2026-09-30 08:55 | 176 s | 40 | ok | — |
| `monitorar_imprensa_saude.py` | coletor | 2026-09-30 08:58 | 103 s | 27 | ok | — |
| `monitorar_politica_por_inteiro.py` | coletor | 2026-09-30 09:11 | 1 s | 1285 | ok | — |
| `monitorar_redes_oficiais.py` | coletor | 2026-09-30 09:27 | 0 s | — | **erro** (2 seguidas) | AttributeError: 'list' object has no attribute 'get' |
| `monitorar_sinais_federais.py` | coletor | 2026-09-30 09:11 | 4 s | 10 | ok | — |
| `preservar_evidencias.py` | coletor | 2026-09-29 11:37 | 0 s | — | ok | — |
| `revisar_pistas.py` | coletor | 2026-09-30 11:29 | 409 s | — | ok | — |
| `scripts/amostra_auditoria_semanal.py` | coletor | 2026-09-30 11:56 | 0 s | — | ok | — |
| `scripts/preservar_textos_integrais.py` | coletor | 2026-09-29 11:37 | 114 s | — | ok | — |
| `seguir_pistas.py` | coletor | 2026-09-30 09:27 | 306 s | — | ok | — |
| `triar_confianca_pistas.py` | coletor | 2026-09-30 09:32 | 2 s | — | ok | — |
| `verificar_pista_imprensa.py` | coletor | 2026-09-30 09:32 | 238 s | — | ok | — |
| `verificar_prazos_legais.py` | coletor | 2026-09-29 09:16 | 0 s | — | ok | — |
