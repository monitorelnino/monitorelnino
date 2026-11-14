#!/usr/bin/env python3
"""Sonda 4 (não grava em data/): a API pública da plataforma do MapBiomas — temas de fogo e água, categoria de estados, e uma estatística mensal por estado."""
import json, urllib.request, urllib.parse
from coletores_base import ua_de

API = "https://prd.plataforma.mapbiomas.org/api/v1/brazil/"
def get(caminho):
    with urllib.request.urlopen(urllib.request.Request(API + caminho, headers={"User-Agent": ua_de("sondar_api_mapbiomas")}), timeout=90) as r:
        return json.loads(r.read())

temas = get("themes?page=1&pageSize=1000&expand=false")
lista = temas.get("themes") or temas.get("data") or []
print("CHAVES DA RESPOSTA", list(temas.keys()), "| exemplo:", json.dumps(lista[:1], ensure_ascii=False)[:600])
for t in lista:
    print("TEMA", t.get("key"), "|", (t.get("name") or {}).get("pt-BR"))
for chave in [t.get("key") for t in lista]:
    if not chave:
        continue
    try:
        d = get("themes/by/key/" + urllib.parse.quote(chave))
    except Exception as e:  # noqa: BLE001
        print("   ERRO", chave, e); continue
    subs = d.get("subthemes") or (d.get("theme") or {}).get("subthemes") or []
    for sb in subs:
        print("   SUB", chave, "→", sb.get("key"), "|", (sb.get("name") or {}).get("pt-BR"), "|", json.dumps({k: v for k, v in sb.items() if k not in ("name", "description", "key", "id", "icon")}, ensure_ascii=False)[:400])
cats = get("territories/categories")
for c in cats.get("categories", []):
    print("CAT", c.get("id"), c.get("key"), (c.get("name") or {}).get("pt-BR"), c.get("parentId"))
