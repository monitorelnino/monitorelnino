# Saúde do pipeline

Gerado por `scripts/gerar_saude_pipeline.py` a partir de `data/saude_pipeline.json`, que os
jobs escrevem com `scripts/saude_pipeline.py --rodar`. Item 2 do handover de desacoplamento
(27/09/2026). **Arquivo derivado: não se edita à mão.**

Duas classes, e a diferença importa. **Essencial** (`recalcular_mare.py`, `gerar_*.py`): se
erra, o site publica um estado que não corresponde ao dado — reprova o portão. **Coletor**:
fonte fora do ar é rotina, e uma falha isolada não é defeito do pipeline; erro em duas
rodadas seguidas vira alerta, porque aí não é a fonte, é o coletor.

Janela: 2026-10-29 a 2026-11-05 (1429 execução(ões) registrada(s), 7 dias de histórico).

## Alertas

- coletar_sih.py: erro em 7 rodadas seguidas — SIH: nenhum arquivo lido (0 na fila, 0 falha(s)); os arquivos anteriores ficam
- consultar_querido_diario.py: erro em 3 rodadas seguidas — portas tentadas: api.queridodiario.org.br: HTTPError HTTP Error 520: <none> | queridodiario.ok.org.br: HTTPError HTTP Error 520: <none> | api.queridodiario.ok.org.br: URLError <urlopen error [SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] sslv3 alert handshake failur
- julgar_filas.py: erro em 3 rodadas seguidas — interrompido pelo prazo do elo
- verificar_links.py: erro em 2 rodadas seguidas — erro: HTTPSConnectionPool(host='www.defesacivil.sc.gov.br', port=443): Max retries exceeded with url: /2026/08/14/chuva-forte-deixa-danos-em-municipios-de-santa-catarina-e-risco-de-temporais-segue-alto-ate-sabado/ (Caused by ConnectTimeoutError(<HTTPSConnection(host='www.defesacivil.sc.gov.br', port

## Cobertura em 15 dias

cobertura 15d: 4983/5571 com verificação real até 2026-11-05 · por canal: web 355 · QD 527 · consorciado 1653 · DOE 4677

## Última execução de cada script

| script | papel | última execução | duração | itens | status | erro |
|---|---|---|---|---:|---|---|
| `gerar_monitor_saude.py` | essencial | 2026-11-01 21:57 | 1 s | — | ok | — |
| `gerar_mortalidade_comparada.py` | essencial | 2026-11-05 07:20 | 0 s | — | ok | — |
| `gerar_saude_municipio.py` | essencial | 2026-11-04 01:37 | 1 s | — | ok | — |
| `recalcular_mare.py` | essencial | 2026-11-05 16:47 | 4 s | — | ok | — |
| `aplicar_promocoes_do_juiz.py` | coletor | 2026-11-05 08:45 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `atualizar.py` | coletor | 2026-10-31 01:55 | 103 s | — | ok | — |
| `atualizar_populacao.py` | coletor | 2026-10-31 01:14 | 1 s | — | ok | — |
| `buscar_planos_fontes_abertas.py` | coletor | 2026-11-02 21:10 | 80 s | — | ok | — |
| `buscar_protocolo_calor.py` | coletor | 2026-11-03 01:17 | 114 s | — | ok | — |
| `classificar_planos_municipais.py` | coletor | 2026-10-31 01:20 | 1 s | — | ok | — |
| `classificar_saude_no_plano.py` | coletor | 2026-11-04 01:37 | 0 s | — | ok | — |
| `coletar_arboviroses_sinan.py` | coletor | 2026-11-04 01:35 | 42 s | — | ok | — |
| `coletar_boletim_df_arboviroses.py` | coletor | 2026-11-04 01:31 | 277 s | — | ok | — |
| `coletar_boletim_ms_dengue.py` | coletor | 2026-11-04 01:30 | 14 s | — | ok | — |
| `coletar_boletim_pb_arboviroses.py` | coletor | 2026-11-04 01:35 | 3 s | — | ok | — |
| `coletar_boletim_pe_arboviroses.py` | coletor | 2026-11-04 01:35 | 7 s | — | ok | — |
| `coletar_cadastro_prioritarios.py` | coletor | 2026-10-31 01:13 | 34 s | — | ok | — |
| `coletar_cobertura_qd.py` | coletor | 2026-11-01 01:20 | 7495 s | — | **erro** | interrompido pelo prazo do elo |
| `coletar_datasus_dbc.py` | coletor | 2026-11-05 07:17 | 41 s | — | ok | — |
| `coletar_dda.py` | coletor | 2026-11-04 01:29 | 55 s | — | ok | — |
| `coletar_desfechos_saude.py` | coletor | 2026-11-04 01:23 | 401 s | — | ok | — |
| `coletar_diarios_consorciados.py` | coletor | 2026-11-04 01:24 | 3435 s | 32 | ok | — |
| `coletar_diarios_municipais.py` | coletor | 2026-11-04 01:24 | 3 s | 0 | ok | — |
| `coletar_doe.py` | coletor | 2026-11-05 02:21 | 3478 s | — | ok | — |
| `coletar_edicoes_doe.py` | coletor | 2026-11-04 01:44 | 6096 s | — | **erro** | interrompido pelo prazo do elo |
| `coletar_espin.py` | coletor | 2026-11-04 03:26 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `coletar_normais_inmet.py` | coletor | 2026-10-31 01:14 | 4 s | — | ok | — |
| `coletar_obitos.py` | coletor | 2026-11-05 07:20 | 4 s | — | ok | — |
| `coletar_obitos_registro_civil.py` | coletor | 2026-11-04 01:36 | 41 s | — | ok | — |
| `coletar_planos_arboviroses.py` | coletor | 2026-11-05 07:20 | 1515 s | — | ok | — |
| `coletar_prioritarios_mma.py` | coletor | 2026-10-31 01:14 | 4 s | — | ok | — |
| `coletar_projecao_cil.py` | coletor | 2026-11-05 07:20 | 2 s | — | ok | — |
| `coletar_recursos_resposta.py` | coletor | 2026-11-05 03:35 | 25 s | — | ok | — |
| `coletar_s2id.py` | coletor | 2026-11-05 03:19 | 925 s | — | ok | — |
| `coletar_saude.py` | coletor | 2026-11-04 01:15 | 69 s | — | ok | — |
| `coletar_saude_estadual.py` | coletor | 2026-11-03 02:26 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `coletar_semiarido_sudene.py` | coletor | 2026-10-31 01:14 | 3 s | — | ok | — |
| `coletar_sg_esus.py` | coletor | 2026-11-05 03:43 | 12 s | — | ok | — |
| `coletar_sih.py` | coletor | 2026-11-05 07:20 | 5 s | — | **erro** (7 seguidas) | SIH: nenhum arquivo lido (0 na fila, 0 falha(s)); os arquivos anteriores ficam |
| `coletar_sim.py` | coletor | 2026-11-05 07:20 | 9 s | — | **erro** | SIM: nenhum arquivo lido (0 na fila, 0 falha(s)); os arquivos anteriores ficam |
| `coletar_sinais_risco.py` | coletor | 2026-11-05 08:50 | 98 s | — | ok | — |
| `coletar_sisab.py` | coletor | 2026-11-05 07:17 | 142 s | — | ok | — |
| `coletar_srag_gripe.py` | coletor | 2026-10-31 01:15 | 282 s | — | ok | — |
| `coletar_srag_sivep.py` | coletor | 2026-11-05 03:42 | 44 s | — | ok | — |
| `coletar_transferencias_municipais.py` | coletor | 2026-11-05 08:52 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `consultar_querido_diario.py` | coletor | 2026-11-04 01:17 | 428 s | — | **erro** (3 seguidas) | portas tentadas: api.queridodiario.org.br: HTTPError HTTP Error 520: <none> \| queridodiario.ok.org.br: HTTPError HTTP E |
| `descobrir_dominios.py` | coletor | 2026-11-01 03:25 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `descobrir_planos.py` | coletor | 2026-11-05 08:57 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `desfechos_sus.py` | coletor | 2026-11-05 07:20 | 1 s | — | ok | — |
| `detectar_marcos_federais.py` | coletor | 2026-11-05 08:57 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `julgar_e_aplicar_descobertas.py` | coletor | 2026-11-05 08:45 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `julgar_filas.py` | coletor | 2026-11-05 08:26 | 1132 s | — | **erro** (3 seguidas) | interrompido pelo prazo do elo |
| `julgar_saude.py` | coletor | 2026-11-03 01:15 | 4291 s | — | **erro** | interrompido pelo prazo do elo |
| `ler_planos_arboviroses.py` | coletor | 2026-11-05 07:45 | 3 s | — | ok | — |
| `monitorar_atos_resposta.py` | coletor | 2026-11-05 08:57 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `monitorar_busca_web.py` | coletor | 2026-11-05 08:57 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `monitorar_imprensa_regional.py` | coletor | 2026-11-05 08:57 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `monitorar_imprensa_saude.py` | coletor | 2026-11-05 08:57 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `monitorar_politica_por_inteiro.py` | coletor | 2026-11-05 08:57 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `monitorar_sinais_federais.py` | coletor | 2026-11-05 08:57 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `preservar_evidencias.py` | coletor | 2026-11-05 06:19 | 2 s | — | ok | — |
| `processar_contribuicoes.py` | coletor | 2026-10-31 01:14 | 2 s | — | ok | — |
| `python3` | coletor | 2026-11-05 14:32 | 3604 s | — | **erro** | interrompido pelo prazo do elo |
| `reconferir_instrumentos_federais.py` | coletor | 2026-11-05 07:45 | 3 s | — | ok | — |
| `revisar_pistas.py` | coletor | 2026-11-05 08:17 | 496 s | — | ok | — |
| `scripts/amostra_auditoria_semanal.py` | coletor | 2026-11-05 08:45 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/corrigir_atribuicao_por_dominio.py` | coletor | 2026-11-05 08:16 | 75 s | — | ok | — |
| `scripts/fechar_saude.py` | coletor | 2026-11-03 02:26 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/preservar_textos_integrais.py` | coletor | 2026-11-05 06:19 | 3 s | — | ok | — |
| `scripts/proveniencia_estadual.py` | coletor | 2026-11-04 03:26 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/reavaliar_fontes_suspensas.py` | coletor | 2026-11-05 05:12 | 1041 s | — | ok | — |
| `scripts/rejulgar_decisoes_do_juiz.py` | coletor | 2026-10-30 06:06 | 3455 s | — | ok | — |
| `scripts/sondar_boletim_infogripe.py` | coletor | 2026-10-31 01:14 | 90 s | — | ok | — |
| `scripts/sondar_credenciais.py` | coletor | 2026-11-05 08:52 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/triar_fila.py` | coletor | 2026-11-05 03:49 | 1 s | — | ok | — |
| `scripts/verificar_esquema_de_pista.py` | coletor | 2026-11-05 04:02 | 2 s | — | ok | — |
| `scripts/verificar_funil.py` | coletor | 2026-10-31 01:20 | 1 s | — | **erro** | ✗ FUNIL: a contagem da rodada se contradiz ou a etapa não funcionou: |
| `seguir_pistas.py` | coletor | 2026-11-05 08:57 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `triar_confianca_pistas.py` | coletor | 2026-11-05 08:57 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `verificar_links.py` | coletor | 2026-11-03 01:36 | 232 s | — | **erro** (2 seguidas) | erro: HTTPSConnectionPool(host='www.defesacivil.sc.gov.br', port=443): Max retries exceeded with url: /2026/08/14/chuva- |
| `verificar_pista_imprensa.py` | coletor | 2026-11-05 08:57 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
