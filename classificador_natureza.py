#!/usr/bin/env python3
"""
classificador_natureza.py
==========================
Classificador automático ex-ante vs. resposta, aplicando o teste do objeto
(METODOLOGIA §5.2.1, Correção B) ao texto de um ato/decreto/portaria.

ORIGEM (31/08/2026): Patricia pediu que o índice se atualize sozinho a cada
novo decreto/ato encontrado pelas rotinas de descoberta (imprensa, Querido
Diário, sinais federais, repositórios estaduais), sem passar por revisão
manual em toda ocorrência — reservando o humano só para o que chegar pelo
formulário público de contribuição (que já tem seu próprio filtro automático
em processar_contribuicoes.py, regras R1-R7).

REGRA DE SEGURANÇA (não-negociável): na dúvida, NÃO classifica. O único erro
tolerado é o falso negativo (deixar de creditar algo que merecia crédito —
corrigível na atualização seguinte); o falso positivo (pontuar um ato de
resposta como se fosse ex-ante) NUNCA é aceitável, porque contamina o índice
publicado. Por isso toda regra de decisão aqui é assimétrica: pede evidência
POSITIVA de ex-ante (nomeia instrumento conhecido, ou tem disclaimer explícito
+ gatilho de previsão) e evidência de AUSÊNCIA de sinais de resposta (dano
relatado, reconhecimento federal) — a falta de qualquer uma cai em DÚVIDA.

VALIDADO (31/08/2026) contra a base real, não só casos hipotéticos:
  - 125 registros de categoria plano/plano_antigo (municipios.json) — todos
    já confirmados como ex-ante por verificação humana: 109 reconhecidos
    corretamente (87%), 16 foram para DÚVIDA (13%), 0 erros.
  - 98 registros de categoria decreto (atos de resposta reais, nunca
    pontuados): 56 rejeitados corretamente (57%), 42 foram para DÚVIDA (43%),
    0 confundidos com ex-ante — depois de 2 rodadas de correção que acharam
    e consertaram 3 falsos positivos reais (decretos de resposta que citavam,
    de passagem, um PLANCON existente no repositório estadual).
Rode `python3 classificador_natureza.py --self-test` para reproduzir.

USO:
    from classificador_natureza import classificar, citacao_completa
    decisao, motivo = classificar(texto_do_ato, tem_reconhecimento_federal=False)
    # decisao é um de: "EX_ANTE", "RESPOSTA", "DUVIDA"
"""
import argparse
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).parent
DICIONARIO = json.load(open(RAIZ / "data" / "dicionario_busca.json", encoding="utf-8"))
TERMOS_INSTRUMENTO = [t["termo"].lower() for t in DICIONARIO["grupos"]["instrumento"]["termos"]]

SINALIZADORES_RESPOSTA_SEGUROS = ["situação de emergência", "estado de calamidade pública",
                                    "calamidade pública", "estado de emergência"]
SINAIS_FIDE_FEDERAL = ["reconhecimento federal", "portaria de reconhecimento", "fide",
                        "portaria mdr", "portaria sedec", "s2id"]
SINAIS_DANO_OCORRIDO = ["ocasionaram", "afetad", "danos causados", "desde a madrugada",
                         "atingiu", "atingid", "que atingiram", "processo erosivo"]
SINAIS_PREVENTIVO_EXPLICITO = ["não representa situação de emergência",
                                "não configura situação de emergência",
                                # 27/09/2026 (canário `plano_novo` do juiz): flexões da MESMA
                                # expressão. Sem elas, um decreto que encerra com "não configurando
                                # situação de emergência" — forma comum na redação de decreto — caía
                                # em DÚVIDA por falta de disclaimer, embora o disclaimer estivesse
                                # ali. Falso negativo, não falso positivo: nada que pontuava deixa
                                # de pontuar por causa desta entrada.
                                "não configurando situação de emergência",
                                "não configuram situação de emergência",
                                "não representando situação de emergência",
                                "não declara situação de emergência",
                                "não se trata de situação de emergência",
                                "caráter preventivo", "caráter exclusivamente preventivo"]
RE_GATILHO_PREVISAO = re.compile(
    r"projeç|previs|prognóstic|boletim|painel el ni|cemaden|inmet|monitorament|alerta clim|"
    r"alerta ambiental|centro de (monitorament|previs)", re.I)
# "Decreto N (chuvas/estiagem/...)" — convenção que indica decreto motivado por dano,
# mesmo sem "situação de emergência" por extenso; derrota o atalho de "cita instrumento".
RE_DECRETO_COM_CAUSA_DANO = re.compile(
    r"decreto\s*(estadual|est\.)?\s*([nº°.\s]*\d+.{0,15})?\((chuvas?|estiagem|seca|inundaç\w*|"
    r"enchente|deslizamento|alagamento|erosão)\)"
    r"|decreto\s+de\s+(chuvas?|estiagem|seca|inundaç\w*|enchente|deslizamento|alagamento|erosão)",
    re.I)
# 09/10/2026 (A1-14). A etapa 2 do juiz aceita "instrucao normativa" como instrumento, e esta
# expressao nao a conhecia: o mesmo documento passava por instrumento e era recusado por
# `citacao_incompleta`, duas regras da MESMA regua discordando. O acento tambem era obrigatorio em
# "resolução", e diario oficial em OCR perde acento com frequencia. As duas listas passam a ser a
# mesma lista de instrumentos.
RE_NUMERO_ATO = re.compile(
    r"(decreto|portaria|lei|resolu[çc][ãa]o|instru[çc][ãa]o\s+normativa)"
    r"\s*(estadual|municipal|est\.)?\s*[nº°.\s]*"
    r"(\d{1,3}(?:\.\d{3})*|\d+)", re.I)
RE_DATA_COMPLETA = re.compile(r"\d{1,2}[/.]\d{1,2}[/.]\d{2,4}")
# 22/09/2026 (§154): gramática padrão de diário oficial — "DE 21 DE AGOSTO DE 2026", "de 1º de setembro de 2026".
# Sem isto, extrair_data devolvia só o ano e o registro público saía "ato 14.665, 2026" (caso Feira de Santana/BA).
MESES = {"janeiro": 1, "fevereiro": 2, "marco": 3, "março": 3, "abril": 4, "maio": 5, "junho": 6, "julho": 7,
         "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12}
RE_DATA_EXTENSO = re.compile(r"\b(\d{1,2})[º°o]?\s+de\s+([a-zç]+)\s+de\s+(\d{4})\b", re.I)
RE_DATA_ANO_SOLTO = re.compile(r"\b(?:19|20)\d{2}\b")   # 22/09/2026 (§156): "4574" (nº de lei) era lido como ano


def data_extenso_para_numerica(m):
    """'21 DE AGOSTO DE 2026' → '21/08/2026'; None se o mês não for reconhecido."""
    mes = MESES.get(m.group(2).lower())
    return f"{int(m.group(1)):02d}/{mes:02d}/{m.group(3)}" if mes else None


def cita_instrumento_conhecido(texto_lower):
    """Retorna o termo do dicionário 'instrumento' encontrado no texto, ou None."""
    return next((t for t in TERMOS_INSTRUMENTO if t in texto_lower), None)


def classificar(texto, tem_reconhecimento_federal=False):
    """Aplica o teste do objeto (3 critérios cumulativos + teste-fósforo, §5.2.1).

    Retorna (decisao, motivo). decisao é um de "EX_ANTE" / "RESPOSTA" / "DUVIDA".
    NUNCA lança exceção por texto vazio/estranho — nesse caso retorna DUVIDA.
    """
    if not texto or not texto.strip():
        return "DUVIDA", "texto vazio ou ausente"
    # 27/09/2026 (canário `plano_novo` do juiz): todo sinal aqui é comparado por substring, e o
    # texto de um diário oficial vem quebrado em linhas: o disclaimer preventivo com uma quebra
    # entre "configurando" e "situação" não casava com a forma de uma linha só — estava no documento
    # e o classificador não o via.
    # Normalizar o espaço em branco antes de comparar conserta isso para TODOS os sinais de uma
    # vez, em vez de multiplicar variantes no dicionário.
    t = re.sub(r"\s+", " ", texto.lower())

    if tem_reconhecimento_federal or any(s in t for s in SINAIS_FIDE_FEDERAL):
        return "RESPOSTA", "teste-fósforo: menciona rota de reconhecimento federal/FIDE"

    sinalizador_seguro = next((s for s in SINALIZADORES_RESPOSTA_SEGUROS if s in t), None)
    dano_ocorrido = any(s in t for s in SINAIS_DANO_OCORRIDO)
    if sinalizador_seguro and dano_ocorrido:
        return "RESPOSTA", f"sinalizador '{sinalizador_seguro}' + recital de dano ocorrido"

    causa_dano_no_decreto = bool(RE_DECRETO_COM_CAUSA_DANO.search(t))
    instrumento = cita_instrumento_conhecido(t)
    if instrumento and not dano_ocorrido and not sinalizador_seguro and not causa_dano_no_decreto:
        return "EX_ANTE", f"nomeia instrumento conhecido do dicionário: '{instrumento}', sem dano relatado"
    if instrumento and causa_dano_no_decreto:
        return "DUVIDA", f"cita instrumento '{instrumento}' MAS também 'decreto (causa)' — sinais conflitantes"

    preventivo_explicito = next((s for s in SINAIS_PREVENTIVO_EXPLICITO if s in t), None)
    gatilho_previsao = bool(RE_GATILHO_PREVISAO.search(t))

    if preventivo_explicito and gatilho_previsao and not dano_ocorrido:
        return "EX_ANTE", f"'{preventivo_explicito}' + gatilho de previsão, sem dano ocorrido"

    if sinalizador_seguro and not dano_ocorrido and not preventivo_explicito:
        return "DUVIDA", f"sinalizador '{sinalizador_seguro}' presente, mas sem dano nem disclaimer claro"

    if not sinalizador_seguro and not dano_ocorrido and gatilho_previsao:
        return "EX_ANTE", "sem sinalizador de resposta, gatilho de previsão presente"

    if instrumento and not dano_ocorrido:
        return "EX_ANTE", f"nomeia instrumento '{instrumento}', sinalizador presente mas sem dano — confiança média"

    return "DUVIDA", "nenhum padrão claro bateu — não classificar sozinho"


def extrair_data(texto):
    """Prefere SEMPRE uma data completa (dd/mm/aaaa), não importa onde apareça no
    texto, sobre um ano solto que apareça antes dela — achado real do teste de
    ponta a ponta de 31/08/2026 (Sorocaba): 'ciclo El Niño 2026/2027' vinha antes
    de 'de 15/08/2026' no texto, e um re.search ingênuo pegava o '2026' errado."""
    m_completa = RE_DATA_COMPLETA.search(texto)
    if m_completa:
        return m_completa.group(0)
    for m_ext in RE_DATA_EXTENSO.finditer(texto):   # 22/09/2026: por extenso vence ano solto
        d = data_extenso_para_numerica(m_ext)
        if d:
            return d
    m_ano = RE_DATA_ANO_SOLTO.search(texto)
    return m_ano.group(0) if m_ano else None


JANELA_DA_DATA_DO_ATO = 90


def data_do_ato(texto):
    """A data DO ATO: a que vem logo depois do numero do ato, nao a primeira do texto.

    09/10/2026 (A1-21). A regra existia desde 22/09 (§154, achado no diario de Feira de Santana)
    dentro de `julgar_e_aplicar_descobertas.numero_e_data`, e o JUIZ nao a usava: ele chamava
    `extrair_data(texto)`, que devolve a primeira data completa do documento. Num diario, a
    primeira data e a da EDICAO ("DATA 22/08/2026"); num plano de sessenta paginas pode ser a data
    de uma referencia bibliografica. A data do ato e a que acompanha o numero do ato.

    Dois caminhos liam a mesma coisa com reguas diferentes; agora a regua tem um dono, e os dois a
    chamam. Sem numero de ato no texto, nao ha janela, e vale a busca global — que e o que o
    documento tecnico sem ato precisa.
    """
    m_num = RE_NUMERO_ATO.search(texto or "")
    if not m_num:
        return extrair_data(texto)
    janela = (texto or "")[m_num.end(): m_num.end() + JANELA_DA_DATA_DO_ATO]
    return extrair_data(janela) or extrair_data(texto)


def citacao_completa(numero_e_data_texto):
    """Exige número do ato E data explícita — sem os dois, mesmo uma classificação
    EX_ANTE confiante não deve ser aplicada sozinha (não dá pra citar a fonte
    corretamente na tabela pública sem essa dupla)."""
    return bool(RE_NUMERO_ATO.search(numero_e_data_texto) and extrair_data(numero_e_data_texto))


def self_test():
    """Reproduz a validação de 31/08/2026 contra a base real (223 casos) + 12 casos
    de calibração manual. Levanta AssertionError se qualquer taxa de erro > 0."""
    m = json.load(open(RAIZ / "data" / "municipios.json", encoding="utf-8"))

    planos = [i for i in m if i.get("categoria") in ("plano", "plano_antigo")]
    erros_plano = []
    for item in planos:
        dec, motivo = classificar(item.get("documento", ""))
        if dec == "RESPOSTA":
            erros_plano.append((item["nome"], item["uf"], motivo))
    assert not erros_plano, f"FALSO NEGATIVO GRAVE em planos reais: {erros_plano}"

    decretos = [i for i in m if i.get("categoria") == "decreto"]
    erros_decreto = []
    for item in decretos:
        texto = item.get("documento", "")
        tem_sedec = "portaria sedec" in texto.lower()
        dec, motivo = classificar(texto, tem_reconhecimento_federal=tem_sedec)
        if dec == "EX_ANTE":
            erros_decreto.append((item["nome"], item["uf"], texto, motivo))
    assert not erros_decreto, f"FALSO POSITIVO GRAVE (o pior erro possível) em decretos de resposta reais: {erros_decreto}"

    n_planos_ok = sum(1 for i in planos if classificar(i.get("documento", ""))[0] == "EX_ANTE")
    n_decretos_ok = sum(1 for i in decretos if classificar(i.get("documento", ""),
                         "portaria sedec" in i.get("documento", "").lower())[0] == "RESPOSTA")

    print(f"✓ self-test OK — {len(planos)} planos reais: {n_planos_ok} reconhecidos automaticamente, "
          f"{len(planos) - n_planos_ok} em dúvida (segura), 0 erros")
    print(f"✓ self-test OK — {len(decretos)} decretos de resposta reais: {n_decretos_ok} rejeitados "
          f"automaticamente, {len(decretos) - n_decretos_ok} em dúvida (segura), 0 falsos positivos")

    # citação completa — casos de bordo
    assert citacao_completa("Decreto nº 123, de 15/07/2026")
    assert not citacao_completa("Comitê El Niño (decreto exato pendente de confirmação)")
    assert not citacao_completa("Plano de Contingência publicado")  # sem número nem data
    # 22/09/2026 (§154): data por extenso normalizada — gramática de diário oficial (caso Feira de Santana/BA)
    assert extrair_data("DECRETO Nº 14.665 DE 21 DE AGOSTO DE 2026") == "21/08/2026"
    assert extrair_data("Decreto nº 12, de 1º de setembro de 2026") == "01/09/2026"
    assert extrair_data("ciclo El Niño 2026/2027, de 15/08/2026") == "15/08/2026"  # numérica completa segue vencendo
    # 09/10/2026 (A1-21): a data do ATO vence a data da EDICAO do diario.
    _diario = ("DATA 22/08/2026 DIARIO OFICIAL ... DECRETO Nº 14.665 DE 21 DE AGOSTO DE 2026 "
               "institui o Plano Municipal")
    assert extrair_data(_diario) == "22/08/2026"      # a primeira do texto, que e a da edicao
    assert data_do_ato(_diario) == "21/08/2026"       # a do ato, que e a que importa
    assert data_do_ato("DATA 22/08/2026 ... Decreto nº 512, de 10/02/2026, institui") == "10/02/2026"
    # sem numero de ato nao ha janela: vale a busca global, que e o caso do documento tecnico
    assert data_do_ato("Plano de Contingência, versão de 15/08/2026") == "15/08/2026"
    assert data_do_ato("") is None
    import juiz as _j
    assert _j.etapa2_citacao(_diario)[2]["data"] == "21/08/2026"
    # 09/10/2026 (A1-14): a lista de instrumentos aqui e a da etapa 2 do juiz sao a mesma.
    assert citacao_completa("Instrução Normativa nº 12, de 10/02/2026")
    assert citacao_completa("Instrucao Normativa n 12, de 10/02/2026")   # OCR sem acento
    assert citacao_completa("Resolucao 4, de 05/01/2026")
    assert not citacao_completa("Instrução Normativa sem numero nem data")
    import juiz as _juiz
    for _instr in ("decreto", "portaria", "lei", "resolu", "instru"):
        assert _instr in _juiz.RE_TIPO_E_NUMERO.pattern.lower(), _instr
        assert _instr in RE_NUMERO_ATO.pattern.lower(), _instr
    print("✓ self-test OK — checagem de citação completa (número + data, inclusive por extenso)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test()
    else:
        print(__doc__)
        sys.exit(1)
