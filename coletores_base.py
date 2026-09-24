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
import hashlib, json, os, pathlib, re, ssl, sys, urllib.error, urllib.parse, urllib.request
from datetime import date, datetime

RAIZ = pathlib.Path(__file__).parent
DATA = RAIZ / "data"
EVID = RAIZ / "evidencias"
LIMITE_EVIDENCIA = 5 * 1024 * 1024  # bytes
UA = "MonitorElNinoBrasil/2.2.4 (+https://monitorelnino.com.br; coletor da Pista A)"
NIVEIS = ("nao_verificado", "nacional", "estadual", "municipal_completo")
EXECUTOR = "robo" if os.environ.get("GITHUB_ACTIONS") else "claude"


def hoje() -> str:
    return date.today().isoformat()


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


def gravar(nome, obj):
    """Escrita ATÔMICA (achado real, 21/09/2026): a versão anterior escrevia direto no arquivo
    final — qualquer interrupção no meio (timeout, Action cancelada, OOM) deixava um JSON
    truncado e inválido. Reproduzido de verdade: coletar_declarado_nacional.py rodando sob
    `timeout 200` corrompeu data/fontes_consultadas.json (368.019 → 166.961 linhas, JSON
    inválido). Corrigido: grava num arquivo temporário no mesmo diretório e substitui via
    os.replace(), que em POSIX é atômico — o arquivo final é sempre a versão antiga completa
    ou a nova completa, nunca uma mistura truncada."""
    p = DATA / nome
    ind = _indent_de(p)
    tmp = p.with_name(f"{p.name}.tmp{os.getpid()}")
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=ind)
        f.write("\n")
    os.replace(tmp, p)


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


def buscar(url: str, timeout: int = 40, origem: str = None) -> bytes:
    """GET simples com User-Agent do projeto. Levanta a exceção — quem chama decide
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
        texto = corpo.decode("utf-8", errors="replace")
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
    assert decisao.split(" ")[0] in ("registro", "pista", "nada", "consultado", "fonte", "erro", "acesso", "sem_cobertura_qd", "coberto_sem_mencao", "com_excerto"), decisao   # "acesso recusado" (§10.1), decisões do §1.2, "consultado sem achado" (§184)
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


def marcar_fonte_consultada(ibges, fonte: str, nivel: str, resultado: str = "consultada"):
    """Registra que `fonte` foi consultada para cada município em `ibges`, com o nível
    que essa fonte confere (§2.2). Nunca rebaixa um nível já alcançado."""
    assert nivel in NIVEIS
    livro = ler("fontes_consultadas.json", {"_governanca": "Livro de fontes consultadas por município "
                                            "(v2.2.4). Insumo do nível de verificação derivado por "
                                            "recalcular_mare.py; nunca lido pelo cálculo da nota.",
                                            "municipios": {}})
    ordem = {n: i for i, n in enumerate(NIVEIS)}
    for cod in ibges:
        cod = str(cod).zfill(7)
        m = livro["municipios"].setdefault(cod, {"nivel_verificacao": "nao_verificado",
                                                  "ultima_verificacao": None, "fontes": []})
        m["fontes"].append({"fonte": fonte, "data": hoje(), "resultado": resultado})
        m["fontes"] = m["fontes"][-12:]
        if ordem[nivel] > ordem[m["nivel_verificacao"]]:
            m["nivel_verificacao"] = nivel
        m["ultima_verificacao"] = hoje()
    gravar("fontes_consultadas.json", livro)


def marcar_fato_municipal(ibge, campo: str, valor):
    """Fatos binários por município (§3.3): decreto_reconhecido, decreto_homologado,
    plano_declarado_munic, plano_declarado_icm."""
    assert campo in ("decreto_reconhecido", "decreto_homologado", "plano_declarado_munic", "plano_declarado_icm")
    livro = ler("fontes_consultadas.json", {"_governanca": "", "municipios": {}})
    m = livro["municipios"].setdefault(str(ibge).zfill(7), {"nivel_verificacao": "nao_verificado",
                                                             "ultima_verificacao": None, "fontes": []})
    m[campo] = valor
    gravar("fontes_consultadas.json", livro)


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
