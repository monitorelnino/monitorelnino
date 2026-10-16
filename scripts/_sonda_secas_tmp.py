"""Sonda pontual (diag 16/10): previsão municipal do INMET (rota previsao/<geocode>)."""
import json, sys, time, urllib.request
sys.path.insert(0, ".")
from coletores_base import UA
for geo in ("5300108", "1505650", "4314902"):
    u = f"https://apiprevmet3.inmet.gov.br/previsao/{geo}"
    t = time.time()
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=60) as f:
            c = f.read(); st = f.status; h = dict(f.headers)
    except urllib.error.HTTPError as e:
        c = e.read()[:300]; st = e.code; h = {}
    except Exception as e:
        c = str(e).encode(); st = "erro"; h = {}
    print("\n", u, st, len(c), f"{time.time()-t:.1f}s", h.get("Cache-Control"))
    try:
        d = json.loads(c)
        print(json.dumps(d, ensure_ascii=False)[:1200])
    except Exception:
        print(c[:300])
st = None
try:
    with urllib.request.urlopen(urllib.request.Request("https://apiprevmet3.inmet.gov.br/robots.txt", headers={"User-Agent": UA}), timeout=30) as f:
        print("robots", f.status, f.read()[:300])
except Exception as e:
    print("robots", e)
