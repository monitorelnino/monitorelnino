#!/usr/bin/env python3
"""Estrutura comum dos desfechos do SUS (E1, 25/10/2026): funções puras, sem rede e sem escrita.

Um registro de desfecho guarda: série por UF (período → valor; `None` = ausência de dado, nunca zero
por omissão), último valor, cortes do mapa (faixa habitual por quintis), fonte, cadência, `preliminar`
e `parcial`. Os cortes da faixa habitual são calculados sobre 2019–2025 uma vez e gravados num arquivo
de parâmetros que só é escrito se ainda não existir (congelamento). `ler` e `gravar` são injetados:
o autoteste troca-os por falsos e nunca toca `data/`.
Uso: `python3 scripts/estrutura_desfechos.py --autoteste`.
"""
from __future__ import annotations

import statistics
import sys

ANOS_HABITUAIS = range(2019, 2026)
ROTULOS_FAIXA = ("muito abaixo", "abaixo", "na faixa", "acima", "muito acima")
CADENCIAS = ("diaria", "semanal", "mensal", "anual")


def cortes_quintis(valores: list) -> list:
    """Quatro cortes (20, 40, 60, 80%) da série habitual; recusa série curta ou valor negativo."""
    limpos = [float(v) for v in valores if v is not None]
    if len(limpos) < 5:
        raise ValueError("série habitual com menos de 5 valores: sem faixa")
    if any(v < 0 for v in limpos):
        raise ValueError("valor negativo na série habitual")
    return statistics.quantiles(limpos, n=5, method="inclusive")


def classificar(valor, cortes: list):
    """Posição do valor na faixa habitual; None para ausência de dado (nunca vira zero)."""
    if valor is None:
        return None
    for limite, rotulo in zip(cortes, ROTULOS_FAIXA):
        if valor <= limite:
            return rotulo
    return ROTULOS_FAIXA[-1]


def congelar(cortes: list, fonte: str, gerado_em: str, ler, gravar, caminho: str) -> bool:
    """Grava os cortes uma única vez. Devolve False se já havia parâmetro congelado (não sobrescreve)."""
    if ler(caminho) is not None:
        return False
    gravar(caminho, {"cortes": cortes, "periodo": [min(ANOS_HABITUAIS), max(ANOS_HABITUAIS)],
                     "fonte": fonte, "gerado_em": gerado_em})
    return True


def montar_desfecho(id_: str, serie_por_uf: dict, cortes: list, fonte: str, cadencia: str,
                    preliminar: bool, parcial: bool) -> dict:
    """Monta o registro; recusa cadência fora da lista e série com período fora de ordem."""
    if cadencia not in CADENCIAS:
        raise ValueError(f"cadência desconhecida: {cadencia}")
    por_uf = {}
    for uf, pontos in serie_por_uf.items():
        periodos = [p for p, _ in pontos]
        if periodos != sorted(periodos):
            raise ValueError(f"período fora de ordem em {uf}")
        com_dado = [(p, v) for p, v in pontos if v is not None]
        ultimo = {"periodo": com_dado[-1][0], "valor": com_dado[-1][1]} if com_dado else None
        por_uf[uf] = {"serie": [[p, v] for p, v in pontos], "ultimo": ultimo}
    return {"id": id_, "fonte": fonte, "cadencia": cadencia, "preliminar": preliminar,
            "parcial": parcial, "cortes": cortes, "por_uf": por_uf}


def _autoteste() -> None:
    cortes = cortes_quintis([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    assert cortes == sorted(cortes) and len(cortes) == 4
    assert classificar(None, cortes) is None            # ausência não vira zero
    assert classificar(0, cortes) == ROTULOS_FAIXA[0]   # zero real continua zero
    assert classificar(100, cortes) == ROTULOS_FAIXA[-1]
    try:
        cortes_quintis([1, 2])
        raise AssertionError("série curta devia recusar")
    except ValueError:
        pass
    escritos = {}

    def ler(c):
        return escritos.get(c)

    def gravar(c, d):
        escritos[c] = d

    assert congelar(cortes, "fonte", "2026-10-25", ler, gravar, "p.json") is True
    assert congelar([9, 9, 9, 9], "outra", "2026-10-26", ler, gravar, "p.json") is False  # write-once
    assert escritos["p.json"]["cortes"] == cortes
    d = montar_desfecho("lepto", {"MG": [("2026-01", 3), ("2026-02", None)]}, cortes,
                        "SINAN", "mensal", preliminar=True, parcial=False)
    assert d["por_uf"]["MG"]["ultimo"] == {"periodo": "2026-01", "valor": 3}
    try:
        montar_desfecho("x", {"MG": [("2026-02", 1), ("2026-01", 1)]}, cortes, "f", "mensal", False, False)
        raise AssertionError("período fora de ordem devia recusar")
    except ValueError:
        pass
    print("autoteste ok")


if __name__ == "__main__":
    if "--autoteste" in sys.argv:
        _autoteste()
