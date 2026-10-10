#!/usr/bin/env python3
"""
scripts/ensaio_real.py — a noite ensaiada no GitHub de verdade, de dia, num ramo `ensaio-real/...`
=============================================================================================
Item 2-bis.2 da janela A (central, 10/10/2026 09:50 UTC; editoria, 06:45 BRT). O
`ensaio_da_noite.py` passa verde e a noite falha, porque ele SIMULA o GitHub num repositório
temporário; os defeitos das últimas noites foram comportamento real da plataforma — pendente
substituído na fila do grupo de concorrência, `workflow_run` disparando duplicata, empurrão
concorrente com o ramo andando (catálogo `config/falhas_da_noite.json`, F21, F23, F26, F27).

O ensaio real dispara os MESMOS workflows da noite (`ensaio_real_da_noite.yml`), com os mesmos
grupos de concorrência, o mesmo job `vez`, o mesmo laço de rebase-e-push e o mesmo marcador, num
ramo `ensaio-real/<data>-<run>`: o `_coletor.yml` parte desse ramo e empurra para ele, e a coleta é
trocada por `scripts/elo_de_ensaio.py` (sem rede). A corrente é CONDUZIDA por este script — cada
elo disparado no ramo quando o anterior deixa o marcador — e não por `workflow_run`: o run disparado
por evento roda sempre no ramo padrão, e alargar o filtro `branches: [main]` dos elos levaria a
corrente do ensaio para a `main` (é o F15). Divergência registrada: o gatilho `workflow_run` em si
não é ensaiado aqui. E provoca de propósito:
  - DOIS PENDENTES: diários disparado duas vezes e a triagem ao mesmo tempo;
  - EMPURRÃO CONCORRENTE: um commit no ramo enquanto os elos rodam, para o laço de rebase-e-push.
O cancelamento de propósito NÃO é provocado: a regra 4 do CLAUDE.md proíbe script que cancele run
de outro, e a regra vence o pedido (divergência registrada).

Critério (este script, `--veredito`): os seis elos com `.feito` no ramo; nenhum run do ensaio
cancelado sem um sucesso depois, no mesmo workflow; nenhum artefato `coleta-perdida-*` dos runs do
ensaio (push perdido). Vermelho sai 1 — e a checagem pré-noite lê a conclusão deste workflow.

USO
  python3 scripts/ensaio_real.py --veredito --ramo ensaio-real/2026-10-10-1 --noite 2026-10-10 --desde 2026-10-10T18:07:00Z
  python3 scripts/ensaio_real.py --conduzir --ramo ... --noite ... --teto-min 110
  python3 scripts/ensaio_real.py --autoteste
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import time

RAIZ = pathlib.Path(__file__).resolve().parent.parent
ELOS = ("diarios", "descoberta", "evidencias", "juiz", "sinais-fisicos", "triagem")
WORKFLOWS = ("noturno_diarios.yml", "noturno_descoberta.yml", "noturno_evidencias.yml",
             "noturno_juiz.yml", "noturno_sinais.yml", "noturno_triagem.yml")


# 10/10/2026 (F33): `ensaio/` colidia com o ramo `ensaio` que já existe (o git recusa
# `ensaio/x` ao lado de `ensaio`: "directory file conflict").
PREFIXO = "ensaio-real/"
RAMOS_QUE_EXISTEM = ("main", "ensaio", "relogio")

CORRENTE = (("diarios", "noturno_diarios.yml"), ("descoberta", "noturno_descoberta.yml"),
            ("evidencias", "noturno_evidencias.yml"), ("juiz", "noturno_juiz.yml"),
            ("sinais-fisicos", "noturno_sinais.yml"))


def proximo_a_disparar(feitos: set, disparados: set, corrente=CORRENTE):
    """O workflow do primeiro elo da corrente ainda sem marcador cujo anterior já tem — se ainda
    não foi disparado. Função pura."""
    anterior_ok = True
    for elo, wf in corrente:
        if elo in feitos:
            anterior_ok = True
            continue
        if anterior_ok and wf not in disparados:
            return wf
        return None
    return None


def marcadores_que_faltam(arquivos: list, noite: str, elos=ELOS) -> list:
    """Os elos sem `data/noite/<noite>/<elo>.feito` na árvore do ramo. Função pura."""
    tem = set(arquivos or [])
    return [e for e in elos if f"data/noite/{noite}/{e}.feito" not in tem]


def cancelados_sem_refazer(runs: list) -> list:
    """Workflows com run cancelado/estourado e nenhum sucesso criado depois. Função pura.

    `runs`: [{workflow, createdAt, status, conclusion}]."""
    fora = []
    por_wf = {}
    for r in runs or []:
        por_wf.setdefault(r.get("workflow"), []).append(r)
    for wf, rr in sorted(por_wf.items()):
        rr = sorted(rr, key=lambda r: str(r.get("createdAt") or ""))
        for i, r in enumerate(rr):
            if str(r.get("conclusion") or "") in ("cancelled", "timed_out", "startup_failure"):
                if not any(str(x.get("conclusion")) == "success" for x in rr[i + 1:]):
                    fora.append(f"{wf} (run {r.get('databaseId')}, {r.get('conclusion')})")
                    break
    return fora


def coletas_perdidas(artefatos: list, ids_do_ensaio: set) -> list:
    """Artefatos `coleta-perdida-<elo>-<run>` de runs do ensaio. Função pura."""
    fora = []
    for a in artefatos or []:
        nome = str(a)
        if nome.startswith("coleta-perdida-") and nome.rsplit("-", 1)[-1] in {str(i) for i in ids_do_ensaio}:
            fora.append(nome)
    return fora


def veredito(arquivos, noite, runs, artefatos) -> dict:
    faltam = marcadores_que_faltam(arquivos, noite)
    canc = cancelados_sem_refazer(runs)
    perd = coletas_perdidas(artefatos, {r.get("databaseId") for r in runs or []})
    return {"noite": noite, "verde": not (faltam or canc or perd),
            "elos_sem_marcador": faltam, "cancelados_sem_refazer": canc, "pushes_perdidos": perd}


# ------------------------------------------------------------------------ portas de I/O
def _gh_json(args):
    try:
        r = subprocess.run(["gh"] + args, cwd=RAIZ, capture_output=True, text=True, timeout=120)
        return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else None
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        return None


def arquivos_do_ramo(ramo: str) -> list:
    subprocess.run(["git", "fetch", "-q", "origin", ramo], cwd=RAIZ, capture_output=True, timeout=120)
    r = subprocess.run(["git", "ls-tree", "-r", "--name-only", "FETCH_HEAD", "--", "data/noite/"],
                       cwd=RAIZ, capture_output=True, text=True, timeout=60)
    return [l.strip() for l in r.stdout.splitlines() if l.strip()]


def runs_do_ensaio(desde: str, ramo: str) -> list:
    """Runs dos workflows da noite disparados no ramo do ensaio desde o início dele."""
    fora = []
    for wf in WORKFLOWS:
        for r in _gh_json(["run", "list", "--workflow", wf, "--limit", "30",
                           "--json", "databaseId,createdAt,status,conclusion,headBranch,event"]) or []:
            if str(r.get("createdAt") or "") >= desde and r.get("headBranch") == ramo:
                fora.append(dict(r, workflow=wf))
    return fora


def artefatos() -> list:
    r = subprocess.run(["gh", "api", "repos/{owner}/{repo}/actions/artifacts", "-X", "GET",
                        "-F", "per_page=100", "--jq", ".artifacts[].name"],
                       cwd=RAIZ, capture_output=True, text=True, timeout=120)
    return [l.strip() for l in (r.stdout or "").splitlines() if l.strip()]


def autoteste() -> int:
    falhas = []

    def ok(nome, cond):
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    n = "2026-10-10"
    todos = [f"data/noite/{n}/{e}.feito" for e in ELOS]
    ok("os seis marcadores no ramo: nada falta", marcadores_que_faltam(todos, n) == [])
    ok("elo sem marcador é nomeado", marcadores_que_faltam(todos[:-1], n) == ["triagem"])
    ok("marcador de outra noite não vale",
       marcadores_que_faltam([t.replace(n, "2026-10-09") for t in todos], n) == list(ELOS))
    canc = [{"workflow": "noturno_diarios.yml", "databaseId": 1, "createdAt": "1", "conclusion": "cancelled"}]
    ok("cancelado sem sucesso depois reprova", len(cancelados_sem_refazer(canc)) == 1)
    ok("cancelado e refeito com sucesso depois passa",
       cancelados_sem_refazer(canc + [{"workflow": "noturno_diarios.yml", "databaseId": 2,
                                       "createdAt": "2", "conclusion": "success"}]) == [])
    ok("sucesso ANTES do cancelado não conta como refazer",
       len(cancelados_sem_refazer([{"workflow": "w", "databaseId": 1, "createdAt": "1", "conclusion": "success"},
                                   {"workflow": "w", "databaseId": 2, "createdAt": "2", "conclusion": "cancelled"}])) == 1)
    ok("push perdido de run do ensaio reprova",
       coletas_perdidas(["coleta-perdida-diarios-77"], {77}) == ["coleta-perdida-diarios-77"])
    ok("push perdido de outro run não é do ensaio", coletas_perdidas(["coleta-perdida-diarios-5"], {77}) == [])
    ok("depois dos diários, a descoberta é a próxima",
       proximo_a_disparar({"diarios"}, {"noturno_diarios.yml"}) == "noturno_descoberta.yml")
    ok("não dispara de novo o que já foi disparado",
       proximo_a_disparar({"diarios"}, {"noturno_diarios.yml", "noturno_descoberta.yml"}) is None)
    ok("sem o anterior feito, o seguinte espera",
       proximo_a_disparar(set(), {"noturno_diarios.yml"}) is None)
    ok("corrente inteira feita: nada a disparar",
       proximo_a_disparar({e for e, _ in CORRENTE}, set()) is None)
    ok("o prefixo do ramo do ensaio não colide com ramo existente",
       PREFIXO == "ensaio-real/" and not any(r == PREFIXO.rstrip("/") for r in RAMOS_QUE_EXISTEM))
    v = veredito(todos, n, [], [])
    ok("ensaio completo é verde", v["verde"])
    ok("ensaio com elo faltando é vermelho", not veredito(todos[:3], n, [], [])["verde"])
    print("✗ AUTOTESTE: %d falha(s)" % len(falhas) if falhas else "✓ AUTOTESTE OK")
    return 1 if falhas else 0


def main() -> int:
    argv = sys.argv[1:]
    if "--autoteste" in argv:
        return autoteste()

    def arg(k, padrao=""):
        return argv[argv.index(k) + 1] if k in argv else padrao

    ramo, noite, desde = arg("--ramo"), arg("--noite"), arg("--desde")
    if not ramo.startswith("ensaio-real/"):
        print("✗ o ensaio real só roda em ramo ensaio-real/")
        return 2
    if "--conduzir" in argv:
        teto = float(arg("--teto-min", "110"))
        disparados = {"noturno_diarios.yml", "noturno_triagem.yml"}   # o workflow já os disparou
        inicio = time.time()
        while (time.time() - inicio) / 60 < teto:
            faltam = marcadores_que_faltam(arquivos_do_ramo(ramo), noite)
            feitos = set(ELOS) - set(faltam)
            print(f"{int((time.time() - inicio) / 60)} min · faltam: {', '.join(faltam) or 'nenhum'}")
            if not faltam:
                return 0
            wf = proximo_a_disparar(feitos, disparados)
            if wf:
                subprocess.run(["gh", "workflow", "run", wf, "--ref", ramo], cwd=RAIZ, timeout=60)
                disparados.add(wf)
                print(f"  → disparado {wf} no ramo {ramo}")
            time.sleep(60)
        return 0
    v = veredito(arquivos_do_ramo(ramo), noite, runs_do_ensaio(desde, ramo), artefatos())
    pathlib.Path("ensaio_real.json").write_text(json.dumps(v, ensure_ascii=False, indent=1) + "\n",
                                                encoding="utf-8", newline="\n")
    print(json.dumps(v, ensure_ascii=False, indent=1))
    print("✓ ENSAIO REAL VERDE" if v["verde"] else "✗ ENSAIO REAL VERMELHO")
    return 0 if v["verde"] else 1


if __name__ == "__main__":
    sys.exit(main())
