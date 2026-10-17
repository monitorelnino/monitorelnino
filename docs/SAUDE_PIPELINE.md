# Saúde do pipeline

Gerado por `scripts/gerar_saude_pipeline.py` a partir de `data/saude_pipeline.json`, que os
jobs escrevem com `scripts/saude_pipeline.py --rodar`. Item 2 do handover de desacoplamento
(27/09/2026). **Arquivo derivado: não se edita à mão.**

Duas classes, e a diferença importa. **Essencial** (`recalcular_mare.py`, `gerar_*.py`): se
erra, o site publica um estado que não corresponde ao dado — reprova o portão. **Coletor**:
fonte fora do ar é rotina, e uma falha isolada não é defeito do pipeline; erro em duas
rodadas seguidas vira alerta, porque aí não é a fonte, é o coletor.

Janela: 2026-10-10 a 2026-10-17 (1047 execução(ões) registrada(s), 7 dias de histórico).

## Alertas

- descobrir_dominios.py: erro em 2 rodadas seguidas — interrompido pelo prazo do elo
- verificar_links.py: erro em 3 rodadas seguidas — erro: HTTPSConnectionPool(host='www.defesacivil.sc.gov.br', port=443): Max retries exceeded with url: /2026/08/14/chuva-forte-deixa-danos-em-municipios-de-santa-catarina-e-risco-de-temporais-segue-alto-ate-sabado/ (Caused by ConnectTimeoutError(<HTTPSConnection(host='www.defesacivil.sc.gov.br', port

## Cobertura em 15 dias

cobertura 15d: 4038/5571 com verificação real até 2026-10-17 · por canal: web 581 · QD 527 · consorciado 1612 · DOE 2320

## Última execução de cada script

| script | papel | última execução | duração | itens | status | erro |
|---|---|---|---|---:|---|---|
| `gerar_saude_municipio.py` | essencial | 2026-10-16 01:36 | 1 s | — | ok | — |
| `recalcular_mare.py` | essencial | 2026-10-17 07:47 | 3 s | — | ok | — |
| `aplicar_promocoes_do_juiz.py` | coletor | 2026-10-17 05:59 | 1 s | — | ok | — |
| `buscar_protocolo_calor.py` | coletor | 2026-10-12 07:33 | 11 s | 3 | ok | — |
| `classificar_planos_municipais.py` | coletor | 2026-10-13 06:56 | 1 s | — | ok | — |
| `classificar_saude_no_plano.py` | coletor | 2026-10-16 01:36 | 0 s | — | ok | — |
| `coletar_arboviroses_sinan.py` | coletor | 2026-10-16 01:34 | 61 s | — | ok | — |
| `coletar_boletim_df_arboviroses.py` | coletor | 2026-10-16 01:27 | 413 s | — | ok | — |
| `coletar_boletim_ms_dengue.py` | coletor | 2026-10-16 01:27 | 18 s | — | ok | — |
| `coletar_boletim_pb_arboviroses.py` | coletor | 2026-10-16 01:34 | 4 s | — | ok | — |
| `coletar_boletim_pe_arboviroses.py` | coletor | 2026-10-16 01:34 | 8 s | — | ok | — |
| `coletar_cadastro_prioritarios.py` | coletor | 2026-10-13 06:52 | 31 s | — | ok | — |
| `coletar_cobertura_qd.py` | coletor | 2026-10-13 06:56 | 2134 s | — | ok | — |
| `coletar_dda.py` | coletor | 2026-10-16 01:26 | 56 s | — | ok | — |
| `coletar_desfechos_saude.py` | coletor | 2026-10-16 01:19 | 387 s | — | ok | — |
| `coletar_diarios_consorciados.py` | coletor | 2026-10-16 01:29 | 2956 s | 47 | ok | — |
| `coletar_diarios_municipais.py` | coletor | 2026-10-16 01:28 | 16 s | 1 | ok | — |
| `coletar_doe.py` | coletor | 2026-10-17 02:18 | 2538 s | — | ok | — |
| `coletar_edicoes_doe.py` | coletor | 2026-10-16 21:53 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `coletar_espin.py` | coletor | 2026-10-12 07:31 | 97 s | — | ok | — |
| `coletar_execucao_mps.py` | coletor | 2026-10-12 07:51 | 16 s | — | ok | — |
| `coletar_normais_inmet.py` | coletor | 2026-10-13 06:52 | 4 s | — | ok | — |
| `coletar_obitos_registro_civil.py` | coletor | 2026-10-16 01:35 | 42 s | — | ok | — |
| `coletar_prioritarios_mma.py` | coletor | 2026-10-13 06:52 | 4 s | — | ok | — |
| `coletar_recursos_resposta.py` | coletor | 2026-10-17 03:18 | 15 s | — | ok | — |
| `coletar_s2id.py` | coletor | 2026-10-17 03:00 | 1084 s | — | ok | — |
| `coletar_saude.py` | coletor | 2026-10-16 01:12 | 76 s | — | ok | — |
| `coletar_saude_estadual.py` | coletor | 2026-10-16 21:53 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `coletar_semiarido_sudene.py` | coletor | 2026-10-13 06:52 | 3 s | — | ok | — |
| `coletar_sg_esus.py` | coletor | 2026-10-11 03:37 | 8 s | — | ok | — |
| `coletar_siconfi_182.py` | coletor | 2026-10-12 07:51 | 1 s | 5571 | ok | — |
| `coletar_sinais_risco.py` | coletor | 2026-10-16 01:12 | 193 s | — | ok | — |
| `coletar_srag_gripe.py` | coletor | 2026-10-13 06:54 | 144 s | — | ok | — |
| `coletar_srag_sivep.py` | coletor | 2026-10-11 03:36 | 34 s | — | ok | — |
| `coletar_transferegov.py` | coletor | 2026-10-12 07:50 | 36 s | — | ok | — |
| `coletar_transferencias_municipais.py` | coletor | 2026-10-16 01:15 | 51 s | — | ok | — |
| `consultar_querido_diario.py` | coletor | 2026-10-16 01:13 | 936 s | 22 | ok | — |
| `descobrir_dominios.py` | coletor | 2026-10-13 08:05 | 3546 s | — | **erro** (2 seguidas) | interrompido pelo prazo do elo |
| `descobrir_planos.py` | coletor | 2026-10-17 06:55 | 392 s | — | ok | — |
| `detectar_marcos_federais.py` | coletor | 2026-10-17 06:55 | 1 s | 0 | ok | — |
| `julgar_e_aplicar_descobertas.py` | coletor | 2026-10-17 05:49 | 629 s | — | ok | — |
| `julgar_filas.py` | coletor | 2026-10-17 05:13 | 2124 s | — | ok | — |
| `julgar_saude.py` | coletor | 2026-10-16 20:40 | 3583 s | — | ok | — |
| `monitorar_atos_resposta.py` | coletor | 2026-10-17 06:53 | 116 s | 6660 | ok | — |
| `monitorar_busca_web.py` | coletor | 2026-10-17 05:44 | 2 s | 0 | ok | — |
| `monitorar_imprensa_regional.py` | coletor | 2026-10-17 06:50 | 102 s | 40 | ok | — |
| `monitorar_imprensa_saude.py` | coletor | 2026-10-17 06:52 | 102 s | 27 | ok | — |
| `monitorar_politica_por_inteiro.py` | coletor | 2026-10-17 06:55 | 5 s | 6660 | ok | — |
| `monitorar_redes_oficiais.py` | coletor | 2026-10-17 07:02 | 1231 s | — | ok | — |
| `monitorar_sinais_federais.py` | coletor | 2026-10-17 06:55 | 4 s | 10 | ok | — |
| `motores_busca.py` | coletor | 2026-10-13 09:39 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `preservar_evidencias.py` | coletor | 2026-10-17 07:36 | 1 s | — | ok | — |
| `revisar_pistas.py` | coletor | 2026-10-17 04:53 | 1236 s | — | ok | — |
| `scripts/amostra_auditoria_semanal.py` | coletor | 2026-10-17 05:59 | 1 s | — | ok | — |
| `scripts/corrigir_atribuicao_por_dominio.py` | coletor | 2026-10-17 04:52 | 23 s | — | ok | — |
| `scripts/fechar_saude.py` | coletor | 2026-10-16 21:53 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/preservar_textos_integrais.py` | coletor | 2026-10-17 07:36 | 2 s | — | ok | — |
| `scripts/sondar_boletim_infogripe.py` | coletor | 2026-10-13 06:52 | 86 s | — | ok | — |
| `scripts/triar_fila.py` | coletor | 2026-10-17 03:22 | 2 s | — | ok | — |
| `scripts/verificar_esquema_de_pista.py` | coletor | 2026-10-17 03:47 | 7 s | — | ok | — |
| `seguir_pistas.py` | coletor | 2026-10-17 07:22 | 48 s | — | ok | — |
| `triar_confianca_pistas.py` | coletor | 2026-10-17 07:23 | 5 s | — | ok | — |
| `verificar_links.py` | coletor | 2026-10-12 07:33 | 163 s | — | **erro** (3 seguidas) | erro: HTTPSConnectionPool(host='www.defesacivil.sc.gov.br', port=443): Max retries exceeded with url: /2026/08/14/chuva- |
| `verificar_pista_imprensa.py` | coletor | 2026-10-17 07:23 | 191 s | — | ok | — |
