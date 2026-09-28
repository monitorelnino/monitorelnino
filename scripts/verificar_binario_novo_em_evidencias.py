#!/usr/bin/env python3
"""
verificar_binario_novo_em_evidencias.py
=======================================
Nenhum binário NOVO entra em `evidencias/` pelo git.

Item 3 do handover `HANDOVER_desacoplar_pipeline_e_emagrecer_repositorio_27-09-2026.md`.

O QUE FOI MEDIDO (28/09/2026)
-----------------------------
`evidencias/` tem **1,5 GB em 3.755 arquivos**, e o pack do git passa de 1 GB. A separação que importa:
**1,25 GB são binários** — 1,0 GB de PDF (619 arquivos) e 254 MB de HTML — contra **10,9 MB de texto
extraído** (101 arquivos de texto e 6 de OCR). O texto é o que a rodada lê e o que a classificação
usa; o binário é prova de registro, consultada por pessoa, não por script.

§275 (28/09/2026) — ESTE PORTÃO ESTÁ SUSPENSO, E O MOTIVO IMPORTA
------------------------------------------------------------------
A regra que ele cobra foi revertida no mesmo dia em que entrou. Na primeira noite com o `.gitignore` de
binário no ar, `monitorar_imprensa_regional.py` preservou 1.496 páginas, indexou as 1.496 e o git
ignorou os arquivos: o índice passou a afirmar cópia preservada que não existia. O erro foi de escopo —
liguei a publicação do lote de Release só ao `noturno_evidencias.yml`, mas **qualquer** coletor que
chama `preservar_evidencia` produz binário.

O portão continua aqui e continua rodando, mas como **informativo**: ele diz quantos binários novos
entraram, sem reprovar. Volta a reprovar quando a publicação do lote cobrir todo caminho que preserva e
`verificar_evidencias.py` souber aceitar "está no lote do mês" como cópia preservada.

A REGRA
-------
O **texto continua no git** (é insumo do pipeline, e o §10.1 já diz "a cópia do binário só até 5 MB, o
texto sempre"). O **binário novo não entra**: vai para um lote mensal publicado como ativo de Release,
com URL estável, e o índice `data/evidencias.json` guarda o hash, a URL de origem, a data, o tamanho e
onde o arquivo está.

O que já está commitado **não é removido por este portão**. Remover 1,25 GB de prova preservada é ação
irreversível na árvore e precisa da palavra da editoria — e reescrever o histórico, mais ainda.

USO
  python3 scripts/verificar_binario_novo_em_evidencias.py             # confere o que está staged
  python3 scripts/verificar_binario_novo_em_evidencias.py --contra origin/main
  python3 scripts/verificar_binario_novo_em_evidencias.py --autoteste
"""
import pathlib
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]

# O que é texto (pode entrar) e o que é binário (não pode). A lista é declarada, não inferida por
# heurística de conteúdo: extensão nova exige decisão, e decisão fica registrada aqui.
TEXTO_PERMITIDO = {".txt", ".json", ".md", ".csv", ".xml"}
BINARIO_BLOQUEADO = {".pdf", ".html", ".htm", ".xlsx", ".xls", ".docx", ".doc", ".zip",
                     ".png", ".jpg", ".jpeg", ".gif", ".webp", ".odt", ".ods"}


def novos_em_evidencias(contra: str = None) -> list:
    """Os caminhos ACRESCENTADOS sob `evidencias/`, comparando com o índice ou com um ref."""
    if contra:
        cmd = ["git", "diff", "--name-only", "--diff-filter=A", f"{contra}...HEAD"]
    else:
        cmd = ["git", "diff", "--name-only", "--diff-filter=A", "--cached"]
    saida = subprocess.run(cmd, cwd=RAIZ, capture_output=True, text=True)
    return [c for c in saida.stdout.splitlines() if c.startswith("evidencias/")]


def classificar(caminhos: list) -> tuple:
    """(bloqueados, permitidos, desconhecidos). Extensão fora das duas listas é DESCONHECIDA e
    bloqueia — a dúvida não passa calada."""
    bloqueados, permitidos, desconhecidos = [], [], []
    for c in caminhos:
        ext = pathlib.PurePosixPath(c).suffix.lower()
        if ext in BINARIO_BLOQUEADO:
            bloqueados.append(c)
        elif ext in TEXTO_PERMITIDO:
            permitidos.append(c)
        else:
            desconhecidos.append(c)
    return bloqueados, permitidos, desconhecidos


def autoteste() -> int:
    casos = []
    caminhos = ["evidencias/aaa.pdf", "evidencias/bbb.html", "evidencias/ccc.txt",
                "evidencias/ddd.json", "evidencias/eee.odt", "evidencias/fff.zzz",
                "data/municipios.json"]
    bloq, perm, desc = classificar([c for c in caminhos if c.startswith("evidencias/")])

    casos.append(("PDF é bloqueado", "evidencias/aaa.pdf" in bloq))
    casos.append(("HTML é bloqueado", "evidencias/bbb.html" in bloq))
    casos.append(("ODT é bloqueado", "evidencias/eee.odt" in bloq))
    casos.append(("texto extraído passa", "evidencias/ccc.txt" in perm))
    casos.append(("json passa", "evidencias/ddd.json" in perm))
    casos.append(("extensão desconhecida NÃO passa calada", "evidencias/fff.zzz" in desc))
    casos.append(("nada fora de evidencias/ é classificado", len(bloq + perm + desc) == 6))
    casos.append(("as duas listas não se sobrepõem", not (TEXTO_PERMITIDO & BINARIO_BLOQUEADO)))
    casos.append(("lista vazia não acusa nada", classificar([]) == ([], [], [])))

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
    contra = sys.argv[sys.argv.index("--contra") + 1] if "--contra" in sys.argv else None
    bloqueados, permitidos, desconhecidos = classificar(novos_em_evidencias(contra))

    if bloqueados or desconhecidos:
        # §275: informativo enquanto a trava está revertida. Reprovar aqui, com o lote cobrindo só um
        # dos caminhos que preservam, foi o que custou 1.496 páginas de prova.
        print("! BINÁRIO NOVO EM evidencias/ (informativo, §275 — a trava está revertida):")
        for c in bloqueados:
            print(f"   - {c}")
        for c in desconhecidos:
            print(f"   - {c} (extensão não declarada — decida e registre em "
                  f"scripts/verificar_binario_novo_em_evidencias.py)")
        print("   O binário está versionado de novo (§275). O lote mensal de Release continua sendo "
              "montado por scripts/empacotar_evidencias.py, e volta a ser a única cópia quando "
              "cobrir todo caminho que preserva.")
        return 0
    print(f"✓ EVIDÊNCIAS OK — nenhum binário novo no git"
          + (f"; {len(permitidos)} arquivo(s) de texto acrescentado(s)." if permitidos else "."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
