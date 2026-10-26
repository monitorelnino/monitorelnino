#!/usr/bin/env python3
"""Sonda do fornecedor da plataforma de transparência das 27 capitais (matriz de planos, S28, N1).

Regime de prioridade (editoria, 22/10/2026), §1.11: o portal de transparência de cada prefeitura é
hospedado por um fornecedor (Betha, IPM/Atende.Net, Elotech, Equiplano, Fiorilli). Saber qual é
decide qual adaptador de busca de plano/decreto/licitação se escreve. Esta sonda só REGISTRA: lê a
página inicial do sítio da prefeitura (hosts já vistos em `data/municipios.json`, mais o padrão
`www.<cidade>.<uf>.gov.br`) e anota quais assinaturas de fornecedor aparecem nas ligações. Ausência
é "não localizamos até o corte", nunca "não existe"; recusa (401/403/429/451, captcha, muro) é
registrada com o motivo e respeitada.

Trava estrutural: escreve só `data/transparencia_fornecedor_capitais.json`. Trava de campo: nada de
pista, nada promovível. Trava de processo: a saída é fila própria, o índice nunca a lê.
Uso: python3 scripts/sondar_fornecedor_transparencia.py [--rodar] | --autoteste
"""
from __future__ import annotations

import re
import sys
import unicodedata
import urllib.error
import urllib.parse
from datetime import date

ARQUIVO = "transparencia_fornecedor_capitais.json"
CAPITAIS = (
    ("Rio Branco", "AC"), ("Maceió", "AL"), ("Macapá", "AP"), ("Manaus", "AM"), ("Salvador", "BA"),
    ("Fortaleza", "CE"), ("Brasília", "DF"), ("Vitória", "ES"), ("Goiânia", "GO"), ("São Luís", "MA"),
    ("Cuiabá", "MT"), ("Campo Grande", "MS"), ("Belo Horizonte", "MG"), ("Belém", "PA"),
    ("João Pessoa", "PB"), ("Curitiba", "PR"), ("Recife", "PE"), ("Teresina", "PI"),
    ("Rio de Janeiro", "RJ"), ("Natal", "RN"), ("Porto Alegre", "RS"), ("Porto Velho", "RO"),
    ("Boa Vista", "RR"), ("Florianópolis", "SC"), ("São Paulo", "SP"), ("Aracaju", "SE"),
    ("Palmas", "TO"),
)
# Assinaturas no endereço das ligações ou nos scripts da página (minúsculas).
ASSINATURAS = {
    "betha": ("betha.cloud", "betha.com.br", "bethacloud"),
    "ipm_atende": ("atende.net", "ipm.com.br", "ipmsistemas"),
    "elotech": ("elotech.com.br", "elotech"),
    "equiplano": ("equiplano.com.br", "equiplano"),
    "fiorilli": ("fiorilli", "sigcloud.com.br", "sigpublico"),
    "portal_transparencia_proprio": ("transparencia.",),
}
RECUSAS = (401, 403, 429, 451)


def _slug(nome: str) -> str:
    s = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "", s)


def candidatos(nome: str, uf: str, hosts_vistos=()) -> list:
    """Hosts a tentar, os já vistos primeiro, o padrão por último; sem repetição."""
    padrao = f"www.{_slug(nome)}.{uf.lower()}.gov.br"
    saida = []
    for h in list(hosts_vistos) + [padrao]:
        h = (h or "").lower().strip()
        if h and h not in saida:
            saida.append(h)
    return saida


def detectar_fornecedores(html: str) -> list:
    """Fornecedores cuja assinatura aparece no texto da página. Função pura."""
    t = (html or "").lower()
    return sorted(f for f, sigs in ASSINATURAS.items() if any(s in t for s in sigs))


def sondar_capital(nome, uf, hosts_vistos, buscar_fn):
    """Uma capital: primeiro host que responde. `buscar_fn(url) -> bytes`; recusa vira motivo."""
    tentativas = []
    for host in candidatos(nome, uf, hosts_vistos):
        url = f"https://{host}/"
        try:
            html = buscar_fn(url).decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            tentativas.append({"host": host, "resultado": f"http_{e.code}",
                               "recusa": e.code in RECUSAS})
            continue
        except Exception as e:  # noqa: BLE001 — a falha é dado da sonda, nunca derruba a rodada
            tentativas.append({"host": host, "resultado": type(e).__name__,
                               "recusa": type(e).__name__ == "MuroDeRobo"})
            continue
        forn = detectar_fornecedores(html)
        return {"capital": nome, "uf": uf, "host": host, "status": "lido",
                "fornecedores": forn, "tentativas": tentativas}
    return {"capital": nome, "uf": uf, "host": None, "status": "sem_resposta_ate_o_corte",
            "fornecedores": [], "tentativas": tentativas}


def hosts_vistos_de(municipios: list, nome: str, uf: str) -> list:
    saida = []
    for m in municipios:
        if m.get("nome") == nome and m.get("uf") == uf and "prefeitura" in (m.get("fonte") or "").lower():
            h = urllib.parse.urlparse(m.get("url") or "").netloc.lower()
            if h and h not in saida:
                saida.append(h)
    return saida


def rodar(ler_fn, gravar_fn, buscar_fn, hoje=None):
    municipios = ler_fn("municipios.json", []) or []
    linhas = [sondar_capital(n, u, hosts_vistos_de(municipios, n, u), buscar_fn) for n, u in CAPITAIS]
    gravar_fn(ARQUIVO, {"_governanca": "Sonda de fornecedor de transparência (S28, N1). Só registra; "
                        "nunca lida pelo cálculo da nota. Ausência = não localizamos até o corte.",
                        "verificado_em": (hoje or date.today()).isoformat(), "capitais": linhas})
    return linhas


def autoteste() -> int:
    assert detectar_fornecedores('<a href="https://x.betha.cloud/y">') == ["betha"]
    assert detectar_fornecedores("nada") == []
    assert candidatos("São Luís", "MA", ["a.b"])[-1] == "www.saoluis.ma.gov.br"
    assert candidatos("Natal", "RN", ["www.natal.rn.gov.br"]) == ["www.natal.rn.gov.br"]
    gravados = {}

    def falso(url):
        if "natal" in url:
            return b"<html>https://natal.atende.net/</html>"
        raise urllib.error.HTTPError(url, 403, "x", None, None)

    r = sondar_capital("Natal", "RN", [], falso)
    assert r["status"] == "lido" and r["fornecedores"] == ["ipm_atende"], r
    r = sondar_capital("Palmas", "TO", [], falso)
    assert r["status"] == "sem_resposta_ate_o_corte" and r["tentativas"][0]["recusa"], r
    linhas = rodar(lambda n, p=None: [], lambda n, o: gravados.update({n: o}), falso)
    assert len(linhas) == 27 and ARQUIVO in gravados
    fonte = open(__file__, encoding="utf-8").read()
    for proibido in ("estados.json", "saude_uf.json", "indice.json", "monitor_saude.json"):
        assert f'gravar_fn("{proibido}' not in fonte and f'gravar("{proibido}' not in fonte
    print("autoteste ok: 6 verificações offline, nada escrito em data/")
    return 0


if __name__ == "__main__":
    if "--autoteste" in sys.argv:
        sys.exit(autoteste())
    if "--rodar" in sys.argv:
        sys.path.insert(0, ".")
        import coletores_base as cb
        n = rodar(cb.ler, cb.gravar, lambda u: cb.buscar(u, timeout=30, origem="sondar_fornecedor_transparencia"))
        print(f"{len(n)} capitais; lidas: {sum(1 for x in n if x['status'] == 'lido')}")
        sys.exit(0)
    print(__doc__)
