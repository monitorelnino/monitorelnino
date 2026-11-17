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

from coletores_base import DATA, INICIO_DO_CICLO, ler, gravar, rodar_autoteste, normalizar_nome

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


def semana_do_ciclo(iso: str) -> int:
    """Semana (calendário epidemiológico de 2026, que começa em 04/01) que contém a data. Pura."""
    import datetime
    return (datetime.date.fromisoformat(iso) - datetime.date(2026, 1, 4)).days // 7 + 1


def tempo(serie: dict, canal: dict, ref: list, mensal: bool = False) -> dict:
    """Posição de cada município na faixa habitual, semana a semana (ou mês a mês, `mensal`), do marco
    zero do ciclo ao último período fechado. Pura. 'a' acima do percentil 90 · 'd' entre a mediana e o percentil 90 · 'b' abaixo
    da mediana · None sem casos registrados (semana ainda em registro ou faixa ausente: nunca zero).
    `nv` é o nível de alerta do InfoDengue na semana, como a fonte o publica."""
    import datetime
    # O mês do marco zero (junho) quase não é ciclo: a série mensal começa em julho, como na UF.
    w0 = int(INICIO_DO_CICLO[5:7]) + 1 if mensal else semana_do_ciclo(INICIO_DO_CICLO)
    campo, chave_canal = ("meses_2026", "{:02d}") if mensal else ("semanas_2026", "{}")
    mun_s, mun_c = (serie or {}).get("municipios") or {}, (canal or {}).get("municipios") or {}
    fechadas = [int(k[-2:]) for m in mun_s.values() for k, v in (m.get(campo) or {}).items()
                if isinstance(v, dict) and v.get("casos") is not None]
    w1 = max(fechadas, default=w0 - 1)
    semanas = list(range(w0, w1 + 1))
    pos = {str(r.get("codigo_ibge")): r for r in ref or []}
    saida = []
    for cod, m in sorted(mun_s.items()):
        r = pos.get(cod)
        if not r or r.get("lat") is None:
            continue
        p, nv = [], []
        for w in semanas:
            x = (m.get(campo) or {}).get(f"2026-{w:02d}") or {}
            f = (mun_c.get(cod) or {}).get(chave_canal.format(w))
            c = x.get("casos")
            p.append(None if c is None or not f or f.get("p90") is None else
                     "a" if c > f["p90"] else ("d" if c >= f["mediana"] else "b"))
            nv.append(x.get("nivel"))
        saida.append({"ibge": cod, "nome": m.get("nome") or r["nome"], "uf": m.get("uf") or r["uf"],
                      "lat": round(r["lat"], 3), "lon": round(r["lon"], 3), "p": p, "nv": nv})
    if mensal:
        return {"meses": [f"2026-{w:02d}" for w in semanas], "municipios": saida}
    inicio = datetime.date(2026, 1, 4)
    return {"semanas": [(inicio + datetime.timedelta(7 * (w - 1))).isoformat() for w in semanas],
            "municipios": saida}


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
    # 17/11/2026 (editoria): o mapa dos municípios anda no tempo, do marco zero do ciclo à última semana fechada.
    ref = ler("municipios_ibge_referencia.json") or []
    srag = ler("saude_desfechos/srag_municipios.json") or {}
    canais = {"dengue": ler("saude_desfechos/canal_endemico.json") or {},
              "chikungunya": ler("saude_desfechos/chik_canal_endemico.json") or {},
              # SRAG (SIVEP-Gripe): o canal vem junto de cada município, no mesmo arquivo.
              "srag": {"municipios": {c: m.get("canal") or {} for c, m in (srag.get("municipios") or {}).items()}}}
    for nome, serie in (("dengue", dengue), ("chikungunya", chik), ("srag", srag)):
        if not serie.get("municipios"):
            continue
        t = tempo(serie, canais[nome], ref)
        gravar(f"saude_municipio/tempo_{nome}.json", {
            "_governanca": ("Posição de cada município acompanhado na faixa habitual da época (a da fonte: "
                            "InfoDengue, 2019–2025 sem 2024; SIVEP-Gripe, 2019–2025), semana a semana desde o "
                            "Boletim nº 1. `semanas` traz o "
                            "domingo de cada semana. 'a' acima do percentil 90, 'd' entre a mediana e ele, "
                            "'b' abaixo da mediana, null sem casos registrados (nunca zero). `nv`: nível de "
                            "alerta do InfoDengue, como a fonte publica. Peso zero."),
            "fonte": serie.get("sistema") or "InfoDengue (Fiocruz/FGV)", "gerado_em": serie.get("gerado_em"), **t}, compacto=True)
    # As internações (SIH/SUS), mês a mês, pelo município de residência; o arquivo tem o nome do desfecho da UF.
    from coletar_sih import DESFECHOS, SAIDA_MUN, serie_municipal_mensal
    from coletar_srag_sivep import municipios_acompanhados
    sih = ler(SAIDA_MUN) or {}
    if sih.get("arquivos"):
        import desfechos_sus as ds
        acomp = municipios_acompanhados(ler("populacao_censo2022.json") or {})
        nomes = {str(r["codigo_ibge"]): r for r in ref}
        for grupo, por_mun in serie_municipal_mensal(sih["arquivos"], acomp, ds.uf_por_codigo(ler)).items():
            serie = {"municipios": {c: {**v, "nome": (nomes.get(c) or {}).get("nome"), "uf": (nomes.get(c) or {}).get("uf")}
                                    for c, v in por_mun.items()}}
            t = tempo(serie, {"municipios": {c: v["canal"] for c, v in por_mun.items()}}, ref, mensal=True)
            gravar(f"saude_municipio/tempo_{DESFECHOS[grupo][0]}.json", {
                "_governanca": ("Posição de cada município de 100.000 habitantes ou mais na faixa habitual do mês "
                                "(SIH/SUS, internações por município de residência, 2019–2025 sem 2024), mês a mês "
                                "desde julho de 2026. 'a' acima do percentil 90, 'd' entre a mediana e ele, 'b' "
                                "abaixo da mediana, null sem o arquivo do mês lido ou mês ainda parcial (nunca "
                                "zero). Peso zero."),
                "fonte": sih.get("sistema"), "gerado_em": sih.get("gerado_em"), **t}, compacto=True)


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
        "tempo: começa no marco zero, para na última semana fechada; sem casos é null, nunca zero":
            lambda: (lambda t: t["semanas"][0] == "2026-06-28" and t["semanas"][-1] == "2026-07-05"
                     and t["municipios"][0]["p"] == ["a", None] and t["municipios"][0]["nv"] == [3, 1])(
                tempo({"municipios": {"1200104": {"nome": "Brasiléia", "uf": "AC", "semanas_2026": {
                    "2026-26": {"casos": 9, "nivel": 3}, "2026-27": {"casos": None, "est": 4, "nivel": 1}}},
                    "9999999": {"semanas_2026": {"2026-27": {"casos": 1}}}}},
                      {"municipios": {"1200104": {"26": {"mediana": 2, "p90": 5}, "27": {"mediana": 2, "p90": 5}}}},
                      [{"codigo_ibge": 1200104, "nome": "Brasiléia", "uf": "AC", "lat": -11, "lon": -68.7}])),
        "tempo mensal: começa em julho, chave do canal com dois dígitos":
            lambda: tempo({"municipios": {"1200104": {"meses_2026": {"2026-06": {"casos": 1}, "2026-07": {"casos": 9},
                                                                     "2026-08": {"casos": None}}}}},
                          {"municipios": {"1200104": {"07": {"mediana": 2, "p90": 5}}}},
                          [{"codigo_ibge": 1200104, "nome": "Brasiléia", "uf": "AC", "lat": -11, "lon": -68.7}],
                          mensal=True) == {"meses": ["2026-07"], "municipios": [{"ibge": "1200104", "nome": "Brasiléia",
                                           "uf": "AC", "lat": -11, "lon": -68.7, "p": ["a"], "nv": [None]}]},
        "tempo: semana 26 é a que contém 29/06/2026": lambda: semana_do_ciclo("2026-06-29") == 26,
        "negativo: série sem nível não gera bloco": lambda: alerta_infodengue({"semanas_2026": {"2026-40": {"nivel": None}}}) is None,
    })


if __name__ == "__main__":
    sys.exit(autoteste() if "--autoteste" in sys.argv else (gerar() or 0))
