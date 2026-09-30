#!/usr/bin/env python3
"""Portão: entrada nova de CHANGELOG é curta e tem chave por data e PR, não por § sequencial.

Item 4 do handover de otimização do ciclo de mudança (editoria, 30/09/2026).

DUAS REGRAS, E O MOTIVO DE CADA UMA
-----------------------------------
**Teto de 80 palavras.** As entradas desta semana passaram de 400. Fundamentação longa tem lugar —
a `METODOLOGIA.md`, que é a fonte de verdade do método e fica onde alguém procura método. O
CHANGELOG responde "o quê · por quê, numa frase · onde", e é lido para achar quando algo mudou.

**Chave por data e PR (`## 2026-09-30 · #470 · título`), não por `§` sequencial.** A numeração
global colidia entre ramos: dois PRs abertos no mesmo dia escolhiam o mesmo número, e a união
sobrescrevia a entrada de um deles — aconteceu três vezes em 29 e 30/09, e uma seção inteira foi
perdida numa união textual. Data e PR são únicos por construção e não precisam de renumeração.

**As entradas antigas ficam como estão.** O portão só cobra o que nasce a partir daqui: reescrever
mil entradas para o formato novo seria trabalho sem leitor.

USO
    python3 scripts/verificar_changelog_curto.py
    python3 scripts/verificar_changelog_curto.py --autoteste
"""
import datetime
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
CHANGELOG = RAIZ / "CHANGELOG.md"
TETO_DE_PALAVRAS = 80
# A partir desta data, entrada nova segue o formato novo. Antes dela, o histórico fica intacto.
VALE_A_PARTIR_DE = datetime.date(2026, 10, 1)

RE_TITULO = re.compile(r"^## (.+)$", re.M)
RE_FORMATO_NOVO = re.compile(r"^(\d{4})-(\d{2})-(\d{2}) · #(\d+) · (.+)$")
RE_FORMATO_ANTIGO = re.compile(r"^§\d+ ·")


def entradas(texto: str) -> list:
    """[(titulo, corpo)] de cada seção `## `. Função pura."""
    partes = []
    achados = list(RE_TITULO.finditer(texto or ""))
    for i, m in enumerate(achados):
        fim = achados[i + 1].start() if i + 1 < len(achados) else len(texto)
        partes.append((m.group(1).strip(), texto[m.end():fim].strip()))
    return partes


def data_da_entrada(titulo: str):
    """A data da entrada, pelo formato novo ou pelo `· dd/mm/aaaa` do antigo. None se não houver."""
    m = RE_FORMATO_NOVO.match(titulo or "")
    if m:
        try:
            return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    m2 = re.search(r"·\s*(\d{2})/(\d{2})/(\d{4})\s*$", titulo or "")
    if m2:
        try:
            return datetime.date(int(m2.group(3)), int(m2.group(2)), int(m2.group(1)))
        except ValueError:
            return None
    return None


def palavras(corpo: str) -> int:
    """Conta palavras do corpo, ignorando tabelas e blocos de código. Função pura.

    Tabela é dado, não prosa: cobrar palavras dentro dela empurraria para prosa pior."""
    limpo = re.sub(r"```.*?```", " ", corpo or "", flags=re.S)
    limpo = "\n".join(l for l in limpo.split("\n") if not l.strip().startswith("|"))
    return len([p for p in re.split(r"\s+", limpo) if p.strip()])


def problemas(texto: str, hoje: datetime.date = None) -> list:
    """As falhas das entradas que nasceram sob a regra nova. Função pura."""
    hoje = hoje or datetime.date.today()
    ruins = []
    for titulo, corpo in entradas(texto):
        d = data_da_entrada(titulo)
        if d is None or d < VALE_A_PARTIR_DE:
            continue          # histórico: fica como está
        if RE_FORMATO_ANTIGO.match(titulo):
            ruins.append(f"{titulo[:60]}: numeração § sequencial — use `AAAA-MM-DD · #PR · título`")
            continue
        if not RE_FORMATO_NOVO.match(titulo):
            ruins.append(f"{titulo[:60]}: título fora do formato `AAAA-MM-DD · #PR · título`")
            continue
        n = palavras(corpo)
        if n > TETO_DE_PALAVRAS:
            ruins.append(f"{titulo[:60]}: {n} palavras, acima do teto de {TETO_DE_PALAVRAS} — "
                         f"fundamentação longa vai para a METODOLOGIA")
    return ruins


def autoteste() -> int:
    casos = []
    nova = "## 2026-10-02 · #500 · Título curto\n\nUma frase.\n"
    casos.append(("entrada nova, curta e no formato, passa", problemas(nova) == []))
    casos.append(("entrada antiga com § não é cobrada",
                  problemas("## §300 · Coisa antiga · 30/09/2026\n\n" + "palavra " * 300) == []))
    casos.append(("entrada nova com § reprova",
                  len(problemas("## §400 · Coisa · 02/10/2026\n\nx")) == 1))
    casos.append(("entrada nova longa reprova",
                  len(problemas("## 2026-10-02 · #500 · T\n\n" + "palavra " * 200)) == 1))
    casos.append(("a falha de tamanho diz o número de palavras",
                  "200 palavras" in problemas("## 2026-10-02 · #500 · T\n\n"
                                              + "palavra " * 200)[0]))
    casos.append(("título novo fora do formato reprova",
                  len(problemas("## 02/10/2026 — coisa\n\nx", datetime.date(2026, 10, 2))) == 0))
    casos.append(("data anterior ao corte não é cobrada",
                  problemas("## 2026-09-30 · #1 · T\n\n" + "palavra " * 300) == []))
    casos.append(("tabela não conta como prosa",
                  problemas("## 2026-10-02 · #500 · T\n\n"
                            + "\n".join("| a | b |" for _ in range(200))) == []))
    casos.append(("bloco de código não conta como prosa",
                  problemas("## 2026-10-02 · #500 · T\n\n```\n" + "x " * 300 + "\n```") == []))
    casos.append(("changelog vazio passa", problemas("") == []))
    casos.append(("lê a data do formato novo",
                  data_da_entrada("2026-10-02 · #500 · T") == datetime.date(2026, 10, 2)))
    casos.append(("lê a data do formato antigo",
                  data_da_entrada("§300 · Coisa · 30/09/2026") == datetime.date(2026, 9, 30)))
    casos.append(("título sem data devolve None", data_da_entrada("Coisa qualquer") is None))
    casos.append(("data impossível não quebra", data_da_entrada("§1 · x · 31/02/2026") is None))
    casos.append((f"o teto é de {TETO_DE_PALAVRAS} palavras", TETO_DE_PALAVRAS == 80))

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
    ruins = problemas(CHANGELOG.read_text(encoding="utf-8"), hoje_editorial())
    if ruins:
        print("✗ CHANGELOG:")
        for r in ruins:
            print("   -", r)
        return 1
    print(f"✓ CHANGELOG OK — entradas a partir de {VALE_A_PARTIR_DE.strftime('%d/%m/%Y')} com "
          f"chave por data e PR e no máximo {TETO_DE_PALAVRAS} palavras.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
