#!/usr/bin/env python3
"""
scripts/catalogo_de_falhas.py — toda falha da noite tem linha, causa, prova e o teste que a reproduz
====================================================================================================
Item 2-bis.1 da janela A (central, 10/10/2026). O ensaio simulado passava verde e a noite falhava,
porque cada defeito era descoberto de madrugada e consertado sem memória: ninguém sabia, de manhã,
se a falha da noite era nova ou a terceira volta da mesma. O catálogo é essa memória:
`config/falhas_da_noite.json` (fonte) e `docs/FALHAS_DA_NOITE.md` (gerado daqui, nunca à mão).

**Falha nova vira linha nova — obrigatório.** Este portão reprova:
  - linha sem `id`, `noite`, `titulo`, `sintoma`, `causa`, `prova` ou `correcao`;
  - `caso_de_teste` que aponta para arquivo, função ou caso que não existe na árvore;
  - `caso_de_teste` nulo sem dizer em `falta` o que faltaria para reproduzi-la;
  - `docs/FALHAS_DA_NOITE.md` diferente do que este script gera.

USO
  python3 scripts/catalogo_de_falhas.py              # confere
  python3 scripts/catalogo_de_falhas.py --gerar-doc  # regrava docs/FALHAS_DA_NOITE.md
  python3 scripts/catalogo_de_falhas.py --autoteste
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
FONTE = RAIZ / "config" / "falhas_da_noite.json"
DOC = RAIZ / "docs" / "FALHAS_DA_NOITE.md"
CAMPOS = ("id", "noite", "titulo", "sintoma", "causa", "prova", "correcao")


def caso_existe(caso: str, ler) -> bool:
    """O caso de teste aponta para algo que existe? `ler(caminho)` devolve o texto ou None."""
    caso = str(caso or "").strip()
    if "::" in caso:
        arq, func = caso.split("::", 1)
        t = ler(arq.strip())
        return t is not None and re.search(r"def\s+" + re.escape(func.strip()) + r"\b", t) is not None
    m = re.match(r"^(\S+)\s+--autoteste:\s*(.+)$", caso)
    if m:
        t = ler(m.group(1))
        return t is not None and m.group(2).strip() in t
    return ler(caso.split()[0]) is not None if caso else False


def problemas(cat: dict, ler) -> list:
    out, vistos = [], set()
    for f in (cat or {}).get("falhas") or []:
        fid = f.get("id") or "?"
        for c in CAMPOS:
            if not f.get(c):
                out.append(f"{fid}: campo `{c}` vazio")
        if fid in vistos:
            out.append(f"{fid}: id repetido")
        vistos.add(fid)
        caso = f.get("caso_de_teste")
        if caso:
            if not caso_existe(caso, ler):
                out.append(f"{fid}: caso de teste inexistente na árvore: {caso}")
        elif not str(f.get("falta") or "").strip():
            out.append(f"{fid}: sem caso de teste e sem dizer o que falta")
    return out


def gerar_doc(cat: dict) -> str:
    fal = (cat or {}).get("falhas") or []
    com = sum(1 for f in fal if f.get("caso_de_teste"))
    linhas = ["# Falhas da noite — catálogo", "",
              "Gerado por `scripts/catalogo_de_falhas.py --gerar-doc` a partir de "
              "`config/falhas_da_noite.json`. Não editar à mão.", "",
              f"Atualizado em {cat.get('atualizado_em', '')}. {len(fal)} falhas; {com} com caso de "
              f"teste que as reproduz; {len(fal) - com} sem, com o que falta dito.", "",
              "Falha nova vira linha nova no JSON, com causa, prova e caso de teste.", ""]
    for f in fal:
        linhas += [f"## {f['id']} · {f['titulo']}", "",
                   f"- **Noite:** {f['noite']}",
                   f"- **Sintoma:** {f['sintoma']}",
                   f"- **Causa:** {f['causa']}",
                   f"- **Prova:** {'; '.join(str(p) for p in f.get('prova') or [])}",
                   f"- **Correção:** {f['correcao']}",
                   f"- **Caso de teste:** `{f['caso_de_teste']}`" if f.get("caso_de_teste")
                   else f"- **Caso de teste:** nenhum — falta: {f.get('falta')}", ""]
    return "\n".join(linhas).rstrip() + "\n"


def _ler(rel: str):
    p = RAIZ / rel
    try:
        return p.read_text(encoding="utf-8") if p.is_file() else None
    except (OSError, UnicodeDecodeError):
        return None


def autoteste() -> int:
    arvore = {"a.py": "def ensaio_x():\n    ok('o caso nomeado')\n"}
    ler = arvore.get
    casos = [
        ("função existente passa", caso_existe("a.py::ensaio_x", ler)),
        ("função inexistente reprova", not caso_existe("a.py::ensaio_y", ler)),
        ("caso de autoteste nomeado passa", caso_existe("a.py --autoteste: o caso nomeado", ler)),
        ("caso de autoteste inexistente reprova", not caso_existe("a.py --autoteste: outro", ler)),
        ("arquivo inexistente reprova", not caso_existe("b.py", ler)),
        ("linha completa passa", problemas({"falhas": [dict(zip(CAMPOS, ["F1", "n", "t", "s", "c", ["r"], "p"]),
                                                          caso_de_teste="a.py::ensaio_x")]}, ler) == []),
        ("sem caso e sem falta reprova", len(problemas({"falhas": [dict(zip(CAMPOS, ["F1", "n", "t", "s", "c", ["r"], "p"]),
                                                                       caso_de_teste=None)]}, ler)) == 1),
        ("sem caso com falta dita passa", problemas({"falhas": [dict(zip(CAMPOS, ["F1", "n", "t", "s", "c", ["r"], "p"]),
                                                                    caso_de_teste=None, falta="x")]}, ler) == []),
        ("campo vazio reprova", any("causa" in x for x in problemas(
            {"falhas": [dict(zip(CAMPOS, ["F1", "n", "t", "s", "", ["r"], "p"]), caso_de_teste=None, falta="x")]}, ler))),
    ]
    for n, ok in casos:
        print(("  ✓ " if ok else "  ✗ ") + n)
    falhas = [n for n, ok in casos if not ok]
    print("✗ AUTOTESTE: %d falha(s)" % len(falhas) if falhas else "✓ AUTOTESTE OK")
    return 1 if falhas else 0


def main() -> int:
    argv = sys.argv[1:]
    if "--autoteste" in argv:
        return autoteste()
    cat = json.loads(FONTE.read_text(encoding="utf-8"))
    if "--gerar-doc" in argv:
        DOC.write_text(gerar_doc(cat), encoding="utf-8")
        print(f"docs/FALHAS_DA_NOITE.md regravado ({len(cat.get('falhas') or [])} falhas)")
        return 0
    ruins = problemas(cat, _ler)
    if not DOC.is_file() or DOC.read_text(encoding="utf-8") != gerar_doc(cat):
        ruins.append("docs/FALHAS_DA_NOITE.md defasado — rode `--gerar-doc`")
    for r in ruins:
        print(f"  ✗ {r}")
    fal = cat.get("falhas") or []
    print(f"✗ CATÁLOGO DE FALHAS: {len(ruins)} problema(s)" if ruins else
          f"✓ CATÁLOGO DE FALHAS OK — {len(fal)} falhas, {sum(1 for f in fal if f.get('caso_de_teste'))} "
          f"com caso de teste que existe na árvore.")
    return 1 if ruins else 0


if __name__ == "__main__":
    sys.exit(main())
