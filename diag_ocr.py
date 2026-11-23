import sys, re
sys.path.insert(0, "scripts"); sys.path.insert(0, ".")
import julgar_e_aplicar_descobertas as j, juiz
U = "https://rsgovbr-my.sharepoint.com/personal/casa-militar_casamilitar_rs_gov_br/Documents/Casa%20Militar/SUBCHEFIAS/SUBCHEFIA%20DE%20PROTE%C3%87%C3%83O%20E%20DEFESA%20CIVIL/3.%20Departamento%20de%20Gest%C3%A3o%20de%20Riscos/Divis%C3%A3o%20T%C3%A9cnica%20de%20Riscos/Planos%20de%20conting%C3%AAncia/TODOS%20PLANCONS%20RECEBIDOS/CREPDEC%2009/Plano%20de%20Conting%C3%AAncia%20S%C3%A3o%20Valentin%20do%20Sul.pdf"
raw = j.obter_documento(U, 120, "diagnóstico OCR")
t0 = j.texto_do_documento(raw, U); t = j.com_ocr(raw, t0)
print("DIAG antes", sum(c.isalpha() for c in t0 or ""), "depois", sum(c.isalpha() for c in t or ""), "ano", juiz.ano_do_plano(t))
print("DIAG inicio", re.sub(r"\s+", " ", t)[:500])
