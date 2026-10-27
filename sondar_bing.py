"""Sonda descartável (ramo coleta-dia, não mesclar): casos que a main registra como `lido` (vários motores) —
o Bing sozinho os acha? Imprime hosts dos resultados e o veredito de `ler_web`. Só mede."""
import json, time
import buscar_planos_fontes_abertas as bp
import monitorar_busca_web as mw

def nome_de(consulta): return consulta.split('"')[1]

for uf, cod, fonte, consulta in json.load(open("casos_lidos.json")):
    nome = nome_de(consulta)
    for rotulo, motores in (("multi", None), ("bing", ["bing"])):
        try:
            d = mw.buscar_searxng(consulta, timeout=40, motores=motores)
            res = d.get("results") or []
            hosts = [bp._host(r.get("url") or "") for r in res[:10]]
            ach = bp.ler_web(d, nome, fonte)
            print(f"{uf}/{nome} {fonte} {rotulo}: n={len(res)} lido={len(ach)} un={[e[0] for e in d.get('unresponsive_engines', [])]} hosts={hosts[:6]}", flush=True)
        except Exception as e:
            print(f"{uf}/{nome} {fonte} {rotulo}: EXC {type(e).__name__} {str(e)[:80]}", flush=True)
        time.sleep(4)
