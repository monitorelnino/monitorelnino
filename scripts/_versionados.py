"""Os arquivos que o Git rastreia: o que a CI vê e o que o deploy publica. Uma função só.

10/11/2026: eram seis cópias de `git ls-files` espalhadas pelos portões, e um `rglob` em
`validar_workflows.py` que contava as cópias de trabalho locais (`.claude/worktrees/…`) — o portão
reprovava a máquina, não o repositório. Quem precisa da lista de arquivos do repositório chama esta.
"""
from __future__ import annotations

import fnmatch
import pathlib
import subprocess

RAIZ = pathlib.Path(__file__).resolve().parent.parent
FORA = ("arquivo", "node_modules", "evidencias")


def versionados(*padroes: str, fora=FORA, raiz=RAIZ) -> list:
    """Caminhos relativos (POSIX) rastreados pelo Git que casam com `padroes` e existem no disco,
    sem os que caem sob uma pasta de `fora` em qualquer nível. Sem padrão, todos."""
    try:
        saida = subprocess.run(["git", "ls-files", "-z", "--", *padroes], cwd=raiz,
                               capture_output=True, text=True, check=True).stdout.split("\0")
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Cópia sem Git (o ensaio de robustez roda os portões numa pasta temporária): a árvore inteira,
        # sem pastas ocultas além de `.github`, que é o que uma cópia sem Git tem de versionado.
        saida = [r for r in (q.relative_to(raiz).as_posix() for q in raiz.rglob("*") if q.is_file())
                 if not any(x.startswith(".") and x != ".github" for x in r.split("/")[:-1])
                 and (not padroes or any(fnmatch.fnmatch(r, pd) for pd in padroes))]
    return sorted(r for r in saida
                  if r and not set(pathlib.PurePosixPath(r).parts[:-1]) & set(fora) and (raiz / r).is_file())


def _autoteste() -> int:
    py = versionados("*.py")
    casos = [("acha um script rastreado", "scripts/gerar_codemap.py" in py),
             ("nada de cópia local de trabalho", not any(r.startswith(".claude/worktrees/") for r in py)),
             ("pasta de fora sai em qualquer nível", not any("node_modules" in r.split("/")[:-1] for r in versionados()))]
    import tempfile
    with tempfile.TemporaryDirectory() as t:
        (pathlib.Path(t) / ".github" / "workflows").mkdir(parents=True)
        (pathlib.Path(t) / ".github" / "workflows" / "a.yml").write_text("x", encoding="utf-8", newline="\n")
        (pathlib.Path(t) / ".claude").mkdir()
        (pathlib.Path(t) / ".claude" / "b.py").write_text("x", encoding="utf-8", newline="\n")
        (pathlib.Path(t) / "c.py").write_text("x", encoding="utf-8", newline="\n")
        casos.append(("sem Git: a árvore, com .github e sem outras pastas ocultas",
                      versionados(".github/workflows/*.yml", "*.py", raiz=pathlib.Path(t)) == [".github/workflows/a.yml", "c.py"]))
    for nome, ok in casos:
        print(("  ✓ " if ok else "  ✗ ") + nome)
    falhas = sum(not ok for _, ok in casos)
    print(f"✓ AUTOTESTE OK — {len(casos)} casos" if not falhas else f"✗ AUTOTESTE: {falhas} falha(s)")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(_autoteste())
