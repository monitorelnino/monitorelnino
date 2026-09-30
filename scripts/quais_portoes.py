#!/usr/bin/env python3
"""Diz quais portões a mudança em curso pode afetar — e, portanto, quais rodar antes do commit.

Item 3 do handover de otimização do ciclo de mudança (editoria, 30/09/2026).

A MESMA REGRA DA CI, NUM LUGAR SÓ
---------------------------------
A CI já decide isso por caminho alterado (`dado_mudou`, `pagina_mudou` em `portoes.yml`). Este
script aplica **o mesmo critério** localmente, para o que se roda antes do commit ser o que a CI vai
cobrar — nem menos (e descobrir o vermelho depois de esperar a fila), nem mais (e pagar quatro
minutos de navegador num PR que só mexeu num coletor).

O PADRÃO É AMPLO DE PROPÓSITO. Falso positivo custa tempo; falso negativo custa um defeito no ar.
Na dúvida — nenhum arquivo reconhecido, ou nada alterado — ele manda rodar tudo.

USO
  python3 scripts/quais_portoes.py                 # compara com origin/main
  python3 scripts/quais_portoes.py --contra HEAD~1
  python3 scripts/quais_portoes.py --comando       # imprime a linha pronta para rodar
  python3 scripts/quais_portoes.py --autoteste
"""
import pathlib
import re
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent

RE_DADO = re.compile(r"(^|/)data/|\.py$|^requirements\.txt$|^\.github/workflows/")
RE_PAGINA = re.compile(r"\.html$|^assets/|^docs/fichas_semanticas\.json$"
                       r"|^scripts/verificar_(legendas|vocabulario_publico|voz_editorial"
                       r"|fichas_semanticas|figuras|movel|consistencia_visual)\.js$")

SEMPRE = ["python3 scripts/verificar_marcadores_de_conflito.py",
          "python3 scripts/validar_workflows.py",
          "node scripts/verificar_estrutura.js",
          "node scripts/verificar_runtime.js",
          "node scripts/verificar_acessibilidade.js",
          "node scripts/verificar_seguranca.js",
          "node scripts/verificar_palavras.js"]
DE_PAGINA = ["node scripts/verificar_vocabulario_publico.js",
             "node scripts/verificar_voz_editorial.js",
             "node scripts/verificar_figuras.js",
             "node scripts/verificar_fichas_semanticas.js",
             "node scripts/verificar_legendas.js",
             "node scripts/verificar_movel.js",
             "node scripts/verificar_consistencia_visual.js"]
DE_DADO = ["python3 scripts/verificar_paridade_cobertura_qd.py",
           "python3 scripts/testar_contador_varredura.py",
           "python3 scripts/verificar_cliente_identificado.py",
           "python3 scripts/verificar_escrita_portavel.py",
           "bash scripts/verificar_derivados.sh --pode-regenerar"]


def classificar(arquivos: list) -> dict:
    """{'dado': bool, 'pagina': bool}. Função pura — mesma regra da CI.

    Lista vazia devolve os dois como verdadeiros: "não sei o que mudou" não é "nada mudou"."""
    if not arquivos:
        return {"dado": True, "pagina": True}
    return {"dado": any(RE_DADO.search(a) for a in arquivos),
            "pagina": any(RE_PAGINA.search(a) for a in arquivos)}


def portoes(marcas: dict) -> list:
    """Os comandos a rodar, na ordem do barato para o caro. Função pura."""
    fila = list(SEMPRE)
    if marcas.get("pagina"):
        fila += DE_PAGINA
    if marcas.get("dado"):
        fila += DE_DADO
    return fila


def alterados(contra: str) -> list:
    r = subprocess.run(["git", "diff", "--name-only", contra], capture_output=True, text=True,
                       cwd=RAIZ)
    fora = [a.strip() for a in r.stdout.split("\n") if a.strip()]
    r2 = subprocess.run(["git", "diff", "--name-only"], capture_output=True, text=True, cwd=RAIZ)
    fora += [a.strip() for a in r2.stdout.split("\n") if a.strip()]
    return sorted(set(fora))


def autoteste() -> int:
    casos = []
    casos.append(("página HTML aciona os de página",
                  classificar(["index.html"]) == {"dado": False, "pagina": True}))
    casos.append(("folha em assets/ aciona os de página",
                  classificar(["assets/base.css"])["pagina"] is True))
    casos.append(("ficha semântica aciona os de página",
                  classificar(["docs/fichas_semanticas.json"])["pagina"] is True))
    casos.append(("coletor .py aciona os de dado, e NÃO os de página",
                  classificar(["coletar_sinais_risco.py"]) == {"dado": True, "pagina": False}))
    casos.append(("arquivo em data/ aciona os de dado",
                  classificar(["data/indice.json"])["dado"] is True))
    casos.append(("workflow aciona os de dado",
                  classificar([".github/workflows/atualizar.yml"])["dado"] is True))
    casos.append(("mudança nos dois aciona os dois",
                  classificar(["index.html", "recalcular_mare.py"])
                  == {"dado": True, "pagina": True}))
    casos.append(("o próprio portão de legendas aciona os de página",
                  classificar(["scripts/verificar_legendas.js"])["pagina"] is True))
    casos.append(("portão de dado em .py aciona os de dado",
                  classificar(["scripts/verificar_paridade_cobertura_qd.py"])["dado"] is True))
    casos.append(("arquivo desconhecido não aciona nada além do sempre",
                  classificar(["LEIA-ME.txt"]) == {"dado": False, "pagina": False}))
    casos.append(("NADA alterado manda rodar tudo — 'não sei' não é 'nada'",
                  classificar([]) == {"dado": True, "pagina": True}))

    casos.append(("o sempre roda em qualquer caso",
                  all(c in portoes({"dado": False, "pagina": False}) for c in SEMPRE)))
    casos.append(("sem página, nada de navegador",
                  not any("movel" in c or "consistencia" in c
                          for c in portoes({"dado": True, "pagina": False}))))
    casos.append(("sem dado, nada de paridade",
                  not any("paridade" in c for c in portoes({"dado": False, "pagina": True}))))
    casos.append(("os baratos vêm antes dos de navegador",
                  portoes({"dado": True, "pagina": True}).index("node scripts/verificar_estrutura.js")
                  < portoes({"dado": True, "pagina": True}).index("node scripts/verificar_movel.js")))
    casos.append(("o portão 12 entra no modo do PR",
                  "bash scripts/verificar_derivados.sh --pode-regenerar"
                  in portoes({"dado": True, "pagina": False})))

    ruins = [n for n, ok in casos if not ok]
    for n, ok in casos:
        print(f"  {'OK  ' if ok else 'FALHA'} {n}")
    if ruins:
        print(f"X AUTOTESTE: {len(ruins)} caso(s) reprovado(s).")
        return 1
    print(f"OK AUTOTESTE — {len(casos)} casos, sem rede e sem escrita.")
    return 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    contra = "origin/main"
    if "--contra" in sys.argv:
        contra = sys.argv[sys.argv.index("--contra") + 1]
    arquivos = alterados(contra)
    marcas = classificar(arquivos)
    fila = portoes(marcas)
    if "--comando" in sys.argv:
        print(" && ".join(fila))
        return 0
    print(f"{len(arquivos)} arquivo(s) alterado(s) contra {contra}")
    print(f"toca dado: {'sim' if marcas['dado'] else 'não'} · "
          f"toca página: {'sim' if marcas['pagina'] else 'não'}")
    print(f"portões a rodar ({len(fila)}):")
    for c in fila:
        print("  " + c)
    if not marcas["pagina"]:
        print("(navegador e portões de texto pulados — nada de página mudou)")
    if not marcas["dado"]:
        print("(portões de dado pulados — nada de dado ou coleta mudou)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
