"""Sonda temporária (ramo diag): formulários de busca AC/PI e WordPress RO."""
import sys, re, json, urllib.request, urllib.parse
sys.path.insert(0, ".")
from coletores_base import buscar
def mostra(rot, f):
    try:
        b = f(); t = b.decode("latin-1", "replace")
        print(json.dumps({"rot": rot, "ok": True, "bytes": len(b), "inicio": t[:300],
                          "inputs": re.findall(r"<(?:input|select)[^>]*>", t, re.I)[:20],
                          "pdfs": sorted(set(re.findall(r'href="([^"]*(?:download|\.pdf)[^"]*)"', t, re.I)))[:8],
                          "conta": t.lower().count("homolog")}, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"rot": rot, "ok": False, "erro": f"{type(e).__name__}: {str(e)[:200]}"}, ensure_ascii=False))
def post(url, campos):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(campos).encode(), headers={"User-Agent": "MonitorElNino/1.0 (+https://monitorelnino.com.br)"})
    return urllib.request.urlopen(req, timeout=40).read()
mostra("AC home", lambda: buscar("https://diario.ac.gov.br/", timeout=40))
mostra("AC post palavra", lambda: post("https://diario.ac.gov.br/", {"palavra": "homologa", "ano_palavra": "2026"}))
mostra("RO wp search", lambda: buscar("https://diof.ro.gov.br/wp-json/wp/v2/search?search=homologa&per_page=10", timeout=40))
mostra("RO wp types", lambda: buscar("https://diof.ro.gov.br/wp-json/wp/v2/types", timeout=40))
mostra("RO busca form", lambda: buscar("https://diof.ro.gov.br/busca/", timeout=40))
mostra("PI post", lambda: post("http://www.diariooficial.pi.gov.br/busca_diario.php", {"ocorrencia": "homologa"}))
