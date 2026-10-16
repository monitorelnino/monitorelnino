"""Medida temporária (ramo diag): o adaptador edicao_pi de ponta a ponta, sem commit."""
import json, subprocess, sys
r = subprocess.run([sys.executable, "coletar_doe.py", "--uf", "PI", "--desde", "2026-10-08"], capture_output=True, text=True, timeout=2400)
print(r.stdout[-6000:]); print(r.stderr[-3000:])
d = json.load(open("data/fontes_doe.json"))["ufs"]["PI"]
print(json.dumps({k: v for k, v in d.items() if k != "sondagem"}, ensure_ascii=False)[:2000])
