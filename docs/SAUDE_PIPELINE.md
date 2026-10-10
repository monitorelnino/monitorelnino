# Saúde do pipeline

Gerado por `scripts/gerar_saude_pipeline.py` a partir de `data/saude_pipeline.json`, que os
jobs escrevem com `scripts/saude_pipeline.py --rodar`. Item 2 do handover de desacoplamento
(27/09/2026). **Arquivo derivado: não se edita à mão.**

Duas classes, e a diferença importa. **Essencial** (`recalcular_mare.py`, `gerar_*.py`): se
erra, o site publica um estado que não corresponde ao dado — reprova o portão. **Coletor**:
fonte fora do ar é rotina, e uma falha isolada não é defeito do pipeline; erro em duas
rodadas seguidas vira alerta, porque aí não é a fonte, é o coletor.

Janela: 2026-10-03 a 2026-10-10 (586 execução(ões) registrada(s), 7 dias de histórico).

## Alertas

- monitorar_imprensa_saude.py: erro em 14 rodadas seguidas — KeyError: 'hash'
- monitorar_politica_por_inteiro.py: erro em 10 rodadas seguidas — NameError: name 'ler' is not defined. Did you mean: 'len'?

## Última execução de cada script

| script | papel | última execução | duração | itens | status | erro |
|---|---|---|---|---:|---|---|
| `recalcular_mare.py` | essencial | 2026-10-10 14:01 | 4 s | — | ok | — |
| `aplicar_promocoes_do_juiz.py` | coletor | 2026-10-09 02:31 | 1 s | — | ok | — |
| `coletar_diarios_consorciados.py` | coletor | 2026-10-10 07:28 | 4019 s | 38 | ok | — |
| `coletar_diarios_municipais.py` | coletor | 2026-10-10 07:27 | 47 s | 50 | ok | — |
| `coletar_doe.py` | coletor | 2026-10-10 08:35 | 847 s | — | ok | — |
| `coletar_recursos_resposta.py` | coletor | 2026-10-10 09:07 | 158 s | — | ok | — |
| `coletar_s2id.py` | coletor | 2026-10-10 08:49 | 1105 s | — | ok | — |
| `coletar_sg_esus.py` | coletor | 2026-10-04 14:20 | 9 s | — | ok | — |
| `coletar_sinais_risco.py` | coletor | 2026-10-09 01:11 | 106 s | — | ok | — |
| `coletar_srag_sivep.py` | coletor | 2026-10-04 14:19 | 40 s | — | ok | — |
| `consultar_querido_diario.py` | coletor | 2026-10-10 07:01 | 1283 s | 12 | ok | — |
| `descobrir_planos.py` | coletor | 2026-10-09 08:27 | 1059 s | 42 | ok | — |
| `detectar_marcos_federais.py` | coletor | 2026-10-09 08:27 | 2 s | 0 | ok | — |
| `julgar_e_aplicar_descobertas.py` | coletor | 2026-10-09 02:21 | 627 s | — | ok | — |
| `julgar_filas.py` | coletor | 2026-10-09 01:48 | 1963 s | — | ok | — |
| `monitorar_atos_resposta.py` | coletor | 2026-10-09 08:24 | 124 s | 3416 | ok | — |
| `monitorar_imprensa_regional.py` | coletor | 2026-10-09 08:22 | 164 s | 40 | ok | — |
| `monitorar_imprensa_saude.py` | coletor | 2026-10-09 08:24 | 1 s | — | **erro** (14 seguidas) | KeyError: 'hash' |
| `monitorar_politica_por_inteiro.py` | coletor | 2026-10-09 08:26 | 13 s | 3416 | **erro** (10 seguidas) | NameError: name 'ler' is not defined. Did you mean: 'len'? |
| `monitorar_redes_oficiais.py` | coletor | 2026-10-09 08:44 | 1287 s | — | ok | — |
| `monitorar_sinais_federais.py` | coletor | 2026-10-09 08:27 | 4 s | 10 | ok | — |
| `preservar_evidencias.py` | coletor | 2026-10-08 08:58 | 1 s | — | ok | — |
| `revisar_pistas.py` | coletor | 2026-10-09 01:38 | 600 s | — | ok | — |
| `scripts/amostra_auditoria_semanal.py` | coletor | 2026-10-09 02:31 | 0 s | — | ok | — |
| `scripts/corrigir_atribuicao_por_dominio.py` | coletor | 2026-10-09 01:38 | 11 s | — | ok | — |
| `scripts/preservar_textos_integrais.py` | coletor | 2026-10-08 08:58 | 1 s | — | ok | — |
| `scripts/triar_fila.py` | coletor | 2026-10-09 01:11 | 2 s | — | ok | — |
| `scripts/verificar_esquema_de_pista.py` | coletor | 2026-10-09 01:34 | 3 s | — | ok | — |
| `seguir_pistas.py` | coletor | 2026-10-09 09:06 | 23 s | — | ok | — |
| `triar_confianca_pistas.py` | coletor | 2026-10-09 09:06 | 3 s | — | ok | — |
| `verificar_pista_imprensa.py` | coletor | 2026-10-09 09:06 | 59 s | — | ok | — |
