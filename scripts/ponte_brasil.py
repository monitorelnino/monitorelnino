#!/usr/bin/env python3
"""Ponte no Brasil: cópia de documento público cujo servidor não responde ao robô de fora do país.

Editoria, 15/11/2026: o domínio to.gov.br inteiro (Semarh, Naturatins, CBMTO, Defesa Civil, diário),
saude.ap.gov.br e saude.rn.gov.br esgotam o tempo ou dão rede inalcançável para os servidores do GitHub,
e abrem normalmente de um computador no Brasil. A cópia é trazida de lá, com o cliente identificado,
e guardada endereçada pelo sha256 em `ponte/`; `coletores_base.buscar` a usa quando a conexão nem
vira conversa HTTP (timeout, DNS, rede). Recusa (401, 403, 429, 451, captcha, login, muro) nunca
chega aqui: a fonte respondeu "não", e isso se respeita.

USO
  python3 scripts/ponte_brasil.py --autoteste
  python3 scripts/ponte_brasil.py --guardar URL ARQUIVO --via "como a cópia foi obtida"
  python3 scripts/ponte_brasil.py --pedidos        # até 40 endereços a trazer, o mais recente primeiro
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import coletores_base as cb  # noqa: E402

PASTA = "ponte"


def registro(doc: dict, url: str, corpo: bytes, via: str, hoje: str) -> tuple:
    """(doc, caminho relativo do arquivo) com a cópia registrada para `url`. Função pura."""
    h = cb.sha256(corpo)
    ext = "pdf" if corpo[:5] == b"%PDF-" else "html"
    caminho = f"{PASTA}/{h}.{ext}"
    doc = dict(doc or {})
    doc.setdefault("_governanca", __doc__.split("\n\n")[1].replace("\n", " "))
    doc["copias"] = dict(doc.get("copias") or {}, **{url: {"arquivo": caminho, "sha256": h, "tamanho": len(corpo),
                                                           "obtido_em": hoje, "via": via}})
    return doc, caminho


def guardar(url: str, arquivo: str, via: str) -> str:
    corpo = pathlib.Path(arquivo).read_bytes()
    doc, caminho = registro(cb.ler(cb.PONTE, {}), url, corpo, via, cb.hoje_editorial().isoformat())
    destino = cb.RAIZ / caminho
    destino.parent.mkdir(exist_ok=True)
    destino.write_bytes(corpo)
    cb.gravar(cb.PONTE, doc)
    return caminho


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
    doc, caminho = registro({}, "https://to.gov.br/x", pdf, "teste", "2026-11-15")

    def com_ponte(erro, copia=True):
        lido = {"copias": doc["copias"]} if copia else {}
        orig_ler, orig_raiz = cb.ler, cb.RAIZ
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            (pathlib.Path(tmp) / PASTA).mkdir()
            (pathlib.Path(tmp) / caminho).write_bytes(pdf)
            cb.ler, cb.RAIZ = (lambda nome, padrao=None: lido if nome == cb.PONTE else padrao), pathlib.Path(tmp)
            try:
                def falha(url, timeout=0):
                    raise erro
                return cb.buscar("https://to.gov.br/x", buscar_fn=falha, dormir=lambda s: None)
            except Exception as e:  # noqa: BLE001
                return type(e).__name__
            finally:
                cb.ler, cb.RAIZ = orig_ler, orig_raiz

    return cb.rodar_autoteste({
        "registro: endereçado pelo sha256, com data e via": lambda: caminho == f"ponte/{cb.sha256(pdf)}.pdf"
            and doc["copias"]["https://to.gov.br/x"]["obtido_em"] == "2026-11-15",
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
    if "--guardar" in sys.argv:
        i = sys.argv.index("--guardar")
        via = sys.argv[sys.argv.index("--via") + 1] if "--via" in sys.argv else "ponte no Brasil"
        print(guardar(sys.argv[i + 1], sys.argv[i + 2], via))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
