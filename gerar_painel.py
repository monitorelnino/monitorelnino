#!/usr/bin/env python3
"""
gerar_painel.py — painel amostral estratificado (E11; doc de redesenho §10-bis)
================================================================================
Universo: 5.571 municípios (municipios_ibge_referencia.json; população Censo 2022).
Estratos: (1) UF; (2) porte SUAS/IBGE — pequeno I ≤ 20 mil · pequeno II 20–50 mil ·
médio 50–100 mil · grande 100–900 mil · metrópole > 900 mil; (3) marcador de risco
oficial com lista nominal ARQUIVADA (data/painel/marcador_*.json, com hash): hoje só
`geo_hidrologico` (Anexo I da NT 1/2023, 1.942); seca/SUDENE, incêndio/MS, calor, arboviroses
e Cemaden ficam DECLARADOS como indisponíveis até serem arquivados pela Action ler_documento
(E8) — a alocação por marcador usa o que existe e diz o que falta; (4) estado no banco MARÉ.

Tamanho e alocação: 12 por UF (324). Dentro da UF: por porte, proporcional ao universo da UF,
mínimo 1 por classe existente; por marcador, mínimo 2 no marcador dominante disponível e 1 no
controle (sem marcador arquivado); capitais fora da cota. Sorteio determinístico com semente
única (random.Random(semente)), lista e semente publicadas ANTES da primeira verificação;
troca posterior só por errata. Ponte Serrada/SC (4213401; sorteado em 02/09 com semente
20260902 sobre os 1.942) integra o painel por decisão registrada.

Saídas em data/painel/: lista.json (imutável; hash), fichas.json (mesmas colunas para os 324,
com fonte e data por campo), agregados.json (região × porte × risco). Nada é lido pelo motor.

USO  python3 gerar_painel.py --sortear --semente 20260902     # só antes da publicação
     python3 gerar_painel.py --fichas                          # reverificação semanal
     python3 gerar_painel.py --autoteste
"""
import hashlib, json, pathlib, random, sys
from datetime import date

RAIZ = pathlib.Path(__file__).parent; D = RAIZ / "data"; P = D / "painel"
UFS = "AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO".split()
REGIAO = {**{u: "Norte" for u in "AC AM AP PA RO RR TO".split()}, **{u: "Nordeste" for u in "AL BA CE MA PB PE PI RN SE".split()},
          **{u: "Centro-Oeste" for u in "DF GO MS MT".split()}, **{u: "Sudeste" for u in "ES MG RJ SP".split()}, **{u: "Sul" for u in "PR RS SC".split()}}
PORTES = [("pequeno_I", 0, 20000), ("pequeno_II", 20000, 50000), ("medio", 50000, 100000), ("grande", 100000, 900000), ("metropole", 900000, 10**9)]
MARCADORES_PREVISTOS = ["geo_hidrologico", "seca_sudene", "incendio_fumaca_ms", "calor_painel_ms", "arboviroses_infodengue", "monitoramento_cemaden"]
POR_UF = 12; FORCADOS = {"4213401": "Ponte Serrada/SC — sorteado em 02/09/2026 com semente 20260902 sobre os 1.942 (decisão registrada, §10-bis)"}


def j(p): return json.load(open(p, encoding="utf-8"))
def w(p, o):
    P.mkdir(exist_ok=True); json.dump(o, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1); open(p, "a").write("\n")
def porte(pop):
    for nome, a, b in PORTES:
        if a <= pop < b: return nome
    return "metropole"


def marcadores_disponiveis():
    disp = {}
    for m in MARCADORES_PREVISTOS:
        p = P / f"marcador_{m}.json"
        disp[m] = set(j(p)["ibge"]) if p.exists() else None
    return disp


def universo():
    ref = j(D / "municipios_ibge_referencia.json"); pop = j(D / "populacao_censo2022.json")
    caps = {(u["capital"]["nome"] if isinstance(u.get("capital"), dict) else u.get("capital"), u["uf"]) for u in j(D / "estados.json")["ufs"]}
    disp = marcadores_disponiveis()
    out = []
    for r in ref:
        cod = str(r["codigo_ibge"]).zfill(7); p = int(pop.get(cod) or pop.get(str(r["codigo_ibge"])) or 0)
        marc = [m for m, s in disp.items() if s and cod in s]
        out.append({"ibge": cod, "nome": r["nome"], "uf": r["uf"], "regiao": REGIAO[r["uf"]], "populacao": p, "porte": porte(p),
                    "capital": (r["nome"], r["uf"]) in caps, "marcadores": marc, "controle": not marc})
    return out, disp


def sortear(semente: int):
    uni, disp = universo(); rng = random.Random(semente); lista = []
    for uf in UFS:
        cand = [m for m in uni if m["uf"] == uf and not m["capital"]]
        if not cand:  # DF: um único município, que é a capital — exceção declarada (§10-bis: "12 por UF" não é alcançável no DF)
            cand = [dict(m, excecao="DF tem um único município (a capital); entra fora da regra de exclusão de capitais") for m in uni if m["uf"] == uf]
        n = min(POR_UF, len(cand)); escolhidos = []
        # forçados (decisão registrada) entram primeiro
        for m in cand:
            if m["ibge"] in FORCADOS: escolhidos.append(m)
        # cota por porte: proporcional, mínimo 1 por classe existente
        por_porte = {}
        for m in cand: por_porte.setdefault(m["porte"], []).append(m)
        cotas = {p: max(1, round(n * len(v) / len(cand))) for p, v in por_porte.items()}
        while sum(cotas.values()) > n:
            pmax = max(cotas, key=lambda k: cotas[k]); cotas[pmax] -= 1
        while sum(cotas.values()) < n:
            pmax = max(por_porte, key=lambda k: len(por_porte[k]) - cotas.get(k, 0)); cotas[pmax] += 1
        # marcador dominante disponível: mínimo 2; controle: mínimo 1
        dominante = max((m for m in disp if disp[m]), key=lambda m: sum(1 for c in cand if m in c["marcadores"]), default=None)
        def tirar(pool, k):
            pool = [x for x in pool if x not in escolhidos]; rng.shuffle(pool); return pool[:k]
        if dominante: escolhidos += tirar([c for c in cand if dominante in c["marcadores"]], max(0, 2 - sum(1 for e in escolhidos if dominante in e["marcadores"])))
        escolhidos += tirar([c for c in cand if c["controle"]], max(0, 1 - sum(1 for e in escolhidos if e["controle"])))
        for p, k in cotas.items():
            ja = sum(1 for e in escolhidos if e["porte"] == p)
            escolhidos += tirar(por_porte[p], max(0, k - ja))
        escolhidos = escolhidos[:n]
        while len(escolhidos) < n: escolhidos += tirar(cand, n - len(escolhidos))
        lista += sorted(escolhidos, key=lambda m: m["ibge"])
    ibges = [m["ibge"] for m in lista]; h = hashlib.sha256(json.dumps(ibges).encode()).hexdigest()
    w(P / "lista.json", {"_governanca": "LISTA IMUTÁVEL do painel amostral (E11, §10-bis). Publicada antes da primeira verificação; troca só por errata. "
                                       "verificar_painel.py bloqueia se o hash mudar. Nunca lida pelo cálculo do índice.",
                        "semente": semente, "n": len(ibges), "por_uf": POR_UF, "hash_lista": h, "sorteado_em": date.today().isoformat(), "lista_publicada_em": date.today().strftime("%d/%m/%Y"),
                        "marcadores_disponiveis": [m for m in MARCADORES_PREVISTOS if disp[m]], "marcadores_indisponiveis": [m for m in MARCADORES_PREVISTOS if not disp[m]],
                        "forcados": FORCADOS, "criterios": "12 por UF; capitais fora; porte proporcional (mín. 1 por classe); mín. 2 no marcador dominante disponível; mín. 1 controle; sorteio random.Random(semente)",
                        "municipios": [{k: m[k] for k in ("ibge", "nome", "uf", "regiao", "populacao", "porte", "marcadores", "controle") + (("excecao",) if m.get("excecao") else ())} for m in lista],
                        "nota_n": "324 = 12 × 27 no documento de redesenho; o DF tem um único município (a capital), logo o painel tem 313 = 12 × 26 + 1, com a exceção declarada."})
    print(f"painel: {len(ibges)} municípios sorteados (semente {semente}); hash {h[:12]}…; marcadores disponíveis: {[m for m in MARCADORES_PREVISTOS if disp[m]]}")
    return h


def fichas():
    lst = j(P / "lista.json"); hoje = date.today().strftime("%d/%m/%Y")
    vm = {v["ibge"].zfill(7): v for v in j(D / "verificacao_municipal.json")}
    mun = {(m["nome"], m["uf"]): m for m in j(D / "municipios.json")}
    atos = j(D / "atos_resposta.json")["eventos"]
    decl = (j(D / "declarado_nacional.json") if (D / "declarado_nacional.json").exists() else {}).get("municipios", {})
    rotas = j(D / "financiamento" / "rotas.json")["rotas"]
    out = []
    for m in lst["municipios"]:
        v = vm.get(m["ibge"], {}); reg = mun.get((m["nome"], m["uf"]), {}); ev = [e for e in atos if e.get("ibge") == m["ibge"] or (e["nome"], e["uf"]) == (m["nome"], m["uf"])]
        out.append({**{k: m.get(k) for k in ("ibge", "nome", "uf", "regiao", "populacao", "porte", "marcadores", "controle", "excecao")}, "nivel_verificacao": v.get("nivel_verificacao", "nao_verificado"), "instrumento_localizado": reg.get("categoria"), "natureza": reg.get("categoria") and ("ex_ante" if reg["categoria"] in ("plano", "plano_antigo", "plano_elaboracao", "coberto_estadual") else "resposta" if reg["categoria"] == "decreto" else None),
                    "documento": reg.get("documento"), "data_ato": reg.get("data"), "data_localizacao": reg.get("data_localizacao"), "fonte_instrumento": reg.get("fonte"),
                    "decreto_reconhecido": v.get("decreto_reconhecido"), "decreto_homologado": v.get("decreto_homologado"),
                    "plano_declarado_munic": (decl.get(m["ibge"]) or {}).get("munic_plano_contingencia"), "plano_declarado_icm": (decl.get(m["ibge"]) or {}).get("icm_var8_plano_contingencia"),
                    "atos_resposta": len(ev), "rotas_2025": {r["id"]: None for r in rotas}, "rotas_2026": {r["id"]: None for r in rotas}, "rotas_status": "aguardando_coleta",
                    "programas_permanentes": "aguardando_coleta", "marcadores_semana": m["marcadores"],
                    "fontes": {"verificacao": "data/verificacao_municipal.json", "instrumento": "data/municipios.json", "atos": "data/atos_resposta.json", "declarado": "data/declarado_nacional.json (simulado)", "rotas": "data/financiamento/ (aguardando coleta)"}, "data_ficha": hoje})
    w(P / "fichas.json", {"_governanca": "Fichas dos 324 (mesmas colunas). Reverificadas toda segunda-feira. Cada campo com fonte declarada; nulo = não coletado. Peso zero.", "data": hoje, "fichas": out})
    # agregados região × porte × risco
    agg = {}
    for f in out:
        risco = f["marcadores"][0] if f["marcadores"] else "controle"
        k = (f["regiao"], f["porte"], risco); a = agg.setdefault(k, {"regiao": k[0], "porte": k[1], "risco": k[2], "n": 0, "com_instrumento": 0, "so_resposta": 0, "nao_verificados": 0, "decreto_reconhecido": 0})
        a["n"] += 1
        if f["natureza"] == "ex_ante": a["com_instrumento"] += 1
        if f["natureza"] == "resposta": a["so_resposta"] += 1
        if f["nivel_verificacao"] == "nao_verificado": a["nao_verificados"] += 1
        if f["decreto_reconhecido"]: a["decreto_reconhecido"] += 1
    w(P / "agregados.json", {"_governanca": "Agregados região × porte × risco (leitura honesta: não por UF isolada). Rotas em R$ entram quando a coleta existir.", "data": hoje,
                             "semente": lst["semente"], "n": lst["n"], "hash_lista": lst["hash_lista"], "lista_publicada_em": lst["lista_publicada_em"], "agregados": sorted(agg.values(), key=lambda a: (a["regiao"], a["porte"], a["risco"]))})
    print(f"fichas: {len(out)} · agregados: {len(agg)} células")


def autoteste():
    from coletores_base import rodar_autoteste
    def t1(): u, d = universo(); return len(u) == 5571 and sum(1 for m in u if m["capital"]) == 27
    def t2(): return [porte(p) for p in (0, 19999, 20000, 49999, 50000, 99999, 100000, 899999, 900000)] == ["pequeno_I", "pequeno_I", "pequeno_II", "pequeno_II", "medio", "medio", "grande", "grande", "metropole"]
    def t3():
        import copy, tempfile, shutil
        h1 = sortear(20260902); l1 = j(P / "lista.json"); h2 = sortear(20260902); l2 = j(P / "lista.json")
        return h1 == h2 and l1["municipios"] == l2["municipios"] and l1["n"] == 313 and all(sum(1 for m in l1["municipios"] if m["uf"] == u) == (1 if u == "DF" else 12) for u in UFS)
    def t4():
        l = j(P / "lista.json"); caps = {(u["capital"]["nome"] if isinstance(u.get("capital"), dict) else u.get("capital"), u["uf"]) for u in j(D / "estados.json")["ufs"]}
        return all((m["nome"], m["uf"]) not in caps or m.get("excecao") for m in l["municipios"]) and any(m["ibge"] == "4213401" for m in l["municipios"])
    def t5():
        l = j(P / "lista.json"); ok = True
        for u in UFS:
            if u == "DF": continue
            ms = [m for m in l["municipios"] if m["uf"] == u]
            ok &= sum(1 for m in ms if "geo_hidrologico" in m["marcadores"]) >= 2 and sum(1 for m in ms if m["controle"]) >= 1
        return ok
    def t6(): fichas(); f = j(P / "fichas.json")["fichas"]; return len(f) == 313 and all(x["fontes"] and x["data_ficha"] for x in f)
    return rodar_autoteste({"universo: 5.571 e 27 capitais": t1, "faixas de porte": t2, "sorteio determinístico: 313 (12 por UF; DF = 1), mesma lista para a mesma semente": t3,
                            "sem capitais; Ponte Serrada presente": t4, "mín. 2 no marcador dominante e 1 controle por UF": t5, "fichas: 313 com fonte e data": t6})


if __name__ == "__main__":
    if "--autoteste" in sys.argv: sys.exit(autoteste())
    if "--sortear" in sys.argv:
        s = int(sys.argv[sys.argv.index("--semente") + 1]) if "--semente" in sys.argv else 20260902
        if (P / "lista.json").exists() and "--forcar" not in sys.argv:
            print("lista já publicada — imutável (troca só por errata, com --forcar e registro)"); sys.exit(1)
        sortear(s); fichas(); sys.exit(0)
    if "--fichas" in sys.argv: fichas(); sys.exit(0)
    print(__doc__)
