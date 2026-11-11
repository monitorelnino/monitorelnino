import urllib.request, json
from coletores_base import ua_de
UA = {"User-Agent": ua_de("coletor TransfereGov")}
base = ["https://repositorio.dados.gov.br/seges/detru/", "http://repositorio.dados.gov.br/seges/detru/"]
nomes = ["", "data_carga_siconv.txt", "siconv_proposta.csv.zip", "siconv_convenio.csv.zip", "historico_de_versoes.pdf"]
out = []
for b in base:
    for n in nomes:
        u = b + n
        try:
            r = urllib.request.urlopen(urllib.request.Request(u, headers=UA, method="HEAD"), timeout=40)
            out.append((u, r.status, r.headers.get("Content-Length"), r.headers.get("Last-Modified")))
        except Exception as e:
            out.append((u, str(e)))
for u in ["https://www.gov.br/transferegov/pt-br/ferramentas-gestao/dados-abertos/download-dados"]:
    try:
        t = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40).read().decode("utf-8", "replace")
        import re
        out.append(("links", sorted(set(re.findall(r"https?://[^\"' <>]*(?:repositorio|dados\.gov|transferegov)[^\"' <>]*", t)))[:40]))
    except Exception as e:
        out.append((u, str(e)))
for o in out:
    print("SONDA", json.dumps(o, ensure_ascii=False))
