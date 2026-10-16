"""Sonda pontual (diag 16/10): amostra de um item do MonitorAr e da RedeAr (estrutura)."""
import json, sys
sys.path.insert(0, ".")
from coletores_base import buscar
m = json.loads(buscar("https://monitorar-backend.mma.gov.br/v1/estacao/todas", timeout=60))
com = [x for x in m if (x.get("indiceQualidadeArAtual") or {})]
print("MONITORAR item:", json.dumps(com[0], ensure_ascii=False)[:2500])
print("indiceQualidadeArAtual exemplos:", [json.dumps(x.get("indiceQualidadeArAtual"), ensure_ascii=False)[:300] for x in com[1:4]])
print("situacao:", sorted({str(x.get("situacao")) for x in m})[:10], "semInfo:", sum(1 for x in m if x.get("semInfoMaisDeTresDias")))
for host in ("https://api.redear.org.br/v1/sensors", "https://hmg.api.redear.org.br/v1/sensors"):
    r = json.loads(buscar(host, timeout=60))
    s = r[0]
    rd = s.get("readings") or []
    print("\nREDEAR", host, "sensor:", json.dumps({k: v for k, v in s.items() if k != "readings"}, ensure_ascii=False)[:600])
    print("  readings:", len(rd), "1ª:", json.dumps(rd[0], ensure_ascii=False)[:900] if rd else None)
    print("  última:", json.dumps(rd[-1], ensure_ascii=False)[:300] if rd else None)
    print("  nº readings por sensor:", sorted(len(x.get("readings") or []) for x in r)[-5:], "fontes:", sorted({x.get("source") for x in r}))
