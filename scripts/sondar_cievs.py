#!/usr/bin/env python3
"""Sonda, só para medir, as páginas oficiais de saúde de UFs sem boletim de arboviroses lido.

Mede por UF: se o robots.txt permite a página, se a página responde (código e tipo), e quais
links apontam para boletim, informe, arbovirose, dengue ou chikungunya (texto e URL, sem seguir).
Não baixa PDF, não grava em `data/`, não promove nada: imprime um JSON no log. Recusa real
(401, 403, 429, 451) é registrada e não é repetida. Cliente identificado; Crawl-delay respeitado.

Uso:  python3 scripts/sondar_cievs.py --ufs PR,SC,MT,ES,GO,MS
      python3 scripts/sondar_cievs.py --autoteste
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from html.parser import HTMLParser

CLIENTE = "MARE-monitor-sondagem/1.0 (+https://monitorelnino.com.br)"
PAGINAS = {
    "PR": "https://www.saude.pr.gov.br/",
    "SC": "https://www.saude.sc.gov.br/",
    "MT": "https://www.saude.mt.gov.br/",
    "ES": "https://saude.es.gov.br/",
    "GO": "https://www.saude.go.gov.br/",
    "MS": "https://www.saude.ms.gov.br/",
}
PALAVRAS = re.compile(r"boletim|informe|arbovirose|dengue|chikungunya|sala de situa", re.I)
RECUSA = {401, 403, 429, 451}


class Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._txt: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._txt = []

    def handle_data(self, data):
        if self._href is not None:
            self._txt.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            self.links.append((" ".join("".join(self._txt).split()), self._href))
            self._href = None


def robots_permite(url: str) -> tuple[bool, float]:
    base = urllib.parse.urljoin(url, "/robots.txt")
    rp = urllib.robotparser.RobotFileParser()
    try:
        req = urllib.request.Request(base, headers={"User-Agent": CLIENTE})
        with urllib.request.urlopen(req, timeout=20) as r:
            rp.parse(r.read().decode("utf-8", "replace").splitlines())
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            return False, 0.0
        return True, 0.0
    except Exception:
        return True, 0.0
    atraso = rp.crawl_delay(CLIENTE) or 2
    return rp.can_fetch(CLIENTE, url), float(atraso)


def sondar(uf: str, url: str) -> dict:
    ok, atraso = robots_permite(url)
    if not ok:
        return {"uf": uf, "url": url, "resultado": "robots_proibe"}
    req = urllib.request.Request(url, headers={"User-Agent": CLIENTE, "Accept": "text/html"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            codigo, tipo = r.status, r.headers.get("Content-Type", "")
            corpo = r.read(2_000_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        resultado = "recusa_real" if e.code in RECUSA else "erro_http"
        return {"uf": uf, "url": url, "resultado": resultado, "codigo": e.code}
    except Exception as e:  # rede, TLS, timeout: registra, não insiste
        return {"uf": uf, "url": url, "resultado": "sem_resposta", "motivo": type(e).__name__}
    time.sleep(max(atraso, 2))
    p = Links()
    p.feed(corpo)
    alvos = [{"texto": t[:120], "url": urllib.parse.urljoin(url, h)}
             for t, h in p.links if PALAVRAS.search(t + " " + h)]
    return {"uf": uf, "url": url, "resultado": "respondeu", "codigo": codigo,
            "tipo": tipo.split(";")[0], "links_candidatos": alvos[:40],
            "n_links_candidatos": len(alvos)}


def autoteste() -> None:
    p = Links()
    p.feed('<a href="/b/x.pdf">Boletim de Arboviroses SE 40</a><a href="/y">Início</a>')
    assert p.links == [("Boletim de Arboviroses SE 40", "/b/x.pdf"), ("Início", "/y")], p.links
    assert PALAVRAS.search("Informe semanal de dengue") and not PALAVRAS.search("Contato")
    assert RECUSA == {401, 403, 429, 451}
    print("autoteste ok")


def main() -> None:
    if "--autoteste" in sys.argv:
        autoteste()
        return
    ap = argparse.ArgumentParser()
    ap.add_argument("--ufs", required=True)
    ufs = [u.strip().upper() for u in ap.parse_args().ufs.split(",") if u.strip()]
    saida = [sondar(u, PAGINAS[u]) for u in ufs if u in PAGINAS]
    print(json.dumps({"sondagem": "cievs_lote4", "resultados": saida}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
