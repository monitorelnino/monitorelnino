#!/usr/bin/env python3
"""Sonda de uma vez (ramo diag, nunca mesclado) — janela A3, 17/10/2026.

Mede, do runner, com o cliente do projeto (coletores_base.buscar: UA identificado, robots e
Crawl-delay respeitados), a página de edições das 13 UFs sem rota e a rede LexML. Não grava nada
em data/ (o rastro de robots vai junto só no runner). Imprime status, tamanho, tipo, links de PDF
e endereços de API achados no HTML e nos pacotes JS.
"""
import io
import json
import re
import sys
import urllib.parse

sys.path.insert(0, ".")
from coletores_base import buscar  # noqa: E402

RE_SRC = re.compile(r'<script[^>]+src="([^"]+\.js[^"]*)"', re.I)
RE_HREF = re.compile(r'(?:href|src|action)="([^"]+)"', re.I)
RE_API = re.compile(r'["\'`](https?://[^"\'`\s]{6,160}|/[A-Za-z0-9_\-./]*(?:api|apifront|rest|ws|json|pdf|edic|diari|caderno|publica)[A-Za-z0-9_\-./{}?=&]*)["\'`]', re.I)


def mostra(rotulo, url, html=True, js=False, maxbytes=12_000_000):
    try:
        b = buscar(url, timeout=60, origem="sonda_a3")
    except Exception as e:  # noqa: BLE001
        cod = getattr(e, "code", None)
        print(f"  [{rotulo}] {url} -> ERRO {type(e).__name__} {cod or ''} {str(e)[:120]}")
        return None
    tipo = "pdf" if b[:5] == b"%PDF-" else "texto"
    print(f"  [{rotulo}] {url} -> 200 {len(b)} B {tipo}")
    if tipo == "pdf":
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(b)) as pdf:
                pgs = [(p.extract_text() or "") for p in pdf.pages[:3]]
                print(f"      páginas={len(pdf.pages)} texto_p1={len(pgs[0]) if pgs else 0} :: {re.sub(r'\s+',' ',(pgs[0] if pgs else ''))[:200]}")
        except Exception as e:  # noqa: BLE001
            print(f"      pdf ilegível: {e}")
        return b
    t = b[:maxbytes].decode("utf-8", "replace")
    if html:
        print("      início:", re.sub(r"\s+", " ", t[:300]))
        links = sorted({h for h in RE_HREF.findall(t) if re.search(r"pdf|edic|diar|caderno|busca|pesquis|api|consulta|download|visualiz", h, re.I)})
        print(f"      links({len(links)}):", links[:40])
    apis = sorted({m for m in RE_API.findall(t)})
    if apis:
        print(f"      apis({len(apis)}):", apis[:60])
    if js:
        base = url
        for s in RE_SRC.findall(t)[:6]:
            u = urllib.parse.urljoin(base, s)
            mostra("js", u, html=False)
    return b


UFS = {
    "PA": ["https://www.ioepa.com.br/", "https://www.ioepa.com.br/pages/2026/2026.09.10.DOE.pdf",
           "https://www.ioepa.com.br/pages/2026/09/10/2026.09.10.DOE.pdf", "https://www.ioepa.com.br/diarios/"],
    "RO": ["https://diof.ro.gov.br/", "https://diof.ro.gov.br/data/uploads/2026/09/Doe-10_09_2026.pdf",
           "https://diof.ro.gov.br/diarios/"],
    "RR": ["https://www.imprensaoficial.rr.gov.br/", "https://www.imprensaoficial.rr.gov.br/app/_edicoes/2026/09/doe-20260910.pdf"],
    "RN": ["https://www.diariooficial.rn.gov.br/", "http://diariooficial.rn.gov.br/dei/dorn3/Search.aspx"],
    "RS": ["https://www.diariooficial.rs.gov.br/", "https://www.diariooficial.rs.gov.br/diario?td=DOE&dt=2026-09-10&pg=1"],
    "MG": ["https://www.jornalminasgerais.mg.gov.br/",
           "https://www.jornalminasgerais.mg.gov.br/api/v1/Jornal/ObterEdicaoPorDataPublicacao?dataPublicacao=2026-09-10"],
    "SC": ["https://portal.doe.sea.sc.gov.br/", "https://doe.sea.sc.gov.br/"],
    "AL": ["https://diario.imprensaoficial.al.gov.br/", "https://imprensaoficial.al.gov.br/"],
    "MA": ["https://www.diariooficial.ma.gov.br/", "https://www.diariooficial.ma.gov.br/public/index.xhtml"],
    "BA": ["https://dool.egba.ba.gov.br/", "https://www.egba.ba.gov.br/"],
    "RJ": ["https://www.ioerj.com.br/portal/", "https://www.ioerj.com.br/portal/modules/conteudoonline/do_seleciona_data.php"],
    "SE": ["https://segrase.se.gov.br/", "https://www.segrase.se.gov.br/", "https://iose.se.gov.br/", "https://iose.se.gov.br/portal/"],
}

LEXML = [
    "https://www.lexml.gov.br/busca/SRU?operation=searchRetrieve&version=1.1&maximumRecords=5&query="
    + urllib.parse.quote('dc.description any "emergência em saúde pública" and tipoDocumento any "decreto" and date any "2026"'),
    "https://www.lexml.gov.br/busca/SRU?operation=searchRetrieve&version=1.1&maximumRecords=5&query="
    + urllib.parse.quote('urn any "estadual" and date any "2026"'),
    "https://www.lexml.gov.br/busca/search?keyword=" + urllib.parse.quote("emergência em saúde pública")
    + ";f1-tipoDocumento=Legisla%C3%A7%C3%A3o::Decreto;f2-date=2026",
]

if __name__ == "__main__":
    so = sys.argv[1:] or list(UFS) + ["LEXML"]
    for uf in so:
        print(f"=== {uf} ===")
        if uf == "LEXML":
            for u in LEXML:
                b = mostra("lexml", u)
                if b:
                    print("      corpo:", re.sub(r"\s+", " ", b.decode("utf-8", "replace"))[:3000])
            continue
        for i, u in enumerate(UFS[uf]):
            mostra(uf, u, js=(i == 0))
        sys.stdout.flush()
