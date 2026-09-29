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
           "ja_tem_registro", "recusada_pelo_juiz", "sindicacao_duplicada")


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


def data_de_publicacao(html: str):
    """Data dos METADADOS da página, nunca a do rastreio. None quando não há — e sem data não
    exibe, porque matéria de 2015 recuperada pela busca é a falha mais comum desta fila."""
    padroes = [r'property=["\']article:published_time["\']\s+content=["\']([^"\']+)',
               r'content=["\']([^"\']+)["\']\s+property=["\']article:published_time["\']',
               r'"datePublished"\s*:\s*"([^"]+)"',
               r'<time[^>]+datetime=["\']([^"\']+)']
    for p in padroes:
        m = re.search(p, html or "", re.I)
        if m:
            try:
                return datetime.date.fromisoformat(m.group(1).strip()[:10])
            except ValueError:
                continue
    return None


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
    data = data_de_publicacao(html)
    if data is None:
        return False, "sem_data", "sem data de publicação nos metadados"
    if data < DATA_BOLETIM_1:
        return False, "fora_do_ciclo", f"publicada em {data.isoformat()}, antes do Boletim nº 1"
    if data > hoje:
        return False, "fora_do_ciclo", f"data futura: {data.isoformat()}"
    return True, "", data.isoformat()


def b5_veiculo(url: str, veiculos: dict) -> tuple:
    """(ok, motivo, trecho). Só domínio listado entra, e só por HTTPS."""
    if not str(url or "").lower().startswith("https://"):
        return False, "sem_https", "a página não é servida por HTTPS"
    host = re.sub(r"^https?://(www\.)?([^/]+).*", r"\2", str(url)).lower()
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

    hoje = contexto.get("hoje") or datetime.date.today()
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
    casos.append(("e a data da matéria, dos metadados", v_bom.get("data_da_materia") == "2026-08-15"))
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
    casos.append(("data de metadado é lida do JSON-LD também",
                  data_de_publicacao('<html>{"datePublished": "2026-07-01T00:00:00"}</html>')
                  == datetime.date(2026, 7, 1)))
    casos.append(("página sem data devolve None, e sem data não exibe",
                  data_de_publicacao("<html></html>") is None))

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
                "nao_lidas_por_orcamento": 0, "por_motivo": {}}
    vistas_por_sindicacao = {}
    fila = ordem_da_fila([p for p in pistas if p.get("url")], veiculos)
    contagem["na_fila"] = len(fila)

    for pista in fila:
        if limite and contagem["lidas"] >= limite:
            contagem["nao_lidas_por_orcamento"] += 1
            continue
        if orcamento.encerrar_a_rodada():
            contagem["nao_lidas_por_orcamento"] += 1
            continue
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


def relatorio_de_amostra(semente: int = 42, n_exibiveis: int = 40, n_recusadas: int = 20) -> str:
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
    if len(am_e) < n_exibiveis:
        L += [f"> **A amostra de exibíveis saiu incompleta: {len(am_e)} de {n_exibiveis}.** "
              "Não há como medir precisão de 95% sobre menos de 40 casos, e completar a amostra "
              "com pista recusada seria medir outra coisa. A causa está nas contagens acima.", ""]
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


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()

    if "--relatorio" in sys.argv:
        print(relatorio_de_amostra())
        return 0

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
    print(f"fila: {c['na_fila']} · lidas: {c['lidas']} · exibíveis: {c['exibiveis']} · "
          f"inacessíveis: {c['inacessiveis']} · não lidas por orçamento: "
          f"{c['nao_lidas_por_orcamento']}")
    for m, n in sorted(c["por_motivo"].items(), key=lambda kv: -kv[1]):
        print(f"  {m}: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
