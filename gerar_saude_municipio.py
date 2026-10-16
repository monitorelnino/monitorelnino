#!/usr/bin/env python3
"""
gerar_saude_municipio.py — a consulta do município na página de Saúde (16/10/2026)
=================================================================================
HANDOVER_SAUDE_PAGINA §6b. Um arquivo por UF, `data/saude_municipio/<UF>.json`, com o que já está
guardado por município em três arquivos de origem — nada é coletado nem recalculado aqui:

  · nível de alerta de dengue e de chikungunya do InfoDengue (`saude_desfechos/serie_painel.json` e
    `chik_serie_painel.json`): a semana mais recente que a fonte publica, com nível e casos
    estimados, e a última semana com notificações registradas;
  · classe de excesso de calor do Painel do MS (`saude_sinais.json` → `calor_excesso`);
  · o degrau de saúde do plano municipal na leitura automática (`saude_no_plano_auto.json`, casado
    ao município pela URL do documento registrado em `municipios.json`).

Município que a fonte não leu fica SEM o bloco — e a página diz "não lido"; nunca vira zero. A
respiratória grave e o índice MARÉ Saúde são do estado e a página os lê dos arquivos do estado.
Escritor único: o elo da saúde (`config/escritores.json`).
"""
import sys

from coletores_base import DATA, ler, gravar, rodar_autoteste, normalizar_nome

UFS = ("AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO").split()


def alerta_infodengue(m: dict):
    """{semana, nivel, casos_estimados, notificacoes: {semana, casos}} da série do município. Pura."""
    semanas = (m or {}).get("semanas_2026") or {}
    com_nivel = sorted(k for k, v in semanas.items() if isinstance(v, dict) and v.get("nivel") is not None)
    if not com_nivel:
        return None
    s = com_nivel[-1]
    notif = sorted(k for k, v in semanas.items() if isinstance(v, dict) and v.get("casos") is not None)
    return {"semana": s, "nivel": semanas[s]["nivel"], "casos_estimados": semanas[s].get("est"),
            "notificacoes": {"semana": notif[-1], "casos": semanas[notif[-1]]["casos"]} if notif else None}


def alerta_da_capital(c: dict):
    """O mesmo alerta do InfoDengue, na forma em que `saude_sinais.json` guarda as capitais. Pura."""
    se = str((c or {}).get("se") or "")
    if len(se) != 6 or (c or {}).get("nivel") is None:
        return None
    semana = f"{se[:4]}-{se[4:]}"
    return {"semana": semana, "nivel": c["nivel"], "casos_estimados": c.get("casos_est"),
            "notificacoes": {"semana": semana, "casos": c["casos_notif"]} if c.get("casos_notif") is not None else None}


def montar(ref: list, dengue: dict, chik: dict, calor: dict, plano_auto: dict, municipios: list,
           capitais: dict = None) -> dict:
    """{UF: {IBGE: {...}}}. A dengue das capitais que a série municipal não traz vem do alerta por
    capital (mesma fonte, mesmo modelo). Função pura."""
    por_url = {}
    for item in (plano_auto or {}).get("itens", {}).values():
        if item.get("url") and item.get("degrau") is not None:
            por_url[item["url"]] = {k: item.get(k) for k in ("degrau", "rotulo", "pagina_citada", "url", "status")}
    planos = {(normalizar_nome(str(m.get("nome") or "")), m.get("uf")): por_url[m["url"]]
              for m in municipios or [] if m.get("url") in por_url}
    dm, cm, km = ((dengue or {}).get("municipios") or {}, (chik or {}).get("municipios") or {},
                  (calor or {}).get("municipios") or {})
    por_capital = {str(c.get("ibge")): c for c in (capitais or {}).values() if isinstance(c, dict)}
    saida = {}
    for r in ref:
        cod, uf = str(r.get("codigo_ibge") or ""), r.get("uf")
        if not cod or uf not in UFS:
            continue
        item = {"nome": r["nome"]}
        for chave, base in (("dengue", dm), ("chikungunya", cm)):
            a = alerta_infodengue(base.get(cod)) or (alerta_da_capital(por_capital.get(cod)) if chave == "dengue" else None)
            if a:
                item[chave] = a
        if isinstance(km.get(cod), dict) and km[cod].get("classe"):
            item["calor"] = km[cod]["classe"]
        p = planos.get((normalizar_nome(r["nome"]), uf))
        if p:
            item["saude_no_plano"] = p
        saida.setdefault(uf, {})[cod] = item
    return saida


def gerar():
    sinais = ler("saude_sinais.json") or {}
    dengue, chik = ler("saude_desfechos/serie_painel.json") or {}, ler("saude_desfechos/chik_serie_painel.json") or {}
    calor = sinais.get("calor_excesso") or {}
    por_uf = montar(ler("municipios_ibge_referencia.json") or [], dengue, chik, calor,
                    ler("saude_no_plano_auto.json") or {}, ler("municipios.json") or [],
                    sinais.get("dengue_capitais") or {})
    cabeca = {"_governanca": ("Consulta do município na página de Saúde: o que os arquivos de origem guardam por "
                              "código IBGE. Município sem bloco não foi lido pela fonte (nunca zero). Respiratória "
                              "grave e MARÉ Saúde são do estado. Peso zero."),
              "origens": {"dengue": {"fonte": "InfoDengue (Fiocruz/FGV)", "gerado_em": dengue.get("gerado_em")},
                          "chikungunya": {"fonte": "InfoDengue (Fiocruz/FGV)", "gerado_em": chik.get("gerado_em")},
                          "calor": {"fonte": "Painel Nacional de Excesso de Calor (Ministério da Saúde)",
                                    "data": calor.get("data"), "url": calor.get("url")},
                          "saude_no_plano": {"fonte": "leitura automática do plano municipal (METODOLOGIA §10.1)"}}}
    (DATA / "saude_municipio").mkdir(exist_ok=True)
    for uf, municipios in sorted(por_uf.items()):
        gravar(f"saude_municipio/{uf}.json", {**cabeca, "uf": uf, "municipios": municipios}, compacto=True)
    print(f"→ data/saude_municipio/: {len(por_uf)} UF(s), {sum(len(v) for v in por_uf.values())} município(s).")


def autoteste() -> int:
    ref = [{"nome": "Brasiléia", "uf": "AC", "codigo_ibge": 1200104}, {"nome": "Manaus", "uf": "AM", "codigo_ibge": 1302603}]
    dengue = {"municipios": {"1200104": {"semanas_2026": {
        "2026-40": {"casos": None, "est": 6.0, "nivel": 1}, "2026-36": {"casos": 4, "est": 5.0, "nivel": 2}}}}}
    plano = {"itens": {"h": {"degrau": 5, "rotulo": "riscos_do_ciclo", "pagina_citada": 35, "url": "https://m/p.pdf",
                             "status": "leitura automática"}}}
    mun = [{"nome": "MANAUS", "uf": "AM", "url": "https://m/p.pdf"}]
    s = montar(ref, dengue, {}, {"municipios": {"1302603": {"classe": "Severo"}}}, plano, mun,
               {"AM": {"se": 202640, "nivel": 2, "casos_est": 81.5, "casos_notif": 3, "ibge": "1302603"}})
    return rodar_autoteste({
        "dengue: semana mais recente com nível; notificações da última semana com casos":
            lambda: s["AC"]["1200104"]["dengue"] == {"semana": "2026-40", "nivel": 1, "casos_estimados": 6.0,
                                                     "notificacoes": {"semana": "2026-36", "casos": 4}},
        "município não lido pela fonte fica sem bloco (nunca zero)":
            lambda: "chikungunya" not in s["AC"]["1200104"] and "chikungunya" not in s["AM"]["1302603"],
        "capital fora da série municipal recebe o alerta da capital (mesma fonte)":
            lambda: s["AM"]["1302603"]["dengue"] == {"semana": "2026-40", "nivel": 2, "casos_estimados": 81.5,
                                                     "notificacoes": {"semana": "2026-40", "casos": 3}},
        "calor na classe da fonte": lambda: s["AM"]["1302603"]["calor"] == "Severo",
        "degrau do plano casado pela URL do registro e pelo nome normalizado":
            lambda: s["AM"]["1302603"]["saude_no_plano"]["degrau"] == 5,
        "negativo: série sem nível não gera bloco": lambda: alerta_infodengue({"semanas_2026": {"2026-40": {"nivel": None}}}) is None,
    })


if __name__ == "__main__":
    sys.exit(autoteste() if "--autoteste" in sys.argv else (gerar() or 0))
