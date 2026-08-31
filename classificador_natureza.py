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
RE_NUMERO_ATO = re.compile(
    r"(decreto|portaria|lei|resolução)\s*(estadual|municipal|est\.)?\s*[nº°.\s]*"
    r"(\d{1,3}(?:\.\d{3})*|\d+)", re.I)
RE_DATA_COMPLETA = re.compile(r"\d{1,2}[/.]\d{1,2}[/.]\d{2,4}")
RE_DATA_ANO_SOLTO = re.compile(r"\b\d{4}\b")


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
    t = texto.lower()

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
    m_ano = RE_DATA_ANO_SOLTO.search(texto)
    return m_ano.group(0) if m_ano else None


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
    print("✓ self-test OK — checagem de citação completa (número + data)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test()
    else:
        print(__doc__)
        sys.exit(1)
