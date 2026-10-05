#!/usr/bin/env python3
"""
scripts/aplicar_edicoes.py — edição de uma linha, do pedido aprovado ao catálogo
=================================================================================
Item 2 do `HANDOVER_catalogo_de_conteudo_05-10-2026.md`.

O CAMINHO. A central grava um pedido em `robo-registro/edicoes/AAAA-MM-DD-<id>.md`, com
frontmatter: `id`, `pagina`, `antes`, `depois`, `aprovado: sim|nao`, `aprovado_em`, `motivo`. Este
script lê os aprovados, aplica no catálogo e deixa o PR pronto.

AS TRÊS TRAVAS, e por que cada uma existe

  1. **Só `aprovado: sim` é aplicado.** O arquivo existir não é aprovação: a central escreve o
     pedido e a editoria aprova, e são dois atos. Pedido sem a marca fica onde está, contado no
     relatório.

  2. **`antes` tem de ser o texto ATUAL.** Se o catálogo mudou desde que o pedido foi escrito — por
     outra edição, por uma migração —, aplicar o `depois` em cima de um texto diferente do que a
     editoria viu produz um resultado que ninguém aprovou. Aí o script RECUSA e relata, com o texto
     que encontrou. É a mesma regra da âncora antes da substituição, que o PROTOCOLO já exige para
     edição de página.

  3. **O verificador de conformidade roda antes de fechar.** Edição aprovada não é edição válida: a
     editoria aprova o conteúdo, e as travas de vocabulário, legenda e ausência continuam valendo.
     Texto reprovado não entra, e o motivo volta no relatório.

O QUE ELE NÃO FAZ. Não cria identificador, não apaga entrada, não muda componente nem dado — isso é
handover com contrato, e o handover diz isso com todas as letras no item 2.4. Edição é trocar o
texto de um identificador que já existe.

USO
    python3 scripts/aplicar_edicoes.py --conferir     # lê e relata, sem gravar
    python3 scripts/aplicar_edicoes.py --aplicar      # grava no catálogo
    python3 scripts/aplicar_edicoes.py --autoteste
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
CATALOGO = RAIZ / "conteudo"
# O privado fica ao lado do público, como todo o resto das notas da editoria.
EDICOES = RAIZ.parent / "robo-registro" / "edicoes"

OBRIGATORIOS = ("id", "pagina", "antes", "depois")


def ler_frontmatter(texto: str) -> dict:
    """O frontmatter YAML simples do pedido. Função pura.

    YAML de verdade seria uma dependência nova para ler seis campos de uma linha cada; o formato do
    pedido é fechado e documentado, e `chave: valor` cobre tudo o que ele tem. Valor entre aspas
    preserva os dois-pontos, que aparecem em texto editorial.
    """
    t = (texto or "").lstrip()
    if not t.startswith("---"):
        return {}
    fim = t.find("\n---", 3)
    if fim < 0:
        return {}
    fora = {}
    for linha in t[3:fim].splitlines():
        if not linha.strip() or linha.lstrip().startswith("#"):
            continue
        if ":" not in linha:
            continue
        chave, valor = linha.split(":", 1)
        valor = valor.strip()
        if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
            valor = valor[1:-1]
        fora[chave.strip()] = valor
    return fora


def aprovado(pedido: dict) -> bool:
    """O pedido tem a marca de aprovação da editoria? Função pura."""
    return str((pedido or {}).get("aprovado") or "").strip().lower() in ("sim", "s", "true")


def problemas_do_pedido(pedido: dict) -> list:
    """O que falta para o pedido ser aplicável. Função pura."""
    fora = [f"sem `{c}`" for c in OBRIGATORIOS if not str((pedido or {}).get(c) or "").strip()]
    if (pedido or {}).get("antes") == (pedido or {}).get("depois"):
        fora.append("`antes` e `depois` são o mesmo texto — nada a aplicar")
    return fora


def aplicavel(pedido: dict, textos: dict) -> tuple:
    """(pode, motivo) — o `antes` ainda é o texto atual? Função pura.

    A comparação colapsa espaço, porque o pedido vem de um editor de texto e pode trazer quebra de
    linha onde o catálogo tem espaço. O que não se tolera é diferença de palavra ou de pontuação.
    """
    ident = str((pedido or {}).get("id") or "")
    atual = (textos or {}).get(ident)
    if atual is None:
        return False, (f"o identificador {ident!r} não existe no catálogo — edição não cria "
                       f"identificador (item 2.4: isso é handover com contrato)")
    norm = lambda s: re.sub(r"\s+", " ", str(s or "")).strip()  # noqa: E731
    if norm(atual) != norm(pedido.get("antes")):
        return False, (f"o texto mudou desde o pedido. No catálogo: {norm(atual)[:80]!r}; "
                       f"no pedido: {norm(pedido.get('antes'))[:80]!r}")
    return True, ""


def aplicar(pedidos: list, textos: dict) -> tuple:
    """(textos_novos, aplicados, recusados) — aplica os aprovados. Função pura.

    Devolve dicionário NOVO: a decisão de gravar é de quem chamou, e uma função que já escreveu não
    dá para conferir antes.
    """
    novos = dict(textos or {})
    aplicados, recusados = [], []
    for p in pedidos or []:
        falta = problemas_do_pedido(p)
        if falta:
            recusados.append((p.get("id") or "?", "; ".join(falta)))
            continue
        if not aprovado(p):
            recusados.append((p["id"], "sem `aprovado: sim` — a editoria ainda não aprovou"))
            continue
        pode, motivo = aplicavel(p, novos)
        if not pode:
            recusados.append((p["id"], motivo))
            continue
        novos[p["id"]] = p["depois"]
        aplicados.append(p["id"])
    return novos, aplicados, recusados


def _autoteste() -> int:
    falhas = []

    def ok(nome, cond):
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    FM = ('---\nid: p.s.e.legenda\npagina: financiamento\n'
          'antes: "Texto velho"\ndepois: "Texto novo"\naprovado: sim\n'
          'aprovado_em: 2026-10-05\nmotivo: clareza\n---\n\ncorpo livre\n')
    p = ler_frontmatter(FM)
    ok("lê as chaves do frontmatter", p.get("id") == "p.s.e.legenda")
    ok("tira as aspas do valor", p.get("antes") == "Texto velho")
    ok("lê a marca de aprovação", aprovado(p))
    ok("sem frontmatter devolve vazio", ler_frontmatter("corpo sem cabeçalho") == {})
    ok("frontmatter aberto e não fechado devolve vazio", ler_frontmatter("---\nid: x\n") == {})
    ok("valor com dois-pontos sobrevive",
       ler_frontmatter('---\nantes: "Ciclo: 2026"\n---\n').get("antes") == "Ciclo: 2026")

    ok("`aprovado: nao` não é aprovação", not aprovado({"aprovado": "nao"}))
    ok("sem a chave não é aprovação", not aprovado({}))

    ok("pedido completo não tem pendência", problemas_do_pedido(p) == [])
    ok("falta de campo é acusada", "sem `depois`" in problemas_do_pedido({"id": "a", "pagina": "b",
                                                                         "antes": "c"}))
    ok("antes igual a depois não é edição",
       any("mesmo texto" in x for x in problemas_do_pedido(
           {"id": "a", "pagina": "b", "antes": "x", "depois": "x"})))

    T = {"p.s.e.legenda": "Texto velho"}
    ok("o `antes` que bate é aplicável", aplicavel(p, T)[0])
    ok("o `antes` que NÃO bate é recusado, com o texto achado",
       not aplicavel(p, {"p.s.e.legenda": "Outro texto"})[0])
    ok("o espaço não decide: quebra de linha no pedido ainda bate",
       aplicavel(dict(p, antes="Texto\n  velho"), T)[0])
    ok("identificador inexistente é recusado com o motivo certo",
       "não cria identificador" in aplicavel(p, {})[1])

    novos, apl, rec = aplicar([p], T)
    ok("o aprovado é aplicado", novos["p.s.e.legenda"] == "Texto novo" and apl == ["p.s.e.legenda"])
    ok("o original não é alterado — a função é pura", T["p.s.e.legenda"] == "Texto velho")
    n2, a2, r2 = aplicar([dict(p, aprovado="nao")], T)
    ok("o não aprovado NÃO é aplicado", a2 == [] and n2 == T)
    ok("e a recusa diz por quê", "ainda não aprovou" in r2[0][1])
    n3, a3, r3 = aplicar([p, dict(p, id="p.s.e.titulo")], T)
    ok("um lote aplica o que pode e recusa o resto",
       a3 == ["p.s.e.legenda"] and len(r3) == 1)
    ok("lote vazio não quebra", aplicar([], T) == (T, [], []))

    import dis
    nomes = set()
    for n in ("ler_frontmatter", "aprovado", "problemas_do_pedido", "aplicavel", "aplicar"):
        c = getattr(globals()[n], "__code__", None)
        if c is not None:
            nomes |= {i.argval for i in dis.get_instructions(c) if isinstance(i.argval, str)}
    ok("trava estrutural: as funções puras não leem disco nem escrevem",
       not ({"read_text", "write_text", "open", "gravar"} & nomes))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else "✓ AUTOTESTE OK — 22 casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def main() -> int:
    argv = sys.argv[1:]
    if "--autoteste" in argv:
        return _autoteste()
    if not EDICOES.exists():
        print(f"✓ EDIÇÕES — {EDICOES} não existe; nada a aplicar")
        return 0

    pedidos_por_pagina = {}
    total = 0
    for arq in sorted(EDICOES.glob("*.md")):
        p = ler_frontmatter(arq.read_text(encoding="utf-8"))
        if not p:
            print(f"  ⚠ {arq.name}: sem frontmatter legível — ignorado")
            continue
        p["_arquivo"] = arq.name
        pedidos_por_pagina.setdefault(p.get("pagina") or "?", []).append(p)
        total += 1
    if not total:
        print("✓ EDIÇÕES — nenhum pedido em edicoes/")
        return 0

    aplicados_tudo, recusados_tudo = [], []
    for pagina, pedidos in sorted(pedidos_por_pagina.items()):
        arq = CATALOGO / f"{pagina}.json"
        if not arq.exists():
            recusados_tudo += [(p.get("id") or p["_arquivo"],
                                f"a página {pagina!r} ainda não foi migrada para o catálogo")
                               for p in pedidos]
            continue
        doc = json.loads(arq.read_text(encoding="utf-8"))
        novos, apl, rec = aplicar(pedidos, doc.get("textos") or {})
        aplicados_tudo += [(pagina, i) for i in apl]
        recusados_tudo += rec
        if apl and "--aplicar" in argv:
            doc["textos"] = novos
            arq.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n",
                           encoding="utf-8", newline="\n")

    print(f"{total} pedido(s) lido(s) · {len(aplicados_tudo)} aplicável(is) · "
          f"{len(recusados_tudo)} recusado(s)")
    for pagina, ident in aplicados_tudo:
        print(f"  ✓ {pagina}: {ident}")
    for ident, motivo in recusados_tudo:
        print(f"  ✗ {ident}: {motivo}")
    if "--aplicar" not in argv:
        print("\n(--conferir: nada foi gravado. Use --aplicar para gravar no catálogo.)")
        return 0
    if aplicados_tudo:
        print("\nAgora: rode `python3 scripts/verificar_catalogo.py` e os portões da página, e "
              "abra o PR com as capturas por figura.")
    # Recusa não é erro do script: é o relatório que a editoria precisa ver. Sai 0 para não
    # derrubar a rotina que o chama a cada hora; o que reprova é o portão, no PR.
    return 0


if __name__ == "__main__":
    sys.exit(main())
