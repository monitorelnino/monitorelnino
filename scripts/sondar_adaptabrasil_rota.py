"""Sonda só leitura (ramo de válvula, nunca mesclada): rotas de download do Painel Nacional AdaptaBrasil.
Lê a página pública e o pacote JS público que ela referencia; imprime só trechos de rotas (prefixo SONDA>),
nunca trechos com credencial. Cliente identificado; 401/403/429/451 = parada."""
import re
import sys
import urllib.error
import urllib.request

sys.path.insert(0, ".")
from coletores_base import UA  # noqa: E402

BASE = "https://sistema.adaptabrasil.mcti.gov.br"
SEG = re.compile(r"(?i)token|secret|senha|password|passwd|authorization|apikey|api_key|bearer|client_?id")


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA + " [sonda de rota de download publica]", "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read(6_000_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""


def main():
    st, html = get(BASE + "/")
    print("SONDA> home", st, len(html))
    js = re.findall(r'src="([^"]+\.js)"', html)
    print("SONDA> scripts", js)
    for rel in js:
        if "main" not in rel:
            continue
        url = rel if rel.startswith("http") else BASE + (rel if rel.startswith("/") else "/" + rel)
        st, src = get(url)
        print("SONDA> js", url, st, len(src))
        if st != 200:
            continue
        vistos = set()
        for chave in ("TotaisApi", "getGeometriaDataDownload", "DataDownload", "location", "/api", "download"):
            for m in re.finditer(re.escape(chave), src):
                a, b = max(0, m.start() - 160), min(len(src), m.end() + 240)
                trecho = src[a:b].replace("\n", " ")
                if SEG.search(trecho) or trecho[:60] in vistos:
                    continue
                vistos.add(trecho[:60])
                print(f"SONDA> [{chave}] {trecho}")
                if len(vistos) > 60:
                    break
            if len(vistos) > 60:
                break


main()
