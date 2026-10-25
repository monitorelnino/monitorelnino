#!/usr/bin/env python3
"""Os cartões do topo do Financiamento (item 4 do contrato de layout, 02/10/2026).

Escreve `data/financiamento/semana.json` com quatro cartões, cada um com o recorte que a FONTE
permite — e nunca com "sem dado" quando a série-base existe:

- `pago_periodo_mp` — pago pelas ações reforçadas pelas medidas provisórias do ciclo. O Portal da
  Transparência publica execução por MÊS: quando o coletor já guardou a quebra mensal
  (`execucao.por_mes`), o cartão fala do último mês fechado; enquanto só houver o acumulado do
  ciclo, ele fala do acumulado e diz quais meses leu. Não inventa semana.
- `transferido_municipios_periodo` — transferido pela União a municípios no último mês FECHADO.
  O coletor marca mês ainda sendo preenchido como `parcial`, e mês parcial não vira cartão: ele
  mostraria queda que é da planilha, não do dinheiro.
- `resposta_liberado_semana` — recursos de resposta autorizados nas portarias da SEDEC nos últimos
  sete dias, com o número de municípios. Portaria tem data por ato, e aí o recorte semanal é real.
- `atos_federais_semana` — atos federais de financiamento novos nos últimos sete dias. Pelo
  contrato, o cartão só aparece quando é maior que zero.

Autoteste offline (`--autoteste`) não toca `data/`: ele exercita as funções puras com entrada
inventada, inclusive mês parcial e série ausente.
"""
from __future__ import annotations

import pathlib

import sys
from datetime import datetime, timedelta

from coletores_base import data_do_corte, gravar, ler

JANELA = 7
INICIO_CICLO = datetime(2026, 6, 29)     # Boletim nº 1 do Painel El Niño (o mesmo de gerar_resposta.py)
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
         "setembro", "outubro", "novembro", "dezembro"]
ARQUIVO = "financiamento/semana.json"
# Trava estrutural: este gerador escreve UM arquivo, e nunca o banco nem o índice.
BANCO_PROIBIDO = {"estados.json", "saude_uf.json", "municipios.json", "indice.json",
                  "monitor_saude.json"}


def emergencia_por_mes(v: dict) -> dict:
    """Repasse do FNS ligado a emergência por mês, desde o início do ciclo (29/06/2026). O FNS é mensal e não traz a
    data do repasse: entram só os meses inteiros a partir do ciclo (o recorte conservador, julho em diante)."""
    mes0 = INICIO_CICLO.strftime("%Y%m") if INICIO_CICLO.day == 1 else (INICIO_CICLO.replace(day=28) + timedelta(days=4)).strftime("%Y%m")
    return {k: float(x[1] or 0.0) for k, x in ((v or {}).get("meses") or {}).items() if k >= mes0}


def emergencia_no_ciclo(v: dict) -> float:
    return round(sum(emergencia_por_mes(v).values()), 2)


def atos_do_ciclo(rec: dict, corte: datetime):
    """(ibge, ato, data) de cada portaria da SEDEC entre 29/06/2026 e o corte: a única seleção que soma o
    cartão, o mapa e a série mensal."""
    for ib, m in ((rec or {}).get("municipios") or {}).items():
        for a in (m or {}).get("atos") or []:
            if (d := _data(a.get("data"))) and INICIO_CICLO <= d <= corte:
                yield ib, a, d


def mes_legivel(aaaamm: str) -> str:
    """'202608' → 'agosto de 2026'. Entrada malformada devolve ela mesma, sem levantar."""
    if not (isinstance(aaaamm, str) and len(aaaamm) == 6 and aaaamm.isdigit()):
        return str(aaaamm)
    mes = int(aaaamm[4:])
    if not 1 <= mes <= 12:
        return aaaamm
    return f"{MESES[mes - 1]} de {aaaamm[:4]}"


def ultimo_mes_fechado(meses: dict) -> str | None:
    """O mês mais recente que a fonte não marcou como parcial.

    O coletor de transferências marca `parcial: True` quando o arquivo do Portal ainda está sendo
    preenchido. Mês parcial no cartão mostraria uma queda que é da planilha.
    """
    if not isinstance(meses, dict):
        return None
    fechados = [m for m, v in meses.items()
                if isinstance(m, str) and m.isdigit() and not (isinstance(v, dict) and v.get("parcial"))]
    return max(fechados) if fechados else None


def na_janela(atos: list, corte: datetime, dias: int = JANELA) -> list:
    """Atos com data nos `dias` anteriores ao corte, inclusive. Data ilegível fica fora."""
    inicio = corte - timedelta(days=dias)
    dentro = []
    for a in atos or []:
        bruta = (a.get("data") or a.get("publicado_em") or "") if isinstance(a, dict) else ""
        d = None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                d = datetime.strptime(str(bruta)[:10], fmt)
                break
            except ValueError:
                continue
        if d and inicio <= d <= corte:
            dentro.append(a)
    return dentro


def corte_do_dado(meta: dict):
    """A data de corte declarada em `meta.json` (dd/mm/aaaa ou ISO); sem ela, `data_do_corte()`."""
    bruta = str((meta or {}).get("corte") or "").strip()[:10]
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(bruta, fmt).date()
        except ValueError:
            continue
    return data_do_corte()


def cartao(ident: str, valor, unidade: str, periodo: str, fonte: str, url_fonte=None,
           detalhe=None) -> dict:
    return {"id": ident, "valor": valor, "unidade": unidade, "periodo": periodo,
            "fonte": fonte, "url_fonte": url_fonte, "detalhe": detalhe, "sem_coleta": False}


def sem_coleta(ident: str, unidade: str, porque: str, fonte: str) -> dict:
    """Lacuna DECLARADA: a série-base não existe. Nunca zero no lugar de ausência."""
    return {"id": ident, "valor": None, "unidade": unidade, "periodo": None, "fonte": fonte,
            "url_fonte": None, "detalhe": porque, "sem_coleta": True}


def sem_data_na_origem(ident: str, unidade: str, porque: str, fonte: str) -> dict:
    """Ausência de OUTRA classe: a série existe e foi lida, e a origem não datou os atos.

    09/10/2026. O A3-10 declarou este caso como `sem_coleta`, e as duas coisas são distintas — a
    regra do site exige quatro estados separados, e dizer "sem coleta" de uma série que está em
    disco é dizer o que não aconteceu. O portão de layout (regra g) reprova exatamente isso, e
    reprovava com razão. O cartão passa a dizer a classe que é, em palavras, sem travessão.
    """
    return {"id": ident, "valor": None, "unidade": unidade, "periodo": None, "fonte": fonte,
            "url_fonte": None, "detalhe": porque, "sem_coleta": False,
            "classe": "sem_data_na_origem"}


def cartao_pago(mps: dict) -> dict:
    """Pago pelas ações reforçadas pelas MPs. Mês fechado quando houver quebra mensal."""
    itens = (mps or {}).get("mps") or []
    execucoes = [(m.get("execucao") or {}) for m in itens]
    coletadas = [e for e in execucoes if e.get("status") == "coletado"]
    if not coletadas:
        return sem_coleta("pago_periodo_mp", "reais",
                          "a execução das medidas provisórias não foi coletada até o corte",
                          "Portal da Transparência, Execução da Despesa")
    # 10/10/2026 (A6-22, A6-13): pago vazio é ausência e fica fora da soma; mês em que nenhuma
    # origem declarou o pago não vira R$ 0,00. Mês marcado `parcial` não é o "último mês".
    por_mes, parciais = {}, set()
    for e in coletadas:
        for mes, v in (e.get("por_mes") or {}).items():
            pago = (v or {}).get("pago")
            if isinstance(v, dict) and v.get("parcial"):
                parciais.add(mes)
            if isinstance(pago, (int, float)):
                por_mes[mes] = por_mes.get(mes, 0.0) + float(pago)
    fechados = [m for m in por_mes if m not in parciais]
    if fechados:
        mes = max(fechados)
        return cartao("pago_periodo_mp", round(por_mes[mes], 2), "reais",
                      f"mês de {mes_legivel(mes)}",
                      "Portal da Transparência, Execução da Despesa (arquivos mensais abertos)",
                      # Sem travessão: o portão de legendas o reprova em texto de figura, e com
                      # razão — travessão em cartão vira frase dentro de frase. Duas frases.
                      # Sem travessão e sem conectivo de causa: o portão de legendas reprova os
                      # dois em texto de figura. O fato, em duas frases, basta.
                      detalhe=("execução das ações reforçadas pelas medidas provisórias do ciclo. "
                               "O valor inclui a dotação ordinária da ação. É teto, não a execução "
                               "do crédito"))
    meses = sorted({m for e in coletadas for m in (e.get("meses") or [])})
    pagos = [float(e["pago"]) for e in coletadas if isinstance(e.get("pago"), (int, float))]
    if not pagos:
        return sem_data_na_origem("pago_periodo_mp", "reais",
                                  "a execução foi lida e a origem não declarou o valor pago",
                                  "Portal da Transparência, Execução da Despesa")
    total = round(sum(pagos), 2)
    janela = (f"meses de {mes_legivel(meses[0])} a {mes_legivel(meses[-1])}"
              if len(meses) > 1 else (f"mês de {mes_legivel(meses[0])}" if meses else "ciclo"))
    return cartao("pago_periodo_mp", total, "reais", janela,
                  "Portal da Transparência, Execução da Despesa (arquivos mensais abertos)",
                  detalhe="acumulado do ciclo: a quebra por mês entra na próxima coleta da execução")


def cartao_transferido(transf: dict) -> dict:
    """Transferido pela União a municípios no último mês fechado."""
    meses = (transf or {}).get("meses_lidos") or {}
    mes = ultimo_mes_fechado(meses)
    if not mes:
        return sem_coleta("transferido_municipios_periodo", "reais",
                          "nenhum mês fechado de transferências lido até o corte",
                          "Portal da Transparência, Transferências de Recursos")
    soma = float((meses[mes] or {}).get("soma") or 0.0)
    casados = (meses[mes] or {}).get("municipios_casados")
    return cartao("transferido_municipios_periodo", round(soma, 2), "reais",
                  f"mês de {mes_legivel(mes)}",
                  "Portal da Transparência, Transferências de Recursos (dados abertos)",
                  url_fonte="https://portaldatransparencia.gov.br/download-de-dados/transferencias",
                  detalhe=(f"{casados} municípios com transferência no mês" if casados else None))


def cartao_resposta(rec: dict, corte: datetime) -> dict:
    """Recursos de resposta autorizados nas portarias da SEDEC nos últimos sete dias."""
    municipios = (rec or {}).get("municipios")
    if not municipios:
        return sem_coleta("resposta_liberado_semana", "reais",
                          "as portarias de recursos de resposta não foram coletadas até o corte",
                          "Portarias da SEDEC no Diário Oficial da União")
    atos = []
    for m in municipios.values():
        for a in (m or {}).get("atos") or []:
            if (a or {}).get("acao") == "resposta":
                atos.append(a)
    na = na_janela(atos, corte)
    valor = round(sum(float(a.get("valor_autorizado") or 0.0) for a in na), 2)
    cidades = len({(a.get("municipio"), a.get("uf")) for a in na})
    c = cartao("resposta_liberado_semana", valor, "reais", "últimos 7 dias",
               "Portarias da SEDEC no Diário Oficial da União",
               detalhe=(f"{cidades} município(s) em {len(na)} portaria(s)" if na
                        else "nenhuma portaria de resposta publicada nos últimos 7 dias"))
    # 17/10/2026 (§9.4): a janela de sete dias aparecia sozinha, como se fosse o total. O total do
    # ciclo, todas as ações, vai ao lado, com o número de municípios de cada recorte.
    c.update(municipios_semana=cidades, **defesa_civil_ciclo(rec, corte))
    return c


def defesa_civil_ciclo(rec: dict, corte: datetime) -> dict:
    """Autorizado por portaria da SEDEC desde 29/06/2026, todas as ações. Função pura."""
    total, por_acao, cidades = 0.0, {}, set()
    for _, a, _ in atos_do_ciclo(rec, corte):
        v = float(a.get("valor_autorizado") or 0.0)
        total += v; cidades.add((a.get("municipio"), a.get("uf")))
        por_acao[a.get("acao") or "outra"] = round(por_acao.get(a.get("acao") or "outra", 0.0) + v, 2)
    return {"valor_ciclo": round(total, 2), "municipios_ciclo": len(cidades),
            "por_acao_ciclo": dict(sorted(por_acao.items())), "desde": INICIO_CICLO.strftime("%d/%m/%Y")}


def _data(bruta):
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(str(bruta or "")[:10], fmt)
        except ValueError:
            continue
    return None


def tem_data_legivel(atos: list) -> bool:
    """Algum item traz data de publicação que a janela saiba ler?

    08/10/2026 (A3-10). Nenhum dos cinco compromissos federais tinha `data` nem `publicado_em`:
    `na_janela` devolvia lista vazia, e o cartão publicava **"0 atos" como fato**, nos últimos sete
    dias, no Financiamento e na Imprensa. Zero medido e zero por campo inexistente são coisas
    diferentes — e a regra do site é que zero só se publica quando a coleta rodou.
    """
    for a in atos or []:
        if not isinstance(a, dict):
            continue
        bruta = str(a.get("data") or a.get("publicado_em") or "")[:10]
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                datetime.strptime(bruta, fmt)
                return True
            except ValueError:
                continue
    return False


def cartao_atos(mps: dict, corte: datetime) -> dict:
    """Atos federais de financiamento (as medidas provisórias do ciclo) novos nos últimos sete dias.

    17/10/2026 (HANDOVER_FINANCIAMENTO §9.4): lia `compromissos_federais.json`, uma lista de
    contexto curada sem data de ato, e o cartão publicava "sem data na origem" como valor. O ato
    federal com data é a MP (`publicada_em`, do texto da MP); é ela que se conta."""
    itens = (mps or {}).get("mps")
    if itens is not None:
        itens = [dict(m, data=m.get("publicada_em"), instrumento=m.get("numero")) for m in itens]
    if itens is None:
        return sem_coleta("atos_federais_semana", "atos",
                          "o arquivo das medidas provisórias não foi coletado até o corte",
                          "Atos federais lidos pelo MARÉ")
    # Lista VAZIA é zero medido: a coleta rodou e não havia ato no período. O caso do A3-10 é
    # outro — há itens, e nenhum deles traz data, de modo que a janela não tem o que medir.
    if itens and not tem_data_legivel(itens):
        return sem_data_na_origem("atos_federais_semana", "atos",
                                  "a origem das medidas provisórias não traz data de publicação "
                                  "do ato; sem data não há janela de sete dias para medir",
                                  "Atos federais lidos pelo MARÉ")
    na = na_janela(itens, corte)
    return cartao("atos_federais_semana", len(na), "atos", "últimos 7 dias",
                  "Atos federais lidos pelo MARÉ",
                  detalhe=(", ".join(filter(None, (a.get("instrumento") for a in na[:3]))) or None))


def _execucoes(mps: dict) -> list:
    return [m for m in (mps or {}).get("mps") or [] if (m.get("execucao") or {}).get("status") == "coletado"]


def mes_a_mes(mps: dict) -> list:
    """Pago por mês de cada MP, desde o mês de publicação; mês corrente marcado parcial. Função pura."""
    out = []
    for m in _execucoes(mps):
        e = m["execucao"]
        out.append({"id": m.get("id"), "numero": m.get("numero"), "tema": m.get("tema"),
                    "risco_declarado": m.get("risco_declarado"),
                    "meses": [{"mes": k, "pago": v.get("pago"), "parcial": bool(v.get("parcial"))
                               or k in (e.get("meses_parciais") or [])}
                              for k, v in sorted((e.get("por_mes") or {}).items()) if isinstance(v, dict)]})
    return out


def topo(mps: dict, comp: dict, rec: dict, fns_mun: dict, corte: datetime) -> list:
    """Os cinco números do topo (HANDOVER_FINANCIAMENTO §3). Cada um com fonte; ausência é lacuna."""
    mp = (mps or {}).get("mps") or []
    nums = [str(m.get("numero") or "").replace("MP ", "").split("/")[0] for m in mp]
    # Anúncio que CONTÉM as MPs (cita o número delas) não soma: duplicaria o valor (§4).
    outras = [i for i in (comp or {}).get("itens") or [] if isinstance(i.get("valor_total"), (int, float))
              and not any(n and n in str(i.get("instrumento") or "") for n in nums)]
    origens = [m for m in mp if isinstance(m.get("valor"), (int, float))] + outras
    anunciado = (cartao("anunciado_atos", round(sum(float(m.get("valor")) for m in mp if isinstance(m.get("valor"), (int, float)))
                                                + sum(float(i["valor_total"]) for i in outras), 2),
                        "reais", "El Niño 2026/2027", "Texto das medidas provisórias e atos estaduais",
                        detalhe=f"{len(origens)} origens") if origens else
                 sem_coleta("anunciado_atos", "reais", "nenhum ato com valor lido até o corte", "Atos oficiais"))
    if origens: anunciado["n_atos"] = len(origens)
    ex = _execucoes(mps)
    pagos = [float(m["execucao"]["pago"]) for m in ex if isinstance(m["execucao"].get("pago"), (int, float))]
    fonte_ex = "Portal da Transparência, Execução da Despesa (arquivos mensais abertos)"
    if pagos:
        parcial = {}
        for m in ex:
            for k, v in (m["execucao"].get("por_mes") or {}).items():
                if isinstance(v, dict) and v.get("parcial") and isinstance(v.get("pago"), (int, float)):
                    parcial[k] = parcial.get(k, 0.0) + float(v["pago"])
        pago = cartao("pago_ate_agora", round(sum(pagos), 2), "reais",
                      "desde o mês de publicação de cada medida", fonte_ex)
        if parcial:
            k = max(parcial); pago.update(variacao_mes=round(parcial[k], 2), mes_variacao=k, mes_variacao_parcial=True)
        direto = sum(float((m.get("forma_de_aplicacao") or {}).get("por_modalidade", {}).get("aplicados diretamente pela União") or 0.0)
                     for m in ex if (m.get("forma_de_aplicacao") or {}).get("status") == "coletado")
        aplic = [m for m in ex if (m.get("forma_de_aplicacao") or {}).get("status") == "coletado"]
        base = sum(float(m["execucao"]["pago"]) for m in aplic if isinstance(m["execucao"].get("pago"), (int, float)))
        gasto = (cartao("gasto_direto_uniao", round(100.0 * direto / base, 1), "% do valor pago",
                        "desde o mês de publicação de cada medida", fonte_ex,
                        detalhe="modalidade de aplicação 90, aplicação direta") if base else
                 sem_coleta("gasto_direto_uniao", "% do valor pago", "a modalidade de aplicação não foi coletada até o corte", fonte_ex))
    else:
        pago = sem_coleta("pago_ate_agora", "reais", "a execução das medidas provisórias não foi coletada até o corte", fonte_ex)
        gasto = sem_coleta("gasto_direto_uniao", "% do valor pago", "a execução das medidas provisórias não foi coletada até o corte", fonte_ex)
    if (rec or {}).get("municipios"):
        dc = defesa_civil_ciclo(rec, corte)
        defesa = cartao("defesa_civil_ciclo", dc["valor_ciclo"], "reais", f"desde {dc['desde']}",
                        "Portarias da SEDEC no Diário Oficial da União", detalhe=f"{dc['municipios_ciclo']} municípios")
        defesa.update(municipios=dc["municipios_ciclo"], por_acao=dc["por_acao_ciclo"])
    else:
        defesa = sem_coleta("defesa_civil_ciclo", "reais", "as portarias de recursos não foram coletadas até o corte",
                            "Portarias da SEDEC no Diário Oficial da União")
    mun = (fns_mun or {}).get("municipios")
    fonte_fns = "Portal da Transparência, Transferências de Recursos (Fundo Nacional de Saúde)"
    if mun:
        meses = sorted({k for v in mun.values() for k in (v.get("meses") or {})})
        com = {k: e for k, v in mun.items() if (e := emergencia_no_ciclo(v)) > 0}
        sus = cartao("sus_emergencia", round(sum(com.values()), 2), "reais", f"desde {INICIO_CICLO.strftime('%d/%m/%Y')}", fonte_fns,
                     detalhe=f"{len(com)} municípios; fundos municipais, linhas cujo nome cita emergência; "
                             "meses inteiros a partir de julho (o FNS não traz a data do repasse)")
        sus.update(municipios=len(com), ultimo_mes=meses[-1] if meses else None)
    else:
        sus = sem_coleta("sus_emergencia", "reais", "os repasses do FNS por município não foram coletados até o corte", fonte_fns)
    return [anunciado, pago, gasto, defesa, sus]


def mapa(rec: dict, fns_mun: dict, ref: list, corte: datetime) -> list:
    """Pontos do mapa municipal (§5): defesa civil (autorizado desde 29/06) e saúde (FNS de
    emergência), com a sede de `municipios_ibge_referencia.json`. Município sem sede fica fora,
    contado em `sem_sede`. Função pura."""
    sede = {str(r.get("codigo_ibge")).zfill(7): (r.get("lat"), r.get("lon"), r.get("nome"), r.get("uf")) for r in ref or []}
    pts = []
    por_mun = {}
    for ib, a, _ in atos_do_ciclo(rec, corte):
        por_mun.setdefault(ib, []).append(a)
    for ib, atos in por_mun.items():
        ult = max(atos, key=lambda a: a.get("data") or "")
        pts.append({"ibge": str(ib).zfill(7), "origem": "defesa_civil", "valor": round(sum(float(a.get("valor_autorizado") or 0) for a in atos), 2),
                    "ato": ("Portaria " + str(ult.get("portaria"))) if ult.get("portaria") else None, "data": ult.get("data"), "url": ult.get("url"),
                    "n_atos": len(atos)})
    for ib, v in ((fns_mun or {}).get("municipios") or {}).items():
        e = emergencia_no_ciclo(v)
        if e > 0:
            pts.append({"ibge": str(ib).zfill(7), "origem": "saude", "valor": round(e, 2), "ato": "repasse do FNS ligado a emergência",
                        "data": None, "url": (fns_mun or {}).get("fonte"), "n_atos": None})
    out = []
    for p in sorted(pts, key=lambda p: (p["origem"], p["ibge"])):
        s = sede.get(p["ibge"])
        if s and s[0] is not None:
            out.append(dict(p, lat=s[0], lon=s[1], nome=s[2], uf=s[3]))
        else:
            out.append(dict(p, lat=None, lon=None, nome=None, uf=None, sem_sede=True))
    return out


DIAS_PENDENCIA = 30


def funil_defesa_civil(dec: dict, rec: dict, corte: datetime) -> dict:
    """Do decreto ao recurso, sobre os mesmos arquivos que a página lia: decretaram, reconhecidos pela União,
    com portaria de recurso no ciclo (a MESMA contagem do cartão `defesa_civil_ciclo`; `n_com_recurso_e_decretaram`
    diz quantos deles constam nos decretos lidos) e reconhecidos há mais de 30 dias SEM portaria localizada até o
    corte (`gerado_em` do arquivo de decretos). Função pura; sem decretos, {}."""
    mun = [m for m in ((dec or {}).get("municipios") or {}).values() if m.get("decreto")]
    ref = _data((dec or {}).get("gerado_em"))
    if not mun or not ref: return {}
    com_recurso = {str(i).zfill(7) for i, v in ((rec or {}).get("municipios") or {}).items() if any(_data(a.get("data")) for a in (v or {}).get("atos") or [])}
    def pendente(m):
        r = _data(m.get("primeiro_reconhecimento"))
        return bool(m.get("reconhecido") and r and str(m.get("ibge")).zfill(7) not in com_recurso and (ref - r).days > DIAS_PENDENCIA)
    return {"referencia": ref.strftime("%d/%m/%Y"), "n_decretaram": len(mun), "n_reconhecidos": sum(1 for m in mun if m.get("reconhecido")),
            "n_com_recurso": defesa_civil_ciclo(rec, corte)["municipios_ciclo"],
            "n_com_recurso_e_decretaram": sum(1 for m in mun if str(m.get("ibge")).zfill(7) in com_recurso), "n_30d": sum(1 for m in mun if pendente(m)),
            "dias_pendencia": DIAS_PENDENCIA}


def serie_mensal(rec: dict, fns_mun: dict, corte: datetime) -> dict:
    """Série mensal do MESMO universo do mapa e dos cartões `defesa_civil_ciclo` e `sus_emergencia` (mesmas
    funções de seleção): defesa civil = autorizado por portaria, no mês da portaria; SUS = repasse de emergência
    do mês fechado do FNS. `saude` é None onde não há dado do FNS (junho, fora do recorte; meses ainda não
    coletados): ausência não é zero. O mês do corte é `parcial`. Função pura."""
    dc = {}
    for _, a, d in atos_do_ciclo(rec, corte):
        k = d.strftime("%Y%m"); dc[k] = dc.get(k, 0.0) + float(a.get("valor_autorizado") or 0.0)
    fns = (fns_mun or {}).get("municipios") or {}
    sus = {}
    for v in fns.values():
        for k, x in emergencia_por_mes(v).items(): sus[k] = sus.get(k, 0.0) + x
    coletados = {k for v in fns.values() for k in emergencia_por_mes(v)}   # meses do FNS dentro do recorte
    if not dc and not fns: return {}
    ini, fim = INICIO_CICLO.strftime("%Y%m"), corte.strftime("%Y%m")
    meses, k = [], ini
    while k <= fim:
        meses.append({"mes": k, "defesa_civil": round(dc.get(k, 0.0), 2),
                      "saude": round(sus.get(k, 0.0), 2) if k in coletados else None,
                      "parcial": k == fim})
        k = (datetime(int(k[:4]), int(k[4:]), 1) + timedelta(days=32)).strftime("%Y%m")
    return {"meses": meses, "saude_desde": (min(sus) if sus else None), "saude_ultimo_mes": max(coletados) if coletados else None,
            "total_defesa_civil": round(sum(dc.values()), 2), "total_saude": round(sum(sus.values()), 2)}


def montar(mps: dict, transf: dict, rec: dict, comp: dict, corte: datetime,
           fns_mun: dict | None = None, ref: list | None = None, dec: dict | None = None) -> dict:
    cartoes = [cartao_pago(mps), cartao_transferido(transf), cartao_resposta(rec, corte),
               cartao_atos(mps, corte)]
    return {"_governanca": "Gerado por gerar_financiamento_semana.py. Cada cartão traz o recorte "
                           "que a fonte permite: mês fechado onde a fonte publica por mês, sete "
                           "dias onde o ato tem data. Lacuna é declarada, nunca zero.",
            "corte": corte.strftime("%d/%m/%Y"),
            "janela_dias": JANELA,
            "cartoes": cartoes,
            "topo": topo(mps, comp, rec, fns_mun, corte),
            "mes_a_mes": mes_a_mes(mps),
            "mapa": mapa(rec, fns_mun, ref, corte),
            "serie_mensal": serie_mensal(rec, fns_mun, corte),
            "funil_defesa_civil": funil_defesa_civil(dec, rec, corte)}


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

    ok("mes legivel", mes_legivel("202608") == "agosto de 2026")
    ok("mes malformado nao levanta", mes_legivel("20260") == "20260" and mes_legivel("202699") == "202699")
    ok("mes parcial nao e fechado",
       ultimo_mes_fechado({"202607": {"soma": 1}, "202608": {"soma": 2, "parcial": True}}) == "202607")
    ok("sem mes fechado devolve None", ultimo_mes_fechado({"202608": {"parcial": True}}) is None)
    ok("meses_lidos ausente nao levanta", ultimo_mes_fechado(None) is None)

    corte = datetime(2026, 10, 2)
    ok("janela pega os dois formatos de data",
       len(na_janela([{"data": "2026-09-30"}, {"data": "28/09/2026"}, {"data": "2026-01-01"},
                      {"data": "nao-e-data"}], corte)) == 2)

    c = cartao_pago({"mps": [{"execucao": {"status": "coletado", "pago": 10.0,
                                           "por_mes": {"202607": {"pago": 4.0},
                                                       "202608": {"pago": 6.0}}}}]})
    ok("pago usa o ultimo mes quando ha quebra", c["valor"] == 6.0 and "agosto" in c["periodo"])
    c = cartao_pago({"mps": [{"execucao": {"status": "coletado", "pago": 10.0,
                                           "meses": ["202606", "202607"]}}]})
    ok("pago cai no acumulado sem quebra, e NAO vira sem dado",
       c["valor"] == 10.0 and not c["sem_coleta"] and "junho" in c["periodo"])
    ok("pago sem coleta declara lacuna", cartao_pago({"mps": [{}]})["sem_coleta"] is True)
    c = cartao_pago({"mps": [{"execucao": {"status": "coletado", "pago": 10.0,
                                           "por_mes": {"202608": {"pago": 6.0},
                                                       "202609": {"pago": 1.0, "parcial": True}}}}]})
    ok("pago ignora o mes parcial (A6-13)", c["valor"] == 6.0 and "agosto" in c["periodo"])
    c = cartao_pago({"mps": [{"execucao": {"status": "coletado", "pago": 4.0,
                                           "por_mes": {"202608": {"pago": 4.0}}}},
                             {"execucao": {"status": "coletado", "pago": None,
                                           "por_mes": {"202608": {"pago": None}}}}]})
    ok("pago vazio fica fora da soma (A6-22)", c["valor"] == 4.0)
    c = cartao_pago({"mps": [{"execucao": {"status": "coletado", "pago": None,
                                           "por_mes": {"202608": {"pago": None}}}}]})
    ok("pago todo vazio e lacuna, nunca zero (A6-22)", c["valor"] is None and not c["sem_coleta"])
    ok("corte vem do meta.json (A3-20)",
       corte_do_dado({"corte": "02/10/2026"}).isoformat() == "2026-10-02"
       and corte_do_dado({"corte": "2026-10-03"}).isoformat() == "2026-10-03")

    c = cartao_transferido({"meses_lidos": {"202608": {"soma": 5.5, "municipios_casados": 3},
                                            "202609": {"soma": 1.0, "parcial": True}}})
    ok("transferido ignora o mes parcial", c["valor"] == 5.5 and "agosto" in c["periodo"])
    ok("transferido sem mes fechado declara lacuna",
       cartao_transferido({"meses_lidos": {}})["sem_coleta"] is True)

    base = {"municipios": {"1": {"atos": [
        {"acao": "resposta", "data": "2026-09-30", "valor_autorizado": 100.0, "municipio": "X", "uf": "SP"},
        {"acao": "recuperacao", "data": "2026-09-30", "valor_autorizado": 900.0, "municipio": "X", "uf": "SP"},
        {"acao": "resposta", "data": "2026-01-02", "valor_autorizado": 50.0, "municipio": "Y", "uf": "BA"}]}}}
    c = cartao_resposta(base, corte)
    ok("resposta soma so resposta e so a janela", c["valor"] == 100.0 and "1 munic" in (c["detalhe"] or ""))
    ok("resposta sem coleta declara lacuna", cartao_resposta({}, corte)["sem_coleta"] is True)

    c = cartao_atos({"mps": [{"publicada_em": "29/09/2026", "numero": "MP 1"},
                             {"publicada_em": "01/02/2026", "numero": "MP 2"}]}, corte)
    ok("atos conta so a janela, pela data de publicacao da MP", c["valor"] == 1 and c["detalhe"] == "MP 1")
    ok("atos com MP sem data declara a CLASSE, nao `sem coleta`",
       cartao_atos({"mps": [{"numero": "MP sem data"}]}, corte)["classe"] == "sem_data_na_origem"
       and cartao_atos({"mps": [{"numero": "MP sem data"}]}, corte)["valor"] is None)
    ok("atos lista vazia e ZERO, nao lacuna", cartao_atos({"mps": []}, corte)["valor"] == 0)
    ok("atos sem arquivo declara lacuna", cartao_atos({}, corte)["sem_coleta"] is True
       and "classe" not in cartao_atos({}, corte))
    c = cartao_resposta(base, corte)
    ok("resposta traz o total do ciclo ao lado da janela (todas as acoes, desde 29/06)",
       c["valor_ciclo"] == 1000.0 and c["municipios_ciclo"] == 1 and c["municipios_semana"] == 1
       and c["por_acao_ciclo"] == {"recuperacao": 900.0, "resposta": 100.0})
    MPS = {"mps": [{"id": "a", "numero": "MP 1.367/2026", "valor": 300.0,
                    "execucao": {"status": "coletado", "pago": 100.0, "meses_parciais": ["202610"],
                                 "por_mes": {"202609": {"pago": 60.0}, "202610": {"pago": 40.0, "parcial": True}}},
                    "forma_de_aplicacao": {"status": "coletado", "por_modalidade": {"aplicados diretamente pela União": 90.0}}}]}
    COMP = {"itens": [{"valor_total": 1000.0, "instrumento": "Anúncio; MP nº 1.367/2026"}, {"valor_total": 20.0, "instrumento": "Fundo estadual"},
                      {"valor_total": None, "instrumento": "Lei"}]}
    FNS = {"municipios": {"1": {"meses": {"202601": [5, 0], "202606": [5, 7], "202609": [5, 2]}, "emergencia": 9.0}, "2": {"meses": {}, "emergencia": 0.0}}}
    t = {x["id"]: x for x in topo(MPS, COMP, base, FNS, corte)}
    ok("topo: anunciado nao soma o anuncio que contem a MP", t["anunciado_atos"]["valor"] == 320.0 and t["anunciado_atos"]["detalhe"] == "2 origens" and t["anunciado_atos"]["n_atos"] == 2)
    ok("topo: pago e variacao do mes parcial", t["pago_ate_agora"]["valor"] == 100.0 and t["pago_ate_agora"]["variacao_mes"] == 40.0)
    ok("topo: gasto direto em % do pago", t["gasto_direto_uniao"]["valor"] == 90.0)
    ok("topo: defesa civil desde 29/06 e SUS de emergencia com municipios",
       t["defesa_civil_ciclo"]["valor"] == 1000.0 and t["sus_emergencia"]["valor"] == 2.0 and t["sus_emergencia"]["municipios"] == 1)
    ok("SUS: repasse de junho (antes de 29/06) fica fora do total e do mapa",
       t["sus_emergencia"]["periodo"] == "desde 29/06/2026" and emergencia_no_ciclo(FNS["municipios"]["1"]) == 2.0)
    ok("topo sem dado declara lacuna em cada cartao", all(x["sem_coleta"] for x in topo({}, {}, {}, {}, corte)))
    ok("mes a mes leva o risco que o ato declara (ou None)", mes_a_mes(MPS)[0]["risco_declarado"] is None)
    ok("mes a mes marca o parcial", mes_a_mes(MPS)[0]["meses"] == [{"mes": "202609", "pago": 60.0, "parcial": False},
                                                                  {"mes": "202610", "pago": 40.0, "parcial": True}])
    base["municipios"]["1"]["atos"][0]["portaria"] = "9"
    pts = mapa(base, FNS, [{"codigo_ibge": 1, "lat": -1.0, "lon": -2.0, "nome": "X", "uf": "SP"}], corte)
    ok("mapa: um ponto por municipio e origem, com sede; sem sede fica marcado",
       [(p["origem"], p["valor"], p["lat"]) for p in pts] == [("defesa_civil", 1000.0, -1.0), ("saude", 2.0, -1.0)]
       and mapa(base, {}, [], corte)[0]["sem_sede"] is True)

    sm = serie_mensal(base, FNS, corte)
    ok("serie mensal: soma = cartao defesa civil + SUS = mapa; junho do SUS fora do recorte (None, nao zero)",
       sm["total_defesa_civil"] == t["defesa_civil_ciclo"]["valor"] == sum(p["valor"] for p in pts if p["origem"] == "defesa_civil")
       and sm["total_saude"] == t["sus_emergencia"]["valor"] == sum(p["valor"] for p in pts if p["origem"] == "saude")
       and sm["meses"][0]["saude"] is None and sm["meses"][-1]["parcial"] is True and serie_mensal({}, {}, corte) == {})
    DEC = {"gerado_em": "25/10/2026", "municipios": {"a": {"ibge": "1", "decreto": True, "reconhecido": True, "primeiro_reconhecimento": "01/09/2026"},
           "b": {"ibge": "2", "decreto": True, "reconhecido": True, "primeiro_reconhecimento": "01/09/2026"},
           "c": {"ibge": "3", "decreto": True, "reconhecido": True, "primeiro_reconhecimento": "20/10/2026"},
           "d": {"ibge": "4", "decreto": True, "reconhecido": False, "primeiro_reconhecimento": None}}}
    ok("funil: 4 decretaram, 3 reconhecidos, 1 com recurso, 1 pendente ha mais de 30 dias (recente e sem reconhecimento fora)",
       funil_defesa_civil(DEC, base, corte) == {"referencia": "25/10/2026", "n_decretaram": 4, "n_reconhecidos": 3, "n_com_recurso": 1, "n_com_recurso_e_decretaram": 1, "n_30d": 1, "dias_pendencia": 30}
       and funil_defesa_civil({}, base, corte) == {})
    d = montar({}, {}, {}, {}, corte)
    ok("montar devolve os quatro cartoes", [x["id"] for x in d["cartoes"]] == [
        "pago_periodo_mp", "transferido_municipios_periodo", "resposta_liberado_semana",
        "atos_federais_semana"])
    ok("trava estrutural: o gerador nao escreve no banco", ARQUIVO not in BANCO_PROIBIDO)
    # Trava estrutural: o autoteste le o PROPRIO codigo-fonte e confere que ha uma escrita so,
    # a de ARQUIVO, e que nenhum arquivo do banco aparece como destino de gravacao.
    fonte = pathlib.Path(__file__).read_text(encoding="utf-8")
    escritas = [l.strip() for l in fonte.splitlines()
                if l.strip().startswith("gravar(")]
    ok("trava estrutural: uma escrita so, e e ARQUIVO",
       len(escritas) == 1 and escritas[0].startswith("gravar(ARQUIVO"))
    ok("trava estrutural: nenhum arquivo do banco como destino",
       not any(b in fonte.split("BANCO_PROIBIDO = ")[-1].split("}")[1] for b in BANCO_PROIBIDO))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else f"✓ AUTOTESTE OK — {len(_casos_contados)} casos, sem rede e sem escrita em data/.")
    return 1 if falhas else 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return _autoteste()
    # 10/10/2026 (A3-20): o corte vem do DADO (meta.json, o corte da edição), não do relógio da
    # parede — gerador de derivado que lê o relógio muda sozinho na virada do dia. Sem meta, o
    # relógio fixado da cadeia (SOURCE_DATE_EPOCH), como os demais geradores.
    corte = corte_do_dado(ler("meta.json", {}) or {})
    d = montar(ler("financiamento/mps_2026.json", {}) or {},
               ler("financiamento/municipios/transferencias_uniao.json", {}) or {},
               ler("resposta/recursos_liberados.json", {}) or {},
               ler("financiamento/compromissos_federais.json", {}) or {},
               datetime(corte.year, corte.month, corte.day),
               ler("financiamento/municipios/fns_municipios_2026.json", {}) or {},
               ler("municipios_ibge_referencia.json", []) or [],
               ler("resposta/municipios_decretados.json", {}) or {})
    gravar(ARQUIVO, d)
    for c in d["cartoes"]:
        print(f"  {c['id']}: " + ("sem coleta — " + str(c['detalhe']) if c["sem_coleta"]
                                  else f"{c['valor']} ({c['periodo']})"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
