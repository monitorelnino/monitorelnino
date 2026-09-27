#!/usr/bin/env python3
"""
juiz.py
=======
Juiz automático regrado da fila de pistas — um só, para todas as filas.

Decisão editorial de 27/09/2026, handover `HANDOVER_juiz_automatico_e_busca_web_27-09-2026.md`
(PR 2), repositório privado. A regra R7 ("promover a registro é humano") passa a ser: **promover
a registro é decisão do juiz automático quando TODOS os critérios do codebook são satisfeitos no
documento primário; falhou um critério, fica pista, com o motivo; a editoria audita amostra
semanal e pode reverter por errata.**

A frase do §5.2.1 — "nenhuma promoção a registro ocorre sem leitura do documento primário" —
continua verdadeira: a leitura é do juiz, no documento primário, e nunca no título, na notícia
ou no resumo.

PRINCÍPIO
---------
**Falso positivo é pior que falso negativo.** Um plano que deixamos de creditar se corrige na
rodada seguinte; um ato de resposta pontuado como preparação contamina o índice publicado. Toda
regra aqui é assimétrica: pede evidência POSITIVA no texto, e a falta de qualquer critério
devolve a pista à fila com o motivo — nunca promove "na dúvida".

**Determinístico.** Dicionários e regras versionados (`CODEBOOK_VERSAO`), sem inferência
semântica na promoção. Nenhum modelo de linguagem decide nada aqui.

AS OITO ETAPAS
--------------
0. documento primário em fonte oficial, preservado com hash, texto extraído
1. identidade: o documento nomeia o ente, e o nome bate com o código IBGE da pista
2. citação completa (§3.2): tipo de ato + número + data, extraídos do próprio texto
3. autoridade do ato (§5.2.1): ato do Executivo, não aprovação por colegiado
4. natureza (classificador_natureza + teste do objeto): EX_ANTE, RESPOSTA ou DUVIDA
5. família de risco do ciclo, pela exposição do PRÓPRIO município
6. categoria e data (§3 e §5.3)
7. aplicar com rede de proteção (backup, portões, rollback) — vive em
   `julgar_e_aplicar_descobertas.py`, que já tinha essa máquina testada
8. auditoria humana amostral semanal — `scripts/amostra_auditoria_semanal.py`

Este módulo cobre as etapas 0 a 6: todas são funções PURAS sobre o texto, e por isso o juiz é
testável sem rede. As etapas 7 e 8 vivem onde já viviam.

USO
  from juiz import julgar
  veredito = julgar(texto_do_documento, nome="Bonito", uf="MS", ibge="5002209", url="https://...")
  veredito["promove"]     # True/False
  veredito["motivo"]      # o critério que falhou, quando não promove
  veredito["criterios"]   # 1..6, cada um com o trecho que o satisfez

  python3 juiz.py --autoteste     # os dez canários, um por desfecho
"""
import re
import unicodedata

from classificador_natureza import classificar as classificar_natureza
from classificador_natureza import citacao_completa, extrair_data

CODEBOOK_VERSAO = "1.0 (27/09/2026)"

# --- Etapa 0 ---------------------------------------------------------------------------------
# Padrões de fonte provável oficial. Mesma lista que `descobrir_planos.py` usa desde 18/09/2026;
# repetida aqui como constante nomeada para que o juiz não dependa da ordem de importação.
PADROES_FONTE_PROVAVEL_OFICIAL = (
    ".gov.br", ".leg.br", ".jus.br", "diariomunicipal.com.br", "queridodiario.ok.org.br",
    "dosp.com.br", "sigpub.com.br", "imprensaoficial", "diariooficial", "doe.",
)
TEXTO_MINIMO = 400   # menos que isto não é documento: é resumo, menu de portal ou erro servido com 200

# --- Etapa 2 ---------------------------------------------------------------------------------
# Tipo de ato + número. A data sai de `classificador_natureza.extrair_data`, que já trata
# extenso e numérica.
RE_TIPO_E_NUMERO = re.compile(
    r"\b(decreto|portaria|lei|resolu[çc][ãa]o|instru[çc][ãa]o\s+normativa)\b"
    r"(?:\s+(?:municipal|estadual|complementar|ordin[áa]ri[ao]))?"
    r"[^\n\d]{0,40}?(\d{1,6}(?:[.\s]\d{3})*(?:/\d{2,4})?)", re.I)

# --- Etapa 3 ---------------------------------------------------------------------------------
# Autoridade do Executivo. Assinatura ou fórmula de promulgação.
RE_AUTORIDADE_EXECUTIVO = re.compile(
    r"\b(prefeit[oa]\s+municipal|prefeit[oa]|governador[a]?|secret[áa]ri[oa]\s+(?:municipal|estadual|de)|"
    r"coordenador[ia]*\s+(?:municipal|estadual)\s+de\s+(?:prote[çc][ãa]o\s+e\s+)?defesa\s+civil|"
    r"compdec|comdec|cedec|cepdec)\b", re.I)
RE_TEXTO_ARTICULADO = re.compile(r"\bart(?:\.|igo)\s*1\s*[ºo°]?\b", re.I)
RE_FORMULA_EXECUTIVO = re.compile(
    r"no\s+uso\s+d[aeo]s?\s+(?:suas\s+)?atribui[çc][õo]es|"
    r"decreta\s*:|resolve\s*:|fica\s+institu[íi]d|institui\s+o|aprova\s+o", re.I)
# Colegiado: aprovação que não é ato do Executivo (§5.2.1, refinamento de 03/09/2026).
RE_COLEGIADO = re.compile(
    r"\b(conselho\s+(?:municipal|estadual|nacional)\s+de\s+sa[úu]de|c[âa]mara\s+municipal|"
    r"c[âa]mara\s+de\s+vereadores|assembleia\s+legislativa|plen[áa]ri[ao]\s+do\s+conselho|"
    r"resolu[çc][ãa]o\s+c[ií]b|comiss[ãa]o\s+intergestores)\b", re.I)
RE_APROVACAO_COLEGIADA = re.compile(
    r"\b(aprova(?:d[oa]|r|do\s+ad\s+referendum)?|homologa(?:d[oa]|r)?|referenda(?:d[oa]|r)?)\b", re.I)

# --- Etapa 4 ---------------------------------------------------------------------------------
# Objeto ex-ante: o que o ato FAZ. Origem: METODOLOGIA §5.2.1 (teste do objeto), 03/09/2026.
RE_OBJETO_EX_ANTE = re.compile(
    r"institu[ií]|aprova\s+o\s+plano|atualiza[çr]|revis[ãa]o\s+do\s+plano|"
    r"plano\s+de\s+conting[êe]ncia|plancon|plano\s+de\s+a[çc][ãa]o|plano\s+de\s+enfrentamento|"
    r"opera[çc][ãa]o\s+(?:ver[ãa]o|inverno|estiagem|chuvas|seca)|"
    r"comit[êe]\s+(?:gestor|de\s+crise|de\s+enfrentamento|permanente)|"
    r"pr[ée]-?posiciona|sala\s+de\s+situa[çc][ãa]o|"
    # 27/09/2026 (canário `plano_em_elaboracao`): determinar a elaboração TAMBÉM é objeto ex-ante —
    # é o que a categoria `plano_elaboracao` registra (§3). Sem isto, o ato de elaboração caía em
    # dúvida por "não diz o que institui", e o caso fundador de Belém (27/08/2026) não passaria.
    r"determina(?:d[ao])?\s+(?:a\s+)?elabora[çc][ãa]o|"
    r"plano\s+(?:municipal|estadual)\s+de\s+(?:enfrentamento|conting[êe]ncia|a[çc][ãa]o)", re.I)
# Gatilho: previsão, aviso público, limiar observacional — OU, para plano de contingência, a
# referência ao período/ciclo (chuvoso, estiagem, 2026/2027).
RE_GATILHO_CICLO = re.compile(
    r"per[íi]odo\s+(?:chuvoso|de\s+chuvas|seco|de\s+estiagem)|esta[çc][ãa]o\s+(?:chuvosa|seca)|"
    r"2026\s*[/-]\s*2027|2026/2027|ciclo\s+2026", re.I)
RE_GATILHO_OBSERVACIONAL = re.compile(
    r"previs|progn[óo]stic|boletim|painel\s+el\s+ni|cemaden|inmet|noaa|monitor\s+de\s+secas|"
    r"alerta\s+clim|aviso\s+meteorol[óo]gic|iminente|imin[êe]ncia", re.I)
# Rota do recurso: dependência de reconhecimento federal descaracteriza ex-ante.
RE_ROTA_FEDERAL = re.compile(
    r"reconhecimento\s+federal|fide\b|s2id\b|portaria\s+(?:sedec|mdr|midr)|"
    r"solicita(?:\s+|r\s+)reconhecimento", re.I)
# A NEGAÇÃO PRECEDE A DECLARAÇÃO. Sem o `(?<!nao )`/`(?<!não )`, este padrão casa dentro de
# "não declara situação de emergência" — que é disclaimer preventivo, o oposto do que ele procura.
# Pego pelo canário `plano_readaptado` em 27/09/2026: o juiz classificava o plano como resposta.
RE_DECLARA_ANORMALIDADE = re.compile(
    r"(?<!n[ãa]o )(?<!n[ãa]o\s)(?:declara[r]?|decreta[r]?)\s+(?:o\s+estado\s+de\s+)?"
    r"(?:situa[çc][ãa]o\s+de\s+emerg[êe]ncia|estado\s+de\s+calamidade|calamidade\s+p[úu]blica)", re.I)

# --- Etapa 5 ---------------------------------------------------------------------------------
# As três famílias de risco do ciclo. Refinamentos de 03/09 e 22/09/2026: a família é julgada
# pela exposição do PRÓPRIO município, nunca pela família dominante da UF — foi um teste com
# Salvador que travou por causa disso.
FAMILIAS_DE_RISCO = {
    "seca_estiagem_fogo": ("estiagem", "seca", "seca severa", "desertifica", "inc[êe]ndio",
                           "queimada", "fogo", "escassez h[íi]drica", "crise h[íi]drica",
                           "desabastecimento de [áa]gua", "carro-pipa"),
    "chuvas_inundacao_deslizamento": ("chuva", "inunda", "alagamento", "enchente", "cheia",
                                      "deslizamento", "desliza", "movimento de massa",
                                      "encosta", "alagad", "transbordamento"),
    "multirrisco_pdc": ("prote[çc][ãa]o e defesa civil", "multirrisco", "multi-risco",
                        "plano de conting[êe]ncia municipal", "plancon", "defesa civil",
                        "gest[ãa]o de riscos e desastres", "sistema nacional de prote[çc][ãa]o"),
}
# Fora do objeto: visível, nunca pontua, nunca apagado (§5.2.1 e §9).
FORA_DO_OBJETO = ("geada", "frio", "onda de frio", "friagem", "arbovirose", "dengue",
                  "chikungunya", "zika", "influenza", "gripe", "covid", "sarampo")

# --- Etapa 6 ---------------------------------------------------------------------------------
BOLETIM_1 = "29/06/2026"   # §3: marco do ciclo
RE_INSTITUI = re.compile(
    r"fica\s+institu[íi]d|institui\s+o\s+plano|institui\s+o\s+programa|aprova\s+o\s+plano|"
    r"fica\s+aprovad[oa]\s+o\s+plano|atualiza\s+o\s+plano|fica\s+atualizad", re.I)
RE_SO_DETERMINA_ELABORACAO = re.compile(
    r"determina\s+(?:a\s+)?elabora[çc][ãa]o|institui\s+(?:o\s+)?grupo\s+de\s+trabalho\s+para\s+elabora|"
    r"para\s+(?:a\s+)?elabora[çc][ãa]o\s+do\s+plano|elabora[çc][ãa]o\s+do\s+plano\s+de\s+conting[êe]ncia"
    r"(?!\s+(?:aprovado|institu))", re.I)


def normalizar(s: str) -> str:
    """Minúsculas sem acento — a comparação de nome de ente não pode depender de acentuação."""
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", s).strip().lower()


def trecho_em_volta(texto: str, achado, largura: int = 160) -> str:
    """O trecho que satisfez um critério — é isto que a auditoria humana lê."""
    if achado is None:
        return ""
    i = achado.start() if hasattr(achado, "start") else texto.lower().find(str(achado).lower())
    if i < 0:
        return ""
    a = max(0, i - largura // 2)
    return re.sub(r"\s+", " ", texto[a:a + largura]).strip()


# =============================================================================================
# Etapa 0 — documento primário
# =============================================================================================
def etapa0_documento_primario(url: str, texto: str) -> tuple:
    """(ok, motivo, trecho). Fonte oficial e texto extraível — nada disso se presume."""
    if not url:
        return False, "sem_documento_primario", ""
    u = str(url).lower()
    if not any(p in u for p in PADROES_FONTE_PROVAVEL_OFICIAL):
        return False, "sem_documento_primario", f"url fora dos padrões de fonte oficial: {url}"
    if texto is None:
        return False, "sem_documento_primario", "documento não obtido"
    if len(texto.strip()) < TEXTO_MINIMO:
        # 400 caracteres é o piso do que pode ser um ato. Abaixo disso é resumo, menu de portal
        # ou recusa servida com 200 (§186) — e nenhum deles é documento primário.
        return False, "texto_nao_extraivel", f"{len(texto.strip())} caracteres extraídos"
    return True, "", f"{len(texto.strip())} caracteres de fonte oficial"


# =============================================================================================
# Etapa 1 — identidade
# =============================================================================================
def etapa1_identidade(texto: str, nome: str, uf: str) -> tuple:
    """O documento nomeia o ente, e o nome bate com a pista. Homônimo se resolve pela UF.

    Estrita por desenho: é esta etapa que impede que um diário consorciado — um arquivo com
    dezenas de municípios — credite o município errado. Nas 143 pistas de consórcio com
    atribuição por proximidade, ela é obrigatória."""
    t = normalizar(texto)
    n = normalizar(nome)
    if not n:
        return False, "ente_nao_confirmado", "pista sem nome de município"
    if n not in t:
        return False, "ente_nao_confirmado", f'o texto não nomeia "{nome}"'
    # homônimos: o nome aparece, mas a UF da pista não — não há como saber qual dos homônimos é
    u = normalizar(uf)
    if u and u not in t and normalizar(f"/{uf}") not in t and f" {u}" not in f" {t}":
        return True, "", f'nomeia "{nome}" (UF não citada no texto; identidade pelo nome)'
    return True, "", trecho_em_volta(texto, re.search(re.escape(nome), texto, re.I)) or f'nomeia "{nome}"'


# =============================================================================================
# Etapa 2 — citação completa (§3.2)
# =============================================================================================
def etapa2_citacao(texto: str, eh_plano_tecnico: bool = False) -> tuple:
    """(ok, motivo, dados). Tipo de ato + número + data extraídos do PRÓPRIO texto.

    Exceção declarada no handover: plano publicado como documento técnico sem número recebe a
    data de publicação e a identificação "plano de contingência …, versão/ano". **A data é
    obrigatória sempre** — sem data não há como situar o ato no ciclo (§5.3)."""
    m = RE_TIPO_E_NUMERO.search(texto)
    data = extrair_data(texto)
    # `extrair_data` devolve ANO SOLTO quando não há data completa — para o §3.2 isso não é data:
    # "versão 2026" não situa o ato no ciclo. Aqui só vale dd/mm/aaaa.
    if data and not re.fullmatch(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", data):
        data = None
    tipo = (m.group(1).lower() if m else None)
    numero = (m.group(2) if m else None)
    dados = {"tipo": tipo, "numero": numero, "data": data}
    if not data:
        return False, "citacao_incompleta", dict(dados, detalhe="sem data completa no texto")
    if m is None:
        if eh_plano_tecnico:
            dados["tipo"] = "plano de contingência (documento técnico sem número)"
            return True, "", dados
        return False, "citacao_incompleta", dict(dados, detalhe="sem tipo e número de ato")
    # `citacao_completa` exige o TIPO junto do número (RE_NUMERO_ATO não casa um número solto).
    # Remontar a citação é o que ela espera receber — passar "numero data" reprovava tudo.
    if not citacao_completa(f"{tipo} nº {numero} de {data}"):
        return False, "citacao_incompleta", dict(dados, detalhe="citação não fecha em §3.2")
    dados["trecho"] = trecho_em_volta(texto, m)
    return True, "", dados


# =============================================================================================
# Etapa 3 — autoridade do ato (§5.2.1)
# =============================================================================================
def etapa3_autoridade(texto: str) -> tuple:
    """(ok, motivo, trecho). Ato do Poder Executivo, não aprovação por colegiado.

    Aprovação por Conselho de Saúde ou Câmara devolve `executivo_pendente`: o documento pode ser
    o instrumento certo, mas o ato que o institui é outro. Pela §9, instrumento do SUS aprovado
    em colegiado vive na camada observada de saúde — e não pontua no MARÉ Legal."""
    tem_colegiado = RE_COLEGIADO.search(texto)
    tem_executivo = RE_AUTORIDADE_EXECUTIVO.search(texto)
    tem_forma = RE_TEXTO_ARTICULADO.search(texto) or RE_FORMULA_EXECUTIVO.search(texto)
    if tem_colegiado and not tem_executivo:
        return False, "executivo_pendente", trecho_em_volta(texto, tem_colegiado)
    if tem_colegiado and RE_APROVACAO_COLEGIADA.search(texto) and not tem_forma:
        # colegiado aprovando, sem fórmula do Executivo: o ato é a aprovação, não a instituição
        return False, "executivo_pendente", trecho_em_volta(texto, tem_colegiado)
    if not tem_executivo:
        return False, "autoridade_nao_confirmada", "nenhuma autoridade do Executivo no texto"
    if not tem_forma:
        return False, "autoridade_nao_confirmada", "sem fórmula de promulgação nem texto articulado"
    return True, "", trecho_em_volta(texto, tem_executivo)


# =============================================================================================
# Etapa 4 — natureza
# =============================================================================================
def etapa4_natureza(texto: str) -> tuple:
    """(natureza, motivo, provas). EX_ANTE só com os três testes cumulativos.

    O classificador de natureza (31/08/2026) continua sendo a primeira palavra — ele é regra, não
    inferência, e já foi validado contra 223 registros reais. O que este juiz acrescenta é o teste
    do objeto explícito em três partes, exigidas CUMULATIVAMENTE."""
    tem_rota_federal = bool(RE_ROTA_FEDERAL.search(texto))
    decisao, motivo = classificar_natureza(texto, tem_reconhecimento_federal=tem_rota_federal)
    if decisao == "RESPOSTA":
        return "RESPOSTA", motivo, {}
    if decisao == "DUVIDA":
        return "DUVIDA", f"natureza_duvidosa: {motivo}", {}

    m_objeto = RE_OBJETO_EX_ANTE.search(texto)
    m_ciclo = RE_GATILHO_CICLO.search(texto)
    m_obs = RE_GATILHO_OBSERVACIONAL.search(texto)
    m_anormal = RE_DECLARA_ANORMALIDADE.search(texto)

    if m_anormal:
        return "RESPOSTA", "declara anormalidade — é ato de resposta", {}
    if not m_objeto:
        return "DUVIDA", "natureza_duvidosa: o texto não diz o que o ato institui ou ativa", {}
    if not (m_ciclo or m_obs):
        return "DUVIDA", "natureza_duvidosa: sem gatilho (previsão, limiar ou referência ao ciclo)", {}
    if tem_rota_federal:
        return "DUVIDA", "natureza_duvidosa: a rota do recurso depende de reconhecimento federal", {}
    return "EX_ANTE", motivo, {
        "objeto": trecho_em_volta(texto, m_objeto),
        "gatilho": trecho_em_volta(texto, m_ciclo or m_obs),
        "rota_do_recurso": "sem dependência de reconhecimento federal no texto",
    }


# =============================================================================================
# Etapa 5 — família de risco
# =============================================================================================
def etapa5_familia_de_risco(texto: str) -> tuple:
    """(ok, familia_ou_motivo, trecho). A exposição do PRÓPRIO município decide.

    Ordem deliberada: primeiro procura família do ciclo; só então considera `fora_do_objeto`. Um
    plano multirrisco que menciona arbovirose numa lista de riscos não é um plano de arbovirose —
    foi assim que Salvador travou num teste de 03/09/2026."""
    t = texto.lower()
    achadas = []
    for familia, termos in FAMILIAS_DE_RISCO.items():
        for termo in termos:
            m = re.search(termo, t)
            if m:
                achadas.append((familia, trecho_em_volta(texto, m)))
                break
    especificas = [a for a in achadas if a[0] != "multirrisco_pdc"]
    fora = next((m for m in (re.search(termo, t) for termo in FORA_DO_OBJETO) if m), None)
    if especificas:
        # família específica do ciclo vence: um plano multirrisco que lista arbovirose entre os
        # riscos não é plano de arbovirose (caso Salvador, travado em teste de 03/09/2026).
        return True, especificas[0][0], especificas[0][1]
    if fora:
        # nenhuma família específica e um risco fora do objeto: é plano de geada, de frio ou de
        # arbovirose. "plano de contingência municipal" no título não basta para virar multirrisco.
        return False, "fora_do_objeto", trecho_em_volta(texto, fora)
    if achadas:
        return True, achadas[0][0], achadas[0][1]
    return False, "familia_de_risco_nao_identificada", ""


# =============================================================================================
# Etapa 6 — categoria e data (§3 e §5.3)
# =============================================================================================
def etapa6_categoria(texto: str, data: str, eh_estadual: bool = False) -> tuple:
    """(categoria, motivo). A escada de créditos NÃO é decidida aqui.

    Este juiz escolhe entre `plano`, `plano_elaboracao` e `plano_antigo` pela data do ato em
    relação ao Boletim nº 1 (29/06/2026). A distinção novo · readaptado · recorrente e os
    créditos por documento continuam onde estão, em `CRED_POP`/`PESO_DOC` e, no estadual, em
    `verificar_recorrencia_uf` — mudar peso, régua ou escada exige a editoria (METODOLOGIA §12)."""
    # O ato que só MANDA elaborar não institui plano nenhum: é `plano_elaboracao` (§3). O teste é
    # pela ausência de verbo de instituição, não por subtração de texto — `RE_OBJETO_EX_ANTE` passou
    # a reconhecer "determina a elaboração" (é objeto ex-ante), então descontá-lo do texto e
    # perguntar de novo devolvia "plano".
    if RE_SO_DETERMINA_ELABORACAO.search(texto) and not RE_INSTITUI.search(texto):
        return "plano_elaboracao", "o ato determina a elaboração do plano, não o institui"
    if not data:
        return None, "citacao_incompleta: sem data não há como situar o ato no ciclo"
    try:
        d, m, a = (int(x) for x in re.split(r"[/-]", data)[:3])
        if a < 100:
            a += 2000
        ato = (a, m, d)
    except (ValueError, TypeError):
        return None, f"data não interpretável: {data!r}"
    bd, bm, ba = (int(x) for x in BOLETIM_1.split("/"))
    boletim = (ba, bm, bd)
    if ato >= boletim:
        return "plano", f"ato de {data}, a partir do Boletim nº 1 ({BOLETIM_1})"
    return "plano_antigo", f"ato de {data}, anterior ao Boletim nº 1 ({BOLETIM_1})"


# =============================================================================================
# O juiz
# =============================================================================================
def julgar(texto: str, nome: str, uf: str, ibge: str = None, url: str = None,
           eh_estadual: bool = False, eh_plano_tecnico: bool = False) -> dict:
    """Aplica as etapas 0 a 6 e devolve o veredito.

    `promove` é True só quando TODAS passam. Quando não promove, `motivo` é o critério que
    falhou — é ele que fica visível na fila, e é por ele que o relatório agrupa as recusas."""
    veredito = {"promove": False, "motivo": None, "codebook": CODEBOOK_VERSAO,
                "criterios": {}, "categoria": None, "data": None, "natureza": None,
                "ibge": ibge, "municipio": nome, "uf": uf, "url": url}

    ok, motivo, trecho = etapa0_documento_primario(url, texto)
    veredito["criterios"]["0_documento_primario"] = {"ok": ok, "trecho": trecho}
    if not ok:
        veredito["motivo"] = motivo
        return veredito

    ok, motivo, trecho = etapa1_identidade(texto, nome, uf)
    veredito["criterios"]["1_identidade"] = {"ok": ok, "trecho": trecho}
    if not ok:
        veredito["motivo"] = motivo
        return veredito

    ok, motivo, dados = etapa2_citacao(texto, eh_plano_tecnico)
    veredito["criterios"]["2_citacao"] = {"ok": ok, "trecho": dados.get("trecho", ""), "dados": dados}
    veredito["data"] = dados.get("data")
    if not ok:
        veredito["motivo"] = motivo
        return veredito

    ok, motivo, trecho = etapa3_autoridade(texto)
    veredito["criterios"]["3_autoridade"] = {"ok": ok, "trecho": trecho}
    if not ok:
        veredito["motivo"] = motivo
        return veredito

    natureza, motivo_nat, provas = etapa4_natureza(texto)
    veredito["natureza"] = natureza
    veredito["criterios"]["4_natureza"] = {"ok": natureza == "EX_ANTE", "trecho": motivo_nat, **provas}
    if natureza == "RESPOSTA":
        # não é recusa: é o outro caminho. Peso zero, registro em atos_resposta.json (§5.2.1),
        # e a pista fica resolvida — isso já é automático desde 31/08/2026.
        veredito["motivo"] = "resposta"
        veredito["encaminhar"] = "atos_resposta"
        return veredito
    if natureza != "EX_ANTE":
        veredito["motivo"] = "natureza_duvidosa"
        return veredito

    ok, familia, trecho = etapa5_familia_de_risco(texto)
    veredito["criterios"]["5_familia_de_risco"] = {"ok": ok, "familia": familia if ok else None,
                                                  "trecho": trecho}
    if not ok:
        veredito["motivo"] = familia
        return veredito
    veredito["familia_de_risco"] = familia

    categoria, motivo_cat = etapa6_categoria(texto, veredito["data"], eh_estadual)
    veredito["criterios"]["6_categoria"] = {"ok": categoria is not None, "trecho": motivo_cat}
    if categoria is None:
        veredito["motivo"] = motivo_cat.split(":")[0]
        return veredito

    veredito["categoria"] = categoria
    veredito["promove"] = True
    veredito["motivo"] = None
    return veredito


# =============================================================================================
# Canários — um documento por desfecho, exigidos pelo handover
# =============================================================================================
URL_OFICIAL = "https://bonito.ms.gov.br/diariooficial/edicao-1234.pdf"

CANARIOS = {
    "plano_novo": dict(
        esperado={"promove": True, "categoria": "plano"},
        nome="Bonito", uf="MS", url=URL_OFICIAL,
        texto="""PREFEITURA MUNICIPAL DE BONITO - MS
DECRETO Nº 1.482, DE 14 DE JULHO DE 2026.
Institui o Plano de Contingência Municipal de Proteção e Defesa Civil para o período de estiagem
2026/2027 e dá outras providências.
O PREFEITO MUNICIPAL DE BONITO, Estado de Mato Grosso do Sul, no uso das atribuições que lhe
confere a Lei Orgânica do Município, e CONSIDERANDO o prognóstico do INMET e o boletim do Painel
El Niño para a estação seca, DECRETA:
Art. 1º Fica instituído o Plano de Contingência Municipal para o período de estiagem 2026/2027,
com as medidas de preparação, pré-posicionamento de carro-pipa e alerta antecipado descritas no
Anexo I. Art. 2º Fica criado o Comitê Gestor de Enfrentamento à Estiagem, coordenado pela
COMPDEC. Art. 3º Este Decreto entra em vigor na data de sua publicação, não configurando
situação de emergência."""),

    "plano_readaptado": dict(
        esperado={"promove": True, "categoria": "plano"},
        nome="Cuiabá", uf="MT", url="https://www.cuiaba.mt.gov.br/diariooficial/2026/dec-99.pdf",
        texto="""PREFEITURA MUNICIPAL DE CUIABÁ - MT
DECRETO Nº 9.117, DE 3 DE AGOSTO DE 2026.
Atualiza o Plano de Contingência Municipal de Proteção e Defesa Civil para o período chuvoso
2026/2027.
O PREFEITO MUNICIPAL DE CUIABÁ, no uso de suas atribuições legais, CONSIDERANDO a previsão
meteorológica do CEMADEN para a estação chuvosa, DECRETA:
Art. 1º O Plano de Contingência Municipal instituído pelo Decreto nº 8.402/2024 fica atualizado
para o período chuvoso 2026/2027, incorporando os cenários de inundação e deslizamento de
encosta mapeados pela Defesa Civil. Art. 2º Este decreto não declara situação de emergência e
tem caráter exclusivamente preventivo."""),

    "plano_em_elaboracao": dict(
        esperado={"promove": True, "categoria": "plano_elaboracao"},
        nome="Belém", uf="PA", url="https://www.belem.pa.gov.br/diariooficial/dec-2026-771.pdf",
        texto="""PREFEITURA MUNICIPAL DE BELÉM - PA
DECRETO Nº 771, DE 20 DE JULHO DE 2026.
Determina a elaboração do Plano Municipal de Enfrentamento ao Super El Niño 2026-2027.
O PREFEITO MUNICIPAL DE BELÉM, Estado do Pará, no uso de suas atribuições, CONSIDERANDO o
prognóstico climático para o período chuvoso 2026/2027, DECRETA:
Art. 1º Fica determinada a elaboração do Plano Municipal de Enfrentamento, sob coordenação da
Secretaria Municipal de Defesa Civil, no prazo de 90 dias. Art. 2º O plano contemplará os
cenários de alagamento e inundação. Art. 3º Este decreto não configura situação de emergência."""),

    "decreto_de_resposta": dict(
        esperado={"promove": False, "motivo": "resposta"},
        nome="Cerrito", uf="RS", url="https://www.diariomunicipal.com.br/famurs/edicao/4455.pdf",
        texto="""MUNICÍPIO DE CERRITO - RS
DECRETO Nº 55, DE 2 DE JULHO DE 2026.
Declara situação de emergência em razão da estiagem que atingiu o território municipal.
O PREFEITO MUNICIPAL DE CERRITO, no uso de suas atribuições, CONSIDERANDO os danos causados pela
estiagem que afetou a produção agrícola desde a madrugada de 20 de junho, DECRETA:
Art. 1º Fica declarada situação de emergência nas áreas do Município atingidas pela estiagem,
conforme o FIDE anexo. Art. 2º Autoriza-se a solicitação de reconhecimento federal junto à
SEDEC, por meio do S2iD."""),

    "aprovacao_por_conselho": dict(
        esperado={"promove": False, "motivo": "executivo_pendente"},
        nome="Recife", uf="PE", url="https://www.recife.pe.gov.br/diariooficial/cms-res-12.pdf",
        texto="""CONSELHO MUNICIPAL DE SAÚDE DO RECIFE - PE
RESOLUÇÃO Nº 12, DE 10 DE AGOSTO DE 2026.
Aprova o Plano de Contingência da Saúde para o período chuvoso 2026/2027.
O Plenário do Conselho Municipal de Saúde do Recife, em reunião ordinária, considerando a
previsão do INMET para a estação chuvosa, RESOLVE aprovar o Plano de Contingência da Saúde
Municipal para enfrentamento dos agravos associados a inundação e alagamento no período chuvoso
2026/2027, homologado ad referendum pela mesa diretora do Conselho."""),

    "plano_de_geada": dict(
        esperado={"promove": False, "motivo": "fora_do_objeto"},
        nome="Urupema", uf="SC", url="https://www.diariomunicipal.com.br/fecam/edicao/9911.pdf",
        texto="""PREFEITURA MUNICIPAL DE URUPEMA - SC
DECRETO Nº 41, DE 1º DE JULHO DE 2026.
Institui o Plano de Contingência para o período de frio intenso e geada de 2026.
O PREFEITO MUNICIPAL DE URUPEMA, no uso de suas atribuições, CONSIDERANDO a previsão do INMET de
onda de frio e geada, DECRETA:
Art. 1º Fica instituído o Plano de Contingência Municipal para o período de frio intenso e
geada, com abertura de abrigos noturnos e distribuição de agasalhos. Art. 2º Este decreto tem
caráter preventivo e não configura situação de emergência."""),

    "noticia_sem_documento": dict(
        esperado={"promove": False, "motivo": "sem_documento_primario"},
        nome="Salvador", uf="BA", url="https://g1.globo.com/ba/bahia/noticia/2026/07/plano.ghtml",
        texto="""Prefeitura de Salvador anuncia plano de contingência para o período chuvoso
A Prefeitura de Salvador anunciou nesta segunda-feira o plano de contingência para o período
chuvoso 2026/2027, com ações de prevenção a deslizamentos de encosta. Segundo a Codesal, o
documento será publicado no Diário Oficial do Município nos próximos dias. O prefeito afirmou
que o plano prevê pré-posicionamento de equipes e alerta antecipado para as áreas de risco
mapeadas pela Defesa Civil municipal, conforme a previsão do INMET."""),

    "pdf_ilegivel": dict(
        esperado={"promove": False, "motivo": "texto_nao_extraivel"},
        nome="Bonito", uf="MS", url="https://bonito.ms.gov.br/diariooficial/edicao-escaneada.pdf",
        texto="DECRETO Nº 1.482"),

    "ente_errado": dict(
        esperado={"promove": False, "motivo": "ente_nao_confirmado"},
        nome="Anhembi", uf="SP", url="https://www.diariomunicipal.com.br/apm/edicao/7788.pdf",
        texto="""PREFEITURA MUNICIPAL DE BOTUCATU - SP
DECRETO Nº 12.004, DE 15 DE JULHO DE 2026.
Institui o Plano de Contingência Municipal para o período chuvoso 2026/2027.
O PREFEITO MUNICIPAL DE BOTUCATU, no uso de suas atribuições, CONSIDERANDO a previsão do CEMADEN
para a estação chuvosa, DECRETA:
Art. 1º Fica instituído o Plano de Contingência Municipal de Proteção e Defesa Civil para o
período chuvoso 2026/2027, contemplando inundação e deslizamento. Art. 2º Este decreto tem
caráter preventivo."""),

    "citacao_incompleta": dict(
        esperado={"promove": False, "motivo": "citacao_incompleta"},
        # URL própria: dois canários na mesma URL fazem o autoteste de `julgar_filas.py`, que indexa
        # os textos por URL, exercitar um só deles.
        nome="Bonito", uf="MS", url="https://bonito.ms.gov.br/diariooficial/edicao-1300.pdf",
        texto="""PREFEITURA MUNICIPAL DE BONITO - MS
DECRETO MUNICIPAL
Institui o Plano de Contingência Municipal para o período de estiagem.
O PREFEITO MUNICIPAL DE BONITO, no uso de suas atribuições, CONSIDERANDO o prognóstico do INMET,
DECRETA: Art. 1º Fica instituído o Plano de Contingência Municipal de Proteção e Defesa Civil
para o período de estiagem, com pré-posicionamento de carro-pipa e alerta antecipado. Art. 2º
Este decreto tem caráter preventivo e não configura situação de emergência. Publicado sem número
e sem data no expediente."""),
}


def autoteste() -> int:
    falhas = []
    for nome_canario, c in CANARIOS.items():
        esperado = c["esperado"]
        v = julgar(c["texto"], nome=c["nome"], uf=c["uf"], url=c["url"])
        for chave, valor in esperado.items():
            if v.get(chave) != valor:
                falhas.append(f"{nome_canario}: {chave} esperado {valor!r}, veio {v.get(chave)!r}"
                              f" (motivo={v.get('motivo')!r})")
        marca = "OK  " if all(v.get(k) == x for k, x in esperado.items()) else "FALHA"
        print(f"  {marca} {nome_canario}: promove={v['promove']} categoria={v['categoria']} motivo={v['motivo']}")

    # travas que não são canário de documento
    checagens = [
        ("todo canário promovido traz trecho em cada critério",
         all(all(cr.get("trecho") is not None for cr in julgar(c["texto"], nome=c["nome"], uf=c["uf"],
                                                              url=c["url"])["criterios"].values())
             for c in CANARIOS.values())),
        ("o codebook é versionado no veredito",
         julgar(CANARIOS["plano_novo"]["texto"], nome="Bonito", uf="MS",
                url=URL_OFICIAL)["codebook"] == CODEBOOK_VERSAO),
        ("família de risco específica vence multirrisco",
         etapa5_familia_de_risco("plano de contingência de proteção e defesa civil para a "
                                 "estiagem e a seca severa")[1] == "seca_estiagem_fogo"),
        ("arbovirose citada numa lista de riscos não torna o plano fora do objeto",
         etapa5_familia_de_risco("plano municipal para inundação, alagamento, deslizamento e "
                                 "também arbovirose")[1] == "chuvas_inundacao_deslizamento"),
        ("rota federal no texto derruba ex-ante para dúvida",
         etapa4_natureza(CANARIOS["plano_novo"]["texto"] + " Solicita-se reconhecimento federal "
                         "junto à SEDEC pelo S2iD.")[0] != "EX_ANTE"),
        ("fonte não oficial nunca chega à etapa 1",
         julgar(CANARIOS["plano_novo"]["texto"], nome="Bonito", uf="MS",
                url="https://blog.exemplo.com/plano")["motivo"] == "sem_documento_primario"),
        ("plano técnico sem número passa a citação quando tem data",
         etapa2_citacao("Plano de Contingência Municipal, versão 2026. Publicado em 14/07/2026. "
                        + "x" * 500, eh_plano_tecnico=True)[0] is True),
        ("plano técnico sem número e SEM data não passa",
         etapa2_citacao("Plano de Contingência Municipal, versão 2026." + "x" * 500,
                        eh_plano_tecnico=True)[0] is False),
    ]
    for nome_check, ok in checagens:
        print(f"  {'OK  ' if ok else 'FALHA'} {nome_check}")
        if not ok:
            falhas.append(nome_check)

    if falhas:
        print(f"X JUIZ: {len(falhas)} falha(s):")
        for f in falhas:
            print(f"   - {f}")
        return 1
    print(f"OK JUIZ — {len(CANARIOS)} canários e {len(checagens)} travas, codebook {CODEBOOK_VERSAO}.")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(autoteste() if "--autoteste" in sys.argv else 0)
