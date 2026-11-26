#!/usr/bin/env python3
"""A `main` aguardando selo (handover do selo, D4, 25/11/2026).

Os derivados que são função do repositório inteiro (`docs/MANIFEST_SHA256.txt`, `mudancas.html`,
`CODEMAP.md`) são selados pelo publicador, que regenera e commita tudo depois de cada merge (D3).
Entre o merge de um PR e a publicação seguinte, a `main` está AGUARDANDO SELO: o push do merge passa
com aviso, para que os portões fiquem verdes e disparem o publicador. Depois da publicação ela está
SELADA, e o derivado velho (inclusive o de commit de elo, F89) volta a reprovar.

Aguardando selo = há commit de merge de PR (committer `GitHub`) mais novo que o último commit do
publicador ("Publicação automática…"). Histórico raso sem publicação visível: decide o que se vê.
Onde se tolera (D1, D4, D7): no PR e na cópia de trabalho, sempre (o selo não é do PR); no push da
`main`, só aguardando selo. Nos outros eventos do Actions (publicador, elos) o portão é estrito.

    python3 scripts/selo_da_main.py DERIVADOS    # avisa e sai 0 se o portão deve tolerar; 1 se estrito
    python3 scripts/selo_da_main.py --autoteste
"""
from __future__ import annotations

import os
import subprocess
import sys

MERGE = "GitHub"
PUBLICACAO = "Publicação automática"


def aguardando_selo(commits) -> bool:
    """`commits`: pares (committer, assunto), do mais novo ao mais velho. Função pura."""
    for committer, assunto in commits:
        if assunto.startswith(PUBLICACAO):
            return False
        if committer == MERGE:
            return True
    return False


def historico(n: int = 200, cwd=None) -> list[tuple[str, str]]:
    r = subprocess.run(["git", "log", f"-n{n}", "--format=%cn%x1f%s"], cwd=cwd,
                       capture_output=True, text=True)
    return [tuple(l.split("\x1f", 1)) for l in r.stdout.splitlines() if "\x1f" in l]


def tolerante(cwd=None, amb=None) -> bool:
    amb = os.environ if amb is None else amb
    evento = amb.get("GITHUB_EVENT_NAME")
    if evento in (None, "", "pull_request"):
        return True
    return (evento == "push" and amb.get("GITHUB_REF") == "refs/heads/main"
            and aguardando_selo(historico(cwd=cwd)))


def avisar(o_que: str) -> None:
    print(f"::warning::{o_que}: o selo é do publicador (D1/D4); passa com aviso.")


def _autoteste() -> int:
    pub, bot, gh = ("monitor-el-nino-bot", "Publicação automática (25/11/2026 16:57 UTC)"), \
        ("monitor-el-nino-bot", "Noturno — sinais"), ("GitHub", "Selo na main (#2090)")
    casos = {
        "merge depois da publicação": ([gh, pub, gh], True),
        "publicação depois do merge": ([pub, gh, pub], False),
        "elo depois do merge, antes da publicação": ([bot, gh, pub], True),
        "só commits de elo": ([bot, bot, pub], False),
        "histórico raso, só o merge": ([gh], True),
        "histórico raso, só o elo": ([bot], False),
        "histórico vazio": ([], False),
    }
    falhas = [n for n, (c, esperado) in casos.items() if aguardando_selo(c) != esperado]
    eventos = {"PR tolera (D1)": ({"GITHUB_EVENT_NAME": "pull_request"}, True),
               "cópia de trabalho tolera (D7)": ({}, True),
               "publicador é estrito": ({"GITHUB_EVENT_NAME": "workflow_run"}, False),
               "elo agendado é estrito": ({"GITHUB_EVENT_NAME": "schedule"}, False)}
    falhas += [n for n, (amb, esperado) in eventos.items() if tolerante(amb=amb) != esperado]
    print(f"✗ AUTOTESTE: {falhas}" if falhas else f"✓ AUTOTESTE OK — {len(casos) + len(eventos)} casos, sem rede.")
    return 1 if falhas else 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return _autoteste()
    if not tolerante():
        return 1
    avisar(" ".join(sys.argv[1:]) or "derivado obsoleto")
    return 0


if __name__ == "__main__":
    sys.exit(main())
