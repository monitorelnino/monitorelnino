#!/usr/bin/env python3
"""Portão: todo script citado por um workflow existe na árvore.

ACHADO A1-25 (auditoria de 08/10/2026). `consolidar_noite.yml` chamava um script que não existia.
O elo rodava, o passo falhava, e o que falha num elo da noite não aparece em lugar nenhum até
alguém abrir o log — a corrente seguia "verde" com um passo morto dentro.

O defeito é barato de achar e barato de impedir: o nome do arquivo está no YAML e o arquivo está
no disco. Este portão compara os dois. Ele não executa nada, não baixa nada e não julga o que o
script faz.

O que ele cobre: `python3 <arquivo>.py`, `bash <arquivo>.sh` e `node <arquivo>.js` citados em
qualquer `.github/workflows/*.yml`, inclusive dentro do bloco `comandos:` que o `_coletor.yml`
reparte. Caminho com variável de ambiente (`$X/foo.py`) fica de fora de propósito: ele só se
resolve em execução, e adivinhar aqui produziria vermelho falso.

USO
    python3 scripts/verificar_scripts_dos_workflows.py
    python3 scripts/verificar_scripts_dos_workflows.py --autoteste
"""
from __future__ import annotations

import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
FLUXOS = RAIZ / ".github" / "workflows"
CITACAO = re.compile(r"(?:python3?|bash|sh|node)\s+([A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:py|sh|js))")


def citados(texto: str) -> list:
    """Os caminhos de script citados num YAML. Função pura, ordem estável e sem repetição."""
    fora, vistos = [], set()
    for caminho in CITACAO.findall(texto or ""):
        if caminho.startswith("-") or "$" in caminho or caminho in vistos:
            continue
        vistos.add(caminho)
        fora.append(caminho)
    return fora


def faltantes(mapa: dict, existe) -> list:
    """(workflow, caminho) de cada script citado que não existe. Função pura dado `existe`."""
    return [(w, c) for w, textos in sorted(mapa.items()) for c in citados(textos)
            if not existe(c)]


def declarados_em_listas() -> list:
    """Caminhos que `verificar_escritor_de_pista.py` declara em ESCRITORES e MANUTENCAO.

    09/10/2026: `scripts/migrar_pistas_para_o_esquema.py` estava declarado em MANUTENCAO desde
    06/10 e **não existia**. É o mesmo defeito do A1-25 por outra porta: a lista diz que aquele
    arquivo mexe na fila, e o arquivo não está lá. Declaração que aponta para o vazio não protege
    nada, e some da leitura de quem confia na lista.
    """
    import ast
    fonte = (RAIZ / "scripts" / "verificar_escritor_de_pista.py").read_text(encoding="utf-8")
    fora = []
    for nome in ("ESCRITORES", "MANUTENCAO"):
        if f"{nome} = (" not in fonte:
            continue
        bloco = fonte.split(f"{nome} = ", 1)[1].split(")", 1)[0] + ")"
        try:
            fora.extend(ast.literal_eval(bloco))
        except (SyntaxError, ValueError):
            continue
    return fora


def autoteste() -> int:
    falhas = []

    def ok(nome, cond):
        print(("  ok " if cond else "  FALHA ") + nome)
        if not cond:
            falhas.append(nome)

    ok("acha o script de um passo simples",
       citados("      - run: python3 scripts/a.py --x") == ["scripts/a.py"])
    ok("acha bash e node também",
       citados("bash scripts/b.sh\nnode scripts/c.js") == ["scripts/b.sh", "scripts/c.js"])
    ok("não repete o mesmo caminho",
       citados("python3 a.py\npython3 a.py") == ["a.py"])
    ok("caminho com variável fica de fora",
       citados("python3 $DIR/a.py") == [])
    ok("script ausente reprova",
       faltantes({"w.yml": "python3 scripts/nao_existe.py"}, lambda _c: False)
       == [("w.yml", "scripts/nao_existe.py")])
    ok("script presente passa",
       faltantes({"w.yml": "python3 scripts/existe.py"}, lambda _c: True) == [])
    ok("o workflow do defeito é lido de verdade",
       (FLUXOS / "consolidar_noite.yml").exists())
    ok("as listas de escritor de pista são lidas e apontam para arquivos reais",
       all((RAIZ / c).is_file() for c in declarados_em_listas()))
    ok("há declaração a conferir nas listas", len(declarados_em_listas()) >= 10)
    print(f"autoteste: {9 - len(falhas)}/9")
    return 1 if falhas else 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    mapa = {p.name: p.read_text(encoding="utf-8") for p in sorted(FLUXOS.glob("*.yml"))}
    fora = faltantes(mapa, lambda c: (RAIZ / c).is_file())
    total = sum(len(citados(t)) for t in mapa.values())
    declarados = declarados_em_listas()
    for c in declarados:
        if not (RAIZ / c).is_file():
            fora.append(("verificar_escritor_de_pista.py (ESCRITORES/MANUTENCAO)", c))
    total += len(declarados)
    if fora:
        print(f"VERMELHO: {len(fora)} script(s) citado(s) por workflow e ausente(s) na árvore:")
        for w, c in fora:
            print(f"  · {w} chama {c}, que não existe")
        return 1
    print(f"ok: {total} citação(ões) de script em {len(mapa)} workflow(s); todas existem na árvore")
    return 0


if __name__ == "__main__":
    sys.exit(main())
