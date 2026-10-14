"""Sonda temporária (ramo diag): alcance da busca PI no tempo."""
import sys, re
sys.path.insert(0, ".")
import coletar_doe as c
for t in ("situação de emergência", "emergência", "decreto", "homologa", "governador"):
    try:
        b = c.enviar(c.BUSCA_PI, {"ocorrencia": t.encode("latin-1")}, timeout=120).decode("latin-1", "replace")
        ed = c.parse_busca_pi(b); tot = re.search(r"Encontradas <b>(\d+)", b)
        ds = sorted(e["data"] for e in ed)
        print(t, "| declaradas", tot and tot.group(1), "| na página", len(ed), "| min", ds[:1], "| max", ds[-3:], "| pag", re.findall(r'href="[^"]*busca[^"]*"', b)[:3])
    except Exception as e:
        print(t, "ERRO", type(e).__name__, e)
