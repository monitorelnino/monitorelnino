"""Sonda pontual (diag 16/10): de onde o aplicativo do Monitor de Secas tira a geometria."""
import re, sys, urllib.request
sys.path.insert(0, ".")
from coletores_base import UA
def get(u):
    r = urllib.request.Request(u, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(r, timeout=90) as f:
            return f.status, f.read().decode("utf-8", "replace"), dict(f.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:300].decode("utf-8", "replace"), {}
    except Exception as e:
        return str(e)[:100], "", {}
st, html, h = get("https://monitordesecas.ana.gov.br/")
js = re.findall(r'src="([^"]+\.js)"', html)
print("js:", js)
achados = set()
for nome in js:
    if "polyfill" in nome or "runtime" in nome:
        continue
    st, corpo, h = get("https://monitordesecas.ana.gov.br/" + nome)
    print(nome, st, len(corpo))
    for m in re.findall(r'["\'`](https?://[^"\'`\s]{6,200}|/?(?:rpc|api|data|geoserver|wms|wfs)[^"\'`\s]{0,160})["\'`]', corpo):
        achados.add(m)
    for m in re.finditer(r'(geojson|shapefile|\.shp|\.zip|topojson|\.json|wms|GetFeature)', corpo, re.I):
        achados.add("CTX " + corpo[max(0, m.start() - 120): m.end() + 60].replace("\n", " "))
for a in sorted(achados)[:120]:
    print(a[:260])
for u in ("https://apimsbr.ana.gov.br/rpc/v1/maps", "https://apimsbr.ana.gov.br/rpc/v1/mapas",
          "https://apimsbr.ana.gov.br/rpc/v1/shapefiles", "https://apimsbr.ana.gov.br/rpc/v1/geojson"):
    st, c, h = get(u)
    print("\nTENTA", u, st, c[:400])
