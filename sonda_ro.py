import sys, re, io; sys.path[:0] = ["scripts", "."]
import julgar_saude as js
from coletores_base import buscar
url = "https://rondonia.ro.gov.br/wp-content/uploads/2026/09/Plano_Adaptacao_Saude_RO_ElNino_2026_2027_RONDONIA.pdf__2_.pdf"
corpo = buscar(url)
t = js.texto_do_documento(corpo, url)
for pat in [r"Plano de Adapta", r"[Ee][Ll]\s*[Nn][Ii]", r"El Ni", r"EL NI"]:
    ms = [m.start() for m in re.finditer(pat, t)][:5]
    print("POS", pat, ms, [repr(t[i:i+90]) for i in ms[:2]])
try:
    from pypdf import PdfReader
    md = PdfReader(io.BytesIO(corpo)).metadata
    print("META", repr(getattr(md, "title", None)))
except Exception as e:
    print("META erro", e)
