#!/usr/bin/env python3
"""Ponte no Brasil: cópia de documento público cujo servidor não responde ao robô de fora do país.

Editoria, 15/11/2026: o domínio to.gov.br inteiro (Semarh, Naturatins, CBMTO, Defesa Civil, diário),
saude.ap.gov.br e saude.rn.gov.br esgotam o tempo ou dão rede inalcançável para os servidores do GitHub,
e abrem normalmente de um computador no Brasil. A cópia é trazida de lá, com o cliente identificado,
e guardada endereçada pelo sha256 em `ponte/`; `coletores_base.buscar` a usa quando a conexão nem
vira conversa HTTP (timeout, DNS, rede). Recusa (401, 403, 429, 451, captcha, login, muro) nunca
chega aqui: a fonte respondeu "não", e isso se respeita.

Toda noite (`.github/workflows/ponte_brasil.yml`): `--pedidos` lista os documentos das filas de pista
que moram nos hosts de `config/ponte_brasil.json` e ainda não têm cópia; o executor no Brasil os baixa
com o cliente identificado e devolve como artefato; `--do-artefato` confere cada um (muro de robô e
recusa não entram) e guarda pela mesma função de `--guardar`.

USO
  python3 scripts/ponte_brasil.py --autoteste
  python3 scripts/ponte_brasil.py --guardar URL ARQUIVO --via "como a cópia foi obtida"
  python3 scripts/ponte_brasil.py --pedidos            # um endereço por linha
  python3 scripts/ponte_brasil.py --do-artefato        # dentro do elo: traz o artefato `ponte` deste run
"""
import os
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import coletores_base as cb  # noqa: E402

PASTA = "ponte"
CONFIG = cb.RAIZ / "config" / "ponte_brasil.json"
FILAS = ("pistas_imprensa.json", "pistas_descobertas.json", "pistas_imprensa_saude.json")
TETO_POR_NOITE = 40


def pedidos(filas: list, hosts: list, copias: dict, teto: int = TETO_POR_NOITE) -> list:
    """Endereços das pistas em host da ponte, ainda sem cópia, sem repetir, até o teto. Função pura."""
    import urllib.parse
    vistos, saida = set(copias or {}), []
    for itens in filas:
        for p in itens or []:
            u = str((p or {}).get("url_final") or (p or {}).get("url") or "").strip()
            h = urllib.parse.urlsplit(u).hostname or ""
            if u.startswith("http") and u not in vistos and any(h == x or h.endswith("." + x) for x in hosts):
                vistos.add(u)
                saida.append(u)
    # documento antes de página: o teto da noite vai primeiro ao que o juiz lê
    return sorted(saida, key=lambda u: not re.search(r"\.pdf\b|/download/", u, re.I))[:teto]


def aceitar(corpo: bytes, status: str) -> str:
    """'' quando a cópia trazida vale; senão o motivo. Recusa e muro de robô nunca entram. Função pura."""
    if not status.startswith("200"):
        return f"a fonte respondeu {status}"
    if not corpo:
        return "corpo vazio"
    muro = cb.detectar_muro_de_robo(corpo)
    return f"muro de robô ({muro})" if muro else ""


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


def do_artefato() -> int:
    """Traz o artefato `ponte` deste run (manifesto.tsv: n, url, status) e guarda o que vale."""
    import subprocess
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        r = subprocess.run(["gh", "run", "download", os.environ["GITHUB_RUN_ID"], "--name", "ponte", "--dir", tmp],
                           capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            print(f"ponte: sem artefato nesta noite ({r.stderr.strip()[:120]})")
            return 0
        pasta = pathlib.Path(tmp)
        manifesto = pasta / "manifesto.tsv"
        for linha in (manifesto.read_text(encoding="utf-8-sig").splitlines() if manifesto.exists() else []):
            n, url, status = (linha.split("\t") + ["", "", ""])[:3]
            arquivo = pasta / f"{n}.bin"
            motivo = aceitar(arquivo.read_bytes() if arquivo.exists() else b"", status)
            if motivo:
                print(f"  ✗ {url}: {motivo}")
                continue
            print(f"  ✓ {url}: {guardar(url, str(arquivo), 'executor no Brasil (ponte_brasil.yml)')}")
    return 0


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
        "pedidos: só host da ponte, sem cópia, sem repetir, até o teto": lambda: pedidos(
            [[{"url": "https://central.to.gov.br/download/1"}, {"url_final": "https://saude.ap.gov.br/p.pdf"},
              {"url": "https://central.to.gov.br/download/1"}, {"url": "https://exemplo.com/to.gov.br"},
              {"url": "https://central.to.gov.br/download/2"}]], ["to.gov.br", "saude.ap.gov.br"],
            {"https://central.to.gov.br/download/2": {}}) == ["https://central.to.gov.br/download/1",
                                                              "https://saude.ap.gov.br/p.pdf"]
            and len(pedidos([[{"url": f"https://to.gov.br/{i}"} for i in range(99)]], ["to.gov.br"], {})) == TETO_POR_NOITE,
        "aceitar: recusa, corpo vazio e muro de robô não entram": lambda: aceitar(pdf, "200") == ""
            and aceitar(pdf, "erro 403").startswith("a fonte respondeu") and aceitar(b"", "200") == "corpo vazio"
            and aceitar(b"<html><title>Just a moment...</title>cf-chl</html>", "200").startswith("muro"),
    })


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    if "--pedidos" in sys.argv:
        import json
        hosts = json.loads(CONFIG.read_text(encoding="utf-8"))["hosts"]
        filas = []
        for nome in FILAS:
            doc = cb.ler(nome, {}) or {}
            filas.append(doc.get("pistas") if isinstance(doc.get("pistas"), list) else doc.get("itens"))
        print("\n".join(pedidos(filas, hosts, (cb.ler(cb.PONTE, {}) or {}).get("copias"))))
        return 0
    if "--do-artefato" in sys.argv:
        return do_artefato()
    if "--guardar" in sys.argv:
        i = sys.argv.index("--guardar")
        via = sys.argv[sys.argv.index("--via") + 1] if "--via" in sys.argv else "ponte no Brasil"
        print(guardar(sys.argv[i + 1], sys.argv[i + 2], via))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
