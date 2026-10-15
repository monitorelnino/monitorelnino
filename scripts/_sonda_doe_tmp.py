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


# SP: o texto integral da publicação
get("SP", "https://doe.sp.gov.br/executivo/casa-civil/despacho-do-secretario-de-2-de-outubro-de-2026-20261002111012042179446", "corpo")
get("SP", "https://do-api-web-search.doe.sp.gov.br/v2/publications/dbeb0429-e167-4e3c-b76c-08df1efd0e0c", "json")
get("SP", "https://do-api-web-search.doe.sp.gov.br/v2/advanced-search/publications?PageNumber=1&PageSize=3&Terms[0]=homologa%20o%20decreto&FromDate=2026-07-01&ToDate=2026-10-15", "json")
get("SP", "https://do-api-web-search.doe.sp.gov.br/v2/advanced-search/publications?PageNumber=1&PageSize=3&Terms[0]=situa%C3%A7%C3%A3o%20de%20emerg%C3%AAncia&FromDate=2026-07-01&ToDate=2026-10-15&JournalId=d65936d7-1ca8-4267-934e-1dea132fa237", "json")
# RR: as rotas expostas
get("RR", "https://www.imprensaoficial.rr.gov.br/_visualizar-doe/", "hrefs")
get("RR", "https://www.imprensaoficial.rr.gov.br/_visualizar-mes/?ano=2026&mes=10", "hrefs")
get("RR", "https://www.imprensaoficial.rr.gov.br/_buscar/", "corpo")
# PI: o host atual
get("PI", "https://www.diario.pi.gov.br/doe/", "hrefs")
get("PI", "https://diario.pi.gov.br/", "hrefs")
# MG: a API v1
for r in ("", "edicoes", "publicacoes", "jornal/ultimas-edicoes", "edicao/ultima"):
    get("MG", "https://www.jornalminasgerais.mg.gov.br/api/v1/" + r, "json")
# PE/RN: a plataforma sdoe
for r in ("", "edicoes", "api/edicoes", "diarios", "edicao/ultima"):
    get("PE", "https://diariooficial.cepe.com.br/diariooficial/" + r, "json")
get("RN", "https://deirn.sdoe.com.br/diariooficialweb/", "hrefs")
get("RN", "https://deirn.sdoe.com.br/diariooficial/edicoes", "json")
# SC
get("SC", "https://portal.doe.sea.sc.gov.br/v2.44.07/", "hrefs")
