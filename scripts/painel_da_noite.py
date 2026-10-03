#!/usr/bin/env python3
"""Painel da noite: cada elo da corrente, com início, fim e se terminou dentro da janela.

Item A.5 do handover da corrente noturna (03/10/2026). O diagnóstico que o motivou: na noite de
02→03/10 o elo das **evidências e OCR não rodou**, e ninguém viu — a corrente terminou, os dados
foram publicados, e a falta só apareceu quando a central foi conferir à mão. Elo que não roda não
deixa buraco visível: deixa um arquivo com a data de ontem, que se parece com um arquivo normal.

O painel é append-only, uma linha por elo por noite:

    {"noite": "2026-10-04", "elo": "diarios", "inicio": "01:02", "fim": "04:49",
     "minutos": 227, "dentro_da_janela": true, "conclusao": "success"}

A JANELA é 22h–06h de Brasília (01:00–09:00 UTC). "Dentro da janela" é o que a editoria pediu para
ver de relance: um elo que termina às 7h da manhã roubou a manhã da redação, e isso não aparece no
log do GitHub sem abrir cada run.

O portão (`--portao`) reprova quando um elo da corrente **não tem linha na noite anterior**: é a
forma de a ausência virar vermelho em vez de silêncio.

USO (no fim de cada elo, dentro do workflow)
    python3 scripts/painel_da_noite.py --registrar diarios --inicio 01:02 --conclusao success
    python3 scripts/painel_da_noite.py --relatorio
    python3 scripts/painel_da_noite.py --portao
    python3 scripts/painel_da_noite.py --autoteste
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

ARQUIVO = "painel_da_noite.json"
# Os elos da corrente, na ordem do handover. A busca web não é elo: ela roda em paralelo, com os
# seus cinco horários próprios — e por isso entra no painel como rotina à parte, sem exigência de
# estar na corrente.
ELOS = ("diarios", "descoberta", "evidencias", "juiz", "sinais", "triagem", "publicar")
PARALELAS = ("busca_web",)
JANELA_UTC = (1, 9)   # 01:00 às 09:00 UTC = 22h às 06h de Brasília
GOV = ("Painel da noite (item A.5 do handover de 03/10/2026): uma linha por elo por noite, com "
       "início, fim e se terminou dentro da janela de 22h às 06h. Append-only. Serve para que elo "
       "que NÃO rodou apareça — foi o que faltou na noite de 02→03/10, quando as evidências não "
       "rodaram e nada acusou.")


def minutos_entre(inicio: str, fim: str):
    """Minutos entre dois HH:MM, virando a meia-noite quando preciso. Função pura."""
    def em_minutos(hhmm):
        try:
            h, m = (int(x) for x in str(hhmm).split(":")[:2])
            return h * 60 + m
        except (ValueError, TypeError):
            return None
    a, b = em_minutos(inicio), em_minutos(fim)
    if a is None or b is None:
        return None
    return (b - a) if b >= a else (b + 24 * 60 - a)


def dentro_da_janela(fim_utc: str, janela=JANELA_UTC) -> bool:
    """O elo terminou dentro da janela noturna? Função pura."""
    try:
        h = int(str(fim_utc).split(":")[0])
    except (ValueError, TypeError):
        return False
    inicio, fim = janela
    return inicio <= h < fim if inicio < fim else (h >= inicio or h < fim)


def linha(elo: str, noite: str, inicio: str, fim: str, conclusao: str) -> dict:
    """A linha do painel. Função pura — é ela que o autoteste exercita."""
    return {"noite": noite, "elo": elo, "inicio": inicio, "fim": fim,
            "minutos": minutos_entre(inicio, fim),
            "dentro_da_janela": dentro_da_janela(fim),
            "conclusao": conclusao or "desconhecida"}


def elos_que_faltaram(linhas: list, noite: str, elos=ELOS) -> list:
    """Os elos da corrente sem linha nesta noite. Função pura."""
    presentes = {l.get("elo") for l in linhas if l.get("noite") == noite}
    return [e for e in elos if e not in presentes]


def _autoteste() -> int:
    falhas = []

    def ok(nome, cond):
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    ok("minutos no mesmo dia", minutos_entre("01:00", "04:47") == 227)
    ok("minutos virando a meia-noite", minutos_entre("23:30", "00:15") == 45)
    ok("hora ilegível não quebra", minutos_entre("x", "01:00") is None)
    ok("fim dentro da janela", dentro_da_janela("04:49"))
    ok("fim na borda de abertura conta", dentro_da_janela("01:00"))
    ok("fim na borda de fechamento não conta", not dentro_da_janela("09:00"))
    ok("fim de manhã está fora", not dentro_da_janela("11:20"))
    ok("hora ilegível está fora", not dentro_da_janela("—"))

    l = linha("diarios", "2026-10-04", "01:02", "04:49", "success")
    ok("a linha traz os minutos", l["minutos"] == 227)
    ok("a linha diz se ficou na janela", l["dentro_da_janela"] is True)
    ok("a linha guarda a conclusão", l["conclusao"] == "success")
    ok("sem conclusão, fica declarado",
       linha("x", "n", "01:00", "02:00", "")["conclusao"] == "desconhecida")

    linhas = [{"noite": "2026-10-04", "elo": "diarios"},
              {"noite": "2026-10-04", "elo": "descoberta"},
              {"noite": "2026-10-03", "elo": "evidencias"}]
    faltam = elos_que_faltaram(linhas, "2026-10-04")
    ok("elo que não rodou aparece", "evidencias" in faltam and "juiz" in faltam)
    ok("elo de outra noite não conta como presente", "evidencias" in faltam)
    ok("noite completa não acusa nada",
       elos_que_faltaram([{"noite": "n", "elo": e} for e in ELOS], "n") == [])
    ok("a busca web não é elo da corrente", "busca_web" not in ELOS)
    ok("a governança diz por que o painel existe", "não rodou" in GOV or "NÃO rodou" in GOV)

    import dis
    nomes = set()
    for nome_obj, obj in list(globals().items()):
        if nome_obj in ("_autoteste", "main", "registrar"):
            continue
        codigo = getattr(obj, "__code__", None)
        if codigo is not None:
            nomes |= {i.argval for i in dis.get_instructions(codigo) if isinstance(i.argval, str)}
    ok("trava estrutural: as funções puras não escrevem",
       not ({"gravar", "gravar_em", "write_text"} & nomes))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else "✓ AUTOTESTE OK — 18 casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def registrar(elo: str, inicio: str, conclusao: str) -> dict:
    """Acrescenta a linha desta execução ao painel. Escreve."""
    from coletores_base import gravar, ler, hoje_editorial
    agora = dt.datetime.utcnow()
    fim = agora.strftime("%H:%M")
    # A NOITE é a data de abertura da janela: um elo que termina às 03h UTC pertence à noite que
    # começou no dia anterior, em Brasília. Sem isso, a mesma noite apareceria partida em dois dias.
    noite = (agora.date() if agora.hour >= JANELA_UTC[0] else
             agora.date() - dt.timedelta(days=1)).isoformat()
    doc = ler(ARQUIVO) or {"_governanca": GOV, "noites": []}
    doc.setdefault("_governanca", GOV)
    nova = linha(elo, noite, inicio or fim, fim, conclusao)
    doc.setdefault("noites", []).append(nova)
    doc["noites"] = doc["noites"][-400:]
    gravar(ARQUIVO, doc)
    return nova


def main() -> int:
    if "--autoteste" in sys.argv:
        return _autoteste()
    from coletores_base import ler
    if "--registrar" in sys.argv:
        i = sys.argv.index("--registrar")
        elo = sys.argv[i + 1]
        inicio = sys.argv[sys.argv.index("--inicio") + 1] if "--inicio" in sys.argv else None
        conclusao = sys.argv[sys.argv.index("--conclusao") + 1] if "--conclusao" in sys.argv else ""
        nova = registrar(elo, inicio, conclusao)
        print(f"painel da noite: {nova['elo']} {nova['inicio']}→{nova['fim']} "
              f"({nova['minutos']} min) · dentro da janela: "
              f"{'sim' if nova['dentro_da_janela'] else 'NÃO'}")
        return 0

    doc = ler(ARQUIVO) or {}
    linhas = doc.get("noites") or []
    if not linhas:
        print("painel da noite: sem linha registrada ainda (vale a partir da próxima corrente)")
        return 0
    ultima = max(l.get("noite", "") for l in linhas)
    desta = [l for l in linhas if l.get("noite") == ultima]
    print(f"noite de {ultima}:")
    for l in desta:
        print(f"   {l['elo']:12s} {l['inicio']}→{l['fim']}  {str(l['minutos']) + ' min':>8s}  "
              f"{'na janela' if l['dentro_da_janela'] else 'FORA DA JANELA':14s}  {l['conclusao']}")
    faltaram = elos_que_faltaram(linhas, ultima)
    fora = [l["elo"] for l in desta if not l["dentro_da_janela"]]
    if faltaram:
        print(f"   elo(s) que não rodaram: {', '.join(faltaram)}")
    if "--portao" in sys.argv:
        if faltaram:
            print(f"✗ PAINEL DA NOITE: {len(faltaram)} elo(s) sem registro na noite de {ultima}: "
                  f"{', '.join(faltaram)}")
            return 1
        if fora:
            print(f"⚠ PAINEL DA NOITE: {len(fora)} elo(s) terminaram fora da janela: "
                  f"{', '.join(fora)}")
        print(f"✓ PAINEL DA NOITE OK — os {len(ELOS)} elos da corrente rodaram na noite de {ultima}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
