#!/usr/bin/env python3
"""verificar_fila_nao_humana.py — nenhuma fila espera por uma pessoa (lote 2.9, A1-17, A7-27).

Decisão de 08/10/2026: não há humano tomando decisões. O código julga sozinho, e fila que diz
"lido por humano", "julgamento humano" ou "revisão humana" é fila que nunca esvazia. Este portão
reprova duas coisas:

  1. status (ou `status_triagem`) que menciona humano/humana, em qualquer fila — BLOQUEIA sempre;
  2. pista em `pendente_confirmacao…` há mais de 21 dias (o `dias_de_vida` do esquema). O estoque
     de 09/10 (3.415 do Google News sem data de registro, drenado pelo lote 2.6 à razão de ~200
     por noite) tem prazo declarado: até PRAZO_DO_ESTOQUE o portão nomeia o passivo e passa;
     depois, reprova. Pista sem data legível conta no passivo, nunca como nova.

USO
    python3 scripts/verificar_fila_nao_humana.py --autoteste
    python3 scripts/verificar_fila_nao_humana.py
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import re
import sys
from email.utils import parsedate_to_datetime

RAIZ = pathlib.Path(__file__).resolve().parent.parent

FILAS = (("data/pistas_imprensa.json", "pistas"),
         ("data/pistas_imprensa_saude.json", "pistas"),
         ("data/pistas_descobertas.json", "itens"),
         ("data/pistas_doe.json", "itens"),
         ("data/pistas_querido_diario.json", "pistas"),
         ("data/saude_no_plano_revisar.json", "fila"),
         ("data/decretos_conteudo_revisar.json", "fila"))
DIAS_DE_VIDA = 21
PRAZO_DO_ESTOQUE = "2026-11-15"
RE_HUMANO = re.compile(r"(?<![a-z])human[oa]s?(?![a-z])", re.I)


def data_da_pista(p: dict):
    """A data mais confiável de entrada na fila, ou None. Função pura."""
    for campo in ("registrado_em", "descoberto_em", "data_publicacao", "data"):
        bruto = str(p.get(campo) or "").strip()
        if not bruto:
            continue
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", bruto)
        if m:
            return dt.date(int(m[1]), int(m[2]), int(m[3]))
        m = re.match(r"(\d{2})/(\d{2})/(\d{4})", bruto)
        if m:
            return dt.date(int(m[3]), int(m[2]), int(m[1]))
        try:
            return parsedate_to_datetime(bruto).date()
        except Exception:  # noqa: BLE001
            continue
    return None


def avaliar(filas: dict, hoje: dt.date) -> tuple:
    """(falhas, passivo). `filas` = {nome: [itens]}. Função pura."""
    falhas, passivo = [], 0
    vence = hoje.isoformat() > PRAZO_DO_ESTOQUE
    for nome, itens in filas.items():
        for p in itens or []:
            if not isinstance(p, dict):
                continue
            for campo in ("status", "status_triagem"):
                v = str(p.get(campo) or "")
                if RE_HUMANO.search(v):
                    falhas.append(f"{nome}: {campo} espera por pessoa — {v[:90]!r}")
            if str(p.get("status") or "").startswith("pendente_confirmacao"):
                d = data_da_pista(p)
                velha = d is None or (hoje - d).days > DIAS_DE_VIDA
                if velha:
                    if vence:
                        falhas.append(f"{nome}: pendente há mais de {DIAS_DE_VIDA} dias "
                                      f"({d or 'sem data'}) — {str(p.get('titulo') or p.get('url'))[:70]!r}")
                    else:
                        passivo += 1
    return falhas, passivo


def autoteste() -> int:
    hoje = dt.date(2026, 10, 9)
    depois = dt.date(2026, 11, 20)
    casos = [
        ("status com 'lido por humano' reprova",
         len(avaliar({"f": [{"status": "pista — exige documento primário lido por humano"}]}, hoje)[0]) == 1),
        ("status_triagem 'pendente_julgamento_humano' reprova",
         len(avaliar({"f": [{"status_triagem": "pendente_julgamento_humano"}]}, hoje)[0]) == 1),
        ("status sem pessoa passa",
         avaliar({"f": [{"status": "pista — na fila, aguardando busca dirigida e juiz"}]}, hoje) == ([], 0)),
        ("pendente de 30 dias antes do prazo do estoque: passivo, não falha",
         avaliar({"f": [{"status": "pendente_confirmacao_documento", "registrado_em": "2026-09-01"}]}, hoje)
         == ([], 1)),
        ("pendente de 30 dias depois do prazo do estoque: reprova",
         len(avaliar({"f": [{"status": "pendente_confirmacao_documento", "registrado_em": "2026-10-15"}]},
                     depois)[0]) == 1),
        ("pendente de 5 dias passa",
         avaliar({"f": [{"status": "pendente_confirmacao_documento", "registrado_em": "2026-11-15"}]}, depois)
         == ([], 0)),
        ("data do feed (RFC 822) é lida",
         data_da_pista({"data_publicacao": "Tue, 25 Aug 2026 07:00:00 GMT"}) == dt.date(2026, 8, 25)),
        ("sem data conta no passivo",
         avaliar({"f": [{"status": "pendente_confirmacao_documento"}]}, hoje) == ([], 1)),
    ]
    falhas = [n for n, ok in casos if not ok]
    for n, ok in casos:
        print(f"  {'OK  ' if ok else 'FALHA'} {n}")
    if falhas:
        print(f"X AUTOTESTE: {len(falhas)} falha(s)")
        return 1
    print(f"OK AUTOTESTE — {len(casos)} casos, sem rede e sem escrita.")
    return 0


def main() -> int:
    filas = {}
    for arq, chave in FILAS:
        caminho = RAIZ / arq
        if not caminho.exists():
            continue
        d = json.loads(caminho.read_text(encoding="utf-8"))
        filas[arq] = d.get(chave) if isinstance(d, dict) else d
    sys.path.insert(0, str(RAIZ))
    from coletores_base import hoje_editorial
    falhas, passivo = avaliar(filas, hoje_editorial())
    if falhas:
        print(f"✗ FILA NÃO HUMANA: {len(falhas)} item(ns) esperando por pessoa ou vencidos:")
        for f in falhas[:30]:
            print(f"  - {f}")
        return 1
    print(f"✓ FILA NÃO HUMANA OK — nenhuma fila espera por pessoa; passivo declarado: {passivo} "
          f"pendente(s) antigo(s), prazo do estoque {PRAZO_DO_ESTOQUE}.")
    return 0


if __name__ == "__main__":
    sys.exit(autoteste() if "--autoteste" in sys.argv else main())
