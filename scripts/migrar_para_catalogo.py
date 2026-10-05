#!/usr/bin/env python3
"""
scripts/migrar_para_catalogo.py — tira o texto público da página e o põe no catálogo
====================================================================================
Item 1.3 e 1.4 do `HANDOVER_catalogo_de_conteudo_05-10-2026.md`.

A EXIGÊNCIA QUE DESENHA ESTE SCRIPT. O handover pede migração **sem mudar uma vírgula**: antes e
depois, o texto visível tem de ser idêntico, e diferença faz o PR não fechar. Um humano (ou um
modelo) copiando texto à mão para um JSON erra uma acentuação a cada cem linhas, e o erro aparece
no site, não no diff.

Então a migração é **mecânica**: este script LÊ o texto que está na página hoje, grava-o no catálogo
sem tocar num caractere, e reescreve o elemento com `data-conteudo="<id>"`. O leitor
(`assets/catalogo.js`) devolve exatamente o que foi lido. A igualdade é por construção, e o portão
a confere depois de renderizar.

O QUE MIGRA, E O QUE NÃO
------------------------
Migra o texto **estático** que o leitor encontra: `h2` de seção, `p.hint`, `.cartao-mapa-familia`,
`h3.figura-titulo`, `p.figura-sub`, `summary`, `.card-body` e `p.note` com prosa.

NÃO migra:
  · o que o JS preenche a partir do dado (`—` nos elementos com `id`) — isso é a camada de DADO, e
    o handover separa as três de propósito. O molde dessas frases entra no catálogo por outro
    caminho (`moldes`), com `{chave}`, quando a frase é frase;
  · atributo técnico (`aria-label`, `alt`, `class`, `id`) — não é texto público editorial, e
    arrastá-lo para o catálogo misturaria acessibilidade com conteúdo;
  · `<script>`, `<style>` e o `<head>`.

O IDENTIFICADOR é `pagina.secao.elemento[.funcao]`, estável, derivado da estrutura que o contrato
de layout já declara (`layout/contratos/<pagina>.json`): a seção vem do `id` da `<section>`, o
elemento vem do `id` da figura/cartão (sem o prefixo `box`), e a função vem da classe.

USO
    python3 scripts/migrar_para_catalogo.py --pagina financiamento --conferir   # só relata
    python3 scripts/migrar_para_catalogo.py --pagina financiamento --aplicar    # grava
    python3 scripts/migrar_para_catalogo.py --autoteste
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
CATALOGO = RAIZ / "conteudo"

# classe (ou tag) -> função no catálogo. A ordem importa: a primeira que casar vence.
FUNCOES = (
    ("cartao-mapa-familia", "familia"),
    ("cartao-numero-familia", "familia"),
    ("figura-titulo", "titulo"),
    ("figura-sub", "legenda"),
    ("cartao-numero-rotulo", "rotulo"),
    ("cartao-numero-fonte", "fonte"),
    ("hint", "abertura"),
    ("card-body", "prosa"),
    ("note", "nota"),
    ("escala", "escala"),
)

# O que o JS preenche: elemento cujo texto é só o travessão de espera.
ESPERA = ("—", "-", "")


def funcao_de(classes: str, tag: str) -> str:
    """A função do elemento no catálogo, pela classe. Função pura."""
    for marca, nome in FUNCOES:
        if marca in (classes or "").split():
            return nome
    if tag == "h2":
        return "titulo_da_secao"
    if tag == "h3":
        return "titulo"
    if tag == "summary":
        return "resumo"
    return "texto"


def identificador(pagina: str, secao: str, elemento: str, funcao: str, ordem: int = 0) -> str:
    """`pagina.secao.elemento.funcao`, estável. Função pura.

    `ordem` entra só quando o mesmo trio se repete na mesma seção — e entra como sufixo, não no
    meio, para que o identificador de quem já existe NUNCA mude quando um irmão é acrescentado.
    Identificador que muda quebra link de edição antiga, e é por isso que
    `conteudo/_renomeacoes.json` existe.
    """
    partes = [pagina, secao]
    if elemento:
        partes.append(elemento)
    partes.append(funcao)
    base = ".".join(p for p in partes if p)
    return f"{base}_{ordem + 1}" if ordem else base


def nome_do_elemento(id_html: str) -> str:
    """O nome do elemento no catálogo, tirado do `id` do HTML. Função pura.

    `boxFormaAplicacao` -> `forma_aplicacao`. O prefixo `box` é convenção de marcação, não parte do
    nome do conteúdo, e carregá-lo para o catálogo amarraria o identificador à implementação.
    """
    s = re.sub(r"^box", "", id_html or "")
    # Duas passadas, para a SIGLA não virar letra por letra: `boxRespostaUF` tem de dar
    # `resposta_uf`, não `resposta_u_f`. A primeira separa palavra iniciada por maiúscula; a
    # segunda separa a fronteira minúscula→maiúscula, que é onde a sigla começa.
    s = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", s)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s).lower()
    return re.sub(r"[^a-z0-9_]+", "_", s).strip("_")


def texto_limpo(bruto: str) -> str:
    """O texto como o leitor o vê: espaço normalizado, entidade preservada. Função pura.

    O HTML quebra linha para caber na coluna de 100 caracteres, e o navegador colapsa esse espaço.
    O catálogo guarda o que o leitor LÊ, então colapsa também — senão o JSON traria a quebra de
    linha do arquivo-fonte como se fosse conteúdo.
    """
    return re.sub(r"\s+", " ", bruto or "").strip()


def extrair(html: str, pagina: str) -> tuple:
    """(entradas, html_novo) — o catálogo e a página com `data-conteudo`. Função pura.

    `entradas` é {identificador: texto}. `html_novo` é o mesmo HTML com o atributo acrescentado nos
    elementos migrados, e nada mais mudado: nem ordem, nem espaço, nem classe.
    """
    if "<main" not in html:
        return {}, html
    ini, fim = html.index("<main"), html.rindex("</main>")
    cabeca, corpo, pe = html[:ini], html[ini:fim], html[fim:]

    # Onde cada seção começa, para dar contexto a cada elemento.
    limites = [(m.start(), m.group(1)) for m in re.finditer(r'<section[^>]*id="([\w-]+)"', corpo)]

    def secao_em(pos: int) -> str:
        atual = ""
        for inicio, nome in limites:
            if inicio <= pos:
                atual = nome
            else:
                break
        return atual

    # O CARTÃO que contém a posição, para nomear o elemento. Só `figure` e `div` de cartão contam:
    # o `div.map-legend` fica DENTRO da figura e vinha depois dela, de modo que o `summary` do
    # "Ver em lista" era nomeado pela legenda de categorias (`leg_forma_aplicacao`) em vez de pela
    # figura. Contexto de conteúdo é o cartão, não o último elemento com `id` que passou.
    CARTAO = re.compile(r'<(figure|div)([^>]*)>')
    cartoes = []
    for m in CARTAO.finditer(corpo):
        attrs = m.group(2)
        classes = (re.search(r'class="([^"]*)"', attrs) or [None, ""])[1] or ""
        if not (m.group(1) == "figure" or any(c.startswith("cartao") for c in classes.split())):
            continue
        nome = (re.search(r'\bid="([\w-]+)"', attrs) or [None, ""])[1]
        if not nome:
            # 05/10/2026 — CARTÃO SEM `id` é nomeado pelo PRIMEIRO `id` que aparece dentro dele.
            #
            # Na Defesa civil os seis cartões de número são `div.cartao-numero` sem `id`, e só o
            # elemento do valor tem (`topoCemaden`, `topoInmet`, …). Sem esta regra os rótulos
            # viravam `rotulo`, `rotulo_2` … `rotulo_6` — ORDINAIS, que mudam quando a editoria
            # reordena a grade. Identificador que muda quebra o pedido de edição antigo, e é por
            # isso que `conteudo/_renomeacoes.json` existe; melhor não produzir o problema.
            #
            # O `id` do valor é a identidade daquele número, e não muda de lugar.
            dentro = re.search(r'\bid="([\w-]+)"', corpo[m.end():m.end() + 900])
            nome = dentro.group(1) if dentro else ""
        if nome:
            cartoes.append((m.start(), nome))

    def elemento_em(pos: int, id_proprio: str = "", funcao: str = "") -> str:
        """O nome do elemento: o `id` DO PRÓPRIO elemento quando ele tem um, senão o do cartão.

        O `id` próprio é melhor nome: `topoPagoMesRotulo` diz qual cartão de número é aquele, e
        sem ele os três cartões da grade viravam `familia`, `familia_2`, `familia_3` — ordinais
        que mudam se a editoria reordenar a grade, e identificador que muda quebra edição antiga.
        O sufixo da função sai do nome, porque a função já é o último campo do identificador.
        """
        if id_proprio:
            base = re.sub(r"(Rotulo|Fonte|Titulo|Familia|Legenda|Sub|Valor|Variacao)$",
                          "", id_proprio)
            if base:
                return nome_do_elemento(base)
        melhor = ""
        for inicio, nome in cartoes:
            if inicio <= pos:
                melhor = nome
            else:
                break
        return nome_do_elemento(melhor)

    entradas = {}
    usados = {}
    pedacos = []
    ultimo = 0
    alvo = re.compile(r"<(h2|h3|p|summary)([^>]*)>([^<]*)</\1>")
    for m in alvo.finditer(corpo):
        tag, attrs, bruto = m.group(1), m.group(2), m.group(3)
        texto = texto_limpo(bruto)
        if texto in ESPERA or "data-conteudo" in attrs:
            continue
        classes = (re.search(r'class="([^"]*)"', attrs) or [None, ""])[1]
        if "sr-only" in (classes or ""):
            continue                      # texto de leitor de tela é acessibilidade, não conteúdo
        funcao = funcao_de(classes, tag)
        secao = secao_em(m.start())
        id_proprio = (re.search(r'id="([\w-]+)"', attrs) or [None, ""])[1]
        elemento = ("" if funcao in ("titulo_da_secao", "abertura")
                    else elemento_em(m.start(), id_proprio, funcao))
        chave = (secao, elemento, funcao)
        ordem = usados.get(chave, 0)
        usados[chave] = ordem + 1
        ident = identificador(pagina, secao, elemento, funcao, ordem)
        entradas[ident] = texto
        novo_attrs = attrs.rstrip() + f' data-conteudo="{ident}"'
        pedacos.append(corpo[ultimo:m.start()])
        pedacos.append(f"<{tag}{novo_attrs}>{bruto}</{tag}>")
        ultimo = m.end()
    pedacos.append(corpo[ultimo:])
    return entradas, cabeca + "".join(pedacos) + pe


def _autoteste() -> int:
    falhas = []

    def ok(nome, cond):
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    ok("a função sai da classe", funcao_de("figura-titulo", "h3") == "titulo")
    ok("figura-sub é a legenda", funcao_de("figura-sub", "p") == "legenda")
    ok("hint é a abertura", funcao_de("hint", "p") == "abertura")
    ok("h2 sem classe é título de seção", funcao_de("", "h2") == "titulo_da_secao")
    ok("summary é resumo", funcao_de("", "summary") == "resumo")
    ok("o prefixo box sai do nome", nome_do_elemento("boxFormaAplicacao") == "forma_aplicacao")
    ok("camelo vira sublinhado", nome_do_elemento("boxRespostaUF") == "resposta_uf")
    ok("a SIGLA não quebra letra por letra",
       nome_do_elemento("boxGastoProprioUF") == "gasto_proprio_uf")
    ok("id sem box também funciona", nome_do_elemento("antes") == "antes")
    ok("o identificador é pagina.secao.elemento.funcao",
       identificador("financiamento", "dinheiroElNino", "forma_aplicacao", "titulo")
       == "financiamento.dinheiroElNino.forma_aplicacao.titulo")
    ok("sem elemento, o identificador não traz campo vazio",
       identificador("financiamento", "dc-topo", "", "titulo_da_secao")
       == "financiamento.dc-topo.titulo_da_secao")
    ok("o irmão repetido ganha SUFIXO, não muda o primeiro",
       (identificador("p", "s", "e", "f", 0), identificador("p", "s", "e", "f", 1))
       == ("p.s.e.f", "p.s.e.f_2"))
    ok("o espaço do arquivo-fonte colapsa como no navegador",
       texto_limpo("De onde vêm\n      os recursos.") == "De onde vêm os recursos.")

    HTML = ('<html><head><title>x</title></head><body><main>'
            '<section id="s1" aria-labelledby="t"><h2 id="t">Título da seção</h2>'
            '<p class="hint">A abertura\n   em duas linhas.</p>'
            '<p class="note" id="esperando">—</p>'
            '<figure class="cartao-mapa" id="boxUm">'
            '<p class="cartao-mapa-familia">Família</p>'
            '<h3 class="figura-titulo">O título da figura</h3>'
            '<p class="figura-sub">Período · unidade · recorte</p>'
            '<details><summary>Ver em lista</summary></details>'
            '</figure></section></main></body></html>')
    ents, novo = extrair(HTML, "pag")
    ok("extrai o título da seção",
       ents.get("pag.s1.titulo_da_secao") == "Título da seção")
    ok("extrai a abertura com o espaço colapsado",
       ents.get("pag.s1.abertura") == "A abertura em duas linhas.")
    ok("extrai a família da figura", ents.get("pag.s1.um.familia") == "Família")
    ok("extrai o título da figura", ents.get("pag.s1.um.titulo") == "O título da figura")
    ok("extrai a legenda", ents.get("pag.s1.um.legenda") == "Período · unidade · recorte")
    ok("extrai o resumo do details", ents.get("pag.s1.um.resumo") == "Ver em lista")

    # 05/10/2026 — cartão SEM `id`, nomeado pelo `id` do valor que ele contém.
    SEM_ID = ('<main><section id="s"><div class="cartao-numero">'
              '<p class="cartao-numero-rotulo">Municípios sob alerta</p>'
              '<p class="cartao-numero-valor" id="topoCemaden">12</p>'
              '<p class="cartao-numero-fonte" id="topoCemadenFonte">Cemaden</p>'
              '</div></section></main>')
    e2 = extrair(SEM_ID, "dc")[0]
    ok("cartão sem id é nomeado pelo id do valor que ele contém",
       "dc.s.topo_cemaden.rotulo" in e2)
    ok("o sufixo do id do valor não entra no nome",
       not any("topo_cemaden_valor" in k for k in e2))
    ok("o irmão com id próprio usa o SEU id, sem o sufixo da função",
       "dc.s.topo_cemaden.fonte" in e2)
    ok("nenhum identificador ordinal sobrou nos cartões de número",
       not any(k.endswith(("_2", "_3", "_4")) for k in e2))

    ok("NÃO extrai o que o JS preenche (travessão de espera)",
       not any("esperando" in k for k in ents))
    ok("o número de entradas é o esperado", len(ents) == 6)

    ok("a página ganha data-conteudo em cada migrado",
       novo.count("data-conteudo=") == len(ents))
    ok("o texto do HTML NÃO muda — só o atributo entra",
       "O título da figura</h3>" in novo and "Período · unidade · recorte</p>" in novo)
    ok("a quebra de linha do fonte fica intacta no HTML",
       "A abertura\n   em duas linhas." in novo)
    ok("o cabeçalho e o pé não são tocados",
       novo.startswith("<html><head><title>x</title>") and novo.endswith("</body></html>"))
    ok("classe e id existentes sobrevivem",
       'class="figura-titulo" data-conteudo=' in novo and 'id="boxUm"' in novo)
    ok("rodar de novo não duplica o atributo",
       extrair(novo, "pag")[1].count("data-conteudo=") == len(ents))
    ok("segunda passada não acha nada novo (idempotente)", extrair(novo, "pag")[0] == {})
    ok("texto de leitor de tela (sr-only) fica fora",
       extrair('<main><section id="s"><h2 class="sr-only">x</h2></section></main>', "p")[0] == {})
    ok("página sem <main> não quebra", extrair("<html></html>", "p") == ({}, "<html></html>"))

    import dis
    nomes = set()
    for n in ("funcao_de", "identificador", "nome_do_elemento", "texto_limpo", "extrair"):
        c = getattr(globals()[n], "__code__", None)
        if c is not None:
            nomes |= {i.argval for i in dis.get_instructions(c) if isinstance(i.argval, str)}
    ok("trava estrutural: as funções puras não leem nem escrevem disco",
       not ({"read_text", "write_text", "open", "gravar"} & nomes))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else "✓ AUTOTESTE OK — 33 casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def main() -> int:
    argv = sys.argv[1:]
    if "--autoteste" in argv:
        return _autoteste()
    if "--pagina" not in argv:
        print("uso: --pagina <nome> [--conferir|--aplicar]")
        return 1
    pagina = argv[argv.index("--pagina") + 1]
    arquivo = RAIZ / f"{pagina}.html"
    if not arquivo.exists():
        print(f"✗ {arquivo.name} não existe")
        return 1
    html = arquivo.read_text(encoding="utf-8")
    entradas, novo = extrair(html, pagina)
    print(f"{pagina}.html · {len(entradas)} identificador(es) de texto público")
    for ident, texto in entradas.items():
        print(f"  {ident}\n      {texto[:92]}")
    if "--aplicar" not in argv:
        print("\n(--conferir: nada foi gravado. Use --aplicar para gravar.)")
        return 0

    CATALOGO.mkdir(exist_ok=True)
    destino = CATALOGO / f"{pagina}.json"
    doc = json.loads(destino.read_text(encoding="utf-8")) if destino.exists() else {}
    doc.setdefault("_governanca", (
        "CATÁLOGO DE CONTEÚDO (handover de 05/10/2026). Todo texto público desta página vive aqui, "
        "com identificador estável `pagina.secao.elemento.funcao`. A página lê este arquivo; o HTML "
        "não contém texto público. Edição pequena passa por `robo-registro/edicoes/*.md` aprovado e "
        "`scripts/aplicar_edicoes.py` — não se edita este arquivo à mão numa rodada de edição. "
        "Mudar identificador exige entrada em `conteudo/_renomeacoes.json`."))
    doc.setdefault("pagina", f"{pagina}.html")
    doc["textos"] = {**(doc.get("textos") or {}), **entradas}
    destino.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n",
                       encoding="utf-8", newline="\n")
    arquivo.write_text(novo, encoding="utf-8", newline="\n")
    print(f"\n✓ gravado: conteudo/{pagina}.json ({len(entradas)} entradas) e {pagina}.html")
    return 0


if __name__ == "__main__":
    sys.exit(main())
