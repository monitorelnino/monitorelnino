#!/usr/bin/env python3
"""Blog do MARÉ — gera as páginas dos textos, o índice e o feed a partir de blog/posts/*.md.

Fonte de verdade: um arquivo Markdown por texto em blog/posts/, com cabeçalho
(front matter) de chaves simples::

    ---
    titulo: Título do texto
    data: 2026-09-22
    etiqueta: Legal e financiamento | Saúde | Acontecimento
    abertura: Uma frase.
    fontes: De onde vêm os números.
    aprovado: sim | nao
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
import pathlib
import os
import re
import sys
import html as _html
from pathlib import Path

import markdown
# §227: a data vem da REDAÇÃO, não do runner (que roda em UTC). A rodada de sábado 22h40
# em Brasília já é domingo em UTC, e o carimbo gravado em data/ sairia um dia adiante do que o
# leitor brasileiro viu.
from coletores_base import hoje_editorial  # noqa: E402

RAIZ = Path(__file__).resolve().parent
DIR_POSTS = RAIZ / "blog" / "posts"
DIR_SAIDA = RAIZ / "blog"
INDICE = RAIZ / "data" / "blog" / "posts.json"
FEED = RAIZ / "feeds" / "blog.xml"
PAGINA_INDICE = RAIZ / "blog.html"
BASE_URL = "https://monitorelnino.com.br/"
# 03/10/2026 (regra 2 da editoria): o blog passa a ter DUAS etiquetas, e as duas são sobre o ciclo.
# "Análise" e "Diário do monitoramento" saíram: a primeira convidava a texto de opinião, e a segunda
# era onde os registros técnicos de mudança entravam — eles agora vivem em `mudancas.html`.
# 04/10/2026 (handover da rotina semanal): as etiquetas são as três da rotina. Sai `Boletim`, que
# era a edição numérica semanal — a rotina passa a produzir TEXTO, não edição de números. O
# cabeçalho que a central escreve é `etiqueta: Legal e financiamento` (o rótulo, não um slug), e o
# gerador aceita o rótulo porque é ele que o guia de redação manda escrever.
ETIQUETAS = ("Legal e financiamento", "Saúde", "Acontecimento")
CATEGORIAS = {"legal e financiamento": "Legal e financiamento", "saude": "Saúde",
              "saúde": "Saúde", "acontecimento": "Acontecimento"}
# `Boletim` NÃO entra: o handover de 04/10 a retirou, e não há texto antigo com ela — o único post
# publicado é o de 04/10, com etiqueta Acontecimento. Aceitá-la "por compatibilidade" deixaria a
# etiqueta revogada voltar por hábito, que é o que a lista de etiquetas existe para barrar.
# A central entrega o texto aprovado no repositório privado; o Code publica só o que tiver a marca.
# Nada gerado automaticamente vai ao ar como texto do blog.
DIR_APROVADOS = pathlib.Path(
    os.environ.get("MARE_BLOG_APROVADOS", str(RAIZ.parent / "robo-registro" / "blog")))
MARCA_DE_APROVACAO = "aprovado"
# O cabeçalho do guia de redação da central (04/10/2026): título, abertura de uma frase, etiqueta,
# data, fontes e a marca de aprovação. `autor` e `resumo` saíram porque a central não os escreve —
# o autor é sempre a editoria do MARÉ e o resumo é a `abertura`. `pacote` é exigido pelo
# verificador, não aqui: o texto de 04/10 foi aprovado ANTES de a rotina de pacotes existir, e o
# Code não altera texto aprovado para fazê-lo caber numa regra posterior.
CHAVES_OBRIGATORIAS = ("titulo", "data", "etiqueta", "abertura")
# Sem `aprovado: sim` o texto não vai ao ar — é a trava do fluxo editorial de 03/10/2026.
CHAVES_DE_APROVACAO = ("aprovado",)
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
        v = v.strip()
        # 04/10/2026: o guia da central escreve título e abertura entre aspas, como manda o YAML
        # quando o valor tem dois-pontos. Sem tirar as aspas, elas iam ao ar no título da página e
        # no feed — e foi o que aconteceu com o primeiro texto aprovado.
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        meta[k.strip().lower()] = v
    faltam = [k for k in CHAVES_OBRIGATORIAS if not meta.get(k)]
    if faltam:
        raise SystemExit(f"{caminho.name}: cabeçalho sem {', '.join(faltam)}")
    rotulo = CATEGORIAS.get(str(meta["etiqueta"]).strip().lower())
    if rotulo is None:
        raise SystemExit(f"{caminho.name}: etiqueta {meta['etiqueta']!r} "
                         f"(use {' | '.join(ETIQUETAS)})")
    try:
        data = _dt.date.fromisoformat(meta["data"])
    except ValueError:
        raise SystemExit(f"{caminho.name}: data {meta['data']!r} fora do formato AAAA-MM-DD")
    slug = caminho.stem
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}-[a-z0-9-]+", slug):
        raise SystemExit(f"{caminho.name}: nome do arquivo deve ser AAAA-MM-DD-slug-em-minusculas.md")
    if str(meta.get(MARCA_DE_APROVACAO) or "").strip().lower() not in ("sim", "s", "true"):
        raise SystemExit(f"{caminho.name}: sem `aprovado: sim` no cabeçalho — a editoria aprova "
                         "antes de o texto ir ao ar (regra 2, 03/10/2026)")
    # O `pacote` declarado tem de EXISTIR. Em 05/10/2026 um texto foi para o repositório público
    # sem pacote e sem verificador, e nada reprovou: o cabeçalho citava um pacote, e ninguém
    # conferia se o arquivo citado estava lá. Citar pacote inexistente é pior que não citar —
    # parece conferido. Quando a pasta de pacotes não está ao alcance (a CI não clona o privado),
    # a conferência não acontece, e isso se DIZ em vez de passar calado.
    pacote = str(meta.get("pacote") or "").strip()
    if pacote:
        pasta = DIR_APROVADOS / "pacotes"
        if not pasta.is_dir():
            print(f"  [blog] {caminho.name}: pacote {pacote!r} não conferido — "
                  f"{pasta} fora de alcance nesta árvore")
        elif not (pasta / f"{pacote}.json").exists() and not (pasta / pacote).exists():
            raise SystemExit(f"{caminho.name}: o cabeçalho declara o pacote {pacote!r} e ele não "
                             f"existe em {pasta} — texto do blog só vai ao ar com o pacote da "
                             "semana (regra de 04/10/2026)")
    corpo_md = m.group(2).strip()
    # REGRA 2: texto corrido. Sem tópicos, sem listas, sem cartões no meio do texto — os números
    # vivem nas páginas, e o texto pode citá-los. A verificação é na GERAÇÃO, porque é aqui que o
    # texto se torna página; o portão de conformidade confere depois, no que foi publicado.
    for marca, nome in (("\n- ", "lista com travessão"), ("\n* ", "lista com asterisco"),
                        ("\n1. ", "lista numerada"), ("<ul", "lista em HTML"),
                        ("<ol", "lista em HTML"), ("cartao", "cartão")):
        if marca in corpo_md:
            raise SystemExit(f"{caminho.name}: o corpo tem {nome} — o blog é texto corrido "
                             "(regra 2, 03/10/2026); os números vivem nas páginas do Monitor")
    corpo_html = markdown.markdown(corpo_md, extensions=["smarty"], output_format="html5")
    # títulos internos do texto começam em h2 (o h1 da página é o título do texto)
    corpo_html = re.sub(r"<(/?)h1>", r"<\1h2>", corpo_html)
    palavras = len(re.sub(r"<[^>]+>", " ", corpo_html).split())
    return {
        "slug": slug, "titulo": meta["titulo"], "data": data.isoformat(), "data_br": data.strftime("%d/%m/%Y"),
        "categoria": rotulo, "categoria_rotulo": rotulo,
        "autor": meta.get("autor") or "Editoria do MARÉ",
        "resumo": meta.get("resumo") or meta.get("abertura") or "",
        "palavras": palavras, "url": f"blog/{slug}.html", "html": corpo_html,
        "etiqueta": rotulo, "pacote": meta.get("pacote") or "",
        "endereco_permanente": BASE_URL + f"blog/{slug}.html",
        "fontes": meta.get("fontes") or "",
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
    atual = max((p["data"] for p in posts), default=hoje_editorial().isoformat())
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


def _reprovacao(caminho: Path) -> list:
    """As linhas de reprovação do verificador para um texto, ou [] se ele passa.

    O verificador é `scripts/verificar_texto_blog.py`, e é ele que decide — não há segunda régua
    aqui. Quando ele não pode ser importado, esta função devolve [] e o publicador segue: a
    conferência que falta se declara no portão, não se inventa um juízo paralelo.
    """
    try:
        sys.path.insert(0, str(RAIZ / "scripts"))
        import verificar_texto_blog as v
    except Exception as erro:          # pragma: no cover — ausência do verificador, não do texto
        print(f"  [blog] verificador indisponível ({erro}) — nenhuma conferência de texto feita")
        return []
    meta, corpo = v.ler_cabecalho(caminho.read_text(encoding="utf-8"))
    exige = caminho.name not in v.SEM_PACOTE_POR_DECISAO
    return v.problemas(meta, corpo, v.pacote_de(meta), exige_pacote=exige,
                       pacotes_ao_alcance=v.DIR_PACOTES.is_dir())


def postos_aprovados() -> list:
    """Os arquivos de texto que a editoria aprovou, no repositório privado.

    03/10/2026 (fluxo editorial): a central entrega em `robo-registro/blog/<data>-<slug>.md`, com
    `aprovado: sim`. O Code copia para `blog/posts/` e publica — e **nada mais entra no blog**. A
    pasta local continua sendo a fonte do que é publicado, para que o site se gere sem o privado;
    o que ela não pode é receber texto que não passou pela editoria.
    """
    if not DIR_APROVADOS.exists():
        return []
    novos = []
    for origem in sorted(DIR_APROVADOS.glob("*.md")):
        texto = origem.read_text(encoding="utf-8")
        if not re.search(r"^aprovado:\s*(sim|s|true)\s*$", texto, re.M | re.I):
            print(f"  [blog] {origem.name}: sem `aprovado: sim` — não publicado")
            continue
        # A APROVAÇÃO NÃO DISPENSA O VERIFICADOR, e é aqui que a regra de 04/10/2026 se cumpre:
        # "texto reprovado não vai ao ar e não bloqueia o site". Enquanto esta conferência não
        # estava aqui, o publicador copiava o texto aprovado e o renderizava sem olhar o pacote —
        # e o portão reprovava DEPOIS, no texto já copiado, deixando o site vermelho por causa de
        # um texto que a regra manda apenas não publicar. Reprovado agora fica de fora, com o
        # motivo impresso, e o site segue.
        veredito = _reprovacao(origem)
        if veredito:
            print(f"  [blog] {origem.name}: reprovado pelo verificador — não publicado")
            for linha in veredito:
                print(f"      · {linha}")
            # Cópia anterior sai: um texto que hoje reprova não pode continuar no ar porque
            # passou ontem.
            antiga = DIR_POSTS / origem.name
            if antiga.exists():
                antiga.unlink()
                print(f"      · a cópia em {antiga} foi retirada")
            continue
        # 04/10/2026: a pasta local de posts foi apagada em 03/10, quando o texto
        # antigo saiu — e sem ela a cópia do texto aprovado não tinha onde cair, de
        # modo que o publicador dizia "0 texto(s)" com o texto aprovado na mão.
        DIR_POSTS.mkdir(parents=True, exist_ok=True)
        destino = DIR_POSTS / origem.name
        if not destino.exists() or destino.read_text(encoding="utf-8") != texto:
            destino.write_text(texto, encoding="utf-8", newline="\n")
            novos.append(origem.name)
    if novos:
        print(f"  [blog] {len(novos)} texto(s) aprovado(s) copiado(s) do repositório da editoria: "
              + ", ".join(novos))
    return novos


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
              "posts": [{k: p[k] for k in ("slug", "titulo", "data", "data_br", "categoria", "categoria_rotulo", "autor", "resumo", "palavras", "url", "etiqueta", "endereco_permanente", "fontes")} for p in posts]}
    saida[INDICE] = json.dumps(indice, ensure_ascii=False, indent=2) + "\n"
    saida[FEED] = render_feed(posts)
    return saida


def main(argv: list[str]) -> int:
    if "--autoteste" in argv:
        return autoteste()
    # 04/10/2026: `postos_aprovados()` existia desde 03/10 e NUNCA era chamada — ficou órfã quando
    # o fluxo editorial entrou. O efeito foi exato: com o primeiro texto aprovado pela editoria no
    # repositório privado, o gerador dizia "0 texto(s)". Função que ninguém chama é função que não
    # existe, e esta era a porta inteira do fluxo.
    postos_aprovados()
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
    # 04/10/2026: o cabeçalho é o do guia de redação da central — etiqueta e abertura, não
    # categoria, autor e resumo. A fixture usava o cabeçalho antigo e reprovava o próprio gerador.
    md = ("---\ntitulo: Teste <b>\ndata: 2026-01-02\netiqueta: Acontecimento\n"
          "abertura: Frase.\nfontes: Fonte.\naprovado: sim\n---\n\n# Sub\n\nTexto **forte**.\n")
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "2026-01-02-teste.md"; p.write_text(md, encoding="utf-8", newline="\n")
        post = ler_post(p)
        assert post["titulo"] == "Teste <b>" and post["categoria_rotulo"] == CATEGORIAS["acontecimento"]
        assert post["etiqueta"] == "Acontecimento" and post["endereco_permanente"].endswith(
            "blog/2026-01-02-teste.html")
        assert "<h2>Sub</h2>" in post["html"] and "<h1>" not in post["html"], post["html"]
        assert post["data_br"] == "02/01/2026" and post["url"] == "blog/2026-01-02-teste.html"
        # As recusas que o blog precisa fazer, uma por linha. As quatro últimas são de 03/10/2026:
        # texto sem aprovação da editoria não vai ao ar, e o corpo é prosa — sem listas.
        ruins = [
            ("---\ntitulo: x\n---\n\ncorpo", "sem data"),
            (md.replace("Acontecimento", "Boletim"), "etiqueta inválida"),
            (md.replace("2026-01-02", "02/01/2026"), "data fora do formato"),
            (md.replace("aprovado: sim", "aprovado: nao"), "texto não aprovado"),
            (md.replace("\naprovado: sim", ""), "texto sem marca de aprovação"),
            (md + "\n- item de lista\n", "lista no corpo"),
            (md + "\n1. item numerado\n", "lista numerada no corpo"),
            (md + "\n<ul><li>x</li></ul>\n", "lista em HTML no corpo"),
        ]
        for ruim, msg in ruins:
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
