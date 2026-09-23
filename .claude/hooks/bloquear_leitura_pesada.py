#!/usr/bin/env python3
"""PreToolUse: impede Read em arquivo grande de data/ (§167, 23/09/2026).

MOTIVO, EM NÚMEROS. data/log_buscas.json tem 14 MB e data/fontes_consultadas.json tem 12 MB.
Um Read acidental em qualquer um dos dois estoura a sessão sozinho e não responde pergunta
nenhuma: o que se quer desses arquivos é sempre um agregado (quantas execuções por canal,
qual o último registro de tal UF), nunca o texto.

A regra já existia como texto no CLAUDE.md. Aqui ela vira impossibilidade, que é a diferença
entre uma boa intenção e um controle.

NÃO bloqueia Bash: `python3 -c` agregando é justamente o caminho certo, e a mensagem de
recusa ensina esse caminho em vez de só negar.
"""
import json
import sys
from pathlib import Path

TETO_BYTES = 1_000_000          # 1 MB: acima disso, agregue
RAIZ = Path(__file__).resolve().parent.parent.parent


def main() -> int:
    try:
        ev = json.load(sys.stdin)
    except Exception:  # noqa: BLE001
        return 0
    if ev.get("tool_name") != "Read":
        return 0
    alvo = (ev.get("tool_input") or {}).get("file_path") or ""
    p = Path(alvo)
    if not p.is_absolute():
        p = RAIZ / alvo
    try:
        tamanho = p.stat().st_size
    except OSError:
        return 0
    # Só vale para dados do projeto: código grande continua legível.
    try:
        rel = p.resolve().relative_to(RAIZ)
    except ValueError:
        return 0
    if rel.parts and rel.parts[0] in ("data", "dados-abertos", "evidencias") and tamanho > TETO_BYTES:
        mb = tamanho / 1_000_000
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                f"{rel} tem {mb:.1f} MB — ler inteiro gasta contexto sem responder nada. "
                f"Consulte agregando, por exemplo:\n"
                f"  python3 -c \"import json,collections; d=json.load(open('{rel}')); "
                f"print(collections.Counter(...))\"")}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
