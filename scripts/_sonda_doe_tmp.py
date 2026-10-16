"""Medida temporária (ramo diag): o coletor do cadastro com a segunda fonte (MIDR), sem commit."""
import json, subprocess, sys
r = subprocess.run([sys.executable, "coletar_cadastro_prioritarios.py"], capture_output=True, text=True, timeout=1800)
print(r.stdout[-4000:]); print(r.stderr[-2000:])
d = json.load(open("data/cadastro_prioritarios_federal.json"))
print(json.dumps({k: d.get(k) for k in ("fontes", "coletado_em", "totais", "evidencias")}, ensure_ascii=False)[:3000])
