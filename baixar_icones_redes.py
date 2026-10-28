#!/usr/bin/env python3
"""baixar_icones_redes.py — kits oficiais de Instagram e LinkedIn para o rodapé (uso único, válvula de dia).

Busca a página oficial de cada rede, acha o SVG (ou o zip com SVGs) que ela distribui e grava só o
glifo monocromático em assets/redes/<rede>.svg, com a procedência em assets/redes/LEIAME.md.
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
    "instagram": "https://about.meta.com/brand/resources/instagram/icons",
    "linkedin": "https://brand.linkedin.com/downloads",
}
PREFERE = ("glyph", "mono", "black", "preto", "icon")


def candidatos(pagina: str, base: str) -> list:
    achados = re.findall(r'(?:href|src|data-src|content)=["\']([^"\']+?\.(?:svg|zip)(?:\?[^"\']*)?)["\']', pagina, re.I)
    return list(dict.fromkeys(urllib.parse.urljoin(base, a.replace("&amp;", "&")) for a in achados))


def pontos(nome: str) -> int:
    n = nome.lower()
    return sum(1 for p in PREFERE if p in n) - (3 if re.search(r"white|branco|logo|wordmark|color", n) else 0)


def glifo(url: str):
    """(nome, bytes_svg) do melhor SVG em `url` (svg direto ou zip), ou None."""
    corpo = cb.buscar(url, timeout=90, origem="icones-redes")
    if url.lower().split("?")[0].endswith(".svg"):
        return url, corpo
    with zipfile.ZipFile(io.BytesIO(corpo)) as z:
        svgs = [n for n in z.namelist() if n.lower().endswith(".svg") and "__macosx" not in n.lower()]
        print(f"  zip {url}: {len(svgs)} svg")
        if not svgs:
            return None
        melhor = max(svgs, key=pontos)
        print(f"  escolhido: {melhor} (pontos {pontos(melhor)}); outros: {svgs[:12]}")
        return f"{url}::{melhor}", z.read(melhor)


def main() -> int:
    linhas, gravados = [], 0
    for rede, pagina_url in REDES.items():
        print(f"== {rede}: {pagina_url}")
        try:
            pagina = cb.buscar(pagina_url, timeout=60, origem="icones-redes").decode("utf-8", "replace")
            cand = candidatos(pagina, pagina_url)
            print(f"  candidatos: {cand[:15]}")
            ordenados = sorted(cand, key=lambda u: -pontos(u))
            for u in ordenados[:6]:
                try:
                    r = glifo(u)
                except Exception as e:  # noqa: BLE001 — recusa ou zip ruim: tenta o próximo
                    print(f"  falha {u}: {type(e).__name__}: {str(e)[:120]}")
                    continue
                if r and b"<svg" in r[1][:2000].lower():
                    cb_path = cb.RAIZ / "assets" / "redes" / f"{rede}.svg"
                    cb_path.parent.mkdir(parents=True, exist_ok=True)
                    cb_path.write_bytes(r[1])
                    linhas.append(f"- {rede}: {pagina_url} · arquivo {r[0]} · baixado em {cb.hoje()} · "
                                   f"guia de uso: conferir na página oficial (monocromático, sem alterar o glifo)")
                    gravados += 1
                    break
            else:
                print(f"  LACUNA {rede}: nenhum SVG utilizável na página")
        except Exception as e:  # noqa: BLE001
            print(f"  LACUNA {rede}: {type(e).__name__}: {str(e)[:200]}")
    if linhas:
        (cb.RAIZ / "assets" / "redes" / "LEIAME.md").write_text(
            "# Ícones das redes — procedência\n\nKits oficiais de cada rede, sem alteração do glifo.\n\n"
            + "\n".join(linhas) + "\n", encoding="utf-8")
    print(f"gravados: {gravados}/{len(REDES)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
