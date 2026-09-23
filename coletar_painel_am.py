#!/usr/bin/env python3
"""Coletor do painel Power BI da Defesa Civil do Amazonas (§165, 23/09/2026).

MOTIVAÇÃO (caso real). Em 22/09/2026 a Ouvidoria da Defesa Civil do AM respondeu a um
pedido de LAI sem enviar a lista pedida: indicou um painel Power BI do próprio órgão. O
painel traz os 62 municípios do estado com calha de rio, ano do plano e um ícone de link
para o documento de cada município — exatamente os itens (1) e (2) do pedido. É público e
provavelmente antigo, e nenhuma rodada do robô o encontrou: a tabela é montada em
JavaScript depois do carregamento, então a busca textual recebe só o esqueleto da página.
A falha foi de CAMADA, não de cobertura (§164, sondar_paineis.py e a nota de diagnóstico).

O QUE ESTE SCRIPT FAZ
  1. Manda scripts/renderizar_painel_am.js abrir o sub-painel num navegador real e devolver
     a tabela em bruto (o Node só renderiza e extrai; não decide nada).
  2. Casa cada nome de município com o código IBGE de data/municipios_ibge_referencia.json.
  3. Para cada linha com link: baixa o documento, preserva a evidência e tenta ler do
     PRÓPRIO documento o número e a data do ato.
  4. Escreve o resultado em data/pistas_painel_am.json (fila própria) e registra tudo no
     log v2 e no livro de fontes consultadas.

DECLARADO ≠ DOCUMENTADO (a distinção que dá sentido ao coletor). A tabela do painel é
DECLARAÇÃO DO ESTADO: traz o ano, não traz número nem data do ato. Isso é camada
`declarado`, com o desconto já previsto na metodologia. Só vira `documentado` o município
cujo link ABRIU o documento e cujo ato teve número e data lidos do documento. Ano 2026 não
é prova de antecipação: a régua do ciclo separa antes e depois de 29/06/2026, e sem a data
do ato o município fica em `declarado` — nunca promovido "por ser de 2026".

===========================================================================
TRAVA ABSOLUTA (idêntica à de descobrir_planos.py e sondar_paineis.py):
  1. ESTRUTURAL: nunca escreve em estados.json, saude_uf.json, municipios.json,
     indice.json ou monitor_saude.json (garantido por autoteste que lê o próprio fonte).
  2. DE CAMPO: todo item nasce com "documento_oficial_confirmado": null e
     "promovivel": false.
  3. DE PROCESSO: sai em fila própria, nunca no banco. Promoção é humana (regra R7).
Link que não abre, PDF ilegível ou painel fora do ar = LACUNA DECLARADA (registrar_lacuna),
jamais valor estimado.
===========================================================================

Uso: python3 coletar_painel_am.py [--url URL] [--de-arquivo render.json] [--limite N]
     python3 coletar_painel_am.py --semear-da-sonda   (usa a leitura humana de 22/09, sem rede)
     python3 coletar_painel_am.py --autoteste     (offline, sem rede e sem navegador)
"""
import json
import re
import subprocess
import sys
import time
import unicodedata
from datetime import date

from coletores_base import (RAIZ, buscar, buscar_com_procedencia, hoje, ler,
                            gravar, log_busca, preservar_evidencia,
                            referencia_ibge, registrar_lacuna, marcar_fonte_consultada,
                            rodar_autoteste, UA)

FILA = "pistas_painel_am.json"
RENDERIZADOR = RAIZ / "scripts" / "renderizar_painel_am.js"

# Sub-painel "Planos de Contingência Municipais" (registrado em data/pistas_paineis.json
# pela sonda de camada; repetido aqui para o coletor rodar sozinho).
URL_SUB_PAINEL = ("https://app.powerbi.com/view?r=eyJrIjoiZjg5MzkyM2QtMGJkZi00MGRiLWJhYmYt"
                  "MjcyZTBkMmNiZDc2IiwidCI6Ijg1NDczOTk4LTFmODEtNDAxMS1iYzk3LTg3YWUwNGU2MTIwNCJ9")

# Régua do ciclo (§ metodologia): o que separa antecipação de resposta é a data do ATO,
# não o ano impresso no painel.
CICLO_INICIO = date(2026, 6, 29)

MESES = {"janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3, "abril": 4, "maio": 5,
         "junho": 6, "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10,
         "novembro": 11, "dezembro": 12}

# "Decreto nº 1.234, de 5 de março de 2026" / "Portaria 12/2026 de 05/03/2026" / "Lei ..."
RE_ATO = re.compile(
    r"(decreto|portaria|resolu[çc][ãa]o|lei|instru[çc][ãa]o normativa)"
    r"[^\n]{0,40}?n?[ºo°\.]?\s*([\d][\d\.\-/]{0,15})"
    r"[^\n]{0,60}?de\s+(\d{1,2})\s*(?:de\s+)?([a-zç]+|\d{1,2})\s*(?:de\s+)?(\d{4})",
    re.IGNORECASE)


def _norm(s: str) -> str:
    """Compara nome de município ignorando acento, caixa, pontuação e espaço duplo."""
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


# Rótulos que o Power BI COLA no texto acessível da célula quando a coluna tem formatação
# condicional. Achado na rodada renderizada de 23/09/2026: o painel devolveu "Atalaia do
# Norte Formatação Condicional Adicional" — nome de município com uma etiqueta de interface
# no fim. As 20 linhas lidas falharam TODAS o casamento com o IBGE por causa disso, e sem
# esta limpeza virariam 20 lacunas falsas: o dado estava lá, quem não leu foi o coletor.
#
# A lista é FECHADA de propósito. Uma heurística de corte ("tire as três últimas palavras")
# mutilaria nome legítimo — São Paulo de Olivença tem quatro, Santo Antônio do Içá tem
# quatro. Rótulo novo aparecendo é preferível como lacuna declarada a nome recortado errado.
ROTULOS_DE_INTERFACE = (
    "Formatação Condicional Adicional",
    "Additional Conditional Formatting",
)


# §180 (23/09/2026, rodada real feita de dentro do Brasil): o ato que estas constantes filtram.
# `ler_ato` pegava a PRIMEIRA ocorrência de "<tipo> nº <n> de <data>" no documento — e todo PLANCON
# municipal tem, na seção de demografia, a frase "Ato de Criação: Lei Estadual Nº 96 DE 19 de
# dezembro de 1955". Resultado medido nos 51 documentos baixados: 16 itens viraram `documentado`
# com o ato de CRIAÇÃO DO MUNICÍPIO no lugar do ato do plano — 13 deles anteriores a 2015 (1874,
# 1881, 1897, 1938, 1955 duas vezes, 1956, 1974, 1975, 1982, 2008, 2012, 2013). Nenhum foi promovido,
# porque `promovivel` nasce false e o §156 exige ato do ciclo; mas o campo publicado na fila estaria
# errado, e quem revisa confiaria nele.
CONTEXTO_DE_CRIACAO = (
    "ato de criacao", "criacao do municipio", "criado pela lei", "criado pelo decreto",
    "elevado a categoria", "instalacao do municipio", "emancipacao", "desmembramento",
    "data de criacao", "lei de criacao",
)
# O ato do plano tem de se APRESENTAR como tal. Vizinhança com a palavra "plano" não basta —
# medido nos 51 documentos do AM em 23/09/2026, a primeira versão desta regra ainda aceitou três
# atos errados, cada um de um tipo diferente de armadilha:
#   · Coari e Rio Preto da Eva: "Coordenador Municipal de Proteção e Defesa Civil / Portaria n° 007
#     de 06 de Janeiro de 2026" — o ato que NOMEIA o coordenador, colado na assinatura dele;
#   · Manicoré: "Lei nº 14.750, de 12 de dezembro de 2023 – Atualiza a PNPDEC" — citação numa lista
#     de fundamentação legal, com "plano de contingência" na mesma frase.
# Então a exigência passa a ser o VERBO instituidor na mesma oração (ou na ementa seguinte, onde o
# decreto brasileiro costuma trazê-lo), mais a palavra do plano, menos os marcadores de citação.
VERBOS_INSTITUIDORES = ("institui", "fica instituido", "aprova", "fica aprovado", "homologa", "adota")
PALAVRAS_DO_PLANO = ("plano de contingencia", "plancon", "plano municipal de contingencia")
MARCADORES_DE_CITACAO = (
    "atualiza a", "politica nacional", "pnpdec", "sinpdec", "conpdec", "estatuto da cidade",
    "transferencias de recursos", "dispoe sobre o sistema", "lei federal", "constituicao federal",
)
# Piso de plausibilidade: plano de contingência do ciclo 2026-27 não é instituído por ato anterior a
# 2015 (a Política Nacional de Proteção e Defesa Civil é de 2012, e os planos que a cumprem vieram
# depois). Ato mais antigo que isto, mesmo fora de contexto de criação, fica como NÃO LIDO — o item
# cai para `declarado`, que é a resposta honesta, em vez de publicar uma data que não é do plano.
ANO_MINIMO_DO_ATO = 2015


def celula_sem_rotulo(valor):
    """Célula do Power BI sem o rótulo de interface. Quando a célula é SÓ o rótulo, devolve ""
    — ausência, não texto. Medido na rodada de 23/09: 53 das 62 linhas traziam apenas
    "Formatação Condicional Adicional" na coluna Calha (a calha aparece uma vez por grupo, e as
    demais linhas herdam visualmente). Publicar esse rótulo seria publicar interface como dado."""
    if not isinstance(valor, str):
        return valor
    s = valor.strip()
    if any(_norm(s) == _norm(r) for r in ROTULOS_DE_INTERFACE):
        return ""
    return limpar_rotulo_powerbi(s)


def limpar_rotulo_powerbi(texto: str) -> str:
    """Remove do FIM do texto os rótulos de interface declarados acima. Só no fim, só os
    declarados, e comparando sem acento nem caixa — o miolo do nome nunca é tocado."""
    s = (texto or "").strip()
    mudou = True
    while mudou:
        mudou = False
        for rotulo in ROTULOS_DE_INTERFACE:
            if _norm(s).endswith(_norm(rotulo)) and _norm(s) != _norm(rotulo):
                s = " ".join(s.split()[:-len(rotulo.split())]).strip()
                mudou = True
    return s


def _ato_do_casamento(m):
    """{tipo, numero, data} de um casamento do RE_ATO, ou None se a data não fecha."""
    tipo, numero, dia, mes_txt, ano = m.groups()
    mes = MESES.get(_norm(mes_txt)) if not mes_txt.isdigit() else int(mes_txt)
    if not mes:
        return None
    try:
        d = date(int(ano), int(mes), int(dia))
    except ValueError:
        return None
    return {"tipo": tipo.lower(), "numero": numero.strip(" ."), "data": d.isoformat()}


def ler_ato(texto: str):
    """Extrai {tipo, numero, data} do ato que INSTITUI o plano, lido no próprio documento.
    None quando não há ato legível — nunca chuta, e "não localizei" é resposta válida (§180).

    Três filtros, nesta ordem, sobre TODAS as ocorrências (a versão anterior lia só a primeira):
      1. descarta quem está em contexto de CRIAÇÃO DO MUNICÍPIO (ver CONTEXTO_DE_CRIACAO);
      2. descarta ato anterior a ANO_MINIMO_DO_ATO, que não pode ser o do plano deste ciclo;
      3. exige que o ato se apresente COMO o ato do plano: verbo instituidor (institui/aprova/
         homologa/adota) e palavra do plano na mesma oração ou na ementa seguinte, e nenhum
         marcador de citação legal. Sem isso o item fica `declarado` — que é a resposta honesta
         quando o documento não diz qual ato o instituiu."""
    t = texto or ""
    candidatos = []
    for m in RE_ATO.finditer(t):
        # só a oração imediatamente anterior conta: no modelo estadual, a frase do ato de criação é
        # seguida de "...a instalação do município ocorreu em ...", e uma janela cega de 160
        # caracteres levava essa marca para dentro do contexto do ato SEGUINTE, que é o do plano.
        esquerda = _norm(re.split(r"[.;\n]", t[max(0, m.start() - 160):m.start()])[-1])
        if any(marca in esquerda for marca in CONTEXTO_DE_CRIACAO):
            continue
        ato = _ato_do_casamento(m)
        if not ato or int(ato["data"][:4]) < ANO_MINIMO_DO_ATO:
            continue
        # janela ANCORADA no casamento: o que resta da oração antes dele, o próprio ato e as duas
        # orações seguintes — é ali que o decreto brasileiro põe a ementa ("… DE 2026. Institui o
        # Plano …"). Contar pedaços a partir do início da fatia cortava antes da ementa quando havia
        # ponto no meio de um número ("População: 25.172").
        antes = re.split(r"[.;\n]", t[max(0, m.start() - 160):m.start()])[-1]
        depois = re.split(r"[.;\n]", t[m.end():m.end() + 300])[:2]
        janela = _norm(" ".join([antes, m.group(0)] + depois))
        if any(marca in janela for marca in MARCADORES_DE_CITACAO):
            continue
        if not any(v in janela for v in VERBOS_INSTITUIDORES):
            continue
        if not any(pl in janela for pl in PALAVRAS_DO_PLANO):
            continue
        candidatos.append((m.start(), ato))
    if not candidatos:
        return None
    return candidatos[0][1]


def eh_pdf(conteudo: bytes, url: str) -> bool:
    """O CONTEÚDO manda, não a extensão da URL: portal estadual que responde HTML numa URL
    terminada em .pdf (página de erro, visualizador, aviso de defeso) é comum, e tratá-lo
    como PDF só produziria uma lacuna falsa. A extensão só decide quando o corpo não é
    claramente HTML."""
    if conteudo[:5] == b"%PDF-":
        return True
    if re.match(rb"\s*(<!doctype html|<html|<\?xml)", conteudo[:64], re.IGNORECASE):
        return False
    return url.lower().split("?")[0].endswith(".pdf")


def texto_do_documento(conteudo: bytes, url: str) -> str:
    """Texto legível de PDF (pypdf) ou HTML. Devolve '' se ilegível — quem chama
    transforma isso em lacuna declarada, nunca em ausência de ato."""
    if eh_pdf(conteudo, url):
        try:
            import io
            import logging

            from pypdf import PdfReader
            # PDF corrompido é caminho ESPERADO aqui (vira lacuna declarada); o aviso do
            # pypdf em stderr só polui a saída do portão.
            logging.getLogger("pypdf").setLevel(logging.ERROR)
            r = PdfReader(io.BytesIO(conteudo), strict=False)
            return "\n".join((p.extract_text() or "") for p in r.pages[:20])
        except Exception:  # noqa: BLE001 — PDF corrompido/protegido vira lacuna
            return ""
    try:
        html = conteudo.decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        return ""
    html = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
    return re.sub(r"\s+", " ", re.sub(r"(?s)<[^>]+>", " ", html))


def linha_para_registro(linha: dict) -> dict:
    """Normaliza uma linha bruta do renderizador para os campos do projeto. Célula ausente
    vira None — o painel não tem coluna de número/data de ato, e isso é o ponto."""
    # §180: limpa o rótulo de interface ANTES de qualquer casamento de coluna. Sem isso a célula
    # "Plano" chega com "Formatação Condicional Adicional" e o casamento por substring de "ano"
    # bate nela ("plano" contém "ano") antes de chegar em "ano do plano" — foi assim que as 62
    # linhas da rodada de 23/09 perderam o ano declarado pelo estado, que é o dado do painel.
    cel = {_norm(k): celula_sem_rotulo(v) for k, v in (linha.get("celulas") or {}).items()}

    def pega(*chaves):
        # passada estrita primeiro: nome de coluna igual, ou começando/terminando pela chave
        for c in chaves:
            for k, v in cel.items():
                if (k == c or k.startswith(c + " ") or k.endswith(" " + c)) and v not in (None, ""):
                    return v
        # depois tolerante, para cabeçalho que muda de redação sem mudar de sentido
        for c in chaves:
            for k, v in cel.items():
                if c in k and v not in (None, ""):
                    return v
        return None

    ano_bruto = pega("ano do plano", "ano")
    m_ano = re.search(r"(19|20)\d{2}", str(ano_bruto or ""))
    ano = int(m_ano.group(0)) if m_ano else None
    # Célula ausente continua None depois da limpeza: "" não é a mesma coisa que ausência.
    def limpo(v):
        return (v or None) if v else None

    return {"municipio_no_painel": limpo(pega("municipio", "município")),
            "calha": limpo(pega("calha")),
            "ano_do_plano": ano,
            "url_do_link": linha.get("url_do_link"),
            "como_obtido": linha.get("como_obtido"),
            "indice_no_painel": linha.get("indice")}


def casar_ibge(nome: str, por_nome: dict):
    """Nome do painel → código IBGE do AM. Sem casamento, devolve None: vira lacuna
    declarada, nunca palpite (um município errado contamina o índice de um terceiro)."""
    if not nome:
        return None
    alvo = _norm(limpar_rotulo_powerbi(nome))
    for (n, uf), cod in por_nome.items():
        if uf == "AM" and _norm(n) == alvo:
            return cod
    return None


def casar_por_eliminacao(nomes_do_painel: list, por_cod: dict, por_nome: dict) -> dict:
    """Resolve o resto por ELIMINAÇÃO, e só quando ela é conclusiva.

    Caso real que motivou isto (23/09/2026): o painel do AM escreve "Careiro Castanho", o
    nome popular; o IBGE registra "Careiro". Existe também "Careiro da Várzea", município
    distinto — e é exatamente por isso que um apelido não pode virar alias solto: errar aqui
    move a nota de um terceiro.

    A regra só dispara quando sobra UM nome sem par de cada lado: aí o par é dedução, não
    palpite. Sobrando dois ou mais, todos continuam lacuna declarada. Devolve
    {nome_do_painel: codigo_ibge} apenas para os casamentos deduzidos."""
    todos_am = {cod for (n, uf), cod in por_nome.items() if uf == "AM"}
    casados = {c for c in (casar_ibge(n, por_nome) for n in nomes_do_painel) if c}
    sobram_painel = [n for n in nomes_do_painel if not casar_ibge(n, por_nome)]
    sobram_ibge = sorted(todos_am - casados)
    if len(sobram_painel) == 1 and len(sobram_ibge) == 1:
        return {sobram_painel[0]: sobram_ibge[0]}
    return {}


class Efeitos:
    """Os quatro efeitos colaterais do coletor num só lugar: rede, evidência, log e livro
    de fontes. Existe para o autoteste poder rodar DE VERDADE offline e sem escrever em
    data/ — antes desta separação, `--autoteste` batia em app.powerbi.com e sujava
    log_buscas.json e fontes_consultadas.json a cada execução do portão."""

    def __init__(self, buscar_fn=buscar_com_procedencia, preservar_fn=preservar_evidencia,
                 log_fn=log_busca, lacuna_fn=registrar_lacuna,
                 marcar_fn=marcar_fonte_consultada, pausa_s=2.0):
        self.buscar = buscar_fn
        self.preservar = preservar_fn
        self.log = log_fn
        self.lacuna = lacuna_fn
        self.marcar = marcar_fn
        self.pausa_s = pausa_s


class EfeitosInertes(Efeitos):
    """Dublê do autoteste: nenhuma requisição, nenhuma escrita. Guarda o que teria feito,
    para os testes afirmarem sobre isso (ex.: 'link que não abre vira lacuna declarada')."""

    def __init__(self, respostas=None):
        self.respostas = respostas or {}      # url → bytes (documento simulado)
        self.lacunas, self.logs, self.marcados, self.preservados = [], [], [], []
        super().__init__(buscar_fn=self._buscar, preservar_fn=self._preservar,
                         log_fn=self._log, lacuna_fn=self._lacuna,
                         marcar_fn=self._marcar, pausa_s=0.0)

    def _buscar(self, url, timeout=45):
        """Devolve (bytes, procedencia), como buscar_com_procedencia. Uma resposta simulada
        pode ser `bytes` (procedência direta, o caso comum) ou a tupla inteira, para o teste
        que precisa simular documento vindo de captura de arquivo."""
        if url not in self.respostas:
            raise OSError(f"offline: sem resposta simulada para {url}")
        r = self.respostas[url]
        return r if isinstance(r, tuple) else (r, "fonte direta")

    def _preservar(self, conteudo, url, ext, origem):
        self.preservados.append(url)
        return "hash-simulado-" + str(len(conteudo))

    def _log(self, *a, **k):
        self.logs.append((a, k))

    def _lacuna(self, fonte, motivo, *a, **k):
        self.lacunas.append((fonte, motivo))

    def _marcar(self, ibges, fonte, nivel, resultado="consultada"):
        self.marcados.append((list(ibges), fonte, nivel))


def renderizar(url: str, de_arquivo: str | None) -> dict:
    """Chama o renderizador Node, ou relê um JSON já salvo (--de-arquivo), que é como se
    audita uma rodada antiga sem bater no sítio de novo."""
    if de_arquivo:
        with open(de_arquivo, encoding="utf-8") as f:
            return json.load(f)
    if not RENDERIZADOR.exists():
        return {"ok": False, "erro": f"renderizador ausente: {RENDERIZADOR}", "linhas": []}
    try:
        p = subprocess.run(["node", str(RENDERIZADOR), url],
                           capture_output=True, text=True, timeout=300,
                           env={**__import__("os").environ, "MONITOR_UA": UA})
        return json.loads(p.stdout.strip().splitlines()[-1])
    except Exception as e:  # noqa: BLE001 — navegador indisponível vira lacuna declarada
        return {"ok": False, "erro": f"{type(e).__name__}: {e}", "linhas": []}


def coletar(url: str, de_arquivo=None, limite=None, efeitos: "Efeitos | None" = None) -> dict:
    ef = efeitos or Efeitos()
    por_cod, por_nome = referencia_ibge()
    render = renderizar(url, de_arquivo)
    if not render.get("ok"):
        ef.lacuna("painel Power BI da Defesa Civil do AM",
                  render.get("erro") or "render sem linhas",
                  "painel AM", 1, strings=[url], uf="AM")
        return {"itens": [], "resumo": {"erro": render.get("erro")}}

    # A eliminação vale para as DUAS origens. Ela nasceu no caminho da semeadura, mas a
    # rodada renderizada de 23/09 mostrou o custo de deixá-la de fora aqui: 62 dos 62
    # municípios lidos, e ainda assim um nome sem par — "Careiro Castanho" no painel contra
    # "Careiro" no IBGE. A regra existia, era testada, e não era chamada no caminho que
    # virou o principal. Só dispara quando sobra UM de cada lado; com dois ou mais, todos
    # seguem lacuna declarada.
    brutas = list((render.get("linhas") or [])[:limite])
    registros = [linha_para_registro(b) for b in brutas]
    deduzidos = casar_por_eliminacao(
        [r["municipio_no_painel"] for r in registros], por_cod, por_nome)

    itens, ibges_lidos = [], []
    for r in registros:
        nome = r["municipio_no_painel"]
        cod = casar_ibge(nome, por_nome)
        if not cod and nome in deduzidos:
            cod = deduzidos[nome]
            r = {**r, "casamento_ibge": "por eliminação (único sem par dos dois lados)"}
        if not cod:
            ef.lacuna(f"município do painel: {nome!r}",
                      "nome não casou com a referência IBGE do AM",
                      "painel AM", 1, uf="AM")
        else:
            ibges_lidos.append(cod)
        item = {**r, "uf": "AM", "ibge": cod,
                "nome_ibge": (por_cod.get(cod) or {}).get("nome") if cod else None,
                # A declaração do estado, isolada e rotulada como tal.
                "camada": "declarado", "ato": None, "hash_evidencia": None,
                "documento_oficial_confirmado": None, "promovivel": False,
                "lido_em": render.get("lido_em") or hoje()}

        if r["url_do_link"]:
            try:
                # Reserva pelo Wayback (o mesmo caminho que o DF, PE e a listagem do DF já
                # usam desde 12/09). Rodada real de 23/09: os 62 documentos do painel do AM
                # responderam "Connection reset by peer" ao runner, um a um, enquanto o
                # próprio painel abria normalmente — logo quem recusa não é a Microsoft, é o
                # hospedeiro dos planos. Ler a captura pública de um arquivo não contorna
                # bloqueio nenhum: é outra fonte, e ela entra declarada como tal.
                conteudo, procedencia = ef.buscar(r["url_do_link"], timeout=45)
                item["procedencia_do_documento"] = procedencia
                ext = "pdf" if conteudo[:5] == b"%PDF-" else "html"
                item["hash_evidencia"] = ef.preservar(
                    conteudo, r["url_do_link"], ext,
                    f"painel Power BI Defesa Civil AM ({procedencia})")
                ato = ler_ato(texto_do_documento(conteudo, r["url_do_link"]))
                if ato:
                    # Único caminho para `documentado`: documento aberto E ato com número e data.
                    item["ato"] = ato
                    item["camada"] = "documentado"
                    item["no_ciclo"] = date.fromisoformat(ato["data"]) >= CICLO_INICIO
                    if procedencia != "fonte direta":
                        # O ato foi lido, mas numa cópia de arquivo. O registro diz isso em
                        # vez de fingir que o documento foi lido na fonte hoje.
                        item["observacao"] = (
                            f"ato lido em {procedencia} — a fonte não respondeu ao coletor; "
                            "documento é o arquivado, não necessariamente o vigente")
                else:
                    item["observacao"] = ("documento preservado, mas sem número e data de ato "
                                          f"legíveis ({procedencia}) — permanece declarado")
            except Exception as e:  # noqa: BLE001
                ef.lacuna(f"documento de {r['municipio_no_painel']}",
                          f"{type(e).__name__}: {e}", "painel AM", 1,
                          strings=[r["url_do_link"]], uf="AM")
                item["observacao"] = f"link não abriu ({type(e).__name__})"
            if ef.pausa_s:
                time.sleep(ef.pausa_s)     # §11: no máximo 1 requisição a cada 2s
        elif r["ano_do_plano"]:
            item["observacao"] = ("painel declara plano sem expor link do documento "
                                  f"({r['como_obtido']})")
        else:
            item["camada"] = "sem_plano_declarado"
        itens.append(item)

    if ibges_lidos:
        ef.marcar(ibges_lidos, "painel Power BI da Defesa Civil do AM",
                  "estadual", resultado="consultada")
    resumo = {
        "n_linhas_lidas": len(itens),
        "documentado": sum(1 for i in itens if i["camada"] == "documentado"),
        "declarado": sum(1 for i in itens if i["camada"] == "declarado"),
        "sem_plano_declarado": sum(1 for i in itens if i["camada"] == "sem_plano_declarado"),
        "sem_codigo_ibge": sum(1 for i in itens if not i["ibge"]),
        "no_ciclo": sum(1 for i in itens if i.get("no_ciclo")),
        # Quantos documentos vieram da fonte e quantos de captura de arquivo. Um lote em que
        # tudo veio de arquivo diz algo sobre a fonte, não sobre os municípios — e sem a
        # contagem esse fato ficaria espalhado item a item, invisível no resumo.
        "documentos_da_fonte": sum(1 for i in itens
                                   if i.get("procedencia_do_documento") == "fonte direta"),
        "documentos_de_captura": sum(1 for i in itens
                                     if (i.get("procedencia_do_documento") or "").startswith("captura")),
    }
    ef.log("painel AM", 1, [url], "pista", uf="AM", nivel="estadual",
           n_resultados=len(itens),
           resultados=(f"{resumo['documentado']} documentado(s), {resumo['declarado']} "
                       f"declarado(s), {resumo['sem_plano_declarado']} sem plano; "
                       f"{resumo['documentos_da_fonte']} documento(s) da fonte, "
                       f"{resumo['documentos_de_captura']} de captura"))
    return {"itens": itens, "resumo": resumo}


N_MUNICIPIOS_AM = 62


def leitura_confiavel(saida: dict) -> tuple:
    """A leitura merece ir para a fila? Devolve (ok, motivo).

    ACHADO DA RODADA 1 (23/09/2026). A primeira rodada renderizada de verdade leu 20 linhas
    em vez de 62 e NENHUMA casou com a referência IBGE — o renderizador havia pegado a grade
    errada da página. Mesmo assim o coletor escreveu as 20 na fila, que foi de 62 para 82
    itens. A trava de promoção segurou o banco, mas a fila de triagem humana foi poluída com
    lixo que parecia dado.

    Daí esta porta: uma leitura em que quase nada casa com o IBGE não é leitura parcial, é
    leitura ERRADA, e leitura errada vira lacuna declarada — nunca item de fila. Duas regras,
    ambas sobre o mesmo princípio de que ausência de leitura não é ausência de plano."""
    itens = saida.get("itens") or []
    if not itens:
        return False, "nenhuma linha lida"
    sem_ibge = sum(1 for i in itens if not i.get("ibge"))
    if sem_ibge > len(itens) // 2:
        return False, (f"{sem_ibge} de {len(itens)} linhas sem código IBGE — a grade lida "
                       "provavelmente não é a tabela dos municípios")
    if len(itens) < N_MUNICIPIOS_AM // 2:
        return False, (f"apenas {len(itens)} de {N_MUNICIPIOS_AM} municípios lidos — "
                       "leitura parcial demais para entrar na fila")
    return True, ""


def gravar_fila(saida: dict, url: str) -> dict:
    fila = ler(FILA, {"_governanca": (
        "Leitura do painel Power BI da Defesa Civil do AM (coletar_painel_am.py, §165). "
        "A tabela do painel é DECLARAÇÃO DO ESTADO: traz o ano, não o número e a data do "
        "ato. Camada 'declarado' entra com o desconto da metodologia; 'documentado' só "
        "para município cujo link abriu o documento e cujo ato teve número e data lidos do "
        "próprio documento. TRAVA ABSOLUTA: nada aqui entra no banco sem promoção humana "
        "(regra R7). Ano 2026 no painel NÃO prova antecipação."),
        "itens": []})
    fila["fonte"] = url
    fila["atualizado_em"] = hoje()
    fila["resumo"] = saida["resumo"]
    por_chave = {(i.get("ibge"), i.get("municipio_no_painel")): i for i in fila["itens"]}
    for i in saida["itens"]:
        por_chave[(i.get("ibge"), i.get("municipio_no_painel"))] = i
    fila["itens"] = sorted(por_chave.values(),
                           key=lambda x: (x.get("indice_no_painel") or 1e9,
                                          x.get("municipio_no_painel") or ""))
    gravar(FILA, fila)
    return fila


# ── autoteste (offline: sem rede, sem navegador) ─────────────────────────────

def semear_da_sonda(efeitos: "Efeitos | None" = None) -> dict:
    """Converte a LEITURA HUMANA do painel (22/09/2026), já registrada em
    data/pistas_paineis.json pela sonda de camada, no formato desta fila — sem rede e sem
    navegador.

    Existe porque a leitura de 22/09 é o dado que temos hoje, e ele não deve ficar preso num
    campo de observação enquanto a rodada renderizada não acontece. O que ela traz: os 62
    municípios com calha e ano. O que ela NÃO traz: a URL do documento de cada município, que
    o leitor humano não capturou. Logo TODOS os itens semeados ficam em `declarado` ou
    `sem_plano_declarado` — nenhum vira `documentado`, porque nenhum documento foi aberto.
    É a mesma regra do resto do coletor, aplicada a uma origem diferente."""
    ef = efeitos or Efeitos()
    sonda = ler("pistas_paineis.json", {"itens": []})
    caso = next((i for i in sonda.get("itens", [])
                 if i.get("uf") == "AM" and (i.get("sub_painel_municipios") or {}).get("tabela")), None)
    if not caso:
        ef.lacuna("leitura do painel do AM em data/pistas_paineis.json",
                  "caso do AM sem sub_painel_municipios.tabela — nada a semear",
                  "painel AM", 1, uf="AM")
        return {"itens": [], "resumo": {"erro": "tabela da leitura humana ausente"}}

    sub = caso["sub_painel_municipios"]
    por_cod, por_nome = referencia_ibge()
    nomes = [l.get("municipio") for l in sub["tabela"]]
    deduzidos = casar_por_eliminacao(nomes, por_cod, por_nome)
    itens, ibges = [], []
    for linha in sub["tabela"]:
        nome = linha.get("municipio")
        cod, como = casar_ibge(nome, por_nome), "nome idêntico"
        if not cod and nome in deduzidos:
            cod, como = deduzidos[nome], "por eliminação (único sem par dos dois lados)"
        if not cod:
            ef.lacuna(f"município do painel: {nome!r}",
                      "nome não casou com a referência IBGE do AM", "painel AM", 1, uf="AM")
            como = None
        else:
            ibges.append(cod)
        tem_plano = bool(linha.get("plano_declarado_pelo_estado"))
        itens.append({
            "municipio_no_painel": nome, "calha": linha.get("calha"),
            "ano_do_plano": linha.get("ano_do_plano"),
            "url_do_link": None,
            "como_obtido": "leitura humana do painel em 22/09/2026 — links por município não capturados",
            "indice_no_painel": linha.get("indice"),
            "uf": "AM", "ibge": cod, "casamento_ibge": como,
            "nome_ibge": (por_cod.get(cod) or {}).get("nome") if cod else None,
            "camada": "declarado" if tem_plano else "sem_plano_declarado",
            "ato": None, "hash_evidencia": None,
            "documento_oficial_confirmado": None, "promovivel": False,
            "origem": "leitura_humana_22-09-2026",
            "lido_em": sub.get("lido_em") or "2026-09-22",
            "observacao": ("o painel declara o ano; número e data do ato exigem abrir o link "
                           "de cada município numa rodada renderizada")
            if tem_plano else "painel não declara plano para este município",
        })
    if ibges:
        ef.marcar(ibges, "painel Power BI da Defesa Civil do AM (leitura humana 22/09/2026)",
                  "estadual", resultado="consultada")
    resumo = {"n_linhas_lidas": len(itens),
              "documentado": 0,
              "declarado": sum(1 for i in itens if i["camada"] == "declarado"),
              "sem_plano_declarado": sum(1 for i in itens if i["camada"] == "sem_plano_declarado"),
              "sem_codigo_ibge": sum(1 for i in itens if not i["ibge"]),
              "no_ciclo": 0,
              "origem": "leitura_humana_22-09-2026"}
    ef.log("painel AM", 1, [sub.get("url", "")], "pista", uf="AM", nivel="estadual",
           n_resultados=len(itens),
           resultados=(f"semeadura da leitura humana: {resumo['declarado']} declarado(s), "
                       f"{resumo['sem_plano_declarado']} sem plano; 0 documentado"))
    return {"itens": itens, "resumo": resumo}


FIXTURE = {
    "ok": True, "url": URL_SUB_PAINEL, "lido_em": "2026-09-22",
    "colunas": ["Índice", "Calha", "Município", "Plano", "Ano do Plano"],
    "linhas": [
        {"indice": 1, "celulas": {"Índice": "1", "Calha": "Alto Solimões",
                                  "Município": "Atalaia do Norte", "Plano": "",
                                  "Ano do Plano": "2026"},
         "url_do_link": "https://defesacivil.am.gov.br/planos/atalaia-do-norte.pdf",
         "como_obtido": "href na própria célula"},
        {"indice": 2, "celulas": {"Índice": "2", "Calha": "Alto Solimões",
                                  "Município": "Benjamin Constant", "Plano": "",
                                  "Ano do Plano": "2026"},
         "url_do_link": None, "como_obtido": "ícone sem href — URL não obtida sem clique"},
        {"indice": 3, "celulas": {"Índice": "3", "Calha": "Madeira",
                                  "Município": "Humaitá", "Plano": "", "Ano do Plano": ""},
         "url_do_link": None, "como_obtido": "sem link na linha"},
    ],
}


DOC_COM_ATO = (b"<html><body><h1>Plano de Contingencia Municipal</h1>"
               b"<p>Aprovado pelo DECRETO N\xc2\xba 1.234, de 5 de mar\xc3\xa7o de 2026.</p>"
               b"</body></html>")
DOC_SEM_ATO = b"<html><body><p>Plano de Contingencia Municipal - versao 2026.</p></body></html>"


def _inertes(respostas=None) -> "EfeitosInertes":
    return EfeitosInertes(respostas or {})


def autoteste() -> int:
    def t_le_ato_por_extenso():
        a = ler_ato("DECRETO Nº 1.234, de 5 de março de 2026, aprova o Plano de Contingência")
        return a and a["numero"] == "1.234" and a["data"] == "2026-03-05" and a["tipo"] == "decreto"

    def t_le_ato_numerico():
        # §180: a data em formato numérico continua sendo lida, mas o ato precisa se apresentar como
        # o do plano — antes desta regra, "Portaria nº 12/2026, de 30 de 06 de 2026" sozinha passava,
        # e era assim que a portaria de nomeação do coordenador virava ato do plano.
        a = ler_ato("Portaria nº 12/2026, de 30 de 06 de 2026, que aprova o plano de contingência municipal")
        return a and a["data"] == "2026-06-30"

    def t_texto_sem_ato_nao_inventa():
        return ler_ato("Plano de Contingência Municipal — versão 2026, sem ato publicado") is None

    def t_data_impossivel_vira_none():
        return ler_ato("Decreto nº 9, de 31 de fevereiro de 2026") is None

    def t_pdf_ilegivel_nao_vira_ausencia_de_ato():
        """PDF corrompido devolve texto vazio — e texto vazio nunca pode ser lido como
        'não há ato'. Quem chama tem de tratar como lacuna."""
        return texto_do_documento(b"%PDF-1.4 lixo binario", "x.pdf") == ""

    def t_html_servido_em_url_pdf():
        """Portal estadual que responde HTML numa URL .pdf: o conteúdo manda. Tratar pela
        extensão produziria lacuna falsa num documento perfeitamente legível."""
        return (eh_pdf(DOC_COM_ATO, "https://x/plano.pdf") is False
                and eh_pdf(b"%PDF-1.7 ...", "https://x/sem-extensao") is True
                and ler_ato(texto_do_documento(DOC_COM_ATO, "https://x/plano.pdf")) is not None)

    # As 20 linhas que a rodada renderizada de 23/09/2026 de fato devolveu, com o rótulo de
    # interface colado no fim. Na rodada, TODAS falharam o casamento com o IBGE.
    LINHAS_REAIS_23_09 = [
        "Atalaia do Norte", "Benjamin Constant", "Tabatinga", "São Paulo de Olivença",
        "Amaturá", "Santo Antônio do Içá", "Tonantins", "Jutaí", "Fonte Boa", "Japurá",
        "Maraã", "Uarini", "Alvarães", "Tefé", "Coari", "Codajás", "Anori", "Anamã",
        "Caapiranga", "Manacapuru",
    ]

    def t_limpa_rotulo_de_interface():
        return limpar_rotulo_powerbi(
            "Atalaia do Norte Formatação Condicional Adicional") == "Atalaia do Norte"

    def t_limpeza_nao_mutila_nome_longo():
        # São Paulo de Olivença tem quatro palavras; um corte por contagem cega o destruiria.
        return (limpar_rotulo_powerbi("São Paulo de Olivença Formatação Condicional Adicional")
                == "São Paulo de Olivença"
                and limpar_rotulo_powerbi("Santo Antônio do Içá") == "Santo Antônio do Içá")

    def t_rotulo_sozinho_nao_vira_nome_vazio():
        # Célula que só tem a etiqueta não vira "" (que casaria com qualquer coisa): fica
        # como está e falha o casamento, isto é, vira lacuna declarada.
        return limpar_rotulo_powerbi("Formatação Condicional Adicional") != ""

    def t_regressao_20_linhas_reais_casam():
        """As 20 linhas da rodada real casam com o IBGE depois da limpeza. Este é o teste
        que teria evitado o dia: a grade estava certa, o dado estava lá, e o coletor
        devolveu 20 lacunas por causa de uma etiqueta de interface."""
        por_cod, por_nome = referencia_ibge()
        for nome in LINHAS_REAIS_23_09:
            bruto = f"{nome} Formatação Condicional Adicional"
            if not casar_ibge(bruto, por_nome):
                return False
        return True

    def t_casa_ibge_com_acento_e_caixa():
        _, por_nome = referencia_ibge()
        return (casar_ibge("SAO GABRIEL DA CACHOEIRA", por_nome)
                == casar_ibge("São Gabriel da Cachoeira", por_nome) is not None)

    def t_nome_desconhecido_nao_casa():
        _, por_nome = referencia_ibge()
        return casar_ibge("Município Que Não Existe", por_nome) is None

    def t_linha_para_registro():
        r = linha_para_registro(FIXTURE["linhas"][0])
        return (r["municipio_no_painel"] == "Atalaia do Norte" and r["ano_do_plano"] == 2026
                and r["calha"] == "Alto Solimões")

    def t_link_abre_com_ato_vira_documentado():
        """Único caminho para `documentado`: o link abriu E o ato tem número e data lidos
        do próprio documento. Aqui a data é 05/03/2026, ANTES do ciclo — logo no_ciclo=False,
        provando que a régua olha a data do ato, não o ano do painel."""
        ef = _inertes({FIXTURE["linhas"][0]["url_do_link"]: DOC_COM_ATO})
        s = coletar(URL_SUB_PAINEL, de_arquivo=_fixture_em_disco(), limite=3, efeitos=ef)
        a = {i["municipio_no_painel"]: i for i in s["itens"]}["Atalaia do Norte"]
        return (a["camada"] == "documentado" and a["ato"]["numero"] == "1.234"
                and a["no_ciclo"] is False and a["hash_evidencia"]
                and a["promovivel"] is False)

    def t_recusa_explicita_nao_cai_na_reserva():
        """A regra do projeto: não contornar bloqueio de acesso de fonte. 403, 401, 429 e 451
        são o servidor RESPONDENDO "não" — ir buscar a mesma página numa captura de arquivo
        seria dar a volta por fora. A reserva existe para o caso oposto, em que a conexão nem
        vira conversa HTTP e portanto não há recusa a respeitar."""
        import urllib.error

        for codigo in (401, 403, 429, 451):
            def recusa(url, timeout=40, _c=codigo):
                raise urllib.error.HTTPError(url, _c, "recusa", {}, None)
            try:
                buscar_com_procedencia("https://x.gov.br/p.pdf", buscar_fn=recusa)
                return False                      # não podia ter voltado com conteúdo
            except urllib.error.HTTPError as e:
                if e.code != codigo:
                    return False
        return True

    def t_falha_de_conexao_cai_na_reserva():
        """O caso do AM: "Connection reset by peer", sem resposta HTTP nenhuma. Aí a reserva
        vale, e o conteúdo volta marcado como captura — nunca como leitura na fonte."""
        def reset(url, timeout=40):
            if "web.archive.org" in url:
                return b"%PDF-copia arquivada"
            raise ConnectionResetError(104, "Connection reset by peer")
        conteudo, proc = buscar_com_procedencia("https://x.gov.br/p.pdf", buscar_fn=reset)
        return conteudo.startswith(b"%PDF-") and proc == "captura do Wayback"

    def t_erro_do_servidor_ainda_usa_reserva():
        """404 e 5xx não são recusa de acesso: são página que sumiu ou servidor com defeito.
        Aí a captura de arquivo é exatamente o instrumento certo."""
        def erro(url, timeout=40):
            import urllib.error as ue
            if "web.archive.org" in url:
                return b"%PDF-copia"
            raise ue.HTTPError(url, 404, "Not Found", {}, None)
        return buscar_com_procedencia("https://x.gov.br/p.pdf", buscar_fn=erro)[1] == "captura do Wayback"

    def t_documento_direto_declara_procedencia():
        """Mesmo o caminho feliz passa a dizer de onde veio: sem o campo, a leitura na fonte
        e a leitura numa cópia de arquivo viravam a mesma coisa no banco."""
        ef = _inertes({FIXTURE["linhas"][0]["url_do_link"]: DOC_COM_ATO})
        s2 = coletar(URL_SUB_PAINEL, de_arquivo=_fixture_em_disco(), limite=3, efeitos=ef)
        a = {i["municipio_no_painel"]: i for i in s2["itens"]}["Atalaia do Norte"]
        return a["procedencia_do_documento"] == "fonte direta" and "observacao" not in a

    def t_ato_lido_em_captura_nao_se_passa_por_fonte():
        """O ato está legível, então vira `documentado` — mas o registro diz, na cara, que
        foi lido numa captura de arquivo e que o documento é o arquivado, não o vigente.
        Sem esta marca o banco afirmaria mais do que a fonte entregou."""
        ef = _inertes({FIXTURE["linhas"][0]["url_do_link"]:
                       (DOC_COM_ATO, "captura do Wayback")})
        s2 = coletar(URL_SUB_PAINEL, de_arquivo=_fixture_em_disco(), limite=3, efeitos=ef)
        a = {i["municipio_no_painel"]: i for i in s2["itens"]}["Atalaia do Norte"]
        return (a["camada"] == "documentado"
                and a["procedencia_do_documento"] == "captura do Wayback"
                and "não necessariamente o vigente" in (a.get("observacao") or "")
                and a["promovivel"] is False)

    def t_captura_sem_ato_continua_declarado():
        """Captura de arquivo não promove nada sozinha: sem número e data de ato legíveis,
        a camada continua `declarado`, com a procedência anotada."""
        ef = _inertes({FIXTURE["linhas"][0]["url_do_link"]:
                       (DOC_SEM_ATO, "captura do Wayback")})
        s2 = coletar(URL_SUB_PAINEL, de_arquivo=_fixture_em_disco(), limite=3, efeitos=ef)
        a = {i["municipio_no_painel"]: i for i in s2["itens"]}["Atalaia do Norte"]
        return (a["camada"] == "declarado" and a["ato"] is None
                and "captura do Wayback" in (a.get("observacao") or ""))

    def t_link_abre_sem_ato_continua_declarado():
        ef = _inertes({FIXTURE["linhas"][0]["url_do_link"]: DOC_SEM_ATO})
        s = coletar(URL_SUB_PAINEL, de_arquivo=_fixture_em_disco(), limite=3, efeitos=ef)
        a = {i["municipio_no_painel"]: i for i in s["itens"]}["Atalaia do Norte"]
        return a["camada"] == "declarado" and a["ato"] is None and a["hash_evidencia"]

    def t_link_que_nao_abre_vira_lacuna():
        ef = _inertes()                       # nenhuma resposta simulada → buscar levanta
        s = coletar(URL_SUB_PAINEL, de_arquivo=_fixture_em_disco(), limite=3, efeitos=ef)
        a = {i["municipio_no_painel"]: i for i in s["itens"]}["Atalaia do Norte"]
        return (a["camada"] == "declarado" and a["hash_evidencia"] is None
                and any("Atalaia" in f for f, _ in ef.lacunas))

    def t_eliminacao_vale_no_caminho_renderizado():
        """A regra de eliminação nasceu na semeadura e NÃO era chamada aqui — a rodada real
        de 23/09 leu os 62 municípios e ainda assim devolveu um sem código IBGE, porque o
        painel escreve "Careiro Castanho" e o IBGE registra "Careiro". Monta uma grade com
        os 62 nomes do IBGE, troca só esse por "Careiro Castanho", e cobra a dedução."""
        por_cod, por_nome = referencia_ibge()
        nomes = sorted((por_cod[c]["nome"] for (n, uf), c in por_nome.items() if uf == "AM"))
        nomes = [("Careiro Castanho" if n == "Careiro" else n) for n in nomes]
        grade = {"ok": True, "colunas": ["Município", "Calha", "Ano do Plano"],
                 "linhas": [{"indice": i, "celulas": {"Município": n, "Calha": "—",
                                                      "Ano do Plano": "2026"},
                             "url_do_link": None, "como_obtido": "sem link na linha"}
                            for i, n in enumerate(nomes, 1)]}
        s2 = coletar(URL_SUB_PAINEL, de_arquivo=_escrever_tmp(grade), efeitos=_inertes())
        por_painel = {i["municipio_no_painel"]: i for i in s2["itens"]}
        cc = por_painel.get("Careiro Castanho")
        sem_ibge = [i for i in s2["itens"] if not i["ibge"]]
        return (cc and cc["ibge"] and "elimina" in (cc.get("casamento_ibge") or "")
                and not sem_ibge)

    def t_eliminacao_nao_dispara_em_leitura_parcial():
        """Duas linhas lidas de 62 deixam 61 códigos sem par: a eliminação não pode deduzir
        nada aí. Um nome desconhecido numa leitura parcial continua lacuna declarada."""
        grade = {"ok": True, "colunas": ["Município", "Ano do Plano"],
                 "linhas": [{"indice": 1, "celulas": {"Município": "Manaus",
                                                      "Ano do Plano": "2026"},
                             "url_do_link": None, "como_obtido": "sem link na linha"},
                            {"indice": 2, "celulas": {"Município": "Cidade Inexistente",
                                                      "Ano do Plano": "2026"},
                             "url_do_link": None, "como_obtido": "sem link na linha"}]}
        s2 = coletar(URL_SUB_PAINEL, de_arquivo=_escrever_tmp(grade), efeitos=_inertes())
        por_painel = {i["municipio_no_painel"]: i for i in s2["itens"]}
        return por_painel["Cidade Inexistente"]["ibge"] is None

    def t_ano_sem_link_fica_declarado():
        """O coração da regra: painel diz 2026, não há link → declarado, nunca documentado,
        e nunca 'antecipado por ser de 2026'."""
        s = coletar(URL_SUB_PAINEL, de_arquivo=_fixture_em_disco(), limite=3, efeitos=_inertes())
        bc = {i["municipio_no_painel"]: i for i in s["itens"]}["Benjamin Constant"]
        return (bc["camada"] == "declarado" and bc["ato"] is None
                and bc["promovivel"] is False and "no_ciclo" not in bc)

    def t_sem_ano_e_sem_link_e_sem_plano():
        s = coletar(URL_SUB_PAINEL, de_arquivo=_fixture_em_disco(), limite=3, efeitos=_inertes())
        h = {i["municipio_no_painel"]: i for i in s["itens"]}["Humaitá"]
        return h["camada"] == "sem_plano_declarado" and h["ibge"] is not None

    def t_render_falho_vira_lacuna():
        ef = _inertes()
        s = coletar(URL_SUB_PAINEL, de_arquivo=_fixture_falha_em_disco(), efeitos=ef)
        return s["itens"] == [] and s["resumo"].get("erro") and len(ef.lacunas) == 1

    def t_trava_de_campo():
        s = coletar(URL_SUB_PAINEL, de_arquivo=_fixture_em_disco(), limite=3, efeitos=_inertes())
        return all(i["promovivel"] is False and i["documento_oficial_confirmado"] is None
                   for i in s["itens"])

    def t_autoteste_nao_toca_em_data():
        """Regressão da falha encontrada ao construir este coletor: a primeira versão do
        autoteste batia na rede e escrevia em log_buscas.json e fontes_consultadas.json a
        cada execução do portão, deixando a árvore suja."""
        antes = {n: (RAIZ / "data" / n).read_bytes()
                 for n in ("log_buscas.json", "fontes_consultadas.json")}
        coletar(URL_SUB_PAINEL, de_arquivo=_fixture_em_disco(), limite=3, efeitos=_inertes())
        return all((RAIZ / "data" / n).read_bytes() == b for n, b in antes.items())

    def t_semeadura_nunca_produz_documentado():
        """A leitura humana de 22/09 não capturou link nenhum — logo nenhum município pode
        sair dela como `documentado`, por mais que o painel diga 2026."""
        ef = _inertes()
        s = semear_da_sonda(efeitos=ef)
        if not s["itens"]:
            return False
        return (s["resumo"]["documentado"] == 0 and s["resumo"]["no_ciclo"] == 0
                and all(i["camada"] in ("declarado", "sem_plano_declarado")
                        and i["ato"] is None and i["promovivel"] is False
                        and i["hash_evidencia"] is None for i in s["itens"]))

    def t_semeadura_casa_os_62_com_ibge():
        s = semear_da_sonda(efeitos=_inertes())
        return (s["resumo"]["n_linhas_lidas"] == 62 and s["resumo"]["sem_codigo_ibge"] == 0
                and s["resumo"]["declarado"] == 51 and s["resumo"]["sem_plano_declarado"] == 11)

    def t_careiro_casa_por_eliminacao_e_fica_marcado():
        """O painel diz 'Careiro Castanho' (nome popular); o IBGE diz 'Careiro'. Existe um
        'Careiro da Várzea' distinto, que casa sozinho — por isso sobra um de cada lado e a
        dedução é segura. O item tem de registrar COMO casou."""
        s = semear_da_sonda(efeitos=_inertes())
        c = {i["municipio_no_painel"]: i for i in s["itens"]}["Careiro Castanho"]
        v = {i["municipio_no_painel"]: i for i in s["itens"]}["Careiro da Várzea"]
        return (c["nome_ibge"] == "Careiro" and "elimina" in (c["casamento_ibge"] or "")
                and v["nome_ibge"] == "Careiro da Várzea"
                and v["casamento_ibge"] == "nome idêntico" and c["ibge"] != v["ibge"])

    def t_eliminacao_nao_dispara_com_dois_sem_par():
        """A trava: sobrando dois nomes desconhecidos, nenhum é deduzido — seria chute, e
        chute aqui move a nota de um terceiro."""
        _, por_nome = referencia_ibge()
        por_cod, _ = referencia_ibge()
        nomes = ["Manaus", "Cidade Inventada A", "Cidade Inventada B"]
        return casar_por_eliminacao(nomes, por_cod, por_nome) == {}

    def t_semeadura_e_offline():
        antes = {n: (RAIZ / "data" / n).read_bytes()
                 for n in ("log_buscas.json", "fontes_consultadas.json")}
        semear_da_sonda(efeitos=_inertes())
        return all((RAIZ / "data" / n).read_bytes() == b for n, b in antes.items())

    def t_leitura_errada_nao_entra_na_fila():
        """Regressão da rodada 1: 20 linhas, nenhuma casando com o IBGE. Isso é grade errada,
        não leitura parcial — e grade errada não polui a fila de triagem humana."""
        s = {"itens": [{"ibge": None, "municipio_no_painel": f"lixo {i}"} for i in range(20)],
             "resumo": {}}
        ok, motivo = leitura_confiavel(s)
        return ok is False and "IBGE" in motivo

    def t_leitura_parcial_demais_nao_entra():
        s = {"itens": [{"ibge": "1300029", "municipio_no_painel": f"m{i}"} for i in range(10)],
             "resumo": {}}
        ok, motivo = leitura_confiavel(s)
        return ok is False and "parcial" in motivo

    def t_leitura_boa_entra():
        s = {"itens": [{"ibge": "1300029", "municipio_no_painel": f"m{i}"} for i in range(62)],
             "resumo": {}}
        return leitura_confiavel(s) == (True, "")

    def t_trava_estrutural():
        fonte = (RAIZ / "coletar_painel_am.py").read_text(encoding="utf-8")
        for proibido in ["estados.json", "saude_uf.json", "municipios.json",
                         "indice.json", "monitor_saude.json"]:
            if re.search(r'gravar\(\s*["\']' + re.escape(proibido), fonte):
                return False
            if re.search(r'open\([^)]*' + re.escape(proibido) + r'[^)]*,\s*["\']([wa])', fonte):
                return False
        return True

    # ---------------------------------------------------------------- §180: os dois defeitos reais
    # Trecho REAL do PLANCON de Jutaí/AM, baixado em 23/09/2026 (a frase existe, com variações, em
    # todos os 51 documentos do painel: é a seção de demografia do modelo estadual).
    TRECHO_ATO_DE_CRIACAO = (
        "8. DEMOGRAFIA Código do Município: 1302306 Ato de Criação: Lei Estadual Nº 96 DE 19 de "
        "dezembro de 1955, e a instalação do município ocorreu em 11 de abril de 1956. População: 25.172"
    )
    TRECHO_ATO_DO_PLANO = (
        "DECRETO Nº 007, DE 06 DE JANEIRO DE 2026. Institui o Plano Municipal de Contingência para "
        "enfrentamento de desastres e dá outras providências."
    )

    def t_ato_de_criacao_do_municipio_nao_e_ato_do_plano():
        return ler_ato(TRECHO_ATO_DE_CRIACAO) is None

    def t_ato_do_plano_e_lido():
        a = ler_ato(TRECHO_ATO_DO_PLANO)
        return a is not None and a["numero"] == "007" and a["data"] == "2026-01-06"

    def t_prefere_o_ato_do_plano_mesmo_vindo_depois():
        # o de criação vem primeiro no documento, como no modelo real
        a = ler_ato(TRECHO_ATO_DE_CRIACAO + " ... " + TRECHO_ATO_DO_PLANO)
        return a is not None and a["data"] == "2026-01-06"

    def t_ato_antigo_fora_de_contexto_de_criacao_nao_passa():
        # a Lei 12.608/2012 é citada em quase todo PLANCON: é a Política Nacional, não o ato do plano
        texto = ("Este plano observa a Lei Nº 12.608 de 10 de abril de 2012, que institui a Política "
                 "Nacional de Proteção e Defesa Civil.")
        return ler_ato(texto) is None

    # Os três atos errados que a PRIMEIRA versão da regra do §180 ainda aceitou, em texto real dos
    # documentos do painel do AM. Cada um é uma armadilha diferente, e é por isso que ficam os três.
    def t_portaria_que_nomeia_coordenador_nao_e_ato_do_plano():
        return ler_ato("Nilson Ferreira Rolim Coordenador Municipal de Proteção e Defesa Civil "
                       "Portaria n° 007 de 06 de Janeiro de 2026. ELABORADO POR: Nilson Ferreira Rolim") is None

    def t_decreto_que_nomeia_coordenador_nao_e_ato_do_plano():
        return ler_ato("RAIMUNDO IVANILDO DE ANDRADE GALVÃO Coordenador Municipal de Proteção e Defesa "
                       "Civil Decreto n° 143-PMC-GP, de 01 de setembro de 2023.") is None

    def t_citacao_em_lista_de_fundamentacao_nao_e_ato_do_plano():
        return ler_ato("• Lei nº 14.750, de 12 de dezembro de 2023 – Atualiza a PNPDEC, reforçando o "
                       "plano de contingência como conjunto de procedimentos e ações") is None

    def t_ato_que_aprova_o_plancon_e_lido():
        a = ler_ato("Decreto nº 1.234, de 10 de julho de 2026 - Aprova o PLANCON municipal para o ciclo 2026/2027.")
        return a is not None and a["data"] == "2026-07-10"

    def t_ano_do_painel_sobrevive_ao_rotulo():
        # células como o painel real devolve: TODAS com o rótulo colado, inclusive a coluna "Plano"
        linha = {"indice": 2, "url_do_link": None, "como_obtido": "x", "celulas": {
            "Seleção de Linha": "Selecionar Linha",
            "Índice": "1 Formatação Condicional Adicional",
            "Calha": "Formatação Condicional Adicional",
            "Município": "Atalaia do Norte Formatação Condicional Adicional",
            "Plano": "Formatação Condicional Adicional",
            "Ano do Plano": "2026 Formatação Condicional Adicional"}}
        r = linha_para_registro(linha)
        # o ano é o dado que o painel declara; a calha, nesta linha, é herança visual do grupo
        return (r["ano_do_plano"] == 2026
                and r["municipio_no_painel"] == "Atalaia do Norte"
                and r["calha"] is None)

    return rodar_autoteste({
        "§180 ato de criação do município não é ato do plano": t_ato_de_criacao_do_municipio_nao_e_ato_do_plano,
        "§180 ato que institui o plano é lido": t_ato_do_plano_e_lido,
        "§180 ato que aprova o PLANCON é lido": t_ato_que_aprova_o_plancon_e_lido,
        "§180 portaria que nomeia o coordenador não é ato do plano": t_portaria_que_nomeia_coordenador_nao_e_ato_do_plano,
        "§180 decreto que nomeia o coordenador não é ato do plano": t_decreto_que_nomeia_coordenador_nao_e_ato_do_plano,
        "§180 citação em lista de fundamentação não é ato do plano": t_citacao_em_lista_de_fundamentacao_nao_e_ato_do_plano,
        "§180 prefere o ato do plano mesmo vindo depois do de criação": t_prefere_o_ato_do_plano_mesmo_vindo_depois,
        "§180 lei citada de passagem (12.608/2012) não vira ato do plano": t_ato_antigo_fora_de_contexto_de_criacao_nao_passa,
        "§180 ano declarado no painel sobrevive ao rótulo de interface": t_ano_do_painel_sobrevive_ao_rotulo,
        "lê nº e data de ato por extenso": t_le_ato_por_extenso,
        "lê nº e data de ato em formato numérico": t_le_ato_numerico,
        "texto sem ato não inventa ato": t_texto_sem_ato_nao_inventa,
        "data impossível vira None (não silencia)": t_data_impossivel_vira_none,
        "PDF ilegível devolve vazio (vira lacuna, não ausência)": t_pdf_ilegivel_nao_vira_ausencia_de_ato,
        "HTML servido em URL .pdf é lido como HTML": t_html_servido_em_url_pdf,
        "limpa rótulo de interface do Power BI": t_limpa_rotulo_de_interface,
        "limpeza não mutila nome longo (São Paulo de Olivença)": t_limpeza_nao_mutila_nome_longo,
        "rótulo sozinho não vira nome vazio": t_rotulo_sozinho_nao_vira_nome_vazio,
        "regressão: as 20 linhas reais de 23/09 casam com o IBGE": t_regressao_20_linhas_reais_casam,
        "casa nome do painel com IBGE (acento/caixa)": t_casa_ibge_com_acento_e_caixa,
        "nome desconhecido não casa (vira lacuna)": t_nome_desconhecido_nao_casa,
        "normaliza linha bruta do renderizador": t_linha_para_registro,
        "link abre + ato com nº e data → documentado": t_link_abre_com_ato_vira_documentado,
        "recusa explícita da fonte não cai na reserva (não se contorna bloqueio)": t_recusa_explicita_nao_cai_na_reserva,
        "falha de conexão cai na reserva, marcada como captura": t_falha_de_conexao_cai_na_reserva,
        "404/5xx ainda usa a reserva (não é recusa de acesso)": t_erro_do_servidor_ainda_usa_reserva,
        "documento lido na fonte declara a procedência": t_documento_direto_declara_procedencia,
        "ato lido em captura não se passa por leitura na fonte": t_ato_lido_em_captura_nao_se_passa_por_fonte,
        "captura sem ato legível continua declarado": t_captura_sem_ato_continua_declarado,
        "link abre sem ato legível → continua declarado": t_link_abre_sem_ato_continua_declarado,
        "link que não abre → lacuna declarada": t_link_que_nao_abre_vira_lacuna,
        "eliminação vale também no caminho renderizado": t_eliminacao_vale_no_caminho_renderizado,
        "eliminação não deduz em leitura parcial": t_eliminacao_nao_dispara_em_leitura_parcial,
        "ano 2026 sem link → declarado, nunca documentado": t_ano_sem_link_fica_declarado,
        "linha sem ano e sem link → sem plano declarado": t_sem_ano_e_sem_link_e_sem_plano,
        "render falho vira lacuna declarada, não ausência": t_render_falho_vira_lacuna,
        "trava de campo: nasce não promovível": t_trava_de_campo,
        "autoteste é offline e não escreve em data/": t_autoteste_nao_toca_em_data,
        "semeadura da leitura humana nunca vira documentado": t_semeadura_nunca_produz_documentado,
        "semeadura casa os 62 municípios com IBGE (51/11)": t_semeadura_casa_os_62_com_ibge,
        "Careiro Castanho casa por eliminação, e fica marcado": t_careiro_casa_por_eliminacao_e_fica_marcado,
        "eliminação não dispara com dois sem par (seria chute)": t_eliminacao_nao_dispara_com_dois_sem_par,
        "semeadura é offline e não escreve em data/": t_semeadura_e_offline,
        "leitura com grade errada não entra na fila": t_leitura_errada_nao_entra_na_fila,
        "leitura parcial demais não entra na fila": t_leitura_parcial_demais_nao_entra,
        "leitura completa entra na fila": t_leitura_boa_entra,
        "trava estrutural: não escreve no banco": t_trava_estrutural,
    })


def _escrever_tmp(obj) -> str:
    import tempfile
    f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    json.dump(obj, f, ensure_ascii=False)
    f.close()
    return f.name


def _fixture_em_disco() -> str:
    return _escrever_tmp(FIXTURE)


def _fixture_falha_em_disco() -> str:
    return _escrever_tmp({"ok": False, "erro": "grade não encontrada no DOM renderizado",
                          "linhas": []})


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    a = sys.argv
    url = a[a.index("--url") + 1] if "--url" in a else URL_SUB_PAINEL
    de_arquivo = a[a.index("--de-arquivo") + 1] if "--de-arquivo" in a else None
    limite = int(a[a.index("--limite") + 1]) if "--limite" in a else None

    if "--semear-da-sonda" in a:
        saida = semear_da_sonda()
    else:
        saida = coletar(url, de_arquivo=de_arquivo, limite=limite)
    ok, motivo = leitura_confiavel(saida)
    if not ok:
        registrar_lacuna("leitura do painel do AM", motivo, "painel AM", 1,
                         strings=[url], uf="AM")
        print(f"Leitura recusada — nada foi escrito na fila.\n  motivo: {motivo}")
        if saida["resumo"].get("erro"):
            print(f"  erro do renderizador: {saida['resumo']['erro']}")
        print("  o artefato da rodada traz o HTML renderizado para conferir a grade.")
        return 1
    fila = gravar_fila(saida, url)
    r = saida["resumo"]
    print(f"\nPainel da Defesa Civil do AM — {r['n_linhas_lidas']} linha(s) lida(s):")
    print(f"  documentado (link abriu + ato com nº e data): {r['documentado']}")
    print(f"  declarado (painel afirma, sem ato legível):    {r['declarado']}")
    print(f"  sem plano declarado no painel:                 {r['sem_plano_declarado']}")
    print(f"  sem código IBGE (lacuna declarada):            {r['sem_codigo_ibge']}")
    print(f"  com ato dentro do ciclo (>= 29/06/2026):       {r['no_ciclo']}")
    if r.get("documentos_de_captura"):
        print(f"  documentos lidos na fonte:                     {r.get('documentos_da_fonte', 0)}")
        print(f"  documentos lidos em captura de arquivo:        {r['documentos_de_captura']}"
              "  ← a fonte não respondeu; o documento é o arquivado")
    print(f"\nFila: data/{FILA} ({len(fila['itens'])} item(ns)).")
    print("Nada entra no banco sem promoção humana (R7). Ano no painel não prova antecipação.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
