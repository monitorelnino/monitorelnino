#!/usr/bin/env python3
"""Busca de planos municipais de contingência em fontes abertas por município (22/10/2026,
HANDOVER_REPOSITORIOS_DE_PLANOS_MUNICIPAIS §1.9–§1.11; matriz S13, S16, S25, S29).

Quatro consultas por município, todas a APIs públicas, sem login, sem LAI, sem chave:
  S13  LexML (SRU)               legislação que cita o plano do município
  S16  Wayback Machine (CDX)     cópias arquivadas do domínio da prefeitura com plano/PLANCON no endereço
  S25  Common Crawl (índice)     o mesmo, no índice de rastreio aberto; o arquivo só se baixa da origem
  S29  dados.gov.br (CKAN)       conjuntos de dados que citam o plano do município
  S27  hospedagem de documentos  Scribd, Issuu, Calameo, Yumpu, DocPlayer, SlideShare (pelo metabuscador, 26/10/2026)
  S24  planos conexos            PMRR, saneamento, plano de saúde, consórcio, comitê (pelo metabuscador, 26/10/2026)
  S18  Querido Diário            excerto de plano nos diários oficiais do território (API pública, por código IBGE, 26/10/2026)
  S20  Ministério Público        recomendação, TAC, inquérito civil (metabuscador, endereço .mp.br, 26/10/2026)
  S21  Judiciário                ação civil pública e decisão (metabuscador, endereço .jus.br, 26/10/2026)
  S23  Saúde                     CIB/CIEVS/SES, plano de contingência da dengue (metabuscador, .gov.br/.leg.br, 26/10/2026)
  S31  Transferegov              proposta, plano de trabalho e anexo (metabuscador, .gov.br, 26/10/2026)
  S17  Coordenadorias          CREPDEC/REDEC e defesa civil estadual (metabuscador, .gov.br, 27/10/2026)
  S19  Diários por associação  AMM, FAMURS, APPM, AMUPE, FEMURN e similares (metabuscador, 27/10/2026)
  S26  Acadêmico               TCC, dissertação e tese em repositório institucional (metabuscador, 27/10/2026)
  S30  Programas por adesão    Operação Verão/Chuvas, plano preventivo (metabuscador, .gov.br, 27/10/2026)
  S22  PNCP (api/consulta)       contratação municipal cujo objeto cita o plano (por código IBGE; só pista, contratação não é plano)

Disciplina: cliente identificado, robots e Crawl-delay pela `buscar_uma_vez`, pausa por host, e
401/403/429/451 ou muro de robô são RECUSA registrada (nunca retentativa). Resposta que não se
entende é `erro`, nunca `sem_resultado`: ausência de achado só vale com a consulta registrada.

Trava estrutural: nunca escreve em estados.json, saude_uf.json, municipios.json, indice.json nem
monitor_saude.json. Trava de campo: toda pista nasce com `documento_oficial_confirmado: null` e
`promovivel: false`. Trava de processo: a saída vai à porta única (`scripts/pistas.gravar_lote`) e ao
juiz; a camada declarada nunca vira documento. O resultado por município/fonte fica em
`data/planos_busca/<UF>.json` (um arquivo por UF, só este script escreve): grupos de UF em paralelo não
gravam o mesmo arquivo.

Uso:
  python3 buscar_planos_fontes_abertas.py --autoteste
  python3 buscar_planos_fontes_abertas.py --alvos data/capitais_alvos.json [--fontes S16,S25] [--limite N] [--uf SP]
  (--alvos aceita `fila` de códigos ou `municipios` com `codigo_ibge`; retoma o que não foi consultado hoje)
"""
import io
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import xml.etree.ElementTree as ET

from coletores_base import (buscar_uma_vez, ler, gravar, hoje_editorial, referencia_ibge,
                            rodar_autoteste, registrar_lacuna, MuroDeRobo)
from descobrir_planos import dominios_do_municipio, identifica_prefeitura, RECUSAS_DE_FONTE
from consultar_querido_diario import STATUS_DA_PISTA, APIS as APIS_QD
from scripts.pistas import gravar_lote

PASTA = "planos_busca"
PAUSA = 2.0
TETO_POR_FONTE = 5
PADRAO_PLANO = re.compile(r"plancon|placon|conting[eê]nc|plano[-_ /]*municipal[-_ /]*de[-_ /]*defesa|pdec", re.I)
# Capitais cujo endereço padrão `<município>.<uf>.gov.br` não é o da prefeitura: candidatos a VERIFICAR
# (só valem se a home se identifica como a prefeitura, como em `descobrir_no_portal`).
CANDIDATOS_EXTRA = {
    "3106200": ["prefeitura.pbh.gov.br"], "5300108": ["df.gov.br"], "1501402": ["belem.pa.gov.br"],
    "2611606": ["recife.pe.gov.br"], "2211001": ["pmt.pi.gov.br"], "3304557": ["prefeitura.rio"],
    "2408102": ["natal.rn.gov.br"], "4314902": ["prefeitura.poa.br"], "4205407": ["pmf.sc.gov.br"],
}


# ---- consultas e leitores (puros) --------------------------------------------------------------
def consulta_wayback(dominio: str) -> str:
    q = {"url": dominio, "matchType": "domain", "output": "json", "fl": "original,timestamp,mimetype",
         "filter": ["statuscode:200", "original:.*(plancon|placon|contingenc).*"], "collapse": "urlkey", "limit": 30}
    return "https://web.archive.org/cdx/search/cdx?" + urllib.parse.urlencode(q, doseq=True)


def ler_wayback(corpo: bytes) -> list:
    """[(url, titulo)]: a cópia arquivada de cada endereço. Levanta ValueError se o corpo não é CDX."""
    linhas = json.loads(corpo.decode("utf-8") or "[]")
    if linhas and linhas[0] != ["original", "timestamp", "mimetype"]:
        raise ValueError("cabeçalho CDX inesperado")
    return [(f"https://web.archive.org/web/{ts}/{orig}", f"Cópia arquivada: {orig}")
            for orig, ts, _ in linhas[1:] if PADRAO_PLANO.search(orig)]


def indice_common_crawl(collinfo: bytes) -> str:
    """O `cdx-api` do rastreio mais novo. Levanta ValueError se a lista vier vazia."""
    lista = json.loads(collinfo.decode("utf-8"))
    return sorted(lista, key=lambda c: c["id"])[-1]["cdx-api"]


def consulta_common_crawl(api: str, dominio: str) -> str:
    q = {"url": f"{dominio}/*", "output": "json", "fl": "url,status,mime",
         "filter": ["=status:200", "url:.*(plancon|placon|contingenc).*"], "limit": 30}
    return api + "?" + urllib.parse.urlencode(q, doseq=True)


def sem_capturas(e: Exception) -> bool:
    """O índice do Common Crawl responde 404 com "No Captures found" quando o domínio não tem captura que
    case: é resposta (ausência com a consulta registrada), não falha. 404 sem essa frase continua erro."""
    if not (isinstance(e, urllib.error.HTTPError) and e.code == 404 and e.fp is not None):
        return False
    return b"no captures found" in e.read().lower()


def ler_common_crawl(corpo: bytes) -> list:
    achados = []
    for linha in corpo.decode("utf-8").splitlines():
        if linha.strip():
            url = json.loads(linha)["url"]
            if PADRAO_PLANO.search(url):
                achados.append((url, f"Rastreio aberto: {url}"))
    return list(dict.fromkeys(achados))


def consulta_lexml(nome: str) -> str:
    cql = f'"plano de contingência" and "{nome}"'
    return "https://www.lexml.gov.br/busca/SRU?" + urllib.parse.urlencode(
        {"operation": "searchRetrieve", "version": "1.1", "query": cql, "maximumRecords": 10})


def ler_lexml(corpo: bytes, nome: str) -> list:
    """[(url, título)] dos registros que citam o município e o plano. Levanta ValueError se não é SRU."""
    raiz = ET.fromstring(corpo)
    if not raiz.tag.endswith("searchRetrieveResponse"):
        raise ValueError("resposta não é SRU")
    achados = []
    for reg in (e for e in raiz.iter() if e.tag.endswith("}recordData") or e.tag == "recordData"):
        campos = {}
        for e in reg.iter():
            tag = e.tag.rsplit("}", 1)[-1]
            if e.text and e.text.strip():
                campos.setdefault(tag, e.text.strip())
        titulo = campos.get("title") or campos.get("description") or ""
        url = campos.get("urn") and "https://www.lexml.gov.br/urn/" + campos["urn"] or campos.get("identifier") or ""
        if url and PADRAO_PLANO.search(titulo) and cita(titulo + " " + campos.get("urn", ""), nome):
            achados.append((url, titulo[:200]))
    return achados


def consulta_ckan(nome: str) -> str:
    return "https://dados.gov.br/api/3/action/package_search?" + urllib.parse.urlencode(
        {"q": f'"plano de contingência" "{nome}"', "rows": 10})


def ler_ckan(corpo: bytes, nome: str) -> list:
    dados = json.loads(corpo.decode("utf-8"))
    if not dados.get("success"):
        raise ValueError("CKAN sem success")
    achados = []
    for p in dados["result"]["results"]:
        texto = f'{p.get("title", "")} {p.get("notes", "")}'
        if PADRAO_PLANO.search(texto) and cita(texto, nome):
            achados.append((f'https://dados.gov.br/dados/conjuntos-dados/{p.get("name", "")}', p.get("title", "")[:200]))
    return achados


def cita(texto: str, nome: str) -> bool:
    """O nome do município aparece como palavra inteira (não dentro de outra palavra). Pura.
    Homônimo composto ("Alfa Verde") passa: quem decide é o juiz, a pista só agrupa candidatos."""
    t = " ".join(re.sub(r"\W+", " ", texto.lower()).split())
    n = " ".join(re.sub(r"\W+", " ", nome.lower()).split())
    return bool(re.search(rf"\b{re.escape(n)}\b", t))


# ---- fontes pelo metabuscador da válvula (SearXNG), filtradas por endereço e por texto -------------
# Uma tabela, uma regra: o endereço é de um dos domínios da fonte, o município aparece no texto ou no
# endereço, o termo da fonte (se houver) e o plano são citados. Fonte nova = linha nova.
HOSPEDAGENS = ("scribd.com", "issuu.com", "calameo.com", "yumpu.com", "docplayer.com.br", "slideshare.net")
INSTITUCIONAIS = (".gov.br", ".leg.br", ".jus.br", ".mp.br", ".def.br", ".tc.br")
PADRAO_CONEXO = re.compile(r"redu[cç][aã]o de risco|pmrr|saneamento b[aá]sico|plano municipal de sa[uú]de|cons[oó]rcio|comit[eê] de bacia", re.I)
PADRAO_MP = re.compile(r"recomenda[cç][aã]o|termo de ajustamento|\bTAC\b|inqu[eé]rito civil|a[cç][aã]o civil p[uú]blica", re.I)
PADRAO_JUS = re.compile(r"a[cç][aã]o civil p[uú]blica|senten[cç]a|ac[oó]rd[aã]o|decis[aã]o|processo n", re.I)
PADRAO_SAUDE = re.compile(r"dengue|arbovirose|chikungunya|\bCIB\b|CIEVS", re.I)
PADRAO_TRANSFERENCIA = re.compile(r"transferegov|plano de trabalho|proposta|conv[eê]nio|termo de fomento", re.I)
ASSOCIACOES = ("famurs.com.br", "appm.org.br", "amupe.org.br", "femurn.org.br", "amm.org.br", "amm-mt.org.br", "fecam.org.br",
               "famem.org.br", "diariomunicipal.com.br")
ACADEMICOS = (".edu.br", "ibict.br", "scielo.br", "usp.br", "unesp.br", "unicamp.br")
PADRAO_COORDENADORIA = re.compile(r"crepdec|redec|coordenadoria (regional|estadual)|defesa civil estadual", re.I)
PADRAO_ATO = re.compile(r"decreto|portaria|lei municipal|institui|aprova", re.I)
PADRAO_ACADEMICO = re.compile(r"tese|disserta[cç][aã]o|monografia|trabalho de conclus[aã]o|\bTCC\b|reposit[oó]rio", re.I)
PADRAO_PROGRAMA = re.compile(r"opera[cç][aã]o (ver[aã]o|chuvas)|plano preventivo|\bPPDC\b|programa estadual|ades[aã]o", re.I)
SITES = lambda ds: "(" + " OR ".join("site:" + d.lstrip(".") for d in ds) + ")"
# fonte: (endereços aceitos, termo da fonte ou None, consulta depois de "nome" UF)
FONTES_WEB = {
    "S27": (HOSPEDAGENS, None, f'"plano de contingência" "defesa civil" {SITES(HOSPEDAGENS)}'),
    "S24": (INSTITUCIONAIS, PADRAO_CONEXO, '("redução de riscos" OR PMRR OR "saneamento básico" OR "plano municipal de saúde" '
                                          'OR consórcio OR "comitê de bacia") "plano de contingência"'),
    "S20": ((".mp.br",), PADRAO_MP, '(recomendação OR "termo de ajustamento de conduta" OR "inquérito civil" OR "ação civil pública") '
                                    '"plano de contingência" site:mp.br'),
    "S21": ((".jus.br",), PADRAO_JUS, '("ação civil pública" OR sentença OR acórdão) "plano de contingência" site:jus.br'),
    "S23": ((".gov.br", ".leg.br"), PADRAO_SAUDE, '(dengue OR arboviroses OR CIB OR CIEVS) "plano de contingência" (site:gov.br OR site:leg.br)'),
    "S31": ((".gov.br",), PADRAO_TRANSFERENCIA, '(Transferegov OR "plano de trabalho" OR proposta OR convênio) "plano de contingência" site:gov.br'),
    "S17": ((".gov.br",), PADRAO_COORDENADORIA, '(CREPDEC OR REDEC OR "coordenadoria regional" OR "defesa civil estadual") "plano de contingência" site:gov.br'),
    "S19": (ASSOCIACOES, PADRAO_ATO, f'(decreto OR portaria OR "lei municipal") "plano de contingência" {SITES(ASSOCIACOES)}'),
    "S26": (ACADEMICOS, PADRAO_ACADEMICO, f'(tese OR dissertação OR TCC OR monografia) "plano de contingência" "defesa civil" {SITES(ACADEMICOS)}'),
    "S30": ((".gov.br",), PADRAO_PROGRAMA, '("Operação Verão" OR "Operação Chuvas" OR "plano preventivo" OR adesão) "plano de contingência" site:gov.br'),
}


def consulta_web(fonte: str, nome: str, uf: str) -> str:
    return f'"{nome}" {uf} {FONTES_WEB[fonte][2]}'


# ---- S18: Querido Diário por município (26/10/2026) ----------------------------------------------
def parametros_qd(ibge: str, cobertura: bool = False) -> dict:
    """Um território por chamada (o lote devolveu 8.165 zeros falsos em 03/09). `cobertura`: sem termo, só o total
    de edições do município no acervo, que distingue 'sem plano' de 'sem diário no acervo'. Pura."""
    base = {"territory_ids": str(ibge).zfill(7), "size": 1 if cobertura else 5}
    if cobertura:
        return base
    return {**base, "querystring": '"plano de contingência" | plancon | placon', "excerpt_size": 300, "number_of_excerpts": 1}


def url_qd(porta: str, params: dict) -> str:
    return porta + "?" + urllib.parse.urlencode(params)


def buscar_qd(buscar, params: dict) -> dict:
    """JSON da primeira porta do Querido Diário que responde. Recusa (401/403/429/451, muro) sobe na hora e nunca
    passa à porta seguinte; só falha de conexão ou TLS tenta a próxima. Se nenhuma responde, sobe o último erro com
    as portas tentadas."""
    falhas, ultimo = [], None
    for porta in APIS_QD:
        try:
            return json.loads(buscar(url_qd(porta, params), 60).decode("utf-8"))
        except (urllib.error.URLError, OSError) as e:
            if isinstance(e, urllib.error.HTTPError) and e.code in RECUSAS_DE_FONTE:
                raise
            ultimo = e
            falhas.append(f"{_host(porta)}: {type(e).__name__} {str(e)[:80]}")
    ultimo.add_note("portas tentadas: " + " | ".join(falhas))
    raise ultimo


def ler_qd(dados: dict) -> list:
    """(url, título) das edições cujo excerto cita o plano. Pura. Levanta se o corpo não é resposta da API."""
    if not isinstance(dados, dict) or not isinstance(dados.get("gazettes"), list):
        raise ValueError("resposta do Querido Diário sem `gazettes`")
    saida = []
    for g in dados["gazettes"]:
        url, excerto = g.get("url") or g.get("txt_url") or "", " ".join(str((g.get("excerpts") or [""])[0] or "").split())
        if url and PADRAO_PLANO.search(excerto) and url not in [u for u, _ in saida]:
            saida.append((url, f"edição de {g.get('date') or 's/d'}: {excerto}"))
    return saida


def consultar_qd(buscar, ibge: str) -> tuple:
    """(consulta, achados, motivo): sem achado, uma segunda chamada diz se o município tem diários no acervo (cobertura parcial)."""
    achados = ler_qd(buscar_qd(buscar, parametros_qd(ibge)))
    motivo = None
    if not achados:
        total = buscar_qd(buscar, parametros_qd(ibge, cobertura=True)).get("total_gazettes")
        if not isinstance(total, int):
            raise ValueError("resposta do Querido Diário sem `total_gazettes`")
        motivo = (f"{total} edição(ões) no acervo, nenhum excerto de plano" if total
                  else "município sem diário no acervo do Querido Diário (cobertura parcial: ausência de acervo, não de plano)")
    return url_qd(APIS_QD[0], parametros_qd(ibge)), achados, motivo


# ---- S22: compras públicas, PNCP por município (26/10/2026) ---------------------------------------
# A busca por texto do PNCP (api/search) recusa o cliente (HTTP 400 e conexão fechada, 27/27 capitais); a
# consulta por publicação (api/consulta) é a rota documentada e aberta: filtra por município e modalidade,
# e o objeto é lido aqui. Contratação de elaboração de plano é rastro de onde procurar o documento, não plano.
PNCP = "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao"
MODALIDADES_PNCP = (8, 9, 6, 4, 5, 7, 12, 10)   # dispensa, inexigibilidade, pregões, concorrências, credenciamento, manifestação
ANO_PNCP_DESDE = 2023
TAMANHO_PNCP = 500                              # páginas grandes: 10 capitais em 200 min a 50 por página; o servidor que recusa (400) volta a 50
PAGINAS_PNCP = 40                               # teto por consulta; estourar sem achado é erro, não ausência
PADRAO_OBJETO = re.compile(PADRAO_PLANO.pattern + r"|redu[cç][aã]o de risco|pmrr|defesa civil", re.I)


def parametros_pncp(ibge: str, modalidade: int, ano: int, hoje: str, pagina: int, tamanho: int = TAMANHO_PNCP) -> dict:
    """Janela de um ano civil (até hoje, `AAAA-MM-DD`), um município e uma modalidade por chamada. Pura."""
    fim = min(f"{ano}1231", hoje.replace("-", ""))
    return {"dataInicial": f"{ano}0101", "dataFinal": fim, "codigoModalidadeContratacao": modalidade,
            "codigoMunicipioIbge": str(ibge).zfill(7), "pagina": pagina, "tamanhoPagina": tamanho}


def ler_pncp(corpo: bytes) -> tuple:
    """((url, objeto) das contratações municipais cujo objeto cita o plano, nº de contratações, nº de páginas). Pura.
    Corpo vazio (204) é zero contratação; corpo que não é resposta da API levanta. Órgão de outra esfera (estadual,
    federal) com sede no município não conta como a prefeitura."""
    if not corpo.strip():
        return [], 0, 0
    d = json.loads(corpo.decode("utf-8"))
    if not isinstance(d, dict) or not isinstance(d.get("data"), list):
        raise ValueError("resposta do PNCP sem `data`")
    saida = []
    for c in d["data"]:
        org, objeto = c.get("orgaoEntidade") or {}, " ".join(str(c.get("objetoCompra") or "").split())
        if org.get("esferaId") not in (None, "M") or not PADRAO_OBJETO.search(objeto):
            continue
        ident = (org.get("cnpj"), c.get("anoCompra"), c.get("sequencialCompra"))
        if all(ident):
            saida.append(("https://pncp.gov.br/app/editais/%s/%s/%s" % ident, f"contratação de {c.get('anoCompra')}: {objeto}"))
    return saida, len(d["data"]), int(d.get("totalPaginas") or 1)


def consultar_pncp(buscar, ibge: str, hoje: str, paginas: int = PAGINAS_PNCP) -> tuple:
    """(consulta, achados, motivo): todas as modalidades e anos; só diz `sem_resultado` se leu tudo."""
    achados, lidas, consultas, truncada, tam = [], 0, 0, False, TAMANHO_PNCP
    for ano in range(ANO_PNCP_DESDE, int(hoje[:4]) + 1):
        for mod in MODALIDADES_PNCP:
            for pag in range(1, paginas + 1):
                try:
                    corpo = buscar(url_qd(PNCP, parametros_pncp(ibge, mod, ano, hoje, pag, tam)), 60)
                except urllib.error.HTTPError as e:
                    if e.code != 400 or consultas or tam == 50:   # só a primeira chamada prova o tamanho; recusa (403…) sobe
                        raise
                    tam = 50
                    corpo = buscar(url_qd(PNCP, parametros_pncp(ibge, mod, ano, hoje, pag, tam)), 60)
                itens, n, total = ler_pncp(corpo)
                consultas += 1
                lidas += n
                achados += [a for a in itens if a[0] not in [u for u, _ in achados]]
                if pag >= total:
                    break
            else:
                truncada = True
    if truncada and not achados:
        raise ValueError(f"leitura incompleta: mais de {paginas} páginas numa consulta, sem achado; não vale como ausência")
    motivo = None if achados else f"{lidas} contratação(ões) lida(s) em {consultas} consulta(s), nenhuma cita plano"
    return url_qd(PNCP, parametros_pncp(ibge, MODALIDADES_PNCP[0], ANO_PNCP_DESDE, hoje, 1)), achados, motivo


def _host(url: str) -> str:
    return (urllib.parse.urlparse(url).netloc or "").lower().split(":")[0]


def ler_web(dados: dict, nome: str, fonte: str) -> list:
    """Resultados do metabuscador que servem à fonte (`FONTES_WEB`). Pura. Levanta se o corpo não é resposta do
    SearXNG; `results` vazio devolve [] e quem chama decide (zero bruto não é ausência: o motor pode estar barrando, §186)."""
    if not isinstance(dados, dict) or not isinstance(dados.get("results"), list):
        raise ValueError("resposta do metabuscador sem `results`")
    dominios, termo, _ = FONTES_WEB[fonte]
    saida = []
    for r in dados["results"]:
        url, titulo = r.get("url") or "", (r.get("title") or "").strip()
        texto = f"{titulo} {r.get('content') or ''}"
        h = _host(url)
        if not url or not cita(texto + " " + url.replace("-", " ").replace("_", " "), nome):
            continue
        ok = any(h == d.lstrip(".") or h.endswith("." + d.lstrip(".")) for d in dominios) and (termo is None or termo.search(texto)) and PADRAO_PLANO.search(texto)
        if ok and url not in [u for u, _ in saida]:
            saida.append((url, titulo or url))
    return saida


def buscar_web(consulta: str) -> dict:
    """Uma consulta ao metabuscador com o ritmo e o disjuntor de `monitorar_busca_web` (intervalo com jitter)."""
    import monitorar_busca_web as mw
    time.sleep(mw.espera_do_ritmo(0))
    return mw.buscar_searxng(consulta)


def classificar_erro(e: Exception) -> tuple:
    """(situacao, motivo): recusa de fonte se respeita e nomeia; o resto é `erro`, não ausência."""
    if isinstance(e, urllib.error.HTTPError):
        return ("recusa_de_fonte", f"HTTP {e.code}") if e.code in RECUSAS_DE_FONTE else ("erro", f"HTTP {e.code}")
    if isinstance(e, MuroDeRobo):
        return "recusa_de_fonte", f"muro de robô ({e})"
    return "erro", f"{type(e).__name__}: {str(e)[:120]}"


def pista_de(nome: str, uf: str, ibge: str, fonte: str, url: str, titulo: str, hoje: str) -> dict:
    return {"documento_oficial_confirmado": None, "promovivel": False,       # trava de campo (R7)
            "municipio": nome, "uf": uf, "ibge": str(ibge).zfill(7), "url": url,
            "titulo": f"{fonte} · {nome}/{uf}: {titulo}"[:300], "trecho": titulo[:500],
            "data_publicacao": None, "origem": "descoberta", "hash_evidencia": None,
            "status": STATUS_DA_PISTA, "data": hoje, "registrado_em": hoje}


# ---- um município, quatro fontes ----------------------------------------------------------------
def resolver_dominio(nome: str, uf: str, ibge: str, buscar, tentativas: list = None) -> str | None:
    """O endereço que SE IDENTIFICA como a prefeitura; None se nenhum se identifica (busca não feita).
    `tentativas` recebe (endereço, situação, motivo) de cada um que não serviu."""
    for d in CANDIDATOS_EXTRA.get(ibge, []) + dominios_do_municipio(nome, uf):
        try:
            if identifica_prefeitura(buscar(f"https://{d}/", 15).decode("utf-8", "replace"), nome):
                return d
            r = ("nao_identifica", "responde, mas não se diz a prefeitura")
        except Exception as e:  # noqa: BLE001 — DNS, TLS, timeout, recusa: o endereço não serve; tenta o próximo
            r = classificar_erro(e)
        if tentativas is not None:
            tentativas.append((d, *r))
    return None


def sem_dominio(tentativas: list) -> tuple:
    """(situacao, motivo) de quem não achou endereço: recusa nomeada só se NENHUM endereço respondeu e algum
    recusou (403, muro); o resto é `dominio_nao_verificado`, com o que foi tentado. Pura."""
    recusas = [f"{d} {m}" for d, s, m in tentativas if s == "recusa_de_fonte"]
    if recusas and not any(s == "nao_identifica" for _, s, _ in tentativas):
        return "recusa_de_fonte", "; ".join(recusas)
    return "dominio_nao_verificado", "tentados: " + "; ".join(f"{d} {m}" for d, _, m in tentativas)[:400]


def consultar_municipio(nome, uf, ibge, fontes, buscar, hoje, dormir=lambda s: None, api_cc=None, lacunas=lambda *a, **k: None, web=None) -> dict:
    """{fonte: {situacao, consulta, pistas:[...]}}; nunca levanta. `situacao`: lido, sem_resultado,
    recusa_de_fonte, erro, dominio_nao_verificado."""
    out, dominio, tentativas = {}, None, []
    if {"S16", "S25"} & set(fontes):
        dominio = resolver_dominio(nome, uf, ibge, buscar, tentativas)
    for f in fontes:
        r = {"situacao": None, "consulta": None, "motivo": None, "pistas": []}
        try:
            if f in ("S16", "S25") and not dominio:
                r["situacao"], r["motivo"] = sem_dominio(tentativas)
            else:
                if f in FONTES_WEB:
                    r["consulta"] = consulta_web(f, nome, uf)
                    dados = (web or buscar_web)(r["consulta"])
                    achados = ler_web(dados, nome, f)
                    # Sonda de 27/10/2026: motor suspenso ("too many requests", CAPTCHA) cala; o Bing sozinho ignora site:/OR e devolve
                    # lixo. Sem achado, resposta vazia ou com motor mudo cobre só parte da busca: erro (refaz depois), nunca ausência.
                    if not achados and isinstance(dados, dict) and (dados.get("results") == [] or dados.get("unresponsive_engines")):
                        raise ValueError(f"metabuscador sem cobertura completa, não vale como ausência; motores: {dados.get('unresponsive_engines') or 'nenhum recusou'}")
                elif f == "S18":
                    r["consulta"], achados, r["motivo"] = consultar_qd(buscar, ibge)
                elif f == "S22":
                    r["consulta"], achados, r["motivo"] = consultar_pncp(buscar, ibge, hoje)
                elif f == "S16":
                    r["consulta"] = consulta_wayback(dominio); achados = ler_wayback(buscar(r["consulta"], 60))
                elif f == "S25":
                    api = api_cc or indice_common_crawl(buscar("https://index.commoncrawl.org/collinfo.json", 30))
                    r["consulta"] = consulta_common_crawl(api, dominio)
                    try:
                        corpo = buscar(r["consulta"], 60)
                    except urllib.error.HTTPError as e:
                        if not sem_capturas(e):
                            raise
                        corpo = b""
                    achados = ler_common_crawl(corpo)
                elif f == "S13":
                    r["consulta"] = consulta_lexml(nome); achados = ler_lexml(buscar(r["consulta"], 60), nome)
                else:
                    r["consulta"] = consulta_ckan(nome); achados = ler_ckan(buscar(r["consulta"], 60), nome)
                r["pistas"] = [pista_de(nome, uf, ibge, f, u, t, hoje) for u, t in achados[:TETO_POR_FONTE]]
                r["situacao"] = "lido" if achados else "sem_resultado"
        except Exception as e:  # noqa: BLE001
            r["situacao"], r["motivo"] = classificar_erro(e)
            lacunas(f"{f} · {nome}/{uf}", f'{r["situacao"]}: {r["motivo"]}', canal="fontes abertas", camada=1, uf=uf)
        r["dominio"] = dominio
        out[f] = r
        dormir(PAUSA)
    return out


ESPERAS_5XX = (30, 90)   # segundos; só indisponibilidade (5xx, timeout, conexão recusada), nunca 4xx nem muro


def indisponivel(e: Exception) -> bool:
    """Falha de serviço sobrecarregado, que se espera e se repete; recusa (4xx, muro) nunca. Pura."""
    if isinstance(e, urllib.error.HTTPError):
        return e.code >= 500
    return isinstance(e, (TimeoutError, urllib.error.URLError, ConnectionError)) and not isinstance(e, MuroDeRobo)


def com_espera(buscar, url: str, timeout: int, dormir=time.sleep) -> bytes:
    for espera in (*ESPERAS_5XX, None):
        try:
            return buscar(url, timeout)
        except Exception as e:  # noqa: BLE001
            if espera is None or not indisponivel(e):
                raise
            dormir(espera)


def buscar_pausado(url: str, timeout: int) -> bytes:
    """Uma pausa de PAUSA s antes de TODO pedido (o ritmo por host é de quem chama; ver `_respeitar_ritmo`)."""
    def uma(u, t):
        time.sleep(PAUSA)
        return buscar_uma_vez(u, timeout=t)
    return com_espera(uma, url, timeout)


ERROS_SEGUIDOS = 5   # a fonte cujos erros superam em tantos os acertos fica de fora do resto do run (cada falha custa 2 min de espera)


def saldo_de_erros(n: int, situacao: str) -> int:
    """Erro soma um; qualquer outra situação tira um (nunca abaixo de zero). Pura. Zerar no acerto deixava a fonte
    que erra duas de cada três vezes (Common Crawl, 23/10: 113 erros em 154) nunca chegar ao teto."""
    return n + 1 if situacao == "erro" else max(n - 1, 0)


def fontes_vivas(fontes: list, seguidos: dict) -> list:
    """Fontes ainda consultáveis neste run; o que ficou de fora não é gravado e volta na próxima rodada. Pura."""
    return [f for f in fontes if seguidos.get(f, 0) < ERROS_SEGUIDOS]


def feito_hoje(feitos: dict, cod: str, fontes: list, hoje: str) -> bool:
    m = feitos["municipios"].get(cod, {})
    return all(m.get(f, {}).get("consultado_em") == hoje and m[f].get("situacao") != "erro" for f in fontes)


def selecionar_fila(doc: dict, por_cod: dict, uf, feitos: dict, fontes: list, hoje: str) -> list:
    """`fila` (códigos) ou `municipios` (com `codigo_ibge`, como em municipios_prioritarios.json); `--uf` recorta
    e o que já foi consultado hoje é pulado, para o disparo seguinte retomar. Quem nunca foi lido vem antes de quem
    só precisa ser relido (dia novo): o prazo do run corta a releitura, não a cobertura."""
    fila = doc.get("fila") or [str(m["codigo_ibge"]) for m in doc.get("municipios", [])]
    pendentes = [c for c in fila if c in por_cod and (not uf or por_cod[c]["uf"] == uf) and not feito_hoje(feitos, c, fontes, hoje)]
    return sorted(pendentes, key=lambda c: c in feitos["municipios"])


def rodar(caminho: str, fontes: list, limite: int = None, uf: str = None) -> int:
    doc = ler(caminho.removeprefix("data/"), {}) or {}
    por_cod, _ = referencia_ibge()
    hoje = hoje_editorial().isoformat()
    ufs = [uf] if uf else sorted({r["uf"] for r in por_cod.values()})
    feitos = {"municipios": {}}
    for u in ufs:
        feitos["municipios"].update(ler(f"{PASTA}/{u}.json", {}).get("municipios", {}))
    fila = selecionar_fila(doc, por_cod, uf, feitos, fontes, hoje)
    pistas, lidos, tocadas, seguidos = [], 0, set(), {}
    try:
        for cod in fila[:limite] if limite else fila:
            ref = por_cod[cod]
            vivas = fontes_vivas(fontes, seguidos)
            if not vivas:
                print(f"[fontes] todas fora do ar depois de {ERROS_SEGUIDOS} erros seguidos; encerrando o run.")
                break
            res = consultar_municipio(ref["nome"], ref["uf"], cod, vivas, buscar_pausado, hoje, lacunas=registrar_lacuna)
            for f, r in res.items():
                seguidos[f] = saldo_de_erros(seguidos.get(f, 0), r["situacao"])
                pistas.extend(r.pop("pistas"))
                feitos["municipios"].setdefault(cod, {})[f] = {"consultado_em": hoje, **r}
            lidos += 1
            tocadas.add(ref["uf"])
    except KeyboardInterrupt:
        print(f"[prazo] interrompido depois de {lidos} município(s); gravando o que foi lido.")
    balanco = gravar_lote(pistas, origem="descoberta", ler_fn=ler, gravar_fn=gravar)
    for u in tocadas:
        gravar(f"{PASTA}/{u}.json", {"gerado_em": hoje, "municipios": {c: m for c, m in feitos["municipios"].items() if por_cod[c]["uf"] == u}})
    por = {}
    for m in feitos["municipios"].values():
        for f, r in m.items():
            if f in fontes and r.get("consultado_em") == hoje:
                por.setdefault(f, {}).setdefault(r["situacao"], 0)
                por[f][r["situacao"]] += 1
    print(f"Fontes abertas: {lidos} município(s); {por}; porta única: {balanco.get('gravadas')} gravada(s), "
          f"{balanco.get('recusadas')} recusada(s) {balanco.get('motivos') or ''}")
    return 0


# ---- autoteste (offline; não escreve em data/) ---------------------------------------------------
def autoteste() -> int:
    import pathlib
    wb = json.dumps([["original", "timestamp", "mimetype"],
                     ["http://x.gov.br/docs/PLANCON-2025.pdf", "20250101000000", "application/pdf"],
                     ["http://x.gov.br/noticias", "20250101000000", "text/html"]]).encode()
    cc = (json.dumps({"url": "https://x.gov.br/a/plano-de-contingencia.pdf"}) + "\n"
          + json.dumps({"url": "https://x.gov.br/a/plano-de-contingencia.pdf"}) + "\n").encode()
    sru = ('<searchRetrieveResponse xmlns="http://www.loc.gov/zing/srw/"><records><record><recordData>'
           '<dc xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Decreto aprova o Plano de Contingência de Alfa</dc:title>'
           '<dc:identifier>urn:lex:br;alfa;municipal:decreto:2025;1</dc:identifier></dc></recordData></record></records>'
           '</searchRetrieveResponse>').encode()
    ckan = json.dumps({"success": True, "result": {"results": [
        {"name": "plancon-alfa", "title": "PLANCON de Alfa", "notes": ""},
        {"name": "outro", "title": "Orçamento de Alfa", "notes": ""}]}}).encode()

    def falso(respostas):
        def b(url, timeout):
            for chave, corpo in respostas.items():
                if chave in url:
                    if isinstance(corpo, Exception):
                        raise corpo
                    return corpo
            raise OSError("sem rota: " + url)
        return b

    home = "<html>Prefeitura Municipal de Alfa</html>".encode()
    base = {"web.archive.org": wb, "collinfo": json.dumps([{"id": "CC-1", "cdx-api": "https://i/c1"}, {"id": "CC-2", "cdx-api": "https://i/c2"}]).encode(),
            "i/c2": cc, "lexml": sru, "dados.gov.br": ckan, "alfa.xx.gov.br": home}   # a home por último: as consultas citam o domínio
    um = lambda fontes, r=base: consultar_municipio("Alfa", "XX", "9999999", fontes, falso(r), "2026-10-22", lacunas=lambda *a, **k: lac.append(a))
    lac = []
    web_ok = {"results": [
        {"url": "https://pt.scribd.com/document/1/PLANCON-de-Alfa", "title": "PLANCON de Alfa - Defesa Civil", "content": "Plano de contingência do município de Alfa"},
        {"url": "https://issuu.com/x/docs/outro", "title": "Revista de Beta", "content": "plano de contingência de Beta"},
        {"url": "https://alfa.xx.gov.br/pmrr.pdf", "title": "PMRR de Alfa", "content": "plano municipal de redução de riscos; plano de contingência de Alfa"},
        {"url": "https://blog.com/alfa", "title": "Alfa", "content": "plano de contingência e saneamento básico de Alfa"},
        {"url": "https://www.mpxx.mp.br/recomendacao-14", "title": "Recomendação ao município de Alfa", "content": "elaborar o plano de contingência de Alfa"},
        {"url": "https://www.famurs.com.br/diario/decreto-7", "title": "Decreto de Alfa aprova o plano de contingência", "content": "Alfa institui o plano de contingência"},
        {"url": "https://repositorio.ufxx.edu.br/tcc/3", "title": "TCC: plano de contingência de Alfa", "content": "monografia sobre Alfa"},
        {"url": "https://defesacivil.xx.gov.br/crepdec-2", "title": "CREPDEC reúne Alfa", "content": "plano de contingência de Alfa"},
        {"url": "https://defesacivil.xx.gov.br/operacao-chuvas", "title": "Operação Chuvas: Alfa adere", "content": "adesão de Alfa; plano de contingência"},
        {"url": "https://tjxx.jus.br/acp/1", "title": "Ação civil pública contra Alfa", "content": "obriga Alfa a elaborar plano de contingência"},
        {"url": "https://saude.xx.gov.br/cib/res-12.pdf", "title": "Resolução CIB: plano de contingência da dengue de Alfa", "content": ""},
        {"url": "https://transferegov.sistema.gov.br/p/9", "title": "Proposta de Alfa: plano de trabalho", "content": "anexo: plano de contingência de Alfa"}]}
    web = lambda r=web_ok: (lambda q: r if not isinstance(r, Exception) else (_ for _ in ()).throw(r))
    qd_ok = {"gazettes": [{"url": "https://q/a.pdf", "date": "2026-03-01", "excerpts": ["Aprova o  Plano de Contingência de Alfa"]},
                          {"url": "https://q/b.pdf", "date": "2026-03-02", "excerpts": ["Orçamento"]},
                          {"url": "", "date": "2026-03-03", "excerpts": ["Plano de Contingência"]}]}
    pc = lambda obj, seq, esfera="M": {"objetoCompra": obj, "anoCompra": 2026, "sequencialCompra": seq, "orgaoEntidade": {"cnpj": "1" if seq else None, "esferaId": esfera}}
    pn = lambda n, itens, tot=1: json.dumps({"data": itens, "totalPaginas": tot, "numeroPagina": n}).encode()
    todas = um(["S16", "S25", "S13", "S29"])
    fonte = pathlib.Path(__file__).read_text(encoding="utf-8")
    escrita_proibida = re.compile(r"gravar\(\s*['\"](estados|saude_uf|municipios|indice|monitor_saude)\.json")
    testes = {
        "Wayback: só o endereço com plano vira cópia arquivada": lambda: ler_wayback(wb) == [("https://web.archive.org/web/20250101000000/http://x.gov.br/docs/PLANCON-2025.pdf", "Cópia arquivada: http://x.gov.br/docs/PLANCON-2025.pdf")],
        "Wayback: corpo que não é CDX levanta, não vira ausência": lambda: _levanta(ler_wayback, b'[["a","b"]]'),
        "Common Crawl: usa o rastreio mais novo e não repete URL": lambda: indice_common_crawl(base["collinfo"]) == "https://i/c2" and len(ler_common_crawl(cc)) == 1,
        "Common Crawl: 404 'No Captures found' é sem_resultado; outro 404 é erro": lambda: (
            um(["S25"], {**base, "i/c2": urllib.error.HTTPError("u", 404, "x", {}, io.BytesIO(b'{"message":"No Captures found for: a/*"}'))})["S25"]["situacao"] == "sem_resultado"
            and um(["S25"], {**base, "i/c2": urllib.error.HTTPError("u", 404, "x", {}, io.BytesIO(b"nao existe"))})["S25"]["situacao"] == "erro"),
        "LexML: exige o plano e o município no registro": lambda: len(ler_lexml(sru, "Alfa")) == 1 and ler_lexml(sru, "Beta") == [],
        "LexML: XML que não é SRU levanta": lambda: _levanta(lambda c: ler_lexml(c, "Alfa"), b"<html/>"),
        "CKAN: só o conjunto que cita plano e município": lambda: len(ler_ckan(ckan, "Alfa")) == 1,
        "as quatro fontes de um município que responde viram pista": lambda: [todas[f]["situacao"] for f in todas] == ["lido"] * 4,
        "pista no esquema e com as travas de campo": lambda: all(p["documento_oficial_confirmado"] is None and p["promovivel"] is False and p["origem"] == "descoberta" and p["ibge"] == "9999999" for r in todas.values() for p in r["pistas"]),
        "403 é recusa de fonte; timeout é erro; nenhum vira sem_resultado": lambda: (
            um(["S13"], {**base, "lexml": urllib.error.HTTPError("u", 403, "x", {}, None)})["S13"]["situacao"] == "recusa_de_fonte"
            and um(["S13"], {**base, "lexml": TimeoutError("t")})["S13"]["situacao"] == "erro"),
        "resposta sem achado registra a consulta (sem_resultado)": lambda: (lambda r: r["situacao"] == "sem_resultado" and r["consulta"].startswith("https://dados.gov.br"))(um(["S29"], {**base, "dados.gov.br": json.dumps({"success": True, "result": {"results": []}}).encode()})["S29"]),
        "domínio que não se identifica como prefeitura: busca não feita": lambda: um(["S16"], {**base, "alfa.xx.gov.br": b"<html>outra coisa</html>"})["S16"]["situacao"] == "dominio_nao_verificado",
        "domínio que recusa (403) sem ninguém responder é recusa nomeada, não 'não verificado'": lambda: (
            um(["S16"], {**base, "alfa.xx.gov.br": urllib.error.HTTPError("u", 403, "x", {}, None)})["S16"]["situacao"] == "recusa_de_fonte"
            and um(["S16"], {"//www.alfa.xx.gov.br": b"<html>outra</html>", **{k: v for k, v in base.items() if k != "alfa.xx.gov.br"}, "//alfa.xx.gov.br": urllib.error.HTTPError("u", 403, "x", {}, None)})["S16"]["situacao"] == "dominio_nao_verificado"
            and "alfa.xx.gov.br" in um(["S16"], {**base, "alfa.xx.gov.br": OSError("dns")})["S16"]["motivo"]),
        "S27: só hospedagem que cita o município e o plano; endereço de outro município ou fora da lista não entra": lambda: ler_web(web_ok, "Alfa", "S27") == [("https://pt.scribd.com/document/1/PLANCON-de-Alfa", "PLANCON de Alfa - Defesa Civil")] and ler_web(web_ok, "Beta", "S27") == [("https://issuu.com/x/docs/outro", "Revista de Beta")],
        "S20, S21, S23, S31: cada fonte aceita só o seu endereço e o seu termo; o resto (hospedagem, blog, outra fonte) fica de fora": lambda: (
            [u for u, _ in ler_web(web_ok, "Alfa", "S20")] == ["https://www.mpxx.mp.br/recomendacao-14"]
            and [u for u, _ in ler_web(web_ok, "Alfa", "S21")] == ["https://tjxx.jus.br/acp/1"]
            and [u for u, _ in ler_web(web_ok, "Alfa", "S23")] == ["https://saude.xx.gov.br/cib/res-12.pdf"]
            and [u for u, _ in ler_web(web_ok, "Alfa", "S31")] == ["https://transferegov.sistema.gov.br/p/9"]),
        "S17, S19, S26, S30: cada fonte aceita só o seu endereço e o seu termo": lambda: (
            [u for u, _ in ler_web(web_ok, "Alfa", "S17")] == ["https://defesacivil.xx.gov.br/crepdec-2"]
            and [u for u, _ in ler_web(web_ok, "Alfa", "S19")] == ["https://www.famurs.com.br/diario/decreto-7"]
            and [u for u, _ in ler_web(web_ok, "Alfa", "S26")] == ["https://repositorio.ufxx.edu.br/tcc/3"]
            and [u for u, _ in ler_web(web_ok, "Alfa", "S30")] == ["https://defesacivil.xx.gov.br/operacao-chuvas"]),
        "S24: só endereço institucional com termo conexo e plano; blog e hospedagem ficam de fora": lambda: ler_web(web_ok, "Alfa", "S24") == [("https://alfa.xx.gov.br/pmrr.pdf", "PMRR de Alfa")],
        "S27 e S24: consulta registrada e pista com as travas de campo": lambda: (lambda r: all(r[f]["situacao"] == "lido" and r[f]["consulta"] and r[f]["pistas"][0]["promovivel"] is False and r[f]["pistas"][0]["documento_oficial_confirmado"] is None for f in r))(consultar_municipio("Alfa", "XX", "9999999", ["S27", "S24"], falso({}), "2026-10-26", web=web())),
        "S27: resultado bruto vazio é erro (motor barrando), nunca sem_resultado; filtrado a zero é sem_resultado": lambda: (
            consultar_municipio("Alfa", "XX", "9999999", ["S27"], falso({}), "d", web=web({"results": [], "unresponsive_engines": [["bing", "Suspended: too many requests"]]}))["S27"]["motivo"].endswith("[['bing', 'Suspended: too many requests']]")
            and consultar_municipio("Alfa", "XX", "9999999", ["S27"], falso({}), "d", web=web({"results": [{"url": "https://x.com/a", "title": "t"}], "unresponsive_engines": [["brave", "Suspended: access denied"]]}))["S27"]["situacao"] == "erro"
            and consultar_municipio("Gama", "XX", "9999999", ["S27"], falso({}), "d", web=web())["S27"]["situacao"] == "sem_resultado"),
        "S27: corpo que não é resposta do metabuscador e 429 são erro/recusa, não ausência": lambda: (
            consultar_municipio("Alfa", "XX", "9999999", ["S27"], falso({}), "d", web=web({"x": 1}))["S27"]["situacao"] == "erro"
            and consultar_municipio("Alfa", "XX", "9999999", ["S27"], falso({}), "d", web=web(urllib.error.HTTPError("u", 429, "x", {}, None)))["S27"]["situacao"] == "recusa_de_fonte"),
        "S18: só a edição cujo excerto cita o plano; sem URL ou sem excerto não entra; corpo alheio levanta": lambda: (
            ler_qd(qd_ok) == [("https://q/a.pdf", "edição de 2026-03-01: Aprova o Plano de Contingência de Alfa")]
            and ler_qd({"gazettes": []}) == [] and _levanta(ler_qd, {"results": []})),
        "S18: um território por chamada e o termo só na consulta de achado": lambda: (
            parametros_qd("123")["territory_ids"] == "0000123" and "," not in parametros_qd("123")["territory_ids"]
            and "querystring" in parametros_qd("123") and "querystring" not in parametros_qd("123", cobertura=True)),
        "S18: achado vira pista com as travas de campo e a consulta registrada": lambda: (lambda r: r["situacao"] == "lido" and r["consulta"].startswith("https://") and r["pistas"][0]["promovivel"] is False and r["pistas"][0]["documento_oficial_confirmado"] is None)(
            um(["S18"], {**base, "gazettes": json.dumps(qd_ok).encode()})["S18"]),
        "S18: sem excerto, município com diários é sem_resultado com o total; sem diário no acervo diz que é falta de acervo": lambda: (
            lambda a, b: a["situacao"] == b["situacao"] == "sem_resultado" and "3 edição" in a["motivo"] and "sem diário no acervo" in b["motivo"])(
            um(["S18"], {**base, "size=1": b'{"total_gazettes": 3, "gazettes": []}', "gazettes": b'{"gazettes": []}'})["S18"],
            um(["S18"], {**base, "size=1": b'{"total_gazettes": 0, "gazettes": []}', "gazettes": b'{"gazettes": []}'})["S18"]),
        "S18: porta com falha de conexão passa à seguinte; todas fora é erro; 403 é recusa e não tenta outra porta": lambda: (
            (lambda vistas: buscar_qd(lambda u, t: (vistas.append(u), (_ for _ in ()).throw(OSError("tls")) if len(vistas) == 1 else b'{"gazettes": []}')[1], {"territory_ids": "1"}) == {"gazettes": []} and len(vistas) == 2)([])
            and um(["S18"], {**base, "gazettes": OSError("tls")})["S18"]["situacao"] == "erro"
            and um(["S18"], {**base, "gazettes": urllib.error.HTTPError("u", 403, "x", {}, None)})["S18"]["situacao"] == "recusa_de_fonte"),
        "S22: só contratação municipal cujo objeto cita o plano; estadual, sem identificador e corpo alheio ficam de fora": lambda: (
            ler_pncp(pn(1, [pc("Elaboração do Plano de Contingência", 7), pc("Compra de papel", 8), pc("PLANCON", 9, "E"), pc("PMRR", None)]))
            == ([("https://pncp.gov.br/app/editais/1/2026/7", "contratação de 2026: Elaboração do Plano de Contingência")], 4, 1)
            and ler_pncp(b"") == ([], 0, 0) and _levanta(ler_pncp, b'{"x": 1}')),
        "S22: um município, uma modalidade e um ano por chamada, janela até hoje": lambda: (lambda p: p["codigoMunicipioIbge"] == "0000123" and p["dataInicial"] == "20260101" and p["dataFinal"] == "20261022" and parametros_pncp("1", 8, 2024, "2026-10-22", 1)["dataFinal"] == "20241231")(parametros_pncp("123", 8, 2026, "2026-10-22", 1)),
        "S22: pagina até o fim, repete o achado sem duplicar; achado vira pista com as travas e a consulta": lambda: (lambda r: r["situacao"] == "lido" and len(r["pistas"]) == 1 and r["consulta"].startswith(PNCP) and r["pistas"][0]["promovivel"] is False and r["pistas"][0]["documento_oficial_confirmado"] is None)(
            um(["S22"], {**base, "pagina=2": pn(2, [], 2), "pncp.gov.br": pn(1, [pc("Plano de Contingência", 7)], 2)})["S22"]),
        "S22: lido tudo sem achado é sem_resultado com a contagem; 204 é zero; teto de páginas sem achado é erro": lambda: (
            lambda a, b: a["situacao"] == "sem_resultado" and "32 contratação" in a["motivo"] and b["situacao"] == "erro" and "incompleta" in b["motivo"])(
            um(["S22"], {**base, "pncp.gov.br": pn(1, [pc("Compra de papel", 8)])})["S22"], um(["S22"], {**base, "pncp.gov.br": pn(1, [], 99)})["S22"])
        and um(["S22"], {**base, "pncp.gov.br": b""})["S22"]["situacao"] == "sem_resultado",
        "S22: páginas de 500; 400 na primeira chamada volta a 50 para o resto, sem repetir o 500": lambda: (
            lambda v: consultar_pncp(lambda u, t: (v.append(u), (_ for _ in ()).throw(urllib.error.HTTPError(u, 400, "x", {}, None)) if "tamanhoPagina=500" in u else pn(1, [pc("Plano de Contingência", 7)]))[1], "1", "2026-10-22")[1] != []
            and "tamanhoPagina=500" in v[0] and sum("tamanhoPagina=500" in u for u in v) == 1 and "tamanhoPagina=50&" in v[1] + "&")([]),
        "S22: 403 é recusa; falha de conexão é erro": lambda: (
            um(["S22"], {**base, "pncp.gov.br": urllib.error.HTTPError("u", 403, "x", {}, None)})["S22"]["situacao"] == "recusa_de_fonte"
            and um(["S22"], {**base, "pncp.gov.br": OSError("tls")})["S22"]["situacao"] == "erro"),
        "trava estrutural: o fonte não grava nos arquivos do índice": lambda: not escrita_proibida.search(fonte),
        "recusa e erro viram lacuna declarada": lambda: (lac.clear(), um(["S13"], {**base, "lexml": urllib.error.HTTPError("u", 429, "x", {}, None)}), len(lac) == 1)[2],
        "401 e 451 também são recusa": lambda: all(classificar_erro(urllib.error.HTTPError("u", c, "x", {}, None))[0] == "recusa_de_fonte" for c in (401, 429, 451)),
        "muro de robô é recusa": lambda: classificar_erro(MuroDeRobo("u", "imperva"))[0] == "recusa_de_fonte",
        "nome só como palavra inteira": lambda: cita("Plano de Alfa", "Alfa") and not cita("Plano de Alfaville", "Alfa"),
        "5xx espera e repete; 4xx e muro não": lambda: _espera_ok(),
        "fila: lê `municipios`, recorta a UF e retoma o que não foi consultado hoje": lambda: (lambda doc, ref, fe: (
            selecionar_fila(doc, ref, None, fe, ["S16"], "d") == ["1", "2", "3"]
            and selecionar_fila(doc, ref, "AC", fe, ["S16"], "d") == ["1", "2"]
            and selecionar_fila(doc, ref, "AC", fe, ["S16", "S25"], "d") == ["1", "2"]
            and selecionar_fila({"fila": ["1", "9"]}, ref, None, fe, ["S16"], "d") == ["1"]))(
            {"municipios": [{"codigo_ibge": 1}, {"codigo_ibge": 2}, {"codigo_ibge": 3}]},
            {"1": {"uf": "AC"}, "2": {"uf": "AC"}, "3": {"uf": "AL"}}, {"municipios": {}}) and
            selecionar_fila({"fila": ["1", "2"]}, {"1": {"uf": "AC"}, "2": {"uf": "AC"}}, None,
                            {"municipios": {"1": {"S16": {"consultado_em": "d"}}}}, ["S16"], "d") == ["2"],
        "fila: quem nunca foi lido vem antes de quem só precisa ser relido": lambda: selecionar_fila(
            {"fila": ["1", "2", "3"]}, {c: {"uf": "AC"} for c in "123"}, "AC",
            {"municipios": {"1": {"S16": {"consultado_em": "ontem"}}, "2": {"S16": {"consultado_em": "ontem"}}}}, ["S16"], "d") == ["3", "1", "2"],
        "disjuntor: fonte com erros seguidos sai do run, as outras seguem": lambda: fontes_vivas(["S16", "S25"], {"S25": ERROS_SEGUIDOS}) == ["S16"] and fontes_vivas(["S16", "S25"], {"S25": ERROS_SEGUIDOS - 1}) == ["S16", "S25"],
        "disjuntor por saldo: dois erros em três chegam ao teto, um em dois não": lambda: (lambda cam: max(cam("eea" * 5)) >= ERROS_SEGUIDOS and max(cam("ea" * 10)) == 1)(lambda seq: __import__("itertools").accumulate(seq, lambda n, c: saldo_de_erros(n, "erro" if c == "e" else "lido"), initial=0)),
        "teto por fonte": lambda: len(ler_common_crawl(("\n".join(json.dumps({"url": f"https://x/plancon{i}.pdf"}) for i in range(9))).encode())) == 9 and TETO_POR_FONTE == 5,
    }
    return rodar_autoteste(testes)


def _espera_ok() -> bool:
    n = {"c": 0}
    def instavel(u, t):
        n["c"] += 1
        if n["c"] < 3:
            raise urllib.error.HTTPError(u, 503, "x", {}, None)
        return b"ok"
    def recusa(u, t):
        n["c"] += 1
        raise urllib.error.HTTPError(u, 403, "x", {}, None)
    esperas = []
    ok = com_espera(instavel, "u", 1, dormir=esperas.append) == b"ok" and esperas == [30, 90]
    n["c"] = 0
    try:
        com_espera(recusa, "u", 1, dormir=esperas.append)
    except urllib.error.HTTPError:
        return ok and n["c"] == 1
    return False


def _levanta(fn, *a) -> bool:
    try:
        fn(*a)
    except Exception:  # noqa: BLE001
        return True
    return False


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    if "--alvos" not in sys.argv:
        print("uso: --alvos <arquivo com fila> [--fontes S16,S25,S13,S29,S27,S24,S18,S22,S20,S21,S23,S31] [--limite N] [--uf SP]")
        return 1
    arg = lambda k: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else None
    fontes = [f.strip().upper() for f in (arg("--fontes") or "S13,S16,S25,S29").split(",") if f.strip()]
    return rodar(arg("--alvos"), fontes, int(arg("--limite")) if arg("--limite") else None, (arg("--uf") or "").upper() or None)


if __name__ == "__main__":
    sys.exit(main())
