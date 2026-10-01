#!/usr/bin/env python3
"""Portão: imprensa DESCOBRE, nunca REGISTRA.

Uma notícia pode levar o Monitor até o ato. Ela não pode SER o ato. O registro que pontua no
MARÉ Legal tem de apontar para o documento primário — diário oficial, sítio do órgão, ato
publicado — porque o que o índice afirma é "isto foi publicado e pode ser conferido", e uma
reportagem não é publicação do ente.

O QUE ELE EXISTE PARA BARRAR
----------------------------
Aconteceu. Em 01/10/2026 a auditoria pedida pela editoria (item 0 do handover da Defesa civil)
encontrou Curitiba (PR) pontuando como `plano` com URL em `agoraparana.com.br` e fonte declarada
como release da Secom "via imprensa regional". O plano noticiado não existia em fonte primária; o
diário municipal trazia outro ato, um decreto de comitê. Resultado: 2,8 pontos de PR apoiados em
notícia, e a errata pública C29 para desfazer.

A pista não é proibida — ela é o começo do trabalho. O que este portão cobra é que, na hora de
pontuar, o registro já tenha trocado a notícia pelo documento.

Domínio oficial aqui é: `*.gov.br`, `*.leg.br`, `*.jus.br`, os agregadores de diário oficial
(`diariomunicipal.com.br`, Querido Diário) e a lista nomeada abaixo, que existe porque alguns
entes publicam fora do `gov.br` há décadas. URL ausente não é tratada como falha: é outro defeito,
de outra regra, e misturar os dois faria este portão reprovar por motivo que não é o seu.

Uso: python3 scripts/verificar_imprensa_nao_registra.py
"""
import json
import pathlib
import sys
from urllib.parse import urlparse

RAIZ = pathlib.Path(__file__).resolve().parent.parent

# Categorias que CREDITAM no índice. Decreto não pontua (fica no banco para transparência) e
# `nao_verificado`/`nao_localizado` valem zero — nenhuma delas move ponto, e por isso nenhuma
# delas entra na conferência.
PONTUAM = {"plano", "plano_novo", "plano_readaptado", "plano_recorrente",
           "plano_antigo", "plano_elaboracao", "plano_saude", "estrutura"}

SUFIXOS_OFICIAIS = (".gov.br", ".leg.br", ".jus.br")

# Entes que publicam ato oficial fora do `gov.br`. Cada linha é um domínio conferido à mão; a
# lista é curta de propósito — crescer por conveniência é como a notícia entraria de volta.
HOSTS_OFICIAIS = {
    "www.diariomunicipal.com.br",   # agregador de diários oficiais municipais (AMUPE/outros)
    "diariomunicipal.com.br",
    "prefeitura.poa.br",            # Prefeitura de Porto Alegre, domínio institucional histórico
}


def oficial(host: str) -> bool:
    host = host.lower()
    if host in HOSTS_OFICIAIS:
        return True
    if "queridodiario.ok.org.br" in host or "data.queridodiario" in host:
        return True
    return host.endswith(SUFIXOS_OFICIAIS)


def conferir(caminho: pathlib.Path) -> list:
    falhas = []
    registros = json.loads(caminho.read_text(encoding="utf-8"))
    if isinstance(registros, dict):
        registros = list(registros.values())
    for r in registros:
        if not isinstance(r, dict) or r.get("categoria") not in PONTUAM:
            continue
        url = (r.get("url") or "").strip()
        if not url:
            continue
        host = urlparse(url).netloc
        if host and not oficial(host):
            quem = f"{r.get('nome') or r.get('uf') or '?'} ({r.get('uf', '?')})"
            falhas.append(f"{caminho.name}: {quem} pontua como '{r['categoria']}' com URL em "
                          f"'{host}' — não é domínio oficial nem diário. Troque pela fonte "
                          f"primária ou rebaixe a pista (C10).")
    return falhas


def main() -> int:
    falhas = []
    for nome in ("municipios.json", "estados.json"):
        p = RAIZ / "data" / nome
        if p.exists():
            falhas += conferir(p)
    if falhas:
        print("✗ IMPRENSA NÃO REGISTRA (C10 · errata C29):")
        for f in falhas:
            print("   -", f)
        return 1
    print("✓ IMPRENSA NÃO REGISTRA OK — nenhum registro pontuável apoiado em domínio "
          "que não seja oficial ou diário.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
