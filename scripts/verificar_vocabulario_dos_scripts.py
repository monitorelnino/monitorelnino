#!/usr/bin/env python3
"""verificar_vocabulario_dos_scripts.py — o vocabulário proibido também no texto que nasce em JS.

09/10/2026 (ajuste 1): o rodapé do cartão de cada estado dizia "feed de atualizações (Atom)" — termo
técnico e instrução de uso — e nenhum portão via: o cartão nasce em JavaScript, dentro de um
`<dialog>` que só abre no clique, e a conformidade lê o texto visível da página renderizada fechada.
Este portão lê o TEXTO DE MARCAÇÃO dentro dos scripts das páginas (o que está entre `>` e `<` em
literais de string e de template) e aplica a lista `vocabulario_proibido.global` de
`layout/regras.json`, com a mesma régua de `verificar_conformidade.problemas_de_vocabulario`.
Atributos (`type="application/atom+xml"`) e o `<head>` não são texto e não contam.

USO
    python3 scripts/verificar_vocabulario_dos_scripts.py --autoteste
    python3 scripts/verificar_vocabulario_dos_scripts.py
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))

RE_TEXTO = re.compile(r">([^<>`'\"]{2,400})<")


def textos_de_marcacao(fonte: str) -> list:
    """Os trechos de texto entre tags num fonte JS, sem interpolação. Função pura."""
    sem_interp = re.sub(r"\$\{[^{}]*\}", " ", fonte)
    return [t.strip() for t in RE_TEXTO.findall(sem_interp) if re.search(r"[A-Za-zÀ-ÿ]{3}", t)]


def problemas(fonte: str, arquivo: str, regras: dict) -> list:
    from verificar_conformidade import problemas_de_vocabulario
    out = []
    for t in textos_de_marcacao(fonte):
        for p in problemas_de_vocabulario(t, arquivo, {"vocabulario_proibido": {
                "global": (regras.get("vocabulario_proibido") or {}).get("global") or []}}, {}):
            out.append(f"{arquivo}: {p} — {t[:80]!r}")
    return out


def autoteste() -> int:
    regras = {"vocabulario_proibido": {"global": ["Atom", "dados abertos"]}}
    velho = '<p class="note">Acompanhe: <a href="f.xml" type="application/atom+xml">feed de atualizações (Atom)</a> — x</p>'
    novo = '<p class="note"><a href="feeds/${d.uf}.xml">Feed de atualizações de ${esc(d.nome)}</a> — cada instrumento</p>'
    casos = [
        ("o texto antigo do cartão reprova", problemas(velho, "index.js", regras) != []),
        ("o texto novo passa", problemas(novo, "index.js", regras) == []),
        ("atributo type não é texto", problemas('<a type="application/atom+xml">Feed</a>', "x.js", regras) == []),
        ("palavra dentro de outra não casa", problemas("<p>anatomia do dado</p>", "x.js", regras) == []),
    ]
    for n, ok in casos:
        print(f"  {'OK  ' if ok else 'FALHA'} {n}")
    falhas = [n for n, ok in casos if not ok]
    print(f"{'X' if falhas else 'OK'} AUTOTESTE — {len(casos)} casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def main() -> int:
    regras = json.loads((RAIZ / "layout" / "regras.json").read_text(encoding="utf-8"))
    ruins = []
    arquivos = sorted((RAIZ / "assets" / "js").glob("*.js")) + [RAIZ / "assets" / "mapas.js"]
    for a in arquivos:
        if a.exists():
            ruins += problemas(a.read_text(encoding="utf-8"), a.relative_to(RAIZ).as_posix(), regras)
    for r in ruins:
        print(f"  ✗ {r}")
    print(f"✗ VOCABULÁRIO DOS SCRIPTS: {len(ruins)} ocorrência(s)." if ruins else
          f"✓ VOCABULÁRIO DOS SCRIPTS OK — {len(arquivos)} script(s) de página, nenhum termo proibido no "
          f"texto que eles escrevem.")
    return 1 if ruins else 0


if __name__ == "__main__":
    sys.exit(autoteste() if "--autoteste" in sys.argv else main())
