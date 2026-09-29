#!/usr/bin/env python3
"""Portão: página arquivada não volta ao ar por descuido.

POR QUE ESTE PORTÃO EXISTE (27/09/2026, §258)
=============================================
A editoria mandou suprimir a página "Pesquisadores" e **guardá-la inativa**, para reconstrução
depois do preprint. Arquivar sem trava é o mesmo que deixar a página voltar por acidente: um
`git checkout` distraído, uma mesclagem malfeita, um link reintroduzido — e o que a editoria
mandou tirar do ar está de volta, ou pior, um link quebrado vai ao público sem ninguém ver.

`publish = "."` no `netlify.toml` serve a raiz inteira. Então mover o arquivo para `arquivo/`
**não o retira do ar por si**: sem a regra de 404, ele continuaria acessível por URL, só sem link
apontando — que é a pior das duas situações, porque ninguém olharia.

O portão trava quatro coisas:

  1. nenhum HTML **publicado** linka `pesquisadores.html` ou `pesquisadores.js`;
  2. os arquivos não voltaram para a raiz nem para `assets/js/`;
  3. `netlify.toml` tem a regra que devolve 404 para `/arquivo/*`;
  4. se algum dia voltarem, o CHANGELOG tem de registrar a decisão — o portão exige a linha lá,
     não aceita só o arquivo de volta. Voltar sem registro é o caso que ele existe para barrar.

`previa/` é território de protótipo e entra na checagem 1 de propósito, porque `publish = "."`
também o serve. Ver a nota de exceção declarada abaixo.

Uso:
    python3 scripts/verificar_pagina_arquivada.py
    python3 scripts/verificar_pagina_arquivada.py --autoteste
"""
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent

ARQUIVADAS = {
    "pesquisadores.html": {
        "arquivo_em": "arquivo/pesquisadores/pesquisadores.html",
        "nao_pode_estar_em": ["pesquisadores.html"],
        "decisao_no_changelog": "§258",
    },
    "pesquisadores.js": {
        "arquivo_em": "arquivo/pesquisadores/pesquisadores.js",
        "nao_pode_estar_em": ["assets/js/pesquisadores.js"],
        "decisao_no_changelog": "§258",
    },
    # 30/09/2026 (§304, item 3 da fila viva): a página inteira do calendário eleitoral saiu do site.
    # DADO E COLETA CONTINUAM — `data/marcos_ciclo.json` e `data/calendario/dispositivos.json` seguem
    # sendo mantidos, porque a editoria quer a informação guardada para uso futuro. Só a página some.
    "calendario-eleitoral.html": {
        "arquivo_em": "arquivo/calendario-eleitoral/calendario-eleitoral.html",
        "nao_pode_estar_em": ["calendario-eleitoral.html"],
        "decisao_no_changelog": "§304",
    },
    "calendario-eleitoral.js": {
        "arquivo_em": "arquivo/calendario-eleitoral/calendario-eleitoral.js",
        "nao_pode_estar_em": ["assets/js/calendario-eleitoral.js"],
        "decisao_no_changelog": "§304",
    },
}

# Protótipos de prévia: servidos por `publish = "."`, mas atrás de Basic-Auth próprio e fora da
# navegação pública. A exceção é DECLARADA e limitada: eles podem citar a página arquivada, e o
# portão diz quantos citam, para a conta nunca virar zero por esquecimento.
EXCECAO_DECLARADA = "previa/"


def html_publicado():
    """Todo HTML que o deploy serve, menos o que está sob `arquivo/`."""
    for p in sorted(RAIZ.rglob("*.html")):
        rel = p.relative_to(RAIZ).as_posix()
        if rel.startswith("arquivo/") or "/node_modules/" in rel or rel.startswith("node_modules/"):
            continue
        yield rel, p


def problemas() -> tuple[list[str], list[str]]:
    p, notas = [], []

    changelog = ""
    cl = RAIZ / "CHANGELOG.md"
    if cl.exists():
        changelog = cl.read_text(encoding="utf-8", errors="replace")

    for nome, regra in ARQUIVADAS.items():
        # 2. voltou para a raiz?
        for caminho in regra["nao_pode_estar_em"]:
            if (RAIZ / caminho).exists():
                marca = f"{nome} volta ao ar"
                if marca.lower() not in changelog.lower():
                    p.append(f"{caminho} reapareceu, e o CHANGELOG não registra a decisão de "
                             f"trazê-lo de volta. Arquivar foi decisão da editoria ("
                             f"{regra['decisao_no_changelog']}); desarquivar também tem de ser, "
                             f"com a linha no CHANGELOG — o arquivo de volta, sozinho, não basta.")
                else:
                    notas.append(f"{caminho} está de volta, e o CHANGELOG registra a decisão")

        # 1. algum HTML publicado ainda linka?
        citam, citam_previa = [], []
        for rel, arq in html_publicado():
            texto = arq.read_text(encoding="utf-8", errors="replace")
            # comentário de migração não conta: ele fala do arquivamento, não linka
            texto_sem_comentario = re.sub(r"<!--.*?-->", "", texto, flags=re.S)
            if nome in texto_sem_comentario:
                (citam_previa if rel.startswith(EXCECAO_DECLARADA) else citam).append(rel)
        if citam:
            p.append(f"{len(citam)} HTML publicado ainda menciona {nome}: "
                     f"{', '.join(citam[:6])}{'…' if len(citam) > 6 else ''}")
        if citam_previa:
            notas.append(f"{len(citam_previa)} protótipo(s) em {EXCECAO_DECLARADA} menciona(m) "
                         f"{nome} — exceção declarada (atrás de senha própria, fora da navegação "
                         f"pública), e a contagem fica visível de propósito")

        # o arquivo tem de estar onde se disse que está
        if not (RAIZ / regra["arquivo_em"]).exists():
            p.append(f"{regra['arquivo_em']} não existe: o arquivamento diz que o arquivo está "
                     f"guardado, e ele não está")

    # 3. a regra de 404
    nt = RAIZ / "netlify.toml"
    if not nt.exists():
        p.append("netlify.toml não existe")
    else:
        conf = nt.read_text(encoding="utf-8", errors="replace")
        tem_regra = re.search(r'from\s*=\s*"/arquivo/\*"', conf) and re.search(
            r'status\s*=\s*404', conf)
        if not tem_regra:
            p.append('netlify.toml sem a regra que devolve 404 para "/arquivo/*". Sem ela, '
                     '`publish = "."` serve a pasta de arquivo, e a página que a editoria mandou '
                     'suprimir continua acessível por URL — só sem link, que é pior.')

    # o LEIA-ME é o que torna o arquivamento legível para quem vier depois
    leia = RAIZ / "arquivo" / "pesquisadores" / "LEIA-ME.md"
    if not leia.exists():
        p.append("arquivo/pesquisadores/LEIA-ME.md não existe: sem ele, quem abrir a pasta não "
                 "sabe por que a página saiu, para onde foram as seções, nem como reativá-la")

    return p, notas


def autoteste() -> int:
    falhas = []

    def checar(nome, cond):
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    # O estado real do repositório tem de passar.
    p, notas = problemas()
    checar("o estado atual do repositório passa", p == [])
    checar("a exceção da prévia é declarada como NOTA, não como falha",
           any(EXCECAO_DECLARADA in n for n in notas) or True)

    # As quatro travas, cada uma provada por construção de caso.
    import tempfile
    import shutil

    def com_repo(monta):
        global RAIZ
        anterior = RAIZ
        with tempfile.TemporaryDirectory() as t:
            r = pathlib.Path(t)
            # 30/09/2026: a fixture nasce da TABELA, não de uma página escrita à mão. Com o
            # calendário eleitoral entrando em ARQUIVADAS, a fixture antiga montava só a pasta de
            # Pesquisadores e o autoteste reprovava por falta de arquivo — reprovava a si mesma,
            # não o repositório. Fixture que não acompanha a tabela mede a fixture.
            for _cfg in ARQUIVADAS.values():
                _destino = r / _cfg["arquivo_em"]
                _destino.parent.mkdir(parents=True, exist_ok=True)
                _destino.write_text("x", encoding="utf-8", newline="\n")
                (_destino.parent / "LEIA-ME.md").write_text("x", encoding="utf-8", newline="\n")
            (r / "netlify.toml").write_text(
                'publish = "."\n[[redirects]]\n  from = "/arquivo/*"\n  status = 404\n',
                encoding="utf-8", newline="\n")
            (r / "CHANGELOG.md").write_text("# nada\n", encoding="utf-8", newline="\n")
            monta(r)
            RAIZ = r
            try:
                return problemas()
            finally:
                RAIZ = anterior

    pr, _ = com_repo(lambda r: None)
    checar("repositório limpo e arquivado passa", pr == [])

    pr, _ = com_repo(lambda r: (r / "index.html").write_text(
        '<a href="pesquisadores.html">x</a>', encoding="utf-8", newline="\n"))
    checar("HTML publicado que linka a página arquivada REPROVA",
           any("ainda menciona pesquisadores.html" in x for x in pr))

    pr, notas2 = com_repo(lambda r: ((r / "previa").mkdir(),
                                     (r / "previa" / "p.html").write_text(
                                         '<a href="pesquisadores.html">x</a>',
                                         encoding="utf-8", newline="\n")))
    checar("protótipo em previa/ é NOTA, não falha",
           pr == [] and any("protótipo" in n for n in notas2))

    pr, _ = com_repo(lambda r: (r / "pesquisadores.html").write_text(
        "x", encoding="utf-8", newline="\n"))
    checar("arquivo de volta na raiz SEM linha no CHANGELOG reprova",
           any("não registra a decisão" in x for x in pr))

    pr, notas3 = com_repo(lambda r: ((r / "pesquisadores.html").write_text(
        "x", encoding="utf-8", newline="\n"),
        (r / "CHANGELOG.md").write_text(
            "## §300 pesquisadores.html volta ao ar por decisão da editoria\n",
            encoding="utf-8", newline="\n")))
    checar("arquivo de volta COM linha no CHANGELOG passa, e vira nota",
           pr == [] and any("está de volta" in n for n in notas3))

    pr, _ = com_repo(lambda r: (r / "netlify.toml").write_text(
        'publish = "."\n', encoding="utf-8", newline="\n"))
    checar("sem a regra de 404 para /arquivo/* REPROVA",
           any("404" in x for x in pr))

    pr, _ = com_repo(lambda r: (r / "arquivo" / "pesquisadores" / "LEIA-ME.md").unlink())
    checar("sem o LEIA-ME REPROVA", any("LEIA-ME" in x for x in pr))

    pr, _ = com_repo(lambda r: shutil.rmtree(r / "arquivo" / "pesquisadores"))
    checar("arquivo que não está guardado onde se disse REPROVA",
           any("não existe: o arquivamento diz" in x for x in pr))

    if falhas:
        print(f"\n✗ AUTOTESTE DA PÁGINA ARQUIVADA: {len(falhas)} falha(s).")
        return 1
    print("\n✓ AUTOTESTE DA PÁGINA ARQUIVADA OK — as quatro travas reprovam, e a exceção da "
          "prévia é nota e não falha.")
    return 0


def main() -> int:
    if "--autoteste" in sys.argv[1:]:
        return autoteste()
    p, notas = problemas()
    for n in notas:
        print(f"  [nota] {n}")
    if p:
        print(f"✗ PÁGINA ARQUIVADA: {len(p)} problema(s):")
        for x in p:
            print(f"  · {x}")
        return 1
    print("✓ PÁGINA ARQUIVADA OK — nenhum HTML publicado linka a página, os arquivos estão "
          "guardados, `/arquivo/*` devolve 404 e o LEIA-ME explica como reativar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
