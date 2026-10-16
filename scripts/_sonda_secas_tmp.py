"""Sonda pontual (diag 16/10): shapefile mensal do Monitor de Secas no S3 da ANA."""
import io, re, sys, zipfile, urllib.request
sys.path.insert(0, ".")
from coletores_base import UA
def get(u, metodo="GET"):
    r = urllib.request.Request(u, headers={"User-Agent": UA}, method=metodo)
    try:
        with urllib.request.urlopen(r, timeout=120) as f:
            return f.status, f.read(), dict(f.headers)
    except urllib.error.HTTPError as e:
        return e.code, b"", dict(e.headers or {})
    except Exception as e:
        return str(e)[:100], b"", {}
st, c, h = get("https://monitordesecas.ana.gov.br/main-es2015.fa1ed2e57f145c927f52.js")
js = c.decode("utf-8", "replace")
i = js.find("uploads/mapas/${")
print("CTX:", js[i - 900: i + 400])
S3 = "https://ana-monitor-secas-files.s3.sa-east-1.amazonaws.com/uploads/mapas/"
st, c, h = get(S3[:-1].rsplit("/uploads", 1)[0] + "/?prefix=uploads/mapas/&max-keys=50")
print("\nLIST", st, c[:1500])
for nome in ("Setembro2026", "Agosto2026", "setembro2026", "Set2026", "Setembro_2026"):
    for ext in (".zip", ".gpkg", ".png"):
        st, c, h = get(S3 + nome + ext, "HEAD")
        print("HEAD", nome + ext, st, h.get("Content-Length"), h.get("Last-Modified"))
