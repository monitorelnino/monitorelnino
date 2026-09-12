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
TENTATIVAS_SE = 4   # edições mais recentes a tentar, da mais nova para a mais antiga (a listagem anuncia antes de publicar)
CABECALHO = "INFORME EPIDEMIOLÓGICO| ARBOVIROSES"   # cabeçalho corrente que separa as páginas no texto extraído
RESSALVA = ("O Monitor não atribui casos ao El Niño; dados da SES-PE / CIEVS-PE (Sinan Online e Sinan Net), extraídos do "
            "Informe Epidemiológico semanal em PDF — dados parciais, sujeitos a alteração. Só totais estaduais: a tabela "
            "municipal do informe é imagem e não é lida por máquina.")


def _texto_paginas(bruto: bytes) -> list:
    """Texto por página. pdfplumber PRIMEIRO (11/09/2026): nestes PDFs-infográfico o pypdf extrai com espaço
    entre caracteres ("1 1 . 2 4 1"), e nenhum padrão numérico casa; pdfplumber preserva o texto como os
    parsers foram afinados. pypdf fica como reserva, para a leitura nunca depender de uma só biblioteca."""
    try:
        import io as _io, pdfplumber
        with pdfplumber.open(_io.BytesIO(bruto)) as pdf:
            pgs = [(pg.extract_text() or "") for pg in pdf.pages]
        if sum(len(t) for t in pgs) > 200:
            return pgs
    except Exception:  # noqa: BLE001
        pass
    from preservar_evidencias import extrair_texto_por_pagina
    return extrair_texto_por_pagina(bruto)


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


def extrair_links(html: str, ano: int) -> list:
    """Todos os informes 'SE 01 a NN' do ano, do mais recente ao mais antigo, como [(url, se), ...].
    11/09/2026: antes devolvia só o mais recente. O portal anuncia a edição nova na listagem ANTES de o PDF
    existir — na primeira rodada real o coletor pediu a SE 35, levou HTTPError e desistiu, sem tentar a SE 34,
    que estava no ar e responde 200. Agora coletar() desce a lista até uma que responda com PDF."""
    html = _norm(html)
    achados = re.findall(r'href="([^"]*Informe Epidemiol[óo]gico Arboviroses_SE ?0?1 a (\d{1,2})_' + str(ano) + r'\.pdf)"', html, re.I)
    vistos, saida = set(), []
    for href, se in sorted(achados, key=lambda t: int(t[1]), reverse=True):
        if se not in vistos:
            vistos.add(se); saida.append((_url_canonica(href), int(se)))
    return saida


def extrair_link_mais_recente(html: str, ano: int) -> tuple:
    """Compatibilidade: só o mais recente. (None, None) se não achar."""
    links = extrair_links(html, ano)
    return links[0] if links else (None, None)


def _url_canonica(href: str) -> str:
    """Host canônico (a listagem linka em http://) + percent-encode de espaços e não-ASCII.
    11/09/2026 (achado da rodada de 22h): o caminho no servidor usa acento COMBINANTE (NFD: "e"+U+0301).
    Normalizar para NFC gera outro byte-a-byte e o servidor devolve HTTPError — foi por isso que SE 35, 34
    e 33 falharam na mesma rodada em que a sonda baixou o PDF da SE 34 com 200 usando a forma NFD.
    O href é usado como veio do HTML; a normalização NFC fica só para CASAR o regex, nunca para montar a URL."""
    url = urljoin(BASE + "/", href)
    m = re.match(r"^https?://[^/]+(/.*)$", url)
    return BASE + quote(unicodedata.normalize("NFD", m.group(1)), safe="/%_.-") if m else url


def candidatos_por_se(html: str, ano: int) -> list:
    """Todos os informes 'SE 01 a NN' do ano, do mais recente ao mais antigo. Função pura.
    11/09/2026 (achado da 1ª rodada real): a listagem anuncia a edição nova ANTES de o PDF existir — o coletor
    pediu a SE 35 e levou HTTPError, embora o PDF da SE 34 baixasse normalmente do runner. Tentar em ordem
    decrescente resolve sem inventar nada: fica com a edição mais recente que realmente responde."""
    html = _norm(html)
    achados = re.findall(r'href="([^"]*Informe Epidemiol[óo]gico Arboviroses_SE ?0?1 a (\d{1,2})_' + str(ano) + r'\.pdf)"', html, re.I)
    vistos, saida = set(), []
    for href, se in sorted(achados, key=lambda t: int(t[1]), reverse=True):
        if int(se) in vistos:
            continue
        vistos.add(int(se)); saida.append((_url_canonica(href), int(se)))
    return saida


def _n(s: str) -> int:
    return int(s.replace(".", ""))


# rótulos do infográfico → chave interna. Ordem importa só para o regex; o casamento é posicional.
_ROTULOS = ((r"Casos notificados", "notificados"), (r"Casos prov[áa]veis", "provaveis"),
            (r"Casos descartados", "descartados"), (r"Casos confirmados", "confirmados"),
            (r"Casos graves", "graves"))


def _pareados(texto: str) -> dict:
    """Padrão de coluna do infográfico: uma linha SÓ com números e a linha seguinte SÓ com rótulos, na mesma
    ordem, mapeados posicionalmente. Função pura.

    11/09/2026: era fixo em dois ("45.017 22.736" / "Casos notificados Casos descartados"), como no informe da
    SE 34 lido em 10/09. O informe da SE 35, lido pelo pdfplumber no runner, traz TRÊS por linha
    ("46.225 22.732 23.493" / "Casos notificados Casos prováveis Casos descartados") — o layout da fonte
    mudou. Agora aceita qualquer quantidade, desde que números e rótulos venham na mesma contagem; se não
    baterem, devolve vazio e quem chama cai nos candidatos adjacentes + identidade contábil."""
    out = {}
    # 12/09/2026: no informe da SE 35 o último rótulo vem PARTIDO entre linhas
    # ("… Casos prováveis Casos\ndescartados"), então a linha tinha 3 números e só 2 rótulos inteiros e o
    # pareamento era descartado. Emenda o rótulo partido antes de casar; não altera linhas já completas.
    texto = re.sub(r"Casos[ \t]*\n[ \t]*(notificados|prov[áa]veis|descartados|confirmados|graves)\b",
                   r"Casos \1", texto, flags=re.I)
    NUM = r"\d{1,3}(?:\.\d{3})+|\d{1,6}"
    # a linha de rótulos pode ter sufixo (na SE 34 vinha "… Casos descartados Incidência **01 óbito…"):
    # conta só a sequência de "Casos X" no começo da linha e ignora o resto.
    for m in re.finditer(r"^[ \t]*((?:" + NUM + r")(?:[ \t]+(?:" + NUM + r"))*)[ \t]*\n[ \t]*((?:Casos [A-Za-zÁÂÃÉÊÍÓÔÕÚÇáâãéêíóôõúç]+)(?:[ \t]+Casos [A-Za-zÁÂÃÉÊÍÓÔÕÚÇáâãéêíóôõúç]+)*)", texto, re.M):
        nums = [_n(x) for x in re.findall(NUM, m.group(1))]
        crus = re.findall(r"Casos [A-Za-zÁÂÃÉÊÍÓÔÕÚÇáâãéêíóôõúç]+", m.group(2))
        if len(nums) != len(crus) or len(nums) < 2:
            continue
        for valor, rotulo in zip(nums, crus):
            for padrao, chave in _ROTULOS:
                if re.fullmatch(padrao, rotulo, re.I):
                    out.setdefault(chave, valor)
                    break
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
    # 11/09/2026: o ano vem do INÍCIO do período, não do fim. O informe da SE 35 traz
    # "SE 01 a 35 (04/01/2026 a 05/09/2027)" — erro de digitação da própria fonte no ano final. Tirar o ano do
    # fim gravaria a leitura como 2027. O início é o ano do ciclo; a incoerência é registrada, não corrigida.
    ref = {"se_inicio": int(m.group(1)), "se": int(m.group(2)), "periodo_inicio": m.group(3), "periodo_fim": m.group(4),
           "ano": int(m.group(3)[-4:])}
    if m.group(4)[-4:] != m.group(3)[-4:]:
        ref["incoerencia_fonte"] = (f"o informe declara período de {m.group(3)} a {m.group(4)} — anos diferentes; "
                                    f"adotado o ano do início ({ref['ano']}) para a chave da série")
    mc = re.search(r"Dados captados em (\d{2}/\d{2}/\d{4})", texto)
    if not mc:
        raise ValueError("'Dados captados em' não encontrado")
    ref["dados_captados_em"] = mc.group(1)

    def agravo(p: str, nome: str, com_graves: bool) -> dict:
        par = _pareados(p)   # linha 'N1 N2' / 'Casos notificados Casos descartados': mapeamento posicional, sem ambiguidade
        cn = [par["notificados"]] if "notificados" in par else _candidatos(p, r"Casos notificados")
        cd = [par["descartados"]] if "descartados" in par else _candidatos(p, r"Casos\s*\n?\s*descartados")
        cp = [par["provaveis"]] if "provaveis" in par else _candidatos(p, r"Casos prováveis(?!\*| por)")
        n, dsc, pr = _resolver_por_identidade(nome, cn, cd, cp)
        d = {"notificados": n, "descartados": dsc, "provaveis": pr}
        # confirmados: candidatos vizinhos, excluindo números já consumidos por outro campo (o infográfico põe o
        # rótulo entre dois números; um deles costuma ser o próprio 'prováveis'); depois exige <= prováveis
        if "confirmados" in par:
            cc = [par["confirmados"]]
        else:
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
    candidatos = candidatos_por_se(html, hoje.year)
    if not candidatos:
        registrar_lacuna("CIEVS-PE (listagem de informes de arboviroses)", f"nenhum link 'SE 01 a NN_{hoje.year}.pdf' na listagem", canal="site_estadual", camada=2, strings=[LISTAGEM])
        print("informe PE: nenhum link reconhecido na listagem — lacuna declarada"); return 0
    pdf_url = se = paginas = None
    anunciados_sem_arquivo = []
    for url_c, se_c in candidatos[:TENTATIVAS_SE]:
        try:
            # 11/09/2026: até TENTATIVAS_SE=4 pedidos nesta busca; diagnóstico mostrou resposta em <1s quando
            # o portal responde — 25s é folgado sem represar a rodada se uma edição específica não existir.
            bruto = buscar(url_c, timeout=25)
            if bruto[:4] != b"%PDF":
                anunciados_sem_arquivo.append(f"SE {se_c}: resposta não é PDF"); continue
            # 11/09/2026 (achado da rodada de 22h): pdfplumber NÃO está em requirements.txt — o coletor chegava
            # a localizar o PDF e morria com ModuleNotFoundError. A função canônica do projeto usa pypdf
            # (instalado) e só cai para pdfplumber se a extração vier vazia: funciona com ou sem o opcional.
            paginas = [_norm(t) for t in _texto_paginas(bruto)]
            pdf_url, se = url_c, se_c; break
        except Exception as e:  # noqa: BLE001
            anunciados_sem_arquivo.append(f"SE {se_c}: {type(e).__name__}"); continue
    if not pdf_url:
        registrar_lacuna("CIEVS-PE (informe de arboviroses)", f"nenhuma das {min(TENTATIVAS_SE, len(candidatos))} edições mais recentes respondeu com PDF ({'; '.join(anunciados_sem_arquivo)})", canal="site_estadual", camada=2, strings=[LISTAGEM])
        print("informe PE: nenhuma edição baixável — lacuna declarada"); return 0
    if anunciados_sem_arquivo:
        # a listagem anunciou edição mais nova sem arquivo no ar: fato da fonte, registrado sem interromper a leitura
        registrar_lacuna("CIEVS-PE (edição anunciada sem arquivo)", f"a listagem anuncia edição(ões) ainda sem PDF publicado ({'; '.join(anunciados_sem_arquivo)}); lido o informe da SE {se}", canal="site_estadual", camada=2, strings=[pdf_url])
    texto = "\n".join(paginas)
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
    def t8b():
        # 11/09/2026: listagem anuncia SE 35 sem arquivo; candidatos vêm do mais novo ao mais antigo, sem repetir
        html = ('<a href="/docs/Informe Epidemiológico Arboviroses_SE 01 a 33_2026.pdf">x</a>'
                '<a href="/docs/Informe Epidemiológico Arboviroses_SE 01 a 35_2026.pdf">x</a>'
                '<a href="/docs/Informe Epidemiológico Arboviroses_SE 01 a 34_2026.pdf">x</a>'
                '<a href="/docs/Informe Epidemiológico Arboviroses_SE 01 a 34_2026.pdf">dup</a>')
        c = candidatos_por_se(html, 2026)
        return [se for _, se in c] == [35, 34, 33] and all(u.startswith("https://portalcievs") and " " not in u for u, _ in c) and candidatos_por_se("<p>nada</p>", 2026) == []
    def t8():
        html = ('<a href="http://portalcievs.saude.pe.gov.br/docs/Informe Epidemiolo\u0301gico Arboviroses_SE 01 a 33_2026.pdf">x</a>'
                '<a href="http://portalcievs.saude.pe.gov.br/docs/Informe Epidemiológico Arboviroses_SE 01 a 34_2026.pdf">x</a>'
                '<a href="http://portalcievs.saude.pe.gov.br/docs/Informe Epidemiológico Arboviroses_SE10-2025.pdf">2025</a>')
        url, se = extrair_link_mais_recente(html, 2026)
        return se == 34 and url.startswith("https://portalcievs.saude.pe.gov.br/docs/Informe%20Epidemiol") and url.endswith("34_2026.pdf") and " " not in url and extrair_link_mais_recente("<p>nada</p>", 2026) == (None, None)
    def t_nfd():
        # 11/09/2026: a URL montada tem de sair em NFD (acento combinante), exatamente como a sonda baixou
        # com HTTP 200 no runner. Em NFC o servidor devolve HTTPError.
        html = '<a href="http://portalcievs.saude.pe.gov.br/docs/Informe Epidemiol\u00f3gico Arboviroses_SE 01 a 34_2026.pdf">x</a>'
        u, se = candidatos_por_se(html, 2026)[0]
        return se == 34 and u == "https://portalcievs.saude.pe.gov.br/docs/Informe%20Epidemiolo%CC%81gico%20Arboviroses_SE%2001%20a%2034_2026.pdf"

    def t_ano_incoerente():
        # informe real da SE 35 traz "(04/01/2026 a 05/09/2027)" — erro da fonte no ano final.
        ruim = TEXTO_REAL_SE34.replace("(04/01/2026 a 29/08/2026)", "(04/01/2026 a 05/09/2027)")
        d = parse_texto(ruim)
        return d["referencia"]["ano"] == 2026 and "incoerencia_fonte" in d["referencia"]

    def t_layout_se35():
        # layout REAL da SE 35 lido pelo pdfplumber no runner (11/09/2026): três números por linha, três
        # rótulos na seguinte. O da SE 34 tinha dois. Os dois têm de funcionar.
        p35 = _pareados("46.225 22.732 23.493\nCasos notificados Casos prováveis Casos descartados")
        p34 = _pareados("45.017 22.736\nCasos notificados Casos descartados Incidência **01 óbito")
        pz = _pareados("1.209 108 1.101 0\nCasos notificados Casos prováveis Casos descartados Casos confirmados")
        # rótulo PARTIDO entre linhas, como veio de verdade no PDF da SE 35
        p35p = _pareados("46.225 22.732 23.493\nCasos notificados Casos prováveis Casos\ndescartados")
        if p35p != {"notificados": 46225, "provaveis": 22732, "descartados": 23493}:
            return False
        return (p35 == {"notificados": 46225, "provaveis": 22732, "descartados": 23493}
                and p35["provaveis"] + p35["descartados"] == p35["notificados"]     # identidade fecha
                and p34 == {"notificados": 45017, "descartados": 22736}
                and pz["confirmados"] == 0 and pz["provaveis"] == 108
                and _pareados("46.225 22.732\nCasos notificados Casos prováveis Casos descartados") == {})  # contagem diferente → vazio

    def t9():
        try:
            parse_texto("nada aqui bate com o padrão esperado"); return False
        except ValueError:
            return True
    def t10():
        return "não atribui casos ao El Niño" in RESSALVA and "tabela municipal" in RESSALVA
    return rodar_autoteste({"layout de 3 colunas da SE 35 e de 2 da SE 34": t_layout_se35,"ano incoerente na fonte → usa o do início e registra": t_ano_incoerente,"URL do PDF em NFD (forma que o servidor aceita)": t_nfd,"referência SE/período/data de captação": t1, "dengue (número antes do rótulo)": t2,
                            "chikungunya (rótulo antes do número — ordem tolerada)": t3, "zika + gestantes": t4,
                            "óbitos por arboviroses + LIRAa fecha 100%": t5, "identidade contábil quebrada → recusa": t6,
                            "leitura por páginas ≡ leitura por cabeçalho": t7,
                            "link mais recente (acento combinante, espaços, anos misturados)": t8,
                            "candidatos por SE, do mais novo ao mais antigo (edição anunciada sem arquivo)": t8b,
                            "formato inesperado nunca adivinha": t9, "ressalva e limitação declaradas": t10})


if __name__ == "__main__":
    sys.exit(autoteste() if "--autoteste" in sys.argv else coletar())
