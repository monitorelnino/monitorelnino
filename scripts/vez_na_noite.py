#!/usr/bin/env python3
"""
scripts/vez_na_noite.py — a fila dos elos que escrevem as filas de pista, por ordem de chegada
================================================================================================
10/10/2026 (janela A, item 2). DEFEITO MEDIDO NA ABERTURA DE 09→10/10
---------------------------------------------------------------------
Os elos que escrevem `data/pistas_*.json` dividiam UM grupo de concorrência do GitHub, `noturno`
(seção G1 do handover de 29/09). O grupo guarda um run em execução e **um só pendente**: o
terceiro que chega cancela o pendente, com `cancel-in-progress: false` ou sem — é a regra do
GitHub, não uma opção. Às 01:09–01:10 o despachante disparou triagem, diários e outros; a triagem
entrou, os diários ficaram pendentes, e o pendente seguinte os cancelou às 01:14, sem passo
executado. A mesma substituição matou `diarios` e `triagem` na noite de 08→09 e a triagem
duplicada de 10/10. Grupo compartilhado não é fila: é fila de um lugar.

O conserto separa as duas coisas que o grupo fazia:
  - **não cancelar**: cada elo tem o seu grupo (`noturno-<elo>`), e um pendente só pode ser
    substituído por outro run do MESMO elo, que fará o mesmo trabalho;
  - **não escrever ao mesmo tempo**: este script, num job `vez` antes da coleta, espera até não
    haver run ANTERIOR (id menor) ainda aberto entre os workflows do antigo grupo, no mesmo ramo.
    Ordem de chegada, sem limite de lugares, e sem cancelar ninguém.

Sem impasse por construção: o run de menor id nunca espera. Se a API não responde três vezes
seguidas, o elo segue (com aviso): ficar parado até o teto é perder a coleta inteira, e o laço de
rebase-e-push com a união pela base comum continua valendo como rede.

USO
  python3 scripts/vez_na_noite.py --esperar --run-id 123 --ramo main [--teto-min 300]
  python3 scripts/vez_na_noite.py --autoteste
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys
import time

RAIZ = pathlib.Path(__file__).resolve().parent.parent

# Os workflows cujo coletor passava `grupo_de_concorrencia: noturno`. O autoteste lê a árvore e
# reprova se um workflow novo entrar no grupo sem entrar aqui.
WORKFLOWS_DO_GRUPO = (
    "noturno_diarios.yml",
    "noturno_descoberta.yml",
    "noturno_evidencias.yml",
    "noturno_juiz.yml",
    "noturno_triagem.yml",
    "noturno_saude_estadual.yml",
    "semanal_respiratorias.yml",
)
ABERTOS = ("queued", "requested", "waiting", "pending", "in_progress")


def quem_vem_antes(meu_id: int, runs: list) -> list:
    """Os runs ainda abertos que chegaram antes deste. Função pura.

    `runs` traz `databaseId` e `status`. Id de run do GitHub cresce com a criação: comparar ids é
    comparar ordem de chegada, sem depender de relógio.
    """
    fora = []
    for r in runs or []:
        try:
            rid = int(r.get("databaseId"))
        except (TypeError, ValueError):
            continue
        if rid < int(meu_id) and str(r.get("status") or "").lower() in ABERTOS:
            fora.append(r)
    return sorted(fora, key=lambda r: int(r["databaseId"]))


def workflows_no_grupo(textos: dict) -> set:
    """Os workflows que entregam o coletor ao grupo da noite. Função pura (texto por arquivo)."""
    return {nome for nome, t in (textos or {}).items()
            if re.search(r"^\s*grupo_de_concorrencia:\s*noturno\s*$", t, re.M)}


def _runs_abertos(workflow: str, ramo: str):
    try:
        r = subprocess.run(["gh", "run", "list", "--workflow", workflow, "--branch", ramo,
                            "--limit", "30", "--json", "databaseId,status,createdAt"],
                           cwd=RAIZ, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    try:
        return [x for x in json.loads(r.stdout or "[]")
                if str(x.get("status") or "").lower() in ABERTOS]
    except json.JSONDecodeError:
        return None


def esperar(meu_id: int, ramo: str, teto_min: float, intervalo_s: int = 30) -> int:
    inicio = time.time()
    falhas_seguidas = 0
    while True:
        runs, falhou = [], False
        for wf in WORKFLOWS_DO_GRUPO:
            r = _runs_abertos(wf, ramo)
            if r is None:
                falhou = True
                continue
            runs += [dict(x, workflow=wf) for x in r]
        if falhou:
            falhas_seguidas += 1
            if falhas_seguidas >= 3:
                print("::warning::a API não respondeu três vezes seguidas; o elo segue sem a vez "
                      "(a união pela base comum no push continua valendo)")
                return 0
        else:
            falhas_seguidas = 0
            antes = quem_vem_antes(meu_id, runs)
            if not antes:
                print(f"vez: nenhum run anterior aberto no grupo da noite — run {meu_id} segue")
                return 0
            print(f"vez: esperando {len(antes)} run(s) anterior(es): "
                  + ", ".join(f"{a['workflow']}#{a['databaseId']} ({a['status']})" for a in antes))
        if (time.time() - inicio) / 60 > teto_min:
            print(f"::warning::a vez não chegou em {teto_min:.0f} min; o elo segue sem ela")
            return 0
        time.sleep(intervalo_s)


def autoteste() -> int:
    falhas = []

    def ok(nome, cond):
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    runs = [{"databaseId": 10, "status": "in_progress"}, {"databaseId": 11, "status": "queued"},
            {"databaseId": 12, "status": "completed"}, {"databaseId": 20, "status": "in_progress"}]
    ok("o run mais antigo aberto não espera ninguém", quem_vem_antes(10, runs) == [])
    ok("o run seguinte espera o anterior em execução",
       [r["databaseId"] for r in quem_vem_antes(11, runs)] == [10])
    ok("run concluído não segura a fila",
       [r["databaseId"] for r in quem_vem_antes(15, runs)] == [10, 11])
    ok("run que chegou depois não passa na frente",
       all(int(r["databaseId"]) < 15 for r in quem_vem_antes(15, runs)))
    ok("à espera de runner conta como aberto (é a fila, não falha)",
       [r["databaseId"] for r in quem_vem_antes(99, [{"databaseId": 5, "status": "waiting"}])] == [5])
    ok("id ilegível é ignorado, não derruba",
       quem_vem_antes(9, [{"databaseId": None, "status": "queued"}]) == [])
    # Caso da abertura de 10/10: triagem rodando, diários e o terceiro chegam juntos. Com a vez,
    # ninguém é cancelado: os três acabam rodando, um de cada vez, por ordem de chegada.
    fila = [{"databaseId": 1, "status": "in_progress"}, {"databaseId": 2, "status": "queued"},
            {"databaseId": 3, "status": "queued"}]
    ordem = []
    while fila:
        livres = [r for r in fila if not quem_vem_antes(r["databaseId"], fila)]
        ordem.append(livres[0]["databaseId"])
        fila = [r for r in fila if r is not livres[0]]
    ok("três elos que chegam juntos rodam os três, em ordem, sem cancelamento", ordem == [1, 2, 3])

    textos = {p.name: p.read_text(encoding="utf-8")
              for p in (RAIZ / ".github" / "workflows").glob("*.yml")}
    no_grupo = workflows_no_grupo(textos)
    ok("todo workflow do grupo da noite está na lista da vez",
       no_grupo <= set(WORKFLOWS_DO_GRUPO))
    coletor = textos.get("_coletor.yml", "")
    ok("o coletor tem o job `vez` e a coleta espera por ele",
       "vez_na_noite.py" in coletor and re.search(r"needs:\s*\[?\s*vez", coletor) is not None)
    ok("o grupo `noturno` virou um grupo por elo no coletor",
       "format('noturno-{0}', inputs.nome)" in coletor)
    print(f"{'✗ AUTOTESTE: ' + str(len(falhas)) + ' falha(s)' if falhas else '✓ AUTOTESTE OK'}")
    return 1 if falhas else 0


def main() -> int:
    argv = sys.argv[1:]
    if "--autoteste" in argv:
        return autoteste()
    if "--esperar" in argv:
        def arg(chave, padrao=""):
            return argv[argv.index(chave) + 1] if chave in argv else padrao
        return esperar(int(arg("--run-id", "0")), arg("--ramo", "main"),
                       float(arg("--teto-min", "300")))
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
