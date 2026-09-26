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
`{"adaptador": "querido_diario"|"direto"|null, "url": ..., "status": ...}`.
UF sem adaptador confirmado → lacuna declarada (nunca inferida). Em 02/09/2026
todas as 27 nascem `a_verificar`; a Action preenche o status ao tentar.

USO
  python coletar_doe.py --autoteste
  python coletar_doe.py --regiao NE            # lote por região (§13: NE, N, CO, SE, S)
  python coletar_doe.py --uf SC --desde 2026-06-29
"""
import json, re, sys, time, urllib.parse
from datetime import date
from coletores_base import (buscar, preservar_evidencia, preservar_texto_integral, log_busca, registrar_lacuna,
                            marcar_fonte_consultada, marcar_fato_municipal, referencia_ibge,
                            abrir_lote_log, fechar_lote_log, abrir_lote_livro, fechar_lote_livro,
                            ler, gravar, rodar_autoteste, eh_suspensao_defeso, hoje_editorial)

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
APIFRONT_SEM_BUSCA = {
    "AM": {"url": "https://diario.imprensaoficial.am.gov.br",
           "medido": "26/09/2026: /apifront e /portal/edicoes/download respondem; "
                     "/busca/busca/buscar devolve HTTP 404 (a busca é outro aplicativo)",
           "caminho": "edições por data (rota a) + leitura do PDF da edição (rota c)"},
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
    for m in PADRAO_HOMOLOGA.finditer(texto):
        juntar(m.group(2), m.group(1), m.start())
    return list(por_municipio.values())


def itens_apifront(uf: str, base: str, desde: str, ate: str, buscar_fn=None, pausa: float = RITMO_APIFRONT_S) -> tuple:
    """(itens no formato comum do coletor, total declarado por termo). Não grava nada."""
    itens, totais = [], {}
    for termo in TERMOS_APIFRONT:
        total, acertos = varrer_busca_apifront(base, termo, desde, ate, buscar_fn=buscar_fn, pausa=pausa)
        totais[termo] = total
        for a in acertos:
            itens.append({"data": a["data"], "pagina": a["pagina"], "paginas": a["paginas"],
                          "url": PDF_APIFRONT.format(base=base.rstrip("/"), diario_id=a["diario_id"]),
                          "trechos": [a["conteudo"]], "territorio": uf})
    return itens, totais


def iso_para_br(s: str) -> str:
    try:
        y, m, d = s[:10].split("-"); return f"{d}/{m}/{y}"
    except ValueError:
        return s


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
            registrar_lacuna(f"DOE/{uf}", "adaptador não confirmado (a_verificar)", canal="repositorio_estadual",
                             camada=1, uf=uf)
        f["status"] = "a_verificar"; return "lacuna"
    if f["adaptador"] == "apifront":
        # §231: a plataforma comum a seis UFs. A janela vai de `desde` até hoje, e a busca entrega
        # o TEXTO INTEGRAL da página que casou — por isso não há teto de 20 kB aqui e não se baixa
        # um PDF de dez megabytes por acerto para depois procurar dentro dele.
        url = f["url"]
        try:
            itens, totais = itens_apifront(uf, url, desde, hoje)
        except FormatoDaBuscaMudou as e:
            registrar_lacuna(f"DOE/{uf}", f"formato da busca mudou: {e}", canal="repositorio_estadual",
                             camada=1, uf=uf, strings=[url])
            f["status"] = "erro: formato"; return "erro"
        except Exception as e:  # noqa: BLE001
            registrar_lacuna(f"DOE/{uf}", f"{type(e).__name__}: {e}", canal="repositorio_estadual",
                             camada=1, uf=uf, strings=[url])
            f["status"] = f"erro: {type(e).__name__}"; return "erro"
        # A evidência é o conjunto de páginas como a BUSCA OFICIAL DO ESTADO as serviu, com a URL
        # do PDF da edição e o número da página em cada uma — quem confere abre o PDF e vai à
        # página. Preservar o PDF inteiro de cada acerto passaria de meio gigabyte por varredura e
        # não acrescentaria prova: o texto é o mesmo, e a origem fica citável do mesmo jeito.
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
            pistas["itens"].append({**hm, "motivo": "sem número do decreto ou município não casou com IBGE",
                                    "hash_evidencia": h, "registrado_em": hoje_editorial().isoformat()}); pist += 1
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
    gravar("atos_resposta.json", atos); gravar("pistas_doe.json", pistas)
    ibges_uf = [c for c, r in por_cod.items() if r["uf"] == uf]
    marcar_fonte_consultada(ibges_uf, f"DOE/{uf}", "estadual", resultado=f"{len(itens)} edição(ões)/trecho(s)")
    log_busca("repositorio_estadual", 1, TERMOS[:4], "registro" if novos else "pista", uf=uf, nivel="estadual",
              n_resultados=len(itens), resultados=f"{len(homol)} homologações, {novos} novas, {pist} pistas", hash_evidencia=h)
    f["status"] = "ok"; return "ok"


FIXTURE_QD = {"total_gazettes": 1, "gazettes": [{"territory_id": "42", "date": "2026-08-31", "url": "https://x/doe.pdf",
              "excerpts": ["DECRETO Nº 5.000 — Homologa o Decreto Municipal nº 123/2026 que declara situação de emergência no Município de Blumenau - SC."]}]}


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
        return (len(r) == 1 and r[0]["municipio"] == "Cafezal do Sul"
                and r[0]["decreto_municipal"] == "242" and r[0]["decreto_estadual"] == "15.155")

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
    print("DOE:", ", ".join(f"{u}={r}" for u, r in res.items()))
    sys.exit(0)
