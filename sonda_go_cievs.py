#!/usr/bin/env python3
"""Sonda temporária (válvula; não vai à main): boletins estaduais PR, SC, AM, PA."""
import re, urllib.parse
from coletores_base import buscar
ALVOS = {
 "PR": ["https://www.saude.pr.gov.br/Pagina/Dengue", "https://www.saude.pr.gov.br/Pagina/Informes-e-Boletins-Epidemiologicos"],
 "SC": ["https://www.dive.sc.gov.br/index.php/dengue", "https://www.dive.sc.gov.br/index.php/boletins"],
 "AM": ["https://www.fvs.am.gov.br/boletins", "https://www.fvs.am.gov.br/"],
 "PA": ["https://www.saude.pa.gov.br/boletins-epidemiologicos/", "https://www.saude.pa.gov.br/"],
}
for uf, urls in ALVOS.items():
    for URL in urls:
        try:
            h = buscar(URL).decode("utf-8", "replace")
        except Exception as e:
            print(uf, URL, "ERRO", repr(e)[:120]); continue
        print(uf, URL, "OK bytes", len(h))
        n = 0
        for href, t in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', h, re.S | re.I):
            t = re.sub(r"<[^>]+>|\s+", " ", t).strip()
            if re.search(r"dengue|arbov|chik|boletim|informe", t + href, re.I) and n < 12:
                n += 1; print("  LINK", urllib.parse.urljoin(URL, href), "|", t[:90])
