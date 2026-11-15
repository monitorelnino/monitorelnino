"""Sonda (não grava em data/): cada host responde ao runner? Classe: ok, http_<código>, conexao (timeout/DNS/rede)."""
import json, urllib.error, concurrent.futures as cf
import coletores_base as c
A = json.load(open("sonda_hosts.json"))
def um(h, u):
    try:
        c.buscar_uma_vez(u, timeout=20, origem="sonda de hosts da ponte"); return h, "ok", u
    except urllib.error.HTTPError as e: return h, f"http_{e.code}", u
    except c.MuroDeRobo as e: return h, "muro", u
    except Exception as e: return h, "conexao:" + type(e).__name__ + ":" + str(e)[:60], u
with cf.ThreadPoolExecutor(12) as ex:
    for h, cl, u in ex.map(lambda kv: um(*kv), A.items()):
        print("SONDA", cl, h, u, flush=True)
