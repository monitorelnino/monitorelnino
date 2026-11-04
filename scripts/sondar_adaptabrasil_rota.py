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


def main():
    st, html = get(BASE + "/")
    print("SONDA> home", st, len(html))
    st, am = get(BASE + "/asset-manifest.json")
    print("SONDA> asset-manifest", st, re.findall(r'"(static/js/[^"]+)"', am)[:20] if st == 200 else "")
    st, src = get(BASE + "/static/js/main.4708008b.js")
    print("SONDA> main", st, len(src))
    for c in CHAVES:
        print("SONDA> contagem", c, len(re.findall(re.escape(c), src)))
    print("SONDA> sourceMappingURL", re.findall(r"sourceMappingURL=(\S+)", src)[:2])
    caminhos = sorted(set(re.findall(r'["\'`](/?(?:api/)?[A-Za-z0-9_\-]+(?:/[A-Za-z0-9_\-{}$.]+){1,5})["\'`]', src)))
    relev = [c for c in caminhos if re.search(r"(?i)download|total|geometr|mapa|indicador|resolu|munic|export|arquivo|file", c) and not SEG.search(c)]
    print("SONDA> caminhos relevantes", len(relev))
    for c in relev[:80]:
        print("SONDA> rota", c)
    for chave in ("TotaisApi", "getGeometriaDataDownload"):
        for i, m in enumerate(re.finditer(re.escape(chave), src)):
            if i >= 6:
                break
            t = src[max(0, m.start() - 90):m.end() + 140].replace("\n", " ")
            if not SEG.search(t):
                print(f"SONDA> [{chave}] {t}")


main()
