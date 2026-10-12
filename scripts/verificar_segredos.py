#!/usr/bin/env python3
"""Nenhuma credencial nem CPF entra no repositório pelo diff do PR (A7-11 do relatório D).

POR QUE EXISTE
--------------
O repositório é público e o Netlify publica a raiz (`publish = "."`). Até 12/10/2026 nenhum portão
de PR procurava segredo fora de `evidencias/`: um token `ghp_…` colado num JSON de `data/` ou num
`.js` de página ia ao ar com todos os portões verdes (mutação registrada na auditoria de 08/10).

O QUE ELE COBRA
---------------
Nas LINHAS ACRESCENTADAS pelo PR (`git diff <contra>...HEAD`), fora de `evidencias/` (que tem
portão próprio, `verificar_evidencia_sem_segredo.py`):
  · em qualquer arquivo de texto: credencial com prefixo que a identifica sozinha (`AKIA…`,
    `ghp_…`/`gh[ousr]_…`, `AIza…`, `sk-…`, `xox[baprs]-…`) e chave privada PEM;
  · em conteúdo publicado (`data/`, `assets/`, `conteudo/`, `feeds/`, `*.html`): também a
    atribuição `api_key = …` e CPF no formato NNN.NNN.NNN-NN.
Os padrões são os de `coletores_base` (`PADROES_DE_SEGREDO`, `redigir_dados_pessoais`) — uma lista
só. Os arquivos que DEFINEM os padrões ficam fora (falariam deles mesmos).

Erro do `git diff` é vermelho, nunca "0 arquivos" verde (A7-20).

USO
  python3 scripts/verificar_segredos.py --contra origin/main
  python3 scripts/verificar_segredos.py --autoteste
"""
import pathlib
import re
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

PUBLICADO = re.compile(r"^(data/|assets/|conteudo/|feeds/)|\.html$")
DEFINEM_OS_PADROES = {"coletores_base.py", "scripts/verificar_segredos.py",
                      "scripts/auditoria_seguranca.py", "scripts/remediar_segredos_evidencias.py",
                      "scripts/verificar_evidencia_sem_segredo.py"}
RE_PEM = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
RE_CPF = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
# O nome do campo de `PADROES_DE_SEGREDO[0]`, aceitando também a aspa que fecha a chave em JSON
# (`"api_key": "…"`) — a regex da porta foi escrita para HTML e não a cobria.
nominal = re.compile(r"(?:api[_-]?key|apikey|access[_-]?token|client[_-]?secret|secret[_-]?key|"
                     r"authorization)[\"']?\s*[:=]\s*[\"']?[A-Za-z0-9_\-\.]{16,}", re.I)
BINARIOS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".zip", ".gz", ".woff", ".woff2",
            ".ttf", ".ico", ".xlsx", ".docx")


def linhas_acrescentadas(contra: str) -> dict:
    """{caminho: [linhas acrescentadas]} do diff. Levanta se o git falhar (A7-20). Só lê."""
    try:
        r = subprocess.run(["git", "diff", "-U0", "--no-color", "--diff-filter=AM",
                            f"{contra}...HEAD"], cwd=RAIZ, capture_output=True, text=True,
                           timeout=300, errors="replace")
    except (OSError, subprocess.SubprocessError) as e:
        raise RuntimeError(f"git diff não rodou: {type(e).__name__}: {e}") from e
    if r.returncode != 0:
        raise RuntimeError(f"git diff falhou ({r.returncode}): {(r.stderr or '').strip()[:200]}")
    return separar_diff(r.stdout)


def separar_diff(texto: str) -> dict:
    """Função pura: {caminho: [linhas com '+']} a partir de um diff unificado."""
    fora, atual = {}, None
    for linha in (texto or "").splitlines():
        if linha.startswith("+++ "):
            alvo = linha[4:].strip()
            atual = alvo[2:] if alvo.startswith("b/") else None
            if atual is not None:
                fora.setdefault(atual, [])
            continue
        if atual is not None and linha.startswith("+") and not linha.startswith("+++"):
            fora[atual].append(linha[1:])
    return fora


def problemas(acrescentadas: dict) -> list:
    """Uma linha por achado: caminho, tipo e trecho mascarado. Função pura."""
    from coletores_base import PADROES_DE_SEGREDO
    por_prefixo = PADROES_DE_SEGREDO[1][0]
    fora = []
    for caminho, linhas in sorted((acrescentadas or {}).items()):
        if caminho.startswith("evidencias/") or caminho in DEFINEM_OS_PADROES \
                or caminho.lower().endswith(BINARIOS):
            continue
        publicado = bool(PUBLICADO.search(caminho))
        for n, linha in enumerate(linhas, 1):
            achados = []
            if por_prefixo.search(linha):
                achados.append("credencial com prefixo")
            if RE_PEM.search(linha):
                achados.append("chave privada")
            if publicado and nominal.search(linha):
                achados.append("atribuição de chave")
            if publicado and RE_CPF.search(linha):
                achados.append("CPF")
            for a in achados:
                fora.append(f"{caminho} (+{n}ª linha acrescentada): {a}")
    return fora


def _autoteste() -> int:
    falhas, contados = [], []

    def ok(nome, cond):
        contados.append(nome)
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    diff = ("+++ b/data/meta.json\n+{\"t\": \"ghp_" + "a" * 36 + "\"}\n"
            "+++ b/assets/js/saude.js\n+const k = 'AKIA" + "B" * 16 + "';\n"
            "+++ b/data/x.json\n+\"cpf\": \"123.456.789-09\"\n"
            "+++ b/scripts/teste.py\n+cpf = '123.456.789-09'  # fixture de teste\n"
            "+++ b/conteudo/saude.json\n+\"api_key\": \"abcdefghijklmnop1234\"\n"
            "+++ b/evidencias/x.html\n+ghp_" + "c" * 36 + "\n"
            "+++ b/scripts/chave.py\n+-----BEGIN RSA PRIVATE KEY-----\n")
    p = problemas(separar_diff(diff))
    ok("token do GitHub em data/ é achado", any("data/meta.json" in x for x in p))
    ok("chave AWS em .js de página é achada", any("saude.js" in x for x in p))
    ok("CPF em data/ é achado", any("data/x.json" in x and "CPF" in x for x in p))
    ok("CPF em fixture de código não é achado", not any("scripts/teste.py" in x for x in p))
    ok("atribuição de chave em conteúdo publicado é achada", any("conteudo/saude.json" in x for x in p))
    ok("evidencias/ fica com o portão próprio", not any(x.startswith("evidencias/") for x in p))
    ok("chave privada em qualquer arquivo é achada", any("scripts/chave.py" in x for x in p))
    ok("diff sem segredo não acusa", problemas(separar_diff("+++ b/data/a.json\n+{\"x\": 1}\n")) == [])
    try:
        linhas_acrescentadas("ref-que-nao-existe-a7-11")
        ok("erro do git diff levanta, não vira verde (A7-20)", False)
    except RuntimeError:
        ok("erro do git diff levanta, não vira verde (A7-20)", True)
    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else f"✓ AUTOTESTE OK — {len(contados)} casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def main() -> int:
    argv = sys.argv[1:]
    if "--autoteste" in argv:
        return _autoteste()
    contra = argv[argv.index("--contra") + 1] if "--contra" in argv else "origin/main"
    acrescentadas = linhas_acrescentadas(contra)
    achados = problemas(acrescentadas)
    if achados:
        print(f"✗ SEGREDOS: {len(achados)} achado(s) nas linhas acrescentadas contra {contra}:")
        for a in achados[:40]:
            print("   - " + a)
        print("   Repositório público, publicado pela raiz: credencial e CPF não entram. Redija na "
              "porta (`coletores_base.redigir_segredos`/`redigir_dados_pessoais`) e reenvie.")
        return 1
    print(f"✓ SEGREDOS OK — {len(acrescentadas)} arquivo(s) do diff contra {contra}, nenhuma "
          f"credencial nem CPF nas linhas acrescentadas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
