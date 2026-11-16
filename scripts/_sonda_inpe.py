import urllib.request
B="https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/"
for u in [B+"anual/Brasil_sat_ref/", B+"anual/Brasil_sat_ref/focos_br_ref_2026.zip", B+"mensal/Brasil/", B+"mensal/Brasil/focos_mensal_br_202607.csv", B+"mensal/Brasil/focos_mensal_br_202609.csv"]:
    try:
        r=urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"MonitorElNino/1.0 (+https://monitorelnino.com.br)"}),timeout=60)
        b=r.read(400000 if u.endswith("/") else 2000)
        print("OK",r.status,u,r.headers.get("Content-Length"), b[:300] if u.endswith(".csv") else "")
        if u.endswith("/"):
            import re; print(sorted(set(re.findall(rb'href="([^"]+)"',b)))[-30:])
    except Exception as e: print("ERRO",u,type(e).__name__,e)
