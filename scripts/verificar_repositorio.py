#!/usr/bin/env python3
"""Regras do repositório, num executor só (consolidação, item 6, 20/10/2026).

Seis portões liam o que está versionado (fonte, workflows, CHANGELOG, páginas) e tinham o mesmo
esqueleto: docstring, função pura, autoteste, `main()`. Aqui cada regra é um bloco — `problemas_*`
(pura), `real_*` (lê o disco) e `_casos_*` (os casos do autoteste); o esqueleto existe uma vez.
Cada regra e cada caso de teste dos seis foram preservados.

AS REGRAS
  marcadores  nenhum arquivo versionado carrega marcador de conflito de merge: `git add -A` marca o
              caminho como resolvido com os marcadores dentro (CHANGELOG, 28/09/2026, duas vezes).
              `=======` sozinho é sublinhado legítimo de Markdown; só abertura e fechamento acusam.
  escrita     escrita portável (§178, 23/09/2026): `open(..., "w")`, `write_text` e `csv.writer` sem
              `newline="\\n"`/`lineterminator` saem em CRLF no Windows e o hash do manifesto deixa de
              bater; e caractere de controle no fonte (05/10/2026: o `\\b` de regex que virou
              backspace e matou a alternativa sem erro). Lê o código com `ast`. Exceção na própria
              linha: `# escrita-nao-portavel-ok: <motivo>`. `assets/vendor/` fica fora.
  arquivada   página arquivada não volta ao ar por descuido (§258, 27/09/2026): nenhum HTML publicado a
              linka (`previa/` é exceção declarada, contada como nota; nome em prosa também é nota),
              os arquivos estão guardados, `netlify.toml` devolve 404 para `/arquivo/*`, e voltar
              exige a linha no CHANGELOG.
  changelog   entrada nova de CHANGELOG tem chave `AAAA-MM-DD · #PR · título` e no máximo 80
              palavras (30/09/2026); as antigas ficam como estão.
  carimbo     o corte é a data da rodada (`corte` == `atualizado_em`, 30/09/2026) e é escrito em
              `atualizar.py` antes da primeira verificação (01/10/2026).
  scripts     todo script citado por workflow existe (A1-25), as listas de escritor de pista apontam
              para arquivos reais (09/10/2026) e nenhum `.py` usa nome indefinido (F56, pyflakes).
  cliente     um cliente só e nunca disfarçado: nenhum `User-Agent` literal fora de `coletores_base`,
              nenhum token de navegador, cabeçalho ASCII por propósito, pedido cru identifica o cliente
              (§228, §235; por AST).

BARRA A PUBLICAÇÃO (editoria, 06/10/2026) só `marcadores` e `escrita`; as outras cinco reprovam o PR e
não seguram o publicador. Por isso a CI chama o executor duas vezes: `--barra` e `--resto`.

USO
  python3 scripts/verificar_repositorio.py [--barra | --resto]   # confere o repositório
  python3 scripts/verificar_repositorio.py --preparados          # só `marcadores`, no que vai no commit (hook)
  python3 scripts/verificar_repositorio.py --autoteste           # puro: não escreve nada
"""
from __future__ import annotations

import ast
import datetime
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))


def _git(*args) -> list:
    saida = subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True)
    if saida.returncode != 0:
        raise RuntimeError(f"git {' '.join(args[:2])} falhou: " + (saida.stderr or "").strip()[:200])
    return [c for c in saida.stdout.split("\0") if c]


def _escrever(caminho: pathlib.Path, texto: str):
    caminho.write_text(texto, encoding="utf-8", newline="\n")


# ───────────────────────────── marcadores ─────────────────────────────
MARCADORES = ("<<<<<<< ", ">>>>>>> ")
EXCECAO_MARCADORES = {"scripts/verificar_repositorio.py"}   # o próprio fonte explica o que procura


def problemas_marcadores(caminhos: list, ler=None) -> list:
    """[(caminho, linha, marcador)]. `ler` é injetável para o autoteste."""
    def ler_arquivo(rel):
        try:
            return (RAIZ / rel).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None        # binário ou ilegível: não é onde marcador de merge se esconde
    ler = ler or ler_arquivo
    achados = []
    for rel in caminhos:
        texto = None if rel in EXCECAO_MARCADORES else ler(rel)
        for n, linha in enumerate((texto or "").split("\n"), 1):
            achados += [(rel, n, m.strip()) for m in MARCADORES if linha.startswith(m)]
    return achados


def real_marcadores(preparados=False):
    caminhos = (_git("diff", "--cached", "--name-only", "--diff-filter=ACM", "-z") if preparados
                else _git("ls-files", "-z"))
    achados = problemas_marcadores(caminhos)
    falhas = [f"{rel}:{n} — {m}" for rel, n, m in achados]
    if falhas:
        falhas.append("`git add` marca como resolvido mesmo com os marcadores dentro; una os dois "
                      "lados e confira pela ausência de marcador.")
    return falhas, f"nenhum dos {len(caminhos)} arquivos conferidos tem merge não resolvido"


def _casos_marcadores() -> list:
    conteudo = {"limpo.md": "# título\n=======\ntexto normal\n",
                "sujo.md": "antes\n<<<<<<< HEAD\nnosso\n=======\ndeles\n>>>>>>> origin/main\ndepois\n",
                "binario.bin": None, "scripts/verificar_repositorio.py": "<<<<<<< HEAD\n"}
    lido = lambda rel: conteudo.get(rel)  # noqa: E731
    achados = problemas_marcadores(list(conteudo), ler=lido)
    sujo = [a for a in achados if a[0] == "sujo.md"]
    return [("acusa o arquivo com marcador", bool(sujo)),
            ("acusa abertura e fechamento", len(sujo) == 2),
            ("diz a linha", sorted(a[1] for a in sujo) == [2, 6]),
            ("`=======` sozinho não acusa (sublinhado de Markdown é legítimo)",
             not any(a[0] == "limpo.md" for a in achados)),
            ("binário ilegível é ignorado", not any(a[0] == "binario.bin" for a in achados)),
            ("o próprio portão está na exceção",
             not any(a[0].endswith("verificar_repositorio.py") for a in achados)),
            ("repositório limpo devolve lista vazia", problemas_marcadores(["limpo.md"], ler=lido) == [])]


# ───────────────────────────── escrita portável ─────────────────────────────
MARCA_EXCECAO = "escrita-nao-portavel-ok:"


def _modo_de(no: ast.Call):
    """Modo literal de uma chamada a open(), por posição ou por palavra-chave; None se não é literal."""
    if len(no.args) >= 2 and isinstance(no.args[1], ast.Constant) and isinstance(no.args[1].value, str):
        return no.args[1].value
    for k in no.keywords:
        if k.arg == "mode" and isinstance(k.value, ast.Constant) and isinstance(k.value.value, str):
            return k.value.value
    return None


def problemas_escrita(src: str, nome: str = "<fonte>") -> list:
    try:
        arvore = ast.parse(src)
    except SyntaxError as e:
        return [f"{nome}:{e.lineno}: não compila ({e.msg})"]
    linhas, problemas = src.split("\n"), []
    for no in ast.walk(arvore):
        if not isinstance(no, ast.Call) or MARCA_EXCECAO in linhas[no.lineno - 1]:
            continue
        tem = {k.arg for k in no.keywords}
        if isinstance(no.func, ast.Name) and no.func.id == "open":
            modo = _modo_de(no)
            if modo and "b" not in modo and any(m in modo for m in "wax") and "newline" not in tem:
                problemas.append(f'{nome}:{no.lineno}: open(..., "{modo}") sem newline="\\n" — no Windows sai em CRLF')
        elif isinstance(no.func, ast.Attribute):
            if no.func.attr == "write_text" and "newline" not in tem:
                problemas.append(f'{nome}:{no.lineno}: write_text(...) sem newline="\\n" — no Windows sai em CRLF')
            elif no.func.attr in ("writer", "DictWriter") and "lineterminator" not in tem:
                # csv.writer escreve \r\n por padrão em TODO sistema, não só no Windows
                problemas.append(f"{nome}:{no.lineno}: csv.{no.func.attr}(...) sem lineterminator — o padrão do módulo é CRLF")
    return problemas


def caracteres_de_controle(texto: str, nome: str = "<fonte>") -> list:
    """Bytes de controle no meio do fonte (05/10/2026: heredoc do shell que gravou o backspace no lugar
    do `\\b`). Tabulação, nova linha e retorno são brancos legítimos. `assets/vendor/` (jspdf traz um
    0x01 numa literal) fica fora. NÃO usa `splitlines()`: ele engole `\\x0b` e `\\x0c` como fim de
    linha, e portão cego no que procura é o defeito que ele existe para pegar."""
    if "assets/vendor/" in (nome or ""):
        return []
    fora, linha, acusada = [], 1, 0
    for c in (texto or ""):
        if c == "\n":
            linha += 1
        elif ord(c) < 0x20 and ord(c) not in (0x09, 0x0a, 0x0d) and acusada != linha:
            acusada = linha
            fora.append(f"{nome}:{linha}: caractere de controle {hex(ord(c))} no fonte — "
                        f"escape do shell que virou byte; reescreva a linha com Edit/Write")
    return fora


def real_escrita():
    problemas, arquivos = [], 0
    for p in sorted(RAIZ.rglob("*.py")):
        if "__pycache__" in p.parts:
            continue
        arquivos += 1
        fonte, rel = p.read_text(encoding="utf-8"), p.relative_to(RAIZ).as_posix()
        problemas += problemas_escrita(fonte, rel) + caracteres_de_controle(fonte, rel)
    for alvo in ("*.js", "*.yml", "*.sh"):     # portão em JS também já teve alternativa morta por backspace
        for p in sorted(RAIZ.rglob(alvo)):
            if any(x in p.parts for x in ("node_modules", "__pycache__", ".git", "arquivo")):
                continue
            try:
                problemas += caracteres_de_controle(p.read_text(encoding="utf-8"), p.relative_to(RAIZ).as_posix())
            except (OSError, UnicodeDecodeError):
                continue
            arquivos += 1
    if problemas:
        problemas.append(f'Conserto: acrescentar newline="\\n" (ou lineterminator="\\n" no csv). Exceção '
                         f'justificada declara "# {MARCA_EXCECAO} <motivo>" na própria linha.')
    return problemas, (f"{arquivos} arquivo(s) de fonte (.py, .js, .yml, .sh): nenhuma escrita em modo "
                       "texto sem newline fixado, nenhum caractere de controle no fonte")


def _casos_escrita() -> list:
    formas = [('open(p, "w")', 1), ('open(p, "w", encoding="utf-8")', 1), ('open(p, "a")', 1),
              ('open(p, mode="w")', 1), ('open(p, "w", newline="\\n")', 0),
              ('open(p, "wb")', 0),                      # binário não traduz nada
              ('open(p, "rb")', 0), ('open(p)', 0),      # leitura
              ('P.write_text(t, encoding="utf-8")', 1),
              ('P.write_text(t, encoding="utf-8", newline="\\n")', 0), ('P.write_bytes(b)', 0),
              ('csv.writer(buf)', 1), ('csv.DictWriter(buf, fieldnames=c)', 1),
              ('csv.writer(buf, lineterminator="\\n")', 0),
              ('open(p, "w")  # escrita-nao-portavel-ok: temporário fora do repositório', 0),
              ('"""docstring que fala de open(p, \\"w\\") sem escrever nada"""', 0),
              ('# open(p, "w") comentado', 0)]
    casos = [(f"forma {src!r}: {esperado} problema(s)", len(problemas_escrita(src, "teste")) == esperado)
             for src, esperado in formas]
    bs = chr(8)    # o defeito real: um backspace onde devia estar a borda de palavra da regex
    controle = [(f'    r"|{bs}SES[-/]?[A-Z]{{2}}{bs}"', 1), ('    r"|\\bSES[-/]?[A-Z]{2}\\b"', 0),
                (f'if (/{bs}199{bs}|40199/.test(x))', 1), (f'linha um\nlinha {chr(1)}dois\nlinha tres', 1),
                (f'{chr(11)}{chr(12)}', 1),              # VT e FF na mesma linha: uma acusação
                (f'linha um{chr(11)}ainda a um', 1), ("tabulação\tnão é controle proibido", 0),
                ("quebra\nde\nlinha\nnão é", 0), ("retorno\r\nde carro é assunto do newline, não daqui", 0),
                ("", 0)]
    casos += [(f"controle {src!r}: {esperado}", len(caracteres_de_controle(src, "teste")) == esperado)
              for src, esperado in controle]
    return casos + [("assets/vendor/ fora da varredura de controle",
                     not caracteres_de_controle(chr(8), "assets/vendor/x.js"))]


# ───────────────────────────── página arquivada ─────────────────────────────
ARQUIVADAS = {"pesquisadores.html": {"arquivo_em": "arquivo/pesquisadores/pesquisadores.html",
                                     "nao_pode_estar_em": ["pesquisadores.html"]},
              "pesquisadores.js": {"arquivo_em": "arquivo/pesquisadores/pesquisadores.js",
                                   "nao_pode_estar_em": ["assets/js/pesquisadores.js"]}}
DECISAO_NO_CHANGELOG = "§258"
# `previa/` é servido por `publish = "."` mas fica atrás de Basic-Auth próprio: pode citar a página
# arquivada, e o portão diz quantos citam, para a conta nunca virar zero por esquecimento.
EXCECAO_DECLARADA = "previa/"
ATRIBUTOS_QUE_LEVAM = ("href", "src", "action", "content")   # o que o navegador SEGUE; nome em prosa é nota


def referencia_em_atributo(nome: str) -> str:
    n = re.escape(nome)
    return (r"(?:" + "|".join(ATRIBUTOS_QUE_LEVAM) + r"|data-[a-z-]+)\s*=\s*[\"'][^\"']*" + n
            + r"|url\(\s*[\"']?[^)]*" + n)


def html_publicado():
    """Todo HTML que o deploy serve, menos `arquivo/` e `evidencias/` (4 GB: a poda é antes de descer)."""
    achados = []
    for raiz, dirs, arquivos in os.walk(RAIZ):
        na_raiz = pathlib.Path(raiz) == RAIZ
        dirs[:] = sorted(d for d in dirs if d not in {".git", "node_modules"}
                         and not (na_raiz and d in {"evidencias", "arquivo"}))
        achados += [pathlib.Path(raiz) / n for n in arquivos if n.endswith(".html")]
    for p in sorted(achados):
        yield p.relative_to(RAIZ).as_posix(), p


def problemas_arquivada() -> tuple:
    p, notas = [], []
    cl = RAIZ / "CHANGELOG.md"
    changelog = cl.read_text(encoding="utf-8", errors="replace") if cl.exists() else ""
    for nome, regra in ARQUIVADAS.items():
        for caminho in regra["nao_pode_estar_em"]:     # voltou para a raiz?
            if (RAIZ / caminho).exists():
                if f"{nome} volta ao ar".lower() not in changelog.lower():
                    p.append(f"{caminho} reapareceu, e o CHANGELOG não registra a decisão de trazê-lo de "
                             f"volta. Arquivar foi decisão da editoria ({DECISAO_NO_CHANGELOG}); "
                             f"desarquivar também tem de ser, com a linha no CHANGELOG — o arquivo de "
                             f"volta, sozinho, não basta.")
                else:
                    notas.append(f"{caminho} está de volta, e o CHANGELOG registra a decisão")
        citam, citam_previa, mencionam = [], [], []
        for rel, arq in html_publicado():              # algum HTML publicado ainda linka?
            texto = re.sub(r"<!--.*?-->", "", arq.read_text(encoding="utf-8", errors="replace"), flags=re.S)
            if re.search(referencia_em_atributo(nome), texto):
                (citam_previa if rel.startswith(EXCECAO_DECLARADA) else citam).append(rel)
            elif nome in texto:
                mencionam.append(rel)
        if citam:
            p.append(f"{len(citam)} HTML publicado ainda menciona {nome}: "
                     f"{', '.join(citam[:6])}{'…' if len(citam) > 6 else ''}")
        if mencionam:
            notas.append(f"{len(mencionam)} HTML publicado nomeia {nome} em prosa, sem linkar: "
                         f"{', '.join(mencionam[:6])} — registro histórico, não link")
        if citam_previa:
            notas.append(f"{len(citam_previa)} protótipo(s) em {EXCECAO_DECLARADA} menciona(m) {nome} — "
                         f"exceção declarada (atrás de senha própria, fora da navegação pública), e a "
                         f"contagem fica visível de propósito")
        if not (RAIZ / regra["arquivo_em"]).exists():
            p.append(f"{regra['arquivo_em']} não existe: o arquivamento diz que o arquivo está guardado, "
                     f"e ele não está")
    nt = RAIZ / "netlify.toml"
    if not nt.exists():
        p.append("netlify.toml não existe")
    else:
        conf = nt.read_text(encoding="utf-8", errors="replace")
        if not (re.search(r'from\s*=\s*"/arquivo/\*"', conf) and re.search(r'status\s*=\s*404', conf)):
            p.append('netlify.toml sem a regra que devolve 404 para "/arquivo/*". Sem ela, `publish = "."` '
                     'serve a pasta de arquivo, e a página que a editoria mandou suprimir continua '
                     'acessível por URL — só sem link, que é pior.')
    if not (RAIZ / "arquivo" / "pesquisadores" / "LEIA-ME.md").exists():
        p.append("arquivo/pesquisadores/LEIA-ME.md não existe: sem ele, quem abrir a pasta não sabe por "
                 "que a página saiu, para onde foram as seções, nem como reativá-la")
    return p, notas


def real_arquivada():
    p, notas = problemas_arquivada()
    for n in notas:
        print(f"  [nota] {n}")
    return p, ("nenhum HTML publicado linka a página, os arquivos estão guardados, `/arquivo/*` devolve "
               "404 e o LEIA-ME explica como reativar")


def _com_repo(monta) -> tuple:
    """`problemas_arquivada()` num repositório de mentira, montado em diretório temporário."""
    global RAIZ
    anterior = RAIZ
    with tempfile.TemporaryDirectory() as t:
        r = pathlib.Path(t)
        (r / "arquivo" / "pesquisadores").mkdir(parents=True)
        for n in ("pesquisadores.html", "pesquisadores.js", "LEIA-ME.md"):
            _escrever(r / "arquivo" / "pesquisadores" / n, "x")
        _escrever(r / "netlify.toml", 'publish = "."\n[[redirects]]\n  from = "/arquivo/*"\n  status = 404\n')
        _escrever(r / "CHANGELOG.md", "# nada\n")
        monta(r)
        RAIZ = r
        try:
            return problemas_arquivada()
        finally:
            RAIZ = anterior


def _casos_arquivada() -> list:
    def pagina(nome, texto):
        return lambda r: _escrever(r / nome, texto)
    pr_limpo, _ = _com_repo(lambda r: None)
    pr_link, _ = _com_repo(pagina("index.html", '<a href="pesquisadores.html">x</a>'))

    def previa(r):
        (r / "previa").mkdir()
        _escrever(r / "previa" / "p.html", '<a href="pesquisadores.html">x</a>')
    pr_previa, notas_previa = _com_repo(previa)
    pr_prosa, notas_prosa = _com_repo(pagina("mudancas.html", "<dd>A página pesquisadores.html saiu do ar em 27/09/2026.</dd>"))
    pr_src, _ = _com_repo(pagina("index.html", '<script src="assets/js/pesquisadores.js"></script>'))
    pr_volta, _ = _com_repo(pagina("pesquisadores.html", "x"))

    def volta_registrada(r):
        _escrever(r / "pesquisadores.html", "x")
        _escrever(r / "CHANGELOG.md", "## §300 pesquisadores.html volta ao ar por decisão da editoria\n")
    pr_registrada, notas_registrada = _com_repo(volta_registrada)
    pr_404, _ = _com_repo(pagina("netlify.toml", 'publish = "."\n'))
    pr_leia, _ = _com_repo(lambda r: (r / "arquivo" / "pesquisadores" / "LEIA-ME.md").unlink())
    pr_guardado, _ = _com_repo(lambda r: shutil.rmtree(r / "arquivo" / "pesquisadores"))
    achou = lambda lista, texto: any(texto in x for x in lista)  # noqa: E731
    return [("o estado atual do repositório passa", problemas_arquivada()[0] == []),
            ("repositório limpo e arquivado passa", pr_limpo == []),
            ("HTML publicado que linka a página arquivada REPROVA",
             achou(pr_link, "ainda menciona pesquisadores.html")),
            ("protótipo em previa/ é NOTA, não falha", pr_previa == [] and achou(notas_previa, "protótipo")),
            ("nome em PROSA, sem link, é nota e não falha", pr_prosa == [] and achou(notas_prosa, "em prosa")),
            ("src apontando para o script arquivado REPROVA", achou(pr_src, "ainda menciona pesquisadores.js")),
            ("arquivo de volta na raiz SEM linha no CHANGELOG reprova", achou(pr_volta, "não registra a decisão")),
            ("arquivo de volta COM linha no CHANGELOG passa, e vira nota",
             pr_registrada == [] and achou(notas_registrada, "está de volta")),
            ("sem a regra de 404 para /arquivo/* REPROVA", achou(pr_404, "404")),
            ("sem o LEIA-ME REPROVA", achou(pr_leia, "LEIA-ME")),
            ("arquivo que não está guardado onde se disse REPROVA", achou(pr_guardado, "não existe: o arquivamento diz"))]


# ───────────────────────────── CHANGELOG curto ─────────────────────────────
TETO_DE_PALAVRAS = 80
VALE_A_PARTIR_DE = datetime.date(2026, 10, 1)    # antes dela, o histórico fica intacto
RE_TITULO = re.compile(r"^## (.+)$", re.M)
RE_FORMATO_NOVO = re.compile(r"^(\d{4})-(\d{2})-(\d{2}) · #(\d+) · (.+)$")
RE_FORMATO_ANTIGO = re.compile(r"^§\d+ ·")


def entradas(texto: str) -> list:
    achados = list(RE_TITULO.finditer(texto or ""))
    return [(m.group(1).strip(), texto[m.end():achados[i + 1].start() if i + 1 < len(achados) else len(texto)].strip())
            for i, m in enumerate(achados)]


def data_da_entrada(titulo: str):
    """A data da entrada, pelo formato novo ou pelo `· dd/mm/aaaa` do antigo. None se não houver."""
    m = RE_FORMATO_NOVO.match(titulo or "")
    d = m and (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    if not m:
        m = re.search(r"·\s*(\d{2})/(\d{2})/(\d{4})\s*$", titulo or "")
        d = m and (int(m.group(3)), int(m.group(2)), int(m.group(1)))
    try:
        return datetime.date(*d) if m else None
    except ValueError:
        return None


def palavras(corpo: str) -> int:
    """Tabela é dado, não prosa: cobrar palavras dentro dela empurraria para prosa pior."""
    limpo = re.sub(r"```.*?```", " ", corpo or "", flags=re.S)
    limpo = "\n".join(l for l in limpo.split("\n") if not l.strip().startswith("|"))
    return len([p for p in re.split(r"\s+", limpo) if p.strip()])


def problemas_changelog(texto: str) -> list:
    ruins = []
    for titulo, corpo in entradas(texto):
        d = data_da_entrada(titulo)
        if d is None or d < VALE_A_PARTIR_DE:
            continue          # histórico: fica como está
        if RE_FORMATO_ANTIGO.match(titulo):
            ruins.append(f"{titulo[:60]}: numeração § sequencial — use `AAAA-MM-DD · #PR · título`")
        elif not RE_FORMATO_NOVO.match(titulo):
            ruins.append(f"{titulo[:60]}: título fora do formato `AAAA-MM-DD · #PR · título`")
        elif palavras(corpo) > TETO_DE_PALAVRAS:
            ruins.append(f"{titulo[:60]}: {palavras(corpo)} palavras, acima do teto de {TETO_DE_PALAVRAS} — "
                         f"fundamentação longa vai para a METODOLOGIA")
    return ruins


def real_changelog():
    return (problemas_changelog((RAIZ / "CHANGELOG.md").read_text(encoding="utf-8")),
            f"entradas a partir de {VALE_A_PARTIR_DE.strftime('%d/%m/%Y')} com chave por data e PR e no "
            f"máximo {TETO_DE_PALAVRAS} palavras")


def _casos_changelog() -> list:
    cab = "## 2026-10-02 · #500 · T\n\n"
    return [("entrada nova, curta e no formato, passa",
             problemas_changelog("## 2026-10-02 · #500 · Título curto\n\nUma frase.\n") == []),
            ("entrada antiga com § não é cobrada",
             problemas_changelog("## §300 · Coisa antiga · 30/09/2026\n\n" + "palavra " * 300) == []),
            ("entrada nova com § reprova", len(problemas_changelog("## §400 · Coisa · 02/10/2026\n\nx")) == 1),
            ("entrada nova longa reprova", len(problemas_changelog(cab + "palavra " * 200)) == 1),
            ("a falha de tamanho diz o número de palavras",
             "200 palavras" in problemas_changelog(cab + "palavra " * 200)[0]),
            ("título novo fora do formato reprova", len(problemas_changelog("## 02/10/2026 — coisa\n\nx")) == 0),
            ("data anterior ao corte não é cobrada",
             problemas_changelog("## 2026-09-30 · #1 · T\n\n" + "palavra " * 300) == []),
            ("tabela não conta como prosa",
             problemas_changelog(cab + "\n".join("| a | b |" for _ in range(200))) == []),
            ("bloco de código não conta como prosa", problemas_changelog(cab + "```\n" + "x " * 300 + "\n```") == []),
            ("changelog vazio passa", problemas_changelog("") == []),
            ("lê a data do formato novo", data_da_entrada("2026-10-02 · #500 · T") == datetime.date(2026, 10, 2)),
            ("lê a data do formato antigo", data_da_entrada("§300 · Coisa · 30/09/2026") == datetime.date(2026, 9, 30)),
            ("título sem data devolve None", data_da_entrada("Coisa qualquer") is None),
            ("data impossível não quebra", data_da_entrada("§1 · x · 31/02/2026") is None),
            (f"o teto é de {TETO_DE_PALAVRAS} palavras", TETO_DE_PALAVRAS == 80)]


# ───────────────────────────── carimbo da rodada ─────────────────────────────
RE_DATA = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")
RE_CARIMBO = re.compile(r'meta\["corte"\]\s*=\s*hoje')
# `verificar_vigencia.py` é COLETOR (roda antes do carimbo) e não conta como verificação.
RE_PORTAO = re.compile(r'rodar\(\[(?:sys\.executable|"node"|"bash"),\s*"(?:scripts/verificar_|verificar_consistencia\.py)')


def data_de(texto: str):
    m = RE_DATA.match(str(texto or "").strip())
    try:
        return datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else None
    except ValueError:
        return None


def problemas_carimbo(meta: dict) -> list:
    """O que o carimbo diz: `corte` == `atualizado_em` (depois da rodada, "rodou e não achou nada novo"
    é informação, diferente de "parou de rodar")."""
    ruins = []
    corte, atualizado = data_de((meta or {}).get("corte")), data_de((meta or {}).get("atualizado_em"))
    if corte is None:
        ruins.append(f"`corte` ilegível ou ausente: {(meta or {}).get('corte')!r}")
    if atualizado is None:
        ruins.append(f"`atualizado_em` ilegível ou ausente: {(meta or {}).get('atualizado_em')!r}")
    if corte and atualizado:
        if corte != atualizado:
            ruins.append(f"`corte` ({corte.strftime('%d/%m/%Y')}) ≠ `atualizado_em` "
                         f"({atualizado.strftime('%d/%m/%Y')}) — o corte é a data da rodada, e a "
                         f"rodada aconteceu. Diferença de {(atualizado - corte).days} dia(s).")
        if corte > atualizado:
            ruins.append("`corte` é posterior a `atualizado_em`: dado com data futura em relação "
                         "à própria rodada")
    return ruins


def problemas_de_ordem(fonte: str) -> list:
    """Quando o carimbo é escrito: antes da primeira verificação em `atualizar.py`. Carimbo ausente é
    falha por si: sem ele o corte congela, que foi o defeito de 30/09."""
    carimbo, primeiro_portao = RE_CARIMBO.search(fonte or ""), RE_PORTAO.search(fonte or "")
    if carimbo is None:
        return ['`meta["corte"] = hoje` não aparece em atualizar.py: sem o carimbo da rodada, '
                "o corte congela e o site passa a dizer uma data que não é a da coleta"]
    if primeiro_portao is None:
        return ["nenhuma chamada de verificação encontrada em atualizar.py: a bateria de portões "
                "saiu da rodada"]
    if carimbo.start() > primeiro_portao.start():
        return [f"o carimbo da rodada (`meta[\"corte\"] = hoje`, posição {carimbo.start()}) vem "
                f"DEPOIS da primeira verificação (posição {primeiro_portao.start()}): no meio da "
                f"rodada `meta.json` fica com `atualizado_em` de hoje e `corte` de ontem, e a "
                f"publicação para no portão do corte sincronizado"]
    return []


def real_carimbo():
    meta = json.loads((RAIZ / "data" / "meta.json").read_text(encoding="utf-8"))
    return (problemas_carimbo(meta) + problemas_de_ordem((RAIZ / "atualizar.py").read_text(encoding="utf-8")),
            f"`corte` e `atualizado_em` na mesma data ({meta.get('corte')}), e o carimbo é escrito "
            "antes da bateria de portões")


def _casos_carimbo() -> list:
    antes = 'meta["corte"] = hoje\nrodar([sys.executable, "verificar_consistencia.py"], obrigatorio=True)\n'
    depois = 'rodar([sys.executable, "verificar_consistencia.py"], obrigatorio=True)\nmeta["corte"] = hoje\n'
    com_node = 'meta["corte"] = hoje\nrodar(["node", "scripts/verificar_runtime.js"], obrigatorio=True)\n'
    node_antes = 'rodar(["node", "scripts/verificar_runtime.js"], obrigatorio=True)\nmeta["corte"] = hoje\n'
    m = lambda c, a: {"corte": c, "atualizado_em": a}  # noqa: E731
    return [("iguais passam", problemas_carimbo(m("30/09/2026", "30/09/2026")) == []),
            ("corte atrasado reprova", len(problemas_carimbo(m("10/09/2026", "30/09/2026"))) == 1),
            ("a falha diz de quantos dias é o atraso", "20 dia(s)" in problemas_carimbo(m("10/09/2026", "30/09/2026"))[0]),
            ("corte no futuro reprova duas vezes (diferente e posterior)",
             len(problemas_carimbo(m("30/09/2026", "10/09/2026"))) == 2),
            ("corte ausente reprova", any("corte` ilegível" in x for x in problemas_carimbo({"atualizado_em": "30/09/2026"}))),
            ("atualizado ausente reprova",
             any("atualizado_em` ilegível" in x for x in problemas_carimbo({"corte": "30/09/2026"}))),
            ("data impossível é ilegível", any("ilegível" in x for x in problemas_carimbo(m("31/02/2026", "30/09/2026")))),
            ("formato ISO não passa por carimbo", any("ilegível" in x for x in problemas_carimbo(m("2026-09-30", "30/09/2026")))),
            ("meta vazio reprova", len(problemas_carimbo({})) == 2),
            ("meta nulo não quebra", len(problemas_carimbo(None)) == 2),
            ("lê a data do carimbo", data_de("30/09/2026") == datetime.date(2026, 9, 30)),
            ("texto que não é data devolve None", data_de("ontem") is None),
            ("carimbo antes da verificação passa", problemas_de_ordem(antes) == []),
            ("carimbo depois da verificação reprova", len(problemas_de_ordem(depois)) == 1),
            ("a falha diz o que acontece na publicação", "corte sincronizado" in problemas_de_ordem(depois)[0]),
            ("portão de node também conta como verificação", problemas_de_ordem(com_node) == []),
            ("coletor com nome de verificação não conta como portão",
             problemas_de_ordem('rodar([sys.executable, "verificar_vigencia.py"])\nmeta["corte"] = hoje\n'
                                'rodar([sys.executable, "verificar_consistencia.py"])\n') == []),
            ("portão de node depois do carimbo reprova", len(problemas_de_ordem(node_antes)) == 1),
            ("carimbo ausente reprova",
             any("não aparece" in x for x in problemas_de_ordem('rodar([sys.executable, "verificar_x.py"])'))),
            ("bateria ausente reprova", any("saiu da rodada" in x for x in problemas_de_ordem('meta["corte"] = hoje'))),
            ("fonte vazia não quebra", len(problemas_de_ordem("")) == 1),
            ("fonte nula não quebra", len(problemas_de_ordem(None)) == 1),
            ("o atualizar.py em vigor passa",      # o fonte REAL, que o portão cobra todo dia
             problemas_de_ordem((RAIZ / "atualizar.py").read_text(encoding="utf-8")) == [])]


# ───────────────────────────── scripts dos workflows ─────────────────────────────
FLUXOS = RAIZ / ".github" / "workflows"
CITACAO = re.compile(r"(?:python3?|bash|sh|node)\s+([A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:py|sh|js))")
# Quem a lista de escritores de pista declara (09/10/2026: `migrar_pistas_para_o_esquema.py` estava lá
# desde 06/10 e não existia). Declaração que aponta para o vazio não protege nada.
LISTA_DE_ESCRITORES = "scripts/verificar_escritor_de_pista.py"


def citados(texto: str) -> list:
    """Os caminhos de script citados num YAML, em ordem estável e sem repetição; `$VAR/x.py` fica de
    fora (só se resolve em execução, e adivinhar produziria vermelho falso)."""
    fora = []
    for caminho in CITACAO.findall(texto or ""):
        if not (caminho.startswith("-") or "$" in caminho or caminho in fora):
            fora.append(caminho)
    return fora


def faltantes(mapa: dict, existe) -> list:
    return [(w, c) for w, textos in sorted(mapa.items()) for c in citados(textos) if not existe(c)]


def declarados_em_listas() -> list:
    fonte = (RAIZ / LISTA_DE_ESCRITORES).read_text(encoding="utf-8")
    fora = []
    for nome in ("ESCRITORES", "MANUTENCAO"):
        if f"{nome} = (" in fonte:
            try:
                fora.extend(ast.literal_eval(fonte.split(f"{nome} = ", 1)[1].split(")", 1)[0] + ")"))
            except (SyntaxError, ValueError):
                continue
    return fora


def nomes_indefinidos(fonte: str, nome: str = "<fonte>") -> list:
    """[(linha, nome)] usados sem definição (F56: `monitorar_politica_por_inteiro.py` morreu com NameError
    em 19 rodadas seguidas e nenhum portão viu)."""
    from pyflakes import checker, messages
    try:
        arvore = ast.parse(fonte, filename=nome)
    except SyntaxError as e:
        return [(e.lineno or 0, f"SyntaxError: {e.msg}")]
    return [(m.lineno, m.message_args[0]) for m in checker.Checker(arvore, filename=nome).messages
            if isinstance(m, messages.UndefinedName)]


def real_scripts():
    mapa = {p.name: p.read_text(encoding="utf-8") for p in sorted(FLUXOS.glob("*.yml"))}
    fora = [f"{w} chama {c}, que não existe" for w, c in faltantes(mapa, lambda c: (RAIZ / c).is_file())]
    declarados = declarados_em_listas()
    fora += [f"{LISTA_DE_ESCRITORES} (ESCRITORES/MANUTENCAO) chama {c}, que não existe"
             for c in declarados if not (RAIZ / c).is_file()]
    for c in _git("ls-files", "-z", "*.py"):
        fora += [f"{c}:{linha}: o nome {nome!r}, sem definição"
                 for linha, nome in nomes_indefinidos((RAIZ / c).read_text(encoding="utf-8"), c)]
    return fora, (f"{sum(len(citados(t)) for t in mapa.values()) + len(declarados)} citação(ões) de script em "
                  f"{len(mapa)} workflow(s); todas existem na árvore")


def _casos_scripts() -> list:
    return [("acha o script de um passo simples", citados("      - run: python3 scripts/a.py --x") == ["scripts/a.py"]),
            ("acha bash e node também", citados("bash scripts/b.sh\nnode scripts/c.js") == ["scripts/b.sh", "scripts/c.js"]),
            ("não repete o mesmo caminho", citados("python3 a.py\npython3 a.py") == ["a.py"]),
            ("caminho com variável fica de fora", citados("python3 $DIR/a.py") == []),
            ("script ausente reprova", faltantes({"w.yml": "python3 scripts/nao_existe.py"}, lambda _c: False)
             == [("w.yml", "scripts/nao_existe.py")]),
            ("script presente passa", faltantes({"w.yml": "python3 scripts/existe.py"}, lambda _c: True) == []),
            ("o workflow do defeito é lido de verdade", (FLUXOS / "consolidar_noite.yml").exists()),
            ("as listas de escritor de pista são lidas e apontam para arquivos reais",
             all((RAIZ / c).is_file() for c in declarados_em_listas())),
            ("há declaração a conferir nas listas", len(declarados_em_listas()) >= 10),
            ("nome usado sem import reprova (F56)", nomes_indefinidos("import json\nler('x')\n") == [(2, "ler")]),
            ("nome importado passa", nomes_indefinidos("from os import path\npath.join('a')\n") == [])]


# ───────────── cliente identificado, nunca disfarçado (§228, §235; 26/09/2026) ─────────────
# Uma auditoria achou 21 strings de User-Agent, seis com token de navegador: cópia que envelhece (o
# `UA` canônico de `coletores_base` não mudava os outros arquivos, e a política de robots §185 mede
# um agente e registra outro) e disfarce (CLAUDE.md: nunca disfarçar o cliente). Lê por AST, para que
# docstring e comentário possam contar a história. (a) valor de `User-Agent` nunca é literal fora de
# `coletores_base.py`; (b) nenhuma string de código traz token de navegador; (c) o `UA` canônico começa
# com o nome do projeto; (c-bis) §235: `ua_de(propósito)` gera cabeçalho ASCII (RFC 7230 §3.2.4) para
# cada propósito literal — `defesacivil.es.gov.br` deu HTTP 400 com acento e 200 sem; (d) todo módulo
# com pedido de rede cru (`urlopen`, `build_opener`, `requests.get`…) identifica o cliente.
TOKEN_NAVEGADOR = "Mozi" + "lla/"      # por pedaços: a regra não pode reprovar a si mesma
CRUAS = ("urlopen", "build_opener")


def _nome_ast(no) -> str:
    """'coletores_base.ua_de' para um Attribute/Name, ou ''."""
    if isinstance(no, ast.Attribute):
        return f"{_nome_ast(no.value)}.{no.attr}".lstrip(".")
    return no.id if isinstance(no, ast.Name) else ""


def problemas_cliente(fonte: str, nome: str, ua_de, eh_base: bool = False) -> list:
    """`nome` é o caminho relativo; `ua_de` a função canônica; `eh_base` isenta `coletores_base.py`."""
    try:
        arvore = ast.parse(fonte)
    except SyntaxError as e:
        return [f"{nome}: não compila ({e})"]
    docs = {id(c.body[0].value) for c in ast.walk(arvore)
            if isinstance(c, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
            and c.body and isinstance(c.body[0], ast.Expr)
            and isinstance(c.body[0].value, ast.Constant) and isinstance(c.body[0].value.value, str)}
    falhas, nos = [], list(ast.walk(arvore))
    for no in nos:
        if not eh_base and isinstance(no, ast.Dict):
            falhas += [f"{nome}:{no.lineno} User-Agent literal — use UA ou ua_de(\"propósito\"): "
                       f"{str(v.value)[:50]!r}" for k, v in zip(no.keys, no.values)
                       if isinstance(k, ast.Constant) and k.value == "User-Agent" and isinstance(v, ast.Constant)]
        if not eh_base and isinstance(no, ast.Tuple) and len(no.elts) == 2:
            a, b = no.elts
            if isinstance(a, ast.Constant) and a.value == "User-Agent" and isinstance(b, ast.Constant):
                falhas.append(f"{nome}:{no.lineno} User-Agent literal em addheaders — use UA ou ua_de(\"propósito\")")
        if isinstance(no, ast.Constant) and isinstance(no.value, str) and id(no) not in docs \
                and TOKEN_NAVEGADOR in no.value:
            falhas.append(f"{nome}:{no.lineno} string de código com token de navegador — "
                          "nunca disfarçar o cliente (CLAUDE.md)")
        if isinstance(no, ast.Call) and _nome_ast(no.func).split(".")[-1] == "ua_de" and no.args \
                and isinstance(no.args[0], ast.Constant) and isinstance(no.args[0].value, str) \
                and not ua_de(no.args[0].value).isascii():
            falhas.append(f"{nome}:{no.lineno} ua_de({no.args[0].value!r}) gera cabeçalho não-ASCII — "
                          "cabeçalho HTTP é ASCII (RFC 7230); veja §235")
    cru = any((isinstance(n, ast.Name) and n.id in CRUAS) or (isinstance(n, ast.Attribute) and (
        n.attr in CRUAS or (isinstance(n.value, ast.Name) and n.value.id == "requests"
                            and n.attr in ("get", "post", "head", "put", "request")))) for n in nos)
    if cru and not eh_base and not any(t in fonte for t in ("User-Agent", "addheaders", "from coletores_base import")):
        falhas.append(f"{nome} faz pedido de rede cru sem identificar o cliente — "
                      "a política de robots (§185) depende do cliente enviado")
    return falhas


def real_cliente():
    from coletores_base import UA, ua_de
    if not UA.startswith("MonitorElNino") or TOKEN_NAVEGADOR in UA:
        return [f"o UA canônico não começa com o nome do projeto ou traz token de navegador: {UA[:60]!r}"], ""
    arquivos = sorted(list(RAIZ.glob("*.py")) + list(RAIZ.glob("scripts/*.py")))
    falhas = [f for p in arquivos for f in problemas_cliente(
        p.read_text(encoding="utf-8"), p.relative_to(RAIZ).as_posix(), ua_de, p.name == "coletores_base.py")]
    return falhas, f"{len(arquivos)} arquivo(s), um cliente só, nenhum disfarce. UA: {UA}"


def _casos_cliente() -> list:
    ascii_ = lambda s: s
    acusa = lambda fonte, texto, **kw: any(texto in x for x in problemas_cliente(fonte, "x.py", ascii_, **kw))
    return [
        ("User-Agent literal num dict reprova", acusa('h = {"User-Agent": "robo/1"}', "User-Agent literal")),
        ("User-Agent literal em addheaders reprova",
         acusa('o.addheaders = [("User-Agent", "robo/1")]', "addheaders")),
        ("User-Agent vindo de UA ou ua_de passa",
         problemas_cliente('h = {"User-Agent": UA}\ng = {"User-Agent": ua_de("x")}', "x.py", ascii_) == []),
        ("coletores_base.py pode ter o literal", not acusa('h = {"User-Agent": "robo/1"}', "literal", eh_base=True)),
        ("token de navegador em string de código reprova",
         acusa(f'h = "{TOKEN_NAVEGADOR}5.0"', "token de navegador")),
        ("token de navegador em docstring é história, não defeito",
         problemas_cliente(f'"""{TOKEN_NAVEGADOR}5.0 era o disfarce."""', "x.py", ascii_) == []),
        ("ua_de com propósito acentuado que vira cabeçalho não-ASCII reprova (§235)",
         any("não-ASCII" in x for x in problemas_cliente('ua_de("coleta çã")', "x.py", lambda s: s))
         and not acusa('ua_de("coleta")', "não-ASCII")),
        ("pedido cru sem cliente identificado reprova",
         acusa("import urllib.request\nurllib.request.urlopen('http://a')", "pedido de rede cru")),
        ("pedido de requests sem cliente reprova", acusa("import requests\nrequests.get('http://a')", "pedido de rede cru")),
        ("pedido cru com cliente importado de coletores_base passa",
         not acusa("from coletores_base import UA\nurlopen('http://a')", "pedido de rede cru")),
        ("fonte que não compila é acusada", acusa("def (", "não compila")),
    ]


# ───────────────────────────── executor ─────────────────────────────
# (nome, barra a publicação, confere o disco, casos do autoteste, roda o autoteste antes da conferência)
REGRAS = [("marcadores", True, real_marcadores, _casos_marcadores, False),
          ("escrita", True, real_escrita, _casos_escrita, True),
          ("arquivada", False, real_arquivada, _casos_arquivada, True),
          ("changelog", False, real_changelog, _casos_changelog, False),
          ("carimbo", False, real_carimbo, _casos_carimbo, True),
          ("scripts", False, real_scripts, _casos_scripts, False),
          ("cliente", False, real_cliente, _casos_cliente, False)]


def _ruins(nome, casos) -> list:
    return [f"{nome}: {r}" for r, ok in casos() if not ok]


def autoteste() -> int:
    total = ruins = 0
    for nome, _, _, casos, _ in REGRAS:
        for r, ok in casos():
            total += 1
            print(f"  {'OK  ' if ok else 'FALHA'} {nome}: {r}")
            ruins += not ok
    print(f"X AUTOTESTE: {ruins} caso(s) reprovado(s)." if ruins
          else f"OK AUTOTESTE — {total} casos, sem rede e sem escrita.")
    return 1 if ruins else 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    if "--preparados" in sys.argv:
        falhas, resumo = real_marcadores(preparados=True)
        print(f"✗ MARCADORES: {len(falhas)} problema(s)\n" + "\n".join(f"   · {f}" for f in falhas)
              if falhas else f"✓ MARCADORES OK — {resumo}.")
        return 1 if falhas else 0
    so_barra, so_resto = "--barra" in sys.argv, "--resto" in sys.argv
    ruim = False
    for nome, barra, real, casos, antes in REGRAS:
        if (so_barra and not barra) or (so_resto and barra):
            continue
        falhas = _ruins(nome, casos) if antes else []
        resumo = ""
        if not falhas:
            falhas, resumo = real()
        if falhas:
            ruim = True
            print(f"✗ {nome.upper()}: {len(falhas)} problema(s)")
            for f in falhas[:40]:
                print(f"   · {f}")
            if len(falhas) > 40:
                print(f"   … e outros {len(falhas) - 40}")
        else:
            print(f"✓ {nome.upper()} OK — {resumo}.")
    return 1 if ruim else 0


if __name__ == "__main__":
    sys.exit(main())
