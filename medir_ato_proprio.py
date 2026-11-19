"""Medição de uma vez (19/11/2026, não vai à main): decisões cujo ato muda com `ato_proprio`, antes e depois."""
import json, re, sys, collections
import juiz, juiz_main
dec = json.load(open("data/promocoes_automaticas.json"))["decisoes"]
vig = {}
for d in dec:
    if d.get("hash_evidencia"):
        vig[(d.get("pista_id"), d.get("url"), d.get("municipio"), d.get("uf"))] = d
mud, cont, vistos = [], collections.Counter(), set()
for d in vig.values():
    h = d["hash_evidencia"]
    if (h, d.get("municipio")) in vistos:
        continue
    vistos.add((h, d.get("municipio")))
    t = juiz.texto_local_18(h)
    if not t.strip():
        cont["sem_texto"] += 1; continue
    cont["com_texto"] += 1
    t20 = t[:juiz.TETO_DO_JULGAMENTO]
    a, b = juiz_main.RE_TIPO_E_NUMERO.search(t20), juiz.ato_proprio(t20)
    if (a and a.start()) == (b and b.start()):
        continue
    kw = dict(nome=d.get("municipio") or "", uf=d.get("uf") or "", ibge=d.get("ibge"), url=d.get("url"))
    try:
        va, vb = juiz_main.julgar(t, **kw), juiz.julgar(t, **kw)
    except Exception as e:
        cont["erro"] += 1; print("ERRO", d.get("municipio"), e); continue
    cont["ato_muda"] += 1
    if (va["promove"], va.get("motivo"), va.get("categoria")) != (vb["promove"], vb.get("motivo"), vb.get("categoria")):
        cont["veredito_muda"] += 1
        cont[f"{va['promove']}->{vb['promove']}"] += 1
        mud.append((d.get("municipio"), d.get("uf"), va["promove"], va.get("motivo"), va.get("categoria"),
                    vb["promove"], vb.get("motivo"), vb.get("categoria"), vb.get("data"), (d.get("url") or "")[-90:],
                    (a.group(0)[:40] if a else None)))
print("RESUMO", dict(cont))
for m in sorted(mud, key=lambda x: (not x[5], x[1], x[0])):
    print("MUDA", json.dumps(m, ensure_ascii=False))
