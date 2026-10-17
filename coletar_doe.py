#!/usr/bin/env python3
"""
coletar_doe.py
==============
Diários Oficiais dos ESTADOS (27 DOEs): homologações estaduais de decretos
municipais → `data/atos_resposta.json` (resposta, peso zero, campo
`decreto_estadual_homologacao`); atos estaduais sobre o ciclo → `data/pistas_doe.json`
(fila de pista: promover a registro é humano, §3.2). Confere nível "estadual" no
livro de fontes consultadas para os municípios da UF quando o DOE da UF foi lido
com sucesso no período.

Cobertura (§15, "a verificar por UF"): `data/fontes_doe.json` declara, por UF,
`{"adaptador": ..., "url": ..., "status": ...}`. Adaptadores: `apifront` (plataforma comum,
busca), `dodf` (DF, busca própria), `busca_to`/`busca_ac` (busca que aponta edições) e
`edicao_<uf>`/`edicao_apifront` (sem busca: a edição em PDF por data — CE, PB, AM, MS, PI) e `busca_sp`
(API própria do DOE-SP; 16/10/2026). UF sem adaptador →
`sem adaptador de busca`, lacuna declarada com o motivo medido (nunca inferida).

USO
  python coletar_doe.py --autoteste
  python coletar_doe.py --regiao NE            # lote por região (§13: NE, N, CO, SE, S)
  python coletar_doe.py --uf SC --desde 2026-06-29
"""
import json, pathlib, re, sys, time, urllib.parse
from datetime import date, timedelta
import funil
# 16/10/2026: o endereço da edição por data é o do canal 2 (saúde) — um padrão por UF, conferido
# lá, lido aqui. Dois padrões para o mesmo PDF divergiriam na primeira mudança de endereço.
from coletar_edicoes_doe import (PADROES as PADROES_CANAL2, MINIMO_BYTES_DE_EDICAO,
                                 datas_do_periodo, endereco_da_data)
from coletores_base import (carimbar_atos, buscar, enviar, preservar_evidencia, preservar_texto_integral, log_busca, registrar_lacuna,
                            marcar_fonte_consultada, marcar_fato_municipal, referencia_ibge,
                            abrir_lote_log, fechar_lote_log, abrir_lote_livro, fechar_lote_livro,
                            ler, gravar, rodar_autoteste, eh_suspensao_defeso, hoje_editorial)
from scripts.pistas import sincronizar as sincronizar_pistas  # 05/10/2026: a fila tem UMA porta

REGIOES = {"N": "AC AM AP PA RO RR TO", "NE": "AL BA CE MA PB PE PI RN SE", "CO": "DF GO MS MT",
           "SE": "ES MG RJ SP", "S": "PR RS SC"}
# 26/09/2026 (§231): o primeiro termo era "homologa a situação de emergência", com um artigo que o
# ato estadual real NÃO tem — medido no DOE-PR de 15/09/2026: "Homologa situação de emergência no
# Município de Palmeira". Termo que não pode casar é pior do que termo ausente: produz "nada
# localizado" com aparência de busca feita. Os dois primeiros abaixo são os que a plataforma
# indexa com resultado, medidos na janela 29/06→26/09/2026 nas seis UFs.
TERMOS = ["situação de emergência", "estado de calamidade pública",
          "homologa situação de emergência", "homologa o decreto municipal",
          "plano de contingência El Niño", "plano de contingência"]
# Termos usados na busca da plataforma comum: os dois primeiros bastam para o que interessa e
# custam duas consultas por UF em vez de seis. "situação de emergência" já casa as homologações
# com e sem número de decreto.
TERMOS_APIFRONT = ("situação de emergência", "estado de calamidade pública")
# 24/09/2026 (§194): host migrado — o antigo responde 302 a cada chamada desde 21/09 (§ do coletor
# municipal). E fica registrado o que foi MEDIDO em 24/09: o Querido Diário **não indexa diário
# ESTADUAL**. Consultados os territórios de SE, ES, SP, RJ e MG (códigos IBGE de dois dígitos), todos
# devolvem total_gazettes=0, enquanto Aracaju devolve 4.582. Ou seja: o adaptador "querido_diario"
# desta rota nunca poderá funcionar, e confirmar um DOE exige adaptador DIRETO, sítio a sítio.
# Registrado para ninguém repetir a tentativa achando que é questão de configuração.
QD_API = "https://api.queridodiario.org.br/gazettes?{params}"
PADRAO_HOMOLOGA = re.compile(r"homologa\s+(?:o\s+)?(?:decreto\s+(?:municipal\s+)?n[ºo°\.]?\s*([\d\.\/-]+))?[^.]{0,160}?munic[íi]pio de ([^,;\.\-–]+?)(?:\s*[-–]\s*([A-Z]{2}))?[\.,;]", re.I)


# §231 (26/09/2026): as seis UFs cujo diário estadual roda a plataforma comum, com o host lido do
# próprio sítio e as três rotas testadas contra produção. Nenhum host foi suposto: cada um respondeu
# `/apifront/portal/edicoes/edicoes_from_data/2026-09-24.json` com JSON válido.
HOSTS_APIFRONT = {
    "AP": "https://diofe.portal.ap.gov.br",
    "ES": "https://ioes.dio.es.gov.br",
    "GO": "https://diariooficial.abc.go.gov.br",
    "MT": "https://www.iomat.mt.gov.br",
    "PR": "https://www.dioe.pr.gov.br",
}
# O Amazonas roda a MESMA plataforma — `/apifront/portal/edicoes/...` e `/portal/edicoes/download/`
# respondem — mas a rota de BUSCA devolve 404: a busca dele é outro aplicativo. Medido em
# 26/09/2026, com o cliente do projeto, na primeira varredura real.
#
# Por isso o AM fica FORA de HOSTS_APIFRONT, e não registrado como `apifront` para falhar todo dia:
# uma UF cujo adaptador não pode funcionar declarada como se pudesse produz lacuna diária falsa —
# com a cadência de duas horas, doze por dia sobre um fato que não muda. O caminho para o AM existe
# e é outro: varrer as edições por data pela rota (a) e ler o PDF de cada uma pela rota (c), o que
# custa download de edição inteira em vez de busca por termo. Fica declarado como trabalho a fazer,
# e não como fonte bloqueada — a distinção é a do §231.
# =============================================================================================
# DF — o DODF tem API de busca PRÓPRIA, e ela é a rota que o próprio JS do sítio chama
# =============================================================================================
# Medido em 01/10/2026: a página de busca (`/dodf/materia/busca`) não traz resultado no HTML — o
# contador nasce em zero e é preenchido por `$.post("/dodf/materia/listar", ...)`, lido em
# `/js/modules/dodf/controllers/MateriaController.js`. Os nomes dos campos e os valores aceitos
# são os do formulário e da validação da própria rota: `tpBusca` só aceita `exata` ou `contexto`
# (a primeira tentativa, com "contextual", foi recusada com `notInArray`), e as datas vão em ISO,
# porque os campos são `type="date"`. Nada aqui foi suposto.
DODF_LISTAR = "https://www.dodf.df.gov.br/dodf/materia/listar"
# O endereço da matéria é o que o JS monta, letra por letra (`linkMateria`).
DODF_MATERIA = ("https://www.dodf.df.gov.br/dodf/materia/visualizar"
                "?co_data={co}&p={slug}&busca=exata")
TETO_PAGINAS_DODF = 20

# =============================================================================================
# TO — a busca do DOE-TO entrega, no HTML, as EDIÇÕES que contêm o termo
# =============================================================================================
# Medido em 01/10/2026: `GET /busca?por=texto&texto=…&data-inicial=…&data-final=…` (datas em ISO,
# campos `type="date"`) devolve a tabela "Resultados da busca" com número da edição, data e o link
# de download do PDF. Ela não devolve o trecho — e é exatamente por isso que o adaptador desce ao
# PDF **só das edições que a busca apontou**: é a diferença entre ler 2 edições e ler as 65 da
# janela.
BUSCA_TO = "https://diariooficial.to.gov.br/busca"
# AC (14/10/2026, run 38576857903): a busca é um POST (`palavra`, `ano_palavra`) que devolve, da
# mais nova para a mais antiga, dez edições por página com data, número e PDF. Lê-se a primeira
# página: a rodada é diária e o diário publica bem menos de dez edições por dia com cada termo.
# (O PI também busca por POST, mas o índice dele para em 21/05/2021 — medido no mesmo dia.)
BUSCA_AC = "https://diario.ac.gov.br/"
TETO_EDICOES_TO = 12

APIFRONT_SEM_BUSCA = {
    "AM": {"url": "https://diario.imprensaoficial.am.gov.br",
           "medido": "26/09/2026: /apifront e /portal/edicoes/download respondem; "
                     "/busca/busca/buscar devolve HTTP 404 (a busca é outro aplicativo)",
           "caminho": "edições por data (rota a) + leitura do PDF da edição (rota c) — adaptador "
                      "`edicao_apifront`, 16/10/2026"},
}


def fontes_doe_padrao():
    ufs = {uf: {"adaptador": None, "url": None, "status": "a_verificar", "ultima_tentativa": None}
           for r in REGIOES.values() for uf in r.split()}
    for uf, base in HOSTS_APIFRONT.items():
        ufs[uf] = {"adaptador": "apifront", "url": base, "status": "a_verificar", "ultima_tentativa": None}
    return {"_governanca": "Cobertura dos 27 DOEs (v2.2.4, §4.2). 'a_verificar' = adaptador não confirmado; "
                           "a Action registra o resultado da tentativa. Nunca inferir cobertura. "
                           "§231: seis UFs usam o adaptador 'apifront' (plataforma comum, rotas medidas).",
            "ufs": ufs}


def parse_querido_diario(dados: dict) -> list:
    """Normaliza a resposta da API do Querido Diário em itens {data, url, trechos, territorio}."""
    out = []
    for g in (dados or {}).get("gazettes", []):
        out.append({"data": g.get("date", ""), "url": g.get("url") or g.get("txt_url", ""),
                    "trechos": [t for t in g.get("excerpts", []) if t], "territorio": str(g.get("territory_id", ""))})
    return out


def extrair_homologacoes(itens: list, uf: str) -> list:
    """Homologações com município identificável; número do decreto pode faltar (vai como pista)."""
    saida = []
    for it in itens:
        for tr in it["trechos"]:
            # §231: as três formas medidas, e não só a que o fixture do Querido Diário usava.
            for hm in homologacoes_no_texto(tr):
                saida.append({"municipio": hm["municipio"], "uf": uf.upper(),
                              "decreto_municipal": hm["decreto_municipal"],
                              "decreto_estadual": hm.get("decreto_estadual"), "data": it["data"],
                              "url": it["url"], "trecho": hm["trecho"],
                              **({"pagina": it["pagina"], "paginas": it["paginas"]}
                                 if it.get("pagina") else {})})
    return saida


# ── Plataforma comum a seis diários oficiais ESTADUAIS (§231, 26/09/2026) ──────────────
# AP, AM, ES, GO, MT e PR rodam o mesmo sistema (CakePHP, tema por estado) com três rotas
# públicas sem autenticação. Tudo abaixo foi MEDIDO contra produção em 26/09/2026, não suposto:
#
#   (a) /apifront/portal/edicoes/edicoes_from_data/AAAA-MM-DD.json
#       → {"erro": false, "itens": [{"id", "data", "numero", "paginas", "tipo_edicao_nome", ...}]}
#       e, quando não há edição no dia, {"erro": true, "msg": "Edição não existente!", "itens": []}
#       — que é resposta CORRETA, não falha.
#   (b) /busca/busca/buscar/query/<pagina>/di:AAAA-MM-DD/df:AAAA-MM-DD/?1=1&q="termo"
#       → resposta Elasticsearch crua, com `hits.total` e, por acerto,
#       `_source.conteudo` = TEXTO INTEGRAL da página que casou, mais data, pagina, paginas,
#       pdf_id, diario_id, tipo_edicao.
#   (c) /portal/edicoes/download/<diario_id> → o PDF da edição inteira.
#
# DUAS MEDIÇÕES QUE EVITAM ERRO DE LEITURA, e que custaram a primeira sonda:
#   · a página da busca é indexada em ZERO e entrega 10 por vez. Pedir `/query/1/` numa UF com
#     menos de 10 acertos devolve `hits.total = 7` e `hits.hits = []` — total declarado, lista
#     vazia. Foi exatamente o que fez GO, ES, AP e MT parecerem sem resultado na primeira tentativa.
#   · o identificador do download é `diario_id`, NÃO `pdf_id`: `pdf_id` devolve 28 kB de HTML e
#     `diario_id` devolve o PDF de verdade (10,9 MB, 104 páginas, no caso testado).
BUSCA_APIFRONT = "{base}/busca/busca/buscar/query/{pagina}/di:{de}/df:{ate}/?1=1&q={termo}"
PDF_APIFRONT = "{base}/portal/edicoes/download/{diario_id}"
TETO_PAGINA_APIFRONT = 10      # medido: a rota entrega 10 acertos por página
TETO_PAGINAS_APIFRONT = 60     # guarda: 600 acertos por termo é muito mais do que qualquer janela real
RITMO_APIFRONT_S = 2.0


class FormatoDaBuscaMudou(Exception):
    """A resposta da busca perdeu a estrutura esperada.

    LEVANTA em vez de devolver lista vazia, pela lição do §210: um guarda que confunde "mudou o
    formato" com "não há resultado" transforma 132 achados reais em zero, calado."""


def parse_busca_apifront(bruto: bytes) -> tuple:
    """(total_declarado, [acerto]) da resposta crua. Função pura.

    Cada acerto traz o texto INTEGRAL da página — não um excerto —, e é isso que permite procurar
    a homologação nele sem baixar um PDF de dez megabytes por acerto."""
    try:
        o = json.loads(bruto.decode("utf-8", "replace"))
    except json.JSONDecodeError as e:
        raise FormatoDaBuscaMudou(f"resposta não é JSON: {e}") from e
    if not isinstance(o, dict) or "hits" not in o:
        raise FormatoDaBuscaMudou("resposta sem a chave 'hits'")
    h = o["hits"]
    if not isinstance(h, dict) or "total" not in h or "hits" not in h:
        raise FormatoDaBuscaMudou("'hits' sem 'total' ou sem 'hits'")
    total = h["total"]
    if isinstance(total, dict):                      # Elasticsearch 7+ devolve {"value": N}
        total = total.get("value")
    if not isinstance(total, int):
        raise FormatoDaBuscaMudou(f"'hits.total' não é inteiro: {total!r}")
    if not isinstance(h["hits"], list):
        raise FormatoDaBuscaMudou("'hits.hits' não é lista")
    acertos = []
    for hit in h["hits"]:
        f = (hit or {}).get("_source")
        if not isinstance(f, dict) or "conteudo" not in f:
            raise FormatoDaBuscaMudou("acerto sem '_source.conteudo'")
        acertos.append({"conteudo": f.get("conteudo") or "", "data": f.get("data") or "",
                        "pagina": f.get("pagina"), "paginas": f.get("paginas"),
                        "diario_id": f.get("diario_id"), "pdf_id": f.get("pdf_id"),
                        "tipo_edicao": f.get("tipo_edicao")})
    return total, acertos


def varrer_busca_apifront(base: str, termo: str, de: str, ate: str, buscar_fn=None,
                          pausa: float = RITMO_APIFRONT_S, dormir=None) -> tuple:
    """Todos os acertos de um termo na janela, paginando de ZERO. Devolve (total, [acerto]).

    Levanta `FormatoDaBuscaMudou` quando a fonte declara acertos e a primeira página vem vazia:
    isso é mudança de contrato, não ausência de resultado, e confundir os dois é o §210."""
    _buscar = buscar_fn or buscar
    _dormir = dormir or time.sleep
    vistos, saida, total = set(), [], None
    for pagina in range(TETO_PAGINAS_APIFRONT):
        url = BUSCA_APIFRONT.format(base=base.rstrip("/"), pagina=pagina, de=de, ate=ate,
                                    termo=urllib.parse.quote(f'"{termo}"'))
        if pagina:
            _dormir(pausa)
        t, acertos = parse_busca_apifront(_buscar(url, timeout=60))
        if total is None:
            total = t
        if not acertos:
            break
        for a in acertos:
            chave = (a["data"], a["pagina"], a["diario_id"])
            if chave in vistos:
                continue
            vistos.add(chave)
            saida.append(a)
        if len(saida) >= (total or 0) or len(acertos) < TETO_PAGINA_APIFRONT:
            break
    if (total or 0) > 0 and not saida:
        raise FormatoDaBuscaMudou(f"a fonte declara {total} acerto(s) e a primeira página veio vazia")
    return total or 0, saida


# As duas formas REAIS do ato estadual de homologação, lidas no DOE-PR de 15/09/2026. O padrão
# antigo (PADRAO_HOMOLOGA) exigia "município de X" na mesma frase do número do decreto, e nenhuma
# das duas formas reais é assim — por isso nunca casou com documento de verdade.
#   1. "Homologa o Decreto Municipal nº 235, de 15 de setembro de 2026, exarado pelo Prefeito de
#      Boa Vista da Aparecida, o qual declara Situação de Emergência…"  (com número)
#   2. "Homologa situação de emergência no Município de Palmeira, em face da ocorrência de…"
#      (sem número — vai para a fila de pista, como já manda o §3.2)
PAD_HOMOLOGA_EXARADO = re.compile(
    r"homologa\s+(?:o\s+)?decreto\s+municipal\s+n[ºo°\.]?\s*([\d\.\/-]+)[^.]{0,220}?"
    r"exarad[oa]\s+pel[oa]\s+(?:Prefeit[oa]|Chefe\s+do\s+Poder\s+Executivo)(?:\s+Municipal)?"
    r"\s+d[eo]\s+([A-ZÀ-Ú][^,;\.]{1,58})", re.I)
# 16/10/2026, DOE-SP (Decreto 70.765, Guariba): "Homologa, por 180 (cento e oitenta) dias, o decreto
# do Prefeito do Município de Guariba, que declarou Situação de Emergência … Artigo 1º - Fica
# homologado, por 180 (…) dias, o Decreto municipal nº 5.019, de 24 de julho de 2026".
PAD_HOMOLOGA_DECRETO_DO_PREFEITO = re.compile(
    r"homologa,?\s+(?:por\s+[^,]{1,40}?dias,?\s+)?o\s+decreto\s+do\s+prefeito\s+do\s+munic[íi]pio"
    r"\s+de\s+([A-ZÀ-Ú][^,;\.]{1,58})(?:.{0,500}?decreto\s+municipal\s+n[ºo°\.]?\s*([\d\.\/-]+\d))?",
    re.I | re.S)
PAD_HOMOLOGA_NO_MUNICIPIO = re.compile(
    r"homologa\s+(?:a\s+)?(?:situa[çc][ãa]o\s+de\s+emerg[êe]ncia|estado\s+de\s+calamidade\s+p[úu]blica)"
    r"\s+n[oa]\s+munic[íi]pio\s+de\s+([A-ZÀ-Ú][^,;\.]{1,58})", re.I)


# O ato estadual de homologação traz o número do DECRETO ESTADUAL logo antes da ementa
# ("DECRETO Nº 15.155 / Homologa situação de emergência no Município de Cafezal do Sul"). É o ato
# que o estado praticou, e entra no registro ao lado do decreto municipal que ele homologa.
PAD_DECRETO_ESTADUAL = re.compile(r"DECRETO\s+N[ºo°\.]?\s*([\d\.]{3,12})", re.I)


def homologacoes_no_texto(texto: str) -> list:
    """[{municipio, decreto_municipal, decreto_estadual, trecho}] das formas medidas. Função pura.

    UMA entrada por município, e não uma por forma de redação. 26/09/2026, medido na primeira
    varredura real: o ato estadual diz a MESMA coisa duas vezes, e as duas casam —

        DECRETO Nº 15.155
        Homologa situação de emergência no Município de Cafezal do Sul, em face da ocorrência …
        O GOVERNADOR … DECRETA: Art. 1º Homologa o Decreto Municipal nº 242, de …, exarado pelo
        Prefeito de Cafezal do Sul …

    a **ementa** (sem o número do decreto municipal) e o **dispositivo** (com ele). Contar as duas
    produziu 54 atos registrados E 54 pistas dos mesmos municípios, com o motivo "sem número do
    decreto" — fila de revisão humana cheia de trabalho já feito. Agora a chave é o município, e
    entre duas leituras do mesmo ato fica a que tem o número.

    Sem invenção: só o que uma das três formas casa. Página que menciona "situação de emergência"
    em regra administrativa — a do IAT no DOE-PR de 01/07/2026, por exemplo — não casa nenhuma, e
    corretamente não produz registro."""
    por_municipio = {}

    def juntar(municipio, numero, pos):
        m = " ".join((municipio or "").split())
        if not m:
            return
        chave = m.lower()
        estadual = None
        antes = texto[max(0, pos - 400):pos]
        achados_est = PAD_DECRETO_ESTADUAL.findall(antes)
        if achados_est:
            estadual = achados_est[-1]        # o mais próximo da ementa
        novo = {"municipio": m, "decreto_municipal": numero or None, "decreto_estadual": estadual,
                "trecho": " ".join(texto[max(0, pos - 60):pos + 300].split())}
        velho = por_municipio.get(chave)
        if velho is None:
            por_municipio[chave] = novo
            return
        # entre as duas leituras do mesmo ato, fica a que tem o número do decreto municipal;
        # o que faltar numa é completado pela outra.
        if velho.get("decreto_municipal") is None and novo["decreto_municipal"]:
            novo["decreto_estadual"] = novo["decreto_estadual"] or velho.get("decreto_estadual")
            novo["trecho"] = velho["trecho"]          # a ementa é o trecho mais legível dos dois
            por_municipio[chave] = novo
        elif not velho.get("decreto_estadual") and novo["decreto_estadual"]:
            velho["decreto_estadual"] = novo["decreto_estadual"]

    for m in PAD_HOMOLOGA_EXARADO.finditer(texto):
        juntar(m.group(2), m.group(1), m.start())
    for m in PAD_HOMOLOGA_NO_MUNICIPIO.finditer(texto):
        juntar(m.group(1), None, m.start())
    for m in PAD_HOMOLOGA_DECRETO_DO_PREFEITO.finditer(texto):
        juntar(m.group(1), m.group(2), m.start())
    for m in PADRAO_HOMOLOGA.finditer(texto):
        juntar(m.group(2), m.group(1), m.start())
    return list(por_municipio.values())


def parse_dodf(bruto: bytes) -> tuple:
    """(total declarado, [matéria]) da resposta da rota de listagem do DODF. Função pura.

    Levanta `FormatoDaBuscaMudou` quando a rota declara matérias e a lista vem vazia: é mudança de
    contrato, não ausência de resultado, e confundir os dois é o §210."""
    dados = json.loads(bruto.decode("utf-8", "replace") if isinstance(bruto, bytes) else bruto)
    total = int(dados.get("totalMaterias") or 0)
    lista = dados.get("listaMaterias") or []
    if total > 0 and not lista:
        raise FormatoDaBuscaMudou(f"a fonte declara {total} matéria(s) e a lista veio vazia")
    return total, lista


def item_do_dodf(m: dict, uf: str) -> dict:
    """Uma matéria do DODF no formato comum do coletor. Função pura.

    O resumo vem com o termo marcado em `<strong>`; a marcação sai, e o que fica é o texto que a
    fonte serviu. `pagina` não existe nesta fonte — o DODF indexa por MATÉRIA, não por página do
    PDF —, e inventar um número seria pior do que não ter: quem confere abre a matéria."""
    resumo = re.sub(r"<[^>]+>", "", m.get("tx_resumo") or "")
    titulo = (m.get("ds_titulo") or "").strip()
    orgao = (m.get("ds_nome") or "").strip()
    secao = (m.get("ds_secao") or "").strip()
    cabeca = " · ".join(x for x in (titulo, orgao, secao) if x)
    return {"data": (m.get("dt_previsao_publicacao") or "")[:10],
            "pagina": None, "paginas": None,
            "url": DODF_MATERIA.format(co=m.get("co_materia"), slug=m.get("slug") or ""),
            "trechos": [f"{cabeca}: {resumo}".strip(": ")], "territorio": uf}


def itens_dodf(uf: str, desde: str, ate: str, enviar_fn=None, termos=None,
               pausa: float = RITMO_APIFRONT_S, dormir=None) -> tuple:
    """(itens, totais por termo) na busca própria do DODF. Pagina até esgotar o que ela declara.

    `termos` existe para o funil de SAÚDE, que pergunta ao mesmo diário com outras palavras: a rota
    é a mesma, os termos não."""
    _enviar = enviar_fn or enviar
    _dormir = dormir or time.sleep
    itens, totais, vistos = [], {}, set()
    primeira = True
    for termo in (termos or TERMOS_APIFRONT):
        pagina, total = 1, None
        while pagina <= TETO_PAGINAS_DODF:
            # O ritmo de 2 s por domínio é de quem chama (o `_respeitar_ritmo` só honra o
            # `Crawl-delay` que o robots declara, e este host não declara nenhum).
            if not primeira:
                _dormir(pausa)
            primeira = False
            bruto = _enviar(DODF_LISTAR, {"termo": termo, "tpBusca": "exata", "pagina": pagina,
                                          "dtInicial": desde, "dtFinal": ate,
                                          "tpPlatform": "desktop"},
                            timeout=120, origem="coletar_doe")
            t, lista = parse_dodf(bruto)
            if total is None:
                total = t
                totais[termo] = t
            if not lista:
                break
            for m in lista:
                if m.get("co_materia") in vistos:
                    continue
                vistos.add(m.get("co_materia"))
                itens.append(item_do_dodf(m, uf))
            if len(vistos) >= (total or 0):
                break
            pagina += 1
        if pagina > TETO_PAGINAS_DODF:
            totais.setdefault("_truncado", []).append(termo)   # o teto parou a leitura: lida em parte
    return itens, totais


def parse_busca_to(html: str) -> list:
    """[{edicao, data, url}] da tabela de resultado do DOE-TO. Função pura.

    Lê só a tabela que vem depois de "Resultados da busca": o resto da página tem as edições do
    dia, que não casaram com o termo nenhum."""
    m = re.search(r"Resultados da busca.*?</table>", html or "", re.S | re.I)
    if not m:
        return []
    saida = []
    for linha in re.findall(r"<tr\b.*?</tr>", m.group(0), re.S | re.I):
        num = re.search(r"N[ºo°]\s*(\d+)", linha)
        data = re.search(r"(\d{2})/(\d{2})/(\d{4})", linha)
        href = re.search(r'href=["\']([^"\']+)["\']', linha)
        if not (num and data and href):
            continue
        saida.append({"edicao": num.group(1),
                      "data": f"{data.group(3)}-{data.group(2)}-{data.group(1)}",
                      "url": href.group(1)})
    return saida


def parse_busca_ac(html: str) -> list:
    """[{edicao, data, url}] da tabela de resultado do DOE-AC. Função pura."""
    return [{"edicao": n, "data": f"{a}-{m}-{d}", "url": href}
            for d, m, a, href, n in re.findall(
                r'<td>\s*(\d{2})/(\d{2})/(\d{4})\s*</td>\s*<td>\s*<a href="([^"]*download\.php[^"]*)"[^>]*>[^<]*?N\S*\s*(\d+)',
                html or "")]


# =============================================================================================
# SP — o DOE-SP tem API de busca PRÓPRIA, a que o próprio sítio (Next.js) chama
# =============================================================================================
# Medido do runner em 15/10/2026 (runs 38820165075 e 38825296534): a busca é um GET em
# `do-api-web-search.doe.sp.gov.br/v2/advanced-search/publications` com `Terms[0]`, `FromDate`,
# `ToDate`, `PageNumber` e `PageSize`, e devolve `items` (id, date, title, slug, excerpt, hierarchy),
# `totalItems` e `hasNextPage`. A publicação inteira sai de `/v2/publications/<id>`, com `content` em
# HTML — é o que se lê, porque o excerto tem 300 caracteres e o ato de homologação não cabe nele.
# O endereço citável é `doe.sp.gov.br/<slug>`. O caderno "Municípios" publica atos das prefeituras.
BUSCA_SP = ("https://do-api-web-search.doe.sp.gov.br/v2/advanced-search/publications"
            "?PageNumber={pagina}&PageSize={tamanho}&Terms[0]={termo}&FromDate={de}&ToDate={ate}")
PUBLICACAO_SP = "https://do-api-web-search.doe.sp.gov.br/v2/publications/{id}"
PAGINA_SP = "https://doe.sp.gov.br/{slug}"
TAMANHO_PAGINA_SP = 50
TETO_PAGINAS_SP = 20


def parse_busca_sp(bruto: bytes) -> tuple:
    """(total declarado, [item], há próxima página) da resposta da busca do DOE-SP. Função pura.

    Levanta `FormatoDaBuscaMudou` quando a estrutura some ou quando a fonte declara itens e a
    lista vem vazia (§210)."""
    try:
        o = json.loads(bruto.decode("utf-8", "replace") if isinstance(bruto, bytes) else bruto)
    except json.JSONDecodeError as e:
        raise FormatoDaBuscaMudou(f"resposta não é JSON: {e}") from e
    if not isinstance(o, dict) or not isinstance(o.get("items"), list) or "totalItems" not in o:
        raise FormatoDaBuscaMudou("resposta sem 'items' ou sem 'totalItems'")
    total = int(o["totalItems"] or 0)
    if total > 0 and not o["items"]:
        raise FormatoDaBuscaMudou(f"a fonte declara {total} item(ns) e a lista veio vazia")
    return total, o["items"], bool(o.get("hasNextPage"))


def texto_da_publicacao_sp(bruto: bytes) -> str:
    """O texto da publicação, sem a marcação HTML em que a API a serve. Função pura.

    16/10/2026: o conteúdo vem com entidades (`Situa&ccedil;&atilde;o`, `Pre&shy;feito`) e às vezes
    com a folha de estilo escapada; sem decodificar, nenhum padrão de homologação casava (Guariba,
    Decreto 70.765, medido do runner). Decodifica antes de tirar a marcação."""
    import html as _html
    o = json.loads(bruto.decode("utf-8", "replace") if isinstance(bruto, bytes) else bruto)
    conteudo = _html.unescape((o or {}).get("content") or "").replace("\u00ad", "")
    conteudo = re.sub(r"<(style|script|title)\b.*?</\1>", " ", conteudo, flags=re.S | re.I)
    conteudo = re.sub(r"\{[^{}]*\}", " ", re.sub(r"<[^>]+>", " ", conteudo))
    return " ".join(conteudo.split())


def itens_sp(uf: str, desde: str, ate: str, termos=None, buscar_fn=None,
             pausa: float = RITMO_APIFRONT_S, dormir=None) -> tuple:
    """(itens, totais por termo) na API do DOE-SP: busca paginada, depois a publicação inteira de
    cada acerto — uma leitura por publicação, mesmo quando dois termos a apontam."""
    _buscar = buscar_fn or buscar
    _dormir = dormir or time.sleep
    itens, totais, vistos = [], {}, set()
    for termo in (termos or TERMOS_APIFRONT):
        pagina, proxima = 1, True
        while proxima and pagina <= TETO_PAGINAS_SP:
            if pagina > 1 or itens:
                _dormir(pausa)
            total, lista, proxima = parse_busca_sp(_buscar(BUSCA_SP.format(
                pagina=pagina, tamanho=TAMANHO_PAGINA_SP, termo=urllib.parse.quote(termo), de=desde, ate=ate),
                timeout=60, origem="coletar_doe"))
            totais.setdefault(termo, total)
            for it in lista:
                if not it.get("id") or it["id"] in vistos:
                    continue
                vistos.add(it["id"])
                _dormir(pausa)
                texto = texto_da_publicacao_sp(_buscar(PUBLICACAO_SP.format(id=it["id"]), timeout=60, origem="coletar_doe"))
                itens.append({"data": (it.get("date") or "")[:10], "pagina": None, "paginas": None,
                              "url": PAGINA_SP.format(slug=it.get("slug") or it["id"]),
                              "trechos": [f"{it.get('title') or ''} · {it.get('hierarchy') or ''}: {texto[:20000]}"],
                              "territorio": uf})
            pagina += 1
        if proxima:
            totais.setdefault("_truncado", []).append(termo)   # o teto parou a leitura: lida em parte
    return itens, totais


def paginas_com_termo(pdf: bytes, termo: str, extrair_fn=None) -> list:
    """[(página, texto)] do PDF em que o termo aparece. Função pura dado o extrator.

    O PDF da edição tem mais de cem páginas; guardar as que não casaram seria guardar a edição
    inteira para provar duas linhas."""
    if extrair_fn is None:
        from preservar_evidencias import extrair_texto_por_pagina as extrair_fn
    termos = [t.lower() for t in ((termo,) if isinstance(termo, str) else termo)]
    saida = []
    for i, texto in enumerate(extrair_fn(pdf) or [], start=1):
        baixo = (texto or "").lower()
        if any(t in baixo for t in termos):
            saida.append((i, texto))
    return saida


def itens_por_busca(uf: str, desde: str, edicoes_fn, termos=None, buscar_fn=None,
                    pausa: float = RITMO_APIFRONT_S, dormir=None) -> tuple:
    """(itens, totais por termo) de uma busca que aponta edições (TO, AC), descendo ao PDF só das
    edições apontadas na janela. `edicoes_fn(termo)` devolve [{edicao, data, url}]."""
    _buscar = buscar_fn or buscar
    _dormir = dormir or time.sleep
    itens, totais = [], {}
    for n, termo in enumerate(termos or TERMOS_APIFRONT):
        if n:
            _dormir(pausa)
        edicoes = sorted((e for e in edicoes_fn(termo) if e["data"] >= desde), key=lambda e: e["data"], reverse=True)
        totais[termo] = len(edicoes)
        if len(edicoes) > TETO_EDICOES_TO:
            totais.setdefault("_truncado", []).append(termo)
        for e in edicoes[:TETO_EDICOES_TO]:
            _dormir(pausa)
            try:
                pdf = _buscar(e["url"], timeout=240, origem="coletar_doe")
            except Exception as ex:  # noqa: BLE001 — edição que não baixa é lacuna de uma edição, não da UF
                if (getattr(ex, "code", None) or 0) in (401, 403, 429, 451):
                    raise                                   # recusa real se respeita, não se pula
                totais["_nao_baixadas"] = totais.get("_nao_baixadas", 0) + 1
                continue
            achadas = paginas_com_termo(pdf if isinstance(pdf, bytes) else pdf.encode("utf-8"), termo)
            for pag, texto in achadas:
                itens.append({"data": e["data"], "pagina": pag, "paginas": None, "url": e["url"],
                              "trechos": [texto[:20000]], "territorio": uf})
            if not achadas:
                # A busca aponta a edição e o PDF não confirma o termo: isso é divergência da
                # fonte, e entra como o que é — edição apontada, trecho não localizado nela.
                itens.append({"data": e["data"], "pagina": None, "paginas": None, "url": e["url"],
                              "trechos": [f"edição {('nº ' + e['edicao']) if e['edicao'] else 'de ' + e['data']} "
                                          f"apontada pela busca para \"{termo}\"; o termo não foi localizado no PDF"],
                              "territorio": uf})
    return itens, totais


def edicoes_to(desde: str, ate: str):
    def fn(termo):
        bruto = buscar(BUSCA_TO + "?" + urllib.parse.urlencode(
            {"por": "texto", "texto": termo, "data-inicial": desde, "data-final": ate}), timeout=120, origem="coletar_doe")
        return parse_busca_to(bruto.decode("utf-8", "replace") if isinstance(bruto, bytes) else bruto)
    return fn


def edicoes_ac(desde: str, ate: str):
    def fn(termo):
        bruto = enviar(BUSCA_AC, {"palavra": termo, "ano_palavra": ate[:4]}, timeout=120, origem="coletar_doe")
        return parse_busca_ac(bruto.decode("latin-1", "replace"))
    return fn


EDICOES_POR_BUSCA = {"busca_to": edicoes_to, "busca_ac": edicoes_ac}


# =============================================================================================
# Edição por data — o DOE sem busca que publica a edição em PDF num endereço previsível
# =============================================================================================
# Medido do runner em 14 e 15/10/2026 (runs 38555616491 e 38820165075):
#   CE  imagens.seplag.ce.gov.br/PDF/AAAAMMDD/doAAAAMMDDpNN.pdf — a edição sai em CADERNOS
#       ("Caderno 1/4"; 3 em 13/10), um PDF por caderno, ~1 MB e 52–64 páginas cada, texto
#       extraível. O caderno seguinte ao último responde HTTP 300 ("Multiple Choices", o servidor
#       sugere os nomes parecidos) — e não 404; os dois encerram a edição. A busca
#       (pesquisa.doe.seplag.ce.gov.br) não responde ao runner.
#   PB  o padrão por data do canal 2 (`coletar_edicoes_doe.PADROES`): 40 páginas, texto extraível.
# Sem busca, o custo é a edição inteira; por isso a janela é curta (os oito dias do elo) e o que já
# foi lido não se relê — `fontes_doe.json` guarda, por UF, as datas lidas (`lidas`), podadas à janela.
# Data sem edição (feriado, atraso) não entra em `lidas`: fica para a tentativa seguinte.
JANELA_EDICOES_DIAS = 8
TETO_CADERNOS = 8
PDF_CE = "https://imagens.seplag.ce.gov.br/PDF/{dc}/do{dc}p{n:02d}.pdf"


def edicoes_ce(buscar_fn, base=None):
    """Os cadernos da edição do dia, do 1º ao último que existe — o seguinte responde 300 ou 404."""
    def fn(data):
        dc, saida = data.replace("-", ""), []
        for n in range(1, TETO_CADERNOS + 1):
            url = PDF_CE.format(dc=dc, n=n)
            try:
                pdf = buscar_fn(url, timeout=240, origem="coletar_doe")
            except Exception as e:  # noqa: BLE001
                if getattr(e, "code", None) in (300, 404):
                    break
                raise
            saida.append({"edicao": f"caderno {n}", "url": url, "pdf": pdf})
        return saida
    return fn


def edicoes_pb(buscar_fn, base=None):
    padrao = PADROES_CANAL2["PB"]["padrao"]
    return lambda data: [{"edicao": None, "url": endereco_da_data(padrao, data)}]


# AM (15/10/2026, runs 38820165075 e 38821475418): a plataforma comum sem busca (§231) serve a
# edição do dia pela rota (a) — `{"erro": false, "itens": [{"id": 18246, "numero": 35804, ...}]}`
# ou `{"erro": true, "msg": "Edição não existente!"}`, que é dia sem edição, não falha — e o PDF pela
# rota (c) com o `id` da listagem (12,8 MB, 58 páginas, texto extraível). Vale para toda UF da
# plataforma cuja busca não responda: a base vem do `fontes_doe.json`.
EDICOES_APIFRONT = "{base}/apifront/portal/edicoes/edicoes_from_data/{data}.json"


def edicoes_apifront(buscar_fn, base):
    def fn(data):
        o = json.loads(buscar_fn(EDICOES_APIFRONT.format(base=base.rstrip("/"), data=data),
                                 timeout=60, origem="coletar_doe").decode("utf-8", "replace"))
        if not isinstance(o, dict) or "itens" not in o:
            raise FormatoDaBuscaMudou("listagem de edições sem a chave 'itens'")
        return [{"edicao": str(it.get("numero") or ""), "url": PDF_APIFRONT.format(base=base.rstrip("/"), diario_id=it["id"])}
                for it in (o.get("itens") or []) if it.get("id")]
    return fn


# MS (15/10/2026, run 38820165075): a listagem `spdo.ms.gov.br/diariodoe/` traz o endereço do PDF de
# cada edição recente, e o nome do arquivo carrega número E data (DO12306_14_10_2026.pdf; suplemento
# DO12302_08_10_2026_SUP_1.pdf). O canal 2 estima o número por âncoras para o histórico; aqui a
# janela é de oito dias e a listagem cobre — lê-se uma vez por rodada.
LISTAGEM_MS = "https://www.spdo.ms.gov.br/diariodoe/"
RE_PDF_MS = re.compile(r'href="(https?://[^"]*?/DO(\d{4,6})_(\d{2})_(\d{2})_(\d{4})(?:_SUP_\d+)?\.pdf)"', re.I)


def edicoes_ms_na_listagem(html: str) -> dict:
    """{data ISO: [{edicao, url}]} lidos dos nomes de arquivo da listagem. Função pura."""
    fora = {}
    for url, num, dd, mm, aaaa in RE_PDF_MS.findall(html or ""):
        fora.setdefault(f"{aaaa}-{mm}-{dd}", []).append({"edicao": num, "url": url})
    return fora


def edicoes_ms(buscar_fn, base=None):
    lista = {}

    def fn(data):
        if not lista:
            lista.update(edicoes_ms_na_listagem(
                buscar_fn(base or LISTAGEM_MS, timeout=60, origem="coletar_doe").decode("utf-8", "replace")))
            if not lista:
                raise FormatoDaBuscaMudou("a listagem do DOE-MS não traz nenhum PDF nomeado por data")
        return lista.get(data, [])
    return fn


# PI (16/10/2026, runs 38878232356 e 38879265290): o diário atual (`www.diario.pi.gov.br/doe/`) lista as
# edições do dia pela rota que a própria tabela chama — POST `Api/listardiarios.json` com `filter_data`
# —, suplementar incluído; dia sem edição é `"data": []`. Cada linha aponta o PDF em
# `files/diarios/anexo/<uuid>/<arquivo>.pdf` (texto extraível, 13 páginas na sonda).
RE_PDF_PI = re.compile(r'href="\.\./doe/(files/diarios/anexo/[^"]+\.pdf)"')


def edicoes_pi(buscar_fn, base, enviar_fn=None):
    raiz = base.rstrip("/")

    def fn(data):
        o = json.loads((enviar_fn or enviar)(raiz + "/Api/listardiarios.json", {"draw": "1", "start": "0", "length": "20",
                                              "filter_numero": "", "filter_data": data},
                                             timeout=60, origem="coletar_doe").decode("utf-8", "replace"))
        if not isinstance(o, dict) or not isinstance(o.get("data"), list):
            raise FormatoDaBuscaMudou("listagem do DOE-PI sem a lista 'data'")
        achados = [(RE_PDF_PI.search(str(linha[0])), linha) for linha in o["data"] if linha]
        if any(m is None for m, _ in achados):
            raise FormatoDaBuscaMudou("linha da listagem do DOE-PI sem o endereço do PDF")
        return [{"edicao": " ".join(str(linha[1]).split()), "url": f"{raiz}/{m.group(1)}"} for m, linha in achados]
    return fn


EDICOES_POR_DATA = {"edicao_ce": edicoes_ce, "edicao_pb": edicoes_pb,
                    "edicao_apifront": edicoes_apifront, "edicao_ms": edicoes_ms, "edicao_pi": edicoes_pi}


def itens_por_edicao(uf: str, desde: str, ate: str, edicoes_fn, lidas: dict, termos=None,
                     buscar_fn=None, pausa: float = RITMO_APIFRONT_S, dormir=None, extrair_fn=None) -> tuple:
    """(itens, totais) das edições por data ainda não lidas na janela.

    `edicoes_fn(data)` devolve [{edicao, url, pdf?}] — vazio quando não há edição na data. Só a
    página em que um termo aparece vira item; a edição lida entra em `lidas[data]` e não se relê.
    Edição que não baixa é lacuna de UMA edição (contada), não da UF; arquivo que não é PDF, ou é
    pequeno demais para ser uma edição, é mudança de contrato e LEVANTA (§210)."""
    _buscar = buscar_fn or buscar
    _dormir = dormir or time.sleep
    inicio = max(desde, (date.fromisoformat(ate) - timedelta(days=JANELA_EDICOES_DIAS)).isoformat())
    itens, totais = [], {"edicoes_lidas": 0, "datas_sem_edicao": 0, "edicoes_nao_baixadas": 0}
    for data in (d for d in datas_do_periodo(inicio, ate) if d not in lidas):
        lidas_na_data = 0
        for e in edicoes_fn(data):
            _dormir(pausa)
            try:
                pdf = e.get("pdf") or _buscar(e["url"], timeout=240, origem="coletar_doe")
            except Exception as ex:  # noqa: BLE001
                if getattr(ex, "code", None) != 404:
                    totais["edicoes_nao_baixadas"] += 1
                continue
            if pdf[:5] != b"%PDF-" or len(pdf) < MINIMO_BYTES_DE_EDICAO:
                raise FormatoDaBuscaMudou(f"{e['url']} não é uma edição em PDF ({len(pdf)} bytes)")
            for pag, texto in paginas_com_termo(pdf, termos or TERMOS_APIFRONT, extrair_fn):
                itens.append({"data": data, "pagina": pag, "paginas": None, "url": e["url"],
                              "trechos": [texto[:20000]], "territorio": uf})
            lidas_na_data += 1
        if lidas_na_data:
            lidas[data] = lidas_na_data
            totais["edicoes_lidas"] += lidas_na_data
        else:
            totais["datas_sem_edicao"] += 1
    for d in [d for d in lidas if d < inicio]:
        del lidas[d]
    return itens, totais


def itens_apifront(uf: str, base: str, desde: str, ate: str, buscar_fn=None, pausa: float = RITMO_APIFRONT_S,
                   termos=None) -> tuple:
    """(itens no formato comum do coletor, total declarado por termo). Não grava nada."""
    itens, totais = [], {}
    for termo in termos or TERMOS_APIFRONT:
        total, acertos = varrer_busca_apifront(base, termo, desde, ate, buscar_fn=buscar_fn, pausa=pausa)
        totais[termo] = total
        if total > len(acertos):
            totais.setdefault("_truncado", []).append(termo)
        for a in acertos:
            itens.append({"data": a["data"], "pagina": a["pagina"], "paginas": a["paginas"],
                          "url": PDF_APIFRONT.format(base=base.rstrip("/"), diario_id=a["diario_id"]),
                          "trechos": [a["conteudo"]], "territorio": uf})
    return itens, totais


# 17/10/2026 (HANDOVER_ROTAS_DOE §0.2): a busca de cada adaptador num lugar só. O canal 1
# (homologação), o funil de saúde (planos) e o canal 2 (declaração de emergência em saúde) perguntam
# ao MESMO diário com termos diferentes; três despachos copiados divergiam na primeira rota nova.
ADAPTADORES_DE_BUSCA = ("dodf", "apifront", "busca_sp", *EDICOES_POR_BUSCA)


def itens_da_busca(uf: str, adaptador: str, base: str, desde: str, ate: str, termos=None) -> tuple:
    """(itens, totais por termo) da busca do diário desta UF pelo seu adaptador. Não grava nada."""
    if adaptador == "dodf":
        return itens_dodf(uf, desde, ate, termos=termos)
    if adaptador == "apifront":
        return itens_apifront(uf, base, desde, ate, termos=termos)
    if adaptador == "busca_sp":
        return itens_sp(uf, desde, ate, termos=termos)
    return itens_por_busca(uf, desde, EDICOES_POR_BUSCA[adaptador](desde, ate), termos=termos)


def iso_para_br(s: str) -> str:
    try:
        y, m, d = s[:10].split("-"); return f"{d}/{m}/{y}"
    except ValueError:
        return s


# 04/10/2026 — A SOBRA DO DOE NASCE NO ESQUEMA.
#
# Medido pela central: `Publicar dados` falhou duas vezes na noite de 03→04 (04:51 e 05:16 UTC) no
# portão `verificar_esquema_de_pista.py`, com "10 pista(s) nova(s) fora do esquema" — e **nenhum dado
# novo foi publicado**. As dez eram homologações estaduais achadas aqui, gravadas na forma antiga
# (`municipio`/`uf`/`url`/`trecho`), que é anterior ao `schemas/pista.json` do handover de 03/10.
#
# O portão acusou o certo. O que estava errado era a GRAVAÇÃO: o esquema diz, em letra de forma, que
# "pista sem os campos obrigatórios é RECUSADA NA GRAVAÇÃO" — filtrar na saída não dá conta do que
# entra errado. Aqui a sobra passa a nascer com os seis campos obrigatórios e com o `destino`
# declarado, porque ela não é pista de plano e nunca foi: homologação de emergência é ato de
# RESPOSTA, e o esquema manda a pista de decreto para a conferência da base oficial, não para a fila
# de planos. O que faltava era dizer isso no dado.
def sobra_de_homologacao(hm: dict, hash_evidencia: str, hoje: str, cod_ibge=None) -> dict:
    """A homologação que não virou registro, na forma do esquema. Função pura.

    Entra aqui o que não casou: sem número do decreto municipal, ou município que não casou com a
    base do IBGE. O `alvo` é o código do município quando ele existe e a UF quando não — "UF" é um
    alvo legítimo no esquema, e é a verdade do que se sabe: o ato é daquele estado, e o município
    ainda não foi identificado. `nivel` é A porque a fonte é o Diário Oficial do Estado.
    """
    return {
        "url_final": hm.get("url"),
        "tipo": "decreto",
        "alvo": str(cod_ibge or hm.get("uf") or ""),
        "nivel": "A",
        "data": hm.get("data") or hoje,
        "origem": "doe",
        "registrado_em": hoje,
        # O destino declarado é o que impede esta sobra de ser lida como pista de plano por quem
        # vier depois — inclusive pelo portão, que rebaixa a aviso o que está declarado.
        "destino": "conferencia_resposta",
        "motivo": hm.get("motivo") or "sem número do decreto ou município não casou com IBGE",
        "municipio": hm.get("municipio"),
        "uf": hm.get("uf"),
        "decreto_estadual": hm.get("decreto_estadual"),
        "decreto_municipal": hm.get("decreto_municipal"),
        "trecho": hm.get("trecho"),
        "pagina": hm.get("pagina"),
        "paginas": hm.get("paginas"),
        "hash_evidencia": hash_evidencia,
    }


def coletar_uf(uf: str, desde: str, cfg: dict) -> str:
    por_cod, por_nome = referencia_ibge()
    f = cfg["ufs"][uf]
    hoje = hoje_editorial().isoformat()
    ja_registrada_hoje = f.get("ultima_tentativa") == hoje
    f["ultima_tentativa"] = hoje
    if not f.get("adaptador") or not f.get("url"):
        # 24/09/2026 (§194): a lacuna é REAL e continua declarada — mas uma vez por dia, não a cada
        # rodada. Com a cadência de 2h, as 27 UFs geravam 324 lacunas idênticas por dia: 2.479 desde
        # 03/09, um terço de todos os erros do log, sobre um fato que não muda de duas em duas horas.
        # Registro que não distingue novidade de repetição deixa de informar e passa a esconder.
        if not ja_registrada_hoje:
            registrar_lacuna(f"DOE/{uf}", "sem adaptador de busca neste diário", canal="repositorio_estadual",
                             camada=1, uf=uf)
        # 14/10/2026: "a_verificar" por 42 dias era lacuna não declarada — já se tentou, e o que
        # falta é o adaptador. O estado diz isso; a sondagem ao lado diz por onde começar.
        f["status"] = "sem adaptador de busca"; return "lacuna"
    if f["adaptador"] in (*ADAPTADORES_DE_BUSCA, *EDICOES_POR_DATA):
        # A evidência é o conjunto de trechos como a FONTE OFICIAL os serviu — na busca, o endereço
        # citável de cada acerto; na edição por data, a URL do PDF e a página. Preservar o PDF
        # inteiro de cada acerto passaria de meio gigabyte por varredura e não acrescentaria prova.
        url = f["url"]
        try:
            if f["adaptador"] in EDICOES_POR_DATA:
                itens, totais = itens_por_edicao(uf, desde, hoje, EDICOES_POR_DATA[f["adaptador"]](buscar, url),
                                                 f.setdefault("lidas", {}))
            else:
                # §231: a busca da plataforma comum entrega o TEXTO INTEGRAL da página que casou.
                itens, totais = itens_da_busca(uf, f["adaptador"], url, desde, hoje)
        except FormatoDaBuscaMudou as e:
            registrar_lacuna(f"DOE/{uf}", f"formato da busca mudou: {e}", canal="repositorio_estadual",
                             camada=1, uf=uf, strings=[url])
            f["status"] = "erro: formato"; return "erro"
        except Exception as e:  # noqa: BLE001
            registrar_lacuna(f"DOE/{uf}", f"{type(e).__name__}: {e}", canal="repositorio_estadual",
                             camada=1, uf=uf, strings=[url])
            f["status"] = f"erro: {type(e).__name__}"; return "erro"
        corpo = json.dumps({"fonte": url, "janela": [desde, hoje], "totais_por_termo": totais,
                            "paginas": itens}, ensure_ascii=False, indent=1).encode("utf-8")
        h = preservar_evidencia(corpo, url, "json", "coletar_doe")
        if any(eh_suspensao_defeso(t) for it in itens for t in it["trechos"]):
            registrar_lacuna(f"DOE/{uf}", "aviso de período eleitoral na fonte", canal="repositorio_estadual",
                             camada=1, uf=uf, strings=[url], suspensa=True, hash_evidencia=h)
            f["status"] = "fonte suspensa (defeso)"; return "suspensa"
    else:
        if f["adaptador"] == "querido_diario":
            params = urllib.parse.urlencode({"territory_ids": f["url"], "published_since": desde,
                                             "querystring": " OR ".join(f'"{t}"' for t in TERMOS[:4]), "size": 100})
            url = QD_API.format(params=params)
        else:
            url = f["url"]
        try:
            bruto = buscar(url)
        except Exception as e:  # noqa: BLE001
            registrar_lacuna(f"DOE/{uf}", f"{type(e).__name__}: {e}", canal="repositorio_estadual", camada=1, uf=uf, strings=[url])
            f["status"] = f"erro: {type(e).__name__}"; return "erro"
        texto = bruto.decode("utf-8", "replace")
        h = preservar_evidencia(bruto, url, "json" if f["adaptador"] == "querido_diario" else "html", "coletar_doe")
        if f["adaptador"] != "querido_diario" and eh_suspensao_defeso(texto):
            registrar_lacuna(f"DOE/{uf}", "aviso de período eleitoral na fonte", canal="repositorio_estadual",
                             camada=1, uf=uf, strings=[url], suspensa=True, hash_evidencia=h)
            f["status"] = "fonte suspensa (defeso)"; return "suspensa"
        if f["adaptador"] == "querido_diario":
            try:
                _dados_qd = json.loads(texto)
                # 10/09/2026: além do excerto da API, o texto integral da edição (mesma regra do
                # coletor municipal) — quem julga lê o documento inteiro offline.
                preservar_texto_integral(h, _dados_qd.get("gazettes", []), "coletar_doe")
                itens = parse_querido_diario(_dados_qd)
            except json.JSONDecodeError:
                registrar_lacuna(f"DOE/{uf}", "resposta não é JSON", canal="repositorio_estadual", camada=1, uf=uf, hash_evidencia=h)
                f["status"] = "erro: formato"; return "erro"
        else:
            itens = [{"data": hoje_editorial().isoformat(), "url": url, "trechos": [texto[:20000]], "territorio": uf}]
    homol = extrair_homologacoes(itens, uf)
    atos = ler("atos_resposta.json"); pistas = ler("pistas_doe.json", {"_governanca": "Pistas de DOE (v2.2.4): "
                                                                        "descoberta, nunca registro.", "itens": []})
    vistos = {(e["nome"], e["uf"], e["data"], e.get("causa")) for e in atos["eventos"]}
    novos = pist = 0
    for hm in homol:
        cod = por_nome.get((hm["municipio"], hm["uf"]))
        if not cod or not hm["decreto_municipal"]:
            pistas["itens"].append(
                sobra_de_homologacao(hm, h, hoje_editorial().isoformat(), cod)); pist += 1
            continue
        ref = por_cod[cod]; dbr = iso_para_br(hm["data"])
        chave = (ref["nome"], hm["uf"], dbr, "homologação estadual")
        if chave in vistos:
            continue
        # §231: quando a fonte diz em que página do PDF o ato está, isso vai ao registro — é a
        # diferença entre "está nesta edição de 104 páginas" e "está na página 11".
        pagina = f" (p. {hm['pagina']} de {hm['paginas']})" if hm.get("pagina") else ""
        est = f"Decreto estadual nº {hm['decreto_estadual']}, " if hm.get("decreto_estadual") else ""
        atos["eventos"].append({"nome": ref["nome"], "uf": hm["uf"], "ibge": cod, "data": dbr,
                                "causa": "homologação estadual", "decreto": f"Decreto municipal nº {hm['decreto_municipal']}",
                                "decreto_estadual_homologacao": f"{est}DOE/{hm['uf']} {dbr}{pagina}", "url_doe": hm["url"],
                                "fonte": f"Diário Oficial do Estado ({hm['uf']})", "url": hm["url"],
                                "lat": ref["lat"], "lon": ref["lon"], "canal": "repositorio_estadual", "hash_evidencia": h})
        marcar_fato_municipal(cod, "decreto_homologado", True); vistos.add(chave); novos += 1
    gravar("atos_resposta.json", carimbar_atos(atos)); sincronizar_pistas("pistas_doe.json", pistas, origem="doe", ler_fn=ler, gravar_fn=gravar)
    ibges_uf = [c for c, r in por_cod.items() if r["uf"] == uf]
    marcar_fonte_consultada(ibges_uf, f"DOE/{uf}", "estadual", resultado=f"{len(itens)} edição(ões)/trecho(s)")
    log_busca("repositorio_estadual", 1, TERMOS[:4], "registro" if novos else "pista", uf=uf, nivel="estadual",
              n_resultados=len(itens), resultados=f"{len(homol)} homologações, {novos} novas, {pist} pistas", hash_evidencia=h)
    f["status"] = "ok"; return "ok"


FIXTURE_QD = {"total_gazettes": 1, "gazettes": [{"territory_id": "42", "date": "2026-08-31", "url": "https://x/doe.pdf",
              "excerpts": ["DECRETO Nº 5.000 — Homologa o Decreto Municipal nº 123/2026 que declara situação de emergência no Município de Blumenau - SC."]}]}


# Recorte REAL da rota de listagem do DODF, 01/10/2026 (um dos 7 acertos de "situação de
# emergência" na janela 29/06→01/10; resumo encurtado, estrutura como veio).
FIXTURE_DODF = json.dumps({
    "type": "success", "totalMaterias": 7, "totalPaginas": 1, "pagina": 1,
    "listaMaterias": [{
        "co_materia": 627377, "ds_titulo": "EXTRATO CONTRATUAL", "ds_nome": "Secretaria de Estado de Saúde",
        "ds_materia_tipo": "Extrato", "ds_secao": "Seção III", "nu_jornal": 169,
        "dt_previsao_publicacao": "2026-09-11T05:30:00Z", "slug": "extrato-contratual",
        "tx_resumo": "...A vigência contratual está vinculada à permanência da <strong>situação</strong> "
                     "<strong>de</strong> <strong>emergência</strong>, devendo o contrato ser rescindido..."}],
}, ensure_ascii=False).encode("utf-8")

# Recorte REAL da tabela de resultado do DOE-TO, 01/10/2026.
FIXTURE_BUSCA_AC = """<p>Quantidade de resultados encontrados: 2</p> <table cellspacing="0"><tbody>
<tr id="trId1_5827" onmouseover="ativarDesativarId(true, 'trId2_5827')"> <td>14/10/2026</td> <td> <a href="https://diario.ac.gov.br/download.php?arquivo=KEQxQHI3IyEpRE8xNzkxOTgyNTkyMjMxMy5wZGY=" title="Fazer download"> Diário Oficial N° 14372 - Caderno Único </a> </td> <td class="txtright">26.79 MB</td> </tr>
<tr id="trId2_5827"> <td colspan="3"> <p>...Declara <span class="destaque">situação de emergência</span> nas áreas...</p> </td> </tr>
<tr id="trId1_5501"> <td>20/08/2026</td> <td> <a href="https://diario.ac.gov.br/download.php?arquivo=QUJD" title="Fazer download"> Diário Oficial N° 14100 - Caderno Único </a> </td> <td class="txtright">20.01 MB</td> </tr>"""
FIXTURE_BUSCA_TO = """<h5 class="center-align">Resultados da busca</h5> <table class="responsive-table">
 <thead><tr><th>Edição</th><th>Publicado em</th><th>Páginas</th></tr></thead><tbody>
 <tr><td>Nº 7154</td><td>30/09/2026</td><td>71 pág.</td>
     <td><a href="https://doe.to.gov.br/diario/5793/download">Baixar</a></td></tr>
 <tr><td>Nº 7153</td><td>29/09/2026</td><td>112 pág.</td>
     <td><a href="https://doe.to.gov.br/diario/5792/download">Baixar</a></td></tr>
 </tbody></table>"""

# Recorte REAL da resposta da busca do DOE-PR, 26/09/2026 (texto encurtado; a estrutura é a que veio).
FIXTURE_APIFRONT = json.dumps({
    "took": 63, "timed_out": False, "_shards": {"total": 1, "successful": 1},
    "hits": {"total": 2, "max_score": 12.3, "hits": [
        {"_source": {"data": "2026-09-15", "pagina": 10, "paginas": 509, "pdf_id": 1204270,
                     "diario_id": 17314, "tipo_edicao": 3,
                     "conteudo": "10 3ª FEIRA |15/SET/2026 - EDIÇÃO N° 12.228 PODER EXECUTIVO ESTADUAL "
                                 "DECRETA: Art. 1º Homologa o Decreto Municipal nº 235, de 15 de setembro "
                                 "de 2026, exarado pelo Prefeito de Boa Vista da Aparecida, o qual declara "
                                 "Situação de Emergência nas áreas do município em face da ocorrência de "
                                 "Tempestade Local/Convectiva - Vendaval."}},
        {"_source": {"data": "2026-09-15", "pagina": 9, "paginas": 509, "pdf_id": 1204269,
                     "diario_id": 17314, "tipo_edicao": 3,
                     "conteudo": "Homologa situação de emergência no Município de Palmeira, em face da "
                                 "ocorrência de Tempestade Local/Convectiva - Vendaval."}},
    ]},
}, ensure_ascii=False).encode("utf-8")
FIXTURE_APIFRONT_VAZIO = json.dumps({"hits": {"total": 0, "hits": []}}, ensure_ascii=False).encode("utf-8")
# O caso que enganou a primeira sonda: total declarado, página vazia.
FIXTURE_APIFRONT_TOTAL_SEM_LISTA = json.dumps({"hits": {"total": 7, "hits": []}}, ensure_ascii=False).encode("utf-8")


def fonte_do_coletor() -> str:
    """O código OPERACIONAL deste arquivo, como texto — tudo o que vem antes do autoteste.

    Mesma trava estrutural do coletor de saúde, e pela mesma razão: o portão tem de perceber se
    uma edição futura ganhar escrita em arquivo do banco. O corte no `def autoteste` evita que o
    teste se encontre a si mesmo nos nomes que procura."""
    texto = pathlib.Path(__file__).read_text(encoding="utf-8")
    corte = texto.find("def autoteste")
    return texto[:corte] if corte > 0 else texto


# A lista canônica do projeto, num só lugar: trava que cobre três dos cinco arquivos não é trava.
BANCO_PROIBIDO = ("estados.json", "saude_uf.json", "municipios.json", "indice.json",
                  "monitor_saude.json")


def _levanta(fn, excecao) -> bool:
    """True quando `fn` levanta `excecao`. Existe para o caso negativo não virar try/except solto
    dentro de um lambda, onde ele não cabe."""
    try:
        fn()
    except excecao:
        return True
    except Exception:  # noqa: BLE001
        return False
    return False


def _erro_http(url, codigo=404):
    import urllib.error
    return urllib.error.HTTPError(url, codigo, "", {}, None)


PDF_FALSO = b"%PDF-1.4 " + b"x" * MINIMO_BYTES_DE_EDICAO


def _t_edicao_por_data() -> bool:
    lidas = {"2026-10-08": 1, "2026-09-01": 1}
    pedidos = []

    def falso(url, **k):
        pedidos.append(url)
        if "2026-10-15" in url:
            raise _erro_http(url)
        return PDF_FALSO

    itens, totais = itens_por_edicao(
        "PB", "2026-06-29", "2026-10-15", lambda d: [{"edicao": None, "url": f"https://x/{d}.pdf"}], lidas,
        buscar_fn=falso, dormir=lambda s: None,
        extrair_fn=lambda _: ["nada", "Homologa situação de emergência no Município de Sobral."])
    # janela de 8 dias a partir de 15/10: dias úteis 07, 08, 09, 12, 13, 14 e 15; o 08 já estava lido
    return (len(pedidos) == 6 and len(itens) == 5 and all(i["pagina"] == 2 for i in itens)
            and totais == {"edicoes_lidas": 5, "datas_sem_edicao": 1, "edicoes_nao_baixadas": 0}
            and sorted(lidas) == ["2026-10-07", "2026-10-08", "2026-10-09", "2026-10-12", "2026-10-13", "2026-10-14"])


# Recorte REAL da listagem do DOE-MS, 15/10/2026 (run 38820165075).
# Recorte REAL da listagem do DOE-PI de 14/10/2026 (run 38879265290): edição e suplementar.
FIXTURE_LISTAGEM_PI = (b'{"draw":1,"recordsTotal":2,"recordsFiltered":2,"data":[["<a href=\\"..\\/doe\\/files\\/diarios\\/anexo'
                       b'\\/d714cae0-47e5-4560-a789-ac9d636518ef\\/e2052f2e-6ed8-4bcb-b399-5f48c77567b3.pdf\\" target=\\"_blank\\">'
                       b'<\\/a>","197\\/2026  SUPLEMENTAR","14\\/10\\/2026","14\\/10\\/2026 21:34:53"],["<a href=\\"..\\/doe'
                       b'\\/files\\/diarios\\/anexo\\/5cc561ff-8ff1-4435-a0a6-d8b59c3c6249\\/0d2588a1-8ba2-4926-a4f8-c2a257a45015.pdf'
                       b'\\" target=\\"_blank\\"><\\/a>","197\\/2026  ","14\\/10\\/2026","14\\/10\\/2026 18:01:55"]]}')


FIXTURE_LISTAGEM_MS = """<a href="https://assets.imprensaoficial.ms.gov.br/public/prd/Diario%20Oficial/2026/10/08/DO12302_08_10_2026.pdf">
<a href="https://assets.imprensaoficial.ms.gov.br/public/prd/Diario%20Oficial/2026/10/08/DO12302_08_10_2026_SUP_1.pdf">
<a href="https://assets.imprensaoficial.ms.gov.br/public/prd/Diario%20Oficial/2026/10/13/DO12304_13_10_2026.pdf">
<a href="https://assets.imprensaoficial.ms.gov.br/public/prd/Diario%20Oficial/2026/10/13/DO12305_13_10_2026.pdf">
<a href="https://assets.imprensaoficial.ms.gov.br/public/assets/prd/app-assets/168049/_next/static/chunks/0-g1xzsskqha5.js">"""
# Recortes REAIS da rota (a) do DOE-AM, 15/10/2026.
FIXTURE_EDICOES_AM = (b'{"erro":false,"msg":"","data":"2026-10-13","numero":null,"ano":"","itens":[{"id":18246,'
                      b'"data":"13\\/10\\/2026","suplemento":0,"numero":35804,"tipo_edicao_id":1,"capa":1,"paginas":48}]}')
FIXTURE_EDICOES_AM_VAZIO = b'{"erro":true,"msg":"Edi\\u00e7\\u00e3o n\\u00e3o existente!","data":"2026-10-14","itens":[]}'


# Recortes REAIS da API do DOE-SP, 15/10/2026 (run 38825296534; excerto encurtado).
FIXTURE_BUSCA_SP = json.dumps({
    "items": [{"isLegacy": False, "id": "dbeb0429-e167-4e3c-b76c-08df1efd0e0c", "date": "2026-10-05T01:03:00.8319626",
               "title": "DESPACHO DO SECRETÁRIO, DE 2 DE OUTUBRO DE 2026",
               "slug": "executivo/casa-civil/despacho-do-secretario-de-2-de-outubro-de-2026-20261002111012042179446",
               "excerpt": "o Decreto nº 70.765, de 24 de julho de 2026, que homologou o decreto do Prefeito de Guariba",
               "hierarchy": "Executivo > Atos Normativos > Casa Civil > Gabinete do Secretário", "totalTermsFound": 1}],
    "currentPage": 1, "totalPages": 1, "totalItems": 1, "pageSize": 2, "hasPreviousPage": False, "hasNextPage": False},
    ensure_ascii=False).encode("utf-8")
FIXTURE_PUBLICACAO_SP = json.dumps({
    "id": "dbeb0429-e167-4e3c-b76c-08df1efd0e0c", "title": "DESPACHO DO SECRETÁRIO, DE 2 DE OUTUBRO DE 2026",
    "date": "2026-10-05", "journal": "Executivo",
    "content": "<html><head><style type=\"text/css\">p.Citacao {font-size:10pt;}</style><title>SEI/GESP</title></head>"
               "<body><p class=\"Estilo_DOE\">bem como o Decreto nº 70.765, de 24 de julho de 2026, que homologou o "
               "decreto do Prefeito de Guariba, que declarou situação de emergência em áreas do Município</p></body></html>"},
    ensure_ascii=False).encode("utf-8")


def _t_cadernos_ce() -> bool:
    def falso(url, **k):
        if "p03" in url:
            raise _erro_http(url, 300)      # medido em 15/10/2026: o caderno a mais responde 300
        return PDF_FALSO
    cadernos = edicoes_ce(falso)("2026-10-14")
    return ([c["url"] for c in cadernos] == ["https://imagens.seplag.ce.gov.br/PDF/20261014/do20261014p01.pdf",
                                             "https://imagens.seplag.ce.gov.br/PDF/20261014/do20261014p02.pdf"]
            and all(c["pdf"] == PDF_FALSO for c in cadernos))


def autoteste() -> int:
    def t1(): return len(parse_querido_diario(FIXTURE_QD)) == 1
    def t2():
        h = extrair_homologacoes(parse_querido_diario(FIXTURE_QD), "SC")
        return len(h) == 1 and h[0]["municipio"] == "Blumenau" and h[0]["decreto_municipal"] == "123/2026"
    def t3(): return parse_querido_diario({}) == [] and parse_querido_diario(None) == []
    def t4():
        cfg = fontes_doe_padrao(); return len(cfg["ufs"]) == 27 and all(v["status"] == "a_verificar" for v in cfg["ufs"].values())
    def t5():
        """§231: o parser da busca da plataforma comum, sobre recorte real."""
        total, acertos = parse_busca_apifront(FIXTURE_APIFRONT)
        return (total == 2 and len(acertos) == 2 and acertos[0]["pagina"] == 10
                and acertos[0]["paginas"] == 509 and acertos[0]["diario_id"] == 17314
                and "Boa Vista da Aparecida" in acertos[0]["conteudo"])

    def t6():
        """As DUAS formas reais do ato estadual, e o falso positivo que não pode virar registro.

        A terceira string é uma página real do DOE-PR de 01/07/2026: regra administrativa do IAT
        que cita "situação de emergência" sem homologar nada. Se ela casasse, o projeto publicaria
        um ato que não existe."""
        a = homologacoes_no_texto("Homologa o Decreto Municipal nº 235, de 15 de setembro de 2026, "
                                  "exarado pelo Prefeito de Boa Vista da Aparecida, o qual declara "
                                  "Situação de Emergência nas áreas do município.")
        b = homologacoes_no_texto("Homologa situação de emergência no Município de Palmeira, em face "
                                  "da ocorrência de Tempestade Local/Convectiva - Vendaval.")
        c = homologacoes_no_texto("indicado pela CEDEC para atuar em colaboração no enfrentamento da "
                                  "situação de emergência ou de estado calamidade pública, observando-se que:")
        return (len(a) == 1 and a[0]["municipio"] == "Boa Vista da Aparecida" and a[0]["decreto_municipal"] == "235"
                and len(b) == 1 and b[0]["municipio"] == "Palmeira" and b[0]["decreto_municipal"] is None
                and c == [])

    def t6b():
        """§231: a ementa e o dispositivo do MESMO ato viram UMA entrada, com o número e o decreto
        estadual. Contar as duas produziu 54 atos e 54 pistas dos mesmos municípios na primeira
        varredura real — fila de revisão humana cheia de trabalho já feito."""
        real = ("Protocolo 129417/2026 DECRETO Nº 15.155 Homologa situação de emergência no "
                "Município de Cafezal do Sul, em face da ocorrência de Tempestade Local/Convectiva "
                "- Vendaval. O GOVERNADOR DO ESTADO DO PARANÁ, no uso das atribuições, DECRETA: "
                "Art. 1º Homologa o Decreto Municipal nº 242, de 22 de setembro de 2026, exarado "
                "pelo Prefeito de Cafezal do Sul, o qual declara Situação de Emergência.")
        r = homologacoes_no_texto(real)
        sp = homologacoes_no_texto(texto_da_publicacao_sp(json.dumps({"content": (
            "<p>DECRETO Nº 70.765, DE 24 DE JULHO DE 2026</p><p>Homologa, por 180 (cento e oi&shy;tenta) "
            "dias, o decreto do Pre&shy;feito do Munic&iacute;pio de Guariba, que declarou Situa&ccedil;"
            "&atilde;o de Emer&shy;g&ecirc;ncia em &aacute;reas do Munic&iacute;pio.</p><p>Artigo 1&ordm; - "
            "Fica homologado, por 180 (cento e oitenta) dias, o Decreto municipal n&ordm; 5.019, de 24 de "
            "julho de 2026, que declarou Situa&ccedil;&atilde;o de Emerg&ecirc;ncia.</p>")})))
        return (len(r) == 1 and r[0]["municipio"] == "Cafezal do Sul"
                and r[0]["decreto_municipal"] == "242" and r[0]["decreto_estadual"] == "15.155"
                and len(sp) == 1 and sp[0]["municipio"] == "Guariba"
                and sp[0]["decreto_municipal"] == "5.019" and sp[0]["decreto_estadual"] == "70.765")

    def t7():
        """Página indexada em ZERO, e para quando a página vem incompleta. Sem rede."""
        pedidos = []

        def falso(url, timeout=None):
            pedidos.append(url)
            return FIXTURE_APIFRONT if "/query/0/" in url else FIXTURE_APIFRONT_VAZIO

        total, acertos = varrer_busca_apifront("https://x.gov.br", "situação de emergência",
                                               "2026-09-01", "2026-09-26", buscar_fn=falso,
                                               dormir=lambda s: None)
        # dois acertos, total dois: para na primeira página, sem pedir a segunda
        return total == 2 and len(acertos) == 2 and len(pedidos) == 1 and "/query/0/" in pedidos[0]

    def t8():
        """§210 outra vez: total declarado com lista vazia é MUDANÇA DE CONTRATO, não ausência.

        Foi o que fez GO, ES, AP e MT parecerem sem resultado na primeira sonda — ali a causa era
        pedir a página 1 numa UF com menos de dez acertos. Se a fonte passar a responder assim na
        página zero, o coletor tem de LEVANTAR, e não gravar 'nada localizado'."""
        try:
            varrer_busca_apifront("https://x.gov.br", "t", "2026-09-01", "2026-09-26",
                                  buscar_fn=lambda u, timeout=None: FIXTURE_APIFRONT_TOTAL_SEM_LISTA,
                                  dormir=lambda s: None)
            return False
        except FormatoDaBuscaMudou:
            pass
        # e o zero honesto continua sendo zero
        total, acertos = varrer_busca_apifront("https://x.gov.br", "t", "2026-09-01", "2026-09-26",
                                               buscar_fn=lambda u, timeout=None: FIXTURE_APIFRONT_VAZIO,
                                               dormir=lambda s: None)
        return total == 0 and acertos == []

    def t9():
        """Estrutura ausente LEVANTA, em cada forma de perdê-la."""
        for corpo in (b"nao e json", b'{"outra":"coisa"}', b'{"hits":{}}',
                      b'{"hits":{"total":1}}', b'{"hits":{"total":"muitos","hits":[]}}',
                      b'{"hits":{"total":1,"hits":[{"_source":{}}]}}'):
            try:
                parse_busca_apifront(corpo)
                return False
            except FormatoDaBuscaMudou:
                pass
        return True

    def t10():
        """As seis UFs da plataforma nascem com adaptador e host; as outras 21 seguem a_verificar."""
        cfg = fontes_doe_padrao()["ufs"]
        seis = [u for u, v in cfg.items() if v["adaptador"] == "apifront"]
        return (sorted(seis) == sorted(HOSTS_APIFRONT)
                and all(cfg[u]["url"] == HOSTS_APIFRONT[u] for u in seis)
                and all(v["adaptador"] is None for u, v in cfg.items() if u not in HOSTS_APIFRONT)
                and all(v["status"] == "a_verificar" for v in cfg.values()))

    def t11():
        """O termo de busca não pode voltar a ter o artigo que o ato real não tem (§231)."""
        return ("homologa a situação de emergência" not in TERMOS
                and TERMOS_APIFRONT[0] == "situação de emergência")

    def t12():
        """§231: UF cujo adaptador NÃO pode funcionar não se registra como se pudesse.

        O AM roda a plataforma, mas a rota de busca dele devolve 404. Registrá-lo como `apifront`
        produziria doze lacunas falsas por dia, sobre um fato que não muda. Ele vive em
        APIFRONT_SEM_BUSCA, com o que foi medido e o caminho que resta."""
        cfg = fontes_doe_padrao()["ufs"]
        return (not (set(HOSTS_APIFRONT) & set(APIFRONT_SEM_BUSCA))
                and all(cfg[uf]["adaptador"] is None for uf in APIFRONT_SEM_BUSCA)
                and all(v.get("medido") and v.get("caminho") for v in APIFRONT_SEM_BUSCA.values()))

    return rodar_autoteste({"parser Querido Diário": t1, "extrai homologação com nº e município": t2,
                            "negativo: resposta vazia/nula": t3, "config nasce a_verificar nas 27 UFs": t4,
                            "§231 parser da busca da plataforma comum (recorte real)": t5,
                            "§231 as duas formas reais do ato, e o falso positivo que não casa": t6,
                            "§231 ementa e dispositivo do mesmo ato viram UMA entrada": t6b,
                            "§231 página indexada em zero, e para quando a página vem incompleta": t7,
                            "§231 total declarado com lista vazia LEVANTA (§210)": t8,
                            "§231 negativo: estrutura ausente levanta em toda forma": t9,
                            "§231 as seis UFs nascem com adaptador e host": t10,
                            "§231 o termo não volta a ter o artigo a mais": t11,
                            # DF — a API própria do DODF, lida da rota que o JS do sítio chama.
        "DODF: total e lista saem da resposta real":
            lambda: parse_dodf(FIXTURE_DODF)[0] == 7 and len(parse_dodf(FIXTURE_DODF)[1]) == 1,
        "DODF: total declarado com lista vazia LEVANTA (§210)":
            lambda: _levanta(lambda: parse_dodf(
                json.dumps({"totalMaterias": 5, "listaMaterias": []}).encode("utf-8")),
                FormatoDaBuscaMudou),
        "DODF: zero declarado com lista vazia é zero, e não erro":
            lambda: parse_dodf(json.dumps({"totalMaterias": 0, "listaMaterias": []}).encode("utf-8")) == (0, []),
        "DODF: a marcação do termo sai do trecho, e o texto fica":
            lambda: ("<strong>" not in item_do_dodf(parse_dodf(FIXTURE_DODF)[1][0], "DF")["trechos"][0]
                     and "situação de emergência" in item_do_dodf(
                         parse_dodf(FIXTURE_DODF)[1][0], "DF")["trechos"][0]),
        "DODF: o item traz data, endereço citável da matéria e o órgão":
            lambda: (item_do_dodf(parse_dodf(FIXTURE_DODF)[1][0], "DF")["data"] == "2026-09-11"
                     and "co_data=627377" in item_do_dodf(parse_dodf(FIXTURE_DODF)[1][0], "DF")["url"]
                     and "Secretaria de Estado de Saúde" in item_do_dodf(
                         parse_dodf(FIXTURE_DODF)[1][0], "DF")["trechos"][0]),
        # Página inventada é pior do que página ausente: o DODF indexa por matéria.
        "DODF: não inventa número de página":
            lambda: item_do_dodf(parse_dodf(FIXTURE_DODF)[1][0], "DF")["pagina"] is None,
        # TO — a busca aponta a edição; o trecho vem do PDF dela.
        "DOE-TO: a tabela entrega edição, data em ISO e endereço do PDF":
            lambda: parse_busca_to(FIXTURE_BUSCA_TO) == [
                {"edicao": "7154", "data": "2026-09-30",
                 "url": "https://doe.to.gov.br/diario/5793/download"},
                {"edicao": "7153", "data": "2026-09-29",
                 "url": "https://doe.to.gov.br/diario/5792/download"}],
        "DOE-TO: cabeçalho da tabela não vira resultado":
            lambda: all(r["edicao"] for r in parse_busca_to(FIXTURE_BUSCA_TO)),
        "DOE-TO: página sem a tabela não produz resultado, e não quebra":
            lambda: parse_busca_to("<html>nada aqui</html>") == [] and parse_busca_to("") == [],
        "DOE-AC: a tabela entrega número, data em ISO e PDF":
            lambda: parse_busca_ac(FIXTURE_BUSCA_AC) == [
                {"edicao": "14372", "data": "2026-10-14",
                 "url": "https://diario.ac.gov.br/download.php?arquivo=KEQxQHI3IyEpRE8xNzkxOTgyNTkyMjMxMy5wZGY="},
                {"edicao": "14100", "data": "2026-08-20",
                 "url": "https://diario.ac.gov.br/download.php?arquivo=QUJD"}],
        "DOE-AC: só edição da janela desce ao PDF, e a que não baixa fica contada":
            lambda: itens_por_busca("AC", "2026-09-01", lambda t: parse_busca_ac(FIXTURE_BUSCA_AC), termos=["x"],
                                    buscar_fn=lambda u, **k: (_ for _ in ()).throw(OSError(u)),
                                    dormir=lambda s: None) == ([], {"x": 1, "_nao_baixadas": 1}),
        "DOE-AC: recusa no PDF da edição levanta, não se pula":
            lambda: _levanta(lambda: itens_por_busca("AC", "2026-09-01", lambda t: parse_busca_ac(FIXTURE_BUSCA_AC),
                                                     termos=["x"], buscar_fn=lambda u, **k: (_ for _ in ()).throw(_erro_http(u, 403)),
                                                     dormir=lambda s: None), Exception),
        "DOE-TO: só as páginas do PDF em que o termo aparece entram":
            lambda: paginas_com_termo(b"x", "emergência",
                                      extrair_fn=lambda _: ["nada", "SITUAÇÃO DE EMERGÊNCIA aqui",
                                                            "outra coisa"]) == [
                (2, "SITUAÇÃO DE EMERGÊNCIA aqui")],
        "DOE-TO: PDF sem o termo não produz página":
            lambda: paginas_com_termo(b"x", "emergência", extrair_fn=lambda _: ["a", "b"]) == [],
        # Edição por data (CE, PB) — sem busca, lê-se a edição; só a página com termo vira item.
        "edição por data: a tupla de termos acha a página que casa com qualquer um":
            lambda: paginas_com_termo(b"x", ("emergência", "calamidade"),
                                      extrair_fn=lambda _: ["a", "estado de CALAMIDADE pública", "b"]) == [
                (2, "estado de CALAMIDADE pública")],
        "edição por data: só a data da janela ainda não lida desce ao PDF; 404 é data sem edição; "
        "data lida não se relê e a antiga sai de `lidas`": _t_edicao_por_data,
        "DOE-CE: os cadernos do dia vão até o primeiro 300/404": _t_cadernos_ce,
        "edição por data: arquivo que não é uma edição em PDF LEVANTA (§210)":
            lambda: _levanta(lambda: itens_por_edicao(
                "PB", "2026-10-14", "2026-10-14", lambda d: [{"edicao": None, "url": "u"}], {},
                buscar_fn=lambda u, **k: b"<html>pagina de erro</html>", dormir=lambda s: None), FormatoDaBuscaMudou),
        "DOE-AM: a rota (a) dá número e id; o PDF é a rota (c) pelo id; dia sem edição é lista vazia":
            lambda: (edicoes_apifront(lambda u, **k: FIXTURE_EDICOES_AM, "https://x.am.gov.br/")("2026-10-13") == [
                        {"edicao": "35804", "url": "https://x.am.gov.br/portal/edicoes/download/18246"}]
                     and edicoes_apifront(lambda u, **k: FIXTURE_EDICOES_AM_VAZIO, "https://x.am.gov.br")("2026-10-14") == []
                     and _levanta(lambda: edicoes_apifront(lambda u, **k: b'{"outra": 1}', "https://x")("2026-10-14"),
                                  FormatoDaBuscaMudou)),
        "DOE-MS: a listagem dá o PDF por data, suplemento incluído; dia fora dela é lista vazia":
            lambda: (edicoes_ms_na_listagem(FIXTURE_LISTAGEM_MS) == {
                        "2026-10-08": [{"edicao": "12302", "url": "https://assets.imprensaoficial.ms.gov.br/public/prd/Diario%20Oficial/2026/10/08/DO12302_08_10_2026.pdf"},
                                       {"edicao": "12302", "url": "https://assets.imprensaoficial.ms.gov.br/public/prd/Diario%20Oficial/2026/10/08/DO12302_08_10_2026_SUP_1.pdf"}],
                        "2026-10-13": [{"edicao": "12304", "url": "https://assets.imprensaoficial.ms.gov.br/public/prd/Diario%20Oficial/2026/10/13/DO12304_13_10_2026.pdf"},
                                       {"edicao": "12305", "url": "https://assets.imprensaoficial.ms.gov.br/public/prd/Diario%20Oficial/2026/10/13/DO12305_13_10_2026.pdf"}]}
                     and edicoes_ms(lambda u, **k: FIXTURE_LISTAGEM_MS.encode("utf-8"))("2026-10-09") == []
                     and _levanta(lambda: edicoes_ms(lambda u, **k: b"<html>nada</html>")("2026-10-09"), FormatoDaBuscaMudou)),
        # SP — a API própria do DOE-SP: busca paginada e publicação inteira.
        "DOE-SP: total, itens e 'há próxima' saem da resposta real; total sem lista LEVANTA (§210)":
            lambda: (parse_busca_sp(FIXTURE_BUSCA_SP)[0] == 1 and len(parse_busca_sp(FIXTURE_BUSCA_SP)[1]) == 1
                     and parse_busca_sp(FIXTURE_BUSCA_SP)[2] is False
                     and _levanta(lambda: parse_busca_sp(b'{"items": [], "totalItems": 5}'), FormatoDaBuscaMudou)
                     and _levanta(lambda: parse_busca_sp(b'{"outra": 1}'), FormatoDaBuscaMudou)
                     and parse_busca_sp(b'{"items": [], "totalItems": 0}') == (0, [], False)),
        "DOE-SP: o texto da publicação sai sem HTML, estilo e título do SEI":
            lambda: (texto_da_publicacao_sp(FIXTURE_PUBLICACAO_SP).startswith("bem como o Decreto nº 70.765")
                     and "font-size" not in texto_da_publicacao_sp(FIXTURE_PUBLICACAO_SP)
                     and "<" not in texto_da_publicacao_sp(FIXTURE_PUBLICACAO_SP)),
        "DOE-SP: cada publicação é lida uma vez, com data, endereço citável e texto; dois termos não dobram":
            lambda: (lambda r: len(r[0]) == 1 and r[0][0]["data"] == "2026-10-05"
                     and r[0][0]["url"] == "https://doe.sp.gov.br/executivo/casa-civil/despacho-do-secretario-de-2-de-outubro-de-2026-20261002111012042179446"
                     and "homologou o decreto do Prefeito de Guariba" in r[0][0]["trechos"][0]
                     and r[1] == {"a": 1, "b": 1})(
                itens_sp("SP", "2026-10-01", "2026-10-15", termos=["a", "b"], dormir=lambda s: None,
                         buscar_fn=lambda u, **k: FIXTURE_PUBLICACAO_SP if "/publications/" in u else FIXTURE_BUSCA_SP)),
        "DOE-PI: a listagem do dia dá edição e suplementar com o PDF; dia sem edição é vazio; linha sem PDF LEVANTA":
            lambda: (edicoes_pi(None, "https://www.diario.pi.gov.br/doe/", lambda u, d, **k: FIXTURE_LISTAGEM_PI)("2026-10-14") == [
                         {"edicao": "197/2026 SUPLEMENTAR", "url": "https://www.diario.pi.gov.br/doe/files/diarios/anexo/"
                          "d714cae0-47e5-4560-a789-ac9d636518ef/e2052f2e-6ed8-4bcb-b399-5f48c77567b3.pdf"},
                         {"edicao": "197/2026", "url": "https://www.diario.pi.gov.br/doe/files/diarios/anexo/"
                          "5cc561ff-8ff1-4435-a0a6-d8b59c3c6249/0d2588a1-8ba2-4926-a4f8-c2a257a45015.pdf"}]
                     and edicoes_pi(None, "https://x/doe", lambda u, d, **k: b'{"draw":1,"data":[]}')("2026-10-11") == []
                     and _levanta(lambda: edicoes_pi(None, "https://x/doe", lambda u, d, **k: b'{"data":[["sem link","1"]]}')("2026-10-14"), FormatoDaBuscaMudou)
                     and _levanta(lambda: edicoes_pi(None, "https://x/doe", lambda u, d, **k: b'{"erro":1}')("2026-10-14"), FormatoDaBuscaMudou)),
        "DOE-PB: o endereço da edição é o padrão do canal 2, preenchido pela data":
            lambda: edicoes_pb(None)("2026-10-14") == [{"edicao": None, "url":
                "https://auniao.pb.gov.br/servicos/doe/2026/outubro/diario-oficial-14-10-2026-portal.pdf"}],
        # TRAVA ESTRUTURAL: este coletor escreve em atos_resposta, pistas_doe e fontes_doe, e em
        # nada mais. O teste confere o que ele PODE fazer, não só o que ele fez nesta versão.
        "o fonte não grava em nenhum arquivo do banco":
            lambda: not any(f'gravar("{nome}' in fonte_do_coletor() for nome in BANCO_PROIBIDO),
        "a lista proibida é a canônica do projeto, com os cinco arquivos":
            lambda: set(BANCO_PROIBIDO) == {"estados.json", "saude_uf.json", "municipios.json",
                                            "indice.json", "monitor_saude.json"},
        "§231 UF sem rota de busca não se registra como apifront": t12})


if __name__ == "__main__":
    if "--autoteste" in sys.argv:
        sys.exit(autoteste())
    cfg = ler("fontes_doe.json", None) or fontes_doe_padrao()
    desde = sys.argv[sys.argv.index("--desde") + 1] if "--desde" in sys.argv else "2026-06-29"
    if "--uf" in sys.argv:
        ufs = [sys.argv[sys.argv.index("--uf") + 1].upper()]
    elif "--regiao" in sys.argv:
        ufs = REGIOES[sys.argv[sys.argv.index("--regiao") + 1].upper()].split()
    else:
        ufs = [u for r in REGIOES.values() for u in r.split()]
    # §212 (25/09/2026): `marcar_fato_municipal` e `marcar_fonte_consultada` leem e regravam o
    # livro de fontes (12 MB) a cada município. Hoje nenhum DOE tem adaptador confirmado e o laço
    # não chega lá — o lote entra agora justamente para que, no dia em que chegar, a varredura
    # não descubra o problema com 27 UFs de municípios na fila.
    abrir_lote_log(); abrir_lote_livro()
    try:
        res = {u: coletar_uf(u, desde, cfg) for u in ufs}
    finally:
        fechar_lote_log(); fechar_lote_livro()
    gravar("fontes_doe.json", cfg)
    # Item B do handover da auditoria do funil (27/09/2026): a rodada conta por etapa, para que
    # "está encontrando?" se responda sem abrir o código. Contagem não decide nada.
    funil.registrar("doe", ufs_consultadas=len(ufs),
                    ufs_com_resultado=sum(1 for r in res.values() if r))
    print("DOE:", ", ".join(f"{u}={r}" for u, r in res.items()))
    sys.exit(0)
