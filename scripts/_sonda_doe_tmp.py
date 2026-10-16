"""Sonda pontual (diag 16/10): OpenAQ v3 — rota de últimas medições de PM2,5 e lista de locais BR."""
import json, os, sys, urllib.request
sys.path.insert(0, ".")
from coletores_base import UA
k = os.environ.get("OPENAQ_API_KEY") or ""
print("chave presente:", bool(k), len(k))
def get(u):
    r = urllib.request.Request(u, headers={"User-Agent": UA, "X-API-Key": k})
    try:
        with urllib.request.urlopen(r, timeout=60) as f:
            return f.status, json.loads(f.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:300]
for u in ("https://api.openaq.org/v3/parameters/2/latest?limit=1000",
          "https://api.openaq.org/v3/parameters/2/latest?limit=1000&iso=BR",
          "https://api.openaq.org/v3/locations?iso=BR&limit=1000"):
    st, d = get(u)
    print("\n", u, st)
    if isinstance(d, dict):
        print(" meta:", json.dumps(d.get("meta"))[:300])
        res = d.get("results") or []
        print(" n:", len(res), "1º:", json.dumps(res[0], ensure_ascii=False)[:900] if res else None)
        if "locations" in u:
            print(" providers:", sorted({str((x.get("provider") or {}).get("name")) for x in res})[:40])
            print(" com datetimeLast 2026-10:", sum(1 for x in res if "2026-10" in json.dumps(x.get("datetimeLast"))))
    else:
        print(d)
