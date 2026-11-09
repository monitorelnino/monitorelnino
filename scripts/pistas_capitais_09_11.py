#!/usr/bin/env python3
"""Só no ramo coleta-dia (09/11/2026): achados da verificação das capitais entram como pista pela porta única.
Cada um traz a página oficial; o juiz lê o documento e decide. Nada vai direto ao banco."""
import sys, pathlib, json
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from scripts.pistas import gravar_lote
PISTAS = [
    {"url_final": "https://codesal.salvador.ba.gov.br/wp-content/uploads/2025/09/PLANO_MUNICIPAL_DE_CONTINGNCIA_DAS_CHUVAS-2025-4.pdf",
     "tipo": "plano", "alvo": "2927408", "nivel": "A", "data": "2025-09-01",
     "trecho": "Plano Municipal de Contingência das Chuvas — Defesa Civil de Salvador (CODESAL), edição 2025, atualizado anualmente"},
    {"url_final": "https://prefeitura.pbh.gov.br/sites/default/files/estrutura-de-governo/obras-e-infraestrutura/2026/pmgrd_pbh_2026-2027.pdf",
     "tipo": "plano", "alvo": "3106200", "nivel": "A", "data": "2026-10-16",
     "trecho": "Plano Municipal de Gestão de Riscos e Desastres 2026/2027, listado na página oficial do plano de contingência da Prefeitura (atualizada em 16/10/2026)"},
    {"url_final": "https://transp-arquivos.portovelho.ro.gov.br/uploads/arquivos/1781801175-Portaria nº 29 - 2026 - Designação - SMPDC.pdf",
     "tipo": "plano", "alvo": "1100205", "nivel": "A", "data": "2026-03-24",
     "trecho": "Portaria nº 29/2026/SGOV/SMPDC (DOM-RO ed. 4198, 24/03/2026): designa servidores para elaborar o Plano de Contingência da Defesa Civil Municipal em 30 dias"},
    {"url_final": "https://www.aracaju.se.gov.br/pdf/PLANO_DE_CONTIGENCIA.pdf",
     "tipo": "plano", "alvo": "2800308", "nivel": "B", "data": "2026-11-09",
     "trecho": "PDF de plano de contingência no domínio da Prefeitura de Aracaju (título e ano não confirmados)"},
]
res = gravar_lote([dict(p, origem="descoberta") for p in PISTAS], origem="descoberta")
print(json.dumps(res, ensure_ascii=False))
