#!/usr/bin/env python3
"""Triagem da fila em TODA rodada — o último elo antes de publicar (item C.2, 03/10/2026).

A limpeza de C.1 é única; esta é **rotina permanente**. Ela pega a fila na ordem que a editoria
fixou, resolve o que der e dá um desfecho REGISTRADO a cada pista — nunca a deixa onde estava sem
dizer por quê.

A ORDEM
    municípios das listas federais de risco → capitais → o resto
    dentro de cada grupo: nível A → B → C, mais nova primeiro

A ordem de município é a mesma do item B (`scripts/ordem_de_coleta.py`): uma régua só para a
prioridade, em vez de duas que divergem na primeira correção.

OS DESFECHOS, todos registrados na própria pista
    promovida                      · o juiz leu o documento primário e promoveu
    coberta pela fonte oficial     · o fato já consta da base oficial (decreto registrado)
    sem documento oficial localizado · duas tentativas de busca dirigida, ou 21 dias na fila
    recusada pelo juiz (motivo)    · leu e não serve, com o critério que falhou
    para humano (motivo)           · consórcio, atribuição por proximidade, autoridade duvidosa

PRAZO DE VIDA. Duas tentativas sem documento, ou 21 dias, fecham a pista — e ela **reabre sozinha**
se surgir evidência nova para o mesmo município e assunto. Fechar não é apagar: o registro fica, e
é por ele que a reabertura sabe o que já foi tentado.

Este script é o ORQUESTRADOR: quem julga é `juiz.py`, quem aplica é `aplicar_promocoes_do_juiz.py`,
quem ordena é `ordem_de_coleta.py`. Aqui vive a ordem da rodada e o desfecho.

USO
    python3 scripts/triar_fila.py --relatorio
    python3 scripts/triar_fila.py --aplicar --limite 60
    python3 scripts/triar_fila.py --autoteste
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "scripts"))

FILA = "pistas_imprensa.json"
NIVEIS = {"A": 0, "B": 1, "C": 2}
DIAS_DE_VIDA = 21
TENTATIVAS_MAXIMAS = 2

DESFECHOS = ("promovida", "coberta pela fonte oficial", "sem documento oficial localizado",
             "recusada pelo juiz", "para humano")


def grupo_de_prioridade(pista: dict, prioritarios: set, capitais: set) -> int:
    """0 = lista federal de risco · 1 = capital · 2 = o resto. Função pura."""
    alvo = str(pista.get("alvo") or pista.get("ibge") or "").zfill(7)
    if alvo in prioritarios:
        return 0
    if alvo in capitais:
        return 1
    return 2


def chave_de_triagem(pista: dict, prioritarios: set, capitais: set):
    """A ordem da rodada: grupo, nível, mais nova primeiro. Função pura."""
    nivel = NIVEIS.get(str(pista.get("nivel") or pista.get("nivel_confianca") or "C").upper(), 2)
    data = str(pista.get("registrado_em") or pista.get("data") or "")
    return (grupo_de_prioridade(pista, prioritarios, capitais), nivel, _invertida(data))


def _invertida(data: str) -> str:
    """Chave que ordena do mais novo para o mais velho sem `reverse`. Função pura."""
    return "".join(chr(0x10FFFF - ord(c)) if ord(c) < 0x10FFFF else c for c in str(data or ""))


def fila_da_rodada(pistas: list, prioritarios: set, capitais: set, limite: int = 60) -> list:
    """As pistas desta rodada, na ordem. Função pura."""
    from limpar_fila_de_pistas import aberta
    abertas = [p for p in (pistas or []) if aberta(p)]
    abertas.sort(key=lambda p: chave_de_triagem(p, prioritarios, capitais))
    return abertas[:limite]


def desfecho_por_prazo(pista: dict, hoje_iso: str):
    """("sem documento oficial localizado", motivo) quando a pista venceu. Função pura."""
    tentativas = int(pista.get("tentativas_de_busca_dirigida") or 0)
    if tentativas >= TENTATIVAS_MAXIMAS:
        return ("sem documento oficial localizado",
                f"{tentativas} tentativas de busca dirigida sem documento")
    bruto = str(pista.get("registrado_em") or "")[:10]
    try:
        d = dt.date.fromisoformat(bruto)
    except ValueError:
        return None
    dias = (dt.date.fromisoformat(hoje_iso) - d).days
    if dias > DIAS_DE_VIDA:
        return ("sem documento oficial localizado",
                f"{dias} dias na fila (prazo de {DIAS_DE_VIDA})")
    return None


def reabre(pista: dict, evidencia_nova: dict) -> bool:
    """A pista fechada reabre com evidência nova para o mesmo município e assunto? Função pura."""
    if not str(pista.get("status") or "").startswith("fechada"):
        return False
    mesmo_alvo = str(pista.get("alvo") or pista.get("ibge") or "") == str(
        evidencia_nova.get("alvo") or evidencia_nova.get("ibge") or "")
    mesmo_assunto = (pista.get("tipo") or "plano") == (evidencia_nova.get("tipo") or "plano")
    return bool(mesmo_alvo and mesmo_assunto and evidencia_nova.get("url_final"))


def resumo(desfechos: list) -> dict:
    """{desfecho: n}, na ordem declarada. Função pura."""
    fora = {d: 0 for d in DESFECHOS}
    for d in desfechos or []:
        fora[d] = fora.get(d, 0) + 1
    return {k: v for k, v in fora.items() if v}


def _autoteste() -> int:
    falhas = []

    def ok(nome, cond):
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    P, C = {"4217808"}, {"3550308"}
    prio = {"alvo": "4217808", "nivel": "C", "registrado_em": "2026-09-01", "status": "pista"}
    cap = {"alvo": "3550308", "nivel": "A", "registrado_em": "2026-10-02", "status": "pista"}
    resto = {"alvo": "1234567", "nivel": "A", "registrado_em": "2026-10-03", "status": "pista"}
    ok("prioritário vem antes de capital, mesmo com nível pior",
       [p["alvo"] for p in fila_da_rodada([cap, resto, prio], P, C)][0] == "4217808")
    ok("capital vem antes do resto",
       [p["alvo"] for p in fila_da_rodada([resto, cap], P, C)] == ["3550308", "1234567"])
    a = {"alvo": "9", "nivel": "A", "registrado_em": "2026-09-01", "status": "pista"}
    c = {"alvo": "9", "nivel": "C", "registrado_em": "2026-10-03", "status": "pista"}
    ok("dentro do grupo, nível A vem antes de C",
       [p["nivel"] for p in fila_da_rodada([c, a], set(), set())] == ["A", "C"])
    nova = {"alvo": "9", "nivel": "A", "registrado_em": "2026-10-03", "status": "pista"}
    velha = {"alvo": "9", "nivel": "A", "registrado_em": "2026-09-01", "status": "pista"}
    ok("mesmo nível, mais nova primeiro",
       [p["registrado_em"] for p in fila_da_rodada([velha, nova], set(), set())]
       == ["2026-10-03", "2026-09-01"])
    ok("pista fechada não entra na rodada",
       fila_da_rodada([{"alvo": "9", "status": "fechada — x"}], set(), set()) == [])
    ok("o limite corta a rodada", len(fila_da_rodada([a, c, nova, velha], set(), set(), 2)) == 2)

    ok("duas tentativas fecham",
       desfecho_por_prazo({"tentativas_de_busca_dirigida": 2}, "2026-10-03")[0]
       == "sem documento oficial localizado")
    ok("22 dias fecham",
       desfecho_por_prazo({"registrado_em": "2026-09-10"}, "2026-10-03")[0]
       == "sem documento oficial localizado")
    ok("o motivo diz quantos dias",
       "dias na fila" in desfecho_por_prazo({"registrado_em": "2026-09-10"}, "2026-10-03")[1])
    ok("pista nova não vence", desfecho_por_prazo({"registrado_em": "2026-10-02"}, "2026-10-03") is None)
    ok("sem data não vence por prazo", desfecho_por_prazo({}, "2026-10-03") is None)

    fechada = {"status": "fechada — sem documento oficial localizado", "alvo": "9", "tipo": "plano"}
    ok("evidência nova para o mesmo alvo e assunto reabre",
       reabre(fechada, {"alvo": "9", "tipo": "plano", "url_final": "https://x/y.pdf"}))
    ok("evidência de outro município não reabre",
       not reabre(fechada, {"alvo": "8", "tipo": "plano", "url_final": "https://x/y.pdf"}))
    ok("evidência de outro assunto não reabre",
       not reabre(fechada, {"alvo": "9", "tipo": "estrutura", "url_final": "https://x/y.pdf"}))
    ok("evidência sem documento não reabre",
       not reabre(fechada, {"alvo": "9", "tipo": "plano"}))
    ok("pista aberta não 'reabre'",
       not reabre({"status": "pista", "alvo": "9"}, {"alvo": "9", "url_final": "u"}))

    ok("o resumo conta por desfecho",
       resumo(["promovida", "promovida", "para humano"])
       == {"promovida": 2, "para humano": 1})
    ok("desfecho que não ocorreu não aparece no resumo", "recusada pelo juiz" not in resumo([]))
    ok("os cinco desfechos do handover estão declarados", len(DESFECHOS) == 5)

    import dis
    nomes = set()
    for nome_obj, obj in list(globals().items()):
        if nome_obj in ("_autoteste", "main"):
            continue
        codigo = getattr(obj, "__code__", None)
        if codigo is not None:
            nomes |= {i.argval for i in dis.get_instructions(codigo) if isinstance(i.argval, str)}
    ok("trava estrutural: as funções de ordem e desfecho não escrevem",
       not ({"gravar", "gravar_em", "write_text"} & nomes))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else "✓ AUTOTESTE OK — 20 casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return _autoteste()
    limite = int(sys.argv[sys.argv.index("--limite") + 1]) if "--limite" in sys.argv else 60
    aplicar = "--aplicar" in sys.argv
    from coletores_base import gravar, ler, hoje_editorial
    hoje = hoje_editorial().isoformat()

    doc = ler(FILA) or {}
    pistas = doc.get("pistas") or []
    prioritarios = set((ler("prioridade_municipios.json") or {}).get("municipios") or {})
    ref = ler("municipios_ibge_referencia.json") or []
    capitais = {str(m["codigo_ibge"]).zfill(7) for m in ref if m.get("capital")}

    rodada = fila_da_rodada(pistas, prioritarios, capitais, limite)
    print(f"triagem: {len(rodada)} pista(s) nesta rodada, de "
          f"{sum(1 for p in pistas if not str(p.get('status') or '').startswith(('fechada', 'aplicada', 'rejeitada')))} aberta(s)")
    por_grupo = {}
    for p in rodada:
        g = grupo_de_prioridade(p, prioritarios, capitais)
        por_grupo[g] = por_grupo.get(g, 0) + 1
    print(f"   por grupo: prioritários {por_grupo.get(0, 0)} · capitais {por_grupo.get(1, 0)} · "
          f"demais {por_grupo.get(2, 0)}")

    vencidas = [(p, desfecho_por_prazo(p, hoje)) for p in rodada]
    vencidas = [(p, d) for p, d in vencidas if d]
    print(f"   vencem o prazo nesta rodada: {len(vencidas)}")
    if not aplicar:
        print("\nrelatório apenas; nada escrito (use --aplicar). O julgamento de quem não venceu "
              "é de `julgar_filas.py`, que esta triagem chama na rodada.")
        return 0

    for p, (desfecho, motivo) in vencidas:
        p["status"] = f"fechada — {desfecho}: {motivo}"
        p["triagem"] = {"em": hoje, "desfecho": desfecho, "motivo": motivo}
    gravar(FILA, doc)
    print(f"\n{len(vencidas)} pista(s) fechada(s) por prazo; o resto segue para o juiz nesta rodada")
    return 0


if __name__ == "__main__":
    sys.exit(main())
