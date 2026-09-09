#!/usr/bin/env python3
"""
coletar_srag_gripe.py — SRAG e síndrome gripal, nacional e por UF (§36, catálogo: srag · sg; 09/09/2026)
=============================================================================================================
Fonte: InfoGripe (Fiocruz/FGV/GT-Influenza, SVS/MS) — série longa com estimativas recentes, publicada em
repositório aberto (GitLab PROCC/Fiocruz), formato "tidy": uma linha por (Tipo, escala, dado, ano
epidemiológico, semana epidemiológica). Tipo ∈ {País, Estado, ...}; dado ∈ {srag, sragflu, sragcovid,
obitos, ...}. Não fornece SRAG por município — é por País e por UF, o que já cobre o gatilho estadual do
plano ("um ou mais alertas... na mesma região").

Como o formato exato de cabeçalho não pôde ser verificado a partir deste ambiente (rede restrita fora da
rotina), o leitor abaixo é DEFENSIVO: localiza as colunas por correspondência de padrão (normalizadas,
sem acento, minúsculas) em vez de nome literal fixo, e REGISTRA no log quais colunas usou — a primeira
rodada real deve ser conferida no relatório do diagnóstico (mesmo princípio do sondar_enso_probabilidades.py).
Se o formato mudar a ponto de não bater nenhum padrão, o coletor falha alto e registra lacuna — nunca adivinha.

Mesmo tratamento do §35 (dengue): canal endêmico (mediana/p75/p90) sobre os mesmos anos, últimas semanas
vazadas até a completude do dado laboratorial, "o Monitor não atribui casos ao El Niño". Peso zero.
  python coletar_srag_gripe.py --autoteste
"""
import csv, io, re, statistics, sys, unicodedata
from collections import defaultdict
from pathlib import Path
from coletores_base import ler, gravar, buscar, registrar_lacuna, log_busca, rodar_autoteste

RAIZ = Path(__file__).resolve().parent
URL_SERIE = "https://gitlab.procc.fiocruz.br/mave/repo/-/raw/master/Dados/InfoGripe/serie_temporal_com_estimativas_recentes.csv"
ANOS_CANAL = list(range(2019, 2026))   # 2019–2025; 2024 tratado à parte só quando houver sinal de excepcionalidade nacional (ver nota no §35)
SE_INCOMPLETAS = 4
RESSALVA = "O Monitor não atribui casos ao El Niño; a série é a do InfoGripe (Fiocruz/FGV/GT-Influenza, SVS/MS), notificações do Sivep-Gripe com estimativa de dados recentes."
SIGLA = {"acre":"AC","alagoas":"AL","amapa":"AP","amazonas":"AM","bahia":"BA","ceara":"CE","distrito federal":"DF","espirito santo":"ES","goias":"GO",
         "maranhao":"MA","mato grosso":"MT","mato grosso do sul":"MS","minas gerais":"MG","para":"PA","paraiba":"PB","parana":"PR","pernambuco":"PE",
         "piaui":"PI","rio de janeiro":"RJ","rio grande do norte":"RN","rio grande do sul":"RS","rondonia":"RO","roraima":"RR","santa catarina":"SC",
         "sao paulo":"SP","sergipe":"SE","tocantins":"TO","brasil":"BR","pais":"BR"}


def _hoje():
    import datetime as _dt, json as _js
    try:
        a = _js.load(open(RAIZ / "data" / "meta.json", encoding="utf-8")).get("atualizado_em")
        return _dt.datetime.strptime(a, "%d/%m/%Y").date()
    except Exception:  # noqa: BLE001
        return _dt.date.today()


def _plano(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", (t or "").lower()) if unicodedata.category(c) != "Mn").strip()


def detectar_colunas(cabecalho: list) -> dict:
    """Localiza, por padrão, as colunas: tipo, escala, dado, ano, semana, valor. Função pura.
    Levanta ValueError se algum papel obrigatório não bater em nenhuma coluna (falha alto, nunca adivinha)."""
    norm = [_plano(h) for h in cabecalho]
    PADROES = {"tipo": [r"^tipo$"], "escala": [r"^escala$"], "dado": [r"^dado$"],
               "ano": [r"ano.*epidemio"], "semana": [r"semana.*epidemio"],
               "valor": [r"casos.*semanais.*reportados", r"^valor$", r"^casos$"]}
    achado = {}
    for papel, pats in PADROES.items():
        for i, h in enumerate(norm):
            if any(re.search(p, h) for p in pats):
                achado[papel] = i; break
        if papel not in achado:
            raise ValueError(f"coluna para '{papel}' não encontrada no cabeçalho InfoGripe: {cabecalho}")
    return achado


def parse_serie_longa(texto: str) -> dict:
    """{'BR'|UF: {'AAAA-SS': valor}} para dado='srag' (ou 'sragflu' se 'srag' ausente), escala='casos'.
    Delimitador autodetectado (';' ou ','). Função pura."""
    delim = ";" if texto.split("\n", 1)[0].count(";") >= texto.split("\n", 1)[0].count(",") else ","
    linhas = list(csv.reader(io.StringIO(texto), delimiter=delim))
    if not linhas:
        return {}
    col = detectar_colunas(linhas[0])
    dados_disponiveis = {_plano(r[col["dado"]]) for r in linhas[1:] if len(r) > col["dado"]}
    alvo = "srag" if "srag" in dados_disponiveis else ("sragflu" if "sragflu" in dados_disponiveis else None)
    if alvo is None:
        raise ValueError(f"nenhum dado 'srag'/'sragflu' encontrado; disponíveis: {sorted(dados_disponiveis)[:10]}")
    out = defaultdict(dict)
    for r in linhas[1:]:
        if len(r) <= max(col.values()):
            continue
        if _plano(r[col["escala"]]) != "casos" or _plano(r[col["dado"]]) != alvo:
            continue
        loc = SIGLA.get(_plano(r[col["tipo"]]))
        if loc is None:
            continue
        try:
            ano = int(re.sub(r"\D", "", r[col["ano"]])[:4]); se = int(re.sub(r"\D", "", r[col["semana"]])[:2])
            val = float(r[col["valor"]].replace(",", "."))
        except (ValueError, IndexError):
            continue
        if 1 <= se <= 53:
            out[loc][f"{ano}-{se:02d}"] = val
    return dict(out)


def canal_endemico(serie: dict) -> dict:
    """{SS: {mediana, p75, p90, n_anos}} sobre ANOS_CANAL de uma série {'AAAA-SS': valor}. Função pura."""
    por_se = defaultdict(list)
    for chave, v in serie.items():
        ano, ss = chave.split("-")
        if int(ano) in ANOS_CANAL:
            por_se[ss].append(v)
    out = {}
    for ss, vals in por_se.items():
        vals = sorted(vals); n = len(vals)
        if n < 3:
            continue
        q = lambda p: vals[min(n - 1, max(0, int(round(p * (n - 1)))))]
        out[ss] = {"mediana": statistics.median(vals), "p75": q(0.75), "p90": q(0.90), "n_anos": n}
    return out


def vazar_incompletas(serie: dict, ano: int, n: int = SE_INCOMPLETAS) -> tuple:
    chaves = sorted(k for k in serie if k.startswith(f"{ano}-"))
    inc = set(chaves[-n:]) if chaves else set()
    cons = {k: (None if k in inc else v) for k, v in serie.items()}
    return cons, sorted(inc)


def coletar() -> int:
    try:
        bruto = buscar(URL_SERIE, timeout=90).decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        registrar_lacuna("InfoGripe (série SRAG)", type(e).__name__, canal="DOU", camada=1); print("srag/sg: falha de rede — lacuna declarada"); return 0
    try:
        serie = parse_serie_longa(bruto)
    except ValueError as e:
        registrar_lacuna("InfoGripe (formato da série SRAG)", str(e)[:180], canal="DOU", camada=1)
        print(f"srag/sg: {e} — coletor não adivinha; corrigir o mapeamento de colunas e reexecutar")
        return 0
    if not serie:
        registrar_lacuna("InfoGripe (série SRAG)", "série vazia após leitura", canal="DOU", camada=1); print("srag/sg: série vazia — lacuna declarada"); return 0
    hoje = _hoje().strftime("%d/%m/%Y"); ano_corrente = _hoje().year
    canal = {loc: canal_endemico(s) for loc, s in serie.items()}
    consolidada = {}; nowcasting = {}
    for loc, s in serie.items():
        cons, vaz = vazar_incompletas(s, ano_corrente)
        consolidada[loc] = cons
        nowcasting[loc] = {k: s[k] for k in vaz if k in s}
    gov = ("SRAG/SG — nacional e por UF (§36, catálogo). Peso zero, sem nota, sem faixa. " + RESSALVA +
           " Canal endêmico: mediana/p75/p90 de " + f"{min(ANOS_CANAL)}–{max(ANOS_CANAL)}" + ". Últimas " + str(SE_INCOMPLETAS) +
           " SE vazadas (dado laboratorial incompleto); nowcasting = valor bruto do InfoGripe nessas semanas, sem faixa de incerteza própria (a fonte não publica min/max nesta série).")
    (RAIZ / "data" / "saude_desfechos").mkdir(parents=True, exist_ok=True)
    gravar("saude_desfechos/srag_serie.json", {"_governanca": gov, "gerado_em": hoje, "fonte": URL_SERIE, "ano_corrente": ano_corrente,
                                               "anos_canal": ANOS_CANAL, "se_incompletas": SE_INCOMPLETAS, "serie": consolidada, "nowcasting": nowcasting, "canal_endemico": canal})
    log_busca("DOU", 1, [URL_SERIE], "registro", nivel="nacional", n_resultados=len(serie), resultados=f"SRAG/SG: série lida para {len(serie)} localidade(s) (BR + UFs); colunas detectadas por padrão")
    ult_br = max((k for k in serie.get("BR", {})), default=None)
    print(f"srag/sg: {len(serie)} localidade(s); última SE (BR): {ult_br or '—'}")
    return 0


def autoteste() -> int:
    def t1():
        cab = ["Tipo", "escala", "dado", "Ano epidemiológico", "Semana epidemiológica", "Casos semanais reportados até a última atualização"]
        c = detectar_colunas(cab)
        return c["tipo"] == 0 and c["ano"] == 3 and c["valor"] == 5
    def t2():
        try:
            detectar_colunas(["a", "b", "c"]); return False
        except ValueError:
            return True
    csv_txt = "Tipo;escala;dado;Ano epidemiológico;Semana epidemiológica;Casos semanais reportados até a última atualização\n"
    for ano in (2019, 2020, 2021, 2022, 2023, 2025):
        csv_txt += f"País;casos;srag;{ano};10;{100+ano-2019}\n"
        csv_txt += f"São Paulo;casos;srag;{ano};10;{20+ano-2019}\n"
    for se in range(30, 36):
        csv_txt += f"País;casos;srag;2026;{se};{300 if se <= 32 else 50}\n"
    csv_txt += "País;incidencia;srag;2026;33;9.9\n"   # escala diferente: deve ser ignorada
    def t3():
        s = parse_serie_longa(csv_txt); return "BR" in s and "SP" in s and s["BR"]["2026-30"] == 300 and "2026-33" in s["BR"]
    def t4():
        s = parse_serie_longa(csv_txt); c = canal_endemico(s["BR"]); return c["10"]["n_anos"] == 6 and c["10"]["p90"] >= c["10"]["p75"] >= c["10"]["mediana"]
    def t5():
        s = parse_serie_longa(csv_txt); cons, vaz = vazar_incompletas(s["BR"], 2026)
        return set(vaz) == {"2026-32", "2026-33", "2026-34", "2026-35"} and cons["2026-32"] is None and cons["2026-30"] == 300
    def t6():
        return "não atribui casos ao El Niño" in RESSALVA and SIGLA["sao paulo"] == "SP" and SIGLA["pais"] == "BR"
    return rodar_autoteste({"detecção de colunas por padrão": t1, "coluna ausente falha alto (nunca adivinha)": t2,
                            "parse: BR e UF, escala 'casos' filtrada": t3, "canal endêmico: 6 anos, ordenado": t4,
                            "últimas 4 SE vazadas": t5, "ressalva e siglas": t6})


if __name__ == "__main__":
    sys.exit(autoteste() if "--autoteste" in sys.argv else coletar())
