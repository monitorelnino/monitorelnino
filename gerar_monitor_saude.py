#!/usr/bin/env python3
"""
gerar_monitor_saude.py — MARÉ · Saúde v0.3 (15/09/2026; v0.2 em 14/09; v0.1 em 05/09/2026)
==========================================================
Prontidão sanitária ESTADUAL para o ciclo El Niño 2026/2027, com a mesma gramática do MARÉ
(escada de status, régua de antecipação, faixas) mas SEPARADA dele: peso zero no índice,
arquivo próprio (data/monitor_saude.json), nunca lido por recalcular_mare.py (portão).

Por UF, três leituras — só a primeira é pontuada:
  1. PRONTIDÃO (0–100, só para UF verificada): média com pesos iguais de dois sub-elementos,
     como no componente estadual do MARÉ v3.0 (Metodologia §30):
       • instrumento operacional — status do plano estadual de saúde (arboviroses/clima):
         NOVO 100 · READ 65 · VIG 45 · ELAB 35 · LAC 0;
       • antecipação — a edição em vigor em relação à janela crítica de saúde declarada pelo
         MS (out/2026–mar/2027): edição para 2026/2027 publicada antes de 01/10/2026 → 100;
         edição 2025/2026 (temporada que acabou de passar, ainda o instrumento vigente) → 45;
         edição anterior a 2025 → 20; sem instrumento → 0.
     UF não verificada NÃO recebe número — fica declarada como tal (não é zero).
  2. RISCO OBSERVADO AGORA — dengue na capital (nível InfoDengue), avisos de calor (INMET),
     focos de fogo (INPE): contexto, nunca pontua.
  3. RISCO PROJETADO — família sanitária derivada dos boletins do Painel: contexto, nunca pontua.

Faixas (as mesmas do site): estágio inicial 0–25 · em construção 25–50 · consolidado 50–70 ·
avançado 70–100. Não há número nacional enquanto houver UF não verificada: o resumo diz quantas
foram verificadas e quantas caem em cada faixa.
  python gerar_monitor_saude.py            # grava data/monitor_saude.json
  python gerar_monitor_saude.py --autoteste
"""
import json, re, sys
from datetime import date
from pathlib import Path
from coletores_base import ler, gravar, rodar_autoteste

RAIZ = Path(__file__).resolve().parent

def _hoje():
    """Data determinística = 'atualizado_em' de data/meta.json (a última rodada que gravou dados), para que a
    cadeia de derivados reproduza o arquivo byte a byte em qualquer dia; 'hoje' só se o meta não existir."""
    import datetime as _dt, json as _js, pathlib as _pl
    try:
        a = _js.load(open(_pl.Path(__file__).resolve().parent / "data" / "meta.json", encoding="utf-8")).get("atualizado_em")
        return _dt.datetime.strptime(a, "%d/%m/%Y").date()
    except Exception:  # noqa: BLE001
        return _dt._hoje()

UFS = ["AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT","PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO"]
PONTOS_STATUS = {"NOVO": 100, "READ": 65, "VIG": 45, "ELAB": 35, "LAC": 0}
PESO_INSTRUMENTO = 0.5   # pesos iguais, como no §30
JANELA_CRITICA_INICIO = "01/10/2026"
# v0.2 (14/09/2026, §31): a régua de antecipação da saúde passa a usar as MESMAS âncoras do índice
# principal (Boletim nº 1 do Painel El Niño, 29/06/2026; +30 dias = 29/07/2026), com a janela crítica
# do MS (01/10/2026) como segundo marco — para que os quadrantes defesa civil × saúde leiam o mesmo tempo.
BOLETIM_1 = "29/06/2026"
BOLETIM_1_MAIS_30 = "29/07/2026"
# v0.3 (15/09/2026, decisão editorial): o MARÉ · Saúde ganha o mesmo terceiro componente do índice principal —
# COBERTURA POPULACIONAL SANITÁRIA: fração da população da UF (Censo 2022) que vive em município cujo plano
# localizado para o ciclo trata a saúde, ponderada pelo crédito municipal do MARÉ (CRED_POP, §5) e pelo degrau da
# variável de leitura `saude_no_plano` (0–5, §10; crédito = degrau/5). Plano ainda não lido = 0 (só o que foi lido
# conta — assimetria probatória), e a contagem de "planos sem leitura" é publicada ao lado. Pesos iguais (1/3).
VERSAO = "0.3"
PESOS = {"instrumento": 1 / 3, "cobertura": 1 / 3, "antecipacao": 1 / 3}
CATEGORIAS_MUNICIPAIS = ("plano", "plano_antigo", "plano_elaboracao", "estrutura")   # as que recebem crédito de cobertura no MARÉ


def faixa(v):
    if v is None: return "não verificado"
    return "estágio inicial" if v < 25 else "em construção" if v < 50 else "consolidado" if v < 70 else "avançado"


def temporada_da_edicao(doc: str, data: str) -> str:
    """'2026/2027' | '2025/2026' | 'anterior' | 'desconhecida' — pela menção no título ou, na falta, pela data.
    Função pura."""
    t = (doc or "")
    if re.search(r"2026\s*[/\-–]\s*20?27", t): return "2026/2027"
    if re.search(r"2025\s*[/\-–]\s*20?26", t): return "2025/2026"
    if re.search(r"2024\s*[/\-–]\s*20?25|2024\s*a\s*2026", t): return "2025/2026" if "2026" in t else "anterior"
    m = re.search(r"(\d{2}/\d{2}/)?(\d{4})", data or "")
    if m:
        ano = int(m.group(2))
        return "2026/2027" if ano >= 2026 else "2025/2026" if ano == 2025 else "anterior"
    return "desconhecida"


def _data_ordinal(data: str):
    """dd/mm/aaaa → ordinal; mm/aaaa → 1º do mês (piso da faixa, regra iii do §5.2 do MARÉ); senão None. Pura."""
    import datetime as _dt
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", (data or "").strip())
    if m: return _dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1))).toordinal()
    m = re.match(r"^(\d{2})/(\d{4})$", (data or "").strip())
    if m: return _dt.date(int(m.group(2)), int(m.group(1)), 1).toordinal()
    return None


def pontos_antecipacao(status: str, doc: str, data: str, camada: str = "ciclo") -> int:
    """Régua de antecipação da saúde — v0.2 (14/09/2026), mesmas âncoras do índice principal. Função pura.

    NOVO / READ (instrumento feito ou reeditado para o ciclo), pela data do ato:
      antes de 29/06/2026 (Boletim nº 1)                     → 100
      de 29/06 a 29/07/2026 (até 30 dias após o boletim)       → 60
      de 30/07 a 30/09/2026 (antes da janela crítica do MS)    → 50
      de 01/10/2026 em diante, ou data só no ano/desconhecida  → 30 (tardio / piso da faixa)
    VIG (plano recorrente de arboviroses/clima, sem menção ao ciclo):
      edição 2025/2026 vigente (estrutura recorrente que cobre o risco projetado) → 40
      edição anterior a 2025                                                     → 20
    ELAB → 20 · LAC / não verificado → 0.
    Plano de adaptação decenal (camada 'adaptacao', p.ex. AdaptaSUS-UF) NUNCA pontua aqui: é estrutura."""
    if status in ("LAC", "NAO_VERIFICADO", None): return 0
    if camada == "adaptacao": return 0
    if status == "ELAB": return 20
    if status in ("NOVO", "READ"):
        o = _data_ordinal(data)
        if o is None: return 30
        if o < _data_ordinal(BOLETIM_1): return 100
        if o <= _data_ordinal(BOLETIM_1_MAIS_30): return 60
        if o < _data_ordinal(JANELA_CRITICA_INICIO): return 50
        return 30
    temp = temporada_da_edicao(doc, data)   # VIG
    return {"2026/2027": 40, "2025/2026": 40, "anterior": 20}.get(temp, 20)


def prontidao(status: str, doc: str, data: str, camada: str = "ciclo"):
    """(prontidão, pontos_instrumento, pontos_antecipacao) ou (None, None, None) se não verificado. Função pura.
    v0.2: instrumento da camada 'adaptacao' (plano decenal) não é instrumento do ciclo — não pontua (estrutura)."""
    if status not in PONTOS_STATUS: return None, None, None
    if camada == "adaptacao": return None, None, None
    pi = PONTOS_STATUS[status]; pa = pontos_antecipacao(status, doc, data, camada)
    return round(PESO_INSTRUMENTO * pi + (1 - PESO_INSTRUMENTO) * pa, 1), pi, pa


def prontidao_v03(status: str, doc: str, data: str, cobertura, camada: str = "ciclo"):
    """v0.3: (prontidão, instrumento, cobertura, antecipação) com pesos iguais (1/3); (None, …) se a UF não foi
    verificada no plano estadual. `cobertura` é a cobertura populacional sanitária 0–100 (função pura)."""
    if status not in PONTOS_STATUS or camada == "adaptacao": return None, None, None, None
    pi = PONTOS_STATUS[status]; pa = pontos_antecipacao(status, doc, data, camada); pc = round(float(cobertura or 0.0), 1)
    return round(PESOS["instrumento"] * pi + PESOS["cobertura"] * pc + PESOS["antecipacao"] * pa, 1), pi, pc, pa


def cobertura_sanitaria(municipios: list, referencia: list, populacao: dict, auto: dict, confirmadas: list, cred_pop: dict) -> dict:
    """Cobertura populacional sanitária por UF (v0.3). Para cada município com plano localizado (categoria em
    CATEGORIAS_MUNICIPAIS), peso = pop × CRED_POP[categoria] × (degrau/5), onde o degrau vem da leitura confirmada
    (saude_no_plano.json, por UF+município) ou, na falta, da leitura automática (saude_no_plano_auto.json, casada pela
    URL do documento). Plano sem leitura pesa 0 e é contado. Devolve {UF: {'cobertura','planos_lidos','planos_sem_leitura',
    'pop_coberta'}}. Função pura."""
    cod, pop_uf = {}, {}
    for m in referencia:
        c = f"{int(m['codigo_ibge']):07d}"; cod[(m["uf"], m["nome"])] = c
        pop_uf[m["uf"]] = pop_uf.get(m["uf"], 0) + float(populacao.get(c, 0) or 0)
    por_url = {v.get("url"): v.get("degrau") for v in (auto or {}).values() if v.get("url") is not None and v.get("degrau") is not None}
    conf = {(x.get("uf"), x.get("municipio")): x.get("categoria") for x in (confirmadas or []) if x.get("nivel") == "municipal" and x.get("municipio")}
    saida = {uf: {"cobertura": 0.0, "planos_lidos": 0, "planos_sem_leitura": 0, "pop_coberta": 0.0} for uf in sorted(set(UFS) | set(pop_uf))}
    for r in municipios:
        cat = r.get("categoria"); uf = r.get("uf")
        if cat not in CATEGORIAS_MUNICIPAIS or uf not in saida or not cred_pop.get(cat): continue
        degrau = conf.get((uf, r.get("nome")))
        if degrau is None: degrau = por_url.get(r.get("url"))
        if degrau is None:
            saida[uf]["planos_sem_leitura"] += 1; continue
        saida[uf]["planos_lidos"] += 1
        saida[uf]["pop_coberta"] += float(populacao.get(cod.get((uf, r.get("nome")), ""), 0) or 0) * float(cred_pop[cat]) * (max(0, min(5, int(degrau))) / 5.0)
    for uf, v in saida.items():
        v["cobertura"] = round(min(100.0, 100.0 * v["pop_coberta"] / pop_uf[uf]), 1) if pop_uf.get(uf) else 0.0
        v["pop_coberta"] = int(v["pop_coberta"])
    return saida


def gerar() -> int:
    su = ler("saude_uf.json", {}) or {}; ss = ler("saude_sinais.json", {}) or {}; sr = ler("sinais_risco.json", {}) or {}
    from recalcular_mare import CRED_POP   # créditos municipais do MARÉ (§5) — a mesma escada, nunca outra
    cob = cobertura_sanitaria(ler("municipios.json", []) or [], ler("municipios_ibge_referencia.json", []) or [], ler("populacao_censo2022.json", {}) or {},
                              (ler("saude_no_plano_auto.json", {}) or {}).get("itens") or {}, (ler("saude_no_plano.json", {}) or {}).get("leituras") or [], CRED_POP)
    ufs = {}
    for uf in UFS:
        u = (su.get("uf") or {}).get(uf, {}); st = u.get("status", "NAO_VERIFICADO")
        camada = u.get("camada") or "ciclo"   # 'ciclo' (contingência/preparação) | 'adaptacao' (plano decenal → estrutura)
        p, pi, pc, pa = prontidao_v03(st, u.get("doc") or "", u.get("data") or "", cob[uf]["cobertura"], camada)
        deng = (ss.get("dengue_capitais") or {}).get(uf) or {}
        sig = ((sr.get("uf") or {}).get(uf) or {})
        avisos = (sig.get("avisos_inmet") or {}); lista = avisos.get("lista") or avisos.get("avisos") or []
        ufs[uf] = {
            "verificado": st != "NAO_VERIFICADO", "prontidao": p, "faixa": faixa(p),
            "instrumento": {"status": st, "pontos": pi, "doc": u.get("doc"), "data": u.get("data"), "orgao": u.get("orgao"), "url": u.get("url"),
                            "temporada": temporada_da_edicao(u.get("doc") or "", u.get("data") or "") if st in PONTOS_STATUS else None},
            "cobertura": {"pontos": pc if st in PONTOS_STATUS and camada != "adaptacao" else None, "cobertura_pct": cob[uf]["cobertura"], "pop_coberta": cob[uf]["pop_coberta"],
                          "planos_lidos": cob[uf]["planos_lidos"], "planos_sem_leitura": cob[uf]["planos_sem_leitura"]},
            "antecipacao": {"pontos": pa, "boletim_1": BOLETIM_1, "janela_critica_inicio": JANELA_CRITICA_INICIO},
            "camada": camada,
            "risco_atual": {"dengue_capital_nivel": deng.get("nivel"), "dengue_capital": deng.get("municipio"), "dengue_se": deng.get("se"),
                            "avisos_calor": sum(1 for x in lista if re.search(r"calor", json.dumps(x, ensure_ascii=False), re.I)),
                            "focos_24h": ((sig.get("fogo") or {}).get("focos_24h"))},
            "risco_projetado": u.get("risco_sanitario_projetado") or [],
        }
    # 15/09/2026 (MARÉ Saúde espelha o MARÉ · Defesa civil): RESPOSTA sanitária como índice 0–100 = 100 × população (Censo 2022)
    # dos estados com emergência sanitária declarada no ciclo (ESPIN federal ou decreto estadual, saude_sinais.emergencias)
    # sobre a população do país; contagem ao lado. Zero de verdade enquanto nenhuma for localizada — nunca imputado.
    pop_censo = ler("populacao_censo2022.json", {}) or {}
    pop_uf = {}
    for m in (ler("municipios_ibge_referencia.json", []) or []):
        pop_uf[m["uf"]] = pop_uf.get(m["uf"], 0) + float(pop_censo.get(f"{int(m['codigo_ibge']):07d}", 0) or 0)
    emergencias = [e for e in ((ss.get("emergencias") or []) if isinstance(ss.get("emergencias"), list) else []) if isinstance(e, dict)]
    ufs_em = sorted({e.get("uf") for e in emergencias if e.get("uf") in UFS})
    pop_total = sum(pop_uf.values()); pop_em = sum(pop_uf.get(u, 0) for u in ufs_em)
    resposta = {"emergencias": len(emergencias), "ufs": ufs_em, "pop_sob_emergencia": int(pop_em), "pop_total": int(pop_total),
                "indice": round(100.0 * pop_em / pop_total, 1) if pop_total else 0.0, "desde": "29/06/2026",
                "fontes": ["DOU (ESPIN)", "diários oficiais estaduais"], "nota": "índice de resposta sanitária = parcela da população em estado com emergência sanitária declarada no ciclo; contagem de emergências ao lado; nunca somado à antecipação"}
    verificadas = [uf for uf in UFS if ufs[uf]["verificado"]]
    por_faixa = {}
    for uf in verificadas: por_faixa[ufs[uf]["faixa"]] = por_faixa.get(ufs[uf]["faixa"], 0) + 1
    saida = {
        "_governanca": ("MARÉ · Saúde v0.3 (15/09/2026; v0.2 em 14/09; v0.1 em 05/09/2026): prontidão sanitária estadual para o ciclo, separada do MARÉ "
                        "(peso zero no índice; nunca lida por recalcular_mare.py). Três componentes com pesos iguais (1/3), como no índice principal: "
                        "instrumento estadual × cobertura populacional sanitária (população em município cujo plano localizado trata a saúde, "
                        "crédito municipal do MARÉ × degrau/5 da leitura saude_no_plano; plano sem leitura = 0, contado) × antecipação. "
                        "Duas leituras de contexto (risco observado e projetado). UF não verificada não recebe número. Sem número nacional "
                        "enquanto houver UF não verificada. Metodologia §31."),
        "versao": VERSAO, "gerado_em": _hoje().strftime("%d/%m/%Y"), "corte": su.get("corte"),
        "metodo": {"pesos": dict(PESOS), "escada": PONTOS_STATUS,
                   "cobertura": {"formula": "100 × Σ(pop_mun × CRED_POP[categoria] × degrau/5) / pop_UF", "creditos_municipais": {k: CRED_POP[k] for k in CATEGORIAS_MUNICIPAIS},
                                 "degraus_saude_no_plano": {"0": "ausente", "1": "orgao_listado", "2": "resposta", "3": "vigilancia_pos", "4": "prevencao_epidemiologica", "5": "riscos_do_ciclo"},
                                 "plano_sem_leitura": "0 (contado em planos_sem_leitura)"},
                   "antecipacao": {"NOVO/READ antes de 29/06/2026": 100, "NOVO/READ até 29/07/2026": 60, "NOVO/READ até 30/09/2026": 50,
                                   "NOVO/READ de 01/10/2026 em diante ou sem data": 30, "VIG edição 2025/2026 (recorrente que cobre o risco)": 40,
                                   "VIG edição anterior": 20, "ELAB": 20, "sem instrumento": 0,
                                   "plano de adaptação decenal (AdaptaSUS-UF)": "não pontua — estrutura"},
                   "ancoras": {"boletim_1": BOLETIM_1, "boletim_1_mais_30": BOLETIM_1_MAIS_30, "janela_critica_ms": JANELA_CRITICA_INICIO},
                   "faixas": {"estágio inicial": "0–25", "em construção": "25–50", "consolidado": "50–70", "avançado": "70–100"}},
        "resposta": resposta,
        "resumo": {"verificadas": len(verificadas), "nao_verificadas": 27 - len(verificadas), "por_faixa": por_faixa,
                   "planos_municipais_lidos": sum(v["planos_lidos"] for v in cob.values()), "planos_municipais_sem_leitura": sum(v["planos_sem_leitura"] for v in cob.values()),
                   "media_das_verificadas": (round(sum(ufs[u]["prontidao"] for u in verificadas) / len(verificadas), 1) if verificadas else None),
                   "nota": "a média cobre só as UFs verificadas e não é um número nacional"},
        "ufs": ufs,
    }
    gravar("monitor_saude.json", saida)
    print(f"monitor_saude: {len(verificadas)}/27 verificadas · por faixa {por_faixa} · média das verificadas {saida['resumo']['media_das_verificadas']}")
    return 0


def autoteste() -> int:
    def t1(): return temporada_da_edicao("Plano 2025/2026", "01/07/2025") == "2025/2026" and temporada_da_edicao("Plano 2026-2027", "") == "2026/2027"
    def t2(): return temporada_da_edicao("Plano de Enfrentamento", "22/12/2023") == "anterior" and temporada_da_edicao("Atualização 2024 a 2026", "05/2025") == "2025/2026"
    def t3(): return prontidao("VIG", "Plano 2025/2026", "01/07/2025") == (42.5, 45, 40) and prontidao("NOVO", "Plano El Niño 2026-2027", "27/08/2026") == (75.0, 100, 50)
    def t4(): return prontidao("VIG", "Plano de Enfrentamento", "22/12/2023") == (32.5, 45, 20) and prontidao("LAC", "", "") == (0.0, 0, 0)
    def t8():  # v0.2: âncoras do índice principal — antes do boletim 100; até +30 dias 60; antes da janela do MS 50; depois 30; data só no ano 30
        return (pontos_antecipacao("NOVO", "", "08/06/2026") == 100 and pontos_antecipacao("NOVO", "", "29/07/2026") == 60
                and pontos_antecipacao("NOVO", "", "30/07/2026") == 50 and pontos_antecipacao("READ", "", "01/10/2026") == 30
                and pontos_antecipacao("NOVO", "", "2026") == 30 and pontos_antecipacao("NOVO", "", "06/2026") == 100)
    def t9():  # v0.2: plano de adaptação decenal (camada 'adaptacao') nunca pontua — é estrutura
        return prontidao("NOVO", "Plano Estadual de Adaptação do Setor Saúde", "01/04/2026", "adaptacao") == (None, None, None)
    def t5(): return prontidao("NAO_VERIFICADO", "", "") == (None, None, None) and faixa(None) == "não verificado"
    def t6(): return faixa(24.9) == "estágio inicial" and faixa(25) == "em construção" and faixa(50) == "consolidado" and faixa(70) == "avançado"
    def t7():  # negativo: status fora do vocabulário não vira número
        return prontidao("TALVEZ", "x", "2026") == (None, None, None) and prontidao_v03("TALVEZ", "x", "2026", 50) == (None, None, None, None)
    def t10():  # v0.3: três componentes com pesos iguais; cobertura entra como está (0–100)
        return prontidao_v03("VIG", "Plano 2025/2026", "01/07/2025", 30.0) == (38.3, 45, 30.0, 40) and prontidao_v03("NOVO", "Plano 2026-2027", "27/08/2026", 0) == (50.0, 100, 0.0, 50)
    def t11():  # v0.3: cobertura sanitária = pop × crédito municipal × degrau/5; sem leitura = 0 e contado; confirmada vence a automática
        ref = [{"uf": "XX", "nome": "A", "codigo_ibge": 1}, {"uf": "XX", "nome": "B", "codigo_ibge": 2}, {"uf": "XX", "nome": "C", "codigo_ibge": 3}, {"uf": "XX", "nome": "D", "codigo_ibge": 4}]
        pop = {"0000001": 100, "0000002": 100, "0000003": 100, "0000004": 100}
        muns = [{"uf": "XX", "nome": "A", "categoria": "plano", "url": "u1"}, {"uf": "XX", "nome": "B", "categoria": "plano_antigo", "url": "u2"}, {"uf": "XX", "nome": "C", "categoria": "plano", "url": "u3"}, {"uf": "XX", "nome": "D", "categoria": "decreto", "url": "u4"}]
        auto = {"h1": {"url": "u1", "degrau": 2}, "h2": {"url": "u2", "degrau": 5}}
        conf = [{"nivel": "municipal", "uf": "XX", "municipio": "A", "categoria": 5}]
        c = cobertura_sanitaria(muns, ref, pop, auto, conf, {"plano": 1.0, "plano_antigo": 0.6})
        return c["XX"]["cobertura"] == 40.0 and c["XX"]["planos_lidos"] == 2 and c["XX"]["planos_sem_leitura"] == 1 and c["XX"]["pop_coberta"] == 160
    return rodar_autoteste({"temporada pelo título": t1, "temporada pela data": t2, "prontidão: VIG 2025/26 = 42,5; NOVO 27/08 = 75": t3,
                            "prontidão: edição antiga = 32,5; LAC = 0": t4, "não verificado não recebe número": t5,
                            "faixas nos limites": t6, "negativo: status inválido não pontua": t7,
                            "v0.2: âncoras do índice principal": t8, "v0.2: plano decenal não pontua": t9,
                            "v0.3: três componentes, pesos iguais": t10, "v0.3: cobertura sanitária por população": t11})


if __name__ == "__main__":
    sys.exit(autoteste() if "--autoteste" in sys.argv else gerar())
