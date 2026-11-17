#!/usr/bin/env python3
"""Gera `mudancas.html` — o registro técnico das mudanças do MARÉ, fora do blog.

Decisão da editoria de 03/10/2026 (regra 2): **o blog é sobre acontecimentos do ciclo**, em prosa.
Os registros técnicos de mudança — que estavam publicados como textos do blog, com título de PR —
saem de lá e vêm para esta página, ligada da metodologia e **sem link no menu**: ela é material de
quem audita, não de quem chega.

A página nasce do `CHANGELOG.md`, que já é o registro canônico. Derivado: não se edita à mão, e a
cadeia de derivados o regenera (portão 12).

USO
    python3 scripts/gerar_mudancas.py
    python3 scripts/gerar_mudancas.py --check
    python3 scripts/gerar_mudancas.py --autoteste
"""
from __future__ import annotations

import html
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
CHANGELOG = RAIZ / "CHANGELOG.md"
SAIDA = RAIZ / "mudancas.html"
MODELO = SAIDA   # 17/11/2026: o blog saiu do site; a página é o próprio modelo (troca só o <main>)
LIMITE_DE_ENTRADAS = 60


def entradas_do_changelog(texto: str, limite: int = LIMITE_DE_ENTRADAS) -> list:
    """[{data, numero, titulo, corpo}] das entradas mais recentes. Função pura.

    O formato é o do projeto desde 02/10/2026: `## AAAA-MM-DD · #PR · título`, com o corpo em
    prosa curta abaixo. Entrada fora desse formato é ignorada — e isso é de propósito: a página
    publica o que o registro canônico declara, não o que ela consegue adivinhar.
    """
    fora = []
    padrao = re.compile(r"^## (\d{4}-\d{2}-\d{2}) · (#\d+) · (.+?)$", re.M)
    achados = list(padrao.finditer(texto or ""))
    for m in achados[:limite]:
        prox = re.search(r"^## ", texto[m.end():], re.M)  # o corpo acaba no próximo título, casado ou não
        corpo = texto[m.end():m.end() + prox.start() if prox else len(texto)].strip()
        fora.append({"data": m.group(1), "numero": m.group(2),
                     "titulo": m.group(3).strip(), "corpo": corpo})
    return fora


def data_br(iso: str) -> str:
    """AAAA-MM-DD → dd/mm/aaaa. Função pura."""
    p = str(iso or "").split("-")
    return f"{p[2]}/{p[1]}/{p[0]}" if len(p) == 3 else str(iso or "")


def corpo_em_html(entradas: list) -> str:
    """O `<main>` da página. Função pura."""
    linhas = ['<main id="conteudo">',
              "  <h1>Mudanças no MARÉ</h1>",
              '  <p class="hint">O registro técnico do que mudou no Monitor: método, verificação, '
              'portões e correções, do mais recente ao mais antigo. A fundamentação de cada '
              'decisão está na metodologia.</p>',
              '  <section id="mudancas" aria-labelledby="mudancasTitulo">',
              '    <h2 id="mudancasTitulo">Registro de mudanças</h2>',
              '    <dl class="mudancas-lista">']
    for e in entradas:
        linhas.append(f'      <dt>{html.escape(data_br(e["data"]))} · '
                      f'{html.escape(e["titulo"])}</dt>')
        corpo = " ".join(e["corpo"].split())
        linhas.append(f'      <dd>{html.escape(corpo)}</dd>')
    linhas += ["    </dl>", "  </section>", "</main>"]
    return "\n".join(linhas)


DESCRICAO = ("O registro técnico do que mudou no Monitor El Niño: método, verificação, portões e "
             "correções.")
LD = ('<script type="application/ld+json">[{"@context": "https://schema.org", "@type": "WebPage", '
      '"name": "Mudanças no MARÉ", "description": "O registro técnico do que mudou no Monitor El '
      'Niño: método, verificação, portões e correções.", "url": '
      '"https://monitorelnino.com.br/mudancas.html", "inLanguage": "pt-BR", "isPartOf": '
      '{"@type": "WebSite", "name": "MARÉ · Monitor de Antecipação e Resposta ao El Niño", "url": '
      '"https://monitorelnino.com.br/", "publisher": {"@type": "Organization", "name": "Futura '
      'Evidence Lab", "url": "https://www.futuraevidencelab.com.br/"}}}]</script>')


def montar(modelo: str, changelog: str) -> str:
    """A página inteira, no esqueleto do site. Função pura."""
    entradas = entradas_do_changelog(changelog)
    # `re.sub` interpreta a SUBSTITUIÇÃO como padrão — e o corpo gerado tem `\d` dentro de texto
    # do changelog, que viraria "bad escape". A troca é por posição, sem passar o conteúdo por regex.
    inicio = modelo.index('<main id="conteudo">')
    fim = modelo.index("</main>", inicio) + len("</main>")
    pagina = modelo[:inicio] + corpo_em_html(entradas) + modelo[fim:]
    pagina = re.sub(r'<meta name="description" content="[^"]*"',
                    f'<meta name="description" content="{DESCRICAO}"', pagina, count=1)
    pagina = re.sub(r'(<meta (?:property="og:description"|name="twitter:description") '
                    r'content=")[^"]*(")', lambda m: m.group(1) + DESCRICAO + m.group(2), pagina)
    pagina = re.sub(r'<script type="application/ld\+json">[\s\S]*?</script>', LD, pagina, count=1)
    # 10/10/2026 (A4-22): o leitor do catálogo veio junto com o modelo e pedia
    # `conteudo/mudancas.json`, que não existe (404 no console). A página não tem texto de catálogo.
    pagina = re.sub(r'<script src="assets/catalogo\.js[^"]*"[^>]*></script>\n?', '', pagina)
    return pagina


def _autoteste() -> int:
    falhas = []
    # O total era um literal e envelhecia calado: dizia cobrir mais casos do que
    # cobre, ou menos. Agora e contado.
    _casos_contados = []

    from _casos import ok_de
    ok = ok_de(falhas, _casos_contados)

    cl = ("# Changelog\n\n## 2026-10-03 · #534 · Título novo\n\nCorpo do 534.\n\n"
          "## 2026-10-02 · #528 · Título antigo\n\nCorpo do 528.\n")
    e = entradas_do_changelog(cl)
    ok("lê as entradas no formato do projeto", len(e) == 2)
    ok("a mais nova vem primeiro", e[0]["numero"] == "#534")
    ok("o corpo é o texto abaixo do título", e[0]["corpo"] == "Corpo do 534.")
    ok("o limite corta", len(entradas_do_changelog(cl, 1)) == 1)
    ok("linha fora do formato é ignorada",
       entradas_do_changelog("## 2026-10-03 sem numero de PR\n") == [])
    ok("entrada fora do formato não entra no corpo da anterior", entradas_do_changelog(
        "## 2026-10-03 · #534 · T\nCorpo.\n## 2026-10-02 · sem PR\nOutro.\n")[0]["corpo"] == "Corpo.")
    ok("data em formato brasileiro", data_br("2026-10-03") == "03/10/2026")
    ok("data vazia não quebra", data_br("") == "")

    h = corpo_em_html(e)
    ok("o corpo tem um item por entrada", h.count("<dt>") == 2)
    ok("o título entra escapado", "Título novo" in h)
    ok("não há cartão na página de mudanças", "cartao" not in h)

    modelo = ('<title>Mudanças no MARÉ</title><meta name="description" content="x">'
              '<meta property="og:description" content="velha">'
              '<script type="application/ld+json">[{"url": "x"}]</script>'
              '<main id="conteudo">velho</main><footer>f</footer>')
    cab = montar(modelo, cl)
    ok("o main é substituído", "velho" not in cab and "Registro de mudanças" in cab)
    ok("o rodapé do modelo é preservado", "<footer>f</footer>" in cab)
    ok("montar a página sobre ela mesma não muda nada", montar(cab, cl) == cab)
    ok("o JSON-LD é o desta página", '"@type": "WebPage"' in cab and '"name": "Mudanças' in cab)
    ok("a descrição social acompanha a da página",
       'og:description" content="' + DESCRICAO + '"' in cab)

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else f"✓ AUTOTESTE OK — {len(_casos_contados)} casos, sem rede.")
    return 1 if falhas else 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return _autoteste()
    pagina = montar(MODELO.read_text(encoding="utf-8"), CHANGELOG.read_text(encoding="utf-8"))
    if "--check" in sys.argv:
        atual = SAIDA.read_text(encoding="utf-8") if SAIDA.exists() else ""
        if atual != pagina:
            print("✗ mudancas.html está obsoleto — rode python3 scripts/gerar_mudancas.py")
            return 1
        print("✓ mudancas.html em dia")
        return 0
    SAIDA.write_text(pagina, encoding="utf-8", newline="\n")
    print(f"→ mudancas.html gerado com {len(entradas_do_changelog(CHANGELOG.read_text(encoding='utf-8')))} entrada(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
