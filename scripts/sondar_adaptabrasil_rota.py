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
    a = src.find('"./src/api/index.js":')
    mostrar("apiindex", src[a:a + 3200])
    for i, m in enumerate(re.finditer(r"getSchemaQuery = ", src)):
        if i >= 2:
            break
        mostrar("schema", src[m.start():m.start() + 900])
    vistos = set()
    for m in re.finditer(r"_index2\.default\.(?:get|post)\(([^;]{5,200}?)\);", src):
        t = m.group(1)
        if t not in vistos and not SEG.search(t):
            vistos.add(t)
            print("SONDA> chamada", t[:230])
            if len(vistos) >= 60:
                break


main()
