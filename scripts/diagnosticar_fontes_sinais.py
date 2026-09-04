#!/usr/bin/env python3
"""
diagnosticar_fontes_sinais.py
==============================
Ferramenta de UMA VEZ (não faz parte do pipeline regular): descobre os
endpoints REAIS das fontes de sinais de risco que ainda não coletam.

Método (04/09/2026, 2ª versão): a 1ª versão testou URLs adivinhadas e todas
falharam — mas o erro era do método, não das fontes. Monitor de Secas e
Queimadas são aplicativos de página única: qualquer rota devolve o HTML do
app, e a API real está escrita DENTRO dos pacotes JavaScript. Esta versão
baixa o HTML, encontra os scripts, baixa cada script e extrai por expressão
regular todas as URLs e caminhos de API que aparecem no código — depois
testa cada candidato encontrado. Nada é gravado em data/.
"""
import json, re, urllib.parse, urllib.request, urllib.error

UA = {"User-Agent": "Mozilla/5.0 (MonitorElNino/diagnostico)"}

ALVOS = {
    "monitor_secas": "https://monitordesecas.ana.gov.br/",
    "inpe_fogo": "https://terrabrasilis.dpi.inpe.br/queimadas/situacao-atual/",
    "cemaden_alertas": "https://mapainterativo.cemaden.gov.br/",
    "cemaden_alertas_portal": "https://www.gov.br/cemaden/pt-br/assuntos/monitoramento/alertas-vigentes",
    "iri_plume": "https://iri.columbia.edu/our-expertise/climate/forecasts/enso/current/",
}

# Padrões de coisa que parece endpoint de dados dentro de um bundle JS.
RE_URL = re.compile(r'["\'`](https?://[^"\'`\s]{10,200})["\'`]')
RE_PATH = re.compile(r'["\'`((](/(?:api|rest|service|services|data|dados|geoserver|ows|wms|wfs|json)[^"\'`\s)]{0,160})["\'`)]', re.I)
RE_INTERESSE = re.compile(r'api|rest|service|geoserver|\.json|\.csv|wfs|ows|dados|data/', re.I)
RE_RUIDO = re.compile(r'w3\.org|schema\.org|googleapis|gstatic|fonts?\.|jquery|bootstrap|angular\.io|github\.com|license|\.png|\.jpg|\.svg|\.woff|\.css$', re.I)


def baixar(url: str, limite: int = 4_000_000) -> tuple:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read(limite).decode("utf-8", "replace"), r.headers.get("Content-Type", "?"), r.status


def scripts_de(html: str, base: str) -> list:
    achados = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html, re.I)
    achados += re.findall(r'<link[^>]+href=["\']([^"\']+\.js)["\']', html, re.I)
    return [urllib.parse.urljoin(base, s) for s in dict.fromkeys(achados)]


def candidatos_em(texto: str, base: str) -> list:
    out = []
    for u in RE_URL.findall(texto):
        if RE_INTERESSE.search(u) and not RE_RUIDO.search(u):
            out.append(u)
    for p in RE_PATH.findall(texto):
        if not RE_RUIDO.search(p):
            out.append(urllib.parse.urljoin(base, p))
    return list(dict.fromkeys(out))


def testar(url: str) -> str:
    try:
        corpo, ct, status = baixar(url, 400)
        marca = "DADOS" if ("json" in ct or "csv" in ct or corpo.lstrip()[:1] in "[{") else "html/outro"
        return f"HTTP {status} | {ct} | {marca} | {corpo[:160]!r}"
    except urllib.error.HTTPError as e:
        return f"HTTPError {e.code}"
    except Exception as e:  # noqa: BLE001
        return f"{type(e).__name__}: {e}"


def main() -> None:
    relatorio = {}
    for chave, pagina in ALVOS.items():
        print(f"\n{'='*70}\n=== {chave} — {pagina}\n{'='*70}")
        relatorio[chave] = {"pagina": pagina, "scripts": [], "candidatos": {}}
        try:
            html, ct, _ = baixar(pagina)
        except Exception as e:  # noqa: BLE001
            print(f"  !! não consegui abrir a página: {type(e).__name__}: {e}")
            relatorio[chave]["erro"] = str(e)
            continue
        # candidatos já visíveis no próprio HTML
        cands = candidatos_em(html, pagina)
        scripts = scripts_de(html, pagina)
        print(f"  scripts encontrados: {len(scripts)}")
        for s in scripts[:12]:
            print(f"    - {s}")
            relatorio[chave]["scripts"].append(s)
            try:
                js, _, _ = baixar(s)
                cands += candidatos_em(js, pagina)
            except Exception as e:  # noqa: BLE001
                print(f"      (falha ao ler: {type(e).__name__})")
        cands = list(dict.fromkeys(cands))
        print(f"  candidatos a endpoint: {len(cands)}")
        for c in cands[:25]:
            r = testar(c)
            print(f"    {c}\n      -> {r}")
            relatorio[chave]["candidatos"][c] = r
    with open("diagnostico_sinais.json", "w", encoding="utf-8") as f:
        json.dump(relatorio, f, ensure_ascii=False, indent=1)
    print("\n→ diagnostico_sinais.json gravado.")


if __name__ == "__main__":
    main()
