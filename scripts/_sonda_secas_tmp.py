"""Sonda pontual (diag 16/10): roda gravar_secas_manchas do ramo edicao/2026-10-16-secas-manchas sem gravar."""
import json, subprocess, sys, pathlib, time, collections
subprocess.run(["git", "fetch", "-q", "origin", "edicao/2026-10-16-secas-manchas"], check=True)
pathlib.Path("_secas_tmp.py").write_text(subprocess.run(["git", "show", "FETCH_HEAD:coletar_sinais_risco.py"],
                                         capture_output=True, text=True, check=True).stdout, encoding="utf-8")
sys.path.insert(0, ".")
import _secas_tmp as c
out = {}
c.escrever_json = lambda caminho, obj, compacto=False: out.update(obj)
t = time.time()
c.gravar_secas_manchas()
print(f"tempo {time.time()-t:.0f}s", c._LIVRO_CONSULTAS[-1] if c._LIVRO_CONSULTAS else None)
print({k: v for k, v in out.items() if k not in ("features", "_governanca")})
for f in out.get("features", []):
    g = f["geometry"]["coordinates"]
    print(f["properties"], "polígonos", len(g), "anéis", sum(len(p) for p in g), "pontos", sum(len(r) for p in g for r in p))
print("tamanho compacto", len(json.dumps(out, ensure_ascii=False, separators=(",", ":"))))
import zipfile, io, urllib.request
print("membros:", [n for n in zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(urllib.request.Request(out["url"], headers={"User-Agent": c.CABECALHO["User-Agent"]}), timeout=120).read())).namelist()])
