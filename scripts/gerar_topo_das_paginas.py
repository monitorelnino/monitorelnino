#!/usr/bin/env python3
"""Instantâneo dos cartões do topo de cada página, para a Imprensa LER em vez de recalcular.

Item 1 do handover "Imprensa — redesenho definitivo" (02/10/2026). O defeito medido naquele dia:

- a Imprensa dizia "sem dado" no dinheiro, com dado publicado no Financiamento;
- a Imprensa dizia 482 casos de dengue na semana 37, lendo o InfoDengue, enquanto o MARÉ Saúde
  dizia 8.146 na semana 33, lendo o Sinan — duas fontes, duas semanas e dois números para a mesma
  pergunta, em páginas vizinhas;
- a temperatura era a máxima ABSOLUTA prevista, e o recorte aprovado é o maior **desvio em relação
  ao normal**.

A raiz é uma só: a Imprensa recalculava. Cada número existia duas vezes, em dois lugares, com duas
definições — e nada obrigava as duas a concordarem. Este arquivo é a correção: ele escreve, a partir
das MESMAS fontes que cada página lê, um instantâneo com o valor, a referência (semana, mês, janela),
o rótulo e a fonte de cada cartão do topo. A Imprensa passa a ler o instantâneo.

Um número só vive num lugar; quem quiser o mesmo número, lê.

    data/saude_desfechos/topo_saude.json      · MARÉ Saúde
    data/resposta/topo_defesa_civil.json      · Defesa civil
    data/financiamento/semana.json            · Financiamento (já existia, por gerar_financiamento_semana.py)

Uso:
    python3 scripts/gerar_topo_das_paginas.py
    python3 scripts/gerar_topo_das_paginas.py --autoteste
"""
from __future__ import annotations

import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

GOV_SAUDE = ("INSTANTÂNEO dos cartões do topo do MARÉ Saúde, para a Imprensa ler em vez de "
             "recalcular (handover de 02/10/2026, item 1). Não é fonte de nada: nasce das mesmas "
             "séries que a página lê. 'Semana epidemiológica fechada' é a última com valor na "
             "série — nunca a última do calendário, porque semana recente existe no arquivo com "
             "valor nulo e tratar nulo como zero publicaria uma queda que é só atraso de "
             "notificação.")
GOV_DC = ("INSTANTÂNEO dos cartões do topo da Defesa civil, para a Imprensa ler em vez de "
          "recalcular (handover de 02/10/2026, item 1). Não é fonte de nada: nasce dos mesmos "
          "arquivos que a página lê. Os três cartões de AGORA trazem a hora da consulta; os três "
          "do ciclo trazem a contagem desde 29/06 e quantos entraram nos últimos sete dias.")


LIMITE_ALERTA_HORAS = 24   # a mesma regra de `assets/js/defesa-civil.js`


def alertas_pararam(marca, agora=None) -> "str | None":
    """A frase da parada quando o carimbo dos alertas passou das 24 horas — ou `None`.

    O carimbo vem no fuso da redação (-03:00), escrito por `coletar_sinais_risco.agora()`; a
    comparação é em UTC, para a resposta não depender de onde o código roda. `agora` existe para
    o autoteste poder provar os dois lados da fronteira sem esperar o relógio.
    """
    from datetime import datetime, timedelta, timezone
    marca = str(marca or "")
    if not marca:
        return "a coleta de avisos e alertas não tem carimbo de data"
    for formato, reserva in (("%d/%m/%Y %H:%M", timedelta()),
                             ("%d/%m/%Y", timedelta(hours=23, minutes=59))):
        try:
            d = datetime.strptime(marca[:len("01/01/2026 00:00") if " " in formato else 10],
                                  formato) + reserva
            break
        except ValueError:
            d = None
    if d is None:
        return f"a coleta de avisos e alertas tem carimbo ilegível ({marca})"
    d = d.replace(tzinfo=timezone(timedelta(hours=-3)))
    agora = agora or datetime.now(timezone.utc)
    if (agora - d).total_seconds() / 3600.0 > LIMITE_ALERTA_HORAS:
        return f"sem atualização desde {marca}: a coleta de avisos e alertas passou das 24 horas"
    return None


def ultima_fechada(serie: dict, ano: str):
    """(semana, valor) da última semana COM valor, no ano dado. Função pura."""
    ses = sorted(k for k, v in (serie or {}).items() if v is not None and str(k).startswith(ano))
    return (ses[-1], (serie or {})[ses[-1]]) if ses else (None, None)


def nacional_da_serie(serie_por_uf: dict, ano: str):
    """A série do país. Função pura.

    02/10/2026 — defeito medido: o arquivo do SIVEP-Gripe traz a linha `BR` **junto** das 27 UFs, e
    somar `serie.values()` somava o país duas vezes. O número publicado era o dobro (8.534 em vez
    de 4.267). Quando existe a linha `BR`, ela é o país; só na falta dela o país é a soma das UFs.
    """
    if not serie_por_uf:
        return {}
    if isinstance(serie_por_uf.get("BR"), dict):
        return {k: v for k, v in serie_por_uf["BR"].items() if str(k).startswith(ano)}
    total = {}
    for uf, semanas in serie_por_uf.items():
        if uf == "BR" or not isinstance(semanas, dict):
            continue
        for se, v in semanas.items():
            if str(se).startswith(ano) and isinstance(v, (int, float)):
                total[se] = total.get(se, 0) + v
    return total


def cartoes_da_saude(dengue: dict, srag: dict, painel: dict, sinais: dict, monitor: dict) -> list:
    """Os seis cartões do topo do MARÉ Saúde. Função pura — é ela que o autoteste exercita."""
    cartoes = []
    ano_d = str((dengue or {}).get("ano_corrente") or "")
    se_d, v_d = ultima_fechada(((dengue or {}).get("serie") or {}).get("BR") or {}, ano_d)
    cartoes.append({
        "id": "dengue_casos_se", "valor": v_d, "referencia": se_d,
        "rotulo": ("notificações de dengue na semana epidemiológica " + se_d.split("-")[-1])
                  if se_d else "notificações de dengue na semana epidemiológica",
        "fonte": "Ministério da Saúde (Sinan)", "sem_coleta": se_d is None,
        "nota": "notificações, não casos confirmados; as últimas semanas são parciais e sobem com "
                "as notificações atrasadas; este número não indica relação com o El Niño",
    })
    ano_s = str((srag or {}).get("ano_corrente") or "")
    nac = nacional_da_serie((srag or {}).get("serie") or {}, ano_s)
    se_s, v_s = ultima_fechada(nac, ano_s)
    cartoes.append({
        "id": "srag_internacoes_se", "valor": v_s, "referencia": se_s,
        "rotulo": ("internações por síndrome respiratória grave na semana epidemiológica "
                   + se_s.split("-")[-1]) if se_s else
                  "internações por síndrome respiratória grave na semana epidemiológica",
        "fonte": "Ministério da Saúde (SIVEP-Gripe)", "sem_coleta": se_s is None,
        "nota": "as últimas semanas são parciais e sobem com as notificações atrasadas; este "
                "número não indica relação com o El Niño",
    })
    M = (painel or {}).get("municipios") or {}
    ufs = sorted({m.get("uf") for m in M.values()
                  if (m.get("nivel_ultima_se") or 0) >= 3 and m.get("uf")})
    cartoes.append({
        "id": "uf_dengue_alerta", "valor": len(ufs) if M else None, "referencia": "nível atual",
        "rotulo": "estados com dengue em nível de alerta", "fonte": "InfoDengue (Fiocruz e FGV)",
        "sem_coleta": not M, "lista": ufs,
        "nota": "nível calculado pelo InfoDengue; o estado entra quando ao menos um município "
                "acompanhado está em nível 3 ou 4",
    })
    # O arquivo traz `calor_excesso.por_uf`, uma linha por estado com os quatro níveis do painel.
    # O cartão conta MUNICÍPIOS em nível severo ou extremo, que é o recorte da página.
    calor = ((sinais or {}).get("calor_excesso") or {})
    por_uf = calor.get("por_uf") or {}
    acima = None
    if por_uf:
        acima = int(sum((v.get("severo") or 0) + (v.get("extremo") or 0) for v in por_uf.values()))
    cartoes.append({
        "id": "calor_municipios_severo", "valor": acima, "referencia": calor.get("data"),
        "rotulo": "municípios em nível severo ou extremo de calor",
        "fonte": "Ministério da Saúde (Painel Nacional de Excesso de Calor)",
        "sem_coleta": acima is None,
    })
    resp = (monitor or {}).get("resposta") or {}
    cartoes.append({
        "id": "emergencias_saude_ciclo", "valor": resp.get("emergencias"),
        "referencia": resp.get("desde"),
        "rotulo": "emergências em saúde declaradas no ciclo",
        "fonte": "atos federais e estaduais lidos pelo MARÉ",
        "sem_coleta": resp.get("emergencias") is None,
    })
    # O índice do MARÉ Saúde é a média das UFs VERIFICADAS, e o rótulo diz quantas são enquanto
    # não forem 27 — é a régua que a página usa, e a Imprensa passa a ler a mesma.
    res = (monitor or {}).get("resumo") or {}
    verificadas = res.get("verificadas")
    cartoes.append({
        "id": "mare_saude_indice", "valor": res.get("media_das_verificadas"),
        "referencia": (monitor or {}).get("gerado_em"),
        "rotulo": "MARÉ Saúde",
        "unidades_verificadas": verificadas,
        "fonte": "MARÉ (verificação própria)",
        "sem_coleta": res.get("media_das_verificadas") is None,
        "nota": (None if (verificadas or 0) >= 27
                 else f"média dos {verificadas} estados verificados"),
    })
    return cartoes


def cartoes_da_defesa_civil(alertas: dict, decretados: dict, por_uf: dict, hoje_iso: str,
                            populacao: dict = None) -> list:
    """Os seis cartões do topo da Defesa civil. Função pura.

    A variação dos três cartões do ciclo é a contagem dos que entraram nos últimos sete dias, pela
    data do próprio ato. Os três de AGORA não têm variação: não há retrato guardado de sete dias
    atrás, e comparar com o que não foi medido seria inventar.
    """
    import datetime as dt
    res = (alertas or {}).get("resumo") or {}
    # 08/10/2026: a página Defesa civil PARA de publicar contagem de alerta depois de 24 horas sem
    # coleta ("desenhar o retrato de ontem como em vigor é o único erro desta página que pode
    # machucar alguém"), e o instantâneo do topo seguia publicando o número — de onde a Imprensa o
    # copiava. A regra passa a estar no instantâneo, que é a fonte das duas superfícies.
    if alertas_pararam((alertas or {}).get("gerado_em")):
        res = {}
    muns_alerta = set(((alertas or {}).get("municipios") or {}).keys())
    quando = (alertas or {}).get("gerado_em")
    decret = {k: v for k, v in ((decretados or {}).get("municipios") or {}).items() if v.get("decreto")}
    reconhecidos = {k: v for k, v in decret.items() if v.get("reconhecido")}
    cruzados = [k for k in decret if k in muns_alerta]
    limite = (dt.date.fromisoformat(hoje_iso) - dt.timedelta(days=7)).isoformat()

    def iso(v):
        s = str(v or "")
        return (s[6:10] + "-" + s[3:5] + "-" + s[0:2]) if len(s) >= 10 and s[2] == "/" else None

    recentes = [k for k, v in decret.items() if (iso(v.get("primeiro_decreto")) or "") >= limite]
    novos = len(recentes)
    # A população de quem entrou na semana sai do Censo 2022 pelo código IBGE. Sem o arquivo, o
    # cartão fica sem variação — e não com uma variação estimada.
    pop_nova = (sum(int((populacao or {}).get(k) or 0) for k in recentes)
                if populacao else None) or None
    novos_rec = sum(1 for v in reconhecidos.values()
                    if (iso(((v.get("fontes") or [{}])[0]).get("data")) or "") >= limite)
    nacional = (por_uf or {}).get("nacional") or {}
    return [
        {"id": "municipios_alerta_cemaden", "valor": res.get("municipios_cemaden"),
         "referencia": quando, "rotulo": "municípios sob alerta do Cemaden",
         "fonte": "Cemaden", "sem_coleta": not res},
        {"id": "municipios_aviso_inmet", "valor": res.get("municipios_inmet"),
         "referencia": quando, "rotulo": "municípios sob aviso do Inmet",
         "fonte": "Inmet", "sem_coleta": not res},
        {"id": "decreto_e_alerta_ao_mesmo_tempo", "valor": len(cruzados) if res else None,
         "referencia": quando,
         "rotulo": "municípios com decreto de emergência e alerta ao mesmo tempo",
         "fonte": "MARÉ (cruzamento das duas consultas)", "sem_coleta": not res},
        {"id": "municipios_decretaram", "valor": len(decret) or nacional.get("n_municipios"),
         "referencia": "desde 29/06/2026", "variacao": novos,
         "rotulo": "municípios que decretaram emergência ou calamidade",
         "fonte": "Defesa Civil nacional, no Diário Oficial da União",
         "sem_coleta": not decret and nacional.get("n_municipios") is None},
        {"id": "populacao_sob_decreto", "valor": nacional.get("pop_sob_decreto"),
         "referencia": "desde 29/06/2026", "variacao": pop_nova,
         "rotulo": "pessoas que vivem nos municípios que decretaram",
         "fonte": "Censo 2022, do IBGE",
         "sem_coleta": nacional.get("pop_sob_decreto") is None},
        {"id": "reconhecidos_pelo_governo_federal",
         "valor": len(reconhecidos) or nacional.get("reconhecidos"),
         "referencia": "desde 29/06/2026", "variacao": novos_rec,
         "rotulo": "municípios com a emergência reconhecida pelo governo federal",
         "fonte": "Defesa Civil nacional, no Diário Oficial da União",
         "sem_coleta": not reconhecidos and nacional.get("reconhecidos") is None},
    ]


GOV_RISCOS = ("INSTANTÂNEO dos dois números do Monitor de riscos que a Imprensa publica, para ela "
              "ler em vez de recalcular (handover de 02/10/2026, item 1). Não é fonte de nada. O de "
              "temperatura é o maior DESVIO em relação à normal 1991–2020 do Inmet, e não a máxima "
              "absoluta: 35 °C é normal em Cuiabá e muito quente em Porto Alegre, e publicar a "
              "máxima absoluta era publicar geografia como se fosse notícia — mesma régua do mapa "
              "de calor da página.")


def cartoes_do_monitor_de_riscos(sinais: dict, normais: dict, limiar_ar: int = 40) -> list:
    """Os dois números do Monitor de riscos que a Imprensa publica. Função pura.

    Capital sem normal publicada fica SEM desvio — nunca com desvio estimado. Zero significaria
    "está na média", que é uma afirmação que o dado não sustenta.
    """
    ufs = (sinais or {}).get("uf") or {}
    caps = (normais or {}).get("capitais") or {}
    melhor = None
    com_normal = 0
    for uf, u in ufs.items():
        t = (u.get("temperatura") or {})
        tmax = t.get("tmax")
        serie = (caps.get(uf) or {}).get("tmax")
        if tmax is None or not isinstance(serie, list):
            continue
        data = str(t.get("data") or "")
        mes = int(data[3:5]) if len(data) >= 10 and data[2] == "/" else None
        normal = serie[mes - 1] if mes and len(serie) >= mes else None
        if not isinstance(normal, (int, float)):
            continue
        com_normal += 1
        desvio = round(tmax - normal, 1)
        if melhor is None or desvio > melhor["desvio"]:
            melhor = {"uf": uf, "capital": t.get("capital"), "desvio": desvio, "tmax": tmax,
                      "normal": normal, "data": t.get("data")}
    cartoes = [{
        "id": "temperatura_desvio_capital",
        "valor": melhor["desvio"] if melhor else None,
        "referencia": melhor["data"] if melhor else None,
        "rotulo": ("a maior diferença de temperatura máxima em relação ao normal, em "
                   + (melhor["capital"] or melhor["uf"]) if melhor
                   else "a maior diferença de temperatura máxima em relação ao normal"),
        "capital": melhor["capital"] if melhor else None,
        "uf": melhor["uf"] if melhor else None,
        "fonte": "Inmet (previsão para as capitais e normal de 1991 a 2020)",
        "sem_coleta": melhor is None,
        "nota": (f"máxima prevista de {melhor['tmax']} °C contra a média de {melhor['normal']} °C "
                 f"do mês; {com_normal} capital(is) com normal publicada" if melhor else None),
    }]
    acima = []
    lidas = 0
    for uf, u in ufs.items():
        ind = ((u.get("qualidade_ar") or {}).get("indice") or {})
        if ind.get("valor") is None:
            continue
        lidas += 1
        if ind["valor"] > limiar_ar:
            acima.append(uf)
    cartoes.append({
        "id": "capitais_ar_ruim_ou_pior",
        "valor": len(acima) if lidas else None,
        "referencia": "leitura mais recente",
        "rotulo": "capitais com o ar na faixa ruim ou acima dela",
        "fonte": "Copernicus (CAMS), via Open-Meteo", "sem_coleta": lidas == 0,
        "lista": sorted(acima),
        "nota": (f"faixa da própria escala europeia, acima de {limiar_ar}; {lidas} capital(is) "
                 f"com leitura" if lidas else None),
    })
    return cartoes


def _autoteste() -> int:
    falhas = []
    # O total era um literal e envelhecia calado: dizia cobrir mais casos do que
    # cobre, ou menos. Agora e contado.
    _casos_contados = []

    def ok(nome, cond):
        _casos_contados.append(nome)
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    ok("última fechada ignora semana com valor nulo",
       ultima_fechada({"2026-33": 10, "2026-34": None}, "2026") == ("2026-33", 10))
    ok("última fechada ignora outro ano",
       ultima_fechada({"2025-50": 9, "2026-02": 3}, "2026") == ("2026-02", 3))
    ok("série vazia devolve nada", ultima_fechada({}, "2026") == (None, None))

    com_br = {"BR": {"2026-35": 4267}, "SP": {"2026-35": 1000}, "RJ": {"2026-35": 500}}
    ok("com linha BR o país é a linha BR, e não a soma",
       nacional_da_serie(com_br, "2026") == {"2026-35": 4267})
    sem_br = {"SP": {"2026-35": 1000}, "RJ": {"2026-35": 500}}
    ok("sem linha BR o país é a soma das UFs",
       nacional_da_serie(sem_br, "2026") == {"2026-35": 1500})
    ok("série ausente não quebra", nacional_da_serie({}, "2026") == {})

    saude = cartoes_da_saude(
        {"ano_corrente": 2026, "serie": {"BR": {"2026-33": 8146, "2026-34": None}}},
        {"ano_corrente": 2026, "serie": com_br},
        {"municipios": {"1": {"uf": "SP", "nivel_ultima_se": 3}, "2": {"uf": "RJ", "nivel_ultima_se": 1}}},
        {"calor_excesso": {"data": "2026-09-25",
                           "por_uf": {"PA": {"severo": 4, "extremo": 1}, "MG": {"severo": 0}}}},
        {"resumo": {"media_das_verificadas": 38.5, "verificadas": 21},
         "resposta": {"emergencias": 2, "desde": "29/06/2026"}})
    por_id = {c["id"]: c for c in saude}
    ok("dengue sai do Sinan, pela última semana fechada",
       por_id["dengue_casos_se"]["valor"] == 8146 and por_id["dengue_casos_se"]["referencia"] == "2026-33")
    ok("dengue declara que são notificações", "notificações" in por_id["dengue_casos_se"]["nota"])
    ok("respiratórias não dobram o país", por_id["srag_internacoes_se"]["valor"] == 4267)
    ok("estados em alerta contam estado, não município", por_id["uf_dengue_alerta"]["valor"] == 1)
    ok("calor soma severo e extremo", por_id["calor_municipios_severo"]["valor"] == 5)
    ok("o índice é a média das verificadas", por_id["mare_saude_indice"]["valor"] == 38.5)
    ok("o índice diz quantos estados a média cobre",
       por_id["mare_saude_indice"]["unidades_verificadas"] == 21
       and "21 estados verificados" in por_id["mare_saude_indice"]["nota"])
    ok("série ausente vira sem_coleta, nunca zero",
       cartoes_da_saude({}, {}, {}, {}, {})[0]["sem_coleta"] is True
       and cartoes_da_saude({}, {}, {}, {}, {})[0]["valor"] is None)

    # 08/10/2026: o carimbo do fixture passa a ser RELATIVO ao relógio do teste. Com data fixa, a
    # regra das 24 horas zeraria o resumo e os três casos abaixo reprovariam por envelhecimento do
    # fixture, não por defeito do código.
    from datetime import datetime as _dt, timedelta as _td, timezone as _tz
    _fresco = (_dt.now(_tz(_td(hours=-3))) - _td(hours=1)).strftime("%d/%m/%Y %H:%M")
    _velho = (_dt.now(_tz(_td(hours=-3))) - _td(hours=30)).strftime("%d/%m/%Y %H:%M")
    ok("carimbo de uma hora não para a contagem", alertas_pararam(_fresco) is None)
    ok("carimbo de trinta horas para a contagem", bool(alertas_pararam(_velho)))
    ok("carimbo ausente para a contagem", bool(alertas_pararam("")))
    _parado = cartoes_da_defesa_civil(
        {"gerado_em": _velho, "resumo": {"municipios_cemaden": 13, "municipios_inmet": 2886},
         "municipios": {"3550308": {}}},
        {"municipios": {}}, {"nacional": {}}, "2026-10-02", {})
    _pp = {c["id"]: c for c in _parado}
    ok("alerta velho não publica contagem, e declara a parada",
       _pp["municipios_alerta_cemaden"]["valor"] is None
       and _pp["municipios_alerta_cemaden"]["sem_coleta"] is True)

    dc = cartoes_da_defesa_civil(
        {"gerado_em": _fresco, "resumo": {"municipios_cemaden": 13, "municipios_inmet": 2886},
         "municipios": {"3550308": {}, "9999999": {}}},
        {"municipios": {"3550308": {"decreto": True, "primeiro_decreto": "01/10/2026",
                                    "reconhecido": True, "fontes": [{"data": "01/10/2026"}]},
                        "2900207": {"decreto": True, "primeiro_decreto": "09/08/2026",
                                    "reconhecido": False, "fontes": [{"data": "09/08/2026"}]}}},
        {"nacional": {"n_municipios": 736, "pop_sob_decreto": 21262196, "reconhecidos": 656}},
        "2026-10-02", {"3550308": 11451245, "2900207": 17000})
    pid = {c["id"]: c for c in dc}
    ok("alerta do Cemaden vem do resumo", pid["municipios_alerta_cemaden"]["valor"] == 13)
    ok("aviso do Inmet vem do resumo", pid["municipios_aviso_inmet"]["valor"] == 2886)
    ok("o cruzamento conta quem decretou E está sob alerta",
       pid["decreto_e_alerta_ao_mesmo_tempo"]["valor"] == 1)
    ok("quem decretou conta o conjunto do consolidado", pid["municipios_decretaram"]["valor"] == 2)
    ok("a variação da semana conta o ato dos últimos sete dias",
       pid["municipios_decretaram"]["variacao"] == 1)
    ok("a população da semana é a de quem entrou na semana",
       pid["populacao_sob_decreto"]["variacao"] == 11451245)
    ok("sem arquivo de população o cartão fica sem variação",
       cartoes_da_defesa_civil(
           {"gerado_em": "x", "resumo": {"municipios_cemaden": 1}, "municipios": {}},
           {"municipios": {"1": {"decreto": True, "primeiro_decreto": "01/10/2026"}}},
           {"nacional": {"pop_sob_decreto": 10}}, "2026-10-02")[4]["variacao"] is None)
    ok("os cartões de agora não trazem variação",
       all("variacao" not in pid[i] for i in ("municipios_alerta_cemaden", "municipios_aviso_inmet",
                                              "decreto_e_alerta_ao_mesmo_tempo")))
    ok("sem alerta coletado o cartão é sem_coleta",
       cartoes_da_defesa_civil({}, {}, {}, "2026-10-02")[0]["sem_coleta"] is True)

    riscos = cartoes_do_monitor_de_riscos(
        {"uf": {"SP": {"temperatura": {"capital": "São Paulo", "tmax": 30.0, "data": "02/10/2026"},
                       "qualidade_ar": {"indice": {"valor": 55}}},
                "MT": {"temperatura": {"capital": "Cuiabá", "tmax": 35.0, "data": "02/10/2026"},
                       "qualidade_ar": {"indice": {"valor": 20}}}}},
        {"capitais": {"SP": {"tmax": [0] * 9 + [26.5, 0, 0]},
                      "MT": {"tmax": [0] * 9 + [34.0, 0, 0]}}})
    rid = {c["id"]: c for c in riscos}
    ok("o calor é o maior DESVIO, não a maior máxima",
       rid["temperatura_desvio_capital"]["capital"] == "São Paulo"
       and rid["temperatura_desvio_capital"]["valor"] == 3.5)
    ok("capital sem normal publicada não entra",
       cartoes_do_monitor_de_riscos(
           {"uf": {"RR": {"temperatura": {"tmax": 38.0, "data": "02/10/2026"}}}},
           {"capitais": {}})[0]["sem_coleta"] is True)
    ok("o ar conta as capitais acima da faixa", rid["capitais_ar_ruim_ou_pior"]["valor"] == 1)

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else f"✓ AUTOTESTE OK — {len(_casos_contados)} casos, sem rede e sem escrita em data/.")
    return 1 if falhas else 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return _autoteste()
    from coletores_base import gravar, hoje_editorial

    def ler(rel, padrao=None):
        p = RAIZ / "data" / rel
        if not p.exists():
            return padrao
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            return padrao

    hoje = hoje_editorial()
    saude = cartoes_da_saude(
        ler("saude_desfechos/dengue_sinan_serie.json", {}) or {},
        ler("saude_desfechos/srag_serie.json", {}) or {},
        ler("saude_desfechos/serie_painel.json", {}) or {},
        ler("saude_sinais.json", {}) or {},
        ler("monitor_saude.json", {}) or {})
    gravar("saude_desfechos/topo_saude.json",
           {"_governanca": GOV_SAUDE, "gerado_em": hoje.strftime("%d/%m/%Y"), "cartoes": saude})
    dc = cartoes_da_defesa_civil(
        ler("alertas/vigentes.json", {}) or {},
        ler("resposta/municipios_decretados.json", {}) or {},
        ler("resposta/por_uf.json", {}) or {},
        hoje.isoformat(), ler("populacao_censo2022.json", {}) or {})
    # Todo arquivo de `data/resposta/` carrega a frase do C18 (§32): é o portão da resposta que a
    # cobra, e com razão — quem abre um arquivo daquela pasta tem de ler, ali, o que o período
    # eleitoral deixa aberto. Ela vem do arquivo de origem, nunca escrita aqui.
    por_uf_arq = ler("resposta/por_uf.json", {}) or {}
    gravar("resposta/topo_defesa_civil.json",
           {"_governanca": GOV_DC, "gerado_em": hoje.strftime("%d/%m/%Y"),
            "frase_c18": por_uf_arq.get("frase_c18"), "cartoes": dc})
    riscos = cartoes_do_monitor_de_riscos(
        ler("sinais_risco.json", {}) or {}, ler("normais_capitais.json", {}) or {})
    gravar("topo_monitor_riscos.json",
           {"_governanca": GOV_RISCOS, "gerado_em": hoje.strftime("%d/%m/%Y"), "cartoes": riscos})
    for nome, cartoes in (("MARÉ Saúde", saude), ("Defesa civil", dc), ("Monitor de riscos", riscos)):
        vazios = [c["id"] for c in cartoes if c.get("sem_coleta")]
        print(f"→ {nome}: {len(cartoes)} cartão(ões)"
              + (f" · sem coleta: {', '.join(vazios)}" if vazios else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
