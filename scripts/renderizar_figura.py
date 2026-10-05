#!/usr/bin/env python3
"""
scripts/renderizar_figura.py — uma figura de cada vez, por identificador
=========================================================================
Item 3 do `HANDOVER_catalogo_de_conteudo_05-10-2026.md`.

POR QUE UMA DE CADA VEZ. Revisar uma legenda hoje custa uma captura de página inteira: a editoria
recebe 1.400 px de altura para olhar três linhas de texto, e a diferença entre o antes e o depois
fica diluída no resto. O renderizador recorta **o cartão inteiro da figura** — sobretítulo, título,
legenda, a figura, a legenda de categorias e a fonte, que são as quatro funções mais o desenho — e
nada além.

Recorta o CARTÃO, não só o texto, de propósito: a governança editorial trata as quatro funções como
um conjunto, e legenda que cabe mas empurra a figura para fora do cartão é defeito que só aparece
junto. Quem revisa precisa ver o que o leitor vê.

USO
    python3 scripts/renderizar_figura.py financiamento.dinheiroElNino.forma_aplicacao
    python3 scripts/renderizar_figura.py <id> --largura 390
    python3 scripts/renderizar_figura.py --pagina financiamento        # uma imagem por figura
    python3 scripts/renderizar_figura.py --autoteste

O identificador aceito é o do CATÁLOGO, com ou sem a função no fim: `…forma_aplicacao` e
`…forma_aplicacao.legenda` levam ao mesmo cartão, porque o cartão é a unidade de revisão.

As imagens saem em `capturas/figuras/<id>-<largura>.png`, fora do manifesto público.
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
CATALOGO = RAIZ / "conteudo"
SAIDA = RAIZ / "capturas" / "figuras"
FUNCOES = ("titulo", "legenda", "familia", "fonte", "nota", "rotulo", "resumo", "abertura",
           "titulo_da_secao", "prosa", "escala", "texto")


def partes_do_id(ident: str) -> tuple:
    """(pagina, secao, elemento, funcao) — a função é "" quando o identificador é do cartão.

    Função pura. O identificador do catálogo é `pagina.secao.elemento[.funcao]`, e a seção pode
    conter hífen (`dc-topo`), então o corte é por ponto e a função se reconhece pela lista fechada.
    """
    pedacos = [p for p in str(ident or "").split(".") if p]
    if not pedacos:
        return "", "", "", ""
    funcao = ""
    if len(pedacos) > 2 and re.sub(r"_\d+$", "", pedacos[-1]) in FUNCOES:
        funcao = pedacos.pop()
    pagina = pedacos[0] if pedacos else ""
    secao = pedacos[1] if len(pedacos) > 1 else ""
    elemento = ".".join(pedacos[2:]) if len(pedacos) > 2 else ""
    return pagina, secao, elemento, funcao


def seletor_do_cartao(secao: str, elemento: str) -> str:
    """O seletor CSS do cartão que contém o identificador. Função pura.

    Sem elemento, o alvo é a seção — é o caso do título de seção e da abertura, que não vivem
    dentro de cartão nenhum. Com elemento, procura-se o `id` do HTML, que é o nome em camelo com o
    prefixo `box` que a marcação usa; as três formas entram no seletor porque a convenção não é
    perfeitamente uniforme e cobrar uniformidade aqui seria pedir um PR de marcação antes de poder
    renderizar uma legenda.
    """
    if not elemento:
        return f'section[id="{secao}"]'
    camelo = "".join(p.capitalize() if i else p
                     for i, p in enumerate(elemento.split("_")))
    alternativas = [f'#box{camelo[:1].upper()}{camelo[1:]}', f'#{camelo}', f'#{elemento}']
    return ", ".join(alternativas)


def caminho_da_imagem(ident: str, largura: int, saida: pathlib.Path = None) -> pathlib.Path:
    """Onde a imagem daquele identificador fica. Função pura quanto ao disco."""
    seguro = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(ident or "sem-id"))
    return (saida or SAIDA) / f"{seguro}-{largura}.png"


def figuras_da_pagina(catalogo: dict) -> list:
    """Os identificadores de CARTÃO de uma página, um por figura. Função pura.

    Tira a função do identificador e devolve o conjunto, em ordem de aparição: é o que `--pagina`
    renderiza, uma imagem por figura e não uma por linha de texto.
    """
    vistos, fora = set(), []
    for ident in (catalogo or {}).get("textos", {}):
        pagina, secao, elemento, _f = partes_do_id(ident)
        if not elemento:
            continue
        chave = f"{pagina}.{secao}.{elemento}"
        if chave not in vistos:
            vistos.add(chave)
            fora.append(chave)
    return fora


def _autoteste() -> int:
    falhas = []

    def ok(nome, cond):
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    ok("corta a função do fim",
       partes_do_id("financiamento.dinheiroElNino.forma_aplicacao.legenda")
       == ("financiamento", "dinheiroElNino", "forma_aplicacao", "legenda"))
    ok("sem função, o identificador é do cartão",
       partes_do_id("financiamento.dinheiroElNino.forma_aplicacao")
       == ("financiamento", "dinheiroElNino", "forma_aplicacao", ""))
    ok("seção com hífen sobrevive ao corte",
       partes_do_id("financiamento.dc-topo.topo_pago_mes.rotulo")[1] == "dc-topo")
    ok("função com sufixo numérico ainda é função",
       partes_do_id("p.s.e.familia_2")[3] == "familia_2")
    ok("título de seção não tem elemento",
       partes_do_id("financiamento.dinheiroElNino.titulo_da_secao")[2] == "")
    ok("identificador vazio não quebra", partes_do_id("") == ("", "", "", ""))

    ok("o seletor do cartão tenta as três formas do id",
       seletor_do_cartao("s", "forma_aplicacao")
       == "#boxFormaAplicacao, #formaAplicacao, #forma_aplicacao")
    ok("sem elemento, o alvo é a seção",
       seletor_do_cartao("dc-topo", "") == 'section[id="dc-topo"]')

    ok("o nome do arquivo é seguro e traz a largura",
       caminho_da_imagem("a.b.c", 390, pathlib.Path("/x")).name == "a.b.c-390.png")
    ok("caractere estranho no id não vira caminho",
       "/" not in caminho_da_imagem("a/../b", 1280, pathlib.Path("/x")).name)

    cat = {"textos": {
        "p.s1.um.titulo": "x", "p.s1.um.legenda": "y", "p.s1.dois.titulo": "z",
        "p.s1.titulo_da_secao": "w", "p.s2.tres.familia": "v"}}
    ok("uma entrada por FIGURA, não por linha de texto",
       figuras_da_pagina(cat) == ["p.s1.um", "p.s1.dois", "p.s2.tres"])
    ok("o que não está em cartão fica fora", "p.s1.titulo_da_secao" not in figuras_da_pagina(cat))
    ok("catálogo vazio não quebra", figuras_da_pagina({}) == [])

    import dis
    nomes = set()
    for n in ("partes_do_id", "seletor_do_cartao", "caminho_da_imagem", "figuras_da_pagina"):
        c = getattr(globals()[n], "__code__", None)
        if c is not None:
            nomes |= {i.argval for i in dis.get_instructions(c) if isinstance(i.argval, str)}
    ok("trava estrutural: as funções puras não abrem navegador nem escrevem",
       not ({"run", "subprocess", "write_bytes", "mkdir"} & nomes))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else "✓ AUTOTESTE OK — 15 casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def renderizar(idents: list, largura: int) -> int:
    """Chama o renderizador (Playwright, em Node) para cada identificador. ESCREVE imagem."""
    SAIDA.mkdir(parents=True, exist_ok=True)
    pedidos = []
    for ident in idents:
        pagina, secao, elemento, _f = partes_do_id(ident)
        if not pagina:
            print(f"  ✗ {ident}: identificador sem página")
            continue
        pedidos.append({"id": ident, "pagina": f"{pagina}.html",
                        "seletor": seletor_do_cartao(secao, elemento),
                        "saida": str(caminho_da_imagem(ident, largura))})
    if not pedidos:
        return 1
    r = subprocess.run(["node", str(RAIZ / "scripts" / "_recortar_figura.js"),
                        json.dumps({"largura": largura, "pedidos": pedidos}, ensure_ascii=False)],
                       cwd=RAIZ)
    return r.returncode


def main() -> int:
    argv = sys.argv[1:]
    if "--autoteste" in argv:
        return _autoteste()
    largura = int(argv[argv.index("--largura") + 1]) if "--largura" in argv else 1280

    if "--pagina" in argv:
        pagina = argv[argv.index("--pagina") + 1]
        arq = CATALOGO / f"{pagina}.json"
        if not arq.exists():
            print(f"✗ conteudo/{pagina}.json não existe — a página ainda não foi migrada")
            return 1
        idents = figuras_da_pagina(json.loads(arq.read_text(encoding="utf-8")))
        print(f"{pagina}: {len(idents)} figura(s) a {largura} px")
        return renderizar(idents, largura)

    soltos = [a for a in argv if not a.startswith("--")
              and a != str(largura)]
    if not soltos:
        print(__doc__.split("USO")[1].strip())
        return 1
    return renderizar(soltos, largura)


if __name__ == "__main__":
    sys.exit(main())
