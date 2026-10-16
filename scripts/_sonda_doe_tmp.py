"""Sonda pontual (diag 16/10): BDQueimadas — colunas do CSV diário, diretórios mensal/anual, robots."""
import csv, io, re, sys, time, collections, urllib.request
sys.path.insert(0, ".")
from coletores_base import UA
B = "https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/"
def get(u, n=None):
    t = time.time()
    r = urllib.request.Request(u, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(r, timeout=90) as f:
            corpo = f.read() if n is None else f.read(n)
            return f.status, corpo, dict(f.headers), time.time() - t
    except urllib.error.HTTPError as e:
        return e.code, b"", dict(e.headers or {}), time.time() - t
    except Exception as e:
        return str(e)[:80], b"", {}, time.time() - t
st, c, h, dt = get("https://dataserver-coids.inpe.br/robots.txt")
print("robots", st, c[:300])
for sub in ("", "diario/Brasil/", "mensal/Brasil/", "anual/", "anual/Brasil_sat_ref/", "10min/", "diario/"):
    st, c, h, dt = get(B + sub)
    nomes = re.findall(r'href="([^"?/][^"]*)"', c.decode("utf-8", "replace"))
    print("\nDIR", sub, st, f"{dt:.1f}s", len(nomes), nomes[:6], "...", nomes[-6:])
st, c, h, dt = get(B + "diario/Brasil/")
dias = sorted(set(re.findall(r"focos_diario_br_(\d{8})\.csv", c.decode())))
print("\ndias disponíveis:", len(dias), dias[:2], dias[-3:])
st, c, h, dt = get(B + f"diario/Brasil/focos_diario_br_{dias[-2]}.csv")
txt = c.decode("utf-8", "replace")
rows = list(csv.DictReader(io.StringIO(txt)))
print("CSV", dias[-2], st, len(c), "bytes", f"{dt:.1f}s", "linhas", len(rows), "Cache-Control", h.get("Cache-Control"))
print("colunas:", list(rows[0].keys()) if rows else None)
print("1ª:", rows[0] if rows else None)
print("satélites:", collections.Counter(r.get("satelite") for r in rows).most_common(12))
print("biomas:", collections.Counter(r.get("bioma") for r in rows).most_common(8))
