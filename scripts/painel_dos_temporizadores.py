#!/usr/bin/env python3
"""
scripts/painel_dos_temporizadores.py — previsto × iniciado × concluído, e quem disparou
========================================================================================
Item 5 do `HANDOVER_garantia_dos_temporizadores_04-10-2026.md` (rev. 2).

POR QUE "QUEM DISPAROU" É A COLUNA QUE IMPORTA
----------------------------------------------
Um temporizador que rodou não diz nada sobre a saúde do sistema: o que diz é **quem o fez rodar**.
Se a abertura da noite roda sempre pelo cron primário, os outros três observadores são teoria. Se
ela passa a rodar pelo despachante, o cron primário está falhando — e isso aparece aqui antes de
alguém notar dado velho no site.

O painel também vigia o próprio relógio da nuvem do Claude: sem disparo de origem
`relogio-claude` por mais de 130 minutos, a rotina está pausada, a conexão com o GitHub expirou ou
a assinatura parou — e o despachante abre Issue, que o GitHub manda por e-mail à editoria.

USO
  python3 scripts/painel_dos_temporizadores.py --autoteste
  python3 scripts/painel_dos_temporizadores.py            # lê a API e imprime o painel
  python3 scripts/painel_dos_temporizadores.py --portao    # reprova se algo está além da tolerância
"""
import datetime as dt
import json
import pathlib
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

REGISTRO = RAIZ / "config" / "temporizadores.json"
ORIGEM_POR_EVENTO = {"schedule": "cron primário", "workflow_dispatch": "despachante ou à mão",
                     "push": "relógio da nuvem do Claude", "workflow_run": "elo anterior"}
SILENCIO_DO_RELOGIO_MIN = 130


def origem_legivel(execucao: dict) -> str:
    """De onde veio esta execução, em português. Função pura."""
    return ORIGEM_POR_EVENTO.get(str((execucao or {}).get("event") or ""), "desconhecida")


def linha_do_painel(temporizador: dict, execucoes: list, agora: dt.datetime) -> dict:
    """Uma linha: previsto, iniciado, concluído, quem disparou, atraso. Função pura."""
    from scripts.despachar_temporizadores import (atraso_min, e_dia_previsto, inicio_da_janela,
                                                  na_janela)
    janela = temporizador.get("janela") or {}
    desde = inicio_da_janela(agora, janela)
    desta = [e for e in (execucoes or []) if str(e.get("createdAt") or "") >= desde]
    desta.sort(key=lambda e: str(e.get("createdAt") or ""))
    primeira = desta[0] if desta else None
    concluida = next((e for e in reversed(desta) if e.get("conclusion") == "success"), None)
    cron = str(temporizador.get("cron_primario") or "")
    partes = cron.split()
    # Cron com lista de minutos ("7,27,47 * * * *") ou de horas não vira "HH:MM": o previsto dele é
    # "a cada 20 min", e enfiar isso numa coluna de hora produzia a string do cron no meio da
    # tabela. Quando não dá uma hora, mostra-se o cron, mas encurtado para caber.
    if len(partes) >= 2 and partes[0].isdigit() and partes[1].isdigit():
        previsto = f"{partes[1].zfill(2)}:{partes[0].zfill(2)}"
    elif len(partes) >= 2 and "," in partes[0] and partes[1] == "*":
        previsto = f":{partes[0]}"
    else:
        previsto = cron[:9]
    return {
        "id": temporizador.get("id"),
        "previsto_utc": previsto,
        "iniciado": (str(primeira.get("createdAt"))[11:16] if primeira else None),
        "concluido": (str(concluida.get("createdAt"))[11:16] if concluida else None),
        "disparado_por": (origem_legivel(primeira) if primeira else None),
        # 04/10/2026: o atraso só é atraso no DIA em que o temporizador roda. Sem isto, a auditoria
        # de segunda apareceu "atrasada 487 min" num domingo — e alarme que grita no dia errado
        # ensina a editoria a ignorar o painel.
        "atraso_min": (atraso_min(temporizador, agora)
                       if primeira is None and na_janela(agora, janela)
                       and e_dia_previsto(temporizador.get("cron_primario"), agora) else 0),
        "na_janela": na_janela(agora, janela)
                     and e_dia_previsto(temporizador.get("cron_primario"), agora),
        "gravidade": temporizador.get("gravidade"),
        "tolerancia_atraso_min": temporizador.get("tolerancia_atraso_min"),
    }


def alem_da_tolerancia(linha: dict) -> bool:
    """Esta linha passou da tolerância sem ter iniciado? Função pura."""
    if linha.get("iniciado"):
        return False
    tol = linha.get("tolerancia_atraso_min")
    return bool(tol) and int(linha.get("atraso_min") or 0) > int(tol)


def ultimo_tique_do_relogio(execucoes_do_relogio: list) -> str | None:
    """O instante do último disparo vindo do relógio da nuvem. Função pura."""
    pushes = [e for e in (execucoes_do_relogio or []) if str(e.get("event")) == "push"]
    if not pushes:
        return None
    return max(str(e.get("createdAt") or "") for e in pushes)


def _autoteste() -> int:
    falhas = []

    def ok(nome, cond):
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    d = dt.datetime
    agora = d(2026, 10, 4, 3, 0)
    t = {"id": "abertura", "workflow": "a.yml", "cron_primario": "7 1 * * *",
         "janela": {"inicio_utc": "01:00", "fim_utc": "09:00"},
         "tolerancia_atraso_min": 60, "gravidade": "alta"}

    ok("schedule é o cron primário", origem_legivel({"event": "schedule"}) == "cron primário")
    ok("push é o relógio da nuvem",
       origem_legivel({"event": "push"}) == "relógio da nuvem do Claude")
    ok("evento desconhecido é nomeado como desconhecido",
       origem_legivel({"event": "outro"}) == "desconhecida")

    l = linha_do_painel(t, [{"createdAt": "2026-10-04T01:08:00Z", "event": "schedule",
                             "conclusion": "success"}], agora)
    ok("o previsto sai do cron", l["previsto_utc"] == "01:07")
    ok("o iniciado é a hora da primeira execução da janela", l["iniciado"] == "01:08")
    ok("o concluído é a última execução com sucesso", l["concluido"] == "01:08")
    ok("quem disparou é nomeado", l["disparado_por"] == "cron primário")
    ok("iniciado no horário não tem atraso", l["atraso_min"] == 0)

    l2 = linha_do_painel(t, [], agora)
    ok("sem execução na janela, o atraso é contado", l2["atraso_min"] == 113)
    ok("sem execução, não há quem disparou", l2["disparado_por"] is None)
    ok("113 minutos passam da tolerância de 60", alem_da_tolerancia(l2))
    ok("linha que iniciou nunca está além da tolerância",
       not alem_da_tolerancia(dict(l2, iniciado="01:08")))

    l3 = linha_do_painel(t, [{"createdAt": "2026-10-04T02:40:00Z", "event": "workflow_dispatch",
                              "conclusion": None}], agora)
    ok("recuperação pelo despachante aparece como tal",
       l3["disparado_por"] == "despachante ou à mão")
    ok("execução sem conclusão não conta como concluída", l3["concluido"] is None)

    ok("execução de ontem não entra nesta janela",
       linha_do_painel(t, [{"createdAt": "2026-10-03T01:08:00Z", "event": "schedule"}],
                       agora)["iniciado"] is None)

    ok("o último tique do relógio é o push mais recente",
       ultimo_tique_do_relogio([{"createdAt": "2026-10-04T01:07:00Z", "event": "push"},
                                {"createdAt": "2026-10-04T02:07:00Z", "event": "push"},
                                {"createdAt": "2026-10-04T02:30:00Z", "event": "schedule"}])
       == "2026-10-04T02:07:00Z")
    ok("sem push, não há tique", ultimo_tique_do_relogio([{"event": "schedule"}]) is None)

    from scripts.despachar_temporizadores import relogio_silencioso
    ok("duas horas sem tique ainda não é silêncio",
       not relogio_silencioso("2026-10-04T01:07:00", agora))
    ok("três horas sem tique é silêncio",
       relogio_silencioso("2026-10-03T23:30:00", agora))

    import dis
    nomes = set()
    for nome_obj, obj in list(globals().items()):
        if nome_obj in ("_autoteste", "main", "montar", "_gh", "execucoes_de"):
            continue
        codigo = getattr(obj, "__code__", None)
        if codigo is not None:
            nomes |= {i.argval for i in dis.get_instructions(codigo) if isinstance(i.argval, str)}
    ok("trava estrutural: o painel não escreve nem dispara",
       not ({"gravar", "write_text", "disparar"} & nomes))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else "✓ AUTOTESTE OK — 19 casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def _gh(args: list) -> str:
    try:
        r = subprocess.run(["gh"] + args, cwd=RAIZ, capture_output=True, text=True, timeout=120)
        return r.stdout
    except (OSError, subprocess.SubprocessError):
        return ""


_IDS = {}


def id_do_workflow(workflow: str):
    """O id numérico do workflow, pela API. Cacheado por execução do painel.

    04/10/2026: `gh run list --workflow <nome>` com um workflow que ainda NÃO existe na `main`
    devolve as execuções do repositório INTEIRO — e o painel atribuiu a `pacote_do_blog.yml` runs
    de outro workflow, dizendo que o relógio da nuvem as havia disparado. O campo `path` não existe
    no `gh run list`; o que existe é `workflowDatabaseId`, e com ele o filtro é exato. Workflow que
    não está na `main` devolve None, e então a resposta correta é lista vazia — "não rodou" e não
    "rodou tudo".
    """
    if workflow in _IDS:
        return _IDS[workflow]
    saida = _gh(["api", "repos/{owner}/{repo}/actions/workflows", "--jq",
                 f'.workflows[] | select(.path | endswith("/{workflow}")) | .id'])
    linha = (saida or "").strip().splitlines()
    _IDS[workflow] = int(linha[0]) if linha and linha[0].strip().isdigit() else None
    return _IDS[workflow]


def execucoes_de(workflow: str) -> list:
    """As execuções do workflow, filtradas pelo id — nunca as do repositório inteiro."""
    ident = id_do_workflow(workflow)
    if ident is None:
        return []
    saida = _gh(["run", "list", "--workflow", workflow, "--limit", "20",
                 "--json", "createdAt,status,conclusion,event,workflowDatabaseId"])
    try:
        bruto = json.loads(saida) if saida.strip() else []
    except json.JSONDecodeError:
        return []
    return [e for e in bruto if e.get("workflowDatabaseId") == ident]


def main() -> int:
    argv = sys.argv[1:]
    if "--autoteste" in argv:
        return _autoteste()
    agora = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    reg = json.loads(REGISTRO.read_text(encoding="utf-8"))
    cache = {}
    linhas = []
    for t in reg.get("temporizadores") or []:
        w = t.get("workflow")
        if w not in cache:
            cache[w] = execucoes_de(w)
        linhas.append(linha_do_painel(t, cache[w], agora))

    print(f"painel dos temporizadores · {agora.strftime('%H:%M')} UTC")
    print(f"  {'temporizador':24s} {'previsto':9s} {'iniciou':8s} {'concluiu':9s} quem disparou")
    for l in linhas:
        if not l["na_janela"]:
            continue
        print(f"  {str(l['id'])[:24]:24s} {l['previsto_utc']:9s} "
              f"{(l['iniciado'] or '—'):8s} {(l['concluido'] or '—'):9s} "
              f"{l['disparado_por'] or ('atrasado ' + str(l['atraso_min']) + ' min')}")

    relogio = execucoes_de("relogio.yml")
    tique = ultimo_tique_do_relogio(relogio)
    from scripts.despachar_temporizadores import relogio_silencioso
    calado = relogio_silencioso((tique or "").replace("Z", ""), agora)
    print(f"  relógio da nuvem do Claude: último tique {tique or 'nenhum'}"
          + (" · SILENCIOSO" if calado else " · vivo"))

    atrasados = [l for l in linhas if alem_da_tolerancia(l)]
    if "--portao" in argv:
        if atrasados:
            print(f"✗ TEMPORIZADORES: {len(atrasados)} além da tolerância: "
                  + ", ".join(str(l["id"]) for l in atrasados))
            return 1
        print("✓ PAINEL DOS TEMPORIZADORES OK — nada além da tolerância nesta janela.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
