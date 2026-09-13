#!/usr/bin/env python3
"""Sonda pontual (13/09/2026): quais links a listagem de informes da SES-DF
realmente traz, quando lida pela reserva do Wayback.

Motivo: em 13/09/2026 a reserva Wayback voltou a funcionar (270 mil caracteres
recebidos, sem "Connection refused" — o bloqueio de 12/09 era rate-limit da
rajada de depuração, não uso normal). Mas `extrair_link_mais_recente()` não
reconheceu nenhum link: o padrão esperado
`/documents/d/saude/informativo_epidemiologico_seNN…-pdf` não aparece na
captura. Esta sonda não coleta e não grava nada em data/ — só mostra o que há,
para decidir o padrão certo com prova, em vez de adivinhar.
"""
import re
import sys
from pathlib import Path

# os coletores vivem na raiz do repositório; esta sonda vive em scripts/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from coletores_base import buscar_com_reserva_wayback  # noqa: E402

BASE = "https://www.saude.df.gov.br"
LISTAGEM = BASE + "/informes-dengue-chikungunya-zika-febre-amarela"


def main() -> int:
    try:
        html = buscar_com_reserva_wayback(LISTAGEM, timeout=60).decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001 — sonda: qualquer falha é resultado a registrar
        print(f"FALHA ao buscar a listagem: {type(e).__name__}: {e}")
        return 1

    print(f"HTML recebido: {len(html)} caracteres")
    print(f"é captura do Wayback: {'web.archive.org' in html or 'archive.org' in html}")

    # 1. Data da captura, se for Wayback — um snapshot antigo explicaria tudo.
    m = re.search(r"/web/(\d{14})/", html)
    print(f"carimbo da captura: {m.group(1) if m else '(não encontrado)'}")

    # 2. Todo href que termine em -pdf ou .pdf, sem presumir a raiz do nome.
    pdfs = re.findall(r'href="([^"]*(?:-pdf|\.pdf))"', html, re.I)
    print(f"\n--- hrefs terminando em -pdf/.pdf: {len(pdfs)} ---")
    for h in pdfs[:60]:
        print(" ", h[:180])

    # 3. Qualquer href sob /documents/ — o padrão do Liferay do GDF.
    docs = re.findall(r'href="(/documents/[^"]*)"', html, re.I)
    print(f"\n--- hrefs sob /documents/: {len(docs)} ---")
    for h in docs[:60]:
        print(" ", h[:180])

    # 4. Qualquer ocorrência das palavras-chave, com contexto — para achar o
    #    nome real que substituiu 'informativo_epidemiologico'.
    for termo in ("informativo", "informe", "epidemiolog", "arbovirose", "boletim"):
        achados = [m.start() for m in re.finditer(termo, html, re.I)][:6]
        print(f"\n--- contexto de '{termo}' ({len(achados)} primeiras ocorrências) ---")
        for i in achados:
            print("  …", html[max(0, i - 120):i + 160].replace("\n", "⏎")[:280])

    return 0


if __name__ == "__main__":
    sys.exit(main())
