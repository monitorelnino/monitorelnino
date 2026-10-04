#!/usr/bin/env python3
"""
gerar_pacote_blog.py — o pacote de dados de onde a central escreve o texto da semana
=====================================================================================
`HANDOVER_blog_rotina_semanal_04-10-2026.md`, item 1.

POR QUE EXISTE UM PACOTE, E NÃO UMA CONSULTA LIVRE
---------------------------------------------------
A central escreve dois textos por semana, e o verificador do publicador exige que **todo número do
corpo esteja no pacote**. O pacote é, então, a lista fechada do que se pode afirmar naquela semana —
com fonte, URL e data de consulta em cada fato. Número fora do pacote não entra no texto; se faltar
um fato, a central o acrescenta ao pacote, com fonte, marcado como adição dela.

O que o pacote NÃO traz, por decisão da editoria: ranking, razão entre números, "maior/menor",
percentual de variação. Só contagens, somas, listas em ordem alfabética, datas e documentos. A
variação entre semanas aparece como **par de valores**, nunca como percentual — a comparação é do
leitor, não nossa.

Dado mais velho que nove dias não entra em `fatos`: vai para `lacunas`, com "sem atualização desde".
Isso é o que impede o texto de afirmar, no presente, o que a coleta não sustenta.

DUAS LINHAS, DUAS SEMANAS
-------------------------
  legal  — semana de domingo a sábado já encerrada; gerado no domingo às 06:00 de Brasília.
  saude  — última semana epidemiológica fechada; gerado na quarta às 06:00.

USO
  python3 gerar_pacote_blog.py --autoteste
  python3 gerar_pacote_blog.py --linha legal --semana 2026-10-03
  python3 gerar_pacote_blog.py --linha saude
  python3 gerar_pacote_blog.py --linha legal --saida /caminho   # padrão: robo-registro/blog/pacotes
"""
from __future__ import annotations

import collections
import datetime as dt
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

LINHAS = ("legal", "saude")
DIAS_DE_VALIDADE = 9
SAIDA_PADRAO = RAIZ.parent / "robo-registro" / "blog" / "pacotes"

REGIOES = {
    "Norte": ("AC", "AM", "AP", "PA", "RO", "RR", "TO"),
    "Nordeste": ("AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"),
    "Centro-Oeste": ("DF", "GO", "MT", "MS"),
    "Sudeste": ("ES", "MG", "RJ", "SP"),
    "Sul": ("PR", "RS", "SC"),
}
BOLETIM_1 = {
    "texto": ("Boletim nº 1 do ciclo, de 29 de junho de 2026: previsão de seca e fogo no Norte e no "
              "Nordeste, chuva forte no Sul e calor no Sudeste até março de 2027."),
    "fonte": "Boletim nº 1 do ciclo El Niño 2026/2027",
    "url": "https://monitorelnino.com.br/METODOLOGIA.pdf",
}


# ---------------------------------------------------------------- datas e semanas (funções puras)
def semana_encerrada(hoje: dt.date) -> tuple:
    """(domingo, sábado) da última semana FECHADA. Função pura.

    A semana do projeto é domingo a sábado, a mesma da semana epidemiológica. Gerado num domingo, o
    pacote fala da semana que terminou no sábado anterior — nunca da que está correndo, porque
    número de semana aberta muda depois de o texto ser escrito.
    """
    dias_desde_domingo = (hoje.weekday() + 1) % 7
    domingo_desta = hoje - dt.timedelta(days=dias_desde_domingo)
    sabado = domingo_desta - dt.timedelta(days=1)
    return sabado - dt.timedelta(days=6), sabado


def para_iso(data_br: str) -> str | None:
    """"dd/mm/aaaa" → "aaaa-mm-dd". Função pura; devolve None no que não é data."""
    try:
        d, m, a = str(data_br).strip().split("/")
        if len(a) == 4 and d.isdigit() and m.isdigit():
            return f"{a}-{m.zfill(2)}-{d.zfill(2)}"
    except (ValueError, AttributeError):
        return None
    return None


def dentro_da_semana(data_br: str, inicio: dt.date, fim: dt.date) -> bool:
    """A data está na semana do pacote? Função pura."""
    iso = para_iso(data_br)
    return bool(iso and inicio.isoformat() <= iso <= fim.isoformat())


def esta_velho(carimbo: str, hoje: dt.date, dias=DIAS_DE_VALIDADE) -> bool:
    """O carimbo passou da validade? Função pura. Sem carimbo legível, trata-se como velho."""
    iso = para_iso(str(carimbo).split(" ")[0]) or (str(carimbo)[:10] if str(carimbo)[:4].isdigit()
                                                   else None)
    if not iso:
        return True
    try:
        return (hoje - dt.date.fromisoformat(iso)).days > dias
    except ValueError:
        return True


def regiao_da_uf(uf: str) -> str | None:
    """A região da UF. Função pura."""
    for nome, ufs in REGIOES.items():
        if str(uf).upper() in ufs:
            return nome
    return None


def numero_pt(valor) -> str:
    """Inteiro no formato que o texto escreve (1.234). Função pura."""
    if isinstance(valor, bool) or valor is None:
        return ""
    if isinstance(valor, int):
        return f"{valor:,}".replace(",", ".")
    return str(valor)


def data_por_extenso(iso: str) -> str:
    """"2026-09-27" → "27 de setembro de 2026". Função pura."""
    MESES = ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
             "setembro", "outubro", "novembro", "dezembro")
    try:
        d = dt.date.fromisoformat(iso)
    except (ValueError, TypeError):
        return ""
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def numeros_permitidos(fatos: list) -> list:
    """Todas as formas em que o texto pode escrever cada valor e cada data dos fatos. Função pura.

    O verificador compara o corpo do texto com esta lista, então ela tem de conter o número em
    TODAS as grafias aceitáveis: inteiro cru, com ponto de milhar, a data em ISO, em dd/mm/aaaa e
    por extenso. Faltar uma grafia faria o verificador reprovar um texto correto — que é o pior
    defeito possível num portão de texto.
    """
    fora = set()
    for f in fatos or []:
        v = f.get("valor")
        if isinstance(v, int) and not isinstance(v, bool):
            fora.add(str(v))
            fora.add(numero_pt(v))
        elif isinstance(v, float):
            fora.add(("%g" % v).replace(".", ","))
        elif isinstance(v, str) and v.strip():
            fora.add(v.strip())
        for chave in ("data", "data_consulta"):
            d = str(f.get(chave) or "")
            iso = d if (len(d) == 10 and d[:4].isdigit()) else para_iso(d)
            if iso:
                fora.add(iso)
                a, m, dd = iso.split("-")
                fora.add(f"{dd}/{m}/{a}")
                fora.add(data_por_extenso(iso))
                fora.add(str(int(dd)))
                fora.add(a)
    return sorted(x for x in fora if x)


def fato(ident: str, secao: str, texto: str, valor=None, unidade=None, fonte=None, url=None,
         data=None, data_consulta=None, uf=None, municipio=None) -> dict:
    """Um fato do pacote, no formato do handover. Função pura."""
    return {"id": ident, "secao": secao, "texto": texto, "valor": valor, "unidade": unidade,
            "uf": uf, "municipio": municipio, "fonte": fonte, "url": url,
            "data": data, "data_consulta": data_consulta}


# ---------------------------------------------------------------- o pacote Legal e financiamento
def fatos_de_emergencia(atos: list, inicio: dt.date, fim: dt.date, hoje: dt.date) -> list:
    """Seção 2 do pacote Legal: reconhecimentos e decretos da semana. Função pura.

    Conta por região, por UF e por tipo de evento (COBRADE), e conta à parte os atos em que a fonte
    não informa o tipo — que é o número que o texto precisa dizer, e que faltava até 04/10.
    """
    hoje_iso = hoje.isoformat()
    na_semana = [e for e in atos or []
                 if dentro_da_semana(e.get("data_reconhecimento") or "", inicio, fim)]
    fatos = [fato("reconhecimentos_semana", "emergencias",
                  "municípios com situação de emergência reconhecida pelo governo federal na semana",
                  len(na_semana), "municípios",
                  "Diário Oficial da União (portarias da Secretaria Nacional de Proteção e Defesa "
                  "Civil) e S2iD", "https://www.gov.br/mdr/", fim.isoformat(), hoje_iso)]

    por_regiao = collections.Counter()
    por_uf = collections.Counter()
    por_tipo = collections.Counter()
    sem_tipo = 0
    for e in na_semana:
        r = regiao_da_uf(e.get("uf") or "")
        if r:
            por_regiao[r] += 1
        if e.get("uf"):
            por_uf[str(e["uf"]).upper()] += 1
        bruto = str(e.get("desastre") or "").strip()
        if bruto:
            por_tipo[bruto.split(" - ")[0]] += 1
        else:
            sem_tipo += 1
    for nome in sorted(por_regiao):
        fatos.append(fato(f"reconhecimentos_regiao_{nome.lower()}", "emergencias",
                          f"reconhecimentos na região {nome}", por_regiao[nome], "municípios",
                          "Diário Oficial da União e S2iD", None, fim.isoformat(), hoje_iso))
    for uf in sorted(por_uf):
        fatos.append(fato(f"reconhecimentos_uf_{uf}", "emergencias",
                          f"reconhecimentos em {uf}", por_uf[uf], "municípios",
                          "Diário Oficial da União e S2iD", None, fim.isoformat(), hoje_iso,
                          uf=uf))
    for tipo in sorted(por_tipo):
        fatos.append(fato(f"reconhecimentos_tipo_{tipo.lower().replace(' ', '_')}", "emergencias",
                          f"reconhecimentos com o tipo de evento {tipo} na classificação oficial",
                          por_tipo[tipo], "municípios", "S2iD (classificação COBRADE)", None,
                          fim.isoformat(), hoje_iso))
    fatos.append(fato("reconhecimentos_sem_tipo", "emergencias",
                      "reconhecimentos em que o registro federal não informa o tipo de evento",
                      sem_tipo, "municípios", "S2iD", None, fim.isoformat(), hoje_iso))

    datas = sorted(x for x in (para_iso(e.get("data_decreto_municipal") or "")
                               for e in na_semana) if x)
    if datas:
        fatos.append(fato("decreto_municipal_mais_antigo", "emergencias",
                          "decreto municipal mais antigo entre os reconhecidos na semana", None,
                          None, "S2iD", None, datas[0], hoje_iso))
        fatos.append(fato("decreto_municipal_mais_recente", "emergencias",
                          "decreto municipal mais recente entre os reconhecidos na semana", None,
                          None, "S2iD", None, datas[-1], hoje_iso))

    por_municipio = sorted({(str(e.get("nome") or ""), str(e.get("uf") or "")) for e in na_semana})
    for nome, uf in por_municipio:
        if not nome:
            continue
        fatos.append(fato(f"reconhecido_{uf}_{nome}".replace(" ", "_"), "emergencias",
                          f"{nome} ({uf}) teve emergência reconhecida na semana", None, None,
                          "Diário Oficial da União e S2iD", None, fim.isoformat(), hoje_iso,
                          uf=uf, municipio=nome))
    return fatos


def fatos_de_planos(municipios: list, estados: list, inicio: dt.date, fim: dt.date,
                    hoje: dt.date) -> list:
    """Seção 1 do pacote Legal: planos e estruturas com ato na semana. Função pura."""
    hoje_iso = hoje.isoformat()
    fatos = []
    novos = [m for m in municipios or [] if dentro_da_semana(m.get("data") or "", inicio, fim)]
    fatos.append(fato("planos_municipais_semana", "planos",
                      "municípios cujo plano ou estrutura tem ato datado na semana",
                      len(novos), "municípios", "registros do MARÉ", None, fim.isoformat(),
                      hoje_iso))
    for m in sorted(novos, key=lambda x: (str(x.get("uf")), str(x.get("nome")))):
        fatos.append(fato(f"plano_{m.get('uf')}_{m.get('nome')}".replace(" ", "_"), "planos",
                          f"{m.get('nome')} ({m.get('uf')}): {m.get('documento') or 'documento'}",
                          None, None, m.get("fonte"), m.get("url"),
                          para_iso(m.get("data") or ""), hoje_iso,
                          uf=m.get("uf"), municipio=m.get("nome")))
    com_plano = [u for u in estados or [] if (u.get("instrumentos") or [])]
    fatos.append(fato("estados_com_instrumento", "planos",
                      "estados com instrumento estadual registrado", len(com_plano), "estados",
                      "registros do MARÉ", None, fim.isoformat(), hoje_iso))
    return fatos


def fatos_de_alertas(alertas: dict, hoje: dt.date) -> tuple:
    """Seção 3: instantâneo dos alertas. Devolve (fatos, lacunas). Função pura.

    Alerta é instantâneo, não semana: ele vale no momento da consulta, e é assim que entra. Coleta
    vencida vira lacuna declarada — nunca número apresentado como vigente.
    """
    carimbo = (alertas or {}).get("gerado_em") or ""
    if esta_velho(carimbo, hoje, dias=1):
        return [], [f"alertas do Cemaden e avisos do Inmet: sem atualização desde {carimbo or 'a última coleta registrada'}"]
    resumo = (alertas or {}).get("resumo") or {}
    hoje_iso = hoje.isoformat()
    return ([fato("alerta_cemaden", "alertas", "municípios sob alerta do Cemaden no momento da "
                  "consulta", resumo.get("municipios_cemaden"), "municípios", "Cemaden", None,
                  hoje_iso, hoje_iso),
             fato("aviso_inmet", "alertas", "municípios sob aviso do Inmet no momento da consulta",
                  resumo.get("municipios_inmet"), "municípios", "Inmet", None, hoje_iso,
                  hoje_iso)], [])


# ---------------------------------------------------------------- o pacote Saúde
def fatos_de_saude(topo: dict, hoje: dt.date) -> tuple:
    """As seções do pacote Saúde a partir do instantâneo do topo. Devolve (fatos, lacunas).

    Função pura. Cada número do topo já é o que a página publica — o pacote não recalcula nada: se
    recalculasse, o texto e a página poderiam divergir, e a página é o que o leitor confere.
    """
    hoje_iso = hoje.isoformat()
    fatos, lacunas = [], []
    for ident, chave, texto, fonte in (
            ("dengue_casos_se", "dengue_casos_se",
             "casos prováveis de dengue na última semana epidemiológica fechada",
             "Ministério da Saúde (Sinan)"),
            ("chik_casos_se", "chik_casos_se",
             "casos prováveis de chikungunya na última semana epidemiológica fechada",
             "Ministério da Saúde (Sinan)"),
            ("srag_internacoes", "srag_internacoes",
             "internações por síndrome respiratória aguda grave na última semana fechada",
             "Ministério da Saúde (Sivep-Gripe)")):
        # O topo guarda os cartões em LISTA, com `id` dentro de cada um — não num dicionário por
        # chave. Medido antes de confiar: a primeira versão deste script assumiu dicionário e
        # quebrou no primeiro pacote de saúde.
        cartoes = (topo or {}).get("cartoes") or []
        if isinstance(cartoes, dict):
            cartao = cartoes.get(chave) or {}
        else:
            cartao = next((c for c in cartoes if c.get("id") == chave), {})
        valor = cartao.get("valor")
        if valor is None or cartao.get("sem_coleta"):
            lacunas.append(f"{texto}: sem coleta na data do pacote")
            continue
        fatos.append(fato(ident, "saude_semana", texto, valor, "casos", fonte,
                          cartao.get("url"), cartao.get("referencia") or hoje_iso, hoje_iso))
    fatos.append(fato("parcialidade", "saude_parcialidade",
                      "as semanas mais recentes são parciais e sobem com notificações atrasadas",
                      None, None, "Ministério da Saúde", None, hoje_iso, hoje_iso))
    fatos.append(fato("sem_relacao_el_nino", "saude_parcialidade",
                      "os números não indicam relação com o El Niño", None, None,
                      "nota metodológica do MARÉ", None, hoje_iso, hoje_iso))
    return fatos, lacunas


# ---------------------------------------------------------------- montagem
def montar(linha: str, inicio: dt.date, fim: dt.date, fatos: list, lacunas: list,
           hoje: dt.date) -> dict:
    """O pacote inteiro, no formato do handover. Função pura."""
    ident = f"{fim.isoformat()}_{linha}"
    # 04/10/2026: o contexto do Boletim nº 1 entra em `fatos` E conta para `numeros_permitidos`.
    # A primeira versão o acrescentava depois do cálculo, e o verificador reprovou "2027" no texto
    # aprovado — a data que está no próprio contexto ("até março de 2027"). Pacote incompleto se
    # corrige no gerador, nunca no texto: foi a regra que a editoria fixou, e ela pegou na
    # primeira execução real.
    todos = list(fatos) + [fato("boletim_1", "contexto", BOLETIM_1["texto"], None, None,
                                BOLETIM_1["fonte"], BOLETIM_1["url"], "2026-06-29",
                                hoje.isoformat()),
                           fato("ciclo_fim", "contexto",
                                "o ciclo previsto no Boletim nº 1 vai até março de 2027", None,
                                None, BOLETIM_1["fonte"], BOLETIM_1["url"], "2027-03-31",
                                hoje.isoformat())]
    return {"pacote": ident,
            "semana": {"inicio": inicio.isoformat(), "fim": fim.isoformat()},
            "gerado_em": hoje.isoformat(),
            "fatos": todos,
            "numeros_permitidos": numeros_permitidos(todos),
            "lacunas": lacunas}


def em_markdown(pacote: dict) -> str:
    """O pacote em texto, para a central ler. Função pura."""
    s = (pacote or {}).get("semana") or {}
    linhas = [f"# Pacote {pacote.get('pacote')}", "",
              f"Semana de {s.get('inicio')} a {s.get('fim')} · gerado em "
              f"{pacote.get('gerado_em')}", "",
              "Só o que está aqui pode entrar no texto. Número fora do pacote não entra; se "
              "faltar um fato, acrescente-o com fonte e URL, marcado \"adição da central\".", ""]
    por_secao = collections.OrderedDict()
    for f in pacote.get("fatos") or []:
        por_secao.setdefault(f.get("secao") or "outros", []).append(f)
    for secao, itens in por_secao.items():
        linhas += [f"## {secao}", ""]
        for f in itens:
            valor = "" if f.get("valor") is None else f"**{numero_pt(f['valor'])}** "
            data = f" · {f['data']}" if f.get("data") else ""
            fonte = f" · {f['fonte']}" if f.get("fonte") else ""
            linhas.append(f"- {valor}{f.get('texto')}{data}{fonte}")
        linhas.append("")
    if pacote.get("lacunas"):
        linhas += ["## lacunas declaradas", ""]
        linhas += [f"- {x}" for x in pacote["lacunas"]] + [""]
    return "\n".join(linhas)


def _autoteste() -> int:
    falhas = []

    def ok(nome, cond):
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    d = dt.date
    ok("domingo devolve a semana que fechou no sábado anterior",
       semana_encerrada(d(2026, 10, 4)) == (d(2026, 9, 27), d(2026, 10, 3)))
    ok("quarta devolve a mesma semana fechada",
       semana_encerrada(d(2026, 10, 7)) == (d(2026, 9, 27), d(2026, 10, 3)))
    ok("sábado ainda fala da semana anterior, porque a dele não fechou",
       semana_encerrada(d(2026, 10, 3)) == (d(2026, 9, 20), d(2026, 9, 26)))

    ok("data brasileira vira ISO", para_iso("27/09/2026") == "2026-09-27")
    ok("data com um dígito é normalizada", para_iso("7/9/2026") == "2026-09-07")
    ok("texto que não é data devolve None", para_iso("sem data") is None)
    ok("dentro da semana é inclusivo nas duas pontas",
       dentro_da_semana("27/09/2026", d(2026, 9, 27), d(2026, 10, 3))
       and dentro_da_semana("03/10/2026", d(2026, 9, 27), d(2026, 10, 3)))
    ok("fora da semana fica fora",
       not dentro_da_semana("04/10/2026", d(2026, 9, 27), d(2026, 10, 3)))

    ok("carimbo de hoje não está velho", not esta_velho("04/10/2026", d(2026, 10, 4)))
    ok("carimbo de dez dias está velho", esta_velho("24/09/2026", d(2026, 10, 4)))
    ok("sem carimbo legível, trata-se como velho", esta_velho("", d(2026, 10, 4)))

    ok("a região da UF é a do IBGE", regiao_da_uf("sc") == "Sul" and regiao_da_uf("BA") == "Nordeste")
    ok("UF inexistente não ganha região", regiao_da_uf("XX") is None)
    ok("inteiro sai com ponto de milhar", numero_pt(8146) == "8.146")
    ok("data por extenso é a do texto", data_por_extenso("2026-09-27") == "27 de setembro de 2026")

    f = [fato("x", "s", "t", 59, "municípios", "S2iD", None, "2026-10-03", "2026-10-04")]
    perm = numeros_permitidos(f)
    ok("o número entra cru e com ponto", "59" in perm)
    ok("a data entra em ISO, em dd/mm/aaaa e por extenso",
       "2026-10-03" in perm and "03/10/2026" in perm and "3 de outubro de 2026" in perm)
    ok("o ano entra, porque o texto o escreve", "2026" in perm)
    ok("o dia sem zero entra, porque o texto escreve '3 de outubro'", "3" in perm)

    atos = [{"uf": "SC", "nome": "Turvo", "data_reconhecimento": "30/09/2026",
             "desastre": "Chuvas Intensas - 1.3.2.1.4", "data_decreto_municipal": "24/08/2026"},
            {"uf": "RS", "nome": "Cerrito", "data_reconhecimento": "01/10/2026",
             "desastre": "Vendaval - 1.3.2.1.5", "data_decreto_municipal": "27/09/2026"},
            {"uf": "BA", "nome": "Cordeiros", "data_reconhecimento": "02/10/2026",
             "desastre": "", "data_decreto_municipal": "01/09/2026"},
            {"uf": "SP", "nome": "Fora", "data_reconhecimento": "10/10/2026",
             "desastre": "Seca - 1.4.1.2.0"}]
    fe = fatos_de_emergencia(atos, d(2026, 9, 27), d(2026, 10, 3), d(2026, 10, 4))
    por_id = {x["id"]: x for x in fe}
    ok("conta só os reconhecimentos da semana",
       por_id["reconhecimentos_semana"]["valor"] == 3)
    ok("conta por região", por_id["reconhecimentos_regiao_sul"]["valor"] == 2)
    ok("conta por UF", por_id["reconhecimentos_uf_SC"]["valor"] == 1)
    ok("conta por tipo da classificação oficial",
       por_id["reconhecimentos_tipo_vendaval"]["valor"] == 1)
    ok("conta à parte quem não tem tipo informado",
       por_id["reconhecimentos_sem_tipo"]["valor"] == 1)
    ok("a data do decreto mais antigo é a mais antiga da semana",
       por_id["decreto_municipal_mais_antigo"]["data"] == "2026-08-24")
    ok("cada município da semana é um fato nomeado",
       "reconhecido_SC_Turvo" in por_id and "reconhecido_SP_Fora" not in por_id)
    ok("nenhum fato traz razão, percentual ou ranking",
       not any(x in (f.get("texto") or "").lower()
               for f in fe for x in ("maior", "menor", "%", "mais rápido", "ranking")))

    fa, la = fatos_de_alertas({"gerado_em": "04/10/2026",
                               "resumo": {"municipios_cemaden": 16, "municipios_inmet": 2582}},
                              d(2026, 10, 4))
    ok("alerta fresco entra como fato", len(fa) == 2 and not la)
    fa2, la2 = fatos_de_alertas({"gerado_em": "01/10/2026", "resumo": {}}, d(2026, 10, 4))
    ok("alerta vencido vira lacuna declarada, não número",
       fa2 == [] and la2 and "sem atualização desde" in la2[0])

    fs, ls = fatos_de_saude({"cartoes": [{"id": "dengue_casos_se", "valor": 8146,
                                          "referencia": "2026-33"},
                                         {"id": "srag_internacoes", "sem_coleta": True}]},
                            d(2026, 10, 4))
    ok("cartão em dicionário também é aceito, para não depender do formato",
       fatos_de_saude({"cartoes": {"dengue_casos_se": {"valor": 1}}}, d(2026, 10, 4))[0][0]["valor"]
       == 1)
    ids = {x["id"] for x in fs}
    ok("o número de saúde vem do instantâneo do topo", "dengue_casos_se" in ids)
    ok("cartão sem coleta vira lacuna", any("sem coleta" in x for x in ls))
    ok("as duas frases obrigatórias de saúde estão no pacote",
       {"parcialidade", "sem_relacao_el_nino"} <= ids)

    pac = montar("legal", d(2026, 9, 27), d(2026, 10, 3), fe, [], d(2026, 10, 4))
    ok("o identificador do pacote é a data de fim e a linha",
       pac["pacote"] == "2026-10-03_legal")
    ok("o contexto do Boletim nº 1 entra em todo pacote",
       any(f["id"] == "boletim_1" for f in pac["fatos"]))
    ok("os números permitidos saem dos fatos", "3" in pac["numeros_permitidos"])
    ok("o contexto do ciclo conta para os números permitidos, e não só para a leitura",
       "2027" in pac["numeros_permitidos"])
    md = em_markdown(pac)
    ok("o markdown diz a regra à central em letra de forma",
       "Número fora do pacote não entra" in md)
    ok("o markdown não tem tabela nem cartão", "|---" not in md and "cartao" not in md)

    import dis
    nomes = set()
    for nome_obj, obj in list(globals().items()):
        if nome_obj in ("_autoteste", "main", "gerar"):
            continue
        codigo = getattr(obj, "__code__", None)
        if codigo is not None:
            nomes |= {i.argval for i in dis.get_instructions(codigo) if isinstance(i.argval, str)}
    ok("trava estrutural: as funções puras não escrevem",
       not ({"gravar", "write_text", "write_bytes"} & nomes))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else "✓ AUTOTESTE OK — 37 casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def gerar(linha: str, fim_da_semana: dt.date = None, saida: pathlib.Path = None) -> dict:
    """Monta e grava o pacote. Escreve em `robo-registro/blog/pacotes/`."""
    from coletores_base import ler, hoje_editorial
    hoje = hoje_editorial()
    if fim_da_semana:
        inicio, fim = fim_da_semana - dt.timedelta(days=6), fim_da_semana
    else:
        inicio, fim = semana_encerrada(hoje)

    if linha == "legal":
        atos = (ler("atos_resposta.json") or {}).get("eventos") or []
        municipios = ler("municipios.json") or []
        estados = (ler("estados.json") or {}).get("ufs") or []
        alertas = ler("alertas/vigentes.json") or {}
        fatos = fatos_de_planos(municipios, estados, inicio, fim, hoje)
        fatos += fatos_de_emergencia(atos, inicio, fim, hoje)
        fa, lacunas = fatos_de_alertas(alertas, hoje)
        fatos += fa
    else:
        topo = ler("saude_desfechos/topo_saude.json") or {}
        fatos, lacunas = fatos_de_saude(topo, hoje)

    pacote = montar(linha, inicio, fim, fatos, lacunas, hoje)
    destino = pathlib.Path(saida or SAIDA_PADRAO)
    destino.mkdir(parents=True, exist_ok=True)
    (destino / f"{pacote['pacote']}.json").write_text(
        json.dumps(pacote, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    (destino / f"{pacote['pacote']}.md").write_text(em_markdown(pacote), encoding="utf-8",
                                                    newline="\n")
    print(f"pacote {pacote['pacote']}: {len(pacote['fatos'])} fato(s) · "
          f"{len(pacote['numeros_permitidos'])} número(s) permitido(s) · "
          f"{len(pacote['lacunas'])} lacuna(s) → {destino}")
    return pacote


def main() -> int:
    argv = sys.argv[1:]
    if "--autoteste" in argv:
        return _autoteste()
    linha = argv[argv.index("--linha") + 1] if "--linha" in argv else "legal"
    if linha not in LINHAS:
        print(f"✗ linha {linha!r} desconhecida (use {' | '.join(LINHAS)})")
        return 1
    fim = None
    if "--semana" in argv:
        fim = dt.date.fromisoformat(argv[argv.index("--semana") + 1])
    saida = pathlib.Path(argv[argv.index("--saida") + 1]) if "--saida" in argv else None
    gerar(linha, fim, saida)
    return 0


if __name__ == "__main__":
    sys.exit(main())
