"""Diagnóstico de uma vez (19/11): de onde vem a data de 2003 do plano de Muqui 2026."""
import sys, json
sys.path.insert(0, "scripts")
from julgar_e_aplicar_descobertas import buscar_texto
import juiz
for nome, url in (("Muqui", "https://defesacivil.es.gov.br/media/Plano%20de%20Conting%C3%AAncia%20atualizado/2026/MUQUI%20-PLANO%20DE%20CONTING%C3%8ANCIA%20-%202026.pdf"),
                  ("Venda Nova do Imigrante", "https://defesacivil.es.gov.br/Media/DefesaCivil/Plano%20de%20Conting%C3%AAncia%20atualizado/2026/VENDA%20NOVA%20DO%20IMIGRANTE-%20PLANO%20DE%20CONTING%C3%8ANCIA%20-%202025.pdf")):
    t = buscar_texto(url) or ""
    t20 = t[:juiz.TETO_DO_JULGAMENTO]
    a = juiz.ato_proprio(t20)
    print(nome, "LETRAS", len(t), "ATO", a and (a.start(), t20[max(0, a.start()-150):a.end()+250]))
    print(nome, "CABECA", t[:600])
    v = juiz.julgar(t, nome, "ES", url=url)
    print(nome, "VEREDITO", v["promove"], v.get("motivo"), v.get("categoria"), v.get("data"), v.get("regras_18"))
