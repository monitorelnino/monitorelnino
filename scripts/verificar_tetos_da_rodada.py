#!/usr/bin/env python3
"""Confere que os tetos de tempo da rodada são ARITMETICAMENTE coerentes.

POR QUE ESTE PORTÃO EXISTE (27/09/2026, §248)
=============================================
Em 27/09 a rodada de atualização foi cortada pelo teto do JOB três vezes, sempre antes do
commit — e portanto sem publicar dado novo, embora o passo de publicação desse `success`. A
causa não era nenhuma fonte lenta: era uma conta.

Os tetos declarados POR PASSO somavam **220 minutos**. O teto do JOB era **180**. Com essa
conta o job é cortado sempre que os passos correm perto dos seus tetos — e o passo cortado sai
como `cancelled`, contra o qual `continue-on-error` NÃO protege (ele só cobre `failure`). Todo
passo depois dele é pulado, incluindo o commit dos dados.

O invariante que este portão trava é o mínimo que torna a rodada capaz de chegar ao fim:

    soma dos tetos por passo  ≤  teto do job

Ele não diz que a rodada vai caber — diz que ela NÃO ESTÁ CONDENADA por construção. Se alguém
subir um teto de passo sem olhar o do job, ou baixar o do job sem olhar os dos passos, reprova
aqui em vez de reprovar em produção três horas depois, calado.

Também confere que todo job com passos tem teto próprio: sem teto o GitHub dá 6 HORAS, e a
trava de concorrência transforma isso na fila de atualização parada o dia todo.

Uso:
    python3 scripts/verificar_tetos_da_rodada.py
    python3 scripts/verificar_tetos_da_rodada.py --autoteste
"""
import io
import pathlib
import sys

import yaml

RAIZ = pathlib.Path(__file__).resolve().parent.parent
ALVO = RAIZ / ".github" / "workflows" / "atualizar.yml"

# O GitHub encerra qualquer job em 6 h. Teto acima disso é ficção, e teto perto disso põe a fila
# de atualização parada o dia todo por causa da trava de concorrência.
TETO_MAXIMO_DO_JOB = 360


def conferir(doc):
    """Devolve a lista de problemas encontrados no documento do workflow."""
    problemas = []
    jobs = doc.get("jobs") or {}
    for nome, job in jobs.items():
        passos = job.get("steps") or []
        if not passos:
            continue
        teto_job = job.get("timeout-minutes")

        if teto_job is None:
            problemas.append(f"job '{nome}': sem timeout-minutes próprio — herdaria as 6 h do "
                             f"GitHub, e a trava de concorrência pararia a fila o dia todo")
            continue

        if teto_job > TETO_MAXIMO_DO_JOB:
            problemas.append(f"job '{nome}': teto de {teto_job} min acima do limite real do "
                             f"GitHub ({TETO_MAXIMO_DO_JOB} min)")

        com_teto = [(k + 1, p.get("timeout-minutes"), str(p.get("name") or "(sem nome)"))
                    for k, p in enumerate(passos) if p.get("timeout-minutes")]
        soma = sum(t for _, t, _ in com_teto)

        if soma > teto_job:
            detalhe = ", ".join(f"passo {n}={t}" for n, t, _ in com_teto)
            problemas.append(
                f"job '{nome}': a soma dos tetos por passo ({soma} min) passa do teto do job "
                f"({teto_job} min). O job seria cortado antes do fim, e o passo cortado sai "
                f"`cancelled` — contra o que `continue-on-error` não protege. [{detalhe}]")

    return problemas


def autoteste() -> int:
    falhas = []

    def checar(nome, cond):
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    # 1. o caso real de 27/09: soma 220 contra teto de 180
    doc = {"jobs": {"atualizar": {"timeout-minutes": 180, "steps": [
        {"name": "a", "timeout-minutes": 50}, {"name": "b", "timeout-minutes": 90},
        {"name": "c", "timeout-minutes": 80}]}}}
    p = conferir(doc)
    checar("soma dos tetos acima do teto do job REPROVA",
           len(p) == 1 and "passa do teto do job" in p[0])

    # 2. a mesma coisa cabendo passa
    doc["jobs"]["atualizar"]["timeout-minutes"] = 300
    checar("com folga no teto do job, passa", conferir(doc) == [])

    # 3. igual também passa: o invariante é ≤, não <
    doc["jobs"]["atualizar"]["timeout-minutes"] = 220
    checar("soma exatamente igual ao teto do job passa", conferir(doc) == [])

    # 4. job sem teto próprio REPROVA
    doc2 = {"jobs": {"x": {"steps": [{"name": "a", "timeout-minutes": 5}]}}}
    p = conferir(doc2)
    checar("job sem teto próprio REPROVA", len(p) == 1 and "sem timeout-minutes" in p[0])

    # 5. teto de job acima do limite real do GitHub REPROVA
    doc3 = {"jobs": {"x": {"timeout-minutes": 600, "steps": [{"name": "a"}]}}}
    p = conferir(doc3)
    checar("teto de job acima de 360 min REPROVA",
           len(p) == 1 and "acima do limite real" in p[0])

    # 6. job sem passos é ignorado (job de guarda, matriz vazia)
    checar("job sem passos não é cobrado",
           conferir({"jobs": {"vazio": {"steps": []}}}) == [])

    # 7. passo sem teto não entra na soma — o portão não exige teto em TODO passo
    doc4 = {"jobs": {"x": {"timeout-minutes": 60, "steps": [
        {"name": "a", "timeout-minutes": 30}, {"name": "b"}, {"name": "c"}]}}}
    checar("passo sem teto não entra na soma", conferir(doc4) == [])

    if falhas:
        print(f"\n✗ TETOS DA RODADA: {len(falhas)} falha(s).")
        return 1
    print("\n✓ TETOS DA RODADA OK (autoteste) — o invariante sabe reprovar e sabe aprovar.")
    return 0


def main() -> int:
    if "--autoteste" in sys.argv[1:]:
        return autoteste()

    doc = yaml.safe_load(io.open(ALVO, encoding="utf-8"))
    problemas = conferir(doc)
    if problemas:
        print(f"✗ TETOS DA RODADA: {len(problemas)} problema(s) em {ALVO.name}:")
        for p in problemas:
            print(f"  · {p}")
        print("  Conserto: subir o teto do job, ou baixar os tetos por passo, até a soma caber.")
        return 1

    job = doc["jobs"]["atualizar"]
    soma = sum(p["timeout-minutes"] for p in job["steps"] if p.get("timeout-minutes"))
    print(f"✓ TETOS DA RODADA OK — soma dos tetos por passo {soma} min ≤ teto do job "
          f"{job['timeout-minutes']} min.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
