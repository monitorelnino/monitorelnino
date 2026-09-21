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

FONTES REGISTRADAS (só verificadas por navegação real em 20-22/09/2026; nenhum slug
foi suposto): ver `UF_SIGPUB` abaixo. Estados fora desta lista NÃO são inventados
aqui — a plataforma provavelmente cobre a maioria dos 27 (o seletor da página
inicial lista todos), mas descobrir o slug de cada um exige abrir o site e ler o
link real, tarefa ainda não feita para os estados ausentes daqui. Adicionar um
estado = adicionar uma linha a UF_SIGPUB, nunca adivinhar um slug pelo padrão dos
outros (ex.: PI quase certamente NÃO é `/pi/`; teria de ser verificado).

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
                            marcar_fonte_consultada, referencia_ibge, ler, gravar, rodar_autoteste)
from classificar_pista_civil import triagem_completa

# Só slugs confirmados por navegação/fetch reais nesta sessão (20-22/09/2026). AL fica de
# fora de propósito: já é o único estado com raspador SIGPub no próprio QD (94,1% de
# cobertura) — o ganho marginal aqui é baixo comparado às UFs abaixo, hoje entre 0% e 2,5%.
UF_SIGPUB = {
    "MG": [{"slug": "amm-mg", "nome": "Diário Oficial dos Municípios Mineiros (AMM-MG)"}],
    "GO": [{"slug": "agm", "nome": "Diário Oficial dos Municípios de Goiás (AGM)"},
           {"slug": "fgm", "nome": "Diário Oficial dos Municípios de Goiás (FGM)"}],
    "BA": [{"slug": "bahia", "nome": "Diário Oficial dos Municípios da Bahia (AMURB)"},
           {"slug": "amurc", "nome": "Diário Oficial dos Municípios do Sul/Extremo Sul/Sudoeste da Bahia (AMURC)"}],
    "CE": [{"slug": "aprece", "nome": "Diário Oficial dos Municípios do Ceará (APRECE)"}],
    "PR": [{"slug": "amp", "nome": "Diário Oficial dos Municípios do Paraná (AMP)"}],
    "RS": [{"slug": "famurs", "nome": "Diário Oficial dos Municípios do Rio Grande do Sul (FAMURS)"}],
    "RN": [{"slug": "femurn", "nome": "Diário Oficial dos Municípios do Rio Grande do Norte (FEMURN)"}],
}
BASE = "https://www.diariomunicipal.com.br/{slug}/"
URL_CALENDARIO = "https://www.diariomunicipal.com.br/{slug}/materia/calendario"
URL_CALENDARIO_EXTRA = "https://www.diariomunicipal.com.br/{slug}/materia/calendario/extra"
TERMOS_RESPOSTA = ['"situação de emergência"', '"estado de calamidade pública"']
TERMOS_PISTA = ['"plano de contingência"', '"El Niño"', '"plano de ação"']
PAD_DECRETO = re.compile(r"decreto\s+(?:municipal\s+)?n[ºo°\.]?\s*([\d\.\/-]+)[^.]{0,200}?(situa[çc][ãa]o de emerg[êe]ncia|estado de calamidade p[úu]blica)", re.I)
PAD_PLANO = re.compile(r"plano\s+(?:municipal\s+)?de\s+conting[êe]ncia[^.]{0,160}", re.I)
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


def normalizar_nome(s: str) -> str:
    """Maiúsculas sem acento, sem duplo espaço — para casar nome do PDF com a referência IBGE."""
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", s).strip().upper()


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


def parse_calendario(bruto: bytes) -> list:
    """[{link_diario, numero_edicao, url_arquivos}] ou [] se 'error' no corpo (sem edição no dia)."""
    try:
        body = json.loads(bruto.decode("utf-8", "replace"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return []
    if "error" in body or "edicao" not in body:
        return []
    base_url = body.get("url_arquivos", "")
    return [{"link_diario": e.get("link_diario", ""), "numero_edicao": e.get("numero_edicao", ""),
             "url_pdf": f"{base_url}{e.get('link_diario', '')}.pdf"} for e in body["edicao"] if e.get("link_diario")]


def extrair_texto_pdf(bruto: bytes) -> str:
    """pdfplumber primeiro (mesma ordem usada nos coletores de boletim de saúde); pypdf como reserva."""
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(bruto)) as pdf:
            texto = "\n".join((pg.extract_text() or "") for pg in pdf.pages)
        if len(texto) > 200:
            return texto
    except Exception:  # noqa: BLE001
        pass
    try:
        import pypdf
        r = pypdf.PdfReader(io.BytesIO(bruto))
        return "\n".join((p.extract_text() or "") for p in r.pages)
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
    dias_com_edicao = dias_com_erro = 0
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
                          "registrado_em": date.today().isoformat(), **triagem_completa(p["trecho"]),
                          "status": "pista — atribuição de município por proximidade no PDF consorciado; "
                                    "promover a registro exige documento primário lido por humano"})
                pistas_todas.append(p)
            dias_com_edicao += 1
        marcar_fonte_consultada([], nome_fonte, "nao_verificado",
                                resultado=f"{dia.isoformat()}: {len(edicoes)} edição(ões)")
    return {"pistas": pistas_todas, "decretos": decretos_todos, "dias_com_edicao": dias_com_edicao,
            "dias_com_erro": dias_com_erro, "erro_fatal": False}


def coletar(desde_iso: str, ate_iso: str, apenas_uf: str = "") -> int:
    por_cod, _ = referencia_ibge()
    pistas_reg = ler("pistas_imprensa.json", {"_governanca": "", "pistas": []})
    pistas_reg.setdefault("pistas", [])
    atos = ler("atos_resposta.json")
    vistos = {(e["nome"], e["uf"], e["data"], e.get("causa")) for e in atos["eventos"]}
    total_pistas = total_decretos_novos = total_bloqueadas = total_fontes = 0
    for uf, fontes in UF_SIGPUB.items():
        if apenas_uf and uf != apenas_uf:
            continue
        for f in fontes:
            total_fontes += 1
            print(f"[{uf}] {f['nome']} ({f['slug']}) — {desde_iso} a {ate_iso}", flush=True)
            r = coletar_fonte(uf, f["slug"], f["nome"], desde_iso, ate_iso, por_cod)
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
                pistas_reg["pistas"].append(p); total_pistas += 1
            print(f"  {r['dias_com_edicao']} dia(s) com edição, {r['dias_com_erro']} erro(s), "
                 f"{len(r['pistas'])} pista(s), {len(r['decretos'])} decreto(s) brutos")
    gravar("pistas_imprensa.json", pistas_reg); gravar("atos_resposta.json", atos)
    print(f"total: {total_pistas} pistas novas, {total_decretos_novos} decretos novos, "
         f"{total_bloqueadas}/{total_fontes} fonte(s) bloqueada(s) por token JS")
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
    def t5(): return parse_calendario(b"not even json") == []  # negativo: corpo inesperado nunca derruba
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
        globals()["sessao_get"], globals()["sessao_post"] = get_falso, post_falso
        globals()["obter_token_via_navegador"] = navegador_falso_ok
        globals()["nova_sessao"] = nova_sessao_espia
        globals()["marcar_fonte_consultada"] = lambda *a, **kw: None
        try:
            coletar_fonte("MG", "amm-mg", "teste", "2026-09-01", "2026-09-01", FIX_REF)
            token_usado_certo = all(c["calendar[_token]"] == "TOKEN-REAL-DE-VERDADE" for c in campos_vistos)
            return token_usado_certo and len(campos_vistos) == 2 and "sessao_sigpub" in cookies_no_jar
        finally:
            globals()["sessao_get"], globals()["sessao_post"] = real_get, real_post
            globals()["obter_token_via_navegador"] = real_nav
            globals()["nova_sessao"] = real_nova_sessao
            globals()["marcar_fonte_consultada"] = real_marcar
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
        globals()["sessao_get"], globals()["sessao_post"] = get_falso, post_falso
        globals()["obter_token_via_navegador"] = navegador_espiao
        globals()["marcar_fonte_consultada"] = lambda *a, **kw: None
        try:
            coletar_fonte("MG", "amm-mg", "teste", "2026-09-01", "2026-09-01", FIX_REF)
            return chamado[0] is False
        finally:
            globals()["sessao_get"], globals()["sessao_post"] = real_get, real_post
            globals()["obter_token_via_navegador"] = real_nav
            globals()["marcar_fonte_consultada"] = real_marcar
    return rodar_autoteste({
        "extrai token do HTML do calendário": t1,
        "regressão 22/09: token com atributos em ordem diferente (achado contra produção)": t1b,
        "negativo: HTML sem token": t2,
        "parse_calendario: edição do dia": t3, "negativo: dia sem edição (error)": t4,
        "negativo: corpo não-JSON nunca derruba": t5, "candidatos_da_uf: nomes normalizados por UF": t6,
        "ponta a ponta: PDF sintético -> pista com o município mais próximo correto": t7,
        "negativo: sem cabeçalho de entidade -> ibge None, pista mantida (não descartada)": t8,
        "negativo: nome de entidade fora da referência IBGE não vira candidato": t9,
        "normalizar_nome remove acento": t10,
        "regressão 20/09: HTML real do SIGPub reconhecido como placeholder JS (bloqueio conhecido)": t11,
        "coletar_fonte: HTTP simples + navegador falham -> bloqueio_js, zero POST gasto": t12,
        "§130: navegador sucede -> token real usado no POST, cookie do navegador chega no jar": t13,
        "§130: GET simples já real -> navegador nunca é chamado (caminho barato)": t14,
    })


if __name__ == "__main__":
    if "--autoteste" in sys.argv:
        sys.exit(autoteste())
    a = sys.argv
    desde = a[a.index("--desde") + 1] if "--desde" in a else (date.today() - timedelta(days=30)).isoformat()
    ate = a[a.index("--ate") + 1] if "--ate" in a else date.today().isoformat()
    uf = a[a.index("--uf") + 1] if "--uf" in a else ""
    sys.exit(coletar(desde, ate, apenas_uf=uf))
