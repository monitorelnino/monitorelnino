# Saúde do pipeline

Gerado por `scripts/gerar_saude_pipeline.py` a partir de `data/saude_pipeline.json`, que os
jobs escrevem com `scripts/saude_pipeline.py --rodar`. Item 2 do handover de desacoplamento
(27/09/2026). **Arquivo derivado: não se edita à mão.**

Duas classes, e a diferença importa. **Essencial** (`recalcular_mare.py`, `gerar_*.py`): se
erra, o site publica um estado que não corresponde ao dado — reprova o portão. **Coletor**:
fonte fora do ar é rotina, e uma falha isolada não é defeito do pipeline; erro em duas
rodadas seguidas vira alerta, porque aí não é a fonte, é o coletor.

Janela: 2026-10-27 a 2026-11-03 (1234 execução(ões) registrada(s), 7 dias de histórico).

## Alertas

- coletar_sih.py: erro em 7 rodadas seguidas — SIH: nenhum arquivo lido (0 na fila, 0 falha(s)); os arquivos anteriores ficam
- monitorar_busca_web.py: erro em 4 rodadas seguidas — ✗ busca web: 100% sem resposta do motor, acima do teto de 25% — esta rodada NÃO conta como verificação da camada 4
- verificar_links.py: erro em 2 rodadas seguidas — erro: HTTPSConnectionPool(host='www.defesacivil.sc.gov.br', port=443): Max retries exceeded with url: /2026/08/14/chuva-forte-deixa-danos-em-municipios-de-santa-catarina-e-risco-de-temporais-segue-alto-ate-sabado/ (Caused by ConnectTimeoutError(<HTTPSConnection(host='www.defesacivil.sc.gov.br', port

## Cobertura em 15 dias

cobertura 15d: 4984/5571 com verificação real até 2026-11-03 · por canal: web 647 · QD 527 · consorciado 1713 · DOE 4677

## Última execução de cada script

| script | papel | última execução | duração | itens | status | erro |
|---|---|---|---|---:|---|---|
| `gerar_monitor_saude.py` | essencial | 2026-11-01 21:57 | 1 s | — | ok | — |
| `gerar_mortalidade_comparada.py` | essencial | 2026-11-03 07:28 | 1 s | — | ok | — |
| `gerar_saude_municipio.py` | essencial | 2026-11-02 01:41 | 0 s | — | ok | — |
| `recalcular_mare.py` | essencial | 2026-11-03 08:43 | 3 s | — | ok | — |
| `aplicar_promocoes_do_juiz.py` | coletor | 2026-11-03 07:50 | 44 s | 1 | ok | — |
| `atualizar.py` | coletor | 2026-10-31 01:55 | 103 s | — | ok | — |
| `atualizar_populacao.py` | coletor | 2026-10-31 01:14 | 1 s | — | ok | — |
| `buscar_planos_fontes_abertas.py` | coletor | 2026-11-02 21:10 | 80 s | — | ok | — |
| `buscar_protocolo_calor.py` | coletor | 2026-10-31 01:21 | 18 s | 4 | ok | — |
| `classificar_planos_municipais.py` | coletor | 2026-10-31 01:20 | 1 s | — | ok | — |
| `classificar_saude_no_plano.py` | coletor | 2026-11-02 01:41 | 5 s | — | ok | — |
| `coletar_arboviroses_sinan.py` | coletor | 2026-11-02 01:39 | 43 s | — | ok | — |
| `coletar_boletim_df_arboviroses.py` | coletor | 2026-11-02 01:31 | 268 s | — | ok | — |
| `coletar_boletim_ms_dengue.py` | coletor | 2026-11-02 01:31 | 15 s | — | ok | — |
| `coletar_boletim_pb_arboviroses.py` | coletor | 2026-11-02 01:36 | 199 s | — | ok | — |
| `coletar_boletim_pe_arboviroses.py` | coletor | 2026-11-02 01:36 | 6 s | — | ok | — |
| `coletar_cadastro_prioritarios.py` | coletor | 2026-10-31 01:13 | 34 s | — | ok | — |
| `coletar_cobertura_qd.py` | coletor | 2026-11-01 01:20 | 7495 s | — | **erro** | interrompido pelo prazo do elo |
| `coletar_datasus_dbc.py` | coletor | 2026-11-03 07:15 | 42 s | — | ok | — |
| `coletar_dda.py` | coletor | 2026-11-02 01:30 | 55 s | — | ok | — |
| `coletar_desfechos_saude.py` | coletor | 2026-11-02 01:23 | 410 s | — | ok | — |
| `coletar_diarios_consorciados.py` | coletor | 2026-11-02 01:27 | 2986 s | 37 | ok | — |
| `coletar_diarios_municipais.py` | coletor | 2026-11-02 01:27 | 3 s | 0 | ok | — |
| `coletar_doe.py` | coletor | 2026-11-03 02:16 | 3530 s | — | ok | — |
| `coletar_edicoes_doe.py` | coletor | 2026-11-01 02:26 | 1499 s | — | ok | — |
| `coletar_espin.py` | coletor | 2026-11-01 02:51 | 231 s | — | ok | — |
| `coletar_normais_inmet.py` | coletor | 2026-10-31 01:14 | 4 s | — | ok | — |
| `coletar_obitos.py` | coletor | 2026-11-03 07:17 | 4 s | — | ok | — |
| `coletar_obitos_registro_civil.py` | coletor | 2026-11-02 01:40 | 51 s | — | ok | — |
| `coletar_planos_arboviroses.py` | coletor | 2026-11-03 07:28 | 780 s | — | ok | — |
| `coletar_prioritarios_mma.py` | coletor | 2026-10-31 01:14 | 4 s | — | ok | — |
| `coletar_projecao_cil.py` | coletor | 2026-11-03 07:28 | 3 s | — | ok | — |
| `coletar_recursos_resposta.py` | coletor | 2026-11-03 03:31 | 22 s | — | ok | — |
| `coletar_s2id.py` | coletor | 2026-11-03 03:15 | 924 s | — | ok | — |
| `coletar_saude.py` | coletor | 2026-11-02 01:15 | 75 s | — | ok | — |
| `coletar_saude_estadual.py` | coletor | 2026-10-27 02:25 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `coletar_semiarido_sudene.py` | coletor | 2026-10-31 01:14 | 3 s | — | ok | — |
| `coletar_sg_esus.py` | coletor | 2026-11-03 03:38 | 9 s | — | ok | — |
| `coletar_sih.py` | coletor | 2026-11-03 07:28 | 6 s | — | **erro** (7 seguidas) | SIH: nenhum arquivo lido (0 na fila, 0 falha(s)); os arquivos anteriores ficam |
| `coletar_sim.py` | coletor | 2026-11-03 07:17 | 618 s | — | ok | — |
| `coletar_sinais_risco.py` | coletor | 2026-11-02 01:14 | 86 s | — | ok | — |
| `coletar_sisab.py` | coletor | 2026-11-03 07:15 | 112 s | — | ok | — |
| `coletar_srag_gripe.py` | coletor | 2026-10-31 01:15 | 282 s | — | ok | — |
| `coletar_srag_sivep.py` | coletor | 2026-11-03 03:37 | 28 s | — | ok | — |
| `coletar_transferencias_municipais.py` | coletor | 2026-11-02 01:16 | 76 s | — | ok | — |
| `consultar_querido_diario.py` | coletor | 2026-11-02 01:17 | 594 s | 47 | ok | — |
| `descobrir_dominios.py` | coletor | 2026-11-01 03:25 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `descobrir_planos.py` | coletor | 2026-11-03 05:51 | 620 s | — | ok | — |
| `desfechos_sus.py` | coletor | 2026-11-03 07:17 | 1 s | — | ok | — |
| `detectar_marcos_federais.py` | coletor | 2026-11-03 05:51 | 2 s | 0 | ok | — |
| `julgar_e_aplicar_descobertas.py` | coletor | 2026-11-03 07:36 | 823 s | — | ok | — |
| `julgar_filas.py` | coletor | 2026-11-03 06:21 | 4502 s | — | **erro** | interrompido pelo prazo do elo |
| `julgar_saude.py` | coletor | 2026-11-01 21:57 | 37 s | — | ok | — |
| `ler_planos_arboviroses.py` | coletor | 2026-11-03 07:41 | 3 s | — | ok | — |
| `monitorar_atos_resposta.py` | coletor | 2026-11-03 05:43 | 415 s | 17619 | ok | — |
| `monitorar_busca_web.py` | coletor | 2026-11-03 08:25 | 315 s | 2 | **erro** (4 seguidas) | ✗ busca web: 100% sem resposta do motor, acima do teto de 25% — esta rodada NÃO conta como verificação da camada 4 |
| `monitorar_imprensa_regional.py` | coletor | 2026-11-03 05:37 | 283 s | 40 | ok | — |
| `monitorar_imprensa_saude.py` | coletor | 2026-11-03 05:42 | 105 s | 27 | ok | — |
| `monitorar_politica_por_inteiro.py` | coletor | 2026-11-03 05:50 | 3 s | 17619 | ok | — |
| `monitorar_sinais_federais.py` | coletor | 2026-11-03 05:50 | 4 s | 10 | ok | — |
| `preservar_evidencias.py` | coletor | 2026-11-03 08:10 | 1 s | — | ok | — |
| `processar_contribuicoes.py` | coletor | 2026-10-31 01:14 | 2 s | — | ok | — |
| `python3` | coletor | 2026-11-02 17:57 | 350 s | — | ok | — |
| `revisar_pistas.py` | coletor | 2026-11-03 06:15 | 371 s | — | ok | — |
| `scripts/amostra_auditoria_semanal.py` | coletor | 2026-11-03 07:51 | 1 s | — | ok | — |
| `scripts/corrigir_atribuicao_por_dominio.py` | coletor | 2026-11-03 06:14 | 75 s | — | ok | — |
| `scripts/fechar_saude.py` | coletor | 2026-10-27 02:25 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/preservar_textos_integrais.py` | coletor | 2026-11-03 08:10 | 3 s | — | ok | — |
| `scripts/reavaliar_fontes_suspensas.py` | coletor | 2026-11-03 05:14 | 746 s | — | ok | — |
| `scripts/rejulgar_decisoes_do_juiz.py` | coletor | 2026-10-30 06:06 | 3455 s | — | ok | — |
| `scripts/sondar_boletim_infogripe.py` | coletor | 2026-10-31 01:14 | 90 s | — | ok | — |
| `scripts/sondar_credenciais.py` | coletor | 2026-11-02 01:17 | 1 s | — | ok | — |
| `scripts/sondar_rotas_doe.py` | coletor | 2026-10-28 21:49 | 92 s | — | ok | — |
| `scripts/triar_fila.py` | coletor | 2026-11-03 03:44 | 2 s | — | ok | — |
| `scripts/verificar_esquema_de_pista.py` | coletor | 2026-11-03 03:57 | 2 s | — | ok | — |
| `scripts/verificar_funil.py` | coletor | 2026-10-31 01:20 | 1 s | — | **erro** | ✗ FUNIL: a contagem da rodada se contradiz ou a etapa não funcionou: |
| `seguir_pistas.py` | coletor | 2026-11-03 06:05 | 209 s | — | ok | — |
| `triar_confianca_pistas.py` | coletor | 2026-11-03 06:09 | 2 s | — | ok | — |
| `verificar_links.py` | coletor | 2026-10-31 01:33 | 194 s | — | **erro** (2 seguidas) | erro: HTTPSConnectionPool(host='www.defesacivil.sc.gov.br', port=443): Max retries exceeded with url: /2026/08/14/chuva- |
| `verificar_pista_imprensa.py` | coletor | 2026-11-03 06:09 | 19 s | — | ok | — |
