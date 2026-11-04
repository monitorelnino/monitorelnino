#!/usr/bin/env python3
"""Sonda só de leitura (ramo de válvula, nunca mesclado): resultado real da busca de RO e formulário de BA."""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import coletores_base as c  # noqa: E402


def texto(html):
    html = re.sub(r"(?is)<(script|style|head|noscript)\b.*?</\1>", " ", html)
    return " ".join(re.sub(r"(?s)<[^>]+>", " ", html).split())


def ler(uf, url):
    try:
        html = c.buscar(url, timeout=60).decode("utf-8", "replace")
    except Exception as e:
        print("SONDA>", uf, "ERRO", url, type(e).__name__, str(e)[:200])
        return None
    print("SONDA>", uf, "OK", url, "bytes", len(html))
    return html


h = ler("RO", "https://diof.ro.gov.br/busca?diarios=emergencia%20em%20saude")
if h:
    print("SONDA> RO texto", texto(h)[:2500])
    links = re.findall(r'href="([^"]+)"', h)
    uteis = [x for x in links if re.search(r"pdf|diario|edicao|download|doe", x, re.I)]
    print("SONDA> RO links", uteis[:25])
for url in ("https://www.egba.ba.gov.br/", "https://dool.egba.ba.gov.br/"):
    h = ler("BA", url)
    if h:
        print("SONDA> BA formularios", re.findall(r'(?is)<form[^>]*>', h)[:6])
        print("SONDA> BA texto", texto(h)[:800])
        links = re.findall(r'href="([^"]+)"', h)
        print("SONDA> BA links", [x for x in links if re.search(r"dool|diario|busca|pesquisa|doe", x, re.I)][:20])
