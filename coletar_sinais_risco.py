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
import hashlib
import json
import pathlib
import re
import ssl
import sys
import urllib.error
import urllib.request
from datetime import date, datetime
from zoneinfo import ZoneInfo

# Fuso da redação: a hora que a figura mostra ao leitor é a de Brasília, não a do runner
# (que roda em UTC). Sem isto, "consultado às 14:02" apareceria três horas adiantado.
FUSO_REDACAO = ZoneInfo("America/Sao_Paulo")

# Livro da rodada: cada chamada de rede das fontes de cadência sub-diária deixa aqui URL,
# hora e hash da resposta, e `gravar` despeja em data/sinais_risco_consultas.json.
_LIVRO_CONSULTAS = []

# Detalhe por aviso/alerta da rodada, antes de virar o registro por município de
# data/alertas/vigentes.json. Fica fora do registro por UF de propósito: aquele é agregado
# e as páginas atuais dependem do formato dele.
_DETALHE_ALERTAS = {"inmet": None, "cemaden": None}

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
# Temperatura e qualidade do ar (24/09/2026, decisão editorial). Peso zero, como
# todo este módulo. Duas NATUREZAS de dado que nunca se misturam na mesma escala de
# cor: `estimativa de modelo` (Open-Meteo/CAMS, grade de ~11 km, não há estação no
# ponto) e `medição` (estação do INMET, monitor do OpenAQ). O rótulo viaja com o
# DADO, não com a figura, para que nenhuma página possa exibir um valor sem ele.
# ---------------------------------------------------------------------------
NATUREZA_MODELO = "estimativa de modelo"
NATUREZA_MEDICAO = "medição"

# Linha de referência para PM2,5: 15 µg/m³ de média diária, diretriz da OMS de 2021 —
# a mesma que o Ministério da Saúde usa no informe semanal de fumaça. A constante é
# declarada AQUI e gravada NO DADO; nenhuma página guarda número de referência.
REF_PM25_OMS_DIARIA = 15.0
REF_PM25_DOCUMENTO = "OMS, Global Air Quality Guidelines (2021) — média diária de PM2,5"

# Idade máxima de uma coleta antes de a figura trocar o valor por "sem coleta desde":
# um aviso do INMET dura horas, e retrato velho sem aviso de idade é dado falso.
VALIDADE_HORAS_SINAL = 36

# Capital de cada UF pelo CÓDIGO IBGE — a chave canônica. Nome e coordenada saem de
# data/municipios_ibge_referencia.json em tempo de execução, então esta tabela não
# duplica a lista de nomes de recalcular_mare.py (que exige numpy e não deve entrar
# num coletor). O autoteste prova que os 27 códigos resolvem, um por UF.
CAPITAL_IBGE = {
    "AC": 1200401, "AL": 2704302, "AM": 1302603, "AP": 1600303, "BA": 2927408,
    "CE": 2304400, "DF": 5300108, "ES": 3205309, "GO": 5208707, "MA": 2111300,
    "MG": 3106200, "MS": 5002704, "MT": 5103403, "PA": 1501402, "PB": 2507507,
    "PE": 2611606, "PI": 2211001, "PR": 4106902, "RJ": 3304557, "RN": 2408102,
    "RO": 1100205, "RR": 1400100, "RS": 4314902, "SC": 4205407, "SE": 2800308,
    "SP": 3550308, "TO": 1721000,
}
MUNICIPIOS_REF = RAIZ / "data" / "municipios_ibge_referencia.json"
CONSULTAS = RAIZ / "data" / "sinais_risco_consultas.json"
ALERTAS = RAIZ / "data" / "alertas" / "vigentes.json"

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
    "open_meteo_tempo": {
        "nome": "Temperatura observada e prevista", "orgao": "Open-Meteo (modelos ECMWF, DWD, NOAA)",
        "camada": "observado",
        "url_publica": "https://open-meteo.com/",
        # Sonda de 24/09/2026 com rede real: várias coordenadas numa chamada devolvem uma LISTA
        # na ORDEM pedida, e o lat/lon de volta é o do NÓ DA GRADE (-15.782 no lugar de -15.7939)
        # — casar por índice, nunca por coordenada.
        "endpoint": "https://api.open-meteo.com/v1/forecast",
        "papel": "Máxima e mínima do dia anterior e dos próximos dias, por capital, em °C.",
        "natureza": NATUREZA_MODELO,
        "licenca": "CC BY 4.0 — crédito obrigatório: Weather data by Open-Meteo.com",
    },
    "open_meteo_ar": {
        "nome": "Qualidade do ar estimada", "orgao": "Copernicus CAMS via Open-Meteo",
        "camada": "observado",
        "url_publica": "https://open-meteo.com/en/docs/air-quality-api",
        # A API entrega só série HORÁRIA (24 valores por dia, sonda de 24/09/2026); a média
        # diária é cálculo nosso e está declarada como tal no dado.
        "endpoint": "https://air-quality-api.open-meteo.com/v1/air-quality",
        "papel": "PM2,5, PM10, ozônio, NO₂ e CO estimados por modelo, por capital, em µg/m³.",
        "natureza": NATUREZA_MODELO,
        "licenca": "CC BY 4.0 — crédito obrigatório: Copernicus CAMS via Open-Meteo.com",
    },
    "noaa_oni": {
        "nome": "Oceanic Niño Index (ONI)", "orgao": "NOAA/CPC", "camada": "enos",
        "url_publica": "https://origin.cpc.ncep.noaa.gov/products/analysis_monitoring/ensostuff/ONI_v5.php",
        "endpoint": "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt",
        "papel": "Série observada do índice que define oficialmente El Niño e La Niña.",
    },
    "noaa_roni": {
        # 17/09/2026 (achado ao checar o valor do ONI, pedido da editoria): desde agosto/2026 a NOAA
        # usa o RONI, não mais o ONI clássico, como métrica oficial de classificação — o RONI desconta
        # o aquecimento médio de todo o oceano tropical, então fica mais conservador em clima mais quente.
        "nome": "Relative Oceanic Niño Index (RONI)", "orgao": "NOAA/CPC", "camada": "enos",
        "url_publica": "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/roni/",
        "endpoint": "https://www.cpc.ncep.noaa.gov/data/indices/RONI.ascii.txt",
        "papel": "Métrica oficial de classificação de El Niño e La Niña desde agosto de 2026, substituindo o ONI clássico.",
    },
    "noaa_nino34_mensal": {
        "nome": "Anomalia mensal da temperatura do mar, região Niño 3.4", "orgao": "NOAA/CPC", "camada": "enos",
        "url_publica": "https://www.cpc.ncep.noaa.gov/data/indices/detrend.nino34.ascii.txt",
        "endpoint": "https://www.cpc.ncep.noaa.gov/data/indices/detrend.nino34.ascii.txt",
        "papel": "Leitura mensal, sem a suavização de três meses que o ONI e o RONI aplicam.",
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


def agora() -> str:
    """Data E HORA da consulta, no fuso da redação, no formato dd/mm/aaaa hh:mm.

    24/09/2026 (decisão editorial): os avisos do INMET e a coleta de temperatura e ar têm
    cadência de horas, e `consultado_em` só com a data não permitia distinguir um retrato de
    quinze minutos de um de vinte e três horas — que é justamente a diferença que a regra das
    36 h precisa ver. Fontes de cadência diária ou mensal seguem só com a data."""
    return datetime.now(FUSO_REDACAO).strftime("%d/%m/%Y %H:%M")


def resolver_capitais() -> list:
    """Devolve [{'uf','ibge','nome','lat','lon'}] das 27 capitais, com nome e coordenada lidos de
    data/municipios_ibge_referencia.json (fonte única das coordenadas dos 5.571). A tabela
    CAPITAL_IBGE guarda só o código, que é a chave canônica. Levanta se alguma não resolver:
    coordenada de capital errada produziria temperatura de outra cidade, e isso não é lacuna,
    é dado falso."""
    ref = json.loads(MUNICIPIOS_REF.read_text(encoding="utf-8"))
    por_codigo = {int(m["codigo_ibge"]): m for m in ref if m.get("codigo_ibge")}
    saida = []
    for uf, codigo in sorted(CAPITAL_IBGE.items()):
        m = por_codigo.get(codigo)
        if not m or m.get("uf") != uf or m.get("lat") is None or m.get("lon") is None:
            raise ValueError(f"capital de {uf} (IBGE {codigo}) não resolve em municipios_ibge_referencia.json")
        saida.append({"uf": uf, "ibge": codigo, "nome": m["nome"],
                      "lat": float(m["lat"]), "lon": float(m["lon"])})
    return saida


def registrar_consulta(chave: str, url: str, bruto: str) -> None:
    """Acrescenta ao livro de consultas (data/sinais_risco_consultas.json) a URL, a hora e o hash
    da resposta. É registro de transparência: permite conferir DEPOIS que o número publicado veio
    daquela resposta, e é append-only dentro da rodada do dia."""
    _LIVRO_CONSULTAS.append({
        "fonte": chave, "url": url, "consultado_em": agora(),
        "bytes": len(bruto or ""),
        "sha256": hashlib.sha256((bruto or "").encode("utf-8", errors="replace")).hexdigest(),
    })


def _contexto_tls():
    """Contexto TLS com o pacote de CAs do `certifi` quando ele existe, e o do sistema quando não.

    24/09/2026: `gsc.cemaden.gov.br` serve uma cadeia que a loja de certificados desta máquina
    Windows não completa, e a coleta morria com CERTIFICATE_VERIFY_FAILED — o que parecia fonte
    fora do ar e era ambiente. Isto NÃO afrouxa a verificação: continua validando o certificado,
    contra um conjunto de raízes mais completo e igual em qualquer máquina. Fonte que recusa de
    verdade continua recusando."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return None


def _buscar(url: str) -> str:
    """GET simples com cabeçalho identificado e tempo limite; erros sobem para quem chamou tratar."""
    req = urllib.request.Request(url, headers=CABECALHO)
    with urllib.request.urlopen(req, timeout=TEMPO_LIMITE, context=_contexto_tls()) as r:
        return r.read().decode("utf-8", errors="replace")


def _buscar_registrado(chave: str, url: str) -> str:
    """Como `_buscar`, e deixa rastro no livro de consultas. Usado pelas fontes de cadência sub-diária."""
    bruto = _buscar(url)
    registrar_consulta(chave, url, bruto)
    return bruto


def _coordenadas_em_lote(pontos: list) -> str:
    """Monta o par latitude=…&longitude=… com as N coordenadas numa chamada só (a API aceita listas
    separadas por vírgula e responde na mesma ordem)."""
    return ("latitude=" + ",".join(f"{p['lat']:.4f}" for p in pontos)
            + "&longitude=" + ",".join(f"{p['lon']:.4f}" for p in pontos))


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


def parse_roni(texto: str) -> list:
    """17/09/2026 (pedido da editoria, achado ao checar o ONI atual): a NOAA passou a usar o RONI
    (Relative Oceanic Niño Index) como métrica oficial de classificação desde agosto/2026 (o ONI
    clássico segue existindo e é o que a página já mostrava). Mesmo formato de parse_oni, mas o
    arquivo do RONI não tem a coluna TOTAL (só SEAS YR ANOM)."""
    serie = []
    for linha in texto.splitlines():
        partes = linha.split()
        if len(partes) != 3 or partes[0] == "SEAS":
            continue
        try:
            serie.append({"trimestre": partes[0], "ano": int(partes[1]), "anomalia": float(partes[2])})
        except ValueError:
            continue
    return serie


def parse_nino34_mensal(texto: str) -> list:
    """17/09/2026: leitura mensal, não suavizada em três meses, da anomalia de temperatura na região
    Niño 3.4 (arquivo 'detrend.nino34.ascii.txt' do CPC, colunas YR MON TOTAL ClimAdjust ANOM) — a
    matéria-prima mensal da qual tanto o ONI quanto o RONI derivam a média móvel trimestral. Só os
    últimos ~48 meses interessam à página (tendência recente), não a série inteira desde 1949."""
    serie = []
    for linha in texto.splitlines():
        partes = linha.split()
        if len(partes) != 5 or partes[0] == "YR":
            continue
        try:
            serie.append({"ano": int(partes[0]), "mes": int(partes[1]), "anomalia": float(partes[4])})
        except ValueError:
            continue
    return serie[-48:]


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


def _media(valores) -> float:
    """Média aritmética dos valores numéricos; None se não houver nenhum — ausência não vira zero."""
    limpos = [v for v in (valores or []) if isinstance(v, (int, float))]
    return round(sum(limpos) / len(limpos), 1) if limpos else None


def parse_open_meteo_tempo(dados, chaves) -> dict:
    """Lê a resposta do Forecast do Open-Meteo para N coordenadas e devolve {chave: {...}}.

    `chaves` é a lista de identificadores NA MESMA ORDEM em que as coordenadas foram pedidas: a
    API devolve uma lista posicional e o lat/lon de volta é o do nó da grade, então casar por
    coordenada erraria. Cada registro traz a série diária (ontem, hoje e os próximos), com a
    unidade declarada pela própria API. Função pura."""
    itens = dados if isinstance(dados, list) else [dados]
    saida = {}
    for chave, bloco in zip(chaves, itens):
        d = (bloco or {}).get("daily") or {}
        dias = d.get("time") or []
        if not dias:
            continue
        unidade = ((bloco.get("daily_units") or {}).get("temperature_2m_max")) or "°C"

        def _v(campo, i):
            col = d.get(campo) or []
            return col[i] if i < len(col) and isinstance(col[i], (int, float)) else None

        serie = [{"data": dia, "maxima": _v("temperature_2m_max", i),
                  "minima": _v("temperature_2m_min", i),
                  "aparente_maxima": _v("apparent_temperature_max", i)}
                 for i, dia in enumerate(dias)]
        if all(p["maxima"] is None for p in serie):
            continue                     # série sem nenhuma máxima é lacuna, não zero
        saida[chave] = {"unidade": unidade, "serie": serie, "natureza": NATUREZA_MODELO,
                        "no_da_grade": {"lat": bloco.get("latitude"), "lon": bloco.get("longitude")}}
    return saida


def parse_open_meteo_ar(dados, chaves) -> dict:
    """Lê o Air Quality do Open-Meteo (Copernicus CAMS) para N coordenadas e devolve {chave: {...}}
    com a média DIÁRIA de cada poluente calculada a partir das horas — a API entrega só horário.
    Ordem posicional, como no Forecast. Sem PM2,5 o registro não entra: lacuna, nunca zero.
    Função pura."""
    itens = dados if isinstance(dados, list) else [dados]
    campos = ("pm2_5", "pm10", "ozone", "nitrogen_dioxide", "carbon_monoxide")
    saida = {}
    for chave, bloco in zip(chaves, itens):
        h = (bloco or {}).get("hourly") or {}
        horas = h.get("time") or []
        if not horas:
            continue
        unidades = bloco.get("hourly_units") or {}
        medias = {c: _media(h.get(c)) for c in campos}
        if medias.get("pm2_5") is None:
            continue
        saida[chave] = {
            "horas_lidas": len(horas),
            "media_diaria": medias,
            "media_diaria_calculada_por": "média aritmética das horas devolvidas pela API",
            "unidades": {c: unidades.get(c, "μg/m³") for c in campos},
            "natureza": NATUREZA_MODELO,
            "referencia_pm25": {"valor": REF_PM25_OMS_DIARIA, "unidade": "µg/m³",
                                "documento": REF_PM25_DOCUMENTO},
            "no_da_grade": {"lat": bloco.get("latitude"), "lon": bloco.get("longitude")},
        }
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


def parse_municipios_do_aviso(texto: str) -> list:
    """Lê o campo `municipios` do INMET e devolve [{'nome','uf','geocode'}].

    Formato real (sonda de 24/09/2026): "Alta Floresta - MT (5100250),Altamira - PA (1500602),…"
    — um aviso pode listar centenas de municípios de várias UFs. Entrada sem o código IBGE entre
    parênteses é DESCARTADA: sem código não há como casar com o banco, e casar por nome traria o
    homônimo errado (há 'Bom Jesus' em seis estados). Função pura."""
    achados, vistos = [], set()
    for bruto in re.split(r"\),\s*", str(texto or "")):
        m = re.match(r"\s*(.+?)\s+-\s+([A-Z]{2})\s*\((\d{7})\)?\s*$", bruto.strip())
        if not m:
            continue
        nome, uf, cod = m.group(1).strip(), m.group(2), m.group(3)
        if uf not in UFS or cod in vistos:
            continue
        vistos.add(cod)
        achados.append({"nome": nome, "uf": uf, "geocode": cod})
    return achados


def parse_avisos_inmet_detalhado(dados) -> list:
    """Devolve UM registro por aviso vigente, com tipo, grau, vigência e municípios — a
    granularidade que a página de Defesa civil precisa e que o agregado por UF descartava.

    O TIPO é o que o INMET escreve em `descricao` ("Chuvas Intensas", "Onda de Calor"), tal e
    qual: lista aberta, sem mapear para categoria própria — o vocabulário de severidade e de
    tipo é o da fonte (§23.2).

    O que NÃO entra: `aviso_cor` (hexadecimal — cor só vive em assets/tokens.css, e a severidade
    textual basta para pintar) e `icone` (base64 de ~30 kB por aviso). Aviso com `encerrado`
    verdadeiro sai: a página diz "em vigor". Função pura."""
    itens = dados.get("hoje", dados) if isinstance(dados, dict) else dados
    if isinstance(itens, dict):
        itens = itens.get("avisos", [])
    saida = []
    for aviso in itens or []:
        if not isinstance(aviso, dict):
            continue
        if str(aviso.get("encerrado", "")).strip().lower() in ("true", "1"):
            continue
        municipios = parse_municipios_do_aviso(aviso.get("municipios"))
        if not municipios:
            continue                      # aviso sem município identificável não vira ponto no mapa
        saida.append({
            "id": str(aviso.get("id_aviso") or aviso.get("id") or "").strip(),
            "tipo": re.sub(r"\s+", " ", str(aviso.get("descricao") or aviso.get("aviso") or "").strip()),
            "severidade": (aviso.get("severidade") or aviso.get("grau") or "").strip() or "não declarada",
            "inicio": (str(aviso.get("inicio") or "").strip() or None),
            "fim": (str(aviso.get("fim") or "").strip() or None),
            "municipios": municipios,
            "ufs": sorted({m["uf"] for m in municipios}),
            "fonte": "inmet_avisos",
        })
    return saida


def parse_alertas_cemaden_detalhado(dados) -> list:
    """Devolve UM registro por alerta vigente do CEMADEN, com município, nível e tipo.

    Nomes reais dos campos, medidos com rede em 24/09/2026 (a camada só respondeu depois de
    apontar a verificação de certificado para o pacote de CAs do `certifi` — a loja desta máquina
    não tem a cadeia do gsc.cemaden.gov.br; ver `_contexto_tls`):
      `codibge` (7 dígitos), `cidade`, `uf`, `nivel`, `evento`, `vigencia`, `datahoracriacao`.

    O TIPO vem em `evento` no formato "Movimentos de Massa - Moderado", que REPETE o nível: o
    tipo é a parte antes do último " - " quando ela coincide com o nível, e o texto inteiro fica
    guardado em `evento` para conferência. Os demais nomes candidatos continuam aceitos — a
    camada já mudou de formato uma vez (04/09/2026) e `campos_vistos` deixa o nome real aparecer
    no log da rodada em vez de exigir nova sonda. Função pura."""
    feicoes = (dados or {}).get("features") if isinstance(dados, dict) else dados
    saida = []
    for f in feicoes or []:
        p = (f.get("properties") if isinstance(f, dict) else None) or (f if isinstance(f, dict) else {})
        uf = next((str(p[k]).strip().upper() for k in ("uf", "sigla_uf", "estado", "UF") if p.get(k)), "")
        if uf not in UFS:
            continue
        cod = next((str(p[k]).strip() for k in ("codibge", "geocodigo", "geocode", "cd_mun",
                                                "codigo_ibge", "cod_ibge", "ibge", "cd_geocmu") if p.get(k)), "")
        nivel = next((str(p[k]).strip() for k in ("nivel", "severidade", "nivel_alerta", "classificacao") if p.get(k)), "")
        evento = next((str(p[k]).strip() for k in ("evento", "tipo", "tipo_alerta", "risco", "ameaca") if p.get(k)), "")
        tipo = evento
        if evento and nivel and evento.lower().endswith(f"- {nivel}".lower()):
            tipo = evento[: evento.rfind(" - ")].strip()
        saida.append({
            "geocode": cod if re.fullmatch(r"\d{7}", cod) else None,
            "nome": next((str(p[k]).strip() for k in ("cidade", "municipio", "nome_municipio", "nm_mun") if p.get(k)), ""),
            "uf": uf,
            "nivel": nivel or "sem nível declarado",
            "tipo": tipo or None,
            "evento": evento or None,
            "inicio": next((str(p[k]).strip() for k in ("vigencia", "datahoracriacao", "inicio",
                                                        "data_inicio", "dt_inicio") if p.get(k)), None),
            "fim": next((str(p[k]).strip() for k in ("fim", "data_fim", "dt_fim") if p.get(k)), None),
            "campos_vistos": sorted(p.keys()),
            "fonte": "cemaden_alertas",
        })
    return saida


def agregar_alertas_por_municipio(avisos_inmet: list, alertas_cemaden: list) -> dict:
    """Junta avisos do INMET e alertas do CEMADEN num registro POR MUNICÍPIO (chave = código IBGE).

    Um município pode estar sob mais de um aviso ao mesmo tempo, de tipos diferentes: a lista
    preserva TODOS. Escolher aqui o "pior" esconderia que há dois riscos distintos em vigor, e a
    página precisa poder dizer quais são. Alerta do CEMADEN sem código IBGE fica de fora do mapa
    por município e é contado à parte por quem chama — descartar em silêncio seria perder alerta
    real. Função pura."""
    saida = {}
    for aviso in avisos_inmet:
        for mun in aviso["municipios"]:
            reg = saida.setdefault(mun["geocode"], {"nome": mun["nome"], "uf": mun["uf"],
                                                    "inmet": [], "cemaden": []})
            reg["inmet"].append({k: aviso[k] for k in ("id", "tipo", "severidade", "inicio", "fim")})
    for alerta in alertas_cemaden:
        cod = alerta.get("geocode")
        if not cod:
            continue
        reg = saida.setdefault(cod, {"nome": alerta.get("nome") or "", "uf": alerta.get("uf") or "",
                                     "inmet": [], "cemaden": [], "cemaden_cessados": []})
        reg.setdefault("cemaden_cessados", [])
        if not reg["nome"]:
            reg["nome"] = alerta.get("nome") or ""
        # 24/09/2026 (medido com rede): a camada se chama `alertas_vigentes_siaden` mas devolve
        # também os ENCERRAMENTOS, com `nivel` = "Cessar" — 17 dos 29 alertas naquela consulta.
        # "Cessar" não é grau de severidade, é o fim de um alerta: contá-lo como alerta em vigor
        # inflaria a contagem pública. Fica guardado à parte, porque alerta encerrado hoje é
        # informação (o risco existiu e passou), e não ausência de dado.
        destino = "cemaden_cessados" if str(alerta.get("nivel", "")).strip().lower() == "cessar" else "cemaden"
        reg[destino].append({k: alerta.get(k) for k in ("nivel", "tipo", "evento", "inicio", "fim")})
    # Município que só tinha encerramento não está sob nada em vigor: sai do mapa de "em vigor",
    # mas o registro do encerramento permanece no arquivo, sob a chave própria.
    for reg in saida.values():
        reg.setdefault("cemaden_cessados", [])
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

    # As duas fontes do Open-Meteo pedem as 27 coordenadas numa chamada só e tratam a resposta
    # posicionalmente; saem antes do GET genérico abaixo.
    if chave in ("open_meteo_tempo", "open_meteo_ar"):
        capitais = resolver_capitais()
        chaves = [c["uf"] for c in capitais]
        if chave == "open_meteo_tempo":
            url = (f"{fonte['endpoint']}?{_coordenadas_em_lote(capitais)}"
                   "&daily=temperature_2m_max,temperature_2m_min,apparent_temperature_max"
                   "&timezone=America%2FSao_Paulo&past_days=1&forecast_days=4")
            lido = parse_open_meteo_tempo(json.loads(_buscar_registrado(chave, url)), chaves)
            if len(lido) < 20:
                raise ValueError(f"temperatura cobriu só {len(lido)} de 27 capitais — recusada")
            dias = sorted({p["data"] for v in lido.values() for p in v["serie"]})
            return ({"por_uf": lido, "capitais": capitais},
                    f"Open-Meteo Forecast — 27 capitais, {dias[0]} a {dias[-1]}")
        url = (f"{fonte['endpoint']}?{_coordenadas_em_lote(capitais)}"
               "&hourly=pm2_5,pm10,ozone,nitrogen_dioxide,carbon_monoxide"
               "&timezone=America%2FSao_Paulo&forecast_days=1&domains=cams_global")
        lido = parse_open_meteo_ar(json.loads(_buscar_registrado(chave, url)), chaves)
        if len(lido) < 20:
            raise ValueError(f"qualidade do ar cobriu só {len(lido)} de 27 capitais — recusada")
        return ({"por_uf": lido, "capitais": capitais},
                "Copernicus CAMS via Open-Meteo — 27 capitais, média diária do dia da consulta")

    bruto = _buscar(fonte["endpoint"] + (str(IBGE_UF["RO"]) if chave == "monitor_secas" else ""))
    if chave == "noaa_oni":
        serie = parse_oni(bruto)
        if len(serie) < 12:
            raise ValueError(f"série ONI curta demais ({len(serie)} pontos) — recusada")
        ultimo = serie[-1]
        return {"serie": serie[-160:]}, f"ONI v5, último trimestre {ultimo['trimestre']}/{ultimo['ano']}"
    if chave == "noaa_roni":
        serie = parse_roni(bruto)
        if len(serie) < 12:
            raise ValueError(f"série RONI curta demais ({len(serie)} pontos) — recusada")
        ultimo = serie[-1]
        return {"serie": serie[-160:]}, f"RONI, último trimestre {ultimo['trimestre']}/{ultimo['ano']}"
    if chave == "noaa_nino34_mensal":
        serie = parse_nino34_mensal(bruto)
        if len(serie) < 6:
            raise ValueError(f"série mensal Niño 3.4 curta demais ({len(serie)} pontos) — recusada")
        ultimo = serie[-1]
        return {"serie": serie}, f"Niño 3.4 mensal, último mês {ultimo['mes']:02d}/{ultimo['ano']}"
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
        dados = json.loads(bruto)
        registrar_consulta(chave, fonte["endpoint"], bruto)
        # 24/09/2026: o agregado por UF continua (as páginas atuais o usam) E passa a sair o
        # detalhe por aviso, com tipo, vigência e municípios — que já vinham na resposta e eram
        # descartados na agregação.
        return ({"por_uf": parse_avisos_inmet(dados),
                 "detalhe": parse_avisos_inmet_detalhado(dados)},
                "Avisos ativos no momento da consulta")
    if chave == "cemaden_alertas":
        dados = json.loads(bruto)
        registrar_consulta(chave, fonte["endpoint"], bruto)
        return ({"por_uf": parse_alertas_wfs_cemaden(dados),
                 "detalhe": parse_alertas_cemaden_detalhado(dados)},
                "Alertas vigentes (camada alertas_vigentes_siaden, CEMADEN)")
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
            # 24/09/2026: as duas naturezas de dado e a linha de referência da OMS ficam
            # declaradas NO DADO, nunca no HTML. Figura de modelo e figura de medição não
            # compartilham escala de cor — a página lê estes rótulos para saber qual é qual.
            "naturezas": {
                NATUREZA_MODELO: "valor calculado por modelo numérico numa grade, sem estação no ponto",
                NATUREZA_MEDICAO: "valor lido por estação ou monitor instalado no local",
            },
            "referencia_pm25_oms": {"valor": REF_PM25_OMS_DIARIA, "unidade": "µg/m³",
                                    "documento": REF_PM25_DOCUMENTO},
            "validade_horas_sinal": VALIDADE_HORAS_SINAL,
            "escrito_por": "coletar_sinais_risco.py",
        },
        "gerado_em": hoje(),
        "fontes": {
            chave: {**{k: v for k, v in dados.items() if k != "endpoint"},
                    "status": "aguardando_primeira_coleta", "consultado_em": None,
                    "documento": None, "detalhe": None}
            for chave, dados in FONTES.items()
        },
        "enos": {"oni": None, "roni": None, "nino34_mensal": None, "probabilidades": None, "prognostico": None},
        "uf": {uf: {"risco_projetado": None, "secas": None, "avisos_inmet": None,
                    "fogo": None, "alertas_cemaden": None,
                    "temperatura": None, "qualidade_ar": None} for uf in UFS},
    }


def normalizar(registro: dict) -> dict:
    """Traz um registro escrito por uma versão anterior ao formato de hoje, sem apagar coleta.

    Fonte nova entra como lacuna declarada (`aguardando_primeira_coleta`), campo novo de UF entra
    nulo. Sem isto, acrescentar uma fonte exigiria `--semear --zerar`, que descartaria a coleta
    acumulada — e a alternativa preguiçosa (criar a chave dentro de `coletar`) esconderia a fonte
    nova do portão enquanto ela não coletasse pela primeira vez."""
    for chave, dados in FONTES.items():
        if chave not in registro.setdefault("fontes", {}):
            registro["fontes"][chave] = {**{k: v for k, v in dados.items() if k != "endpoint"},
                                         "status": "aguardando_primeira_coleta", "consultado_em": None,
                                         "documento": None, "detalhe": None}
    for uf in UFS:
        bloco = registro.setdefault("uf", {}).setdefault(uf, {})
        for campo in ("risco_projetado", "secas", "avisos_inmet", "fogo", "alertas_cemaden",
                      "temperatura", "qualidade_ar"):
            bloco.setdefault(campo, None)
    # O catálogo do _formato também envelhece: campos declarativos novos entram sem tocar no resto.
    formato = registro.setdefault("_formato", {})
    formato.setdefault("naturezas", {
        NATUREZA_MODELO: "valor calculado por modelo numérico numa grade, sem estação no ponto",
        NATUREZA_MEDICAO: "valor lido por estação ou monitor instalado no local",
    })
    formato.setdefault("referencia_pm25_oms", {"valor": REF_PM25_OMS_DIARIA, "unidade": "µg/m³",
                                               "documento": REF_PM25_DOCUMENTO})
    formato.setdefault("validade_horas_sinal", VALIDADE_HORAS_SINAL)
    return registro


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
        elif chave == "noaa_roni":
            registro["enos"]["roni"] = {**payload, "fonte": chave, "documento": documento}
        elif chave == "noaa_nino34_mensal":
            registro["enos"]["nino34_mensal"] = {**payload, "fonte": chave, "documento": documento}
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
            _DETALHE_ALERTAS["inmet"] = payload.get("detalhe") or []
            for uf in UFS:
                dados = payload["por_uf"].get(uf) or {"total": 0, "graus": {}, "exemplos": []}
                registro["uf"][uf]["avisos_inmet"] = {**dados, "fonte": chave,
                                                      "documento": documento, "consultado_em": agora()}
        elif chave == "cemaden_alertas":
            _DETALHE_ALERTAS["cemaden"] = payload.get("detalhe") or []
            for uf in UFS:
                dados = payload["por_uf"].get(uf) or {"total": 0, "niveis": {}, "municipios": []}
                registro["uf"][uf]["alertas_cemaden"] = {**dados, "fonte": chave,
                                                         "documento": documento, "consultado_em": agora()}
        # 24/09/2026: temperatura e ar são por CAPITAL, e a capital representa a UF no mapa —
        # o registro diz qual cidade foi medida, para que a legenda não sugira média estadual.
        elif chave in ("open_meteo_tempo", "open_meteo_ar"):
            campo = "temperatura" if chave == "open_meteo_tempo" else "qualidade_ar"
            capital_de = {c["uf"]: c for c in payload["capitais"]}
            for uf in UFS:
                lido = payload["por_uf"].get(uf)
                cap = capital_de.get(uf, {})
                registro["uf"][uf][campo] = ({**lido, "capital": {k: cap.get(k) for k in ("nome", "ibge", "lat", "lon")},
                                              "fonte": chave, "documento": documento,
                                              "consultado_em": agora()}
                                             if lido else None)   # capital sem leitura fica nula: lacuna, nunca zero
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
    REGISTRO.write_text(json.dumps(registro, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"→ {REGISTRO.relative_to(RAIZ)} gravado.")


def gravar_alertas_vigentes() -> None:
    """Grava data/alertas/vigentes.json: um registro por MUNICÍPIO sob aviso do INMET ou alerta
    do CEMADEN, com tipo, grau, início e fim.

    Só grava quando ao menos uma das duas fontes respondeu nesta rodada. Fonte muda não é fonte
    dizendo zero: reescrever o arquivo com a metade que respondeu apagaria os alertas da outra e
    a página mostraria menos município do que há. Quando uma das duas falha, o arquivo anterior
    fica intacto e a rodada diz isso no log."""
    inmet, cemaden = _DETALHE_ALERTAS["inmet"], _DETALHE_ALERTAS["cemaden"]
    if inmet is None and cemaden is None:
        print("[aviso] alertas: nenhuma das duas fontes respondeu — data/alertas/vigentes.json mantido.")
        return
    if inmet is None or cemaden is None:
        qual = "INMET" if inmet is None else "CEMADEN"
        print(f"[aviso] alertas: {qual} não respondeu — data/alertas/vigentes.json mantido "
              "(meia coleta apagaria alerta real da outra fonte).")
        return
    todos = agregar_alertas_por_municipio(inmet, cemaden)
    # "Em vigor" é o que está em vigor: município que só tem encerramento do CEMADEN não entra no
    # mapa nem na contagem. O encerramento segue registrado em `cessados`, à parte.
    por_municipio = {k: v for k, v in todos.items() if v["inmet"] or v["cemaden"]}
    cessados = {k: v["cemaden_cessados"] for k, v in todos.items() if v["cemaden_cessados"]}
    sem_codigo = [a for a in cemaden if not a.get("geocode")]
    # Chaves que o CEMADEN devolveu nesta rodada: é assim que o nome real do campo de TIPO
    # aparece no log, sem precisar de outra sonda com rede.
    campos_cemaden = sorted({c for a in cemaden for c in (a.get("campos_vistos") or [])})
    ALERTAS.parent.mkdir(parents=True, exist_ok=True)
    ALERTAS.write_text(json.dumps({
        "_formato": {
            "descricao": "Avisos meteorológicos do INMET e alertas do CEMADEN em vigor, por município.",
            "efeito_no_indice": "NENHUM — peso zero, como todo sinal de risco (METODOLOGIA §23).",
            "regra_de_prova": "Tipo, grau e vigência são reproduzidos no vocabulário do órgão que "
                              "os emitiu. Município pode estar sob mais de um aviso ao mesmo tempo: "
                              "a lista preserva todos, sem escolher o mais grave.",
            "cessados": "A camada do CEMADEN devolve também os ENCERRAMENTOS, com nível 'Cessar'. "
                        "Encerramento não é alerta em vigor e não entra na contagem; fica aqui "
                        "porque alerta encerrado hoje é informação, não ausência de dado.",
            "validade_horas": VALIDADE_HORAS_SINAL,
            "escrito_por": "coletar_sinais_risco.py",
        },
        "gerado_em": agora(),
        "resumo": {
            "municipios": len(por_municipio),
            "municipios_inmet": sum(1 for v in por_municipio.values() if v["inmet"]),
            "municipios_cemaden": sum(1 for v in por_municipio.values() if v["cemaden"]),
            "avisos_inmet": len(inmet),
            "alertas_cemaden_em_vigor": sum(len(v["cemaden"]) for v in por_municipio.values()),
            "alertas_cemaden_cessados": sum(len(v) for v in cessados.values()),
            "alertas_cemaden_devolvidos": len(cemaden),
            "alertas_cemaden_sem_codigo_ibge": len(sem_codigo),
            "campos_devolvidos_pelo_cemaden": campos_cemaden,
        },
        "municipios": {k: {c: v[c] for c in ("nome", "uf", "inmet", "cemaden")}
                       for k, v in sorted(por_municipio.items())},
        "cessados": dict(sorted(cessados.items())),
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"→ {ALERTAS.relative_to(RAIZ)} gravado ({len(por_municipio)} município(s) "
          f"em vigor; {sum(len(v) for v in cessados.values())} encerramento(s) à parte; "
          f"{len(sem_codigo)} alerta(s) do CEMADEN sem código IBGE).")
    if campos_cemaden:
        print(f"  campos do CEMADEN nesta rodada: {', '.join(campos_cemaden)}")


def gravar_consultas() -> None:
    """Grava o livro de consultas da rodada (URL, hora e hash de cada chamada de rede).

    É registro de transparência, não série histórica: guarda A RODADA, porque o que ele prova é
    que o número publicado agora veio daquela resposta. Rodada sem nenhuma chamada não apaga o
    livro anterior — apagar seria dizer que não houve consulta, e o certo é dizer que esta
    rodada não consultou."""
    if not _LIVRO_CONSULTAS:
        return
    CONSULTAS.write_text(json.dumps({
        "_formato": {
            "descricao": "URL, hora e hash da resposta de cada chamada de rede da última rodada "
                         "das fontes de cadência sub-diária.",
            "efeito_no_indice": "NENHUM — peso zero, como todo sinal de risco.",
            "escrito_por": "coletar_sinais_risco.py",
        },
        "gerado_em": agora(),
        "consultas": _LIVRO_CONSULTAS,
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"→ {CONSULTAS.relative_to(RAIZ)} gravado ({len(_LIVRO_CONSULTAS)} consulta(s)).")


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

    # 17/09/2026: parse_roni e parse_nino34_mensal, mesmo padrão de checagem que parse_oni já tinha.
    _roni_teste = parse_roni("SEAS   YR  ANOM\nDJF  2026 -0.91\nJFM  2026 -0.76\nJJA  2026  1.36\n")
    checar("RONI: lê três colunas (sem TOTAL)", _roni_teste == [
        {"trimestre": "DJF", "ano": 2026, "anomalia": -0.91},
        {"trimestre": "JFM", "ano": 2026, "anomalia": -0.76},
        {"trimestre": "JJA", "ano": 2026, "anomalia": 1.36},
    ])
    checar("RONI negativo: cabeçalho não vira ponto de série", parse_roni("SEAS   YR  ANOM\n") == [])
    _mensal_teste = parse_nino34_mensal(" YR   MON  TOTAL ClimAdjust ANOM\n2026   7   29.07   27.29    1.78\n2026   8   29.04   26.87    2.17\n")
    checar("Niño 3.4 mensal: lê a 5ª coluna (ANOM), não a 3ª (TOTAL)", _mensal_teste == [
        {"ano": 2026, "mes": 7, "anomalia": 1.78}, {"ano": 2026, "mes": 8, "anomalia": 2.17}])

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
    checar("esqueleto: temperatura e qualidade do ar existem como lacuna declarada",
           all(esq["uf"][u]["temperatura"] is None and esq["uf"][u]["qualidade_ar"] is None for u in UFS))
    checar("esqueleto: a linha da OMS e as duas naturezas estão declaradas NO DADO",
           esq["_formato"]["referencia_pm25_oms"]["valor"] == 15.0
           and set(esq["_formato"]["naturezas"]) == {NATUREZA_MODELO, NATUREZA_MEDICAO})

    # ---- temperatura e qualidade do ar (24/09/2026) ----------------------
    checar("média: ignora nulo e não conta como zero", _media([10, None, 20]) == 15.0)
    checar("média negativa: só nulos devolve None (ausência não vira zero)", _media([None, None]) is None)

    # A resposta devolve o lat/lon do NÓ DA GRADE, diferente do pedido — o teste usa valores
    # trocados de propósito para provar que o casamento é POSICIONAL e não por coordenada.
    _tempo = parse_open_meteo_tempo([
        {"latitude": -15.78, "longitude": -47.88, "daily_units": {"temperature_2m_max": "°C"},
         "daily": {"time": ["2026-09-23", "2026-09-24"], "temperature_2m_max": [30.3, 31.1],
                   "temperature_2m_min": [18.0, 19.2], "apparent_temperature_max": [32.0, 33.0]}},
        {"latitude": -23.55, "longitude": -46.63, "daily_units": {"temperature_2m_max": "°C"},
         "daily": {"time": ["2026-09-23", "2026-09-24"], "temperature_2m_max": [24.0, 25.5],
                   "temperature_2m_min": [14.0, 15.0], "apparent_temperature_max": [25.0, 26.0]}},
    ], ["DF", "SP"])
    checar("Open-Meteo tempo: casa por POSIÇÃO, não por coordenada",
           _tempo["DF"]["serie"][0]["maxima"] == 30.3 and _tempo["SP"]["serie"][1]["maxima"] == 25.5)
    checar("Open-Meteo tempo: guarda ontem e os dias seguintes, com unidade da própria API",
           len(_tempo["DF"]["serie"]) == 2 and _tempo["DF"]["unidade"] == "°C")
    checar("Open-Meteo tempo: rotula a natureza no próprio dado",
           _tempo["SP"]["natureza"] == NATUREZA_MODELO)
    checar("Open-Meteo tempo negativo: série sem nenhuma máxima é lacuna, não zero",
           parse_open_meteo_tempo([{"daily": {"time": ["2026-09-24"], "temperature_2m_max": [None]}}], ["DF"]) == {})
    checar("Open-Meteo tempo negativo: resposta vazia não quebra",
           parse_open_meteo_tempo([], ["DF"]) == {} and parse_open_meteo_tempo([{}], ["DF"]) == {})

    _ar = parse_open_meteo_ar([
        {"latitude": -15.78, "longitude": -47.88, "hourly_units": {"pm2_5": "μg/m³"},
         "hourly": {"time": ["h1", "h2", "h3", "h4"], "pm2_5": [10.0, 20.0, None, 30.0],
                    "pm10": [15.0, 25.0, 35.0, 45.0], "ozone": [None, None, None, None],
                    "nitrogen_dioxide": [1.0, 1.0, 1.0, 1.0], "carbon_monoxide": [2.0, 2.0, 2.0, 2.0]}},
    ], ["DF"])
    checar("Open-Meteo ar: média diária é a média das horas, pulando as nulas (10+20+30)/3 = 20",
           _ar["DF"]["media_diaria"]["pm2_5"] == 20.0)
    checar("Open-Meteo ar: poluente só com nulos fica None, não zero",
           _ar["DF"]["media_diaria"]["ozone"] is None)
    checar("Open-Meteo ar: a linha da OMS viaja com o dado",
           _ar["DF"]["referencia_pm25"]["valor"] == REF_PM25_OMS_DIARIA)
    checar("Open-Meteo ar: declara que a média diária é cálculo nosso",
           "média aritmética" in _ar["DF"]["media_diaria_calculada_por"])
    checar("Open-Meteo ar negativo: sem PM2,5 o registro não entra (lacuna, nunca zero)",
           parse_open_meteo_ar([{"hourly": {"time": ["h1"], "pm2_5": [None]}}], ["DF"]) == {})

    _caps = resolver_capitais()
    checar("capitais: as 27 resolvem em municipios_ibge_referencia.json, uma por UF",
           len(_caps) == 27 and {c["uf"] for c in _caps} == set(UFS))
    checar("capitais: coordenada e nome vêm do arquivo de referência, não desta tabela",
           all(isinstance(c["lat"], float) and isinstance(c["lon"], float) and c["nome"] for c in _caps))
    checar("capitais: DF é Brasília e RJ é Rio de Janeiro (prova de que o código não trocou de cidade)",
           next(c["nome"] for c in _caps if c["uf"] == "DF") == "Brasília"
           and next(c["nome"] for c in _caps if c["uf"] == "RJ") == "Rio de Janeiro")
    checar("lote: N coordenadas viram um par latitude=…&longitude=… na mesma ordem",
           _coordenadas_em_lote([{"lat": -1.5, "lon": -2.5}, {"lat": -3.5, "lon": -4.5}])
           == "latitude=-1.5000,-3.5000&longitude=-2.5000,-4.5000")
    checar("hora: consultado_em das fontes sub-diárias tem dd/mm/aaaa hh:mm",
           re.fullmatch(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}", agora()) is not None)

    # ---- granularidade municipal dos avisos e alertas (24/09/2026) -------
    _muns = parse_municipios_do_aviso(
        "Alta Floresta - MT (5100250),Altamira - PA (1500602),Sem Codigo - BA,Alta Floresta - MT (5100250)")
    checar("municípios do aviso: lê nome, UF e código IBGE do formato real do INMET",
           _muns == [{"nome": "Alta Floresta", "uf": "MT", "geocode": "5100250"},
                     {"nome": "Altamira", "uf": "PA", "geocode": "1500602"}])
    checar("municípios do aviso: entrada sem código IBGE é descartada (homônimo entraria errado)",
           all(m["geocode"] for m in _muns))
    checar("municípios do aviso negativo: campo vazio devolve lista vazia",
           parse_municipios_do_aviso("") == [] and parse_municipios_do_aviso(None) == [])

    _crus = {"hoje": [
        {"id_aviso": "28327", "descricao": "Chuvas Intensas", "severidade": "Perigo Potencial",
         "aviso_cor": "#FFFE00", "inicio": "2026-09-24 09:02", "fim": "2026-09-24 23:59",
         "encerrado": "False", "municipios": "Alta Floresta - MT (5100250),Altamira - PA (1500602)"},
        {"id_aviso": "28400", "descricao": "Onda de Calor", "severidade": "Perigo",
         "inicio": "2026-09-24 10:00", "fim": "2026-09-25 23:59",
         "encerrado": "False", "municipios": "Alta Floresta - MT (5100250)"},
        {"id_aviso": "28111", "descricao": "Geada", "severidade": "Perigo", "encerrado": "True",
         "municipios": "Curitiba - PR (4106902)"},
        {"id_aviso": "28999", "descricao": "Vendaval", "severidade": "Perigo", "municipios": ""},
    ]}
    _det = parse_avisos_inmet_detalhado(_crus)
    checar("avisos detalhados: um registro por aviso, com o tipo que o INMET escreve",
           [a["tipo"] for a in _det] == ["Chuvas Intensas", "Onda de Calor"])
    checar("avisos detalhados: aviso encerrado não entra em 'em vigor'",
           all(a["id"] != "28111" for a in _det))
    checar("avisos detalhados: aviso sem município identificável não vira ponto no mapa",
           all(a["id"] != "28999" for a in _det))
    checar("avisos detalhados: guarda vigência com hora e as UFs alcançadas",
           _det[0]["inicio"] == "2026-09-24 09:02" and _det[0]["ufs"] == ["MT", "PA"])
    checar("avisos detalhados: NÃO grava hexadecimal (cor só vive em tokens.css)",
           not any("#" in json.dumps(a, ensure_ascii=False) for a in _det))

    _cem = parse_alertas_cemaden_detalhado({"features": [
        {"properties": {"uf": "RJ", "municipio": "Petrópolis", "geocodigo": "3303906",
                        "nivel": "Alto", "tipo": "Geológico"}},
        {"properties": {"uf": "MG", "municipio": "Ubá", "nivel": "Moderado"}},
        {"properties": {"uf": "ZZ", "municipio": "Nenhum", "nivel": "Alto"}},
    ]})
    checar("alertas CEMADEN detalhados: lê município, nível e tipo; descarta UF inválida",
           len(_cem) == 2 and _cem[0]["tipo"] == "Geológico" and _cem[0]["geocode"] == "3303906")
    checar("alertas CEMADEN detalhados: sem código IBGE o geocode fica nulo, não inventado",
           _cem[1]["geocode"] is None)
    checar("alertas CEMADEN detalhados: guarda as chaves vistas, para o log revelar o nome real do tipo",
           "nivel" in _cem[1]["campos_vistos"])

    _agg = agregar_alertas_por_municipio(_det, _cem)
    checar("alertas por município: o mesmo município com dois avisos preserva OS DOIS",
           len(_agg["5100250"]["inmet"]) == 2)
    checar("alertas por município: INMET e CEMADEN convivem na mesma chave de município",
           set(_agg) == {"5100250", "1500602", "3303906"})
    checar("alertas por município: alerta sem código IBGE fica fora do mapa, e não vira município falso",
           all(k != "None" and k is not None for k in _agg))
    checar("alertas por município negativo: sem nada em vigor devolve vazio",
           agregar_alertas_por_municipio([], []) == {})

    # "Cessar" é o FIM de um alerta, não um grau — medido com rede em 24/09/2026, 17 dos 29
    # registros da camada "alertas_vigentes" eram encerramentos.
    _cess = parse_alertas_cemaden_detalhado({"features": [
        {"properties": {"uf": "RJ", "cidade": "PETRÓPOLIS", "codibge": "3303906",
                        "nivel": "Cessar", "evento": "Risco Hidrológico - Cessar"}},
        {"properties": {"uf": "RJ", "cidade": "PETRÓPOLIS", "codibge": "3303906",
                        "nivel": "Moderado", "evento": "Movimentos de Massa - Moderado"}},
    ]})
    checar("CEMADEN: o tipo sai de `evento` sem repetir o nível ('Movimentos de Massa - Moderado' → 'Movimentos de Massa')",
           _cess[1]["tipo"] == "Movimentos de Massa" and _cess[1]["evento"] == "Movimentos de Massa - Moderado")
    _sep = agregar_alertas_por_municipio([], _cess)
    checar("CEMADEN: 'Cessar' não conta como alerta em vigor",
           len(_sep["3303906"]["cemaden"]) == 1 and _sep["3303906"]["cemaden"][0]["nivel"] == "Moderado")
    checar("CEMADEN: o encerramento fica registrado à parte, não é apagado",
           len(_sep["3303906"]["cemaden_cessados"]) == 1)
    _so_cess = agregar_alertas_por_municipio([], [_cess[0]])
    checar("CEMADEN: município só com encerramento não fica 'sob alerta'",
           _so_cess["3303906"]["cemaden"] == [] and len(_so_cess["3303906"]["cemaden_cessados"]) == 1)

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
    registro = normalizar(json.loads(REGISTRO.read_text(encoding="utf-8"))) if REGISTRO.exists() else esqueleto()
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
    gravar_alertas_vigentes()
    gravar_consultas()


if __name__ == "__main__":
    main()
