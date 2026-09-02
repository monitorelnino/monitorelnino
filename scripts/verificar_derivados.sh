#!/usr/bin/env bash
# Portão 12 — derivados reproduzíveis em árvore limpa (AUD-04, auditoria externa 02/09/2026).
# Regenera TODA a cadeia canônica (índice → selos → feeds → dados abertos → PDFs → manifesto)
# com relógio fixado no corte e exige `git diff --exit-code`: se algo mudar, um derivado
# publicado estava obsoleto e o portão bloqueia. Uso: bash scripts/verificar_derivados.sh
set -euo pipefail
cd "$(dirname "$0")/.."
export SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-$(python3 -c "import json,datetime;d=json.load(open('data/meta.json'))['corte'];dd,mm,aa=d.split('/');print(int(datetime.datetime(int(aa),int(mm),int(dd)).timestamp()))")}"
python3 recalcular_mare.py --write >/dev/null
python3 gerar_feeds.py >/dev/null
python3 gerar_dados_abertos.py >/dev/null
python3 gerar_pdf_indice.py >/dev/null
python3 gerar_pdf_metodologia.py >/dev/null
python3 scripts/gerar_manifesto.py >/dev/null
if git diff --quiet --exit-code -- . ':!data/snapshot_feed.json'; then
  echo "✓ DERIVADOS OK — cadeia canônica regenerada em árvore limpa sem diferença (índice, selos, feeds, dados abertos, PDFs, manifesto)."
else
  echo "✗ DERIVADOS: a regeneração alterou arquivos versionados — havia derivado obsoleto:"; git diff --stat -- . ':!data/snapshot_feed.json' | tail -8; exit 1
fi
