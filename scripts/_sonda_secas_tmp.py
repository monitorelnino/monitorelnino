"""Sonda pontual (diag 16/10): de onde vem a lista de mapas (com shapefile) do Monitor de Secas."""
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
print("urls:", sorted(set(re.findall(r'https?://[A-Za-z0-9.\-]+(?:\.gov\.br|amazonaws\.com|funceme\.br)[A-Za-z0-9_./\-]*', js))))
for pad in (r'.{0,140}["\'`/]mapas?[/"\'`?].{0,140}', r'.{0,160}shapefile.{0,160}', r'.{0,200}mapaFacade\.\w+\(.{0,80}', r'.{0,120}\.get\(.{0,200}'):
    vistos = sorted(set(re.findall(pad, js)))[:14]
    print("\n##", pad, len(vistos))
    for v in vistos:
        print("  ", v[:380])
