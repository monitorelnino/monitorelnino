#!/usr/bin/env python3
"""Portão: sinal diário não pode cair em cadência semanal.

POR QUE ESTE PORTÃO EXISTE (30/09/2026, §306)
=============================================
A editoria decidiu, em 29/09/2026, que os sinais físicos do Monitor de riscos — avisos do INMET,
focos do INPE, seca, temperatura, ar — são **diários na fonte** e não podem cair na cadência
semanal. A decisão foi escrita quando `coletar_sinais_risco.py` rodava nas quatro coletas diárias do
`atualizar.yml`.

Um dia depois, a condição já não valia. O desacoplamento do item 1b tirou o `schedule` diário do
monólito, e o script ficou só no workflow **semanal** de domingo. Ninguém decidiu isso: foi efeito
colateral de outra mudança, e não havia nada que reprovasse. Um aviso de perigo do INMET com sete
dias de atraso não é sinal, é arquivo — e o card diria "em vigor" sobre aviso que expirou na terça.

Este portão trava a propriedade, não o arranjo: **existe pelo menos um workflow com `schedule`
diário que chama `coletar_sinais_risco.py`**. Ele não exige que seja este ou aquele arquivo; se a
coleta migrar de lugar amanhã, o portão continua valendo, e é isso que o diferencia de um teste que
decora o nome do workflow de hoje.

Uso:
    python3 scripts/verificar_cadencia_sinais.py
    python3 scripts/verificar_cadencia_sinais.py --autoteste
"""
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
FLUXOS = RAIZ / ".github" / "workflows"
SCRIPT = "coletar_sinais_risco.py"


def crons(texto: str) -> list:
    """As expressões de cron declaradas no workflow. Função pura."""
    return [m.group(1).strip() for m in re.finditer(r"""cron:\s*["']([^"']+)["']""", texto or "")]


def eh_diario(cron: str) -> bool:
    """True quando o cron roda todo dia. Função pura.

    "Todo dia" é dia-do-mês e dia-da-semana livres (`*`). `0 8 * * 0` roda só aos domingos e é
    exatamente o caso que este portão existe para reprovar."""
    campos = str(cron or "").split()
    if len(campos) != 5:
        return False
    dia_do_mes, mes, dia_da_semana = campos[2], campos[3], campos[4]
    return dia_do_mes.strip() == "*" and mes.strip() == "*" and dia_da_semana.strip() == "*"


def problemas(fluxos: dict) -> list:
    """`fluxos` é {nome: conteúdo}. Devolve a lista de falhas, vazia quando está tudo certo."""
    chamam = {n: t for n, t in (fluxos or {}).items() if SCRIPT in t}
    if not chamam:
        return [f"nenhum workflow chama {SCRIPT} — a coleta de sinais físicos sumiu"]
    diarios = [n for n, t in chamam.items() if any(eh_diario(c) for c in crons(t))]
    if diarios:
        return []
    onde = ", ".join(sorted(chamam))
    return [f"{SCRIPT} só aparece em workflow sem cron diário ({onde}) — os sinais físicos são "
            f"diários na fonte (decisão da editoria, 29/09/2026) e não podem cair em cadência "
            f"semanal"]


def autoteste() -> int:
    casos = []
    diario = 'schedule:\n    - cron: "0 8 * * *"\n' + SCRIPT
    semanal = 'schedule:\n    - cron: "30 7 * * 0"\n' + SCRIPT
    manual = "workflow_dispatch:\n" + SCRIPT

    casos.append(("cron de todo dia é diário", eh_diario("0 8 * * *") is True))
    casos.append(("cron de domingo NÃO é diário", eh_diario("30 7 * * 0") is False))
    casos.append(("cron de dia 1 do mês não é diário", eh_diario("0 8 1 * *") is False))
    casos.append(("cron de dia útil não é diário", eh_diario("0 8 * * 1-5") is False))
    casos.append(("cron com hora de lista segue diário", eh_diario("0 1,3,5 * * *") is True))
    casos.append(("texto que não é cron não é diário", eh_diario("todo dia") is False))
    casos.append(("cron vazio não é diário", eh_diario("") is False))

    casos.append(("lê as expressões de cron do texto",
                  crons('  - cron: "0 8 * * *"\n  - cron: "5 9 * * *"') == ["0 8 * * *", "5 9 * * *"]))
    casos.append(("cron com aspas simples também é lido",
                  crons("- cron: '0 8 * * *'") == ["0 8 * * *"]))

    casos.append(("workflow diário passa", problemas({"a.yml": diario}) == []))
    casos.append(("só semanal reprova", len(problemas({"a.yml": semanal})) == 1))
    casos.append(("semanal + diário passa: basta um diário",
                  problemas({"a.yml": semanal, "b.yml": diario}) == []))
    casos.append(("só manual reprova — botão não é cadência",
                  len(problemas({"a.yml": manual})) == 1))
    casos.append(("nenhum workflow chamando o coletor reprova",
                  len(problemas({"a.yml": "nada aqui"})) == 1))
    casos.append(("a falha do semanal nomeia onde ele está",
                  "a.yml" in problemas({"a.yml": semanal})[0]))
    casos.append(("a falha diz que a decisão é da editoria e a data",
                  "29/09/2026" in problemas({"a.yml": semanal})[0]))

    ruins = [n for n, ok in casos if not ok]
    for n, ok in casos:
        print(f"  {'OK  ' if ok else 'FALHA'} {n}")
    if ruins:
        print(f"X AUTOTESTE DA CADÊNCIA DE SINAIS: {len(ruins)} caso(s) reprovado(s).")
        return 1
    print(f"OK AUTOTESTE — {len(casos)} casos, sem rede e sem escrita.")
    return 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    fluxos = {p.name: p.read_text(encoding="utf-8") for p in sorted(FLUXOS.glob("*.yml"))}
    ruins = problemas(fluxos)
    if ruins:
        print("✗ CADÊNCIA DOS SINAIS:")
        for r in ruins:
            print("   -", r)
        return 1
    diarios = sorted(n for n, t in fluxos.items()
                     if SCRIPT in t and any(eh_diario(c) for c in crons(t)))
    print(f"✓ CADÊNCIA DOS SINAIS OK — {SCRIPT} roda todo dia em: {', '.join(diarios)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
