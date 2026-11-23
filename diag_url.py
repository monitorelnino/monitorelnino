import sys, re
from urllib.parse import urlparse, unquote, quote
sys.path.insert(0, "scripts"); sys.path.insert(0, ".")
import julgar_e_aplicar_descobertas as j
from atualizar_instrumentos_estaduais import REPOSITORIOS
from coletores_base import sessao_sharepoint
import json
pis = json.load(open("data/pistas_imprensa.json"))["pistas"]
urls = [(p["municipio"], p.get("url_final") or p["url"]) for p in pis if "CREPDEC%2007" in str(p.get("url")) and str(p.get("url")).endswith(".url")]
s = sessao_sharepoint(REPOSITORIOS["RS"]["url"], "diagnóstico dos atalhos")
p = urlparse(urls[0][1]); api = f"{p.scheme}://{p.netloc}{'/'.join(p.path.split('/')[:3])}/_api/web"
pasta = unquote(p.path).rsplit("/", 1)[0]
r = s.get(f"{api}/GetFolderByServerRelativeUrl('{quote(pasta)}')/Files", params={"$select": "Name,UniqueId,TimeCreated"},
          headers={"Accept": "application/json;odata=nometadata"}, timeout=60)
ids = {f["Name"]: f for f in r.json()["value"]}
for mun, u in sorted(urls):
    nome = unquote(urlparse(u).path).rsplit("/", 1)[1]
    f = ids.get(nome)
    if not f: print("DIAG", mun, "| fora da listagem"); continue
    c = s.get(f"{api}/GetFileById('{f['UniqueId']}')/$value", timeout=60).content
    alvo = re.search(rb"(?im)^URL=(\S+)", c)
    print("DIAG", mun, "|", alvo.group(1).decode("latin-1") if alvo else c[:80], "|", f.get("TimeCreated"))
