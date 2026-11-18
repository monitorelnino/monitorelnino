#!/usr/bin/env python3
"""Ponte no Brasil: cópia de documento público cujo servidor não responde ao robô de fora do país.

Editoria, 15/11/2026: o domínio to.gov.br inteiro (Semarh, Naturatins, CBMTO, Defesa Civil, diário),
saude.ap.gov.br e saude.rn.gov.br esgotam o tempo ou dão rede inalcançável para os servidores do GitHub,
e abrem normalmente de um computador no Brasil. A cópia é trazida de lá, com o cliente identificado,
e guardada endereçada pelo sha256 em `ponte/`; `coletores_base.buscar` a usa quando a conexão nem
vira conversa HTTP (timeout, DNS, rede). Recusa (401, 403, 429, 451, captcha, login, muro) nunca
chega aqui: a fonte respondeu "não", e isso se respeita.

Página (não PDF) passa pela mesma redação da evidência preservada antes de ser guardada: credencial e
CPF de terceiro não se republicam (18/11/2026). Corpo vazio e muro de robô não são cópia. Documento (PDF,
binário) trazido em lote não entra na `main`: fica no ramo do lote e o índice aponta para ele (18/11/2026,
`ponte/` já passava de 270 MB com 157 arquivos).

USO
  python3 scripts/ponte_brasil.py --autoteste
  python3 scripts/ponte_brasil.py --guardar URL ARQUIVO --via "como a cópia foi obtida"
  python3 scripts/ponte_brasil.py --receber PASTA --via "…" [--ramo ponte-local/<carimbo>]   # lote: manifesto.json + corpos pelo sha256
  python3 scripts/ponte_brasil.py --pedidos        # até 40 endereços a trazer, o mais recente primeiro
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import coletores_base as cb  # noqa: E402

PASTA = "ponte"


def aceitar(corpo: bytes):
    """Motivo para NÃO guardar, ou None: corpo vazio e muro de robô não são cópia do documento. Pura."""
    if not corpo:
        return "corpo vazio"
    muro = cb.detectar_muro_de_robo(corpo)
    return f"muro de robô ({muro})" if muro else None


def documento(corpo: bytes) -> bool:
    """PDF ou binário (não é página de texto). Função pura."""
    return corpo[:5] == b"%PDF-" or b"\x00" in corpo[:4096]


def redigido(corpo: bytes) -> tuple:
    """(corpo a guardar, campos da redação). PDF e binário não se editam. Função pura."""
    if documento(corpo):
        return corpo, {}
    texto, codificacao = cb.decodificar_pagina(corpo)
    limpo, segredos = cb.redigir_segredos(texto)
    limpo, cpfs = cb.redigir_dados_pessoais(limpo)
    if not (segredos or cpfs):
        return corpo, {}
    return limpo.encode(codificacao), {"sha256_de_origem": cb.sha256(corpo), "segredos_redigidos": segredos,
                                       "cpfs_redigidos": cpfs}


def registro(doc: dict, url: str, corpo: bytes, via: str, hoje: str, ramo: str = None) -> tuple:
    """(doc, caminho relativo ou None, corpo guardado) com a cópia registrada para `url`; a página entra redigida,
    com o sha256 de origem ao lado. Documento de lote (`ramo`) fica no ramo: sem caminho na `main`. Função pura."""
    corpo, redacao = redigido(corpo)
    h = cb.sha256(corpo)
    onde = {"ramo": ramo} if ramo and documento(corpo) else {"arquivo": f"{PASTA}/{h}.{'pdf' if corpo[:5] == b'%PDF-' else 'html'}"}
    doc = dict(doc or {})
    doc.setdefault("_governanca", __doc__.split("\n\n")[1].replace("\n", " "))
    doc["copias"] = dict(doc.get("copias") or {}, **{url: dict(onde, sha256=h, tamanho=len(corpo), obtido_em=hoje,
                                                                via=via, **redacao)})
    return doc, onde.get("arquivo"), corpo


def guardar_lote(itens: list, via: str, ramo: str = None) -> tuple:
    """Guarda [(url, corpo, via própria ou None)] numa leitura e numa escrita do índice. Devolve
    ([caminho guardado na `main` ou no ramo], [(url, motivo da recusa)])."""
    from verificar_tamanho_dos_dados import TETO_MB   # o que entra na `main` respeita o teto por arquivo do repositório
    doc, hoje, guardados, recusados = cb.ler(cb.PONTE, {}), cb.hoje_editorial().isoformat(), [], []
    for url, corpo, via_do_item in itens:
        motivo = aceitar(corpo) or (f"acima do teto de {TETO_MB:.0f} MB por arquivo do repositório"
                                    if len(corpo) > TETO_MB * 1048576 and not (ramo and documento(corpo)) else None)
        if motivo:
            recusados.append((url, motivo))
            continue
        doc, caminho, corpo = registro(doc, url, corpo, via_do_item or via, hoje, ramo)
        if caminho:
            destino = cb.RAIZ / caminho
            destino.parent.mkdir(exist_ok=True)
            destino.write_bytes(corpo)
        guardados.append(caminho or f"{ramo}/{cb.sha256(corpo)}")
    if guardados:
        cb.gravar(cb.PONTE, doc)
    return guardados, recusados


def itens_do_manifesto(pasta: pathlib.Path) -> tuple:
    """([(url, corpo, via)], [(url, motivo)]) de um lote trazido do Brasil: `manifesto.json` (ou `itens.json`)
    com url, status, sha256 e endereço final, e um arquivo por corpo, nomeado pelo sha256. Só entra o que
    respondeu 200 e confere com o sha256 declarado; recusa da fonte e 404 ficam listados, nunca guardados."""
    man = json.loads((pasta / ("manifesto.json" if (pasta / "manifesto.json").exists() else "itens.json")).read_text(encoding="utf-8"))
    itens, fora = [], []
    for it in (man.get("itens") if isinstance(man, dict) else man) or []:
        url, arq = it.get("url"), pasta / str(it.get("sha256"))
        if it.get("status") != 200 or not it.get("sha256") or not arq.exists():
            fora.append((url, "recusa da fonte" if it.get("recusa") else f"sem cópia: {it.get('status') or it.get('erro')}"))
            continue
        corpo = arq.read_bytes()
        if cb.sha256(corpo) != it["sha256"]:
            fora.append((url, "sha256 não confere com o manifesto"))
            continue
        final = (it.get("final") or "").split("#")[0]
        itens.append((url, corpo, None if not final or final == url.split("#")[0] else f"endereço final {final}"))
    return itens, fora


def guardar(url: str, arquivo: str, via: str) -> str:
    guardados, recusados = guardar_lote([(url, pathlib.Path(arquivo).read_bytes(), None)], via)
    if recusados:
        raise SystemExit(f"não guardado: {recusados[0][1]}")
    return guardados[0]


DIAS_DO_PEDIDO = 30
LIMITE_DE_PEDIDOS = 40


def pedidos(fila: dict, copias: dict, hoje: str) -> list:
    """Endereços a trazer: pedidos dos últimos DIAS_DO_PEDIDO dias ainda sem cópia, sem repetição, o
    mais recente primeiro, até LIMITE_DE_PEDIDOS. Função pura."""
    import datetime as dt
    corte = (dt.date.fromisoformat(hoje) - dt.timedelta(days=DIAS_DO_PEDIDO)).isoformat()
    vistos, saida = set(), []
    for p in sorted((fila or {}).get("pedidos") or [], key=lambda p: p.get("em") or "", reverse=True):
        u = p.get("url")
        if not u or u in vistos or u in (copias or {}) or (p.get("em") or "") < corte:
            continue
        vistos.add(u)
        saida.append(u)
    return saida[:LIMITE_DE_PEDIDOS]


def autoteste() -> int:
    import http.client
    import urllib.error
    pdf = b"%PDF-1.7 plano"
    doc, caminho, _ = registro({}, "https://to.gov.br/x", pdf, "teste", "2026-11-15")
    pagina = '<html><script>var f={"access_token":"IGQVJVabcdefghij0123456789"};</script>CPF 123.456.789-09</html>'.encode()
    doc2, _, guardada = registro({}, "https://x.gov.br/p", pagina, "teste", "2026-11-18")
    c2 = doc2["copias"]["https://x.gov.br/p"]

    def lote():
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            d = pathlib.Path(tmp)
            (d / cb.sha256(pdf)).write_bytes(pdf)
            (d / "trocado").write_bytes(b"x")
            (d / "manifesto.json").write_text(json.dumps({"itens": [
                {"url": "https://a.gov.br/1.pdf", "status": 200, "sha256": cb.sha256(pdf), "final": "https://a.gov.br/novo/1.pdf"},
                {"url": "https://a.gov.br/2", "status": 403, "recusa": True},
                {"url": "https://a.gov.br/3", "status": 200, "sha256": "trocado"},
                {"url": "https://a.gov.br/4", "status": 404}]}), encoding="utf-8", newline="\n")
            return itens_do_manifesto(d)

    idas = []

    def com_ponte(erro, copia=True, conta=None):
        lido = {"copias": doc["copias"]} if copia else {}
        orig_ler, orig_raiz = cb.ler, cb.RAIZ
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            (pathlib.Path(tmp) / PASTA).mkdir()
            (pathlib.Path(tmp) / caminho).write_bytes(pdf)
            cb.ler, cb.RAIZ = (lambda nome, padrao=None: lido if nome == cb.PONTE else padrao), pathlib.Path(tmp)
            try:
                def falha(url, timeout=0):
                    idas.append(url)
                    raise erro
                return cb.buscar("https://to.gov.br/x", buscar_fn=falha, dormir=lambda s: None, sem_resposta=conta)
            except Exception as e:  # noqa: BLE001
                return type(e).__name__
            finally:
                cb.ler, cb.RAIZ = orig_ler, orig_raiz

    doc3, caminho3, _ = registro({}, "https://a.gov.br/1.pdf", pdf, "teste", "2026-11-18", ramo="ponte-local/20261118-140100")
    c3 = doc3["copias"]["https://a.gov.br/1.pdf"]

    def do_ramo(corpo):
        pedidos_ao_ramo, orig = [], cb.ler
        cb.ler = lambda nome, padrao=None: doc3 if nome == cb.PONTE else padrao
        try:
            return cb.copia_da_ponte("https://a.gov.br/1.pdf", buscar_fn=lambda u, timeout=0: (pedidos_ao_ramo.append(u), corpo)[1]), pedidos_ao_ramo
        finally:
            cb.ler = orig

    def lote_grande():
        import tempfile
        orig = cb.RAIZ, cb.ler, cb.gravar
        with tempfile.TemporaryDirectory() as tmp:
            cb.RAIZ, cb.ler, cb.gravar = pathlib.Path(tmp), (lambda nome, padrao=None: padrao), (lambda nome, obj, **k: None)
            try:
                grande = b"%PDF-" + b"x" * (51 * 1048576)
                return (guardar_lote([("https://a.gov.br/g.pdf", grande, None)], "t"),
                        guardar_lote([("https://a.gov.br/g.pdf", grande, None)], "t", "ponte-local/x")[0],
                        list(pathlib.Path(tmp).rglob("*.pdf")))
            finally:
                cb.RAIZ, cb.ler, cb.gravar = orig

    return cb.rodar_autoteste({
        "documento de lote fica no ramo: na main entra só o índice; página segue entrando redigida": lambda: caminho3 is None
            and c3 == {"ramo": "ponte-local/20261118-140100", "sha256": cb.sha256(pdf), "tamanho": len(pdf),
                       "obtido_em": "2026-11-18", "via": "teste"}
            and registro({}, "https://x.gov.br/p", pagina, "t", "2026-11-18", ramo="ponte-local/x")[1].endswith(".html"),
        "cópia no ramo: lida do ramo do lote, conferida pelo sha256; corpo trocado não é cópia": lambda: do_ramo(pdf) == (
            (pdf, "2026-11-18"), [f"{cb.RAMOS_CRUS}/ponte-local/20261118-140100/ponte-local/20261118-140100/{cb.sha256(pdf)}"])
            and do_ramo(b"outro")[0] == (None, None),
        "acima do teto por arquivo não entra na main; por referência ao ramo, entra e nada é escrito": lambda: (
            lambda r: r[0] == ([], [("https://a.gov.br/g.pdf", "acima do teto de 50 MB por arquivo do repositório")])
            and len(r[1]) == 1 and r[1][0].startswith("ponte-local/x/") and r[2] == [])(lote_grande()),
        "site fora da rodada vai direto à cópia da ponte, sem ir à rede": lambda: (
            idas.clear(), com_ponte(TimeoutError(), conta={"to.gov.br": 2}), len(idas))[1:] == (pdf, 0),
        "registro: endereçado pelo sha256, com data e via": lambda: caminho == f"ponte/{cb.sha256(pdf)}.pdf"
            and doc["copias"]["https://to.gov.br/x"]["obtido_em"] == "2026-11-15",
        "página entra redigida, com o sha256 de origem ao lado; PDF não se edita": lambda: b"IGQVJV" not in guardada
            and b"123.456.789-09" not in guardada and c2["sha256"] == cb.sha256(guardada)
            and c2["sha256_de_origem"] == cb.sha256(pagina) and (c2["segredos_redigidos"], c2["cpfs_redigidos"]) == (1, 1)
            and redigido(pdf) == (pdf, {}),
        "corpo vazio e muro de robô não são cópia": lambda: aceitar(b"") == "corpo vazio" and aceitar(pdf) is None
            and "muro" in (aceitar(b'<html><head><script src="/TSPD/08a1?type=9"></script></head></html>') or ""),
        "lote: só entra o que respondeu 200 e confere com o sha256; recusa e 404 ficam listados": lambda: lote() == (
            [("https://a.gov.br/1.pdf", pdf, "endereço final https://a.gov.br/novo/1.pdf")],
            [("https://a.gov.br/2", "recusa da fonte"), ("https://a.gov.br/3", "sha256 não confere com o manifesto"),
             ("https://a.gov.br/4", "sem cópia: 404")]),
        "timeout e rede inalcançável caem na cópia da ponte": lambda: com_ponte(TimeoutError()) == pdf
            and com_ponte(urllib.error.URLError("[Errno 101] Network is unreachable")) == pdf
            and com_ponte(http.client.IncompleteRead(b"")) == pdf,
        "recusa da fonte (403, 451) nunca cai na cópia": lambda: com_ponte(
            urllib.error.HTTPError("u", 403, "x", {}, None)) == "HTTPError"
            and com_ponte(urllib.error.HTTPError("u", 451, "x", {}, None)) == "HTTPError",
        "sem cópia registrada, o erro sobe": lambda: com_ponte(TimeoutError(), copia=False) == "TimeoutError",
        "autoteste com falha de rede não vira pedido": lambda: (com_ponte(TimeoutError(), copia=False),
                                                                 "https://to.gov.br/x" not in cb._PEDIDOS_DA_PONTE)[1],
        "pedidos: sem cópia, recentes, sem repetição, o mais novo primeiro": lambda: pedidos(
            {"pedidos": [{"url": "a", "em": "2026-11-10"}, {"url": "b", "em": "2026-11-15"}, {"url": "a", "em": "2026-11-12"},
                         {"url": "c", "em": "2026-09-01"}, {"url": "d", "em": "2026-11-14"}]},
            {"d": {}}, "2026-11-16") == ["b", "a"],
    })


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    if "--pedidos" in sys.argv:
        for u in pedidos(cb.ler(cb.PEDIDOS_DA_PONTE, {}), (cb.ler(cb.PONTE, {}) or {}).get("copias"),
                         cb.hoje_editorial().isoformat()):
            print(u)
        return 0
    via = sys.argv[sys.argv.index("--via") + 1] if "--via" in sys.argv else "ponte no Brasil"
    if "--guardar" in sys.argv:
        i = sys.argv.index("--guardar")
        print(guardar(sys.argv[i + 1], sys.argv[i + 2], via))
        return 0
    if "--receber" in sys.argv:
        itens, fora = itens_do_manifesto(pathlib.Path(sys.argv[sys.argv.index("--receber") + 1]))
        ramo = sys.argv[sys.argv.index("--ramo") + 1] if "--ramo" in sys.argv else None
        guardados, recusados = guardar_lote([(u, c, f"{via}; {v}" if v else None) for u, c, v in itens], via, ramo)
        no_ramo = sum(1 for g in guardados if not g.startswith(PASTA + "/"))
        print(f"{len(guardados)} cópia(s) guardada(s), {no_ramo} por referência ao ramo do lote; {len(fora) + len(recusados)} fora")
        for u, motivo in fora + recusados:
            print(f"  fora: {u} — {motivo}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
