#!/usr/bin/env python3
"""
sondar_transferegov.py — sonda de UMA VEZ (04/09/2026) para desenhar o coletor do
TransfereGov com evidência: lista o repositório de CSVs do módulo Discricionárias e
Legais e testa as APIs PostgREST públicas (sem chave) de Fundo a Fundo e Transferências
Especiais, imprimindo status, cabeçalhos e amostra de cada resposta. Nada é gravado em data/.
"""
import json, re, urllib.request, urllib.error

UA = {"User-Agent": "Mozilla/5.0 (MonitorElNino/sonda)", "Accept": "application/json, text/csv, */*"}

def baixar(url, limite=300_000):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
        return r.read(limite).decode("utf-8", "replace"), r.headers.get("Content-Type", "?"), r.status, r.headers.get("Content-Length")

def testar(url):
    try:
        corpo, ct, st, cl = baixar(url, 1200)
        return f"HTTP {st} | {ct} | len={cl} | {corpo[:400]!r}"
    except urllib.error.HTTPError as e:
        return f"HTTPError {e.code} | {e.read(300)!r}"
    except Exception as e:  # noqa: BLE001
        return f"{type(e).__name__}: {e}"

print("=== REPOSITÓRIO DE CSVs (Discricionárias e Legais) ===")
for u in ["http://repositorio.dados.gov.br/seges/detru/", "https://repositorio.dados.gov.br/seges/detru/"]:
    print(f"\n-- {u}")
    try:
        corpo, ct, st, _ = baixar(u, 400_000)
        links = re.findall(r'href="([^"?][^"]*)"', corpo)
        tam = dict(re.findall(r'href="([^"]+\.csv(?:\.zip)?)"[^\n]*?(\d[\d.,]*\s*[KMG]?)', corpo))
        print(f"   HTTP {st} | {len(links)} links")
        for l in links:
            if l.endswith((".csv", ".zip", ".txt", ".pdf")): print("    ", l, tam.get(l, ""))
    except Exception as e:  # noqa: BLE001
        print(f"   !! {type(e).__name__}: {e}")

print("\n=== APIs PostgREST públicas ===")
for u in [
    "https://api.transferegov.gestao.gov.br/fundoafundo/programa?limit=3",
    "https://api.transferegov.gestao.gov.br/fundoafundo/programa?ano_programa=eq.2026&limit=5",
    "https://api.transferegov.gestao.gov.br/fundoafundo/",
    "https://api.transferegov.gestao.gov.br/transferenciasespeciais/programa_especial?ano_programa=eq.2026&limit=3",
    "https://api.transferegov.gestao.gov.br/transferenciasespeciais/",
    "https://api.transferegov.gestao.gov.br/ted/",
    "https://api-publica.transferegov.gestao.gov.br/",
    "https://api-publica.transferegov.gestao.gov.br/gestaoparcerias/",
    "https://api-publica.transferegov.gestao.gov.br/transferenciasespeciais/",
]:
    print(f"\n-- {u}\n   -> {testar(u)}")
