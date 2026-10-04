#!/usr/bin/env python3
"""Portão do esquema da pista, e da saúde da fila (item C.3 do handover de 03/10/2026).

POR QUE ELE EXISTE. A fila de pistas chegou a **8.681** itens, e o retrato que a central mediu em
03/10/2026 diz o que estava errado — não na saída, na ENTRADA:

    6.462 sem município nem UF identificável   (busca por termo, sem alvo)
    6.455 em redirecionamento do Google News   (não o endereço do veículo)
    2.549 URLs repetidas
    4.455 sobre decreto (resposta), que não pontua e já vem de fonte oficial

Filtrar na saída não dá conta: a cada rodada entra mais do mesmo. Então a regra passa a valer na
gravação — `coletores_base.gravar_pista` recusa pista fora do esquema — e este portão confere duas
coisas:

  (a) **esquema**: as pistas ABERTAS da fila trazem os campos obrigatórios de `schemas/pista.json`;
  (b) **saúde da fila**: alerta quando ela cresce três rodadas seguidas, quando a idade mediana
      passa de 14 dias, ou quando a fração de nível C passa de 70%.

A alínea (a) é medida só nas pistas abertas DEPOIS da data em que a regra passou a valer: exigir o
esquema de quem entrou antes dele produziria 8 mil vermelhos que ninguém pode apagar, e vermelho
que não se apaga deixa de ser sinal. As antigas são tratadas pela limpeza e pela triagem.

USO
    python3 scripts/verificar_esquema_de_pista.py
    python3 scripts/verificar_esquema_de_pista.py --autoteste
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import statistics
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

ESQUEMA = RAIZ / "schemas" / "pista.json"
FILAS = ("pistas_imprensa.json", "pistas_descobertas.json", "pistas_doe.json")
# A regra do esquema passou a valer nesta data (handover da corrente noturna).
VALE_A_PARTIR_DE = "2026-10-04"
IDADE_MEDIANA_MAXIMA = 14
FRACAO_C_MAXIMA = 0.70
RODADAS_DE_CRESCIMENTO = 3


def ler_esquema(caminho=ESQUEMA) -> dict:
    try:
        return json.loads(pathlib.Path(caminho).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


# 04/10/2026 — O QUE BLOQUEIA E O QUE AVISA.
#
# Medido pela central: a publicação da noite de 03→04 falhou duas vezes por 10 pistas fora do
# esquema, e **nenhum dado novo foi ao ar**. O portão acusou o certo — pista malformada não pode
# entrar —, mas parar o site inteiro por dez sobras de Diário Oficial é desproporcional, e a
# editoria mandou rebaixar.
#
# A linha nova é esta: pista que está na FILA ATIVA (vai ao juiz, pode virar registro) e está fora do
# esquema **bloqueia**; pista já tirada da fila — em quarentena, ou com `destino` declarado para
# outro lugar, como a conferência da base de resposta — **avisa**. A diferença é de consequência: a
# primeira pode entrar no índice errada, a segunda já não vai a lugar nenhum sem alguém olhar.
DESTINOS_FORA_DA_FILA = ("conferencia_resposta", "quarentena", "rejeitada")


def fora_da_fila_ativa(pista: dict) -> bool:
    """A pista já foi tirada da fila ativa, e portanto não pode virar registro? Função pura."""
    p = pista or {}
    if p.get("quarentena") or p.get("rejeitada"):
        return True
    return str(p.get("destino") or "") in DESTINOS_FORA_DA_FILA


def problemas_de_esquema(pistas: list, esquema: dict, vale_a_partir_de=VALE_A_PARTIR_DE,
                         so_fila_ativa: bool = False) -> list:
    """As pistas novas que não cumprem o esquema. Função pura.

    Com `so_fila_ativa=True`, ignora o que já saiu da fila: é a lista que BLOQUEIA. Sem o
    parâmetro, devolve tudo — é a lista que vira aviso no painel.
    """
    obrigatorios = list((esquema.get("obrigatorios") or {}).keys())
    tipos = set(esquema.get("tipos_validos") or [])
    niveis = set(esquema.get("niveis_validos") or [])
    origens = set(esquema.get("origens_validas") or [])
    ruins = []
    for p in pistas or []:
        # Só `registrado_em`: é a data em que a pista ENTROU na fila. `data` é a data do item na
        # fonte (a notícia pode ser de ontem ou de amanhã), e usá-la cobrava o esquema de pistas
        # antigas cuja notícia tinha data recente — vermelho em quem a regra não alcança.
        registrado = str(p.get("registrado_em") or "")[:10]
        if not registrado or registrado < vale_a_partir_de:
            continue
        if so_fila_ativa and fora_da_fila_ativa(p):
            continue
        ident = str(p.get("id") or p.get("url_final") or p.get("url") or "?")[:12]
        faltam = [c for c in obrigatorios if not p.get(c)]
        if faltam:
            ruins.append(f"{ident}: sem {', '.join(faltam)}")
            continue
        if tipos and p.get("tipo") not in tipos:
            ruins.append(f"{ident}: tipo {p.get('tipo')!r} fora de {sorted(tipos)}")
        if niveis and str(p.get("nivel") or "").upper() not in niveis:
            ruins.append(f"{ident}: nível {p.get('nivel')!r} fora de {sorted(niveis)}")
        if origens and p.get("origem") not in origens:
            ruins.append(f"{ident}: origem {p.get('origem')!r} fora de {sorted(origens)}")
        if "news.google.com" in str(p.get("url_final") or ""):
            ruins.append(f"{ident}: url_final é redirecionamento, não o endereço do veículo")
        if p.get("tipo") == "decreto":
            ruins.append(f"{ident}: pista de decreto na fila de planos — vai para a base oficial")
    return ruins


def saude_da_fila(pistas: list, historico: list, hoje_iso: str) -> dict:
    """{tamanho, idade_mediana, fracao_c, crescendo, alertas}. Função pura."""
    import sys as _s
    _s.path.insert(0, str(RAIZ / "scripts"))
    from limpar_fila_de_pistas import aberta
    abertas = [p for p in (pistas or []) if aberta(p)]
    idades = []
    for p in abertas:
        bruto = str(p.get("registrado_em") or "")[:10]
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                d = dt.datetime.strptime(bruto, fmt).date()
                idades.append((dt.date.fromisoformat(hoje_iso) - d).days)
                break
            except ValueError:
                continue
    niveis_c = sum(1 for p in abertas
                   if str(p.get("nivel") or p.get("nivel_confianca") or "").upper() == "C")
    tamanhos = [h.get("tamanho") for h in (historico or []) if isinstance(h.get("tamanho"), int)]
    crescendo = (len(tamanhos) >= RODADAS_DE_CRESCIMENTO
                 and all(tamanhos[-i] > tamanhos[-i - 1]
                         for i in range(1, RODADAS_DE_CRESCIMENTO)))
    fora = {
        "tamanho": len(abertas),
        "idade_mediana": round(statistics.median(idades), 1) if idades else None,
        "fracao_c": round(niveis_c / len(abertas), 2) if abertas else 0.0,
        "crescendo": bool(crescendo),
        "alertas": [],
    }
    if fora["idade_mediana"] is not None and fora["idade_mediana"] > IDADE_MEDIANA_MAXIMA:
        fora["alertas"].append(f"idade mediana de {fora['idade_mediana']} dias "
                               f"(limite {IDADE_MEDIANA_MAXIMA})")
    if fora["fracao_c"] > FRACAO_C_MAXIMA:
        fora["alertas"].append(f"{fora['fracao_c']:.0%} das pistas abertas em nível C "
                               f"(limite {FRACAO_C_MAXIMA:.0%})")
    if crescendo:
        fora["alertas"].append(f"a fila cresceu {RODADAS_DE_CRESCIMENTO} rodadas seguidas")
    return fora


def _autoteste() -> int:
    falhas = []

    def ok(nome, cond):
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    esquema = ler_esquema()
    ok("o esquema existe e declara os obrigatórios",
       set(esquema.get("obrigatorios") or {}) >= {"url_final", "tipo", "alvo", "nivel", "data", "origem"})
    ok("o esquema declara o teto por município",
       (esquema.get("regras") or {}).get("teto_por_municipio_e_assunto") == 5)

    boa = {"id": "n1", "url_final": "https://x.com.br/a", "tipo": "plano", "alvo": "4217808",
           "nivel": "A", "data": "2026-10-05", "origem": "busca_web",
           "registrado_em": "2026-10-05"}
    ok("pista completa passa", problemas_de_esquema([boa], esquema) == [])
    ok("pista antiga não é cobrada",
       problemas_de_esquema([dict(boa, registrado_em="2026-09-01", tipo=None)], esquema) == [])
    ok("pista sem registrado_em não é cobrada, mesmo com data recente",
       problemas_de_esquema([{"id": "x", "data": "2026-10-09"}], esquema) == [])
    ok("falta de alvo reprova",
       any("alvo" in x for x in problemas_de_esquema([dict(boa, alvo=None)], esquema)))
    ok("falta de url_final reprova",
       any("url_final" in x for x in problemas_de_esquema([dict(boa, url_final=None)], esquema)))
    ok("tipo inválido reprova",
       any("tipo" in x for x in problemas_de_esquema([dict(boa, tipo="qualquer")], esquema)))
    ok("nível inválido reprova",
       any("nível" in x for x in problemas_de_esquema([dict(boa, nivel="Z")], esquema)))
    ok("origem inválida reprova",
       any("origem" in x for x in problemas_de_esquema([dict(boa, origem="telepatia")], esquema)))
    ok("redirecionamento na url_final reprova",
       any("redirecionamento" in x for x in problemas_de_esquema(
           [dict(boa, url_final="https://news.google.com/rss/articles/X")], esquema)))
    ok("pista de decreto na fila de planos reprova",
       any("base oficial" in x for x in problemas_de_esquema([dict(boa, tipo="decreto")], esquema)))

    abertas = [{"status": "pista", "registrado_em": "2026-09-20", "nivel": "C"},
               {"status": "pista", "registrado_em": "2026-10-01", "nivel": "A"},
               {"status": "fechada — x", "registrado_em": "2026-01-01", "nivel": "C"}]
    s = saude_da_fila(abertas, [], "2026-10-03")
    ok("a saúde conta só as pistas abertas", s["tamanho"] == 2)
    ok("a idade mediana sai das datas", s["idade_mediana"] == 7.5)
    ok("a fração de nível C é das abertas", s["fracao_c"] == 0.5)
    velhas = [{"status": "pista", "registrado_em": "2026-09-01", "nivel": "C"}] * 3
    ok("idade mediana acima do limite alerta",
       any("idade mediana" in a for a in saude_da_fila(velhas, [], "2026-10-03")["alertas"]))
    ok("fração de C acima do limite alerta",
       any("nível C" in a for a in saude_da_fila(velhas, [], "2026-10-03")["alertas"]))
    ok("três rodadas de crescimento alertam",
       any("rodadas seguidas" in a for a in
           saude_da_fila(abertas, [{"tamanho": 1}, {"tamanho": 2}, {"tamanho": 3}], "2026-10-03")["alertas"]))
    ok("fila estável não alerta por crescimento",
       not any("rodadas seguidas" in a for a in
               saude_da_fila(abertas, [{"tamanho": 3}, {"tamanho": 2}, {"tamanho": 1}], "2026-10-03")["alertas"]))
    ok("fila vazia não quebra", saude_da_fila([], [], "2026-10-03")["tamanho"] == 0)

    import dis
    nomes = set()
    for nome_obj, obj in list(globals().items()):
        if nome_obj in ("_autoteste", "main"):
            continue
        codigo = getattr(obj, "__code__", None)
        if codigo is not None:
            nomes |= {i.argval for i in dis.get_instructions(codigo) if isinstance(i.argval, str)}
    ok("trava estrutural: o portão não escreve",
       not ({"gravar", "gravar_em", "write_text", "write_bytes"} & nomes))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else "✓ AUTOTESTE OK — 21 casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return _autoteste()
    from coletores_base import ler, hoje_editorial
    esquema = ler_esquema()
    hoje = hoje_editorial().isoformat()
    ruins, alertas = [], []
    for nome in FILAS:
        doc = ler(nome)
        if not doc:
            continue
        pistas = doc.get("pistas") or doc.get("itens") or []
        ruins += [f"{nome}: {x}" for x in problemas_de_esquema(pistas, esquema, so_fila_ativa=True)]
        declaradas = [x for x in problemas_de_esquema(pistas, esquema)
                      if x not in problemas_de_esquema(pistas, esquema, so_fila_ativa=True)]
        if declaradas:
            alertas.append(f"{nome}: {len(declaradas)} pista(s) fora do esquema já tirada(s) da "
                           f"fila (conferência ou quarentena) — não bloqueia, mas fica visível")
        if nome == "pistas_imprensa.json":
            s = saude_da_fila(pistas, (ler("saude_da_fila.json") or {}).get("rodadas") or [], hoje)
            print(f"fila de planos: {s['tamanho']} aberta(s) · idade mediana "
                  f"{s['idade_mediana']} dia(s) · nível C {s['fracao_c']:.0%}")
            alertas += s["alertas"]

    for a in alertas:
        print(f"⚠ saúde da fila: {a}")
    if ruins:
        print(f"✗ ESQUEMA DA PISTA: {len(ruins)} pista(s) nova(s) fora do esquema:")
        for r in ruins[:20]:
            print("   - " + r)
        return 1
    print(f"✓ ESQUEMA DA PISTA OK — nenhuma pista nova DA FILA ATIVA fora de schemas/pista.json"
          + (f"; {len(alertas)} alerta(s) de saúde da fila" if alertas else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
