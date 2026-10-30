#!/usr/bin/env python3
"""
gerar_mortalidade_comparada.py — quadro "mortalidade registrada, lado a lado" (30/10/2026)
=========================================================================================
HANDOVER_MORTALIDADE_COMPARADA §1–§3. Gerador único de `data/saude_desfechos/mortalidade_comparada.json`,
lido pela MARÉ Saúde e pela consulta do município (dado do estado). Nada é coletado aqui: lê
`obitos.json` (Registro Civil, todas as causas) e `obitos_calor.json` (SIM).

Por UF e BR, para cada mês a partir de 2026-07:
  registrados  óbitos lavrados no mês (null = lacuna);   parcial  o mês ainda cresce;
  faixa_ref    {min, max} do mesmo mês em 2019 e 2022–2025 (2020 e 2021 ficam fora: covid-19);
  esperado     média desses cinco anos;
  excesso      {valor, min, max} = registrados − esperado; min/max = registrados − máximo/mínimo da
               referência. Mês parcial ou referência incompleta: sem número, com o motivo;
  obitos_x30   SIM, causa básica calor natural (X30). Enquanto o arquivo do SIM não traz o critério
               X30 (hoje T67, que mede zero por construção), vira lacuna "critério em correção";
  projecao_cil lacuna "aguarda a série da fonte" (licença com a editoria, §6).
Valor negativo fica como está. Zero é zero medido; ausência é null com motivo.

Escritor único; roda depois de `coletar_obitos_registro_civil.py` (PARA A A1: linha em
`config/escritores.json` e elo na corrente). Peso zero. O Monitor não atribui óbitos ao El Niño.
"""
import sys

from coletores_base import ler, gravar, rodar_autoteste

ARQ = "saude_desfechos/mortalidade_comparada.json"
METODO = "v1 (30/10/2026)"
A_PARTIR_DE = "2026-07"
ANOS_REF = (2019, 2022, 2023, 2024, 2025)
ANOS_FORA = (2020, 2021)
L_PARCIAL, L_REF = "mês incompleto", "referência incompleta (menos de cinco anos com registro)"
L_X30 = "critério em correção (a causa básica do calor natural é X30; a série anterior usava T67)"
L_CIL = "aguarda a série da fonte"


def comparar(reg: dict, parciais: set, mes: str) -> dict:
    """Linha do mês para uma UF: registrados, faixa_ref, esperado, excesso. Função pura."""
    v = reg.get(mes)
    ref = [reg.get(f"{a}-{mes[5:]}") for a in ANOS_REF]
    parcial = mes in parciais
    out = {"registrados": v, "parcial": parcial}
    if v is None:
        out["lacuna_registrados"] = "sem registro lido para o mês"
    if any(x is None for x in ref):
        out.update(faixa_ref=None, esperado=None, excesso=None, lacuna_excesso=L_REF)
        return out
    out["faixa_ref"] = {"min": min(ref), "max": max(ref)}
    out["esperado"] = round(sum(ref) / len(ref), 1)
    if v is None or parcial:
        out.update(excesso=None, lacuna_excesso=L_PARCIAL if parcial else out["lacuna_registrados"])
    else:
        out["excesso"] = {"valor": round(v - out["esperado"], 1), "min": v - max(ref), "max": v - min(ref)}
    return out


def x30(sim: dict, uf: str, mes: str):
    """(valor, parcial, lacuna) da causa básica X30; sem o critério no arquivo, lacuna. Função pura."""
    if not sim or "X30" not in str(sim.get("rotulo", "")):
        return None, None, L_X30
    v = (sim.get("serie") or {}).get(uf, {}).get(mes)
    if v is None:
        return None, None, "sem registro lido para o mês"
    return v, mes in set(sim.get("parcial") or []), None


def montar(obitos: dict, sim: dict) -> dict:
    serie = obitos["serie"]
    meses = sorted({m for s in serie.values() for m in s if m >= A_PARTIR_DE})
    parciais = set(obitos.get("parcial") or [])
    territorios = {}
    for uf, reg in sorted(serie.items()):
        linhas = {}
        for mes in meses:
            if mes not in reg:
                continue
            linha = comparar(reg, parciais, mes)
            v, p, lac = x30(sim, uf, mes)
            linha["obitos_x30"] = {"valor": v, "parcial": p} if lac is None else None
            if lac:
                linha["lacuna_x30"] = lac
            linha["projecao_cil"] = None
            linha["lacuna_projecao_cil"] = L_CIL
            linhas[mes] = linha
        territorios[uf] = linhas
    return {
        "esquema": 1, "desfecho": "mortalidade_comparada", "metodo_excesso": METODO,
        "a_partir_de": A_PARTIR_DE, "anos_referencia": list(ANOS_REF), "anos_fora_da_referencia": list(ANOS_FORA),
        "consultado_em": obitos.get("coletado_em"),
        "fontes": {
            "registrados": {"sistema": (obitos.get("fonte") or {}).get("sistema"), "url": (obitos.get("fonte") or {}).get("url"),
                            "arquivo": "data/saude_desfechos/obitos.json", "conta": "óbitos lavrados no mês, todas as causas"},
            "obitos_x30": {"sistema": "SIM, Ministério da Saúde (preliminar)", "arquivo": "data/saude_desfechos/obitos_calor.json",
                           "consultado_em": (sim or {}).get("coletado_em")},
            "projecao_cil": {"sistema": "Climate Impact Lab, El Niño Heat Mortality Tracker (modelo)", "estado": L_CIL}},
        "limitacoes": ["não ajusta crescimento nem envelhecimento da população", "o registro em cartório atrasa",
                       "o excesso conta óbitos de todas as causas", "cinco anos de referência"],
        "territorios": territorios}


def gerar() -> int:
    obitos = ler("saude_desfechos/obitos.json")
    if not obitos or not obitos.get("serie"):
        print("obitos.json ausente ou vazio; o arquivo anterior fica")
        return 0
    obj = montar(obitos, ler("saude_desfechos/obitos_calor.json"))
    if ler(ARQ) == obj:
        print("mortalidade_comparada: sem mudança; nada a regravar")
        return 0
    gravar(ARQ, obj, compacto=True)
    print(f"→ data/{ARQ}: {len(obj['territorios'])} territórios, {len(next(iter(obj['territorios'].values())))} mês(es).")
    return 0


def autoteste() -> int:
    ref = {f"{a}-08": v for a, v in zip(ANOS_REF, (100, 110, 120, 130, 140))}
    reg = {**ref, "2026-07": 90, "2026-08": 150, "2026-09": 80, "2020-08": 999}
    c = comparar(reg, {"2026-09"}, "2026-08")
    p = comparar(reg, {"2026-08"}, "2026-08")
    n = comparar({**ref, "2026-08": 50}, set(), "2026-08")
    sem = comparar({"2026-08": 5}, set(), "2026-08")
    o = {"serie": {"AC": {**reg}}, "coletado_em": "2026-10-29", "parcial": ["2026-09"]}
    m = montar(o, {"rotulo": "Óbitos por efeitos do calor e da luz (CID-10 T67)", "serie": {"AC": {"2026-08": 0}}})
    t = m["territorios"]["AC"]
    return rodar_autoteste({
        "esperado é a média dos cinco anos; 2020 e 2021 ficam fora": lambda: c["esperado"] == 120.0 and c["faixa_ref"] == {"min": 100, "max": 140},
        "excesso = registrados − esperado, intervalo contra máximo e mínimo": lambda: c["excesso"] == {"valor": 30.0, "min": 10, "max": 50},
        "mês parcial não tem excesso, com o motivo": lambda: p["excesso"] is None and p["lacuna_excesso"] == L_PARCIAL and p["parcial"] is True,
        "valor negativo fica negativo": lambda: n["excesso"]["valor"] == -70.0 and n["excesso"]["max"] == -50,
        "referência incompleta é lacuna, nunca zero": lambda: sem["excesso"] is None and sem["lacuna_excesso"] == L_REF and sem["esperado"] is None,
        "meses antes de julho de 2026 não entram": lambda: all(k >= A_PARTIR_DE for k in t) and "2026-07" in t,
        "SIM com critério T67 vira lacuna, não zero": lambda: t["2026-08"]["obitos_x30"] is None and t["2026-08"]["lacuna_x30"] == L_X30,
        "SIM com critério X30 entra com o valor e a marca de parcial":
            lambda: x30({"rotulo": "calor natural (CID-10 X30)", "serie": {"AC": {"2026-08": 7}}, "parcial": ["2026-08"]}, "AC", "2026-08") == (7, True, None),
        "projeção CIL é lacuna declarada": lambda: t["2026-08"]["projecao_cil"] is None and t["2026-08"]["lacuna_projecao_cil"] == L_CIL,
        "consultado_em vem da fonte, não do relógio (idempotência)": lambda: m["consultado_em"] == "2026-10-29",
    })


if __name__ == "__main__":
    sys.exit(autoteste() if "--autoteste" in sys.argv else gerar())
