#!/usr/bin/env python3
"""Sonda (só no ramo coleta-dia, 09/11/2026): lê, com o cliente identificado e respeitando recusa, as páginas e
PDFs dos planos das capitais e imprime o que cada um diz (título, anos, trecho inicial)."""
import re, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from coletores_base import buscar
from preservar_evidencias import extrair_texto_por_pagina
URLS = {
 "Belo Horizonte (PMGRD)": "https://prefeitura.pbh.gov.br/sites/default/files/estrutura-de-governo/obras-e-infraestrutura/2026/pmgrd_pbh_2026-2027.pdf",
 "Belo Horizonte (página)": "https://prefeitura.pbh.gov.br/obras-e-infraestruturadefesa-civil/plano-de-contingencia",
 "Aracaju": "https://www.aracaju.se.gov.br/pdf/PLANO_DE_CONTIGENCIA.pdf",
 "Salvador": "https://codesal.salvador.ba.gov.br/wp-content/uploads/2025/09/PLANO_MUNICIPAL_DE_CONTINGNCIA_DAS_CHUVAS-2025-4.pdf",
 "Porto Velho": "https://transp-arquivos.portovelho.ro.gov.br/uploads/arquivos/1781801175-Portaria nº 29 - 2026 - Designação - SMPDC.pdf",
 "Maceió": "https://maceio.al.gov.br/noticias/defesa-civil/defesa-civil-intensifica-acoes-preventivas-para-o-periodo-chuvoso-em-maceio",
 "Fortaleza": "https://www.fortaleza.ce.gov.br/noticias/prefeitura-de-fortaleza-anuncia-acoes-da-operacao-quadra-chuvosa-de-2026",
 "São Luís": "https://www.saoluis.ma.gov.br/portal/noticias/0/3/2902/defesa-civil-de-sao-luis-conclui-mapeamento-de-areas-com-riscos-de-alagamentos",
 "Rio Branco": "https://www.riobranco.ac.gov.br/saerb/prefeitura-de-rio-branco-apresenta-plano-de-contingencia-para-garantir-abastecimento-de-agua-durante-estiagem-severa/",
}
for nome, u in URLS.items():
    print(f"\n===== {nome}\n{u}")
    try:
        b = buscar(u.replace(" ", "%20"), timeout=180, origem="sonda_capitais")
    except Exception as e:
        print(f"   NÃO LIDO: {type(e).__name__}: {str(e)[:200]}"); continue
    if b[:5] == b"%PDF-":
        pags = extrair_texto_por_pagina(b)
        tudo = "\n".join(pags)
        print(f"   PDF {len(b)} bytes, {len(pags)} páginas, {len(tudo)} caracteres")
        print("   anos citados:", sorted(set(re.findall(r"\b20(?:1\d|2\d)\b", tudo)))[-8:])
        print("   " + " ".join(tudo[:1800].split()))
    else:
        t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", b.decode("utf-8", "replace"), flags=re.S)
        t = " ".join(re.sub(r"<[^>]+>", " ", t).split())
        i = max(0, t.lower().find("conting") - 600)
        pdfs = re.findall(r"""href=["']([^"']+[.]pdf)""", b.decode("utf-8", "replace"))[:8]
        print(f"   HTML {len(b)} bytes; links pdf: {pdfs}")
        print("   " + t[i:i+1800])
