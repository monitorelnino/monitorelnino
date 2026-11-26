"""Conferência de texto de imprensa (central, 26/11/2026): focos de calor do INPE no Marajó e nas áreas prioritárias do
PEPIF. Só lê e imprime no log; não grava nada. Some com o ramo."""
import csv, io, json, sys, urllib.request, collections, datetime as dt
UA = "MonitorElNinoBrasil/2.2.4 (+https://monitorelnino.com.br; conferencia da central)"
BASE = "https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/"
MARAJO = {"1500305":"Afuá","1500701":"Anajás","1501105":"Bagre","1501808":"Breves","1502004":"Cachoeira do Arari","1502509":"Chaves",
 "1502806":"Curralinho","1503101":"Gurupá","1504505":"Melgaço","1504901":"Muaná","1505700":"Ponta de Pedras","1505809":"Portel",
 "1506302":"Salvaterra","1506401":"Santa Cruz do Arari","1507706":"São Sebastião da Boa Vista","1507904":"Soure","1505205":"Oeiras do Pará"}
PRIOR = {"1503093":"Goianésia do Pará","1506187":"Rondon do Pará","1504703":"Moju","1505502":"Paragominas","1506195":"Rurópolis",
 "1508050":"Trairão","1503606":"Itaituba","1505031":"Novo Progresso","1507300":"São Félix do Xingu","1502707":"Conceição do Araguaia","1506138":"Redenção"}
def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for t in range(4):
        try:
            with urllib.request.urlopen(req, timeout=300) as r: return r.read()
        except Exception as e:
            print("  falha", url, e, file=sys.stderr)
    return None
def linhas(url):
    b = get(url)
    if not b: print("SEM ARQUIVO", url); return []
    if url.endswith(".zip"):
        import zipfile; z = zipfile.ZipFile(io.BytesIO(b)); b = z.read(z.namelist()[0])
    return list(csv.DictReader(io.StringIO(b.decode("utf-8", "replace"))))
def chave(l):
    for k in ("municipio_id","id_municipio","cod_municipio"):
        if l.get(k): return str(l[k]).split(".")[0].zfill(7)
    return None
def data(l): return (l.get("data_hora_gmt") or l.get("data_pas") or l.get("datahora") or "")[:10]
def sat(l): return l.get("satelite") or l.get("satelite_referencia") or ""
out = {}
# A: 01/10–22/11/2026, todos os satélites e só o de referência
cont = {"todos": collections.Counter(), "ref": collections.Counter()}
pa26 = {"todos": collections.Counter(), "ref": collections.Counter()}
def soma(ls, alvo, filtro=lambda d: True):
    for l in ls:
        c = chave(l)
        if not c or not c.startswith("15") or not filtro(data(l)): continue
        alvo["todos"][c] += 1
        if sat(l) == "AQUA_M-T": alvo["ref"][c] += 1
ini, fim = dt.date(2026,10,1), dt.date(2026,11,22)
ls10 = linhas(BASE + "mensal/Brasil/focos_mensal_br_202610.csv"); print("out/2026 linhas", len(ls10))
soma(ls10, cont)
d = dt.date(2026,11,1)
nov = []
while d <= dt.date(2026,11,25):
    ls = linhas(BASE + f"diario/Brasil/focos_diario_br_{d:%Y%m%d}.csv"); nov.append((d, ls)); d += dt.timedelta(days=1)
for dd, ls in nov:
    if dd <= fim: soma(ls, cont)
for tipo in ("todos","ref"):
    m = sum(cont[tipo][c] for c in MARAJO); p = sum(cont[tipo][c] for c in PRIOR)
    out[f"A_{tipo}"] = {"marajo_17": m, "marajo_16_sem_oeiras": m - cont[tipo]["1505205"], "prioritarios_11": p,
                        "por_mun_marajo": {MARAJO[c]: cont[tipo][c] for c in MARAJO}, "por_mun_prior": {PRIOR[c]: cont[tipo][c] for c in PRIOR}}
# B: 2024 e 2025 por mês, e C: 2026 até 25/11 por município do PA
mes = {"todos": collections.defaultdict(collections.Counter), "ref": collections.defaultdict(collections.Counter)}
for ano in (2024, 2025, 2026):
    for m in range(1, 13):
        if ano == 2026 and m >= 11: break
        ls = linhas(BASE + f"mensal/Brasil/focos_mensal_br_{ano}{m:02d}.csv")
        print(ano, m, len(ls))
        for l in ls:
            c = chave(l)
            if not c or not c.startswith("15"): continue
            mes["todos"][(ano, m)][c] += 1
            if sat(l) == "AQUA_M-T": mes["ref"][(ano, m)][c] += 1
for dd, ls in nov:
    for l in ls:
        c = chave(l)
        if not c or not c.startswith("15"): continue
        mes["todos"][(2026, 11)][c] += 1
        if sat(l) == "AQUA_M-T": mes["ref"][(2026, 11)][c] += 1
for tipo in ("todos","ref"):
    serie = {f"{a}-{m:02d}": {"marajo": sum(v[c] for c in MARAJO), "prior": sum(v[c] for c in PRIOR)} for (a, m), v in sorted(mes[tipo].items())}
    out[f"B_{tipo}"] = serie
    tot26 = collections.Counter()
    for (a, m), v in mes[tipo].items():
        if a == 2026: tot26.update(v)
    out[f"C_{tipo}_2026_top10"] = tot26.most_common(10)
    tot2425 = collections.Counter()
    for (a, m), v in mes[tipo].items():
        if a in (2024, 2025): tot2425.update(v)
    rank = [c for c, _ in tot2425.most_common()]
    out[f"D_{tipo}_rank_focos_2024_2025"] = {"Portel": rank.index("1505809") + 1 if "1505809" in rank else None,
        "Redenção": rank.index("1506138") + 1 if "1506138" in rank else None, "n_municipios": len(rank),
        "marajo": {MARAJO[c]: (rank.index(c) + 1 if c in rank else None) for c in MARAJO},
        "prior": {PRIOR[c]: (rank.index(c) + 1 if c in rank else None) for c in PRIOR}}
print("RESULTADO_MARAJO " + json.dumps(out, ensure_ascii=False, default=str))
