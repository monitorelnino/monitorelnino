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
from coletores_base import ler, gravar, registrar_lacuna, log_busca, rodar_autoteste, ua_de, hoje_editorial

BASE = "https://portaldatransparencia.gov.br/download-de-dados/despesas-execucao/"
UA = {"User-Agent": ua_de("execução das MPs")}
UFS = {"AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT","PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO"}

# (id da MP, órgão subordinado/superior, ações) — vocabulário do arquivo, códigos confirmados
ALVOS = {
    "mp1367": {"primeiro_mes": "202606", "orgaos": {"20701": {"nome": "Ibama", "acoes": {"214M", "214N"}}, "44207": {"nome": "ICMBio", "acoes": {"214P"}}}},
    "mp1384": {"primeiro_mes": "202608", "orgaos": {"22211": {"nome": "MDA / Conab", "acoes": {"2130"}}, "55000": {"nome": "MDS", "acoes": {"2792", "2798"}}}},
}


def numero(v):
    """'1.000,50' → 1000.5; vazio ou ilegível → None (A6-22, 10/10/2026: virava 0.0, e célula
    vazia entrava na soma como execução zero medida)."""
    t = str(v if v is not None else "").strip()
    if not t:
        return None
    try:
        return float(t.replace(".", "").replace(",", "."))
    except ValueError:
        return None


def somar(a, b):
    """Soma só o que está presente: None + None = None (lacuna), None + x = x."""
    if a is None:
        return b
    return a if b is None else a + b


def arred(v):
    return None if v is None else round(v, 2)


def _fmt(v) -> str:
    return "sem valor declarado" if v is None else f"{v:,.0f}"


def mes_parcial(mes: str, hoje) -> bool:
    """O mês corrente na data da coleta: o Portal ainda está preenchendo o arquivo (A6-13)."""
    return mes == f"{hoje.year}{hoje.month:02d}"


def uf_da_linha(row: dict) -> str:
    """UF da unidade gestora: coluna UF se válida; senão sufixo '/UF' do nome da UG; senão 'BR' (nacional)."""
    uf = (row.get("UF") or "").strip().upper()
    if uf in UFS:
        return uf
    m = re.search(r"/\s*([A-Z]{2})\s*$", (row.get("Nome Unidade Gestora") or "").strip().upper())
    return m.group(1) if m and m.group(1) in UFS else "BR"


# Modalidade de aplicação, pelos códigos do orçamento federal. A fonte traz o código e, em alguns
# arquivos, o nome; o código é a chave, porque o nome varia de grafia entre meses. Agrupa-se em
# quatro categorias de leitor, e o que não casar entra como "outras formas" — nunca é descartado,
# porque a soma das categorias tem de fechar com o desembolsado.
MODALIDADES = {
    "90": "aplicados diretamente pela União",
    "91": "aplicados diretamente pela União",
    "99": "aplicados diretamente pela União",
    "30": "transferidos aos estados",
    "31": "transferidos aos estados",
    "32": "transferidos aos estados",
    "35": "transferidos aos estados",
    "40": "transferidos aos municípios",
    "41": "transferidos aos municípios",
    "42": "transferidos aos municípios",
    "45": "transferidos aos municípios",
    "50": "transferidos a entidades sem fins lucrativos",
    "80": "transferidos ao exterior",
}
OUTRAS_FORMAS = "outras formas de aplicação"


def modalidade_da_linha(row: dict) -> str:
    """A categoria de aplicação desta linha. Função pura.

    Lê o CÓDIGO da modalidade; sem código legível, devolve "outras formas de aplicação" — e não
    uma categoria inventada, porque a soma tem de fechar com o desembolsado.
    """
    bruto = ""
    # MEDIDO em 02/10/2026 no arquivo mensal do Portal: a coluna se chama "Código Modalidade da
    # Despesa" (e "Modalidade da Despesa" para o nome). Os outros nomes ficam como reserva, porque
    # a grafia do Portal já mudou antes e o §219 nasceu exatamente disso.
    for chave in ("Código Modalidade da Despesa", "Modalidade da Despesa",
                  "Código Modalidade de Aplicação", "Codigo Modalidade de Aplicacao",
                  "Código Modalidade Aplicação", "Modalidade de Aplicação"):
        if row.get(chave):
            bruto = str(row[chave]).strip()
            break
    m = re.match(r"(\d{2})", bruto)
    return MODALIDADES.get(m.group(1), OUTRAS_FORMAS) if m else OUTRAS_FORMAS


def agregar(linhas, alvos: dict = ALVOS) -> dict:
    """{mp: {'orgaos': {codigo: {empenhado, liquidado, pago}}, 'por_uf_pago': {UF: v}, 'empenhado','liquidado','pago'}}
    Só linhas cujo (órgão, ação) está nos alvos. Função pura, testável."""
    out = {mp: {"orgaos": {c: {"empenhado": None, "liquidado": None, "pago": None} for c in a["orgaos"]},
                "por_uf_pago": defaultdict(float), "por_modalidade_pago": defaultdict(float),
                "empenhado": None, "liquidado": None, "pago": None} for mp, a in alvos.items()}
    for row in linhas:
        cod_sub = (row.get("Código Órgão Subordinado") or "").strip(); cod_sup = (row.get("Código Órgão Superior") or "").strip()
        acao = (row.get("Código Ação") or "").strip()
        for mp, a in alvos.items():
            for cod_org, spec in a["orgaos"].items():
                if acao in spec["acoes"] and (cod_sub == cod_org or (cod_org == "55000" and cod_sup == "55000")):
                    e, l, p = numero(row.get("Valor Empenhado (R$)")), numero(row.get("Valor Liquidado (R$)")), numero(row.get("Valor Pago (R$)"))
                    o = out[mp]["orgaos"][cod_org]
                    for k, v in (("empenhado", e), ("liquidado", l), ("pago", p)):
                        o[k] = somar(o[k], v); out[mp][k] = somar(out[mp][k], v)
                    if p:   # só o que foi pago entra no destino (estornos e empenhos sem pagamento não desenham mapa)
                        out[mp]["por_uf_pago"][uf_da_linha(row)] += p
                        out[mp]["por_modalidade_pago"][modalidade_da_linha(row)] += p
    for mp in out:
        out[mp]["por_uf_pago"] = {k: round(v, 2) for k, v in out[mp]["por_uf_pago"].items()}
        out[mp]["por_modalidade_pago"] = {k: round(v, 2)
                                          for k, v in out[mp]["por_modalidade_pago"].items()}
        for k in ("empenhado", "liquidado", "pago"): out[mp][k] = arred(out[mp][k])
        for o in out[mp]["orgaos"].values():
            for k in o: o[k] = arred(o[k])
    return out


def _linhas_do_zip(bruto: bytes):
    z = zipfile.ZipFile(io.BytesIO(bruto)); nome = [n for n in z.namelist() if n.lower().endswith(".csv")][0]
    with z.open(nome) as f:
        txt = io.TextIOWrapper(f, encoding="latin-1", errors="replace", newline="")
        for row in csv.DictReader(txt, delimiter=";"):
            yield row


def meses_ate_hoje(primeiro: str) -> list:
    ano, mes = int(primeiro[:4]), int(primeiro[4:]); hoje = hoje_editorial(); out = []
    while (ano, mes) <= (hoje.year, hoje.month):
        out.append(f"{ano}{mes:02d}"); mes += 1
        if mes > 12: ano, mes = ano + 1, 1
    return out


def coletar() -> int:
    hoje = hoje_editorial().strftime("%d/%m/%Y")
    mps = ler("financiamento/mps_2026.json", {}) or {}
    if not mps.get("mps"):
        print("execucao_mps: sem mps_2026.json — nada a fazer"); return 0
    primeiro = min(a["primeiro_mes"] for a in ALVOS.values())
    # 02/10/2026 (item 4 do contrato de layout): alem do acumulado, guarda-se a quebra POR MES.
    # O Portal publica execucao por mes, e o cartao do topo do Financiamento diz "no mes de X":
    # sem esta quebra o gerador so teria o acumulado do ciclo e o cartao ficaria sem dado.
    acumulado = {mp: {"orgaos": {c: {"empenhado": None, "liquidado": None, "pago": None} for c in a["orgaos"]}, "por_uf_pago": defaultdict(float),
                      "por_mes": {}, "por_modalidade_pago": defaultdict(float),
                      "empenhado": None, "liquidado": None, "pago": None} for mp, a in ALVOS.items()}
    dia = hoje_editorial()
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
            for k in ("empenhado", "liquidado", "pago"): acumulado[mp][k] = somar(acumulado[mp][k], parcial[mp][k])
            acumulado[mp]["por_mes"][mes] = {k: arred(parcial[mp][k])
                                             for k in ("empenhado", "liquidado", "pago")}
            # A6-13: o mês corrente é lido com o arquivo ainda sendo preenchido; marca-se parcial
            # para nenhum consumidor o apresentar como mês fechado.
            if mes_parcial(mes, dia):
                acumulado[mp]["por_mes"][mes]["parcial"] = True
            for c, o in parcial[mp]["orgaos"].items():
                for k in o: acumulado[mp]["orgaos"][c][k] = somar(acumulado[mp]["orgaos"][c][k], o[k])
            for uf, v in parcial[mp]["por_uf_pago"].items(): acumulado[mp]["por_uf_pago"][uf] += v
            for m_, v in parcial[mp]["por_modalidade_pago"].items():
                acumulado[mp]["por_modalidade_pago"][m_] += v
    if not meses_lidos:
        print("execucao_mps: nenhum arquivo mensal lido — lacuna declarada, nada alterado"); return 0
    # 25/09/2026 (§219): o filtro depende dos NOMES das colunas do Portal ("Código Órgão
    # Subordinado", "Código Ação"). Se algum for renomeado, nenhuma linha casa, todo total fica
    # 0,00 — e a checagem acima não pega, porque ela só confere se o ZIP baixou. O site passaria
    # a dizer que as MPs não executaram nada. Nenhuma linha casada é LEITURA QUEBRADA, não
    # execução zero: declara-se a lacuna e não se toca no que já estava gravado.
    if not any(a["empenhado"] or a["liquidado"] or a["pago"] for a in acumulado.values()):
        registrar_lacuna("Execução das MPs (Portal da Transparência)",
                         f"{len(meses_lidos)} arquivo(s) mensal(is) lido(s) e NENHUMA linha casou com o "
                         "filtro de órgão/ação — nomes de coluna a reverificar; execução anterior mantida",
                         canal="DOU", camada=1)
        print("execucao_mps: arquivos lidos e nenhuma linha casada — lacuna declarada, nada alterado")
        return 0
    for mp in mps["mps"]:
        a = acumulado.get(mp["id"]);
        if not a: continue
        mp["execucao"] = {"status": "coletado", "fonte": "Portal da Transparência — Execução da Despesa (arquivos mensais abertos)",
                          "empenhado": arred(a["empenhado"]), "liquidado": arred(a["liquidado"]), "pago": arred(a["pago"]),
                          "meses": [m for m in meses_lidos if m >= ALVOS[mp["id"]]["primeiro_mes"]], "atualizado_em": hoje,
                          "meses_parciais": [m for m in meses_lidos if m >= ALVOS[mp["id"]]["primeiro_mes"] and mes_parcial(m, dia)],
                          "por_mes": dict(sorted(a["por_mes"].items())),
                          "limite": "execução das AÇÕES reforçadas pela MP desde o mês de publicação — inclui a dotação ordinária da ação; teto, não a execução do crédito"}
        for org in mp["orgaos"]:
            cod = next((c for c, s in ALVOS[mp["id"]]["orgaos"].items() if s["nome"] == org["nome"]), None)
            if cod:
                org["execucao_empenhado"] = arred(a["orgaos"][cod]["empenhado"]); org["execucao_pago"] = arred(a["orgaos"][cod]["pago"])
                org["acoes"] = sorted(ALVOS[mp["id"]]["orgaos"][cod]["acoes"])
        # A forma de aplicação é o que o cartão "Como os recursos estão sendo aplicados" lê. Ela
        # responde "a quem o dinheiro foi", e é diferente de `destino`, que diz onde o pagamento foi
        # REGISTRADO (sede da unidade gestora) — a distinção está na METODOLOGIA.
        mp["forma_de_aplicacao"] = {
            "status": "coletado",
            "medida": "valor desembolsado por modalidade de aplicação do orçamento federal",
            "por_modalidade": {k: round(v, 2) for k, v in
                               sorted(a["por_modalidade_pago"].items(), key=lambda x: -x[1])},
            "atualizado_em": hoje}
        mp["destino"] = {"status": "coletado", "medida": "valor pago por UF da unidade gestora (BR = unidade nacional)",
                         "por_uf_pago": {k: round(v, 2) for k, v in sorted(a["por_uf_pago"].items(), key=lambda x: -x[1])}, "atualizado_em": hoje}
    mps["gerado_em"] = hoje; mps["hashes_arquivos_mensais"] = hashes
    gravar("financiamento/mps_2026.json", mps)
    log_busca("DOU", 1, [BASE + m for m in meses_lidos], "registro", nivel="nacional", n_resultados=len(meses_lidos),
              resultados="Execução das ações das MPs 1.367 e 1.384: " + "; ".join(f"{mp['numero']} pago R$ {_fmt(mp['execucao']['pago'])} ({', '.join(mp['execucao']['meses'])})" for mp in mps["mps"]))
    print("execucao_mps:", "; ".join(f"{mp['numero']}: empenhado {_fmt(mp['execucao']['empenhado'])} pago {_fmt(mp['execucao']['pago'])}" for mp in mps["mps"]))
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
    def t7(): return (modalidade_da_linha({"Código Modalidade de Aplicação": "90"})
                      == "aplicados diretamente pela União"
                      and modalidade_da_linha({"Código Modalidade de Aplicação": "41 - Transf"})
                      == "transferidos aos municípios")
    def t8(): return (modalidade_da_linha({"Modalidade de Aplicação": "sem código"}) == OUTRAS_FORMAS
                      and modalidade_da_linha({}) == OUTRAS_FORMAS)
    def t9():
        # As linhas do caso nao trazem o campo: o agregado guarda "outras formas", e a soma
        # fecha com o desembolsado. Com o campo, a categoria aparece pelo codigo.
        sem = r["mp1367"]["por_modalidade_pago"]
        com = agregar([dict(L[0], **{"Código Modalidade de Aplicação": "41"})])["mp1367"]
        return (round(sum(sem.values()), 2) == r["mp1367"]["pago"]
                and "transferidos aos municípios" in com["por_modalidade_pago"])
    def t6(): return meses_ate_hoje("202606")[0] == "202606" and all(len(m) == 6 for m in meses_ate_hoje("202606")) and numero("abc") is None
    def t10():
        # A6-22: célula vazia é ausência — fica fora da soma; tudo vazio dá None (lacuna), não 0.0
        vazio = dict(L[0], **{"Valor Empenhado (R$)": "", "Valor Liquidado (R$)": "", "Valor Pago (R$)": ""})
        so_vazio = agregar([vazio])["mp1367"]
        com = agregar([vazio, L[2]])["mp1367"]
        return (numero("") is None and numero("0,00") == 0.0 and somar(None, None) is None and somar(None, 2.0) == 2.0
                and so_vazio["pago"] is None and so_vazio["orgaos"]["20701"]["empenhado"] is None
                and com["pago"] == 300.0 and com["orgaos"]["20701"]["pago"] is None)
    def t11():
        # A6-13: o mês corrente da coleta é parcial; o anterior, não
        from datetime import date as _d
        return mes_parcial("202610", _d(2026, 10, 10)) and not mes_parcial("202609", _d(2026, 10, 10))
    return rodar_autoteste({"agrega por MP e órgão (empenhado/pago)": t1, "destino por UF (nome da UG ou coluna)": t2,
                            "MP 1.384: MDS por órgão superior, Conab por subordinado": t3, "negativo: ação fora dos alvos ignorada": t4,
                            "UF: sufixo '/UF' e fallback BR": t5, "meses e números malformados": t6,
                            "modalidade pelo código do orçamento": t7,
                            "modalidade ilegível não inventa categoria": t8,
                            "o agregado guarda o desembolsado por modalidade": t9,
                            "valor vazio é ausência, soma só os presentes (A6-22)": t10,
                            "mês corrente da coleta é parcial (A6-13)": t11})


if __name__ == "__main__":
    sys.exit(autoteste() if "--autoteste" in sys.argv else coletar())
