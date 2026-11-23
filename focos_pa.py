"""Focos do INPE (satélite de referência) por município do Pará e mês, 2023–2026 (relatório do Marajó; não vai à main)."""
import collections, json, pathlib, sys
import coletar_sinais_risco as sr
from coletores_base import buscar
out = {"meses": {}, "falhas": {}}
for ano in (2023, 2024, 2025, 2026):
    for m in range(1, 13):
        mes = f"{ano}{m:02d}"
        if mes > "202611":
            continue
        try:
            texto = buscar(sr.FOCOS_MENSAL.format(mes=mes), timeout=180, origem="coletar_sinais_risco").decode("utf-8", "replace")
            c = collections.Counter()
            for d in sr.resumo_focos_ref(texto).values():
                for k, v in d["municipio"].items():
                    if k.startswith("15"):
                        c[k] += v
            out["meses"][mes] = dict(c); print(mes, sum(c.values()), flush=True)
        except Exception as e:  # noqa: BLE001
            out["falhas"][mes] = f"{type(e).__name__}: {str(e)[:120]}"; print(mes, "FALHA", flush=True)
pathlib.Path("data/relatorio_marajo").mkdir(exist_ok=True)
json.dump(out, open("data/relatorio_marajo/focos_pa.json", "w"))
