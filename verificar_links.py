#!/usr/bin/env python3
"""
verificar_links.py
=====================
Verifica TODOS os links externos do Monitor El Niño Brasil: os embutidos na
marcação (rodapé de fontes, hub de acompanhamento, guias de proteja-se.html
etc.) e os que vivem em data/municipios.json (url por município/capital).

Para cada link, faz uma requisição HTTP e classifica:
  OK           — resposta 200-299
  REDIRECIONA  — 300-399 (registra o destino final)
  QUEBRADO     — 400-599 ou erro de conexão/timeout
  (link nunca é removido automaticamente — só reportado; a regra de ouro
   continua exigindo decisão humana sobre o que fazer com um link quebrado)

LIMITAÇÃO DE AMBIENTE (mesma de todo o resto do pipeline): o sandbox de edição
tem rede restrita a um allowlist de pacotes; a maioria dos domínios aqui
verificados (.gov.br, prefeituras, imprensa) não está nele. A LÓGICA de
extração e classificação é testada com --self-test (fixture local, sem rede);
a verificação de verdade roda no ambiente real (Action do GitHub com job
próprio, ou a máquina de quem publica).

Uso:
  python3 verificar_links.py                    # verifica tudo (marcação + banco)
  python3 verificar_links.py --so-marcacao       # só os links embutidos no HTML
  python3 verificar_links.py --so-banco          # só as urls de municipios.json
  python3 verificar_links.py --self-test         # testa a lógica sem rede
"""
import argparse
import concurrent.futures
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).parent
DATA = RAIZ / "data"
ARQUIVOS_HTML = ["index.html", "mapas-e-graficos.html", "proteja-se.html", "envie-dados.html", "obrigado.html", "para-gestores.html"]


def extrair_links_marcacao():
    """Devolve {url: [(arquivo, contexto)]} para todo href="http..." nas 4 páginas."""
    achados = {}
    for nome in ARQUIVOS_HTML:
        p = RAIZ / nome
        if not p.exists():
            continue
        html = p.read_text(encoding="utf-8")
        for m in re.finditer(r'href="(https?://[^"]+)"', html):
            url = m.group(1)
            # contexto: os ~50 caracteres de texto de link mais próximos (heurística simples)
            depois = html[m.end():m.end() + 120]
            texto = re.search(r">([^<]{1,60})<", depois)
            contexto = texto.group(1).strip() if texto else "(sem texto de link identificado)"
            achados.setdefault(url, []).append((nome, contexto))
    return achados


def extrair_links_js_e_estados():
    """URLs que não estão em href= mas o usuário recebe do mesmo jeito: constantes JS de
    index.html (PORTAIS_UF, DOM_LINKS, GUIAS, os link() do PDF do cidadão) e as urls dos
    instrumentos estaduais em data/estados.json. Ampliação de 31/08/2026: Patricia
    perguntou se todos os links do site estavam conferidos — estes não estavam no escopo."""
    achados = {}
    html = (RAIZ / "index.html").read_text(encoding="utf-8")
    scripts = " ".join(re.findall(r"<script>([\s\S]*?)</script>", html))
    for m in re.finditer(r"'(https?://[^'\s]+)'", scripts):
        achados.setdefault(m.group(1), []).append(("index.html (JS: portais/diários/guias/PDF)", ""))
    est = json.load(open(DATA / "estados.json", encoding="utf-8"))
    for u in est.get("ufs", []):
        for campo in ("url", "doc_url", "fonte_url"):
            v = u.get(campo)
            if v and v.startswith("http"):
                achados.setdefault(v, []).append((f"estados.json ({u['uf']})", u.get("doc", "")))
    return achados


def extrair_links_banco():
    """Devolve {url: [(municipio, uf)]} para todo campo 'url' não nulo em municipios.json."""
    achados = {}
    municipios = json.load(open(DATA / "municipios.json", encoding="utf-8"))
    for m in municipios:
        if m.get("url"):
            achados.setdefault(m["url"], []).append((m["nome"], m["uf"]))
    return achados


def classificar_status(codigo: int) -> str:
    """Classifica o código de resposta HTTP em OK, REDIRECIONA ou QUEBRADO, conforme as faixas declaradas no docstring do módulo."""
    if 200 <= codigo < 300:
        return "OK"
    if 300 <= codigo < 400:
        return "REDIRECIONA"
    return "QUEBRADO"


def verificar_um(url: str, timeout=15):
    """Faz a requisição real. Isolado nesta função para poder ser substituído
    por uma versão-fixture em --self-test."""
    import requests
    try:
        resp = requests.head(url, timeout=timeout, allow_redirects=True,
                              headers={"User-Agent": "MonitorElNinoBrasil/1.0 (Futura Evidence Lab; verificacao-de-links)"})
        if resp.status_code == 405:  # alguns servidores recusam HEAD; tenta GET
            resp = requests.get(url, timeout=timeout, allow_redirects=True,
                                 headers={"User-Agent": "MonitorElNinoBrasil/1.0"})
        return classificar_status(resp.status_code), resp.status_code, resp.url
    except Exception as e:
        return "QUEBRADO", None, str(e)


def rodar_verificacao(links: dict, workers=8):
    """Executa as requisições HTTP em paralelo (concurrent.futures) para a lista de links informada e coleta o status de cada uma."""
    resultados = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        futuros = {ex.submit(verificar_um, url): url for url in links}
        for fut in concurrent.futures.as_completed(futuros):
            url = futuros[fut]
            resultados[url] = fut.result()
    return resultados


def relatorio(links: dict, resultados: dict, titulo: str):
    """Formata os resultados da verificação em relatório de terminal, agrupado por status."""
    linhas = [f"\n=== {titulo} ({len(links)} link(s) únicos) ==="]
    contagem = {"OK": 0, "REDIRECIONA": 0, "QUEBRADO": 0}
    quebrados = []
    codigos_quebrados = []
    for url, onde in sorted(links.items()):
        status, codigo, destino = resultados[url]
        contagem[status] += 1
        marca = {"OK": "✓", "REDIRECIONA": "↪", "QUEBRADO": "✗"}[status]
        linhas.append(f"  {marca} [{status}{' '+str(codigo) if codigo else ''}] {url}")
        if status == "REDIRECIONA" and destino != url:
            linhas.append(f"      → {destino}")
        if status == "QUEBRADO":
            linhas.append(f"      erro: {destino}")
            quebrados.append((url, onde))
            codigos_quebrados.append(codigo)
        for arq, ctx in onde[:2]:
            linhas.append(f"      usado em: {arq} ({ctx})")
    linhas.append(f"\n  Resumo: {contagem['OK']} OK · {contagem['REDIRECIONA']} redirecionam · {contagem['QUEBRADO']} quebrados")

    # Salvaguarda: bloqueio de rede/proxy parece com "tudo quebrado", mas não é.
    # Domínios completamente diferentes falhando pelo MESMO código sugere bloqueio
    # de saída (como o allowlist do sandbox de edição), não 82 links realmente mortos.
    dominios_unicos = len({re.match(r"https?://([^/]+)", u).group(1) for u in links})
    if len(quebrados) >= 5 and dominios_unicos >= 5:
        so_um_codigo = len(set(c for c in codigos_quebrados if c)) <= 1 and codigos_quebrados
        taxa = len(quebrados) / max(len(links), 1)
        if so_um_codigo and taxa > 0.7:
            linhas.append(f"\n  [ATENÇÃO] {len(quebrados)}/{len(links)} links falharam com o MESMO código "
                          f"({codigos_quebrados[0]}), em {dominios_unicos} domínios totalmente diferentes.")
            linhas.append("  Isto tem a assinatura de um BLOQUEIO DE REDE/PROXY (ex.: o allowlist do sandbox de")
            linhas.append("  edição, que não libera a maioria destes domínios), não de 82 documentos removidos ")
            linhas.append("  de verdade. Rode este script no ambiente real (Action do GitHub ou máquina de quem")
            linhas.append("  publica, com internet irrestrita) antes de tratar qualquer um destes como quebrado.")
    return "\n".join(linhas), quebrados


def self_test():
    """Testa a lógica de extração e classificação contra uma fixture local, sem depender de rede (ver limitação de ambiente no docstring do módulo)."""
    print("=== Teste de extração (sem rede) ===")
    html_fixture = '''<a href="https://exemplo.gov.br/pagina">Ver fonte oficial</a>
    <a href="https://exemplo.gov.br/pagina">link duplicado, mesma url</a>
    <a href="https://outro.org/doc.pdf">Outro documento</a>'''
    achados = {}
    for m in re.finditer(r'href="(https?://[^"]+)"', html_fixture):
        achados.setdefault(m.group(1), []).append(("fixture.html", "teste"))
    ok1 = len(achados) == 2 and len(achados["https://exemplo.gov.br/pagina"]) == 2
    print(f"  {'✓' if ok1 else '✗'} deduplica URLs repetidas, mantém as duas ocorrências ({len(achados)} únicas)")

    print("\n=== Teste de classificação de status ===")
    casos = [(200, "OK"), (204, "OK"), (301, "REDIRECIONA"), (302, "REDIRECIONA"),
             (404, "QUEBRADO"), (500, "QUEBRADO"), (403, "QUEBRADO")]
    falhas = 0
    for codigo, esperado in casos:
        obtido = classificar_status(codigo)
        ok = obtido == esperado
        falhas += not ok
        print(f"  {'✓' if ok else '✗'} {codigo} → {obtido}" + ("" if ok else f" (esperado {esperado})"))

    print("\n=== Teste do banco: extrai url de municipios.json real ===")
    links_banco = extrair_links_banco()
    ok2 = len(links_banco) >= 3  # pelo menos as 3 capitais recém-verificadas + Recife
    print(f"  {'✓' if ok2 else '✗'} extraiu {len(links_banco)} url(s) únicas do banco real")
    falhas += not (ok1 and ok2)

    print(f"\n{'✓ TODOS OS TESTES PASSARAM' if not falhas else f'✗ {falhas} teste(s) falharam'}")
    return 1 if falhas else 0


def main():
    """Interface de linha de comando: escolhe o escopo (marcação, banco ou ambos) e despacha para rodar_verificacao ou self_test."""
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--so-marcacao", action="store_true")
    ap.add_argument("--so-banco", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    todos_quebrados = []
    if not args.so_banco:
        links = extrair_links_marcacao()
        print(f"Verificando {len(links)} link(s) únicos da marcação (pode levar alguns minutos)...")
        try:
            res = rodar_verificacao(links)
            texto, quebrados = relatorio(links, res, "Links na marcação (HTML das 5 páginas)")
            print(texto)
            todos_quebrados += quebrados
        except Exception as e:
            print(f"[FALHA] não foi possível verificar a rede: {e}")
            print("(esperado no sandbox de edição — allowlist não cobre a maioria destes domínios;")
            print(" roda de verdade na Action do GitHub ou na máquina de quem publica)")

    if not args.so_banco:
        links = extrair_links_js_e_estados()
        print(f"\nVerificando {len(links)} url(s) de constantes JS e de estados.json...")
        try:
            res = rodar_verificacao(links)
            texto, quebrados = relatorio(links, res, "URLs em JS (portais, diários, guias, PDF) e estados.json")
            print(texto)
            todos_quebrados += quebrados
        except Exception as e:
            print(f"[FALHA] não foi possível verificar a rede: {e}")

    if not args.so_marcacao:
        links = extrair_links_banco()
        print(f"\nVerificando {len(links)} url(s) únicas de data/municipios.json...")
        try:
            res = rodar_verificacao(links)
            texto, quebrados = relatorio(links, res, "URLs em municipios.json (documentos municipais)")
            print(texto)
            todos_quebrados += quebrados
        except Exception as e:
            print(f"[FALHA] não foi possível verificar a rede: {e}")

    if todos_quebrados:
        print(f"\n[ATENÇÃO] {len(todos_quebrados)} link(s) quebrado(s) — decisão humana necessária "
              "(remover, substituir por link novo, ou manter nomeado sem link).")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
