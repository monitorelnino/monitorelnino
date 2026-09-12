#!/usr/bin/env python3
"""
coletar_boletim_ms_dengue.py — dengue por município, a partir do boletim semanal da SES-MS (09/09/2026)
============================================================================================================
Fonte: Secretaria de Estado de Saúde de Mato Grosso do Sul, "Boletim Epidemiológico Dengue" — PDF semanal
(SINAN Online), com uma tabela por município (IBGE, casos prováveis, população, incidência). Confirmado
em 10/09/2026, lendo a íntegra do boletim da SE 30/2026 (publicado 10/08/2026): estrutura de texto estável
o bastante para leitura por regex — mas o coletor é DEFENSIVO: se a tabela municipal não render pelo menos
70 dos 79 municípios (limiar de segurança), ele recusa o resultado e registra lacuna, nunca publica parcial.

O boletim da SES-MS só traz o HISTÓRICO POR ANO (não por semana); a série SEMANAL por semana epidemiológica
o Monitor constrói sozinho, uma leitura por vez, a partir de agora — como qualquer série nova, começa fina
e cresce a cada rodada. Ressalva de não-atribuição ao El Niño em toda superfície, como o resto do §35/§36.
Peso zero; nunca lido pelo motor.

Localização do boletim da semana: a página de listagem WordPress não tem URL previsível por PDF, então o
coletor tenta o permalink previsível da semana corrente e recua até 3 semanas se ainda não publicado —
nunca adivinha o link do PDF em si (que sempre vem de dentro da página do post, por regex de .pdf).
  python coletar_boletim_ms_dengue.py --autoteste
"""
import io, re, sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from coletores_base import ler, gravar, buscar, registrar_lacuna, log_busca, rodar_autoteste

RAIZ = Path(__file__).resolve().parent
LISTAGEM = "https://www.saude.ms.gov.br/informativos/boletins/"
PERMALINK = "https://www.saude.ms.gov.br/informativos/boletins/boletim-epidemiologico-dengue-semana-{se:02d}-{ano}/"
LISTAGEM = "https://www.saude.ms.gov.br/informativos/boletins/"
# 11/09/2026 (verificado em navegador real): a listagem expõe os PDFs DIRETO, sem passar por post.
# Padrão observado: /wp-content/uploads/<ano>/<mes>/Boletim-Epidemiologico-Dengue-–-Semana-NN-–-AAAA.pdf
# (o separador é travessão U+2013, não hífen). A SE 34/2026 está publicada — o que derrubava a coleta
# não era a fonte ter parado, era o coletor procurar um permalink de post que a listagem não usa.
RE_PDF_LISTAGEM = re.compile(
    r'href="(https?://[^"]*?/wp-content/uploads/\d{4}/\d{2}/Boletim-Epidemiologico-Dengue-[^"]*?Semana-(\d{1,2})-[^"]*?(\d{4})\.pdf)"', re.I)
MIN_MUNICIPIOS = 70   # MS tem 79; abaixo disso, a tabela não veio inteira — recusar, nunca publicar parcial
RECUO_MAX = 14        # semanas para trás na busca do último boletim publicado (11/09/2026: a série parou na SE 25)
DEFASAGEM_ALERTA = 4  # acima disso, a lacuna deixa de ser "atraso normal" e vira defasagem declarada da fonte
RESSALVA = "O Monitor não atribui casos ao El Niño; dados da SES-MS (SINAN Online), extraídos do boletim semanal em PDF — dados parciais, sujeitos a alteração pelos municípios."


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


def se_epidemiologica(d: date) -> tuple:
    """(ano, semana) epidemiológica ISO-like: semana 1 começa no primeiro domingo do ano cuja semana contém 4/jan. Aproximação por ISO calendar (suficiente para localizar o boletim, não para o cálculo do índice)."""
    iso = d.isocalendar()
    return iso[0], iso[1]


def extrair_pdf_do_post(html: str) -> str:
    """Acha o primeiro link .pdf dentro da página do post. Função pura. None se não achar (nunca adivinha)."""
    m = re.search(r'href="(https://www\.saude\.ms\.gov\.br/wp-content/uploads/[^"]+?\.pdf)"', html, re.I)
    return m.group(1) if m else None


def parse_texto(texto: str) -> dict:
    """Extrai do texto do PDF: referencia {ano, se, data}, totais estaduais (4 números) e a tabela municipal.
    Função pura. Levanta ValueError se algo essencial não bater — o coletor nunca adivinha."""
    m = re.search(r"Atualizado at[ée] SE\s*(\d{1,2}),\s*(\d{1,2})\s*de\s*(\w+)\s*de\s*(\d{4})", texto, re.I)
    if not m:
        raise ValueError("referência 'Atualizado até SE …' não encontrada")
    MESES = {"janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3, "abril": 4, "maio": 5, "junho": 6, "julho": 7,
             "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12}
    se_ref = int(m.group(1)); mes = MESES.get(m.group(3).lower())
    if mes is None:
        raise ValueError(f"mês não reconhecido: {m.group(3)}")
    data_ref = date(int(m.group(4)), mes, int(m.group(2)))
    # 12/09/2026: casar direto no texto com \n? explícito é frágil — depende de exatamente onde CADA
    # extrator de PDF decide quebrar linha, e isso muda entre pdfplumber e outras ferramentas mesmo para o
    # mesmo PDF. Casa numa cópia com todo espaço em branco (incluindo quebra de linha) normalizado para um
    # espaço; a posição na string original é recuperada, então totais e municípios continuam do mesmo texto.
    _flat = re.sub(r"\s+", " ", texto)
    # 12/09/2026: a SES-MS não usa um layout fixo — a SE 30 trazia NÚMEROS antes dos rótulos; a SE 34, na
    # mesma posição do boletim, trazia os RÓTULOS antes dos números (verificado com os dois PDFs reais).
    # Casa as duas ordens; None nos grupos que não existirem na ordem escolhida.
    ROTULOS = r"Casos +Casos +[ÓO]bitos em +[ÓO]bitos +prov[áa]veis +confirmados +investiga[çc][ãa]o +confirmados"
    m2 = re.search(r"(" + ROTULOS + r") ([\d.]+) ([\d.]+) (\d+) (\d+)", _flat, re.I)  # rótulos → números
    if m2:
        g = (m2.group(2), m2.group(3), m2.group(4), m2.group(5))
    else:
        m2 = re.search(r"([\d.]+) ([\d.]+) (\d+) (\d+) Casos +prov[áa]veis Casos ?confirmados [ÓO]bitos em +investiga[çc][ãa]o [ÓO]bitos +confirmados", _flat, re.I)  # números → rótulos
        g = m2.groups() if m2 else None
    if not g:
        raise ValueError("bloco de totais estaduais (casos prováveis/confirmados/óbitos) não encontrado")
    totais = {"casos_provaveis": int(g[0].replace(".", "")), "casos_confirmados": int(g[1].replace(".", "")),
              "obitos_investigacao": int(g[2]), "obitos_confirmados": int(g[3])}
    linhas = re.findall(r"^\s*\d{1,3}\s+(\d{7})\s+([A-Za-zÀ-ÿ' .\-]+?)\s+(\d[\d.]*)\s+(\d[\d.]*)\s+([\d.,]+)\s*(Alta|M[ée]dia|Baixa|Sem\s*notifica[çc][ãa]o)?\s*$",
                         texto, re.M)
    municipios = {}
    for ibge, nome, casos, pop, inc, classe in linhas:
        municipios[ibge] = {"nome": nome.strip(), "casos_provaveis": int(casos.replace(".", "")), "populacao": int(pop.replace(".", "")),
                            "incidencia": float(inc.replace(".", "").replace(",", ".")), "classificacao": (classe or "").strip() or None}
    return {"referencia": {"ano": data_ref.year, "se": se_ref, "data": data_ref.strftime("%d/%m/%Y")}, "totais_estaduais": totais, "municipios": municipios}


def extrair_pdfs_da_listagem(html: str, ano: int) -> list:
    """Boletins de dengue do ano na listagem, do mais recente ao mais antigo: [(url, se), ...]. Função pura."""
    achados = [(u, int(se)) for u, se, a in RE_PDF_LISTAGEM.findall(html) if int(a) == ano]
    vistos, saida = set(), []
    for u, se in sorted(achados, key=lambda t: t[1], reverse=True):
        if se not in vistos:
            vistos.add(se); saida.append((u, se))
    return saida


def extrair_municipios_por_tabela(bruto: bytes) -> dict:
    """12/09/2026: caminho alternativo para a tabela municipal, usando extract_tables() do pdfplumber (células
    já separadas pela grade do PDF) em vez de regex sobre texto corrido. Existe porque, na rodada real, o
    texto corrido só rendeu 35 das 79 linhas — a segunda metade da tabela cai numa página com gráfico/mapa ao
    lado, e a extração de texto por posição intercala as duas colunas de forma imprevisível. extract_tables()
    lê a grade da própria tabela, imune a esse problema. Função pura no sentido de nunca inventar: linha cuja
    forma não reconhece é ignorada, não adivinhada. [] ou erro de importação → {} (quem chama decide o que
    fazer com uma tabela vazia; não é este ponto que decide publicar ou recusar)."""
    municipios = {}
    try:
        import io as _io, pdfplumber
        with pdfplumber.open(_io.BytesIO(bruto)) as pdf:
            for pg in pdf.pages:
                for tabela in (pg.extract_tables() or []):
                    for linha in tabela:
                        celulas = [(c or "").strip() for c in linha]
                        # forma esperada: [ranking?, IBGE(7 díg.), nome, casos, pop, incidência, classificação?]
                        idx_ibge = next((i for i, c in enumerate(celulas) if re.fullmatch(r"\d{7}", c)), None)
                        if idx_ibge is None or idx_ibge + 4 >= len(celulas):
                            continue
                        ibge, nome, casos, pop, inc = celulas[idx_ibge:idx_ibge + 5]
                        if not re.fullmatch(r"\d[\d.]*", casos) or not re.fullmatch(r"\d[\d.]*", pop) or not re.fullmatch(r"[\d.,]+", inc):
                            continue
                        classe = celulas[idx_ibge + 5] if idx_ibge + 5 < len(celulas) else ""
                        municipios[ibge] = {"nome": nome, "casos_provaveis": int(casos.replace(".", "")),
                                            "populacao": int(pop.replace(".", "")),
                                            "incidencia": float(inc.replace(".", "").replace(",", ".")),
                                            "classificacao": classe or None}
    except Exception:  # noqa: BLE001
        return {}
    return municipios


def coletar() -> int:
    hoje = _hoje(); ano, se_atual = se_epidemiologica(hoje)
    pdf_url = None; tentativas = []; se_achada = None
    # 11/09/2026: caminho primário — a LISTAGEM, que expõe os PDFs direto (verificado em navegador real).
    # O permalink de post fica como segundo caminho, para o caso de a listagem mudar de forma.
    try:
        html_lst = buscar(LISTAGEM, timeout=45).decode("utf-8", "replace")
        for u, se in extrair_pdfs_da_listagem(html_lst, ano):
            pdf_url, se_achada = u, se
            break
    except Exception:  # noqa: BLE001
        pass
    if pdf_url:
        tentativas.append(LISTAGEM)
    # 11/09/2026 (achado da 1ª rodada real): o recuo de 3 semanas era curto demais. A listagem da SES-MS
    # responde 200 normalmente do runner — o padrão de permalink está certo —, mas o último boletim publicado
    # é o da SE 25 (10/07/2026): a secretaria interrompeu a série. Com recuo curto, isso chegava como
    # "nenhum permalink respondeu", indistinguível de erro do coletor. Recuo até RECUO_MAX para localizar o
    # último realmente publicado e DECLARAR A DEFASAGEM — interrupção da fonte é achado do §36, não falha da coleta.
    for delta in (range(0, RECUO_MAX) if not pdf_url else ()):
        se = se_atual - delta; a = ano
        if se < 1:
            a -= 1; se += 52
        url_post = PERMALINK.format(se=se, ano=a)
        tentativas.append(url_post)
        try:
            html = buscar(url_post, timeout=40).decode("utf-8", "replace")
        except Exception:  # noqa: BLE001
            continue
        pdf_url = extrair_pdf_do_post(html)
        if pdf_url:
            se_achada = se; break
    if not pdf_url:
        registrar_lacuna("SES-MS (boletim semanal de dengue)", f"nenhum permalink respondeu com PDF nas últimas {RECUO_MAX} semanas (SE {se_atual} a {se_atual - RECUO_MAX + 1}) — série possivelmente interrompida pela secretaria", canal="site_estadual", camada=2, strings=[tentativas[0], tentativas[-1]])
        print(f"boletim MS: não localizado em {RECUO_MAX} semanas — lacuna declarada"); return 0
    defasagem = se_atual - se_achada
    if defasagem >= DEFASAGEM_ALERTA:
        # o boletim existe, mas é antigo: registrar a defasagem como fato da fonte, além de seguir com a leitura
        registrar_lacuna("SES-MS (boletim semanal de dengue)", f"último boletim publicado é o da SE {se_achada}; a semana corrente é a {se_atual} — {defasagem} semanas de defasagem na fonte", canal="site_estadual", camada=2, strings=[pdf_url])
    try:
        bruto = buscar(pdf_url, timeout=90)
        # 11/09/2026 (achado da rodada de 22h): pdfplumber NÃO está em requirements.txt — o coletor chegava
        # a localizar o PDF e morria com ModuleNotFoundError. A função canônica do projeto usa pypdf
        # (instalado) e só cai para pdfplumber se a extração vier vazia: funciona com ou sem o opcional.
        texto = "\n".join(_texto_paginas(bruto)[:3])   # os dados-chave estão nas 3 primeiras páginas
    except Exception as e:  # noqa: BLE001
        registrar_lacuna(f"SES-MS boletim {pdf_url[:60]}", type(e).__name__, canal="site_estadual", camada=2, strings=[pdf_url]); print("boletim MS: falha ao ler o PDF — lacuna declarada"); return 0
    try:
        dados = parse_texto(texto)
    except ValueError as e:
        # 12/09/2026: leva uma amostra do texto REAL extraído — foi o que permitiu corrigir o coletor de PE
        # sem rede no ambiente de edição. Sem isso, a lacuna diz que o formato mudou mas não em quê.
        amostra = texto[:1400].replace("\n", "⏎")
        print("AMOSTRA:", amostra)  # 12/09/2026: debug do diagnóstico isolado, que não comita log_buscas.json
        registrar_lacuna("SES-MS (formato do boletim)", str(e)[:180], canal="site_estadual", camada=2, strings=[pdf_url, "amostra: " + amostra])
        print(f"boletim MS: {e} — coletor não adivinha; corrigir o parser e reexecutar"); return 0
    if len(dados["municipios"]) < MIN_MUNICIPIOS:
        # 12/09/2026: antes de recusar, tenta extract_tables() do pdfplumber sobre o PDF completo — não só as
        # 3 primeiras páginas de texto. Achado real: o texto corrido rendeu 35/79 porque a 2ª metade da tabela
        # cai numa página com gráfico ao lado, e a extração por posição intercala as colunas fora de ordem;
        # extract_tables() lê a grade da própria tabela, imune a isso. Só substitui se vier MAIOR — nunca troca
        # um resultado bom por um pior, e continua recusando se nenhum dos dois caminhos chegar ao limiar.
        por_tabela = extrair_municipios_por_tabela(bruto)
        if len(por_tabela) > len(dados["municipios"]):
            print(f"boletim MS: texto corrido só achou {len(dados['municipios'])} vs {len(por_tabela)} por extract_tables() — usando o maior")
            dados["municipios"] = por_tabela
    if len(dados["municipios"]) < MIN_MUNICIPIOS:
        registrar_lacuna("SES-MS (tabela municipal incompleta)", f"só {len(dados['municipios'])} de ~79 municípios reconhecidos (texto e extract_tables()) — resultado recusado", canal="site_estadual", camada=2, strings=[pdf_url])
        print(f"boletim MS: tabela municipal incompleta ({len(dados['municipios'])} municípios) — recusado, nada publicado"); return 0
    # acumula a série própria do Monitor (o boletim da SES só dá o instantâneo da semana + totais anuais, não a série semanal histórica)
    serie = ler("saude_desfechos/ses_ms_dengue.json", {"_governanca": "Dengue por município, Mato Grosso do Sul — lido do boletim semanal da SES-MS (SINAN Online). " + RESSALVA + " Série semanal construída pelo próprio Monitor a partir de 10/09/2026 (a SES só publica o instantâneo da semana e o total anual, não a série semanal histórica). Peso zero; nunca lido pelo motor.", "serie": {}})
    chave = f"{dados['referencia']['ano']}-{dados['referencia']['se']:02d}"
    serie.setdefault("serie", {})[chave] = dados
    serie["ultima_atualizacao"] = hoje.strftime("%d/%m/%Y"); serie["fonte_pdf_mais_recente"] = pdf_url
    gravar("saude_desfechos/ses_ms_dengue.json", serie)
    log_busca("site_estadual", 2, [pdf_url], "registro", nivel="estadual", n_resultados=len(dados["municipios"]), resultados=f"SES-MS: boletim SE {dados['referencia']['se']}/{dados['referencia']['ano']} lido — {len(dados['municipios'])} municípios, {dados['totais_estaduais']['casos_provaveis']} casos prováveis")
    print(f"boletim MS: SE {dados['referencia']['se']}/{dados['referencia']['ano']} — {len(dados['municipios'])} municípios, {dados['totais_estaduais']['casos_provaveis']} casos prováveis, {dados['totais_estaduais']['casos_confirmados']} confirmados")
    return 0


def autoteste() -> int:
    TXT = """CENÁRIO EM MATO GROSSO DO SUL, 2026
Semana Epidemiológica 30/2026
4.669 1.873 1 1
Casos 
prováveis
Casos
confirmados
Óbitos em 
investigação
Óbitos 
confirmados
Fonte: SINAN Online – Dados parciais, sujeitos a alterações pelos municípios. Atualizado até SE 30, 03 de agosto de 2026.
Ranking IBGE Município Casos Prováveis População Incidência
1 5007554 Santa Rita do Pardo 144 7.027 2.049,2 Alta
2 5003207 Corumbá 1698 96.268 1.763,8 Alta
26 5008404 Vicentina 13 6.336 205,2
79 5007802 Selvíria 0 8.142 0,0 Sem notificação
"""
    def t_listagem():
        # HTML real observado em 11/09/2026 na listagem da SES-MS (navegador): travessão U+2013 no nome
        html = ('<a href="https://www.saude.ms.gov.br/wp-content/uploads/2026/09/Boletim-Epidemiologico-Chikungunya-\u2013-Semana-34-\u2013-2026.pdf">x</a>'
                '<a href="https://www.saude.ms.gov.br/wp-content/uploads/2026/09/Boletim-Epidemiologico-Dengue-\u2013-Semana-33-\u2013-2026.pdf">x</a>'
                '<a href="https://www.saude.ms.gov.br/wp-content/uploads/2026/09/Boletim-Epidemiologico-Dengue-\u2013-Semana-34-\u2013-2026.pdf">x</a>'
                '<a href="https://www.saude.ms.gov.br/wp-content/uploads/2025/09/Boletim-Epidemiologico-Dengue-\u2013-Semana-40-\u2013-2025.pdf">ano anterior</a>')
        r = extrair_pdfs_da_listagem(html, 2026)
        # só dengue, só 2026, mais recente primeiro, sem repetir SE
        return r and r[0][1] == 34 and r[0][0].endswith("Semana-34-\u2013-2026.pdf") and [se for _, se in r] == [34, 33] and extrair_pdfs_da_listagem(html, 2027) == []

    def t_extract_tables():
        # 12/09/2026: gera um PDF real (reportlab) com uma tabela no mesmo formato da SES-MS e confere que
        # extract_tables() do pdfplumber recupera as linhas certas — inclusive os dois casos difíceis: sem
        # classificação (Vicentina) e "Sem notificação" com vírgula na incidência (Selvíria). PDF real, não
        # texto sintético: prova que o caminho de bytes -> pdfplumber -> células funciona de ponta a ponta.
        import io as _io
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
        from reportlab.lib import colors
        linhas = [["Ranking", "IBGE", "Município", "Casos Prováveis", "População", "Incidência", ""],
                  ["1", "5007554", "Santa Rita do Pardo", "144", "7.027", "2.049,2", "Alta"],
                  ["26", "5008404", "Vicentina", "13", "6.336", "205,2", ""],
                  ["79", "5007802", "Selvíria", "0", "8.142", "0,0", "Sem notificação"]]
        buf = _io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4)
        t = Table(linhas); t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.black)]))
        doc.build([t])
        m = extrair_municipios_por_tabela(buf.getvalue())
        return (len(m) == 3 and m["5007554"] == {"nome": "Santa Rita do Pardo", "casos_provaveis": 144, "populacao": 7027, "incidencia": 2049.2, "classificacao": "Alta"}
                and m["5008404"]["classificacao"] is None and m["5007802"]["incidencia"] == 0.0 and m["5007802"]["classificacao"] == "Sem notificação")

    def t_ordem_invertida():
        # 12/09/2026: a SES-MS não usa layout fixo — a SE 30 trazia números antes dos rótulos; a SE 34,
        # na mesma seção, trazia os rótulos ANTES dos números. Ambos vieram de PDFs reais.
        se34 = ("BOLETIM EPIDEMIOLOGICO\nDENGUE\nSemana Epidemiológica 34/2026\n"
                "Data de publicação: 04 de setembro de 2026\nCENÁRIO EM MATO GROSSO DO SUL, 2026\n"
                "Casos Casos Óbitos em Óbitos\nprováveis confirmados investigação\nconfirmados\n4.465 2.081 2 1\n"
                "Fonte: SINAN Online – Dados parciais, sujeitos a alterações pelos municípios. "
                "Atualizado até SE 34, 29 de agosto de 2026.")
        return parse_texto(se34)["totais_estaduais"] == {"casos_provaveis": 4465, "casos_confirmados": 2081, "obitos_investigacao": 2, "obitos_confirmados": 1}

    def t_normalizacao():
        # 12/09/2026: o bloco de totais tem de bater não importa como o extrator quebra linha —
        # verificado localmente contra o texto de verdade do boletim SE 30/2026 (fetch fora do sandbox).
        variantes = [
            "4.669 1.873 1 1\nCasos \nprováveis\nCasos\nconfirmados\nÓbitos em \ninvestigação\nÓbitos \nconfirmados",
            "4.669 1.873 1 1 Casos prováveis Casos confirmados Óbitos em investigação Óbitos confirmados",
            "4.669 1.873 1 1\nCasos prováveis Casos confirmados\nÓbitos em investigação Óbitos confirmados",
        ]
        base = "Atualizado até SE 30, 03 de agosto de 2026.\n"
        return all(parse_texto(base + v)["totais_estaduais"] == {"casos_provaveis": 4669, "casos_confirmados": 1873, "obitos_investigacao": 1, "obitos_confirmados": 1} for v in variantes)

    def t1():
        d = parse_texto(TXT); return d["referencia"] == {"ano": 2026, "se": 30, "data": "03/08/2026"}
    def t2():
        d = parse_texto(TXT); return d["totais_estaduais"] == {"casos_provaveis": 4669, "casos_confirmados": 1873, "obitos_investigacao": 1, "obitos_confirmados": 1}
    def t3():
        d = parse_texto(TXT); m = d["municipios"]["5007554"]; return m["nome"] == "Santa Rita do Pardo" and m["casos_provaveis"] == 144 and m["incidencia"] == 2049.2 and m["classificacao"] == "Alta"
    def t4():
        d = parse_texto(TXT); return d["municipios"]["5008404"]["classificacao"] is None and d["municipios"]["5007802"]["classificacao"] == "Sem notificação"
    def t5():
        try:
            parse_texto("nada aqui bate com o padrão esperado"); return False
        except ValueError:
            return True
    def t6():
        html = '<a href="https://www.saude.ms.gov.br/wp-content/uploads/2026/08/Boletim-Epidemiologico-Dengue-%E2%80%93-Semana-30-%E2%80%93-2026.pdf">baixar</a>'
        return extrair_pdf_do_post(html) is not None and extrair_pdf_do_post("<p>nada</p>") is None
    def t7():
        return "não atribui casos ao El Niño" in RESSALVA and MIN_MUNICIPIOS < 79
    return rodar_autoteste({"tabela municipal via extract_tables() (PDF real gerado)": t_extract_tables,"totais com rótulos ANTES dos números (texto real da SE 34)": t_ordem_invertida,"totais estaduais robusto a qualquer quebra de linha (texto real da SE 30)": t_normalizacao,"listagem: PDFs de dengue do ano, mais recente primeiro": t_listagem,"referência SE e data": t1, "totais estaduais (4 números antes dos rótulos)": t2,
                            "linha municipal completa": t3, "classificação ausente/tolerada": t4,
                            "formato inesperado nunca adivinha": t5, "extração do link do PDF no post": t6, "ressalva e limiar de segurança": t7})


if __name__ == "__main__":
    sys.exit(autoteste() if "--autoteste" in sys.argv else coletar())
