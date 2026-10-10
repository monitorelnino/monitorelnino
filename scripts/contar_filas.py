#!/usr/bin/env python3
"""scripts/contar_filas.py — resumo de contagem das filas (pistas, descobertas, conferência),
para o relatório semanal (nome até 09/10/2026: contar_filas_humanas.py) (21/09/2026: absorve o que a "rotina diária",
prática manual sem definição formal no repositório, cobria de único)."""
import json

# 21/09/2026: cada arquivo usa uma chave de lista diferente — achado ao testar contra os
# dados reais (um fallback genérico anterior contava as CHAVES do dict, não os itens).
ARQUIVOS = [("data/pistas_imprensa.json", "pistas"),
            ("data/pistas_imprensa_saude.json", "pistas"),
            ("data/pistas_descobertas.json", "itens"),
            ("data/saude_no_plano_revisar.json", "fila"),
            ("data/decretos_conteudo_revisar.json", "fila")]

for f, chave in ARQUIVOS:
    try:
        d = json.load(open(f, encoding="utf-8"))
        n = len(d[chave]) if isinstance(d, dict) and chave in d else (len(d) if isinstance(d, list) else f"chave '{chave}' ausente")
    except Exception as e:  # noqa: BLE001
        n = f"erro: {e}"
    print(f"  {f}: {n}")
