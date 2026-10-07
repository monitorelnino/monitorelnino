#!/usr/bin/env python3
"""
scripts/commit_do_elo.py — cada elo comita só os seus arquivos
================================================================
Item 1 do `HANDOVER_noite_confiavel_parte2_06-10-2026.md`.

O QUE ACONTECEU
---------------
A regra "um escritor por arquivo, ou uma resolução declarada" estava **registrada** em
`config/escritores.json` e **não aplicada**: todo elo terminava com

    git add -A data/ dados-abertos/ feeds/ selos/ evidencias/ docs/MANIFEST_SHA256.txt docs/FILA_PISTAS.md

e levava junto arquivo que não era dele. Na noite de 05→06/10 isso custou, só nos elos medidos,
**364 minutos de coleta descartados**: os diários perderam 100 minutos num conflito em
`data/saude_pipeline.json`, e a busca web perdeu 136 e 128 em `data/pistas_revisao.json`,
`docs/FILA_PISTAS.md` e `docs/MANIFEST_SHA256.txt`. Nenhum dos três é arquivo da busca web.

A CONTA QUE ESTE SCRIPT FAZ
----------------------------
Ele põe no índice **só o que aquele elo pode escrever**, lido de `config/escritores.json`:

  · `escritor: <elo>`      → só aquele elo. Outro elo que tenha mexido no arquivo NÃO o comita.
  · `escritor: qualquer_elo` → qualquer um pode, porque o caminho tem resolução declarada e
                               testada (fila com porta única, log que só cresce, derivado). É a
                               segunda metade da regra, e ela continua valendo.
  · `escritor: ninguem`      → ninguém comita por rotina (`data/publicacao.json`).

Caminho que termina em `/` é prefixo: vale para tudo abaixo dele.

**Caminho não declarado não entra.** É a trava que importa: arquivo novo que apareça na árvore do
runner e não esteja em `config/escritores.json` fica de fora do commit e sai listado no resumo, em
vez de entrar calado no commit de quem passou por último.

USO
  python3 scripts/commit_do_elo.py --autoteste
  python3 scripts/commit_do_elo.py <elo> --mensagem "..."      # comita
  python3 scripts/commit_do_elo.py <elo> --listar              # só diz o que entraria
"""
import json
import pathlib
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
CONFIG = RAIZ / "config" / "escritores.json"

QUALQUER = "qualquer_elo"
NINGUEM = "ninguem"


def regras(config: dict) -> dict:
    """{caminho: escritor}, só as entradas de verdade. Função pura."""
    arquivos = (config or {}).get("arquivos") or {}
    return {k: str((v or {}).get("escritor") or "")
            for k, v in arquivos.items() if not k.startswith("_")}


def escritor_de(caminho: str, tabela: dict) -> str | None:
    """Quem pode escrever este caminho, ou None se ele não está declarado. Função pura.

    A regra mais específica ganha: `data/noite/` declara a pasta, e um arquivo dentro dela herda —
    mas se o próprio arquivo estiver declarado, é a declaração dele que vale.
    """
    c = str(caminho).replace("\\", "/")
    if c in (tabela or {}):
        return tabela[c]
    melhor, tam = None, -1
    for regra, dono in (tabela or {}).items():
        r = regra.replace("\\", "/")
        if r.endswith("/") and c.startswith(r) and len(r) > tam:
            melhor, tam = dono, len(r)
    if melhor is not None:
        return melhor
    # `*.html` na RAIZ: as páginas do site são derivadas e só o publicador as comita. O padrão vale
    # só para a raiz, de propósito — `blog/x.html` é outra coisa, e tem a sua própria linha.
    if "/" not in c:
        for regra, dono in (tabela or {}).items():
            if regra.startswith("*.") and c.endswith(regra[1:]):
                return dono
    return None


def pode_comitar(caminho: str, elo: str, tabela: dict) -> bool:
    """Este elo pode pôr este caminho no índice? Função pura."""
    dono = escritor_de(caminho, tabela)
    if dono is None or dono == NINGUEM:
        return False
    return dono == QUALQUER or dono == elo


def separar(mudados: list, elo: str, tabela: dict) -> tuple:
    """(entram, de_outro_elo, nao_declarados). Função pura — é ela que o autoteste exercita."""
    entram, de_outro, sem_regra = [], [], []
    for caminho in sorted(set(mudados or [])):
        dono = escritor_de(caminho, tabela)
        if dono is None:
            sem_regra.append(caminho)
        elif pode_comitar(caminho, elo, tabela):
            entram.append(caminho)
        else:
            de_outro.append(f"{caminho} (de `{dono}`)")
    return entram, de_outro, sem_regra


def _git(*args, **kw):
    return subprocess.run(["git", *args], cwd=str(RAIZ), capture_output=True, text=True, **kw)


def mudados_na_arvore() -> list:
    """Os caminhos modificados, novos ou apagados. Lê o git; não escreve."""
    saida = _git("status", "--porcelain", "-z").stdout or ""
    fora = []
    for pedaco in saida.split("\0"):
        if len(pedaco) > 3:
            fora.append(pedaco[3:])
    return fora


def _autoteste() -> int:
    falhas, contados = [], []

    def ok(nome, cond):
        contados.append(nome)
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    T = {
        "data/municipios.json": "atualizar.yml",
        "docs/MANIFEST_SHA256.txt": "publicar",
        "docs/FILA_PISTAS.md": "triagem",
        "data/pistas_revisao.json": "triagem",
        "data/pistas_imprensa.json": QUALQUER,
        "data/publicacao.json": NINGUEM,
        "data/noite/": QUALQUER,
    }

    ok("arquivo do próprio elo entra", pode_comitar("docs/FILA_PISTAS.md", "triagem", T))
    ok("arquivo de outro elo NÃO entra", not pode_comitar("docs/FILA_PISTAS.md", "busca_web", T))
    ok("fila com resolução declarada entra para qualquer elo",
       pode_comitar("data/pistas_imprensa.json", "busca_web", T))
    ok("arquivo de `ninguem` nunca entra", not pode_comitar("data/publicacao.json", "publicar", T))
    ok("caminho não declarado não entra", not pode_comitar("data/novo.json", "busca_web", T))

    ok("prefixo vale para o que está abaixo",
       pode_comitar("data/noite/2026-10-06/diarios.feito", "diarios", T))
    ok("declaração do arquivo ganha do prefixo",
       escritor_de("data/pistas_revisao.json", dict(T, **{"data/": QUALQUER})) == "triagem")
    ok("sufixo na raiz vale para o publicador",
       escritor_de("index.html", dict(T, **{"*.html": "publicar"})) == "publicar")
    ok("sufixo na raiz NAO alcanca subpasta",
       escritor_de("blog/x.html", dict(T, **{"*.html": "publicar"})) is None)
    ok("prefixo mais longo ganha do mais curto",
       escritor_de("data/noite/x", dict(T, **{"data/": "outro"})) == QUALQUER)
    ok("barra invertida do Windows não muda a resposta",
       pode_comitar("data\\noite\\2026-10-06\\x.feito", "diarios", T))

    # O caso exato da noite de 05→06: a busca web levava três arquivos que não são dela.
    entram, de_outro, sem_regra = separar(
        ["data/pistas_imprensa.json", "data/pistas_revisao.json", "docs/FILA_PISTAS.md",
         "docs/MANIFEST_SHA256.txt", "data/inventado.json"], "busca_web", T)
    ok("a busca web comita só a fila dela", entram == ["data/pistas_imprensa.json"])
    ok("os três de outro elo ficam de fora", len(de_outro) == 3)
    ok("o não declarado é listado, não comitado", sem_regra == ["data/inventado.json"])
    ok("nada se perde da conta",
       len(entram) + len(de_outro) + len(sem_regra) == 5)

    ok("a triagem comita os dela",
       separar(["docs/FILA_PISTAS.md", "data/pistas_revisao.json"], "triagem", T)[0]
       == ["data/pistas_revisao.json", "docs/FILA_PISTAS.md"])
    ok("árvore limpa não produz commit", separar([], "triagem", T) == ([], [], []))

    cfg = {"arquivos": {"_governanca": "texto", "a.json": {"escritor": "x"}}}
    ok("a chave de governança não vira regra", regras(cfg) == {"a.json": "x"})

    import dis
    nomes = set()
    for nome_obj, obj in list(globals().items()):
        if nome_obj in ("_autoteste", "main", "_git", "mudados_na_arvore"):
            continue
        if getattr(obj, "__module__", None) not in (__name__, None):
            continue
        codigo = getattr(obj, "__code__", None)
        if codigo is not None:
            nomes |= {i.argval for i in dis.get_instructions(codigo) if isinstance(i.argval, str)}
    ok("trava estrutural: as funções puras não chamam git nem escrevem",
       not ({"subprocess", "run", "write_text", "read_text"} & nomes))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else f"✓ AUTOTESTE OK — {len(contados)} casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def main(argv: list) -> int:
    if "--autoteste" in argv:
        return _autoteste()
    sem_bandeira = [a for a in argv if not a.startswith("--")]
    if not sem_bandeira:
        print("uso: python3 scripts/commit_do_elo.py <elo> [--listar] [--mensagem TEXTO]")
        return 2
    elo = sem_bandeira[0]
    tabela = regras(json.loads(CONFIG.read_text(encoding="utf-8")))
    entram, de_outro, sem_regra = separar(mudados_na_arvore(), elo, tabela)

    for caminho in de_outro:
        print(f"  · fora do commit de `{elo}`: {caminho}")
    for caminho in sem_regra:
        print(f"  ⚠ caminho sem escritor declarado, fora do commit: {caminho}")
    if not entram:
        print(f"Sem alterações de `{elo}`.")
        print("houve=0")
        return 0
    print(f"  · no commit de `{elo}`: {len(entram)} caminho(s)")
    if "--listar" in argv:
        for caminho in entram:
            print("      " + caminho)
        return 0

    for lote in [entram[i:i + 200] for i in range(0, len(entram), 200)]:
        r = _git("add", "--", *lote)
        if r.returncode != 0:
            print("✗ git add falhou: " + (r.stderr or "").strip()[:300])
            return 1
    # `--somente-indice` serve ao laço de rebase: ali o commit já existe e o que falta é marcar os
    # caminhos como resolvidos, para `git rebase --continue` seguir.
    if "--somente-indice" in argv:
        print("houve=1")
        return 0
    if _git("diff", "--cached", "--quiet").returncode == 0:
        print(f"Sem alterações de `{elo}`.")
        print("houve=0")
        return 0
    mensagem = (argv[argv.index("--mensagem") + 1] if "--mensagem" in argv
                else f"{elo} automático")
    r = _git("commit", "-m", mensagem)
    if r.returncode != 0:
        print("✗ git commit falhou: " + (r.stderr or "").strip()[:300])
        return 1
    print("houve=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
