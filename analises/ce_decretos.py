"""Sonda descartável: lê no DOE-CE os Decretos 37.608 (13/11) e 37.624 (19/11) e imprime os artigos. Nada grava em data/."""
import re, subprocess, sys, tempfile, pathlib
sys.path.insert(0, ".")
from coletores_base import buscar
for nome, url, num in (("13/11 cad.1", "https://ocrdoeapi.casacivil.ce.gov.br/publications/401/files/1149/download", "37.608"),
                       ("19/11 cad.1", "https://ocrdoeapi.casacivil.ce.gov.br/publications/405/files/1159/download", "37.624")):
    try:
        b = buscar(url, timeout=180, origem="coletar_edicoes_doe")
    except Exception as e:
        print("==", nome, "FALHA", type(e).__name__, str(e)[:200]); continue
    d = pathlib.Path(tempfile.mkdtemp()); (d / "a.pdf").write_bytes(b)
    t = subprocess.run(["pdftotext", "-layout", str(d / "a.pdf"), "-"], capture_output=True, text=True).stdout
    i = t.find(num)
    print("==", nome, len(b), "bytes; posição", i)
    if i >= 0:
        print(re.sub(r"[ \t]+", " ", t[max(0, i - 300): i + 6000]))
