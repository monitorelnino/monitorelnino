"""Sonda de diagnóstico (ramo de válvula, nunca mesclado): por que os diários da BA e do MA não respondem ao runner.
Mede, com o cliente identificado do projeto: DNS, TCP, TLS e HTTP de cada rota; a mesma rota vista de sondas públicas
no Brasil e fora (Globalping, check-host); e quanto do diário existe no Internet Archive. Não grava dado nenhum."""
import sys, json, socket, ssl, time, urllib.request, urllib.error, urllib.parse
sys.path[:0] = ["scripts", "."]
import coletores_base as cb

UA = cb.ua_de("sonda de rota de diario oficial")
print("UA", UA, flush=True)
Q = urllib.parse.quote
MA_BUSCA = ("https://diariooficial.ma.gov.br/ajax.busca.php?&termo=" + Q('"estado de emergência em saúde"')
            + "&sigla=&datai=2026-06-29&dataf=2026-11-18&scrollId=")
ALVOS = [
    ("BA dool raiz", "https://dool.egba.ba.gov.br/"),
    ("BA dool edicoes", "https://dool.egba.ba.gov.br/apifront/portal/edicoes/edicoes_from_data/2026-11-17.json"),
    ("BA dool http80", "http://dool.egba.ba.gov.br/"),
    ("BA egbanet", "https://egbanet.egba.ba.gov.br/"),
    ("BA egba", "https://www.egba.ba.gov.br/"),
    ("BA ba.gov.br/egba", "https://www.ba.gov.br/egba/"),
    ("BA legislabahia", "https://www.legislabahia.ba.gov.br/"),
    ("MA raiz", "https://diariooficial.ma.gov.br/"),
    ("MA busca", MA_BUSCA),
    ("MA pdf", "https://diariooficial.ma.gov.br/download.php?arq=EX20261116"),
    ("MA www", "https://www.diariooficial.ma.gov.br/"),
    ("MA http80", "http://diariooficial.ma.gov.br/"),
    ("MA ma.gov.br", "https://www.ma.gov.br/"),
    ("espelho jusbrasil DOEBA", "https://www.jusbrasil.com.br/diarios/DOEBA/"),
    ("espelho jusbrasil DOEMA", "https://www.jusbrasil.com.br/diarios/DOEMA/"),
]


def estagios(url):
    u = urllib.parse.urlparse(url); host = u.hostname; porta = u.port or (443 if u.scheme == "https" else 80)
    r = {}
    try:
        ips = sorted({i[4][0] for i in socket.getaddrinfo(host, porta, proto=socket.IPPROTO_TCP)})
        r["dns"] = ips[:4]
    except Exception as e:  # noqa: BLE001
        r["dns"] = f"ERRO {type(e).__name__}: {e}"; return r
    t = time.time()
    try:
        s = socket.create_connection((r["dns"][0], porta), timeout=15)
        r["tcp"] = f"ok {time.time() - t:.2f}s"
    except Exception as e:  # noqa: BLE001
        r["tcp"] = f"ERRO {type(e).__name__}: {e} ({time.time() - t:.1f}s)"; return r
    if u.scheme == "https":
        try:
            ss = ssl.create_default_context().wrap_socket(s, server_hostname=host)
            cn = dict(x[0] for x in ss.getpeercert().get("subject", ())).get("commonName")
            r["tls"] = f"ok {ss.version()} cn={cn}"; ss.close()
        except Exception as e:  # noqa: BLE001
            r["tls"] = f"ERRO {type(e).__name__}: {str(e)[:140]}"
            return r
    else:
        s.close()
    t = time.time()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"}), timeout=45) as resp:
            corpo = resp.read(200000)
            r["http"] = f"{resp.status} {len(corpo)}b {time.time() - t:.1f}s server={resp.headers.get('Server')} tipo={resp.headers.get('Content-Type')} final={resp.geturl()[:90]}"
            r["inicio"] = corpo[:260].decode("utf-8", "replace").replace("\n", " ")
            r["muro"] = cb.detectar_muro_de_robo(corpo)
    except urllib.error.HTTPError as e:
        corpo = e.read(4000)
        r["http"] = f"HTTP {e.code} {time.time() - t:.1f}s server={e.headers.get('Server')} via={e.headers.get('Via')} tipo={e.headers.get('Content-Type')}"
        r["cabecalhos"] = {k: v[:80] for k, v in list(e.headers.items())[:22]}
        r["inicio"] = corpo[:700].decode("utf-8", "replace").replace("\n", " ")
    except Exception as e:  # noqa: BLE001
        r["http"] = f"ERRO {type(e).__name__}: {str(e)[:170]} ({time.time() - t:.1f}s)"
    return r


for nome, url in ALVOS:
    print("DIRETO", nome, "|", json.dumps(estagios(url), ensure_ascii=False)[:1500], flush=True)
    time.sleep(1)


def pedir(url, dados=None, cab=None, timeout=45):
    cab = dict({"User-Agent": UA, "Accept": "application/json"}, **(cab or {}))
    corpo = json.dumps(dados).encode() if dados is not None else None
    if corpo:
        cab["Content-Type"] = "application/json"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=corpo, headers=cab), timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8", "replace") or "null")
    except urllib.error.HTTPError as e:
        return e.code, e.read(600).decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return None, f"{type(e).__name__}: {e}"


# ---- Globalping: a mesma rota vista de sondas no Brasil (residencial, datacenter, nuvens em São Paulo) e fora
GRUPOS = [
    ("BR residencial", {"country": "BR", "tags": ["eyeball-network"], "limit": 4}),
    ("BR datacenter", {"country": "BR", "tags": ["datacenter-network"], "limit": 4}),
    ("GCP São Paulo", {"tags": ["gcp-southamerica-east1"], "limit": 1}),
    ("AWS São Paulo", {"tags": ["aws-sa-east-1"], "limit": 1}),
    ("Azure Brasil", {"tags": ["azure-brazilsouth"], "limit": 1}),
    ("EUA", {"country": "US", "limit": 3}),
    ("Alemanha", {"country": "DE", "limit": 2}),
]
ROTAS = [
    ("BA", "dool.egba.ba.gov.br", "/apifront/portal/edicoes/edicoes_from_data/2026-11-17.json", ""),
    ("MA", "diariooficial.ma.gov.br", "/ajax.busca.php", urllib.parse.urlparse(MA_BUSCA).query),
    ("MA-raiz", "diariooficial.ma.gov.br", "/", ""),
]
pendentes = []
for uf, host, caminho, query in ROTAS:
    for nome, loc in GRUPOS:
        req = {"method": "GET", "path": caminho}
        if query:
            req["query"] = query
        st, resp = pedir("https://api.globalping.io/v1/measurements",
                         {"type": "http", "target": host, "locations": [loc],
                          "measurementOptions": {"protocol": "HTTPS", "port": 443, "request": req}})
        if st in (200, 202) and isinstance(resp, dict) and resp.get("id"):
            pendentes.append((uf, nome, resp["id"]))
        else:
            print("GLOBALPING", uf, "|", nome, "| não medido:", st, str(resp)[:200], flush=True)
        time.sleep(1.2)
time.sleep(25)
for uf, nome, mid in pendentes:
    for _ in range(8):
        st, m = pedir(f"https://api.globalping.io/v1/measurements/{mid}")
        if isinstance(m, dict) and m.get("status") != "in-progress":
            break
        time.sleep(6)
    if not isinstance(m, dict):
        print("GLOBALPING", uf, "|", nome, "| sem resultado:", st, str(m)[:160], flush=True); continue
    for x in m.get("results") or []:
        p, res = x.get("probe") or {}, x.get("result") or {}
        saida = (res.get("rawOutput") or "")
        print("GLOBALPING", uf, "|", nome, "|", p.get("country"), p.get("city"), "| AS", p.get("asn"), (p.get("network") or "")[:34],
              "|", [t for t in (p.get("tags") or []) if "network" in t or "-" in t][:3],
              "| estado:", res.get("status"), "| HTTP:", res.get("statusCode"),
              "| total ms:", (res.get("timings") or {}).get("total"),
              "| saída:", saida[:150].replace("\n", " ") if res.get("statusCode") in (None, 0) or (res.get("statusCode") or 0) >= 400 else (res.get("rawBody") or "")[:90].replace("\n", " "),
              flush=True)

# ---- check-host.net: segunda opinião, nós do Brasil e de fora
st, nos = pedir("https://check-host.net/nodes/hosts")
if isinstance(nos, dict):
    todos = nos.get("nodes") or {}
    br = [n for n, v in todos.items() if (v.get("location") or [""])[0] == "br"]
    fora = [n for n, v in todos.items() if (v.get("location") or [""])[0] in ("us", "de", "fr", "nl")][:4]
    print("CHECKHOST nós BR:", br, "| fora:", fora, flush=True)
    for uf, alvo in (("BA", "https://dool.egba.ba.gov.br/"), ("MA", "https://diariooficial.ma.gov.br/")):
        q = "&".join("node=" + n for n in br + fora)
        st, r = pedir(f"https://check-host.net/check-http?host={Q(alvo, safe='')}&{q}")
        if not (isinstance(r, dict) and r.get("request_id")):
            print("CHECKHOST", uf, "| não medido:", st, str(r)[:200], flush=True); continue
        time.sleep(22)
        st, res = pedir(f"https://check-host.net/check-result/{r['request_id']}")
        for no, v in (res or {}).items() if isinstance(res, dict) else []:
            pais = ((todos.get(no) or {}).get("location") or ["?"])
            print("CHECKHOST", uf, "|", no, pais[:3], "|", json.dumps(v, ensure_ascii=False)[:230], flush=True)
else:
    print("CHECKHOST sem lista de nós:", st, str(nos)[:200], flush=True)

# ---- Internet Archive: quanto de cada diário foi capturado desde o início do ciclo
for host in ("dool.egba.ba.gov.br", "egbanet.egba.ba.gov.br", "diariooficial.ma.gov.br", "www.diariooficial.ma.gov.br"):
    url = ("http://web.archive.org/cdx/search/cdx?url=" + host + "&matchType=host&from=20260629&output=json"
           "&fl=timestamp,original,statuscode,mimetype,length&limit=4000")
    st, linhas = pedir(url, timeout=120)
    if not isinstance(linhas, list):
        print("ARQUIVO", host, "| sem resposta:", st, str(linhas)[:160], flush=True); continue
    linhas = linhas[1:]
    pdfs = [l for l in linhas if "pdf" in (l[3] or "") or "download" in l[1]]
    print("ARQUIVO", host, "| capturas desde 29/06:", len(linhas), "| de PDF ou download:", len(pdfs),
          "| exemplos:", [f"{l[0][:8]} {l[1][-60:]} {l[2]}" for l in (pdfs or linhas)[:6]], flush=True)
