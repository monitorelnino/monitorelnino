"""Sonda 2 (ramo de válvula, nunca mesclado): host irmão do diário da BA, Internet Archive do MA e o TLS do portal de legislação da BA."""
import sys, json, socket, ssl, time, urllib.request, urllib.error, urllib.parse
sys.path[:0] = ["scripts", "."]
import coletores_base as cb

UA = cb.ua_de("sonda de rota de diario oficial")
Q = urllib.parse.quote


def get(url, timeout=45, n=1200):
    t = time.time()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"}), timeout=timeout) as r:
            c = r.read(400000)
            return f"{r.status} {len(c)}b {time.time() - t:.1f}s tipo={r.headers.get('Content-Type')} final={r.geturl()[:110]} | {c[:n].decode('utf-8', 'replace')}".replace("\n", " ")
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code} www-auth={e.headers.get('WWW-Authenticate')} local={e.headers.get('Location')} | {e.read(300).decode('utf-8', 'replace')}".replace("\n", " ")
    except Exception as e:  # noqa: BLE001
        return f"ERRO {type(e).__name__}: {str(e)[:160]} ({time.time() - t:.1f}s)"


B = "https://egbanet.egba.ba.gov.br"
for nome, url in [
    ("egbanet ultimas", B + "/apifront/portal/edicoes/ultimas_edicoes.json?subtheme=false"),
    ("egbanet edicoes 17/11", B + "/apifront/portal/edicoes/edicoes_from_data/2026-11-17.json"),
    ("egbanet busca", B + "/busca/busca/buscar/query/0/di:2026-06-29/df:2026-11-18/?1=1&q=" + Q('"emergência em saúde pública"')),
    ("egbanet alba ultimas", B + "/alba/apifront/portal/edicoes/ultimas_edicoes.json?subtheme=false"),
    ("egbanet robots", B + "/robots.txt"),
]:
    print("EGBANET", nome, "|", get(url, n=420), flush=True)
    time.sleep(2)

# o portal de legislação da BA: a falha é de criptografia antiga do servidor ou de rede?
host = "www.legislabahia.ba.gov.br"
for nome, prep in [
    ("padrão", lambda c: None),
    ("só TLS 1.2", lambda c: setattr(c, "maximum_version", ssl.TLSVersion.TLSv1_2)),
    ("TLS 1.2 com cifras antigas aceitas (nível 1)", lambda c: (setattr(c, "maximum_version", ssl.TLSVersion.TLSv1_2), c.set_ciphers("DEFAULT:@SECLEVEL=1"))),
    ("TLS 1.2, nível 0, cifras RSA/3DES", lambda c: (setattr(c, "maximum_version", ssl.TLSVersion.TLSv1_2), setattr(c, "minimum_version", ssl.TLSVersion.TLSv1), c.set_ciphers("ALL:@SECLEVEL=0"))),
]:
    try:
        c = ssl.create_default_context(); prep(c)
        s = socket.create_connection((host, 443), timeout=15)
        ss = c.wrap_socket(s, server_hostname=host)
        print("LEGISLA TLS", nome, "| ok", ss.version(), ss.cipher(), flush=True); ss.close()
    except Exception as e:  # noqa: BLE001
        print("LEGISLA TLS", nome, "| ERRO", type(e).__name__, str(e)[:150], flush=True)


def pedir(url, dados=None, timeout=60):
    cab = {"User-Agent": UA, "Accept": "application/json"}
    corpo = json.dumps(dados).encode() if dados is not None else None
    if corpo:
        cab["Content-Type"] = "application/json"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=corpo, headers=cab), timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8", "replace") or "null")
    except urllib.error.HTTPError as e:
        return e.code, e.read(300).decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return None, f"{type(e).__name__}: {e}"


pend = []
for nome, loc in [("BR", {"country": "BR", "limit": 3}), ("EUA", {"country": "US", "limit": 2}), ("Alemanha", {"country": "DE", "limit": 1})]:
    st, r = pedir("https://api.globalping.io/v1/measurements", {"type": "http", "target": host, "locations": [loc],
                  "measurementOptions": {"protocol": "HTTPS", "port": 443, "request": {"method": "GET", "path": "/documentos", "query": "categoria%5B0%5D=2"}}})
    if isinstance(r, dict) and r.get("id"):
        pend.append((nome, r["id"]))
    else:
        print("GLOBALPING legisla", nome, "| não medido:", st, str(r)[:160], flush=True)
    time.sleep(1.2)
time.sleep(25)
for nome, mid in pend:
    for _ in range(8):
        st, m = pedir(f"https://api.globalping.io/v1/measurements/{mid}")
        if isinstance(m, dict) and m.get("status") != "in-progress":
            break
        time.sleep(6)
    for x in (m.get("results") or []) if isinstance(m, dict) else []:
        p, res = x.get("probe") or {}, x.get("result") or {}
        print("GLOBALPING legisla", nome, "|", p.get("country"), p.get("city"), (p.get("network") or "")[:28], "| estado:", res.get("status"), "| HTTP:", res.get("statusCode"),
              "|", (res.get("rawOutput") or "")[:110].replace("\n", " ") if not res.get("statusCode") else "", flush=True)

for host2 in ("diariooficial.ma.gov.br", "www.diariooficial.ma.gov.br"):
    for tentativa in range(4):
        st, linhas = pedir("http://web.archive.org/cdx/search/cdx?url=" + host2 + "&matchType=host&from=20260629&output=json&fl=timestamp,original,statuscode,mimetype&limit=4000", timeout=120)
        if isinstance(linhas, list):
            break
        time.sleep(40)
    if not isinstance(linhas, list):
        print("ARQUIVO", host2, "| sem resposta:", st, str(linhas)[:120], flush=True); continue
    linhas = linhas[1:]
    pdfs = [l for l in linhas if "pdf" in (l[3] or "") or "download.php" in l[1] or "ajax" in l[1]]
    print("ARQUIVO", host2, "| capturas desde 29/06:", len(linhas), "| de PDF, download ou busca:", len(pdfs), "| exemplos:", [f"{l[0][:8]} {l[1][-56:]} {l[2]}" for l in (pdfs or linhas)[:6]], flush=True)
