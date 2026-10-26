#!/usr/bin/env python3
"""
seguir_pistas.py — o seguidor do Buscador 2 (26/10/2026)
========================================================
Substitui o seguidor de 22/09/2026 (§159), que só seguia notícia A/B por três rotas e deixava na fila
o resto: link do Google News nunca aberto, página inicial no lugar do documento, domínio de empresa,
o município errado. As regras vivem em `buscador2.py`; aqui elas são aplicadas à fila que já existe.

Para cada pista a seguir (B6: nível A primeiro, depois domínio de prefeitura com termo de plano):
  · rótulo de setor no campo município → fecha (B1);
  · redirecionador → abre; resolvido, a URL final entra como pista nova pela porta; não resolvido,
    fecha com "redirecionamento não resolvido" (B2);
  · fora da entrada (empresa, rede social, outro ente, outra UF) → fecha com o motivo (B3, B8);
  · página oficial que não é documento → um nível no mesmo domínio (B4), mapa do site quando
    ilegível (B9), `site:` + plano citado quando é notícia oficial sem link (B7);
  · notícia de veículo (rota) → os links que ela dá para o domínio oficial do ente; Querido Diário
    quando o município tem diário indexado.
E o documento oficial com termo de plano que o juiz não conseguiu ler (`inacessivel_persistente`)
volta à fila noutra noite, até três vezes (B5, B10).

Nada aqui julga, pontua ou apaga: a pista fechada continua no arquivo com o status anterior e o
motivo, e a recusa fica contada em `data/pistas_rejeitadas.json`. Pista nova só pela porta
(`scripts/pistas.gravar_lote`); o estado das pistas existentes, por `scripts/pistas.sincronizar`.

USO   python3 seguir_pistas.py [--limite 60] [--refazer-dias 7]
      python3 seguir_pistas.py --restante          # o que sobrou para a rodada seguinte (sem rede)
      python3 seguir_pistas.py --autoteste
"""
import argparse, collections, datetime, hashlib, json, re, sys, urllib.parse
import buscador2 as b2
from coletores_base import ler, gravar, rodar_autoteste, hoje_editorial, ua_de

STATUS_PENDENTE = "pista — na fila, aguardando busca dirigida e juiz"
PREFIXO_FECHADA = "fechada — Buscador 2: "
TERMOS_QD = '"plano de contingência" OR plancon OR "plano municipal de proteção e defesa civil"'
QD_DESDE = "2025-10-01"
MAX_POR_ROTA = 4
BLOCO = 200   # URLs abertas entre duas gravações


def _id(ibge, url, trecho):
    return hashlib.sha1(f"{ibge or ''}|{url or ''}|{(trecho or '')[:500]}".encode("utf-8")).hexdigest()[:10]


def _url(p):
    return str(p.get("url_final") or p.get("url") or "")


def _data(s):
    try:
        return datetime.datetime.strptime(s, "%d/%m/%Y").date()
    except (TypeError, ValueError):
        return None


def candidatos_qd(pista, consultar):
    """Edições do Querido Diário do código IBGE da pista com os termos do plano (rota da notícia)."""
    params = urllib.parse.urlencode({"territory_ids": pista.get("ibge"), "querystring": TERMOS_QD,
                                     "published_since": QD_DESDE, "excerpt_size": 500,
                                     "number_of_excerpts": 1, "size": MAX_POR_ROTA})
    d = json.loads(consultar(params).decode("utf-8", "replace"))
    return [(g["url"], " ".join(((g.get("excerpts") or [""])[0]).split())[:600])
            for g in d.get("gazettes", [])[:MAX_POR_ROTA] if g.get("url") and g.get("excerpts")]


def e_rota(p) -> bool:
    return (str(p.get("status") or "").startswith("rota") or p.get("entrada") == "rota"
            or p.get("origem") == "imprensa")


def a_seguir(p: dict, d_hoje, refazer_dias: int = 7, reprocessar: bool = False) -> bool:
    """A pista entra nesta rodada do seguidor? Um critério só para `seguir()` e `restantes()`. Pura.

    Na noite, só o que chegou na janela de `refazer_dias` (a fila antiga é do reprocessamento, que
    corre pela válvula em lotes): sem isso o restante da noite seria a fila inteira, e a reserva
    redispararia o elo até as 08:00. No reprocessamento, toda pista que o Buscador 2 ainda não viu."""
    status = str(p.get("status") or "")
    if not (status.startswith(("pista", "pendente_confirmacao_documento")) or e_rota(p)) \
            or "inacessivel_persistente" in status:
        return False
    if reprocessar:
        if p.get("buscador2_em"):
            return False
    elif str(p.get("registrado_em") or "")[:10] < (d_hoje - datetime.timedelta(days=refazer_dias)).isoformat():
        return False
    if str(p.get("origem_do_coletor") or p.get("origem") or "").startswith(("seguimento", "buscador2")):
        return False   # filho do seguidor: um nível só (B4)
    url = _url(p)
    if b2.e_documento(url) and not b2.eh_redirecionador(url) and not e_rota(p):
        return not b2.classe_da_pista(p)[0]   # documento: o juiz lê; só se segue para fechar o que está fora
    s = p.get("seguimento") or {}
    visto = _data(s.get("data"))
    if visto and (d_hoje - visto).days < refazer_dias and not s.get("falhas"):
        return False
    return True


def retentar(p: dict, d_hoje) -> bool:
    """Documento oficial com termo de plano que o juiz não leu volta à fila? (B5, B10) Pura."""
    if "inacessivel_persistente" not in str(p.get("status") or "") or not b2.volta_a_fila(p):
        return False
    feitas = p.get("retentativas_buscador2") or []
    if len(feitas) >= b2.TENTATIVAS_DO_BUSCADOR:
        return False
    devida = p.get("retentar_buscador2_em")
    return not devida or devida <= d_hoje.isoformat()


def restantes(fila: dict, hoje: str, refazer_dias: int = 7) -> int:
    """O que sobrou para a rodada seguinte: pistas a seguir que a noite ainda não tocou. Maior que zero,
    o elo grava `.parcial` e a reserva o redispara (fila reentrante). Quem já foi seguido hoje não conta."""
    d_hoje = datetime.datetime.strptime(hoje, "%d/%m/%Y").date()
    return sum(1 for p in fila.get("pistas") or []
               if a_seguir(p, d_hoje, refazer_dias) and p.get("buscador2_em") != d_hoje.isoformat())


def seguir(fila, hoje, abrir=None, abrir_final=None, consultar_qd_=None, buscar_web_=None,
           cobertura_qd=frozenset(), limite=60, refazer_dias=7, reprocessar=False, parar=None):
    """Segue as pistas na ordem do B6, com até `limite` URLs abertas na rede (fechar o que está fora da
    entrada não abre nada e não conta). Planeja só em memória e devolve a estatística:
    `novas_lista` vai à porta, `fechadas_lista` vai às rejeitadas, e o estado das existentes
    (`seguimento`, status de fechada ou de volta à fila) fica nos próprios dicionários da fila.

    `abrir(url) -> bytes` e `abrir_final(url) -> url` são a rede, injetadas (o autoteste não usa)."""
    d_hoje = datetime.datetime.strptime(hoje, "%d/%m/%Y").date()
    hoje_iso = d_hoje.isoformat()
    pistas = fila["pistas"]
    existentes = {b2.url_normalizada(_url(p)) for p in pistas}
    est = {"seguidas": 0, "candidatos": 0, "novas": 0, "resolvidas": 0, "retentadas": 0, "lacunas": 0,
           "rotas_falharam": 0, "por_via": collections.Counter(), "motivos": collections.Counter(),
           "novas_lista": [], "fechadas_lista": []}

    def fechar(p, motivo):
        p["status_anterior"] = p.get("status")
        p["status"] = PREFIXO_FECHADA + motivo
        p["fechada_em"] = hoje_iso
        est["fechadas_lista"].append((p, motivo))
        est["motivos"][motivo.split(" (")[0].split(":")[0]] += 1

    def nova(p, url, ancora, via):
        n = b2.url_normalizada(url)
        if not n or n in existentes:
            return 0
        existentes.add(n)
        # o nome do arquivo entra no trecho com espaços: é nele que a porta lê o tipo (plano, decreto)
        arquivo = urllib.parse.unquote(urllib.parse.urlsplit(url).path.rsplit("/", 1)[-1])
        ancora = " ".join(x for x in (ancora, re.sub(r"[-_.+]+", " ", arquivo)) if x).strip()
        item = {"municipio": p.get("municipio"), "uf": p.get("uf"), "ibge": p.get("ibge"),
                "alvo": p.get("alvo"), "url": url, "titulo": ancora or p.get("titulo"),
                "trecho": ancora or p.get("trecho") or url, "data": hoje, "origem": "buscador2",
                "via_buscador2": via, "nivel": p.get("nivel") or p.get("nivel_confianca"),
                "pista_origem": p.get("id")}
        item["id"] = _id(item["ibge"], url, item["trecho"])
        est["novas_lista"].append(item)
        return 1

    rede = [0]

    def precisa_de_rede(p, url):
        if b2.rotulo_no_lugar_do_municipio(p.get("municipio")):
            return False
        if b2.eh_redirecionador(url) or (not p.get("url_final") and b2.eh_redirecionador(p.get("url"))):
            return True
        classe = b2.classe_da_pista(p)[0]
        return (bool(classe) or e_rota(p)) and not (b2.e_documento(url) and not e_rota(p))

    for p in sorted((p for p in pistas if a_seguir(p, d_hoje, refazer_dias, reprocessar)), key=b2.prioridade):
        if parar and parar[0]:
            break   # o prazo do elo chegou (SIGINT do invólucro): grava o que já se fez
        url = _url(p)
        if precisa_de_rede(p, url):
            if rede[0] >= limite:
                continue
            rede[0] += 1
        est["seguidas"] += 1
        p["buscador2_em"] = hoje_iso
        if b2.rotulo_no_lugar_do_municipio(p.get("municipio")):
            fechar(p, f"rótulo de setor no campo município ({p.get('municipio')}) (B1)")
            continue
        if b2.eh_redirecionador(url) or (not p.get("url_final") and b2.eh_redirecionador(p.get("url"))):
            final, como = b2.resolver(p.get("url"), abrir=abrir_final, veiculo=p.get("veiculo_dominio"),
                                      titulo=p.get("titulo"), buscar_web=buscar_web_)
            if not final:
                fechar(p, "redirecionamento não resolvido (B2)")
                continue
            est["resolvidas"] += 1
            novas = nova(p, final, p.get("titulo"), "B2")
            fechar(p, f"redirecionamento resolvido (B2): segue como pista nova pela porta ({b2.host_de(final)})")
            est["novas"] += novas
            continue
        classe, motivo = b2.classe_da_pista(p)
        if not classe and not e_rota(p):
            fechar(p, f"fora da entrada (B3/B8): {motivo}")
            continue
        cands, falhas, via, lacuna = [], [], "", ""
        if b2.e_documento(url) and not e_rota(p):
            via = "documento"
        else:
            try:
                corpo = abrir(url) if abrir else None
            except Exception as e:  # noqa: BLE001 — recusa e queda viram falha nomeada, nunca contorno
                corpo = None
                falhas.append(f"pagina: {type(e).__name__}")
            if corpo is not None:
                r = b2.candidatos_da_pagina(p, corpo, abrir=abrir, buscar_web=buscar_web_, hoje_iso=hoje_iso)
                cands, via, lacuna = r["candidatos"], r["via"], r["lacuna"]
        if e_rota(p) and consultar_qd_ and str(p.get("ibge")) in cobertura_qd:
            try:
                cands += candidatos_qd(p, consultar_qd_)
            except Exception as e:  # noqa: BLE001
                falhas.append(f"querido_diario: {type(e).__name__}")
        n_novas = sum(nova(p, u, a, via) for u, a in cands)
        est["candidatos"] += len(cands)
        est["novas"] += n_novas
        est["rotas_falharam"] += len(falhas)
        est["lacunas"] += bool(lacuna)
        est["por_via"][via or "falha"] += 1
        p["seguimento"] = {"data": hoje, "via": via, "candidatos": len(cands), "pistas_novas": n_novas,
                           "falhas": falhas, **({"lacuna": lacuna} if lacuna else {})}

    for p in pistas:
        if est["retentadas"] >= limite or not retentar(p, d_hoje):
            continue
        feitas = p.setdefault("retentativas_buscador2", [])
        feitas.append(hoje_iso)
        prox = b2.proxima_tentativa(len(feitas), d_hoje)
        p["status_anterior"] = p.get("status")
        p["status"] = STATUS_PENDENTE
        p["proxima_tentativa_em"] = hoje_iso
        p["retentar_buscador2_em"] = prox.isoformat() if prox else b2.lacuna_datada("documento não lido", hoje_iso)
        est["retentadas"] += 1
    est["rede"] = rede[0]
    return est


def gravar_rodada(fila, est, ler_fn=ler, gravar_fn=gravar) -> dict:
    """Leva a rodada ao disco pela porta: pistas novas (gravar_lote), estado das existentes
    (sincronizar) e as fechadas como recusa contada (rejeitar_lote). ESCREVE."""
    from scripts.pistas import gravar_lote, sincronizar, rejeitar_lote
    balanco = gravar_lote(est["novas_lista"], origem="buscador2", ler_fn=ler_fn, gravar_fn=gravar_fn)
    novos = {n["id"] for n in est["novas_lista"]}
    tocadas = {"pistas": [p for p in fila["pistas"] if p.get("id") not in novos
                          and (p.get("buscador2_em") or p.get("retentativas_buscador2"))]}
    sincronizar("pistas_imprensa.json", tocadas, origem="buscador2", ler_fn=ler_fn, gravar_fn=gravar_fn)
    rejeitar_lote([(p, "buscador2", m) for p, m in est["fechadas_lista"]], ler_fn=ler_fn, gravar_fn=gravar_fn)
    return balanco


# ------------------------------------------------------------------ compatibilidade: modo paralelo J18
# `scripts/rejulgar_decisoes_do_juiz.py` (rodada J18, #1202) importa daqui o seguidor antigo da notícia e as
# três funções "_18". Ficam como estavam até a J18 passar a usar `buscador2.py` (pedido no LOTES); a noite
# não as chama.
from monitorar_imprensa_regional import parece_fonte_oficial  # noqa: E402
RE_LINK = re.compile(r'<a\s[^>]*href=["\']([^"\'#]+)["\'][^>]*>(.*?)</a>', re.I | re.S)
RE_SINAL_ATO = re.compile(r"decreto|\blei\b|portaria|plancon|plano|conting|diario|\.pdf", re.I)


def _limpo(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html or "")).strip()


def buscar_html(url, timeout=20):
    """HTML cru (os links importam). Tolerante: None em falha."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": ua_de("seguir pistas")})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            if "pdf" in (r.headers.get("Content-Type") or "").lower():
                return None
            raw = r.read(1_500_000)
        return raw.decode("utf-8", errors="ignore")
    except Exception:  # noqa: BLE001
        return None


# ------------------------------------------------------------------ rota 1: links da notícia
def candidatos_da_noticia(pista, html):
    if not html:
        return []
    out, vistos = [], set()
    for href, texto in RE_LINK.findall(html):
        url = urllib.parse.urljoin(pista.get("url") or "", href.strip())
        if not url.startswith("http") or url in vistos or url == pista.get("url"):
            continue
        ancora = _limpo(texto)[:200]
        if not parece_fonte_oficial(url):
            continue
        if not (RE_SINAL_ATO.search(url) or RE_SINAL_ATO.search(ancora)):
            continue
        vistos.add(url)
        out.append({"url": url, "trecho": ancora or url, "titulo": ancora, "rota": "seguimento_link_noticia"})
        if len(out) >= MAX_POR_ROTA:
            break
    return out


# ------------------------------------------------------------------ codebook 1.8 (modo paralelo, 26/10/2026)
# Só a rodada paralela J18 usa estas três funções; a rodada da noite não muda.
EXTENSOES_DE_ATO_18 = (".pdf", ".doc", ".docx", ".odt", ".rtf")
RE_ATO_18 = re.compile(r"decreto|\blei\b|portaria|plancon|instru[çc][ãa]o", re.I)
RECUSAS_HTTP_18 = (401, 403, 429, 451)
ESPERAS_18 = (0, 30, 120)


def seguir_agregador_18(pista, resolver, buscar_html_=buscar_html):
    """B2: o link do agregador é resolvido até a matéria e só os links oficiais citados nela viram pista
    (rota 1). Devolve (candidatos, como); sem resolução, ([], "nao_resolvido") e o chamador conta a
    tentativa — na segunda, fecha."""
    final, como = resolver(pista)
    if not final:
        return [], "nao_resolvido"
    return candidatos_da_noticia(dict(pista, url=final), buscar_html_(final)), como


def documentos_da_pagina_18(url, html):
    """B4: página oficial que fala do plano → os links do MESMO domínio para PDF ou ato, um nível."""
    host = urllib.parse.urlparse(url).netloc.lower()
    return [c for c in candidatos_da_noticia({"url": url}, html)
            if urllib.parse.urlparse(c["url"]).netloc.lower() == host
            and (c["url"].lower().split("?")[0].endswith(EXTENSOES_DE_ATO_18)
                 or RE_ATO_18.search(c["url"] + " " + c["titulo"]))]


def ler_com_espera_18(url, buscar, esperas=ESPERAS_18, dormir=None):
    """B5: nova tentativa com espera crescente e registro por arquivo. 401/403/429/451 é recusa real:
    registra e não insiste. `buscar` pode levantar; texto vazio conta como tentativa falha."""
    import time
    dormir = dormir or time.sleep
    registro = {"url": url, "tentativas": 0, "resultado": "inacessivel", "erros": []}
    for espera in esperas:
        dormir(espera)
        registro["tentativas"] += 1
        try:
            texto = buscar(url)
        except Exception as e:  # noqa: BLE001
            codigo = getattr(e, "code", None) or getattr(getattr(e, "response", None), "status_code", None)
            registro["erros"].append(f"{type(e).__name__} {codigo or ''}".strip())
            if codigo in RECUSAS_HTTP_18:
                registro["resultado"] = f"recusa_{codigo}"
                return None, registro
            continue
        if texto:
            registro["resultado"] = "lido"
            return texto, registro
    return None, registro



def autoteste():
    import buscador2
    S = {"PR": {"palotina": "Palotina"}, "SC": {"taio": "Taió", "blumenau": "Blumenau"},
         "_por_ibge": {"4117909": ("Palotina", "PR"), "4217808": ("Taió", "SC"), "4202404": ("Blumenau", "SC")}}
    buscador2._SLUGS = S
    base = lambda: {"pistas": [dict(x, registrado_em=x.get("registrado_em", "2026-10-25")) for x in [
        {"id": "n1", "municipio": "Palotina", "uf": "PR", "ibge": "4117909", "alvo": "4117909",
         "url": "https://jornal.com.br/palotina-plano", "status": "rota — notícia", "entrada": "rota",
         "nivel": "B"},
        {"id": "o1", "municipio": "Taió", "uf": "SC", "ibge": "4217808", "alvo": "4217808",
         "url": "https://taio.sc.gov.br/defesa-civil", "status": STATUS_PENDENTE, "nivel": "C"},
        {"id": "e1", "municipio": "Taió", "uf": "SC", "ibge": "4217808", "alvo": "4217808",
         "url": "https://www.cristalconsult.com.br/plano.pdf", "status": STATUS_PENDENTE, "nivel": "C"},
        {"id": "g1", "municipio": "Taió", "uf": "SC", "ibge": "4217808", "alvo": "4217808",
         "url": "https://news.google.com/rss/articles/CBMiAU_yqLopaco", "status": STATUS_PENDENTE, "nivel": "A"},
        {"id": "r1", "municipio": "defesa_civil", "uf": "AC", "alvo": "AC",
         "url": "https://www.speedtest.net/", "status": STATUS_PENDENTE, "nivel": "C"},
        {"id": "d1", "municipio": "Blumenau", "uf": "SC", "ibge": "4202404", "alvo": "4202404",
         "url": "https://blumenau.sc.gov.br/plancon-2026.pdf", "nivel": "C",
         "status": "pista — inacessivel_persistente: 5 tentativas sem leitura do documento"},
        {"id": "v1", "municipio": "Taió", "uf": "SC", "ibge": "4217808", "alvo": "4217808", "nivel": "C",
         "url": "https://www.grupoavanteservicos.com.br/x", "status": STATUS_PENDENTE,
         "registrado_em": "2026-09-01"}]]}
    NOTICIA = (b'<a href="https://palotina.pr.gov.br/arquivos/plancon-2026.pdf">PLANCON 2026</a>'
               b'<a href="https://facebook.com/palotina">Facebook</a>')
    PAGINA = (b"<html><body>" + b"Defesa Civil de Taio " * 20 +
              b'<a href="/arquivos/plano-de-contingencia-2026.pdf">Plano</a><a href="/turismo">Turismo</a></body></html>')
    abrir = lambda u: NOTICIA if "jornal" in u else PAGINA
    status = lambda f, i: next(p for p in f["pistas"] if p["id"] == i)["status"]

    def t_rota_e_b4_viram_pistas_novas():
        f = base(); e = seguir(f, "26/10/2026", abrir=abrir, abrir_final=lambda u: u)
        urls = sorted(n["url"] for n in e["novas_lista"])
        return urls == ["https://palotina.pr.gov.br/arquivos/plancon-2026.pdf",
                        "https://taio.sc.gov.br/arquivos/plano-de-contingencia-2026.pdf"] \
            and all(n["origem"] == "buscador2" for n in e["novas_lista"])

    def t_lixo_cai_com_motivo():
        f = base(); e = seguir(f, "26/10/2026", abrir=abrir, abrir_final=lambda u: u)
        return (status(f, "e1").startswith(PREFIXO_FECHADA + "fora da entrada (B3/B8): domínio não oficial")
                and status(f, "r1").startswith(PREFIXO_FECHADA + "rótulo de setor")
                and status(f, "g1") == PREFIXO_FECHADA + "redirecionamento não resolvido (B2)"
                and len(e["fechadas_lista"]) == 3
                and next(p for p in f["pistas"] if p["id"] == "e1")["status_anterior"] == STATUS_PENDENTE)

    def t_redirecionador_resolvido_vira_pista_nova():
        f = base(); e = seguir(f, "26/10/2026", abrir=abrir, abrir_final=lambda u: "https://taio.sc.gov.br/plancon.pdf")
        return e["resolvidas"] == 1 and any(n["url"] == "https://taio.sc.gov.br/plancon.pdf" for n in e["novas_lista"]) \
            and status(f, "g1").startswith(PREFIXO_FECHADA + "redirecionamento resolvido")

    def t_b6_ordem_nivel_a_primeiro():
        abertas = []
        f = base(); seguir(f, "26/10/2026", abrir=lambda u: (abertas.append(u), PAGINA)[1],
                           abrir_final=lambda u: (abertas.append(u), u)[1], limite=1)
        return set(abertas) == {"https://news.google.com/rss/articles/CBMiAU_yqLopaco"}   # g1 é nível A

    def t_b10_documento_volta_ate_tres_vezes():
        f = base(); d = next(p for p in f["pistas"] if p["id"] == "d1")
        seguir(f, "26/10/2026", abrir=abrir, abrir_final=lambda u: u)
        volta1 = d["status"] == STATUS_PENDENTE and d["retentar_buscador2_em"] == "2026-10-27"
        d["status"] = "pista — inacessivel_persistente: 6"
        seguir(f, "26/10/2026", abrir=abrir)                 # antes da data: não volta
        cedo = d["status"].startswith("pista — inacessivel")
        for dia in ("27/10/2026", "29/10/2026", "30/11/2026", "30/12/2026"):
            d["status"] = "pista — inacessivel_persistente: x"
            seguir(f, dia, abrir=abrir)
        return volta1 and cedo and len(d["retentativas_buscador2"]) == 3 and "inacessivel" in d["status"]

    def t_fila_antiga_e_do_reprocessamento_e_limite_e_de_rede():
        f = base(); seguir(f, "26/10/2026", abrir=abrir, abrir_final=lambda u: u)
        noite_nao_toca = status(f, "v1") == STATUS_PENDENTE
        f2 = base(); e2 = seguir(f2, "26/10/2026", abrir=abrir, abrir_final=lambda u: u, limite=1,
                                 reprocessar=True)
        tocadas = {p["id"] for p in f2["pistas"] if p.get("buscador2_em")}
        e3 = seguir(f2, "26/10/2026", abrir=abrir, abrir_final=lambda u: u, reprocessar=True)
        return (noite_nao_toca and status(f2, "v1").startswith(PREFIXO_FECHADA)
                and tocadas == {"g1", "e1", "r1", "v1"} and e3["seguidas"] == 2
                and seguir(f2, "26/10/2026", abrir=abrir, reprocessar=True)["seguidas"] == 0)

    def t_prazo_para_e_guarda_o_feito():
        f = base(); e = seguir(f, "26/10/2026", abrir=abrir, abrir_final=lambda u: u, parar=[True])
        return e["seguidas"] == 0 and e["rede"] == 0

    def t_restante_converge():
        f = base(); hoje = "26/10/2026"
        antes = restantes(f, hoje)
        seguir(f, hoje, abrir=lambda u: None, abrir_final=lambda u: u)
        return antes > 0 and restantes(f, hoje) == 0

    def t_qd_so_com_cobertura_e_falha_nao_quebra():
        chamadas = []
        def qd(params): chamadas.append(params); raise OSError("503")
        f = base(); e = seguir(f, "26/10/2026", abrir=lambda u: None, abrir_final=lambda u: u,
                               consultar_qd_=qd, cobertura_qd={"4117909"})
        return len(chamadas) == 1 and e["rotas_falharam"] >= 1

    def t_gravar_rodada_pela_porta():
        import json as _j
        disco = {"pistas_imprensa.json": base()}
        l = lambda n, padrao=None: _j.loads(_j.dumps(disco[n])) if n in disco else padrao
        def g(n, o, compacto=False): disco[n] = _j.loads(_j.dumps(o))
        f = l("pistas_imprensa.json"); e = seguir(f, "26/10/2026", abrir=abrir, abrir_final=lambda u: u)
        gravar_rodada(f, e, ler_fn=l, gravar_fn=g)
        fila = disco["pistas_imprensa.json"]["pistas"]
        return (len(fila) == 7 + 2 and disco["pistas_rejeitadas.json"]["total"] == 3
                and any(p["status"].startswith(PREFIXO_FECHADA) for p in fila))

    try:
        return rodar_autoteste({
            "rota (notícia) e página oficial (B4) viram pistas novas de documento": t_rota_e_b4_viram_pistas_novas,
            "lixo cai com motivo (B1, B2, B3), com o status anterior guardado": t_lixo_cai_com_motivo,
            "redirecionador resolvido: a URL final entra como pista nova (B2)": t_redirecionador_resolvido_vira_pista_nova,
            "B6: nível A é o primeiro da rodada": t_b6_ordem_nivel_a_primeiro,
            "B10: documento oficial não lido volta à fila, até três vezes": t_b10_documento_volta_ate_tres_vezes,
            "restante converge para zero depois de seguir (fila reentrante)": t_restante_converge,
            "prazo do elo (SIGINT) para a rodada sem perder o que já se fez": t_prazo_para_e_guarda_o_feito,
            "fila antiga só no reprocessamento; o limite conta URL aberta, não fechamento":
                t_fila_antiga_e_do_reprocessamento_e_limite_e_de_rede,
            "Querido Diário só com cobertura; falha registrada sem quebrar": t_qd_so_com_cobertura_e_falha_nao_quebra,
            "a rodada grava só pela porta: novas, estado e rejeitadas": t_gravar_rodada_pela_porta,
        })
    finally:
        buscador2._SLUGS = None


def _abrir(url):
    from coletores_base import buscar
    return buscar(url, timeout=30, origem="buscador2")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--autoteste", action="store_true")
    ap.add_argument("--limite", type=int, default=60)
    ap.add_argument("--refazer-dias", type=int, default=7)
    ap.add_argument("--restante", action="store_true")
    ap.add_argument("--reprocessar", action="store_true",
                    help="a fila antiga: toda pista que o Buscador 2 ainda não viu (válvula, lotes de --limite URLs)")
    a = ap.parse_args()
    if a.autoteste:
        sys.exit(autoteste())
    fila = ler("pistas_imprensa.json") or {"pistas": []}
    hoje = hoje_editorial().strftime("%d/%m/%Y")
    if a.restante:
        print(restantes(fila, hoje, a.refazer_dias))
        sys.exit(0)
    cob = {k for k, v in ((ler("cobertura_qd.json") or {}).get("municipios") or {}).items()
           if isinstance(v, dict) and v.get("cobertura_qd")}
    try:
        from coletar_diarios_municipais import consultar_qd
        qd = lambda params: consultar_qd(params, timeout=40)
    except Exception:  # noqa: BLE001
        qd = None
    try:
        from monitorar_busca_web import buscar_searxng
        buscar_searxng("teste", timeout=5)
        from monitorar_busca_web import espera_do_ritmo
        import time
        web = lambda q: (time.sleep(espera_do_ritmo()), buscar_searxng(q))[1]
    except Exception:  # noqa: BLE001
        web = None
    # Sem o degrau HTTP no redirecionador: o link opaco do Google News responde 200 com uma casca de
    # JavaScript e nunca redireciona (A1-08). Resolve-se pela URL embutida e pela busca no veículo.
    # Em blocos de até BLOCO URLs, cada um gravado ao fim: o lote de 2.000 da válvula leva horas, e o
    # prazo do invólucro (SIGINT) ou uma queda não podem levar consigo o que já se seguiu.
    import signal
    parar = [False]
    signal.signal(signal.SIGINT, lambda *_: parar.__setitem__(0, True))
    orcamento = a.limite
    while True:
        e = seguir(fila, hoje, abrir=_abrir, abrir_final=None, consultar_qd_=qd, buscar_web_=web,
                   cobertura_qd=cob, limite=min(BLOCO, orcamento), refazer_dias=a.refazer_dias,
                   reprocessar=a.reprocessar, parar=parar)
        balanco = gravar_rodada(fila, e)
        orcamento -= e["rede"]
        print(f"Buscador 2: {e['seguidas']} seguida(s) · {len(e['fechadas_lista'])} fechada(s) {dict(e['motivos'])} · "
          f"{e['resolvidas']} redirecionamento(s) resolvido(s) · {e['candidatos']} candidato(s) · "
          f"{balanco['gravadas']} pista(s) nova(s) ({balanco['recusadas']} recusada(s) na porta) · "
          f"{e['retentadas']} documento(s) de volta à fila · {e['lacunas']} lacuna(s) · vias {dict(e['por_via'])} · "
          f"SearXNG={'sim' if web else 'não'} · QD={'sim' if qd else 'não'}", flush=True)
        if parar[0] or orcamento <= 0 or e["rede"] == 0 or not a.reprocessar:
            break
        fila = ler("pistas_imprensa.json") or {"pistas": []}
