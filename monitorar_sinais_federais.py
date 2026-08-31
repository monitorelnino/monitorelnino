#!/usr/bin/env python3
"""Vigia de sinais federais novos: decretos/portarias no DOU, movimentações da
ADPF 743 e novos boletins ou indicativos de data do ciclo El Niño 2026-2027.

Criado em 29/08/2026 (METODOLOGIA §15). Estatuto idêntico ao do Querido Diário:
DESCOBERTA, NUNCA CLASSIFICAÇÃO — esta rotina apenas propõe pistas em
data/pistas_sinais.json, com status "pendente_triagem", para julgamento humano.
Ela NUNCA escreve em data/marcos_prazos.json (registro curado), NUNCA altera o
banco, NUNCA pontua. Falha de rede não interrompe o pipeline (aviso e saída 0),
no padrão de atualizar_boletins.py.

Fontes vigiadas:
  1. DOU (consulta pública da Imprensa Nacional) — termos do ciclo em atos
     normativos federais (decreto, portaria, resolução) sobre proteção e
     defesa civil / El Niño.
  2. Notícias do STF sobre a ADPF 743 (novos despachos e prazos).
  3. Novos boletins do Painel El Niño (delegado a atualizar_boletins.py, cujo
     registro data/boletins.json é lido aqui apenas para o digesto).

Uso: python3 monitorar_sinais_federais.py               (vigia ao vivo)
     python3 monitorar_sinais_federais.py --self-test   (valida parsing, dedup e
                                                         garantias, sem rede)
"""
import hashlib
import json
import pathlib
import re
import sys
import urllib.parse
import urllib.request

RAIZ = pathlib.Path(__file__).parent
FILA = RAIZ / "data" / "pistas_sinais.json"
TERMOS_DOU = ["El Niño", "proteção e defesa civil", "plano de contingência"]
UA = {"User-Agent": "MonitorElNinoBrasil/1.0"}


def _hash(p):
    """Identidade estável de uma pista (fonte+titulo+data) para deduplicação."""
    return hashlib.sha256(f"{p['fonte']}|{p['titulo']}|{p.get('data','')}".encode()).hexdigest()[:16]


def _get(url, timeout=30):
    """GET tolerante: devolve o corpo como texto, ou None com aviso (nunca exceção)."""
    try:
        req = urllib.request.Request(url, headers=UA)
        return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "ignore")
    except Exception as e:
        print(f"[aviso] não foi possível consultar {url}: {e}")
        return None


def extrair_pistas_dou(texto, termo):
    """Extrai pistas de um retorno da consulta do DOU (JSON preferencial; HTML de reserva).

    O endpoint público da Imprensa Nacional muda de formato sem aviso; por isso o
    parser aceita (a) JSON com lista de itens contendo title/pubDate/urlTitle e
    (b) HTML simples com âncoras de resultado. Tudo que não casar é ignorado —
    descoberta perde recall com formato novo, nunca inventa resultado.
    """
    pistas = []
    try:
        d = json.loads(texto)
        itens = d.get("jsonArray") or d.get("items") or []
        for it in itens:
            titulo = re.sub(r"<[^>]+>", "", it.get("title", "")).strip()
            if not titulo:
                continue
            pistas.append({
                "fonte": "DOU", "termo": termo, "titulo": titulo,
                "data": it.get("pubDate", ""),
                "url": ("https://www.in.gov.br/web/dou/-/" + it["urlTitle"]) if it.get("urlTitle") else "",
            })
        return pistas
    except (json.JSONDecodeError, TypeError):
        pass
    for m in re.finditer(r'href="(/web/dou/-/[^"]+)"[^>]*>([^<]{10,200})<', texto or ""):
        pistas.append({"fonte": "DOU", "termo": termo,
                       "titulo": m.group(2).strip(),
                       "data": "", "url": "https://www.in.gov.br" + m.group(1)})
    return pistas


def vigiar_dou():
    """Consulta a busca pública do DOU para cada termo do ciclo; devolve pistas."""
    pistas = []
    for termo in TERMOS_DOU:
        q = urllib.parse.quote(termo)
        texto = _get(f"https://www.in.gov.br/consulta/-/buscar/dou?q=%22{q}%22&s=do1&exactDate=personalizado&sortType=0")
        if texto:
            pistas += extrair_pistas_dou(texto, termo)
    return pistas


def extrair_pistas_stf(html):
    """Extrai das notícias do STF os títulos que mencionem a ADPF 743 ou prazos a estados."""
    pistas = []
    for m in re.finditer(r"<a[^>]+href=\"([^\"]+)\"[^>]*>([^<]{15,220})</a>", html or ""):
        titulo = m.group(2).strip()
        if re.search(r"ADPF\s*743|incêndio|queimada|defesa civil|El Niño", titulo, re.I):
            url = m.group(1)
            if url.startswith("/"):
                url = "https://noticias.stf.jus.br" + url
            pistas.append({"fonte": "STF", "termo": "ADPF 743 / prazos",
                           "titulo": titulo, "data": "", "url": url})
    return pistas


def vigiar_stf():
    """Consulta o portal de notícias do STF; devolve pistas relacionadas à ADPF 743."""
    html = _get("https://noticias.stf.jus.br/?s=ADPF+743")
    return extrair_pistas_stf(html) if html else []


def carregar_fila():
    """Carrega a fila de pistas (ou inicializa vazia com o cabeçalho de governança)."""
    if FILA.exists():
        return json.load(open(FILA, encoding="utf-8"))
    return {"_governanca": ("Fila de DESCOBERTA para triagem humana (METODOLOGIA §15). Nada aqui é "
                            "classificação, marco ou dado do banco; a promoção de uma pista a marco em "
                            "data/marcos_prazos.json ou a registro do banco é sempre ato humano, pelo "
                            "protocolo padrão (busca, canal, log)."),
            "pistas": []}


def registrar(fila, novas):
    """Deduplica por hash e anexa as pistas inéditas com status pendente_triagem."""
    vistos = {p["hash"] for p in fila["pistas"]}
    ineditas = []
    for p in novas:
        p["hash"] = _hash(p)
        if p["hash"] not in vistos:
            p["status"] = "pendente_triagem"
            fila["pistas"].append(p)
            vistos.add(p["hash"])
            ineditas.append(p)
    return ineditas


def self_test():
    """Valida, sem rede: parsing DOU (JSON e HTML), parsing STF, dedup e as garantias de escrita."""
    # 1. DOU em JSON
    fx_json = json.dumps({"jsonArray": [
        {"title": "DECRETO Nº 99.999 — <b>Plano</b> federal El Niño", "pubDate": "28/08/2026",
         "urlTitle": "decreto-99999"}]})
    p1 = extrair_pistas_dou(fx_json, "El Niño")
    assert len(p1) == 1 and p1[0]["titulo"].startswith("DECRETO Nº 99.999") and "<b>" not in p1[0]["titulo"], "parser DOU/JSON"
    # 2. DOU em HTML
    fx_html = '<a href="/web/dou/-/portaria-123">PORTARIA Nº 123 — proteção e defesa civil</a>'
    p2 = extrair_pistas_dou(fx_html, "proteção e defesa civil")
    assert len(p2) == 1 and p2[0]["url"].endswith("portaria-123"), "parser DOU/HTML"
    # 3. STF
    fx_stf = '<a href="/postsnoticias/x">STF fixa novo prazo na ADPF 743 para estados</a><a href="/y">Outra nota qualquer sem relação</a>'
    p3 = extrair_pistas_stf(fx_stf)
    assert len(p3) == 1 and "ADPF 743" in p3[0]["titulo"], "parser STF"
    # 4. dedup
    fila = {"_governanca": "x", "pistas": []}
    a = registrar(fila, p1 + p2 + p3)
    b = registrar(fila, p1 + p2 + p3)
    assert len(a) == 3 and len(b) == 0 and all(p["status"] == "pendente_triagem" for p in fila["pistas"]), "dedup/status"
    # 5. garantias: este módulo não ABRE os arquivos curados (menção em docstring é
    # documentação; o que a garantia veda é qualquer chamada open() sobre eles)
    fonte = pathlib.Path(__file__).read_text(encoding="utf-8")
    for proibido in ["marcos_prazos.json", "estados.json", "municipios.json", "indice.json"]:
        assert not re.search(r"open\([^)]*" + re.escape(proibido), fonte), \
            f"garantia violada: open() sobre {proibido} na rotina de descoberta"
    print("✓ TODOS OS TESTES PASSARAM — parsers, dedup e garantias de escrita")
    return 0


def main():
    """CLI: vigia as fontes, registra pistas inéditas na fila e imprime o digesto."""
    if "--self-test" in sys.argv:
        return self_test()
    fila = carregar_fila()
    novas = registrar(fila, vigiar_dou() + vigiar_stf())
    json.dump(fila, open(FILA, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    try:
        ult = json.load(open(RAIZ / "data" / "boletins.json", encoding="utf-8")).get("ultimo_boletim")
        print(f"(vigia de boletins delegada a atualizar_boletins.py — último registrado: nº {ult})")
    except Exception:
        pass
    if novas:
        print(f"[PISTAS NOVAS] {len(novas)} para triagem humana:")
        for p in novas[:20]:
            print(f"  · [{p['fonte']}] {p['titulo'][:110]}")
        print("  → triagem pelo protocolo padrão; nada foi classificado nem registrado como marco.")
    else:
        print(f"Nenhuma pista inédita (fila com {len(fila['pistas'])} itens acumulados).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
