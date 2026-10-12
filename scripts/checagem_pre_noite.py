#!/usr/bin/env python3
"""
scripts/checagem_pre_noite.py — a noite conferida ANTES de abrir, e não descoberta de madrugada
==============================================================================================
Item 2-bis.3 da janela A (central, 10/10/2026 09:50 UTC; editoria, 06:45 BRT). As falhas das
últimas noites foram comportamento real da plataforma, e várias eram visíveis às 23h: `main`
vermelha (10/10, 09:12 → 10:59), fila de runs entupida, despachante parado. Esta checagem roda por
volta das 23:00 UTC e diz, em seis perguntas, se a noite tem condição de abrir:

  1. a `main` está verde (último "Portões" no push concluído)?
  2. algum PR foi mesclado depois das 23:30 UTC (perto demais da abertura)?
  3. a fila de runs está vazia (nada `queued`/`in_progress` além desta checagem e dos relógios)?
  4. o despachante e o relógio estão vivos (último run há menos de 70 min)?
  5. os segredos de que a noite depende estão presentes (só presença, nunca valor)?
  6. o ensaio real do dia está verde (quando o workflow existir)?

Saída: `preflight-<noite>.json` (artefato do run e resumo do job) e, se vermelho, Issue no
`robo-registro` antes de a noite começar.

DIVERGÊNCIA REGISTRADA (regra vence handover): o pedido era gravar `data/noite/<noite>/preflight.json`
na `main`. Às 23h isso seria commit automático na `main` de dia — proibido pela regra de 27/09/2026
(`guarda_da_janela.py`). O resultado vai como artefato do run; nada é commitado.

USO
  python3 scripts/checagem_pre_noite.py --autoteste
  python3 scripts/checagem_pre_noite.py --saida preflight.json   # consulta a API (gh)
"""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))

VIVO_MIN = 70
CORTE_DE_MERGE = "23:30"
SEGREDOS_DA_NOITE = ("ROBO_TOKEN", "ROBO_DEPLOY_KEY", "NETLIFY_AUTH_TOKEN", "NETLIFY_SITE_ID")
QUEM_PODE_ESTAR_RODANDO = ("checagem_pre_noite.yml", "despachante.yml", "relogio.yml",
                           "vigia_da_abertura.yml")
ABERTOS = ("queued", "requested", "waiting", "pending", "in_progress")
REPOSITORIO_PRIVADO = "monitorelnino/robo-registro"
RAMOS_FORA_DA_FILA = ("ensaio-real/", "coleta-dia/")


def _iso(s: str):
    try:
        return dt.datetime.fromisoformat(str(s or "").replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


FIM_DA_JANELA_H = 9   # a janela da noite é 01:00–09:00 UTC


def noite_seguinte(agora: dt.datetime) -> str:
    """A noite que esta checagem antecede — ou, de madrugada, a que já está em curso. Função pura.

    11/10/2026 (F36): era "hora < 1 → hoje"; o cron das 22:53 chegou às 01:20 (2h27 de atraso do
    GitHub) e a checagem julgou a noite de AMANHÃ, com a de hoje aberta debaixo dela.
    """
    return (agora.date() if agora.hour < FIM_DA_JANELA_H
            else agora.date() + dt.timedelta(days=1)).isoformat()


def atrasada(agora: dt.datetime) -> bool:
    """A checagem chegou com a janela já aberta (cron atrasado)? Então não julga. Função pura.

    Pré-noite depois de a noite abrir não é pré-noite: a fila está cheia de elos rodando, o
    despachante e o relógio já trabalharam, e "vermelho" ali só confunde quem lê de manhã.
    """
    return 1 <= agora.hour < FIM_DA_JANELA_H


def avaliar(fatos: dict, agora: dt.datetime) -> list:
    """As seis perguntas, cada uma com ok/detalhe. Função pura: os fatos entram por parâmetro.

    `fatos` traz: portoes_main (último run concluído: conclusion, sha), merges (lista de ISO das
    mesclagens na `main` desde ontem), runs_abertos (lista de {workflow, status}), ultimo_run
    ({workflow: createdAt}), segredos ({nome: bool}), ensaio_real (None quando o workflow não
    existe; senão {conclusion, createdAt}).
    """
    out = []

    p = fatos.get("portoes_main") or {}
    out.append({"pergunta": "main verde", "ok": p.get("conclusion") == "success",
                "detalhe": f"último Portões no push: {p.get('conclusion') or 'desconhecido'} "
                           f"({str(p.get('sha') or '')[:8]})"})

    h, m = (int(x) for x in CORTE_DE_MERGE.split(":"))
    corte = agora.replace(hour=h, minute=m, second=0, microsecond=0)
    if agora.hour < 12:
        corte -= dt.timedelta(days=1)
    tardios = [x for x in fatos.get("merges") or [] if (_iso(x) or dt.datetime.min) >= corte]
    out.append({"pergunta": f"nenhum PR mesclado depois das {CORTE_DE_MERGE} UTC",
                "ok": not tardios,
                "detalhe": f"{len(tardios)} mesclagem(ns) depois do corte" if tardios
                           else "nenhuma mesclagem depois do corte"})

    presos = [r for r in fatos.get("runs_abertos") or []
              if r.get("workflow") not in QUEM_PODE_ESTAR_RODANDO
              and str(r.get("status") or "").lower() in ABERTOS]
    out.append({"pergunta": "fila de runs vazia", "ok": not presos,
                "detalhe": ", ".join(f"{r['workflow']} ({r['status']})" for r in presos[:8])
                           or "nenhum run aberto"})

    for wf, nome in (("despachante.yml", "despachante"), ("relogio.yml", "relógio")):
        ultimos = fatos.get("ultimo_run") or {}
        # F43 (11/10/2026): o despacho também roda dentro de `relogio.yml`
        # (`despachar_temporizadores.py --origem relogio-claude`); despachante vivo é o mais recente
        # dos dois. O relógio continua julgado sozinho.
        quando = _iso(ultimos.get(wf))
        if wf == "despachante.yml":
            datas = [d for d in (_iso(ultimos.get("despachante.yml")),
                                 _iso(ultimos.get("relogio.yml"))) if d]
            quando = max(datas) if datas else None
        idade = None if quando is None else int((agora - quando).total_seconds() // 60)
        out.append({"pergunta": f"{nome} vivo (último run há menos de {VIVO_MIN} min)",
                    "ok": idade is not None and idade < VIVO_MIN,
                    "detalhe": "nenhum run encontrado" if idade is None else f"último run há {idade} min"})

    seg = fatos.get("segredos") or {}
    faltam = [s for s in SEGREDOS_DA_NOITE if not seg.get(s)]
    out.append({"pergunta": "segredos da noite presentes", "ok": not faltam,
                "detalhe": ("faltam: " + ", ".join(faltam)) if faltam else
                           f"{len(SEGREDOS_DA_NOITE)} presentes (só presença, nunca valor)"})

    er = fatos.get("ensaio_real")
    # O ensaio "do dia" é o da VÉSPERA da noite (o real roda às 18:13 UTC), não o da data do
    # relógio: à 00:20 a data já virou e o ensaio verde das 21:44 parecia "não é de hoje" (F36).
    vespera = dt.date.fromisoformat(noite_seguinte(agora)) - dt.timedelta(days=1)
    if er is None:
        out.append({"pergunta": "ensaio real do dia verde", "ok": True, "aviso": True,
                    "detalhe": "o ensaio real ainda não existe neste repositório — não avaliado"})
    else:
        de_hoje = (_iso(er.get("createdAt")) or dt.datetime.min).date() == vespera
        out.append({"pergunta": "ensaio real do dia verde",
                    "ok": de_hoje and er.get("conclusion") == "success",
                    "detalhe": f"último: {er.get('conclusion') or 'em curso'} em {er.get('createdAt')}"
                               + ("" if de_hoje else " (não é de hoje)")})

    erros = fatos.get("erros_de_consulta") or []
    out.append({"pergunta": "as consultas ao GitHub responderam", "ok": not erros,
                "detalhe": ("; ".join(erros[:4])) if erros else "todas responderam"})
    return out


class ErroDoGh(RuntimeError):
    pass


def _gh_json(args: list, erros: list = None, executar=subprocess.run):
    """JSON do `gh`, ou None — e o ERRO fica anotado em `erros`.

    11/10/2026 (F37): devolvia None calado em qualquer falha, e quem chamava fazia `or []`. Um
    campo inexistente no `--json` virou "fila de runs vazia" às 02:11, com seis elos rodando.
    Resposta vazia legítima (`[]`) continua sendo resposta; erro do `gh` nunca é.
    """
    def anotar(motivo: str):
        if erros is not None:
            erros.append(f"gh {' '.join(str(a) for a in args[:2])}: {motivo}"[:200])
        return None
    try:
        r = executar(["gh"] + args, cwd=RAIZ, capture_output=True, text=True, timeout=90)
    except (OSError, subprocess.SubprocessError) as e:
        return anotar(type(e).__name__)
    if r.returncode != 0:
        ultima = [l for l in (r.stderr or "").splitlines() if l.strip()]
        return anotar(ultima[-1] if ultima else f"código {r.returncode}")
    if not (r.stdout or "").strip():
        return anotar("resposta vazia")
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return anotar("resposta não é JSON")


def abertos_da_api(respostas: list) -> list:
    """Runs abertos a partir das respostas de `GET /actions/runs?status=…`. Função pura.

    A API REST traz `path` (`.github/workflows/x.yml`); o `gh run list --json` não tem esse campo.
    """
    vistos, out = set(), []
    for resp in respostas or []:
        for r in (resp or {}).get("workflow_runs") or []:
            if r.get("id") in vistos:
                continue
            vistos.add(r.get("id"))
            # F43 (11/10/2026): run de ramo de ensaio ou de coleta de dia não ocupa a fila da
            # noite — o 1º disparo da checagem de 11/10 deu ✗ só por contar `ensaio-real/*`.
            if str(r.get("head_branch") or "").startswith(RAMOS_FORA_DA_FILA):
                continue
            out.append({"workflow": pathlib.Path(str(r.get("path") or "")).name or r.get("name"),
                        "status": r.get("status")})
    return out


def coletar_fatos(agora: dt.datetime) -> dict:
    erros = []
    portoes = _gh_json(["run", "list", "--workflow", "portoes.yml", "--branch", "main", "--event",
                        "push", "--status", "completed", "--limit", "1",
                        "--json", "conclusion,headSha"], erros) or []
    desde = (agora - dt.timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    commits = _gh_json(["api", f"repos/{{owner}}/{{repo}}/commits?sha=main&since={desde}&per_page=100"],
                       erros) or []
    merges = [c["commit"]["committer"]["date"] for c in commits
              if len(c.get("parents") or []) > 1
              and str(c["commit"].get("message", "")).startswith("Merge pull request")]
    abertos = abertos_da_api([
        _gh_json(["api", f"repos/{{owner}}/{{repo}}/actions/runs?status={st}&per_page=100"], erros)
        for st in ("queued", "in_progress", "waiting", "pending", "requested")])
    ultimo = {}
    for wf in ("despachante.yml", "relogio.yml"):
        rr = _gh_json(["run", "list", "--workflow", wf, "--limit", "1", "--json", "createdAt"], erros) or []
        ultimo[wf] = rr[0]["createdAt"] if rr else None
    ensaio = None
    if (RAIZ / ".github" / "workflows" / "ensaio_real_da_noite.yml").exists():
        rr = _gh_json(["run", "list", "--workflow", "ensaio_real_da_noite.yml", "--limit", "1",
                       "--json", "conclusion,createdAt"], erros) or []
        ensaio = rr[0] if rr else {"conclusion": None, "createdAt": None}
    segredos = {s: os.environ.get(f"TEM_{s}", "").strip().lower() == "true" for s in SEGREDOS_DA_NOITE}
    return {"portoes_main": {"conclusion": (portoes[0] if portoes else {}).get("conclusion"),
                             "sha": (portoes[0] if portoes else {}).get("headSha")},
            "merges": merges, "runs_abertos": abertos, "ultimo_run": ultimo,
            "segredos": segredos, "ensaio_real": ensaio, "erros_de_consulta": erros}


def abrir_issue(noite: str, vermelhos: list) -> None:
    titulo = f"Checagem pré-noite vermelha: noite de {noite}"
    corpo = "A checagem das 23h reprovou antes de a noite abrir:\n\n" + "\n".join(
        f"- **{v['pergunta']}** — {v['detalhe']}" for v in vermelhos) + \
        "\n\nGerado por `scripts/checagem_pre_noite.py`.\n"
    subprocess.run(["gh", "issue", "create", "--repo", REPOSITORIO_PRIVADO, "--title", titulo,
                    "--body", corpo], cwd=RAIZ, capture_output=True, text=True, timeout=60)


def autoteste() -> int:
    falhas = []

    def ok(nome, cond):
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    agora = dt.datetime(2026, 10, 10, 23, 0)
    bom = {"portoes_main": {"conclusion": "success", "sha": "20272a72"},
           "merges": ["2026-10-10T20:08:00Z"],
           "runs_abertos": [{"workflow": "despachante.yml", "status": "in_progress"}],
           "ultimo_run": {"despachante.yml": "2026-10-10T22:47:00Z", "relogio.yml": "2026-10-10T22:10:00Z"},
           "segredos": {s: True for s in SEGREDOS_DA_NOITE}, "ensaio_real": None}
    r = avaliar(bom, agora)
    ok("noite saudável: as perguntas verdes", all(x["ok"] for x in r) and len(r) == 8)
    ok("ensaio real ausente é aviso, não vermelho", any(x.get("aviso") for x in r))
    ok("main vermelha reprova (10/10, 09:12 → 10:59)",
       not avaliar(dict(bom, portoes_main={"conclusion": "failure"}), agora)[0]["ok"])
    tarde = avaliar(dict(bom, merges=["2026-10-10T23:40:00Z"]), dt.datetime(2026, 10, 10, 23, 50))
    ok("mesclagem depois das 23:30 reprova", not tarde[1]["ok"])
    madrugada = avaliar(dict(bom, merges=["2026-10-10T23:40:00Z"]), dt.datetime(2026, 10, 11, 0, 20))
    ok("rodando depois da meia-noite, o corte é o das 23:30 da véspera", not madrugada[1]["ok"])
    presa = avaliar(dict(bom, runs_abertos=[{"workflow": "noturno_triagem.yml", "status": "queued"}]), agora)
    ok("run preso na fila reprova", not presa[2]["ok"])
    ok("despachante e relógio rodando não contam como fila", r[2]["ok"])
    parado = avaliar(dict(bom, ultimo_run={"despachante.yml": "2026-10-10T21:00:00Z",
                                           "relogio.yml": None}), agora)
    ok("despachante parado há 120 min reprova; relógio sem run reprova",
       not parado[3]["ok"] and not parado[4]["ok"])
    sem = avaliar(dict(bom, segredos={"ROBO_TOKEN": True}), agora)
    ok("segredo ausente reprova e é nomeado", not sem[5]["ok"] and "ROBO_DEPLOY_KEY" in sem[5]["detalhe"])
    ens = avaliar(dict(bom, ensaio_real={"conclusion": "failure", "createdAt": "2026-10-10T18:20:00Z"}), agora)
    ok("ensaio real vermelho reprova", not ens[6]["ok"])
    velho = avaliar(dict(bom, ensaio_real={"conclusion": "success", "createdAt": "2026-10-09T18:20:00Z"}), agora)
    ok("ensaio real verde de ontem não vale por hoje", not velho[6]["ok"])
    ok("a noite seguinte às 23h é a de amanhã", noite_seguinte(agora) == "2026-10-11")
    ok("a noite seguinte às 00:20 é a de hoje", noite_seguinte(dt.datetime(2026, 10, 11, 0, 20)) == "2026-10-11")
    # F36: o cron das 22:53 chegou às 01:20 e às 02:10 de 11/10 e julgou a noite de 12/10.
    ok("às 01:20 a noite é a que está em curso (F36)",
       noite_seguinte(dt.datetime(2026, 10, 11, 1, 20)) == "2026-10-11")
    ok("às 01:20 a checagem está atrasada e não julga; às 23:00 e à 00:20, julga",
       atrasada(dt.datetime(2026, 10, 11, 1, 20)) and not atrasada(agora)
       and not atrasada(dt.datetime(2026, 10, 11, 0, 20)))
    meia_noite = avaliar(dict(bom, ensaio_real={"conclusion": "success",
                                                "createdAt": "2026-10-10T21:44:00Z"}),
                         dt.datetime(2026, 10, 11, 0, 20))
    ok("à 00:20, o ensaio verde das 21:44 da véspera vale pela noite (F36)", meia_noite[6]["ok"])
    # F37: a resposta real da API (forma de GET /actions/runs) e o erro real do `gh`.
    api = [{"total_count": 2, "workflow_runs": [
        {"id": 1, "name": "Noturno — triagem da fila", "path": ".github/workflows/noturno_triagem.yml",
         "status": "in_progress"},
        {"id": 2, "name": "Despachante", "path": ".github/workflows/despachante.yml", "status": "in_progress"}]},
        None]
    fila = avaliar(dict(bom, runs_abertos=abertos_da_api(api)), agora)
    ok("run aberto lido da API reprova a fila; o despachante não (F37)",
       not fila[2]["ok"] and "noturno_triagem.yml" in fila[2]["detalhe"]
       and "despachante" not in fila[2]["detalhe"])
    _f43 = abertos_da_api([{"workflow_runs": [
        {"id": 7, "path": ".github/workflows/noturno_diarios.yml", "status": "in_progress",
         "head_branch": "ensaio-real/2026-10-11-1"},
        {"id": 8, "path": ".github/workflows/noturno_sinais.yml", "status": "queued",
         "head_branch": "coleta-dia/2026-10-11-protocolo"}]}])
    ok("F43: run de ensaio-real/* e coleta-dia/* não entra na fila", _f43 == [])
    _ag = dt.datetime(2026, 10, 11, 20, 20)
    _r43 = avaliar(dict(bom, ultimo_run={"despachante.yml": "2026-10-11T19:06:00Z",
                                         "relogio.yml": "2026-10-11T20:08:00Z"}), _ag)
    ok("F43: despachante dentro do relógio conta como despachante vivo",
       [x for x in _r43 if x["pergunta"].startswith("despachante")][0]["ok"])

    class _R:
        def __init__(self, rc, out="", err=""):
            self.returncode, self.stdout, self.stderr = rc, out, err
    erros = []
    falho = _gh_json(["run", "list", "--json", "workflowName,status,path"], erros,
                     executar=lambda *a, **k: _R(1, "", 'Unknown JSON field: "path"'))
    ok("erro do `gh` fica anotado, não vira lista vazia (F37)",
       falho is None and erros and "Unknown JSON field" in erros[0])
    vazio = _gh_json(["api", "x"], erros, executar=lambda *a, **k: _R(0, "[]"))
    ok("resposta vazia legítima (`[]`) é resposta", vazio == [] and len(erros) == 1)
    cega = avaliar(dict(bom, erros_de_consulta=erros), agora)
    ok("consulta que falhou deixa a checagem vermelha e nomeada (F37)",
       not cega[7]["ok"] and "Unknown JSON field" in cega[7]["detalhe"])
    import inspect
    ok("trava: `avaliar` não lê disco nem vai à rede",
       not any(x in inspect.getsource(avaliar) for x in ("open(", "subprocess", "_gh_json")))
    print("✗ AUTOTESTE: %d falha(s)" % len(falhas) if falhas else "✓ AUTOTESTE OK")
    return 1 if falhas else 0


def main() -> int:
    argv = sys.argv[1:]
    if "--autoteste" in argv:
        return autoteste()
    agora = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    noite = noite_seguinte(agora)
    if atrasada(agora) and "--forcar" not in argv:
        # F36: cron atrasado para dentro da janela. Sai em silêncio e verde, com o motivo escrito:
        # a noite já abriu, e quem a julga agora é a conferência da abertura, não a pré-noite.
        doc = {"noite": noite, "conferido_em": agora.strftime("%Y-%m-%dT%H:%M:%SZ"),
               "verde": True, "atrasada": True, "perguntas": []}
        saida = argv[argv.index("--saida") + 1] if "--saida" in argv else f"preflight-{noite}.json"
        pathlib.Path(saida).write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n",
                                       encoding="utf-8", newline="\n")
        print(f"· pré-noite ATRASADA ({agora.strftime('%H:%M')} UTC, noite de {noite} já aberta)"
              " — sem veredito; a abertura é conferida por quem confere a abertura")
        return 0
    resultado = avaliar(coletar_fatos(agora), agora)
    vermelhos = [x for x in resultado if not x["ok"]]
    doc = {"noite": noite, "conferido_em": agora.strftime("%Y-%m-%dT%H:%M:%SZ"),
           "verde": not vermelhos, "perguntas": resultado}
    saida = argv[argv.index("--saida") + 1] if "--saida" in argv else f"preflight-{noite}.json"
    pathlib.Path(saida).write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    for x in resultado:
        print(f"  {'✓' if x['ok'] else '✗'} {x['pergunta']} — {x['detalhe']}")
    print(f"{'✓ PRÉ-NOITE VERDE' if not vermelhos else '✗ PRÉ-NOITE VERMELHA'} · noite de {noite}")
    if vermelhos and "--abrir-issue" in argv:
        abrir_issue(noite, vermelhos)
    return 1 if vermelhos else 0


if __name__ == "__main__":
    sys.exit(main())
