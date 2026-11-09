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

for u in ["https://apisidra.ibge.gov.br/values/t/5938/n3/all/v/37/p/2023?formato=json",
          "https://apisidra.ibge.gov.br/values/t/6579/n3/all/v/9324/p/2023?formato=json",
          "https://apisidra.ibge.gov.br/values/t/6579/n3/all/v/all/p/last?formato=json"]:
    try:
        d = pega(u); print(f"\n== {u}\n   {len(d)} linhas\n   {json.dumps(d[:3], ensure_ascii=False)[:1200]}")
    except Exception as e:
        print(f"\n== {u}\n   {type(e).__name__}: {e}")
