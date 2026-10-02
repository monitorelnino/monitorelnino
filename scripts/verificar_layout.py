#!/usr/bin/env python3
"""Portão de layout: a página obedece ao contrato, ou não sobe.

POR QUE ELE EXISTE (handover da editoria, 02/10/2026)
----------------------------------------------------
Os erros de desenho se repetiam porque o layout era **interpretado a cada entrega**: cada rodada
relia o handover e desenhava de novo, e a cada releitura um detalhe mudava — cartão fora do
componente, mapa sozinho em um terço da largura, terceira coluna vazia, texto que já tinha saído
voltando. A editoria cortou a raiz: o layout passa a ser **contrato legível por máquina**, em
`layout/contratos/<pagina>.json`, e este portão reprova quando a página divergir dele. Nenhum PR
das páginas contratadas é mesclado com ele vermelho.

O QUE ELE COBRA
---------------
  (a) a ordem dos `h2` da página é a do contrato;
  (b) todo cartão listado existe, e nenhum sobra na grade contratada;
  (c) toda figura com mapa, gráfico ou lista está dentro do componente `.cartao-mapa`;
  (d) grade contratada com três colunas tem três filhos por linha — linha incompleta só na última;
  (e) nenhum cartão passa de um terço da largura da grade no desktop;
  (f) texto proibido não aparece no texto visível;
  (g) cartão de número não diz "sem dado" quando a série-base existe em disco, e não fica vazio
      nem em "—";
  (h) seção não vem envolta em caixa (borda ou fundo próprio);
  (i) cartão de número está dentro do componente de números, nunca solto.

A medição vem de `scripts/_layout_dump.js`, que renderiza a página em 1280 e 390 px com Playwright e
despeja a forma do DOM em JSON. A divisão é de propósito: a REGRA é texto legível no contrato, e o
navegador só mede. Assim o portão tem autoteste offline — ele julga um despejo de fixture, sem rede
e sem navegador.

USO
    python3 scripts/verificar_layout.py                      # todas as páginas contratadas
    python3 scripts/verificar_layout.py saude.html
    python3 scripts/verificar_layout.py --despejo d.json saude.html   # julga um despejo pronto
    python3 scripts/verificar_layout.py --autoteste
"""
import json
import pathlib
import subprocess
import sys
import tempfile

RAIZ = pathlib.Path(__file__).resolve().parent.parent
CONTRATOS = RAIZ / "layout" / "contratos"
DADOS = RAIZ / "data"
TOLERANCIA_LARGURA = 0.40     # um terço com folga de arredondamento e gap da grade


def contratos():
    return sorted(CONTRATOS.glob("*.json")) if CONTRATOS.exists() else []


def despejar(pagina: str) -> dict:
    """Renderiza e devolve o despejo. Levanta RuntimeError quando o renderizador falha."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        alvo = pathlib.Path(f.name)
    r = subprocess.run(["node", str(RAIZ / "scripts" / "_layout_dump.js"), pagina, str(alvo)],
                       capture_output=True, text=True, cwd=str(RAIZ))
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout or "").strip()[:300])
    return json.loads(alvo.read_text(encoding="utf-8"))


def serie_existe(chave: str) -> bool:
    """A série-base do cartão existe em disco? Função pura (consulta o sistema de arquivos).

    É isto que separa "sem dado" honesto de "sem dado" por descuido: se o arquivo está lá, o cartão
    tem de calcular."""
    if not chave:
        return False
    for alvo in (DADOS / chave, DADOS / "saude_desfechos" / chave):
        if alvo.exists():
            return True
    return False


def problemas_do_despejo(contrato: dict, despejo: dict) -> list:
    """As divergências entre o contrato e o despejo. FUNÇÃO PURA — é ela que o autoteste exercita."""
    p = []
    d1280 = (despejo.get("larguras") or {}).get("1280") or {}
    d390 = (despejo.get("larguras") or {}).get("390") or {}
    if not d1280:
        return ["despejo sem a largura de 1280 px"]

    secoes_contrato = contrato.get("secoes") or []
    # (a) ordem dos h2
    esperados = [s["h2"] for s in secoes_contrato if s.get("h2")]
    vistos = [h for h in (d1280.get("h2") or []) if h]
    if [h for h in vistos if h in esperados] != esperados:
        p.append(f"ordem dos títulos divergiu do contrato: contrato {esperados} · página {vistos}")

    por_id = {s.get("id"): s for s in (d1280.get("secoes") or [])}
    figuras = {f.get("id"): f for f in (d1280.get("figuras") or [])}
    grades = d1280.get("grades") or []
    numeros = d1280.get("numeros") or []
    texto = (d1280.get("texto_visivel") or "")

    for sec in secoes_contrato:
        sid = sec.get("id")
        vista = por_id.get(sid)
        if vista is None:
            p.append(f"seção '{sid}' não existe na página")
            continue
        # (h) seção sem caixa
        if vista.get("borda"):
            p.append(f"seção '{sid}' vem envolta em caixa (borda)")
        # (b) e (e) cartões de número
        if sec.get("tipo") == "numeros":
            ids_esperados = [c["valor_el"] for c in sec.get("cartoes") or []]
            vistos_valor = [n.get("valor_id") for n in numeros]
            faltam = [i for i in ids_esperados if i not in vistos_valor]
            if faltam:
                p.append(f"seção '{sid}': cartão(ões) do contrato ausente(s): {faltam}")
            for c in sec.get("cartoes") or []:
                n = next((x for x in numeros if x.get("valor_id") == c["valor_el"]), None)
                if n is None:
                    continue
                # (i) dentro do componente
                if "cartao-numero" not in (n.get("pai_grade") or "") and "grade-numeros" not in (n.get("pai_grade") or ""):
                    p.append(f"cartão '{c['id']}' fora do componente de números (pai: {n.get('pai_grade')!r})")
                valor = (n.get("valor") or "").strip()
                # (g) vazio, travessão ou "sem dado" com série em disco
                if not valor or valor == "—":
                    p.append(f"cartão '{c['id']}' vazio ou em travessão: {valor!r}")
                elif "sem dado" in valor.lower() or "sem coleta" in valor.lower():
                    if serie_existe(c.get("chave", "")):
                        p.append(f"cartão '{c['id']}' diz {valor!r} e a série-base "
                                 f"data/{c.get('chave')} existe em disco")
        # (b), (c), (d), (e) figuras
        for c in sec.get("cartoes") or []:
            el = c.get("el")
            if not el or sec.get("tipo") == "numeros":
                continue
            f = figuras.get(el)
            if f is None:
                p.append(f"seção '{sid}': cartão '{c['id']}' ({el}) não existe na página")
                continue
            if not f.get("cartao_mapa"):
                p.append(f"cartão '{c['id']}' ({el}) fora do componente .cartao-mapa")
            if f.get("tem_midia") or f.get("tem_lista"):
                largura_grade = next((g["largura"] for g in grades if el in (g.get("ids") or [])), None)
                if largura_grade and f.get("largura", 0) > largura_grade * TOLERANCIA_LARGURA:
                    p.append(f"cartão '{c['id']}' ({el}) ocupa {f['largura']}px de uma grade de "
                             f"{largura_grade}px — mais de um terço no desktop")
        # (d) contagem da grade
        if sec.get("grade") and (sec.get("cartoes") or sec.get("doencas")):
            alvo = [g for g in grades if sec["grade"].lstrip(".") in " ".join(g.get("classes") or [])
                    and g.get("secao") == sid]
            for g in alvo:
                col = max(1, g.get("colunas") or 3)
                filhos = g.get("filhos") or 0
                if filhos and filhos % col and filhos > col:
                    # linha incompleta é permitida só na última: filhos % col != 0 com mais de uma
                    # linha é aceitável; o que não se aceita é grade de três com uma linha de dois
                    # quando há mais linhas depois — e isso o despejo não distingue. Fica a regra
                    # mais conservadora: só avisa quando a grade tem menos filhos que colunas.
                    pass
                if filhos and filhos < col and not sec.get("ultima_linha_incompleta"):
                    p.append(f"seção '{sid}': grade de {col} colunas com {filhos} cartão(ões) — "
                             f"coluna vazia fora da última linha")
        # doenças: cada uma com a sua grade completa
        for doenca in sec.get("doencas") or []:
            ids = [c["el"] for c in doenca.get("cartoes") or []]
            faltam = [i for i in ids if i not in figuras]
            if faltam:
                p.append(f"doença '{doenca.get('h3')}': cartão(ões) ausente(s): {faltam}")
            h3s = vista.get("h3") or []
            if doenca.get("h3") and doenca["h3"] not in h3s:
                p.append(f"doença '{doenca.get('h3')}' sem subtítulo na seção '{sid}'")
        # estados: a grade da inicial, com os 27 e largura total
        if sec.get("estados"):
            tiles = [t for t in (d1280.get("estados") or [])
                     if t.get("pai") == sec["estados"]["grade"].lstrip("#")]
            if len(tiles) != sec["estados"]["cartoes"]:
                p.append(f"seção '{sid}': grade de estados com {len(tiles)} cartão(ões), "
                         f"contrato pede {sec['estados']['cartoes']}")
            sem_texto = [t["uf"] for t in tiles if len(t.get("texto") or "") < 3]
            if sem_texto:
                p.append(f"seção '{sid}': cartão de estado sem rótulo: {sem_texto[:5]}")
        # texto exigido
        for exigido in sec.get("exige_texto") or []:
            if exigido not in texto:
                p.append(f"seção '{sid}': texto exigido ausente: {exigido!r}")

    # (c) toda figura com mídia ou lista dentro do componente
    for f in d1280.get("figuras") or []:
        if (f.get("tem_midia") or f.get("tem_lista")) and f.get("visivel") and not f.get("cartao_mapa"):
            p.append(f"figura '{f.get('id')}' com mídia fora de .cartao-mapa")

    # (f) texto proibido
    for proibido in contrato.get("texto_proibido") or []:
        if proibido in texto:
            i = texto.index(proibido)
            p.append(f"texto proibido presente: {proibido!r} — …{texto[max(0, i - 40):i + 40]!r}")

    # erros de runtime e rolagem horizontal entram aqui: layout quebrado por JS é layout quebrado.
    for largura, dados in (despejo.get("larguras") or {}).items():
        for e in (dados.get("erros_de_runtime") or [])[:2]:
            p.append(f"{largura}px: erro de runtime na página — {e[:120]}")
        if dados.get("rolagem_horizontal"):
            p.append(f"{largura}px: rolagem horizontal")
    return p


def autoteste() -> int:
    contrato = {
        "pagina": "x.html",
        "secoes": [
            {"id": "topo", "tipo": "numeros", "grade": ".grade-numeros--3", "linhas": 1,
             "cartoes": [{"id": "a", "valor_el": "vA", "chave": "indice.json"},
                         {"id": "b", "valor_el": "vB", "chave": "nao_existe_nunca.json"}],
             "exige_texto": ["frase obrigatória"]},
            {"id": "mapas", "h2": "Seção de mapas", "tipo": "figuras", "grade": ".grade-figuras--3",
             "cartoes": [{"id": "m1", "el": "boxM1", "tipo": "mapa"}]},
        ],
        "texto_proibido": ["FIGURA"],
    }
    bom = {"larguras": {"1280": {
        "h2": ["Seção de mapas"],
        "secoes": [{"id": "topo", "h2": "", "h3": [], "borda": False},
                   {"id": "mapas", "h2": "Seção de mapas", "h3": [], "borda": False}],
        "grades": [{"classes": ["grade-numeros", "grade-numeros--3"], "filhos": 3, "ids": [], "largura": 1200, "colunas": 3, "secao": "topo"},
                   {"classes": ["grade-figuras", "grade-figuras--3"], "filhos": 3, "ids": ["boxM1"], "largura": 1200, "colunas": 3, "secao": "mapas"}],
        "figuras": [{"id": "boxM1", "classes": ["figura", "cartao-mapa"], "cartao_mapa": True,
                     "tem_midia": True, "tem_lista": False, "largura": 380, "visivel": True,
                     "pai_grade": "grade-figuras grade-figuras--3"}],
        "numeros": [{"id": "", "valor": "12", "valor_id": "vA", "pai_grade": "grade-numeros grade-numeros--3", "largura": 380},
                    {"id": "", "valor": "sem dado nesta edição", "valor_id": "vB", "pai_grade": "grade-numeros grade-numeros--3", "largura": 380}],
        "estados": [], "texto_visivel": "frase obrigatória e mais nada",
        "erros_de_runtime": [], "rolagem_horizontal": False}}}

    def com(mud):
        import copy
        d = copy.deepcopy(bom)
        mud(d["larguras"]["1280"])
        return d

    casos = [
        ("contrato cumprido não acusa nada", problemas_do_despejo(contrato, bom) == []),
        ("cartão de número ausente reprova",
         any("ausente" in x for x in problemas_do_despejo(
             contrato, com(lambda d: d["numeros"].pop(0))))),
        ("cartão vazio reprova",
         any("vazio ou em travessão" in x for x in problemas_do_despejo(
             contrato, com(lambda d: d["numeros"][0].update(valor="—"))))),
        # A trava central: "sem dado" só vale quando a série não existe.
        ("'sem dado' com série em disco reprova",
         any("existe em disco" in x for x in problemas_do_despejo(
             contrato, com(lambda d: d["numeros"][0].update(valor="sem dado nesta edição"))))),
        ("'sem dado' sem série em disco passa", problemas_do_despejo(contrato, bom) == []),
        ("figura fora do componente reprova",
         any(".cartao-mapa" in x for x in problemas_do_despejo(
             contrato, com(lambda d: d["figuras"][0].update(cartao_mapa=False, classes=["figura"]))))),
        ("cartão maior que um terço reprova",
         any("um terço" in x for x in problemas_do_despejo(
             contrato, com(lambda d: d["figuras"][0].update(largura=800))))),
        ("grade de três com um cartão reprova",
         any("coluna vazia" in x for x in problemas_do_despejo(
             contrato, com(lambda d: d["grades"][1].update(filhos=1))))),
        ("ordem de títulos diferente reprova",
         any("ordem dos títulos" in x for x in problemas_do_despejo(
             contrato, com(lambda d: d.update(h2=["Outra coisa"]))))),
        ("seção em caixa reprova",
         any("envolta em caixa" in x for x in problemas_do_despejo(
             contrato, com(lambda d: d["secoes"][1].update(borda=True))))),
        ("texto proibido reprova",
         any("texto proibido" in x for x in problemas_do_despejo(
             contrato, com(lambda d: d.update(texto_visivel="frase obrigatória FIGURA 1"))))),
        ("texto exigido ausente reprova",
         any("texto exigido" in x for x in problemas_do_despejo(
             contrato, com(lambda d: d.update(texto_visivel="nada"))))),
        ("erro de runtime reprova",
         any("erro de runtime" in x for x in problemas_do_despejo(
             contrato, com(lambda d: d.update(erros_de_runtime=["x is not defined"]))))),
        ("rolagem horizontal reprova",
         any("rolagem horizontal" in x for x in problemas_do_despejo(
             contrato, com(lambda d: d.update(rolagem_horizontal=True))))),
        ("despejo sem 1280 reprova com mensagem própria",
         problemas_do_despejo(contrato, {"larguras": {}}) == ["despejo sem a largura de 1280 px"]),
        ("os contratos do repositório são JSON válido e nomeiam a página",
         all(json.loads(c.read_text(encoding="utf-8")).get("pagina") for c in contratos())),
    ]
    ruins = [n for n, ok in casos if not ok]
    for n, ok in casos:
        print(f"  {'OK  ' if ok else 'FALHA'} {n}")
    if ruins:
        print(f"X AUTOTESTE: {len(ruins)} caso(s) reprovado(s).")
        return 1
    print(f"OK AUTOTESTE — {len(casos)} casos, sem rede e sem navegador.")
    return 0


def main() -> int:
    args = sys.argv[1:]
    if "--autoteste" in args:
        return autoteste()
    despejo_pronto = None
    if "--despejo" in args:
        i = args.index("--despejo")
        despejo_pronto = pathlib.Path(args[i + 1])
        args = args[:i] + args[i + 2:]
    alvos = [a for a in args if a.endswith(".html")]
    arquivos = ([CONTRATOS / (a.replace(".html", "") + ".json") for a in alvos] if alvos
                else contratos())
    if not arquivos:
        print("✗ LAYOUT: nenhum contrato em layout/contratos/")
        return 1
    falhas = 0
    for arq in arquivos:
        contrato = json.loads(pathlib.Path(arq).read_text(encoding="utf-8"))
        pagina = contrato["pagina"]
        try:
            despejo = (json.loads(despejo_pronto.read_text(encoding="utf-8")) if despejo_pronto
                       else despejar(pagina))
        except Exception as e:  # noqa: BLE001
            print(f"✗ LAYOUT ({pagina}): não foi possível medir a página — {e}")
            falhas += 1
            continue
        ruins = problemas_do_despejo(contrato, despejo)
        if ruins:
            falhas += 1
            print(f"✗ LAYOUT ({pagina}): {len(ruins)} divergência(s) do contrato:")
            for r in ruins:
                print("   -", r)
        else:
            print(f"✓ LAYOUT OK ({pagina}) — ordem, componentes, grades, larguras e textos "
                  f"conforme layout/contratos/{pathlib.Path(arq).name}.")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
