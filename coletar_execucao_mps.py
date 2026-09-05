#!/usr/bin/env python3
"""
coletar_execucao_mps.py
=======================
Execução das ações orçamentárias reforçadas pelas MPs do ciclo (05/09/2026), a partir dos
arquivos mensais abertos "Execução da Despesa" do Portal da Transparência (sem chave):
  https://portaldatransparencia.gov.br/download-de-dados/despesas-execucao/AAAAMM

Ações confirmadas no arquivo de 08/2026 (sonda de 05/09/2026):
  MP 1.367 → Ibama (órgão 20701): 214M prevenção e controle de incêndios; 214N fiscalização
             ICMBio (órgão 44207): 214P fiscalização ambiental e prevenção
  MP 1.384 → Conab (órgão 22211): 2130 formação de estoques públicos
             MDS (órgão superior 55000): 2792 e 2798 distribuição/aquisição de alimentos

LIMITE DECLARADO: o arquivo não separa a fonte do dinheiro. O que se soma é a execução
da AÇÃO desde o mês da MP — que inclui a dotação ordinária da mesma ação. É um teto para a
execução do crédito extraordinário, nunca a execução "da MP". A figura diz isso na legenda.
Destino: a unidade gestora traz a UF no nome ("… SUPERINTENDENCIA DO AMAPA/AP") ou na
coluna UF — soma por estado do que foi PAGO.

Sem rede: lacuna declarada, nada muda.  python coletar_execucao_mps.py --autoteste
"""
import csv, hashlib, io, json, re, sys, urllib.request, zipfile
from collections import defaultdict
from datetime import date
from coletores_base import ler, gravar, registrar_lacuna, log_busca, rodar_autoteste

BASE = "https://portaldatransparencia.gov.br/download-de-dados/despesas-execucao/"
UA = {"User-Agent": "MonitorElNinoBrasil/3.0 (coletor execução das MPs; dados abertos)"}
UFS = {"AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT","PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO"}

# (id da MP, órgão subordinado/superior, ações) — vocabulário do arquivo, códigos confirmados
ALVOS = {
    "mp1367": {"primeiro_mes": "202606", "orgaos": {"20701": {"nome": "Ibama", "acoes": {"214M", "214N"}}, "44207": {"nome": "ICMBio", "acoes": {"214P"}}}},
    "mp1384": {"primeiro_mes": "202608", "orgaos": {"22211": {"nome": "MDA / Conab", "acoes": {"2130"}}, "55000": {"nome": "MDS", "acoes": {"2792", "2798"}}}},
}


def numero(v) -> float:
    try:
        return float(str(v or "0").replace(".", "").replace(",", "."))
    except ValueError:
        return 0.0


def uf_da_linha(row: dict) -> str:
    """UF da unidade gestora: coluna UF se válida; senão sufixo '/UF' do nome da UG; senão 'BR' (nacional)."""
    uf = (row.get("UF") or "").strip().upper()
    if uf in UFS:
        return uf
    m = re.search(r"/\s*([A-Z]{2})\s*$", (row.get("Nome Unidade Gestora") or "").strip().upper())
    return m.group(1) if m and m.group(1) in UFS else "BR"


def agregar(linhas, alvos: dict = ALVOS) -> dict:
    """{mp: {'orgaos': {codigo: {empenhado, liquidado, pago}}, 'por_uf_pago': {UF: v}, 'empenhado','liquidado','pago'}}
    Só linhas cujo (órgão, ação) está nos alvos. Função pura, testável."""
    out = {mp: {"orgaos": {c: {"empenhado": 0.0, "liquidado": 0.0, "pago": 0.0} for c in a["orgaos"]},
                "por_uf_pago": defaultdict(float), "empenhado": 0.0, "liquidado": 0.0, "pago": 0.0} for mp, a in alvos.items()}
    for row in linhas:
        cod_sub = (row.get("Código Órgão Subordinado") or "").strip(); cod_sup = (row.get("Código Órgão Superior") or "").strip()
        acao = (row.get("Código Ação") or "").strip()
        for mp, a in alvos.items():
            for cod_org, spec in a["orgaos"].items():
                if acao in spec["acoes"] and (cod_sub == cod_org or (cod_org == "55000" and cod_sup == "55000")):
                    e, l, p = numero(row.get("Valor Empenhado (R$)")), numero(row.get("Valor Liquidado (R$)")), numero(row.get("Valor Pago (R$)"))
                    o = out[mp]["orgaos"][cod_org]; o["empenhado"] += e; o["liquidado"] += l; o["pago"] += p
                    out[mp]["empenhado"] += e; out[mp]["liquidado"] += l; out[mp]["pago"] += p
                    if p:   # só o que foi pago entra no destino (estornos e empenhos sem pagamento não desenham mapa)
                        out[mp]["por_uf_pago"][uf_da_linha(row)] += p
    for mp in out:
        out[mp]["por_uf_pago"] = {k: round(v, 2) for k, v in out[mp]["por_uf_pago"].items()}
        for k in ("empenhado", "liquidado", "pago"): out[mp][k] = round(out[mp][k], 2)
        for o in out[mp]["orgaos"].values():
            for k in o: o[k] = round(o[k], 2)
    return out


def _linhas_do_zip(bruto: bytes):
    z = zipfile.ZipFile(io.BytesIO(bruto)); nome = [n for n in z.namelist() if n.lower().endswith(".csv")][0]
    with z.open(nome) as f:
        txt = io.TextIOWrapper(f, encoding="latin-1", errors="replace", newline="")
        for row in csv.DictReader(txt, delimiter=";"):
            yield row


def meses_ate_hoje(primeiro: str) -> list:
    ano, mes = int(primeiro[:4]), int(primeiro[4:]); hoje = date.today(); out = []
    while (ano, mes) <= (hoje.year, hoje.month):
        out.append(f"{ano}{mes:02d}"); mes += 1
        if mes > 12: ano, mes = ano + 1, 1
    return out


def coletar() -> int:
    hoje = date.today().strftime("%d/%m/%Y")
    mps = ler("financiamento/mps_2026.json", {}) or {}
    if not mps.get("mps"):
        print("execucao_mps: sem mps_2026.json — nada a fazer"); return 0
    primeiro = min(a["primeiro_mes"] for a in ALVOS.values())
    acumulado = {mp: {"orgaos": {c: {"empenhado": 0.0, "liquidado": 0.0, "pago": 0.0} for c in a["orgaos"]}, "por_uf_pago": defaultdict(float),
                      "empenhado": 0.0, "liquidado": 0.0, "pago": 0.0} for mp, a in ALVOS.items()}
    meses_lidos, hashes = [], {}
    for mes in meses_ate_hoje(primeiro):
        try:
            with urllib.request.urlopen(urllib.request.Request(BASE + mes, headers=UA), timeout=900) as r:
                bruto = r.read()
            zipfile.ZipFile(io.BytesIO(bruto))
        except Exception as e:  # noqa: BLE001
            registrar_lacuna(f"Portal — execução mensal {mes}", f"{type(e).__name__}: {e}", canal="DOU", camada=1, strings=[BASE + mes]); continue
        parcial = agregar(_linhas_do_zip(bruto))
        hashes[mes] = hashlib.sha256(bruto).hexdigest(); meses_lidos.append(mes)
        for mp, a in ALVOS.items():
            if mes < a["primeiro_mes"]:
                continue
            for k in ("empenhado", "liquidado", "pago"): acumulado[mp][k] += parcial[mp][k]
            for c, o in parcial[mp]["orgaos"].items():
                for k in o: acumulado[mp]["orgaos"][c][k] += o[k]
            for uf, v in parcial[mp]["por_uf_pago"].items(): acumulado[mp]["por_uf_pago"][uf] += v
    if not meses_lidos:
        print("execucao_mps: nenhum arquivo mensal lido — lacuna declarada, nada alterado"); return 0
    for mp in mps["mps"]:
        a = acumulado.get(mp["id"]);
        if not a: continue
        mp["execucao"] = {"status": "coletado", "fonte": "Portal da Transparência — Execução da Despesa (arquivos mensais abertos)",
                          "empenhado": round(a["empenhado"], 2), "liquidado": round(a["liquidado"], 2), "pago": round(a["pago"], 2),
                          "meses": [m for m in meses_lidos if m >= ALVOS[mp["id"]]["primeiro_mes"]], "atualizado_em": hoje,
                          "limite": "execução das AÇÕES reforçadas pela MP desde o mês de publicação — inclui a dotação ordinária da ação; teto, não a execução do crédito"}
        for org in mp["orgaos"]:
            cod = next((c for c, s in ALVOS[mp["id"]]["orgaos"].items() if s["nome"] == org["nome"]), None)
            if cod:
                org["execucao_empenhado"] = round(a["orgaos"][cod]["empenhado"], 2); org["execucao_pago"] = round(a["orgaos"][cod]["pago"], 2)
                org["acoes"] = sorted(ALVOS[mp["id"]]["orgaos"][cod]["acoes"])
        mp["destino"] = {"status": "coletado", "medida": "valor pago por UF da unidade gestora (BR = unidade nacional)",
                         "por_uf_pago": {k: round(v, 2) for k, v in sorted(a["por_uf_pago"].items(), key=lambda x: -x[1])}, "atualizado_em": hoje}
    mps["gerado_em"] = hoje; mps["hashes_arquivos_mensais"] = hashes
    gravar("financiamento/mps_2026.json", mps)
    log_busca("DOU", 1, [BASE + m for m in meses_lidos], "registro", nivel="nacional", n_resultados=len(meses_lidos),
              resultados="Execução das ações das MPs 1.367 e 1.384: " + "; ".join(f"{mp['numero']} pago R$ {mp['execucao']['pago']:,.0f} ({', '.join(mp['execucao']['meses'])})" for mp in mps["mps"]))
    print("execucao_mps:", "; ".join(f"{mp['numero']}: empenhado {mp['execucao']['empenhado']:,.0f} pago {mp['execucao']['pago']:,.0f}" for mp in mps["mps"]))
    return 0


def autoteste() -> int:
    L = [{"Código Órgão Superior": "44000", "Código Órgão Subordinado": "20701", "Código Ação": "214M", "Nome Unidade Gestora": "IBAMA - SUPERINTENDENCIA DO AMAPA/AP", "UF": "", "Valor Empenhado (R$)": "1.000,50", "Valor Liquidado (R$)": "500,00", "Valor Pago (R$)": "400,00"},
         {"Código Órgão Superior": "44000", "Código Órgão Subordinado": "20701", "Código Ação": "214N", "Nome Unidade Gestora": "IBAMA-INST.BRAS.", "UF": "", "Valor Empenhado (R$)": "-200,00", "Valor Liquidado (R$)": "0,00", "Valor Pago (R$)": "0,00"},
         {"Código Órgão Superior": "44000", "Código Órgão Subordinado": "44207", "Código Ação": "214P", "Nome Unidade Gestora": "ICMBIO", "UF": "PA", "Valor Empenhado (R$)": "300,00", "Valor Liquidado (R$)": "300,00", "Valor Pago (R$)": "300,00"},
         {"Código Órgão Superior": "55000", "Código Órgão Subordinado": "55101", "Código Ação": "2792", "Nome Unidade Gestora": "MDS", "UF": "", "Valor Empenhado (R$)": "10,00", "Valor Liquidado (R$)": "10,00", "Valor Pago (R$)": "10,00"},
         {"Código Órgão Superior": "44000", "Código Órgão Subordinado": "20701", "Código Ação": "9999", "Nome Unidade Gestora": "IBAMA", "UF": "", "Valor Empenhado (R$)": "999,00", "Valor Liquidado (R$)": "999,00", "Valor Pago (R$)": "999,00"},
         {"Código Órgão Superior": "22000", "Código Órgão Subordinado": "22211", "Código Ação": "2130", "Nome Unidade Gestora": "CONAB", "UF": "DF", "Valor Empenhado (R$)": "5,00", "Valor Liquidado (R$)": "0,00", "Valor Pago (R$)": "0,00"}]
    r = agregar(L)
    def t1(): return r["mp1367"]["empenhado"] == 1100.5 and r["mp1367"]["pago"] == 700.0 and r["mp1367"]["orgaos"]["20701"]["pago"] == 400.0 and r["mp1367"]["orgaos"]["44207"]["pago"] == 300.0
    def t2(): return r["mp1367"]["por_uf_pago"] == {"AP": 400.0, "PA": 300.0}   # UG com '/AP' e coluna UF; estorno sem pago não entra
    def t3(): return r["mp1384"]["orgaos"]["55000"]["pago"] == 10.0 and r["mp1384"]["orgaos"]["22211"]["empenhado"] == 5.0
    def t4(): return "9999" not in str(r) and r["mp1367"]["empenhado"] != 2099.5   # ação fora dos alvos ignorada
    def t5(): return uf_da_linha({"UF": "xx", "Nome Unidade Gestora": "IBAMA - SUP. DO ACRE/AC"}) == "AC" and uf_da_linha({"UF": "", "Nome Unidade Gestora": "IBAMA SEDE"}) == "BR"
    def t6(): return meses_ate_hoje("202606")[0] == "202606" and all(len(m) == 6 for m in meses_ate_hoje("202606")) and numero("abc") == 0.0
    return rodar_autoteste({"agrega por MP e órgão (empenhado/pago)": t1, "destino por UF (nome da UG ou coluna)": t2,
                            "MP 1.384: MDS por órgão superior, Conab por subordinado": t3, "negativo: ação fora dos alvos ignorada": t4,
                            "UF: sufixo '/UF' e fallback BR": t5, "meses e números malformados": t6})


if __name__ == "__main__":
    sys.exit(autoteste() if "--autoteste" in sys.argv else coletar())
