# Saúde do pipeline

Gerado por `scripts/gerar_saude_pipeline.py` a partir de `data/saude_pipeline.json`, que os
jobs escrevem com `scripts/saude_pipeline.py --rodar`. Item 2 do handover de desacoplamento
(27/09/2026). **Arquivo derivado: não se edita à mão.**

Duas classes, e a diferença importa. **Essencial** (`recalcular_mare.py`, `gerar_*.py`): se
erra, o site publica um estado que não corresponde ao dado — reprova o portão. **Coletor**:
fonte fora do ar é rotina, e uma falha isolada não é defeito do pipeline; erro em duas
rodadas seguidas vira alerta, porque aí não é a fonte, é o coletor.

Janela: 2026-10-30 a 2026-11-06 (1389 execução(ões) registrada(s), 7 dias de histórico).

## Alertas

- coletar_sih.py: erro em 7 rodadas seguidas — SIH: nenhum arquivo lido (0 na fila, 0 falha(s)); os arquivos anteriores ficam
- coletar_sim.py: erro em 2 rodadas seguidas — SIM: nenhum arquivo lido (0 na fila, 0 falha(s)); os arquivos anteriores ficam
- consultar_querido_diario.py: erro em 4 rodadas seguidas — portas tentadas: api.queridodiario.org.br: TimeoutError The read operation timed out | queridodiario.ok.org.br: HTTPError HTTP Error 520: <none> | api.queridodiario.ok.org.br: URLError <urlopen error [SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] sslv3 alert handshake failur
- julgar_filas.py: erro em 6 rodadas seguidas — interrompido pelo prazo do elo
- monitorar_busca_web.py: erro em 4 rodadas seguidas — ✗ busca web: 100% sem resposta do motor, acima do teto de 25% — esta rodada NÃO conta como verificação da camada 4
- verificar_links.py: erro em 2 rodadas seguidas — erro: HTTPSConnectionPool(host='www.defesacivil.sc.gov.br', port=443): Max retries exceeded with url: /2026/08/14/chuva-forte-deixa-danos-em-municipios-de-santa-catarina-e-risco-de-temporais-segue-alto-ate-sabado/ (Caused by ConnectTimeoutError(<HTTPSConnection(host='www.defesacivil.sc.gov.br', port

## Cobertura em 15 dias

cobertura 15d: 4985/5571 com verificação real até 2026-11-06 · por canal: web 298 · QD 527 · consorciado 1667 · DOE 4862

## Última execução de cada script

| script | papel | última execução | duração | itens | status | erro |
|---|---|---|---|---:|---|---|
| `gerar_monitor_saude.py` | essencial | 2026-11-01 21:57 | 1 s | — | ok | — |
| `gerar_mortalidade_comparada.py` | essencial | 2026-11-06 07:16 | 0 s | — | ok | — |
| `gerar_saude_municipio.py` | essencial | 2026-11-06 01:38 | 1 s | — | ok | — |
| `recalcular_mare.py` | essencial | 2026-11-06 01:55 | 4 s | — | ok | — |
| `aplicar_promocoes_do_juiz.py` | coletor | 2026-11-06 08:25 | 2 s | — | ok | — |
| `atualizar.py` | coletor | 2026-10-31 01:55 | 103 s | — | ok | — |
| `atualizar_populacao.py` | coletor | 2026-10-31 01:14 | 1 s | — | ok | — |
| `buscar_planos_fontes_abertas.py` | coletor | 2026-11-02 21:10 | 80 s | — | ok | — |
| `buscar_protocolo_calor.py` | coletor | 2026-11-03 01:17 | 114 s | — | ok | — |
| `classificar_planos_municipais.py` | coletor | 2026-10-31 01:20 | 1 s | — | ok | — |
| `classificar_saude_no_plano.py` | coletor | 2026-11-06 01:38 | 1 s | — | ok | — |
| `coletar_arboviroses_sinan.py` | coletor | 2026-11-06 01:36 | 59 s | — | ok | — |
| `coletar_boletim_df_arboviroses.py` | coletor | 2026-11-06 01:30 | 382 s | — | ok | — |
| `coletar_boletim_ms_dengue.py` | coletor | 2026-11-06 01:30 | 19 s | — | ok | — |
| `coletar_boletim_pb_arboviroses.py` | coletor | 2026-11-06 01:36 | 3 s | — | ok | — |
| `coletar_boletim_pe_arboviroses.py` | coletor | 2026-11-06 01:36 | 6 s | — | ok | — |
| `coletar_cadastro_prioritarios.py` | coletor | 2026-10-31 01:13 | 34 s | — | ok | — |
| `coletar_cobertura_qd.py` | coletor | 2026-11-01 01:20 | 7495 s | — | **erro** | interrompido pelo prazo do elo |
| `coletar_datasus_dbc.py` | coletor | 2026-11-06 07:13 | 43 s | — | ok | — |
| `coletar_dda.py` | coletor | 2026-11-06 01:29 | 55 s | — | ok | — |
| `coletar_desfechos_saude.py` | coletor | 2026-11-06 01:22 | 406 s | — | ok | — |
| `coletar_diarios_consorciados.py` | coletor | 2026-11-05 01:50 | 2868 s | 31 | ok | — |
| `coletar_diarios_municipais.py` | coletor | 2026-11-05 01:50 | 2 s | 0 | ok | — |
| `coletar_doe.py` | coletor | 2026-11-06 02:38 | 3263 s | — | ok | — |
| `coletar_edicoes_doe.py` | coletor | 2026-11-06 02:22 | 3032 s | — | ok | — |
| `coletar_espin.py` | coletor | 2026-11-06 18:24 | 372 s | — | ok | — |
| `coletar_normais_inmet.py` | coletor | 2026-10-31 01:14 | 4 s | — | ok | — |
| `coletar_obitos.py` | coletor | 2026-11-06 07:16 | 4 s | — | ok | — |
| `coletar_obitos_registro_civil.py` | coletor | 2026-11-06 01:37 | 54 s | — | ok | — |
| `coletar_planos_arboviroses.py` | coletor | 2026-11-06 07:16 | 811 s | — | ok | — |
| `coletar_prioritarios_mma.py` | coletor | 2026-10-31 01:14 | 4 s | — | ok | — |
| `coletar_projecao_cil.py` | coletor | 2026-11-06 07:16 | 2 s | — | ok | — |
| `coletar_recursos_resposta.py` | coletor | 2026-11-06 03:47 | 29 s | — | ok | — |
| `coletar_s2id.py` | coletor | 2026-11-06 03:32 | 896 s | — | ok | — |
| `coletar_saude.py` | coletor | 2026-11-06 01:14 | 83 s | — | ok | — |
| `coletar_saude_estadual.py` | coletor | 2026-11-03 02:26 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `coletar_semiarido_sudene.py` | coletor | 2026-10-31 01:14 | 3 s | — | ok | — |
| `coletar_sg_esus.py` | coletor | 2026-11-05 02:23 | 8 s | — | ok | — |
| `coletar_sih.py` | coletor | 2026-11-06 07:16 | 5 s | — | **erro** (7 seguidas) | SIH: nenhum arquivo lido (0 na fila, 0 falha(s)); os arquivos anteriores ficam |
| `coletar_sim.py` | coletor | 2026-11-06 07:16 | 8 s | — | **erro** (2 seguidas) | SIM: nenhum arquivo lido (0 na fila, 0 falha(s)); os arquivos anteriores ficam |
| `coletar_sinais_risco.py` | coletor | 2026-11-06 01:14 | 102 s | — | ok | — |
| `coletar_sisab.py` | coletor | 2026-11-06 07:14 | 122 s | — | ok | — |
| `coletar_srag_gripe.py` | coletor | 2026-10-31 01:15 | 282 s | — | ok | — |
| `coletar_srag_sivep.py` | coletor | 2026-11-05 02:22 | 35 s | — | ok | — |
| `coletar_transferencias_municipais.py` | coletor | 2026-11-06 01:16 | 41 s | — | ok | — |
| `consultar_querido_diario.py` | coletor | 2026-11-05 01:20 | 1824 s | — | **erro** (4 seguidas) | portas tentadas: api.queridodiario.org.br: TimeoutError The read operation timed out \| queridodiario.ok.org.br: HTTPErr |
| `descobrir_dominios.py` | coletor | 2026-11-01 03:25 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `descobrir_planos.py` | coletor | 2026-11-06 07:14 | 446 s | — | ok | — |
| `desfechos_sus.py` | coletor | 2026-11-06 07:16 | 0 s | — | ok | — |
| `detectar_marcos_federais.py` | coletor | 2026-11-06 07:13 | 32 s | — | ok | — |
| `julgar_e_aplicar_descobertas.py` | coletor | 2026-11-06 08:13 | 716 s | — | ok | — |
| `julgar_filas.py` | coletor | 2026-11-06 06:58 | 4502 s | — | **erro** (6 seguidas) | interrompido pelo prazo do elo |
| `julgar_saude.py` | coletor | 2026-11-03 01:15 | 4291 s | — | **erro** | interrompido pelo prazo do elo |
| `ler_planos_arboviroses.py` | coletor | 2026-11-06 07:30 | 4 s | — | ok | — |
| `monitorar_atos_resposta.py` | coletor | 2026-11-06 07:10 | 206 s | 17905 | ok | — |
| `monitorar_busca_web.py` | coletor | 2026-11-06 01:36 | 315 s | 2 | **erro** (4 seguidas) | ✗ busca web: 100% sem resposta do motor, acima do teto de 25% — esta rodada NÃO conta como verificação da camada 4 |
| `monitorar_imprensa_regional.py` | coletor | 2026-11-06 07:05 | 186 s | 40 | ok | — |
| `monitorar_imprensa_saude.py` | coletor | 2026-11-06 07:08 | 102 s | 27 | ok | — |
| `monitorar_politica_por_inteiro.py` | coletor | 2026-11-06 07:13 | 6 s | 17905 | ok | — |
| `monitorar_sinais_federais.py` | coletor | 2026-11-06 07:13 | 5 s | 10 | ok | — |
| `preservar_evidencias.py` | coletor | 2026-11-06 08:53 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `processar_contribuicoes.py` | coletor | 2026-10-31 01:14 | 2 s | — | ok | — |
| `python3` | coletor | 2026-11-06 20:50 | 94 s | — | ok | — |
| `reconferir_instrumentos_federais.py` | coletor | 2026-11-06 07:30 | 1 s | — | ok | — |
| `revisar_pistas.py` | coletor | 2026-11-06 06:47 | 659 s | — | ok | — |
| `scripts/amostra_auditoria_semanal.py` | coletor | 2026-11-06 08:25 | 1 s | — | ok | — |
| `scripts/corrigir_atribuicao_por_dominio.py` | coletor | 2026-11-06 06:45 | 80 s | — | ok | — |
| `scripts/fechar_saude.py` | coletor | 2026-11-03 02:26 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/preservar_textos_integrais.py` | coletor | 2026-11-06 08:53 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/proveniencia_estadual.py` | coletor | 2026-11-06 03:18 | 1 s | — | ok | — |
| `scripts/reavaliar_fontes_suspensas.py` | coletor | 2026-11-06 05:15 | 1004 s | — | ok | — |
| `scripts/rejulgar_decisoes_do_juiz.py` | coletor | 2026-10-30 06:06 | 3455 s | — | ok | — |
| `scripts/sondar_boletim_infogripe.py` | coletor | 2026-10-31 01:14 | 90 s | — | ok | — |
| `scripts/sondar_credenciais.py` | coletor | 2026-11-06 01:16 | 2 s | — | ok | — |
| `scripts/triar_fila.py` | coletor | 2026-11-05 02:23 | 1 s | — | ok | — |
| `scripts/verificar_esquema_de_pista.py` | coletor | 2026-11-06 03:03 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/verificar_funil.py` | coletor | 2026-10-31 01:20 | 1 s | — | **erro** | ✗ FUNIL: a contagem da rodada se contradiz ou a etapa não funcionou: |
| `seguir_pistas.py` | coletor | 2026-11-06 07:25 | 109 s | — | ok | — |
| `triar_confianca_pistas.py` | coletor | 2026-11-06 07:27 | 3 s | — | ok | — |
| `verificar_links.py` | coletor | 2026-11-03 01:36 | 232 s | — | **erro** (2 seguidas) | erro: HTTPSConnectionPool(host='www.defesacivil.sc.gov.br', port=443): Max retries exceeded with url: /2026/08/14/chuva- |
| `verificar_pista_imprensa.py` | coletor | 2026-11-06 07:27 | 20 s | — | ok | — |
