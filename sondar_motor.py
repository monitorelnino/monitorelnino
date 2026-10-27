"""Sonda descartável (ramo coleta-dia, nunca mesclado): só mede, não escreve em data/.
Por que o SearXNG devolve results==[] nas fontes S20/S21/S23/S31? Imprime, por consulta, n de resultados e
`unresponsive_engines` (o motivo que cada motor de origem deu), e depois uma consulta por motor."""
import json, time, sys
import buscar_planos_fontes_abertas as bp
import monitorar_busca_web as mw

mun = json.load(open("data/municipios_prioritarios.json"))["municipios"]
amostra = mun[::105][:20]
FONTES = ["S20", "S21", "S23", "S31"]
CURTA = {"S20": 'plano de contingência site:mp.br', "S21": 'plano de contingência site:jus.br',
         "S23": 'plano de contingência dengue site:gov.br', "S31": 'plano de contingência convênio site:gov.br'}

def uma(rotulo, q, motores=None):
    t = time.time()
    try:
        d = mw.buscar_searxng(q, timeout=40, motores=motores)
        n = len(d.get("results") or [])
        un = d.get("unresponsive_engines") or []
        print(f"{rotulo} n={n} un={json.dumps(un, ensure_ascii=False)} t={time.time()-t:.1f}s q={q[:90]}", flush=True)
        return n
    except Exception as e:
        print(f"{rotulo} EXC {type(e).__name__}: {str(e)[:100]} q={q[:90]}", flush=True)
        return -1

print("== A. completa x curta, 20 municípios")
tot = {}
for m in amostra:
    for f in FONTES:
        for tipo, q in (("cheia", bp.consulta_web(f, m["nome"], m["uf"])), ("curta", f'"{m["nome"]}" {m["uf"]} {CURTA[f]}')):
            n = uma(f"{m['uf']}/{m['nome']} {f} {tipo}", q)
            tot.setdefault((f, tipo), []).append(n)
            time.sleep(3)
print("== resumo (consultas com n>0 / total)")
for k, v in sorted(tot.items()):
    print(k, sum(1 for n in v if n > 0), "/", len(v))

print("== B. motor a motor (1 município, 3 consultas)")
m = amostra[3]
for motor in ["google", "bing", "duckduckgo", "brave", "startpage", "mojeek", "qwant", "yahoo", "wikipedia"]:
    for f in ("S20", "S23"):
        uma(f"motor={motor} {f}", bp.consulta_web(f, m["nome"], m["uf"]), [motor]); time.sleep(3)
    uma(f"motor={motor} simples", f'"{m["nome"]}" plano de contingência', [motor]); time.sleep(3)
