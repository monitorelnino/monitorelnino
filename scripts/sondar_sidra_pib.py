#!/usr/bin/env python3
"""Sonda (só no ramo coleta-dia): que parâmetro do SIDRA recusa o pedido do PIB per capita 2023?
Imprime o status e o começo da resposta de variantes da consulta e a descrição da tabela."""
import urllib.request, urllib.error
from coletores_base import ua_de
URLS = [
    "https://apisidra.ibge.gov.br/values/t/5938/n3/all/v/6323/p/2023?formato=json",
    "https://apisidra.ibge.gov.br/values/t/5938/n3/all/v/6323/p/last?formato=json",
    "https://apisidra.ibge.gov.br/values/t/5938/n3/all/v/37/p/last?formato=json",
    "https://apisidra.ibge.gov.br/values/t/5938/n3/all/v/all/p/last/d/v6323%202?formato=json",
    "https://apisidra.ibge.gov.br/desctabapi.aspx?c=5938",
]
for u in URLS:
    try:
        req = urllib.request.Request(u, headers={"User-Agent": ua_de("sonda SIDRA PIB per capita")})
        with urllib.request.urlopen(req, timeout=60) as r:
            corpo = r.read(3000).decode("utf-8", "replace")
            print(f"\n== {u}\n   HTTP {r.status}\n   {corpo[:1500]}")
    except urllib.error.HTTPError as e:
        print(f"\n== {u}\n   HTTP {e.code} {e.reason}\n   {e.read(800).decode('utf-8','replace')}")
    except Exception as e:
        print(f"\n== {u}\n   {type(e).__name__}: {e}")
