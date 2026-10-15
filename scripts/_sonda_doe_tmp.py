"""Sonda temporária 2 (ramo diag, não vai à main): confirmar os caminhos apontados pela sonda 1."""
import io, json, re, sys, time, urllib.error
sys.path.insert(0, ".")
from coletores_base import buscar_uma_vez  # noqa: E402

RE_URL = re.compile(r'https?://[^\s"\'<>\\]{8,160}')
RE_HREF = re.compile(r'(?:href|src|action)="([^"]{4,200})"', re.I)


def pdf_info(b):
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(b)) as pdf:
            n = len(pdf.pages)
            txt = "\n".join((pdf.pages[i].extract_text() or "") for i in range(min(n, 6)))
        return {"paginas": n, "texto_6pg": len(txt), "inicio_texto": " ".join(txt.split())[:200]}
    except Exception as e:  # noqa: BLE001
        return {"pdf_erro": f"{type(e).__name__}: {str(e)[:80]}"}


def get(uf, u, modo="html", grep=None, timeout=30):
    t0 = time.time()
    try:
        b = buscar_uma_vez(u, timeout=timeout, origem="sonda DOE")
    except urllib.error.HTTPError as e:
        corpo = b""
        try: corpo = e.read()[:600]
        except Exception: pass  # noqa: BLE001
        print(json.dumps({"uf": uf, "url": u, "http": e.code, "corpo": corpo.decode("utf-8", "replace")}, ensure_ascii=False), flush=True); return None
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"uf": uf, "url": u, "erro": f"{type(e).__name__}: {str(e)[:200]}"}, ensure_ascii=False), flush=True); return None
    s = {"uf": uf, "url": u, "bytes": len(b), "ms": int((time.time() - t0) * 1000)}
    if b[:5] == b"%PDF-":
        s.update(pdf_info(b))
    else:
        t = b.decode("utf-8", "replace")
        if modo == "json":
            s["json"] = t[:3500]
        elif modo == "hrefs":
            s["hrefs"] = sorted(set(RE_HREF.findall(t)))[:80]
        elif modo == "urls_js":
            urls = sorted(set(RE_URL.findall(t)))
            s["urls"] = [x for x in urls if grep is None or re.search(grep, x, re.I)][:60]
            s["trechos_api"] = [t[max(0, m.start() - 60):m.end() + 60] for m in re.finditer(r"/api/|apifront|/rest/|/v[12]/", t)][:30]
        elif modo == "corpo":
            s["corpo"] = t[:4000]
    print(json.dumps(s, ensure_ascii=False), flush=True)
    return b


# AM: o id da listagem é o do download?
get("AM", "https://diario.imprensaoficial.am.gov.br/portal/edicoes/download/18242", timeout=120)
get("AM", "https://diario.imprensaoficial.am.gov.br/apifront/portal/edicoes/edicoes_from_data/2026-10-13.json", "json")
# CE: o 5º caderno não existe (fim da iteração)
get("CE", "https://imagens.seplag.ce.gov.br/PDF/20261014/do20261014p05.pdf")
get("CE", "https://imagens.seplag.ce.gov.br/PDF/20261013/do20261013p01.pdf")
# SP: a API de busca — estrutura inteira de 2 itens, e a listagem de edições por data
get("SP", "https://do-api-web-search.doe.sp.gov.br/v2/advanced-search/publications?PageNumber=1&PageSize=2&Terms[0]=situa%C3%A7%C3%A3o%20de%20emerg%C3%AAncia&FromDate=2026-10-01&ToDate=2026-10-14", "json")
get("SP", "https://do-api-web-search.doe.sp.gov.br/v2/advanced-search/publications?PageNumber=1&PageSize=2&Terms[0]=homologa&FromDate=2026-09-01&ToDate=2026-10-14", "json")
get("SP", "https://do-api-web-search.doe.sp.gov.br/v2/journals?Date=2026-10-14", "json")
get("SP", "https://do-api-web-search.doe.sp.gov.br/v2/summary?Date=2026-10-14&JournalId=d65936d7-1ca8-4267-934e-1dea132fa237", "json")
# PI: a página do dia — todos os endereços
get("PI", "http://www.diariooficial.pi.gov.br/diarios.php?dia=20261014", "hrefs")
get("PI", "http://www.diariooficial.pi.gov.br/diarios.php?dia=20261014", "corpo")
# RO: resultado da busca → posts → PDF
b = get("RO", "https://diof.ro.gov.br/?s=situa%C3%A7%C3%A3o%20de%20emerg%C3%AAncia", "hrefs")
if b:
    t = b.decode("utf-8", "replace")
    posts = [h for h in RE_HREF.findall(t) if h.startswith("https://diof.ro.gov.br/") and re.search(r"/\d{4}/\d{2}/|/diario|edicao|doe", h, re.I)]
    arts = re.findall(r'<article[^>]*>.*?</article>', t, re.S)[:3]
    print(json.dumps({"uf": "RO", "posts": posts[:15], "n_articles": len(re.findall(r"<article", t)), "article1": " ".join(arts[0].split())[:1500] if arts else None}, ensure_ascii=False), flush=True)
    if posts:
        get("RO", posts[0], "hrefs")
# RJ: a página do conteúdo online
get("RJ", "https://www.ioerj.com.br/portal/modules/conteudoonline/index.php", "hrefs")
# SPAs: onde fica a API
get("MG", "https://www.jornalminasgerais.mg.gov.br/main-A77B4DKJ.js", "urls_js", r"api|edic|public|jornal|diario")
get("RS", "https://www.diariooficial.rs.gov.br/main-WOM4SM2S.js", "urls_js", r"api|edic|diario|materia")
get("AL", "http://diario.imprensaoficial.al.gov.br/assets/index-344f66e8.js", "urls_js", r"api|edic|diario|busca")
get("PE", "https://diariooficial.cepe.com.br/diariooficialweb/app/app.config.js", "corpo")
get("SC", "https://doe.sea.sc.gov.br/", "corpo")
get("RR", "https://www.imprensaoficial.rr.gov.br/_inicial/", "hrefs")
get("MA", "https://www.diariooficial.ma.gov.br/", "corpo")
get("BA", "https://www.egba.ba.gov.br/", "hrefs")
get("BA", "http://dool.egba.ba.gov.br/", "corpo", timeout=20)
get("PA", "https://www.ioepa.com.br/", "hrefs")
get("RN", "http://www.diariooficial.rn.gov.br/dei/dorn3", "corpo")
