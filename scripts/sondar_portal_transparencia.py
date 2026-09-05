#!/usr/bin/env python3
"""
sondar_portal_transparencia.py — 2ª rodada (05/09/2026): a chave é válida no endpoint de
DESPESAS (a 1ª rodada provou: 400 com mensagem de filtros, não 403). Esta sonda descobre os
nomes de parâmetros e a forma da resposta para puxar a execução (empenhado/liquidado/pago) das
duas MPs do ciclo: MP 1.367 (MMA: Ibama 44201, ICMBio 44207) e MP 1.384 (MDA/Conab, MDS).
NUNCA imprime a chave.
"""
import json, os, urllib.error, urllib.parse, urllib.request

API = "https://api.portaldatransparencia.gov.br/api-de-dados"

def testar(caminho, chave, params):
    url = f"{API}{caminho}?{urllib.parse.urlencode(params)}"
    print(f"\n-- {caminho} {params}")
    req = urllib.request.Request(url, headers={"chave-api-dados": chave.strip(), "User-Agent": "MonitorElNinoBrasil/3.0", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            corpo = r.read(3000).decode("utf-8", "replace")
            print(f"   -> HTTP {r.status} | {corpo[:1200]}")
    except urllib.error.HTTPError as e:
        print(f"   -> HTTPError {e.code} | {e.read(500)!r}")
    except Exception as e:  # noqa: BLE001
        print(f"   -> {type(e).__name__}: {e}")

def main():
    chave = os.environ.get("PORTAL_TRANSPARENCIA_API_KEY", "")
    print("chave presente:", bool(chave), "| comprimento:", len(chave))
    if not chave: return
    # variantes de nome de parâmetro para descobrir a forma aceita
    for params in ({"ano": 2026, "orgao": "44201", "pagina": 1}, {"ano": 2026, "codigoOrgao": "44201", "pagina": 1},
                   {"ano": 2026, "orgaoSuperior": "44000", "pagina": 1}, {"ano": 2026, "codigoOrgaoSuperior": "44000", "pagina": 1}):
        testar("/despesas/por-orgao", chave, params)
    # documentos de despesa (empenhos) por órgão/período — forma provável
    for params in ({"unidadeGestora": "443001", "dataEmissaoInicial": "15/06/2026", "dataEmissaoFinal": "05/09/2026", "fase": 1, "pagina": 1},
                   {"codigoOrgao": "44201", "dataEmissaoInicial": "15/06/2026", "dataEmissaoFinal": "05/09/2026", "fase": 1, "pagina": 1}):
        testar("/despesas/documentos", chave, params)
    testar("/despesas/por-funcional", chave, {"ano": 2026, "codigoFuncao": "18", "pagina": 1})
    testar("/despesas/por-orgao", chave, {"ano": 2026, "orgao": "22211", "pagina": 1})   # Conab?
    testar("/despesas/por-orgao", chave, {"ano": 2026, "orgao": "55000", "pagina": 1})   # MDS
    testar("/despesas/por-orgao", chave, {"ano": 2026, "orgao": "44207", "pagina": 1})   # ICMBio

if __name__ == "__main__":
    main()
