# Saúde do pipeline

Gerado por `scripts/gerar_saude_pipeline.py` a partir de `data/saude_pipeline.json`, que os
jobs escrevem com `scripts/saude_pipeline.py --rodar`. Item 2 do handover de desacoplamento
(27/09/2026). **Arquivo derivado: não se edita à mão.**

Duas classes, e a diferença importa. **Essencial** (`recalcular_mare.py`, `gerar_*.py`): se
erra, o site publica um estado que não corresponde ao dado — reprova o portão. **Coletor**:
fonte fora do ar é rotina, e uma falha isolada não é defeito do pipeline; erro em duas
rodadas seguidas vira alerta, porque aí não é a fonte, é o coletor.

Janela: 2026-10-12 a 2026-10-19 (1220 execução(ões) registrada(s), 7 dias de histórico).

## Alertas

- consultar_querido_diario.py: erro em 2 rodadas seguidas — urllib.error.URLError: <urlopen error [SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] sslv3 alert handshake failure (_ssl.c:1010)>
- descobrir_dominios.py: erro em 4 rodadas seguidas — interrompido pelo prazo do elo
- julgar_filas.py: erro em 2 rodadas seguidas — interrompido pelo prazo do elo
- monitorar_busca_web.py: erro em 4 rodadas seguidas — ✗ busca web: 100% sem resposta do motor, acima do teto de 25% — esta rodada NÃO conta como verificação da camada 4
- verificar_links.py: erro em 4 rodadas seguidas — erro: HTTPSConnectionPool(host='www.defesacivil.sc.gov.br', port=443): Max retries exceeded with url: /2026/08/14/chuva-forte-deixa-danos-em-municipios-de-santa-catarina-e-risco-de-temporais-segue-alto-ate-sabado/ (Caused by ConnectTimeoutError(<HTTPSConnection(host='www.defesacivil.sc.gov.br', port

## Cobertura em 15 dias

cobertura 15d: 4578/5571 com verificação real até 2026-10-19 · por canal: web 1067 · QD 527 · consorciado 1612 · DOE 2732

## Última execução de cada script

| script | papel | última execução | duração | itens | status | erro |
|---|---|---|---|---:|---|---|
| `gerar_monitor_saude.py` | essencial | 2026-10-18 08:41 | 1 s | — | ok | — |
| `gerar_saude_municipio.py` | essencial | 2026-10-18 02:10 | 1 s | — | ok | — |
| `recalcular_mare.py` | essencial | 2026-10-19 16:32 | 3 s | — | ok | — |
| `aplicar_promocoes_do_juiz.py` | coletor | 2026-10-19 08:45 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `atualizar.py` | coletor | 2026-10-18 08:39 | 87 s | — | ok | — |
| `atualizar_populacao.py` | coletor | 2026-10-18 08:00 | 1 s | — | ok | — |
| `buscar_protocolo_calor.py` | coletor | 2026-10-17 01:58 | 13 s | 3 | ok | — |
| `classificar_planos_municipais.py` | coletor | 2026-10-18 03:56 | 1 s | — | ok | — |
| `classificar_saude_no_plano.py` | coletor | 2026-10-18 02:10 | 0 s | — | ok | — |
| `coletar_arboviroses_sinan.py` | coletor | 2026-10-18 02:08 | 60 s | — | ok | — |
| `coletar_boletim_df_arboviroses.py` | coletor | 2026-10-18 02:02 | 344 s | — | ok | — |
| `coletar_boletim_ms_dengue.py` | coletor | 2026-10-18 02:02 | 29 s | — | ok | — |
| `coletar_boletim_pb_arboviroses.py` | coletor | 2026-10-18 02:08 | 3 s | — | ok | — |
| `coletar_boletim_pe_arboviroses.py` | coletor | 2026-10-18 02:08 | 8 s | — | ok | — |
| `coletar_cadastro_prioritarios.py` | coletor | 2026-10-18 03:51 | 34 s | — | ok | — |
| `coletar_cobertura_qd.py` | coletor | 2026-10-18 03:56 | 6883 s | — | ok | — |
| `coletar_dda.py` | coletor | 2026-10-18 02:01 | 57 s | — | ok | — |
| `coletar_desfechos_saude.py` | coletor | 2026-10-18 01:53 | 468 s | — | ok | — |
| `coletar_diarios_consorciados.py` | coletor | 2026-10-18 01:45 | 2040 s | 38 | ok | — |
| `coletar_diarios_municipais.py` | coletor | 2026-10-18 01:45 | 4 s | 0 | ok | — |
| `coletar_doe.py` | coletor | 2026-10-18 02:19 | 1678 s | — | ok | — |
| `coletar_edicoes_doe.py` | coletor | 2026-10-19 12:18 | 1322 s | — | ok | — |
| `coletar_espin.py` | coletor | 2026-10-17 01:56 | 124 s | — | ok | — |
| `coletar_execucao_mps.py` | coletor | 2026-10-12 07:51 | 16 s | — | ok | — |
| `coletar_normais_inmet.py` | coletor | 2026-10-18 03:52 | 4 s | — | ok | — |
| `coletar_obitos_registro_civil.py` | coletor | 2026-10-18 02:09 | 19 s | — | ok | — |
| `coletar_prioritarios_mma.py` | coletor | 2026-10-18 03:52 | 4 s | — | ok | — |
| `coletar_recursos_resposta.py` | coletor | 2026-10-19 03:04 | 24 s | — | ok | — |
| `coletar_s2id.py` | coletor | 2026-10-19 02:47 | 1017 s | — | ok | — |
| `coletar_saude.py` | coletor | 2026-10-18 01:44 | 80 s | — | ok | — |
| `coletar_saude_estadual.py` | coletor | 2026-10-16 21:53 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `coletar_semiarido_sudene.py` | coletor | 2026-10-18 03:52 | 3 s | — | ok | — |
| `coletar_sg_esus.py` | coletor | 2026-10-18 03:26 | 10 s | — | ok | — |
| `coletar_siconfi_182.py` | coletor | 2026-10-12 07:51 | 1 s | 5571 | ok | — |
| `coletar_sinais_risco.py` | coletor | 2026-10-19 08:49 | 108 s | — | ok | — |
| `coletar_srag_gripe.py` | coletor | 2026-10-18 03:53 | 146 s | — | ok | — |
| `coletar_srag_sivep.py` | coletor | 2026-10-18 03:25 | 39 s | — | ok | — |
| `coletar_transferegov.py` | coletor | 2026-10-12 07:50 | 36 s | — | ok | — |
| `coletar_transferencias_municipais.py` | coletor | 2026-10-19 08:50 | 42 s | — | ok | — |
| `consultar_querido_diario.py` | coletor | 2026-10-18 01:45 | 40 s | — | **erro** (2 seguidas) | urllib.error.URLError: <urlopen error [SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] sslv3 alert handshake failure (_ssl.c:1010)> |
| `descobrir_dominios.py` | coletor | 2026-10-18 05:50 | 823 s | — | **erro** (4 seguidas) | interrompido pelo prazo do elo |
| `descobrir_planos.py` | coletor | 2026-10-19 08:49 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `detectar_marcos_federais.py` | coletor | 2026-10-19 08:49 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `julgar_e_aplicar_descobertas.py` | coletor | 2026-10-19 08:38 | 417 s | — | **erro** | interrompido pelo prazo do elo |
| `julgar_filas.py` | coletor | 2026-10-19 07:22 | 4504 s | — | **erro** (2 seguidas) | interrompido pelo prazo do elo |
| `julgar_saude.py` | coletor | 2026-10-16 20:40 | 3583 s | — | ok | — |
| `monitorar_atos_resposta.py` | coletor | 2026-10-19 08:49 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `monitorar_busca_web.py` | coletor | 2026-10-19 06:50 | 317 s | 2 | **erro** (4 seguidas) | ✗ busca web: 100% sem resposta do motor, acima do teto de 25% — esta rodada NÃO conta como verificação da camada 4 |
| `monitorar_imprensa_regional.py` | coletor | 2026-10-19 08:49 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `monitorar_imprensa_saude.py` | coletor | 2026-10-19 08:49 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `monitorar_politica_por_inteiro.py` | coletor | 2026-10-19 08:49 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `monitorar_redes_oficiais.py` | coletor | 2026-10-19 08:49 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `monitorar_sinais_federais.py` | coletor | 2026-10-19 08:49 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `motores_busca.py` | coletor | 2026-10-13 09:39 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `preservar_evidencias.py` | coletor | 2026-10-19 08:52 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `processar_contribuicoes.py` | coletor | 2026-10-18 08:00 | 1 s | — | ok | — |
| `revisar_pistas.py` | coletor | 2026-10-19 07:12 | 658 s | — | ok | — |
| `scripts/amostra_auditoria_semanal.py` | coletor | 2026-10-19 08:45 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/corrigir_atribuicao_por_dominio.py` | coletor | 2026-10-19 07:10 | 63 s | — | ok | — |
| `scripts/fechar_saude.py` | coletor | 2026-10-16 21:53 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/preservar_textos_integrais.py` | coletor | 2026-10-19 08:52 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/reavaliar_fontes_suspensas.py` | coletor | 2026-10-17 01:58 | 659 s | — | ok | — |
| `scripts/sondar_boletim_infogripe.py` | coletor | 2026-10-18 03:52 | 84 s | — | ok | — |
| `scripts/triar_fila.py` | coletor | 2026-10-19 03:09 | 3 s | — | ok | — |
| `scripts/verificar_esquema_de_pista.py` | coletor | 2026-10-19 03:42 | 22 s | — | ok | — |
| `scripts/verificar_funil.py` | coletor | 2026-10-18 08:12 | 1 s | — | ok | — |
| `seguir_pistas.py` | coletor | 2026-10-19 08:49 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `triar_confianca_pistas.py` | coletor | 2026-10-19 08:49 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `verificar_links.py` | coletor | 2026-10-17 02:09 | 296 s | — | **erro** (4 seguidas) | erro: HTTPSConnectionPool(host='www.defesacivil.sc.gov.br', port=443): Max retries exceeded with url: /2026/08/14/chuva- |
| `verificar_pista_imprensa.py` | coletor | 2026-10-19 08:49 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
