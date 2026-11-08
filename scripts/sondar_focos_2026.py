#!/usr/bin/env python3
"""Sonda pontual (08/11/2026): que arquivos mensais/anuais de focos o INPE publica para 2026, e os totais
jun–set do satélite de referência. Só imprime; não grava em data/."""
import csv, io, re, sys, pathlib, urllib.request, collections, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from coletores_base import ua_de
UA = ua_de("sonda de focos 2026"); B = "https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/"
def get(u, t=120):
    return urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=t).read()
for d in ["", "mensal/", "anual/", "mensal/Brasil/", "mensal/Brasil_sat_ref/", "anual/Brasil_sat_ref/"]:
    try:
        h = get(B + d, 60).decode("utf-8", "replace"); print("DIR", d, re.findall(r'href="([^"?/][^"]*)"', h)[-12:])
    except Exception as e: print("DIR", d, type(e).__name__, getattr(e, "code", ""))
    time.sleep(1)
tot = {}
for m in ["202606", "202607", "202608", "202609"]:
    for cand in [f"mensal/Brasil_sat_ref/focos_mensal_br_ref_{m}.csv", f"mensal/Brasil/focos_mensal_br_{m}.csv"]:
        try:
            txt = get(B + cand).decode("utf-8", "replace"); r = list(csv.DictReader(io.StringIO(txt)))
            sat = collections.Counter(x.get("satelite", "?") for x in r)
            ref = sum(1 for x in r if (x.get("satelite") or "").upper().startswith("AQUA_M-T"))
            print("OK", cand, "linhas", len(r), "colunas", r[0].keys() if r else None, "sat", sat.most_common(4), "AQUA_M-T", ref)
            tot[m] = (len(r), ref); break
        except Exception as e: print("ERRO", cand, type(e).__name__, getattr(e, "code", ""))
        time.sleep(1)
print("TOTAIS jun-set (todos, ref):", sum(v[0] for v in tot.values()), sum(v[1] for v in tot.values()), tot)
