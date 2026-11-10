"""Os arquivos que o Git rastreia: o que a CI vê e o que o deploy publica. Uma função só.

10/11/2026: eram seis cópias de `git ls-files` espalhadas pelos portões, e um `rglob` em
`validar_workflows.py` que contava as cópias de trabalho locais (`.claude/worktrees/…`) — o portão
reprovava a máquina, não o repositório. Quem precisa da lista de arquivos do repositório chama esta.
"""
from __future__ import annotations

import pathlib
import subprocess

RAIZ = pathlib.Path(__file__).resolve().parent.parent
FORA = ("arquivo", "node_modules", "evidencias")


def versionados(*padroes: str, fora=FORA, raiz=RAIZ) -> list:
    """Caminhos relativos (POSIX) rastreados pelo Git que casam com `padroes` e existem no disco,
    sem os que caem sob uma pasta de `fora` em qualquer nível. Sem padrão, todos."""
    saida = subprocess.run(["git", "ls-files", "-z", "--", *padroes], cwd=raiz,
                           capture_output=True, text=True, check=True).stdout
    return sorted(r for r in saida.split("\0")
                  if r and not set(pathlib.PurePosixPath(r).parts[:-1]) & set(fora) and (raiz / r).is_file())


def _autoteste() -> int:
    py = versionados("*.py")
    casos = [("acha um script rastreado", "scripts/gerar_codemap.py" in py),
             ("nada de cópia local de trabalho", not any(r.startswith(".claude/worktrees/") for r in py)),
             ("pasta de fora sai em qualquer nível", not any("node_modules" in r.split("/")[:-1] for r in versionados()))]
    for nome, ok in casos:
        print(("  ✓ " if ok else "  ✗ ") + nome)
    falhas = sum(not ok for _, ok in casos)
    print(f"✓ AUTOTESTE OK — {len(casos)} casos" if not falhas else f"✗ AUTOTESTE: {falhas} falha(s)")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(_autoteste())
