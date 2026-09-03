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
import html as _html, json, re, sys, urllib.parse
from datetime import date
from coletores_base import (buscar, preservar_evidencia, log_busca, registrar_lacuna,
                            marcar_fonte_consultada, marcar_fato_municipal, referencia_ibge,
                            ler, gravar, rodar_autoteste, eh_suspensao_defeso, sha256)

FONTES = {
    "s2id": {"nome": "S2iD — Sistema Integrado de Informações sobre Desastres", "url": None,
             "status": "a_verificar", "nota": "sem API pública confirmada (§15)"},
    "dou": {"nome": "DOU — portarias SEDEC de reconhecimento",
            "url": "https://www.in.gov.br/consulta/-/buscar/dou?q={q}&s=do1&exactDate=personalizado&sortType=0&publishFrom={de}&publishTo={ate}",
            "status": "parser_provado_por_fixture"},
}
COBRADE_CICLO = ("1.4.1", "1.4.2", "1.3.2", "1.3.1", "1.2.1", "1.2.2", "1.2.3", "2.4.1", "2.4.2")
PADRAO_TITULO = re.compile(r"PORTARIA\s+(?:SEDEC/MIDR\s+)?N[ºo°]\s*([\d\.]+),?\s+DE\s+(\d{1,2})\s+DE\s+([A-ZÇ]+)\s+DE\s+(\d{4})", re.I)
MESES = {m: i + 1 for i, m in enumerate("janeiro fevereiro março abril maio junho julho agosto setembro outubro novembro dezembro".split())}
PADRAO_MUN = re.compile(r"Munic[íi]pio de ([^\-–,;\.]+?)\s*-\s*([A-Z]{2})", re.I)


def parse_dou_html(texto: str) -> list:
    """Extrai a lista de resultados do JSON embutido na página de consulta do DOU.
    Devolve dicts {titulo, url, data, conteudo}. Função pura."""
    m = re.search(r'id="_br_com_seatecnologia_in_buscadou_BuscaDouPortlet_params"[^>]*value="([^"]*)"', texto)
    if not m:
        return []
    bruto = _html.unescape(m.group(1))
    try:
        dados = json.loads(bruto)
    except json.JSONDecodeError:
        return []
    out = []
    for it in dados.get("jsonArray", []):
        out.append({"titulo": it.get("title", ""), "url": "https://www.in.gov.br/web/dou/-/" + it.get("urlTitle", ""),
                    "data": it.get("pubDate", ""), "conteudo": it.get("content", "")})
    return out


def extrair_reconhecimentos(resultados: list) -> list:
    """De cada portaria, extrai (número, data, município, UF). Só entra o que tem
    número E data E município — citação completa como condição de entrada (§3.3)."""
    saida = []
    for r in resultados:
        t = PADRAO_TITULO.search(r["titulo"] or "")
        if not t:
            continue
        numero, dia, mes, ano = t.groups()
        try:
            data_iso = date(int(ano), MESES[mes.lower()], int(dia)).strftime("%d/%m/%Y")
        except (KeyError, ValueError):
            continue
        for nome, uf in PADRAO_MUN.findall(r["conteudo"] or ""):
            saida.append({"portaria": f"Portaria SEDEC/MIDR nº {numero}", "data": data_iso,
                          "municipio": nome.strip(), "uf": uf.upper(), "url": r["url"]})
    return saida


RSS_MIDR = "https://www.gov.br/mdr/pt-br/noticias/RSS"
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
    try:
        bruto = buscar(RSS_MIDR)
    except Exception as e:  # noqa: BLE001
        registrar_lacuna("MIDR — notícias de reconhecimento (RSS)", f"{type(e).__name__}: {e}", canal="DOU", camada=1, strings=[RSS_MIDR]); return 0, 0, False
    h = preservar_evidencia(bruto, RSS_MIDR, "xml", "coletar_s2id")
    itens = parse_rss_midr(bruto.decode("utf-8", "replace"))
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
                for nome, uf in parse_portaria_dou(pp.decode("utf-8", "replace")): mapa[(nome, uf)] = (p, hp)
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
    log_busca("DOU", 1, [RSS_MIDR], "registro" if novos else "pista", resultados=f"MIDR RSS: {len(itens)} notícias de reconhecimento, {total} municípios lidos, {novos} novos",
              nivel="nacional", n_resultados=len(itens), hash_evidencia=h)
    return novos, total, bool(itens)


def coletar(desde: str, ate: str) -> int:
    por_cod, por_nome = referencia_ibge()
    atos = ler("atos_resposta.json"); vistos = {(e["nome"], e["uf"], e["data"], e.get("causa")) for e in atos["eventos"]}
    novos_midr, lidos_midr, rss_ok = coletar_midr(por_cod, por_nome, atos, vistos, True)
    gravar("atos_resposta.json", atos)
    if rss_ok:
        marcar_fonte_consultada(list(por_cod), "DOU/SEDEC reconhecimentos (via MIDR)", "nacional", resultado=f"{lidos_midr} município(s) reconhecido(s) lidos nas notícias do MIDR")
        print(f"MIDR/DOU: {lidos_midr} reconhecimentos lidos, {novos_midr} novos em atos_resposta.json")
    # S2iD: lacuna declarada enquanto o endpoint não for confirmado
    registrar_lacuna(FONTES["s2id"]["nome"], FONTES["s2id"]["nota"], canal="DOU", camada=1)
    q = urllib.parse.quote('"reconhece a situação de emergência"')
    de = date.fromisoformat(desde).strftime("%d-%m-%Y"); at = date.fromisoformat(ate).strftime("%d-%m-%Y")
    url = FONTES["dou"]["url"].format(q=q, de=de, ate=at)
    try:
        bruto = buscar(url)
    except Exception as e:  # noqa: BLE001
        registrar_lacuna(FONTES["dou"]["nome"], f"{type(e).__name__}: {e}", canal="DOU", camada=1, strings=[url])
        return 0
    texto = bruto.decode("utf-8", "replace")
    h = preservar_evidencia(bruto, url, "html", "coletar_s2id")
    if eh_suspensao_defeso(texto) and "jsonArray" not in texto:
        registrar_lacuna(FONTES["dou"]["nome"], "página com aviso de período eleitoral", canal="DOU",
                         camada=1, strings=[url], suspensa=True, hash_evidencia=h)
        return 0
    if "jsonArray" not in texto:
        # 03/09/2026 (achado da 1ª atualização real): a página veio sem a estrutura de resultados —
        # NÃO é consulta bem-sucedida; ninguém sobe de nível por uma leitura vazia.
        registrar_lacuna(FONTES["dou"]["nome"], "página sem a estrutura de resultados (jsonArray ausente) — parser/endpoint a verificar",
                         canal="DOU", camada=1, strings=[url], hash_evidencia=h)
        return 0
    itens = extrair_reconhecimentos(parse_dou_html(texto))
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
            continue
        atos["eventos"].append({"nome": ref["nome"], "uf": it["uf"], "ibge": cod, "data": it["data"],
                                "causa": "reconhecimento federal", "decreto": it["portaria"],
                                "data_reconhecimento": it["data"], "portaria": it["portaria"],
                                "fonte": "DOU (portaria SEDEC/MIDR)", "url": it["url"],
                                "lat": ref["lat"], "lon": ref["lon"], "canal": "DOU",
                                "hash_evidencia": h})
        marcar_fato_municipal(cod, "decreto_reconhecido", True)
        vistos.add(chave); novos += 1
    gravar("atos_resposta.json", atos)
    # (03/09/2026) a consulta textual do DOU é COMPLEMENTAR: não confere nível — o nível nacional vem do RSS do MIDR lido
    log_busca("DOU", 1, [url], "registro" if novos else "pista", resultados=f"{len(itens)} itens, {novos} novos",
              nivel="nacional", n_resultados=len(itens), hash_evidencia=h)
    print(f"DOU: {len(itens)} reconhecimento(s) lidos, {novos} novo(s) em atos_resposta.json")
    return 0


FIXTURE_HTML = ('<input id="_br_com_seatecnologia_in_buscadou_BuscaDouPortlet_params" type="hidden" value="'
                + _html.escape(json.dumps({"jsonArray": [
                    {"title": "PORTARIA SEDEC/MIDR Nº 2.659, DE 28 DE AGOSTO DE 2026", "urlTitle": "portaria-2659",
                     "pubDate": "29/08/2026", "content": "Reconhece a situação de emergência no Município de Blumenau - SC, afetado por chuvas intensas (COBRADE 1.3.2.1.4)."},
                    {"title": "AVISO DE LICITAÇÃO", "urlTitle": "x", "pubDate": "29/08/2026", "content": "nada"}]}), quote=True)
                + '"></input>')


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
    def t4():  # negativo: HTML sem o JSON embutido → lista vazia, nunca exceção
        return parse_dou_html("<html>vazio</html>") == []
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
    return rodar_autoteste({"parser do DOU lê o JSON embutido": t1, "extrai portaria+data+município": t2,
                            "negativo: sem número não entra": t3, "negativo: HTML sem JSON": t4,
                            "heurística de suspensão por defeso": t5,
                            "RSS do MIDR: só notícias de reconhecimento": t6, "notícia do MIDR: portarias (nº+data) e 14+ municípios/UF": t7,
                            "página da portaria no DOU: municípios nomeados": t8, "negativo: RSS sem reconhecimentos": t9})


if __name__ == "__main__":
    if "--autoteste" in sys.argv:
        sys.exit(autoteste())
    desde = sys.argv[sys.argv.index("--desde") + 1] if "--desde" in sys.argv else "2026-06-29"
    sys.exit(coletar(desde, date.today().isoformat()))
