#!/usr/bin/env python3
"""Sonda da válvula (D, 25/10/2026): páginas públicas de IEG-M (TCE-SP), ICM (MIDR) e TCE-RS.
Só lê (coletores_base.buscar: cliente identificado, robots, recusa respeitada) e imprime links
de arquivo/painel; não grava em data/."""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import coletores_base as cb

ALVOS = [
    "https://www.tce.sp.gov.br/transparencia-tcesp/resultados-iegm",
    "https://www.gov.br/mdr/pt-br/assuntos/protecao-e-defesa-civil/indice-de-capacidade-municipal",
    "https://portal.tce.rs.gov.br/",
    "https://www.tce.pe.gov.br/internet/index.php/icm-tcepe",
]
CHAVE = re.compile(r"iegm|ieg-m|i-cidade|icm|contingen|plancon|levantamento|\.xlsx|\.xls|\.csv|\.ods|\.pdf|looker|powerbi|datastudio|script\.google", re.I)

for url in ALVOS:
    print(f"== {url}")
    try:
        corpo = cb.buscar(url, timeout=60, origem="sondar_paineis_contas")
    except Exception as e:  # noqa: BLE001 — sonda
        print(f"  FALHA {type(e).__name__}: {str(e)[:200]}")
        continue
    muro = cb.detectar_muro_de_robo(corpo)
    html = corpo.decode("utf-8", "replace")
    t = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    print(f"  {len(corpo)} bytes · título: {(t.group(1).strip()[:120] if t else '-')} · muro: {muro}")
    vistos = set()
    for m in re.finditer(r'(?:href|src)=["\']([^"\']+)["\'][^>]*>([^<]{0,100})', html, re.I):
        h, rot = m.group(1), re.sub(r"\s+", " ", m.group(2)).strip()
        if CHAVE.search(h) or CHAVE.search(rot):
            if h not in vistos:
                vistos.add(h); print(f"  - {h[:200]} | {rot}")
        if len(vistos) >= 60: break
