#!/usr/bin/env python3
"""Sonda pontual (08/11/2026), passo 2: a estrutura do Atom de notícias do MIDR. Só imprime."""
import sys, pathlib, urllib.request
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from coletores_base import ua_de
for u in ["https://www.gov.br/mdr/pt-br/noticias/RSS", "https://www.gov.br/mdr/pt-br/noticias/RSS?b_size=60"]:
    t = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": ua_de("sonda de comunicados da Defesa Civil Nacional")}), timeout=40).read().decode("utf-8", "replace")
    print("=====", u, len(t), "entries:", t.count("<entry"))
    i = t.find("<entry"); print(t[:min(len(t), 600)].replace("\n", " ")); print("-----"); print(t[i:i+2600].replace("\n", " "))
    import re; print("TITULOS:"); [print("  ", x) for x in re.findall(r"<entry>.*?<title[^>]*>([^<]*)</title>", t, re.S)]
