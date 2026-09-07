#!/usr/bin/env python3
"""
gerar_contadores_financiamento.py — quatro contadores por UF (v3.1 §11, E18; 06/09/2026)
Mesma gramática ex-ante | defeso | ex-post; contagens e razões, sem escala nem juízo. Peso zero.
 1. R$ por rota, por habitante (2026): r5 (voluntárias, TransfereGov) coletado; demais rotas 'sem coleta'.
    Fatia por período (antes de 04/07 · defeso · depois de 25/10) exige a série por UF — 'sem coleta' até lá.
 2. Municípios cobertos: preventivo (fundo a fundo estadual preventivo, quando localizado) × resposta (r3/r4: sem coleta).
 3. Razão do dinheiro: R$ depois / R$ antes — só quando os dois existirem; senão null.
 4. Represado: instrumentos aprovados antes de 04/07 sem cronograma prefixado — 'não disponível' (Transferegov sem status).
Lê data/financiamento/por_uf.json e data/populacao_censo2022.json; grava data/financiamento/contadores_uf.json.
"""
import json, sys
from datetime import date
from coletores_base import ler, gravar, rodar_autoteste
UFS = ["AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT","PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO"]


def contadores_uf(uf: str, dados: dict, pop_uf: float) -> dict:
    """Função pura: os quatro contadores de uma UF a partir do registro de por_uf.json e da população."""
    rotas = (dados or {}).get("rotas") or {}
    por_hab = {}
    for r, v in rotas.items():
        val = (v or {}).get("valor_2026")
        por_hab[r] = round(val / pop_uf, 2) if (val is not None and pop_uf) else None
    faf = (dados or {}).get("fundo_a_fundo_preventivo") or {}
    prev_n = faf.get("repasses") if faf.get("status") == "localizado" else None
    antes = None; depois = None   # fatias por período: exigem a série por UF (sem coleta)
    return {"por_habitante_2026": por_hab, "por_periodo": {"antes_04_07": antes, "defeso": None, "depois_25_10": depois, "status": "sem_coleta"},
            "municipios_cobertos": {"preventivo": prev_n, "preventivo_fonte": faf.get("fonte") if prev_n is not None else None, "preventivo_valor": faf.get("valor_total") if prev_n is not None else None, "resposta": None, "resposta_status": "sem_coleta (r3/r4)"},
            "razao_depois_antes": (round(depois / antes, 2) if (antes and depois) else None),
            "represado": {"status": "nao_disponivel", "nota": "Transferegov não expõe o status dos planos de trabalho; pedido de LAI e 'não disponível' até lá"}}


def gerar() -> int:
    por = ler("financiamento/por_uf.json", {}) or {}; pop = ler("populacao_censo2022.json", {}) or {}
    vm = ler("verificacao_municipal.json", []) or []
    pop_uf = {}
    for r in vm:
        pop_uf[r["uf"]] = pop_uf.get(r["uf"], 0) + float(pop.get(str(r["ibge"]).zfill(7), 0) or 0)
    out = {uf: contadores_uf(uf, (por.get("uf") or {}).get(uf), pop_uf.get(uf, 0)) for uf in UFS}
    gravar("financiamento/contadores_uf.json", {"_governanca": "Quatro contadores por UF (v3.1 §11): R$ por rota por habitante; municípios cobertos preventivo × resposta; razão depois/antes; represado. Contagens e razões, sem escala nem juízo; peso zero. Lacunas declaradas campo a campo.", "gerado_em": date.today().strftime("%d/%m/%Y"), "uf": out})
    n = sum(1 for u in out.values() if u["municipios_cobertos"]["preventivo"] is not None)
    print(f"contadores: 27 UFs; r5 por habitante em {sum(1 for u in out.values() if u['por_habitante_2026'].get('r5') is not None)}; preventivo localizado em {n}")
    return 0


def autoteste() -> int:
    d = {"rotas": {"r5": {"valor_2026": 1000.0}, "r3": {"valor_2026": None}}, "fundo_a_fundo_preventivo": {"status": "localizado", "repasses": 12, "valor_total": 500, "fonte": "u"}}
    c = contadores_uf("XX", d, 200.0)
    def t1(): return c["por_habitante_2026"]["r5"] == 5.0 and c["por_habitante_2026"]["r3"] is None
    def t2(): return c["municipios_cobertos"]["preventivo"] == 12 and c["municipios_cobertos"]["resposta"] is None and c["razao_depois_antes"] is None
    def t3(): return contadores_uf("XX", {}, 0)["por_habitante_2026"] == {} and contadores_uf("XX", d, 0)["por_habitante_2026"]["r5"] is None
    return rodar_autoteste({"R$/hab por rota e lacuna por rota": t1, "cobertos preventivo × resposta; razão só com os dois": t2, "sem população = sem número": t3})


if __name__ == "__main__":
    sys.exit(autoteste() if "--autoteste" in sys.argv else gerar())def _hoje():
    """Data determinística = 'atualizado_em' de data/meta.json (a última rodada que gravou dados), para que a
    cadeia de derivados reproduza o arquivo byte a byte; 'hoje' só se o meta não existir."""
    import datetime as _dt, json as _js, pathlib as _pl
    try:
        a = _js.load(open(_pl.Path(__file__).resolve().parent / "data" / "meta.json", encoding="utf-8")).get("atualizado_em")
        return _dt.datetime.strptime(a, "%d/%m/%Y").date()
    except Exception:  # noqa: BLE001
        return _dt.date.today()
