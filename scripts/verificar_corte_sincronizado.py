#!/usr/bin/env python3
"""Portão: a data de corte é a da rodada, não a de um arquivo que pode congelar.

Item 2 do handover dos textos da inicial (editoria, 30/09/2026).

O DEFEITO QUE ELE EXISTE PARA BARRAR
------------------------------------
`meta["corte"]` só avançava quando o hash do arquivo de transferências federais mudava. As
transferências voluntárias ficam bloqueadas no período eleitoral, então o arquivo parou em 10/09 —
e o site passou a dizer "dados até 10/09" enquanto o índice recebia planos todos os dias, pelo juiz
automático. O número estava certo sobre o arquivo de transferências e **errado sobre o que o leitor
entendia**: que a coleta tinha parado.

Nada reprovava, porque um carimbo velho não quebra nada — só mente devagar. Por isso o portão.

A REGRA
-------
Depois de uma rodada, `corte` e `atualizado_em` são a mesma data: o corte é o dia em que a coleta
rodou, tenha ela achado algo ou não. "Rodou e não achou nada novo" é informação, e é diferente de
"parou de rodar".

USO
    python3 scripts/verificar_corte_sincronizado.py
    python3 scripts/verificar_corte_sincronizado.py --autoteste
"""
import datetime
import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
META = RAIZ / "data" / "meta.json"

RE_DATA = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")


def data_de(texto: str):
    """A data do carimbo `dd/mm/aaaa`. None quando ilegível. Função pura."""
    m = RE_DATA.match(str(texto or "").strip())
    if not m:
        return None
    try:
        return datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None


def problemas(meta: dict) -> list:
    """As falhas do carimbo. Função pura."""
    ruins = []
    corte, atualizado = data_de((meta or {}).get("corte")), data_de((meta or {}).get("atualizado_em"))
    if corte is None:
        ruins.append(f"`corte` ilegível ou ausente: {(meta or {}).get('corte')!r}")
    if atualizado is None:
        ruins.append(f"`atualizado_em` ilegível ou ausente: {(meta or {}).get('atualizado_em')!r}")
    if corte and atualizado:
        if corte != atualizado:
            ruins.append(f"`corte` ({corte.strftime('%d/%m/%Y')}) ≠ `atualizado_em` "
                         f"({atualizado.strftime('%d/%m/%Y')}) — o corte é a data da rodada, e a "
                         f"rodada aconteceu. Diferença de {(atualizado - corte).days} dia(s).")
        if corte > atualizado:
            ruins.append("`corte` é posterior a `atualizado_em`: dado com data futura em relação "
                         "à própria rodada")
    return ruins


def autoteste() -> int:
    casos = []
    casos.append(("iguais passam",
                  problemas({"corte": "30/09/2026", "atualizado_em": "30/09/2026"}) == []))
    casos.append(("corte atrasado reprova",
                  len(problemas({"corte": "10/09/2026", "atualizado_em": "30/09/2026"})) == 1))
    casos.append(("a falha diz de quantos dias é o atraso",
                  "20 dia(s)" in problemas({"corte": "10/09/2026",
                                            "atualizado_em": "30/09/2026"})[0]))
    casos.append(("corte no futuro reprova duas vezes (diferente e posterior)",
                  len(problemas({"corte": "30/09/2026", "atualizado_em": "10/09/2026"})) == 2))
    casos.append(("corte ausente reprova",
                  any("corte` ilegível" in x for x in problemas({"atualizado_em": "30/09/2026"}))))
    casos.append(("atualizado ausente reprova",
                  any("atualizado_em` ilegível" in x for x in problemas({"corte": "30/09/2026"}))))
    casos.append(("data impossível é ilegível",
                  any("ilegível" in x for x in problemas({"corte": "31/02/2026",
                                                          "atualizado_em": "30/09/2026"}))))
    casos.append(("formato ISO não passa por carimbo",
                  any("ilegível" in x for x in problemas({"corte": "2026-09-30",
                                                          "atualizado_em": "30/09/2026"}))))
    casos.append(("meta vazio reprova", len(problemas({})) == 2))
    casos.append(("meta nulo não quebra", len(problemas(None)) == 2))
    casos.append(("lê a data do carimbo", data_de("30/09/2026") == datetime.date(2026, 9, 30)))
    casos.append(("texto que não é data devolve None", data_de("ontem") is None))

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
    meta = json.loads(META.read_text(encoding="utf-8"))
    ruins = problemas(meta)
    if ruins:
        print("✗ CORTE:")
        for r in ruins:
            print("   -", r)
        return 1
    print(f"✓ CORTE OK — `corte` e `atualizado_em` na mesma data ({meta.get('corte')}): o carimbo "
          f"é o da rodada, não o de um arquivo que pode congelar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
