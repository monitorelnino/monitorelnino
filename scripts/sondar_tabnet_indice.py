#!/usr/bin/env python3
"""Sonda do índice do TabNet (DATASUS), 27/10/2026: só mede, não grava em data/.

Lê a página pública que lista os tabuladores e imprime os links de DEF do SINAN (nomes reais dos
arquivos), para a sonda seguinte pedir uma célula (DDA, uma UF, um mês). Cliente identificado;
robots lido antes; 401/403/429/451 são recusa e encerram a rota.
"""
from __future__ import annotations

import re
import sys
import urllib.error
import urllib.request

UA = "Monitor El Nino Brasil (monitorelnino.com.br; contato@futuraevidencelab.com.br)"
INDICE = "https://datasus.saude.gov.br/informacoes-de-saude-tabnet/"


def pedir(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.status, r.read(3_000_000)
    except urllib.error.HTTPError as e:
        return e.code, e.read(300)
    except Exception as e:
        return None, repr(e).encode()[:200]


def main() -> int:
    st, rb = pedir("https://datasus.saude.gov.br/robots.txt")
    print(f"ROBOTS datasus.saude.gov.br status={st} bytes={len(rb)}")
    if st == 200:
        for ln in rb.decode("utf-8", "replace").splitlines():
            if re.match(r"(?i)\s*(crawl-delay|disallow|user-agent)", ln) and len(ln) < 140:
                print("   ", ln.strip())
    st, corpo = pedir(INDICE)
    print(f"INDICE status={st} bytes={len(corpo)}")
    if st != 200:
        print("  recusa/erro:", corpo[:200])
        return 0
    t = corpo.decode("utf-8", "replace")
    links = sorted(set(re.findall(r'href="([^"]+)"', t)))
    print("  links:", len(links))
    for h in links:
        if re.search(r"tabnet|sinan|\.def|deftohtm|tabcgi", h, re.I):
            print("  ", h[:200])
    return 0


if __name__ == "__main__":
    sys.exit(main())
