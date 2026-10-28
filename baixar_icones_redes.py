#!/usr/bin/env python3
"""baixar_icones_redes.py — kits oficiais de Instagram e LinkedIn para o rodapé (uso único, válvula de dia).

Busca a página oficial de cada rede, acha o SVG (ou o zip com SVGs) que ela distribui e grava os SVGs
pequenos em data/icones_redes/<rede>/ (+ .origem); a escolha do glifo e o assets/redes/ são de outro passo.
Recusa (401, 403, 429, 451, muro de robô) ou glifo não achado = lacuna impressa no log; nada é
desenhado à mão nem copiado de terceiro. Cliente identificado e robots pelos coletores_base.
Uso: python3 baixar_icones_redes.py"""
import io
import re
import sys
import urllib.parse
import zipfile

import coletores_base as cb

REDES = {
    "instagram": ["https://about.meta.com/brand/resources/instagram/icons",
                  "https://about.meta.com/brand/resources/instagram/instagram-brand/",
                  "https://about.instagram.com/brand"],
    "linkedin": ["https://brand.linkedin.com/downloads"],
}


def candidatos(pagina: str, base: str) -> list:
    achados = re.findall(r'(?:href|src|data-src|content)=["\']([^"\']+?\.(?:svg|zip)(?:\?[^"\']*)?)["\']', pagina, re.I)
    return list(dict.fromkeys(urllib.parse.urljoin(base, a.replace("&amp;", "&")) for a in achados))


def todos(url: str):
    """[(nome, bytes)] de todos os SVGs pequenos em `url` (svg direto ou zip)."""
    corpo = cb.buscar(url, timeout=90, origem="icones-redes")
    if url.lower().split("?")[0].endswith(".svg"):
        return [(url.rsplit("/", 1)[-1].split("?")[0], corpo)]
    with zipfile.ZipFile(io.BytesIO(corpo)) as z:
        return [(n, z.read(n)) for n in z.namelist()
                if n.lower().endswith(".svg") and "__macosx" not in n.lower()][:40]


def main() -> int:
    saida = cb.RAIZ / "data" / "icones_redes"
    total = 0
    for rede, paginas in REDES.items():
        for pagina_url in paginas:
            print(f"== {rede}: {pagina_url}")
            try:
                pagina = cb.buscar(pagina_url, timeout=60, origem="icones-redes").decode("utf-8", "replace")
            except Exception as e:  # noqa: BLE001
                print(f"  LACUNA {rede}: {type(e).__name__}: {str(e)[:160]}")
                continue
            cand = candidatos(pagina, pagina_url)
            print(f"  candidatos: {cand[:15]}")
            for u in cand[:6]:
                try:
                    for nome, svg in todos(u):
                        if len(svg) > 60000 or b"<svg" not in svg[:3000].lower():
                            continue
                        d = saida / rede
                        d.mkdir(parents=True, exist_ok=True)
                        alvo = re.sub(r"[^A-Za-z0-9._-]+", "_", nome)
                        (d / alvo).write_bytes(svg)
                        (d / (alvo + ".origem")).write_text(f"{pagina_url}\n{u}\n{cb.hoje()}\n", encoding="utf-8")
                        total += 1
                        print(f"  gravado {rede}/{alvo} ({len(svg)} B)")
                except Exception as e:  # noqa: BLE001 — recusa ou zip ruim: tenta o próximo
                    print(f"  falha {u}: {type(e).__name__}: {str(e)[:120]}")
    print(f"gravados: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
