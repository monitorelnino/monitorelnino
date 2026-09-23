#!/usr/bin/env python3
"""Blog do MARÉ — gera as páginas dos textos, o índice e o feed a partir de blog/posts/*.md.

Fonte de verdade: um arquivo Markdown por texto em blog/posts/, com cabeçalho
(front matter) de chaves simples::

    ---
    titulo: Título do texto
    data: 2026-09-22
    categoria: analise | diario
    autor: Editoria · Futura Evidence Lab
    resumo: Uma frase.
    ---

Derivados (nunca editados à mão; regenerados pela cadeia canônica — Portão 12):
  · blog/<slug>.html          página de cada texto (masthead, navegação e rodapé copiados de blog.html,
                              com caminhos reescritos para ../ — o mesmo carimbo ?v= das demais páginas)
  · data/blog/posts.json      índice lido por assets/js/blog.js (lista da página blog.html)
  · feeds/blog.xml            feed Atom dos textos (jornalistas e pesquisadores acompanham sem visitar o site)

O slug é o nome do arquivo .md sem a extensão (já começa pela data, o que ordena
o diretório). Sem dependência paga: Markdown (BSD) já está em requirements.txt.

Uso: python3 gerar_blog.py            → escreve os derivados
     python3 gerar_blog.py --check    → só compara (sai com 1 se algum derivado estiver obsoleto)
     python3 gerar_blog.py --autoteste
"""
import datetime as _dt
import json
import os
import re
import sys
import html as _html
from pathlib import Path

import markdown

RAIZ = Path(__file__).resolve().parent
DIR_POSTS = RAIZ / "blog" / "posts"
DIR_SAIDA = RAIZ / "blog"
INDICE = RAIZ / "data" / "blog" / "posts.json"
FEED = RAIZ / "feeds" / "blog.xml"
PAGINA_INDICE = RAIZ / "blog.html"
BASE_URL = "https://monitorelnino.com.br/"
CATEGORIAS = {"analise": "Análise", "diario": "Diário do monitoramento"}
CHAVES_OBRIGATORIAS = ("titulo", "data", "categoria", "autor", "resumo")
SITE = "MARÉ · Monitor de Antecipação e Resposta ao El Niño"


def ler_post(caminho: Path) -> dict:
    texto = caminho.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", texto, re.S)
    if not m:
        raise SystemExit(f"{caminho.name}: sem cabeçalho ---/--- no início do arquivo")
    meta = {}
    for linha in m.group(1).splitlines():
        if not linha.strip():
            continue
        if ":" not in linha:
            raise SystemExit(f"{caminho.name}: linha de cabeçalho sem 'chave: valor' → {linha!r}")
        k, v = linha.split(":", 1)
        meta[k.strip().lower()] = v.strip()
    faltam = [k for k in CHAVES_OBRIGATORIAS if not meta.get(k)]
    if faltam:
        raise SystemExit(f"{caminho.name}: cabeçalho sem {', '.join(faltam)}")
    if meta["categoria"] not in CATEGORIAS:
        raise SystemExit(f"{caminho.name}: categoria {meta['categoria']!r} (use {' | '.join(CATEGORIAS)})")
    try:
        data = _dt.date.fromisoformat(meta["data"])
    except ValueError:
        raise SystemExit(f"{caminho.name}: data {meta['data']!r} fora do formato AAAA-MM-DD")
    slug = caminho.stem
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}-[a-z0-9-]+", slug):
        raise SystemExit(f"{caminho.name}: nome do arquivo deve ser AAAA-MM-DD-slug-em-minusculas.md")
    corpo_md = m.group(2).strip()
    corpo_html = markdown.markdown(corpo_md, extensions=["smarty"], output_format="html5")
    # títulos internos do texto começam em h2 (o h1 da página é o título do texto)
    corpo_html = re.sub(r"<(/?)h1>", r"<\1h2>", corpo_html)
    palavras = len(re.sub(r"<[^>]+>", " ", corpo_html).split())
    return {
        "slug": slug, "titulo": meta["titulo"], "data": data.isoformat(), "data_br": data.strftime("%d/%m/%Y"),
        "categoria": meta["categoria"], "categoria_rotulo": CATEGORIAS[meta["categoria"]], "autor": meta["autor"],
        "resumo": meta["resumo"], "palavras": palavras, "url": f"blog/{slug}.html", "html": corpo_html,
    }


def _bloco(html: str, inicio: str, fim: str) -> str:
    i = html.index(inicio); j = html.index(fim, i) + len(fim)
    return html[i:j]


def _para_subpasta(trecho: str) -> str:
    """Reescreve href/src relativos (assets/, *.html) para valer a partir de blog/."""
    trecho = re.sub(r'(href|src)="(?!https?:|mailto:|#|\.\./|/)([^"]+)"', r'\1="../\2"', trecho)
    return trecho


def render_post(post: dict, cabecalho: str, rodape: str, scripts: str) -> str:
    t = _html.escape(post["titulo"]); desc = _html.escape(post["resumo"])
    url = BASE_URL + post["url"]
    ld = {"@context": "https://schema.org", "@type": "BlogPosting", "headline": post["titulo"], "description": post["resumo"],
          "datePublished": post["data"], "inLanguage": "pt-BR", "url": url,
          "author": {"@type": "Organization", "name": "Futura Evidence Lab"},
          "publisher": {"@type": "Organization", "name": "Futura Evidence Lab", "url": "https://www.futuraevidencelab.com.br/"},
          "isPartOf": {"@type": "Blog", "name": "Blog do MARÉ", "url": BASE_URL + "blog.html"}}
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="description" content="{desc}"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<!-- seo -->
<link rel="canonical" href="{url}">
<meta name="robots" content="noindex, nofollow">
<meta property="og:type" content="article">
<meta property="og:site_name" content="{SITE}">
<meta property="og:locale" content="pt_BR">
<meta property="og:title" content="{t} · Blog do MARÉ">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{BASE_URL}assets/social/card-monitor-el-nino.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{SITE} — como o país se prepara para o ciclo 2026/2027">
<meta property="article:published_time" content="{post['data']}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{t} · Blog do MARÉ">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="{BASE_URL}assets/social/card-monitor-el-nino.png">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
<!-- /seo -->
<link rel="alternate" type="application/atom+xml" title="Blog do MARÉ" href="../feeds/blog.xml">
<title>{t} · Blog do MARÉ</title>
{cabecalho}
<main id="conteudo">
  <article class="panel post" id="post-{post['slug']}">
    <p class="selo">{_html.escape(post['categoria_rotulo'])} · {post['data_br']} · {_html.escape(post['autor'])}</p>
    <h1>{t}</h1>
    <p class="hint post-lede">{desc}</p>
    <div class="post-corpo">
{post['html']}
    </div>
    <p class="post-volta"><a href="../blog.html">Todos os textos</a> · <a href="../feeds/blog.xml">Feed</a></p>
  </article>
</main>
{rodape}
</div>

{scripts}
</body>
</html>
"""


def render_feed(posts: list[dict]) -> str:
    atual = max((p["data"] for p in posts), default=_dt.date.today().isoformat())
    itens = []
    for p in posts:
        itens.append(f"""  <entry>
    <title>{_html.escape(p['titulo'])}</title>
    <link href="{BASE_URL}{p['url']}"/>
    <id>{BASE_URL}{p['url']}</id>
    <updated>{p['data']}T12:00:00-03:00</updated>
    <published>{p['data']}T12:00:00-03:00</published>
    <category term="{p['categoria']}" label="{_html.escape(p['categoria_rotulo'])}"/>
    <author><name>{_html.escape(p['autor'])}</name></author>
    <summary>{_html.escape(p['resumo'])}</summary>
    <content type="html">{_html.escape(p['html'])}</content>
  </entry>""")
    return f"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Blog do MARÉ</title>
  <subtitle>Textos da editoria e situação do monitoramento — {SITE}</subtitle>
  <link href="{BASE_URL}feeds/blog.xml" rel="self"/>
  <link href="{BASE_URL}blog.html"/>
  <id>{BASE_URL}feeds/blog.xml</id>
  <updated>{atual}T12:00:00-03:00</updated>
  <author><name>Futura Evidence Lab</name></author>
{chr(10).join(itens)}
</feed>
"""


def gerar() -> dict[Path, str]:
    """Devolve {caminho: conteúdo} de todos os derivados, sem escrever nada."""
    pagina = PAGINA_INDICE.read_text(encoding="utf-8")
    # cabeçalho: do <link preconnect> até o fim do <header> (fontes, acesso.js, folhas, body, skip, .wrap, masthead)
    cabecalho = _para_subpasta(_bloco(pagina, '<link rel="preconnect"', "</header>"))
    rodape = _para_subpasta(_bloco(pagina, '<footer class="site-footer">', "</footer>"))
    scripts = _para_subpasta(_bloco(pagina, '<script src="assets/colunas.js', "</html>")).rsplit("</body>", 1)[0]
    scripts = re.sub(r'<script src="\.\./assets/js/blog\.js[^>]*></script>\n?', "", scripts)   # a página do texto não tem dados a carregar
    posts = sorted((ler_post(p) for p in DIR_POSTS.glob("*.md")), key=lambda p: (p["data"], p["slug"]), reverse=True)
    saida: dict[Path, str] = {}
    for p in posts:
        saida[DIR_SAIDA / f"{p['slug']}.html"] = render_post(p, cabecalho, rodape, scripts)
    indice = {"_governanca": "Índice dos textos do Blog do MARÉ, gerado por gerar_blog.py a partir de blog/posts/*.md. Nunca editado à mão.",
              "categorias": CATEGORIAS,
              "posts": [{k: p[k] for k in ("slug", "titulo", "data", "data_br", "categoria", "categoria_rotulo", "autor", "resumo", "palavras", "url")} for p in posts]}
    saida[INDICE] = json.dumps(indice, ensure_ascii=False, indent=2) + "\n"
    saida[FEED] = render_feed(posts)
    return saida


def main(argv: list[str]) -> int:
    if "--autoteste" in argv:
        return autoteste()
    saida = gerar()
    if "--check" in argv:
        obsoletos = [str(c.relative_to(RAIZ)) for c, conteudo in saida.items() if not c.exists() or c.read_text(encoding="utf-8") != conteudo]
        sobrando = [str(c.relative_to(RAIZ)) for c in DIR_SAIDA.glob("*.html") if c not in saida]
        if obsoletos or sobrando:
            print("✗ BLOG: derivado obsoleto —", ", ".join(obsoletos + [s + " (sem fonte .md)" for s in sobrando]))
            return 1
        print(f"✓ BLOG OK — {len(saida) - 2} texto(s), índice e feed em dia.")
        return 0
    for c in list(DIR_SAIDA.glob("*.html")):
        if c not in saida:
            c.unlink()
    for c, conteudo in saida.items():
        c.parent.mkdir(parents=True, exist_ok=True)
        c.write_text(conteudo, encoding="utf-8", newline="\n")
    print(f"gerar_blog: {len(saida) - 2} texto(s) → blog/, data/blog/posts.json, feeds/blog.xml")
    return 0


def autoteste() -> int:
    import tempfile
    md = "---\ntitulo: Teste <b>\ndata: 2026-01-02\ncategoria: diario\nautor: Editoria\nresumo: Frase.\n---\n\n# Sub\n\nTexto **forte**.\n"
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "2026-01-02-teste.md"; p.write_text(md, encoding="utf-8", newline="\n")
        post = ler_post(p)
        assert post["titulo"] == "Teste <b>" and post["categoria_rotulo"] == CATEGORIAS["diario"]
        assert "<h2>Sub</h2>" in post["html"] and "<h1>" not in post["html"], post["html"]
        assert post["data_br"] == "02/01/2026" and post["url"] == "blog/2026-01-02-teste.html"
        for ruim, msg in [("---\ntitulo: x\n---\n\ncorpo", "sem data"), (md.replace("diario", "outra"), "categoria inválida"), (md.replace("2026-01-02", "02/01/2026"), "data fora do formato")]:
            q = Path(d) / "2026-01-02-ruim.md"; q.write_text(ruim, encoding="utf-8", newline="\n")
            try:
                ler_post(q); raise AssertionError("aceitou " + msg)
            except SystemExit:
                pass
        r = Path(d) / "Ruim_Slug.md"; r.write_text(md, encoding="utf-8", newline="\n")
        try:
            ler_post(r); raise AssertionError("aceitou slug fora do padrão")
        except SystemExit:
            pass
    assert _para_subpasta('<a href="index.html">x</a><link href="assets/a.css?v=1"><a href="https://x/">y</a><a href="#z">w</a>') == \
        '<a href="../index.html">x</a><link href="../assets/a.css?v=1"><a href="https://x/">y</a><a href="#z">w</a>'
    render_post(post, "<body><div class=\"wrap\"><header class=\"masthead\"></header>", "<footer class=\"site-footer\"></footer>", "")
    print("✓ gerar_blog --autoteste OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
