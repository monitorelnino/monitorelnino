#!/usr/bin/env python3
"""Sonda 4 (não grava em data/): a API pública da plataforma do MapBiomas — temas de fogo e água, categoria de estados, e uma estatística mensal por estado."""
import json, urllib.request, urllib.parse
from coletores_base import ua_de

API = "https://prd.plataforma.mapbiomas.org/api/v1/brazil/"
def get(caminho):
    with urllib.request.urlopen(urllib.request.Request(API + caminho, headers={"User-Agent": ua_de("sondar_api_mapbiomas")}), timeout=90) as r:
        return json.loads(r.read())

temas = get("themes?page=1&pageSize=1000&expand=true")
for t in temas.get("themes", []):
    if any(k in (t.get("key") or "") for k in ("fire", "fogo", "water", "agua", "burn")) or "fogo" in json.dumps(t.get("name", {}), ensure_ascii=False).lower() or "água" in json.dumps(t.get("name", {}), ensure_ascii=False).lower():
        print("TEMA", t.get("key"), t.get("name", {}).get("pt-BR"))
        for s in t.get("subthemes", []) or []:
            print("   SUB", s.get("key"), "|", (s.get("name") or {}).get("pt-BR"), "|", {k: s.get(k) for k in ("years", "yearsRange", "periodicity", "temporalResolution", "months", "dates") if s.get(k)})
print("TEMAS (todas as chaves):", [t.get("key") for t in temas.get("themes", [])])
cats = get("territories/categories")
for c in cats.get("categories", []):
    print("CAT", c.get("id"), c.get("key"), (c.get("name") or {}).get("pt-BR"))
