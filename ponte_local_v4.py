#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MARÉ · ponte no Brasil — programa local (monitorelnino.com.br)

O que faz, de hora em hora, neste computador (regra da editoria, 18/11/2026):
  1. leva para esta pasta os arquivos "ponte_*.bin" que o navegador do app do Claude deixou em Downloads;
  2. lê a lista pública de endereços que não abrem para o robô do MARÉ fora do Brasil;
  3. busca cada um com o cliente identificado do MARÉ, no ritmo do site, e para diante de recusa
     (401, 403, 429, 451): recusa da fonte se respeita, também no Brasil;
  4. guarda as cópias em "copias" e envia o lote ao repositório do projeto; no que é enviado, credencial e
     CPF de terceiro que venham dentro de uma página são redigidos antes (a cópia desta pasta fica como veio).

Não executa nada que venha da internet: só lê uma lista de endereços. Não apaga arquivo seu.
Só usa o que já vem com o Python. Para desinstalar: DESINSTALAR_PONTE.cmd, nesta pasta.

USO
  ponte_local.py              uma rodada, em silêncio (é o que a tarefa do Windows chama)
  ponte_local.py --agora      uma rodada, contando o que faz
  ponte_local.py --instalar   cria a tarefa do Windows e faz a primeira rodada
"""
import datetime as dt
import hashlib
import ipaddress
import json
import os
import pathlib
import re
import shutil
import socket
import ssl
import stat
import struct
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from xml.sax.saxutils import escape as _x

VERSAO = "4"
AQUI = pathlib.Path(__file__).resolve().parent
UA = f"MonitorElNinoBrasil/2.2.4 (+https://monitorelnino.com.br; ponte no Brasil, programa local v{VERSAO})"
ORDEM = os.environ.get("PONTE_ORDEM") or "https://raw.githubusercontent.com/monitorelnino/monitorelnino/ponte-ordem/ponte_ordem.json"
REMOTO = os.environ.get("PONTE_REMOTO") or "https://github.com/monitorelnino/monitorelnino.git"
TESTE = os.environ.get("PONTE_TESTE") == "1"          # só para o autoteste: aceita endereço local
DOWNLOADS = pathlib.Path(os.environ.get("PONTE_DOWNLOADS") or (pathlib.Path.home() / "Downloads"))
RECUSAS = (401, 403, 429, 451)
TETO_ARQUIVO = 60 * 2 ** 20        # um documento maior que isto não é trazido (o envio recusa acima de 100 MB)
TETO_LOTE = 250 * 2 ** 20          # por rodada
TETO_ENDERECOS = 200               # por rodada
POR_HOST = 25                      # por site, por rodada
PAUSA = 3.0                        # segundos entre dois pedidos ao mesmo site (ou o Crawl-delay dele, se maior)
TEMPO = 60
PRAZO_POR_ENDERECO = 180            # segundos, do pedido ao último byte: site que pinga devagar não prende a rodada
SEM_SINAL = 15 * 60                 # trava sem sinal há mais que isto é de rodada que morreu (janela fechada, queda)
DIAS_SEM_VOLTAR = {"recusa": 7, "nao_existe": 30}
NOME_DA_TAREFA = "MARE ponte no Brasil"
FALANTE = "--agora" in sys.argv or "--instalar" in sys.argv
SEM_JANELA = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def agora() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def dizer(msg: str, so_log: bool = False) -> None:
    linha = f"{dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  {msg}"
    try:
        arq = AQUI / "ponte.log"
        if arq.exists() and arq.stat().st_size > 1_000_000:
            arq.write_bytes(arq.read_bytes()[-300_000:])
        with open(arq, "a", encoding="utf-8") as f:
            f.write(linha + "\n")
    except OSError:
        pass
    if FALANTE and not so_log and sys.stdout is not None:
        try:
            print("  " + msg, flush=True)
        except Exception:  # noqa: BLE001 — console sem o caractere: o log já tem a linha
            pass


def ler_json(arq: pathlib.Path, padrao):
    try:
        return json.loads(arq.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return padrao


def gravar_json(arq: pathlib.Path, dado) -> None:
    tmp = arq.with_suffix(arq.suffix + ".novo")
    tmp.write_text(json.dumps(dado, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, arq)


def ident(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


# ── só endereço público; a lista nunca faz este computador pedir nada à rede de casa ─────────────

def endereco_publico(url: str, exigir_br: bool = True) -> bool:
    p = urllib.parse.urlparse(url)
    host = (p.hostname or "").lower()
    if p.scheme not in ("http", "https") or not host:
        return False
    if TESTE and host in ("127.0.0.1", "localhost"):
        return True
    if exigir_br and not host.endswith(".br"):
        return False
    try:
        ipaddress.ip_address(host)
        return False                      # endereço numérico nunca
    except ValueError:
        pass
    try:
        ips = {i[4][0] for i in socket.getaddrinfo(host, None)}
    except OSError:
        return True                       # não resolve: a busca falha e a falha é registrada
    return all(ipaddress.ip_address(i.split("%")[0]).is_global for i in ips)


class _SoPublico(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not endereco_publico(newurl, exigir_br=False):
            raise urllib.error.URLError(f"redirecionamento para endereço não público: {newurl[:80]}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_ABRIDOR = urllib.request.build_opener(_SoPublico(), urllib.request.HTTPSHandler(context=ssl.create_default_context()))

# ── cadeia de certificado incompleta (v4, 18/11/2026) ─────────────────────────────────────────────
# Alguns sites oficiais enviam o certificado sem o intermediário que o assinou (editor.amapa.gov.br e
# transparencia.ap.gov.br, medido em 18/11). O navegador busca o emissor no endereço que o próprio certificado
# declara ("CA Issuers"); o programa faz o mesmo e repete o pedido com a verificação plena. Nada afrouxa: o
# certificado autoassinado nunca se aprende, e o site só é lido num contexto que exige a cadeia inteira até
# uma raiz de confiança do sistema, o nome e a validade.
_APRENDIDOS = {}        # endereço "CA Issuers" -> certificado intermediário (PEM)
_ESTRITOS = {}          # site -> abridor com a cadeia completada
_OID_CA_ISSUERS = bytes.fromhex("06082b06010505073002")
CADEIA_INCOMPLETA = (2, 20, 21)


def _tlv(der: bytes, i: int) -> tuple:
    """(etiqueta, início do valor, fim do valor) do elemento DER que começa em `i`. Função pura."""
    n = der[i + 1]
    if n < 0x80:
        return der[i], i + 2, i + 2 + n
    q = n & 0x7F
    return der[i], i + 2 + q, i + 2 + q + int.from_bytes(der[i + 2:i + 2 + q], "big")


def emissor_e_titular(der: bytes) -> tuple:
    """(emissor, titular) de um certificado DER, em bytes; iguais, é autoassinado. Função pura."""
    _, i, _ = _tlv(der, 0)
    etiqueta, i, _ = _tlv(der, i)
    if etiqueta != 0x30:
        raise ValueError("não é certificado X.509")
    campos = []
    while len(campos) < 5:                     # série, algoritmo, EMISSOR, validade, TITULAR
        etiqueta, _, fim = _tlv(der, i)
        if etiqueta != 0xA0:                   # [0] versão, opcional
            campos.append(der[i:fim])
        i = fim
    return campos[2], campos[4]


def emissores_no_certificado(der: bytes) -> list:
    """Endereços http "CA Issuers" que o certificado DER declara. Função pura."""
    urls, i = [], der.find(_OID_CA_ISSUERS)
    while i != -1:
        j = i + len(_OID_CA_ISSUERS)
        if der[j:j + 1] == b"\x86":
            _, a, b = _tlv(der, j)
            urls.append(der[a:b].decode("ascii", "replace"))
        i = der.find(_OID_CA_ISSUERS, j)
    return [u for u in urls if re.match(r"http://[A-Za-z0-9.-]+\.[A-Za-z]{2,}(:\d+)?/", u)]


def completar_cadeia(host: str, porta: int = 443, tempo: int = 20, folha_fn=None, baixar_fn=None) -> bool:
    """Aprende o(s) intermediário(s) que o servidor não envia e monta o abridor do site. True se montou."""
    antes = len(_APRENDIDOS)
    try:
        if folha_fn:
            der = folha_fn(host, porta)
        else:
            sem = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)      # só para ler o certificado apresentado; nenhum pedido passa aqui
            sem.check_hostname, sem.verify_mode = False, ssl.CERT_NONE
            with socket.create_connection((host, porta), timeout=tempo) as s, sem.wrap_socket(s, server_hostname=host) as t:
                der = t.getpeercert(binary_form=True)
        for _ in range(3):
            url = next(iter(emissores_no_certificado(der)), None)
            if not url or url in _APRENDIDOS or not (baixar_fn or endereco_publico(url, exigir_br=False)):
                break
            if baixar_fn:
                der = baixar_fn(url)
            else:
                with _ABRIDOR.open(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=tempo) as r:
                    der = r.read(200_000)
            if der.lstrip().startswith(b"-----BEGIN"):
                der = ssl.PEM_cert_to_DER_cert(der.decode("ascii", "ignore"))
            emissor, titular = emissor_e_titular(der)
            if emissor == titular:
                break                          # raiz não se aprende da rede: âncora é só a do sistema
            pem = ssl.DER_cert_to_PEM_cert(der)
            ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT).load_verify_locations(cadata=pem)   # não carrega: levanta, e nada se aprende
            _APRENDIDOS[url] = pem
    except Exception:  # noqa: BLE001 — sem o intermediário, a verificação segue recusando como antes
        pass
    if len(_APRENDIDOS) == antes:
        return False
    ctx = ssl.create_default_context()
    ctx.verify_flags &= ~getattr(ssl, "VERIFY_X509_PARTIAL_CHAIN", 0)   # intermediário aprendido nunca é âncora
    ctx.load_verify_locations(cadata="".join(_APRENDIDOS.values()))
    _ESTRITOS[host] = urllib.request.build_opener(_SoPublico(), urllib.request.HTTPSHandler(context=ctx))
    return True


def _abrir(req, url: str, tempo: int):
    """Abre o pedido; cadeia de certificado incompleta é completada e o pedido se repete uma vez."""
    p = urllib.parse.urlparse(url)
    host = (p.hostname or "").lower()
    try:
        return _ESTRITOS.get(host, _ABRIDOR).open(req, timeout=tempo)
    except urllib.error.URLError as e:
        m = getattr(e, "reason", None)
        if not (isinstance(m, ssl.SSLCertVerificationError) and m.verify_code in CADEIA_INCOMPLETA
                and host not in _ESTRITOS and completar_cadeia(host, p.port or 443)):
            raise
        return _ESTRITOS[host].open(req, timeout=tempo)


def baixar(url: str, tempo: int = TEMPO, teto: int = TETO_ARQUIVO) -> dict:
    """Um GET com o cliente identificado. Devolve status, tipo, endereço final e corpo; levanta o erro."""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*", "From": "contato@monitorelnino.com.br"})
    fim = time.monotonic() + PRAZO_POR_ENDERECO
    with _abrir(req, url, tempo) as r:
        pedacos, lido = [], 0
        while True:
            bloco = r.read(256 * 1024)
            if not bloco:
                break
            pedacos.append(bloco)
            lido += len(bloco)
            if lido > teto:
                raise ValueError(f"maior que o teto de {teto // 2 ** 20} MB")
            if time.monotonic() > fim:
                raise TimeoutError(f"passou do prazo de {PRAZO_POR_ENDERECO} s")
        return {"status": r.status, "tipo": r.headers.get("Content-Type"), "final": r.geturl(), "corpo": b"".join(pedacos)}


def pausa_do_site(esquema: str, host: str) -> float:
    """O Crawl-delay que o robots.txt do site pede (até 60 s), nunca menos que PAUSA."""
    try:
        txt = baixar(f"{esquema}://{host}/robots.txt", tempo=15, teto=200_000)["corpo"].decode("utf-8", "replace")
    except Exception:  # noqa: BLE001 — sem robots legível, vale a pausa padrão
        return PAUSA
    pedidos = [float(x) for x in re.findall(r"(?im)^\s*crawl-delay\s*:\s*(\d+(?:\.\d+)?)", txt)]
    return min(max([PAUSA] + pedidos), 60.0)


# ── o que vai ao repositório público sai sem credencial nem CPF de terceiro ───────────────────────
# Os mesmos padrões da evidência preservada do MARÉ (coletores_base.PADROES_DE_SEGREDO e CPF), com a aspa
# que fecha a chave em JSON, a aspa escapada e a aspa em entidade HTML. Redige o VALOR, nunca o nome do campo.
_ASPA = r"(?:\\?[\"']|&quot;|&#0?3[49];)?"
_SEGREDOS = (
    (re.compile(r"((?:api[_-]?key|apikey|access[_-]?token|client[_-]?secret|secret[_-]?key|authorization)"
                + _ASPA + r"\s*[:=]\s*" + _ASPA + r")([A-Za-z0-9_\-\.]{16,})", re.I), r"\1[SEGREDO REDIGIDO]"),
    (re.compile(r"\b(AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_\-]{20,}|"
                r"sk-[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9\-]{10,})"), "[SEGREDO REDIGIDO]"),
)
_CPF = re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}")


def redigir(corpo: bytes) -> tuple:
    """(corpo a enviar, campos de redação). PDF e binário não se editam; página é redigida. Função pura."""
    if corpo[:5] == b"%PDF-" or b"\x00" in corpo[:4096]:
        return corpo, {}
    try:
        texto, codificacao = corpo.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        texto, codificacao = corpo.decode("latin-1"), "latin-1"
    segredos = 0
    for padrao, troca_ in _SEGREDOS:
        texto, k = padrao.subn(troca_, texto)
        segredos += k
    texto, cpfs = _CPF.subn("[CPF REDIGIDO]", texto)
    if not (segredos or cpfs):
        return corpo, {}
    return texto.encode(codificacao), {"sha256_de_origem": hashlib.sha256(corpo).hexdigest(),
                                       "segredos_redigidos": segredos, "cpfs_redigidos": cpfs}


# ── as cópias legíveis, nesta pasta ───────────────────────────────────────────────────────────────

def extensao(corpo: bytes, tipo: str = "") -> str:
    c = corpo[:600].lstrip().lower()
    if corpo[:5] == b"%PDF-":
        return "pdf"
    if c.startswith(b"<!doctype html") or c.startswith(b"<html") or b"<head" in c or "html" in (tipo or ""):
        return "html"
    if c[:1] in (b"{", b"["):
        return "json"
    if c.startswith(b"<?xml") or "xml" in (tipo or ""):
        return "xml"
    return "bin"


def nome_legivel(url: str, corpo: bytes, tipo: str = "") -> str:
    p = urllib.parse.urlparse(url)
    base = urllib.parse.unquote(p.path.rstrip("/").rsplit("/", 1)[-1]) or "pagina-inicial"
    base = re.sub(r"\.(pdf|html?|php|aspx?|json|xml)$", "", base, flags=re.I)
    base = re.sub(r"[^\w.\-]+", "_", base, flags=re.UNICODE).strip("._")[:70] or "pagina"
    return f"{base}__{ident(url)[:6]}.{extensao(corpo, tipo)}"


def guardar_copia(url: str, corpo: bytes, tipo: str = "") -> None:
    host = (urllib.parse.urlparse(url).hostname or "site").lower()
    pasta = AQUI / "copias" / re.sub(r"[^\w.\-]+", "_", host)
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / nome_legivel(url, corpo, tipo)).write_bytes(corpo)


def abrir_conteiner(arq: pathlib.Path) -> int:
    """Arquivo que o navegador do app deixou: se for o pacote da ponte (PONT + índice + corpos), abre os
    documentos em "copias"; se for um documento solto, ganha a extensão certa. Devolve documentos abertos."""
    try:
        b = arq.read_bytes()
    except OSError:
        return 0
    if b[:4] != b"PONT" or len(b) < 8:
        ext = extensao(b)
        if ext != "bin":
            try:
                arq.rename(arq.with_suffix("." + ext))
            except OSError:
                pass
        return 0
    try:
        n = struct.unpack(">I", b[4:8])[0]
        cab = json.loads(b[8:8 + n].decode("utf-8"))
        corpos, abertos = b[8 + n:], 0
        for it in cab.get("itens") or []:
            if it.get("status") == 200 and it.get("bytes"):
                guardar_copia(it["url"], corpos[it["pos"]:it["pos"] + it["bytes"]], it.get("tipo") or "")
                abertos += 1
        return abertos
    except Exception as e:  # noqa: BLE001 — pacote ilegível fica como está
        dizer(f"pacote ilegível: {arq.name} ({type(e).__name__})", so_log=True)
        return 0


def varrer_downloads() -> tuple:
    """Leva de Downloads para "navegador", nesta pasta, tudo o que a ponte deixou lá (ponte_*.bin)."""
    levados = abertos = 0
    try:
        achados = sorted(f for f in DOWNLOADS.glob("ponte_*.bin") if f.is_file())
    except OSError:
        achados = []
    for f in achados:
        destino = AQUI / "navegador"
        destino.mkdir(exist_ok=True)
        alvo = destino / f.name
        if alvo.exists():
            alvo = destino / f"{f.stem}__{int(f.stat().st_mtime)}{f.suffix}"
        try:
            shutil.move(str(f), str(alvo))
        except OSError as e:
            dizer(f"não consegui levar {f.name}: {e}", so_log=True)
            continue
        levados += 1
        abertos += abrir_conteiner(alvo)
    return levados, abertos


# ── a rodada ──────────────────────────────────────────────────────────────────────────────────────

def a_buscar(ordem: dict, estado: dict, hoje: dt.datetime) -> list:
    """Os endereços da lista que ainda cabe buscar, na ordem da lista. Função pura."""
    nao_pedir = {h.lower() for h in ordem.get("nao_pedir") or []}
    for h, quando in (estado.get("sites_que_recusaram") or {}).items():
        if (hoje - dt.datetime.fromisoformat(quando)).days < DIAS_SEM_VOLTAR["recusa"]:
            nao_pedir.add(h)                 # o site disse não: recusa se respeita, e não se insiste
    feitos, saida, vistos = estado.get("feitos") or {}, [], set()
    for it in ordem.get("buscar") or []:
        url = (it.get("url") if isinstance(it, dict) else it) or ""
        host = (urllib.parse.urlparse(url).hostname or "").lower()
        if not url or url in vistos or host in nao_pedir:
            continue
        vistos.add(url)
        f = feitos.get(ident(url))
        if f:
            quando = dt.datetime.fromisoformat(f["em"])
            horas = (hoje - quando).total_seconds() / 3600
            frescor = it.get("frescor_h") if isinstance(it, dict) else None
            if f["resultado"] == "ok" and not (frescor and horas >= frescor):
                continue
            if f["resultado"] in DIAS_SEM_VOLTAR and horas < 24 * DIAS_SEM_VOLTAR[f["resultado"]]:
                continue
            if f["resultado"] == "erro" and f.get("tentativas", 1) >= 6 and horas < 24:
                continue
        saida.append(url)
    return saida[:TETO_ENDERECOS]


def rodada(estado: dict) -> dict:
    resumo = {"pedidos": 0, "trazidos": 0, "recusas": 0, "nao_existem": 0, "erros": 0, "lote": None}
    try:
        ordem = json.loads(baixar(ORDEM, tempo=30, teto=5_000_000)["corpo"].decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        dizer(f"não li a lista de endereços ({type(e).__name__}: {str(e)[:80]}); tento na próxima hora")
        resumo["sem_lista"] = True
        return resumo
    if isinstance(ordem, list):
        ordem = {"buscar": ordem}
    urls = a_buscar(ordem, estado, agora())
    resumo["pedidos"] = len(urls)
    if not urls:
        dizer("lista lida: nada novo a buscar")
        return resumo
    dizer(f"lista lida: {len(urls)} endereço(s) a buscar (leva alguns minutos; cada linha abaixo é um endereço)")
    carimbo = agora().strftime("%Y%m%d-%H%M%S")
    pasta = AQUI / "saida" / carimbo
    pasta.mkdir(parents=True, exist_ok=True)
    itens, tamanho, por_host, pausas, ultimo, recusou = [], 0, {}, {}, {}, set()
    feitos = estado.setdefault("feitos", {})
    for url in urls:
        p = urllib.parse.urlparse(url)
        host = (p.hostname or "").lower()
        if host in recusou or por_host.get(host, 0) >= POR_HOST or tamanho >= TETO_LOTE:
            continue
        it = {"url": url, "em": agora().isoformat(timespec="seconds")}
        if not endereco_publico(url):
            it["erro"] = "endereço fora da regra (só site público .br)"
            resultado = "nao_existe"
        else:
            if host not in pausas:
                pausas[host] = pausa_do_site(p.scheme, host)
            espera = pausas[host] - (time.time() - ultimo.get(host, 0))
            if espera > 0:
                time.sleep(espera)
            por_host[host] = por_host.get(host, 0) + 1
            try:
                r = baixar(url)
                corpo = r.pop("corpo")
                if corpo:
                    guardar_copia(url, corpo, r.get("tipo") or "")       # nesta pasta, como veio
                    corpo, redacao = redigir(corpo)                      # ao repositório, sem credencial nem CPF
                    it.update(r, bytes=len(corpo), sha256=hashlib.sha256(corpo).hexdigest(), **redacao)
                    (pasta / it["sha256"]).write_bytes(corpo)
                    tamanho += len(corpo)
                    resultado = "ok"
                else:
                    it.update(r, bytes=0)
                    it["erro"], resultado = "corpo vazio", "erro"
            except urllib.error.HTTPError as e:
                it["status"] = e.code
                if e.code in RECUSAS:
                    it["recusa"], resultado = True, "recusa"
                    recusou.add(host)       # o site disse não: nada mais se pede a ele, nesta rodada e por 7 dias
                    estado.setdefault("sites_que_recusaram", {})[host] = it["em"]
                elif e.code in (404, 410):
                    resultado = "nao_existe"
                else:
                    it["erro"], resultado = f"HTTP {e.code}", "erro"
            except Exception as e:  # noqa: BLE001 — rede, certificado, tempo esgotado, teto
                it["erro"], resultado = f"{type(e).__name__}: {str(e)[:120]}", "erro"
            ultimo[host] = time.time()
        itens.append(it)
        ant = feitos.get(ident(url)) or {}
        feitos[ident(url)] = {"em": it["em"], "resultado": resultado, "lote": carimbo,
                              "tentativas": ant.get("tentativas", 0) + 1 if resultado == "erro" else 1}
        chave = {"ok": "trazidos", "recusa": "recusas", "nao_existe": "nao_existem", "erro": "erros"}[resultado]
        resumo[chave] += 1
        gravar_json(pasta / "manifesto.json", {"ponte_local": VERSAO, "cliente": UA, "gerado_em": it["em"], "itens": itens})
        gravar_json(AQUI / "estado.json", estado)
        sinal()
        dizer(f"{resultado:<10} {url[:110]}" + (f"  [{it.get('erro') or it.get('status')}]" if resultado != "ok" else ""), so_log=not FALANTE)
    gravar_json(pasta / "manifesto.json", {"ponte_local": VERSAO, "cliente": UA, "gerado_em": agora().isoformat(timespec="seconds"),
                                           "itens": itens})
    resumo["lote"] = carimbo
    return resumo


# ── o envio ao projeto ────────────────────────────────────────────────────────────────────────────

def achar_git():
    g = shutil.which("git")
    if g:
        return g
    for c in (r"C:\Program Files\Git\cmd\git.exe", r"C:\Program Files (x86)\Git\cmd\git.exe",
              os.path.expandvars(r"%LOCALAPPDATA%\Programs\Git\cmd\git.exe")):
        if os.path.exists(c):
            return c
    return None


def apagar_pasta(pasta: pathlib.Path) -> None:
    def solta(func, caminho, _):
        try:
            os.chmod(caminho, stat.S_IWRITE)
            func(caminho)
        except OSError:
            pass
    shutil.rmtree(pasta, onerror=solta)


def enviar(pasta: pathlib.Path) -> tuple:
    """Envia o lote como um ramo ponte-local/<carimbo> do repositório do projeto. Nunca abre janela de
    senha: sem acesso gravado neste computador, o lote fica em "saida" e o Claude o recolhe."""
    git = achar_git()
    if not git:
        return False, "git não encontrado"
    rep = AQUI / "envio"
    if rep.exists():
        apagar_pasta(rep)
    (rep / "ponte-local" / pasta.name).mkdir(parents=True)
    for f in pasta.iterdir():
        if f.is_file():
            shutil.copy2(f, rep / "ponte-local" / pasta.name / f.name)
    (rep / ".gitattributes").write_text("* -text\n", encoding="ascii")   # o byte que veio é o byte que vai
    amb = dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="Never", GIT_ASKPASS="echo",
               GIT_AUTHOR_NAME="MARE ponte no Brasil", GIT_AUTHOR_EMAIL="ponte@monitorelnino.com.br",
               GIT_COMMITTER_NAME="MARE ponte no Brasil", GIT_COMMITTER_EMAIL="ponte@monitorelnino.com.br")

    def g(*args, tempo=180):
        return subprocess.run([git, "-c", "core.autocrlf=false", "-c", "core.safecrlf=false", "-C", str(rep), *args],
                              capture_output=True, text=True, env=amb, timeout=tempo, creationflags=SEM_JANELA)
    try:
        for passo in (("init", "-q"), ("add", "-A")):
            r = g(*passo)
            if r.returncode:
                return False, f"git {passo[0]}: {r.stderr.strip()[-200:]}"
        arvore = g("write-tree").stdout.strip()
        commit = g("commit-tree", arvore, "-m", f"Ponte local {pasta.name}").stdout.strip()
        if not commit:
            return False, "git commit-tree não devolveu commit"
        r = g("push", "-q", REMOTO, f"{commit}:refs/heads/ponte-local/{pasta.name}", tempo=1200)
        return (r.returncode == 0), (r.stderr.strip()[-300:] if r.returncode else "")
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}: {str(e)[:160]}"
    finally:
        apagar_pasta(rep)


def enviar_pendentes(estado: dict) -> tuple:
    enviados, falha = 0, ""
    saida = AQUI / "saida"
    for pasta in sorted(saida.iterdir()) if saida.exists() else []:
        if not (pasta / "manifesto.json").exists():
            continue
        ok, falha = enviar(pasta)
        if not ok:
            dizer(f"lote {pasta.name} não enviado ({falha}); fica guardado em 'saida'")
            break
        enviados += 1
        estado.setdefault("lotes", {})[pasta.name] = {"enviado_em": agora().isoformat(timespec="seconds")}
        apagar_pasta(pasta)      # as cópias legíveis seguem em "copias"
        dizer(f"lote {pasta.name} enviado ao projeto")
    return enviados, falha


# ── a tarefa do Windows ───────────────────────────────────────────────────────────────────────────

def instalar() -> bool:
    if os.name != "nt":
        dizer("instalação só existe no Windows")
        return False
    exe = pathlib.Path(sys.executable)
    pyw = exe.with_name("pythonw.exe")
    comando = str(pyw if pyw.exists() else exe)
    usuario = "\\".join(x for x in (os.environ.get("USERDOMAIN"), os.environ.get("USERNAME")) if x)
    inicio = (dt.datetime.now() + dt.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:00")
    xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo><Description>MARE - ponte no Brasil: busca, deste computador, documentos publicos que nao abrem para o robo do MARE fora do pais. Para desinstalar: DESINSTALAR_PONTE.cmd em {_x(str(AQUI))}</Description></RegistrationInfo>
  <Triggers><TimeTrigger><StartBoundary>{inicio}</StartBoundary><Enabled>true</Enabled><Repetition><Interval>PT1H</Interval><StopAtDurationEnd>false</StopAtDurationEnd></Repetition></TimeTrigger></Triggers>
  <Principals><Principal id="Author">{"<UserId>" + _x(usuario) + "</UserId>" if usuario else ""}<LogonType>InteractiveToken</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal></Principals>
  <Settings><MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy><DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries><StopIfGoingOnBatteries>false</StopIfGoingOnBatteries><StartWhenAvailable>true</StartWhenAvailable><RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable><ExecutionTimeLimit>PT1H</ExecutionTimeLimit><Enabled>true</Enabled></Settings>
  <Actions Context="Author"><Exec><Command>{_x(comando)}</Command><Arguments>"{_x(str(AQUI / 'ponte_local.py'))}"</Arguments><WorkingDirectory>{_x(str(AQUI))}</WorkingDirectory></Exec></Actions>
</Task>
"""
    arq = AQUI / "tarefa.xml"
    try:
        arq.write_text(xml, encoding="utf-16")
        r = subprocess.run(["schtasks", "/Create", "/F", "/TN", NOME_DA_TAREFA, "/XML", str(arq)], capture_output=True, text=True)
        if r.returncode:
            dizer(f"forma completa recusada ({(r.stderr or r.stdout).strip()[:120]}); tento a forma simples", so_log=True)
            r = subprocess.run(["schtasks", "/Create", "/F", "/SC", "HOURLY", "/TN", NOME_DA_TAREFA,
                                "/TR", f'"{comando}" "{AQUI / "ponte_local.py"}"'], capture_output=True, text=True)
        if r.returncode:
            dizer(f"NÃO consegui criar a tarefa do Windows: {(r.stderr or r.stdout).strip()[:200]}")
            return False
        dizer("tarefa do Windows criada: roda de hora em hora, com o computador ligado")
        return True
    finally:
        try:
            arq.unlink()
        except OSError:
            pass


def sinal() -> None:
    """A rodada em curso renova a trava a cada endereço; trava sem sinal é de rodada que morreu."""
    try:
        (AQUI / "rodando.lock").write_text(str(os.getpid()), encoding="ascii")
    except OSError:
        pass


def trava() -> bool:
    arq = AQUI / "rodando.lock"
    try:
        if arq.exists() and time.time() - arq.stat().st_mtime < SEM_SINAL:
            return False
    except OSError:
        pass
    sinal()
    return True


def limpar_restos() -> None:
    """Lote que ficou sem manifesto (rodada interrompida antes da v3) não tem como ser conferido: sai, e os
    endereços dele voltam na lista. A trava antiga também sai."""
    saida = AQUI / "saida"
    for pasta in sorted(saida.iterdir()) if saida.exists() else []:
        if pasta.is_dir() and not (pasta / "manifesto.json").exists():
            apagar_pasta(pasta)
    try:
        (AQUI / "em_execucao.lock").unlink()
    except OSError:
        pass


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    if FALANTE and sys.stdout is not None:
        print("\n  MARÉ — ponte no Brasil\n", flush=True)
    instalou = instalar() if "--instalar" in sys.argv else None
    if not trava():
        dizer("a ponte já está rodando agora (em outra janela ou pela tarefa do Windows); esta janela pode fechar")
        return 0
    if FALANTE and sys.stdout is not None:
        print("  Deixe esta janela aberta até aparecer \"Pronto\". Se fechar antes, nada se perde:\n"
              "  a tarefa do Windows continua sozinha, de onde parou, na próxima hora.\n", flush=True)
    try:
        limpar_restos()
        estado = ler_json(AQUI / "estado.json", {})
        levados, abertos = varrer_downloads()
        if levados:
            dizer(f"levei {levados} arquivo(s) da ponte de Downloads para {AQUI / 'navegador'} ({abertos} documento(s) abertos em 'copias')")
        resumo = rodada(estado)
        gravar_json(AQUI / "estado.json", estado)
        enviados, falha = enviar_pendentes(estado)
        gravar_json(AQUI / "estado.json", estado)
        resumo.update(em=agora().isoformat(timespec="seconds"), versao=VERSAO, levados_de_downloads=levados,
                      lotes_enviados=enviados, falha_de_envio=falha or None,
                      lotes_guardados=sorted(p.name for p in (AQUI / "saida").iterdir()) if (AQUI / "saida").exists() else [])
        gravar_json(AQUI / "ultimo.json", resumo)
        dizer(f"resultado: {resumo['trazidos']} documento(s) trazido(s); {resumo['recusas']} recusa(s) de site, respeitada(s); "
              f"{resumo['nao_existem']} endereço(s) que não existem mais; {resumo['erros']} sem resposta agora (o programa tenta de novo)")
        if resumo["lotes_guardados"]:
            dizer(f"envio ao projeto: ficou guardado nesta pasta, e o Claude recolhe ({falha or 'sem envio'})")
        elif enviados:
            dizer("envio ao projeto: feito")
        if FALANTE and sys.stdout is not None:
            print("\n  Pronto. Pode fechar esta janela." if instalou is not False else
                  "\n  A tarefa do Windows NÃO foi criada. Avise o Claude: \"a tarefa não foi criada\".", flush=True)
        return 0
    finally:
        try:
            (AQUI / "rodando.lock").unlink()
        except OSError:
            pass


# ── autoteste, sem rede de fora: um servidor local faz as vezes dos sites ─────────────────────────

def autoteste() -> int:
    import http.server
    import tempfile
    import threading
    global AQUI, ORDEM, REMOTO, DOWNLOADS, TESTE, PAUSA
    falhas = []

    class S(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            c, corpo, tipo = 200, b"", "text/html"
            if self.path == "/ordem.json":
                corpo, tipo = json.dumps(S.ordem).encode(), "application/json"
            elif self.path == "/doc.pdf":
                corpo, tipo = b"%PDF-1.7\r\nlinha com CRLF\r\n", "application/pdf"
            elif self.path == "/pagina":
                corpo = (b"<!doctype html>\r\n<html><body>p\xc3\xa1gina<script>var f={\"access_token\":\"IGQVJVabcdefghij0123456789\"};"
                         b"</script> CPF 123.456.789-09</body></html>\r\n")
            elif self.path == "/recusa":
                c = 403
            elif self.path == "/sumiu":
                c = 404
            elif self.path == "/robots.txt":
                corpo, tipo = b"User-agent: *\nCrawl-delay: 0\n", "text/plain"
            else:
                c = 500
            S.vistos.append((self.path, self.headers.get("User-Agent")))
            self.send_response(c)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)
    S.vistos = []
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), S)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_port}"
    S.ordem = {"buscar": [{"url": base + "/doc.pdf"}, {"url": base + "/pagina"}, {"url": base + "/sumiu"},
                          {"url": base + "/recusa"}, {"url": base + "/depois-da-recusa"}, {"url": "http://192.168.0.1/roteador"},
                          {"url": "https://exemplo.com/fora-do-br"}], "nao_pedir": []}
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        AQUI, DOWNLOADS, TESTE, PAUSA = tmp / "ponte", tmp / "Downloads", True, 0.0
        AQUI.mkdir()
        DOWNLOADS.mkdir()
        ORDEM, REMOTO = base + "/ordem.json", str(tmp / "remoto.git")
        # um pacote do navegador e um documento solto, esquecidos em Downloads
        cab = json.dumps({"ponte": 1, "itens": [{"url": "https://www.x.gov.br/a/plano.pdf", "status": 200, "pos": 0, "bytes": 9, "tipo": "application/pdf"}]}).encode()
        (DOWNLOADS / "ponte_www.x.gov.br.bin").write_bytes(b"PONT" + struct.pack(">I", len(cab)) + cab + b"%PDF-1.4\n")
        (DOWNLOADS / "ponte_7.bin").write_bytes(b"%PDF-1.4 solto")
        (DOWNLOADS / "outro.bin").write_bytes(b"nao e da ponte")
        estado = {}
        levados, abertos = varrer_downloads()
        if (levados, abertos) != (2, 1) or not (DOWNLOADS / "outro.bin").exists() or not (AQUI / "navegador" / "ponte_7.pdf").exists() \
                or not list((AQUI / "copias" / "www.x.gov.br").glob("plano__*.pdf")):
            falhas.append(f"varredura de Downloads: {levados}, {abertos}")
        r = rodada(estado)
        if (r["trazidos"], r["recusas"], r["nao_existem"], r["erros"]) != (2, 1, 3, 0):
            falhas.append(f"contagem da rodada: {r}")
        pedidos = [p for p, _ in S.vistos]
        if "/depois-da-recusa" in pedidos:
            falhas.append("pediu ao site depois da recusa")
        if any("roteador" in p or "fora-do-br" in p for p in pedidos):
            falhas.append("pediu endereço fora da regra")
        if not all((ua or "").startswith("MonitorElNinoBrasil/") for _, ua in S.vistos):
            falhas.append("cliente não identificado em algum pedido")
        man = ler_json(AQUI / "saida" / r["lote"] / "manifesto.json", {})
        pdf = next((i for i in man.get("itens", []) if i["url"].endswith("/doc.pdf")), {})
        if pdf.get("sha256") != hashlib.sha256(b"%PDF-1.7\r\nlinha com CRLF\r\n").hexdigest():
            falhas.append("sha256 do manifesto não é o do corpo")
        pag = next((i for i in man.get("itens", []) if i["url"].endswith("/pagina")), {})
        enviado = (AQUI / "saida" / r["lote"] / pag.get("sha256", "x")).read_bytes() if pag.get("sha256") else b""
        guardada = b"".join(f.read_bytes() for f in (AQUI / "copias" / "127.0.0.1").glob("pagina__*.html"))
        if b"IGQVJV" in enviado or b"123.456.789-09" in enviado or pag.get("segredos_redigidos") != 1 or pag.get("cpfs_redigidos") != 1 \
                or b"[SEGREDO REDIGIDO]" not in enviado or not pag.get("sha256_de_origem") or b"IGQVJV" not in guardada:
            falhas.append(f"redação antes do envio: {pag}")
        if a_buscar(S.ordem, estado, agora()) != []:
            falhas.append(f"pediria ao site que recusou: {a_buscar(S.ordem, estado, agora())}")
        estado["sites_que_recusaram"] = {}
        if a_buscar(S.ordem, estado, agora()) != [base + "/depois-da-recusa"]:
            falhas.append(f"segunda rodada pediria de novo: {a_buscar(S.ordem, estado, agora())}")
        S.ordem["buscar"][1]["frescor_h"] = 0.0001
        time.sleep(0.5)
        if base + "/pagina" not in a_buscar(S.ordem, estado, agora()):
            falhas.append("página com frescor vencido não volta à lista")
        (AQUI / "saida" / "resto-sem-manifesto").mkdir()
        (AQUI / "saida" / "resto-sem-manifesto" / "abc").write_bytes(b"x")
        (AQUI / "em_execucao.lock").write_text("1", encoding="ascii")
        limpar_restos()
        if (AQUI / "saida" / "resto-sem-manifesto").exists() or (AQUI / "em_execucao.lock").exists() \
                or not (AQUI / "saida" / r["lote"] / "manifesto.json").exists():
            falhas.append("limpeza dos restos de rodada interrompida")
        if trava():
            falhas.append("trava: a rodada acabou de dar sinal, e outra não pode começar")
        (AQUI / "rodando.lock").unlink()
        if not trava() or trava():
            falhas.append("trava: a primeira chamada tem de pegar e a segunda, com sinal fresco, não")
        os.utime(AQUI / "rodando.lock", (time.time() - SEM_SINAL - 5,) * 2)
        if not trava():
            falhas.append("trava sem sinal há mais de 15 min tem de ser tomada")
        if ler_json(AQUI / "estado.json", {}).get("feitos") != estado.get("feitos"):
            falhas.append("o estado não foi gravado a cada endereço")
        git = achar_git()
        if git:
            subprocess.run([git, "init", "-q", "--bare", REMOTO], check=True, capture_output=True)
            enviados, falha = enviar_pendentes(estado)
            ramos = subprocess.run([git, "-C", REMOTO, "for-each-ref", "--format=%(refname)"], capture_output=True, text=True).stdout
            if enviados != 1 or f"refs/heads/ponte-local/{r['lote']}" not in ramos:
                falhas.append(f"envio: {enviados}, {falha}, {ramos}")
            else:
                blob = subprocess.run([git, "-C", REMOTO, "cat-file", "blob", f"ponte-local/{r['lote']}:ponte-local/{r['lote']}/{pdf['sha256']}"], capture_output=True).stdout
                if hashlib.sha256(blob).hexdigest() != pdf["sha256"]:
                    falhas.append("o byte enviado não é o byte trazido (conversão de fim de linha)")
                autor = subprocess.run([git, "-C", REMOTO, "log", "-1", "--format=%an <%ae>", f"ponte-local/{r['lote']}"], capture_output=True, text=True).stdout.strip()
                if autor != "MARE ponte no Brasil <ponte@monitorelnino.com.br>":
                    falhas.append(f"autor do envio: {autor}")
                if (AQUI / "saida" / r["lote"]).exists() or (AQUI / "envio").exists():
                    falhas.append("lote enviado não saiu de 'saida' ou sobrou a pasta de envio")
        if not list((AQUI / "copias" / "127.0.0.1").glob("doc__*.pdf")):
            falhas.append("cópia legível do documento não ficou em 'copias'")
    srv.shutdown()
    # cadeia de certificado: só intermediário se aprende; raiz e resposta que não é certificado ficam de fora
    folha = b"0" + _OID_CA_ISSUERS + b"\x86" + bytes([27]) + b"http://ca.exemplo.com/x.crt"
    if emissores_no_certificado(folha) != ["http://ca.exemplo.com/x.crt"] or emissores_no_certificado(b"") != []:
        falhas.append("endereço do emissor não lido do certificado")

    def autoassinado(c):
        try:
            e, tit = emissor_e_titular(c)
            return e == tit
        except Exception:  # noqa: BLE001
            return False
    raiz = next((c for c in ssl.create_default_context().get_ca_certs(binary_form=True) if autoassinado(c)), None)
    if raiz is not None and completar_cadeia("site.gov.br", folha_fn=lambda h, pt: folha, baixar_fn=lambda u: raiz):
        falhas.append("raiz vinda da rede foi aprendida")
    if completar_cadeia("site.gov.br", folha_fn=lambda h, pt: folha, baixar_fn=lambda u: b"<html>pagina</html>"):
        falhas.append("resposta que não é certificado foi aprendida")
    if _APRENDIDOS or _ESTRITOS:
        falhas.append("o teste da cadeia deixou certificado aprendido")
    print("autoteste da ponte local:", "OK" if not falhas else "FALHOU")
    for f in falhas:
        print("  -", f)
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
