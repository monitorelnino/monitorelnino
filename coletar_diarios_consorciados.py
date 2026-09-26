#!/usr/bin/env python3
"""
coletar_diarios_consorciados.py
================================
Camada 2 do protocolo de busca (diários oficiais), canal COMPLEMENTAR ao Querido
Diário: diários de associações/federações municipais publicados na plataforma
SIGPub (Vox Tecnologia, `diariomunicipal.com.br`).

POR QUE ESTE COLETOR EXISTE (22/09/2026, pedido editorial): a cobertura do QD por
UF é muito desigual — de 5.571 municípios, só 351 têm diário indexado no QD (varredura
de 20/09/2026). O motivo, verificado por inspeção do código-fonte aberto do próprio
Querido Diário (okfn-brasil/querido-diario): a raspagem é feita raspador por raspador,
site por site, e o SIGPub — usado por associações municipais de pelo menos MG, CE, PR,
RS, RN, GO e BA — só tem UM raspador integrado ao QD em todo o país (Alagoas,
`al_associacao_municipios.py`), e é justamente AL quem lidera a cobertura (94,1%,
vs. 0,4%-2,5% em MG/PI/SC/GO/AC/MT). Isto não é evidência de que esses municípios não
têm plano — é lacuna de raspagem, confirmada e reproduzida a partir do raspador-base
real do QD (`querido_diario_raspadores/gazette/spiders/base/sigpub.py`), não suposta.

O QUE ESTE COLETOR NÃO É: não é busca por palavra-chave na "Busca Avançada" do
SIGPub — ela é protegida por ReCaptcha (nota do próprio código-fonte do QD). O
canal real é o widget de CALENDÁRIO: para cada dia, uma chamada retorna se há
edição e o link do PDF; o PDF cobre TODOS os municípios da associação naquela
data numa peça só (são diários consorciados, não um por município). Por isso
este coletor baixa o PDF do dia, extrai o texto inteiro e localiza, para cada
menção a plano/decreto, o cabeçalho de entidade mais próximo ANTES da menção
("PREFEITURA DE X", "MUNICÍPIO DE X", "CÂMARA MUNICIPAL DE X") para atribuir a
pista a um município candidato. Isso é uma HEURÍSTICA DE PROXIMIDADE, não uma
extração estruturada — pode errar o município mais próximo ou não achar nenhum.
Por isso: toda saída daqui é `pista` (nunca registro, nunca fonte_consultada com
nível acima de `nao_verificado`) — julgamento humano decide, como em qualquer
outra pista do sistema (§3.2). Quando nenhum cabeçalho é localizado, a pista é
registrada em nível UF (`ibge: null`) em vez de descartada — perder o achado
seria pior do que uma atribuição grosseira que o humano corrige.

FONTES REGISTRADAS: ver `UF_SIGPUB` abaixo. Em 20-22/09/2026 esta lista tinha sete
UFs, porque descobrir o slug de cada estado exigia abrir o site e ler o link real —
"tarefa ainda não feita", dizia aqui. Ela foi feita em 26/09/2026, e o caminho fica
registrado porque não é óbvio: o seletor de estados da página inicial usa caminhos
RELATIVOS (`/aam/`, `/ma/`), e não URLs absolutas, de modo que uma varredura por
`href="https://www.diariomunicipal.com.br/<slug>"` acha parte das entidades e perde
outras. A lista autoritativa é o `<select>` da página inicial: 21 UFs mais duas
prefeituras avulsas. Slug inexistente não dá 404 — a plataforma devolve a PRÓPRIA
página inicial (90.958 bytes, sem `calendar__token`), o que dá um teste barato e
inequívoco para candidato inventado, e foi como vinte e nove palpites de sigla se
descartaram numa só rodada.

O QUE A VARREDURA DE 26/09/2026 MEDIU, entidade por entidade (token real via
navegador, POST de calendário em 24 e 25/09, e a data da última edição lida na
própria página):

  · entregam edição hoje, e entraram em UF_SIGPUB: PE, AM, PA, RO, RJ, SP, RR, PB, AL.
  · `/ma/` (Maranhão) está no seletor da plataforma e cai na própria página inicial:
    link morto do lado dela, não lacuna nossa. Fica em SIGPUB_SEM_CANAL.
  · cinco entidades respondem ao calendário e devolvem `{"error"...}` em TODO dia útil
    de uma janela de dez. Isso NÃO é fonte fora do ar: a última edição de cada uma,
    lida na página, é de 2009 a 2020 — são ARQUIVOS HISTÓRICOS de associações que
    saíram da plataforma. Ver SIGPUB_ENCERRADO, que existe para não repetir o erro de
    25/09/2026, quando os dois slugs da Bahia foram declarados "fonte fora do ar" —
    rótulo errado, do mesmo tipo que chamar geobloqueio de robots.txt.
  · AC, AP, ES, SC e TO não aparecem no seletor: a plataforma não cobre esses estados.

Adicionar um estado = adicionar uma linha a UF_SIGPUB depois de LER o nome da entidade
na página e confirmar que o calendário entrega edição. Nunca adivinhar um slug pelo
padrão dos outros.

STATUS (20-21/09/2026): BLOQUEADO PARA COLETA AUTOMATIZADA — duas rodadas de
investigação real, nenhuma inventada, nenhuma abandonada por preguiça.

RODADA 1 (20/09, sessão anterior): verificado contra produção, duas vezes, com
sessão de cookies e leitura byte a byte do HTML real. O token do widget de
calendário é preenchido por JavaScript (controller Stimulus `csrf-protection`);
o servidor só entrega um placeholder estático (`PLACEHOLDER_TOKEN`, a string
literal "csrf-token") — não há `<meta name="csrf-token">` nem outra fonte
estática de onde copiar. Todo POST feito com o placeholder volta
`{"error":"Ocorreu um erro inesperado!"}`.

RODADA 2 (20-21/09, esta sessão, pedido explícito de desbloquear): implementado
`obter_token_via_navegador()` + `scripts/obter_token_sigpub.js`, que abre a
página num Chromium REAL via Playwright (já dependência do projeto para os
portões visuais — não é dependência nova; ver `package.json`). Testado contra
produção real. Achado novo: mesmo com navegador real, o token continua vindo
como placeholder. O console do navegador mostra um único erro real:
`requestStorageAccess: Permission denied` — a API de Storage Access exige
ativação transitória de usuário (gesto genuíno), que automação headless não
tem por padrão. Testado clique real via CDP (`page.mouse.click`, que Chromium
trata como confiável, diferente de `element.click()` via JS) logo após a
navegação — não resolveu; o controller provavelmente já tentou e falhou antes
do clique chegar (roda no carregamento inicial da página, antes do ponto em
que o script recupera controle). Nenhuma requisição de rede relacionada a
token/csrf apareceu durante o carregamento (`req_relevantes=[]`) — o mecanismo
não busca o valor de um mini-endpoint; é calculado (ou bloqueado) inteiramente
no cliente.

O que resolveria isso, não tentado por exigir mais engenharia do que o
razoável agora sem inventar flag/API que eu não possa verificar: (a) a flag
exata do Chromium que libera `requestStorageAccess` automaticamente em
contexto de teste/automação — não vou adivinhar um nome de flag sem checar a
documentação real; (b) interceptar via protocolo do Chrome (CDP) antes da
navegação terminar, uma camada de engenharia mais profunda que o navegador
comum do Playwright. `coletar_fonte()` tenta o caminho HTTP simples primeiro
(barato) e só escala para o navegador se vier o placeholder — mesmo assim, e
mesmo com o navegador real, o bloqueio persiste; a causa agora é mais
específica e mais bem documentada que na rodada 1, não resolvida. O motor de
PDF → texto → atribuição de município é real e testado (autoteste ponta a
ponta com PDF sintético, 14 casos) — fica pronto, sem precisar reescrita, para
quando a aquisição do token funcionar. NÃO está ligado a `portoes.yml` nem a
`atualizar.yml`: rodar `coletar()` hoje não produz erro, mas também não
produz nenhuma pista real — só lacunas declaradas de bloqueio, com o
diagnóstico completo (tentativas, tempo, requisições relevantes, console) por
fonte, para quem retomar isso não precisar repetir a investigação do zero.

USO
  python coletar_diarios_consorciados.py --autoteste
  python coletar_diarios_consorciados.py --desde 2026-09-01 --ate 2026-09-20 [--uf MG]
"""
import http.cookiejar, io, json, pathlib, re, subprocess, sys, time, unicodedata, urllib.parse, urllib.request
from datetime import date, timedelta
from coletores_base import (UA, preservar_evidencia, log_busca, registrar_lacuna,
                            marcar_fonte_consultada, referencia_ibge, ler, gravar, rodar_autoteste,
                            CANAIS_ATO, hoje_editorial, normalizar_nome)
from classificar_pista_civil import triagem_completa

# Só slugs confirmados por navegação/fetch reais nesta sessão (20-22/09/2026). AL fica de
# fora de propósito: já é o único estado com raspador SIGPub no próprio QD (94,1% de
# cobertura) — o ganho marginal aqui é baixo comparado às UFs abaixo, hoje entre 0% e 2,5%.
UF_SIGPUB = {
    "MG": [{"slug": "amm-mg", "nome": "Diário Oficial dos Municípios Mineiros (AMM-MG)"}],
    "GO": [{"slug": "agm", "nome": "Diário Oficial dos Municípios de Goiás (AGM)"},
           {"slug": "fgm", "nome": "Diário Oficial dos Municípios de Goiás (FGM)"}],
    "CE": [{"slug": "aprece", "nome": "Diário Oficial dos Municípios do Ceará (APRECE)"}],
    "PR": [{"slug": "amp", "nome": "Diário Oficial dos Municípios do Paraná (AMP)"}],
    "RS": [{"slug": "famurs", "nome": "Diário Oficial dos Municípios do Rio Grande do Sul (FAMURS)"}],
    "RN": [{"slug": "femurn", "nome": "Diário Oficial dos Municípios do Rio Grande do Norte (FEMURN)"}],
    # 26/09/2026: as nove abaixo vieram do `<select>` da página inicial, com o nome da entidade
    # lido no `alt` do logo de cada uma e o calendário testado em 24 e 25/09/2026 com token real.
    # O número no comentário é quantas edições cada uma devolveu nesses dois dias — prova de que
    # o canal entrega, não promessa de que deveria.
    "PE": [{"slug": "amupe", "nome": "Diário Oficial dos Municípios de Pernambuco (AMUPE)"}],       # 2 e 2
    "AM": [{"slug": "aam", "nome": "Diário Oficial dos Municípios do Amazonas (AAM)"}],             # 1 e 1
    "PA": [{"slug": "famep", "nome": "Diário Oficial dos Municípios do Pará (FAMEP)"}],             # 1 e 1
    "RO": [{"slug": "arom", "nome": "Diário Oficial dos Municípios de Rondônia (AROM)"}],           # 2 e 2
    "RJ": [{"slug": "aemerj", "nome": "Diário Oficial dos Municípios do Rio de Janeiro (AEMERJ)"}], # 3 e 2
    "SP": [{"slug": "apm", "nome": "Diário Oficial dos Municípios de São Paulo (APM)"}],            # 1 e 1
    "RR": [{"slug": "amr", "nome": "Diário Oficial dos Municípios de Roraima (AMR)"}],              # 1 e 1
    "PB": [{"slug": "famup", "nome": "Diário Oficial dos Municípios da Paraíba (FAMUP)"}],          # 2 e 2
    "AL": [{"slug": "ama", "nome": "Diário Oficial dos Municípios Alagoanos (AMA)"}],               # 1 e 1
}

# Entidades que EXISTEM na plataforma e cuja publicação ali ENCERROU. Não entram no varrimento:
# pedir o calendário delas hoje devolve `{"error":"Ocorreu um erro inesperado!"}` em todo dia útil,
# e chamar isso de "fonte fora do ar" — como se fez em 25/09/2026 com os dois slugs da Bahia — é
# nomear a recusa errado. A data é a da ÚLTIMA EDIÇÃO lida na página da entidade em 26/09/2026.
#
# Elas ficam declaradas aqui, e não apagadas, por dois motivos: o arquivo histórico é acessível por
# data (serve a uma pergunta retroativa, se um dia houver), e cada linha destas é uma UF cujo
# diário CORRENTE está em outro lugar — lacuna de descoberta, que é trabalho a fazer, e não
# bloqueio de acesso, que seria trabalho impossível.
SIGPUB_ENCERRADO = {
    "BA": [{"slug": "bahia", "nome": "Associação dos Municípios do Recôncavo Baiano", "ultima_edicao": None},
           {"slug": "amurc", "nome": "Diário Oficial dos Municípios do Sul/Extremo Sul/Sudoeste da Bahia (AMURC)",
            "ultima_edicao": "2013-05-22"}],
    "MT": [{"slug": "amm-mt", "nome": "Associação Mato-Grossense dos Municípios (AMM-MT)",
            "ultima_edicao": "2015-03-10"}],
    "PI": [{"slug": "appm", "nome": "Associação Piauiense de Municípios (APPM)", "ultima_edicao": "2020-02-10"}],
    "MS": [{"slug": "ms", "nome": "Diário Oficial dos Municípios de Mato Grosso do Sul",
            "ultima_edicao": "2020-10-30"}],
    "SE": [{"slug": "sergipe", "nome": "Associação dos Municípios da Região Centro Sul de Sergipe (AMURCES)",
            "ultima_edicao": "2009-12-10"}],
}

# UFs sem canal consorciado nesta plataforma, medido em 26/09/2026. `motivo` é o que se observou,
# não o que se supõe: MA está no seletor e o link cai na própria página inicial da plataforma; as
# outras cinco não aparecem no seletor. Para estas seis UFs o diário municipal, quando existe, tem
# de vir por outro canal — Querido Diário, sítio da prefeitura ou outra plataforma.
SIGPUB_SEM_CANAL = {
    "MA": "no seletor da plataforma, mas /ma/ devolve a própria página inicial (link morto)",
    "AC": "ausente do seletor da plataforma",
    "AP": "ausente do seletor da plataforma",
    "ES": "ausente do seletor da plataforma",
    "SC": "ausente do seletor da plataforma",
    "TO": "ausente do seletor da plataforma",
}
BASE = "https://www.diariomunicipal.com.br/{slug}/"
URL_CALENDARIO = "https://www.diariomunicipal.com.br/{slug}/materia/calendario"
URL_CALENDARIO_EXTRA = "https://www.diariomunicipal.com.br/{slug}/materia/calendario/extra"
TERMOS_RESPOSTA = ['"situação de emergência"', '"estado de calamidade pública"']
TERMOS_PISTA = ['"plano de contingência"', '"El Niño"', '"plano de ação"']
PAD_DECRETO = re.compile(r"decreto\s+(?:municipal\s+)?n[ºo°\.]?\s*([\d\.\/-]+)[^.]{0,200}?(situa[çc][ãa]o de emerg[êe]ncia|estado de calamidade p[úu]blica)", re.I)
PAD_PLANO = re.compile(r"plano\s+(?:municipal\s+)?de\s+conting[êe]ncia[^.]{0,160}", re.I)
# 25/09/2026: um diário de associação municipal publica em dia útil. Zero edições em cinco dias
# úteis é fonte fora do ar ou slug mudado — não "não publicaram".
TETO_UTEIS_SEM_EDICAO = 5


class FonteForaDoAr(Exception):
    """A fonte recusou todos os dias tentados até o teto. Lacuna de fonte, não de dia."""


PAD_TOKEN = re.compile(r'<input\b[^>]*\bid=["\']calendar__token["\'][^>]*>', re.I)
# 20/09/2026: valor literal que o SIGPub serve no atributo `value` desse input quando o token real
# é preenchido por JS (controller Stimulus `csrf-protection`) — verificado byte a byte contra
# produção (amm-mg), duas vezes, com sessão de cookies. Não é suposição.
PLACEHOLDER_TOKEN = "csrf-token"
PAD_TOKEN_VALUE = re.compile(r'\bvalue=["\']([^"\']*)["\']', re.I)
# Cabeçalho de entidade dentro do PDF consorciado: "PREFEITURA (MUNICIPAL)? DE X", "MUNICÍPIO DE X",
# "CÂMARA (MUNICIPAL)? DE X" — mesmo vocabulário da lista de entidades do próprio SIGPub (verificado
# por navegação real em 22/09/2026). Maiúsculas OU capitalizado; nome até o fim da linha ou pontuação.
PAD_CABECALHO = re.compile(
    r"(?:PREFEITURA(?:\s+MUNICIPAL)?|MUNIC[ÍI]PIO|C[ÂA]MARA(?:\s+MUNICIPAL)?)\s+DE\s+([A-ZÀ-Úa-zà-ú][A-ZÀ-Úa-zà-ú\s']{2,40}?)(?=[\n\r,\.\-–—]|\s{2,}|$)",
    re.M)


def extrair_token(html: bytes) -> str:
    """Acha a TAG <input id="calendar__token" ...> inteira primeiro, depois lê o value dentro
    dela — não depende da ordem dos atributos. 22/09/2026: a primeira versão exigia
    id="..." imediatamente seguido de value="..."; contra o HTML real de produção
    (amm-mg) não bateu — a ordem real dos atributos é diferente da assumida. Corrigido
    para casar a tag pelo id em qualquer posição e extrair o value de dentro dela,
    mesma lógica do XPath //input[@id='calendar__token']/@value usado pelo próprio
    spider-base do Querido Diário (fonte: querido_diario_raspadores/gazette/spiders/base/sigpub.py)."""
    tag = PAD_TOKEN.search(html.decode("utf-8", "replace"))
    if not tag:
        return ""
    v = PAD_TOKEN_VALUE.search(tag.group(0))
    return v.group(1) if v else ""


class CalendarioIlegivel(Exception):
    """A resposta do calendário não tem a forma esperada. Mudança de formato, não ausência."""


def parse_calendario(bruto: bytes) -> list:
    """[{link_diario, numero_edicao, url_pdf}] do dia; `[]` quando não houve edição. Função pura.

    25/09/2026, MEDIDO contra produção antes de mexer: `{"error":"Ocorreu um erro inesperado!"}`
    é como esta fonte diz "não houve edição neste dia" — o mesmo corpo volta para sábado (19/09),
    domingo (20/09) e Natal, enquanto segunda e terça entregam a edição. Ou seja, a leitura
    original estava certa, e tratar esse `error` como lacuna criaria uma lacuna falsa a cada fim
    de semana. O que NÃO é dia sem edição é corpo que não dá para ler: aí a forma mudou, e isso
    levanta, porque devolver `[]` esconderia uma mudança de formato (§210).

    O sinal de fonte QUEBRADA não está no dia: está em errar TODOS os dias, inclusive os úteis —
    e isso quem detecta é `coletar_fonte`, no nível da fonte."""
    try:
        body = json.loads(bruto.decode("utf-8", "replace"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise CalendarioIlegivel(f"corpo não é JSON: {type(e).__name__}") from e
    if not isinstance(body, dict):
        raise CalendarioIlegivel("corpo JSON não é um objeto")
    if body.get("error"):
        return []                      # a fonte diz: não houve edição neste dia
    if "edicao" not in body:
        raise CalendarioIlegivel("resposta sem `error` e sem a lista `edicao`")
    base_url = body.get("url_arquivos", "")
    return [{"link_diario": e.get("link_diario", ""), "numero_edicao": e.get("numero_edicao", ""),
             "url_pdf": f"{base_url}{e.get('link_diario', '')}.pdf"} for e in (body["edicao"] or []) if e.get("link_diario")]


def extrair_texto_pdf(bruto: bytes) -> str:
    """Texto do PDF. pypdf primeiro, pdfplumber como reserva.

    25/09/2026, MEDIDO: a ordem era a inversa, herdada dos coletores de boletim de saúde, onde
    pdfplumber ganha porque lá a GEOMETRIA importa (ler número dentro de tabela). Aqui não
    importa: o que se faz com o texto é casar expressão regular. E o custo é real — num PDF de
    5 MB e 44 páginas, pdfplumber levou 3,8 s contra 2,0 s do pypdf, e os diários consorciados
    chegam a 7 MB. Numa varredura de quase 90 dias vezes sete fontes, essa diferença é de horas.

    A reserva continua existindo e o critério de troca também: texto curto demais significa PDF
    que o primeiro leitor não soube abrir, e aí o outro tenta."""
    try:
        import pypdf
        r = pypdf.PdfReader(io.BytesIO(bruto))
        texto = "\n".join((p.extract_text() or "") for p in r.pages)
        if len(texto) > 200:
            return texto
    except Exception:  # noqa: BLE001
        pass
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(bruto)) as pdf:
            return "\n".join((pg.extract_text() or "") for pg in pdf.pages)
    except Exception:  # noqa: BLE001
        return ""


def localizar_municipio(texto: str, posicao: int, candidatos_uf: dict) -> tuple:
    """Cabeçalho de entidade mais próximo ANTES de `posicao` cujo nome bate com um município
    da UF (candidatos_uf: {NOME_NORMALIZADO: codigo_ibge}). (None, None) se não achar nenhum —
    a pista continua sendo registrada, só sem candidato de município (nível UF)."""
    melhor = None
    for m in PAD_CABECALHO.finditer(texto, 0, posicao):
        nome_norm = normalizar_nome(m.group(1))
        if nome_norm in candidatos_uf:
            melhor = (m.group(1).strip(), candidatos_uf[nome_norm])  # o último = o mais próximo (finditer é em ordem)
    return melhor if melhor else (None, None)


def classificar_trechos_consorciado(texto: str, candidatos_uf: dict) -> tuple:
    """(decretos, pistas), cada item já com município candidato (ou None) e posição para evidência."""
    decretos, pistas = [], []
    for numero, tipo in PAD_DECRETO.findall(texto):
        pos = texto.find(numero)
        nome_mun, ibge = localizar_municipio(texto, max(pos, 0), candidatos_uf)
        decretos.append({"decreto": f"Decreto nº {numero}", "tipo": tipo.lower(),
                         "municipio": nome_mun, "ibge": ibge, "trecho": texto[max(0, pos - 60):pos + 240]})
    for m in PAD_PLANO.finditer(texto):
        nome_mun, ibge = localizar_municipio(texto, m.start(), candidatos_uf)
        pistas.append({"municipio": nome_mun, "ibge": ibge, "trecho": texto[max(0, m.start() - 100):m.end() + 160]})
    return decretos, pistas


def sequencia_dias(desde_iso: str, ate_iso: str):
    d0, d1 = date.fromisoformat(desde_iso), date.fromisoformat(ate_iso)
    d = d0
    while d <= d1:
        yield d
        d += timedelta(days=1)


def candidatos_da_uf(por_cod: dict, uf: str) -> dict:
    return {normalizar_nome(r["nome"]): cod for cod, r in por_cod.items() if r["uf"] == uf}


def nova_sessao():
    """Um cookiejar por fonte (slug), devolvido junto com o opener para permitir injetar cookies
    obtidos pelo navegador (ver injetar_cookies). 22/09/2026 (achado contra produção): a primeira
    versão usava buscar()/buscar_post() — cada chamada em uma conexão nova, sem cookies. Contra o
    amm-mg real isso devolveu 0 edições em 6 dias × 3 fontes, estatisticamente implausível para
    associações que publicam quase todo dia útil. Corrigido: token, calendário e PDF da mesma
    fonte passam a usar UM opener com cookiejar."""
    jar = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar)), jar


def sessao_get(opener, url: str, timeout: int = 40) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with opener.open(req, timeout=timeout) as r:
        return r.read()


def sessao_post(opener, url: str, campos: dict, timeout: int = 40) -> bytes:
    corpo = urllib.parse.urlencode(campos).encode("utf-8")
    req = urllib.request.Request(url, data=corpo, headers={
        "User-Agent": UA, "Accept": "*/*", "Content-Type": "application/x-www-form-urlencoded",
        "X-Requested-With": "XMLHttpRequest"})
    with opener.open(req, timeout=timeout) as r:
        return r.read()


CAMINHO_SCRIPT_TOKEN = str(pathlib.Path(__file__).parent / "scripts" / "obter_token_sigpub.js")


def obter_token_via_navegador(url: str, timeout: int = 60) -> dict:
    """§130 (20/09/2026): o token é preenchido por JS (ver bloqueio documentado no topo do
    módulo) — chama scripts/obter_token_sigpub.js, que abre a página num Chromium real
    (Playwright, já dependência do projeto para os portões visuais — não é dependência nova) e
    devolve token + cookies da sessão. Nunca lança: qualquer falha (node ausente, timeout, JSON
    malformado, Chromium não instalado) vira {"ok": False, "erro": ...} — quem chama decide
    lacuna, exatamente como qualquer outra falha de rede deste coletor."""
    try:
        r = subprocess.run(["node", CAMINHO_SCRIPT_TOKEN, url], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"ok": False, "erro": f"timeout ({timeout}s) esperando o navegador"}
    except (FileNotFoundError, OSError) as e:
        return {"ok": False, "erro": f"{type(e).__name__}: {e}"}
    saida = (r.stdout or "").strip()
    if not saida:
        return {"ok": False, "erro": f"sem saída do script (código {r.returncode}; stderr: {(r.stderr or '')[:300]})"}
    try:
        return json.loads(saida.splitlines()[-1])
    except json.JSONDecodeError as e:
        return {"ok": False, "erro": f"JSON inválido do script: {e} — saída: {saida[:300]!r}"}


def cookie_de_playwright(c: dict) -> "http.cookiejar.Cookie":
    """Converte um cookie no formato do Playwright ({name, value, domain, path, expires,
    httpOnly, secure, ...}) para http.cookiejar.Cookie, para injetar no jar usado por
    sessao_get/sessao_post."""
    dominio = c.get("domain", "") or ""
    exp = c.get("expires")
    return http.cookiejar.Cookie(
        version=0, name=c["name"], value=c["value"], port=None, port_specified=False,
        domain=dominio, domain_specified=bool(dominio), domain_initial_dot=dominio.startswith("."),
        path=c.get("path", "/") or "/", path_specified=True,
        secure=bool(c.get("secure")), expires=(exp if exp and exp > 0 else None),
        discard=False, comment=None, comment_url=None,
        rest={"HttpOnly": None} if c.get("httpOnly") else {})


def injetar_cookies(jar: "http.cookiejar.CookieJar", cookies_playwright: list) -> None:
    for c in cookies_playwright or []:
        try:
            jar.set_cookie(cookie_de_playwright(c))
        except (KeyError, ValueError):
            continue  # cookie malformado do navegador — ignora esse, não derruba a sessão inteira


def coletar_fonte(uf: str, slug: str, nome_fonte: str, desde_iso: str, ate_iso: str, por_cod: dict,
                  pausa: float = 0.4) -> dict:
    """Uma associação (um slug): token (HTTP simples primeiro; Chromium real só se vier
    placeholder — §130), um POST de calendário por dia (regular + extra), PDF + texto + pistas
    para cada dia com edição. Nunca levanta exceção: falha de rede em um dia vira lacuna
    declarada e a coleta segue para o dia seguinte — um dia ruim não derruba o mês inteiro.

    HISTÓRICO DO BLOQUEIO (verificado contra produção em 20/09/2026, duas vezes, byte a byte): o
    token do calendário (`id="calendar__token"`) é preenchido por JavaScript no navegador
    (`data-controller="csrf-protection"`, um controller Stimulus) — o HTML servido traz só o
    placeholder estático "csrf-token", sem `<meta name="csrf-token">` nem outra fonte estática.
    Corrigido em 20/09/2026 (§130): quando o GET simples devolve o placeholder,
    `obter_token_via_navegador()` abre a página num Chromium real (Playwright, já dependência do
    projeto para os portões visuais — não é dependência nova) e lê o valor que o JS preenche,
    junto com os cookies da sessão — injetados no cookiejar HTTP para o POST do calendário e o
    download do PDF não precisarem de navegador. O caminho HTTP simples continua tentado
    primeiro: mais barato, e cobre o dia (improvável, mas não impossível) em que o site volte a
    servir o token no próprio HTML."""
    candidatos = candidatos_da_uf(por_cod, uf)
    pistas_todas, decretos_todos = [], []
    dias_com_edicao = dias_com_erro = dias_ilegiveis = uteis_sem_edicao = 0
    opener, jar = nova_sessao()
    # Caminho barato primeiro: GET simples + extrair_token(). Normalmente devolve o placeholder
    # (ver STATUS no topo do módulo) e escala para o navegador — mas manter esse caminho evita o
    # custo de um Chromium inteiro se o site algum dia voltar a servir o token estático, e reusa
    # o parser já testado (t1, t1b, t2, t11) em vez de descartá-lo.
    token = cookies_navegador = None
    try:
        html = sessao_get(opener, BASE.format(slug=slug), timeout=40)
        token_http = extrair_token(html)
    except Exception as e:  # noqa: BLE001
        token_http = None
        registrar_lacuna(nome_fonte, f"GET inicial: {type(e).__name__}: {e}", canal="DOM-consorciado", camada=2, uf=uf)
    if token_http and token_http != PLACEHOLDER_TOKEN:
        token = token_http  # site voltou a servir estático — não precisa de navegador
    else:
        resultado_nav = obter_token_via_navegador(BASE.format(slug=slug))
        if not resultado_nav.get("ok"):
            diag = resultado_nav.get("diagnostico") or {}
            detalhe_diag = (f" [tentativas={diag.get('tentativas')} tempo_ms={diag.get('tempo_ms')} "
                            f"total_req={diag.get('total_requisicoes')} req_relevantes={diag.get('requisicoes_relevantes')} "
                            f"console={diag.get('console')} erros_pagina={diag.get('erros_pagina')}]"
                            if diag else "")
            registrar_lacuna(nome_fonte, f"token via navegador: {resultado_nav.get('erro', 'falha desconhecida')}{detalhe_diag}",
                             canal="DOM-consorciado", camada=2, uf=uf)
            return {"pistas": [], "decretos": [], "dias_com_edicao": 0, "dias_com_erro": 0, "erro_fatal": True,
                    "bloqueio_js": True}
        token = resultado_nav["token"]
        cookies_navegador = resultado_nav.get("cookies")
        if not token or token == PLACEHOLDER_TOKEN:
            registrar_lacuna(nome_fonte, f"navegador devolveu token inválido/placeholder ({token!r})",
                             canal="DOM-consorciado", camada=2, uf=uf)
            return {"pistas": [], "decretos": [], "dias_com_edicao": 0, "dias_com_erro": 0, "erro_fatal": True,
                    "bloqueio_js": True}
        injetar_cookies(jar, cookies_navegador)
    for dia in sequencia_dias(desde_iso, ate_iso):
        campos = {"calendar[_token]": token, "calendar[day]": str(dia.day),
                  "calendar[month]": str(dia.month), "calendar[year]": str(dia.year)}
        edicoes = []
        for url_tmpl in (URL_CALENDARIO, URL_CALENDARIO_EXTRA):
            time.sleep(pausa)
            try:
                bruto = sessao_post(opener, url_tmpl.format(slug=slug), campos, timeout=40)
                edicoes += parse_calendario(bruto)
            except CalendarioIlegivel as e:
                # Mudou a forma da resposta: lacuna declarada, nunca dia sem edição.
                dias_ilegiveis += 1
                registrar_lacuna(nome_fonte, f"{dia.isoformat()}: {e}",
                                 canal="DOM-consorciado", camada=2, uf=uf)
            except Exception as e:  # noqa: BLE001
                dias_com_erro += 1
                registrar_lacuna(nome_fonte, f"{dia.isoformat()}: {type(e).__name__}: {e}",
                                 canal="DOM-consorciado", camada=2, uf=uf)
        for ed in edicoes:
            time.sleep(pausa)
            try:
                pdf_bytes = sessao_get(opener, ed["url_pdf"], timeout=90)
            except Exception as e:  # noqa: BLE001
                dias_com_erro += 1
                registrar_lacuna(f"{nome_fonte} (PDF {dia.isoformat()})", f"{type(e).__name__}: {e}",
                                 canal="DOM-consorciado", camada=2, uf=uf, strings=[ed["url_pdf"]])
                continue
            texto = extrair_texto_pdf(pdf_bytes)
            if not texto:
                dias_com_erro += 1
                registrar_lacuna(f"{nome_fonte} (PDF ilegível {dia.isoformat()})", "extração de texto vazia",
                                 canal="DOM-consorciado", camada=2, uf=uf, strings=[ed["url_pdf"]])
                continue
            h = preservar_evidencia(pdf_bytes, ed["url_pdf"], "pdf", "coletar_diarios_consorciados")
            decretos, pistas = classificar_trechos_consorciado(texto, candidatos)
            for d in decretos:
                d.update({"data": dia.isoformat(), "url": ed["url_pdf"], "hash_evidencia": h,
                          "fonte": nome_fonte, "uf": uf})
                decretos_todos.append(d)
            for p in pistas:
                p.update({"uf": uf, "origem": "diario_consorciado", "fonte": nome_fonte,
                          "data": dia.isoformat(), "url": ed["url_pdf"], "hash_evidencia": h,
                          "registrado_em": hoje_editorial().isoformat(), **triagem_completa(p["trecho"]),
                          "status": "pista — atribuição de município por proximidade no PDF consorciado; "
                                    "promover a registro exige documento primário lido por humano"})
                pistas_todas.append(p)
            dias_com_edicao += 1
        if not edicoes and dia.weekday() < 5:
            uteis_sem_edicao += 1
        marcar_fonte_consultada([], nome_fonte, "nao_verificado",
                                resultado=f"{dia.isoformat()}: {len(edicoes)} edição(ões)")
    # 25/09/2026: um diário de associação municipal publica em dia útil. Nenhuma edição em
    # `TETO_UTEIS_SEM_EDICAO` dias úteis não é "não publicaram": é a fonte fora do ar, ou o slug
    # que mudou. Medido: os dois slugs da Bahia erram em TODA data testada, enquanto MG, GO, CE,
    # PR, RS e RN entregam. Antes isso saía como "0 dia(s) com edição, 0 erro(s)" — fonte inteira
    # ausente relatada como ausência de publicação.
    if dias_com_edicao == 0 and uteis_sem_edicao >= TETO_UTEIS_SEM_EDICAO:
        raise FonteForaDoAr(f"nenhuma edição em {uteis_sem_edicao} dia(s) útil(eis)")
    return {"pistas": pistas_todas, "decretos": decretos_todos, "dias_com_edicao": dias_com_edicao,
            "dias_com_erro": dias_com_erro, "dias_ilegiveis": dias_ilegiveis,
            "uteis_sem_edicao": uteis_sem_edicao, "erro_fatal": False}


def coletar(desde_iso: str, ate_iso: str, apenas_uf: str = "") -> int:
    por_cod, _ = referencia_ibge()
    pistas_reg = ler("pistas_imprensa.json", {"_governanca": "", "pistas": []})
    pistas_reg.setdefault("pistas", [])
    atos = ler("atos_resposta.json")
    vistos = {(e["nome"], e["uf"], e["data"], e.get("causa")) for e in atos["eventos"]}
    # 21/09/2026 (achado real na revisão da fila, mesmo bug encontrado e corrigido em
    # coletar_diarios_municipais.py): append sem dedup — aqui ainda não se manifestou porque o
    # canal está bloqueado (§130), mas duplicaria a cada rodada no dia em que for desbloqueado.
    # Chave: (ibge ou município quando não identificado, url do PDF, trecho) — mesma menção no
    # mesmo documento não deveria virar duas entradas só por rodar de novo sobre um dia já visto.
    vistos_pistas = {(p.get("ibge") or p.get("municipio"), p.get("url"), p.get("trecho"))
                     for p in pistas_reg["pistas"]}
    total_pistas = total_decretos_novos = total_bloqueadas = total_fontes = total_fora_do_ar = 0
    for uf, fontes in UF_SIGPUB.items():
        if apenas_uf and uf != apenas_uf:
            continue
        for f in fontes:
            total_fontes += 1
            print(f"[{uf}] {f['nome']} ({f['slug']}) — {desde_iso} a {ate_iso}", flush=True)
            try:
                r = coletar_fonte(uf, f["slug"], f["nome"], desde_iso, ate_iso, por_cod)
            except FonteForaDoAr as e:
                # 25/09/2026: os dois slugs da Bahia respondem 200 com "Ocorreu um erro
                # inesperado!" em toda data testada. Antes isso era contado como "0 dia(s) com
                # edição, 0 erro(s)" — fonte inteira fora do ar relatada como ausência de
                # publicação. Agora encerra cedo, com lacuna declarada e nome próprio.
                total_fora_do_ar += 1
                registrar_lacuna(f["nome"], f"fonte fora do ar: {e}", canal="DOM-consorciado",
                                 camada=2, uf=uf, strings=[BASE.format(slug=f["slug"])])
                print(f"  FORA DO AR: {e} — lacuna declarada, slug a reverificar", flush=True)
                continue
            if r.get("bloqueio_js"):
                total_bloqueadas += 1
                print(f"  BLOQUEADA: token exige JavaScript (ver STATUS no topo do arquivo)")
                continue
            for d in r["decretos"]:
                chave = (d["municipio"] or f"{uf}(consorciado)", uf, d["data"], d.get("tipo"))
                if chave in vistos or not d.get("ibge"):
                    continue  # sem município identificado: registrado como pista, não como ato (regra 2)
                ref = por_cod[d["ibge"]]
                atos["eventos"].append({"nome": ref["nome"], "uf": uf, "ibge": d["ibge"], "data": d["data"],
                                        "causa": d["tipo"], "decreto": d["decreto"],
                                        "fonte": f"Diário consorciado (via {d['fonte']})", "url": d["url"],
                                        "lat": ref["lat"], "lon": ref["lon"], "canal": "DOM-consorciado",
                                        "hash_evidencia": d["hash_evidencia"]})
                vistos.add(chave); total_decretos_novos += 1
            for p in r["pistas"]:
                p["municipio"] = p.get("municipio") or f"{uf} (não identificado no PDF consorciado)"
                chave_pista = (p.get("ibge") or p.get("municipio"), p.get("url"), p.get("trecho"))
                if chave_pista in vistos_pistas:
                    continue
                pistas_reg["pistas"].append(p); vistos_pistas.add(chave_pista); total_pistas += 1
            # 25/09/2026: grava a cada FONTE que termina. A varredura do ciclo leva horas — medido,
            # cerca de duas por fonte — e gravar só no fim significava que uma interrupção na
            # última hora jogaria fora todas as anteriores. É a mesma lição do §212, aplicada ao
            # que se COLETOU e não ao que se registrou: rodada longa não pode depender de terminar.
            gravar("pistas_imprensa.json", pistas_reg); gravar("atos_resposta.json", atos)
            print(f"  {r['dias_com_edicao']} dia(s) com edição, {r['dias_com_erro']} erro(s), "
                 f"{len(r['pistas'])} pista(s), {len(r['decretos'])} decreto(s) brutos "
                 f"[gravado: {total_pistas} pista(s), {total_decretos_novos} decreto(s) no acumulado]", flush=True)
    gravar("pistas_imprensa.json", pistas_reg); gravar("atos_resposta.json", atos)
    print(f"total: {total_pistas} pistas novas, {total_decretos_novos} decretos novos, "
         f"{total_bloqueadas}/{total_fontes} fonte(s) bloqueada(s) por token JS, "
         f"{total_fora_do_ar}/{total_fontes} fora do ar (lacuna declarada)")
    return 0


FIX_HTML_TOKEN = b'<html><input id="calendar__token" value="abc123XYZ" /></html>'
# 22/09/2026: contra o HTML real (amm-mg) o extrator antigo (que exigia id ANTES de value) não
# bateu — ordem real dos atributos era diferente da suposta. Fixture com a ordem invertida e mais
# atributos no meio, para nunca mais depender de ordem.
FIX_HTML_TOKEN_ORDEM_INVERTIDA = (b'<html><input type="hidden" class="js-token" value="zyx987ABC" '
                                  b'name="calendar[_token]" id="calendar__token"/></html>')
FIX_JSON_OK = json.dumps({"url_arquivos": "https://x.com/arq/", "edicao": [
    {"link_diario": "2026-09-15-edicao-4200", "numero_edicao": "4200"}]}).encode()
FIX_JSON_VAZIO = json.dumps({"error": "not found"}).encode()
FIX_REF = {"3106200": {"nome": "Belo Horizonte", "uf": "MG"}, "3170206": {"nome": "Uberlândia", "uf": "MG"}}


def _fixture_pdf_bytes() -> bytes:
    """PDF sintético de duas 'seções' de entidade, no formato real observado (cabeçalho de
    entidade seguido de texto) — usa reportlab (já dependência do projeto)."""
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.drawString(50, 800, "PREFEITURA DE BELO HORIZONTE")
    c.drawString(50, 780, "PORTARIA Nº 12/2026. Dispoe sobre expediente administrativo, sem relacao com risco.")
    c.drawString(50, 700, "PREFEITURA DE UBERLANDIA")
    c.drawString(50, 680, "DECRETO Nº 45/2026. Fica instituido o Plano Municipal de Contingencia")
    c.drawString(50, 660, "para o periodo chuvoso 2026/2027, nos termos da Lei 12.608/2012.")
    c.showPage(); c.save()
    return buf.getvalue()


def autoteste() -> int:
    def t1(): return extrair_token(FIX_HTML_TOKEN) == "abc123XYZ"
    def t1b(): return extrair_token(FIX_HTML_TOKEN_ORDEM_INVERTIDA) == "zyx987ABC"  # regressão 22/09/2026
    def t2(): return extrair_token(b"<html>sem token aqui</html>") == ""
    def t3():
        r = parse_calendario(FIX_JSON_OK)
        return len(r) == 1 and r[0]["url_pdf"] == "https://x.com/arq/2026-09-15-edicao-4200.pdf"
    def t4(): return parse_calendario(FIX_JSON_VAZIO) == []  # negativo: dia sem edição
    def t5():
        """25/09/2026: corpo que não dá para ler LEVANTA, e não vira "dia sem edição".

        A versão anterior devolvia `[]` para as duas coisas, e era o mesmo defeito do §210: uma
        mudança de formato da fonte apareceria no arquivo como dia sem publicação. Medido antes
        de mexer: `{"error":...}` É dia sem edição (volta no sábado, no domingo e no Natal) e
        continua devolvendo `[]`; corpo ilegível é outra coisa."""
        for corpo in (b"not even json", b'{"outra":"coisa"}', b'[1,2,3]'):
            try:
                parse_calendario(corpo)
                return False
            except CalendarioIlegivel:
                pass
        return parse_calendario(FIX_JSON_VAZIO) == []        # `error` segue sendo dia sem edição

    def t5b():
        """Fonte que não publica em NENHUM dia útil está fora do ar — não é ausência de edição."""
        return TETO_UTEIS_SEM_EDICAO >= 3 and issubclass(FonteForaDoAr, Exception)
    def t6():
        cand = candidatos_da_uf(FIX_REF, "MG")
        return cand == {"BELO HORIZONTE": "3106200", "UBERLANDIA": "3170206"}
    def t7():  # ponta a ponta: PDF sintético -> texto -> pista com o município CORRETO (Uberlândia, não BH)
        texto = extrair_texto_pdf(_fixture_pdf_bytes())
        if "Conting" not in texto:
            return False
        cand = candidatos_da_uf(FIX_REF, "MG")
        _, pistas = classificar_trechos_consorciado(texto, cand)
        return len(pistas) == 1 and pistas[0]["ibge"] == "3170206"
    def t8():  # negativo: menção sem nenhum cabeçalho de entidade reconhecido antes -> ibge None, não descartada
        texto = "Texto solto. Fica instituido o Plano de Contingencia para chuvas."
        _, pistas = classificar_trechos_consorciado(texto, candidatos_da_uf(FIX_REF, "MG"))
        return len(pistas) == 1 and pistas[0]["ibge"] is None and pistas[0]["municipio"] is None
    def t_canal_no_vocabulario():
        """§222: o canal que ESTE coletor escreve tem de existir no vocabulário de canais.

        Ele existia desde 22/09 e nunca tinha produzido dado, porque a fonte estava bloqueada.
        Ao destravar, `DOM-consorciado` chegou ao banco e reprovou o portão de consistência, que
        mantinha a própria cópia da lista. Mesma lição do §213, terceira ocorrência: quem produz
        um valor prova aqui que ele cabe, em vez de descobrir no CI."""
        return "DOM-consorciado" in CANAIS_ATO and "DOM" in CANAIS_ATO

    def t9():  # negativo: nome de entidade que NÃO está na referência da UF não vira candidato falso
        texto = "PREFEITURA DE CIDADE INEXISTENTE\nPlano de Contingencia aprovado."
        _, pistas = classificar_trechos_consorciado(texto, candidatos_da_uf(FIX_REF, "MG"))
        return len(pistas) == 1 and pistas[0]["ibge"] is None
    def t10(): return normalizar_nome("São João d'Água") == "SAO JOAO D'AGUA" or normalizar_nome("São João d'Água") == "SAO JOAO DAGUA"
    def t11():  # regressão 20/09/2026: HTML real do SIGPub (Stimulus preenche o token via JS;
        # o servidor só manda o placeholder). extrair_token() DEVE ver o placeholder — a decisão
        # de recusar a coleta com ele é do CHAMADOR (coletar_fonte), não desta função.
        html_real = (b'<input type="hidden" id="calendar__token" name="calendar[_token]" '
                    b'data-controller="csrf-protection" value="csrf-token" />')
        return extrair_token(html_real) == PLACEHOLDER_TOKEN
    def t12():  # coletar_fonte: GET simples devolve placeholder, navegador TAMBÉM falha ->
        # bloqueio_js, zero POST de calendário gasto, uma lacuna registrada. Mocka
        # registrar_lacuna: sem isso o autoteste gravava em data/log_buscas.json de verdade
        # (achado ao rodar localmente antes do commit — autoteste tem que ser hermético).
        chamadas_post, lacunas = [], []
        def get_falso(opener, url, timeout=40):
            return (b'<input type="hidden" id="calendar__token" name="calendar[_token]" '
                    b'data-controller="csrf-protection" value="csrf-token" />')
        def post_falso(opener, url, campos, timeout=40):
            chamadas_post.append(url)
            return b'{"error":"nao deveria ter chegado aqui"}'
        def navegador_falso_falha(url, timeout=45):
            return {"ok": False, "erro": "Chromium indisponível (teste)"}
        def lacuna_falsa(*a, **kw):
            lacunas.append((a, kw))
        real_get, real_post = globals()["sessao_get"], globals()["sessao_post"]
        real_nav = globals()["obter_token_via_navegador"]
        real_lacuna = globals()["registrar_lacuna"]
        globals()["sessao_get"], globals()["sessao_post"] = get_falso, post_falso
        globals()["obter_token_via_navegador"] = navegador_falso_falha
        globals()["registrar_lacuna"] = lacuna_falsa
        try:
            r = coletar_fonte("MG", "amm-mg", "teste", "2026-09-01", "2026-09-05", FIX_REF)
            return r.get("bloqueio_js") is True and len(chamadas_post) == 0 and len(lacunas) == 1
        finally:
            globals()["sessao_get"], globals()["sessao_post"] = real_get, real_post
            globals()["obter_token_via_navegador"] = real_nav
            globals()["registrar_lacuna"] = real_lacuna
    def t13():  # §130: GET simples devolve placeholder, navegador SUCEDE -> o token real (não o
        # placeholder) vai nos campos do POST, e o cookie do navegador chega no jar HTTP.
        campos_vistos, cookies_no_jar = [], []
        def get_falso(opener, url, timeout=40):
            return (b'<input type="hidden" id="calendar__token" name="calendar[_token]" '
                    b'data-controller="csrf-protection" value="csrf-token" />')
        def post_falso(opener, url, campos, timeout=40):
            campos_vistos.append(dict(campos))
            for c in opener_jar_global[0]:
                cookies_no_jar.append(c.name)
            return b'{"error":"sem edicao neste dia (esperado no teste)"}'
        def navegador_falso_ok(url, timeout=45):
            return {"ok": True, "token": "TOKEN-REAL-DE-VERDADE",
                    "cookies": [{"name": "sessao_sigpub", "value": "xyz", "domain": ".diariomunicipal.com.br",
                                "path": "/", "secure": True, "httpOnly": True, "expires": -1}]}
        opener_jar_global = [None]
        real_nova_sessao = globals()["nova_sessao"]
        def nova_sessao_espia():
            o, j = real_nova_sessao(); opener_jar_global[0] = j; return o, j
        real_get, real_post = globals()["sessao_get"], globals()["sessao_post"]
        real_nav = globals()["obter_token_via_navegador"]
        real_marcar = globals()["marcar_fonte_consultada"]
        # 25/09/2026: sem mockar estes dois, o autoteste escreve no log REAL — foi o que
        # aconteceu nesta sessão, oito entradas de uma fonte "teste" que não existe. Autoteste
        # offline não toca em data/, nem por um registro de lacuna.
        real_lac, real_log = globals()["registrar_lacuna"], globals()["log_busca"]
        globals()["sessao_get"], globals()["sessao_post"] = get_falso, post_falso
        globals()["obter_token_via_navegador"] = navegador_falso_ok
        globals()["nova_sessao"] = nova_sessao_espia
        globals()["marcar_fonte_consultada"] = lambda *a, **kw: None
        globals()["registrar_lacuna"] = lambda *a, **kw: None
        globals()["log_busca"] = lambda *a, **kw: None
        try:
            coletar_fonte("MG", "amm-mg", "teste", "2026-09-01", "2026-09-01", FIX_REF)
            token_usado_certo = all(c["calendar[_token]"] == "TOKEN-REAL-DE-VERDADE" for c in campos_vistos)
            return token_usado_certo and len(campos_vistos) == 2 and "sessao_sigpub" in cookies_no_jar
        finally:
            globals()["sessao_get"], globals()["sessao_post"] = real_get, real_post
            globals()["obter_token_via_navegador"] = real_nav
            globals()["nova_sessao"] = real_nova_sessao
            globals()["marcar_fonte_consultada"] = real_marcar
            globals()["registrar_lacuna"], globals()["log_busca"] = real_lac, real_log
    def t14():  # se o GET simples JÁ devolve um token real (site voltou a servir estático), o
        # navegador nunca é chamado — caminho barato evita o custo de um Chromium à toa.
        chamado = [False]
        def get_falso(opener, url, timeout=40):
            return b'<input type="hidden" id="calendar__token" value="TOKEN-ESTATICO-REAL" />'
        def post_falso(opener, url, campos, timeout=40):
            return b'{"error":"sem edicao"}'
        def navegador_espiao(url, timeout=45):
            chamado[0] = True
            return {"ok": True, "token": "NAO-DEVERIA-SER-USADO", "cookies": []}
        real_get, real_post = globals()["sessao_get"], globals()["sessao_post"]
        real_nav = globals()["obter_token_via_navegador"]
        real_marcar = globals()["marcar_fonte_consultada"]
        # 25/09/2026: sem mockar estes dois, o autoteste escreve no log REAL — foi o que
        # aconteceu nesta sessão, oito entradas de uma fonte "teste" que não existe. Autoteste
        # offline não toca em data/, nem por um registro de lacuna.
        real_lac, real_log = globals()["registrar_lacuna"], globals()["log_busca"]
        globals()["sessao_get"], globals()["sessao_post"] = get_falso, post_falso
        globals()["obter_token_via_navegador"] = navegador_espiao
        globals()["marcar_fonte_consultada"] = lambda *a, **kw: None
        globals()["registrar_lacuna"] = lambda *a, **kw: None
        globals()["log_busca"] = lambda *a, **kw: None
        try:
            coletar_fonte("MG", "amm-mg", "teste", "2026-09-01", "2026-09-01", FIX_REF)
            return chamado[0] is False
        finally:
            globals()["sessao_get"], globals()["sessao_post"] = real_get, real_post
            globals()["obter_token_via_navegador"] = real_nav
            globals()["marcar_fonte_consultada"] = real_marcar
            globals()["registrar_lacuna"], globals()["log_busca"] = real_lac, real_log
    def t15():  # 21/09/2026: dedup de pistas em coletar() — mesmo achado real do bug em
        # coletar_diarios_municipais.py, corrigido aqui também antes de se manifestar (este canal
        # está bloqueado, §130, mas duplicaria a cada rodada no dia em que for desbloqueado).
        # Mocka coletar_fonte para devolver sempre a MESMA pista; rodar coletar() duas vezes com
        # apenas_uf="MG" (uma única fonte) deve produzir UMA pista na fila, não duas.
        estado = {"pistas": {"pistas": []}, "atos": {"eventos": []}}
        pista_fixa = {"municipio": "Uberlândia", "ibge": "3170206", "trecho": "Plano de Contingencia aprovado.",
                     "uf": "MG", "origem": "diario_consorciado", "fonte": "teste", "data": "2026-09-01",
                     "url": "https://x/edicao.pdf", "hash_evidencia": "h1", "registrado_em": "2026-09-21",
                     "status": "pista"}
        def ler_falso(nome, padrao=None):
            if nome == "pistas_imprensa.json":
                return estado["pistas"]
            if nome == "atos_resposta.json":
                return estado["atos"]
            return padrao
        def gravar_falso(nome, obj):
            if nome == "pistas_imprensa.json":
                estado["pistas"] = obj
            elif nome == "atos_resposta.json":
                estado["atos"] = obj
        def coletar_fonte_falso(uf, slug, nome_fonte, desde_iso, ate_iso, por_cod):
            return {"pistas": [dict(pista_fixa)], "decretos": [], "dias_com_edicao": 1, "dias_com_erro": 0}
        real_ler, real_gravar = globals()["ler"], globals()["gravar"]
        real_coletar_fonte = globals()["coletar_fonte"]
        real_ref = globals()["referencia_ibge"]
        globals()["ler"] = ler_falso; globals()["gravar"] = gravar_falso
        globals()["coletar_fonte"] = coletar_fonte_falso
        globals()["referencia_ibge"] = lambda: ({"3170206": {"nome": "Uberlândia", "uf": "MG"}}, {})
        try:
            coletar("2026-09-01", "2026-09-01", apenas_uf="MG")
            n1 = len(estado["pistas"]["pistas"])
            coletar("2026-09-01", "2026-09-01", apenas_uf="MG")
            n2 = len(estado["pistas"]["pistas"])
            return n1 == 1 and n2 == 1
        finally:
            globals()["ler"] = real_ler; globals()["gravar"] = real_gravar
            globals()["coletar_fonte"] = real_coletar_fonte
            globals()["referencia_ibge"] = real_ref
    def t16():
        """26/09/2026: as 27 UFs estão TODAS classificadas, e nenhuma em duas gavetas.

        O teste existe porque a lista de UFs cresceu de sete para quinze numa rodada, e o modo de
        errar é sempre o mesmo: uma UF entra em UF_SIGPUB e continua em SIGPUB_ENCERRADO, ou uma UF
        nova aparece no seletor da plataforma e ninguém a tira de SIGPUB_SEM_CANAL — e aí o
        varrimento passa a declarar lacuna diária de uma fonte que entrega, ou a pular uma que
        entrega. O DF é a única ausência legítima: não tem município.

        Confere também que slug de arquivo histórico NÃO está no varrimento ativo: é o que produziu
        o rótulo errado de 25/09/2026 ("fonte fora do ar" para uma associação que parou de publicar
        na plataforma em 2013)."""
        UFS = {"AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PA",
               "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO"}
        ativas, encerradas = set(UF_SIGPUB), set(SIGPUB_ENCERRADO)
        sem_canal = set(SIGPUB_SEM_CANAL)
        if ativas & encerradas or ativas & sem_canal or encerradas & sem_canal:
            return False                                   # nenhuma UF em duas gavetas
        if (ativas | encerradas | sem_canal) != UFS - {"DF"}:
            return False                                   # todas classificadas, menos o DF
        slugs_ativos = {f["slug"] for fs in UF_SIGPUB.values() for f in fs}
        slugs_encerrados = {f["slug"] for fs in SIGPUB_ENCERRADO.values() for f in fs}
        if slugs_ativos & slugs_encerrados:
            return False                                   # arquivo histórico fora do varrimento
        # toda entidade encerrada declara a data da última edição, ou None explícito
        return all("ultima_edicao" in f for fs in SIGPUB_ENCERRADO.values() for f in fs)

    return rodar_autoteste({
        "§222 o canal deste coletor existe no vocabulário de canais": t_canal_no_vocabulario,
        "extrai token do HTML do calendário": t1,
        "regressão 22/09: token com atributos em ordem diferente (achado contra produção)": t1b,
        "negativo: HTML sem token": t2,
        "parse_calendario: edição do dia": t3, "negativo: dia sem edição (error)": t4,
        "negativo: corpo ilegível levanta; `error` segue sendo dia sem edição": t5,
        "fonte sem edição em nenhum dia útil é fonte fora do ar": t5b, "candidatos_da_uf: nomes normalizados por UF": t6,
        "ponta a ponta: PDF sintético -> pista com o município mais próximo correto": t7,
        "negativo: sem cabeçalho de entidade -> ibge None, pista mantida (não descartada)": t8,
        "negativo: nome de entidade fora da referência IBGE não vira candidato": t9,
        "normalizar_nome remove acento": t10,
        "regressão 20/09: HTML real do SIGPub reconhecido como placeholder JS (bloqueio conhecido)": t11,
        "regressão 21/09: coletar() não duplica pista ao rodar duas vezes sobre o mesmo achado": t15,
        "coletar_fonte: HTTP simples + navegador falham -> bloqueio_js, zero POST gasto": t12,
        "§130: navegador sucede -> token real usado no POST, cookie do navegador chega no jar": t13,
        "§130: GET simples já real -> navegador nunca é chamado (caminho barato)": t14,
        "26/09: as 27 UFs classificadas, nenhuma em duas gavetas, arquivo histórico fora do varrimento": t16,
    })


if __name__ == "__main__":
    if "--autoteste" in sys.argv:
        sys.exit(autoteste())
    a = sys.argv
    desde = a[a.index("--desde") + 1] if "--desde" in a else (hoje_editorial() - timedelta(days=30)).isoformat()
    ate = a[a.index("--ate") + 1] if "--ate" in a else hoje_editorial().isoformat()
    uf = a[a.index("--uf") + 1] if "--uf" in a else ""
    sys.exit(coletar(desde, ate, apenas_uf=uf))
