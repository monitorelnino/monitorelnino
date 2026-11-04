#!/usr/bin/env python3
"""sondar_adaptabrasil.py — sonda de UMA VEZ (04/11/2026), só leitura, válvula coleta-dia/*.
Handover AdaptaBrasil §2: (1) robots, termos e crédito; (2) data/versão dos índices; (3) árvore de saúde.
Recusa (robots, 401/403/429/451, captcha, muro) é registrada e respeitada, nunca contornada.
Saída no log com prefixo ADAPTA>. Não escreve em data/."""
import json, pathlib, re, sys, urllib.parse

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import coletores_base as cb  # noqa: E402

PAINEL, API, NACIONAL = "painel.adaptabrasil.mcti.gov.br", "api.painel.adaptabrasil.mcti.gov.br", "sistema.adaptabrasil.mcti.gov.br"
SAUDE = re.compile(r"sa[uú]de|arbovir|dengue|mal[aá]ria|leishmani|zika|chikung", re.I)


def p(*a):
    print("ADAPTA>", *a, flush=True)


def pegar(url):
    h = urllib.parse.urlparse(url).netloc
    if cb.robots_permite(h, url) is False:
        p("RECUSA robots", url)
        return None
    try:
        b = cb.buscar_uma_vez(url, timeout=40, origem="sonda AdaptaBrasil")
    except Exception as e:  # noqa: BLE001
        p("ERRO", url, type(e).__name__, str(e)[:160])
        return None
    p("OK", url, len(b), "bytes")
    return b.decode("utf-8", "replace")


def forma(o, n=0):
    if isinstance(o, dict):
        return {k: forma(v, n + 1) for k, v in list(o.items())[:14]} if n < 3 else "{…}"
    if isinstance(o, list):
        return [forma(o[0], n + 1), f"… {len(o)} itens"] if o else []
    return o if not isinstance(o, str) else o[:80]


for h in (PAINEL, API, NACIONAL):
    r = cb.robots_de(h)
    p("ROBOTS", h, r.get("status"), "crawl_delay", r.get("crawl_delay"))
    t = pegar(f"https://{h}/robots.txt")
    if t:
        p("ROBOTS-TXT", h, t.replace("\n", " | ")[:700])

for h in (PAINEL, NACIONAL):
    t = pegar(f"https://{h}/")
    if t:
        tit = re.search(r"<title>(.*?)</title>", t, re.S | re.I)
        p("TITULO", h, (tit.group(1).strip() if tit else "-")[:120])
        for m in sorted(set(re.findall(r'(?:href|src)="([^"]+)"', t)))[:40]:
            if re.search(r"termo|licen|sobre|uso|politica|privac|dados|api|doc|\.js$", m, re.I):
                p("LINK", h, m[:150])
        for m in re.findall(r"[^<>]{0,80}(?:licen[çc]a|termos? de uso|Creative Commons|CC BY|cite|citar|vers[aã]o|edi[çc][aã]o|atualiza)[^<>]{0,100}", t, re.I)[:12]:
            p("TEXTO", h, " ".join(m.split()))

ind = pegar(f"https://{API}/public/v1/indicators")
if ind:
    try:
        j = json.loads(ind)
    except ValueError:
        j = None
        p("NAO-JSON indicators", ind[:200])
    if j is not None:
        itens = j if isinstance(j, list) else next((v for v in j.values() if isinstance(v, list)), [])
        p("INDICATORS forma", json.dumps(forma(j), ensure_ascii=False)[:900])
        p("INDICATORS total", len(itens))
        saude = [i for i in itens if isinstance(i, dict) and SAUDE.search(json.dumps(i, ensure_ascii=False))]
        p("INDICATORS saúde", len(saude))
        for i in saude[:30]:
            p("IND", json.dumps(i, ensure_ascii=False)[:300])
        ids = [i.get("masterId") or i.get("id") for i in saude if isinstance(i, dict)]
        for mid in [x for x in ids if x][:8]:
            t = pegar(f"https://{API}/public/v1/indicators/{mid}/tree")
            if t:
                p("TREE", mid, t[:1500].replace("\n", " "))

for rota in ("/public/v1/locations/states", "/public/v1/ibge-summary/2927408"):
    t = pegar(f"https://{API}{rota}")
    if t:
        p("ROTA", rota, t[:500].replace("\n", " "))
