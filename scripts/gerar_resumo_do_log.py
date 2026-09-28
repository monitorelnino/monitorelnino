#!/usr/bin/env python3
"""
gerar_resumo_do_log.py
======================
`data/log_buscas_resumo.json`: o que a página precisa saber do log, em alguns quilobytes.

Item 4 do handover `HANDOVER_desacoplar_pipeline_e_emagrecer_repositorio_27-09-2026.md`. Com o log
fatiado em JSONL mensal, a página não tem mais um `log_buscas.json` para buscar — e isso é bom por
uma razão que já valia antes: ela baixava **30,8 MB no navegador do leitor** para exibir dois números,
o total de execuções e a divisão por canal da última rodada.

O resumo é **derivado** (entra na cadeia canônica) e traz exatamente esses dois números, mais o total
por mês, que serve de prova de que o log não encolheu. Nada aqui é lido pelo cálculo do índice.

USO
  python3 scripts/gerar_resumo_do_log.py
  python3 scripts/gerar_resumo_do_log.py --autoteste
"""
import collections
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

SAIDA = RAIZ / "data" / "log_buscas_resumo.json"


def resumir(execucoes: list) -> dict:
    """Total, divisão por canal da ÚLTIMA data presente, e total por mês.

    "Última rodada" é a maior data do log, não "hoje": rodada que não rodou não inventa linha, e o
    resumo tem de dizer a data do que mostra."""
    if not execucoes:
        return {"total": 0, "ultima_data": None, "por_canal_na_ultima": {}, "por_mes": {}}
    ultima = max(str(e.get("data") or "") for e in execucoes)
    canais = collections.Counter(str(e.get("canal") or "—")
                                 for e in execucoes if str(e.get("data") or "") == ultima)
    meses = collections.Counter(str(e.get("data") or "sem-data")[:7] for e in execucoes)
    return {"total": len(execucoes), "ultima_data": ultima or None,
            "por_canal_na_ultima": dict(canais.most_common()),
            "por_mes": dict(sorted(meses.items()))}


def autoteste() -> int:
    casos = []
    execucoes = [
        {"data": "2026-09-27", "canal": "busca_web"},
        {"data": "2026-09-28", "canal": "busca_web"},
        {"data": "2026-09-28", "canal": "busca_web"},
        {"data": "2026-09-28", "canal": "DOM"},
        {"data": "2026-08-31", "canal": "DOU"},
    ]
    r = resumir(execucoes)
    casos.append(("o total é o número de execuções", r["total"] == 5))
    casos.append(("a última data é a maior do log, não hoje", r["ultima_data"] == "2026-09-28"))
    casos.append(("conta por canal só na última data",
                  r["por_canal_na_ultima"] == {"busca_web": 2, "DOM": 1}))
    casos.append(("o canal mais frequente vem primeiro",
                  list(r["por_canal_na_ultima"])[0] == "busca_web"))
    casos.append(("total por mês", r["por_mes"] == {"2026-08": 1, "2026-09": 4}))

    vazio = resumir([])
    casos.append(("log vazio não inventa data", vazio["ultima_data"] is None and vazio["total"] == 0))
    casos.append(("canal ausente aparece como travessão",
                  resumir([{"data": "2026-09-28"}])["por_canal_na_ultima"] == {"—": 1}))
    casos.append(("o resumo é pequeno por construção: cinco chaves no máximo",
                  set(r) == {"total", "ultima_data", "por_canal_na_ultima", "por_mes"}))

    ruins = [n for n, ok in casos if not ok]
    for n, ok in casos:
        print(f"  {'OK  ' if ok else 'FALHA'} {n}")
    if ruins:
        print(f"X AUTOTESTE: {len(ruins)} caso(s) reprovado(s).")
        return 1
    print(f"OK AUTOTESTE — {len(casos)} casos.")
    return 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    from coletores_base import gravar_em, ler_log
    doc = resumir(ler_log().get("execucoes") or [])
    doc["_governanca"] = ("Resumo do log de buscas (item 4, 28/09/2026). Derivado de "
                          "data/log_buscas/AAAA-MM.jsonl; existe para que a página não baixe o log "
                          "inteiro no navegador do leitor. Não é lido pelo cálculo do índice.")
    gravar_em(SAIDA, doc)
    print(f"✓ data/{SAIDA.name} — {doc['total']} execução(ões), última {doc['ultima_data']}, "
          f"{len(doc['por_canal_na_ultima'])} canal(is) na última rodada "
          f"({SAIDA.stat().st_size / 1e3:.1f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
