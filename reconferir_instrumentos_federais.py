#!/usr/bin/env python3
"""Reconferência semanal dos instrumentos federais de saúde "anunciados, não localizados".

Pedido da central, 04/11/2026 23:35 (plano federal do El Niño, MS, 26/08): "não localizado" só vale com
data de conferência, e a data tem de andar. A cada 7 dias o elo dos desfechos lê o portal de publicações
do MS e a página já registrada do instrumento, procura um link para o documento e grava o resultado no
MESMO formato que `scripts/proveniencia_estadual.py` usa nos estados: `endereco_lacuna`
{motivo, verificado_em}. O cartão federal diz "não localizado até dd/mm" a partir dele.

REGRAS
  - Só instrumento sem documento: status "não localizado", "a localizar" ou "a conferir" e que não
    comece por "localizado". Instrumento com `endereco_lacuna` verificado há menos de 7 dias não é relido.
  - Achado = link do domínio gov.br, para PDF, cujo endereço ou texto traz TODAS as palavras do
    instrumento (`PALAVRAS`). Achou → `url` e `consultado_em`, e a lacuna sai. Instrumento sem
    palavras registradas não é conferido (nada se infere).
  - Fonte que não respondeu (rede, 401/403/429/451, muro de robô) NÃO é "não localizado": a data não
    anda e o instrumento fica como estava (indisponível ≠ ausente). Só se grava lacuna quando ao menos
    uma fonte foi lida por inteiro.
  - Cliente identificado, robots e Crawl-delay pelo `buscar_uma_vez`; recusa se respeita, sem insistir.

TRAVAS (as de `descobrir_planos.py`)
  1. ESTRUTURAL: escreve só `data/saude_desfechos/instrumentos.json`; nunca estados.json, saude_uf.json,
     municipios.json, indice.json nem monitor_saude.json.
  2. DE CAMPO: não cria pista nem promove nada; `documento_oficial_confirmado` não existe aqui.
  3. DE PROCESSO: peso zero, nunca lido pelo motor; nenhuma fila, nenhum banco.

Uso: python3 reconferir_instrumentos_federais.py [--aplicar]
     python3 reconferir_instrumentos_federais.py --autoteste     (offline, não escreve em data/)
"""
import re
import sys
from datetime import date
from urllib.parse import urljoin, urlsplit

from coletores_base import buscar_uma_vez, gravar, hoje, ler, normalizar_nome, rodar_autoteste
from scripts.proveniencia_estadual import LACUNA

ARQUIVO = "saude_desfechos/instrumentos.json"
PORTAL = "https://www.gov.br/saude/pt-br/centrais-de-conteudo/publicacoes"
DIAS = 7
# Cada instrumento: grupos de palavras; um grupo casa se QUALQUER alternativa aparece (endereço ou texto
# do link, sem acento); o link casa se TODOS os grupos casam.
PALAVRAS = {
    "ms_plano_el_nino_2026": (("el nino", "el-nino", "elnino"), ("plano",)),
    "ms_portaria_4185_2022": (("4185", "4.185"),),
    "ms_portaria_painel_especialistas": (("painel",), ("especialistas",)),
    "ms_plano_inundacao_2019": (("inundac",), ("plano", "contingencia")),
}
RE_LINK = re.compile(r'<a\b[^>]*?href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.I | re.S)


def sem_documento(ins: dict) -> bool:
    """Status diz que o documento não está em mãos. Função pura."""
    s = normalizar_nome(ins.get("status") or "").lower()
    return not s.startswith("localizado") and bool(re.search(r"nao localizad|a localizar|a conferir", s))


def devido(ins: dict, hoje_iso: str) -> bool:
    """Sem conferência registrada ou com ela há DIAS ou mais. Função pura."""
    v = (ins.get("endereco_lacuna") or {}).get("verificado_em")
    return not v or (date.fromisoformat(hoje_iso) - date.fromisoformat(v)).days >= DIAS


def achar_link(html: str, base: str, grupos: tuple) -> "str | None":
    """Primeiro link gov.br para PDF cujo endereço ou texto traz todos os grupos. Função pura."""
    for href, texto in RE_LINK.findall(html):
        url = urljoin(base, href.strip())
        p = urlsplit(url)
        if not (p.hostname or "").endswith("gov.br") or not p.path.lower().endswith(".pdf"):
            continue
        alvo = normalizar_nome(f"{url} {re.sub(r'<[^>]+>', ' ', texto)}").lower()
        if all(any(a in alvo for a in g) for g in grupos):
            return url
    return None


def conferir(federais: list, paginas: dict, hoje_iso: str) -> dict:
    """Atualiza `federais` no lugar. `paginas` = {url: html lido por inteiro}; fonte que falhou não está
    nele. Devolve contagem. Função pura (a rede fica em `ler_paginas`)."""
    c = {"achado": 0, "lacuna": 0, "sem_leitura": 0, "sem_palavras": 0, "em_dia": 0}
    for ins in federais:
        if not sem_documento(ins):
            continue
        if not devido(ins, hoje_iso):
            c["em_dia"] += 1
            continue
        grupos = PALAVRAS.get(ins.get("id"))
        if not grupos:
            c["sem_palavras"] += 1
            continue
        fontes = [u for u in (PORTAL, ins.get("url")) if u in paginas]
        if not fontes:
            c["sem_leitura"] += 1
            continue
        url = next((u for f in fontes for u in [achar_link(paginas[f], f, grupos)] if u), None)
        if url:
            ins["url"], ins["consultado_em"] = url, hoje_iso
            ins.pop("endereco_lacuna", None)
            c["achado"] += 1
        else:
            ins["endereco_lacuna"] = {"motivo": LACUNA, "verificado_em": hoje_iso}
            c["lacuna"] += 1
    return c


def ler_paginas(federais: list, buscar=buscar_uma_vez) -> dict:
    """Uma tentativa por endereço; falha vira ausência no dicionário, nunca zero."""
    urls = {PORTAL} | {i["url"] for i in federais if sem_documento(i) and i.get("url")}
    out = {}
    for u in sorted(urls):
        try:
            out[u] = buscar(u, origem="reconferir_instrumentos_federais").decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001 — recusa/rede/muro: a fonte não foi lida, o instrumento fica como estava
            print(f"  fonte não lida ({type(e).__name__}): {u}")
    return out


def autoteste() -> int:
    h = "2026-11-05"
    pag = '<a href="/saude/x/plano-el-nino-2026.pdf">Plano El Niño</a><a href="/saude/y.html">el nino</a>'
    base = "https://www.gov.br/saude/pt-br/centrais-de-conteudo/publicacoes"
    def novo(**k): return {"id": "ms_plano_el_nino_2026", "status": "documento integral não localizado até 09/09", **k}
    a, b, c_, d = novo(), novo(), novo(endereco_lacuna={"motivo": LACUNA, "verificado_em": "2026-11-01"}), novo()
    r1 = conferir([a], {base: "<p>nada</p>"}, h)
    r2 = conferir([b], {base: pag}, h)
    r3 = conferir([c_], {base: "<p>nada</p>"}, h)
    r4 = conferir([d], {}, h)
    lido = {"id": "ms_plano_seca_2026", "status": "localizado e lido (íntegra)"}
    fonte = open(__file__, encoding="utf-8").read()
    return rodar_autoteste({
        "sem achado, fonte lida → lacuna com a data de hoje": lambda: a["endereco_lacuna"] == {"motivo": LACUNA, "verificado_em": h} and r1["lacuna"] == 1,
        "link PDF gov.br com as palavras → url, sem lacuna": lambda: b["url"].endswith("plano-el-nino-2026.pdf") and "endereco_lacuna" not in b and r2["achado"] == 1,
        "html sem PDF não é achado": lambda: achar_link('<a href="/s/el-nino.html">plano el nino</a>', base, PALAVRAS["ms_plano_el_nino_2026"]) is None,
        "domínio fora de gov.br não é achado": lambda: achar_link('<a href="https://x.com/plano-el-nino.pdf">x</a>', base, PALAVRAS["ms_plano_el_nino_2026"]) is None,
        "conferido há menos de 7 dias não é relido": lambda: c_["endereco_lacuna"]["verificado_em"] == "2026-11-01" and r3["em_dia"] == 1,
        "fonte não lida: a data NÃO anda e nada é afirmado": lambda: "endereco_lacuna" not in d and r4["sem_leitura"] == 1,
        "instrumento localizado e lido não é tocado": lambda: not sem_documento(lido),
        "'a conferir' sem url conta como sem documento": lambda: sem_documento({"status": "citada no plano (p. 7); íntegra a conferir"}),
        "devido em 7 dias": lambda: devido({"endereco_lacuna": {"verificado_em": "2026-10-29"}}, h) and not devido({"endereco_lacuna": {"verificado_em": "2026-10-30"}}, h),
        "trava estrutural: só instrumentos.json é gravado": lambda: re.findall(r"\bgravar\(([^)]*)\)", fonte.split("\ndef main(")[1]) == ["ARQUIVO, d"],
    })


def main() -> int:
    d = ler(ARQUIVO)
    c = conferir(d["federais"], ler_paginas(d["federais"]) if any(sem_documento(i) and devido(i, hoje()) for i in d["federais"]) else {}, hoje())
    print(f"instrumentos federais: {c}")
    if "--aplicar" in sys.argv:
        gravar(ARQUIVO, d)
    return 0


if __name__ == "__main__":
    sys.exit(autoteste() if "--autoteste" in sys.argv else main())
