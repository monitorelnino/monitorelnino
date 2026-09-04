#!/usr/bin/env python3
"""
diagnosticar_fontes_sinais.py
==============================
Ferramenta de UMA VEZ (não faz parte do pipeline regular): testa, com rede
real, os endpoints candidatos das cinco fontes de sinais de risco que nunca
coletaram (monitor_secas, inpe_fogo, cemaden_alertas, iri_plume) e imprime
status HTTP, content-type e os primeiros bytes de cada resposta — só isso,
sem gravar dados. O sandbox de desenvolvimento não alcança esses domínios;
esta rodada roda dentro do Actions, que tem rede real, para diagnosticar
com evidência em vez de suposição (04/09/2026).
"""
import json, urllib.request, urllib.error

CANDIDATOS = {
    "monitor_secas": [
        "https://monitordesecas.ana.gov.br/api/mapa",
        "https://monitordesecas.ana.gov.br/api/dados-tabulares",
        "https://monitordesecas.ana.gov.br/api/mapa-mais-recente",
        "https://dadosabertos.ana.gov.br/api/3/action/package_search?q=monitor+de+secas&rows=5",
    ],
    "inpe_fogo": [
        "https://terrabrasilis.dpi.inpe.br/queimadas/situacao-atual/media/focos/focos_abertos_24h_brasil.csv",
        "https://data.inpe.br/queimadas/dados-abertos/",
        "https://terrabrasilis.dpi.inpe.br/queimadas/situacao-atual/situacao_atual/",
        "https://terrabrasilis.dpi.inpe.br/queimadas/api/focos/24h",
    ],
    "cemaden_alertas": [
        "http://www2.cemaden.gov.br/mapainterativo/alertas/alertas.json",
        "https://www2.cemaden.gov.br/mapainterativo/alertas/alertas.json",
        "https://mapainterativo.cemaden.gov.br/api/alertas",
    ],
    "iri_plume": [
        "https://iri.columbia.edu/~forecast/ensofcst/Data/ensofcst_ONI",
        "https://iri.columbia.edu/~forecast/ensofcst/Data/",
        "https://iri.columbia.edu/~forecast/ensofcst/Data/archive/ensofcst_cpc_ALL_KMASNU",
    ],
}


def testar(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (MonitorElNino/diagnostico)"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            corpo = r.read(300)
            return f"HTTP {r.status} | {r.headers.get('Content-Type','?')} | {len(corpo)}+ bytes | {corpo[:200]!r}"
    except urllib.error.HTTPError as e:
        return f"HTTPError {e.code} | {e.reason}"
    except Exception as e:  # noqa: BLE001
        return f"{type(e).__name__}: {e}"


def main() -> None:
    saida = {}
    for chave, urls in CANDIDATOS.items():
        print(f"\n=== {chave} ===")
        saida[chave] = []
        for u in urls:
            r = testar(u)
            print(f"  {u}\n    -> {r}")
            saida[chave].append({"url": u, "resultado": r})
    with open("diagnostico_sinais.json", "w", encoding="utf-8") as f:
        json.dump(saida, f, ensure_ascii=False, indent=1)
    print("\n→ diagnostico_sinais.json gravado (não versionado; só para o relatório do robô).")


if __name__ == "__main__":
    main()
