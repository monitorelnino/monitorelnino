#!/usr/bin/env python3
"""Estrutura comum dos arquivos de desfecho do SUS em `data/saude_desfechos/` (janela E1, 17/10/2026).

Um arquivo por desfecho, todos com a mesma forma, escritos e lidos por UMA função cada
(`gravar_desfecho`, `ler_desfecho`). Os coletores da E1 (SINAN, SISAB, TabNet) e da E2 (SIH,
óbitos) entregam só a série; a forma, a faixa habitual, os cortes do mapa, o último valor e as
marcas de preliminar e parcial nascem aqui, iguais para todos. A página (seção de desfechos da
Saúde, B1) lê só esta forma.

O QUE CADA CAMPO GARANTE
------------------------
- `serie[UF][período]`: inteiro (zero é zero medido) ou `null` (lacuna: período sem dado lido).
  Nunca se preenche lacuna com zero. `BR` é a soma das UFs só onde as 27 têm valor.
- `por_100mil`: a mesma série dividida pela população do Censo 2022 (`populacao_censo2022.json`).
- `faixa_habitual[UF][período do ano]`: o canal endêmico do projeto (`canal_endemico` de
  `coletar_desfechos_saude.py`, importado, não copiado): mediana, p75 e p90 de 2019–2025, com 2024
  à parte, sobre `por_100mil` quando há população.
- `cortes_mapa`: os quintis (20, 40, 60, 80) de todos os valores UF × período de 2019–2025
  (decisão da editoria, §6a de 16/10). **Congelados**: calculados uma vez; a regravação reaproveita
  os do arquivo anterior enquanto a métrica e o período forem os mesmos.
- `ultimo[UF]`: o período mais recente com valor e se ele é parcial; `consolidado`, o mais recente
  que já não é parcial (é o que o mapa mostra).
- `parcial`: os últimos períodos, que ainda crescem com notificação atrasada.
- `anos_preliminares`: anos que a fonte ainda publica como preliminares (o número pode mudar).

Arquivo fora do esquema não substitui o bom: vai para `saude_desfechos/quarentena/` e a rodada
registra a falha (regra 5 da corrente noturna: o esquema quarentena, não apaga).

Peso zero, nunca lido pelo motor do índice. O Monitor não atribui casos ao El Niño.

USO
  python3 desfechos_sus.py --autoteste
  python3 desfechos_sus.py --derivar [dengue chikungunya srag]
"""
import re
import statistics
import sys
from collections import defaultdict

from coletores_base import ler, gravar, rodar_autoteste
from coletar_desfechos_saude import canal_endemico

ESQUEMA = 1
PASTA = "saude_desfechos"
ANOS_CORTES = range(2019, 2026)
PERIODOS = {"semana": 53, "mes": 12}
RESSALVA = "O Monitor não atribui casos ao El Niño."
_CAMPOS = ("esquema", "desfecho", "rotulo", "unidade", "periodo", "territorio", "fonte", "cadencia",
           "coletado_em", "anos_preliminares", "parcial", "serie", "ultimo", "cortes_mapa",
           "faixa_habitual", "ressalva", "lacunas")


class ForaDoEsquema(ValueError):
    """O arquivo não tem a forma comum: vai para a quarentena, nunca substitui o bom."""


# ------------------------------------------------------------------ população (só leitura)
def populacao_por_uf(ler_fn=ler) -> dict:
    """{UF: população do Censo 2022}, somando os municípios. Arquivo ausente → {} (sem taxa)."""
    ref = ler_fn("municipios_ibge_referencia.json") or []
    pop = ler_fn("populacao_censo2022.json") or {}
    out = defaultdict(int)
    for r in ref:
        p = pop.get(str(r.get("codigo_ibge", "")).zfill(7))
        if isinstance(p, int) and r.get("uf"):
            out[r["uf"]] += p
    return dict(out)


def uf_por_codigo(ler_fn=ler) -> dict:
    """{'23': 'CE', ...}: os dois primeiros dígitos do código IBGE para a sigla."""
    return {str(r["codigo_ibge"])[:2]: r["uf"] for r in (ler_fn("municipios_ibge_referencia.json") or [])
            if r.get("codigo_ibge") and r.get("uf")}


# ------------------------------------------------------------------ montagem (funções puras)
def _chaves_parciais(periodos: list, n: int, periodo: str = "mes") -> list:
    """Os n últimos períodos do calendário até o mais recente (mês a mês, não chave a chave: um
    ano sem arquivo no meio da série não empurra o parcial para trás). Função pura."""
    if n <= 0 or not periodos:
        return []
    if periodo != "mes":
        return sorted(periodos)[-n:]
    a, m = int(max(periodos)[:4]), int(max(periodos)[5:])
    out = []
    for _ in range(n):
        out.append(f"{a}-{m:02d}")
        a, m = (a - 1, 12) if m == 1 else (a, m - 1)
    return sorted(p for p in out if p in set(periodos))


def _soma_br(serie: dict, ufs_esperadas: int = 27) -> dict:
    por_per = defaultdict(list)
    for uf, s in serie.items():
        for per, v in s.items():
            por_per[per].append(v)
    return {per: (sum(vs) if len(vs) == ufs_esperadas and None not in vs else None)
            for per, vs in por_per.items()}


def _taxa(serie: dict, populacao: dict) -> dict:
    return {uf: {per: (round(v * 1e5 / populacao[uf], 3) if v is not None else None) for per, v in s.items()}
            for uf, s in serie.items() if populacao.get(uf)}


def quintis(valores: list) -> list:
    """Os quatro cortes que separam cinco classes. Função pura."""
    vs = sorted(v for v in valores if v is not None)
    if len(vs) < 5:
        return []
    return [round(x, 3) for x in statistics.quantiles(vs, n=5, method="inclusive")]


def montar(desfecho: str, rotulo: str, unidade: str, periodo: str, territorio: str, serie: dict,
           fonte: dict, cadencia: str, coletado_em: str, anos_preliminares=(), n_parciais: int = 0,
           populacao: dict = None, anterior: dict = None, lacunas: list = None) -> dict:
    """O arquivo comum a partir da série crua. Função pura (população e anterior vêm de fora)."""
    if periodo not in PERIODOS:
        raise ForaDoEsquema(f"período {periodo!r} fora de {sorted(PERIODOS)}")
    serie = {uf: dict(sorted(s.items())) for uf, s in sorted(serie.items()) if uf != "BR"}
    if len(serie) == 27:
        serie["BR"] = dict(sorted(_soma_br(serie).items()))
    taxa = _taxa(serie, {**(populacao or {}), "BR": sum((populacao or {}).values())}) if populacao else None
    base = taxa or serie
    metrica = "por_100mil" if taxa else "contagem"
    todos = sorted({p for s in serie.values() for p in s})
    parciais = _chaves_parciais(todos, n_parciais, periodo)
    if (anterior and anterior.get("cortes_mapa", {}).get("metrica") == metrica
            and anterior.get("periodo") == periodo and anterior["cortes_mapa"].get("cortes")):
        cortes = anterior["cortes_mapa"]
    else:
        vals = [v for uf, s in base.items() if uf != "BR" for p, v in s.items() if int(p[:4]) in ANOS_CORTES]
        cortes = {"metrica": metrica, "quantis": [20, 40, 60, 80], "anos": [ANOS_CORTES[0], ANOS_CORTES[-1]],
                  "cortes": quintis(vals), "congelados_em": coletado_em}
    faixa = {uf: canal_endemico({p: {"casos": v} for p, v in s.items()}) for uf, s in base.items()}
    ultimo = {}
    for uf, s in serie.items():
        com_valor = [p for p, v in s.items() if v is not None]
        if com_valor:
            p = com_valor[-1]
            ultimo[uf] = {"periodo": p, "valor": s[p], "por_100mil": (taxa or {}).get(uf, {}).get(p),
                          "parcial": p in parciais}
            fechados = [q for q in com_valor if q not in parciais]
            if fechados:
                q = fechados[-1]
                ultimo[uf]["consolidado"] = {"periodo": q, "valor": s[q], "por_100mil": (taxa or {}).get(uf, {}).get(q)}
    obj = {"esquema": ESQUEMA, "desfecho": desfecho, "rotulo": rotulo, "unidade": unidade,
           "periodo": periodo, "territorio": territorio, "fonte": fonte, "cadencia": cadencia,
           "coletado_em": coletado_em, "anos_preliminares": sorted(set(anos_preliminares)),
           "parcial": parciais, "serie": serie, "ultimo": ultimo, "cortes_mapa": cortes,
           "faixa_habitual": faixa, "ressalva": RESSALVA, "lacunas": lacunas or []}
    if taxa:
        obj["por_100mil"] = taxa
    return obj


def validar(obj: dict) -> None:
    """Levanta `ForaDoEsquema` com o primeiro defeito. Função pura."""
    if not isinstance(obj, dict):
        raise ForaDoEsquema("não é objeto")
    falta = [c for c in _CAMPOS if c not in obj]
    if falta:
        raise ForaDoEsquema(f"campos ausentes: {falta}")
    if obj["esquema"] != ESQUEMA:
        raise ForaDoEsquema(f"esquema {obj['esquema']} ≠ {ESQUEMA}")
    if not isinstance(obj["fonte"], dict) or not obj["fonte"].get("url") or not obj["fonte"].get("sistema"):
        raise ForaDoEsquema("fonte sem url ou sistema")
    for uf, s in obj["serie"].items():
        if not (isinstance(uf, str) and len(uf) == 2 and uf.isupper()):
            raise ForaDoEsquema(f"UF inválida: {uf!r}")
        for p, v in s.items():
            if len(p) != 7 or p[4] != "-" or not (1 <= int(p[5:]) <= PERIODOS[obj["periodo"]]):
                raise ForaDoEsquema(f"período inválido em {uf}: {p!r}")
            if v is not None and (not isinstance(v, int) or isinstance(v, bool) or v < 0):
                raise ForaDoEsquema(f"valor inválido em {uf} {p}: {v!r}")
    if not obj["serie"]:
        raise ForaDoEsquema("série vazia: lacuna se declara no catálogo, não com arquivo vazio")


# ------------------------------------------------------------------ escrita e leitura
def caminho(desfecho: str) -> str:
    return f"{PASTA}/{desfecho}.json"


def gravar_desfecho(obj: dict, gravar_fn=gravar) -> bool:
    """Grava o arquivo comum. Fora do esquema → quarentena, e o arquivo bom fica como está."""
    nome = obj.get("desfecho") if isinstance(obj, dict) else None
    try:
        validar(obj)
    except ForaDoEsquema as e:
        gravar_fn(f"{PASTA}/quarentena/{nome or 'sem_nome'}.json", {"motivo": str(e), "conteudo": obj})
        print(f"desfecho {nome}: fora do esquema ({e}); em quarentena, o arquivo anterior fica")
        return False
    gravar_fn(caminho(nome), obj, compacto=True)
    return True


def ler_desfecho(desfecho: str, ler_fn=ler):
    """O arquivo comum, ou None se ausente ou fora do esquema (quem lê declara a lacuna)."""
    obj = ler_fn(caminho(desfecho))
    if obj is None:
        return None
    try:
        validar(obj)
    except ForaDoEsquema:
        return None
    return obj


# ------------------------------------------------------------------ derivados dos arquivos que já existem
# Dengue, chikungunya e SRAG já têm coletor (`coletar_arboviroses_sinan.py`, `coletar_srag_sivep.py`).
# A forma comum nasce LENDO o arquivo deles, sem nova coleta e sem mexer no arquivo que a página de
# hoje lê. As semanas que eles vazam como incompletas (`nowcasting`, contagem sem estimativa) voltam
# como valor e ficam marcadas `parcial`.
DERIVADOS = {
    "dengue": {"origem": "dengue_sinan_serie.json", "rotulo": "Dengue, notificações", "unidade": "notificações"},
    "chikungunya": {"origem": "chik_sinan_serie.json", "rotulo": "Chikungunya, notificações", "unidade": "notificações"},
    "srag": {"origem": "srag_serie.json", "rotulo": "SRAG hospitalizada, notificações", "unidade": "notificações"},
}


def de_serie_existente(orig: dict) -> tuple:
    """(série com as semanas vazadas devolvidas, quantas semanas vazadas). Função pura."""
    serie = {}
    for uf, s in (orig.get("serie") or {}).items():
        if uf == "BR":
            continue
        now = (orig.get("nowcasting") or {}).get(uf, {})
        serie[uf] = {p: (v if v is not None else now.get(p)) for p, v in s.items()}
        for p, v in now.items():
            serie[uf].setdefault(p, v)
    return serie, int(orig.get("se_incompletas") or 0)


def derivar(nome: str, ler_fn=ler, gravar_fn=gravar) -> bool:
    """Grava `<nome>.json` na forma comum a partir do arquivo do coletor existente."""
    cfg = DERIVADOS[nome]
    orig = ler_fn(f"{PASTA}/{cfg['origem']}")
    if not orig or not orig.get("serie"):
        print(f"{nome}: {cfg['origem']} ausente ou vazio; o arquivo anterior fica"); return False
    serie, n = de_serie_existente(orig)
    anterior = ler_fn(caminho(nome))
    if anterior and {u: v for u, v in anterior.get("serie", {}).items() if u != "BR"} == serie:
        print(f"{nome}: {cfg['origem']} sem mudança; nada a regravar"); return False
    fonte = {"sistema": orig.get("sistema"), "url": orig.get("fonte"), "arquivo_de_origem": f"data/{PASTA}/{cfg['origem']}",
             "gerado_em_na_origem": orig.get("gerado_em"), "uf": "residência", "data_do_periodo": "início dos sintomas"}
    data = data_iso(orig.get("gerado_em"))
    obj = montar(desfecho=nome, rotulo=cfg["rotulo"], unidade=cfg["unidade"], periodo="semana",
                 territorio="UF de residência", serie=serie, fonte=fonte,
                 cadencia="a do coletor de origem", coletado_em=data,
                 anos_preliminares=[orig.get("ano_corrente")] if orig.get("ano_corrente") else [],
                 n_parciais=n, populacao=populacao_por_uf(ler_fn), anterior=anterior)
    return gravar_desfecho(obj, gravar_fn=gravar_fn)


def data_iso(br) -> str:
    """'16/10/2026' → '2026-10-16'; o que não for data volta como veio. Função pura."""
    m = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", str(br or ""))
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else str(br or "")


# ------------------------------------------------------------------ autoteste
def _serie_de_teste(ufs=("CE", "PE"), anos=range(2019, 2027), meses=12):
    return {uf: {f"{a}-{m:02d}": (i + m + (a - 2019)) for m in range(1, meses + 1) for a in anos}
            for i, uf in enumerate(ufs)}


def _montado(**kw):
    base = dict(desfecho="teste", rotulo="Teste, casos confirmados", unidade="casos", periodo="mes",
                territorio="UF de residência", serie=_serie_de_teste(),
                fonte={"sistema": "SINAN", "url": "ftp://ftp.datasus.gov.br/x", "arquivos": []},
                cadencia="semanal", coletado_em="2026-10-17", anos_preliminares=[2025, 2026], n_parciais=2,
                populacao={"CE": 100000, "PE": 200000})
    base.update(kw)
    return montar(**base)


def _t_forma():
    o = _montado()
    return (o["parcial"] == ["2026-11", "2026-12"] and o["ultimo"]["CE"]["periodo"] == "2026-12"
            and o["ultimo"]["CE"]["parcial"] and o["por_100mil"]["PE"]["2019-01"] == 1.0
            and o["ultimo"]["CE"]["consolidado"]["periodo"] == "2026-10"
            and len(o["cortes_mapa"]["cortes"]) == 4 and o["cortes_mapa"]["metrica"] == "por_100mil"
            and set(o["faixa_habitual"]["CE"]["01"]) >= {"mediana", "p75", "p90"} and "BR" not in o["serie"])


def _t_cortes_congelados():
    a = _montado()
    s = _serie_de_teste(); s["CE"]["2019-01"] = 10 ** 6
    b = _montado(serie=s, anterior=a, coletado_em="2026-10-24")
    return b["cortes_mapa"] == a["cortes_mapa"] and b["cortes_mapa"]["congelados_em"] == "2026-10-17"


def _t_cortes_recalculam_se_metrica_muda():
    a = _montado()
    b = _montado(populacao=None, anterior=a)
    return b["cortes_mapa"]["metrica"] == "contagem" and b["cortes_mapa"] != a["cortes_mapa"]


def _t_lacuna_nao_vira_zero():
    s = _serie_de_teste(); s["CE"]["2026-12"] = None
    o = _montado(serie=s)
    return o["serie"]["CE"]["2026-12"] is None and o["ultimo"]["CE"]["periodo"] == "2026-11" \
        and o["por_100mil"]["CE"]["2026-12"] is None


def _t_br_so_com_27():
    ufs = [f"A{chr(65 + i)}" for i in range(26)] + ["BA"]
    s = {u: {"2026-01": 1, "2026-02": 2} for u in ufs}; s[ufs[0]]["2026-02"] = None
    o = _montado(serie=s, populacao=None)
    return o["serie"]["BR"] == {"2026-01": 27, "2026-02": None}


def _t_quarentena():
    escritos = {}
    def falso(nome, obj, compacto=False): escritos[nome] = obj
    ruim = _montado(); ruim["serie"]["CE"]["2026-13"] = 1
    ok = gravar_desfecho(_montado(), gravar_fn=falso)
    nok = gravar_desfecho(ruim, gravar_fn=falso)
    return ok and not nok and set(escritos) == {"saude_desfechos/teste.json", "saude_desfechos/quarentena/teste.json"}


def _t_ler_recusa_fora_do_esquema():
    bom = _montado(); ruim = {**bom, "esquema": 99}
    return ler_desfecho("teste", ler_fn=lambda n: bom) == bom and ler_desfecho("teste", ler_fn=lambda n: ruim) is None \
        and ler_desfecho("teste", ler_fn=lambda n: None) is None


def _t_valor_negativo_recusado():
    s = _serie_de_teste(); s["CE"]["2026-01"] = -1
    escritos = []
    return not gravar_desfecho(_montado(serie=s), gravar_fn=lambda n, o, compacto=False: escritos.append(n)) \
        and escritos == ["saude_desfechos/quarentena/teste.json"]


def _t_populacao():
    ref = [{"codigo_ibge": 2304400, "uf": "CE"}, {"codigo_ibge": 2307650, "uf": "CE"}, {"codigo_ibge": 2611606, "uf": "PE"}]
    pop = {"2304400": 10, "2307650": 5, "2611606": 7}
    f = lambda n: {"municipios_ibge_referencia.json": ref, "populacao_censo2022.json": pop}.get(n)
    return populacao_por_uf(ler_fn=f) == {"CE": 15, "PE": 7} and uf_por_codigo(ler_fn=f) == {"23": "CE", "26": "PE"}


_BANCO = ("estados", "saude_uf", "municipios", "indice", "monitor_saude")


def fonte_cita_banco(caminho: str) -> bool:
    """Trava estrutural dos coletores de desfecho: o fonte cita, entre aspas simples ou duplas, algum
    arquivo do índice? Lê o arquivo inteiro; os nomes aqui não levam a extensão, para não se acusarem."""
    rx = re.compile(r"""["'](?:data/)?(?:%s)\.json["']""" % "|".join(_BANCO))
    return bool(rx.search(open(caminho, encoding="utf-8").read()))


def _t_fonte_nao_escreve_banco():
    return not fonte_cita_banco(__file__) and fonte_cita_banco.__doc__ and _t_trava_acusa()


def _t_trava_acusa():
    import os
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(f"gravar('data/{_BANCO[1]}.json', x)\n")
    try:
        return fonte_cita_banco(f.name)
    finally:
        os.unlink(f.name)


def _t_derivar():
    orig = {"sistema": "SINAN", "fonte": "https://x", "gerado_em": "16/10/2026", "ano_corrente": 2026, "se_incompletas": 2,
            "serie": {"CE": {"2019-01": 3, "2026-38": None, "2026-39": None}, "BR": {"2019-01": 3}},
            "nowcasting": {"CE": {"2026-38": 7, "2026-39": 1}}}
    banco = {f"{PASTA}/dengue_sinan_serie.json": orig}
    escritos = []
    def g(n, o, compacto=False): banco[n] = o; escritos.append(n)
    ok1 = derivar("dengue", ler_fn=banco.get, gravar_fn=g); ok2 = derivar("dengue", ler_fn=banco.get, gravar_fn=g)
    o = banco[caminho("dengue")]
    return (ok1 and not ok2 and escritos == [caminho("dengue")] and o["serie"]["CE"]["2026-39"] == 1
            and o["parcial"] == ["2026-38", "2026-39"] and o["periodo"] == "semana" and o["coletado_em"] == "2026-10-16"
            and orig["serie"]["CE"]["2026-38"] is None)


TESTES = {
    "derivado: semanas vazadas voltam como parcial; origem intocada": _t_derivar,
    "forma comum: parcial, último, taxa, quintis, faixa habitual": _t_forma,
    "cortes do mapa congelados na regravação": _t_cortes_congelados,
    "cortes recalculam só se a métrica muda": _t_cortes_recalculam_se_metrica_muda,
    "lacuna fica null, nunca zero": _t_lacuna_nao_vira_zero,
    "BR só onde as 27 UFs têm valor": _t_br_so_com_27,
    "fora do esquema vai à quarentena; o bom fica": _t_quarentena,
    "leitura recusa arquivo fora do esquema": _t_ler_recusa_fora_do_esquema,
    "valor negativo é recusado": _t_valor_negativo_recusado,
    "população por UF a partir dos municípios": _t_populacao,
    "trava estrutural: não escreve nos arquivos do índice": _t_fonte_nao_escreve_banco,
}

if __name__ == "__main__":
    if "--autoteste" in sys.argv:
        sys.exit(rodar_autoteste(TESTES))
    if "--derivar" in sys.argv:
        for nome in sys.argv[sys.argv.index("--derivar") + 1:] or list(DERIVADOS):
            derivar(nome)
        sys.exit(0)
    print(__doc__)
