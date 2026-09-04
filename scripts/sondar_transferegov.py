#!/usr/bin/env python3
"""
sondar_transferegov.py — sonda de UMA VEZ, 2ª rodada (04/09/2026): (a) lista os recursos
(paths) do Swagger das três APIs PostgREST; (b) baixa os CSVs de convênio, proposta e programa
do módulo Discricionárias e Legais e imprime cabeçalho, 2 linhas de amostra, nº de linhas e as
colunas que parecem IBGE/UF/data/valor/objeto — para desenhar o coletor com evidência.
"""
import csv, io, json, re, urllib.request, zipfile

UA = {"User-Agent": "Mozilla/5.0 (MonitorElNino/sonda)"}
REPO = "https://repositorio.dados.gov.br/seges/detru/"

def baixar(url, limite=None):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=600) as r:
        return r.read(limite) if limite else r.read()

print("=== SWAGGER: recursos de cada API ===")
for api in ("fundoafundo", "transferenciasespeciais", "ted"):
    try:
        sw = json.loads(baixar(f"https://api.transferegov.gestao.gov.br/{api}/").decode("utf-8", "replace"))
        paths = sorted(sw.get("paths", {}).keys())
        print(f"\n-- {api}: {len(paths)} recursos\n   " + "\n   ".join(paths))
    except Exception as e:  # noqa: BLE001
        print(f"\n-- {api}: !! {type(e).__name__}: {e}")

print("\n=== data da carga ===")
try: print("  ", baixar(REPO + "data_carga_siconv.txt").decode("utf-8", "replace")[:200].strip())
except Exception as e: print("   !!", e)

print("\n=== CSVs: cabeçalho, amostra e colunas-chave ===")
for nome in ("siconv_convenio.csv.zip", "siconv_proposta.csv.zip", "siconv_programa.csv.zip", "siconv_proponentes.csv.zip"):
    print(f"\n-- {nome}")
    try:
        z = zipfile.ZipFile(io.BytesIO(baixar(REPO + nome)))
        interno = z.namelist()[0]
        with z.open(interno) as f:
            txt = io.TextIOWrapper(f, encoding="latin-1", errors="replace")
            primeira = txt.readline()
            sep = ";" if primeira.count(";") > primeira.count(",") else ","
            cab = [c.strip() for c in primeira.strip().split(sep)]
            linhas = [txt.readline() for _ in range(2)]
            n = 2
            for _ in txt: n += 1
        print(f"   arquivo interno: {interno} | sep='{sep}' | colunas: {len(cab)} | linhas: {n:,}")
        print(f"   cabeçalho: {cab}")
        for l in linhas: print(f"   amostra: {l.strip()[:300]}")
        chaves = [c for c in cab if re.search(r"IBGE|UF|MUNIC|DATA|DIA_|ANO|VALOR|VL_|OBJETO|SITUACAO|PROGRAMA|ORGAO|NR_", c, re.I)]
        print(f"   colunas-chave: {chaves}")
    except Exception as e:  # noqa: BLE001
        print(f"   !! {type(e).__name__}: {e}")
