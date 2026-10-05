#!/usr/bin/env python3
"""
scripts/verificar_catalogo.py — o portão do catálogo de conteúdo
=================================================================
Item 1.5 do `HANDOVER_catalogo_de_conteudo_05-10-2026.md`.

O catálogo tira o texto público do HTML e o põe em `conteudo/<pagina>.json`. Isso só é um ganho se
o texto continuar passando pelas mesmas travas que passava quando estava na página — senão a
migração teria trocado conteúdo verificado por conteúdo solto num JSON.

O QUE ELE REPROVA

  (a) **Identificador referenciado e ausente.** A página pede `data-conteudo="x"` e o catálogo não
      tem `x`. Em produção isso não quebra a página (o leitor deixa o texto de reserva do HTML),
      e é exatamente por isso que precisa de portão: defeito que não aparece é defeito que fica.

  (b) **Vocabulário proibido** dentro de entrada do catálogo, pela mesma lista de
      `layout/regras.json` que o `verificar_conformidade.py` usa na página. Uma lista só.

  (c) **Legenda acima do teto** de `figura.legenda_maxima_caracteres` (180), e **legenda que
      repete o título**, que é a regra §13 da governança.

  (d) **Molde malformado**: marcador aberto e não fechado, ou ramo de plural com número de ramos
      diferente de três. Molde quebrado publica `{n}` para o leitor.

  (e) **Renomeação não registrada.** Identificador que sumiu do catálogo e não está em
      `conteudo/_renomeacoes.json` quebra o link de edição antiga — a editoria aponta um trecho
      pelo identificador, e identificador que muda em silêncio transforma o pedido dela em recusa.

O QUE ELE NÃO FAZ. Não julga o texto editorial: isso é dos portões de legenda, voz e vocabulário
público, que continuam valendo sobre a página RENDERIZADA — e é lá que têm de valer, porque é o
texto renderizado que o leitor encontra. Este portão cuida da integridade do catálogo.

USO
    python3 scripts/verificar_catalogo.py --autoteste
    python3 scripts/verificar_catalogo.py
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
CATALOGO = RAIZ / "conteudo"
REGRAS = RAIZ / "layout" / "regras.json"
RENOMEACOES = CATALOGO / "_renomeacoes.json"

RE_MARCADOR = re.compile(r"\{([^{}|]+)\}")
RE_PLURAL = re.compile(r"\{(\w+)((?:\|[^|{}]*){1,})\}")


def identificadores_da_pagina(html: str) -> set:
    """Os identificadores que a página pede. Função pura."""
    return set(re.findall(r'data-conteudo(?:-html)?="([^"]+)"', html or ""))


def sem_o_leitor(html: str, pedidos: set) -> list:
    """Página que pede identificador e não carrega `assets/catalogo.js`. Função pura.

    Faltava a mais óbvia das conferências, e ela escapou em 05/10/2026 no próprio blog: a migração
    marcou os elementos, este portão conferiu que todo identificador pedido existia, e passou verde
    com a página sem o leitor — de modo que o catálogo não era lido e o que o leitor via era só o
    texto de reserva do HTML. Identificador pedido sem leitor na página não é catálogo: é marcação
    inerte que ninguém resolve.
    """
    if not pedidos:
        return []
    if "assets/catalogo.js" in html:
        return []
    return [f"pede {len(pedidos)} identificador(es) do catálogo e não carrega "
            f"assets/catalogo.js — a página fica com o texto de reserva"]


def ausentes(pedidos: set, catalogo: dict, comum: dict = None) -> list:
    """Os identificadores pedidos e não declarados. Função pura."""
    tem = set(catalogo or {}) | set(comum or {})
    return sorted(p for p in (pedidos or set()) if p not in tem)


def vocabulario_proibido_em(textos: dict, proibidas: list, por_pagina: dict = None,
                            pagina: str = "") -> list:
    """As entradas que trazem palavra proibida. Função pura.

    Casa palavra inteira, sem acento e sem caixa — a mesma régua do portão de conformidade: cobrar
    subcadeia acusaria "subfunção" dentro de "subfunções" e também dentro de palavra inocente.
    """
    import unicodedata

    def normal(s):
        b = unicodedata.normalize("NFKD", str(s or "").lower())
        return "".join(c for c in b if not unicodedata.combining(c))

    lista = list(proibidas or []) + list((por_pagina or {}).get(pagina) or [])
    fora = []
    for ident, texto in sorted((textos or {}).items()):
        alvo = normal(texto)
        for termo in lista:
            t = normal(termo)
            if not t:
                continue
            if re.search(r"(?<![a-z0-9])" + re.escape(t) + r"(?![a-z0-9])", alvo):
                fora.append(f"{ident}: traz {termo!r}, que o site não escreve")
                break
    return fora


def legendas_fora_da_regua(textos: dict, teto: int = 180) -> list:
    """Legenda longa demais, ou que repete o título. Função pura."""
    fora = []
    for ident, texto in sorted((textos or {}).items()):
        if not ident.endswith("legenda") and ".legenda" not in ident:
            continue
        if len(str(texto or "")) > teto:
            fora.append(f"{ident}: {len(texto)} caracteres, acima do teto de {teto}")
        titulo = (textos or {}).get(ident.rsplit(".", 1)[0] + ".titulo")
        if titulo and str(texto or "").strip().lower() == str(titulo).strip().lower():
            fora.append(f"{ident}: repete o título, e a legenda acrescenta — não repete (§13)")
    return fora


def moldes_quebrados(textos: dict) -> list:
    """Molde com marcador aberto, ou plural que não tem três ramos. Função pura."""
    fora = []
    for ident, texto in sorted((textos or {}).items()):
        s = str(texto or "")
        if s.count("{") != s.count("}"):
            fora.append(f"{ident}: marcador aberto e não fechado — o leitor veria a chave crua")
            continue
        for m in RE_PLURAL.finditer(s):
            ramos = m.group(2).split("|")[1:]
            if len(ramos) != 3:
                fora.append(f"{ident}: ramo de plural com {len(ramos)} opção(ões); são três, na "
                            f"ordem zero · um · muitos")
    return fora


def renomeacoes_faltando(antigos: set, atuais: set, registradas: dict) -> list:
    """Identificador que sumiu sem registro de renomeação. Função pura."""
    sumidos = set(antigos or set()) - set(atuais or set())
    registrados = set(registradas or {})
    return sorted(s for s in sumidos if s not in registrados)


def _autoteste() -> int:
    falhas = []
    # O total era um literal e envelhecia calado: dizia cobrir mais casos do que
    # cobre, ou menos. Agora e contado.
    _casos_contados = []

    def ok(nome, cond):
        _casos_contados.append(nome)
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    ok("lê os identificadores que a página pede",
       identificadores_da_pagina('<p data-conteudo="a.b.c">x</p><p data-conteudo-html="d.e">y</p>')
       == {"a.b.c", "d.e"})
    ok("página sem catálogo não pede nada", identificadores_da_pagina("<p>x</p>") == set())
    ok("identificador pedido e ausente é acusado",
       ausentes({"a", "b"}, {"a": "x"}) == ["b"])
    ok("o comum conta como declarado", ausentes({"a"}, {}, {"a": "x"}) == [])

    ok("palavra proibida é acusada",
       any("dados abertos" in x for x in
           vocabulario_proibido_em({"i": "veja os dados abertos"}, ["dados abertos"])))
    ok("acento e caixa não escapam",
       vocabulario_proibido_em({"i": "A SUBFUNÇÃO 182"}, ["subfunção"]) != [])
    ok("palavra dentro de outra NÃO é acusada",
       vocabulario_proibido_em({"i": "subfuncionalidade"}, ["subfunção"]) == [])
    ok("proibição por página se soma à global",
       vocabulario_proibido_em({"i": "chave que abre"}, [], {"f": ["chave que abre"]}, "f") != [])
    ok("texto limpo passa", vocabulario_proibido_em({"i": "A metodologia é pública."},
                                                    ["dados abertos"]) == [])

    ok("legenda acima do teto reprova",
       legendas_fora_da_regua({"p.s.e.legenda": "x" * 181}) != [])
    ok("legenda no teto passa", legendas_fora_da_regua({"p.s.e.legenda": "x" * 180}) == [])
    ok("legenda que repete o título reprova",
       any("repete o título" in x for x in legendas_fora_da_regua(
           {"p.s.e.titulo": "Mesmo texto", "p.s.e.legenda": "mesmo TEXTO"})))
    ok("legenda diferente do título passa",
       legendas_fora_da_regua({"p.s.e.titulo": "A", "p.s.e.legenda": "B"}) == [])
    ok("o que não é legenda fica fora da régua",
       legendas_fora_da_regua({"p.s.e.titulo": "x" * 400}) == [])

    ok("marcador aberto reprova", moldes_quebrados({"i": "são {n municípios"}) != [])
    ok("molde fechado passa", moldes_quebrados({"i": "são {n} municípios"}) == [])
    ok("plural com três ramos passa",
       moldes_quebrados({"i": "{n|nenhum|um|{n} vários}"}) == [])
    ok("plural com dois ramos reprova",
       any("três" in x for x in moldes_quebrados({"i": "{n|nenhum|um}"})))
    ok("texto sem molde passa", moldes_quebrados({"i": "frase simples"}) == [])

    ok("identificador sumido sem registro reprova",
       renomeacoes_faltando({"a", "b"}, {"a"}, {}) == ["b"])
    ok("identificador sumido COM registro passa",
       renomeacoes_faltando({"a", "b"}, {"a"}, {"b": "a"}) == [])
    ok("identificador novo não é sumiço", renomeacoes_faltando({"a"}, {"a", "c"}, {}) == [])

    ok("pagina que pede identificador e nao carrega o leitor reprova",
       sem_o_leitor("<p data-conteudo='x.y'></p>", {"x.y"}) != [])
    ok("pagina com o leitor passa",
       sem_o_leitor("<script src='assets/catalogo.js?v=1'></script>", {"x.y"}) == [])
    ok("pagina que nao pede nada nao precisa do leitor", sem_o_leitor("<p></p>", set()) == [])

    import dis
    nomes = set()
    for n in ("identificadores_da_pagina", "ausentes", "vocabulario_proibido_em",
              "legendas_fora_da_regua", "moldes_quebrados", "renomeacoes_faltando"):
        c = getattr(globals()[n], "__code__", None)
        if c is not None:
            nomes |= {i.argval for i in dis.get_instructions(c) if isinstance(i.argval, str)}
    ok("trava estrutural: as funções puras não leem disco nem escrevem",
       not ({"read_text", "write_text", "open", "gravar"} & nomes))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else f"✓ AUTOTESTE OK — {len(_casos_contados)} casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def main() -> int:
    if "--autoteste" in sys.argv[1:]:
        return _autoteste()
    if not CATALOGO.exists():
        print("✓ CATÁLOGO OK — nenhuma página migrada ainda")
        return 0

    regras = json.loads(REGRAS.read_text(encoding="utf-8")) if REGRAS.exists() else {}
    vocab = regras.get("vocabulario_proibido") or {}
    teto = int(((regras.get("figura") or {}).get("legenda_maxima_caracteres")) or 180)
    comum = {}
    arq_comum = CATALOGO / "_comum.json"
    if arq_comum.exists():
        comum = (json.loads(arq_comum.read_text(encoding="utf-8")) or {}).get("textos") or {}
    registradas = {}
    if RENOMEACOES.exists():
        registradas = (json.loads(RENOMEACOES.read_text(encoding="utf-8")) or {}).get("de_para") or {}

    problemas, paginas, entradas = [], 0, 0
    for arq in sorted(CATALOGO.glob("*.json")):
        if arq.name.startswith("_"):
            continue
        doc = json.loads(arq.read_text(encoding="utf-8"))
        textos = doc.get("textos") or {}
        nome = arq.stem
        paginas += 1
        entradas += len(textos)

        html_arq = RAIZ / f"{nome}.html"
        if html_arq.exists():
            html = html_arq.read_text(encoding="utf-8")
            pedidos = identificadores_da_pagina(html)
            problemas += [f"{nome}: {x} pedido pela página e ausente do catálogo"
                          for x in ausentes(pedidos, textos, comum)]
            problemas += [f"{nome}: {x}" for x in sem_o_leitor(html, pedidos)]

        problemas += [f"{nome}: {x}" for x in vocabulario_proibido_em(
            textos, vocab.get("global") or [], vocab.get("por_pagina") or {},
            f"{nome}.html")]
        problemas += [f"{nome}: {x}" for x in legendas_fora_da_regua(textos, teto)]
        problemas += [f"{nome}: {x}" for x in moldes_quebrados(textos)]

        antigos = set((doc.get("_identificadores_anteriores") or []))
        if antigos:
            problemas += [f"{nome}: {x} sumiu do catálogo sem entrada em conteudo/_renomeacoes.json"
                          for x in renomeacoes_faltando(antigos, set(textos), registradas)]

    if problemas:
        print(f"✗ CATÁLOGO: {len(problemas)} problema(s):")
        for x in problemas[:25]:
            print("   - " + x)
        if len(problemas) > 25:
            print(f"   … e mais {len(problemas) - 25}")
        return 1
    print(f"✓ CATÁLOGO OK — {paginas} página(s) migrada(s), {entradas} entrada(s); todo "
          f"identificador pedido existe, vocabulário limpo, legendas na régua, moldes fechados.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
