#!/usr/bin/env python3
"""
coletar_desfechos_saude.py — Monitor de desfechos em saúde, "o que aconteceu" (§8 das instruções, 07/09/2026)
=================================================================================================================
Terceira coluna: índice (preparação) · contador (resposta) · OBSERVADO (desfecho). Peso zero, sem nota, sem faixa.
Toda superfície carrega: "o Monitor não atribui casos ao El Niño".

Fonte primária: InfoDengue `alertcity` (Fiocruz/FGV), sem chave — uma consulta por município do painel amostral
(313 municípios) com a janela 2019–2026 numa chamada só (ey_start=2019). Campos usados: casos (notificados,
Sinan via InfoDengue), casos_est (nowcasting) com casos_est_min/max, p_inc100k, nivel, pop.
Canal endêmico: mediana, p75 e p90 das MESMAS semanas epidemiológicas de 2019–2025 (2024 fora do canal e
marcado à parte, por ser o ano epidêmico recorde), calculado sobre os notificados da própria série.
Semanas incompletas (últimas 4 SE disponíveis) ficam VAZADAS na série consolidada; o nowcasting entra como faixa creditada.
Ciclo: SE 27/2026 → SE 13/2027. "Acima do esperado" = > p75 por 2 SE seguidas; "epidêmico" = > p90.

Produz data/saude_desfechos/{serie_painel,serie_uf,canal_endemico,completude}.json.
  python coletar_desfechos_saude.py --autoteste
"""
import json, statistics, sys, time, urllib.parse
from collections import defaultdict
from datetime import date
from pathlib import Path
from coletores_base import ler, gravar, buscar, registrar_lacuna, log_busca, rodar_autoteste, preservar_evidencia

RAIZ = Path(__file__).resolve().parent
API = "https://info.dengue.mat.br/api/alertcity?geocode={geocode}&disease=dengue&format=json&ew_start=1&ew_end=53&ey_start=2019&ey_end=2026"
ANOS_CANAL = [2019, 2020, 2021, 2022, 2023, 2025]     # 2024 à parte
SE_INCOMPLETAS = 4
RESSALVA = "O Monitor não atribui casos ao El Niño; a série é a do InfoDengue (Fiocruz/FGV), notificações do Sinan com estimativa de nowcasting nas semanas recentes."


def _hoje():
    import datetime as _dt, json as _js
    try:
        a = _js.load(open(RAIZ / "data" / "meta.json", encoding="utf-8")).get("atualizado_em")
        return _dt.datetime.strptime(a, "%d/%m/%Y").date()
    except Exception:  # noqa: BLE001
        return _dt.date.today()


def parse_serie(dados) -> dict:
    """{'AAAA-SS': {casos, est, est_min, est_max, inc, nivel, pop}} de uma resposta alertcity. Função pura."""
    out = {}
    for r in (dados if isinstance(dados, list) else []):
        se = r.get("SE")
        if not isinstance(se, int) or se < 201900:
            continue
        out[f"{se // 100}-{se % 100:02d}"] = {"casos": r.get("casos"), "est": r.get("casos_est"), "est_min": r.get("casos_est_min"), "est_max": r.get("casos_est_max"),
                                              "inc": r.get("p_inc100k"), "nivel": r.get("nivel"), "pop": r.get("pop")}
    return out


def canal_endemico(serie: dict) -> dict:
    """{SS: {mediana, p75, p90, n_anos, 2024}} sobre 'casos' das mesmas SE de ANOS_CANAL; 2024 à parte. Função pura."""
    por_se = defaultdict(list); v2024 = {}
    for chave, v in serie.items():
        ano, ss = chave.split("-"); c = v.get("casos")
        if c is None: continue
        if int(ano) in ANOS_CANAL: por_se[ss].append(float(c))
        elif int(ano) == 2024: v2024[ss] = float(c)
    out = {}
    for ss, vals in por_se.items():
        vals = sorted(vals); n = len(vals)
        if n < 3: continue
        q = lambda p: vals[min(n - 1, max(0, int(round(p * (n - 1)))))]
        out[ss] = {"mediana": statistics.median(vals), "p75": q(0.75), "p90": q(0.90), "n_anos": n, "2024": v2024.get(ss)}
    return out


def classificar(serie: dict, canal: dict, ano: int = 2026) -> dict:
    """Por SE de `ano`: 'dentro' | 'acima_do_esperado' (> p75 por 2 SE seguidas) | 'epidemico' (> p90). Só semanas consolidadas."""
    out = {}; seguidas = 0
    for chave in sorted(k for k in serie if k.startswith(f"{ano}-")):
        ss = chave.split("-")[1]; c = serie[chave].get("casos"); ref = canal.get(ss)
        if c is None or not ref: out[chave] = "sem_canal"; seguidas = 0; continue
        if c > ref["p90"]: out[chave] = "epidemico"; seguidas += 1
        elif c > ref["p75"]:
            seguidas += 1; out[chave] = "acima_do_esperado" if seguidas >= 2 else "dentro"
        else: out[chave] = "dentro"; seguidas = 0
    return out


def vazar_incompletas(serie: dict, n: int = SE_INCOMPLETAS) -> tuple:
    """Devolve (consolidada, nowcasting): as últimas n SE disponíveis de 2026 saem da consolidada (casos = None) e ficam só como faixa est_min–est_max."""
    chaves = sorted(k for k in serie if k.startswith("2026-"))
    inc = set(chaves[-n:]) if chaves else set()
    cons = {k: ({**v, "casos": None, "inc": None} if k in inc else v) for k, v in serie.items()}
    now = {k: {"est": serie[k].get("est"), "est_min": serie[k].get("est_min"), "est_max": serie[k].get("est_max")} for k in inc}
    return cons, now


def coletar() -> int:
    lista = ler("painel/lista.json", {}) or {}
    mun = lista.get("municipios") if isinstance(lista, dict) else lista
    if not mun:
        print("desfechos: painel amostral ausente"); return 0
    hoje = _hoje().strftime("%d/%m/%Y"); serie_painel = {}; canal = {}; completude = {}; por_uf = defaultdict(lambda: defaultdict(lambda: {"casos": 0.0, "est": 0.0, "n": 0}))
    ok = 0; falhas = []
    for m in mun:
        cod = str(m["ibge"]).zfill(7); url = API.format(geocode=cod)
        try:
            time.sleep(0.25)
            bruto = buscar(url, timeout=60); dados = json.loads(bruto.decode("utf-8", "replace"))
        except Exception as e:  # noqa: BLE001
            falhas.append(f"{m['nome']}/{m['uf']}: {type(e).__name__}"); continue
        s = parse_serie(dados)
        if not s: continue
        ok += 1
        c = canal_endemico(s); cons, now = vazar_incompletas(s)
        cls = classificar(s, c)
        ult = sorted(k for k in s if k.startswith("2026-"))[-1] if any(k.startswith("2026-") for k in s) else None
        serie_painel[cod] = {"nome": m["nome"], "uf": m["uf"], "pop": next((v.get("pop") for v in s.values() if v.get("pop")), None),
                             "semanas_2026": {k: v for k, v in cons.items() if k.startswith("2026-")}, "nowcasting": now, "classe": cls,
                             "acumulado": {str(a): round(sum(float(v["casos"] or 0) for k, v in s.items() if k.startswith(f"{a}-")), 1) for a in (2024, 2025, 2026)},
                             "ultima_se": ult, "nivel_ultima_se": (s.get(ult) or {}).get("nivel") if ult else None}
        canal[cod] = c; completude[cod] = {"ultima_se_disponivel": ult, "se_vazadas": sorted(now.keys())}
        for k, v in s.items():
            if k.startswith(("2024-", "2025-", "2026-")) and v.get("casos") is not None:
                por_uf[m["uf"]][k]["casos"] += float(v["casos"]); por_uf[m["uf"]][k]["est"] += float(v.get("est") or 0); por_uf[m["uf"]][k]["n"] += 1
    if falhas:   # uma lacuna por rodada, não uma por município (o log não é lugar de ruído de rede)
        registrar_lacuna("InfoDengue (painel amostral)", f"{len(falhas)} município(s) sem resposta — ex.: {falhas[0]}", canal="DOU", camada=1)
    if not ok:
        print("desfechos: nenhuma série coletada — lacuna declarada"); return 0
    (RAIZ / "data" / "saude_desfechos").mkdir(parents=True, exist_ok=True)
    gov = ("Monitor de desfechos em saúde (§8, 07/09/2026): terceira coluna — observado. Peso zero, sem nota, sem faixa. " + RESSALVA +
           " Canal endêmico: mediana/p75/p90 das mesmas SE de 2019–2025 (2024 à parte). Últimas 4 SE vazadas na série consolidada; nowcasting como faixa.")
    gravar("saude_desfechos/serie_painel.json", {"_governanca": gov, "gerado_em": hoje, "fonte": "InfoDengue (Fiocruz/FGV), alertcity", "municipios": serie_painel})
    gravar("saude_desfechos/canal_endemico.json", {"_governanca": gov, "gerado_em": hoje, "anos_canal": ANOS_CANAL, "ano_a_parte": 2024, "municipios": canal})
    gravar("saude_desfechos/completude.json", {"_governanca": gov, "gerado_em": hoje, "se_incompletas": SE_INCOMPLETAS, "municipios": completude})
    gravar("saude_desfechos/serie_uf.json", {"_governanca": gov + " Soma dos municípios do painel amostral por UF — não é o total da UF.", "gerado_em": hoje,
                                              "uf": {uf: {k: {"casos": round(v["casos"], 1), "est": round(v["est"], 1), "n_municipios": v["n"]} for k, v in sorted(d.items())} for uf, d in por_uf.items()}})
    log_busca("DOU", 1, [API.format(geocode="<ibge>")], "registro", nivel="nacional", n_resultados=ok, resultados=f"Desfechos em saúde: {ok} municípios do painel com série InfoDengue 2019–2026; canal endêmico e nowcasting calculados")
    print(f"desfechos: {ok}/{len(mun)} municípios do painel com série; última SE disponível: {max((v['ultima_se'] or '') for v in serie_painel.values())}")
    return 0


def autoteste() -> int:
    d = [{"SE": 201901, "casos": 10, "casos_est": 11, "casos_est_min": 9, "casos_est_max": 13, "p_inc100k": 1.0, "nivel": 1, "pop": 100000}]
    for a in (2020, 2021, 2022, 2023, 2025): d.append({"SE": a * 100 + 1, "casos": 10 + a - 2019, "casos_est": 11, "casos_est_min": 9, "casos_est_max": 13, "pop": 100000})
    d.append({"SE": 202401, "casos": 100, "casos_est": 100})
    for w in (1, 2, 3, 4, 5, 6): d.append({"SE": 202600 + w, "casos": 30 if w <= 2 else 5, "casos_est": 31, "casos_est_min": 20, "casos_est_max": 45})
    s = parse_serie(d); c = canal_endemico(s); cons, now = vazar_incompletas(s); cls = classificar(s, c)
    def t1(): return "2019-01" in s and s["2024-01"]["casos"] == 100 and "2018-01" not in s
    def t2(): return c["01"]["n_anos"] == 6 and c["01"]["2024"] == 100 and 10 <= c["01"]["mediana"] <= 16 and c["01"]["p90"] >= c["01"]["p75"] >= c["01"]["mediana"]
    def t3(): return cons["2026-06"]["casos"] is None and cons["2026-02"]["casos"] == 30 and set(now) == {"2026-03", "2026-04", "2026-05", "2026-06"} and now["2026-06"]["est_max"] == 45
    def t4(): return cls["2026-01"] == "epidemico" and cls["2026-02"] == "sem_canal" and all(v == "sem_canal" for k, v in cls.items() if k >= "2026-02")   # só a SE 01 tem canal na fixture
    def t5(): return "não atribui casos ao El Niño" in RESSALVA and 2024 not in ANOS_CANAL
    return rodar_autoteste({"parse: SE AAAASS → chave; 2018 fora": t1, "canal: 6 anos, 2024 à parte, p90 ≥ p75 ≥ mediana": t2,
                            "últimas 4 SE vazadas; nowcasting como faixa": t3, "classificação: epidêmico > p90; sem canal declarado": t4, "ressalva e 2024 fora do canal": t5})


if __name__ == "__main__":
    sys.exit(autoteste() if "--autoteste" in sys.argv else coletar())
