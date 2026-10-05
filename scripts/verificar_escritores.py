#!/usr/bin/env python3
"""
scripts/verificar_escritores.py — um escritor por arquivo, ou uma resolução declarada
=====================================================================================
Item 2.3 do `HANDOVER_noite_confiavel_05-10-2026.md`.

POR QUE ELE EXISTE. Na noite de 04→05/10 a busca web **perdeu 114 minutos de trabalho**: o commit
com rebase falhou quatro vezes por conflito em `data/pistas_imprensa.json`,
`data/pistas_revisao.json` e `docs/MANIFEST_SHA256.txt`. A causa é de desenho — vários elos gravam
os mesmos arquivos compartilhados em paralelo, e a busca web passou a correr ao lado dos diários em
03/10.

Há duas maneiras honestas de lidar com isso, e `config/escritores.json` obriga a escolher uma, por
escrito, para cada arquivo:

  · **escritor único** — só aquele workflow commita o arquivo; corrida impossível;
  · **`qualquer_elo`** — vários commitam, e a corrida é **resolvida**: o arquivo tem de estar numa
    das classes de `scripts/unir_conflito_de_rodada.py` (log que só cresce · fila de pista ·
    derivado regenerável), ou trazer um `pendente` que diga o que falta decidir.

O que o portão reprova:

  1. arquivo com escritor único que aparece no `git add` de outro workflow;
  2. arquivo com `escritor: ninguem` que aparece em algum `git add`;
  3. arquivo `qualquer_elo` que o resolvedor **não sabe resolver** e que **não declara** `pendente`
     — é o caso em que a perda de 114 minutos volta a acontecer calada.

O portão não decide concorrência: grupo de workflow é outra coisa. Ele garante que, onde dois elos
se cruzam, a resolução esteja escrita.

USO
    python3 scripts/verificar_escritores.py --autoteste
    python3 scripts/verificar_escritores.py
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
DECLARACAO = RAIZ / "config" / "escritores.json"
WORKFLOWS = RAIZ / ".github" / "workflows"

# Os elos da corrente: workflows que commitam dado coletado. `_coletor.yml` é o invólucro
# compartilhado, e por isso vale como "qualquer elo" — é ele que todos os noturnos chamam.
INVOLUCRO_DOS_ELOS = "_coletor.yml"


def ler_declaracao(caminho=None) -> dict:
    try:
        doc = json.loads(pathlib.Path(caminho or DECLARACAO).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return doc.get("arquivos") or {}


def caminhos_no_git_add(fonte: str) -> set:
    """Os caminhos que este workflow marca para commit. Função pura.

    Lê as linhas de `git add`, ignorando comentário. `-A` e as opções não são caminho; `*.html` e
    outros curingas também não entram, porque este portão fala de arquivo nomeado.
    """
    fora = set()
    for linha in str(fonte or "").splitlines():
        nua = linha.strip()
        if nua.startswith("#") or "git add" not in nua:
            continue
        depois = nua.split("git add", 1)[1]
        # Corta o que vem depois de um encadeamento: `git add x && git commit` não adiciona o
        # `git`, o `commit` nem a mensagem.
        depois = re.split(r"&&|\|\||;|2>|\|", depois)[0]
        for peca in depois.split():
            peca = peca.strip("\"'")
            if not peca or peca.startswith("-") or "*" in peca or peca.startswith("$"):
                continue
            fora.add(peca.rstrip("/") + ("/" if peca.endswith("/") else ""))
    return fora


def classes_do_resolvedor() -> set:
    """Os caminhos e prefixos que `unir_conflito_de_rodada.py` sabe resolver."""
    sys.path.insert(0, str(RAIZ / "scripts"))
    try:
        import unir_conflito_de_rodada as u
    except ImportError:
        return set()
    return (set(u.LOGS_QUE_SO_CRESCEM) | set(u.REGENERAVEIS)
            | set(getattr(u, "FILAS_DE_PISTA", ())) | set(u.PREFIXOS_REGENERAVEIS))


def resolvido_pelo_resolvedor(caminho: str, classes: set) -> bool:
    """O resolvedor sabe resolver conflito neste caminho? Função pura."""
    c = str(caminho or "").replace("\\", "/")
    if c in classes:
        return True
    return any(c.startswith(x) for x in classes if str(x).endswith("/"))


def problemas(declarados: dict, por_workflow: dict, classes: set) -> list:
    """As violações. Função pura.

    `por_workflow` é {nome_do_arquivo_yml: {caminhos no git add}}.
    """
    fora = []
    for caminho, regra in sorted((declarados or {}).items()):
        if caminho.startswith("_"):
            continue
        escritor = str((regra or {}).get("escritor") or "").strip()
        pendente = str((regra or {}).get("pendente") or "").strip()
        quem_commita = sorted(wf for wf, caminhos in (por_workflow or {}).items()
                              if caminho in caminhos)

        if escritor == "ninguem":
            for wf in quem_commita:
                fora.append(f"{caminho}: declarado `escritor: ninguem` e {wf} o commita — "
                            f"só a editoria muda este arquivo")
            continue

        if escritor == "qualquer_elo":
            # `sem_colisao_possivel`: o caminho é endereçado pelo CONTEÚDO (nome = hash), de modo
            # que dois elos nunca escrevem o mesmo arquivo. Não há conflito a resolver, e exigir
            # uma classe do resolvedor seria exigir resposta a uma pergunta que não existe.
            if (regra or {}).get("sem_colisao_possivel"):
                continue
            if not resolvido_pelo_resolvedor(caminho, classes) and not pendente:
                fora.append(f"{caminho}: declarado `qualquer_elo` e o resolvedor NÃO sabe "
                            f"resolvê-lo — ou ele entra numa classe de "
                            f"unir_conflito_de_rodada.py, ou declara `pendente` dizendo o que "
                            f"falta decidir")
            continue

        if not escritor:
            fora.append(f"{caminho}: sem `escritor` declarado")
            continue

        # Escritor único: ninguém mais pode commitar. O invólucro dos elos conta como elo, e por
        # isso um arquivo de escritor único jamais pode estar no `git add` dele.
        for wf in quem_commita:
            if wf != escritor:
                fora.append(f"{caminho}: escritor declarado é {escritor}, mas {wf} também o "
                            f"commita")
    return fora


def _autoteste() -> int:
    falhas = []
    # O total era um literal e envelhecia calado: dizia cobrir mais casos do que
    # cobre, ou menos. Agora e contado.
    _casos_contados = []

    def ok(nome, cond):
        _casos_contados.append(nome)
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    # ---- a leitura do `git add` ----
    ok("o caminho nomeado é reconhecido",
       caminhos_no_git_add("          git add data/ docs/MANIFEST_SHA256.txt")
       == {"data/", "docs/MANIFEST_SHA256.txt"})
    ok("as opções não são caminho",
       "-A" not in caminhos_no_git_add("git add -A data/"))
    ok("o curinga não é caminho",
       caminhos_no_git_add("git add *.html data/") == {"data/"})
    ok("o encadeamento não vira caminho",
       caminhos_no_git_add("git add -A && git commit -q -m x") == set())
    ok("o redirecionamento não vira caminho",
       caminhos_no_git_add("git add data/ 2>/dev/null || true") == {"data/"})
    ok("comentário que cita git add é ignorado",
       caminhos_no_git_add("   # o `git add` nunca o incluiu") == set())
    ok("variável não vira caminho",
       caminhos_no_git_add('git add -A "$alvo"') == set())

    # ---- o resolvedor ----
    classes = {"data/log_buscas.json", "docs/MANIFEST_SHA256.txt", "dados-abertos/"}
    ok("caminho exato numa classe é resolvido",
       resolvido_pelo_resolvedor("data/log_buscas.json", classes))
    ok("caminho sob prefixo de classe é resolvido",
       resolvido_pelo_resolvedor("dados-abertos/x.csv", classes))
    ok("caminho fora das classes não é resolvido",
       not resolvido_pelo_resolvedor("data/municipios.json", classes))

    # ---- as três reprovações ----
    D = {
        "data/municipios.json": {"escritor": "atualizar.yml", "por_que": "o banco"},
        "data/publicacao.json": {"escritor": "ninguem", "por_que": "a editoria"},
        "data/log_buscas.json": {"escritor": "qualquer_elo", "por_que": "log"},
        "data/novo.json": {"escritor": "qualquer_elo", "por_que": "sem resolução"},
    }
    ok("escritor único commitado pelo próprio passa",
       problemas({"data/municipios.json": D["data/municipios.json"]},
                 {"atualizar.yml": {"data/municipios.json"}}, classes) == [])
    p = problemas({"data/municipios.json": D["data/municipios.json"]},
                  {"_coletor.yml": {"data/municipios.json"}}, classes)
    ok("escritor único commitado por outro REPROVA",
       len(p) == 1 and "também o commita" in p[0])
    p = problemas({"data/publicacao.json": D["data/publicacao.json"]},
                  {"atualizar.yml": {"data/publicacao.json"}}, classes)
    ok("`escritor: ninguem` commitado por alguém REPROVA",
       len(p) == 1 and "ninguem" in p[0])
    ok("`qualquer_elo` que o resolvedor resolve passa",
       problemas({"data/log_buscas.json": D["data/log_buscas.json"]},
                 {"_coletor.yml": {"data/log_buscas.json"}}, classes) == [])
    p = problemas({"data/novo.json": D["data/novo.json"]}, {}, classes)
    ok("`qualquer_elo` sem resolução e sem `pendente` REPROVA",
       len(p) == 1 and "NÃO sabe" in p[0])
    ok("`qualquer_elo` endereçado pelo conteúdo passa sem classe nem pendência",
       problemas({"evidencias/": {"escritor": "qualquer_elo", "por_que": "hash",
                                  "sem_colisao_possivel": True}},
                 {"_coletor.yml": {"evidencias/"}}, classes) == [])
    ok("`qualquer_elo` sem resolução mas com `pendente` passa",
       problemas({"data/novo.json": dict(D["data/novo.json"], pendente="a editoria decide")},
                 {}, classes) == [])
    p = problemas({"data/x.json": {"por_que": "esqueci"}}, {}, classes)
    ok("arquivo sem `escritor` REPROVA", len(p) == 1 and "sem `escritor`" in p[0])
    ok("as chaves de governança (com _) são ignoradas",
       problemas({"_governanca": "texto"}, {}, classes) == [])
    ok("declaração vazia não quebra", problemas({}, {}, classes) == [])

    # ---- a declaração real ----
    real = ler_declaracao()
    ok("config/escritores.json existe e declara arquivos", len(real) >= 10)
    ok("todo arquivo real declara `escritor` e `por_que`",
       all(r.get("escritor") and r.get("por_que")
           for k, r in real.items() if not k.startswith("_")))
    ok("data/publicacao.json é de ninguém — só a editoria",
       real.get("data/publicacao.json", {}).get("escritor") == "ninguem")

    import dis
    nomes = set()
    for nome_obj in ("caminhos_no_git_add", "resolvido_pelo_resolvedor", "problemas"):
        codigo = getattr(globals()[nome_obj], "__code__", None)
        if codigo is not None:
            nomes |= {i.argval for i in dis.get_instructions(codigo) if isinstance(i.argval, str)}
    ok("trava estrutural: as funções puras não leem o disco nem escrevem",
       not ({"read_text", "write_text", "gravar", "rglob"} & nomes))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else f"✓ AUTOTESTE OK — {len(_casos_contados)} casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def main() -> int:
    if "--autoteste" in sys.argv[1:]:
        return _autoteste()
    declarados = ler_declaracao()
    if not declarados:
        print("✗ ESCRITORES: config/escritores.json não pôde ser lido")
        return 1
    por_workflow = {}
    for yml in sorted(WORKFLOWS.glob("*.yml")):
        try:
            por_workflow[yml.name] = caminhos_no_git_add(yml.read_text(encoding="utf-8"))
        except OSError:
            continue
    p = problemas(declarados, por_workflow, classes_do_resolvedor())
    if p:
        print(f"✗ ESCRITORES: {len(p)} arquivo(s) sem um escritor único nem resolução declarada:")
        for x in p:
            print("   - " + x)
        print("   Onde dois elos se cruzam, a resolução tem de estar escrita: escritor único em")
        print("   config/escritores.json, ou uma classe de unir_conflito_de_rodada.py.")
        return 1
    uteis = [k for k in declarados if not k.startswith("_")]
    print(f"✓ ESCRITORES OK — {len(uteis)} arquivo(s) declarado(s), "
          f"{len(por_workflow)} workflow(s) conferido(s); nenhuma sobreposição sem resolução.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
