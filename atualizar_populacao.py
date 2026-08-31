#!/usr/bin/env python3
"""Aquisição da população municipal do Censo 2022 (IBGE) — Monitor El Niño Brasil.

Busca a tabela 4714 (variável 93, População residente) da API SIDRA do IBGE
para todos os municípios (nível N6) e grava data/populacao_censo2022.json
no formato {codigo_ibge_7digitos: populacao}.

VALIDAÇÃO OBRIGATÓRIA (o script FALHA se qualquer uma não passar):
  1. Exatamente 5.570 municípios retornados.
  2. Total nacional = 203.080.756 (Censo 2022 oficial, segunda apuração,
     tolerância de 0,1% para revisões pontuais do IBGE).
  3. Cinco municípios-sentinela com valor censitário conhecido, conferidos
     um a um (São Paulo, Rio de Janeiro, Belém, Boa Vista, Rio Branco).

Por que estas validações existem: em 26/08/2026, a primeira fonte candidata
(espelho de dados DATASUS/RIPSA no GitHub) foi REJEITADA exatamente por elas —
os valores rotulados "2022" eram projeções pré-Censo, com desvios de 4% a 8,5%
nas capitais. Sem as sentinelas, o erro teria entrado no índice citando o Censo.

Uso:
  python atualizar_populacao.py           # busca, valida e grava
  python atualizar_populacao.py --check   # só valida o arquivo existente
"""
import json, pathlib, sys, urllib.request

RAIZ = pathlib.Path(__file__).parent
DESTINO = RAIZ / "data" / "populacao_censo2022.json"
URL_SIDRA = "https://apisidra.ibge.gov.br/values/t/4714/n6/all/v/93/p/2022"

# O Censo 2022 tem DUAS apurações oficiais do IBGE. A validação exige que as
# cinco sentinelas batam EXATAMENTE com os valores de uma mesma apuração e que
# o total nacional bata EXATO com o total dessa apuração — regra estritamente
# mais forte que a tolerância anterior de ±0,1%. Uma fonte de projeções
# (RIPSA/POPSVS, prévia dez/2022) continua reprovando por ordens de grandeza:
# em 27/08/2026 este contrato reprovou a série RIPSA (desvios 4–8,5%) e a
# Prévia (total 207,7 mi) antes de aprovar a apuração oficial.
APURACOES = {
    "1ª apuração (divulgação 28/06/2023, planilha CD2022 do IBGE)": {
        "total": 203_062_512,
        "sentinelas": {"3550308": ("São Paulo", 11_451_245),
                        "3304557": ("Rio de Janeiro", 6_211_423),
                        "1501402": ("Belém", 1_303_389),
                        "1400100": ("Boa Vista", 413_486),
                        "1200401": ("Rio Branco", 364_756)},
    },
    "2ª apuração (POP2022/Malha 2023, Relação DOU dez/2023; servida pelo SIDRA)": {
        "total": 203_080_756,
        "sentinelas": {"3550308": ("São Paulo", 11_451_245),
                        "3304557": ("Rio de Janeiro", 6_211_423),
                        "1501402": ("Belém", 1_303_403),
                        "1400100": ("Boa Vista", 413_486),
                        "1200401": ("Rio Branco", 364_756)},
    },
}


def buscar():
    """Busca a população por município no Censo 2022 (API SIDRA do IBGE), com paginação e tratamento de timeout."""
    req = urllib.request.Request(URL_SIDRA, headers={"User-Agent": "MonitorElNino/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        dados = json.load(r)
    # linha 0 é cabeçalho; D1C = código do município (7 díg.), V = valor
    pop = {}
    for linha in dados[1:]:
        cod, v = linha.get("D1C"), linha.get("V")
        if cod and v not in (None, "...", "-"):
            pop[cod] = int(v)
    return pop


def validar(pop):
    """Valida contra as apurações oficiais. Retorna (erros, apuracao_identificada)."""
    erros = []
    if len(pop) != 5570:
        erros.append(f"esperados 5570 municípios, obtidos {len(pop)}")
    total = sum(pop.values())
    for rotulo, ap in APURACOES.items():
        if all(pop.get(c) == v for c, (_n, v) in ap["sentinelas"].items()):
            if total != ap["total"]:
                erros.append(f"sentinelas casam com a {rotulo}, mas total {total:,} ≠ {ap['total']:,} exato")
                return erros, None
            return erros, rotulo
    detal = "; ".join(f"{n}: obtido {pop.get(c)}" for c, (n, _v) in
                      list(APURACOES.values())[1]["sentinelas"].items())
    erros.append("sentinelas não casam integralmente com NENHUMA apuração oficial — fonte rejeitada (" + detal + ")")
    return erros, None


def carregar_xlsx_oficial(caminho):
    """Modo offline: lê a planilha oficial do IBGE 'CD2022 População Coletada,
    Imputada e Total' (aba Municípios: UF, COD.UF, COD.MUNIC, nome, coletada,
    imputada, TOTAL). O arquivo passa pelas MESMAS validações do caminho SIDRA."""
    import openpyxl
    ws = openpyxl.load_workbook(caminho, read_only=True)["Municípios"]
    pop = {}
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i < 3:
            continue
        _, _uf, cuf, cmun, _nome, _col, _imp, tot = (list(row) + [None] * 8)[:8]
        if cuf is None or cmun is None or tot is None:
            continue
        try:
            pop[f"{int(cuf):02d}{int(cmun):05d}"] = int(tot)
        except (ValueError, TypeError):
            continue
    return pop


def main():
    """Baixa a população municipal do Censo 2022, valida contra as cinco UFs-sentinela e o total nacional (tolerância de 0,1%), e só então grava data/populacao_censo2022.json."""
    if "--check" in sys.argv:
        if not DESTINO.exists():
            print("✗ data/populacao_censo2022.json não existe ainda — rode sem --check para buscar.")
            return 1
        pop = json.load(open(DESTINO))
        erros, ap = validar(pop)
        for e in erros:
            print("  ✗", e)
        print(f"✓ POPULAÇÃO VÁLIDA — Censo 2022 confirmado · {ap}." if not erros else "✗ ARQUIVO INVÁLIDO.")
        return 1 if erros else 0

    if "--de-arquivo" in sys.argv:
        caminho = sys.argv[sys.argv.index("--de-arquivo") + 1]
        print(f"Lendo planilha oficial: {caminho}")
        pop = carregar_xlsx_oficial(caminho)
        erros, ap = validar(pop)
        if erros:
            for e in erros:
                print("  ✗", e)
            print("✗ VALIDAÇÃO FALHOU — nada foi gravado.")
            return 1
        DESTINO.parent.mkdir(exist_ok=True)
        json.dump(pop, open(DESTINO, "w"), separators=(",", ":"))
        print(f"✓ {len(pop)} municípios · total {sum(pop.values()):,} · {ap} · gravado em {DESTINO.name}")
        return 0

    print(f"Buscando {URL_SIDRA} ...")
    pop = buscar()
    erros, ap = validar(pop)
    if erros:
        for e in erros:
            print("  ✗", e)
        print("✗ VALIDAÇÃO FALHOU — nada foi gravado. O índice continua sem o componente populacional.")
        return 1
    DESTINO.parent.mkdir(exist_ok=True)
    json.dump(pop, open(DESTINO, "w"), separators=(",", ":"))
    print(f"✓ {len(pop)} municípios · total {sum(pop.values()):,} · {ap} · gravado em {DESTINO.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
