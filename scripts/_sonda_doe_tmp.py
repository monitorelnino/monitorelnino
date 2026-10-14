"""Sonda temporária (ramo diag): resultado da busca do DOE-PA."""
import sys, re
sys.path.insert(0, ".")
from coletores_base import enviar_uma_vez as e1
for di, df in (("01/09/2026", "14/10/2026"), ("2026-09-01", "2026-10-14")):
    try:
        t = e1("https://www.ioepa.com.br/pesquisa/resultado/QueryTexto",
               {"InputTexto": "situação de emergência", "InputDataInicial": di, "InputDataFinal": df}, timeout=60).decode("utf-8", "replace")
        i = max(t.lower().find("emerg") - 1500, 0)
        print("====", di, len(t), "pdf", t.lower().count(".pdf"), "datas", len(re.findall(r"\d{2}/\d{2}/2026", t)))
        print(re.sub(r"\s+", " ", t[i:i + 3500]))
    except Exception as e:
        print("ERRO", di, type(e).__name__, e)
