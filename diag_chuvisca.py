import sys, re, traceback
sys.path.insert(0, "scripts"); sys.path.insert(0, ".")
import julgar_e_aplicar_descobertas as j, juiz
U = ("https://rsgovbr-my.sharepoint.com/personal/casa-militar_casamilitar_rs_gov_br/Documents/Casa%20Militar/SUBCHEFIAS/"
     "SUBCHEFIA%20DE%20PROTE%C3%87%C3%83O%20E%20DEFESA%20CIVIL/3.%20Departamento%20de%20Gest%C3%A3o%20de%20Riscos/"
     "Divis%C3%A3o%20T%C3%A9cnica%20de%20Riscos/Planos%20de%20conting%C3%AAncia/TODOS%20PLANCONS%20RECEBIDOS/CREPDEC%2001/PLANCON%20-%20CHUVISCA.doc")
raw = j.obter_documento(U, 120, "diagnóstico Chuvisca")
try:
    t = j.texto_do_documento(raw, U)
    print("DIAG texto", len(t), "letras", sum(c.isalpha() for c in t), "ano", juiz.ano_do_plano(t))
    print("DIAG inicio", t[:700])
    print("DIAG anos", sorted(set(re.findall(r"\b(?:19|20)\d\d\b", t))))
except Exception:
    print("DIAG EXC", traceback.format_exc()[-600:].replace("\n", " | "))
