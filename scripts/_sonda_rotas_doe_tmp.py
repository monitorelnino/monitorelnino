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
    print("=== PA ===")
    for d in ("2026/2026.07.01", "2026/2026.10.15", "2026/2026.10.16"):
        corpo(f"https://www.ioepa.com.br/pages/{d}.DOE.pdf")
    print("=== SE ===")
    corpo("https://iose.se.gov.br/apifront/portal/edicoes/edicoes_from_data/2026-09-10.json", 800)
    corpo("https://iose.se.gov.br/busca/busca/buscar/query/0/di:2026-09-01/df:2026-09-30/?1=1&q=%22situa%C3%A7%C3%A3o%20de%20emerg%C3%AAncia%22", 800)
    corpo("https://iose.se.gov.br/diario-oficial", 800)
    print("=== RJ ===")
    corpo(f"https://www.ioerj.com.br/portal/modules/conteudoonline/do_seleciona_edicao.php?data={b64('20260910')}", 2500)
    print("=== AL ===")
    for s in scripts("https://diario.imprensaoficial.al.gov.br/"):
        ctx(s, r"apinova|editions/|ver-edicao|/edicoes")
    print("=== RS ===")
    for s in scripts("https://www.diariooficial.rs.gov.br/"):
        if "main-" in s:
            ctx(s, r"https?://[a-z0-9.\-]*procergs[^\"'`]*|apiUrl|baseUrl|/diario[\"'`/?]|/pdf[\"'`/?]|\.get\(`", maximo=40)
    print("=== MG ===")
    for s in scripts("https://www.jornalminasgerais.mg.gov.br/"):
        if "main-" in s:
            ctx(s, r"api/v1[^\"'`]*|apiUrl|baseUrl|environment", maximo=40)
    print("=== SC ===")
    corpo("https://portal.doe.sea.sc.gov.br/", 1200)
    for s in scripts("https://portal.doe.sea.sc.gov.br/v2.44.07/"):
        ctx(s, r"https?://[a-z0-9.\-]*sc\.gov\.br[^\"'`]*|apiUrl|baseUrl|/api/", maximo=30)
    print("=== RR ===")
    corpo("https://www.imprensaoficial.rr.gov.br/", 600)
    print("=== RN ===")
    corpo("http://www.diariooficial.rn.gov.br/dei/dorn3/", 2000)
    print("=== RO ===")
    corpo("https://diof.ro.gov.br/", 300)
    print("=== MA ===")
    corpo("https://diariooficial.ma.gov.br/", 600)
    corpo("http://www.diariooficial.ma.gov.br/", 600)
    print("=== BA ===")
    corpo("http://dool.egba.ba.gov.br/", 600)
    corpo("https://www.egba.ba.gov.br/egba/noticias/2025-01/331/diario-oficial-online", 1500)
