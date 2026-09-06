#!/usr/bin/env python3
"""
diagnosticar_querido_diario.py — PR-N0 §1.1 (06/09/2026)
=========================================================
Testes de RESULTADO CONHECIDO contra a API do Querido Diário, com request e response
integrais gravados (o chamador copia a saída para robo-registro/leituras/). Roda na Action.

Hipóteses, na ordem do documento: (1) consulta em LOTE (territory_ids com vírgulas — usada
pelo varredor antigo) vs UM território; (2) sintaxe do querystring (aspas/OR); (3) published_since;
(4) size; (5) limite de requisições (backoff); (6) endpoint/versão (docs).
"""
import json, time, urllib.parse, urllib.request, urllib.error, sys
from pathlib import Path

API = "https://queridodiario.ok.org.br/api/gazettes"
UA = {"User-Agent": "MonitorElNino/3.1 (diagnostico; monitorelnino.com.br)"}
SAIDA = Path("leituras_qd"); SAIDA.mkdir(exist_ok=True)


def chamar(nome, params, tent=3):
    url = API + "?" + urllib.parse.urlencode(params)
    for i in range(tent):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                corpo = r.read().decode("utf-8", "replace")
            (SAIDA / f"{nome}.request.txt").write_text(url + "\n", encoding="utf-8")
            (SAIDA / f"{nome}.response.json").write_text(corpo, encoding="utf-8")
            try:
                d = json.loads(corpo)
            except ValueError:
                print(f"  {nome}: HTTP 200 mas não-JSON ({corpo[:120]!r})"); return None
            n = d.get("total_gazettes"); g = d.get("gazettes") or []
            ex = sum(len(x.get("excerpts") or []) for x in g)
            print(f"  {nome}: total_gazettes={n} | gazettes={len(g)} | excerpts={ex} | url={url[:140]}")
            return d
        except urllib.error.HTTPError as e:
            print(f"  {nome}: HTTPError {e.code} {e.reason} (tentativa {i+1})"); (SAIDA / f"{nome}.error.txt").write_text(f"{url}\nHTTP {e.code}\n{e.read(500)!r}", encoding="utf-8")
            if e.code == 429: time.sleep(10 * (i + 1)); continue
            return None
        except Exception as e:  # noqa: BLE001
            print(f"  {nome}: {type(e).__name__}: {e} (tentativa {i+1})"); time.sleep(5 * (i + 1))
    return None


def main():
    # município com decreto certo em 2026 (RS, atos_resposta.json) — escolhido na Action a partir do arquivo
    try:
        atos = json.load(open("data/atos_resposta.json", encoding="utf-8"))["eventos"]
        rs = [a for a in atos if a.get("uf") == "RS" and a.get("ibge")]
        alvo = rs[0]; ibge = str(alvo["ibge"]).zfill(7); nome = alvo.get("nome")
    except Exception:  # noqa: BLE001
        ibge, nome = "4314902", "Porto Alegre"
    print(f"=== alvo com decreto certo: {nome} ({ibge}) ===")
    print("\n[1] um território, com aspas, published_since, size=10")
    chamar("t1_um_territorio", {"territory_ids": ibge, "published_since": "2026-06-29", "querystring": '"situação de emergência"', "size": 10})
    print("\n[2] cobertura: capital indexada, SEM querystring, size=1 (Porto Alegre 4314902; Curitiba 4106902)")
    chamar("t2_cobertura_poa", {"territory_ids": "4314902", "size": 1})
    chamar("t2_cobertura_cwb", {"territory_ids": "4106902", "size": 1})
    chamar("t2_cobertura_alvo", {"territory_ids": ibge, "size": 1})
    print("\n[3a] mesma consulta SEM published_since")
    chamar("t3a_sem_data", {"territory_ids": ibge, "querystring": '"situação de emergência"', "size": 10})
    print("[3b] querystring sem aspas nem OR")
    chamar("t3b_sem_aspas", {"territory_ids": ibge, "published_since": "2026-06-29", "querystring": "situação de emergência", "size": 10})
    print("[3c] querystring com OR e aspas (forma do coletor de 03/09)")
    chamar("t3c_or", {"territory_ids": ibge, "published_since": "2026-06-29", "querystring": '"situação de emergência" OR "plano de contingência"', "size": 10, "excerpt_size": 300, "number_of_excerpts": 2})
    print("\n[4] LOTE: 20 territórios do RS separados por vírgula (forma do varredor antigo)")
    try:
        ref = json.load(open("data/municipios_ibge_referencia.json", encoding="utf-8"))
        itens = ref if isinstance(ref, list) else list(ref.values())
        codigos = [str(x.get("codigo_ibge") or x.get("ibge")).zfill(7) for x in itens if (x.get("uf") == "RS")][:20]
    except Exception:  # noqa: BLE001
        codigos = ["4314902", "4305108", "4304606"]
    chamar("t4_lote_20", {"territory_ids": ",".join(codigos), "published_since": "2026-06-29", "querystring": '"situação de emergência"', "size": 20})
    chamar("t4_lote_20_sem_query", {"territory_ids": ",".join(codigos), "size": 5})
    print("\n[5] size grande (100) e pequeno (1), um território")
    chamar("t5_size100", {"territory_ids": ibge, "published_since": "2026-06-29", "size": 100})
    print("\n[6] docs da API")
    for u in ("https://queridodiario.ok.org.br/api/docs", "https://queridodiario.ok.org.br/api/openapi.json"):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30) as r:
                c = r.read(200000).decode("utf-8", "replace"); (SAIDA / ("docs_" + u.split("/")[-1] + ".txt")).write_text(c, encoding="utf-8")
                print(f"  {u}: HTTP {r.status}, {len(c)} chars; parâmetros vistos: {sorted(set(p for p in ('territory_ids','published_since','published_until','querystring','size','offset','excerpt_size','number_of_excerpts','pre_tags','post_tags','sort_by') if p in c))}")
        except Exception as e:  # noqa: BLE001
            print(f"  {u}: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
