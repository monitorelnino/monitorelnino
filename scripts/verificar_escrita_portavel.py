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

    # 05/10/2026 — os casos do caractere de controle. O primeiro é o defeito real: um backspace
    # (0x08) onde devia estar a borda de palavra da expressão regular.
    BACKSPACE = chr(8)
    controle = [
        (f'    r"|{BACKSPACE}SES[-/]?[A-Z]{{2}}{BACKSPACE}"', 1),
        ('    r"|\\bSES[-/]?[A-Z]{2}\\b"', 0),
        (f'if (/{BACKSPACE}199{BACKSPACE}|40199/.test(x))', 1),
        (f'linha um\nlinha {chr(1)}dois\nlinha tres', 1),
        # Tabulação vertical e avanço de página na MESMA linha: uma acusação, e ela aparece —
        # `splitlines()` as trataria como fim de linha e não acharia nada.
        (f'{chr(11)}{chr(12)}', 1),
        (f'linha um{chr(11)}ainda a um', 1),
        ("tabulação\tnão é controle proibido", 0),
        ("quebra\nde\nlinha\nnão é", 0),
        ("retorno\r\nde carro é assunto do newline, não daqui", 0),
        ("", 0),
    ]
    for src, esperado in controle:
        n = len(caracteres_de_controle(src, "teste"))
        if n != esperado:
            falhas.append(f"controle: {src!r} devolveu {n}; esperado {esperado}")
    if caracteres_de_controle(chr(8), "assets/vendor/x.js"):
        falhas.append("controle: assets/vendor/ devia ficar fora da varredura")

    if falhas:
        print("✗ AUTOTESTE (escrita portável):"); [print("   ", f) for f in falhas]; return 1
    print(f"✓ AUTOTESTE OK — {len(casos) + len(controle) + 1} casos: modo texto, binário, "
          f"leitura, write_text, csv, exceção declarada e caractere de controle no fonte.")
    return 0


def caracteres_de_controle(texto: str, nome: str = "<fonte>") -> list:
    """Bytes de controle no meio do fonte. Função pura.

    05/10/2026 — A MESMA FAMÍLIA DE DEFEITO, pela terceira vez na mesma semana. Escrever arquivo
    por heredoc do shell (`python3 - <<'PY'`) e deixar um `\\b` ou um `\\n` chegar ao shell faz o
    shell gravar o CARACTERE DE CONTROLE, não a sequência de escape. O resultado é um fonte que
    parece certo quando se lê — `[^>]*\\bid=` — e que na verdade traz um backspace (`0x08`) ali.

    Já custou três vezes: um `printf '%s\\n'` que virou quebra de linha real dentro do YAML e
    rejeitou o workflow; um `json.dumps(...) + "\\n"` que virou literal de string sem fechamento; e
    um `\\b` de expressão regular que virou backspace e fez o padrão nunca casar — este último o
    mais perigoso, porque não dá erro de sintaxe: o programa roda e silenciosamente não acha nada.

    É a mesma lição deste portão, por outro caminho: **os bytes em disco não são o que se lê.** O
    que o portão de newline faz pelo fim de linha, esta função faz pelo resto.

    Tabulação (`0x09`), nova linha (`0x0a`) e retorno (`0x0d`) ficam fora: são brancos legítimos,
    e o fim de linha é assunto do resto do portão.
    """
    # Tabulação, nova linha e retorno são brancos legítimos; o fim de linha é assunto do resto
    # deste portão. Biblioteca de terceiro minificada (`assets/vendor/`) fica fora: o `jspdf`
    # carrega um `0x01` dentro de uma literal, é assim que o autor o publicou, e reescrever
    # dependência de terceiro por causa disso seria pior que o defeito.
    LEGITIMOS = (0x09, 0x0a, 0x0d)
    if "assets/vendor/" in (nome or ""):
        return []
    # Varre o texto caractere a caractere, contando a linha só no `\n`. NÃO usa `splitlines()`:
    # em Python ele trata `\x0b` (tabulação vertical) e `\x0c` (avanço de página) como FIM DE LINHA
    # e os engole, de modo que justamente dois dos caracteres que este portão procura ficariam
    # invisíveis para ele. Portão cego no que procura é o defeito que ele existe para pegar.
    fora = []
    linha, acusada = 1, 0
    for c in (texto or ""):
        if c == "\n":
            linha += 1
            continue
        if ord(c) < 0x20 and ord(c) not in LEGITIMOS and acusada != linha:
            acusada = linha
            fora.append(f"{nome}:{linha}: caractere de controle {hex(ord(c))} no fonte — "
                        f"escape do shell que virou byte; reescreva a linha com Edit/Write")
    return fora


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
        fonte = p.read_text(encoding="utf-8")
        rel = p.relative_to(RAIZ).as_posix()
        problemas += problemas_do_fonte(fonte, rel)
        problemas += caracteres_de_controle(fonte, rel)

    # 05/10/2026: a varredura de caractere de controle NÃO para no Python. Dos quatro casos achados
    # em 05/10, dois estavam em portão escrito em JavaScript — `verificar_imprensa_do_dado.js` e
    # `verificar_runtime.js` —, cada um com uma alternativa de expressão regular morta por um
    # backspace no lugar da borda de palavra. Portão com alternativa morta não reprova e não avisa:
    # ele passa verde cobrindo menos do que diz. Por isso `.js`, `.yml` e `.sh` entram aqui.
    for alvo in ("*.js", "*.yml", "*.sh"):
        for p in sorted(RAIZ.rglob(alvo)):
            if any(x in p.parts for x in ("node_modules", "__pycache__", ".git", "arquivo")):
                continue
            rel = p.relative_to(RAIZ).as_posix()
            try:
                problemas += caracteres_de_controle(p.read_text(encoding="utf-8"), rel)
            except (OSError, UnicodeDecodeError):
                continue
            arquivos += 1
    if problemas:
        print(f"✗ ESCRITA PORTÁVEL: {len(problemas)} sítio(s) de escrita que corrompem o arquivo fora do runner:")
        for x in problemas[:20]:
            print("   ", x)
        if len(problemas) > 20:
            print(f"    … e mais {len(problemas) - 20}")
        print(f'    Conserto: acrescentar newline="\\n" (ou lineterminator="\\n" no csv). Exceção justificada '
              f'declara "# {MARCA_EXCECAO} <motivo>" na própria linha.')
        return 1
    print(f"✓ ESCRITA PORTÁVEL OK — {arquivos} arquivo(s) de fonte (.py, .js, .yml, .sh): nenhuma "
          f"escrita em modo texto sem newline fixado, nenhum caractere de controle no fonte.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
