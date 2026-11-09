# Saúde do pipeline

Gerado por `scripts/gerar_saude_pipeline.py` a partir de `data/saude_pipeline.json`, que os
jobs escrevem com `scripts/saude_pipeline.py --rodar`. Item 2 do handover de desacoplamento
(27/09/2026). **Arquivo derivado: não se edita à mão.**

Duas classes, e a diferença importa. **Essencial** (`recalcular_mare.py`, `gerar_*.py`): se
erra, o site publica um estado que não corresponde ao dado — reprova o portão. **Coletor**:
fonte fora do ar é rotina, e uma falha isolada não é defeito do pipeline; erro em duas
rodadas seguidas vira alerta, porque aí não é a fonte, é o coletor.

Janela: 2026-11-01 a 2026-11-08 (1434 execução(ões) registrada(s), 7 dias de histórico).

## Alertas

- coletar_cobertura_qd.py: erro em 2 rodadas seguidas — interrompido pelo prazo do elo
- coletar_sih.py: erro em 8 rodadas seguidas — SIH: nenhum arquivo lido (0 na fila, 0 falha(s)); os arquivos anteriores ficam
- coletar_sim.py: erro em 4 rodadas seguidas — SIM: nenhum arquivo lido (0 na fila, 0 falha(s)); os arquivos anteriores ficam
- julgar_filas.py: erro em 3 rodadas seguidas — interrompido pelo prazo do elo
- monitorar_busca_web.py: erro em 4 rodadas seguidas — ✗ busca web: 100% sem resposta do motor, acima do teto de 25% — esta rodada NÃO conta como verificação da camada 4

## Cobertura em 15 dias

cobertura 15d: 5031/5571 com verificação real até 2026-11-08 · por canal: web 249 · QD 527 · consorciado 1675 · DOE 4937

## Última execução de cada script

| script | papel | última execução | duração | itens | status | erro |
|---|---|---|---|---:|---|---|
| `gerar_monitor_saude.py` | essencial | 2026-11-07 01:45 | 0 s | — | ok | — |
| `gerar_mortalidade_comparada.py` | essencial | 2026-11-08 07:16 | 0 s | — | ok | — |
| `gerar_saude_municipio.py` | essencial | 2026-11-08 01:39 | 1 s | — | ok | — |
| `recalcular_mare.py` | essencial | 2026-11-08 01:55 | 4 s | — | ok | — |
| `aplicar_promocoes_do_juiz.py` | coletor | 2026-11-08 08:45 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `atualizar.py` | coletor | 2026-11-07 01:43 | 104 s | — | ok | — |
| `atualizar_populacao.py` | coletor | 2026-11-07 01:15 | 1 s | — | ok | — |
| `buscar_planos_fontes_abertas.py` | coletor | 2026-11-02 21:10 | 80 s | — | ok | — |
| `buscar_protocolo_calor.py` | coletor | 2026-11-07 01:28 | 91 s | 4 | ok | — |
| `classificar_planos_municipais.py` | coletor | 2026-11-07 01:19 | 1 s | — | ok | — |
| `classificar_saude_no_plano.py` | coletor | 2026-11-08 01:39 | 1 s | — | ok | — |
| `coletar_arboviroses_sinan.py` | coletor | 2026-11-08 01:38 | 38 s | — | ok | — |
| `coletar_boletim_df_arboviroses.py` | coletor | 2026-11-08 01:32 | 356 s | — | ok | — |
| `coletar_boletim_ms_dengue.py` | coletor | 2026-11-08 01:32 | 24 s | — | ok | — |
| `coletar_boletim_pb_arboviroses.py` | coletor | 2026-11-08 01:38 | 4 s | — | ok | — |
| `coletar_boletim_pe_arboviroses.py` | coletor | 2026-11-08 01:38 | 7 s | — | ok | — |
| `coletar_cadastro_prioritarios.py` | coletor | 2026-11-07 01:14 | 28 s | — | ok | — |
| `coletar_cobertura_qd.py` | coletor | 2026-11-08 01:19 | 7542 s | — | **erro** (2 seguidas) | interrompido pelo prazo do elo |
| `coletar_datasus_dbc.py` | coletor | 2026-11-08 07:14 | 38 s | — | ok | — |
| `coletar_dda.py` | coletor | 2026-11-08 01:31 | 56 s | — | ok | — |
| `coletar_desfechos_saude.py` | coletor | 2026-11-08 01:23 | 454 s | — | ok | — |
| `coletar_diarios_consorciados.py` | coletor | 2026-11-07 01:18 | 2469 s | 27 | ok | — |
| `coletar_diarios_municipais.py` | coletor | 2026-11-07 01:18 | 2 s | 0 | ok | — |
| `coletar_doe.py` | coletor | 2026-11-07 01:59 | 3017 s | — | ok | — |
| `coletar_edicoes_doe.py` | coletor | 2026-11-06 02:22 | 3032 s | — | ok | — |
| `coletar_espin.py` | coletor | 2026-11-07 01:14 | 878 s | — | ok | — |
| `coletar_normais_inmet.py` | coletor | 2026-11-07 01:15 | 18 s | — | ok | — |
| `coletar_obitos.py` | coletor | 2026-11-08 07:16 | 3 s | — | ok | — |
| `coletar_obitos_registro_civil.py` | coletor | 2026-11-08 01:39 | 20 s | — | ok | — |
| `coletar_planos_arboviroses.py` | coletor | 2026-11-08 07:17 | 1517 s | — | ok | — |
| `coletar_prioritarios_mma.py` | coletor | 2026-11-07 01:15 | 2 s | — | ok | — |
| `coletar_projecao_cil.py` | coletor | 2026-11-08 07:16 | 2 s | — | ok | — |
| `coletar_recursos_resposta.py` | coletor | 2026-11-07 02:50 | 87 s | — | **erro** | TimeoutError: The read operation timed out |
| `coletar_s2id.py` | coletor | 2026-11-07 02:50 | 44 s | — | ok | — |
| `coletar_saude.py` | coletor | 2026-11-08 01:14 | 73 s | — | ok | — |
| `coletar_saude_estadual.py` | coletor | 2026-11-03 02:26 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `coletar_semiarido_sudene.py` | coletor | 2026-11-07 01:15 | 3 s | — | ok | — |
| `coletar_sg_esus.py` | coletor | 2026-11-08 03:00 | 9 s | — | ok | — |
| `coletar_sih.py` | coletor | 2026-11-08 07:16 | 5 s | — | **erro** (8 seguidas) | SIH: nenhum arquivo lido (0 na fila, 0 falha(s)); os arquivos anteriores ficam |
| `coletar_sim.py` | coletor | 2026-11-08 07:16 | 7 s | — | **erro** (4 seguidas) | SIM: nenhum arquivo lido (0 na fila, 0 falha(s)); os arquivos anteriores ficam |
| `coletar_sinais_risco.py` | coletor | 2026-11-08 01:14 | 134 s | — | ok | — |
| `coletar_sisab.py` | coletor | 2026-11-08 07:14 | 110 s | — | ok | — |
| `coletar_srag_gripe.py` | coletor | 2026-11-07 01:17 | 144 s | — | ok | — |
| `coletar_srag_sivep.py` | coletor | 2026-11-08 02:59 | 37 s | — | ok | — |
| `coletar_transferencias_municipais.py` | coletor | 2026-11-08 01:16 | 68 s | — | ok | — |
| `consultar_querido_diario.py` | coletor | 2026-11-07 01:17 | 62 s | — | **erro** | portas tentadas: api.queridodiario.org.br: HTTPError HTTP Error 520: <none> \| queridodiario.ok.org.br: HTTPError HTTP E |
| `descobrir_dominios.py` | coletor | 2026-11-08 03:25 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `descobrir_planos.py` | coletor | 2026-11-08 08:57 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `desfechos_sus.py` | coletor | 2026-11-08 07:16 | 1 s | — | ok | — |
| `detectar_marcos_federais.py` | coletor | 2026-11-08 08:57 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `julgar_e_aplicar_descobertas.py` | coletor | 2026-11-08 08:45 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `julgar_filas.py` | coletor | 2026-11-08 08:37 | 477 s | — | **erro** (3 seguidas) | interrompido pelo prazo do elo |
| `julgar_saude.py` | coletor | 2026-11-03 01:15 | 4291 s | — | **erro** | interrompido pelo prazo do elo |
| `ler_planos_arboviroses.py` | coletor | 2026-11-08 07:42 | 5 s | — | ok | — |
| `monitorar_atos_resposta.py` | coletor | 2026-11-08 08:57 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `monitorar_busca_web.py` | coletor | 2026-11-08 01:37 | 316 s | 2 | **erro** (4 seguidas) | ✗ busca web: 100% sem resposta do motor, acima do teto de 25% — esta rodada NÃO conta como verificação da camada 4 |
| `monitorar_imprensa_regional.py` | coletor | 2026-11-08 08:57 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `monitorar_imprensa_saude.py` | coletor | 2026-11-08 08:57 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `monitorar_politica_por_inteiro.py` | coletor | 2026-11-08 08:57 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `monitorar_sinais_federais.py` | coletor | 2026-11-08 08:57 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `preservar_evidencias.py` | coletor | 2026-11-08 06:02 | 269 s | — | ok | — |
| `processar_contribuicoes.py` | coletor | 2026-11-07 01:15 | 1 s | — | ok | — |
| `python3` | coletor | 2026-11-08 13:24 | 152 s | — | ok | — |
| `reconferir_instrumentos_federais.py` | coletor | 2026-11-08 07:42 | 1 s | — | ok | — |
| `revisar_pistas.py` | coletor | 2026-11-08 08:30 | 420 s | — | ok | — |
| `scripts/amostra_auditoria_semanal.py` | coletor | 2026-11-08 08:45 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/corrigir_atribuicao_por_dominio.py` | coletor | 2026-11-08 08:28 | 94 s | — | ok | — |
| `scripts/diagnostico_fontes_saude.py` | coletor | 2026-11-07 19:03 | 372 s | — | ok | — |
| `scripts/fechar_saude.py` | coletor | 2026-11-03 02:26 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `scripts/preservar_textos_integrais.py` | coletor | 2026-11-08 06:06 | 3 s | — | ok | — |
| `scripts/proveniencia_estadual.py` | coletor | 2026-11-06 03:18 | 1 s | — | ok | — |
| `scripts/reavaliar_fontes_suspensas.py` | coletor | 2026-11-08 05:13 | 1135 s | — | ok | — |
| `scripts/sondar_boletim_infogripe.py` | coletor | 2026-11-07 01:15 | 97 s | — | ok | — |
| `scripts/sondar_credenciais.py` | coletor | 2026-11-08 01:17 | 3 s | — | ok | — |
| `scripts/triar_fila.py` | coletor | 2026-11-08 03:06 | 1 s | — | ok | — |
| `scripts/verificar_esquema_de_pista.py` | coletor | 2026-11-08 03:19 | 2 s | — | ok | — |
| `scripts/verificar_funil.py` | coletor | 2026-11-07 01:21 | 0 s | — | **erro** | ✗ FUNIL: a contagem da rodada se contradiz ou a etapa não funcionou: |
| `seguir_pistas.py` | coletor | 2026-11-08 08:57 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `triar_confianca_pistas.py` | coletor | 2026-11-08 08:57 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `verificar_links.py` | coletor | 2026-11-07 01:44 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
| `verificar_pista_imprensa.py` | coletor | 2026-11-08 08:57 | 0 s | — | pulado | prazo do elo esgotado antes de começar |
