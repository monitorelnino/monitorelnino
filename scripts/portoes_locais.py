#!/usr/bin/env python3
"""Roda os portões locais DERIVANDO a lista de .github/workflows/portoes.yml (§167, 23/09/2026).

POR QUE EXISTE. Até hoje havia três listas de portões que divergiam entre si: a do CLAUDE.md
(páginas + validar_workflows), a numerada do PROTOCOLO §3.3 (mistura página e dado) e a do
próprio portoes.yml, que é a única que reprova de verdade. Rodar um subconjunto coerente com
uma das listas e passar batido por um portão que só existe noutra custou um ciclo de CI em
23/09/2026 (verificar_seguranca.js: Action sem SHA fixado).

A correção não é escrever a lista uma quarta vez: é parar de escrevê-la. Este script lê o
workflow e roda o que ele roda, na ordem em que ele roda. Portão novo no CI passa a valer
aqui sem ninguém lembrar de copiar.

SAÍDA ENXUTA, DE PROPÓSITO. Imprime uma linha por portão (a última linha da saída dele, que
nos scripts do projeto é sempre o veredito). Só o portão que reprova mostra saída completa.
A suíte inteira em modo verboso são centenas de linhas de ✓ que não informam nada e custam
contexto caro quando lidas por um agente.

Uso: python3 scripts/portoes_locais.py [paginas|dados|tudo] [--verboso] [--ate N] [--listar]
  paginas  portões que rodam sempre no CI (não dependem de dado ter mudado)
  dados    portões condicionados a `dado_mudou` no workflow (inclui autotestes de coletor)
  tudo     os dois, na ordem do workflow (padrão)
"""
import re
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
WORKFLOW = RAIZ / ".github" / "workflows" / "portoes.yml"

# Passos que existem no workflow mas NÃO são portão: diagnóstico, preparo de ambiente,
# publicação de relatório. Casados pelo nome do passo, que é estável e legível.
PASSOS_IGNORADOS = re.compile(
    r"diagn[óo]stico|relat[óo]rio|detectar se a mudan|checkout|setup|instalar|depend[êe]ncias",
    re.IGNORECASE)

# Uma linha de `run:` só vira portão se começa por um destes. `for c in ...` cobre o laço de
# autotestes de coletor, que roda como uma linha de shell.
INICIOS = ("python3 ", "node ", "bash ", "for c in ")


def comandos_do_workflow():
    """[(grupo, comando)] na ordem do workflow. grupo ∈ {'paginas','dados'}.

    Classificação declarada: passo com `if: ... dado_mudou ...` é de dado; o resto é de
    página. É a mesma divisão que o CI faz, e por isso não inventa uma terceira semântica."""
    import yaml
    wf = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    job = next(iter(wf["jobs"].values()))
    saida = []
    for passo in job.get("steps", []):
        nome = passo.get("name") or ""
        run = passo.get("run")
        if not run or PASSOS_IGNORADOS.search(nome):
            continue
        grupo = "dados" if "dado_mudou" in str(passo.get("if", "")) else "paginas"
        for linha in run.splitlines():
            linha = linha.strip()
            if not linha or linha.startswith("#"):
                continue
            if linha.startswith(INICIOS):
                saida.append((grupo, linha))
    return saida


def rodar(cmd: str, verboso: bool) -> tuple:
    t0 = time.time()
    p = subprocess.run(cmd, shell=True, cwd=RAIZ, capture_output=True, text=True)
    saida = (p.stdout or "") + (p.stderr or "")
    linhas = [x for x in saida.splitlines() if x.strip()]
    veredito = linhas[-1] if linhas else "(sem saída)"
    return p.returncode, veredito, saida, time.time() - t0


def main() -> int:
    args = sys.argv[1:]
    verboso = "--verboso" in args
    listar = "--listar" in args
    grupo_pedido = next((a for a in args if a in ("paginas", "dados", "tudo")), "tudo")
    ate = None
    if "--ate" in args:
        ate = int(args[args.index("--ate") + 1])

    cmds = [(g, c) for g, c in comandos_do_workflow()
            if grupo_pedido == "tudo" or g == grupo_pedido][:ate]
    if listar:
        for i, (g, c) in enumerate(cmds, 1):
            print(f"{i:2}. [{g:7}] {c}")
        print(f"\n{len(cmds)} portão(ões) derivado(s) de {WORKFLOW.relative_to(RAIZ)}")
        return 0

    print(f"{len(cmds)} portão(ões) — derivados de {WORKFLOW.relative_to(RAIZ)}\n")
    falhou = None
    for i, (g, c) in enumerate(cmds, 1):
        rotulo = c if len(c) <= 52 else c[:49] + "..."
        print(f"{i:2}/{len(cmds)} [{g:7}] {rotulo:<52} ", end="", flush=True)
        rc, veredito, saida, dt = rodar(c, verboso)
        if rc == 0:
            print(f"✓ {dt:5.1f}s")
            if verboso:
                print(saida)
        else:
            print(f"✗ {dt:5.1f}s")
            print("\n--- saída do portão que reprovou ---")
            print(saida[-4000:])
            falhou = c
            break          # para no primeiro vermelho: o resto perde o sentido

    if falhou:
        print(f"\n✗ PORTÕES: parou em `{falhou}`. Nada sobe com portão vermelho.")
        return 1
    print(f"\n✓ PORTÕES OK — {len(cmds)} portão(ões) verdes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
