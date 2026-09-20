#!/usr/bin/env python3
"""Portão (§123): toda UF do cadastro federal tem posição determinística na fila da varredura.

O que trava. `data/cadastro_prioritarios.json` traz duas estruturas que precisam concordar:
`por_uf` (os 27 estados, com o percentual de municípios no Cadastro Nacional de Municípios
Suscetíveis) e `ordem_prioridade_uf_por_percentual` (a lista curada que decide em que UF a
varredura de diários municipais entra primeiro). Em 21/09/2026 a lista tinha 26 entradas: PI
estava em `por_uf` com pct 21,0 e fora da ordem. Quem ficasse de fora caía num rank fixo (99),
o que punha a UF no fim da fila por acidente de implementação, não por decisão de método — e
sem nenhum sinal: a varredura rodava verde com 224 municípios do Piauí sempre por último.

Este portão não exige que a lista curada nomeie as 27 — essa é decisão editorial, e o
percentual não é o único critério (a lista vigente não é monotônica em pct). Ele exige que
`ordem_prioridade()` produza uma fila **total e determinística**: nenhuma UF do cadastro pode
acabar num balde de ordem indefinida, e duas execuções sobre o mesmo dado devem dar a mesma
fila. Se a lista curada omitir uma UF, o coletor a posiciona pelo percentual do próprio
cadastro, logo após as UFs nomeadas.

Uso: python3 scripts/testar_ordem_prioridade_ufs.py
"""
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from coletar_diarios_municipais import ordem_prioridade  # noqa: E402

UFS_BRASIL = {"AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT",
              "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO"}


def carregar():
    cadastro = json.loads((RAIZ / "data" / "cadastro_prioritarios.json").read_text(encoding="utf-8"))
    municipios = json.loads((RAIZ / "data" / "verificacao_municipal.json").read_text(encoding="utf-8"))
    por_cod = {m["ibge"]: {"uf": m["uf"]} for m in municipios}
    return cadastro, por_cod


def main() -> int:
    cadastro, por_cod = carregar()
    por_uf = cadastro.get("por_uf") or {}
    ordem_curada = cadastro.get("ordem_prioridade_uf_por_percentual") or []
    falhas = []

    # 1. O cadastro descreve as 27 UFs.
    faltam_cadastro = sorted(UFS_BRASIL - set(por_uf))
    if faltam_cadastro:
        falhas.append(f"por_uf não cobre as 27 UFs — ausentes: {', '.join(faltam_cadastro)}")

    # 2. Toda UF do cadastro recebe posição na fila; nenhuma cai num balde indefinido.
    fila = ordem_prioridade(por_cod, cadastro, {})
    ufs_na_fila = []
    for cod in fila:
        uf = por_cod[cod]["uf"]
        if uf not in ufs_na_fila:
            ufs_na_fila.append(uf)
    faltam_fila = sorted(set(por_uf) - set(ufs_na_fila))
    if faltam_fila:
        falhas.append(f"UF do cadastro fora da fila da varredura: {', '.join(faltam_fila)}")

    # 3. As UFs aparecem em blocos contíguos — uma UF não pode ficar partida na fila,
    #    o que indicaria rank empatado entre estados diferentes.
    vistos, partidas, anterior = set(), [], None
    for cod in fila:
        uf = por_cod[cod]["uf"]
        if uf != anterior:
            if uf in vistos:
                partidas.append(uf)
            vistos.add(uf)
            anterior = uf
    if partidas:
        falhas.append(f"UF com bloco partido na fila (rank empatado): {', '.join(sorted(set(partidas)))}")

    # 4. Determinismo: a mesma entrada produz a mesma fila.
    if ordem_prioridade(por_cod, cadastro, {}) != fila:
        falhas.append("fila não determinística: duas execuções sobre o mesmo dado divergiram")

    # 5. Negativo: uma UF omitida da lista curada precisa entrar pelo percentual,
    #    depois das nomeadas, e não empatar com as demais ausentes. As ausentes entram no
    #    dicionário em ordem INVERSA ao percentual (GO 10,2 antes de PI 21,0) — com o rank
    #    fixo antigo o empate se resolvia pela ordem de iteração e sairia GO, PI; só o
    #    posicionamento por percentual produz PI, GO.
    por_teste = {"1": {"uf": "SC"}, "2": {"uf": "GO"}, "3": {"uf": "PI"}, "4": {"uf": "RS"}}
    cad_teste = {"ordem_prioridade_uf_por_percentual": ["SC", "RS"],
                 "por_uf": {"SC": {"pct": 73.9}, "RS": {"pct": 41.4}, "GO": {"pct": 10.2}, "PI": {"pct": 21.0}}}
    esperado = ["1", "4", "3", "2"]
    if ordem_prioridade(por_teste, cad_teste, {}) != esperado:
        falhas.append("UF ausente da lista curada não foi posicionada pelo percentual do cadastro")

    if falhas:
        print("✗ ORDEM DE PRIORIDADE: a fila da varredura não é total e determinística:")
        for f in falhas:
            print(f"  · {f}")
        return 1

    nomeadas = [u for u in ordem_curada if u in por_uf]
    ausentes = [u for u in ufs_na_fila if u not in ordem_curada]
    nota = f"; {len(ausentes)} posicionada(s) pelo percentual ({', '.join(ausentes)})" if ausentes else ""
    print(f"✓ ORDEM DE PRIORIDADE OK — {len(ufs_na_fila)} UFs em blocos contíguos, fila determinística: "
          f"{len(nomeadas)} nomeada(s) na lista curada{nota}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
