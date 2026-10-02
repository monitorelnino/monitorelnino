#!/usr/bin/env python3
"""Portão de frescor POR COLETOR: quem declarou cadência tem de tê-la cumprido.

Item 7 do handover da rodada 2 (editoria, 30/09/2026), depois da certificação de 30/09.

O QUE ELE EXISTE PARA BARRAR
----------------------------
A certificação encontrou três coisas que nenhum portão pegava:

1. **Coletor que não roda não faz barulho.** `noturno_diarios` foi cancelado no teto em duas das
   três últimas noites, e diários municipais, DOE e S2iD ficaram sem coleta desde 29/09 — sem
   nenhum sinal vermelho em lugar nenhum. Dado velho não quebra nada; só envelhece.
2. **Coletor fora do painel não pode ser certificado.** Saúde, financiamento, cadastros federais e
   cobertura do Querido Diário não tinham registro de execução — e "não aparece" foi lido como
   "está bem" por tempo demais. Aqui, coletor declarado que nunca apareceu é **atrasado**, não
   silêncio.
3. **Cadência que só existe no cron não é cadência.** O cron do GitHub é de melhor esforço: atrasa,
   descarta sob carga e pode não rodar. A cadência declarada vive em `docs/CADENCIAS.md`, e este
   portão compara a promessa com o que de fato aconteceu.

A REGRA
-------
Atrasado = passou de **1,1 × a cadência** sem execução bem-sucedida. O fator existe para atraso de
minutos não virar alarme: um coletor diário só fica atrasado depois de 26,4 h; um semanal, depois
de 7,7 dias.

`por_documento` não tem prazo (o documento é que manda) e `sob_demanda` nunca fica atrasado — mas
os dois precisam estar declarados, porque o que não está declarado não se confere.

**Ele avisa; não reprova sozinho.** Fonte fora do ar é rotina, e transformar todo atraso em portão
vermelho faria a suíte inteira depender da rede de terceiros. `--reprovar` existe para quem quiser
usá-lo como portão duro; o uso padrão é o resumo, que entra no painel e no publicador.

USO
    python3 scripts/verificar_cadencia_coletores.py
    python3 scripts/verificar_cadencia_coletores.py --reprovar
    python3 scripts/verificar_cadencia_coletores.py --autoteste
"""
import datetime
import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

CADENCIAS = RAIZ / "docs" / "CADENCIAS.md"
SAUDE = RAIZ / "data" / "saude_pipeline.json"

# 02/10/2026: "quinzenal" entra no vocabulário porque a bateria de saúde estadual passou a
# rodar nos dias 1 e 15 — ato estadual é publicado uma vez, e varrer toda noite o que já foi
# localizado gasta a busca sem produzir informação nova.
HORAS = {"diaria": 24, "semanal": 24 * 7, "quinzenal": 24 * 15, "mensal": 24 * 30}
FATOR_TOLERANCIA = 1.1
SEM_PRAZO = ("por_documento", "sob_demanda")

RE_LINHA = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*(\w+)\s*\|")


def cadencias_declaradas(texto: str) -> dict:
    """{script: cadência} lido de docs/CADENCIAS.md. Função pura.

    Lê só as linhas cujo primeiro campo é um script entre crases e o segundo é uma palavra — o
    cabeçalho e a legenda do formato ficam de fora por não casarem, sem precisar de lista de
    exceções."""
    fora = {}
    for linha in (texto or "").split("\n"):
        m = RE_LINHA.match(linha.strip())
        if m and (m.group(2) in HORAS or m.group(2) in SEM_PRAZO):
            fora[m.group(1)] = m.group(2)
    return fora


def ultima_execucao_ok(execucoes) -> dict:
    """{script: datetime da última execução com status ok}. Função pura.

    Só `ok` conta: execução que terminou em erro não renova o frescor, e é exatamente o caso que
    o painel precisava distinguir de 'não rodou'."""
    fora = {}
    for x in execucoes or []:
        if not isinstance(x, dict) or x.get("status") != "ok":
            continue
        quando = str(x.get("inicio") or x.get("data") or "")
        try:
            d = datetime.datetime.fromisoformat(quando)
        except ValueError:
            continue
        s = x.get("script")
        if s and (s not in fora or d > fora[s]):
            fora[s] = d
    return fora


def atrasados(declaradas: dict, ultimas: dict, agora) -> list:
    """[(script, cadência, horas desde a última ok ou None)] dos atrasados. Função pura."""
    fora = []
    for script, cadencia in sorted((declaradas or {}).items()):
        if cadencia in SEM_PRAZO:
            continue
        teto = HORAS[cadencia] * FATOR_TOLERANCIA
        ultima = (ultimas or {}).get(script)
        if ultima is None:
            fora.append((script, cadencia, None))
            continue
        horas = (agora - ultima).total_seconds() / 3600
        if horas > teto:
            fora.append((script, cadencia, round(horas, 1)))
    return fora


RE_ESSENCIAL = re.compile(r"^(recalcular_mare\.py|gerar_[\w-]+\.py|scripts/gerar_[\w-]+\.py)$")


def nao_declarados(declaradas: dict, ultimas: dict) -> list:
    """Coletores que aparecem no painel e não estão em CADENCIAS.md. Função pura.

    Coletor que roda sem cadência declarada não pode ser certificado — não há contra o que
    comparar. Os ESSENCIAIS (o motor e os geradores) ficam de fora: eles não são coletores, rodam
    quando a rodada manda e já têm portão próprio em gerar_saude_pipeline.py."""
    return sorted(s for s in (ultimas or {})
                  if s not in (declaradas or {}) and not RE_ESSENCIAL.match(str(s)))


def autoteste() -> int:
    tabela = """
| coletor | cadência | janela | onde roda | o que ele responde |
|---|---|---|---|---|
| `a.py` | diaria | 00:05 UTC | x | y |
| `b.py` | semanal | dom | x | y |
| `c.py` | por_documento | dom | x | y |
| `d.py` | sob_demanda | — | x | y |
"""
    d = cadencias_declaradas(tabela)
    casos = [
        ("lê quatro coletores da tabela", len(d) == 4),
        ("lê a cadência de cada um", d["a.py"] == "diaria" and d["b.py"] == "semanal"),
        ("cabeçalho não vira coletor", "coletor" not in d),
        ("separador não vira coletor", "---" not in d),
        # 02/10/2026: "quinzenal" passou a ser cadência conhecida (bateria de saúde estadual nos
        # dias 1 e 15). O caso continua, com uma palavra que de fato não é cadência.
        ("cadência desconhecida é ignorada",
         cadencias_declaradas("| `x.py` | quando_der | a | b | c |") == {}),
        ("quinzenal é cadência conhecida, de 15 dias",
         cadencias_declaradas("| `x.py` | quinzenal | a | b | c |") == {"x.py": "quinzenal"}
         and HORAS["quinzenal"] == 24 * 15),
        ("texto vazio não quebra", cadencias_declaradas("") == {}),
        ("texto nulo não quebra", cadencias_declaradas(None) == {}),
    ]

    execs = [
        {"script": "a.py", "status": "ok", "inicio": "2026-09-30T01:00:00"},
        {"script": "a.py", "status": "erro", "inicio": "2026-09-30T23:00:00"},
        {"script": "b.py", "status": "ok", "inicio": "2026-09-01T01:00:00"},
        {"script": "z.py", "status": "ok", "inicio": "2026-09-30T01:00:00"},
        {"script": "ruim.py", "status": "ok", "inicio": "ontem"},
        "isto não é um registro",
    ]
    u = ultima_execucao_ok(execs)
    casos += [
        ("só execução ok conta", u["a.py"] == datetime.datetime(2026, 9, 30, 1, 0)),
        ("erro não renova o frescor", u["a.py"].hour == 1),
        ("carimbo ilegível é descartado", "ruim.py" not in u),
        ("registro que não é dicionário não quebra", "z.py" in u),
        ("lista vazia não quebra", ultima_execucao_ok([]) == {}),
        ("lista nula não quebra", ultima_execucao_ok(None) == {}),
    ]

    agora = datetime.datetime(2026, 9, 30, 12, 0)
    a = dict((s, c) for s, c, _ in [(x[0], x[1], x[2]) for x in atrasados(d, u, agora)])
    casos += [
        ("diário dentro da tolerância não é atrasado", "a.py" not in a),
        ("semanal vencido é atrasado", "b.py" in a),
        ("por_documento e sob_demanda nunca atrasam",
         all(s not in a for s in ("c.py", "d.py"))),
        ("declarado sem nenhuma execução aparece com horas None",
         ("naoRodou.py", "diaria", None) in atrasados({"naoRodou.py": "diaria"}, {}, agora)),
        ("diário com 27 h vira atrasado",
         atrasados({"a.py": "diaria"}, {"a.py": datetime.datetime(2026, 9, 29, 9, 0)}, agora) != []),
        ("diário com 26 h ainda não é atrasado",
         atrasados({"a.py": "diaria"}, {"a.py": datetime.datetime(2026, 9, 29, 10, 0)},
                   agora) == []),
    ]
    casos += [
        ("script no painel e fora da tabela é apontado", nao_declarados(d, u) == ["z.py"]),
        ("essencial não é cobrado de cadência",
         nao_declarados({}, {"recalcular_mare.py": 1, "gerar_feeds.py": 1}) == []),
        ("coletor fora da tabela continua sendo cobrado",
         nao_declarados({}, {"coletar_x.py": 1}) == ["coletar_x.py"]),
        ("tabela e painel vazios não quebram", nao_declarados({}, {}) == []),
    ]

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
    from coletores_base import hoje_editorial

    declaradas = cadencias_declaradas(CADENCIAS.read_text(encoding="utf-8"))
    painel = json.loads(SAUDE.read_text(encoding="utf-8")) if SAUDE.exists() else {}
    ultimas = ultima_execucao_ok(painel.get("execucoes"))
    # A hora vem do carimbo do painel quando existe: comparar o relógio de quem roda o portão com
    # execuções gravadas noutro fuso produziria atraso imaginário.
    try:
        agora = datetime.datetime.fromisoformat(str(painel.get("atualizado_em")))
    except (TypeError, ValueError):
        agora = datetime.datetime.combine(hoje_editorial(), datetime.time(12, 0))

    atrasos = atrasados(declaradas, ultimas, agora)
    fora_da_tabela = nao_declarados(declaradas, ultimas)

    print(f"{len(declaradas)} coletor(es) com cadência declarada em docs/CADENCIAS.md · "
          f"referência: {agora.isoformat(timespec='minutes')}")
    if atrasos:
        print(f"! {len(atrasos)} atrasado(s) (acima de {FATOR_TOLERANCIA}× a cadência):")
        for script, cadencia, horas in atrasos:
            quando = "nenhuma execução bem-sucedida registrada" if horas is None \
                else f"última há {horas} h"
            print(f"   - {script} ({cadencia}) — {quando}")
    else:
        print("✓ nenhum coletor atrasado")
    if fora_da_tabela:
        print(f"! {len(fora_da_tabela)} script(s) no painel sem cadência declarada — sem cadência "
              f"não há certificação: {', '.join(fora_da_tabela)}")

    if "--reprovar" in sys.argv and (atrasos or fora_da_tabela):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
