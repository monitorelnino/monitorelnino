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

import urllib.error
for t in list(range(5939, 5951)) + [6784, 7358, 7359, 7360, 7361, 7362, 1996, 2049, 7001, 6579]:
    u = f"https://apisidra.ibge.gov.br/values/t/{t}/n3/33/v/all/p/last?formato=json"
    try:
        d = pega(u)
        nomes = sorted({f"v/{l.get('D2C')} {l.get('D2N')} [{l.get('MN')}] {l.get('D3N')}" for l in d[1:]})
        pc = [n for n in nomes if "per capita" in n.lower()]
        print(f"\n== t/{t}: {len(d)-1} linhas; per capita: {pc if pc else 'nenhuma'}; exemplo: {nomes[:2]}")
    except urllib.error.HTTPError as e:
        print(f"\n== t/{t}: HTTP {e.code} {e.read(200).decode('utf-8','replace')}")
    except Exception as e:
        print(f"\n== t/{t}: {type(e).__name__}: {e}")
