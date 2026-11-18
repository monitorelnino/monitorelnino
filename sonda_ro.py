import sys, re, unicodedata; sys.path[:0] = ["scripts", "."]
import julgar_saude as js
from coletores_base import buscar
url = "https://rondonia.ro.gov.br/wp-content/uploads/2026/09/Plano_Adaptacao_Saude_RO_ElNino_2026_2027_RONDONIA.pdf__2_.pdf"
r = buscar(url)
corpo = r if isinstance(r, (bytes, bytearray)) else (getattr(r, "content", None) or getattr(r, "corpo", None) or r)
print("TIPO", type(r).__name__)
if not isinstance(corpo, (bytes, bytearray)) and isinstance(r, tuple): corpo = r[0]
t = js.texto_do_documento(corpo, url)
print("LEN", len(t))
print("CAPA", repr(t[:900]))
i = t.lower().find("ni")
for m in re.finditer(r"[Nn][Ii].{0,3}[Oo]", t[:5000]): print("NINO", repr(t[max(0,m.start()-8):m.end()+4])); break
print("TITULO", repr(js.titulo_do_documento(t, "", url)))
print("RISCO", js.risco_do_documento(js.titulo_do_documento(t, "", url), t))
