#!/usr/bin/env python3
"""Portão do ENCANAMENTO dos passos que decidem (07/10/2026).

Nenhuma decisão de workflow desta árvore passa pelo status de um cano. O Actions roda
`bash -e {0}` quando o passo não declara `shell:`, e `bash -e` **não** tem `pipefail`: o status de
`cmd | tee` é o do `tee`, que é sempre 0. Entre 06/10/2026 22:26 UTC e 07/10/2026 16:00 UTC a
guarda da janela respondeu `pode=1` em toda execução por causa disso, e a `main` recebeu nove
commits de coleta durante o dia — a regra existia, tinha script correto e nunca barrou nada.

O que este portão reprova:

1. `if ! <cmd> | tee ...` em qualquer workflow: o `tee` sai 0 sempre, então a decisão nunca vê a
   falha. `if <cmd> | grep -q`, ao contrário, lê o `grep` de propósito, e passa.
2. passo de GUARDA ou de QUARENTENA que termine em cano sem `pipefail` efetivo — isto é, num job
   que não declare `shell: bash` nem `defaults.run.shell`.
3. workflow da CORRENTE NOTURNA cujo job não declare `shell: bash`: ali todo passo decide algo.

Não reprova cano em passo que só imprime, nem cano com `|| true` ou `|| echo` explícito: ali está
escrito que a falha não barra, e é isso que se quer.

USO
    python3 scripts/verificar_encanamento_de_portao.py
    python3 scripts/verificar_encanamento_de_portao.py --autoteste
"""
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
FLUXOS = RAIZ / ".github" / "workflows"

# A corrente noturna: aqui todo passo decide se coleta, se escreve ou se publica.
DA_CORRENTE = ("_coletor.yml", "publicar_dados.yml", "consolidar_noite.yml",
               "ensaio_da_noite.yml", "noturno_diarios.yml", "noturno_descoberta.yml",
               "noturno_evidencias.yml", "noturno_juiz.yml", "noturno_sinais.yml",
               "noturno_triagem.yml", "busca_web_cadencia.yml")

PALAVRAS_DE_DECISAO = ("guarda", "quarentena", "janela", "esquema_de_pista", "commit_do_elo")

RE_IF_COM_CANO = re.compile(
    r"^\s*if\s+(!\s+)?[^#\n]*\|\s*(tee|cat)\b[^\n]*;\s*then", re.MULTILINE)


def tem_pipefail(texto: str) -> bool:
    """O job declara um shell que traz `pipefail`? Função pura.

    `shell: bash` faz o Actions rodar `bash --noprofile --norc -eo pipefail {0}`. Sem declaração,
    ele roda `bash -e {0}`, sem `pipefail`.
    """
    return bool(re.search(r"^\s*shell:\s*bash\s*$", texto or "", re.MULTILINE))


def escapa_do_cano(linha: str) -> bool:
    """A linha diz, por escrito, que a falha não barra? Função pura."""
    return "|| true" in linha or "|| echo" in linha or "|| {" in linha


def decisoes_por_cano(texto: str) -> list:
    """`if` que lê o status de um cano. Função pura."""
    fora = []
    for m in RE_IF_COM_CANO.finditer(texto or ""):
        linha = m.group(0).strip()
        if linha.startswith("#") or escapa_do_cano(linha):
            continue
        fora.append(linha[:120])
    return fora


def passos_de_decisao_sem_pipefail(texto: str) -> list:
    """Passo de guarda/quarentena que termina em cano num arquivo sem `pipefail`. Função pura."""
    if tem_pipefail(texto):
        return []
    fora = []
    for linha in (texto or "").split("\n"):
        nua = linha.strip()
        if nua.startswith("#") or "|" not in nua:
            continue
        if not any(p in nua for p in PALAVRAS_DE_DECISAO):
            continue
        if escapa_do_cano(nua) or nua.lstrip("- ").startswith(("echo", "run: echo", "printf")):
            continue
        fora.append(nua[:120])
    return fora


def problemas(nome: str, texto: str) -> list:
    """Tudo o que reprova neste arquivo. Função pura."""
    fora = [f"{nome}: decisão pelo status de um cano — `{linha}`"
            for linha in decisoes_por_cano(texto)]
    fora += [f"{nome}: passo de decisão em cano sem `pipefail` — `{linha}`"
             for linha in passos_de_decisao_sem_pipefail(texto)]
    tem_run = re.search(r"^\s+-?\s*run:\s", texto or "", re.MULTILINE) is not None
    if nome in DA_CORRENTE and tem_run and not tem_pipefail(texto):
        fora.append(f"{nome}: workflow da corrente noturna sem `shell: bash` no job — "
                    "sem `pipefail`, o status de todo cano é o do último comando")
    return fora


def _autoteste() -> int:
    casos, contados = [], []

    def ok(nome, cond):
        contados.append(nome)
        casos.append((nome, bool(cond)))

    RUIM = ("jobs:\n  x:\n    runs-on: ubuntu-latest\n    steps:\n"
            "      - run: |\n"
            "          if ! python3 scripts/guarda_da_janela.py --ramo main | tee -a \"$S\"; then\n"
            "            echo pode=0\n          fi\n")
    BOM = ("jobs:\n  x:\n    runs-on: ubuntu-latest\n    defaults:\n      run:\n"
           "        shell: bash\n    steps:\n"
           "      - run: |\n"
           "          if python3 scripts/guarda_da_janela.py --ramo main > /tmp/g.txt; then\n"
           "            echo pode=1\n          fi\n          cat /tmp/g.txt\n")

    ok("o `if` com cano reprova", decisoes_por_cano(RUIM) != [])
    ok("sem cano no `if`, não reprova", decisoes_por_cano(BOM) == [])
    ok("`shell: bash` é reconhecido", tem_pipefail(BOM) and not tem_pipefail(RUIM))
    ok("guarda em cano sem pipefail reprova", passos_de_decisao_sem_pipefail(RUIM) != [])
    ok("com pipefail, o mesmo cano passa", passos_de_decisao_sem_pipefail(BOM) == [])
    ok("`|| true` diz que não barra, e passa",
       decisoes_por_cano("      - run: if python3 x.py | tee a.txt || true; then :; fi\n") == [])
    ok("`|| echo` idem",
       passos_de_decisao_sem_pipefail(
           "      - run: python3 scripts/verificar_esquema_de_pista.py | tee a || echo falhou\n") == [])
    ok("`echo` em cano não é decisão",
       passos_de_decisao_sem_pipefail('      - run: echo "guarda ok" | tee -a "$S"\n') == [])
    ok("comentário não conta",
       decisoes_por_cano("      # if ! python3 x.py | tee a.txt; then\n") == [])
    ok("arquivo da corrente sem shell, e com passo `run:`, reprova",
       any("corrente noturna" in p for p in problemas("_coletor.yml", RUIM)))
    ok("arquivo da corrente com shell não reprova por isso",
       not any("corrente noturna" in p for p in problemas("_coletor.yml", BOM)))
    ok("arquivo fora da corrente não exige shell",
       not any("corrente noturna" in p for p in problemas("outro.yml", BOM.replace("shell: bash", "x: y"))))
    ok("quarentena em cano sem pipefail reprova",
       passos_de_decisao_sem_pipefail(
           "      - run: python3 scripts/verificar_esquema_de_pista.py | tee -a \"$S\"\n") != [])
    ok("`if cmd | grep -q` não é decisão perdida",
       decisoes_por_cano('      - run: if echo "$A" | grep -q x; then :; fi\n') == []),
    ok("invólucro sem passo `run:` não exige shell",
       not any("corrente noturna" in p
               for p in problemas("noturno_diarios.yml",
                                  "jobs:\n  x:\n    uses: ./.github/workflows/_coletor.yml\n")))
    ok("texto vazio não quebra", problemas("x.yml", "") == [] or True)
    ok("texto nulo não quebra", decisoes_por_cano(None) == [])

    # Trava estrutural: as funções puras não leem disco nem vão à rede.
    import dis
    nomes = set()
    for fn in (tem_pipefail, escapa_do_cano, decisoes_por_cano,
               passos_de_decisao_sem_pipefail, problemas):
        nomes |= {i.argval for i in dis.get_instructions(fn.__code__) if isinstance(i.argval, str)}
    ok("trava estrutural: as funções puras não leem disco nem vão à rede",
       not ({"read_text", "open", "urlopen", "write_text"} & nomes))

    ruins = [n for n, bom in casos if not bom]
    for n, bom in casos:
        print(f"  {'✓' if bom else '✗'} {n}")
    if ruins:
        print(f"✗ AUTOTESTE: {len(ruins)} caso(s) reprovado(s).")
        return 1
    print(f"✓ AUTOTESTE OK — {len(contados)} casos, sem rede e sem escrita.")
    return 0


def main(argv: list) -> int:
    if "--autoteste" in argv:
        return _autoteste()
    if not FLUXOS.exists():
        print("✗ ENCANAMENTO: não encontrei .github/workflows")
        return 1
    ruins, n = [], 0
    for arq in sorted(FLUXOS.glob("*.yml")):
        n += 1
        ruins += problemas(arq.name, arq.read_text(encoding="utf-8"))
    if ruins:
        print(f"✗ ENCANAMENTO: {len(ruins)} problema(s) em {n} workflow(s):")
        for r in ruins:
            print(f"   - {r}")
        print("   Decisão não se toma pelo status de um cano: redirecione, leia `$?` e imprima")
        print("   depois. Em workflow da corrente, declare `shell: bash` no job.")
        return 1
    print(f"✓ ENCANAMENTO OK — {n} workflow(s); nenhuma decisão pelo status de um cano, e os da "
          "corrente noturna declaram `shell: bash`.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
