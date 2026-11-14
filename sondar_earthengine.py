#!/usr/bin/env python3
"""Sonda (não grava em data/): a conta de serviço do Earth Engine autentica? Que forma têm os mapas de fogo e de água do
MapBiomas e que limites estaduais existem como asset público? A chave vem de EE_CHAVE_CONTA_SERVICO; nunca é impressa."""
import json, os, sys

chave, projeto = os.environ.get("EE_CHAVE_CONTA_SERVICO"), os.environ.get("EE_PROJETO")
if not chave or not projeto:
    sys.exit("sem EE_CHAVE_CONTA_SERVICO ou EE_PROJETO no ambiente: nada a sondar")
import ee
info = json.loads(chave)
ee.Initialize(ee.ServiceAccountCredentials(info["client_email"], key_data=chave), project=projeto)
print("autenticado no projeto", projeto)

ALVOS = ["projects/mapbiomas-public/assets/brazil/fire/monitor/mapbiomas_fire_monthly_burned_v1",
         "projects/mapbiomas-public/assets/brazil/fire/collection5_1/mapbiomas_fire_collection51_monthly_burned_v1"]
for a in ALVOS:
    try:
        meta = ee.data.getAsset(a)
        print("ASSET", a, meta.get("type"), json.dumps({k: meta.get(k) for k in ("startTime", "endTime", "bands", "properties")}, ensure_ascii=False)[:700])
        if meta.get("type") == "IMAGE_COLLECTION":
            col = ee.ImageCollection(a)
            print("   n =", col.size().getInfo(), "· índices:", col.aggregate_array("system:index").getInfo()[-8:])
            img = col.sort("system:time_start", False).first()
        else:
            img = ee.Image(a)
        print("   bandas:", img.bandNames().getInfo()[:30])
        print("   valores (amostra no Pantanal):", img.reduceRegion(ee.Reducer.frequencyHistogram(), ee.Geometry.Rectangle([-57.8, -19.2, -57.0, -18.4]), 300, maxPixels=1e9).getInfo())
    except Exception as e:  # noqa: BLE001
        print("ASSET", a, "ERRO", type(e).__name__, str(e)[:300])

for raiz in ("projects/mapbiomas-territories/assets", "projects/mapbiomas-public/assets/brazil", "projects/mapbiomas-public/assets/brazil/water"):
    try:
        print("LISTA", raiz, [x["name"] for x in ee.data.listAssets({"parent": raiz}).get("assets", [])][:40])
    except Exception as e:  # noqa: BLE001
        print("LISTA", raiz, "ERRO", type(e).__name__, str(e)[:200])
try:
    ufs = ee.FeatureCollection("FAO/GAUL/2015/level1").filter(ee.Filter.eq("ADM0_NAME", "Brazil"))
    print("GAUL estados:", ufs.size().getInfo())
except Exception as e:  # noqa: BLE001
    print("GAUL ERRO", str(e)[:200])
