#!/usr/bin/env python3
"""De quem é este domínio? Resolve o host de uma URL oficial no município dono dele.

NASCEU DE ATRIBUIÇÃO ERRADA, MEDIDA EM 03/10/2026. A central garimpou a fila de pistas e achou 88
documentos de plano em domínio oficial parados como "a confirmar". Passados pelo juiz, **nenhum foi
promovido** — e o relatório mostrou por quê:

    documento                                      pista atribuída a
    celsoramos.sc.gov.br/.../plano.pdf             Salete/SC
    defesacivil.taio.sc.gov.br/.../PLANO-TAIO.pdf  Rio do Oeste/SC
    tubarao.sc.gov.br/.../PLANO_2025.pdf           Monte Castelo/SC
    ibiam.sc.gov.br/.../PLANO-DE-CONTINGENCIA.pdf  Videira/SC
    encantado.rs.gov.br/.../plano-encantado.html   Porto Alegre/RS
    gcpstorage.caxias.rs.gov.br/.../plano.pdf      Bom Jesus/RS
    itapetininga.sp.gov.br/.../download/75/        Leme/SP

A pista vinha da busca web, e o município era atribuído pelo **trecho** do documento — o nome de
cidade que aparecia perto do termo encontrado. Num plano de contingência municipal, os nomes que
aparecem no texto são os das comunidades, dos municípios vizinhos e dos consórcios: o plano de
Celso Ramos lista as capelas de Salete, e a pista virou de Salete.

O domínio é evidência mais forte do que um nome no meio do texto: `celsoramos.sc.gov.br` é o sítio
do município de Celso Ramos, e um PDF servido ali é documento DELE. Este módulo resolve o host no
município dono, e quem o usa atribui a pista por ele — guardando a atribuição anterior, porque
corrigir sem registrar é perder a trilha.

O que ele NÃO faz: adivinhar. Host que não casa com município nenhum devolve `None`, e a pista
continua como está. Domínio de estado, de consórcio, de câmara ou de armazenamento genérico não
resolve município — `camara.leme.sp.leg.br` é da Câmara, e Câmara não é Executivo (a etapa 3 do
codebook cuidaria disso, mas é melhor não chegar lá com a atribuição errada).

USO
    from municipio_do_dominio import municipio_de
    municipio_de("https://celsoramos.sc.gov.br/uploads/x.pdf")  # -> {'nome','uf','ibge'}

    python3 scripts/municipio_do_dominio.py --autoteste
    python3 scripts/municipio_do_dominio.py https://tubarao.sc.gov.br/x.pdf
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
import unicodedata
import urllib.parse

RAIZ = pathlib.Path(__file__).resolve().parent.parent
REFERENCIA = RAIZ / "data" / "municipios_ibge_referencia.json"

UFS = ("ac", "al", "am", "ap", "ba", "ce", "df", "es", "go", "ma", "mg", "ms", "mt", "pa", "pb",
       "pe", "pi", "pr", "rj", "rn", "ro", "rr", "rs", "sc", "se", "sp", "to")

# Rótulos que vêm ANTES do nome do município no host e não fazem parte dele. A lista é do que
# apareceu de verdade na fila: `defesacivil.taio.sc.gov.br`, `web.arapiraca.al.gov.br`,
# `gcpstorage.caxias.rs.gov.br`, `www3.franca.sp.gov.br`.
PREFIXOS = ("www", "www2", "www3", "web", "portal", "novoportal", "site", "transparencia",
            "defesacivil", "defesa-civil", "protecaocivil", "saude", "educacao", "gcpstorage",
            "storage", "arquivos", "documentos", "doc", "docs", "cdn", "static", "media",
            "diariooficial", "dom", "do", "legislacao", "leis", "sapl",
            # 09/10/2026 (A1-10): `prefeitura.<nome>.<uf>.gov.br` e suas variantes eram host de
            # dois rótulos antes da UF, e a função devolvia None por "sobrou mais de um rótulo" —
            # o corretor de atribuição não resolvia nenhum deles. "prefeitura" é rótulo de
            # serviço, como "portal": o nome do município é o outro.
            "prefeitura", "prefeituramunicipal", "pref", "municipio", "governo",
            "cidadao", "servicos", "atendimento")



def _norm(texto: str) -> str:
    """Nome sem acento, sem pontuação e sem espaço — a forma com que um host nomeia a cidade."""
    n = unicodedata.normalize("NFKD", str(texto or "").replace("'", "").replace("’", ""))
    n = n.encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", n)


def partes_do_host(host: str):
    """(candidato_a_municipio, uf) a partir do host. Função pura; (None, None) quando não serve.

    O padrão municipal brasileiro é `<nome>.<uf>.gov.br`: o ente recebe a delegação desse nome, e todo
    rótulo à esquerda é subdomínio DELE (`codesal.salvador.ba.gov.br`, `transp-arquivos.portovelho.ro.gov.br`).
    O candidato é, portanto, o rótulo colado à UF. 10/11/2026: a regra antiga descartava rótulos de serviço
    de uma lista e recusava quando sobrava mais de um, e o juiz recusou o plano de Salvador e a portaria de
    Porto Velho como "fora do domínio do ente". Rótulo de serviço colado à UF (`saude.ba.gov.br`,
    `www.sc.gov.br`) é sítio de estado; câmara (`camara.<nome>`) não é Executivo.
    """
    h = (host or "").lower().strip().rstrip(".")
    if not h or "." not in h:
        return None, None
    rotulos = h.split(".")
    if len(rotulos) < 4 or ".".join(rotulos[-2:]) != "gov.br":
        return None, None     # só o padrão municipal `<nome>.<uf>.gov.br`
    uf, nome = rotulos[-3], rotulos[-4]
    if uf not in UFS or not nome or nome in PREFIXOS:
        return None, None
    if any(r.startswith("camara") for r in rotulos[:-4]):
        return None, None
    return nome, uf.upper()


# Versão do resolvedor, como a do codebook: muda a cada correção dele. Recusa por autoridade julgada antes
# dela, em domínio que o resolvedor em vigor dá ao próprio ente, volta ao juiz uma vez
# (`julgar_filas.recusa_desmentida_pelo_dominio`). Sobe-se a data; nada de regra antiga guardada.
RESOLVEDOR_DESDE = "2026-11-10"

# Domínio municipal fora do padrão `<nome>.<uf>.gov.br`. Lista fechada, só de domínio conferido (a página
# inicial se identifica como a prefeitura). Era cópia em `buscador2.py` (30/10/2026); uma lista só.
MUNICIPAIS_SEM_UF = {"pbh.gov.br": ("Belo Horizonte", "MG")}


def diarios_estaduais() -> dict:
    """{host: UF} das imprensas oficiais estaduais, de `data/fontes_doe.json` (a lista do coletor do DOE).
    Três são servidas fora de `.gov.br` (IOERJ, IOEPA, CEPE). Era cópia em `buscador2.py`; o juiz não a via
    e recusou o Decreto RJ 50.357/2026 sem baixá-lo (10/11/2026)."""
    global _DOES
    if _DOES is None:
        try:
            ufs = json.loads((RAIZ / "data" / "fontes_doe.json").read_text(encoding="utf-8")).get("ufs") or {}
        except (OSError, ValueError):
            ufs = {}
        _DOES = {h: uf for uf, f in ufs.items() if (h := _host(str((f or {}).get("url") or "")))}
    return _DOES


_DOES = None


def _host(url: str) -> str:
    h = (urllib.parse.urlsplit(str(url or "").strip()).hostname or "").lower().rstrip(".")
    return h[4:] if h.startswith("www.") else h


def _indice(referencia=None):
    if referencia is None:
        if not _INDICE_REAL:
            _INDICE_REAL.append(_indice(json.loads(REFERENCIA.read_text(encoding="utf-8"))))
        return _INDICE_REAL[0]
    ref = referencia
    indice = {}
    for m in ref:
        indice[(_norm(m["nome"]), str(m["uf"]).upper())] = {
            "nome": m["nome"], "uf": str(m["uf"]).upper(),
            "ibge": str(m["codigo_ibge"]).zfill(7)}
    return indice


_INDICE_REAL = []   # a malha do IBGE, lida uma vez por processo


def municipio_de(url: str, referencia=None):
    """O município dono do domínio desta URL, ou None. Função pura dada a referência."""
    host = urllib.parse.urlparse(str(url or "")).netloc or str(url or "")
    host = host.split("@")[-1].split(":")[0].lower()
    indice = _indice(referencia)
    for d, (nome, uf_d) in MUNICIPAIS_SEM_UF.items():
        if host == d or host.endswith("." + d):
            return indice.get((_norm(nome), uf_d))
    candidato, uf = partes_do_host(host)
    if not candidato or not uf:
        return None
    achado = indice.get((_norm(candidato), uf))
    if achado:
        return achado
    # O host às vezes traz o nome CURTO: `caxias.rs.gov.br` é Caxias do Sul, `santamaria.rs.gov.br`
    # é Santa Maria. Resolver isso exige unicidade: só vale quando UM município daquela UF começa
    # pelo candidato. Em RS, "caxias" só casa com Caxias do Sul; em MA existe Caxias, mas é outra
    # UF, e a UF vem do próprio host. Sem unicidade, não se adivinha.
    alvo = _norm(candidato)
    # Com rótulo à esquerda, o host é de órgão: nome curto não se adivinha (`tesouro.fazenda.rs.gov.br`
    # não é Fazenda Vilanova).
    if len(alvo) < 5 or any(r not in PREFIXOS for r in host.split(".")[:-4]):
        return None
    casam = [v for (n, u), v in indice.items() if u == uf and n.startswith(alvo)]
    return casam[0] if len(casam) == 1 else None


def _autoteste() -> int:
    falhas = []
    # O total era um literal e envelhecia calado: dizia cobrir mais casos do que
    # cobre, ou menos. Agora e contado.
    _casos_contados = []

    from _casos import ok_de
    ok = ok_de(falhas, _casos_contados)

    REF = [
        {"nome": "Celso Ramos", "uf": "SC", "codigo_ibge": 4204004},
        {"nome": "Taió", "uf": "SC", "codigo_ibge": 4217808},
        {"nome": "Tubarão", "uf": "SC", "codigo_ibge": 4218707},
        {"nome": "Franca", "uf": "SP", "codigo_ibge": 3516200},
        {"nome": "Caxias do Sul", "uf": "RS", "codigo_ibge": 4305108},
        {"nome": "Arapiraca", "uf": "AL", "codigo_ibge": 2700300},
        {"nome": "Leme", "uf": "SP", "codigo_ibge": 3526704},
        {"nome": "Encantado", "uf": "RS", "codigo_ibge": 4306809},
    ]

    ok("host municipal simples",
       (municipio_de("https://celsoramos.sc.gov.br/uploads/x.pdf", REF) or {}).get("nome") == "Celso Ramos")
    ok("devolve o código IBGE com sete dígitos",
       (municipio_de("https://celsoramos.sc.gov.br/x", REF) or {}).get("ibge") == "4204004")
    ok("rótulo de serviço à frente não atrapalha",
       (municipio_de("https://defesacivil.taio.sc.gov.br/wp/PLANO.pdf", REF) or {}).get("nome") == "Taió")
    ok("www3 não atrapalha",
       (municipio_de("https://www3.franca.sp.gov.br/pdf/x.pdf", REF) or {}).get("nome") == "Franca")
    ok("web. não atrapalha",
       (municipio_de("https://web.arapiraca.al.gov.br/tipo/x", REF) or {}).get("nome") == "Arapiraca")
    ok("nome curto resolve quando é único na UF",
       (municipio_de("https://gcpstorage.caxias.rs.gov.br/documents/x.pdf", REF) or {}).get("nome")
       == "Caxias do Sul")
    ok("nome exato vence o prefixo",
       (municipio_de("https://bomjesus.rs.gov.br/x", REF + [
           {"nome": "Bom Jesus", "uf": "RS", "codigo_ibge": 4302303},
           {"nome": "Bom Jesus do Sul", "uf": "RS", "codigo_ibge": 4302304}]) or {}).get("ibge")
       == "4302303")
    ok("prefixo ambíguo na UF não resolve",
       municipio_de("https://bomjes.rs.gov.br/x", REF + [
           {"nome": "Bom Jesus", "uf": "RS", "codigo_ibge": 4302303},
           {"nome": "Bom Jesus do Sul", "uf": "RS", "codigo_ibge": 4302304}]) is None)
    ok("nome curto curto demais não resolve (menos de cinco letras)",
       municipio_de("https://leme.sp.gov.br/x", [{"nome": "Lemeirinha", "uf": "SP",
                                                  "codigo_ibge": 3500000}]) is None)
    ok("acento no nome casa com o host sem acento",
       (municipio_de("https://tubarao.sc.gov.br/x.pdf", REF) or {}).get("ibge") == "4218707")
    ok("UF errada não casa", municipio_de("https://franca.rs.gov.br/x", REF) is None)
    ok("domínio de estado não resolve município",
       municipio_de("https://www.sc.gov.br/noticias", REF) is None)
    ok("câmara (.leg.br) não resolve município",
       municipio_de("https://camara.leme.sp.leg.br/ato.pdf", REF) is None)
    ok("domínio federal não resolve município",
       municipio_de("https://www.gov.br/mdr/pt-br", REF) is None)
    ok("veículo privado não resolve município",
       municipio_de("https://g1.globo.com/sc/noticia.html", REF) is None)
    ok("todo rótulo à esquerda de <nome>.<uf>.gov.br é subdomínio do ente",
       (municipio_de("https://a.b.taio.sc.gov.br/x", REF) or {}).get("nome") == "Taió")
    ok("órgão do município em subdomínio (codesal.salvador.ba.gov.br)",
       (municipio_de("https://codesal.salvador.ba.gov.br/wp/PLANO.pdf",
                     REF + [{"nome": "Salvador", "uf": "BA", "codigo_ibge": 2927408}]) or {}).get("ibge") == "2927408")
    ok("subdomínio de arquivos (transp-arquivos.portovelho.ro.gov.br)",
       (municipio_de("https://transp-arquivos.portovelho.ro.gov.br/u/p.pdf",
                     REF + [{"nome": "Porto Velho", "uf": "RO", "codigo_ibge": 1100205}]) or {}).get("nome") == "Porto Velho")
    ok("domínio municipal sem UF da lista fechada (prefeitura.pbh.gov.br)",
       (municipio_de("https://prefeitura.pbh.gov.br/plano.pdf",
                     REF + [{"nome": "Belo Horizonte", "uf": "MG", "codigo_ibge": 3106200}]) or {}).get("ibge") == "3106200")
    ok("órgão de estado colado à UF segue sem município (vigilancia.saude.sc.gov.br)",
       municipio_de("https://vigilanciasanitaria.saude.sc.gov.br/x", REF) is None)
    ok("subdomínio de órgão de estado não vira município por prefixo (tesouro.fazenda.rs.gov.br)",
       municipio_de("https://tesouro.fazenda.rs.gov.br/x.pdf",
                     REF + [{"nome": "Fazenda Vilanova", "uf": "RS", "codigo_ibge": 4307815}]) is None)
    ok("câmara em subdomínio do ente não é Executivo",
       municipio_de("https://camara.taio.sc.gov.br/x", REF) is None)
    ok("imprensa oficial estadual fora de .gov.br vem da lista do DOE",
       diarios_estaduais().get("ioerj.com.br") == "RJ" or not (RAIZ / "data" / "fontes_doe.json").exists())
    ok("município fora da referência devolve None",
       municipio_de("https://cidadeinexistente.sc.gov.br/x", REF) is None)
    ok("url vazia devolve None", municipio_de("", REF) is None and municipio_de(None, REF) is None)
    ok("host sem ponto devolve None", partes_do_host("localhost") == (None, None))
    ok("partes_do_host nomeia a UF em maiúscula",
       partes_do_host("encantado.rs.gov.br") == ("encantado", "RS"))

    # 09/10/2026 (A1-10): `prefeitura.<nome>` e companhia eram host de dois rótulos antes da UF,
    # e a função devolvia None — o corretor de atribuição não resolvia nenhum deles.
    ok("prefeitura.<nome>.<uf>.gov.br resolve o municipio",
       partes_do_host("prefeitura.sorocaba.sp.gov.br") == ("sorocaba", "SP"))
    ok("www.prefeitura.<nome> tambem resolve",
       partes_do_host("www.prefeitura.taio.sc.gov.br") == ("taio", "SC"))
    ok("camara segue fora (nao e Executivo)",
       partes_do_host("camara.leme.sp.leg.br") == (None, None))
    ok("host de estado segue sem municipio", partes_do_host("sp.gov.br") == (None, None))

    # A referência real existe e o índice se monta sobre ela (sem rede).
    if REFERENCIA.exists():
        real = _indice()
        ok("a referência do IBGE tem as 5.571 unidades", len(real) >= 5560)
        ok("Taió está na referência real", ("taio", "SC") in real)

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else f"✓ AUTOTESTE OK — {len(_casos_contados)} casos, sem rede.")
    return 1 if falhas else 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return _autoteste()
    alvos = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not alvos:
        print(__doc__)
        return 2
    for url in alvos:
        m = municipio_de(url)
        print(f"{url}\n  -> " + (f"{m['nome']}/{m['uf']} ({m['ibge']})" if m else "não resolve município"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
