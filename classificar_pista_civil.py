#!/usr/bin/env python3
"""
classificar_pista_civil.py
===========================
Triagem (nunca registro) das pistas de "plano de contingência" encontradas
pela varredura dos diários municipais (coletar_diarios_municipais.py). Uma
pista é um trecho de diário oficial onde a expressão aparece — pode ser um
decreto instituindo um plano municipal de defesa civil, ou pode ser uma
cláusula padrão de continuidade de serviço num contrato de TI, edital de
saúde, ou matriz de risco genérica de licitação, sem nenhuma relação com
El Niño ou defesa civil.

Esta triagem só ORDENA a fila de revisão humana — nunca decide sozinha.
"candidato_forte" e "falso_positivo_provavel" ainda exigem leitura do
documento primário antes de qualquer promoção a registro (§3.2, C10); a
regra é "na dúvida, não classifica": qualquer trecho que não bata claramente
com um dos dois lados vira "indefinido" e fica na frente da fila de revisão,
não classificado como um ou outro.

Calibrado em 03/09/2026 contra as 41 pistas reais da primeira varredura
integral (14 candidato_forte, 13 falso_positivo_provavel, 14 indefinido).
"""
import json, re, sys
from coletores_base import ler, gravar, rodar_autoteste

# Sinais de que o trecho é (ou está muito perto de ser) o ATO que institui,
# aprova ou publica um plano de contingência de defesa civil/desastres.
SINAIS_FORTES = [
    r"fica institu[íi]do",
    r"institui\s+(?:o\s+)?(?:placom|plancon|o\s+plano)",
    r"aprova[çc][ãa]o\s+(?:do\s+|de\s+)?plano\s+(?:municipal\s+)?de\s+conting[êe]ncia",
    r"aprova(?:r|do)?\s+(?:e\s+institui\s+)?o\s+plano\s+(?:municipal\s+)?de\s+conting[êe]ncia",
    r"extrato do plano de conting[êe]ncia",
    r"plano de conting[êe]ncia de prote[çc][ãa]o e defesa",
    r"opera[çc][ãa]o (estiagem|sem fogo)",
    r"estabelece o plano de conting[êe]ncia",
    r"decreto\s+n[º°ºo\.]*\s*[\d\.\-\/]+.{0,150}(institui|aprova).{0,80}plano",
]

# Sinais de que o trecho vem de um contexto administrativo SEM relação com
# defesa civil/El Niño: cláusula padrão de contrato de TI, edital de saúde
# ou obra, matriz de risco genérica, plano setorial não climático, etc.
SINAIS_FRACOS = [
    r"termo de refer[êe]ncia",
    r"continuidade (?:do\s+)?servi[çc]o",
    r"backup|c[óo]pias? de seguran[çc]a|recupera[çc][ãa]o das informa[çc][õo]es",
    r"matriz de riscos",
    r"sandbox|descontinuidade ordenada",
    r"transporte escolar",
    r"s[íi]ndrome grip",
    r"aus[êe]ncia de plano",
    r"o documento dever[áa] conter",
    r"crmv|veterin[áa]ri",
    r"experimenta[çc][ãa]o|ciclo experimental",
]


# ---------------------------------------------------------------------------
# Duas decisões editoriais de 03/09/2026 (registro em METODOLOGIA §5.2.1-bis):
#
# (1) AUTORIDADE. Só ato do EXECUTIVO (decreto, portaria, lei sancionada)
#     institui um plano para o componente pontuado. Aprovação por COLEGIADO
#     (conselho municipal, câmara) não é ato instituinte: conselho de SAÚDE
#     aprovando plano → camada observada de saúde (§9, peso zero); câmara ou
#     outro colegiado → pista "executivo pendente" até aparecer o decreto.
#
# (2) OBJETO (família de risco). O ciclo tem três famílias COBRADE declaradas
#     (§5.2.1: seca/estiagem/fogo; chuvas/inundação/deslizamento; multirrisco).
#     Plano cujo risco é outro (frio, baixas temperaturas, geada; epidemia,
#     arboviroses, gripe) falha o teste do objeto: fica VISÍVEL como pista
#     "fora do objeto", nunca pontua, nunca se apaga.
# ---------------------------------------------------------------------------

SINAIS_EXECUTIVO = [
    r"\bdecreto\b",
    r"\bportaria\b",
    r"gabinete do prefeito",
    r"\bo prefeito\b.{0,80}\bdecreta\b",
    r"lei municipal n[º°o\.]*\s*[\d\.]+.{0,60}(institui|aprova)",
    r"art\.?\s*1[ºo°]?\b.{0,40}fica institu",          # texto articulado de norma (decreto/lei): "Art. 1º Fica instituído…"
    r"coordenadoria municipal de prote[çc][ãa]o|\bcompdec\b|\bcomdec\b",  # órgão do Executivo (o trecho pode cortar antes de 'e Defesa Civil')
]
SINAIS_COLEGIADO = [
    r"conselho municipal",
    r"c[âa]mara municipal",
    r"\bpauta\b",
    r"\bresolve\b.{0,40}aprovar",
    r"\bresolu[çc][ãa]o\b",
    r"reuni[ãa]o (ordin[áa]ria|extraordin[áa]ria)",
]
SINAIS_SAUDE = [
    r"conselho municipal de sa[úu]de",
    r"programa[çc][ãa]o anual de sa[úu]de|\bPAS\b",
    r"arbovirose|dengue|chikungunya|zika",
    r"secretaria (municipal )?de sa[úu]de",
]

FAMILIAS_EL_NINO = [
    r"\bseca\b|estiagem",
    r"chuva|inunda[çc]|alagamento|enxurrada|enchente|deslizamento|escorregamento",
    r"\bcalor\b|onda de calor",
    r"queimad|inc[êe]ndio|\bfogo\b",
    r"desastre|prote[çc][ãa]o e defesa civil|defesa civil",
    r"el ni[ñn]o",
]
FORA_DO_OBJETO = [
    r"\bfrio\b|baixas? temperaturas?|\bgeada\b|onda de frio",
    r"gripal|\bgripe\b|epidemi|pandemi|\bcovid\b|influenza",
    r"arbovirose|dengue|chikungunya|zika",
]


def classificar_autoridade(trecho: str) -> str:
    """'executivo' | 'colegiado' | 'indefinido' — quem assina o ato, pelo que o trecho mostra."""
    t = normalizar(trecho)
    ex = any(re.search(p, t) for p in SINAIS_EXECUTIVO)
    co = any(re.search(p, t) for p in SINAIS_COLEGIADO)
    if ex and not co:
        return "executivo"
    if co and not ex:
        return "colegiado"
    return "indefinido"


def classificar_objeto(trecho: str) -> str:
    """'el_nino' | 'fora_do_objeto' | 'misto' | 'indefinido' — família de risco do plano (§5.2.1)."""
    t = normalizar(trecho)
    dentro = any(re.search(p, t) for p in FAMILIAS_EL_NINO)
    fora = any(re.search(p, t) for p in FORA_DO_OBJETO)
    if dentro and not fora:
        return "el_nino"
    if fora and not dentro:
        return "fora_do_objeto"
    if dentro and fora:
        return "misto"
    return "indefinido"


def eh_contexto_saude(trecho: str) -> bool:
    t = normalizar(trecho)
    return any(re.search(p, t) for p in SINAIS_SAUDE)


def destino_pista(triagem: str, autoridade: str, objeto: str, saude: bool) -> str:
    """Para onde a pista vai SE confirmada por leitura humana. Nunca promove sozinho.
    'registro_defesa_civil'   → candidata ao componente pontuado (exige leitura + citação completa)
    'camada_saude'            → camada observada de saúde (§9, peso zero)
    'pista_executivo_pendente'→ aprovada por colegiado; falta o ato do Executivo
    'fora_do_objeto'          → risco fora das famílias do ciclo; visível, nunca pontua
    'indefinido'              → leitura humana decide tudo"""
    if objeto == "fora_do_objeto":
        return "fora_do_objeto"
    if autoridade == "colegiado":
        return "camada_saude" if saude else "pista_executivo_pendente"
    if saude and objeto in ("misto", "indefinido"):
        return "camada_saude"
    if autoridade == "executivo" and objeto == "el_nino" and triagem == "candidato_forte":
        return "registro_defesa_civil"
    return "indefinido"


def triagem_completa(trecho: str) -> dict:
    """Todos os campos de triagem de uma pista, de uma vez (usado pelo coletor e pela retriagem)."""
    tri = triagem_pista(trecho)
    aut = classificar_autoridade(trecho)
    obj = classificar_objeto(trecho)
    sau = eh_contexto_saude(trecho)
    return {"triagem": tri, "autoridade": aut, "objeto": obj, "destino": destino_pista(tri, aut, obj, sau)}


def normalizar(trecho: str) -> str:
    """Colapsa quebras de linha e espaços (o PDF do diário quebra palavras no meio)."""
    return re.sub(r"\s+", " ", (trecho or "").replace("-\n", "")).lower()


def triagem_pista(trecho: str) -> str:
    """'candidato_forte' | 'falso_positivo_provavel' | 'indefinido' (padrão seguro)."""
    t = normalizar(trecho)
    forte = any(re.search(p, t) for p in SINAIS_FORTES)
    fraco = any(re.search(p, t) for p in SINAIS_FRACOS)
    if forte and not fraco:
        return "candidato_forte"
    if fraco and not forte:
        return "falso_positivo_provavel"
    return "indefinido"


def retriar_arquivo() -> int:
    """(Re)aplica a triagem completa a todas as pistas de origem querido_diario que ainda
    não tenham todos os campos (triagem, autoridade, objeto, destino)."""
    p = ler("pistas_imprensa.json", {"_governanca": "", "pistas": []})
    n = 0
    for item in p.get("pistas", []):
        if item.get("origem") == "querido_diario" and not all(k in item for k in ("triagem", "autoridade", "objeto", "destino")):
            item.update(triagem_completa(item.get("trecho", "")))
            n += 1
    gravar("pistas_imprensa.json", p)
    print(f"triagem completa aplicada a {n} pista(s)")
    return 0


def autoteste() -> int:
    def t1():  # decreto que institui plano → candidato forte
        return triagem_pista("DECRETO Nº 021, DE 10 DE JULHO DE 2026.\n―Institui o PLACOM – Plano de Contingência\nMunicipal") == "candidato_forte"

    def t2():  # câmara aprova o plano municipal de contingência → candidato forte
        return triagem_pista("PAUTA: 2 – Apreciação e aprovação do Plano Municipal de\nContingência de desastres 2026-2028") == "candidato_forte"

    def t3():  # cláusula de TI/continuidade de serviço → falso positivo provável
        return triagem_pista("III – continuidade e contingência: manutenção de plano de\ncontinuidade do serviço e de plano de contingência operacional") == "falso_positivo_provavel"

    def t4():  # matriz de riscos genérica de licitação → falso positivo provável
        return triagem_pista("Matriz de Riscos contendo: VI – medida preventiva; VII – plano de contingência; VIII – responsáveis") == "falso_positivo_provavel"

    def t5():  # trecho ambíguo (competência de elaborar PLANCON, sem confirmar que existe) → indefinido
        return triagem_pista("elaborar, manter atualizado e implementar o Plano de Contingência Municipal (PLANCON)") == "indefinido"

    def t6():  # negativo: trecho vazio não quebra, vira indefinido
        return triagem_pista("") == "indefinido"

    def t7():  # quebra de linha no meio da palavra-chave não engana o normalizador
        return triagem_pista("Nomeia os membros e estabelece o Plano de\nContingência – 2026") == "candidato_forte"

    def t8():  # negativo: nunca os dois lados ao mesmo tempo — no empate, fica indefinido
        return triagem_pista("Fica instituído o Plano de Contingência (matriz de riscos em anexo)") == "indefinido"

    def t9():  # DECISÃO 1: conselho de saúde aprovando plano de desastres → camada saúde, não componente pontuado
        r = triagem_completa("PAUTA: 1 – Apreciação e aprovação da Programação Anual de Saúde – PAS 2027; "
                             "2 – Apreciação e aprovação do Plano Municipal de Contingência de desastres 2026-2028 "
                             "e Plano de Contingência das Arboviroses 2026-2028")
        return r["autoridade"] == "colegiado" and r["destino"] == "camada_saude"

    def t10():  # DECISÃO 1b: câmara aprova por resolução, sem decreto → executivo pendente
        r = triagem_completa("A Câmara Municipal, em reunião ordinária, RESOLVE aprovar o Plano Municipal de Contingência de desastres")
        return r["autoridade"] == "colegiado" and r["destino"] == "pista_executivo_pendente"

    def t11():  # DECISÃO 2: plano para baixas temperaturas → fora do objeto (família de risco fora do ciclo)
        r = triagem_completa("Nomeia os membros do Comitê Permanente de Gestão em Situações de Baixas Temperaturas "
                             "e estabelece o Plano de Contingência – 2026")
        return r["objeto"] == "fora_do_objeto" and r["destino"] == "fora_do_objeto"

    def t12():  # decreto do Executivo instituindo plano de estiagem → candidato ao componente pontuado
        r = triagem_completa("DECRETO MUNICIPAL Nº 021, DE 10 DE JULHO DE 2026. Institui o PLACOM – Plano de Contingência Municipal para Estiagem e Seca")
        return r["autoridade"] == "executivo" and r["objeto"] == "el_nino" and r["destino"] == "registro_defesa_civil"

    def t13():  # negativo: sem sinal de autoridade nem de família → tudo indefinido, nunca promovido
        r = triagem_completa("plano de contingência")
        return r["autoridade"] == "indefinido" and r["destino"] == "indefinido"

    def t14():  # negativo: fora do objeto vence mesmo com decreto do Executivo (não pontua nunca)
        r = triagem_completa("DECRETO Nº 10, DE 2026. Institui o Plano de Contingência para Ondas de Frio e Geadas")
        return r["destino"] == "fora_do_objeto"

    return rodar_autoteste({
        "DECISÃO 1: conselho de saúde aprova plano de desastres → camada saúde": t9,
        "DECISÃO 1b: câmara aprova sem decreto → executivo pendente": t10,
        "DECISÃO 2: plano de baixas temperaturas → fora do objeto": t11,
        "decreto do Executivo, estiagem → candidato ao componente pontuado": t12,
        "negativo: sem sinais → indefinido, nunca promovido": t13,
        "negativo: fora do objeto vence mesmo com decreto": t14,
        "decreto que institui plano: candidato forte": t1,
        "câmara aprova plano municipal: candidato forte": t2,
        "cláusula de TI/continuidade de serviço: falso positivo": t3,
        "matriz de riscos de licitação: falso positivo": t4,
        "competência de elaborar PLANCON sem confirmar existência: indefinido": t5,
        "negativo: trecho vazio não quebra": t6,
        "quebra de linha na palavra-chave não engana o normalizador": t7,
        "negativo: sinal forte e fraco juntos ficam indefinido (nunca decide sozinho)": t8,
    })


if __name__ == "__main__":
    if "--autoteste" in sys.argv:
        sys.exit(autoteste())
    sys.exit(retriar_arquivo())
