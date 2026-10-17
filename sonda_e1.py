"""Sonda descartável da janela E1 (17/10/2026). Vive só no ramo coleta-dia/2026-10-17-sonda-sus."""
import io, json, re, sys
from coletores_base import buscar
import coletar_tabnet as T

CHAVES = __import__("os").environ.get("CHAVES") or r"(fumaça|respirat|diarr|água tratada|Aedes|dengue|chikungunya|armazen|reservat|calor|cardi|renal|rins|idos|crian|leptospir|hepatite)"

def texto(url):
    b = buscar(url, timeout=90)
    if b[:4] == b"%PDF":
        import pdfplumber
        with pdfplumber.open(io.BytesIO(b)) as pdf:
            return [(i + 1, (pg.extract_text() or "")) for i, pg in enumerate(pdf.pages)]
    h = b.decode("utf-8", "replace")
    h = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", h)
    return [(0, re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h)))]

def fontes():
    for url in sys.argv[2:]:
        try:
            pags = texto(url)
        except Exception as e:
            print(f"[fonte] {url}: FALHA {type(e).__name__}: {e}"); continue
        print(f"[fonte] {url}: {len(pags)} pág.")
        vistos = 0
        for n, t in pags:
            t1 = re.sub(r"\s+", " ", t)
            for m in re.finditer(CHAVES, t1, re.I):
                print(f"   p{n} …{t1[max(0, m.start()-160):m.end()+160]}…"); vistos += 1
                if vistos > 80: break
            if vistos > 80: break

def tabnet():
    T.sondar_def("sinannet/cnv/leptobr.def", "UF de resid")
    for pag in ("https://datasus.saude.gov.br/epidemiologicas-e-morbidade/",
                "https://datasus.saude.gov.br/acesso-a-informacao/doencas-e-agravos-de-notificacao-de-2007-em-diante-sinan/",
                "https://datasus.saude.gov.br/informacoes-de-saude-tabnet/"):
        try:
            h = buscar(pag, timeout=60).decode("utf-8", "replace")
            rx = re.compile(r"href=[\"']([^\"']*(?:tabnet|tabcgi|deftohtm|[.]def)[^\"']*)", re.I)
            print(f"[tabnet] {pag}: links {sorted(set(rx.findall(h)))[:80]}")
        except Exception as e:
            print(f"[tabnet] {pag}: FALHA {type(e).__name__}: {e}")

def sisab():
    h = buscar(__import__("coletar_sisab").RELATORIO, timeout=90).decode("utf-8", "replace")
    for nome in ("unidGeo", "j_idt76", "selectLinha", "selectcoluna", "j_idt89", "condicaoAvaliada", "tpProducao", "tipoAtendimento"):
        m = re.search(rf'<select[^>]*name="{nome}"[^>]*>(.*?)</select>', h, re.S)
        ops = re.findall(r'<option[^>]*value="([^"]*)"[^>]*>([^<]*)', m.group(1)) if m else []
        print(f"[sisab] {nome}: {ops[:45]}")
    print("[sisab] forms:", re.findall(r'<form[^>]*id="([^"]+)"[^>]*action="([^"]+)"', h)[:5])
    print("[sisab] cid:", sorted(set(re.findall(r'(?:id|name)="([^"]*[Cc]id[^"]*)"', h)))[:30])

def ckan():
    for termo in ("diarreica", "leptospirose", "malaria", "sinan", "sih", "sim", "gripal", "hepatite"):
        try:
            r = json.loads(buscar(f"https://ckan-dadosabertos.saude.gov.br/api/3/action/package_search?rows=40&q={termo}", timeout=60))
            res = r["result"]["results"]
            print(f"[ckan] {termo}: {r['result']['count']} → {[(p['name'], (p.get('metadata_modified') or '')[:10]) for p in res][:25]}")
        except Exception as e:
            print(f"[ckan] {termo}: FALHA {type(e).__name__}: {e}")

def sisab_html():
    h = buscar(__import__("coletar_sisab").RELATORIO, timeout=180).decode("utf-8", "replace")
    i = h.find('id="j_idt44"')
    form = h[i:i + 400000]
    nomes = sorted(set(re.findall(r'name="([^"]+)"', form)))
    print("[sisab-html] nomes no form j_idt44:", nomes[:200])
    for alvo in ("btnAddCid", "verTela", "cid-30-4", "selectLinha", "j_idt76", "Download", "csv", "exportar"):
        k = h.find(alvo)
        print(f"[sisab-html] --- {alvo} @ {k}")
        if k >= 0:
            print(re.sub(r"\s+", " ", h[max(0, k - 1200):k + 1800]))
    js = re.findall(r'<script[^>]*src="([^"]+)"', h)
    print("[sisab-html] scripts:", js)


def dbc_extra():
    import collections, coletar_datasus_dbc as C
    for pref in ("SDTA", "MALA"):
        for sub in ("PRELIM", "FINAIS"):
            itens = sorted(n for n, _ in C.listar_ftp(f"{C.SINAN}/{sub}") if n.upper().startswith(pref))
            print(f"[dbc] {pref} {sub}: {itens}")
            if not itens:
                continue
            cam = f"{C.SINAN}/{sub}/{itens[-1]}"
            desc, ls = C.ler_dbc(C.baixar_ftp(cam)); L = list(ls)
            print(f"[dbc] {cam}: {len(L)} registros; colunas {[d['nome'] for d in desc]}")
            for col in ("NU_ANO", "SG_UF_NOT", "SG_UF", "CLASSI_FIN", "RESULT", "DT_NOTIFIC"):
                if L and col in L[0]:
                    print(f"   {col}: {sorted(collections.Counter(x[col][:6] for x in L).items())[:40]}")
    with C._ftp() as f:
        for cam in ("PRELIM/LEPTBR26.dbc", "PRELIM/LEPTBR25.dbc", "FINAIS/LEPTBR24.dbc"):
            print(f"[mdtm] {cam}: {f.sendcmd('MDTM ' + C.SINAN + '/' + cam)}")


def sisab_post():
    import http.cookiejar, urllib.request, urllib.parse
    from coletores_base import ua_de
    import coletar_sisab as S
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    ua = ua_de("SISAB relatorio publico")
    h = op.open(urllib.request.Request(S.RELATORIO, headers={"User-Agent": ua}), timeout=180).read().decode("utf-8", "replace")
    vs = re.search(r'name="javax\.faces\.ViewState"[^>]*value="([^"]+)"', h).group(1)
    acao = re.search(r'<form id="j_idt44"[^>]*action="([^"]+)"', h).group(1)
    ids = re.findall(r'id="cid-([A-Z0-9]+-[14])"', h)
    alvo = [c for c in ids if c.split("-")[0] in ("D11", "D70", "D73", "A00", "A01", "A02", "A03", "A04", "A05", "A06", "A07", "A08", "A09")]
    print("[sisab-post] códigos de diarreia achados:", alvo, "de", len(ids))
    comps = re.findall(r'<option value="(\d{6})">', h)
    print("[sisab-post] competências:", comps[:3], "...", comps[-3:], len(comps))
    campos = [("j_idt44", "j_idt44"), ("unidGeo", "brasil"), ("selectLinha", "ATD.CO_UF_IBGE"), ("selectcoluna", "NU_COMPETENCIA"),
              ("tpProducao", "4"), ("lsCid", ",".join(alvo) + ","), ("javax.faces.ViewState", vs), ("j_idt192", "j_idt192")]
    campos += [("j_idt76", c) for c in comps[:3]]
    for e in re.findall(r'<option value="(eq-[a-z]+)"', h):
        campos.append(("j_idt89", e))
    url = urllib.parse.urljoin(S.RELATORIO, acao)
    r = op.open(urllib.request.Request(url, data=urllib.parse.urlencode(campos).encode(), headers={"User-Agent": ua, "Content-Type": "application/x-www-form-urlencoded"}), timeout=300)
    corpo = r.read()
    print("[sisab-post] resposta:", r.status, r.headers.get("Content-Type"), r.headers.get("Content-Disposition"), len(corpo))
    print("[sisab-post] início:", corpo[:3000].decode("latin-1"))
    # sem códigos: total de atendimentos, para comparação
    campos2 = [c for c in campos if c[0] != "lsCid"] + [("lsCid", "")]
    r2 = op.open(urllib.request.Request(url, data=urllib.parse.urlencode(campos2).encode(), headers={"User-Agent": ua, "Content-Type": "application/x-www-form-urlencoded"}), timeout=300)
    print("[sisab-post] sem filtro:", r2.read()[:1500].decode("latin-1"))


if __name__ == "__main__":
    {"fontes": fontes, "tabnet": tabnet, "sisab": sisab, "ckan": ckan, "sisab_html": sisab_html, "dbc_extra": dbc_extra, "sisab_post": sisab_post}[sys.argv[1]]()
