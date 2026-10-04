#!/usr/bin/env bash
# Portão 12 — derivados reproduzíveis em árvore limpa (AUD-04, auditoria externa 02/09/2026).
# Regenera TODA a cadeia canônica (índice → selos → feeds → dados abertos → PDFs → manifesto)
# com relógio fixado no corte e exige `git diff --exit-code`: se algo mudar, um derivado
# publicado estava obsoleto e o portão bloqueia. Uso: bash scripts/verificar_derivados.sh
set -euo pipefail
cd "$(dirname "$0")/.."
# Modo --idempotencia (usado DENTRO da rotina, onde a árvore está suja com dados novos
# ainda não comitados): não compara com o git; regenera a cadeia e exige que uma
# SEGUNDA regeneração não mude nada (derivados são função pura dos dados desta rodada).
# Modo --pode-regenerar (30/09/2026, §314, item 2 do handover de otimização): usado NO PR. Ele
# regenera a cadeia inteira e falha só se um GERADOR quebrar — não compara com o git.
#
# Por quê: o manifesto sela o hash de todo arquivo versionado, então qualquer mudança o deixa
# obsoleto. Cobrar isso dentro do PR forçava "regenerar + commitar + esperar a CI de novo" em quase
# toda entrega, e o manifesto commitado no ramo conflitava com o do `main` a cada união.
#
# O que NÃO se afrouxa: a checagem estrita (`git`) continua rodando onde o dado é selado — no push
# para a `main`. Derivado obsoleto continua sendo bloqueio; mudou ONDE se cobra, não SE se cobra.
MODO="${1:-git}"
export SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-$(python3 -c "import json,datetime;d=json.load(open('data/meta.json'))['corte'];dd,mm,aa=d.split('/');print(int(datetime.datetime(int(aa),int(mm),int(dd),tzinfo=datetime.timezone.utc).timestamp()))")}"
python3 recalcular_mare.py --write >/dev/null
python3 gerar_monitor_saude.py >/dev/null
python3 gerar_resposta.py >/dev/null
python3 gerar_prioritarios.py >/dev/null
python3 gerar_contadores_financiamento.py >/dev/null
python3 gerar_feeds.py >/dev/null
python3 gerar_dados_abertos.py >/dev/null
python3 scripts/gerar_enquadramento_card.py >/dev/null   # PR 4: enquadramento federal enxuto para o cartão
python3 gerar_card_municipios.py >/dev/null   # §155: card por município (prioritário, situação, pistas de imprensa)
python3 gerar_pdf_indice.py >/dev/null
python3 gerar_pdf_metodologia.py >/dev/null
python3 scripts/carimbar_assets.py >/dev/null
python3 gerar_blog.py >/dev/null   # 22/09/2026: depois do carimbo (as páginas dos textos copiam o cabeçalho carimbado de blog.html)
python3 scripts/gerar_resumo_do_log.py >/dev/null   # item 4: resumo do log para a página (o log inteiro não vai ao navegador)
# 28/09/2026 (§273): `scripts/gerar_saude_pipeline.py` SAIU desta cadeia. O painel é relatório da
# execução em curso, não função do dado commitado: o passo que recalcula o índice grava a própria linha
# de saúde, e a regeneração seguinte encontra o painel diferente do commitado. Na primeira execução real
# do `publicar_dados.yml` isso reprovou o portão 12 — corretamente, porque um derivado que muda durante
# a própria rodada não pode ser cobrado por "regenerar não altera nada". O painel agora é gerado no
# passo anterior ao commit, junto com o dado que ele resume.
python3 scripts/gerar_manifesto.py >/dev/null
if [ "$MODO" = "--idempotencia" ]; then
  ANTES="$(git ls-files -z | xargs -0 sha256sum 2>/dev/null | sha256sum)"
  python3 recalcular_mare.py --write >/dev/null; python3 gerar_monitor_saude.py >/dev/null; python3 gerar_resposta.py >/dev/null; python3 gerar_prioritarios.py >/dev/null; python3 gerar_contadores_financiamento.py >/dev/null; python3 gerar_feeds.py >/dev/null; python3 gerar_dados_abertos.py >/dev/null; python3 gerar_card_municipios.py >/dev/null; python3 scripts/gerar_enquadramento_card.py >/dev/null
  python3 gerar_pdf_indice.py >/dev/null; python3 gerar_pdf_metodologia.py >/dev/null; python3 scripts/carimbar_assets.py >/dev/null; python3 gerar_blog.py >/dev/null; python3 scripts/gerar_resumo_do_log.py >/dev/null; python3 scripts/gerar_manifesto.py >/dev/null
  python3 gerar_pdf_indice.py >/dev/null; python3 gerar_pdf_metodologia.py >/dev/null; python3 scripts/carimbar_assets.py >/dev/null; python3 gerar_blog.py >/dev/null; python3 scripts/gerar_manifesto.py >/dev/null
  DEPOIS="$(git ls-files -z | xargs -0 sha256sum 2>/dev/null | sha256sum)"
  if [ "$ANTES" = "$DEPOIS" ]; then echo "✓ DERIVADOS OK — cadeia canônica idempotente nesta rodada (segunda regeneração não alterou nada)."; exit 0
  else echo "✗ DERIVADOS: a segunda regeneração alterou arquivos — derivado não determinístico ou ordem errada no pipeline."; exit 1; fi
fi
# 04/10/2026 — O MODO DO PUBLICADOR.
#
# Medido: a publicação das 07:41 e das 08:05 UTC morreu no portão 12 com 49 derivados obsoletos
# (selos, índice, feeds), e o passo de commit do publicador havia dito "sem alterações a publicar".
# As duas coisas juntas revelam o buraco: o publicador regenerava a cadeia em `--idempotencia`, que
# mede se DUAS regenerações seguidas dão o mesmo resultado — determinismo —, e não se o resultado
# bate com o que está no git. Partindo de árvore limpa, as duas passavam; a árvore ficava igual ao
# commit anterior; o commit não via nada para publicar; e então a SUÍTE rodava a cadeia em modo
# estrito e achava os 49. O publicador reprovava a si mesmo.
#
# Este modo é o que ele precisa: regenera a cadeia inteira e sai 0, sem comparar com nada. Quem
# compara é a suíte, depois do commit — que é a ordem desenhada em 28/09 (commit local antes da
# suíte, push condicionado a ela). Nome explícito para que a escolha fique legível no workflow.
if [ "$MODO" = "--regenerar-para-commit" ]; then
  echo "✓ DERIVADOS — cadeia canônica regenerada para o commit do publicador. A comparação com o"
  echo "  git é da suíte, que roda depois do commit."
  exit 0
fi
if [ "$MODO" = "--pode-regenerar" ]; then
  # 04/10/2026: o modo do PR deixa de ser cego para o MANIFESTO.
  #
  # O §314 afrouxou a comparação no PR para não cobrar derivado de dado que a noite ainda vai
  # mudar — e isso continua certo. Mas o manifesto é outra coisa: ele é função dos ARQUIVOS DO
  # PR, não do dado da noite. PR que toca arquivo selado e não resela deixa a `main` vermelha no
  # push, e foi o que aconteceu quatro vezes entre 03 e 04/10 (#538, #541 e duas no publicador).
  # Cada uma custou um ciclo de CI e um PR de uma linha só para carimbar.
  #
  # Então aqui o manifesto é cobrado, e só ele: se estiver obsoleto, reprova no PR, onde o
  # conserto é `git add docs/MANIFEST_SHA256.txt` no mesmo commit.
  if ! git diff --quiet --exit-code -- docs/MANIFEST_SHA256.txt; then
    echo "✗ DERIVADOS: o manifesto está obsoleto. A cadeia regenerou e ele mudou, o que significa"
    echo "  que este PR toca arquivo selado e não reselou. Rode:"
    echo "      bash scripts/verificar_derivados.sh && git add docs/MANIFEST_SHA256.txt"
    echo "  e inclua no commit. Sem isso a \`main\` fica vermelha no push (§314 afrouxa o derivado"
    echo "  de DADO no PR, não o manifesto, que é função dos arquivos do próprio PR)."
    exit 1
  fi
  echo "✓ DERIVADOS OK — a cadeia canônica inteira regenerou sem erro e o manifesto está em dia."
  echo "  A comparação do resto com o git é do push para a \`main\` (§314)."
  exit 0
fi
# 03/10/2026: `data/saude_pipeline.json` e `docs/SAUDE_PIPELINE.md` saem da COMPARAÇÃO, não só da
# cadeia. O §273 tirou o gerador daqui, mas o painel continua mudando quando a cadeia roda — porque
# `recalcular_mare.py --write`, que é um passo da cadeia, grava a própria linha de execução no
# painel. Então uma árvore limpa fica suja pela regeneração, por desenho, e o portão cobrava
# "regenerar não altera nada" de um arquivo que registra a própria regeneração. Foi isso que
# reprovou o publicador duas vezes em 03/10. O painel é selado pelo passo que o gera, antes do
# commit, como o §273 determinou.
SEM_PAINEL=(':!data/snapshot_feed.json' ':!capturas-ci' ':!data/saude_pipeline.json'
            ':!docs/SAUDE_PIPELINE.md' ':!data/painel_da_noite.json')
if git diff --quiet --exit-code -- . "${SEM_PAINEL[@]}"; then
  echo "✓ DERIVADOS OK — cadeia canônica regenerada em árvore limpa sem diferença (índice, selos, feeds, dados abertos, PDFs, manifesto)."
else
  echo "✗ DERIVADOS: a regeneração alterou arquivos versionados — havia derivado obsoleto:"; git diff --stat -- . "${SEM_PAINEL[@]}" | tail -8; exit 1
fi
