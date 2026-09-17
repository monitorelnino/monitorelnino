#!/usr/bin/env python3
"""
coletar_sinais_risco.py
=======================
Coletor das três camadas de SINAIS OFICIAIS DE RISCO exibidas em
`monitor-de-riscos.html` (METODOLOGIA §23).

ESTATUTO DESTE MÓDULO — leia antes de mexer
-------------------------------------------
1. **Peso zero, sempre.** Nada que este script escreve entra no índice MARÉ.
   `data/sinais_risco.json` é registro de transparência, no mesmo estatuto de
   `data/atos_resposta.json`: mostrado, datado, nunca pontuado. Qualquer
   mudança que faça um sinal pontuar é mudança de MÉTODO (versão maior,
   PROTOCOLO_ATUALIZACAO §3.2).
2. **Reprodução, nunca previsão.** O Monitor não faz previsão climática. Cada
   valor publicado é a reprodução de um número ou rótulo que um órgão oficial
   já publicou, com documento e data. O vocabulário de severidade é o DA FONTE
   (S0-S4 do Monitor de Secas, "perigo potencial" do INMET, °C do ONI). O
   projeto não cria escala de dano própria — proibição registrada na
   transferência conceitual §11.
3. **Nada inventado.** Fonte não coletada fica com status
   `aguardando_primeira_coleta` e a página mostra a lacuna declarada. Nenhum
   valor é preenchido por memória, estimativa ou interpolação.
4. **Falha de rede não derruba o pipeline.** Padrão de `atualizar_boletins.py`:
   aviso no log e saída 0; o registro anterior permanece intacto.

USO
---
  python coletar_sinais_risco.py --autoteste   # prova os parsers contra fixtures (sem rede)
  python coletar_sinais_risco.py --semear      # (re)cria o registro a partir do que já é verificado no repositório
  python coletar_sinais_risco.py               # coleta as três camadas (precisa de rede aberta)
  python coletar_sinais_risco.py --camada enos # coleta só uma camada

As três camadas (METODOLOGIA §23.2):
  ciclo      — Painel El Niño 2026-2027 (CEMADEN/INPE): risco projetado por UF
  observado  — Monitor de Secas (ANA), avisos INMET, risco de fogo (INPE), alertas CEMADEN
  enos       — ONI/CPC-NOAA, plume IRI, prognóstico trimestral INMET/CPTEC
"""
import json
import pathlib
import re
import sys
import urllib.error
import urllib.request
from datetime import date, datetime

RAIZ = pathlib.Path(__file__).parent
REGISTRO = RAIZ / "data" / "sinais_risco.json"
CONSIST = RAIZ / "data" / "consist.json"
BOLETINS = RAIZ / "data" / "boletins.json"
UFS = ["AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT",
       "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO"]
TEMPO_LIMITE = 25
# Código IBGE de cada UF (2 dígitos) — usado pelo RPC de dados tabulares do Monitor de Secas
# (parâmetro `area`) e para ler os `geocodes` (7 dígitos) dos avisos do INMET.
IBGE_UF = {"RO": 11, "AC": 12, "AM": 13, "RR": 14, "PA": 15, "AP": 16, "TO": 17, "MA": 21, "PI": 22, "CE": 23, "RN": 24,
           "PB": 25, "PE": 26, "AL": 27, "SE": 28, "BA": 29, "MG": 31, "ES": 32, "RJ": 33, "SP": 35, "PR": 41, "SC": 42,
           "RS": 43, "MS": 50, "MT": 51, "GO": 52, "DF": 53}
UF_POR_IBGE = {v: k for k, v in IBGE_UF.items()}
NOME_PARA_SIGLA = {
    "ACRE": "AC", "ALAGOAS": "AL", "AMAZONAS": "AM", "AMAPÁ": "AP", "AMAPA": "AP",
    "BAHIA": "BA", "CEARÁ": "CE", "CEARA": "CE", "DISTRITO FEDERAL": "DF",
    "ESPÍRITO SANTO": "ES", "ESPIRITO SANTO": "ES", "GOIÁS": "GO", "GOIAS": "GO",
    "MARANHÃO": "MA", "MARANHAO": "MA", "MINAS GERAIS": "MG", "MATO GROSSO DO SUL": "MS",
    "MATO GROSSO": "MT", "PARÁ": "PA", "PARA": "PA", "PARAÍBA": "PB", "PARAIBA": "PB",
    "PERNAMBUCO": "PE", "PIAUÍ": "PI", "PIAUI": "PI", "PARANÁ": "PR", "PARANA": "PR",
    "RIO DE JANEIRO": "RJ", "RIO GRANDE DO NORTE": "RN", "RONDÔNIA": "RO", "RONDONIA": "RO",
    "RORAIMA": "RR", "RIO GRANDE DO SUL": "RS", "SANTA CATARINA": "SC", "SERGIPE": "SE",
    "SÃO PAULO": "SP", "SAO PAULO": "SP", "TOCANTINS": "TO",
}
CABECALHO = {"User-Agent": "MonitorElNinoBrasil/2.2 (+https://monitorelnino.com.br; contato via site)"}

# ---------------------------------------------------------------------------
# Catálogo de fontes. `url_publica` é o que a página mostra ao leitor (a página
# de onde o dado veio, legível por humano); `endpoint` é de onde o script lê.
# Fonte sem endpoint é coletada por leitura humana e entra por --semear.
# ---------------------------------------------------------------------------
FONTES = {
    "painel_el_nino": {
        "nome": "Painel El Niño 2026-2027", "orgao": "CEMADEN/INPE", "camada": "ciclo",
        "url_publica": "https://www.gov.br/cemaden/pt-br",
        "endpoint": None,
        "papel": "Risco projetado por região e a largada pública do ciclo.",
    },
    "monitor_secas": {
        "nome": "Monitor de Secas", "orgao": "ANA e parceiros estaduais", "camada": "observado",
        "url_publica": "https://monitordesecas.ana.gov.br/",
        # 04/09/2026: catálogo antigo responde 404. API real: apimsbr.ana.gov.br/rpc/v1/<recurso>.
        # 15/09/2026 (sonda com rede real): o RPC que alimenta a página "Dados tabulares" do
        # Monitor é dados-tabulares-monitor?tipo_area=1&area=<código IBGE da UF> — devolve, por
        # mapa mensal, a área em cada categoria S0–S4 da UF. change_maps (só PNGs) fica como
        # inventário de mapas; o valor por UF vem daqui.
        "endpoint": "https://apimsbr.ana.gov.br/rpc/v1/dados-tabulares-monitor?tipo_area=1&area=",
        "endpoint_mapas": "https://apimsbr.ana.gov.br/rpc/v1/change_maps",
        "papel": "Fração da área de cada UF em cada categoria de seca (S0 a S4), no mapa mensal mais recente.",
    },
    "inmet_avisos": {
        "nome": "Avisos meteorológicos", "orgao": "INMET", "camada": "observado",
        "url_publica": "https://alertas2.inmet.gov.br/",
        "endpoint": "https://apiprevmet3.inmet.gov.br/avisos/ativos",
        "papel": "Avisos vigentes por área, com grau e vigência declarados pelo INMET.",
    },
    "inpe_fogo": {
        "nome": "Programa Queimadas — risco de fogo", "orgao": "INPE", "camada": "observado",
        "url_publica": "https://terrabrasilis.dpi.inpe.br/queimadas/situacao-atual/",
        # 04/09/2026: endereço antigo devolvia HTML (o portal mudou). Diretório real,
        # confirmado por diagnóstico: dataserver-coids.inpe.br, arquivos focos_diario_br_AAAAMMDD.csv.
        "endpoint": "https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/diario/Brasil/",
        "papel": "Focos ativos nas últimas 24 h por UF (contagem publicada pelo INPE).",
    },
    "cemaden_alertas": {
        "nome": "Alertas hidrológicos e geológicos", "orgao": "CEMADEN", "camada": "observado",
        "url_publica": "https://www.gov.br/cemaden/pt-br/assuntos/monitoramento/alertas-vigentes",
        # 04/09/2026: o JSON antigo não existe mais (404). Camada confirmada por GetCapabilities.
        "endpoint": ("https://gsc.cemaden.gov.br/geoserver/cemaden_dev/ows?service=WFS&version=2.0.0"
                      "&request=GetFeature&typeNames=cemaden_dev:alertas_vigentes_siaden&outputFormat=application/json&count=3000"),
        "papel": "Alertas vigentes emitidos aos municípios monitorados.",
    },
    "noaa_oni": {
        "nome": "Oceanic Niño Index (ONI)", "orgao": "NOAA/CPC", "camada": "enos",
        "url_publica": "https://origin.cpc.ncep.noaa.gov/products/analysis_monitoring/ensostuff/ONI_v5.php",
        "endpoint": "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt",
        "papel": "Série observada do índice que define oficialmente El Niño e La Niña.",
    },
    "iri_plume": {
        "nome": "Probabilidades ENSO (plume IRI/CPC)", "orgao": "IRI/Columbia", "camada": "enos",
        "url_publica": "https://iri.columbia.edu/our-expertise/climate/forecasts/enso/current/",
        "endpoint": "https://iri.columbia.edu/~forecast/ensofcst/Data/ensofcst_ONI",
        "papel": "Probabilidade de El Niño, neutro e La Niña por trimestre.",
    },
    "cptec_prognostico": {
        "nome": "Prognóstico climático trimestral", "orgao": "INMET/CPTEC-INPE", "camada": "enos",
        "url_publica": "https://portal.inmet.gov.br/boletinsagro",
        "endpoint": None,
        "papel": "A leitura brasileira da mesma previsão, em português.",
    },
}

# Vocabulário controlado do TIPO de risco projetado (não é escala de severidade —
# ver docstring, item 2). Classificação documental feita por analista sobre o
# texto do boletim, no mesmo estatuto do vocabulário do índice (§6 da
# transferência conceitual): lista fechada, categoria nova exige decisão editorial.
TIPOS_RISCO = {
    "estiagem": "Estiagem, seca ou pressão sobre reservatórios",
    "chuvas": "Chuvas acima da média, enchentes ou alagamentos",
    "incendios": "Incêndios florestais e risco de fogo",
    "misto": "Mais de um tipo de risco no mesmo trimestre",
    "sem_sinal": "Sem sinal elevado declarado no trimestre",
}
# Rótulos curtos dos MESMOS tipos, para eixos de gráfico e legendas estreitas.
# Mesmas chaves, obrigatoriamente — verificado por verificar_sinais.py.
TIPOS_RISCO_CURTO = {"estiagem": "Estiagem", "chuvas": "Chuvas", "incendios": "Incêndios",
                     "misto": "Misto", "sem_sinal": "Sem sinal elevado"}
_PADROES = [  # ordem importa: o primeiro que casa vence dentro de cada eixo
    ("chuvas", re.compile(r"chuv|enchent|alagam|inunda|hidrol[óo]g", re.I)),
    ("estiagem", re.compile(r"estiagem|seca|reservat[óo]ri|d[ée]ficit h[íi]dric|ir+egularidade", re.I)),
    ("incendios", re.compile(r"inc[êe]ndi|queimad|fogo", re.I)),
]


def classificar_tipo(texto: str) -> str:
    """Classifica o TIPO (nunca a intensidade) do risco projetado a partir do texto do boletim; 'misto' quando o boletim cita mais de um eixo e 'sem_sinal' quando declara ausência de sinal elevado."""
    if not texto or re.search(r"sem sinal|sem anomalia|neutr", texto, re.I):
        return "sem_sinal"
    achados = [nome for nome, padrao in _PADROES if padrao.search(texto)]
    if not achados:
        return "sem_sinal"
    return achados[0] if len(achados) == 1 else "misto"


def componentes_de_risco(texto: str) -> list:
    """17/09/2026 (pedido da editoria): quando classificar_tipo(texto) devolve 'misto', o gráfico de
    tipos de risco precisa recontar cada estado nos riscos que de fato o compõem (não numa categoria
    'misto' à parte, que só informa uma contagem sem dizer do quê), e o mapa precisa dizer, ao passar
    o mouse, quais riscos compõem o misto daquele estado. Mesma detecção de classificar_tipo — só que
    devolve a LISTA de achados, sem colapsar em 'misto' quando há mais de um eixo."""
    if not texto or re.search(r"sem sinal|sem anomalia|neutr", texto, re.I):
        return []
    return [nome for nome, padrao in _PADROES if padrao.search(texto)]


def hoje() -> str:
    """Data de hoje no formato dd/mm/aaaa usado em todo o repositório."""
    return date.today().strftime("%d/%m/%Y")


def _buscar(url: str) -> str:
    """GET simples com cabeçalho identificado e tempo limite; erros sobem para quem chamou tratar."""
    req = urllib.request.Request(url, headers=CABECALHO)
    with urllib.request.urlopen(req, timeout=TEMPO_LIMITE) as r:
        return r.read().decode("utf-8", errors="replace")


# ===========================================================================
# PARSERS — funções puras, testáveis sem rede (--autoteste prova cada uma)
# ===========================================================================
def parse_oni(texto: str) -> list:
    """Lê a série ONI do arquivo ASCII do CPC (colunas SEAS YR TOTAL ANOM) e devolve [{'trimestre','ano','anomalia'}] em ordem cronológica."""
    serie = []
    for linha in texto.splitlines():
        partes = linha.split()
        if len(partes) != 4 or partes[0] == "SEAS":
            continue
        try:
            serie.append({"trimestre": partes[0], "ano": int(partes[1]), "anomalia": float(partes[3])})
        except ValueError:
            continue
    return serie


def parse_plume_iri(texto: str) -> list:
    """Lê o arquivo de probabilidades ENSO do IRI e devolve [{'trimestre','la_nina','neutro','el_nino'}] em porcentagem."""
    saida = []
    for linha in texto.splitlines():
        partes = linha.split()
        if len(partes) < 4:
            continue
        rotulo = partes[0]
        if not re.fullmatch(r"[A-Z]{3}", rotulo):
            continue
        try:
            nina, neutro, nino = (float(p) for p in partes[1:4])
        except ValueError:
            continue
        if not (0 <= nina <= 100 and 0 <= neutro <= 100 and 0 <= nino <= 100):
            continue
        saida.append({"trimestre": rotulo, "la_nina": nina, "neutro": neutro, "el_nino": nino})
    return saida


def parse_focos_inpe(texto: str) -> dict:
    """Conta focos ativos por UF a partir do CSV de focos abertos do INPE (coluna 'estado' ou 'uf'), devolvendo {'UF': n}."""
    import csv
    import io
    linhas = list(csv.DictReader(io.StringIO(texto)))
    if not linhas:
        return {}
    campos = {c.lower(): c for c in linhas[0].keys()}
    coluna = campos.get("uf") or campos.get("estado") or campos.get("sigla_uf")
    if not coluna:
        return {}
    contagem = {}
    for linha in linhas:
        bruto = (linha.get(coluna) or "").strip().upper()
        sigla = bruto if bruto in UFS else NOME_PARA_SIGLA.get(bruto)
        if sigla:
            contagem[sigla] = contagem.get(sigla, 0) + 1
    return contagem


def escolher_csv_focos(html_indice: str) -> str:
    """Nome do CSV diário mais recente listado no diretório do INPE (focos_diario_br_AAAAMMDD.csv). Função pura."""
    nomes = re.findall(r'focos_diario_br_(\d{8})\.csv', html_indice or "")
    return f"focos_diario_br_{max(nomes)}.csv" if nomes else ""


def parse_alertas_wfs_cemaden(dados) -> dict:
    """Agrega o GeoJSON de alertas vigentes do CEMADEN por UF. O nível é o vocabulário da fonte, nunca reescalado (§23.3)."""
    feicoes = (dados or {}).get("features") or []
    saida = {}
    for f in feicoes:
        p = f.get("properties") or {}
        uf = next((str(p[k]).strip().upper() for k in ("uf", "sigla_uf", "estado", "UF") if p.get(k)), "")
        if uf not in UFS:
            continue
        nivel = next((str(p[k]).strip() for k in ("nivel", "severidade", "nivel_alerta", "classificacao") if p.get(k)), "sem nível declarado")
        mun = next((str(p[k]).strip() for k in ("municipio", "nome_municipio", "nm_mun", "cidade") if p.get(k)), "")
        d = saida.setdefault(uf, {"total": 0, "niveis": {}, "municipios": []})
        d["total"] += 1
        d["niveis"][nivel] = d["niveis"].get(nivel, 0) + 1
        if mun and mun not in d["municipios"]:
            d["municipios"].append(mun)
    for d in saida.values():
        d["municipios"] = sorted(d["municipios"])[:40]
    return saida


def parse_change_maps_ana(dados) -> dict:
    """Extrai do recurso /rpc/v1/change_maps da ANA a lista datada de mapas e a data mais recente."""
    bruto = (dados or {}).get("file") or ""
    caminhos = re.findall(r'([\w/\-.]+\.(?:png|pdf|zip|xlsx|csv))', bruto)
    datas = sorted(set(re.findall(r'(\d{4}-\d{2}-\d{2})', bruto)))
    return {"arquivos": caminhos[-24:], "datas": datas[-24:], "ultima_data": (datas[-1] if datas else None),
            "base": "https://ana-monitor-secas-files.s3.sa-east-1.amazonaws.com/"}


def parse_avisos_inmet(dados) -> dict:
    """Agrega avisos ativos do INMET por UF, preservando o grau tal como o INMET o nomeia, e devolve {'UF': {'total': n, 'graus': {...}, 'exemplos': [...]}}."""
    itens = dados.get("hoje", dados) if isinstance(dados, dict) else dados
    if isinstance(itens, dict):
        itens = itens.get("avisos", [])
    saida = {}
    for aviso in itens or []:
        if not isinstance(aviso, dict):
            continue
        grau = (aviso.get("severidade") or aviso.get("aviso_cor") or aviso.get("grau") or "").strip()
        descricao = (aviso.get("descricao") or aviso.get("aviso") or "").strip()
        # 15/09/2026 (sonda com rede real): `estados` vem por extenso ("Minas Gerais,Espírito Santo");
        # `geocodes` traz os códigos IBGE dos municípios (7 dígitos). Aceita sigla, nome ou geocode.
        estados = aviso.get("estados") or aviso.get("uf") or ""
        siglas = set()
        for parte in re.split(r"[,;/]+", str(estados)):
            nome = parte.strip().upper()
            if nome in UFS:
                siglas.add(nome)
            elif nome in NOME_PARA_SIGLA:
                siglas.add(NOME_PARA_SIGLA[nome])
        for cod in re.findall(r"\d{7}", str(aviso.get("geocodes") or "")):
            uf = UF_POR_IBGE.get(int(cod[:2]))
            if uf:
                siglas.add(uf)
        siglas = sorted(siglas)
        for sigla in siglas:
            reg = saida.setdefault(sigla, {"total": 0, "graus": {}, "exemplos": []})
            reg["total"] += 1
            if grau:
                reg["graus"][grau] = reg["graus"].get(grau, 0) + 1
            if descricao and len(reg["exemplos"]) < 3 and descricao not in reg["exemplos"]:
                reg["exemplos"].append(descricao)
    return saida


def parse_alertas_cemaden(dados) -> dict:
    """Agrega alertas vigentes do CEMADEN por UF, preservando o nível declarado, e devolve {'UF': {'total': n, 'niveis': {...}}}."""
    itens = dados if isinstance(dados, list) else (dados.get("alertas") or dados.get("features") or [])
    saida = {}
    for item in itens:
        if not isinstance(item, dict):
            continue
        corpo = item.get("properties", item)
        sigla = str(corpo.get("uf") or corpo.get("sigla_uf") or "").strip().upper()
        if sigla not in UFS:
            continue
        nivel = str(corpo.get("nivel") or corpo.get("severidade") or "").strip() or "não declarado"
        reg = saida.setdefault(sigla, {"total": 0, "niveis": {}})
        reg["total"] += 1
        reg["niveis"][nivel] = reg["niveis"].get(nivel, 0) + 1
    return saida


def parse_dados_tabulares_secas(dados) -> dict:
    """Lê o RPC dados-tabulares-monitor da ANA para UMA UF e devolve o mapa mensal mais recente. Formato real
    (sonda de 15/09/2026, conferido com o código do site da ANA): `area` de cada categoria é a fração CUMULATIVA
    da área da UF naquela categoria OU PIOR, em centésimos de ponto percentual (S0 = 10000 → 100 % da UF em seca
    fraca ou pior; sem seca = 100 − S0/100). Devolve {'mapa','ano','mes','final','cobertura_pct':{'sem seca',S0..S4}
    (exclusivas, em %), 'cumulativa_pct':{S0..S4} (% na categoria ou pior), 'categoria_mediana' (categoria que
    cobre pelo menos metade da área da UF; 'sem seca' se a seca não chega à metade), 'categoria_maxima'
    (mais severa com pelo menos 1 % da área)}. {} se nada casar. Função pura."""
    lista = ((dados or {}).get("data") or {}).get("list") or []
    melhor = None
    for item in lista:
        mapa = item.get("mapa") or {}
        areas = item.get("areas") or []
        if not areas or not mapa.get("ano") or not mapa.get("mes"):
            continue
        chave = (int(mapa["ano"]), int(mapa["mes"]), 1 if mapa.get("final") else 0)
        if melhor is None or chave > melhor[0]:
            melhor = (chave, mapa, areas)
    if not melhor:
        return {}
    _, mapa, areas = melhor
    cum = {}
    for a in areas:
        c = str(a.get("categoria") or "").strip().upper()
        if re.fullmatch(r"S[0-4]", c):
            try:
                cum[c] = max(0.0, min(100.0, float(a.get("area") or 0) / 100.0))
            except (TypeError, ValueError):
                cum[c] = 0.0
    if not cum:
        return {}
    ordem = ["S0", "S1", "S2", "S3", "S4"]
    cumulativa = {c: round(cum.get(c, 0.0), 2) for c in ordem}
    # cumulativa é não crescente por construção da fonte; garante-o para dados inconsistentes
    for i in range(1, len(ordem)):
        cumulativa[ordem[i]] = min(cumulativa[ordem[i]], cumulativa[ordem[i - 1]])
    excl = {"sem seca": round(100.0 - cumulativa["S0"], 2)}
    for i, c in enumerate(ordem):
        seguinte = cumulativa[ordem[i + 1]] if i + 1 < len(ordem) else 0.0
        excl[c] = round(cumulativa[c] - seguinte, 2)
    mediana = "sem seca"
    for c in ordem:
        if cumulativa[c] >= 50.0:
            mediana = c
    com_area = [c for c in reversed(ordem) if cumulativa[c] >= 1.0]
    return {"mapa": mapa.get("nome"), "ano": int(mapa["ano"]), "mes": int(mapa["mes"]), "final": bool(mapa.get("final")),
            "cobertura_pct": excl, "cumulativa_pct": cumulativa,
            "categoria_mediana": mediana, "categoria_maxima": com_area[0] if com_area else "sem seca"}


def parse_catalogo_secas(dados) -> dict:
    """Descobre no catálogo CKAN da ANA o recurso mais recente do Monitor de Secas, devolvendo {'titulo','url','atualizado_em'} ou {} se nada casar."""
    pacotes = (dados.get("result") or {}).get("results") or []
    melhor = {}
    for pacote in pacotes:
        titulo = (pacote.get("title") or "") + " " + (pacote.get("name") or "")
        if not re.search(r"seca", titulo, re.I):
            continue
        for recurso in pacote.get("resources") or []:
            formato = (recurso.get("format") or "").upper()
            if formato not in {"CSV", "SHP", "GEOJSON", "XLSX", "ZIP"}:
                continue
            quando = recurso.get("last_modified") or recurso.get("created") or ""
            if quando > melhor.get("atualizado_em", ""):
                melhor = {"titulo": recurso.get("name") or pacote.get("title"),
                          "url": recurso.get("url"), "atualizado_em": quando}
    return melhor


# ===========================================================================
# COLETA — cada adaptador devolve (payload, documento) ou levanta exceção
# ===========================================================================
def coletar_fonte(chave: str):
    """Executa o adaptador de rede da fonte indicada e devolve (payload, rótulo do documento); levanta exceção em qualquer falha, tratada por quem chama."""
    fonte = FONTES[chave]
    if not fonte["endpoint"]:
        raise RuntimeError("fonte sem endpoint automático — entra por leitura humana (--semear)")
    bruto = _buscar(fonte["endpoint"] + (str(IBGE_UF["RO"]) if chave == "monitor_secas" else ""))
    if chave == "noaa_oni":
        serie = parse_oni(bruto)
        if len(serie) < 12:
            raise ValueError(f"série ONI curta demais ({len(serie)} pontos) — recusada")
        ultimo = serie[-1]
        return {"serie": serie[-160:]}, f"ONI v5, último trimestre {ultimo['trimestre']}/{ultimo['ano']}"
    if chave == "iri_plume":
        plume = parse_plume_iri(bruto)
        if not plume:
            raise ValueError("plume IRI sem trimestres reconhecíveis — recusada")
        return {"trimestres": plume}, f"Plume ENSO, {len(plume)} trimestres"
    if chave == "inpe_fogo":
        nome = escolher_csv_focos(bruto)   # `bruto` é o ÍNDICE do diretório
        if not nome:
            raise ValueError("índice do INPE sem arquivo focos_diario_br_*.csv — recusado")
        focos = parse_focos_inpe(_buscar(fonte["endpoint"] + nome))
        if not focos:
            raise ValueError("CSV de focos sem coluna de UF reconhecível — recusado")
        return {"focos_por_uf": focos}, f"Focos do dia — {nome}"
    if chave == "inmet_avisos":
        avisos = parse_avisos_inmet(json.loads(bruto))
        return {"por_uf": avisos}, "Avisos ativos no momento da consulta"
    if chave == "cemaden_alertas":
        alertas = parse_alertas_wfs_cemaden(json.loads(bruto))
        return {"por_uf": alertas}, "Alertas vigentes (camada alertas_vigentes_siaden, CEMADEN)"
    if chave == "monitor_secas":
        # `bruto` é a resposta da UF de menor código (RO) — só prova que o RPC responde; abaixo, as 27.
        por_uf, falhas = {}, []
        for uf in UFS:
            try:
                lido = parse_dados_tabulares_secas(json.loads(_buscar(fonte["endpoint"] + str(IBGE_UF[uf]))))
            except (urllib.error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as e:
                falhas.append(f"{uf}:{e.__class__.__name__}")
                continue
            if lido:
                por_uf[uf] = lido
        if len(por_uf) < 20:
            raise ValueError(f"dados tabulares da ANA cobriram só {len(por_uf)} UF(s) ({', '.join(falhas)[:200]}) — recusados")
        mapas = sorted({(v["ano"], v["mes"], v["mapa"]) for v in por_uf.values()})
        recurso = {}
        try:
            recurso = parse_change_maps_ana(json.loads(_buscar(fonte["endpoint_mapas"])))
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError):
            pass
        return {"por_uf": por_uf, "recurso": recurso, "falhas": falhas}, f"Monitor de Secas (ANA) — dados tabulares por UF, mapa {mapas[-1][2]}"
    raise RuntimeError(f"adaptador ausente para {chave}")


# ===========================================================================
# REGISTRO
# ===========================================================================
def esqueleto() -> dict:
    """Monta o registro vazio, com o catálogo de fontes e as 27 UFs, tudo em estado de lacuna declarada."""
    return {
        "_formato": {
            "descricao": "Sinais oficiais de risco reproduzidos de fontes primárias, em três camadas "
                         "(ciclo, observado, ENOS). Cada valor traz órgão, documento e data.",
            "efeito_no_indice": "NENHUM — peso zero. Registro de transparência, nunca insumo do MARÉ "
                                "(METODOLOGIA §23; mudança de pontuação exige versão maior).",
            "regra_de_prova": "O Monitor não faz previsão climática: reproduz o que o órgão publicou, "
                              "no vocabulário do próprio órgão. Fonte não coletada permanece como lacuna "
                              "declarada — nenhum valor é preenchido por estimativa.",
            "tipos_de_risco": TIPOS_RISCO,
            "tipos_de_risco_curto": TIPOS_RISCO_CURTO,
            "escrito_por": "coletar_sinais_risco.py",
        },
        "gerado_em": hoje(),
        "fontes": {
            chave: {**{k: v for k, v in dados.items() if k != "endpoint"},
                    "status": "aguardando_primeira_coleta", "consultado_em": None,
                    "documento": None, "detalhe": None}
            for chave, dados in FONTES.items()
        },
        "enos": {"oni": None, "probabilidades": None, "prognostico": None},
        "uf": {uf: {"risco_projetado": None, "secas": None, "avisos_inmet": None,
                    "fogo": None, "alertas_cemaden": None} for uf in UFS},
    }


def semear(registro: dict) -> dict:
    """Preenche a camada 'ciclo' a partir do que já está verificado no repositório (data/consist.json e data/boletins.json), sem rede e sem inventar nada."""
    consist = json.loads(CONSIST.read_text(encoding="utf-8"))
    boletins = json.loads(BOLETINS.read_text(encoding="utf-8"))
    numero = boletins.get("ultimo_boletim")
    documento = f"Boletins nº 1 e {numero} do Painel El Niño 2026-2027" if numero else "Painel El Niño 2026-2027"
    faltando = [uf for uf in UFS if uf not in consist]
    if faltando:
        raise SystemExit(f"✗ consist.json não cobre {len(faltando)} UF(s): {', '.join(faltando)}")
    for uf in UFS:
        texto = consist[uf]["risco"]
        registro["uf"][uf]["risco_projetado"] = {
            "texto": texto,
            "tipo": classificar_tipo(texto),
            "componentes": componentes_de_risco(texto),   # 17/09/2026: riscos individuais que compõem o tipo, mesmo quando "misto"
            "instrumento_estadual": consist[uf]["instr"],
            "relacao_com_instrumento": consist[uf]["cat"],
            "fonte": "painel_el_nino",
            "documento": documento,
            "url": FONTES["painel_el_nino"]["url_publica"],
        }
    registro["fontes"]["painel_el_nino"].update({
        "status": "coletado", "consultado_em": hoje(), "documento": documento,
        "detalhe": "Risco projetado por UF conforme registro curado em data/consist.json, "
                   "derivado da leitura humana dos boletins do Painel.",
    })
    return registro


def coletar(registro: dict, camadas) -> dict:
    """Percorre as fontes das camadas pedidas, atualiza as que responderem e deixa as demais como lacuna declarada; nenhuma falha de rede interrompe o pipeline."""
    for chave, fonte in FONTES.items():
        if fonte["camada"] not in camadas or not fonte["endpoint"]:
            continue
        try:
            payload, documento = coletar_fonte(chave)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            print(f"[aviso] {chave}: rede indisponível ({e.__class__.__name__}) — registro anterior mantido.")
            continue
        except (ValueError, RuntimeError, json.JSONDecodeError) as e:
            print(f"[aviso] {chave}: resposta recusada ({e}) — registro anterior mantido.")
            continue
        registro["fontes"][chave].update({
            "status": "coletado", "consultado_em": hoje(), "documento": documento,
            "detalhe": fonte["papel"],
        })
        if chave == "noaa_oni":
            registro["enos"]["oni"] = {**payload, "fonte": chave, "documento": documento}
        elif chave == "iri_plume":
            registro["enos"]["probabilidades"] = {**payload, "fonte": chave, "documento": documento}
        # 15/09/2026: INPE, INMET e CEMADEN respondem pelo país inteiro — UF ausente da resposta é ZERO
        # (nenhum foco, aviso ou alerta), não lacuna. Zero ≠ ausência de dado: só a fonte não coletada
        # fica nula (cinza no mapa). Sonda de 15/09: CEMADEN tinha 88 alertas em 6 UFs; as outras 21 eram zero.
        elif chave == "inpe_fogo":
            for uf in UFS:
                registro["uf"][uf]["fogo"] = {"focos_24h": payload["focos_por_uf"].get(uf, 0), "fonte": chave,
                                              "documento": documento, "consultado_em": hoje()}
        elif chave == "inmet_avisos":
            for uf in UFS:
                dados = payload["por_uf"].get(uf) or {"total": 0, "graus": {}, "exemplos": []}
                registro["uf"][uf]["avisos_inmet"] = {**dados, "fonte": chave,
                                                      "documento": documento, "consultado_em": hoje()}
        elif chave == "cemaden_alertas":
            for uf in UFS:
                dados = payload["por_uf"].get(uf) or {"total": 0, "niveis": {}, "municipios": []}
                registro["uf"][uf]["alertas_cemaden"] = {**dados, "fonte": chave,
                                                         "documento": documento, "consultado_em": hoje()}
        elif chave == "monitor_secas":
            if payload.get("recurso"):
                registro["fontes"][chave]["recurso"] = payload["recurso"]
            for uf in UFS:
                lido = payload["por_uf"].get(uf)
                registro["uf"][uf]["secas"] = ({**lido, "fonte": chave, "documento": documento, "consultado_em": hoje()}
                                               if lido else None)   # UF que o RPC não devolveu fica nula (lacuna), nunca zero
        print(f"  ✓ {chave}: {documento}")
    return registro


def gravar(registro: dict) -> None:
    """Grava o registro em data/sinais_risco.json com indentação de 1 espaço, padrão dos demais arquivos de data/."""
    registro["gerado_em"] = hoje()
    REGISTRO.write_text(json.dumps(registro, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"→ {REGISTRO.relative_to(RAIZ)} gravado.")


# ===========================================================================
# AUTOTESTE — prova os parsers e os guardas sem depender de rede
# ===========================================================================
def autoteste() -> int:
    """Roda os testes de parser, de classificação e os testes negativos; devolve 0 se todos passarem, 1 caso contrário."""
    falhas = []

    def checar(nome, condicao):
        print(("  ✓ " if condicao else "  ✗ ") + nome)
        if not condicao:
            falhas.append(nome)

    oni = parse_oni("SEAS YR TOTAL ANOM\nDJF 2025 26.8 0.3\nJFM 2025 27.0 0.5\nlixo\nMAM 2025 27.4 0.9\n")
    checar("ONI: 3 pontos lidos e lixo descartado", len(oni) == 3)
    checar("ONI: último ponto correto", oni[-1] == {"trimestre": "MAM", "ano": 2025, "anomalia": 0.9})
    checar("ONI negativo: cabeçalho não vira dado", all(p["trimestre"] != "SEAS" for p in oni))

    plume = parse_plume_iri("JJA 10.0 30.0 60.0\nJAS 5.0 25.0 70.0\ncomentário qualquer\nXX 1 2 3\n")
    checar("plume: 2 trimestres lidos", len(plume) == 2)
    checar("plume: rótulo inválido descartado", all(p["trimestre"] in {"JJA", "JAS"} for p in plume))
    checar("plume negativo: fora de 0-100 é descartado", parse_plume_iri("ABC 120 10 10\n") == [])

    focos = parse_focos_inpe("estado,municipio\nPARÁ,Altamira\nPará,Novo Progresso\nBAHIA,Barreiras\nXX,Nada\n")
    checar("focos: agrega por UF com acentuação e caixa variadas", focos == {"PA": 2, "BA": 1})
    checar("focos negativo: CSV sem coluna de UF devolve vazio", parse_focos_inpe("a,b\n1,2\n") == {})

    avisos = parse_avisos_inmet({"hoje": {"avisos": [
        {"severidade": "Perigo Potencial", "descricao": "Chuvas intensas", "estados": "BA, SE"},
        {"severidade": "Perigo", "descricao": "Baixa umidade", "estados": "GO"},
    ]}})
    checar("avisos INMET: espalha por todas as UFs citadas", set(avisos) == {"BA", "SE", "GO"})
    _real = parse_avisos_inmet({"hoje": [{"severidade": "Perigo", "descricao": "Tempestade", "estados": "Minas Gerais,Espírito Santo,", "geocodes": "3100104,3200102,5200209"}], "futuro": []})
    checar("avisos INMET: nomes por extenso e geocodes (formato real, 15/09/2026)", set(_real) == {"MG", "ES", "GO"} and _real["MG"]["total"] == 1)
    checar("avisos INMET: preserva o grau do próprio INMET", avisos["BA"]["graus"] == {"Perigo Potencial": 1})
    checar("avisos negativo: payload vazio não quebra", parse_avisos_inmet({}) == {})

    alertas = parse_alertas_cemaden([{"uf": "MG", "nivel": "Moderado"}, {"uf": "MG", "nivel": "Alto"},
                                     {"uf": "ZZ", "nivel": "Alto"}])
    checar("alertas CEMADEN: agrega por nível e ignora UF inválida", alertas == {"MG": {"total": 2, "niveis": {"Moderado": 1, "Alto": 1}}})

    catalogo = parse_catalogo_secas({"result": {"results": [
        {"title": "Monitor de Secas do Brasil", "resources": [
            {"name": "antigo", "format": "CSV", "url": "u1", "last_modified": "2026-01-01"},
            {"name": "novo", "format": "CSV", "url": "u2", "last_modified": "2026-08-01"}]},
        {"title": "Outra base qualquer", "resources": [{"name": "x", "format": "CSV", "url": "u3", "last_modified": "2026-12-01"}]},
    ]}})
    checar("catálogo ANA: escolhe o recurso mais recente do pacote certo", catalogo.get("url") == "u2")
    checar("catálogo negativo: sem pacote de seca devolve vazio", parse_catalogo_secas({"result": {"results": []}}) == {})

    checar("tipo: chuva", classificar_tipo("Chuvas extremas e enchentes") == "chuvas")
    checar("tipo: estiagem", classificar_tipo("Estiagem prolongada; pressão sobre reservatórios") == "estiagem")
    checar("tipo: misto", classificar_tipo("Incêndios; seca em intensificação (IIS-3)") == "misto")
    checar("tipo: sem sinal", classificar_tipo("Sem sinal elevado no trimestre") == "sem_sinal")
    checar("tipo negativo: vazio não vira categoria de risco", classificar_tipo("") == "sem_sinal")

    # 17/09/2026: componentes_de_risco() é a mesma detecção de classificar_tipo(), sem colapsar em
    # "misto" — todo "misto" precisa render pelo menos 2 componentes; todo tipo único, exatamente 1.
    checar("componentes: misto vira dois componentes", componentes_de_risco("Estiagem; incêndios") == ["estiagem", "incendios"])
    checar("componentes: tipo único vira um componente", componentes_de_risco("Chuvas extremas e enchentes") == ["chuvas"])
    checar("componentes: sem sinal não vira componente", componentes_de_risco("Sem sinal elevado no trimestre") == [])
    checar("componentes e tipo concordam: len(componentes) > 1 sse tipo é misto",
           (len(componentes_de_risco("Incêndios; seca em intensificação (IIS-3)")) > 1) == (classificar_tipo("Incêndios; seca em intensificação (IIS-3)") == "misto"))

    # --- endpoints reais (04/09/2026) ---
    checar("INPE: escolhe o CSV diário mais recente",
           escolher_csv_focos('<a href="focos_diario_br_20260902.csv">x</a><a href="focos_diario_br_20260904.csv">y</a><a href="focos_diario_br_20260903.csv">z</a>') == "focos_diario_br_20260904.csv")
    checar("INPE negativo: índice sem CSV não quebra",
           escolher_csv_focos("<html>vazio</html>") == "" and escolher_csv_focos("") == "")
    _gj = {"features": [{"properties": {"uf": "SP", "municipio": "Santos", "nivel": "Moderado"}},
                        {"properties": {"uf": "SP", "municipio": "Cubatão", "nivel": "Alto"}},
                        {"properties": {"uf": "RJ", "municipio": "Petrópolis", "nivel": "Alto"}},
                        {"properties": {"uf": "XX", "municipio": "Fora", "nivel": "Alto"}}]}
    _r = parse_alertas_wfs_cemaden(_gj)
    checar("CEMADEN WFS: agrega por UF com o nível da fonte",
           set(_r) == {"SP", "RJ"} and _r["SP"]["total"] == 2 and _r["SP"]["niveis"] == {"Moderado": 1, "Alto": 1})
    checar("CEMADEN negativo: GeoJSON vazio não quebra",
           parse_alertas_wfs_cemaden({}) == {} and parse_alertas_wfs_cemaden({"features": []}) == {})
    _ana = parse_change_maps_ana({"file": '["data/change-maps/2026/08/drought-monitor_2026-08-31_66m.png", "data/change-maps/2026/07/x_2026-07-31_66m.png"]'})
    checar("ANA: extrai datas e arquivos do recurso change_maps",
           _ana["ultima_data"] == "2026-08-31" and len(_ana["arquivos"]) == 2)
    checar("ANA negativo: recurso vazio não quebra",
           parse_change_maps_ana({})["ultima_data"] is None)
    _tab = parse_dados_tabulares_secas({"data": {"list": [
        {"areas": [{"categoria": "S0", "area": 1000}, {"categoria": "S1", "area": 0}], "mapa": {"nome": "Junho de 2026", "ano": 2026, "mes": 6, "final": True}},
        {"areas": [{"categoria": "S0", "area": 8988}, {"categoria": "S1", "area": 7161}, {"categoria": "S2", "area": 0}], "mapa": {"nome": "Julho de 2026", "ano": 2026, "mes": 7, "final": True}}]}})
    checar("ANA dados tabulares: escolhe o mapa mais recente; frações cumulativas viram exclusivas (BA jul/2026: 10,12 % sem seca · 18,27 % S0 · 71,61 % S1)",
           _tab.get("mapa") == "Julho de 2026" and _tab["cobertura_pct"] == {"sem seca": 10.12, "S0": 18.27, "S1": 71.61, "S2": 0.0, "S3": 0.0, "S4": 0.0}
           and _tab["categoria_mediana"] == "S1" and _tab["categoria_maxima"] == "S1")
    _sp = parse_dados_tabulares_secas({"data": {"list": [{"areas": [{"categoria": "S0", "area": 6483}, {"categoria": "S1", "area": 3739}, {"categoria": "S2", "area": 654}], "mapa": {"nome": "Julho de 2026", "ano": 2026, "mes": 7, "final": True}}]}})
    checar("ANA dados tabulares: mediana é a categoria que cobre metade da área (SP jul/2026: 64,8 % S0+, 37,4 % S1+ → S0); máxima com ≥1 % é S2",
           _sp["categoria_mediana"] == "S0" and _sp["categoria_maxima"] == "S2" and _sp["cobertura_pct"]["sem seca"] == 35.17)
    checar("ANA dados tabulares: tudo zero vira 'sem seca'",
           parse_dados_tabulares_secas({"data": {"list": [{"areas": [{"categoria": "S0", "area": 0}], "mapa": {"nome": "x", "ano": 2026, "mes": 7, "final": True}}]}})["categoria_mediana"] == "sem seca")
    checar("ANA dados tabulares negativo: resposta vazia devolve {}", parse_dados_tabulares_secas({"data": {"list": []}}) == {} and parse_dados_tabulares_secas({}) == {})

    esq = esqueleto()
    checar("esqueleto: 27 UFs", len(esq["uf"]) == 27)
    checar("esqueleto: nenhuma fonte nasce como coletada",
           all(f["status"] == "aguardando_primeira_coleta" for f in esq["fontes"].values()))
    checar("esqueleto: peso zero declarado no formato", "NENHUM" in esq["_formato"]["efeito_no_indice"])

    if falhas:
        print(f"\n✗ AUTOTESTE: {len(falhas)} falha(s).")
        return 1
    print("\n✓ AUTOTESTE OK — parsers, classificação e guardas provados sem rede.")
    return 0


def main() -> None:
    """Interpreta os argumentos de linha de comando e executa autoteste, semeadura ou coleta das camadas pedidas."""
    args = sys.argv[1:]
    if "--autoteste" in args:
        sys.exit(autoteste())
    registro = json.loads(REGISTRO.read_text(encoding="utf-8")) if REGISTRO.exists() else esqueleto()
    if "--semear" in args:
        registro = semear(esqueleto() if "--zerar" in args else registro)
        gravar(registro)
        return
    camadas = {"ciclo", "observado", "enos"}
    if "--camada" in args:
        camadas = {args[args.index("--camada") + 1]}
    print(f"Coletando sinais oficiais de risco · camadas: {', '.join(sorted(camadas))}")
    registro = coletar(registro, camadas)
    gravar(registro)


if __name__ == "__main__":
    main()
