#!/usr/bin/env python3
"""Portão: os cartões do topo do Financiamento contra a edição da imprensa (item 4, 02/10/2026).

Dois arquivos contam a mesma coisa para públicos diferentes — `data/financiamento/semana.json`
(topo da página) e `data/imprensa/semana.json` (edição para a imprensa). Quando os dois falam do
MESMO recorte, o número tem de ser o mesmo: duas contas do mesmo dado publicadas com valores
diferentes é o tipo de divergência que o leitor encontra antes de nós.

O que ele confere:
1. Os quatro cartões existem, com os identificadores do contrato de layout.
2. Cartão sem coleta tem motivo escrito e valor nulo — nunca zero no lugar de ausência.
3. Cartão com recorte de sete dias bate com o cartão equivalente da imprensa, quando ela traz o
   mesmo recorte. Recorte mensal não se compara com semanal: a divergência seria da janela.
4. O corte do arquivo não está mais velho que o da imprensa.

Autoteste (`--autoteste`) exercita a função pura com entrada inventada, sem ler `data/`.
"""
from __future__ import annotations

import json
import pathlib
import sys
from datetime import datetime

RAIZ = pathlib.Path(__file__).resolve().parent.parent
ESPERADOS = ["pago_periodo_mp", "transferido_municipios_periodo", "resposta_liberado_semana",
             "atos_federais_semana"]
# Cartão do Financiamento → cartão da imprensa que mede a MESMA coisa na MESMA janela.
MESMO_NUMERO = {"atos_federais_semana": "atos_federais_no_periodo"}


def _data(s):
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(s)[:10], fmt)
        except (ValueError, TypeError):
            continue
    return None


def problemas(fin: dict, imp: dict) -> list:
    """Função pura: devolve a lista de divergências, sem ler disco nem rede."""
    ruins = []
    cartoes = {c.get("id"): c for c in (fin or {}).get("cartoes") or []}
    for ident in ESPERADOS:
        if ident not in cartoes:
            ruins.append(f"cartão '{ident}' não existe em financiamento/semana.json")
    for ident, c in cartoes.items():
        if c.get("sem_coleta"):
            if c.get("valor") is not None:
                ruins.append(f"cartão '{ident}': declarado sem coleta e com valor — ausência não é número")
            if not c.get("detalhe"):
                ruins.append(f"cartão '{ident}': sem coleta e sem motivo escrito (lacuna tem de ser declarada)")
        else:
            if c.get("valor") is None:
                ruins.append(f"cartão '{ident}': valor nulo sem declarar a lacuna")
            if not c.get("periodo"):
                ruins.append(f"cartão '{ident}': sem o período a que o número se refere")
            if not c.get("fonte"):
                ruins.append(f"cartão '{ident}': sem fonte")

    por_id_imp = {c.get("id"): c for c in (imp or {}).get("cartoes") or []}
    for aqui, la in MESMO_NUMERO.items():
        a, b = cartoes.get(aqui), por_id_imp.get(la)
        if not a or not b or a.get("sem_coleta") or b.get("sem_coleta"):
            continue
        if a.get("valor") != b.get("valor"):
            ruins.append(f"mesmo número com valores diferentes: '{aqui}' = {a.get('valor')} e "
                         f"imprensa '{la}' = {b.get('valor')}")

    d_fin, d_imp = _data((fin or {}).get("corte")), _data((imp or {}).get("corte"))
    if d_fin and d_imp and d_fin < d_imp:
        ruins.append(f"corte do Financiamento ({fin.get('corte')}) mais velho que o da imprensa "
                     f"({imp.get('corte')})")
    return ruins


def _autoteste() -> int:
    falhas = []

    def ok(nome, cond):
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    base = {"corte": "02/10/2026", "cartoes": [
        {"id": i, "valor": 1, "periodo": "x", "fonte": "f", "sem_coleta": False} for i in ESPERADOS]}
    ok("arquivo completo passa", problemas(base, {"corte": "02/10/2026", "cartoes": []}) == [])

    faltando = {"corte": "02/10/2026", "cartoes": base["cartoes"][:2]}
    ok("cartão faltando reprova", len(problemas(faltando, {})) == 2)

    zero_falso = {"corte": "02/10/2026", "cartoes": [
        dict(base["cartoes"][0], sem_coleta=True, valor=0, detalhe="x")] + base["cartoes"][1:]}
    ok("sem coleta com valor reprova", any("ausência não é número" in p for p in problemas(zero_falso, {})))

    sem_motivo = {"corte": "02/10/2026", "cartoes": [
        dict(base["cartoes"][0], sem_coleta=True, valor=None)] + base["cartoes"][1:]}
    ok("sem coleta sem motivo reprova", any("sem motivo escrito" in p for p in problemas(sem_motivo, {})))

    sem_periodo = {"corte": "02/10/2026", "cartoes": [
        dict(base["cartoes"][0], periodo=None)] + base["cartoes"][1:]}
    ok("valor sem período reprova", any("sem o período" in p for p in problemas(sem_periodo, {})))

    imp = {"corte": "02/10/2026", "cartoes": [
        {"id": "atos_federais_no_periodo", "valor": 9, "sem_coleta": False}]}
    ok("mesmo número divergente reprova", any("valores diferentes" in p for p in problemas(base, imp)))
    imp_igual = {"corte": "02/10/2026", "cartoes": [
        {"id": "atos_federais_no_periodo", "valor": 1, "sem_coleta": False}]}
    ok("mesmo número igual passa", problemas(base, imp_igual) == [])
    imp_lacuna = {"corte": "02/10/2026", "cartoes": [
        {"id": "atos_federais_no_periodo", "valor": None, "sem_coleta": True}]}
    ok("imprensa sem coleta não compara", problemas(base, imp_lacuna) == [])

    ok("corte mais velho reprova",
       any("mais velho" in p for p in problemas(dict(base, corte="29/09/2026"),
                                                {"corte": "02/10/2026", "cartoes": []})))
    ok("corte ilegível não levanta", problemas(dict(base, corte="ontem"), {"corte": "x"}) == [])

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else "✓ AUTOTESTE OK — 10 casos, sem rede e sem leitura de data/.")
    return 1 if falhas else 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return _autoteste()

    def ler(rel):
        p = RAIZ / "data" / rel
        if not p.exists():
            return None
        return json.loads(p.read_text(encoding="utf-8"))

    fin = ler("financiamento/semana.json")
    if fin is None:
        print("✗ COERÊNCIA FINANCIAMENTO: data/financiamento/semana.json não existe — "
              "rode gerar_financiamento_semana.py")
        return 1
    ruins = problemas(fin, ler("imprensa/semana.json") or {})
    if ruins:
        print(f"✗ COERÊNCIA FINANCIAMENTO: {len(ruins)} divergência(s):")
        for r in ruins:
            print("   - " + r)
        return 1
    print(f"✓ COERÊNCIA FINANCIAMENTO OK — {len(fin.get('cartoes') or [])} cartões com período, "
          "fonte e lacuna declarada, e o mesmo número da imprensa onde a janela é a mesma.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
