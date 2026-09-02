#!/usr/bin/env python3
"""
verificar_financiamento.py — portão 13 (v2.3, §7.8)
====================================================
 (a) nenhuma chave de API em código ou dados (padrões de chave do Portal);
 (b) toda figura de financiamento.html tem crédito (fonteFigura) — cartões de texto isentos;
 (c) reconciliação: quando houver série, soma das rotas por semana = total declarado;
 (d) nenhum valor imputado: rota "aguardando_coleta" tem valor null;
 (e) resposta nunca somada a preparação: rotas r3/r4 marcadas ex_ante=false e a função
     somaPreparacao da página exclui-as (testado no runtime); aqui: modelo coerente;
 (f) nada de data/financiamento/ lido por recalcular_mare.py; TESTE DE ESTRESSE: com a
     pasta inteira renomeada, o índice recomputado é idêntico bit a bit;
 (g) faixa do defeso presente na série (datas e base legal);
 (h) ausência de qualquer campo de autor de emenda em data/financiamento/ (E10).
Uso: python3 verificar_financiamento.py [--negativos]
"""
import json, os, pathlib, re, shutil, sys, tempfile

RAIZ = pathlib.Path(__file__).parent; FIN = RAIZ / "data" / "financiamento"
AUTOR = re.compile(r'"(nomeAutor|codigoAutor|autor(?:_emenda)?|nomeParlamentar|autorEmenda)"', re.I)
CHAVE = re.compile(r'chave-api-dados["\']?\s*[:=]\s*["\'][0-9a-f]{20,}', re.I)


def checar(html, rotas, serie, poruf, motor, arquivos_fin: dict) -> list:
    e = []
    if CHAVE.search(html) or CHAVE.search(motor) or any(CHAVE.search(t) for t in arquivos_fin.values()): e.append("(a) chave de API em código ou dados")
    for cid in ["boxSerie", "boxFundoEstadual", "boxPorHab", "boxDinheiro", "boxResposta", "boxPainel", "boxCompromissos", "boxFinance", "boxFontesMonit", "boxConsultas"]:
        if f"fonteFigura('{cid}'" not in html: e.append(f"(b) figura sem crédito: #{cid}")
    ids = [r["id"] for r in rotas["rotas"]]
    for s in serie.get("semanas", []):
        soma = sum(float(s.get(i) or 0) for i in ids)
        if s.get("total") is not None and abs(soma - float(s["total"])) > 0.5: e.append(f"(c) semana {s.get('semana')}: soma das rotas {soma} ≠ total {s['total']}")
    for uf, u in poruf.get("uf", {}).items():
        for rid, r in (u.get("rotas") or {}).items():
            if r.get("status") == "aguardando_coleta" and r.get("valor_2026") is not None: e.append(f"(d) {uf}/{rid}: valor imputado em rota aguardando coleta")
    resp = {r["id"] for r in rotas["rotas"] if not r["ex_ante"]}
    if resp != {"r3", "r4"}: e.append(f"(e) rotas de resposta devem ser exatamente r3 e r4; achou {sorted(resp)}")
    if "somaPreparacao" not in html or "filter(r => r.ex_ante)" not in html: e.append("(e) página sem somaPreparacao restrita a rotas ex_ante")
    if re.search(r"financiamento/", motor): e.append("(f) recalcular_mare.py referencia data/financiamento/")
    d = serie.get("defeso", {})
    if not (d.get("inicio") == "2026-07-04" and d.get("fim") == "2026-10-25" and "73" in str(d.get("base", ""))): e.append("(g) faixa do defeso ausente ou incompleta na série")
    for nome, t in arquivos_fin.items():
        m = AUTOR.search(t)
        if m: e.append(f"(h) E10: campo de autor em {nome}: {m.group(1)}")
    return e


def carregar():
    j = lambda p: json.load(open(p, encoding="utf-8"))
    arqs = {p.name: p.read_text(encoding="utf-8") for p in FIN.glob("*.json")}
    return (open(RAIZ / "financiamento.html", encoding="utf-8").read(), j(FIN / "rotas.json"), j(FIN / "serie_nacional.json"), j(FIN / "por_uf.json"),
            open(RAIZ / "recalcular_mare.py", encoding="utf-8").read(), arqs)


def estresse() -> bool:
    """Renomeia data/financiamento/ inteira e recomputa o índice: precisa ser bit a bit igual."""
    sys.path.insert(0, str(RAIZ)); import recalcular_mare as rm
    antes, media, _, _ = rm.calcular(); tmp = RAIZ / "data" / "_financiamento_estresse"
    os.rename(FIN, tmp)
    try:
        depois, media2, _, _ = rm.calcular()
    finally:
        os.rename(tmp, FIN)
    return antes == depois and media == media2


def negativos() -> int:
    html, rotas, serie, poruf, motor, arqs = carregar(); import copy
    casos = {
        "chave de API no motor": lambda: checar(html, rotas, serie, poruf, motor + '\nchave-api-dados = "0123456789abcdef0123456789abcdef"', arqs),
        "figura sem crédito": lambda: checar(html.replace("fonteFigura('boxSerie'", "fonteFigura('boxX'"), rotas, serie, poruf, motor, arqs),
        "reconciliação quebrada": lambda: checar(html, rotas, {**serie, "semanas": [{"semana": "2026-01-05", "r1": 10, "total": 99}]}, poruf, motor, arqs),
        "valor imputado": lambda: checar(html, rotas, serie, {**poruf, "uf": {**poruf["uf"], "SC": {**poruf["uf"]["SC"], "rotas": {**poruf["uf"]["SC"]["rotas"], "r1": {"valor_2026": 5, "status": "aguardando_coleta"}}}}}, motor, arqs),
        "motor lendo financiamento": lambda: checar(html, rotas, serie, poruf, motor + "\nx = 'data/financiamento/x.json'", arqs),
        "campo de autor (E10)": lambda: checar(html, rotas, serie, poruf, motor, {**arqs, "emendas.json": '{"itens":[{"nomeAutor":"X"}]}'}),
        "faixa do defeso ausente": lambda: checar(html, rotas, {**serie, "defeso": {}}, poruf, motor, arqs),
    }
    f = 0
    for n, fn in casos.items():
        ok = bool(fn()); print(("  ✓ " if ok else "  ✗ ") + "negativo acusado: " + n); f += (not ok)
    return 1 if f else 0


if __name__ == "__main__":
    if "--negativos" in sys.argv: sys.exit(negativos())
    e = checar(*carregar())
    if not estresse(): e.append("(f) TESTE DE ESTRESSE: índice mudou sem data/financiamento/")
    if e:
        print("✗ FINANCIAMENTO: publicação bloqueada:"); [print("   ", x) for x in e]; sys.exit(1)
    print("✓ FINANCIAMENTO OK — sem chave, créditos por figura, modelo coerente, nada imputado, resposta separada, motor intacto sob estresse, defeso na série, E10.")
