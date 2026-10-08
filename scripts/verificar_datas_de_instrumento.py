#!/usr/bin/env python3
"""Portão: a data do instrumento é a do DOCUMENTO, nunca a da consulta.

Item 1.9 do HANDOVER_CORRECAO_DEFINITIVA_08-10-2026 (A3-09, A3-30). `atualizar_instrumentos_
estaduais.py` gravava `data: hoje` — o dia em que o Monitor abriu o repositório estadual — e a
ficha publicava aquilo como se fosse a data do plano. Em 08/10/2026 havia **83 registros** de ES e
SE com `data: 26/08/2026`, e **nove deles são `plano_antigo`**: um plano antigo carimbado com data
deste ano é contradição publicada, e o leitor não tem como saber qual das duas coisas é verdade.

A régua que este portão cobra:

- `plano_antigo` com ano de `data` ≥ `ANO_LIMIAR_VIGENTE` reprova — a categoria diz "antigo" e a
  data diz "deste ano";
- `plano` com ano de `data` < `ANO_LIMIAR_VIGENTE` reprova — o inverso, pelo mesmo motivo;
- registro de repositório estadual precisa de `localizado_em` (a data da consulta tem campo
  próprio) e o ano de `data` tem de aparecer em `documento`, que é de onde ele sai.

`--autoteste` é puro: fixtures de ES e SE no próprio arquivo, sem ler `data/` e sem escrever nada.
"""
import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
ARQUIVO = RAIZ / "data" / "municipios.json"
ANO_LIMIAR_VIGENTE = 2024  # a mesma régua de `atualizar_instrumentos_estaduais.categoria_por_ano`
CANAL = "repositorio_estadual"
RE_ANO = re.compile(r"(19|20)\d{2}")


def ano_de(valor) -> "int | None":
    """O ano de 'AAAA', 'dd/mm/aaaa' ou '2025-2026' (o último do intervalo: a edição em vigor)."""
    anos = [int(m.group(0)) for m in RE_ANO.finditer(str(valor or ""))]
    return anos[-1] if anos else None


def problemas(municipios) -> list:
    fora = []
    for m in municipios:
        if m.get("canal") != CANAL:
            continue
        etiqueta = f"{m.get('nome')}/{m.get('uf')}"
        cat = m.get("categoria")
        ano = ano_de(m.get("data"))
        if ano is None:
            fora.append(f"{etiqueta}: data sem ano reconhecível ({m.get('data')!r})")
            continue
        if cat == "plano_antigo" and ano >= ANO_LIMIAR_VIGENTE:
            fora.append(f"{etiqueta}: plano_antigo com data de {ano} — a categoria diz antigo e a "
                        f"data diz deste ciclo")
        if cat == "plano" and ano < ANO_LIMIAR_VIGENTE:
            fora.append(f"{etiqueta}: plano (vigente) com data de {ano}, anterior ao limiar "
                        f"{ANO_LIMIAR_VIGENTE}")
        if not m.get("localizado_em"):
            fora.append(f"{etiqueta}: sem `localizado_em` — a data da consulta tem campo próprio")
        doc = str(m.get("documento") or "")
        if str(ano) not in doc:
            fora.append(f"{etiqueta}: o ano da data ({ano}) não aparece em `documento` ({doc!r}); "
                        f"a data do instrumento sai do documento, não do relógio")
    return fora


def autoteste() -> int:
    # Fixtures reais reduzidos: ES publica PLANCON por edição anual; SE publica edição 2026 e
    # mantém no mesmo repositório planos de 2018 e 2019 (A3-30).
    es_bom = {"nome": "Linhares", "uf": "ES", "categoria": "plano", "canal": CANAL,
              "documento": "PLANCON edição 2025 (repositório estadual)", "data": "2025",
              "localizado_em": "26/08/2026"}
    se_antigo = {"nome": "Poço Redondo", "uf": "SE", "categoria": "plano_antigo", "canal": CANAL,
                 "documento": "PLANCON edição 2019 (repositório estadual)", "data": "2019",
                 "localizado_em": "26/08/2026"}
    casos = [
        ("ES vigente com ano da edição passa", [es_bom], 0),
        ("SE antigo com ano da edição passa", [se_antigo], 0),
        ("intervalo 2025-2026 passa",
         [{**es_bom, "data": "2025-2026",
           "documento": "PLANCON edição 2025-2026 (repositório estadual)"}], 0),
        ("data da consulta no lugar da data do documento reprova",
         [{**es_bom, "data": "26/08/2026"}], 1),
        ("plano_antigo com data de 2026 reprova",
         [{**se_antigo, "data": "2026", "documento": "PLANCON edição 2026 (repositório estadual)"}],
         1),
        ("plano vigente com data de 2019 reprova",
         [{**es_bom, "data": "2019", "documento": "PLANCON edição 2019 (repositório estadual)"}],
         1),
        ("sem localizado_em reprova",
         [{k: v for k, v in es_bom.items() if k != "localizado_em"}], 1),
        ("data sem ano reprova", [{**es_bom, "data": "sem data"}], 1),
        ("edição antiga com atualização recente passa pela data da atualização",
         [{**es_bom, "categoria": "plano", "data": "2025",
           "documento": "PLANCON ed. 2023, atualizado 31/01/2025 (repositório estadual)"}], 0),
        ("outro canal é ignorado",
         [{**es_bom, "canal": "DOM", "data": "26/08/2026"}], 0),
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
        print(f"VERMELHO: {len(fora)} problema(s) de data de instrumento em data/municipios.json")
        for f in fora[:40]:
            print(f"  · {f}")
        if len(fora) > 40:
            print(f"  … e outros {len(fora) - 40}")
        return 1
    n = sum(1 for m in municipios if m.get("canal") == CANAL)
    print(f"ok: {n} registros de repositório estadual com a data do documento e a da consulta "
          f"em campos separados")
    return 0


if __name__ == "__main__":
    sys.exit(main())
