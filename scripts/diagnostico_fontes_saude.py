#!/usr/bin/env python3
"""
scripts/diagnostico_fontes_saude.py — por que os coletores estaduais de saúde não coletam no runner
===================================================================================================
Criado em 11/09/2026, depois da primeira rodada real com os quatro coletores (MS, DF, PE, PB): todos
declararam lacuna, nenhum baixou. Do sandbox de edição e de um navegador no Brasil os mesmos documentos
abrem; do runner, não. Hipótese a testar: os portais estaduais recusam o IP do runner (GitHub/Azure, fora
do Brasil) ou o User-Agent do Monitor.

Este script NÃO coleta e NÃO grava dado nenhum no site. Só mede e imprime, para o relatório da execução:
código HTTP, tamanho, tipo de conteúdo e primeiros bytes do corpo de cada fonte, com dois User-Agents
(o do Monitor e um de navegador) — isolando "é o IP" de "é o UA".

  python3 scripts/diagnostico_fontes_saude.py
"""
import json, socket, ssl, sys, time, urllib.error, urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from coletores_base import ua_de  # o cliente do projeto, com propósito declarado (§228)

# §228 (26/09/2026): havia aqui um `UA_NAVEGADOR` — Chrome completo no Windows — e o laço de
# medição pedia cada alvo DUAS vezes, uma com o cliente do Monitor e outra com o do navegador,
# "para separar bloqueio por IP de bloqueio por UA". A intenção de diagnóstico é boa; o meio
# não é: enviar identidade falsa a um sítio público é o que o CLAUDE.md proíbe sem exceção.
#
# E a resposta que a comparação daria não mudaria nada. Diante de bloqueio por agente, a
# conduta do projeto é a mesma que diante de bloqueio por IP: respeitar e declarar a lacuna.
# Saber que o sítio entregaria o documento a um navegador só serviria para tentar passar por
# um — que é justamente o que não se faz aqui. A sonda mede com o cliente do Monitor, que é o
# cliente que vai coletar, e o que ela mede é o que a coleta vai encontrar.

ALVOS = [
    ("MS · listagem de boletins", "https://www.saude.ms.gov.br/informativos/boletins/"),
    ("DF · listagem de informes", "https://www.saude.df.gov.br/informes-dengue-chikungunya-zika-febre-amarela"),
    ("PE · listagem CIEVS", "https://portalcievs.saude.pe.gov.br/noticias/INFORMES/arbovirose"),
    ("PE · PDF do informe (SE 34)", "https://portalcievs.saude.pe.gov.br/docs/Informe%20Epidemiolo%CC%81gico%20Arboviroses_SE%2001%20a%2034_2026.pdf"),
    ("PB · boletim nº 03/2026", "https://paraiba.pb.gov.br/diretas/saude/arquivos-1/vigilancia-em-saude/boletim-epidemiologico-arboviroses-urbanas-no-03_2026.pdf"),
    ("SP · portal CVE (controle)", "https://portal.saude.sp.gov.br/"),
    # 11/09/2026: a figura "SRAG por semana · Brasil" está sem gráfico no site porque
    # data/saude_desfechos/srag_serie.json nunca foi criado — coletar_srag_gripe.py registra URLError
    # desde 09/09. Verificado em navegador no Brasil: gitlab.procc.fiocruz.br dá ERR_CONNECTION_TIMED_OUT.
    # Medir aqui separa "servidor fora do ar" de "migrou de endereço": o InfoGripe aparece agora também em
    # gitlab.fiocruz.br/marcelo.gomes/infogripe, mas esse host pede login (não serve para coleta anônima).
    ("InfoGripe · CSV canônico (host antigo)", "https://gitlab.procc.fiocruz.br/mave/repo/-/raw/master/Dados/InfoGripe/serie_temporal_com_estimativas_recentes.csv"),
    ("InfoGripe · host antigo, raiz", "https://gitlab.procc.fiocruz.br/"),
    ("InfoGripe · host novo, raiz", "https://gitlab.fiocruz.br/"),
    ("InfoGripe · host novo, CSV equivalente", "https://gitlab.fiocruz.br/marcelo.gomes/infogripe/-/raw/master/Dados/InfoGripe/serie_temporal_com_estimativas_recentes.csv"),
    ("controle: fonte que já funciona", "https://queridodiario.ok.org.br/"),
    # 12/09/2026: hipótese a testar — web.archive.org é um CDN global; se o runner o alcançar mesmo sem
    # alcançar saude.df.gov.br diretamente, dá pra usar o Wayback como intermediário: o próprio archive.org
    # busca o site (de onde ele conseguir) e devolve a cópia arquivada, sem o runner precisar falar com a
    # fonte original.
    ("web.archive.org (candidato a intermediário para o DF)", "https://web.archive.org/web/2/https://www.saude.df.gov.br/informes-dengue-chikungunya-zika-febre-amarela"),
    # 07/11/2026: síndrome gripal (SG). O e-SUS Notifica recusa as duas rotas do portal (§80) e o conjunto
    # anual para em 2024. Onde mais o Ministério publica a SG, aberto e por máquina? Medir antes de decidir:
    # o catálogo CKAN (há conjunto de 2025/2026 com outro nome?), o conjunto do e-SUS 2024 (a recusa é do
    # objeto no S3 ou do host?), o Painel Coronavírus e o painel público do InfoGripe.
    ("SG · CKAN package_search q=gripal", "https://dadosabertos.saude.gov.br/api/3/action/package_search?q=gripal&rows=50"),
    ("SG · CKAN package_search q=notifica", "https://dadosabertos.saude.gov.br/api/3/action/package_search?q=notifica&rows=50"),
    ("SG · CKAN package_search q=covid", "https://dadosabertos.saude.gov.br/api/3/action/package_search?q=covid&rows=50"),
    ("SG · S3 raiz do CKAN (o host responde?)", "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/"),
    ("SG · S3 CSV 2024 AC lote 1 (a recusa é do objeto?)", "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SGL/2024/uf=AC/lote=1/part-00000.csv"),
    ("SG · Painel Coronavírus (raiz)", "https://covid.saude.gov.br/"),
    ("SG · InfoGripe painel público", "https://info.gripe.fiocruz.br/"),
    ("SG · InfoGripe dados do painel (candidato)", "https://info.gripe.fiocruz.br/api/"),
    ("SG · CVE-SP boletins de síndromes gripais (listagem)", "https://www.saude.sp.gov.br/cve-centro-de-vigilancia-epidemiologica-prof.-alexandre-vranjac/areas-de-vigilancia/doencas-de-transmissao-respiratoria/influenza/boletins"),
]


def medir(url: str, ua: str, timeout: int = 45) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept": "*/*"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            corpo = r.read(400)
            return {"status": r.status, "ms": int((time.time() - t0) * 1000), "bytes_lidos": len(corpo),
                    "tipo": r.headers.get("Content-Type", "")[:60], "servidor": r.headers.get("Server", "")[:40],
                    "inicio": corpo[:120].decode("utf-8", "replace").replace("\n", " ")}
    except urllib.error.HTTPError as e:
        corpo = b""
        try:
            corpo = e.read(400)
        except Exception:  # noqa: BLE001
            pass
        return {"status": e.code, "erro": "HTTPError", "ms": int((time.time() - t0) * 1000),
                "tipo": (e.headers.get("Content-Type", "") if e.headers else "")[:60],
                "servidor": (e.headers.get("Server", "") if e.headers else "")[:40],
                "inicio": corpo[:200].decode("utf-8", "replace").replace("\n", " ")}
    except urllib.error.URLError as e:
        return {"erro": "URLError", "motivo": str(e.reason)[:160], "ms": int((time.time() - t0) * 1000)}
    except (socket.timeout, TimeoutError):
        return {"erro": "timeout", "ms": int((time.time() - t0) * 1000)}
    except ssl.SSLError as e:
        return {"erro": "SSLError", "motivo": str(e)[:160], "ms": int((time.time() - t0) * 1000)}
    except Exception as e:  # noqa: BLE001
        return {"erro": type(e).__name__, "motivo": str(e)[:160], "ms": int((time.time() - t0) * 1000)}


def main() -> int:
    print("=== DIAGNÓSTICO DAS FONTES ESTADUAIS DE SAÚDE (11/09/2026) ===")
    print("Nada é coletado nem gravado; só medição. Dois User-Agents por alvo, para separar bloqueio por IP de bloqueio por UA.\n")
    try:
        ip = urllib.request.urlopen("https://api.github.com/meta", timeout=20).status
        print(f"(conectividade básica ok: api.github.com → {ip})\n")
    except Exception as e:  # noqa: BLE001
        print(f"(aviso: nem api.github.com respondeu: {type(e).__name__})\n")
    resultado = {}
    for nome, url in ALVOS:
        print(f"--- {nome}\n    {url}")
        r = medir(url, ua_de("diagnóstico de fontes de saúde"))
        resultado[nome] = r
        print(f"    {json.dumps(r, ensure_ascii=False)}")
        time.sleep(1.5)
        print()
    # 07/11/2026: para o catálogo CKAN, o que importa é a lista de conjuntos (título, ano no nome,
    # recursos) — 120 bytes do corpo não dizem se existe síndrome gripal de 2025/2026 com outro nome.
    for nome, url in ALVOS:
        if "package_search" not in url:
            continue
        try:
            req = urllib.request.Request(url, headers={"User-Agent": ua_de("diagnóstico de fontes de saúde")})
            doc = json.loads(urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace"))
            print(f"--- {nome}: {doc.get('result', {}).get('count')} conjunto(s)")
            for d in doc.get("result", {}).get("results", []):
                recs = d.get("resources") or []
                anos = sorted({a for r in recs for a in __import__("re").findall(r"20[12]\d", (r.get("name") or "") + (r.get("url") or ""))})
                print(f"    {d.get('name')} · {d.get('title', '')[:70]} · {len(recs)} recurso(s) · anos {anos} · atualizado {str(d.get('metadata_modified', ''))[:10]}")
        except Exception as e:  # noqa: BLE001
            print(f"--- {nome}: {type(e).__name__}: {str(e)[:120]}")
        time.sleep(1.5)
    bloqueios = {k: v for k, v in resultado.items() if v.get("status") not in (200, None) or v.get("erro")}
    print(f"=== RESUMO: {len(bloqueios)} de {len(resultado)} tentativas sem HTTP 200 ===")
    for k, v in bloqueios.items():
        print(f"  {k} → {v.get('status') or v.get('erro')} {v.get('motivo', '')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
