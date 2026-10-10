#!/usr/bin/env python3
"""Conserta as execuções que o aplicador gravou fora do esquema do log v2.

28/09/2026. Na primeira noite em que `julgar_e_aplicar_descobertas.py` rodou com teto e
commitou, ele gravou **150 execuções** por uma porta própria: um dicionário com `data`,
`canal`, `alvo`, `decisao` e `motivo`, direto no monólito `data/log_buscas.json`. Faltavam
`strings`, `executor` e `nivel`, e `verificar_consistencia.py` reprovou — 300 erros, dois por
linha. A porta foi fechada no próprio aplicador (agora ele chama `log_busca`); este script
conserta o que já ficou gravado.

O QUE ELE FAZ, E O QUE NÃO FAZ
------------------------------
**Converte**, não apaga. O log é append-only: as 150 execuções são tentativas reais e contam.
Cada uma vira uma execução v2 com os campos obrigatórios, o território extraído do `alvo` e a
decisão traduzida pelo mesmo mapa que o aplicador passou a usar. O total de execuções antes e
depois tem de ser **idêntico** — o script recusa gravar se não for.

Não inventa território: alvo sem UF reconhecível fica com `municipio` e `uf` nulos. Não inventa
`nivel`: fica nulo, porque nenhuma bateria municipal completa foi feita. E nunca usa "nada
localizado", que é da bateria completa (§2.1).

USO
  python3 scripts/corrigir_log_do_aplicador.py              # relatório, nada escrito
  python3 scripts/corrigir_log_do_aplicador.py --escrever
  python3 scripts/corrigir_log_do_aplicador.py --autoteste
"""
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

MONOLITO = RAIZ / "data" / "log_buscas.json"
OBRIGATORIOS = ("data", "canal", "strings", "decisao", "executor")


def fora_do_esquema(e: dict) -> bool:
    return any(k not in e for k in OBRIGATORIOS)


# Nome histórico (28/09/2026) da decisão que o aplicador hoje grava como ABSTENCAO. As execuções
# antigas do log o carregam, e este conserto as traduz pelo mesmo vocabulário.
DECISAO_LEGADA = "FILA_HUMANA"


def converter(e: dict, executor: str, municipio_uf, mapa_decisao: dict) -> dict:
    """A execução antiga no esquema v2, sem perder nada do que ela dizia."""
    municipio, uf = municipio_uf(e.get("alvo"))
    return {
        "data": e.get("data"), "canal": e.get("canal") or "julgamento_automatico", "camada": 5,
        "uf": uf, "municipio": municipio, "ibge": None, "nivel": None,
        "strings": [str(e.get("alvo") or "")], "n_resultados": None,
        "resultados": str(e.get("motivo") or e.get("decisao") or "")[:600],
        "decisao": mapa_decisao.get(e.get("decisao"), "erro"),
        "fonte_suspensa_defeso": False, "executor": executor, "hash_evidencia": None,
    }


def autoteste() -> int:
    casos = []
    mapa = {"APLICADA": "registro", DECISAO_LEGADA: "pista",
            "DESCARTADA": "consultado sem achado", "REVERTIDA": "erro"}
    mu = lambda a: (("Camaçari", "BA") if str(a).endswith("/BA") else (None, None))  # noqa: E731
    velha = {"data": "28/09/2026", "canal": "julgamento_automatico",
             "alvo": "D-municipio-prioritario/Camaçari/BA", "decisao": DECISAO_LEGADA,
             "motivo": "fonte não reconhecida como oficial (sem mudança)"}
    nova = converter(velha, "robô", mu, mapa)

    casos.append(("a execução antiga é reconhecida como fora do esquema", fora_do_esquema(velha)))
    casos.append(("a convertida tem todos os campos obrigatórios", not fora_do_esquema(nova)))
    casos.append(("o motivo não se perde", "fonte não reconhecida" in nova["resultados"]))
    casos.append(("o alvo vira a string consultada", nova["strings"] == [velha["alvo"]]))
    casos.append(("o território sai do alvo", (nova["municipio"], nova["uf"]) == ("Camaçari", "BA")))
    casos.append(("a decisão é traduzida para o vocabulário", nova["decisao"] == "pista"))
    casos.append(("nivel fica nulo: nenhuma bateria completa foi feita", nova["nivel"] is None))
    sem_uf = converter({**velha, "alvo": "sem barra"}, "robô", mu, mapa)
    casos.append(("alvo sem UF não inventa território",
                  sem_uf["municipio"] is None and sem_uf["uf"] is None))
    desconhecida = converter({**velha, "decisao": "COISA_NOVA"}, "robô", mu, mapa)
    casos.append(("decisão desconhecida cai em 'erro', nunca em 'registro'",
                  desconhecida["decisao"] == "erro"))
    casos.append(("execução já no esquema não é tocada",
                  not fora_do_esquema({"data": "x", "canal": "y", "strings": [], "decisao": "erro",
                                       "executor": "z"})))

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

    from coletores_base import EXECUTOR, gravar_em, ler_log
    from julgar_e_aplicar_descobertas import DECISAO_NO_LOG, municipio_uf_do_alvo

    antes = len(ler_log().get("execucoes", []))
    doc = json.loads(MONOLITO.read_text(encoding="utf-8")) if MONOLITO.exists() else {}
    execucoes = doc.get("execucoes") or []
    alvos = [i for i, e in enumerate(execucoes) if fora_do_esquema(e)]
    print(f"{len(alvos)} execução(ões) fora do esquema, de {len(execucoes)} no monólito "
          f"({antes} no log inteiro)")
    if not alvos:
        print("nada a consertar")
        return 0

    for i in alvos:
        execucoes[i] = converter(execucoes[i], EXECUTOR, municipio_uf_do_alvo,
                                 {**DECISAO_NO_LOG, DECISAO_LEGADA: DECISAO_NO_LOG["ABSTENCAO"]})
    restantes = [i for i, e in enumerate(execucoes) if fora_do_esquema(e)]
    if restantes:
        print(f"X {len(restantes)} continuam fora do esquema depois da conversão — nada escrito")
        return 1

    if "--escrever" not in sys.argv:
        print("relatório apenas; nada escrito (use --escrever)")
        return 0

    doc["execucoes"] = execucoes
    gravar_em(MONOLITO, doc)   # §229
    depois = len(ler_log().get("execucoes", []))
    if depois != antes:
        print(f"X o total mudou de {antes} para {depois} — o log é append-only; confira antes de "
              f"commitar")
        return 1
    print(f"OK {len(alvos)} execução(ões) convertida(s) para o esquema v2; total intacto: {depois}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
