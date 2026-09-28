#!/usr/bin/env python3
"""
verificar_marcadores_de_conflito.py
===================================
Nenhum arquivo versionado carrega marcador de conflito de merge.

POR QUE ESTE PORTÃO EXISTE
--------------------------
Em 28/09/2026 o `CHANGELOG.md` foi commitado **duas vezes** com `<<<<<<<`, `=======` e `>>>>>>>`
dentro. A causa não é distração: `git add -A` marca o caminho como **resolvido** mesmo quando o
conteúdo ainda tem os marcadores, e `git commit` então aceita sem reclamar. Quem resolve conflito em
lote — e uma união de `CHANGELOG.md` em ramo que atravessa vários PRs é exatamente isso — não recebe
aviso nenhum.

O portão é barato e cobre o repositório inteiro. Ele olha os arquivos **rastreados pelo git**, ignora
o que é binário e se anuncia pelo caminho e pela linha, para que o conserto seja imediato.

USO
  python3 scripts/verificar_marcadores_de_conflito.py
  python3 scripts/verificar_marcadores_de_conflito.py --autoteste
"""
import pathlib
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]

# `=======` sozinho aparece em texto legítimo (sublinhado de título em Markdown, régua em docstring),
# então ele NÃO entra sozinho: o que acusa é a abertura e o fechamento, que não têm uso legítimo.
MARCADORES = ("<<<<<<< ", ">>>>>>> ")

# O próprio portão fala dos marcadores para explicar o que procura; a docstring dele está aqui dentro.
EXCECOES = {"scripts/verificar_marcadores_de_conflito.py"}


def arquivos_rastreados() -> list:
    saida = subprocess.run(["git", "ls-files", "-z"], cwd=RAIZ, capture_output=True, text=True)
    return [c for c in saida.stdout.split("\0") if c]


def achar(caminhos: list, ler=None) -> list:
    """Devolve [(caminho, linha, marcador)]. `ler` é injetável para o autoteste."""
    def ler_arquivo(rel):
        p = RAIZ / rel
        try:
            return p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None        # binário ou ilegível: não é onde marcador de merge se esconde
    ler = ler or ler_arquivo
    achados = []
    for rel in caminhos:
        if rel in EXCECOES:
            continue
        texto = ler(rel)
        if texto is None:
            continue
        for n, linha in enumerate(texto.split("\n"), 1):
            for m in MARCADORES:
                if linha.startswith(m):
                    achados.append((rel, n, m.strip()))
    return achados


def autoteste() -> int:
    casos = []
    conteudo = {
        "limpo.md": "# título\n=======\ntexto normal\n",
        "sujo.md": "antes\n<<<<<<< HEAD\nnosso\n=======\ndeles\n>>>>>>> origin/main\ndepois\n",
        "binario.bin": None,
        "scripts/verificar_marcadores_de_conflito.py": "<<<<<<< HEAD\n",
    }
    achados = achar(list(conteudo), ler=lambda rel: conteudo.get(rel))

    casos.append(("acusa o arquivo com marcador", any(a[0] == "sujo.md" for a in achados)))
    casos.append(("acusa abertura e fechamento", len([a for a in achados if a[0] == "sujo.md"]) == 2))
    casos.append(("diz a linha", sorted(a[1] for a in achados if a[0] == "sujo.md") == [2, 6]))
    casos.append(("`=======` sozinho não acusa (sublinhado de Markdown é legítimo)",
                  not any(a[0] == "limpo.md" for a in achados)))
    casos.append(("binário ilegível é ignorado", not any(a[0] == "binario.bin" for a in achados)))
    casos.append(("o próprio portão está na exceção",
                  not any(a[0].endswith("verificar_marcadores_de_conflito.py") for a in achados)))
    casos.append(("repositório limpo devolve lista vazia",
                  achar(["limpo.md"], ler=lambda rel: conteudo.get(rel)) == []))

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
    achados = achar(arquivos_rastreados())
    if achados:
        print("✗ MARCADORES DE CONFLITO: arquivo versionado com merge não resolvido:")
        for rel, n, m in achados[:40]:
            print(f"   - {rel}:{n} — {m}")
        print("   `git add` marca como resolvido mesmo com os marcadores dentro; una os dois lados e "
              "confira pela ausência de marcador.")
        return 1
    print(f"✓ MARCADORES OK — nenhum dos {len(arquivos_rastreados())} arquivos versionados tem merge "
          f"não resolvido.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
