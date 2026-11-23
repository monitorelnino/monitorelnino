"""Área queimada (MapBiomas, Monitor do Fogo) por município do Pará e mês, 2024–2026 (relatório do Marajó; não vai à main)."""
import json, pathlib
import coletar_mapbiomas as mb
ee = mb._ee()
ids = ee.ImageCollection(mb.TERRITORIOS).aggregate_array("system:index").getInfo()
cand = [i for i in ids if "MUNIC" in i.upper()]
print("camadas", len(ids), cand, flush=True)
out = {"camadas_municipais": cand, "todas": ids}
try:
    idx = next(i for i in cand if "MUNICIPIOS_IBGE" in i)
    mun = ee.Image(ee.ImageCollection(mb.TERRITORIOS).filter(ee.Filter.eq("system:index", idx)).first()).rename("uf")
    ref = [m for m in json.load(open("data/municipios_ibge_referencia.json")) if m["uf"] == "PA"]
    pts = ee.FeatureCollection([ee.Feature(ee.Geometry.Point([m["lon"], m["lat"]]), {"ibge": str(m["codigo_ibge"])}) for m in ref])
    lidos = mun.reduceRegions(pts, ee.Reducer.first(), 30).getInfo()["features"]
    mapa = {}
    for f in lidos:
        v = f["properties"].get("first")
        if v is not None:
            mapa.setdefault(int(v), []).append(f["properties"]["ibge"])
    out["camada"] = idx; out["mapa"] = mapa
    mb.CAIXA = (-59, -10, -46, 3)
    col = ee.ImageCollection(mb.MONITOR)
    out["meses"] = {}
    for ano, meses in ((2024, range(1, 13)), (2025, range(1, 13)), (2026, range(1, 11))):
        imgs = [col.filter(ee.Filter.eq("year", ano)).filter(ee.Filter.eq("month", m)).first() for m in meses]
        pilha = ee.Image.cat([ee.Image(i).gt(0).unmask(0).multiply(mb._ha(ee)) for i in imgs])
        soma = mb._reduzir(ee, pilha, mun, len(list(meses)), 1)
        for i, m in enumerate(meses):
            out["meses"][f"{ano}-{m:02d}"] = {str(k): round(v[i], 1) for k, v in soma.items() if v[i]}
        print(ano, "ok", len(soma), flush=True)
except Exception as e:  # noqa: BLE001
    out["erro"] = f"{type(e).__name__}: {str(e)[:400]}"; print("FALHA", out["erro"], flush=True)
pathlib.Path("saida_zoneamento").mkdir(exist_ok=True)
json.dump(out, open("saida_zoneamento/fogo_municipal_pa.json", "w"))
