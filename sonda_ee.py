"""Sonda (não grava em data/): o Earth Engine aceita a identidade do repositório? O que o MapBiomas publica lá?"""
import os, sys
import google.auth
import ee

cred, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/earthengine", "https://www.googleapis.com/auth/cloud-platform"])
ee.Initialize(credentials=cred, project=os.environ["GEE_PROJECT"])
print("EE OK", ee.Number(1).add(1).getInfo())

def listar(pai, nivel=0, teto=3):
    try:
        filhos = ee.data.listAssets({"parent": pai}).get("assets", [])
    except Exception as e:  # noqa: BLE001
        print("  " * nivel + "ERRO", pai, str(e)[:160]); return
    for a in filhos[:80]:
        print("  " * nivel + a["type"], a["name"])
        if a["type"] == "FOLDER" and nivel < teto:
            listar(a["name"], nivel + 1, teto)

for raiz in sys.argv[1:] or ["projects/mapbiomas-public/assets/brazil"]:
    print("RAIZ", raiz); listar(raiz)
