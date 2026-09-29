# Saúde do pipeline

Gerado por `scripts/gerar_saude_pipeline.py` a partir de `data/saude_pipeline.json`, que os
jobs escrevem com `scripts/saude_pipeline.py --rodar`. Item 2 do handover de desacoplamento
(27/09/2026). **Arquivo derivado: não se edita à mão.**

Duas classes, e a diferença importa. **Essencial** (`recalcular_mare.py`, `gerar_*.py`): se
erra, o site publica um estado que não corresponde ao dado — reprova o portão. **Coletor**:
fonte fora do ar é rotina, e uma falha isolada não é defeito do pipeline; erro em duas
rodadas seguidas vira alerta, porque aí não é a fonte, é o coletor.

Janela: 2026-09-28 a 2026-09-29 (23 execução(ões) registrada(s), 7 dias de histórico).

Nenhum script essencial com erro e nenhum coletor errando duas rodadas seguidas.

## Última execução de cada script

| script | papel | última execução | duração | itens | status | erro |
|---|---|---|---|---:|---|---|
| `recalcular_mare.py` | essencial | 2026-09-29 06:48 | 3 s | — | ok | — |
| `aplicar_promocoes_do_juiz.py` | coletor | 2026-09-28 23:16 | 0 s | — | ok | — |
| `descobrir_planos.py` | coletor | 2026-09-28 09:03 | 881 s | 41 | ok | — |
| `detectar_marcos_federais.py` | coletor | 2026-09-28 09:03 | 2 s | 0 | ok | — |
| `julgar_e_aplicar_descobertas.py` | coletor | 2026-09-28 23:16 | 0 s | — | ok | — |
| `julgar_filas.py` | coletor | 2026-09-28 22:57 | 1165 s | — | ok | — |
| `monitorar_atos_resposta.py` | coletor | 2026-09-28 08:58 | 318 s | 1161 | ok | — |
| `monitorar_imprensa_regional.py` | coletor | 2026-09-28 08:54 | 124 s | 40 | ok | — |
| `monitorar_imprensa_saude.py` | coletor | 2026-09-28 08:56 | 103 s | 27 | ok | — |
| `monitorar_politica_por_inteiro.py` | coletor | 2026-09-28 09:03 | 2 s | 1161 | ok | — |
| `monitorar_sinais_federais.py` | coletor | 2026-09-28 09:03 | 4 s | 10 | ok | — |
| `revisar_pistas.py` | coletor | 2026-09-28 22:52 | 276 s | — | ok | — |
| `scripts/amostra_auditoria_semanal.py` | coletor | 2026-09-28 23:16 | 0 s | — | ok | — |
| `seguir_pistas.py` | coletor | 2026-09-28 09:18 | 19 s | — | ok | — |
| `triar_confianca_pistas.py` | coletor | 2026-09-28 09:18 | 2 s | — | ok | — |
| `verificar_prazos_legais.py` | coletor | 2026-09-28 09:03 | 1 s | — | ok | — |
