#!/usr/bin/env python3
"""
scripts/verificar_escrita_portavel.py — portão da escrita portável (§178, 23/09/2026)
======================================================================================
Fecha a série aberta no §163. No Windows, `open(..., "w")` e `Path.write_text(...)` sem
`newline="\n"` traduzem cada `\n` para `\r\n`: o arquivo sai em CRLF, o hash deixa de bater com o
selado em `docs/MANIFEST_SHA256.txt` e o derivado regenerado fora do runner não é o mesmo arquivo.
O mesmo vale para `csv.writer` sem `lineterminator`, que escreve `\r\n` por padrão em qualquer
sistema. O defeito é invisível no runner (Linux) — só aparece quando alguém roda o pipeline em
outra máquina, que é exatamente quando se precisa reproduzir o que o robô publicou.

Não é regra de estilo: é a condição para o repositório ser auditável fora da Action.

O portão lê o código com `ast` (e não por expressão regular sobre a linha, que confunde comentário
e docstring com código). Exceção justificada se declara na própria linha:

    open(tmp, "w")  # escrita-nao-portavel-ok: arquivo temporário fora do repositório

Uso:  python3 scripts/verificar_escrita_portavel.py
      python3 scripts/verificar_escrita_portavel.py --autoteste
"""
import ast
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MARCA_EXCECAO = "escrita-nao-portavel-ok:"
MODOS_TEXTO = ("w", "a", "x")


def _modo_de(no: ast.Call):
    """Modo literal de uma chamada a open(), por posição ou por palavra-chave; None se não é literal."""
    if len(no.args) >= 2 and isinstance(no.args[1], ast.Constant) and isinstance(no.args[1].value, str):
        return no.args[1].value
    for k in no.keywords:
        if k.arg == "mode" and isinstance(k.value, ast.Constant) and isinstance(k.value.value, str):
            return k.value.value
    return None


def problemas_do_fonte(src: str, nome: str = "<fonte>") -> list:
    """Lista de problemas de escrita não portável num código-fonte. Função pura, sem disco."""
    try:
        arvore = ast.parse(src)
    except SyntaxError as e:
        return [f"{nome}:{e.lineno}: não compila ({e.msg})"]
    linhas = src.split("\n")
    problemas = []

    def dispensado(no) -> bool:
        return MARCA_EXCECAO in linhas[no.lineno - 1]

    for no in ast.walk(arvore):
        if not isinstance(no, ast.Call):
            continue
        tem = {k.arg for k in no.keywords}
        if isinstance(no.func, ast.Name) and no.func.id == "open":
            modo = _modo_de(no)
            if modo and "b" not in modo and any(m in modo for m in MODOS_TEXTO) and "newline" not in tem:
                if not dispensado(no):
                    problemas.append(f'{nome}:{no.lineno}: open(..., "{modo}") sem newline="\\n" — no Windows sai em CRLF')
        elif isinstance(no.func, ast.Attribute):
            if no.func.attr == "write_text" and "newline" not in tem and not dispensado(no):
                problemas.append(f'{nome}:{no.lineno}: write_text(...) sem newline="\\n" — no Windows sai em CRLF')
            elif no.func.attr in ("writer", "DictWriter") and "lineterminator" not in tem and not dispensado(no):
                # csv.writer escreve \r\n por padrão em TODO sistema, não só no Windows
                problemas.append(f"{nome}:{no.lineno}: csv.{no.func.attr}(...) sem lineterminator — o padrão do módulo é CRLF")
    return problemas


def autoteste() -> int:
    """Testes negativos permanentes: cada forma do defeito reprova, e cada forma correta passa."""
    casos = [
        ('open(p, "w")', 1),
        ('open(p, "w", encoding="utf-8")', 1),
        ('open(p, "a")', 1),
        ('open(p, mode="w")', 1),
        ('open(p, "w", newline="\\n")', 0),
        ('open(p, "wb")', 0),                      # binário não traduz nada
        ('open(p, "rb")', 0),
        ('open(p)', 0),                            # leitura
        ('P.write_text(t, encoding="utf-8")', 1),
        ('P.write_text(t, encoding="utf-8", newline="\\n")', 0),
        ('P.write_bytes(b)', 0),
        ('csv.writer(buf)', 1),
        ('csv.DictWriter(buf, fieldnames=c)', 1),
        ('csv.writer(buf, lineterminator="\\n")', 0),
        ('open(p, "w")  # escrita-nao-portavel-ok: temporário fora do repositório', 0),
        ('"""docstring que fala de open(p, \\"w\\") sem escrever nada"""', 0),
        ('# open(p, "w") comentado', 0),
    ]
    falhas = []
    for src, esperado in casos:
        n = len(problemas_do_fonte(src, "teste"))
        if n != esperado:
            falhas.append(f"{src!r} devolveu {n} problema(s); esperado {esperado}")
    if falhas:
        print("✗ AUTOTESTE (escrita portável):"); [print("   ", f) for f in falhas]; return 1
    print(f"✓ AUTOTESTE OK — {len(casos)} casos: modo texto, binário, leitura, write_text, csv e exceção declarada.")
    return 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    if autoteste() != 0:
        return 1
    problemas = []
    arquivos = 0
    for p in sorted(RAIZ.rglob("*.py")):
        if "__pycache__" in p.parts:
            continue
        arquivos += 1
        problemas += problemas_do_fonte(p.read_text(encoding="utf-8"), p.relative_to(RAIZ).as_posix())
    if problemas:
        print(f"✗ ESCRITA PORTÁVEL: {len(problemas)} sítio(s) de escrita que corrompem o arquivo fora do runner:")
        for x in problemas[:20]:
            print("   ", x)
        if len(problemas) > 20:
            print(f"    … e mais {len(problemas) - 20}")
        print(f'    Conserto: acrescentar newline="\\n" (ou lineterminator="\\n" no csv). Exceção justificada '
              f'declara "# {MARCA_EXCECAO} <motivo>" na própria linha.')
        return 1
    print(f"✓ ESCRITA PORTÁVEL OK — {arquivos} arquivo(s) Python, nenhuma escrita em modo texto sem newline fixado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
