#!/usr/bin/env python3
"""
verificar_log_de_buscas.py
=========================
O log só cresce: a contagem de hoje nunca é menor que a maior já registrada.

Item 4 do handover `HANDOVER_desacoplar_pipeline_e_emagrecer_repositorio_27-09-2026.md` — "migração
com script e portão de paridade (contagem antes = depois)". Este é o portão, e ele continua valendo
depois da migração: com o log fatiado em `data/log_buscas/AAAA-MM.jsonl`, perder um arquivo de mês
passaria sem ruído nenhum — o JSON continuaria válido, só menor.

QUATRO INVARIANTES
----------------
1. **Nunca encolhe.** A marca d'água (`data/log_buscas_marca.json`) guarda o maior total já visto e a
   contagem por mês. Total menor que a marca reprova. Foi exatamente esse o defeito de 23/09, quando
   uma união por conteúdo produziu um log **menor** que cada um dos lados e apagou quase 3.000
   execuções sem aviso.
2. **Nenhum mês encolhe.** O total pode crescer enquanto um mês perde linhas — a marca é por mês
   também.
3. **Nenhuma linha inválida.** JSONL truncado por interrupção perde a última linha; `ler_log()` a
   ignora para não estourar, mas o portão acusa, porque linha perdida é dado perdido.
4. **Esquema (A6-27, ex-`verificar_esquema_do_log.py`).** Toda execução tem `data` em AAAA-MM-DD e a
   primeira palavra de `decisao` em `DECISOES_LOG`. Houve quem escrevesse por fora da porta
   `coletores_base.log_busca`: 14 execuções de 27–29/08 com a decisão em prosa e 150 de 28/09 com data
   `dd/mm/aaaa`, que `_caminho_do_mes` mandaria para `sem-data.jsonl`.

USO
  python3 scripts/verificar_log_de_buscas.py             # confere
  python3 scripts/verificar_log_de_buscas.py --marcar    # atualiza a marca d'água (após crescer)
  python3 scripts/verificar_log_de_buscas.py --autoteste
"""
import collections
import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

MARCA = RAIZ / "data" / "log_buscas_marca.json"
RE_ISO = re.compile(r"\d{4}-\d{2}-\d{2}")


def contar(doc: dict) -> tuple:
    """(total, {mês: n}, linhas_invalidas) a partir do documento de `ler_log()`."""
    execucoes = doc.get("execucoes") or []
    por_mes = collections.Counter(str(e.get("data") or "sem-data")[:7] for e in execucoes)
    return len(execucoes), dict(por_mes), int(doc.get("linhas_invalidas") or 0)


def conferir(total: int, por_mes: dict, invalidas: int, marca: dict) -> list:
    """Função pura: devolve a lista de falhas. É ela que o autoteste exercita."""
    falhas = []
    marca_total = int((marca or {}).get("total") or 0)
    if total < marca_total:
        falhas.append(f"o log ENCOLHEU: {total} execuções contra {marca_total} da marca d'água "
                      f"({marca_total - total} a menos). Log é append-only; união por conteúdo já "
                      f"apagou quase 3.000 execuções em 23/09/2026.")
    for mes, n in sorted(((marca or {}).get("por_mes") or {}).items()):
        agora = int(por_mes.get(mes, 0))
        if agora < int(n):
            falhas.append(f"o mês {mes} encolheu: {agora} contra {n} da marca d'água")
    if invalidas:
        falhas.append(f"{invalidas} linha(s) inválida(s) no JSONL — linha perdida é dado perdido")
    return falhas


def esquema(log: dict, vocabulario) -> list:
    """Uma linha por execução fora do esquema. Função pura."""
    fora = []
    for i, e in enumerate((log or {}).get("execucoes") or []):
        data, dec = str(e.get("data") or ""), str(e.get("decisao") or "")
        if not RE_ISO.fullmatch(data):
            fora.append(f"execução {i} ({e.get('canal')}): data fora de AAAA-MM-DD: {data!r}")
        if dec.split(" ")[0] not in vocabulario:
            fora.append(f"execução {i} ({e.get('canal')}): decisão fora do vocabulário: {dec[:60]!r}")
    return fora


def autoteste() -> int:
    casos = []
    marca = {"total": 100, "por_mes": {"2026-08": 40, "2026-09": 60}}

    casos.append(("crescer passa",
                  conferir(120, {"2026-08": 40, "2026-09": 80}, 0, marca) == []))
    casos.append(("ficar igual passa",
                  conferir(100, {"2026-08": 40, "2026-09": 60}, 0, marca) == []))
    f = conferir(90, {"2026-08": 40, "2026-09": 50}, 0, marca)
    casos.append(("encolher o total reprova", any("ENCOLHEU" in x for x in f)))
    casos.append(("a falha diz quantas a menos", any("10 a menos" in x for x in f)))
    f = conferir(120, {"2026-08": 30, "2026-09": 90}, 0, marca)
    casos.append(("mês que encolhe reprova mesmo com total crescendo",
                  any("2026-08 encolheu" in x for x in f)))
    casos.append(("linha inválida reprova",
                  any("inválida" in x for x in conferir(100, {"2026-08": 40, "2026-09": 60}, 1, marca))))
    casos.append(("sem marca d'água nada reprova (primeira execução)",
                  conferir(10, {"2026-09": 10}, 0, {}) == []))
    casos.append(("mês novo não reprova",
                  conferir(101, {"2026-08": 40, "2026-09": 60, "2026-10": 1}, 0, marca) == []))

    doc = {"execucoes": [{"data": "2026-09-01"}, {"data": "2026-08-31"}, {"data": None}],
           "linhas_invalidas": 2}
    total, por_mes, inval = contar(doc)
    casos.append(("conta total, meses e inválidas",
                  total == 3 and por_mes.get("2026-09") == 1 and inval == 2))
    casos.append(("data ausente conta como sem-data", por_mes.get("sem-dat") == 1
                  or por_mes.get("sem-data") == 1 or "sem" in "".join(por_mes)))

    V = ("registro", "pista", "consultado", "nada")
    for nome, log, esperado in [
            ("esquema: log no esquema passa", {"execucoes": [{"data": "2026-10-12", "decisao": "pista"},
                                                              {"data": "2026-10-12", "decisao": "nada localizado"}]}, 0),
            ("esquema: data dd/mm/aaaa reprova", {"execucoes": [{"data": "28/09/2026", "decisao": "pista"}]}, 1),
            ("esquema: decisão em prosa reprova", {"execucoes": [{"data": "2026-08-27", "decisao": "+6 registros"}]}, 1),
            ("esquema: log vazio passa", {}, 0)]:
        casos.append((nome, len(esquema(log, V)) == esperado))
    import dis
    casos.append(("trava: a função pura do esquema não lê nem grava", not any(
        i.argval in ("gravar", "open", "write_text") for i in dis.get_instructions(esquema))))

    ruins = [n for n, ok in casos if not ok]
    for n, ok in casos:
        print(f"  {'OK  ' if ok else 'FALHA'} {n}")
    if ruins:
        print(f"X AUTOTESTE: {len(ruins)} caso(s) reprovado(s).")
        return 1
    print(f"OK AUTOTESTE — {len(casos)} casos.")
    return 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()

    from coletores_base import DECISOES_LOG, gravar_em, ler_log

    log = ler_log()
    total, por_mes, invalidas = contar(log)
    marca = json.loads(MARCA.read_text(encoding="utf-8")) if MARCA.exists() else {}

    if "--marcar" in sys.argv:
        nova = {"_governanca": ("Marca d'água do log append-only (item 4, 28/09/2026): o maior total "
                                "já visto, e por mês. O portão reprova se a contagem encolher."),
                "total": max(total, int(marca.get("total") or 0)),
                "por_mes": {m: max(int(por_mes.get(m, 0)), int((marca.get("por_mes") or {}).get(m, 0)))
                            for m in set(por_mes) | set(marca.get("por_mes") or {})}}
        gravar_em(MARCA, nova)
        print(f"✓ marca d'água em {nova['total']} execução(ões), {len(nova['por_mes'])} mês(es)")
        return 0

    falhas = conferir(total, por_mes, invalidas, marca) + esquema(log, DECISOES_LOG)[:20]
    if falhas:
        print("✗ LOG DE BUSCAS:")
        for f in falhas:
            print(f"   - {f}")
        return 1
    print(f"✓ LOG DE BUSCAS OK — {total} execução(ões) em {len(por_mes)} mês(es), nenhuma perdida "
          f"(marca d'água: {int(marca.get('total') or 0)}), data ISO e decisão do vocabulário.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
