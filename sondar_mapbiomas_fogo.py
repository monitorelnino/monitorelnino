#!/usr/bin/env python3
"""Sonda (não grava em data/): quais arquivos de fogo do MapBiomas existem, tamanho, e se são COG com visões reduzidas."""
import struct, urllib.request
from coletores_base import ua_de

B = "https://storage.googleapis.com/mapbiomas-public/initiatives/brazil/fire/"
ALVOS = [B + f"collection_05_1/monthly_burned/monthly_burned-brazil_burned_monthly_{a}.tif" for a in range(2014, 2026)] + \
        [B + f"monitor/mapbiomas_fire_monthly_burned_v1/monthly_burned-brazil_{a}_{m:02d}.tif" for a in (2019, 2023, 2025, 2026) for m in range(1, 13)]


def cabeca(url):
    r = urllib.request.Request(url, method="HEAD", headers={"User-Agent": ua_de("sondar_mapbiomas_fogo")})
    try:
        with urllib.request.urlopen(r, timeout=60) as x:
            return x.status, int(x.headers.get("Content-Length") or 0), x.headers.get("Last-Modified")
    except urllib.error.HTTPError as e:
        return e.code, 0, None


def tiff(url):
    r = urllib.request.Request(url, headers={"User-Agent": ua_de("sondar_mapbiomas_fogo"), "Range": "bytes=0-65535"})
    with urllib.request.urlopen(r, timeout=60) as x:
        b = x.read()
    o = "<" if b[:2] == b"II" else ">"
    big = struct.unpack(o + "H", b[2:4])[0] == 43
    ifd = struct.unpack(o + "Q", b[8:16])[0] if big else struct.unpack(o + "I", b[4:8])[0]
    n_ifd, tags = 0, {}
    while ifd and ifd < len(b) and n_ifd < 20:
        n = struct.unpack(o + ("Q" if big else "H"), b[ifd:ifd + (8 if big else 2)])[0]
        p = ifd + (8 if big else 2)
        for i in range(n):
            e = b[p + i * (20 if big else 12): p + (i + 1) * (20 if big else 12)]
            tag, typ = struct.unpack(o + "HH", e[:4])
            val = struct.unpack(o + ("Q" if big else "I"), e[(12 if big else 8):(20 if big else 12)])[0] if typ in (4, 16) else struct.unpack(o + "H", e[(12 if big else 8):(14 if big else 10)])[0]
            if n_ifd == 0 or tag in (256, 257):
                tags.setdefault(n_ifd, {})[tag] = val
        q = p + n * (20 if big else 12)
        ifd = struct.unpack(o + ("Q" if big else "I"), b[q:q + (8 if big else 4)])[0] if q + 8 <= len(b) else 0
        n_ifd += 1
    t0 = tags.get(0, {})
    return {"bigtiff": big, "visoes": n_ifd, "largura": t0.get(256), "altura": t0.get(257), "bits": t0.get(258),
            "compressao": t0.get(259), "tile": t0.get(322), "amostras": t0.get(277),
            "tamanhos": [(tags[k].get(256), tags[k].get(257)) for k in sorted(tags)][:8]}


for u in ALVOS:
    st, tam, mod = cabeca(u)
    linha = f"{st} {tam / 1e6:8.1f} MB {mod or '':30} {u.split('/fire/')[1]}"
    if st == 200 and (u.endswith("2025.tif") or u.endswith("2026_01.tif") or u.endswith("2025_09.tif")):
        try:
            linha += f"  {tiff(u)}"
        except Exception as e:  # noqa: BLE001
            linha += f"  tiff? {type(e).__name__}: {e}"
    print(linha, flush=True)
