#!/usr/bin/env python3
"""Gera o `CODEMAP.md`: que arquivo afeta que tela, consome que dado, é coberto por que portão.

Item 1 do handover de otimização do ciclo de mudança (editoria, 30/09/2026).

PARA QUE SERVE, E POR QUE É GERADO E NÃO ESCRITO À MÃO
------------------------------------------------------
O custo maior de cada pedido não é rodar os portões: é **reexplorar o repositório do zero** para
descobrir o que a mudança toca. São 99 scripts Python na raiz, 36 portões e dez páginas; achar
"quem lê `data/municipios.json`" por busca custa minutos, toda vez, e o resultado se perde no fim
da sessão.

O mapa responde isso de uma vez. E é **gerado do próprio código** — dos `fetch(...)` do JavaScript,
dos `gravar(...)`/`gravar_em(...)` do Python, das listas de páginas dos portões — porque mapa
escrito à mão envelhece em silêncio, e mapa que mente é pior que mapa nenhum: manda ler o arquivo
errado com a confiança de quem conferiu.

O QUE ELE NÃO PROMETE
---------------------
Não é análise de dependência completa: não segue `import` transitivo nem chamada dinâmica. É um
índice de primeira ordem, e diz isso na própria página. Para o uso que tem — "por onde começo a
ler" — é o suficiente; para "nada mais pode ser afetado", não é, e o portão de runtime continua
sendo quem responde isso.

USO
  python3 scripts/gerar_codemap.py            # reescreve CODEMAP.md
  python3 scripts/gerar_codemap.py --conferir  # falha se o mapa estiver desatualizado
  python3 scripts/gerar_codemap.py --autoteste
"""
import ast
import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
MAPA = RAIZ / "CODEMAP.md"

RE_FETCH = re.compile(r"""fetch\(\s*['"]([^'"]+)['"]""")
RE_FETCH_DADO = re.compile(r"""['"]data/([\w./-]+\.json)['"]""")
RE_GRAVAR = re.compile(r"""gravar(?:_em)?\(\s*(?:[A-Z_]+\s*/\s*)?['"]([\w./-]+\.json)['"]""")
RE_SAIDA = re.compile(r"""^(?:SAIDA|ARQUIVO|DESTINO)\s*=\s*.*?['"]([\w./-]+\.json)['"]""", re.M)
# `index.js` não escreve o nome de cada arquivo: monta `fetch('data/' + f + '.json')` sobre uma
# lista de nomes. Sem ler esse idioma, o mapa dizia "— " justamente na página mais carregada do
# site, que é o caso em que ele mais precisa acertar. Mapa que mente é pior que mapa nenhum.
RE_FETCH_MONTADO = re.compile(r"""fetch\(\s*['"]data/['"]\s*\+""")
RE_LISTA_DE_NOMES = re.compile(r"""\[((?:\s*['"][\w./-]+['"]\s*,){2,}\s*['"][\w./-]+['"]\s*)\]""")
RE_NOME = re.compile(r"""['"]([\w./-]+)['"]""")

RE_PAGINAS_PORTAO = re.compile(r"""(?:PAGINAS|PADRAO)\s*=\s*\[(.*?)\]""", re.S)
RE_HTML = re.compile(r"""['"]([\w-]+\.html)['"]""")
# O `src` leva `?v=hash` de cache-busting, e nem todo script da página vive em `assets/js/` —
# `acesso.js`, `mapas.js` e `colunas.js` estão em `assets/`. Exigir o caminho exato e o fecho de
# aspas logo após o `.js` fazia o mapa não achar script nenhum na inicial.
RE_SCRIPT_HTML = re.compile(r"""<script[^>]+src=['"]assets/(?:js/)?([\w-]+\.js)(?:\?[^'"]*)?['"]""")

TOCA_O_INDICE = ("recalcular_mare.py", "aplicar_promocoes_do_juiz.py", "juiz.py",
                 "converter_contribuicao.py", "gerar_resposta.py")


def importadores(fontes: dict) -> dict:
    """{caminho: quantos arquivos o importam}. Função pura — recebe `{caminho: fonte}`.

    05/10/2026 — A COLUNA QUE O GRAFO DE DEPENDÊNCIAS PRODUZIU, e que o mapa não tinha.
    O cabeçalho do CODEMAP sempre disse, com razão, que ele não é análise de dependência completa.
    Mas há um fato de primeira ordem que ele podia dar e não dava: **quantos arquivos importam
    este**. É a resposta mais útil para "o que a minha mudança alcança".

    Medido em 05/10: `coletores_base.py` tem **169 importadores** — dois terços dos 247 `.py` do
    repositório. Isso explica, retroativamente, por que os dois acidentes de isolamento daqui
    custaram tanto: em 02/10 um ajudante que gravava neste módulo apagou 907 atos do ciclo, e em
    05/10 o mesmo desenho apagou seis execuções do log. Quem mexe num arquivo com 169 importadores
    precisa ver esse número ANTES de mexer, e agora ele está na linha.

    Conta `import x` e `from x import y` em nível de módulo ou dentro de função — as duas formas
    valem, porque as duas criam dependência. Import relativo (`from . import x`) fica fora: o
    projeto não os usa, e resolvê-los exigiria saber o pacote.
    """
    por_nome = {}
    for caminho in fontes:
        base = caminho.rsplit("/", 1)[-1][:-3] if caminho.endswith(".py") else None
        if base:
            por_nome.setdefault(base, caminho)
            if caminho.startswith("scripts/"):
                por_nome.setdefault("scripts." + base, caminho)
    contagem = {c: 0 for c in fontes}
    for caminho, fonte in fontes.items():
        try:
            arvore = ast.parse(fonte or "")
        except (SyntaxError, ValueError):
            continue
        alcanca = set()
        for no in ast.walk(arvore):
            nomes = []
            if isinstance(no, ast.Import):
                nomes = [a.name for a in no.names]
            elif isinstance(no, ast.ImportFrom) and no.module and not no.level:
                nomes = [no.module]
            for n in nomes:
                destino = por_nome.get(n) or por_nome.get(n.split(".")[0])
                if destino and destino != caminho:
                    alcanca.add(destino)
        for d in alcanca:
            contagem[d] = contagem.get(d, 0) + 1
    return contagem


def constantes_de(texto: str) -> set:
    """Nomes de `.json` guardados em CONSTANTE de módulo. Função pura.

    05/10/2026 — O PONTO CEGO QUE A COMPARAÇÃO COM O GRAFO DE DEPENDÊNCIAS ACHOU.
    `RE_SAIDA` só reconhecia três nomes de constante (`SAIDA`, `ARQUIVO`, `DESTINO`) e um literal por
    linha. Quem guarda o nome do dado em qualquer outra constante — ou numa tupla, que é como as
    filas e as listas de arquivo são escritas — ficava invisível para o mapa.

    Medido: **33 arquivos** com dependência de dado que o gerador não via. O pior caso é
    `coletores_base.py`, que tem **169 importadores** e aparecia no mapa sem `log_buscas.json` nem
    `robots_registro.json` — dois dos arquivos mais importantes do projeto. A linha existia; a coluna
    "dados que usa" é que mentia por omissão, e omissão num índice é pior que ausência, porque quem
    o lê acha que já olhou.

    Lê só o nível do módulo, e só constante em MAIÚSCULAS: é o estilo do projeto, e descer em corpo
    de função traria nome calculado, que o mapa não deve afirmar. `ast` em texto que não é Python
    (os `.js` passam por aqui) levanta `SyntaxError`, e aí não há constante a achar.
    """
    fora = set()
    try:
        arvore = ast.parse(texto or "")
    except (SyntaxError, ValueError):
        return fora
    for no in arvore.body:
        if not isinstance(no, ast.Assign):
            continue
        if not any(isinstance(a, ast.Name) and a.id.isupper() for a in no.targets):
            continue
        valores = ([no.value] if isinstance(no.value, ast.Constant)
                   else list(no.value.elts) if isinstance(no.value, (ast.Tuple, ast.List))
                   else [])
        for v in valores:
            if not (isinstance(v, ast.Constant) and isinstance(v.value, str)):
                continue
            nome = v.value
            # `.json` sozinho é a extensão, não um arquivo: entraria como dependência fantasma.
            if nome.endswith(".json") and nome not in (".json",) and not nome.startswith("."):
                fora.add(nome)
    return fora


def dados_de(texto: str) -> set:
    """Os arquivos de `data/` que este código lê ou escreve. Função pura."""
    achados = set()
    for m in RE_FETCH.finditer(texto or ""):
        alvo = m.group(1)
        if alvo.startswith("data/"):
            achados.add(alvo[len("data/"):])
    achados |= set(RE_FETCH_DADO.findall(texto or ""))
    achados |= set(RE_GRAVAR.findall(texto or ""))
    achados |= set(RE_SAIDA.findall(texto or ""))
    achados |= constantes_de(texto)
    if RE_FETCH_MONTADO.search(texto or ""):
        for bloco in RE_LISTA_DE_NOMES.findall(texto or ""):
            for nome in RE_NOME.findall(bloco):
                if not nome.endswith((".html", ".js", ".css", ".png", ".svg", ".pdf")):
                    achados.add(nome if nome.endswith(".json") else nome + ".json")
    # Normaliza o prefixo: o mesmo arquivo aparece como `data/x.json` num padrão e `x.json` noutro,
    # e duas grafias do mesmo dado fariam o mapa listar duas dependências onde há uma.
    return {a[len("data/"):] if a.startswith("data/") else a for a in achados if a}


def paginas_do_portao(texto: str) -> set:
    """As páginas que um portão lista. Função pura."""
    achados = set()
    for bloco in RE_PAGINAS_PORTAO.findall(texto or ""):
        achados |= set(RE_HTML.findall(bloco))
    return achados


def js_da_pagina(html: str) -> set:
    """Os scripts que a página carrega. Função pura."""
    return set(RE_SCRIPT_HTML.findall(html or ""))


def montar(paginas: dict, scripts: dict, pythons: dict, portoes: dict,
           caminhos_js: dict = None, quem_importa: dict = None) -> list:
    """A tabela do mapa, uma linha por arquivo. Função pura — recebe conteúdos, não lê disco."""
    cobertura = {}
    for nome, texto in (portoes or {}).items():
        for pag in paginas_do_portao(texto):
            cobertura.setdefault(pag, set()).add(nome)

    linhas = []
    for pag in sorted(paginas or {}):
        js = js_da_pagina(paginas[pag])
        dados = dados_de(paginas[pag])
        for j in js:
            dados |= dados_de((scripts or {}).get(j, ""))
        linhas.append({"arquivo": pag, "telas": [pag], "js": sorted(js),
                       "dados": sorted(dados), "portoes": sorted(cobertura.get(pag, [])),
                       "indice": "não"})
    # 05/10/2026 — DEFEITO CONSERTADO. Aqui havia uma compreensão sobre lista VAZIA
    # (`for p in []`), com um comentário dizendo que quem lê o disco a preencheria. Ninguém
    # preenchia, então o `get` caía sempre no padrão `assets/js/<nome>` — e três arquivos que vivem
    # em `assets/` apareciam no mapa com um caminho que NÃO EXISTE: `assets/js/acesso.js`,
    # `assets/js/colunas.js` e `assets/js/mapas.js`. Num índice cujo único propósito é dizer "por
    # onde começar a ler", apontar caminho inexistente é o pior defeito possível — e `assets/mapas.js`
    # é um dos dois únicos arquivos do projeto autorizados a carregar cor em hexadecimal.
    # Agora `ler_tudo` passa os caminhos reais do disco, e o padrão só vale no autoteste.
    caminho_js = dict(caminhos_js or {})
    for j in sorted(scripts or {}):
        telas = sorted(p for p, h in (paginas or {}).items() if j in js_da_pagina(h))
        linhas.append({"arquivo": caminho_js.get(j, f"assets/js/{j}"), "telas": telas, "js": [],
                       "dados": sorted(dados_de(scripts[j])),
                       "portoes": sorted({g for t in telas for g in cobertura.get(t, [])}),
                       "indice": "não"})
    for py in sorted(pythons or {}):
        dados = sorted(dados_de(pythons[py]))
        linhas.append({"arquivo": py, "telas": [], "js": [],
                       "dados": dados, "portoes": [],
                       "importado_por": (quem_importa or {}).get(py, 0),
                       "indice": "SIM" if py in TOCA_O_INDICE else "não"})
    return linhas


def como_markdown(linhas: list, gerado_em: str) -> str:
    L = ["# CODEMAP · o que cada arquivo afeta", "",
         "**Gerado por `scripts/gerar_codemap.py` — não editar à mão.** O portão de frescor reprova "
         "se ele estiver desatualizado.", "",
         "Serve a uma pergunta só: **por onde começar a ler** quando um pedido chega. Antes de "
         "explorar o repositório, consulte esta tabela e leia apenas o que ela lista para o que a "
         "tarefa toca.", "",
         "**O que ele não é:** análise de dependência completa. Não segue `import` transitivo nem "
         "chamada dinâmica — é um índice de primeira ordem, tirado dos `fetch(...)`, dos "
         "`gravar(...)` e das listas de páginas dos portões. Para \"por onde começo\", basta; para "
         "\"nada mais pode ser afetado\", quem responde é o portão de runtime.", "",
         "**Regra de página: contrato + componentes** (editoria, 02/10/2026). A forma de uma "
         "página não vive no HTML: vive em `layout/contratos/<pagina>.json`, que declara "
         "seções, ordem, cartões, grades e texto proibido. O HTML e o JavaScript se "
         "conformam ao contrato, e `scripts/verificar_layout.py` reprova a divergência — "
         "nenhum PR de página com contrato é mesclado com ele vermelho. Cartão de "
         "número é `.cartao-numero` em `.grade-numeros--3`; figura é `.cartao-mapa` em "
         "`.grade-figuras--3`; nada de ajuste de pixel por cartão.", "",
         f"Atualizado em {gerado_em}.", "",
         "**A coluna `importado por`** (05/10/2026) diz quantos arquivos do repositório importam aquele — é a resposta curta para \"o que a minha mudança alcança\". Ela não substitui o portão de runtime, mas evita a surpresa: `coletores_base.py` tem 169 importadores, e os dois acidentes de isolamento de 02 e 05/10 custaram 907 atos e seis execuções de log por mexer ali sem ver esse número.", "",
         "| arquivo | telas que afeta | dados que usa | portões que o cobrem | importado por | toca o índice? |",
         "|---|---|---|---|---|---|"]
    for x in linhas:
        telas = ", ".join(x["telas"]) or "—"
        dados = ", ".join(f"`{d}`" for d in x["dados"][:6]) or "—"
        if len(x["dados"]) > 6:
            dados += f" (+{len(x['dados']) - 6})"
        portoes = ", ".join(f"`{p}`" for p in x["portoes"]) or "—"
        imp = x.get("importado_por")
        imp = "—" if not imp else (f"**{imp}**" if imp >= 20 else str(imp))
        L.append(f"| `{x['arquivo']}` | {telas} | {dados} | {portoes} | {imp} | "
                 f"{x['indice']} |")
    L.append("")
    return "\n".join(L)


def ler_tudo() -> tuple:
    paginas = {p.name: p.read_text(encoding="utf-8", errors="replace")
               for p in sorted(RAIZ.glob("*.html"))}
    js_em_disco = sorted(list((RAIZ / "assets" / "js").glob("*.js"))
                         + list((RAIZ / "assets").glob("*.js")))
    scripts = {p.name: p.read_text(encoding="utf-8", errors="replace") for p in js_em_disco}
    # O caminho REAL de cada script, para o mapa não inventar diretório (ver `montar`).
    caminhos_js = {p.name: p.relative_to(RAIZ).as_posix() for p in js_em_disco}
    pythons = {p.name: p.read_text(encoding="utf-8", errors="replace")
               for p in sorted(RAIZ.glob("*.py"))}
    # 05/10/2026 — OS SCRIPTS DE `scripts/` QUE TOCAM `data/` ENTRAM NO MAPA.
    #
    # Até hoje o mapa cobria `*.py` da raiz e `scripts/verificar_*`, e deixava 127 arquivos de
    # `scripts/` de fora. A maioria deles o mapa não teria o que dizer: não leem nem escrevem dado,
    # e as três colunas sairiam vazias. Mas 19 tocam `data/` — e entre eles estava
    # `scripts/pistas.py`, que desde o #555 é a ÚNICA porta da fila de pistas. Um índice que existe
    # para dizer "por onde começar a ler" e que omite a porta da fila está omitindo justamente o
    # ponto de partida.
    #
    # O critério é o que o mapa consegue afirmar: entra quem lê ou escreve `data/`. Isso acrescenta
    # 19 linhas, não 127 — e o mapa é lido em toda sessão, então dobrá-lo com linhas vazias custaria
    # contexto sem dar resposta.
    for q in sorted((RAIZ / "scripts").glob("*.py")):
        if q.name.startswith("verificar_") or q.name == "__init__.py":
            continue                      # portão já entra abaixo; `__init__` não tem conteúdo
        texto = q.read_text(encoding="utf-8", errors="replace")
        if dados_de(texto):
            pythons[q.relative_to(RAIZ).as_posix()] = texto
    portoes = {p.name: p.read_text(encoding="utf-8", errors="replace")
               for p in sorted(list((RAIZ / "scripts").glob("verificar_*.js"))
                               # 01/10/2026: os portões de página em PYTHON também entram. Sem
                               # isto, o portão de âncoras internas — que é o que faz valer a regra
                               # de sincronia entre "Para gestores" e "Financiamento" — não
                               # aparecia na coluna de cobertura de nenhuma das duas páginas, e o
                               # mapa dizia que a regra não existia.
                               + list((RAIZ / "scripts").glob("verificar_*.py")))}
    # A contagem de importadores sai de TODOS os .py versionados, não só dos que o mapa
    # lista: quem importa `coletores_base` conta mesmo que não tenha linha própria.
    todos_py = {q.relative_to(RAIZ).as_posix(): q.read_text(encoding="utf-8",
                                                            errors="replace")
                for q in sorted(RAIZ.rglob("*.py"))
                if not any(x in q.parts for x in ("arquivo", "node_modules", ".git"))}
    quem_importa = importadores(todos_py)
    return paginas, scripts, pythons, portoes, caminhos_js, quem_importa


def autoteste() -> int:
    casos = []
    casos.append(("lê fetch de data/", dados_de("fetch('data/indice.json')") == {"indice.json"}))
    casos.append(("fetch fora de data/ não entra", dados_de("fetch('https://x/y.json')") == set()))
    casos.append(("lê gravar_em com constante",
                  dados_de('gravar_em(RAIZ / "data/cobertura_qd.json", d)') == {"cobertura_qd.json"}))
    casos.append(("lê SAIDA montado por partes",
                  dados_de('SAIDA = RAIZ / "data" / "x.json"') == {"x.json"}))
    casos.append(("o prefixo data/ é normalizado: uma dependência, não duas",
                  dados_de('gravar_em(RAIZ / "data/x.json", d)') == {"x.json"}))
    casos.append(("lê SAIDA em uma string", dados_de('SAIDA = "saude/x.json"') == {"saude/x.json"}))
    casos.append(("código sem dado devolve vazio", dados_de("const a = 1;") == set()))
    montado = ("[BR, PCT] = await Promise.all(['geo_uf','percentual_uf','indice']"
               ".map(f => fetch('data/' + f + '.json')))")
    casos.append(("lê a lista de nomes do fetch montado",
                  dados_de(montado) == {"geo_uf.json", "percentual_uf.json", "indice.json"}))
    casos.append(("lista de nomes SEM o fetch montado não vira dado",
                  dados_de("const ORDEM = ['a','b','c'];") == set()))
    casos.append(("nome já com .json não ganha outra extensão",
                  dados_de("fetch('data/' + f + '.json'); const L=['a.json','b.json','c.json']")
                  == {"a.json", "b.json", "c.json"}))
    casos.append(("página, script e folha não entram como dado",
                  dados_de("fetch('data/' + f + '.json'); const L=['a.html','b.js','c.css']")
                  == set()))
    casos.append(("texto nulo não quebra", dados_de(None) == set()))

    casos.append(("lê a lista de páginas de um portão",
                  paginas_do_portao('const PAGINAS = ["index.html", "saude.html"];')
                  == {"index.html", "saude.html"}))
    casos.append(("lê PADRAO também",
                  paginas_do_portao('const PADRAO = ["a.html"]') == {"a.html"}))
    casos.append(("portão sem lista devolve vazio", paginas_do_portao("const X = 1;") == set()))

    casos.append(("lê o script da página",
                  js_da_pagina('<script src="assets/js/index.js"></script>') == {"index.js"}))
    casos.append(("o cache-busting não esconde o script",
                  js_da_pagina('<script src="assets/js/index.js?v=138f4495"></script>')
                  == {"index.js"}))
    casos.append(("script fora de assets/js também conta",
                  js_da_pagina('<script src="assets/mapas.js?v=1"></script>') == {"mapas.js"}))
    casos.append(("script externo não entra",
                  js_da_pagina('<script src="https://cdn/x.js"></script>') == set()))

    linhas = montar({"index.html": '<script src="assets/js/index.js"></script>'},
                    {"index.js": "fetch('data/indice.json')"},
                    {"recalcular_mare.py": 'gravar("indice.json", x)'},
                    {"verificar_runtime.js": 'const PAGINAS = ["index.html"];'})
    por_arquivo = {x["arquivo"]: x for x in linhas}
    casos.append(("a página herda o dado do script dela",
                  "indice.json" in por_arquivo["index.html"]["dados"]))
    casos.append(("o script aponta a tela que o carrega",
                  por_arquivo["assets/js/index.js"]["telas"] == ["index.html"]))
    casos.append(("o portão que lista a página cobre a página",
                  "verificar_runtime.js" in por_arquivo["index.html"]["portoes"]))
    casos.append(("o portão cobre também o script da página",
                  "verificar_runtime.js" in por_arquivo["assets/js/index.js"]["portoes"]))
    casos.append(("quem mexe no índice é marcado",
                  por_arquivo["recalcular_mare.py"]["indice"] == "SIM"))
    casos.append(("quem não mexe no índice não é marcado",
                  por_arquivo["index.html"]["indice"] == "não"))

    md = como_markdown(linhas, "2026-09-30")
    casos.append(("o markdown diz que é gerado", "não editar à mão" in md))
    casos.append(("e declara o que NÃO é", "análise de dependência completa" in md))
    casos.append(("uma linha por arquivo", md.count("\n| `") == len(linhas)))

    # 05/10/2026 — as travas do PONTO CEGO DA CONSTANTE, achado ao comparar o mapa com o grafo de
    # dependências: 33 arquivos tinham dado em constante que o gerador não via.
    casos.append(("constante escalar com nome de dado é vista",
                  constantes_de('ARQUIVO = "painel_da_noite.json"') == {"painel_da_noite.json"}))
    casos.append(("constante em TUPLA é vista — é como as filas são escritas",
                  constantes_de('FILAS = ("pistas_imprensa.json", "pistas_doe.json")')
                  == {"pistas_imprensa.json", "pistas_doe.json"}))
    casos.append(("constante em LISTA é vista", constantes_de('X = ["a.json"]') == {"a.json"}))
    casos.append(("constante com qualquer NOME é vista, não só SAIDA/ARQUIVO/DESTINO",
                  constantes_de('PAINEL_DA_NOITE = "x.json"') == {"x.json"}))
    casos.append((".json sozinho não entra: é extensão, não arquivo",
                  constantes_de('EXT = ".json"') == set()))
    casos.append(("nome minúsculo não entra: constante do projeto é MAIÚSCULA",
                  constantes_de('arquivo = "x.json"') == set()))
    casos.append(("variável DENTRO de função não entra — nome calculado não se afirma",
                  constantes_de('def f():\n    ARQ = "x.json"') == set()))
    casos.append(("texto que não é Python não quebra (os .js passam por aqui)",
                  constantes_de('const X = "x.json";') == set()))
    casos.append(("o ponto cego fechou: dados_de agora vê a constante",
                  "painel_da_noite.json" in dados_de('ARQUIVO = "painel_da_noite.json"')))

    # 05/10/2026 — as travas da coluna `importado por`.
    fontes = {"a.py": "import coletores_base",
              "b.py": "from coletores_base import ler",
              "c.py": "def f():\n    import coletores_base",
              "d.py": "import json, re",
              "coletores_base.py": "x = 1"}
    cont = importadores(fontes)
    casos.append(("conta `import x` e `from x import y`", cont["coletores_base.py"] == 3))
    casos.append(("conta import DENTRO de função — ele cria dependência igual",
                  "c.py" in fontes and cont["coletores_base.py"] == 3))
    casos.append(("quem ninguém importa fica em zero", cont["a.py"] == 0))
    casos.append(("import da biblioteca padrão não conta", cont.get("d.py") == 0))
    casos.append(("o próprio arquivo não se conta",
                  importadores({"x.py": "import x"})["x.py"] == 0))
    casos.append(("import duplicado no mesmo arquivo conta UMA vez",
                  importadores({"a.py": "import b\nfrom b import c", "b.py": ""})["b.py"] == 1))
    casos.append(("fonte que não é Python não quebra a contagem",
                  importadores({"a.js": "const x = require('b')", "b.py": ""})["b.py"] == 0))
    casos.append(("a coluna sai na tabela, e o hub vem em negrito",
                  "| **99** |" in como_markdown(
                      [{"arquivo": "h.py", "telas": [], "js": [], "dados": [], "portoes": [],
                        "importado_por": 99, "indice": "não"}], "x")))
    casos.append(("quem tem poucos importadores sai sem negrito",
                  "| 3 |" in como_markdown(
                      [{"arquivo": "h.py", "telas": [], "js": [], "dados": [], "portoes": [],
                        "importado_por": 3, "indice": "não"}], "x")))

    # 05/10/2026 — as travas do defeito do caminho inventado. Elas existem porque o mapa apontou
    # `assets/js/mapas.js` durante dias, e esse arquivo nunca existiu: ele vive em `assets/`. A
    # causa era uma compreensão sobre lista vazia, com um comentário dizendo que outro trecho a
    # preencheria; ninguém preenchia, e o padrão errado vencia sempre.
    caminhos = {"acesso.js": "assets/acesso.js", "index.js": "assets/js/index.js"}
    l2 = montar({}, {"acesso.js": "", "index.js": ""}, {}, {}, caminhos_js=caminhos)
    casos.append(("o caminho real do script é respeitado, não inventado",
                  {x["arquivo"] for x in l2} == {"assets/acesso.js", "assets/js/index.js"}))
    casos.append(("sem o mapa de caminhos, o padrão continua servindo ao teste",
                  {x["arquivo"] for x in montar({}, {"index.js": ""}, {}, {})}
                  == {"assets/js/index.js"}))

    # A trava que fecha o caso geral: TODO caminho de script no mapa tem de existir no disco. É
    # barata, e é a que teria pegado o defeito no dia em que ele entrou.
    mapa_em_disco = MAPA.read_text(encoding="utf-8") if MAPA.exists() else ""
    fora_do_disco = [c for c in re.findall(r"^\| `(assets/[^`]+)`", mapa_em_disco, re.M)
                     if not (RAIZ / c).exists()]
    casos.append(("todo caminho de assets/ no mapa existe no disco", not fora_do_disco))
    if fora_do_disco:
        print("    caminhos que o mapa inventou:", ", ".join(fora_do_disco[:5]))

    ruins = [n for n, ok in casos if not ok]
    for n, ok in casos:
        print(f"  {'OK  ' if ok else 'FALHA'} {n}")
    if ruins:
        print(f"X AUTOTESTE DO CODEMAP: {len(ruins)} caso(s) reprovado(s).")
        return 1
    print(f"OK AUTOTESTE — {len(casos)} casos, sem rede e sem escrita.")
    return 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()

    # §193, de novo em 06/10/2026: o carimbo vem do RELOGIO FIXADO da cadeia, nunca
    # do relogio da parede. Com `hoje_editorial`, o mapa mudava sozinho na virada do
    # dia e o portao 12 fechava a publicacao -- nove vezes seguidas na noite de
    # 05 para 06/10, das 23:53 as 06:09.
    from coletores_base import data_do_corte
    paginas, scripts_js, pythons, portoes, caminhos_js, quem_importa = ler_tudo()
    linhas = montar(paginas, scripts_js, pythons, portoes,
                    caminhos_js=caminhos_js, quem_importa=quem_importa)
    novo = como_markdown(linhas, data_do_corte().strftime("%d/%m/%Y"))

    if "--conferir" in sys.argv:
        if not MAPA.exists():
            print("✗ CODEMAP: o mapa não existe. Rode `python3 scripts/gerar_codemap.py`.")
            return 1
        atual = MAPA.read_text(encoding="utf-8")
        # A data muda todo dia e não é o que importa: compara-se a TABELA.
        corpo = lambda t: t[t.index("| arquivo |"):] if "| arquivo |" in t else t  # noqa: E731
        if corpo(atual) != corpo(novo):
            print("✗ CODEMAP desatualizado — rode `python3 scripts/gerar_codemap.py` e commite.")
            return 1
        print(f"✓ CODEMAP OK — {len(linhas)} arquivos mapeados, tabela em dia.")
        return 0

    MAPA.write_text(novo, encoding="utf-8", newline="\n")
    print(f"CODEMAP.md regravado · {len(linhas)} arquivos mapeados")
    return 0


if __name__ == "__main__":
    sys.exit(main())
