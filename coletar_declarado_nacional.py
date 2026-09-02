#!/usr/bin/env python3
"""
coletar_declarado_nacional.py
=============================
Camada DECLARADA nacional (doc de redesenho §3.9, decisão C5): o que o município
DECLARA ter — MUNIC/IBGE (bloco de defesa civil: possui plano de contingência?)
e ICM/SEDEC (faixa A–D; variável 8: plano de contingência). Produz
`data/declarado_nacional.json`, por município: `munic_plano_contingencia`
(sim/não/NA + ano da edição), `icm_faixa`, `icm_var8_plano_contingencia`.

GOVERNANÇA: esta camada NÃO altera nota antes de 26/10/2026. Até lá só existe
via `recalcular_mare.py --simular-declarado-nacional`, que aplica o desconto de
50% já existente (declarar ≠ publicar, §3.4 da transferência) e grava as 27
notas antes/depois em `data/simulacao_declarado_nacional.json` — anexo público
da metodologia. Regra declarada em 02/09/2026, vigência 26/10/2026 (§12.4).

Fontes (§15, "a verificar"): edição mais recente da MUNIC com bloco de defesa
civil e formato de download do ICM. `data/fontes_declarado.json` guarda url e
status; sem confirmação → lacuna declarada. Os parsers (CSV) são provados por
fixture; a primeira coleta real é da Action.

USO
  python coletar_declarado_nacional.py --autoteste
  python coletar_declarado_nacional.py           # coleta (rede)
"""
import csv, io, sys
from datetime import date
from coletores_base import (buscar, preservar_evidencia, log_busca, registrar_lacuna,
                            marcar_fonte_consultada, marcar_fato_municipal, referencia_ibge,
                            ler, gravar, rodar_autoteste)

FONTES_PADRAO = {"_governanca": "Fontes da camada declarada nacional (v2.2.4, §3.9). Sem url confirmada → lacuna.",
                 "munic": {"nome": "MUNIC/IBGE — bloco Gestão de riscos e desastres", "url": None, "edicao": None,
                           "status": "a_verificar", "coluna_ibge": "CodMun", "coluna_plano": "MGRD_PlanoContingencia"},
                 "icm": {"nome": "ICM/SEDEC — Indicador de Capacidade Municipal", "url": None, "edicao": None,
                         "status": "a_verificar", "coluna_ibge": "codigo_ibge", "coluna_faixa": "faixa",
                         "coluna_var8": "var8_plano_contingencia"}}
SIM = {"sim", "s", "1", "true", "possui"}
NAO = {"não", "nao", "n", "0", "false", "não possui", "nao possui"}


def normalizar_sim_nao(v) -> str:
    t = str(v or "").strip().lower()
    return "sim" if t in SIM else "nao" if t in NAO else "NA"


def parse_munic_csv(texto: str, col_ibge: str, col_plano: str, edicao) -> dict:
    """{ibge7: {"munic_plano_contingencia": sim|nao|NA, "munic_edicao": edicao}}. Função pura."""
    out = {}
    rd = csv.DictReader(io.StringIO(texto), delimiter=";" if texto.count(";") > texto.count(",") else ",")
    for row in rd:
        cod = str(row.get(col_ibge, "")).strip()
        if len(cod) not in (6, 7) or not cod.isdigit():
            continue
        cod = cod.zfill(7) if len(cod) == 7 else cod  # MUNIC usa 7 dígitos; 6 dígitos → não casável, ignorado
        if len(cod) != 7:
            continue
        out[cod] = {"munic_plano_contingencia": normalizar_sim_nao(row.get(col_plano)), "munic_edicao": edicao}
    return out


def parse_icm_csv(texto: str, col_ibge: str, col_faixa: str, col_var8: str, edicao) -> dict:
    out = {}
    rd = csv.DictReader(io.StringIO(texto), delimiter=";" if texto.count(";") > texto.count(",") else ",")
    for row in rd:
        cod = str(row.get(col_ibge, "")).strip()
        if len(cod) != 7 or not cod.isdigit():
            continue
        faixa = str(row.get(col_faixa, "")).strip().upper()
        out[cod] = {"icm_faixa": faixa if faixa in ("A", "B", "C", "D") else None,
                    "icm_var8_plano_contingencia": normalizar_sim_nao(row.get(col_var8)), "icm_edicao": edicao}
    return out


def coletar() -> int:
    cfg = ler("fontes_declarado.json", None) or FONTES_PADRAO
    por_cod, _ = referencia_ibge()
    reg = ler("declarado_nacional.json", {"_governanca": "Camada declarada nacional (§3.9, C5): construída e "
                                          "SIMULADA desde 02/09/2026; entra na nota só em 26/10/2026. "
                                          "Declarar ≠ publicar: desconto de 50% quando ativada.",
                                          "vigencia_na_nota": "2026-10-26", "municipios": {}})
    for chave, parser in (("munic", "munic"), ("icm", "icm")):
        f = cfg[chave]
        if not f.get("url"):
            registrar_lacuna(f["nome"], "url/edição não confirmada (a_verificar)", canal="DOU", camada=1)
            continue
        try:
            bruto = buscar(f["url"], timeout=120)
        except Exception as e:  # noqa: BLE001
            registrar_lacuna(f["nome"], f"{type(e).__name__}: {e}", canal="DOU", camada=1, strings=[f["url"]])
            f["status"] = f"erro: {type(e).__name__}"; continue
        h = preservar_evidencia(bruto, f["url"], "csv", "coletar_declarado_nacional")
        texto = bruto.decode("utf-8", "replace")
        if parser == "munic":
            dados = parse_munic_csv(texto, f["coluna_ibge"], f["coluna_plano"], f.get("edicao"))
            campo, fato = "munic_plano_contingencia", "plano_declarado_munic"
        else:
            dados = parse_icm_csv(texto, f["coluna_ibge"], f["coluna_faixa"], f["coluna_var8"], f.get("edicao"))
            campo, fato = "icm_var8_plano_contingencia", "plano_declarado_icm"
        casados = 0
        for cod, d in dados.items():
            if cod in por_cod:
                reg["municipios"].setdefault(cod, {}).update(d); casados += 1
                if d.get(campo) in ("sim", "nao"):
                    marcar_fato_municipal(cod, fato, d[campo] == "sim")
        marcar_fonte_consultada([c for c in dados if c in por_cod], f["nome"], "nacional",
                                resultado=f"{casados} municípios na base")
        log_busca("DOU", 1, [f["url"]], "registro", nivel="nacional", n_resultados=casados,
                  resultados=f"{f['nome']}: {casados} municípios casados com IBGE", hash_evidencia=h)
        f["status"] = "ok"; f["ultima_coleta"] = date.today().isoformat()
        print(f"{f['nome']}: {casados} municípios")
    gravar("fontes_declarado.json", cfg); gravar("declarado_nacional.json", reg)
    return 0


FIX_MUNIC = "CodMun;Nome;MGRD_PlanoContingencia\n4202404;Blumenau;Sim\n2927408;Salvador;Não\n99;lixo;Sim\n"
FIX_ICM = "codigo_ibge,faixa,var8_plano_contingencia\n4202404,A,sim\n2927408,C,nao\n4202404x,Z,talvez\n"


def autoteste() -> int:
    def t1():
        d = parse_munic_csv(FIX_MUNIC, "CodMun", "MGRD_PlanoContingencia", 2024)
        return d == {"4202404": {"munic_plano_contingencia": "sim", "munic_edicao": 2024},
                     "2927408": {"munic_plano_contingencia": "nao", "munic_edicao": 2024}}
    def t2():
        d = parse_icm_csv(FIX_ICM, "codigo_ibge", "faixa", "var8_plano_contingencia", 2025)
        return len(d) == 2 and d["4202404"]["icm_faixa"] == "A" and d["2927408"]["icm_var8_plano_contingencia"] == "nao"
    def t3(): return normalizar_sim_nao("talvez") == "NA" and normalizar_sim_nao(None) == "NA"
    def t4():  # negativo: CSV sem as colunas → vazio, nunca exceção
        return parse_munic_csv("a,b\n1,2\n", "CodMun", "X", 2024) == {}
    return rodar_autoteste({"parser MUNIC": t1, "parser ICM": t2, "valores fora do vocabulário viram NA": t3,
                            "negativo: colunas ausentes": t4})


if __name__ == "__main__":
    sys.exit(autoteste() if "--autoteste" in sys.argv else coletar())
