#!/usr/bin/env python3
"""Portão: a capital tem UMA fonte, e ela é o banco.

Item 1.10 do HANDOVER_CORRECAO_DEFINITIVA_08-10-2026 (achados A3-11 e A4-03). `data/estados.json`
guardava, em `capital`, um `status` e um `info` escritos à mão, e `data/municipios.json` guardava a
categoria que pontua. As duas se contradiziam em **nove UFs**, e o leitor via no mesmo clique
"Novo, base da pontuação" e "ainda não verificado" — Rio Branco, Macapá, Belém, Brasília, Campo
Grande, Belo Horizonte, Curitiba, Porto Alegre e Florianópolis.

A régua: `capital` guarda **só o nome**. O estado e a frase da capital saem do registro do banco,
pela mesma função do cartão do município (`textoDaCapital` em `assets/js/index.js`). Dado que
pontua tem um dono, e texto editorial sobre dado que pontua é uma segunda fonte disfarçada.

`--autoteste` é puro: não lê `data/`, não escreve nada.
"""
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
ESTADOS = RAIZ / "data" / "estados.json"
MUNICIPIOS = RAIZ / "data" / "municipios.json"
JS = RAIZ / "assets" / "js" / "index.js"
PERMITIDO = {"nome"}


def problemas(ufs, categorias, fonte_js="") -> list:
    fora = []
    for x in ufs:
        c = x.get("capital")
        uf = x.get("uf")
        if not c:
            continue
        sobrando = sorted(set(c) - PERMITIDO)
        if sobrando:
            fora.append(f"{uf}: `capital` guarda {', '.join(sobrando)} — a capital tem uma fonte "
                        f"só, o banco; campo de texto aqui é segunda fonte (A3-11)")
        if not str(c.get("nome") or "").strip():
            fora.append(f"{uf}: `capital` sem nome")
            continue
        if (uf, c["nome"]) not in categorias:
            fora.append(f"{uf}: a capital {c['nome']} não tem registro em municipios.json — sem "
                        f"registro não há o que publicar sobre ela")
    if fonte_js:
        for proibido in ("d.capital.status", "d.capital.info"):
            if proibido in fonte_js:
                fora.append(f"assets/js/index.js ainda lê {proibido}; o estado da capital sai do "
                            f"banco (textoDaCapital)")
    return fora


def autoteste() -> int:
    cats = {("AC", "Rio Branco"): "nao_verificado", ("PR", "Curitiba"): "estrutura"}
    casos = [
        ("capital só com nome passa",
         [{"uf": "AC", "capital": {"nome": "Rio Branco"}}], cats, "", 0),
        ("capital com status reprova",
         [{"uf": "AC", "capital": {"nome": "Rio Branco", "status": "Novo"}}], cats, "", 1),
        ("capital com info reprova",
         [{"uf": "PR", "capital": {"nome": "Curitiba", "info": "caso mais avançado"}}], cats,
         "", 1),
        ("capital sem registro no banco reprova",
         [{"uf": "SP", "capital": {"nome": "São Paulo"}}], cats, "", 1),
        ("UF sem capital é ignorada", [{"uf": "DF"}], cats, "", 0),
        ("JS que lê o status reprova",
         [{"uf": "AC", "capital": {"nome": "Rio Branco"}}], cats,
         "item('Capital: ' + d.capital.status)", 1),
        ("JS que lê o banco passa",
         [{"uf": "AC", "capital": {"nome": "Rio Branco"}}], cats,
         "item(textoDaCapital(regCap))", 0),
    ]
    falhas = 0
    for nome, ufs, cs, js, esperado in casos:
        achados = problemas(ufs, cs, js)
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
    estados = json.loads(ESTADOS.read_text(encoding="utf-8"))
    doc = json.loads(MUNICIPIOS.read_text(encoding="utf-8"))
    bruto = doc["municipios"] if isinstance(doc, dict) else doc
    itens = list(bruto.values()) if isinstance(bruto, dict) else bruto
    categorias = {(m["uf"], m["nome"]): m.get("categoria") for m in itens}
    fora = problemas(estados["ufs"], categorias, JS.read_text(encoding="utf-8"))
    if fora:
        print(f"VERMELHO: {len(fora)} problema(s) na capital")
        for f in fora[:40]:
            print(f"  · {f}")
        return 1
    n = sum(1 for x in estados["ufs"] if x.get("capital"))
    print(f"ok: {n} capitais com uma fonte só — o registro do banco")
    return 0


if __name__ == "__main__":
    sys.exit(main())
