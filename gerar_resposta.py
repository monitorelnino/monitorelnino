#!/usr/bin/env python3
"""
gerar_resposta.py — Contador de RESPOSTA (v3.1 §3, 06/09/2026)
================================================================
A outra metade do MARÉ (Medida de Antecipação e Resposta): o que foi DECRETADO depois.
Contagens, frações e datas — sem fórmula, sem faixa, sem peso, sem composto com o índice (C17).
Peso ZERO: nada aqui é lido por recalcular_mare.py (portão verificar_resposta.py).

Fontes: data/atos_resposta.json (decretos e reconhecimentos: DOU/SEDEC, DOE, diários municipais,
imprensa oficial) + data/verificacao_municipal.json (decreto_reconhecido, nível nacional via S2iD).
Ponderação: data/populacao_censo2022.json; universo por UF: verificacao_municipal.json.

Produz data/resposta/{municipios,por_uf,serie_semanal,quadrantes}.json.
Fatia "evento observado" (C16): até existir o adaptador municipal (Cemaden por município, INMET por
área, INPE por município, ANA), TODO decreto fica em `em_classificacao` — nunca imputado.
Frase C18 obrigatória em toda superfície: FRASE_C18.
  python gerar_resposta.py --autoteste
"""
import json, sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from coletores_base import ler, gravar, rodar_autoteste

RAIZ = Path(__file__).resolve().parent
UFS = ["AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT","PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO"]
INICIO_CICLO = date(2026, 6, 29)     # Boletim nº 1 do Painel El Niño
DEFESO = (date(2026, 7, 4), date(2026, 10, 25))
FRASE_C18 = ("Entre 04/07 e 25/10/2026 o decreto de emergência é a única porta de recurso federal e estadual "
             "que a lei deixa aberta (art. 73, VI, a).")


def data_br(v):
    try:
        return datetime.strptime(str(v).strip(), "%d/%m/%Y").date()
    except (ValueError, TypeError):
        return None


def semana_de(d: date) -> str:
    return (d - timedelta(days=d.weekday())).isoformat()


def tipo_do_evento(ev: dict) -> str:
    c = (ev.get("causa") or "").lower()
    if "reconhecimento" in c: return "reconhecimento_federal"
    if "calamidade" in c: return "ECP"
    return "SE"


def consolidar_municipios(eventos: list, verificacao: list) -> dict:
    """{ibge: {decreto, primeiro_decreto, tipos, reconhecido, decretado, evento_observado, fontes}} para os 5.571.
    Reconhecido = DOU/SEDEC (reconhecimento federal) ou decreto_reconhecido em verificacao_municipal. Função pura."""
    out = {}
    for r in verificacao:
        out[str(r["ibge"]).zfill(7)] = {"ibge": str(r["ibge"]).zfill(7), "nome": r.get("nome"), "uf": r.get("uf"), "decreto": False,
                                       "primeiro_decreto": None, "tipos": [], "reconhecido": bool(r.get("decreto_reconhecido")), "decretado": False,
                                       "evento_observado": "em_classificacao", "fontes": [], "n_eventos": 0}
    for ev in eventos:
        ib = str(ev.get("ibge") or "").zfill(7)
        m = out.get(ib)
        if not m:
            continue
        d = data_br(ev.get("data")); t = tipo_do_evento(ev)
        m["decreto"] = True; m["n_eventos"] += 1
        if t == "reconhecimento_federal": m["reconhecido"] = True
        else: m["decretado"] = True
        if t not in m["tipos"]: m["tipos"].append(t)
        if d and (m["primeiro_decreto"] is None or d < data_br(m["primeiro_decreto"])): m["primeiro_decreto"] = d.strftime("%d/%m/%Y")
        m["fontes"].append({"canal": ev.get("canal"), "fonte": ev.get("fonte"), "url": ev.get("url"), "data": ev.get("data"), "decreto": ev.get("decreto"), "hash": ev.get("hash_evidencia")})
    for m in out.values():
        if m["reconhecido"] and not m["decreto"]: m["decreto"] = True     # reconhecido via S2iD sem evento no arquivo de atos
    return out


def agregar_uf(municipios: dict, populacao: dict) -> dict:
    """Por UF: n, total, fração de municípios; população sob decreto e fração; primeiro decreto; fatias (C16) e tons."""
    por = {}
    for uf in UFS:
        ms = [m for m in municipios.values() if m["uf"] == uf]
        com = [m for m in ms if m["decreto"]]
        pop_uf = sum(float(populacao.get(m["ibge"], 0) or 0) for m in ms)
        pop_dec = sum(float(populacao.get(m["ibge"], 0) or 0) for m in com)
        datas = [data_br(m["primeiro_decreto"]) for m in com if m["primeiro_decreto"]]
        por[uf] = {"n_municipios": len(com), "total_municipios": len(ms), "fracao_municipios": round(len(com) / len(ms), 4) if ms else 0.0,
                   "pop_sob_decreto": int(pop_dec), "pop_uf": int(pop_uf), "fracao_populacao": round(pop_dec / pop_uf, 4) if pop_uf else 0.0,
                   "primeiro_decreto": min(datas).strftime("%d/%m/%Y") if datas else None,
                   "fatias": {"apos_evento": 0, "antes_com_previsao": 0, "em_classificacao": len(com)},
                   "tons": {"reconhecido": sum(1 for m in com if m["reconhecido"]), "decretado_sem_reconhecimento": sum(1 for m in com if m["decretado"] and not m["reconhecido"])}}
    return por


def serie_semanal(municipios: dict) -> list:
    """Municípios por semana do PRIMEIRO decreto, desde 29/06/2026 até hoje; flag do defeso por semana."""
    cont = defaultdict(int)
    for m in municipios.values():
        d = data_br(m["primeiro_decreto"]) if m["primeiro_decreto"] else None
        if d and d >= INICIO_CICLO: cont[semana_de(d)] += 1
    out = []; d = INICIO_CICLO - timedelta(days=INICIO_CICLO.weekday()); hoje = date.today(); acum = 0
    while d <= hoje:
        n = cont.get(d.isoformat(), 0); acum += n
        out.append({"semana": d.isoformat(), "municipios": n, "acumulado": acum, "defeso": DEFESO[0] <= d <= DEFESO[1]})
        d += timedelta(days=7)
    return out


def quadrantes(por_uf: dict, indice: dict) -> list:
    """27 pontos: antecipação (nota MARÉ) × resposta (fração de municípios); forma = evento observado (sem dado até o adaptador)."""
    return [{"uf": uf, "antecipacao": (indice.get(uf) or {}).get("total"), "resposta": por_uf[uf]["fracao_municipios"],
             "fracao_populacao": por_uf[uf]["fracao_populacao"], "evento_observado": "sem_dado"} for uf in UFS]


def gerar() -> int:
    atos = ler("atos_resposta.json", {"eventos": []}) or {"eventos": []}
    verificacao = ler("verificacao_municipal.json", []) or []
    pop = ler("populacao_censo2022.json", {}) or {}
    indice = ler("indice.json", {}) or {}
    mun = consolidar_municipios(atos["eventos"], verificacao)
    por = agregar_uf(mun, pop); serie = serie_semanal(mun); quad = quadrantes(por, indice)
    hoje = date.today().strftime("%d/%m/%Y")
    n_total = sum(v["n_municipios"] for v in por.values()); pop_total = sum(v["pop_uf"] for v in por.values()); pop_dec = sum(v["pop_sob_decreto"] for v in por.values())
    datas = [data_br(m["primeiro_decreto"]) for m in mun.values() if m["primeiro_decreto"] and data_br(m["primeiro_decreto"]) >= INICIO_CICLO]
    gov = ("Contador de RESPOSTA (v3.1 §3; Metodologia §32): contagens, frações e datas do que foi decretado depois. Sem fórmula, "
           "sem faixa, sem peso; nunca combinado com o índice (C17). Peso zero no MARÉ (portão verificar_resposta.py). "
           "Fatia 'evento observado' em_classificacao até o adaptador municipal existir (C16). " + FRASE_C18)
    (RAIZ / "data" / "resposta").mkdir(parents=True, exist_ok=True)
    gravar("resposta/municipios.json", {"_governanca": gov, "gerado_em": hoje, "frase_c18": FRASE_C18, "municipios": mun})
    gravar("resposta/por_uf.json", {"_governanca": gov, "gerado_em": hoje, "frase_c18": FRASE_C18, "inicio_ciclo": INICIO_CICLO.strftime("%d/%m/%Y"),
                                    "nacional": {"n_municipios": n_total, "total_municipios": len(mun), "fracao_municipios": round(n_total / len(mun), 4) if mun else 0,
                                                 "pop_sob_decreto": pop_dec, "pop_total": pop_total, "fracao_populacao": round(pop_dec / pop_total, 4) if pop_total else 0,
                                                 "primeiro_decreto": min(datas).strftime("%d/%m/%Y") if datas else None,
                                                 "reconhecidos": sum(v["tons"]["reconhecido"] for v in por.values()), "decretados_sem_reconhecimento": sum(v["tons"]["decretado_sem_reconhecimento"] for v in por.values())},
                                    "uf": por})
    gravar("resposta/municipios_decretados.json", {"_governanca": gov + " Arquivo reduzido para a página: só municípios sob decreto; ausência = 'não consta decreto reconhecido no ciclo' (S2iD completo; DOE/DOM parcial).", "gerado_em": hoje, "frase_c18": FRASE_C18, "municipios": {k: v for k, v in mun.items() if v["decreto"]}})
    gravar("resposta/serie_semanal.json", {"_governanca": gov, "gerado_em": hoje, "frase_c18": FRASE_C18, "defeso": [DEFESO[0].strftime("%d/%m/%Y"), DEFESO[1].strftime("%d/%m/%Y")], "semanas": serie})
    gravar("resposta/quadrantes.json", {"_governanca": gov + " Dispersão antecipação × resposta (C20): forma do ponto = evento observado (sem dado até o adaptador).", "gerado_em": hoje, "frase_c18": FRASE_C18, "pontos": quad})
    print(f"resposta: {n_total} municípios sob decreto ({100*n_total/len(mun):.1f}%) · {100*pop_dec/pop_total:.1f}% da população · primeiro decreto {min(datas).strftime('%d/%m/%Y') if datas else '—'}")
    return 0


def autoteste() -> int:
    V = [{"ibge": "1", "nome": "A", "uf": "RS", "decreto_reconhecido": None}, {"ibge": "2", "nome": "B", "uf": "RS", "decreto_reconhecido": True},
         {"ibge": "3", "nome": "C", "uf": "RS", "decreto_reconhecido": None}, {"ibge": "4", "nome": "D", "uf": "BA", "decreto_reconhecido": None}]
    E = [{"ibge": "1", "uf": "RS", "data": "10/07/2026", "causa": "situação de emergência", "canal": "DOM", "fonte": "x", "url": "u"},
         {"ibge": "1", "uf": "RS", "data": "20/07/2026", "causa": "reconhecimento federal", "canal": "DOU", "fonte": "y", "url": "u"},
         {"ibge": "9", "uf": "XX", "data": "01/07/2026", "causa": "situação de emergência", "canal": "DOM", "fonte": "z", "url": "u"}]
    P = {"0000001": 100, "0000002": 300, "0000003": 600, "0000004": 50}
    m = consolidar_municipios(E, V); por = agregar_uf(m, P)
    def t1(): return m["0000001"]["decreto"] and m["0000001"]["reconhecido"] and m["0000001"]["decretado"] and m["0000001"]["primeiro_decreto"] == "10/07/2026"
    def t2(): return m["0000002"]["decreto"] and m["0000002"]["reconhecido"] and not m["0000002"]["decretado"] and not m["0000003"]["decreto"]
    def t3(): return por["RS"]["n_municipios"] == 2 and por["RS"]["fracao_municipios"] == round(2/3, 4) and por["RS"]["fracao_populacao"] == 0.4 and por["BA"]["n_municipios"] == 0
    def t4(): return por["RS"]["fatias"]["em_classificacao"] == 2 and por["RS"]["fatias"]["apos_evento"] == 0 and por["RS"]["tons"] == {"reconhecido": 2, "decretado_sem_reconhecimento": 0}
    def t5(): s = serie_semanal(m); return sum(x["municipios"] for x in s) == 1 and any(x["defeso"] for x in s) and s[0]["semana"] == "2026-06-29"
    def t6(): return all(m2["evento_observado"] == "em_classificacao" for m2 in m.values() if m2["decreto"])   # C16: nunca imputado
    def t7(): return "art. 73, VI, a" in FRASE_C18 and semana_de(date(2026, 7, 8)) == "2026-07-06"
    return rodar_autoteste({"município: decretado + reconhecido, primeiro decreto": t1, "reconhecido só pelo S2iD conta; ibge fora do universo ignorado": t2,
                            "UF: fração de municípios e de população": t3, "fatias em_classificacao e tons": t4, "série desde 29/06 com defeso": t5,
                            "C16: evento observado nunca imputado": t6, "frase C18 e semana ISO": t7})


if __name__ == "__main__":
    sys.exit(autoteste() if "--autoteste" in sys.argv else gerar())
