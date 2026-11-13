#!/usr/bin/env python3
"""Sondagem semanal de repositórios de planos municipais de contingência, nas 27 UFs (13/11/2026, editoria).

Por que existe. Os repositórios estaduais (ES, SE, RS) deram a maior parte dos planos do banco, e os três
foram achados à mão; a sondagem de 24/09 testou três endereços por UF, deixou "reconferir depois de 25/10"
escrito em prosa e ninguém voltou. Aqui a sondagem é rotina: toda UF é sondada a cada `DIAS` dias, o
resultado tem data em `data/repositorios_estaduais.json`, e o frescor reprova UF parada.

O que faz, por UF: (1) pergunta ao metabuscador onde estão os planos municipais (defesa civil, ministério
público, tribunal de contas, associação de municípios, imprensa); (2) abre, como navegador, cada página
oficial apontada e as páginas já conhecidas; (3) conta em cada uma os municípios da UF nomeados em link de
documento ou de pasta (SharePoint, Drive). Página com `MINIMO` municípios ou mais é candidata a
repositório. Cada link vira PISTA pela porta única, e o juiz lê o documento: nenhum parser por estado.

Travas: nunca escreve em estados.json, saude_uf.json, municipios.json, indice.json nem monitor_saude.json;
toda pista nasce com `documento_oficial_confirmado: null` e `promovivel: false`; a saída vai à porta única.
Recusa (401/403/429/451, muro) é da página e fica registrada; resultado de imprensa é só notícia a seguir.

Uso:  python3 sondar_repositorios_estaduais.py [--uf PA] [--todas]     |     --autoteste
"""
import re
import sys
import urllib.parse

from coletores_base import ler, gravar, hoje_editorial, rodar_autoteste, log_busca, decodificar_pagina
from atualizar_instrumentos_estaduais import norm

ARQUIVO = "repositorios_estaduais.json"
DIAS, MINIMO, PAGINAS_POR_UF, SECOES_POR_PAGINA = 7, 5, 8, 4
PASTA_EXTERNA = re.compile(r"sharepoint\.com|drive\.google\.com|onedrive\.live\.com|1drv\.ms|dropbox\.com", re.I)
OFICIAL = re.compile(r"\.(gov|mp|tc|leg|jus|def)\.br$")
DOCUMENTO = re.compile(r"\.(pdf|docx?|odt|zip)(\?|$)", re.I)
PLANO = re.compile(r"plancon|placon|conting[eê]nc|plano\s+municipal|pdec", re.I)
CONSULTAS = ('"planos de contingência" municípios defesa civil {estado} site:{uf}.gov.br',
             '"planos de contingência" municipais {estado} ministério público OR "tribunal de contas"',
             '"plano de contingência" municípios {estado} pasta OR repositório OR "acesse os planos"')


def hosts_oficiais(resultados: list, uf: str) -> tuple:
    """(páginas oficiais, notícias) do que a busca devolveu. Oficial: gov, mp, tc, leg, jus ou def, do estado
    (ou sem UF no endereço). Pura."""
    paginas, noticias = [], []
    for r in resultados or []:
        url = str(r.get("url") or "")
        host = urllib.parse.urlparse(url).netloc.lower()
        m = re.search(r"\.([a-z]{2})\.(?:gov|mp|tc|leg|jus|def)\.br$", host)
        if OFICIAL.search(host) and (not m or m.group(1) == uf.lower()):
            paginas.append(url)
        elif host and PLANO.search(str(r.get("title") or "")):
            noticias.append({"url": url, "titulo": " ".join(str(r.get("title") or "").split())[:160]})
    return list(dict.fromkeys(paginas)), noticias[:5]


def avaliar_pagina(url: str, links: list, municipios: dict) -> dict:
    """O que a página lista: {municipios: {ibge: (href, texto)}, pastas_externas: [href]}. Só conta link de
    documento ou de pasta externa cujo texto ou endereço nomeia um município da UF (nome inteiro, quatro
    letras ou mais; o nome mais longo vence) e que fala de plano, ele ou a página. Pura."""
    achados, pastas = {}, []
    pagina_de_plano = bool(PLANO.search(urllib.parse.unquote(url)))
    for l in links or []:
        href, texto = str(l.get("href") or ""), " ".join(str(l.get("texto") or "").split())
        externo = bool(PASTA_EXTERNA.search(href))
        if externo and (PLANO.search(texto) or pagina_de_plano):
            pastas.append(href)
        if not (externo or DOCUMENTO.search(href)):
            continue
        alvo = " " + norm(texto + " " + re.sub(r"[_/.+%-]+", " ", urllib.parse.unquote(href))) + " "
        if not (PLANO.search(texto) or PLANO.search(urllib.parse.unquote(href)) or pagina_de_plano):
            continue
        nome = max((n for n in municipios if len(n) >= 4 and f" {n} " in alvo), key=len, default=None)
        if nome:
            achados.setdefault(municipios[nome], (href, texto[:160]))
    return {"municipios": achados, "pastas_externas": list(dict.fromkeys(pastas))}


def pistas_da_pagina(url: str, uf: str, achados: dict, por_cod: dict, hoje: str) -> list:
    """Uma pista por município listado, no esquema da porta única. Pura."""
    host = urllib.parse.urlparse(url).netloc
    return [{"documento_oficial_confirmado": None, "promovivel": False, "municipio": por_cod[c]["nome"], "uf": uf,
             "ibge": c, "url": href, "tipo": "plano", "nivel": "A", "origem": "descoberta", "data": hoje,
             "titulo": f"Página estadual a confirmar ({host}) · {por_cod[c]['nome']}/{uf}: {texto or 'plano de contingência'}"[:300],
             "trecho": texto, "hash_evidencia": None, "registrado_em": hoje} for c, (href, texto) in achados.items()]


def devida(reg: dict, hoje: str) -> bool:
    """A UF nunca sondada, ou sondada há `DIAS` dias ou mais, ou cuja última sondagem ficou incompleta (nenhuma
    página lida, ou busca sem cobertura). Pura."""
    import datetime
    if not reg or not reg.get("sondado_em") or not reg.get("paginas_lidas") or not reg.get("busca_completa"):
        return True
    return (datetime.date.fromisoformat(hoje) - datetime.date.fromisoformat(reg["sondado_em"])).days >= DIAS


def secoes_de_plano(url: str, links: list) -> list:
    """As páginas internas que a página aponta como de plano de contingência (menu, botão), sem os documentos:
    é nelas, e não na home, que a lista dos municípios costuma estar. Pura."""
    host = urllib.parse.urlparse(url).netloc
    return list(dict.fromkeys(
        str(l.get("href")) for l in links or []
        if urllib.parse.urlparse(str(l.get("href") or "")).netloc == host and not DOCUMENTO.search(str(l.get("href")))
        and PLANO.search(str(l.get("texto") or "") + " " + urllib.parse.unquote(str(l.get("href"))))
        and str(l.get("href")).split("#")[0].rstrip("/") != url.split("#")[0].rstrip("/")))[:SECOES_POR_PAGINA]


def sondar_uf(uf: str, estado: str, conhecidas: list, municipios: dict, por_cod: dict, hoje: str, busca, ler_pagina) -> tuple:
    """(registro da UF, pistas). `busca(consulta) -> {results, unresponsive_engines}` e `ler_pagina(url) ->
    {ok, links, erro}` são injetados. Busca vazia ou com motor mudo é falha (a UF segue devida), nunca
    "sem repositório"."""
    paginas, noticias, falhas, buscas_ok = list(conhecidas), [], [], 0
    for c in CONSULTAS:
        try:
            dados = busca(c.format(estado=estado, uf=uf.lower())) or {}
            p, n = hosts_oficiais(dados.get("results") or [], uf)
            paginas, noticias = paginas + p, noticias + n
            if not dados.get("results") or dados.get("unresponsive_engines"):
                raise ValueError(f"sem cobertura: {dados.get('unresponsive_engines') or 'vazia'}")
            buscas_ok += 1
        except Exception as e:  # noqa: BLE001
            falhas.append(f"busca: {type(e).__name__}: {str(e)[:120]}")
    lidas, candidatos, pistas = 0, [], []
    fila, vistas = list(dict.fromkeys(paginas))[:PAGINAS_POR_UF], set()
    while fila and len(vistas) < 2 * PAGINAS_POR_UF:
        url = fila.pop(0)
        if url in vistas:
            continue
        vistas.add(url)
        r = ler_pagina(url) or {}
        if not r.get("ok"):
            falhas.append(f"{urllib.parse.urlparse(url).netloc}: {str(r.get('erro') or 'sem resposta')[:200]}")
            continue
        lidas += 1
        a = avaliar_pagina(url, r.get("links"), municipios)
        fila += [s for s in secoes_de_plano(url, r.get("links")) if s not in vistas]
        if len(a["municipios"]) >= MINIMO or a["pastas_externas"]:
            candidatos.append({"url": url, "municipios": len(a["municipios"]), "pastas_externas": a["pastas_externas"][:5]})
        if len(a["municipios"]) >= MINIMO:
            pistas += pistas_da_pagina(url, uf, a["municipios"], por_cod, hoje)
    return ({"sondado_em": hoje, "paginas_lidas": lidas, "busca_completa": buscas_ok == len(CONSULTAS), "candidatos": candidatos,
             "noticias": list({n["url"]: n for n in noticias}.values())[:5], "falhas": list(dict.fromkeys(falhas))[:8],
             "paginas_conhecidas": list(dict.fromkeys(conhecidas + [c["url"] for c in candidatos]))[:PAGINAS_POR_UF]},
            pistas)


def ler_pagina(url: str, renderizar, buscar) -> dict:
    """A página como o navegador a vê; se o navegador falhar, o HTML estático (`buscar(url) -> bytes`)."""
    r = renderizar(url) or {}
    if r.get("ok"):
        return r
    try:
        html = decodificar_pagina(buscar(url)[:600000])[0]
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "erro": f"{r.get('erro') or 'navegador'}; estático: {type(e).__name__}: {str(e)[:40]}"}
    return {"ok": True, "links": [{"href": urllib.parse.urljoin(url, m.group(1)), "texto": re.sub(r"<[^>]+>", " ", m.group(2))}
                                  for m in re.finditer(r'<a\s[^>]*href=["\']([^"\'#]+)["\'][^>]*>(.*?)</a>', html, re.I | re.S)]}


def autoteste() -> int:
    mun = {"BELEM": "1501402", "SANTAREM": "1506807", "MARABA": "1504208", "ALTAMIRA": "1500602",
           "CAMETA": "1502103", "SANTA MARIA DO PARA": "1506500", "SANTA MARIA": "9999999"}
    por_cod = {c: {"nome": n.title()} for n, c in mun.items()}
    links = [{"href": f"https://defesacivil.pa.gov.br/docs/PLANCON_{n}.pdf", "texto": f"Plano de Contingência de {n}"}
             for n in ("Belém", "Santarém", "Marabá", "Altamira", "Cametá")]
    pagina = "https://defesacivil.pa.gov.br/planos-de-contingencia"
    a = avaliar_pagina(pagina, links + [{"href": "https://x.sharepoint.com/:f:/g/abc", "texto": "Acesse os planos"},
                                        {"href": "/noticias/belem", "texto": "Belém recebe kits"}], mun)
    busca = lambda q: {"results": [{"url": pagina, "title": "Planos"}, {"url": "https://defesacivil.sp.gov.br/x", "title": "x"},
                                   {"url": "https://jornal.com/a", "title": "Estado publica planos de contingência"}]}
    reg, pistas = sondar_uf("PA", "Pará", [], mun, por_cod, "2026-11-13", busca, lambda u: {"ok": True, "links": links})
    falho, sem = sondar_uf("PA", "Pará", [pagina], mun, por_cod, "2026-11-13", busca, lambda u: {"ok": False, "erro": "HTTP 403"})
    home = "https://defesacivil.pa.gov.br/"
    menu = [{"href": pagina, "texto": "Planos de Contingência"}, {"href": home + "noticias", "texto": "Notícias"}]
    fundo, p_fundo = sondar_uf("PA", "Pará", [home], mun, por_cod, "2026-11-13", lambda q: {"results": [{"url": home, "title": "x"}]},
                               lambda u: {"ok": True, "links": menu if u == home else links})
    mudo, _ = sondar_uf("PA", "Pará", [pagina], mun, por_cod, "2026-11-13", lambda q: {"results": [], "unresponsive_engines": ["x"]},
                        lambda u: {"ok": True, "links": links})
    parcial, p_parcial = sondar_uf("PA", "Pará", [], mun, por_cod, "2026-11-13",
                                   lambda q: {"results": [{"url": pagina, "title": "Planos"}], "unresponsive_engines": ["x"]},
                                   lambda u: {"ok": True, "links": links})
    estatico = ler_pagina(pagina, lambda u: {"ok": False, "erro": "contexto destruído"},
                          lambda u: b"<a href='/docs/PLANCON_Belem.pdf'>Plano de <b>Bel\xc3\xa9m</b></a>")
    return rodar_autoteste({
        "página: cinco municípios em link de documento; notícia e link sem documento não contam":
            lambda: len(a["municipios"]) == 5 and a["pastas_externas"] == ["https://x.sharepoint.com/:f:/g/abc"],
        "página: o nome mais longo vence (Santa Maria do Pará, não Santa Maria)":
            lambda: avaliar_pagina(pagina, [{"href": "/a/plancon-santa-maria-do-para.pdf", "texto": ""}], mun)["municipios"].keys() == {"1506500"},
        "página fora do assunto: PDF com nome de município sem plano não conta":
            lambda: avaliar_pagina("https://x.pa.gov.br/licitacoes", [{"href": "/edital_belem.pdf", "texto": "Edital Belém"}], mun)["municipios"] == {},
        "busca: só página oficial da UF vira página; imprensa vira notícia; outro estado sai":
            lambda: hosts_oficiais(busca("")["results"], "PA") == ([pagina], [{"url": "https://jornal.com/a", "titulo": "Estado publica planos de contingência"}]),
        "UF: candidata com cinco municípios, uma pista por município, com as travas de campo":
            lambda: reg["candidatos"][0]["municipios"] == 5 and len(pistas) == 5 and reg["paginas_lidas"] == 1
            and all(p["promovivel"] is False and p["documento_oficial_confirmado"] is None for p in pistas),
        "UF: página que recusa é falha registrada, nunca 'sem repositório', e a UF segue devida":
            lambda: falho["paginas_lidas"] == 0 and sem == [] and "HTTP 403" in falho["falhas"][0] and devida(falho, "2026-11-13"),
        "a lista está uma página adentro: a seção de planos do menu é aberta, e a de notícias não":
            lambda: len(p_fundo) == 5 and fundo["paginas_lidas"] == 2 and fundo["candidatos"][0]["url"] == pagina,
        "busca vazia ou com motor mudo é falha: a UF segue devida mesmo com página lida":
            lambda: mudo["busca_completa"] is False and devida(mudo, "2026-11-14") and any("busca" in f for f in mudo["falhas"]),
        "motor mudo com resultado: a página achada é lida e vira pista, e a UF segue devida":
            lambda: len(p_parcial) == 5 and parcial["busca_completa"] is False and devida(parcial, "2026-11-14"),
        "navegador que falha cai no HTML estático, com link absoluto e texto sem marcação":
            lambda: estatico["ok"] and estatico["links"][0]["href"] == "https://defesacivil.pa.gov.br/docs/PLANCON_Belem.pdf"
            and "Belém" in estatico["links"][0]["texto"],
        "cadência: sondada hoje não é devida; há sete dias, é; nunca sondada, é":
            lambda: not devida(reg, "2026-11-14") and devida(reg, "2026-11-20") and devida({}, "2026-11-13"),
        "garantia estrutural: nunca escreve nos bancos":
            lambda: re.findall(r"(?<![_\w])gravar\(([^,)]+)", open(__file__, encoding="utf-8").read().split("def main")[-1]) == ["ARQUIVO"],
    })


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    from buscar_planos_fontes_abertas import buscar_web
    from descobrir_planos import _renderizar
    from coletores_base import buscar_uma_vez
    from scripts.pistas import gravar_lote
    hoje = hoje_editorial().isoformat()
    doc = ler(ARQUIVO, {"ufs": {}})
    ref = ler("municipios_ibge_referencia.json", [])
    so = sys.argv[sys.argv.index("--uf") + 1].upper() if "--uf" in sys.argv else None
    estados = {u["uf"]: u["nome"] for u in ler("estados.json", {"ufs": []})["ufs"]}
    pistas = []
    try:
        for uf in sorted(estados):
            if (so and uf != so) or not (so or "--todas" in sys.argv or devida(doc["ufs"].get(uf), hoje)):
                continue
            mun = {norm(r["nome"]): str(r["codigo_ibge"]).zfill(7) for r in ref if r["uf"] == uf}
            por_cod = {str(r["codigo_ibge"]).zfill(7): r for r in ref if r["uf"] == uf}
            reg, novas = sondar_uf(uf, estados[uf], (doc["ufs"].get(uf) or {}).get("paginas_conhecidas") or [], mun, por_cod,
                                   hoje, buscar_web, lambda u: ler_pagina(u, lambda x: _renderizar(x, "sondar_repositorios_estaduais"), buscar_uma_vez))
            doc["ufs"][uf] = reg
            pistas += novas
            print(f"[{uf}] {reg['paginas_lidas']} página(s) lida(s); candidatos: "
                  f"{[(c['url'], c['municipios'], len(c['pastas_externas'])) for c in reg['candidatos']]}; falhas: {reg['falhas']}")
    except KeyboardInterrupt:
        print("[prazo] interrompido; gravando o que foi sondado.")
    doc["atualizado_em"] = hoje
    gravar(ARQUIVO, doc)
    balanco = gravar_lote(pistas, origem="descoberta", ler_fn=ler, gravar_fn=gravar) if pistas else {}
    log_busca("sondar_repositorios_estaduais", 1, ["27 UFs"], "pista" if pistas else "consultado sem achado",
              n_resultados=len(pistas), resultados=f"porta única: {balanco.get('gravadas', 0)} gravada(s), {balanco.get('recusadas', 0)} recusada(s)")
    print(f"Pistas: {len(pistas)}; porta única: {balanco}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
