"""Sonda descartável (ramo coleta-dia, nunca mesclada): o que o DOE-RJ serve em data sem edição. Só leitura."""
import base64, re
from coletores_base import buscar
B = "https://www.ioerj.com.br/portal/modules/conteudoonline/"
for d in ("20261030", "20261031", "20261101", "20261102", "20261103"):
    cod = base64.b64encode(d.encode()).decode()
    try:
        t = buscar(f"{B}do_seleciona_edicao.php?data={cod}", timeout=60, origem="coletar_doe").decode("utf-8", "replace")
    except Exception as e:
        print(d, "ERRO", type(e).__name__, str(e)[:300]); continue
    s = re.sub(r"\s+", " ", re.sub(r"<script.*?</script>|<style.*?</style>|<!--.*?-->|<[^>]+>", " ", t, flags=re.S))
    print("=====", d, len(t), "marcador:", "cadernos do Di" in t, "Parte I (:", len(re.findall(r"Parte I \(", t)))
    for m in re.finditer(r"(cadernos? d[oe]|não (?:há|foi|existe|foram)|nenhum|inexist|sem edi)", s, flags=re.I):
        print("  >", s[max(0, m.start() - 80): m.start() + 160]); break
    print("  FIM:", s[-500:])
