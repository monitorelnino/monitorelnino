"""Sonda pontual (diag 16/10): tamanho do anual de referência; geometria do Monitor de Secas (ANA)."""
import io, json, re, sys, time, zipfile, csv, collections, urllib.request
sys.path.insert(0, ".")
from coletores_base import UA
def get(u, metodo="GET", n=None):
    t = time.time()
    r = urllib.request.Request(u, headers={"User-Agent": UA}, method=metodo)
    try:
        with urllib.request.urlopen(r, timeout=120) as f:
            return f.status, (f.read() if n is None else f.read(n)), dict(f.headers), time.time() - t
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:400], dict(e.headers or {}), time.time() - t
    except Exception as e:
        return str(e)[:100], b"", {}, time.time() - t
B = "https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/"
for u in (B + "anual/Brasil_sat_ref/focos_br_ref_2025.zip", B + "mensal/Brasil/focos_mensal_br_202510.zip",
          B + "mensal/Brasil/focos_mensal_br_202610.csv"):
    st, c, h, dt = get(u, "HEAD")
    print("HEAD", u.rsplit("/", 1)[1], st, h.get("Content-Length"), h.get("Last-Modified"))
st, c, h, dt = get(B + "anual/Brasil_sat_ref/focos_br_ref_2025.zip")
print("anual 2025:", st, len(c), f"{dt:.1f}s")
z = zipfile.ZipFile(io.BytesIO(c))
print(" membros:", [(i.filename, i.file_size) for i in z.infolist()][:5])
txt = z.read(z.infolist()[0]).decode("utf-8", "replace")
rows = list(csv.DictReader(io.StringIO(txt)))
print(" colunas:", list(rows[0].keys()), "linhas", len(rows))
print(" 1ª:", rows[0])
print(" satélites:", collections.Counter(r.get("satelite") for r in rows).most_common(3))
print(" 15/10/2025:", sum(1 for r in rows if str(r.get("data_pas") or r.get("data_hora_gmt") or "").startswith("2025-10-15")))
A = "https://apimsbr.ana.gov.br/rpc/v1/"
for u in (A, A + "change_maps", "https://apimsbr.ana.gov.br/", "https://apimsbr.ana.gov.br/rpc/v1/openapi.json",
          "https://monitordesecas.ana.gov.br/robots.txt", "https://apimsbr.ana.gov.br/robots.txt"):
    st, c, h, dt = get(u, n=3000)
    print("\nANA", u, st, h.get("Content-Type"), c[:1500])
