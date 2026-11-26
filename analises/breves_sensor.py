"""Sonda descartável: há sensor de baixo custo em Breves (PA) com dado de 2026 na RedeAr (IPAM)? Nada grava."""
import json, math, sys
sys.path.insert(0, "."); sys.path.insert(0, "scripts")
from coletores_base import buscar
B = (-1.68, -50.48)
for host in ("https://api.redear.org.br/v1/sensors", "https://hmg.api.redear.org.br/v1/sensors"):
    try:
        d = json.loads(buscar(host, timeout=90, origem="coletar_sinais_risco"))
        it = d if isinstance(d, list) else (d.get("data") or d.get("sensors") or d.get("results") or [])
        print("==", host, type(d).__name__, len(it), json.dumps(it[:1], ensure_ascii=False)[:800])
        for s in it:
            txt = json.dumps(s, ensure_ascii=False)
            lat = s.get("latitude") or s.get("lat") or (s.get("location") or {}).get("latitude") if isinstance(s, dict) else None
            lon = s.get("longitude") or s.get("lon") or (s.get("location") or {}).get("longitude") if isinstance(s, dict) else None
            perto = lat is not None and lon is not None and math.hypot(float(lat) - B[0], float(lon) - B[1]) < 1.0
            if perto or "reves" in txt or "araj" in txt or "UFPA" in txt:
                print("  ACHADO", txt[:1500])
    except Exception as e:
        print("==", host, "FALHA", type(e).__name__, str(e)[:300])
