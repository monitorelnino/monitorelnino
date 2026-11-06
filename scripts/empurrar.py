#!/usr/bin/env python3
"""Um push, com o nome certo da recusa.

Causa raiz (F79, ensaio real 42127323105): o laço de push dos elos escrevia "push recusado (main
avançou)" para toda recusa. Os cinco pushes do elo diários voltaram `fatal error in commit_refs` /
`[remote rejected] (failure)`, erro do servidor do GitHub: a main não andou, repetir logo em seguida
não ajuda, e o log culpava a corrida.

Uso: python3 scripts/empurrar.py DESTINO TENTATIVA   (o remoto vem de GIT_SSH_COMMAND/ambiente,
como nos workflows; `EMPURRAR_REMOTO` o substitui). Sai 0 se empurrou; senão nomeia a recusa,
espera (corrida: TENTATIVA×10 s; servidor: TENTATIVA×30 s) e sai 1.
"""
import os
import re
import subprocess
import sys
import time

SERVIDOR = re.compile(r"commit_refs|\[remote rejected\][^\n]*\(failure\)|\b5\d\d\b[^\n]*(error|erro)|"
                      r"internal server error|unexpected disconnect|The remote end hung up", re.I)


def classificar(saida: str) -> str:
    """'servidor' (falha do GitHub, não da corrida) ou 'corrida' (main avançou / não-fast-forward)."""
    return "servidor" if SERVIDOR.search(saida) else "corrida"


def empurrar(destino: str, tentativa: int, remoto: str) -> int:
    p = subprocess.run(["git", "push", remoto, f"HEAD:{destino}"], capture_output=True, text=True)
    sys.stderr.write(p.stdout + p.stderr)
    if p.returncode == 0:
        print(f"empurrado na tentativa {tentativa}")
        return 0
    tipo = classificar(p.stdout + p.stderr)
    if tipo == "servidor":
        print(f"tentativa {tentativa}: push recusado pelo servidor do GitHub (falha dele, a main não andou); "
              "espera maior e nova tentativa")
        time.sleep(tentativa * 30)
    else:
        print(f"tentativa {tentativa}: push recusado (main avançou); nova tentativa")
        time.sleep(tentativa * 10)
    return 1


def autoteste() -> int:
    casos = [("remote: fatal error in commit_refs\n ! [remote rejected] HEAD -> x (failure)", "servidor"),
             (" ! [remote rejected] HEAD -> x (failure)", "servidor"),
             ("error: RPC failed; HTTP 502 error", "servidor"),
             (" ! [rejected] HEAD -> x (fetch first)\nhint: Updates were rejected", "corrida"),
             (" ! [remote rejected] HEAD -> x (protected branch hook declined)", "corrida"),
             ("", "corrida")]
    ruins = [(s, e) for s, e in casos if classificar(s) != e]
    for s, e in ruins:
        print(f"✗ esperado {e}: {s!r}")
    print("empurrar.py autoteste:", "vermelho" if ruins else f"verde ({len(casos)} casos)")
    return 1 if ruins else 0


if __name__ == "__main__":
    if sys.argv[1:] == ["--autoteste"]:
        sys.exit(autoteste())
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    sys.exit(empurrar(sys.argv[1], int(sys.argv[2]), os.environ.get("EMPURRAR_REMOTO", f"git@github.com:{os.environ['GITHUB_REPOSITORY']}.git")))
