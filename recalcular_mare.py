#!/usr/bin/env python3
"""Cálculo canônico do índice MARÉ v3.0 — Monitor El Niño Brasil.

v3.0 (04/09/2026, decisão editorial; Metodologia §30): o componente estadual passa a ser
a média de DOIS sub-elementos com peso igual — ESTRUTURA DE COORDENAÇÃO (comitê, gabinete,
sala de situação, COE criados ou ativados para o ciclo) e INSTRUMENTO OPERACIONAL (plano,
protocolo, decreto preventivo). Cada um usa a escada ESTADO_SCORE. A cobertura municipal ganha
a categoria `estrutura` (comitê/gabinete municipal nomeado para o ciclo, ou COMPDEC ativada por
ato datado — nunca a COMPDEC genérica), crédito 0,45 = paridade com plano_elaboracao.

Reproduz integralmente os 27 valores publicados em data/indice.json a partir de
data/municipios.json, data/percentual_uf.json, data/municipios_ibge_referencia.json
e data/populacao_censo2022.json (Censo 2022 validado por atualizar_populacao.py).

Fórmula (Metodologia §5, §5.2.1 e §12.4.2-3; reestruturação populacional 27/08/2026;
régua de antecipação formalizada — teste do objeto — em 27/08/2026, sem mudança numérica):
  • 3 componentes, pesos iguais (1/3): instrumento estadual, cobertura populacional, antecipação.
  • Cobertura populacional = Σ(população_município × crédito_da_categoria) ÷ população_UF × 100 (teto 100)
      crédito (CRED_POP, escala do antigo componente capital generalizada):
        plano 1,0 · plano_antigo 0,6 · plano_elaboracao 0,45 · coberto_estadual 0,3 · nao_localizado 0
        decreto: 0 (Correção B) · nao_el_nino: 0 — desvio DELIBERADO do §12.4.2 (que herdaria 0,1):
        o vocabulário OBRIGATÓRIO manda "NUNCA conta como preparação p/ El Niño"; generalizar o 0,1
        da capital dava ao AP 2,6 pontos de cobertura por emergência sanitária (achado na simulação
        de 27/08/2026). Regra de hierarquia: vocabulário > escala derivada.
      agregado sem lista nominal (RO 38 planos): excedente × população municipal MEDIANA da UF × crédito
      camada declarada sem lista nominal (desconto de 50% sobre o crédito), mesmo estimador de mediana:
        excedente_declarado_plano × mediana × 0,5 + declarado_antigo × mediana × 0,3
      município pós-Censo (Boa Esperança do Norte/MT, instalado 2025): população 0 sob a safra
        censitária — seus habitantes estão contidos nos municípios-mãe; jamais imputar.
  • O status da capital permanece verificado e exibido EDITORIALMENTE (card de detalhe);
    aritmeticamente a capital vale sua fração populacional real, como qualquer município (§12.4.2).
  • Agregação: linear (manchete) + geométrica com piso 5 (tooltip).
  • Sensibilidade: Monte Carlo 10.000 × Dirichlet(1,1,1), semente 42; intervalo de posições p5–p95.

Uso:
  python recalcular_mare.py --check   # compara com data/indice.json; falha se divergir (padrão)
  python recalcular_mare.py --write   # regrava data/indice.json
"""
import json, re, pathlib, sys
import numpy as np

RAIZ = pathlib.Path(__file__).parent
PESO_DOC = {"plano": 1.0, "plano_antigo": 0.7}  # Correção B (26/08/2026): "decreto" removido —
# não é purga pontual de dado, é regra estrutural. Sem isto, um decreto novo achado pela busca
# automática de segunda-feira (ou por contribuição de leitor) voltaria a pontuar 0,4 por registro,
# desfazendo a Correção B sozinho a cada atualização. `k in PESO_DOC` nas linhas abaixo já basta
# para excluir decreto de w, doc_n e do excedente agregado — nenhuma outra mudança necessária.
ESTADO_SCORE = {"NOVO": 100, "READ": 65, "VIG": 45, "ELAB": 35, "LAC": 0}
# Crédito populacional por categoria (v2.2). Origem: escala do componente capital
# da v2.1 (÷100), generalizada pelo §12.4.2 — com o desvio documentado de
# nao_el_nino (0, não 0,1; ver docstring). decreto ausente por regra estrutural
# (Correção B): `CRED_POP.get(cat, 0.0)` já o exclui sem lista de exceções.
CRED_POP = {"plano": 1.0, "plano_antigo": 0.6, "plano_elaboracao": 0.45,
            # v3.0: estrutura de coordenação nomeada para o ciclo — compromisso formal sem instrumento
            # operacional; paridade declarada com plano_elaboracao (§30). O crédito é o MAIOR, nunca a soma.
            "estrutura": 0.45,
            "coberto_estadual": 0.3, "nao_el_nino": 0.0, "nao_localizado": 0.0,
            # v2.2.4 (§2.1): ausência de verificação ≠ ausência de documento; mesmo crédito 0.0
            "nao_verificado": 0.0}
AGREGADOS = {"RO": (38, "plano")}  # Correção B (26/08/2026): agregados tipo decreto (PB, RN) excluídos do índice — atos de resposta, nunca ex-ante
CAPITAIS = {"Rio Branco":"AC","Maceió":"AL","Manaus":"AM","Macapá":"AP","Salvador":"BA","Fortaleza":"CE",
 "Brasília":"DF","Vitória":"ES","Goiânia":"GO","São Luís":"MA","Cuiabá":"MT","Campo Grande":"MS",
 "Belo Horizonte":"MG","Belém":"PA","João Pessoa":"PB","Curitiba":"PR","Recife":"PE","Teresina":"PI",
 "Rio de Janeiro":"RJ","Natal":"RN","Porto Alegre":"RS","Porto Velho":"RO","Boa Vista":"RR",
 "Florianópolis":"SC","São Paulo":"SP","Aracaju":"SE","Palmas":"TO"}

# (status do INSTRUMENTO OPERACIONAL, antecipação, confiança) — insumos de julgamento da verificação,
# datados no banco de registros; régua de antecipação na Metodologia §5.2.
# v3.0: o status aqui é o do instrumento operacional (plano/protocolo/decreto preventivo); a
# estrutura de coordenação está em ESTRUTURA, abaixo. Componente estadual = média dos dois.
ESTADOS = {
 "AC":("ELAB",100,"Alta"),  "AL":("ELAB",30,"Média"),   "AM":("NOVO",100,"Média"),
 "AP":("VIG",40,"Média"),    "BA":("ELAB",20,"Média"), "CE":("VIG",40,"Média"),
 "DF":("VIG",40,"Média"),   "ES":("VIG",30,"Baixa"),  "GO":("NOVO",30,"Média"),
 "MA":("READ",100,"Média"),"MG":("VIG",20,"Baixa"),  "MS":("READ",100,"Média"),
 "MT":("NOVO",100,"Média"),"PA":("READ",30,"Alta"),   "PB":("LAC",10,"Alta"),
 "PE":("ELAB",20,"Média"), "PI":("VIG",40,"Média"),  "PR":("READ",100,"Alta"),
 "RJ":("VIG",30,"Baixa"),  "RN":("LAC",10,"Alta"),   "RO":("READ",40,"Alta"),
 "RR":("VIG",40,"Alta"),   "RS":("READ",100,"Alta"), "SC":("NOVO",100,"Alta"),
 "SE":("NOVO",30,"Média"),   "SP":("VIG",40,"Baixa"),  "TO":("READ",40,"Média"),
}

# v3.0 — ESTRUTURA DE COORDENAÇÃO por UF (§30), julgada pela FUNÇÃO do ato, não pelo nome:
#   NOVO = órgão/instância criado para o ciclo por ato do Executivo (comitê, gabinete, sala de situação),
#          OU plano do ciclo que institui níveis de mobilização e responsáveis (SC);
#   READ = estrutura permanente ativada/re-instituída/designada para o ciclo por ato datado;
#   VIG  = ativação recorrente anual (plano de verão/operação sazonal que mobiliza o sistema todo ano);
#   LAC  = nenhum ato do ciclo toca a estrutura (estrutura permanente sem ato = 0, como a COMPDEC genérica).
# Fontes e datas de cada julgamento: data/estados.json (campo estrutura) e log_buscas (04/09/2026).
ESTRUTURA = {
 "AC":"READ","AL":"NOVO","AM":"READ","AP":"LAC","BA":"LAC","CE":"LAC","DF":"READ","ES":"VIG","GO":"NOVO",
 "MA":"VIG","MG":"VIG","MS":"READ","MT":"NOVO","PA":"READ","PB":"LAC","PE":"LAC","PI":"LAC","PR":"READ",
 "RJ":"VIG","RN":"LAC","RO":"VIG","RR":"VIG","RS":"READ","SC":"NOVO","SE":"NOVO","SP":"VIG","TO":"VIG",
}
PESO_ESTRUTURA = 0.5   # v3.0: peso igual entre estrutura e instrumento operacional (padrão da casa; sensibilidade 30/70–50/50 sem troca de faixa, §30)


def score_estado(uf: str) -> float:
    """Componente estadual v3.0 = média ponderada (PESO_ESTRUTURA) de estrutura e instrumento operacional."""
    st = ESTADOS[uf][0]
    return PESO_ESTRUTURA * ESTADO_SCORE[ESTRUTURA[uf]] + (1 - PESO_ESTRUTURA) * ESTADO_SCORE[st]


def excedente_agregado(uf, c):
    """Excesso do agregado estadual sobre o que já está contado individualmente
    (mesma regra usada nos dois lugares: score de cobertura E percentual_uf —
    fonte única, para as duas contagens nunca mais poderem divergir). 'c' é a
    contagem por categoria de um único UF. Devolve (tipo_do_agregado, excedente)
    ou (None, 0) se a UF não tem agregado.

    Correção B (26/08/2026, achada pelo teste de estresse formal da Metodologia
    §12.1 — "27 UFs decretando simultaneamente devem deslocar o MARÉ em exatamente
    zero décimos"): a subtração cruzada de 'decreto' contra um agregado tipo
    'plano' (caso de RO) fazia sentido ANTES da Correção B, quando evitava dupla
    contagem de um município com decreto individual E aggregate plano. Como
    decreto não pontua mais nada, esse termo cruzado só reduzia o crédito do
    agregado sem motivo — um decreto novo em QUALQUER município de RO diminuía
    o score de RO, mesmo sem o decreto em si valer ponto algum. Removido.
    """
    if uf not in AGREGADOS:
        return None, 0
    tot_ag, tipo = AGREGADOS[uf]
    ja = c.get(tipo, 0)
    return tipo, max(tot_ag - ja, 0)


def derivar_percentual_uf(cnt, totais, pct_existente):
    """Deriva total/com_ato/n_plano/n_decreto/pct de cada UF a partir da MESMA
    contagem por categoria ('cnt') usada no cálculo do score de cobertura —
    incluindo o mesmo desconto de sobreposição dos agregados estaduais, para
    que as duas métricas nunca possam divergir uma da outra. Preserva campos de
    levantamento externo (declarado_plano, declarado_antigo, fonte_declarada),
    que vêm de auditorias de TCEs/órgãos estaduais e não são deriváveis daqui.
    Fecha a lacuna que exigia sincronizar percentual_uf.json à mão a cada
    mudança em municipios.json (achada e corrigida em 26/08/2026)."""
    novo = {}
    for uf, total in totais.items():
        c = cnt.get(uf, {})
        n_plano = c.get("plano", 0) + c.get("plano_antigo", 0)
        n_decreto = c.get("decreto", 0)
        tipo_agr, excedente = excedente_agregado(uf, c)
        if tipo_agr == "plano":
            n_plano += excedente
        elif tipo_agr == "decreto":
            n_decreto += excedente
        com_ato = n_plano + n_decreto
        entrada = {"total": total, "com_ato": com_ato,
                   "pct": round(100 * com_ato / total, 2) if total else 0.0,
                   "n_plano": n_plano, "n_decreto": n_decreto}
        antiga = pct_existente.get(uf, {})
        for chave in ("declarado_plano", "declarado_antigo", "fonte_declarada"):
            if chave in antiga:
                entrada[chave] = antiga[chave]
        novo[uf] = entrada
    return novo


def _declarado_nacional_uf():
    """Nº de municípios por UF que DECLARAM plano de contingência (MUNIC 'sim' ou ICM
    variável 8 'sim') em data/declarado_nacional.json. Vazio se o arquivo não existe."""
    p = RAIZ / "data" / "declarado_nacional.json"
    if not p.exists(): return {}
    d = json.load(open(p, encoding="utf-8")).get("municipios", {})
    ref = json.load(open(RAIZ / "data" / "municipios_ibge_referencia.json", encoding="utf-8"))
    uf_por = {str(r["codigo_ibge"]).zfill(7): r["uf"] for r in ref}
    n = {}
    for cod, v in d.items():
        if v.get("munic_plano_contingencia") == "sim" or v.get("icm_var8_plano_contingencia") == "sim":
            uf = uf_por.get(cod)
            if uf: n[uf] = n.get(uf, 0) + 1
    return n

def calcular(simular_declarado_nacional: bool = False):
    """Motor do índice: lê data/*.json, calcula os três componentes por estado, agrega com elemento geométrico e piso, e devolve o dicionário completo (270 campos) que vira data/indice.json."""
    import statistics
    tab = json.load(open(RAIZ / "data" / "municipios.json", encoding="utf-8"))
    pct_arquivo = json.load(open(RAIZ / "data" / "percentual_uf.json", encoding="utf-8"))
    ref = json.load(open(RAIZ / "data" / "municipios_ibge_referencia.json", encoding="utf-8"))
    pop = json.load(open(RAIZ / "data" / "populacao_censo2022.json", encoding="utf-8"))
    totais, pop_uf, pops_uf, cod_por = {}, {}, {}, {}
    for m in ref:
        totais[m["uf"]] = totais.get(m["uf"], 0) + 1
        p = pop.get(f"{m['codigo_ibge']:07d}", 0)  # 0 apenas p/ município pós-Censo (docstring)
        pop_uf[m["uf"]] = pop_uf.get(m["uf"], 0) + p
        if p:
            pops_uf.setdefault(m["uf"], []).append(p)
        cod_por[(m["nome"], m["uf"])] = f"{m['codigo_ibge']:07d}"
    mediana_uf = {u: statistics.median(v) for u, v in pops_uf.items()}

    cnt, cap_cat, wpop = {}, {}, {}
    for r in tab:
        cnt.setdefault(r["uf"], {}).setdefault(r["categoria"], 0)
        cnt[r["uf"]][r["categoria"]] += 1
        if r["nome"] in CAPITAIS and CAPITAIS[r["nome"]] == r["uf"]:
            cap_cat[r["uf"]] = r["categoria"]
        chave = (r["nome"], r["uf"])
        if chave not in cod_por:
            raise SystemExit(f"✗ registro sem casamento na malha IBGE: {chave} — "
                             "grafia deve ser a oficial (convenção do banco)")
        wpop[r["uf"]] = wpop.get(r["uf"], 0.0) + pop.get(cod_por[chave], 0) * CRED_POP.get(r["categoria"], 0.0)

    pct = derivar_percentual_uf(cnt, totais, pct_arquivo)

    ufs = sorted(ESTADOS)
    comp = []
    for uf in ufs:
        c = cnt.get(uf, {})
        w = wpop.get(uf, 0.0)
        tipo_agr, excedente = excedente_agregado(uf, c)
        if tipo_agr:
            w += excedente * mediana_uf[uf] * CRED_POP[tipo_agr]
        dp = pct[uf].get("declarado_plano", 0) or 0
        da = pct[uf].get("declarado_antigo", 0) or 0
        if simular_declarado_nacional:
            # C5/§3.9 (regra declarada em 02/09/2026, vigência 26/10/2026): camada declarada
            # nacional (MUNIC/ICM) entra com o MESMO desconto de 50%. Conservador: não soma
            # à declaração de tribunal de contas — usa o maior dos dois contadores.
            dp = max(dp, _declarado_nacional_uf().get(uf, 0))
        doc_n = sum(v for k, v in c.items() if k in PESO_DOC)
        if dp: w += max(dp - doc_n, 0) * mediana_uf[uf] * (CRED_POP["plano"] * 0.5)
        if da: w += da * mediana_uf[uf] * (CRED_POP["plano_antigo"] * 0.5)
        cobertura = min(100.0, 100.0 * w / pop_uf[uf])
        st, ant, conf = ESTADOS[uf]
        comp.append([score_estado(uf), round(cobertura, 1), ant])

    X = np.array(comp, float)
    lin = X.mean(axis=1)
    geo = np.exp(np.log(np.maximum(X, 5.0)).mean(axis=1))
    rng = np.random.default_rng(42)
    W = rng.dirichlet(np.ones(3), size=10000)
    S = X @ W.T
    order = (-S).argsort(axis=0)
    ranks = np.empty_like(order)
    for j in range(S.shape[1]):
        ranks[order[:, j], j] = np.arange(1, len(ufs) + 1)

    saida, robustez = {}, {}
    for i, uf in enumerate(ufs):
        st, ant, conf = ESTADOS[uf]
        saida[uf] = {
            "estado": round(float(X[i, 0]), 1), "cobertura_pop": round(float(X[i, 1]), 1),
            "antecipacao": int(ant),
            "total": round(float(lin[i]), 1), "total_geo": round(float(geo[i]), 1),
            "confianca": conf, "status_estadual": st,
            # v3.0: os dois sub-elementos do componente estadual, sempre visíveis
            "estrutura_status": ESTRUTURA[uf], "estado_estrutura": ESTADO_SCORE[ESTRUTURA[uf]],
            "operacional_status": st, "estado_operacional": ESTADO_SCORE[st],
            "metodo": "v3.0 — 3 componentes, pesos iguais (1/3): instrumento estadual = média (1/2, 1/2) de ESTRUTURA DE COORDENAÇÃO e INSTRUMENTO OPERACIONAL (Metodologia §30, decisão de 04/09/2026), cobertura populacional (Censo 2022; crédito por categoria, inclusive `estrutura` 0,45; agregados e declarada via mediana; §5 e §12.4.2-3), antecipação (régua e teste do objeto: §5.2.1); linear + geométrico piso 5. Sem ranking ordinal público (§13); Monte Carlo 10k Dirichlet(1,1,1) seed 42 em data/robustez_mc.json.",
        }
        # Decisão de 29/08/2026 (Metodologia §13): o rank ordinal deixa de ser
        # produto público por UF — a resolução do instrumento não sustenta
        # comparação ordinal fina (12 pares de UFs a <2 pontos; amplitude
        # mediana p5–p95 de 7 posições). O Monte Carlo permanece integralmente
        # computado e selado AQUI, como evidência de robustez, com o intervalo
        # sempre publicado junto do rank mediano (recomendação da auditoria de
        # 29/08/2026, §6) — nunca o ordinal isolado.
        robustez[uf] = {
            "rank_mediano": int(np.median(ranks[i])),
            "rank_p5": int(np.percentile(ranks[i], 5)),
            "rank_p95": int(np.percentile(ranks[i], 95)),
        }
        robustez[uf]["amplitude"] = robustez[uf]["rank_p95"] - robustez[uf]["rank_p5"]
    robustez["_parametros"] = {"metodo": "Monte Carlo 10.000 sorteios de pesos Dirichlet(1,1,1), semente 42",
                               "uso": "evidência de robustez (anexo metodológico); não é produto público por UF",
                               "decisao": "Metodologia §13, 29/08/2026"}
    return saida, float(lin.mean()), pct, robustez

def _recomputar_verificacao_em_memoria():
    """v2.2.4 (§3.3): data/verificacao_municipal.json é ARTEFATO DERIVADO de
    municipios.json + log_buscas.json + municipios_ibge_referencia.json —
    regravado por quem regrava a origem (lição §10 da transferência: 'artefato
    derivado precisa ser regravado por quem regrava a origem'). O nível de
    verificação só sobe com log estruturado; nada é imputado."""
    import re as _re
    PONT = {"plano","plano_antigo","plano_elaboracao","estrutura","coberto_estadual","decreto","nao_el_nino"}
    with open(RAIZ / "data" / "municipios.json", encoding="utf-8") as f: mun = json.load(f)
    with open(RAIZ / "data" / "log_buscas.json", encoding="utf-8") as f: lg = json.load(f)
    with open(RAIZ / "data" / "municipios_ibge_referencia.json", encoding="utf-8") as f: ref = json.load(f)
    completos = set()
    for e in lg.get("execucoes", []):
        if e.get("nivel") == "municipal_completo" and str(e.get("decisao","")).strip().lower().startswith("nada localizado") and e.get("municipio") and e.get("uf"):
            completos.add((e["municipio"], e["uf"]))
    niveis_log = {}
    for e in lg.get("execucoes", []):
        if e.get("municipio") and e.get("uf") and e.get("nivel") in ("nacional","estadual","municipal_completo"):
            ordem = {"nacional":1,"estadual":2,"municipal_completo":3}
            ch=(e["municipio"],e["uf"])
            if ordem[e["nivel"]] > ordem.get(niveis_log.get(ch,""),0): niveis_log[ch]=e["nivel"]
    por = {(m["nome"], m["uf"]): m for m in mun}
    # v2.2.4 (PR-C): livro de fontes consultadas dos coletores (nível, datas, fatos binários)
    _lp = RAIZ / "data" / "fontes_consultadas.json"
    livro = (json.load(open(_lp, encoding="utf-8")).get("municipios", {}) if _lp.exists() else {})
    ordem = {"nao_verificado": 0, "nacional": 1, "estadual": 2, "municipal_completo": 3}
    out = []
    for r in ref:
        ch = (r["nome"], r["uf"]); reg = por.get(ch)
        cod7 = str(r["codigo_ibge"]).zfill(7)
        lv = livro.get(cod7, {})
        n_log = niveis_log.get(ch, "nao_verificado"); n_livro = lv.get("nivel_verificacao", "nao_verificado")
        # "municipal_completo" só pelo log (bateria inteira logada por município), nunca pelo livro
        if n_livro == "municipal_completo": n_livro = "estadual"
        nivel = n_log if ordem[n_log] >= ordem[n_livro] else n_livro
        out.append({"ibge": str(r["codigo_ibge"]), "nome": r["nome"], "uf": r["uf"],
            "nivel_verificacao": nivel,
            "ultima_verificacao": lv.get("ultima_verificacao"),
            "fontes_consultadas": sorted({f["fonte"] for f in lv.get("fontes", [])}),
            "decreto_reconhecido": lv.get("decreto_reconhecido"), "decreto_homologado": lv.get("decreto_homologado"),
            "plano_declarado_munic": lv.get("plano_declarado_munic"), "plano_declarado_icm": lv.get("plano_declarado_icm"),
            "plano_localizado": (reg["categoria"] if reg and reg["categoria"] in PONT else None)})
    return out

def _resumo_verificacao(out):
    """Resumo derivado para o site (data/verificacao_resumo.json): contagens por
    nível e por UF, mapa compacto ibge→nível apenas para níveis acima do padrão,
    nº de fontes suspensas pelo defeso na última rodada do log e tamanho da fila
    de citação incompleta. Fonte única: verificacao_municipal.json."""
    tot = {}
    por_uf = {}
    acima = {}
    for v in out:
        n = v["nivel_verificacao"]; tot[n] = tot.get(n, 0) + 1
        d_uf = por_uf.setdefault(v["uf"], {}); d_uf[n] = d_uf.get(n, 0) + 1
        if n != "nao_verificado": acima[v["ibge"]] = n
    try:
        lg = json.load(open(RAIZ / "data" / "log_buscas.json", encoding="utf-8"))
        datas = [e["data"] for e in lg.get("execucoes", []) if e.get("data")]
        ult = max(datas) if datas else None
        suspensas = sum(1 for e in lg.get("execucoes", []) if e.get("data") == ult and e.get("fonte_suspensa_defeso"))
    except Exception:
        ult, suspensas = None, 0
    try:
        fila = len(json.load(open(RAIZ / "data" / "citacao_incompleta.json", encoding="utf-8")).get("fila", []))
    except Exception:
        fila = None
    try:
        # 03/09/2026: o registro de LAI vive no repositório PRIVADO (nunca no site); aqui só
        # entra a lista de UFs cuja verificação estadual depende de resposta — sem contagens.
        _lp = RAIZ / "data" / "ufs_dependentes_de_lai.json"
        _lai = json.load(open(_lp, encoding="utf-8")) if _lp.exists() else {"ufs": []}
        lai = {"ufs_dependentes": sorted(_lai.get("ufs", []))}
        raise StopIteration
        _lai = json.load(open(RAIZ / "data" / "lai_pedidos.json", encoding="utf-8")).get("pedidos", [])
        lai = {"total": len(_lai), "a_enviar": sum(1 for p in _lai if p.get("status") == "a_enviar"),
               "enviados_sem_resposta": sum(1 for p in _lai if p.get("status") == "enviado" and not p.get("data_resposta")),
               "respondidos": sum(1 for p in _lai if p.get("data_resposta")),
               "ufs_dependentes": sorted({p["uf"] for p in _lai if p.get("tipo") == "defesa_civil" and not p.get("data_resposta") and p["uf"] != "BR"})}
    except StopIteration:
        pass
    except Exception:
        lai = None
    try:
        # 03/09/2026: progresso da varredura integral dos diários municipais (Querido Diário).
        # Consulta NÃO é verificação (§4.1.2): o número diz quantos municípios já foram consultados
        # nessa fonte, quantos tiveram menção e quantos não — nunca quantos "têm" ou "não têm" plano.
        _fc = json.load(open(RAIZ / "data" / "fontes_consultadas.json", encoding="utf-8")).get("municipios", {})
        _FQD = "Querido Diário (diário municipal)"
        _qd = {c: [f for f in m.get("fontes", []) if f.get("fonte") == _FQD] for c, m in _fc.items()}
        _qd = {c: f for c, f in _qd.items() if f}
        _datas = sorted({f["data"] for fs in _qd.values() for f in fs if f.get("data")})
        _com_mencao = sum(1 for fs in _qd.values() if any(not str(f.get("resultado", "")).startswith("sem edições") for f in fs))
        varredura = {"fonte": _FQD, "consultados": len(_qd), "total": len(out), "com_mencao": _com_mencao,
                     "sem_mencao": len(_qd) - _com_mencao, "desde": (_datas[0] if _datas else None), "ultima": (_datas[-1] if _datas else None)}
    except Exception:
        varredura = None
    resumo = {"gerado_de": "verificacao_municipal.json", "total_municipios": len(out), "lai": lai,
              "totais_por_nivel": tot, "por_uf": por_uf, "niveis_acima_do_padrao": acima,
              "ultima_rodada_log": ult, "fontes_suspensas_defeso_ultima_rodada": suspensas,
              "fila_citacao_incompleta": fila, "varredura_diarios": varredura}
    with open(RAIZ / "data" / "verificacao_resumo.json", "w", encoding="utf-8") as f:
        json.dump(resumo, f, ensure_ascii=False, indent=1); f.write("\n")
    return resumo

def regravar_verificacao_municipal():
    out = _recomputar_verificacao_em_memoria()
    with open(RAIZ / "data" / "verificacao_municipal.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1); f.write("\n")
    _resumo_verificacao(out)
    return out

def main():
    """Interface de linha de comando: sem flag, recalcula e grava; com --check, recalcula em memória e compara campo a campo contra o data/indice.json publicado (portão 2), sem gravar nada."""
    modo = sys.argv[1] if len(sys.argv) > 1 else "--check"
    if modo == "--simular-declarado-nacional":
        novo_b, ma, _, _ = calcular(); novo_s, ms, _, _ = calcular(simular_declarado_nacional=True)
        linhas = {}
        for uf in sorted(k for k in novo_b if len(k) == 2):
            a_, b_ = novo_b[uf]["total"], novo_s[uf]["total"]
            linhas[uf] = {"antes": a_, "depois": b_, "delta": round(b_ - a_, 1),
                          "declarados_nacional": _declarado_nacional_uf().get(uf, 0)}
        json.dump({"_governanca": "SIMULAÇÃO da camada declarada nacional (C5, §3.9). Regra declarada em "
                                  "02/09/2026 com vigência em 26/10/2026; nada disto altera data/indice.json "
                                  "antes dessa data. Anexo público da METODOLOGIA (§26).",
                   "gerado_em": __import__("datetime").date.today().isoformat(),
                   "media_nacional_antes": round(ma, 1), "media_nacional_depois": round(ms, 1),
                   "por_uf": linhas},
                  open(RAIZ / "data" / "simulacao_declarado_nacional.json", "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print(f"simulação gravada: média {ma:.1f} → {ms:.1f} (27 UFs em data/simulacao_declarado_nacional.json)")
        return 0
    novo, media, pct_derivado, robustez = calcular()
    alvo = RAIZ / "data" / "indice.json"
    alvo_pct = RAIZ / "data" / "percentual_uf.json"
    alvo_rob = RAIZ / "data" / "robustez_mc.json"
    if modo == "--write":
        json.dump(novo, open(alvo, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        json.dump(pct_derivado, open(alvo_pct, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        json.dump(robustez, open(alvo_rob, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"data/indice.json, data/percentual_uf.json e data/robustez_mc.json regravados · média nacional {media:.1f}")
        # 03/09/2026: o fallback estático do medidor do herói (index.html) é DERIVADO do índice
        _p = RAIZ / "index.html"; _h = _p.read_text(encoding="utf-8"); _m = f"{media:.1f}"; _mbr = _m.replace(".", ",")
        _h2 = re.sub(r'(id="gaugeNum">)[\d,]+(<)', rf"\g<1>{_mbr}\g<2>", _h, count=1)
        _h2 = re.sub(r'data-alvo="[\d.]+" style="--galvo:[\d.]+;"', f'data-alvo="{_m}" style="--galvo:{_m};"', _h2, count=1)
        _h2 = re.sub(r'aria-label="Barra de progresso: MARÉ nacional em [\d,]+ de 100"', f'aria-label="Barra de progresso: MARÉ nacional em {_mbr} de 100"', _h2, count=1)
        if _h2 != _h: _p.write_text(_h2, encoding="utf-8"); print(f"index.html: fallback do medidor regravado ({_mbr})")
        vm = regravar_verificacao_municipal()
        print(f"data/verificacao_municipal.json regravado (derivado) · {len(vm)} municípios")
        # Selos SVG são função pura do índice: quem regrava o índice regrava os selos
        # (31/08/2026 — sem isto, o portão selo×índice revertia toda mudança legítima
        # dentro do julgamento automático).
        import gerar_selos
        gerar_selos.gerar()
        print("selos/ regravados a partir do índice")
        print("(percentual_uf.json agora é DERIVADO de municipios.json a cada --write; campos")
        print(" declarado_plano/declarado_antigo/fonte_declarada de auditorias externas preservados.)")
        return 0
    # v2.2.4: paridade do artefato derivado verificacao_municipal.json
    import tempfile, copy
    vm_disco_path = RAIZ / "data" / "verificacao_municipal.json"
    if vm_disco_path.exists():
        vm_disco = json.load(open(vm_disco_path, encoding="utf-8"))
        vm_novo = _recomputar_verificacao_em_memoria()
        if vm_disco != vm_novo:
            print("✗ VERIFICACAO_MUNICIPAL NÃO REPRODUZIDA — derivado em disco diverge do recomputado (rode --write)")
            return 1
        # resumo também é derivado: conferir contra o recomputado (sem gravar)
        import io, contextlib
        res_path = RAIZ / "data" / "verificacao_resumo.json"
        if res_path.exists():
            res_disco = json.load(open(res_path, encoding="utf-8"))
            _tmp = res_path.read_bytes()
            _resumo_verificacao(vm_novo)          # regrava…
            res_novo = json.load(open(res_path, encoding="utf-8"))
            res_path.write_bytes(_tmp)            # …e restaura o disco (modo --check não grava)
            if res_disco != res_novo:
                print("✗ VERIFICACAO_RESUMO NÃO REPRODUZIDO — derivado em disco diverge do recomputado (rode --write)")
                return 1
        else:
            print("✗ data/verificacao_resumo.json ausente (rode --write)")
            return 1
    else:
        print("✗ data/verificacao_municipal.json ausente (rode --write)")
        return 1
    _h = (RAIZ / "index.html").read_text(encoding="utf-8")
    _mm = re.search(r'data-alvo="([\d.]+)"', _h); _mn = re.search(r'id="gaugeNum">([\d,]+)<', _h)
    if not _mm or abs(float(_mm.group(1)) - round(media, 1)) > 0.05 or not _mn or _mn.group(1) != f"{media:.1f}".replace(".", ","):
        print(f"✗ MEDIDOR DO HERÓI desatualizado no index.html (fallback ≠ média {media:.1f}; rode --write)"); return 1
    atual = json.load(open(alvo, encoding="utf-8"))
    campos = ["estado", "cobertura_pop", "antecipacao", "total", "total_geo",
              "confianca", "status_estadual"]
    rob_atual = json.load(open(alvo_rob, encoding="utf-8")) if alvo_rob.exists() else None
    if rob_atual != robustez:
        print("✗ ROBUSTEZ NÃO REPRODUZIDA — data/robustez_mc.json diverge do recomputado (rode --write)")
        return 1
    div = [(uf, k, atual[uf][k], novo[uf][k]) for uf in novo for k in campos
           if atual.get(uf, {}).get(k) != novo[uf][k]]
    if div:
        print(f"✗ ÍNDICE NÃO REPRODUZIDO — {len(div)} divergência(s):")
        for d in div[:12]:
            print(f"   {d[0]}.{d[1]}: publicado={d[2]} recomputado={d[3]}")
        return 1
    print(f"✓ MARÉ REPRODUZIDO — 27 estados × {len(campos)} campos idênticos (+ robustez_mc.json) · média nacional {media:.1f}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
