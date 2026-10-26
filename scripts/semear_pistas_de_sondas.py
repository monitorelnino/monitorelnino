#!/usr/bin/env python3
"""Candidatos das sondas de busca (matriz de planos S20, S21, S23, S31, N1) entram na fila de pistas.

A sonda de 24/10/2026 achou endereços por capital e não leu nenhum: pista só vale lida pelo juiz.
Aqui cada candidato vira pista pela porta única (`scripts.pistas.gravar_lote`), com as travas de
campo de `buscar_planos_fontes_abertas.pista_de` (nada confirmado, nada promovível). Repetida a fila
recusa sozinha. Entrada: `data/sondas_websearch_N1.json` (só leitura). Escreve só a fila, via porta.
Uso: python3 scripts/semear_pistas_de_sondas.py [--rodar] | --autoteste
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")
from buscar_planos_fontes_abertas import pista_de  # noqa: E402
from coletores_base import ler, gravar, hoje_editorial, referencia_ibge  # noqa: E402
from scripts.pistas import gravar_lote  # noqa: E402

ARQUIVO = "sondas_websearch_N1.json"
NOMES = {"S20": "Ministério Público", "S21": "Judiciário", "S23": "Saúde", "S31": "Transferegov"}


def pistas_das_sondas(doc: dict, por_nome: dict, hoje: str) -> tuple:
    pistas, sem_codigo = [], []
    for s in doc.get("sondas", []):
        cod = por_nome.get((s["capital"], s["uf"]))
        if not cod or not str(s.get("url", "")).startswith("http"):
            sem_codigo.append(s.get("capital"))
            continue
        pistas.append(pista_de(s["capital"], s["uf"], cod, NOMES.get(s["fonte"], s["fonte"]), s["url"],
                               s.get("titulo") or s["url"], hoje))
    return pistas, sem_codigo


def rodar(ler_fn=ler, gravar_fn=gravar) -> dict:
    _, por_nome = referencia_ibge()
    pistas, sem = pistas_das_sondas(ler_fn(ARQUIVO, {}) or {}, por_nome, hoje_editorial().isoformat())
    balanco = gravar_lote(pistas, origem="descoberta", ler_fn=ler_fn, gravar_fn=gravar_fn)
    print(f"Sondas: {len(pistas)} candidato(s); porta única: {balanco.get('gravadas')} gravada(s), "
          f"{balanco.get('recusadas')} recusada(s) {balanco.get('motivos') or ''}; sem município: {sem}")
    return balanco


def autoteste() -> int:
    doc = {"sondas": [{"fonte": "S23", "capital": "Manaus", "uf": "AM", "url": "https://x.gov.br/p.pdf", "titulo": "Plano"},
                      {"fonte": "S20", "capital": "Lugar", "uf": "ZZ", "url": "https://x.gov.br/q.pdf"},
                      {"fonte": "S20", "capital": "Manaus", "uf": "AM", "url": "nao-e-url"}]}
    pistas, sem = pistas_das_sondas(doc, {("Manaus", "AM"): "1302603"}, "2026-10-26")
    assert len(pistas) == 1 and sem == ["Lugar", "Manaus"], (pistas, sem)
    p = pistas[0]
    assert p["ibge"] == "1302603" and p["promovivel"] is False and p["documento_oficial_confirmado"] is None
    assert p["titulo"].startswith("Saúde · Manaus/AM") and p["url"] == "https://x.gov.br/p.pdf"
    print("autoteste ok: 4 verificações offline, nada escrito em data/")
    return 0


if __name__ == "__main__":
    if "--autoteste" in sys.argv:
        sys.exit(autoteste())
    if "--rodar" in sys.argv:
        sys.exit(0 if rodar() is not None else 1)
    print(__doc__)
