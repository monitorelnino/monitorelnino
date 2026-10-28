#!/usr/bin/env python3
"""Sonda temporária E1 (válvula; não vai à main): só mede a alcançabilidade do OpenDataSUS para o SRAG."""
import re, time, urllib.request, urllib.error
from coletores_base import ua_de, contexto_tls
UA = ua_de("sonda E1 srag")
def get(url, n=600):
    t = time.time()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=40, context=contexto_tls()) as r:
            c = r.read(200000)
            return f"HTTP {r.status} {len(c)}B {time.time()-t:.1f}s", c
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code} {time.time()-t:.1f}s", b""
    except Exception as e:
        return f"{type(e).__name__}: {str(e)[:90]} {time.time()-t:.1f}s", b""
for i in range(3):
    print("portal", i, get("https://dadosabertos.saude.gov.br/dataset/srag-2019-a-2026")[0])
    time.sleep(20)
print("portal robots", get("https://dadosabertos.saude.gov.br/robots.txt")[0])
for u in ["https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/?prefix=SRAG/2026/&max-keys=50",
          "https://ckan.saude.gov.br.s3.sa-east-1.amazonaws.com/?prefix=SRAG/2026/&max-keys=50"]:
    st, c = get(u)
    print("s3", u[:70], st)
    for k in re.findall(rb"<Key>([^<]+)</Key>", c)[:20]:
        print("  ", k.decode())
