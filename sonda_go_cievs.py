#!/usr/bin/env python3
"""Sonda temporária (válvula; não vai à main): boletins da SES-GO."""
import re, sys, urllib.parse
from coletores_base import buscar
from preservar_evidencias import extrair_texto_por_pagina

URL = "https://goias.gov.br/saude/boletins-epidemiologicos/"
html = buscar(URL).decode("utf-8", "replace")
print("pagina bytes", len(html))
links = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, re.S | re.I)
ach = [(h, re.sub(r"<[^>]+>|\s+", " ", t).strip()) for h, t in links
       if re.search(r"dengue|arbov|lepto|chik|informe|boletim", t + h, re.I)]
for h, t in ach[:40]:
    print("LINK", urllib.parse.urljoin(URL, h), "|", t[:110])
alvo = next((urllib.parse.urljoin(URL, h) for h, t in ach if re.search(r"2026", t + h) and re.search(r"dengue|arbov", t + h, re.I)), None)
print("ALVO", alvo)
if alvo:
    corpo = buscar(alvo)
    print("alvo bytes", len(corpo), corpo[:8])
    if corpo[:4] == b"%PDF":
        pgs = extrair_texto_por_pagina(corpo)
        print("paginas", len(pgs))
        for i, p in enumerate(pgs[:3]):
            print("--- pag", i + 1, len(p)); print(p[:1400])
    else:
        print(corpo[:1500].decode("utf-8", "replace"))
