#!/usr/bin/env python3
"""
scripts/deduplicar_fila_de_pistas.py — a mesma pista uma vez só
=================================================================
Item 2 da conferência da central de 06/10/2026: "deduplicar o arquivo (URL final + município +
assunto) e medir o tamanho real".

O QUE SE ACHOU
---------------
`data/pistas_imprensa.json` tinha **12.143 pistas** e **8.755 chaves distintas**: 3.388 repetições,
uma delas 33 vezes. Isso é anterior ao incidente de hoje — o salto de 28 MB para 187,53 MB foi uma
união que concatenava, e está corrigido em `scripts/pendente_do_elo.py`; estas 3.388 são o acúmulo
de antes, de rodadas que gravaram a mesma pista de novo.

A CHAVE É A DA PORTA, NÃO UMA NOVA
-----------------------------------
`scripts/pistas.py` já define `chave_da_pista`, e é ela que decide se duas pistas são a mesma. Usar
outra chave aqui criaria duas noções de identidade no mesmo projeto, e a segunda discordaria da
primeira na primeira esquina. Quem deduplica usa a chave de quem grava.

O QUE SE PRESERVA
------------------
Da repetição fica **uma** pista, com os campos de todas: a primeira vista é a base, e cada repetição
preenche o que falta nela, sem sobrescrever. Campo que já existe não muda — a repetição não sabe
mais que o original, e trocar seria escolher às cegas.

É operação sobre a fila INTEIRA, declarada em `MANUTENCAO` de `verificar_escritor_de_pista.py`.

USO
  python3 scripts/deduplicar_fila_de_pistas.py --autoteste
  python3 scripts/deduplicar_fila_de_pistas.py --conferir          # só mede
  python3 scripts/deduplicar_fila_de_pistas.py --aplicar
"""
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
FILAS = ("data/pistas_imprensa.json", "data/pistas_descobertas.json", "data/pistas_doe.json",
         "data/pistas_sinais.json", "data/pistas_rejeitadas.json")


def deduplicar(pistas: list, chave) -> tuple:
    """(sem_repetição, quantas_saíram). Função pura.

    `chave` é injetada para o autoteste poder provar o comportamento sem depender da porta — mas em
    uso real é sempre `pistas.chave_da_pista`, e é isso que importa.
    """
    por_chave, ordem = {}, []
    for pista in pistas or []:
        k = chave(pista)
        if k in por_chave:
            for campo, valor in (pista or {}).items():
                # `setdefault`: a repetição preenche o que falta e não sobrescreve o que há.
                if campo not in por_chave[k] or por_chave[k][campo] in (None, "", [], {}):
                    por_chave[k][campo] = valor
        else:
            por_chave[k] = dict(pista or {})
            ordem.append(k)
    fora = [por_chave[k] for k in ordem]
    return fora, len(pistas or []) - len(fora)


def _autoteste() -> int:
    falhas, contados = [], []

    def ok(nome, cond):
        contados.append(nome)
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    k = lambda p: (p.get("url"), p.get("municipio"))

    fora, n = deduplicar([{"url": "a", "municipio": "X"}, {"url": "a", "municipio": "X"}], k)
    ok("a mesma pista duas vezes vira uma", len(fora) == 1 and n == 1)
    ok("pistas diferentes ficam as duas",
       len(deduplicar([{"url": "a"}, {"url": "b"}], k)[0]) == 2)
    ok("a ordem da primeira aparição é preservada",
       [p["url"] for p in deduplicar([{"url": "b"}, {"url": "a"}, {"url": "b"}], k)[0]]
       == ["b", "a"])

    fora, _ = deduplicar([{"url": "a", "titulo": "T"}, {"url": "a", "data": "01/10/2026"}], k)
    ok("a repetição preenche o campo que faltava", fora[0].get("data") == "01/10/2026")
    ok("e não apaga o que já havia", fora[0].get("titulo") == "T")

    fora, _ = deduplicar([{"url": "a", "titulo": "ORIGINAL"}, {"url": "a", "titulo": "OUTRO"}], k)
    ok("campo preenchido NÃO é sobrescrito", fora[0]["titulo"] == "ORIGINAL")
    fora, _ = deduplicar([{"url": "a", "titulo": ""}, {"url": "a", "titulo": "BOM"}], k)
    ok("campo vazio é preenchido pela repetição", fora[0]["titulo"] == "BOM")

    ok("fila vazia não quebra", deduplicar([], k) == ([], 0))
    ok("nada repetido devolve zero removidas", deduplicar([{"url": "a"}], k)[1] == 0)
    ok("trinta e três repetições viram uma",
       len(deduplicar([{"url": "a"}] * 33, k)[0]) == 1)
    ok("a conta de removidas fecha", deduplicar([{"url": "a"}] * 33, k)[1] == 32)


    def chave_rej(r):
        return "|".join([str(r.get("url") or ""), str(r.get("alvo") or ""),
                         str(r.get("origem_canonica") or ""), str(r.get("motivo") or "")])
    recusas = [{"url": "u", "alvo": "5002704", "motivo": "sem url_final", "vezes": 2},
               {"url": "u", "alvo": "5002704", "motivo": "sem url_final"},
               {"url": "u", "alvo": "5002704", "motivo": "tipo outro"}]
    fora_rej, saiu = deduplicar(recusas, chave_rej)
    ok("recusa repetida sai, recusa de outro motivo fica", len(fora_rej) == 2 and saiu == 1)
    import dis
    nomes = set()
    for nome_obj, obj in list(globals().items()):
        if nome_obj in ("_autoteste", "main"):
            continue
        if getattr(obj, "__module__", None) not in (__name__, None):
            continue
        codigo = getattr(obj, "__code__", None)
        if codigo is not None:
            nomes |= {i.argval for i in dis.get_instructions(codigo) if isinstance(i.argval, str)}
    ok("trava estrutural: a função pura não lê disco nem escreve",
       not ({"read_text", "write_text", "open"} & nomes))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else f"✓ AUTOTESTE OK — {len(contados)} casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def main(argv: list) -> int:
    if "--autoteste" in argv:
        return _autoteste()
    sys.path.insert(0, str(RAIZ / "scripts"))
    from pistas import chave_da_pista, chave_da_rejeicao

    aplicar = "--aplicar" in argv
    total_fora = 0
    for rel in FILAS:
        arq = RAIZ / rel
        if not arq.exists():
            continue
        antes_bytes = arq.stat().st_size
        doc = json.loads(arq.read_text(encoding="utf-8"))
        # O arquivo de recusas guarda a lista em `rejeitadas`, nao em `pistas`: ele estava nesta
        # lista desde o inicio e nunca era tocado, porque o `continue` abaixo o pulava calado.
        campo = "pistas" if isinstance(doc.get("pistas"), list) else "rejeitadas"
        pistas = doc.get(campo)
        if not isinstance(pistas, list):
            continue
        chave = chave_da_pista if campo == "pistas" else chave_da_rejeicao
        # Na recusa, a repeticao e contavel: ela vira `vezes`, e nao desaparece com a copia.
        vezes = {}
        if campo == "rejeitadas":
            for r in pistas:
                vezes[chave(r)] = vezes.get(chave(r), 0) + int((r or {}).get("vezes") or 1)
        fora, n = deduplicar(pistas, chave)
        for r in fora if campo == "rejeitadas" else []:
            r["vezes"] = vezes.get(chave(r), 1)
        if not n:
            print(f"  · {rel}: {len(pistas)} pista(s), nenhuma repetida")
            continue
        total_fora += n
        doc[campo] = fora
        if campo == "rejeitadas":
            doc["total"] = len(fora)
        bruto = json.dumps(doc, ensure_ascii=False, indent=1) + "\n"
        print(f"  {'·' if aplicar else '⚠'} {rel}: {len(pistas)} → {len(fora)} pista(s), "
              f"{n} repetida(s) removida(s); {round(antes_bytes / 1048576, 1)} MB → "
              f"{round(len(bruto.encode('utf-8')) / 1048576, 1)} MB")
        if aplicar:
            arq.write_text(bruto, encoding="utf-8", newline="\n")
    if not aplicar:
        print("  (--conferir: nada foi gravado. Use --aplicar para gravar.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
