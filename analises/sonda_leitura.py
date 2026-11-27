"""Sonda descartável: estrutura do in.gov.br/leiturajornal e leitura de um ato. Nada grava."""
import json, re, sys, html
sys.path.insert(0, ".")
from coletores_base import buscar
t = buscar("https://www.in.gov.br/leiturajornal?data=24-11-2026&secao=do1", timeout=90, origem="coletar_s2id").decode("utf-8", "replace")
for m in re.finditer(r'<script([^>]*)>', t):
    if 'json' in m.group(1) or 'params' in m.group(1): print("SCRIPT", m.group(1)[:200])
i = t.find("jsonArray"); print("POS", i, repr(t[max(0,i-400):i+600]))
for k in ("Defesa Civil", "Reconhecer"):
    j = t.find(k); print(k, j, repr(t[max(0,j-500):j+300]) if j>=0 else "")
m = re.search(r'<script[^>]*id="params"[^>]*>(.*?)</script>', t, re.S) or re.search(r'id="params"[^>]*value="([^"]*)"', t)
d = json.loads(html.unescape(m.group(1)))
print("chaves", list(d.keys())[:20]); arr = d.get("jsonArray") or []
print("itens", len(arr)); print("item0", json.dumps(arr[0], ensure_ascii=False)[:800])
sed = [x for x in arr if re.search(r"Defesa Civil", x.get("hierarchyStr") or x.get("hierarchyList", "") if isinstance(x.get("hierarchyStr"), str) else "", re.I)]
print("sedec", len(sed)); 
for x in sed[:3]: print(json.dumps(x, ensure_ascii=False)[:700])
if sed:
    u = "https://www.in.gov.br/web/dou/-/" + sed[0]["urlTitle"]
    try:
        a = buscar(u, timeout=90, origem="coletar_s2id").decode("utf-8", "replace"); print("ATO OK", len(a), "tabela" in a.lower(), re.findall(r"Reconhecer[^<]{0,120}", a)[:2])
    except Exception as e: print("ATO FALHA", type(e).__name__, str(e)[:200])
t2 = buscar("https://www.in.gov.br/leiturajornal?data=24-11-2026&secao=do1e", timeout=90, origem="coletar_s2id").decode("utf-8", "replace")
print("extra", len(t2), 'id="params"' in t2)
