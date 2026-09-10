#!/usr/bin/env python3
"""
coletar_boletim_pe_arboviroses.py — arboviroses em Pernambuco (TOTAIS ESTADUAIS), a partir do Informe
Epidemiológico semanal do CIEVS-PE (10/09/2026)
====================================================================================================
Fonte: Secretaria Estadual de Saúde de Pernambuco / Portal CIEVS-PE, "Informe Epidemiológico | Arboviroses"
— PDF semanal acumulado (Sinan Online e Sinan Net), com dengue, chikungunya e Zika. Íntegra conferida em
10/09/2026 no informe "SE 01 a 34 (04/01/2026 a 29/08/2026)", dados captados em 31/08/2026, publicado
03/09/2026.

LIMITAÇÃO DECLARADA — o que este coletor NÃO faz. O informe de PE é um PDF-infográfico: a Tabela 1
(casos prováveis, incidência, formas graves e óbitos POR MUNICÍPIO) está embutida como IMAGEM — a extração
de texto devolve só o título da tabela, nenhuma linha. Portanto, ao contrário dos coletores de MS (tabela
municipal em texto) e DF (regiões de saúde em texto), este coletor entrega apenas os TOTAIS ESTADUAIS por
agravo. A granularidade municipal de PE existe só no painel Power BI do CIEVS, que não é lido por máquina
com confiabilidade. Registrado em fontes_uf.json e no §36.

Por ser infográfico, a ordem "número → rótulo" NÃO é estável no texto extraído (na página de dengue o
número precede o rótulo; na de chikungunya, "Casos notificados" precede o número). O parser é, por isso,
TOLERANTE À ORDEM: para cada rótulo, pega o número mais próximo dentro de uma janela curta, antes ou
depois. E é VALIDADO POR IDENTIDADE CONTÁBIL: para cada agravo, exige notificados == prováveis +
descartados (fechou exatamente nos três agravos na SE 34), confirmados <= prováveis e graves <=
prováveis. Se qualquer identidade falhar, recusa o resultado e declara lacuna — nunca publica número mal
associado. A unidade de leitura é a PÁGINA (p1 dengue, p2 chikungunya, p3 zika, p4 controle vetorial),
que é estável independentemente da ordem interna dos blocos.

Localização: a listagem do portal (noticias/INFORMES/arbovirose) traz uma tabela com link e data de
publicação; os nomes de arquivo têm espaços e acento combinante e variaram entre anos ("SE10-2025",
"SE 49-2023", "SE 01 a 34_2026") — o coletor raspa a listagem e escolhe a maior SE do ano corrente; nunca
adivinha o link.
  python coletar_boletim_pe_arboviroses.py --autoteste
"""
import io, re, sys, unicodedata
from pathlib import Path
from urllib.parse import quote, urljoin
from coletores_base import ler, gravar, buscar, registrar_lacuna, log_busca, rodar_autoteste

RAIZ = Path(__file__).resolve().parent
BASE = "https://portalcievs.saude.pe.gov.br"
LISTAGEM = BASE + "/noticias/INFORMES/arbovirose"
CABECALHO = "INFORME EPIDEMIOLÓGICO| ARBOVIROSES"   # cabeçalho corrente que separa as páginas no texto extraído
RESSALVA = ("O Monitor não atribui casos ao El Niño; dados da SES-PE / CIEVS-PE (Sinan Online e Sinan Net), extraídos do "
            "Informe Epidemiológico semanal em PDF — dados parciais, sujeitos a alteração. Só totais estaduais: a tabela "
            "municipal do informe é imagem e não é lida por máquina.")


def _hoje():
    import datetime as _dt, json as _js
    try:
        a = _js.load(open(RAIZ / "data" / "meta.json", encoding="utf-8")).get("atualizado_em")
        return _dt.datetime.strptime(a, "%d/%m/%Y").date()
    except Exception:  # noqa: BLE001
        return _dt.date.today()


def _norm(s: str) -> str:
    """NFC — o portal usa acento combinante (e + U+0301) nos nomes de arquivo."""
    return unicodedata.normalize("NFC", s)


def extrair_link_mais_recente(html: str, ano: int) -> tuple:
    """Acha na listagem o link do informe 'SE 01 a NN' de maior NN do ano. Função pura. (None, None) se não achar."""
    html = _norm(html)
    achados = re.findall(r'href="([^"]*Informe Epidemiol[óo]gico Arboviroses_SE ?0?1 a (\d{1,2})_' + str(ano) + r'\.pdf)"', html, re.I)
    if not achados:
        return None, None
    href, se = max(achados, key=lambda t: int(t[1]))
    url = urljoin(BASE + "/", href)
    # normaliza para o host canônico (a listagem linka em http://) e percent-encode espaços e não-ASCII do caminho
    m = re.match(r"^https?://[^/]+(/.*)$", url)
    return (BASE + quote(m.group(1), safe="/%_.-") if m else url), int(se)


def _n(s: str) -> int:
    return int(s.replace(".", ""))


def _pareados(texto: str) -> dict:
    """Padrão de coluna do infográfico: uma linha com dois números e a linha seguinte com dois rótulos, na mesma
    ordem ('45.017 22.736' / 'Casos notificados Casos descartados'). Mapeia posicionalmente. Função pura."""
    out = {}
    for m in re.finditer(r"^\s*(\d{1,3}(?:\.\d{3})+|\d{1,6})\s+(\d{1,3}(?:\.\d{3})+|\d{1,6})\s*\n\s*(Casos notificados)\s+(Casos descartados)", texto, re.M | re.I):
        out["notificados"] = _n(m.group(1)); out["descartados"] = _n(m.group(2))
    return out


def _candidatos(texto: str, rotulo: str, janela: int = 40) -> list:
    """Números ADJACENTES ao rótulo: o imediatamente antes e o imediatamente depois (só espaço/quebra de linha
    entre número e rótulo). Um número separado do rótulo por outro texto pertence a outro rótulo — não entra.
    Ignora marcadores de nota ('**01') e decimais ('22,9'). ValueError se o rótulo não existir ou não houver
    número adjacente — nunca adivinha."""
    m = re.search(rotulo, texto)   # sensível a maiúsculas: rótulos são "Casos …"; legendas de gráfico, "casos …"
    if not m:
        raise ValueError(f"rótulo não encontrado: {rotulo}")
    antes = texto[max(0, m.start() - janela): m.start()]
    depois = texto[m.end(): m.end() + janela]
    c = []
    ma = re.search(r"(?<![\d,%*])(\d{1,3}(?:\.\d{3})+|\d{1,6})(?![\d,%])\s*$", antes)
    if ma:
        c.append(_n(ma.group(1)))
    md = re.match(r"\s*(\d{1,3}(?:\.\d{3})+|\d{1,6})(?![\d,%])", depois)
    if md:
        c.append(_n(md.group(1)))
    if not c:
        raise ValueError(f"nenhum número adjacente a: {rotulo}")
    return c


def _perto(texto: str, rotulo: str, janela: int = 40) -> int:
    """Número adjacente ao rótulo, quando só há um (campos sem identidade para desempatar: graves, óbitos).
    Se houver dois adjacentes, é ambíguo → ValueError."""
    c = _candidatos(texto, rotulo, janela)
    if len(c) != 1:
        raise ValueError(f"'{rotulo}' ambíguo: números adjacentes {c}")
    return c[0]


def _resolver_por_identidade(nome: str, cn: list, cd: list, cp: list) -> tuple:
    """Escolhe (notificados, descartados, prováveis) entre os candidatos vizinhos: a ÚNICA combinação em que
    notificados == prováveis + descartados. Nenhuma ou mais de uma → ValueError (recusa)."""
    sol = {(n, d, p) for n in cn for d in cd for p in cp if n == p + d and n > 0}
    if len(sol) != 1:
        raise ValueError(f"{nome}: identidade notificados = prováveis + descartados não fecha de forma única (candidatos n={cn} d={cd} p={cp})")
    return next(iter(sol))


def _pct(texto: str, rotulo: str) -> float:
    m = re.search(r"(\d{1,3},\d)%\s*\n\s*" + rotulo, texto, re.I) or re.search(rotulo + r".{0,80}?(\d{1,3},\d)%", texto, re.I | re.S)
    if not m:
        raise ValueError(f"variação % não encontrada perto de: {rotulo}")
    return float(m.group(1).replace(",", "."))


def _paginas(texto: str) -> list:
    """Divide o texto extraído em páginas pelo cabeçalho corrente. Página 0 = dengue."""
    partes = texto.split(CABECALHO)
    return [p for p in partes if p.strip()]


def parse_texto(texto: str, paginas: list = None) -> dict:
    """Extrai referência, totais estaduais de dengue/chikungunya/zika, óbitos por arboviroses e LIRAa.
    `paginas`: lista de textos por página (pdfplumber); se None, divide `texto` pelo cabeçalho corrente."""
    texto = _norm(texto)
    pg = paginas if paginas is not None else _paginas(texto)
    if len(pg) < 3:
        raise ValueError(f"esperava ≥3 páginas (dengue, chikungunya, zika); veio {len(pg)}")
    m = re.search(r"SE\s*E?\s*0?(\d{1,2}) a (\d{1,2}) \((\d{2}/\d{2}/\d{4}) a (\d{2}/\d{2}/\d{4})\)", texto)
    if not m:
        raise ValueError("referência 'SE 01 a NN (dd/mm/aaaa a dd/mm/aaaa)' não encontrada")
    ref = {"se_inicio": int(m.group(1)), "se": int(m.group(2)), "periodo_inicio": m.group(3), "periodo_fim": m.group(4),
           "ano": int(m.group(4)[-4:])}
    mc = re.search(r"Dados captados em (\d{2}/\d{2}/\d{4})", texto)
    if not mc:
        raise ValueError("'Dados captados em' não encontrado")
    ref["dados_captados_em"] = mc.group(1)

    def agravo(p: str, nome: str, com_graves: bool) -> dict:
        par = _pareados(p)   # linha 'N1 N2' / 'Casos notificados Casos descartados': mapeamento posicional, sem ambiguidade
        cn = [par["notificados"]] if "notificados" in par else _candidatos(p, r"Casos notificados")
        cd = [par["descartados"]] if "descartados" in par else _candidatos(p, r"Casos\s*\n?\s*descartados")
        cp = _candidatos(p, r"Casos prováveis(?!\*| por)")
        n, dsc, pr = _resolver_por_identidade(nome, cn, cd, cp)
        d = {"notificados": n, "descartados": dsc, "provaveis": pr}
        # confirmados: candidatos vizinhos, excluindo números já consumidos por outro campo (o infográfico põe o
        # rótulo entre dois números; um deles costuma ser o próprio 'prováveis'); depois exige <= prováveis
        cc = [c for c in _candidatos(p, r"Casos\s*\n?\s*confirmados(?! \+)") if c not in (n, dsc, pr)]
        cc = [c for c in cc if c <= pr]
        if len(cc) != 1:
            raise ValueError(f"{nome}: 'Casos confirmados' ambíguo ou ausente (candidatos válidos: {cc})")
        d["confirmados"] = cc[0]
        if com_graves:
            d["graves"] = _perto(p, r"Casos graves")
        try:
            d["variacao_vs_ano_anterior_pct"] = _pct(p, nome)
        except ValueError:
            d["variacao_vs_ano_anterior_pct"] = None
        # identidades contábeis — se não fecham, o número está mal associado: recusar
        if d["notificados"] != d["provaveis"] + d["descartados"]:
            raise ValueError(f"{nome}: notificados ({d['notificados']}) ≠ prováveis ({d['provaveis']}) + descartados ({d['descartados']})")
        if d["confirmados"] > d["provaveis"]:
            raise ValueError(f"{nome}: confirmados ({d['confirmados']}) > prováveis ({d['provaveis']})")
        if com_graves and d["graves"] > d["provaveis"]:
            raise ValueError(f"{nome}: graves ({d['graves']}) > prováveis ({d['provaveis']})")
        return d

    dengue = agravo(pg[0], "Dengue", True)
    chik = agravo(pg[1], "Chikungunya", False)
    zika = agravo(pg[2], "Zika", False)
    mz = re.search(r"em gestantes\s*\n\s*(\d+)", pg[2])
    zika["provaveis_em_gestantes"] = int(mz.group(1)) if mz else None
    obitos = {"em_investigacao": _perto(pg[0], r"Óbitos em investigação"), "confirmados": _perto(pg[0], r"Óbitos confirmados"),
              "descartados": _perto(pg[0], r"Óbitos descartados")}
    liraa = {}
    if len(pg) > 3:
        # os três percentuais de risco vêm logo depois das faixas de IIP (que também têm '%'): ancorar em 'IIP<1%'
        mi = re.search(r"IIP<1%(.*)", pg[3], re.S)
        ml = re.findall(r"(\d{1,3},\d)%", mi.group(1)) if mi else []
        if len(ml) >= 3:
            liraa = {"risco_alto_pct": float(ml[0].replace(",", ".")), "risco_moderado_pct": float(ml[1].replace(",", ".")),
                     "risco_baixo_pct": float(ml[2].replace(",", "."))}
            if abs(sum(liraa.values()) - 100.0) > 0.6:
                liraa = {}   # não fecha 100%: não publica
    return {"referencia": ref, "escopo": "totais_estaduais", "dengue": dengue, "chikungunya": chik, "zika": zika,
            "obitos_arboviroses": obitos, "liraa_4o_ciclo": liraa,
            "tabela_municipal": "não extraída — imagem no PDF (ver fontes_uf.json/PE)"}


def coletar() -> int:
    hoje = _hoje()
    try:
        html = buscar(LISTAGEM, timeout=60).decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        registrar_lacuna("CIEVS-PE (listagem de informes de arboviroses)", type(e).__name__, canal="site_estadual", camada=2, strings=[LISTAGEM])
        print("informe PE: listagem inacessível — lacuna declarada"); return 0
    pdf_url, se = extrair_link_mais_recente(html, hoje.year)
    if not pdf_url:
        registrar_lacuna("CIEVS-PE (listagem de informes de arboviroses)", f"nenhum link 'SE 01 a NN_{hoje.year}.pdf' na listagem", canal="site_estadual", camada=2, strings=[LISTAGEM])
        print("informe PE: nenhum link reconhecido na listagem — lacuna declarada"); return 0
    try:
        bruto = buscar(pdf_url, timeout=90)
        import pdfplumber
        with pdfplumber.open(io.BytesIO(bruto)) as pdf:
            paginas = [_norm(pg.extract_text() or "") for pg in pdf.pages]
        texto = "\n".join(paginas)
    except Exception as e:  # noqa: BLE001
        registrar_lacuna(f"CIEVS-PE informe SE {se}", type(e).__name__, canal="site_estadual", camada=2, strings=[pdf_url])
        print("informe PE: falha ao ler o PDF — lacuna declarada"); return 0
    try:
        dados = parse_texto(texto, paginas=paginas)
    except ValueError as e:
        # leva um trecho do texto extraído pelo pdfplumber: se a ordem do infográfico diferir da que afinou o parser
        # (afinado em 10/09/2026 contra outra ferramenta de extração), a próxima sessão vê o porquê sem precisar de rede
        amostra = " | ".join((p[:220].replace("\n", "⏎")) for p in paginas[:3])
        registrar_lacuna("CIEVS-PE (formato do informe / identidade contábil)", str(e)[:180], canal="site_estadual", camada=2, strings=[pdf_url, "amostra pdfplumber: " + amostra])
        print(f"informe PE: {e} — coletor não adivinha; nada publicado"); return 0
    serie = ler("saude_desfechos/ses_pe_arboviroses.json", {"_governanca": "Arboviroses em Pernambuco (dengue, chikungunya, Zika) — TOTAIS ESTADUAIS lidos do Informe Epidemiológico semanal do CIEVS-PE (Sinan Online / Sinan Net). " + RESSALVA + " Cada leitura é o ACUMULADO do ano até a SE do informe; a série é construída pelo próprio Monitor a partir de 10/09/2026. Peso zero; nunca lido pelo motor.", "serie": {}})
    chave = f"{dados['referencia']['ano']}-{dados['referencia']['se']:02d}"
    serie.setdefault("serie", {})[chave] = dados
    serie["ultima_atualizacao"] = hoje.strftime("%d/%m/%Y"); serie["fonte_pdf_mais_recente"] = pdf_url
    gravar("saude_desfechos/ses_pe_arboviroses.json", serie)
    d = dados["dengue"]
    log_busca("site_estadual", 2, [pdf_url], "registro", nivel="estadual", n_resultados=3,
              resultados=f"CIEVS-PE: informe SE 01 a {dados['referencia']['se']}/{dados['referencia']['ano']} lido — dengue {d['provaveis']} prováveis / {d['confirmados']} confirmados / {d['graves']} graves; chik {dados['chikungunya']['provaveis']}; zika {dados['zika']['provaveis']} (só totais estaduais)")
    print(f"informe PE: SE 01 a {dados['referencia']['se']}/{dados['referencia']['ano']} — dengue {d['provaveis']} prováveis, chik {dados['chikungunya']['provaveis']}, zika {dados['zika']['provaveis']}; óbitos confirmados {dados['obitos_arboviroses']['confirmados']} (totais estaduais)")
    return 0


# Texto REAL extraído do PDF "SE 01 a 34 (04/01/2026 a 29/08/2026)", lido em 10/09/2026 — as 4 primeiras páginas.
TEXTO_REAL_SE34 = """SE 01 a 34 (04/01/2026 a 29/08/2026)
38,8%
Dengue
Casos prováveis por
100 mil hab.
10.848
Casos confirmados Casos confirmados +
casos em investigação
22.281
Casos prováveis
Gráfico 3. Distribuição da incidência dos casos
prováveis de dengue, por sexo e faixa etária.
Pernambuco, SE 01 a 34/2026.
649
Casos graves Dengue com sinais
de alarme e gravidade
Figura 1. Distribuição espacial da incidência dos casos prováveis de dengue. Pernambuco, SE 01 a 34/2026.
Fonte: Sinan Online/SES-PE.
Dados captados em 31/08/2026, sujeitos a alterações.
233
Gráfico 2. Distribuição da incidência dos casos
22
Óbitos em investigação*
para arboviroses
03
Óbitos confirmados
para arboviroses
25
Óbitos descartados
para arboviroses
Variação dos casos
notificados
Comparação com o mesmo
período do ano anterior
45.017 22.736
Casos notificados Casos descartados Incidência **01 óbito confirmado de caso alóctone.
INFORME EPIDEMIOLÓGICO| ARBOVIROSES
SE 01 a 34 (04/01/2026 a 29/08/2026) Variação dos casos
notificados
Comparação com o mesmo
período do ano anterior
20,8%
Chikungunya
346
Casos
confirmados
2.187
Casos prováveis
Gráfico 4. Diagrama de Controle dos casos prováveis de
chikungunya. Pernambuco, 2026.
Fonte: Sinan Online/SES-PE.
Dados captados em 31/08/2026, sujeitos a alterações.
Casos confirmados +
casos em investigação
22,9
Casos notificados
6.292
Casos
descartados
4.105
Incidência Casos prováveis por
100 mil hab.
INFORME EPIDEMIOLÓGICO| ARBOVIROSES
SE E 01 a 34 (04/01/2026 a 29/08/2026)
5,8%
0
Casos
confirmados
Casos prováveis*
em gestantes
12
Gráfico 7. Diagrama de Controle dos casos prováveis de zika.
Zika
1,1
104
Casos prováveis Fonte: Sinan Net/SES-PE.
Dados captados em 31/08/2026, sujeitos a alterações.
Casos confirmados +
casos em investigação
Variação dos casos
notificados
Incidência Casos prováveis por
100 mil hab.
1.128
Casos notificados
1.024
Casos
descartados
16
INFORME EPIDEMIOLÓGICO| ARBOVIROSES
SE 01 a 34 (04/01/2026 a 29/08/2026)
Epizootias
Notificações
Risco alto
Situação de risco de surto
IIP>3,9%
Risco moderado
Situação de alerta
IIP=1 a 3,9%
Risco baixo
Situação satisfatória
IIP<1%
30,0%
57,0%
13,0%
Figura 5. Distribuição espacial do Índice de Infestação Predial (IIP), Pernambuco,
referente ao 4° ciclo do LIRAa/LIA de 2026.
0
Confirmados
"""


def autoteste() -> int:
    def t1():
        r = parse_texto(TEXTO_REAL_SE34)["referencia"]
        return r == {"se_inicio": 1, "se": 34, "periodo_inicio": "04/01/2026", "periodo_fim": "29/08/2026", "ano": 2026, "dados_captados_em": "31/08/2026"}
    def t2():
        d = parse_texto(TEXTO_REAL_SE34)["dengue"]
        return (d["notificados"], d["descartados"], d["provaveis"], d["confirmados"], d["graves"], d["variacao_vs_ano_anterior_pct"]) == (45017, 22736, 22281, 10848, 649, 38.8)
    def t3():
        c = parse_texto(TEXTO_REAL_SE34)["chikungunya"]   # aqui o rótulo 'Casos notificados' vem ANTES do número
        return (c["notificados"], c["descartados"], c["provaveis"], c["confirmados"], c["variacao_vs_ano_anterior_pct"]) == (6292, 4105, 2187, 346, 20.8)
    def t4():
        z = parse_texto(TEXTO_REAL_SE34)["zika"]
        return (z["notificados"], z["descartados"], z["provaveis"], z["confirmados"], z["provaveis_em_gestantes"]) == (1128, 1024, 104, 0, 12)
    def t5():
        d = parse_texto(TEXTO_REAL_SE34)
        return d["obitos_arboviroses"] == {"em_investigacao": 22, "confirmados": 3, "descartados": 25} and d["liraa_4o_ciclo"] == {"risco_alto_pct": 30.0, "risco_moderado_pct": 57.0, "risco_baixo_pct": 13.0}
    def t6():
        # identidade contábil quebrada → recusa (número mal associado nunca é publicado)
        quebrado = TEXTO_REAL_SE34.replace("45.017 22.736", "45.017 22.000")
        try:
            parse_texto(quebrado); return False
        except ValueError as e:
            return "notificados" in str(e)
    def t7():
        # a mesma leitura por lista de páginas (caminho do pdfplumber) dá o mesmo resultado
        pgs = _paginas(_norm(TEXTO_REAL_SE34))
        return parse_texto(TEXTO_REAL_SE34, paginas=pgs) == parse_texto(TEXTO_REAL_SE34)
    def t8():
        html = ('<a href="http://portalcievs.saude.pe.gov.br/docs/Informe Epidemiolo\u0301gico Arboviroses_SE 01 a 33_2026.pdf">x</a>'
                '<a href="http://portalcievs.saude.pe.gov.br/docs/Informe Epidemiológico Arboviroses_SE 01 a 34_2026.pdf">x</a>'
                '<a href="http://portalcievs.saude.pe.gov.br/docs/Informe Epidemiológico Arboviroses_SE10-2025.pdf">2025</a>')
        url, se = extrair_link_mais_recente(html, 2026)
        return se == 34 and url.startswith("https://portalcievs.saude.pe.gov.br/docs/Informe%20Epidemiol") and url.endswith("34_2026.pdf") and " " not in url and extrair_link_mais_recente("<p>nada</p>", 2026) == (None, None)
    def t9():
        try:
            parse_texto("nada aqui bate com o padrão esperado"); return False
        except ValueError:
            return True
    def t10():
        return "não atribui casos ao El Niño" in RESSALVA and "tabela municipal" in RESSALVA
    return rodar_autoteste({"referência SE/período/data de captação": t1, "dengue (número antes do rótulo)": t2,
                            "chikungunya (rótulo antes do número — ordem tolerada)": t3, "zika + gestantes": t4,
                            "óbitos por arboviroses + LIRAa fecha 100%": t5, "identidade contábil quebrada → recusa": t6,
                            "leitura por páginas ≡ leitura por cabeçalho": t7,
                            "link mais recente (acento combinante, espaços, anos misturados)": t8,
                            "formato inesperado nunca adivinha": t9, "ressalva e limitação declaradas": t10})


if __name__ == "__main__":
    sys.exit(autoteste() if "--autoteste" in sys.argv else coletar())
