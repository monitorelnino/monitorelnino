"""Sonda temporária (ramo diag): busca dos DOEs AL, PA, RR, RN, RO, MA."""
import sys, re, json, urllib.parse
sys.path.insert(0, ".")
from coletores_base import buscar_uma_vez as b1, enviar_uma_vez as e1
T = "situação de emergência"; q = urllib.parse.quote(T)
ROTAS = [
 ("AL", lambda: b1("http://diario.imprensaoficial.al.gov.br/", timeout=30)),
 ("AL busca", lambda: b1(f"https://diario.imprensaoficial.al.gov.br/apifront/portal/busca/busca/buscar/%22{q}%22?page=0&dataInicial=2026-09-01&dataFinal=2026-10-14", timeout=30)),
 ("PA", lambda: b1(f"https://www.ioepa.com.br/pesquisa/?termo={q}", timeout=30)),
 ("RR", lambda: b1("https://www.imprensaoficial.rr.gov.br/app/", timeout=30)),
 ("RN", lambda: b1("http://diariooficial.rn.gov.br/dei/dorn3/", timeout=30)),
 ("RO busca", lambda: b1(f"https://diof.ro.gov.br/?s={q}", timeout=30)),
 ("MA", lambda: b1("https://www.diariooficial.ma.gov.br/", timeout=30)),
]
for uf, f in ROTAS:
    try:
        t = f().decode("utf-8", "replace")
        print(json.dumps({"uf": uf, "ok": True, "bytes": len(t), "titulo": (re.search(r"<title>(.*?)</title>", t, re.S | re.I) or [None, None])[1],
                          "forms": re.findall(r"<form[^>]*>", t, re.I)[:3], "inputs": re.findall(r"<input[^>]*name=\"([^\"]+)\"", t, re.I)[:12],
                          "links": sorted(set(re.findall(r'href="([^"]*(?:busca|pesquis|edic|diario|\.pdf|download|materia)[^"]*)"', t, re.I)))[:10],
                          "conta": t.lower().count("emerg"), "datas2026": len(re.findall(r"\d{2}/\d{2}/2026", t))}, ensure_ascii=False)[:1500])
    except Exception as e:
        print(json.dumps({"uf": uf, "ok": False, "erro": f"{type(e).__name__}: {str(e)[:150]}"}, ensure_ascii=False))
