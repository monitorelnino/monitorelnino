#!/usr/bin/env python3
"""Busca de planos municipais de contingência em fontes abertas por município (22/10/2026,
HANDOVER_REPOSITORIOS_DE_PLANOS_MUNICIPAIS §1.9–§1.11; matriz S13, S16, S25, S29).

Quatro consultas por município, todas a APIs públicas, sem login, sem LAI, sem chave:
  S13  LexML (SRU)               legislação que cita o plano do município
  S16  Wayback Machine (CDX)     cópias arquivadas do domínio da prefeitura com plano/PLANCON no endereço
  S25  Common Crawl (índice)     o mesmo, no índice de rastreio aberto; o arquivo só se baixa da origem
  S29  dados.gov.br (CKAN)       conjuntos de dados que citam o plano do município

Disciplina: cliente identificado, robots e Crawl-delay pela `buscar_uma_vez`, pausa por host, e
401/403/429/451 ou muro de robô são RECUSA registrada (nunca retentativa). Resposta que não se
entende é `erro`, nunca `sem_resultado`: ausência de achado só vale com a consulta registrada.

Trava estrutural: nunca escreve em estados.json, saude_uf.json, municipios.json, indice.json nem
monitor_saude.json. Trava de campo: toda pista nasce com `documento_oficial_confirmado: null` e
`promovivel: false`. Trava de processo: a saída vai à porta única (`scripts/pistas.gravar_lote`) e ao
juiz; a camada declarada nunca vira documento. O resultado por município/fonte fica em
`data/planos_busca_fontes.json`, que só este script escreve.

Uso:
  python3 buscar_planos_fontes_abertas.py --autoteste
  python3 buscar_planos_fontes_abertas.py --alvos data/capitais_alvos.json [--fontes S16,S25] [--limite N]
"""
import io
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import xml.etree.ElementTree as ET

from coletores_base import (buscar_uma_vez, ler, gravar, hoje_editorial, referencia_ibge,
                            rodar_autoteste, registrar_lacuna, MuroDeRobo)
from descobrir_planos import dominios_do_municipio, identifica_prefeitura, RECUSAS_DE_FONTE
from consultar_querido_diario import STATUS_DA_PISTA
from scripts.pistas import gravar_lote

RESULTADO = "planos_busca_fontes.json"
PAUSA = 2.0
TETO_POR_FONTE = 5
PADRAO_PLANO = re.compile(r"plancon|placon|conting[eê]nc|plano[-_ /]*municipal[-_ /]*de[-_ /]*defesa|pdec", re.I)
# Capitais cujo endereço padrão `<município>.<uf>.gov.br` não é o da prefeitura: candidatos a VERIFICAR
# (só valem se a home se identifica como a prefeitura, como em `descobrir_no_portal`).
CANDIDATOS_EXTRA = {
    "3106200": ["prefeitura.pbh.gov.br"], "5300108": ["df.gov.br"], "1501402": ["belem.pa.gov.br"],
    "2611606": ["recife.pe.gov.br"], "2211001": ["pmt.pi.gov.br"], "3304557": ["prefeitura.rio"],
    "2408102": ["natal.rn.gov.br"], "4314902": ["prefeitura.poa.br"], "4205407": ["pmf.sc.gov.br"],
}


# ---- consultas e leitores (puros) --------------------------------------------------------------
def consulta_wayback(dominio: str) -> str:
    q = {"url": dominio, "matchType": "domain", "output": "json", "fl": "original,timestamp,mimetype",
         "filter": ["statuscode:200", "original:.*(plancon|placon|contingenc).*"], "collapse": "urlkey", "limit": 30}
    return "https://web.archive.org/cdx/search/cdx?" + urllib.parse.urlencode(q, doseq=True)


def ler_wayback(corpo: bytes) -> list:
    """[(url, titulo)]: a cópia arquivada de cada endereço. Levanta ValueError se o corpo não é CDX."""
    linhas = json.loads(corpo.decode("utf-8") or "[]")
    if linhas and linhas[0] != ["original", "timestamp", "mimetype"]:
        raise ValueError("cabeçalho CDX inesperado")
    return [(f"https://web.archive.org/web/{ts}/{orig}", f"Cópia arquivada: {orig}")
            for orig, ts, _ in linhas[1:] if PADRAO_PLANO.search(orig)]


def indice_common_crawl(collinfo: bytes) -> str:
    """O `cdx-api` do rastreio mais novo. Levanta ValueError se a lista vier vazia."""
    lista = json.loads(collinfo.decode("utf-8"))
    return sorted(lista, key=lambda c: c["id"])[-1]["cdx-api"]


def consulta_common_crawl(api: str, dominio: str) -> str:
    q = {"url": f"{dominio}/*", "output": "json", "fl": "url,status,mime",
         "filter": ["=status:200", "url:.*(plancon|placon|contingenc).*"], "limit": 30}
    return api + "?" + urllib.parse.urlencode(q, doseq=True)


def sem_capturas(e: Exception) -> bool:
    """O índice do Common Crawl responde 404 com "No Captures found" quando o domínio não tem captura que
    case: é resposta (ausência com a consulta registrada), não falha. 404 sem essa frase continua erro."""
    if not (isinstance(e, urllib.error.HTTPError) and e.code == 404 and e.fp is not None):
        return False
    return b"no captures found" in e.read().lower()


def ler_common_crawl(corpo: bytes) -> list:
    achados = []
    for linha in corpo.decode("utf-8").splitlines():
        if linha.strip():
            url = json.loads(linha)["url"]
            if PADRAO_PLANO.search(url):
                achados.append((url, f"Rastreio aberto: {url}"))
    return list(dict.fromkeys(achados))


def consulta_lexml(nome: str) -> str:
    cql = f'"plano de contingência" and "{nome}"'
    return "https://www.lexml.gov.br/busca/SRU?" + urllib.parse.urlencode(
        {"operation": "searchRetrieve", "version": "1.1", "query": cql, "maximumRecords": 10})


def ler_lexml(corpo: bytes, nome: str) -> list:
    """[(url, título)] dos registros que citam o município e o plano. Levanta ValueError se não é SRU."""
    raiz = ET.fromstring(corpo)
    if not raiz.tag.endswith("searchRetrieveResponse"):
        raise ValueError("resposta não é SRU")
    achados = []
    for reg in (e for e in raiz.iter() if e.tag.endswith("}recordData") or e.tag == "recordData"):
        campos = {}
        for e in reg.iter():
            tag = e.tag.rsplit("}", 1)[-1]
            if e.text and e.text.strip():
                campos.setdefault(tag, e.text.strip())
        titulo = campos.get("title") or campos.get("description") or ""
        url = campos.get("urn") and "https://www.lexml.gov.br/urn/" + campos["urn"] or campos.get("identifier") or ""
        if url and PADRAO_PLANO.search(titulo) and cita(titulo + " " + campos.get("urn", ""), nome):
            achados.append((url, titulo[:200]))
    return achados


def consulta_ckan(nome: str) -> str:
    return "https://dados.gov.br/api/3/action/package_search?" + urllib.parse.urlencode(
        {"q": f'"plano de contingência" "{nome}"', "rows": 10})


def ler_ckan(corpo: bytes, nome: str) -> list:
    dados = json.loads(corpo.decode("utf-8"))
    if not dados.get("success"):
        raise ValueError("CKAN sem success")
    achados = []
    for p in dados["result"]["results"]:
        texto = f'{p.get("title", "")} {p.get("notes", "")}'
        if PADRAO_PLANO.search(texto) and cita(texto, nome):
            achados.append((f'https://dados.gov.br/dados/conjuntos-dados/{p.get("name", "")}', p.get("title", "")[:200]))
    return achados


def cita(texto: str, nome: str) -> bool:
    """O nome do município aparece como palavra inteira (não dentro de outra palavra). Pura.
    Homônimo composto ("Alfa Verde") passa: quem decide é o juiz, a pista só agrupa candidatos."""
    t = " ".join(re.sub(r"\W+", " ", texto.lower()).split())
    n = " ".join(re.sub(r"\W+", " ", nome.lower()).split())
    return bool(re.search(rf"\b{re.escape(n)}\b", t))


def classificar_erro(e: Exception) -> tuple:
    """(situacao, motivo): recusa de fonte se respeita e nomeia; o resto é `erro`, não ausência."""
    if isinstance(e, urllib.error.HTTPError):
        return ("recusa_de_fonte", f"HTTP {e.code}") if e.code in RECUSAS_DE_FONTE else ("erro", f"HTTP {e.code}")
    if isinstance(e, MuroDeRobo):
        return "recusa_de_fonte", f"muro de robô ({e})"
    return "erro", f"{type(e).__name__}: {str(e)[:120]}"


def pista_de(nome: str, uf: str, ibge: str, fonte: str, url: str, titulo: str, hoje: str) -> dict:
    return {"documento_oficial_confirmado": None, "promovivel": False,       # trava de campo (R7)
            "municipio": nome, "uf": uf, "ibge": str(ibge).zfill(7), "url": url,
            "titulo": f"{fonte} · {nome}/{uf}: {titulo}"[:300], "trecho": titulo[:500],
            "data_publicacao": None, "origem": "descoberta", "hash_evidencia": None,
            "status": STATUS_DA_PISTA, "data": hoje, "registrado_em": hoje}


# ---- um município, quatro fontes ----------------------------------------------------------------
def resolver_dominio(nome: str, uf: str, ibge: str, buscar) -> str | None:
    """O endereço que SE IDENTIFICA como a prefeitura; None se nenhum se identifica (busca não feita)."""
    for d in CANDIDATOS_EXTRA.get(ibge, []) + dominios_do_municipio(nome, uf):
        try:
            if identifica_prefeitura(buscar(f"https://{d}/", 15).decode("utf-8", "replace"), nome):
                return d
        except Exception:  # noqa: BLE001 — DNS, TLS, timeout: o endereço não serve; tenta o próximo
            continue
    return None


def consultar_municipio(nome, uf, ibge, fontes, buscar, hoje, dormir=lambda s: None, api_cc=None, lacunas=lambda *a, **k: None) -> dict:
    """{fonte: {situacao, consulta, pistas:[...]}}; nunca levanta. `situacao`: lido, sem_resultado,
    recusa_de_fonte, erro, dominio_nao_verificado."""
    out, dominio = {}, None
    if {"S16", "S25"} & set(fontes):
        dominio = resolver_dominio(nome, uf, ibge, buscar)
    for f in fontes:
        r = {"situacao": None, "consulta": None, "motivo": None, "pistas": []}
        try:
            if f in ("S16", "S25") and not dominio:
                r["situacao"] = "dominio_nao_verificado"
            else:
                if f == "S16":
                    r["consulta"] = consulta_wayback(dominio); achados = ler_wayback(buscar(r["consulta"], 60))
                elif f == "S25":
                    api = api_cc or indice_common_crawl(buscar("https://index.commoncrawl.org/collinfo.json", 30))
                    r["consulta"] = consulta_common_crawl(api, dominio)
                    try:
                        corpo = buscar(r["consulta"], 60)
                    except urllib.error.HTTPError as e:
                        if not sem_capturas(e):
                            raise
                        corpo = b""
                    achados = ler_common_crawl(corpo)
                elif f == "S13":
                    r["consulta"] = consulta_lexml(nome); achados = ler_lexml(buscar(r["consulta"], 60), nome)
                else:
                    r["consulta"] = consulta_ckan(nome); achados = ler_ckan(buscar(r["consulta"], 60), nome)
                r["pistas"] = [pista_de(nome, uf, ibge, f, u, t, hoje) for u, t in achados[:TETO_POR_FONTE]]
                r["situacao"] = "lido" if achados else "sem_resultado"
        except Exception as e:  # noqa: BLE001
            r["situacao"], r["motivo"] = classificar_erro(e)
            lacunas(f"{f} · {nome}/{uf}", f'{r["situacao"]}: {r["motivo"]}', canal="fontes abertas", camada=1, uf=uf)
        r["dominio"] = dominio
        out[f] = r
        dormir(PAUSA)
    return out


ESPERAS_5XX = (30, 90)   # segundos; só indisponibilidade (5xx, timeout, conexão recusada), nunca 4xx nem muro


def indisponivel(e: Exception) -> bool:
    """Falha de serviço sobrecarregado, que se espera e se repete; recusa (4xx, muro) nunca. Pura."""
    if isinstance(e, urllib.error.HTTPError):
        return e.code >= 500
    return isinstance(e, (TimeoutError, urllib.error.URLError, ConnectionError)) and not isinstance(e, MuroDeRobo)


def com_espera(buscar, url: str, timeout: int, dormir=time.sleep) -> bytes:
    for espera in (*ESPERAS_5XX, None):
        try:
            return buscar(url, timeout)
        except Exception as e:  # noqa: BLE001
            if espera is None or not indisponivel(e):
                raise
            dormir(espera)


def buscar_pausado(url: str, timeout: int) -> bytes:
    """Uma pausa de PAUSA s antes de TODO pedido (o ritmo por host é de quem chama; ver `_respeitar_ritmo`)."""
    def uma(u, t):
        time.sleep(PAUSA)
        return buscar_uma_vez(u, timeout=t)
    return com_espera(uma, url, timeout)


def rodar(caminho: str, fontes: list, limite: int = None) -> int:
    doc = ler(caminho.removeprefix("data/"), {}) or {}
    por_cod, _ = referencia_ibge()
    hoje = hoje_editorial().isoformat()
    feitos = ler(RESULTADO, {"municipios": {}})
    feitos.setdefault("municipios", {})
    fila = [c for c in doc.get("fila", []) if c in por_cod]
    pistas, lidos = [], 0
    try:
        for cod in fila[:limite] if limite else fila:
            ref = por_cod[cod]
            res = consultar_municipio(ref["nome"], ref["uf"], cod, fontes, buscar_pausado, hoje, lacunas=registrar_lacuna)
            for f, r in res.items():
                pistas.extend(r.pop("pistas"))
                feitos["municipios"].setdefault(cod, {})[f] = {"consultado_em": hoje, **r}
            lidos += 1
    except KeyboardInterrupt:
        print(f"[prazo] interrompido depois de {lidos} município(s); gravando o que foi lido.")
    balanco = gravar_lote(pistas, origem="descoberta", ler_fn=ler, gravar_fn=gravar)
    feitos["gerado_em"] = hoje
    gravar(RESULTADO, feitos)
    por = {}
    for m in feitos["municipios"].values():
        for f, r in m.items():
            if f in fontes and r.get("consultado_em") == hoje:
                por.setdefault(f, {}).setdefault(r["situacao"], 0)
                por[f][r["situacao"]] += 1
    print(f"Fontes abertas: {lidos} município(s); {por}; porta única: {balanco.get('gravadas')} gravada(s), "
          f"{balanco.get('recusadas')} recusada(s) {balanco.get('motivos') or ''}")
    return 0


# ---- autoteste (offline; não escreve em data/) ---------------------------------------------------
def autoteste() -> int:
    import pathlib
    wb = json.dumps([["original", "timestamp", "mimetype"],
                     ["http://x.gov.br/docs/PLANCON-2025.pdf", "20250101000000", "application/pdf"],
                     ["http://x.gov.br/noticias", "20250101000000", "text/html"]]).encode()
    cc = (json.dumps({"url": "https://x.gov.br/a/plano-de-contingencia.pdf"}) + "\n"
          + json.dumps({"url": "https://x.gov.br/a/plano-de-contingencia.pdf"}) + "\n").encode()
    sru = ('<searchRetrieveResponse xmlns="http://www.loc.gov/zing/srw/"><records><record><recordData>'
           '<dc xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Decreto aprova o Plano de Contingência de Alfa</dc:title>'
           '<dc:identifier>urn:lex:br;alfa;municipal:decreto:2025;1</dc:identifier></dc></recordData></record></records>'
           '</searchRetrieveResponse>').encode()
    ckan = json.dumps({"success": True, "result": {"results": [
        {"name": "plancon-alfa", "title": "PLANCON de Alfa", "notes": ""},
        {"name": "outro", "title": "Orçamento de Alfa", "notes": ""}]}}).encode()

    def falso(respostas):
        def b(url, timeout):
            for chave, corpo in respostas.items():
                if chave in url:
                    if isinstance(corpo, Exception):
                        raise corpo
                    return corpo
            raise OSError("sem rota: " + url)
        return b

    home = "<html>Prefeitura Municipal de Alfa</html>".encode()
    base = {"web.archive.org": wb, "collinfo": json.dumps([{"id": "CC-1", "cdx-api": "https://i/c1"}, {"id": "CC-2", "cdx-api": "https://i/c2"}]).encode(),
            "i/c2": cc, "lexml": sru, "dados.gov.br": ckan, "alfa.xx.gov.br": home}   # a home por último: as consultas citam o domínio
    um = lambda fontes, r=base: consultar_municipio("Alfa", "XX", "9999999", fontes, falso(r), "2026-10-22", lacunas=lambda *a, **k: lac.append(a))
    lac = []
    todas = um(["S16", "S25", "S13", "S29"])
    fonte = pathlib.Path(__file__).read_text(encoding="utf-8")
    escrita_proibida = re.compile(r"gravar\(\s*['\"](estados|saude_uf|municipios|indice|monitor_saude)\.json")
    testes = {
        "Wayback: só o endereço com plano vira cópia arquivada": lambda: ler_wayback(wb) == [("https://web.archive.org/web/20250101000000/http://x.gov.br/docs/PLANCON-2025.pdf", "Cópia arquivada: http://x.gov.br/docs/PLANCON-2025.pdf")],
        "Wayback: corpo que não é CDX levanta, não vira ausência": lambda: _levanta(ler_wayback, b'[["a","b"]]'),
        "Common Crawl: usa o rastreio mais novo e não repete URL": lambda: indice_common_crawl(base["collinfo"]) == "https://i/c2" and len(ler_common_crawl(cc)) == 1,
        "Common Crawl: 404 'No Captures found' é sem_resultado; outro 404 é erro": lambda: (
            um(["S25"], {**base, "i/c2": urllib.error.HTTPError("u", 404, "x", {}, io.BytesIO(b'{"message":"No Captures found for: a/*"}'))})["S25"]["situacao"] == "sem_resultado"
            and um(["S25"], {**base, "i/c2": urllib.error.HTTPError("u", 404, "x", {}, io.BytesIO(b"nao existe"))})["S25"]["situacao"] == "erro"),
        "LexML: exige o plano e o município no registro": lambda: len(ler_lexml(sru, "Alfa")) == 1 and ler_lexml(sru, "Beta") == [],
        "LexML: XML que não é SRU levanta": lambda: _levanta(lambda c: ler_lexml(c, "Alfa"), b"<html/>"),
        "CKAN: só o conjunto que cita plano e município": lambda: len(ler_ckan(ckan, "Alfa")) == 1,
        "as quatro fontes de um município que responde viram pista": lambda: [todas[f]["situacao"] for f in todas] == ["lido"] * 4,
        "pista no esquema e com as travas de campo": lambda: all(p["documento_oficial_confirmado"] is None and p["promovivel"] is False and p["origem"] == "descoberta" and p["ibge"] == "9999999" for r in todas.values() for p in r["pistas"]),
        "403 é recusa de fonte; timeout é erro; nenhum vira sem_resultado": lambda: (
            um(["S13"], {**base, "lexml": urllib.error.HTTPError("u", 403, "x", {}, None)})["S13"]["situacao"] == "recusa_de_fonte"
            and um(["S13"], {**base, "lexml": TimeoutError("t")})["S13"]["situacao"] == "erro"),
        "resposta sem achado registra a consulta (sem_resultado)": lambda: (lambda r: r["situacao"] == "sem_resultado" and r["consulta"].startswith("https://dados.gov.br"))(um(["S29"], {**base, "dados.gov.br": json.dumps({"success": True, "result": {"results": []}}).encode()})["S29"]),
        "domínio que não se identifica como prefeitura: busca não feita": lambda: um(["S16"], {**base, "alfa.xx.gov.br": b"<html>outra coisa</html>"})["S16"]["situacao"] == "dominio_nao_verificado",
        "trava estrutural: o fonte não grava nos arquivos do índice": lambda: not escrita_proibida.search(fonte),
        "recusa e erro viram lacuna declarada": lambda: (lac.clear(), um(["S13"], {**base, "lexml": urllib.error.HTTPError("u", 429, "x", {}, None)}), len(lac) == 1)[2],
        "401 e 451 também são recusa": lambda: all(classificar_erro(urllib.error.HTTPError("u", c, "x", {}, None))[0] == "recusa_de_fonte" for c in (401, 429, 451)),
        "muro de robô é recusa": lambda: classificar_erro(MuroDeRobo("u", "imperva"))[0] == "recusa_de_fonte",
        "nome só como palavra inteira": lambda: cita("Plano de Alfa", "Alfa") and not cita("Plano de Alfaville", "Alfa"),
        "5xx espera e repete; 4xx e muro não": lambda: _espera_ok(),
        "teto por fonte": lambda: len(ler_common_crawl(("\n".join(json.dumps({"url": f"https://x/plancon{i}.pdf"}) for i in range(9))).encode())) == 9 and TETO_POR_FONTE == 5,
    }
    return rodar_autoteste(testes)


def _espera_ok() -> bool:
    n = {"c": 0}
    def instavel(u, t):
        n["c"] += 1
        if n["c"] < 3:
            raise urllib.error.HTTPError(u, 503, "x", {}, None)
        return b"ok"
    def recusa(u, t):
        n["c"] += 1
        raise urllib.error.HTTPError(u, 403, "x", {}, None)
    esperas = []
    ok = com_espera(instavel, "u", 1, dormir=esperas.append) == b"ok" and esperas == [30, 90]
    n["c"] = 0
    try:
        com_espera(recusa, "u", 1, dormir=esperas.append)
    except urllib.error.HTTPError:
        return ok and n["c"] == 1
    return False


def _levanta(fn, *a) -> bool:
    try:
        fn(*a)
    except Exception:  # noqa: BLE001
        return True
    return False


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    if "--alvos" not in sys.argv:
        print("uso: --alvos <arquivo com fila> [--fontes S16,S25,S13,S29] [--limite N]")
        return 1
    arg = lambda k: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else None
    fontes = [f.strip().upper() for f in (arg("--fontes") or "S13,S16,S25,S29").split(",") if f.strip()]
    return rodar(arg("--alvos"), fontes, int(arg("--limite")) if arg("--limite") else None)


if __name__ == "__main__":
    sys.exit(main())
