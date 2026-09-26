#!/usr/bin/env python3
"""
coletores_base.py
=================
Disciplina comum dos coletores da Pista A introduzidos na v2.2.4 (documento de
redesenho de 02/09/2026, §3.8, §4): S2iD/DOU, diários oficiais estaduais,
camada declarada nacional (MUNIC/ICM) e diários municipais.

Cinco regras herdadas de `coletar_sinais_risco.py` e da transferência conceitual:
1. **Nada inventado.** Fonte fora do ar, endpoint não confirmado ou parser sem
   correspondência → lacuna declarada (`registrar_lacuna`), nunca valor estimado.
2. **Descoberta ≠ registro.** O que os coletores acham vai para atos de resposta
   (peso zero) ou para filas de pista; promover pista a registro é humano.
3. **Log estruturado v2** (§3.1): toda consulta gera entrada com data, canal,
   camada, UF/município quando couber, strings, decisão, executor e hash.
4. **Preservação de evidência** (§3.8): todo documento citado ganha cópia em
   `evidencias/<sha256>.<ext>` (ou só o hash, com tentativa de snapshot no
   Wayback, se > 5 MB) e entrada em `data/evidencias.json`.
5. **Livro de fontes consultadas** (`data/fontes_consultadas.json`): por
   município IBGE, quais fontes foram consultadas, quando e com que resultado.
   É deste livro (mais o log) que `recalcular_mare.py` deriva o nível de
   verificação — os coletores nunca escrevem `verificacao_municipal.json`.
"""
import hashlib, html, json, os, pathlib, re, ssl, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

RAIZ = pathlib.Path(__file__).parent
DATA = RAIZ / "data"
EVID = RAIZ / "evidencias"
LIMITE_EVIDENCIA = 5 * 1024 * 1024  # bytes
UA = "MonitorElNinoBrasil/2.2.4 (+https://monitorelnino.com.br; coletor da Pista A)"


def ua_de(proposito: str = "") -> str:
    """O cliente do projeto, com o PROPÓSITO desta rotina declarado entre colchetes.

    26/09/2026 (§228): uma auditoria contou **vinte e uma strings de User-Agent diferentes** no
    repositório, cada arquivo com a sua. Duas coisas erradas ao mesmo tempo. A primeira é a
    cópia que envelhece, já conhecida do §213 e do §222: mudar o endereço de contato no `UA`
    canônico não mudava nada nos outros vinte. A segunda é pior — **seis dessas strings
    começavam com `Mozilla/5.0`**, duas delas um User-Agent completo de Chrome no Windows. O
    CLAUDE.md diz, sem exceção: *nunca disfarçar o cliente*. Disfarce não fica menos disfarce
    por trazer o nome do projeto entre parênteses, e a razão de alguém escrever `Mozilla/5.0`
    é exatamente passar por filtro que recusa robô — o que é contornar recusa.

    Distinguir uma sonda de um coletor nos registros da fonte é um objetivo legítimo, e é o que
    esta função serve: MESMA identidade, propósito declarado. Quem recebe o pedido continua
    sabendo quem somos, e passa a saber também por que estamos ali.

    A política de robots (§185) depende disto: `can_fetch` é avaliado contra `UA`, e o rastro
    de `data/robots_registro.json` grava o cliente. Módulo que enviava outra string era medido
    contra a regra de um agente e registrado como outro."""
    return f"{UA} [{proposito}]" if proposito else UA
NIVEIS = ("nao_verificado", "nacional", "estadual", "municipal_completo")
EXECUTOR = "robo" if os.environ.get("GITHUB_ACTIONS") else "claude"


# Vocabulário FECHADO do canal de um ato/registro municipal. Vive aqui, e não dentro do portão,
# pela lição do §213: uma cópia do vocabulário no lugar que CONFERE envelhece quando quem PRODUZ
# inventa um valor novo. Foi o que aconteceu em 25/09/2026 com `DOM-consorciado` — o coletor de
# diários consorciados existia desde 22/09, mas estava bloqueado, e só ao destravá-lo o canal
# novo chegou ao dado e reprovou o portão de consistência.
#
# `DOM` e `DOM-consorciado` são propositalmente DISTINTOS: no primeiro o diário é do próprio
# município; no segundo é um diário de associação, onde a atribuição do município é heurística de
# proximidade no PDF. Mesma origem legal, força probatória diferente — e quem lê o dado precisa
# saber qual dos dois é.
CANAIS_ATO = ("DOM", "DOM-consorciado", "DOU", "repositorio_estadual", "orgao_estadual",
              "site_municipal", "imprensa", "\u2014")


# Fuso da REDAÇÃO. A data de uma edição é compromisso com o leitor brasileiro, e o runner do
# GitHub Actions roda em UTC: a rodada de sábado 22h40 em Brasília já é domingo em UTC, e a edição
# sairia datada de um dia que no Brasil ainda não começou.
#
# 26/09/2026 (§227): isto vivia só em `atualizar.py`, e o portão de cadência também só conferia
# `atualizar.py`. Enquanto isso o `hoje()` DESTE arquivo — o que os dezesseis coletores chamam,
# vinte e nove vezes só nos `coletar_*.py` — devolvia `date.today()`, a data do runner. A função
# certa existia, o portão existia, e a porta por onde todo mundo passava era a errada. Mesmo
# defeito de escopo do §213, do §222 e do §226: a lição aplicada num lugar só.
FUSO_EDITORIAL = ZoneInfo("America/Sao_Paulo")


def hoje_editorial(agora=None) -> date:
    """Data de hoje no fuso da redação (America/Sao_Paulo), não no do runner.

    `agora` existe para o portão poder provar o caso que importa sem esperar as 22h: um instante
    que já virou o dia em UTC mas não em Brasília. Sem o relógio injetável, um teste só pegaria a
    regressão nas três horas do dia em que os dois fusos discordam."""
    return (agora or datetime.now(FUSO_EDITORIAL)).astimezone(FUSO_EDITORIAL).date()


def hoje() -> str:
    """Data editorial em ISO. É o que vai a carimbo de arquivo, `consultado_em` e data de registro
    — tudo que o leitor lê como "quando isto foi visto"."""
    return hoje_editorial().isoformat()


def ler(nome, padrao=None):
    p = DATA / nome
    if not p.exists():
        return padrao
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _indent_de(p) -> int:
    """Reusa a indentação do arquivo existente (diffs limpos nos commits do robô)."""
    try:
        with open(p, encoding="utf-8") as f:
            f.readline(); seg = f.readline()
        n = len(seg) - len(seg.lstrip(" "))
        return n if 0 < n <= 8 else 1
    except FileNotFoundError:
        return 1


def gravar(nome, obj, compacto: bool = False):
    """Escrita ATÔMICA (achado real, 21/09/2026): a versão anterior escrevia direto no arquivo
    final — qualquer interrupção no meio (timeout, Action cancelada, OOM) deixava um JSON
    truncado e inválido. Reproduzido de verdade: coletar_declarado_nacional.py rodando sob
    `timeout 200` corrompeu data/fontes_consultadas.json (368.019 → 166.961 linhas, JSON
    inválido). Corrigido: grava num arquivo temporário no mesmo diretório e substitui via
    os.replace(), que em POSIX é atômico — o arquivo final é sempre a versão antiga completa
    ou a nova completa, nunca uma mistura truncada."""
    p = DATA / nome
    # 25/09/2026 (§221): `compacto` para o arquivo que a PÁGINA carrega inteiro. A indentação
    # existe para deixar o diff do robô legível, e vale a pena na maioria dos arquivos; nos que o
    # navegador baixa por completo ela custa 38% do peso. A decisão já tinha sido tomada uma vez,
    # para o clima municipal — só que lá o arquivo era escrito por fora desta função, e por isso
    # ficava sem a escrita atômica e sem a espera do cadeado do Windows. Agora é a mesma porta.
    tmp = p.with_name(f"{p.name}.tmp{os.getpid()}")
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        if compacto:
            json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
        else:
            json.dump(obj, f, ensure_ascii=False, indent=_indent_de(p))
        f.write("\n")
    # 24/09/2026: no Windows, os.replace() falha com PermissionError (WinError 5) quando OUTRO
    # processo tem o destino aberto — o indexador do sistema e o antivírus abrem os JSON grandes
    # de data/ sozinhos, por um instante. Derrubou o `coletar_s2id` no meio da rodada nacional,
    # em `evidencias.json`. É janela de milissegundos: espera-se e tenta-se de novo. O que NÃO se
    # faz é engolir o erro, porque falta de permissão de verdade tem de aparecer.
    for tentativa in range(6):
        try:
            os.replace(tmp, p)
            return
        except PermissionError:
            if tentativa == 5:
                try:
                    os.unlink(tmp)          # não deixa .tmp órfão ao lado do arquivo bom
                except OSError:
                    pass
                raise
            time.sleep(0.2 * (tentativa + 1))


# ---------------------------------------------------------------------------------
# Detector de página de defeso eleitoral (PR-N0 §1.5, 06/09/2026). Sítios estaduais e
# municipais que respondem com aviso de "período eleitoral" NÃO são "nada localizado":
# são fonte suspensa (defeso). O detector roda dentro de buscar(); a marcação é registrada
# em data/calendario/fontes_suspensas.json e propagada ao log_busca() da mesma URL.
# ---------------------------------------------------------------------------------
import unicodedata as _ud

PADROES_DEFESO = [
    r"periodo eleitoral", r"conduta vedada", r"legislacao eleitoral", r"lei 9\.?504", r"lei n[oº.]* ?9\.?504",
    r"conteudo temporariamente indisponivel(?=[\s\S]{0,400}(eleic|9\.?504))",   # só com contexto eleitoral: manutenção não é defeso
    r"indisponivel[^.]{0,80}eleic", r"defeso eleitoral", r"restricoes eleitorais",
    r"suspens[ao][^.]{0,80}legislacao eleitoral", r"em razao d[ao] (periodo|calendario) eleitoral", r"vedacoes eleitorais",
    r"\(defeso\)", r"edicao (de )?defeso", r"versao (de )?defeso",   # §9 (07/09/2026): painéis em "edição de defeso" (ex.: Painel das Arboviroses do MS)
]
_RE_DEFESO = [re.compile(p) for p in PADROES_DEFESO]
_SUSPENSAS_SESSAO = {}   # url → padrão que casou (nesta execução)


def _plano(t: str) -> str:
    return "".join(c for c in _ud.normalize("NFD", str(t or "").lower()) if _ud.category(c) != "Mn")


def texto_declarativo(html: str) -> str:
    """O que a página DIZ ao leitor: texto visível, mais <title> e <meta name="description">.

    §182 (23/09/2026, achado numa rodada real): a detecção de defeso rodava sobre o HTML cru, e
    casava em atributo — `alt="banner periodo eleitoral"` de uma imagem em saude.pi.gov.br marcou o
    portal inteiro como suspenso, embora a página estivesse no ar e servindo conteúdo. Título e
    descrição ficam DENTRO da régua de propósito: os avisos de defeso reais de MA e MG moram
    exatamente ali (`<title>Suspensão Temporária | Período Eleitoral 2026</title>` e
    `<meta name="description" content="em função do período eleitoral, esta página está
    indisponível…">`). Atributo de imagem, classe de CSS e endereço de link ficam fora."""
    if not html:
        return ""
    h = html[:200000]
    partes = []
    for rx in (r"<title[^>]*>(.*?)</title>",
               r"""<meta[^>]+name=["']description["'][^>]*content=["'](.*?)["']""",
               r"""<meta[^>]+content=["'](.*?)["'][^>]*name=["']description["']"""):
        partes += re.findall(rx, h, re.IGNORECASE | re.DOTALL)
    # texto visível: fora de script/style e fora de qualquer tag
    corpo = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", h)
    partes.append(re.sub(r"(?s)<[^>]+>", " ", corpo))
    return " ".join(partes)


# §182 (23/09/2026): o ESCOPO do que o sítio declara suspenso. Medido nas páginas reais de 23/09:
#   · MA  — "Suspensão Temporária | Período Eleitoral 2026" no <title>: o sítio inteiro saiu do ar;
#   · MG  — "em função do período eleitoral, esta página está indisponível": a página saiu do ar;
#   · MT  — "em cumprimento à legislação eleitoral, o governo suspende a exibição das NOTÍCIAS
#            institucionais": o que saiu do ar foi a notícia, não o documento nem o serviço;
#   · SP  — "os conteúdos desta SEÇÃO DE NOTÍCIAS ficarão indisponíveis": idem;
#   · SC  — "banner home - legislação eleitoral - full banner": só o nome de um banner.
# A distinção é material para o índice: a Lei 9.504/97 restringe PUBLICIDADE institucional, e é isso
# que os estados dizem estar suspendendo. Chamar de "fonte suspensa" um sítio que só tirou a seção de
# notícias esconderia que o plano de contingência continua servido — e transformaria uma restrição de
# propaganda em lacuna de transparência que ninguém declarou.
_MARCAS_DE_NOTICIA = ("noticia", "noticias", "publicidade institucional", "propaganda institucional",
                      "secao de noticias", "conteudo institucional", "sala de imprensa", "materias")
_MARCAS_DE_SITIO = ("esta pagina esta indisponivel", "este portal", "deste portal", "conteudo deste",
                    "suspensao temporaria", "conteudo indisponivel", "site esta indisponivel",
                    "portal encontra-se", "pagina indisponivel", "temporariamente indisponivel",
                    "conteudo temporariamente")


def classificar_defeso(texto: str) -> tuple:
    """(padrao, escopo) do que a página declara: escopo "sitio", "noticias" ou None.

    Função pura. Lê só o texto declarativo (texto visível, <title>, <meta description>) — atributo de
    imagem e classe de CSS ficam fora, porque `alt="banner periodo eleitoral"` marcou um portal
    inteiro como suspenso em 23/09/2026 com a página no ar."""
    if not texto:
        return None, None
    t = _plano(texto_declarativo(texto) if "<" in texto[:2000] else texto[:200000])
    for rx in _RE_DEFESO:
        m = rx.search(t)
        if not m:
            continue
        janela = t[max(0, m.start() - 220):m.end() + 220]
        if any(marca in janela for marca in _MARCAS_DE_NOTICIA):
            return m.group(0), "noticias"
        if any(marca in janela for marca in _MARCAS_DE_SITIO):
            return m.group(0), "sitio"
        # padrão que se basta: nomeia o defeso, não só o calendário eleitoral
        if m.group(0) in ("defeso eleitoral", "(defeso)", "restricoes eleitorais", "vedacoes eleitorais"):
            return m.group(0), "sitio"
        return m.group(0), None      # menção sem declaração de indisponibilidade: não é suspensão
    return None, None


def detectar_defeso(texto: str) -> str | None:
    """Padrão que casou (sem acento) ou None, SÓ quando o sítio declara indisponibilidade do próprio
    conteúdo (§182). Notícia institucional suspensa não fecha o canal que o Monitor usa: o documento
    continua servido, e marcar a fonte como suspensa inventaria uma lacuna."""
    padrao, escopo = classificar_defeso(texto)
    return padrao if escopo == "sitio" else None


def _dominio_publico(url: str) -> bool:
    """Sítio estadual/municipal (não API de dados): .gov.br, .leg.br, .jus.br ou domínio brasileiro de prefeitura."""
    h = (urllib.parse.urlparse(url).netloc or "").lower()
    if any(h.startswith(x) or x in h for x in ("api.", "apimsbr", "queridodiario", "dataserver", "geoserver", "gsc.cemaden", "info.dengue", "portaldatransparencia.gov.br", "repositorio.dados.gov.br", "transferegov", "s3.", "amazonaws")):
        return False
    return h.endswith((".gov.br", ".leg.br", ".jus.br", ".def.br", ".mp.br")) or "prefeitura" in h


def setor_da_url(url: str) -> str:
    """§9: setor da fonte suspensa pela URL — saude | financiamento | defesa_civil."""
    u = url.lower()
    if any(x in u for x in ("saude", "sus.gov", "arbovir", "dengue", "vigil", "epidem")): return "saude"
    if any(x in u for x in ("transparencia", "transferegov", "tesouro", "orcament")): return "financiamento"
    return "defesa_civil"


def registrar_fonte_suspensa(url: str, corpo: bytes, padrao: str) -> None:
    """Grava a detecção (hash + 500 primeiras letras) e a contagem por UF em data/calendario/fontes_suspensas.json."""
    import datetime as _dt
    h = hashlib.sha256(corpo).hexdigest()
    (DATA / "calendario").mkdir(parents=True, exist_ok=True)
    p = DATA / "calendario" / "fontes_suspensas.json"
    d = json.load(open(p, encoding="utf-8")) if p.exists() else {"_governanca": "Fontes oficiais que responderam com página de período eleitoral (detector de PR-N0 §1.5). Nunca 'nada localizado': fonte suspensa (defeso). A reabertura é o flag voltando a false, com data.", "fontes": {}}
    hoje = _dt.date.today().isoformat()
    f = d["fontes"].setdefault(url, {"primeira_deteccao": hoje, "ultima_deteccao": hoje, "padrao": padrao, "hash": h, "amostra": corpo[:2000].decode("utf-8", "replace")[:500], "suspensa": True, "setor": setor_da_url(url)})
    f.update({"ultima_deteccao": hoje, "padrao": padrao, "hash": h, "suspensa": True, "setor": f.get("setor") or setor_da_url(url)})
    json.dump(d, open(p, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1); open(p, "a", newline="\n").write("\n")
    (EVID).mkdir(parents=True, exist_ok=True)
    (EVID / f"defeso_{h[:16]}.txt").write_text(corpo[:20000].decode("utf-8", "replace"), encoding="utf-8", newline="\n")


def url_ascii(url: str) -> str:
    """IRI → URI (RFC 3987 §3.1): codifica em percent-encoding os caracteres fora do ASCII que
    sobraram no endereço, preservando os escapes já existentes. Achado de 08/09/2026: 69 URLs do
    repositório estadual do ES trazem "Contingência" com o "ê" cru no caminho; http.client só
    envia ASCII e levantava UnicodeEncodeError — a falha era do nosso cliente, não do sítio."""
    return urllib.parse.quote(url, safe=":/?&=%#+~@!$,;'()*[]")


def redigir_dados_pessoais(texto: str) -> tuple:
    """12/09/2026 (achado de auditoria): edições inteiras de Diário Oficial preservadas por
    coletar_diarios_municipais.py às vezes trazem, na mesma edição do plano de contingência que
    motivou a busca, atos completamente não relacionados — despachos tributários, decisões de
    pessoal — citando CPF de terceiros (contribuintes, servidores) que nada têm a ver com o objeto
    do Monitor. A fonte original (o Diário Oficial do município) já é pública por lei; mas
    preservar e publicar o texto INTEIRO, pesquisável e indexado no domínio do projeto, quando só
    o trecho do plano de contingência interessa, viola o princípio de minimização de dados da LGPD
    (art. 6º, III) — facilita achar o que na fonte original exigiria vasculhar a edição inteira.

    Redige (não extrai seletivamente: extrair só o trecho relevante é um problema de NLP separado,
    arriscado de acertar sem falsos negativos) o padrão de CPF (NNN.NNN.NNN-NN) por [CPF REDIGIDO].
    Devolve (texto_redigido, quantidade_redigida) — a contagem vai ao log, para nunca esconder que
    a redação aconteceu."""
    padrao = re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}")
    n = len(padrao.findall(texto))
    return padrao.sub("[CPF REDIGIDO]", texto), n


# ---------------------------------------------------------------------------------
# robots.txt: leitura, ritmo e rastro (§185, 23/09/2026 — decisão da editoria).
#
# O QUE O ARQUIVO É. A RFC 9309 diz, em letra de forma: as regras do robots.txt "não são uma forma
# de autorização de acesso" (§ 1.3) e o protocolo "não substitui medidas válidas de segurança"
# (§ 3). É um PEDIDO publicado pelo sítio. No direito brasileiro não há norma nem precedente que o
# torne vinculante; o que é crime (CP, art. 154-A) exige "violação indevida de mecanismo de
# segurança", que o robots.txt não é; ato oficial não tem proteção autoral (Lei 9.610/98, art. 8º,
# IV); e a LAI (art. 8º, § 3º, III) obriga o órgão a possibilitar acesso automatizado ao que publica.
# O Querido Diário, de onde este projeto lê os diários, roda com ROBOTSTXT_OBEY = False e cliente
# identificado. A METODOLOGIA fixou em 10/09/2026 que bloqueio a robô não é evidência de
# indisponibilidade ao cidadão.
#
# O QUE O MONITOR FAZ, então, por decisão da editoria em 23/09/2026:
#   1. LÊ o robots.txt de cada sítio antes do primeiro acesso, e guarda o que ele declara;
#   2. RESPEITA o Crawl-delay pedido (o de defesacivil.mt.gov.br é 30 s) — o pedido de ritmo é
#      barato de honrar e é a parte do robots que protege o servidor de verdade;
#   3. ACESSA documento público mesmo onde o robots pede que robôs não entrem — com o cliente
#      IDENTIFICADO (coletores_base.UA), nunca disfarçado de navegador ou de Googlebot;
#   4. DEIXA RASTRO: todo acesso feito contra o que o robots pediu fica em
#      data/robots_registro.json, com URL, data e origem, publicado como o resto de data/.
#
# O QUE NÃO MUDA: 401, 403, 429 e 451 continuam sendo recusa que se respeita (§170); captcha e
# login não se contornam; dado pessoal segue fora (LGPD, art. 6º, III). robots.txt é pedido;
# aquilo é tranca.
import urllib.robotparser as _robotparser

ROBOTS_REGISTRO = "robots_registro.json"
CRAWL_DELAY_MAXIMO = 60.0            # pedido acima disso vira 60 s: honra o ritmo sem travar a rodada
_ROBOTS_CACHE = {}                    # host -> {"status", "crawl_delay", "rp"}
_ULTIMO_ACESSO = {}                   # host -> time.time() do último pedido


def _ler_robots_bruto(host: str, timeout: int = 15):
    """(status_http, texto) do robots.txt, sem passar por buscar() — evita recursão e defeso."""
    req = urllib.request.Request(f"https://{host}/robots.txt", headers={"User-Agent": UA, "Accept": "text/plain,*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(200000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception:  # noqa: BLE001 — DNS, TLS, timeout: indeterminado
        return None, ""


def robots_de(host: str, ler_fn=_ler_robots_bruto) -> dict:
    """O que o sítio declara em robots.txt, lido uma vez por host por execução.

    status: "permite" | "proibe" (o grupo que nos alcança nega a raiz) | "sem_robots" (4xx) |
    "indeterminado" (servidor não respondeu). Segue a RFC 9309 § 2.3.1: 4xx = sem restrição."""
    if host in _ROBOTS_CACHE:
        return _ROBOTS_CACHE[host]
    codigo, texto = ler_fn(host)
    reg = {"status": "indeterminado", "crawl_delay": None, "rp": None}
    if codigo == 200 and texto.strip():
        rp = _robotparser.RobotFileParser()
        rp.parse(texto.splitlines())
        cd = rp.crawl_delay(UA) or rp.crawl_delay("*")
        reg = {"status": "permite" if rp.can_fetch(UA, f"https://{host}/") else "proibe",
               "crawl_delay": min(float(cd), CRAWL_DELAY_MAXIMO) if cd else None, "rp": rp}
    elif codigo is not None and 400 <= codigo < 500:
        reg = {"status": "sem_robots", "crawl_delay": None, "rp": None}
    _ROBOTS_CACHE[host] = reg
    return reg


def robots_permite(host: str, url: str) -> bool | None:
    """True/False pelo robots do sítio para o NOSSO cliente; None quando não há robots ou não deu
    para ler. Só informa — a decisão de acessar é da editoria (§185), não desta função."""
    reg = robots_de(host)
    if reg["rp"] is None:
        return None
    return bool(reg["rp"].can_fetch(UA, url))


def _respeitar_ritmo(host: str, crawl_delay, dormir=None):
    """Espera o que o sítio pediu entre dois acessos ao mesmo host. Sem pedido, não espera
    (o ritmo de 2 s por domínio continua sendo responsabilidade de quem chama, como sempre)."""
    import time as _t
    dormir = dormir or _t.sleep
    if not crawl_delay:
        _ULTIMO_ACESSO[host] = _t.time()
        return
    passado = _t.time() - _ULTIMO_ACESSO.get(host, 0.0)
    if passado < crawl_delay:
        dormir(crawl_delay - passado)
    _ULTIMO_ACESSO[host] = _t.time()


def registrar_acesso_contra_robots(host: str, url: str, origem: str = None) -> None:
    """Rastro público (§185): cada acesso feito onde o robots pediu que robôs não entrassem.
    Guarda os 200 últimos por host e a contagem total — nunca apaga o fato de ter acessado."""
    import datetime as _dt
    reg = ler(ROBOTS_REGISTRO, {"_governanca": "Rastro dos acessos feitos contra o pedido do robots.txt "
                                                 "(§185, decisão da editoria de 23/09/2026): o Monitor lê "
                                                 "documento público com cliente identificado e Crawl-delay "
                                                 "respeitado, e registra aqui cada acesso desse tipo. "
                                                 "Nunca lido pelo cálculo da nota.", "hosts": {}}) or {}
    hosts = reg.setdefault("hosts", {})
    h = hosts.setdefault(host, {"status_robots": None, "crawl_delay": None, "primeiro_acesso": hoje(),
                                "total_acessos": 0, "acessos": []})
    r = _ROBOTS_CACHE.get(host) or {}
    h["status_robots"] = r.get("status"); h["crawl_delay"] = r.get("crawl_delay")
    h["ultimo_acesso"] = hoje(); h["total_acessos"] = int(h.get("total_acessos", 0)) + 1
    h["acessos"].append({"url": url, "quando": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "origem": origem or EXECUTOR, "cliente": UA.split(" ")[0]})
    h["acessos"] = h["acessos"][-200:]
    gravar(ROBOTS_REGISTRO, reg)


# ---------------------------------------------------------------------------------
# Muro de robô: a recusa que vem com HTTP 200 (§186, 23/09/2026).
#
# ACHADO REAL. Na releitura de SP, `defesacivil.sp.gov.br` respondeu 200 e 107 kB de HTML na
# primeira leitura e, depois de alguns pedidos, passou a devolver **200 com a página "Pardon Our
# Interruption"** — o muro do Imperva. Um 403 o projeto já sabia tratar (§170: o servidor respondeu
# não). Um muro com 200 é pior, porque *parece* conteúdo: sem este detector, ele entraria no índice
# de evidências como documento preservado, e uma página de bloqueio de 6 kB ficaria registrada como
# se fosse o plano do estado. Seria prova falsa — o defeito mais grave que este projeto pode ter.
#
# A LEITURA CORRETA é a do §170: isto é recusa, e recusa se respeita. Não se disfarça cliente, não
# se troca de rota, não se tenta de novo em loop. Vira lacuna declarada com o motivo escrito.
class MuroDeRobo(Exception):
    """A resposta veio com 200, mas é página de bloqueio de robô, não o documento pedido."""

    def __init__(self, url: str, marca: str):
        super().__init__(f"muro de robô em {url}: {marca!r} — recusa com HTTP 200 (§186); não se contorna")
        self.url = url
        self.marca = marca


# Marcas de muro, no texto declarativo da página. Cada uma é assinatura de um produto conhecido, e a
# lista é fechada de propósito: heurística larga ("acesso negado") confundiria página institucional
# que fala de negativa de acesso à informação com bloqueio técnico.
MARCAS_DE_MURO = (
    "pardon our interruption",              # Imperva/Incapsula
    "attention required! | cloudflare",     # Cloudflare
    "checking your browser before accessing",
    "just a moment...",                     # Cloudflare challenge
    "enable javascript and cookies to continue",
    "request unsuccessful. incapsula incident",
    "access denied | akamai",
    "you have been blocked",
    "sorry, you have been blocked",
    "bot detection",
    "verificando seu navegador",
    # §187: geobloqueio de WAF, servido com HTTP 200. ACHADO REAL: portal.saude.sp.gov.br devolveu
    # esta página no lugar do robots.txt (captura de 29/04/2026), e a rodada de 10/09 registrou no
    # banco que o host "recusa acesso automatizado por robots.txt" — diagnóstico errado que virou
    # regra de abstenção por treze dias. Não é muro de robô no sentido estrito: é muro de país. A
    # classe é a mesma, e é isso que importa — o servidor respondeu não, e a resposta parece conteúdo.
    "connection denied by geolocation",
)


def detectar_muro_de_robo(corpo: bytes, tamanho_maximo: int = 60000) -> str | None:
    """Marca do muro, ou None. Só olha respostas PEQUENAS: muro é página curta, e varrer um PDF de
    20 MB em busca de frase de bloqueio custa caro e acha falso positivo em documento que cite o
    assunto. Função pura."""
    if not corpo or len(corpo) > tamanho_maximo:
        return None
    if corpo[:5] == b"%PDF-":
        return None
    try:
        texto = _plano(texto_declarativo(corpo.decode("utf-8", "replace")))
    except Exception:  # noqa: BLE001
        return None
    for marca in MARCAS_DE_MURO:
        if _plano(marca) in texto:
            return marca
    return None


def contexto_tls():
    """Contexto TLS verificado contra o pacote de CAs do `certifi`, quando ele existe.

    24/09/2026 (§208): três fontes oficiais falhavam aqui com CERTIFICATE_VERIFY_FAILED —
    `gsc.cemaden.gov.br`, `ftp.ibge.gov.br` e a listagem da MUNIC — porque a loja de
    certificados da máquina Windows não completa a cadeia delas. No runner Linux passavam, e por
    isso o defeito se disfarçava de "fonte fora do ar no ambiente de edição": a sonda da MUNIC
    chegou a documentar a causa errada (403 de host) e ficou marcada como não executável
    localmente. Nomear a recusa errado é exatamente o que o CLAUDE.md proíbe.

    Isto NÃO afrouxa verificação: continua validando o certificado, contra um conjunto de raízes
    mais completo e igual em qualquer máquina. Fonte que recusa de verdade continua recusando, e
    `certifi` está declarado e travado em requirements.txt. Sem o pacote, devolve None e o
    comportamento é o de antes."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return None


def buscar_uma_vez(url: str, timeout: int = 40, origem: str = None) -> bytes:
    """GET simples com User-Agent do projeto, UMA tentativa (ver `buscar`, que repete). Levanta a exceção — quem chama decide
    se vira lacuna declarada (regra 1) ou aborta. Em sítio público (não API), testa o corpo
    contra os padrões de página de defeso e registra a fonte como suspensa (PR-N0 §1.5).

    §185: antes do pedido, lê o robots.txt do sítio (uma vez por host) e respeita o Crawl-delay
    que ele declara; depois do pedido, se o robots pedia que robôs não entrassem ali, registra o
    acesso em data/robots_registro.json. O acesso acontece — decisão da editoria —, mas nunca
    sem rastro e nunca disfarçado."""
    host = (urllib.parse.urlparse(url).netloc or "").lower()
    robots = robots_de(host) if host else {"status": "indeterminado", "crawl_delay": None, "rp": None}
    _respeitar_ritmo(host, robots.get("crawl_delay"))
    req = urllib.request.Request(url_ascii(url), headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout, context=contexto_tls()) as r:
        corpo = r.read()
        ct = (r.headers.get("Content-Type") or "").lower()
    if robots.get("rp") is not None and not robots["rp"].can_fetch(UA, url_ascii(url)):
        try:
            registrar_acesso_contra_robots(host, url, origem)
        except Exception:  # noqa: BLE001 — o rastro nunca derruba a coleta; a falha aparece no log
            pass
    # §186: muro de robô com HTTP 200 é recusa, não conteúdo. Levanta antes de qualquer preservação,
    # para que uma página de bloqueio não entre no índice de evidências como se fosse o documento.
    marca = detectar_muro_de_robo(corpo)
    if marca:
        raise MuroDeRobo(url, marca)
    if _dominio_publico(url) and ("html" in ct or "text" in ct or corpo[:200].lstrip().lower().startswith(b"<!doctype") or b"<html" in corpo[:2000].lower()):
        pad = detectar_defeso(corpo[:200000].decode("utf-8", "replace")) or ("defeso" if "defeso" in url.lower() else None)
        if pad:
            _SUSPENSAS_SESSAO[url] = pad
            try:
                registrar_fonte_suspensa(url, corpo, pad)
            except Exception:  # noqa: BLE001
                pass
    return corpo


# Quanto esperar antes de repetir, por status HTTP. Nasceu local em coletar_diarios_municipais.py
# em 25/09/2026, depois de uma medição na varredura nacional: **63 dos 505 primeiros municípios**
# viraram lacuna por `HTTP 503 Service Unavailable` — 12 %, e nenhum deles bloqueio de acesso.
# Indisponibilidade temporária é a fonte dizendo "tente mais tarde", e a resposta certa a isso é
# tentar mais tarde.
#
# 26/09/2026 (§226): a política sobe para cá porque a lição valia para os dezesseis coletores e
# estava aplicada em UM. Os outros quinze chamavam `buscar()` direto e desistiam na primeira
# tentativa — mesmo defeito de escopo do §213 e do §222, agora numa regra de rede em vez de num
# vocabulário. Quem faz o pedido é quem tem de saber esperar, e o pedido é feito aqui.
ESPERAS_429 = (30,)        # limite de taxa: a fonte manda esperar, e esperar é a resposta certa
ESPERAS_5XX = (5, 15)      # indisponibilidade temporária: "tente mais tarde", crescendo
# Conexão que nem chegou a virar conversa HTTP — reset, handshake TLS incompleto, DNS mudo,
# timeout. UMA repetição curta, e não duas como no 5xx, por uma razão de custo medida: host
# realmente fora do ar paga esta espera em CADA url de uma varredura, e uma varredura tem
# milhares. Cinco segundos por url morta é aceitável; vinte, não.
#
# Que uma repetição basta veio de medição: em 24/09/2026, **105 leituras de PDF** falharam com
# `URLError` num único dia, nos sítios de defesa civil de SE e AM. Testados em 26/09 sem
# nenhuma mudança de código, os três documentos que a amostra apontava responderam na hora, com
# 5,8 MB, 642 kB e 7,7 MB de PDF válido. Não era fonte fora do ar: era uma tarde ruim de rede
# tratada como ausência de documento.
ESPERAS_CONEXAO = (5,)


def esperas_para(codigo: int) -> tuple:
    """Sequência de esperas, em segundos, antes de repetir um pedido que devolveu `codigo`.
    Vazia quando repetir não ajuda. Função pura.

    4xx (fora 429) não repete: consulta errada não melhora com repetição, e repetir só dobraria a
    carga sobre APIs públicas mantidas por projetos sem fins lucrativos. 429 repete UMA vez, depois
    da espera que a fonte pede — respeitar um limite de taxa é honrar a espera, não desistir na
    hora nem insistir sem parar."""
    if codigo == 429:
        return ESPERAS_429
    if codigo >= 500:
        return ESPERAS_5XX
    return ()


def buscar(url: str, timeout: int = 40, origem: str = None, buscar_fn=None, dormir=None) -> bytes:
    """`buscar_uma_vez` com a espera do §226: repete quando a fonte pede tempo (429 e 5xx) ou
    quando a conexão nem virou conversa HTTP (reset, TLS, DNS, timeout), e sobe na hora quando
    repetir não ajudaria — 4xx e muro de robô, que são recusa e não indisponibilidade.

    É a porta por onde todo coletor pede rede, e a correção entra aqui de propósito: dezesseis
    coletores passam a esperar sem mudar uma linha de chamada em nenhum deles. Quem mocka `buscar`
    num autoteste continua funcionando — o mock substitui a função inteira, repetição incluída.

    `buscar_fn` e `dormir` existem para o autoteste, que precisa provar a espera sem rede e sem
    esperar de verdade."""
    _dormir = dormir or time.sleep

    def uma_vez():
        if buscar_fn is not None:
            return buscar_fn(url, timeout=timeout)
        return buscar_uma_vez(url, timeout=timeout, origem=origem)

    restantes = None
    while True:
        try:
            return uma_vez()
        except urllib.error.HTTPError as e:
            # HTTPError é subclasse de URLError: tem de vir ANTES, senão todo status viraria
            # "erro de conexão" e perderia a distinção entre recusa e indisponibilidade.
            if restantes is None:
                restantes = list(esperas_para(e.code))
            if not restantes:
                raise
            _dormir(restantes.pop(0))
        except (urllib.error.URLError, TimeoutError):
            if restantes is None:
                restantes = list(ESPERAS_CONEXAO)
            if not restantes:
                raise
            _dormir(restantes.pop(0))


# Códigos em que o servidor NÃO falhou: ele respondeu, e a resposta foi "não". Cair na
# reserva do Wayback nesses casos seria contornar bloqueio de acesso de fonte, que o
# CLAUDE.md proíbe. A reserva existe para o caso oposto — a conexão que nem chega a virar
# conversa HTTP (reset, handshake TLS incompleto, DNS mudo), em que não há recusa a
# respeitar porque não houve resposta.
RECUSAS_EXPLICITAS = {401, 402, 403, 429, 451}


def buscar_com_procedencia(url: str, timeout: int = 40, buscar_fn=None) -> tuple:
    """Como buscar_com_reserva_wayback, mas DIZ por qual caminho o conteúdo veio:
    devolve (bytes, procedencia) com procedencia em {"fonte direta", "captura do Wayback"}.

    A distinção não é cosmética. Um plano lido no sítio do órgão e um plano lido numa
    captura de arquivo provam coisas diferentes: o primeiro é o documento como está hoje,
    o segundo é como estava quando alguém o arquivou. Registrar qual dos dois foi é a
    mesma disciplina que separa `declarado` de `documentado` no resto do projeto — e sem
    o campo, as duas viravam a mesma coisa no banco."""
    _buscar = buscar_fn or buscar
    try:
        return _buscar(url, timeout=timeout), "fonte direta"
    except urllib.error.HTTPError as e:
        if e.code in RECUSAS_EXPLICITAS:
            raise                       # a fonte disse não; não se dá a volta por fora
        e_direto = e
    except Exception as e:  # noqa: BLE001
        e_direto = e

    # 12/09/2026: a mensagem antiga só repetia o erro direto — sem dizer se foi o PEDIDO de
    # captura que falhou (arquivo.org pode demorar mais que nosso timeout num sítio lento)
    # ou a LEITURA dela. Timeout maior para o Wayback e mensagem que preserva os dois passos.
    erro_salvar = erro_ler = None
    try:
        _buscar("https://web.archive.org/save/" + url, timeout=max(timeout, 90))
    except Exception as e:  # noqa: BLE001
        erro_salvar = e
    try:
        return (_buscar(f"https://web.archive.org/web/20301231000000/{url}",
                        timeout=max(timeout, 60)),
                "captura do Wayback")
    except Exception as e:  # noqa: BLE001
        erro_ler = e
    raise RuntimeError(f"direto: {type(e_direto).__name__}: {e_direto} | wayback/save: "
                       f"{type(erro_salvar).__name__ if erro_salvar else 'ok'} | wayback/ler: "
                       f"{type(erro_ler).__name__}: {erro_ler}") from e_direto


def buscar_com_reserva_wayback(url: str, timeout: int = 40) -> bytes:
    """12/09/2026: reserva para fontes que o runner não alcança diretamente (medido: alguns portais estaduais
    pequenos não completam handshake TLS/conexão com o runner do Actions, enquanto web.archive.org — um CDN
    global — responde em ~1s no mesmo runner). Tenta buscar() direto primeiro; se falhar, pede ao archive.org
    para capturar a página AGORA (rede própria dele, não passa pelo runner) e lê a captura mais recente
    (timestamp bem no futuro é o truque para pegar a mais nova, não a mais antiga disponível). Se o pedido de
    captura falhar ou for limitado, ainda tenta ler uma captura já existente antes de desistir — pode não ser
    da mesma hora, mas é melhor que lacuna para fonte semanal."""
    return buscar_com_procedencia(url, timeout=timeout)[0]


def fonte_esta_suspensa(urls) -> bool:
    """True se alguma URL desta execução casou o detector de defeso."""
    return any(u in _SUSPENSAS_SESSAO for u in (urls or []))


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def preservar_evidencia(conteudo: bytes, url: str, ext: str, origem: str) -> str:
    """Guarda cópia da evidência e indexa em data/evidencias.json. Retorna o hash.
    Acima de 5 MB: só o hash + pedido de snapshot ao Wayback (best effort)."""
    h = sha256(conteudo)
    idx = ler("evidencias.json", {"_governanca": "Índice de evidências preservadas (§3.8, v2.2.4). "
                                   "Chave = sha256 do documento; nunca lido pelo cálculo do índice.",
                                   "itens": {}})
    if h in idx["itens"]:
        return h
    item = {"url": url, "origem": origem, "preservado_em": hoje(), "tamanho": len(conteudo),
            "arquivo": None, "wayback": None}
    if len(conteudo) <= LIMITE_EVIDENCIA:
        EVID.mkdir(exist_ok=True)
        destino = EVID / f"{h}.{ext.lstrip('.')}"
        if not destino.exists():
            destino.write_bytes(conteudo)
        item["arquivo"] = destino.relative_to(RAIZ).as_posix()
    else:
        try:
            buscar("https://web.archive.org/save/" + url, timeout=60)
            item["wayback"] = "https://web.archive.org/web/*/" + url
        except Exception as e:  # noqa: BLE001
            item["wayback"] = f"tentativa falhou ({type(e).__name__})"
    idx["itens"][h] = item
    gravar("evidencias.json", idx)
    return h


def _indexar_texto_integral(h: str, destino, origem=None) -> str:
    """Indexa o texto integral preservado — e o HASH do arquivo (§176, 23/09/2026).

    Sem o hash, o portão 6 não tem com o que comparar o arquivo publicado: 148 itens ficaram
    assim, e quatro apontavam para um `.txt` que não estava em disco sem que nada acusasse (o
    campo foi gravado em 12/09 e o arquivo nunca entrou no commit da rodada). Chamado também
    quando o arquivo JÁ existe, para curar o índice de quem foi preservado antes desta regra —
    daí `origem=None`, que preserva a data e a origem da preservação original.
    """
    caminho = destino.relative_to(RAIZ).as_posix()
    idx = ler("evidencias.json", {"itens": {}})
    item = (idx.get("itens") or {}).get(h)
    if item is None:
        return caminho
    antes = dict(item)
    item["texto_integral"] = caminho
    item["texto_integral_hash"] = sha256(destino.read_bytes())
    if origem is not None:
        item["texto_integral_em"] = hoje()
        item["texto_integral_origem"] = origem
    if item != antes:
        gravar("evidencias.json", idx)
    return caminho


def normalizar_quebras(texto: str) -> str:
    """Toda quebra de linha vira LF. Função pura.

    §177: cópia preservada em CRLF é cópia que depende da máquina que a produziu. A regra nasceu
    do OCR (o Tesseract do Windows devolve CRLF) e vale igual para o documento de origem, que
    também pode trazer CRLF solto — e aí o modo de escrita não resolve, porque ele só traduz a
    quebra que nós escrevemos."""
    return texto.replace("\r\n", "\n").replace("\r", "\n")


def preservar_texto_integral(h: str, gazettes, origem: str):
    """Baixa o texto integral (txt_url) das edições cuja resposta da API já foi preservada
    sob o hash h, gravando em evidencias/<h>.txt (decisão editorial de 10/09/2026: o excerto
    localiza a menção, mas quem julga precisa do documento inteiro, legível offline — a coleta
    é o único momento garantidamente sem bloqueio de acesso). Idempotente e best-effort:
    falha de rede não derruba a coleta; a pista continua valendo com o excerto (regra 1)."""
    destino = EVID / f"{h}.txt"
    if destino.exists():
        return _indexar_texto_integral(h, destino)   # §176: sela o hash de quem já está em disco
    partes, total = [], 0
    for g in (gazettes or []):
        u = g.get("txt_url") or ""
        if not u:
            continue
        try:
            corpo = buscar(u, timeout=60)
        except Exception as e:  # noqa: BLE001 — best effort; a falha fica declarada no arquivo
            partes.append(f"=== {g.get('date', '')} · {u} ===\n[texto integral indisponível nesta coleta: {type(e).__name__}]")
            continue
        # 25/09/2026 (§177, achado na varredura nacional): o documento de ORIGEM pode trazer
        # CRLF solto — dois diários municipais vieram com 8 e 16 quebras CRLF entre mais de cem
        # mil LF. A cópia preservada é transcrição, não arquivo byte a byte (já redigimos CPF dela),
        # e a regra do projeto é que ela não dependa da máquina. A normalização tem de ser AQUI, na
        # entrada: o `newline` da escrita traduz a quebra que NÓS escrevemos, e não a que já veio
        # dentro do texto.
        texto = normalizar_quebras(corpo.decode("utf-8", errors="replace"))
        total += len(corpo)
        if total > LIMITE_EVIDENCIA:
            corte = max(0, len(texto) - (total - LIMITE_EVIDENCIA))
            partes.append(f"=== {g.get('date', '')} · {u} ===\n{texto[:corte]}\n[truncado no limite de evidência de {LIMITE_EVIDENCIA} bytes]")
            break
        partes.append(f"=== {g.get('date', '')} · {u} ===\n{texto}")
    if not partes:
        return None
    texto_final = "\n\n".join(partes) + "\n"
    # 12/09/2026 (achado de auditoria): a edição INTEIRA do diário vem junto, e diários oficiais
    # brasileiros publicam dezenas de atos não relacionados na mesma edição — inclusive CPF de
    # contribuintes e servidores em despachos tributários e de pessoal que nada têm a ver com o
    # objeto do Monitor. Ver redigir_dados_pessoais() para a fundamentação (LGPD art. 6º, III).
    texto_final, n_cpfs = redigir_dados_pessoais(texto_final)
    EVID.mkdir(exist_ok=True)
    destino.write_text(texto_final, encoding="utf-8", newline="\n")
    if n_cpfs:
        # 19/09/2026 (ensaio da rodada antecipada, portão bloqueante vermelho): este registro
        # documenta uma REDAÇÃO de dados pessoais num documento preservado — não é uma busca
        # territorial, e não tem município/UF estruturados no ponto da chamada. O valor
        # "municipal" que estava aqui nunca existiu no vocabulário controlado de
        # verificar_consistencia.py (_NIVEIS = {None, "nacional", "estadual",
        # "municipal_completo"}), então toda vez que um diário com CPF era preservado o
        # portão obrigatório caía com "nivel inválido: municipal" e a rodada inteira parava
        # antes do commit. Bug latente desde 12/09/2026: só dispara quando há CPF a redigir.
        # nivel=None é o valor honesto (sem nível territorial declarado) e já aceito; não usar
        # "municipal_completo", que tem sentido próprio no §2.1 (bateria municipal completa) e
        # exige municipio e uf estruturados.
        log_busca("site_estadual", 2, [destino.relative_to(RAIZ).as_posix()], "registro", nivel=None,
                  resultados=f"redação de dados pessoais: {n_cpfs} CPF(s) removido(s) do texto integral preservado ({origem})")
    return _indexar_texto_integral(h, destino, origem)


# ---------------------------------------------------------------------------------
# LOTE DO LOG (24/09/2026, §209) — para varredura nacional
#
# `log_busca` lê E grava `log_buscas.json` (hoje 16 MB) a CADA chamada. Isso é correto para
# coletores de dezenas de municípios, e inviável numa varredura dos 5.570: seriam 5.570 leituras
# e 5.570 gravações de 16 MB, cerca de 180 GB de E/S — e, pior, cada gravação é uma janela em que
# uma interrupção deixa o arquivo pela metade. É a mesma armadilha que `marcar_fato_municipal`
# criou em `coletar_declarado_nacional.py` em 21/09, quando corrompeu `fontes_consultadas.json`.
#
# A saída aqui é a mesma, mas no lugar certo: um lote OPCIONAL. Sem abrir lote, nada muda para
# nenhum coletor existente. Com lote aberto, as execuções ficam em memória e são descarregadas de
# 250 em 250 — teto que limita tanto a E/S quanto o que se perderia numa interrupção.
_LOTE_LOG = None
_LOTE_LOG_TETO = 250


def abrir_lote_log():
    """Começa a acumular execuções em memória em vez de gravar a cada chamada."""
    global _LOTE_LOG
    if _LOTE_LOG is None:
        _LOTE_LOG = []


def descarregar_lote_log():
    """Grava o que está acumulado, numa leitura e uma gravação. Idempotente."""
    global _LOTE_LOG
    if not _LOTE_LOG:
        return 0
    pendentes, _LOTE_LOG = _LOTE_LOG, []
    lg = ler("log_buscas.json")
    assert lg and lg.get("formato_versao") == 2, "log_buscas.json precisa estar no esquema v2"
    lg["execucoes"].extend(pendentes)
    gravar("log_buscas.json", lg)
    _LOTE_LOG = []
    return len(pendentes)


def fechar_lote_log():
    """Descarrega o que resta e volta ao comportamento de gravar a cada chamada."""
    global _LOTE_LOG
    n = descarregar_lote_log()
    _LOTE_LOG = None
    return n


# Vocabulário FECHADO das decisões do log. Era uma tupla anônima dentro do `assert`, e por isso
# ninguém percebeu quando o §194 (24/09/2026) criou a decisão `sem_edicao_no_periodo` no coletor
# dos diários municipais e não a acrescentou aqui: a varredura passou a morrer com AssertionError
# no primeiro município indexado sem edição na janela — e morrer é melhor do que gravar errado,
# mas a varredura ficou parada sem que isso aparecesse como problema de vocabulário. Nomear a
# lista é o que permite que o coletor que INVENTA uma decisão prove, no autoteste dele, que ela
# cabe aqui.
DECISOES_LOG = ("registro", "pista", "nada", "consultado", "fonte", "erro", "acesso",
                "sem_cobertura_qd", "sem_edicao_no_periodo", "coberto_sem_mencao", "com_excerto")


def log_busca(canal: str, camada: int, strings: list, decisao: str, resultados: str = "",
              uf=None, municipio=None, ibge=None, nivel=None, n_resultados=None,
              fonte_suspensa_defeso: bool = False, hash_evidencia=None):
    """Acrescenta uma execução ao log v2. `decisao` no vocabulário fechado:
    registro | pista | nada localizado | consultado sem achado | fonte suspensa (defeso) | erro.

    §184 (23/09/2026): "consultado sem achado" existe porque "nada localizado" **não podia ser
    reusado**. Aquele valor é da bateria municipal completa: `recalcular_mare.py` o lê para elevar o
    nível de verificação do município, `verificar_consistencia.py` reprova se ele aparecer sem
    `nivel="municipal_completo"`, e o assert abaixo o exige. Uma sonda de UF que consultou o portal
    e não achou painel precisa registrar isso — o silêncio foi o pior defeito do §181 —, mas não pode
    entrar pela porta da verificação municipal."""
    assert decisao.split(" ")[0] in DECISOES_LOG, decisao
    if decisao.startswith("nada localizado"):
        assert nivel == "municipal_completo", "regra §2.1: 'nada localizado' exige bateria municipal completa"
    execucao = {
        "data": hoje(), "canal": canal, "camada": camada, "uf": uf, "municipio": municipio,
        "ibge": ibge, "nivel": nivel, "strings": strings, "n_resultados": n_resultados,
        "resultados": resultados[:600], "decisao": decisao,
        "fonte_suspensa_defeso": bool(fonte_suspensa_defeso) or fonte_esta_suspensa(strings), "executor": EXECUTOR,
        "hash_evidencia": hash_evidencia}
    # Com lote aberto, acumula e descarrega de 250 em 250 (ver LOTE DO LOG acima). Sem lote, o
    # comportamento é o de sempre: uma leitura e uma gravação por execução.
    if _LOTE_LOG is not None:
        _LOTE_LOG.append(execucao)
        if len(_LOTE_LOG) >= _LOTE_LOG_TETO:
            descarregar_lote_log()
        return
    lg = ler("log_buscas.json")
    assert lg and lg.get("formato_versao") == 2, "log_buscas.json precisa estar no esquema v2"
    lg["execucoes"].append(execucao)
    gravar("log_buscas.json", lg)


# ── página de consulta do DOU (compartilhada por coletar_s2id e coletar_espin) ──
# 24/09/2026: a busca do DOU trocou o transporte do resultado. Ele vinha num
# <input ... value="{json}"> e passou a vir num <script type="application/json">. Os dois
# coletores tinham, cada um, a cópia do regex do <input> — e devolviam LISTA VAZIA para
# qualquer consulta, calados: a guarda do s2id testava `"jsonArray" in texto`, e essa
# string continua na página (está no script e no JS ao lado), de modo que a guarda passava
# e o zero virava "consultamos e não há". Medido em 24/09: a consulta de reconhecimentos
# tinha 132 resultados reais no ciclo, e o coletor lia 0. Agora o leitor é UM, e a ausência
# do elemento LEVANTA — nunca devolve lista vazia.

class FormatoDoDOUMudou(Exception):
    """A página de consulta não trouxe o elemento de resultados. É lacuna, não ausência."""


_ID_BUSCA_DOU = "_br_com_seatecnologia_in_buscadou_BuscaDouPortlet_params"
# A data VAI em dd-mm-aaaa. Com aaaa-mm-dd a página responde 200 e devolve outra janela
# (medido em 24/09: 132 resultados contra 3) — formato errado aqui não dá erro, dá número menor.
BUSCA_DOU = ("https://www.in.gov.br/consulta/-/buscar/dou?q={q}&s={secao}&exactDate=personalizado"
             "&sortType=0&publishFrom={de}&publishTo={ate}&delta=50")
TETO_PAGINA_DOU = 50      # medido: delta=50 devolve 50; delta=100 volta a 20, e `start` é ignorado


def _sem_marcacao(s: str) -> str:
    """Tira a marcação do trecho devolvido pela busca (o termo vem embrulhado em
    <span class='highlight'>) e normaliza o espaço. Função pura."""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", s or ""))).strip()


def parse_busca_dou(texto: str) -> list:
    """Resultados da página de consulta do DOU: [{titulo, url, data, trecho}]. Função pura.

    `trecho` é EXCERTO (≈235 caracteres com reticências), não o ato: quem precisa do texto
    inteiro tem de abrir `url`. Levanta FormatoDoDOUMudou quando o elemento de resultados
    não está na página — ausência de estrutura é lacuna, e lista vazia mentiria."""
    m = (re.search(r'<script[^>]*id="' + _ID_BUSCA_DOU + r'"[^>]*>(.*?)</script>', texto, re.S)
         or re.search(r'id="' + _ID_BUSCA_DOU + r'"[^>]*value="([^"]*)"', texto))
    if not m:
        raise FormatoDoDOUMudou("elemento de resultados ausente na página de consulta")
    try:
        dados = json.loads(html.unescape(m.group(1)).strip())
    except json.JSONDecodeError as e:
        raise FormatoDoDOUMudou(f"elemento de resultados ilegível: {e}") from e
    if not isinstance(dados, dict) or "jsonArray" not in dados:
        raise FormatoDoDOUMudou("elemento de resultados sem a chave jsonArray")
    return [{"titulo": _sem_marcacao(it.get("title")),
             "url": "https://www.in.gov.br/web/dou/-/" + (it.get("urlTitle") or ""),
             "data": it.get("pubDate", ""),
             # `orgao` é a hierarquia que a PRÓPRIA busca declara ("Ministério da Saúde/Gabinete
             # do Ministro"). Vale mais do que adivinhar o órgão pelo título: é a fonte dizendo
             # de quem é o ato, e é por ele que um coletor decide quais atos vale a pena abrir.
             "orgao": _sem_marcacao(it.get("hierarchyStr")),
             "trecho": _sem_marcacao(it.get("content"))}
            for it in (dados.get("jsonArray") or [])]


def total_declarado_dou(texto: str):
    """Quantos resultados a PÁGINA diz ter ("132 resultados"), ou None. Função pura.
    Serve para saber se a leitura foi completa — ler 50 de 132 e não dizer nada seria
    apresentar recorte como varredura."""
    m = re.search(r"([\d.]+)\s*resultados?\b", texto, re.I)
    return int(m.group(1).replace(".", "")) if m else None


def varrer_busca_dou(q: str, de, ate, secao: str = "do1", buscar_fn=None, pausa: float = 2.0,
                     _prof: int = 0, _relogio=None) -> tuple:
    """Varre a consulta do DOU numa janela de datas e devolve (itens, janelas_incompletas).

    A página entrega no máximo 50 por consulta e não pagina (`start` é ignorado): o jeito de
    ler tudo é ESTREITAR a janela. Quando o total declarado passa do que veio, a janela é
    partida ao meio e as metades são lidas — recursivamente, até o dia. Dia único que ainda
    estoure entra em `janelas_incompletas`, que o coletor declara; nunca se apresenta recorte
    como varredura. `buscar_fn(url) -> bytes` é injetável (autoteste offline, preservação de
    evidência no chamador)."""
    buscar_fn = buscar_fn or buscar
    dormir = _relogio or time.sleep
    url = BUSCA_DOU.format(q=urllib.parse.quote(q), secao=secao,
                           de=de.strftime("%d-%m-%Y"), ate=ate.strftime("%d-%m-%Y"))
    # §11: no máximo uma requisição a cada 2 s por domínio. Aqui isso importa duas vezes, porque
    # estreitar a janela multiplica as chamadas ao MESMO host — quem varre tem de ir mais devagar,
    # não mais rápido. A primeira consulta de cada varredura não espera; as seguintes, sim.
    if _prof and pausa:
        dormir(pausa)
    texto = buscar_fn(url).decode("utf-8", "replace")
    itens = parse_busca_dou(texto)
    total = total_declarado_dou(texto)
    if total is None and len(itens) >= TETO_PAGINA_DOU:
        # A página veio cheia e não declarou o total (a contagem mudou de forma?). Não dá para
        # afirmar que é tudo — trata-se como janela que não coube, e estreita-se do mesmo jeito.
        total = len(itens) + 1
    if total is None or total <= len(itens):
        return itens, []
    if de >= ate:                                   # um dia só, e ainda não coube
        return itens, [{"de": de.isoformat(), "ate": ate.isoformat(), "lidos": len(itens), "total": total}]
    meio = de + (ate - de) / 2
    a, fa = varrer_busca_dou(q, de, meio, secao, buscar_fn, pausa, _prof + 1, _relogio)
    b, fb = varrer_busca_dou(q, meio + timedelta(days=1), ate, secao, buscar_fn, pausa, _prof + 1, _relogio)
    vistos, saida = set(), []
    for it in a + b:                                # janelas vizinhas não se sobrepõem, mas o
        if it["url"] in vistos:                     # DOU republica o mesmo ato em retificação
            continue
        vistos.add(it["url"]); saida.append(it)
    return saida, fa + fb


def eh_suspensao_defeso(html: str) -> bool:
    """Heurística declarada (§3.1): aviso de período eleitoral, ou página institucional
    esvaziada. Só rotula; nunca infere conteúdo."""
    t = html.lower()
    return any(k in t for k in ("período eleitoral", "periodo eleitoral", "legislação eleitoral",
                                "lei 9.504", "lei nº 9.504", "vedação eleitoral", "defeso eleitoral"))


def registrar_lacuna(fonte: str, motivo: str, canal: str, camada: int, strings=None, **kw):
    """Fonte não coletada → entrada de log com decisão 'erro' (ou 'fonte suspensa (defeso)')."""
    dec = "fonte suspensa (defeso)" if kw.pop("suspensa", False) else "erro"
    log_busca(canal, camada, strings or [fonte], dec, resultados=f"{fonte}: {motivo}",
              fonte_suspensa_defeso=(dec.startswith("fonte")), **kw)
    print(f"  [lacuna declarada] {fonte}: {motivo}")


# ── livro de fontes consultadas (por município) ─────────────────────────────

def referencia_ibge():
    ref = ler("municipios_ibge_referencia.json")
    por_cod = {str(r["codigo_ibge"]).zfill(7): r for r in ref}
    por_nome = {(r["nome"], r["uf"]): str(r["codigo_ibge"]).zfill(7) for r in ref}
    return por_cod, por_nome


# 25/09/2026: o mesmo problema do log, no livro de fontes. `marcar_fonte_consultada` e
# `marcar_fato_municipal` leem e regravam `fontes_consultadas.json` — 12 MB — a CADA município.
# Na varredura dos diários municipais são 2.965 municípios: cerca de 71 GB de entrada e saída, e
# 2.965 janelas em que uma interrupção deixa o arquivo pela metade. É literalmente o arquivo que
# foi corrompido assim em 21/09. A saída é a mesma do log: um lote OPCIONAL. Sem abrir lote, nada
# muda para nenhum coletor existente.
_LOTE_LIVRO = None          # o livro inteiro, em memória, enquanto o lote está aberto
_LOTE_LIVRO_PENDENTES = 0
_LOTE_LIVRO_TETO = 250


def abrir_lote_livro():
    """Carrega o livro de fontes uma vez e passa a mutá-lo em memória."""
    global _LOTE_LIVRO, _LOTE_LIVRO_PENDENTES
    if _LOTE_LIVRO is None:
        _LOTE_LIVRO = _livro_de_fontes()
        _LOTE_LIVRO_PENDENTES = 0


def descarregar_lote_livro():
    """Grava o livro se houver mutação pendente. Idempotente."""
    global _LOTE_LIVRO_PENDENTES
    if _LOTE_LIVRO is None or not _LOTE_LIVRO_PENDENTES:
        return 0
    n, _LOTE_LIVRO_PENDENTES = _LOTE_LIVRO_PENDENTES, 0
    gravar("fontes_consultadas.json", _LOTE_LIVRO)
    return n


def fechar_lote_livro():
    """Descarrega o que resta e volta a gravar a cada chamada."""
    global _LOTE_LIVRO
    n = descarregar_lote_livro()
    _LOTE_LIVRO = None
    return n


def _livro_de_fontes():
    return ler("fontes_consultadas.json", {"_governanca": "Livro de fontes consultadas por município "
                                           "(v2.2.4). Insumo do nível de verificação derivado por "
                                           "recalcular_mare.py; nunca lido pelo cálculo da nota.",
                                           "municipios": {}})


def _gravar_livro(livro):
    """Grava agora, ou deixa para o lote — e o lote tem teto, para limitar o que uma
    interrupção levaria embora."""
    global _LOTE_LIVRO_PENDENTES
    if _LOTE_LIVRO is None:
        gravar("fontes_consultadas.json", livro)
        return
    _LOTE_LIVRO_PENDENTES += 1
    if _LOTE_LIVRO_PENDENTES >= _LOTE_LIVRO_TETO:
        descarregar_lote_livro()


JANELA_FONTES = 12      # quantas consultas DISTINTAS cada município guarda no livro


def janela_de_fontes(entradas) -> list:
    """As últimas `JANELA_FONTES` consultas DISTINTAS (fonte, dia). Função pura.

    25/09/2026, medido: a janela era das últimas 12 ENTRADAS, e 38.434 delas eram repetição da
    mesma fonte no mesmo dia — cada município guardava 12 registros para apenas 5 ou 6 consultas
    distintas. `coletar_s2id` marca os 5.571 municípios a cada rodada, e roda mais de uma vez por
    dia; quatro entradas idênticas empurravam para fora do arquivo a consulta ao diário municipal.
    Foi o que fez 1.896 municípios voltarem a aparecer como pendentes depois de consultados.

    Isto NÃO contradiz a regra de nunca deduplicar o log: são arquivos com perguntas diferentes.
    O log responde "quantas tentativas houve" — e duas tentativas iguais em dias diferentes são
    duas tentativas, que contam. Este livro responde "que fontes foram consultadas, e quando" —
    e a mesma fonte no mesmo dia, repetida, não acrescenta resposta nenhuma. A entrada que fica
    é a ÚLTIMA de cada par, porque é ela que traz o resultado mais recente."""
    por_chave = {}
    for e in entradas or []:
        por_chave[(e.get("fonte"), e.get("data"))] = e      # a última de cada par vence
    distintas = list(por_chave.values())
    distintas.sort(key=lambda e: e.get("data") or "")        # estável: empate mantém a ordem
    return distintas[-JANELA_FONTES:]


def marcar_fonte_consultada(ibges, fonte: str, nivel: str, resultado: str = "consultada"):
    """Registra que `fonte` foi consultada para cada município em `ibges`, com o nível
    que essa fonte confere (§2.2). Nunca rebaixa um nível já alcançado."""
    assert nivel in NIVEIS
    livro = _LOTE_LIVRO if _LOTE_LIVRO is not None else _livro_de_fontes()
    ordem = {n: i for i, n in enumerate(NIVEIS)}
    for cod in ibges:
        cod = str(cod).zfill(7)
        m = livro["municipios"].setdefault(cod, {"nivel_verificacao": "nao_verificado",
                                                  "ultima_verificacao": None, "fontes": []})
        m["fontes"].append({"fonte": fonte, "data": hoje(), "resultado": resultado})
        m["fontes"] = janela_de_fontes(m["fontes"])
        if ordem[nivel] > ordem[m["nivel_verificacao"]]:
            m["nivel_verificacao"] = nivel
        m["ultima_verificacao"] = hoje()
    _gravar_livro(livro)


def marcar_fato_municipal(ibge, campo: str, valor):
    """Fatos binários por município (§3.3): decreto_reconhecido, decreto_homologado,
    plano_declarado_munic, plano_declarado_icm."""
    assert campo in ("decreto_reconhecido", "decreto_homologado", "plano_declarado_munic", "plano_declarado_icm")
    livro = _LOTE_LIVRO if _LOTE_LIVRO is not None else _livro_de_fontes()
    m = livro["municipios"].setdefault(str(ibge).zfill(7), {"nivel_verificacao": "nao_verificado",
                                                             "ultima_verificacao": None, "fontes": []})
    m[campo] = valor
    _gravar_livro(livro)


# ── autoteste ────────────────────────────────────────────────────────────────

def rodar_autoteste(testes: dict) -> int:
    """`testes` = {nome: callable→bool}. Imprime ✓/✗ e devolve o código de saída."""
    falhas = 0
    for nome, fn in testes.items():
        try:
            ok = bool(fn())
        except Exception as e:  # noqa: BLE001
            ok = False
            print(f"    ({type(e).__name__}: {e})")
        print(("  ✓ " if ok else "  ✗ ") + nome)
        falhas += (not ok)
    print("✓ AUTOTESTE OK" if not falhas else f"✗ AUTOTESTE: {falhas} falha(s)")
    return 1 if falhas else 0
