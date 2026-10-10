#!/usr/bin/env python3
"""
scripts/elo_de_ensaio.py — a "coleta" de um elo no ensaio real da noite (item 2-bis.2, 10/10/2026)
=================================================================================================
No ensaio real, os workflows da noite rodam de verdade no GitHub — fila de concorrência, job `vez`,
`workflow_run`, laço de rebase-e-push, marcador `.feito` e artefato —, mas num ramo `ensaio-real/...` e
sem ir à rede: o que se ensaia é a mecânica da plataforma, não o coletor. Este script ocupa o lugar
dos comandos do elo: espera alguns segundos (para alargar a janela de corrida com os outros elos e
com o empurrão concorrente que o ensaio provoca) e sai. O commit do elo é o próprio marcador.

Recusa rodar fora de um ramo `ensaio-real/...`: na `main` ele não coletaria nada e o marcador mentiria.

USO
  python3 scripts/elo_de_ensaio.py --elo diarios --ramo ensaio-real/2026-10-10-123
  python3 scripts/elo_de_ensaio.py --autoteste
"""
from __future__ import annotations

import sys
import time

ESPERA_S = 20


def pode_rodar(ramo: str) -> bool:
    """Só em ramo `ensaio-real/...`. Função pura."""
    return str(ramo or "").startswith("ensaio-real/")


def autoteste() -> int:
    casos = [("ramo de ensaio roda", pode_rodar("ensaio-real/2026-10-10-1")),
             ("main não roda", not pode_rodar("main")),
             ("ramo qualquer não roda", not pode_rodar("edicao/x")),
             ("vazio não roda", not pode_rodar(""))]
    for n, ok in casos:
        print(("  ✓ " if ok else "  ✗ ") + n)
    falhas = [n for n, ok in casos if not ok]
    print("✗ AUTOTESTE: %d falha(s)" % len(falhas) if falhas else "✓ AUTOTESTE OK")
    return 1 if falhas else 0


def main() -> int:
    argv = sys.argv[1:]
    if "--autoteste" in argv:
        return autoteste()
    elo = argv[argv.index("--elo") + 1] if "--elo" in argv else "?"
    ramo = argv[argv.index("--ramo") + 1] if "--ramo" in argv else ""
    if not pode_rodar(ramo):
        print(f"✗ elo de ensaio fora de ramo ensaio-real/ ({ramo!r}): recusado")
        return 1
    print(f"elo de ensaio `{elo}` no ramo {ramo}: sem rede; {ESPERA_S} s de trabalho simulado")
    time.sleep(ESPERA_S)
    return 0


if __name__ == "__main__":
    sys.exit(main())
