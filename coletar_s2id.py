#!/usr/bin/env python3
"""
coletar_s2id.py
===============
Reconhecimentos FEDERAIS de situação de emergência/calamidade (portarias da
SEDEC/MIDR publicadas no DOU; base S2iD), do ciclo 2026/2027.
ESTATUTO (doc de redesenho §3.2, §4): atos de RESPOSTA — peso zero, sempre.
Alimentam `data/atos_resposta.json` (camada própria, fonte "DOU" ou "S2iD"),
o livro de fontes consultadas (nível "nacional" para TODOS os municípios quando
a fonte de abrangência nacional é consultada com sucesso) e o fato binário
`decreto_reconhecido`.

Endpoints (§15 — "a verificar"):
  - S2iD (s2id.mi.gov.br): sem API pública confirmada em 02/09/2026 →
    status `a_verificar`; nada é coletado dele até a confirmação.
  - DOU (in.gov.br/consulta): busca textual por "reconhece a situação de
    emergência" no período; o resultado vem num JSON embutido no HTML.
    Parser provado por fixture (--autoteste); a primeira coleta real é da Action.

USO
  python coletar_s2id.py --autoteste
  python coletar_s2id.py --desde 2026-06-29        # coleta (precisa de rede)
"""
import html as _html, json, re, sys, time, urllib.parse
from datetime import date
from coletores_base import (buscar, preservar_evidencia, log_busca, registrar_lacuna,
                            marcar_fonte_consultada, marcar_fato_municipal, referencia_ibge,
                            ler, gravar, rodar_autoteste, eh_suspensao_defeso, sha256,
                            parse_busca_dou, varrer_busca_dou, FormatoDoDOUMudou, RAIZ,
                            abrir_lote_log, fechar_lote_log, abrir_lote_livro, fechar_lote_livro)

FONTES = {
    "s2id": {"nome": "S2iD — Sistema Integrado de Informações sobre Desastres", "url": None,
             "status": "a_verificar", "nota": "sem API pública confirmada (§15)"},
    "dou": {"nome": "DOU — portarias SEDEC de reconhecimento",
            "url": "https://www.in.gov.br/consulta/-/buscar/dou?q={q}&s=do1&exactDate=personalizado&sortType=0&publishFrom={de}&publishTo={ate}",
            "status": "parser_provado_por_fixture"},
}
RITMO_S = 2.0        # §11: no máximo uma requisição a cada 2 s por domínio
COBRADE_CICLO = ("1.4.1", "1.4.2", "1.3.2", "1.3.1", "1.2.1", "1.2.2", "1.2.3", "2.4.1", "2.4.2")
PADRAO_TITULO = re.compile(r"PORTARIA\s+(?:SEDEC/MIDR\s+)?N[ºo°]\s*([\d\.]+),?\s+DE\s+(\d{1,2})\s+DE\s+([A-ZÇ]+)\s+DE\s+(\d{4})", re.I)
MESES = {m: i + 1 for i, m in enumerate("janeiro fevereiro março abril maio junho julho agosto setembro outubro novembro dezembro".split())}
PADRAO_MUN = re.compile(r"Munic[íi]pio de ([^\-–,;\.]+?)\s*-\s*([A-Z]{2})", re.I)
# 24/09/2026: quem reconhece situação de emergência de município é a SEDEC (Lei 12.608; Decreto
# 10.593, art. 20). O órgão vem declarado pela própria busca do DOU, então o rótulo
# "Portaria SEDEC/MIDR nº N" deixou de ser afirmação nossa e passou a ser o que a fonte diz —
# e ato de outro órgão que apenas casa com a mesma expressão não vira reconhecimento federal.
# Órgão que a fonte não declarou é lido, nunca descartado: silêncio da fonte não é filtro.
ORGAO_QUE_RECONHECE = re.compile(r"Prote[çc][ãa]o e Defesa Civil", re.I)


def e_do_orgao_que_reconhece(item: dict) -> bool:
    """O ato é de quem tem competência para reconhecer? Função pura."""
    orgao = (item.get("orgao") or "").strip()
    return (not orgao) or bool(ORGAO_QUE_RECONHECE.search(orgao))


def parse_dou_html(texto: str) -> list:
    """Resultados da consulta do DOU, no formato deste coletor ({..., conteudo}).

    24/09/2026: o leitor passou a ser o de `coletores_base` — o DOU trocou o <input value="">
    por um <script type="application/json"> e a cópia local devolvia lista vazia, calada, para
    toda consulta. Ausência do elemento agora LEVANTA (FormatoDoDOUMudou), nunca devolve zero.
    `conteudo` é EXCERTO (≈235 caracteres) e não serve para extrair município: quem precisa do
    ato inteiro abre `url`. Função pura."""
    return [{**it, "conteudo": it.get("trecho", "")} for it in parse_busca_dou(texto)]


# 24/09/2026: a portaria moderna não diz "Município de X - UF" em prosa — traz uma TABELA
# (UF | Município | Desastre | Decreto | Data | Processo), que é dado melhor do que a prosa:
# vem com o número e a data do decreto MUNICIPAL. Colunas casadas pelo CABEÇALHO, nunca pela
# posição, porque ordem de coluna é decisão da fonte e muda sem aviso.
_CAB_TABELA = {"uf": "uf", "município": "municipio", "municipio": "municipio", "desastre": "desastre",
               "decreto": "decreto", "data": "data", "processo": "processo"}


def _celulas(linha_html: str) -> list:
    return [re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", c))).strip()
            for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", linha_html, flags=re.S | re.I)]


def parse_tabela_portaria_dou(html_txt: str) -> list:
    """Da tabela da portaria: [{uf, municipio, desastre, decreto, data, processo}]. Função pura.

    Só entra linha com UF de duas letras e nome de município — cabeçalho, linha vazia e
    rodapé ficam de fora. Tabela sem a coluna 'Município' é ignorada (é outra tabela)."""
    saida = []
    for tabela in re.findall(r"<table[^>]*>(.*?)</table>", html_txt, flags=re.S | re.I):
        linhas = re.findall(r"<tr[^>]*>(.*?)</tr>", tabela, flags=re.S | re.I)
        mapa = None
        for linha in linhas:
            cels = _celulas(linha)
            if mapa is None:
                chaves = [_CAB_TABELA.get(c.lower()) for c in cels]
                if "municipio" in chaves and "uf" in chaves:
                    mapa = chaves
                continue
            if len(cels) != len(mapa):
                continue
            reg = {k: v for k, v in zip(mapa, cels) if k}
            uf, mun = reg.get("uf", ""), reg.get("municipio", "")
            if re.fullmatch(r"[A-Z]{2}", uf) and mun and not mun.lower().startswith("munic"):
                saida.append(reg)
    return saida


def extrair_reconhecimentos(resultados: list, ler_ato=None, falhas=None) -> list:
    """De cada portaria, extrai (número, data, município, UF). Só entra o que tem
    número E data E município — citação completa como condição de entrada (§3.3).

    `ler_ato(url) -> str` (opcional) abre a página do ato quando o excerto da busca não
    nomeia município, que desde este ciclo é o caso normal. `falhas` (opcional) é a lista onde
    os atos que NÃO puderam ser abertos são anotados: descartá-los em silêncio transformaria
    falha de rede em ausência de reconhecimento, que é exatamente o que este projeto não faz."""
    saida = []
    for r in resultados:
        if not e_do_orgao_que_reconhece(r):
            continue
        t = PADRAO_TITULO.search(r["titulo"] or "")
        if not t:
            continue
        numero, dia, mes, ano = t.groups()
        try:
            data_iso = date(int(ano), MESES[mes.lower()], int(dia)).strftime("%d/%m/%Y")
        except (KeyError, ValueError):
            continue
        # `conteudo` é o nome deste coletor; `trecho`, o do leitor compartilhado. A função aceita
        # os dois porque é chamada dos dois lados — do parser local e da varredura por janela.
        excerto = r.get("conteudo") or r.get("trecho") or ""
        achados = [{"municipio": n.strip(), "uf": uf.upper()} for n, uf in PADRAO_MUN.findall(excerto)]
        # 24/09/2026: o excerto da busca (≈235 caracteres) nunca chega ao município — o ato é
        # que diz quem foi reconhecido, e desde este ciclo ele diz numa tabela. Sem `ler_ato`
        # a função continua pura e devolve o que o excerto der; com ele, lê o ato.
        if not achados and ler_ato:
            try:
                pagina = ler_ato(r["url"])
            except Exception as e:  # noqa: BLE001 — falha de rede não é ausência de reconhecimento
                if falhas is not None:
                    falhas.append({"url": r["url"], "titulo": (r.get("titulo") or "")[:120],
                                   "erro": type(e).__name__})
                continue
            for linha in parse_tabela_portaria_dou(pagina):
                achados.append({"municipio": linha.get("municipio", "").strip(), "uf": linha.get("uf", "").upper(),
                                "decreto_municipal": linha.get("decreto") or None,
                                "data_decreto_municipal": linha.get("data") or None,
                                "desastre": linha.get("desastre") or None})
            for n, uf in parse_portaria_dou(pagina):      # atos antigos, em prosa
                if not any(a["municipio"] == n and a["uf"] == uf for a in achados):
                    achados.append({"municipio": n, "uf": uf})
        for a in achados:
            if not a["municipio"] or not re.fullmatch(r"[A-Z]{2}", a["uf"] or ""):
                continue
            saida.append({"portaria": f"Portaria SEDEC/MIDR nº {numero}", "data": data_iso,
                          "url": r["url"], **a})
    return saida


RSS_MIDR = "https://www.gov.br/mdr/pt-br/noticias-midr/RSS"
# 03/09/2026: a pasta antiga (/noticias/RSS, que o rodapé do sítio ainda aponta) passou a exigir login
# ("Conteúdo Restrito"); as notícias vivem em /noticias-midr. Se o RSS dessa pasta também não vier como
# XML, lê-se a LISTAGEM HTML da pasta (2 páginas) — e resposta sem <item>/<h2> é lacuna declarada, nunca "0 notícias".
LISTAGEM_MIDR = ["https://www.gov.br/mdr/pt-br/noticias-midr", "https://www.gov.br/mdr/pt-br/noticias-midr?b_start:int=30"]
ESTADOS = {"acre": "AC", "alagoas": "AL", "amazonas": "AM", "amapá": "AP", "bahia": "BA", "ceará": "CE", "distrito federal": "DF", "espírito santo": "ES",
           "goiás": "GO", "maranhão": "MA", "minas gerais": "MG", "mato grosso do sul": "MS", "mato grosso": "MT", "pará": "PA", "paraíba": "PB", "pernambuco": "PE",
           "piauí": "PI", "paraná": "PR", "rio de janeiro": "RJ", "rio grande do norte": "RN", "rondônia": "RO", "roraima": "RR", "rio grande do sul": "RS",
           "santa catarina": "SC", "sergipe": "SE", "são paulo": "SP", "tocantins": "TO"}
PADRAO_SLUG = re.compile(r"/portaria-n-([\d.]+)-de-(\d{1,2})-de-([a-z]+)-de-(\d{4})-\d+", re.I)


def parse_rss_midr(xml: str) -> list:
    """Itens do RSS do MIDR cujo título fala de reconhecimento: [{titulo, link, data}]. Função pura."""
    out = []
    for it in re.findall(r"<item>(.*?)</item>", xml, flags=re.S):
        t = re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", it, flags=re.S); l = re.search(r"<link>(.*?)</link>", it, flags=re.S); d = re.search(r"<(?:pubDate|dc:date)>(.*?)</", it)
        if t and l and re.search(r"reconhec", t.group(1), re.I):
            out.append({"titulo": _html.unescape(t.group(1).strip()), "link": l.group(1).strip(), "data": (d.group(1).strip() if d else "")})
    return out


def parse_listagem_midr(html_txt: str) -> list:
    """Itens da listagem HTML de /noticias-midr cujo título fala de reconhecimento: [{titulo, link, data}]. Função pura.
    Cada item: <h2><a href="…/noticias-midr/slug">Título</a></h2> … dd/mm/aaaa - subtítulo."""
    out = []
    for m in re.finditer(r'<h2[^>]*>\s*<a[^>]+href="([^"]+/noticias-midr/[^"]+)"[^>]*>(.*?)</a>\s*</h2>(.{0,2500}?)(\d{2}/\d{2}/\d{4})', html_txt, flags=re.S | re.I):
        link, tit, _, data = m.groups(); tit = _html.unescape(re.sub(r"<[^>]+>", "", tit)).strip()
        if re.search(r"reconhec", tit, re.I):
            out.append({"titulo": tit, "link": link.strip(), "data": data})
    return out


def eh_xml_rss(texto: str) -> bool:
    """Resposta é mesmo um feed (tem <item>), e não uma página HTML/login."""
    return bool(re.search(r"<item[ >]", texto)) and "<rss" in texto[:2000].lower() + texto[:2000]


def parse_noticia_midr(html_txt: str) -> dict:
    """Da notícia do MIDR: links de portarias no DOU (número + data no endereço) e pares município/UF do texto."""
    texto = re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", html_txt)))
    portarias = []
    for m in PADRAO_SLUG.finditer(html_txt):
        numero, dia, mes, ano = m.groups()
        try: data_iso = date(int(ano), MESES[mes.lower()], int(dia)).strftime("%d/%m/%Y")
        except (KeyError, ValueError): continue
        url = re.search(r"https?://[^\s\"']*" + re.escape(m.group(0)), html_txt)
        portarias.append({"numero": numero, "data": data_iso, "url": (url.group(0) if url else "https://www.in.gov.br/web/dou/-" + m.group(0).split("/web/dou/-")[-1])})
    # município/UF: segmentos "A, B e C, na Bahia" / "a cidade de X, no Amazonas" / "X, em Santa Catarina"
    pares = []
    for seg in re.split(r"[;.]", texto):
        seg = seg.strip()
        ms = list(re.finditer(r",\s+(?:n[oa]s?|em)\s+([A-ZÁÉÍÓÚÃÕÇ][\wÀ-ÿ ]+?)(?=[,.]|$|\s+(?:e |obteve|enfrenta|passa|por |que ))", seg))
        if not ms: continue
        m = ms[0]; uf = ESTADOS.get(m.group(1).strip().lower())
        if not uf: continue
        lista = seg[:m.start()]
        lista = re.sub(r"^.*?(?:munic[íi]pios?(?: de)?|cidades?(?: de)?|cidade de|o munic[íi]pio de)\s+", "", lista, flags=re.I)
        lista = re.sub(r"^(?:Já|Enquanto|E|Foram castigad[oa]s por fortes chuvas as|Passam por um período de estiagem os)\s+", "", lista.strip(), flags=re.I)
        for nome in re.split(r",\s*|\s+e\s+", lista):
            nome = re.sub(r"^(?:[a-záéíóúãõçà-ÿ0-9]+\s+)+", "", nome.strip())  # remove palavras minúsculas iniciais ("enquanto", "os")
            if nome and nome[0].isupper() and 2 < len(nome) < 60 and not re.search(r"\b(reconhecimento|situação|estiagem|chuvas|Portaria)\b", nome, re.I): pares.append((nome, uf))
        # segmentos seguintes do mesmo período: "D, no Paraná, e Gentil e São Pedro do Sul, no Rio Grande do Sul"
        for k in range(1, len(ms)):
            uf2 = ESTADOS.get(ms[k].group(1).strip().lower())
            if not uf2: continue
            trecho = seg[ms[k-1].end():ms[k].start()]; trecho = re.sub(r"^[,\s]*(?:e\s+)?", "", trecho)
            for nome in re.split(r",\s*|\s+e\s+", trecho):
                nome = re.sub(r"^(?:[a-záéíóúãõçà-ÿ0-9]+\s+)+", "", nome.strip())
                if nome and nome[0].isupper() and 2 < len(nome) < 60 and not re.search(r"\b(reconhecimento|situação|estiagem|chuvas|Portaria)\b", nome, re.I): pares.append((nome, uf2))
    return {"portarias": portarias, "municipios": sorted(set(pares))}


def parse_portaria_dou(html_txt: str) -> list:
    """Da página da portaria no DOU: municípios nomeados ('Município de X - UF')."""
    texto = _html.unescape(re.sub(r"<[^>]+>", " ", html_txt))
    return sorted({(n.strip(), uf.upper()) for n, uf in PADRAO_MUN.findall(texto)})


def _norm(nome: str) -> str:
    import unicodedata
    n = unicodedata.normalize("NFKD", nome.replace("’", "'").replace("`", "'")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9' ]", "", n).strip()


def coletar_midr(por_cod, por_nome, atos, vistos, h_rss_ok) -> tuple:
    """Fonte principal (03/09/2026): RSS do MIDR → notícias de reconhecimento → portarias no DOU."""
    itens, h, origem = [], None, None
    try:
        bruto = buscar(RSS_MIDR); txt = bruto.decode("utf-8", "replace")
        if eh_xml_rss(txt):
            h = preservar_evidencia(bruto, RSS_MIDR, "xml", "coletar_s2id"); itens = parse_rss_midr(txt); origem = RSS_MIDR
        else:
            registrar_lacuna("MIDR — RSS de /noticias-midr", "resposta não é RSS (HTML/login); usando a listagem HTML", canal="DOU", camada=1, strings=[RSS_MIDR])
    except Exception as e:  # noqa: BLE001
        registrar_lacuna("MIDR — RSS de /noticias-midr", f"{type(e).__name__}: {e}; usando a listagem HTML", canal="DOU", camada=1, strings=[RSS_MIDR])
    if origem is None:
        paginas_ok = 0
        for url_l in LISTAGEM_MIDR:
            try:
                bl = buscar(url_l); tl = bl.decode("utf-8", "replace")
            except Exception as e:  # noqa: BLE001
                registrar_lacuna("MIDR — listagem de notícias", f"{type(e).__name__}: {e}", canal="DOU", camada=1, strings=[url_l]); continue
            if "noticias-midr/" not in tl or "<h2" not in tl:
                registrar_lacuna("MIDR — listagem de notícias", "página sem a estrutura de listagem (endpoint a verificar)", canal="DOU", camada=1, strings=[url_l]); continue
            hl = preservar_evidencia(bl, url_l, "html", "coletar_s2id"); h = h or hl; paginas_ok += 1
            itens += parse_listagem_midr(tl)
        if not paginas_ok:
            return 0, 0, False
        origem = LISTAGEM_MIDR[0]
    vistos_links = set(); itens = [i for i in itens if not (i["link"] in vistos_links or vistos_links.add(i["link"]))]
    por_norm = {(_norm(n), uf): cod for (n, uf), cod in por_nome.items()}  # casamento tolerante a acento/apóstrofo
    novos = total = 0
    for it in itens[:40]:
        try:
            pag = buscar(it["link"])
        except Exception as e:  # noqa: BLE001
            registrar_lacuna(f"MIDR notícia {it['link'][-40:]}", type(e).__name__, canal="DOU", camada=1, strings=[it["link"]]); continue
        hn = preservar_evidencia(pag, it["link"], "html", "coletar_s2id"); info = parse_noticia_midr(pag.decode("utf-8", "replace"))
        # mapeamento exato município↔portaria pela página da portaria no DOU; se falhar, o lote inteiro é citado
        mapa = {}
        for p in info["portarias"]:
            try:
                pp = buscar(p["url"]); hp = preservar_evidencia(pp, p["url"], "html", "coletar_s2id")
                _t = pp.decode("utf-8", "replace")
                # 24/09/2026: o ato moderno traz TABELA, não prosa — sem ler a tabela o mapa
                # ficava vazio e o lote inteiro era citado no lugar da portaria exata.
                for nome, uf in parse_portaria_dou(_t): mapa[(nome, uf)] = (p, hp)
                for linha in parse_tabela_portaria_dou(_t): mapa[(linha["municipio"], linha["uf"])] = (p, hp)
            except Exception:  # noqa: BLE001
                pass
        for nome, uf in info["municipios"]:
            cod = por_nome.get((nome, uf)) or por_norm.get((_norm(nome), uf)); total += 1
            if not cod:
                log_busca("DOU", 1, [it["link"]], "pista", resultados=f"MIDR: município não casou com IBGE: {nome}/{uf}", uf=uf, nivel="nacional", hash_evidencia=hn); continue
            p, hp = mapa.get((nome, uf)) or next((v for (n2, u2), v in mapa.items() if u2 == uf and _norm(n2) == _norm(nome)), (None, hn))
            if p: dec, dt, url = f"Portaria SEDEC/MIDR nº {p['numero']}", p["data"], p["url"]
            elif info["portarias"]: dec, dt, url = "Portaria SEDEC/MIDR (lote: " + ", ".join("nº " + x["numero"] for x in info["portarias"]) + ")", info["portarias"][0]["data"], it["link"]
            else: dec, dt, url = "Portaria SEDEC/MIDR (número na notícia do MIDR)", "", it["link"]
            ref = por_cod[cod]; chave = (ref["nome"], uf, dt, "reconhecimento federal")
            if chave in vistos: continue
            atos["eventos"].append({"nome": ref["nome"], "uf": uf, "ibge": cod, "data": dt or "", "causa": "reconhecimento federal", "decreto": dec,
                                    "data_reconhecimento": dt, "portaria": dec, "fonte": "DOU (portaria SEDEC/MIDR), via notícia do MIDR", "url": url,
                                    "lat": ref["lat"], "lon": ref["lon"], "canal": "DOU", "hash_evidencia": hp})
            marcar_fato_municipal(cod, "decreto_reconhecido", True); vistos.add(chave); novos += 1
    log_busca("DOU", 1, [origem], "registro" if novos else "pista", resultados=f"MIDR ({'RSS' if origem == RSS_MIDR else 'listagem HTML'}): {len(itens)} notícias de reconhecimento, {total} municípios lidos, {novos} novos",
              nivel="nacional", n_resultados=len(itens), hash_evidencia=h)
    return novos, total, bool(itens)


def coletar(desde: str, ate: str) -> int:
    # 25/09/2026 (§212), medido: a rodada ficou 53 minutos presa com a CPU em 100%, e não era
    # rede. Cada município reconhecido chamava `marcar_fato_municipal`, que lê e regrava o livro
    # de fontes — 12 MB —, e cada município sem casamento com o IBGE chamava `log_busca`, que faz
    # o mesmo com o log de 20 MB. São mais de 600 municípios em 136 portarias: horas de
    # serialização de JSON para gravar algumas centenas de campos. Com os lotes abertos, é uma
    # leitura e uma gravação de cada arquivo a cada 250 registros. O `finally` fecha os dois em
    # qualquer saída, inclusive nas antecipadas por lacuna.
    abrir_lote_log()
    abrir_lote_livro()
    try:
        return _coletar(desde, ate)
    finally:
        fechar_lote_log()
        fechar_lote_livro()


def _coletar(desde: str, ate: str) -> int:
    por_cod, por_nome = referencia_ibge()
    atos = ler("atos_resposta.json"); vistos = {(e["nome"], e["uf"], e["data"], e.get("causa")) for e in atos["eventos"]}
    novos_midr, lidos_midr, rss_ok = coletar_midr(por_cod, por_nome, atos, vistos, True)
    gravar("atos_resposta.json", atos)
    if rss_ok:
        marcar_fonte_consultada(list(por_cod), "DOU/SEDEC reconhecimentos (via MIDR)", "nacional", resultado=f"{lidos_midr} município(s) reconhecido(s) lidos nas notícias do MIDR")
        print(f"MIDR/DOU: {lidos_midr} reconhecimentos lidos, {novos_midr} novos em atos_resposta.json")
    # S2iD: lacuna declarada enquanto o endpoint não for confirmado
    registrar_lacuna(FONTES["s2id"]["nome"], FONTES["s2id"]["nota"], canal="DOU", camada=1)
    # 24/09/2026: a consulta passou a ser VARREDURA. A página devolve no máximo 50 por consulta e
    # não pagina (`start` é ignorado, medido); ler os 50 mais recentes de 132 e não dizer nada
    # seria apresentar recorte como varredura. `varrer_busca_dou` estreita a janela até caber e
    # devolve, à parte, as janelas que não couberam — que entram como lacuna declarada.
    consulta = '"reconhece a situação de emergência"'
    url = FONTES["dou"]["url"].format(q=urllib.parse.quote(consulta),
                                      de=date.fromisoformat(desde).strftime("%d-%m-%Y"),
                                      ate=date.fromisoformat(ate).strftime("%d-%m-%Y"))
    h = None
    paginas = []

    def _buscar_pagina(u):
        b = buscar(u); paginas.append((b, u)); return b

    try:
        resultados, incompletas = varrer_busca_dou(consulta, date.fromisoformat(desde),
                                                   date.fromisoformat(ate), buscar_fn=_buscar_pagina)
    except FormatoDoDOUMudou as e:
        # A página respondeu e não trouxe a estrutura de resultados: NÃO é consulta bem-sucedida.
        # Ninguém sobe de nível por leitura vazia, e zero aqui não é ausência de reconhecimento.
        if paginas:
            h = preservar_evidencia(paginas[-1][0], paginas[-1][1], "html", "coletar_s2id")
        registrar_lacuna(FONTES["dou"]["nome"], f"página sem a estrutura de resultados ({e}) — parser/endpoint a verificar",
                         canal="DOU", camada=1, strings=[url], hash_evidencia=h)
        return 0
    except Exception as e:  # noqa: BLE001
        registrar_lacuna(FONTES["dou"]["nome"], f"{type(e).__name__}: {e}", canal="DOU", camada=1, strings=[url])
        return 0
    for bruto, u in paginas:
        hp = preservar_evidencia(bruto, u, "html", "coletar_s2id"); h = h or hp
        if eh_suspensao_defeso(bruto.decode("utf-8", "replace")):
            registrar_lacuna(FONTES["dou"]["nome"], "página com aviso de período eleitoral", canal="DOU",
                             camada=1, strings=[u], suspensa=True, hash_evidencia=hp)
    for j in incompletas:
        registrar_lacuna(FONTES["dou"]["nome"], f"janela {j['de']} a {j['ate']} declara {j['total']} resultados e a página entrega {j['lidos']} — leitura parcial declarada",
                         canal="DOU", camada=1, strings=[url], hash_evidencia=h)

    def _ler_ato(u):
        time.sleep(RITMO_S)      # §11: no máximo uma requisição a cada 2 s por domínio
        b = buscar(u); preservar_evidencia(b, u, "html", "coletar_s2id")
        return b.decode("utf-8", "replace")

    falhas_de_ato = []
    itens = extrair_reconhecimentos(resultados, ler_ato=_ler_ato, falhas=falhas_de_ato)
    enriquecidos = set()
    for f in falhas_de_ato:
        registrar_lacuna(f"DOU — ato não aberto ({f['titulo'][:60]})", f"{f['erro']}; os municípios desta portaria não foram lidos",
                         canal="DOU", camada=1, strings=[f["url"]], hash_evidencia=h)
    novos = 0
    for it in itens:
        cod = por_nome.get((it["municipio"], it["uf"]))
        if not cod:
            log_busca("DOU", 1, [url], "pista", resultados=f"município não casou com IBGE: {it['municipio']}/{it['uf']}",
                      uf=it["uf"], nivel="nacional", hash_evidencia=h)
            continue
        ref = por_cod[cod]
        chave = (ref["nome"], it["uf"], it["data"], "reconhecimento federal")
        if chave in vistos:
            # 25/09/2026: o evento já está no banco pelo canal do MIDR, que chega antes — e a
            # primeira rodada com o canal do DOU consertado leu 618 reconhecimentos e criou ZERO,
            # o que é a melhor notícia possível (os dois canais independentes concordam). Só que
            # o ato traz o que a notícia do MIDR não tem: o número e a data do decreto MUNICIPAL
            # e a classe do desastre. Descartar isso seria jogar fora dado por causa do que já
            # sabíamos. O acréscimo é ADITIVO e sob a MESMA chave que já serve para deduplicar:
            # preenche campo ausente, nunca sobrescreve campo existente.
            for e in atos["eventos"]:
                if (e.get("nome"), e.get("uf"), e.get("data"), e.get("causa")) != chave:
                    continue
                for campo in ("decreto_municipal", "data_decreto_municipal", "desastre"):
                    if it.get(campo) and not e.get(campo):
                        e[campo] = it[campo]
                        enriquecidos.add(chave)
                break
            continue
        # `decreto`/`data` seguem sendo a PORTARIA e a data dela, como sempre foram; o decreto
        # MUNICIPAL que a tabela do ato passou a declarar entra em campo próprio, para não
        # mudar o significado de campo que o banco já usa.
        ev = {"nome": ref["nome"], "uf": it["uf"], "ibge": cod, "data": it["data"],
              "causa": "reconhecimento federal", "decreto": it["portaria"],
              "data_reconhecimento": it["data"], "portaria": it["portaria"],
              "fonte": "DOU (portaria SEDEC/MIDR)", "url": it["url"],
              "lat": ref["lat"], "lon": ref["lon"], "canal": "DOU",
              "hash_evidencia": h}
        for campo in ("decreto_municipal", "data_decreto_municipal", "desastre"):
            if it.get(campo):
                ev[campo] = it[campo]
        atos["eventos"].append(ev)
        marcar_fato_municipal(cod, "decreto_reconhecido", True)
        vistos.add(chave); novos += 1
    gravar("atos_resposta.json", atos)
    # (03/09/2026) a consulta textual do DOU é COMPLEMENTAR: não confere nível — o nível nacional vem do RSS do MIDR lido
    log_busca("DOU", 1, [url], "registro" if (novos or enriquecidos) else "pista",
              resultados=f"{len(itens)} itens, {novos} novos, {len(enriquecidos)} com decreto municipal acrescentado",
              nivel="nacional", n_resultados=len(itens), hash_evidencia=h)
    print(f"DOU: {len(itens)} reconhecimento(s) lidos, {novos} novo(s) e "
          f"{len(enriquecidos)} enriquecido(s) com o decreto municipal em atos_resposta.json")
    return 0


# Forma ANTIGA (<input value="...">): mantida porque a evidência preservada até 23/09/2026 está
# nela, e o leitor tem de continuar lendo o que já guardamos.
FIXTURE_HTML = ('<input id="_br_com_seatecnologia_in_buscadou_BuscaDouPortlet_params" type="hidden" value="'
                + _html.escape(json.dumps({"jsonArray": [
                    {"title": "PORTARIA SEDEC/MIDR Nº 2.659, DE 28 DE AGOSTO DE 2026", "urlTitle": "portaria-2659",
                     "pubDate": "29/08/2026", "content": "Reconhece a situação de emergência no Município de Blumenau - SC, afetado por chuvas intensas (COBRADE 1.3.2.1.4)."},
                    {"title": "AVISO DE LICITAÇÃO", "urlTitle": "x", "pubDate": "29/08/2026", "content": "nada"}]}), quote=True)
                + '"></input>')
# Forma de HOJE (24/09/2026): <script type="application/json">, título embrulhado em <span
# class="highlight"> e trecho de ~235 caracteres que NUNCA chega ao município.
FIXTURE_SCRIPT = ('<script id="_br_com_seatecnologia_in_buscadou_BuscaDouPortlet_params" type="application/json">'
                  + json.dumps({"jsonArray": [
                      {"title": "<span class='highlight'>PORTARIA</span> Nº 3.175, DE 23 DE SETEMBRO DE 2026",
                       "urlTitle": "portaria-n-3.175-de-23-de-setembro-de-2026-733736080", "pubDate": "24/09/2026",
                       "content": "resolve: Art. 1º Reconhecer ... a situação de emergência nas áreas descritas no Formulário de Informações do Desastre - FIDE, conforme",
                       "hierarchyStr": "Ministério da Integração e do Desenvolvimento Regional/Secretaria Nacional de Proteção e Defesa Civil"}]})
                  + '</script><p>132 resultados</p>')
# Ato de hoje: a tabela no lugar da prosa.
FIXTURE_ATO_TABELA = """<table class="dou-table"><tbody><tr></tr>
 <tr><td><p>UF</p></td><td><p>Munic&iacute;pio</p></td><td><p>Desastre</p></td><td><p>Decreto</p></td><td><p>Data</p></td><td><p>Processo</p></td></tr>
 <tr><td><p>SP</p></td><td><p>Juqui&aacute;</p></td><td><p>Chuvas Intensas - 1.3.2.1.4</p></td><td><p>2351</p></td><td><p>18/09/2026</p></td><td><p>59051.048293/2026-09</p></td></tr>
 <tr><td><p>SC</p></td><td><p>Blumenau</p></td><td><p>Estiagem - 1.4.1.1.0</p></td><td><p>77</p></td><td><p>12/09/2026</p></td><td><p>59051.000001/2026-11</p></td></tr>
</tbody></table>"""


FIX_RSS = """<rss><channel><item><title><![CDATA[MIDR reconhece a situação de emergência em 18 cidades afetadas por desastres]]></title><link>https://www.gov.br/mdr/pt-br/noticias/midr-reconhece-a-situacao-de-emergencia-em-18-cidades-afetadas-por-desastres-4</link><pubDate>Mon, 25 May 2026 13:54:00 GMT</pubDate></item><item><title>Açaí do Amapá conquista mercado chinês</title><link>https://www.gov.br/mdr/pt-br/noticias/acai</link></item></channel></rss>"""
FIX_NOTICIA = """<p><a href="http://www.in.gov.br/web/dou/-/portaria-n-1.723-de-22-de-maio-de-2026-707496193">Portaria n⁰ 1.723</a> <a href="http://www.in.gov.br/web/dou/-/portaria-n-1.724-de-22-de-maio-de-2026-707513635">Portaria nº 1.724</a></p>
<p>Passam por um período de estiagem os municípios Chorrochó e Tremedal, na Bahia; Barra de São Miguel, São Bento, Joca Claudino, Taperoá, Princesa Isabel e Manaíra, na Paraíba; Pérola D’Oeste, no Paraná, e Gentil e São Pedro do Sul, no Rio Grande do Sul. Já Alexandria, no Rio Grande do Norte, enfrenta a seca, que é um período de ausência de chuva mais prolongado do que a estiagem.</p>
<p>Foram castigadas por fortes chuvas as cidades de Parintins e Borba, no Amazonas; Godofredo Viana, no Maranhão, e Santa Izabel do Pará, no Pará.</p>
<p>O município de Careiro, no Amazonas, obteve o reconhecimento federal de situação de emergência por causa de alagamentos, enquanto Correia Pinto, em Santa Catarina, por subsidência e colapso.</p>"""
FIX_PORTARIA = "<article>PORTARIA Nº 1.723, DE 22 DE MAIO DE 2026 ... Reconhece a situação de emergência no Município de Chorrochó - BA, e no Município de Tremedal - BA, afetados por estiagem.</article>"


def autoteste() -> int:
    def t1():
        r = parse_dou_html(FIXTURE_HTML); return len(r) == 2 and r[0]["url"].endswith("portaria-2659")
    def t2():
        e = extrair_reconhecimentos(parse_dou_html(FIXTURE_HTML))
        return len(e) == 1 and e[0]["municipio"] == "Blumenau" and e[0]["uf"] == "SC" and e[0]["data"] == "28/08/2026"
    def t3():  # negativo: sem número de portaria → não entra
        e = extrair_reconhecimentos([{"titulo": "PORTARIA SEM NUMERO", "url": "", "data": "", "conteudo": "Município de X - SC"}])
        return e == []
    def t4():  # 24/09/2026: HTML sem a estrutura de resultados LEVANTA — nunca devolve zero.
        # Era o inverso, e foi o que escondeu a troca do <input> pelo <script>: a página
        # respondia, a lista vinha vazia, e 132 reconhecimentos reais viravam "não há".
        try:
            parse_dou_html("<html>vazio</html>")
        except FormatoDoDOUMudou:
            return True
        return False

    def t12():  # a forma de hoje é lida, com o título já sem a marcação de destaque
        r = parse_dou_html(FIXTURE_SCRIPT)
        return (len(r) == 1 and r[0]["titulo"] == "PORTARIA Nº 3.175, DE 23 DE SETEMBRO DE 2026"
                and r[0]["url"].endswith("733736080"))

    def t13():  # o excerto da busca não nomeia município: sem ler o ato, não se extrai nada
        return extrair_reconhecimentos(parse_dou_html(FIXTURE_SCRIPT)) == []

    def t14():  # lendo o ato, a tabela dá município, UF e o decreto MUNICIPAL
        e = extrair_reconhecimentos(parse_dou_html(FIXTURE_SCRIPT), ler_ato=lambda u: FIXTURE_ATO_TABELA)
        juquia = [x for x in e if x["municipio"] == "Juquiá"]
        return (len(e) == 2 and len(juquia) == 1 and juquia[0]["uf"] == "SP"
                and juquia[0]["decreto_municipal"] == "2351"
                and juquia[0]["data_decreto_municipal"] == "18/09/2026"
                and juquia[0]["portaria"] == "Portaria SEDEC/MIDR nº 3.175"
                and juquia[0]["data"] == "23/09/2026")

    def t21():
        """Acrescentar o decreto municipal a um evento que já existe é ADITIVO: preenche campo
        ausente e nunca sobrescreve o que o outro canal já tinha escrito."""
        e = {"nome": "Juquiá", "uf": "SP", "data": "23/09/2026", "causa": "reconhecimento federal",
             "decreto": "Portaria SEDEC/MIDR nº 3.175", "desastre": "já sabido"}
        it = {"decreto_municipal": "2351", "data_decreto_municipal": "18/09/2026", "desastre": "Chuvas Intensas"}
        for campo in ("decreto_municipal", "data_decreto_municipal", "desastre"):
            if it.get(campo) and not e.get(campo):
                e[campo] = it[campo]
        return (e["decreto_municipal"] == "2351" and e["data_decreto_municipal"] == "18/09/2026"
                and e["desastre"] == "já sabido" and e["decreto"] == "Portaria SEDEC/MIDR nº 3.175")

    def t19():
        """Trava estrutural: este coletor escreve em `atos_resposta.json` e em mais nada do
        banco — nem por `open()`, nem por `json.dump()`, nem por `gravar()`, que é a via real."""
        fonte = (RAIZ / "coletar_s2id.py").read_text(encoding="utf-8")
        for proibido in ["estados.json", "saude_uf.json", "municipios.json", "indice.json",
                         "monitor_saude.json", "resposta/por_uf.json"]:
            for padrao in (r'open\([^)]*' + re.escape(proibido) + r'[^)]*,\s*["\']([wa])',
                           r'json\.dump\([^,]*,\s*open\([^)]*' + re.escape(proibido),
                           r'gravar\(\s*["\'][^"\']*' + re.escape(proibido)):
                if re.search(padrao, fonte):
                    return False
        return True

    def t20():
        """Falha ao abrir o ato é ANOTADA, não descartada: sem isso, rede ruim se pareceria com
        portaria sem município — e o reconhecimento federal sumiria sem deixar rastro."""
        def cai(u):
            raise TimeoutError("rede")

        falhas = []
        r = extrair_reconhecimentos([{"titulo": "PORTARIA SEDEC/MIDR Nº 2.659, DE 28 DE AGOSTO DE 2026",
                                      "url": "u", "data": "29/08/2026", "trecho": "sem município aqui"}],
                                    ler_ato=cai, falhas=falhas)
        return r == [] and len(falhas) == 1 and falhas[0]["erro"] == "TimeoutError"

    def t18():  # ato de outro órgão não vira reconhecimento federal; órgão ausente é lido
        base = {"titulo": "PORTARIA SEDEC/MIDR Nº 2.659, DE 28 DE AGOSTO DE 2026", "url": "u",
                "data": "29/08/2026", "conteudo": "Município de Blumenau - SC"}
        sedec = {**base, "orgao": "Ministério da Integração e do Desenvolvimento Regional/Secretaria Nacional de Proteção e Defesa Civil"}
        tcu = {**base, "orgao": "Tribunal de Contas da União/2ª Câmara"}
        return (len(extrair_reconhecimentos([sedec])) == 1 and extrair_reconhecimentos([tcu]) == []
                and len(extrair_reconhecimentos([base])) == 1)

    def t17():  # a função é chamada dos dois lados: aceita `conteudo` e `trecho`
        base = {"titulo": "PORTARIA SEDEC/MIDR Nº 2.659, DE 28 DE AGOSTO DE 2026", "url": "u", "data": "29/08/2026"}
        a = extrair_reconhecimentos([{**base, "conteudo": "Município de Blumenau - SC"}])
        b = extrair_reconhecimentos([{**base, "trecho": "Município de Blumenau - SC"}])
        return a == b and len(a) == 1 and a[0]["municipio"] == "Blumenau"

    def t15():  # negativo: tabela sem coluna de município não vira reconhecimento
        outra = "<table><tr><td>Ano</td><td>Valor</td></tr><tr><td>2026</td><td>10</td></tr></table>"
        return parse_tabela_portaria_dou(outra) == [] and parse_tabela_portaria_dou("<p>sem tabela</p>") == []

    def t16():  # a linha de cabeçalho não entra como município
        linhas = parse_tabela_portaria_dou(FIXTURE_ATO_TABELA)
        return len(linhas) == 2 and all(l["municipio"] not in ("Município", "Municipio") for l in linhas)
    def t5():
        return eh_suspensao_defeso("Conteúdo suspenso em razão do período eleitoral") and not eh_suspensao_defeso("normal")
    def t6():
        r = parse_rss_midr(FIX_RSS); return len(r) == 1 and r[0]["link"].endswith("-4")
    def t7():
        info = parse_noticia_midr(FIX_NOTICIA); ufs = {uf for _, uf in info["municipios"]}
        return len(info["portarias"]) == 2 and info["portarias"][0]["numero"] == "1.723" and info["portarias"][0]["data"] == "22/05/2026" and len(info["municipios"]) >= 14 and {"BA", "PB", "PR", "RS", "RN", "AM", "MA", "PA", "SC"} <= ufs
    def t8():
        return parse_portaria_dou(FIX_PORTARIA) == [("Chorrochó", "BA"), ("Tremedal", "BA")]
    def t9():  # negativo: RSS sem itens de reconhecimento → lista vazia, nunca exceção
        return parse_rss_midr("<rss><channel><item><title>x</title><link>y</link></item></channel></rss>") == []
    FIX_LIST = """<ul><li><h2><a href="https://www.gov.br/mdr/pt-br/noticias-midr/reconhecida-emergencia-em-20-cidades-afetadas-por-desastres-1">Reconhecida emergência em 20 cidades afetadas por desastres</a></h2>
<img src="x"> 13/08/2026 - Estão na lista municípios de Alagoas</li>
<li><h2><a href="https://www.gov.br/mdr/pt-br/noticias-midr/autorizado-repasse-de-r-12-9-milhoes-para-gramado">Autorizado repasse de R$ 12,9 milhões para Gramado</a></h2> 12/08/2026 - Recursos</li></ul>"""
    def t10():  # listagem HTML: só reconhecimentos, com link e data
        r = parse_listagem_midr(FIX_LIST); return len(r) == 1 and r[0]["link"].endswith("desastres-1") and r[0]["data"] == "13/08/2026"
    def t11():  # negativo: página de login/HTML não é RSS
        return (not eh_xml_rss("<!DOCTYPE html><html><body>Conteúdo Restrito</body></html>")) and eh_xml_rss(FIX_RSS)
    return rodar_autoteste({"parser do DOU lê o JSON embutido": t1, "extrai portaria+data+município": t2,
                            "negativo: sem número não entra": t3,
                            "negativo: página sem a estrutura de resultados levanta, não devolve zero": t4,
                            "lê a forma de hoje (<script>), sem a marcação de destaque": t12,
                            "negativo: excerto da busca não basta para extrair município": t13,
                            "lendo o ato, a tabela dá município, UF e decreto municipal": t14,
                            "negativo: tabela de outro assunto não vira reconhecimento": t15,
                            "cabeçalho da tabela não entra como município": t16,
                            "extrai tanto de `conteudo` quanto de `trecho`": t17,
                            "ato de órgão sem competência não vira reconhecimento federal": t18,
                            "trava estrutural: não escreve em arquivo do banco (nem via gravar)": t19,
                            "decreto municipal é acrescentado sem sobrescrever o que já havia": t21,
                            "falha ao abrir o ato é anotada, não descartada": t20,
                            "heurística de suspensão por defeso": t5,
                            "RSS do MIDR: só notícias de reconhecimento": t6, "notícia do MIDR: portarias (nº+data) e 14+ municípios/UF": t7,
                            "página da portaria no DOU: municípios nomeados": t8, "negativo: RSS sem reconhecimentos": t9,
                            "listagem HTML do MIDR: só reconhecimentos": t10, "negativo: HTML/login não é RSS": t11})


if __name__ == "__main__":
    if "--autoteste" in sys.argv:
        sys.exit(autoteste())
    desde = sys.argv[sys.argv.index("--desde") + 1] if "--desde" in sys.argv else "2026-06-29"
    sys.exit(coletar(desde, date.today().isoformat()))
