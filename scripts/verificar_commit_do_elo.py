#!/usr/bin/env python3
"""
scripts/verificar_commit_do_elo.py — nenhum workflow comita pasta inteira neste repositório
=============================================================================================
Item 1.1 do `HANDOVER_noite_confiavel_parte2_06-10-2026.md`: "**Proibido** em qualquer workflow:
`git add -A`, `git add .`, `git add <pasta>/`. Portão de PR reprova a ocorrência".

POR QUE
-------
`config/escritores.json` diz quem pode escrever cada arquivo, e a regra estava **registrada e não
aplicada**: todo elo terminava com um `git add` de pasta e levava junto arquivo de outro elo. O
conflito que isso cria descartou **364 minutos de coleta** na noite de 05→06/10 — 100 nos diários,
em `data/saude_pipeline.json`, e 136 + 128 na busca web, em `data/pistas_revisao.json`,
`docs/FILA_PISTAS.md` e `docs/MANIFEST_SHA256.txt`. Nenhum dos quatro é arquivo de quem os perdeu.

Quem comita é `scripts/commit_do_elo.py`, que lê a declaração. Este portão existe para o atalho não
voltar: regra sem portão é esquecimento com data marcada.

O QUE ELE NÃO COBRA, E POR QUÊ
-------------------------------
`git add` dentro de um clone do repositório PRIVADO da editoria. Vários workflows copiam relatório
para `/tmp/registro` ou `/tmp/reg` e comitam lá; `config/escritores.json` não governa aquele
repositório, e exigir o ajudante ali seria exigir que ele respondesse por um arquivo que não
conhece. O portão reconhece o caso pelo `cd` para fora da árvore, no mesmo bloco `run:`.

USO
  python3 scripts/verificar_commit_do_elo.py --autoteste
  python3 scripts/verificar_commit_do_elo.py
"""
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
WORKFLOWS = RAIZ / ".github" / "workflows"

# `git add -A`, `git add .`, `git add <pasta>/` — com ou sem opções antes do caminho.
_RE_LARGO = re.compile(r"\bgit\s+add\b(?P<resto>[^\n;&|]*)")
_RE_FORA_DA_ARVORE = re.compile(r"\bcd\s+(/tmp/\S+|\$\{?RUNNER_TEMP\}?\S*)")


def e_add_largo(resto: str) -> bool:
    """O que vem depois de `git add` é pasta inteira ou tudo? Função pura.

    `git add -- caminho/arquivo.json` não é largo; `git add -A data/` é. A diferença que importa é
    o ALVO: se algum alvo é `.`, `-A`/`--all` sem caminho, ou termina em `/`, ele varre.
    """
    alvos = [a for a in str(resto or "").split() if a]
    if not alvos:
        return True                     # `git add` pelado adiciona tudo rastreado
    so_opcoes = all(a.startswith("-") for a in alvos)
    if so_opcoes:
        return True
    for alvo in alvos:
        if alvo in ("--", "-u", "--update", "-A", "--all", "-f", "--force"):
            continue
        if alvo.startswith("-"):
            continue
        if alvo in (".", "*") or alvo.endswith("/") or alvo.endswith("/*"):
            return True
    return False


# `HEAD:main` escrito a mão: o workflow grava na `main` esteja onde estiver.


def destino_fixo(linha: str) -> bool:
    """A linha empurra para a `main` por nome, em vez do ramo em que roda? Função pura.

    Causa B de 06/10/2026: `_coletor.yml` tinha `git push … HEAD:main` fixo, então o elo rodando no
    ramo `ensaio` tentava gravar na `main` — de dia, contra a regra de 27/09. O ensaio não era
    isolado coisa nenhuma; só não estragou a `main` porque o arquivo passou de 100 MB e o GitHub
    recusou o push por outro motivo.
    """
    sem_comentario = str(linha or "").split("#")[0]
    if "HEAD:main" not in sem_comentario:
        return False
    # `HEAD:${{ ... }}` é o certo e não casa com o literal; o que resta é o nome escrito à mão.
    return True


def blocos_run(texto: str) -> list:
    """Os blocos `run:` do workflow, como listas de linhas. Função pura.

    Grosseiro de propósito: um bloco começa em `run:` e vai até a linha seguinte com menos recuo
    que a primeira linha de corpo. É o suficiente para saber se o `cd` para fora da árvore está no
    MESMO bloco do `git add` — que é a única pergunta que este portão faz sobre estrutura.
    """
    linhas = str(texto or "").split("\n")
    fora, i = [], 0
    while i < len(linhas):
        if re.search(r"^\s*(-\s+)?run:\s*\|?\s*$", linhas[i]) or re.search(r"^\s*(-\s+)?run:\s+\S",
                                                                           linhas[i]):
            recuo = len(linhas[i]) - len(linhas[i].lstrip())
            bloco, j = [linhas[i]], i + 1
            while j < len(linhas):
                atual = linhas[j]
                if atual.strip() and (len(atual) - len(atual.lstrip())) <= recuo:
                    break
                bloco.append(atual)
                j += 1
            fora.append(bloco)
            i = j
            continue
        i += 1
    return fora


def problemas_do_texto(nome: str, texto: str) -> list:
    """As ocorrências proibidas num workflow. Função pura."""
    fora = []
    for bloco in blocos_run(texto):
        corpo = "\n".join(bloco)
        fora_da_arvore = bool(_RE_FORA_DA_ARVORE.search(corpo))
        for linha in bloco:
            sem_comentario = linha.split("#")[0]
            m = _RE_LARGO.search(sem_comentario)
            if not m or not e_add_largo(m.group("resto")):
                continue
            if fora_da_arvore:
                continue               # clone do repositório privado: outra árvore, outra regra
            fora.append(f"{nome}: `{linha.strip()[:100]}` — comita pasta inteira. "
                        f"Use `python3 scripts/commit_do_elo.py <elo>`.")
    # O destino do push é outra pergunta, e ela vale em TODO bloco, com `cd` ou sem: empurrar para a
    # `main` por nome é empurrar para a `main` mesmo rodando no ramo `ensaio`.
    for n, linha in enumerate(str(texto or "").splitlines(), start=1):
        if destino_fixo(linha):
            fora.append(f"{nome}:{n}: `HEAD:main` escrito à mão — o workflow grava na `main` "
                        f"esteja no ramo em que estiver. Use o ramo em que ele roda.")
    return fora


def _autoteste() -> int:
    falhas, contados = [], []

    def ok(nome, cond):
        contados.append(nome)
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    ok("`-A` com pasta é largo", e_add_largo(" -A data/"))
    ok("`.` é largo", e_add_largo(" ."))
    ok("pasta com barra é larga", e_add_largo(" data/ docs/"))
    ok("`git add` pelado é largo", e_add_largo(""))
    ok("só opções é largo", e_add_largo(" -A"))
    ok("arquivo nomeado não é largo", e_add_largo(" -- data/municipios.json") is False)
    ok("dois arquivos nomeados não é largo", e_add_largo(" a.json b.json") is False)
    ok("glob de pasta é largo", e_add_largo(" data/*"))

    yml = ("jobs:\n  x:\n    steps:\n      - name: comitar\n        run: |\n"
           "          git add -A data/\n          git commit -m x\n")
    ok("o add largo é acusado", problemas_do_texto("a.yml", yml) != [])
    ok("a mensagem diz o arquivo", "a.yml:" in problemas_do_texto("a.yml", yml)[0])

    privado = ("jobs:\n  x:\n    steps:\n      - run: |\n"
               "          git clone ... /tmp/reg\n"
               "          cd /tmp/reg && git add -A && git commit -m x\n")
    ok("add dentro do clone privado não é acusado", problemas_do_texto("b.yml", privado) == [])

    dois = ("jobs:\n  x:\n    steps:\n      - run: |\n          cd /tmp/reg && git add -A\n"
            "      - run: |\n          git add -A data/\n")
    ok("o `cd` de um bloco não protege o outro", len(problemas_do_texto("c.yml", dois)) == 1)

    ajudante = ("jobs:\n  x:\n    steps:\n      - run: |\n"
                "          python3 scripts/commit_do_elo.py diarios --mensagem x\n")
    ok("quem usa o ajudante passa", problemas_do_texto("d.yml", ajudante) == [])
    ok("`HEAD:main` escrito a mão é acusado", destino_fixo("git push origin HEAD:main"))
    ok("destino pelo ramo que roda passa",
       not destino_fixo("git push origin \"HEAD:${{ github.ref_name }}\""))
    ok("`HEAD:main` em comentário não é acusado", not destino_fixo("# nunca use HEAD:main"))
    ok("linha sem push passa", not destino_fixo("echo main"))
    ok("o portão acusa o destino fixo no workflow inteiro",
       any("HEAD:main" in x for x in problemas_do_texto(
           "a.yml", "jobs:\n  x:\n    steps:\n      - run: |\n          git push o HEAD:main\n")))
    ok("add em comentário não é acusado",
       problemas_do_texto("e.yml", "jobs:\n  x:\n    steps:\n      - run: |\n"
                                   "          # nao use git add -A aqui\n") == [])

    import dis
    nomes = set()
    for nome_obj, obj in list(globals().items()):
        if nome_obj in ("_autoteste", "main"):
            continue
        if getattr(obj, "__module__", None) not in (__name__, None):
            continue
        codigo = getattr(obj, "__code__", None)
        if codigo is not None:
            nomes |= {i.argval for i in dis.get_instructions(codigo) if isinstance(i.argval, str)}
    ok("trava estrutural: as funções puras não leem disco nem escrevem",
       not ({"read_text", "write_text", "urlopen"} & nomes))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else f"✓ AUTOTESTE OK — {len(contados)} casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def main(argv: list) -> int:
    if "--autoteste" in argv:
        return _autoteste()
    fora, n = [], 0
    for arq in sorted(WORKFLOWS.glob("*.yml")):
        n += 1
        fora += problemas_do_texto(arq.name, arq.read_text(encoding="utf-8"))
    if fora:
        print(f"✗ COMMIT DO ELO: {len(fora)} ocorrência(s) de `git add` de pasta inteira:")
        for x in fora:
            print("   - " + x)
        print("   A regra é `config/escritores.json`, e quem a aplica é "
              "`scripts/commit_do_elo.py`. Pasta inteira leva arquivo de outro elo junto.")
        return 1
    print(f"✓ COMMIT DO ELO OK — {n} workflow(s); nenhum comita pasta inteira desta árvore.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
