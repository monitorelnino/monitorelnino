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
MODO="${1:-git}"
export SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-$(python3 -c "import json,datetime;d=json.load(open('data/meta.json'))['corte'];dd,mm,aa=d.split('/');print(int(datetime.datetime(int(aa),int(mm),int(dd)).timestamp()))")}"
python3 recalcular_mare.py --write >/dev/null
python3 gerar_feeds.py >/dev/null
python3 gerar_dados_abertos.py >/dev/null
python3 gerar_pdf_indice.py >/dev/null
python3 gerar_pdf_metodologia.py >/dev/null
python3 scripts/gerar_manifesto.py >/dev/null
if [ "$MODO" = "--idempotencia" ]; then
  ANTES="$(git ls-files -z | xargs -0 sha256sum 2>/dev/null | sha256sum)"
  python3 recalcular_mare.py --write >/dev/null; python3 gerar_feeds.py >/dev/null; python3 gerar_dados_abertos.py >/dev/null
  python3 gerar_pdf_indice.py >/dev/null; python3 gerar_pdf_metodologia.py >/dev/null; python3 scripts/gerar_manifesto.py >/dev/null
  DEPOIS="$(git ls-files -z | xargs -0 sha256sum 2>/dev/null | sha256sum)"
  if [ "$ANTES" = "$DEPOIS" ]; then echo "✓ DERIVADOS OK — cadeia canônica idempotente nesta rodada (segunda regeneração não alterou nada)."; exit 0
  else echo "✗ DERIVADOS: a segunda regeneração alterou arquivos — derivado não determinístico ou ordem errada no pipeline."; exit 1; fi
fi
if git diff --quiet --exit-code -- . ':!data/snapshot_feed.json'; then
  echo "✓ DERIVADOS OK — cadeia canônica regenerada em árvore limpa sem diferença (índice, selos, feeds, dados abertos, PDFs, manifesto)."
else
  echo "✗ DERIVADOS: a regeneração alterou arquivos versionados — havia derivado obsoleto:"; git diff --stat -- . ':!data/snapshot_feed.json' | tail -8; exit 1
fi
