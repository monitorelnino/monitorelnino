#!/usr/bin/env python3
"""Sonda 2 (não grava em data/): o 403 do HEAD é recusa de verdade? GET com Range, listagem pública do bucket e a página da plataforma."""
import urllib.request
from coletores_base import ua_de

UA = {"User-Agent": ua_de("sondar_mapbiomas_fogo")}
B = "https://storage.googleapis.com/mapbiomas-public/initiatives/brazil/fire/"
TESTES = [
    ("GET range, exemplo da página", B + "monitor/mapbiomas_fire_monthly_burned_v1/monthly_burned-brazil_2026_07.tif", {"Range": "bytes=0-1023"}),
    ("GET range, coleção 5.1 de 2025", B + "collection_05_1/monthly_burned/monthly_burned-brazil_burned_monthly_2025.tif", {"Range": "bytes=0-1023"}),
    ("listagem JSON do bucket (fogo)", "https://storage.googleapis.com/storage/v1/b/mapbiomas-public/o?prefix=initiatives/brazil/fire/monitor/&maxResults=50", {}),
    ("listagem XML do bucket (fogo)", "https://storage.googleapis.com/mapbiomas-public?prefix=initiatives/brazil/fire/&max-keys=50", {}),
    ("objeto conhecido de cobertura (controle)", "https://storage.googleapis.com/mapbiomas-public/initiatives/brazil/collection_10/lulc/coverage/brazil_coverage_2024.tif", {"Range": "bytes=0-1023"}),
    ("plataforma (HTML)", "https://plataforma.brasil.mapbiomas.org/", {}),
]
for nome, url, extra in TESTES:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={**UA, **extra}), timeout=60) as r:
            corpo = r.read(4000)
            print(f"{r.status} {nome}: {r.headers.get('Content-Type')} {r.headers.get('Content-Range')} :: {corpo[:600]!r}", flush=True)
    except urllib.error.HTTPError as e:
        print(f"{e.code} {nome}: {e.read(600)!r}", flush=True)
    except Exception as e:  # noqa: BLE001
        print(f"ERRO {nome}: {type(e).__name__}: {e}", flush=True)
