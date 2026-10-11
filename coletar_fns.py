#!/usr/bin/env python3
"""
coletar_fns.py — repasses do Fundo Nacional de Saúde em 2026, do download de dados abertos do
Portal da Transparência (HANDOVER_FINANCIAMENTO_SAUDE_10-10-2026, item 1).

DE ONDE VEM
    O mesmo ZIP mensal que `coletar_transferencias_municipais.py` já baixa
    (`portaldatransparencia.gov.br/download-de-dados/transferencias/AAAAMM`). Medido em 11/10/2026
    no arquivo de agosto: 65.198 linhas na função Saúde, R$ 12,5 bi, quase tudo pela unidade
    gestora "DIRETORIA EXECUTIVA DO FUNDO NAC. DE SAÚDE" — o fundo a fundo — e com o favorecido
    classificado como "Administração Pública" (o fundo municipal ou estadual de saúde), não como
    "Administração Pública Municipal". Por isso a rota "saúde" do arquivo de transferências por
    município saía quase vazia: o filtro dele é o tipo de favorecido municipal, e o SUS chega ao
    município pelo fundo. Este coletor lê a mesma fonte com o recorte certo; nenhuma consulta nova,
    nenhuma chave.

O QUE GRAVA (peso zero; nunca lido pelo índice)
    `data/financiamento/fns_2026.json` — meses[AAAAMM]: linhas, soma, por UF (municipal · estadual ·
    outros · por programa orçamentário), a lista dos repasses ligados a emergência e os fundos
    municipais que não casaram com a referência do IBGE (com o valor). É o que a página lê.
    `data/financiamento/municipios/fns_municipios_2026.json` — municipios[ibge]: total do ano e
    total ligado a emergência, com o mês a mês.

"LIGADO A EMERGÊNCIA" É TEXTO DO ATO, NÃO SUPOSIÇÃO
    Marca-se só a linha cujo nome de ação ou de plano orçamentário, tal como o Portal o escreve,
    cita emergência, calamidade, desastre, El Niño, ESPIN, seca, estiagem, calor, crédito
    extraordinário ou a Força Nacional do SUS. Nome que não cita nada disso não é marcado, ainda
    que o dinheiro possa ter servido a isso — dúvida não marca.

USO
    python3 coletar_fns.py --autoteste
    python3 coletar_fns.py --de-arquivo evidencias/<hash>.zip 202608   # lê uma cópia preservada
    (na rotina, quem chama é coletar_transferencias_municipais.py, sobre o ZIP que já baixou)
"""
from __future__ import annotations

import csv
import io
import json
import pathlib
import re
import sys
import zipfile

RAIZ = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

SAIDA = RAIZ / "data" / "financiamento" / "fns_2026.json"
# O detalhe por município mora à parte: com 5,5 mil fundos e um registro por mês ele passa de
# 2 MB em setembro, e a página só precisa do agregado por estado.
SAIDA_MUNICIPIOS = RAIZ / "data" / "financiamento" / "municipios" / "fns_municipios_2026.json"
FUNCAO_SAUDE = "10"
RE_FNS = re.compile(r"FUNDO NAC\.?\s*DE SA[UÚ]", re.I)
RE_EMERGENCIA = re.compile(
    r"EMERG[EÊ]NCI|CALAMIDADE|DESASTRE|EL\s*NI[NÑ]O|\bESPIN\b|ESTIAGEM|\bSECA\b|CALOR|"
    r"CR[EÉ]DITO EXTRAORDIN|FOR[CÇ]A NACIONAL DO S", re.I)
RE_MUNICIPAL = re.compile(r"MUNICIP", re.I)
RE_ESTADUAL = re.compile(r"ESTAD|DISTRITO FEDERAL", re.I)
COLUNAS = ("CÓDIGO FUNÇÃO", "NOME UNIDADE GESTORA", "UF", "NOME MUNICÍPIO", "NOME FAVORECIDO",
           "NOME PROGRAMA", "NOME AÇÃO", "NOME PLANO ORÇAMENTÁRIO", "VALOR TRANSFERIDO")


def esfera(nome_favorecido: str) -> str:
    """municipal | estadual | outros, pelo nome do favorecido (o fundo). Função pura."""
    n = nome_favorecido or ""
    if RE_MUNICIPAL.search(n):
        return "municipal"
    if RE_ESTADUAL.search(n):
        return "estadual"
    return "outros"


def ligado_a_emergencia(nome_acao: str, nome_plano: str) -> bool:
    """O texto da ação ou do plano orçamentário cita emergência/clima? Função pura."""
    return bool(RE_EMERGENCIA.search(f"{nome_acao or ''} {nome_plano or ''}"))


def ler_fns(corpo: bytes, chave: dict, normalizar, valor_br, re_sufixo) -> dict:
    """Agregado do mês. Função pura sobre os bytes do ZIP; `chave` é {(UF, nome): ibge}."""
    z = zipfile.ZipFile(io.BytesIO(corpo))
    nomes = [n for n in z.namelist() if n.lower().endswith(".csv")]
    if not nomes:
        raise ValueError("ZIP do Portal sem CSV dentro: formato mudou")
    por_uf, por_ibge, emergencia, nao_casados = {}, {}, {}, {}
    linhas, soma = 0, 0.0
    with z.open(nomes[0]) as f:
        leitor = csv.reader(io.TextIOWrapper(f, encoding="latin-1", newline=""), delimiter=";")
        col = {c: i for i, c in enumerate(next(leitor))}
        faltam = [c for c in COLUNAS if c not in col]
        if faltam:
            raise ValueError(f"colunas ausentes no CSV do Portal: {faltam}")
        for l in leitor:
            if len(l) <= col["VALOR TRANSFERIDO"]:
                continue
            if l[col["CÓDIGO FUNÇÃO"]].strip().lstrip("0") != FUNCAO_SAUDE:
                continue
            if not RE_FNS.search(l[col["NOME UNIDADE GESTORA"]]):
                continue
            v = valor_br(l[col["VALOR TRANSFERIDO"]])
            linhas += 1
            soma += v
            uf = l[col["UF"]].strip() or "?"
            esf = esfera(l[col["NOME FAVORECIDO"]])
            prog = l[col["NOME PROGRAMA"]].strip() or "sem programa na fonte"
            u = por_uf.setdefault(uf, {"municipal": 0.0, "estadual": 0.0, "outros": 0.0,
                                       "programas": {}, "emergencia": 0.0})
            u[esf] += v
            u["programas"][prog] = u["programas"].get(prog, 0.0) + v
            emerg = ligado_a_emergencia(l[col["NOME AÇÃO"]], l[col["NOME PLANO ORÇAMENTÁRIO"]])
            if emerg:
                u["emergencia"] += v
                k = (uf, l[col["NOME AÇÃO"]].strip(), l[col["NOME PLANO ORÇAMENTÁRIO"]].strip())
                emergencia[k] = emergencia.get(k, 0.0) + v
            if esf != "municipal":
                continue
            nome = re_sufixo.sub("", normalizar(l[col["NOME MUNICÍPIO"]])).strip()
            ibge = chave.get((uf, nome)) if nome else None
            if ibge is None:
                nao_casados[f"{uf}/{nome or '?'}"] = round(nao_casados.get(f"{uf}/{nome or '?'}", 0.0) + v, 2)
                continue
            m = por_ibge.setdefault(ibge, {"total": 0.0, "emergencia": 0.0})
            m["total"] += v
            if emerg:
                m["emergencia"] += v
    r2 = lambda x: round(x, 2)  # noqa: E731
    return {
        "linhas": linhas, "soma": r2(soma),
        "por_uf": {uf: {"municipal": r2(u["municipal"]), "estadual": r2(u["estadual"]),
                        "outros": r2(u["outros"]), "emergencia": r2(u["emergencia"]),
                        "programas": {p: r2(x) for p, x in sorted(u["programas"].items())}}
                   for uf, u in sorted(por_uf.items())},
        "emergencia": [{"uf": k[0], "acao": k[1], "plano_orcamentario": k[2], "valor": r2(x)}
                       for k, x in sorted(emergencia.items())],
        "por_ibge": {i: {"total": r2(m["total"]), "emergencia": r2(m["emergencia"])}
                     for i, m in sorted(por_ibge.items())},
        "nao_casados": dict(sorted(nao_casados.items())),
    }


def fundir_fns(anterior: dict, mes: str, ag: dict, hash_evidencia=None) -> dict:
    """Junta o mês ao agregado. Função pura e IDEMPOTENTE: reler o mês o substitui."""
    saida = dict(anterior or {})
    saida.pop("municipios", None)
    meses = dict(saida.get("meses") or {})
    meses[mes] = {"linhas": ag["linhas"], "soma": ag["soma"], "por_uf": ag["por_uf"],
                  "emergencia": ag["emergencia"], "nao_casados": ag["nao_casados"],
                  "hash_evidencia": hash_evidencia}
    saida["meses"] = {m: meses[m] for m in sorted(meses)}
    return saida


def fundir_municipios(anterior: dict, mes: str, ag: dict) -> dict:
    """Junta o mês ao detalhe por município. Função pura e IDEMPOTENTE."""
    saida = dict(anterior or {})
    munis = {}
    for i, reg in (saida.get("municipios") or {}).items():
        munis[i] = {"meses": {m: x for m, x in (reg.get("meses") or {}).items() if m != mes}}
    # Mês a mês como par [total, ligado a emergência]: o arquivo tem 5,5 mil fundos e doze meses.
    for i, x in ag["por_ibge"].items():
        munis.setdefault(i, {"meses": {}})["meses"][mes] = [x["total"], x["emergencia"]]
    for i, reg in munis.items():
        reg["meses"] = {m: reg["meses"][m] for m in sorted(reg["meses"])}
        reg["total"] = round(sum(x[0] for x in reg["meses"].values()), 2)
        reg["emergencia"] = round(sum(x[1] for x in reg["meses"].values()), 2)
    saida["municipios"] = {i: munis[i] for i in sorted(munis) if munis[i]["meses"]}
    return saida


def cabecalho(dados: dict, hoje_br: str) -> dict:
    dados["_formato"] = (
        "Repasses do Fundo Nacional de Saúde (função Saúde, unidade gestora do FNS) por mês, UF, "
        "esfera do fundo favorecido (municipal · estadual · outros, pelo nome do favorecido) e "
        "programa orçamentário, do download de dados abertos do Portal da Transparência. "
        "`emergencia` lista só as linhas cujo nome de ação ou de plano orçamentário, tal como a "
        "fonte o escreve, cita emergência, calamidade, desastre, El Niño, ESPIN, seca, estiagem, "
        "calor, crédito extraordinário ou a Força Nacional do SUS. PESO ZERO: nunca lido pelo índice.")
    dados["fonte"] = "https://portaldatransparencia.gov.br/download-de-dados/transferencias/"
    dados["atualizado_em"] = hoje_br
    return dados


def processar(corpo: bytes, mes: str, hash_evidencia=None) -> dict:
    """Lê o ZIP do mês e grava o arquivo. Chamado por coletar_transferencias_municipais.py."""
    import coletar_transferencias_municipais as ctm
    from coletores_base import gravar_em, hoje_editorial, ler
    chave = ctm.mapa_siafi_para_ibge(ler("municipios_ibge_referencia.json", []) or [])
    ag = ler_fns(corpo, chave, ctm.normalizar, ctm.valor_br, ctm.RE_SUFIXO_EX)
    if ag["linhas"] == 0:
        raise ValueError(f"{mes}: nenhuma linha do FNS no arquivo — formato mudou?")
    anterior = json.loads(SAIDA.read_text(encoding="utf-8")) if SAIDA.exists() else {}
    hoje_br = hoje_editorial().strftime("%d/%m/%Y")
    dados = cabecalho(fundir_fns(anterior, mes, ag, hash_evidencia), hoje_br)
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    gravar_em(SAIDA, dados)
    ant_m = (json.loads(SAIDA_MUNICIPIOS.read_text(encoding="utf-8"))
             if SAIDA_MUNICIPIOS.exists() else {})
    mun = fundir_municipios(ant_m, mes, ag)
    mun["_formato"] = ("Repasses do Fundo Nacional de Saúde a fundos MUNICIPAIS de saúde, por município "
                       "(IBGE) e mês, e o que deles é ligado a emergência pelo texto do ato — detalhe de "
                       "`data/financiamento/fns_2026.json`. PESO ZERO.")
    mun["fonte"] = dados["fonte"]
    mun["atualizado_em"] = hoje_br
    SAIDA_MUNICIPIOS.parent.mkdir(parents=True, exist_ok=True)
    gravar_em(SAIDA_MUNICIPIOS, mun, compacto=True)
    print(f"FNS {mes}: {ag['linhas']} linha(s), R$ {ag['soma']:,.2f}, "
          f"{len(ag['por_ibge'])} fundo(s) municipal(is) casado(s), "
          f"{len(ag['emergencia'])} linha(s) agregada(s) ligada(s) a emergência")
    return ag


def _zip_de_teste(linhas: list) -> bytes:
    cab = list(COLUNAS) + ["TIPO FAVORECIDO"]
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(cab)
    for l in linhas:
        w.writerow(l + ["Administração Pública"])
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        z.writestr("202608_Transferencias.csv", buf.getvalue().encode("latin-1"))
    return out.getvalue()


def autoteste() -> int:
    falhas = []

    def ok(nome, cond):
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    norm = lambda s: re.sub(r"\s+", " ", s.upper()).strip()  # noqa: E731
    vbr = lambda s: float(s.replace(".", "").replace(",", ".")) if s.strip() else 0.0  # noqa: E731
    suf = re.compile(r"$^")
    fns = "DIRETORIA EXECUTIVA DO FUNDO NAC. DE SAUDE"
    corpo = _zip_de_teste([
        ["10", fns, "PE", "RECIFE", "FUNDO MUNICIPAL DE SAUDE DE RECIFE", "ATENCAO PRIMARIA A SAUDE",
         "PISO DE ATENCAO PRIMARIA A SAUDE", "INCENTIVO FINANCEIRO DA APS", "1.000,50"],
        ["10", fns, "PE", "RECIFE", "FUNDO MUNICIPAL DE SAUDE DE RECIFE", "ATENCAO PRIMARIA A SAUDE",
         "PISO DE ATENCAO PRIMARIA A SAUDE", "INCREMENTO FINANCEIRO DESTINADO A EMERGENCIAS EM SAUDE", "200,00"],
        ["10", fns, "PE", "RECIFE", "FUNDO ESTADUAL DE SAUDE DE PERNAMBUCO", "ATENCAO ESPECIALIZADA",
         "MAC", "MAC", "3.000,00"],
        ["10", fns, "PE", "CIDADE INEXISTENTE", "FUNDO MUNICIPAL DE SAUDE", "ATENCAO PRIMARIA A SAUDE",
         "PISO", "PISO", "50,00"],
        ["10", "CEF-PROGRAMAS DO MINISTERIO DA SAUDE", "PE", "RECIFE", "PREFEITURA", "X", "X", "X", "999,00"],
        ["12", fns, "PE", "RECIFE", "FUNDO MUNICIPAL DE SAUDE DE RECIFE", "EDUCACAO", "X", "X", "777,00"],
    ])
    ag = ler_fns(corpo, {("PE", "RECIFE"): "2611606"}, norm, vbr, suf)
    ok("só função Saúde e unidade gestora do FNS entram", ag["linhas"] == 4 and ag["soma"] == 4250.5)
    ok("esfera pelo nome do fundo: municipal, estadual",
       ag["por_uf"]["PE"]["municipal"] == 1250.5 and ag["por_uf"]["PE"]["estadual"] == 3000.0)
    ok("emergência só pelo texto do plano/ação",
       ag["por_uf"]["PE"]["emergencia"] == 200.0 and len(ag["emergencia"]) == 1)
    ok("fundo municipal casado vai ao município; o que não casa fica em nao_casados com o valor",
       ag["por_ibge"]["2611606"] == {"total": 1200.5, "emergencia": 200.0}
       and ag["nao_casados"] == {"PE/CIDADE INEXISTENTE": 50.0})
    ok("programa sem nome não some", sum(ag["por_uf"]["PE"]["programas"].values()) == 4250.5)
    ok("dúvida não marca: nome sem termo de emergência",
       not ligado_a_emergencia("PISO DE ATENCAO PRIMARIA", "INCENTIVO FINANCEIRO DA APS"))
    ok("Força Nacional do SUS e crédito extraordinário marcam",
       ligado_a_emergencia("IMPLANTACAO E MANUTENCAO DA FORCA NACIONAL DO SISTEMA UNICO", "")
       and ligado_a_emergencia("", "CREDITO EXTRAORDINARIO - MP 1.367"))
    d1 = fundir_municipios({}, "202608", ag)
    d2 = fundir_municipios(d1, "202608", ag)
    ok("fundir é idempotente: reler o mês não soma duas vezes",
       d1 == d2 and d2["municipios"]["2611606"]["total"] == 1200.5)
    d3 = fundir_municipios(d2, "202607", ag)
    ok("dois meses somam no total do município", d3["municipios"]["2611606"]["total"] == 2401.0)
    a1 = fundir_fns({}, "202608", ag)
    ok("o agregado da página não carrega o detalhe por município",
       "municipios" not in a1 and a1 == fundir_fns(a1, "202608", ag))
    try:
        ler_fns(_zip_de_teste([]).replace(b"NOME PLANO", b"NOME XXXXX"), {}, norm, vbr, suf)
        ok("coluna que some levanta, não vira zero", False)
    except Exception:  # noqa: BLE001
        ok("coluna que some levanta, não vira zero", True)
    print("✗ AUTOTESTE: %d falha(s)" % len(falhas) if falhas else "✓ AUTOTESTE OK — sem rede e sem escrita.")
    return 1 if falhas else 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    if "--de-arquivo" in sys.argv:
        i = sys.argv.index("--de-arquivo")
        caminho, mes = sys.argv[i + 1], sys.argv[i + 2]
        corpo = pathlib.Path(caminho).read_bytes()
        import hashlib
        processar(corpo, mes, hashlib.sha256(corpo).hexdigest())
        return 0
    print(__doc__.strip().split("USO")[-1].strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
