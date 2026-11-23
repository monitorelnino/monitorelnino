"""Dados do Marajó para relatório (23/11/2026; não vai à main): focos do INPE por município e mês, PM2,5 estimado
(CAMS, via Open-Meteo) por dia, internações (SIH) e óbitos (SIM) por município de residência. Só agregados."""
import collections, io, json, pathlib, sys, time
sys.path.insert(0, "scripts")
import coletar_sinais_risco as sr
import coletar_sih as sih
import coletar_sim as sim
from coletar_datasus_dbc import baixar_ftp, ler_dbc, listar_ftp
from coletores_base import buscar, ler
NOMES = ("Afuá,Anajás,Bagre,Breves,Cachoeira do Arari,Chaves,Curralinho,Gurupá,Melgaço,Muaná,Oeiras do Pará,Ponta de Pedras,"
         "Portel,Salvaterra,Santa Cruz do Arari,São Sebastião da Boa Vista,Soure").split(",")
ref = {r["nome"]: r for r in ler("municipios_ibge_referencia.json", []) if r["uf"] == "PA"}
MUN = {str(ref[n]["codigo_ibge"]): n for n in NOMES}
SEIS = {k[:6]: k for k in MUN}
out = {"municipios": MUN, "falhas": {}}
def tenta(nome, fn):
    try:
        out[nome] = fn()
        print(nome, "ok", flush=True)
    except Exception as e:  # noqa: BLE001
        out["falhas"][nome] = f"{type(e).__name__}: {str(e)[:200]}"
        print(nome, "FALHA", out["falhas"][nome], flush=True)

def focos():
    r = {"marajo": {}, "pa": {}, "falhas": {}}
    for ano in (2023, 2024, 2025, 2026):
        for m in range(1, 13):
            mes = f"{ano}{m:02d}"
            if mes > "202611":
                continue
            try:
                texto = buscar(sr.FOCOS_MENSAL.format(mes=mes), timeout=180, origem="coletar_sinais_risco").decode("utf-8", "replace")
                dias = sr.resumo_focos_ref(texto)
                mun = collections.Counter(); pa = 0
                for d in dias.values():
                    pa += d["uf"].get("PA", 0)
                    for k, v in d["municipio"].items():
                        if k in MUN:
                            mun[k] += v
                r["marajo"][mes] = dict(mun); r["pa"][mes] = pa
                print("focos", mes, sum(mun.values()), pa, flush=True)
            except Exception as e:  # noqa: BLE001
                r["falhas"][mes] = f"{type(e).__name__}: {str(e)[:120]}"
    return r

def ar():
    r = {}
    for k, n in MUN.items():
        u = ("https://air-quality-api.open-meteo.com/v1/air-quality?latitude=%s&longitude=%s&hourly=pm2_5"
             "&start_date=2026-08-01&end_date=2026-11-23&timezone=America%%2FBelem" % (ref[n]["lat"], ref[n]["lon"]))
        try:
            d = json.loads(buscar(u, timeout=60, origem="coletar_sinais_risco"))
            dia = collections.defaultdict(list)
            for t, v in zip(d["hourly"]["time"], d["hourly"]["pm2_5"]):
                if v is not None:
                    dia[t[:10]].append(v)
            r[k] = {x: [round(sum(v) / len(v), 1), round(max(v), 1), len(v)] for x, v in sorted(dia.items())}
        except Exception as e:  # noqa: BLE001
            r[k] = {"erro": f"{type(e).__name__}: {str(e)[:120]}"}
        time.sleep(1)
    return r

def sih_():
    r = {"meses": {}, "falhas": {}}
    nomes = {n for n, _ in listar_ftp(sih.FTP_DIR_RD)}
    for ano in (23, 24, 25, 26):
        for m in range(1, 13):
            arq = f"RDPA{ano:02d}{m:02d}.dbc"
            if arq not in nomes:
                continue
            try:
                _d, linhas = ler_dbc(baixar_ftp(f"{sih.FTP_DIR_RD}/{arq}"), ("ANO_CMPT", "MES_CMPT", "IDENT", "DIAG_PRINC", "MUNIC_RES"))
                c = {}
                for x in linhas:
                    cod = str(x.get("MUNIC_RES") or "").strip()[:6]
                    if cod not in SEIS or str(x.get("IDENT") or "").strip() == "5":
                        continue
                    cid = str(x.get("DIAG_PRINC") or "").strip().upper()
                    g = c.setdefault(SEIS[cod], collections.Counter())
                    g["total"] += 1
                    if cid[:1] == "J":
                        g["cap_J"] += 1
                    if "respiratorias" in sih.grupo_do_cid(cid):
                        g["J00_J22"] += 1
                    if cid[:3] in ("J40", "J41", "J42", "J43", "J44", "J45", "J46", "J47"):
                        g["J40_J47"] += 1
                    if cid[:3] in ("T58", "T59", "J68", "J70") or cid[:3] in ("X00", "X01", "X08", "X09"):
                        g["fumaca"] += 1
                r["meses"][f"20{ano:02d}-{m:02d}"] = {k: dict(v) for k, v in c.items()}
                print("sih", arq, sum(v["total"] for v in c.values()), flush=True)
            except Exception as e:  # noqa: BLE001
                r["falhas"][arq] = f"{type(e).__name__}: {str(e)[:120]}"
            time.sleep(1)
    return r

def sim_():
    r = {"anos": {}, "falhas": {}}
    for d in (sim.DIR_FINAL, sim.DIR_PRELIM):
        try:
            nomes = {n for n, _ in listar_ftp(d)}
        except Exception as e:  # noqa: BLE001
            r["falhas"][d] = str(e)[:120]; continue
        for ano in (2023, 2024, 2025, 2026):
            arq = f"DOPA{ano}.dbc"
            if arq not in nomes or str(ano) in r["anos"]:
                continue
            try:
                _d, linhas = ler_dbc(baixar_ftp(f"{d}/{arq}"), ("DTOBITO", "CAUSABAS", "CODMUNRES"))
                c = {}
                for x in linhas:
                    cod, dt = str(x.get("CODMUNRES") or "").strip()[:6], str(x.get("DTOBITO") or "").strip()
                    if cod not in SEIS or len(dt) != 8 or dt[4:] != str(ano):
                        continue
                    cid = str(x.get("CAUSABAS") or "").strip().upper()
                    g = c.setdefault(SEIS[cod], {}).setdefault(dt[2:4], collections.Counter())
                    g["total"] += 1
                    if cid[:1] == "J":
                        g["cap_J"] += 1
                r["anos"][str(ano)] = {"dir": d, "mun": {k: {m: dict(v) for m, v in mm.items()} for k, mm in c.items()}}
                print("sim", arq, d, flush=True)
            except Exception as e:  # noqa: BLE001
                r["falhas"][arq] = f"{type(e).__name__}: {str(e)[:120]}"
    return r

tenta("focos", focos); tenta("ar", ar); tenta("sih", sih_); tenta("sim", sim_)
pathlib.Path("data/relatorio_marajo").mkdir(exist_ok=True)
json.dump(out, open("data/relatorio_marajo/dados.json", "w"), ensure_ascii=False)
print("FALHAS", out["falhas"])
