#!/usr/bin/env python3
"""Registra a faixa de cada unidade da federação, por edição, nos dois índices.

Por que existe (02/10/2026): o cartão "estados que mudaram de faixa no período", da edição para a
imprensa, estava declarado como lacuna — e a lacuna era real: `data/historico_mudancas.json` está
vazio, e sem série de faixa por data não há como dizer quem mudou **nem** dizer que ninguém mudou.
Faltava quem escrevesse a série.

Este script roda a cada publicação, depois do recálculo, e **acrescenta** uma linha por edição em
`data/historico_faixas.json` com a faixa de cada unidade no MARÉ Legal e no MARÉ Saúde. O arquivo
é **append-only**, como o log de buscas: edição já escrita nunca é reescrita, e duas execuções no
mesmo dia atualizam a linha do dia em vez de duplicá-la — a unidade do registro é a EDIÇÃO, não a
execução.

A partir da segunda edição registrada, o cartão da imprensa passa a ter lastro. Até lá ele continua
declarando a lacuna, agora com o motivo certo: a série começou, e ainda não tem dois pontos.

Uso:
    python3 scripts/registrar_faixas.py              # registra a edição de hoje
    python3 scripts/registrar_faixas.py --ensaio     # só imprime
    python3 scripts/registrar_faixas.py --autoteste  # funções puras, sem rede e sem escrita
"""
from __future__ import annotations

import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
ARQUIVO = "historico_faixas.json"
BANCO_PROIBIDO = {"estados.json", "saude_uf.json", "municipios.json", "indice.json",
                  "monitor_saude.json", "monitor_saude_v04.json"}


def faixa_do_total(registro: dict):
    """A faixa de um registro do índice: a publicada, ou a da régua canônica sobre `total`.

    Função pura. Devolve `None` quando não há total — e `None` é "não verificado", não é faixa.
    """
    if not isinstance(registro, dict):
        return None
    if registro.get("faixa"):
        return registro["faixa"]
    total = registro.get("total")
    if total is None:
        return None
    try:
        if str(RAIZ) not in sys.path:
            sys.path.insert(0, str(RAIZ))
        from gerar_monitor_saude import faixa as faixa_canonica
    except Exception:  # noqa: BLE001
        return None
    return faixa_canonica(float(total))


def faixas_de(indice: dict, saude: dict) -> dict:
    """{uf: {legal, saude}} com a faixa publicada em cada índice. Função pura.

    Unidade sem valor publicado entra como `None` — e `None` não é faixa: é "não verificado". A
    diferença importa no passo seguinte, porque entrar e sair de "não verificado" **não é** mudança
    de faixa, é mudança de cobertura.
    """
    fora = {}
    # `indice.json` é um mapa por sigla, direto, e publica `total` — não `faixa`. A faixa sai da
    # régua canônica do projeto (`gerar_monitor_saude.faixa`), e não de uma régua copiada aqui:
    # duas réguas é como uma delas fica velha sem ninguém ver.
    legal = (indice or {}).get("estados") or (indice or {}).get("uf") or indice or {}
    if isinstance(legal, list):
        legal = {x.get("uf"): x for x in legal if isinstance(x, dict)}
    saude_ufs = (saude or {}).get("ufs") or (saude or {}).get("uf") or {}
    for uf in sorted(set(legal) | set(saude_ufs)):
        if not isinstance(uf, str) or len(uf) != 2:
            continue
        a = legal.get(uf) or {}
        b = saude_ufs.get(uf) or {}
        fora[uf] = {"legal": faixa_do_total(a) if isinstance(a, dict) else None,
                    "saude": b.get("faixa") if isinstance(b, dict) else None}
    return fora


def acrescentar(historico: dict, data: str, faixas: dict) -> dict:
    """Acrescenta (ou atualiza) a linha da edição `data`. Função pura, append-only por edição.

    Nunca remove edição anterior: a série é o lastro do cartão, e série que encurta é a falha que
    o projeto já viu uma vez no log de buscas (§merge pela base comum).
    """
    h = dict(historico or {})
    edicoes = list(h.get("edicoes") or [])
    for i, e in enumerate(edicoes):
        if e.get("data") == data:
            edicoes[i] = {"data": data, "faixas": faixas}
            break
    else:
        edicoes.append({"data": data, "faixas": faixas})
    h["edicoes"] = sorted(edicoes, key=lambda e: e.get("data") or "")
    h["_governanca"] = (
        "Faixa de cada unidade da federação por edição, nos dois índices. Append-only: a unidade do "
        "registro é a EDIÇÃO, e edição já escrita não é reescrita por outra execução do mesmo dia. "
        "Serve ao cartão 'estados que mudaram de faixa' da edição para a imprensa. Entrar ou sair de "
        "'não verificado' não é mudança de faixa: é mudança de cobertura, e fica separado.")
    return h


def mudaram(historico: dict, indice_de: str = "legal") -> dict:
    """{'mudaram': [...], 'de_ate': (a, b)} entre as duas últimas edições. Função pura.

    Devolve `None` em `de_ate` quando não há duas edições: um ponto não é série, e "nenhum estado
    mudou" com um ponto só seria afirmação sem lastro.
    """
    edicoes = (historico or {}).get("edicoes") or []
    if len(edicoes) < 2:
        return {"mudaram": None, "de_ate": None, "motivo": "a série tem menos de duas edições"}
    antes, agora = edicoes[-2], edicoes[-1]
    lista = []
    for uf, v in sorted((agora.get("faixas") or {}).items()):
        a = ((antes.get("faixas") or {}).get(uf) or {}).get(indice_de)
        b = (v or {}).get(indice_de)
        # "não verificado" de um lado não é mudança de faixa: é cobertura, e não entra.
        if a is None or b is None:
            continue
        if a != b:
            lista.append({"uf": uf, "de": a, "para": b})
    return {"mudaram": lista, "de_ate": (antes.get("data"), agora.get("data")), "motivo": None}


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

    f = faixas_de({"estados": {"GO": {"faixa": "em construção"}, "SP": {"faixa": "avançado"}}},
                  {"ufs": {"GO": {"faixa": "consolidado"}, "DF": {"faixa": "x"},
                           "total_do_pais": {"faixa": "y"}}})
    ok("junta as unidades dos dois índices", sorted(f) == ["DF", "GO", "SP"])
    ok("chave que não é sigla de duas letras fica fora", "total_do_pais" not in f)
    ok("lê a faixa de cada índice", f["GO"] == {"legal": "em construção", "saude": "consolidado"})
    ok("unidade sem valor no outro índice fica None", f["SP"]["saude"] is None)
    ok("faixa sai da régua canónica quando o índice publica só o total",
       faixa_do_total({"total": 69.2}) == "consolidado" and faixa_do_total({}) is None)
    ok("índice como mapa por sigla, sem invólucro, é lido",
       sorted(faixas_de({"GO": {"total": 10.0}}, {})) == ["GO"])

    h = acrescentar({}, "2026-10-02", {"GO": {"legal": "em construção", "saude": None}})
    ok("primeira edição entra", len(h["edicoes"]) == 1)
    h2 = acrescentar(h, "2026-10-02", {"GO": {"legal": "consolidado", "saude": None}})
    ok("segunda execução no mesmo dia atualiza a edição, não duplica",
       len(h2["edicoes"]) == 1 and h2["edicoes"][0]["faixas"]["GO"]["legal"] == "consolidado")
    h3 = acrescentar(h2, "2026-10-09", {"GO": {"legal": "avançado", "saude": None}})
    ok("edição nova entra e a antiga permanece", [e["data"] for e in h3["edicoes"]]
       == ["2026-10-02", "2026-10-09"])

    m = mudaram(h3)
    ok("acha quem mudou entre as duas últimas edições",
       m["mudaram"] == [{"uf": "GO", "de": "consolidado", "para": "avançado"}])
    ok("declara o intervalo", m["de_ate"] == ("2026-10-02", "2026-10-09"))
    ok("uma edição só não produz número", mudaram(h2)["mudaram"] is None)
    ok("histórico vazio não quebra", mudaram({})["mudaram"] is None)

    h4 = acrescentar(acrescentar({}, "2026-10-02", {"GO": {"legal": None, "saude": None}}),
                     "2026-10-09", {"GO": {"legal": "em construção", "saude": None}})
    ok("sair de 'não verificado' não conta como mudança de faixa", mudaram(h4)["mudaram"] == [])

    fonte = pathlib.Path(__file__).read_text(encoding="utf-8")
    escritas = [l for l in fonte.splitlines() if l.strip().startswith("gravar(")]
    ok("trava estrutural: uma escrita só, e é o histórico",
       len(escritas) == 1 and escritas[0].strip().startswith("gravar(ARQUIVO"))
    ok("trava estrutural: nenhum arquivo do banco é destino",
       not any(f'gravar("{b}' in fonte for b in BANCO_PROIBIDO))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else f"✓ AUTOTESTE OK — {len(_casos_contados)} casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return _autoteste()

    sys.path.insert(0, str(RAIZ))
    from coletores_base import gravar, hoje_editorial, ler

    faixas = faixas_de(ler("indice.json", {}) or {}, ler("monitor_saude.json", {}) or {})
    if not faixas:
        print("registrar_faixas: nenhum índice publicado — nada a registrar")
        return 0
    historico = acrescentar(ler(ARQUIVO, {}) or {}, hoje_editorial().isoformat(), faixas)
    m = mudaram(historico)
    print(f"registrar_faixas: {len(faixas)} unidade(s) na edição de {hoje_editorial().isoformat()}; "
          + (f"{len(m['mudaram'])} mudança(s) de faixa desde {m['de_ate'][0]}"
             if m["mudaram"] is not None else f"sem comparação ({m['motivo']})"))
    if "--ensaio" in sys.argv:
        print("ensaio: nada gravado")
        return 0
    gravar(ARQUIVO, historico)
    print(f"{ARQUIVO} atualizado · {len(historico['edicoes'])} edição(ões) na série")
    return 0


if __name__ == "__main__":
    sys.exit(main())
