"""Sonda (ramo de válvula, nunca mesclado): quais sites das pistas pendentes do juiz respondem ao robô.
Só DNS, conexão e /robots.txt com o cliente identificado; não grava nada."""
import sys, json, socket, ssl, datetime, collections, concurrent.futures as cf
import urllib.request, urllib.error, urllib.parse
sys.path[:0] = ["scripts", "."]
import coletores_base as cb
import julgar_filas as jf

UA = cb.ua_de("sonda de alcance")
hoje = datetime.date.today()
hosts = collections.Counter()
for f in jf.FILAS:
    for p in jf.pistas_da_fila(cb.ler(f) or {}):
        if jf.pendente(p, hoje):
            h = (urllib.parse.urlparse(jf.url_da_pista(p) or "").netloc or "").lower()
            if h:
                hosts[h] += 1
print(f"hosts das pistas pendentes: {len(hosts)} · pistas: {sum(hosts.values())}", flush=True)


def medir(host):
    try:
        socket.gethostbyname(host)
    except Exception:  # noqa: BLE001
        return "dns"
    err, porta = "", None
    for p in (443, 80):
        try:
            socket.create_connection((host, p), timeout=10).close()
            porta = p
            break
        except socket.timeout:
            err = "timeout"
        except ConnectionRefusedError:
            err = "recusada"
        except Exception as e:  # noqa: BLE001
            err = type(e).__name__
    if porta is None:
        return f"sem conexão ({err})"
    try:
        req = urllib.request.Request(f"{'https' if porta == 443 else 'http'}://{host}/robots.txt", headers={"User-Agent": UA})
        kw = {"context": cb.contexto_tls()} if porta == 443 else {}
        with urllib.request.urlopen(req, timeout=20, **kw) as r:
            corpo = r.read(60000)
            muro = cb.detectar_muro_de_robo(corpo)
            return f"muro ({muro[:40]})" if muro else f"HTTP {r.status}"
    except urllib.error.HTTPError as e:
        try:
            muro = cb.muro_no_erro(e)
        except Exception:  # noqa: BLE001
            muro = None
        return f"muro ({str(muro)[:40]})" if muro else f"HTTP {e.code}"
    except urllib.error.URLError as e:
        r = e.reason
        if isinstance(r, ssl.SSLCertVerificationError):
            return f"certificado ({r.verify_code}: {r.verify_message})"
        if isinstance(r, ssl.SSLError):
            return f"tls ({str(r.reason or r)[:50]})"
        return f"conecta:{porta}, sem resposta ({type(r).__name__}: {str(r)[:40]})"
    except Exception as e:  # noqa: BLE001
        return f"conecta:{porta}, sem resposta ({type(e).__name__}: {str(e)[:40]})"


with cf.ThreadPoolExecutor(32) as ex:
    res = dict(zip(hosts, ex.map(medir, hosts)))
# quem falhou ganha uma segunda medida (falha passageira não vira classe)
refazer = [h for h, r in res.items() if not r.startswith(("HTTP", "muro", "dns", "certificado"))]
with cf.ThreadPoolExecutor(16) as ex:
    res2 = dict(zip(refazer, ex.map(medir, refazer)))
for h, r in res2.items():
    if r.startswith(("HTTP", "muro")):
        res[h] = r + " (na 2ª medida)"
classe = lambda r: r.split(" (")[0].split(":")[0] if not r.startswith("HTTP") else "responde"
c = collections.Counter(); pistas = collections.Counter()
for h, r in res.items():
    c[classe(r)] += 1; pistas[classe(r)] += hosts[h]
print("CLASSES (hosts):", dict(c), "· (pistas):", dict(pistas), flush=True)
print("RESULTADO_JSON " + json.dumps({h: [res[h], hosts[h]] for h in hosts}, ensure_ascii=False, separators=(",", ":")), flush=True)
