"""Sonda pontual (diag 16/10): conteúdo do shapefile mensal do Monitor de Secas (setembro/2026)."""
import io, sys, zipfile, urllib.request, subprocess, json
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "pyshp"], check=True)
import shapefile
sys.path.insert(0, ".")
from coletores_base import UA
u = "https://ana-monitor-secas-files.s3.sa-east-1.amazonaws.com/uploads/mapas/setembro2026.zip"
with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=120) as f:
    z = zipfile.ZipFile(io.BytesIO(f.read()))
for i in z.infolist():
    print(i.filename, i.file_size)
for nome in [i.filename for i in z.infolist() if i.filename.lower().endswith(".shp")]:
    base = nome[:-4]
    def abre(ext):
        for n in z.namelist():
            if n.lower() == (base + ext).lower():
                return io.BytesIO(z.read(n))
    r = shapefile.Reader(shp=abre(".shp"), dbf=abre(".dbf"), shx=abre(".shx"))
    prj = abre(".prj")
    print("\n##", nome, "tipo", r.shapeTypeName, "registros", len(r), "bbox", [round(x, 2) for x in r.bbox])
    print(" campos:", r.fields[1:])
    print(" prj:", prj.read()[:200] if prj else None)
    for rec in r.records()[:8]:
        print("  ", rec.as_dict())
    print(" pontos totais:", sum(len(s.points) for s in r.shapes()))
