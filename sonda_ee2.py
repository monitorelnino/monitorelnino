"""Sonda 2 (não grava em data/): até que mês vai o Monitor do Fogo e a água mensal no Earth Engine, e uma estatística por estado."""
import os
import google.auth
import ee
cred, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/earthengine", "https://www.googleapis.com/auth/cloud-platform"])
ee.Initialize(credentials=cred, project=os.environ["GEE_PROJECT"])
B = "projects/mapbiomas-public/assets/brazil/"

def todos(pai):
    fora, tok = [], None
    while True:
        r = ee.data.listAssets({"parent": pai, "pageSize": 1000, **({"pageToken": tok} if tok else {})})
        fora += r.get("assets", []); tok = r.get("nextPageToken")
        if not tok: return fora

for a in todos(B + "fire/monitor"):
    print("MONITOR", a["type"], a["name"].replace(B, ""))
    if a["type"] in ("FOLDER", "IMAGE_COLLECTION"):
        f = todos(a["name"]); print("   n =", len(f), "| primeiro:", f[0]["name"].split("/")[-1] if f else None, "| último:", f[-1]["name"].split("/")[-1] if f else None)
        if f and a["type"] == "IMAGE_COLLECTION":
            i = ee.Image(f[-1]["name"]); print("   bandas:", i.bandNames().getInfo()[:20], "| props:", {k: v for k, v in i.toDictionary().getInfo().items()})
        if f and f[-1]["type"] == "TABLE":
            t = ee.FeatureCollection(f[-1]["name"]); print("   tabela:", t.size().getInfo(), "feições | colunas:", t.first().propertyNames().getInfo())
for nome in ("water/collection5/mapbiomas_brazil_collection5_water_monthly_v4",):
    c = ee.ImageCollection(B + nome); print("ÁGUA", c.size().getInfo(), "imagens |", c.first().bandNames().getInfo()[:8], c.first().toDictionary().getInfo())
    print("   datas:", c.aggregate_min("system:time_start").getInfo(), c.aggregate_max("system:time_start").getInfo(), "| ids:", c.limit(3).aggregate_array("system:index").getInfo(), c.sort("system:index", False).limit(3).aggregate_array("system:index").getInfo())
for nome in ("fire/collection5_1", "fire/collection5"):
    for a in todos(B + nome):
        linha = a["name"].replace(B, "")
        if a["type"] == "IMAGE": linha += " | bandas: " + ", ".join(ee.Image(a["name"]).bandNames().getInfo()[-3:])
        print("COL", a["type"], linha)
