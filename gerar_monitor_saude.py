#!/usr/bin/env python3
"""
gerar_monitor_saude.py — Monitor Saúde v0.1 (05/09/2026)
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
VERSAO = "0.2"


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


def gerar() -> int:
    su = ler("saude_uf.json", {}) or {}; ss = ler("saude_sinais.json", {}) or {}; sr = ler("sinais_risco.json", {}) or {}
    ufs = {}
    for uf in UFS:
        u = (su.get("uf") or {}).get(uf, {}); st = u.get("status", "NAO_VERIFICADO")
        camada = u.get("camada") or "ciclo"   # 'ciclo' (contingência/preparação) | 'adaptacao' (plano decenal → estrutura)
        p, pi, pa = prontidao(st, u.get("doc") or "", u.get("data") or "", camada)
        deng = (ss.get("dengue_capitais") or {}).get(uf) or {}
        sig = ((sr.get("uf") or {}).get(uf) or {})
        avisos = (sig.get("avisos_inmet") or {}); lista = avisos.get("lista") or avisos.get("avisos") or []
        ufs[uf] = {
            "verificado": st != "NAO_VERIFICADO", "prontidao": p, "faixa": faixa(p),
            "instrumento": {"status": st, "pontos": pi, "doc": u.get("doc"), "data": u.get("data"), "orgao": u.get("orgao"), "url": u.get("url"),
                            "temporada": temporada_da_edicao(u.get("doc") or "", u.get("data") or "") if st in PONTOS_STATUS else None},
            "antecipacao": {"pontos": pa, "boletim_1": BOLETIM_1, "janela_critica_inicio": JANELA_CRITICA_INICIO},
            "camada": camada,
            "risco_atual": {"dengue_capital_nivel": deng.get("nivel"), "dengue_capital": deng.get("municipio"), "dengue_se": deng.get("se"),
                            "avisos_calor": sum(1 for x in lista if re.search(r"calor", json.dumps(x, ensure_ascii=False), re.I)),
                            "focos_24h": ((sig.get("fogo") or {}).get("focos_24h"))},
            "risco_projetado": u.get("risco_sanitario_projetado") or [],
        }
    verificadas = [uf for uf in UFS if ufs[uf]["verificado"]]
    por_faixa = {}
    for uf in verificadas: por_faixa[ufs[uf]["faixa"]] = por_faixa.get(ufs[uf]["faixa"], 0) + 1
    saida = {
        "_governanca": ("MARÉ · Saúde v0.2 (14/09/2026; v0.1 em 05/09/2026): prontidão sanitária estadual para o ciclo, separada do MARÉ "
                        "(peso zero no índice; nunca lida por recalcular_mare.py). Um componente pontuado (instrumento "
                        "operacional × antecipação, pesos iguais) e duas leituras de contexto (risco observado e projetado). "
                        "UF não verificada não recebe número. Sem número nacional enquanto houver UF não verificada. Metodologia §31."),
        "versao": VERSAO, "gerado_em": _hoje().strftime("%d/%m/%Y"), "corte": su.get("corte"),
        "metodo": {"pesos": {"instrumento": PESO_INSTRUMENTO, "antecipacao": 1 - PESO_INSTRUMENTO}, "escada": PONTOS_STATUS,
                   "antecipacao": {"NOVO/READ antes de 29/06/2026": 100, "NOVO/READ até 29/07/2026": 60, "NOVO/READ até 30/09/2026": 50,
                                   "NOVO/READ de 01/10/2026 em diante ou sem data": 30, "VIG edição 2025/2026 (recorrente que cobre o risco)": 40,
                                   "VIG edição anterior": 20, "ELAB": 20, "sem instrumento": 0,
                                   "plano de adaptação decenal (AdaptaSUS-UF)": "não pontua — estrutura"},
                   "ancoras": {"boletim_1": BOLETIM_1, "boletim_1_mais_30": BOLETIM_1_MAIS_30, "janela_critica_ms": JANELA_CRITICA_INICIO},
                   "faixas": {"estágio inicial": "0–25", "em construção": "25–50", "consolidado": "50–70", "avançado": "70–100"}},
        "resumo": {"verificadas": len(verificadas), "nao_verificadas": 27 - len(verificadas), "por_faixa": por_faixa,
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
        return prontidao("TALVEZ", "x", "2026") == (None, None, None)
    return rodar_autoteste({"temporada pelo título": t1, "temporada pela data": t2, "prontidão: VIG 2025/26 = 42,5; NOVO 27/08 = 75": t3,
                            "prontidão: edição antiga = 32,5; LAC = 0": t4, "não verificado não recebe número": t5,
                            "faixas nos limites": t6, "negativo: status inválido não pontua": t7,
                            "v0.2: âncoras do índice principal": t8, "v0.2: plano decenal não pontua": t9})


if __name__ == "__main__":
    sys.exit(autoteste() if "--autoteste" in sys.argv else gerar())
