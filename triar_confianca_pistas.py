#!/usr/bin/env python3
"""
triar_confianca_pistas.py — nível de confiança de cada pista (§150, 22/09/2026)
==============================================================================
Complementa classificar_pista_civil.py (triagem pelo TEXTO do trecho, calibrada para
linguagem de diário oficial) com sinais que aquela camada não vê e que, na prática da
busca web (§140-§143), separaram sinal de ruído:

  • a FONTE (host da URL): oficial (.gov.br, .leg.br, diário oficial, prefeitura) vale mais
    que imprensa, que vale mais que domínio desconhecido;
  • ONDE o município aparece: no título é forte; só na URL é médio; só no trecho é fraco
    (o caso real "MUNICÍPIO DE ANITA GARIBALDI/SC" rotulado como pista de Ipixuna/AM
    vinha de um documento onde Ipixuna só aparecia numa tabela);
  • ONDE o termo de plano aparece (título > trecho);
  • impressão digital de ATO FORMAL (decreto nº, lei nº, portaria nº, data dd/mm/aaaa);
  • família de risco do ciclo no texto (seca, chuva, calor, fogo, defesa civil);
  • ALERTAS que rebaixam sem descartar: risco errado no TÍTULO (covid, dengue, gripe,
    energia, eleição, tráfico, frio…) e padrão de LISTA de municípios no trecho.

Regra editorial central — "cuidado com falsos negativos" (pedido de 22/09/2026):
  ESTA CAMADA NUNCA DESCARTA NADA. Ela só ordena e agrupa a revisão humana. Nível C fica
  no fim da fila, visível, nunca oculto nem apagado. Quem rejeita é a pessoa, pista a pista,
  com motivo — e a rejeição é DAQUELA pista, não do município (que segue elegível). O que
  vira registro continua exigindo documento primário lido por humano (§3.2, C10).

Saída: campos `nivel_confianca` (A/B/C), `pontos_confianca`, `sinais`, `alertas` gravados em
cada pista de data/pistas_imprensa.json, e a fila de revisão agrupada por município em
data/pistas_revisao.json (derivado; regenerado a cada rodada).

USO
  python triar_confianca_pistas.py            # anota as pistas e gera a fila
  python triar_confianca_pistas.py --autoteste
"""
import json, re, sys, unicodedata
from collections import defaultdict
from datetime import date
from urllib.parse import urlparse
from coletores_base import ler, gravar, rodar_autoteste

# --- sinais literais ---------------------------------------------------------------------
HOSTS_OFICIAIS = (r"\.gov\.br$", r"\.leg\.br$", r"\.jus\.br$", r"\.mp\.br$", r"\.def\.br$",
                  r"diariomunicipal", r"diario", r"prefeitura", r"^camara", r"\.camara\.")
HOSTS_IMPRENSA = (r"g1\.globo", r"globo\.com", r"folha", r"estadao", r"uol\.com", r"terra\.com",
                  r"r7\.com", r"cnnbrasil", r"exame\.com", r"correio", r"gazeta", r"noticia",
                  r"jornal", r"agencia", r"portal", r"news", r"\.com\.br$")
TERMOS_PLANO = (r"plano de conting", r"plano de a[çc][ãa]o", r"plano municipal", r"\bplancon\b",
                r"\bplacom\b", r"plano operacional", r"plano preventivo", r"plano de prote[çc][ãa]o")
RE_ATO = re.compile(r"(decreto|lei|portaria|resolu[çc][ãa]o)\s+(municipal\s+)?n[º°o\.]*\s*[\d\.\-\/]+|\b\d{1,2}/\d{1,2}/\d{4}\b", re.I)
FAMILIAS = (r"\bseca\b|estiagem", r"chuva|inunda[çc]|alagamento|enxurrada|enchente|deslizamento",
            r"\bcalor\b|onda de calor", r"queimad|inc[êe]ndio|\bfogo\b",
            r"desastre|defesa civil|el ni[ñn]o")
# risco errado só conta no TÍTULO: um plano real pode citar dengue de passagem no trecho.
RISCO_ERRADO_TITULO = (r"covid|coronav", r"dengue|chikungunya|zika|arbovirose", r"gripe|influenza|vacin",
                       r"\benergia\b|apag[ãa]o|el[ée]trica", r"elei[çc][ãa]o|\btre\b|vereador|cassa",
                       r"tr[áa]fico|dro[gq]a", r"\bfrio\b|geada|baixas temperaturas", r"\bcovid-19\b")
# lista de municípios no trecho: 3+ ocorrências de "Nome/UF" ou "Nome (UF)" ou "Nome, UF"
RE_LISTA = re.compile(r"[A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÀ-ÿ\.\- ]{2,40}(?:/|\s\(|,\s)(?:AC|AL|AP|AM|BA|CE|DF|ES|GO|MA|MT|MS|MG|PA|PB|PR|PE|PI|RJ|RN|RS|RO|RR|SC|SP|SE|TO)\b")


def _norm(s):
    # 22/09/2026 (calibração contra as 172 pistas reais): sem tirar acento, "Petrópolis" nunca
    # casava com "petropolis" na URL — plano real do g1 caía em C. Nomes têm acento; URLs, nunca.
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).lower()


def _host(url):
    try:
        return (urlparse(url or "").hostname or "").lower()
    except Exception:  # noqa: BLE001
        return ""


def classificar_confianca(pista: dict) -> dict:
    """Pura e literal. Devolve nível (A/B/C), pontos, sinais e alertas. Nunca decide registro."""
    titulo, trecho, url = _norm(pista.get("titulo")), _norm(pista.get("trecho")), pista.get("url") or ""
    nome = _norm(pista.get("municipio"))
    host = _host(url)
    sinais, alertas, pts = [], [], 0

    if any(re.search(p, host) for p in HOSTS_OFICIAIS):
        sinais.append("fonte_oficial"); pts += 2
    elif any(re.search(p, host) for p in HOSTS_IMPRENSA):
        sinais.append("fonte_imprensa"); pts += 1
    else:
        sinais.append("fonte_desconhecida")

    eh_lista = len(RE_LISTA.findall(pista.get("trecho") or "")) >= 3
    if nome and nome in titulo:
        sinais.append("municipio_no_titulo"); pts += 2
    elif nome and nome.replace(" ", "-") in url.lower():
        sinais.append("municipio_na_url"); pts += 1
    elif nome and nome in trecho[:70] and not eh_lista:
        # 22/09/2026 (calibração): snippet costuma abrir com a manchete ("Itajaí apresenta o Plano…");
        # pistas anteriores a §150 não guardaram título — sem isto, plano real caía em C.
        # `not eh_lista`: numa lista de municípios o nome pode cair no início por acaso (caso Ipixuna).
        sinais.append("municipio_no_inicio_do_trecho"); pts += 1
    elif nome and nome in trecho:
        sinais.append("municipio_so_no_trecho")   # 0 pontos: é o padrão do ruído real

    if any(re.search(p, titulo) for p in TERMOS_PLANO):
        sinais.append("plano_no_titulo"); pts += 2
    elif any(re.search(p, trecho) for p in TERMOS_PLANO):
        sinais.append("plano_no_trecho"); pts += 1

    if RE_ATO.search(titulo) or RE_ATO.search(trecho):
        sinais.append("ato_formal"); pts += 2
    if any(re.search(p, titulo + " " + trecho) for p in FAMILIAS):
        sinais.append("familia_de_risco_do_ciclo"); pts += 1

    tri = pista.get("triagem")
    if tri == "candidato_forte":
        sinais.append("texto_candidato_forte"); pts += 2
    elif tri == "falso_positivo_provavel":
        alertas.append("texto_falso_positivo_provavel")

    if any(re.search(p, titulo) for p in RISCO_ERRADO_TITULO):
        alertas.append("risco_errado_no_titulo")
    if eh_lista:
        alertas.append("padrao_lista_de_municipios")
    if "municipio_so_no_trecho" in sinais and "padrao_lista_de_municipios" in alertas:
        alertas.append("municipio_citado_de_passagem")   # o caso Anita Garibaldi/Ipixuna

    if "risco_errado_no_titulo" in alertas or "municipio_citado_de_passagem" in alertas:
        nivel = "C"
    elif pts >= 6 and not alertas:
        nivel = "A"
    elif pts >= 3:
        nivel = "B"
    else:
        nivel = "C"
    return {"nivel_confianca": nivel, "pontos_confianca": pts, "sinais": sinais, "alertas": alertas}


def anotar_e_gerar_fila() -> dict:
    """Anota cada pista com o nível e grava a fila de revisão agrupada por município."""
    d = ler("pistas_imprensa.json") or {"pistas": []}
    por_mun = defaultdict(list)
    for p in d["pistas"]:
        p.update(classificar_confianca(p))
        por_mun[(p.get("ibge"), p.get("municipio"), p.get("uf"))].append(p)
    gravar("pistas_imprensa.json", d)

    ordem = {"A": 0, "B": 1, "C": 2}
    grupos = []
    for (ibge, mun, uf), ps in por_mun.items():
        ps.sort(key=lambda p: (ordem[p["nivel_confianca"]], -p["pontos_confianca"]))
        melhor = ps[0]["nivel_confianca"]
        grupos.append({"ibge": ibge, "municipio": mun, "uf": uf, "melhor_nivel": melhor,
                       "n_pistas": len(ps), "niveis": {n: sum(1 for p in ps if p["nivel_confianca"] == n) for n in "ABC"},
                       "pistas": [{k: p.get(k) for k in ("nivel_confianca", "pontos_confianca", "sinais", "alertas",
                                                         "origem", "url", "titulo", "trecho", "data", "status")} for p in ps]})
    grupos.sort(key=lambda g: (ordem[g["melhor_nivel"]], -g["n_pistas"], g["uf"] or "", g["municipio"] or ""))
    fila = {"_governanca": ("Fila de revisão humana das pistas, agrupada por município e ordenada por nível de "
                            "confiança (§150). DERIVADO — regenerado a cada rodada por triar_confianca_pistas.py. "
                            "Nível C está no fim, visível, nunca oculto: esta fila só ordena, nunca descarta. "
                            "Registro continua exigindo documento primário lido por humano (§3.2, C10)."),
            "gerado_em": date.today().isoformat(), "total_pistas": len(d["pistas"]), "total_municipios": len(grupos),
            "por_nivel": {n: sum(g["niveis"][n] for g in grupos) for n in "ABC"}, "grupos": grupos}
    gravar("pistas_revisao.json", fila)
    return fila


def autoteste():
    """Hermético — réplicas dos casos reais vistos ao vivo em 21/09/2026 (§141-§143)."""
    def t_marilia_imprensa_local():
        r = classificar_confianca({"municipio": "Marília", "uf": "SP", "triagem": "indefinido",
            "titulo": "Marília prepara plano de contingência para reduzir impactos de chuvas",
            "url": "https://marilianoticia.com.br/marilia-prepara-plano", "trecho": "A prefeitura de Marília..."})
        return r["nivel_confianca"] in ("A", "B") and "municipio_no_titulo" in r["sinais"] and "plano_no_titulo" in r["sinais"]

    def t_decreto_oficial_vira_A():
        r = classificar_confianca({"municipio": "Bagé", "uf": "RS", "triagem": "candidato_forte",
            "titulo": "Decreto nº 1.234/2026 institui o Plano de Contingência de Bagé para o período chuvoso",
            "url": "https://bage.rs.gov.br/diario/decreto-1234", "trecho": "Fica instituído o Plano de Contingência..."})
        return r["nivel_confianca"] == "A" and "fonte_oficial" in r["sinais"] and "ato_formal" in r["sinais"]

    def t_anita_garibaldi_nao_e_de_ipixuna():
        # ruído real: documento de outro município, Ipixuna só numa tabela — fim da fila, NÃO descartado
        r = classificar_confianca({"municipio": "Ipixuna", "uf": "AM", "triagem": "indefinido",
            "titulo": "PLANO DE CONTINGÊNCIA (PLANCON) — MUNICÍPIO DE ANITA GARIBALDI/SC",
            "url": "https://anitagaribaldi.sc.gov.br/plancon.pdf",
            "trecho": "Municípios participantes: Rio Preto da Eva/AM, Ipixuna/AM, Urucurituba/AM, Manacapuru/AM..."})
        return r["nivel_confianca"] == "C" and "municipio_citado_de_passagem" in r["alertas"]

    def t_risco_errado_no_titulo_vai_pro_fim():
        r = classificar_confianca({"municipio": "Ipixuna", "uf": "AM", "triagem": "indefinido",
            "titulo": "Plano de contingência de COVID-19 — Ipixuna/AM",
            "url": "https://ipixuna.am.gov.br/covid", "trecho": "plano de contingência para o enfrentamento da covid"})
        return r["nivel_confianca"] == "C" and "risco_errado_no_titulo" in r["alertas"]

    def t_dengue_so_no_trecho_nao_rebaixa():
        # falso negativo a evitar: plano real cita dengue de passagem no trecho
        r = classificar_confianca({"municipio": "Bagé", "uf": "RS", "triagem": "indefinido",
            "titulo": "Bagé lança plano de contingência para chuvas de verão",
            "url": "https://bage.rs.gov.br/noticias/plano", "trecho": "...ações contra dengue também estão previstas..."})
        return "risco_errado_no_titulo" not in r["alertas"] and r["nivel_confianca"] != "C"

    def t_sem_titulo_degrada_sem_quebrar():
        # pistas antigas da busca web não guardavam título — não pode quebrar nem descartar
        r = classificar_confianca({"municipio": "Manaus", "uf": "AM", "triagem": "indefinido",
            "url": "https://exame.com/esg/el-nino-manaus", "trecho": "a prefeitura pretende lançar o Plano de Contingência"})
        return r["nivel_confianca"] in ("B", "C") and "plano_no_trecho" in r["sinais"]

    def t_nunca_descarta():
        # a fila é só ordenação: toda pista entra em algum nível
        for caso in ({}, {"titulo": "", "trecho": "", "url": ""}, {"municipio": None}):
            if classificar_confianca(caso)["nivel_confianca"] not in "ABC": return False
        return True

    def t_acento_petropolis_casa_com_url():
        # falso negativo REAL da calibração (22/09): "Petrópolis" vs "petropolis" na URL do g1
        r = classificar_confianca({"municipio": "Petrópolis", "uf": "RJ", "triagem": "indefinido",
            "url": "https://g1.globo.com/rj/regiao-serrana/noticia/2026/05/23/prefeitura-de-petropolis-abre-plano.ghtml",
            "trecho": "Prefeitura de Petrópolis abre Plano de Contingência do Inverno 2026"})
        return "municipio_na_url" in r["sinais"] and r["nivel_confianca"] != "C"

    return rodar_autoteste({
        "imprensa local com município e plano no título: A ou B (caso Marília)": t_marilia_imprensa_local,
        "decreto em fonte oficial com ato formal: A": t_decreto_oficial_vira_A,
        "documento de outro município, citado só em lista: C com alerta (caso Anita Garibaldi/Ipixuna)": t_anita_garibaldi_nao_e_de_ipixuna,
        "risco errado no título: C com alerta, não descartado": t_risco_errado_no_titulo_vai_pro_fim,
        "risco errado só no trecho NÃO rebaixa (evita falso negativo)": t_dengue_so_no_trecho_nao_rebaixa,
        "pista sem título degrada sem quebrar": t_sem_titulo_degrada_sem_quebrar,
        "nunca descarta: toda pista recebe um nível": t_nunca_descarta,
        "acento: Petrópolis casa com 'petropolis' na URL (falso negativo real corrigido)": t_acento_petropolis_casa_com_url,
    })


if __name__ == "__main__":
    if "--autoteste" in sys.argv:
        sys.exit(autoteste())
    f = anotar_e_gerar_fila()
    print(f"triagem de confiança: {f['total_pistas']} pistas em {f['total_municipios']} municípios · "
          f"A={f['por_nivel']['A']} B={f['por_nivel']['B']} C={f['por_nivel']['C']} → data/pistas_revisao.json")
