#!/usr/bin/env python3
"""Vocabulário proibido: UMA régua para catálogo, blog, conformidade e texto público (JS).

Casa palavra inteira. `acha` ignora acento e caixa (catálogo e blog), salvo termo todo em CAIXA ALTA,
que casa com caixa ("FIGURA" é o rótulo de numeração que a editoria tirou, não a palavra numa frase
legítima). `exato=True` casa a grafia como está (texto renderizado: "Antecipação" no nome do site não
é a palavra "antecipação" proibida). `sem_citacao` tira o que está entre aspas (o blog cita lei e ato). CLI: `--json` lê
{"texto","pagina","contrato"} da entrada padrão e imprime os problemas (é o que o JS chama).
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def _sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFKD", str(s or "")) if not unicodedata.combining(c))


def acha(texto, termos, sem_citacao=False, exato=False):
    """Os termos proibidos que o texto traz (na ordem dada). Função pura."""
    if sem_citacao:
        texto = re.sub(r"[\"“][^\"”]{0,400}[\"”]", " ", texto or "")
    achados = []
    for termo in termos or []:
        alta = any(c.isalpha() for c in str(termo)) and str(termo).upper() == str(termo)
        if exato:
            alvo, t = str(texto or ""), str(termo)
        else:
            alvo, t = (_sem_acento(texto), _sem_acento(termo)) if alta else (_sem_acento(texto).lower(), _sem_acento(termo).lower())
        if t and re.search(r"(?<![A-Za-z0-9])" + re.escape(t) + r"(?![A-Za-z0-9])", alvo):
            achados.append(termo)
    return achados


def problemas(texto, pagina, regras, contrato):
    """Global, por página, `texto_proibido` do contrato, advérbio colado a número, locução de dever."""
    v = (regras or {}).get("vocabulario_proibido") or {}
    t = texto or ""
    baixo = t.lower()
    lista = sorted(set(list(v.get("global") or []) + list((v.get("por_pagina") or {}).get(pagina) or [])
                       + list((contrato or {}).get("texto_proibido") or [])))
    p = []
    for w in acha(t, lista, exato=True):
        i = max(t.find(w), 0)
        p.append(f"vocabulário proibido: {w!r} — …{t[max(0, i - 40):i + 40]!r}")
    for q in v.get("indice_e_ranking") or []:
        for m in re.finditer(q["padrao"], t, re.I):
            p.append(f"{q['motivo']}: {m.group(0)!r} — …{t[max(0, m.start() - 40):m.end() + 40]!r}")
    for adv in v.get("com_numero") or []:
        for m in re.finditer(r"\b" + re.escape(adv) + r"\s+[\d]", baixo):
            p.append(f"juízo colado a número: {adv!r} — …{t[max(0, m.start() - 30):m.start() + 40]!r}")
    for loc in v.get("dever") or []:
        if loc.lower() in baixo:
            i = baixo.index(loc.lower())
            p.append(f"locução de dever fora de citação de lei: {loc!r} — …{t[max(0, i - 40):i + 40]!r}")
    return p


def _autoteste():
    q = json.loads((RAIZ / "layout" / "regras.json").read_text(encoding="utf-8"))["vocabulario_proibido"]["indice_e_ranking"]
    reprova = lambda s: bool(problemas(s, "x.html", {"vocabulario_proibido": {"indice_e_ranking": q}}, {}))
    r = {"vocabulario_proibido": {"global": ["FIGURA", "desastre", "dados abertos"], "com_numero": ["apenas"],
                                  "dever": ["deve"]}}
    casos = [
        ("termo comum casa sem caixa e sem acento", acha("Houve um DESASTRE", ["desastre"]) == ["desastre"]),
        ("palavra que só contém o termo não casa", acha("subfuncionalidade", ["subfunção"]) == []),
        ("sem acento casa", acha("a subfuncao", ["subfunção"]) == ["subfunção"]),
        ("CAIXA ALTA casa com caixa", acha("a fonte de cada figura", ["FIGURA"]) == []
         and acha("FIGURA 3", ["FIGURA"]) == ["FIGURA"]),
        ("citação só vale com sem_citacao", acha('a lei diz "deve"', ["deve"]) == ["deve"]
         and acha('a lei diz "deve"', ["deve"], sem_citacao=True) == []),
        ("texto renderizado é exato: o nome 'Antecipação' não é a palavra 'antecipação'",
         problemas("Monitor de Antecipação", "x.html", {"vocabulario_proibido": {"global": ["antecipação"]}}, {}) == []),
        ("texto limpo passa", problemas("Os municípios com decreto.", "x.html", r, {}) == []),
        ("global reprova", any("desastre" in x for x in problemas("houve um desastre", "x.html", r, {}))),
        ("contrato soma", any("Backlog" in x for x in problemas("Backlog da fila", "x.html", {}, {"texto_proibido": ["Backlog"]}))),
        ("juízo colado a número", any("juízo" in x for x in problemas("apenas 3 estados", "x.html", r, {}))),
        ("juízo longe de número passa", not any("juízo" in x for x in problemas("apenas o estado", "x.html", r, {}))),
        ("'nota' do índice reprova: 'A nota de cada estado'", reprova("A nota de cada estado vai de 0 a 100")),
        ("'nota' do índice reprova: 'não entram na nota'", reprova("os decretos não entram na nota")),
        ("'nota' do índice reprova: 'fora da nota'", reprova("contexto, fora da nota")),
        ("'nota' do índice reprova: 'nota do MARÉ Legal'", reprova("a nota do MARÉ Legal sobe")),
        ("'nota' de rodapé e técnica passam", not reprova("Veja a nota técnica e a nota de rodapé. Nota: fonte Inmet")),
        ("'índice' passa", not reprova("O índice de cada estado e o valor do índice nacional")),
        ("ranking reprova", reprova("Ranking de estados")),
        ("ranqueia reprova", reprova("o painel ranqueia os municípios")),
        ("classificação dos estados reprova", reprova("a classificação dos estados")),
        ("pior colocado reprova", reprova("o pior colocado")),
        ("lidera reprova", reprova("o estado lidera a lista")),
        ("lanterna reprova", reprova("fica na lanterna")),
        ("último lugar reprova", reprova("ficou em último lugar")),
        ("'lugar' sem posição passa", not reprova("um lugar seguro; o lugar do abrigo")),
        ("locução de dever", any("dever" in x for x in problemas("o município deve publicar", "x.html", r, {}))),
    ]
    falhas = [n for n, c in casos if not c]
    for n, c in casos:
        print(("  ✓ " if c else "  ✗ ") + n)
    print(f"✗ AUTOTESTE: {len(falhas)} falha(s)" if falhas else f"✓ AUTOTESTE OK — {len(casos)} casos.")
    return 1 if falhas else 0


if __name__ == "__main__":
    if "--json" in sys.argv:
        d = json.load(sys.stdin)
        regras = json.loads((RAIZ / "layout" / "regras.json").read_text(encoding="utf-8"))
        print(json.dumps(problemas(d.get("texto"), d.get("pagina"), regras, d.get("contrato")), ensure_ascii=False))
        sys.exit(0)
    sys.exit(_autoteste())
