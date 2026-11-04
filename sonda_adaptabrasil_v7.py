#!/usr/bin/env python3
"""Sonda v8 (editoria, 04/11/2026 16:25): hierarquia + UM download de teste por indicador (rota
/geometria/data, a outra do botão Download). v7 mostrou que `location` vem na RAIZ da resposta.
Cliente identificado, sem cookie/token, um GET por tentativa, 401/403 para. Só imprime (SONDA>);
não grava dado. Vive só no ramo coleta-dia/*."""
import json
import re
import sys

sys.path.insert(0, ".")
from coletores_base import buscar_uma_vez

B = "https://sistema.adaptabrasil.mcti.gov.br/api"
ALVOS = [(2, "estresse hídrico"), (50076, "arboviroses")]


def get(url, mostrar=True):
    try:
        c = buscar_uma_vez(url, timeout=180)
        print(f"SONDA> GET {url[:230]} -> 200, {len(c)} bytes" + (f", início {c[:120]!r}" if mostrar else ""))
        return c
    except Exception as e:  # noqa: BLE001 - sonda: registra a recusa/erro e segue
        print(f"SONDA> GET {url[:230]} -> ERRO {type(e).__name__}: {str(e)[:300]}")
        return None


def descrever(c):
    try:
        d = json.loads(c)
    except ValueError:
        print(f"SONDA> arquivo não é JSON; início {c[:200]!r}")
        return
    if isinstance(d, dict):
        print(f"SONDA> arquivo chaves raiz: {list(d)[:12]}")
        fs = d.get("features") or []
        print(f"SONDA> features: {len(fs)}")
        if fs:
            pr = fs[0].get("properties", {})
            print(f"SONDA> properties da 1ª feature: {json.dumps(pr, ensure_ascii=False)[:700]}")
        resto = {k: v for k, v in d.items() if k != "features"}
        print(f"SONDA> metadados fora de features: {json.dumps(resto, ensure_ascii=False)[:500]}")
        datas = sorted(set(re.findall(r'"[^"]*(?:edi|vers|atualiz|data|date)[^"]*"\s*:\s*"[^"]{0,40}"', c.decode("utf-8", "replace")[:400000], re.I)))[:8]
        print(f"SONDA> campos de edição/data: {datas}")


for i, nome in ALVOS:
    r = get(f"{B}/geometria/data/{i}/BR/null/2020/municipio/GEOJSONz", mostrar=False)
    if not r:
        continue
    try:
        loc = json.loads(r).get("location")
    except ValueError:
        loc = None
    print(f"SONDA> {nome} id={i} location={loc}")
    if loc:
        arq = get(loc, mostrar=False)
        if arq:
            descrever(arq)
