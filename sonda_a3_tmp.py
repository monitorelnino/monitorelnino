import re, sys
import coletores_base as c

def ver(u, n=3500):
    try:
        b = c.buscar(u)
        t = b.decode("utf8", "replace")
        print("OK", u, len(b))
        return t
    except Exception as e:
        print("ERR", u, repr(e)[:300])
        return ""

t = ver("https://www.egba.ba.gov.br/egba/busca-solr-multisite?search_api_fulltext=decreto")
# links de resultado e de PDF
for m in sorted(set(re.findall(r'href="([^"]+)"', t)))[:120]:
    if any(k in m.lower() for k in ("pdf", "egba", "diario", "doe", "edicao", "page=")):
        print("LINK", m)
i = t.find("view-content")
print("TRECHO", t[max(0, i - 200): i + 3500])
for u in ("https://diariooficial.ma.gov.br", "https://diariooficial.ma.gov.br/public/index.xhtml"):
    x = ver(u)
    print(x[:1500])
