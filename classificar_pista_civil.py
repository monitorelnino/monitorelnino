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
    """Aplica a triagem a todas as pistas já registradas (origem querido_diario) que ainda não a têm."""
    p = ler("pistas_imprensa.json", {"_governanca": "", "pistas": []})
    n = 0
    for item in p.get("pistas", []):
        if item.get("origem") == "querido_diario" and "triagem" not in item:
            item["triagem"] = triagem_pista(item.get("trecho", ""))
            n += 1
    gravar("pistas_imprensa.json", p)
    print(f"triagem aplicada a {n} pista(s) sem classificação prévia")
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

    return rodar_autoteste({
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
