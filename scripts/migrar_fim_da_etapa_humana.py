#!/usr/bin/env python3
"""migrar_fim_da_etapa_humana.py — migração única do lote 2.9 (09/10/2026, A1-17).

O texto de status que dizia "lido por humano" e o `status_triagem` "pendente_julgamento_humano"
passam ao texto da regra automática. Nada sai da fila e nenhuma decisão muda: as 148 pistas
continuam pendentes do juiz (já estavam em back-off técnico dele) e os 97 decretos continuam na
conferência — muda o nome do estado, que dizia esperar por uma pessoa que não existe.
Idempotente: rodar de novo não muda nada.

USO
    python3 scripts/migrar_fim_da_etapa_humana.py --autoteste
    python3 scripts/migrar_fim_da_etapa_humana.py --aplicar
"""
from __future__ import annotations

import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

TROCAS = (("promover a registro exige documento primário lido por humano",
           "na fila, aguardando busca dirigida e juiz"),)
TRIAGEM = {"pendente_julgamento_humano": "pendente_julgamento"}


def migrar_item(p: dict) -> bool:
    """Troca o texto no próprio item. True se mudou. Função pura sobre o dict."""
    mudou = False
    st = p.get("status")
    if isinstance(st, str):
        novo = st
        for velho, bom in TROCAS:
            novo = novo.replace(velho, bom)
        if novo != st:
            p["status"] = novo
            mudou = True
    t = p.get("status_triagem")
    if t in TRIAGEM:
        p["status_triagem"] = TRIAGEM[t]
        mudou = True
    return mudou


def autoteste() -> int:
    a = {"status": "pista — promover a registro exige documento primário lido por humano"}
    b = {"status": "pista — atribuição de município por proximidade no PDF consorciado; "
                   "promover a registro exige documento primário lido por humano"}
    c = {"status_triagem": "pendente_julgamento_humano"}
    d = {"status": "aplicada"}
    ok = (migrar_item(a) and a["status"] == "pista — na fila, aguardando busca dirigida e juiz"
          and migrar_item(b) and b["status"].endswith("na fila, aguardando busca dirigida e juiz")
          and migrar_item(c) and c["status_triagem"] == "pendente_julgamento"
          and not migrar_item(d) and not migrar_item(a))
    print("OK AUTOTESTE — 5 casos, sem escrita." if ok else "X AUTOTESTE falhou")
    return 0 if ok else 1


def main() -> int:
    from coletores_base import gravar_em
    total = 0
    for arq, chave in (("data/pistas_imprensa.json", "pistas"),
                       ("data/decretos_conteudo_revisar.json", "fila")):
        caminho = RAIZ / arq
        doc = json.loads(caminho.read_text(encoding="utf-8"))
        n = sum(1 for p in doc.get(chave) or [] if isinstance(p, dict) and migrar_item(p))
        if n and "--aplicar" in sys.argv:
            gravar_em(caminho, doc)
        print(f"{arq}: {n} item(ns) {'migrado(s)' if '--aplicar' in sys.argv else 'a migrar'}")
        total += n
    return 0


if __name__ == "__main__":
    sys.exit(autoteste() if "--autoteste" in sys.argv else main())
