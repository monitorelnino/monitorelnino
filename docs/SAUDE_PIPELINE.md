# Saúde do pipeline

Gerado por `scripts/gerar_saude_pipeline.py` a partir de `data/saude_pipeline.json`, que os
jobs escrevem com `scripts/saude_pipeline.py --rodar`. Item 2 do handover de desacoplamento
(27/09/2026). **Arquivo derivado: não se edita à mão.**

Duas classes, e a diferença importa. **Essencial** (`recalcular_mare.py`, `gerar_*.py`): se
erra, o site publica um estado que não corresponde ao dado — reprova o portão. **Coletor**:
fonte fora do ar é rotina, e uma falha isolada não é defeito do pipeline; erro em duas
rodadas seguidas vira alerta, porque aí não é a fonte, é o coletor.

Janela: 2026-09-28 a 2026-10-04 (183 execução(ões) registrada(s), 7 dias de histórico).

## Alertas

- consultar_querido_diario.py: erro em 5 rodadas seguidas — urllib.error.URLError: <urlopen error [SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] sslv3 alert handshake failure (_ssl.c:1010)>

## Última execução de cada script

| script | papel | última execução | duração | itens | status | erro |
|---|---|---|---|---:|---|---|
| `recalcular_mare.py` | essencial | 2026-10-04 09:18 | 3 s | — | ok | — |
| `aplicar_promocoes_do_juiz.py` | coletor | 2026-10-01 21:35 | 1 s | — | ok | — |
| `coletar_diarios_consorciados.py` | coletor | 2026-10-04 03:56 | 3037 s | 0 | ok | — |
| `coletar_diarios_municipais.py` | coletor | 2026-10-04 03:43 | 822 s | 49 | ok | — |
| `coletar_doe.py` | coletor | 2026-10-04 04:47 | 837 s | — | ok | — |
| `coletar_recursos_resposta.py` | coletor | 2026-10-04 05:13 | 97 s | — | ok | — |
| `coletar_s2id.py` | coletor | 2026-10-04 05:01 | 749 s | — | ok | — |
| `coletar_saude_estadual.py` | coletor | 2026-10-02 10:25 | 829 s | — | ok | — |
| `coletar_sg_esus.py` | coletor | 2026-10-01 02:18 | 9 s | — | ok | — |
| `coletar_sinais_risco.py` | coletor | 2026-10-03 12:55 | 62 s | — | ok | — |
| `coletar_srag_sivep.py` | coletor | 2026-10-01 02:13 | 294 s | — | ok | — |
| `consultar_querido_diario.py` | coletor | 2026-10-03 02:41 | 62 s | — | **erro** (5 seguidas) | urllib.error.URLError: <urlopen error [SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] sslv3 alert handshake failure (_ssl.c:1010)> |
| `descobrir_planos.py` | coletor | 2026-10-03 09:05 | 915 s | — | ok | — |
| `detectar_marcos_federais.py` | coletor | 2026-10-03 09:05 | 2 s | 0 | ok | — |
| `julgar_e_aplicar_descobertas.py` | coletor | 2026-10-01 21:35 | 1 s | — | ok | — |
| `julgar_filas.py` | coletor | 2026-10-01 20:24 | 4289 s | — | ok | — |
| `julgar_saude.py` | coletor | 2026-10-02 10:39 | 2 s | — | ok | — |
| `monitorar_atos_resposta.py` | coletor | 2026-10-03 08:58 | 388 s | 1821 | ok | — |
| `monitorar_imprensa_regional.py` | coletor | 2026-10-03 08:54 | 240 s | 40 | ok | — |
| `monitorar_imprensa_saude.py` | coletor | 2026-10-03 08:58 | 1 s | — | **erro** | KeyError: 'hash' |
| `monitorar_politica_por_inteiro.py` | coletor | 2026-10-03 09:05 | 2 s | 1821 | ok | — |
| `monitorar_redes_oficiais.py` | coletor | 2026-10-03 09:20 | 1311 s | — | ok | — |
| `monitorar_sinais_federais.py` | coletor | 2026-10-03 09:05 | 4 s | 10 | ok | — |
| `preservar_evidencias.py` | coletor | 2026-10-04 06:18 | 45 s | — | ok | — |
| `revisar_pistas.py` | coletor | 2026-10-01 20:20 | 261 s | — | ok | — |
| `scripts/amostra_auditoria_semanal.py` | coletor | 2026-10-01 21:35 | 0 s | — | ok | — |
| `scripts/fechar_saude.py` | coletor | 2026-10-02 10:39 | 1 s | — | ok | — |
| `scripts/preservar_textos_integrais.py` | coletor | 2026-10-04 06:18 | 1 s | — | ok | — |
| `seguir_pistas.py` | coletor | 2026-10-03 09:42 | 20 s | — | ok | — |
| `triar_confianca_pistas.py` | coletor | 2026-10-03 09:42 | 2 s | — | ok | — |
| `verificar_pista_imprensa.py` | coletor | 2026-10-03 09:42 | 237 s | — | ok | — |
| `verificar_prazos_legais.py` | coletor | 2026-09-29 09:16 | 0 s | — | ok | — |
