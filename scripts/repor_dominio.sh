#!/usr/bin/env bash
# Repõe o site completo no domínio (deploy de produção, noindex, atrás de senha) quando
# `data/publicacao.json` declara dominio=senha. Único lugar que faz esse deploy: o publicador
# (depois do dado), a prévia (depois de merge de PR) e a reposição manual o chamam.
# Uso: scripts/repor_dominio.sh "<mensagem do deploy>" [--estrito]   (--estrito: segredo ou modo errado reprova)
# Sai 0 com "Deploy is live" ou quando nada há a repor; 1 se o deploy falhar.
set -u
MSG="${1:?uso: repor_dominio.sh <mensagem> [--estrito]}"; ESTRITO="${2:-}"
nada() { if [ "$ESTRITO" = "--estrito" ]; then echo "::error::$1"; exit 1; fi; echo "::warning::$1"; exit 0; }
MODO=$(python3 -c "import json;print(json.load(open('data/publicacao.json')).get('dominio',''))" 2>/dev/null || echo "")
echo "modo declarado em data/publicacao.json: '${MODO}'"
[ "$MODO" = "senha" ] || nada "Domínio não está em modo senha — nada a repor."
{ [ -n "${PREVIA_BASIC_AUTH:-}" ] && [ -n "${NETLIFY_AUTH_TOKEN:-}" ]; } || nada "Segredo ausente (PREVIA_BASIC_AUTH ou NETLIFY_AUTH_TOKEN) — domínio fica como está."
printf '/*\n  Basic-Auth: %s\n  X-Robots-Tag: noindex, nofollow\n' "$PREVIA_BASIC_AUTH" > _headers
printf 'User-agent: *\nDisallow: /\n' > robots.txt
npx --yes netlify-cli@17 deploy --prod --dir=. --message "$MSG" > /tmp/repor_out.txt 2>&1
CODIGO=$?
rm -f _headers; git checkout -- robots.txt 2>/dev/null
RELATORIO=$(echo "codigo_saida=$CODIGO"; grep -vE "npm warn" /tmp/repor_out.txt | grep -E "Error|error|422|Deploy is live|Website URL" | head -c 1200)
echo "$RELATORIO" | sed "s/${NETLIFY_AUTH_TOKEN}/[TOKEN]/g; s/${PREVIA_BASIC_AUTH}/[SENHA]/g" | tee /tmp/repor_relatorio.txt
# 11/10/2026 (F42): sem "Deploy is live" é vermelho, nunca aviso.
grep -q "Deploy is live" /tmp/repor_relatorio.txt || { echo "::error::Reposição do domínio falhou (sem 'Deploy is live') — ver o relatório acima."; exit 1; }
echo "Domínio reposto com o site completo, atrás de senha."
