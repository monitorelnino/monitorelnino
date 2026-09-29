#!/usr/bin/env python3
"""SRAG hospitalizada pela fonte primária — SIVEP-Gripe no Portal de Dados Abertos do SUS.

Decisão da central de 29/09/2026 (bloco 4 · Doenças respiratórias). O coletor anterior,
`coletar_srag_gripe.py`, depende da série do InfoGripe no GitLab da Fiocruz, e as duas URLs
falham desde setembro: `gitlab.procc.fiocruz.br` não responde e `gitlab.fiocruz.br` devolve
página de login — repositório passou a exigir autenticação. **Login é recusa que se respeita**
(§170), e o coletor fazia o certo ao declarar lacuna em vez de inventar série.

A troca é para a fonte **primária**: o Sivep-Gripe é o sistema oficial de registro de casos e
óbitos por SRAG no Brasil, e o Ministério da Saúde publica o banco completo, por ano
epidemiológico, com atualização semanal. A hierarquia de fontes da METODOLOGIA já prefere a
primária; o InfoGripe era o atalho, não a origem.

O QUE MUDA NO DADO, DITO EM VOZ ALTA
------------------------------------
A série do InfoGripe trazia **estimativa de dados recentes** (nowcasting da própria Fiocruz). Esta
traz **contagem de notificações como estão no sistema** — sem estimativa. As últimas semanas
aparecem menores do que ficarão, porque notificação e resultado laboratorial chegam depois; é o
mesmo fenômeno de sempre, e por isso as últimas 4 SE seguem marcadas como incompletas. O que não
existe mais é a estimativa: onde o InfoGripe dizia "provavelmente serão N", aqui se diz "até agora
são N, e este número ainda sobe".

MICRODADO NÃO SE GUARDA
-----------------------
Cada ano tem ~250 MB de microdado com sexo, idade, raça, município e comorbidades. Nada disso entra
no repositório: o arquivo é lido **em fluxo**, agregado por UF × semana epidemiológica, e
descartado. O que se guarda é a contagem.

ANO CONGELADO SE LÊ UMA VEZ
---------------------------
O próprio portal declara: 2019 a 2024 estão "congelados", e só o ano corrente é "banco vivo". O
agregado dos anos congelados fica em `data/saude_desfechos/srag_sivep_agregados.json`, com o nome
do arquivo de origem; ele só é relido se o nome mudar. Sem isso, o canal endêmico custaria 1,5 GB
de rede por semana para produzir o mesmo número.

USO
  python3 coletar_srag_sivep.py --autoteste
  python3 coletar_srag_sivep.py --relatorio     # o que seria lido, sem baixar
  python3 coletar_srag_sivep.py
"""
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

PAGINA = "https://dadosabertos.saude.gov.br/dataset/srag-2019-a-2026"
SAIDA = "saude_desfechos/srag_serie.json"
CACHE = "saude_desfechos/srag_sivep_agregados.json"
ANOS_CONGELADOS = range(2019, 2025)      # o portal declara 2019–2024 congelados
RESSALVA = ("O Monitor não atribui casos ao El Niño. A série é a contagem de notificações de SRAG "
            "hospitalizada no Sivep-Gripe (Ministério da Saúde), por UF de residência e semana "
            "epidemiológica de primeiros sintomas, sem estimativa de dados recentes.")
# Colunas do banco, pelo dicionário de variáveis do próprio conjunto.
COL_SEMANA = "SEM_PRI"     # semana epidemiológica dos primeiros sintomas
COL_UF = "SG_UF"           # UF de residência
PADRAO_ANO = r"/SRAG/(20\d\d)/"   # o ano vem do caminho do arquivo no bucket







def autoteste() -> int:
    """O que é específico do SRAG. O que migrou para `saude_opendatasus.py` é testado lá — e este
    autoteste prova que a ligação existe, em vez de repetir os casos."""
    from coletar_srag_gripe import ANOS_CANAL, canal_endemico, vazar_incompletas
    from saude_opendatasus import agregar_por_uf_semana, recursos_por_ano
    casos = []

    html = ('<html><script id="__NEXT_DATA__" type="application/json">'
            + json.dumps({"props": {"pageProps": {"resources": [
                {"url": "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SRAG/2026/INFLUD26-28-09-2026.csv"},
                {"url": "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SRAG/2025/INFLUD25-28-09-2026.csv"},
                {"url": "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SRAG/dicionario.pdf"}]}}})
            + "</script></html>")
    r = recursos_por_ano(html, PADRAO_ANO, sufixos=(".csv",))
    casos.append(("o padrão do SRAG acha um CSV por ano", sorted(r) == [2025, 2026]))
    casos.append(("guarda o nome do arquivo publicado, que carrega a data",
                  r[2026]["arquivo"] == "INFLUD26-28-09-2026.csv"))

    # No SIVEP-Gripe a UF vem como SIGLA, não como código — é a diferença que justifica o
    # `uf_da_linha` aceitar as duas formas.
    a = agregar_por_uf_semana([{"SG_UF": "ES", "SEM_PRI": "10"}, {"SG_UF": "es", "SEM_PRI": "10"},
                               {"SG_UF": "SP", "SEM_PRI": "202611"}],
                              2026, COL_UF, COL_SEMANA)
    casos.append(("conta por UF e semana, com a sigla do SIVEP", a["ES"]["2026-10"] == 2))
    casos.append(("semana com ano colado é lida pelos dois últimos dígitos", a["SP"]["2026-11"] == 1))

    serie = {f"{ano}-10": 100 + ano for ano in ANOS_CANAL}
    c = canal_endemico(serie)
    casos.append(("o canal endêmico é o do coletor anterior, reusado e não recriado",
                  c["10"]["n_anos"] == len(ANOS_CANAL)
                  and c["10"]["p90"] >= c["10"]["p75"] >= c["10"]["mediana"]))
    cons, vaz = vazar_incompletas({f"2026-{s:02d}": 1 for s in range(1, 21)}, 2026)
    casos.append(("as últimas 4 SE do ano corrente saem como incompletas",
                  len(vaz) == 4 and cons["2026-20"] is None and cons["2026-16"] == 1))
    casos.append(("os anos congelados declarados são os que o portal declara",
                  list(ANOS_CONGELADOS) == list(range(2019, 2025))))

    ruins = [n for n, ok in casos if not ok]
    for n, ok in casos:
        print(f"  {'OK  ' if ok else 'FALHA'} {n}")
    if ruins:
        print(f"X AUTOTESTE: {len(ruins)} caso(s) reprovado(s).")
        return 1
    print(f"OK AUTOTESTE — {len(casos)} casos, sem rede e sem escrita.")
    return 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()

    from coletar_srag_gripe import ANOS_CANAL, SE_INCOMPLETAS, canal_endemico, vazar_incompletas
    from coletores_base import (DATA, buscar, buscar_em_fluxo, gravar_em, hoje_editorial,
                                log_busca, registrar_lacuna)
    from saude_opendatasus import (agregar_por_uf_semana, juntar, linhas_do_fluxo, precisa_reler,
                                   recursos_por_ano)

    try:
        html = buscar(PAGINA, timeout=60).decode("utf-8", "replace")
        recursos = recursos_por_ano(html, PADRAO_ANO, sufixos=(".csv",))
    except Exception as e:  # noqa: BLE001
        registrar_lacuna("SIVEP-Gripe (catálogo do conjunto SRAG)", f"{type(e).__name__}: {e}"[:180],
                         canal="DOU", camada=1)
        print(f"srag: não foi possível ler o catálogo ({type(e).__name__}) — lacuna declarada")
        return 0

    print(f"{len(recursos)} ano(s) publicados: {sorted(recursos)}")
    if "--relatorio" in sys.argv:
        for ano in sorted(recursos):
            print(f"  {ano}: {recursos[ano]['arquivo']}")
        return 0

    caminho_cache = DATA / CACHE
    cache = json.loads(caminho_cache.read_text(encoding="utf-8")) if caminho_cache.exists() else {}
    cache.setdefault("_governanca", (
        "Agregado por UF e semana epidemiológica do banco do SIVEP-Gripe. Microdado NÃO é guardado: "
        "o arquivo de cada ano é lido em fluxo e descartado. Ano congelado (2019–2024, declarado "
        "pelo portal) só é relido quando o arquivo publicado muda de nome."))
    cache.setdefault("anos", {})

    agregados, lidos, reusados, falhas = [], [], [], {}
    for ano in sorted(recursos):
        arquivo = recursos[ano]["arquivo"]
        congelado = ano in ANOS_CONGELADOS
        if congelado and not precisa_reler(cache, ano, arquivo):
            agregados.append(cache["anos"][str(ano)]["serie"])
            reusados.append(ano)
            continue
        try:
            serie = agregar_por_uf_semana(
                linhas_do_fluxo(buscar_em_fluxo(recursos[ano]["url"], timeout=180,
                                                origem="coletar_srag_sivep")),
                ano, COL_UF, COL_SEMANA)
        except Exception as e:  # noqa: BLE001
            falhas[ano] = f"{type(e).__name__}"
            continue
        if not serie:
            falhas[ano] = "arquivo lido sem nenhuma linha utilizável"
            continue
        agregados.append(serie)
        lidos.append(ano)
        cache["anos"][str(ano)] = {"arquivo": arquivo, "serie": serie,
                                   "lido_em": hoje_editorial().isoformat()}

    if falhas:
        registrar_lacuna("SIVEP-Gripe (banco SRAG por ano)",
                         "; ".join(f"{a}: {m}" for a, m in sorted(falhas.items()))[:180],
                         canal="DOU", camada=1)
    if not agregados:
        print("srag: nenhum ano lido — lacuna declarada, série não escrita")
        return 0

    gravar_em(caminho_cache, cache)   # §229
    serie = juntar(agregados)
    ano_corrente = hoje_editorial().year
    canal = {loc: canal_endemico(s) for loc, s in serie.items()}
    consolidada, nowcasting = {}, {}
    for loc, s in serie.items():
        cons, vaz = vazar_incompletas(s, ano_corrente)
        consolidada[loc] = cons
        nowcasting[loc] = {k: s[k] for k in vaz if k in s}

    gov = ("SRAG hospitalizada — nacional e por UF (§36, catálogo). Peso zero, sem nota, sem faixa. "
           + RESSALVA + f" Canal endêmico: mediana/p75/p90 de {min(ANOS_CANAL)}–{max(ANOS_CANAL)}. "
           f"Últimas {SE_INCOMPLETAS} SE marcadas como incompletas: notificação e resultado "
           "laboratorial chegam depois, e o número dessas semanas ainda sobe. Diferente da série "
           "anterior (InfoGripe), esta NÃO traz estimativa de dados recentes — é a contagem como "
           "está no sistema.")
    (DATA / "saude_desfechos").mkdir(parents=True, exist_ok=True)
    gravar_em(DATA / SAIDA, {
        "_governanca": gov, "gerado_em": hoje_editorial().strftime("%d/%m/%Y"),
        "fonte": PAGINA, "sistema": "SIVEP-Gripe (Ministério da Saúde)",
        "indicador": "srag", "ano_corrente": ano_corrente, "anos_canal": ANOS_CANAL,
        "se_incompletas": SE_INCOMPLETAS, "anos_lidos": sorted(lidos + reusados),
        "anos_reusados_do_cache": sorted(reusados),
        "serie": consolidada, "nowcasting": nowcasting, "canal_endemico": canal})

    log_busca("DOU", 1, [PAGINA], "registro", nivel="nacional", n_resultados=len(serie),
              resultados=(f"SRAG/SIVEP-Gripe: {len(serie)} localidade(s); anos lidos {sorted(lidos)}; "
                          f"reusados do cache {sorted(reusados)}"))
    ult = max(serie.get("BR", {}), default="—")
    print(f"srag: {len(serie)} localidade(s); anos lidos {sorted(lidos)}, reusados {sorted(reusados)}; "
          f"última SE (BR): {ult}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
