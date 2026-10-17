#!/usr/bin/env python3
"""Sonda A3, rodada 2 (ramo diag, nunca mesclado): corpo, links e contexto de chamadas de API."""
import base64, io, re, sys, urllib.parse
sys.path.insert(0, ".")
from coletores_base import buscar  # noqa: E402

RE_HREF = re.compile(r'(?:href|src|action|content)="([^"]+)"', re.I)
FILTRO = re.compile(r"pdf|edic|diar|caderno|busca|pesquis|api|consulta|download|visualiz|jornal|URL=", re.I)


def pega(url):
    try:
        return buscar(url, timeout=60, origem="sonda_a3")
    except Exception as e:  # noqa: BLE001
        print(f"  {url} -> ERRO {type(e).__name__} {getattr(e, 'code', '') or ''} {str(e)[:100]}")
        return None


def corpo(url, n=1500):
    b = pega(url)
    if b is None:
        return None
    if b[:5] == b"%PDF-":
        import pdfplumber
        with pdfplumber.open(io.BytesIO(b)) as pdf:
            t = (pdf.pages[0].extract_text() or "")
            print(f"  {url} -> PDF {len(b)} B, {len(pdf.pages)} p., texto p1 {len(t)}: {re.sub(r'\s+', ' ', t)[:160]}")
        return b
    t = b.decode("utf-8", "replace")
    print(f"  {url} -> 200 {len(b)} B")
    print("    corpo:", re.sub(r"\s+", " ", re.sub(r"<style.*?</style>|<script.*?</script>", " ", t, flags=re.S))[:n])
    links = [h for h in dict.fromkeys(RE_HREF.findall(t)) if FILTRO.search(h)]
    print(f"    links({len(links)}):", links[:60])
    return b


def ctx(url, regex, largura=160, maximo=30):
    b = pega(url)
    if b is None:
        return
    t = b.decode("utf-8", "replace")
    print(f"  {url} -> {len(b)} B; contexto de /{regex}/:")
    vistos = set()
    for m in re.finditer(regex, t):
        trecho = t[max(0, m.start() - largura):m.end() + largura].replace("\n", " ")
        chave = trecho[largura - 20:largura + 60]
        if chave in vistos:
            continue
        vistos.add(chave)
        print("    …", trecho)
        if len(vistos) >= maximo:
            break


def scripts(url):
    b = pega(url)
    if b is None:
        return []
    return [urllib.parse.urljoin(url, s) for s in re.findall(r'<script[^>]+src="([^"]+\.js[^"]*)"', b.decode("utf-8", "replace"))]


def b64(d):
    return base64.b64encode(d.encode()).decode()


def posta_json(url, corpo_json):
    import json as _j, urllib.request
    from coletores_base import UA
    req = urllib.request.Request(url, data=_j.dumps(corpo_json).encode(), method="POST",
                                 headers={"User-Agent": UA, "Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            b = r.read()
        print(f"  POST {url} -> 200 {len(b)} B: {b[:1500].decode('utf-8','replace')}")
    except Exception as e:  # noqa: BLE001
        print(f"  POST {url} -> ERRO {type(e).__name__} {getattr(e,'code','')} {str(e)[:100]}")


if __name__ == "__main__":
    RJ = "https://www.ioerj.com.br/portal/modules/conteudoonline/mostra_edicao.php?session=VDBWR1JrNXFhM3BQUkZsMFQwUlNRazE1TURCTk1FMHpURlJzUlU5VlJYUk5ha0V6VFRCRk5VMXJXWGxSYTA1RVRWUmpOVTFxU1hwTlJFVjVUa0U5UFE9PQ=="
    print("=== RJ ===")
    ctx(RJ, r"PDFView\.open|PDFJS\.|\.open\(|DEFAULT_URL|file\s*=|url\s*=|\.pdf", 250, 12)
    ctx("https://www.ioerj.com.br/portal/modules/conteudoonline/include/pdfjs/web/viewer-min.js", r"DEFAULT_URL|session|mostra_edicao|\.php", 200, 10)
    print("=== RS ===")
    for s in scripts("https://www.diariooficial.rs.gov.br/"):
        if "main-" in s:
            ctx(s, r"getDoeEndpoint\(\)[^;]{0,200}", 200, 6)
    print("=== BA ===")
    for u in ("https://dool.egba.ba.gov.br/dool/", "http://www.egba.ba.gov.br/diario/", "https://www.ba.gov.br/egba/diario-oficial"):
        corpo(u, 400)
    print("=== LEGISLACAO ===")
    for u in ("https://legis.alepe.pe.gov.br/", "https://dadosabertos.almg.gov.br/ws/legislacao/pesquisa/avancada?tipo=DEC&ano=2026&expressao=emerg%C3%AAncia&formato=json",
              "https://www.almg.gov.br/legislacao-mineira/", "http://alerjln1.alerj.rj.gov.br/decest.nsf", "https://www.al.rs.gov.br/legis/",
              "https://al.se.leg.br/", "https://www.al.ma.leg.br/", "https://legislacao.pe.gov.br/"):
        corpo(u, 500)
    print("=== MA ===")
    corpo("https://www.diariooficial.ma.gov.br/", 300)
