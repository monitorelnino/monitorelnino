#!/usr/bin/env python3
"""Sonda (07/09/2026): onde está, em dado aberto, a tabela de probabilidades ENSO por trimestre (La Niña/Neutro/El Niño).
Candidatos: IRI (arquivos de dados do plume; QuickLook), CPC/NOAA (discussão mensal; tabela). Imprime status, tipo e amostra."""
import urllib.request, urllib.error
UA={"User-Agent":"MonitorElNino/3.1 (sonda ENSO)"}
CANDIDATOS=["https://iri.columbia.edu/~forecast/ensofcst/Data/ensofcst_ONI","https://iri.columbia.edu/~forecast/ensofcst/Data/ensofcst_ALLto","https://iri.columbia.edu/~forecast/ensofcst/Data/ensofcst_ONI_v3",
            "https://iri.columbia.edu/climate/ENSO/currentinfo/QuickLook.html","https://iri.columbia.edu/climate/ENSO/currentinfo/SST_table.html","https://iri.columbia.edu/our-expertise/climate/forecasts/enso/current/",
            "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/ensodisc.shtml","https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/enso-probabilities.txt",
            "https://www.cpc.ncep.noaa.gov/products/CFSv2/CFSv2_body.html","https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/figure1.png"]
for u in CANDIDATOS:
    try:
        with urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=40) as r:
            corpo=r.read(400000); ct=r.headers.get("Content-Type","")
            txt=corpo.decode("utf-8","replace") if "image" not in ct else ""
            import re
            achou=re.findall(r"(?:El Ni[nñ]o|La Ni[nñ]a|Neutral)[^\n]{0,40}?(\d{1,3})\s*%",txt)[:6]
            print(f"OK  {u} | {r.status} {ct[:30]} | {len(corpo)} bytes | percentuais vistos: {achou} | amostra: {txt[:160].replace(chr(10),' ')!r}")
    except urllib.error.HTTPError as e: print(f"ERR {u} | HTTP {e.code}")
    except Exception as e: print(f"ERR {u} | {type(e).__name__}: {e}")
