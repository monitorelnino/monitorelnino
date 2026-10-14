"""Sonda temporária (ramo diag): estrutura do resultado AC/PI, busca WP RO."""
import sys, re, urllib.request, urllib.parse
sys.path.insert(0, ".")
from coletores_base import buscar
UA = {"User-Agent": "MonitorElNino/1.0 (+https://monitorelnino.com.br)"}
def post(url, campos):
    return urllib.request.urlopen(urllib.request.Request(url, data=urllib.parse.urlencode(campos).encode(), headers=UA), timeout=40).read()
def trecho(rot, b, ancora):
    t = b.decode("latin-1", "replace"); i = t.find(ancora)
    print(f"=== {rot} bytes={len(b)} idx={i}")
    print(re.sub(r"\s+", " ", t[max(0, i - 1500): i + 2500]))
for rot, f, a in [
    ("AC", lambda: post("https://diario.ac.gov.br/", {"palavra": "situação de emergência".encode("latin-1"), "ano_palavra": "2026", "tipoBusca": "0", "paginaIni": "0"}), "download.php"),
    ("PI", lambda: post("http://www.diariooficial.pi.gov.br/busca_diario.php", {"ocorrencia": "situação de emergência".encode("latin-1")}), "diario/20"),
    ("RO", lambda: buscar("https://diof.ro.gov.br/?s=homologa", timeout=40), "homolog"),
]:
    try:
        trecho(rot, f(), a)
    except Exception as e:
        print(rot, "ERRO", type(e).__name__, e)
