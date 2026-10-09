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
import json
import pathlib
import re
import unicodedata

from classificador_natureza import classificar as classificar_natureza
from classificador_natureza import citacao_completa, data_do_ato, extrair_data

RAIZ = pathlib.Path(__file__).resolve().parent

# 1.1 (28/09/2026): a Etapa 4 passou a exigir VERBO e INSTRUMENTO na mesma vizinhança. A versão sobe
# porque o critério mudou, e porque `pendente()` usa a versão para decidir o que volta à fila: subir
# aqui devolve ao juiz toda pista já julgada sob a regra frouxa — inclusive as quatro que ela
# promoveu por engano.
CODEBOOK_VERSAO = "1.4 (09/10/2026)"
# 1.4 (09/10/2026, lote 2): atribuição pelo domínio do ente (2.1), classificação com fronteira de
# palavra e instrução normativa numa régua só (2.3), recorte do ato no texto colapsado e corte de
# 20.000 depois do recorte (2.2). A versão sobe para que `pendente()` devolva ao juiz tudo o que o
# 1.3 decidiu — inclusive as pistas que o prazo fechou depois de uma leitura (2.5, A1-16).
# 1.3 — primeira rodada real do caminho novo, no mesmo dia: cinco promoções em sessenta pistas, e
# DUAS eram notícia institucional no domínio do ente ("Prefeitura apresenta plano de contingência
# para emergências"). A notícia satisfazia as três condições por acidente — está em domínio oficial,
# cita o órgão, o título e o ano, e não é minuta. Faltava a condição que o handover do garimpo já
# dizia com outras palavras: **a URL tem de ser o documento**. Sem isto, o caminho novo creditaria
# preparação a quem publicou um release. Falso positivo é pior que falso negativo.
#
# 1.2 — DECISÃO DA EDITORIA de 03/10/2026: **plano publicado sem ato de aprovação localizado**
# conta no degrau que a leitura do documento indicar, nos DOIS índices, com três condições
# (domínio oficial do ente; órgão, título e ano identificados; não ser minuta, rascunho, versão
# para consulta ou apresentação) e a marca "sem ato de aprovação localizado" na ficha.
#
# Por que a versão sobe: `pendente()` em `julgar_filas.py` compara a versão do codebook com a do
# veredito guardado na pista. Subir a versão é o que faz um critério novo ALCANÇAR o que o critério
# velho já decidiu — sem isso, as centenas de pistas recusadas por "citacao_incompleta" e
# "autoridade_nao_confirmada" ficariam fora da fila para sempre, com uma recusa que a editoria
# acabou de revogar.

# --- Etapa 0 ---------------------------------------------------------------------------------
# Padrões de fonte provável oficial. Mesma lista que `descobrir_planos.py` usa desde 18/09/2026;
# repetida aqui como constante nomeada para que o juiz não dependa da ordem de importação.
PADROES_FONTE_PROVAVEL_OFICIAL = (
    ".gov.br", ".leg.br", ".jus.br", "diariomunicipal.com.br", "queridodiario.ok.org.br",
    "dosp.com.br", "sigpub.com.br", "imprensaoficial", "diariooficial", "doe.",
)
TEXTO_MINIMO = 400   # menos que isto não é documento: é resumo, menu de portal ou erro servido com 200
# Piso do RECORTE do ato, que é outra pergunta: aqui já se sabe que a edição é documento, e ato curto
# existe — um decreto de instituição de plano cabe em 400 caracteres. O piso serve só para impedir que
# um cabeçalho solto, ou duas linhas de sumário, sejam julgados como se fossem o ato.
MINIMO_DO_RECORTE = 200

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

# --- Etapas 2 e 3, caminho do PLANO SEM ATO (decisão da editoria, 03/10/2026) ----------------
# Condição 3 da decisão: **não ser minuta, rascunho, versão para consulta ou apresentação**. É a
# trava assimétrica deste caminho — sem ato de aprovação, o que separa o documento publicado de um
# esboço é o próprio documento dizer que é esboço. Falso positivo aqui creditaria preparação a quem
# publicou uma minuta.
RE_MINUTA = re.compile(
    r"\b(minuta|rascunho|vers[ãa]o\s+preliminar|vers[ãa]o\s+para\s+consulta|consulta\s+p[úu]blica|"
    r"em\s+elabora[çc][ãa]o|documento\s+de\s+trabalho|draft|apresenta[çc][ãa]o\s+em\s+slides|"
    r"n[ãa]o\s+aprovado)\b", re.I)
# Condição 2, primeira parte: o documento identifica o ÓRGÃO do ente. Publicação em domínio oficial
# é ato do ente (etapa 0 já exige o domínio); aqui se exige que o documento diga de quem é.
RE_ORGAO_DO_ENTE = re.compile(
    r"\b(prefeitura\s+municipal|prefeitura\s+d[aeo]|munic[íi]pio\s+d[aeo]|"
    r"coordenadoria\s+(?:municipal|estadual)\s+de\s+(?:prote[çc][ãa]o\s+e\s+)?defesa\s+civil|"
    r"coordenadoria\s+de\s+(?:prote[çc][ãa]o\s+e\s+)?defesa\s+civil|"
    r"compdec|comdec|cedec|cepdec|defesa\s+civil\s+(?:de|do|da|municipal|estadual)|"
    r"secretaria\s+(?:municipal|de\s+estado|estadual)|governo\s+do\s+estado|"
    r"estado\s+d[aeo]\s+\w+)\b", re.I)
# Condição 2, segunda parte: o TÍTULO é de plano, e não de outro documento qualquer.
RE_TITULO_DE_PLANO = re.compile(
    r"\bplano\s+(?:municipal\s+|estadual\s+)?(?:de\s+)?"
    r"(conting[êe]ncia|a[çc][ãa]o\s+e\s+conting[êe]ncia|prote[çc][ãa]o\s+e\s+defesa\s+civil|"
    r"opera[çc][õo]es|preven[çc][ãa]o)\b|\bplamcon\b|\bplancon\b|\bplacon\b", re.I)
# Condição 2, terceira parte: o ANO, ou o ciclo. Ano solto BASTA aqui — e só aqui. No caminho do
# ATO a data completa continua obrigatória, porque ato se situa por data.
RE_ANO_OU_CICLO = re.compile(r"\b(20\d{2})\s*[/-]?\s*(20\d{2})?\b|\bel\s*ni[ñn]o\b", re.I)
# O documento se APRESENTA como ato? Palavra de tipo de ato numa linha só, sem número junto (se
# houvesse número, `RE_TIPO_E_NUMERO` teria casado). Serve para separar as duas recusas: decreto
# sem número é ATO com citação incompleta, e continua recusado por `citacao_incompleta` — o ato
# existe e não se consegue citá-lo. O caminho do plano sem ato é para o documento que NÃO se
# apresenta como ato: o PDF do plano publicado pelo ente.
RE_ATO_SEM_NUMERO = re.compile(
    r"^\s*(decreto|portaria|lei|resolu[çc][ãa]o|instru[çc][ãa]o\s+normativa)"
    r"(?:\s+(?:municipal|estadual|complementar|ordin[áa]ri[oa]))?\s*$", re.I | re.M)


# O documento É o plano, ou é uma NOTÍCIA sobre o plano? A pergunta separa o release institucional
# ("Prefeitura apresenta o plano de contingência") do documento. Dois sinais, nos dois sentidos:
RE_MARCA_DE_NOTICIA = re.compile(
    r"\b(assessoria\s+de\s+(?:comunica[çc][ãa]o|imprensa)|secom|leia\s+(?:tamb[ée]m|mais)|"
    r"compartilh[ae]|publicado\s+(?:em|por)\s|not[íi]cias?\s*[:>|]|"
    r"[úu]ltimas\s+not[íi]cias|fale\s+com\s+a\s+prefeitura|redes\s+sociais|"
    r"apresent(?:a|ou)\s+o\s+plano|lan[çc](?:a|ou)\s+o\s+plano)\b", re.I)
# Estrutura de PLANO: as partes que um plano de contingência tem e uma notícia não tem.
RE_ESTRUTURA_DE_PLANO = re.compile(
    r"\b(este\s+plano|o\s+presente\s+plano|objetivo\s+deste\s+plano|"
    r"n[íi]veis?\s+de\s+(?:alerta|prontid[ãa]o)|acionamento|atribui[çc][õo]es|"
    r"fluxograma|an[eé]xo\s+[ivx0-9]|sum[áa]rio|"
    r"1\s*[.)]\s*introdu[çc][ãa]o|pontos?\s+de\s+apoio|abrigos?\s+tempor[áa]rio|"
    r"a[çc][õo]es\s+de\s+(?:prepara[çc][ãa]o|resposta)|matriz\s+de\s+risco)\b", re.I)
EXTENSOES_DE_DOCUMENTO = (".pdf", ".doc", ".docx", ".odt", ".rtf")
MINIMO_DE_ESTRUTURA = 2


def e_o_proprio_plano(texto: str, url: str = None) -> tuple:
    """(ok, motivo, provas). O julgado é o PLANO, e não uma notícia sobre ele. Função pura.

    A prova vem por um de dois caminhos, e o segundo é mais exigente de propósito:
      · a URL é um documento (`.pdf`, `.doc`, `.docx`, `.odt`, `.rtf`) — aí o que foi baixado é o
        arquivo que o ente publicou;
      · ou o texto traz pelo menos DOIS sinais de estrutura de plano (este plano, níveis de alerta,
        acionamento, atribuições, anexo, sumário, pontos de apoio…) e nenhuma marca de notícia.

    Marca de notícia com URL de página derruba: "Prefeitura apresenta o plano" é release, e release
    não é plano. Com URL de documento a marca de notícia não derruba — um PDF pode citar a notícia
    que o divulgou, e o que vale é o que foi baixado.
    """
    u = str(url or "").lower().split("?")[0]
    e_documento = u.endswith(EXTENSOES_DE_DOCUMENTO)
    estrutura = set(m.group(0).lower() for m in RE_ESTRUTURA_DE_PLANO.finditer(texto or ""))
    noticia = RE_MARCA_DE_NOTICIA.search(texto or "")
    if e_documento:
        return True, "", {"prova": "a URL é o documento publicado pelo ente",
                          "estrutura": sorted(estrutura)[:4]}
    if noticia:
        return False, "noticia_institucional_nao_e_o_plano", {
            "prova": trecho_em_volta(texto, noticia),
            "detalhe": "página de notícia no domínio do ente: a notícia diz que o plano existe, "
                       "mas não é o plano"}
    if len(estrutura) < MINIMO_DE_ESTRUTURA:
        return False, "noticia_institucional_nao_e_o_plano", {
            "detalhe": f"a página não é documento e traz {len(estrutura)} sinal(is) de estrutura "
                       f"de plano (mínimo {MINIMO_DE_ESTRUTURA})",
            "estrutura": sorted(estrutura)}
    return True, "", {"prova": "página com estrutura de plano e sem marca de notícia",
                      "estrutura": sorted(estrutura)[:4]}


def plano_sem_ato(texto: str, url: str = None) -> tuple:
    """(ok, motivo, dados) do caminho "plano publicado sem ato de aprovação localizado". PURA.

    Decisão da editoria de 03/10/2026. O índice mede **preparação publicada e verificável**: a
    publicação em domínio oficial é ato do ente, com autoria e data conferíveis, e o ato de
    aprovação é atributo de FORMALIZAÇÃO — não de existência do plano. O documento conta no degrau
    que a leitura indicar, e a ficha diz que o ato não foi localizado.

    As três condições da decisão, nesta ordem:
      1. domínio oficial do ente — já exigido na etapa 0, pela URL;
      2. órgão, título e ano (ou o ciclo) identificados NO documento;
      3. não ser minuta, rascunho, versão para consulta ou apresentação.
    """
    ok_doc, motivo_doc, provas_doc = e_o_proprio_plano(texto, url)
    if not ok_doc:
        return False, motivo_doc, provas_doc
    if RE_MINUTA.search(texto or ""):
        return False, "minuta_ou_rascunho", {
            "detalhe": "o documento se declara minuta, rascunho, versão para consulta ou "
                       "apresentação",
            "trecho": trecho_em_volta(texto, RE_MINUTA.search(texto))}
    orgao = RE_ORGAO_DO_ENTE.search(texto or "")
    titulo = RE_TITULO_DE_PLANO.search(texto or "")
    ano = RE_ANO_OU_CICLO.search(texto or "")
    faltam = [nome for nome, achado in (("órgão", orgao), ("título de plano", titulo),
                                        ("ano ou ciclo", ano)) if not achado]
    if faltam:
        return False, "plano_sem_identificacao", {
            "detalhe": "o documento não identifica: " + ", ".join(faltam)}
    return True, "", {
        "tipo": "plano publicado sem ato de aprovação localizado",
        "numero": None,
        "data": (ano.group(1) if ano.lastindex else None) or ano.group(0),
        "sem_ato_de_aprovacao": True,
        "orgao": orgao.group(0),
        "titulo": titulo.group(0),
        "trecho": trecho_em_volta(texto, titulo),
        "prova_de_que_e_o_plano": provas_doc.get("prova"),
    }


# --- Etapa 4 ---------------------------------------------------------------------------------
# Objeto ex-ante: o que o ato FAZ. Origem: METODOLOGIA §5.2.1 (teste do objeto), 03/09/2026.
#
# 28/09/2026: a regra era UMA alternância só, e entre as alternativas estava o verbo solto
# `institu[ií]`. Numa edição inteira de diário — vinte mil caracteres, dezenas de atos — sempre há
# um "institui" em algum lugar, e quase sempre há um "comitê gestor" de outra coisa. Na primeira
# passada real do juiz isso promoveu **quatro registros falsos de cinco**: em Salto/SP, Apucarana/PR
# e Goiânia/GO não havia NENHUMA ocorrência de termo de plano nos 20.000 caracteres julgados
# (Apucarana casou em "Comitê Gestor do Programa Sandbox"; Goiânia saiu com data de 21/08/1959), e
# Alagoinhas/BA casou em "Plano de Contingência / PGR" dentro de condicionante de licença ambiental
# de estabelecimento privado — obrigação imposta a um licenciado, não plano do município.
#
# O objeto passa a exigir DUAS coisas, e perto uma da outra: o VERBO que cria ou atualiza, e o
# INSTRUMENTO nomeado. "Institui" sozinho não diz o que foi instituído; "plano de contingência"
# sozinho pode ser exigência feita a terceiro. A vizinhança é o que liga um ao outro — em Serra/ES,
# o único caso verdadeiro dos cinco, eles são vizinhos imediatos: "Fica instituído o Plano Municipal
# de Proteção e Defesa Civil".
JANELA_OBJETO = 300   # caracteres entre o verbo e o instrumento

RE_VERBO_EX_ANTE = re.compile(
    r"institu[ií]|aprova\s+o\s+plano|atualiza[çr]|revis[ãa]o\s+do\s+plano|"
    # 27/09/2026 (canário `plano_em_elaboracao`): determinar a elaboração TAMBÉM é objeto ex-ante —
    # é o que a categoria `plano_elaboracao` registra (§3). Sem isto, o ato de elaboração caía em
    # dúvida por "não diz o que institui", e o caso fundador de Belém (27/08/2026) não passaria.
    r"determina(?:d[ao])?\s+(?:a\s+)?elabora[çc][ãa]o", re.I)

RE_INSTRUMENTO_EX_ANTE = re.compile(
    r"plano\s+de\s+conting[êe]ncia|plancon|plano\s+de\s+a[çc][ãa]o|plano\s+de\s+enfrentamento|"
    r"plano\s+(?:municipal|estadual)\s+de\s+(?:enfrentamento|conting[êe]ncia|a[çc][ãa]o|"
    r"prote[çc][ãa]o\s+e\s+defesa\s+civil)|"
    r"opera[çc][ãa]o\s+(?:ver[ãa]o|inverno|estiagem|chuvas|seca)|"
    r"comit[êe]\s+(?:gestor|de\s+crise|de\s+enfrentamento|permanente)|"
    r"pr[ée]-?posiciona|sala\s+de\s+situa[çc][ãa]o", re.I)


def objeto_ex_ante(texto: str) -> tuple:
    """(ok, trecho). Exige verbo E instrumento a menos de JANELA_OBJETO caracteres um do outro.

    Devolve o trecho que mostra os dois juntos — que é o que faltava no registro: os `trecho` dos
    critérios das quatro promoções falsas traziam cabeçalho de diário e até texto invertido, e
    ninguém conseguiria conferir a decisão por eles."""
    verbos = list(RE_VERBO_EX_ANTE.finditer(texto))
    if not verbos:
        return False, ""
    instrumentos = list(RE_INSTRUMENTO_EX_ANTE.finditer(texto))
    if not instrumentos:
        return False, ""
    for v in verbos:
        for x in instrumentos:
            if abs(x.start() - v.start()) <= JANELA_OBJETO:
                ini, fim = sorted((v.start(), x.start()))
                return True, " ".join(texto[max(0, ini - 40):fim + 160].split())
    return False, ""
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
# 09/10/2026 (A1-26). Os termos eram SUBSTRING solta e casavam dentro de outra palavra: "secagem
# de graos" virava seca, "fogo de artificio" virava fogo, "cheirava" virava cheia. Medido no juiz
# de hoje, antes da correcao: `maquina de secagem de graos` -> seca_estiagem_fogo. Agora cada termo
# fechado tem fronteira de palavra, e "fogo" exige nao ser fogo de artificio. Os termos que sao
# RADICAL de proposito (`inunda`, `desliza`, `alagad`, `desertifica`) seguem abertos a direita, que
# e o que os faz pegar "inundacao", "inundacoes" e "inundado": ali a abertura e a regra.
B = chr(92) + "b"   # a fronteira de palavra, montada sem escape no fonte
S = chr(92) + "s"   # o espaço, idem

FAMILIAS_DE_RISCO = {
    "seca_estiagem_fogo": (B + "estiagem", B + "seca(?:s)?" + B, B + "seca severa" + B,
                           B + "desertifica", B + "inc[êe]ndio",
                           B + "queimada", B + "fogo" + B + "(?!" + S + "+de" + S + "+artif)",
                           B + "escassez h[íi]drica", B + "crise h[íi]drica",
                           B + "desabastecimento de [áa]gua", B + "carro-pipa"),
    "chuvas_inundacao_deslizamento": (B + "chuva", B + "inunda", B + "alagamento",
                                      B + "enchente", B + "cheia(?:s)?" + B,
                                      B + "deslizamento", B + "desliza",
                                      B + "movimento de massa",
                                      B + "encosta", B + "alagad", B + "transbordamento"),
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


# Cabeçalho de ato dentro de uma edição de diário. Uma edição do Querido Diário traz dezenas de atos
# num arquivo só; o documento primário do §5.2.1 é o ATO, não a edição.
#
# 09/10/2026 (lote 2.2, A1-03): a versão anterior era ancorada em `^…$` com `re.M`, e o texto que o
# juiz recebe em produção chega com o espaço colapsado (`buscar_texto` faz `\s+ -> " "`). Sem quebra
# de linha, o único "início de linha" era o começo do arquivo: o recorte devolvia a edição inteira
# em 5.499 de 5.499 decisões, e a lei de rua do topo do diário virava a citação do plano (Sobral/CE).
# Agora o cabeçalho é reconhecido pela FORMA, em qualquer posição: tipo do ato em CAIXA ALTA (como
# os diários o compõem) + marca de número + número. A citação no corpo ("nos termos da Lei nº
# 12.608") vem em caixa mista e não corta o recorte. Cabeçalho em caixa mista não é reconhecido: o
# recorte devolve o texto inteiro, que é o erro tolerado (o juiz lê tudo e provavelmente recusa).
RE_CABECALHO_DE_ATO = re.compile(
    r"(?<![A-Za-zÀ-ÿ])((?:DECRETO|PORTARIA|LEI|RESOLU[ÇC][ÃA]O|INSTRU[ÇC][ÃA]O\s+NORMATIVA)"
    r"(?:\s+(?:MUNICIPAL|ESTADUAL|COMPLEMENTAR|ORDIN[ÁA]RI[AO]))?"
    r"\s+N\s*[º°o.]{0,2}\s*\d[\d.]*(?:/\d{2,4})?)")

# O juiz julga no máximo isto. O corte existia em `buscar_texto`, ANTES do recorte: 185 das 197
# recusas `ente_nao_confirmado` do codebook 1.3 leram um diário truncado, com o ato além do corte
# (A1-20). Agora a leitura traz o documento inteiro, o recorte acha o ato no texto integral, e o
# corte se aplica ao que vai ser julgado.
TETO_DO_JULGAMENTO = 20000


def posicao_do_trecho(texto: str, trecho: str) -> int:
    """Onde o `trecho` começa no `texto`, tolerando quebra de linha e caixa. -1 se não achar.

    O excerto do Querido Diário vem com quebras próprias e caixa diferente da do diário — busca
    literal não acha. A comparação é feita sobre uma cópia com espaço colapsado e em minúsculas, com um
    mapa de posições de volta ao texto ORIGINAL, porque é no original que o recorte é feito."""
    if not texto or not trecho:
        return -1
    plano, mapa, espaco = [], [], False
    for i, ch in enumerate(texto):
        if ch.isspace():
            if not espaco and plano:
                plano.append(" ")
                mapa.append(i)
            espaco = True
        else:
            plano.append(ch.lower())
            mapa.append(i)
            espaco = False
    plano = "".join(plano)
    alvo = " ".join(str(trecho).split()).lower()
    for tamanho in (120, 60, 30):
        pedaco = alvo[:tamanho].strip()
        if len(pedaco) < 12:
            continue
        j = plano.find(pedaco)
        if j >= 0:
            return mapa[j]
    return -1


def recortar_ato(texto: str, trecho: str, margem: int = 6000) -> str:
    """O ato que contém o `trecho`, recortado de dentro da edição do diário.

    Por que isto existe (28/09/2026, item 1): a pista do Querido Diário aponta a EDIÇÃO — vinte mil
    caracteres com dezenas de atos. O juiz lido sobre a edição inteira cai em `natureza_duvidosa`
    corretamente, porque não há um ato a julgar: há muitos. O documento primário do §5.2.1 é o ato.

    O recorte vai do cabeçalho de ato imediatamente ANTES do trecho até o cabeçalho seguinte. Sem
    trecho, sem cabeçalho antes dele, ou trecho ausente do texto, devolve o texto INTEIRO — a regra é
    conservadora de propósito: na dúvida o juiz lê tudo e provavelmente recusa, que é o erro tolerado.
    """
    if not texto or not trecho:
        return texto
    pos = posicao_do_trecho(texto, trecho)
    if pos < 0:
        return texto
    cabecalhos = [m.start() for m in RE_CABECALHO_DE_ATO.finditer(texto)]
    antes = [i for i in cabecalhos if i <= pos]
    if not antes:
        return texto
    inicio = antes[-1]
    depois = [i for i in cabecalhos if i > pos]
    fim = depois[0] if depois else min(len(texto), inicio + margem)
    recorte = texto[inicio:fim]
    # recorte minúsculo não é ato: devolve o texto inteiro em vez de julgar um pedaço
    return recorte if len(recorte.strip()) >= MINIMO_DO_RECORTE else texto


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
def etapa0_documento_primario(url: str, texto: str, proveniencia: dict = None) -> tuple:
    """(ok, motivo, trecho). Fonte oficial e texto extraível — nada disso se presume.

    28/09/2026: "documento não obtido" ganhou motivo PRÓPRIO (`documento_inacessivel`). Ele estava
    junto de "url fora dos padrões de fonte oficial" sob o mesmo nome, e as duas coisas são
    opostas: a segunda é estável (a URL é o que é), a primeira é uma noite ruim de rede. Separá-las
    é o que permite recusar uma e adiar a outra."""
    # 04/10/2026 — DOCUMENTO ENTREGUE PELO PRÓPRIO ÓRGÃO.
    #
    # Até aqui a proveniência era sempre uma URL: fonte oficial se reconhecia pelo domínio. Mas o
    # handover de LAI (03/10) decidiu que "documento anexado ou vinculado vai ao juiz, como qualquer
    # documento oficial" — e os quatro primeiros, de AM e RO, chegaram por e-mail do órgão, sem
    # endereço público. Recusá-los por falta de URL seria recusar a prova MAIS forte que existe:
    # o documento entregue pelo órgão que o escreveu, em resposta a um pedido formal.
    #
    # A proveniência de LAI exige as três coisas que a tornam verificável — órgão, data da resposta
    # e hash do arquivo guardado no repositório privado —, e nenhuma delas é presumida: sem as três,
    # a recusa continua. O hash é o que liga o veredito ao byte julgado.
    if not url and e_proveniencia_de_lai(proveniencia):
        if texto is None:
            return False, "documento_inacessivel", "documento não obtido nesta tentativa"
        if len(str(texto).strip()) < TEXTO_MINIMO:
            return False, "texto_nao_extraivel", f"{len(str(texto).strip())} caracteres extraídos"
        return True, "", (f"documento entregue por {proveniencia['orgao']} em "
                          f"{proveniencia['data']} (resposta a pedido de acesso à informação; "
                          f"sha256 {str(proveniencia['hash'])[:12]}…)")
    if not url:
        return False, "sem_documento_primario", ""
    u = str(url).lower()
    if not any(p in u for p in PADROES_FONTE_PROVAVEL_OFICIAL):
        return False, "sem_documento_primario", f"url fora dos padrões de fonte oficial: {url}"
    if texto is None:
        return False, "documento_inacessivel", "documento não obtido nesta tentativa"
    if len(texto.strip()) < TEXTO_MINIMO:
        # 400 caracteres é o piso do que pode ser um ato. Abaixo disso é resumo, menu de portal
        # ou recusa servida com 200 (§186) — e nenhum deles é documento primário.
        return False, "texto_nao_extraivel", f"{len(texto.strip())} caracteres extraídos"
    return True, "", f"{len(texto.strip())} caracteres de fonte oficial"


def e_proveniencia_de_lai(proveniencia: dict) -> bool:
    """A proveniência declara documento entregue pelo órgão, com as três provas? Função pura.

    Órgão, data da resposta e hash do arquivo. Sem as três, não é proveniência: é alegação — e
    alegação não substitui documento primário em lugar nenhum deste codebook.
    """
    p = proveniencia or {}
    if str(p.get("tipo") or "") != "resposta_lai":
        return False
    return all(str(p.get(c) or "").strip() for c in ("orgao", "data", "hash"))


# =============================================================================================
# Etapa 1 — identidade
# =============================================================================================
_HOMONIMOS = None


def nomes_homonimos() -> set:
    """Nomes de município que existem em MAIS DE UMA UF, pela referência do IBGE.

    São 233 na malha de 5.571 — "Bom Jesus" está em seis estados. Enquanto a etapa 1 aceitava o
    nome sem a UF, qualquer um deles podia creditar o município errado, e o diário consorciado é
    justamente o arquivo onde dezenas de nomes convivem na mesma página.
    """
    global _HOMONIMOS
    if _HOMONIMOS is None:
        caminho = RAIZ / "data" / "municipios_ibge_referencia.json"
        conta = {}
        try:
            for m in json.loads(caminho.read_text(encoding="utf-8")):
                n = normalizar(str(m.get("nome") or ""))
                if n:
                    conta[n] = conta.get(n, 0) + 1
        except (OSError, ValueError):
            return set()
        _HOMONIMOS = {n for n, v in conta.items() if v > 1}
    return _HOMONIMOS


def etapa1_identidade(texto: str, nome: str, uf: str, homonimos=None) -> tuple:
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
    # homônimos: o nome aparece, mas a UF da pista não.
    #
    # 09/10/2026 (A1-09). Antes isto passava com uma nota, e a nota não impedia nada: "Bom Jesus"
    # existe em seis estados, e um diário consorciado nomeia dezenas de municípios na mesma
    # página. Quando o nome é homônimo — está em mais de uma UF na referência do IBGE —, sem a UF
    # no texto NÃO HÁ COMO SABER qual deles é, e o juiz não classifica: recusa, com motivo.
    # Nome único segue passando pelo nome, que é identidade suficiente.
    u = normalizar(uf)
    sem_uf = bool(u) and u not in t and normalizar(f"/{uf}") not in t and f" {u}" not in f" {t}"
    conjunto = nomes_homonimos() if homonimos is None else homonimos
    if sem_uf and n in conjunto:
        return (False, "homonimo_sem_uf",
                f'"{nome}" existe em mais de uma UF e o texto não cita {uf}')
    if sem_uf:
        return True, "", f'nomeia "{nome}" (UF não citada no texto; identidade pelo nome)'
    return True, "", trecho_em_volta(texto, re.search(re.escape(nome), texto, re.I)) or f'nomeia "{nome}"'


# =============================================================================================
# Etapa 2 — citação completa (§3.2)
# =============================================================================================
def etapa2_citacao(texto: str, eh_plano_tecnico: bool = False, url: str = None) -> tuple:
    """(ok, motivo, dados). Tipo de ato + número + data extraídos do PRÓPRIO texto.

    Exceção declarada no handover: plano publicado como documento técnico sem número recebe a
    data de publicação e a identificação "plano de contingência …, versão/ano". **A data é
    obrigatória sempre** — sem data não há como situar o ato no ciclo (§5.3)."""
    m = RE_TIPO_E_NUMERO.search(texto)
    # 09/10/2026 (A1-21): a data do ATO, nao a primeira data do texto — num diario a primeira e a
    # da edicao. A regua tem um dono em `classificador_natureza.data_do_ato`.
    data = data_do_ato(texto)
    # `extrair_data` devolve ANO SOLTO quando não há data completa — para o §3.2 isso não é data:
    # "versão 2026" não situa o ato no ciclo. Aqui só vale dd/mm/aaaa.
    if data and not re.fullmatch(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", data):
        data = None
    tipo = (m.group(1).lower() if m else None)
    numero = (m.group(2) if m else None)
    dados = {"tipo": tipo, "numero": numero, "data": data}
    if m is None:
        # CAMINHO DO PLANO SEM ATO (editoria, 03/10/2026): quando não há tipo e número de ato, o
        # documento pode ainda ser o PLANO publicado pelo ente. Aí a identificação exigida é outra
        # — órgão, título e ano —, e o ano solto basta. Este caminho vem ANTES da exigência de data
        # completa, de propósito: data completa é como se situa um ATO, e aqui não há ato.
        apresenta_se_como_ato = RE_ATO_SEM_NUMERO.search(texto or "")
        ok_plano, motivo_plano, dados_plano = plano_sem_ato(texto, url)
        if ok_plano and not apresenta_se_como_ato:
            return True, "", dados_plano
        if eh_plano_tecnico and data:
            # Caminho anterior, de 28/09: plano técnico com DATA completa declarada pelo chamador.
            # Ele continua valendo — o caminho novo é mais largo, não substitui este.
            dados["tipo"] = "plano de contingência (documento técnico sem número)"
            return True, "", dados
        if not data and not apresenta_se_como_ato:
            # Sem ato e sem conseguir ser plano publicado: a recusa é a do plano, que diz o que
            # faltou (minuta, ou identificação incompleta), e não "sem data" — que mandaria quem lê
            # procurar a coisa errada.
            return False, motivo_plano, dict(dados, **dados_plano)
        return False, "citacao_incompleta", dict(dados, detalhe="sem tipo e número de ato")
    if not data:
        return False, "citacao_incompleta", dict(dados, detalhe="sem data completa no texto")
    # `citacao_completa` exige o TIPO junto do número (RE_NUMERO_ATO não casa um número solto).
    # Remontar a citação é o que ela espera receber — passar "numero data" reprovava tudo.
    if not citacao_completa(f"{tipo} nº {numero} de {data}"):
        return False, "citacao_incompleta", dict(dados, detalhe="citação não fecha em §3.2")
    dados["trecho"] = trecho_em_volta(texto, m)
    return True, "", dados


# =============================================================================================
# Etapa 3 — autoridade do ato (§5.2.1)
# =============================================================================================
def etapa3_autoridade(texto: str, sem_ato_de_aprovacao: bool = False) -> tuple:
    """(ok, motivo, trecho). Ato do Poder Executivo, não aprovação por colegiado.

    Aprovação por Conselho de Saúde ou Câmara devolve `executivo_pendente`: o documento pode ser
    o instrumento certo, mas o ato que o institui é outro. Pela §9, instrumento do SUS aprovado
    em colegiado vive na camada observada de saúde — e não pontua no MARÉ Legal.

    03/10/2026 (decisão da editoria): quando a etapa 2 reconheceu **plano publicado sem ato de
    aprovação localizado**, a autoridade já foi verificada ali, e de outra maneira — o documento
    identifica o ÓRGÃO do ente e está publicado no domínio oficial dele, o que é ato do ente com
    autoria e data conferíveis. Exigir aqui fórmula de promulgação seria exigir o ato que a decisão
    declarou não ser condição. O que continua valendo é a trava do colegiado: documento que é só a
    aprovação de um conselho não é o plano publicado pelo Executivo.
    """
    if sem_ato_de_aprovacao:
        tem_colegiado = RE_COLEGIADO.search(texto)
        if tem_colegiado and RE_APROVACAO_COLEGIADA.search(texto) \
                and not RE_ORGAO_DO_ENTE.search(texto):
            return False, "executivo_pendente", trecho_em_volta(texto, tem_colegiado)
        orgao = RE_ORGAO_DO_ENTE.search(texto)
        if not orgao:
            return False, "plano_sem_identificacao", "o documento não identifica o órgão do ente"
        return True, "", trecho_em_volta(texto, orgao)
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
def etapa4_natureza(texto: str, sem_ato_de_aprovacao: bool = False) -> tuple:
    """(natureza, motivo, provas). EX_ANTE só com os três testes cumulativos.

    O classificador de natureza (31/08/2026) continua sendo a primeira palavra — ele é regra, não
    inferência, e já foi validado contra 223 registros reais. O que este juiz acrescenta é o teste
    do objeto explícito em três partes, exigidas CUMULATIVAMENTE.

    03/10/2026 (decisão da editoria, plano sem ato): o teste do objeto pergunta se o ato **institui**
    um instrumento nomeado — e isso cabe a um ATO. Quando o documento julgado É o plano, não há
    verbo de instituição a procurar: o plano não institui o plano, ele **é** o plano, e diz
    "estabelece os procedimentos", "define as atribuições". Nesse caminho o objeto se prova pelo
    próprio instrumento nomeado no título, que a etapa 2 já conferiu.

    O que NÃO muda, e é o que protege o índice: ato que declara anormalidade continua RESPOSTA;
    rota que depende de reconhecimento federal continua dúvida; e o gatilho (previsão, limiar ou
    referência ao ciclo) continua exigido. Um "plano" que só fala de desastre ocorrido não passa.
    """
    tem_rota_federal = bool(RE_ROTA_FEDERAL.search(texto))
    decisao, motivo = classificar_natureza(texto, tem_reconhecimento_federal=tem_rota_federal)
    if decisao == "RESPOSTA":
        return "RESPOSTA", motivo, {}
    if decisao == "DUVIDA" and not sem_ato_de_aprovacao:
        return "DUVIDA", f"natureza_duvidosa: {motivo}", {}

    tem_objeto, prova_objeto = objeto_ex_ante(texto)
    if sem_ato_de_aprovacao and not tem_objeto:
        m_instrumento = RE_INSTRUMENTO_EX_ANTE.search(texto or "")
        if m_instrumento:
            tem_objeto = True
            prova_objeto = ("o documento É o instrumento nomeado: "
                            + trecho_em_volta(texto, m_instrumento))
    m_ciclo = RE_GATILHO_CICLO.search(texto)
    m_obs = RE_GATILHO_OBSERVACIONAL.search(texto)
    m_anormal = RE_DECLARA_ANORMALIDADE.search(texto)

    if m_anormal:
        return "RESPOSTA", "declara anormalidade — é ato de resposta", {}
    if not tem_objeto:
        return "DUVIDA", ("natureza_duvidosa: o texto não traz verbo de instituição junto de um "
                          "instrumento nomeado"), {}
    if not (m_ciclo or m_obs):
        return "DUVIDA", "natureza_duvidosa: sem gatilho (previsão, limiar ou referência ao ciclo)", {}
    if tem_rota_federal:
        return "DUVIDA", "natureza_duvidosa: a rota do recurso depende de reconhecimento federal", {}
    return "EX_ANTE", motivo, {
        "objeto": prova_objeto,
        "gatilho": trecho_em_volta(texto, m_ciclo or m_obs),
        "rota_do_recurso": "sem dependência de reconhecimento federal no texto",
    }


def etapa4_natureza_com_marca(texto: str, sem_ato_de_aprovacao: bool = False) -> tuple:
    """Ponte: `julgar()` conhece a marca da etapa 2 e a repassa. Existe para que a assinatura de
    `etapa4_natureza` continue servindo a quem a chama com um argumento só (os canários e o
    classificador) — e para que a passagem da marca seja visível numa linha, em vez de escondida
    num parâmetro posicional no meio da cadeia."""
    return etapa4_natureza(texto, sem_ato_de_aprovacao=sem_ato_de_aprovacao)


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
def etapa6_categoria(texto: str, data: str, eh_estadual: bool = False,
                    sem_ato_de_aprovacao: bool = False) -> tuple:
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
    if sem_ato_de_aprovacao:
        # DECISÃO DA EDITORIA, 03/10/2026: sem degrau novo — o plano conta no degrau que **a leitura
        # do documento** indicar. Aqui a leitura dá o ano (a etapa 2 o exigiu) e a menção ao ciclo:
        #   · cita o El Niño ou o ciclo        -> `plano`        (feito para o ciclo)
        #   · ano de 2026 ou posterior         -> `plano`        (de todo ano, revisado no ciclo)
        #   · ano anterior                     -> `plano_antigo`
        # Nenhuma categoria nova, nenhum peso novo: são os degraus que já existem, atribuídos pela
        # mesma pergunta que o resto do codebook faz — o documento cobre este ciclo?
        if RE_GATILHO_CICLO.search(texto or ""):
            return "plano", f"plano publicado ({data}) que cita o ciclo; ato de aprovação não localizado"
        ano = None
        m_ano = re.search(r"(20\d{2})", str(data or ""))
        if m_ano:
            ano = int(m_ano.group(1))
        if ano and ano >= 2026:
            return "plano", f"plano publicado de {ano}; ato de aprovação não localizado"
        if ano:
            return "plano_antigo", (f"plano publicado de {ano}, anterior ao ciclo; ato de aprovação "
                                    "não localizado")
        return None, "plano_sem_identificacao: sem ano no documento"
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
           eh_estadual: bool = False, eh_plano_tecnico: bool = False, trecho: str = None,
           proveniencia: dict = None) -> dict:
    """Aplica as etapas 0 a 6 e devolve o veredito.

    `promove` é True só quando TODAS passam. Quando não promove, `motivo` é o critério que
    falhou — é ele que fica visível na fila, e é por ele que o relatório agrupa as recusas."""
    veredito = {"promove": False, "motivo": None, "codebook": CODEBOOK_VERSAO,
                "criterios": {}, "categoria": None, "data": None, "natureza": None,
                "ibge": ibge, "municipio": nome, "uf": uf, "url": url}

    ok, motivo, prova = etapa0_documento_primario(url, texto, proveniencia)
    veredito["criterios"]["0_documento_primario"] = {"ok": ok, "trecho": prova}
    if not ok:
        veredito["motivo"] = motivo
        return veredito

    # Edição de diário traz dezenas de atos; o documento primário é o ATO que contém o excerto.
    # 09/10/2026 (lote 2.2): a identidade do ente se lê na CABEÇA da edição ("Diário Oficial do
    # Município de Bonito - MS") somada ao ato recortado — o ato sozinho costuma não repetir a UF, e
    # o homônimo seria recusado por um corte nosso, não pelo documento. Citação, autoridade e objeto
    # continuam lidos só no ato.
    texto_da_identidade = None
    if trecho:
        recorte = recortar_ato(texto, trecho)
        if recorte is not texto and len(recorte) < len(texto):
            veredito["criterios"]["0_documento_primario"]["recorte_do_ato"] = (
                f"{len(recorte)} de {len(texto)} caracteres — ato recortado da edição pelo excerto")
            texto_da_identidade = texto[:600] + "\n" + recorte
            texto = recorte
    texto = texto[:TETO_DO_JULGAMENTO]

    ok, motivo, trecho = etapa1_identidade(texto_da_identidade or texto, nome, uf)
    veredito["criterios"]["1_identidade"] = {"ok": ok, "trecho": trecho}
    if not ok:
        veredito["motivo"] = motivo
        return veredito

    ok, motivo, dados = etapa2_citacao(texto, eh_plano_tecnico, url=url)
    veredito["criterios"]["2_citacao"] = {"ok": ok, "trecho": dados.get("trecho", ""), "dados": dados}
    veredito["data"] = dados.get("data")
    if not ok:
        veredito["motivo"] = motivo
        return veredito

    # A marca viaja da etapa 2 para a 3 e para o veredito: é ela que diz à ficha do município e do
    # estado que o plano conta, e que o ato de aprovação não foi localizado.
    sem_ato = bool(dados.get("sem_ato_de_aprovacao"))
    veredito["sem_ato_de_aprovacao"] = sem_ato
    ok, motivo, trecho = etapa3_autoridade(texto, sem_ato_de_aprovacao=sem_ato)
    veredito["criterios"]["3_autoridade"] = {"ok": ok, "trecho": trecho}
    if not ok:
        veredito["motivo"] = motivo
        return veredito

    natureza, motivo_nat, provas = etapa4_natureza_com_marca(texto, sem_ato_de_aprovacao=sem_ato)
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

    categoria, motivo_cat = etapa6_categoria(texto, veredito["data"], eh_estadual,
                                             sem_ato_de_aprovacao=sem_ato)
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

# Edição de diário com três atos, para exercitar o recorte: o do meio é o que interessa, e o juiz não
# pode julgar a edição inteira nem misturar atos vizinhos.
EDICAO_DE_DIARIO = """DIÁRIO OFICIAL DO MUNICÍPIO DE BONITO - MS
ANO V EDIÇÃO Nº 1234
LEI Nº 87, DE 2 DE JULHO DE 2026
Denomina logradouro público no bairro Centro e dá outras providências.
O PREFEITO MUNICIPAL, no uso de suas atribuições, sanciona a seguinte lei sobre denominação de rua.
DECRETO Nº 88, DE 3 DE JULHO DE 2026
Institui o Plano de Contingência Municipal para o período de estiagem 2026/2027.
O PREFEITO MUNICIPAL DE BONITO, no uso de suas atribuições, CONSIDERANDO o prognóstico do INMET,
DECRETA: Art. 1º Fica instituído o Plano de Contingência Municipal para a estiagem, com
pré-posicionamento de carro-pipa. Art. 2º Este decreto não configura situação de emergência.
PORTARIA Nº 45, DE 4 DE JULHO DE 2026
Concede licença a servidor do quadro efetivo, sem relação com o ciclo climático.
"""

URL_PDF_DE_PLANO = "https://defesacivil.taio.sc.gov.br/plano-2026.pdf"

PLANO_PUBLICADO_SEM_ATO = 'PREFEITURA MUNICIPAL DE TAIO - SC\nCOORDENADORIA MUNICIPAL DE PROTECAO E DEFESA CIVIL DE TAIO\nPLANO DE CONTINGENCIA DE PROTECAO E DEFESA CIVIL\nVersao 01/2026\nO presente plano estabelece os procedimentos de preparacao e de resposta para inundacao brusca,\ndeslizamento e estiagem no municipio, com pre-posicionamento de equipes, pontos de apoio e\nacionamento do sistema de alerta. Define as atribuicoes de cada orgao municipal na preparacao\npara o ciclo El Nino 2026/2027, a rotina de monitoramento e os abrigos. xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'

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

    # 03/10/2026 — DECISÃO DA EDITORIA: plano publicado sem ato de aprovação localizado. Os três
    # canários abaixo são o contorno exato da decisão: o que passa, o que não passa por ser esboço,
    # e o que não passa por não se identificar. O quarto guarda a fronteira que a decisão NÃO moveu:
    # decreto sem número continua recusado por citação incompleta.
    "plano_sem_ato_de_aprovacao": dict(
        esperado={"promove": True, "categoria": "plano"},
        nome="Taió", uf="SC", url="https://defesacivil.taio.sc.gov.br/plano-2026.pdf",
        texto=PLANO_PUBLICADO_SEM_ATO),

    "plano_minuta_nao_passa": dict(
        esperado={"promove": False, "motivo": "minuta_ou_rascunho"},
        nome="Taió", uf="SC", url="https://defesacivil.taio.sc.gov.br/minuta-plano.pdf",
        texto=PLANO_PUBLICADO_SEM_ATO.replace("PLANO DE CONTINGENCIA DE PROTECAO E DEFESA CIVIL",
                                              "MINUTA DO PLANO DE CONTINGENCIA")),

    "plano_sem_identificacao_nao_passa": dict(
        esperado={"promove": False, "motivo": "plano_sem_identificacao"},
        nome="Taió", uf="SC", url="https://defesacivil.taio.sc.gov.br/documento.pdf",
        texto=("Taio - SC. Este documento descreve procedimentos de preparacao para inundacao e "
               "estiagem, com pre-posicionamento de equipes e pontos de apoio. " + "x" * 600)),

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

    # 28/09/2026 — as duas formas que promoveram registro FALSO na primeira passada real. Elas não
    # são hipóteses: são o resumo do que estava nos 20.000 caracteres julgados em Salto/SP,
    # Apucarana/PR, Goiânia/GO (verbo solto em edição inteira, sem instrumento nenhum) e em
    # Alagoinhas/BA (instrumento presente, mas como obrigação imposta a um licenciado).
    "edicao_inteira_com_verbo_solto": dict(
        esperado={"promove": False, "motivo": "natureza_duvidosa"},
        nome="Bonito", uf="MS", url="https://bonito.ms.gov.br/diariooficial/edicao-1400.pdf",
        texto="""DIÁRIO OFICIAL DO MUNICÍPIO DE BONITO - MS
Publicação Oficial do Município, conforme Lei Municipal n. 3.713, de 13 de dezembro de 2017.
O PREFEITO MUNICIPAL DE BONITO, no uso de suas atribuições, DECRETA:
PORTARIA Nº 221/2026 — Institui a Comissão de Organização, Bens e Serviços da Secretaria de
Administração, para o exercício de 2026, e designa seus membros.
EXTRATO DE CONTRATO — objeto: aquisição de mobiliário escolar. Vigência: 12 meses.
AVISO — a Secretaria de Meio Ambiente informa a previsão de chuvas para o período chuvoso
2026/2027 divulgada pelo INMET, para conhecimento dos munícipes.
COMITÊ GESTOR do Programa Sandbox Municipal — convocação da terceira reunião ordinária."""),

    "instrumento_exigido_de_terceiro": dict(
        esperado={"promove": False, "motivo": "natureza_duvidosa"},
        nome="Bonito", uf="MS", url="https://bonito.ms.gov.br/diariooficial/edicao-1401.pdf",
        texto="""PREFEITURA MUNICIPAL DE BONITO - MS
DECRETO Nº 44/2026, DE 26 DE AGOSTO DE 2026.
Concede licença ambiental de operação e fixa condicionantes.
O SECRETÁRIO MUNICIPAL DE MEIO AMBIENTE DE BONITO, no uso de suas atribuições, e CONSIDERANDO o
prognóstico do INMET para o período chuvoso 2026/2027, resolve conceder licença de operação ao
estabelecimento, mediante as seguintes condicionantes:
XI – Manter em local de fácil acesso à equipe de fiscalização os relatórios de manutenção
preventiva de equipamentos, os laudos de integridade estrutural da pista de concreto armado e o
Plano de Contingência / PGR. Prazo: durante a vigência da Licença;
XII – Realizar treinamentos periódicos voltados aos funcionários, comprovados documentalmente."""),
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
        # 09/10/2026 (A1-09): homônimo sem UF não se classifica. O conjunto entra por parâmetro
        # para a trava ser pura — não depende da malha em disco.
        ("nome homônimo sem a UF no texto é recusado",
         etapa1_identidade("decreto de Bom Jesus declara emergência", "Bom Jesus", "PI",
                           homonimos={"bom jesus"})[:2] == (False, "homonimo_sem_uf")),
        ("nome homônimo COM a UF no texto passa",
         etapa1_identidade("decreto de Bom Jesus - PI declara emergência", "Bom Jesus", "PI",
                           homonimos={"bom jesus"})[0] is True),
        ("nome único sem a UF segue passando pelo nome",
         etapa1_identidade("decreto de Irauçuba declara emergência", "Irauçuba", "CE",
                           homonimos={"bom jesus"})[0] is True),
        ("a malha real tem homônimo, e a etapa 1 o enxerga",
         "bom jesus" in nomes_homonimos()),
        # 09/10/2026 (A1-26): termo de risco nao casa dentro de outra palavra.
        ("'secagem de graos' nao e seca",
         etapa5_familia_de_risco("maquina de secagem de graos")[1]
         == "familia_de_risco_nao_identificada"),
        ("'fogo de artificio' nao e incendio",
         etapa5_familia_de_risco("fogo de artificio na festa de agosto")[1]
         == "familia_de_risco_nao_identificada"),
        ("'cheirava' nao e cheia",
         etapa5_familia_de_risco("o bueiro cheirava mal")[1]
         == "familia_de_risco_nao_identificada"),
        ("seca no singular e no plural seguem valendo",
         etapa5_familia_de_risco("a seca severa de 2026")[1] == "seca_estiagem_fogo"
         and etapa5_familia_de_risco("secas recorrentes no municipio")[1]
         == "seca_estiagem_fogo"),
        ("cheia no plural segue valendo",
         etapa5_familia_de_risco("as cheias do rio Itajai")[1]
         == "chuvas_inundacao_deslizamento"),
        ("fogo em vegetacao segue valendo",
         etapa5_familia_de_risco("combate a fogo em vegetacao")[1] == "seca_estiagem_fogo"),
        ("radical de inundacao segue aberto a direita",
         etapa5_familia_de_risco("inundacoes e alagados recorrentes")[1]
         == "chuvas_inundacao_deslizamento"),
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
        # as três condições da decisão de 03/10/2026, uma a uma
        ("plano sem ato: passa com órgão, título e ano, e marca a ficha",
         plano_sem_ato(PLANO_PUBLICADO_SEM_ATO, URL_PDF_DE_PLANO)[0] is True
         and plano_sem_ato(PLANO_PUBLICADO_SEM_ATO, URL_PDF_DE_PLANO)[2]["sem_ato_de_aprovacao"] is True),
        ("plano sem ato: minuta não passa",
         plano_sem_ato("MINUTA DO PLANO DE CONTINGENCIA de 2026, Prefeitura Municipal de X",
                       URL_PDF_DE_PLANO)[1] == "minuta_ou_rascunho"),
        ("plano sem ato: versão para consulta não passa",
         plano_sem_ato("PLANO DE CONTINGENCIA — versão para consulta pública, 2026, "
                       "Prefeitura Municipal de X", URL_PDF_DE_PLANO)[1] == "minuta_ou_rascunho"),
        ("plano sem ato: sem órgão não passa",
         plano_sem_ato("PLANO DE CONTINGENCIA 2026 — procedimentos de resposta", URL_PDF_DE_PLANO)[1]
         == "plano_sem_identificacao"),
        ("plano sem ato: sem ano nem ciclo não passa",
         plano_sem_ato("Prefeitura Municipal de X — PLANO DE CONTINGENCIA de proteção e defesa "
                       "civil", URL_PDF_DE_PLANO)[1] == "plano_sem_identificacao"),
        # 03/10/2026, codebook 1.3: o julgado tem de SER o plano. Duas promoções da primeira rodada
        # real eram notícia institucional no domínio do ente, e é esta trava que as barra.
        ("notícia institucional no domínio do ente NÃO é o plano",
         e_o_proprio_plano("A Prefeitura Municipal de Toledo apresenta o plano de contingência "
                           "para emergências. Assessoria de Comunicação. Leia também.",
                           "https://toledo.pr.gov.br/noticia/prefeitura-apresenta-plano")[1]
         == "noticia_institucional_nao_e_o_plano"),
        ("página sem estrutura de plano NÃO é o plano",
         e_o_proprio_plano("Prefeitura Municipal de X — Plano de Contingência 2026. Acesse aqui.",
                           "https://x.sp.gov.br/pagina/plano")[1]
         == "noticia_institucional_nao_e_o_plano"),
        ("página COM estrutura de plano e sem marca de notícia é o plano",
         e_o_proprio_plano("Este plano estabelece os níveis de alerta e o acionamento das equipes, "
                           "com as atribuições de cada órgão e os pontos de apoio.",
                           "https://x.sp.gov.br/pagina/plano")[0] is True),
        ("URL de documento basta, mesmo com marca de notícia no texto",
         e_o_proprio_plano("Publicado em 2026 pela Assessoria de Comunicação. Este plano…",
                           URL_PDF_DE_PLANO)[0] is True),
        ("plano sem ato: o ano solto basta (e só aqui)",
         etapa2_citacao(PLANO_PUBLICADO_SEM_ATO)[0] is True
         and etapa2_citacao(PLANO_PUBLICADO_SEM_ATO)[2].get("sem_ato_de_aprovacao") is True),
        ("plano sem ato: a etapa 3 não exige fórmula de promulgação",
         etapa3_autoridade(PLANO_PUBLICADO_SEM_ATO, sem_ato_de_aprovacao=True)[0] is True
         and etapa3_autoridade(PLANO_PUBLICADO_SEM_ATO)[0] is False),
        ("a fronteira não se moveu: decreto sem número continua citação incompleta",
         etapa2_citacao(CANARIOS["citacao_incompleta"]["texto"])[1] == "citacao_incompleta"),
        ("o veredito carrega a marca para a ficha",
         julgar(PLANO_PUBLICADO_SEM_ATO, nome="Taió", uf="SC",
                url="https://defesacivil.taio.sc.gov.br/plano-2026.pdf")
         .get("sem_ato_de_aprovacao") is True),
        ("plano COM ato não leva a marca",
         julgar(CANARIOS["plano_novo"]["texto"], nome="Bonito", uf="MS",
                url=CANARIOS["plano_novo"]["url"]).get("sem_ato_de_aprovacao") is False),
        ("recorte do ato: o trecho isola o ato dentro da edição do diário",
         recortar_ato(EDICAO_DE_DIARIO, "institui o Plano de Contingência").strip().startswith("DECRETO Nº 88")
         and "PORTARIA" not in recortar_ato(EDICAO_DE_DIARIO, "institui o Plano de Contingência")),
        # 09/10/2026 (lote 2.2): a forma em que o texto chega em produção — espaço colapsado.
        ("recorte do ato funciona no texto colapsado de produção (A1-03)",
         recortar_ato(re.sub(r"\s+", " ", EDICAO_DE_DIARIO), "institui o Plano de Contingência")
         .strip().startswith("DECRETO Nº 88")
         and "PORTARIA Nº 45" not in recortar_ato(re.sub(r"\s+", " ", EDICAO_DE_DIARIO),
                                                  "institui o Plano de Contingência")),
        ("veredito sobre a edição colapsada cita o decreto 88, não a lei de rua (A1-03)",
         (lambda v: (v["criterios"].get("2_citacao", {}).get("dados") or {}).get("numero") == "88")(
             julgar(re.sub(r"\s+", " ", EDICAO_DE_DIARIO), nome="Bonito", uf="MS", url=URL_OFICIAL,
                    trecho="Institui o Plano de Contingência Municipal para o período de estiagem"))),
        ("citação em caixa mista no corpo não é cabeçalho",
         not RE_CABECALHO_DE_ATO.search("nos termos da Lei nº 12.608, de 10 de abril de 2012")),
        ("ato além dos 20.000 caracteres é achado pelo trecho no texto integral (A1-20)",
         (lambda v: (v["criterios"].get("2_citacao", {}).get("dados") or {}).get("numero") == "88")(
             julgar(("DIÁRIO OFICIAL DO MUNICÍPIO DE BONITO - MS PORTARIA Nº 1, DE 1 DE JULHO DE"
                     " 2026 Concede férias. " + "z " * 15000
                     + re.sub(r"\s+", " ", EDICAO_DE_DIARIO.split("ANO V EDIÇÃO Nº 1234")[1])),
                    nome="Bonito", uf="MS", url=URL_OFICIAL,
                    trecho="Institui o Plano de Contingência Municipal para o período de estiagem"))),
        ("recorte sem trecho devolve o texto inteiro",
         recortar_ato(EDICAO_DE_DIARIO, "") == EDICAO_DE_DIARIO),
        ("trecho ausente do texto devolve o texto inteiro",
         recortar_ato(EDICAO_DE_DIARIO, "isto não está na edição") == EDICAO_DE_DIARIO),
        ("texto sem cabeçalho de ato devolve o texto inteiro",
         recortar_ato("um texto qualquer com o trecho aqui " + "x" * 500, "trecho aqui")
         .endswith("x" * 10)),
        ("recorte minúsculo é recusado e devolve o texto inteiro",
         recortar_ato("DECRETO Nº 1\ncurto\nPORTARIA Nº 2\n" + "y" * 500, "curto").count("y") == 500),
        ("plano técnico sem número e SEM data não passa",
         etapa2_citacao("Plano de Contingência Municipal, versão 2026." + "x" * 500,
                        eh_plano_tecnico=True)[0] is False),
        # 04/10/2026 — proveniência de LAI. Documento entregue pelo órgão é prova de proveniência;
        # alegação de que foi entregue, não.
        ("proveniência de LAI completa dispensa a URL",
         etapa0_documento_primario(None, "PLANO DE CONTINGENCIA " * 60,
                                   {"tipo": "resposta_lai", "orgao": "Defesa Civil AM",
                                    "data": "01/10/2026", "hash": "a" * 64})[0] is True),
        ("proveniência sem hash NÃO passa",
         etapa0_documento_primario(None, "PLANO DE CONTINGENCIA " * 60,
                                   {"tipo": "resposta_lai", "orgao": "x", "data": "01/10/2026",
                                    "hash": ""})[0] is False),
        ("proveniência sem órgão NÃO passa",
         etapa0_documento_primario(None, "PLANO DE CONTINGENCIA " * 60,
                                   {"tipo": "resposta_lai", "orgao": "", "data": "01/10/2026",
                                    "hash": "a" * 64})[0] is False),
        ("proveniência sem data NÃO passa",
         etapa0_documento_primario(None, "PLANO DE CONTINGENCIA " * 60,
                                   {"tipo": "resposta_lai", "orgao": "x", "data": "",
                                    "hash": "a" * 64})[0] is False),
        ("tipo de proveniência desconhecido NÃO passa",
         etapa0_documento_primario(None, "PLANO DE CONTINGENCIA " * 60,
                                   {"tipo": "email", "orgao": "x", "data": "01/10/2026",
                                    "hash": "a" * 64})[0] is False),
        ("sem proveniência e sem URL continua recusando",
         etapa0_documento_primario(None, "PLANO DE CONTINGENCIA " * 60, None)[1]
         == "sem_documento_primario"),
        ("proveniência de LAI não dispensa o piso de texto",
         etapa0_documento_primario(None, "curto",
                                   {"tipo": "resposta_lai", "orgao": "x", "data": "01/10/2026",
                                    "hash": "a" * 64})[1] == "texto_nao_extraivel"),
        ("URL de fonte oficial continua valendo sozinha",
         etapa0_documento_primario("https://x.gov.br/a.pdf",
                                   "PLANO DE CONTINGENCIA " * 60)[0] is True),
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
