#!/usr/bin/env python3
"""Sonda (só no ramo coleta-dia): em que tabela do SIDRA vive o PIB per capita por UF?
Lê o catálogo de agregados do IBGE e imprime as tabelas cujo nome ou variável cita "per capita"."""
import json, sys, pathlib, urllib.request
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from coletores_base import ua_de

def pega(u):
    req = urllib.request.Request(u, headers={"User-Agent": ua_de("sonda SIDRA PIB per capita")})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8", "replace"))

cat = pega("https://servicodados.ibge.gov.br/api/v3/agregados")
for pesq in cat:
    for ag in pesq.get("agregados", []):
        n = ag.get("nome", "")
        if "per capita" in n.lower() or ("produto interno bruto" in n.lower() and "unidade" in n.lower()):
            print(f"[{pesq.get('nome')}] t/{ag.get('id')}: {n}")
for t in ("5938", "7358", "7359", "1996"):
    try:
        m = pega(f"https://servicodados.ibge.gov.br/api/v3/agregados/{t}/metadados")
        print(f"\n== t/{t}: {m.get('nome')} · níveis {m.get('nivelTerritorial')} · periodicidade {m.get('periodicidade',{}).get('fim')}")
        for v in m.get("variaveis", []):
            if "per capita" in v.get("nome", "").lower():
                print(f"   v/{v['id']}: {v['nome']} ({v.get('unidade')})")
    except Exception as e:
        print(f"\n== t/{t}: {type(e).__name__}: {e}")
