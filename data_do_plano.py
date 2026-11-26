"""data_do_plano.py — a data que o plano de contingência informa de si. Funções puras; sem rede e sem arquivo.

METODOLOGIA §129: a idade do plano conta "pela data da edição ou da última atualização que o próprio plano declara".
Até 25/11/2026 o juiz tomava como data o primeiro ano de quatro dígitos do texto (`RE_ANO_OU_CICLO`) e, por cima,
o primeiro ano não citado dos 1.500 caracteres iniciais (`ano_do_plano`). Medido nos 452 planos da pasta do RS: 198
ficavam só com o ano tendo dia ou mês no documento; 22 ganhavam o ano de um evento do histórico, de estimativa de
população ou de citação bibliográfica (Ajuricaba 2017, Palmeira das Missões 2004, Rio dos Índios 2005); 8, o ano
errado (Sério 2012 × 23/10/2025). Aqui a data é lida onde o documento se data: marca de atualização, versão, edição ou
elaboração; capa; fecho com local e data; assinatura digital. Lei citada, censo, receita, histórico de eventos,
referência bibliográfica e data futura anunciada não datam o plano. A data com hora (impressão do formulário no
sistema estadual) sai à parte, em `carimbo_de_impressao`: quem decide se ela conta é o chamador.

Uso: `data_do_plano(texto, municipio, ano_corrente)` -> (data, origem, trecho); `python3 data_do_plano.py --autoteste`.
"""
import re
import unicodedata

_MESES = "janeiro fevereiro marco abril maio junho julho agosto setembro outubro novembro dezembro".split()
MES = {**{m: i for i, m in enumerate(_MESES, 1)}, **{m[:3]: i for i, m in enumerate(_MESES, 1)}}   # "dez." também
_M = r"(" + "|".join(_MESES) + r"|(?:jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)(?=\.?[\s/,-]))\.?"
_A = r"((?:19|20)\d{2})"
ANO_MINIMO, CAPA, FRENTE, FECHO = 1990, 1000, 6000, 1500

# As grafias de data, da mais precisa à menos precisa. Tudo é lido no texto sem acento e em minúsculas.
RE_NUMERICA = re.compile(r"(?<![\d/.])(\d{1,2})[/.](\d{1,2})[/.]" + _A + r"(?![\d/])")
RE_ISO = re.compile(r"(?<![\d/.-])" + _A + r"[-.](\d{2})[-.](\d{2})(?![\d/-])")
RE_EXTENSO = re.compile(r"(?<!\d)(\d{1,2})[ºo°]?\s+(?:de\s+|e\s+)?" + _M + r"\s+(?:de\s+)?" + _A + r"(?!\d)")
RE_MES_BARRA_ANO = re.compile(r"(?<![a-z])" + _M + r"\s?[/l|\[]\s?" + _A + r"(?!\d)")        # "março/2026", "maio/ 2025"; OCR: "julho [ 2023"
RE_MES_ANO = re.compile(r"(?<![a-z])" + _M + r"(?:\s*(?:,|-|de|do)){0,2}\s*" + _A + r"(?!\d)")   # "junho de 2026", "maio, 2025", "abril de, 2025"
RE_MES_NUM_ANO = re.compile(r"(?<![\d/.-])(0?[1-9]|1[0-2])/" + _A + r"(?![\d/])")
RE_ANO = re.compile(r"(?<!\d)(?<!\d[/.,-])" + _A + r"(?![/.-]?\d)")
RE_PERIODO = re.compile(r"(?<!\d)(?<!\d[/.,-])" + _A + r"\s?[/-]\s?(?:(?:19|20)\d{2}|\d{2})(?!\d)")   # "2025/2026": vale o primeiro ano

# O que NÃO data o plano, esteja onde estiver: ato citado, e o que vem depois destas palavras.
RE_ATO_CITADO = re.compile(
    r"\b(?:leis?|decretos?|portarias?|resolucao|resolucoes|instrucao\s+normativa|medida\s+provisoria|doe|dou|diario\s+oficial)\b"
    r"(?:[\s\d.,/ºo°ª()-]|\bn[º°o.]*|\bde\b|\be\b|\bfedera(?:l|is)\b|\bmunicipa(?:l|is)\b|\bestadua(?:l|is)\b|"
    r"\bcomplementar(?:es)?\b|\b" + _M + r"\b)*")
RE_COM_HORA = re.compile(r"\d{1,2}/\d{1,2}/\d{2,4}\s*[,.-]?\s*(?:as\s+)?\d{1,2}[:h.]\d{2}")   # impressão ou emissão
RE_ANTES_NAO_DATA = re.compile(
    r"(?:censo|ibge|populacao|habitantes|estimativa|rcl|receita|pib|idhm|fundad[oa]|fundacao|criad[oa]|criacao|emancipad[oa]|"
    r"emancipacao|instalad[oa]|instalacao|aniversario|\bn[º°o.]|validade|valid[oa]\s+ate|vigencia\s+ate|proxim[oa]|previst[oa]|"
    r"programad[oa]|administracao|gestao|mandato|quadrienio|ocorr(?:eu|ido|ida|encia|eram)|historico|safra|exercicio|acesso)"
    r"(?:\s+(?:em|de|do|da|no|na|dia|ate))?[^a-z]{0,14}$"
    r"|(?:enchentes?|inundac(?:ao|oes)|enxurradas?|estiagem|seca|chuvas?|eventos?|desastres?|anos?)\s+(?:em|de|do|da|no|na)\s[^a-z]{0,6}$"
    r"|(?:rcl|receita)[^a-z]{0,4}(?:r\$)?[^a-z]{0,24}$"      # "RCL: R$ 29.469.541,45 (Janeiro/2024 a Dezembro/2024)"
    r"|\([a-z .&;]{2,40},\s?$"                                # "(BRASIL, 2012)"
    r"|\ba\s$")                                               # "janeiro/2024 a dezembro/2024"
RE_PREPOSICAO = re.compile(r"\b(?:em|de|desde|ate|entre|durante|no|na|do|da|a|e|ou|dia|mes\s+de)\s+$")   # data no meio da frase

RE_TITULO = re.compile(
    r"\bplano\s+(?:municipal\s+|estadual\s+)?(?:de\s+)?(?:contingencia|acao\s+e\s+contingencia|protecao\s+e\s+defesa\s+civil|"
    r"operacoes|prevencao)\b|\bplamcon\b|\bplancon\b|\bplacon\b")
RE_SIGLA_COM_ANO = re.compile(r"\b(?:compdec|comdec|comudec|placon|plancon|plamcon|pmpdc|pmpdec)\s?[-/]?\s?" + _A + r"(?!\d)")
RE_UF_COM_ANO = re.compile(r"[/-]\s?[a-z]{2}\s?[.,-]?\s?" + _A + r"(?:\s?[/-]\s?(?:(?:19|20)\d{2}|\d{2}))?(?![/.-]?\d)")   # "x/rs 2025", "x - rs 2021/2024"
RE_UF_COM_MES = re.compile(r"[/-]\s?[a-z]{2}\s?[.,-]?\s?(0?[1-9]|1[0-2])\s?/\s?" + _A + r"(?![/.-]?\d)")                          # "x/rs 03/2025"
RE_ANO_ROTULADO = re.compile(r"(?<![(a-z])ano\s?[-:/]?\s?" + _A + r"(?!\d)")                            # "ano: 2025", "ano-2025"
# Onde o documento diz quando foi feito ou atualizado. A palavra começa ali ("previsão" não é "revisão").
RE_MARCA = re.compile(
    r"(?<![a-z])(?:ultima\s+atualizacao|atualizac(?:ao|oes)|atualizad[oa]|revisao|revisad[oa]|versao(?:\s+de\s+revisao)?|edicao|"
    r"elaborad[oa]|aprovad[oa]\s+em|registro\s+de\s+alteracoes|data\s+de\s+(?:criacao|elaboracao|emissao|aprovacao))(?![a-z])")
JANELA_DA_MARCA, JANELA_DO_REGISTRO, JANELA_DO_TITULO = 60, 300, 110
RE_ASSINATURA = re.compile(
    r"(?:assinado\s+(?:digital|eletronica)mente|assinado\s+de\s+forma\s+digital|digitally\s+signed)[^|]{0,200}?"
    r"(?:dat[ae]|dados)\s?:\s?(?:(\d{1,2})/(\d{1,2})/" + _A + r"|" + _A + r"[.-](\d{2})[.-](\d{2}))")


def sem_acento(s):
    """Minúsculas e sem acento, com o MESMO comprimento do original (as posições valem nos dois)."""
    out = []
    for ch in str(s or ""):
        base = unicodedata.normalize("NFKD", ch)
        out.append((base[0] if base and base[0].isascii() else ch).lower()[:1] or " ")
    return "".join(out)


def _valida(a, m=None, d=None, teto=2100):
    return ANO_MINIMO <= a <= teto and (m is None or 1 <= m <= 12) and (d is None or 1 <= d <= 31)


def datas_em(t, teto, mes_numerico=False, ano=True, com_hora=False, prosa=True):
    """[(posição, (ano, mês, dia), trecho)] das datas escritas em `t` (já sem acento), fora de ato citado e,
    salvo `com_hora`, fora de data com hora. `prosa=False` recusa a data no meio da frase ("em maio de 2024")."""
    fora = [m.span() for m in RE_ATO_CITADO.finditer(t)]
    horas = [m.span() for m in RE_COM_HORA.finditer(t)]
    ocupado, out = [], []

    def anota(m, data, grupo=0):
        i, f = m.span(grupo)
        if any(a < f and i < b for a, b in fora + ocupado) or not _valida(*data, teto=teto):
            return
        if not com_hora and any(a <= i < b for a, b in horas):
            return
        antes = t[max(0, i - 40):i]
        if RE_ANTES_NAO_DATA.search(antes) or (not prosa and RE_PREPOSICAO.search(antes)):
            ocupado.append((i, f))
            return
        out.append((i, data, t[i:f]))
        ocupado.append((i, f))

    for m in RE_NUMERICA.finditer(t):
        anota(m, (int(m.group(3)), int(m.group(2)), int(m.group(1))))
    for m in RE_ISO.finditer(t):
        anota(m, (int(m.group(1)), int(m.group(2)), int(m.group(3))))
    for m in RE_EXTENSO.finditer(t):
        anota(m, (int(m.group(3)), MES[m.group(2)], int(m.group(1))))
    for m in RE_MES_BARRA_ANO.finditer(t):
        anota(m, (int(m.group(2)), MES[m.group(1)], None))
    for m in RE_MES_ANO.finditer(t):
        anota(m, (int(m.group(2)), MES[m.group(1)], None))
    if mes_numerico:
        for m in RE_MES_NUM_ANO.finditer(t):
            anota(m, (int(m.group(2)), int(m.group(1)), None))
    if ano:
        for m in RE_PERIODO.finditer(t):
            anota(m, (int(m.group(1)), None, None))
        for m in RE_ANO.finditer(t):
            anota(m, (int(m.group(1)), None, None))
    return sorted(out)


def _teto(d):
    return (d[0], d[1] or 12, d[2] or 31)


def _precisao(d):
    return (d[1] is not None) + (d[2] is not None)


def _detalha(geral, fina):
    """`fina` é a mesma data de `geral`, com mais precisão?"""
    return (geral[0] == fina[0] and (geral[1] is None or geral[1] == fina[1])
            and (geral[2] is None or geral[2] == fina[2]) and _precisao(fina) > _precisao(geral))


def formatar(d):
    a, m, dia = d
    return f"{dia:02d}/{m:02d}/{a}" if dia else f"{m:02d}/{a}" if m else str(a)


RE_VERSAO_COM_ANO = re.compile(r"(?<![\d/.])(?:v\.?\s?)?\d{1,2}\s?/\s?" + _A + r"(?!\d)")    # "versão 01/2026", "v.5/2026"
RE_ASSINATURA_ADOBE = re.compile(r"\bdat[ae]\s?:\s?" + _A + r"\.(\d{2})\.(\d{2})\s+\d{2}:\d{2}:\d{2}\s?[-+]\d{2}'\d{2}'")
# Legenda de figura, tabela ou fonte ("FIGURA 02: … SEMUSA, Porto Velho, 2019."): o local e o ano são do dado, não do plano.
RE_LEGENDA = re.compile(r"\b(?:figura|grafico|tabela|quadro|mapa|foto|fonte)\s?\d*\s?[:.–-][^.]{0,140}$")
RE_REFERENCIA = re.compile(r"^.{0,30}(?:disponivel\s+em|acesso\s+em)")


def candidatas(texto, municipio=None, ano_corrente=None):
    """[(data, origem, trecho)] de tudo o que data o plano no documento."""
    bruto = re.sub(r"\s+", " ", str(texto or ""))   # a extração deixa quebras e espaços duplos na capa ("São  José  (SC),  2025")
    bruto = re.sub(r"(?<!\d)([12])\s(\d)\s(\d)\s(\d)(?!\d)", r"\1\2\3\4", bruto)    # OCR: "2 0 2 5"
    bruto = re.sub(r"(?<!\d)((?:19|20)\d)\s(\d)(?!\d)(?!\s?[/.]\d)", r"\1\2", bruto)             # OCR: "201 8"
    t = sem_acento(bruto)
    if not ano_corrente:
        from coletores_base import hoje_editorial
        ano_corrente = hoje_editorial().year
    teto, out = ano_corrente, []
    blocos = [(0, t[:FRENTE])] + ([(len(t) - FECHO, t[-FECHO:])] if len(t) > FRENTE + FECHO else [])
    nome = re.escape(sem_acento(municipio)).replace(r"\ ", r"\s+") if municipio else None

    def junta(data, origem, i, f):
        if _valida(*data, teto=teto):
            out.append((data, origem, re.sub(r"\s+", " ", bruto[i:f]).strip()[:160]))

    def marca(base, bloco, m):
        """A data que segue a palavra de atualização, versão, edição, elaboração ou o registro de alterações."""
        antes = bloco[max(0, m.start() - 30):m.start()]
        if RE_ANTES_NAO_DATA.search(antes) or re.search(r"\bdados\b[^.:]{0,22}$", antes):   # "próxima atualização"; "Dados municipais — última atualização" é do quadro
            return
        palavra = m.group(0)
        janela = bloco[m.end(): m.end() + (JANELA_DO_REGISTRO if palavra.startswith("registro") else JANELA_DA_MARCA)]
        corte = re.search(r"proxim[oa]|previst[oa]|validade", janela)
        janela = janela[:corte.start()] if corte else janela
        so_ano = palavra.startswith(("versao", "edicao")) and "revisao" not in palavra
        achadas = datas_em(janela, teto, mes_numerico=not so_ano, com_hora=True)
        if so_ano:   # "versão 01/2026" é a versão 1 de 2026, não janeiro
            achadas += [(v.start(1), (int(v.group(1)), None, None), v.group(1)) for v in RE_VERSAO_COM_ANO.finditer(janela)]
        if achadas:
            p, d, s = max(achadas, key=lambda x: (_teto(x[1]), _precisao(x[1])))
            finas = [x for x in achadas if _detalha(d, x[1])]
            p, d, s = max(finas, key=lambda x: (_precisao(x[1]), _teto(x[1]))) if finas else (p, d, s)
            junta(d, "atualizacao", base + m.start(), base + m.end() + p + len(s))

    for base, bloco in blocos:
        # 1. Marca de atualização, versão, edição, elaboração.
        for m in RE_MARCA.finditer(bloco):
            if not m.group(0).startswith("registro"):
                marca(base, bloco, m)
        # 2. Capa: mês/ano com barra; sigla, UF ou município seguidos do ano; "ano: 2025"; linha de título.
        for m in RE_MES_BARRA_ANO.finditer(bloco):
            antes = bloco[max(0, m.start() - 40):m.start()]
            if not (RE_ANTES_NAO_DATA.search(antes) or RE_PREPOSICAO.search(antes) or antes.rstrip().endswith("(")):
                junta((int(m.group(2)), MES[m.group(1)], None), "capa", base + m.start(), base + m.end())
        for m in RE_UF_COM_MES.finditer(bloco):
            junta((int(m.group(2)), int(m.group(1)), None), "capa", base + m.start(), base + m.end())
        rotulos = [RE_SIGLA_COM_ANO, RE_UF_COM_ANO, RE_ANO_ROTULADO]
        if nome:
            rotulos.append(re.compile(nome + r"\s?(?:[-/,(]\s?[a-z]{2}\s?\)?)?\s?[,.-]?\s?" + _A + r"(?:\s?[/-]\s?(?:(?:19|20)\d{2}|\d{2}))?(?![/.-]?\d)"))
        for rx in rotulos:
            for m in rx.finditer(bloco):
                if not (RE_ANTES_NAO_DATA.search(bloco[max(0, m.start() - 40):m.start()])
                        or RE_LEGENDA.search(bloco[max(0, m.start() - 160):m.start()])):
                    junta((int(m.group(1)), None, None), "capa", base + m.start(), base + m.end())
        for m in RE_TITULO.finditer(bloco):   # o título e, logo depois, a data, sem outro número nem citação no meio
            janela = bloco[m.end(): m.end() + JANELA_DO_TITULO]
            for p, d, s in datas_em(janela, teto, mes_numerico=True, prosa=False):
                entre = janela[:p]
                if (not re.search(r"\d|[\u201c\u201d\"]", entre) and not re.search(r"\b(?:que|foi|sera|sao|como|quando|onde|pois)\b", entre)
                        and not (d[1] and not d[2] and "/" in s and re.search(r"versao|edicao", entre))   # "versão: 01/2025"
                        and not RE_REFERENCIA.search(janela[p + len(s):])):
                    junta(d, "capa", base + m.start(), base + m.end() + p + len(s))
                break
    for m in RE_MARCA.finditer(t):   # o registro de alterações e a "última atualização" podem vir depois do sumário
        if m.group(0).startswith(("registro", "ultima")) and not (m.start() < FRENTE and not m.group(0).startswith("registro")):
            marca(0, t, m)
    # 2b. A capa propriamente: data completa ou mês com ano no começo do documento; ano que abre o documento.
    for p, d, s in datas_em(t[:CAPA], teto, mes_numerico=False, ano=False, prosa=False):
        junta(d, "capa", p, p + len(s))
    m = re.match(r"\W{0,3}" + _A + r"(?!\d)", t)
    if m:
        junta((int(m.group(1)), None, None), "capa", m.start(1), m.end(1))
    # 3. Fecho: "Município, 24 de outubro de 2025"; "Data: 17/03/2025" no fim.
    if nome:
        cola = r"\s?(?:[-/,(]\s?[a-z]{2}\s?\)?|\s[a-z]{2})?\s?[,.-]?\s?(?:em\s+)?"
        for rx in (re.compile(nome + cola + r"(\d{1,2})[ºo°]?\s+(?:de\s+|e\s+)?" + _M + r"\s+(?:de\s+)?" + _A),
                   re.compile(nome + cola + r"()" + _M + r"\s+(?:de\s+)?" + _A)):
            for m in rx.finditer(t):
                junta((int(m.group(3)), MES[m.group(2)], int(m.group(1)) if m.group(1) else None), "fecho", m.start(), m.end())
    fim = len(t) - len(t[-800:])
    for m in re.finditer(r"\bdata\s?:\s?(\d{1,2})/(\d{1,2})/" + _A + r"(?!\s*,?\s*\d{1,2}:\d{2})", t[-800:]):
        junta((int(m.group(3)), int(m.group(2)), int(m.group(1))), "fecho", fim + m.start(), fim + m.end())
    # 4. Assinatura digital.
    for m in RE_ASSINATURA.finditer(t):
        junta((int(m.group(3)), int(m.group(2)), int(m.group(1))) if m.group(3)
              else (int(m.group(4)), int(m.group(5)), int(m.group(6))), "assinatura_digital", m.start(), m.end())
    for m in RE_ASSINATURA_ADOBE.finditer(t):
        junta((int(m.group(1)), int(m.group(2)), int(m.group(3))), "assinatura_digital", m.start(), m.end())
    return out


def data_do_plano(texto, municipio=None, ano_corrente=None):
    """(data, origem, trecho) da data que o plano informa de si; (None, None, None) quando não informa.

    Vale a mais recente entre as que datam o documento (marca de atualização ou versão, capa, fecho com local e
    data, assinatura digital); se outra candidata dá a mesma data com mais precisão, fica a mais precisa. Lei
    citada, censo, histórico de eventos, data futura anunciada ("próxima revisão") e data com hora solta
    (impressão do formulário) não datam o plano."""
    cands = candidatas(texto, municipio, ano_corrente)
    if not cands:
        return None, None, None
    melhor = max(cands, key=lambda c: (_teto(c[0]), _precisao(c[0])))
    finas = [c for c in cands if _detalha(melhor[0], c[0])]
    if finas:
        melhor = max(finas, key=lambda c: (_precisao(c[0]), _teto(c[0])))
    return formatar(melhor[0]), melhor[1], melhor[2]


def carimbo_de_impressao(texto, ano_corrente=None):
    """dd/mm/aaaa da primeira data com hora do documento (impressão do formulário no sistema estadual), ou None.
    Não é a data do plano: é o dia em que alguém imprimiu o formulário."""
    if not ano_corrente:
        from coletores_base import hoje_editorial
        ano_corrente = hoje_editorial().year
    for m in RE_COM_HORA.finditer(sem_acento(texto)):
        d = RE_NUMERICA.match(m.group(0))
        if d and _valida(int(d.group(3)), int(d.group(2)), int(d.group(1)), teto=ano_corrente):
            return formatar((int(d.group(3)), int(d.group(2)), int(d.group(1))))
    return None


def autoteste() -> int:
    lei = "PLANO DE CONTINGÊNCIA DE PROTEÇÃO E DEFESA CIVIL. Conforme a Lei nº 12.608, de 10 de abril de 2012, "
    casos = {
        "capa com mês e ano (Aceguá/RS)":
            data_do_plano("PLANO DE CONTINGÊNCIA Municipio de Aceguá/ RS Março/2026. Nome: Aceguá", "Aceguá", 2026)[:2] == ("03/2026", "capa"),
        "a atualização vence a versão e a lei citada (Feliz/RS; Tubarão/SC)":
            data_do_plano(lei + "Feliz/RS 2025. Atualizado 06/08/2026", "Feliz", 2026)[0] == "06/08/2026"
            and data_do_plano("Data da Primeira Versão: 2014 Atualizações: 03/2024 Município de Tubarão/SC", "Tubarão", 2026)[0] == "03/2024",
        "ano de lei citada, de censo, de evento do histórico e de referência não datam o plano (Antônio Prado, Palmeira das Missões, Ajuricaba, Rio dos Índios)":
            all(data_do_plano(t, m, 2026) == (None, None, None) for t, m in (
                (lei + "e mais especificamente ao Art. 22. (BRASIL, 2012).", "Antônio Prado"),
                ("PLANO DE CONTINGÊNCIA MUNICIPAL. Sua população estimada em 2004 era de 36.049 habitantes. Já em 2010, o Censo do IBGE", "Palmeira das Missões"),
                ("PLANO DE CONTINGÊNCIA MUNICIPAL Histórico da recorrência: O EVENTO DE ENXURRADAS OCORREU EM 2017, 2019 e 2022", "Ajuricaba"),
                ("PLANO DE CONTINGÊNCIA MUNICIPAL derrubada de matas nativas da região (SANTOS, 2005, p18).", "Rio dos Índios"))),
        "campo de data em branco não inventa data (Mormaço, Faxinal do Soturno)":
            data_do_plano("PLANCON VERSÃO: Versão 1 ÚLTIMA ATUALIZAÇÃO: 1 SUMÁRIO Leis 12.608, de abril de 2012, e 12.983, de Junho de 2014.", "Mormaço", 2026)[0] is None
            and data_do_plano("PLANO DE CONTINGÊNCIA DEFESA CIVIL FAXINAL DO SOTURNO - RS 2. ANO: [INSERIR ANO] 3.", "Faxinal do Soturno", 2026)[0] is None,
        "o carimbo de impressão do sistema estadual não é a data do plano, e sai à parte (Barra do Guarita)":
            (lambda t: data_do_plano(t, "Barra do Guarita", 2026)[0] is None and carimbo_de_impressao(t, 2026) == "16/11/2023")(
                "16/11/2023, 09:23 SEGIRD - Sistema Estadual de Gestão Integrada de Risco e Desastres PLANO DE CONTINGÊNCIA "
                "MUNICIPAL MUNICÍPIO DE BARRA DO GUARITA Caracterização do Cenário"),
        "fecho com local e data, e a mais recente entre as datas do documento (Campos Borges)":
            data_do_plano("PLANO DE CONTINGÊNCIA Versão de Revisão: 19 de Junho de 2026 Nome: Campos Borges " + "x " * 4000
                          + "Campos Borges - RS, 26 de junho de 2026. Prefeita", "Campos Borges", 2026)[:2] == ("26/06/2026", "fecho"),
        "período na capa vale pelo primeiro ano; versão NN/AAAA é o ano, não o mês (Cerrito; Taió)":
            data_do_plano("PLANO DE CONTINGÊNCIA MUNICIPIO DE CERRITO/ RS 2025 - 2026", "Cerrito", 2026)[0] == "2025"
            and data_do_plano("PLANO DE CONTINGENCIA DE PROTECAO E DEFESA CIVIL Versao 01/2026 O presente plano", "Taió", 2026)[0] == "2026",
        "ano partido pelo OCR e ano fora da faixa (Tobias Barreto; telefone '…-2077')":
            data_do_plano("PLANO DE CONTINGÊNCIA DESLIZAMENTO MUNICIPAL - Versão 201 8 Tobias Barreto - SE", "Tobias Barreto", 2026)[0] == "2018"
            and data_do_plano("PLANO DE CONTINGÊNCIA Versão 2034 Telefone 51 92002-2077", "Chuvisca", 2026)[0] is None,
        "a atualização de um quadro de dados não é a do plano (Balneário Pinhal)":
            data_do_plano("PLANO DE CONTINGÊNCIA " + "x " * 4000 + "Dados Municipais — Última atualização Nov/2023 Quantidade de casas " + "x " * 1000, "Balneário Pinhal", 2026)[0] is None,
        "capa com espaços duplos e quebras é lida; local e ano em legenda de figura não datam (São José/SC, Porto Velho/RO)":
            data_do_plano("PLANO DE CONTINGÊNCIA DA POLÍTICA  DE  ASSISTÊNCIA SOCIAL          São  José  (SC),  2025\n\nSUMÁRIO "
                          "Plamcon da Assistência Social. 2022", "São José", 2026)[0] == "2025"
            and data_do_plano("Plano de Contingência por Seca e Estiagem SECRETARIA MUNICIPAL DE SAÚDE \n \nPORTO VELHO (RO) \n 2024 \n LISTA DE FIGURAS "
                              "FIGURA 02: Distribuição da rede assistencial de saúde na área urbana, SEMUSA, Porto \nVelho, 2019. FIGURA 03",
                              "Porto Velho", 2026)[0] == "2024",
        "assinatura digital data o documento":
            data_do_plano("PLANO DE CONTINGÊNCIA " + "x " * 4000 + "Assinado digitalmente por FULANO Data: 2025.05.29 10:11:12-03'00'", "X", 2026)[:2] == ("29/05/2025", "assinatura_digital"),
    }
    falhas = [n for n, ok in casos.items() if not ok]
    for n in casos:
        print(("  ✓ " if n not in falhas else "  ✗ ") + n)
    print("✓ AUTOTESTE OK" if not falhas else f"✗ AUTOTESTE: {len(falhas)} falha(s)")
    return 1 if falhas else 0


if __name__ == "__main__":
    import sys
    sys.exit(autoteste() if "--autoteste" in sys.argv else 0)
