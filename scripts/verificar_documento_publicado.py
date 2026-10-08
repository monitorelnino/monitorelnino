#!/usr/bin/env python3
"""Portão: o campo `documento` da ficha é o título do documento, não sobra de página.

Item 1.12 do HANDOVER_CORRECAO_DEFINITIVA_08-10-2026 (achados A1-06 e A4-08). O campo vinha do
trecho do objeto julgado, e no caminho do "plano publicado em domínio oficial" não existe objeto:
o trecho era o que estivesse na página. A ficha publicou, para o leitor:

- "o documento É o instrumento nomeado: tanhaém Secretaria Municipal…" (Itanhaém/SP) — frase
  interna do juiz e o nome do município sem a primeira letra;
- "neste Plano. 11/08/2026 Página 3 de 72 Plano de contingência…" (Umuarama/PR e Leme/SP);
- "a Católica 8 1.5. INSTRUÇÕES PARA USO E ATUALIZAÇÃO DO PLANO…" (Celso Ramos/SC).

O que reprova: marcador de paginação, frase interna do juiz, reticências de corte ("……", "...."),
e `documento` começando em minúscula — título de documento não começa em minúscula.

`--autoteste` é puro: não lê `data/`, não escreve nada.
"""
import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
ARQUIVO = RAIZ / "data" / "municipios.json"

PROIBIDOS = (
    (re.compile(r"P[áa]gina\s+\d+\s+de\s+\d+", re.I), "marcador de paginação do PDF"),
    (re.compile(r"o documento [ÉE] o instrumento", re.I), "frase interna do juiz"),
    (re.compile(r"……|\.\.\.\."), "reticências de corte de trecho"),
    (re.compile(r"Estado das fontes|em verifica[çc][ãa]o|em classifica[çc][ãa]o", re.I),
     "texto interno de painel"),
)


def problemas(municipios) -> list:
    fora = []
    for m in municipios:
        doc = str(m.get("documento") or "").strip()
        if not doc:
            continue
        etiqueta = f"{m.get('nome')}/{m.get('uf')}"
        for regex, por_que in PROIBIDOS:
            achado = regex.search(doc)
            if achado:
                fora.append(f"{etiqueta}: `documento` traz {por_que} ({achado.group(0)!r})")
        if doc[:1].islower():
            fora.append(f"{etiqueta}: `documento` começa em minúscula ({doc[:40]!r}) — título de "
                        f"documento não começa em minúscula")
    return fora


def autoteste() -> int:
    bom = {"nome": "Serra", "uf": "ES",
           "documento": "Fica instituído o Plano Municipal de Proteção e Defesa Civil"}
    casos = [
        ("ementa limpa passa", [bom], 0),
        ("título com órgão e ano passa",
         [{**bom, "documento": "PLANCON PLANO DE CONTIGÊNCIA 2024-2025 — Prefeitura de "
                               "Itanhaém, 2024"}], 0),
        ("marcador de página reprova",
         [{**bom, "documento": "neste Plano. 11/08/2026 Página 3 de 72 Plano de contingência"}],
         2),
        ("frase interna do juiz reprova",
         [{**bom, "documento": "o documento É o instrumento nomeado: tanhaém Secretaria"}], 2),
        ("minúscula inicial reprova",
         [{**bom, "documento": "a Católica 8 1.5. INSTRUÇÕES PARA USO"}], 1),
        ("reticências de corte reprovam",
         [{**bom, "documento": "Plano de contingência do município ……"}], 1),
        ("texto de painel reprova", [{**bom, "documento": "Estado das fontes"}], 1),
        ("documento ausente é ignorado", [{"nome": "X", "uf": "BA"}], 0),
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
        print(f"VERMELHO: {len(fora)} problema(s) no campo `documento` publicado")
        for f in fora[:40]:
            print(f"  · {f}")
        if len(fora) > 40:
            print(f"  … e outros {len(fora) - 40}")
        return 1
    n = sum(1 for m in municipios if str(m.get("documento") or "").strip())
    print(f"ok: {n} fichas com `documento` em forma de título")
    return 0


if __name__ == "__main__":
    sys.exit(main())
