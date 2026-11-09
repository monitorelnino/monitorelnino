#!/usr/bin/env python3
"""Sonda (só no ramo coleta-dia): lê a Parte I do DOE-RJ de 03 a 10/07/2026 e imprime as páginas que citam El Niño."""
import json, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from coletores_base import buscar
from coletar_doe import edicoes_rj, paginas_com_termo
base = json.load(open("data/fontes_doe.json"))["ufs"]["RJ"]["url"]
fn = edicoes_rj(lambda u, **k: buscar(u, **k), base)
for dia in ["2026-07-03", "2026-07-06"]:
    try:
        eds = fn(dia)
    except Exception as e:
        print(f"== {dia}: {type(e).__name__}: {e}"); continue
    for ed in eds:
        try:
            pdf = buscar(ed["url"], timeout=180, origem="sonda")
            from preservar_evidencias import extrair_texto_por_pagina
            tx = extrair_texto_por_pagina(pdf) or []
            print(f"   {len(tx)} páginas extraídas, {sum(len(t or '') for t in tx)} caracteres; amostra: {(tx[0] if tx else '')[:300]!r}")
            pags = [(i, t) for i, t in enumerate(tx, 1) if any(k in (t or '').lower() for k in ("el niño", "el nino", "50.357", "niño"))]
            print(f"== {dia} {ed['edicao']}: {len(pdf)} bytes, {len(pags)} página(s) com o termo")
            for p, t in pags[:4]:
                i = max(0, t.lower().find("el ni") - 1500)
                print(f"--- p. {p}\n{t[i:i+3500]}\n")
        except Exception as e:
            print(f"== {dia} {ed.get('edicao')}: {type(e).__name__}: {e}")
