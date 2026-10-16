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
import html
import json
import math
import os
import pathlib
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime
from zoneinfo import ZoneInfo
from coletores_base import ua_de, hoje_editorial  # noqa: E402  (§228: um cliente só, com propósito)
from coletores_base import normalizar_nome  # §233

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
# 29/09/2026: pontos de foco agregados em grade, gravados em arquivo próprio ao fim da rodada.
_PONTOS_FOCOS = {}
# 16/10/2026: locais do OpenAQ lidos pela fonte `openaq`, reaproveitados pelo ar medido (uma chamada só).
_AR_MEDIDO = {}

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
CABECALHO = {"User-Agent": ua_de("sinais de risco")}

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

# Teto de distância entre o monitor/estação e a capital que ele representa. Monitor longe medindo
# outra cidade não é "medição na capital", e aceitar por proximidade folgada produz crédito falso.
OPENAQ_RAIO_KM = 30.0
INMET_RAIO_KM = 40.0

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
    "inmet_previsao_capitais": {
        # 27/09/2026 (pedido da editoria: "temperatura reportada por órgão competente, para a gente
        # referenciar um órgão de referência"). Até aqui a previsão vinha do Open-Meteo, que roda
        # modelos europeus e americanos. O INMET publica previsão própria para as 27 capitais, em
        # JSON aberto e sem chave — e já é a fonte dos avisos e das estações neste mesmo site.
        # Conferido em 27/09/2026: 27 capitais, 27 UFs, cinco dias, com manhã, tarde e noite.
        "nome": "Previsão do tempo para as capitais", "orgao": "INMET", "camada": "observado",
        "url_publica": "https://previsao.inmet.gov.br/",
        "endpoint": "https://apiprevmet3.inmet.gov.br/previsao/capitais",
        "papel": "Máxima e mínima previstas para cada capital, pelo instituto oficial brasileiro.",
        "natureza": NATUREZA_MODELO,
    },
    # ---------------------------------------------------------------------
    # CAMADA DE MEDIÇÃO. O que ela promete é o que nenhuma estimativa de modelo substitui, e por
    # isso cada fonte daqui só entra com o que de fato mediu.
    #   OpenAQ v3: recusa com HTTP 401 sem `X-API-Key` (medido em 24/09/2026). 401 é bloqueio de
    #     acesso real e se respeita, sempre. A chave vem do AMBIENTE (segredo da Action), nunca do
    #     repositório — que é público. Em 26/09/2026 a sonda do §224 confirmou: a chave cadastrada
    #     é ACEITA (HTTP 200).
    #   Estações do INMET: **a credencial que travava esta fonte não era exigida pela rota que ela
    #     usa.** Medido em 26/09/2026 — `https://apitempo.inmet.gov.br/estacoes/T` responde HTTP 200
    #     com 262.904 bytes de JSON e 673 estações, SEM token nenhum, e é tudo o que
    #     `parse_estacoes_inmet` consome. A fonte declarava `INMET_API_TOKEN`, e `coletar_fonte`
    #     levantava `CredencialAusente` antes de tocar a rede: a camada de medição ficava vazia por
    #     falta de uma chave que a rota não pede. O token saiu da declaração.
    #
    #     Ao lado, dois diagnósticos errados que ficavam aqui e foram conferidos: o comentário
    #     afirmava que sem token a rota de dados devolve "204 com corpo vazio" — ela devolve **404**
    #     (medido em `/estacao/diaria/2026-09-24/2026-09-25/A001`). E o papel declarado prometia
    #     "máxima e mínima medidas", coisa que o adaptador não fazia: ele só escolhia a estação mais
    #     próxima de cada capital. A promessa agora é cumprida pela rota pública
    #     `/condicao/capitais/<data>` (200, 28 registros, sem token), abaixo.
    # ---------------------------------------------------------------------
    "openaq": {
        # 27/09/2026: investigado a pedido da editoria, porque o campo nunca teve dado.
        # A causa é só uma: a API v3 exige `X-API-Key` (responde 401 sem ela) e a v2 foi
        # desativada (410). O código JÁ estava inteiro para isso — `credencial` declarada abaixo,
        # `credencial_de()` lendo do AMBIENTE (nunca do repositório, que é público), o cabeçalho
        # enviado no despacho, e `atualizar.yml` passando o segredo. O status
        # `aguardando_credencial` que o registro mostrava era a coisa certa sendo dita.
        # Faltava apenas o segredo existir. A editoria o cadastrou em 26/09/2026.
        # NOTA: a chave é gratuita e viaja em cabeçalho, nunca em URL — por isso não entra no
        # livro de consultas, que vai ao repositório público.
        "nome": "Qualidade do ar medida", "orgao": "OpenAQ (agrega redes oficiais brasileiras)",
        "camada": "observado",
        "url_publica": "https://openaq.org/",
        "endpoint": "https://api.openaq.org/v3/locations?iso=BR&limit=1000",
        "papel": "PM2,5 medido por monitor oficial, onde existir monitor.",
        "natureza": NATUREZA_MEDICAO,
        "licenca": "CC BY 4.0 — crédito obrigatório do OpenAQ e da rede de origem",
        "credencial": "OPENAQ_API_KEY",
    },
    "inmet_estacoes": {
        "nome": "Temperatura medida em estação", "orgao": "INMET",
        "camada": "observado",
        "url_publica": "https://portal.inmet.gov.br/dadoshistoricos",
        "endpoint": "https://apitempo.inmet.gov.br/estacoes/T",
        "papel": "Máxima e mínima medidas na estação automática da capital.",
        "natureza": NATUREZA_MEDICAO,
        "licenca": "Dados abertos INMET",
        # §233: a rota de condição das capitais, que traz a máxima e a mínima MEDIDAS. Pública,
        # sem token, medida em 26/09/2026. É ela que cumpre o papel declarado acima.
        "endpoint_medida": "https://apitempo.inmet.gov.br/condicao/capitais/{data}",
    },
    "noaa_oni": {
        # 30/09/2026: APOIO TÉCNICO. Esta fonte saiu das páginas quando o Monitor de riscos
        # passou a usar o RONI como índice de referência. Ela continua coletada e passou a
        # viver na METODOLOGIA (§58) — a camada declara isso, e o portão de sinais cobra a
        # citação lá, em vez de cobrar um crédito numa página onde ela não aparece.
        "nome": "Oceanic Niño Index (ONI)", "orgao": "NOAA/CPC", "camada": "apoio_tecnico",
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
        # 30/09/2026: APOIO TÉCNICO. Esta fonte saiu das páginas quando o Monitor de riscos
        # passou a usar o RONI como índice de referência. Ela continua coletada e passou a
        # viver na METODOLOGIA (§58) — a camada declara isso, e o portão de sinais cobra a
        # citação lá, em vez de cobrar um crédito numa página onde ela não aparece.
        "nome": "Anomalia mensal da temperatura do mar, região Niño 3.4", "orgao": "NOAA/CPC", "camada": "apoio_tecnico",
        "url_publica": "https://www.cpc.ncep.noaa.gov/data/indices/detrend.nino34.ascii.txt",
        "endpoint": "https://www.cpc.ncep.noaa.gov/data/indices/detrend.nino34.ascii.txt",
        "papel": "Leitura mensal, sem a suavização de três meses que o ONI e o RONI aplicam.",
    },
    "iri_plume": {
        # 24/09/2026 (§209): varredura dos caminhos de DADO, com o resultado de que não há tabela
        # aberta. Registrado para ninguém repetir:
        #   · `~forecast/ensofcst/Data/ensofcst_ONI` e as duas variantes: HTTP 404 (desde ~15/09);
        #   · `ensoforecast.iri.columbia.edu`, host novo que serve os gráficos da página:
        #     HTTP 403 em tudo que não seja a imagem publicada. 403 é bloqueio de acesso real e
        #     se respeita — não se insiste.
        #
        # 27/09/2026: aquela varredura procurou TABELA e por isso concluiu cedo demais. As
        # probabilidades estão publicadas na mesma página, em PROSA, com os trimestres nomeados:
        #   "El Niño probabilities remain at 100% from SON 2026 through FMA 2027, followed by
        #    99% in MAM 2027 and 90% in AMJ, before declining to 61% in MJJ 2027."
        # O endpoint passa a ser a própria página pública, lida por `parse_plume_prosa`. Esse
        # leitor só aceita par explicito de porcentagem e trimestre nomeado, e guarda o TRECHO de
        # onde cada número saiu — na dúvida ele não classifica, e a lacuna continua declarada.
        # `parse_plume_iri` fica, provado por fixture, para o dia em que a tabela voltar.
        "nome": "Probabilidades ENSO (plume IRI/CPC)", "orgao": "IRI/Columbia", "camada": "enos",
        "url_publica": "https://iri.columbia.edu/our-expertise/climate/forecasts/enso/current/",
        "endpoint": "https://iri.columbia.edu/our-expertise/climate/forecasts/enso/current/",
        "papel": "Probabilidade de El Niño, neutro e La Niña por trimestre.",
    },
    "cptec_prognostico": {
        # 30/09/2026: APOIO TÉCNICO. Esta fonte saiu das páginas quando o Monitor de riscos
        # passou a usar o RONI como índice de referência. Ela continua coletada e passou a
        # viver na METODOLOGIA (§58) — a camada declara isso, e o portão de sinais cobra a
        # citação lá, em vez de cobrar um crédito numa página onde ela não aparece.
        # 27/09/2026: esta fonte NUNCA teve endereço. O campo `enos.prognostico` que ela alimentava
        # foi semeado à mão uma vez, em 07/09/2026, e nada no repositório o renovava: `leitura_em`
        # não é escrito em lugar nenhum do módulo, e `coletar()` nunca tocava em `prognostico`. Como
        # o registro é lido do arquivo e modificado, o campo sobrevivia a cada rodada — congelado.
        # A página o exibia como leitura corrente. Fica declarado e sem coleta, até que exista
        # endereço aberto: a leitura automática do estado do ENOS passou a vir de `cpc_ensodisc`.
        "nome": "Prognóstico climático trimestral", "orgao": "INMET/CPTEC-INPE", "camada": "apoio_tecnico",
        "url_publica": "https://portal.inmet.gov.br/boletinsagro",
        "endpoint": None,
        "papel": "A leitura brasileira da mesma previsão, em português.",
    },
    "cpc_ensodisc": {
        # 30/09/2026: APOIO TÉCNICO. Esta fonte saiu das páginas quando o Monitor de riscos
        # passou a usar o RONI como índice de referência. Ela continua coletada e passou a
        # viver na METODOLOGIA (§58) — a camada declara isso, e o portão de sinais cobra a
        # citação lá, em vez de cobrar um crédito numa página onde ela não aparece.
        # 27/09/2026 (pedido da editoria: "construa coletores automáticos, pode até trocar a fonte").
        # A Discussão Diagnóstica do ENOS é publicada pelo CPC todo mês, aberta, sem chave, com
        # estrutura estável: data de emissão, "ENSO Alert System Status", sinopse e data da próxima.
        # O coletor extrai FATOS (status, probabilidade declarada, datas) e guarda a sinopse
        # original para conferência. A frase em inglês NÃO é traduzida automaticamente: tradução de
        # máquina sem fonte é texto inventado, e a página compõe a frase em português a partir dos
        # fatos, que é o que se pode afirmar.
        "nome": "Discussão diagnóstica do ENOS", "orgao": "CPC/NCEP/NWS (NOAA)", "camada": "apoio_tecnico",
        "url_publica": "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/ensodisc.shtml",
        "endpoint": "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/ensodisc.shtml",
        "papel": "Estado oficial do alerta de El Niño e a probabilidade declarada, mês a mês.",
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
    return hoje_editorial().strftime("%d/%m/%Y")


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
        "sha256": hashlib.sha256(bruto if isinstance(bruto, bytes)
                                 else (bruto or "").encode("utf-8", errors="replace")).hexdigest(),
    })


class CredencialAusente(RuntimeError):
    """Fonte que exige credencial e não a encontrou no ambiente.

    É classe própria, e não ValueError, porque o desfecho é diferente: resposta recusada é
    problema da fonte ou nosso, credencial ausente é decisão que a editoria ainda não tomou. A
    página diz coisas diferentes nos dois casos, e quem lê o log precisa distinguir."""


def credencial_de(chave: str) -> str | None:
    """Lê do AMBIENTE a credencial que a fonte declara em `credencial`. Nunca do repositório, que é
    público. Fonte sem `credencial` devolve None e segue sem nada."""
    nome = FONTES.get(chave, {}).get("credencial")
    return os.environ.get(nome) if nome else None


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


def _buscar(url: str, extra: dict = None, binario: bool = False):
    """GET simples com cabeçalho identificado e tempo limite; erros sobem para quem chamou tratar.

    `extra` acrescenta cabeçalho (é por onde a chave do OpenAQ viaja). O User-Agent identificado
    NUNCA é substituído: disfarçar o cliente é proibido no projeto."""
    req = urllib.request.Request(url, headers={**CABECALHO, **(extra or {})})
    with urllib.request.urlopen(req, timeout=TEMPO_LIMITE, context=_contexto_tls()) as r:
        corpo = r.read()
    return corpo if binario else corpo.decode("utf-8", errors="replace")


def _buscar_registrado(chave: str, url: str, extra: dict = None) -> str:
    """Como `_buscar`, e deixa rastro no livro de consultas. Usado pelas fontes de cadência sub-diária.

    O livro guarda a URL, e a URL nunca carrega credencial — a chave viaja em cabeçalho, de propósito,
    para não ficar registrada num arquivo que vai ao repositório público."""
    bruto = _buscar(url, extra)
    registrar_consulta(chave, url, bruto)
    return bruto


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


# Trimestres ENOS: as doze janelas de três meses, pelas iniciais em inglês, como o IRI publica.
TRIMESTRES_ENOS = ("DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ",
                   "JJA", "JAS", "ASO", "SON", "OND", "NDJ")


def parse_plume_prosa(texto: str) -> list:
    """Extrai probabilidade de El Niño por trimestre da PROSA da página do IRI.

    Devolve [{'trimestre','el_nino','la_nina','neutro','trecho'}]. `la_nina` e `neutro` ficam em
    None de propósito: a prosa publica só a probabilidade de El Niño, e completar os outros dois
    por subtração seria inventar número que a fonte não dá.

    Só aceita par explícito de porcentagem e trimestre nomeado, na mesma frase, e guarda o trecho
    de onde saiu — todo número fica conferível contra o texto da fonte. Na dúvida, não classifica.
    """
    limpo = re.sub(r"<script.*?</script>|<style.*?</style>", " ", texto, flags=re.S | re.I)
    limpo = re.sub(r"<[^>]+>", " ", limpo)
    limpo = html.unescape(limpo)
    limpo = re.sub(r"\s+", " ", limpo)

    tri = "|".join(TRIMESTRES_ENOS)
    saida, vistos = [], set()
    for frase in re.split(r"(?<=[.!?])\s+", limpo):
        if "el ni" not in frase.lower():
            continue
        # "100% from SON 2026", "99% in MAM 2027", "90% in AMJ", "61% in MJJ 2027"
        padrao = r"(\d{1,3})\s*%[^.%]{0,40}?\b(" + tri + r")\b(?:\s+(\d{4}))?"
        for m in re.finditer(padrao, frase):
            pct, rotulo, ano = int(m.group(1)), m.group(2), m.group(3)
            if not 0 <= pct <= 100:
                continue
            chave = rotulo + (ano or "")
            if chave in vistos:
                continue
            vistos.add(chave)
            saida.append({"trimestre": rotulo + (" " + ano if ano else ""), "el_nino": float(pct),
                          "la_nina": None, "neutro": None, "trecho": frase.strip()[:300]})
    return saida


MESES_EN = {n: i + 1 for i, n in enumerate("January February March April May June July August September October November December".split())}


def parse_ensodisc_cpc(texto: str) -> dict:
    """Lê a Discussão Diagnóstica do ENOS (CPC) e devolve os FATOS declarados.

    Devolve {'estado', 'sinopse', 'emitido_em', 'proxima_em', 'probabilidade', 'limiar'}.
    Nada é traduzido: a sinopse fica no original, para conferência, e a página compõe o texto em
    português a partir dos fatos. Campo que a página não encontrar fica None — na dúvida, não
    classifica.
    """
    limpo = re.sub(r"<script.*?</script>|<style.*?</style>", " ", texto, flags=re.S | re.I)
    limpo = html.unescape(re.sub(r"<[^>]+>", " ", limpo))
    limpo = re.sub(r"[ \t\xa0]+", " ", limpo)
    plano = re.sub(r"\s+", " ", limpo)

    def data(m):
        if not m:
            return None
        dia, mes, ano = int(m.group(1)), MESES_EN.get(m.group(2)), int(m.group(3))
        return "%02d/%02d/%04d" % (dia, mes, ano) if mes else None

    datas = list(re.finditer(r"\b(\d{1,2}) (" + "|".join(MESES_EN) + r") (20\d\d)\b", plano))
    emitido = data(datas[0]) if datas else None
    proxima = data(datas[1]) if len(datas) > 1 else None

    m_estado = re.search(r"ENSO Alert System Status:\s*(.{0,40}?)\s{2,}", limpo)
    estado = m_estado.group(1).strip() if m_estado else None
    if estado:
        estado = re.sub(r"\s+", " ", estado)

    m_sin = re.search(r"Synopsis:\s*(.+?\.)(?:\s|$)", plano)
    sinopse = m_sin.group(1).strip() if m_sin else None

    prob, limiar = None, None
    if sinopse:
        m_p = re.search(r"(greater than|less than|about|approximately)?\s*(\d{1,3})\s*% chance", sinopse, re.I)
        if m_p:
            valor = int(m_p.group(2))
            if 0 <= valor <= 100:
                prob = valor
                limiar = {"greater than": "acima de", "less than": "abaixo de"}.get(
                    (m_p.group(1) or "").lower(), "de")

    return {"estado": estado, "sinopse": sinopse, "emitido_em": emitido,
            "proxima_em": proxima, "probabilidade": prob, "limiar": limiar}


def parse_previsao_capitais_inmet(dados, quando: str = None) -> dict:
    """Lê a previsão do INMET para as capitais e devolve {UF: {...}} do dia pedido.

    A API devolve {cidade: {dd/mm/aaaa: {manha|tarde|noite: {...}}}}. Para cada UF toma-se a MAIOR
    máxima e a MENOR mínima entre os períodos do dia — é o que "máxima e mínima do dia" significa,
    e o critério fica declarado no registro.

    Sem `quando`, usa a primeira data que a resposta traz. UF sem máxima não entra: lacuna, nunca
    zero. Função pura.
    """
    saida = {}
    for cidade, dias in (dados or {}).items():
        if not isinstance(dias, dict) or not dias:
            continue
        dia = quando if quando in dias else sorted(dias, key=lambda t: t.split("/")[::-1])[0]
        periodos = dias.get(dia) or {}
        maximas, minimas, resumos, uf = [], [], [], None
        for nome, bloco in periodos.items():
            if not isinstance(bloco, dict):
                continue
            uf = bloco.get("uf") or uf
            for campo, alvo in (("temp_max", maximas), ("temp_min", minimas)):
                valor = bloco.get(campo)
                if isinstance(valor, (int, float)) and -90 <= valor <= 60:
                    alvo.append(float(valor))
            if bloco.get("resumo"):
                resumos.append(str(bloco["resumo"]))
        if not uf or not maximas:
            continue
        saida[uf] = {
            "capital": cidade,
            "data": dia,
            "tmax": max(maximas),
            "tmin": min(minimas) if minimas else None,
            "resumo": resumos[0] if resumos else None,
            "criterio": "maior máxima e menor mínima entre manhã, tarde e noite",
            "natureza": NATUREZA_MODELO,
        }
    return saida


PASSO_GRADE_FOCOS = 0.1   # grau; ~11 km — ver `agregar_focos_em_grade`


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


def agregar_focos_em_grade(texto: str, passo: float = PASSO_GRADE_FOCOS) -> list:
    """[[lat, lon, n]] — focos agrupados numa grade regular. Função pura.

    29/09/2026 (decisão da editoria): o mapa de focos passa a ser de PONTOS pela posição real, e não
    coroplético por UF. O CSV do INPE traz `lat` e `lon` por foco, mas o volume não desenha: em
    28/09 foram **26.873 focos num dia**, e um SVG com vinte e seis mil círculos é ilegível antes de
    ser pesado.

    A escolha é agrupar na renderização, como o handover manda, e o agrupamento é feito **aqui** —
    não no navegador — porque mandar quatro megabytes de CSV para o leitor agrupar seria pior. A
    grade de 0,1° foi medida contra as alternativas sobre o dia real:

        0,05° -> 4.195 células     0,1° -> 3.315     0,25° -> 2.238     0,5° -> 1.251

    0,1° (~11 km) guarda o desenho do arco do desmatamento e do cerrado baiano e cabe em ~70 KB.
    O dado bruto continua no INPE, e a contagem por UF continua no arquivo de sinais: nada do que
    já existia foi substituído por esta agregação.

    O que NÃO se faz aqui: escala de intensidade por foco. O CSV traz `frp` e `risco_fogo`, e a
    editoria foi explícita — não introduzir escala que o dado não sustente foco a foco. O que o
    ponto diz é **quantos focos naquele pedaço de mapa**, e nada mais."""
    import csv
    import io
    linhas = csv.DictReader(io.StringIO(texto))
    celulas = {}
    for linha in linhas:
        try:
            la = float(str(linha.get("lat") or linha.get("latitude") or "").strip())
            lo = float(str(linha.get("lon") or linha.get("longitude") or "").strip())
        except (TypeError, ValueError):
            continue
        if not (-35 <= la <= 6 and -75 <= lo <= -32):   # fora do Brasil não entra
            continue
        chave = (round(la / passo) * passo, round(lo / passo) * passo)
        celulas[chave] = celulas.get(chave, 0) + 1
    return sorted(([round(la, 3), round(lo, 3), n] for (la, lo), n in celulas.items()),
                  key=lambda c: (-c[2], c[0], c[1]))


def escolher_csv_focos(html_indice: str) -> str:
    """Nome do CSV diário mais recente listado no diretório do INPE (focos_diario_br_AAAAMMDD.csv). Função pura."""
    nomes = re.findall(r'focos_diario_br_(\d{8})\.csv', html_indice or "")
    return f"focos_diario_br_{max(nomes)}.csv" if nomes else ""


# ---------------------------------------------------------------------------
# FOCOS PELO SATÉLITE DE REFERÊNCIA (HANDOVER_MONITOR_DE_RISCOS §6a, 16/10/2026) → data/focos_referencia.json
# O CSV diário traz a detecção de todos os satélites; o mesmo fogo aparece em vários (15/10/2026:
# 35.850 linhas, 569 do AQUA_M-T). Comparar dias e anos só faz sentido pelo satélite de referência
# do INPE, que é o que o arquivo anual de referência traz. Bioma e município vêm da fonte; terra
# indígena e unidade de conservação NÃO vêm (sondado em 16/10) e não são estimados.
# ---------------------------------------------------------------------------
SATELITE_REFERENCIA = "AQUA_M-T"
FOCOS_DIAS_SERIE = 400        # cobre o mesmo dia do ano anterior
FOCOS_DIAS_MUNICIPIO = 30
FOCOS_ANUAL_REF = "https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/anual/Brasil_sat_ref/focos_br_ref_{ano}.zip"


def resumo_focos_ref(texto: str, filtrar_satelite: bool = True) -> dict:
    """{dia ISO: {total, uf, bioma, municipio}} só do satélite de referência. Função pura.

    O CSV diário traz `satelite`, `data_hora_gmt` e `municipio_id`; o anual de referência já vem
    filtrado e traz `data_pas` e o nome do município, sem código — por isso `municipio` só existe
    para o diário. O dia é o do horário GMT, como o INPE o publica."""
    import csv
    import io
    saida = {}
    for linha in csv.DictReader(io.StringIO(texto or "")):
        if filtrar_satelite and (linha.get("satelite") or "").strip() != SATELITE_REFERENCIA:
            continue
        dia = str(linha.get("data_hora_gmt") or linha.get("data_pas") or "").strip()[:10]
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", dia):
            continue
        r = saida.setdefault(dia, {"total": 0, "uf": {}, "bioma": {}, "municipio": {}})
        r["total"] += 1
        uf = NOME_PARA_SIGLA.get((linha.get("estado") or "").strip().upper())
        if uf:
            r["uf"][uf] = r["uf"].get(uf, 0) + 1
        bioma = (linha.get("bioma") or "").strip()
        if bioma:
            r["bioma"][bioma] = r["bioma"].get(bioma, 0) + 1
        mun = (linha.get("municipio_id") or "").strip()
        if mun.isdigit():
            r["municipio"][mun] = r["municipio"].get(mun, 0) + 1
    return saida


def _ano_antes(dia: date) -> date:
    try:
        return dia.replace(year=dia.year - 1)
    except ValueError:                                # 29/02 → 28/02
        return dia.replace(year=dia.year - 1, day=28)


def atualizar_focos_ref(anterior: dict, novos: dict, ultimo_dia: str) -> dict:
    """Junta os dias novos à série guardada, apara as janelas e calcula o resumo do último dia
    completo. Somas e contagens só; dia sem arquivo fica fora da soma e o número de dias com dado
    vai junto. Função pura."""
    serie = dict((anterior or {}).get("serie") or {})
    por_mun = dict((anterior or {}).get("municipios_por_dia") or {})
    for dia, r in (novos or {}).items():
        serie[dia] = {"total": r["total"], "uf": r["uf"], "bioma": r["bioma"]}
        if r.get("municipio"):
            por_mun[dia] = r["municipio"]
    fim = date.fromisoformat(ultimo_dia)
    serie = {d: v for d, v in sorted(serie.items()) if 0 <= (fim - date.fromisoformat(d)).days < FOCOS_DIAS_SERIE}
    por_mun = {d: v for d, v in sorted(por_mun.items()) if 0 <= (fim - date.fromisoformat(d)).days < FOCOS_DIAS_MUNICIPIO}
    janela = [d for d in serie if (fim - date.fromisoformat(d)).days < FOCOS_DIAS_MUNICIPIO]
    mes = [d for d in serie if d[:7] == ultimo_dia[:7]]
    ano_antes = _ano_antes(fim).isoformat()
    acumulado = {}
    for m in por_mun.values():
        for k, n in m.items():
            acumulado[k] = acumulado.get(k, 0) + n
    return {
        "serie": serie, "municipios_por_dia": por_mun,
        "resumo": {
            "ultimo_dia": ultimo_dia,
            "dia": serie.get(ultimo_dia),
            "mesmo_dia_ano_anterior": {"dia": ano_antes, "total": serie[ano_antes]["total"]} if ano_antes in serie else None,
            "mes": {"total": sum(serie[d]["total"] for d in mes), "dias_com_dado": len(mes)},
            "ultimos_30_dias": {"total": sum(serie[d]["total"] for d in janela), "dias_com_dado": len(janela),
                                "por_dia": [[d, serie[d]["total"]] for d in janela]},
            "municipios_30_dias": dict(sorted(acumulado.items())),
        },
    }


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


def dist_km(a, b):
    """Distância plana em km entre (lat, lon): basta para tetos de metros a dezenas de km (sem
    trigonometria esférica: a 30 km o erro do achatamento é menor que a resolução do monitor)."""
    dy = (a[0] - b[0]) * 111.0
    dx = (a[1] - b[1]) * 111.0 * math.cos(math.radians((a[0] + b[0]) / 2))
    return math.hypot(dx, dy)


def parse_openaq_locais(dados, por_uf_capital: dict) -> dict:
    """Lê as estações brasileiras do OpenAQ v3 e devolve {UF: {...}} só das que ficam NA CAPITAL.

    O OpenAQ agrega redes oficiais (CETESB, INEA, FEAM e outras) e a rede de origem tem de ser
    creditada junto — ela vem em `provider`/`owner` e é guardada. A seleção é pela coordenada mais
    próxima da capital, com teto de 30 km: monitor a 200 km da capital medindo outra cidade não é
    "medição na capital", e aceitar por proximidade folgada produziria crédito falso. Função pura."""
    itens = (dados or {}).get("results") if isinstance(dados, dict) else dados
    melhor = {}
    for loc in itens or []:
        if not isinstance(loc, dict):
            continue
        coord = loc.get("coordinates") or {}
        lat, lon = coord.get("latitude"), coord.get("longitude")
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            continue
        params = [p.get("name") for p in (loc.get("sensors") or []) if isinstance(p, dict)]
        if not any("pm25" in str(p).replace("_", "").lower() or "pm2.5" in str(p).lower()
                   for p in params + [s.get("parameter", {}).get("name") if isinstance(s, dict) else None
                                      for s in (loc.get("sensors") or [])]):
            continue                                  # sem PM2,5 o monitor não serve a esta figura
        for uf, cap in por_uf_capital.items():
            d = dist_km((lat, lon), (cap["lat"], cap["lon"]))
            if d > OPENAQ_RAIO_KM:
                continue
            atual = melhor.get(uf)
            if atual and atual["distancia_km"] <= d:
                continue
            melhor[uf] = {
                "id": loc.get("id"), "nome": loc.get("name"),
                "rede_de_origem": (loc.get("provider") or {}).get("name") if isinstance(loc.get("provider"), dict) else loc.get("provider"),
                "distancia_km": round(d, 1),
                "coordenada": {"lat": lat, "lon": lon},
                "natureza": NATUREZA_MEDICAO,
            }
    return melhor


# ---------------------------------------------------------------------------
# AR MEDIDO POR ESTAÇÃO (HANDOVER_MONITORAR, 16/10/2026) → data/ar_medido.json
# Três fontes, uma régua só de índice: o IQAr (CONAMA 506/2024) vem PRONTO do MMA/MonitorAr,
# calculado pelo órgão, e nunca é recalculado aqui. OpenAQ dá a concentração (PM2,5, µg/m³) das
# MESMAS estações oficiais, casadas por coordenada ou nome. IPAM/RedeAr dá PM2,5 de sensores de
# baixo custo: concentração, nunca índice. Leitura com mais de VALIDADE_HORAS_SINAL vira lacuna.
# ---------------------------------------------------------------------------
NATUREZA_SENSOR = "sensor de baixo custo"
AR_CASAMENTO_KM = 0.3      # estação MMA ↔ local OpenAQ: mesma estação a até 300 m
FUSO_BR = ZoneInfo("America/Sao_Paulo")
AR_FONTES = {
    "monitorar": {
        "orgao": "MMA · MonitorAr (redes estaduais)", "url_publica": "https://monitorar.mma.gov.br/",
        "endpoint": "https://monitorar-backend.mma.gov.br/v1/estacao/todas",
        "natureza": NATUREZA_MEDICAO,
        "papel": "IQAr por estação oficial, calculado pelo órgão (CONAMA 506/2024); hora da fonte "
                 "lida como horário de Brasília",
    },
    "openaq": {
        "orgao": "OpenAQ (redes de origem)", "url_publica": "https://openaq.org/",
        # A rota por parâmetro ignora `iso` (sondado em 16/10: 21.371 locais do mundo); a por local
        # é chamada só para os monitores de referência brasileiros com PM2,5 recente.
        "endpoint": "https://api.openaq.org/v3/locations/{id}/latest",
        "natureza": NATUREZA_MEDICAO,
        "papel": "PM2,5 em µg/m³ da última medição publicada da mesma estação oficial",
    },
    "redear": {
        "orgao": "IPAM/RedeAr", "url_publica": "https://redear.org.br/",
        # O host de produção (api.) respondeu em 16/10 com leituras de julho e sensores de teste;
        # o de homologação traz o código IBGE e leituras do dia. O host usado fica no dado.
        "endpoint": "https://hmg.api.redear.org.br/v1/sensors",
        "natureza": NATUREZA_SENSOR,
        "papel": "PM2,5 e PM10 em µg/m³ da leitura mais recente (média dos dois canais do sensor "
                 "ótico, correção atmosférica `_env` da fonte); hora da fonte sem fuso declarado; "
                 "não é estação regulatória e não gera IQAr",
    },
}


def _idade_h(quando: datetime, agora_dt: datetime):
    return (agora_dt - quando).total_seconds() / 3600 if quando else None


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def parse_monitorar(dados, agora_dt: datetime) -> list:
    """Estações do MonitorAr com o IQAr vigente como o órgão publica. Função pura.

    `dtMedicao` vem sem fuso ("2025-06-16 20:00") e é lida como horário de Brasília. Medição com
    mais de VALIDADE_HORAS_SINAL horas fica como lacuna (`iqar: null` + motivo): nunca valor velho
    como atual."""
    saida = []
    for e in dados if isinstance(dados, list) else []:
        mun = e.get("municipio") if isinstance(e, dict) else None
        if not isinstance(mun, dict):
            continue
        atual = e.get("indiceQualidadeArAtual") or {}
        med = atual.get("medicao") or {}
        quando = None
        try:
            quando = datetime.strptime(str(med.get("dtMedicao")), "%Y-%m-%d %H:%M").replace(tzinfo=FUSO_BR)
        except ValueError:
            pass
        idade = _idade_h(quando, agora_dt)
        valor = _num(med.get("indiceQualidadeAr"))
        item = {
            "id": e.get("idEstacao"), "nome": e.get("noEstacao"), "rede": e.get("noFonteDados"),
            "ibge": mun.get("idMunicipio"), "municipio": mun.get("noMunicipio"), "uf": mun.get("sgUf"),
            "lat": _num(e.get("nuLatitude")), "lon": _num(e.get("nuLongitude")),
            "categoria": (e.get("categoriaEstacao") or {}).get("descricao"),
            "sem_informacao_mais_de_tres_dias": e.get("semInfoMaisDeTresDias"),
            "iqar": None, "lacuna": None,
        }
        if valor is None or quando is None:
            item["lacuna"] = "sem IQAr publicado pela fonte"
        elif idade > VALIDADE_HORAS_SINAL:
            item["lacuna"] = f"última medição da fonte com mais de {VALIDADE_HORAS_SINAL} h ({quando:%d/%m/%Y %H:%M})"
        else:
            item["iqar"] = {"valor": valor, "classificacao": (atual.get("classificacaoIqAr") or {}).get("noClassificacao"),
                            "poluente": (atual.get("poluente") or {}).get("noPoluente"),
                            "medido_em": quando.isoformat()}
        saida.append(item)
    return saida


def parse_redear(dados, agora_dt: datetime) -> list:
    """Sensores da RedeAr com PM2,5/PM10 da leitura mais recente. Função pura. Nunca AQI."""
    def media(leitura, campo):
        vals = [v for v in (_num(leitura.get(f"pms{c}_{campo}_env")) for c in (1, 2)) if v is not None and v >= 0]
        return round(sum(vals) / len(vals), 1) if vals else None

    saida = []
    for s in dados if isinstance(dados, list) else []:
        if not isinstance(s, dict) or not s.get("geocode_mun"):
            continue                                  # sem município IBGE: sensor de teste ou sem lugar
        coord = ((s.get("gps") or {}).get("coordinates") or [None, None])
        leituras = sorted((x for x in s.get("readings") or [] if isinstance(x, dict) and x.get("datetime")),
                          key=lambda x: x["datetime"], reverse=True)
        item = {"id": s.get("sensor_id"), "nome": s.get("name"), "fonte": s.get("source"),
                "ibge": s.get("geocode_mun"), "municipio": s.get("municipio"),
                "uf_ibge": s.get("geocode_uf"), "bioma": s.get("bioma"),
                "lat": _num(coord[1]), "lon": _num(coord[0]), "pm25": None, "lacuna": None}
        quando = None
        if leituras:
            try:
                quando = datetime.fromisoformat(leituras[0]["datetime"][:19]).replace(tzinfo=FUSO_BR)
            except ValueError:
                pass
        if quando is None:
            item["lacuna"] = "sem leitura publicada pela fonte"
        elif _idade_h(quando, agora_dt) > VALIDADE_HORAS_SINAL:
            item["lacuna"] = f"leitura mais recente com mais de {VALIDADE_HORAS_SINAL} h ({quando:%d/%m/%Y %H:%M})"
        elif media(leituras[0], "pm2_5") is None:
            item["lacuna"] = "leitura sem PM2,5"
        else:
            item["pm25"] = {"valor": media(leituras[0], "pm2_5"), "pm10": media(leituras[0], "pm10"),
                            "unidade": "µg/m³", "lido_em": leituras[0]["datetime"][:19]}
        saida.append(item)
    return saida


def locais_openaq_pm25(locais: list, agora_dt: datetime) -> dict:
    """{id do local: ids dos sensores de PM2,5} dos MONITORES DE REFERÊNCIA (`isMonitor`) com última
    medição a menos de VALIDADE_HORAS_SINAL. Sensor de baixo custo agregado pelo OpenAQ
    (AirGradient, HabitatMap) não é estação oficial e não casa com uma. Função pura."""
    saida = {}
    for loc in locais or []:
        if not isinstance(loc, dict) or loc.get("isMonitor") is not True:
            continue
        try:
            ultima = datetime.fromisoformat(str((loc.get("datetimeLast") or {}).get("utc")).replace("Z", "+00:00"))
        except ValueError:
            continue
        sensores = {x.get("id") for x in loc.get("sensors") or []
                    if isinstance(x, dict) and (x.get("parameter") or {}).get("name") == "pm25"}
        if sensores and _idade_h(ultima, agora_dt) <= VALIDADE_HORAS_SINAL:
            saida[loc.get("id")] = sensores
    return saida


def casar_openaq(estacoes: list, locais: list, ultimas: list, agora_dt: datetime) -> int:
    """Pendura em cada estação MMA o PM2,5 do local OpenAQ que é a MESMA estação: a até 300 m, ou
    com o mesmo nome a até OPENAQ_RAIO_KM. Sem par, a estação diz que a fonte de concentrações não
    tem o dado. Devolve quantas casaram. Função pura (altera só as estações recebidas)."""
    por_local = {u.get("locationsId"): u for u in ultimas or []
                 if isinstance(u, dict) and _num(u.get("value")) is not None}
    pontos = []
    for loc in locais or []:
        c = (loc or {}).get("coordinates") or {}
        if loc.get("id") in por_local and _num(c.get("latitude")) is not None:
            pontos.append((loc, (c["latitude"], c["longitude"]), normalizar_nome(str(loc.get("name") or ""))))
    casadas = 0
    for e in estacoes:
        e["pm25_openaq"] = None
        if e["lat"] is None or e["lon"] is None:
            continue
        nome = normalizar_nome(str(e.get("nome") or ""))
        par = None
        for loc, xy, nome_loc in pontos:
            d = dist_km((e["lat"], e["lon"]), xy)
            if d <= AR_CASAMENTO_KM or (nome and nome == nome_loc and d <= OPENAQ_RAIO_KM):
                par = (d, loc) if par is None or d < par[0] else par
        if not par:
            continue
        u = por_local[par[1]["id"]]
        quando = (u.get("datetime") or {}).get("utc")
        try:
            idade = _idade_h(datetime.fromisoformat(str(quando).replace("Z", "+00:00")), agora_dt)
        except ValueError:
            idade = None
        if idade is None or idade > VALIDADE_HORAS_SINAL:
            continue
        e["pm25_openaq"] = {"valor": round(_num(u["value"]), 1), "unidade": "µg/m³", "medido_em": quando,
                            "local_openaq": par[1]["id"], "distancia_m": round(par[0] * 1000)}
        casadas += 1
    return casadas


# A rota devolve o valor como TEXTO, e três formas aparecem: "28.8" (número limpo), "29.6*"
# (número com asterisco) e "*" sozinho. As três são coisas diferentes e o projeto não pode
# confundi-las — zero, ausência de dado e dado não divulgado são distintos.
#
# O que o asterisco SIGNIFICA não está declarado em nenhum lugar da resposta, e não vou afirmar.
# Ele é registrado como o que é: uma marca que a fonte aplicou ao valor. Quem publicar o número
# publica a marca junto.
PAD_VALOR_INMET = re.compile(r"^\s*(-?\d+(?:[.,]\d+)?)\s*(\*?)\s*$")


def _valor_inmet(bruto) -> tuple:
    """(número, marcado_pela_fonte) ou (None, False) quando a fonte não divulgou. Função pura."""
    t = str(bruto if bruto is not None else "").strip()
    if not t or t == "*":
        return None, False
    m = PAD_VALOR_INMET.match(t)
    if not m:
        return None, False
    return float(m.group(1).replace(",", ".")), bool(m.group(2))


def parse_condicao_capitais(dados, por_uf_capital: dict, data_iso: str) -> dict:
    """{UF: {tmax, tmin, umin_pct, pmax_mm, marcado_pela_fonte, data}} para as capitais com valor.

    Três coisas MEDIDAS em 26/09/2026 que este leitor trata explicitamente:
      • os nomes vêm em MAIÚSCULAS e sem acento — menos "MACEIÓ", que vem acentuado. A fonte é
        inconsistente consigo mesma, então o casamento normaliza dos dois lados.
      • **Brasília aparece DUAS vezes** (28 registros para 27 capitais). Nos dados de 26/09 as duas
        linhas são idênticas, e nesse caso a duplicata é inofensiva. Se algum dia divergirem, a
        capital é RECUSADA: duas medições diferentes para o mesmo dia e o mesmo lugar não se
        resolvem escolhendo uma.
      • seis das 28 linhas traziam `*` em vez de número. Isso é "não divulgado", nunca zero, e a
        capital simplesmente não entra — a ausência fica como ausência.

    Função pura."""
    por_nome = {}
    for uf, cap in (por_uf_capital or {}).items():
        por_nome[normalizar_nome(cap["nome"])] = uf
    vistos, saida, conflitos = {}, {}, []
    for r in dados or []:
        nome = normalizar_nome(str((r or {}).get("CAPITAL") or ""))
        uf = por_nome.get(nome)
        if not uf:
            continue
        tmax, marca_max = _valor_inmet(r.get("TMAX18"))
        tmin, marca_min = _valor_inmet(r.get("TMIN18"))
        if tmax is None and tmin is None:
            continue
        umin, _ = _valor_inmet(r.get("UMIN18"))
        pmax, _ = _valor_inmet(r.get("PMAX12"))
        reg = {"tmax": tmax, "tmin": tmin, "umin_pct": umin, "pmax_mm": pmax,
               "marcado_pela_fonte": bool(marca_max or marca_min), "data": data_iso}
        anterior = vistos.get(uf)
        if anterior is not None and anterior != reg:
            conflitos.append(uf)
            continue
        vistos[uf] = reg
        saida[uf] = reg
    for uf in conflitos:                 # duas linhas divergentes: nenhuma das duas serve
        saida.pop(uf, None)
    return saida


def parse_estacoes_inmet(dados, por_uf_capital: dict) -> dict:
    """Escolhe a estação automática OPERANTE mais próxima de cada capital e devolve {UF: {...}}.

    Duas coisas medidas em 24/09/2026 que este código registra para ninguém repetir:
      • `FL_CAPITAL` NÃO serve: vale "N" em 561 estações e nulo em 112, e "S" em nenhuma. Campo
        quebrado na fonte, não indicador de capital.
      • casar pelo nome da cidade perde 5 capitais, porque a estação se chama "SAO PAULO -
        MIRANTE", "BELO HORIZONTE - PAMPULHA", e Fortaleza não tem estação com o nome da cidade.
    Por isso a escolha é por COORDENADA, com teto, e `CD_SITUACAO` tem de ser "Operante": estação
    em pane devolveria série vazia que pareceria ausência de calor. Função pura."""
    melhor = {}
    for e in dados or []:
        if not isinstance(e, dict) or str(e.get("CD_SITUACAO", "")).strip() != "Operante":
            continue
        try:
            lat, lon = float(e["VL_LATITUDE"]), float(e["VL_LONGITUDE"])
        except (KeyError, TypeError, ValueError):
            continue
        uf = str(e.get("SG_ESTADO") or "").strip().upper()
        cap = por_uf_capital.get(uf)
        if not cap:
            continue
        d = dist_km((lat, lon), (cap["lat"], cap["lon"]))
        if d > INMET_RAIO_KM:
            continue
        atual = melhor.get(uf)
        if atual and atual["distancia_km"] <= d:
            continue
        melhor[uf] = {"codigo": e.get("CD_ESTACAO"), "nome": e.get("DC_NOME"),
                      "situacao": e.get("CD_SITUACAO"), "distancia_km": round(d, 1),
                      "coordenada": {"lat": lat, "lon": lon}, "natureza": NATUREZA_MEDICAO}
    return melhor


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


# ---------------------------------------------------------------------------
# MANCHAS DO MONITOR DE SECAS (HANDOVER_MONITOR_DE_RISCOS §6b, 16/10/2026) → data/secas_manchas.json
# A API da ANA só dá tabela por UF e PNG. O shapefile mensal está no repositório público de arquivos
# do Monitor (S3 da ANA), com o nome que o próprio aplicativo monta: `uploads/mapas/<mês><ano>.zip`
# (sondado: `setembro2026.zip`, 15,8 MB, publicado em 16/10/2026). Lido sem dependência nova: o
# formato .shp/.dbf é público (ESRI, 1998) e só se usa polígono e um campo de texto.
# ---------------------------------------------------------------------------
SECAS_ZIP = "https://ana-monitor-secas-files.s3.sa-east-1.amazonaws.com/uploads/mapas/{mes}{ano}.zip"
SECAS_MESES = ["janeiro", "fevereiro", "marco", "abril", "maio", "junho", "julho", "agosto",
               "setembro", "outubro", "novembro", "dezembro"]
SECAS_TOLERANCIA = 0.02     # grau (~2 km): Douglas-Peucker por anel; alvo ≤ 150 kB


def ler_poligonos_shp(shp: bytes, dbf: bytes, campo: str) -> list:
    """[(valor do campo, [anéis [[lon, lat], ...]])] de um .shp de polígonos com o seu .dbf. Função pura."""
    import struct
    n_reg, cab, tam = struct.unpack("<IHH", dbf[4:12])
    campos, pos, desloc = [], 32, 1
    while dbf[pos] != 0x0D:
        nome = dbf[pos:pos + 11].split(b"\0")[0].decode("latin-1")
        campos.append((nome, desloc, dbf[pos + 16]))
        desloc += dbf[pos + 16]
        pos += 32
    alvo = next((c for c in campos if c[0].lower() == campo.lower()), None)
    valores = [dbf[cab + i * tam + alvo[1]: cab + i * tam + alvo[1] + alvo[2]].decode("latin-1").strip()
               if alvo else None for i in range(n_reg)]
    saida, pos = [], 100
    while pos + 8 <= len(shp):
        n, tam_reg = struct.unpack(">ii", shp[pos:pos + 8])
        corpo = shp[pos + 8: pos + 8 + tam_reg * 2]
        pos += 8 + tam_reg * 2
        if struct.unpack("<i", corpo[:4])[0] not in (5, 15, 25):
            continue
        n_partes, n_pontos = struct.unpack("<ii", corpo[36:44])
        partes = list(struct.unpack(f"<{n_partes}i", corpo[44:44 + 4 * n_partes])) + [n_pontos]
        xy = struct.unpack(f"<{2 * n_pontos}d", corpo[44 + 4 * n_partes: 44 + 4 * n_partes + 16 * n_pontos])
        aneis = [[[xy[2 * k], xy[2 * k + 1]] for k in range(partes[j], partes[j + 1])] for j in range(n_partes)]
        saida.append((valores[n - 1] if 0 < n <= len(valores) else None, aneis))
    return saida


def simplificar_anel(anel: list, tol: float) -> list:
    """Douglas-Peucker iterativo; mantém primeiro e último ponto, arredonda a 3 casas. Função pura."""
    if len(anel) < 5:
        return [[round(x, 3), round(y, 3)] for x, y in anel]
    manter, pilha = {0, len(anel) - 1}, [(0, len(anel) - 1)]
    while pilha:
        a, b = pilha.pop()
        (x1, y1), (x2, y2) = anel[a], anel[b]
        dx, dy = x2 - x1, y2 - y1
        norma = math.hypot(dx, dy) or 1e-12
        idx, dmax = None, tol
        for k in range(a + 1, b):
            d = abs(dy * (anel[k][0] - x1) - dx * (anel[k][1] - y1)) / norma if (dx or dy) else math.hypot(anel[k][0] - x1, anel[k][1] - y1)
            if d > dmax:
                idx, dmax = k, d
        if idx is not None:
            manter.add(idx)
            pilha += [(a, idx), (idx, b)]
    return [[round(anel[k][0], 3), round(anel[k][1], 3)] for k in sorted(manter)]


def _area_assinada(anel: list) -> float:
    return sum(anel[i][0] * anel[i + 1][1] - anel[i + 1][0] * anel[i][1] for i in range(len(anel) - 1)) / 2


def _dentro(p: list, anel: list) -> bool:
    dentro, j = False, len(anel) - 1
    for i in range(len(anel)):
        (xi, yi), (xj, yj) = anel[i], anel[j]
        if (yi > p[1]) != (yj > p[1]) and p[0] < (xj - xi) * (p[1] - yi) / ((yj - yi) or 1e-12) + xi:
            dentro = not dentro
        j = i
    return dentro


def manchas_de_seca(poligonos: list, tol: float = SECAS_TOLERANCIA) -> list:
    """Features GeoJSON (MultiPolygon) por categoria, anéis simplificados. Como no shapefile, anel
    horário é externo e anti-horário é buraco; o buraco vai para o externo que o contém. Anel que cai
    abaixo de 4 pontos sai. Categoria: `s0`…`s4` → S0…S4; outro código fica só como veio. Função pura."""
    feats = []
    for codigo, aneis in poligonos:
        simples = [r for r in (simplificar_anel(a, tol) for a in aneis) if len(r) >= 4]
        externos = [[r] for r in simples if _area_assinada(r) < 0]
        for r in simples:
            if _area_assinada(r) >= 0:
                dono = next((p for p in externos if _dentro(r[0], p[0])), None)
                if dono:
                    dono.append(r)
        if not externos:
            continue
        cod = (codigo or "").strip().lower()
        feats.append({"type": "Feature",
                      "properties": {"categoria": cod.upper() if re.fullmatch(r"s[0-4]", cod) else None,
                                     "codigo_da_fonte": codigo},
                      "geometry": {"type": "MultiPolygon", "coordinates": externos}})
    return feats


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
        raise RuntimeError("fonte sem endpoint automático — sem acesso automático, lacuna declarada (só entra por --semear, com fonte)")

    # Fonte com credencial declarada: sem a credencial no ambiente, nem tenta a rede. Bater na
    # porta para levar 401 gastaria a fonte e sujaria o log com uma recusa que já é conhecida.
    if fonte.get("credencial") and not credencial_de(chave):
        raise CredencialAusente(
            f"{fonte['credencial']} ausente no ambiente — camada de medição fica em lacuna declarada")

    if chave == "openaq":
        capitais = {c["uf"]: c for c in resolver_capitais()}
        bruto = _buscar_registrado(chave, fonte["endpoint"],
                                   extra={"X-API-Key": credencial_de(chave)})
        _AR_MEDIDO["openaq_locais"] = (json.loads(bruto) or {}).get("results") or []
        locais = parse_openaq_locais({"results": _AR_MEDIDO["openaq_locais"]}, capitais)
        if not locais:
            raise ValueError("OpenAQ respondeu sem monitor de PM2,5 a menos de "
                             f"{OPENAQ_RAIO_KM:.0f} km de nenhuma capital — recusada")
        return ({"por_uf": locais}, f"OpenAQ — {len(locais)} capital(is) com monitor de PM2,5")

    if chave == "inmet_estacoes":
        capitais = {c["uf"]: c for c in resolver_capitais()}
        estacoes = parse_estacoes_inmet(json.loads(_buscar_registrado(chave, fonte["endpoint"])), capitais)
        if not estacoes:
            raise ValueError("lista de estações do INMET sem estação operante a menos de "
                             f"{INMET_RAIO_KM:.0f} km de nenhuma capital — recusada")
        # §233: a MEDIDA, que é o que esta fonte promete no papel declarado. A rota é pública e
        # separada; se ela falhar, a seleção de estações entra sozinha e a medida fica em lacuna —
        # meia leitura declarada é melhor do que nenhuma, e muito melhor do que uma inventada.
        dia = hoje_editorial().isoformat()
        medidas, nota_medida = {}, "sem medida do dia"
        try:
            crus = json.loads(_buscar_registrado(chave, fonte["endpoint_medida"].format(data=dia)))
            medidas = parse_condicao_capitais(crus, capitais, dia)
            nota_medida = f"{len(medidas)} capital(is) com máxima/mínima medidas em {dia}"
        except Exception as e:  # noqa: BLE001 — a seleção de estações não cai por causa da medida
            nota_medida = f"medida do dia não obtida ({type(e).__name__})"
        for uf, m in medidas.items():
            if uf in estacoes:
                estacoes[uf]["medida"] = m
        return ({"por_uf": estacoes},
                f"INMET — {len(estacoes)} estação(ões) automática(s) de capital; {nota_medida}")

    # As duas fontes do Open-Meteo pedem as 27 coordenadas numa chamada só e tratam a resposta
    # posicionalmente; saem antes do GET genérico abaixo.
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
        # 07/10/2026 (handover "Monitor de riscos, parte 1", item 3): a série do RONI deixa de ser
        # cortada. Ela saía em `serie[-160:]`, os últimos 160 trimestres móveis — treze anos, a
        # partir de 2013 —, e a página mostrava isso enquanto o subtítulo dizia "1950 a 2026".
        # Quem precisa dos 1950 é o próprio gráfico: o leitor compara o ciclo em curso com os
        # episódios anteriores, e os maiores da série estão fora da janela de treze anos.
        #
        # O custo foi medido na origem em 07/10/2026: 920 pontos, de DJF/1950 a JAS/2026, 49 KB de
        # JSON. `data/sinais_risco.json` passa de 146 KB para cerca de 187 KB — longe do teto de
        # 50 MB da trava de tamanho, e abaixo do piso de 1 MB a partir do qual a taxa de
        # crescimento é conferida (`scripts/consolidar_noite.py`). O ONI segue cortado: ele é apoio
        # técnico, vive na METODOLOGIA e não é figura de página.
        #
        # A página já lê o intervalo de anos do dado, então o título passa a dizer 1950 sozinho.
        return {"serie": serie}, f"RONI, último trimestre {ultimo['trimestre']}/{ultimo['ano']}"
    if chave == "noaa_nino34_mensal":
        serie = parse_nino34_mensal(bruto)
        if len(serie) < 6:
            raise ValueError(f"série mensal Niño 3.4 curta demais ({len(serie)} pontos) — recusada")
        ultimo = serie[-1]
        return {"serie": serie}, f"Niño 3.4 mensal, último mês {ultimo['mes']:02d}/{ultimo['ano']}"
    if chave == "inmet_previsao_capitais":
        lido = parse_previsao_capitais_inmet(json.loads(_buscar_registrado(chave, fonte["endpoint"])))
        if not lido:
            raise ValueError("previsão do INMET sem capital com máxima — recusada")
        return {"por_uf": lido}, f"INMET — previsão para {len(lido)} capital(is)"

    if chave == "cpc_ensodisc":
        lido = parse_ensodisc_cpc(bruto)
        if not lido.get("estado") or not lido.get("emitido_em"):
            raise ValueError("discussão do CPC sem estado de alerta ou sem data de emissão — recusada")
        return lido, f"ENOS: {lido['estado']} (emitida em {lido['emitido_em']})"

    if chave == "iri_plume":
        # A tabela (formato antigo) tem precedência: ela traz os três valores por trimestre.
        # A prosa é o caminho de hoje e só traz a probabilidade de El Niño — melhor que a lacuna,
        # e cada número guarda o trecho de onde saiu.
        plume = parse_plume_iri(bruto) or parse_plume_prosa(bruto)
        if not plume:
            raise ValueError("plume IRI sem trimestres reconhecíveis — recusada")
        return {"trimestres": plume}, f"Plume ENSO, {len(plume)} trimestres"
    if chave == "inpe_fogo":
        nome = escolher_csv_focos(bruto)   # `bruto` é o ÍNDICE do diretório
        if not nome:
            raise ValueError("índice do INPE sem arquivo focos_diario_br_*.csv — recusado")
        csv_focos = _buscar(fonte["endpoint"] + nome)
        focos = parse_focos_inpe(csv_focos)
        if not focos:
            # 29/09/2026: o arquivo do dia corrente nasce **só com cabeçalho** e é preenchido ao
            # longo do dia — medido: 29/09 com 0 focos às 9h, 28/09 com 26.873. Tratar isso como
            # recusa daria falha declarada toda manhã, e tratar como zero seria pior ainda: diria
            # "nenhum foco no Brasil" onde só faltava o arquivo encher. Cai para o dia anterior,
            # UMA vez, e o nome do arquivo (que vai para a figura) diz de que dia é o dado.
            dias = sorted(set(re.findall(r"focos_diario_br_(\d{8})\.csv", bruto or "")))
            if len(dias) >= 2:
                nome = f"focos_diario_br_{dias[-2]}.csv"
                csv_focos = _buscar(fonte["endpoint"] + nome)
                focos = parse_focos_inpe(csv_focos)
        if not focos:
            raise ValueError("CSV de focos sem coluna de UF reconhecível — recusado")
        # 29/09/2026: além da contagem por UF, os PONTOS agregados em grade — é o que o mapa novo
        # desenha. A contagem por UF fica: ela alimenta a lista e o texto, e trocá-la pelos pontos
        # tiraria do leitor de tela o número exato.
        return {"focos_por_uf": focos, "pontos": agregar_focos_em_grade(csv_focos),
                "arquivo": nome}, f"Focos do dia — {nome}"
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
                    "temperatura": None,
                    "temperatura_medida": None, "ar_medido": None} for uf in UFS},
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
    # 16/10/2026: fonte que saiu do catálogo sai do arquivo (Open-Meteo de tempo e de ar, sem
    # figura desde 27/09 e desde o #802); campo que só ela escrevia também.
    for chave in [c for c in registro["fontes"] if c not in FONTES]:
        del registro["fontes"][chave]
    for uf in UFS:
        bloco = registro.setdefault("uf", {}).setdefault(uf, {})
        bloco.pop("qualidade_ar", None)
        for campo in ("risco_projetado", "secas", "avisos_inmet", "fogo", "alertas_cemaden",
                      "temperatura", "temperatura_medida", "ar_medido"):
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
    # 07/10/2026 (A3): o documento e a URL vêm do registro do boletim, com número e mês, e o
    # endereço é o do PDF — a página inicial do Cemaden não é a fonte de uma afirmação datada.
    documento = boletins.get("documento") or (
        f"Boletins nº 1 e {numero} do Painel El Niño 2026-2027" if numero
        else "Painel El Niño 2026-2027")
    url_do_boletim = boletins.get("url") or FONTES["painel_el_nino"]["url_publica"]
    fonte_painel = registro.get("fontes", {}).get("painel_el_nino")
    if isinstance(fonte_painel, dict):
        fonte_painel["documento"] = documento
        fonte_painel["url_publica"] = url_do_boletim
        if boletins.get("horizonte"):
            fonte_painel["horizonte"] = boletins["horizonte"]
        if boletins.get("consultado_em"):
            fonte_painel["consultado_em"] = boletins["consultado_em"]
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
            "url": url_do_boletim,
        }
    registro["fontes"]["painel_el_nino"].update({
        "status": "coletado", "consultado_em": hoje(), "documento": documento,
        "detalhe": "Risco projetado por UF conforme registro curado em data/consist.json, "
                   "derivado da leitura registrada dos boletins do Painel.",
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
        except CredencialAusente as e:
            # Não é falha: é decisão pendente. O status diz isso, e a página mostra lacuna
            # declarada em vez de sugerir que a fonte está fora do ar.
            registro["fontes"][chave].update({"status": "aguardando_credencial", "motivo": str(e)})
            print(f"[aviso] {chave}: {e}")
            continue
        except (ValueError, RuntimeError, json.JSONDecodeError) as e:
            print(f"[aviso] {chave}: resposta recusada ({e}) — registro anterior mantido.")
            continue
        registro["fontes"][chave].update({
            "status": "coletado", "consultado_em": hoje(), "documento": documento,
            "detalhe": fonte["papel"],
        })
        # §233: `update` MERGE, e por isso um `motivo` de rodada anterior sobrevivia à coleta bem
        # sucedida. Visto no arquivo em 26/09/2026: `inmet_estacoes` gravado com
        # `status: "coletado"` E `motivo: "INMET_API_TOKEN ausente — camada de medição fica em
        # lacuna declarada"` ao mesmo tempo. Registro que se contradiz é pior do que registro
        # ausente: quem lesse o `motivo` concluiria o oposto do que a coleta fez. Fonte que voltou
        # a coletar não carrega o motivo de quando não coletava.
        registro["fontes"][chave].pop("motivo", None)
        if not fonte.get("credencial"):
            # Mesma razão: a fonte deixou de exigir chave (§233, porque a rota dela é pública),
            # e o campo antigo continuava no arquivo dizendo que exige.
            registro["fontes"][chave].pop("credencial", None)
        if chave == "noaa_oni":
            registro["enos"]["oni"] = {**payload, "fonte": chave, "documento": documento}
        elif chave == "noaa_roni":
            registro["enos"]["roni"] = {**payload, "fonte": chave, "documento": documento}
        elif chave == "noaa_nino34_mensal":
            registro["enos"]["nino34_mensal"] = {**payload, "fonte": chave, "documento": documento}
        elif chave == "inmet_previsao_capitais":
            for uf, valor in (payload.get("por_uf") or {}).items():
                if uf in registro["uf"]:
                    registro["uf"][uf]["temperatura"] = {**valor, "fonte": chave, "documento": documento}

        elif chave == "cpc_ensodisc":
            # Substitui a leitura humana congelada: agora o estado do ENOS chega sozinho, com a
            # data de emissão do próprio documento, a cada rodada.
            registro["enos"]["prognostico"] = {**payload, "fonte": chave, "documento": documento}

        elif chave == "iri_plume":
            registro["enos"]["probabilidades"] = {**payload, "fonte": chave, "documento": documento}
        # 15/09/2026: INPE, INMET e CEMADEN respondem pelo país inteiro — UF ausente da resposta é ZERO
        # (nenhum foco, aviso ou alerta), não lacuna. Zero ≠ ausência de dado: só a fonte não coletada
        # fica nula (cinza no mapa). Sonda de 15/09: CEMADEN tinha 88 alertas em 6 UFs; as outras 21 eram zero.
        elif chave == "inpe_fogo":
            for uf in UFS:
                registro["uf"][uf]["fogo"] = {"focos_24h": payload["focos_por_uf"].get(uf, 0), "fonte": chave,
                                              "documento": documento, "consultado_em": hoje()}
            # Os pontos vão para arquivo PRÓPRIO: são milhares de células e não cabem no arquivo de
            # sinais, que o navegador carrega inteiro em toda página da seção.
            _PONTOS_FOCOS.update({"pontos": payload.get("pontos") or [],
                                  "arquivo": payload.get("arquivo"),
                                  "por_uf": payload["focos_por_uf"],
                                  "passo_grau": PASSO_GRADE_FOCOS})
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
        # Camada de MEDIÇÃO: guarda a estação/monitor escolhido e a distância até a capital, para
        # que a figura possa dizer ONDE mediu. Sem isso, "medição" viraria um rótulo sem endereço.
        elif chave in ("openaq", "inmet_estacoes"):
            campo = "ar_medido" if chave == "openaq" else "temperatura_medida"
            for uf in UFS:
                lido = payload["por_uf"].get(uf)
                registro["uf"][uf][campo] = ({**lido, "fonte": chave, "documento": documento,
                                              "consultado_em": agora()} if lido else None)
        elif chave == "monitor_secas":
            if payload.get("recurso"):
                registro["fontes"][chave]["recurso"] = payload["recurso"]
            for uf in UFS:
                lido = payload["por_uf"].get(uf)
                registro["uf"][uf]["secas"] = ({**lido, "fonte": chave, "documento": documento, "consultado_em": hoje()}
                                               if lido else None)   # UF que o RPC não devolveu fica nula (lacuna), nunca zero
        print(f"  ✓ {chave}: {documento}")
    return registro


def escrever_json(caminho, obj, compacto: bool = False) -> None:
    """Escrita ATOMICA, com a espera do cadeado do Windows (§221).

    25/09/2026: este coletor nunca foi migrado depois da corrupcao de 21/09/2026, quando um
    processo interrompido no meio de uma gravacao deixou um JSON truncado em `data/`. Os quatro
    arquivos dele — sinais, alertas, clima e consultas — ainda escreviam direto no destino, e o
    de clima e o maior de todos, regravado dezenas de vezes numa varredura nacional: era o mais
    exposto. Mesmo remedio do resto do projeto: temporario ao lado, `os.replace()` no fim, e
    espera curta quando o Windows recusa por cadeado de outro processo.

    `compacto` para o arquivo que a pagina carrega inteiro; indentado para os demais, que sao
    lidos por gente no diff."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    tmp = caminho.with_name(caminho.name + ".tmp" + str(os.getpid()))
    corpo = (json.dumps(obj, ensure_ascii=False, separators=(",", ":")) if compacto
             else json.dumps(obj, ensure_ascii=False, indent=1))
    tmp.write_text(corpo + "\n", encoding="utf-8", newline="\n")
    for tentativa in range(6):
        try:
            os.replace(tmp, caminho)
            return
        except PermissionError:
            if tentativa == 5:
                try:
                    tmp.unlink()
                except OSError:
                    pass
                raise
            time.sleep(0.2 * (tentativa + 1))


def gravar(registro: dict) -> None:
    """Grava o registro em data/sinais_risco.json com indentação de 1 espaço, padrão dos demais arquivos de data/."""
    registro["gerado_em"] = hoje()
    escrever_json(REGISTRO, registro)
    print(f"→ {REGISTRO.relative_to(RAIZ)} gravado.")


def gravar_ar_medido(agora_dt: datetime = None) -> None:
    """Coleta MonitorAr, RedeAr e as últimas medições do OpenAQ e grava data/ar_medido.json.

    Cada fonte falha sozinha: a que não respondeu sai com status e lista vazia (lacuna declarada),
    nunca com a lista da rodada anterior como se fosse de hoje. Se nenhuma respondeu, o arquivo
    anterior fica, com a data dele. Resposta bruta preservada por hash (`preservar_evidencia`)."""
    from coletores_base import preservar_evidencia
    agora_dt = agora_dt or datetime.now(FUSO_BR)
    fontes, dados = {}, {}
    for chave, f in AR_FONTES.items():
        meta = {k: f[k] for k in ("orgao", "url_publica", "endpoint", "natureza", "papel")}
        fontes[chave] = meta
        extra = None
        if chave == "openaq":
            if not credencial_de("openaq"):
                meta["status"] = "aguardando_credencial"
                continue
            extra = {"X-API-Key": credencial_de("openaq")}
        try:
            if chave == "openaq":            # uma chamada por monitor candidato; bruto = as respostas juntas
                if not _AR_MEDIDO.get("openaq_locais"):
                    raise RuntimeError("lista de locais do OpenAQ não lida nesta rodada")
                alvos = locais_openaq_pm25(_AR_MEDIDO.get("openaq_locais"), agora_dt)
                respostas = [json.loads(_buscar_registrado(chave, f["endpoint"].format(id=i), extra=extra))
                             for i in sorted(alvos, key=str)]
                bruto = json.dumps(respostas, ensure_ascii=False)
                dados[chave] = [u for r, i in zip(respostas, sorted(alvos, key=str))
                                for u in (r or {}).get("results") or [] if u.get("sensorsId") in alvos[i]]
            else:
                bruto = _buscar_registrado(chave, f["endpoint"], extra=extra)
                dados[chave] = json.loads(bruto)
            meta.update(status="coletado", consultado_em=agora(),
                        evidencia_sha256=preservar_evidencia(bruto.encode("utf-8"), f["endpoint"], "json", "coletar_sinais_risco.py"))
        except Exception as e:  # noqa: BLE001 — fonte externa: vira lacuna declarada
            meta["status"] = "falha_de_rede"
            print(f"[aviso] ar medido: {chave} falhou ({type(e).__name__}: {str(e)[:120]})")
    if "monitorar" not in dados and "redear" not in dados:
        print("[aviso] ar medido: MonitorAr e RedeAr sem resposta — data/ar_medido.json mantido.")
        return
    estacoes = parse_monitorar(dados.get("monitorar"), agora_dt)
    if "openaq" in dados:
        fontes["openaq"]["estacoes_casadas"] = casar_openaq(
            estacoes, _AR_MEDIDO.get("openaq_locais"), dados["openaq"], agora_dt)
    sensores = parse_redear(dados.get("redear"), agora_dt)
    escrever_json(RAIZ / "data" / "ar_medido.json", {
        "_governanca": ("Ar medido por estação e sensor. IQAr calculado pelo órgão (MMA/MonitorAr, "
                        "CONAMA 506/2024), nunca recalculado aqui; PM2,5 do OpenAQ só para a mesma "
                        "estação oficial; sensores de baixo custo (IPAM/RedeAr) só em concentração, "
                        f"nunca índice. Medição com mais de {VALIDADE_HORAS_SINAL} h é lacuna. Peso "
                        "zero, sinal físico."),
        "gerado_em": agora(), "fontes": fontes, "estacoes": estacoes, "sensores": sensores,
    })
    print(f"→ data/ar_medido.json: {sum(1 for e in estacoes if e['iqar'])}/{len(estacoes)} estação(ões) "
          f"com IQAr, {sum(1 for x in sensores if x['pm25'])}/{len(sensores)} sensor(es) com PM2,5.")


def gravar_secas_manchas() -> None:
    """Baixa o shapefile do mapa mensal mais recente do Monitor de Secas, simplifica e grava
    data/secas_manchas.json. Mês já gravado não é baixado de novo; mês ainda não publicado (404) cai
    para o anterior. O original fica identificado pelo hash no livro de consultas. Falha deixa o
    arquivo anterior, com o mês dele."""
    import io
    import zipfile
    destino = RAIZ / "data" / "secas_manchas.json"
    anterior = json.loads(destino.read_text(encoding="utf-8")) if destino.exists() else {}
    d = hoje_editorial()
    for k in range(3):
        ano, mes = (d.year, d.month - k) if d.month > k else (d.year - 1, d.month - k + 12)
        chave, url = f"{ano}-{mes:02d}", SECAS_ZIP.format(mes=SECAS_MESES[mes - 1], ano=ano)
        if anterior.get("mes") == chave:
            print(f"[secas] mapa de {chave} já gravado — data/secas_manchas.json mantido.")
            return
        try:
            bruto = _buscar(url, binario=True)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue
            print(f"[aviso] secas: HTTP {e.code} em {url} — arquivo anterior mantido.")
            return
        except Exception as e:  # noqa: BLE001 — fonte externa
            print(f"[aviso] secas: {type(e).__name__} em {url} — arquivo anterior mantido.")
            return
        registrar_consulta("monitor_secas", url, bruto)
        z = zipfile.ZipFile(io.BytesIO(bruto))
        nomes = {n.lower(): n for n in z.namelist()}
        shps = [n for n in z.namelist() if n.lower().endswith(".shp") and "/" not in n
                and "impact" not in n.lower() and n[:-4].lower() + ".dbf" in nomes]
        # o pacote traz mais de um shapefile (16/10: `setembro26.shp`, `setembro26_isolado.shp`,
        # `202609_MS_IMPACTOS.shp`, `Estados_monitor/`); o mapa é o que leva o nome do mês
        preferidos = [f"{SECAS_MESES[mes - 1]}{ano % 100:02d}.shp", f"{ano}{mes:02d}_ms.shp"]
        shps.sort(key=lambda n: preferidos.index(n.lower()) if n.lower() in preferidos else len(preferidos))
        for nome in shps:
            polis = ler_poligonos_shp(z.read(nome), z.read(nomes[nome[:-4].lower() + ".dbf"]), "uf_codigo")
            feats = manchas_de_seca(polis)
            if feats and any(p for p, _ in polis):
                break
        else:
            print(f"[aviso] secas: {url} sem polígono de categoria reconhecível — arquivo anterior mantido.")
            return
        escrever_json(destino, {
            "_governanca": ("Manchas do mapa mensal do Monitor de Secas (ANA e parceiros), por categoria, "
                            "como a fonte publica. Geometria simplificada para desenho (Douglas-Peucker, "
                            f"tolerância {SECAS_TOLERANCIA}°, ~2 km): o contorno oficial é o do arquivo "
                            "original, identificado pelo hash no livro de consultas. Peso zero, sinal físico."),
            "gerado_em": hoje(), "consultado_em": agora(), "fonte": "Monitor de Secas — ANA",
            "url_publica": FONTES["monitor_secas"]["url_publica"], "url": url, "arquivo": nome,
            "mes": chave, "tolerancia_graus": SECAS_TOLERANCIA,
            "type": "FeatureCollection", "features": feats,
        }, compacto=True)
        print(f"→ data/secas_manchas.json: mapa de {chave}, {len(feats)} categoria(s), {nome}.")
        return
    print("[aviso] secas: nenhum mapa publicado nos três últimos meses — arquivo anterior mantido.")
def gravar_focos_referencia() -> None:
    """Lê o último dia COMPLETO de focos (o penúltimo arquivo do diretório: o do dia corrente
    nasce vazio e enche ao longo do dia), completa os dias que faltam na janela de 30 e, se faltar
    o mesmo dia do ano anterior, o arquivo anual de referência daquele ano — uma vez, porque o ano
    inteiro fica na série. Cada resposta deixa URL, hora e hash no livro de consultas. Fonte que não
    responde deixa o arquivo anterior, com a data dele."""
    import io
    import zipfile
    destino = RAIZ / "data" / "focos_referencia.json"
    base = FONTES["inpe_fogo"]["endpoint"]
    try:
        indice = _buscar_registrado("inpe_fogo", base)
        dias = sorted(set(re.findall(r"focos_diario_br_(\d{8})\.csv", indice)))
        if len(dias) < 2:
            raise ValueError("diretório sem dia completo")
        ultimo = f"{dias[-2][:4]}-{dias[-2][4:6]}-{dias[-2][6:]}"
        anterior = json.loads(destino.read_text(encoding="utf-8")) if destino.exists() else {}
        guardados = set((anterior.get("serie") or {}))
        fim = date.fromisoformat(ultimo)
        novos = {}
        for d in dias[:-1]:
            iso = f"{d[:4]}-{d[4:6]}-{d[6:]}"
            idade = (fim - date.fromisoformat(iso)).days
            # os dois últimos dias são relidos sempre: o INPE ainda pode completar o arquivo
            if idade < FOCOS_DIAS_MUNICIPIO and (iso not in guardados or idade < 2):
                novos.update(resumo_focos_ref(_buscar_registrado("inpe_fogo", f"{base}focos_diario_br_{d}.csv")))
        ano_antes = _ano_antes(fim)
        if ano_antes.isoformat() not in guardados:
            url = FOCOS_ANUAL_REF.format(ano=ano_antes.year)
            bruto = _buscar(url, binario=True)
            registrar_consulta("inpe_fogo", url, bruto)
            z = zipfile.ZipFile(io.BytesIO(bruto))
            anual = resumo_focos_ref(z.read(z.infolist()[0]).decode("utf-8", "replace"), filtrar_satelite=False)
            novos.update({d: v for d, v in anual.items() if 0 <= (fim - date.fromisoformat(d)).days < FOCOS_DIAS_SERIE})
    except Exception as e:  # noqa: BLE001 — fonte externa: o arquivo anterior fica, com a data dele
        print(f"[aviso] focos de referência: {type(e).__name__}: {str(e)[:160]} — data/focos_referencia.json mantido.")
        return
    novos = {d: v for d, v in novos.items() if d <= ultimo}
    escrever_json(destino, {
        "_governanca": (f"Focos de calor do INPE pelo satélite de referência ({SATELITE_REFERENCIA}), "
                        "por UF, bioma e município (código IBGE), como o INPE publica. Contagem por dia GMT; "
                        "somas de dias com arquivo, com o número de dias. Terra indígena e unidade de "
                        "conservação não vêm na fonte e não são estimadas. Peso zero, sinal físico."),
        "gerado_em": hoje(), "consultado_em": agora(), "fonte": "INPE — Programa Queimadas (BDQueimadas)",
        "url_publica": FONTES["inpe_fogo"]["url_publica"], "satelite_referencia": SATELITE_REFERENCIA,
        **atualizar_focos_ref(anterior, novos, ultimo),
    }, compacto=True)
    print(f"→ data/focos_referencia.json: {ultimo}, {len(novos)} dia(s) lido(s) nesta rodada.")


# ---------------------------------------------------------------------------
# CONSULTA DO MUNICÍPIO NO MONITOR DE RISCOS (HANDOVER_MONITOR_DE_RISCOS §6g, 16/10/2026)
# → data/riscos_municipio/<UF>.json. Junta, por código IBGE, o que os outros arquivos do elo já
# guardam: focos do satélite de referência em 30 dias, avisos do INMET e alertas do CEMADEN em vigor,
# decretos de resposta, a estação oficial de ar e o sensor mais próximos e a capital mais próxima.
# Nada é recalculado aqui; cada bloco diz de que arquivo veio. O plano do município fica no
# `municipios_card.json`, que a consulta já lê — copiar daria duas fontes para o mesmo fato.
# ---------------------------------------------------------------------------
RISCOS_MUNICIPIO = RAIZ / "data" / "riscos_municipio"
RISCOS_DECRETOS_MAX = 3
RISCOS_RAIO_AR_KM = 50.0    # além disso a estação mede outra cidade: o município fica sem bloco de ar


def montar_riscos_municipio(ref: list, focos: dict, vigentes: dict, ar: dict, atos: dict) -> dict:
    """{UF: {"estacoes": [...], "sensores": [...], "municipios": {IBGE: {...}}}}. Função pura.

    Focos ausentes no acumulado de 30 dias são 0 só quando a série tem os 30 dias; com menos, o
    campo vem `None` (não sabemos). Ar: a estação oficial mais próxima COM IQAr vigente e o sensor
    mais próximo COM leitura, até RISCOS_RAIO_AR_KM, cada um com a distância. Aviso, estação e
    sensor vão como índice da lista da UF, para o mesmo aviso não se repetir em centenas de
    municípios. Lista vazia não é gravada no município."""
    resumo = (focos or {}).get("resumo") or {}
    mun30 = resumo.get("municipios_30_dias") or {}
    completo = ((resumo.get("ultimos_30_dias") or {}).get("dias_com_dado") or 0) >= FOCOS_DIAS_MUNICIPIO
    por_mun = (vigentes or {}).get("municipios") or {}
    estacoes = [e for e in (ar or {}).get("estacoes") or [] if e.get("iqar") and e.get("lat") is not None]
    sensores = [s for s in (ar or {}).get("sensores") or [] if s.get("pm25") and s.get("lat") is not None]
    capitais = [m for m in ref if int(m.get("codigo_ibge") or 0) in set(CAPITAL_IBGE.values())]
    decretos = {}
    for ev in (atos or {}).get("eventos") or []:
        decretos.setdefault((normalizar_nome(str(ev.get("nome") or "")), ev.get("uf")), []).append(
            {k: ev.get(k) for k in ("data", "decreto", "url")})

    def mais_proximo(lista, ponto):
        return min(((dist_km(ponto, (x["lat"], x["lon"])), i) for i, x in enumerate(lista)), default=None)

    saida = {}
    for m in ref:
        cod, uf = str(m.get("codigo_ibge") or ""), m.get("uf")
        if not cod or uf not in UFS or m.get("lat") is None:
            continue
        bloco = saida.setdefault(uf, {"avisos_inmet": [], "estacoes": [], "sensores": [], "municipios": {}})
        ponto, v = (m["lat"], m["lon"]), por_mun.get(cod) or {}
        item = {"nome": m["nome"], "focos_30_dias": mun30.get(cod, 0 if completo else None)}
        for a in v.get("inmet") or []:
            aviso = {k: a.get(k) for k in ("tipo", "severidade", "inicio", "fim")}
            if aviso not in bloco["avisos_inmet"]:
                bloco["avisos_inmet"].append(aviso)
            item.setdefault("avisos_inmet", []).append(bloco["avisos_inmet"].index(aviso))
        if v.get("cemaden"):
            item["alertas_cemaden"] = v["cemaden"]
        dec = sorted(decretos.get((normalizar_nome(m["nome"]), uf)) or [],
                     key=lambda d: "".join(reversed(str(d.get("data") or "").split("/"))), reverse=True)
        if dec:
            item["decretos"], item["decretos_no_ciclo"] = dec[:RISCOS_DECRETOS_MAX], len(dec)
        for chave, lista, campos in (("ar_estacao", estacoes, ("nome", "municipio", "uf", "rede", "iqar")),
                                     ("ar_sensor", sensores, ("nome", "municipio", "fonte", "pm25"))):
            perto = mais_proximo(lista, ponto)
            if perto and perto[0] <= RISCOS_RAIO_AR_KM:
                destino = bloco["estacoes" if chave == "ar_estacao" else "sensores"]
                registro = {k: lista[perto[1]].get(k) for k in campos}
                if registro not in destino:
                    destino.append(registro)
                item[chave] = {"indice": destino.index(registro), "distancia_km": round(perto[0])}
        c = mais_proximo(capitais, ponto)
        if c:
            item["capital_mais_proxima"] = {"uf": capitais[c[1]]["uf"], "nome": capitais[c[1]]["nome"],
                                            "distancia_km": round(c[0])}
        bloco["municipios"][cod] = item
    return saida


def gravar_riscos_municipio() -> None:
    """Lê os arquivos que o elo acabou de gravar e escreve um arquivo por UF. Arquivo de entrada
    ausente vira bloco ausente, nunca zero; a data de cada entrada vai no cabeçalho."""
    def abrir(nome):
        p = RAIZ / "data" / nome
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    focos, vigentes, ar, atos = (abrir("focos_referencia.json"), abrir("alertas/vigentes.json"),
                                 abrir("ar_medido.json"), abrir("atos_resposta.json"))
    ref = json.loads(MUNICIPIOS_REF.read_text(encoding="utf-8"))
    por_uf = montar_riscos_municipio(ref, focos, vigentes, ar, atos)
    cabeca = {
        "_governanca": ("Consulta do município no Monitor de riscos: junta, por código IBGE, o que os "
                        "arquivos de origem guardam. Nada é recalculado; o plano do município está em "
                        "municipios_card.json. Peso zero, sinal físico."),
        "gerado_em": hoje(),
        "origens": {"focos": {"arquivo": "focos_referencia.json", "ultimo_dia": (focos.get("resumo") or {}).get("ultimo_dia"),
                              "dias_com_dado": ((focos.get("resumo") or {}).get("ultimos_30_dias") or {}).get("dias_com_dado")},
                    "avisos_e_alertas": {"arquivo": "alertas/vigentes.json", "gerado_em": vigentes.get("gerado_em")},
                    "ar": {"arquivo": "ar_medido.json", "gerado_em": ar.get("gerado_em")},
                    "decretos": {"arquivo": "atos_resposta.json", "atualizado_em": atos.get("atualizado_em")}},
    }
    for uf, bloco in sorted(por_uf.items()):
        escrever_json(RISCOS_MUNICIPIO / f"{uf}.json", {**cabeca, "uf": uf, **bloco}, compacto=True)
    print(f"→ data/riscos_municipio/: {len(por_uf)} UF(s), {sum(len(v) for v in por_uf.values())} município(s).")


def gravar_pontos_de_foco() -> None:
    """Grava data/focos_pontos.json com os focos agregados em grade.

    Só grava quando a coleta do INPE respondeu nesta rodada: reescrever com lista vazia mostraria
    "nenhum foco" onde houve "não perguntamos", que é a distinção que este projeto existe para
    manter. Quando o INPE não responde, o arquivo anterior fica, com a data dele — e a figura dirá
    de quando é."""
    if not _PONTOS_FOCOS.get("pontos"):
        print("[aviso] focos: INPE não respondeu nesta rodada — data/focos_pontos.json mantido.")
        return
    escrever_json(RAIZ / "data" / "focos_pontos.json", {
        "_governanca": ("Focos de calor do INPE agregados numa grade de "
                        f"{PASSO_GRADE_FOCOS}° (~11 km) para desenho. Cada item é [lat, lon, "
                        "focos na célula]. Peso zero, sinal físico. O agrupamento é de DESENHO: o "
                        "dado bruto, foco a foco, é do INPE e não é redistribuído aqui. Não há "
                        "escala de intensidade — o ponto diz quantos focos há na célula, e nada "
                        "mais."),
        "gerado_em": hoje(), "fonte": "INPE — Programa Queimadas",
        "arquivo_de_origem": _PONTOS_FOCOS.get("arquivo"),
        "passo_grau": _PONTOS_FOCOS.get("passo_grau", PASSO_GRADE_FOCOS),
        "celulas": len(_PONTOS_FOCOS["pontos"]),
        # A contagem por UF sai do MESMO arquivo do INPE que gerou os pontos. Ela também está em
        # sinais_risco.json, mas ali pode ser de outra rodada — e mapa e lista discordando na mesma
        # figura é o tipo de defeito que ninguém percebe até alguém somar.
        "por_uf": _PONTOS_FOCOS.get("por_uf") or {},
        "focos": sum(p[2] for p in _PONTOS_FOCOS["pontos"]),
        "pontos": _PONTOS_FOCOS["pontos"]})
    print(f"→ data/focos_pontos.json: {len(_PONTOS_FOCOS['pontos'])} célula(s), "
          f"{sum(p[2] for p in _PONTOS_FOCOS['pontos'])} foco(s).")


def municipios_por_uf_e_grau(por_municipio: dict) -> dict:
    """{UF: {grau: municípios}} dos avisos do INMET em vigor. Função pura."""
    saida = {}
    for v in por_municipio.values():
        for grau in sorted({a.get("severidade") for a in v.get("inmet") or [] if a.get("severidade")}):
            d = saida.setdefault(v.get("uf"), {})
            d[grau] = d.get(grau, 0) + 1
    return dict(sorted(saida.items()))


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
    escrever_json(ALERTAS, {
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
            # 16/10/2026 (Monitor de riscos §6c): municípios sob aviso do INMET por UF e por grau,
            # no vocabulário do órgão. Município sob dois graus conta nos dois — a lista preserva todos.
            "municipios_inmet_por_uf_e_grau": municipios_por_uf_e_grau(por_municipio),
        },
        "municipios": {k: {c: v[c] for c in ("nome", "uf", "inmet", "cemaden")}
                       for k, v in sorted(por_municipio.items())},
        "cessados": dict(sorted(cessados.items())),
    })
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
    escrever_json(CONSULTAS, {
        "_formato": {
            "descricao": "URL, hora e hash da resposta de cada chamada de rede da última rodada "
                         "das fontes de cadência sub-diária.",
            "efeito_no_indice": "NENHUM — peso zero, como todo sinal de risco.",
            "escrito_por": "coletar_sinais_risco.py",
        },
        "gerado_em": agora(),
        "consultas": _LIVRO_CONSULTAS,
    })
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

    # ── Previsão do INMET (27/09/2026): órgão competente no lugar de modelo estrangeiro ─────
    _prev = {"Bras\u00edlia": {"27/09/2026": {
        "manha": {"uf": "DF", "entidade": "Bras\u00edlia", "resumo": "Muitas nuvens", "temp_max": 30, "temp_min": 19},
        "tarde": {"uf": "DF", "entidade": "Bras\u00edlia", "resumo": "Sol", "temp_max": 33, "temp_min": 22},
        "noite": {"uf": "DF", "entidade": "Bras\u00edlia", "resumo": "Nublado", "temp_max": 25, "temp_min": 18}}}}
    _r = parse_previsao_capitais_inmet(_prev)
    checar("INMET: maior m\u00e1xima entre os per\u00edodos", _r["DF"]["tmax"] == 33.0)
    checar("INMET: menor m\u00ednima entre os per\u00edodos", _r["DF"]["tmin"] == 18.0)
    checar("INMET: capital e data preservadas", _r["DF"]["capital"] == "Bras\u00edlia" and _r["DF"]["data"] == "27/09/2026")
    _semmax = parse_previsao_capitais_inmet({"X": {"27/09/2026": {"manha": {"uf": "SP", "temp_min": 12}}}})
    checar("INMET negativo: UF sem m\u00e1xima n\u00e3o entra (lacuna, nunca zero)", _semmax == {})
    _absurdo = parse_previsao_capitais_inmet({"Y": {"27/09/2026": {"manha": {"uf": "RJ", "temp_max": 999}}}})
    checar("INMET negativo: temperatura imposs\u00edvel recusada", _absurdo == {})
    checar("INMET negativo: resposta vazia n\u00e3o inventa UF", parse_previsao_capitais_inmet({}) == {})

    # ── Discussão do CPC (27/09/2026): substitui a leitura humana congelada ─────────────
    _cpc = ("<p>DIAGNOSTIC DISCUSSION issued by CLIMATE PREDICTION CENTER/NCEP/NWS "
            "10 September 2026</p><p>ENSO Alert System Status: \n\n El Ni\u00f1o Advisory \n\n</p>"
            "<p>Synopsis: El Ni\u00f1o is strengthening, with a greater than 90% chance of a very "
            "strong event during the Northern Hemisphere fall and winter 2026-27.</p>"
            "<p>The next update is 8 October 2026.</p>")
    _d = parse_ensodisc_cpc(_cpc)
    checar("CPC: estado do alerta lido", _d["estado"] == "El Ni\u00f1o Advisory")
    checar("CPC: data de emiss\u00e3o em formato brasileiro", _d["emitido_em"] == "10/09/2026")
    checar("CPC: data da pr\u00f3xima atualiza\u00e7\u00e3o", _d["proxima_em"] == "08/10/2026")
    checar("CPC: probabilidade e limiar declarados", _d["probabilidade"] == 90 and _d["limiar"] == "acima de")
    checar("CPC: sinopse guardada no original, sem tradu\u00e7\u00e3o", _d["sinopse"].startswith("El Ni\u00f1o is strengthening"))
    # negativos: o que n\u00e3o estiver declarado fica None, e nada \u00e9 deduzido
    _vazio = parse_ensodisc_cpc("<p>Nenhuma discuss\u00e3o aqui.</p>")
    checar("CPC negativo: p\u00e1gina sem discuss\u00e3o n\u00e3o inventa estado", _vazio["estado"] is None and _vazio["emitido_em"] is None)
    _sem_prob = parse_ensodisc_cpc("<p>ENSO Alert System Status: \n\n La Ni\u00f1a Watch \n\n</p>"
                                   "<p>Synopsis: La Ni\u00f1a conditions are expected to emerge. </p>"
                                   "<p>1 March 2027</p>")
    checar("CPC negativo: sinopse sem porcentagem n\u00e3o vira n\u00famero", _sem_prob["probabilidade"] is None)
    _absurdo = parse_ensodisc_cpc("<p>ENSO Alert System Status: \n\n El Ni\u00f1o Advisory \n\n</p>"
                                  "<p>Synopsis: chance is 180% chance of something. </p><p>2 May 2027</p>")
    checar("CPC negativo: porcentagem imposs\u00edvel recusada", _absurdo["probabilidade"] is None)

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

    # 29/09/2026: o mapa de focos virou de PONTOS. A grade é de desenho, e estas travas garantem
    # que ela não invente posição nem escala.
    _linhas_focos = ["id,lat,lon,estado",
                     "1, -11.373500, -43.420900,BAHIA",
                     "2, -11.379000, -43.425000,BAHIA",
                     "3,  -4.504600, -54.944600,PARA",
                     "4, 40.000000,  -3.000000,ESPANHA",   # fora do Brasil
                     "5, , ,BAHIA"]                        # sem coordenada
    _csv_pontos = "\n".join(_linhas_focos) + "\n"
    _g = agregar_focos_em_grade(_csv_pontos)
    checar("focos em grade: pontos proximos caem na mesma celula",
           [c for c in _g if c[2] == 2] == [[-11.4, -43.4, 2]])
    checar("focos em grade: coordenada fora do Brasil nao entra",
           all(-35 <= c[0] <= 6 and -75 <= c[1] <= -32 for c in _g))
    checar("focos em grade: linha sem coordenada nao vira ponto na origem",
           all(c[:2] != [0.0, 0.0] for c in _g) and sum(c[2] for c in _g) == 3)
    checar("focos em grade: a celula mais cheia vem primeiro", _g[0][2] >= _g[-1][2])
    checar("focos em grade: CSV vazio devolve lista vazia, nao erro",
           agregar_focos_em_grade("id,lat,lon" + "\n") == [])
    checar("focos em grade: o passo e o medido, 0,1 grau", PASSO_GRADE_FOCOS == 0.1)


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

    # 07/10/2026 (item 3): a série do RONI não é mais cortada, e são estas três coisas que o
    # handover pede provadas. Os testes rodam sobre uma série sintética que imita a forma da de
    # verdade — o autoteste é offline, e provar a leitura do arquivo da NOAA é papel da coleta,
    # não dele. O que se prova aqui é o CONTRATO: o que `_ler_fonte` devolve para `noaa_roni`.
    _TRI = ["DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ"]
    _bruta = "SEAS   YR  ANOM\n" + "".join(
        f"{_TRI[i % 12]}  {1950 + i // 12} {((i % 37) - 18) / 10:+.2f}\n" for i in range(920))
    _roni_longa = parse_roni(_bruta)
    checar("RONI: a série inteira é lida, sem corte em 160 pontos", len(_roni_longa) == 920)
    checar("RONI: a série começa em DJF de 1950",
           _roni_longa[0]["trimestre"] == "DJF" and _roni_longa[0]["ano"] == 1950)
    checar("RONI: o último ponto da leitura é o último da entrada",
           _roni_longa[-1] == {"trimestre": "JAS", "ano": 2026, "anomalia": 1.3})
    # O corte não vivia no parser, e sim em `_ler_fonte`: provar que `parse_roni` lê tudo não prova
    # que a série chega inteira ao registro. Esta é a mesma trava ESTRUTURAL das outras — lê o
    # próprio fonte e reprova se o corte voltar. Sem ela, um `serie[-160:]` reintroduzido passaria
    # com todos os testes acima verdes.
    _fonte = pathlib.Path(__file__).read_text(encoding="utf-8")
    _bloco_roni = _fonte[_fonte.index('if chave == "noaa_roni":'):_fonte.index('if chave == "noaa_nino34_mensal":')]
    # Só o CÓDIGO: o comentário do bloco cita `serie[-160:]` para dizer o que saiu, e um teste que
    # lesse o comentário reprovaria a própria explicação de por que ele foi embora.
    _codigo_roni = chr(10).join(l.split("#")[0] for l in _bloco_roni.splitlines())
    checar("RONI: `_ler_fonte` devolve a série inteira, sem fatia",
           not re.search(r"serie\[-?\d*:", _codigo_roni)
           and 'return {"serie": serie}' in _codigo_roni)
    # Duplicado é o defeito silencioso desta série: dois pontos no mesmo trimestre do mesmo ano
    # passariam no desenho (duas barras coladas) e falseariam a contagem de médias consecutivas
    # que define um episódio de El Niño.
    _chaves = [(p["trimestre"], p["ano"]) for p in _roni_longa]
    checar("RONI: nenhum ponto duplicado (trimestre e ano)", len(_chaves) == len(set(_chaves)))
    # A trava de tamanho: a série inteira em JSON tem de caber com folga no teto da consolidação.
    checar("RONI: a série inteira cabe muito abaixo do teto de 50 MB da trava de tamanho",
           len(json.dumps(_roni_longa, ensure_ascii=False)) < 200_000)
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
           all(esq["uf"][u]["temperatura"] is None and "qualidade_ar" not in esq["uf"][u] for u in UFS))
    checar("esqueleto: a linha da OMS e as duas naturezas estão declaradas NO DADO",
           esq["_formato"]["referencia_pm25_oms"]["valor"] == 15.0
           and set(esq["_formato"]["naturezas"]) == {NATUREZA_MODELO, NATUREZA_MEDICAO})

    # ---- temperatura e qualidade do ar (24/09/2026) ----------------------
    checar("média: ignora nulo e não conta como zero", _media([10, None, 20]) == 15.0)
    checar("média negativa: só nulos devolve None (ausência não vira zero)", _media([None, None]) is None)

    # A resposta devolve o lat/lon do NÓ DA GRADE, diferente do pedido — o teste usa valores
    # trocados de propósito para provar que o casamento é POSICIONAL e não por coordenada.
    _caps = resolver_capitais()
    checar("capitais: as 27 resolvem em municipios_ibge_referencia.json, uma por UF",
           len(_caps) == 27 and {c["uf"] for c in _caps} == set(UFS))
    checar("capitais: coordenada e nome vêm do arquivo de referência, não desta tabela",
           all(isinstance(c["lat"], float) and isinstance(c["lon"], float) and c["nome"] for c in _caps))
    checar("capitais: DF é Brasília e RJ é Rio de Janeiro (prova de que o código não trocou de cidade)",
           next(c["nome"] for c in _caps if c["uf"] == "DF") == "Brasília"
           and next(c["nome"] for c in _caps if c["uf"] == "RJ") == "Rio de Janeiro")
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

    # ---- camada de MEDIÇÃO: OpenAQ e estações do INMET (24/09/2026) ------
    _caps = {"DF": {"uf": "DF", "lat": -15.7939, "lon": -47.8828},
             "SP": {"uf": "SP", "lat": -23.5505, "lon": -46.6333}}
    _locais = parse_openaq_locais({"results": [
        {"id": 1, "name": "Perto de Brasília", "coordinates": {"latitude": -15.80, "longitude": -47.89},
         "provider": {"name": "Rede X"}, "sensors": [{"parameter": {"name": "pm25"}}]},
        {"id": 2, "name": "Mais perto ainda", "coordinates": {"latitude": -15.795, "longitude": -47.883},
         "provider": {"name": "Rede Y"}, "sensors": [{"parameter": {"name": "pm25"}}]},
        {"id": 3, "name": "Longe demais", "coordinates": {"latitude": -14.0, "longitude": -47.0},
         "provider": {"name": "Rede Z"}, "sensors": [{"parameter": {"name": "pm25"}}]},
        {"id": 4, "name": "Sem PM2,5 em SP", "coordinates": {"latitude": -23.551, "longitude": -46.634},
         "provider": {"name": "Rede W"}, "sensors": [{"parameter": {"name": "o3"}}]},
    ]}, _caps)
    checar("OpenAQ: escolhe o monitor MAIS PRÓXIMO da capital",
           _locais["DF"]["id"] == 2 and _locais["DF"]["distancia_km"] < 1)
    checar("OpenAQ: guarda a rede de origem, que o crédito exige",
           _locais["DF"]["rede_de_origem"] == "Rede Y")
    checar("OpenAQ: monitor além do teto de raio não representa a capital",
           all(v["id"] != 3 for v in _locais.values()))
    checar("OpenAQ: monitor sem PM2,5 não entra nesta figura", "SP" not in _locais)
    checar("OpenAQ: rotula a natureza como medição, nunca como modelo",
           _locais["DF"]["natureza"] == NATUREZA_MEDICAO)
    checar("OpenAQ negativo: resposta vazia devolve vazio",
           parse_openaq_locais({}, _caps) == {} and parse_openaq_locais({"results": []}, _caps) == {})

    # ── Ar medido (16/10/2026): IQAr do órgão, 36 h, casamento com OpenAQ, sensor sem índice ──
    _agora = datetime(2026, 10, 16, 12, 0, tzinfo=FUSO_BR)
    _mun = {"idMunicipio": 5300108, "noMunicipio": "Brasília", "sgUf": "DF"}
    _mma = parse_monitorar([
        {"idEstacao": 1, "noEstacao": "Fercal", "noFonteDados": "IBRAM", "nuLatitude": "-15.6",
         "nuLongitude": "-47.87", "municipio": _mun, "categoriaEstacao": {"descricao": "Regulatória"},
         "indiceQualidadeArAtual": {"poluente": {"noPoluente": "MP₁₀"}, "classificacaoIqAr": {"noClassificacao": "Moderada"},
                                    "medicao": {"indiceQualidadeAr": 52.0, "dtMedicao": "2026-10-16 09:00"}}},
        {"idEstacao": 2, "noEstacao": "Velha", "nuLatitude": "-15.7", "nuLongitude": "-47.9", "municipio": _mun,
         "indiceQualidadeArAtual": {"medicao": {"indiceQualidadeAr": 30.0, "dtMedicao": "2025-06-16 20:00"}}},
        {"idEstacao": 3, "noEstacao": "Sem índice", "nuLatitude": "-15.8", "nuLongitude": "-47.9", "municipio": _mun},
        "lixo"], _agora)
    checar("Ar: IQAr do órgão entra como publicado (valor, faixa, poluente)",
           _mma[0]["iqar"]["valor"] == 52.0 and _mma[0]["iqar"]["classificacao"] == "Moderada"
           and _mma[0]["ibge"] == 5300108 and _mma[0]["lat"] == -15.6)
    checar("Ar: medição com mais de 36 h é lacuna, nunca valor velho como atual",
           _mma[1]["iqar"] is None and "36 h" in _mma[1]["lacuna"])
    checar("Ar: estação sem IQAr publicado é lacuna", _mma[2]["iqar"] is None and _mma[2]["lacuna"])
    checar("Ar negativo: item malformado e resposta não-lista não quebram",
           len(_mma) == 3 and parse_monitorar({"erro": 1}, _agora) == [])
    _n = casar_openaq(_mma,
                      [{"id": 10, "name": "FERCAL", "coordinates": {"latitude": -15.601, "longitude": -47.871}},
                       {"id": 11, "name": "Outra", "coordinates": {"latitude": -15.7, "longitude": -47.9}}],
                      [{"locationsId": 10, "value": 21.04, "datetime": {"utc": "2026-10-16T13:00:00Z"}},
                       {"locationsId": 11, "value": 9.0, "datetime": {"utc": "2026-10-01T13:00:00Z"}}], _agora)
    checar("Ar: OpenAQ casa a mesma estação a até 300 m e pendura o PM2,5",
           _n == 1 and _mma[0]["pm25_openaq"]["valor"] == 21.0 and _mma[0]["pm25_openaq"]["distancia_m"] < 300)
    checar("Ar: medição do OpenAQ com mais de 36 h não casa", _mma[1]["pm25_openaq"] is None)
    _alvos = locais_openaq_pm25([
        {"id": 10, "isMonitor": True, "datetimeLast": {"utc": "2026-10-16T13:00:00Z"},
         "sensors": [{"id": 7, "parameter": {"name": "pm25"}}, {"id": 8, "parameter": {"name": "o3"}}]},
        {"id": 12, "isMonitor": False, "datetimeLast": {"utc": "2026-10-16T13:00:00Z"},
         "sensors": [{"id": 9, "parameter": {"name": "pm25"}}]},
        {"id": 13, "isMonitor": True, "datetimeLast": {"utc": "2023-04-01T00:00:00Z"},
         "sensors": [{"id": 5, "parameter": {"name": "pm25"}}]}], _agora)
    checar("Ar: OpenAQ só consulta monitor de referência com PM2,5 recente (sensor de baixo custo e local parado ficam fora)",
           _alvos == {10: {7}})
    _sens = parse_redear([
        {"sensor_id": 1, "source": "RedeAr", "name": "Carauari", "geocode_mun": 1301001, "geocode_uf": 13,
         "gps": {"coordinates": [-67.17, -5.09]}, "readings": [
             {"datetime": "2026-10-16T08:55:04", "pms1_pm2_5_env": 13, "pms2_pm2_5_env": 18, "pms1_pm10_env": 13, "pms2_pm10_env": 19},
             {"datetime": "2026-10-16T09:51:04", "pms1_pm2_5_env": 10, "pms2_pm2_5_env": 12, "pms1_pm10_env": 11, "pms2_pm10_env": 13}]},
        {"sensor_id": 2, "name": "teste sem município", "readings": []},
        {"sensor_id": 3, "geocode_mun": 5300108, "readings": [{"datetime": "2026-07-06T15:11:04", "pms1_pm2_5_env": 5}]},
    ], _agora)
    checar("Ar: sensor usa a leitura MAIS RECENTE, média dos dois canais, em µg/m³ (nunca AQI)",
           _sens[0]["pm25"] == {"valor": 11.0, "pm10": 12.0, "unidade": "µg/m³", "lido_em": "2026-10-16T09:51:04"})
    checar("Ar: sensor sem código IBGE fica de fora; leitura velha é lacuna",
           len(_sens) == 2 and _sens[1]["pm25"] is None and "36 h" in _sens[1]["lacuna"])

    # ── Manchas do Monitor de Secas (16/10/2026): leitor de .shp/.dbf, buraco, simplificação ──
    import struct as _st
    _ext = [[0, 0], [0, 5], [0, 10], [10, 10], [10, 0], [0, 0]]          # horário: externo
    _bur = [[2, 2], [4, 2], [4, 4], [2, 4], [2, 2]]                       # anti-horário: buraco
    _pts = _ext + _bur
    _corpo = (_st.pack("<i4d2i", 5, 0, 0, 0, 0, 2, len(_pts)) + _st.pack("<2i", 0, len(_ext))
              + b"".join(_st.pack("<2d", *p) for p in _pts))
    _shp = b"\0" * 100 + _st.pack(">ii", 1, len(_corpo) // 2) + _corpo
    _dbf = (bytes([3, 0, 0, 0]) + _st.pack("<IHH", 1, 65, 5) + b"\0" * 20
            + b"uf_codigo".ljust(11, b"\0") + b"C" + b"\0" * 4 + bytes([4]) + b"\0" * 15 + b"\x0d" + b" s2  ")
    _pol = ler_poligonos_shp(_shp, _dbf, "uf_codigo")
    checar("Secas: lê polígono e categoria do .shp/.dbf", _pol[0][0] == "s2" and len(_pol[0][1]) == 2)
    _man = manchas_de_seca(_pol)
    checar("Secas: buraco fica dentro do externo (não vira mancha cheia) e categoria S2",
           _man[0]["properties"]["categoria"] == "S2" and len(_man[0]["geometry"]["coordinates"]) == 1
           and len(_man[0]["geometry"]["coordinates"][0]) == 2)
    checar("Secas: simplificação tira ponto colinear e mantém o anel fechado",
           [0.0, 5.0] not in _man[0]["geometry"]["coordinates"][0][0]
           and _man[0]["geometry"]["coordinates"][0][0][0] == _man[0]["geometry"]["coordinates"][0][0][-1])
    checar("Secas negativo: código fora de s0–s4 não vira categoria", manchas_de_seca([("si", [_ext])])[0]["properties"]["categoria"] is None)
    checar("Avisos: municípios por UF e grau, município com dois graus conta nos dois",
           municipios_por_uf_e_grau({"1": {"uf": "PA", "inmet": [{"severidade": "Perigo"}, {"severidade": "Perigo Potencial"}]},
                                     "2": {"uf": "PA", "inmet": [{"severidade": "Perigo"}, {"severidade": "Perigo"}]},
                                     "3": {"uf": "MA", "inmet": []}})
           == {"PA": {"Perigo": 2, "Perigo Potencial": 1}})
    # ── Focos pelo satélite de referência (16/10/2026) ────────────────────────────────────
    _csv = ("id,lat,lon,data_hora_gmt,satelite,municipio,estado,municipio_id,bioma\n"
            "1,-3.5,-54.6,2026-10-15 17:00:00,AQUA_M-T,PLACAS,PARÁ,1505650,Amazônia\n"
            "2,-3.5,-54.6,2026-10-15 17:01:00,NOAA-20,PLACAS,PARÁ,1505650,Amazônia\n"
            "3,-9.0,-45.0,2026-10-15 16:00:00,AQUA_M-T,BALSAS,MARANHÃO,2101400,Cerrado\n"
            "4,-9.0,-45.0,2026-10-14 16:00:00,AQUA_M-T,BALSAS,MARANHÃO,2101400,Cerrado\n")
    _r = resumo_focos_ref(_csv)
    checar("Focos ref: só o satélite de referência conta (o NOAA-20 do mesmo fogo fica fora)",
           _r["2026-10-15"]["total"] == 2 and _r["2026-10-15"]["uf"] == {"PA": 1, "MA": 1}
           and _r["2026-10-15"]["bioma"] == {"Amazônia": 1, "Cerrado": 1} and _r["2026-10-14"]["total"] == 1)
    checar("Focos ref: município pelo código IBGE da fonte", _r["2026-10-15"]["municipio"] == {"1505650": 1, "2101400": 1})
    _anual = resumo_focos_ref("id_bdq,data_pas,estado,municipio,bioma\n9,2025-10-15 16:52:00,PERNAMBUCO,SOLIDÃO,Caatinga\n",
                              filtrar_satelite=False)
    _f = atualizar_focos_ref({"serie": {"2024-01-01": {"total": 5, "uf": {}, "bioma": {}}}}, {**_r, **_anual}, "2026-10-15")
    checar("Focos ref: mesmo dia do ano anterior vem do anual de referência",
           _f["resumo"]["mesmo_dia_ano_anterior"] == {"dia": "2025-10-15", "total": 1})
    checar("Focos ref: mês e 30 dias somam só dias com arquivo e dizem quantos",
           _f["resumo"]["mes"] == {"total": 3, "dias_com_dado": 2}
           and _f["resumo"]["ultimos_30_dias"]["dias_com_dado"] == 2
           and _f["resumo"]["municipios_30_dias"] == {"1505650": 1, "2101400": 2})
    checar("Focos ref: série apara o que passou de 400 dias", "2024-01-01" not in _f["serie"])
    checar("Focos ref negativo: sem o ano anterior na série, o campo é lacuna (None), não zero",
           atualizar_focos_ref({}, _r, "2026-10-15")["resumo"]["mesmo_dia_ano_anterior"] is None
           and resumo_focos_ref("") == {})

    # ── Consulta do município no Monitor de riscos (16/10/2026) ──────────────────────────
    _ref = [{"nome": "Brasília", "uf": "DF", "codigo_ibge": 5300108, "lat": -15.79, "lon": -47.88},
            {"nome": "Planaltina", "uf": "GO", "codigo_ibge": 5217609, "lat": -15.45, "lon": -47.61}]
    _rm = montar_riscos_municipio(
        _ref,
        {"resumo": {"municipios_30_dias": {"5300108": 4}, "ultimos_30_dias": {"dias_com_dado": 30}}},
        {"municipios": {"5300108": {"inmet": [{"tipo": "Baixa Umidade", "severidade": "Perigo", "fim": "x"}], "cemaden": []},
                        "5217609": {"inmet": [{"tipo": "Baixa Umidade", "severidade": "Perigo", "fim": "x"}]}}},
        {"estacoes": [{"nome": "Fercal", "municipio": "Brasília", "uf": "DF", "rede": "IBRAM", "lat": -15.6, "lon": -47.87,
                       "iqar": {"valor": 52.0}}]},
        {"eventos": [{"nome": "BRASILIA", "uf": "DF", "data": "01/09/2026", "decreto": "SE", "url": "u1"},
                     {"nome": "Brasília", "uf": "DF", "data": "20/09/2026", "decreto": "SE 2", "url": "u2"}]})
    _df, _go = _rm["DF"]["municipios"]["5300108"], _rm["GO"]["municipios"]["5217609"]
    checar("Município: focos de 30 dias; sem foco com série completa é 0", _df["focos_30_dias"] == 4 and _go["focos_30_dias"] == 0)
    checar("Município: série incompleta deixa focos em None (não sabemos), nunca 0",
           montar_riscos_municipio(_ref[:1], {"resumo": {"ultimos_30_dias": {"dias_com_dado": 12}}}, {}, {}, {})
           ["DF"]["municipios"]["5300108"]["focos_30_dias"] is None)
    checar("Município: aviso vai como índice da lista da UF; decreto mais recente primeiro, casado pelo nome",
           _rm["DF"]["avisos_inmet"][_df["avisos_inmet"][0]]["tipo"] == "Baixa Umidade"
           and _df["decretos"][0]["url"] == "u2" and _df["decretos_no_ciclo"] == 2)
    checar("Município: estação de ar a até 50 km com distância; capital mais próxima com distância",
           _df["ar_estacao"]["distancia_km"] == 21 and _rm["DF"]["estacoes"][0]["iqar"]["valor"] == 52.0
           and _go["capital_mais_proxima"]["nome"] == "Brasília" and "ar_sensor" not in _df)

    _est = parse_estacoes_inmet([
        {"CD_ESTACAO": "A001", "DC_NOME": "BRASILIA", "SG_ESTADO": "DF", "CD_SITUACAO": "Operante",
         "VL_LATITUDE": "-15.7893", "VL_LONGITUDE": "-47.9257"},
        {"CD_ESTACAO": "A999", "DC_NOME": "MAIS PERTO EM PANE", "SG_ESTADO": "DF", "CD_SITUACAO": "Pane",
         "VL_LATITUDE": "-15.7939", "VL_LONGITUDE": "-47.8828"},
        {"CD_ESTACAO": "A701", "DC_NOME": "SAO PAULO - MIRANTE", "SG_ESTADO": "SP", "CD_SITUACAO": "Operante",
         "VL_LATITUDE": "-23.4961", "VL_LONGITUDE": "-46.6200"},
        {"CD_ESTACAO": "A555", "DC_NOME": "LONGE", "SG_ESTADO": "SP", "CD_SITUACAO": "Operante",
         "VL_LATITUDE": "-22.0", "VL_LONGITUDE": "-47.0"},
    ], _caps)
    checar("INMET estações: estação em PANE não é escolhida, mesmo sendo a mais próxima",
           _est["DF"]["codigo"] == "A001")
    checar("INMET estações: acha capital cujo nome de estação NÃO é o nome da cidade (SAO PAULO - MIRANTE)",
           _est["SP"]["codigo"] == "A701")
    checar("INMET estações: estação além do teto de raio não representa a capital",
           all(v["codigo"] != "A555" for v in _est.values()))
    checar("INMET estações negativo: lista vazia devolve vazio",
           parse_estacoes_inmet([], _caps) == {} and parse_estacoes_inmet(None, _caps) == {})

    # §233: o leitor da condição das capitais, com as três sutilezas medidas em 26/09/2026.
    _cond = [
        {"CAPITAL": "BELO HORIZONTE", "TMIN18": "19.5", "TMAX18": "28.8", "UMIN18": "53", "PMAX12": "0"},
        {"CAPITAL": "MACEIÓ", "TMIN18": "23.1", "TMAX18": "29.6*", "UMIN18": "60", "PMAX12": "0"},
        {"CAPITAL": "ARACAJU", "TMIN18": "*", "TMAX18": "*", "UMIN18": "*", "PMAX12": "*"},
        {"CAPITAL": "BRASILIA", "TMIN18": "18.2", "TMAX18": "31.9", "UMIN18": "37", "PMAX12": "0"},
        {"CAPITAL": "BRASILIA", "TMIN18": "18.2", "TMAX18": "31.9", "UMIN18": "37", "PMAX12": "0"},
    ]
    _capsc = {"MG": {"nome": "Belo Horizonte"}, "AL": {"nome": "Maceió"},
              "SE": {"nome": "Aracaju"}, "DF": {"nome": "Brasília"}}
    _m = parse_condicao_capitais(_cond, _capsc, "2026-09-25")
    checar("§233 condição das capitais: lê a máxima e a mínima medidas",
           _m.get("MG", {}).get("tmax") == 28.8 and _m["MG"]["tmin"] == 19.5)
    checar("§233 nome em maiúscula E com acento ('MACEIÓ') casa dos dois lados",
           "AL" in _m and _m["AL"]["tmax"] == 29.6)
    checar("§233 o asterisco do valor é registrado como marca da fonte, não interpretado",
           _m["AL"]["marcado_pela_fonte"] is True and _m["MG"]["marcado_pela_fonte"] is False)
    checar("§233 negativo: '*' sozinho é NÃO DIVULGADO e a capital não entra — nunca zero",
           "SE" not in _m)
    checar("§233 Brasília vem DUAS vezes na fonte; idênticas, entra uma",
           _m.get("DF", {}).get("tmax") == 31.9)
    _div = _cond[:4] + [{"CAPITAL": "BRASILIA", "TMIN18": "18.2", "TMAX18": "40.0",
                         "UMIN18": "37", "PMAX12": "0"}]
    checar("§233 duas linhas DIVERGENTES para a mesma capital: nenhuma serve, recusa",
           "DF" not in parse_condicao_capitais(_div, _capsc, "2026-09-25"))
    checar("§233 negativo: lista vazia ou nula devolve vazio",
           parse_condicao_capitais([], _capsc, "x") == {} and parse_condicao_capitais(None, _capsc, "x") == {})

    # A credencial vem SÓ do ambiente, e sem ela a fonte nem bate na porta.
    _antes = {k: os.environ.pop(k, None) for k in ("OPENAQ_API_KEY", "INMET_API_TOKEN")}
    try:
        # §233: a lista é derivada de quem DECLARA credencial, e não fixa. Até 26/09/2026 ela
        # tinha `inmet_estacoes` escrito à mão, e a fonte declarava `INMET_API_TOKEN` — numa rota
        # que, medida no mesmo dia, responde HTTP 200 com 673 estações SEM token. O teste provava
        # o defeito: exigia que a fonte recusasse por falta de uma chave que a rota não pede.
        for _f in [k for k, v in FONTES.items() if v.get("credencial")]:
            try:
                coletar_fonte(_f)
                checar(f"{_f}: sem credencial levanta CredencialAusente", False)
            except CredencialAusente as e:
                checar(f"{_f}: sem credencial levanta CredencialAusente, sem tocar a rede",
                       FONTES[_f]["credencial"] in str(e))
            except Exception as e:  # noqa: BLE001
                checar(f"{_f}: sem credencial levanta CredencialAusente (veio {type(e).__name__})", False)
        checar("§233 inmet_estacoes NÃO exige credencial: a rota dela é pública (medido 26/09)",
               not FONTES["inmet_estacoes"].get("credencial"))
        checar("§233 e a fonte promete a MEDIDA, então declara a rota que a traz",
               "condicao/capitais" in FONTES["inmet_estacoes"].get("endpoint_medida", ""))
        checar("credencial: lida do ambiente, nunca do repositório",
               credencial_de("openaq") is None)
        os.environ["OPENAQ_API_KEY"] = "chave-de-teste"
        checar("credencial: encontra a chave quando o ambiente a tem",
               credencial_de("openaq") == "chave-de-teste")
        checar("credencial: fonte sem credencial declarada devolve None",
               credencial_de("noaa_oni") is None)
    finally:
        os.environ.pop("OPENAQ_API_KEY", None)
        for k, v in _antes.items():
            if v is not None:
                os.environ[k] = v
    checar("esqueleto: a camada de medição nasce como lacuna nas 27 UFs",
           all(esq["uf"][u]["temperatura_medida"] is None and esq["uf"][u]["ar_medido"] is None for u in UFS))


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
        gravar_pontos_de_foco()
        return
    camadas = {"ciclo", "observado", "enos"}
    if "--camada" in args:
        camadas = {args[args.index("--camada") + 1]}
    print(f"Coletando sinais oficiais de risco · camadas: {', '.join(sorted(camadas))}")
    registro = coletar(registro, camadas)
    gravar(registro)
    gravar_pontos_de_foco()
    gravar_alertas_vigentes()
    if "observado" in camadas:
        gravar_ar_medido()
        gravar_secas_manchas()
        gravar_focos_referencia()
        gravar_riscos_municipio()
    gravar_consultas()


if __name__ == "__main__":
    main()