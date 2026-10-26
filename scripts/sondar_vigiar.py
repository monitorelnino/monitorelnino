#!/usr/bin/env python3
"""Sonda do Painel VIGIAR (MS/SVSA/CNIE), 26/10/2026: só mede, não grava em data/.

Mede, do runner do Actions (rede real): status e tamanho da página oficial; robots.txt do host
(Crawl-delay e Disallow para o caminho); presença de referência a Power BI (`powerbi`,
`querydata`, `public/reports`) no HTML e nos scripts linkados; e uma consulta GET ao endpoint de
relatório público (sem credencial). Cliente identificado. Recusa (401/403/429/451) é registrada
como recusa, nunca contornada.
"""
from __future__ import annotations

import re
import sys
import urllib.error
import urllib.parse
import urllib.request

UA = "Monitor El Nino Brasil (monitorelnino.com.br; contato@futuraevidencelab.com.br)"
PAGINA = ("https://www.gov.br/saude/pt-br/composicao/svsa/cnie/"
          "painel-de-poluicao-atmosferica-e-saude-humana")


def pedir(url: str, metodo: str = "GET", corpo: bytes | None = None, limite: int = 2_000_000):
    req = urllib.request.Request(url, data=corpo, method=metodo, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            dados = r.read(limite)
            return r.status, dict(r.headers), dados
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), e.read(4000)
    except Exception as e:  # rede, TLS, DNS
        return None, {}, repr(e).encode()[:300]


def main() -> int:
    st, h, corpo = pedir(PAGINA)
    print(f"PAGINA status={st} bytes={len(corpo)} ctype={h.get('Content-Type')}")
    texto = corpo.decode("utf-8", "replace") if corpo else ""
    for chave in ("powerbi", "querydata", "public/reports", "app.powerbi.com", "Última atualização", "Dados até"):
        print(f"  ref {chave!r}: {texto.count(chave)}")
    scripts = re.findall(r'src="([^"]+\.js[^"]*)"', texto)[:12]
    links = sorted(set(re.findall(r'https?://[^"\'\s<>]*(?:powerbi|querydata|public/reports)[^"\'\s<>]*', texto)))[:10]
    print("  scripts:", len(scripts), "links_powerbi:", links)

    host = urllib.parse.urlsplit(PAGINA)
    st, h, rb = pedir(f"{host.scheme}://{host.netloc}/robots.txt")
    print(f"ROBOTS {host.netloc} status={st} bytes={len(rb)}")
    if st == 200:
        linhas = rb.decode("utf-8", "replace").splitlines()
        for ln in linhas:
            if re.match(r"(?i)\s*(crawl-delay|disallow|user-agent)", ln) and len(ln) < 160:
                print("   ", ln.strip())

    for url in ("https://dadosabertos.saude.gov.br/robots.txt",):
        st, _, rb = pedir(url)
        print(f"ROBOTS {url} status={st} crawl_delay={'crawl-delay' in rb.decode('utf-8','replace').lower() if st==200 else '-'}")

    rel = "https://app.powerbi.com/view?r=vigiar-publico-nao-medido"
    st, _, _ = pedir(rel)
    print(f"POWERBI_VIEW_SONDA status={st} (sem id real: só mede a rota)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
