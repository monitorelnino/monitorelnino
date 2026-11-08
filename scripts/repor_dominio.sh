#!/usr/bin/env bash
# Repõe o site completo no domínio (deploy de produção, noindex, atrás de senha) quando
# `data/publicacao.json` declara dominio=senha. Único lugar que faz esse deploy: o publicador
# (depois do dado), a reposição manual e o vigia o chamam.
# Uso: scripts/repor_dominio.sh "<mensagem do deploy>" [--estrito] [--forcar]
#   --estrito: segredo ou modo errado reprova (sem ele, é aviso e sai 0)
#   --forcar:  ignora a janela de deploy (reposição manual pedida pela editoria)
# Sai 0 com "Deploy is live", com IGUAL (domínio já neste manifesto) ou ADIADO (janela fechada —
# /tmp/repor_relatorio.txt começa por ADIADO); 1 se o deploy falhar.
#
# 08/11/2026 — a janela: o Netlify cobra 15 créditos por deploy de produção (prévia custa zero), e o
# publicador fazia ~25 por dia; em 07/11 os créditos acabaram e o domínio congelou por 35 horas. O
# deploy só sai se o manifesto mudou desde o último que chegou ao ar E se a janela
# (JANELA_DEPLOY_HORAS, padrão 12) fechou — ~2 deploys/dia, ~60/mês. Quem decide é
# scripts/janela_de_deploy.py, lendo a lista de deploys do próprio Netlify (sem arquivo novo no
# repositório, sem escritor novo). O título do deploy carrega `manifesto=<hash>` para a próxima decisão.
set -u
MSG="${1:?uso: repor_dominio.sh <mensagem> [--estrito] [--forcar]}"; shift
ESTRITO=""; FORCAR=""
for a in "$@"; do [ "$a" = "--estrito" ] && ESTRITO="--estrito"; [ "$a" = "--forcar" ] && FORCAR="--forcar"; done
nada() { if [ "$ESTRITO" = "--estrito" ]; then echo "::error::$1"; exit 1; fi; echo "::warning::$1"; exit 0; }
MODO=$(python3 -c "import json;print(json.load(open('data/publicacao.json')).get('dominio',''))" 2>/dev/null || echo "")
echo "modo declarado em data/publicacao.json: '${MODO}'"
[ "$MODO" = "senha" ] || nada "Domínio não está em modo senha — nada a repor."
{ [ -n "${PREVIA_BASIC_AUTH:-}" ] && [ -n "${NETLIFY_AUTH_TOKEN:-}" ]; } || nada "Segredo ausente (PREVIA_BASIC_AUTH ou NETLIFY_AUTH_TOKEN) — domínio fica como está."

MANIFESTO=$(sha256sum docs/MANIFEST_SHA256.txt | cut -c1-12)
if [ "$FORCAR" != "--forcar" ]; then
  npx --yes netlify-cli@17 api listSiteDeploys --data "{\"site_id\":\"${NETLIFY_SITE_ID:-}\",\"per_page\":20}" > /tmp/deploys.json 2>/dev/null || echo "[]" > /tmp/deploys.json
  DECISAO=$(python3 scripts/janela_de_deploy.py --manifesto "$MANIFESTO" --janela-horas "${JANELA_DEPLOY_HORAS:-12}" < /tmp/deploys.json)
  echo "janela de deploy: $DECISAO (manifesto da main: $MANIFESTO)" | tee /tmp/repor_relatorio.txt
  case "$DECISAO" in
    IGUAL*)  echo "Domínio já serve este manifesto — nada a repor."; exit 0;;
    ADIADO*) echo "$DECISAO" > /tmp/repor_relatorio.txt; echo "::notice::Deploy adiado: a janela do último deploy de produção ainda não fechou (${DECISAO#ADIADO }). O próximo publicador repõe."; exit 0;;
  esac
fi

printf '/*\n  Basic-Auth: %s\n  X-Robots-Tag: noindex, nofollow\n' "$PREVIA_BASIC_AUTH" > _headers
printf 'User-agent: *\nDisallow: /\n' > robots.txt
npx --yes netlify-cli@17 deploy --prod --dir=. --message "$MSG · manifesto=$MANIFESTO" > /tmp/repor_out.txt 2>&1
CODIGO=$?
rm -f _headers; git checkout -- robots.txt 2>/dev/null
RELATORIO=$(echo "codigo_saida=$CODIGO"; grep -vE "npm warn" /tmp/repor_out.txt | grep -E "Error|error|422|Deploy is live|Website URL" | head -c 1200)
echo "$RELATORIO" | sed "s/${NETLIFY_AUTH_TOKEN}/[TOKEN]/g; s/${PREVIA_BASIC_AUTH}/[SENHA]/g" | tee /tmp/repor_relatorio.txt
# 11/10/2026 (F42): sem "Deploy is live" é vermelho, nunca aviso.
grep -q "Deploy is live" /tmp/repor_relatorio.txt || { echo "::error::Reposição do domínio falhou (sem 'Deploy is live') — ver o relatório acima."; exit 1; }
echo "Domínio reposto com o site completo, atrás de senha."
