#!/usr/bin/env python3
"""Sonda do PNCP para planos de defesa civil nas 27 capitais (matriz de planos, S22, N1).

Regime de prioridade (editoria, 22/10/2026), §1.10: contratação de elaboração de plano
(contingência, redução de riscos) e o decreto de aprovação deixam rastro de compras públicas no PNCP.
A sonda consulta a busca pública do PNCP (sem chave) por capital e REGISTRA os resultados cujo
município e UF coincidem com a capital: título, órgão, data e endereço. Contratação não é plano: o
registro é só pista de onde procurar o documento. Ausência é "não localizamos até o corte", nunca
"não existe"; recusa (401/403/429/451, captcha, muro) é registrada com o motivo e respeitada.

Trava estrutural: escreve só `data/pncp_planos_capitais.json`. Trava de campo: nada de pista,
nada promovível. Trava de processo: a saída é fila própria, o índice nunca a lê.
Uso: python3 scripts/sondar_pncp_planos.py [--rodar] | --autoteste
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
from datetime import date

from sondar_fornecedor_transparencia import CAPITAIS, RECUSAS, _slug

ARQUIVO = "pncp_planos_capitais.json"
BASE = "https://pncp.gov.br/api/search/"
TERMOS = ("plano de contingência defesa civil", "plano municipal de redução de riscos", "PLANCON")
LIMITE_POR_CONSULTA = 10


def url_busca(termo: str, cidade: str) -> str:
    q = urllib.parse.urlencode({"q": f"{termo} {cidade}", "tipos_documento": "edital", "status": "todos",
                                "ordenacao": "-data", "pagina": 1, "tam_pagina": LIMITE_POR_CONSULTA})
    return f"{BASE}?{q}"


def extrair(corpo: bytes, cidade: str, uf: str) -> list:
    """Itens da resposta cujo município e UF são os da capital. Função pura; esquema inesperado = []."""
    try:
        itens = (json.loads(corpo.decode("utf-8", "replace")) or {}).get("items") or []
    except (ValueError, AttributeError):
        return []
    saida = []
    for i in itens:
        if not isinstance(i, dict):
            continue
        if _slug(str(i.get("municipio_nome") or "")) != _slug(cidade) or str(i.get("uf") or "").upper() != uf:
            continue
        saida.append({"titulo": i.get("title"), "orgao": i.get("orgao_nome"),
                      "publicado_em": i.get("data_publicacao_pncp"),
                      "url": "https://pncp.gov.br/app" + str(i["item_url"]) if i.get("item_url") else None})
    return saida


def sondar_capital(cidade, uf, buscar_fn):
    achados, falhas = [], []
    for termo in TERMOS:
        try:
            achados += extrair(buscar_fn(url_busca(termo, cidade)), cidade, uf)
        except urllib.error.HTTPError as e:
            falhas.append({"termo": termo, "resultado": f"http_{e.code}", "recusa": e.code in RECUSAS})
        except Exception as e:  # noqa: BLE001 — a falha é dado da sonda, nunca derruba a rodada
            falhas.append({"termo": termo, "resultado": type(e).__name__,
                           "recusa": type(e).__name__ == "MuroDeRobo"})
    unicos = list({a["url"] or a["titulo"]: a for a in achados}.values())
    status = "com_resultado" if unicos else ("sem_resposta_ate_o_corte" if len(falhas) == len(TERMOS)
                                             else "sem_resultado_ate_o_corte")
    return {"capital": cidade, "uf": uf, "status": status, "resultados": unicos, "falhas": falhas}


def rodar(gravar_fn, buscar_fn, hoje=None):
    linhas = [sondar_capital(n, u, buscar_fn) for n, u in CAPITAIS]
    gravar_fn(ARQUIVO, {"_governanca": "Sonda do PNCP (S22, N1). Contratação não é plano: só aponta onde "
                        "procurar. Nunca lida pelo cálculo da nota. Ausência = não localizamos até o corte.",
                        "verificado_em": (hoje or date.today()).isoformat(), "termos": list(TERMOS),
                        "capitais": linhas})
    return linhas


def autoteste() -> int:
    ok = json.dumps({"items": [
        {"municipio_nome": "NATAL", "uf": "RN", "title": "Plano de contingência", "orgao_nome": "SEMURB",
         "item_url": "/editais/1/2026/3", "data_publicacao_pncp": "2026-05-01"},
        {"municipio_nome": "Natal", "uf": "SP", "title": "homônimo em outra UF"}]}).encode()
    r = extrair(ok, "Natal", "RN")
    assert len(r) == 1 and r[0]["url"].endswith("/editais/1/2026/3"), r
    assert extrair(b"<html>", "Natal", "RN") == [] and extrair(b'{"items": [1]}', "Natal", "RN") == []

    def falso(url):
        if "Palmas" in url:
            raise urllib.error.HTTPError(url, 403, "x", None, None)
        return ok

    assert sondar_capital("Natal", "RN", falso)["status"] == "com_resultado"
    p = sondar_capital("Palmas", "TO", falso)
    assert p["status"] == "sem_resposta_ate_o_corte" and p["falhas"][0]["recusa"], p
    assert sondar_capital("Manaus", "AM", lambda u: b'{"items": []}')["status"] == "sem_resultado_ate_o_corte"
    gravados = {}
    assert len(rodar(lambda n, o: gravados.update({n: o}), falso)) == 27 and ARQUIVO in gravados
    fonte = open(__file__, encoding="utf-8").read()
    for proibido in ("estados.json", "saude_uf.json", "indice.json", "monitor_saude.json"):
        assert f'gravar_fn("{proibido}' not in fonte
    print("autoteste ok: 7 verificações offline, nada escrito em data/")
    return 0


if __name__ == "__main__":
    if "--autoteste" in sys.argv:
        sys.exit(autoteste())
    if "--rodar" in sys.argv:
        sys.path.insert(0, ".")
        import coletores_base as cb
        n = rodar(cb.gravar, lambda u: cb.buscar(u, timeout=30, origem="sondar_pncp_planos"))
        print(f"{len(n)} capitais; com resultado: {sum(1 for x in n if x['status'] == 'com_resultado')}")
        sys.exit(0)
    print(__doc__)
