"""Sonda de alcance (ramo de válvula, nunca mesclado): quais hosts que falham na rede para o robô
respondem a quem pede do Brasil. Mede daqui (executor do GitHub) e do Brasil (sondas públicas do
Globalping), pedindo só /robots.txt. Não grava nada."""
import sys, json, re, socket, time, random, collections, concurrent.futures as cf
import urllib.request, urllib.error, urllib.parse
sys.path[:0] = ["scripts", "."]
import coletores_base as cb

UA = cb.ua_de("sonda de alcance")
RAIZ = cb.RAIZ


def host_de(u):
    return (urllib.parse.urlparse(u).netloc or "").lower()


grupos = collections.OrderedDict()   # host -> grupo
# 1. diários oficiais estaduais (a rota de cada UF) + os dois da BA e o do MA
for uf, v in ((json.load(open(RAIZ / "data/fontes_doe.json")).get("ufs")) or {}).items():
    h = host_de(v.get("url") or "")
    if h:
        grupos[h] = f"diário {uf}"
for h, g in [("dool.egba.ba.gov.br", "diário BA"), ("egbanet.egba.ba.gov.br", "diário BA (irmão)"),
             ("diariooficial.ma.gov.br", "diário MA"), ("www.diario.pi.gov.br", "diário PI"),
             ("diariooficial.to.gov.br", "diário TO"), ("www.spdo.ms.gov.br", "diário MS (listagem)")]:
    grupos[h] = g
# 2. hosts dos pedidos da ponte sem cópia
copias = (json.load(open(RAIZ / "data/ponte_brasil.json")).get("copias")) or {}
for p in json.load(open(RAIZ / "data/ponte_pedidos.json")).get("pedidos") or []:
    h = host_de(p.get("url") or "")
    if h and "." in h and p["url"] not in copias:
        grupos.setdefault(h, "pedido")
# 3. portais municipais não verificados por falha de rede em novembro (amostra)
rede, dns = {}, {}
try:
    for linha in open(RAIZ / "data/log_buscas/2026-11.jsonl", encoding="utf-8", errors="replace"):
        if "portal_nao_verificado" not in linha:
            continue
        try:
            e = json.loads(linha)
        except Exception:  # noqa: BLE001
            continue
        r = str(e.get("resultados") or "")
        por = collections.defaultdict(set)
        for u, err in re.findall(r"(https?://[^:\s;]+)\s*:\s*([^;]+)", r):
            por[re.sub(r"^www\.", "", host_de(u))].add(err.strip()[:30])
        for h, errs in por.items():
            alvo, outro = (dns, rede) if all("DNS" in x for x in errs) else (rede, dns)
            alvo[h] = (e.get("uf") or "?", sorted(errs))
            outro.pop(h, None)
except FileNotFoundError:
    print("log de novembro ausente neste checkout")
rnd = random.Random(18112026)
am_rede = rnd.sample(sorted(rede), min(60, len(rede)))
am_dns = rnd.sample(sorted(dns), min(20, len(dns)))
for h in am_rede:
    grupos.setdefault(h, f"município {rede[h][0]} (rede)")
for h in am_dns:
    grupos.setdefault(h, f"município {dns[h][0]} (DNS)")
print(f"hosts a medir: {len(grupos)} · municipais com falha de rede no log: {len(rede)} (amostra {len(am_rede)}) · só DNS: {len(dns)} (amostra {len(am_dns)})", flush=True)


def daqui(host):
    try:
        socket.gethostbyname(host)
    except Exception:  # noqa: BLE001
        return "dns"
    err, porta = "", None
    for p in (443, 80):
        try:
            socket.create_connection((host, p), timeout=8).close()
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
        with urllib.request.urlopen(req, timeout=15, **kw) as r:
            return f"HTTP {r.status}"
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001
        return f"conecta:{porta}, sem resposta ({type(e).__name__}: {str(e)[:50]})"


with cf.ThreadPoolExecutor(24) as ex:
    medido = dict(zip(grupos, ex.map(daqui, grupos)))
print("daqui:", collections.Counter(re.sub(r"\(.*", "", v).strip() if not v.startswith("HTTP") else "HTTP (responde)" for v in medido.values()).most_common(), flush=True)


def pedir(url, dados=None, timeout=40):
    cab = {"User-Agent": UA, "Accept": "application/json"}
    corpo = json.dumps(dados).encode() if dados is not None else None
    if corpo:
        cab["Content-Type"] = "application/json"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=corpo, headers=cab), timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8", "replace") or "null")
    except urllib.error.HTTPError as e:
        return e.code, e.read(200).decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return None, f"{type(e).__name__}: {e}"


def medir_do_brasil(hosts, n, protocolo="HTTPS", porta=443):
    ids, parou = {}, None
    for h in hosts:
        if parou:
            break
        st, r = pedir("https://api.globalping.io/v1/measurements", {
            "type": "http", "target": h, "locations": [{"country": "BR", "limit": n}],
            "measurementOptions": {"protocol": protocolo, "port": porta, "request": {"method": "GET", "path": "/robots.txt"}}})
        if isinstance(r, dict) and r.get("id"):
            ids[h] = r["id"]
        elif st == 429:
            parou = f"limite do Globalping atingido em {h}"
        else:
            ids[h] = None
        time.sleep(1.3)
    if parou:
        print(parou, flush=True)
    time.sleep(20)
    saida = {}
    for h, mid in ids.items():
        if not mid:
            saida[h] = ["não medido"]
            continue
        m = None
        for _ in range(10):
            st, m = pedir(f"https://api.globalping.io/v1/measurements/{mid}")
            if isinstance(m, dict) and m.get("status") != "in-progress":
                break
            time.sleep(5)
        res = []
        for x in (m.get("results") or []) if isinstance(m, dict) else []:
            rr, pb = x.get("result") or {}, x.get("probe") or {}
            if rr.get("statusCode"):
                res.append(f"HTTP {rr['statusCode']} [{(pb.get('network') or '')[:18]}]")
            else:
                res.append("falha: " + re.sub(r"\s+", " ", (rr.get("rawOutput") or rr.get("status") or "?"))[:60])
        saida[h] = res or ["sem resultado"]
    return saida


diarios = [h for h, g in grupos.items() if g.startswith("diário")]
resto = [h for h, g in grupos.items() if not g.startswith("diário")]
do_br = medir_do_brasil(diarios, 2)
do_br.update(medir_do_brasil(resto, 1))
# quem falhou em HTTPS no Brasil sem ser DNS ganha uma medida em HTTP simples (porta 80), até 30 hosts
refazer = [h for h, r in do_br.items() if not any(x.startswith("HTTP") for x in r) and not any("ENOTFOUND" in x or "não medido" in x for x in r)][:30]
http80 = medir_do_brasil(refazer, 1, "HTTP", 80) if refazer else {}


def classe(h):
    aqui_ok = medido[h].startswith("HTTP")
    br = do_br.get(h, ["não medido"]) + http80.get(h, [])
    br_ok = any(x.startswith("HTTP") for x in br)
    if any("não medido" in x for x in br) and not br_ok:
        return "não medido do Brasil"
    if aqui_ok and br_ok:
        return "responde aos dois (falha passageira)"
    if not aqui_ok and br_ok:
        return "SÓ RESPONDE DO BRASIL"
    if aqui_ok and not br_ok:
        return "responde aqui, falhou na sonda do Brasil"
    return "não existe no DNS (aqui e no Brasil)" if medido[h] == "dns" and any("ENOTFOUND" in x for x in br) else "fora do ar para os dois"


final = {h: {"grupo": g, "daqui": medido[h], "br": do_br.get(h, []) + [f"(porta 80) {x}" for x in http80.get(h, [])], "classe": classe(h)} for h, g in grupos.items()}
for nome, filtro in [("diários e pedidos", lambda g: not g.startswith("município")), ("municípios (rede)", lambda g: g.endswith("(rede)")), ("municípios (DNS)", lambda g: g.endswith("(DNS)"))]:
    c = collections.Counter(v["classe"] for v in final.values() if filtro(v["grupo"]))
    print(f"CLASSES · {nome}: {dict(c)}", flush=True)
for h, v in final.items():
    if not v["grupo"].startswith("município"):
        print(f"HOST {v['classe']} | {h} | {v['grupo']} | daqui: {v['daqui']} | BR: {'; '.join(v['br'])}", flush=True)
print("RESULTADO_JSON " + json.dumps(final, ensure_ascii=False, separators=(",", ":")), flush=True)
