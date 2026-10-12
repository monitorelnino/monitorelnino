#!/usr/bin/env bash
# A7-23 (12/10/2026): liga os hooks versionados em `.githooks/` neste clone. Idempotente.
set -e
cd "$(dirname "$0")/.."
git config core.hooksPath .githooks
echo "hooks de git ligados: core.hooksPath=.githooks ($(ls .githooks | tr '\n' ' '))"
