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
import csv
import io
import json
import pathlib
import re
import sys
from collections import defaultdict

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
RE_ANO_NO_NOME = re.compile(r"/SRAG/(20\d\d)/", re.I)


def recursos_csv(html: str) -> dict:
    """{ano: {'url', 'arquivo'}} lido do JSON que a própria página carrega.

    A URL do arquivo carrega a data de publicação (`INFLUD26-28-09-2026.csv`), então não dá para
    montá-la: ela se descobre. O portal é uma aplicação Next.js e embute o pacote inteiro em
    `__NEXT_DATA__` — é o caminho estável, sem depender do `buildId`, que muda a cada publicação
    do site."""
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        raise ValueError("a página do conjunto não trouxe __NEXT_DATA__ — formato mudou")
    dados = json.loads(m.group(1))
    recursos = (((dados.get("props") or {}).get("pageProps") or {}).get("resources")) or []
    out = {}
    for r in recursos:
        url = str(r.get("url") or "")
        if not url.lower().endswith(".csv"):
            continue
        ano = RE_ANO_NO_NOME.search(url)
        if not ano:
            continue
        out[int(ano.group(1))] = {"url": url, "arquivo": url.rsplit("/", 1)[-1]}
    if not out:
        raise ValueError("nenhum CSV por ano no pacote — formato mudou")
    return out


def agregar_linhas(linhas, ano: int) -> dict:
    """{'BR'|UF: {'AAAA-SS': casos}} contando uma notificação por linha. Função pura.

    Linha sem UF de residência ou sem semana legível **não é contada e não é adivinhada**: ela
    existe no banco e não diz onde nem quando, e inventar qualquer um dos dois seria pior que
    perdê-la. O total nacional é a soma das UFs, e por isso ele também não inclui essas linhas."""
    out = defaultdict(lambda: defaultdict(int))
    for linha in linhas:
        uf = str(linha.get(COL_UF) or "").strip().upper()
        if len(uf) != 2 or not uf.isalpha():
            continue
        bruto = re.sub(r"\D", "", str(linha.get(COL_SEMANA) or ""))
        if not bruto:
            continue
        se = int(bruto[-2:]) if len(bruto) > 2 else int(bruto)
        if not 1 <= se <= 53:
            continue
        chave = f"{ano}-{se:02d}"
        out[uf][chave] += 1
        out["BR"][chave] += 1
    return {loc: dict(v) for loc, v in out.items()}


def juntar(agregados: list) -> dict:
    """Une agregados de anos diferentes. Chaves são 'AAAA-SS', então não há colisão entre anos."""
    out = defaultdict(dict)
    for a in agregados:
        for loc, serie in (a or {}).items():
            out[loc].update(serie)
    return dict(out)


def linhas_do_fluxo(pedacos, limite_linhas: int = None):
    """Gera dicionários de linha a partir de um fluxo de bytes, sem materializar o arquivo.

    O banco vem em latin-1 com `;` — mas nada disso se presume: o delimitador sai do cabeçalho, e a
    decodificação é tolerante, porque uma linha com acento estragado não pode derrubar a leitura de
    dois milhões de outras."""
    resto = b""
    cabecalho = None
    delim = ";"
    n = 0
    for bloco in pedacos:
        resto += bloco
        *linhas, resto = resto.split(b"\n")
        for bruta in linhas:
            texto = bruta.decode("latin-1", "replace").rstrip("\r")
            if cabecalho is None:
                delim = ";" if texto.count(";") >= texto.count(",") else ","
                cabecalho = next(csv.reader(io.StringIO(texto), delimiter=delim))
                continue
            valores = next(csv.reader(io.StringIO(texto), delimiter=delim), None)
            if not valores:
                continue
            yield dict(zip(cabecalho, valores))
            n += 1
            if limite_linhas and n >= limite_linhas:
                return
    if resto and cabecalho is not None:
        valores = next(csv.reader(io.StringIO(resto.decode("latin-1", "replace")), delimiter=delim), None)
        if valores:
            yield dict(zip(cabecalho, valores))


def precisa_reler(cache: dict, ano: int, arquivo: str) -> bool:
    """Ano congelado só se relê quando o arquivo publicado muda de nome."""
    guardado = (cache.get("anos") or {}).get(str(ano))
    if not guardado:
        return True
    return guardado.get("arquivo") != arquivo


def autoteste() -> int:
    casos = []

    html = ('<html><script id="__NEXT_DATA__" type="application/json">'
            + json.dumps({"props": {"pageProps": {"resources": [
                {"url": "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SRAG/2026/INFLUD26-28-09-2026.csv"},
                {"url": "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SRAG/2025/INFLUD25-28-09-2026.csv"},
                {"url": "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SRAG/dicionario.pdf"},
            ]}}})
            + "</script></html>")
    r = recursos_csv(html)
    casos.append(("acha um CSV por ano", sorted(r) == [2025, 2026]))
    casos.append(("guarda o nome do arquivo publicado",
                  r[2026]["arquivo"] == "INFLUD26-28-09-2026.csv"))
    casos.append(("PDF não entra", all(x["url"].endswith(".csv") for x in r.values())))
    try:
        recursos_csv("<html>sem next data</html>")
        casos.append(("página sem __NEXT_DATA__ levanta, não devolve vazio", False))
    except ValueError:
        casos.append(("página sem __NEXT_DATA__ levanta, não devolve vazio", True))

    linhas = [{"SG_UF": "ES", "SEM_PRI": "10"}, {"SG_UF": "es", "SEM_PRI": "10"},
              {"SG_UF": "SP", "SEM_PRI": "202611"}, {"SG_UF": "", "SEM_PRI": "10"},
              {"SG_UF": "SP", "SEM_PRI": ""}, {"SG_UF": "XX1", "SEM_PRI": "10"},
              {"SG_UF": "SP", "SEM_PRI": "99"}]
    a = agregar_linhas(linhas, 2026)
    casos.append(("conta por UF e semana", a["ES"]["2026-10"] == 2))
    casos.append(("semana com ano colado é lida pelos dois últimos dígitos", a["SP"]["2026-11"] == 1))
    casos.append(("o nacional é a soma das UFs", a["BR"]["2026-10"] == 2 and a["BR"]["2026-11"] == 1))
    casos.append(("linha sem UF não é contada nem adivinhada", sum(a["BR"].values()) == 3))
    casos.append(("semana fora de 1–53 não entra", "2026-99" not in a["BR"]))
    casos.append(("UF de três letras não vira UF", "XX" not in a and "XX1" not in a))

    j = juntar([{"BR": {"2025-01": 5}}, {"BR": {"2026-01": 7}, "SP": {"2026-01": 7}}])
    casos.append(("anos diferentes se somam sem colidir",
                  j["BR"] == {"2025-01": 5, "2026-01": 7} and j["SP"]["2026-01"] == 7))

    fluxo = [b'"SG_UF";"SEM_PRI"\n"ES";"10"\n"S', b'P";"11"\n"RJ";"12"\n']
    lidas = list(linhas_do_fluxo(fluxo))
    casos.append(("o fluxo remonta linha partida entre pedaços", len(lidas) == 3))
    casos.append(("e lê os valores certos",
                  [l["SG_UF"] for l in lidas] == ["ES", "SP", "RJ"]))
    casos.append(("o limite de linhas para a leitura",
                  len(list(linhas_do_fluxo(fluxo, limite_linhas=2))) == 2))
    casos.append(("delimitador sai do cabeçalho",
                  [l["SG_UF"] for l in linhas_do_fluxo([b"SG_UF,SEM_PRI\nBA,5\n"])] == ["BA"]))

    cache = {"anos": {"2019": {"arquivo": "INFLUD19-23-03-2026.csv"}}}
    casos.append(("ano congelado com o mesmo arquivo não é relido",
                  not precisa_reler(cache, 2019, "INFLUD19-23-03-2026.csv")))
    casos.append(("arquivo republicado com outro nome é relido",
                  precisa_reler(cache, 2019, "INFLUD19-30-09-2026.csv")))
    casos.append(("ano que não está no cache é lido", precisa_reler(cache, 2020, "x.csv")))

    from coletar_srag_gripe import ANOS_CANAL, canal_endemico, vazar_incompletas
    serie = {f"{ano}-10": 100 + ano for ano in ANOS_CANAL}
    c = canal_endemico(serie)
    casos.append(("o canal endêmico é o mesmo do coletor anterior, reusado",
                  c["10"]["n_anos"] == len(ANOS_CANAL)
                  and c["10"]["p90"] >= c["10"]["p75"] >= c["10"]["mediana"]))
    cons, vaz = vazar_incompletas({f"2026-{s:02d}": 1 for s in range(1, 21)}, 2026)
    casos.append(("as últimas 4 SE do ano corrente saem como incompletas",
                  len(vaz) == 4 and cons["2026-20"] is None and cons["2026-16"] == 1))

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

    try:
        html = buscar(PAGINA, timeout=60).decode("utf-8", "replace")
        recursos = recursos_csv(html)
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
            serie = agregar_linhas(
                linhas_do_fluxo(buscar_em_fluxo(recursos[ano]["url"], timeout=180,
                                                origem="coletar_srag_sivep")), ano)
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
