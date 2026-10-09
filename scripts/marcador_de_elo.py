#!/usr/bin/env python3
"""Este elo trabalhou nesta noite? A pergunta tem UM dono, e duas provas.

DEFEITO MEDIDO NA NOITE DE 08→09/10/2026
----------------------------------------
O marcador `data/noite/<noite>/<elo>.feito` é a prova de que houve COLETA, e não só de que houve
run. Ele era gravado na árvore do runner e chegava à `main` **no mesmo commit do dado** — então o
push que se perde leva o marcador junto. Foi o que aconteceu com `diarios` (run 37875038703): o
elo coletou por 11 minutos, o laço de rebase-e-push falhou nas cinco tentativas, o dado saiu como
artefato `coleta-perdida-diarios-37875038703` e **o marcador não existiu em lugar nenhum**. Para a
guarda e para o vigia, aquela coleta nunca aconteceu.

As duas provas, e por que são duas:

  1. **o arquivo na árvore** — vale quando o commit do elo chegou à `main`. É a prova barata, e é
     a que vale na maioria das noites;
  2. **o artefato do run** — `feito-<elo>-<noite>`, subido pelo elo no mesmo passo em que grava o
     marcador, antes de qualquer commit. Ele existe mesmo quando o push morre, porque artefato não
     depende de `git push`.

Quem pergunta são a guarda de abertura (`noturno_diarios.yml`), o vigia (`vigia_da_abertura.yml`) e
a reserva. Antes cada um escrevia a sua própria condição em `bash`, e a segunda prova não existia:
o mesmo defeito teria de ser corrigido em três lugares. Agora a pergunta tem dono.

USO
    python3 scripts/marcador_de_elo.py --elo diarios --noite 2026-10-09
    python3 scripts/marcador_de_elo.py --elo diarios            # a noite em curso
    python3 scripts/marcador_de_elo.py --autoteste
Sai 0 quando o elo trabalhou, 1 quando não — e imprime qual prova valeu.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

PREFIXO_DO_ARTEFATO = "feito-"


def nome_do_artefato(elo: str, noite: str) -> str:
    """O nome do artefato que prova a coleta deste elo nesta noite. Função pura."""
    return f"{PREFIXO_DO_ARTEFATO}{elo}-{noite}"


def caminho_do_marcador(elo: str, noite: str) -> str:
    """O caminho do marcador na árvore. Função pura."""
    return f"data/noite/{noite}/{elo}.feito"


def trabalhou(elo: str, noite: str, existe_arquivo, artefatos) -> tuple:
    """(trabalhou, prova). Função pura: as duas provas entram por parâmetro.

    A ordem é a do custo: o arquivo na árvore primeiro, porque é leitura local; o artefato depois,
    porque é uma chamada à API. Nenhuma das duas sozinha basta — a primeira falta quando o push
    morre, e a segunda falta nos catorze dias seguintes, quando o artefato expira.
    """
    if existe_arquivo(caminho_do_marcador(elo, noite)):
        return True, "marcador na árvore"
    alvo = nome_do_artefato(elo, noite)
    if alvo in set(artefatos or []):
        return True, f"artefato {alvo} (o commit do elo se perdeu, a coleta não)"
    return False, "nenhuma das duas provas"


def artefatos_do_repositorio(limite: int = 200) -> list:
    """Os nomes dos artefatos não expirados. LÊ a API; devolve [] quando não dá."""
    cmd = ["gh", "api", "repos/{owner}/{repo}/actions/artifacts",
           "--paginate", "-X", "GET", "-F", f"per_page={min(limite, 100)}",
           "--jq", ".artifacts[] | select(.expired == false) | .name"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return []
    return [l.strip() for l in (r.stdout or "").splitlines() if l.strip()]


def autoteste() -> int:
    falhas = []

    def ok(nome, cond):
        print(("  ok " if cond else "  FALHA ") + nome)
        if not cond:
            falhas.append(nome)

    ok("o nome do artefato junta elo e noite",
       nome_do_artefato("diarios", "2026-10-09") == "feito-diarios-2026-10-09")
    ok("o caminho do marcador é o do contrato",
       caminho_do_marcador("diarios", "2026-10-09") == "data/noite/2026-10-09/diarios.feito")
    ok("marcador na árvore prova",
       trabalhou("diarios", "2026-10-09", lambda c: True, []) [0] is True)
    ok("sem arquivo, o artefato prova",
       trabalhou("diarios", "2026-10-09", lambda c: False,
                 ["feito-diarios-2026-10-09"])[0] is True)
    ok("a prova diz que o commit se perdeu",
       "se perdeu" in trabalhou("diarios", "2026-10-09", lambda c: False,
                                ["feito-diarios-2026-10-09"])[1])
    ok("artefato de OUTRA noite não prova",
       trabalhou("diarios", "2026-10-09", lambda c: False,
                 ["feito-diarios-2026-10-08"])[0] is False)
    ok("artefato de OUTRO elo não prova",
       trabalhou("diarios", "2026-10-09", lambda c: False,
                 ["feito-juiz-2026-10-09"])[0] is False)
    ok("sem prova nenhuma, não trabalhou",
       trabalhou("diarios", "2026-10-09", lambda c: False, [])[0] is False)
    ok("`coleta-perdida` NÃO é prova de coleta deste elo nesta noite",
       trabalhou("diarios", "2026-10-09", lambda c: False,
                 ["coleta-perdida-diarios-37875038703"])[0] is False)
    import inspect
    ok("trava estrutural: as funções puras não leem disco nem vão à rede",
       all(x not in inspect.getsource(trabalhou) for x in ("open(", "subprocess", "requests")))
    print(f"autoteste: {10 - len(falhas)}/10")
    return 1 if falhas else 0


def main() -> int:
    argv = sys.argv[1:]
    if "--autoteste" in argv:
        return autoteste()
    elo = ""
    noite = ""
    for chave in ("--elo", "--noite"):
        if chave in argv:
            i = argv.index(chave)
            valor = argv[i + 1] if i + 1 < len(argv) else ""
            if chave == "--elo":
                elo = valor
            else:
                noite = valor
    if not elo:
        print("uso: marcador_de_elo.py --elo <nome> [--noite AAAA-MM-DD]")
        return 2
    if not noite:
        import datetime as dt
        from janela_da_noite import noite_de
        noite = noite_de(dt.datetime.now(dt.timezone.utc).replace(tzinfo=None))
    feito, prova = trabalhou(elo, noite, lambda c: (RAIZ / c).is_file(),
                             artefatos_do_repositorio())
    print(f"{elo} · noite de {noite} · trabalhou={'sim' if feito else 'nao'} · {prova}")
    return 0 if feito else 1


if __name__ == "__main__":
    sys.exit(main())
