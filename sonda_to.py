"""Sonda (não grava em data/): o diário do Tocantins responde? As páginas oficiais do estado linkam o plano de incêndios?"""
import re, socket
import coletores_base as c
for h in ("diariooficial.to.gov.br", "www.to.gov.br", "semarh.to.gov.br", "naturatins.to.gov.br", "cbm.to.gov.br", "defesacivil.to.gov.br"):
    try: print("DNS", h, socket.gethostbyname(h), flush=True)
    except Exception as e: print("DNS", h, "FALHA", e, flush=True)
URLS = ["https://diariooficial.to.gov.br", "https://diariooficial.to.gov.br/busca?por=texto&texto=7.140",
        "https://www.to.gov.br/semarh", "https://www.to.gov.br/naturatins", "https://www.to.gov.br/cbmto", "https://www.to.gov.br/defesacivil",
        "https://www.to.gov.br/semarh/plano-integrado-de-prevencao-e-combate-aos-incendios-florestais",
        "https://www.to.gov.br/cbmto/noticias"]
for u in URLS:
    try:
        b = c.buscar(u, timeout=40, origem="sonda do plano de incêndios do Tocantins"); t = b.decode("utf-8", "replace")
        links = sorted(set(re.findall(r'href="([^"]+)"', t)))
        alvo = [l for l in links if re.search(r"inc[eê]ndi|queimad|fogo|plano|\.pdf", l, re.I)]
        print("OK", u, len(b), "| links de interesse:", alvo[:40], flush=True)
        for m in re.finditer(r"Plano Integrado[^<]{0,160}|7\.140[^<]{0,120}", t): print("   TRECHO", m.group(0)[:200], flush=True)
    except Exception as e:
        print("ERRO", u, type(e).__name__, str(e)[:160], flush=True)
