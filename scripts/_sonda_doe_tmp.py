"""Sonda temporária (ramo diag): o DOE-PA acha alguma coisa?"""
import sys, re
sys.path.insert(0, ".")
from coletores_base import enviar_uma_vez as e1
for termo in ("decreto", "emergência", "emergencia", "homologa"):
    try:
        t = e1("https://www.ioepa.com.br/pesquisa/resultado/QueryTexto",
               {"InputTexto": termo, "InputDataInicial": "01/09/2026", "InputDataFinal": "14/10/2026"}, timeout=60).decode("utf-8", "replace")
        nada = "Nenhum resultado" in t
        i = t.find("pagination-container")
        print("====", termo, len(t), "nada" if nada else "ACHOU", "datas", len(re.findall(r"\d{2}/\d{2}/2026", t)))
        if not nada:
            j = t.find("alert") if t.find("alert") > 0 else 3000
            print(re.sub(r"\s+", " ", t[2800:6500]))
    except Exception as e:
        print("ERRO", termo, type(e).__name__, e)
