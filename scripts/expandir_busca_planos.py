#!/usr/bin/env python3
"""Expande os comandos da busca de planos municipais em uma matriz de grupos de UF.

Regime de prioridade (editoria, 22/10/2026), HANDOVER_REGIME_DE_PRIORIDADE §6.1: a busca de planos
corria em UM job por rodada, em série por município, e a troca de `comandos` num ramo `coleta-dia/*`
era o único jeito de pedi-la. O gargalo é tempo de runner, não sessão. `busca_planos.yml` dispara um
job por grupo de UF e este módulo, que tem um dono só para a lista dos grupos, diz o que cada job roda.

Nos comandos (um por linha, como em `_coletor.yml`):
  `{UF}`   a linha repete-se uma vez por UF do grupo      (consultar_querido_diario.py --uf {UF})
  `{UFS}`  a linha recebe as UFs do grupo, separadas por vírgula   (descobrir_planos.py --uf {UFS})
  sem marcador: a linha não se parte por UF e roda uma vez só, no primeiro grupo escolhido.

Uso:
  python3 scripts/expandir_busca_planos.py --grupos todos|N,NE1,... < comandos > matriz.json
  python3 scripts/expandir_busca_planos.py --autoteste
Função pura: não escreve, não vai à rede.
"""
from __future__ import annotations

import json
import sys

GRUPOS = {
    "N": ("AC", "AM", "AP", "PA", "RO", "RR", "TO"),
    "NE1": ("MA", "PI", "CE", "RN", "PB"),
    "NE2": ("PE", "AL", "SE", "BA"),
    "CO": ("DF", "GO", "MT", "MS"),
    "SE": ("SP", "RJ", "MG", "ES"),
    "S": ("PR", "SC", "RS"),
}


def escolher(grupos: str) -> list:
    """`todos` ou uma lista de nomes de grupo; nome desconhecido é erro, não grupo vazio."""
    pedido = [g.strip() for g in (grupos or "todos").split(",") if g.strip()]
    if pedido in ([], ["todos"]):
        return list(GRUPOS)
    erro = [g for g in pedido if g not in GRUPOS]
    if erro:
        raise ValueError(f"grupo desconhecido: {', '.join(erro)} (valem: {', '.join(GRUPOS)})")
    return list(dict.fromkeys(pedido))


def expandir(comandos: str, grupos: str = "todos") -> list:
    """A matriz: um item `{grupo, ufs, comandos}` por grupo que ficou com algum comando."""
    nomes = escolher(grupos)
    linhas = [l.strip() for l in (comandos or "").splitlines()]
    linhas = [l for l in linhas if l and not l.startswith("#")]
    matriz = []
    for i, nome in enumerate(nomes):
        ufs = GRUPOS[nome]
        saida = []
        for l in linhas:
            if "{UF}" in l:
                saida += [l.replace("{UF}", u) for u in ufs]
            elif "{UFS}" in l:
                saida.append(l.replace("{UFS}", ",".join(ufs)))
            elif i == 0:
                saida.append(l)
        if saida:
            matriz.append({"grupo": nome, "ufs": ",".join(ufs), "comandos": "\n".join(saida)})
    return matriz


def autoteste() -> int:
    falhas = []

    from _casos import ok_de
    ok = ok_de(falhas)

    todas = [u for g in GRUPOS.values() for u in g]
    ok("os seis grupos cobrem as 27 UFs, cada uma uma vez", sorted(todas) == sorted(set(todas)) and len(todas) == 27)
    m = expandir("x.py --uf {UF}\ny.py --uf {UFS}\nz.py\n# nota\n")
    ok("seis jobs, um por grupo", [i["grupo"] for i in m] == list(GRUPOS))
    ok("{UF} repete a linha por UF do grupo", m[5]["comandos"].splitlines()[:3] == ["x.py --uf PR", "x.py --uf SC", "x.py --uf RS"])
    ok("{UFS} entrega a lista do grupo", "y.py --uf PR,SC,RS" in m[5]["comandos"])
    ok("linha sem marcador roda uma vez, só no primeiro grupo",
       sum(i["comandos"].splitlines().count("z.py") for i in m) == 1 and "z.py" in m[0]["comandos"])
    ok("comentário e linha vazia não viram comando", all("nota" not in i["comandos"] for i in m))
    ok("escolher grupos filtra e mantém a ordem pedida", [i["grupo"] for i in expandir("x.py --uf {UF}", "S,N")] == ["S", "N"])
    ok("grupo sem comando some da matriz", [i["grupo"] for i in expandir("z.py", "S,N")] == ["S"])
    try:
        escolher("Z")
        ok("grupo desconhecido é erro", False)
    except ValueError:
        ok("grupo desconhecido é erro", True)
    print("✓ AUTOTESTE OK" if not falhas else f"✗ {len(falhas)} falha(s)")
    return 1 if falhas else 0


def main(argv: list) -> int:
    if "--autoteste" in argv:
        return autoteste()
    grupos = argv[argv.index("--grupos") + 1] if "--grupos" in argv else "todos"
    try:
        matriz = expandir(sys.stdin.read(), grupos)
    except ValueError as e:
        print(f"::error::{e}", file=sys.stderr)
        return 2
    if not matriz:
        print("::error::nenhum comando para os grupos pedidos", file=sys.stderr)
        return 2
    print(json.dumps({"include": matriz}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
