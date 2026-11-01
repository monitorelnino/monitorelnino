#!/usr/bin/env python3
"""Diagnóstico descartável (não mesclar): o que o juiz de saúde vê no PDF da SESAPI-PI. Não grava nada."""
import re, sys
import julgar_saude as js
import juiz
URL = "https://portal.pi.gov.br/sesapi/wp-content/uploads/sites/101/2026/09/PLANO-DE-ENFRENTAMENTO-DOS-EFEITOS-DO-EL-NINO_SESAPI_2026.pdf"
corpo = js.buscar(URL, timeout=150, origem="julgar_saude")
texto = js.texto_do_documento(corpo, URL)
print("bytes", len(corpo), "texto", len(texto))
print("CABECALHO>>", texto[:900].replace("\n", " | "))
m = juiz.RE_TIPO_E_NUMERO.search(texto)
print("RE_TIPO_E_NUMERO:", m.group(0) if m else None, "@", m.start() if m else None)
print("data_do_ato:", juiz.data_do_ato(texto))
print("e_plano_pelo_cabecalho:", juiz.e_plano_pelo_cabecalho(texto))
inst = js.o_que_institui(texto)
print("institui:", sorted(inst), "plano_tecnico:", "instrumento" in inst and m is None)
for com in (False, True):
    print("etapa2 como_plano=%s:" % com, juiz.etapa2_citacao(texto, "instrumento" in inst and m is None, url=URL, como_plano=com))
print("plano_sem_ato:", juiz.plano_sem_ato(texto, URL))
v = js.julgar_camada_saude(texto, "PI", URL, "instrumento" in inst and m is None, "Plano Estadual de Preparação do Setor Saúde")
print("veredito:", {k: v.get(k) for k in ("promove", "motivo", "data", "numero")})
for k, c in v.get("criterios", {}).items():
    print(" ", k, c.get("ok"), str(c.get("trecho") or c.get("dados"))[:200])
