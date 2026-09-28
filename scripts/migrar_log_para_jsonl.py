#!/usr/bin/env python3
"""
migrar_log_para_jsonl.py
========================
Move as execuções de `data/log_buscas.json` para `data/log_buscas/AAAA-MM.jsonl`.

Item 4 do handover `HANDOVER_desacoplar_pipeline_e_emagrecer_repositorio_27-09-2026.md`: o log
chegou a 30,8 MB num único JSON, lido **e regravado inteiro** a cada execução registrada, por vários
scripts a cada rodada. Duas consequências: tempo gasto reescrevendo 30 MB, e um erro de escrita no
meio pondo em risco o arquivo todo — foi assim que `fontes_consultadas.json` se corrompeu em 21/09
(368.019 para 166.961 linhas).

O QUE A MIGRAÇÃO GARANTE
------------------------
**Paridade de contagem.** Antes e depois têm de somar o mesmo número de execuções, e a checagem é
condição para o monólito ser esvaziado. Se não fechar, nada é tocado.

**Ordem preservada.** Dentro de cada mês, a ordem é a do arquivo original. O log é append-only e
"a última execução de um canal" é pergunta real — reordenar mudaria a resposta.

**Idempotência.** Rodar duas vezes não duplica: a segunda execução vê o monólito já vazio e não tem
o que mover.

O monólito **não é apagado**: fica com `execucoes: []` e um campo `migrado_para` apontando a pasta.
Apagar o arquivo quebraria os leitores que ainda o abrem direto, e `ler_log()` concatena os dois.

USO
  python3 scripts/migrar_log_para_jsonl.py --relatorio     # conta, não escreve
  python3 scripts/migrar_log_para_jsonl.py --escrever
  python3 scripts/migrar_log_para_jsonl.py --autoteste
"""
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))


def por_mes(execucoes: list) -> dict:
    """Agrupa por AAAA-MM preservando a ordem de entrada dentro de cada mês."""
    grupos = {}
    for e in execucoes:
        mes = str(e.get("data") or "")[:7]
        if len(mes) != 7 or mes[4] != "-":
            mes = "sem-data"
        grupos.setdefault(mes, []).append(e)
    return grupos


def autoteste() -> int:
    import tempfile
    import coletores_base as cb
    casos = []

    execucoes = ([{"data": "2026-08-31", "canal": "a", "i": i} for i in range(3)]
                 + [{"data": "2026-09-01", "canal": "b", "i": i} for i in range(5)]
                 + [{"data": None, "canal": "c"}])

    grupos = por_mes(execucoes)
    casos.append(("agrupa por mês", sorted(grupos) == ["2026-08", "2026-09", "sem-data"]))
    casos.append(("data ausente vai para sem-data", len(grupos["sem-data"]) == 1))
    casos.append(("a ordem dentro do mês é a de entrada",
                  [e["i"] for e in grupos["2026-09"]] == [0, 1, 2, 3, 4]))

    real = cb.DATA
    try:
        cb.DATA = pathlib.Path(tempfile.mkdtemp())
        escritas = cb.acrescentar_ao_log(execucoes)
        casos.append(("escreve uma linha por execução", escritas == len(execucoes)))
        lido = cb.ler_log()["execucoes"]
        casos.append(("paridade de contagem na volta", len(lido) == len(execucoes)))
        # a ordem entre meses sai da ordem dos nomes de arquivo: agosto antes de setembro
        datas = [str(e.get("data")) for e in lido if e.get("data")]
        casos.append(("agosto vem antes de setembro na leitura",
                      datas.index("2026-08-31") < datas.index("2026-09-01")))
        # idempotência do append: acrescentar de novo DUPLICA (é append puro), e é por isso que a
        # migração esvazia o monólito em vez de reexecutar o append
        cb.acrescentar_ao_log(execucoes)
        casos.append(("append é puro: chamar de novo duplica (daí o monólito ser esvaziado)",
                      len(cb.ler_log()["execucoes"]) == 2 * len(execucoes)))
        # linha inválida não estoura a leitura
        alvo = cb.DATA / "log_buscas" / "2026-09.jsonl"
        with open(alvo, "a", encoding="utf-8", newline="\n") as fh:
            fh.write("{isto nao e json}\n")
        doc = cb.ler_log()
        casos.append(("linha inválida é contada e ignorada, não estoura",
                      doc["linhas_invalidas"] == 1))
    finally:
        cb.DATA = real

    casos.append(("o autoteste não tocou data/",
                  not (RAIZ / "data" / "log_buscas" / "sem-data.jsonl").exists()))

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

    import coletores_base as cb

    caminho = cb.DATA / cb.LOG_MONOLITO
    doc = json.loads(caminho.read_text(encoding="utf-8")) if caminho.exists() else {}
    no_monolito = list(doc.get("execucoes") or [])
    ja_em_jsonl = len(cb.ler_log()["execucoes"]) - len(no_monolito)
    print(f"monólito: {len(no_monolito)} execução(ões) ({caminho.stat().st_size / 1e6:.1f} MB)"
          if caminho.exists() else "monólito ausente")
    print(f"já em JSONL: {ja_em_jsonl}")
    for mes, linhas in sorted(por_mes(no_monolito).items()):
        print(f"  {mes}: {len(linhas)}")

    if "--escrever" not in sys.argv:
        print("relatório apenas; nada escrito (use --escrever)")
        return 0
    if not no_monolito:
        print("nada a migrar — o monólito já está vazio")
        return 0

    antes = len(cb.ler_log()["execucoes"])
    escritas = cb.acrescentar_ao_log(no_monolito)
    if escritas != len(no_monolito):
        print(f"✗ escrevi {escritas} de {len(no_monolito)} — monólito NÃO esvaziado")
        return 1
    depois_jsonl = len(cb.ler_log()["execucoes"])
    # o monólito ainda conta na leitura; a paridade se confere contra o dobro esperado
    if depois_jsonl != antes + len(no_monolito):
        print(f"✗ paridade falhou: {antes} + {len(no_monolito)} != {depois_jsonl} — "
              f"monólito NÃO esvaziado")
        return 1

    doc["execucoes"] = []
    doc["migrado_para"] = f"data/{cb.PASTA_LOG}/AAAA-MM.jsonl"
    doc["migrado_em"] = cb.hoje_editorial().isoformat()
    cb.gravar_em(caminho, doc)
    final = len(cb.ler_log()["execucoes"])
    if final != antes:
        print(f"✗ depois de esvaziar o monólito a contagem virou {final}, esperava {antes}")
        return 1
    print(f"✓ {len(no_monolito)} execução(ões) migradas; total conferido: {final} antes e depois; "
          f"monólito esvaziado ({caminho.stat().st_size / 1e3:.1f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
