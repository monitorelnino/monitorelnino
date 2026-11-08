#!/usr/bin/env python3
"""Sonda pontual (08/11/2026): onde o gov.br/MIDR publica as notícias da Defesa Civil Nacional de forma
legível por máquina (RSS, listagem). Só mede e imprime; não grava nada em data/."""
import re, sys, time, urllib.request, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from coletores_base import ua_de
UA = ua_de("sonda de comunicados da Defesa Civil Nacional")
ALVOS = [
 "https://www.gov.br/mdr/pt-br/noticias",
 "https://www.gov.br/mdr/pt-br/noticias/RSS",
 "https://www.gov.br/mdr/pt-br/noticias/rss.xml",
 "https://www.gov.br/mdr/pt-br/noticias/protecao-e-defesa-civil",
 "https://www.gov.br/mdr/pt-br/noticias/protecao-e-defesa-civil/RSS",
 "https://www.gov.br/mdr/pt-br/assuntos/protecao-e-defesa-civil",
 "https://www.gov.br/mdr/pt-br/composicao/secretarias-nacionais/protecao-e-defesa-civil",
 "https://www.gov.br/mdr/pt-br/@@search?SearchableText=defesa+civil&sort_on=Date&portal_type=News+Item",
 "https://www.gov.br/mdr/pt-br/++api++/noticias?b_size=5",
 "https://agenciagov.ebc.com.br/noticias/defesa-civil",
 "https://agenciagov.ebc.com.br/rss",
 "https://www.gov.br/pt-br/noticias/RSS",
]
for u in ALVOS:
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA, "Accept": "text/html,application/xml,application/json"}), timeout=40)
        b = r.read(400000); t = b.decode("utf-8", "replace")
        itens = len(re.findall(r"<item[\s>]", t)); links = len(set(re.findall(r'href="(https://www\.gov\.br/mdr/pt-br/noticias/[^"#?]+)"', t)))
        tit = re.findall(r"<title>([^<]{0,90})", t)[:3]
        print(f"OK {r.status} {r.headers.get('Content-Type','')[:40]} {len(b)}B itens_rss={itens} links_noticia={links} {u}\n   titulos={tit}")
        if links:
            for l in sorted(set(re.findall(r'href="(https://www\.gov\.br/mdr/pt-br/noticias/[^"#?]+)"', t)))[:12]: print("   ", l)
    except Exception as e:
        print(f"ERRO {type(e).__name__} {getattr(e,'code','')} {str(e)[:80]} {u}")
    time.sleep(2)
