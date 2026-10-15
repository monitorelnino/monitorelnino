"""Sonda temporária (ramo diag, não vai à main): rotas dos 19 DOEs sem adaptador, do runner.

Uma requisição por candidato, sem repetição (buscar_uma_vez), 30 s. Imprime uma linha JSON por
candidato: código, tipo, bytes, título, início, links com cara de edição/PDF/busca, scripts (para
achar a API de SPA) e, para PDF, páginas e se há texto extraível + contagem dos termos do Legal.
"""
import io, json, re, sys, time, urllib.error, urllib.parse
sys.path.insert(0, ".")
from coletores_base import buscar_uma_vez, enviar_uma_vez, UA  # noqa: E402

D = "2026-10-14"; DC = "20261014"; DBR = "14/10/2026"
T = urllib.parse.quote("situação de emergência")
ROTAS = {
 "AL": ["http://diario.imprensaoficial.al.gov.br",
        "http://diario.imprensaoficial.al.gov.br/apifront/portal/edicoes/edicoes_from_data/2026-10-14.json",
        "http://diario.imprensaoficial.al.gov.br/busca/busca/buscar/query/0/di:2026-09-14/df:2026-10-14/?1=1&q=%22situa%C3%A7%C3%A3o%20de%20emerg%C3%AAncia%22"],
 "AM": ["https://diario.imprensaoficial.am.gov.br/apifront/portal/edicoes/edicoes_from_data/2026-10-14.json",
        "https://diario.imprensaoficial.am.gov.br/apifront/portal/edicoes/edicoes_from_data/2026-10-09.json",
        "https://diario.imprensaoficial.am.gov.br/portal/edicoes"],
 "BA": ["https://dool.egba.ba.gov.br/", "https://dool.egba.ba.gov.br/portal/edicoes/edicoes_from_data/2026-10-14.json",
        "https://dool.egba.ba.gov.br/apifront/portal/edicoes/edicoes_from_data/2026-10-14.json",
        "https://www.egba.ba.gov.br/diario-oficial"],
 "CE": [f"http://imagens.seplag.ce.gov.br/PDF/{DC}/do{DC}p01.pdf", f"http://imagens.seplag.ce.gov.br/PDF/{DC}/do{DC}p02.pdf",
        f"http://imagens.seplag.ce.gov.br/PDF/{DC}/do{DC}p03.pdf", f"http://imagens.seplag.ce.gov.br/PDF/{DC}/do{DC}p04.pdf",
        f"https://imagens.seplag.ce.gov.br/PDF/{DC}/do{DC}p01.pdf", "https://pesquisa.doe.seplag.ce.gov.br/doepesquisa/",
        "http://pesquisa.doe.seplag.ce.gov.br/doepesquisa/sead.do?page=ultimasEdicoes&cmd=11&action=Ultimas"],
 "MA": ["https://www.diariooficial.ma.gov.br/", "https://diariooficial.ma.gov.br/public/index.jsf",
        "https://www.diariooficial.ma.gov.br/public/diario.jsf", "https://diariooficial.ma.gov.br/"],
 "MG": ["https://www.jornalminasgerais.mg.gov.br/", "https://www.jornalminasgerais.mg.gov.br/api/publicacao/ultimas",
        "https://www.jornalminasgerais.mg.gov.br/edicao-do-dia", "https://www.jornalminasgerais.mg.gov.br/api/edicoes?data=2026-10-14"],
 "MS": ["https://www.spdo.ms.gov.br/diariodoe/", "https://www.spdo.ms.gov.br/diariodoe/Index/Download/DO12299_14_10_2026"],
 "PA": ["https://www.ioepa.com.br/pages/2026/10/14/2026.10.14.DOE.pdf", "https://www.ioepa.com.br/pages/2026/10/14/",
        "https://www.ioepa.com.br/pesquisa/", "https://www.ioepa.com.br/edicao/", "https://www.ioepa.com.br/diario/"],
 "PB": ["https://auniao.pb.gov.br/servicos/doe/2026/outubro/diario-oficial-14-10-2026-portal.pdf",
        "https://auniao.pb.gov.br/servicos/doe/2026/outubro"],
 "PE": ["https://diariooficial.cepe.com.br/diariooficialweb/", "https://diariooficial.cepe.com.br/diariooficialweb/api/edicoes",
        "https://diariooficial.cepe.com.br/diariooficialweb/rest/edicao/ultima", "https://diariooficial.cepe.com.br/diariooficialweb/scripts/app.js"],
 "PI": [f"http://www.diariooficial.pi.gov.br/diarios.php?dia={DC}", f"http://www.diariooficial.pi.gov.br/diario.php?dia={DC}",
        "http://www.diariooficial.pi.gov.br/diario.php?dia=20261013"],
 "RJ": ["https://www.ioerj.com.br/portal/", "https://www.ioerj.com.br/portal/modules/conteudoonline/mostra_edicao.php",
        "https://www.ioerj.com.br/portal/modules/conteudoonline/index.php", "https://doweb.rio.rj.gov.br/"],
 "RN": ["https://www.diariooficial.rn.gov.br", "http://diariooficial.rn.gov.br/dei/dorn3/", "https://diariooficial.rn.gov.br/dei/dorn3/docview.aspx",
        "http://diariooficial.rn.gov.br/dei/dorn3/Search.aspx", "http://diariooficial.rn.gov.br/dei/dorn3/edicaovisualizar.aspx"],
 "RO": ["https://diof.ro.gov.br/2026/10/14/", f"https://diof.ro.gov.br/?s={T}", "https://diof.ro.gov.br/data-de-publicacao/2026/10/14/",
        "https://diof.ro.gov.br/wp-json/wp/v2/posts?per_page=3", "https://diof.ro.gov.br/feed/"],
 "RR": ["https://www.imprensaoficial.rr.gov.br/", "https://www.imprensaoficial.rr.gov.br/api/", "https://www.imprensaoficial.rr.gov.br/app/",
        "https://www.imprensaoficial.rr.gov.br/app/_edicoes/"],
 "RS": ["https://www.diariooficial.rs.gov.br/", "https://www.diariooficial.rs.gov.br/diario?pg=1", "https://www.diariooficial.rs.gov.br/api/",
        "https://www.diariooficial.rs.gov.br/diario?data=14/10/2026", "https://www.diariooficial.rs.gov.br/materia?id=1"],
 "SC": ["https://doe.sea.sc.gov.br/", "https://doe.sea.sc.gov.br/edicoes", "https://portal.doe.sea.sc.gov.br/", "https://doe.sea.sc.gov.br/api/"],
 "SE": ["https://segrase.se.gov.br/portal/", "https://www.segrase.se.gov.br/", "https://doe.se.gov.br/", "https://diariooficial.se.gov.br/",
        "http://www.se.gov.br/diario-oficial"],
 "SP": ["https://doe.sp.gov.br/", "https://do-api-web-search.doe.sp.gov.br/v2/advanced-search/publications?PageNumber=1&PageSize=5&Terms[0]=situa%C3%A7%C3%A3o%20de%20emerg%C3%AAncia&FromDate=2026-10-01&ToDate=2026-10-14",
        "https://do-api-web-search.doe.sp.gov.br/v2/journals?Date=2026-10-14", "https://doe.sp.gov.br/api/"],
}
RE_L = re.compile(r'(?:href|src)="([^"]*(?:busca|pesquis|edic|diario|pdf|download|api|\.js)[^"]*)"', re.I)


def pdf_info(b):
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(b)) as pdf:
            n = len(pdf.pages)
            txt = "\n".join((pdf.pages[i].extract_text() or "") for i in range(min(n, 6)))
        return {"paginas": n, "texto_6pg": len(txt), "homologa": txt.lower().count("homologa"),
                "emergencia": txt.lower().count("situação de emergência"), "inicio_texto": " ".join(txt.split())[:160]}
    except Exception as e:  # noqa: BLE001
        return {"pdf_erro": f"{type(e).__name__}: {str(e)[:80]}"}


def sondar(uf, u, post=None):
    t0 = time.time()
    try:
        b = enviar_uma_vez(u, post, timeout=30, origem="sonda DOE") if post else buscar_uma_vez(u, timeout=30, origem="sonda DOE")
        s = {"uf": uf, "url": u, "ok": True, "bytes": len(b), "ms": int((time.time() - t0) * 1000)}
        if b[:5] == b"%PDF-":
            s.update(pdf_info(b)); return s
        t = b[:60000].decode("utf-8", "replace")
        tit = re.search(r"<title>(.*?)</title>", t, re.S | re.I)
        s.update({"titulo": (tit.group(1).strip()[:100] if tit else None), "inicio": " ".join(t[:400].split()),
                  "links": sorted(set(RE_L.findall(t)))[:25], "forms": re.findall(r"<form[^>]*>", t, re.I)[:4],
                  "conta_emerg": t.lower().count("situação de emergência")})
        return s
    except urllib.error.HTTPError as e:
        corpo = b""
        try: corpo = e.read()[:400]
        except Exception: pass  # noqa: BLE001
        return {"uf": uf, "url": u, "ok": False, "http": e.code, "local": e.headers.get("Location"), "corpo": corpo.decode("utf-8", "replace")}
    except Exception as e:  # noqa: BLE001
        return {"uf": uf, "url": u, "ok": False, "erro": f"{type(e).__name__}: {str(e)[:200]}"}


ufs = sys.argv[1:] or list(ROTAS)
for uf in ufs:
    for u in ROTAS[uf]:
        print(json.dumps(sondar(uf, u), ensure_ascii=False), flush=True)
# PA: a busca é POST (form1 ASP.NET); PI: busca_diario.php por POST, já medida morta (índice até 2021).
print(json.dumps(sondar("PA", "https://www.ioepa.com.br/pesquisa/resultado/QueryTexto", {"texto": "situação de emergência"}), ensure_ascii=False), flush=True)
