#!/usr/bin/env python3
"""
scripts/verificar_idempotencia_dos_derivados.py — gerador que não se repete não entra
======================================================================================
Item 3 do `HANDOVER_publicacao_definitiva_e_rodadas_agora_06-10-2026.md`.

A CLASSE DE DEFEITO
--------------------
Entre 03 e 06/10/2026, `Publicar dados` falhou **33 vezes**, e **29** delas foram
`verificar_derivados.sh` dizendo "havia derivado obsoleto". A causa individual era o `CODEMAP.md`
carimbando pelo relógio, e ela foi corrigida (#567) — mas a CLASSE continua aberta: **qualquer**
gerador não idempotente volta a travar a publicação, e trava do mesmo jeito, sem dizer qual é.

O lugar de pegar isso é o PR, onde o gerador muda. No publicador, regenerar é a função — "havia
derivado obsoleto" não pode barrar a publicação de dado.

O QUE ELE FAZ
--------------
Regenera a cadeia canônica **duas vezes** e compara. Diferença entre a primeira e a segunda
passagem é não determinismo: o gerador depende de algo que muda sozinho — relógio, ordem de
dicionário, caminho absoluto, semente aleatória. Reprova com o arquivo e a primeira linha que
diverge.

Primeira passagem contra o git é outra pergunta (é o portão 12) e não se mistura com esta: aqui não
importa se o derivado estava em dia, importa se o gerador dá sempre o mesmo resultado.

USO
  python3 scripts/verificar_idempotencia_dos_derivados.py --autoteste
  python3 scripts/verificar_idempotencia_dos_derivados.py
"""
import pathlib
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
CADEIA = RAIZ / "scripts" / "verificar_derivados.sh"


def primeira_divergencia(antes: str, depois: str) -> str:
    """A primeira linha em que os dois textos diferem, descrita. Função pura."""
    a = str(antes or "").splitlines()
    b = str(depois or "").splitlines()
    for n, (x, y) in enumerate(zip(a, b), start=1):
        if x != y:
            return f"linha {n}: {x.strip()[:70]!r} → {y.strip()[:70]!r}"
    if len(a) != len(b):
        return f"tamanho: {len(a)} linha(s) → {len(b)} linha(s)"
    return ""


def nao_idempotentes(antes: dict, depois: dict) -> list:
    """Os arquivos que mudaram entre as duas regenerações. Função pura.

    `antes` e `depois` são {caminho: conteúdo}. Arquivo que só existe num dos lados também conta:
    gerador que cria arquivo numa passagem e não na outra é tão não determinístico quanto o que
    muda o conteúdo.
    """
    fora = []
    for caminho in sorted(set(antes or {}) | set(depois or {})):
        a, b = (antes or {}).get(caminho), (depois or {}).get(caminho)
        if a == b:
            continue
        if a is None:
            fora.append(f"{caminho}: só existe depois da segunda regeneração")
        elif b is None:
            fora.append(f"{caminho}: sumiu na segunda regeneração")
        else:
            fora.append(f"{caminho}: {primeira_divergencia(a, b)}")
    return fora


def _git(*args):
    return subprocess.run(["git", *args], cwd=str(RAIZ), capture_output=True, text=True,
                          timeout=300)


def _ler_arvore() -> dict:
    """{caminho: conteúdo} dos arquivos que a cadeia mexeu. Lê disco; não escreve."""
    mudados = [l[3:] for l in (_git("status", "--porcelain").stdout or "").splitlines()
               if len(l) > 3]
    fora = {}
    for rel in mudados:
        arq = RAIZ / rel.strip()
        if not arq.exists() or arq.is_dir():
            continue
        try:
            fora[rel.strip()] = arq.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
    return fora


def _autoteste() -> int:
    falhas, contados = [], []

    def ok(nome, cond):
        contados.append(nome)
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    ok("conteúdo igual não acusa nada", nao_idempotentes({"a": "x"}, {"a": "x"}) == [])
    ok("conteúdo diferente acusa", nao_idempotentes({"a": "x"}, {"a": "y"}) != [])
    ok("a mensagem traz os dois lados",
       "'x' → 'y'" in nao_idempotentes({"a": "x"}, {"a": "y"})[0])
    ok("arquivo que aparece depois acusa",
       "só existe depois" in nao_idempotentes({}, {"a": "x"})[0])
    ok("arquivo que some acusa", "sumiu" in nao_idempotentes({"a": "x"}, {})[0])
    ok("árvores vazias não acusam", nao_idempotentes({}, {}) == [])

    # O caso real: o CODEMAP mudando a linha do carimbo entre duas passagens.
    a = "titulo\nAtualizado em 05/10/2026.\nresto\n"
    b = "titulo\nAtualizado em 06/10/2026.\nresto\n"
    ok("o defeito do CODEMAP seria pego", nao_idempotentes({"CODEMAP.md": a},
                                                           {"CODEMAP.md": b}) != [])
    ok("a divergência é apontada na linha certa",
       "linha 2" in primeira_divergencia(a, b))
    ok("textos iguais não têm divergência", primeira_divergencia("x\ny", "x\ny") == "")
    ok("tamanho diferente é divergência", "tamanho" in primeira_divergencia("x", "x\ny"))

    import dis
    nomes = set()
    for nome_obj, obj in list(globals().items()):
        if nome_obj in ("_autoteste", "main", "_git", "_ler_arvore"):
            continue
        if getattr(obj, "__module__", None) not in (__name__, None):
            continue
        codigo = getattr(obj, "__code__", None)
        if codigo is not None:
            nomes |= {i.argval for i in dis.get_instructions(codigo) if isinstance(i.argval, str)}
    ok("trava estrutural: as funções puras não leem disco nem chamam git",
       not ({"read_text", "write_text", "subprocess"} & nomes))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else f"✓ AUTOTESTE OK — {len(contados)} casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def main(argv: list) -> int:
    if "--autoteste" in argv:
        return _autoteste()
    if not CADEIA.exists():
        print(f"✗ {CADEIA.relative_to(RAIZ)} não existe")
        return 1

    def regenerar():
        return subprocess.run(["bash", str(CADEIA), "--regenerar-para-commit"],
                              cwd=str(RAIZ), capture_output=True, text=True, timeout=1800)

    r1 = regenerar()
    if r1.returncode != 0:
        print("✗ IDEMPOTÊNCIA: a primeira regeneração FALHOU:")
        print((r1.stderr or r1.stdout or "").strip()[-600:])
        return 1
    antes = _ler_arvore()

    r2 = regenerar()
    if r2.returncode != 0:
        print("✗ IDEMPOTÊNCIA: a segunda regeneração FALHOU:")
        print((r2.stderr or r2.stdout or "").strip()[-600:])
        return 1
    depois = _ler_arvore()

    fora = nao_idempotentes(antes, depois)
    if fora:
        print(f"✗ IDEMPOTÊNCIA: {len(fora)} derivado(s) mudam entre duas regenerações:")
        for x in fora[:15]:
            print("   - " + x)
        print("   Gerador não determinístico trava a publicação sem dizer qual é: entre 03 e "
              "06/10/2026 foram 29 publicações perdidas assim. Fixe o que varia (relógio, ordem, "
              "caminho absoluto, semente) pelo dado, não pela parede.")
        return 1
    print(f"✓ IDEMPOTÊNCIA OK — a cadeia canônica regenera igual duas vezes "
          f"({len(antes)} arquivo(s) conferido(s)).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
