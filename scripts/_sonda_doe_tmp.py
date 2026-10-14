"""Sonda temporária (ramo diag): adaptador PI de ponta a ponta, do runner."""
import sys, json
sys.path.insert(0, ".")
import coletar_doe as c
itens, totais = c.itens_por_busca("PI", "2026-07-01", c.EDICOES_POR_BUSCA["busca_pi"]("2026-07-01", "2026-10-14"))
print("TOTAIS", totais, "itens", len(itens))
for it in itens[:8]:
    print(json.dumps({k: (v if k != "trechos" else [t[:200] for t in v]) for k, v in it.items()}, ensure_ascii=False))
print("HOMOLOGACOES", [h for it in itens for t in it["trechos"] for h in c.homologacoes_no_texto(t)][:10])
