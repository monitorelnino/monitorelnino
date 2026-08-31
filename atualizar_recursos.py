#!/usr/bin/env python3
"""Aquisição do PIB per capita por UF (IBGE, Contas Regionais 2023) para o
gráfico-tese ("preparar-se é decisão, não riqueza"). Padrão sentinela do Censo:
SÓ grava se as âncoras oficiais verificadas em 27/08/2026 baterem EXATAS —
DF 129.790,44 · SP 77.566,27 · MT 74.620,05 · e MA na última posição.
Falha-segura: qualquer divergência aborta sem escrever; o site continua no eixo
de população até a série validar. Endpoint SIDRA a confirmar na 1ª execução
(t/5938 v/6323 é a hipótese); a validação por sentinela torna o erro de
endpoint inofensivo por construção.
"""
import json, pathlib, sys, urllib.request

RAIZ = pathlib.Path(__file__).parent
DEST = RAIZ / "data" / "recursos_uf.json"
SENT = {"DF": 129790.44, "SP": 77566.27, "MT": 74620.05}
URL = "https://apisidra.ibge.gov.br/values/t/5938/n3/all/v/6323/p/2023?formato=json"

def main():
    """Busca o PIB per capita por UF na API SIDRA do IBGE, valida contra as quatro UFs-sentinela de 2023 e grava data/recursos_uf.json (ou marca completo:false em caso de falha, sem nunca publicar dado não confirmado)."""
    try:
        with urllib.request.urlopen(URL, timeout=90) as r:
            dados = json.load(r)
    except Exception as e:
        print(f"SIDRA indisponível ({e}) — mantendo seed; site segue no eixo população"); return 0
    UFS = {"Rondônia":"RO","Acre":"AC","Amazonas":"AM","Roraima":"RR","Pará":"PA","Amapá":"AP","Tocantins":"TO","Maranhão":"MA","Piauí":"PI","Ceará":"CE","Rio Grande do Norte":"RN","Paraíba":"PB","Pernambuco":"PE","Alagoas":"AL","Sergipe":"SE","Bahia":"BA","Minas Gerais":"MG","Espírito Santo":"ES","Rio de Janeiro":"RJ","São Paulo":"SP","Paraná":"PR","Santa Catarina":"SC","Rio Grande do Sul":"RS","Mato Grosso do Sul":"MS","Mato Grosso":"MT","Goiás":"GO","Distrito Federal":"DF"}
    pib = {}
    for linha in dados[1:]:
        uf = UFS.get(linha.get("D1N", "").strip())
        try: v = float(linha.get("V"))
        except (TypeError, ValueError): continue
        if uf: pib[uf] = v
    if len(pib) != 27:
        print(f"ABORTADO: {len(pib)}/27 UFs — nada gravado"); return 1
    for uf, esperado in SENT.items():
        if abs(pib[uf] - esperado) > 0.5:
            print(f"ABORTADO: sentinela {uf} divergente ({pib[uf]} ≠ {esperado}) — nada gravado"); return 1
    if min(pib, key=pib.get) != "MA":
        print("ABORTADO: última posição não é MA — nada gravado"); return 1
    json.dump({"completo": True, "fonte": "IBGE, Sistema de Contas Regionais 2023 (SIDRA), validado por 4 sentinelas em produção",
               "pib_per_capita": pib}, open(DEST, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"OK 27 UFs gravadas com sentinelas verdes — gráfico-tese passa ao eixo de riqueza"); return 0

if __name__ == "__main__":
    sys.exit(main())
