#!/usr/bin/env python3
"""Sonda: onde está, em dado aberto, a tabela de probabilidades ENSO por trimestre (La Niña/Neutro/El Niño).

07/09/2026 — versão inicial: testa candidatos e imprime status/tipo/amostra.
22/09/2026 — o endpoint tabular do IRI (`~forecast/ensofcst/Data/ensofcst_ONI`) responde
  HTTP 404 desde pelo menos 15/09/2026, nas três variantes conhecidas, enquanto as páginas
  públicas do IRI respondem 200. Ou seja: a FONTE está viva e o ARQUIVO é que saiu do ar.
  A sonda antiga não conseguia dizer isso porque só procurava o padrão "El Niño … N%" —
  e a tabela do Quick Look não tem esse formato; ela tem uma linha por trimestre, no
  formato `RÓTULO nina neutro nino` (ex.: `MJJ 5 92 3`), que é exatamente o que
  `parse_plume_iri()` em coletar_sinais_risco.py já sabe ler.

  Esta versão, então, procura a TABELA e não o percentual solto, e imprime o trecho em volta
  do primeiro acerto, para que um parser possa ser escrito a partir de HTML real — e não de
  suposição. Enquanto não houver esse HTML real preservado, o endpoint do coletor NÃO muda:
  a fonte segue como lacuna declarada no site, que é o comportamento correto.

Uso:
  python3 scripts/sondar_enso_probabilidades.py              # sonda a rede (só em ambiente com rede aberta)
  python3 scripts/sondar_enso_probabilidades.py --autoteste  # testa só o extrator, sem rede
"""
import re
import sys
import urllib.error
import urllib.request

UA = {"User-Agent": "MonitorElNino/3.1 (sonda ENSO)"}

CANDIDATOS = [
    # Arquivos tabulares historicamente usados (404 em 15/09/2026 e 22/09/2026).
    "https://iri.columbia.edu/~forecast/ensofcst/Data/ensofcst_ONI",
    "https://iri.columbia.edu/~forecast/ensofcst/Data/ensofcst_ALLto",
    "https://iri.columbia.edu/~forecast/ensofcst/Data/ensofcst_ONI_v3",
    # Páginas públicas do IRI (200 em 15/09/2026) — a tabela do plume deve estar aqui.
    "https://iri.columbia.edu/climate/ENSO/currentinfo/QuickLook.html",
    "https://iri.columbia.edu/climate/ENSO/currentinfo/SST_table.html",
    "https://iri.columbia.edu/our-expertise/climate/forecasts/enso/current/",
    # CPC/NOAA — a previsão oficial, que é fonte distinta da do plume objetivo do IRI.
    "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/ensodisc.shtml",
    "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/enso-probabilities.txt",
    "https://www.cpc.ncep.noaa.gov/products/CFSv2/CFSv2_body.html",
    "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/figure1.png",
]

# Rótulos de trimestre corridos usados pelo IRI/CPC (JFM, FMA, …). Só estes contam como
# linha de tabela: evita casar siglas soltas do HTML (DIV, IMG, PDF, GMT…) com três números
# quaisquer da página.
TRIMESTRES = {
    "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA",
    "JAS", "ASO", "SON", "OND", "NDJ", "DJF",
}


def texto_de_html(bruto: str) -> str:
    """Remove script/style e marcação, devolvendo texto corrido com os espaços normalizados por linha."""
    sem_script = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", bruto)
    # Fecha-linha nos elementos que quebram linha visualmente, para a tabela não virar um blocão.
    com_quebras = re.sub(r"(?i)</(tr|p|div|li|h[1-6]|table|br)\s*>|<br\s*/?>", "\n", sem_script)
    # Toda tag vira UM ESPAÇO, nunca string vazia: sem isso <td>MJJ</td><td>5</td>
    # colaria em "MJJ5" e a tabela inteira se perderia. É o caso negativo 1 do autoteste.
    sem_tags = re.sub(r"(?s)<[^>]+>", " ", com_quebras)
    sem_entidades = (
        sem_tags.replace("&nbsp;", " ").replace("&amp;", "&")
        .replace("&lt;", "<").replace("&gt;", ">").replace("&#8211;", "-")
    )
    return "\n".join(re.sub(r"[ \t\xa0]+", " ", l).strip() for l in sem_entidades.splitlines())


def linhas_plume_de_texto(texto: str) -> list:
    """Extrai [{'trimestre','la_nina','neutro','el_nino'}] das linhas `RÓTULO nina neutro nino`.

    Mesmo contrato de parse_plume_iri() em coletar_sinais_risco.py, com duas diferenças:
    só aceita rótulo de trimestre real (não qualquer trigrama maiúsculo) e exige que os três
    números somem perto de 100 — que é o que distingue uma linha de probabilidade de uma
    linha de números quaisquer alinhados numa página.
    """
    saida = []
    for linha in texto.splitlines():
        partes = linha.split()
        if len(partes) < 4:
            continue
        if partes[0].upper() not in TRIMESTRES:
            continue
        try:
            nina, neutro, nino = (float(p.rstrip("%")) for p in partes[1:4])
        except ValueError:
            continue
        if not all(0 <= v <= 100 for v in (nina, neutro, nino)):
            continue
        if not 97 <= nina + neutro + nino <= 103:
            continue
        saida.append(
            {"trimestre": partes[0].upper(), "la_nina": nina, "neutro": neutro, "el_nino": nino}
        )
    return saida


def _trecho_em_volta(texto: str, achados: list) -> str:
    """Devolve o pedaço do texto em volta do primeiro trimestre achado, para inspeção humana."""
    if not achados:
        return ""
    pos = texto.find(achados[0]["trimestre"])
    if pos < 0:
        return ""
    return texto[max(0, pos - 220): pos + 420].replace("\n", " ⏎ ")


def autoteste() -> int:
    """Testa o extrator sem rede. Inclui o caso negativo que a sonda antiga não pegava."""
    falhas = []

    def checar(nome, condicao):
        print(("  ✓ " if condicao else "  ✗ ") + nome)
        if not condicao:
            falhas.append(nome)

    # 1. Tabela em HTML de verdade (marcação de tabela, como a do Quick Look).
    html = (
        "<html><body><h2>IRI ENSO Forecast</h2><table>"
        "<tr><th>Season</th><th>La Ni&ntilde;a</th><th>Neutral</th><th>El Ni&ntilde;o</th></tr>"
        "<tr><td>MJJ</td><td>5</td><td>92</td><td>3</td></tr>"
        "<tr><td>JJA</td><td>16</td><td>73</td><td>11</td></tr>"
        "<tr><td>JAS</td><td>24</td><td>62</td><td>14</td></tr>"
        "</table></body></html>"
    )
    achados = linhas_plume_de_texto(texto_de_html(html))
    checar("tabela HTML: 3 trimestres extraídos", len(achados) == 3)
    checar(
        "tabela HTML: primeiro trimestre correto",
        achados[:1] == [{"trimestre": "MJJ", "la_nina": 5.0, "neutro": 92.0, "el_nino": 3.0}],
    )

    # 2. Texto corrido (caso o arquivo tabular volte a existir).
    achados_txt = linhas_plume_de_texto("MJJ 5 92 3\nJJA 16 73 11\ncomentário solto\n")
    checar("texto corrido: 2 trimestres extraídos", len(achados_txt) == 2)

    # 3. NEGATIVO — a página respondia 200 e a sonda antiga dizia 'percentuais vistos: []',
    #    o que era indistinguível de uma página sem os dados. Sem separador de célula,
    #    <td>MJJ</td><td>5</td> vira 'MJJ5' e nada é extraído: este caso tem que achar 0
    #    numa página realmente sem tabela, e não 0 por falha de limpeza.
    sem_tabela = "<html><body><p>The plume is updated monthly. See the PDF for details.</p></body></html>"
    checar("página sem tabela: nada extraído", linhas_plume_de_texto(texto_de_html(sem_tabela)) == [])

    # 4. NEGATIVO — trigrama maiúsculo que não é trimestre, seguido de números.
    checar("sigla que não é trimestre é ignorada", linhas_plume_de_texto("PDF 10 20 70\n") == [])

    # 5. NEGATIVO — três números que não somam ~100 não são probabilidades.
    checar("linha que não soma ~100 é ignorada", linhas_plume_de_texto("MJJ 10 20 30\n") == [])

    # 6. NEGATIVO — valor fora de 0–100.
    checar("valor fora de 0–100 é ignorado", linhas_plume_de_texto("MJJ 120 -30 10\n") == [])

    if falhas:
        print(f"✗ AUTOTESTE DA SONDA: {len(falhas)} caso(s) falharam")
        return 1
    print("✓ AUTOTESTE OK — extrator do plume lê tabela HTML e texto corrido, e rejeita o que não é probabilidade")
    return 0


def sondar() -> int:
    for u in CANDIDATOS:
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40) as r:
                corpo = r.read(400000)
                ct = r.headers.get("Content-Type", "")
                txt = corpo.decode("utf-8", "replace") if "image" not in ct else ""
                limpo = texto_de_html(txt) if "html" in ct.lower() else txt
                achados = linhas_plume_de_texto(limpo)
                percentuais = re.findall(r"(?:El Ni[nñ]o|La Ni[nñ]a|Neutral)[^\n]{0,40}?(\d{1,3})\s*%", txt)[:6]
                print(
                    f"OK  {u} | {r.status} {ct[:30]} | {len(corpo)} bytes | "
                    f"trimestres na tabela: {len(achados)} | percentuais soltos: {percentuais}"
                )
                if achados:
                    print(f"    TABELA ACHADA → {achados[:4]}")
                    print(f"    contexto: {_trecho_em_volta(limpo, achados)!r}")
                else:
                    print(f"    amostra: {limpo[:160].replace(chr(10), ' ')!r}")
        except urllib.error.HTTPError as e:
            print(f"ERR {u} | HTTP {e.code}")
        except Exception as e:
            print(f"ERR {u} | {type(e).__name__}: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(autoteste() if "--autoteste" in sys.argv else sondar())
