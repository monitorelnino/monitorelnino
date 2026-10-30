#!/usr/bin/env python3
"""Lê um documento (PDF ou página) e imprime o que ele diz sobre os termos pedidos. Só leitura.

Por que existe (30/10/2026): fonte da matriz de planos (S10, S17, S19, S26, S30) parava em "não li o
anexo". Um leitor só, pela porta de rede do projeto (robots, muro de robô, recusa respeitada),
resolve as cinco sem um script por fonte. Não grava em `data/`; a saída é o log do run.

Uso: python3 scripts/sondar_documento.py URL [--termos a,b,c]
     python3 scripts/sondar_documento.py --autoteste
"""
import io
import re
import sys

TETO = 6000


def texto_de(corpo: bytes) -> tuple:
    """(tipo, texto, links_pdf). Função pura."""
    if corpo[:5] == b"%PDF-":
        import pdfplumber  # dependência travada em requirements.txt; o runner não traz pdftotext
        with pdfplumber.open(io.BytesIO(corpo)) as pdf:
            return "pdf", "\n".join(p.extract_text() or "" for p in pdf.pages), []
    html = corpo.decode("utf-8", "replace")
    links = sorted(set(re.findall(r'href="([^"]+\.pdf[^"]*)"', html, re.I)))[:20]
    return "html", re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)), links


def trechos(texto: str, termo: str, n: int = 3, raio: int = 140) -> list:
    achados = [m.start() for m in re.finditer(re.escape(termo), texto, re.I)]
    return [re.sub(r"\s+", " ", texto[max(0, i - raio):i + raio]) for i in achados[:n]]


def main(argv: list) -> int:
    if "--autoteste" in argv:
        t, txt, ln = texto_de('<p>Plano de <b>Contingência</b></p><a href="a.pdf">x</a>'.encode())
        falhas = [m for m, c in (("html", t == "html" and "Contingência" in txt and ln == ["a.pdf"]),
                                 ("trecho", len(trechos("aaa contingência bbb", "CONTINGÊNCIA")) == 1)) if not c]
        print("✗ AUTOTESTE: " + ", ".join(falhas) if falhas else "✓ AUTOTESTE OK — 2 casos, sem rede e sem escrita.")
        return 1 if falhas else 0
    url = argv[0]
    termos = (argv[argv.index("--termos") + 1] if "--termos" in argv else "plano de contingência").split(",")
    from coletores_base import buscar
    tipo, texto, links = texto_de(buscar(url, timeout=90))
    print(f"{url}: {tipo}, {len(texto)} caracteres")
    for ln in links:
        print("  link pdf:", ln)
    for termo in termos:
        achados = trechos(texto, termo.strip())
        print(f"termo {termo!r}: {len(re.findall(re.escape(termo.strip()), texto, re.I))} ocorrência(s)")
        for a in achados:
            print("   …", a)
    print("--- início ---\n" + texto[:TETO])
    return 0


if __name__ == "__main__":
    sys.path.insert(0, __file__.rsplit("/", 2)[0])
    sys.exit(main(sys.argv[1:]))
