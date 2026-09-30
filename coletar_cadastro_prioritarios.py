#!/usr/bin/env python3
"""Cadastro federal de municípios suscetíveis a enxurradas e inundações — fonte: Casa Civil.

Tarefa A do handover de 30/09/2026.

O NOME IMPORTA, E A CONFERÊNCIA JURÍDICA DA CENTRAL EXPLICOU POR QUÊ
--------------------------------------------------------------------
Esta lista **não é** o "Cadastro Nacional de Municípios com Áreas Suscetíveis" do art. 3º-A da Lei
12.340. São dois cadastros distintos, e o próprio Decreto 12.444/2025 diz isso ao ressalvar que o
outro "permanece disciplinado por regulamento próprio".

  * **O que este coletor lê** — cadastro de municípios suscetíveis a **enxurradas e inundações**,
    publicado pela SEPAC/Casa Civil (Decreto 12.444/2025, regulamento do art. 50 da Lei 11.445/2007,
    de saneamento). Identificação por sete critérios técnicos, sem pedido do município; serve para
    afastar condicionantes de recursos federais de drenagem. **Não gera dever de plano de
    contingência.**
  * **O que ele NÃO lê** — o cadastro do art. 3º-A, de inscrição voluntária, que inclui
    deslizamentos e **esse sim** gera o dever de plano. Não tem consulta pública; só a LAI ao
    MIDR/SEDEC chega nele, e por isso **o pedido de LAI continua necessário** — o handover original
    dizia que ele tinha perdido o objeto, e a conferência jurídica corrigiu.

Por isso o campo do art. 3º-A nasce vazio aqui: quando a LAI responder, ele recebe
`cadastro_nacional_art3A`. Confundir os dois no site seria afirmar dever legal que esta lista não
cria.

AS TRÊS CONTAGENS
-----------------
1.942 (NT 1/2023, base 1991–2022) + 153 (NT 1/2025, base até 2024) = **2.095** prioritários
geo-hidrológicos; menos os **9** que só têm risco de deslizamento — fora do escopo da Lei 11.445 —
= **2.086** no cadastro publicado. O universo do MARÉ é 2.095; 2.086 é o subconjunto com efeito na
lei. Os dois ficam gravados, por município.

PESO ZERO
---------
Camada de contexto: não escreve em `estados.json`, `indice.json`, `saude_uf.json` nem
`monitor_saude.json`, e não pontua. Prioridade federal não é preparação.

USO
  python3 coletar_cadastro_prioritarios.py --autoteste
  python3 coletar_cadastro_prioritarios.py
"""
import io
import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

BASE = ("https://www.gov.br/casacivil/pt-br/assuntos/"
        "cadastro-de-municipios-suscetiveis-a-eventos-de-enxurradas-e-inundacoes/")
FONTES = {
    "nt2_2025": BASE + "copy2_of_NotaTecnica2.2025_SADJVISEPAC.pdf",
    "nt1_2025": BASE + "NotaTecnica1.2025_SADJVISEPACCCeAnexoI.pdf",
    "nt1_2023": BASE + "copy10_of_NotaTcnica01_2023_SAM_CC_PR_eAnexosIeII.pdf",
}
SAIDA = RAIZ / "data" / "cadastro_prioritarios_federal.json"
MUNICIPIOS = RAIZ / "data" / "verificacao_municipal.json"

TOTAL_CADASTRO = 2086
TOTAL_PRIORITARIOS = 2095
TOTAL_SO_DESLIZAMENTO = 9
# Conferência de distribuição: números do próprio handover, que os leu no anexo.
POR_UF_ESPERADO = {"DF": 1, "RR": 5, "AC": 20, "AL": 47}

UFS = {"AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PA", "PB",
       "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO"}

GOVERNANCA = (
    "Cadastro federal de municípios suscetíveis a ENXURRADAS E INUNDAÇÕES, publicado pela "
    "SEPAC/Casa Civil (Decreto 12.444/2025, regulamento do art. 50 da Lei 11.445/2007). NÃO é o "
    "'Cadastro Nacional de Municípios com Áreas Suscetíveis' do art. 3º-A da Lei 12.340, que é de "
    "inscrição voluntária, inclui deslizamentos e gera o dever de plano de contingência — esse "
    "outro não tem fonte pública e depende do pedido de LAI ao MIDR/SEDEC, que continua de pé. "
    "Camada de contexto, PESO ZERO: não pontua e não entra no índice."
)


def linhas_do_anexo(texto: str) -> list:
    """[(item, uf, municipio, ibge)] das linhas `item · UF · município · código`. Função pura.

    O PDF quebra cada campo em uma linha. Nome longo vem partido em duas ou mais, então junta-se o
    que houver entre a UF e o código — que é o delimitador confiável, por ser sempre 7 dígitos."""
    linhas = [l.strip() for l in (texto or "").split("\n")]
    fora, i = [], 0
    while i < len(linhas):
        if not linhas[i].isdigit() or len(linhas[i]) > 5:
            i += 1
            continue
        item = int(linhas[i])
        if i + 1 >= len(linhas) or linhas[i + 1] not in UFS:
            i += 1
            continue
        uf = linhas[i + 1]
        partes, j = [], i + 2
        while j < len(linhas) and not (linhas[j].isdigit() and len(linhas[j]) == 7):
            if linhas[j] in UFS or (linhas[j].isdigit() and len(linhas[j]) <= 5):
                break          # entrou na próxima linha da tabela: esta está truncada
            partes.append(linhas[j])
            j += 1
        if j < len(linhas) and linhas[j].isdigit() and len(linhas[j]) == 7 and partes:
            fora.append((item, uf, " ".join(partes).strip(), linhas[j]))
            i = j + 1
            continue
        i += 1
    return fora


# A Tabela 1 INVERTE as colunas do anexo: lá é `item · UF · município · código`, aqui é
# `item · município · UF · código · população`. Ler as duas com o mesmo leitor devolvia zero — e a
# validação recusou gravar, que é o comportamento certo, mas a causa era esta.
RE_TABELA_1 = re.compile(r"\n(\d{1,2})\n([^\n]+)\n([A-Z]{2})\n(\d{7})\n")


def apenas_deslizamento(texto: str) -> set:
    """Os códigos IBGE da Tabela 1 (municípios só com risco de deslizamento). Função pura.

    Eles ficam FORA do cadastro publicado porque a Lei 11.445 trata de enxurrada e inundação — mas
    continuam prioritários no universo de 2.095, e é por isso que se guardam os dois flags.

    A leitura do PDF é conferida contra a lista nomeada no handover: o PDF é a fonte, e a lista
    conferida é a trava. Se a nota mudar, a diferença aparece na validação em vez de passar."""
    conhecidos = {"3501152", "3528403", "3536000", "3521309", "3143153", "3130101",
                  "1504307", "1502103", "5200308"}
    achados = {m.group(4) for m in RE_TABELA_1.finditer(texto or "") if m.group(3) in UFS}
    return achados & conhecidos


# A NT 1/2025 traz tudo numa linha: `item · código · UF · município · população · … · riscos`. É
# dela que saem os 153 complementares E os tipos de risco de cada um — ler o risco daqui, e não de
# uma varredura solta por código, evita casar um número com o texto do município seguinte.
RE_COMPLEMENTAR = re.compile(r"(\d{7})\s+([A-Z]{2})\s+([^\d]{2,60}?)\s+[\d.]+\s")

TIPOS_CONHECIDOS = (("enxurrada", "enxurrada"), ("inundação", "inunda"),
                    ("deslizamento", "deslizam"), ("alagamento", "alagam"))


def riscos_por_codigo(texto: str) -> dict:
    """{ibge: [tipos de risco]} lido da nota. Função pura.

    O risco é lido no trecho que vem DEPOIS do código e antes do próximo código — a nota lista os
    tipos logo após a população, um por linha. Só se extrai o que a nota escreve, sem inferir: um
    município sem tipo nomeado fica sem tipo, não com lista vazia por suposição."""
    fora = {}
    achados = list(re.finditer(r"\b(\d{7})\b", texto or ""))
    for i, m in enumerate(achados):
        fim = achados[i + 1].start() if i + 1 < len(achados) else min(len(texto), m.end() + 200)
        trecho = (texto[m.end():fim] or "").lower()
        tipos = [t for t, chave in TIPOS_CONHECIDOS if chave in trecho]
        if tipos:
            fora[m.group(1)] = sorted(set(tipos))
    return fora


def complementares_de(texto: str) -> set:
    """Os códigos IBGE dos municípios acrescentados em 2025. Função pura."""
    return {m.group(1) for m in RE_COMPLEMENTAR.finditer(texto or "") if m.group(2) in UFS}


def juntar(cadastro: list, complementares: set, so_deslizamento: set, riscos: dict) -> dict:
    """{ibge: registro} com os dois flags e o que a fonte disser. Função pura."""
    fora = {}
    for _item, uf, nome, ibge in cadastro:
        fora[ibge] = {"codigo_ibge": ibge, "uf": uf, "municipio": nome,
                      "prioritario_2095": True, "cadastro_casa_civil_2086": True,
                      "apenas_deslizamento": False,
                      "acrescido_em": 2025 if ibge in complementares else None,
                      "tipos_de_risco": riscos.get(ibge) or [],
                      # Preenchido só quando a LAI ao MIDR/SEDEC responder: é outro cadastro.
                      "cadastro_nacional_art3A": None}
    for ibge in so_deslizamento:
        fora.setdefault(ibge, {"codigo_ibge": ibge, "uf": "", "municipio": "",
                               "tipos_de_risco": ["deslizamento"],
                               "cadastro_nacional_art3A": None})
        # O ano vale para ELE também: três dos nove excluídos (Cametá, Maracanã e Igarapé) são
        # complementares de 2025, e a primeira versão os deixava sem ano — 150 marcados onde a nota
        # traz 153. Estar fora do cadastro por ser só deslizamento não apaga quando ele entrou.
        fora[ibge].update({"prioritario_2095": True, "cadastro_casa_civil_2086": False,
                           "apenas_deslizamento": True,
                           "acrescido_em": 2025 if ibge in complementares else
                           fora[ibge].get("acrescido_em")})
    return fora


def problemas(registros: dict, codigos_do_pais: set) -> list:
    """As validações obrigatórias do handover. Falha = não grava. Função pura."""
    ruins = []
    no_cadastro = [r for r in registros.values() if r.get("cadastro_casa_civil_2086")]
    so_desl = [r for r in registros.values() if r.get("apenas_deslizamento")]
    if len(no_cadastro) != TOTAL_CADASTRO:
        ruins.append(f"cadastro publicado tem {len(no_cadastro)} municípios, e são {TOTAL_CADASTRO}")
    if len(so_desl) != TOTAL_SO_DESLIZAMENTO:
        ruins.append(f"{len(so_desl)} municípios só de deslizamento, e são {TOTAL_SO_DESLIZAMENTO}")
    if len(registros) != TOTAL_PRIORITARIOS:
        ruins.append(f"{len(registros)} prioritários no total, e são {TOTAL_PRIORITARIOS} "
                     f"({TOTAL_CADASTRO} + {TOTAL_SO_DESLIZAMENTO})")
    if codigos_do_pais:
        fantasmas = sorted(set(registros) - codigos_do_pais)
        if fantasmas:
            ruins.append(f"{len(fantasmas)} código(s) que não existem na base do projeto: "
                         f"{fantasmas[:5]}")
    for uf, esperado in POR_UF_ESPERADO.items():
        visto = sum(1 for r in no_cadastro if r.get("uf") == uf)
        if visto != esperado:
            ruins.append(f"{uf}: {visto} no cadastro, e a nota traz {esperado}")
    return ruins


def autoteste() -> int:
    casos = []
    pagina = ("14\nAC\nRio Branco\n1200401\n15\nAC\nRodrigues Alves\n1200427\n"
              "21\nAL\nBarra de Santo Antônio\n2700508\n")
    ls = linhas_do_anexo(pagina)
    casos.append(("lê três linhas do anexo", len(ls) == 3))
    casos.append(("item, UF, nome e código saem certos",
                  ls[0] == (14, "AC", "Rio Branco", "1200401")))
    casos.append(("nome com espaços não se perde",
                  ls[2][2] == "Barra de Santo Antônio"))
    partido = "30\nMG\nSão João\ndo Paraíso\n3162807\n"
    casos.append(("nome quebrado em duas linhas é juntado",
                  linhas_do_anexo(partido) == [(30, "MG", "São João do Paraíso", "3162807")]))
    casos.append(("texto sem tabela devolve vazio", linhas_do_anexo("Nota Técnica nº 2") == []))
    casos.append(("texto nulo não quebra", linhas_do_anexo(None) == []))
    casos.append(("sigla que não é UF não vira linha",
                  linhas_do_anexo("1\nXX\nLugar\n1234567\n") == []))
    casos.append(("código de 6 dígitos não é IBGE",
                  linhas_do_anexo("1\nAC\nLugar\n123456\n") == []))

    t1 = "\n1\nAlumínio\nSP\n3501152\n17.301\n2\nMairinque\nSP\n3528403\n49.972\n"
    casos.append(("acha os da Tabela 1, que tem as colunas invertidas",
                  apenas_deslizamento(t1) == {"3501152", "3528403"}))
    casos.append(("município fora da lista conferida não entra",
                  apenas_deslizamento("\n1\nRio Branco\nAC\n1200401\n0\n") == set()))
    casos.append(("o leitor do anexo NÃO lê a Tabela 1 (a ordem das colunas é outra)",
                  linhas_do_anexo(t1) == []))

    r = riscos_por_codigo("3501152 enxurrada e deslizamento no município")
    casos.append(("lê os tipos de risco que a nota escreve",
                  r.get("3501152") == ["deslizamento", "enxurrada"]))
    casos.append(("não inventa risco onde a nota não diz",
                  riscos_por_codigo("3501152 município do interior") == {}))
    casos.append(("o risco de um não vaza para o código seguinte",
                  riscos_por_codigo("1200401 enxurrada 3501152 nada aqui").get("3501152") is None))
    linha = "4 2906808 BA Cansanção 37.439                   -    Enxurrada  \n"
    casos.append(("lê o complementar na linha corrida da nota de 2025",
                  complementares_de(linha) == {"2906808"}))
    casos.append(("e o risco dele junto",
                  riscos_por_codigo(linha).get("2906808") == ["enxurrada"]))
    casos.append(("sigla que não é UF não vira complementar",
                  complementares_de("4 2906808 XX Lugar 1.000  ") == set()))

    cad = [(1, "AC", "Rio Branco", "1200401"), (2, "SP", "Santos", "3548500")]
    j = juntar(cad, {"3548500"}, {"3501152"}, {"1200401": ["enxurrada"]})
    casos.append(("quem está no cadastro leva os dois flags",
                  j["1200401"]["cadastro_casa_civil_2086"] is True
                  and j["1200401"]["prioritario_2095"] is True))
    casos.append(("o complementar é marcado com o ano", j["3548500"]["acrescido_em"] == 2025))
    casos.append(("quem não é complementar fica sem ano",
                  j["1200401"]["acrescido_em"] is None))
    j2 = juntar([], {"1502103"}, {"1502103"}, {})
    casos.append(("excluído que também é complementar mantém o ano de entrada",
                  j2["1502103"]["acrescido_em"] == 2025))
    casos.append(("e continua fora do cadastro publicado",
                  j2["1502103"]["cadastro_casa_civil_2086"] is False))
    casos.append(("o só-deslizamento é prioritário mas NÃO está no cadastro publicado",
                  j["3501152"]["prioritario_2095"] is True
                  and j["3501152"]["cadastro_casa_civil_2086"] is False))
    casos.append(("o campo do art. 3º-A nasce vazio, porque é outro cadastro",
                  all(v["cadastro_nacional_art3A"] is None for v in j.values())))
    casos.append(("o tipo de risco vem da nota", j["1200401"]["tipos_de_risco"] == ["enxurrada"]))

    bom = {str(1000000 + i): {"cadastro_casa_civil_2086": True, "apenas_deslizamento": False,
                              "uf": "AC" if i < 20 else "XX"} for i in range(TOTAL_CADASTRO)}
    bom.update({str(9000000 + i): {"cadastro_casa_civil_2086": False, "apenas_deslizamento": True,
                                   "uf": ""} for i in range(TOTAL_SO_DESLIZAMENTO)})
    p = problemas(bom, set())
    casos.append(("contagem certa passa nas três somas",
                  not any("no total" in x or "só de deslizamento" in x
                          or "cadastro publicado tem" in x for x in p)))
    faltando = dict(list(bom.items())[:-1])
    casos.append(("contagem errada reprova", len(problemas(faltando, set())) >= 1))
    casos.append(("código fora da base do país reprova",
                  any("não existem na base" in x for x in problemas({"9999999": {
                      "cadastro_casa_civil_2086": True, "apenas_deslizamento": False, "uf": "AC"}},
                      {"1200401"}))))
    casos.append(("distribuição por UF fora do esperado reprova",
                  any("no cadastro, e a nota traz" in x for x in problemas(bom, set()))))

    casos.append(("a governança diz que NÃO é o Cadastro Nacional do art. 3º-A",
                  "NÃO é o 'Cadastro Nacional" in GOVERNANCA))
    casos.append(("e diz que a LAI continua de pé", "continua de pé" in GOVERNANCA))
    casos.append(("e declara peso zero", "PESO ZERO" in GOVERNANCA))

    ruins = [n for n, ok in casos if not ok]
    for n, ok in casos:
        print(f"  {'OK  ' if ok else 'FALHA'} {n}")
    if ruins:
        print(f"X AUTOTESTE: {len(ruins)} caso(s) reprovado(s).")
        return 1
    print(f"OK AUTOTESTE — {len(casos)} casos, sem rede e sem escrita.")
    return 0


def texto_do_pdf(corpo: bytes) -> str:
    import pypdf
    r = pypdf.PdfReader(io.BytesIO(corpo))
    return "\n".join((p.extract_text() or "") for p in r.pages)


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()

    from coletores_base import buscar, gravar_em, hoje_editorial, preservar_evidencia
    hoje = hoje_editorial()
    textos, hashes = {}, {}
    for nome, url in FONTES.items():
        corpo = buscar(url, timeout=120, origem="coletar_cadastro_prioritarios")
        hashes[nome] = preservar_evidencia(corpo, url, "pdf", "coletar_cadastro_prioritarios")
        textos[nome] = texto_do_pdf(corpo)
        print(f"{nome}: {len(corpo)} bytes · evidência {hashes[nome][:12]}")

    cadastro = linhas_do_anexo(textos["nt2_2025"])
    so_desl = apenas_deslizamento(textos["nt2_2025"])
    cadastro = [l for l in cadastro if l[3] not in so_desl]
    complementares = complementares_de(textos["nt1_2025"])
    # O tipo de risco vem das DUAS notas: a de 2025 traz os complementares, a de 2023 os
    # originais. A de 2023 entra primeiro para a de 2025 poder corrigi-la, por ser mais nova.
    riscos = riscos_por_codigo(textos["nt1_2023"])
    riscos.update(riscos_por_codigo(textos["nt1_2025"]))
    print(f"anexo: {len(cadastro)} · só deslizamento: {len(so_desl)} · "
          f"complementares: {len(complementares)} · com risco nomeado: {len(riscos)}")

    registros = juntar(cadastro, complementares, so_desl, riscos)
    do_pais = set()
    if MUNICIPIOS.exists():
        do_pais = {str(m["ibge"]).zfill(7)
                   for m in json.loads(MUNICIPIOS.read_text(encoding="utf-8")) if m.get("ibge")}
    ruins = problemas(registros, do_pais)
    if ruins:
        print("X VALIDAÇÃO — nada foi gravado:")
        for r in ruins:
            print("   -", r)
        return 1

    gravar_em(SAIDA, {"_governanca": GOVERNANCA, "fonte": BASE, "coletado_em": hoje.isoformat(),
                      "evidencias": hashes, "totais": {"prioritarios_2095": TOTAL_PRIORITARIOS,
                                                       "cadastro_2086": TOTAL_CADASTRO,
                                                       "apenas_deslizamento": TOTAL_SO_DESLIZAMENTO},
                      "municipios": registros})          # §229
    print(f"{SAIDA.relative_to(RAIZ)} gravado · {len(registros)} municípios")
    return 0


if __name__ == "__main__":
    sys.exit(main())
