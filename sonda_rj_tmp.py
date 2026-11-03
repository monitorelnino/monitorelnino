"""Sonda descartável (ramo coleta-dia, nunca mesclada): mostra o que o DOE-RJ serve hoje. Só leitura."""
import base64, re, sys
from coletores_base import buscar
B = "https://www.ioerj.com.br/portal/modules/conteudoonline/"
for d in ("20261029", "20261103", "20261102"):
    cod = base64.b64encode(d.encode()).decode()
    try:
        t = buscar(f"{B}do_seleciona_edicao.php?data={cod}", timeout=60, origem="coletar_doe").decode("utf-8", "replace")
    except Exception as e:
        print(d, "ERRO", type(e).__name__, str(e)[:300]); continue
    print("=====", d, len(t), "bytes; 'cadernos do Di' em t:", "cadernos do Di" in t)
    print(re.sub(r"\s+", " ", re.sub(r"<script.*?</script>|<style.*?</style>", "", t, flags=re.S))[:1500])
    print("LINKS:", re.findall(r'href="([^"]*(?:session|edicao|caderno)[^"]*)"[^>]*>\s*([^<]{0,80})', t)[:15])
