"""Conferência de texto (central, 26/11/2026): PM2,5 estimado do Copernicus CAMS (via Open-Meteo, a mesma fonte do site)
em municípios do Marajó, 05 a 22/11/2026. Só imprime; não grava nada."""
import json, urllib.request, statistics
UA = "MonitorElNinoBrasil/2.2.4 (+https://monitorelnino.com.br; conferencia da central)"
PONTOS = {"Portel": (-1.9358, -50.8208), "Melgaço": (-1.8032, -50.7149), "Breves": (-1.6822, -50.4791), "Bagre": (-1.9006, -50.1636),
          "Curralinho": (-1.8118, -49.7952), "Gurupá": (-1.4052, -51.6401), "Anajás": (-0.9868, -49.9404)}
out = {}
for n, (la, lo) in PONTOS.items():
    u = (f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={la}&longitude={lo}&hourly=pm2_5"
         f"&start_date=2026-11-05&end_date=2026-11-22&timezone=America%2FBelem&domains=cams_global")
    try:
        d = json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=60))
    except Exception as e:
        out[n] = f"erro {e}"; continue
    h = d["hourly"]; por = {}
    for t, v in zip(h["time"], h["pm2_5"]):
        if v is not None: por.setdefault(t[:10], []).append(v)
    out[n] = {"celula": [d.get("latitude"), d.get("longitude")], "media_diaria": {k: round(statistics.mean(v), 1) for k, v in sorted(por.items())},
              "max_horaria": {k: max(v) for k, v in sorted(por.items())}}
print("RESULTADO_CAMS " + json.dumps(out, ensure_ascii=False))
