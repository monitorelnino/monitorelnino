#!/usr/bin/env python3
"""O conjunto prioritário de municípios: a união das três listas federais de risco.

Item B do handover da corrente noturna (03/10/2026). **A prioridade é de ORDEM DE COLETA**: ela não
muda pontuação, nem critério, nem categoria — município fora das listas continua sendo buscado, só
depois. Está dito assim na METODOLOGIA e repetido aqui porque é a confusão que esta regra pode
causar: prioridade de fila lida como peso no índice.

As três listas, já coletadas e versionadas:

    cadastro de municípios suscetíveis a enxurradas e inundações  Casa Civil, NT 2/2025
    delimitação do Semiárido                                       Sudene, Res. Condel 176/2024
    prioritários do controle do desmatamento e do fogo             MMA, portaria vigente

Saída: `data/prioridade_municipios.json` — código IBGE, nome, UF e as listas a que pertence.
Regerado a cada atualização das listas (entra na cadeia de derivados).

USO
    python3 scripts/gerar_prioridade_municipios.py
    python3 scripts/gerar_prioridade_municipios.py --autoteste
"""
from __future__ import annotations

import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

GOV = ("Conjunto PRIORITÁRIO de municípios para a ORDEM DE COLETA (item B do handover de "
       "03/10/2026): união das três listas federais de risco já coletadas. Não muda pontuação, "
       "critério nem categoria — é ordem de fila. Município fora das listas continua sendo "
       "buscado, depois dos prioritários. Derivado: nasce de cadastro_prioritarios_federal.json e "
       "enquadramento_card.json; não se edita à mão.")


def montar(cadastro: dict, card: dict, referencia: list) -> dict:
    """{ibge: {nome, uf, listas}} com a união das três listas. Função pura.

    `cadastro` é o da Casa Civil (nominal, por código); `card` é o derivado do enquadramento, que
    marca `sa` (Semiárido) e `mma` (prioritários do fogo). Nome e UF vêm da referência do IBGE —
    uma fonte só para o nome, como no resto do projeto.
    """
    por_codigo = {}
    for m in referencia or []:
        por_codigo[str(m["codigo_ibge"]).zfill(7)] = {"nome": m["nome"], "uf": str(m["uf"]).upper()}
    fora = {}

    def marcar(cod, lista):
        cod = str(cod).zfill(7)
        base = por_codigo.get(cod)
        if not base:
            return
        alvo = fora.setdefault(cod, {"nome": base["nome"], "uf": base["uf"], "listas": []})
        if lista not in alvo["listas"]:
            alvo["listas"].append(lista)

    for cod in ((cadastro or {}).get("municipios") or {}):
        marcar(cod, "enxurradas_e_inundacoes")
    for cod, marcas in ((card or {}).get("municipios") or {}).items():
        if marcas.get("sa"):
            marcar(cod, "semiarido")
        if marcas.get("mma"):
            marcar(cod, "fogo")
    return dict(sorted(fora.items()))


def _autoteste() -> int:
    falhas = []

    def ok(nome, cond):
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    REF = [{"nome": "Taió", "uf": "SC", "codigo_ibge": 4217808},
           {"nome": "Petrolina", "uf": "PE", "codigo_ibge": 2611101},
           {"nome": "Altamira", "uf": "PA", "codigo_ibge": 1500602}]
    cad = {"municipios": {"4217808": {}}}
    card = {"municipios": {"2611101": {"sa": True}, "1500602": {"mma": True},
                           "4217808": {"sa": True}}}
    r = montar(cad, card, REF)
    ok("as três listas entram na união", set(r) == {"4217808", "2611101", "1500602"})
    ok("município em duas listas traz as duas",
       sorted(r["4217808"]["listas"]) == ["enxurradas_e_inundacoes", "semiarido"])
    ok("nome e UF vêm da referência do IBGE",
       r["2611101"]["nome"] == "Petrolina" and r["2611101"]["uf"] == "PE")
    ok("código fora da referência não entra",
       montar({"municipios": {"9999999": {}}}, {}, REF) == {})
    ok("marca falsa não conta", montar({}, {"municipios": {"2611101": {"sa": False}}}, REF) == {})
    ok("saída ordenada por código", list(montar(cad, card, REF)) == sorted(montar(cad, card, REF)))
    ok("sem listas, conjunto vazio", montar({}, {}, REF) == {})
    ok("a governança diz que é ordem, não peso",
       "Não muda pontuação" in GOV and "ordem de fila" in GOV)

    import dis
    nomes = set()
    for nome_obj, obj in list(globals().items()):
        if nome_obj in ("_autoteste", "main"):
            continue
        codigo = getattr(obj, "__code__", None)
        if codigo is not None:
            nomes |= {i.argval for i in dis.get_instructions(codigo) if isinstance(i.argval, str)}
    ok("trava estrutural: `montar` não escreve",
       not ({"gravar", "gravar_em", "write_text"} & nomes))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else "✓ AUTOTESTE OK — 9 casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return _autoteste()
    from coletores_base import gravar, ler, hoje_editorial
    municipios = montar(ler("cadastro_prioritarios_federal.json") or {},
                        ler("enquadramento_card.json") or {},
                        ler("municipios_ibge_referencia.json") or [])
    por_lista = {}
    for v in municipios.values():
        for l in v["listas"]:
            por_lista[l] = por_lista.get(l, 0) + 1
    gravar("prioridade_municipios.json", {
        "_governanca": GOV,
        "gerado_em": hoje_editorial().strftime("%d/%m/%Y"),
        "total": len(municipios),
        "por_lista": por_lista,
        "municipios": municipios,
    })
    print(f"→ data/prioridade_municipios.json: {len(municipios)} município(s) prioritário(s) "
          f"· {por_lista}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
