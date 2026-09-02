#!/usr/bin/env python3
"""Decisão C10 (doc de redesenho 02/09/2026): registros PONTUÁVEIS apoiados apenas
em imprensa (canal == "imprensa") violam a regra de prova (§3.1 da transferência:
documento primário) e são rebaixados a PISTA — categoria `nao_verificado`, com a
citação original preservada em data/pistas_imprensa.json (status "rebaixado_c10")
e errata pública em data/erratas_v224.json com o efeito na nota. Correção de dado,
não de método (C6): permitida no defeso. Idempotente."""
import json, sys, datetime
D = "data/"; PONT = {"plano", "plano_antigo", "plano_elaboracao", "coberto_estadual"}
def j(n): return json.load(open(D + n, encoding="utf-8"))
def w(n, o):
    json.dump(o, open(D + n, "w", encoding="utf-8"), ensure_ascii=False, indent=1); open(D + n, "a").write("\n")
mun = j("municipios.json"); pistas = j("pistas_imprensa.json"); pistas.setdefault("pistas", [])
try: err = j("erratas_v224.json")
except FileNotFoundError: err = []
hoje = datetime.date.today().strftime("%d/%m/%Y"); n = 0
for m in mun:
    if m["categoria"] in PONT and m.get("canal") == "imprensa":
        pistas["pistas"].append({"municipio": m["nome"], "uf": m["uf"], "origem": "rebaixamento C10", "categoria_anterior": m["categoria"],
            "documento": m.get("documento"), "fonte": m.get("fonte"), "url": m.get("url"), "data": m.get("data"),
            "registrado_em": hoje, "status": "rebaixado_c10 — volta a registro só com documento primário (ato com número e data, em fonte oficial)"})
        err.append({"data": hoje, "municipio": m["nome"], "uf": m["uf"], "de": m["categoria"], "para": "nao_verificado",
            "motivo": "C10 (02/09/2026): registro pontuável apoiado apenas em imprensa; regra de prova exige documento primário",
            "efeito_na_nota": "cobertura populacional da UF reduzida (valor no CHANGELOG, por UF)"})
        m["categoria"] = "nao_verificado"; m["canal"] = "imprensa"; n += 1
if n:
    w("municipios.json", mun); w("pistas_imprensa.json", pistas); w("erratas_v224.json", err)
    p = j("pontos_mapa.json"); porm = {(x["nome"], x["uf"]): x["categoria"] for x in mun}
    for x in p:
        if (x.get("nome"), x.get("uf")) in porm: x["categoria"] = porm[(x["nome"], x["uf"])]
    w("pontos_mapa.json", p)
print(f"C10: {n} registro(s) rebaixado(s) a pista")
