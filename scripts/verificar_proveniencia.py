#!/usr/bin/env python3
"""verificar_proveniencia.py — todo documento pontuado aponta para o próprio endereço (ajuste 2, 09/10/2026).

Reprova:
  1. instrumento estadual (`data/estados.json › ufs[].instrumentos[]`) com status diferente de `LAC`
     sem `url`/`urls` E sem `endereco_lacuna` declarada — endereço ou lacuna, nunca silêncio;
  2. registro municipal pontuado (`plano`, `plano_antigo`, `estrutura`) sem `url` em
     `data/municipios.json`;
  3. o cartão do estado em `assets/js/index.js` sem o link do documento (`docComEndereco`) ou sem a
     frase do teto de ausência.

USO
    python3 scripts/verificar_proveniencia.py --autoteste
    python3 scripts/verificar_proveniencia.py
"""
from __future__ import annotations

import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
PONTUADAS = ("plano", "plano_antigo", "estrutura")


def problemas(estados: dict, municipios: list, js: str) -> list:
    out = []
    for u in (estados or {}).get("ufs") or []:
        for i in u.get("instrumentos") or []:
            if i.get("status") == "LAC":
                continue
            if not (i.get("url") or i.get("urls") or i.get("endereco_lacuna")):
                out.append(f"{u.get('uf')} · {i.get('tipo')}: sem endereço e sem lacuna declarada")
    for m in municipios or []:
        if m.get("categoria") in PONTUADAS and not m.get("url"):
            out.append(f"{m.get('nome')}/{m.get('uf')} · {m.get('categoria')}: pontuado sem endereço")
    if "docComEndereco(d)" not in js or "docComEndereco(d.estrutura)" not in js:
        out.append("assets/js/index.js: o cartão do estado não liga o documento ao endereço")
    if "endereço do documento não localizado até o corte" not in js:
        out.append("assets/js/index.js: o cartão do estado não declara a lacuna de endereço")
    return out


def autoteste() -> int:
    js_ok = "docComEndereco(d) docComEndereco(d.estrutura) endereço do documento não localizado até o corte"
    bom = {"ufs": [{"uf": "SC", "instrumentos": [{"tipo": "x", "status": "NOVO", "url": "https://a.sc.gov.br/p.pdf"},
                                                {"tipo": "y", "status": "READ", "endereco_lacuna": {"motivo": "m"}},
                                                {"tipo": "z", "status": "LAC"}]}]}
    ruim = {"ufs": [{"uf": "SC", "instrumentos": [{"tipo": "x", "status": "NOVO"}]}]}
    casos = [
        ("endereço ou lacuna declarada passa", problemas(bom, [], js_ok) == []),
        ("instrumento sem endereço e sem lacuna reprova", len(problemas(ruim, [], js_ok)) == 1),
        ("plano municipal sem endereço reprova",
         len(problemas(bom, [{"nome": "X", "uf": "SC", "categoria": "plano"}], js_ok)) == 1),
        ("decreto sem endereço não é pontuado e passa",
         problemas(bom, [{"nome": "X", "uf": "SC", "categoria": "decreto"}], js_ok) == []),
        ("cartão sem link reprova", len(problemas(bom, [], "nada")) == 2),
    ]
    for n, ok in casos:
        print(f"  {'OK  ' if ok else 'FALHA'} {n}")
    falhas = [n for n, ok in casos if not ok]
    print(f"{'X' if falhas else 'OK'} AUTOTESTE — {len(casos)} casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def main() -> int:
    estados = json.loads((RAIZ / "data" / "estados.json").read_text(encoding="utf-8"))
    mun = json.loads((RAIZ / "data" / "municipios.json").read_text(encoding="utf-8"))
    mun = mun if isinstance(mun, list) else mun.get("municipios") or []
    js = (RAIZ / "assets" / "js" / "index.js").read_text(encoding="utf-8")
    ruins = problemas(estados, mun, js)
    for r in ruins:
        print(f"  ✗ {r}")
    com = sum(1 for u in estados["ufs"] for i in u.get("instrumentos") or [] if i.get("url") or i.get("urls"))
    lac = sum(1 for u in estados["ufs"] for i in u.get("instrumentos") or [] if i.get("endereco_lacuna"))
    print(f"✗ PROVENIÊNCIA: {len(ruins)} problema(s)." if ruins else
          f"✓ PROVENIÊNCIA OK — instrumentos estaduais: {com} com endereço, {lac} com lacuna declarada; "
          f"todo registro municipal pontuado tem endereço; o cartão liga o documento.")
    return 1 if ruins else 0


if __name__ == "__main__":
    sys.exit(autoteste() if "--autoteste" in sys.argv else main())
