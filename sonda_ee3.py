"""Sonda 3 (não grava em data/): territórios de estado no Earth Engine, escala dos produtos e tempo de uma soma por estado."""
import os, time
import google.auth
import ee
cred, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/earthengine", "https://www.googleapis.com/auth/cloud-platform"])
ee.Initialize(credentials=cred, project=os.environ["GEE_PROJECT"])
B = "projects/mapbiomas-public/assets/brazil/"

def tenta(rotulo, f):
    t = time.time()
    try: print(rotulo, "→", str(f())[:900], f"({time.time() - t:.0f}s)", flush=True)
    except Exception as e: print(rotulo, "ERRO", str(e)[:300], f"({time.time() - t:.0f}s)", flush=True)

for pai in ("projects/mapbiomas-territories/assets", "projects/mapbiomas-territories/assets/TERRITORIES", "projects/mapbiomas-territories/assets/TERRITORIES/LULC",
            "projects/mapbiomas-territories/assets/TERRITORIES/LULC/BRAZIL", "projects/mapbiomas-territories/assets/TERRITORIES/LULC/BRAZIL/COLLECTION10",
            "projects/mapbiomas-territories/assets/TERRITORIES/LULC/BRAZIL/COLLECTION10/WORKSPACE", "projects/mapbiomas-workspace/AUXILIAR"):
    tenta("LISTA " + pai, lambda: [(a["type"][:5], a["name"].split("/assets/")[-1]) for a in ee.data.listAssets({"parent": pai, "pageSize": 60}).get("assets", [])])
for cand in ("projects/mapbiomas-workspace/AUXILIAR/estados-2017", "projects/mapbiomas-workspace/AUXILIAR/estados-2016",
             "projects/mapbiomas-territories/assets/TERRITORIES/LULC/BRAZIL/COLLECTION10/WORKSPACE/POLITICAL_LEVEL_2",
             "projects/mapbiomas-territories/assets/TERRITORIES/LULC/BRAZIL/COLLECTION9/WORKSPACE/POLITICAL_LEVEL_2"):
    tenta("TABELA " + cand, lambda: (ee.FeatureCollection(cand).size().getInfo(), ee.FeatureCollection(cand).first().toDictionary().getInfo()))
gaul = ee.FeatureCollection("FAO/GAUL/2015/level1").filter(ee.Filter.eq("ADM0_NAME", "Brazil"))
tenta("GAUL", lambda: (gaul.size().getInfo(), gaul.aggregate_array("ADM1_NAME").getInfo()))
m = ee.Image(B + "fire/monitor/mapbiomas_fire_monthly_burned_v1/brazil-2026-9")
tenta("MONITOR escala", lambda: (m.projection().nominalScale().getInfo(), m.projection().crs().getInfo()))
c = ee.Image(B + "fire/collection5_1/mapbiomas_fire_collection51_monthly_burned_v1")
tenta("COLEÇÃO escala e bandas", lambda: (c.projection().nominalScale().getInfo(), c.bandNames().size().getInfo(), c.bandNames().getInfo()[:2]))
w = ee.Image(B + "water/collection5/mapbiomas_brazil_collection5_water_annual_v4")
tenta("ÁGUA escala e bandas", lambda: (w.projection().nominalScale().getInfo(), w.bandNames().size().getInfo(), w.bandNames().getInfo()[:2], w.bandNames().getInfo()[-2:]))
ha = ee.Image.pixelArea().divide(1e4)
for nome in ("Mato Grosso", "Amazonas"):
    g = gaul.filter(ee.Filter.eq("ADM1_NAME", nome)).geometry()
    tenta(f"SOMA monitor 2026-9 {nome} escala nativa", lambda: ha.updateMask(m.gt(0)).reduceRegion(ee.Reducer.sum(), g, scale=m.projection().nominalScale(), maxPixels=1e13, tileScale=8).getInfo())
    tenta(f"SOMA coleção 2024 por mês {nome} 30 m", lambda: ha.addBands(c.select("burned_monthly_2024")).updateMask(c.select("burned_monthly_2024").gt(0)).reduceRegion(ee.Reducer.sum().group(1, "mes"), g, scale=30, maxPixels=1e13, tileScale=8).getInfo())
    tenta(f"SOMA água 2025 {nome} 30 m", lambda: ha.updateMask(w.select(w.bandNames().get(-1)).gt(0)).reduceRegion(ee.Reducer.sum(), g, scale=30, maxPixels=1e13, tileScale=8).getInfo())
