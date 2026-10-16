"""Sonda pontual (diag 16/10): roda gravar_focos_referencia do ramo edicao/2026-10-16-focos-referencia sem gravar."""
import json, subprocess, sys, pathlib, time
subprocess.run(["git", "fetch", "-q", "origin", "edicao/2026-10-16-focos-referencia"], check=True)
pathlib.Path("_focos_tmp.py").write_text(subprocess.run(["git", "show", "FETCH_HEAD:coletar_sinais_risco.py"],
                                         capture_output=True, text=True, check=True).stdout, encoding="utf-8")
sys.path.insert(0, ".")
import _focos_tmp as c
out = {}
c.escrever_json = lambda caminho, obj, compacto=False: out.update(obj)
t = time.time()
c.gravar_focos_referencia()
print(f"tempo {time.time()-t:.0f}s, consultas {len(c._LIVRO_CONSULTAS)}")
r = out.get("resumo", {})
print("ultimo_dia", r.get("ultimo_dia"), "dia", json.dumps(r.get("dia"), ensure_ascii=False)[:400])
print("ano anterior", r.get("mesmo_dia_ano_anterior"), "mês", r.get("mes"))
print("30d", {k: v for k, v in (r.get("ultimos_30_dias") or {}).items() if k != "por_dia"}, (r.get("ultimos_30_dias") or {}).get("por_dia", [])[-5:])
print("municípios 30d", len(r.get("municipios_30_dias") or {}), "série", len(out.get("serie") or {}), "dias mun", len(out.get("municipios_por_dia") or {}))
print("tamanho compacto", len(json.dumps(out, ensure_ascii=False, separators=(",", ":"))))
