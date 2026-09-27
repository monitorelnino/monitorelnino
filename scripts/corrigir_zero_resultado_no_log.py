#!/usr/bin/env python3
"""
corrigir_zero_resultado_no_log.py
=================================
Correção retroativa do log de buscas: as consultas da camada 4 que voltaram com ZERO
resultado bruto e receberam a decisão `coberto_sem_mencao`.

Handover `HANDOVER_juiz_automatico_e_busca_web_27-09-2026.md`, PR 1 item 5.

Medido no `data/log_buscas.json` de 21 a 27/09/2026: 11.412 consultas da busca web, das quais
5.263 (46%) voltaram com zero resultado bruto e ainda assim registraram `coberto_sem_mencao` —
que é uma afirmação de ausência. A decisão correta é `motor_sem_resposta`: o motor não
respondeu, e a consulta não conta como verificação do município.

**Nada é apagado e nada é reescrito.** O log é append-only (a união pela base comum do §247
existe por causa disso). A execução original permanece exatamente como está; a correção entra
como uma execução NOVA, com `decisao: "motor_sem_resposta"`, `corrige` apontando para a
original (data, ibge, canal, camada e a posição no log) e `motivo_da_correcao`. Quem lê o log
vê as duas linhas e a ordem entre elas.

Idempotente: uma correção já gravada não é gravada de novo (a chave é a posição da execução
original). Rodar duas vezes não produz duas correções.

USO
  python3 scripts/corrigir_zero_resultado_no_log.py --relatorio        # só conta, não escreve
  python3 scripts/corrigir_zero_resultado_no_log.py --de 2026-09-21 --ate 2026-09-27 --escrever
  python3 scripts/corrigir_zero_resultado_no_log.py --autoteste
"""
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

MOTIVO = ("decisão editorial de 27/09/2026: zero resultado bruto não é ausência. "
          "A consulta original registrou coberto_sem_mencao com n_resultados=0; a decisão correta "
          "é motor_sem_resposta, e a consulta não conta como verificação do município.")


def precisa_de_correcao(e: dict) -> bool:
    """A execução a corrigir: camada 4 da busca web, zero resultado bruto, decisão de ausência.

    `n_resultados` ausente NÃO é zero — é desconhecido, e o que não foi medido não se corrige.
    Foi assim que uma auditoria anterior quase tratou 'não coletado' como 'zero'."""
    if e.get("canal") != "busca_web" or e.get("decisao") != "coberto_sem_mencao":
        return False
    n = e.get("n_resultados")
    return isinstance(n, int) and n == 0


def ja_corrigida(execucoes: list) -> set:
    """Posições originais que já têm linha de correção — base da idempotência."""
    feitas = set()
    for e in execucoes:
        alvo = e.get("corrige")
        if isinstance(alvo, dict) and isinstance(alvo.get("posicao"), int):
            feitas.add(alvo["posicao"])
    return feitas


def correcoes_para(execucoes: list, de: str = None, ate: str = None) -> list:
    """Devolve as execuções de correção a acrescentar. Função pura, sem disco."""
    feitas = ja_corrigida(execucoes)
    novas = []
    for i, e in enumerate(execucoes):
        if i in feitas or not precisa_de_correcao(e):
            continue
        data = e.get("data") or ""
        if de and data < de:
            continue
        if ate and data > ate:
            continue
        novas.append({
            "data": data, "canal": e.get("canal"), "camada": e.get("camada"),
            "uf": e.get("uf"), "municipio": e.get("municipio"), "ibge": e.get("ibge"),
            "nivel": e.get("nivel"), "strings": e.get("strings"), "n_resultados": 0,
            "resultados": "correção retroativa: o motor não respondeu nesta consulta",
            "decisao": "motor_sem_resposta",
            "fonte_suspensa_defeso": bool(e.get("fonte_suspensa_defeso")),
            "executor": "corrigir_zero_resultado_no_log.py",
            "hash_evidencia": None,
            "corrige": {"posicao": i, "data": data, "ibge": e.get("ibge"),
                        "canal": e.get("canal"), "camada": e.get("camada"),
                        "decisao_original": e.get("decisao")},
            "motivo_da_correcao": MOTIVO,
        })
    return novas


def autoteste() -> int:
    casos = []
    base = [
        {"data": "2026-09-21", "canal": "busca_web", "camada": 4, "ibge": "2927408",
         "decisao": "coberto_sem_mencao", "n_resultados": 0, "strings": ["q"]},
        {"data": "2026-09-22", "canal": "busca_web", "camada": 4, "ibge": "3550308",
         "decisao": "coberto_sem_mencao", "n_resultados": 7, "strings": ["q"]},
        {"data": "2026-09-23", "canal": "busca_web", "camada": 4, "ibge": "3304557",
         "decisao": "pista", "n_resultados": 0, "strings": ["q"]},
        {"data": "2026-09-24", "canal": "querido_diario", "camada": 2, "ibge": "1501402",
         "decisao": "coberto_sem_mencao", "n_resultados": 0, "strings": ["q"]},
        {"data": "2026-09-25", "canal": "busca_web", "camada": 4, "ibge": "5300108",
         "decisao": "coberto_sem_mencao", "strings": ["q"]},
    ]

    novas = correcoes_para(base)
    casos.append(("corrige só a consulta de zero resultado bruto da busca web", len(novas) == 1))
    casos.append(("a correção aponta para a posição original", novas and novas[0]["corrige"]["posicao"] == 0))
    casos.append(("a decisão da correção é motor_sem_resposta", novas and novas[0]["decisao"] == "motor_sem_resposta"))
    casos.append(("guarda a decisão original na linha de correção",
                  novas and novas[0]["corrige"]["decisao_original"] == "coberto_sem_mencao"))
    casos.append(("resultado bruto > 0 não é corrigido", all(c["corrige"]["posicao"] != 1 for c in novas)))
    casos.append(("pista não é corrigida", all(c["corrige"]["posicao"] != 2 for c in novas)))
    casos.append(("outro canal não é corrigido", all(c["corrige"]["posicao"] != 3 for c in novas)))
    casos.append(("n_resultados ausente não é tratado como zero",
                  all(c["corrige"]["posicao"] != 4 for c in novas)))

    # idempotência: com a correção já no log, nada novo é produzido
    casos.append(("idempotente: não corrige duas vezes", correcoes_para(base + novas) == []))

    # janela de datas
    casos.append(("janela de datas respeitada", correcoes_para(base, de="2026-09-22") == []))
    casos.append(("janela inclui o primeiro dia", len(correcoes_para(base, de="2026-09-21", ate="2026-09-27")) == 1))

    # o vocabulário da decisão nova existe de fato no log
    from coletores_base import DECISOES_LOG
    casos.append(("motor_sem_resposta existe no vocabulário fechado do log",
                  "motor_sem_resposta" in DECISOES_LOG))

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

    from coletores_base import DATA, gravar_em

    de = sys.argv[sys.argv.index("--de") + 1] if "--de" in sys.argv else None
    ate = sys.argv[sys.argv.index("--ate") + 1] if "--ate" in sys.argv else None
    escrever = "--escrever" in sys.argv

    caminho = DATA / "log_buscas.json"
    log = json.loads(caminho.read_text(encoding="utf-8"))
    if log.get("formato_versao") != 2:
        print("✗ log_buscas.json precisa estar no esquema v2")
        return 1
    execucoes = log["execucoes"]
    antes = len(execucoes)
    novas = correcoes_para(execucoes, de, ate)

    por_dia = {}
    for c in novas:
        por_dia[c["data"]] = por_dia.get(c["data"], 0) + 1
    print(f"log com {antes} execuções; {len(novas)} consulta(s) a corrigir"
          + (f" (janela {de or 'início'} a {ate or 'fim'})" if de or ate else ""))
    for d in sorted(por_dia):
        print(f"  {d}: {por_dia[d]}")

    if not escrever:
        print("relatório apenas; nada escrito (use --escrever)")
        return 0
    if not novas:
        print("nada a fazer")
        return 0

    log["execucoes"] = execucoes + novas
    # NÃO acrescenta carimbo algum ao documento: `scripts/unir_conflito_de_rodada.py` (§247/§252)
    # recusa a união quando os campos fora de 'execucoes' divergem entre os lados — e com razão,
    # porque divergência de formato pode esconder perda de dado. Uma chave nova aqui transformaria
    # todo merge da rodada numa recusa. O carimbo de quando a correção rodou já vive em cada linha
    # de correção, no campo `executor`.
    # trava de append-only: o log só cresce, e cresce exatamente o que foi contado
    assert len(log["execucoes"]) == antes + len(novas), "o log teria mudado de tamanho fora do previsto"
    gravar_em(caminho, log)
    print(f"✓ {len(novas)} linha(s) de correção acrescentada(s); log passou de {antes} para {len(log['execucoes'])} execuções")
    print("  nenhuma execução original foi alterada ou removida")
    return 0


if __name__ == "__main__":
    sys.exit(main())
