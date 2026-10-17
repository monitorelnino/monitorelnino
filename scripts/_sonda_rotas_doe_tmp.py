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


if __name__ == "__main__":
    print("=== RO ===")
    for u in ("https://diof.ro.gov.br/data/uploads/2026/09/DOE-10-09-2026.pdf", "https://diof.ro.gov.br/data/uploads/2026/07/DOE-01-07-2026.pdf"):
        corpo(u)
    corpo("https://diof.ro.gov.br/busca", 600)
    print("=== RJ ===")
    corpo("https://www.ioerj.com.br/portal/modules/conteudoonline/mostra_edicao.php?session=VDBWR1JrNXFhM3BQUkZsMFQwUlNRazE1TURCTk1FMHpURlJzUlU5VlJYUk5ha0V6VFRCRk5VMXJXWGxSYTA1RVRWUmpOVTFxU1hwTlJFVjVUa0U5UFE9PQ==", 2500)
    print("=== RR ===")
    corpo("https://www.imprensaoficial.rr.gov.br/_inicial/", 1500)
    print("=== RN ===")
    corpo("https://www.diariooficial.rn.gov.br/dei/dorn3/", 1500)
    corpo("http://diariooficial.rn.gov.br/dei/dorn3/", 800)
    print("=== AL ===")
    corpo("https://diario.imprensaoficial.al.gov.br/apinova/api/editions/published?page=1", 1500)
    for s in scripts("https://diario.imprensaoficial.al.gov.br/"):
        ctx(s, r"searchES|formBusca:|formBusca=|populateSearch", 300, 12)
    print("=== RS ===")
    for s in scripts("https://www.diariooficial.rs.gov.br/"):
        if "main-" in s:
            ctx(s, r"API_URL\s*[=:]|apiUrl\s*[=:]|https://[a-z0-9.\-]*rs\.gov\.br/[a-z0-9_\-/]*api[^\"'`]*", 200, 15)
    print("=== MG ===")
    for s in scripts("https://www.jornalminasgerais.mg.gov.br/"):
        if "main-" in s:
            ctx(s, r"[\"'`][^\"'`\s]{0,80}(?:/api/|api\.|Api)[^\"'`\s]{0,80}[\"'`]", 120, 25)
    print("=== SC ===")
    for s in scripts("https://portal.doe.sea.sc.gov.br/v2.44.07/"):
        if "main." in s:
            ctx(s, r"restPrefix\+\"[^\"]*\"|restPrefix\}[^`]*`|cdJornal|/jornal[^\"'`]{0,60}", 160, 25)
    print("=== MA ===")
    corpo("https://www.diariooficial.ma.gov.br/public/index.xhtml", 400)
