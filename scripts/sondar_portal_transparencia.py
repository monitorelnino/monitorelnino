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

def sondar_execucao_mensal():
    """4ª rodada (05/09/2026): arquivo mensal 'Execução da Despesa' (download aberto, sem chave):
    lista cabeçalho e as linhas das ações das MPs (2130 Conab; ações de incêndio/fiscalização do Ibama e ICMBio)."""
    import io, zipfile, csv, re
    for mes in ("202608", "202607"):
        url = f"https://portaldatransparencia.gov.br/download-de-dados/despesas-execucao/{mes}"
        print(f"\n=== execução mensal {mes}: {url}")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (MonitorElNino/sonda)"})
            with urllib.request.urlopen(req, timeout=600) as r:
                bruto = r.read()
            print(f"   bytes: {len(bruto):,}")
            z = zipfile.ZipFile(io.BytesIO(bruto)); print("   arquivos:", z.namelist())
            nome = [n for n in z.namelist() if n.lower().endswith(".csv")][0]
            with z.open(nome) as f:
                txt = io.TextIOWrapper(f, encoding="latin-1", errors="replace", newline="")
                rd = csv.reader(txt, delimiter=";"); cab = next(rd); print("   colunas:", cab)
                ia = next((i for i, c in enumerate(cab) if re.search(r"Ação", c, re.I) and "Nome" not in c), None)
                ino = next((i for i, c in enumerate(cab) if re.search(r"Nome Ação|Ação.*Nome|Nome da Ação", c, re.I)), None)
                iorg = next((i for i, c in enumerate(cab) if re.search(r"Nome Órgão|Órgão.*Nome|Nome do Órgão", c, re.I)), None)
                n = 0; achados = []
                for row in rd:
                    n += 1
                    if len(row) <= max(x or 0 for x in (ia, ino, iorg)): continue
                    acao = row[ia] if ia is not None else ""; nome_a = row[ino] if ino is not None else ""; org = row[iorg] if iorg is not None else ""
                    if acao == "2130" or re.search(r"INC[ÊE]NDI|QUEIMAD|FISCALIZA[ÇC][ÃA]O AMBIENTAL|DISTRIBUI[ÇC][ÃA]O DE ALIMENTOS|ESTOQUES P[ÚU]BLICOS", nome_a, re.I):
                        if re.search(r"IBAMA|CHICO MENDES|ABASTECIMENTO|DESENVOLVIMENTO E ASSIST|MEIO AMBIENTE", org, re.I):
                            achados.append(row)
                print(f"   linhas: {n:,} | achados nas ações das MPs: {len(achados)}")
                for r_ in achados[:25]: print("     ", [c[:40] for c in r_])
        except Exception as e:  # noqa: BLE001
            print(f"   !! {type(e).__name__}: {e}")
        break

def main():
    chave = os.environ.get("PORTAL_TRANSPARENCIA_API_KEY", "")
    print("chave presente:", bool(chave), "| comprimento:", len(chave))
    sondar_execucao_mensal()

if __name__ == "__main__":
    main()
