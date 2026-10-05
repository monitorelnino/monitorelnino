#!/usr/bin/env python3
"""
scripts/gerar_indice_de_conteudo.py — o índice do conteúdo, para a editoria apontar
====================================================================================
Item 4 do `HANDOVER_catalogo_de_conteudo_05-10-2026.md`.

PARA QUE SERVE. A editoria precisa de um lugar onde veja, por página, **cada identificador, o texto
atual e a figura a que ele pertence** — é por ele que ela diz "quero mudar este trecho" sem ter de
descrever onde o trecho fica. O identificador é o endereço, e o pedido de edição (`edicoes/*.md`) o
usa como `id`.

ONDE ELE VIVE, e por que isso importa. **Fora do site público.** Ele é material interno: lista
identificador, molde e nome de arquivo, que é exatamente o tipo de coisa que a regra editorial de
03/10 tirou do ar ("dizemos o que disponibilizamos; nunca o que não disponibilizamos" — e nada
sobre código ou base). Por isso:

  · o arquivo gerado é `indice-de-conteudo.html`, na raiz;
  · ele entra em `.gitignore`? **Não** — ele é versionado, para a editoria abri-lo do repositório;
  · mas fica **fora do manifesto público** e **fora da lista de páginas** dos portões de página, e o
    publicador do domínio não o envia. Quem o serve é a prévia, que já é fechada por senha.

Se um dia ele vazar para o domínio, o portão de integridade acusa um arquivo servido fora do
manifesto — que é o sinal certo.

USO
    python3 scripts/gerar_indice_de_conteudo.py
    python3 scripts/gerar_indice_de_conteudo.py --autoteste
"""
from __future__ import annotations

import html as _html
import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
CATALOGO = RAIZ / "conteudo"
SAIDA = RAIZ / "indice-de-conteudo.html"
FUNCOES = ("titulo", "legenda", "familia", "fonte", "nota", "rotulo", "resumo", "abertura",
           "titulo_da_secao", "prosa", "escala", "texto")


def e_molde(texto: str) -> bool:
    """A entrada tem marcador a preencher? Função pura."""
    return bool(re.search(r"\{[^{}]+\}", str(texto or "")))


def exemplo_preenchido(texto: str) -> str:
    """O molde com os marcadores preenchidos por um valor de exemplo. Função pura.

    A editoria precisa ver a FRASE, não o molde: `{n} municípios` não diz se a frase soa bem. O
    exemplo usa 3 para o número e escolhe o ramo de "muitos" no plural, que é o caso comum.
    """
    s = str(texto or "")
    # A MESMA gramática do leitor (`assets/catalogo.js`): o último ramo pode conter `{n}`, e por
    # isso ele NÃO exclui chaves — foi o que esta função errava, deixando o molde de plural inteiro
    # na tela quando o ramo de "muitos" trazia o número.
    # O último ramo aceita `{chave}` dentro, e SÓ isso: com `[^|]*?` ele fechava no `}` do marcador
    # interno e devolvia `{n vários}`; com `[^|]*` guloso ele atravessaria dois moldes na mesma
    # frase. A forma abaixo diz o que de fato é permitido ali.
    s = re.sub(r"\{(\w+)\|([^|{}]*)\|([^|{}]*)\|((?:[^|{}]|\{\w+\})*)\}",
               lambda m: m.group(4).replace("{" + m.group(1) + "}", "3"), s)
    return re.sub(r"\{(\w+)\}", "3", s)


def agrupar(textos: dict) -> list:
    """[(secao, elemento, [(funcao, id, texto)])] na ordem do catálogo. Função pura."""
    grupos, ordem = {}, []
    for ident, texto in (textos or {}).items():
        pedacos = [p for p in ident.split(".") if p]
        funcao = ""
        if len(pedacos) > 2 and re.sub(r"_\d+$", "", pedacos[-1]) in FUNCOES:
            funcao = pedacos.pop()
        elif len(pedacos) > 1 and re.sub(r"_\d+$", "", pedacos[-1]) in FUNCOES:
            funcao = pedacos.pop()
        secao = pedacos[1] if len(pedacos) > 1 else ""
        elemento = ".".join(pedacos[2:]) if len(pedacos) > 2 else ""
        chave = (secao, elemento)
        if chave not in grupos:
            grupos[chave] = []
            ordem.append(chave)
        grupos[chave].append((funcao or "texto", ident, texto))
    return [(s, e, grupos[(s, e)]) for s, e in ordem]


def como_html(paginas: dict) -> str:
    """O índice inteiro. Função pura — recebe {pagina: catalogo}."""
    E = _html.escape
    L = ["<!doctype html><html lang=\"pt-BR\"><head><meta charset=\"utf-8\">",
         "<meta name=\"robots\" content=\"noindex, nofollow\">",
         "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">",
         "<title>Índice de conteúdo · MARÉ (interno)</title>",
         "<style>",
         "body{font-family:system-ui,sans-serif;max-width:60rem;margin:2rem auto;padding:0 1rem;",
         "line-height:1.5;color:#1b1b1b}",
         # 05/10/2026 — A ESCALA TIPOGRÁFICA VALE AQUI TAMBÉM, e o portão 18 reprovou por isso.
         # `1.8rem` computa 28,8 px, `.92rem` dá 14,72, `.82rem` dá 13,12 — todos FORA da escala
         # fixa do projeto (12 · 14 · 16 · 18 · 22 · 28 · 36 · 48). Esta página é interna e não
         # carrega `assets/tokens.css`, então os valores entram em px literal, da própria escala:
         # é o único jeito de uma página autônoma respeitá-la, e o portão confere o computado.
         # Mesmo critério das outras duas correções desta série: interna fica fora do SEO, porque
         # metadado de compartilhamento não faz sentido nela; não fica fora de design nem de
         # acessibilidade, porque quem lê é uma pessoa.
         "h1{font-weight:300;font-size:28px} h2{font-weight:300;font-size:22px;margin-top:2.5rem}",
         "h3{font-weight:400;font-size:16px;margin:1.5rem 0 .4rem;color:#444}",
         "h2 small{font-size:14px}",
         ".aviso{background:#f6f3ec;border-left:3px solid #7C4A34;padding:.8rem 1rem;margin:1rem 0}",
         # `table-layout:fixed` + quebra em qualquer ponto: sem isso o identificador longo
         # (`financiamento.dinheiroElNino.forma_aplicacao.legenda`) força a tabela a 403 px e a
         # página ganha rolagem horizontal a 390 px — o portão móvel reprovou exatamente isso.
         # Esta página é interna, mas a régua de acessibilidade não é só do público: a editoria
         # também a lê no celular, e rolagem lateral em tabela é onde a leitura se perde.
         "table{border-collapse:collapse;width:100%;table-layout:fixed;margin:.4rem 0 1.2rem}",
         "td,th{border-bottom:1px solid #e3e3e3;padding:.45rem .5rem;vertical-align:top;",
         "font-size:14px;text-align:left;overflow-wrap:anywhere;word-break:break-word}",
         "th{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:#666}",
         "th:first-child{width:5.5rem}",
         "code{font-family:ui-monospace,monospace;font-size:12px;color:#5E7C93;",
         "overflow-wrap:anywhere}",
         "@media (max-width:28rem){body{padding:0 .6rem}td,th{padding:.4rem .25rem;",
         "font-size:12px}th:first-child{width:4rem}}",
         ".molde{color:#7C4A34} .ex{color:#666;font-style:italic}",
         "</style></head><body>",
         "<h1>Índice de conteúdo</h1>",
         "<div class=\"aviso\"><strong>Material interno.</strong> Esta página não vai ao domínio "
         "público: ela lista identificadores e moldes, que são o avesso do site. Serve para a "
         "editoria apontar o trecho que quer mudar, pelo <strong>identificador</strong>, num pedido "
         "em <code>robo-registro/edicoes/AAAA-MM-DD-&lt;id&gt;.md</code>.</div>",
         "<p>Gerado por <code>scripts/gerar_indice_de_conteudo.py</code> — não editar à mão. "
         "Para ver a figura de um identificador: "
         "<code>python3 scripts/renderizar_figura.py &lt;identificador&gt;</code>.</p>"]

    for pagina in sorted(paginas):
        textos = (paginas[pagina] or {}).get("textos") or {}
        L.append(f"<h2>{E(pagina)} <small>({len(textos)} trechos)</small></h2>")
        for secao, elemento, itens in agrupar(textos):
            rotulo = f"{secao}" + (f" · {elemento}" if elemento else "")
            L.append(f"<h3>{E(rotulo or 'página')}</h3>")
            L.append("<table><tr><th>função</th><th>identificador</th><th>texto atual</th></tr>")
            for funcao, ident, texto in itens:
                celula = E(str(texto))
                if e_molde(texto):
                    celula = (f"<span class=\"molde\">{E(str(texto))}</span><br>"
                              f"<span class=\"ex\">exemplo: {E(exemplo_preenchido(texto))}</span>")
                L.append(f"<tr><td>{E(funcao)}</td><td><code>{E(ident)}</code></td>"
                         f"<td>{celula}</td></tr>")
            L.append("</table>")
    L.append("</body></html>")
    return "\n".join(L) + "\n"


def _autoteste() -> int:
    falhas = []

    def ok(nome, cond):
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    ok("molde é reconhecido", e_molde("são {n} municípios"))
    ok("texto simples não é molde", not e_molde("são três municípios"))
    ok("o exemplo preenche o marcador", exemplo_preenchido("são {n} municípios")
       == "são 3 municípios")
    ok("o exemplo escolhe o ramo de muitos",
       exemplo_preenchido("{n|nenhum|um|{n} vários}") == "3 vários")
    ok("texto sem molde passa inteiro", exemplo_preenchido("frase") == "frase")

    T = {"p.s1.um.titulo": "T", "p.s1.um.legenda": "L", "p.s1.titulo_da_secao": "S",
         "p.s2.dois.familia": "F"}
    g = agrupar(T)
    ok("agrupa por seção e elemento", [(s, e) for s, e, _ in g]
       == [("s1", "um"), ("s1", ""), ("s2", "dois")])
    ok("o grupo traz as funções do cartão", [f for f, _i, _t in g[0][2]] == ["titulo", "legenda"])
    ok("catálogo vazio não quebra", agrupar({}) == [])

    h = como_html({"financiamento": {"textos": {"financiamento.s.e.legenda": "Uma legenda"}}})
    ok("o HTML traz o identificador", "financiamento.s.e.legenda" in h)
    ok("o HTML traz o texto", "Uma legenda" in h)
    ok("o HTML é noindex — material interno não se indexa", 'content="noindex, nofollow"' in h)
    ok("o HTML diz que é interno e como pedir edição",
       "Material interno" in h and "robo-registro/edicoes/" in h)
    ok("texto com < e & sai escapado",
       "&lt;b&gt;" in como_html({"p": {"textos": {"p.s.e.texto": "<b>&"}}}))
    ok("molde aparece com o exemplo ao lado",
       "exemplo: 3 municípios" in como_html({"p": {"textos": {"p.s.e.t": "{n} municípios"}}}))

    import dis
    nomes = set()
    for n in ("e_molde", "exemplo_preenchido", "agrupar", "como_html"):
        c = getattr(globals()[n], "__code__", None)
        if c is not None:
            nomes |= {i.argval for i in dis.get_instructions(c) if isinstance(i.argval, str)}
    ok("trava estrutural: as funções puras não leem disco nem escrevem",
       not ({"read_text", "write_text", "open"} & nomes))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else "✓ AUTOTESTE OK — 15 casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def main() -> int:
    if "--autoteste" in sys.argv[1:]:
        return _autoteste()
    paginas = {}
    if CATALOGO.exists():
        for arq in sorted(CATALOGO.glob("*.json")):
            if arq.name.startswith("_"):
                continue
            paginas[arq.stem] = json.loads(arq.read_text(encoding="utf-8"))
    SAIDA.write_text(como_html(paginas), encoding="utf-8", newline="\n")
    trechos = sum(len((p.get("textos") or {})) for p in paginas.values())
    print(f"✓ índice de conteúdo: {len(paginas)} página(s), {trechos} trecho(s) → "
          f"{SAIDA.name} (interno, noindex, fora do domínio público)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
