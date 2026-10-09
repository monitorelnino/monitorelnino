#!/usr/bin/env python3
"""Verificador da fonte das pistas de imprensa — fase 1, modo sombra.

Handover de 29/09/2026, seções A, B, D, E, F, mais a seção G do consolidado. A editoria aceitou que
uma menção de imprensa apareça no cartão do município como "pista encontrada", **sem entrar no
índice**, com uma condição: cada pista passa antes por leitura cuidadosa da página de origem.

**Falsa pista exibida no cartão de uma cidade tem custo reputacional. Em dúvida, não exibe.**

FASE 1 É SOMBRA
---------------
Este script roda, grava em `data/pistas_imprensa.json` o que **exibiria** (`verificacao_fonte`) e
não toca o cartão. A exibição é a fase 2, e só depois do "vai" e de precisão ≥ 95% na amostra.

O QUE ELE NUNCA FAZ
-------------------
- Não decide por título, trecho de busca ou snippet: lê o CORPO da página.
- Não usa modelo de linguagem. As regras são determinísticas e versionadas.
- Não insiste em bloqueio: 403, CAPTCHA, login, robots que veta → `inacessivel`, e pronto.
- Não escreve nenhum campo além de `verificacao_fonte` (um escritor por campo, seção G1).

USO
  python3 verificar_pista_imprensa.py --autoteste
  python3 verificar_pista_imprensa.py --sombra [--limite N]
  python3 verificar_pista_imprensa.py --relatorio
"""
import datetime
import json
import pathlib
import re
import sys
import unicodedata

RAIZ = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

VERSAO = "1.0 (29/09/2026)"
PISTAS = RAIZ / "data" / "pistas_imprensa.json"
VEICULOS = RAIZ / "data" / "veiculos_imprensa.json"
LOCAIS = RAIZ / "data" / "veiculos_locais.json"
CORPO_MINIMO = 300                      # A1: abaixo disso não é matéria, é título ou paywall
DATA_BOLETIM_1 = datetime.date(2026, 6, 29)

# --- B2/B3: marcadores. Dicionários versionados; nada aqui é inferido em tempo de execução. ---
RE_MARCADOR_DO_CICLO = re.compile(
    r"el\s*ni[ñn]o|2026\s*[/-]\s*2027|per[íi]odo\s+chuvoso\s+(?:de\s+)?2026|"
    r"esta[çc][ãa]o\s+chuvosa\s+(?:de\s+)?2026|estiagem\s+(?:de\s+)?2026|seca\s+(?:de\s+)?2026", re.I)
RE_MARCADOR_DE_INSTRUMENTO = re.compile(
    r"plano\s+de\s+conting[êe]ncia|plancon|plano\s+de\s+a[çc][ãa]o|plano\s+de\s+enfrentamento|"
    r"plano\s+preventivo|decreto\s+que\s+institu|institu[ií]\s+o\s+plano|"
    r"opera[çc][ãa]o\s+(?:ver[ãa]o|inverno|estiagem|chuvas|seca)", re.I)
# B4: gênero que não é notícia.
RE_GENERO_VEDADO = re.compile(
    r"/opiniao/|/colunas?/|/artigo/|/editorial/|/blog/|/publieditorial/|/patrocinad|/branded|"
    r"/satira/|/humor/", re.I)
PALAVRAS_DE_GENERO = ("opinião", "opiniao", "coluna", "colunista", "artigo assinado", "editorial",
                      "publieditorial", "conteúdo patrocinado", "conteudo patrocinado",
                      "informe publicitário", "sátira", "satira")
# B1: o município tem de ser SUJEITO da ação, não citação de passagem.
RE_SUJEITO = re.compile(
    r"(?:a\s+)?prefeitura\s+(?:municipal\s+)?d[eoa]s?\s+{alvo}|"
    r"{alvo}\s+(?:publicou|decretou|institu[ií]|aprovou|lan[çc]ou|criou|atualizou|elaborou)|"
    r"munic[íi]pio\s+d[eoa]s?\s+{alvo}\s+(?:publicou|decretou|institu[ií]|aprovou|lan[çc]ou|criou)|"
    r"defesa\s+civil\s+d[eoa]s?\s+{alvo}")
UF_POR_EXTENSO = {
    "AC": "acre", "AL": "alagoas", "AM": "amazonas", "AP": "amapá", "BA": "bahia", "CE": "ceará",
    "DF": "distrito federal", "ES": "espírito santo", "GO": "goiás", "MA": "maranhão",
    "MG": "minas gerais", "MS": "mato grosso do sul", "MT": "mato grosso", "PA": "pará",
    "PB": "paraíba", "PE": "pernambuco", "PI": "piauí", "PR": "paraná", "RJ": "rio de janeiro",
    "RN": "rio grande do norte", "RO": "rondônia", "RR": "roraima", "RS": "rio grande do sul",
    "SC": "santa catarina", "SE": "sergipe", "SP": "são paulo", "TO": "tocantins"}
MOTIVOS = ("texto_insuficiente", "inacessivel", "ente_nao_confirmado", "resposta_a_desastre",
           "natureza_duvidosa", "fora_do_objeto", "sem_marcador_do_ciclo", "fora_do_ciclo",
           "sem_data", "genero_nao_noticia", "veiculo_nao_listado", "sem_https",
           "ja_tem_registro", "recusada_pelo_juiz", "sindicacao_duplicada",
           # 29/09/2026 (item 1): link de agregador que não chegou à página do veículo. NÃO é
           # recusa da fonte nem ausência de matéria — é o nosso lado que não conseguiu abrir.
           "redirecionamento_nao_resolvido")

AGREGADORES = ("news.google.com", "google.com/url", "feedproxy.google.com", "flipboard.com")


def norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode("ascii")
    return " ".join(s.split()).lower()


def corpo_da_pagina(html: str) -> str:
    """Texto do conteúdo, sem menu, rodapé e "leia também". Extração pobre e honesta: tira script,
    style, nav, header, footer e aside, e devolve o texto que sobra.

    Não é leitor de artigo de verdade — e é de propósito: o que interessa é ter texto corrido o
    bastante para os critérios lerem. Abaixo de 300 caracteres a pista não passa, e é assim que
    paywall, página só com título e JS que não renderiza caem fora sem precisar de navegador."""
    t = re.sub(r"(?is)<(script|style|nav|header|footer|aside|form)[^>]*>.*?</\1>", " ", html or "")
    t = re.sub(r"(?is)<!--.*?-->", " ", t)
    t = re.sub(r"(?is)<br\s*/?>|</p>|</div>|</li>", "\n", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    t = (t.replace("&nbsp;", " ").replace("&amp;", "&").replace("&quot;", '"')
          .replace("&#39;", "'").replace("&lt;", "<").replace("&gt;", ">"))
    return "\n".join(l.strip() for l in t.splitlines() if len(l.strip()) > 1)


MESES_PT = {"janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3, "abril": 4, "maio": 5,
            "junho": 6, "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10,
            "novembro": 11, "dezembro": 12}
# A data visível só vale na CABEÇA da matéria — os primeiros caracteres do corpo. Mais abaixo
# aparecem datas de outros assuntos ("a enchente de 2024", "o edital de 12/08"), e tomá-las por
# data de publicação é o erro que este degrau existe para não cometer.
CABECA_DA_MATERIA = 600
RE_DATA_EXTENSO = re.compile(r"\b([0-3]?\d)\s+de\s+([a-zç]+)\s+de\s+(20\d\d)\b", re.I)
RE_DATA_NUMERICA = re.compile(r"\b([0-3]?\d)/([0-1]?\d)/(20\d\d)\b")


def data_de_publicacao(html: str, corpo: str = None) -> tuple:
    """(data, degrau). Data dos METADADOS, nunca a do rastreio.

    Item 2 do bloco de 29/09/2026: a extração vira uma **escada**, e o degrau fica registrado na
    pista — saber de onde veio a data é o que permite desconfiar dela depois.

        1. JSON-LD `datePublished`      — o mais estruturado, e o que mais veículo publica
        2. `article:published_time`     — Open Graph
        3. `<time datetime=…>`          — marcação semântica
        4. data visível na cabeça       — último recurso, e só acima do corpo

    Sem nenhum degrau, `(None, None)`: continua `sem_data`, e sem data não exibe. Matéria de 2015
    recuperada pela busca é a falha mais comum desta fila, e a data é a única coisa que a separa
    de uma de ontem."""
    degraus = [
        ("json_ld", r'"datePublished"\s*:\s*"([^"]+)"'),
        ("og_published_time", r'property=["\']article:published_time["\']\s+content=["\']([^"\']+)'),
        ("og_published_time", r'content=["\']([^"\']+)["\']\s+property=["\']article:published_time["\']'),
        ("time_datetime", r'<time[^>]+datetime=["\']([^"\']+)'),
    ]
    for nome, p in degraus:
        m = re.search(p, html or "", re.I)
        if m:
            try:
                return datetime.date.fromisoformat(m.group(1).strip()[:10]), nome
            except ValueError:
                continue
    if corpo:
        cabeca = corpo[:CABECA_DA_MATERIA]
        m = RE_DATA_EXTENSO.search(cabeca)
        if m:
            mes = MESES_PT.get(norm(m.group(2)))
            if mes:
                try:
                    return datetime.date(int(m.group(3)), mes, int(m.group(1))), "visivel_extenso"
                except ValueError:
                    pass
        m = RE_DATA_NUMERICA.search(cabeca)
        if m:
            try:
                return datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1))), "visivel_numerica"
            except ValueError:
                pass
    return None, None


# =============================================================================================
# Item 1 — o link do agregador não é a fonte; é o caminho até ela
# =============================================================================================
def eh_agregador(url) -> bool:
    u = str(url or "").lower()
    return any(a in u for a in AGREGADORES)


def url_dentro_do_segmento(url: str):
    """A URL do veículo embutida no próprio link, quando o formato a carrega. None quando não.

    O Google News teve dois formatos. O antigo trazia a URL do veículo em base64 dentro do
    caminho — esse se decodifica aqui, sem rede e sem pedir nada a ninguém. O formato em uso
    hoje (`CBMi…AU_yqL…`) é **opaco**: o blob decodifica, mas não contém URL nenhuma; o endereço
    do veículo só chega por uma chamada interna do Google, depois que o JavaScript roda.

    **Essa chamada interna não é usada aqui, e é uma escolha.** Ela é um endpoint não
    documentado, para consumo do próprio site — usá-la seria fazer engenharia reversa de uma API
    privada, não ler documento público. O projeto respeita o que a fonte oferece e declara o que
    não conseguiu: link que não resolve vira `redirecionamento_nao_resolvido`, visível na fila."""
    import base64
    bruto = str(url or "")
    if "/articles/" not in bruto:
        return None
    seg = bruto.split("/articles/", 1)[1].split("?")[0].split("/")[0]
    for pad in range(4):
        try:
            blob = base64.urlsafe_b64decode(seg + "=" * pad)
        except Exception:  # noqa: BLE001
            continue
        achados = re.findall(rb"https?://[\w\-./%?=&+#:]{12,}", blob)
        for a in achados:
            u = a.decode("utf-8", "replace")
            if not eh_agregador(u):
                return u
        break
    return None


def busca_no_veiculo(veiculo, titulo, buscar_web) -> str:
    """Degrau 3 (09/10/2026, lote 2.6, A1-08): a matéria procurada no PRÓPRIO veículo, pelo título.

    O feed do Google News grava o `<source url>` (o veículo) e o título em toda pista, e ninguém os
    usava: 2.876 pistas ficaram abertas para sempre com o link opaco do agregador. A busca é
    restrita ao host do veículo e só aceita URL nesse host (ou subdomínio dele) com caminho — nunca
    a home, nunca outro site. Sem resultado assim, devolve None: não se chuta."""
    from urllib.parse import urlsplit
    host = dominio_de(veiculo)
    titulo = " ".join(str(titulo or "").split())
    # o Google News acrescenta " - Nome do Veículo" ao título
    titulo = re.sub(r"\s+-\s+[^-]{2,60}$", "", titulo)[:80].strip()
    if not host or not titulo or buscar_web is None:
        return None
    try:
        resultados = buscar_web(f'site:{host} "{titulo}"') or []
    except Exception:  # noqa: BLE001
        return None
    for r in resultados:
        u = r.get("url") if isinstance(r, dict) else r
        d = dominio_de(u)
        if d and (d == host or d.endswith("." + host)) and urlsplit(str(u)).path.strip("/"):
            return u
    return None


def resolver_redirecionamento(url: str, abrir=None, tentativas: int = 2, veiculo=None,
                              titulo=None, buscar_web=None) -> tuple:
    """(url_final, como). `como` diz por qual degrau resolveu, ou por que não.

    Duas rotas, nesta ordem, e nenhuma delas pede nada além do que a fonte serve:
      1. **redirecionamento HTTP** — o agregador manda para o veículo, e o cliente segue;
      2. **URL embutida no link**, quando o formato a carrega.

    Sem as duas, em `tentativas` tentativas, devolve (None, "redirecionamento_nao_resolvido"). O
    handover pediu exatamente isso, e a razão é que o contrário seria pior: chutar o veículo a
    partir do título, ou tratar o domínio do agregador como se fosse a fonte."""
    if not eh_agregador(url):
        return url, "nao_era_agregador"
    embutida = url_dentro_do_segmento(url)
    if embutida:
        return embutida, "url_embutida_no_link"
    for _ in range(max(1, tentativas)) if abrir is not None else ():
        try:
            final = abrir(url)
        except Exception:  # noqa: BLE001
            continue
        if final and not eh_agregador(final):
            return final, "redirecionamento_http"
    achada = busca_no_veiculo(veiculo, titulo, buscar_web)
    if achada:
        return achada, "busca_no_veiculo"
    return None, "redirecionamento_nao_resolvido"


def abrir_seguindo_redirecionamento(url: str, timeout: int = 30):
    """A URL final depois de seguir os redirecionamentos, pelo cliente identificado do projeto."""
    import urllib.request
    from coletores_base import UA, contexto_tls, url_ascii
    req = urllib.request.Request(url_ascii(url), headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout, context=contexto_tls()) as r:
        return r.url


# =============================================================================================
# Item 3 — a lista de veículos cresce por CRITÉRIO, não por leitura humana de cada domínio
# =============================================================================================
BLOQUEADOS = RAIZ / "data" / "dominios_bloqueados.json"
MATERIAS_MINIMAS = 2          # o domínio precisa aparecer em mais de uma matéria da fila
RE_EXPEDIENTE = re.compile(
    r"/(?:expediente|quem-?somos|sobre-?nos|sobre|contato|fale-?conosco|institucional)\b", re.I)
RE_CNPJ = re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b")


# 30/09/2026 (decisão da editoria, caso CEIVAP) — a lista de veículos aceita SÓ IMPRENSA.
#
# `ceivap.org.br` entrou pela entrada automática cumprindo os quatro sinais do item 3: HTTPS, página
# de expediente, nome localizável e itens na fila. Não é imprensa: é o Comitê de Integração da Bacia
# Hidrográfica do Rio Paraíba do Sul, órgão colegiado do sistema de recursos hídricos, e os itens
# eram PDFs de Planos Municipais de Saneamento Básico hospedados no sítio dele. O defeito não estava
# em nenhum dos quatro sinais: estava no que eles NÃO perguntavam. Um sítio institucional tem
# expediente, tem HTTPS e publica documento — e não é veículo.
#
# Dois sinais novos, ambos obrigatórios, e uma exclusão por padrão. Sítio de órgão, comitê, agência,
# associação, consórcio, ONG, universidade ou empresa **não é bloqueado**: é fonte institucional, e o
# caminho dela é o juiz, com documento primário. Vai para `data/dominios_institucionais.json`, que é
# encaminhamento, não punição — confundir as duas listas jogaria fonte oficial no lixo.
RE_IDENTIDADE_JORNALISTICA = re.compile(
    r"\b(jornal|jornalismo|jornalista|portal de not[ií]cias|site de not[ií]cias|r[áa]dio|"
    r"emissora|tv\b|televis[ãa]o|ag[êe]ncia de not[ií]cias|reda[çc][ãa]o|editor[ -]?chefe|"
    r"editora[ -]?chefe|chefe de reda[çc][ãa]o|jornal[íi]stico|jornal[íi]stica)\b", re.I)
RE_INSTITUCIONAL = re.compile(
    r"\b(comit[êe] (?:de )?(?:bacia|integra[çc][ãa]o)|comit[êe] de bacia|ag[êe]ncia reguladora|"
    r"autarquia|ag[êe]ncia nacional|cons[óo]rcio (?:p[úu]blico|intermunicipal)|"
    r"associa[çc][ãa]o (?:de|dos|das)|federa[çc][ãa]o (?:de|dos|das)|sindicato|"
    r"conselho (?:municipal|estadual|nacional|deliberativo|gestor)|"
    r"universidade|instituto federal|funda[çc][ãa]o (?:p[úu]blica|estadual|municipal)|"
    r"organiza[çc][ãa]o (?:n[ãa]o governamental|da sociedade civil)|oscip|"
    r"secretaria (?:de|municipal|estadual)|minist[ée]rio (?:da|do|de)|"
    r"empresa (?:p[úu]blica|de economia mista)|sistema de recursos h[íi]dricos)\b", re.I)
INSTITUCIONAIS = RAIZ / "data" / "dominios_institucionais.json"
MATERIAS_DATADAS_MINIMAS = 3
CAMINHOS_DE_NOTICIAS = ("/", "/noticias", "/notícias", "/ultimas-noticias")


RE_TIME_DATETIME = re.compile(r"<time[^>]*datetime=[\"']20\d\d-[01]\d-[0-3]\d", re.I)
RE_DATA_RELATIVA = re.compile(r"\bh[áa]\s+\d+\s+(?:minuto|hora|dia|semana)s?\b", re.I)


def tem_secao_de_noticias(paginas: dict) -> bool:
    """True quando alguma página do domínio mostra pelo menos três itens com MARCA DE TEMPO.

    Este é o sinal que o sítio institucional não tem: ele publica documento, e documento não vem
    numa lista de manchetes com hora ao lado. Três, não uma, porque uma data solta aparece em
    qualquer rodapé de "atualizado em".

    **Conta-se a marca de tempo como a imprensa a escreve**, não como seria conveniente medir: data
    por extenso, data numérica, `<time datetime>` e o "há 2 horas" das capas. A primeira versão
    exigia data literal no texto e reprovou `ndmais.com.br` e `abcdoabc.com.br`, que são jornais de
    verdade — critério que derruba o caso típico está medindo a própria implementação, não o mundo."""
    for html in (paginas or {}).values():
        texto = corpo_da_pagina(html)
        marcas = (len(set(RE_DATA_EXTENSO.findall(texto)))
                  + len(set(RE_DATA_NUMERICA.findall(texto)))
                  + len(RE_TIME_DATETIME.findall(html or ""))
                  + len(set(m.lower() for m in RE_DATA_RELATIVA.findall(texto or ""))))
        if marcas >= MATERIAS_DATADAS_MINIMAS:
            return True
        if len(RE_ITEM_DE_FEED.findall(html or "")) >= MATERIAS_DATADAS_MINIMAS:
            return True
    return False


# Cargo de redação no expediente é marca de imprensa tão forte quanto capa datada — e funciona onde
# a capa não funciona. `plantaoguaruja.com.br` e `abcdoabc.com.br` são jornais, têm DIRETOR e
# EDITOR-CHEFE no expediente, e a home deles devolve "Aguarde, carregando..." porque é renderizada
# por JavaScript. Exigir só a capa datada expulsaria os dois, e expulsar veículo real por limitação
# da minha sonda seria perder prova para preservar a regra.
RE_CARGO_DE_REDACAO = re.compile(
    r"\b(editor[ -]?chefe|editora[ -]?chefe|chefe de reda[çc][ãa]o|diretor de reda[çc][ãa]o|"
    r"diretor[ae]? respons[áa]vel|editor[ae]? geral|jornalista respons[áa]vel|"
    r"reda[çc][ãa]o)\b", re.I)
AUTODESCRICAO = 700


def tem_cargo_de_redacao(paginas: dict) -> str:
    """O cargo de redação encontrado no expediente, ou string vazia."""
    for url, html in (paginas or {}).items():
        if not RE_EXPEDIENTE.search(str(url)):
            continue
        m = RE_CARGO_DE_REDACAO.search(corpo_da_pagina(html))
        if m:
            return m.group(0)
    return ""


def eh_sitio_institucional(paginas: dict) -> str:
    """O termo institucional encontrado na AUTODESCRIÇÃO do sítio, ou string vazia.

    Onde se lê é decisivo. A primeira versão varria a página inteira e transformava jornal em
    instituição porque a capa trazia "Secretaria de" numa manchete — `horacampinas.com.br`,
    `portaldoholanda.com.br` e outros dois caíram assim. Jornal fala de órgão público todo dia; o
    que distingue o sítio institucional é ele **dizer que é um**, e isso está no começo da página de
    expediente, onde mora o "somos". Fora do expediente não se lê nada: manchete não define dono."""
    for url, html in (paginas or {}).items():
        if not RE_EXPEDIENTE.search(str(url)):
            continue
        m = RE_INSTITUCIONAL.search(corpo_da_pagina(html)[:AUTODESCRICAO])
        if m:
            return m.group(0)
    return ""


def tem_identidade_jornalistica(paginas: dict) -> str:
    """O termo jornalístico encontrado na página de expediente, ou string vazia."""
    for url, html in (paginas or {}).items():
        if not RE_EXPEDIENTE.search(str(url)):
            continue
        m = RE_IDENTIDADE_JORNALISTICA.search(corpo_da_pagina(html))
        if m:
            return m.group(0)
    return ""


def sinais_de_veiculo(dominio: str, paginas: dict, materias: int) -> dict:
    """Os quatro sinais do item 3, medidos — e o que faltou, quando falta.

    `paginas` é {caminho: html} do que se conseguiu abrir no próprio domínio. A função é pura: quem
    baixa é o chamador, e é isso que permite provar a regra sem rede."""
    tem_https = any(str(u).lower().startswith("https://") for u in paginas)
    achou_expediente = None
    tem_nome_ou_cnpj = False
    for url, html in (paginas or {}).items():
        if not RE_EXPEDIENTE.search(str(url)):
            continue
        achou_expediente = url
        texto = corpo_da_pagina(html)
        # Nome do veículo: o domínio sem o sufixo, escrito por extenso em algum lugar da página.
        # Compara-se sem espaço nem hífen dos dois lados, porque o domínio junta o que o nome
        # separa: `horacampinas.com.br` e "Hora Campinas" são o mesmo veículo.
        def _colado(s):
            return re.sub(r"[\s\-]+", "", norm(s))
        raiz = _colado(str(dominio).split(".")[0])
        if raiz and raiz in _colado(texto):
            tem_nome_ou_cnpj = True
        if RE_CNPJ.search(texto):
            tem_nome_ou_cnpj = True
        if tem_nome_ou_cnpj:
            break
    return {"https": tem_https, "expediente": achou_expediente,
            "nome_ou_cnpj": tem_nome_ou_cnpj, "materias_na_fila": materias,
            "materias_suficientes": materias >= MATERIAS_MINIMAS,
            "identidade_jornalistica": tem_identidade_jornalistica(paginas),
            "secao_de_noticias": tem_secao_de_noticias(paginas),
            "cargo_de_redacao": tem_cargo_de_redacao(paginas),
            "termo_institucional": eh_sitio_institucional(paginas)}


def pode_entrar(dominio: str, sinais: dict, bloqueados: set) -> tuple:
    """(entra, motivo). Todos os sinais são obrigatórios — não há nota média, como no verificador.

    Um domínio bloqueado não é avaliado: é recusado antes, porque agregador com expediente e HTTPS
    continua sendo agregador."""
    d = str(dominio or "").lower()
    if not d:
        return False, "sem_dominio"
    if any(b == d or d.endswith("." + b) for b in bloqueados):
        return False, "dominio_bloqueado"
    de_ente = eh_dominio_de_ente(d)
    if de_ente:
        # Sítio de governo é fonte oficial, outro canal, com outras exigências de prova. Entrar na
        # lista de VEÍCULOS confundiria "imprensa descobre" com "documento registra", que é a
        # distinção em que todo o método se apoia.
        return False, de_ente
    if not sinais.get("https"):
        return False, "sem_https"
    if not sinais.get("expediente"):
        return False, "sem_pagina_de_expediente"
    if not sinais.get("nome_ou_cnpj"):
        return False, "expediente_sem_nome_nem_cnpj"
    if not sinais.get("materias_suficientes"):
        return False, f"menos_de_{MATERIAS_MINIMAS}_materias_na_fila"
    # A exclusão institucional vem ANTES da identidade jornalística, de propósito: um comitê de bacia
    # que cite "nossa redação" em algum lugar continua não sendo imprensa, e a ordem inversa deixaria
    # a palavra solta vencer o que o sítio é.
    if sinais.get("termo_institucional"):
        return False, "sitio_institucional_nao_e_veiculo"
    if not sinais.get("identidade_jornalistica"):
        return False, "expediente_sem_identidade_jornalistica"
    if not (sinais.get("secao_de_noticias") or sinais.get("cargo_de_redacao")):
        return False, "sem_vitrine_datada_nem_cargo_de_redacao"
    return True, ""


def registrar_institucionais(itens: list, hoje) -> dict:
    """Encaminha o domínio institucional, em vez de descartá-lo.

    `data/dominios_institucionais.json` **não é lista de bloqueio**. Quem está nela é fonte oficial
    ou institucional, cujo caminho é o juiz com documento primário — não o verificador de imprensa.
    Tratar as duas listas como uma jogaria fonte oficial no lixo, que é o oposto do que o método
    quer."""
    from coletores_base import gravar_em
    doc = {}
    if INSTITUCIONAIS.exists():
        doc = json.loads(INSTITUCIONAIS.read_text(encoding="utf-8")) or {}
    doc.setdefault("_governanca", "Domínios institucionais ou oficiais que NÃO são veículos de "
                                  "imprensa. Não é lista de bloqueio: o caminho deles é o juiz, com "
                                  "documento primário. Decisão da editoria de 30/09/2026 (CEIVAP).")
    lista = doc.setdefault("dominios", [])
    tem = {str(x.get("dominio", "")).lower() for x in lista}
    for dominio, sinais in itens:
        if dominio in tem:
            continue
        lista.append({"dominio": dominio,
                      "termo_institucional": sinais.get("termo_institucional"),
                      "expediente": sinais.get("expediente"),
                      "incluido_em": hoje.isoformat(),
                      "incluido_por": "triagem automática da entrada de veículos (30/09/2026)"})
        tem.add(dominio)
    doc["atualizado_em"] = hoje.isoformat()
    gravar_em(INSTITUCIONAIS, doc)          # §229
    return doc


def ler_institucionais() -> set:
    if not INSTITUCIONAIS.exists():
        return set()
    d = json.loads(INSTITUCIONAIS.read_text(encoding="utf-8")) or {}
    return {str(x.get("dominio", "")).lower() for x in (d.get("dominios") or [])}


def ler_bloqueados() -> set:
    if not BLOQUEADOS.exists():
        return set()
    d = json.loads(BLOQUEADOS.read_text(encoding="utf-8"))
    return {str(x.get("dominio", "")).lower() for x in (d.get("dominios") or [])}


def registrar_entrada(lista: dict, dominio: str, sinais: dict, hoje) -> dict:
    """Acrescenta o domínio à lista de veículos, com os sinais que o justificaram.

    A entrada é automática, mas **não é silenciosa**: ela grava a data e cada sinal, e a editoria
    recebe a lista semanal para vetar em uma linha. Entrada sem rastro seria a lista crescendo por
    conta própria, que é o que o handover proíbe."""
    lista.setdefault("veiculos", []).append({
        "dominio": dominio,
        "nome": dominio,
        "cobertura": "a confirmar",
        "incluido_em": hoje.isoformat(),
        "incluido_por": "entrada automática por critério (item 3, 29/09/2026)",
        "sinais": {"https": sinais.get("https"),
                   "expediente": sinais.get("expediente"),
                   "nome_ou_cnpj": sinais.get("nome_ou_cnpj"),
                   "materias_na_fila": sinais.get("materias_na_fila")},
    })
    return lista


# =============================================================================================
# B1 … B6 — cada critério é função pura, e o trecho que decidiu volta junto
# =============================================================================================
def b1_cidade_certa(corpo: str, municipio: str, uf: str, dominio: str, locais: dict) -> tuple:
    """(ok, motivo, trecho). Exige o município no corpo E (a UF por perto OU domínio local),
    E o município como SUJEITO da ação."""
    alvo = norm(municipio)
    if not alvo or alvo not in norm(corpo):
        return False, "ente_nao_confirmado", "o nome do município não aparece no corpo"
    local = locais.get(dominio)
    confirmado_por_dominio = bool(local and norm(local.get("municipio")) == alvo
                                  and str(local.get("uf", "")).upper() == str(uf).upper())
    perto = False
    for bloco in re.split(r"\n{1,}|(?<=[.!?])\s+", corpo):
        nb = norm(bloco)
        if alvo in nb and (norm(uf) in re.findall(r"\b[a-z]{2}\b", nb)
                           or norm(UF_POR_EXTENSO.get(str(uf).upper(), "")) in nb):
            perto = True
            break
    if not (perto or confirmado_por_dominio):
        return False, "ente_nao_confirmado", "município sem UF na mesma frase e domínio não é local"
    rx = re.compile(RE_SUJEITO.pattern.replace("{alvo}", re.escape(alvo)), re.I)
    m = rx.search(norm(corpo))
    if not m:
        return False, "ente_nao_confirmado", "município citado, mas sem ação própria atribuída"
    return True, "", corpo[max(0, m.start() - 40):m.end() + 120].replace("\n", " ")


def b2_preparacao(corpo: str, classificar) -> tuple:
    """(ok, motivo, trecho). Só EX_ANTE passa. RESPOSTA e DUVIDA não exibem."""
    decisao, motivo = classificar(corpo)
    if decisao == "EX_ANTE":
        return True, "", motivo
    return False, ("resposta_a_desastre" if decisao == "RESPOSTA" else "natureza_duvidosa"), motivo


def b3_risco_do_ciclo(corpo: str, classificar_objeto) -> tuple:
    """(ok, motivo, trecho). Objeto tem de ser `el_nino`, E os dois marcadores têm de estar no
    corpo: um do ciclo e um de instrumento. Sem os dois, não exibe."""
    objeto = classificar_objeto(corpo)
    if objeto != "el_nino":
        return False, "fora_do_objeto", f"objeto classificado como {objeto}"
    ciclo = RE_MARCADOR_DO_CICLO.search(corpo)
    instrumento = RE_MARCADOR_DE_INSTRUMENTO.search(corpo)
    if not ciclo:
        return False, "sem_marcador_do_ciclo", "nenhum marcador do ciclo 2026/2027 no corpo"
    if not instrumento:
        return False, "sem_marcador_do_ciclo", "nenhum instrumento nomeado no corpo"
    return True, "", f"{ciclo.group(0)} · {instrumento.group(0)}"


def b4_ciclo_atual_e_noticia(html: str, url: str, corpo: str, hoje: datetime.date) -> tuple:
    """(ok, motivo, trecho). Data dos metadados dentro da janela do ciclo, e gênero de notícia."""
    if RE_GENERO_VEDADO.search(url or ""):
        return False, "genero_nao_noticia", "a URL marca opinião, coluna, patrocinado ou sátira"
    cabeca = (html or "")[:4000]
    for palavra in PALAVRAS_DE_GENERO:
        if palavra in norm(cabeca):
            return False, "genero_nao_noticia", f"marcação de gênero na página: {palavra}"
    if re.search(r'"isSponsored"\s*:\s*true', html or "", re.I):
        return False, "genero_nao_noticia", "JSON-LD marca conteúdo patrocinado"
    data, degrau = data_de_publicacao(html, corpo)
    if data is None:
        return False, "sem_data", "sem data de publicação em nenhum degrau da escada"
    if data < DATA_BOLETIM_1:
        return False, "fora_do_ciclo", f"publicada em {data.isoformat()}, antes do Boletim nº 1"
    if data > hoje:
        return False, "fora_do_ciclo", f"data futura: {data.isoformat()}"
    # O degrau vai junto: saber de ONDE veio a data é o que permite desconfiar dela depois.
    return True, "", f"{data.isoformat()} (degrau: {degrau})"


def dominio_de(url) -> str:
    """O host, sem esquema e sem `www.`. Uma regra só, usada pelo B5 e pela entrada automática —
    duas regras de host divergiriam e o domínio entraria na lista com uma grafia e seria buscado
    com outra."""
    u = str(url or "")
    if not u:
        return ""
    return re.sub(r"^https?://(www\.)?([^/]+).*", r"\2", u).lower().split("/")[0]


def b5_veiculo(url: str, veiculos: dict) -> tuple:
    """(ok, motivo, trecho). Só domínio listado entra, e só por HTTPS."""
    if not str(url or "").lower().startswith("https://"):
        return False, "sem_https", "a página não é servida por HTTPS"
    host = dominio_de(url)
    v = veiculos.get(host)
    if not v:
        return False, "veiculo_nao_listado", f"{host} não está em data/veiculos_imprensa.json"
    return True, "", f"{v.get('nome')} · {v.get('cobertura')}"


def b6_nao_duplica(pista: dict, no_banco: bool) -> tuple:
    """(ok, motivo, trecho). Município com registro não recebe pista; recusa POR CRITÉRIO do juiz
    tira a pista; recusa TÉCNICA a mantém, porque o documento só não foi lido ainda."""
    if no_banco:
        return False, "ja_tem_registro", "o município já tem registro no banco"
    juiz = pista.get("juiz") or {}
    if juiz and not juiz.get("promove"):
        motivo = str(juiz.get("motivo") or "")
        if motivo in ("documento_inacessivel", "texto_nao_extraivel"):
            return True, "", "recusa técnica do juiz: o documento ainda não foi lido"
        return False, "recusada_pelo_juiz", f"o juiz recusou por critério: {motivo}"
    return True, "", ""


def chave_de_sindicacao(pista: dict, data_iso: str) -> tuple:
    """(municipio, data, titulo normalizado) — a mesma matéria em dez domínios conta uma vez."""
    titulo = norm(pista.get("titulo"))[:80]
    return (norm(pista.get("municipio") or pista.get("alvo")), str(data_iso)[:10], titulo)


# =============================================================================================
# Canários — um por falha nomeada na seção B do handover. Não são hipóteses: vários vieram das
# promoções falsas do §286 (o "Comitê Gestor do Programa Sandbox", a licença ambiental).
# =============================================================================================
def _pagina(corpo, data="2026-08-15", extra=""):
    cabeca = ""
    if data:
        cabeca = '<meta property="article:published_time" content="' + data + 'T10:00:00Z">'
    return ("<html><head>" + cabeca + extra + "</head><body><article><p>"
            + corpo + "</p></article></body></html>")


_CORPO_BOM = (
    "A Prefeitura de Bonito publicou nesta semana o plano de contingencia municipal para o periodo "
    "chuvoso 2026/2027, elaborado pela Defesa Civil de Bonito, MS. O documento preve "
    "pre-posicionamento de equipes e pontos de apoio, e foi instituido por decreto. "
    "A administracao informou que o plano vale para toda a area urbana e rural do municipio, com "
    "revisao trimestral prevista ao longo da vigencia do periodo chuvoso e da estiagem de 2026.")

CANARIOS = {
    "bom": dict(esperado=True, url="https://horacampinas.com.br/noticia/1",
                municipio="Bonito", uf="MS", corpo=_CORPO_BOM),
    "homonimo_sem_uf": dict(
        esperado="ente_nao_confirmado", url="https://horacampinas.com.br/n/2",
        municipio="Bom Jesus", uf="PI",
        corpo=("A Prefeitura de Bom Jesus publicou o plano de contingencia para o periodo chuvoso "
               "2026/2027 com pre-posicionamento de equipes. O documento foi instituido por "
               "decreto nesta semana pela administracao municipal e pela Defesa Civil local, e "
               "vale para toda a area urbana durante a estiagem de 2026."
               " A reportagem procurou a assessoria, que confirmou os dados apresentados na coletiva e informou que novas reunioes tecnicas serao marcadas ao longo das proximas semanas para acompanhar o andamento dos trabalhos em curso na regiao.")),
    "nome_de_rua": dict(
        esperado="ente_nao_confirmado", url="https://horacampinas.com.br/n/3",
        municipio="Guaruja", uf="SP",
        corpo=("O plano de contingencia para o periodo chuvoso 2026/2027 foi apresentado na rua "
               "Guaruja, no centro de Santos, SP, durante audiencia publica sobre o El Nino e a "
               "estiagem de 2026, com a presenca de tecnicos da Defesa Civil estadual."
               " A reportagem procurou a assessoria, que confirmou os dados apresentados na coletiva e informou que novas reunioes tecnicas serao marcadas ao longo das proximas semanas para acompanhar o andamento dos trabalhos em curso na regiao.")),
    "citado_sem_acao": dict(
        esperado="ente_nao_confirmado", url="https://horacampinas.com.br/n/4",
        municipio="Jacarei", uf="SP",
        corpo=("A Prefeitura de Taubate instituiu o plano de contingencia para o periodo chuvoso "
               "2026/2027, como aconteceu em Jacarei, SP, no ano passado. O documento preve "
               "pre-posicionamento de equipes e pontos de apoio durante a estiagem de 2026."
               " A reportagem procurou a assessoria, que confirmou os dados apresentados na coletiva e informou que novas reunioes tecnicas serao marcadas ao longo das proximas semanas para acompanhar o andamento dos trabalhos em curso na regiao.")),
    "decreto_pos_enchente": dict(
        esperado="resposta_a_desastre", url="https://horacampinas.com.br/n/5",
        municipio="Bonito", uf="MS",
        corpo=("Após a enchente que atingiu bairros na semana passada, a Prefeitura de Bonito, MS, "
               "decretou situação de emergência e montou abrigos. O decreto reconhece os danos e "
               "autoriza a contratação direta para socorro às famílias atingidas, no período "
               "chuvoso 2026/2027."
               " A reportagem procurou a assessoria, que confirmou os dados apresentados na coletiva e informou que novas reunioes tecnicas serao marcadas ao longo das proximas semanas para acompanhar o andamento dos trabalhos em curso na regiao.")),
    "plano_de_dengue": dict(
        esperado="fora_do_objeto", url="https://horacampinas.com.br/n/7",
        municipio="Bonito", uf="MS",
        corpo=("A Prefeitura de Bonito, MS, instituiu o plano de contingência para arboviroses, com "
               "foco em dengue e chikungunya, no periodo chuvoso 2026/2027. A Secretaria de Saude "
               "coordenara as acoes de combate ao mosquito e os mutiroes de limpeza nos bairros."
               " A reportagem procurou a assessoria, que confirmou os dados apresentados na coletiva e informou que novas reunioes tecnicas serao marcadas ao longo das proximas semanas para acompanhar o andamento dos trabalhos em curso na regiao.")),
    "licenca_ambiental": dict(
        esperado="fora_do_objeto", url="https://horacampinas.com.br/n/9",
        municipio="Bonito", uf="MS",
        corpo=("A Prefeitura de Bonito, MS, concedeu licença ambiental de operação a "
               "estabelecimento privado, com condicionante de manter o plano de contingência e o "
               "PGR a disposicao da fiscalizacao durante o periodo chuvoso 2026/2027 e a vigencia "
               "da licenca concedida pela secretaria de meio ambiente."
               " A reportagem procurou a assessoria, que confirmou os dados apresentados na coletiva e informou que novas reunioes tecnicas serao marcadas ao longo das proximas semanas para acompanhar o andamento dos trabalhos em curso na regiao.")),
    "materia_antiga": dict(esperado="fora_do_ciclo", url="https://horacampinas.com.br/n/10",
                           municipio="Bonito", uf="MS", corpo=_CORPO_BOM, data="2023-11-02"),
    "sem_data": dict(esperado="sem_data", url="https://horacampinas.com.br/n/11",
                     municipio="Bonito", uf="MS", corpo=_CORPO_BOM, data=None),
    "coluna_de_opiniao": dict(esperado="genero_nao_noticia",
                              url="https://horacampinas.com.br/opiniao/12",
                              municipio="Bonito", uf="MS", corpo=_CORPO_BOM),
    "patrocinado": dict(esperado="genero_nao_noticia", url="https://horacampinas.com.br/n/13",
                        municipio="Bonito", uf="MS", corpo=_CORPO_BOM,
                        extra='<script type="application/ld+json">{"isSponsored": true}</script>'),
    "satira": dict(esperado="genero_nao_noticia", url="https://horacampinas.com.br/satira/14",
                   municipio="Bonito", uf="MS", corpo=_CORPO_BOM),
    "agregador": dict(esperado="veiculo_nao_listado",
                      url="https://news.google.com/rss/articles/x",
                      municipio="Bonito", uf="MS", corpo=_CORPO_BOM),
    "blog_pessoal": dict(esperado="veiculo_nao_listado", url="https://meublog.wordpress.com/post",
                         municipio="Bonito", uf="MS", corpo=_CORPO_BOM),
    "sem_https": dict(esperado="sem_https", url="http://horacampinas.com.br/n/15",
                      municipio="Bonito", uf="MS", corpo=_CORPO_BOM),
    "so_titulo": dict(esperado="texto_insuficiente", url="https://horacampinas.com.br/n/16",
                      municipio="Bonito", uf="MS", corpo="Prefeitura publica plano"),
    "paywall": dict(esperado="texto_insuficiente", url="https://horacampinas.com.br/n/17",
                    municipio="Bonito", uf="MS",
                    corpo="Assine para continuar lendo. Este conteudo e exclusivo para assinantes."),
    "ja_tem_registro": dict(esperado="ja_tem_registro", url="https://horacampinas.com.br/n/18",
                            municipio="Bonito", uf="MS", corpo=_CORPO_BOM, no_banco=True),
    "recusada_pelo_juiz": dict(esperado="recusada_pelo_juiz", url="https://horacampinas.com.br/n/19",
                               municipio="Bonito", uf="MS", corpo=_CORPO_BOM,
                               juiz={"promove": False, "motivo": "fora_do_objeto"}),
    "recusa_tecnica_do_juiz": dict(esperado=True, url="https://horacampinas.com.br/n/20",
                                   municipio="Bonito", uf="MS", corpo=_CORPO_BOM,
                                   juiz={"promove": False, "motivo": "documento_inacessivel"}),
}


def verificar(pagina_html: str, pista: dict, contexto: dict) -> dict:
    """O veredito de exibição de UMA pista.

    Todos os critérios são obrigatórios e a verificação para no primeiro que falha — não há nota
    média, como a seção A3 exige. A ordem é a barata primeiro: veículo e tamanho do corpo não
    custam nada, e derrubam a maioria antes de rodar classificador."""
    from classificador_natureza import classificar as classificar_natureza
    from classificar_pista_civil import classificar_objeto

    # A data vem do contexto (o autoteste passa uma fixa) ou da data EDITORIAL — nunca de
    # `date.today()`, que no runner é UTC: uma matéria publicada às 22h de Brasília cairia no dia
    # seguinte e o teste do ciclo (B4) julgaria pela data errada. O portão pegou isto na CI.
    if contexto.get("hoje"):
        hoje = contexto["hoje"]
    else:
        from coletores_base import hoje_editorial
        hoje = hoje_editorial()
    veredito = {"versao": VERSAO, "exibivel": False, "motivo": None, "criterios": {},
                "lido_em": hoje.isoformat(), "url": pista.get("url")}

    ok, motivo, trecho = b5_veiculo(pista.get("url"), contexto.get("veiculos") or {})
    veredito["criterios"]["B5_veiculo"] = {"ok": ok, "trecho": trecho}
    if not ok:
        veredito["motivo"] = motivo
        return veredito

    corpo = corpo_da_pagina(pagina_html)
    veredito["tamanho_do_corpo"] = len(corpo)
    veredito["criterios"]["A1_corpo"] = {"ok": len(corpo) >= CORPO_MINIMO,
                                         "trecho": str(len(corpo)) + " caracteres"}
    if len(corpo) < CORPO_MINIMO:
        veredito["motivo"] = "texto_insuficiente"
        return veredito
    from coletores_base import sha256
    veredito["hash_do_corpo"] = sha256(corpo.encode("utf-8"))

    ok, motivo, trecho = b4_ciclo_atual_e_noticia(pagina_html, pista.get("url"), corpo, hoje)
    veredito["criterios"]["B4_ciclo_e_genero"] = {"ok": ok, "trecho": trecho}
    if not ok:
        veredito["motivo"] = motivo
        return veredito
    veredito["data_da_materia"] = trecho

    dominio = re.sub(r"^https?://(www\.)?([^/]+).*", r"\2", str(pista.get("url") or "")).lower()
    ok, motivo, trecho = b1_cidade_certa(corpo, pista.get("municipio"), pista.get("uf"),
                                         dominio, contexto.get("locais") or {})
    veredito["criterios"]["B1_cidade"] = {"ok": ok, "trecho": trecho}
    if not ok:
        veredito["motivo"] = motivo
        return veredito

    ok, motivo, trecho = b2_preparacao(corpo, classificar_natureza)
    veredito["criterios"]["B2_preparacao"] = {"ok": ok, "trecho": trecho}
    if not ok:
        veredito["motivo"] = motivo
        return veredito

    ok, motivo, trecho = b3_risco_do_ciclo(corpo, classificar_objeto)
    veredito["criterios"]["B3_ciclo"] = {"ok": ok, "trecho": trecho}
    if not ok:
        veredito["motivo"] = motivo
        return veredito

    ok, motivo, trecho = b6_nao_duplica(pista, contexto.get("no_banco", False))
    veredito["criterios"]["B6_nao_duplica"] = {"ok": ok, "trecho": trecho}
    if not ok:
        veredito["motivo"] = motivo
        return veredito

    veredito["exibivel"] = True
    return veredito


def autoteste() -> int:
    """Offline: sem rede, sem escrita. Os canários da seção E, um por falha nomeada."""
    veiculos = {"horacampinas.com.br": {"nome": "Hora Campinas", "cobertura": "Campinas/SP"}}
    locais = {"horacampinas.com.br": {"municipio": "Campinas", "uf": "SP"}}
    hoje = datetime.date(2026, 9, 29)
    casos = []

    for nome, c in CANARIOS.items():
        html = _pagina(c["corpo"], data=c.get("data", "2026-08-15"), extra=c.get("extra", ""))
        pista = {"url": c["url"], "municipio": c["municipio"], "uf": c["uf"],
                 "titulo": "t", "juiz": c.get("juiz")}
        v = verificar(html, pista, {"veiculos": veiculos, "locais": locais, "hoje": hoje,
                                    "no_banco": c.get("no_banco", False)})
        esperado = c["esperado"]
        ok = (v["exibivel"] is True) if esperado is True else (
            v["exibivel"] is False and v["motivo"] == esperado)
        casos.append((f"canário {nome}: esperado {esperado}, veio "
                      + ("exibivel" if v["exibivel"] else str(v["motivo"])), ok))

    casos.append(("todo motivo de recusa está no vocabulário declarado",
                  all(v in MOTIVOS for v in
                      [c["esperado"] for c in CANARIOS.values() if c["esperado"] is not True])))
    casos.append(("o veredito carrega a versão do verificador",
                  verificar(_pagina(_CORPO_BOM), {"url": "https://x/1"},
                            {"veiculos": {}})["versao"] == VERSAO))
    v_bom = verificar(_pagina(_CORPO_BOM), {"url": "https://horacampinas.com.br/n/1",
                                            "municipio": "Bonito", "uf": "MS"},
                      {"veiculos": veiculos, "locais": locais, "hoje": hoje})
    casos.append(("a pista exibível guarda o hash do corpo lido", bool(v_bom.get("hash_do_corpo"))))
    casos.append(("e a data da matéria, com o degrau de onde ela veio",
                  str(v_bom.get("data_da_materia") or "").startswith("2026-08-15 (degrau: og_published_time)")))
    casos.append(("e o trecho que satisfez cada critério",
                  all(c.get("trecho") is not None for c in v_bom["criterios"].values())))

    # Sindicação: a mesma matéria em três domínios tem uma chave só.
    ch = [chave_de_sindicacao({"municipio": "Bonito", "titulo": "Plano publicado"}, "2026-08-15")
          for _ in range(3)]
    casos.append(("sindicação: a mesma matéria em três domínios dá uma chave só", len(set(ch)) == 1))
    casos.append(("títulos diferentes não se fundem",
                  chave_de_sindicacao({"municipio": "Bonito", "titulo": "Outro"}, "2026-08-15")
                  != ch[0]))

    # O corpo é lido sem menu, rodapé e "leia também".
    corpo = corpo_da_pagina("<html><body><nav>menu</nav><article><p>Texto do conteúdo aqui.</p>"
                            "</article><footer>rodapé</footer></body></html>")
    casos.append(("o corpo sai sem menu e sem rodapé",
                  "Texto do conteúdo" in corpo and "menu" not in corpo and "rodapé" not in corpo))
    # Item 2: a escada de extração, degrau a degrau, com o nome de cada um registrado.
    casos.append(("degrau 1: JSON-LD datePublished",
                  data_de_publicacao('<html>{"datePublished": "2026-07-01T00:00:00"}</html>')
                  == (datetime.date(2026, 7, 1), "json_ld")))
    casos.append(("degrau 2: article:published_time",
                  data_de_publicacao('<meta property="article:published_time" content="2026-07-02">')
                  == (datetime.date(2026, 7, 2), "og_published_time")))
    casos.append(("degrau 3: <time datetime>",
                  data_de_publicacao('<time datetime="2026-07-03T08:00:00">')
                  == (datetime.date(2026, 7, 3), "time_datetime")))
    casos.append(("degrau 4: data visível por extenso na cabeça da matéria",
                  data_de_publicacao("<html></html>", "Publicado em 4 de julho de 2026 por Fulano")
                  == (datetime.date(2026, 7, 4), "visivel_extenso")))
    casos.append(("degrau 4: data visível numérica",
                  data_de_publicacao("<html></html>", "05/07/2026 · Redação")
                  == (datetime.date(2026, 7, 5), "visivel_numerica")))
    casos.append(("a escada prefere o degrau mais estruturado",
                  data_de_publicacao('<html>{"datePublished": "2026-07-01"}<time datetime="2020-01-01">',
                                     "10 de março de 2019")[1] == "json_ld"))
    casos.append(("data longe da cabeça da matéria NÃO é tomada por data de publicação",
                  data_de_publicacao("<html></html>", "x" * 700 + " 9 de agosto de 2026")
                  == (None, None)))
    casos.append(("mês inventado não vira data",
                  data_de_publicacao("<html></html>", "4 de julhembro de 2026") == (None, None)))
    casos.append(("dia impossível não vira data",
                  data_de_publicacao("<html></html>", "31/02/2026") == (None, None)))
    casos.append(("página sem data nenhuma devolve (None, None), e sem data não exibe",
                  data_de_publicacao("<html></html>") == (None, None)))

    # --- item 1: o agregador resolve ou declara, nunca chuta -------------------------------------
    import base64 as _b64
    legado = ("https://news.google.com/articles/"
              + _b64.urlsafe_b64encode(b"\x08\x13\x22https://horacampinas.com.br/materia-x-2026"
                                       ).decode().rstrip("="))
    casos.append(("link antigo do Google News: a URL embutida sai sem rede",
                  resolver_redirecionamento(legado)
                  == ("https://horacampinas.com.br/materia-x-2026", "url_embutida_no_link")))
    casos.append(("link opaco sem rede não vira chute: declara não resolvido",
                  resolver_redirecionamento("https://news.google.com/articles/CBMiOPAQUE")
                  == (None, "redirecionamento_nao_resolvido")))
    casos.append(("redirecionamento HTTP resolve quando a fonte o serve",
                  resolver_redirecionamento("https://news.google.com/articles/CBMiX",
                                            abrir=lambda u: "https://horacampinas.com.br/a")
                  == ("https://horacampinas.com.br/a", "redirecionamento_http")))
    casos.append(("agregador que redireciona para agregador não conta como resolvido",
                  resolver_redirecionamento("https://news.google.com/articles/CBMiX",
                                            abrir=lambda u: "https://flipboard.com/x")
                  == (None, "redirecionamento_nao_resolvido")))
    # 09/10/2026 (lote 2.6, A1-08): degrau 3, busca no veículo pelo título.
    falso = lambda q: [{"url": "https://g1.globo.com/x"}, {"url": "https://www.palmas.to.gov.br/"},
                       {"url": "https://www.palmas.to.gov.br/noticia/x"}]  # noqa: E731
    casos.append(("link opaco resolve pela busca no veículo, só no host do veículo e com caminho",
                  resolver_redirecionamento("https://news.google.com/articles/CBMiOPAQUE",
                                            veiculo="https://www.palmas.to.gov.br",
                                            titulo="Palmas aprova plano - Prefeitura de Palmas",
                                            buscar_web=falso)
                  == ("https://www.palmas.to.gov.br/noticia/x", "busca_no_veiculo")))
    casos.append(("busca no veículo sem resultado no host declara não resolvido",
                  resolver_redirecionamento("https://news.google.com/articles/CBMiOPAQUE",
                                            veiculo="https://outro.com.br", titulo="x y z",
                                            buscar_web=falso)
                  == (None, "redirecionamento_nao_resolvido")))
    casos.append(("URL de veículo passa intacta",
                  resolver_redirecionamento("https://horacampinas.com.br/a")[1]
                  == "nao_era_agregador"))
    casos.append(("o domínio se lê por uma regra só, com ou sem www",
                  dominio_de("https://www.horacampinas.com.br/a/b") == "horacampinas.com.br"))

    # --- item 3: a lista cresce por critério, e todo critério é obrigatório ----------------------
    expediente = {"https://x.com.br/expediente":
                  _pagina("Hora Campinas é um jornal. CNPJ 12.345.678/0001-90.")}
    bloq = {"news.google.com", "blogspot.com"}
    s_ok = sinais_de_veiculo("horacampinas.com.br",
                            {"https://horacampinas.com.br/expediente":
                             _pagina("O Hora Campinas circula desde 2014.")}, 3)
    casos.append(("sinais: nome do veículo localizável no expediente",
                  s_ok["nome_ou_cnpj"] and s_ok["https"] and s_ok["materias_suficientes"]))
    casos.append(("sinais: CNPJ serve no lugar do nome",
                  sinais_de_veiculo("outro.com.br", expediente, 2)["nome_ou_cnpj"] is True))
    casos.append(("página que não é de expediente não conta como expediente",
                  sinais_de_veiculo("horacampinas.com.br",
                                    {"https://horacampinas.com.br/noticia/x":
                                     _pagina("Hora Campinas")}, 5)["expediente"] is None))
    # 30/09/2026: `s_ok` tem os quatro sinais do §299 e NÃO tem os dois novos. Ele passou a ser o
    # caso do sítio que cumpre a forma e não se identifica como imprensa — que é exatamente o que a
    # decisão da editoria manda recusar.
    casos.append(("os quatro sinais do §299 já não bastam sozinhos",
                  pode_entrar("horacampinas.com.br", s_ok, bloq)[1]
                  == "expediente_sem_identidade_jornalistica"))
    casos.append(("agregador NÃO entra, mesmo com HTTPS e expediente em ordem",
                  pode_entrar("news.google.com", s_ok, bloq) == (False, "dominio_bloqueado")))
    casos.append(("subdomínio de fazenda de conteúdo também não entra",
                  pode_entrar("jornal.blogspot.com", s_ok, bloq) == (False, "dominio_bloqueado")))
    casos.append(("sem HTTPS não entra",
                  pode_entrar("x.com.br", {**s_ok, "https": False}, bloq)[1] == "sem_https"))
    casos.append(("sem página de expediente não entra",
                  pode_entrar("x.com.br", {**s_ok, "expediente": None}, bloq)[1]
                  == "sem_pagina_de_expediente"))
    casos.append(("expediente sem nome nem CNPJ não entra",
                  pode_entrar("x.com.br", {**s_ok, "nome_ou_cnpj": False}, bloq)[1]
                  == "expediente_sem_nome_nem_cnpj"))
    casos.append((f"menos de {MATERIAS_MINIMAS} matérias na fila não entra",
                  pode_entrar("x.com.br", {**s_ok, "materias_suficientes": False}, bloq)[1]
                  == f"menos_de_{MATERIAS_MINIMAS}_materias_na_fila"))
    casos.append(("a entrada grava a data e cada sinal que a justificou",
                  (lambda e: e["incluido_em"] == "2026-09-29" and e["sinais"]["https"] is True
                   and e["sinais"]["materias_na_fila"] == 3)(
                      registrar_entrada({}, "horacampinas.com.br", s_ok, hoje)["veiculos"][0])))
    fila_teste = [{"url": "https://a.com.br/1", "titulo": "Plano de contingência"},
                  {"url": "https://a.com.br/2", "titulo": "Outra matéria"},
                  {"url": "https://b.com.br/1", "titulo": "Só uma"},
                  {"url": "https://c.com.br/1", "titulo": "Igual"},
                  {"url": "https://c.com.br/2", "titulo": "Igual"},
                  {"url": "https://news.google.com/articles/X", "titulo": "Um"},
                  {"url": "https://news.google.com/articles/Y", "titulo": "Dois"}]
    cand = dominios_candidatos(fila_teste, {"listado.com.br": {}}, bloq)
    casos.append(("candidatos: domínio com 2 matérias distintas entra na avaliação",
                  cand.get("a.com.br") == 2))
    casos.append(("candidatos: uma matéria só não basta", "b.com.br" not in cand))
    casos.append(("candidatos: a mesma matéria duas vezes conta uma", "c.com.br" not in cand))
    casos.append(("candidatos: agregador nunca é candidato", "news.google.com" not in cand))
    casos.append(("candidatos: domínio já listado não é reavaliado",
                  "listado.com.br" not in cand))
    casos.append(("a lista de bloqueados existe e traz os agregadores",
                  {"news.google.com", "blogspot.com"} <= ler_bloqueados()))
    casos.append(("nenhum domínio da lista de veículos está bloqueado",
                  not (set(carregar_listas()[0]) & ler_bloqueados())))

    # --- 30/09/2026: a lista aceita só imprensa (caso CEIVAP) ------------------------------------
    exp_jornal = _pagina("O Hora Campinas é um portal de notícias. Editor-chefe: alguém. "
                         "CNPJ 12.345.678/0001-90.")
    vitrine = _pagina("Chuva alaga bairro 12/08/2026 Prefeitura decreta 13/08/2026 "
                      "Defesa Civil alerta 14/08/2026")
    pags_jornal = {"https://horacampinas.com.br/expediente": exp_jornal,
                   "https://horacampinas.com.br/": vitrine}
    s_jornal = sinais_de_veiculo("horacampinas.com.br", pags_jornal, 3)
    casos.append(("veículo com expediente jornalístico e vitrine datada entra",
                  pode_entrar("horacampinas.com.br", s_jornal, bloq) == (True, "")))
    casos.append(("o termo jornalístico é o achado literal, não inferência",
                  s_jornal["identidade_jornalistica"].lower() == "portal de notícias"))

    exp_ceivap = _pagina("O CEIVAP é o Comitê de Integração da Bacia Hidrográfica do Rio Paraíba "
                         "do Sul, órgão colegiado do sistema de recursos hídricos.")
    pags_ceivap = {"https://ceivap.org.br/quem-somos": exp_ceivap,
                   "https://ceivap.org.br/": _pagina("PMSB Barra do Piraí 12/08/2026 "
                                                     "PMSB Miguel Pereira 13/08/2026 "
                                                     "Ata da reunião 14/08/2026")}
    s_ceivap = sinais_de_veiculo("ceivap.org.br", pags_ceivap, 9)
    casos.append(("CANÁRIO: sítio institucional com expediente NÃO é veículo",
                  pode_entrar("ceivap.org.br", s_ceivap, bloq)
                  == (False, "sitio_institucional_nao_e_veiculo")))
    casos.append(("o termo institucional achado fica registrado, para a decisão ser auditável",
                  "comit" in s_ceivap["termo_institucional"].lower()))
    casos.append(("sítio institucional NÃO vai para a lista de bloqueio — vai ao juiz",
                  "ceivap.org.br" not in ler_bloqueados()))
    casos.append(("institucional vence palavra jornalística solta: comitê que diz 'redação' segue "
                  "não sendo veículo",
                  pode_entrar("ceivap.org.br", {**s_ceivap,
                                                "identidade_jornalistica": "redação"}, bloq)[1]
                  == "sitio_institucional_nao_e_veiculo"))
    casos.append(("expediente sem identidade jornalística não entra",
                  pode_entrar("x.com.br", {**s_jornal, "identidade_jornalistica": ""}, bloq)[1]
                  == "expediente_sem_identidade_jornalistica"))
    casos.append(("sem vitrine datada E sem cargo de redação não entra",
                  pode_entrar("x.com.br", {**s_jornal, "secao_de_noticias": False,
                                           "cargo_de_redacao": ""}, bloq)[1]
                  == "sem_vitrine_datada_nem_cargo_de_redacao"))
    casos.append(("expediente com editor-chefe basta, mesmo com capa renderizada por JavaScript",
                  pode_entrar("x.com.br", {**s_jornal, "secao_de_noticias": False,
                                           "cargo_de_redacao": "EDITOR – CHEFE"}, bloq)[0] is True))
    casos.append(("o cargo se lê no expediente, não na capa",
                  tem_cargo_de_redacao({"https://x.com.br/":
                                        _pagina("Editor-chefe comenta")}) == ""))
    casos.append(("comitê sem cargo de redação no expediente não tem o sinal",
                  tem_cargo_de_redacao({"https://ceivap.org.br/quem-somos":
                                        _pagina("Somos o Comitê de Integração da Bacia.")}) == ""))
    casos.append((f"uma data solta não faz seção de notícias (o mínimo é "
                  f"{MATERIAS_DATADAS_MINIMAS})",
                  tem_secao_de_noticias({"https://x.com.br/":
                                         _pagina("atualizado em 12/08/2026")}) is False))
    casos.append(("três matérias datadas fazem seção de notícias",
                  tem_secao_de_noticias({"https://x.com.br/": vitrine}) is True))
    casos.append(("<time datetime> conta como marca de tempo",
                  tem_secao_de_noticias({"https://x.com.br/":
                                         '<time datetime="2026-08-15">a</time>'
                                         '<time datetime="2026-08-16">b</time>'
                                         '<time datetime="2026-08-17">c</time>'}) is True))
    casos.append(("o 'há 2 horas' das capas conta como marca de tempo",
                  tem_secao_de_noticias({"https://x.com.br/":
                                         _pagina("há 2 horas · há 3 horas · há 1 dia")}) is True))
    casos.append(("feed com três itens conta como seção de notícias",
                  tem_secao_de_noticias({"https://x.com.br/feed":
                                         "<pubDate>a</pubDate><pubDate>b</pubDate>"
                                         "<pubDate>c</pubDate>"}) is True))
    casos.append(("feed com um item só não conta",
                  tem_secao_de_noticias({"https://x.com.br/feed":
                                         "<pubDate>a</pubDate>"}) is False))
    casos.append(("'pauta' não é identidade jornalística — sinal fraco, fora da lista da editoria",
                  tem_identidade_jornalistica(
                      {"https://x.com.br/expediente": _pagina("Sugira uma pauta.")}) == ""))
    casos.append(("o termo institucional se lê SÓ na autodescrição do expediente: manchete com "
                  "'Secretaria de' não transforma jornal em instituição",
                  eh_sitio_institucional(
                      {"https://x.com.br/": _pagina("Secretaria de Saúde anuncia mutirão")}) == ""))
    casos.append(("e se lê quando o próprio expediente diz o que é",
                  "comit" in eh_sitio_institucional(
                      {"https://x.com.br/quem-somos":
                       _pagina("Somos o Comitê de Integração da Bacia do Paraíba do Sul.")}).lower()))
    casos.append(("a identidade jornalística se lê no expediente, não na vitrine",
                  tem_identidade_jornalistica({"https://x.com.br/": exp_jornal}) == ""))
    # 30/09/2026 (decisão da editoria): falso negativo se trata como falso negativo, SEM exceção
    # nomeada. Este canário é a trava: no dia em que alguém quiser salvar um veículo escrevendo o
    # domínio dele dentro da decisão, o autoteste reprova. Exceção por domínio faria a regra parar de
    # ser regra — e a regra é o que permite a entrada ser automática.
    import inspect
    fonte_da_decisao = "".join(inspect.getsource(f)
                               for f in (pode_entrar, sinais_de_veiculo, eh_dominio_de_ente,
                                         tem_identidade_jornalistica, tem_cargo_de_redacao,
                                         tem_secao_de_noticias, eh_sitio_institucional))
    casos.append(("o caminho de decisão não tem exceção por domínio: nenhum `.com.br`, `.org.br` "
                  "ou `.net` literal",
                  not re.search(r"[\"'][\w.-]+\.(?:com|org|net|br)\b", fonte_da_decisao)))
    casos.append(("o falso negativo conhecido está registrado no próprio veículo, com data e motivo",
                  (lambda vs: any(v.get("falso_negativo_conhecido", {}).get("desde")
                                  and v["falso_negativo_conhecido"].get("motivo")
                                  for v in vs.values()))(carregar_listas()[0])))

    casos.append(("nenhum domínio institucional continua na lista de veículos",
                  not (set(carregar_listas()[0]) & ler_institucionais())))

    casos.append(("domínio de governo não entra na lista de veículos",
                  pode_entrar("curitiba.pr.gov.br", s_jornal, bloq)[1]
                  == "dominio_de_governo_nao_e_veiculo"))
    casos.append(("nem câmara, nem tribunal, nem ministério público",
                  all(pode_entrar("x." + g, s_jornal, bloq)[1] == "dominio_de_governo_nao_e_veiculo"
                      for g in SUFIXOS_DE_GOVERNO)))
    casos.append(("o domínio NU de governo também não entra — a fresta que deixou `gov.br` passar",
                  pode_entrar("gov.br", s_jornal, bloq)[1] == "dominio_de_governo_nao_e_veiculo"))
    casos.append(("prefeitura fora do .gov.br não entra",
                  pode_entrar("prefeitura.poa.br", s_jornal, bloq)[1]
                  == "dominio_de_ente_publico_nao_e_veiculo"))
    casos.append(("ente público não ocupa vaga da sonda",
                  not (set(dominios_candidatos(
                      [{"url": "https://prefeitura.poa.br/1", "titulo": "a"},
                       {"url": "https://prefeitura.poa.br/2", "titulo": "b"},
                       {"url": "https://gov.br/1", "titulo": "c"},
                       {"url": "https://gov.br/2", "titulo": "d"}], {}, bloq)))))
    casos.append(("nenhum domínio de ente público está na lista de veículos",
                  not [d for d in carregar_listas()[0] if eh_dominio_de_ente(d)]))
    casos.append(("veículo comum continua entrando",
                  pode_entrar("horacampinas.com.br",
                              {**s_ok, "identidade_jornalistica": "jornal",
                               "secao_de_noticias": True}, bloq)[0] is True))
    import urllib.error as _ue
    def _http(c):
        return _ue.HTTPError("https://x.com.br/expediente", c, "", None, None)
    casos.append(("404 na sonda de expediente NÃO é recusa de acesso",
                  eh_recusa_de_acesso(_http(404)) is False))
    casos.append(("500 na sonda também não é recusa de acesso",
                  eh_recusa_de_acesso(_http(500)) is False))
    for c in CODIGOS_DE_RECUSA:
        casos.append((f"{c} é recusa de acesso e o disjuntor deve contá-la",
                      eh_recusa_de_acesso(_http(c)) is True))
    casos.append(("erro de rede sem código não conta como recusa da fonte",
                  eh_recusa_de_acesso(OSError("timed out")) is False))
    casos.append((f"o teto de resolução por noite é sondagem, não varredura: "
                  f"{RESOLUCOES_POR_NOITE}", RESOLUCOES_POR_NOITE <= 40))

    # --- item 4: o limiar tem n e intervalo, não só proporção -----------------------------------
    casos.append(("Wilson: n zero não inventa intervalo", wilson(0, 0) == (0.0, 0.0)))
    casos.append(("Wilson: 19 de 20 dá limite inferior perto de 76%",
                  0.74 < wilson(19, 20)[0] < 0.78))
    casos.append(("Wilson: 95 de 100 dá limite inferior perto de 89%",
                  0.88 < wilson(95, 100)[0] < 0.90))
    casos.append(("Wilson: o intervalo é crescente em n para a mesma proporção",
                  wilson(95, 100)[0] > wilson(19, 20)[0]))
    casos.append(("Wilson: certeza total ainda tem limite inferior abaixo de 1",
                  wilson(20, 20)[0] < 1.0 and wilson(20, 20)[1] == 1.0))
    casos.append((f"19 de 20 = 95% NÃO passa, porque o limite inferior fica abaixo de "
                  f"{WILSON_MINIMO * 100:.0f}%",
                  veredito_da_amostra(19, 20)["passa"] is False))
    casos.append(("20 de 20 passa", veredito_da_amostra(20, 20)["passa"] is True))
    casos.append(("38 de 40 = 95% passa, porque o n sustenta o intervalo",
                  veredito_da_amostra(38, 40)["passa"] is True))
    casos.append((f"amostra menor que {EXIBIVEIS_PARA_AMOSTRA} nunca passa, nem perfeita",
                  veredito_da_amostra(19, 19)["passa"] is False))
    casos.append(("precisão abaixo do mínimo não passa nem com n grande",
                  veredito_da_amostra(180, 200)["passa"] is False))
    casos.append(("o veredito escreve o n e o intervalo por extenso",
                  all(t in veredito_da_amostra(19, 20)["frase"]
                      for t in ("de 20", "Wilson", "NÃO passa"))))
    casos.append(("a amostra abre com 20 exibíveis e 10 recusadas",
                  (EXIBIVEIS_PARA_AMOSTRA, RECUSADAS_NA_AMOSTRA) == (20, 10)))

    ruins = [n for n, ok in casos if not ok]
    for n, ok in casos:
        print(f"  {'OK  ' if ok else 'FALHA'} {n}")
    if ruins:
        print(f"X AUTOTESTE: {len(ruins)} caso(s) reprovado(s).")
        return 1
    print(f"OK AUTOTESTE — {len(casos)} casos ({len(CANARIOS)} canários), sem rede e sem escrita.")
    return 0


# =============================================================================================
# Modo sombra (seção D) — roda sobre as pistas, grava o que EXIBIRIA, e não toca o cartão
# =============================================================================================
def carregar_listas():
    def ler(p, chave, campo):
        if not p.exists():
            return {}
        d = json.loads(p.read_text(encoding="utf-8"))
        return {str(x.get(campo, "")).lower(): x for x in (d.get(chave) or [])}
    return ler(VEICULOS, "veiculos", "dominio"), ler(LOCAIS, "dominios", "dominio")


def municipios_no_banco() -> set:
    p = RAIZ / "data" / "municipios.json"
    if not p.exists():
        return set()
    d = json.loads(p.read_text(encoding="utf-8"))
    L = d if isinstance(d, list) else (d.get("municipios") or [])
    return {(norm(m.get("nome")), str(m.get("uf") or "").upper()) for m in L
            if str(m.get("categoria") or "").startswith(("plano", "decreto"))}


def alvo_para_municipio(pista: dict) -> tuple:
    """A pista de imprensa guarda o território no `alvo` ('…/Camaçari/BA'), não em campo próprio."""
    partes = [x.strip() for x in str(pista.get("alvo") or "").split("/") if x.strip()]
    if len(partes) >= 2 and len(partes[-1]) == 2 and partes[-1].isalpha():
        return partes[-2], partes[-1].upper()
    return pista.get("municipio"), pista.get("uf")


def ordem_da_fila(pistas: list, veiculos: dict) -> list:
    """Prioridade da seção G2: pista mais recente primeiro; depois as de veículo já listado; depois
    as demais. Ordem estável, para que a noite seguinte continue de onde esta parou."""
    def chave(p):
        host = re.sub(r"^https?://(www\.)?([^/]+).*", r"\2", str(p.get("url") or "")).lower()
        return (0 if host in veiculos else 1, str(p.get("data_publicacao") or "")[::-1])
    return sorted(pistas, key=chave)


# Quatro caminhos, não seis, e timeout curto: a sonda é descoberta, não leitura de prova. Com
# seis caminhos a 30 s e 15 domínios, o pior caso da sonda passava de 40 minutos dentro de uma
# rotina noturna que tem outras coisas para fazer — e o ganho do quinto caminho é marginal.
CAMINHOS_DE_EXPEDIENTE = ("/expediente", "/quem-somos", "/sobre", "/contato")
# A sonda abre também a home e a seção de notícias: o sinal "matérias datadas" não mora no
# expediente, e sem ele o sítio institucional voltaria a entrar.
CAMINHOS_DE_VITRINE = ("/", "/noticias", "/ultimas-noticias")
# O feed entra na sonda porque capa de jornal hoje é renderizada por JavaScript: `plantaoguaruja` e
# `abcdoabc` dizem "site de notícias" no expediente e não mostravam marca de tempo nenhuma no HTML
# da home. O feed mostra — e é a mesma fonte que o monitor de imprensa já lê.
CAMINHOS_DE_FEED = ("/feed", "/rss", "/feed/rss")
RE_ITEM_DE_FEED = re.compile(r"<(?:pubDate|updated|published)>", re.I)
TIMEOUT_DA_SONDA = 12


def dominios_candidatos(fila: list, veiculos: dict, bloqueados: set) -> dict:
    """{dominio: matérias distintas na fila} dos domínios que ainda não estão na lista.

    Distintas pelo título normalizado: dez cópias da mesma matéria não são dois veículos de
    verdade, e sindicação é justamente o que enche a fila."""
    import collections
    titulos = collections.defaultdict(set)
    for p in fila:
        d = dominio_de(p.get("veiculo_dominio") or p.get("url"))
        if not d or d in veiculos:
            continue
        if any(b == d or d.endswith("." + b) for b in bloqueados):
            continue
        if eh_dominio_de_ente(d):
            continue        # sítio oficial é outro canal; nem ocupa vaga da sonda
        titulos[d].add(norm(p.get("titulo") or p.get("url") or "")[:120])
    return {d: len(t) for d, t in titulos.items() if len(t) >= MATERIAS_MINIMAS}


SUFIXOS_DE_GOVERNO = ("gov.br", "leg.br", "jus.br", "mp.br", "def.br")
# Ente público fora do `.gov.br` existe e é comum: `prefeitura.poa.br` entrou na primeira medição
# por não ter sufixo de governo. A palavra no domínio resolve o caso sem inferência semântica.
PALAVRAS_DE_ENTE = ("prefeitura", "municipio", "município", "camaramunicipal", "camara-municipal",
                    "governo", "defesacivil", "gabinete")


def eh_dominio_de_ente(dominio) -> str:
    """O motivo, quando o domínio é de ente público; string vazia quando não é.

    Duas leituras, nesta ordem: sufixo oficial (inclusive o domínio **nu** — `gov.br` não termina
    em `.gov.br`, e foi exatamente por essa fresta que ele entrou na lista de veículos na primeira
    medição) e palavra de ente no nome."""
    d = str(dominio or "").lower()
    if not d:
        return ""
    if any(d == g or d.endswith("." + g) for g in SUFIXOS_DE_GOVERNO):
        return "dominio_de_governo_nao_e_veiculo"
    if any(w in d for w in PALAVRAS_DE_ENTE):
        return "dominio_de_ente_publico_nao_e_veiculo"
    return ""
CODIGOS_DE_RECUSA = (401, 403, 429, 451)


def eh_recusa_de_acesso(erro) -> bool:
    """True só quando a fonte barrou o Monitor de verdade. Ausência de página não é barreira.

    A distinção importa duas vezes: o disjuntor do orçamento só deve reagir a barreira real, e a
    regra do projeto é que bloqueio de acesso se respeita sempre — então ele tem de ser reconhecido,
    não confundido com 404."""
    codigo = getattr(erro, "code", None)
    if codigo in CODIGOS_DE_RECUSA:
        return True
    return "muro" in type(erro).__name__.lower() or "robo" in type(erro).__name__.lower()


DOMINIOS_AVALIADOS_POR_NOITE = 15
# Teto de links de agregador tentados por rede numa noite. Vinte, não cento e cinquenta: na
# primeira medição real, **150 tentativas e 150 falhas** — o formato em uso do Google News não
# redireciona e não carrega a URL do veículo. O teto baixo mantém a SONDA (se o formato voltar a
# redirecionar, vinte tentativas por noite descobrem isso) e para de gastar requisição para chegar
# ao mesmo "não resolve". Quem passa do teto fica na fila, contado no funil, sem veredito falso.
RESOLUCOES_POR_NOITE = 20


def crescer_lista_de_veiculos(fila: list, veiculos: dict, orcamento=None, hoje=None,
                              escrever: bool = True, abrir=None) -> dict:
    """Item 3: a lista de veículos cresce por critério medido, não por leitura humana de cada
    domínio — e nunca em silêncio.

    Cada entrada grava a data e os quatro sinais que a justificaram, de modo que a editoria vete
    em uma linha o que o critério deixou passar. Domínio bloqueado não chega aqui.

    **O orçamento é próprio, e isso não é detalhe.** Sondar `/expediente` em domínio desconhecido
    dá 404 na maior parte das vezes; com o orçamento da verificação, essas recusas esperadas
    disparavam o disjuntor de 25% e a noite terminava com 0 páginas lidas — foi o que aconteceu na
    primeira rodada, 5.425 pistas na fila e nenhuma lida. Sonda de descoberta e leitura de matéria
    são consumos diferentes e contam separado."""
    from coletores_base import OrcamentoDeRequisicoes, buscar, gravar_em, hoje_editorial
    hoje = hoje or hoje_editorial()
    del orcamento                       # o orçamento da verificação não financia a sonda
    orcamento = OrcamentoDeRequisicoes()
    abrir = abrir or (lambda u: buscar(u, timeout=TIMEOUT_DA_SONDA,
                                       origem="verificar_pista_imprensa").decode("utf-8", "replace"))
    bloqueados = ler_bloqueados()
    candidatos = dominios_candidatos(fila, veiculos, bloqueados)
    entradas, recusas, institucionais = [], {}, []

    for dominio, materias in sorted(candidatos.items(), key=lambda kv: -kv[1])[
            :DOMINIOS_AVALIADOS_POR_NOITE]:
        if orcamento.encerrar_a_rodada():
            recusas["nao_avaliado_por_orcamento"] = recusas.get(
                "nao_avaliado_por_orcamento", 0) + 1
            continue
        paginas = {}
        for caminho in CAMINHOS_DE_EXPEDIENTE:
            url = f"https://{dominio}{caminho}"
            pode, _ = orcamento.pode_ler(url)
            if not pode:
                break
            try:
                paginas[url] = abrir(url)
                orcamento.registrar(url, recusada=False)
            except Exception as e:  # noqa: BLE001
                # **404 não é recusa.** O disjuntor do orçamento existe para parar de insistir com
                # host que está barrando o Monitor (403, 429, 451, captcha, login). Uma página de
                # expediente que simplesmente não existe naquele caminho é ausência, e contá-la como
                # recusa desligava a sonda depois de dois domínios: na primeira medição, 149
                # candidatos e 13 nunca avaliados por um disjuntor disparado por 404.
                recusou = eh_recusa_de_acesso(e)
                orcamento.registrar(url, recusada=recusou)
                if recusou:
                    # O host barrou o Monitor. Tentar os outros três caminhos seria insistir contra
                    # bloqueio explícito — e, de quebra, foi assim que um único host hostil somou
                    # quatro recusas e desligou a sonda da noite inteira na primeira medição.
                    break
                continue
            break
        for caminho in tuple(CAMINHOS_DE_VITRINE) + tuple(CAMINHOS_DE_FEED):
            url = f"https://{dominio}{caminho}"
            pode, _ = orcamento.pode_ler(url)
            if not pode:
                break
            try:
                paginas[url] = abrir(url)
                orcamento.registrar(url, recusada=False)
            except Exception as e:  # noqa: BLE001
                recusou = eh_recusa_de_acesso(e)
                orcamento.registrar(url, recusada=recusou)
                if recusou:
                    break
                continue
            break
        sinais = sinais_de_veiculo(dominio, paginas, materias)
        entra, motivo = pode_entrar(dominio, sinais, bloqueados)
        if entra:
            entradas.append((dominio, sinais))
        else:
            recusas[motivo] = recusas.get(motivo, 0) + 1
            if motivo == "sitio_institucional_nao_e_veiculo":
                institucionais.append((dominio, sinais))

    if institucionais and escrever:
        registrar_institucionais(institucionais, hoje)
    if entradas and escrever:
        lista = json.loads(VEICULOS.read_text(encoding="utf-8")) if VEICULOS.exists() else {}
        for dominio, sinais in entradas:
            registrar_entrada(lista, dominio, sinais, hoje)
        gravar_em(VEICULOS, lista)          # §229
    return {"candidatos": len(candidatos), "avaliados_por_noite": DOMINIOS_AVALIADOS_POR_NOITE,
            "entraram": [d for d, _ in entradas], "recusas": recusas,
            "institucionais": [d for d, _ in institucionais]}


def rodar_sombra(limite: int = None, escrever: bool = True) -> dict:
    """Lê as pistas pendentes, verifica e grava `verificacao_fonte` — e SÓ esse campo."""
    from coletores_base import OrcamentoDeRequisicoes, buscar, gravar_em, hoje_editorial

    doc = json.loads(PISTAS.read_text(encoding="utf-8"))
    pistas = doc.get("pistas") or []
    veiculos, locais = carregar_listas()
    banco = municipios_no_banco()
    hoje = hoje_editorial()
    orcamento = OrcamentoDeRequisicoes()

    contagem = {"na_fila": 0, "lidas": 0, "exibiveis": 0, "inacessiveis": 0,
                "nao_lidas_por_orcamento": 0, "resolucoes": 0,
                "nao_resolvidas_por_orcamento": 0, "por_motivo": {}}
    vistas_por_sindicacao = {}
    fila = ordem_da_fila([p for p in pistas if p.get("url")], veiculos)
    contagem["na_fila"] = len(fila)

    # Item 3: a lista cresce ANTES da verificação da noite — do contrário o domínio que acabou de
    # cumprir o critério esperaria a noite seguinte para ter a primeira matéria lida.
    contagem["crescimento_da_lista"] = crescer_lista_de_veiculos(
        fila, veiculos, orcamento=orcamento, hoje=hoje, escrever=escrever)
    if contagem["crescimento_da_lista"]["entraram"]:
        veiculos, locais = carregar_listas()

    for pista in fila:
        if limite and contagem["lidas"] >= limite:
            contagem["nao_lidas_por_orcamento"] += 1
            continue
        if orcamento.encerrar_a_rodada():
            contagem["nao_lidas_por_orcamento"] += 1
            continue
        # O `<source url>` do RSS já diz de quem é a matéria. Quando ele diz, e o domínio não está
        # na lista, a recusa sai SEM REDE — resolver o link para depois descartar por lista gastaria
        # uma requisição por pista, milhares por noite, para não mudar o veredito.
        dom_do_feed = dominio_de(pista.get("veiculo_dominio"))
        if dom_do_feed and dom_do_feed not in veiculos:
            m = "veiculo_nao_listado"
            contagem["por_motivo"][m] = contagem["por_motivo"].get(m, 0) + 1
            pista["verificacao_fonte"] = {
                "versao": VERSAO, "exibivel": False, "motivo": m, "lido_em": hoje.isoformat(),
                "url": pista["url"], "criterios": {"B5_veiculo": {
                    "ok": False, "trecho": f"{dom_do_feed} (do `<source url>` do feed) não está em "
                                           "data/veiculos_imprensa.json"}}}
            continue

        # Item 1: o link do agregador é caminho, não fonte. Resolve-se primeiro; sem resolver, a
        # pista fica declarada na fila em vez de ser verificada contra o domínio do agregador.
        #
        # A resolução tem TETO PRÓPRIO por noite. As 5.425 pistas já na fila vieram antes de o
        # monitor guardar o `<source url>`, de modo que nelas a pré-checagem sem rede não se aplica
        # e cada uma exigiria uma requisição ao agregador. Sem teto, a noite terminava resolvendo
        # link em vez de ler matéria: com limite de 10 leituras, mais de dez minutos sem chegar à
        # primeira página de veículo. O que passa do teto espera a noite seguinte, contado no funil.
        precisa_rede = eh_agregador(pista["url"]) and not url_dentro_do_segmento(pista["url"])
        if precisa_rede and contagem["resolucoes"] >= RESOLUCOES_POR_NOITE:
            contagem["nao_resolvidas_por_orcamento"] += 1
            continue
        if precisa_rede:
            contagem["resolucoes"] += 1
        alvo_url, degrau = resolver_redirecionamento(
            pista["url"], abrir=(lambda u: abrir_seguindo_redirecionamento(u, timeout=15)))
        if alvo_url is None:
            contagem["por_motivo"]["redirecionamento_nao_resolvido"] = contagem["por_motivo"].get(
                "redirecionamento_nao_resolvido", 0) + 1
            pista["verificacao_fonte"] = {
                "versao": VERSAO, "exibivel": False, "motivo": "redirecionamento_nao_resolvido",
                "lido_em": hoje.isoformat(), "url": pista["url"], "criterios": {}}
            continue
        if alvo_url != pista["url"]:
            # Não se reatribui `pista`: ela é o objeto DENTRO de `doc`, e a cópia perderia a
            # gravação do veredito. O endereço resolvido anda nos campos, não numa cópia.
            pista["url_do_agregador"] = pista["url"]
            pista["degrau_do_redirecionamento"] = degrau
            pista["url"] = alvo_url

        pode, motivo_orc = orcamento.pode_ler(pista["url"])
        municipio, uf = alvo_para_municipio(pista)
        contexto = {"veiculos": veiculos, "locais": locais, "hoje": hoje,
                    "no_banco": (norm(municipio), str(uf or "").upper()) in banco}

        # O veículo não listado é decidido SEM rede: não se gasta requisição para descobrir que o
        # domínio não está na lista.
        pre = b5_veiculo(pista["url"], veiculos)
        if not pre[0]:
            v = {"versao": VERSAO, "exibivel": False, "motivo": pre[1], "lido_em": hoje.isoformat(),
                 "criterios": {"B5_veiculo": {"ok": False, "trecho": pre[2]}}, "url": pista["url"]}
        elif not pode:
            contagem["nao_lidas_por_orcamento"] += 1
            v = {"versao": VERSAO, "exibivel": False, "motivo": "nao_lido_esta_noite",
                 "lido_em": hoje.isoformat(), "criterios": {}, "orcamento": motivo_orc,
                 "url": pista["url"]}
            pista["verificacao_fonte"] = v
            continue
        else:
            try:
                html = buscar(pista["url"], timeout=45, origem="verificar_pista_imprensa").decode(
                    "utf-8", "replace")
                orcamento.registrar(pista["url"], recusada=False)
                contagem["lidas"] += 1
                v = verificar(html, {**pista, "municipio": municipio, "uf": uf}, contexto)
            except Exception as e:  # noqa: BLE001
                orcamento.registrar(pista["url"], recusada=True)
                contagem["inacessiveis"] += 1
                v = {"versao": VERSAO, "exibivel": False, "motivo": "inacessivel",
                     "lido_em": hoje.isoformat(), "url": pista["url"],
                     "criterios": {"A4_acesso": {"ok": False, "trecho": type(e).__name__}}}

        # Sindicação: a mesma matéria em vários domínios exibe uma vez só, a do veículo mais local.
        if v.get("exibivel"):
            ch = chave_de_sindicacao({"municipio": municipio, "titulo": pista.get("titulo")},
                                     v.get("data_da_materia") or "")
            if ch in vistas_por_sindicacao:
                v["exibivel"] = False
                v["motivo"] = "sindicacao_duplicada"
                v["criterios"]["B5_sindicacao"] = {"ok": False,
                                                   "trecho": "mesma matéria já contada em "
                                                             + vistas_por_sindicacao[ch]}
            else:
                vistas_por_sindicacao[ch] = pista["url"]

        pista["verificacao_fonte"] = v      # ÚNICO campo que este script escreve (seção G1)
        if v.get("exibivel"):
            contagem["exibiveis"] += 1
        else:
            m = v.get("motivo") or "sem_motivo"
            contagem["por_motivo"][m] = contagem["por_motivo"].get(m, 0) + 1

    contagem["orcamento"] = orcamento.contadores()
    if escrever:
        gravar_em(PISTAS, doc)              # §229
        _gravar_contadores(contagem, hoje)
    return contagem


def _gravar_contadores(contagem: dict, hoje) -> None:
    """Contadores do dia em data/funil/<data>.json (seção G4), sem apagar o que já está lá."""
    from coletores_base import gravar_em
    pasta = RAIZ / "data" / "funil"
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / f"{hoje.isoformat()}.json"
    doc = json.loads(caminho.read_text(encoding="utf-8")) if caminho.exists() else {}
    doc["verificador_imprensa"] = {**contagem, "versao": VERSAO}
    gravar_em(caminho, doc)


# =============================================================================================
# Item 4 — a amostra abre com 20, e o limiar tem intervalo, não só ponto
# =============================================================================================
EXIBIVEIS_PARA_AMOSTRA = 20
RECUSADAS_NA_AMOSTRA = 10
PRECISAO_MINIMA = 0.95
WILSON_MINIMO = 0.80
NOITES_ATE_RELATAR = 14


def wilson(acertos: int, n: int, z: float = 1.96) -> tuple:
    """(limite_inferior, limite_superior) do intervalo de Wilson a 95%. Função pura.

    Por que Wilson e não só a proporção: com n pequeno, "19 de 20 = 95%" e "95 de 100 = 95%" são
    a mesma proporção e não são a mesma evidência. O intervalo diz isso — com 20 casos, o limite
    inferior de 95% de acerto fica perto de 76%, e é esse número que mede o risco de ligar a
    exibição cedo demais. A regra de passagem pede os dois: proporção e limite inferior."""
    if n <= 0:
        return 0.0, 0.0
    p = acertos / n
    d = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / d
    meia = (z / d) * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return max(0.0, centro - meia), min(1.0, centro + meia)


def veredito_da_amostra(acertos: int, n: int) -> dict:
    """Passa ou não passa, com o n e o intervalo escritos por extenso.

    Nunca devolve só "passou": devolve a frase que vai para o relatório e para a METODOLOGIA,
    porque limiar sem n e sem intervalo é número solto."""
    p = (acertos / n) if n else 0.0
    inf, sup = wilson(acertos, n)
    passa = (n >= EXIBIVEIS_PARA_AMOSTRA and p >= PRECISAO_MINIMA and inf >= WILSON_MINIMO)
    frase = (f"{acertos} de {n} corretas = {p * 100:.1f}% de precisão observada; "
             f"intervalo de Wilson a 95%: de {inf * 100:.1f}% a {sup * 100:.1f}%. "
             f"Regra de passagem: n de no mínimo {EXIBIVEIS_PARA_AMOSTRA}, precisão de no mínimo "
             f"{PRECISAO_MINIMA * 100:.0f}% e limite inferior de no mínimo "
             f"{WILSON_MINIMO * 100:.0f}%.")
    if not passa:
        faltou = []
        if n < EXIBIVEIS_PARA_AMOSTRA:
            faltou.append(f"a amostra tem {n}, e o mínimo é {EXIBIVEIS_PARA_AMOSTRA}")
        if p < PRECISAO_MINIMA:
            faltou.append(f"a precisão é {p * 100:.1f}%, abaixo de {PRECISAO_MINIMA * 100:.0f}%")
        if inf < WILSON_MINIMO:
            faltou.append(f"o limite inferior é {inf * 100:.1f}%, abaixo de "
                          f"{WILSON_MINIMO * 100:.0f}%")
        frase += " NÃO passa: " + "; ".join(faltou) + "."
    return {"passa": passa, "n": n, "acertos": acertos, "precisao": p,
            "wilson_inferior": inf, "wilson_superior": sup, "frase": frase}


def relatorio_de_amostra(semente: int = 42, n_exibiveis: int = EXIBIVEIS_PARA_AMOSTRA,
                         n_recusadas: int = RECUSADAS_NA_AMOSTRA) -> str:
    """O pacote cego da seção D2: amostra sorteada para leitura humana.

    Cego quer dizer: o que a editoria lê é URL, município e os trechos que o verificador usou —
    **não** o veredito. Quem lê decide sem saber o que a máquina decidiu, que é o que faz a medição
    de precisão valer alguma coisa."""
    import random
    doc = json.loads(PISTAS.read_text(encoding="utf-8"))
    verificadas = [p for p in (doc.get("pistas") or []) if p.get("verificacao_fonte")]
    exibiveis = [p for p in verificadas if p["verificacao_fonte"].get("exibivel")]
    recusadas = [p for p in verificadas
                 if not p["verificacao_fonte"].get("exibivel")
                 and p["verificacao_fonte"].get("motivo") not in ("veiculo_nao_listado",
                                                                  "nao_lido_esta_noite")]
    r = random.Random(semente)
    am_e = r.sample(exibiveis, min(n_exibiveis, len(exibiveis)))
    am_r = r.sample(recusadas, min(n_recusadas, len(recusadas)))

    L = [f"# Verificador de pistas de imprensa — amostra cega · {VERSAO}", "",
         f"Verificadas: **{len(verificadas)}** · exibíveis: **{len(exibiveis)}** · "
         f"recusadas (fora as de veículo não listado): **{len(recusadas)}**", "",
         f"Amostra pedida: {n_exibiveis} exibíveis + {n_recusadas} recusadas, semente {semente}. "
         f"Amostra obtida: **{len(am_e)} + {len(am_r)}**.", ""]
    L += ["Regra de passagem, escrita por extenso antes da leitura para que ela não se ajuste ao "
          f"resultado: a exibição só liga com amostra de no mínimo {EXIBIVEIS_PARA_AMOSTRA} "
          f"exibíveis, precisão observada de no mínimo {PRECISAO_MINIMA * 100:.0f}% e limite "
          f"inferior do intervalo de Wilson a 95% de no mínimo {WILSON_MINIMO * 100:.0f}%. "
          "Ao fim da leitura, informe quantas das exibíveis estavam corretas; o veredito sai de "
          "`--veredito <corretas> <n>`.", ""]
    if len(am_e) < n_exibiveis:
        L += [f"> **A amostra de exibíveis saiu incompleta: {len(am_e)} de {n_exibiveis}.** "
              f"Não há como medir precisão de {PRECISAO_MINIMA * 100:.0f}% sobre menos de "
              f"{n_exibiveis} casos, e completar a amostra com pista recusada seria medir outra "
              f"coisa. Se depois de {NOITES_ATE_RELATAR} noites a fila não tiver "
              f"{EXIBIVEIS_PARA_AMOSTRA} exibíveis, o que vale é o relato da composição da fila e "
              "da causa dominante, nas contagens acima — não uma amostra menor.", ""]
    for titulo, grupo in (("## Exibíveis", am_e), ("## Recusadas", am_r)):
        L.append(titulo)
        L.append("")
        for p in grupo:
            v = p["verificacao_fonte"]
            municipio, uf = alvo_para_municipio(p)
            L.append(f"### {municipio}/{uf} · {p.get('url')}")
            L.append(f"- título na fonte: {p.get('titulo') or '—'}")
            L.append(f"- data da matéria: {v.get('data_da_materia') or '—'}")
            for nome, c in (v.get("criterios") or {}).items():
                L.append(f"- {nome}: {str(c.get('trecho'))[:220]}")
            L.append("")
    return "\n".join(L)


def funil_da_noite(data=None) -> str:
    """Item 5: o funil da noite em Markdown, pronto para o resumo do job e para o ESTADO_ATUAL.

    Fila, resolvidas, lidas, exibíveis e cada motivo de recusa com o seu número. O funil é o que
    mostra por que a exibição ainda não liga: sem ele, "0 exibíveis" pareceria defeito quando é
    critério — e, no caso contrário, esconderia critério frouxo atrás de um total bonito."""
    from coletores_base import hoje_editorial
    data = data or hoje_editorial()
    caminho = RAIZ / "data" / "funil" / f"{data.isoformat()}.json"
    if not caminho.exists():
        return f"Verificador de imprensa · {data.isoformat()}: não há funil gravado para esta data."
    c = (json.loads(caminho.read_text(encoding="utf-8")) or {}).get("verificador_imprensa") or {}
    if not c:
        return (f"Verificador de imprensa · {data.isoformat()}: o funil do dia existe, mas não "
                "traz a seção do verificador — o modo sombra não rodou nesta data.")
    cresc = c.get("crescimento_da_lista") or {}
    L = [f"### Verificador de imprensa · {data.isoformat()} · {c.get('versao', VERSAO)}",
         "",
         f"- fila: **{c.get('na_fila', 0)}**",
         f"- resolvidas por rede: **{c.get('resolucoes', 0)}** de um teto de "
         f"{RESOLUCOES_POR_NOITE} · não resolvidas por teto: "
         f"**{c.get('nao_resolvidas_por_orcamento', 0)}**",
         f"- lidas: **{c.get('lidas', 0)}** · inacessíveis: **{c.get('inacessiveis', 0)}** · "
         f"não lidas por orçamento: **{c.get('nao_lidas_por_orcamento', 0)}**",
         f"- exibíveis: **{c.get('exibiveis', 0)}** (limiar da amostra humana: "
         f"{EXIBIVEIS_PARA_AMOSTRA})",
         f"- entradas automáticas na lista de veículos: **{len(cresc.get('entraram') or [])}** "
         f"de {cresc.get('candidatos', 0)} candidatos"]
    if cresc.get("entraram"):
        L.append("  - " + ", ".join(cresc["entraram"]))
    if cresc.get("recusas"):
        L.append("  - não entraram: " + " · ".join(
            f"{m}: {n}" for m, n in sorted((cresc["recusas"]).items(), key=lambda kv: -kv[1])))
    L.append("- recusas por motivo:")
    for m, n in sorted((c.get("por_motivo") or {}).items(), key=lambda kv: -kv[1]):
        L.append(f"  - {m}: **{n}**")
    return "\n".join(L)


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()

    if "--relatorio" in sys.argv:
        print(relatorio_de_amostra())
        return 0

    if "--funil" in sys.argv:
        print(funil_da_noite())
        return 0

    if "--veredito" in sys.argv:
        i = sys.argv.index("--veredito")
        try:
            acertos, n = int(sys.argv[i + 1]), int(sys.argv[i + 2])
        except (IndexError, ValueError):
            print("--veredito exige dois inteiros: corretas e total lido")
            return 2
        if acertos > n:
            print("--veredito: corretas não pode passar do total")
            return 2
        r = veredito_da_amostra(acertos, n)
        print(r["frase"])
        print("PASSA" if r["passa"] else "NÃO PASSA")
        return 0 if r["passa"] else 1

    limite = None
    if "--limite" in sys.argv:
        try:
            limite = int(sys.argv[sys.argv.index("--limite") + 1])
        except (IndexError, ValueError):
            print("--limite exige um inteiro")
            return 2

    if "--sombra" not in sys.argv:
        print(__doc__.strip().splitlines()[0])
        print("use --autoteste, --sombra ou --relatorio")
        return 0

    c = rodar_sombra(limite=limite)
    print(f"fila: {c['na_fila']} · resolvidas: {c['resolucoes']} · "
          f"não resolvidas por teto: {c['nao_resolvidas_por_orcamento']} · lidas: {c['lidas']} · "
          f"exibíveis: {c['exibiveis']} · "
          f"inacessíveis: {c['inacessiveis']} · não lidas por orçamento: "
          f"{c['nao_lidas_por_orcamento']}")
    for m, n in sorted(c["por_motivo"].items(), key=lambda kv: -kv[1]):
        print(f"  {m}: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
