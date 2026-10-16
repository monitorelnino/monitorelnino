"""Sonda pontual (diag 16/10): documentos federais de saúde (lote 6, 1.2) — título, data, hash."""
import hashlib, re, sys, time, urllib.parse
sys.path.insert(0, ".")
from coletores_base import buscar
URLS = [
 "https://www.gov.br/saude/pt-br/assuntos/noticias-ms/2026/junho/ministerio-da-saude-lanca-plano-para-preparar-sus-para-o-el-nino",
 "https://www.gov.br/saude/pt-br/assuntos/noticias-ms/2026/agosto/ministerio-da-saude-apresenta-a-secretarios-estaduais-plano-de-preparacao-para-o-el-nino-2026-2027",
 "https://www.gov.br/saude/pt-br/assuntos/noticias-ms/2026/setembro/ministerio-da-saude-detalha-acoes-do-adaptasus-para-enfrentar-impactos-do-fenomeno-el-nino",
]
def info(u):
    try:
        b = buscar(u, timeout=60)
    except Exception as e:
        print("ERRO", u, type(e).__name__, e); return None
    t = b.decode("utf-8", "replace")
    tit = re.search(r"<title>(.*?)</title>", t, re.S)
    pub = re.search(r'(Publicado em[^<]{0,60})', t)
    print("OK", u, "|", len(b), "|", hashlib.sha256(b).hexdigest()[:16], "|", (tit.group(1).strip() if tit else "")[:150], "|", pub.group(1) if pub else "")
    return t
for u in URLS:
    info(u); time.sleep(3)
for q in ("nota técnica conjunta 308/2026", "308/2026 El Niño"):
    u = "https://www.gov.br/saude/pt-br/search?SearchableText=" + urllib.parse.quote(q)
    t = info(u)
    if t:
        for m in re.finditer(r'href="(https://www\.gov\.br/saude[^"]+)"[^>]*>([^<]{5,200})<', t):
            if re.search(r"308|nota", m.group(1) + m.group(2), re.I):
                print("  ->", m.group(1), "|", m.group(2).strip()[:150])
    time.sleep(3)
