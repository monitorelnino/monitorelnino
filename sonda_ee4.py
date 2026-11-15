"""Sonda 4 (não grava em data/): a imagem de territórios do MapBiomas e o tempo de uma soma por célula, agrupada por estado."""
import os, time
import google.auth
import ee
cred, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/earthengine", "https://www.googleapis.com/auth/cloud-platform"])
ee.Initialize(credentials=cred, project=os.environ["GEE_PROJECT"])
B = "projects/mapbiomas-public/assets/brazil/"
T = ee.Image("projects/mapbiomas-territories/assets/TERRITORIES/LULC/BRAZIL/COLLECTION10/territory-collection")

def tenta(rotulo, f):
    t = time.time()
    try: print(rotulo, "→", str(f())[:1500], f"({time.time() - t:.0f}s)", flush=True)
    except Exception as e: print(rotulo, "ERRO", str(e)[:300], f"({time.time() - t:.0f}s)", flush=True)

TC = ee.ImageCollection("projects/mapbiomas-territories/assets/TERRITORIES/LULC/BRAZIL/COLLECTION10/territory-collection")
tenta("TERRITÓRIOS n", lambda: TC.size().getInfo())
tenta("TERRITÓRIOS ids", lambda: TC.aggregate_array("system:index").getInfo())
tenta("TERRITÓRIOS props da primeira", lambda: (TC.first().bandNames().getInfo(), TC.first().toDictionary().getInfo(), TC.first().projection().nominalScale().getInfo()))
cel = lambda x, y, d: ee.Geometry.Rectangle([x, y, x + d, y + d], None, False)
ids = TC.aggregate_array("system:index").getInfo()
cand = [i for i in ids if "state" in i.lower() or "political_level_2" in i.lower() or "estado" in i.lower()]
print("CANDIDATAS A ESTADO:", cand, flush=True)
for i in (cand or ids)[:6]:
    im = ee.Image(TC.filter(ee.Filter.eq("system:index", i)).first())
    tenta(f"VALORES {i}", lambda: (im.bandNames().getInfo(), im.reduceRegion(ee.Reducer.frequencyHistogram(), cel(-58, -11, 4), scale=1000, maxPixels=1e9).getInfo()))
T = ee.Image(TC.filter(ee.Filter.eq("system:index", cand[0])).first()) if cand else None
nomes = T.bandNames().getInfo() if T else []
ha = ee.Image.pixelArea().divide(1e4)
col = ee.ImageCollection(B + "fire/monitor/mapbiomas_fire_monthly_burned_v1")
ano = col.filter(ee.Filter.eq("year", 2024)).sort("month")
tenta("MONITOR 2024 meses", lambda: ano.aggregate_array("month").getInfo())
pilha = ano.toBands().gt(0).multiply(ha)
c51 = ee.Image(B + "fire/collection5_1/mapbiomas_fire_collection51_monthly_burned_v1").select("burned_monthly_2024")
w = ee.Image(B + "water/collection5/mapbiomas_brazil_collection5_water_annual_v4")
tenta("ÁGUA valores 2025", lambda: w.select("classification_2025").reduceRegion(ee.Reducer.frequencyHistogram(), cel(-58, -11, 2), scale=300, maxPixels=1e9).getInfo())
tenta("COLEÇÃO valores 2024", lambda: c51.reduceRegion(ee.Reducer.frequencyHistogram(), cel(-58, -11, 2), scale=300, maxPixels=1e9).getInfo())
tenta("MONITOR valores 2024-9", lambda: ee.Image(B + "fire/monitor/mapbiomas_fire_monthly_burned_v1/brazil-2024-9").reduceRegion(ee.Reducer.frequencyHistogram(), cel(-58, -11, 2), scale=300, maxPixels=1e9).getInfo())
uf = nomes[0] if nomes else None
print("BANDA DE ESTADO escolhida:", uf, flush=True)
if uf:
    for d in (1, 2, 4):
        g = cel(-58, -13, d)
        tenta(f"SOMA monitor 2024 (12 bandas) por estado, célula {d}°", lambda: pilha.addBands(T.select(uf)).reduceRegion(ee.Reducer.sum().repeat(12).group(12, "uf"), g, scale=30, maxPixels=1e13).getInfo())
        tenta(f"SOMA coleção 2024 por estado e mês, célula {d}°", lambda: ha.addBands(T.select(uf).multiply(100).add(c51)).updateMask(c51.gt(0)).reduceRegion(ee.Reducer.sum().group(1, "ufmes"), g, scale=30, maxPixels=1e13).getInfo())
        tenta(f"SOMA água 41 anos por estado, célula {d}°", lambda: w.gt(0).multiply(ha).addBands(T.select(uf)).reduceRegion(ee.Reducer.sum().repeat(41).group(41, "uf"), g, scale=30, maxPixels=1e13).getInfo())
