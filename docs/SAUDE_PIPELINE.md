# Saúde do pipeline

Gerado por `scripts/gerar_saude_pipeline.py` a partir de `data/saude_pipeline.json`, que os
jobs escrevem com `scripts/saude_pipeline.py --rodar`. Item 2 do handover de desacoplamento
(27/09/2026). **Arquivo derivado: não se edita à mão.**

Duas classes, e a diferença importa. **Essencial** (`recalcular_mare.py`, `gerar_*.py`): se
erra, o site publica um estado que não corresponde ao dado — reprova o portão. **Coletor**:
fonte fora do ar é rotina, e uma falha isolada não é defeito do pipeline; erro em duas
rodadas seguidas vira alerta, porque aí não é a fonte, é o coletor.

Janela: 2026-10-25 a 2026-11-01 (1083 execução(ões) registrada(s), 7 dias de histórico).

## Alertas

- coletar_sih.py: erro em 6 rodadas seguidas — SIH: nenhum arquivo lido (0 na fila, 0 falha(s)); os arquivos anteriores ficam
- monitorar_busca_web.py: erro em 4 rodadas seguidas — ✗ busca web: 100% sem resposta do motor, acima do teto de 25% — esta rodada NÃO conta como verificação da camada 4
- verificar_links.py: erro em 2 rodadas seguidas — erro: HTTPSConnectionPool(host='www.defesacivil.sc.gov.br', port=443): Max retries exceeded with url: /2026/08/14/chuva-forte-deixa-danos-em-municipios-de-santa-catarina-e-risco-de-temporais-segue-alto-ate-sabado/ (Caused by ConnectTimeoutError(<HTTPSConnection(host='www.defesacivil.sc.gov.br', port

## Cobertura em 15 dias

cobertura 15d: 5080/5571 com verificação real até 2026-10-31 · por canal: web 1174 · QD 527 · consorciado 1720 · DOE 4677

## Última execução de cada script

| script | papel | última execução | duração | itens | status | erro |
|---|---|---|---|---:|---|---|
| `gerar_mortalidade_comparada.py` | essencial | 2026-10-30 01:28 | 1 s | — | ok | — |
| `gerar_saude_municipio.py` | essencial | 2026-10-31 01:43 | 1 s | — | ok | — |
| `recalcular_mare.py` | essencial | 2026-11-01 03:30 | 3 s | — | ok | — |
| `aplicar_promocoes_do_juiz.py` | coletor | 2026-10-31 08:53 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `atualizar.py` | coletor | 2026-10-25 08:45 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `atualizar_populacao.py` | coletor | 2026-10-25 08:23 | 1 s | — | ok | — |
| `buscar_planos_fontes_abertas.py` | coletor | 2026-10-28 23:21 | 718 s | — | ok | — |
| `buscar_protocolo_calor.py` | coletor | 2026-10-31 01:21 | 18 s | 4 | ok | — |
| `classificar_planos_municipais.py` | coletor | 2026-10-31 01:20 | 1 s | — | ok | — |
| `classificar_saude_no_plano.py` | coletor | 2026-10-31 01:43 | 3 s | — | ok | — |
| `coletar_arboviroses_sinan.py` | coletor | 2026-10-31 01:41 | 62 s | — | ok | — |
| `coletar_boletim_df_arboviroses.py` | coletor | 2026-10-31 01:31 | 385 s | — | ok | — |
| `coletar_boletim_ms_dengue.py` | coletor | 2026-10-31 01:31 | 21 s | — | ok | — |
| `coletar_boletim_pb_arboviroses.py` | coletor | 2026-10-31 01:38 | 197 s | — | ok | — |
| `coletar_boletim_pe_arboviroses.py` | coletor | 2026-10-31 01:38 | 7 s | — | ok | — |
| `coletar_cadastro_prioritarios.py` | coletor | 2026-10-31 01:13 | 34 s | — | ok | — |
| `coletar_cobertura_qd.py` | coletor | 2026-11-01 01:20 | 7495 s | — | **erro** | interrompido pelo prazo do elo |
| `coletar_datasus_dbc.py` | coletor | 2026-10-30 01:14 | 39 s | — | ok | — |
| `coletar_dda.py` | coletor | 2026-10-31 01:30 | 57 s | — | ok | — |
| `coletar_desfechos_saude.py` | coletor | 2026-10-31 01:22 | 471 s | — | ok | — |
| `coletar_diarios_consorciados.py` | coletor | 2026-10-31 01:23 | 6436 s | 60 | ok | — |
| `coletar_diarios_municipais.py` | coletor | 2026-10-30 01:23 | 2 s | 0 | ok | — |
| `coletar_doe.py` | coletor | 2026-10-31 03:11 | 2632 s | — | ok | — |
| `coletar_edicoes_doe.py` | coletor | 2026-10-30 17:16 | 326 s | — | ok | — |
| `coletar_espin.py` | coletor | 2026-10-31 01:13 | 480 s | — | ok | — |
| `coletar_normais_inmet.py` | coletor | 2026-10-31 01:14 | 4 s | — | ok | — |
| `coletar_obitos.py` | coletor | 2026-10-30 01:17 | 19 s | — | ok | — |
| `coletar_obitos_registro_civil.py` | coletor | 2026-10-31 01:42 | 28 s | — | ok | — |
| `coletar_planos_arboviroses.py` | coletor | 2026-10-30 01:28 | 1355 s | — | ok | — |
| `coletar_prioritarios_mma.py` | coletor | 2026-10-31 01:14 | 4 s | — | ok | — |
| `coletar_recursos_resposta.py` | coletor | 2026-10-31 04:11 | 33 s | — | ok | — |
| `coletar_s2id.py` | coletor | 2026-10-31 03:54 | 1021 s | — | ok | — |
| `coletar_saude.py` | coletor | 2026-10-31 01:13 | 99 s | — | ok | — |
| `coletar_saude_estadual.py` | coletor | 2026-10-27 02:25 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `coletar_semiarido_sudene.py` | coletor | 2026-10-31 01:14 | 3 s | — | ok | — |
| `coletar_sg_esus.py` | coletor | 2026-10-30 02:10 | 9 s | — | ok | — |
| `coletar_sih.py` | coletor | 2026-10-30 01:28 | 4 s | — | **erro** (6 seguidas) | SIH: nenhum arquivo lido (0 na fila, 0 falha(s)); os arquivos anteriores ficam |
| `coletar_sim.py` | coletor | 2026-10-30 01:18 | 627 s | — | ok | — |
| `coletar_sinais_risco.py` | coletor | 2026-10-31 01:13 | 94 s | — | ok | — |
| `coletar_sisab.py` | coletor | 2026-10-30 01:15 | 154 s | — | ok | — |
| `coletar_srag_gripe.py` | coletor | 2026-10-31 01:15 | 282 s | — | ok | — |
| `coletar_srag_sivep.py` | coletor | 2026-10-30 02:09 | 32 s | — | ok | — |
| `coletar_transferencias_municipais.py` | coletor | 2026-10-31 01:14 | 36 s | — | ok | — |
| `consultar_querido_diario.py` | coletor | 2026-10-30 01:15 | 519 s | 30 | ok | — |
| `descobrir_dominios.py` | coletor | 2026-11-01 03:25 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `descobrir_planos.py` | coletor | 2026-10-31 08:49 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `desfechos_sus.py` | coletor | 2026-10-30 01:17 | 1 s | — | ok | — |
| `detectar_marcos_federais.py` | coletor | 2026-10-31 08:49 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `julgar_e_aplicar_descobertas.py` | coletor | 2026-10-31 07:44 | 903 s | — | ok | — |
| `julgar_filas.py` | coletor | 2026-10-31 08:53 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `julgar_saude.py` | coletor | 2026-10-27 01:13 | 4321 s | — | **erro** | interrompido pelo prazo do elo |
| `ler_planos_arboviroses.py` | coletor | 2026-10-30 01:51 | 4 s | — | ok | — |
| `monitorar_atos_resposta.py` | coletor | 2026-10-31 08:49 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `monitorar_busca_web.py` | coletor | 2026-10-31 01:34 | 315 s | 2 | **erro** (4 seguidas) | ✗ busca web: 100% sem resposta do motor, acima do teto de 25% — esta rodada NÃO conta como verificação da camada 4 |
| `monitorar_imprensa_regional.py` | coletor | 2026-10-31 08:49 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `monitorar_imprensa_saude.py` | coletor | 2026-10-31 08:49 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `monitorar_politica_por_inteiro.py` | coletor | 2026-10-31 08:49 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `monitorar_redes_oficiais.py` | coletor | 2026-10-26 07:34 | 1012 s | — | ok | — |
| `monitorar_sinais_federais.py` | coletor | 2026-10-31 08:49 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `preservar_evidencias.py` | coletor | 2026-10-31 08:58 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `processar_contribuicoes.py` | coletor | 2026-10-25 08:23 | 1 s | — | ok | — |
| `python3` | coletor | 2026-10-31 21:20 | 4049 s | — | ok | — |
| `revisar_pistas.py` | coletor | 2026-10-31 06:23 | 392 s | — | ok | — |
| `scripts/amostra_auditoria_semanal.py` | coletor | 2026-10-31 07:59 | 1 s | — | ok | — |
| `scripts/corrigir_atribuicao_por_dominio.py` | coletor | 2026-10-31 06:22 | 78 s | — | ok | — |
| `scripts/fechar_saude.py` | coletor | 2026-10-27 02:25 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/preservar_textos_integrais.py` | coletor | 2026-10-31 08:58 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/reavaliar_fontes_suspensas.py` | coletor | 2026-10-31 01:21 | 686 s | — | ok | — |
| `scripts/rejulgar_decisoes_do_juiz.py` | coletor | 2026-10-30 06:06 | 3455 s | — | ok | — |
| `scripts/sondar_boletim_infogripe.py` | coletor | 2026-10-31 01:14 | 90 s | — | ok | — |
| `scripts/sondar_rotas_doe.py` | coletor | 2026-10-28 21:49 | 92 s | — | ok | — |
| `scripts/triar_fila.py` | coletor | 2026-10-31 08:53 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/verificar_esquema_de_pista.py` | coletor | 2026-10-31 08:53 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/verificar_funil.py` | coletor | 2026-10-25 08:35 | 0 s | — | ok | — |
| `seguir_pistas.py` | coletor | 2026-10-31 08:49 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `triar_confianca_pistas.py` | coletor | 2026-10-31 08:49 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `verificar_links.py` | coletor | 2026-10-31 01:33 | 194 s | — | **erro** (2 seguidas) | erro: HTTPSConnectionPool(host='www.defesacivil.sc.gov.br', port=443): Max retries exceeded with url: /2026/08/14/chuva- |
| `verificar_pista_imprensa.py` | coletor | 2026-10-31 08:49 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
