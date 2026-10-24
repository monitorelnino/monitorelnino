#!/usr/bin/env python3
"""Diagnóstico descartável (ramo coleta-dia, nunca mesclado): por que PDFs da pasta RS saem inacessíveis."""
import sys, io, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import julgar_e_aplicar_descobertas as j
for url in pathlib.Path("data/rs_diag_urls.txt").read_text().split():
    try:
        raw = j._ler_sharepoint_rs(url, 60)
        print("DIAG", len(raw), raw[:8], url[-60:])
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(raw)) as pdf:
                n = len(pdf.pages); t = (pdf.pages[0].extract_text() or "")[:60]
            print("DIAG   pdfplumber ok paginas", n, repr(t))
        except Exception as e:
            print("DIAG   pdfplumber", type(e).__name__, str(e)[:120])
    except Exception as e:
        r = getattr(e, "response", None)
        print("DIAG ERRO", type(e).__name__, str(e)[:160], getattr(r, "status_code", None), url[-60:])
