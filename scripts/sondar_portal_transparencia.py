#!/usr/bin/env python3
"""
sondar_portal_transparencia.py — 2ª rodada (05/09/2026): a chave é válida no endpoint de
DESPESAS (a 1ª rodada provou: 400 com mensagem de filtros, não 403). Esta sonda descobre os
nomes de parâmetros e a forma da resposta para puxar a execução (empenhado/liquidado/pago) das
duas MPs do ciclo: MP 1.367 (MMA: Ibama 44201, ICMBio 44207) e MP 1.384 (MDA/Conab, MDS).
NUNCA imprime a chave.
"""
import json, os, pathlib, sys, urllib.error, urllib.parse, urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from coletores_base import ua_de  # noqa: E402

API = "https://api.portaldatransparencia.gov.br/api-de-dados"

def testar(caminho, chave, params):
    url = f"{API}{caminho}?{urllib.parse.urlencode(params)}"
    print(f"\n-- {caminho} {params}")
    req = urllib.request.Request(url, headers={"chave-api-dados": chave.strip(), "User-Agent": ua_de("sonda Portal da Transparência"), "Accept": "application/json"})
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
            req = urllib.request.Request(url, headers={"User-Agent": ua_de("sonda Portal da Transparência")})
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

def sondar_empenho_dotacao():
    """5ª rodada (26/10/2026, vias 3 e 4 do HANDOVER_EXECUCAO_CREDITOS_MPS): descobre qual download aberto
    traz a observação do empenho e qual traz a dotação inicial/atualizada. Só imprime cabeçalho, nomes
    de arquivo e contagens nas ações das MPs; não grava nada em data/."""
    import io, zipfile, csv, re
    try:  # o índice público lista os conjuntos de dados reais (os palpites de URL deram 403/500)
        req = urllib.request.Request("https://portaldatransparencia.gov.br/download-de-dados", headers={"User-Agent": ua_de("sonda Portal da Transparência")})
        with urllib.request.urlopen(req, timeout=120) as r:
            html = r.read().decode("utf-8", "replace")
        print("   índice:", sorted(set(re.findall(r'download-de-dados/([a-z0-9-]+)', html))))
    except Exception as e:  # noqa: BLE001
        print(f"   !! índice: {type(e).__name__}: {e}")
    cand = ["orcamento-despesa/2026"]
    acoes = {"2130", "2792", "2798", "214M", "214N", "214P"}
    for c in cand:
        url = f"https://portaldatransparencia.gov.br/download-de-dados/{c}"
        print(f"\n=== {url}")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": ua_de("sonda Portal da Transparência")})
            with urllib.request.urlopen(req, timeout=900) as r:
                ct = r.headers.get("Content-Type"); bruto = r.read()
            print(f"   HTTP ok | {ct} | bytes: {len(bruto):,} | zip: {bruto[:2] == b'PK'}")
            if bruto[:2] != b"PK":
                continue
            z = zipfile.ZipFile(io.BytesIO(bruto)); print("   arquivos:", z.namelist())
            for nome in [n for n in z.namelist() if n.lower().endswith(".csv")]:
                with z.open(nome) as f:
                    rd = csv.reader(io.TextIOWrapper(f, encoding="latin-1", errors="replace", newline=""), delimiter=";")
                    cab = next(rd); print(f"   [{nome}] colunas:", cab)
                    ia = next((i for i, x in enumerate(cab) if re.fullmatch(r"C[óo]digo A[çc][ãa]o", x, re.I)), None)
                    iobs = [i for i, x in enumerate(cab) if re.search(r"Observa|Descri", x, re.I)]
                    n = m = o = 0
                    for row in rd:
                        n += 1
                        if ia is None or len(row) <= ia or row[ia] not in acoes:
                            continue
                        m += 1
                        txt = " ".join(row[i] for i in iobs if i < len(row))
                        if re.search(r"cr[ée]dito extraordin|\bMP\b|medida provis|el ni[ñn]o", txt, re.I):
                            o += 1
                            if o <= 5: print("      obs:", [x[:60] for x in row[:6]], "|", txt[:200])
                        if m <= 8: print("      amostra:", [x[:30] for x in row[:2] + row[7:15] + row[19:]])
                    print(f"   linhas: {n:,} | nas ações das MPs: {m} | com menção a MP/crédito/El Niño: {o}")
        except Exception as e:  # noqa: BLE001
            print(f"   !! {type(e).__name__}: {e}")

def main():
    chave = os.environ.get("PORTAL_TRANSPARENCIA_API_KEY", "")
    print("chave presente:", bool(chave), "| comprimento:", len(chave))
    sondar_execucao_mensal()
    sondar_empenho_dotacao()

if __name__ == "__main__":
    main()
