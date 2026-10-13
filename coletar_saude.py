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



def risco_projetado(texto: str) -> list:
    """Riscos sanitários derivados do campo "risco" do boletim (consist.json), sem projeção nova.

    11/10/2026 (Relatório D, A5-16): boletim sem sinal ("Sem sinal elevado no trimestre", ES e RJ)
    caía em "chuvas", e risco vazio em "multi" — risco que o boletim não projeta. Sem sinal de seca
    nem de chuva, a lista fica vazia e a página diz "sem risco previsto registrado". Função pura."""
    r = str(texto or "").lower()
    tem_seca = any(k in r for k in ("seca", "estiagem", "incêndio", "incendio", "calor"))
    tem_chuva = any(k in r for k in ("chuva", "enchente", "inunda", "alagamento"))
    tipo = "multi" if tem_seca and tem_chuva else "seca" if tem_seca else "chuvas" if tem_chuva else None
    return list(RISCO_SANITARIO[tipo]) if tipo else []


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
                   {"titulo": "Painel Nacional de Excesso de Calor", "orgao": "Ministério da Saúde",
                    "data": "leitura até 25/09/2026", "url": "https://clima.saude.gov.br/", "status": "localizado",
                    "nota": "Localizado em clima.saude.gov.br; leitura até 25/09/2026, sem resposta legível desde então."},
                   {"titulo": "VigiAR · GeoRisk",
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
        risco = str(c.get("risco", "")) if isinstance(c, dict) else ""
        ufs[uf] = {"status": "NAO_VERIFICADO", "orgao": None, "doc": None, "numero": None, "data": None, "url": None,
                   "hash_evidencia": None, "natureza_doc": "nenhum", "justificativa_ex_ante": None,
                   "risco_sanitario_projetado": risco_projetado(risco), "consist": "NEUTRO",
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
# O painel de clima.saude.gov.br não publica API. 13/10/2026 (decisão 10 da central, sonda do
# runner, run 38441817094): a página já vem com o agregado do dia renderizado no servidor — `ufData`,
# `mapaData` com os 5.571 municípios, totais e `operationalWindow` —, em literal de objeto JS. A rota
# antiga (achar o bundle, colher os hashes `/_serverFn/<sha256>` e chamar cada um) quebrou com o build
# novo depois de 25/09: os cinco handlers passaram a responder 200 com corpo vazio sem o cabeçalho
# próprio do framework. Ler a página que o leitor recebe é a rota que não depende de build.
#
# O vocabulário de severidade é O DO MS (Normal, Baixo, Severo, Extremo). O projeto não reescala nada.
# ---------------------------------------------------------------------------------
CALOR_MS_SITIO = "https://clima.saude.gov.br/"
CALOR_MS_CLASSES = ("Normal", "Baixo", "Severo", "Extremo")
_NUM = r"(-?[\d.]+(?:e-?\d+)?|null)"


def _num(v):
    return None if v in (None, "null") else (int(v) if re.fullmatch(r"-?\d+", v) else float(v))


def parse_calor_ms(pagina: str) -> dict:
    """Lê o agregado de excesso de calor da página do painel do MS e devolve
    {'data','janela','por_uf','municipios','resumo','municipios_lidos'}. Função pura.

    Página sem `ufData` e `mapaData` — inclusive 200 com corpo vazio, que é recusa — devolve {}: o
    coletor trata como lacuna, e não grava dado de origem duvidosa."""
    pagina = pagina or ""
    a, b = pagina.find("ufData:"), pagina.find("mapaData:")
    if a < 0 or b < a:
        return {}
    por_uf = {}
    for m in re.finditer(r'sigla_uf:"(\w\w)",normal:(\d+),baixo:(\d+),severo:(\d+),extremo:(\d+),total:(\d+)',
                         pagina[a:b]):
        if m.group(1) in UFS:
            por_uf[m.group(1)] = dict(zip(("normal", "baixo", "severo", "extremo", "total"),
                                          map(int, m.groups()[1:])))
    municipios = {}
    padrao_mun = (r'cd_mun:"(\d{7})",classification:"(\w+)",ehf:' + _NUM + r",tmax:" + _NUM
                  + r",tmax_pico_p75:" + _NUM)
    for m in re.finditer(padrao_mun, pagina[b:]):
        municipios.setdefault(m.group(1), {"classe": m.group(2), "ehf": _num(m.group(3)),
                                           "tmax": _num(m.group(4)), "tmax_pico_p75": _num(m.group(5))})
    tot = re.search(r'date:"(\d{4}-\d\d-\d\d)",totalSeveroExtremo:\d+,totalExtremo:(\d+),totalSevero:(\d+),'
                    r"totalBaixo:(\d+),totalNormal:(\d+),totalMunicipios:(\d+)", pagina)
    if not por_uf or not municipios or not tot:
        return {}
    janela = {c: (re.search(c + r':"([^"]+)"', pagina) or [None, None])[1]
              for c in ("minDate", "latestAvailableDate", "forecastMaxDate", "resolvedAt")}
    return {"data": tot.group(1), "janela": janela, "por_uf": por_uf, "municipios": municipios,
            "resumo": {"extremo": int(tot.group(2)), "severo": int(tot.group(3)),
                       "baixo": int(tot.group(4)), "normal": int(tot.group(5))},
            "municipios_lidos": int(tot.group(6))}


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


# 11/10/2026 (HANDOVER_SAUDE, item 1.4): fonte "a verificar" há semanas não é fonte exibida, é
# pendência sem prazo. As duas abaixo não têm coletor, e o motivo é este — dito, não escondido.
LACUNAS_DECLARADAS = {
    "painel_arboviroses_ms": "sem coletor: o MS publica microdado do Sinan, não a série semanal do "
                             "painel; a contagem de casos da página vem do Sinan agregado "
                             "(coletar_arboviroses_sinan.py) e do InfoDengue, com crédito",
    "sisagua": "sem coletor automático: não há endereço público estável da série de intermitência "
               "por município localizado até o corte",
}


LIMITE_DIAS_DADO = 9


def vencer_calor(sinais: dict, fonte: dict, motivo: str, hoje) -> dict:
    """Coleta do calor falhou: dado de mais de 9 dias deixa de ser "a consulta mais recente".

    11/10/2026 (HANDOVER_SAUDE, item 1.6): o painel do MS parou de responder em 25/09 e a página
    seguiu mostrando aquela fotografia como "consulta mais recente" por 16 dias. Passado o
    limite, o retrato sai de `calor_excesso` (a página passa a dizer que não há coleta) e fica
    guardado em `calor_excesso_anterior`; a fonte vira lacuna declarada, com o motivo e a data
    da última coleta boa. Função pura sobre os dicionários (só os altera)."""
    from datetime import datetime
    cal = sinais.get("calor_excesso") or {}
    ultima = fonte.get("ultima_coleta_ok") or cal.get("coletado_em")
    if ultima:
        fonte["ultima_coleta_ok"] = ultima
    try:
        idade = (hoje - datetime.strptime(str(ultima)[:10], "%d/%m/%Y").date()).days
    except (TypeError, ValueError):
        idade = None
    if idade is not None and idade > LIMITE_DIAS_DADO:
        if cal:  # F46: na 2ª falha seguida o retrato já está guardado; não sobrescrever com {}
            sinais["calor_excesso_anterior"] = cal
        sinais.pop("calor_excesso", None)
        fonte["status"] = "lacuna"
        fonte["motivo"] = f"painel do MS sem resposta legível desde a coleta de {ultima}: {motivo}"[:300]
    return sinais


def falha_calor(sinais: dict, fonte: dict, motivo: str, hoje) -> dict:
    """Coleta do calor falhou. "Aguardando primeira coleta" só quando NUNCA houve coleta boa.

    F46 (13/10/2026): depois de `vencer_calor` tirar `calor_excesso`, a falha da noite seguinte
    testava só `calor_excesso` e rebaixava a lacuna declarada para "aguardando primeira coleta",
    apagando a data da última coleta boa da leitura da página. Função pura sobre os dicionários."""
    ja_coletou = (sinais.get("calor_excesso") or sinais.get("calor_excesso_anterior")
                  or fonte.get("ultima_coleta_ok"))
    if not ja_coletou:
        fonte["status"] = "aguardando_primeira_coleta"
        return sinais
    return vencer_calor(sinais, fonte, motivo, hoje)


def declarar_lacunas(fontes: dict) -> dict:
    """Troca "a verificar" pela lacuna declarada com motivo. Função pura sobre o dicionário."""
    for nome, motivo in LACUNAS_DECLARADAS.items():
        f = fontes.get(nome)
        if isinstance(f, dict) and f.get("status") in ("a_verificar", None, ""):
            f["status"] = "lacuna"
            f["motivo"] = motivo
    return fontes


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
        bruto_calor, url_calor = buscar(CALOR_MS_SITIO, origem="painel_calor_ms").decode("utf-8", errors="replace"), CALOR_MS_SITIO
        lido = parse_calor_ms(bruto_calor)
        if not lido:
            raise ValueError("resposta do painel do MS sem o agregado de calor")
        sinais["calor_excesso"] = {
            **lido, "fonte": "painel_calor_ms", "orgao": "Ministério da Saúde",
            "documento": f"Painel Nacional de Excesso de Calor, dia {lido.get('data')}",
            "vocabulario": list(CALOR_MS_CLASSES),
            "url": CALOR_MS_SITIO, "coletado_em": hoje_br,
            "hash_evidencia": preservar_evidencia(bruto_calor.encode("utf-8"), url_calor, "html", "coletar_saude"),
        }
        fonte_calor.update({"status": "coletado", "consultado_em": hoje_br, "ultima_coleta_ok": hoje_br,
                            "documento": sinais["calor_excesso"]["documento"]})
        fonte_calor.pop("ultima_tentativa_falhou", None)
        fonte_calor.pop("motivo_da_falha", None)
        print(f"Excesso de calor (MS): {len(lido['por_uf'])} UFs, {len(lido['municipios'])} municípios")
    except Exception as e:  # noqa: BLE001
        motivo = f"{type(e).__name__}: {e}"
        fonte_calor["consultado_em"] = hoje_br
        fonte_calor["ultima_tentativa_falhou"] = hoje_br
        fonte_calor["motivo_da_falha"] = motivo
        falha_calor(sinais, fonte_calor, motivo, hoje_editorial())
        registrar_lacuna("Painel de Excesso de Calor (MS)", motivo, canal="DOU", camada=1,
                         strings=[CALOR_MS_SITIO])
        print(f"[aviso] excesso de calor (MS) não coletado — {motivo}")

    declarar_lacunas(sinais["fontes"])
    sinais["gerado_em"] = hoje_editorial().strftime("%d/%m/%Y")
    gravar("saude_sinais.json", sinais)
    print(f"InfoDengue: {ok} capitais coletadas, {lac} lacunas")
    return 0


# Fixture do painel do MS: trecho reduzido da página real de 13/10/2026 (sonda do runner), no
# literal de objeto JS que o servidor renderiza.
_FIX_CALOR = ('<script>$R[16]={error:!1,apiDown:!1,operationalWindow:$R[17]={minDate:"2009-01-01",'
              'latestAvailableDate:"2026-10-13",forecastMaxDate:"2026-10-17",resolvedAt:"2026-10-13T17:33:27.705Z",'
              'source:"ehf/agregado/regiao"},ufData:$R[18]=[$R[19]={sigla_uf:"MG",normal:853,baixo:0,severo:0,'
              'extremo:0,total:853},$R[21]={sigla_uf:"PA",normal:135,baixo:2,severo:6,extremo:1,total:144},'
              '$R[22]={sigla_uf:"ZZ",normal:9,baixo:0,severo:0,extremo:0,total:9}],regiaoData:$R[50]=[$R[51]='
              '{nm_regiao:"Centro-Oeste",normal:468,baixo:0,severo:0,extremo:0,total:468}],mapaData:$R[52]='
              '{municipios:$R[53]=[$R[54]={cd_mun:"1301803",classification:"Normal",ehf:0,tmax:33.7,'
              'tmax_pico_p75:34.84},$R[55]={cd_mun:"1500602",classification:"Severo",ehf:3.4,tmax:38.2,'
              'tmax_pico_p75:null},$R[56]={cd_mun:"abc",classification:"Extremo",ehf:9,tmax:40,tmax_pico_p75:39}]},'
              'date:"2026-10-13",totalSeveroExtremo:7,totalExtremo:1,totalSevero:6,totalBaixo:2,totalNormal:988,'
              'totalMunicipios:5571,previousDayTotals:$R[5629]={date:"2026-10-12"}}</script>')

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
    def t4b():  # A5-16: sem sinal → lista vazia; seca, chuva e as duas → família certa
        return (risco_projetado("Sem sinal elevado no trimestre") == [] and risco_projetado("") == []
                and risco_projetado("Seca em intensificação") == RISCO_SANITARIO["seca"]
                and risco_projetado("Chuvas acima da média") == RISCO_SANITARIO["chuvas"]
                and risco_projetado("Seca no norte e chuvas no sul") == RISCO_SANITARIO["multi"])
    def t4(): f = ler("saude_federal.json"); return all(c["url"] is None or re.match(r"https://([a-z0-9-]+\.)*gov\.br/", c["url"]) for c in f["cartoes"])
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
    def t9():  # formato REAL da página do painel (13/10/2026): UF, município, EHF, janela, totais
        lido = parse_calor_ms(_FIX_CALOR)
        return (lido["data"] == "2026-10-13"
                and lido["por_uf"]["PA"]["severo"] == 6 and lido["por_uf"]["PA"]["total"] == 144
                and lido["municipios"]["1301803"]["classe"] == "Normal"
                and lido["municipios"]["1301803"]["tmax"] == 33.7
                and lido["municipios"]["1500602"]["tmax_pico_p75"] is None
                and lido["resumo"]["severo"] == 6 and lido["municipios_lidos"] == 5571
                and lido["janela"]["forecastMaxDate"] == "2026-10-17")

    def t10():  # negativo: página sem o agregado, ou 200 com corpo vazio (recusa), NÃO vira dado
        return (parse_calor_ms(_FIX_CALOR.replace("mapaData", "outra")) == {}
                and parse_calor_ms("") == {} and parse_calor_ms("   ") == {} and parse_calor_ms(None) == {})

    def t11():  # negativo: UF fora das 27 e código IBGE inválido não entram
        lido = parse_calor_ms(_FIX_CALOR)
        return "ZZ" not in lido["por_uf"] and "abc" not in lido["municipios"] and len(lido["municipios"]) == 2

    def t14():  # "a verificar" vira lacuna com motivo; fonte coletada não é tocada
        f = declarar_lacunas({"sisagua": {"status": "a_verificar"}, "infodengue": {"status": "coletado"}})
        return (f["sisagua"]["status"] == "lacuna" and "sem coletor" in f["sisagua"]["motivo"]
                and f["infodengue"] == {"status": "coletado"})
    def t15():  # calor que falha há mais de 9 dias vira lacuna e sai da "consulta mais recente"
        from datetime import date
        ss = {"calor_excesso": {"coletado_em": "25/09/2026", "resumo": {}}}
        f = {"status": "coletado"}
        vencer_calor(ss, f, "ValueError: x", date(2026, 10, 11))
        recente = {"calor_excesso": {"coletado_em": "08/10/2026"}}
        g = {"status": "coletado"}
        vencer_calor(recente, g, "x", date(2026, 10, 11))
        return ("calor_excesso" not in ss and ss["calor_excesso_anterior"]["coletado_em"] == "25/09/2026"
                and f["status"] == "lacuna" and "25/09/2026" in f["motivo"]
                and f["ultima_coleta_ok"] == "25/09/2026"
                and "calor_excesso" in recente and g["status"] == "coletado"
                and g["ultima_coleta_ok"] == "08/10/2026")
    def t16():  # F46: segunda falha seguida depois de vencer mantém a lacuna, não volta a "aguardando"
        from datetime import date
        ss = {"calor_excesso": {"coletado_em": "25/09/2026", "resumo": {}}}
        f = {"status": "coletado"}
        falha_calor(ss, f, "1ª", date(2026, 10, 11))
        falha_calor(ss, f, "2ª", date(2026, 10, 12))
        g = {"status": "lacuna", "ultima_coleta_ok": "25/09/2026"}   # estado já rebaixado: se repõe
        sg = {"calor_excesso_anterior": {"coletado_em": "25/09/2026"}}
        falha_calor(sg, g, "3ª", date(2026, 10, 13))
        nunca = {}; n = {"status": "aguardando_primeira_coleta"}
        falha_calor(nunca, n, "x", date(2026, 10, 13))
        return (f["status"] == "lacuna" and "2ª" in f["motivo"] and f["ultima_coleta_ok"] == "25/09/2026"
                and ss["calor_excesso_anterior"]["coletado_em"] == "25/09/2026" and "calor_excesso" not in ss
                and g["status"] == "lacuna" and sg["calor_excesso_anterior"]["coletado_em"] == "25/09/2026"
                and n["status"] == "aguardando_primeira_coleta" and "calor_excesso_anterior" not in nunca)
    import coletores_base as cb
    _SNAP = (cb.DATA / "saude_sinais.json").read_bytes() if (cb.DATA / "saude_sinais.json").exists() else b""
    return rodar_autoteste({"parser InfoDengue: última SE": t1, "negativo: resposta vazia/malformada": t2,
                            "semear: 27 UFs NAO_VERIFICADO (sem tocar os dados reais)": t3, "cartões federais: nenhum link fora de gov.br": t4, "A5-16: boletim sem sinal não vira risco de chuvas": t4b,
                            "negativo: autoteste não altera dados reais": t5, "status: falha de rede não rebaixa coleta válida": t6,
                            "série 2024–2026: parse e soma das capitais": t7,
                            "MS calor: lê a página real (UF, município, EHF, janela, totais)": t9,
                            "MS calor negativo: página sem o agregado, ou vazia (recusa), não vira dado": t10,
                            "MS calor negativo: UF inválida e código IBGE inválido não entram": t11,
                            "fonte sem coletor vira lacuna declarada com motivo": t14,
                            "calor parado há mais de 9 dias vira lacuna, não 'consulta mais recente'": t15,
                            "F46: 2ª falha seguida mantém a lacuna com a última coleta boa": t16})


if __name__ == "__main__":
    if "--autoteste" in sys.argv: sys.exit(autoteste())
    if "--semear" in sys.argv: semear(); sys.exit(0)
    sys.exit(coletar())
