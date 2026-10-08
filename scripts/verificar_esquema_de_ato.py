#!/usr/bin/env python3
"""Portão: `data/atos_resposta.json` dentro de `schemas/ato_resposta.json`.

Item 1.3 do HANDOVER_CORRECAO_DEFINITIVA_08-10-2026 (A3-08, A6-02, A6-21). O arquivo é a base do
contador de resposta, do mapa e do feed. Tinha 832 datas em dd/mm/aaaa e 97 em ISO: o diário
consorciado gravava `dia.isoformat()`. Quem compara string com string — a série semanal, o cartão,
o feed — nunca casa os dois formatos, e o erro é silencioso.

`--autoteste` é puro: não lê `data/`, não escreve nada.
"""
import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
ESQUEMA = RAIZ / "schemas" / "ato_resposta.json"
ARQUIVO = RAIZ / "data" / "atos_resposta.json"

RE_BR = re.compile(r"^\d{2}/\d{2}/\d{4}$")
RE_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def esquema() -> dict:
    return json.loads(ESQUEMA.read_text(encoding="utf-8"))


def problemas(eventos, esq, corte=None) -> list:
    obrig = list(esq["obrigatorios"])
    campos_de_data = list(esq["datas"]["campos"])
    fora = []
    for i, e in enumerate(eventos):
        etiqueta = f"evento {i} ({e.get('nome')}/{e.get('uf')} {e.get('decreto')})"
        for c in obrig:
            if str(e.get(c) or "").strip():
                continue
            # `url` vazia é legítima no único caso em que o ato é conhecido por fonte oficial e o
            # documento ainda não foi lido — os três eventos de MT do item 1.5, que já carregam
            # `documento_nao_localizado`. Fora dele, ato sem endereço não é conferível.
            if c == "url" and e.get("documento_nao_localizado"):
                continue
            fora.append(f"{etiqueta}: campo obrigatório ausente: {c}")
        for c in campos_de_data:
            v = e.get(c)
            if v is None or v == "":
                continue
            v = str(v)
            if RE_ISO.match(v):
                fora.append(f"{etiqueta}: {c} em ISO ({v}); o esquema exige dd/mm/aaaa")
            elif not RE_BR.match(v):
                fora.append(f"{etiqueta}: {c} fora de dd/mm/aaaa ({v})")
            elif corte:
                d, m, a = (int(x) for x in v.split("/"))
                if (a, m, d) > corte:
                    fora.append(f"{etiqueta}: {c} posterior ao corte ({v})")
        ibge = str(e.get("ibge") or "")
        if ibge and not re.fullmatch(r"\d{7}", ibge):
            fora.append(f"{etiqueta}: ibge fora de sete dígitos ({ibge})")
    return fora


def autoteste() -> int:
    esq = {"obrigatorios": {k: "" for k in ("nome", "uf", "data", "causa", "decreto", "fonte",
                                            "url", "canal")},
           "datas": {"campos": ["data", "data_ato", "data_publicacao"]}}
    bom = {"nome": "Piranhas", "uf": "AL", "data": "22/09/2026", "causa": "situação de emergência",
           "decreto": "Decreto nº 31", "fonte": "Diário consorciado", "url": "https://x/e.pdf",
           "canal": "DOM-consorciado", "ibge": "2707602", "data_publicacao": "23/09/2026"}
    casos = [
        ("evento completo passa", [bom], 0),
        ("data em ISO reprova", [{**bom, "data": "2026-09-22"}], 1),
        ("data_publicacao em ISO reprova", [{**bom, "data_publicacao": "2026-09-23"}], 1),
        ("data em texto reprova", [{**bom, "data": "22 de setembro"}], 1),
        ("campo obrigatório vazio reprova", [{**bom, "canal": ""}], 1),
        ("ibge curto reprova", [{**bom, "ibge": "27076"}], 1),
        ("ibge ausente passa", [{k: v for k, v in bom.items() if k != "ibge"}], 0),
        ("data futura reprova", [{**bom, "data": "31/12/2027"}], 1),
        ("url vazia reprova", [{**bom, "url": ""}], 1),
        ("url vazia passa com documento_nao_localizado",
         [{**bom, "url": "", "documento_nao_localizado": True}], 0),
    ]
    falhas = 0
    for nome, eventos, esperado in casos:
        achados = problemas(eventos, esq, corte=(2026, 10, 8))
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
    eventos = doc.get("eventos") or []
    sys.path.insert(0, str(RAIZ))
    from coletores_base import data_do_corte  # noqa: PLC0415
    c = data_do_corte()
    fora = problemas(eventos, esquema(), corte=(c.year, c.month, c.day))
    if fora:
        print(f"VERMELHO: {len(fora)} problema(s) de esquema em data/atos_resposta.json")
        for f in fora[:40]:
            print(f"  · {f}")
        if len(fora) > 40:
            print(f"  … e outros {len(fora) - 40}")
        return 1
    print(f"ok: {len(eventos)} eventos dentro de schemas/ato_resposta.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
