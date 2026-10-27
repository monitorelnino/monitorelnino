#!/usr/bin/env python3
"""Sonda CIEVS por estado (E1, 27/10/2026): só mede, nada em data/.

Para cada UF da lista, lê robots.txt e a página inicial da secretaria de saúde (cliente identificado,
Crawl-delay respeitado) e lista os links cujo texto cita boletim, informe, arbovirose, dengue,
chikungunya ou vigilância. 401/403/429/451 e muro de robô servido com 200 = recusa, registrada e
nunca contornada. Falha de rede (sem código HTTP) = não medido, nunca ausência.
Autoteste offline: python3 sondar_cievs.py --autoteste
"""
from __future__ import annotations

import re
import sys
import time
import urllib.error
import urllib.request
import urllib.robotparser
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

UA = "Monitor El Nino Brasil (monitorelnino.com.br; contato@futuraevidencelab.com.br)"
ALVOS = {
    "AC": ["https://saude.ac.gov.br/"],
    "AP": ["https://www.saude.ap.gov.br/"],
    "AM": ["https://www.saude.am.gov.br/", "https://www.fvs.am.gov.br/"],
    "PA": ["https://www.saude.pa.gov.br/"],
    "RO": ["https://rondonia.ro.gov.br/sesau/"],
    "RR": ["https://saude.rr.gov.br/", "https://vigilancia.saude.rr.gov.br/"],
    "TO": ["https://www.to.gov.br/saude"],
    "MA": ["https://www.saude.ma.gov.br/"],
    "PI": ["https://www.saude.pi.gov.br/"],
}
CASA = re.compile(r"boletim|informe|arbovir|dengue|chikungunya|zika|vigil[aâ]ncia epidemiol", re.I)
MURO = re.compile(r"captcha|cloudflare|attention required|access denied|verifying you are human", re.I)
RECUSA = {401, 403, 429, 451}


class Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.itens: list[tuple[str, str]] = []
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
            self.itens.append((" ".join("".join(self._txt).split()), self._href))
            self._href = None


def candidatos(html: str, base: str) -> list[tuple[str, str]]:
    p = Links()
    p.feed(html)
    vistos, saida = set(), []
    for txt, href in p.itens:
        if txt and CASA.search(txt):
            url = urljoin(base, href)
            if (txt, url) not in vistos:
                vistos.add((txt, url))
                saida.append((txt[:90], url))
    return saida[:12]


def classificar(status: int | None, corpo: str) -> str:
    if status is None:
        return "nao_medido"
    if status in RECUSA:
        return f"recusa_{status}"
    if status == 200 and MURO.search(corpo[:4000]):
        return "recusa_muro_200"
    return "ok" if status == 200 else f"http_{status}"


def get(url: str, timeout: int = 30) -> tuple[int | None, str, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(600_000).decode("utf-8", "replace"), ""
    except urllib.error.HTTPError as e:
        return e.code, "", ""
    except Exception as e:  # noqa: BLE001
        return None, "", f"{type(e).__name__}: {e}"[:120]


def sondar(uf: str, url: str) -> None:
    host = urlparse(url)
    rb = urllib.robotparser.RobotFileParser()
    st, txt, err = get(f"{host.scheme}://{host.netloc}/robots.txt")
    if st == 200:
        rb.parse(txt.splitlines())
        if not rb.can_fetch(UA, url):
            print(f"{uf} {url} -> robots.txt NÃO permite; não lido")
            return
        espera = rb.crawl_delay(UA) or 0
        time.sleep(min(espera, 30))
    st, corpo, err = get(url)
    cls = classificar(st, corpo)
    print(f"{uf} {url} -> {cls} (status={st}, {len(corpo)} bytes){' ' + err if err else ''}")
    if cls == "ok":
        for txt_, u in candidatos(corpo, url):
            print(f"    link: {txt_} | {u}")


def autoteste() -> int:
    html = '<a href="/b.pdf">Boletim de Dengue SE 40</a><a href="/x">Contato</a><a href="/i">Informe semanal</a>'
    c = candidatos(html, "https://exemplo.gov.br/")
    assert [t for t, _ in c] == ["Boletim de Dengue SE 40", "Informe semanal"], c
    assert c[0][1] == "https://exemplo.gov.br/b.pdf"
    assert classificar(None, "") == "nao_medido"
    assert classificar(403, "") == "recusa_403"
    assert classificar(200, "<title>Attention Required! | Cloudflare</title>") == "recusa_muro_200"
    assert classificar(200, "<html>ok</html>") == "ok"
    assert classificar(404, "") == "http_404"
    print("autoteste 5/5 ok")
    return 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    print("=== SONDA CIEVS lote 6 (E1, 27/10/2026): só mede, nada em data/ ===")
    for uf, urls in ALVOS.items():
        for u in urls:
            sondar(uf, u)
            time.sleep(2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
