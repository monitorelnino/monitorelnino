#!/usr/bin/env python3
"""
coletar_declarado_nacional.py
=============================
Camada DECLARADA nacional (doc de redesenho §3.9, decisão C5): o que o município
DECLARA ter — MUNIC/IBGE (bloco "Gestão de riscos e de desastres": possui plano
de contingência?) e ICM/SEDEC (faixa A–D; variável 8: plano de contingência).
Produz `data/declarado_nacional.json`, por município: `munic_plano_contingencia`
(sim/não/NA + ano da edição), `icm_faixa`, `icm_var8_plano_contingencia`.

GOVERNANÇA: esta camada NÃO altera nota antes de 26/10/2026. Até lá só existe
via `recalcular_mare.py --simular-declarado-nacional`, que aplica o desconto de
50% já existente (declarar ≠ publicar, §3.4 da transferência) e grava as 27
notas antes/depois em `data/simulacao_declarado_nacional.json` — anexo público
da metodologia. Regra declarada em 02/09/2026, vigência 26/10/2026 (§12.4).

FONTE MUNIC — verificada por download real em 20/09/2026 (§128), não por
suposição (os nomes anteriores em `fontes_declarado.json`, "MGRD_PlanoContingencia"
e parser CSV, nunca foram conferidos contra arquivo e estavam errados em dois
pontos: (1) a MUNIC não distribui CSV — só .xlsx/.ods; (2) o nome real da
coluna do plano é `Mgrd184`, não `MGRD_PlanoContingencia`).

A MUNIC roda módulos temáticos ROTATIVOS: cada edição cobre um conjunto
diferente de temas, e "Gestão de riscos e de desastres" não está em toda
edição. Confirmado por leitura direta do dicionário de variáveis (aba
"Dicionário" de cada arquivo) e por inspeção das abas de cada ano:
  - 2017 e 2020: têm a aba "Gestão de risco"/"Gestão de riscos" com o bloco.
  - 2019, 2021, 2023, 2024: NÃO têm esse módulo (temas diferentes cada ano;
    colunas com prefixo parecido nessas edições — MREG, Mmig — são de outros
    temas, "Recursos para gestão" e "Gestão migratória", e não devem ser
    confundidas com risco por semelhança de prefixo).
Portanto a edição mais recente com o bloco é 2020, não por escolha editorial,
mas porque é a única disponível nesse recorte temporal.

Dentro do bloco (aba "Gestão de riscos", dicionário seção 6), dois campos são
candidatos a "plano de contingência" e medem coisas diferentes:
  - `Mgrd184` — "Plano de Contingência", dentro de 6.6 Gerenciamento de riscos
    (instrumento geral, ligado a enchentes/inundações/deslizamentos).
  - `Mgrd05` — "O município possui Plano de Contingência e/ou Preservação para
    a seca", dentro de 6.1 Seca.
Usamos `Mgrd184` como padrão: é o instrumento geral de gestão de riscos, no
mesmo nível de abstração que o "plano de contingência" já mede em outras
camadas do MARÉ (S2iD, diários municipais). `Mgrd05` (seca) fica registrado
em paralelo (`munic_plano_contingencia_seca`) para uso futuro, sem entrar na
simulação de nota — decisão sobre usá-lo pertence à editoria, dado que seca é
o padrão de impacto mais associado ao El Niño no Nordeste.

Fontes (§15, "a verificar"): formato de download do ICM segue sem confirmação.
`data/fontes_declarado.json` guarda url e status; sem confirmação → lacuna
declarada. O parser MUNIC (xlsx) é provado por fixture; a primeira coleta real
roda contra o arquivo publicado pelo IBGE.

USO
  python coletar_declarado_nacional.py --autoteste
  python coletar_declarado_nacional.py           # coleta (rede)
"""
import csv, io, sys
from datetime import date
from coletores_base import (buscar, preservar_evidencia, log_busca, registrar_lacuna,
                            marcar_fonte_consultada, marcar_fato_municipal, referencia_ibge,
                            ler, gravar, rodar_autoteste)

FONTES_PADRAO = {
    "_governanca": "Fontes da camada declarada nacional (v2.2.4, §3.9). Sem url confirmada → lacuna.",
    "munic": {
        "nome": "MUNIC/IBGE 2020 — bloco Gestão de riscos e desastres",
        "url": "https://ftp.ibge.gov.br/Perfil_Municipios/2020/Base_de_Dados/Base_MUNIC_2020.xlsx",
        "edicao": 2020,
        "status": "a_verificar",
        "aba": "Gestão de riscos",
        "coluna_ibge": "CodMun",
        "coluna_plano": "Mgrd184",
        "coluna_plano_seca": "Mgrd05",
        "_nota": "2017 e 2020 são as únicas edições recentes com este bloco (módulos rotativos "
                 "da MUNIC); 2020 é a mais recente. Verificado por download real em 20/09/2026.",
    },
    "icm": {"nome": "ICM/SEDEC — Indicador de Capacidade Municipal", "url": None, "edicao": None,
            "status": "a_verificar", "coluna_ibge": "codigo_ibge", "coluna_faixa": "faixa",
            "coluna_var8": "var8_plano_contingencia"},
}
SIM = {"sim", "s", "1", "true", "possui"}
NAO = {"não", "nao", "n", "0", "false", "não possui", "nao possui"}


def normalizar_sim_nao(v) -> str:
    t = str(v or "").strip().lower()
    return "sim" if t in SIM else "nao" if t in NAO else "NA"


def parse_munic_xlsx(bruto: bytes, aba: str, col_ibge: str, col_plano: str,
                      col_plano_seca: str, edicao) -> dict:
    """{ibge7: {munic_plano_contingencia, munic_plano_contingencia_seca, munic_edicao}}.

    A MUNIC distribui .xlsx, não CSV (confirmado por download real em 20/09/2026,
    §128) — leitura via openpyxl, aba nomeada (não a primeira do arquivo: a aba de
    risco costuma vir depois de "Recursos humanos" e outras, então pegar por nome
    evita repetir o defeito da sonda §126, que só olhava as 3 primeiras abas).
    """
    import openpyxl
    out = {}
    wb = openpyxl.load_workbook(io.BytesIO(bruto), read_only=True, data_only=True)
    try:
        if aba not in wb.sheetnames:
            return out
        ws = wb[aba]
        linhas = ws.iter_rows(values_only=True)
        cabecalho = list(next(linhas))
        try:
            idx_ibge = cabecalho.index(col_ibge)
        except ValueError:
            return out
        idx_plano = cabecalho.index(col_plano) if col_plano in cabecalho else None
        idx_seca = cabecalho.index(col_plano_seca) if col_plano_seca in cabecalho else None
        for linha in linhas:
            cod = str(linha[idx_ibge] or "").strip()
            if len(cod) != 7 or not cod.isdigit():
                continue
            d = {"munic_edicao": edicao}
            if idx_plano is not None:
                d["munic_plano_contingencia"] = normalizar_sim_nao(linha[idx_plano])
            if idx_seca is not None:
                d["munic_plano_contingencia_seca"] = normalizar_sim_nao(linha[idx_seca])
            out[cod] = d
    finally:
        wb.close()
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
    for chave in ("munic", "icm"):
        f = cfg[chave]
        if not f.get("url"):
            registrar_lacuna(f["nome"], "url/edição não confirmada (a_verificar)", canal="DOU", camada=1)
            continue
        try:
            bruto = buscar(f["url"], timeout=120)
        except Exception as e:  # noqa: BLE001
            registrar_lacuna(f["nome"], f"{type(e).__name__}: {e}", canal="DOU", camada=1, strings=[f["url"]])
            f["status"] = f"erro: {type(e).__name__}"; continue
        ext = "xlsx" if chave == "munic" else "csv"
        h = preservar_evidencia(bruto, f["url"], ext, "coletar_declarado_nacional")
        if chave == "munic":
            dados = parse_munic_xlsx(bruto, f["aba"], f["coluna_ibge"], f["coluna_plano"],
                                     f.get("coluna_plano_seca", ""), f.get("edicao"))
            campo, fato = "munic_plano_contingencia", "plano_declarado_munic"
        else:
            texto = bruto.decode("utf-8", "replace")
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


def _xlsx_fixture() -> bytes:
    """Monta um .xlsx mínimo em memória, mesmo layout da MUNIC real (aba nomeada,
    cabeçalho na primeira linha), para o autoteste não depender de rede."""
    import openpyxl
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    ws = wb.create_sheet("Gestão de riscos")
    ws.append(["CodMun", "UF", "Mgrd01", "Mgrd05", "Mgrd184"])
    ws.append([4202404, "SC", "Sim", "Não", "Sim"])
    ws.append([2927408, "BA", "Não", "Sim", "Não"])
    ws.append([99, "XX", "Sim", "Sim", "Sim"])  # código inválido (não IBGE de 7 dígitos) — deve ser ignorado
    buf = io.BytesIO(); wb.save(buf)
    return buf.getvalue()


FIX_ICM = "codigo_ibge,faixa,var8_plano_contingencia\n4202404,A,sim\n2927408,C,nao\n4202404x,Z,talvez\n"


def autoteste() -> int:
    def t1():
        d = parse_munic_xlsx(_xlsx_fixture(), "Gestão de riscos", "CodMun", "Mgrd184", "Mgrd05", 2020)
        return d == {
            "4202404": {"munic_edicao": 2020, "munic_plano_contingencia": "sim",
                        "munic_plano_contingencia_seca": "nao"},
            "2927408": {"munic_edicao": 2020, "munic_plano_contingencia": "nao",
                        "munic_plano_contingencia_seca": "sim"},
        }
    def t2():
        d = parse_icm_csv(FIX_ICM, "codigo_ibge", "faixa", "var8_plano_contingencia", 2025)
        return len(d) == 2 and d["4202404"]["icm_faixa"] == "A" and d["2927408"]["icm_var8_plano_contingencia"] == "nao"
    def t3(): return normalizar_sim_nao("talvez") == "NA" and normalizar_sim_nao(None) == "NA"
    def t4():  # negativo: aba errada → vazio, nunca exceção
        return parse_munic_xlsx(_xlsx_fixture(), "Aba Inexistente", "CodMun", "Mgrd184", "Mgrd05", 2020) == {}
    def t5():  # negativo: coluna do plano ausente da aba → ainda casa por IBGE, sem o campo do plano
        import openpyxl
        wb = openpyxl.Workbook(); wb.remove(wb.active)
        ws = wb.create_sheet("Gestão de riscos")
        ws.append(["CodMun", "OutraColuna"])
        ws.append([4202404, "x"])
        buf = io.BytesIO(); wb.save(buf)
        d = parse_munic_xlsx(buf.getvalue(), "Gestão de riscos", "CodMun", "Mgrd184", "Mgrd05", 2020)
        return d == {"4202404": {"munic_edicao": 2020}}
    return rodar_autoteste({"parser MUNIC (xlsx, aba nomeada)": t1, "parser ICM": t2,
                            "valores fora do vocabulário viram NA": t3,
                            "negativo: aba inexistente": t4,
                            "negativo: coluna do plano ausente": t5})


if __name__ == "__main__":
    sys.exit(autoteste() if "--autoteste" in sys.argv else coletar())
