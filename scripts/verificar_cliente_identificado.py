#!/usr/bin/env python3
"""
verificar_cliente_identificado.py — um cliente só, e nunca disfarçado · §228
============================================================================
POR QUE ESTE PORTÃO EXISTE. Uma auditoria de 26/09/2026 contou **vinte e uma strings de
User-Agent diferentes** no repositório, uma por arquivo, e encontrou **seis começando com o
token de navegador** — duas delas o agente completo de um Chrome no Windows. Dois defeitos
distintos, no mesmo lugar:

1. **Cópia que envelhece.** É o §213 e o §222 outra vez: mudar o endereço de contato no `UA`
   canônico de `coletores_base` não mudava nada nos outros vinte arquivos. Pior, a política de
   robots (§185) avalia `can_fetch` contra `UA` e grava o cliente no rastro de
   `data/robots_registro.json` — módulo que enviava outra string era medido contra a regra de
   um agente e registrado como outro.

2. **Disfarce.** O `CLAUDE.md` diz, sem exceção: *nunca disfarçar o cliente*. Trazer o nome do
   projeto entre parênteses não desfaz o disfarce, e a razão pela qual alguém escreve o token de
   navegador é exatamente passar por filtro que recusa robô — o que é contornar recusa. Um dos
   casos vinha com a justificativa escrita na própria docstring ("robô educado" para portais que
   recusam robô); outro pedia cada alvo duas vezes, uma com cada identidade, "para separar
   bloqueio por IP de bloqueio por agente". A intenção de diagnóstico é boa, o meio não é — e a
   resposta não mudaria conduta nenhuma: diante de bloqueio por agente o projeto respeita e
   declara a lacuna, igual ao bloqueio por IP.

O QUE ELE CONFERE
  a) nenhum valor de `User-Agent` é string literal fora de `coletores_base.py` — tem de vir de
     `UA` ou de `ua_de(proposito)`;
  b) nenhuma string do código (docstring e comentário à parte, que podem contar a história)
     traz token de navegador;
  c) o `UA` canônico começa com o nome do projeto;
  c-bis) §235: `ua_de(proposito)` gera cabeçalho ASCII para CADA propósito literal do
     repositório. Cabeçalho HTTP é ASCII (RFC 7230 §3.2.4), e quando o §228 unificou o
     cliente dezoito chamadas passaram a mandar propósito acentuado: `defesacivil.es.gov.br`
     respondeu HTTP 400 ao pedido com acento e 200 com o PDF ao mesmo pedido sem ele. A trava
     protege a transliteração dentro de `ua_de` — tirá-la reprova o portão nas dezoito;
  d) todo módulo que faz pedido de rede cru identifica o cliente.

A leitura é por AST, e não por `grep`, justamente para que docstring e comentário possam
explicar o defeito sem reprovar o portão.
"""
import ast
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from coletores_base import UA, ua_de  # noqa: E402

ESTE = pathlib.Path(__file__).name
BASE = "coletores_base.py"
# Montado por pedaços de propósito: o portão não pode reprovar a si mesmo por citar o token.
TOKEN_NAVEGADOR = "Mozi" + "lla/"
# Chamada de rede crua, sem passar pelo `buscar` do projeto.
CRUAS = ("urlopen", "build_opener")


def _nome(no) -> str:
    """'coletores_base.ua_de' para um Attribute/Name, ou ''."""
    if isinstance(no, ast.Attribute):
        return f"{_nome(no.value)}.{no.attr}".lstrip(".")
    return no.id if isinstance(no, ast.Name) else ""


def arquivos():
    for p in sorted(list(RAIZ.glob("*.py")) + list(RAIZ.glob("scripts/*.py"))):
        if p.name == ESTE:
            continue
        yield p


def docstrings(arvore) -> set:
    """Ids dos nós Constant que são docstring — podem citar o defeito sem serem o defeito."""
    ids = set()
    for no in ast.walk(arvore):
        if isinstance(no, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            corpo = getattr(no, "body", None) or []
            if corpo and isinstance(corpo[0], ast.Expr) and isinstance(corpo[0].value, ast.Constant) \
                    and isinstance(corpo[0].value.value, str):
                ids.add(id(corpo[0].value))
    return ids


def conferir(p: pathlib.Path) -> list:
    falhas = []
    try:
        arvore = ast.parse(p.read_text(encoding="utf-8"))
    except SyntaxError as e:
        return [f"{p.name}: não compila ({e})"]
    docs = docstrings(arvore)
    rel = p.relative_to(RAIZ).as_posix()

    # (a) valor de User-Agent nunca é literal fora do coletores_base
    for no in ast.walk(arvore):
        if not isinstance(no, ast.Dict):
            continue
        for chave, valor in zip(no.keys, no.values):
            if not (isinstance(chave, ast.Constant) and chave.value == "User-Agent"):
                continue
            if isinstance(valor, ast.Constant) and p.name != BASE:
                falhas.append(f"{rel}:{no.lineno} User-Agent literal — use UA ou "
                              f'ua_de("propósito"): {str(valor.value)[:50]!r}')
    # também a forma addheaders = [("User-Agent", "...")]
    for no in ast.walk(arvore):
        if isinstance(no, ast.Tuple) and len(no.elts) == 2 and p.name != BASE:
            a, b = no.elts
            if isinstance(a, ast.Constant) and a.value == "User-Agent" and isinstance(b, ast.Constant):
                falhas.append(f"{rel}:{no.lineno} User-Agent literal em addheaders — "
                              f'use UA ou ua_de("propósito")')

    # (b) nenhum token de navegador em string de código
    for no in ast.walk(arvore):
        if isinstance(no, ast.Constant) and isinstance(no.value, str) and id(no) not in docs:
            if TOKEN_NAVEGADOR in no.value:
                falhas.append(f"{rel}:{no.lineno} string de código com token de navegador — "
                              "nunca disfarçar o cliente (CLAUDE.md)")

    # (c-bis) §235: o cliente montado para cada propósito tem de caber num CABEÇALHO HTTP, e
    #     cabeçalho é ASCII (RFC 7230 §3.2.4). Quando o §228 unificou o cliente, dezoito chamadas
    #     passaram a mandar propósito acentuado e o cabeçalho ficou inválido — medido no mesmo dia:
    #     `defesacivil.es.gov.br` respondeu **HTTP 400 em 0,4 s** ao pedido com acento e **200 com
    #     o PDF** ao mesmo pedido sem ele. O portão confere o resultado de `ua_de` para CADA
    #     propósito literal do repositório, e não a função isolada: era a combinação que quebrava.
    for no in ast.walk(arvore):
        if not (isinstance(no, ast.Call) and _nome(no.func).split(".")[-1] == "ua_de" and no.args):
            continue
        a0 = no.args[0]
        if not (isinstance(a0, ast.Constant) and isinstance(a0.value, str)):
            continue
        if not ua_de(a0.value).isascii():
            falhas.append(f"{rel}:{no.lineno} ua_de({a0.value!r}) gera cabeçalho não-ASCII — "
                          "cabeçalho HTTP é ASCII (RFC 7230); veja §235")

    # (d) pedido cru de rede sem cliente identificado. Duas formas: `urllib` e `requests` —
    #     a segunda entrou em 26/09/2026 porque era justamente por ela que a chave do Portal da
    #     Transparência viajava sem cliente ao lado, um pedido autenticado de agente anônimo.
    tem_cru = any(isinstance(no, ast.Name) and no.id in CRUAS for no in ast.walk(arvore)) or \
        any(isinstance(no, ast.Attribute) and no.attr in CRUAS for no in ast.walk(arvore)) or \
        any(isinstance(no, ast.Attribute) and isinstance(no.value, ast.Name)
            and no.value.id == "requests" and no.attr in ("get", "post", "head", "put", "request")
            for no in ast.walk(arvore))
    if tem_cru and p.name != BASE:
        fonte = p.read_text(encoding="utf-8")
        if "User-Agent" not in fonte and "addheaders" not in fonte and "from coletores_base import" not in fonte:
            falhas.append(f"{rel} faz pedido de rede cru sem identificar o cliente — "
                          "a política de robots (§185) depende do cliente enviado")
    return falhas


def main() -> int:
    if not UA.startswith("MonitorElNino"):
        print(f"✗ CLIENTE IDENTIFICADO: o UA canônico não começa com o nome do projeto: {UA[:60]!r}")
        return 1
    if TOKEN_NAVEGADOR in UA:
        print("✗ CLIENTE IDENTIFICADO: o UA canônico traz token de navegador")
        return 1
    falhas = []
    n = 0
    for p in arquivos():
        n += 1
        falhas += conferir(p)
    if falhas:
        print(f"✗ CLIENTE IDENTIFICADO: {len(falhas)} problema(s) em {n} arquivo(s):")
        for f in falhas:
            print(f"    {f}")
        print("\n  Conserto: `from coletores_base import ua_de` e "
              '`headers={"User-Agent": ua_de("o que esta rotina faz")}`.')
        return 1
    print(f"✓ CLIENTE IDENTIFICADO OK — {n} arquivo(s), um cliente só, nenhum disfarce. UA: {UA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
