#!/usr/bin/env python3
"""Aviso do projeto: UMA Issue por causa no repositório privado, que fecha sozinha quando a causa some.

Até 15/11/2026 cada alarme abria a sua Issue por conta própria, uma por ocorrência: 75 Issues iguais de
"portão reprovou na publicação" e 14 de "pré-noite vermelha" ficaram abertas sem leitor. Aqui a causa tem
um título estável; com corpo, a Issue abre se não houver uma aberta; sem corpo, fecha a que houver.

    python3 scripts/avisos.py "Título estável" corpo.txt   # a causa existe (corpo de arquivo, ou - para a entrada)
    python3 scripts/avisos.py "Título estável"             # a causa sumiu

Falha do GitHub é aviso no log, nunca erro: alarme não derruba coleta nem publicação.
"""
import json
import subprocess
import sys

REPO_DOS_AVISOS = "monitorelnino/robo-registro"


def _gh(args, entrada=None):
    return subprocess.run(["gh", *args], capture_output=True, text=True, input=entrada, timeout=60)


def issues_abertas(gh=_gh):
    p = gh(["issue", "list", "--repo", REPO_DOS_AVISOS, "--state", "open", "--limit", "1000",
            "--json", "number,title"])
    if p.returncode != 0:
        return None
    return {i["title"]: i["number"] for i in json.loads(p.stdout or "[]")}


def _mudou(gh, n, corpo) -> bool:
    """O que a Issue aberta diz (corpo ou último comentário) já não é o que a causa diz hoje."""
    p = gh(["issue", "view", str(n), "--repo", REPO_DOS_AVISOS, "--json", "body,comments"])
    try:
        d = json.loads(p.stdout or "{}")
        ultimo = ((d.get("comments") or [{}])[-1].get("body") or d.get("body") or "").strip()
    except (ValueError, AttributeError, IndexError):
        return False
    return p.returncode == 0 and not ultimo.startswith(corpo.strip())


def avisar(titulo: str, corpo: str = "", ao_fechar: str = "A causa sumiu. Fechada.", gh=_gh, abertas=None) -> str:
    """Com corpo, abre a Issue se não houver uma aberta com o título, ou comenta se a causa mudou; sem corpo, fecha."""
    abertas = issues_abertas(gh) if abertas is None else abertas
    if abertas is None:
        print(f"::warning::não consegui listar as Issues de {REPO_DOS_AVISOS}; aviso adiado: {titulo}")
        return "sem acesso às Issues"
    n = abertas.get(titulo)
    if corpo and n is None:
        gh(["issue", "create", "--repo", REPO_DOS_AVISOS, "--title", titulo, "--body-file", "-"],
           corpo.rstrip() + "\n\nFecha sozinha quando a causa some (`scripts/avisos.py`).")
        return "aberta"
    if corpo and n is not None and _mudou(gh, n, corpo):
        gh(["issue", "comment", str(n), "--repo", REPO_DOS_AVISOS, "--body-file", "-"], corpo.rstrip())
        return "atualizada"
    if not corpo and n is not None:
        gh(["issue", "close", str(n), "--repo", REPO_DOS_AVISOS, "--comment", ao_fechar])
        return "fechada"
    return "sem mudança"


def autoteste() -> int:
    def gh_com(lista, rc=0):
        return lambda args, entrada=None: type("R", (), {"returncode": rc, "stdout": json.dumps(lista)})()
    aberta = [{"title": "T", "number": 9}]
    casos = {
        "causa nova abre": avisar("T", "x", gh=gh_com([])) == "aberta",
        "causa repetida não abre a segunda": avisar("T", "x", gh=gh_com(aberta)) == "sem mudança",
        "causa que sumiu fecha": avisar("T", gh=gh_com(aberta)) == "fechada",
        "causa que mudou comenta": avisar("T", "novo", gh=lambda a, e=None: type("R", (), {"returncode": 0, "stdout": json.dumps(
            {"body": "velho", "comments": []} if a[:2] == ["issue", "view"] else aberta)})()) == "atualizada",
        "causa igual não comenta": avisar("T", "x", gh=lambda a, e=None: type("R", (), {"returncode": 0, "stdout": json.dumps(
            {"body": "x\n\nFecha sozinha", "comments": []} if a[:2] == ["issue", "view"] else aberta)})()) == "sem mudança",
        "sem causa e sem Issue, nada": avisar("T", gh=gh_com([])) == "sem mudança",
        "GitHub fora do ar não é erro": avisar("T", "x", gh=gh_com([], rc=1)) == "sem acesso às Issues",
    }
    falhas = [k for k, v in casos.items() if not v]
    print(f"✗ AUTOTESTE: {falhas}" if falhas else f"✓ AUTOTESTE OK — {len(casos)} casos, sem rede.")
    return 1 if falhas else 0


def main(argv) -> int:
    if "--autoteste" in argv:
        return autoteste()
    if not argv:
        print(__doc__)
        return 2
    corpo = ""
    if len(argv) > 1:
        corpo = sys.stdin.read() if argv[1] == "-" else open(argv[1], encoding="utf-8", errors="replace").read()
    print(f"aviso «{argv[0]}»: {avisar(argv[0], corpo)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
