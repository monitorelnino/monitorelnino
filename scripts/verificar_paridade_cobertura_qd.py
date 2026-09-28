#!/usr/bin/env python3
"""Portão de paridade: `data/cobertura_qd.json` × `data/verificacao_resumo.json`.

POR QUE ESTE PORTÃO EXISTE (27/09/2026, §256)
=============================================
Pendência aberta em `notas/PENDENCIAS_2026-09-14.md` e cobrada pelo T1 do pedido do preprint: os
dois arquivos contam a MESMA coisa — quantos municípios têm diário indexado no Querido Diário — e
nada garantia que concordassem.

O número entra no preprint como limitação quantificada do E6, e uma divergência entre os dois
arquivos viraria duas afirmações incompatíveis publicadas no mesmo trabalho.

Medido em 27/09, antes deste portão existir: os dois **já concordavam** em 527. O pedido do
preprint relatava "as 5.571 entradas com `cobertura_qd: false`" e `data_teste` 2026-09-06 — o que
não se confirma. O `false` e o `06/09` eram os do PRIMEIRO município da ordem de iteração, tomado
pelo todo. A contagem real: 527 `true`, 5.041 `false`, 3 `None`, somando 5.571.

O portão existe para que a próxima divergência apareça na hora, e não numa leitura de arquivo
grande feita a olho.

Uso:
    python3 scripts/verificar_paridade_cobertura_qd.py
    python3 scripts/verificar_paridade_cobertura_qd.py --autoteste
"""
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
COBERTURA = RAIZ / "data" / "cobertura_qd.json"
RESUMO = RAIZ / "data" / "verificacao_resumo.json"


def contar(cobertura: dict) -> dict:
    """Conta os três desfechos possíveis. `None` é indefinido, e NÃO é `false`."""
    municipios = (cobertura or {}).get("municipios") or {}
    indexados = nao_indexados = indefinidos = 0
    for registro in municipios.values():
        valor = registro.get("cobertura_qd") if isinstance(registro, dict) else registro
        if valor is True:
            indexados += 1
        elif valor is False:
            nao_indexados += 1
        else:
            indefinidos += 1
    return {"indexados": indexados, "nao_indexados": nao_indexados,
            "indefinidos": indefinidos, "total": len(municipios)}


def problemas(cobertura: dict, resumo: dict) -> list[str]:
    p = []
    c = contar(cobertura)
    v = (resumo or {}).get("varredura_diarios") or {}

    if not c["total"]:
        return ["data/cobertura_qd.json sem municípios"]
    if not v:
        return ["data/verificacao_resumo.json sem o bloco varredura_diarios"]

    # A paridade que dá nome ao portão.
    if v.get("indexados") is not None and c["indexados"] != v["indexados"]:
        p.append(f"indexados divergem: cobertura_qd.json conta {c['indexados']} e "
                 f"verificacao_resumo.json declara {v['indexados']}")

    # As três classes têm de somar o total — senão uma delas está sendo perdida na contagem.
    soma = c["indexados"] + c["nao_indexados"] + c["indefinidos"]
    if soma != c["total"]:
        p.append(f"as três classes somam {soma} e o arquivo tem {c['total']} municípios")

    if v.get("total") is not None and c["total"] != v["total"]:
        p.append(f"total de municípios diverge: cobertura_qd.json {c['total']} × "
                 f"verificacao_resumo.json {v['total']}")

    # `sem_cobertura_qd` do resumo é o `false` daqui. Indefinido fica de fora dos dois.
    if v.get("sem_cobertura_qd") is not None and c["nao_indexados"] != v["sem_cobertura_qd"]:
        p.append(f"não indexados divergem: cobertura_qd.json conta {c['nao_indexados']} e "
                 f"verificacao_resumo.json declara {v['sem_cobertura_qd']}")

    # A partição dos indexados no resumo tem TRÊS parcelas, não duas. Até 28/09/2026 (§280) este
    # portão somava só `com_mencao + coberto_sem_mencao`, porque `sem_edicao_no_periodo` — criada
    # pelo §194 — estava sendo contada dentro de `com_mencao` por definição por exclusão. Diário
    # indexado sem edição na janela continua indexado: ele pertence à partição, e não a nenhuma
    # das outras duas classes.
    com, sem = v.get("com_mencao"), v.get("coberto_sem_mencao")
    vazio = v.get("sem_edicao_no_periodo")
    if com is not None and sem is not None and vazio is not None:
        if com + sem + vazio != v.get("indexados"):
            p.append(f"no resumo, com_mencao {com} + coberto_sem_mencao {sem} + "
                     f"sem_edicao_no_periodo {vazio} = {com + sem + vazio}, que não é indexados "
                     f"{v.get('indexados')}")
    elif com is not None and sem is not None:
        p.append("o resumo traz com_mencao e coberto_sem_mencao sem sem_edicao_no_periodo — a "
                 "partição dos indexados tem três parcelas desde o §280; sem a terceira, os "
                 "municípios com diário indexado e nenhuma edição na janela voltam a ser "
                 "contados como tendo menção")

    # Zero indexado seria o sintoma que o pedido do preprint relatou. Se acontecer de verdade,
    # reprova: 5.571 municípios sem um único diário indexado é falha de coleta, não um fato.
    if c["indexados"] == 0:
        p.append("nenhum município indexado — 5.571 em false é falha de coleta, não um fato; "
                 "confira se a rotina que preenche cobertura_qd.json rodou")

    return p


def autoteste() -> int:
    falhas = []

    def checar(nome, cond):
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    def cob(t, f, n):
        m = {}
        i = 0
        for valor, quantos in ((True, t), (False, f), (None, n)):
            for _ in range(quantos):
                i += 1
                m[str(i)] = {"cobertura_qd": valor, "data_teste": "2026-09-12"}
        return {"municipios": m}

    def res(**kw):
        return {"varredura_diarios": kw}

    checar("estado real de 28/09 passa: 527 / 5041 / 3 contra indexados 527",
           problemas(cob(527, 5041, 3),
                     res(indexados=527, total=5571, sem_cobertura_qd=5041,
                         com_mencao=260, coberto_sem_mencao=211,
                         sem_edicao_no_periodo=56)) == [])

    p = problemas(cob(500, 5068, 3), res(indexados=527, total=5571))
    checar("indexados divergentes REPROVAM", any("indexados divergem" in x for x in p))

    p = problemas(cob(0, 5571, 0), res(indexados=0, total=5571, sem_cobertura_qd=5571))
    checar("zero indexado REPROVA, mesmo com os dois arquivos de acordo",
           any("nenhum município indexado" in x for x in p))

    p = problemas(cob(527, 5041, 3), res(indexados=527, total=5571, sem_cobertura_qd=5000))
    checar("não indexados divergentes REPROVAM",
           any("não indexados divergem" in x for x in p))

    p = problemas(cob(527, 5041, 3),
                  res(indexados=527, total=5571, com_mencao=300, coberto_sem_mencao=180,
                      sem_edicao_no_periodo=56))
    checar("partição interna do resumo que não fecha REPROVA",
           any("não é indexados" in x for x in p))

    # O defeito do §280 exatamente como ele estava publicado: 347 + 180 fechava 527 com a
    # partição de duas parcelas, e o portão passava verde sobre uma conta errada.
    p = problemas(cob(527, 5041, 3),
                  res(indexados=527, total=5571, sem_cobertura_qd=5041,
                      com_mencao=347, coberto_sem_mencao=180))
    checar("partição de DUAS parcelas REPROVA, mesmo fechando a soma (o defeito do §280)",
           any("três parcelas" in x for x in p))

    p = problemas(cob(527, 5041, 3), res(indexados=527, total=9999))
    checar("total divergente REPROVA", any("total de municípios diverge" in x for x in p))

    # `None` não é `false`: contá-lo como não indexado inflaria a limitação declarada no E6.
    c = contar(cob(10, 20, 5))
    checar("indefinido é contado à parte, nunca como não indexado",
           c["indefinidos"] == 5 and c["nao_indexados"] == 20)

    if falhas:
        print(f"\n✗ AUTOTESTE DA PARIDADE: {len(falhas)} falha(s).")
        return 1
    print("\n✓ AUTOTESTE DA PARIDADE OK — os sete desacordos reprovam, e o acordo real passa.")
    return 0


def main() -> int:
    if "--autoteste" in sys.argv[1:]:
        return autoteste()
    if not COBERTURA.exists() or not RESUMO.exists():
        falta = [str(p.relative_to(RAIZ)) for p in (COBERTURA, RESUMO) if not p.exists()]
        print(f"✗ PARIDADE COBERTURA QD: arquivo ausente: {', '.join(falta)}")
        return 1
    cobertura = json.loads(COBERTURA.read_text(encoding="utf-8"))
    resumo = json.loads(RESUMO.read_text(encoding="utf-8"))
    p = problemas(cobertura, resumo)
    c = contar(cobertura)
    v = resumo.get("varredura_diarios") or {}
    if p:
        print(f"✗ PARIDADE COBERTURA QD: {len(p)} problema(s):")
        for x in p:
            print(f"  · {x}")
        return 1
    print(f"✓ PARIDADE COBERTURA QD OK — {c['indexados']} município(s) com diário indexado nos "
          f"dois arquivos ({c['nao_indexados']} não indexados, {c['indefinidos']} indefinidos, "
          f"total {c['total']}); última varredura {v.get('ultima')}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
