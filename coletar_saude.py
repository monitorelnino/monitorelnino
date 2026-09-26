#!/usr/bin/env python3
"""
coletar_saude.py — página Saúde e El Niño (doc de redesenho §9; E2, C1–C3)
=========================================================================
ESTATUTO: peso ZERO no MARÉ, provado por portão (verificar_saude.py). Reproduz o
que órgãos oficiais publicaram (órgão, documento, data); verifica o que os
estados publicaram com o protocolo do Monitor; nunca projeta; nunca dá
orientação médica própria.

Três registros:
  data/saude_federal.json — cartões da camada federal (§9.1); lacuna = linha
    própria "anunciado, não localizado até o corte". Sem cartão inventado.
  data/saude_uf.json — camada estadual verificada (§9.2), 27 UFs no vocabulário
    NOVO/READ/VIG/ELAB/LAC/NAO_VERIFICADO. Em 02/09/2026 nasce NAO_VERIFICADO
    nas 27 (C1): a bateria estadual é executada e logada por UF na semana
    intensiva; até lá a página diz "ainda não verificado".
  data/saude_sinais.json — camada observada (§9.3): dengue (Painel MS primário;
    InfoDengue com crédito, nível de alerta por município), calor (reuso INMET
    do PR #3), queimadas (reuso INPE), ESPIN (resposta, peso zero).

USO
  python coletar_saude.py --autoteste
  python coletar_saude.py --semear      # (re)cria os três registros sem rede
  python coletar_saude.py               # coleta a camada observada (rede)
"""
import json, re, sys, urllib.parse
from datetime import date
from coletores_base import (buscar, preservar_evidencia, log_busca, registrar_lacuna, ler, gravar,
                            rodar_autoteste, referencia_ibge, hoje_editorial)

UFS = "AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO".split()
CAPITAIS = {"AC": "Rio Branco", "AL": "Maceió", "AM": "Manaus", "AP": "Macapá", "BA": "Salvador", "CE": "Fortaleza",
            "DF": "Brasília", "ES": "Vitória", "GO": "Goiânia", "MA": "São Luís", "MG": "Belo Horizonte",
            "MS": "Campo Grande", "MT": "Cuiabá", "PA": "Belém", "PB": "João Pessoa", "PE": "Recife", "PI": "Teresina",
            "PR": "Curitiba", "RJ": "Rio de Janeiro", "RN": "Natal", "RO": "Porto Velho", "RR": "Boa Vista",
            "RS": "Porto Alegre", "SC": "Florianópolis", "SE": "Aracaju", "SP": "São Paulo", "TO": "Palmas"}
INFODENGUE_API = "https://info.dengue.mat.br/api/alertcity?geocode={geocode}&disease=dengue&format=json&ew_start=1&ew_end=53&ey_start={ano}&ey_end={ano}"

# Riscos sanitários por família de risco projetado (§9.2) — derivação declarada, sem projeção nova
RISCO_SANITARIO = {
    "seca": ["arboviroses (armazenamento de água)", "doenças respiratórias por fumaça de queimadas",
             "ondas de calor", "qualidade da água em estiagem"],
    "chuvas": ["leptospirose", "doenças diarreicas agudas", "hepatite A", "abrigos e continuidade de serviços"],
    "multi": ["arboviroses", "respiratórias por queimadas", "leptospirose e diarreias", "continuidade de serviços (diálise, oxigênio, rede de frio)"],
}


def semear():
    hoje = hoje_editorial().strftime("%d/%m/%Y")
    federal = {"_governanca": "Camada federal de saúde (§9.1). Reproduz documentos oficiais com órgão, data e "
                              "estatuto; 'anunciado_nao_localizado' = existência noticiada oficialmente, documento "
                              "não localizado até o corte. Nunca lido pelo cálculo do índice.",
               "corte": hoje,
               "cartoes": [
                   {"titulo": "Plano de Preparação e Resposta a Emergências em Saúde Pública associadas ao El Niño 2026-2027",
                    "orgao": "Ministério da Saúde → CONASS", "data": "26/08/2026", "url": None,
                    "status": "anunciado_nao_localizado", "nota": "Existência verificada na apresentação ao CONASS; PDF a localizar (§15)."},
                   {"titulo": "AdaptaSUS — Plano Setorial de Adaptação à Mudança do Clima na Saúde (27 metas, 93 ações até 2035)",
                    "orgao": "Ministério da Saúde", "data": "2025", "url": None, "status": "localizado",
                    "nota": "Documento verificado em 02/09/2026; endereço estável em verificação."},
                   {"titulo": "Portaria do painel de especialistas em clima e saúde",
                    "orgao": "Ministério da Saúde", "data": "anunciada em 26/08/2026", "url": None,
                    "status": "anunciado_nao_localizado", "nota": "Portaria não localizada no DOU até o corte."},
                   {"titulo": "CISC — Centros Integrados de Saúde e Clima (8 cidades-piloto, 5 regiões)",
                    "orgao": "Ministério da Saúde", "data": "2026", "url": None,
                    "status": "anunciado_nao_localizado", "nota": "Existência verificada; relação nominal das cidades não localizada até o corte."},
                   {"titulo": "Painel Nacional de Excesso de Calor · VigiAR · GeoRisk",
                    "orgao": "Ministério da Saúde", "data": "—", "url": None,
                    "status": "anunciado_nao_localizado", "nota": "Citados pelo MS; endereço e formato em verificação."},
                   {"titulo": "Orientações oficiais sobre dengue (sintomas, sinais de alarme, quando procurar atendimento)",
                    "orgao": "Ministério da Saúde", "data": "página oficial, consultada em 02/09/2026",
                    "url": "https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/d/dengue", "status": "localizado",
                    "nota": "Reproduzida na camada do cidadão, com link; o Monitor não emite orientação médica própria."},
               ]}
    consist = ler("consist.json", {}) or {}
    ufs = {}
    for uf in UFS:
        c = consist.get(uf, {}) if isinstance(consist, dict) else {}
        risco = str(c.get("risco", "")).lower() if isinstance(c, dict) else ""
        # derivação declarada do campo "risco" de consist.json (texto dos boletins): sem projeção nova
        tem_seca = any(k in risco for k in ("seca", "estiagem", "incêndio", "incendio", "calor"))
        tem_chuva = any(k in risco for k in ("chuva", "enchente", "inunda", "alagamento"))
        tipo = "multi" if (tem_seca and tem_chuva) or not risco else "seca" if tem_seca else "chuvas"
        ufs[uf] = {"status": "NAO_VERIFICADO", "orgao": None, "doc": None, "numero": None, "data": None, "url": None,
                   "hash_evidencia": None, "natureza_doc": "nenhum", "justificativa_ex_ante": None,
                   "risco_sanitario_projetado": RISCO_SANITARIO[tipo], "consist": "NEUTRO",
                   "data_verificacao": None, "log_ref": None}
    saude_uf = {"_governanca": "Camada estadual de saúde (§9.2, C1). Vocabulário fechado: NOVO · READ · VIG · ELAB · "
                               "LAC (bateria datada) · NAO_VERIFICADO. NUNCA lida por recalcular_mare.py (portão). "
                               "'LAC' só com bateria estadual logada (nivel='estadual').",
                "vocabulario": ["NOVO", "READ", "VIG", "ELAB", "LAC", "NAO_VERIFICADO"],
                "consist_vocabulario": ["COBRE", "PARCIAL", "DIFERE", "SEM", "NEUTRO"],
                "corte": hoje, "uf": ufs}
    sinais = {"_governanca": "Camada observada de saúde (§9.3). Mesmo formato de sinais_risco.json: por fonte, "
                             "coletado_em, órgão, documento, data de referência, URL, valores por UF/município, "
                             "lacuna declarada. Dado epidemiológico é observação, nunca juízo de preparo. Peso zero.",
              "fontes": {
                  # 24/09/2026 (§209): procurado o dado aberto do painel. O portal de dados do MS
                  # mudou de endereço (opendatasus → dadosabertos.saude.gov.br, aplicativo novo, 140
                  # conjuntos) e o que ele publica sobre dengue é MICRODADO do Sinan — 83 arquivos,
                  # atualizados em setembro/2026 —, não a série de casos prováveis por semana que o
                  # painel mostra. Agregar microdado do Sinan produziria número NOSSO, que poderia
                  # divergir do painel do MS: é projeto próprio, não coleta, e exige decisão da
                  # editoria. Até lá a página usa o InfoDengue, com crédito de modelo.
                  "painel_arboviroses_ms": {"nome": "Painel de Arboviroses", "orgao": "Ministério da Saúde", "papel": "fonte PRIMÁRIA do número de casos prováveis por semana epidemiológica",
                                             "url_publica": "https://dadosabertos.saude.gov.br/dataset/arboviroses-dengue",
                                             "status": "a_verificar", "consultado_em": None,
                                             "nota": "o MS publica microdado do Sinan (83 arquivos), não a série semanal do painel; agregar seria número nosso"},
                  "infodengue": {"nome": "InfoDengue", "orgao": "Fiocruz/FGV", "papel": "nível de alerta e série municipal semanal (modelo); crédito obrigatório 'modelo InfoDengue (Fiocruz/FGV)'",
                                 "url_publica": "https://info.dengue.mat.br", "status": "aguardando_primeira_coleta", "consultado_em": None,
                                 "regra_divergencia": "divergência com o painel do MS → exibe o MS e loga a diferença (C2)"},
                  "inmet_calor": {"nome": "Avisos de calor", "orgao": "INMET", "papel": "reuso do adaptador do PR #3 (sinais_risco.json → avisos_inmet)", "status": "reuso", "consultado_em": None},
                  # 24/09/2026: o aviso de calor do INMET é ALERTA e foi para defesa-civil.html; o que a
                  # página de Saúde passa a mostrar é dado de saúde — a classe de excesso de calor que o
                  # próprio MS publica por município, no vocabulário dele (Normal, Baixo, Severo, Extremo).
                  "painel_calor_ms": {"nome": "Painel Nacional de Excesso de Calor", "orgao": "Ministério da Saúde",
                                       "papel": "classe de excesso de calor por município (índice EHF), no vocabulário do MS",
                                       "url_publica": "https://clima.saude.gov.br/", "status": "aguardando_primeira_coleta",
                                       "consultado_em": None,
                                       "nota": "sem API documentada: o endereço da função interna é descoberto a cada rodada e validado por conteúdo"},
                  "inpe_focos": {"nome": "Focos de queimada (proxy respiratório)", "orgao": "INPE", "papel": "reuso (sinais_risco.json → fogo)", "status": "reuso", "consultado_em": None},
                  "sisagua": {"nome": "SISAGUA (água/intermitência em estiagem)", "orgao": "Ministério da Saúde", "url_publica": None, "status": "a_verificar", "consultado_em": None},
                  "espin": {"nome": "ESPIN e decretos de emergência sanitária", "orgao": "DOU / diários municipais", "papel": "RESPOSTA, peso zero", "status": "aguardando_primeira_coleta", "consultado_em": None},
              },
              "dengue_capitais": {}, "gerado_em": hoje}
    gravar("saude_federal.json", federal); gravar("saude_uf.json", saude_uf); gravar("saude_sinais.json", sinais)
    print("saúde: 3 registros semeados — 27 UFs NAO_VERIFICADO; 6 cartões federais; fontes observadas em lacuna declarada")


# ---------------------------------------------------------------------------------
# Painel Nacional de Excesso de Calor (Ministério da Saúde) — 24/09/2026
#
# POR QUE ISTO É MAIS DIFÍCIL DO QUE UMA API: o painel de clima.saude.gov.br não
# publica API documentada. O dado por município existe, e é dado de SAÚDE (classe de
# excesso de calor, índice EHF, máxima do dia), mas chega por uma FUNÇÃO INTERNA do
# aplicativo, num endereço `/_serverFn/<sha256>` cujo hash é ARTEFATO DE BUILD: muda a
# cada publicação do site do MS. Fixar o hash no código é dependência que quebra em
# silêncio, então ele é DESCOBERTO a cada rodada, e validado POR CONTEÚDO — nunca por
# nome de variável minificada, que também muda a cada build.
#
# A serialização também é própria (TanStack Start): objeto é
# {"t":10,"p":{"k":[chaves],"v":[valores]}}, lista é {"t":9,"a":[itens]}, escalar é
# {"t":0|1,"s":valor}. `decodificar_tanstack` desfaz isso.
#
# O vocabulário de severidade é O DO MS (Normal, Baixo, Severo, Extremo). O projeto não
# reescala nada — mesma regra de sempre.
# ---------------------------------------------------------------------------------
CALOR_MS_SITIO = "https://clima.saude.gov.br/"
# Marcas que provam que a resposta é a do agregado de excesso de calor, e não de outra
# função interna qualquer. Validação por conteúdo é o que sobrevive a um build novo.
CALOR_MS_MARCAS = ("ufData", "mapaData", "operationalWindow")
CALOR_MS_CLASSES = ("Normal", "Baixo", "Severo", "Extremo")


def decodificar_tanstack(no):
    """Desfaz a serialização própria do app do MS e devolve dado Python comum. Função pura.

    Formatos vistos com rede real em 24/09/2026:
      {"t":10,"p":{"k":[chaves],"v":[valores]}}  → dicionário
      {"t":9,"a":[itens]}                        → lista
      {"t":0|1,"s":escalar}                      → número ou texto
      {"t":2,"s":3}                              → ausência (o app usa para nulo)
    Nó desconhecido devolve None em vez de levantar: formato novo do MS vira lacuna
    declarada na página, não exceção que derruba a coleta de saúde inteira."""
    if not isinstance(no, dict):
        return no
    tipo = no.get("t")
    if tipo == 10:
        p = no.get("p") or {}
        chaves, valores = p.get("k") or [], p.get("v") or []
        return {k: decodificar_tanstack(v) for k, v in zip(chaves, valores)}
    if tipo == 9:
        return [decodificar_tanstack(x) for x in (no.get("a") or [])]
    if tipo in (0, 1):
        return no.get("s")
    return None


def parse_calor_ms(bruto: str) -> dict:
    """Lê a resposta do painel de excesso de calor do MS e devolve
    {'data','janela','por_uf','municipios','resumo'}. Função pura.

    `por_uf` traz a contagem de municípios em cada classe do MS; `municipios` traz
    classe, EHF e máxima por código IBGE. Resposta sem as marcas esperadas devolve {} —
    o coletor trata como lacuna, e não grava dado de origem duvidosa."""
    try:
        alvo = decodificar_tanstack(json.loads(bruto))
    except (ValueError, TypeError):
        return {}
    bloco = ((alvo or {}).get("result") or {})
    if not all(m in bloco for m in CALOR_MS_MARCAS):
        return {}
    por_uf = {}
    for linha in bloco.get("ufData") or []:
        sigla = str((linha or {}).get("sigla_uf") or "").strip().upper()
        if sigla not in UFS:
            continue
        por_uf[sigla] = {c.lower(): (linha.get(c.lower()) or 0) for c in CALOR_MS_CLASSES}
        por_uf[sigla]["total"] = linha.get("total") or 0
    municipios = {}
    for m in ((bloco.get("mapaData") or {}).get("municipios") or []):
        cod = str((m or {}).get("cd_mun") or "").strip()
        if not re.fullmatch(r"\d{7}", cod):
            continue
        municipios[cod] = {"classe": m.get("classification"), "ehf": m.get("ehf"),
                           "tmax": m.get("tmax"), "tmax_pico_p75": m.get("tmax_pico_p75")}
    if not por_uf or not municipios:
        return {}
    janela = bloco.get("operationalWindow") or {}
    return {
        "data": bloco.get("date"),
        "janela": {k: janela.get(k) for k in ("minDate", "latestAvailableDate", "forecastMaxDate", "resolvedAt")},
        "por_uf": por_uf,
        "municipios": municipios,
        "resumo": {c.lower(): bloco.get("total" + c) for c in CALOR_MS_CLASSES},
        "municipios_lidos": bloco.get("totalMunicipios"),
    }


def descobrir_calor_ms(buscar_fn=None, data: str = None) -> tuple:
    """Descobre o endereço da função interna do painel do MS e devolve (payload lido, url usada).

    Três passos, nesta ordem, porque cada um só depende do anterior:
      1. lê a casca e acha o bundle `assets/index-<hash de build>.js`;
      2. no bundle, colhe os handlers `(\\`<64 hex>\\`)` — os NOMES em volta são minificados
         e mudam a cada build, então não servem de âncora;
      3. chama cada handler e aceita o PRIMEIRO cuja resposta traz as marcas do agregado
         de calor. Validar por conteúdo é o que sobrevive a um build novo.
    Levanta ValueError quando nenhum casa: isso é lacuna declarada, não dado aproximado."""
    fn = buscar_fn or (lambda u: buscar(u, origem="painel_calor_ms").decode("utf-8", errors="replace"))
    casca = fn(CALOR_MS_SITIO)
    bundles = re.findall(r"(assets/index-[\w-]+\.js)", casca)
    if not bundles:
        raise ValueError("casca do painel do MS sem bundle assets/index-*.js — formato novo")
    js = fn(CALOR_MS_SITIO + bundles[0])
    handlers = list(dict.fromkeys(re.findall(r"\(`([0-9a-f]{64})`\)", js)))
    if not handlers:
        raise ValueError("bundle do painel do MS sem handler de função interna — formato novo")
    dia = data or hoje_editorial().strftime("%Y-%m-%d")
    payload = {"t": {"t": 10, "i": 0, "p": {"k": ["data"], "v": [
        {"t": 10, "i": 1, "p": {"k": ["date"], "v": [{"t": 1, "s": dia}]}, "o": 0}]}, "o": 0}, "f": 63, "m": []}
    consulta = urllib.parse.quote(json.dumps(payload, separators=(",", ":")), safe="")
    import time
    vazias = 0
    for h in handlers:
        url = f"{CALOR_MS_SITIO}_serverFn/{h}?payload={consulta}"
        bruto = None
        # 24/09/2026 (§209): a recusa com 200 e corpo vazio é TRANSITÓRIA — medida como limite de
        # taxa, não bloqueio: minutos depois o mesmo endereço devolveu os 5.573 municípios. Sem
        # espera, a fonte ficava eternamente em "aguardando primeira coleta" por uma janela de
        # alguns minutos. Esperar é respeitar o limite; insistir sem pausa é o contrário.
        for tentativa in range(3):
            try:
                bruto = fn(url)
            except Exception:
                bruto = None
            if (bruto or "").strip():
                break
            if tentativa < 2:
                time.sleep(15 * (tentativa + 1))
        if bruto is None:
            continue
        # 24/09/2026, medido: este endereço serve HTTP 200 com CORPO VAZIO quando não quer
        # responder — aconteceu 8 vezes em 8 tentativas depois de uma rajada de consultas, e
        # também no navegador, então não é discriminação de cliente. Corpo vazio com 200 é
        # RECUSA, não ausência de dado (§186, §187): tem de subir como falha, nunca ser gravado
        # como "nenhum município em excesso de calor" — que é o que um zero silencioso diria.
        if not (bruto or "").strip():
            vazias += 1
            continue
        if parse_calor_ms(bruto):
            return bruto, url
    if vazias:
        raise ValueError(f"painel do MS respondeu 200 com corpo vazio em {vazias} de {len(handlers)} "
                         "handlers — recusa servida com 200, não ausência de dado")
    raise ValueError(f"nenhum dos {len(handlers)} handlers do painel do MS devolveu o agregado de calor")


def parse_infodengue(dados) -> dict:
    """Última semana epidemiológica disponível: {se, casos_est, casos, nivel, data}. Função pura.
    Níveis do InfoDengue: 1 verde, 2 amarelo, 3 laranja, 4 vermelho (vocabulário DA FONTE)."""
    if not isinstance(dados, list) or not dados:
        return {}
    ult = max(dados, key=lambda r: (r.get("SE") or 0))
    return {"se": ult.get("SE"), "casos_est": ult.get("casos_est"), "casos_notif": ult.get("casos"),
            "nivel": ult.get("nivel"), "data_iniSE": ult.get("data_iniSE")}


def parse_serie_infodengue(dados) -> dict:
    """{'AAAA-SS': casos_est} de uma resposta multi-ano do InfoDengue (SE no formato AAAASS). Função pura."""
    out = {}
    for r in (dados if isinstance(dados, list) else []):
        se = r.get("SE"); v = r.get("casos_est")
        if isinstance(se, int) and se >= 200000 and v is not None:
            out[f"{se // 100}-{se % 100:02d}"] = float(v)
    return out


def somar_series(series: list) -> dict:
    """Soma por semana (AAAA-SS) as séries das capitais → {ano: {SS: total}}. Função pura."""
    tot = {}
    for serie in series:
        for chave, v in serie.items():
            ano, ss = chave.split("-")
            tot.setdefault(ano, {})[ss] = round(tot.setdefault(ano, {}).get(ss, 0.0) + v, 1)
    return tot


def coletar():
    _, por_nome = referencia_ibge()
    sinais = ler("saude_sinais.json"); ano = hoje_editorial().year; ok = lac = 0
    series_capitais = []   # 05/09/2026: série semanal 2024–2026 (27 capitais somadas) para o gráfico da página de Saúde
    for uf, cap in CAPITAIS.items():
        cod = por_nome.get((cap, uf))
        url = INFODENGUE_API.format(geocode=cod, ano=ano)
        try:
            bruto = buscar(url, timeout=30); dados = json.loads(bruto.decode("utf-8", "replace"))
        except Exception as e:  # noqa: BLE001
            registrar_lacuna(f"InfoDengue/{cap}-{uf}", type(e).__name__, canal="DOU", camada=1, uf=uf, municipio=cap, ibge=cod, strings=[url]); lac += 1
            continue
        h = preservar_evidencia(bruto, url, "json", "coletar_saude")
        r = parse_infodengue(dados)
        # série 2024–2026 da capital (mesma API, janela de três anos)
        try:
            url_s = INFODENGUE_API.format(geocode=cod, ano=ano).replace(f"ey_start={ano}", f"ey_start={ano-2}")
            series_capitais.append(parse_serie_infodengue(json.loads(buscar(url_s, timeout=45).decode("utf-8", "replace"))))
        except Exception as e:  # noqa: BLE001
            registrar_lacuna(f"InfoDengue série/{cap}-{uf}", type(e).__name__, canal="DOU", camada=1, uf=uf, municipio=cap, ibge=cod)
        if r:
            sinais["dengue_capitais"][uf] = {**r, "municipio": cap, "ibge": cod, "fonte": "modelo InfoDengue (Fiocruz/FGV)",
                                             "url": url, "coletado_em": hoje_editorial().strftime("%d/%m/%Y"), "hash_evidencia": h}
            ok += 1
        log_busca("DOU", 1, [url], "registro" if r else "pista", uf=uf, municipio=cap, ibge=cod, nivel=None,
                  n_resultados=len(dados) if isinstance(dados, list) else 0, resultados=f"InfoDengue: {r}", hash_evidencia=h)
    hoje_br = hoje_editorial().strftime("%d/%m/%Y")
    if ok:
        sinais["fontes"]["infodengue"]["status"] = "coletado"
        sinais["fontes"]["infodengue"]["ultima_coleta_ok"] = hoje_br
        sinais["fontes"]["infodengue"].pop("ultima_tentativa_falhou", None)
    elif sinais.get("dengue_capitais"):
        # 03/09/2026: tentativa sem rede NÃO rebaixa uma coleta anterior — os dados exibidos continuam
        # sendo os da última coleta bem-sucedida, e a falha fica declarada ao lado.
        sinais["fontes"]["infodengue"]["status"] = "coletado"
        sinais["fontes"]["infodengue"]["ultima_tentativa_falhou"] = hoje_br
    else:
        sinais["fontes"]["infodengue"]["status"] = "aguardando_primeira_coleta"
    sinais["fontes"]["infodengue"]["consultado_em"] = hoje_br
    if series_capitais:
        sinais["serie_capitais"] = {"medida": "casos estimados de dengue por semana epidemiológica, soma das 27 capitais (InfoDengue) — não é o total nacional",
                                    "capitais": len(series_capitais), "anos": somar_series(series_capitais), "coletado_em": hoje_br}
    # ---- Painel Nacional de Excesso de Calor (MS) — 24/09/2026 -------------------
    # Falha aqui NÃO rebaixa coleta anterior e NÃO grava zero: o motivo fica declarado ao lado
    # do status, para que a página diga por que não há número em vez de mostrar um.
    fonte_calor = sinais["fontes"].setdefault("painel_calor_ms", {
        "nome": "Painel Nacional de Excesso de Calor", "orgao": "Ministério da Saúde",
        "papel": "classe de excesso de calor por município (índice EHF), no vocabulário do MS",
        "url_publica": CALOR_MS_SITIO, "status": "aguardando_primeira_coleta", "consultado_em": None})
    try:
        bruto_calor, url_calor = descobrir_calor_ms()
        lido = parse_calor_ms(bruto_calor)
        if not lido:
            raise ValueError("resposta do painel do MS sem o agregado de calor")
        sinais["calor_excesso"] = {
            **lido, "fonte": "painel_calor_ms", "orgao": "Ministério da Saúde",
            "documento": f"Painel Nacional de Excesso de Calor, dia {lido.get('data')}",
            "vocabulario": list(CALOR_MS_CLASSES),
            "url": CALOR_MS_SITIO, "coletado_em": hoje_br,
            "hash_evidencia": preservar_evidencia(bruto_calor.encode("utf-8"), url_calor, "json", "coletar_saude"),
        }
        fonte_calor.update({"status": "coletado", "consultado_em": hoje_br,
                            "documento": sinais["calor_excesso"]["documento"]})
        fonte_calor.pop("ultima_tentativa_falhou", None)
        fonte_calor.pop("motivo_da_falha", None)
        print(f"Excesso de calor (MS): {len(lido['por_uf'])} UFs, {len(lido['municipios'])} municípios")
    except Exception as e:  # noqa: BLE001
        motivo = f"{type(e).__name__}: {e}"
        fonte_calor["consultado_em"] = hoje_br
        fonte_calor["ultima_tentativa_falhou"] = hoje_br
        fonte_calor["motivo_da_falha"] = motivo
        if not sinais.get("calor_excesso"):
            fonte_calor["status"] = "aguardando_primeira_coleta"
        registrar_lacuna("Painel de Excesso de Calor (MS)", motivo, canal="DOU", camada=1,
                         strings=[CALOR_MS_SITIO])
        print(f"[aviso] excesso de calor (MS) não coletado — {motivo}")

    sinais["gerado_em"] = hoje_editorial().strftime("%d/%m/%Y")
    gravar("saude_sinais.json", sinais)
    print(f"InfoDengue: {ok} capitais coletadas, {lac} lacunas")
    return 0


# Fixture do painel do MS (24/09/2026): escrita como dado PLANO e serializada pelo `_serializar`
# abaixo, que é o inverso exato de `decodificar_tanstack`. Escrever o aninhado à mão é ilegível e
# foi onde este arquivo quebrou na primeira tentativa; assim a fixture diz o que significa, e o
# ida-e-volta prova o decodificador contra a forma real da resposta.
_CALOR_PLANO = {"result": {
    "error": None, "apiDown": None,
    "operationalWindow": {"minDate": "2009-01-01", "latestAvailableDate": "2026-09-24",
                          "forecastMaxDate": "2026-09-28", "resolvedAt": "2026-09-24T14:29:11.621Z"},
    "ufData": [{"sigla_uf": "MG", "normal": 853, "baixo": 0, "severo": 0, "extremo": 0, "total": 853},
               {"sigla_uf": "PA", "normal": 137, "baixo": 1, "severo": 5, "extremo": 1, "total": 144}],
    "regiaoData": [],
    "mapaData": {"municipios": [
        {"cd_mun": "1301803", "classification": "Normal", "ehf": 0, "tmax": 33.7, "tmax_pico_p75": 34.84},
        {"cd_mun": "1500602", "classification": "Severo", "ehf": 3.4, "tmax": 38.2, "tmax_pico_p75": 35.1}]},
    "date": "2026-09-24", "totalMunicipios": 5573,
    "totalNormal": 990, "totalBaixo": 1, "totalSevero": 5, "totalExtremo": 1,
}}


def _serializar(v):
    """Inverso de `decodificar_tanstack`, só para as fixtures do autoteste. Função pura."""
    if isinstance(v, dict):
        return {"t": 10, "p": {"k": list(v), "v": [_serializar(x) for x in v.values()]}}
    if isinstance(v, list):
        return {"t": 9, "a": [_serializar(x) for x in v]}
    if v is None:
        return {"t": 2, "s": 3}
    return {"t": 1 if isinstance(v, str) else 0, "s": v}


_FIX_CALOR = _serializar(_CALOR_PLANO)

FIX = [{"SE": 202634, "casos_est": 12.3, "casos": 10, "nivel": 2, "data_iniSE": "2026-08-23"},
       {"SE": 202635, "casos_est": 15.0, "casos": 9, "nivel": 3, "data_iniSE": "2026-08-30"}]


def autoteste():
    def t1(): r = parse_infodengue(FIX); return r["se"] == 202635 and r["nivel"] == 3
    def t2(): return parse_infodengue([]) == {} and parse_infodengue(None) == {} and parse_infodengue({"erro": 1}) == {}
    def t3():
        # 03/09/2026: o autoteste NUNCA toca os dados reais — semeia e restaura byte a byte
        # (antes, rodar --autoteste apagava a coleta do InfoDengue do repositório).
        import coletores_base as cb
        nomes = ("saude_federal.json", "saude_uf.json", "saude_sinais.json")
        antes = {n: (cb.DATA / n).read_bytes() if (cb.DATA / n).exists() else None for n in nomes}
        try:
            semear(); u = ler("saude_uf.json")["uf"]; return len(u) == 27 and all(v["status"] == "NAO_VERIFICADO" for v in u.values())
        finally:
            for n, b in antes.items():
                if b is not None: (cb.DATA / n).write_bytes(b)
    def t4(): f = ler("saude_federal.json"); return all(c["url"] is None or c["url"].startswith("https://www.gov.br/") for c in f["cartoes"])
    def t7():  # série: SE AAAASS → 'AAAA-SS'; soma de capitais por semana; malformado ignorado
        a = parse_serie_infodengue([{"SE": 202601, "casos_est": 10.5}, {"SE": 202602, "casos_est": 2}, {"SE": "x", "casos_est": 1}, {"SE": 202601}])
        b = parse_serie_infodengue([{"SE": 202601, "casos_est": 4.5}, {"SE": 202503, "casos_est": 7}])
        t = somar_series([a, b])
        return a == {"2026-01": 10.5, "2026-02": 2.0} and t["2026"]["01"] == 15.0 and t["2026"]["02"] == 2.0 and t["2025"]["03"] == 7.0 and parse_serie_infodengue(None) == {}
    def t5():  # negativo: autoteste não altera dados reais (o próprio t3 já rodou)
        import coletores_base as cb
        return (cb.DATA / "saude_sinais.json").read_bytes() == _SNAP
    def t6():  # falha de rede não rebaixa coleta válida: regra de status
        fontes = {"infodengue": {"status": "coletado"}}
        def regra(ok, tem_dados):
            if ok: return "coletado"
            return "coletado" if tem_dados else "aguardando_primeira_coleta"
        return regra(0, True) == "coletado" and regra(0, False) == "aguardando_primeira_coleta" and regra(3, False) == "coletado"
    # ---- Painel de Excesso de Calor do MS (24/09/2026) ----
    def t8():  # decodificador da serialização própria do app do MS
        no = {"t": 10, "p": {"k": ["a", "b"], "v": [{"t": 1, "s": "texto"}, {"t": 0, "s": 7}]}}
        lista = {"t": 9, "a": [{"t": 0, "s": 1}, {"t": 0, "s": 2}]}
        return (decodificar_tanstack(no) == {"a": "texto", "b": 7}
                and decodificar_tanstack(lista) == [1, 2]
                and decodificar_tanstack({"t": 2, "s": 3}) is None
                and decodificar_tanstack({"t": 99}) is None
                and decodificar_tanstack("cru") == "cru")

    def t9():  # formato REAL do painel (fixture reduzida da resposta de 24/09/2026)
        lido = parse_calor_ms(json.dumps(_FIX_CALOR))
        return (lido["data"] == "2026-09-24"
                and lido["por_uf"]["PA"]["severo"] == 5 and lido["por_uf"]["PA"]["total"] == 144
                and lido["municipios"]["1301803"]["classe"] == "Normal"
                and lido["municipios"]["1301803"]["tmax"] == 33.7
                and lido["janela"]["forecastMaxDate"] == "2026-09-28")

    def t10():  # negativo: resposta sem as marcas do agregado NÃO vira dado
        semMarcas = {"t": 10, "p": {"k": ["result"], "v": [{"t": 10, "p": {"k": ["outra"], "v": [{"t": 0, "s": 1}]}}]}}
        return (parse_calor_ms(json.dumps(semMarcas)) == {}
                and parse_calor_ms("") == {} and parse_calor_ms("nao é json") == {})

    def t11():  # negativo: UF fora das 27 e código IBGE inválido não entram
        # Monta a partir do dado PLANO, não indexando o aninhado por posição: assim o teste não
        # depende da ordem das chaves da fixture.
        sujo = json.loads(json.dumps(_CALOR_PLANO))
        sujo["result"]["ufData"].append({"sigla_uf": "ZZ", "normal": 9, "baixo": 0, "severo": 0,
                                         "extremo": 0, "total": 9})
        sujo["result"]["mapaData"]["municipios"].append({"cd_mun": "abc", "classification": "Extremo",
                                                         "ehf": 9, "tmax": 40, "tmax_pico_p75": 39})
        lido = parse_calor_ms(json.dumps(_serializar(sujo)))
        return ("ZZ" not in lido["por_uf"] and "abc" not in lido["municipios"]
                and len(lido["por_uf"]) == 2 and len(lido["municipios"]) == 2)

    def t12():  # 200 com corpo VAZIO é recusa, não ausência — nunca vira zero município
        chamadas = []
        def falso(url):
            chamadas.append(url)
            if url.endswith("/"): return '<script src="assets/index-abc123.js"></script>'
            if url.endswith(".js"): return 'handler(`' + ("a" * 64) + '`)'
            return "   "                      # 200 com corpo vazio
        try:
            descobrir_calor_ms(buscar_fn=falso, data="2026-09-24")
        except ValueError as e:
            return "corpo vazio" in str(e) and "recusa" in str(e)
        return False

    def t13():  # a descoberta valida POR CONTEÚDO, não por posição nem por nome minificado
        bom = "b" * 64
        def falso(url):
            if url.endswith("/"): return '<script src="assets/index-abc123.js"></script>'
            if url.endswith(".js"): return 'x(`' + ("a" * 64) + '`)' + 'y(`' + bom + '`)'
            if bom in url: return json.dumps(_FIX_CALOR)
            return json.dumps({"t": 10, "p": {"k": ["result"], "v": [{"t": 1, "s": "outra coisa"}]}})
        bruto, url = descobrir_calor_ms(buscar_fn=falso, data="2026-09-24")
        return bom in url and parse_calor_ms(bruto)["por_uf"]["MG"]["normal"] == 853

    import coletores_base as cb
    _SNAP = (cb.DATA / "saude_sinais.json").read_bytes() if (cb.DATA / "saude_sinais.json").exists() else b""
    return rodar_autoteste({"parser InfoDengue: última SE": t1, "negativo: resposta vazia/malformada": t2,
                            "semear: 27 UFs NAO_VERIFICADO (sem tocar os dados reais)": t3, "cartões federais: nenhum link fora de gov.br": t4,
                            "negativo: autoteste não altera dados reais": t5, "status: falha de rede não rebaixa coleta válida": t6,
                            "série 2024–2026: parse e soma das capitais": t7,
                            "MS calor: decodifica a serialização própria do app": t8,
                            "MS calor: lê o formato real (UF, município, EHF, janela)": t9,
                            "MS calor negativo: resposta sem as marcas do agregado não vira dado": t10,
                            "MS calor negativo: UF inválida e código IBGE inválido não entram": t11,
                            "MS calor: 200 com corpo vazio é RECUSA, não ausência": t12,
                            "MS calor: descoberta valida por CONTEÚDO, não por nome minificado": t13})


if __name__ == "__main__":
    if "--autoteste" in sys.argv: sys.exit(autoteste())
    if "--semear" in sys.argv: semear(); sys.exit(0)
    sys.exit(coletar())
