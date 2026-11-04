"""Sonda só leitura (ramo de válvula, nunca mesclada): rotas de download do Painel Nacional AdaptaBrasil.
Lê a página pública e os pacotes JS públicos; imprime contagens e SÓ caminhos de rota (prefixo SONDA>),
nunca trechos com credencial. Cliente identificado; 401/403/429/451 = parada."""
import re
import sys
import urllib.error
import urllib.request

sys.path.insert(0, ".")
from coletores_base import UA  # noqa: E402

BASE = "https://sistema.adaptabrasil.mcti.gov.br"
SEG = re.compile(r"(?i)token|secret|senha|password|passwd|authorization|apikey|api_key|bearer|client_?id")
CHAVES = ("TotaisApi", "MapaApi", "getGeometriaDataDownload", "DataDownload", "download", "csv", "geojson", "5570")


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA + " [sonda de rota de download publica]", "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read(12_000_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""


def mostrar(titulo, trecho):
    """Imprime o trecho linha a linha; a linha com termo de credencial sai como [redigida]."""
    for ln in trecho.replace("\\n", "\n").split("\n"):
        ln = ln.strip()
        if ln:
            print("SONDA>", titulo, "[redigida]" if SEG.search(ln) else ln[:260])


def main():
    st, src = get(BASE + "/static/js/main.4708008b.js")
    print("SONDA> main", st, len(src))
    a = src.find('"./src/api/menu-structure-base.json"')
    b = src.find("JSON.parse(", a)
    bruto = src[b:b + 2600].replace("\\\\\\\"", "'").replace("\\\"", "'")
    print("SONDA> menu", bruto[:2600])
    st, h = get(BASE + "/api/hierarquia")
    print("SONDA> hierarquia", st, len(h))
    print("SONDA> hierarquia-inicio", "[redigida]" if SEG.search(h[:1800]) else h[:1800])
    for m in list(re.finditer(r'"(?:nome|name|titulo|title)"\s*:\s*"([^"]{3,80})"[^{}]{0,120}?"id"\s*:\s*(\d+)', h))[:60]:
        print("SONDA> ind", m.group(2), m.group(1))


main()
