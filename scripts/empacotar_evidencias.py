#!/usr/bin/env python3
"""
empacotar_evidencias.py
=======================
Monta o lote mensal de evidências para publicar como ativo de Release, com índice próprio.

Item 3 do handover `HANDOVER_desacoplar_pipeline_e_emagrecer_repositorio_27-09-2026.md`.

A DECISÃO, E A RAZÃO (28/09/2026)
--------------------------------
O handover deixou a escolha ao Code: **ativo de Release** ou **repositório separado**. Escolhi
Release, e a razão é medida: o que os scripts da rodada leem é o **texto extraído** — 10,9 MB, que
continua no git —, não o binário. Binário é prova de registro, consultada por pessoa. Repositório
separado só se justificaria se algum script precisasse do binário num checkout, e nenhum precisa.
Release dá URL estável, ativo de até 2 GB, sem clone e sem custo.

O QUE ESTE SCRIPT FAZ, E O QUE NÃO FAZ
--------------------------------------
**Faz:** agrupa por mês de preservação, monta `evidencias-AAAA-MM.zip` com os binários daquele mês e
um `INDICE.tsv` dentro do pacote (hash, arquivo, URL de origem, data, tamanho), e imprime o comando de
publicação. Confere que o sha256 de cada arquivo bate com a chave do índice antes de empacotar — hash
que não bate não entra, e é acusado.

**Não faz:** não publica sozinho (publicar é ação externa, e o comando fica à vista para ser rodado
com credencial), **não apaga nada** do repositório, e não reescreve histórico. Remover 1,25 GB de prova
da árvore e reescrever o pack são ações irreversíveis que dependem da palavra da editoria.

USO
  python3 scripts/empacotar_evidencias.py --relatorio
  python3 scripts/empacotar_evidencias.py --mes 2026-09 --saida /tmp
  python3 scripts/empacotar_evidencias.py --autoteste
"""
import collections
import hashlib
import io
import json
import pathlib
import sys
import zipfile

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

EVIDENCIAS = RAIZ / "evidencias"
INDICE = RAIZ / "data" / "evidencias.json"
BINARIOS = {".pdf", ".html", ".htm", ".xlsx", ".xls", ".docx", ".doc", ".zip", ".png", ".jpg",
            ".jpeg", ".gif", ".webp", ".odt", ".ods"}


def sha256_do_arquivo(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with io.open(p, "rb") as fh:
        for pedaco in iter(lambda: fh.read(1 << 20), b""):
            h.update(pedaco)
    return h.hexdigest()


def agrupar(itens: dict, existe=None) -> dict:
    """{mês: [(hash, nome, item)]} para os itens com binário presente.

    `existe(nome) -> bool` é injetável: o autoteste roda sem tocar em `evidencias/`."""
    def existe_no_disco(nome):
        return (EVIDENCIAS / nome).exists()
    existe = existe or existe_no_disco
    grupos = collections.defaultdict(list)
    for h, item in (itens or {}).items():
        arquivo = item.get("arquivo")
        if not arquivo or arquivo == "None":
            continue
        nome = pathlib.PurePosixPath(str(arquivo)).name
        if pathlib.PurePosixPath(nome).suffix.lower() not in BINARIOS:
            continue
        if not existe(nome):
            continue
        mes = str(item.get("preservado_em") or "")[:7]
        if len(mes) != 7 or mes[4] != "-":
            mes = "sem-data"
        grupos[mes].append((h, nome, item))
    return dict(sorted(grupos.items()))


def linha_do_indice(h: str, nome: str, item: dict) -> str:
    """Uma linha do INDICE.tsv dentro do pacote. Tab porque URL tem vírgula e ponto e vírgula."""
    return "\t".join([h, nome, str(item.get("url") or ""), str(item.get("preservado_em") or ""),
                      str(item.get("tamanho") or ""), str(item.get("origem") or "")])


def autoteste() -> int:
    casos = []
    itens = {
        "aaa": {"arquivo": "evidencias/aaa.pdf", "preservado_em": "2026-09-03", "url": "https://x",
                "tamanho": "10", "origem": "coletar_s2id"},
        "bbb": {"arquivo": "evidencias/bbb.html", "preservado_em": "2026-08-31", "url": "https://y"},
        "ccc": {"arquivo": None, "preservado_em": "2026-09-03"},
        "ddd": {"arquivo": "evidencias/ddd.txt", "preservado_em": "2026-09-03"},
        "eee": {"arquivo": "evidencias/eee.pdf", "preservado_em": None},
        "fff": {"arquivo": "evidencias/fff.pdf", "preservado_em": "2026-09-05"},
    }
    presentes = {"aaa.pdf", "bbb.html", "eee.pdf"}   # fff.pdf indexado mas ausente do disco
    grupos = agrupar(itens, existe=lambda nome: nome in presentes)

    casos.append(("agrupa por mês de preservação", sorted(grupos) == ["2026-08", "2026-09", "sem-data"]))
    casos.append(("o mês de setembro tem só o PDF presente",
                  [n for _, n, _ in grupos["2026-09"]] == ["aaa.pdf"]))
    casos.append(("item sem arquivo fica de fora",
                  all(h != "ccc" for g in grupos.values() for h, _, _ in g)))
    casos.append(("TEXTO fica de fora do pacote (ele continua no git)",
                  all(not n.endswith(".txt") for g in grupos.values() for _, n, _ in g)))
    casos.append(("indexado mas ausente do disco fica de fora",
                  all(n != "fff.pdf" for g in grupos.values() for _, n, _ in g)))
    casos.append(("data ausente vai para sem-data",
                  [n for _, n, _ in grupos["sem-data"]] == ["eee.pdf"]))

    linha = linha_do_indice("aaa", "aaa.pdf", itens["aaa"])
    casos.append(("a linha do índice é separada por tab e traz seis campos",
                  linha.count("\t") == 5))
    casos.append(("a linha traz o hash primeiro", linha.split("\t")[0] == "aaa"))
    casos.append(("campo ausente vira string vazia, não 'None'",
                  "None" not in linha_do_indice("bbb", "bbb.html", itens["bbb"])))

    # sha256 de verdade, num arquivo temporário
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as fh:
        fh.write(b"conteudo de prova")
        tmp = pathlib.Path(fh.name)
    try:
        esperado = hashlib.sha256(b"conteudo de prova").hexdigest()
        casos.append(("o sha256 do arquivo é o do conteúdo", sha256_do_arquivo(tmp) == esperado))
    finally:
        tmp.unlink(missing_ok=True)

    ruins = [n for n, ok in casos if not ok]
    for n, ok in casos:
        print(f"  {'OK  ' if ok else 'FALHA'} {n}")
    if ruins:
        print(f"X AUTOTESTE: {len(ruins)} caso(s) reprovado(s).")
        return 1
    print(f"OK AUTOTESTE — {len(casos)} casos, sem tocar em evidencias/.")
    return 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()

    itens = json.loads(INDICE.read_text(encoding="utf-8")).get("itens") or {}
    grupos = agrupar(itens)
    total = sum(len(v) for v in grupos.values())
    peso = {m: sum((EVIDENCIAS / n).stat().st_size for _, n, _ in v) for m, v in grupos.items()}
    print(f"{total} binário(s) presentes, em {len(grupos)} mês(es):")
    for m, v in grupos.items():
        print(f"  {m}: {len(v)} arquivo(s), {peso[m] / 1e6:.1f} MB")

    if "--mes" not in sys.argv:
        print("\nrelatório apenas. Para montar um lote: --mes AAAA-MM --saida <dir>")
        return 0
    mes = sys.argv[sys.argv.index("--mes") + 1]
    if mes not in grupos:
        print(f"✗ mês {mes} não tem binário presente")
        return 1
    destino = pathlib.Path(sys.argv[sys.argv.index("--saida") + 1] if "--saida" in sys.argv else ".")
    destino.mkdir(parents=True, exist_ok=True)
    pacote = destino / f"evidencias-{mes}.zip"

    divergentes, escritos = [], 0
    with zipfile.ZipFile(pacote, "w", zipfile.ZIP_DEFLATED) as z:
        linhas = ["hash\tarquivo\turl\tpreservado_em\ttamanho\torigem"]
        for h, nome, item in grupos[mes]:
            caminho = EVIDENCIAS / nome
            # a chave do índice É o sha256 do binário: hash que não bate não entra no pacote
            if sha256_do_arquivo(caminho) != h:
                divergentes.append(nome)
                continue
            z.write(caminho, arcname=nome)
            linhas.append(linha_do_indice(h, nome, item))
            escritos += 1
        z.writestr("INDICE.tsv", "\n".join(linhas) + "\n")

    print(f"\n✓ {pacote} — {escritos} arquivo(s), {pacote.stat().st_size / 1e6:.1f} MB")
    if divergentes:
        print(f"✗ {len(divergentes)} arquivo(s) com sha256 diferente da chave do índice, FORA do "
              f"pacote: {', '.join(divergentes[:5])}")
    print("\nPublicar (exige credencial; este script não publica sozinho):")
    print(f"  gh release create evidencias-{mes} {pacote} \\")
    print(f"    --title 'Evidências preservadas — {mes}' \\")
    print(f"    --notes 'Lote mensal de evidências preservadas (item 3, 28/09/2026). "
          f"Índice em INDICE.tsv; a chave de cada arquivo é o sha256 do binário.'")
    return 1 if divergentes else 0


if __name__ == "__main__":
    sys.exit(main())
