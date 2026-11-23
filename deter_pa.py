"""Alertas do DETER (INPE) no Pará por município, ano e classe, 2024–2026 (relatório do Marajó; não vai à main)."""
import collections, csv, io, json, pathlib, urllib.parse
from coletores_base import buscar
BASE = "https://terrabrasilis.dpi.inpe.br/geoserver/{ws}/{lay}/ows?service=WFS&version=2.0.0&request=GetFeature&typeName={ws}:{lay}"
out = {"tentativas": {}}
for ws, lay in (("deter-amz", "deter_amz"), ("deter-amz", "deter_public")):
    try:
        um = json.loads(buscar(BASE.format(ws=ws, lay=lay) + "&count=1&outputFormat=application/json", timeout=120, origem="coletar_sinais_risco"))
        campos = list(um["features"][0]["properties"])
        out["tentativas"][lay] = campos
        pega = lambda *n: next((c for c in n if c in campos), None)
        data, mun, geo, area = pega("view_date", "date"), pega("municipality", "municipali", "mun", "county"), pega("geocodibge", "geocode", "geocodigo"), pega("areamunkm", "areatotalkm")
        props = [c for c in ("classname", data, mun, geo, area, "uf") if c]
        filtro = urllib.parse.quote(f"uf='PA' AND {data}>='2024-01-01'")
        texto = buscar(BASE.format(ws=ws, lay=lay) + f"&outputFormat=csv&propertyName={','.join(props)}&CQL_FILTER={filtro}",
                       timeout=600, origem="coletar_sinais_risco").decode("utf-8", "replace")
        tab = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0.0])))
        n = 0
        for l in csv.DictReader(io.StringIO(texto)):
            n += 1
            chave = (l.get(geo) or "") + "|" + (l.get(mun) or "") if geo else (l.get(mun) or "")
            c = tab[chave][(l.get(data) or "")[:4]][l.get("classname") or ""]
            c[0] += 1; c[1] += float(l.get(area) or 0)
        out.update({"camada": lay, "campos_usados": props, "linhas": n,
                    "municipios": {k: {a: {c: [x[0], round(x[1], 3)] for c, x in cl.items()} for a, cl in v.items()} for k, v in tab.items()}})
        print(lay, "ok", n, len(tab), flush=True)
        break
    except Exception as e:  # noqa: BLE001
        out["tentativas"][lay + "_erro"] = f"{type(e).__name__}: {str(e)[:200]}"; print(lay, "FALHA", e, flush=True)
pathlib.Path("data/relatorio_marajo").mkdir(parents=True, exist_ok=True)
json.dump(out, open("data/relatorio_marajo/deter_pa.json", "w"), ensure_ascii=False)
