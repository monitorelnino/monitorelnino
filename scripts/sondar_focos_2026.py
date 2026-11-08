#!/usr/bin/env python3
"""Sonda pontual (08/11/2026): focos do satélite de referência por mês em 2026, do arquivo anual do INPE.
Só imprime; não grava em data/."""
import csv, io, sys, zipfile, pathlib, urllib.request, collections
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from coletores_base import ua_de
u = "https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/anual/Brasil_sat_ref/focos_br_ref_2026.zip"
b = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": ua_de("sonda de focos 2026")}), timeout=120).read()
print("bytes", len(b))
z = zipfile.ZipFile(io.BytesIO(b)); print(z.namelist())
por_mes = collections.Counter(); sat = collections.Counter(); n = 0
for nome in z.namelist():
    if not nome.endswith(".csv"): continue
    txt = z.read(nome).decode("utf-8", "replace")
    r = csv.DictReader(io.StringIO(txt)); cab = r.fieldnames; print("colunas", cab)
    for row in r:
        n += 1; d = row.get("data_pas") or row.get("data_hora_gmt") or row.get("data") or ""
        por_mes[d[:7]] += 1; sat[row.get("satelite", "?")] += 1
print("linhas", n, "satelites", sat.most_common(3)); [print(m, c) for m, c in sorted(por_mes.items())]
print("jun-set:", sum(c for m, c in por_mes.items() if m in ("2026-06", "2026-07", "2026-08", "2026-09")))
