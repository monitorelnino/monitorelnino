#!/usr/bin/env python3
"""PreToolUse: arquivo derivado não se edita à mão (§167, 23/09/2026).

A regra é do CLAUDE.md e do PROTOCOLO: data/*.json, os feeds, os dados abertos e o manifesto
são REGERADOS pela cadeia canônica (scripts/verificar_derivados.sh), nunca escritos à mão.
Editar um deles direto produz um arquivo que o portão 12 vai desfazer — na melhor hipótese.
Na pior, entra no commit e o site publica um número que nenhum script sabe reproduzir.

Bloqueia só Edit/Write (a ferramenta de edição direta). Não bloqueia Bash: é por lá que os
geradores do projeto escrevem, e é assim que tem de ser.

Exceção declarada: as filas de PISTA (pistas_*.json) são escritas por coletor, mas também
recebem triagem humana item a item — por isso ficam de fora do bloqueio.
"""
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
DERIVADO = re.compile(r"^(data/.+\.json|dados-abertos/.+|feeds/.+\.xml|docs/MANIFEST_SHA256\.txt|selos/.+\.svg)$")
EXCECOES = re.compile(r"^data/(pistas_[\w-]+\.json|publicacao\.json)$")


def main() -> int:
    try:
        ev = json.load(sys.stdin)
    except Exception:  # noqa: BLE001
        return 0
    if ev.get("tool_name") not in ("Edit", "Write", "NotebookEdit"):
        return 0
    alvo = (ev.get("tool_input") or {}).get("file_path") or ""
    p = Path(alvo)
    if not p.is_absolute():
        p = RAIZ / alvo
    try:
        rel = p.resolve().relative_to(RAIZ).as_posix()
    except ValueError:
        return 0
    if DERIVADO.match(rel) and not EXCECOES.match(rel):
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                f"{rel} é arquivo DERIVADO — não se edita à mão (CLAUDE.md, PROTOCOLO §3.1).\n"
                "Altere a fonte e regenere: bash scripts/verificar_derivados.sh\n"
                "Dado novo entra por aplicar_revisao.py / converter_contribuicao.py, nunca "
                "por edição direta.")}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
