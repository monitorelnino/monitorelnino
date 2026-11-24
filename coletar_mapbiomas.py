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

    python3 coletar_mapbiomas.py [--monitor] [--colecao] [--agua] [--desde-zero]   # soma no Earth Engine
    python3 coletar_mapbiomas.py --do-artefato    # no elo que grava: traz o que o job da soma guardou
    python3 coletar_mapbiomas.py --autoteste

Dois jobs em `.github/workflows/mapbiomas.yml`: a soma precisa da identidade do repositório no Google
(`id-token`), que o invólucro dos coletores não tem; ela guarda os três arquivos como artefato do run, e o
elo do invólucro os traz, confere de novo e faz o commit como todo coletor.
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


def mes_do_id(ident: str) -> str:
    """'brazil-2026-9' → '2026-09'. Função pura."""
    _, ano, mes = str(ident).rsplit("/", 1)[-1].rsplit("-", 2)
    return f"{int(ano):04d}-{int(mes):02d}"


def meses_a_somar(tem: list, antes: dict, agora: dict) -> list:
    """Meses do Monitor que precisam de soma: os que ainda não temos e os que a fonte reescreveu depois da
    nossa soma. Mês que temos sem impressão anterior (soma de antes deste controle) é adotado, não somado
    de novo. Função pura. 15/11/2026 (editoria): o Earth Engine cobra processamento; não se soma o que não mudou."""
    return sorted(m for m, v in agora.items() if m not in tem or (m in antes and antes[m] != v))


def precisa_somar(existe: bool, antes, agora) -> bool:
    """Produto de imagem única (coleção de fogo, água): soma só se não existe ou se a fonte mudou. Pura."""
    return not existe or (antes is not None and antes != agora)


def impressoes(ee) -> dict:
    """Só metadado, sem processamento: a data de atualização de cada imagem do Monitor e dos dois produtos."""
    mon, tok = {}, None
    while True:
        r = ee.data.listAssets({"parent": MONITOR, "pageSize": 1000, **({"pageToken": tok} if tok else {})})
        for a in r.get("assets", []):
            mon[mes_do_id(a["name"])] = a.get("updateTime") or "presente"
        tok = r.get("nextPageToken")
        if not tok:
            break
    return {"monitor": mon, "colecao": ee.data.getAsset(COLECAO).get("updateTime"),
            "agua": ee.data.getAsset(AGUA).get("updateTime")}


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


def coletar_monitor(ee, estados, mapa, anterior: dict, ler: list, na_fonte: dict) -> dict:
    col = ee.ImageCollection(MONITOR)
    publicados = sorted(na_fonte)
    tabela = {uf: dict((anterior.get("ufs") or {}).get(uf) or {}) for uf in UFS}
    for ano in sorted({p[:4] for p in ler}):
        meses = [p for p in ler if p[:4] == ano]
        imgs = [col.filter(ee.Filter.eq("year", int(ano))).filter(ee.Filter.eq("month", int(p[5:]))).first() for p in meses]
        pilha = ee.Image.cat([ee.Image(i).gt(0).unmask(0).multiply(_ha(ee)) for i in imgs])
        somas = _reduzir(ee, pilha, estados, len(meses), 4)
        for i, uf in mapa.items():
            for k, p in enumerate(meses):
                tabela[uf][p] = round((somas.get(i) or [0.0] * len(meses))[k], 1)
        print(f"  monitor {ano}: {len(meses)} mês(es) somado(s): {', '.join(meses)}", flush=True)
    return {"produto": "MapBiomas · Monitor do Fogo", "asset": MONITOR, "unidade": "hectares",
            "primeiro_mes": publicados[0], "ultimo_mes": publicados[-1], "meses": publicados, "ufs": tabela,
            "na_fonte": na_fonte}


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
            "na_fonte": ee.data.getAsset(COLECAO).get("updateTime"), "meses": [f"{a}-{m:02d}" for a in ANOS_DA_COLECAO for m in range(1, 13)], "ufs": tabela}


def coletar_agua(ee, estados, mapa) -> dict:
    img = ee.Image(AGUA)
    anos = [b.split("_")[-1] for b in img.bandNames().getInfo()]
    somas = _reduzir(ee, img.gt(0).unmask(0).multiply(_ha(ee)), estados, len(anos), 2)
    tabela = {uf: {a: round((somas.get(i) or [0.0] * len(anos))[k], 1) for k, a in enumerate(anos)} for i, uf in mapa.items()}
    print(f"  água: {anos[0]}–{anos[-1]} · Brasil {sum(tabela[uf][anos[-1]] for uf in UFS):,.0f} ha em {anos[-1]}", flush=True)
    return {"produto": "MapBiomas · Água, coleção 5", "asset": AGUA, "unidade": "hectares", "anos": anos, "ufs": tabela,
            "na_fonte": ee.data.getAsset(AGUA).get("updateTime")}


def gravar(nome: str, doc: dict, periodos: list, consultado_em: str = None) -> bool:
    faltas = completo(doc["ufs"], periodos)
    if faltas:
        print(f"✗ {nome}: nada gravado — {len(faltas)} falta(s), ex.: {faltas[:3]}")
        return False
    doc = {"_governanca": "Dado de contexto, somado dos mapas do MapBiomas por estado. Não entra no índice. "
                          "Escritor único: coletar_mapbiomas.py.",
           "fonte": "MapBiomas", "consultado_em": consultado_em or __import__("coletores_base").hoje_editorial().isoformat(), **doc}
    SAIDA.mkdir(parents=True, exist_ok=True)
    (SAIDA / nome).write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"✓ {nome}: 27 estados × {len(periodos)} período(s)")
    return True


ARQUIVOS = {"fogo_monitor.json": "meses", "fogo_colecao.json": "meses", "agua_anual.json": "anos"}


def do_artefato() -> int:
    """Traz o artefato `mapbiomas` deste run e só deixa em `data/mapbiomas/` o arquivo completo."""
    import subprocess
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        r = subprocess.run(["gh", "run", "download", os.environ["GITHUB_RUN_ID"], "--name", "mapbiomas", "--dir", tmp],
                           capture_output=True, text=True, timeout=300)
        if r.returncode != 0:   # sem artefato: nada mudou desde a última gravação, nem a data da consulta
            print(f"MapBiomas: nada a gravar, nem a data da consulta ({r.stderr.strip()[:120]})")
            return 0
        ok = True
        for nome, chave in ARQUIVOS.items():
            origem = pathlib.Path(tmp) / nome
            if not origem.exists():
                continue   # a soma pode ter sido só de um produto
            doc = json.loads(origem.read_text(encoding="utf-8"))
            ok &= gravar(nome, {k: v for k, v in doc.items() if k not in ("_governanca", "fonte", "consultado_em")}, doc[chave],
                         consultado_em=doc.get("consultado_em"))
    return 0 if ok else 1


def _ler(nome: str) -> dict:
    f = SAIDA / nome
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def _sem_meta(doc: dict) -> dict:
    return {k: v for k, v in doc.items() if k not in ("_governanca", "fonte", "consultado_em")}


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    if "--do-artefato" in sys.argv:
        return do_artefato()
    tudo = not any(a in sys.argv for a in ("--monitor", "--colecao", "--agua"))
    ee = _ee()
    agora = impressoes(ee)   # só metadado: decide o que somar antes de gastar processamento
    mon, col, agu = _ler("fogo_monitor.json"), _ler("fogo_colecao.json"), _ler("agua_anual.json")
    if "--desde-zero" in sys.argv:
        mon = {}
    tem = sorted(set().union(*[set(v) for v in (mon.get("ufs") or {}).values()])) if mon.get("ufs") else []
    somar_mon = meses_a_somar(tem, mon.get("na_fonte") or {}, agora["monitor"]) if tudo or "--monitor" in sys.argv else []
    somar_col = (tudo or "--colecao" in sys.argv) and precisa_somar(bool(col), col.get("na_fonte"), agora["colecao"])
    somar_agu = (tudo or "--agua" in sys.argv) and precisa_somar(bool(agu), agu.get("na_fonte"), agora["agua"])
    print(f"na fonte: Monitor até {max(agora['monitor'])}; a somar: Monitor {somar_mon or 'nada'}, "
          f"coleção {'sim' if somar_col else 'não'}, água {'sim' if somar_agu else 'não'}", flush=True)
    ok = True
    estados = mapa = None
    if somar_mon or somar_col or somar_agu:
        estados, mapa = _estados(ee)
    # 24/11/2026: `consultado_em` é o dia em que a fonte foi consultada, com ou sem número novo. Antes, sem
    # nada a somar, o arquivo guardava a data antiga e a figura dizia "consultado em 15/11" depois da consulta
    # de 24/11 (editoria). Consultada a fonte, os três arquivos saem com a data de hoje.
    if somar_mon or mon:
        doc = coletar_monitor(ee, estados, mapa, mon, somar_mon, agora["monitor"]) if somar_mon else \
            dict(_sem_meta(mon), na_fonte=agora["monitor"])   # nada a somar: só a impressão e a data da consulta
        ok &= gravar("fogo_monitor.json", doc, doc["meses"])
    if somar_col or col:
        doc = coletar_colecao(ee, estados, mapa) if somar_col else dict(_sem_meta(col), na_fonte=agora["colecao"])
        ok &= gravar("fogo_colecao.json", doc, doc["meses"])
    if somar_agu or agu:
        doc = coletar_agua(ee, estados, mapa) if somar_agu else dict(_sem_meta(agu), na_fonte=agora["agua"])
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
        "Monitor: soma o mês novo e o que a fonte reescreveu; o igual e o já somado sem impressão, não":
            meses_a_somar(["2026-07", "2026-08", "2026-09"], {"2026-08": "t1", "2026-09": "t1"},
                          {"2026-07": "t0", "2026-08": "t1", "2026-09": "t2", "2026-10": "t3"}) == ["2026-09", "2026-10"],
        "imagem única: soma se falta ou se a fonte mudou; sem impressão anterior, adota":
            precisa_somar(False, None, "t") and precisa_somar(True, "t0", "t1")
            and not precisa_somar(True, "t1", "t1") and not precisa_somar(True, None, "t1"),
        "id da imagem do Monitor vira mês": mes_do_id("projects/x/assets/brazil-2026-9") == "2026-09",
        "trava estrutural: só escreve em data/mapbiomas/":
            pathlib.Path(__file__).read_text(encoding="utf-8").split("def autoteste")[0].count("write_text") == 1,
    }
    falhas = [k for k, v in casos.items() if not v]
    print(f"✗ AUTOTESTE: {falhas}" if falhas else f"✓ AUTOTESTE OK — {len(casos)} casos, sem rede e sem escrita.")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
