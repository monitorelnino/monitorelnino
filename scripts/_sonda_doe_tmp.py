"""Sonda pontual (diag 16/10): MonitorAr/MMA e RedeAr/IPAM do runner — robots, código, tamanho, tempo, cabeçalhos."""
import json, sys, time, urllib.request, urllib.error
sys.path.insert(0, ".")
from coletores_base import UA
def get(u, t=60):
    t0 = time.time()
    req = urllib.request.Request(u, headers={"User-Agent": UA, "Accept": "application/json, text/plain, */*"})
    try:
        with urllib.request.urlopen(req, timeout=t) as r:
            b = r.read(); h = dict(r.headers)
            return r.status, b, h, time.time() - t0
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:300], dict(e.headers or {}), time.time() - t0
    except Exception as e:
        return f"ERRO {type(e).__name__}: {e}", b"", {}, time.time() - t0
for u in ["https://monitorar-backend.mma.gov.br/robots.txt", "https://monitorar.mma.gov.br/robots.txt",
          "https://monitorar-backend.mma.gov.br/v1/estacao/todas",
          "https://redear.org.br/robots.txt", "https://hmg.api.redear.org.br/robots.txt",
          "https://api.redear.org.br/v1/sensors", "https://hmg.api.redear.org.br/v1/sensors"]:
    st, b, h, dt = get(u)
    hh = {k: v for k, v in h.items() if k.lower() in ("content-type", "cache-control", "access-control-allow-origin", "server", "content-length", "date")}
    print(f"\n== {u}\n   status={st} bytes={len(b)} tempo={dt:.1f}s cabeçalhos={hh}")
    if u.endswith("robots.txt") and isinstance(st, int) and st == 200:
        print("   robots:", b[:400].decode("utf-8", "replace").replace("\n", " | "))
    elif isinstance(st, int) and st == 200:
        try:
            o = json.loads(b)
            if isinstance(o, list):
                print("   lista com", len(o), "itens; chaves do 1º:", list(o[0])[:25] if o else None)
                if "estacao" in u:
                    rec = [x for x in o if str((x.get("indiceQualidadeArAtual") or {}).get("dtMedicao") or x.get("dtUltimaAtualizacao") or "")[:7] == "2026-10"]
                    print("   com dado em 2026-10:", len(rec))
            elif isinstance(o, dict):
                print("   dict, chaves:", list(o)[:15])
                for k in ("data", "sensors", "items", "results"):
                    if isinstance(o.get(k), list): print("   ", k, len(o[k]), list(o[k][0])[:20] if o[k] else None)
        except Exception as e:
            print("   não é JSON:", e, b[:200])
    time.sleep(2)
