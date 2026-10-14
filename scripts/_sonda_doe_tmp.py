"""Sonda temporária (ramo diag): resultado da busca do DOE-AC."""
import sys, re
sys.path.insert(0, ".")
import coletar_doe as c
for campos in ({"palavra": "homologa", "ano_palavra": "2026"},
               {"palavra": "situação de emergência".encode("latin-1"), "ano_palavra": "2026"},
               {"palavra": "situação de emergência", "ano_palavra": "2026"},
               {"palavra": "situação de emergência".encode("latin-1"), "ano_palavra": "2026", "paginaIni": "20"}):
    try:
        b = c.enviar("https://diario.ac.gov.br/", campos, timeout=120).decode("latin-1", "replace")
        i = b.find("resultado"); j = b.find("download.php", 4500)
        print("====", {k: (v if isinstance(v, str) else "latin1") for k, v in campos.items()}, len(b), "links", b.count("download.php"))
        print(re.sub(r"\s+", " ", b[max(0, j - 1200): j + 1800]))
        print("PAGINACAO", re.findall(r"paginaIni[^>]{0,120}", b)[:6])
    except Exception as e:
        print("ERRO", type(e).__name__, e)
