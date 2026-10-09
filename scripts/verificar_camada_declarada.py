#!/usr/bin/env python3
"""Portão: a camada declarada nunca conta mais municípios do que o estado tem.

Item 1.8 do HANDOVER_CORRECAO_DEFINITIVA_08-10-2026 (achado A3-02, decisão D2). A camada declarada
soma ao índice os municípios que um levantamento oficial diz ter plano, com metade do crédito. Ela
contava população **duas vezes**, por dois caminhos:

1. o excedente subtraía só as categorias de `PESO_DOC`, deixando fora `estrutura` e
   `coberto_estadual`, que também recebem crédito — município já creditado voltava a contar;
2. o termo dos planos desatualizados era somado ao dos planos sem desconto nenhum, e nada impedia
   a soma de passar do número de municípios do estado. No RS eram 183 + 215 = 398 declarantes num
   levantamento de 485 respondentes, em 497 municípios; o DF aparecia com cobertura 80 tendo um
   município só.

O que este portão cobra, em `data/percentual_uf.json`:

- `declarado_plano + declarado_antigo ≤ total` de municípios da UF;
- cada contador, isolado, ≤ `total`;
- contador declarado exige `fonte_declarada` — número sem fonte não entra no índice;
- nenhum contador negativo.

`--autoteste` é puro: não lê `data/`, não escreve nada.
"""
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
ARQUIVO = RAIZ / "data" / "percentual_uf.json"


def problemas(por_uf: dict) -> list:
    fora = []
    for uf, x in sorted(por_uf.items()):
        dp = x.get("declarado_plano") or 0
        da = x.get("declarado_antigo") or 0
        total = x.get("total") or 0
        if dp < 0 or da < 0:
            fora.append(f"{uf}: contador declarado negativo (plano {dp}, antigo {da})")
        if total and dp > total:
            fora.append(f"{uf}: declarado_plano {dp} acima dos {total} municípios da UF")
        if total and da > total:
            fora.append(f"{uf}: declarado_antigo {da} acima dos {total} municípios da UF")
        if total and dp + da > total:
            fora.append(f"{uf}: declarado_plano + declarado_antigo = {dp + da} acima dos {total} "
                        f"municípios da UF — a mesma população contada duas vezes (D2)")
        if (dp or da) and not str(x.get("fonte_declarada") or "").strip():
            fora.append(f"{uf}: contador declarado sem `fonte_declarada` — número sem fonte não "
                        f"entra no índice")
    return fora


def autoteste() -> int:
    casos = [
        ("dentro do total passa",
         {"RS": {"total": 497, "declarado_plano": 183, "declarado_antigo": 215,
                 "fonte_declarada": "TCE-RS 2025"}}, 0),
        ("soma acima do total reprova",
         {"RS": {"total": 300, "declarado_plano": 183, "declarado_antigo": 215,
                 "fonte_declarada": "TCE-RS 2025"}}, 1),
        ("um contador acima do total reprova",
         {"DF": {"total": 1, "declarado_plano": 80, "fonte_declarada": "MUNIC"}}, 2),
        ("sem fonte reprova",
         {"PR": {"total": 399, "declarado_plano": 399}}, 1),
        ("negativo reprova",
         {"PR": {"total": 399, "declarado_plano": -1, "fonte_declarada": "x"}}, 1),
        ("UF sem contador declarado passa", {"SP": {"total": 645}}, 0),
        ("soma igual ao total passa",
         {"PR": {"total": 399, "declarado_plano": 399, "declarado_antigo": 0,
                 "fonte_declarada": "SISDC/CEPDEC-PR"}}, 0),
    ]
    falhas = 0
    for nome, dado, esperado in casos:
        achados = problemas(dado)
        ok = len(achados) == esperado
        print(f"  {'ok ' if ok else 'FALHA'} {nome}: {len(achados)} problema(s)")
        if not ok:
            falhas += 1
            for a in achados:
                print(f"        {a}")
    print(f"autoteste: {len(casos) - falhas}/{len(casos)}")
    return 1 if falhas else 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    doc = json.loads(ARQUIVO.read_text(encoding="utf-8"))
    bruto = doc.get("uf") if isinstance(doc, dict) and "uf" in doc else doc
    por_uf = bruto if isinstance(bruto, dict) else {x["uf"]: x for x in bruto}
    fora = problemas(por_uf)
    if fora:
        print(f"VERMELHO: {len(fora)} problema(s) na camada declarada (D2)")
        for f in fora:
            print(f"  · {f}")
        return 1
    n = sum(1 for x in por_uf.values()
            if (x.get("declarado_plano") or 0) or (x.get("declarado_antigo") or 0))
    print(f"ok: {n} UF(s) com camada declarada, todas dentro do número de municípios do estado")
    return 0


if __name__ == "__main__":
    sys.exit(main())
