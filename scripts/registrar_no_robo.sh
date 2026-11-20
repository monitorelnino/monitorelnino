#!/usr/bin/env bash
# Grava relatórios de workflow em robo-registro/relatorios/<carimbo>_<nome>.txt.
# Uso: ROBO_TOKEN=… bash scripts/registrar_no_robo.sh "<mensagem>" <nome>=<arquivo> …  (arquivo ausente é pulado)
# Um só escritor de relatório para todos os workflows; o push tenta de novo com rebase porque
# vários workflows escrevem ao mesmo tempo ("fetch first": run 38074123643, 10/10; portões, 20/11).
set -u
msg=$1; shift
d=$(mktemp -d); carimbo=$(date -u +%Y-%m-%d_%H%M%S)
git clone -q --depth 1 "https://x-access-token:${ROBO_TOKEN}@github.com/monitorelnino/robo-registro.git" "$d" || exit 1
mkdir -p "$d/relatorios"
for par in "$@"; do [ -f "${par#*=}" ] && cp "${par#*=}" "$d/relatorios/${carimbo}_${par%%=*}.txt"; done
cd "$d" && git config user.name monitor-el-nino-bot && git config user.email bot@users.noreply.github.com
git add -A && git commit -q -m "$msg" >/dev/null || { echo "nada novo para registrar"; exit 0; }
for i in 1 2 3 4 5; do git push -q 2>/dev/null && exit 0; sleep $((i * 2 + RANDOM % 5)); git pull -q --rebase; done
exit 1
