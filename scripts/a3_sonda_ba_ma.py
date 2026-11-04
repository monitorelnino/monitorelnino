#!/usr/bin/env python3
"""Sonda só de leitura (ramo de válvula, nunca mesclado): BA dool e MA, GET identificado, uma tentativa cada."""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import coletores_base as c  # noqa: E402

ALVOS = (
    ("BA", "https://dool.egba.ba.gov.br/robots.txt"),
    ("BA", "https://dool.egba.ba.gov.br/"),
    ("BA", "https://www.legislabahia.ba.gov.br/"),
    ("MA", "https://diariooficial.ma.gov.br/robots.txt"),
    ("MA", "https://diariooficial.ma.gov.br/"),
)


def texto(html):
    html = re.sub(r"(?is)<(script|style|head|noscript)\b.*?</\1>", " ", html)
    return " ".join(re.sub(r"(?s)<[^>]+>", " ", html).split())


for uf, url in ALVOS:
    try:
        html = c.buscar(url, timeout=45).decode("utf-8", "replace")
    except Exception as e:
        print("SONDA>", uf, "ERRO", url, type(e).__name__, str(e)[:200])
        continue
    print("SONDA>", uf, "OK", url, "bytes", len(html))
    if url.endswith("robots.txt"):
        print("SONDA>", uf, "robots", html[:600].replace("\n", " | "))
        continue
    print("SONDA>", uf, "forms", re.findall(r"(?is)<form[^>]*>", html)[:5])
    print("SONDA>", uf, "texto", texto(html)[:500])
    links = re.findall(r'href="([^"]+)"', html)
    print("SONDA>", uf, "links", [x for x in links if re.search(r"pdf|diario|edicao|download|busca|pesquisa|doe", x, re.I)][:20])
