#!/usr/bin/env python3
"""Congela os três números do boletim da semana, por edição.

Handover do blog e da imprensa (03/10/2026). O boletim do blog e o ponteiro da Imprensa mostram os
MESMOS três números:

    municípios que decretaram emergência na semana
    municípios sob alerta do Cemaden
    casos prováveis de dengue na última semana fechada

Eles vêm do motor da semana (`data/imprensa/semana.json`), que por sua vez lê o instantâneo do topo
de cada página — nenhuma conta nova nasce aqui. O que este script faz é **congelar**: grava
`data/blog/boletins/<data>.json` com os números daquela edição, e `boletim_mais_recente.json` com a
última. A razão é de leitura: um boletim de três semanas atrás mostrando o número de hoje seria
outro documento, e quem cita a edição cita o que ela dizia.

USO
    python3 scripts/gerar_boletim.py
    python3 scripts/gerar_boletim.py --autoteste
"""
from __future__ import annotations

import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

# (id do cartão no motor da semana, rótulo do boletim)
TRES_NUMEROS = (
    ("decretos_na_semana", "municípios decretaram emergência na semana"),
    ("municipios_alerta_cemaden", "municípios sob alerta do Cemaden"),
    ("dengue_casos_se", "casos prováveis de dengue na última semana fechada"),
)
GOV = ("Boletim da semana, CONGELADO por edição (handover de 03/10/2026). Os três números vêm do "
       "motor da semana, que lê o instantâneo do topo de cada página — nenhuma conta nasce aqui. "
       "Congelar é o ponto: um boletim de semanas atrás mostrando o número de hoje seria outro "
       "documento, e quem cita a edição cita o que ela dizia.")


def numeros_do_boletim(semana: dict, tres=TRES_NUMEROS) -> list:
    """[{rotulo, valor, fonte, referencia}] para os três números. Função pura.

    Cartão sem dado **não vira zero**: ele sai do boletim, e a ausência fica no campo `sem_dado`.
    """
    por_id = {c.get("id"): c for c in (semana or {}).get("cartoes") or []}
    fora = []
    for ident, rotulo in tres:
        c = por_id.get(ident)
        if not c or c.get("sem_coleta") or c.get("valor") is None:
            continue
        valor = c["valor"]
        if isinstance(valor, (int, float)) and float(valor).is_integer():
            texto = f"{int(valor):,}".replace(",", ".")
        else:
            texto = str(valor)
        fora.append({"rotulo": rotulo, "valor": texto, "fonte": c.get("fonte"),
                     "referencia": c.get("referencia")})
    return fora


def sem_dado(semana: dict, tres=TRES_NUMEROS) -> list:
    """Os rótulos que ficaram sem dado nesta edição. Função pura."""
    presentes = {n["rotulo"] for n in numeros_do_boletim(semana, tres)}
    return [rotulo for _ident, rotulo in tres if rotulo not in presentes]


def _autoteste() -> int:
    falhas = []

    def ok(nome, cond):
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    semana = {"cartoes": [
        {"id": "decretos_na_semana", "valor": 69, "fonte": "Defesa Civil nacional",
         "referencia": "últimos 7 dias", "sem_coleta": False},
        {"id": "municipios_alerta_cemaden", "valor": 14, "fonte": "Cemaden", "sem_coleta": False},
        {"id": "dengue_casos_se", "valor": 8146, "fonte": "Ministério da Saúde (Sinan)",
         "referencia": "2026-33", "sem_coleta": False},
    ]}
    n = numeros_do_boletim(semana)
    ok("os três números saem do motor da semana", len(n) == 3)
    ok("o número vem formatado em pt-BR", n[2]["valor"] == "8.146")
    ok("o rótulo é o do boletim", n[0]["rotulo"].startswith("municípios decretaram"))
    ok("a fonte viaja com o número", n[1]["fonte"] == "Cemaden")
    ok("sem dado não entra, e fica declarado",
       len(numeros_do_boletim({"cartoes": [{"id": "decretos_na_semana", "sem_coleta": True}]})) == 0)
    ok("o que faltou é nomeado",
       "municípios sob alerta do Cemaden" in sem_dado({"cartoes": []}))
    ok("zero medido É publicado, e não tratado como ausência",
       numeros_do_boletim({"cartoes": [{"id": "decretos_na_semana", "valor": 0,
                                        "sem_coleta": False}]})[0]["valor"] == "0")
    ok("edição completa não declara ausência", sem_dado(semana) == [])

    import dis
    nomes = set()
    for nome_obj, obj in list(globals().items()):
        if nome_obj in ("_autoteste", "main"):
            continue
        codigo = getattr(obj, "__code__", None)
        if codigo is not None:
            nomes |= {i.argval for i in dis.get_instructions(codigo) if isinstance(i.argval, str)}
    ok("trava estrutural: as funções puras não escrevem",
       not ({"gravar", "gravar_em", "write_text"} & nomes))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else "✓ AUTOTESTE OK — 9 casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return _autoteste()
    from coletores_base import gravar, ler, hoje_editorial
    semana = ler("imprensa/semana.json") or {}
    hoje = hoje_editorial()
    edicao = hoje.strftime("%d/%m/%Y")
    numeros = numeros_do_boletim(semana)
    faltam = sem_dado(semana)
    doc = {"_governanca": GOV, "edicao": edicao, "gerado_em": hoje.isoformat(),
           "numeros": numeros, "sem_dado": faltam}
    # A pasta da edição pode não existir na primeira vez: `gravar` escreve atômico, e escrita
    # atômica precisa do diretório pronto.
    (RAIZ / "data" / "blog" / "boletins").mkdir(parents=True, exist_ok=True)
    gravar(f"blog/boletins/{hoje.isoformat()}.json", doc)
    gravar("blog/boletim_mais_recente.json", doc)
    print(f"→ boletim de {edicao}: {len(numeros)} número(s) congelado(s)"
          + (f"; sem dado: {', '.join(faltam)}" if faltam else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
