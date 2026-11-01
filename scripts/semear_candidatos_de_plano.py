#!/usr/bin/env python3
"""
scripts/semear_candidatos_de_plano.py — candidatos das sondas entram na fila pela porta única
=============================================================================================
Recria o adaptador do #1177 (perdido na consolidação). Uma sonda de busca (`dados/planos_busca/`
no privado) acha endereços de documento por município; este script passa cada um por
`pistas.gravar_lote`, que normaliza, recusa com motivo e segue ao juiz. Endereço de busca não vira
documento nem pontua: só o juiz, lendo o documento, dá crédito.

Entrada: JSON com `entradas` (sonda por município: `municipio`, `status` = documento_oficial, `url`,
`tipo`) ou `sondas` (sonda por capital: `capital`, `url`, `titulo`), mais `uf` e `data` no topo ou
em cada item. O IBGE vem da referência (`data/municipios_ibge_referencia.json`) por UF + nome; sem
IBGE o candidato é contado como `sem_ibge` e não entra (alvo por UF faria a pista do município
virar pista do estado). Nada de URL montada: só a que a sonda trouxe.

USO
    python3 scripts/semear_candidatos_de_plano.py --entrada <json> [--uf RS] [--simular]
    python3 scripts/semear_candidatos_de_plano.py --autoteste
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))

from pistas import _sem_acento, gravar_lote  # noqa: E402

ORIGEM = "busca_web"


def _referencia() -> dict:
    lista = json.loads((RAIZ / "data" / "municipios_ibge_referencia.json").read_text(encoding="utf-8"))
    return {(m["uf"], _sem_acento(m["nome"]).lower()): str(m["codigo_ibge"]) for m in lista}


def candidatos(doc: dict, referencia: dict, uf: str = "") -> tuple:
    """(pistas, sem_ibge): os candidatos da sonda como pistas brutas, sem IBGE contados à parte. Pura."""
    itens = [i for i in doc.get("entradas") or [] if i.get("status") == "documento_oficial"]
    itens += doc.get("sondas") or []
    pistas, sem_ibge = [], 0
    for i in itens:
        nome, sigla = i.get("municipio") or i.get("capital") or "", (i.get("uf") or doc.get("uf") or "").upper()
        ibge = referencia.get((sigla, _sem_acento(nome).lower()))
        if not i.get("url") or not ibge or (uf and sigla != uf.upper()):
            sem_ibge += bool(i.get("url") and not ibge)
            continue
        pistas.append({"municipio": nome, "uf": sigla, "ibge": ibge, "url": i["url"], "nivel_confianca": "C",
                       "titulo": i.get("titulo") or i.get("tipo") or "", "data": i.get("data") or doc.get("data") or ""})
    return pistas, sem_ibge


def semear(doc: dict, uf: str = "", simular: bool = False, **portas) -> dict:
    pistas, sem_ibge = candidatos(doc, _referencia(), uf)
    if simular:
        return {"candidatos": len(pistas), "sem_ibge": sem_ibge, "simulado": True}
    return {"candidatos": len(pistas), "sem_ibge": sem_ibge, **gravar_lote(pistas, ORIGEM, **portas)}


def _autoteste() -> int:
    from _casos import ok_de
    falhas, contados = [], []
    ok = ok_de(falhas, contados)
    ref = {("RS", "ijui"): "4310207", ("CE", "fortaleza"): "2304400"}
    doc = {"uf": "RS", "data": "2026-10-31", "entradas": [
        {"municipio": "Ijuí", "status": "documento_oficial", "url": "https://www.ijui.rs.gov.br/plano.pdf", "tipo": "plano de contingência"},
        {"municipio": "Agudo", "status": "sem_resultado", "tipo": "nada"},
        {"municipio": "Lugar Sem Código", "status": "documento_oficial", "url": "https://x.rs.gov.br/a.pdf"}]}
    p, sem = candidatos(doc, ref)
    ok("só documento_oficial com IBGE vira pista", [x["ibge"] for x in p] == ["4310207"])
    ok("candidato sem IBGE é contado, não gravado", sem == 1)
    ok("o título cai para o tipo e a data para a da sonda", p[0]["titulo"] == "plano de contingência" and p[0]["data"] == "2026-10-31")
    n, _ = candidatos({"sondas": [{"capital": "Fortaleza", "uf": "CE", "url": "https://a.ce.gov.br/p.pdf", "titulo": "Plano", "data": "2026-10-24"}]}, ref)
    ok("sonda por capital entra com a própria data", n and n[0]["ibge"] == "2304400" and n[0]["data"] == "2026-10-24")
    ok("filtro de UF descarta as outras", candidatos(doc, ref, "CE")[0] == [])
    fila = {}
    r = gravar_lote(p, ORIGEM, ler_fn=lambda nome: fila.get(nome), gravar_fn=lambda nome, d: fila.__setitem__(nome, d))
    ok("a porta recebe o lote sem tocar em data/ (portas injetadas)", r["gravadas"] + r["recusadas"] == 1 and "pistas_imprensa.json" in fila)
    print(("✗ AUTOTESTE: %d falha(s)" % len(falhas)) if falhas else f"✓ AUTOTESTE OK — {len(contados)} casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[1])
    ap.add_argument("--entrada")
    ap.add_argument("--uf", default="")
    ap.add_argument("--simular", action="store_true")
    ap.add_argument("--autoteste", action="store_true")
    a = ap.parse_args()
    if a.autoteste:
        return _autoteste()
    if not a.entrada:
        ap.error("--entrada é obrigatório")
    print(json.dumps(semear(json.loads(pathlib.Path(a.entrada).read_text(encoding="utf-8")), a.uf, a.simular),
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
