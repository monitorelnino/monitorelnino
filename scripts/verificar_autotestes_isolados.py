#!/usr/bin/env python3
"""
verificar_autotestes_isolados.py — nenhum autoteste ALTERA `data/` · §220
=========================================================================
POR QUE ESTE PORTÃO EXISTE. Em 25/09/2026 o autoteste de um coletor gravou **oito execuções
no log de buscas real**, com uma fonte "teste" que não existe e uma consulta que nunca
aconteceu. Ele mockava a rede, os arquivos e o livro de fontes — e não mockava
`registrar_lacuna`, que chama `log_busca`, que grava. Ninguém percebeu porque o autoteste
ficou verde: autoteste prova o que o autor lembrou de provar.

A regra já existia, declarada em vários coletores ("nunca toca dado real"). O que faltava era
alguém conferir. Este portão roda cada autoteste e compara `data/` antes e depois.

DUAS COISAS DIFERENTES, E A DISTINÇÃO CUSTOU UMA ACUSAÇÃO FALSA. Comparar só tamanho e
carimbo acusa de "alterar dado" três autotestes que regravam arquivos com o MESMO conteúdo.
Reescrever idêntico é desperdício e vale mockar — mas não é o defeito. **Alterar** conteúdo é,
e é o que reprova. O caso que originou o portão cai no segundo grupo: ele acrescentou linhas.

POR QUE NÃO BASTA LER O CÓDIGO. As travas estruturais dos coletores procuram `open(...)` e
`gravar(...)` no próprio fonte, e não veem a escrita que acontece três chamadas abaixo, dentro
de `coletores_base`. Só a execução mostra.

USO
  python scripts/verificar_autotestes_isolados.py            # roda todos
  python scripts/verificar_autotestes_isolados.py --rapido   # só coletores e afins
"""
import hashlib
import pathlib
import re
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
DATA = RAIZ / "data"
FORA = {"verificar_autotestes_isolados.py"}          # evita rodar a si mesmo


def com_autoteste() -> list:
    """Todo script do projeto que aceita `--autoteste`, pelo próprio fonte. Ordenado."""
    achados = []
    for arq in sorted(list(RAIZ.glob("*.py")) + list(RAIZ.glob("scripts/*.py"))):
        if arq.name in FORA:
            continue
        try:
            fonte = arq.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if re.search(r'["\']--autoteste["\']', fonte):
            achados.append(arq)
    return achados


def retrato(anterior: dict = None) -> dict:
    """(tamanho, carimbo, hash) de cada arquivo de `data/`.

    O hash só é recalculado quando tamanho ou carimbo mudaram desde o retrato anterior — na
    rodada normal isso é zero arquivo, e o portão não lê os 20 MB do log à toa."""
    fotos = {}
    for f in DATA.rglob("*"):
        if not f.is_file():
            continue
        rel = f.relative_to(RAIZ).as_posix()
        st = f.stat()
        marca = (st.st_size, st.st_mtime_ns)
        antes = (anterior or {}).get(rel)
        if antes and antes[:2] == marca:
            fotos[rel] = antes                      # nada mudou: reaproveita o hash
        else:
            fotos[rel] = marca + (hashlib.sha256(f.read_bytes()).hexdigest(),)
    return fotos


def diferenca(antes: dict, depois: dict) -> tuple:
    """(alterados de verdade, reescritos iguais). Função pura.

    Criado, removido ou com hash diferente conta como ALTERADO. Mesmo hash com carimbo novo é
    reescrita inócua — reportada como aviso, nunca como reprovação."""
    suspeitos = [c for c in set(antes) | set(depois) if antes.get(c) != depois.get(c)]
    alterados, iguais = [], []
    for c in sorted(suspeitos):
        a, d = antes.get(c), depois.get(c)
        if a is None or d is None or a[2] != d[2]:
            alterados.append(c)
        else:
            iguais.append(c)
    return alterados, iguais


def main(args) -> int:
    scripts = com_autoteste()
    if "--rapido" in args:
        scripts = [s for s in scripts if s.name.startswith(("coletar_", "descobrir_", "monitorar_"))]
    print(f"{len(scripts)} script(s) com autoteste; conferindo que nenhum altera data/")
    sujos, gastadores, quebrados = [], [], []
    antes = retrato()
    for s in scripts:
        rel = s.relative_to(RAIZ).as_posix()
        r = subprocess.run([sys.executable, str(s), "--autoteste"], cwd=RAIZ,
                           capture_output=True, timeout=600)
        depois = retrato(antes)
        alterados, iguais = diferenca(antes, depois)
        if alterados:
            sujos.append((rel, alterados[:4]))
        if iguais:
            gastadores.append((rel, iguais[:4]))
        if alterados or iguais:
            antes = depois            # não repete a mesma acusação no próximo script
        if r.returncode != 0:
            ultima = (r.stdout or b"").decode("utf-8", "replace").strip().split("\n")[-1][:120]
            quebrados.append((rel, ultima))
    for rel, erro in quebrados:
        print(f"  [autoteste vermelho] {rel}: {erro}")
    for rel, arquivos in gastadores:
        print(f"  ⚠ {rel} regrava {', '.join(arquivos)} com o MESMO conteúdo — inócuo, mas é "
              "escrita em data/ durante autoteste; vale mockar")
    if sujos:
        print("\n✗ AUTOTESTES ISOLADOS: autoteste que ALTERA data/ não é autoteste offline:")
        for rel, arquivos in sujos:
            print(f"    {rel} alterou {', '.join(arquivos)}")
        print("    Conserto: mockar TAMBÉM o que grava indiretamente — registrar_lacuna e log_busca\n"
              "    chamam gravar() dentro de coletores_base, mesmo com a rede mockada.")
        return 1
    print(f"✓ AUTOTESTES ISOLADOS OK — {len(scripts)} autoteste(s) rodados, nenhum ALTEROU data/."
          + (f" ({len(quebrados)} autoteste(s) vermelho(s), reportado(s) pelos portões próprios.)"
             if quebrados else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
