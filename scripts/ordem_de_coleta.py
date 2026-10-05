#!/usr/bin/env python3
"""A ordem em que os municípios são percorridos — prioritários primeiro, com cursor persistido.

Item B do handover da corrente noturna (03/10/2026). **É ordem de coleta, não peso**: nada aqui
muda pontuação, critério ou categoria. Município fora das listas federais continua sendo buscado —
depois dos prioritários, e nunca "nunca".

A REGRA, nas palavras do handover:

    Toda coleta e busca por município percorre primeiro o conjunto prioritário e, só depois de
    esgotá-lo na rodada, expande para os demais municípios do mesmo estado e, por fim, dos demais
    estados.

    Ordem dentro de cada grupo: (a) nunca verificados; (b) verificação mais antiga; (c) maior
    população.

    Se a rodada terminar o conjunto prioritário, o tempo que sobrar vai para os demais; se não
    terminar, a próxima rodada continua de onde parou (cursor persistido), sem recomeçar do início.

O cursor é o que impede o pior desfecho possível desta regra: uma rodada curta percorrer sempre os
mesmos primeiros municípios da lista e os do fim nunca chegarem a ser consultados. Ele guarda o
último código atendido por grupo; a rodada seguinte começa depois dele e dá a volta.

USO (de dentro de um coletor)
    from ordem_de_coleta import ordenar, proximos, avancar_cursor
    alvos = proximos("busca_web", todos_os_municipios, limite=200)
    ...
    avancar_cursor("busca_web", alvos[-1]["ibge"])

    python3 scripts/ordem_de_coleta.py --autoteste
    python3 scripts/ordem_de_coleta.py --mostrar busca_web 10
"""
from __future__ import annotations

import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

ARQUIVO_CURSOR = "cursor_de_coleta.json"
GOV_CURSOR = ("Cursor da ORDEM DE COLETA por rotina (item B do handover de 03/10/2026). Guarda o "
              "último código IBGE atendido por grupo, para que a rodada seguinte continue de onde "
              "a anterior parou em vez de recomeçar pelo primeiro da lista — sem isso, uma rodada "
              "curta percorreria sempre os mesmos municípios e os do fim nunca seriam consultados.")


def grupo_do_municipio(m: dict, prioritarios: set, uf_em_foco: str = None) -> int:
    """0 = prioritário · 1 = mesmo estado de um prioritário em foco · 2 = os demais. Função pura."""
    cod = str(m.get("ibge") or m.get("codigo_ibge") or "").zfill(7)
    if cod in prioritarios:
        return 0
    if uf_em_foco and str(m.get("uf") or "").upper() == str(uf_em_foco).upper():
        return 1
    return 2


def chave_dentro_do_grupo(m: dict):
    """(a) nunca verificados · (b) verificação mais antiga · (c) maior população. Função pura.

    `None` em `verificado_em` é "nunca verificado", e vem primeiro de propósito: é o município
    sobre o qual o projeto não tem nada a dizer, e é dele que o leitor mais precisa.
    """
    verificado = str(m.get("verificado_em") or "")
    nunca = 0 if not verificado else 1
    pop = -int(m.get("populacao") or 0)
    return (nunca, verificado, pop, str(m.get("ibge") or ""))


def ordenar(municipios: list, prioritarios: set, uf_em_foco: str = None) -> list:
    """A lista na ordem de coleta. Função pura — é ela que o autoteste exercita."""
    return sorted(municipios,
                  key=lambda m: (grupo_do_municipio(m, prioritarios, uf_em_foco),
                                 chave_dentro_do_grupo(m)))


def a_partir_do_cursor(ordenados: list, cursor: str, limite: int) -> list:
    """Os próximos `limite` depois do cursor, dando a volta no fim da lista. Função pura."""
    if not ordenados:
        return []
    if not cursor:
        return ordenados[:limite]
    codigos = [str(m.get("ibge") or "") for m in ordenados]
    try:
        i = codigos.index(str(cursor)) + 1
    except ValueError:
        i = 0
    girada = ordenados[i:] + ordenados[:i]
    return girada[:limite]


def _autoteste() -> int:
    falhas = []
    # O total era um literal e envelhecia calado: dizia cobrir mais casos do que
    # cobre, ou menos. Agora e contado.
    _casos_contados = []

    def ok(nome, cond):
        _casos_contados.append(nome)
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    P = {"0000001", "0000002"}
    muns = [
        {"ibge": "0000003", "uf": "SP", "populacao": 100, "verificado_em": "2026-09-01"},
        {"ibge": "0000001", "uf": "SP", "populacao": 10, "verificado_em": "2026-09-30"},
        {"ibge": "0000002", "uf": "BA", "populacao": 20, "verificado_em": None},
        {"ibge": "0000004", "uf": "BA", "populacao": 999, "verificado_em": None},
    ]
    o = [m["ibge"] for m in ordenar(muns, P)]
    ok("prioritários vêm primeiro", o[:2] == ["0000002", "0000001"])
    ok("dentro do grupo, nunca verificado vem antes do verificado",
       o.index("0000002") < o.index("0000001"))
    ok("não prioritário nunca verificado vem antes do verificado",
       o.index("0000004") < o.index("0000003"))
    ok("sem prioritário em foco, os demais ficam no fim",
       o[-2:] == ["0000004", "0000003"])

    o_foco = [m["ibge"] for m in ordenar(muns, P, uf_em_foco="BA")]
    ok("com UF em foco, o não prioritário daquela UF sobe",
       o_foco.index("0000004") < o_foco.index("0000003"))

    antigos = [{"ibge": "1", "verificado_em": "2026-01-01"}, {"ibge": "2", "verificado_em": "2026-09-01"}]
    ok("verificação mais antiga primeiro",
       [m["ibge"] for m in ordenar(antigos, set())] == ["1", "2"])
    pops = [{"ibge": "1", "verificado_em": "2026-01-01", "populacao": 10},
            {"ibge": "2", "verificado_em": "2026-01-01", "populacao": 99}]
    ok("empate na data, maior população primeiro",
       [m["ibge"] for m in ordenar(pops, set())] == ["2", "1"])

    ordenados = [{"ibge": str(i)} for i in range(1, 6)]
    ok("sem cursor, começa do início",
       [m["ibge"] for m in a_partir_do_cursor(ordenados, "", 2)] == ["1", "2"])
    ok("com cursor, continua depois dele",
       [m["ibge"] for m in a_partir_do_cursor(ordenados, "2", 2)] == ["3", "4"])
    ok("no fim da lista, dá a volta",
       [m["ibge"] for m in a_partir_do_cursor(ordenados, "5", 2)] == ["1", "2"])
    ok("cursor desconhecido começa do início",
       [m["ibge"] for m in a_partir_do_cursor(ordenados, "99", 1)] == ["1"])
    ok("lista vazia devolve vazio", a_partir_do_cursor([], "", 5) == [])
    ok("limite maior que a lista devolve a lista",
       len(a_partir_do_cursor(ordenados, "", 50)) == 5)
    ok("a ordem é estável entre chamadas", ordenar(muns, P) == ordenar(muns, P))
    ok("a governança do cursor explica por que ele existe",
       "recomeçar pelo primeiro" in GOV_CURSOR)

    import dis
    nomes = set()
    for nome_obj, obj in list(globals().items()):
        if nome_obj in ("_autoteste", "main", "proximos", "avancar_cursor", "prioritarios_de_disco"):
            continue
        codigo = getattr(obj, "__code__", None)
        if codigo is not None:
            nomes |= {i.argval for i in dis.get_instructions(codigo) if isinstance(i.argval, str)}
    ok("trava estrutural: as funções de ordem não escrevem",
       not ({"gravar", "gravar_em", "write_text"} & nomes))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else f"✓ AUTOTESTE OK — {len(_casos_contados)} casos, sem rede e sem escrita.")
    return 1 if falhas else 0


# ── as portas que os coletores usam (estas leem e escrevem) ─────────────────────────────────
def prioritarios_de_disco() -> set:
    """O conjunto prioritário gravado por `gerar_prioridade_municipios.py`."""
    from coletores_base import ler
    return set((ler("prioridade_municipios.json") or {}).get("municipios") or {})


def proximos(rotina: str, municipios: list, limite: int = 200, uf_em_foco: str = None) -> list:
    """Os próximos municípios que ESTA rotina deve percorrer, na ordem e a partir do cursor."""
    from coletores_base import ler
    cursores = (ler(ARQUIVO_CURSOR) or {}).get("cursores") or {}
    ordenados = ordenar(municipios, prioritarios_de_disco(), uf_em_foco)
    return a_partir_do_cursor(ordenados, cursores.get(rotina), limite)


def avancar_cursor(rotina: str, ultimo_ibge: str) -> None:
    """Guarda o último código atendido por esta rotina."""
    from coletores_base import gravar, ler, hoje_editorial
    doc = ler(ARQUIVO_CURSOR) or {"_governanca": GOV_CURSOR, "cursores": {}, "em": {}}
    doc.setdefault("_governanca", GOV_CURSOR)
    doc.setdefault("cursores", {})[rotina] = str(ultimo_ibge or "")
    doc.setdefault("em", {})[rotina] = hoje_editorial().isoformat()
    gravar(ARQUIVO_CURSOR, doc)


def main() -> int:
    if "--autoteste" in sys.argv:
        return _autoteste()
    from coletores_base import ler
    if "--mostrar" in sys.argv:
        i = sys.argv.index("--mostrar")
        rotina = sys.argv[i + 1]
        quantos = int(sys.argv[i + 2]) if len(sys.argv) > i + 2 else 10
        ref = ler("municipios_ibge_referencia.json") or []
        pop = ler("populacao_censo2022.json") or {}
        muns = [{"ibge": str(m["codigo_ibge"]).zfill(7), "uf": m["uf"],
                 "populacao": pop.get(str(m["codigo_ibge"]).zfill(7), 0)} for m in ref]
        alvos = proximos(rotina, muns, quantos)
        pr = prioritarios_de_disco()
        for m in alvos:
            print(f"  {m['ibge']} {m['uf']} "
                  + ("prioritário" if m["ibge"] in pr else "—"))
        print(f"{len(alvos)} alvo(s) para a rotina {rotina!r}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
