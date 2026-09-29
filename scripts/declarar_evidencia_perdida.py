#!/usr/bin/env python3
"""
declarar_evidencia_perdida.py
=============================
Índice que aponta arquivo inexistente vira **lacuna declarada**, com o motivo e a data.

§275, 28/09/2026. Em 28/09 a regra de `.gitignore` do §270 fez `monitorar_imprensa_regional.py`
preservar 1.496 páginas, indexá-las em `data/evidencias.json` e o git ignorar os arquivos. O índice
passou a afirmar cópia preservada que não existia — e afirmação de prova sem prova é o defeito mais
grave que este projeto pode ter. `verificar_evidencias.py` reprovou, corretamente.

O QUE ESTE SCRIPT FAZ
---------------------
Para cada item cujo `arquivo` não existe no disco: move o caminho para `arquivo_perdido`, zera
`arquivo`, e escreve `nota` com o motivo e a data. Segue a convenção que já existia no índice desde
03/09/2026 ("cópia perdida … não comitada pela rotina; re-preservar").

**Não apaga item nenhum.** O hash, a URL de origem, a data e o tamanho ficam: é por eles que a
re-preservação acha o que buscar, e é a URL que permite a qualquer pessoa conferir a fonte.
`preservar_evidencias.py` trata item sem `arquivo` como fila de re-preservação.

**Não inventa prova.** Ele não baixa nada e não marca nada como preservado: só troca uma afirmação
falsa por uma lacuna declarada, que é o que a METODOLOGIA exige (§3.8, e a regra de teto de ausência).

USO
  python3 scripts/declarar_evidencia_perdida.py --relatorio
  python3 scripts/declarar_evidencia_perdida.py --escrever --motivo "regra de .gitignore do §270"
  python3 scripts/declarar_evidencia_perdida.py --autoteste
"""
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

EVIDENCIAS = RAIZ / "evidencias"
INDICE = RAIZ / "data" / "evidencias.json"


def orfaos(itens: dict, existe=None) -> list:
    """Hashes cujo `arquivo` está declarado e não existe. `existe(nome)` é injetável."""
    def existe_no_disco(nome):
        return (EVIDENCIAS / nome).exists()
    existe = existe or existe_no_disco
    fora = []
    for h, item in (itens or {}).items():
        arquivo = item.get("arquivo")
        if not arquivo or arquivo == "None":
            continue
        if not existe(pathlib.PurePosixPath(str(arquivo)).name):
            fora.append(h)
    return fora


def com_texto_integral_ausente(itens: dict, existe=None) -> list:
    """Itens cujo `texto_integral` aponta arquivo que não está no disco."""
    existe = existe or (lambda c: pathlib.Path(c).exists())
    return [h for h, x in itens.items()
            if x.get("texto_integral") and not existe(x["texto_integral"])]


def declarar(itens: dict, hashes: list, motivo: str, data: str) -> int:
    """Troca a afirmação de cópia por lacuna declarada. Devolve quantos itens mudaram."""
    n = 0
    for h in hashes:
        item = itens[h]
        # Idempotente por CAMPO, não pelo item: um item já declarado no binário pode ter o texto
        # integral ainda afirmado, e pular o item inteiro deixava a segunda afirmação de pé.
        mudou = False
        if item.get("arquivo") and not item.get("arquivo_perdido"):
            item["arquivo_perdido"] = item.get("arquivo")
            item["arquivo"] = None
            mudou = True
        # 29/09/2026: o `texto_integral` some junto com o binário — é gravado pelo mesmo caminho e
        # ficou de fora na primeira versão deste script, que só olhava `arquivo`. Um item com o
        # binário declarado perdido e o texto ainda afirmado seria a mesma mentira, menor.
        if item.get("texto_integral"):
            item["texto_integral_perdido"] = item.get("texto_integral")
            item["texto_integral"] = None
            mudou = True
        if not mudou:
            continue
        nota = (f"cópia perdida em {data}: {motivo}. O hash, a URL de origem e o tamanho ficam no "
                f"índice; a re-preservação usa a URL. Nenhuma nota do índice depende deste item.")
        item["nota"] = (str(item.get("nota") or "").strip() + " " + nota).strip()
        n += 1
    return n


def autoteste() -> int:
    casos = []
    itens = {
        "aaa": {"arquivo": "evidencias/aaa.html", "url": "https://a", "tamanho": "10"},
        "bbb": {"arquivo": "evidencias/bbb.html", "url": "https://b"},
        "ccc": {"arquivo": None, "url": "https://c", "nota": "já era lacuna"},
        "ddd": {"arquivo": "evidencias/ddd.pdf", "url": "https://d"},
    }
    presentes = {"ddd.pdf"}
    fora = orfaos(itens, existe=lambda nome: nome in presentes)
    casos.append(("acha os dois órfãos", sorted(fora) == ["aaa", "bbb"]))
    casos.append(("item com arquivo presente não é órfão", "ddd" not in fora))
    casos.append(("item que já era lacuna não é órfão", "ccc" not in fora))

    n = declarar(itens, fora, "regra de .gitignore do §270", "28/09/2026")
    casos.append(("declara os dois", n == 2))
    casos.append(("zera arquivo", itens["aaa"]["arquivo"] is None))
    casos.append(("guarda o caminho perdido", itens["aaa"]["arquivo_perdido"] == "evidencias/aaa.html"))
    casos.append(("a nota diz o motivo e a data",
                  "28/09/2026" in itens["aaa"]["nota"] and "gitignore" in itens["aaa"]["nota"]))
    casos.append(("a URL e o tamanho ficam — é por eles que se re-preserva",
                  itens["aaa"]["url"] == "https://a" and itens["aaa"]["tamanho"] == "10"))
    casos.append(("o item presente não foi tocado", itens["ddd"]["arquivo"] == "evidencias/ddd.pdf"))
    casos.append(("nenhum item foi apagado", len(itens) == 4))

    # idempotência
    casos.append(("rodar de novo não muda nada",
                  declarar(itens, orfaos(itens, existe=lambda n_: n_ in presentes), "x", "y") == 0))
    # nota anterior é preservada, não substituída
    itens2 = {"eee": {"arquivo": "evidencias/eee.html", "nota": "nota velha"}}
    declarar(itens2, ["eee"], "motivo", "28/09/2026")
    casos.append(("nota anterior é preservada", itens2["eee"]["nota"].startswith("nota velha")))

    ruins = [n for n, ok in casos if not ok]
    for n, ok in casos:
        print(f"  {'OK  ' if ok else 'FALHA'} {n}")
    if ruins:
        print(f"X AUTOTESTE: {len(ruins)} caso(s) reprovado(s).")
        return 1
    print(f"OK AUTOTESTE — {len(casos)} casos, sem tocar em data/ nem em evidencias/.")
    return 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()

    from coletores_base import gravar_em, hoje_editorial

    doc = json.loads(INDICE.read_text(encoding="utf-8"))
    itens = doc.get("itens") or {}
    fora = orfaos(itens)
    # Item cujo binário está no disco mas cujo TEXTO INTEGRAL sumiu também entra: os dois são
    # gravados pelo mesmo caminho, e afirmar texto preservado que não existe é a mesma falta.
    so_texto = [h for h in com_texto_integral_ausente(itens) if h not in fora]
    fora = fora + so_texto
    import collections
    print(f"{len(fora)} item(ns) apontando arquivo inexistente"
          + (f" ({len(so_texto)} só no texto integral)" if so_texto else ""))
    for chave, contagem in (("preservado_em", "data"), ("origem", "origem")):
        c = collections.Counter(str(itens[h].get(chave)) for h in fora)
        print(f"  por {contagem}: {c.most_common(5)}")

    if "--escrever" not in sys.argv:
        print("relatório apenas; nada escrito (use --escrever)")
        return 0
    if not fora:
        print("nada a declarar")
        return 0
    motivo = sys.argv[sys.argv.index("--motivo") + 1] if "--motivo" in sys.argv else \
        "arquivo não chegou ao commit da rodada"
    data = hoje_editorial().strftime("%d/%m/%Y")
    antes = len(itens)
    n = declarar(itens, fora, motivo, data)
    assert len(itens) == antes, "nenhum item pode ser apagado"
    doc["itens"] = itens
    gravar_em(INDICE, doc)
    print(f"✓ {n} item(ns) passaram a lacuna declarada, com motivo e data; {antes} itens no índice, "
          f"antes e depois")
    return 0


if __name__ == "__main__":
    sys.exit(main())
