#!/usr/bin/env python3
"""Sonda (24/10/2026, janela D): o Apêndice IV do relatório ICM-TCE/PE traz plano de contingência por município?
Só lê e imprime; não grava em data/. Ramo coleta-dia/*, nunca mesclado."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from coletores_base import buscar_com_procedencia  # noqa: E402

URL = "https://www.tcepe.tc.br/internet/docs/tce/Relatorio-levantamento-municipios.pdf"


def main() -> int:
    try:
        corpo = buscar_com_procedencia(URL, timeout=120)[0]
    except Exception as e:  # noqa: BLE001
        print(f"FALHA: {type(e).__name__}: {e}")
        return 1
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(corpo)
    print("bytes:", len(corpo))
    pags = [doc[i].get_textpage().get_text_range() for i in range(len(doc))]
    t = "\f".join(pags)
    print("paginas:", len(pags), "caracteres:", len(t))
    for i, p in enumerate(pags, 1):
        if re.search(r"AP[ÊE]NDICE\s+IV", p, re.I):
            print(f"--- 'Apêndice IV' na pág {i}")
    achados = [i for i, p in enumerate(pags, 1) if re.search(r"conting[eê]ncia", p, re.I)]
    print("páginas com 'contingência':", achados[:60])
    for i in achados[:3] + achados[-3:]:
        print(f"===== pág {i} =====")
        print("\n".join(pags[i - 1].splitlines()[:60]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
