"""Sonda pontual (diag 16/10): endpoints que o aplicativo do Monitor de Secas usa para mapas/shapefiles."""
import re, sys, json, urllib.request
sys.path.insert(0, ".")
from coletores_base import UA
def get(u):
    r = urllib.request.Request(u, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(r, timeout=90) as f:
            return f.status, f.read(), dict(f.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:300], {}
    except Exception as e:
        return str(e)[:100], b"", {}
st, c, h = get("https://monitordesecas.ana.gov.br/main-es2015.fa1ed2e57f145c927f52.js")
js = c.decode("utf-8", "replace")
for pad in (r"rpc/v1/[A-Za-z0-9_\-/]+", r"apiUrl[^,;]{0,120}", r"filesEndpoint[^,;]{0,160}", r"imagemMsUrl[^;]{0,160}",
            r"amazonaws\.com[^\"'`]{0,120}", r"environment\s*=\s*\{[^}]{0,600}"):
    vistos = sorted(set(re.findall(pad, js)))[:25]
    print("\n##", pad, len(vistos))
    for v in vistos:
        print("  ", v[:300])
