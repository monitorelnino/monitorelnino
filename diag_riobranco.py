"""Diagnóstico de uma vez (19/11/2026): por que o PLANCON 2025 de Rio Branco caiu no caminho do ato."""
import sys, json
sys.path.insert(0, "scripts")
from julgar_e_aplicar_descobertas import obter_documento, com_ocr, texto_do_documento
import juiz
url = "https://portalcgm.riobranco.ac.gov.br/lai/wp-content/uploads/2013/09/PLANO-DE-CONTING%C3%8ANCIA-INUNDA%C3%87%C3%83O-GRADUAL-PMRB-2025.pdf"
raw = obter_documento(url, 60)
t = com_ocr(raw, texto_do_documento(raw, url))
print("LETRAS", len(t))
print("CABECA<<<", t[:3500].replace("\n", " ⏎ "), ">>>")
print("como_plano", juiz.e_plano_pelo_cabecalho(t))
cab = t[:juiz.CABECALHO_18]
m = juiz.RE_TITULO_PLANO_18.search(cab); print("titulo", m and (m.start(), m.group(0)[:80]))
a = juiz.RE_CABECALHO_DE_ATO.search(cab); print("ato_no_cabecalho", a and (a.start(), a.group(0)[:80]))
print("secoes", sorted({juiz.normalizar(x.group(1))[:6] for x in juiz.RE_SECAO_DE_PLANO.finditer(t)}))
print("CABECALHO_18", juiz.CABECALHO_18)
v = juiz.julgar(t, "Rio Branco", "AC", "1200401", url=url)
print(json.dumps(v, ensure_ascii=False, default=str)[:2500])
