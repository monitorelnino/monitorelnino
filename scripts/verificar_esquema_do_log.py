#!/usr/bin/env python3
"""Toda execução do log de buscas tem data ISO e decisão do vocabulário fechado (A6-27).

POR QUE EXISTE
--------------
`coletores_base.log_busca` já recusa decisão fora de `DECISOES_LOG` e grava a data em ISO. Mas
houve quem escrevesse no log por fora da porta: 14 execuções de 27–29/08 com a decisão em prosa
("+6 registros…", "Base pontuada…") e 150 de 28/09 com data `dd/mm/aaaa` no monólito — que
`_caminho_do_mes` mandaria para `sem-data.jsonl` e que quem procura "a última execução" ordena
errado. Foram normalizadas em 12/10/2026 (a decisão original ficou em `resultados`). Este portão
impede que voltem.

O QUE COBRA
-----------
Em `ler_log()` (monólito + meses): `data` em AAAA-MM-DD e a primeira palavra de `decisao` em
`DECISOES_LOG`. Linha JSONL inválida também reprova. Só lê.

USO
  python3 scripts/verificar_esquema_do_log.py
  python3 scripts/verificar_esquema_do_log.py --autoteste
"""
import re
import sys
import pathlib

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

RE_ISO = re.compile(r"\d{4}-\d{2}-\d{2}")


def problemas(log: dict, vocabulario) -> list:
    """Uma linha por execução fora do esquema (no máximo as 20 primeiras). Função pura."""
    fora = []
    for i, e in enumerate((log or {}).get("execucoes") or []):
        data, dec = str(e.get("data") or ""), str(e.get("decisao") or "")
        if not RE_ISO.fullmatch(data):
            fora.append(f"execução {i} ({e.get('canal')}): data fora de AAAA-MM-DD: {data!r}")
        if dec.split(" ")[0] not in vocabulario:
            fora.append(f"execução {i} ({e.get('canal')}): decisão fora do vocabulário: {dec[:60]!r}")
    if (log or {}).get("linhas_invalidas"):
        fora.append(f"{log['linhas_invalidas']} linha(s) JSONL inválida(s) no log")
    return fora


def _autoteste() -> int:
    V = ("registro", "pista", "consultado", "nada")
    casos = [
        ("log no esquema passa", {"execucoes": [{"data": "2026-10-12", "decisao": "pista"},
                                                 {"data": "2026-10-12", "decisao": "nada localizado"}]}, 0),
        ("data dd/mm/aaaa reprova", {"execucoes": [{"data": "28/09/2026", "decisao": "pista"}]}, 1),
        ("decisão em prosa reprova", {"execucoes": [{"data": "2026-08-27", "decisao": "+6 registros"}]}, 1),
        ("linha inválida reprova", {"execucoes": [], "linhas_invalidas": 2}, 1),
        ("log vazio passa", {}, 0),
    ]
    falhas = 0
    for nome, log, esperado in casos:
        ok = len(problemas(log, V)) == esperado
        falhas += not ok
        print(("  ✓ " if ok else "  ✗ ") + nome)
    import dis
    escreve = any(i.argval in ("gravar", "open", "write_text") for i in dis.get_instructions(problemas))
    print(("  ✗ " if escreve else "  ✓ ") + "trava: a função pura não lê nem grava")
    falhas += escreve
    print(f"✗ AUTOTESTE: {falhas} falha(s)" if falhas
          else f"✓ AUTOTESTE OK — {len(casos) + 1} casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return _autoteste()
    from coletores_base import ler_log, DECISOES_LOG
    log = ler_log()
    fora = problemas(log, DECISOES_LOG)
    if fora:
        print(f"✗ ESQUEMA DO LOG: {len(fora)} problema(s):")
        for x in fora[:20]:
            print("   - " + x)
        print("   Grave pelo `coletores_base.log_busca` (data ISO, decisão do vocabulário).")
        return 1
    print(f"✓ ESQUEMA DO LOG OK — {len(log.get('execucoes') or [])} execuções com data ISO e "
          f"decisão do vocabulário.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
