#!/usr/bin/env python3
"""Portão: nada pontua sem documento lido e preservado (D1).

Item 1.11 do HANDOVER_CORRECAO_DEFINITIVA_08-10-2026 (achados A4-05 e A4-09, decisão D1). Em
08/10/2026 havia **47 registros pontuando sem documento**: 41 sem endereço nenhum e 6 com notícia
no lugar do documento — 24 `plano`, 11 `plano_antigo` e 12 `plano_elaboracao`. A metodologia exige
documento primário; "nomeado" não é "localizado", e zero inventado é pior que zero medido.

A régua: categoria que recebe crédito (`plano`, `plano_antigo`, `plano_elaboracao`, `plano_novo`,
`plano_readaptado`, `plano_recorrente`, `estrutura`) exige `url` de documento **e**
`hash_evidencia`. Endereço de notícia, de sala de imprensa ou raiz de portal não é documento. Quem
não tem passa a `plano_nomeado`, crédito 0, até a busca dirigida anexar o documento.

`--autoteste` é puro: não lê `data/`, não escreve nada.
"""
import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
ARQUIVO = RAIZ / "data" / "municipios.json"

PONTUAM = ("plano", "plano_antigo", "plano_elaboracao", "plano_novo", "plano_readaptado",
           "plano_recorrente", "estrutura")
RE_NOTICIA = re.compile(r"/notici|/imprensa|/news|/sala-de-imprensa|/blog", re.I)
RE_RAIZ = re.compile(r"^https?://[^/]+/?$")


def problemas(municipios) -> list:
    fora = []
    for m in municipios:
        cat = m.get("categoria")
        etiqueta = f"{m.get('nome')}/{m.get('uf')}"
        if cat == "plano_nomeado":
            if not str(m.get("por_que_nomeado") or "").strip():
                fora.append(f"{etiqueta}: plano_nomeado sem `por_que_nomeado` — a razão da "
                            f"ausência do documento se declara, não se presume")
            continue
        if cat not in PONTUAM:
            continue
        url = str(m.get("url") or "")
        if not url:
            fora.append(f"{etiqueta}: {cat} sem endereço de documento (D1); use plano_nomeado")
            continue
        if RE_NOTICIA.search(url):
            fora.append(f"{etiqueta}: {cat} com endereço de notícia, não de documento ({url})")
        elif RE_RAIZ.match(url):
            fora.append(f"{etiqueta}: {cat} com raiz de portal no lugar do documento ({url})")
        if not str(m.get("hash_evidencia") or "").strip():
            fora.append(f"{etiqueta}: {cat} sem `hash_evidencia` — documento que pontua fica "
                        f"preservado e conferível")
    return fora


def autoteste() -> int:
    bom = {"nome": "Linhares", "uf": "ES", "categoria": "plano",
           "url": "https://linhares.es.gov.br/wp-content/plancon-2025.pdf",
           "hash_evidencia": "a" * 64, "fonte": "Prefeitura de Linhares"}
    casos = [
        ("plano com documento e hash passa", [bom], 0),
        ("plano sem url reprova", [{k: v for k, v in bom.items() if k != "url"}], 1),
        ("plano com url de notícia reprova",
         [{**bom, "url": "https://x.es.gov.br/noticias/plano-apresentado"}], 1),
        ("plano com raiz de portal reprova", [{**bom, "url": "https://x.es.gov.br/"}], 1),
        ("plano sem hash reprova", [{k: v for k, v in bom.items() if k != "hash_evidencia"}], 1),
        ("plano_nomeado com razão declarada passa",
         [{"nome": "Maruim", "uf": "SE", "categoria": "plano_nomeado",
           "por_que_nomeado": "D1: sem endereço de documento"}], 0),
        ("plano_nomeado sem razão reprova",
         [{"nome": "Maruim", "uf": "SE", "categoria": "plano_nomeado"}], 1),
        ("nao_localizado é ignorado", [{"nome": "X", "uf": "BA", "categoria": "nao_localizado"}], 0),
        ("decreto é ignorado (não pontua no índice)",
         [{"nome": "Y", "uf": "BA", "categoria": "decreto"}], 0),
    ]
    falhas = 0
    for nome, mun, esperado in casos:
        achados = problemas(mun)
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
    bruto = doc["municipios"] if isinstance(doc, dict) else doc
    municipios = list(bruto.values()) if isinstance(bruto, dict) else bruto
    fora = problemas(municipios)
    if fora:
        print(f"VERMELHO: {len(fora)} registro(s) pontuando sem documento lido (D1)")
        for f in fora[:40]:
            print(f"  · {f}")
        if len(fora) > 40:
            print(f"  … e outros {len(fora) - 40}")
        return 1
    n = sum(1 for m in municipios if m.get("categoria") in PONTUAM)
    nom = sum(1 for m in municipios if m.get("categoria") == "plano_nomeado")
    print(f"ok: {n} registros com crédito têm documento e evidência; {nom} em plano_nomeado")
    return 0


if __name__ == "__main__":
    sys.exit(main())
