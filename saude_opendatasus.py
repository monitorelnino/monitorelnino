#!/usr/bin/env python3
"""Peças comuns aos coletores de desfecho que leem o Portal de Dados Abertos do SUS.

29/09/2026 (bloco "fontes primárias"). O primeiro coletor por fonte primária foi o de SRAG
(`coletar_srag_sivep.py`); o segundo, o de arboviroses. Os dois descobrem recursos na mesma
página, leem arquivo grande em fluxo, agregam por UF e semana epidemiológica e guardam só o
agregado. Escrever isso duas vezes seria copiar — e cópia envelhece em silêncio, que é a lição do
§213 e do §222.

O QUE MORA AQUI
---------------
- descoberta de recursos por ano, do JSON que a própria página carrega;
- leitura de CSV em fluxo, com o delimitador saindo do cabeçalho;
- leitura de CSV dentro de `.zip` (o SINAN publica assim);
- resolução de UF, tanto por sigla quanto pelo código numérico do IBGE;
- agregação por UF × semana epidemiológica;
- cache de ano congelado.

O QUE NÃO MORA AQUI
-------------------
Regra de desfecho: quais colunas, qual ano, o que conta e o que não conta. Isso é de cada coletor,
porque é onde cada sistema difere — e esconder essa diferença numa função genérica seria fingir que
SRAG e dengue se contam do mesmo jeito.
"""
import csv
import io
import json
import pathlib
import re
import zipfile
from collections import defaultdict

RAIZ = pathlib.Path(__file__).resolve().parent

_UF_POR_CODIGO = None


def uf_por_codigo(codigo, referencia=None) -> str | None:
    """'35' ou '352900' -> 'SP'. None quando não é código de UF conhecido.

    O SINAN grava a UF como código numérico do IBGE; o SIVEP-Gripe grava a sigla. Os dois passam
    por aqui para que nenhum coletor invente a conversão por conta própria."""
    global _UF_POR_CODIGO
    bruto = re.sub(r"\D", "", str(codigo or ""))
    if len(bruto) < 2:
        return None
    if _UF_POR_CODIGO is None or referencia is not None:
        ref = referencia if referencia is not None else json.loads(
            (RAIZ / "data" / "municipios_ibge_referencia.json").read_text(encoding="utf-8"))
        mapa = {str(x["codigo_ibge"])[:2]: x["uf"] for x in ref}
        if referencia is not None:
            return mapa.get(bruto[:2])
        _UF_POR_CODIGO = mapa
    return _UF_POR_CODIGO.get(bruto[:2])


def uf_da_linha(valor, referencia=None) -> str | None:
    """Aceita sigla ('ES') ou código ('32'). Devolve a sigla, ou None — nunca chuta."""
    t = str(valor or "").strip().upper()
    if len(t) == 2 and t.isalpha():
        return t
    return uf_por_codigo(t, referencia)


def recursos_por_ano(html: str, padrao_ano: str, sufixos=(".csv", ".csv.zip")) -> dict:
    """{ano: {'url', 'arquivo'}} do JSON embutido na página do conjunto.

    A URL do arquivo carrega a data de publicação ou o ano no nome, então não se monta: descobre-se.
    O portal é uma aplicação Next.js e embute o pacote inteiro em `__NEXT_DATA__` — é o caminho
    estável, sem depender do `buildId`, que muda a cada publicação do site."""
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        raise ValueError("a página do conjunto não trouxe __NEXT_DATA__ — formato mudou")
    dados = json.loads(m.group(1))
    recursos = (((dados.get("props") or {}).get("pageProps") or {}).get("resources")) or []
    padrao = re.compile(padrao_ano, re.I)
    out = {}
    for r in recursos:
        url = str(r.get("url") or "")
        if not any(url.lower().endswith(s) for s in sufixos):
            continue
        ano = padrao.search(url)
        if not ano:
            continue
        ano = int(ano.group(1))
        if ano < 100:                      # nome curto tipo DENGBR26 -> 2026
            ano += 2000
        out[ano] = {"url": url, "arquivo": url.rsplit("/", 1)[-1]}
    if not out:
        raise ValueError("nenhum arquivo por ano no pacote — formato mudou")
    return out


def linhas_do_fluxo(pedacos, limite_linhas: int = None):
    """Gera dicionários de linha a partir de um fluxo de bytes, sem materializar o arquivo.

    Delimitador sai do cabeçalho e a decodificação é tolerante: uma linha com acento estragado não
    pode derrubar a leitura de dois milhões de outras."""
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
                cabecalho = [c.strip().strip('"').upper()
                             for c in next(csv.reader(io.StringIO(texto), delimiter=delim))]
                continue
            valores = next(csv.reader(io.StringIO(texto), delimiter=delim), None)
            if not valores:
                continue
            yield dict(zip(cabecalho, valores))
            n += 1
            if limite_linhas and n >= limite_linhas:
                return
    if resto and cabecalho is not None:
        valores = next(csv.reader(io.StringIO(resto.decode("latin-1", "replace")),
                                  delimiter=delim), None)
        if valores:
            yield dict(zip(cabecalho, valores))


def pedacos_do_zip(bruto: bytes, pedaco: int = 1 << 20):
    """Gera o conteúdo do primeiro arquivo de um zip, em pedaços.

    O SINAN publica `.csv.zip`: o zip guarda o índice no FIM do arquivo, então ele não se lê em
    fluxo direto da rede — baixa-se o zip (uma dezena de megabytes) e o CSV de dentro, esse sim, sai
    em pedaços, sem nunca virar um texto de cem megabytes na memória."""
    z = zipfile.ZipFile(io.BytesIO(bruto))
    nomes = [i.filename for i in z.infolist() if not i.is_dir()]
    if not nomes:
        raise ValueError("zip sem arquivo dentro")
    with z.open(nomes[0]) as f:
        while True:
            bloco = f.read(pedaco)
            if not bloco:
                break
            yield bloco


def agregar_por_uf_semana(linhas, ano: int, col_uf: str, col_semana: str,
                          referencia=None, filtro=None) -> dict:
    """{'BR'|UF: {'AAAA-SS': n}}, contando uma linha por ocorrência. Função pura.

    Linha sem UF ou sem semana legível **não é contada e não é adivinhada**: ela existe no banco e
    não diz onde nem quando, e inventar qualquer um dos dois seria pior que perdê-la. O total
    nacional é a soma das UFs, e por isso ele também não as inclui.

    `filtro(linha) -> bool` deixa cada coletor dizer o que conta, sem que esta função saiba de
    classificação de caso — que é regra de desfecho, não de leitura."""
    out = defaultdict(lambda: defaultdict(int))
    for linha in linhas:
        if filtro is not None and not filtro(linha):
            continue
        uf = uf_da_linha(linha.get(col_uf), referencia)
        if not uf:
            continue
        bruto = re.sub(r"\D", "", str(linha.get(col_semana) or ""))
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


def precisa_reler(cache: dict, ano: int, arquivo: str) -> bool:
    """Ano congelado só se relê quando o arquivo publicado muda de nome."""
    guardado = (cache.get("anos") or {}).get(str(ano))
    if not guardado:
        return True
    return guardado.get("arquivo") != arquivo


def autoteste() -> int:
    casos = []
    REF = [{"codigo_ibge": 3205002, "uf": "ES", "nome": "Serra"},
           {"codigo_ibge": 3550308, "uf": "SP", "nome": "São Paulo"}]

    casos.append(("código de UF vira sigla", uf_por_codigo("32", REF) == "ES"))
    casos.append(("código de município vira a UF dele", uf_por_codigo("352900", REF) == "SP"))
    casos.append(("código desconhecido não vira UF", uf_por_codigo("99", REF) is None))
    casos.append(("sigla passa direto", uf_da_linha("es", REF) == "ES"))
    casos.append(("código também é aceito", uf_da_linha("35", REF) == "SP"))
    casos.append(("vazio não vira UF", uf_da_linha("", REF) is None and uf_da_linha(None, REF) is None))
    casos.append(("três letras não é sigla nem código", uf_da_linha("XXX", REF) is None))

    html = ('<html><script id="__NEXT_DATA__" type="application/json">'
            + json.dumps({"props": {"pageProps": {"resources": [
                {"url": "https://x/SINAN/Dengue/csv/DENGBR26.csv.zip"},
                {"url": "https://x/SINAN/Dengue/csv/DENGBR25.csv.zip"},
                {"url": "https://x/SINAN/Dengue/dic.pdf"}]}}})
            + "</script></html>")
    r = recursos_por_ano(html, r"DENGBR(\d\d)\.csv")
    casos.append(("ano de dois dígitos vira ano de quatro", sorted(r) == [2025, 2026]))
    casos.append(("PDF fica de fora", all(x["url"].endswith(".zip") for x in r.values())))
    r2 = recursos_por_ano(html.replace("DENGBR26", "SRAG/2026/INFLUD26").replace(".csv.zip", ".csv"),
                          r"/(20\d\d)/", sufixos=(".csv",))
    casos.append(("ano de quatro dígitos no caminho também é lido", 2026 in r2))
    try:
        recursos_por_ano("<html>nada</html>", r"(\d\d)")
        casos.append(("página sem __NEXT_DATA__ levanta", False))
    except ValueError:
        casos.append(("página sem __NEXT_DATA__ levanta", True))

    fluxo = [b'"SG_UF";"SEM_PRI"\n"32";"10"\n"3', b'5";"11"\n']
    lidas = list(linhas_do_fluxo(fluxo))
    casos.append(("o fluxo remonta linha partida entre pedaços", len(lidas) == 2))
    casos.append(("o cabeçalho é normalizado para maiúsculas sem aspas",
                  set(lidas[0]) == {"SG_UF", "SEM_PRI"}))
    casos.append(("o limite de linhas para a leitura",
                  len(list(linhas_do_fluxo(fluxo, limite_linhas=1))) == 1))

    a = agregar_por_uf_semana(lidas, 2026, "SG_UF", "SEM_PRI", REF)
    casos.append(("agrega por UF e semana", a["ES"]["2026-10"] == 1 and a["SP"]["2026-11"] == 1))
    casos.append(("o nacional é a soma das UFs", a["BR"]["2026-10"] == 1 and a["BR"]["2026-11"] == 1))
    a2 = agregar_por_uf_semana(
        [{"SG_UF": "32", "SEM_PRI": "10", "CLASSI_FIN": "5"},
         {"SG_UF": "32", "SEM_PRI": "10", "CLASSI_FIN": "10"}],
        2026, "SG_UF", "SEM_PRI", REF, filtro=lambda l: l.get("CLASSI_FIN") != "5")
    casos.append(("o filtro do coletor decide o que conta", a2["ES"]["2026-10"] == 1))
    ruim = agregar_por_uf_semana([{"SG_UF": "", "SEM_PRI": "10"}, {"SG_UF": "32", "SEM_PRI": ""},
                                  {"SG_UF": "32", "SEM_PRI": "99"}], 2026, "SG_UF", "SEM_PRI", REF)
    casos.append(("linha sem UF, sem semana ou com semana impossível não entra", ruim == {}))

    import zipfile as _z
    buf = io.BytesIO()
    with _z.ZipFile(buf, "w") as z:
        z.writestr("D.csv", "SG_UF;SEM_PRI\n32;10\n")
    lidas_zip = list(linhas_do_fluxo(pedacos_do_zip(buf.getvalue())))
    casos.append(("lê o CSV de dentro do zip", lidas_zip == [{"SG_UF": "32", "SEM_PRI": "10"}]))

    j = juntar([{"BR": {"2025-01": 5}}, {"BR": {"2026-01": 7}}])
    casos.append(("anos diferentes se somam sem colidir", j["BR"] == {"2025-01": 5, "2026-01": 7}))

    cache = {"anos": {"2019": {"arquivo": "A.csv"}}}
    casos.append(("mesmo arquivo não é relido", not precisa_reler(cache, 2019, "A.csv")))
    casos.append(("arquivo republicado é relido", precisa_reler(cache, 2019, "B.csv")))
    casos.append(("ano fora do cache é lido", precisa_reler(cache, 2020, "A.csv")))

    ruins = [n for n, ok in casos if not ok]
    for n, ok in casos:
        print(f"  {'OK  ' if ok else 'FALHA'} {n}")
    if ruins:
        print(f"X AUTOTESTE: {len(ruins)} caso(s) reprovado(s).")
        return 1
    print(f"OK AUTOTESTE — {len(casos)} casos, sem rede e sem escrita.")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(autoteste())
