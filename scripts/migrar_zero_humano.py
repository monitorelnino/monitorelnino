#!/usr/bin/env python3
"""migrar_zero_humano.py — migração única de 10/10/2026 (zero etapa humana no código ativo).

Os valores de dado que o código lê e que nomeavam uma etapa humana passam ao vocabulário da regra
automática (D7 de 08/10/2026; METODOLOGIA §106; achado A5-08):

  - `data/doe_edicoes/<UF>.json`: canal 2 `verificacao_humana` → `sem_acesso_automatico`, e
    `conta_como_consultado` passa a false — verificação por pessoa não conta como consulta;
  - `data/saude_desfechos/gatilhos.json`: `status_monitor` `leitura_humana` → `sem_acesso_automatico`;
  - `data/saude_desfechos/fontes_uf.json`: a rota alternativa da secretaria (PB, RJ) troca a chave e
    o `modo_acesso` para `sem_acesso_automatico`, com o motivo dizendo que não conta como consulta;
  - `data/saude_sinais.json`: a fila do ESPIN `para_leitura_humana` → `pendente_leitura_automatica`.

Nada sai de fila e nenhum item é apagado: muda o nome do estado e, no canal 2 e no canal 3, a
contagem de consultado (a opção conservadora). Idempotente: rodar de novo não muda nada.

USO
    python3 scripts/migrar_zero_humano.py --autoteste
    python3 scripts/migrar_zero_humano.py              # relatório, nada escrito
    python3 scripts/migrar_zero_humano.py --aplicar
"""
from __future__ import annotations

import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

NOVO = "sem_acesso_automatico"
MODO_VELHO = "verificacao_humana"
STATUS_VELHO = "leitura_humana"
CHAVE_ROTA_VELHA, CHAVE_ROTA_NOVA = "canais_instrumento_humano", "canais_instrumento_sem_acesso_automatico"
FILA_VELHA, FILA_NOVA = "para_leitura_humana", "pendente_leitura_automatica"
MOTIVO_NOVO = "rota sem acesso automático — lacuna declarada, não conta como canal consultado (10/10/2026)"
TROCAS_DE_MOTIVO = (("; a verificacao desta rota e humana, e conta como canal consultado", "; " + MOTIVO_NOVO),
                    (", e ate ela o canal 3 e verificacao humana", "; " + MOTIVO_NOVO))
GOVERNANCA_FONTES = (("(máquina/leitura humana/defeso)", "(máquina/sem acesso automático/defeso)"),)
NOTA_ESPIN = ("Ato de RESPOSTA: declarar emergência é posterior ao dano e não entra na nota. "
              "Nada aqui entra no banco sem o juiz automático com documento oficial lido (R7, §106); "
              "o que está em dúvida fica pendente de leitura automática, não vai ao registro.")


def _renomear(d: dict, velha: str, nova: str) -> dict:
    """Mesmo dict com a chave renomeada, na mesma posição. Função pura."""
    return {(nova if k == velha else k): v for k, v in d.items()}


def migrar_canal2(reg: dict, governanca: str) -> bool:
    c2 = reg.get("canal2")
    if not isinstance(c2, dict) or c2.get("modo") != MODO_VELHO:
        return False
    c2["modo"] = NOVO
    c2["conta_como_consultado"] = False
    if "_governanca" in reg:
        reg["_governanca"] = governanca
    return True


def migrar_gatilhos(doc: dict) -> int:
    n = 0
    for g in doc.get("gatilhos") or []:
        if isinstance(g, dict) and g.get("status_monitor") == STATUS_VELHO:
            g["status_monitor"] = NOVO
            n += 1
    return n


def migrar_fontes_uf(doc: dict) -> int:
    n = 0
    gov = doc.get("_governanca")
    if isinstance(gov, str):
        for a, b in GOVERNANCA_FONTES:
            gov = gov.replace(a, b)
        n += gov != doc["_governanca"]
        doc["_governanca"] = gov
    ufs = doc.get("uf") if isinstance(doc.get("uf"), dict) else doc
    for uf, cfg in list(ufs.items()):
        if not isinstance(cfg, dict) or CHAVE_ROTA_VELHA not in cfg:
            continue
        rota = dict(cfg[CHAVE_ROTA_VELHA])
        rota["modo_acesso"] = NOVO
        motivo = str(rota.get("motivo") or "")
        for a, b in TROCAS_DE_MOTIVO:
            motivo = motivo.replace(a, b)
        rota["motivo"] = motivo
        novo = _renomear(cfg, CHAVE_ROTA_VELHA, CHAVE_ROTA_NOVA)
        novo[CHAVE_ROTA_NOVA] = rota
        ufs[uf] = novo
        n += 1
    return n


def migrar_espin(doc: dict) -> int:
    bloco = doc.get("espin_busca")
    if not isinstance(bloco, dict) or FILA_VELHA not in bloco:
        return 0
    novo = _renomear(bloco, FILA_VELHA, FILA_NOVA)
    novo["nota"] = NOTA_ESPIN
    doc["espin_busca"] = novo
    return 1


def autoteste() -> int:
    casos = []
    r = {"_governanca": "x", "canal2": {"modo": MODO_VELHO, "conta_como_consultado": True, "motivo": "403"}}
    casos.append(("canal 2 migra e deixa de contar como consultado",
                  migrar_canal2(r, "G") and r["canal2"]["modo"] == NOVO
                  and r["canal2"]["conta_como_consultado"] is False and r["_governanca"] == "G"))
    casos.append(("canal 2 é idempotente", not migrar_canal2(r, "G")))
    casos.append(("canal 2 com rota medida não muda",
                  not migrar_canal2({"canal2": {"modo": "padrao_por_data"}}, "G")))
    g = {"gatilhos": [{"status_monitor": STATUS_VELHO}, {"status_monitor": "computavel"}]}
    casos.append(("gatilho migra só o legado", migrar_gatilhos(g) == 1
                  and [x["status_monitor"] for x in g["gatilhos"]] == [NOVO, "computavel"]))
    f = {"_governanca": "status (máquina/leitura humana/defeso)",
         "PB": {"a": 1, CHAVE_ROTA_VELHA: {"modo_acesso": "x",
                "motivo": "muro; a verificacao desta rota e humana, e conta como canal consultado"}, "z": 2}}
    casos.append(("rota alternativa troca chave, modo e motivo, na mesma posição",
                  migrar_fontes_uf(f) == 2 and list(f["PB"]) == ["a", CHAVE_ROTA_NOVA, "z"]
                  and f["PB"][CHAVE_ROTA_NOVA]["modo_acesso"] == NOVO
                  and "não conta" in f["PB"][CHAVE_ROTA_NOVA]["motivo"]
                  and "sem acesso automático" in f["_governanca"]))
    casos.append(("fontes_uf é idempotente", migrar_fontes_uf(f) == 0))
    e = {"espin_busca": {"declaracoes": [], FILA_VELHA: [1], "nota": "n"}}
    casos.append(("fila do ESPIN troca de nome sem perder item",
                  migrar_espin(e) == 1 and e["espin_busca"][FILA_NOVA] == [1]
                  and list(e["espin_busca"])[1] == FILA_NOVA and migrar_espin(e) == 0))
    for nome, ok in casos:
        print(f"  {'OK  ' if ok else 'FALHA'} {nome}")
    ruins = [n for n, ok in casos if not ok]
    print(f"{'X AUTOTESTE: ' + str(len(ruins)) + ' falha(s)' if ruins else 'OK AUTOTESTE — ' + str(len(casos)) + ' casos, sem escrita.'}")
    return 1 if ruins else 0


def main() -> int:
    from coletores_base import gravar_em
    from coletar_edicoes_doe import GOVERNANCA_CANAL2
    aplicar = "--aplicar" in sys.argv
    alvos = []
    for p in sorted((RAIZ / "data" / "doe_edicoes").glob("*.json")):
        doc = json.loads(p.read_text(encoding="utf-8"))
        alvos.append((p, doc, int(migrar_canal2(doc, GOVERNANCA_CANAL2))))
    for rel, fn in (("data/saude_desfechos/gatilhos.json", migrar_gatilhos),
                    ("data/saude_desfechos/fontes_uf.json", migrar_fontes_uf),
                    ("data/saude_sinais.json", migrar_espin)):
        p = RAIZ / rel
        if p.exists():
            doc = json.loads(p.read_text(encoding="utf-8"))
            alvos.append((p, doc, fn(doc)))
    for p, doc, n in alvos:
        if n:
            if aplicar:
                gravar_em(p, doc)
            print(f"{p.relative_to(RAIZ)}: {n} troca(s) {'aplicada(s)' if aplicar else 'a aplicar'}")
    return 0


if __name__ == "__main__":
    sys.exit(autoteste() if "--autoteste" in sys.argv else main())
