"""Sonda descartável: Agência Gov como canal de notícias de reconhecimento; leiturajornal. Nada grava."""
import json, re, sys
sys.path.insert(0, ".")
from coletores_base import buscar
import coletar_s2id as c
x = buscar("https://agenciagov.ebc.com.br/noticias/defesa-civil/RSS", timeout=60, origem="coletar_s2id").decode("utf-8", "replace")
print("RSS", len(x), c.eh_xml_rss(x)); its = c.parse_rss_midr(x); print("itens", len(its)); print(json.dumps(its[:6], ensure_ascii=False)[:1500])
for it in its[:3]:
    try:
        h = buscar(it["link"], timeout=60, origem="coletar_s2id").decode("utf-8", "replace")
        print("NOTICIA", it["titulo"][:100], "->", json.dumps(c.parse_noticia_midr(h), ensure_ascii=False)[:900])
        k = h.find("Portaria"); print("   trecho", re.sub(r"<[^>]+>", " ", h[k-300:k+700]).replace("\n", " ")[:900] if k >= 0 else "sem 'Portaria'")
    except Exception as e: print("NOTICIA FALHA", type(e).__name__, str(e)[:150])
for u in ("https://www.in.gov.br/leiturajornal?data=24-11-2026&secao=do1",):
    try:
        t = buscar(u, timeout=90, origem="coletar_s2id").decode("utf-8", "replace")
        print("LEITURA", len(t), [m.group(0)[:150] for m in re.finditer(r"<script[^>]*>", t)][:12])
        i = t.find("Reconhecer"); print("CTX", repr(t[max(0, i-1500):i+200]) if i >= 0 else "sem")
    except Exception as e: print("LEITURA FALHA", type(e).__name__, str(e)[:200])
