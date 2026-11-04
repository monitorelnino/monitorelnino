#!/usr/bin/env python3
"""Sonda só de leitura (ramo de válvula, nunca mesclado): GET real do formulário de busca de BA e RO."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import coletores_base as c  # noqa: E402

ALVOS = (
    ("BA", "https://www.egba.ba.gov.br/egba/busca-solr-multisite?search_api_fulltext=emergencia%20em%20saude"),
    ("RO", "https://diof.ro.gov.br/busca?diarios=emergencia%20em%20saude"),
)
for uf, url in ALVOS:
    try:
        b = c.buscar(url, timeout=60)
        t = " ".join(b.decode("utf-8", "replace").split())
        print("SONDA>", uf, "bytes", len(b))
        print("SONDA>", uf, t[:2000])
    except Exception as e:
        print("SONDA>", uf, "ERRO", type(e).__name__, str(e)[:300])
