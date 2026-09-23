#!/usr/bin/env python3
"""PostToolUse: roda o --autoteste do script recém-editado (§167, 23/09/2026).

Achado de 23/09/2026: a primeira versão do autoteste de coletar_painel_am.py batia na rede e
sujava data/log_buscas.json a cada execução do portão. Descobri isso por acaso, olhando o
git status. Um autoteste que roda no instante da edição transforma esse "por acaso" em
retorno imediato — e é barato, porque autoteste de coletor é offline e leva menos de um
segundo.

Só dispara para script Python da raiz que DECLARA --autoteste. Nunca falha a edição: o
resultado volta como contexto, não como bloqueio, porque editar um arquivo no meio de uma
refatoração pode legitimamente deixá-lo vermelho por um instante.
"""
import json
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent


def main() -> int:
    try:
        ev = json.load(sys.stdin)
    except Exception:  # noqa: BLE001
        return 0
    entrada = ev.get("tool_input") or {}
    resposta = ev.get("tool_response") or {}
    alvo = resposta.get("filePath") or entrada.get("file_path") or ""
    p = Path(alvo)
    if not p.is_absolute():
        p = RAIZ / alvo
    try:
        rel = p.resolve().relative_to(RAIZ)
    except (ValueError, OSError):
        return 0
    # Só script da raiz (os coletores), não os de scripts/ nem os de teste.
    if p.suffix != ".py" or len(rel.parts) != 1:
        return 0
    try:
        if "--autoteste" not in p.read_text(encoding="utf-8", errors="ignore"):
            return 0
    except OSError:
        return 0

    r = subprocess.run([sys.executable, str(p), "--autoteste"], cwd=RAIZ,
                       capture_output=True, text=True, timeout=120)
    linhas = [x for x in ((r.stdout or "") + (r.stderr or "")).splitlines() if x.strip()]
    veredito = linhas[-1] if linhas else "(sem saída)"
    if r.returncode == 0:
        print(json.dumps({"suppressOutput": True,
                          "systemMessage": f"{rel} --autoteste: {veredito}"}, ensure_ascii=False))
    else:
        falhas = [x for x in linhas if x.strip().startswith("✗")][:6]
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": (f"O autoteste de {rel} está VERMELHO após esta edição:\n"
                                  + "\n".join(falhas) + f"\n{veredito}")}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
