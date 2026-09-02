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
import json, sys
from datetime import date
from coletores_base import (buscar, preservar_evidencia, log_busca, registrar_lacuna, ler, gravar,
                            rodar_autoteste, referencia_ibge)

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
    hoje = date.today().strftime("%d/%m/%Y")
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
                    "nota": "Documento verificado na sessão de 02/09/2026; endereço estável em verificação."},
                   {"titulo": "Portaria do painel de especialistas em clima e saúde",
                    "orgao": "Ministério da Saúde", "data": "anunciada em 26/08/2026", "url": None,
                    "status": "anunciado_nao_localizado", "nota": "A vigiar no DOU (termo incluído no vigia federal)."},
                   {"titulo": "CISC — Centros Integrados de Saúde e Clima (8 cidades-piloto, 5 regiões)",
                    "orgao": "Ministério da Saúde", "data": "2026", "url": None,
                    "status": "anunciado_nao_localizado", "nota": "Existência verificada; relação nominal das cidades não localizada — não inventar."},
                   {"titulo": "Painel Nacional de Excesso de Calor · VigiAR · GeoRisk",
                    "orgao": "Ministério da Saúde", "data": "—", "url": None,
                    "status": "anunciado_nao_localizado", "nota": "Citados pelo MS; URL e formato a verificar (§15)."},
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
                  "painel_arboviroses_ms": {"nome": "Painel de Arboviroses", "orgao": "Ministério da Saúde", "papel": "fonte PRIMÁRIA do número de casos prováveis por semana epidemiológica",
                                             "url_publica": None, "status": "a_verificar", "consultado_em": None, "nota": "formato a verificar (§15)"},
                  "infodengue": {"nome": "InfoDengue", "orgao": "Fiocruz/FGV", "papel": "nível de alerta e série municipal semanal (modelo); crédito obrigatório 'modelo InfoDengue (Fiocruz/FGV)'",
                                 "url_publica": "https://info.dengue.mat.br", "status": "aguardando_primeira_coleta", "consultado_em": None,
                                 "regra_divergencia": "divergência com o painel do MS → exibe o MS e loga a diferença (C2)"},
                  "inmet_calor": {"nome": "Avisos de calor", "orgao": "INMET", "papel": "reuso do adaptador do PR #3 (sinais_risco.json → avisos_inmet)", "status": "reuso", "consultado_em": None},
                  "inpe_focos": {"nome": "Focos de queimada (proxy respiratório)", "orgao": "INPE", "papel": "reuso (sinais_risco.json → fogo)", "status": "reuso", "consultado_em": None},
                  "sisagua": {"nome": "SISAGUA — água/intermitência em estiagem", "orgao": "Ministério da Saúde", "url_publica": None, "status": "a_verificar", "consultado_em": None},
                  "espin": {"nome": "ESPIN e decretos de emergência sanitária", "orgao": "DOU / diários municipais", "papel": "RESPOSTA, peso zero", "status": "aguardando_primeira_coleta", "consultado_em": None},
              },
              "dengue_capitais": {}, "gerado_em": hoje}
    gravar("saude_federal.json", federal); gravar("saude_uf.json", saude_uf); gravar("saude_sinais.json", sinais)
    print("saúde: 3 registros semeados — 27 UFs NAO_VERIFICADO; 6 cartões federais; fontes observadas em lacuna declarada")


def parse_infodengue(dados) -> dict:
    """Última semana epidemiológica disponível: {se, casos_est, casos, nivel, data}. Função pura.
    Níveis do InfoDengue: 1 verde, 2 amarelo, 3 laranja, 4 vermelho (vocabulário DA FONTE)."""
    if not isinstance(dados, list) or not dados:
        return {}
    ult = max(dados, key=lambda r: (r.get("SE") or 0))
    return {"se": ult.get("SE"), "casos_est": ult.get("casos_est"), "casos_notif": ult.get("casos"),
            "nivel": ult.get("nivel"), "data_iniSE": ult.get("data_iniSE")}


def coletar():
    _, por_nome = referencia_ibge()
    sinais = ler("saude_sinais.json"); ano = date.today().year; ok = lac = 0
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
        if r:
            sinais["dengue_capitais"][uf] = {**r, "municipio": cap, "ibge": cod, "fonte": "modelo InfoDengue (Fiocruz/FGV)",
                                             "url": url, "coletado_em": date.today().strftime("%d/%m/%Y"), "hash_evidencia": h}
            ok += 1
        log_busca("DOU", 1, [url], "registro" if r else "pista", uf=uf, municipio=cap, ibge=cod, nivel=None,
                  n_resultados=len(dados) if isinstance(dados, list) else 0, resultados=f"InfoDengue: {r}", hash_evidencia=h)
    sinais["fontes"]["infodengue"]["status"] = "coletado" if ok else "aguardando_primeira_coleta"
    sinais["fontes"]["infodengue"]["consultado_em"] = date.today().strftime("%d/%m/%Y")
    sinais["gerado_em"] = date.today().strftime("%d/%m/%Y")
    gravar("saude_sinais.json", sinais)
    print(f"InfoDengue: {ok} capitais coletadas, {lac} lacunas")
    return 0


FIX = [{"SE": 202634, "casos_est": 12.3, "casos": 10, "nivel": 2, "data_iniSE": "2026-08-23"},
       {"SE": 202635, "casos_est": 15.0, "casos": 9, "nivel": 3, "data_iniSE": "2026-08-30"}]


def autoteste():
    def t1(): r = parse_infodengue(FIX); return r["se"] == 202635 and r["nivel"] == 3
    def t2(): return parse_infodengue([]) == {} and parse_infodengue(None) == {} and parse_infodengue({"erro": 1}) == {}
    def t3():
        semear(); u = ler("saude_uf.json")["uf"]; return len(u) == 27 and all(v["status"] == "NAO_VERIFICADO" for v in u.values())
    def t4(): f = ler("saude_federal.json"); return all(c["url"] is None or c["url"].startswith("https://www.gov.br/") for c in f["cartoes"])
    return rodar_autoteste({"parser InfoDengue: última SE": t1, "negativo: resposta vazia/malformada": t2,
                            "semear: 27 UFs NAO_VERIFICADO": t3, "cartões federais: nenhum link fora de gov.br": t4})


if __name__ == "__main__":
    if "--autoteste" in sys.argv: sys.exit(autoteste())
    if "--semear" in sys.argv: semear(); sys.exit(0)
    sys.exit(coletar())
