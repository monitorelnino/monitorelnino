"""Sonda pontual (diag 16/10): texto real das homologações do DOE-SP (Guariba, Ribeirão Preto)."""
import json, re, sys, time, urllib.parse
sys.path.insert(0, ".")
from coletores_base import buscar
B = ("https://do-api-web-search.doe.sp.gov.br/v2/advanced-search/publications"
     "?PageNumber=1&PageSize=20&Terms[0]={t}&FromDate={de}&ToDate={ate}")
P = "https://do-api-web-search.doe.sp.gov.br/v2/publications/{id}"
def txt(b):
    h = (json.loads(b) or {}).get("content") or ""
    return " ".join(re.sub(r"<[^>]+>", " ", h).split())
for termo, de, ate in (("Guariba", "2026-07-20", "2026-08-05"), ("Ribeirão Preto situação de emergência", "2026-07-20", "2026-08-05"),
                       ("70.765", "2026-07-20", "2026-10-16"), ("homologa situação de emergência", "2026-07-20", "2026-08-05")):
    try:
        o = json.loads(buscar(B.format(t=urllib.parse.quote(termo), de=de, ate=ate), timeout=60))
    except Exception as e:
        print("ERRO busca", termo, e); continue
    print(f"\n=== {termo}: total {o.get('totalItems')}")
    for it in (o.get("items") or [])[:8]:
        print("-", it.get("date"), "|", it.get("title"), "|", it.get("hierarchy"), "|", it.get("slug"))
        if not re.search(r"homolog|emerg", (it.get("title") or "") + (it.get("excerpt") or ""), re.I):
            continue
        time.sleep(2)
        try:
            t = txt(buscar(P.format(id=it["id"]), timeout=60))
        except Exception as e:
            print("  ERRO pub", e); continue
        for m in re.finditer(r"homolog", t, re.I):
            print("  >>", t[max(0, m.start()-250):m.start()+450])
            break
    time.sleep(2)
