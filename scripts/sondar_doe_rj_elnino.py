#!/usr/bin/env python3
"""Sonda (só no ramo coleta-dia): texto da p. 3 do DOE-RJ de 03/07/2026 pelo extrator de produção, em volta do 50.357."""
import json, sys, pathlib, re
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from coletores_base import buscar
from coletar_doe import edicoes_rj
from preservar_evidencias import extrair_texto_por_pagina
base = json.load(open("data/fontes_doe.json"))["ufs"]["RJ"]["url"]
for ed in edicoes_rj(lambda u, **k: buscar(u, **k), base)("2026-07-03"):
    pags = extrair_texto_por_pagina(buscar(ed["url"], timeout=240, origem="sonda"))
    t = pags[2]
    for m in re.finditer(r"50\.357|El Ni|EL NI|40\.013", t):
        print(f"--- {m.group(0)} @ {m.start()}: {t[max(0,m.start()-300):m.start()+300]!r}")
    break
