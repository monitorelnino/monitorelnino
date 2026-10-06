#!/usr/bin/env python3
"""
scripts/aplicar_delta_do_elo.py — o meu delta sobre o ramo mais novo, sem fusão de três vias
==============================================================================================
Causa C do `HANDOVER_noite_confiavel_parte3_causas_confirmadas_06-10-2026.md`.

O QUE O DESENHO ANTIGO FAZIA
-----------------------------
O laço de cinco tentativas fazia `git rebase FETCH_HEAD` sobre um commit que **já continha a união
da tentativa anterior**, e chamava o resolvedor de novo. O conteúdo acumulava a cada volta:
`data/pistas_imprensa.json` foi de 28 MB para 104,79 MB e 187,53 MB **num único run**, passou do
limite de 100 MB do GitHub e o push ficou impossível. Cada tentativa de salvar o trabalho o
destruía um pouco mais.

O DESENHO NOVO, EM UMA FRASE
-----------------------------
**Guarda-se o que este elo produziu; a cada tentativa, parte-se do ramo mais novo e reaplica-se só
isso.** Nenhuma fusão de três vias em arquivo compartilhado, nunca.

    1. antes do commit, as saídas do elo vão para fora do repositório (`--guardar`);
    2. a cada tentativa: `fetch` do ramo → `reset --hard` nele → `--reaplicar` → commit → push.

Reaplicar é, para cada arquivo de que o elo é o único escritor, **a cópia**: ele é o dono, e o que
ele tem é a verdade. Para a FILA, é `pistas.sincronizar`, que é a porta: pista nova entra, pista
repetida mescla campos, nada duplica. Para o resto, o arquivo não é reaplicado e fica dito.

Por que isso não perde o trabalho do outro elo: partindo do ramo mais novo, o que o outro gravou já
está lá. O elo acrescenta o dele por cima, sem tocar no que não é dele — que é a regra de
`config/escritores.json` aplicada no momento em que ela mais importa.

USO
  python3 scripts/aplicar_delta_do_elo.py --autoteste
  python3 scripts/aplicar_delta_do_elo.py <elo> --guardar   # antes do commit
  python3 scripts/aplicar_delta_do_elo.py <elo> --reaplicar # depois do reset --hard
"""
import json
import pathlib
import shutil
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
GUARDADO = pathlib.Path("/tmp/delta_do_elo")
CONFIG = RAIZ / "config" / "escritores.json"


def filas_de_pista(caminhos: list) -> tuple:
    """(filas, demais). Função pura. Fila é o que a porta governa, e ela tem política própria."""
    filas = [c for c in caminhos or [] if c.startswith("data/pistas_") and c.endswith(".json")]
    return filas, [c for c in caminhos or [] if c not in set(filas)]


def meus_arquivos(mudados: list, elo: str, tabela: dict) -> list:
    """Os caminhos deste elo, pela declaração. Função pura.

    Reaproveita a mesma leitura do ajudante de commit — a lista de quem pode escrever o quê tem um
    dono só, e duas leituras dela discordariam na primeira mudança.
    """
    sys.path.insert(0, str(RAIZ / "scripts"))
    from commit_do_elo import pode_comitar
    return sorted(c for c in set(mudados or []) if pode_comitar(c, elo, tabela))


def _git(*args, **kw):
    return subprocess.run(["git", *args], cwd=str(RAIZ), capture_output=True, text=True, **kw)


def _tabela() -> dict:
    sys.path.insert(0, str(RAIZ / "scripts"))
    from commit_do_elo import regras
    return regras(json.loads(CONFIG.read_text(encoding="utf-8")))


def _mudados() -> list:
    sys.path.insert(0, str(RAIZ / "scripts"))
    from commit_do_elo import mudados_na_arvore
    return mudados_na_arvore()


def _guardar(elo: str) -> int:
    """Copia as saídas deste elo para fora do repositório."""
    alvos = meus_arquivos(_mudados(), elo, _tabela())
    if GUARDADO.exists():
        shutil.rmtree(GUARDADO, ignore_errors=True)
    GUARDADO.mkdir(parents=True, exist_ok=True)
    for rel in alvos:
        origem = RAIZ / rel
        if not origem.exists():
            continue
        destino = GUARDADO / rel
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origem, destino)
    (GUARDADO / "_lista.json").write_text(json.dumps(alvos, ensure_ascii=False, indent=1) + "\n",
                                          encoding="utf-8", newline="\n")
    print(f"· guardado fora do repositorio: {len(alvos)} caminho(s) de `{elo}`")
    return 0


def _reaplicar(elo: str) -> int:
    """Devolve as saídas guardadas à árvore, que acaba de ser resetada no ramo mais novo."""
    lista = GUARDADO / "_lista.json"
    if not lista.exists():
        print("· nada guardado para reaplicar")
        return 0
    alvos = json.loads(lista.read_text(encoding="utf-8"))
    filas, demais = filas_de_pista(alvos)

    for rel in demais:
        origem = GUARDADO / rel
        if not origem.exists():
            continue
        destino = RAIZ / rel
        destino.parent.mkdir(parents=True, exist_ok=True)
        # CÓPIA, não fusão: este elo é o único escritor declarado deste caminho, e o que ele tem é
        # a verdade dele. O que os outros gravaram já veio no `reset --hard` do ramo.
        shutil.copy2(origem, destino)

    if filas:
        sys.path.insert(0, str(RAIZ / "scripts"))
        from pistas import sincronizar
        for rel in filas:
            origem = GUARDADO / rel
            if not origem.exists():
                continue
            doc = json.loads(origem.read_text(encoding="utf-8"))
            nome = pathlib.Path(rel).stem
            try:
                r = sincronizar(nome, doc, origem=f"reaplicacao de {elo}")
                print(f"  · {rel}: {r if not isinstance(r, dict) else r.get('resumo', 'sincronizada')}")
            except Exception as erro:
                print(f"  ⚠ {rel}: a porta recusou a sincronizacao ({str(erro)[:90]})")

    print(f"· reaplicado: {len(demais)} arquivo(s) por copia, {len(filas)} fila(s) pela porta")
    return 0


def _autoteste() -> int:
    falhas, contados = [], []

    def ok(nome, cond):
        contados.append(nome)
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    filas, demais = filas_de_pista(
        ["data/pistas_imprensa.json", "data/focos_pontos.json", "data/pistas_doe.json",
         "data/pistas_revisao.json"])
    ok("as filas de pista são separadas", "data/pistas_imprensa.json" in filas)
    ok("arquivo comum não vira fila", "data/focos_pontos.json" in demais)
    ok("duas filas entram as duas", len(filas) == 3)
    ok("nada se perde da conta", len(filas) + len(demais) == 4)
    ok("lista vazia devolve dois vazios", filas_de_pista([]) == ([], []))

    T = {"data/focos_pontos.json": "sinais", "data/pistas_imprensa.json": "qualquer_elo",
         "docs/MANIFEST_SHA256.txt": "publicar"}
    meus = meus_arquivos(
        ["data/focos_pontos.json", "docs/MANIFEST_SHA256.txt", "data/pistas_imprensa.json",
         "data/nao_declarado.json"], "sinais", T)
    ok("o arquivo do elo entra", "data/focos_pontos.json" in meus)
    ok("a fila com resolução declarada entra", "data/pistas_imprensa.json" in meus)
    ok("o arquivo de outro elo NÃO entra", "docs/MANIFEST_SHA256.txt" not in meus)
    ok("o não declarado NÃO entra", "data/nao_declarado.json" not in meus)
    ok("árvore limpa não dá nada", meus_arquivos([], "sinais", T) == [])

    import dis
    nomes = set()
    for nome_obj, obj in list(globals().items()):
        if nome_obj in ("_autoteste", "main", "_git", "_guardar", "_reaplicar", "_tabela",
                        "_mudados", "meus_arquivos"):
            continue
        if getattr(obj, "__module__", None) not in (__name__, None):
            continue
        codigo = getattr(obj, "__code__", None)
        if codigo is not None:
            nomes |= {i.argval for i in dis.get_instructions(codigo) if isinstance(i.argval, str)}
    ok("trava estrutural: a função pura não copia, não escreve e não chama git",
       not ({"copy2", "write_text", "subprocess", "rmtree"} & nomes))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else f"✓ AUTOTESTE OK — {len(contados)} casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def main(argv: list) -> int:
    if "--autoteste" in argv:
        return _autoteste()
    sem_bandeira = [a for a in argv if not a.startswith("--")]
    if not sem_bandeira:
        print("uso: python3 scripts/aplicar_delta_do_elo.py <elo> --guardar|--reaplicar")
        return 2
    elo = sem_bandeira[0]
    if "--guardar" in argv:
        return _guardar(elo)
    if "--reaplicar" in argv:
        return _reaplicar(elo)
    print("uso: python3 scripts/aplicar_delta_do_elo.py <elo> --guardar|--reaplicar")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
