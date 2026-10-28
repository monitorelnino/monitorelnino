#!/usr/bin/env python3
"""Baixa o kit oficial do LinkedIn (brand.linkedin.com) para data/marca_kit/linkedin/. Válvula única, ramo coleta-dia/* (nunca mesclado)."""
import os, re, sys, io, zipfile, urllib.request, urllib.error, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from coletores_base import ua_de  # noqa: E402

UA = {"User-Agent": ua_de("logo do LinkedIn para o rodapé (kit oficial)")}
BASE = "https://brand.linkedin.com/downloads"
SAIDA = "data/marca_kit/linkedin"

def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status, r.read()

def main():
    try:
        st, html = get(BASE)
    except urllib.error.HTTPError as e:
        print(f"recusa {e.code} em {BASE}: parar"); return 0
    except Exception as e:
        print(f"erro {e!r} em {BASE}: parar"); return 0
    txt = html.decode("utf-8", "replace")
    print("pagina", st, len(txt), "bytes")
    links = sorted(set(re.findall(r'["\'(]([^"\'()\s]+\.(?:zip|svg))', txt)))
    print("links zip/svg:", links)
    os.makedirs(SAIDA, exist_ok=True)
    for l in links:
        url = urllib.parse.urljoin(BASE, l)
        if "in-logo" not in url and "linkedin-logo" not in url and not url.endswith(".svg"):
            continue
        try:
            st, b = get(url)
        except Exception as e:
            print("falha", url, repr(e)); continue
        nome = os.path.basename(urllib.parse.urlparse(url).path)
        print("baixado", url, st, len(b))
        if nome.endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(b)) as z:
                for n in z.namelist():
                    print("  zip:", n, z.getinfo(n).file_size)
                    if n.lower().endswith((".svg", ".png")) and not n.endswith("/"):
                        d = os.path.join(SAIDA, nome[:-4], os.path.dirname(n))
                        os.makedirs(d, exist_ok=True)
                        open(os.path.join(d, os.path.basename(n)), "wb").write(z.read(n))
        else:
            open(os.path.join(SAIDA, nome), "wb").write(b)
    return 0

if __name__ == "__main__":
    sys.exit(main())
