#!/usr/bin/env python3
"""
seguir_pistas.py — da notícia ao documento (§159, 22/09/2026)
=============================================================
Decisão editorial de 22/09/2026: notícia de imprensa nunca pontua; ela é PISTA de que o plano
existe. Este módulo segue cada pista de imprensa pendente (nível A/B) até documentos candidatos
a ato oficial, por três rotas, da mais precisa à mais ampla:

  1. LINKS DA PRÓPRIA NOTÍCIA — jornal local costuma linkar o decreto ou o PDF do plano. Extrai os
     links de saída da página para host oficial (.gov.br/.leg.br/diário) que sejam PDF, diário, ou
     cujo endereço/texto do link fale em decreto, lei, portaria, plano ou PLANCON.
  2. QUERIDO DIÁRIO — só para os ~518 municípios com diário indexado (data/cobertura_qd.json):
     edições desde 01/10/2025 com os termos do plano; cada edição com trecho vira candidato.
  3. BUSCA NO DOMÍNIO OFICIAL — SearXNG (o mesmo efêmero da busca web): "{município}" {UF} +
     plano de contingência + decreto, só resultados em host oficial.

Cada candidato vira uma PISTA NOVA (origem "seguimento_*", com `pista_origem` = id da notícia),
e segue o caminho de sempre: triagem de confiança → revisar_pistas --preparar → portão automático
(§156: só ato publicado de 2026, lido no próprio diário/PDF) → juiz (backup + derivados + portões +
rollback, §158). Nada aqui pontua, decide ou descarta; a notícia de origem continua pendente e
visível no card (§155) até o documento aparecer. Tudo tolerante a falha: rota indisponível
(QD fora do ar, SearXNG não subiu) fica registrada no `seguimento` da notícia e é tentada de novo.

USO   python seguir_pistas.py [--limite 20] [--refazer-dias 7]   ·   python seguir_pistas.py --autoteste
"""
import argparse, datetime, hashlib, json, re, sys, urllib.parse, urllib.request
from coletores_base import ler, gravar, rodar_autoteste, ua_de, hoje_editorial
from monitorar_imprensa_regional import parece_fonte_oficial

STATUS_PENDENTE = "pista — promover a registro exige documento primário lido por humano"
RE_LINK = re.compile(r'<a\s[^>]*href=["\']([^"\'#]+)["\'][^>]*>(.*?)</a>', re.I | re.S)
RE_SINAL_ATO = re.compile(r"decreto|\blei\b|portaria|plancon|plano|conting|diario|\.pdf", re.I)
TERMOS_QD = '"plano de contingência" OR plancon OR "plano municipal de proteção e defesa civil"'
QD_DESDE = "2025-10-01"
MAX_POR_ROTA = 4


def _id(ibge, url, trecho):
    return hashlib.sha1(f"{ibge or ''}|{url or ''}|{(trecho or '')[:500]}".encode("utf-8")).hexdigest()[:10]


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


# ------------------------------------------------------------------ rota 2: Querido Diário
def candidatos_qd(pista, consultar):
    params = urllib.parse.urlencode({"territory_ids": pista.get("ibge"), "querystring": TERMOS_QD,
                                     "published_since": QD_DESDE, "excerpt_size": 500,
                                     "number_of_excerpts": 1, "size": MAX_POR_ROTA})
    d = json.loads(consultar(params).decode("utf-8", "replace"))
    out = []
    for g in d.get("gazettes", [])[:MAX_POR_ROTA]:
        exc = " ".join(((g.get("excerpts") or [""])[0]).split())
        if g.get("url") and exc:
            out.append({"url": g["url"], "trecho": exc[:600], "titulo": f"Diário oficial de {g.get('date')}",
                        "rota": "seguimento_querido_diario", "data_edicao": g.get("date")})
    return out


# ------------------------------------------------------------------ rota 3: busca no domínio oficial
def candidatos_busca(pista, buscar):
    q = f'"{pista.get("municipio")}" {pista.get("uf")} decreto "plano de contingência"'
    d = buscar(q) or {}
    out = []
    for r in d.get("results", []):
        url = r.get("url") or ""
        if not parece_fonte_oficial(url):
            continue
        out.append({"url": url, "trecho": (r.get("content") or "")[:600], "titulo": (r.get("title") or "")[:300],
                    "rota": "seguimento_busca_oficial"})
        if len(out) >= MAX_POR_ROTA:
            break
    return out


def seguir(fila, hoje, buscar_html_=buscar_html, consultar_qd_=None, buscar_web_=None, cobertura_qd=frozenset(),
           limite=20, refazer_dias=7):
    """Segue até `limite` notícias pendentes A/B ainda não seguidas (ou seguidas há mais de `refazer_dias`).
    Devolve estatística. Acrescenta pistas novas ao fim da fila; nunca altera status de ninguém."""
    urls_existentes = {p.get("url") for p in fila["pistas"]}
    d_hoje = datetime.datetime.strptime(hoje, "%d/%m/%Y").date()
    est = {"seguidas": 0, "candidatos": 0, "novas": 0, "rotas_falharam": 0}
    novas = []
    for p in fila["pistas"]:
        if est["seguidas"] >= limite:
            break
        if not (p.get("status") or "").startswith("pista") or p.get("nivel_confianca") not in ("A", "B"):
            continue
        if (p.get("origem") or "").startswith("seguimento") or parece_fonte_oficial(p.get("url") or ""):
            continue   # só notícia (fonte não oficial) é seguida; documento oficial já vai direto ao juiz
        s = p.get("seguimento") or {}
        if s.get("data"):
            try:
                if (d_hoje - datetime.datetime.strptime(s["data"], "%d/%m/%Y").date()).days < refazer_dias and not s.get("falhas"):
                    continue
            except ValueError:
                pass
        est["seguidas"] += 1
        cands, falhas = [], []
        try:
            cands += candidatos_da_noticia(p, buscar_html_(p.get("url")))
        except Exception as e:  # noqa: BLE001
            falhas.append(f"link_noticia: {e.__class__.__name__}")
        if consultar_qd_ and str(p.get("ibge")) in cobertura_qd:
            try:
                cands += candidatos_qd(p, consultar_qd_)
            except Exception as e:  # noqa: BLE001
                falhas.append(f"querido_diario: {e.__class__.__name__}")
        if buscar_web_:
            try:
                cands += candidatos_busca(p, buscar_web_)
            except Exception as e:  # noqa: BLE001
                falhas.append(f"busca_oficial: {e.__class__.__name__}")
        est["rotas_falharam"] += len(falhas)
        est["candidatos"] += len(cands)
        n_novas = 0
        for c in cands:
            if c["url"] in urls_existentes:
                continue
            urls_existentes.add(c["url"])
            nova = {"municipio": p.get("municipio"), "uf": p.get("uf"), "ibge": p.get("ibge"), "url": c["url"],
                    "trecho": c["trecho"], "titulo": c.get("titulo"), "data": hoje, "origem": c["rota"],
                    "status": STATUS_PENDENTE, "pista_origem": p.get("id")}
            nova["id"] = _id(nova["ibge"], nova["url"], nova["trecho"])
            novas.append(nova); n_novas += 1
        p["seguimento"] = {"data": hoje, "candidatos": len(cands), "pistas_novas": n_novas, "falhas": falhas}
        est["novas"] += n_novas
    fila["pistas"].extend(novas)
    return est


def autoteste():
    base = lambda: {"pistas": [
        {"id": "n1", "municipio": "Palotina", "uf": "PR", "ibge": "4117909", "url": "https://jornal.com.br/palotina-plano",
         "status": STATUS_PENDENTE, "nivel_confianca": "A", "origem": "busca_web"},
        {"id": "o1", "municipio": "Bagé", "uf": "RS", "ibge": "4301602", "url": "https://bage.rs.gov.br/decreto.pdf",
         "status": STATUS_PENDENTE, "nivel_confianca": "A", "origem": "busca_web"},
        {"id": "c1", "municipio": "Ipixuna", "uf": "AM", "ibge": "1301803", "url": "https://x.com.br/a",
         "status": STATUS_PENDENTE, "nivel_confianca": "C", "origem": "busca_web"}]}
    HTML = ('<p>A prefeitura publicou o <a href="/x">anúncio</a>.</p>'
            '<a href="https://palotina.pr.gov.br/leis/decreto-512-2026.pdf">Decreto nº 512/2026 — Plano de Contingência</a>'
            '<a href="https://facebook.com/palotina">Facebook</a>'
            '<a href="https://palotina.pr.gov.br/turismo">Turismo</a>')

    def t_link_da_noticia_vira_pista_nova():
        f = base(); e = seguir(f, "22/09/2026", buscar_html_=lambda u: HTML)
        nov = [p for p in f["pistas"] if p.get("origem") == "seguimento_link_noticia"]
        return e["novas"] == 1 and nov[0]["url"].endswith("decreto-512-2026.pdf") and nov[0]["pista_origem"] == "n1" \
               and nov[0]["status"] == STATUS_PENDENTE

    def t_nao_segue_fonte_oficial_nem_C():
        f = base(); e = seguir(f, "22/09/2026", buscar_html_=lambda u: HTML)
        return e["seguidas"] == 1 and "seguimento" not in f["pistas"][1] and "seguimento" not in f["pistas"][2]

    def t_nunca_altera_status_da_noticia():
        f = base(); seguir(f, "22/09/2026", buscar_html_=lambda u: HTML)
        return f["pistas"][0]["status"] == STATUS_PENDENTE and f["pistas"][0]["seguimento"]["pistas_novas"] == 1

    def t_qd_so_com_cobertura_e_falha_nao_quebra():
        chamadas = []
        def qd(params): chamadas.append(params); raise OSError("503")
        f = base(); e = seguir(f, "22/09/2026", buscar_html_=lambda u: None, consultar_qd_=qd, cobertura_qd={"4117909"})
        return len(chamadas) == 1 and e["rotas_falharam"] == 1 and f["pistas"][0]["seguimento"]["falhas"] == ["querido_diario: OSError"]

    def t_qd_edicao_vira_candidato():
        resp = json.dumps({"gazettes": [{"date": "2026-08-21", "url": "https://data.queridodiario.ok.org.br/4117909/x.pdf",
                                         "excerpts": ["DECRETO Nº 512 institui o Plano de Contingência"]}]}).encode()
        f = base(); seguir(f, "22/09/2026", buscar_html_=lambda u: None, consultar_qd_=lambda q: resp, cobertura_qd={"4117909"})
        return any(p.get("origem") == "seguimento_querido_diario" for p in f["pistas"])

    def t_busca_so_host_oficial():
        res = {"results": [{"url": "https://g1.globo.com/x", "title": "notícia"},
                           {"url": "https://palotina.pr.gov.br/decreto-512", "title": "Decreto 512", "content": "institui o plano"}]}
        f = base(); seguir(f, "22/09/2026", buscar_html_=lambda u: None, buscar_web_=lambda q: res)
        nov = [p for p in f["pistas"] if p.get("origem") == "seguimento_busca_oficial"]
        return len(nov) == 1 and "gov.br" in nov[0]["url"]

    def t_dedup_e_refazer_depois_de_7_dias():
        f = base(); seguir(f, "22/09/2026", buscar_html_=lambda u: HTML)
        e2 = seguir(f, "23/09/2026", buscar_html_=lambda u: HTML)          # 1 dia depois: não refaz
        e3 = seguir(f, "30/09/2026", buscar_html_=lambda u: HTML)          # 8 dias: refaz, mas não duplica
        return e2["seguidas"] == 0 and e3["seguidas"] == 1 and e3["novas"] == 0

    return rodar_autoteste({
        "link oficial da notícia vira pista nova ligada à de origem": t_link_da_noticia_vira_pista_nova,
        "não segue fonte oficial (vai direto ao juiz) nem nível C": t_nao_segue_fonte_oficial_nem_C,
        "nunca altera o status da notícia (continua pendente, visível no card)": t_nunca_altera_status_da_noticia,
        "Querido Diário só com cobertura; falha registrada sem quebrar": t_qd_so_com_cobertura_e_falha_nao_quebra,
        "edição do Querido Diário vira candidato": t_qd_edicao_vira_candidato,
        "busca: só resultado em host oficial vira candidato": t_busca_so_host_oficial,
        "sem duplicar; refaz só depois de 7 dias": t_dedup_e_refazer_depois_de_7_dias,
    })


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--autoteste", action="store_true")
    ap.add_argument("--limite", type=int, default=20)
    ap.add_argument("--refazer-dias", type=int, default=7)
    a = ap.parse_args()
    if a.autoteste:
        sys.exit(autoteste())
    fila = ler("pistas_imprensa.json") or {"pistas": []}
    cob = {k for k, v in ((ler("cobertura_qd.json") or {}).get("municipios") or {}).items()
           if isinstance(v, dict) and v.get("cobertura_qd")}
    try:
        from coletar_diarios_municipais import consultar_qd
        qd = lambda params: consultar_qd(params, timeout=40)
    except Exception:  # noqa: BLE001
        qd = None
    try:
        from monitorar_busca_web import buscar_searxng
        buscar_searxng("teste", timeout=5)   # SearXNG no ar? (só na rodada de cadência)
        web = buscar_searxng
    except Exception:  # noqa: BLE001
        web = None
    e = seguir(fila, hoje_editorial().strftime("%d/%m/%Y"), consultar_qd_=qd, buscar_web_=web,
               cobertura_qd=cob, limite=a.limite, refazer_dias=a.refazer_dias)
    gravar("pistas_imprensa.json", fila)
    print(f"seguimento: {e['seguidas']} notícia(s) seguida(s) · {e['candidatos']} candidato(s) · {e['novas']} pista(s) nova(s) "
          f"· {e['rotas_falharam']} rota(s) indisponível(is) · SearXNG={'sim' if web else 'não'} · QD={'sim' if qd else 'não'}")
