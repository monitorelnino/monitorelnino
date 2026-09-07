"""Helper dos portões em Python (06/09/2026, CSP sem unsafe-inline): o script de cada página vive em
assets/js/<página>.js; os portões que inspecionam o JS da página leem o HTML com o script embutido."""
import pathlib, re

def ler_pagina(caminho) -> str:
    p = pathlib.Path(caminho); html = p.read_text(encoding="utf-8")
    def emb(m):
        js = p.parent / m.group(1)
        return "<script>\n" + js.read_text(encoding="utf-8") + "\n</script>" if js.exists() else m.group(0)
    return re.sub(r'<script src="(assets/js/[^"?]+)(?:\?v=[0-9a-f]+)?" defer></script>', emb, html)
