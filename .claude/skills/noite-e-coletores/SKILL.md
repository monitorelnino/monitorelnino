---
name: noite-e-coletores
description: As regras da corrente noturna do MARÉ — coleta, pistas, workflows, temporizadores e publicação — reunidas para quem vai tocar coletor, script de coleta, pista, fila, workflow do GitHub Actions, cron, temporizador, despachante, publicador ou portão de dado. Use SEMPRE antes de criar ou alterar qualquer `.py` que colete ou grave dado, qualquer arquivo em `.github/workflows/`, qualquer coisa que escreva em `data/`, e antes de mexer em cadência, janela da noite ou ordem dos elos. Use também ao diagnosticar noite que falhou, coleta perdida, conflito de rebase, publicação reprovada ou run cancelado. Esta skill não cria regra nenhuma: ela reúne o que já está decidido e diz qual portão reprova cada coisa.
---

# A corrente noturna e os coletores

Esta skill é um **índice de primeira ordem**, não uma fonte. Nada aqui é regra nova: tudo vem do
`CLAUDE.md` e dos handovers vigentes, e onde esta página e o documento divergirem, **vence o
documento**.

Cada regra abaixo tem um **portão que a reprova**, e isso não é decoração: regra sem portão volta a
ser esquecimento — foi assim que a noite de 04→05/10 acumulou quatro defeitos ao mesmo tempo.

## Por onde começar, pela tarefa

| vou mexer em… | leia aqui |
|---|---|
| coletor novo | **O coletor novo, de ponta a ponta** · **Acesso e recusa** · regra 1 |
| coletor existente | regra 1 · **Todo coletor novo ou alterado** |
| workflow, cron, elo da noite | regras 2, 3, 4 e 6 · **Temporizadores** |
| conflito de rebase, coleta perdida | **Log e fila** · regra 2 |
| publicação reprovada | regra 5 · **Publicação** |

## O coletor novo, de ponta a ponta

**Os campos que a pista precisa ter** (`schemas/pista.json`, obrigatórios — a porta recusa sem eles):

| campo | o que é |
|---|---|
| `url_final` | o endereço do **veículo ou do documento**, já resolvido. Redirecionador (Google News e afins) é recusado |
| `tipo` | `plano` · `estrutura` · `decreto` · `outro`. **`decreto` não entra na fila de planos** (vai à conferência da base oficial) e **`outro` é descartado com motivo** |
| `alvo` | código IBGE do município (7 dígitos) ou sigla da UF. Sem alvo identificável, descarta — "notícia sobre municípios" não é pista de município |
| `nivel` | `A` · `B` · `C`, pelo critério de confiança em uso |
| `data` | data do achado, em AAAA-MM-DD |
| `origem` | qual coletor gravou |

A porta deriva o que pode (`url` → `url_final`, `ibge` → `alvo`, `nivel_confianca` → `nivel`,
dd/mm/aaaa → AAAA-MM-DD) e **recusa com motivo** o resto. Opcionais e regras de teto, deduplicação e
dias de vida estão no mesmo arquivo.

**As três travas** (`.claude/agents/revisor-de-trava.md`; `descobrir_planos.py` é a referência):

1. **Estrutural** — nunca escreve em `estados.json`, `saude_uf.json`, `municipios.json`,
   `indice.json` nem `monitor_saude.json`, e há autoteste que lê o **próprio fonte** e reprova se
   aparecer escrita nesses arquivos.
2. **De campo** — todo item nasce com `documento_oficial_confirmado: null` e `promovivel: false`.
3. **De processo** — a saída vai para **fila própria**, nunca ao banco. Promoção é humana (R7).

**Entrar na noite**, quando o coletor passa a ser elo: declarar o que ele commita em
`config/escritores.json` (regra 2), registrar a cadência em `config/temporizadores.json`, e — se ele
for um elo da corrente, não um comando dentro de outro — gravar o marcador
`data/noite/<noite>/<elo>.feito` pelo invólucro `_coletor.yml`, que já faz isso por `inputs.nome`.
Coletor que roda **dentro** de um elo existente não precisa de marcador próprio: o elo tem o dele.

**Varredura longa**: `coletores_base` já traz o ritmo (`Crawl-delay` respeitado,
`_respeitar_ritmo`), o cliente identificado (`ua_de`), a busca com retomada
(`buscar_em_fluxo_confiavel`) e a preservação de evidência (`preservar_evidencia`, que grava em
`evidencias/` por hash e **redige segredo e dado pessoal antes do hash**). Use-os em vez de abrir
`urllib` na mão: é por eles que o rastro em `data/robots_registro.json` e o índice de evidências
ficam corretos.

## As seis regras permanentes (editoria, 05/10/2026)

**1 · Nenhum coletor grava pista fora de `scripts/pistas.py`.**
A fila tem uma porta. Ela normaliza para `schemas/pista.json` (`url` → `url_final` resolvido, `ibge` →
`alvo`, `nivel_confianca` → `nivel`, dd/mm/aaaa → AAAA-MM-DD), classifica o `tipo` e **recusa com
motivo** em `data/pistas_rejeitadas.json`, com origem e campo ausente.
Três entradas, por caso de uso:
- `gravar(pista, origem="", nome_da_fila=FILA_PADRAO)` — uma pista;
- `gravar_lote(novas, origem="", nome_da_fila=FILA_PADRAO, ler_fn=None, gravar_fn=None)` — a rodada
  inteira, **numa leitura e numa escrita**: `data/pistas_imprensa.json` passa de 25 MB, e chamar
  `gravar` por pista faria centenas de leituras do arquivo todo;
- `sincronizar(nome_da_fila, fila_em_memoria, origem="", ler_fn=None, gravar_fn=None)` — varredura de
  horas com salvamento parcial, idempotente.

`ler_fn`/`gravar_fn` têm padrão `None` e caem em `coletores_base`. **O coletor passa o seu próprio
par** (`ler_fn=ler, gravar_fn=gravar`) — é o que mantém o autoteste isolado; ver a seção dos
coletores, abaixo.
Operação sobre a fila **inteira** (limpeza, triagem, união de conflito) declara-se em `MANUTENCAO`,
por escrito, dentro do portão.
→ Portão: **`scripts/verificar_escritor_de_pista.py`**.

**2 · Um escritor por arquivo, ou uma resolução declarada.**
`config/escritores.json` diz, para cada arquivo compartilhado da corrente, quem pode commitá-lo.
Quando vários elos commitam o mesmo arquivo, a corrida tem de estar **resolvida** — uma classe de
`scripts/unir_conflito_de_rodada.py` — ou o arquivo declara `pendente` dizendo o que falta decidir.
→ Portão: **`scripts/verificar_escritores.py`**.

**3 · Cancelado e pulado nunca contam como feito.**
A guarda "esta noite já abriu?" conta só o run que **trabalhou**: `in_progress`, ou
`success`/`failure` com o marcador `data/noite/<noite>/<elo>.feito`, que o elo grava **depois dos
comandos de coleta e antes do commit**. A ordem é a regra: elo que coletou e perdeu o push trabalhou
(refazê-lo duplicaria lote e commit); elo cancelado antes de coletar não trabalhou, e a reserva
refaz. Quem decide é `painel_da_noite.trabalhou()`.

**4 · Nenhum script cancela run de outro.**
Grupo de concorrência é **fila**, não cancelamento: `cancel-in-progress: false` em todo elo. Só o
publicador cancela o anterior, porque publicar duas vezes o mesmo estado não tem valor. Cancelar é
decisão de quem está ao teclado.
→ Portão: **`scripts/validar_workflows.py`** (reprova `gh run cancel` e chamada `/cancel` na API).

**5 · O portão de esquema quarentena; ele não bloqueia a publicação.**
Pista fora do esquema sai da fila ativa pela mão do próprio portão, marcada e contável por coletor, e
a publicação segue. Bloqueio só quando a **quarentena falha** — aí o dado malformado seguiria a
caminho do juiz. Parar o site por sobra de coletor é desproporcional; deixar sobra ir ao índice, não.
→ Portão: **`scripts/verificar_esquema_de_pista.py`**.

**6 · Toda mudança na corrente noturna passa pelo ensaio da noite.**
`scripts/ensaio_da_noite.py` roda a noite em miniatura, de dia, em repositório temporário, sem tocar
a `main`, e fica vermelho quando qualquer uma das quatro causas de 04→05/10 volta. **Mudança na
corrente sem ensaio verde não entra.**
→ Portão: **`scripts/ensaio_da_noite.py`** + `.github/workflows/ensaio_da_noite.yml`.

## Log e fila: unir pela base comum, nunca por conteúdo

`data/log_buscas*`, `data/historico_mudancas.json`, `data/saude_pipeline.json` e as filas de pista
**só crescem**. Quando os dois lados acrescentam e o merge conflita:

- **Nunca deduplique por conteúdo.** Execuções idênticas são tentativas reais distintas e contam. Em
  23/09/2026 uma união por conteúdo produziu um log **menor** que cada lado e apagou quase 3.000
  execuções.
- Una pela **base comum**: `base + nossos_novos + deles_novos`, e confira que o total final é
  **maior ou igual** a cada lado.
- Nas **filas de pista**, a política é a da porta única: acréscimo dos dois lados entra, campo que só
  um lado tocou entra, **mesmo campo com valores diferentes é RECUSADO** em vez de adivinhado.
- `git rebase -X theirs` num arquivo de fila **não resolve, apaga**: ele escolhe um lado inteiro, e o
  lado perdedor são as pistas que o outro elo acabou de achar. Foi o que custou 114 minutos de busca
  web na noite de 04→05/10.

Use `python3 scripts/unir_conflito_de_rodada.py`, ou a skill `/merge-main`. Recusa do resolvedor é o
comportamento **certo** quando a política não está decidida: o elo desiste da tentativa e o trabalho
sai como **artefato do run**. Trabalho coletado nunca é descartado em silêncio.

## Todo coletor novo ou alterado

- **Três travas e um autoteste offline que não escreve em `data/`.** O subagente `revisor-de-trava`
  confere isso antes do PR.
- **O autoteste não pode escrever no banco.** Ele troca o `ler`/`gravar` **do próprio módulo** por
  falsos, e um ajudante que chame `coletores_base.gravar` passa **por fora** da troca. Isso já
  aconteceu duas vezes: apagou 907 atos em 02/10 e seis execuções do log em 05/10. Por isso
  `gravar_lote`, `sincronizar` e `rejeitar` recebem `ler_fn`/`gravar_fn`, e **cada coletor passa o seu
  par**.
  → Portão: **`scripts/verificar_autoteste_nao_escreve.py`** (10 coletores, 12 arquivos de banco).
- **Função pura não escreve e não vai à rede.** A trava estrutural do autoteste confere isso lendo o
  bytecode — é o padrão de todos os portões do projeto, e vale a pena copiar.

## Acesso, robôs e recusa

- `robots.txt` é **pedido, não tranca** (RFC 9309 §1.3; §185): o Monitor o lê, respeita o
  `Crawl-delay` e acessa documento público mesmo onde ele pede que robôs não entrem — com o cliente
  **identificado** e rastro em `data/robots_registro.json`. **Nunca disfarçar o cliente.**
- **Bloqueio de acesso real se respeita, sempre**: `401`, `403`, `429`, `451`, captcha, login.
- **Recusa servida com `200` é recusa** (§186, §187). Muro de robô (Imperva, Cloudflare, Akamai) e
  geobloqueio de WAF parecem conteúdo e entrariam no índice como **prova falsa**.
  `coletores_base.detectar_muro_de_robo` levanta antes de preservar.
- **Nunca nomeie a recusa errado**: chamar geobloqueio de `robots.txt` já custou treze dias de
  abstenção indevida.

## Temporizadores e cadência

- O princípio: **nada roda às 22h07; tudo roda quando está devido.** Quatro observadores independentes
  (cron, relógio da nuvem, tique oportunista, vigia), com idempotência por janela.
- O registro de temporizadores é `config/temporizadores.json`; quem despacha é
  `scripts/despachar_temporizadores.py`; quem confere é `scripts/verificar_temporizadores.py`; quem
  mostra é `scripts/painel_dos_temporizadores.py`.
- Regras do GitHub Actions que já custaram workflow rejeitado:
  - **`secrets` não existe no contexto de `if`** — a decisão vai para dentro do `run`;
  - **passo com `run` junto de `with` ou `uses` é inválido para o GitHub e válido para o YAML** —
    `actionlint` passa, e só o GitHub reprova, em silêncio, com o caminho no lugar do nome.
  → Portões: **`scripts/validar_workflows.py`** e **`scripts/verificar_workflow_aceito.py`** (este
  pergunta ao próprio GitHub).

## Dado que nunca entra em contexto

A lista com os tamanhos medidos está no **`CLAUDE.md`**, na tabela "Arquivos que nunca entram em
contexto" — e é lá que ela se consulta, porque número de tamanho envelhece por rotina. Em 05/10/2026
três linhas dela estavam erradas: `evidencias/` figurava como 380 MB e tem **4,1 GB**, e
`data/log_buscas/*.jsonl` (31 MB) e `data/pistas_imprensa.json` (26 MB) não estavam na tabela.

Os maiores hoje: `evidencias/` · `data/log_buscas/*.jsonl` · `data/pistas_imprensa.json` ·
`data/fontes_consultadas.json` · `data/financiamento/municipios/transferencias_uniao.json`.

Consulte **sempre agregando** (`python3 -c "import json,collections; ..."`), nunca com `Read`. Um
`Read` nos três maiores estoura a sessão sozinho; há hook que bloqueia acima de 1 MB em `data/`,
`dados-abertos/` e `evidencias/`. **Quem vir a tabela defasada, remede** — subestimar o tamanho é o
único erro dela que custa a sessão.

## Regras editoriais que o código não pode violar

- Nunca inventar dado. Ausência é **lacuna declarada**, com fonte.
- Teto público de ausência: **"não localizamos até o corte"** — nunca "não existe".
- **Zero, ausência de dado, dado indisponível e dado não coletado são coisas distintas.**
- Decreto (`categoria=decreto`) **não pontua** no índice; fica no banco para transparência.
- **Na dúvida, o classificador não classifica** — contribuição pública vai à revisão humana, e
  `tipo: outro` é recusado com motivo em vez de chutado.
- Mudança de pesos, créditos ou componentes do índice exige **versão maior** (`METODOLOGIA.md` §12).

## Publicação

- **Merge com portões verdes já autoriza publicar e republicar** o domínio, no regime vigente de
  cortina (senha + `noindex`). Não se espera resposta para publicar.
- **`data/publicacao.json` só muda por decisão da editoria** — indexação e regime do domínio.
- **A central (chat) não commita, não mescla e não publica.** Todo código e toda publicação passam
  pelo Code, a partir de handover.
- Repositório **público**: nunca commitar token, chave, senha ou `.env` preenchido. O acesso ao GitHub
  vem do login local. Material privado (LAI, notas jurídicas, diagnósticos) vive no repositório
  privado da editoria.
- **Preprint (T0–T11) não é rotina do site** e não se toca sem pedido explícito da editoria.

## Rodar os portões

```bash
python3 scripts/quais_portoes.py --comando     # só o que a mudança pode afetar
python3 scripts/portoes_locais.py dados        # sempre que tocar data/, *.py de coleta ou dependências
python3 scripts/ensaio_da_noite.py             # antes de qualquer mudança na corrente
```

Na dúvida, `tudo`. **Nada sobe com portão vermelho.** Para a suíte inteira sem gastar contexto, o
subagente `portoes-runner` devolve só o veredito e as falhas. Atalhos: `/portoes`, `/p12`
(derivado obsoleto), `/e-da-main` (a falha é minha ou já estava na `main`?), `/merge-main`, `/lote`.

## O relatório, que faz parte do trabalho

Ao concluir, **até 6 linhas**: o que mudou · verificação executada (portões, CI, testes, números com
fonte) · o que ficou sem solução · o que só a editoria decide.

Duas exigências que a corrente noturna acrescenta: dizer **com todas as letras o que passa a ser
garantido e como foi provado**, e declarar **o que ficou pendente com o motivo** — pendência sem
motivo volta como surpresa. Suposição não verificada nunca é apresentada como dado: o que não foi
verificado se diz "não verificado".

## Onde está cada decisão

| assunto | fonte |
|---|---|
| as seis regras, cadência, segurança, log append-only | `CLAUDE.md` |
| a lista canônica dos portões | `.github/workflows/portoes.yml` (`--listar` confere) |
| o esquema da pista | `schemas/pista.json` |
| quem commita cada arquivo | `config/escritores.json` |
| os temporizadores | `config/temporizadores.json` |
| que arquivo afeta que tela e que portão o cobre | `CODEMAP.md` |
| o que pode ser afirmado | `METODOLOGIA.md` |
| como a mudança entra no site | `docs/PROTOCOLO_ATUALIZACAO.md` §3 |
| a noite de 04→05/10 e o que ela consertou | `notas/ESTADO_ATUAL.md` **do repositório privado** da editoria (não há cópia aqui) |
