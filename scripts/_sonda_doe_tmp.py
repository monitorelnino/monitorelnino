"""Sonda temporária (ramo diag, não vai à main): rotas de busca dos DOEs N/NE, do runner."""
import sys, re, json
sys.path.insert(0, ".")
from coletores_base import buscar
T = "plano+de+conting%C3%AAncia"
ROTAS = {
 "BA": [f"https://www.egba.ba.gov.br/egba/busca-solr-multisite?search_api_fulltext={T}"],
 "PB": [f"https://auniao.pb.gov.br/@@busca?SearchableText={T}", "https://auniao.pb.gov.br/servicos/doe"],
 "MA": ["https://diariooficial.ma.gov.br/busca/", f"https://diariooficial.ma.gov.br/busca/?q={T}"],
 "RO": [f"https://diof.ro.gov.br/busca?diarios={T}"],
 "AM": ["https://diario.imprensaoficial.am.gov.br/apifront/portal/edicoes/edicoes_from_data/2026-10-13.json",
        "https://diario.imprensaoficial.am.gov.br/busca"],
 "AC": ["https://diario.ac.gov.br", "https://diario.ac.gov.br/apifront/portal/edicoes/edicoes_from_data/2026-10-13.json"],
 "PA": ["https://www.ioepa.com.br", "https://www.ioepa.com.br/pages/2026/10/13/2026.10.13.DOE.pdf"],
 "RR": ["https://www.imprensaoficial.rr.gov.br", "https://www.imprensaoficial.rr.gov.br/apifront/portal/edicoes/edicoes_from_data/2026-10-13.json"],
 "AL": ["https://imprensaoficial.al.gov.br", "https://imprensaoficial.al.gov.br/apifront/portal/edicoes/edicoes_from_data/2026-10-13.json"],
 "CE": ["https://www.saude.ce.gov.br", "http://imagens.seplag.ce.gov.br/PDF/20261013/do20261013p01.pdf"],
 "PE": ["https://diariooficial.cepe.com.br", "https://diariooficial.cepe.com.br/diariooficialweb/"],
 "PI": ["https://www.diariooficial.pi.gov.br", "http://www.diariooficial.pi.gov.br/diarios.php"],
 "RN": ["https://www.diariooficial.rn.gov.br", "http://diariooficial.rn.gov.br/dei/dorn3/Search.aspx"],
 "SE": ["https://segrase.se.gov.br", "https://www.se.gov.br/diario-oficial"],
}
for uf, urls in ROTAS.items():
    for u in urls:
        try:
            b = buscar(u, timeout=40, origem="sonda DOE")
            t = b[:20000].decode("utf-8", "replace")
            tit = re.search(r"<title>(.*?)</title>", t, re.S | re.I)
            links = sorted(set(re.findall(r'href="([^"]*(?:busca|pesquis|edic|diario|pdf)[^"]*)"', t, re.I)))[:12]
            forms = re.findall(r"<form[^>]*>", t, re.I)[:4]
            print(json.dumps({"uf": uf, "url": u, "ok": True, "bytes": len(b), "inicio": t[:120],
                              "titulo": (tit.group(1).strip()[:100] if tit else None), "links": links,
                              "forms": forms, "conta_plano": t.lower().count("conting")}, ensure_ascii=False))
        except Exception as e:
            print(json.dumps({"uf": uf, "url": u, "ok": False, "erro": f"{type(e).__name__}: {str(e)[:200]}"}, ensure_ascii=False))
