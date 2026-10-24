#!/usr/bin/env python3
"""
gerar_monitor_saude.py — MARÉ · Saúde v0.7 (24/10/2026; v0.6 em 22/10; v0.5 em 21/10; v0.1 em 05/09/2026)
==========================================================
Prontidão sanitária ESTADUAL para o ciclo El Niño 2026/2027, com a mesma gramática do MARÉ
(escada de status, faixas) mas SEPARADA dele: peso zero no índice, arquivo próprio
(data/monitor_saude.json), nunca lido por recalcular_mare.py (portão). É o ÚNICO motor do Saúde.

Por UF, leituras de contexto e uma só pontuada:
  1. PRONTIDÃO (0–100, só para UF com instrumento verificado): dois componentes, metade cada:
       • instrumento operacional — status do plano estadual de saúde (arboviroses/clima):
         NOVO 100 · READ 65 · VIG 45 · ELAB 35 · LAC 0;
       • cobertura populacional — população em município cujo plano de contingência localizado trata
         a saúde, ponderada pelo crédito municipal do MARÉ e pelo degrau de leitura (0–5);
         plano não lido pesa 0 e é contado ao lado.
     Nenhum componente depende de data (decisão da editoria, 24/10/2026). UF sem instrumento
     verificado NÃO recebe número — fica declarada como tal (não é zero).
  2. TEMPO, à parte e de peso zero: `dias_apos_boletim_1` do ato do ciclo (negativo = anterior ao
     Boletim nº 1); contexto do cartão do estado, nunca nota.
  3. COORDENAÇÃO (peso zero até a v0.8): duas funções, comando interno da saúde e ligação com a
     coordenação do estado; entra na nota, um terço cada com instrumento e cobertura, quando as 27 UFs
     tiverem as duas funções verificadas (`resumo.coordenacao_verificadas`).
  4. RISCO OBSERVADO AGORA (dengue na capital, avisos de calor, focos de fogo) e RISCO PROJETADO
     (família sanitária dos boletins do Painel): contexto, nunca pontua.

Faixas (as mesmas do site): estágio inicial 0–25 · em construção 25–50 · consolidado 50–70 ·
avançado 70–100. Índice NACIONAL = média das 27 UFs, como o MARÉ Legal (`resumo_nacional`); a UF sem
documento lido entra com instrumento 0 e a cobertura que tem, e o estatuto dela viaja junto do número
(METODOLOGIA §115, §119).
  python gerar_monitor_saude.py            # grava data/monitor_saude.json
  python gerar_monitor_saude.py --autoteste
"""
import json, re, sys
from datetime import datetime
from pathlib import Path
from coletores_base import ler, gravar, rodar_autoteste, data_da_edicao

RAIZ = Path(__file__).resolve().parent


UFS = ["AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT","PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO"]
PONTOS_STATUS = {"NOVO": 100, "READ": 65, "VIG": 45, "ELAB": 35, "LAC": 0}
# Âncora do indicador de tempo (publicado à parte, peso zero): Boletim nº 1 do Painel El Niño.
BOLETIM_1 = "29/06/2026"
# v0.7 (24/10/2026, editoria): instrumento + cobertura populacional, metade cada; a antecipação sai
# da nota e o tempo vira indicador à parte. v0.8 (quando a coordenação estiver verificada nas 27 UFs):
# instrumento + coordenação + cobertura, um terço cada.
VERSAO = "0.7"
PESOS = {"instrumento": 0.5, "cobertura": 0.5}
PESOS_V08 = {"instrumento": 1 / 3, "coordenacao": 1 / 3, "cobertura": 1 / 3}

# Coordenação na saúde — construto formativo de duas funções (METODOLOGIA §91, editoria 02/10/2026);
# mede-se a FUNÇÃO, não o órgão, e um ato que cumpre as duas pontua nas duas.
#   F1 — comando interno da saúde: estrutura própria da SES (grupo condutor, sala de situação, COE).
#   F2 — ligação da saúde com a coordenação do estado: SES nomeada em comitê ou sala de governo.
COORDENACAO_SCORE = {"CRIADO_CICLO": 100, "REATIVADO_CICLO": 65, "PERMANENTE": 45, "ANUNCIADO": 35, "LAC": 0}
F1_SCORE = dict(COORDENACAO_SCORE)
# F2 tem três degraus: entre "nomeada com atribuição" e "nada", o documento só sustenta "apenas listada".
F2_SCORE = {"NOMEADA_COM_ATRIBUICAO": 100, "LISTADA_SEM_ATRIBUICAO": 50, "LAC": 0}
# Pesos iguais entre F1 e F2 por falta de base para desigualar; a robustez testa 0,4/0,6 e 0,6/0,4.
PESOS_COORDENACAO = {"f1": 0.5, "f2": 0.5}


def coordenacao_pontos(f1: str, f2: str, agregacao: str = "aritmetica", pesos=None):
    """(pontos, p_f1, p_f2) da coordenação, pela média das duas funções. Função pura.

    (None, None, None) quando QUALQUER função não foi verificada: somar metade de zero afirmaria que
    a secretaria não está na coordenação do estado porque ninguém procurou. Média aritmética: faltar
    uma função reduz, não zera; `geometrica` existe só para o teste de robustez (§91.5)."""
    if f1 not in F1_SCORE or f2 not in F2_SCORE:
        return None, None, None
    p1, p2 = F1_SCORE[f1], F2_SCORE[f2]
    w = pesos or PESOS_COORDENACAO
    total = (p1 ** w["f1"]) * (p2 ** w["f2"]) if agregacao == "geometrica" else w["f1"] * p1 + w["f2"] * p2
    return round(total, 1), p1, p2


def coordenacao_da_uf(co: dict) -> dict:
    """Bloco `coordenacao` da UF a partir do que `saude_uf.json` guarda. Função pura. Peso zero até a v0.8."""
    f1o, f2o = co.get("f1") or (co if co.get("status") else {}), co.get("f2") or {}   # forma antiga: um status só = F1
    f1, f2 = f1o.get("status") or "NAO_VERIFICADO", f2o.get("status") or "NAO_VERIFICADO"
    pontos, p1, p2 = coordenacao_pontos(f1, f2)
    def funcao(o, status, p, citada):
        return {"status": status, "pontos": p, "doc": o.get("doc"), "data": o.get("data"), "url": o.get("url"), "citado": o.get(citada)}
    return {"peso": 0, "entra_na_nota": False, "verificada": pontos is not None, "pontos": pontos,
            "f1": funcao(f1o, f1, p1, "pagina_citada"), "f2": funcao(f2o, f2, p2, "atribuicao_citada")}
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


def prontidao(status: str, cobertura, camada: str = "ciclo"):
    """(prontidão, pontos_instrumento, pontos_cobertura) ou (None, None, None) se não verificado. Função pura.
    v0.7: instrumento e cobertura populacional, metade cada; nenhum parâmetro de data. A cobertura (0–100)
    é contagem sobre planos municipais lidos e declara ao lado o que não foi lido. Instrumento da camada
    'adaptacao' (plano decenal) não é instrumento do ciclo — não pontua (estrutura)."""
    if status not in PONTOS_STATUS or camada == "adaptacao": return None, None, None
    pi, pc = PONTOS_STATUS[status], round(float(cobertura or 0.0), 1)
    return round(PESOS["instrumento"] * pi + PESOS["cobertura"] * pc, 1), pi, pc


def credito_nacional(prontidao_uf, cobertura=0.0):
    """Prontidão que a UF leva à média nacional. Função pura.

    UF com número entra com o dela. UF sem documento lido (não verificada, ou com plano que não é
    do ciclo) entra como o MARÉ Legal trata a UF sem plano localizado: instrumento 0, porque nada
    pontua sem documento lido (§104), e a cobertura que ela tem. Não é nota de UF reprovada: o número
    exibido da UF segue nulo."""
    return prontidao_uf if prontidao_uf is not None else prontidao("LAC", cobertura)[0]


def estatuto_do_plano(status: str, prontidao_uf) -> str:
    """'plano_localizado' | 'plano_nao_localizado' | 'nao_verificado'. Função pura."""
    if status == "NAO_VERIFICADO":
        return "nao_verificado"
    return "plano_nao_localizado" if status == "LAC" or prontidao_uf is None else "plano_localizado"


def resumo_nacional(ufs: dict) -> dict:
    """Índice nacional = soma das prontidões levadas à conta das 27 UFs / 27, sem excluir nenhuma
    (a mesma agregação de `recalcular_mare.py`). Função pura; UF que falta é KeyError, não média
    menor. As contagens por estatuto somam o denominador."""
    por = {k: 0 for k in ("plano_localizado", "plano_nao_localizado", "nao_verificado")}
    for uf in UFS:
        por[ufs[uf]["estatuto"]] += 1
    return {"denominador": len(UFS), "indice_nacional": round(sum(ufs[uf]["prontidao_nacional"] for uf in UFS) / len(UFS), 1),
            "por_estatuto": por}


def dias_apos_boletim_1(status: str, data: str, camada: str = "ciclo"):
    """Indicador de tempo, publicado à parte e de peso zero: dias entre o Boletim nº 1 e o ato do ciclo
    (NOVO ou READ). Função pura. Negativo = ato anterior ao boletim. `None` quando o instrumento não é
    ato do ciclo (recorrente, em elaboração, não localizado, plano decenal) ou quando a data não fecha
    em dia — mês solto não vira dia, e lacuna declarada vale mais que dia inventado."""
    if status not in ("NOVO", "READ") or camada == "adaptacao" or not re.match(r"^\d{2}/\d{2}/\d{4}$", (data or "").strip()):
        return None
    dia = lambda d: datetime.strptime(d.strip(), "%d/%m/%Y").toordinal()
    return dia(data) - dia(BOLETIM_1)


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


def resposta_sanitaria(emergencias, busca: dict, pop_uf: dict) -> dict:
    """Resposta sanitária a partir do que `saude_sinais` diz, sem inventar. Função pura.

    17/10/2026 (HANDOVER_RESPOSTA_SANITARIA §1.2): `emergencias` ausente é "não coletado" (antes
    virava lista vazia e índice 0,0); lista vazia só é 0 com as duas buscas datadas — federal (DOU)
    e estadual nas 27 —; metade sem busca deixa o índice nulo e é nomeada. ESPIN (`BR`) cobre o país."""
    pop_total = sum(pop_uf.values())
    base = {"desde": "29/06/2026", "fontes": ["DOU (ESPIN)", "diários oficiais estaduais"], "pop_total": int(pop_total),
            "nota": "índice de resposta sanitária = parcela da população em estado com emergência sanitária declarada no ciclo; contagem de emergências ao lado; nunca somado à antecipação"}
    if not isinstance(emergencias, list):
        return {**base, "situacao": "nao_coletado", "emergencias": None, "indice": None, "eventos": [], "ufs": [],
                "pop_sob_emergencia": None, "faltam": ["federal (DOU)", "estadual (27 UFs)"]}
    ev = [e for e in emergencias if isinstance(e, dict)]
    ufs_em = list(UFS) if any(e.get("uf") == "BR" for e in ev) else sorted({e.get("uf") for e in ev if e.get("uf") in UFS})
    fed, est = busca.get("federal") or {}, busca.get("estadual") or {}
    sem_estadual = [u for u in UFS if not (est.get(u) or {}).get("consultado_em")]
    faltam = ([] if fed.get("consultado_em") else ["federal (DOU)"]) + ([f"estadual: {', '.join(sem_estadual)}"] if sem_estadual else [])
    completo = len(ufs_em) == len(UFS) or not faltam   # ESPIN: nenhuma UF fica de fora
    pop_em = sum(pop_uf.get(u, 0) for u in ufs_em)
    return {**base, "situacao": "verificado" if completo else "parcial",
            "emergencias": len(ev) if completo else None,   # parcial: a lista vai em `eventos`, sem total
            "indice": round(100.0 * pop_em / pop_total, 1) if completo and pop_total else None,
            "eventos": [{k: e.get(k) for k in ("uf", "tipo", "documento", "data", "url")} for e in ev],
            "ufs": ufs_em, "pop_sob_emergencia": int(pop_em) if completo else None, "faltam": faltam,
            "consultado_em": {"federal": fed.get("consultado_em"),
                              "estadual": {u: v.get("consultado_em") for u, v in sorted(est.items()) if v.get("consultado_em")}},
            "lacunas_estaduais": {u: (est.get(u) or {}).get("lacuna") or "sem registro do canal 2" for u in sem_estadual}}


def gerar() -> int:
    from migrar_saude_instrumentos import melhor_instrumento   # 18/09/2026: instrumentos[] é a fonte de
    # verdade agora (handover ponto cego saúde §3.2) — o campo de topo de cada UF deixa de ser lido
    # direto; é recalculado do melhor item da lista a cada geração, para que uma LAI ou pista aplicada
    # só na lista (sem reescrever o topo à mão) já valha no índice na próxima rodada.
    su = ler("saude_uf.json", {}) or {}; ss = ler("saude_sinais.json", {}) or {}; sr = ler("sinais_risco.json", {}) or {}
    from recalcular_mare import CRED_POP   # créditos municipais do MARÉ (§5) — a mesma escada, nunca outra
    cob = cobertura_sanitaria(ler("municipios.json", []) or [], ler("municipios_ibge_referencia.json", []) or [], ler("populacao_censo2022.json", {}) or {},
                              (ler("saude_no_plano_auto.json", {}) or {}).get("itens") or {}, (ler("saude_no_plano.json", {}) or {}).get("leituras") or [], CRED_POP)
    ufs = {}
    for uf in UFS:
        u = (su.get("uf") or {}).get(uf, {})
        melhor = melhor_instrumento(u.get("instrumentos") or []) or u   # sem instrumentos[] (dado velho, não migrado): usa o topo como sempre
        st = melhor.get("status", "NAO_VERIFICADO")
        camada = u.get("camada") or "ciclo"   # 'ciclo' (contingência/preparação) | 'adaptacao' (plano decenal → estrutura)
        pc_uf = cob[uf]["cobertura"]
        p, pi, pc = prontidao(st, pc_uf, camada)
        deng = (ss.get("dengue_capitais") or {}).get(uf) or {}
        sig = ((sr.get("uf") or {}).get(uf) or {})
        avisos = (sig.get("avisos_inmet") or {}); lista = avisos.get("lista") or avisos.get("avisos") or []
        ufs[uf] = {
            "verificado": st != "NAO_VERIFICADO", "prontidao": p, "faixa": faixa(p),
            "instrumento": {"status": st, "pontos": pi, "doc": melhor.get("doc"), "data": melhor.get("data"), "orgao": melhor.get("orgao"), "url": melhor.get("url"),
                            "temporada": temporada_da_edicao(melhor.get("doc") or "", melhor.get("data") or "") if st in PONTOS_STATUS else None},
            "cobertura": {"peso": PESOS["cobertura"], "pontos": pc, "cobertura_pct": pc_uf, "pop_coberta": cob[uf]["pop_coberta"],
                          "planos_lidos": cob[uf]["planos_lidos"], "planos_sem_leitura": cob[uf]["planos_sem_leitura"]},
            "tempo": {"peso": 0, "boletim_1": BOLETIM_1, "dias_apos_boletim_1": dias_apos_boletim_1(st, melhor.get("data") or "", camada)},
            "coordenacao": coordenacao_da_uf(u.get("coordenacao") or {}),
            "camada": camada,
            "risco_atual": {"dengue_capital_nivel": deng.get("nivel"), "dengue_capital": deng.get("municipio"), "dengue_se": deng.get("se"),
                            "avisos_calor": sum(1 for x in lista if re.search(r"calor", json.dumps(x, ensure_ascii=False), re.I)),
                            "focos_24h": ((sig.get("fogo") or {}).get("focos_24h"))},
            "risco_projetado": u.get("risco_sanitario_projetado") or [],
            "estatuto": estatuto_do_plano(st, p), "prontidao_nacional": credito_nacional(p, pc_uf),
        }
    # 15/09/2026 (MARÉ Saúde espelha o MARÉ · Defesa civil): RESPOSTA sanitária como índice 0–100 = 100 × população (Censo 2022)
    # dos estados com emergência sanitária declarada no ciclo (ESPIN federal ou decreto estadual, saude_sinais.emergencias)
    # sobre a população do país; contagem ao lado. Zero só com as duas buscas datadas (resposta_sanitaria).
    pop_censo = ler("populacao_censo2022.json", {}) or {}
    pop_uf = {}
    for m in (ler("municipios_ibge_referencia.json", []) or []):
        pop_uf[m["uf"]] = pop_uf.get(m["uf"], 0) + float(pop_censo.get(f"{int(m['codigo_ibge']):07d}", 0) or 0)
    resposta = resposta_sanitaria(ss.get("emergencias"), ss.get("emergencias_busca") or {}, pop_uf)
    verificadas = [uf for uf in UFS if ufs[uf]["verificado"]]
    por_faixa = {}
    for uf in verificadas: por_faixa[ufs[uf]["faixa"]] = por_faixa.get(ufs[uf]["faixa"], 0) + 1
    saida = {
        "_governanca": ("MARÉ · Saúde v0.7: prontidão sanitária estadual para o ciclo, separada do MARÉ (peso zero no índice; nunca lida por "
                        "recalcular_mare.py). Dois componentes, metade cada: instrumento estadual e cobertura populacional (população em município "
                        "cujo plano de contingência localizado trata a saúde). Nenhum componente depende de data: o tempo é publicado à parte, de peso "
                        "zero, e a coordenação na saúde entra na nota, um terço cada, quando as 27 UFs a tiverem verificada. Índice nacional = média "
                        "das 27 UFs, como o MARÉ Legal; a UF sem documento lido entra com instrumento 0 e a cobertura que tem, e o estatuto dela viaja "
                        "junto. Duas leituras de contexto (risco observado e projetado). UF não verificada não recebe número próprio. "
                        "Metodologia §31, §115 e §119."),
        "versao": VERSAO, "gerado_em": data_da_edicao().strftime("%d/%m/%Y"), "corte": su.get("corte"),
        "metodo": {"pesos": dict(PESOS), "escada": PONTOS_STATUS,
                   "cobertura": {"nome": "cobertura populacional: saúde no plano municipal de defesa civil", "peso": PESOS["cobertura"], "entra_na_nota": True,
                                 "formula": "100 × Σ(pop_mun × CRED_POP[categoria] × degrau/5) / pop_UF", "creditos_municipais": {k: CRED_POP[k] for k in CATEGORIAS_MUNICIPAIS},
                                 "degraus_saude_no_plano": {"0": "ausente", "1": "orgao_listado", "2": "resposta", "3": "vigilancia_pos", "4": "prevencao_epidemiologica", "5": "riscos_do_ciclo"},
                                 "plano_sem_leitura": "0 (contado em planos_sem_leitura)"},
                   "tempo": {"peso": 0, "entra_na_nota": False, "indicador": "dias_apos_boletim_1", "ancora": BOLETIM_1,
                             "regra": "dias entre o Boletim nº 1 e o ato do ciclo (NOVO ou READ); negativo = anterior ao boletim; sem dia fechado, sem número"},
                   "coordenacao": {"peso": 0, "entra_na_nota": False, "escada_f1": F1_SCORE, "escada_f2": F2_SCORE, "pesos_das_funcoes": PESOS_COORDENACAO,
                                   "proxima_etapa": {"versao": "0.8", "pesos": {k: round(v, 4) for k, v in PESOS_V08.items()},
                                                     "condicao": "as 27 UFs com as duas funções verificadas (resumo.coordenacao_verificadas)"}},
                   "agregacao_nacional": {"formula": "Σ prontidao_nacional das 27 UFs / 27", "denominador": 27, "uf_sem_documento_lido": "instrumento 0 e a cobertura da UF (credito_nacional)"},
                   "faixas": {"estágio inicial": "0–25", "em construção": "25–50", "consolidado": "50–70", "avançado": "70–100"}},
        "resposta": resposta,
        "resumo": {"verificadas": len(verificadas), "nao_verificadas": 27 - len(verificadas), "por_faixa": por_faixa,
                   "planos_municipais_lidos": sum(v["planos_lidos"] for v in cob.values()), "planos_municipais_sem_leitura": sum(v["planos_sem_leitura"] for v in cob.values()),
                   **(nac := resumo_nacional(ufs)),
                   "ufs_com_plano_localizado": nac["por_estatuto"]["plano_localizado"],
                   "ufs_sem_plano_localizado": 27 - nac["por_estatuto"]["plano_localizado"],
                   "coordenacao_verificadas": sum(1 for uf in UFS if ufs[uf]["coordenacao"]["verificada"])},
        "ufs": ufs,
    }
    gravar("monitor_saude.json", saida)
    print(f"monitor_saude: {len(verificadas)}/27 verificadas · por faixa {por_faixa} · índice nacional {saida['resumo']['indice_nacional']} ({saida['resumo']['ufs_com_plano_localizado']} UFs com plano localizado)")
    return 0


def autoteste() -> int:
    def t1(): return temporada_da_edicao("Plano 2025/2026", "01/07/2025") == "2025/2026" and temporada_da_edicao("Plano 2026-2027", "") == "2026/2027"
    def t2(): return temporada_da_edicao("Plano de Enfrentamento", "22/12/2023") == "anterior" and temporada_da_edicao("Atualização 2024 a 2026", "05/2025") == "2025/2026"
    def t3(): return prontidao("NOVO", 60.0) == (80.0, 100, 60.0) and prontidao("VIG", 20.0) == (32.5, 45, 20.0) and prontidao("LAC", 0) == (0.0, 0, 0.0)
    def t4(): return prontidao("READ", None) == (32.5, 65, 0.0) and prontidao("ELAB", 40) == (37.5, 35, 40.0)
    def t8():  # tempo: só ato do ciclo com dia fechado; negativo antes do boletim; mês solto e recorrente sem número
        return (dias_apos_boletim_1("NOVO", "08/06/2026") == -21 and dias_apos_boletim_1("READ", "29/06/2026") == 0
                and dias_apos_boletim_1("NOVO", "03/2026") is None and dias_apos_boletim_1("VIG", "08/06/2026") is None
                and dias_apos_boletim_1("NOVO", "") is None and dias_apos_boletim_1("NOVO", "08/06/2026", "adaptacao") is None)
    def t9():  # plano de adaptação decenal (camada 'adaptacao') nunca pontua — é estrutura
        return prontidao("NOVO", 50, "adaptacao") == (None, None, None)
    def t5(): return prontidao("NAO_VERIFICADO", 50) == (None, None, None) and faixa(None) == "não verificado"
    def t6(): return faixa(24.9) == "estágio inicial" and faixa(25) == "em construção" and faixa(50) == "consolidado" and faixa(70) == "avançado"
    def t7():  # negativo: status fora do vocabulário não vira número
        return prontidao("TALVEZ", 10) == (None, None, None)
    def t10():  # v0.7: dois componentes, metade cada; nada datado na nota (a assinatura não recebe doc, data nem antecipação)
        import inspect
        return (PESOS == {"instrumento": 0.5, "cobertura": 0.5} and sum(PESOS.values()) == 1
                and list(inspect.signature(prontidao).parameters) == ["status", "cobertura", "camada"]
                and not any("antecip" in k or "tempo" in k for k in PESOS) and not any(k in PESOS for k in ("coordenacao",)))
    def t19():  # v0.8 declarada, não aplicada: um terço cada; coordenação só com as duas funções; lacuna não é zero
        return (abs(sum(PESOS_V08.values()) - 1) < 1e-9 and all(abs(v - 1 / 3) < 1e-9 for v in PESOS_V08.values())
                and coordenacao_pontos("CRIADO_CICLO", "NOMEADA_COM_ATRIBUICAO") == (100.0, 100, 100)
                and coordenacao_pontos("CRIADO_CICLO", "LISTADA_SEM_ATRIBUICAO")[0] == 75.0
                and coordenacao_pontos("PERMANENTE", "NAO_VERIFICADO") == (None, None, None)
                and coordenacao_pontos("CRIADO_CICLO", "LAC")[0] == 50.0 and coordenacao_pontos("CRIADO_CICLO", "LAC", "geometrica")[0] == 0.0)
    def t20():  # coordenação da UF: peso zero, fora da nota; forma antiga (status só) vale como F1; sem F2 não é verificada
        c = coordenacao_da_uf({"status": "PERMANENTE", "doc": "Portaria 1"})
        d = coordenacao_da_uf({"f1": {"status": "CRIADO_CICLO"}, "f2": {"status": "NOMEADA_COM_ATRIBUICAO"}})
        return (c["peso"] == 0 and not c["entra_na_nota"] and not c["verificada"] and c["f1"]["doc"] == "Portaria 1" and c["pontos"] is None
                and d["verificada"] and d["pontos"] == 100.0 and not coordenacao_da_uf({})["verificada"])
    def t11():  # v0.3: cobertura sanitária = pop × crédito municipal × degrau/5; sem leitura = 0 e contado; confirmada vence a automática
        ref = [{"uf": "XX", "nome": "A", "codigo_ibge": 1}, {"uf": "XX", "nome": "B", "codigo_ibge": 2}, {"uf": "XX", "nome": "C", "codigo_ibge": 3}, {"uf": "XX", "nome": "D", "codigo_ibge": 4}]
        pop = {"0000001": 100, "0000002": 100, "0000003": 100, "0000004": 100}
        muns = [{"uf": "XX", "nome": "A", "categoria": "plano", "url": "u1"}, {"uf": "XX", "nome": "B", "categoria": "plano_antigo", "url": "u2"}, {"uf": "XX", "nome": "C", "categoria": "plano", "url": "u3"}, {"uf": "XX", "nome": "D", "categoria": "decreto", "url": "u4"}]
        auto = {"h1": {"url": "u1", "degrau": 2}, "h2": {"url": "u2", "degrau": 5}}
        conf = [{"nivel": "municipal", "uf": "XX", "municipio": "A", "categoria": 5}]
        c = cobertura_sanitaria(muns, ref, pop, auto, conf, {"plano": 1.0, "plano_antigo": 0.6})
        return c["XX"]["cobertura"] == 40.0 and c["XX"]["planos_lidos"] == 2 and c["XX"]["planos_sem_leitura"] == 1 and c["XX"]["pop_coberta"] == 160
    def t16():  # v0.5: denominador 27, UF sem documento lido entra com crédito 0, estatuto soma 27
        ufs = {u: {"prontidao": 30.0, "estatuto": "plano_localizado"} for u in UFS}
        for u in ("AC", "AP"): ufs[u] = {"prontidao": None, "estatuto": "nao_verificado"}
        for u in UFS: ufs[u]["prontidao_nacional"] = credito_nacional(ufs[u]["prontidao"], 20.0 if u == "AC" else 0.0)
        r = resumo_nacional(ufs)
        return (credito_nacional(None) == 0.0 and credito_nacional(41.2) == 41.2 and credito_nacional(None, 20.0) == 10.0
                and r["indice_nacional"] == round((25 * 30.0 + 10.0) / 27, 1) and sum(r["por_estatuto"].values()) == 27)
    def t17():  # v0.5: UF fora da conta é erro, não média menor
        ufs = {u: {"estatuto": "plano_localizado", "prontidao_nacional": 30.0} for u in UFS if u != "TO"}
        try: resumo_nacional(ufs)
        except KeyError: return True
        return False
    def t18(): return (estatuto_do_plano("NAO_VERIFICADO", None) == "nao_verificado" and estatuto_do_plano("LAC", 0.0) == "plano_nao_localizado"
                       and estatuto_do_plano("NOVO", None) == "plano_nao_localizado" and estatuto_do_plano("VIG", 30.0) == "plano_localizado")
    pop = {u: 10 for u in UFS}
    todas = {"federal": {"consultado_em": "12/10/2026"}, "estadual": {u: {"consultado_em": "15/10/2026"} for u in UFS}}
    def t12():
        r = resposta_sanitaria(None, {}, pop); return r["situacao"] == "nao_coletado" and r["indice"] is None and r["emergencias"] is None
    def t13():
        r = resposta_sanitaria([], todas, pop); return r["situacao"] == "verificado" and r["indice"] == 0.0 and r["emergencias"] == 0
    def t14():
        r = resposta_sanitaria([], {"federal": todas["federal"], "estadual": {"PB": {"consultado_em": "15/10/2026"}}}, pop)
        return r["indice"] is None and r["emergencias"] is None and "MS" in r["faltam"][0] and "PB" not in r["lacunas_estaduais"]
    def t15():
        r = resposta_sanitaria([{"uf": "BR", "tipo": "espin"}], {"federal": todas["federal"]}, pop)
        return r["indice"] == 100.0 and r["situacao"] == "verificado" and len(r["ufs"]) == 27
    return rodar_autoteste({"temporada pelo título": t1, "temporada pela data": t2, "prontidão: metade instrumento, metade cobertura": t3,
                            "prontidão: cobertura ausente vale 0; LAC só leva a cobertura": t4, "não verificado não recebe número": t5,
                            "faixas nos limites": t6, "negativo: status inválido não pontua": t7,
                            "v0.7: tempo à parte, só ato do ciclo com dia": t8, "plano decenal não pontua": t9,
                            "v0.7: instrumento + cobertura, metade cada, nada datado na nota": t10,
                            "v0.8 declarada: um terço cada, coordenação só com as duas funções": t19, "coordenação da UF: peso zero, fora da nota": t20,
                            "v0.5: média das 27, crédito sem documento, estatutos somam 27": t16,
                            "v0.5: UF fora do denominador é erro": t17, "v0.5: estatuto do plano": t18, "v0.3: cobertura sanitária por população": t11,
                            "resposta: campo ausente é não coletado, nunca 0": t12, "resposta: lista vazia com as duas buscas é 0 verificado": t13,
                            "resposta: metade estadual sem busca deixa o índice nulo e nomeada": t14, "resposta: ESPIN cobre 100% da população": t15})


if __name__ == "__main__":
    sys.exit(autoteste() if "--autoteste" in sys.argv else gerar())
