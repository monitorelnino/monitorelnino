#!/usr/bin/env python3
"""verificar_grades_de_numeros.py — grade sem cartão órfão; cartão de figura com um título só.

09/10/2026 (ajustes 3 e 5 do Monitor de riscos): quatro cartões numa grade de três deixavam o
quarto sozinho na segunda linha, e cada mapa tinha quatro camadas de cabeçalho (sobretítulo
versalete + frase + título + fonte). Este portão lê o HTML publicado:

  1. toda `.grade-numeros--N` (N = 3 ou 4) com cartões escritos no HTML tem um múltiplo de N;
  2. nas páginas cujo contrato declara `"cartao_figura_um_titulo": true`, nenhum `.cartao-mapa`
     traz sobretítulo (`.cartao-mapa-familia`) além do título.

USO
    python3 scripts/verificar_grades_de_numeros.py --autoteste
    python3 scripts/verificar_grades_de_numeros.py
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent


def _blocos(html: str, abertura: re.Pattern) -> list:
    """Os trechos de cada <div|figure> que casa com `abertura`, até o fechamento equilibrado."""
    out = []
    for m in abertura.finditer(html):
        tag = m.group(1)
        nivel, i = 0, m.start()
        for t in re.finditer(rf"<(/?){tag}\b[^>]*>", html[m.start():]):
            nivel += -1 if t.group(1) else 1
            if nivel == 0:
                out.append(html[m.start(): m.start() + t.end()])
                break
    return out


def problemas(html: str, um_titulo: bool = False) -> list:
    p = []
    for bloco in _blocos(html, re.compile(r'<(div)[^>]*class="[^"]*grade-numeros--(3|4)[^"]*"')):
        n = int(re.search(r"grade-numeros--(\d)", bloco).group(1))
        filhos = len(re.findall(r'class="cartao-numero(?:\s|")', bloco))
        if filhos and filhos % n:
            p.append(f"grade de {n} com {filhos} cartões: cartão órfão na última linha")
    if um_titulo:
        for fig in _blocos(html, re.compile(r'<(figure)[^>]*class="[^"]*cartao-mapa[^"]*"')):
            if "cartao-mapa-familia" in fig and "figura-titulo" in fig:
                ident = re.search(r'id="([^"]+)"', fig)
                p.append(f"cartão de figura {ident.group(1) if ident else ''} com sobretítulo e título")
    return p


def autoteste() -> int:
    c = lambda: '<div class="cartao-numero x"></div>'  # noqa: E731
    casos = [
        ("quatro numa grade de três reprova",
         problemas(f'<div class="grade-numeros grade-numeros--3">{c()*4}</div>') != []),
        ("três numa grade de três passa", problemas(f'<div class="grade-numeros grade-numeros--3">{c()*3}</div>') == []),
        ("seis numa grade de três passa", problemas(f'<div class="grade-numeros grade-numeros--3">{c()*6}</div>') == []),
        ("grade vazia (preenchida pelo script) passa", problemas('<div class="grade-numeros grade-numeros--3"></div>') == []),
        ("figura com sobretítulo e título reprova",
         problemas('<figure class="figura cartao-mapa" id="a"><p class="cartao-mapa-familia">Seca</p><h3 class="figura-titulo">T</h3></figure>', True) != []),
        ("figura só com título passa",
         problemas('<figure class="figura cartao-mapa" id="a"><h3 class="figura-titulo">T</h3></figure>', True) == []),
    ]
    for n, ok in casos:
        print(f"  {'OK  ' if ok else 'FALHA'} {n}")
    f = [n for n, ok in casos if not ok]
    print(f"{'X' if f else 'OK'} AUTOTESTE — {len(casos)} casos, sem rede e sem escrita.")
    return 1 if f else 0


def main() -> int:
    regras = json.loads((RAIZ / "layout" / "regras.json").read_text(encoding="utf-8"))
    paginas = [x for x in regras.get("paginas_publicas") or [] if (RAIZ / x).exists()]
    ruins = []
    for pg in paginas:
        contrato = RAIZ / "layout" / "contratos" / pg.replace(".html", ".json")
        um = json.loads(contrato.read_text(encoding="utf-8")).get("cartao_figura_um_titulo") if contrato.exists() else False
        ruins += [f"{pg}: {x}" for x in problemas((RAIZ / pg).read_text(encoding="utf-8"), bool(um))]
    for r in ruins:
        print(f"  ✗ {r}")
    print(f"✗ GRADES: {len(ruins)} problema(s)." if ruins else
          f"✓ GRADES OK — {len(paginas)} página(s): nenhum cartão órfão; figura com um título só onde o contrato pede.")
    return 1 if ruins else 0


if __name__ == "__main__":
    sys.exit(autoteste() if "--autoteste" in sys.argv else main())
