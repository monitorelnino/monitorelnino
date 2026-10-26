#!/usr/bin/env python3
"""Limpeza de 26/10/2026: confirmações falsas e links falsos saem do que o site exibe ou publica.

Decisão da editoria (26/10/2026, 14:56 BRT): "retire do site tudo o que for link falso ou
confirmação falsa que passou por engano". Ordem: robo-registro/notas/HANDOVER_LIMPEZA_26-10-2026.md.

O QUE FAZ, E COMO NADA SOME SEM RASTRO
-------------------------------------
1. **Confirmações falsas** (`ERRATAS`): a decisão do juiz que promoveu vira recusa com `errata`
   datada, guardando o que era (METODOLOGIA §106, errata por linha). O registro do banco que ela
   sustentava sai de `municipios.json` e de `pontos_mapa.json`; a pista sai da fila pela porta.
   `CONFERIDAS` registra o trecho das que foram lidas e ficam.
2. **Links falsos** (`motivo_de_link_falso`): endereço sem relação com o tema sai das filas de pista
   e de `promocoes_automaticas.json`. Cada pista ou decisão retirada vai, inteira, para
   `arquivo/limpeza_26-10-2026/` (guardado no repositório e nunca servido: netlify.toml, §258), e a
   recusa vai para `data/pistas_rejeitadas.json` pela porta (`scripts/pistas.rejeitar`).
   Redirecionamento do Google News entra em `pistas_rejeitadas.json` agregado por UF, com a
   contagem e o caminho do arquivo: uma linha por URL seriam 8 MB, mais que o portão de tamanho
   admite numa execução, e a lista inteira já está no arquivo.

Não muda peso, crédito, régua nem regra do juiz; não toca o buscador; não apaga log.

USO
  python3 scripts/limpeza_26_10_2026.py --relatorio
  python3 scripts/limpeza_26_10_2026.py --aplicar
  python3 scripts/limpeza_26_10_2026.py --autoteste
"""
from __future__ import annotations

import json
import pathlib
import sys
import urllib.parse
from collections import Counter

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "scripts"))

ARQUIVO = RAIZ / "arquivo" / "limpeza_26-10-2026"
EM = "2026-10-26"
POR = "editoria, 26/10/2026 (rodada Limpeza)"
ORIGEM = "limpeza_26_10_2026"
QD = "https://data.queridodiario.ok.org.br/"

# (município, UF, URL exata, motivo). Tabela do handover §1 e a varredura das 159 promoções.
ERRATAS = (
    ("Candeias", "MG", "https://prefeitura.candeias.ba.gov.br/2025/03/defesa-civil-de-candeias-apresenta-plano-de-contingencia-para-continuacao-da-operacao-chuva/",
     "documento de Candeias/BA (outra UF) e é notícia"),
    ("Santa Rosa", "RS", "https://www.trindadedosul.rs.gov.br/wp-content/uploads/2025/06/Plano-de-Contingencia.pdf",
     "plano de Trindade do Sul; \"Santa Rosa\" é nome do hospital"),
    ("Rio do Oeste", "SC", "https://defesacivil.taio.sc.gov.br/wp-content/uploads/2026/08/PLANO-DE-CONTINGENCIA-Taio-agosto-2026.pdf",
     "plano de Taió; Rio do Oeste só aparece como vizinho"),
    ("Cubatão", "SP", "https://www.bndes.gov.br/arquivos/fep-mobilidade-urbana/relatorios-diagnostico/relatorio-Santos-vol-3.pdf",
     "relatório do BNDES, não documento do município"),
    ("Apucarana", "PR", QD + "4101408/2026-08-19/dae418d4fd84e033218a03d861c0a3ea8e21a8a9.pdf",
     "ato de calendário, não plano"),
    ("Goiânia", "GO", QD + "5208707/2026-08-12/92a375a415f1751fe37c697e62d361237cffda2f.pdf",
     "texto não é plano; data lida impossível (1959)"),
    ("Toledo", "PR", "https://www.toledo.pr.gov.br/sites/default/files/paginabasica-2026-09/"
     "24-09-2026_instrucao_normativa_no_17-2026_smed_plano_de_contingencia_da_rede_publica_municipal_de_ensino_para_eventos_climaticos_adversos.pdf",
     "instrução normativa de plano escolar (SMED), não plano municipal"),
    ("Rio Branco", "AC", "https://www.riobranco.ac.gov.br/saerb/prefeitura-de-rio-branco-apresenta-plano-de-contingencia-para-garantir-abastecimento-de-agua-durante-estiagem-severa/",
     "notícia, não documento"),
    ("Ilhabela", "SP", "https://www.ilhabela.sp.gov.br/portal/noticias/0/3/17590/defesa-civil-de-ilhabela-regulamenta-novo-plano-municipal-de-contingencia",
     "notícia, não documento"),
    ("Toledo", "PR", "https://www.toledo.pr.gov.br/noticias/assistencia-social/assistencia-social-apresenta-plano-de-contingencia-para-emergencias",
     "notícia, não documento"),
    ("Duque de Caxias", "RJ", "https://www.cmdc.rj.gov.br/?p=32729",
     "página da Câmara (notícia), não documento do Executivo"),
    ("Salto", "SP", QD + "3545209/2026-07-01/e6fd8348ed7a25d5db2d34ffd9fc1ad81e82edc4.pdf",
     "edição lida em 26/10/2026 sem instrumento do município (plano, PMPDEC ou decreto que institui)"),
    ("Alagoinhas", "BA", QD + "2900702/2026-09-11/c8ca60a50045716ee029b2b4d95a589481b052fe.pdf",
     "edição lida em 26/10/2026: o plano citado é de empreendimento, em condicionante de licença ambiental"),
    ("Birigui", "SP", QD + "3506508/2026-03-23/33b13c5b167987f08f78b707c1c5ee95e14c7a40.txt",
     "comitê municipal da dengue: plano setorial de saúde, não plano de proteção e defesa civil"),
    ("Serra", "ES", QD + "3205002/2025-12-19/35d226b9dea4bc74b05a648fb52e72ac5d1116a2.pdf",
     "lei de calendário oficial de eventos, não plano"),
)

# Lidas e mantidas: o instrumento do município está no texto (handover §1).
CONFERIDAS = (
    ("Coronel Macedo", "SP", QD + "3512605/2026-07-08/cfc3861c7e5a2f000dc424a19cdfa00ac7afea06.pdf",
     "Decreto nº 088/2026, de 03/07/2026: \"com fundamento no artigo 9º da Lei Ordinária nº 434, de 29 de "
     "maio de 2024, que institui o Plano Municipal de Contingência, Proteção e Defesa Civil – PLANCON\""),
)

# Endereço sem relação com o tema, por categoria (handover §2). Lista fechada: só o que a medição
# de 26/10 achou nas filas; host fora dela não cai por aqui.
SEM_RELACAO = {
    "conteúdo adulto": ("xvideos.com", "xnxx.com", "pornhub.com", "xhamster.com"),
    "fórum ou perguntas e respostas": (
        "reddit.com", "stackoverflow.com", "zhihu.com", "quora.com", "answers.com", "brainly.com",
        "chegg.com", "quizlet.com", "justanswer.com", "answers.microsoft.com",
        "social.msdn.microsoft.com", "community.ebay.com", "paypal-community.com",
        "minecraftforum.net", "jlaforums.com"),
    "entretenimento": ("imdb.com", "fandom.com", "genius.com", "goodreads.com", "mlb.com", "nfl.com",
                       "espn.com", "yardbarker.com", "minecraft.net", "encyclopedia-titanica.org"),
    "comércio": ("amazon.com", "walmart.com", "ebay.com", "flipkart.com", "zillow.com", "autotrader.com",
                 "edmunds.com", "tesla.com", "bentleymotors.com", "chanel.com", "chapelhats.com",
                 "southwest.com", "allegiantair.com", "indeed.com", "humana.com", "leafhome.com",
                 "evanwilliams.com", "regus.com", "shutterstock.com", "realhotelsgroup.com",
                 "hoteljardimviana.pt", "ludvigsenmortuary.com", "drugs.com", "electricityforum.com",
                 "jalbum.net"),
    "receitas": ("allrecipes.com", "foodnetwork.com"),
    "dicionário ou enciclopédia": ("merriam-webster.com", "britannica.com", "dictionary.com",
                                   "en.wikipedia.org", "en.m.wikipedia.org"),
}
# Rótulo que a busca estadual pôs no campo município (defeito B1 do Buscador 2).
ROTULOS = ("saude", "defesa_civil")
SUFIXOS_OFICIAIS = (".gov.br", ".leg.br", ".mp.br", ".jus.br", ".def.br", ".mil.br")
REDIRECIONAMENTO = "redirecionamento não resolvido (Google News)"


def _host(url) -> str:
    try:
        return (urllib.parse.urlsplit(str(url or "")).hostname or "").lower()
    except ValueError:
        return ""


def _uf_do_host(url, host, resolver) -> str | None:
    """UF dona de um domínio .gov.br (municipal pelo resolvedor, estadual pelo rótulo). Pura."""
    from municipio_do_dominio import UFS
    if not host.endswith(".gov.br"):
        return None
    dono = resolver(url)
    if dono:
        return str(dono.get("uf") or "").upper() or None
    partes = host.split(".")
    return partes[-3].upper() if len(partes) >= 3 and partes[-3] in UFS else None


def motivo_de_link_falso(url, uf=None, municipio=None, resolver=None) -> str | None:
    """Por que este endereço não tem relação com o tema, ou None. Função pura dado o resolvedor."""
    from pistas import REDIRECIONADORES
    from municipio_do_dominio import UFS
    if resolver is None:
        from municipio_do_dominio import municipio_de as resolver
    u, h = str(url or ""), _host(url)
    if any(r in u for r in REDIRECIONADORES):
        return REDIRECIONAMENTO
    for categoria, hosts in SEM_RELACAO.items():
        if any(h == x or h.endswith("." + x) for x in hosts):
            return "sem relação com o tema: " + categoria
    if municipio in ROTULOS and h and not h.endswith(SUFIXOS_OFICIAIS):
        return "sem relação com o tema: a busca por rótulo devolveu site sem município"
    uf = str(uf or "").upper()
    if uf.lower() in UFS:
        dono = _uf_do_host(u, h, resolver)
        if dono and dono != uf:
            return f"domínio de outra UF ({dono})"
    return None


def _chave(municipio, uf, url) -> tuple:
    return (str(municipio or "").strip().lower(), str(uf or "").strip().upper(), str(url or "").strip())


ERRATA_POR_CHAVE = {_chave(m, u, url): mot for m, u, url, mot in ERRATAS}
CONFERIDA_POR_CHAVE = {_chave(m, u, url): t for m, u, url, t in CONFERIDAS}


def aplicar_erratas(decisoes: list) -> list:
    """Errata por linha nas decisões que promoveram. Devolve as chaves tocadas. Muda a lista."""
    tocadas = []
    for d in decisoes:
        k = _chave(d.get("municipio"), d.get("uf"), d.get("url"))
        if d.get("promove") and k in ERRATA_POR_CHAVE:
            motivo = ERRATA_POR_CHAVE[k]
            d["errata"] = {"em": EM, "por": POR, "motivo": motivo,
                           "antes": {"promove": True, "motivo": d.get("motivo"),
                                     "categoria": d.get("categoria")}}
            d["promove"], d["motivo"] = False, "errata: " + motivo
            tocadas.append(k)
        elif k in CONFERIDA_POR_CHAVE and d.get("promove") and not d.get("conferida"):
            d["conferida"] = {"em": EM, "por": POR, "resultado": "mantida",
                              "trecho": CONFERIDA_POR_CHAVE[k]}
    return tocadas


def retirar_do_banco(municipios: list, pontos: list) -> tuple:
    """Registros sustentados por confirmação falsa saem do banco e do mapa. Devolve (fica, sai, pontos).

    `nao_verificado` não é confirmação (vale 0 e diz que não verificou): fica."""
    sai = [r for r in municipios if _chave(r.get("nome"), r.get("uf"), r.get("url")) in ERRATA_POR_CHAVE
           and r.get("categoria") != "nao_verificado"]
    tiradas = {(r["nome"], r["uf"], r["categoria"]) for r in sai}
    fica = [r for r in municipios if r not in sai]
    pontos_fica = [p for p in pontos if (p.get("nome"), p.get("uf"), p.get("categoria")) not in tiradas]
    return fica, sai, pontos_fica


def separar(itens: list, url_de, resolver=None) -> tuple:
    """(fica, sai com motivo) para uma lista de pistas ou decisões. Pura dado o resolvedor."""
    fica, sai = [], []
    for it in itens:
        k = _chave(it.get("municipio"), it.get("uf"), url_de(it))
        if k in ERRATA_POR_CHAVE and not it.get("promove") and "errata" not in it:
            sai.append((it, "confirmação desfeita por errata: " + ERRATA_POR_CHAVE[k]))
            continue
        m = None if it.get("promove") or "errata" in it else motivo_de_link_falso(
            url_de(it), it.get("uf"), it.get("municipio"), resolver)
        (sai.append((it, m)) if m else fica.append(it))
    return fica, sai


def _url_da_pista(p):
    return p.get("url_final") or p.get("url")


def executar(aplicar: bool) -> int:
    from coletores_base import ler, gravar
    import pistas as porta
    decisoes_doc = ler("promocoes_automaticas.json")
    decisoes = decisoes_doc["decisoes"]
    tocadas = aplicar_erratas(decisoes)
    municipios, pontos = ler("municipios.json"), ler("pontos_mapa.json")
    municipios_fica, registros_sai, pontos_fica = retirar_do_banco(municipios, pontos)
    decisoes_fica, decisoes_sai = separar(decisoes, lambda d: d.get("url"))
    filas = {}
    for f in sorted((RAIZ / "data").glob("pistas_*.json")):
        doc = ler(f.name)
        if f.name == porta.ARQUIVO_DE_REJEITADAS or not isinstance((doc or {}).get("pistas"), list):
            continue
        fica, sai = separar(doc["pistas"], _url_da_pista)
        if sai:
            filas[f.name] = (doc, fica, sai)

    motivos = Counter()
    for _, sai in [(None, decisoes_sai)] + [(None, v[2]) for v in filas.values()]:
        motivos.update(m.split(" (")[0] if m.startswith("domínio") else m for _, m in sai)
    print(f"erratas aplicadas: {len(tocadas)} decisão(ões) · registros retirados do banco: "
          f"{len(registros_sai)} ({', '.join(r['nome'] + '/' + r['uf'] for r in registros_sai)})")
    print(f"decisões retiradas: {len(decisoes_sai)} · pistas retiradas: "
          + ", ".join(f"{k} {len(v[2])}" for k, v in filas.items()))
    for m, n in motivos.most_common():
        print(f"   {n:6d}  {m}")
    if not aplicar:
        return 0

    ARQUIVO.mkdir(parents=True, exist_ok=True)
    def guardar(nome, obj):
        (ARQUIVO / nome).write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8", newline="\n")
    guardar("registros_retirados.json", {"_governanca": __doc__.split("\n")[0], "em": EM,
                                         "registros": registros_sai})
    guardar("decisoes_retiradas.json", {"em": EM, "itens": [{"motivo": m, "decisao": d} for d, m in decisoes_sai]})
    for nome, (_, _, sai) in filas.items():
        guardar(nome.replace(".json", "_retiradas.json"),
                {"em": EM, "fila": nome, "itens": [{"motivo": m, "pista": p} for p, m in sai]})

    # A recusa pela porta: uma linha por URL; o redirecionamento, agregado por UF (ver docstring).
    rej = ler(porta.ARQUIVO_DE_REJEITADAS) or {"rejeitadas": []}
    memoria = {porta.ARQUIVO_DE_REJEITADAS: rej}
    ler_m, gravar_m = (lambda n: memoria.get(n)), (lambda n, o: memoria.__setitem__(n, o))
    vistas, redir = set(), Counter()
    todas = [(d, m, "promocoes_automaticas.json") for d, m in decisoes_sai] + \
            [(p, m, nome) for nome, v in filas.items() for p, m in v[2]]
    for it, m, de in todas:
        url = str(_url_da_pista(it) or "")
        if m == REDIRECIONAMENTO:
            redir[(de, str(it.get("uf") or "").upper() or "sem UF")] += 1
            continue
        k = (url, it.get("municipio"), it.get("uf"))
        if k in vistas:
            continue
        vistas.add(k)
        porta.rejeitar(dict(it, url_final=url), ORIGEM, f"limpeza 26/10/2026: {m}",
                       ler_fn=ler_m, gravar_fn=gravar_m)
    for (de, uf), n in sorted(redir.items()):
        porta.rejeitar({"url_final": "", "uf": uf, "origem": de}, ORIGEM,
                       f"limpeza 26/10/2026: {REDIRECIONAMENTO}: {n} item(ns) de {de}, lista em "
                       f"arquivo/limpeza_26-10-2026/", ler_fn=ler_m, gravar_fn=gravar_m)
    gravar(porta.ARQUIVO_DE_REJEITADAS, memoria[porta.ARQUIVO_DE_REJEITADAS])

    decisoes_doc["decisoes"] = decisoes_fica
    gravar("promocoes_automaticas.json", decisoes_doc)
    for nome, (doc, fica, _) in filas.items():
        doc["pistas"] = fica
        gravar(nome, doc)
    gravar("municipios.json", municipios_fica)
    gravar("pontos_mapa.json", pontos_fica)
    print("aplicado.")
    return 0


def _autoteste() -> int:
    from _casos import ok_de
    falhas = []
    ok = ok_de(falhas)
    sem_dono = lambda u: None
    taio = lambda u: {"nome": "Taió", "uf": "SC"} if "taio" in u else None
    ok("Google News é redirecionamento", motivo_de_link_falso(
        "https://news.google.com/rss/articles/X", "SP", "Leme", sem_dono) == REDIRECIONAMENTO)
    ok("Reddit cai por categoria", "fórum" in (motivo_de_link_falso(
        "https://www.reddit.com/r/x", "AC", "saude", sem_dono) or ""))
    ok("rótulo com site comercial desconhecido cai", "rótulo" in (motivo_de_link_falso(
        "https://loja-qualquer.com/x", "AL", "saude", sem_dono) or ""))
    ok("rótulo com domínio oficial fica", motivo_de_link_falso(
        "https://www.saude.al.gov.br/x", "AL", "saude", sem_dono) is None)
    ok("domínio estadual de outra UF cai", motivo_de_link_falso(
        "https://defesacivil.es.gov.br/p.pdf", "MG", "Medeiros", sem_dono) == "domínio de outra UF (ES)")
    ok("domínio municipal de outra UF cai", motivo_de_link_falso(
        "https://defesacivil.taio.sc.gov.br/p.pdf", "PR", "Toledo", taio) == "domínio de outra UF (SC)")
    ok("domínio da própria UF fica", motivo_de_link_falso(
        "https://defesacivil.taio.sc.gov.br/p.pdf", "SC", "Taió", taio) is None)
    ok("jornal regional fica", motivo_de_link_falso(
        "https://g1.globo.com/sc/x", "SC", "Taió", sem_dono) is None)
    ok("wikipedia em português fica (não é dicionário da lista)", motivo_de_link_falso(
        "https://pt.wikipedia.org/wiki/El_Ni%C3%B1o", "SP", "Leme", sem_dono) is None)

    url_t = ERRATAS[2][2]
    decs = [{"promove": True, "municipio": "Rio do Oeste", "uf": "SC", "url": url_t, "motivo": "x",
             "categoria": "plano"},
            {"promove": True, "municipio": "Taió", "uf": "SC", "url": url_t, "categoria": "plano"},
            {"promove": False, "municipio": "Rio do Oeste", "uf": "SC", "url": url_t}]
    tocadas = aplicar_erratas(decs)
    ok("errata só na decisão do par falso", len(tocadas) == 1 and decs[0]["promove"] is False
       and decs[0]["errata"]["antes"]["promove"] is True and decs[1]["promove"] is True)
    fica, sai = separar(decs, lambda d: d.get("url"), taio)
    ok("decisão com errata fica no registro; recusa antiga do par falso sai; a de Taió fica",
       decs[0] in fica and decs[1] in fica and [d for d, _ in sai] == [decs[2]])
    mun = [{"nome": "Cubatão", "uf": "SP", "url": ERRATAS[3][2], "categoria": "plano_elaboracao"},
           {"nome": "Rio Branco", "uf": "AC", "url": ERRATAS[7][2], "categoria": "nao_verificado"},
           {"nome": "Leme", "uf": "SP", "url": "https://leme.sp.gov.br/p", "categoria": "plano_antigo"}]
    pts = [{"nome": r["nome"], "uf": r["uf"], "categoria": r["categoria"]} for r in mun]
    f, s, p = retirar_do_banco(mun, pts)
    ok("banco: sai a confirmação falsa; não verificado e plano verdadeiro ficam",
       [r["nome"] for r in s] == ["Cubatão"] and len(f) == 2 and len(p) == 2)
    c = aplicar_erratas([{"promove": True, "municipio": "Coronel Macedo", "uf": "SP", "url": CONFERIDAS[0][2]}])
    ok("conferida e mantida não recebe errata", c == [])

    import dis
    nomes = {i.argval for fn in (motivo_de_link_falso, aplicar_erratas, retirar_do_banco, separar)
             for i in dis.get_instructions(fn) if i.opname in ("LOAD_GLOBAL", "LOAD_NAME", "LOAD_ATTR", "IMPORT_NAME")}
    ok("trava estrutural: funções puras não escrevem nem vão à rede",
       not ({"gravar", "gravar_em", "write_text", "rejeitar", "buscar", "urlopen"} & nomes))
    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas else "✓ AUTOTESTE OK — sem rede e sem escrita.")
    return 1 if falhas else 0


if __name__ == "__main__":
    if "--autoteste" in sys.argv:
        raise SystemExit(_autoteste())
    raise SystemExit(executar("--aplicar" in sys.argv))
