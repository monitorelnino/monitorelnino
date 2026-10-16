"""Sonda pontual (diag 16/10): roda gravar_ar_medido do ramo edicao/2026-10-16-ar-medido sem gravar nada."""
import json, subprocess, sys, pathlib, collections
subprocess.run(["git", "fetch", "-q", "origin", "edicao/2026-10-16-ar-medido"], check=True)
pathlib.Path("_ar_tmp.py").write_text(subprocess.run(["git", "show", "FETCH_HEAD:coletar_sinais_risco.py"],
                                     capture_output=True, text=True, check=True).stdout, encoding="utf-8")
sys.path.insert(0, ".")
import coletores_base as cb
cb.preservar_evidencia = lambda c, *a, **k: "hash-de-teste(%d bytes)" % len(c)
import _ar_tmp as c
out = {}
c.escrever_json = lambda caminho, obj, compacto=False: out.update(obj)
try:
    print(c.coletar_fonte("openaq")[1])
except Exception as e:
    print("openaq locais:", type(e).__name__, e)
c.gravar_ar_medido()
for k, v in out.get("fontes", {}).items():
    print(k, {x: v.get(x) for x in ("status", "consultado_em", "evidencia_sha256", "estacoes_casadas")})
e = out.get("estacoes", [])
print("estacoes", len(e), "com IQAr", sum(1 for x in e if x["iqar"]), "com PM2,5 OpenAQ", sum(1 for x in e if x.get("pm25_openaq")))
print("faixas:", collections.Counter((x["iqar"] or {}).get("classificacao") for x in e))
print("UFs com IQAr:", sorted({x["uf"] for x in e if x["iqar"]}))
print("lacunas:", collections.Counter((x["lacuna"] or "")[:40] for x in e).most_common(5))
print("exemplo:", json.dumps([x for x in e if x.get("pm25_openaq")][:2] or [x for x in e if x["iqar"]][:1], ensure_ascii=False))
s = out.get("sensores", [])
print("sensores", len(s), "com PM2,5", sum(1 for x in s if x["pm25"]), json.dumps([x for x in s if x["pm25"]][:1], ensure_ascii=False))
print("lacunas sensores:", collections.Counter((x["lacuna"] or "")[:40] for x in s).most_common(4))
print("tamanho json:", len(json.dumps(out, ensure_ascii=False, indent=1)))
