"""Sonda (não grava em data/): domínios das secretarias estaduais de saúde respondem à API do WordPress? Que PDFs de plano aparecem?"""
import json, socket, urllib.parse
import coletores_base as c
DOM = {"RR": ["vigilancia.saude.rr.gov.br", "saude.rr.gov.br"], "AP": ["saude.ap.gov.br", "svs.ap.gov.br", "portal.ap.gov.br"],
       "RN": ["saude.rn.gov.br", "portal.rn.gov.br", "www.saude.rn.gov.br"], "TO": ["saude.to.gov.br", "www.to.gov.br"],
       "AC": ["saude.ac.gov.br", "agencia.ac.gov.br"], "MA": ["www.saude.ma.gov.br", "saude.ma.gov.br"],
       "MT": ["www.saude.mt.gov.br"], "RJ": ["www.saude.rj.gov.br"], "RO": ["rondonia.ro.gov.br", "sesau.ro.gov.br"],
       "GO": ["goias.gov.br"], "SE": ["saude.se.gov.br"]}
TERMOS = ["contingência", "plano estadual", "arboviroses", "El Niño", "emergências em saúde"]
for uf, doms in DOM.items():
    for d in doms:
        try: socket.gethostbyname(d)
        except Exception as e: print("DNS", uf, d, "FALHA", flush=True); continue
        for t in TERMOS:
            u = f"https://{d}/wp-json/wp/v2/media?search={urllib.parse.quote(t)}&mime_type=application/pdf&per_page=20"
            try:
                j = json.loads(c.buscar(u, timeout=25, origem="sonda wp saude estadual"))
                for m in j if isinstance(j, list) else []:
                    print("PDF", uf, d, t, "|", m.get("date", "")[:10], "|", (m.get("title") or {}).get("rendered", "")[:110], "|", m.get("source_url"), flush=True)
                print("OK", uf, d, t, len(j) if isinstance(j, list) else type(j).__name__, flush=True)
            except Exception as e:
                print("ERRO", uf, d, t, type(e).__name__, str(e)[:100], flush=True); break
