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
# 14/09/2026: o host canônico (gitlab.procc) dá timeout desde 09/09 (ver scripts/diagnostico_fontes_saude.py); o InfoGripe
# passou a aparecer também em gitlab.fiocruz.br — a interface pede login, mas o endpoint /-/raw/ pode servir anônimo.
# Tenta em ordem e REGISTRA qual respondeu; nunca mistura as duas.
URLS_SERIE = [URL_SERIE, "https://gitlab.fiocruz.br/marcelo.gomes/infogripe/-/raw/master/Dados/InfoGripe/serie_temporal_com_estimativas_recentes.csv"]
# Indicadores extraídos do mesmo CSV, pela coluna `dado` (rótulos casados por padrão, sem literal fixo). SRAG obrigatório;
# SG (síndrome gripal) só sai se o CSV trouxer um rótulo que case — senão vira lacuna declarada, nunca série vazia/inventada.
INDICADORES = {
    "srag": {"padroes": [r"^srag$", r"^sragflu$"], "arquivo": "saude_desfechos/srag_serie.json", "rotulo": "SRAG", "obrigatorio": True},
    "sg":   {"padroes": [r"^sg$", r"sindrome.*gripal", r"^ili$"],  "arquivo": "saude_desfechos/sg_serie.json",   "rotulo": "síndrome gripal (SG)", "obrigatorio": False},
}
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


def dados_disponiveis(texto: str) -> tuple:
    """(cabeçalho, delimitador, {valores distintos da coluna `dado`}) — para diagnóstico e para escolher o alvo. Função pura."""
    delim = ";" if texto.split("\n", 1)[0].count(";") >= texto.split("\n", 1)[0].count(",") else ","
    linhas = list(csv.reader(io.StringIO(texto), delimiter=delim))
    if not linhas:
        return [], delim, set()
    col = detectar_colunas(linhas[0])
    return linhas[0], delim, {_plano(r[col["dado"]]) for r in linhas[1:] if len(r) > col["dado"]}


def escolher_alvo(disponiveis: set, padroes: list):
    """Primeiro valor de `dado` que casa com algum padrão (na ordem dos padrões); None se nenhum. Função pura."""
    for pat in padroes:
        for d in sorted(disponiveis):
            if re.search(pat, d):
                return d
    return None


def parse_serie_longa(texto: str, padroes: list = None) -> dict:
    """{'BR'|UF: {'AAAA-SS': valor}} para o `dado` que casar com `padroes` (padrão: SRAG), escala='casos'.
    Delimitador autodetectado (';' ou ','). Função pura."""
    padroes = padroes or INDICADORES["srag"]["padroes"]
    delim = ";" if texto.split("\n", 1)[0].count(";") >= texto.split("\n", 1)[0].count(",") else ","
    linhas = list(csv.reader(io.StringIO(texto), delimiter=delim))
    if not linhas:
        return {}
    col = detectar_colunas(linhas[0])
    disponiveis = {_plano(r[col["dado"]]) for r in linhas[1:] if len(r) > col["dado"]}
    alvo = escolher_alvo(disponiveis, padroes)
    if alvo is None:
        raise ValueError(f"nenhum dado casando {padroes} encontrado; disponíveis: {sorted(disponiveis)[:12]}")
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


def _gravar_diagnostico(url_ok, cabecalho, disponiveis, erro_por_url):
    """Guarda o que a rodada VIU (host que respondeu, cabeçalho real, rótulos de `dado`) — para a próxima sessão
    ajustar padrões sem precisar de rede. Nunca contém dado epidemiológico."""
    gravar("saude_desfechos/infogripe_diagnostico.json", {
        "_governanca": "Diagnóstico de formato do InfoGripe (14/09/2026): registro do que o coletor encontrou; sem dado epidemiológico.",
        "gerado_em": _hoje().strftime("%d/%m/%Y"), "url_que_respondeu": url_ok, "cabecalho": cabecalho,
        "valores_de_dado": sorted(disponiveis)[:60], "erro_por_url": erro_por_url})


def coletar() -> int:
    bruto = None; url_ok = None; erro_por_url = {}
    for url in URLS_SERIE:
        try:
            bruto = buscar(url, timeout=90).decode("utf-8", "replace"); url_ok = url; break
        except Exception as e:  # noqa: BLE001
            erro_por_url[url] = type(e).__name__
    if bruto is None:
        _gravar_diagnostico(None, [], set(), erro_por_url)
        registrar_lacuna("InfoGripe (série SRAG)", " · ".join(f"{u.split('/')[2]}: {e}" for u, e in erro_por_url.items()), canal="DOU", camada=1)
        print("srag/sg: falha de rede em todos os hosts — lacuna declarada"); return 0
    try:
        cabecalho, _delim, disponiveis = dados_disponiveis(bruto)
    except ValueError as e:
        _gravar_diagnostico(url_ok, bruto.split("\n", 1)[0].split(";")[:20], set(), erro_por_url)
        registrar_lacuna("InfoGripe (formato da série SRAG)", str(e)[:180], canal="DOU", camada=1)
        print(f"srag/sg: {e} — coletor não adivinha; ver data/saude_desfechos/infogripe_diagnostico.json")
        return 0
    _gravar_diagnostico(url_ok, list(cabecalho), disponiveis, erro_por_url)
    hoje = _hoje().strftime("%d/%m/%Y"); ano_corrente = _hoje().year
    escritos = 0
    for chave, ind in INDICADORES.items():
        alvo = escolher_alvo(disponiveis, ind["padroes"])
        if alvo is None:
            registrar_lacuna(f"InfoGripe ({ind['rotulo']})", f"nenhum rótulo de `dado` casou {ind['padroes']}; disponíveis: {sorted(disponiveis)[:12]}", canal="DOU", camada=1)
            print(f"{chave}: rótulo não encontrado no CSV — lacuna declarada (ver infogripe_diagnostico.json)")
            if ind["obrigatorio"]: return 0
            continue
        serie = parse_serie_longa(bruto, ind["padroes"])
        if not serie:
            registrar_lacuna(f"InfoGripe ({ind['rotulo']})", "série vazia após leitura", canal="DOU", camada=1); print(f"{chave}: série vazia — lacuna declarada")
            if ind["obrigatorio"]: return 0
            continue
        canal = {loc: canal_endemico(s_) for loc, s_ in serie.items()}
        consolidada = {}; nowcasting = {}
        for loc, s_ in serie.items():
            cons, vaz = vazar_incompletas(s_, ano_corrente)
            consolidada[loc] = cons
            nowcasting[loc] = {k: s_[k] for k in vaz if k in s_}
        gov = (f"{ind['rotulo']} — nacional e por UF (§36, catálogo). Peso zero, sem nota, sem faixa. " + RESSALVA +
               " Canal endêmico: mediana/p75/p90 de " + f"{min(ANOS_CANAL)}–{max(ANOS_CANAL)}" + ". Últimas " + str(SE_INCOMPLETAS) +
               " SE vazadas (dado laboratorial incompleto); nowcasting = valor bruto do InfoGripe nessas semanas, sem faixa de incerteza própria (a fonte não publica min/max nesta série).")
        (RAIZ / "data" / "saude_desfechos").mkdir(parents=True, exist_ok=True)
        gravar(ind["arquivo"], {"_governanca": gov, "gerado_em": hoje, "fonte": url_ok, "indicador": chave, "rotulo_dado": alvo, "ano_corrente": ano_corrente,
                                "anos_canal": ANOS_CANAL, "se_incompletas": SE_INCOMPLETAS, "serie": consolidada, "nowcasting": nowcasting, "canal_endemico": canal})
        log_busca("DOU", 1, [url_ok], "registro", nivel="nacional", n_resultados=len(serie), resultados=f"{ind['rotulo']}: série lida para {len(serie)} localidade(s) (BR + UFs); dado='{alvo}'; colunas detectadas por padrão")
        ult_br = max((k for k in serie.get("BR", {})), default=None)
        print(f"{chave}: {len(serie)} localidade(s); dado='{alvo}'; última SE (BR): {ult_br or '—'}")
        escritos += 1
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
    # 14/09/2026: SRAG e SG do mesmo CSV; SG só quando o rótulo existe; dois hosts em ordem
    def t7():
        _, _, disp = dados_disponiveis(csv_txt)
        return escolher_alvo(disp, INDICADORES["srag"]["padroes"]) == "srag" and escolher_alvo(disp, INDICADORES["sg"]["padroes"]) is None
    def t8():
        com_sg = csv_txt + "País;casos;sg;2026;30;900\n"
        _, _, disp = dados_disponiveis(com_sg)
        return escolher_alvo(disp, INDICADORES["sg"]["padroes"]) == "sg" and parse_serie_longa(com_sg, INDICADORES["sg"]["padroes"])["BR"]["2026-30"] == 900
    def t9():
        try:
            parse_serie_longa(csv_txt, INDICADORES["sg"]["padroes"]); return False
        except ValueError:
            return len(URLS_SERIE) == 2 and URLS_SERIE[0] == URL_SERIE and "gitlab.fiocruz.br" in URLS_SERIE[1]
    return rodar_autoteste({"detecção de colunas por padrão": t1, "coluna ausente falha alto (nunca adivinha)": t2,
                            "parse: BR e UF, escala 'casos' filtrada": t3, "canal endêmico: 6 anos, ordenado": t4,
                            "últimas 4 SE vazadas": t5, "ressalva e siglas": t6,
                            "alvo: srag casa, sg ausente → None": t7, "sg extraído só quando o rótulo existe": t8,
                            "sg ausente falha alto; dois hosts em ordem": t9})


if __name__ == "__main__":
    sys.exit(autoteste() if "--autoteste" in sys.argv else coletar())
