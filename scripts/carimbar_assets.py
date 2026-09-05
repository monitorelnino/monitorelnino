#!/usr/bin/env python3
"""
carimbar_assets.py — cache-busting determinístico (05/09/2026)
==============================================================
Os arquivos em /assets/* ficam 24 h no cache do navegador (netlify.toml). Quando o tema
muda, o HTML (revalidado a cada visita) continuaria apontando para o MESMO nome de
arquivo, e o leitor veria a folha velha. Este script reescreve, nas páginas, cada
referência a assets/<arquivo> com ?v=<8 hex do sha256 do conteúdo>. Determinístico:
o mesmo conteúdo produz o mesmo carimbo (a cadeia de derivados continua reprodutível).
Roda na cadeia de derivados, antes do manifesto.
"""
import hashlib, re, sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PAGINAS = sorted(RAIZ.glob("*.html"))


def carimbo(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()[:8]


def carimbar(html: str) -> tuple:
    """Substitui href/src="assets/x.ext(?v=...)?" por assets/x.ext?v=<hash>. Devolve (html, nº de trocas)."""
    n = 0
    def f(m):
        nonlocal n
        attr, rel = m.group(1), m.group(2)
        p = RAIZ / rel
        if not p.exists():
            return m.group(0)
        n += 1
        return f'{attr}="{rel}?v={carimbo(p)}"'
    out = re.sub(r'\b(href|src)="(assets/[A-Za-z0-9_\-./]+\.(?:css|js|svg|png|woff2?))(?:\?v=[0-9a-f]+)?"', f, html)
    return out, n


def main() -> int:
    total = 0
    for pg in PAGINAS:
        t = pg.read_text(encoding="utf-8"); t2, n = carimbar(t)
        if t2 != t:
            pg.write_text(t2, encoding="utf-8")
        total += n
    print(f"carimbar_assets: {total} referência(s) carimbada(s) em {len(PAGINAS)} página(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
