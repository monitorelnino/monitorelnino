#!/usr/bin/env python3
"""Juiz dos planos MUNICIPAIS de saúde (arboviroses): a régua da camada de saúde, aplicada ao município.

Editoria, 15/11/2026: "priorize a varredura dos planos municipais de saúde [...] com todas as pistas
julgadas" e publicadas. Até aqui a fila `data/pistas_arboviroses.json` (menções a plano de contingência
de dengue, chikungunya e zika nos diários municipais, de `coletar_planos_arboviroses.py`) não tinha juiz.

A RÉGUA é a do juiz estadual de saúde (`julgar_saude.julgar_camada_saude`), etapa por etapa, com três
diferenças que só mudam QUEM é o ente:
  · etapa 1 — o documento nomeia o MUNICÍPIO da pista (homônimo se resolve pela UF, como no Legal);
  · etapa 3 — ato do Executivo municipal; sem ato, a exceção de autoridade da camada de saúde vale para
    o plano publicado no domínio do próprio município ou no diário dele, com órgão, título e ano;
  · etapa 3b — o documento é do município (o estadual é do outro juiz).
Na edição do diário, o ato julgado é o que contém o trecho da pista (`juiz.recortar_ato`).

TRAVAS: escreve só `data/planos_arboviroses_juiz.json`; nunca a fila (que segue com seu único escritor),
nem estados.json, saude_uf.json, municipios.json, indice.json ou monitor_saude.json. Peso zero: o
arquivo não entra no índice. Falha de rede não é veredito: a pista volta na rodada seguinte.

Uso: python3 julgar_saude_municipal.py [--limite N]     ·     python3 julgar_saude_municipal.py --autoteste
"""
import re
import sys
import urllib.error
import urllib.parse

import juiz
import julgar_saude as js
from coletores_base import buscar, gravar, hoje_editorial, ler, rodar_autoteste

FILA = "pistas_arboviroses.json"
ARQUIVO = "planos_arboviroses_juiz.json"
COLETA = "planos_arboviroses.json"
GOVERNANCA = ("Planos municipais de contingência de arboviroses julgados pela régua da camada de saúde, aplicada "
              "ao município (julgar_saude_municipal.py). Peso zero: não entra no índice. `municipios` guarda, por "
              "código IBGE, o plano mais forte promovido; município sem linha não teve plano promovido até o corte, "
              "o que não afirma que não haja plano.")
# Órgão e título na esfera do município (os de `julgar_saude` nomeiam a secretaria e o plano ESTADUAIS).
RE_ORGAO_MUNICIPAL = re.compile(r"secretaria\s+municipal\s+d[ae]\s+sa[úu]de|fundo\s+municipal\s+de\s+sa[úu]de"
                                r"|\b(?:SMS|SEMSA|SEMUS|SESAU)\b", re.I)
RE_PLANO_MUNICIPAL = re.compile(r"plano\s+(?:municipal\s+)?(?:de\s+)?(?:conting[êe]ncia|prepara[çc][ãa]o|a[çc][ãa]o"
                                r"|enfrentamento|resposta)", re.I)
FORCA = {"NOVO": 4, "READ": 3, "VIG": 2, "ELAB": 1, "VENC": 0}


def pistas_da_fila(doc) -> list:
    if isinstance(doc, list):
        return doc
    return max((v for v in (doc or {}).values() if isinstance(v, list)), key=len, default=[])


def titulo_no_texto(ato: str) -> str:
    """O título do plano como o documento o escreve, até o primeiro ponto. Função pura."""
    m = RE_PLANO_MUNICIPAL.search(ato or "")
    if not m:
        return ""
    t = re.split(r"[.;“”\"]|,\s|\s+Considerando|\s+e\s+\d", (ato or "")[m.start():m.start() + 200])[0].strip()
    return t if len(t) <= 140 else t[:140].rsplit(" ", 1)[0]


def julgar_municipal(texto: str, p: dict) -> dict:
    """As etapas da camada de saúde para o município da pista. Função pura."""
    nome, uf, ibge, url = p.get("municipio"), p.get("uf"), p.get("ibge") or p.get("alvo"), p.get("url_final") or p.get("url")
    ato = juiz.recortar_ato(texto, p.get("trecho"))
    v = {"promove": False, "motivo": None, "codebook": juiz.CODEBOOK_VERSAO, "categoria": None, "data": None,
         "ibge": ibge, "municipio": nome, "uf": uf, "url": url, "criterios": {}}

    def recusa(etapa, motivo, trecho=""):
        v["criterios"][etapa] = {"ok": False, "trecho": str(trecho)[:300]}
        v["motivo"] = motivo
        return v

    ok, motivo, prova = juiz.etapa0_documento_primario(url, ato)
    if not ok:
        return recusa("0_documento_primario", motivo, prova)
    ok, motivo, trecho = juiz.etapa1_identidade(ato if ato is not texto else texto, nome, uf)
    if not ok:
        return recusa("1_identidade", motivo, trecho)
    titulo = titulo_no_texto(ato) or js.titulo_do_documento(ato, p.get("titulo") or "", url)
    como_plano = juiz.e_plano_pelo_cabecalho(ato) or js.titulo_diz_plano(titulo)
    if como_plano:
        ok, motivo, _ = juiz.e_o_proprio_plano(ato, url)
        if not ok and not juiz.ato_proprio(ato):
            return recusa("1b_e_o_plano", motivo)
    plano_tecnico = "instrumento" in js.o_que_institui(ato) and juiz.ato_proprio(ato) is None
    ok, motivo, dados = juiz.etapa2_citacao(ato, plano_tecnico, url=url, como_plano=como_plano)
    dados = js.data_do_plano(dados, url) if como_plano else js.com_data_do_cabecalho(ato, dados)
    v["data"], v["numero"] = dados.get("data"), dados.get("numero")
    if not ok:
        return recusa("2_citacao", motivo, dados.get("trecho", ""))
    ok, motivo, trecho = juiz.etapa3_autoridade(ato, esfera="municipal")
    if not ok and motivo == "autoridade_nao_confirmada":
        host = urllib.parse.urlparse(url or "").netloc.lower()
        do_municipio = js.host_de_municipio(host) or p.get("origem") == "querido_diario"
        ok2 = bool(RE_ORGAO_MUNICIPAL.search(ato) and RE_PLANO_MUNICIPAL.search(ato) and js.RE_ANO_OU_CICLO.search(ato))
        if do_municipio and ok2:
            ok, trecho = True, "exceção de autoridade da camada de saúde, no município: plano publicado pelo município, com órgão, título e ano"
            v["excecao_autoridade"] = "sem ato de aprovação localizado"
    if not ok:
        return recusa("3_autoridade", motivo, trecho)
    if como_plano:
        natureza = "EX_ANTE"
    else:
        natureza, _, _ = juiz.etapa4_natureza(ato)
    v["natureza"] = natureza
    if natureza == "RESPOSTA":
        return recusa("4_natureza", "resposta")
    if natureza != "EX_ANTE":
        return recusa("4_natureza", "natureza_duvidosa")
    # O risco vem do DOCUMENTO (título lido ou capa), nunca do título da pista: na fila do diário ele é a
    # própria consulta ('"plano de contingência" dengue') e aprovaria qualquer plano.
    risco = js.trata_de_risco_do_ciclo(titulo_no_texto(ato) or "")
    risco = risco if risco[0] else js.trata_de_risco_do_ciclo((ato or "")[:1500])
    v["titulo_do_documento"] = titulo
    if not risco[0]:
        return recusa("5b_risco_do_ciclo", "risco_fora_do_ciclo", titulo)
    categoria, motivo_cat = juiz.etapa6_categoria(ato, v["data"], True,
                                                  sem_ato_de_aprovacao=bool(dados.get("sem_ato_de_aprovacao")),
                                                  como_plano=como_plano)
    if categoria is None:
        return recusa("6_categoria", motivo_cat.split(":")[0], motivo_cat)
    v.update(promove=True, categoria=categoria, criterios={"5b_risco_do_ciclo": {"ok": True, "trecho": risco[1]}})
    encerrada = js.vigencia_encerrada(ato, titulo)
    v["vigencia_declarada"] = encerrada or None
    v["status"] = js.status_instrumento(categoria, encerrada)
    return no_municipio(v)


RE_PLANO_DE_OUTRO_ENTE = re.compile(r"\bestadua(?:l|is)\b|\bdo\s+estado\b", re.I)


def no_municipio(v: dict) -> dict:
    """Duas guardas da esfera municipal sobre o veredito promovido. Função pura.

    16/11/2026, na primeira rodada: (1) o ato municipal que cita o PLANO ESTADUAL ("Plano Estadual de
    Contingência das Arboviroses Urbanas") entrava como plano do município (Jaú, Dirce Reis, Igaraçu do
    Tietê); (2) plano datado antes de 2026 saía "feito para o ciclo" porque citava o El Niño anterior
    (Marília, 2024). O ciclo é o de 2026/2027."""
    if not v.get("promove"):
        return v
    if RE_PLANO_DE_OUTRO_ENTE.search(v.get("titulo_do_documento") or ""):
        return {**v, "promove": False, "motivo": "plano_de_outro_ente", "status": None}
    ano = re.search(r"(20\d{2})", str(v.get("data") or ""))
    if v.get("status") == "NOVO" and ano and int(ano.group(1)) < js.ANO_DO_CICLO:
        return {**v, "status": "VIG"}
    return v


def consolidar(vereditos: dict) -> dict:
    """{ibge: o plano mais forte promovido}. Função pura."""
    por_ibge = {}
    for url, v in sorted(vereditos.items()):
        if not v.get("promove") or not v.get("status"):
            continue
        atual = por_ibge.get(v["ibge"])
        if atual is None or FORCA[v["status"]] > FORCA[atual["status"]]:
            por_ibge[v["ibge"]] = {"municipio": v["municipio"], "uf": v["uf"], "status": v["status"],
                                   "doc": v.get("titulo_do_documento"), "data": v.get("data"), "url": url}
    return por_ibge


def sem_plano_promovido(coleta: dict, municipios: dict) -> dict:
    """{ibge: "citado" | "nao_localizado"} para a página, pela leitura de `coletar_planos_arboviroses.py`.
    Município fora do mapa não foi verificado. Função pura."""
    classe = {"menção localizada em diário oficial": "citado", "não localizado até o corte": "nao_localizado"}
    return {ibge: classe[m["estatuto"]] for ibge, m in sorted((coleta.get("municipios") or {}).items())
            if ibge not in municipios and m.get("estatuto") in classe}


def ja_julgada(v) -> bool:
    """Veredito desta versão do juiz; o de serviço fora do ar (5xx) gravado como recusa volta. Pura."""
    v = v or {}
    return v.get("codebook") == juiz.CODEBOOK_VERSAO and not re.match(r"documento não baixado: HTTP 5", str(v.get("motivo") or ""))


def rodar(limite=None, buscar_fn=None, ler_fn=ler, gravar_fn=gravar) -> dict:
    doc = ler_fn(ARQUIVO, {}) or {}
    vereditos = dict(doc.get("vereditos") or {})
    pistas = [p for p in pistas_da_fila(ler_fn(FILA, [])) if (p.get("url_final") or p.get("url"))
              and not ja_julgada(vereditos.get(p.get("url_final") or p.get("url")))]
    pistas = pistas[:limite] if limite else pistas
    print(f"{len(pistas)} pista(s) municipal(is) de arboviroses a julgar")
    feitos = {"promovida": 0, "recusada": 0, "pendente": 0}
    try:
        for p in pistas:
            url = p.get("url_final") or p.get("url")
            try:
                corpo = (buscar_fn or buscar)(url, timeout=150, origem="julgar_saude_municipal")
            except urllib.error.HTTPError as e:
                if e.code >= 500:   # serviço fora do ar não é veredito (26/11/2026)
                    feitos["pendente"] += 1
                    continue
                vereditos[url] = {"promove": False, "motivo": f"documento não baixado: HTTP {e.code}",
                                  "codebook": juiz.CODEBOOK_VERSAO, "ibge": p.get("ibge") or p.get("alvo")}
                feitos["recusada"] += 1
                continue
            except Exception:  # noqa: BLE001 — rede: não é veredito, volta na rodada seguinte
                feitos["pendente"] += 1
                continue
            v = julgar_municipal(js.com_ocr(corpo, js.texto_do_documento(corpo, url)), p)
            v["criterios"] = {k: c for k, c in v["criterios"].items() if not c.get("ok")}
            v["julgado_em"] = hoje_editorial().isoformat()
            vereditos[url] = v
            feitos["promovida" if v["promove"] else "recusada"] += 1
            print(f"  {'✓' if v['promove'] else '✗'} {p.get('municipio')}/{p.get('uf')} · {v.get('status') or v.get('motivo')}")
    except KeyboardInterrupt:
        print("prazo: gravando o que foi julgado")
    municipios = consolidar(vereditos)
    gravar_fn(ARQUIVO, {"_governanca": GOVERNANCA, "atualizado_em": hoje_editorial().isoformat(),
                        "municipios": municipios,
                        "sem_plano_promovido": sem_plano_promovido(ler_fn(COLETA, {}) or {}, municipios),
                        "vereditos": vereditos})
    print(f"{feitos['promovida']} promovida(s) · {feitos['recusada']} recusada(s) · {feitos['pendente']} pendente(s) · "
          f"{len(municipios)} município(s) com plano promovido")
    return feitos


def autoteste() -> int:
    plano = ("Prefeitura Municipal de Cuiabá. Secretaria Municipal de Saúde. PLANO MUNICIPAL DE CONTINGÊNCIA "
             "PARA ENFRENTAMENTO DAS ARBOVIROSES (DENGUE, CHIKUNGUNYA E ZIKA) 2026/2027. Cuiabá-MT, agosto de 2026. "
             "SUMÁRIO. 1 Introdução. 2 Objetivos. 3 Níveis de resposta e acionamento. 4 Atribuições. Anexo. " * 6)
    p = {"municipio": "Cuiabá", "uf": "MT", "ibge": "5103403", "origem": "busca_web",
         "url_final": "https://www.cuiaba.mt.gov.br/plano-arboviroses-2026-2027", "titulo": "Plano municipal de arboviroses"}
    escrito = {}
    fila = [p, {**p, "url_final": "https://www.cuiaba.mt.gov.br/fora.pdf"}]

    def falso_buscar(url, **k):
        if "fora" in url:
            raise TimeoutError()
        return plano.encode()
    rodar(buscar_fn=falso_buscar, ler_fn=lambda n, d=None: fila if n == FILA else {},
          gravar_fn=lambda n, d: escrito.update({n: d}))
    out = escrito.get(ARQUIVO) or {}
    import inspect
    fonte = inspect.getsource(sys.modules[__name__])
    proibidos = [a for a in ("estados.json", "saude_uf.json", "municipios.json", "indice.json", "monitor_saude.json")
                 if f'gravar("{a.split(".")[0]}' in fonte or f"gravar_fn(\"{a}" in fonte]
    return rodar_autoteste({
        "plano municipal de arboviroses do próprio município é promovido": lambda:
            (out.get("municipios") or {}).get("5103403", {}).get("status") in ("NOVO", "VIG", "READ"),
        "queda de rede não vira veredito": lambda: "https://www.cuiaba.mt.gov.br/fora.pdf" not in (out.get("vereditos") or {}),
        "outro município no texto não credita a pista": lambda:
            not julgar_municipal(plano, {**p, "municipio": "Várzea Grande", "ibge": "5108402"})["promove"],
        "plano de outro risco não entra": lambda: not julgar_municipal(
            plano.replace("ARBOVIROSES (DENGUE, CHIKUNGUNYA E ZIKA)", "SARAMPO"), p)["promove"],
        "ato que cita o plano ESTADUAL não é plano do município": lambda: no_municipio(
            {"promove": True, "status": "VIG", "titulo_do_documento": "Plano Estadual de Contingência das Arboviroses"})["motivo"] == "plano_de_outro_ente",
        "plano de 2024 não é feito para este ciclo": lambda: no_municipio(
            {"promove": True, "status": "NOVO", "data": "2024", "titulo_do_documento": "Plano de Contingência"})["status"] == "VIG",
        "veredito de serviço fora do ar (5xx) volta; o desta versão do juiz e o de recusa 4xx ficam": lambda:
            not ja_julgada({"codebook": juiz.CODEBOOK_VERSAO, "motivo": "documento não baixado: HTTP 500"})
            and ja_julgada({"codebook": juiz.CODEBOOK_VERSAO, "motivo": "documento não baixado: HTTP 403"})
            and not ja_julgada({"codebook": "antigo"}),
        "escreve só o próprio arquivo": lambda: list(escrito) == [ARQUIVO] and not proibidos,
    })


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    limite = int(sys.argv[sys.argv.index("--limite") + 1]) if "--limite" in sys.argv else None
    rodar(limite)
    return 0


if __name__ == "__main__":
    sys.exit(main())
