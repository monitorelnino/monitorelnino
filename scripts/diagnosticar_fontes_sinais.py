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
RE_RUIDO = re.compile(r'w3\.org|schema\.org|opengis\.net|googleapis|googletagmanager|googleadservices|adservice\.google|doubleclick|gstatic|youtube|pinterest|facebook|twitter|linkedin|fonts?\.|jquery|bootstrap|angular\.io|github\.com|cloudflare|jsdelivr|vlibras|recaptcha|wp\.com|api\.w\.org|license|\.png|\.jpg|\.svg|\.woff|\.css$', re.I)


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


# Sondagens dirigidas, a partir do que a 2ª rodada já provou existir.
# 04/09/2026 (v4): três achados firmes da v3 orientam esta rodada —
#  (a) ANA: API é apimsbr.ana.gov.br/rpc/v1/<recurso> (change_maps e disclaimer confirmados);
#      os arquivos ficam no bucket ana-monitor-secas-files.s3.sa-east-1.amazonaws.com/data/...
#  (b) CEMADEN: GeoServer em gsc.cemaden.gov.br (responde WMS) + WebService MapaInterativoWS;
#  (c) INPE: os dados não estão no JS da página — o exportador monta a URL do portal de
#      dados abertos, então sondamos diretamente os caminhos publicados do Programa Queimadas.
ALVO_EXTRA_JS = {
    "inpe_exportador": "https://terrabrasilis.dpi.inpe.br/queimadas/situacao-atual/assets-sa/js/situacao_atual/exportador_csv_situacao_atual.js",
    "inpe_boot": "https://terrabrasilis.dpi.inpe.br/queimadas/situacao-atual/assets-sa/js/situacao_atual/boot.js",
    "inpe_loader": "https://terrabrasilis.dpi.inpe.br/queimadas/situacao-atual/components-sa/loader.js",
    "iri_enso": "https://iri.columbia.edu/wp-content/themes/iri/assets/js/enso_forecast.js?ver=7.1",
}

SONDAS = {
    "monitor_secas_rpc": [f"https://apimsbr.ana.gov.br/rpc/v1/{r}" for r in
        ("mapa", "mapas", "map", "monitor", "shapefile", "shapefiles", "municipios", "municipio",
         "categorias", "dados_tabulares", "dados-tabulares", "tabular", "tabulares", "planilha",
         "ultimo_mapa", "ultimo-mapa", "last_map", "arquivos", "files", "sig", "dados_sig",
         "publicacoes", "calendario", "change_maps", "disclaimer")],
    "monitor_secas_raiz": ["https://apimsbr.ana.gov.br/rpc/v1/", "https://apimsbr.ana.gov.br/rpc/",
                            "https://apimsbr.ana.gov.br/rest/", "https://apimsbr.ana.gov.br/api/"],
    "ana_s3": ["https://ana-monitor-secas-files.s3.sa-east-1.amazonaws.com/?list-type=2&prefix=data/&max-keys=60",
               "https://ana-monitor-secas-files.s3.sa-east-1.amazonaws.com/?list-type=2&prefix=data/shapefile&max-keys=40",
               "https://ana-monitor-secas-files.s3.sa-east-1.amazonaws.com/?list-type=2&prefix=data/spreadsheet&max-keys=40"],
    "cemaden_ws": ["https://mapservices.cemaden.gov.br/MapaInterativoWS/resources/layer/",
                    "https://mapainterativo.cemaden.gov.br/MapaInterativoWS/resources/layer/",
                    "https://gsc.cemaden.gov.br/geoserver/ows?service=WFS&version=2.0.0&request=GetCapabilities",
                    "https://gsc.cemaden.gov.br/geoserver/cemaden_dev/ows?service=WFS&version=2.0.0&request=GetCapabilities",
                    "https://gsc.cemaden.gov.br/geoserver/cemaden_dev/wms?service=WMS&version=1.3.0&request=GetCapabilities"],
    "inpe_portal": ["https://terrabrasilis.dpi.inpe.br/queimadas/situacao-atual/estatisticas/estatisticas_estados/",
                     "https://terrabrasilis.dpi.inpe.br/queimadas/situacao-atual/media/focos/focos_abertos_24h_Brasil.csv",
                     "https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/diario/Brasil/",
                     "https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/24h/",
                     "https://terrabrasilis.dpi.inpe.br/queimadas/situacao-atual/estatisticas/estatisticas_estados/dados.json"],
    "cemaden_geoserver": ["https://mapainterativo.cemaden.gov.br/geoserver/web/",
        "https://mapainterativo.cemaden.gov.br/geoserver/ows?service=WFS&version=1.0.0&request=GetCapabilities",
        "http://www2.cemaden.gov.br/geoserver/ows?service=WFS&version=1.0.0&request=GetCapabilities",
        "https://mapainterativo.cemaden.gov.br/resources/alertas.json"],
}


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
        # 04/09/2026 (2ª correção): prioriza scripts do PRÓPRIO domínio da fonte e lê todos.
        # O corte em 12 e a mistura com Google/jQuery/YouTube escondiam justamente os
        # arquivos que carregam os dados (exportador_csv_situacao_atual.js, enso_forecast.js).
        host = urllib.parse.urlparse(pagina).netloc
        proprios = [u for u in scripts if urllib.parse.urlparse(u).netloc == host]
        terceiros = [u for u in scripts if urllib.parse.urlparse(u).netloc != host]
        scripts = proprios + terceiros
        print(f"  scripts encontrados: {len(scripts)} ({len(proprios)} do próprio domínio)")
        for s in scripts:
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
    print(f"\n{'='*70}\n=== SCRIPTS-CHAVE (leitura direta e extração de URLs)\n{'='*70}")
    relatorio["_scripts_chave"] = {}
    for nome, url in ALVO_EXTRA_JS.items():
        print(f"\n-- {nome}: {url}")
        try:
            js, _, _ = baixar(url)
        except Exception as e:  # noqa: BLE001
            print(f"   !! {type(e).__name__}: {e}"); continue
        achados = candidatos_em(js, url)
        # também qualquer coisa que pareça caminho de arquivo de dados
        achados += [m for m in re.findall(r'["\'`]([^"\'`\s]{4,160}\.(?:csv|json|geojson|zip|txt))["\'`]', js)]
        achados = list(dict.fromkeys(achados))
        print(f"   {len(achados)} candidato(s)")
        relatorio["_scripts_chave"][nome] = {}
        for c in achados[:20]:
            u = c if c.startswith("http") else urllib.parse.urljoin(url, c)
            r = testar(u)
            print(f"   {u}\n     -> {r}")
            relatorio["_scripts_chave"][nome][u] = r

    print(f"\n{'='*70}\n=== SONDAGENS DIRIGIDAS\n{'='*70}")
    relatorio["_sondas"] = {}
    for grupo, urls in SONDAS.items():
        print(f"\n-- {grupo}")
        for u in urls:
            r = testar(u)
            if "HTTPError 404" not in r:   # só o que não é 404 interessa
                print(f"  {u}\n    -> {r}")
            relatorio["_sondas"][u] = r
    with open("diagnostico_sinais.json", "w", encoding="utf-8") as f:
        json.dump(relatorio, f, ensure_ascii=False, indent=1)
    print("\n→ diagnostico_sinais.json gravado.")


if __name__ == "__main__":
    main()
