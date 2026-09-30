#!/usr/bin/env python3
"""Mede o ciclo de mudança por PR: minutos até o merge, rodadas de CI, portões pulados.

Item 8 do handover de otimização (editoria, 30/09/2026).

PARA QUE SERVE
--------------
Os itens 1 a 7 prometem um ciclo mais barato. Promessa sem medição é opinião — e a própria decisão
de onde atacar, nesta rodada, saiu de uma medição (a máquina local não era o gargalo; os ciclos
repetidos de CI eram). Este script fecha o laço: lê os PRs já mesclados pela API do GitHub e
escreve, por PR, quanto tempo levou do primeiro commit ao merge e quantas execuções de CI foram
precisas.

**A meta declarada pela editoria:** PR de página em ≤ 20 min, PR de coletor em ≤ 15 min, zero
rodadas extras por manifesto.

O QUE ELE NÃO MEDE
------------------
Não mede o tempo de quem escreve o código — só o que o GitHub registra. Um PR que ficou aberto
esperando a editoria aparece como lento sem que nada no ciclo esteja errado, e por isso a mediana
vale mais que a média aqui: um PR parado uma noite não é um ciclo de oito horas.

USO
  python3 scripts/medir_ciclo_de_mudanca.py            # últimos 20 PRs mesclados
  python3 scripts/medir_ciclo_de_mudanca.py --quantos 50
  python3 scripts/medir_ciclo_de_mudanca.py --autoteste
"""
import datetime
import json
import pathlib
import statistics
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

SAIDA = RAIZ / "data" / "saude_pipeline.json"
META_PAGINA_MIN = 20
META_COLETOR_MIN = 15


def minutos(inicio: str, fim: str):
    """Minutos entre dois carimbos ISO do GitHub. None quando falta algum. Função pura."""
    if not inicio or not fim:
        return None
    try:
        a = datetime.datetime.fromisoformat(inicio.replace("Z", "+00:00"))
        b = datetime.datetime.fromisoformat(fim.replace("Z", "+00:00"))
    except ValueError:
        return None
    return round((b - a).total_seconds() / 60, 1)


def tipo_do_pr(arquivos: list) -> str:
    """'pagina', 'coletor' ou 'misto', pelo que o PR tocou. Função pura."""
    tem_pagina = any(a.endswith(".html") or a.startswith("assets/") for a in arquivos or [])
    tem_dado = any(a.endswith(".py") or a.startswith("data/") for a in arquivos or [])
    if tem_pagina and tem_dado:
        return "misto"
    if tem_pagina:
        return "pagina"
    if tem_dado:
        return "coletor"
    return "outro"


def resumo(medidas: list) -> dict:
    """Mediana e pior caso por tipo, mais a contagem de rodadas de CI. Função pura.

    Mediana, e não média: um PR que dormiu esperando a editoria não é um ciclo de oito horas, e a
    média deixaria esse caso mandar no número."""
    fora = {"n": len(medidas)}
    for tipo in ("pagina", "coletor", "misto", "outro"):
        ms = [m["minutos"] for m in medidas if m["tipo"] == tipo and m.get("minutos") is not None]
        if ms:
            fora[tipo] = {"n": len(ms), "mediana_min": round(statistics.median(ms), 1),
                          "pior_min": max(ms)}
    rodadas = [m["rodadas_ci"] for m in medidas if m.get("rodadas_ci") is not None]
    if rodadas:
        fora["rodadas_ci"] = {"mediana": statistics.median(rodadas), "pior": max(rodadas),
                              "com_mais_de_uma": sum(1 for r in rodadas if r > 1)}
    return fora


def cumpre_a_meta(r: dict) -> list:
    """O que ficou fora da meta declarada. Função pura."""
    fora = []
    if r.get("pagina", {}).get("mediana_min", 0) > META_PAGINA_MIN:
        fora.append(f"PR de página: mediana {r['pagina']['mediana_min']} min, meta {META_PAGINA_MIN}")
    if r.get("coletor", {}).get("mediana_min", 0) > META_COLETOR_MIN:
        fora.append(f"PR de coletor: mediana {r['coletor']['mediana_min']} min, "
                    f"meta {META_COLETOR_MIN}")
    if r.get("rodadas_ci", {}).get("com_mais_de_uma", 0):
        fora.append(f"{r['rodadas_ci']['com_mais_de_uma']} PR(s) com mais de uma rodada de CI")
    return fora


def coletar(quantos: int) -> list:
    campos = "number,title,createdAt,mergedAt,files,commits"
    r = subprocess.run(["gh", "pr", "list", "--state", "merged", "--limit", str(quantos),
                        "--json", campos], capture_output=True, text=True, cwd=RAIZ)
    if r.returncode != 0:
        raise RuntimeError(f"gh pr list falhou: {r.stderr.strip()[:200]}")
    medidas = []
    for pr in json.loads(r.stdout or "[]"):
        commits = pr.get("commits") or []
        primeiro = (commits[0].get("committedDate") if commits else None) or pr.get("createdAt")
        arquivos = [f.get("path", "") for f in (pr.get("files") or [])]
        checks = subprocess.run(["gh", "run", "list", "--limit", "20", "--json",
                                 "databaseId,headSha"], capture_output=True, text=True, cwd=RAIZ)
        rodadas = None
        if checks.returncode == 0:
            shas = {c.get("oid") for c in commits if c.get("oid")}
            rodadas = sum(1 for x in json.loads(checks.stdout or "[]")
                          if x.get("headSha") in shas) or None
        medidas.append({"pr": pr.get("number"), "titulo": (pr.get("title") or "")[:60],
                        "tipo": tipo_do_pr(arquivos), "arquivos": len(arquivos),
                        "minutos": minutos(primeiro, pr.get("mergedAt")),
                        "rodadas_ci": rodadas})
    return medidas


def autoteste() -> int:
    casos = []
    casos.append(("conta minutos entre dois carimbos",
                  minutos("2026-09-30T10:00:00Z", "2026-09-30T10:30:00Z") == 30.0))
    casos.append(("carimbo faltando devolve None", minutos(None, "2026-09-30T10:00:00Z") is None))
    casos.append(("carimbo ilegível devolve None", minutos("ontem", "hoje") is None))

    casos.append(("PR de página é reconhecido", tipo_do_pr(["index.html"]) == "pagina"))
    casos.append(("folha de estilo também é página", tipo_do_pr(["assets/base.css"]) == "pagina"))
    casos.append(("PR de coletor é reconhecido", tipo_do_pr(["coletar_x.py"]) == "coletor"))
    casos.append(("dado também é coletor", tipo_do_pr(["data/indice.json"]) == "coletor"))
    casos.append(("os dois juntos é misto", tipo_do_pr(["index.html", "x.py"]) == "misto"))
    casos.append(("nem um nem outro é outro", tipo_do_pr(["LEIA-ME.md"]) == "outro"))
    casos.append(("lista vazia é outro", tipo_do_pr([]) == "outro"))

    m = [{"tipo": "pagina", "minutos": 10, "rodadas_ci": 1},
         {"tipo": "pagina", "minutos": 30, "rodadas_ci": 2},
         {"tipo": "coletor", "minutos": 12, "rodadas_ci": 1}]
    r = resumo(m)
    casos.append(("a mediana de página sai certa", r["pagina"]["mediana_min"] == 20.0))
    casos.append(("o pior caso aparece", r["pagina"]["pior_min"] == 30))
    casos.append(("conta os PRs com mais de uma rodada", r["rodadas_ci"]["com_mais_de_uma"] == 1))
    casos.append(("mediana, não média: um PR parado não manda no número",
                  resumo([{"tipo": "pagina", "minutos": 10, "rodadas_ci": 1},
                          {"tipo": "pagina", "minutos": 12, "rodadas_ci": 1},
                          {"tipo": "pagina", "minutos": 600, "rodadas_ci": 1}]
                         )["pagina"]["mediana_min"] == 12.0))
    casos.append(("sem medida, o tipo não aparece", "coletor" not in resumo(
        [{"tipo": "pagina", "minutos": 5, "rodadas_ci": 1}])))

    casos.append(("dentro da meta não reclama",
                  cumpre_a_meta({"pagina": {"mediana_min": 15},
                                 "rodadas_ci": {"com_mais_de_uma": 0}}) == []))
    casos.append(("acima da meta de página reclama",
                  len(cumpre_a_meta({"pagina": {"mediana_min": 40},
                                     "rodadas_ci": {"com_mais_de_uma": 0}})) == 1))
    casos.append(("rodada extra de CI reclama",
                  len(cumpre_a_meta({"rodadas_ci": {"com_mais_de_uma": 3}})) == 1))

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
    quantos = 20
    if "--quantos" in sys.argv:
        quantos = int(sys.argv[sys.argv.index("--quantos") + 1])

    from coletores_base import gravar_em, hoje_editorial
    medidas = coletar(quantos)
    r = resumo(medidas)
    fora = cumpre_a_meta(r)

    print(f"{r['n']} PR(s) mesclado(s) medido(s)")
    for tipo in ("pagina", "coletor", "misto", "outro"):
        if tipo in r:
            x = r[tipo]
            print(f"  {tipo}: n={x['n']} · mediana {x['mediana_min']} min · pior {x['pior_min']} min")
    if "rodadas_ci" in r:
        print(f"  rodadas de CI: mediana {r['rodadas_ci']['mediana']} · "
              f"{r['rodadas_ci']['com_mais_de_uma']} PR(s) com mais de uma")
    for f in fora:
        print(f"  fora da meta: {f}")

    doc = json.loads(SAIDA.read_text(encoding="utf-8")) if SAIDA.exists() else {}
    doc["ciclo_de_mudanca"] = {"medido_em": hoje_editorial().isoformat(), "resumo": r,
                               "fora_da_meta": fora, "por_pr": medidas}
    gravar_em(SAIDA, doc)          # §229
    print(f"{SAIDA.relative_to(RAIZ)} atualizado")
    return 0


if __name__ == "__main__":
    sys.exit(main())
