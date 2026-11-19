"""Diagnóstico de uma vez (19/11): as 11 promoções do rejulgamento, de novo pelo juiz em vigor (#1944)."""
import sys, json
sys.path.insert(0, "scripts")
import julgar_filas as jf
from julgar_e_aplicar_descobertas import buscar_texto
ids = sys.argv[1].split(",")
doc = json.load(open("data/pistas_imprensa.json"))
for p in jf.pistas_da_fila(doc):
    if str(p.get("id")) in ids:
        v = jf.julgar_uma(p, buscar_texto, None)
        j = p.get("juiz") or {}
        print("ONZE", json.dumps([p.get("municipio"), p.get("uf"), j.get("categoria"), j.get("data"), "->", v.get("promove"),
                                  v.get("motivo"), v.get("categoria"), v.get("data"), v.get("regras_18")], ensure_ascii=False))
