"""Sonda temporária (ramo diag): CE e PI, edição por data."""
import sys, re, json
sys.path.insert(0, ".")
from coletores_base import buscar
URLS = ["http://imagens.seplag.ce.gov.br/PDF/20261013/do20261013.pdf",
        "http://imagens.seplag.ce.gov.br/PDF/20261013/",
        "http://imagens.seplag.ce.gov.br/PDF/20261013/do20261013p02.pdf",
        "http://imagens.seplag.ce.gov.br/PDF/20261013/do20261013p05.pdf",
        "http://imagens.seplag.ce.gov.br/PDF/20261013/do20261013p20.pdf",
        "http://imagens.seplag.ce.gov.br/PDF/20261010/do20261010p01.pdf",
        "http://www.diariooficial.pi.gov.br/diario.php?dia=20261013",
        "http://www.diariooficial.pi.gov.br/diarios.php?dia=20261013"]
for u in URLS:
    try:
        b = buscar(u, timeout=40, origem="sonda DOE")
        t = b[:60000].decode("latin-1", "replace")
        links = sorted(set(re.findall(r'(?:href|src)="([^"]*\.pdf[^"]*)"', t, re.I)))[:20]
        print(json.dumps({"url": u, "ok": True, "bytes": len(b), "inicio": t[:80], "pdfs": links,
                          "outros": sorted(set(re.findall(r'href="([^"]*(?:diario|arquivo|download)[^"]*)"', t, re.I)))[:15]}, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"url": u, "ok": False, "erro": f"{type(e).__name__}: {str(e)[:150]}"}, ensure_ascii=False))
