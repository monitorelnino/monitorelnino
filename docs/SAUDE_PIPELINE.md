# Saúde do pipeline

Gerado por `scripts/gerar_saude_pipeline.py` a partir de `data/saude_pipeline.json`, que os
jobs escrevem com `scripts/saude_pipeline.py --rodar`. Item 2 do handover de desacoplamento
(27/09/2026). **Arquivo derivado: não se edita à mão.**

Duas classes, e a diferença importa. **Essencial** (`recalcular_mare.py`, `gerar_*.py`): se
erra, o site publica um estado que não corresponde ao dado — reprova o portão. **Coletor**:
fonte fora do ar é rotina, e uma falha isolada não é defeito do pipeline; erro em duas
rodadas seguidas vira alerta, porque aí não é a fonte, é o coletor.

Janela: 2026-10-08 a 2026-10-15 (993 execução(ões) registrada(s), 7 dias de histórico).

## Alertas

- descobrir_dominios.py: erro em 2 rodadas seguidas — interrompido pelo prazo do elo
- monitorar_busca_web.py: erro em 4 rodadas seguidas — ✗ busca web: 100% sem resposta do motor, acima do teto de 25% — esta rodada NÃO conta como verificação da camada 4
- verificar_links.py: erro em 3 rodadas seguidas — erro: HTTPSConnectionPool(host='www.defesacivil.sc.gov.br', port=443): Max retries exceeded with url: /2026/08/14/chuva-forte-deixa-danos-em-municipios-de-santa-catarina-e-risco-de-temporais-segue-alto-ate-sabado/ (Caused by ConnectTimeoutError(<HTTPSConnection(host='www.defesacivil.sc.gov.br', port

## Cobertura em 15 dias

cobertura 15d: 1452/5571 com verificação real até 2026-10-15 · por canal: web 433 · QD 1 · consorciado 0 · DOE 1021

## Última execução de cada script

| script | papel | última execução | duração | itens | status | erro |
|---|---|---|---|---:|---|---|
| `recalcular_mare.py` | essencial | 2026-10-15 13:53 | 3 s | — | ok | — |
| `aplicar_promocoes_do_juiz.py` | coletor | 2026-10-15 09:09 | 0 s | — | ok | — |
| `buscar_protocolo_calor.py` | coletor | 2026-10-12 07:33 | 11 s | 3 | ok | — |
| `classificar_planos_municipais.py` | coletor | 2026-10-13 06:56 | 1 s | — | ok | — |
| `classificar_saude_no_plano.py` | coletor | 2026-10-14 01:35 | 1 s | — | ok | — |
| `coletar_arboviroses_sinan.py` | coletor | 2026-10-14 01:34 | 53 s | — | ok | — |
| `coletar_boletim_df_arboviroses.py` | coletor | 2026-10-14 01:29 | 292 s | — | ok | — |
| `coletar_boletim_ms_dengue.py` | coletor | 2026-10-14 01:28 | 16 s | — | ok | — |
| `coletar_boletim_pb_arboviroses.py` | coletor | 2026-10-14 01:34 | 4 s | — | ok | — |
| `coletar_boletim_pe_arboviroses.py` | coletor | 2026-10-14 01:34 | 9 s | — | ok | — |
| `coletar_cadastro_prioritarios.py` | coletor | 2026-10-13 06:52 | 31 s | — | ok | — |
| `coletar_cobertura_qd.py` | coletor | 2026-10-13 06:56 | 2134 s | — | ok | — |
| `coletar_dda.py` | coletor | 2026-10-14 01:27 | 56 s | — | ok | — |
| `coletar_desfechos_saude.py` | coletor | 2026-10-14 01:21 | 409 s | — | ok | — |
| `coletar_diarios_consorciados.py` | coletor | 2026-10-15 02:48 | 3324 s | 40 | ok | — |
| `coletar_diarios_municipais.py` | coletor | 2026-10-14 01:28 | 4768 s | 250 | ok | — |
| `coletar_doe.py` | coletor | 2026-10-15 03:43 | 1126 s | — | ok | — |
| `coletar_edicoes_doe.py` | coletor | 2026-10-14 04:07 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `coletar_espin.py` | coletor | 2026-10-12 07:31 | 97 s | — | ok | — |
| `coletar_execucao_mps.py` | coletor | 2026-10-12 07:51 | 16 s | — | ok | — |
| `coletar_normais_inmet.py` | coletor | 2026-10-13 06:52 | 4 s | — | ok | — |
| `coletar_obitos_registro_civil.py` | coletor | 2026-10-14 01:35 | 34 s | — | ok | — |
| `coletar_prioritarios_mma.py` | coletor | 2026-10-13 06:52 | 4 s | — | ok | — |
| `coletar_recursos_resposta.py` | coletor | 2026-10-15 04:21 | 30 s | — | ok | — |
| `coletar_s2id.py` | coletor | 2026-10-15 04:02 | 1155 s | — | ok | — |
| `coletar_saude.py` | coletor | 2026-10-14 01:13 | 67 s | — | ok | — |
| `coletar_saude_estadual.py` | coletor | 2026-10-14 04:07 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `coletar_semiarido_sudene.py` | coletor | 2026-10-13 06:52 | 3 s | — | ok | — |
| `coletar_sg_esus.py` | coletor | 2026-10-11 03:37 | 8 s | — | ok | — |
| `coletar_siconfi_182.py` | coletor | 2026-10-12 07:51 | 1 s | 5571 | ok | — |
| `coletar_sinais_risco.py` | coletor | 2026-10-14 01:11 | 98 s | — | ok | — |
| `coletar_srag_gripe.py` | coletor | 2026-10-13 06:54 | 144 s | — | ok | — |
| `coletar_srag_sivep.py` | coletor | 2026-10-11 03:36 | 34 s | — | ok | — |
| `coletar_transferegov.py` | coletor | 2026-10-12 07:50 | 36 s | — | ok | — |
| `coletar_transferencias_municipais.py` | coletor | 2026-10-14 01:13 | 69 s | — | ok | — |
| `consultar_querido_diario.py` | coletor | 2026-10-14 01:12 | 952 s | 27 | ok | — |
| `descobrir_dominios.py` | coletor | 2026-10-13 08:05 | 3546 s | — | **erro** (2 seguidas) | interrompido pelo prazo do elo |
| `descobrir_planos.py` | coletor | 2026-10-15 07:20 | 487 s | 42 | ok | — |
| `detectar_marcos_federais.py` | coletor | 2026-10-15 07:20 | 2 s | 0 | ok | — |
| `julgar_e_aplicar_descobertas.py` | coletor | 2026-10-15 09:01 | 471 s | — | ok | — |
| `julgar_filas.py` | coletor | 2026-10-15 09:00 | 75 s | — | ok | — |
| `julgar_saude.py` | coletor | 2026-10-14 04:07 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `monitorar_atos_resposta.py` | coletor | 2026-10-15 07:18 | 101 s | 5136 | ok | — |
| `monitorar_busca_web.py` | coletor | 2026-10-15 06:27 | 315 s | 2 | **erro** (4 seguidas) | ✗ busca web: 100% sem resposta do motor, acima do teto de 25% — esta rodada NÃO conta como verificação da camada 4 |
| `monitorar_imprensa_regional.py` | coletor | 2026-10-15 07:13 | 196 s | 40 | ok | — |
| `monitorar_imprensa_saude.py` | coletor | 2026-10-15 07:16 | 104 s | 27 | ok | — |
| `monitorar_politica_por_inteiro.py` | coletor | 2026-10-15 07:20 | 4 s | 5136 | ok | — |
| `monitorar_redes_oficiais.py` | coletor | 2026-10-15 07:28 | 1199 s | — | ok | — |
| `monitorar_sinais_federais.py` | coletor | 2026-10-15 07:20 | 4 s | 10 | ok | — |
| `motores_busca.py` | coletor | 2026-10-13 09:39 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `preservar_evidencias.py` | coletor | 2026-10-15 07:19 | 46 s | — | ok | — |
| `revisar_pistas.py` | coletor | 2026-10-15 08:42 | 1087 s | — | ok | — |
| `scripts/amostra_auditoria_semanal.py` | coletor | 2026-10-15 09:09 | 1 s | — | ok | — |
| `scripts/corrigir_atribuicao_por_dominio.py` | coletor | 2026-10-15 08:41 | 19 s | — | ok | — |
| `scripts/fechar_saude.py` | coletor | 2026-10-14 04:07 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/preservar_textos_integrais.py` | coletor | 2026-10-15 07:20 | 1 s | — | ok | — |
| `scripts/sondar_boletim_infogripe.py` | coletor | 2026-10-13 06:52 | 86 s | — | ok | — |
| `scripts/triar_fila.py` | coletor | 2026-10-15 04:25 | 2 s | — | ok | — |
| `scripts/verificar_esquema_de_pista.py` | coletor | 2026-10-15 05:02 | 4 s | — | ok | — |
| `seguir_pistas.py` | coletor | 2026-10-15 07:48 | 60 s | — | ok | — |
| `triar_confianca_pistas.py` | coletor | 2026-10-15 07:49 | 4 s | — | ok | — |
| `verificar_links.py` | coletor | 2026-10-12 07:33 | 163 s | — | **erro** (3 seguidas) | erro: HTTPSConnectionPool(host='www.defesacivil.sc.gov.br', port=443): Max retries exceeded with url: /2026/08/14/chuva- |
| `verificar_pista_imprensa.py` | coletor | 2026-10-15 07:49 | 166 s | — | ok | — |
