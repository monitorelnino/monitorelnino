#!/usr/bin/env python3
"""Sonda v7 (editoria, 04/11/2026 16:25): hierarquia + UM download de teste por indicador (rota
/geometria/data, a outra do botão Download). Cliente identificado, sem cookie/token, um GET por
tentativa, 401/403 para. Só imprime (linhas SONDA>); não grava dado. Vive só no ramo coleta-dia/*."""
import json
import sys

sys.path.insert(0, ".")
from coletores_base import buscar_uma_vez

B = "https://sistema.adaptabrasil.mcti.gov.br/api"


def nos(o, pai=""):
    if isinstance(o, dict):
        i, n = o.get("id"), o.get("nome") or o.get("name") or o.get("title")
        if i is not None and isinstance(n, str):
            yield i, n, pai
        for v in o.values():
            yield from nos(v, n if isinstance(n, str) else pai)
    elif isinstance(o, list):
        for v in o:
            yield from nos(v, pai)


def get(url):
    try:
        c = buscar_uma_vez(url, timeout=120)
        print(f"SONDA> GET {url[:150]} -> 200, {len(c)} bytes, início {c[:160]!r}")
        return c
    except Exception as e:  # noqa: BLE001 - sonda: registra a recusa/erro e segue
        print(f"SONDA> GET {url[:150]} -> ERRO {type(e).__name__}: {str(e)[:300]}")
        return None


h = get(B + "/hierarquia")
if not h:
    sys.exit(0)
lista = list(nos(json.loads(h)))
print(f"SONDA> nós com id+nome: {len(lista)}")
alvos = []
for chave in ("estresse hídrico", "dengue", "malária", "saúde"):
    for i, n, p in lista:
        if chave in n.lower() and i not in [a[0] for a in alvos]:
            alvos.append((i, n, p))
            print(f"SONDA> alvo {chave}: id={i} nome={n!r} pai={p!r}")
            break
for i, n, p in alvos[:2]:
    c = get(f"{B}/geometria/data/{i}/BR/null/2020/municipio/GEOJSONz")
    if not c:
        continue
    try:
        d = json.loads(c)
        loc = (d.get("data") or {}).get("location") if isinstance(d, dict) else None
        print(f"SONDA> resposta chaves={list(d)[:10] if isinstance(d, dict) else type(d)} location={loc}")
        if loc:
            get(loc if loc.startswith("http") else B.rsplit("/api", 1)[0] + loc)
    except ValueError:
        print("SONDA> resposta não é JSON")
