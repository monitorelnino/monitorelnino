# Falhas da noite — catálogo

Gerado por `scripts/catalogo_de_falhas.py --gerar-doc` a partir de `config/falhas_da_noite.json`. Não editar à mão.

Atualizado em 2026-10-10. 32 falhas; 26 com caso de teste que as reproduz; 6 sem, com o que falta dito.

Falha nova vira linha nova no JSON, com causa, prova e caso de teste.

## F01 · A abertura por cron não disparou

- **Noite:** 2026-10-03→2026-10-04
- **Sintoma:** O cron das 01:00 UTC de `noturno_diarios` e os da busca web não dispararam, e a corrente só abriu à mão às 02:40 UTC de 04/10 (já em 30/09 o cron atrasara 5h30).
- **Causa:** O cron do GitHub é de melhor esforço e descarta ou atrasa agendamentos em horário de pico (:00, :10, :30), e a abertura dependia só dele.
- **Prova:** run 37171775015 (diários, disparo manual 02:40:26 UTC); run 37171798170 (busca web, disparo manual 02:40:55 UTC); atraso de 5h30 medido em 30/09
- **Correção:** PR #544 (minuto fora do pico, reserva às 01:37, vigia às 02:07) e PR #553 (despachante e relógio da nuvem)
- **Caso de teste:** `scripts/ensaio_da_noite.py::ensaio_despachante_nao_depende_do_cron`

## F02 · Publicação parada por 10 pistas fora do esquema

- **Noite:** 2026-10-03→2026-10-04
- **Sintoma:** `Publicar dados` falhou às 04:51 e às 05:16 UTC de 04/10 e nenhum dado novo foi publicado naquela noite.
- **Causa:** O portão `verificar_esquema_de_pista.py` bloqueava a publicação inteira por 10 pistas malformadas, em vez de pô-las em quarentena.
- **Prova:** Publicar dados 04/10 04:51 UTC e 05:16 UTC, passo Portões
- **Correção:** PR #545 (parcial; o defeito voltou em F07) e PR #555 (quarentena pelo próprio portão)
- **Caso de teste:** `scripts/ensaio_da_noite.py::ensaio_pista_invalida_nao_para_a_publicacao`

## F03 · 29 publicações reprovadas por derivado obsoleto

- **Noite:** 2026-10-03→2026-10-06
- **Sintoma:** 29 das 33 falhas do publicador entre 03 e 06/10 foram o portão de derivado obsoleto, com o dado certo; o site chegou a ficar com dado de 05/10 em 06/10.
- **Causa:** Gerador não idempotente (CODEMAP) regenerava diferente no publicador, e um portão de código barrava a publicação de dado.
- **Prova:** Publicar dados 37467174563 (06/10, portões); contagem de 03–06/10 no handover de publicação definitiva
- **Correção:** PR #567 (fase 0, causa A) e PR #570 (idempotência vira portão de PR; perfil `publicacao`)
- **Caso de teste:** `scripts/verificar_idempotencia_dos_derivados.py`

## F04 · 3 publicações reprovadas pela corrida do medidor

- **Noite:** 2026-10-03→2026-10-06
- **Sintoma:** Três publicações reprovaram por "texto ausente" no medidor de layout, com o dado certo.
- **Causa:** `_layout_dump.js` media com `networkidle` mais 1,5 s, antes de o `fetch` de `financiamento.js` escrever a frase exigida pelo contrato.
- **Prova:** contagem de 03–06/10 no handover de publicação definitiva
- **Correção:** PR #570 (espera pela condição do contrato, até 20 s, e duas renderizações); em 08/10 a página deixou de buscar `compromissos_federais.json` quatro vezes
- **Caso de teste:** `scripts/testar_corrida_do_medidor.js`

## F05 · Despachante mudo: dois workflows rejeitados pelo GitHub

- **Noite:** 2026-10-04
- **Sintoma:** `busca_web_cadencia.yml` e `auditoria_seguranca.yml` apareciam com o caminho no lugar do nome, e cada push na `main` gerava um run `failure` com zero jobs; a busca web não rodaria na noite.
- **Causa:** O tique oportunista do #552 foi inserido no meio do `actions/setup-python`, deixando um passo com `run` e `with` ao mesmo tempo, o que só o GitHub rejeita (actionlint e o validador local passavam).
- **Prova:** run 37220698605; commit 5bd3119a (PR #552)
- **Correção:** PR #553 (`with` devolvido ao setup-python; trava em `validar_workflows.py`; `verificar_workflow_aceito.py`; despachante trata rejeição como gravidade alta)
- **Caso de teste:** `scripts/verificar_workflow_aceito.py`

## F06 · Pacote do blog com credencial errada

- **Noite:** 2026-10-04
- **Sintoma:** O workflow `Pacote do blog` falhou às 19:08 BRT de 04/10 (e de novo às 22:08 UTC) com `Repository not found` ao gravar no repositório privado.
- **Causa:** O passo usava `ROBO_DEPLOY_KEY` por SSH, que não alcança o repositório privado, enquanto os outros gravadores usam `ROBO_TOKEN` por HTTPS.
- **Prova:** Pacote do blog 04/10 19:08 BRT; Pacote do blog 04/10 22:08:28 UTC
- **Correção:** PR #554 (o clone avisa e segue), PR #555 (credencial dos outros gravadores) e PR #557 (passo removido: o pacote fica no artefato, por decisão da editoria)
- **Caso de teste:** nenhum — falta: Nenhum teste reprova workflow que grave no repositório privado com credencial diferente da dos demais gravadores; hoje o risco não volta só porque o passo saiu (#557).

## F07 · Oito publicações reprovadas pelo esquema de pista

- **Noite:** 2026-10-04→2026-10-05
- **Sintoma:** A publicação reprovou oito vezes entre 21:23 e 03:57 BRT e o site ficou com dado de 04/10.
- **Causa:** Coletores não migrados ao esquema de 03/10 (sobretudo `rede_social_oficial`) gravavam a fila direto, sem `url_final`, `tipo`, `alvo` e `nivel`, e o portão de esquema bloqueava a publicação inteira.
- **Prova:** 8 runs de Publicar dados 21:23→03:57 BRT; primeira publicação depois da correção: run 37289714404 (05/10 09:42 UTC)
- **Correção:** PR #555 (`scripts/pistas.py` como porta única, oito coletores migrados, quarentena no portão)
- **Caso de teste:** `scripts/ensaio_da_noite.py::ensaio_pista_invalida_nao_para_a_publicacao`

## F08 · Diários cancelados e contados como noite aberta

- **Noite:** 2026-10-04→2026-10-05
- **Sintoma:** O job `diarios / coletar` foi cancelado às 01:14:09 UTC, dois minutos depois de começar, e as tentativas das 03:56 e 04:38 BRT saíram sem trabalhar.
- **Causa:** A guarda "esta noite já abriu?" contava qualquer run criado na janela, inclusive cancelado, então reserva e despachante não refizeram a coleta.
- **Prova:** run 37250382122
- **Correção:** PR #556 (marcador `.feito`; `painel_da_noite.trabalhou`; `janela_da_noite.ja_abriu` exige trabalho)
- **Caso de teste:** `scripts/ensaio_da_noite.py::ensaio_elo_cancelado_e_recuperado`

## F09 · Triagem pendente cancelada pelo grupo `noturno`

- **Noite:** 2026-10-04→2026-10-05
- **Sintoma:** A triagem criada às 01:14:08 UTC foi cancelada sem rodar quando a descoberta chegou às 01:14:12.
- **Causa:** Todos os elos dividiam o grupo de concorrência `noturno`, e o GitHub guarda um só pendente por grupo: o pendente novo cancela o anterior mesmo com `cancel-in-progress: false`.
- **Prova:** relatório do PR #556 (triagem 01:14:08 × descoberta 01:14:12)
- **Correção:** PR #627: grupo `noturno-<elo>`, fila por ordem de chegada (`scripts/vez_na_noite.py`) e reserva dos elos no despachante
- **Caso de teste:** `scripts/ensaio_da_noite.py::ensaio_pendente_cancelado_pela_fila_e_refeito`

## F10 · Conflito de rebase perdeu 114 min de busca web

- **Noite:** 2026-10-04→2026-10-05
- **Sintoma:** A busca web trabalhou 114 minutos e falhou no passo "Commit com rebase" depois de quatro tentativas, descartando a rodada.
- **Causa:** Vários elos gravavam em paralelo `pistas_imprensa.json`, `pistas_revisao.json` e o manifesto, e `_coletor.yml` resolvia com `git rebase -X theirs`, que apaga o lado perdedor em vez de unir.
- **Prova:** mensagem `could not apply 446b1b8… Busca web automática` (4 tentativas)
- **Correção:** PR #556 (classe `FILAS_DE_PISTA` em `unir_conflito_de_rodada.py`; `config/escritores.json`; trabalho recusado sai como artefato)
- **Caso de teste:** `scripts/ensaio_da_noite.py::ensaio_dois_elos_em_paralelo`

## F11 · Painel da noite só mostrava sucesso

- **Noite:** 2026-10-04→2026-10-08
- **Sintoma:** O painel tinha 138 linhas desde 04/10, todas `success`, e os seis elos perdidos de 07→08 não tinham linha.
- **Causa:** A linha do painel só era escrita quando o elo terminava o próprio commit; run cancelado ou com push perdido não deixava rastro.
- **Prova:** medição do lote 0 (#583)
- **Correção:** PR #583 (30 linhas recuperadas da API: descoberta failure ×3, publicar cancelled ×3, elos fora da janela)
- **Caso de teste:** nenhum — falta: Nenhum caso reprova painel sem linha para run cancelado ou com push perdido; os autotestes de `painel_da_noite.py` cobrem só a decisão `trabalhou`.

## F12 · Busca web seguiu morrendo no commit

- **Noite:** 2026-10-05→2026-10-08
- **Sintoma:** 11 de 20 runs da busca web desde 05/10 morreram no passo "Commit com rebase", com 2 a 3 horas de busca cada.
- **Causa:** A busca web tem workflow próprio, fora do `_coletor.yml`, e não recebeu a união pela base comum nem o artefato de trabalho perdido do #556.
- **Prova:** medição do lote 0 (#583): 11 de 20 runs desde 05/10
- **Correção:** PR #583 (guarda, união, artefato e deploy próprio removido na busca web)
- **Caso de teste:** `scripts/ensaio_da_noite.py::ensaio_dois_elos_em_paralelo`

## F13 · Fila de pistas passou de 100 MB

- **Noite:** 2026-10-06
- **Sintoma:** `data/pistas_imprensa.json` foi de 104,79 MB para 187,53 MB em 23 minutos, e todo elo que gravava o arquivo falhou no push (limite GH001 de 100 MB).
- **Causa:** O laço de tentativas do commit fundia de novo o que já estava fundido, multiplicando as pistas.
- **Prova:** triagem 37462427876 (ramo ensaio); sinais 37465646681 (ramo ensaio); publicar 37463752432
- **Correção:** Handover parte 3 (causa C), consolidador de escritor único e trava de tamanho (PR #583)
- **Caso de teste:** `scripts/verificar_tamanho_dos_dados.py --autoteste: o arquivo de 187 MB seria barrado`

## F14 · Domínio reposto sobre árvore reprovada

- **Noite:** 2026-10-06
- **Sintoma:** O publicador repôs o domínio depois de o portão de dado reprovar, com "Portões=failure | Repor=success".
- **Causa:** O passo "Repor o site" tinha `if: always()` e rodava mesmo com portão vermelho ou push cancelado.
- **Prova:** 4 runs de 06/10; run 37732159332 (08/10)
- **Correção:** PR #583 (achado A2-04: deploy só depois do push e com portão verde)
- **Caso de teste:** `scripts/ensaio_da_noite.py::ensaio_portao_vermelho_nao_repoe_o_dominio`

## F15 · Corrente da `main` disparada pelo ramo de ensaio

- **Noite:** 2026-10-06→2026-10-07
- **Sintoma:** A publicação da fase 0 e os elos do `ensaio` puxaram a corrente antiga na `main` de dia (juiz e evidências falharam no commit em 06/10; quatro descobertas em 07/10, uma cancelando a triagem pendente).
- **Causa:** `workflow_run` dispara para run do workflow nomeado em qualquer ramo, e os elos não filtravam `branches: [main]`.
- **Prova:** juiz 37518704648; evidências 37517687385; artefatos coleta-perdida-juiz-37518704648 e coleta-perdida-evidencias-37517687385
- **Correção:** PR #569 (guarda da janela) e PR #583 (achado A2-05: `branches: [main]` nos `workflow_run`)
- **Caso de teste:** nenhum — falta: Nenhum portão ou ensaio reprova `workflow_run` sem `branches: [main]` num elo que grava na `main`.

## F16 · Guarda da janela nunca barrou: 96 commits de dia

- **Noite:** 2026-10-06→2026-10-08
- **Sintoma:** 96 commits de coletor entraram na `main` fora de 01:00–09:00 UTC entre 05 e 08/10, todos com o passo da guarda verde.
- **Causa:** `if ! guarda | tee` rodava em `bash -e` sem `pipefail` e lia o status do `tee`, sempre 0.
- **Prova:** run 37637363692 (juiz 07/10 14:31 UTC, guarda success e Coletar executado); prova do conserto: run 37781162237 (08/10 13:02 UTC, Coletar skipped)
- **Correção:** PR #583 (`shell: bash` e `|| rc=$?` nos passos que decidem; portão de encanamento)
- **Caso de teste:** `scripts/ensaio_da_noite.py::ensaio_guarda_com_o_shell_do_actions`

## F17 · Quatro elos perderam o commit no rebase

- **Noite:** 2026-10-06→2026-10-07
- **Sintoma:** Sinais físicos (duas vezes) e descoberta (duas vezes) perderam o commit no passo de rebase-e-push.
- **Causa:** Não registrada nas notas para esta noite; a noite seguinte mostrou o resolvedor recusando o carimbo de `saude_pipeline.json` (F19).
- **Prova:** conferência da central de 07/10 08:50 UTC
- **Correção:** PR #583 (item 0.2, se a causa for a mesma de F19)
- **Caso de teste:** nenhum — falta: Falta o diagnóstico desta noite, com o arquivo que conflitou, antes de se poder apontar um caso.

## F18 · Fila de recusas dobrou e barrou a publicação

- **Noite:** 2026-10-07
- **Sintoma:** `data/pistas_rejeitadas.json` foi de 4,8 MB para 9,0 MB numa execução, e a trava de tamanho reprovou a publicação na prévia.
- **Causa:** `pistas.rejeitar` empilhava registro idêntico a cada reencontro, e o deduplicador pulava o arquivo de recusas porque a lista se chama `rejeitadas`.
- **Prova:** commit 44332410
- **Correção:** commit 44332410 (campo `vezes`; deduplicador atende os dois formatos)
- **Caso de teste:** `scripts/deduplicar_fila_de_pistas.py --autoteste: recusa repetida sai, recusa de outro motivo fica`

## F19 · Carimbo que recusava a noite

- **Noite:** 2026-10-07→2026-10-08
- **Sintoma:** Seis elos perderam o commit (diários com 2h23 de coleta, descoberta, juiz e dois sinais) e foram para artefato `coleta-perdida-*`.
- **Causa:** Todo elo commita `data/saude_pipeline.json` com a sua hora, e o resolvedor recusava divergência em qualquer escalar; o laço tentava cinco vezes e desistia.
- **Prova:** 37711273308; 37711285165; 37723194156; 37727858615; 37742559024; 37746774655
- **Correção:** PR #583 (item 0.2: o carimbo maior vence em `unir_log`) e PR #584 (reaplicação da noite)
- **Caso de teste:** `scripts/ensaio_da_noite.py::ensaio_carimbo_nao_recusa_a_noite`

## F20 · Vigia viu `queued` como noite não aberta

- **Noite:** 2026-10-08→2026-10-09
- **Sintoma:** Às 01:11 o vigia contou zero execuções na janela e disparou a corrente de novo, com os diários ainda à espera de runner.
- **Causa:** O filtro do vigia, da guarda de abertura e de `painel_da_noite.trabalhou` só aceitava `in_progress`, `success` e `failure`.
- **Prova:** run 37868393670 (diários); run 37868726158 (triagem)
- **Correção:** PR #607 (`queued`, `requested`, `waiting` e `pending` contam como noite aberta; vigia só age após 25 min)
- **Caso de teste:** `scripts/ensaio_da_noite.py::ensaio_fila_de_runner_nao_e_falha`

## F21 · Diários e triagem cancelados na fila

- **Noite:** 2026-10-08→2026-10-09
- **Sintoma:** `diarios / coletar` foi cancelado às 01:13:32 e a triagem por `workflow_run` às 01:16:09, os dois sem passo executado e sem `.feito`.
- **Causa:** O terceiro disparo (F20) entrou como pendente novo no grupo `noturno` compartilhado, e o GitHub cancelou o pendente anterior.
- **Prova:** run 37868393670; run 37868726158
- **Correção:** PR #627: grupo `noturno-<elo>`, fila por ordem de chegada (`scripts/vez_na_noite.py`) e reserva dos elos no despachante
- **Caso de teste:** `scripts/ensaio_da_noite.py::ensaio_pendente_cancelado_pela_fila_e_refeito`

## F22 · Despachante mudo: cron pulado, reserva não refez

- **Noite:** 2026-10-08→2026-10-09
- **Sintoma:** Não houve run do despachante entre 00:29 e 06:43 nem do vigia depois de 01:10; os diários só foram redisparados à mão, às 02:32.
- **Causa:** Três dos quatro observadores do despachante dependiam do cron do GitHub, que pulou 01:07, 01:27, 01:47, 02:07 e 02:27, e o `relogio.yml` declarado não existia.
- **Prova:** redisparo de 02:32 com triggering_actor do dono do repositório; Relógio da nuvem rodou 01:08 e 02:08 sem redisparar
- **Correção:** PR #612 (`relogio.yml`: push no ramo `relogio` chama o despachante)
- **Caso de teste:** `scripts/ensaio_da_noite.py::ensaio_despachante_nao_depende_do_cron`

## F23 · Perda de push no passo 1a

- **Noite:** 2026-10-08→2026-10-09
- **Sintoma:** Os diários coletaram de 02:33 a 04:24 e o passo "Commit com rebase-e-push (item 1a)" falhou em 11 s; o juiz das 04:27 também; os artefatos ficaram sem reaplicação até o dia seguinte.
- **Causa:** A `main` andou durante a coleta (merges e publicações) e a união pela base comum não cobriu o conflito; `reaplicar_noite.py` existia e nada o chamava.
- **Prova:** run 37875038703 (coleta-perdida-diarios-37875038703, 18,7 MB); run 37883961718 (coleta-perdida-juiz-37883961718, 18,7 MB)
- **Correção:** PR #612 (todo elo reaplica no começo; artefatos de 08→09 reaplicados)
- **Caso de teste:** `scripts/ensaio_da_noite.py::ensaio_coleta_perdida_volta_para_dentro`

## F24 · `.feito` perdido junto com o push

- **Noite:** 2026-10-08→2026-10-09
- **Sintoma:** Diários e juiz trabalharam, mas a `main` ficou sem `diarios.feito` e sem o `juiz.feito` novo.
- **Causa:** O marcador era gravado na árvore e chegava à `main` no mesmo commit do dado, então morreu com o push perdido.
- **Prova:** run 37875038703; run 37883961718; data/noite/2026-10-09 só com juiz.feito e sinais-fisicos.feito às 06:05
- **Correção:** PR #612 (artefato `feito-<elo>-<noite>` antes do commit; dono `scripts/marcador_de_elo.py`)
- **Caso de teste:** `scripts/ensaio_da_noite.py::ensaio_marcador_sobrevive_ao_push`

## F25 · `main` vermelha no portão de layout durante a noite

- **Noite:** 2026-10-09
- **Sintoma:** "Portões" no push da `main` reprovou em todo push de 02:57 a 06:06 UTC, no portão de layout.
- **Causa:** O cartão de atos federais do Financiamento dizia "sem coleta" sobre uma série em disco cuja origem não data os atos, ausência de outra classe.
- **Prova:** 83db187 (#598); e4a718e (#599); f5f7850 (#600); 28e88c5 (#602); 9a72f76
- **Correção:** PR #604 (classe `sem_data_na_origem`)
- **Caso de teste:** `scripts/verificar_financiamento_coerencia.py --autoteste: classe de ausencia declarada passa, e sem exigir periodo`

## F26 · Diários cancelados na fila e contados pelo despachante

- **Noite:** 2026-10-09→2026-10-10
- **Sintoma:** `diarios / coletar` ficou na fila de 01:10:45 a 01:14:44 e foi cancelado sem passo; o despachante das 02:26 não redisparou, e os diários só rodaram às 07:42, com commit às 09:11.
- **Causa:** Pendente substituído no grupo de concorrência `noturno`, e o despachante contava run cancelado como execução da janela.
- **Prova:** run 38012085139; descoberta 38012418805 skipped
- **Correção:** PR #627: grupo `noturno-<elo>`, fila por ordem de chegada (`scripts/vez_na_noite.py`) e reserva dos elos no despachante
- **Caso de teste:** `scripts/ensaio_da_noite.py::ensaio_pendente_cancelado_pela_fila_e_refeito`

## F27 · Triagem duplicada por `workflow_run`

- **Noite:** 2026-10-09→2026-10-10
- **Sintoma:** Além da triagem por disparo manual, que rodou de 01:10 a 01:35, uma segunda triagem por `workflow_run` entrou na fila e foi cancelada sem passo.
- **Causa:** A triagem tem dois gatilhos na mesma noite (disparo do despachante e término dos sinais físicos) e nada impede a segunda; o cancelamento veio da fila do grupo.
- **Prova:** run 38012414909 (workflow_run, cancelada); run 38012115315 (dispatch, success)
- **Correção:** PR #627 (grupo por elo: a duplicata da triagem não cancela outro elo; a vez serializa)
- **Caso de teste:** nenhum — falta: Nenhum caso reprova dois runs do mesmo elo na mesma noite por gatilhos diferentes; falta um ensaio em que o segundo saia sem trabalho quando o primeiro já gravou `.feito`.

## F28 · Portões vermelhos no push às 01:12 e 01:14

- **Noite:** 2026-10-09→2026-10-10
- **Sintoma:** Dois runs de "Portões" no push da `main` falharam na abertura da noite.
- **Causa:** Não diagnosticada nas notas.
- **Prova:** run 38012291473; run 38012410116
- **Correção:** nenhuma registrada
- **Caso de teste:** nenhum — falta: Falta o diagnóstico (portão e saída) antes de se poder escrever o caso.

## F29 · Descoberta e evidências sem `.feito`

- **Noite:** 2026-10-09→2026-10-10
- **Sintoma:** Descoberta (07:43 e 09:12) e evidências (09:14 e 09:16) rodaram e não gravaram marcador em `data/noite/2026-10-10/`.
- **Causa:** Os dois esperaram no grupo atrás dos diários (que só rodaram às 07:42) e chegaram à coleta depois das 09:00 UTC, quando a guarda da janela adia a coleta na `main`.
- **Prova:** balanço da central de 10/10 09:30 UTC
- **Correção:** PR #627 (reserva dos elos refaz dentro da janela o elo sem `.feito`)
- **Caso de teste:** `scripts/despachar_temporizadores.py --autoteste: elo da corrente pulado só é refeito depois de o anterior ter trabalhado`

## F30 · Portões vermelhos após o commit dos diários

- **Noite:** 2026-10-10
- **Sintoma:** "Portões" no push da `main` reprovou desde 09:12 no passo de dado e coleta, depois do commit dos diários.
- **Causa:** Em `coletar_s2id.py` o canal do DOU decidia por chaves montadas antes de o MIDR gravar na mesma rodada e reacrescentou 44 reconhecimentos federais (mesma portaria, `http` × `https`).
- **Prova:** `verificar_consistencia.py` vermelho desde 09:12; `atos_resposta.json` 1122 → 1078; push 20272a72 verde às 10:59
- **Correção:** PR #626 (`incorporar_ato_dou` em `coletar_s2id.py`)
- **Caso de teste:** `coletar_s2id.py --autoteste: o DOU não reacrescenta o que o MIDR acabou de acrescentar`

## F31 · Artefato do marcador nunca existiu

- **Noite:** 2026-10-10
- **Sintoma:** O artefato `feito-<elo>-<noite>` saía como `feito-<elo>-` com caminho `data/noite//<elo>.feito`, ou seja, não subia; a segunda prova do marcador nunca funcionou.
- **Causa:** O passo de upload lia `env.NOITE`, e o passo que grava o marcador não exportava `NOITE` para `$GITHUB_ENV`.
- **Prova:** comentário de 10/10 em `.github/workflows/_coletor.yml`
- **Correção:** PR #627 (`echo "NOITE=$NOITE" >> "$GITHUB_ENV"`)
- **Caso de teste:** `scripts/ensaio_da_noite.py::ensaio_env_usada_e_exportada`

## F32 · Elo fora da `main` empurrava para a `main`

- **Noite:** 2026-10-10
- **Sintoma:** Um elo disparado no ramo `ensaio` (ou em qualquer ramo) partia da `main` e empurrava `HEAD:main`; como a guarda da janela não barra fora da `main`, o commit chegaria à `main` de dia.
- **Causa:** `_coletor.yml` fazia `git fetch ... main` + `git push ... HEAD:main` sem olhar o ramo do disparo.
- **Prova:** `.github/workflows/_coletor.yml`, passo "Commit com rebase-e-push" (achado ao desenhar o ensaio real, 10/10); F15 (corrente da `main` disparada pelo ramo de ensaio, 06→07/10)
- **Correção:** PR #632 (o passo de commit não empurra para a `main` fora dela) e PR do ensaio real (cada ramo `ensaio/` empurra para si mesmo)
- **Caso de teste:** `scripts/ensaio_da_noite.py::ensaio_fora_da_main_nao_empurra`
