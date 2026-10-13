#!/usr/bin/env python3
"""Medida do código — linha de base da consolidação (HANDOVER_CONSOLIDACAO_13-10-2026, item 1).

Imprime linhas de .py/.js por pasta, os maiores scripts, funções de mesmo nome em arquivos
distintos (candidatas a um lugar só) e os portões por perfil. Informação, não portão: não reprova.

  python3 scripts/medir_codigo.py            # imprime
  python3 scripts/medir_codigo.py --gravar   # regrava docs/MEDIDA_DO_CODIGO.md
"""
import collections
import pathlib
import re
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
DOC = RAIZ / "docs" / "MEDIDA_DO_CODIGO.md"
DEF = re.compile(r"^(?:def|async def)\s+([A-Za-z_]\w*)\s*\(|^(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(",
                 re.M)
COMUNS = {"main", "autoteste", "_autoteste", "t", "ok", "ler", "gravar", "rodar"}


def arquivos() -> list:
    saida = subprocess.run(["git", "ls-files", "*.py", "*.js"], cwd=RAIZ, capture_output=True,
                           text=True, check=True).stdout.split()
    return sorted(p for p in saida if not p.startswith(("node_modules/", "evidencias/")))


def medir(caminhos: list, ler) -> dict:
    """Linhas por pasta, por arquivo e nomes de função repetidos entre arquivos. Função pura."""
    por_pasta, por_arquivo, onde = collections.Counter(), {}, collections.defaultdict(set)
    for c in caminhos:
        texto = ler(c)
        n = texto.count("\n") + (1 if texto and not texto.endswith("\n") else 0)
        por_arquivo[c] = n
        por_pasta[c.split("/")[0] if "/" in c else "(raiz)"] += n
        for m in DEF.finditer(texto):
            nome = m.group(1) or m.group(2)
            if nome not in COMUNS:
                onde[nome].add(c)
    repetidas = {k: sorted(v) for k, v in onde.items() if len(v) > 1}
    return {"arquivos": len(caminhos), "linhas": sum(por_arquivo.values()),
            "por_pasta": dict(por_pasta), "por_arquivo": por_arquivo, "repetidas": repetidas}


def portoes() -> collections.Counter:
    sys.path.insert(0, str(RAIZ / "scripts"))
    from portoes_locais import comandos_do_workflow
    c = collections.Counter()
    for grupo, cmd, _ in comandos_do_workflow():
        c[(grupo, "autoteste" if "--autoteste" in cmd else "portão")] += 1
    return c


def relatorio(m: dict, p: collections.Counter, workflows: int) -> str:
    L = ["# Medida do código", "",
         "Gerado por `python3 scripts/medir_codigo.py --gravar`. Linha de base da consolidação "
         "(meta: ≤ 50 mil linhas de .py/.js, mesma proteção).", "",
         f"- **{m['linhas']:,} linhas** em **{m['arquivos']} arquivos** .py/.js; "
         f"**{workflows} workflows**.".replace(",", "."),
         f"- **{sum(p.values())} comandos de portão**: "
         + ", ".join(f"{g}/{t} {n}" for (g, t), n in sorted(p.items())) + ".",
         f"- **{len(m['repetidas'])} nomes de função** definidos em mais de um arquivo.", "",
         "## Por pasta", "", "| pasta | linhas |", "|---|---:|"]
    L += [f"| `{k}` | {v} |" for k, v in sorted(m["por_pasta"].items(), key=lambda x: (-x[1], x[0]))]
    L += ["", "## Os 25 maiores", "", "| arquivo | linhas |", "|---|---:|"]
    maiores = sorted(m["por_arquivo"].items(), key=lambda x: (-x[1], x[0]))[:25]
    L += [f"| `{k}` | {v} |" for k, v in maiores]
    L += ["", "## Funções de mesmo nome em arquivos distintos (as 40 mais repetidas)", "",
          "| função | arquivos | onde |", "|---|---:|---|"]
    rep = sorted(m["repetidas"].items(), key=lambda x: (-len(x[1]), x[0]))[:40]
    L += [f"| `{k}` | {len(v)} | " + ", ".join(f"`{x}`" for x in v[:4])
          + (" …" if len(v) > 4 else "") + " |" for k, v in rep]
    return "\n".join(L) + "\n"


def _autoteste() -> int:
    fonte = {"a.py": "def f(x):\n    pass\ndef main():\n    pass\n",
             "scripts/b.py": "def f(y):\n    pass\n", "assets/c.js": "function f(){}\nfunction g(){}"}
    m = medir(sorted(fonte), fonte.get)
    casos = {"conta linhas por pasta": m["por_pasta"] == {"(raiz)": 4, "scripts": 2, "assets": 2},
             "acha a função repetida entre py e js": m["repetidas"] == {
                 "f": ["a.py", "assets/c.js", "scripts/b.py"]},
             "nome comum (main) não conta": "main" not in m["repetidas"]}
    for nome, ok in casos.items():
        print(("  ✓ " if ok else "  ✗ ") + nome)
    bom = all(casos.values())
    print("✓ AUTOTESTE OK" if bom else "✗ AUTOTESTE FALHOU")
    return 0 if bom else 1


def main() -> int:
    if "--autoteste" in sys.argv:
        return _autoteste()
    m = medir(arquivos(), lambda c: (RAIZ / c).read_text(encoding="utf-8", errors="replace"))
    texto = relatorio(m, portoes(), len(list((RAIZ / ".github" / "workflows").glob("*.yml"))))
    if "--gravar" in sys.argv:
        DOC.write_text(texto, encoding="utf-8", newline="\n")
        print(f"{DOC.relative_to(RAIZ)} regravado")
    else:
        print(texto)
    return 0


if __name__ == "__main__":
    sys.exit(main())
