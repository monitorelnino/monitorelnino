#!/usr/bin/env python3
"""Sonda (só no ramo coleta-dia): que parâmetro do SIDRA recusa o pedido do PIB per capita 2023?
Imprime o status e o começo da resposta de variantes da consulta e a descrição da tabela."""
import sys, pathlib, urllib.request, urllib.error
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from coletores_base import ua_de
URLS = [
    "https://apisidra.ibge.gov.br/values/t/5938/n3/33/v/all/p/last?formato=json",
    "https://apisidra.ibge.gov.br/values/t/5938/n1/1/v/allxp/p/last?formato=json",
]
for u in URLS:
    try:
        req = urllib.request.Request(u, headers={"User-Agent": ua_de("sonda SIDRA PIB per capita")})
        with urllib.request.urlopen(req, timeout=60) as r:
            corpo = r.read(200000).decode("utf-8", "replace")
            print(f"\n== {u}\n   HTTP {r.status}\n   {corpo}")
    except urllib.error.HTTPError as e:
        print(f"\n== {u}\n   HTTP {e.code} {e.reason}\n   {e.read(800).decode('utf-8','replace')}")
    except Exception as e:
        print(f"\n== {u}\n   {type(e).__name__}: {e}")
