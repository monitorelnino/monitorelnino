#!/usr/bin/env python3
"""
coletar_boletim_df_arboviroses.py — arboviroses no Distrito Federal, a partir do Informativo Epidemiológico
semanal da SES-DF (10/09/2026)
====================================================================================================
Fonte: Secretaria de Saúde do Distrito Federal, "Informativo Epidemiológico – DIVEP | SVS | SES-DF —
Monitoramento dos casos de arboviroses no Distrito Federal" — PDF SEMANAL (Sinan Online / Sinan Net),
com dengue, chikungunya, Zika e febre amarela. Confirmado em 10/09/2026, lendo a íntegra do Nº 34
(SE 34/2026, dados extraídos em 31/08/2026, publicado em 03/09/2026).

Correção de registro: data/saude_desfechos/fontes_uf.json dizia "mensal (última sexta-feira do mês)".
A listagem oficial e o próprio PDF mostram que em 2026 a série é SEMANAL (Nº 1 a Nº 34 até 03/09/2026);
o texto "uma vez por mês" que ainda aparece na página é um resíduo de 2022. Registrado no CHANGELOG.

Diferença estrutural em relação ao coletor de MS: o DF é município-estado (IBGE 5300108) — não há tabela
por município. A granularidade sub-estadual é por REGIÃO DE SAÚDE (7 regiões + "Ignorado/Em branco").
O coletor é DEFENSIVO em dois pontos: (1) exige as 7 regiões nomeadas; (2) exige que a soma das regiões
(incluindo Ignorado) feche exatamente com o N de casos prováveis declarado na tabela — se não fechar,
recusa o resultado e registra lacuna, nunca publica parcial.

Os informes da SES-DF trazem o ACUMULADO do ano até a SE do informe (não a série semanal); a série semanal
o Monitor constrói sozinho, uma leitura por vez, a partir de agora. Ressalva de não-atribuição ao El Niño
em toda superfície, como o resto do §35/§36. Peso zero; nunca lido pelo motor.

Localização do informe: a página de listagem (acordeão por ano, painel de 2026) traz links relativos no
padrão /documents/d/saude/informativo_epidemiologico_se{NN}…-pdf, com sufixos imprevisíveis
(-27-01-26, __2_, _-df-2026…). O coletor raspa a listagem por regex e escolhe a maior SE; nunca adivinha
um link. Se a listagem não trouxer nenhum link nesse padrão, lacuna declarada.
  python coletar_boletim_df_arboviroses.py --autoteste
"""
import io, re, sys
from datetime import date
from pathlib import Path
from coletores_base import ler, gravar, buscar, registrar_lacuna, log_busca, rodar_autoteste

RAIZ = Path(__file__).resolve().parent
BASE = "https://www.saude.df.gov.br"
LISTAGEM = BASE + "/informes-dengue-chikungunya-zika-febre-amarela"
IBGE_DF = "5300108"
REGIOES = ("Leste", "Sul", "Norte", "Oeste", "Sudoeste", "Centro-Sul", "Central")
RESSALVA = ("O Monitor não atribui casos ao El Niño; dados da SES-DF (Sinan Online / Sinan Net), extraídos do "
            "Informativo Epidemiológico semanal em PDF — dados parciais e provisórios, sujeitos a alteração.")
MESES = {"janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3, "abril": 4, "maio": 5, "junho": 6, "julho": 7,
         "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12}


def _hoje():
    import datetime as _dt, json as _js
    try:
        a = _js.load(open(RAIZ / "data" / "meta.json", encoding="utf-8")).get("atualizado_em")
        return _dt.datetime.strptime(a, "%d/%m/%Y").date()
    except Exception:  # noqa: BLE001
        return _dt.date.today()


def extrair_link_mais_recente(html: str) -> tuple:
    """Acha, na listagem, o link do informe de maior SE. Função pura. (None, None) se não achar (nunca adivinha).
    Os hrefs são relativos e têm sufixo imprevisível; só a raiz 'informativo_epidemiologico_seNN' é estável."""
    achados = re.findall(r'href="(/documents/d/saude/informativo_epidemiologico_se(\d{1,2})[^"]*-pdf)"', html, re.I)
    if not achados:
        return None, None
    href, se = max(achados, key=lambda t: int(t[1]))
    return BASE + href, int(se)


def _n(s: str) -> int:
    return int(s.replace(".", "").replace(" ", ""))


def _cards(texto: str, rotulos: list) -> dict:
    """Lê o bloco de 'cards' (rótulo numa linha, número na seguinte) de um agravo. Cada rótulo é obrigatório;
    se faltar, ValueError — o coletor nunca adivinha."""
    out = {}
    for chave, padrao in rotulos:
        m = re.search(padrao + r"\s*\n\s*([\d.]+)\s*\n", texto, re.I)
        if not m:
            raise ValueError(f"card '{chave}' não encontrado")
        out[chave] = _n(m.group(1))
    return out


def parse_texto(texto: str) -> dict:
    """Extrai do texto do PDF: referência, período, data de extração, cards dos quatro agravos, tabelas por
    Região de Saúde (dengue e chikungunya) e monitoramento laboratorial. Função pura; ValueError se algo
    essencial não bater."""
    m = re.search(r"N[ºo°]\s*(\d{1,3})\s+Semana Epidemiol[óo]gica\s+(\d{1,2})/(\d{4})\s+(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})", texto, re.I)
    if not m:
        raise ValueError("cabeçalho 'Nº N Semana Epidemiológica SS/AAAA D de mês de AAAA' não encontrado")
    mes = MESES.get(m.group(5).lower())
    if mes is None:
        raise ValueError(f"mês não reconhecido: {m.group(5)}")
    referencia = {"numero": int(m.group(1)), "se": int(m.group(2)), "ano": int(m.group(3)),
                  "data_publicacao": date(int(m.group(6)), mes, int(m.group(4))).strftime("%d/%m/%Y")}
    mp = re.search(r"entre a Semana\s+Epidemiol[óo]gica \(SE\) (\d{1,2}) e a SE (\d{1,2}) de (\d{4}) \((\d{2}/\d{2}/\d{4}) a (\d{2}/\d{2}/\d{4})\)", texto, re.I)
    if not mp:
        raise ValueError("período 'entre a SE 01 e a SE NN de AAAA (dd/mm/aaaa a dd/mm/aaaa)' não encontrado")
    referencia.update({"se_inicio": int(mp.group(1)), "periodo_inicio": mp.group(4), "periodo_fim": mp.group(5)})
    me = re.search(r"qualificado pela [áa]rea t[ée]cnica respons[áa]vel em (\d{2}/\d{2}/\d{4})", texto, re.I)
    if not me:
        raise ValueError("data de extração do banco não encontrada")
    referencia["dados_extraidos_em"] = me.group(1)

    # --- dengue: cards + tabela por região ---
    sec_d = texto[texto.find("SITUAÇÃO EPIDEMIOLÓGICA DA DENGUE"): texto.find("SITUAÇÃO EPIDEMIOLÓGICA DA CHIKUNGUNYA")]
    if not sec_d:
        raise ValueError("seção da dengue não delimitada")
    dengue = _cards(sec_d, [("notificados", r"Notificados"), ("provaveis", r"Prov[áa]veis"), ("descartados", r"Descartados"),
                            ("inconclusivos", r"Inconclusivos"), ("em_investigacao", r"Em investiga[çc][ãa]o"),
                            ("confirmados_dengue", r"\nDengue"), ("sinais_de_alarme", r"Dengue com sinais\s*\n?\s*de alarme"),
                            ("dengue_grave", r"Dengue grave"), ("obitos", r"[ÓO]bitos")])
    ms = re.search(r"notificados ([\d.]+) casos suspeitos de dengue", sec_d, re.I)
    dengue["suspeitos_brutos"] = _n(ms.group(1)) if ms else None
    dengue["regioes"] = _tabela_regioes(sec_d, "Tabela 1")
    if dengue["regioes"]["total_declarado"] != dengue["provaveis"]:
        raise ValueError(f"dengue: N da Tabela 1 ({dengue['regioes']['total_declarado']}) ≠ card de prováveis ({dengue['provaveis']})")

    # --- chikungunya ---
    sec_c = texto[texto.find("SITUAÇÃO EPIDEMIOLÓGICA DA CHIKUNGUNYA"): texto.find("SITUAÇÃO EPIDEMIOLÓGICA DA ZIKA")]
    chik = _cards(sec_c, [("notificados", r"Notificados"), ("provaveis", r"Prov[áa]veis"), ("descartados", r"Descartados"),
                          ("confirmados", r"\nChikungunya"), ("inconclusivos", r"Inconclusivo"),
                          ("em_investigacao", r"Em investiga[çc][ãa]o"), ("obitos", r"[ÓO]bitos")])
    chik["regioes"] = _tabela_regioes(sec_c, "Tabela 2")
    if chik["regioes"]["total_declarado"] != chik["provaveis"]:
        raise ValueError(f"chikungunya: N da Tabela 2 ({chik['regioes']['total_declarado']}) ≠ card de prováveis ({chik['provaveis']})")

    # --- zika e febre amarela (só cards) ---
    sec_z = texto[texto.find("SITUAÇÃO EPIDEMIOLÓGICA DA ZIKA"): texto.find("SITUAÇÃO EPIDEMIOLÓGICA DA FEBRE AMARELA")]
    zika = _cards(sec_z, [("notificados", r"Notificados"), ("descartados", r"Descartados"), ("confirmados", r"\nZika"),
                          ("inconclusivos", r"Inconclusivo"), ("em_investigacao", r"Em investiga[çc][ãa]o"), ("obitos", r"[ÓO]bitos")])
    sec_f = texto[texto.find("SITUAÇÃO EPIDEMIOLÓGICA DA FEBRE AMARELA"): texto.find("Expediente")]
    fa = _cards(sec_f, [("notificados", r"Notificados"), ("descartados", r"Descartados"), ("confirmados", r"Febre Amarela"),
                        ("inconclusivos", r"Inconclusivo"), ("em_investigacao", r"Em investiga[çc][ãa]o"), ("obitos", r"[ÓO]bitos")])

    # --- laboratório (opcional: se o informe mudar, não derruba a leitura) ---
    lab = {}
    ml = re.search(r"realizados ([\d.]+) exames de PCR para dengue.*?([\d.]+) foram confirmados para dengue.*?positividade acumulada de ([\d,]+)%", texto, re.I | re.S)
    if ml:
        lab["dengue_pcr"] = {"exames": _n(ml.group(1)), "detectaveis": _n(ml.group(2)), "positividade_pct": float(ml.group(3).replace(",", "."))}
        ms_ = re.findall(r"DENV-(\d) \(n = (\d+)\)", texto)
        if ms_:
            lab["dengue_pcr"]["sorotipos"] = {f"DENV-{a}": int(b) for a, b in ms_}
    mc = re.search(r"realizados ([\d.]+) exames de PCR para chikungunya.*?([\d.]+) foram confirmados para chikungunya.*?positividade acumulada de ([\d,]+)%", texto, re.I | re.S)
    if mc:
        lab["chik_pcr"] = {"exames": _n(mc.group(1)), "detectaveis": _n(mc.group(2)), "positividade_pct": float(mc.group(3).replace(",", "."))}

    return {"referencia": referencia, "ibge": IBGE_DF, "dengue": dengue, "chikungunya": chik, "zika": zika, "febre_amarela": fa, "laboratorio": lab}


def _tabela_regioes(sec: str, rotulo_tabela: str) -> dict:
    """Tabela 'Região de Saúde | Casos prováveis (N = x) | Incidência'. Exige as 7 regiões e que a soma feche com N."""
    mt = re.search(re.escape(rotulo_tabela) + r".*?Casos prov[áa]veis \(N = ([\d.]+)\)", sec, re.I | re.S)
    if not mt:
        raise ValueError(f"{rotulo_tabela}: cabeçalho com 'N = …' não encontrado")
    total = _n(mt.group(1))
    linhas = re.findall(r"^\s*Regi[ãa]o (Leste|Sul|Norte|Oeste|Sudoeste|Centro-Sul|Central)\s+(\d[\d.]*)\s+([\d.,]+)\s*$", sec, re.M)
    regioes = {nome: {"casos_provaveis": _n(c), "incidencia_100k": float(i.replace(".", "").replace(",", "."))} for nome, c, i in linhas}
    faltam = [r for r in REGIOES if r not in regioes]
    if faltam:
        raise ValueError(f"{rotulo_tabela}: regiões ausentes {faltam}")
    mi = re.search(r"^\s*Ignorado(?:/Em branco)?\s+(\d[\d.]*)\s+([\d.,]+)\s*$", sec, re.M)
    ignorado = _n(mi.group(1)) if mi else 0
    soma = sum(v["casos_provaveis"] for v in regioes.values()) + ignorado
    if soma != total:
        raise ValueError(f"{rotulo_tabela}: soma das regiões ({soma}) ≠ N declarado ({total})")
    return {"total_declarado": total, "ignorado": ignorado, "por_regiao": regioes}


def coletar() -> int:
    hoje = _hoje()
    try:
        html = buscar(LISTAGEM, timeout=60).decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        registrar_lacuna("SES-DF (listagem de informes de arboviroses)", type(e).__name__, canal="site_estadual", camada=2, strings=[LISTAGEM])
        print("informe DF: listagem inacessível — lacuna declarada"); return 0
    pdf_url, se = extrair_link_mais_recente(html)
    if not pdf_url:
        registrar_lacuna("SES-DF (listagem de informes de arboviroses)", "nenhum link no padrão informativo_epidemiologico_seNN…-pdf", canal="site_estadual", camada=2, strings=[LISTAGEM])
        print("informe DF: nenhum link reconhecido na listagem — lacuna declarada"); return 0
    try:
        bruto = buscar(pdf_url, timeout=90)
        import pdfplumber
        with pdfplumber.open(io.BytesIO(bruto)) as pdf:
            texto = "\n".join((pg.extract_text() or "") for pg in pdf.pages)
    except Exception as e:  # noqa: BLE001
        registrar_lacuna(f"SES-DF informe {pdf_url[-40:]}", type(e).__name__, canal="site_estadual", camada=2, strings=[pdf_url])
        print("informe DF: falha ao ler o PDF — lacuna declarada"); return 0
    try:
        dados = parse_texto(texto)
    except ValueError as e:
        registrar_lacuna("SES-DF (formato do informe)", str(e)[:180], canal="site_estadual", camada=2, strings=[pdf_url])
        print(f"informe DF: {e} — coletor não adivinha; corrigir o parser e reexecutar"); return 0
    serie = ler("saude_desfechos/ses_df_arboviroses.json", {"_governanca": "Arboviroses no Distrito Federal (dengue, chikungunya, Zika, febre amarela), por Região de Saúde — lido do Informativo Epidemiológico semanal da SES-DF (Sinan Online / Sinan Net). " + RESSALVA + " Cada leitura é o ACUMULADO do ano até a SE do informe; a série semanal é construída pelo próprio Monitor a partir de 10/09/2026. DF é município-estado (IBGE 5300108): não há tabela municipal. Peso zero; nunca lido pelo motor.", "serie": {}})
    chave = f"{dados['referencia']['ano']}-{dados['referencia']['se']:02d}"
    serie.setdefault("serie", {})[chave] = dados
    serie["ultima_atualizacao"] = hoje.strftime("%d/%m/%Y"); serie["fonte_pdf_mais_recente"] = pdf_url
    gravar("saude_desfechos/ses_df_arboviroses.json", serie)
    d = dados["dengue"]
    log_busca("site_estadual", 2, [pdf_url], "registro", nivel="estadual", n_resultados=len(d["regioes"]["por_regiao"]),
              resultados=f"SES-DF: informe Nº {dados['referencia']['numero']} (SE {dados['referencia']['se']}/{dados['referencia']['ano']}) lido — dengue {d['provaveis']} prováveis / {d['confirmados_dengue'] + d['sinais_de_alarme'] + d['dengue_grave']} confirmados, chik {dados['chikungunya']['provaveis']} prováveis")
    print(f"informe DF: Nº {dados['referencia']['numero']} SE {dados['referencia']['se']}/{dados['referencia']['ano']} — dengue {d['provaveis']} prováveis, chik {dados['chikungunya']['provaveis']}, zika {dados['zika']['notificados']} notif., FA {dados['febre_amarela']['notificados']} notif.")
    return 0


# Texto REAL extraído do PDF do Nº 34 (SE 34/2026), lido em 10/09/2026 — só os trechos que o parser consome.
TEXTO_REAL_SE34 = """Nº 34 Semana Epidemiológica 34/2026 31 de agosto de 2026
 1
INFORMATIVO EPIDEMIOLÓGICO – DIVEP | SVS | SES - DF
Monitoramento dos casos de arboviroses no Distrito Federal
As informações sobre os vírus da dengue, chikungunya, Zika e febre amarela apresentadas neste 
Informe são referentes às notificações em residentes do Distrito Federal, ocorridas entre a Semana 
Epidemiológica (SE) 01 e a SE 34 de 2026 (04/01/2026 a 29/08/2026), disponíveis no Sistema de 
Informação de Agravos de Notificação – Sinan Online e Sinan Net. Os dados foram extraídos e o 
banco qualificado pela área técnica responsável em 31/08/2026. 
SITUAÇÃO EPIDEMIOLÓGICA DA DENGUE
Em 2026, até a SE 34, foram notificados 10.203 casos suspeitos de dengue em residentes do 
Distrito Federal, dos quais 9.312 atenderam aos critérios de definição de caso da metodologia 
adotada para este informativo epidemiológico. Destes, 3.264 foram classificados como casos 
prováveis, entre os quais 195 foram confirmados para a doença, incluindo 14 com sinais de alarme, 
após revisão e qualificação do banco de dados. 
Fonte: Sinan Online. Dados acessados em 31/08/2026.
Notificados
9.312
Prováveis
3.264
Descartados 
6.048
Inconclusivos
2.367
Em investigação
702
Dengue
181
Dengue com sinais 
de alarme
14
Dengue grave
0
Óbitos
0
Tabela 1. Número de casos prováveis e coeficiente de incidência (casos por 100 mil hab.) de dengue em 
residentes do Distrito Federal por Região de Saúde até a SE 34, Distrito Federal, 2026.
Região de Saúde Casos prováveis (N = 3.264) Incidência (por 100 mil hab.)
Região Leste 586 158,2
Região Sul 348 124,4
Região Norte 472 106,6
Região Oeste 549 104,4
Região Sudoeste 771 84,0
Região Centro-Sul 217 57,0
Região Central 101 24,2
Ignorado/Em branco 220 6,6
Fonte: Sinan Online. Dados acessados em 31/08/2026.
Em 2026, até a SE 34, foram realizados 9.284 exames de PCR para dengue em residentes do 
Distrito Federal. Dentre os exames realizados, 129 foram confirmados para dengue no território,
correspondendo a uma positividade acumulada de 1,39% em relação ao total processado.
Em relação ao monitoramento das cepas do vírus da dengue, entre as 129 amostras de PCR 
detectáveis, os sorotipos encontrados foram DENV-1 (n = 2), DENV-2 (n = 39) e DENV-3 (n = 68), 
com predominância do sorotipo DENV-3 (Figura 6).
SITUAÇÃO EPIDEMIOLÓGICA DA CHIKUNGUNYA
Em 2026, até a SE 34 foram notificados 356 casos suspeitos de chikungunya em residentes do 
Distrito Federal, dos quais 240 eram prováveis.
Notificados
356
Prováveis
240
Descartados
116
Chikungunya
192
Inconclusivo
0
Em investigação
48
Óbitos 
0
Tabela 2. Número de casos prováveis e coeficiente de incidência acumulada (casos por 100 mil hab.) de 
chikungunya em residentes do Distrito Federal por Região de Saúde até a SE 34, Distrito Federal, 2026.
Região de Saúde Casos prováveis (N = 240) Incidência (por 100 mil hab.)
Região Sul 70 25,0
Região Central 38 9,1
Região Centro-Sul 24 6,3
Região Sudoeste 47 5,1
Região Oeste 23 4,4
Região Norte 18 4,1
Região Leste 6 1,6
Ignorado 14 0,4
Fonte: Sinan Online. Dados acessados em 31/08/2026.
Em 2026, até a SE 34, foram realizados 9.027 exames de PCR para chikungunya em residentes do 
Distrito Federal. Dentre os exames realizados, 78 foram confirmados para chikungunya, 
correspondendo a uma positividade acumulada de 0,86% em relação ao total processado.
SITUAÇÃO EPIDEMIOLÓGICA DA ZIKA
Em 2026, até a SE 34 foram notificados 12 casos suspeitos de Zika em residentes do Distrito 
Federal, 11 deles descartados após investigação epidemiológica. 
Notificados
12
Descartados
11
Zika
0
Inconclusivo
1
Em investigação
0
Óbitos
0
SITUAÇÃO EPIDEMIOLÓGICA DA FEBRE AMARELA
Em 2026, até a SE 34 foram notificados e descartados quatro casos suspeitos de febre amarela.
Notificados
4
Descartados
4
Febre Amarela
0
Inconclusivo
0
Em investigação
0
Óbitos
0
Expediente
"""


def autoteste() -> int:
    def t1():
        d = parse_texto(TEXTO_REAL_SE34); r = d["referencia"]
        return r["numero"] == 34 and r["se"] == 34 and r["ano"] == 2026 and r["data_publicacao"] == "31/08/2026" and r["dados_extraidos_em"] == "31/08/2026" and r["periodo_fim"] == "29/08/2026"
    def t2():
        d = parse_texto(TEXTO_REAL_SE34)["dengue"]
        return (d["notificados"], d["provaveis"], d["descartados"], d["inconclusivos"], d["em_investigacao"], d["confirmados_dengue"], d["sinais_de_alarme"], d["dengue_grave"], d["obitos"], d["suspeitos_brutos"]) == (9312, 3264, 6048, 2367, 702, 181, 14, 0, 0, 10203)
    def t3():
        r = parse_texto(TEXTO_REAL_SE34)["dengue"]["regioes"]
        return r["total_declarado"] == 3264 and r["ignorado"] == 220 and r["por_regiao"]["Leste"] == {"casos_provaveis": 586, "incidencia_100k": 158.2} and len(r["por_regiao"]) == 7
    def t4():
        c = parse_texto(TEXTO_REAL_SE34)["chikungunya"]
        return c["provaveis"] == 240 and c["confirmados"] == 192 and c["regioes"]["por_regiao"]["Sul"]["casos_provaveis"] == 70 and c["regioes"]["ignorado"] == 14
    def t5():
        d = parse_texto(TEXTO_REAL_SE34)
        return d["zika"]["notificados"] == 12 and d["zika"]["inconclusivos"] == 1 and d["febre_amarela"]["notificados"] == 4 and d["febre_amarela"]["descartados"] == 4
    def t6():
        l = parse_texto(TEXTO_REAL_SE34)["laboratorio"]
        return l["dengue_pcr"]["exames"] == 9284 and l["dengue_pcr"]["sorotipos"] == {"DENV-1": 2, "DENV-2": 39, "DENV-3": 68} and l["chik_pcr"]["positividade_pct"] == 0.86
    def t7():
        # soma das regiões não fechando com N → recusa (nunca publica parcial)
        quebrado = TEXTO_REAL_SE34.replace("Região Leste 586 158,2", "Região Leste 500 158,2")
        try:
            parse_texto(quebrado); return False
        except ValueError as e:
            return "soma das regiões" in str(e)
    def t8():
        # região faltando → recusa
        quebrado = TEXTO_REAL_SE34.replace("Região Central 101 24,2\n", "")
        try:
            parse_texto(quebrado); return False
        except ValueError as e:
            return "regiões ausentes" in str(e)
    def t9():
        html = ('<a href="/documents/d/saude/informativo_epidemiologico_se01-27-01-26-pdf">x</a>'
                '<a href="/documents/d/saude/informativo_epidemiologico_se02__2_27-01-26-pdf">x</a>'
                '<a href="/documents/d/saude/informativo_epidemiologico_se34-pdf">x</a>'
                '<a href="/documents/37101/0/34_BOLETIM_SEMANAL_DENGUE_SE_34.pdf/abc?t=1">2024</a>')
        url, se = extrair_link_mais_recente(html)
        return se == 34 and url.endswith("informativo_epidemiologico_se34-pdf") and extrair_link_mais_recente("<p>nada</p>") == (None, None)
    def t10():
        try:
            parse_texto("nada aqui bate com o padrão esperado"); return False
        except ValueError:
            return True
    def t11():
        return "não atribui casos ao El Niño" in RESSALVA and len(REGIOES) == 7 and IBGE_DF == "5300108"
    return rodar_autoteste({"referência (Nº, SE, ano, datas)": t1, "cards de dengue (texto real SE 34)": t2,
                            "Tabela 1 por Região de Saúde fecha com N": t3, "chikungunya cards + Tabela 2": t4,
                            "zika e febre amarela": t5, "monitoramento laboratorial e sorotipos": t6,
                            "soma das regiões ≠ N → recusa": t7, "região ausente → recusa": t8,
                            "link mais recente na listagem (maior SE, hrefs relativos com sufixo)": t9,
                            "formato inesperado nunca adivinha": t10, "ressalva, 7 regiões e IBGE fixo": t11})


if __name__ == "__main__":
    sys.exit(autoteste() if "--autoteste" in sys.argv else coletar())
