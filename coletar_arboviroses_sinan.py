#!/usr/bin/env python3
"""Dengue e chikungunya pela fonte primária — SINAN no Portal de Dados Abertos do SUS.

Item 2 do bloco "fontes primárias" (decisão da central, 29/09/2026). Até aqui as contagens vinham
do **InfoDengue**, que é produto derivado do SINAN: ele estima casos prováveis e calcula nível de
alerta a partir da mesma notificação que o SINAN publica. A regra da decisão é clara — primária
quando existir, derivado só para o que a primária não dá.

O QUE CADA FONTE PASSA A FAZER
------------------------------
- **SINAN (aqui):** a contagem. Notificações de dengue e de chikungunya, por UF de residência e
  semana epidemiológica de primeiros sintomas.
- **InfoDengue (onde já está):** o **nível de alerta**, que é interpretação da série e não existe no
  banco primário. Ele não passa a contar nada.

CONTA-SE NOTIFICAÇÃO, E ISSO PRECISA SER DITO
---------------------------------------------
A decisão pede "casos por notificação", e é o que se faz: cada linha do banco é uma notificação. Uma
parte delas será **descartada** depois pela investigação (`CLASSI_FIN = 5`), e outra parte ainda não
tem classificação fechada. Contar só as confirmadas daria um número menor e mais velho — a
classificação demora —, e contar notificação é o que o próprio Ministério publica como série
corrente. O que não se pode é chamar notificação de caso confirmado, e o campo `_governanca` do
arquivo diz exatamente o que foi contado.

MICRODADO NÃO SE GUARDA
-----------------------
O banco tem 121 colunas com sexo, raça, gestação, sintomas, sorologia e município. Nada disso entra
no repositório: o zip é lido, o CSV de dentro sai em pedaços, agrega-se por UF × semana e descarta.

USO
  python3 coletar_arboviroses_sinan.py --autoteste
  python3 coletar_arboviroses_sinan.py --relatorio
  python3 coletar_arboviroses_sinan.py [--agravo dengue|chikungunya]
"""
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

AGRAVOS = {
    "dengue": {
        "pagina": "https://dadosabertos.saude.gov.br/dataset/arboviroses-dengue",
        "padrao_ano": r"DENGBR(\d\d)\.csv",
        "arquivo": "saude_desfechos/dengue_sinan_serie.json",
        "rotulo": "dengue",
    },
    "chikungunya": {
        "pagina": "https://dadosabertos.saude.gov.br/dataset/arboviroses-febre-de-chikungunya",
        "padrao_ano": r"CHIKBR(\d\d)\.csv",
        "arquivo": "saude_desfechos/chik_sinan_serie.json",
        "rotulo": "febre de chikungunya",
    },
}
CACHE = "saude_desfechos/arboviroses_sinan_agregados.json"
COL_UF = "SG_UF"          # UF de residência (código numérico do IBGE)
COL_SEMANA = "SEM_PRI"    # semana epidemiológica dos primeiros sintomas
ANOS_CONGELADOS = range(2000, 2025)   # só o ano corrente e o anterior seguem sendo republicados
RESSALVA = ("O Monitor não atribui casos ao El Niño. A série é a contagem de NOTIFICAÇÕES no SINAN "
            "(Ministério da Saúde), por UF de residência e semana epidemiológica de primeiros "
            "sintomas — não é contagem de casos confirmados: parte das notificações é descartada "
            "pela investigação e parte ainda não tem classificação fechada.")


def anos_uteis(recursos: dict, anos_canal, ano_corrente: int) -> list:
    """Os anos que interessam: os do canal endêmico mais os que já correram depois dele.

    O banco do SINAN publica desde 2000. Ler 27 anos para um canal de sete seria pagar rede por
    dado que nenhuma conta usa."""
    quero = set(anos_canal) | {a for a in range(min(anos_canal), ano_corrente + 1)}
    return sorted(a for a in recursos if a in quero)


def autoteste() -> int:
    from saude_opendatasus import agregar_por_uf_semana, recursos_por_ano
    casos = []
    REF = [{"codigo_ibge": 3205002, "uf": "ES"}, {"codigo_ibge": 3550308, "uf": "SP"}]

    html = ('<html><script id="__NEXT_DATA__" type="application/json">'
            + json.dumps({"props": {"pageProps": {"resources": [
                {"url": "https://x/SINAN/Dengue/csv/DENGBR26.csv.zip"},
                {"url": "https://x/SINAN/Dengue/csv/DENGBR19.csv.zip"},
                {"url": "https://x/SINAN/Dengue/csv/DENGBR05.csv.zip"}]}}})
            + "</script></html>")
    r = recursos_por_ano(html, AGRAVOS["dengue"]["padrao_ano"])
    casos.append(("acha um arquivo por ano", sorted(r) == [2005, 2019, 2026]))

    uteis = anos_uteis(r, range(2019, 2026), 2026)
    casos.append(("lê do primeiro ano do canal em diante", uteis == [2019, 2026]))
    casos.append(("ano anterior ao canal fica de fora", 2005 not in uteis))

    linhas = [{"SG_UF": "32", "SEM_PRI": "10", "CLASSI_FIN": "10"},
              {"SG_UF": "32", "SEM_PRI": "10", "CLASSI_FIN": "5"},
              {"SG_UF": "35", "SEM_PRI": "202611", "CLASSI_FIN": ""}]
    a = agregar_por_uf_semana(linhas, 2026, COL_UF, COL_SEMANA, REF)
    casos.append(("conta NOTIFICAÇÃO, inclusive a descartada e a sem classificação",
                  a["ES"]["2026-10"] == 2 and a["SP"]["2026-11"] == 1))
    casos.append(("o código de UF do SINAN vira sigla", "ES" in a and "SP" in a))
    casos.append(("a ressalva diz que é notificação e não caso confirmado",
                  "NOTIFICAÇÕES" in RESSALVA and "não é contagem de casos confirmados" in RESSALVA))
    casos.append(("os dois agravos têm arquivo próprio",
                  AGRAVOS["dengue"]["arquivo"] != AGRAVOS["chikungunya"]["arquivo"]))
    casos.append(("a coluna de semana é a de primeiros sintomas", COL_SEMANA == "SEM_PRI"))
    casos.append(("a coluna de UF é a de residência", COL_UF == "SG_UF"))

    ruins = [n for n, ok in casos if not ok]
    for n, ok in casos:
        print(f"  {'OK  ' if ok else 'FALHA'} {n}")
    if ruins:
        print(f"X AUTOTESTE: {len(ruins)} caso(s) reprovado(s).")
        return 1
    print(f"OK AUTOTESTE — {len(casos)} casos, sem rede e sem escrita.")
    return 0


def coletar_um(chave: str, cfg: dict, cache: dict, deps) -> int:
    buscar, gravar_em, hoje_editorial, log_busca, registrar_lacuna, DATA = deps
    from coletar_srag_gripe import ANOS_CANAL, SE_INCOMPLETAS, canal_endemico, vazar_incompletas
    from saude_opendatasus import (agregar_por_uf_semana, juntar, linhas_do_fluxo, pedacos_do_zip,
                                   precisa_reler, recursos_por_ano)

    try:
        html = buscar(cfg["pagina"], timeout=60).decode("utf-8", "replace")
        recursos = recursos_por_ano(html, cfg["padrao_ano"])
    except Exception as e:  # noqa: BLE001
        registrar_lacuna(f"SINAN ({cfg['rotulo']}) — catálogo", f"{type(e).__name__}: {e}"[:180],
                         canal="DOU", camada=1)
        print(f"{chave}: catálogo ilegível ({type(e).__name__}) — lacuna declarada")
        return 0

    ano_corrente = hoje_editorial().year
    alvo = anos_uteis(recursos, ANOS_CANAL, ano_corrente)
    print(f"{chave}: {len(recursos)} ano(s) publicados; {len(alvo)} usados: {alvo}")
    if "--relatorio" in sys.argv:
        for a in alvo:
            print(f"    {a}: {recursos[a]['arquivo']}")
        return 0

    agregados, lidos, reusados, falhas = [], [], [], {}
    for ano in alvo:
        arquivo = recursos[ano]["arquivo"]
        chave_cache = f"{chave}:{ano}"
        if ano in ANOS_CONGELADOS and not precisa_reler(cache, chave_cache, arquivo):
            agregados.append(cache["anos"][str(chave_cache)]["serie"])
            reusados.append(ano)
            continue
        try:
            bruto = buscar(recursos[ano]["url"], timeout=300)
            serie = agregar_por_uf_semana(linhas_do_fluxo(pedacos_do_zip(bruto)),
                                          ano, COL_UF, COL_SEMANA)
        except Exception as e:  # noqa: BLE001
            falhas[ano] = type(e).__name__
            continue
        if not serie:
            falhas[ano] = "arquivo lido sem nenhuma linha utilizável"
            continue
        agregados.append(serie)
        lidos.append(ano)
        cache["anos"][str(chave_cache)] = {"arquivo": arquivo, "serie": serie,
                                           "lido_em": hoje_editorial().isoformat()}

    if falhas:
        registrar_lacuna(f"SINAN ({cfg['rotulo']}) — banco por ano",
                         "; ".join(f"{a}: {m}" for a, m in sorted(falhas.items()))[:180],
                         canal="DOU", camada=1)
    if not agregados:
        print(f"{chave}: nenhum ano lido — lacuna declarada, série não escrita")
        return 0

    serie = juntar(agregados)
    canal = {loc: canal_endemico(s) for loc, s in serie.items()}
    consolidada, nowcasting = {}, {}
    for loc, s in serie.items():
        cons, vaz = vazar_incompletas(s, ano_corrente)
        consolidada[loc] = cons
        nowcasting[loc] = {k: s[k] for k in vaz if k in s}

    gov = (f"{cfg['rotulo'].capitalize()} — nacional e por UF (§36, catálogo). Peso zero, sem nota, "
           f"sem faixa. " + RESSALVA + f" Canal endêmico: mediana/p75/p90 de {min(ANOS_CANAL)}–"
           f"{max(ANOS_CANAL)}. Últimas {SE_INCOMPLETAS} SE marcadas como incompletas: a notificação "
           f"chega depois do adoecimento, e o número dessas semanas ainda sobe. O nível de alerta "
           f"continua vindo do InfoDengue, que é produto derivado — esta série não o substitui.")
    (DATA / "saude_desfechos").mkdir(parents=True, exist_ok=True)
    gravar_em(DATA / cfg["arquivo"], {
        "_governanca": gov, "gerado_em": hoje_editorial().strftime("%d/%m/%Y"),
        "fonte": cfg["pagina"], "sistema": "SINAN (Ministério da Saúde)",
        "indicador": chave, "conta": "notificacoes", "ano_corrente": ano_corrente,
        "anos_canal": list(ANOS_CANAL), "se_incompletas": SE_INCOMPLETAS,
        "anos_lidos": sorted(lidos + reusados), "anos_reusados_do_cache": sorted(reusados),
        "serie": consolidada, "nowcasting": nowcasting, "canal_endemico": canal})
    log_busca("DOU", 1, [cfg["pagina"]], "registro", nivel="nacional", n_resultados=len(serie),
              resultados=f"SINAN/{chave}: {len(serie)} localidade(s); lidos {sorted(lidos)}")
    print(f"{chave}: {len(serie)} localidade(s); lidos {sorted(lidos)}, reusados {sorted(reusados)}; "
          f"última SE (BR): {max(serie.get('BR', {}), default='—')}")
    return 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()

    from coletores_base import DATA, buscar, gravar_em, hoje_editorial, log_busca, registrar_lacuna
    deps = (buscar, gravar_em, hoje_editorial, log_busca, registrar_lacuna, DATA)

    caminho = DATA / CACHE
    cache = json.loads(caminho.read_text(encoding="utf-8")) if caminho.exists() else {}
    cache.setdefault("_governanca", (
        "Agregado por UF e semana epidemiológica dos bancos do SINAN (dengue e chikungunya). "
        "Microdado NÃO é guardado: o zip de cada ano é lido e descartado. Ano fechado só é relido "
        "quando o arquivo publicado muda de nome."))
    cache.setdefault("anos", {})

    escolhido = None
    if "--agravo" in sys.argv:
        escolhido = sys.argv[sys.argv.index("--agravo") + 1]
        if escolhido not in AGRAVOS:
            print(f"--agravo aceita {sorted(AGRAVOS)}")
            return 2

    for chave, cfg in AGRAVOS.items():
        if escolhido and chave != escolhido:
            continue
        coletar_um(chave, cfg, cache, deps)

    if "--relatorio" not in sys.argv:
        gravar_em(caminho, cache)   # §229
    return 0


if __name__ == "__main__":
    sys.exit(main())
