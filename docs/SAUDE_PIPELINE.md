# Saúde do pipeline

Gerado por `scripts/gerar_saude_pipeline.py` a partir de `data/saude_pipeline.json`, que os
jobs escrevem com `scripts/saude_pipeline.py --rodar`. Item 2 do handover de desacoplamento
(27/09/2026). **Arquivo derivado: não se edita à mão.**

Duas classes, e a diferença importa. **Essencial** (`recalcular_mare.py`, `gerar_*.py`): se
erra, o site publica um estado que não corresponde ao dado — reprova o portão. **Coletor**:
fonte fora do ar é rotina, e uma falha isolada não é defeito do pipeline; erro em duas
rodadas seguidas vira alerta, porque aí não é a fonte, é o coletor.

Janela: 2026-10-28 a 2026-11-04 (1399 execução(ões) registrada(s), 7 dias de histórico).

## Alertas

- coletar_sih.py: erro em 7 rodadas seguidas — SIH: nenhum arquivo lido (0 na fila, 0 falha(s)); os arquivos anteriores ficam
- consultar_querido_diario.py: erro em 2 rodadas seguidas — portas tentadas: api.queridodiario.org.br: HTTPError HTTP Error 520: <none> | queridodiario.ok.org.br: HTTPError HTTP Error 520: <none> | api.queridodiario.ok.org.br: URLError <urlopen error [SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] sslv3 alert handshake failur
- verificar_links.py: erro em 2 rodadas seguidas — erro: HTTPSConnectionPool(host='www.defesacivil.sc.gov.br', port=443): Max retries exceeded with url: /2026/08/14/chuva-forte-deixa-danos-em-municipios-de-santa-catarina-e-risco-de-temporais-segue-alto-ate-sabado/ (Caused by ConnectTimeoutError(<HTTPSConnection(host='www.defesacivil.sc.gov.br', port

## Cobertura em 15 dias

cobertura 15d: 4984/5571 com verificação real até 2026-11-04 · por canal: web 501 · QD 527 · consorciado 1723 · DOE 4677

## Última execução de cada script

| script | papel | última execução | duração | itens | status | erro |
|---|---|---|---|---:|---|---|
| `gerar_monitor_saude.py` | essencial | 2026-11-01 21:57 | 1 s | — | ok | — |
| `gerar_mortalidade_comparada.py` | essencial | 2026-11-04 07:20 | 1 s | — | ok | — |
| `gerar_saude_municipio.py` | essencial | 2026-11-03 01:35 | 1 s | — | ok | — |
| `recalcular_mare.py` | essencial | 2026-11-04 20:25 | 4 s | — | ok | — |
| `aplicar_promocoes_do_juiz.py` | coletor | 2026-11-04 12:31 | 259 s | 1 | ok | — |
| `atualizar.py` | coletor | 2026-10-31 01:55 | 103 s | — | ok | — |
| `atualizar_populacao.py` | coletor | 2026-10-31 01:14 | 1 s | — | ok | — |
| `buscar_planos_fontes_abertas.py` | coletor | 2026-11-02 21:10 | 80 s | — | ok | — |
| `buscar_protocolo_calor.py` | coletor | 2026-11-03 01:17 | 114 s | — | ok | — |
| `classificar_planos_municipais.py` | coletor | 2026-10-31 01:20 | 1 s | — | ok | — |
| `classificar_saude_no_plano.py` | coletor | 2026-11-03 01:35 | 0 s | — | ok | — |
| `coletar_arboviroses_sinan.py` | coletor | 2026-11-03 01:34 | 48 s | — | ok | — |
| `coletar_boletim_df_arboviroses.py` | coletor | 2026-11-03 01:30 | 254 s | — | ok | — |
| `coletar_boletim_ms_dengue.py` | coletor | 2026-11-03 01:30 | 21 s | — | ok | — |
| `coletar_boletim_pb_arboviroses.py` | coletor | 2026-11-03 01:34 | 3 s | — | ok | — |
| `coletar_boletim_pe_arboviroses.py` | coletor | 2026-11-03 01:34 | 6 s | — | ok | — |
| `coletar_cadastro_prioritarios.py` | coletor | 2026-10-31 01:13 | 34 s | — | ok | — |
| `coletar_cobertura_qd.py` | coletor | 2026-11-01 01:20 | 7495 s | — | **erro** | interrompido pelo prazo do elo |
| `coletar_datasus_dbc.py` | coletor | 2026-11-04 07:15 | 38 s | — | ok | — |
| `coletar_dda.py` | coletor | 2026-11-03 01:29 | 56 s | — | ok | — |
| `coletar_desfechos_saude.py` | coletor | 2026-11-03 01:21 | 453 s | — | ok | — |
| `coletar_diarios_consorciados.py` | coletor | 2026-11-04 04:07 | 2286 s | 32 | ok | — |
| `coletar_diarios_municipais.py` | coletor | 2026-11-04 04:07 | 2 s | 0 | ok | — |
| `coletar_doe.py` | coletor | 2026-11-04 04:45 | 3074 s | — | ok | — |
| `coletar_edicoes_doe.py` | coletor | 2026-11-04 01:44 | 6096 s | — | **erro** | interrompido pelo prazo do elo |
| `coletar_espin.py` | coletor | 2026-11-04 03:26 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `coletar_normais_inmet.py` | coletor | 2026-10-31 01:14 | 4 s | — | ok | — |
| `coletar_obitos.py` | coletor | 2026-11-04 07:17 | 5 s | — | ok | — |
| `coletar_obitos_registro_civil.py` | coletor | 2026-11-03 01:35 | 25 s | — | ok | — |
| `coletar_planos_arboviroses.py` | coletor | 2026-11-04 07:20 | 1505 s | — | ok | — |
| `coletar_prioritarios_mma.py` | coletor | 2026-10-31 01:14 | 4 s | — | ok | — |
| `coletar_projecao_cil.py` | coletor | 2026-11-04 07:20 | 2 s | — | ok | — |
| `coletar_recursos_resposta.py` | coletor | 2026-11-04 05:52 | 30 s | — | ok | — |
| `coletar_s2id.py` | coletor | 2026-11-04 05:37 | 934 s | — | ok | — |
| `coletar_saude.py` | coletor | 2026-11-03 01:12 | 91 s | — | ok | — |
| `coletar_saude_estadual.py` | coletor | 2026-11-03 02:26 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `coletar_semiarido_sudene.py` | coletor | 2026-10-31 01:14 | 3 s | — | ok | — |
| `coletar_sg_esus.py` | coletor | 2026-11-03 03:38 | 9 s | — | ok | — |
| `coletar_sih.py` | coletor | 2026-11-04 07:20 | 4 s | — | **erro** (7 seguidas) | SIH: nenhum arquivo lido (0 na fila, 0 falha(s)); os arquivos anteriores ficam |
| `coletar_sim.py` | coletor | 2026-11-04 07:17 | 141 s | — | ok | — |
| `coletar_sinais_risco.py` | coletor | 2026-11-03 01:11 | 123 s | — | ok | — |
| `coletar_sisab.py` | coletor | 2026-11-04 07:15 | 126 s | — | ok | — |
| `coletar_srag_gripe.py` | coletor | 2026-10-31 01:15 | 282 s | — | ok | — |
| `coletar_srag_sivep.py` | coletor | 2026-11-03 03:37 | 28 s | — | ok | — |
| `coletar_transferencias_municipais.py` | coletor | 2026-11-03 01:13 | 80 s | — | ok | — |
| `consultar_querido_diario.py` | coletor | 2026-11-04 04:05 | 158 s | — | **erro** (2 seguidas) | portas tentadas: api.queridodiario.org.br: HTTPError HTTP Error 520: <none> \| queridodiario.ok.org.br: HTTPError HTTP E |
| `descobrir_dominios.py` | coletor | 2026-11-01 03:25 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `descobrir_planos.py` | coletor | 2026-11-04 08:33 | 465 s | 42 | ok | — |
| `desfechos_sus.py` | coletor | 2026-11-04 07:17 | 1 s | — | ok | — |
| `detectar_marcos_federais.py` | coletor | 2026-11-04 08:33 | 2 s | 0 | ok | — |
| `julgar_e_aplicar_descobertas.py` | coletor | 2026-11-04 08:57 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `julgar_filas.py` | coletor | 2026-11-04 10:01 | 9002 s | — | **erro** | interrompido pelo prazo do elo |
| `julgar_saude.py` | coletor | 2026-11-03 01:15 | 4291 s | — | **erro** | interrompido pelo prazo do elo |
| `ler_planos_arboviroses.py` | coletor | 2026-11-04 07:45 | 5 s | — | ok | — |
| `monitorar_atos_resposta.py` | coletor | 2026-11-04 08:23 | 614 s | 17664 | ok | — |
| `monitorar_busca_web.py` | coletor | 2026-11-04 08:41 | 214 s | — | **erro** | interrompido pelo prazo do elo |
| `monitorar_imprensa_regional.py` | coletor | 2026-11-04 08:18 | 176 s | 40 | ok | — |
| `monitorar_imprensa_saude.py` | coletor | 2026-11-04 08:21 | 106 s | 27 | ok | — |
| `monitorar_politica_por_inteiro.py` | coletor | 2026-11-04 08:33 | 4 s | 17664 | ok | — |
| `monitorar_sinais_federais.py` | coletor | 2026-11-04 08:33 | 5 s | 10 | ok | — |
| `preservar_evidencias.py` | coletor | 2026-11-03 08:10 | 1 s | — | ok | — |
| `processar_contribuicoes.py` | coletor | 2026-10-31 01:14 | 2 s | — | ok | — |
| `python3` | coletor | 2026-11-04 19:47 | 52 s | 1 | ok | — |
| `revisar_pistas.py` | coletor | 2026-11-04 08:57 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/amostra_auditoria_semanal.py` | coletor | 2026-11-04 08:57 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/corrigir_atribuicao_por_dominio.py` | coletor | 2026-11-04 08:57 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/fechar_saude.py` | coletor | 2026-11-03 02:26 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/preservar_textos_integrais.py` | coletor | 2026-11-03 08:10 | 3 s | — | ok | — |
| `scripts/proveniencia_estadual.py` | coletor | 2026-11-04 03:26 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/reavaliar_fontes_suspensas.py` | coletor | 2026-11-04 05:14 | 1007 s | — | ok | — |
| `scripts/rejulgar_decisoes_do_juiz.py` | coletor | 2026-10-30 06:06 | 3455 s | — | ok | — |
| `scripts/sondar_boletim_infogripe.py` | coletor | 2026-10-31 01:14 | 90 s | — | ok | — |
| `scripts/sondar_credenciais.py` | coletor | 2026-11-03 01:14 | 2 s | — | ok | — |
| `scripts/sondar_rotas_doe.py` | coletor | 2026-10-28 21:49 | 92 s | — | ok | — |
| `scripts/triar_fila.py` | coletor | 2026-11-03 01:45 | 2 s | — | ok | — |
| `scripts/verificar_esquema_de_pista.py` | coletor | 2026-11-03 01:53 | 3 s | — | ok | — |
| `scripts/verificar_funil.py` | coletor | 2026-10-31 01:20 | 1 s | — | **erro** | ✗ FUNIL: a contagem da rodada se contradiz ou a etapa não funcionou: |
| `seguir_pistas.py` | coletor | 2026-11-04 08:45 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `triar_confianca_pistas.py` | coletor | 2026-11-04 08:45 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `verificar_links.py` | coletor | 2026-11-03 01:36 | 232 s | — | **erro** (2 seguidas) | erro: HTTPSConnectionPool(host='www.defesacivil.sc.gov.br', port=443): Max retries exceeded with url: /2026/08/14/chuva- |
| `verificar_pista_imprensa.py` | coletor | 2026-11-04 08:45 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
