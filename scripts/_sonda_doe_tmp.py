"""Sonda temporária (ramo diag): adaptador AC de ponta a ponta, do runner."""
import sys, json, time
sys.path.insert(0, ".")
import coletar_doe as c
t0 = time.time()
itens, totais = c.itens_por_busca("AC", "2026-09-14", c.EDICOES_POR_BUSCA["busca_ac"]("2026-09-14", "2026-10-14"))
print("TOTAIS", totais, "itens", len(itens), "seg", int(time.time() - t0))
for it in itens[:10]:
    print(json.dumps({k: (v if k != "trechos" else [t[:160] for t in v]) for k, v in it.items()}, ensure_ascii=False))
print("HOMOLOGACOES", [h for it in itens for t in it["trechos"] for h in c.homologacoes_no_texto(t)][:10])
