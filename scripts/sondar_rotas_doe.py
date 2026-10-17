#!/usr/bin/env python3
"""Sonda os diários oficiais estaduais sem adaptador e REGISTRA o que a fonte respondeu.

Por que existe (02/10/2026): a campanha dos 27 estados do MARÉ Saúde está travada em 22 unidades
por um motivo só — não há rota de busca no diário oficial. Esse diagnóstico vinha sendo refeito à
mão a cada rodada, e à mão ele não acumula: a sondagem de hoje não sabia o que a de ontem já tinha
medido. Este script faz a medição uma vez por rodada quinzenal e escreve o resultado em
`data/fontes_doe.json`, por unidade da federação, com a data e o motivo.

O que ele mede, por UF sem adaptador:

- se a página inicial do diário responde, e com que código;
- se existe **formulário** cuja ação ou cujos campos são de busca (e quais são os campos);
- se existe **link** para uma página de busca;
- se a página declara uma plataforma conhecida (apifront, DOSP, Doem, WordPress, Plone, SEI);
- a recusa, quando houver: bloqueio de acesso real (401, 403, 429, 451) ou muro de robô servido
  com 200 — as duas se respeitam e as duas ficam escritas.

O que ele **não** faz: não executa JavaScript, não tenta adivinhar rota por tentativa cega, não
promove nada a registro e não escreve em nenhum arquivo do banco. Rota encontrada aqui é **pista
de engenharia** — quem decide escrever o adaptador é quem lê o relatório.

Uso:
    python3 scripts/sondar_rotas_doe.py              # sonda e grava o diagnóstico
    python3 scripts/sondar_rotas_doe.py --ensaio     # sonda e só imprime
    python3 scripts/sondar_rotas_doe.py --autoteste  # funções puras, sem rede e sem escrita
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
ARQUIVO = "fontes_doe.json"
# Trava estrutural: este script escreve UM arquivo, o registro de fontes, e nunca o banco.
BANCO_PROIBIDO = {"estados.json", "saude_uf.json", "municipios.json", "indice.json",
                  "monitor_saude.json", "monitor_saude_v04.json"}

ASSINATURAS = (
    ("apifront", re.compile(r"apifront", re.I)),
    ("dosp", re.compile(r"dosp\.com\.br", re.I)),
    ("doem", re.compile(r"doem\.org\.br", re.I)),
    ("plone", re.compile(r"@@busca|plone", re.I)),
    ("wordpress", re.compile(r"/wp-json/|wp-content", re.I)),
    ("sei_publicacoes", re.compile(r"sei/publicacoes|publicacoes/controlador", re.I)),
    ("angular", re.compile(r"<app-root|main\.[0-9a-f]{8,}\.js", re.I)),
)
RE_FORM = re.compile(r"<form[^>]*>.{0,2000}?</form>", re.S | re.I)
RE_ACTION = re.compile(r'action="([^"]*)"', re.I)
RE_METODO = re.compile(r'method="([^"]*)"', re.I)
RE_CAMPO = re.compile(r'<(?:input|select|textarea)[^>]*name="([^"]+)"', re.I)
RE_LINK_BUSCA = re.compile(r'href="([^"]*(?:busca|pesquis|consulta)[^"]*)"', re.I)
RE_PALAVRA_DE_BUSCA = re.compile(r"(busca|pesquis|consulta|palavra|termo|texto)", re.I)
CAMPOS_DE_BUSCA = {"q", "s", "termo", "texto", "palavra", "searchabletext", "search",
                   "search_api_fulltext", "query"}


def plataforma_de(html: str):
    """A primeira assinatura de plataforma que o HTML declara. Função pura."""
    for nome, regra in ASSINATURAS:
        if regra.search(html or ""):
            return nome
    return None


def formularios_de_busca(html: str) -> list:
    """Os formulários cuja ação ou cujos campos são de busca. Função pura.

    O critério é deliberadamente largo — ação com "busca" no caminho, ou um campo com nome de
    termo de busca —, porque falso positivo aqui custa uma leitura humana, e falso negativo custa
    um estado fora da campanha.
    """
    fora = []
    for m in RE_FORM.finditer(html or ""):
        bloco = m.group(0)
        acao = (RE_ACTION.search(bloco) or [None, ""])[1]
        campos = RE_CAMPO.findall(bloco)
        if RE_PALAVRA_DE_BUSCA.search(acao or "") \
           or any(c.lower() in CAMPOS_DE_BUSCA for c in campos) \
           or any(RE_PALAVRA_DE_BUSCA.search(c) for c in campos):
            fora.append({"acao": (acao or "")[:140],
                         "metodo": ((RE_METODO.search(bloco) or [None, "get"])[1] or "get").lower(),
                         "campos": campos[:10]})
    return fora[:3]


def links_de_busca(html: str) -> list:
    """Links que levam a uma página de busca. Função pura."""
    return sorted({u[:140] for u in RE_LINK_BUSCA.findall(html or "")})[:5]


def diagnostico(html: str) -> dict:
    """O diagnóstico de uma página inicial de diário. Função pura, sem rede."""
    formas = formularios_de_busca(html)
    links = links_de_busca(html)
    return {"plataforma": plataforma_de(html),
            "formularios_de_busca": formas,
            "links_de_busca": links,
            # "pista" quer dizer: há por onde começar. Não quer dizer que a busca funcione.
            "veredito": "pista_de_rota" if (formas or links) else "sem_rota_na_pagina_inicial"}


def veredito_da_recusa(erro) -> dict:
    """Recusa da fonte, pelo nome certo. Função pura.

    Nunca chamar bloqueio de geolocalização ou muro de robô de "robots.txt": nomear a recusa
    errado já custou treze dias de abstenção indevida (§187).
    """
    nome = type(erro).__name__
    codigo = getattr(erro, "code", None)
    if nome == "MuroDeRobo":
        return {"veredito": "recusa_servida_com_200", "motivo": f"muro de robô: {str(erro)[:140]}"}
    if codigo in (401, 403, 429, 451):
        return {"veredito": "bloqueio_de_acesso", "motivo": f"HTTP {codigo} — recusa respeitada"}
    if nome in ("URLError", "TimeoutError", "SSLError", "ConnectionResetError"):
        return {"veredito": "nao_respondeu", "motivo": f"{nome}: {str(erro)[:140]}"}
    return {"veredito": "erro", "motivo": f"{nome}: {str(erro)[:140]}"}


# 17/10/2026 (HANDOVER_ROTAS_DOE §1, degraus 1 e 3): o diário em SPA chama uma API pública que só
# aparece no código que a própria página carrega; e o decreto do governador também sai na rede LexML.
# Os dois modos abaixo só MEDEM e imprimem — quem escreve o adaptador é quem lê o relatório.
RE_SCRIPT = re.compile(r'<script[^>]+src="([^"]+)"', re.I)
RE_ROTA_NO_CODIGO = re.compile(r"""["'`]((?:https?://[\w.\-]+)?/[\w\-./{}:$]{2,100})["'`]""")
RE_ROTA_DE_DIARIO = re.compile(r"(api|edic|diario|jornal|publica|busca|pesquis|pdf|caderno|materia)", re.I)
LEXML_SRU = ("https://www.lexml.gov.br/busca/SRU?operation=searchRetrieve&version=1.1"
             "&maximumRecords={n}&query={q}")
RE_SRU_TOTAL = re.compile(r"<(?:\w+:)?numberOfRecords>(\d+)<", re.I)
RE_SRU_URN = re.compile(r"(urn:lex:[^<\s\"]+)")


def rotas_no_codigo(js: str) -> list:
    """Caminhos citados no código da página que têm cara de rota de diário. Função pura."""
    vistos = []
    for r in RE_ROTA_NO_CODIGO.findall(js or ""):
        if RE_ROTA_DE_DIARIO.search(r) and not r.endswith((".css", ".png", ".svg", ".woff2", ".js")) and r not in vistos:
            vistos.append(r)
    return vistos


def leitura_sru(xml: str) -> dict:
    """{total, urns} da resposta SRU do LexML. Função pura."""
    m = RE_SRU_TOTAL.search(xml or "")
    return {"total": int(m.group(1)) if m else None, "urns": list(dict.fromkeys(RE_SRU_URN.findall(xml or "")))}


def sondar_codigo(buscar, base: str, teto_bytes: int = 12_000_000) -> dict:
    import urllib.parse
    html = buscar(base, timeout=45).decode("utf-8", "replace")
    rotas, lidos = rotas_no_codigo(html), []
    for src in RE_SCRIPT.findall(html)[:6]:
        url = urllib.parse.urljoin(base, src)
        try:
            js = buscar(url, timeout=60)
        except Exception as e:  # noqa: BLE001
            lidos.append(f"{url[:80]}: {type(e).__name__}")
            continue
        lidos.append(f"{url[:80]}: {len(js)} B")
        if len(js) <= teto_bytes:
            rotas += [r for r in rotas_no_codigo(js.decode("utf-8", "replace")) if r not in rotas]
    return {"scripts": lidos, "rotas": rotas[:60]}


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

    ok("acha a plataforma declarada", plataforma_de('<script src="/x/apifront/y.js">') == "apifront")
    ok("sem assinatura devolve None", plataforma_de("<html></html>") is None)

    html_form = ('<form action="/busca" method="post">'
                 '<input name="palavra"><select name="ano_palavra"></select></form>')
    f = formularios_de_busca(html_form)
    ok("acha o formulário de busca, com método e campos",
       len(f) == 1 and f[0]["metodo"] == "post" and "palavra" in f[0]["campos"])
    ok("formulário que não é de busca fica fora",
       formularios_de_busca('<form action="/login"><input name="senha"></form>') == [])
    ok("campo de busca com nome curto conta",
       len(formularios_de_busca('<form action="/"><input name="q"></form>')) == 1)
    ok("acha o link de busca",
       links_de_busca('<a href="/busca/">x</a><a href="/sobre">y</a>') == ["/busca/"])

    d = diagnostico(html_form)
    ok("veredito de pista quando há formulário", d["veredito"] == "pista_de_rota")
    ok("veredito de ausência quando não há nada",
       diagnostico("<html><body>só texto</body></html>")["veredito"] == "sem_rota_na_pagina_inicial")

    class _Muro(Exception):
        pass
    _Muro.__name__ = "MuroDeRobo"
    r = veredito_da_recusa(_Muro("Imperva"))
    ok("muro de robô é recusa servida com 200, e é dito assim",
       r["veredito"] == "recusa_servida_com_200" and "muro de robô" in r["motivo"])

    class _HTTP(Exception):
        code = 403
    ok("403 é bloqueio de acesso, respeitado",
       veredito_da_recusa(_HTTP())["veredito"] == "bloqueio_de_acesso")

    class _TLS(Exception):
        pass
    _TLS.__name__ = "URLError"
    ok("falha de conexão não é recusa da fonte",
       veredito_da_recusa(_TLS("EOF"))["veredito"] == "nao_respondeu")
    ok("recusa nunca é chamada de robots.txt",
       "robots" not in json.dumps([veredito_da_recusa(_Muro("x")), veredito_da_recusa(_HTTP())]))

    fonte = pathlib.Path(__file__).read_text(encoding="utf-8")
    escritas = [l for l in fonte.splitlines() if l.strip().startswith("gravar(")]
    ok("rotas de diário citadas no código da página saem, e estilo e imagem não",
       rotas_no_codigo('a="/api/v1/edicoes/{data}";b="/assets/x.png";c="https://h.gov.br/diario/pdf";d="/sobre"')
       == ["/api/v1/edicoes/{data}", "https://h.gov.br/diario/pdf"])
    ok("a resposta SRU do LexML dá o total e as URNs",
       leitura_sru("<srw:numberOfRecords>2</srw:numberOfRecords><x>urn:lex:br;parana:estadual:decreto:2026-09-10;123</x>")
       == {"total": 2, "urns": ["urn:lex:br;parana:estadual:decreto:2026-09-10;123"]})
    ok("resposta SRU sem total não vira zero", leitura_sru("<html>erro</html>")["total"] is None)
    ok("trava estrutural: uma escrita só, e é o registro de fontes",
       len(escritas) == 1 and escritas[0].strip().startswith("gravar(ARQUIVO"))
    ok("trava estrutural: nenhum arquivo do banco é destino",
       not any(f'gravar("{b}' in fonte for b in BANCO_PROIBIDO))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else f"✓ AUTOTESTE OK — {len(_casos_contados)} casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return _autoteste()

    sys.path.insert(0, str(RAIZ))
    from coletores_base import MuroDeRobo, buscar, gravar, hoje_editorial, ler

    registro = ler(ARQUIVO, {}) or {}
    ufs = registro.get("ufs") or {}
    hoje = hoje_editorial().strftime("%d/%m/%Y")
    def arg(nome):
        return sys.argv[sys.argv.index(nome) + 1] if nome in sys.argv and sys.argv.index(nome) + 1 < len(sys.argv) else ""
    if "--codigo" in sys.argv:              # só mede e imprime
        for alvo in arg("--codigo").split(","):
            uf, _, base = alvo.partition("=")
            base = base or (ufs.get(uf) or {}).get("url")
            try:
                r = sondar_codigo(buscar, base)
            except Exception as e:  # noqa: BLE001
                r = veredito_da_recusa(e)
            print(f"== {uf} {base}\n" + json.dumps(r, ensure_ascii=False, indent=1))
        return 0
    if "--trecho" in sys.argv:              # só mede e imprime: endereço~termo~termo; sem termo, o começo
        for alvo in arg("--trecho").split("|"):
            url, *termos = alvo.split("~")
            try:
                t = buscar(url, timeout=60).decode("utf-8", "replace")
            except Exception as e:  # noqa: BLE001
                print(f"== {url}: {veredito_da_recusa(e)}")
                continue
            print(f"== {url} ({len(t)} caracteres)")
            for termo in termos or [""]:
                for m in list(re.finditer(re.escape(termo), t))[:12] if termo else [None]:
                    i = m.start() if m else 0
                    print(f"-- {termo or 'início'} @{i}: " + t[max(0, i - 160):i + 340].replace("\n", " "))
        return 0
    if "--lexml" in sys.argv:               # só mede e imprime: uma consulta CQL por linha de --lexml
        import urllib.parse
        for q in arg("--lexml").replace("+", " ").split("|"):   # "+" é espaço: a linha do elo não leva aspas
            try:
                r = leitura_sru(buscar(LEXML_SRU.format(n=20, q=urllib.parse.quote(q)), timeout=60).decode("utf-8", "replace"))
            except Exception as e:  # noqa: BLE001
                r = veredito_da_recusa(e)
            print(f"== LexML {q}\n" + json.dumps(r, ensure_ascii=False, indent=1)[:4000])
        return 0
    alvos = [(uf, (v or {}).get("url")) for uf, v in sorted(ufs.items()) if not (v or {}).get("adaptador")]
    print(f"{len(alvos)} unidade(s) sem adaptador a sondar")

    for uf, url in alvos:
        if not url:
            d = {"veredito": "sem_endereco", "motivo": "nenhum endereço de diário registrado"}
        else:
            try:
                html = buscar(url, timeout=45).decode("utf-8", "replace")
                d = diagnostico(html)
            except MuroDeRobo as e:
                d = veredito_da_recusa(e)
            except Exception as e:  # noqa: BLE001
                d = veredito_da_recusa(e)
        d["sondado_em"] = hoje
        ufs[uf]["sondagem"] = d
        print(f"  {uf}: {d['veredito']}" + (f" — {d.get('motivo', '')[:90]}" if d.get("motivo") else "")
              + (f" · campos {d['formularios_de_busca'][0]['campos']}" if d.get("formularios_de_busca") else ""))

    registro["ufs"] = ufs
    registro["sondagem_de_rotas_em"] = hoje
    registro["_nota_sondagem"] = (
        "Diagnóstico por unidade da federação sem adaptador de busca, escrito por "
        "scripts/sondar_rotas_doe.py. 'pista_de_rota' quer dizer que há por onde começar a escrever "
        "o adaptador, e não que a busca funcione; 'sem_rota_na_pagina_inicial' é medição da página "
        "inicial, não afirmação de que o diário não tem busca. Recusa da fonte é registrada pelo "
        "nome certo (§186, §187).")
    if "--ensaio" in sys.argv:
        print("ensaio: nada gravado")
        return 0
    gravar(ARQUIVO, registro)
    print(f"{ARQUIVO} atualizado")
    return 0


if __name__ == "__main__":
    sys.exit(main())
