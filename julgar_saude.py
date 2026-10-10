#!/usr/bin/env python3
"""
julgar_saude.py — o juiz sobre a fila de saúde estadual
========================================================
Item 3 do handover "fechar os 27 e trocar para a v0.4" (editoria, 01/10/2026).

`julgar_filas.py` roda o juiz sobre as filas do MARÉ Legal e escreve em `municipios.json`. A fila
de saúde é outra (`pistas_imprensa_saude.json`), a pergunta é outra (plano ESTADUAL de saúde, e
agora também a COORDENAÇÃO em saúde) e o destino é outro (`saude_uf.json`). Juntar as duas num
script só exigiria um `if` em cada etapa; separadas, cada uma diz o que julga.

O QUE ELE FAZ
-------------
Para cada pista de domínio oficial: baixa o documento, extrai o texto (PDF ou HTML), e roda
`juiz.julgar(..., eh_estadual=True)` — as mesmas sete etapas do Legal, porque a pergunta "isto é um
ato oficial, identificado, citável, do Executivo, com objeto ex-ante?" não muda por ser saúde.

O que ele acrescenta é UMA classificação, e ela é regra lida no texto, não inferência: o ato que
**institui sala de situação ou centro de operações de emergência** é COORDENAÇÃO; o ato que
institui ou aprova **plano** é INSTRUMENTO. Quando o mesmo ato faz as duas coisas — e a 0195/2026 de
MT faz —, ele conta nas duas, porque são dois componentes e o documento sustenta os dois.

O QUE ELE NÃO FAZ
-----------------
- Não promove por título, notícia ou resumo: julga o texto do documento primário, preservado com
  hash. Pista de domínio que não é oficial nem é baixada — fica na fila para a triagem humana.
- Não decide escala nem peso. O degrau da v0.4 sai de `gerar_monitor_saude.instrumento_v04` e da
  classificação de coordenação abaixo, que são regra versionada.
- Não marca "não localizado". Essa decisão é do item 4 do handover e exige bateria completa por UF:
  ela vive em `marcar_nao_localizado.py`, não aqui.
- Não apaga pista: a recusa fica na fila com o motivo à vista.

USO
  python3 julgar_saude.py --autoteste
  python3 julgar_saude.py --relatorio          # julga e conta, não escreve
  python3 julgar_saude.py --aplicar            # julga e escreve em saude_uf.json
  python3 julgar_saude.py --relatorio --uf MA
"""
import io
import json
import pathlib
import re
import unicodedata
import sys
import urllib.parse

RAIZ = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

import juiz
# `oficial` vem do coletor que produziu as pistas, e não de uma cópia: a pergunta "este endereço é
# de fonte oficial?" tem de ter UMA resposta nos dois lados. Duas cópias divergem na primeira
# exceção de domínio que alguém acrescentar a um dos arquivos.
from coletar_saude_estadual import oficial
from coletores_base import buscar, gravar, hoje_editorial, ler, preservar_evidencia, rodar_autoteste

FILA = "pistas_imprensa_saude.json"
ALVO = "saude_uf.json"

# A classificação do que o ato INSTITUI. Literal, lida no texto do próprio ato.
# 02/10/2026: "grupo condutor" FALTAVA aqui, e e o primeiro termo que a editoria lista — foi o
# que fez a Portaria 764/2026 da Paraiba, que cria o GC El Nino/PB no ambito da SES-PB, passar
# pelo juiz sem ser reconhecida como estrutura de coordenacao. O defeito apareceu ao registrar o
# documento que a central ja havia lido: o degrau saia vazio com o ato na mao.
RE_COORDENACAO = re.compile(
    r"(sala\s+de\s+situa[çc][ãa]o|centro\s+de\s+opera[çc][õo]es\s+de\s+emerg[êe]ncia|\bCOES?\b"
    r"|grupo\s+condutor|\bGC\s+El\s*Ni[ñn]o"
    r"|gabinete\s+de\s+crise|comit[êe]\s+(?:gestor|de\s+crise|de\s+enfrentamento))", re.I)
RE_PLANO = re.compile(r"(plano\s+(?:estadual\s+)?(?:de\s+)?(?:conting[êe]ncia|prepara[çc][ãa]o|"
                      r"a[çc][ãa]o|enfrentamento|resposta))", re.I)
# Menção NOMINAL ao ciclo: é o que separa "criado para o ciclo" de "permanente".
RE_CICLO = re.compile(r"El\s*Ni[ñn]o", re.I)
RE_REATIVA = re.compile(r"(reativa|reinstitui|prorroga|renova|reconduz)", re.I)

# ── F2: a ligacao do setor saude com a coordenacao do estado ──────────────────────────────────
# Mede-se a FUNCAO, nao o orgao (METODOLOGIA §91): o ato pode ser do governo nomeando a saude no
# comite intersetorial, ou da propria saude integrando a defesa civil e os demais orgaos. Os dois
# cumprem F2, e e por isso que a busca e por DUAS direcoes no mesmo texto.
RE_F2_ESTRUTURA_INTERSETORIAL = re.compile(
    r"(comit[êe]\s+(?:intersetorial|interinstitucional|estadual|gestor)"
    r"|sala\s+de\s+governo|gabinete\s+(?:de\s+crise|integrado)"
    r"|grupo\s+de\s+trabalho\s+intersetorial|c[âa]mara\s+t[ée]cnica)", re.I)
# A5-02 (08/10/2026): esta regex era UMA só, com `re.I` e sem borda inicial na sigla — e por
# isso `SES\b` casava o FIM de qualquer palavra terminada em "ses": "meses", "fases", "doses",
# "interesses", "bases". Medido: um comitê que não nomeia a saúde pontuava F2 = 100 porque o ato
# dizia "a cada dois meses". A sigla é sigla: só casa em CAIXA ALTA, e por isso são duas regex.
RE_F2_SAUDE_POR_EXTENSO = re.compile(
    r"(secretaria\s+(?:de\s+estado\s+)?(?:estadual\s+)?d[ae]\s+sa[úu]de"
    r"|setor\s+sa[úu]de|pasta\s+d[ae]\s+sa[úu]de)", re.I)
RE_F2_SAUDE_SIGLA = re.compile(r"(\bSES(?:[-/\s]?[A-Z]{2})?\b|\bSESA[UB]?\b|\bSESAP[A-Z]?\b)")


def cita_saude(texto: str):
    """O match da menção à saúde, por extenso ou pela sigla em caixa alta. Função pura."""
    return RE_F2_SAUDE_POR_EXTENSO.search(texto or "") or RE_F2_SAUDE_SIGLA.search(texto or "")
RE_F2_DEFESA_CIVIL = re.compile(
    r"(defesa\s+civil|prote[çc][ãa]o\s+e\s+defesa\s+civil|coordenadoria\s+estadual\s+de\s+defesa)", re.I)
# A atribuicao DEFINIDA e o que separa 100 de 50: nome numa lista de composicao nao e funcao.
RE_F2_ATRIBUICAO = re.compile(
    r"(compete|caber[áa]|atribui[çc][õo]es|coordena(?:r|d[ao]|[çc][ãa]o\s+d[eo])"
    r"|respons[áa]vel\s+por|incumbe|exercer[áa]\s+a\s+coordena)", re.I)


# Onde termina o preâmbulo do ato. O "considerando" cita normas, sistemas e órgãos que o ato NÃO
# integra: medido no MT, onde a única menção à Defesa Civil estava num considerando sobre o S2iD
# nacional, e isso dava F2 = 100 a uma sala de situação composta só por áreas da própria secretaria.
RE_DISPOSITIVO = re.compile(r"\b(RESOLVE|DECRETA|RESOLVEM|DETERMINA)\b\s*:?", re.I)
# A composição é onde a integração formal acontece.
RE_COMPOSICAO = re.compile(
    r"(ser[áa]\s+compost[oa]|composi[çc][ãa]o|composto\s+por|integrad[oa]\s+por|integrar[áa]"
    r"|ser[áa]\s+integrad[oa]|membros\s+(?:natos|titulares))", re.I)
# Convidado não é membro: "poderá participar, na condição de convidado" é menção sem atribuição.
RE_CONVIDADO = re.compile(
    r"(convidad[oa]s?|poder[ãa]o?\s+participar|a\s+crit[ée]rio\s+do|quando\s+necess[áa]rio)", re.I)
JANELA_DE_COMPOSICAO = 1200


def corpo_do_ato(texto: str) -> str:
    """O texto a partir do dispositivo, sem o preâmbulo. Função pura.

    Sem dispositivo identificado, devolve o texto como veio — cortar pelo que não se achou seria
    pior do que ler o preâmbulo junto.
    """
    m = RE_DISPOSITIVO.search(texto or "")
    return (texto or "")[m.end():] if m else (texto or "")


def degrau_f2(texto: str) -> tuple:
    """(degrau, motivo) de F2, na escala de três degraus do §91.3. Função pura.

    `NOMEADA_COM_ATRIBUICAO` exige as duas coisas **no corpo do ato** (sem o preâmbulo): a saúde
    citada numa estrutura intersetorial do estado, ou a estrutura da saúde integrando formalmente a
    defesa civil **na composição** — e uma atribuição escrita. Órgão citado apenas como convidado,
    ou apenas num "considerando", é menção sem integração: degrau do meio. Nada disso, LAC — que é
    lacuna, não zero de estrutura.
    """
    t = texto or ""
    corpo = corpo_do_ato(t)
    # direção 1: estrutura intersetorial do estado que cita a saúde
    de_fora = bool(RE_F2_ESTRUTURA_INTERSETORIAL.search(corpo) and cita_saude(corpo))
    # direção 2: estrutura da própria saúde que integra a defesa civil NA COMPOSIÇÃO. A proximidade
    # importa: a palavra solta no meio do ato não diz que o órgão é membro.
    de_dentro = False
    convidado = False
    if RE_COORDENACAO.search(corpo):
        for m in RE_F2_DEFESA_CIVIL.finditer(corpo):
            perto = corpo[max(0, m.start() - JANELA_DE_COMPOSICAO):m.end() + JANELA_DE_COMPOSICAO]
            if RE_CONVIDADO.search(corpo[max(0, m.start() - 300):m.end() + 120]):
                convidado = True
                continue
            if RE_COMPOSICAO.search(perto):
                de_dentro = True
                break
    if not (de_fora or de_dentro):
        if convidado:
            return ("LISTADA_SEM_ATRIBUICAO",
                    "o ato cita a defesa civil como convidada, sem integrá-la à composição")
        return "LAC", "o ato não liga o setor saúde à coordenação do estado"
    onde = ("estrutura intersetorial do estado com a saúde citada" if de_fora
            else "estrutura da saúde que integra a defesa civil na composição")
    # A direção 2 só vale quando o ato é da saúde — e aí o colegiado é dela.
    tem_atribuicao = atribuicao_da_saude(corpo, estrutura_da_saude=(de_dentro and ato_e_da_saude(t)))
    if tem_atribuicao:
        return "NOMEADA_COM_ATRIBUICAO", f"{onde}, com atribuição escrita no ato"
    return "LISTADA_SEM_ATRIBUICAO", f"{onde}, sem atribuição escrita"


# "Compete ao comitê coordenar" é atribuição DO COMITÊ, não da saúde — e era contada como da
# saúde (A5-02). Duas travas: o verbo tem de estar perto de uma menção à saúde, e o sujeito dele
# não pode ser o próprio colegiado. A janela de 300 caracteres é a do relatório.
JANELA_DE_ATRIBUICAO = 300
RE_SUJEITO_COLEGIADO = re.compile(
    r"(compete|caber[áa]|incumbe)\s+a?o?\s*(comit[êe]|grupo|c[âa]mara|gabinete|conselho|colegiado)", re.I)


def atribuicao_da_saude(corpo: str, estrutura_da_saude: bool = False) -> bool:
    """Há verbo de atribuição ligado ao setor saúde, e não ao próprio colegiado. Função pura.

    `estrutura_da_saude` distingue as DUAS direções do §91.3, e a distinção importa:

    - direção 1, o comitê do GOVERNO que cita a saúde: "compete ao comitê coordenar" é
      competência do comitê, não da saúde, e não conta. É o defeito A5-02.
    - direção 2, a estrutura da PRÓPRIA saúde que integra a defesa civil: ali o colegiado **é** o
      órgão de saúde, e "compete-lhe coordenar" atribui à saúde. Aplicar a trava da direção 1 aqui
      recusaria o ato da Paraíba, que é justamente o caso que o degrau cheio existe para medir.
    """
    for m in RE_F2_ATRIBUICAO.finditer(corpo or ""):
        trecho = corpo[max(0, m.start() - 40):m.end() + 60]
        if RE_SUJEITO_COLEGIADO.search(trecho) and not estrutura_da_saude:
            continue                       # a competência é do comitê, não da saúde
        if estrutura_da_saude:
            return True
        perto = corpo[max(0, m.start() - JANELA_DE_ATRIBUICAO):m.end() + JANELA_DE_ATRIBUICAO]
        if cita_saude(perto):
            return True
    return False


def atribuicao_citada(texto: str) -> str:
    """O trecho do ato que fundamenta F2 — artigo, inciso ou a frase da atribuicao. Funcao pura.

    Guardar o trecho e exigencia do handover: a classificacao tem de poder ser conferida sem
    reabrir o documento.
    """
    t = texto or ""
    m = RE_F2_ATRIBUICAO.search(t)
    if not m:
        return None
    ini = max(0, m.start() - 120)
    pedaco = re.sub(r"\s+", " ", t[ini:m.end() + 180]).strip()
    art = re.search(r"(art\.?\s*\d+[ºo]?(?:[,\s]*(?:inciso\s*)?[IVXLC]+)?)", pedaco, re.I)
    return (art.group(1) + " — " if art else "") + pedaco[:240]


# =============================================================================================
# A exceção de autoridade da camada de saúde — DECISÃO DA EDITORIA, 01/10/2026, 16h UTC
# =============================================================================================
# A pergunta que a execução de hoje levantou: o plano de contingência de saúde publicado no portal
# oficial da secretaria estadual, SEM ato de aprovação no texto, vale como documento primário? A
# editoria decidiu que sim — e pôs três condições, que são o que esta seção implementa:
#
#   (1) domínio oficial da SES ou do governo do estado;
#   (2) o documento identifica ÓRGÃO, TÍTULO e ANO ou ciclo;
#   (3) o registro traz a observação "sem ato de aprovação localizado", substituída pelo ato
#       quando ele aparecer.
#
# A exceção vale **só para a camada de saúde** (MARÉ Saúde, peso zero). `juiz.etapa3_autoridade`
# continua intocada: ela é a régua do MARÉ Legal, e foi justamente por ser dela que recusou 14 dos
# 27 planos estaduais de saúde. O que muda é que a camada de saúde passa a ter a sua, declarada.
RE_ORGAO_SAUDE = re.compile(
    r"(secretaria\s+(?:de\s+estado\s+)?(?:estadual\s+)?d[ae]\s+sa[úu]de"
    r"|secretaria\s+d[ae]\s+sa[úu]de\s+d[eo]\s+estado"
    # 05/10/2026: esta linha trazia DOIS caracteres de backspace (0x08) no lugar das bordas de palavra —
    # escape de shell que virou byte quando o arquivo foi escrito por heredoc, em 01/10. O
    # padrão não dava erro: ele simplesmente nunca casava, e a alternativa "SES-XX" ficou morta
    # por quatro dias dentro do juiz da saúde. Achado pelo portão de escrita portável, que
    # passou a varrer caractere de controle no fonte.
    # 05/10/2026: esta linha trazia DOIS caracteres de backspace (0x08) no lugar dos `\b` —
    # escape de shell que virou byte quando o arquivo foi escrito por heredoc, em 01/10. O
    # padrão não dava erro: ele simplesmente nunca casava, e a alternativa "SES-XX" ficou
    # morta por quatro dias dentro do juiz da saúde. Achado pelo portão de escrita portável,
    # que passou a varrer caractere de controle no fonte.
    r"|\bSES[-/\s]?[A-Z]{2}\b"
    r"|funda[çc][ãa]o\s+de\s+vigil[âa]ncia\s+em\s+sa[úu]de"
    r"|superintend[êe]ncia\s+de\s+vigil[âa]ncia\s+em\s+sa[úu]de)", re.I)
RE_ANO_OU_CICLO = re.compile(r"\b20\d{2}\b")


def dominio_de_saude_estadual(url: str, texto: str) -> bool:
    """Condição (1): domínio oficial da SES ou do governo do estado. Função pura.

    Oficial já exige `.gov.br`; o que se acrescenta aqui é que o documento seja da secretaria
    ESTADUAL de saúde — pelo subdomínio (`saude.XX.gov.br`, `ses.XX.gov.br`, `fvs.am.gov.br`) ou,
    quando o portal do estado publica tudo num domínio só, pelo próprio texto nomeando o órgão.
    Domínio municipal não entra: a camada é estadual, e `saude.goiania.go.gov.br` é de Goiânia."""
    if not oficial(url):
        return False
    host = urllib.parse.urlparse(url or "").netloc.lower()
    # A5-01, causa (e): isto contava PARTES do host, e por isso recusava o domínio do instrumento
    # vigente do ES — `mosquito.saude.es.gov.br` tem cinco. Recusava também `cvs.saude.sp.gov.br`
    # e `antigo.saude.sc.gov.br`, que são estaduais. O que distingue estado de município não é o
    # número de pontos: é o sufixo `.<uf>.gov.br` e a ausência de nome de município daquela UF.
    estadual = bool(re.search(r"\.[a-z]{2}\.gov\.br$", host)) and not host_de_municipio(host)
    return estadual and bool(RE_ORGAO_SAUDE.search(texto or "") or RE_ORGAO_SAUDE.search(host))


_MUNICIPIOS_CACHE = None


def nomes_de_municipio() -> set:
    """Os nomes de município normalizados, da referência do IBGE. Lido uma vez."""
    global _MUNICIPIOS_CACHE
    if _MUNICIPIOS_CACHE is None:
        _MUNICIPIOS_CACHE = set()
        try:
            caminho = pathlib.Path(__file__).resolve().parent / "data" / "municipios_ibge_referencia.json"
            for m in json.loads(caminho.read_text(encoding="utf-8")):
                nome = unicodedata.normalize("NFD", str(m.get("nome", "")).lower())
                nome = "".join(c for c in nome if unicodedata.category(c) != "Mn")
                nome = re.sub(r"[^a-z]", "", nome)
                # Nome curto demais vira falso positivo em subdomínio ("ses" é sigla, "una" é
                # município de MG e pedaço de palavra). O corte é por tamanho, e é declarado.
                if len(nome) >= 5:
                    _MUNICIPIOS_CACHE.add(nome)
        except Exception:
            _MUNICIPIOS_CACHE = set()
    return _MUNICIPIOS_CACHE


# Palavras que nomeiam a FUNÇÃO do subdomínio, e que por acaso também são nome de município.
# Medido em 08/10/2026: existe o município de **Saúde**, na Bahia, e sem esta lista o cache do
# IBGE fazia `saude.es.gov.br` — o subdomínio da secretaria de saúde de QUALQUER estado — ser
# lido como domínio municipal. A regra seria recusar exatamente o que ela existe para aceitar.
SERVICO_NAO_E_MUNICIPIO = {"saude", "portal", "transparencia", "servicos", "cidadao", "legisla",
                           "imprensa", "diario", "sistemas", "central", "progresso", "capital"}


def host_de_municipio(host: str) -> bool:
    """O host nomeia um município? Função pura sobre o cache. `saude.goiania.go.gov.br` → True."""
    partes = [p for p in (host or "").split(".")
              if p not in ("gov", "br", "www", "portal") and p not in SERVICO_NAO_E_MUNICIPIO]
    nomes = nomes_de_municipio()
    return any(p in nomes for p in partes)


def identifica_orgao_titulo_e_ano(texto: str) -> tuple:
    """Condição (2): (ok, o que faltou). Função pura."""
    faltam = []
    if not RE_ORGAO_SAUDE.search(texto or ""):
        faltam.append("órgão")
    if not RE_PLANO.search(texto or ""):
        faltam.append("título do plano")
    if not RE_ANO_OU_CICLO.search(texto or ""):
        faltam.append("ano ou ciclo")
    return (not faltam), ", ".join(faltam)


def autoridade_de_saude(texto: str, url: str) -> tuple:
    """(ok, motivo, trecho) — a etapa 3 da camada de saúde. Função pura.

    Primeiro tenta a régua normal: ato do Executivo com fórmula de promulgação passa por ela e nem
    chega aqui. Só então, e só para plano publicado em domínio de SES, aplica a exceção."""
    ok, motivo, trecho = juiz.etapa3_autoridade(texto)
    if ok:
        return True, "", trecho
    if motivo != "autoridade_nao_confirmada":
        # `executivo_pendente` (aprovação por colegiado) NÃO entra na exceção: ali existe um ato, e
        # ele é de outro órgão. A exceção é para a AUSÊNCIA de ato, não para o ato errado.
        return False, motivo, trecho
    if not dominio_de_saude_estadual(url, texto):
        return False, "autoridade_nao_confirmada", "sem ato e fora de domínio de secretaria estadual de saúde"
    ok2, faltou = identifica_orgao_titulo_e_ano(texto)
    if not ok2:
        return False, "autoridade_nao_confirmada", f"sem ato e o documento não identifica: {faltou}"
    return True, "", "exceção de autoridade da camada de saúde (editoria, 01/10/2026): plano em domínio de SES, com órgão, título e ano identificados, sem ato de aprovação localizado"


def texto_do_documento(corpo: bytes, url: str) -> str:
    """O texto corrido do documento, de PDF ou de HTML. Função pura (não busca nada).

    PDF sem texto extraível devolve string vazia, e o juiz reprova na etapa 0 — que é o certo: um
    PDF digitalizado sem OCR não é documento lido, e tratar vazio como "sem objeto ex-ante" seria
    reprovar o ato pelo defeito do arquivo. O motivo fica visível na fila."""
    if (url or "").lower().split("?")[0].endswith(".pdf") or corpo[:5] == b"%PDF-":
        try:
            from pdfminer.high_level import extract_text
            return re.sub(r"\s+", " ", extract_text(io.BytesIO(corpo)) or "")
        except Exception:  # noqa: BLE001
            return ""
    bruto = corpo.decode("utf-8", "replace") if isinstance(corpo, bytes) else str(corpo)
    bruto = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", bruto, flags=re.S | re.I)
    import html as _html
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", bruto)))


def o_que_institui(texto: str) -> set:
    """{'coordenacao'} | {'instrumento'} | os dois | conjunto vazio. Função pura.

    Um ato pode instituir as duas coisas, e nesse caso conta nas duas: são dois componentes do
    índice, e o mesmo documento sustenta os dois. A Portaria 0195/2026 de MT é exatamente esse
    caso — institui o processo de elaboração do plano E a sala de situação permanente."""
    achados = set()
    # A5-03 (08/10/2026): "coordenacao" era marcada por "comitê gestor|de crise|de enfrentamento",
    # "gabinete de crise" e "sala de situação" em QUALQUER texto — e F1 é, pelo §91, estrutura da
    # SECRETARIA DE SAÚDE. Com isso o decreto de MG (Sala de Situação da Defesa Civil) saía
    # F1 = CRIADO_CICLO (100), e o despacho de SP (comitê de mudanças climáticas) saía
    # F1 = PERMANENTE (45). Um terço do componente creditado a estrutura que não é da saúde.
    # Comitê de governo é F2; F1 exige que o ato seja da saúde.
    if RE_COORDENACAO.search(texto or "") and estrutura_e_da_saude(texto or ""):
        achados.add("coordenacao")
    if RE_PLANO.search(texto or ""):
        achados.add("instrumento")
    return achados


# A AUTORIA do ato, que é mais larga que o nome do órgão: um ato assinado por "O SECRETÁRIO DE
# ESTADO DE SAÚDE" é da saúde, e `RE_ORGAO_SAUDE` só conhecia a forma feminina ("secretaria").
# Medido ao escrever a trava do A5-03: ela recusava a Portaria 0666/2024, que é da própria SES e
# está assinada assim. Entram também as siglas de gabinete que os atos usam (GS/SES, GBSES).
RE_AUTORIA_SAUDE = re.compile(
    r"(secret[áa]ri[oa]\s+(?:de\s+estado\s+)?(?:d[aeo]\s+)?sa[úu]de"
    r"|\bGB?S?/?SES\b|\bGBSES\b|\bGS/SES\b)", re.I)


def ato_e_da_saude(texto: str) -> bool:
    """O ato é da secretaria de saúde — pelo órgão ou por quem o assina. Função pura."""
    return bool(RE_ORGAO_SAUDE.search(texto or "") or RE_AUTORIA_SAUDE.search(texto or ""))


def estrutura_e_da_saude(texto: str) -> bool:
    """A estrutura de coordenação é da secretaria de saúde? Função pura.

    Duas formas de provar, as duas do relatório: o ato é da saúde (o órgão aparece no cabeçalho ou
    na assinatura, isto é, nos primeiros ou nos últimos 1.200 caracteres), ou a estrutura é criada
    "no âmbito da Secretaria de Estado da Saúde" — o órgão a menos de 300 caracteres dela."""
    t = texto or ""
    cabeca, pe = t[:1200], t[-1200:]
    if ato_e_da_saude(cabeca) or ato_e_da_saude(pe):
        return True
    for m in RE_COORDENACAO.finditer(t):
        perto = t[max(0, m.start() - JANELA_DE_ATRIBUICAO):m.end() + JANELA_DE_ATRIBUICAO]
        if ato_e_da_saude(perto):
            return True
    return False


def degrau_coordenacao(texto: str, data: str) -> tuple:
    """(degrau, motivo) na escala aprovada da v0.4. Função pura.

    CRIADO_CICLO exige que o ato NOMEIE o ciclo e seja de 2026 — as duas coisas: um ato de 2026 que
    não nomeia o ciclo é estrutura permanente que por acaso é recente, e afirmar criação para o
    ciclo seria ler intenção no calendário. REATIVADO_CICLO exige o verbo de reativação mais a
    menção ao ciclo. Sem menção, PERMANENTE — a estrutura existe, e é o que se pode afirmar."""
    t = texto or ""
    cita_ciclo = bool(RE_CICLO.search(t))
    ano = None
    m = re.search(r"/(\d{4})$", (data or "").strip())
    if m:
        ano = int(m.group(1))
    if cita_ciclo and ano == 2026 and RE_REATIVA.search(t):
        return "REATIVADO_CICLO", "ato de 2026 que reativa estrutura e nomeia o ciclo"
    if cita_ciclo and ano == 2026:
        return "CRIADO_CICLO", "ato de 2026 que institui a estrutura e nomeia o ciclo"
    if cita_ciclo:
        return "REATIVADO_CICLO", "ato que nomeia o ciclo, sem data de 2026 confirmada"
    return "PERMANENTE", "ato institui a estrutura e não nomeia o ciclo"


def status_instrumento(categoria: str) -> str:
    """A categoria do juiz → o vocabulário de `saude_uf.json`. Função pura.

    `plano_elaboracao` → ELAB; `plano` (ato a partir do Boletim nº 1) → NOVO; `plano_antigo` (ato
    anterior) → VIG, porque plano de ciclo anterior que segue vigente é recorrente, não novo. A
    divisão do VIG em revisado/outro risco é da v0.4 e acontece em `instrumento_v04`, com o
    `consist` da UF — não aqui."""
    return {"plano_elaboracao": "ELAB", "plano": "NOVO", "plano_antigo": "VIG"}.get(categoria)


# ── O risco do CICLO, no TÍTULO, e só risco explícito (01/10/2026) ───────────────────────────
# Isto nasceu de uma promoção falsa, e de duas tentativas de consertá-la.
#
# O caso: um **plano de contingência do SARAMPO de 2019**, do portal da SES-MG, foi promovido como
# instrumento de saúde de MG para este ciclo — e como a sua coordenação, porque o plano menciona
# níveis de ativação por dentro. Sarampo não é risco deste ciclo.
#
# Primeira tentativa: exigir um risco do ciclo em qualquer lugar do texto. **Não funcionou, e a
# medição mostrou por quê**: em 77 mil caracteres, o documento casou "dengue" numa frase de
# diagnóstico diferencial ("suspeita de dengue, mas com clínica compatível com sarampo") e
# "emergências em saúde pública" no próprio título, porque esse é o arcabouço genérico que o plano
# de qualquer doença usa. Palavra solta em documento longo não é assunto do documento.
#
# Regra em vigor: o risco do ciclo tem de estar no **título** do documento, e tem de ser **risco
# explícito**. O arcabouço genérico de emergências em saúde pública NÃO conta sozinho: ele cabe em
# sarampo, em cólera e em acidente radiológico com a mesma naturalidade. Um instrumento genérico
# existe e pode valer — o PPResp/MT é um —, mas então ele vai para verificação humana, com o ato
# lido, que foi exatamente como MT entrou. Na dúvida, o classificador não classifica.
RE_RISCO_DO_CICLO = re.compile(
    r"(el\s*ni[ñn]o"
    r"|arbovirose|dengue|chikungunya|zika"
    r"|estiagem|\bseca\b|escassez\s+h[íi]drica"
    r"|onda[s]?\s+de\s+calor|excesso\s+de\s+calor|calor\s+extremo"
    r"|queimada|fuma[çc]a|inc[êe]ndio\s+florestal|qualidade\s+do\s+ar"
    r"|leptospirose|doen[çc]as?\s+diarreicas|hepatite\s+a\b"
    r"|qualidade\s+da\s+[áa]gua"
    r"|eventos?\s+clim[áa]ticos|mudan[çc]as?\s+clim[áa]ticas)", re.I)


def trata_de_risco_do_ciclo(titulo: str) -> tuple:
    """(ok, o que casou) — sobre o TÍTULO do documento. Função pura.

    Exigido na camada de saúde, e só nela: o MARÉ Saúde mede preparação para os riscos DESTE ciclo.
    Um plano de saúde excelente para outra doença é um documento excelente que não responde à
    pergunta do índice — a mesma distinção que o degrau `VIG_OUTRO_RISCO` faz no instrumento
    estadual. Não é demérito do documento; é escopo do índice."""
    achados = sorted({m.group(0).lower() for m in RE_RISCO_DO_CICLO.finditer(titulo or "")})
    return bool(achados), ", ".join(achados[:6])


# A5-37: `etapa2`/`extrair_data` tomavam a PRIMEIRA data do texto, e o preâmbulo de um ato cita
# as normas em que ele se apoia. A Resolução SESA 680/2008 do PR saiu com data 03/06/1987 — a da
# lei citada no "considerando". A data do ato está no cabeçalho dele, junto do número.
RE_CABECALHO_DE_ATO = re.compile(
    r"((?:portaria|decreto|resolu[çc][ãa]o|delibera[çc][ãa]o|instru[çc][ãa]o\s+normativa)"
    r"[^\n]{0,120}?\bn?[ºo°]?\s*[\d.]+[^\n]{0,60}?"
    r"\bde\s+(\d{1,2})\s+de\s+([a-zç]+)\s+de\s+(\d{4}))", re.I)
MESES_PT = {"janeiro": 1, "fevereiro": 2, "marco": 3, "março": 3, "abril": 4, "maio": 5,
            "junho": 6, "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10,
            "novembro": 11, "dezembro": 12}


def data_do_cabecalho(texto: str):
    """dd/mm/aaaa do cabeçalho do ato, ou None. Função pura."""
    m = RE_CABECALHO_DE_ATO.search(texto or "")
    if not m:
        return None
    dia, mes, ano = m.group(2), m.group(3).lower(), m.group(4)
    n = MESES_PT.get(mes)
    return f"{int(dia):02d}/{n:02d}/{ano}" if n else None


def titulo_do_documento(texto: str, titulo_da_pista: str, url: str) -> str:
    """O título que vai para o registro público. Função pura.

    O título da PISTA vem do metabuscador, e para um PDF ele costuma ser o host ou um fragmento de
    metadado — "GOVERNO DO ESTADO DE MINAS GERAIS - saude.mg.gov.br" foi o que apareceu de verdade
    em 01/10/2026. Esse texto vira nome de documento na ficha do estado, e nome de documento é
    afirmação sobre o documento.

    Então: quando o próprio texto traz o nome do plano, é ele que vale. O título da pista só fica
    quando o texto não nomeia o plano — e, mesmo aí, sem o host, que não é nome de nada."""
    m = RE_PLANO.search(texto or "")
    if m:
        # A frase inteira do título, do começo do nome do plano até a pontuação ou o ano.
        trecho = (texto[m.start():m.start() + 180]).strip()
        corte = re.search(r"(?<=\S)\s*(?:\.|;|—|–| - |Sum[áa]rio|Apresenta[çc][ãa]o)", trecho)
        titulo = (trecho[:corte.start()] if corte else trecho).strip(" ,.-;")
        if len(titulo) >= 20:
            return titulo
    host = urllib.parse.urlparse(url or "").netloc.lower()
    limpo = re.sub(r"\s*[-|–]\s*" + re.escape(host) + r"\s*$", "", (titulo_da_pista or ""), flags=re.I)
    return limpo.strip() or (titulo_da_pista or "")


def julgar_camada_saude(texto: str, uf: str, url: str, plano_tecnico: bool,
                        titulo_da_pista: str = "") -> dict:
    """As sete etapas do juiz, com a etapa 3 da camada de saúde. Devolve o mesmo veredito.

    A orquestração é repetida aqui de propósito, e não delegada a `juiz.julgar`: aquele devolve na
    etapa 3 e as etapas 4 a 6 nunca rodam, de modo que natureza, família e categoria ficariam sem
    resposta — e sem categoria não há registro. O que não se repete é NENHUMA das réguas: todas as
    outras etapas são chamadas de `juiz.py`, versionadas lá."""
    v = {"promove": False, "motivo": None, "codebook": juiz.CODEBOOK_VERSAO, "criterios": {},
         "categoria": None, "data": None, "natureza": None, "municipio": uf, "uf": uf, "url": url}

    ok, motivo, prova = juiz.etapa0_documento_primario(url, texto)
    v["criterios"]["0_documento_primario"] = {"ok": ok, "trecho": prova}
    if not ok:
        v["motivo"] = motivo; return v

    ok, motivo, trecho = juiz.etapa1_identidade(texto, uf, uf)
    v["criterios"]["1_identidade"] = {"ok": ok, "trecho": trecho}
    if not ok:
        v["motivo"] = motivo; return v

    ok, motivo, dados = juiz.etapa2_citacao(texto, plano_tecnico)
    v["criterios"]["2_citacao"] = {"ok": ok, "trecho": dados.get("trecho", ""), "dados": dados}
    v["data"] = dados.get("data")
    v["numero"] = dados.get("numero")
    if not ok:
        v["motivo"] = motivo; return v

    ok, motivo, trecho = autoridade_de_saude(texto, url)
    v["criterios"]["3_autoridade"] = {"ok": ok, "trecho": trecho}
    if not ok:
        v["motivo"] = motivo; return v
    if trecho.startswith("exceção de autoridade"):
        # Condição (3) da decisão: a observação acompanha o registro, e sai quando o ato aparecer.
        v["excecao_autoridade"] = "sem ato de aprovação localizado"

    natureza, motivo_nat, provas = juiz.etapa4_natureza(texto)
    v["natureza"] = natureza
    v["criterios"]["4_natureza"] = {"ok": natureza == "EX_ANTE", "trecho": motivo_nat, **provas}
    if natureza == "RESPOSTA":
        v["motivo"] = "resposta"; v["encaminhar"] = "atos_resposta"; return v
    if natureza != "EX_ANTE":
        v["motivo"] = "natureza_duvidosa"; return v

    ok, familia, trecho = juiz.etapa5_familia_de_risco(texto)
    v["criterios"]["5_familia_de_risco"] = {"ok": ok, "familia": familia if ok else None, "trecho": trecho}
    if not ok:
        v["motivo"] = familia; return v
    v["familia_de_risco"] = familia

    # Condição da CAMADA: o documento trata de risco deste ciclo. Um plano de sarampo de 2019 passou
    # por todas as etapas anteriores em 01/10/2026 e foi promovido como instrumento E coordenação de
    # MG — foi o que fez esta etapa existir.
    titulo = titulo_do_documento(texto, titulo_da_pista, url)
    v["titulo_do_documento"] = titulo
    ok, casou = trata_de_risco_do_ciclo(titulo)
    v["criterios"]["5b_risco_do_ciclo"] = {"ok": ok, "titulo": titulo,
                                           "trecho": casou or "nenhum risco do ciclo no título"}
    if not ok:
        v["motivo"] = "risco_fora_do_ciclo"; return v

    categoria, motivo_cat = juiz.etapa6_categoria(texto, v["data"], True)
    v["criterios"]["6_categoria"] = {"ok": categoria is not None, "trecho": motivo_cat}
    if categoria is None:
        v["motivo"] = motivo_cat.split(":")[0]; return v

    v["categoria"] = categoria
    v["promove"] = True
    v["motivo"] = None
    return v


def julgar_pista(p: dict, buscar_fn=None) -> dict:
    """Baixa, lê e julga uma pista. Devolve o veredito com o que o ato institui."""
    url = p.get("url")
    uf = p.get("uf")
    try:
        corpo = (buscar_fn or buscar)(url, timeout=150, origem="julgar_saude")
    except Exception as e:  # noqa: BLE001
        return {"promove": False, "motivo": f"documento não baixado: {type(e).__name__}", "uf": uf}
    texto = texto_do_documento(corpo, url)
    if not texto.strip():
        return {"promove": False, "motivo": "documento sem texto extraível (PDF sem OCR?)", "uf": uf}
    institui = o_que_institui(texto)
    # O plano de contingência estadual de saúde é, na maioria dos estados, um DOCUMENTO TÉCNICO:
    # ele traz título, ano e órgão, e o ato que o aprova é outro papel. O juiz tem exceção
    # declarada para esse caso (`eh_plano_tecnico`), e a regra para ligá-la é a que o próprio
    # handover do juiz fixou: ligar quando o documento é plano E não traz tipo e número de ato no
    # texto. A data continua obrigatória — sem data não há como situar o ato no ciclo.
    plano_tecnico = ("instrumento" in institui
                     and juiz.RE_TIPO_E_NUMERO.search(texto) is None)
    v = julgar_camada_saude(texto, uf, url, plano_tecnico, p.get("titulo") or "")
    v["institui"] = sorted(institui)
    v["uf"] = uf
    if v.get("promove"):
        v["hash_evidencia"] = preservar_evidencia(
            corpo, url, "pdf" if (url or "").lower().endswith(".pdf") else "html", "julgar_saude")
        # As duas funcoes da coordenacao, cada uma classificada por conta propria: um ato que
        # cumpre as duas pontua nas duas, e dois atos que cumprem uma cada pontuam o mesmo.
        # F2 nao depende de o ato instituir estrutura de saude — um decreto do governo que nomeia
        # a SES no comite intersetorial cumpre F2 sem instituir nada na saude.
        f2, motivo_f2 = degrau_f2(texto)
        if f2 != "LAC":
            v["coordenacao_f2"] = {"degrau": f2, "motivo": motivo_f2,
                                   "atribuicao_citada": atribuicao_citada(texto)}
        if "coordenacao" in v["institui"]:
            v["coordenacao"] = dict(zip(("degrau", "motivo"), degrau_coordenacao(texto, v.get("data"))))
            v["coordenacao_f1"] = dict(v["coordenacao"])
        if "instrumento" in v["institui"]:
            v["status_instrumento"] = status_instrumento(v.get("categoria"))
    return v


def aplicar(su: dict, v: dict, titulo: str, url: str) -> list:
    """Escreve o veredito em `saude_uf.json`. Devolve o que mudou. Não apaga o que já existia.

    O instrumento entra como item NOVO em `instrumentos[]` — a lista é a fonte de verdade desde
    18/09/2026 e o campo de topo é recalculado do melhor item a cada geração. A coordenação é um
    campo único por UF: quando já existe uma com degrau igual ou maior, a nova não rebaixa."""
    uf = v["uf"]
    u = (su.setdefault("uf", {})).setdefault(uf, {})
    mudou = []
    hoje = hoje_editorial().strftime("%d/%m/%Y")
    if v.get("status_instrumento"):
        item = {"status": v["status_instrumento"], "orgao": f"SES-{uf}", "doc": titulo,
                "observacao": v.get("excecao_autoridade"),
                "numero": v.get("numero"), "data": v.get("data"), "url": url,
                "natureza_doc": v.get("natureza"), "tipo": "saude_do_ciclo",
                "hash_evidencia": v.get("hash_evidencia"),
                "justificativa_ex_ante": (f"promovido por julgar_saude.py em {hoje}, codebook "
                                          f"{v.get('codebook')}: documento primário baixado e lido, "
                                          f"sete etapas aprovadas")}
        u.setdefault("instrumentos", []).append(item)
        u["data_verificacao"] = hoje
        u["log_ref"] = f"julgar_saude_{hoje.replace('/', '-')}"
        mudou.append(f"instrumento {v['status_instrumento']}")
    # 02/10/2026: a coordenacao passa a ter duas funcoes, cada uma com o seu documento. O campo
    # `coordenacao.status` continua existindo e continua sendo F1 — e o que o motor antigo le, e
    # apagar isso no meio da travessia deixaria a coordenacao em branco em quem ja foi lido.
    if v.get("coordenacao_f2"):
        ordem_f2 = ["LAC", "LISTADA_SEM_ATRIBUICAO", "NOMEADA_COM_ATRIBUICAO"]
        coord = u.setdefault("coordenacao", {})
        atual_f2 = (coord.get("f2") or {}).get("status")
        novo_f2 = v["coordenacao_f2"]["degrau"]
        if atual_f2 is None or ordem_f2.index(novo_f2) > ordem_f2.index(atual_f2):
            coord["f2"] = {"status": novo_f2, "doc": titulo, "numero": v.get("numero"),
                           "data": v.get("data"), "url": url,
                           "hash_evidencia": v.get("hash_evidencia"),
                           "justificativa_degrau": v["coordenacao_f2"]["motivo"],
                           "atribuicao_citada": v["coordenacao_f2"].get("atribuicao_citada"),
                           "data_verificacao": hoje,
                           "log_ref": f"julgar_saude_{hoje.replace('/', '-')}"}
            mudou.append(f"coordenação F2 {novo_f2}")
    if v.get("coordenacao"):
        ordem = ["LAC", "ANUNCIADO", "PERMANENTE", "REATIVADO_CICLO", "CRIADO_CICLO"]
        atual = (u.get("coordenacao") or {}).get("status")
        novo = v["coordenacao"]["degrau"]
        if atual is None or ordem.index(novo) > ordem.index(atual):
            guardado_f2 = (u.get("coordenacao") or {}).get("f2")
            u["coordenacao"] = {"status": novo, "orgao": f"SES-{uf}", "doc": titulo,
                                "observacao": v.get("excecao_autoridade"),
                                "numero": v.get("numero"), "data": v.get("data"), "url": url,
                                "hash_evidencia": v.get("hash_evidencia"),
                                "justificativa_degrau": v["coordenacao"]["motivo"],
                                "data_verificacao": hoje,
                                "log_ref": f"julgar_saude_{hoje.replace('/', '-')}"}
            # F1 e a mesma classificacao, guardada tambem com o nome da funcao; F2 que ja existia
            # nao se perde quando F1 melhora.
            u["coordenacao"]["f1"] = {
                "status": novo, "doc": titulo, "numero": v.get("numero"), "data": v.get("data"),
                "url": url, "hash_evidencia": v.get("hash_evidencia"),
                "justificativa_degrau": v["coordenacao"]["motivo"], "data_verificacao": hoje}
            if guardado_f2:
                u["coordenacao"]["f2"] = guardado_f2
            mudou.append(f"coordenação F1 {novo}")
    return mudou


def autoteste() -> int:
    t_sala = ("PORTARIA Nº 0666/2024 — Dispõe sobre a instituição da Sala de Situação em Saúde para "
              "o enfrentamento das Mudanças Climáticas. O SECRETÁRIO DE ESTADO DE SAÚDE resolve:")
    t_plano = ("RESOLUÇÃO Nº 10 — Aprova o Plano Estadual de Contingência das Arboviroses. "
               "O SECRETÁRIO resolve:")
    # 08/10/2026 (A5-03): os fixtures passam a trazer o CABEÇALHO REAL do ato. A régua agora
    # exige que a estrutura seja da saúde, e trecho mínimo sem autoria não prova isso — nem
    # deveria. O cabeçalho abaixo é o do ato de MT: "GBSES" é o gabinete do secretário.
    t_dois = ("PORTARIA Nº 0195/2026/GBSES — Secretaria de Estado de Saúde de Mato Grosso. "
              "Institui o processo de elaboração do Plano Estadual de "
              "Preparação e Resposta a Emergências em Saúde Pública, a sala de situação permanente "
              "e o centro de operações de emergência temporário.")
    t_ciclo = ("PORTARIA Nº 9/2026 — Institui o Centro de Operações de Emergência para o "
               "enfrentamento do El Niño 2026/2027.")
    t_plano_ses = ("Secretaria de Estado da Saúde do Maranhão. PLANO DE CONTINGÊNCIA EM RESPOSTA ÀS "
                   "ARBOVIROSES, 2026. Sumário. Introdução.")
    t_portaria = ("PORTARIA Nº 10/2026 — Aprova o Plano Estadual de Contingência. O SECRETÁRIO DE "
                  "ESTADO DE SAÚDE, no uso das atribuições legais, resolve: Art. 1º Fica aprovado.")
    # Colegiado SEM autoridade do Executivo no texto: é aqui que `executivo_pendente` aparece.
    # Com a SES nomeada e "aprova", a régua do Legal aceita o documento e a exceção nem é
    # consultada — foi o que a primeira versão deste caso media, e media errado.
    t_colegiado = ("Resolução CIB nº 5 — a Comissão Intergestores Bipartite, reunida em sessão, "
                   "aprova o Plano de Contingência das Arboviroses 2026.")
    fonte = pathlib.Path(__file__).read_text(encoding="utf-8")

    def grava_em(nome):
        return ("grav" + "ar(\"" + nome) in fonte

    casos = {
        "ato de sala de situação é coordenação":
            lambda: o_que_institui(t_sala) == {"coordenacao"},
        "ato de plano é instrumento":
            lambda: o_que_institui(t_plano) == {"instrumento"},
        "ato que institui os dois conta nos dois":
            lambda: o_que_institui(t_dois) == {"coordenacao", "instrumento"},
        "texto sem nenhum dos dois não institui nada":
            lambda: o_que_institui("Portaria de nomeação de servidor") == set(),
        # A trava do degrau: ato de 2026 que NÃO nomeia o ciclo é permanente, não criado para ele.
        "ato de 2026 sem menção ao ciclo é PERMANENTE":
            lambda: degrau_coordenacao(t_dois, "30/03/2026")[0] == "PERMANENTE",
        "ato de 2026 que nomeia o ciclo é CRIADO_CICLO":
            lambda: degrau_coordenacao(t_ciclo, "15/07/2026")[0] == "CRIADO_CICLO",
        "ato que reativa e nomeia o ciclo é REATIVADO_CICLO":
            lambda: degrau_coordenacao("Reativa o COE para o El Niño", "10/08/2026")[0] == "REATIVADO_CICLO",
        "ato antigo sem menção ao ciclo é PERMANENTE":
            lambda: degrau_coordenacao(t_sala, "03/10/2024")[0] == "PERMANENTE",
        "categoria do juiz vira vocabulário da saúde":
            lambda: (status_instrumento("plano") == "NOVO"
                     and status_instrumento("plano_elaboracao") == "ELAB"
                     and status_instrumento("plano_antigo") == "VIG"
                     and status_instrumento("decreto") is None),
        "PDF sem texto não vira reprovação de mérito":
            lambda: texto_do_documento(b"%PDF-1.4 lixo", "x.pdf") == "",
        "HTML perde script e tag, e sobra o texto":
            lambda: ("ola" in texto_do_documento(b"<p>ola</p><script>x=1</script>", "a.html")
                     and "x=1" not in texto_do_documento(b"<p>ola</p><script>x=1</script>", "a.html")),
        # A coordenação não rebaixa: UF que já tem ato do ciclo não volta a permanente.
        "coordenação já verificada não é rebaixada":
            lambda: (aplicar({"uf": {"AC": {"coordenacao": {"status": "CRIADO_CICLO"}}}},
                             {"uf": "AC", "coordenacao": {"degrau": "PERMANENTE", "motivo": "x"}},
                             "t", "u") == []),
        # 02/10/2026: a coordenação passou a ter duas funções, e o que se escreve diz qual.
        "coordenação ausente é escrita, dizendo a função":
            lambda: (aplicar({"uf": {"AC": {}}},
                             {"uf": "AC", "coordenacao": {"degrau": "PERMANENTE", "motivo": "x"}},
                             "t", "u") == ["coordenação F1 PERMANENTE"]),
        # F2 é classificada por conta própria, e a atribuição escrita é o que separa 100 de 50.
        "F2: saúde nomeada no comitê intersetorial COM atribuição":
            lambda: degrau_f2("Institui o Comitê Intersetorial de Enfrentamento. "
                              "À Secretaria de Estado da Saúde compete coordenar o eixo "
                              "sanitário.")[0] == "NOMEADA_COM_ATRIBUICAO",
        "F2: saúde apenas listada na composição vale menos, e não zero":
            lambda: degrau_f2("Institui o Comitê Intersetorial, composto por: Casa Civil, "
                              "Secretaria de Estado da Saúde, Defesa Civil.")[0]
                    == "LISTADA_SEM_ATRIBUICAO",
        "F2: estrutura da própria saúde que integra a defesa civil cumpre a função":
            lambda: degrau_f2("Institui a Sala de Situação da SES, que será coordenada pela "
                              "secretaria e integrará a Defesa Civil estadual.")[0]
                    == "NOMEADA_COM_ATRIBUICAO",
        # O termo que faltava, com o ato real da Paraíba.
        "grupo condutor é estrutura de coordenação":
            lambda: o_que_institui("PORTARIA Nº 764/2026 – GS/SES/PB. Fica criado, no âmbito da "
                                   "Secretaria de Estado da Saúde, o Grupo Condutor El Niño/PB")
                    == {"coordenacao"},
        "F1 do ato da Paraíba: criado para o ciclo":
            lambda: degrau_coordenacao("Fica criado, no âmbito da Secretaria de Estado da Saúde, "
                                       "o Grupo Condutor El Niño/PB", "03/09/2026")[0] == "CRIADO_CICLO",
        "F2 do ato da Paraíba: a saúde integra a defesa civil, com atribuição":
            lambda: degrau_f2("PORTARIA Nº 764/2026 – GS/SES/PB. RESOLVE: Grupo Condutor El "
                              "Niño/PB, no âmbito da Secretaria de Estado da Saúde. Art. 2º "
                              "Compete à Secretaria de Estado da Saúde coordenar. Art. 5º "
                              "Composto por: Defesa Civil Estadual; AESA.")[0]
                    == "NOMEADA_COM_ATRIBUICAO",
        # MEDIDO em 02/10/2026 nos dois atos: menção no considerando e menção como convidado não
        # são integração formal, e davam F2 = 100 a estruturas compostas só por áreas internas.
        "F2: defesa civil citada no considerando não integra o ato (MT 0666/2024)":
            lambda: degrau_f2("CONSIDERANDO que o S2iD da Secretaria Nacional de Proteção e "
                              "Defesa Civil registrou 148 eventos; RESOLVE: Art. 1º Instituir a "
                              "Sala de Situação, composta pelos seguintes setores: I - Vigilância "
                              "em Saúde; II - Coordenadoria de Vigilância Epidemiológica. Compete "
                              "coordenar.")[0] == "LAC",
        "F2: defesa civil como convidada vale o degrau do meio (MS 1041/2026)":
            lambda: degrau_f2("RESOLVE: Art. 1º Instituir o Grupo Condutor. Art. 6º Será composto "
                              "por: I - Superintendência de Vigilância em Saúde. §2º Poderão "
                              "participar, na condição de convidados, representantes da Defesa "
                              "Civil. Compete coordenar.")[0] == "LISTADA_SEM_ATRIBUICAO",
        "F2: defesa civil na composição, com atribuição, é o degrau cheio (PB 764/2026)":
            lambda: degrau_f2("PORTARIA Nº 764/2026 – GS/SES/PB. Secretaria de Estado da Saúde. "
                              "RESOLVE: Art. 1º Fica criado o Grupo Condutor. Art. 2º Compete-lhe "
                              "coordenar. Art. 5º Será "
                              "composto por: XIX - Defesa Civil Estadual; XX - AESA.")[0]
                    == "NOMEADA_COM_ATRIBUICAO",
        # ── A5-02, A5-03, A5-37 e o domínio (08/10/2026): os NEGATIVOS que provam as travas.
        # Sem eles, as correções passariam a existir sem nada que mostrasse o que elas impedem.
        "A5-02: a sigla SES não casa o fim de 'meses', 'fases', 'doses', 'interesses'":
            lambda: not any(cita_saude(x) for x in
                            ("nos últimos meses", "fases do plano", "doses", "interesses")),
        "A5-02: SES e SESAU em caixa alta são a saúde; 'ses' minúsculo solto não é":
            lambda: bool(cita_saude("Resolução SES-PB")) and bool(cita_saude("a SESAU informa"))
                    and not cita_saude("os reveses do ano"),
        "A5-02: comitê que NÃO nomeia a saúde não cumpre F2, nem com 'a cada dois meses'":
            lambda: degrau_f2("DECRETA: Art. 1º Fica instituído o Comitê Estadual de Enfrentamento. "
                              "Art. 2º Compete ao Comitê coordenar. Art. 3º O Comitê reunir-se-á a "
                              "cada dois meses. Composto por: Casa Civil; Defesa Civil.")[0] == "LAC",
        "A5-02: 'compete ao comitê' não é atribuição da saúde — degrau do meio, não o cheio":
            lambda: degrau_f2("DECRETA: Fica instituído o Comitê Estadual. Compete ao Comitê "
                              "coordenar as ações. Composição: Casa Civil; Secretaria de Estado "
                              "da Saúde; Defesa Civil.")[0] == "LISTADA_SEM_ATRIBUICAO",
        "A5-03: sala de situação da Defesa Civil NÃO é estrutura da saúde (F1 não entra)":
            lambda: o_que_institui("DECRETO Nº 49.283 — Institui a Sala de Situação Integrada da "
                                   "Coordenadoria Estadual de Defesa Civil e o Comitê Gestor da "
                                   "Convivência com a Seca.") == set(),
        "A5-03: comitê de governo sobre clima NÃO é F1":
            lambda: o_que_institui("Despacho do Governador — Comitê Gestor da Política Estadual de "
                                   "Mudanças Climáticas. Designa representantes.") == set(),
        "A5-03: a mesma estrutura, no âmbito da SES, É F1":
            lambda: o_que_institui("PORTARIA — Fica instituída, no âmbito da Secretaria de Estado "
                                   "da Saúde, a Sala de Situação.") == {"coordenacao"},
        "A5-37: a data é a do cabeçalho do ato, não a da lei citada no preâmbulo":
            lambda: data_do_cabecalho("Considerando a Lei nº 7.498, de 03 de junho de 1987; "
                                      "RESOLUÇÃO SESA nº 680, de 15 de dezembro de 2008. "
                                      "O Secretário resolve:") == "15/12/2008",
        "domínio: o subdomínio do instrumento vigente do ES é estadual (cinco partes)":
            lambda: dominio_de_saude_estadual("https://mosquito.saude.es.gov.br/p.pdf",
                                              "Secretaria de Estado da Saúde") is True,
        "domínio: Goiânia é município, e não entra na camada estadual":
            lambda: dominio_de_saude_estadual("https://saude.goiania.go.gov.br/p.pdf",
                                              "Secretaria de Saúde") is False,
        "domínio: existe o município de Saúde (BA), e ele não pode derrubar saude.XX.gov.br":
            lambda: dominio_de_saude_estadual("https://saude.ma.gov.br/p.pdf",
                                              "Secretaria de Estado da Saúde") is True,
        "o preâmbulo fica de fora da leitura do dispositivo":
            lambda: "Instituir" in corpo_do_ato("CONSIDERANDO x; RESOLVE: Art. 1º Instituir")
                    and "CONSIDERANDO" not in corpo_do_ato("CONSIDERANDO x; RESOLVE: Art. 1º Instituir"),
        "ato sem dispositivo identificado é lido inteiro":
            lambda: corpo_do_ato("texto sem verbo de dispositivo") == "texto sem verbo de dispositivo",
        "F2: comitê que não nomeia a saúde não cumpre a função":
            lambda: degrau_f2("Institui o Comitê Intersetorial, composto por Casa Civil e "
                              "Defesa Civil, a quem compete coordenar.")[0] == "LAC",
        "F2 nunca conclui ausência de estrutura, só ausência de prova":
            lambda: "o ato não liga" in degrau_f2("texto qualquer")[1],
        "F2 guarda o trecho que fundamenta a classificação":
            lambda: "art. 3" in (atribuicao_citada(
                "Art. 3º Compete à Secretaria de Estado da Saúde coordenar o eixo sanitário.")
                or "").lower(),
        # Condição (3) da decisão da editoria: o registro CARREGA a observação, e ela sai quando o
        # ato de aprovação aparecer. Sem isto, a exceção ficaria invisível no banco.
        # O título do registro sai do DOCUMENTO, não do resultado de busca: título de documento é
        # afirmação sobre o documento, e o metabuscador devolve host e metadado.
        # O filtro de risco do ciclo, e o caso real que o criou.
        # O caso REAL que criou esta etapa, com o título como ele saiu do documento.
        "plano de sarampo não é risco deste ciclo":
            lambda: not trata_de_risco_do_ciclo(
                "Sarampo Plano de Contingência para Resposta às Emergências em Saúde Pública "
                "Sarampo Minas Gerais 2019")[0],
        "arcabouço genérico de emergências em saúde pública não conta sozinho":
            lambda: not trata_de_risco_do_ciclo(
                "Plano Estadual de Preparação e Resposta a Emergências em Saúde Pública")[0],
        "palavra solta no corpo do documento não entra: o teste é no título":
            lambda: not trata_de_risco_do_ciclo(
                "Plano de Contingência do Sarampo")[0],
        "plano de arboviroses é risco deste ciclo":
            lambda: trata_de_risco_do_ciclo("Plano de Contingência das Arboviroses: dengue e chikungunya")[0],
        "plano que nomeia o El Niño cobre o ciclo":
            lambda: trata_de_risco_do_ciclo("Plano de Enfrentamento ao El Niño do Estado")[0],
        "calor, fumaça e estiagem contam":
            lambda: all(trata_de_risco_do_ciclo(t)[0] for t in
                        ("protocolo de onda de calor", "fumaça de queimadas", "qualidade da água em estiagem")),
        "o que casou fica registrado, para a recusa ser auditável":
            lambda: "dengue" in trata_de_risco_do_ciclo("Plano de dengue")[1],
        "o título vem do documento quando ele nomeia o plano":
            lambda: titulo_do_documento(t_plano_ses, "GOVERNO DE MG - saude.mg.gov.br",
                                        "https://saude.mg.gov.br/p.pdf").startswith("PLANO DE CONTINGÊNCIA"),
        "sem nome de plano no texto, o host sai do título da pista":
            lambda: titulo_do_documento("texto qualquer", "Alguma coisa - saude.mg.gov.br",
                                        "https://saude.mg.gov.br/p.pdf") == "Alguma coisa",
        "registro feito pela exceção carrega a observação":
            lambda: (aplicar({"uf": {"AC": {}}},
                             {"uf": "AC", "status_instrumento": "NOVO",
                              "excecao_autoridade": "sem ato de aprovação localizado"}, "t", "u")
                     and True),
        "instrumento entra como item novo, sem apagar a lista":
            lambda: (len(aplicar({"uf": {"AC": {"instrumentos": [{"status": "VIG"}]}}},
                                 {"uf": "AC", "status_instrumento": "NOVO"}, "t", "u")) == 1),
        # TRAVA ESTRUTURAL: este juiz não escreve no índice do Legal nem marca não localizado.
        "o fonte grava só na camada estadual de saúde e na fila":
            lambda: not any(grava_em(n) for n in ("indice", "municipios", "estados", "pontos_mapa")),
        # A trava certa é de COMPORTAMENTO, não de texto: este juiz só vê documentos que existem,
        # e por isso nunca pode concluir ausência. Marcar ausência exige bateria completa por UF, e
        # essa decisão é de outro passo. (A primeira versão desta trava procurava a palavra no
        # fonte e reprovava por encontrá-la na lista de ordenação — texto não é comportamento.)
        # A exceção de autoridade da camada de saúde (editoria, 01/10/2026, 16h UTC) e as suas
        # três condições. Cada caso é uma condição, e os negativos são o que a exceção NÃO cobre.
        "plano em domínio de SES, com órgão, título e ano, passa pela exceção":
            lambda: autoridade_de_saude(t_plano_ses, "https://saude.ma.gov.br/plano.pdf")[0],
        "a exceção se declara no trecho, para o registro poder carregá-la":
            lambda: autoridade_de_saude(t_plano_ses, "https://saude.ma.gov.br/p.pdf")[2].startswith("exceção de autoridade"),
        "ato com fórmula do Executivo passa pela régua normal, sem exceção":
            lambda: (autoridade_de_saude(t_portaria, "https://saude.mt.gov.br/p.pdf")[0]
                     and not autoridade_de_saude(t_portaria, "https://saude.mt.gov.br/p.pdf")[2].startswith("exceção")),
        "domínio MUNICIPAL não entra na exceção: a camada é estadual":
            lambda: not autoridade_de_saude(t_plano_ses, "https://saude.goiania.go.gov.br/p.pdf")[0],
        "domínio não oficial não entra na exceção":
            lambda: not autoridade_de_saude(t_plano_ses, "https://g1.globo.com/p.pdf")[0],
        "sem identificar o órgão não entra na exceção":
            lambda: not autoridade_de_saude("Plano de Contingência das Arboviroses 2026", "https://saude.ma.gov.br/p.pdf")[0],
        "sem ano nem ciclo não entra na exceção":
            lambda: not autoridade_de_saude("Secretaria de Estado da Saúde. Plano de Contingência das Arboviroses.", "https://saude.ma.gov.br/p.pdf")[0],
        "aprovação por colegiado NÃO entra na exceção: ali existe ato, de outro órgão":
            lambda: autoridade_de_saude(t_colegiado, "https://saude.ma.gov.br/p.pdf")[1] == "executivo_pendente",
        "a régua do MARÉ Legal fica intocada":
            lambda: juiz.etapa3_autoridade(t_plano_ses)[1] == "autoridade_nao_confirmada",
        "o degrau de coordenação nunca conclui ausência":
            lambda: all(degrau_coordenacao(t, d)[0] != "LAC" for t, d in (
                (t_sala, "03/10/2024"), (t_dois, "30/03/2026"), (t_ciclo, "15/07/2026"),
                ("", ""), ("texto qualquer", "01/01/2020"))),
    }
    return rodar_autoteste(casos)


def main() -> int:
    args = sys.argv[1:]
    if "--autoteste" in args:
        return autoteste()
    alvo = args[args.index("--uf") + 1].upper() if "--uf" in args else None
    fila = ler(FILA, {}) or {}
    pistas = fila.get("pistas") or []
    # `--rejulgar` revisita pistas que já têm veredito. Existe porque a régua pode mudar por
    # decisão da editoria — foi o que aconteceu em 01/10/2026, 16h UTC, com a exceção de autoridade
    # da camada de saúde: sem rejulgar, as 27 recusas ficariam de pé por serem antigas, e não por
    # serem certas. Pista já PROMOVIDA não volta: o registro dela existe, e rejulgar criaria um
    # segundo item igual em `instrumentos[]`.
    rejulgar = "--rejulgar" in args
    candidatas = [p for p in pistas
                  if p.get("oficial") and p.get("url")
                  and (rejulgar or not p.get("juiz"))
                  and not (p.get("juiz") or {}).get("promove")
                  and (alvo is None or p.get("uf") == alvo)]
    if "--limite" in args:
        candidatas = candidatas[:int(args[args.index("--limite") + 1])]
    print(f"{len(candidatas)} pista(s) oficial(is) a julgar"
          + (f" em {alvo}" if alvo else "") + f", de {len(pistas)} na fila")
    su = ler(ALVO, {}) or {}
    promovidas, recusadas, mudancas = 0, {}, []
    for p in candidatas:
        v = julgar_pista(p)
        p["juiz"] = {k: v.get(k) for k in ("promove", "motivo", "codebook", "categoria", "data",
                                           "institui", "status_instrumento", "coordenacao")}
        if v.get("promove"):
            promovidas += 1
            m = aplicar(su, v, v.get("titulo_do_documento") or p.get("titulo") or "", p.get("url"))
            if m:
                mudancas.append(f"{v['uf']}: {', '.join(m)}")
                p["documento_oficial_confirmado"] = p.get("url")
                p["promovivel"] = True
                p["status"] = "promovido_pelo_juiz"
            print(f"  ✓ {v['uf']} · {v.get('categoria')} · institui {v['institui']} · {m or 'sem mudança'}")
        else:
            recusadas[v.get("motivo")] = recusadas.get(v.get("motivo"), 0) + 1
            print(f"  ✗ {p.get('uf')} · {v.get('motivo')}")
    print(f"\n{promovidas} promovida(s) · {len(candidatas) - promovidas} recusada(s)")
    for motivo, n in sorted(recusadas.items(), key=lambda x: -x[1]):
        print(f"   {n}× {motivo}")
    if mudancas:
        print("mudanças: " + " · ".join(mudancas))
    if "--aplicar" in args:
        gravar(ALVO, su)
        gravar(FILA, fila)
        print(f"data/{ALVO} e data/{FILA} gravados")
    else:
        print("(relatório: nada foi gravado)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
