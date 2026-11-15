#!/usr/bin/env python3
"""Área queimada e superfície de água por estado, somadas dos mapas do MapBiomas no Earth Engine.

O que grava (e só isto): `data/mapbiomas/fogo_monitor.json` (Monitor do Fogo, hectares por estado e mês,
de 2019 ao último mês publicado), `data/mapbiomas/fogo_colecao.json` (coleção anual de fogo, hectares por
estado e mês do ano da queimada) e `data/mapbiomas/agua_anual.json` (hectares de superfície de água por
estado e ano). Nenhum valor é estimado: cada número é a soma da área dos pixels que o mapa do MapBiomas
marca, dentro do estado que a camada de territórios do próprio MapBiomas (IBGE 2025) indica.

Travas: (1) não escreve fora de `data/mapbiomas/`; (2) antes de gravar confere os 27 estados e todos os
períodos pedidos; faltou um, nada é gravado e o arquivo anterior fica; (3) é dado de contexto, nunca entra
no índice. Acesso: identidade do repositório no Google (sem chave), projeto em `GEE_PROJECT`.

    python3 coletar_mapbiomas.py [--monitor] [--colecao] [--agua] [--desde-zero]
    python3 coletar_mapbiomas.py --autoteste
"""
import concurrent.futures as cf
import datetime as dt
import json
import os
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent
SAIDA = RAIZ / "data" / "mapbiomas"
B = "projects/mapbiomas-public/assets/brazil/"
MONITOR = B + "fire/monitor/mapbiomas_fire_monthly_burned_v1"
COLECAO = B + "fire/collection5_1/mapbiomas_fire_collection51_monthly_burned_v1"
AGUA = B + "water/collection5/mapbiomas_brazil_collection5_water_annual_v4"
TERRITORIOS = "projects/mapbiomas-territories/assets/TERRITORIES/LULC/BRAZIL/COLLECTION10/territory-collection"
ESTADOS = "214_ESTADOS_IBGE_2025_F7EAF953_3"
ANOS_DA_COLECAO = range(2015, 2026)          # os dois El Niños (2015–16, 2023–24) e a faixa de dez anos
RELER_MESES = 3                                # o Monitor revisa os meses recentes
CAIXA = (-74, -34, -34, 6)                     # oeste, sul, leste, norte
UFS = "AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO".split()


def celulas(lado: int) -> list:
    o, s, l, n = CAIXA
    return [(x, y, lado) for x in range(o, l, lado) for y in range(s, n, lado)]


def somar_grupos(respostas: list, n: int) -> dict:
    """Junta as respostas das células: {id do território: [soma por banda]}. Função pura."""
    fora = {}
    for r in respostas:
        for g in (r or {}).get("groups", []):
            soma = g["sum"] if isinstance(g["sum"], list) else [g["sum"]]
            acum = fora.setdefault(int(g["uf"]), [0.0] * n)
            for i, v in enumerate(soma):
                acum[i] += v or 0.0
    return fora


def completo(tabela: dict, periodos: list) -> list:
    """O que falta para gravar: estado ausente ou período ausente. Função pura."""
    faltas = [f"estado ausente: {uf}" for uf in UFS if uf not in tabela]
    faltas += [f"{uf}: falta {p}" for uf in UFS if uf in tabela for p in periodos if p not in tabela[uf]]
    return faltas


def meses_a_ler(existentes: list, publicados: list, reler: int = RELER_MESES) -> list:
    """Meses publicados que ainda não temos, mais os `reler` últimos (a fonte revisa). Função pura."""
    return sorted(set(publicados) - set(existentes) | set(sorted(publicados)[-reler:]))


def _ee():
    import ee
    import google.auth
    cred, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/earthengine",
                                          "https://www.googleapis.com/auth/cloud-platform"])
    ee.Initialize(credentials=cred, project=os.environ["GEE_PROJECT"])
    return ee


def _estados(ee):
    """A imagem de estados do MapBiomas e o {id: UF}, medido em pontos de municípios de cada estado."""
    img = ee.Image(ee.ImageCollection(TERRITORIOS).filter(ee.Filter.eq("system:index", ESTADOS)).first()).rename("uf")
    ref = json.loads((RAIZ / "data" / "municipios_ibge_referencia.json").read_text(encoding="utf-8"))
    por_uf = {}
    for m in ref:
        por_uf.setdefault(m["uf"], []).append(m)
    pontos = [ee.Feature(ee.Geometry.Point([m["lon"], m["lat"]]), {"sigla": uf})
              for uf, ms in por_uf.items() for m in ms[:: max(1, len(ms) // 15)][:15]]
    lidos = img.reduceRegions(ee.FeatureCollection(pontos), ee.Reducer.first(), 30).getInfo()["features"]
    votos = {}
    for f in lidos:
        v = f["properties"].get("first")
        if v is not None:
            votos.setdefault(int(v), {}).setdefault(f["properties"]["sigla"], 0)
            votos[int(v)][f["properties"]["sigla"]] += 1
    mapa = {i: max(c, key=c.get) for i, c in votos.items()}
    if sorted(mapa.values()) != sorted(UFS):
        raise SystemExit(f"✗ a camada de estados não casou com as 27 UFs: {sorted(mapa.items())}")
    return img, mapa


def _reduzir(ee, imagem, estados, n: int, lado: int) -> dict:
    """Soma, por estado, cada uma das `n` bandas de `imagem` (hectares), célula a célula."""
    pilha = imagem.addBands(estados)
    redutor = ee.Reducer.sum().repeat(n).group(n, "uf") if n > 1 else ee.Reducer.sum().group(1, "uf")

    def uma(c, tentativa=0):
        x, y, d = c
        try:
            return pilha.reduceRegion(redutor, ee.Geometry.Rectangle([x, y, x + d, y + d], None, False),
                                      scale=30, maxPixels=1e13).getInfo()
        except Exception as e:  # noqa: BLE001
            if "timed out" in str(e).lower() and d > 1:      # célula pesada: parte em quatro
                h = d // 2
                return {"groups": [{"uf": k, "sum": v} for k, v in somar_grupos(
                    [uma((x + i * h, y + j * h, h)) for i in (0, 1) for j in (0, 1)], n).items()]}
            if tentativa < 3:
                return uma(c, tentativa + 1)
            raise

    with cf.ThreadPoolExecutor(12) as ex:
        return somar_grupos(list(ex.map(uma, celulas(lado))), n)


def _ha(ee):
    return ee.Image.pixelArea().divide(1e4)


def coletar_monitor(ee, estados, mapa, anterior: dict) -> dict:
    col = ee.ImageCollection(MONITOR)
    publicados = sorted(f"{a:04d}-{m:02d}" for a, m in zip(col.aggregate_array("year").getInfo(),
                                                            col.aggregate_array("month").getInfo()))
    tabela = {uf: dict((anterior.get("ufs") or {}).get(uf) or {}) for uf in UFS}
    ler = meses_a_ler(list(next(iter(tabela.values()))), publicados)
    for ano in sorted({p[:4] for p in ler}):
        meses = [p for p in ler if p[:4] == ano]
        imgs = [col.filter(ee.Filter.eq("year", int(ano))).filter(ee.Filter.eq("month", int(p[5:]))).first() for p in meses]
        pilha = ee.Image.cat([ee.Image(i).gt(0).unmask(0).multiply(_ha(ee)) for i in imgs])
        somas = _reduzir(ee, pilha, estados, len(meses), 4)
        for i, uf in mapa.items():
            for k, p in enumerate(meses):
                tabela[uf][p] = round((somas.get(i) or [0.0] * len(meses))[k], 1)
        print(f"  monitor {ano}: {len(meses)} mês(es) · Brasil {sum(tabela[uf][meses[-1]] for uf in UFS):,.0f} ha em {meses[-1]}", flush=True)
    return {"produto": "MapBiomas · Monitor do Fogo", "asset": MONITOR, "unidade": "hectares",
            "primeiro_mes": publicados[0], "ultimo_mes": publicados[-1], "meses": publicados, "ufs": tabela}


def coletar_colecao(ee, estados, mapa) -> dict:
    img = ee.Image(COLECAO)
    tabela = {uf: {} for uf in UFS}
    for ano in ANOS_DA_COLECAO:
        mes = img.select(f"burned_monthly_{ano}").unmask(0)
        pilha = ee.Image.cat([mes.eq(m).multiply(_ha(ee)) for m in range(1, 13)])
        somas = _reduzir(ee, pilha, estados, 12, 4)
        for i, uf in mapa.items():
            for m in range(12):
                tabela[uf][f"{ano}-{m + 1:02d}"] = round((somas.get(i) or [0.0] * 12)[m], 1)
        print(f"  coleção {ano}: Brasil {sum(v for uf in UFS for p, v in tabela[uf].items() if p[:4] == str(ano)):,.0f} ha", flush=True)
    return {"produto": "MapBiomas · Fogo, coleção 5.1", "asset": COLECAO, "unidade": "hectares",
            "meses": [f"{a}-{m:02d}" for a in ANOS_DA_COLECAO for m in range(1, 13)], "ufs": tabela}


def coletar_agua(ee, estados, mapa) -> dict:
    img = ee.Image(AGUA)
    anos = [b.split("_")[-1] for b in img.bandNames().getInfo()]
    somas = _reduzir(ee, img.gt(0).unmask(0).multiply(_ha(ee)), estados, len(anos), 2)
    tabela = {uf: {a: round((somas.get(i) or [0.0] * len(anos))[k], 1) for k, a in enumerate(anos)} for i, uf in mapa.items()}
    print(f"  água: {anos[0]}–{anos[-1]} · Brasil {sum(tabela[uf][anos[-1]] for uf in UFS):,.0f} ha em {anos[-1]}", flush=True)
    return {"produto": "MapBiomas · Água, coleção 5", "asset": AGUA, "unidade": "hectares", "anos": anos, "ufs": tabela}


def gravar(nome: str, doc: dict, periodos: list) -> bool:
    faltas = completo(doc["ufs"], periodos)
    if faltas:
        print(f"✗ {nome}: nada gravado — {len(faltas)} falta(s), ex.: {faltas[:3]}")
        return False
    doc = {"_governanca": "Dado de contexto, somado dos mapas do MapBiomas por estado. Não entra no índice. "
                          "Escritor único: coletar_mapbiomas.py.",
           "fonte": "MapBiomas", "consultado_em": dt.date.today().isoformat(), **doc}
    SAIDA.mkdir(parents=True, exist_ok=True)
    (SAIDA / nome).write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"✓ {nome}: 27 estados × {len(periodos)} período(s)")
    return True


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    tudo = not any(a in sys.argv for a in ("--monitor", "--colecao", "--agua"))
    ee = _ee()
    estados, mapa = _estados(ee)
    ok = True
    if tudo or "--monitor" in sys.argv:
        ant = {} if "--desde-zero" in sys.argv or not (SAIDA / "fogo_monitor.json").exists() else \
            json.loads((SAIDA / "fogo_monitor.json").read_text(encoding="utf-8"))
        doc = coletar_monitor(ee, estados, mapa, ant)
        ok &= gravar("fogo_monitor.json", doc, doc["meses"])
    if tudo or "--colecao" in sys.argv:
        doc = coletar_colecao(ee, estados, mapa)
        ok &= gravar("fogo_colecao.json", doc, doc["meses"])
    if tudo or "--agua" in sys.argv:
        doc = coletar_agua(ee, estados, mapa)
        ok &= gravar("agua_anual.json", doc, doc["anos"])
    return 0 if ok else 1


def autoteste() -> int:
    casos = {
        "células cobrem a caixa do Brasil sem sobra nem buraco": len(celulas(4)) == 100 and len(celulas(2)) == 400,
        "respostas de células diferentes somam por estado e por banda":
            somar_grupos([{"groups": [{"uf": 14, "sum": [1, 2]}]}, {"groups": [{"uf": 14, "sum": [3, None]}, {"uf": 26, "sum": [5, 5]}]}, {"groups": []}], 2)
            == {14: [4.0, 2.0], 26: [5.0, 5.0]},
        "estado ausente ou período ausente impede a gravação":
            completo({uf: {"2026-09": 1.0} for uf in UFS if uf != "RR"}, ["2026-09"]) == ["estado ausente: RR"]
            and completo({uf: {"2026-09": 1.0} for uf in UFS}, ["2026-09", "2026-10"])[0] == "AC: falta 2026-10"
            and completo({uf: {"2026-09": 0.0} for uf in UFS}, ["2026-09"]) == [],
        "lê o mês novo e relê os últimos, que a fonte revisa":
            meses_a_ler(["2026-06", "2026-07", "2026-08"], ["2026-06", "2026-07", "2026-08", "2026-09"], 2) == ["2026-08", "2026-09"],
        "trava estrutural: só escreve em data/mapbiomas/":
            pathlib.Path(__file__).read_text(encoding="utf-8").split("def autoteste")[0].count("write_text") == 1,
    }
    falhas = [k for k, v in casos.items() if not v]
    print(f"✗ AUTOTESTE: {falhas}" if falhas else f"✓ AUTOTESTE OK — {len(casos)} casos, sem rede e sem escrita.")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
