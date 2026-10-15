#!/usr/bin/env bash
# Medida temporária (ramo diag): roda o coletor real nas UFs novas, sem commit. Imprime a conta.
set -o pipefail
python3 - <<'PY'
import json; d=json.load(open("data/atos_resposta.json")); print("atos antes:", len(d["eventos"]))
p=json.load(open("data/pistas_doe.json")) if __import__("os").path.exists("data/pistas_doe.json") else {"itens":[]}; print("pistas_doe antes:", len(p.get("itens",[])))
PY
for uf in $UFS; do
  echo "=== $uf ==="; SECONDS=0
  python3 coletar_doe.py --uf $uf 2>&1 | tail -15
  echo "tempo ${uf}: ${SECONDS}s"
  python3 - "$uf" <<'PY'
import json,sys; uf=sys.argv[1]; f=json.load(open("data/fontes_doe.json"))["ufs"][uf]
print(json.dumps({k:f.get(k) for k in ("adaptador","status","lidas")}, ensure_ascii=False))
import glob,os
ev=sorted(glob.glob("evidencias/*.json"), key=os.path.getmtime)[-1]; e=json.load(open(ev))
print("evidencia:", ev[-20:], "totais:", e.get("totais_por_termo"), "paginas com termo:", len(e.get("paginas",[])))
for pg in e.get("paginas",[])[:6]: print("   ", pg["data"], "p.", pg["pagina"], " ".join(pg["trechos"][0].split())[:160])
PY
done
python3 - <<'PY'
import json; d=json.load(open("data/atos_resposta.json")); print("atos depois:", len(d["eventos"]))
novos=[e for e in d["eventos"] if e.get("canal")=="repositorio_estadual" and e.get("uf") in __import__("os").environ["UFS"].split()]
for e in novos[-20:]: print(" ", e["uf"], e["nome"], e["data"], e.get("decreto"), e.get("decreto_estadual_homologacao"))
p=json.load(open("data/pistas_doe.json")); print("pistas_doe depois:", len(p.get("itens",[])))
for it in [i for i in p.get("itens",[]) if i.get("uf") in __import__("os").environ["UFS"].split()][-10:]: print(" ", it.get("uf"), it.get("municipio"), it.get("data"), (it.get("motivo") or "")[:60])
import glob; print("evidencias novas:", len(glob.glob("evidencias/*.json")))
PY
git status --short | head -20
