#!/usr/bin/env python3
"""Portão de conformidade: toda página, todo texto, toda figura, sempre.

POR QUE ELE EXISTE (handover da editoria, 02/10/2026)
----------------------------------------------------
As regras de design e editoriais já decididas **valem para todas as páginas, o tempo todo**, e não
dependem de um handover repeti-las. O que não é verificado por máquina volta a ser interpretado a
cada rodada — e foi assim que um cartão saiu de uma página numa reforma de desenho, que um rótulo
foi cortado no meio por um eixo de gráfico, e que um texto ficou da cor do fundo.

Este portão incorpora o de layout (`verificar_layout.py`, que continua existindo e é chamado por
ele) e acrescenta o que as regras exigem: tipografia, componentes, as quatro funções da figura,
vocabulário proibido, forma dos números, acessibilidade e a coerência entre páginas.

O QUE ELE CONFERE, por página
-----------------------------
  (A) o CONTRATO da página — ordem de seção, cartão, grade, largura, texto exigido e proibido
      (delegado a `verificar_layout.problemas_do_despejo`, que já tem autoteste próprio);
  (B) TIPOGRAFIA — família, peso e tamanho renderizados, contra `layout/regras.json`;
  (C) FIGURA — título, legenda que não repete o título, fonte, mídia rotulada;
  (D) VOCABULÁRIO — global, por página, advérbio colado a número, locução de dever;
  (E) NÚMEROS — travessão em cartão, "sem dado" com série em disco;
  (F) ACESSIBILIDADE — alvo de toque no celular, rolagem horizontal, texto invisível;
  (G) FUNDO — branco, que é decisão editorial declarada e já foi revertida por engano uma vez.

A medição vem de `scripts/_layout_dump.js` (Playwright, 1280 e 390 px). A REGRA é texto legível em
`layout/regras.json` e nos contratos; aqui só se julga. Por isso o portão tem autoteste offline: ele
julga despejos de fixture, sem rede e sem navegador.

EXCEÇÃO
-------
Só por `layout/excecoes.json`, com regra, página, motivo, data e quem decidiu. Exceção sem registro
é vermelho — exceção que não se declara é regra que se perdeu.

USO
    python3 scripts/verificar_conformidade.py                    # todas as páginas contratadas
    python3 scripts/verificar_conformidade.py imprensa.html
    python3 scripts/verificar_conformidade.py --todas            # todas as páginas públicas
    python3 scripts/verificar_conformidade.py --despejo d.json imprensa.html
    python3 scripts/verificar_conformidade.py --autoteste
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))

CONTRATOS = RAIZ / "layout" / "contratos"
REGRAS = RAIZ / "layout" / "regras.json"
EXCECOES = RAIZ / "layout" / "excecoes.json"


def ler_json(p, padrao=None):
    try:
        return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return padrao


def excecoes_de(pagina: str, excecoes: dict) -> set:
    """As regras dispensadas nesta página. Função pura.

    Exceção sem motivo e sem data NÃO vale: ela é o registro da decisão, e registro sem a decisão
    é só uma regra desligada em silêncio.
    """
    fora = set()
    for e in (excecoes or {}).get("excecoes") or []:
        if e.get("pagina") not in (pagina, "*"):
            continue
        if not (e.get("motivo") and e.get("data") and e.get("decidido_por")):
            continue
        fora.add(e.get("regra"))
    return fora


# ── (B) tipografia ──────────────────────────────────────────────────────────────────────────
def problemas_de_tipografia(amostras: list, regras: dict) -> list:
    """Divergências de família, peso e tamanho. Função pura."""
    t = (regras or {}).get("tipografia") or {}
    familias = t.get("familias_permitidas") or {}
    por_seletor = t.get("por_seletor") or {}
    escala = set(t.get("escala_px") or [])
    vers = t.get("versalete") or {}
    p = []
    vistos = set()
    for a in amostras or []:
        regra = por_seletor.get(a.get("seletor"))
        if not regra:
            continue
        chave = (a.get("seletor"), a.get("familia"), a.get("peso"), a.get("tamanho"))
        if chave in vistos:
            continue
        vistos.add(chave)
        permitidas = familias.get(regra.get("grupo")) or []
        if permitidas and a.get("familia") not in permitidas:
            p.append(f"tipografia: {a['seletor']} em {a.get('familia')!r}, e a regra pede "
                     f"{regra.get('grupo')} ({', '.join(permitidas)})")
        teto = regra.get("peso_maximo")
        try:
            peso = int(str(a.get("peso") or "400"))
        except ValueError:
            peso = 400
        if teto and peso > int(teto):
            p.append(f"tipografia: {a['seletor']} em peso {peso}, e a regra proíbe acima de {teto} "
                     f"(display nunca em bold)")
        if escala and a.get("tamanho") and int(a["tamanho"]) not in escala:
            p.append(f"tipografia: {a['seletor']} em {a['tamanho']}px, fora da escala "
                     f"{sorted(escala)}")
        if regra.get("versalete"):
            if (a.get("caixa") or "") != (vers.get("caixa") or "uppercase"):
                p.append(f"tipografia: {a['seletor']} deveria ser versalete e está em "
                         f"{a.get('caixa')!r}")
            esp = float(re.sub(r"[^0-9.\-]", "", str(a.get("espacamento") or "0")) or 0)
            if esp < float(vers.get("espacamento_minimo_px") or 1.0):
                p.append(f"tipografia: {a['seletor']} em versalete sem espaçamento de letra "
                         f"({a.get('espacamento')})")
    return p


# ── (C) as quatro funções da figura ─────────────────────────────────────────────────────────
def problemas_de_figura(figuras: list, regras: dict) -> list:
    """Título, legenda, fonte e mídia rotulada. Função pura."""
    r = (regras or {}).get("figura") or {}
    p = []
    for f in figuras or []:
        if not f.get("visivel"):
            continue
        nome = f.get("id") or "(figura sem id)"
        if r.get("titulo_obrigatorio") and not (f.get("titulo") or "").strip():
            p.append(f"figura '{nome}': sem título")
        if r.get("fonte_obrigatoria") and not (f.get("fonte") or "").strip():
            p.append(f"figura '{nome}': sem linha de fonte")
        titulo = (f.get("titulo") or "").strip().lower()
        legenda = (f.get("legenda") or "").strip().lower()
        if r.get("legenda_nao_repete_titulo") and titulo and legenda and titulo == legenda:
            p.append(f"figura '{nome}': a legenda repete o título")
        teto = r.get("legenda_maxima_caracteres")
        if teto and len(f.get("legenda") or "") > int(teto):
            p.append(f"figura '{nome}': legenda com {len(f['legenda'])} caracteres (teto {teto})")
        if r.get("midia_rotulada") and f.get("tem_midia") and not f.get("rotulada"):
            p.append(f"figura '{nome}': mídia sem rótulo acessível (aria-label ou alt)")
    return p


# ── (D) vocabulário ─────────────────────────────────────────────────────────────────────────
def problemas_de_vocabulario(texto: str, pagina: str, regras: dict, contrato: dict) -> list:
    """Vocabulário proibido: global, por página, advérbio com número, locução de dever. Pura."""
    v = (regras or {}).get("vocabulario_proibido") or {}
    t = texto or ""
    baixo = t.lower()
    p = []
    proibidas = list(v.get("global") or [])
    proibidas += list((v.get("por_pagina") or {}).get(pagina) or [])
    proibidas += list((contrato or {}).get("texto_proibido") or [])
    # Comparação SENSÍVEL à caixa, de propósito: o que a regra barra é "FIGURA" em caixa alta — a
    # numeração de figura que a editoria tirou —, e não a palavra "figura" numa frase legítima
    # ("a fonte primária de cada figura"). Barrar as duas foi o primeiro falso positivo deste
    # portão, em 03/10/2026, na própria página que explica como citar.
    for palavra in sorted(set(proibidas)):
        if palavra and palavra in t:
            i = t.index(palavra)
            p.append(f"vocabulário proibido: {palavra!r} — …{t[max(0, i - 40):i + 40]!r}")
    for adv in v.get("com_numero") or []:
        for m in re.finditer(r"\b" + re.escape(adv) + r"\s+[\d]", baixo):
            p.append(f"juízo colado a número: {adv!r} — …{t[max(0, m.start() - 30):m.start() + 40]!r}")
    for locucao in v.get("dever") or []:
        if locucao.lower() in baixo:
            i = baixo.index(locucao.lower())
            p.append(f"locução de dever fora de citação de lei: {locucao!r} — "
                     f"…{t[max(0, i - 40):i + 40]!r}")
    return p


# ── (E) números e (F) acessibilidade ────────────────────────────────────────────────────────
def problemas_de_numero(numeros: list, regras: dict) -> list:
    """Travessão e vazio em cartão de número. Função pura."""
    r = (regras or {}).get("numeros") or {}
    p = []
    if not r.get("travessao_em_cartao_proibido"):
        return p
    for n in numeros or []:
        valor = (n.get("valor") or "").strip()
        if valor in ("", "—", "-"):
            p.append(f"cartão de número '{n.get('id') or n.get('valor_id')}' em travessão ou vazio")
    return p


def problemas_de_acessibilidade(d390: dict, regras: dict) -> list:
    """Alvo de toque e rolagem horizontal no celular. Função pura."""
    a = (regras or {}).get("acessibilidade") or {}
    p = []
    alvo = int(a.get("alvo_de_toque_px") or 44)
    for x in (d390.get("alvos_de_toque") or [])[:6]:
        p.append(f"alvo de toque de {x.get('altura')}px no celular (mínimo {alvo}): "
                 f"<{x.get('tag')}> {x.get('texto')!r}")
    if a.get("sem_rolagem_horizontal") and d390.get("rolagem_horizontal"):
        p.append("rolagem horizontal a 390 px")
    return p


def problemas_de_fundo(d1280: dict, regras: dict) -> list:
    """O fundo do corpo é o declarado. Função pura."""
    esperado = ((regras or {}).get("cor") or {}).get("fundo_do_corpo")
    visto = (d1280 or {}).get("fundo_do_corpo")
    if esperado and visto and visto.replace(" ", "") != esperado.replace(" ", ""):
        return [f"fundo do corpo em {visto}, e a decisão editorial é {esperado}"]
    return []


# ── o julgamento inteiro ────────────────────────────────────────────────────────────────────
def problemas(pagina: str, despejo: dict, regras: dict, contrato: dict, excecoes: dict) -> list:
    """Todas as divergências desta página. FUNÇÃO PURA — é ela que o autoteste exercita."""
    import verificar_layout

    d1280 = (despejo.get("larguras") or {}).get("1280") or {}
    d390 = (despejo.get("larguras") or {}).get("390") or {}
    if not d1280:
        return ["despejo sem a largura de 1280 px"]
    dispensadas = excecoes_de(pagina, excecoes)
    p = []
    por_regra = [
        ("contrato", verificar_layout.problemas_do_despejo(contrato, despejo) if contrato else []),
        ("tipografia", problemas_de_tipografia(d1280.get("tipografia") or [], regras)),
        ("figura", problemas_de_figura(d1280.get("figuras_completas") or [], regras)),
        ("vocabulario", problemas_de_vocabulario(d1280.get("texto_visivel") or "", pagina,
                                                 regras, contrato)),
        ("numeros", problemas_de_numero(d1280.get("numeros") or [], regras)),
        ("acessibilidade", problemas_de_acessibilidade(d390, regras)),
        ("fundo", problemas_de_fundo(d1280, regras)),
    ]
    for nome, achados in por_regra:
        if nome in dispensadas:
            continue
        p += [f"[{nome}] {x}" for x in achados]
    return p


def _autoteste() -> int:
    falhas = []

    def ok(nome, cond):
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    regras = ler_json(REGRAS) or {}
    ok("as regras existem e declaram a hierarquia",
       bool(regras.get("hierarquia")) and regras["hierarquia"][0].startswith("AI_EDITORIAL"))
    ok("a hierarquia põe handover por último", regras["hierarquia"][-1] == "handovers")

    # (B) tipografia
    bom = [{"seletor": "main h2", "familia": "Fraunces", "peso": "300", "tamanho": 28,
            "espacamento": "normal", "caixa": "none"}]
    ok("título em Fraunces 300 passa", problemas_de_tipografia(bom, regras) == [])
    bold = [dict(bom[0], peso="700")]
    ok("título em bold reprova", any("bold" in x for x in problemas_de_tipografia(bold, regras)))
    outra = [dict(bom[0], familia="Comic Sans MS")]
    ok("título fora da família reprova",
       any("Comic" in x for x in problemas_de_tipografia(outra, regras)))
    fora = [dict(bom[0], tamanho=27)]
    ok("tamanho fora da escala reprova",
       any("fora da escala" in x for x in problemas_de_tipografia(fora, regras)))
    rot = [{"seletor": "main .cartao-numero-rotulo", "familia": "Archivo Narrow", "peso": "400",
            "tamanho": 12, "espacamento": "1.44px", "caixa": "uppercase"}]
    ok("rótulo em versalete espaçado passa", problemas_de_tipografia(rot, regras) == [])
    semcaixa = [dict(rot[0], caixa="none")]
    ok("rótulo sem versalete reprova",
       any("versalete" in x for x in problemas_de_tipografia(semcaixa, regras)))
    semesp = [dict(rot[0], espacamento="normal")]
    ok("versalete sem espaçamento de letra reprova",
       any("espaçamento" in x for x in problemas_de_tipografia(semesp, regras)))
    ok("seletor não listado não é julgado",
       problemas_de_tipografia([{"seletor": "main .qualquer", "familia": "X", "peso": "900",
                                 "tamanho": 13}], regras) == [])

    # (C) figura
    fig = [{"id": "boxA", "titulo": "Municípios sob alerta", "legenda": "Consulta mais recente",
            "fonte": "Fonte: Cemaden · Atualização: 02/10/2026", "tem_midia": True,
            "rotulada": True, "visivel": True}]
    ok("figura completa passa", problemas_de_figura(fig, regras) == [])
    ok("figura sem título reprova",
       any("sem título" in x for x in problemas_de_figura([dict(fig[0], titulo="")], regras)))
    ok("figura sem fonte reprova",
       any("sem linha de fonte" in x for x in problemas_de_figura([dict(fig[0], fonte="")], regras)))
    ok("legenda que repete o título reprova",
       any("repete o título" in x for x in
           problemas_de_figura([dict(fig[0], legenda="Municípios sob alerta")], regras)))
    ok("mídia sem rótulo reprova",
       any("sem rótulo" in x for x in problemas_de_figura([dict(fig[0], rotulada=False)], regras)))
    ok("figura invisível não é julgada",
       problemas_de_figura([dict(fig[0], visivel=False, titulo="")], regras) == [])

    # (D) vocabulário
    ok("texto limpo passa",
       problemas_de_vocabulario("Os municípios com decreto no ciclo.", "x.html", regras, {}) == [])
    ok("palavra global proibida reprova",
       any("desastre" in x for x in
           problemas_de_vocabulario("houve um desastre", "x.html", regras, {})))
    ok("'figura' em frase legítima NÃO é a numeração 'FIGURA' proibida",
       problemas_de_vocabulario("a fonte primária de cada figura", "imprensa.html", regras, {}) == [])
    ok("juízo colado a número reprova",
       any("juízo" in x for x in
           problemas_de_vocabulario("apenas 3 estados publicaram", "x.html", regras, {})))
    ok("a mesma palavra longe de número NÃO reprova",
       not any("juízo" in x for x in
               problemas_de_vocabulario("apenas o estado publicou", "x.html", regras, {})))
    ok("locução de dever reprova",
       any("dever" in x for x in
           problemas_de_vocabulario("o município deve publicar o plano", "x.html", regras, {})))
    ok("proibido do contrato entra junto",
       any("Backlog" in x for x in
           problemas_de_vocabulario("Backlog da fila", "x.html", regras, {"texto_proibido": ["Backlog"]})))

    # (E) e (F)
    ok("cartão com valor passa", problemas_de_numero([{"id": "a", "valor": "749"}], regras) == [])
    ok("cartão em travessão reprova",
       len(problemas_de_numero([{"id": "a", "valor": "—"}], regras)) == 1)
    ok("cartão vazio reprova", len(problemas_de_numero([{"id": "a", "valor": ""}], regras)) == 1)
    ok("alvo de toque pequeno reprova",
       any("alvo de toque" in x for x in problemas_de_acessibilidade(
           {"alvos_de_toque": [{"tag": "button", "texto": "Ver", "altura": 30}]}, regras)))
    ok("rolagem horizontal reprova",
       any("rolagem" in x for x in problemas_de_acessibilidade({"rolagem_horizontal": True}, regras)))
    ok("celular sem problema passa",
       problemas_de_acessibilidade({"alvos_de_toque": [], "rolagem_horizontal": False}, regras) == [])
    ok("fundo branco passa", problemas_de_fundo({"fundo_do_corpo": "rgb(255, 255, 255)"}, regras) == [])
    ok("fundo escuro reprova",
       any("decisão editorial" in x for x in
           problemas_de_fundo({"fundo_do_corpo": "rgb(14, 15, 13)"}, regras)))

    # exceções
    exc = {"excecoes": [{"regra": "tipografia", "pagina": "x.html", "motivo": "m",
                         "data": "03/10/2026", "decidido_por": "editoria"}]}
    ok("exceção declarada dispensa a regra naquela página",
       excecoes_de("x.html", exc) == {"tipografia"})
    ok("exceção sem motivo não vale",
       excecoes_de("y.html", {"excecoes": [{"regra": "cor", "pagina": "y.html"}]}) == set())
    ok("exceção de outra página não vale aqui", excecoes_de("z.html", exc) == set())

    # trava estrutural: o portão não escreve
    import dis
    nomes = set()
    for nome_obj, obj in list(globals().items()):
        if nome_obj == "_autoteste":
            continue
        codigo = getattr(obj, "__code__", None)
        if codigo is not None:
            nomes |= {i.argval for i in dis.get_instructions(codigo) if isinstance(i.argval, str)}
    ok("trava estrutural: o portão não escreve nada",
       not ({"gravar", "gravar_em", "write_text", "write_bytes"} & nomes))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else "✓ AUTOTESTE OK — 32 casos, sem rede e sem navegador.")
    return 1 if falhas else 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return _autoteste()
    import verificar_layout

    regras = ler_json(REGRAS) or {}
    excecoes = ler_json(EXCECOES) or {}
    argumentos = [a for a in sys.argv[1:] if not a.startswith("--")]
    despejo_pronto = None
    if "--despejo" in sys.argv:
        i = sys.argv.index("--despejo")
        despejo_pronto = ler_json(sys.argv[i + 1])
        argumentos = [a for a in argumentos if a != sys.argv[i + 1]]

    if argumentos:
        paginas = argumentos
    elif "--todas" in sys.argv:
        paginas = [p for p in regras.get("paginas_publicas") or [] if (RAIZ / p).exists()]
    else:
        paginas = [c.stem + ".html" for c in sorted(CONTRATOS.glob("*.json"))]

    total = 0
    for pagina in paginas:
        contrato = ler_json(CONTRATOS / (pagina.replace(".html", "") + ".json"), {})
        try:
            despejo = despejo_pronto or verificar_layout.despejar(pagina)
        except RuntimeError as e:
            print(f"✗ CONFORMIDADE ({pagina}): o renderizador falhou — {e}")
            total += 1
            continue
        ruins = problemas(pagina, despejo, regras, contrato, excecoes)
        if ruins:
            total += len(ruins)
            print(f"✗ CONFORMIDADE ({pagina}): {len(ruins)} violação(ões):")
            for r in ruins:
                print("   - " + r)
        else:
            print(f"✓ CONFORMIDADE OK ({pagina})"
                  + (" — com contrato" if contrato else " — sem contrato próprio, só as regras"))
    if total:
        print(f"\n✗ CONFORMIDADE: {total} violação(ões) em {len(paginas)} página(s). "
              "Publicação bloqueada.")
        return 1
    print(f"\n✓ CONFORMIDADE OK — {len(paginas)} página(s) conformes às regras de "
          "layout/regras.json e ao contrato de cada uma.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
