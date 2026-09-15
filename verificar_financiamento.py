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
from pagina_completa import ler_pagina

RAIZ = pathlib.Path(__file__).parent; FIN = RAIZ / "data" / "financiamento"
AUTOR = re.compile(r'"(nomeAutor|codigoAutor|autor(?:_emenda)?|nomeParlamentar|autorEmenda)"', re.I)
CHAVE = re.compile(r'chave-api-dados["\']?\s*[:=]\s*["\'][0-9a-f]{20,}', re.I)


def checar(html, rotas, serie, poruf, motor, arquivos_fin: dict) -> list:
    e = []
    if CHAVE.search(html) or CHAVE.search(motor) or any(CHAVE.search(t) for t in arquivos_fin.values()): e.append("(a) chave de API em código ou dados")
    for cid in ["boxRede", "boxPreventivoSetor", "boxRSGrafico"]:   # 15/09/2026: figuras vivas na página (Fundo estadual, contadores, dinheiro e resposta saíram a pedido da editoria)   # boxFontesMonit/boxConsultas vivem em pesquisadores.html (07/09/2026); boxPorHab retirado do HTML em 13/09/2026 (auditoria de visualizações) — sem cobertura mínima (1/8 rotas), JS mantido desativado; boxPainel, boxCompromissos, boxFinance, boxSerie, boxRotaMPs, boxMpsBrUf, boxMpsUf e boxMpsUfBarras migraram para pesquisadores.html em 13/09/2026 (proposta de enxugamento, Manus AI)
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
    # 14/09/2026 (rota preventiva do fogo): (f) toda rota tem `objeto` ∈ {preventivo, resposta, livre}; (g) rotas_preventivas.json:
    # toda linha com lei, artigo, fonte e hash, objeto válido; frase de não-existência para seca/chuva só enquanto não houver linha
    # com esses riscos; (h) o motor do índice nunca lê financiamento/fogo nem rotas_preventivas.
    for r in rotas["rotas"]:
        if r.get("objeto") not in {"preventivo", "resposta", "livre"}: e.append(f"(f) rota {r.get('id')} sem `objeto` válido")
    import hashlib as _hl
    try:
        rp = json.loads((FIN / "rotas_preventivas.json").read_text(encoding="utf-8"))
        for l in rp.get("rotas", []):
            for k in ("lei", "artigo", "fonte", "hash", "objeto", "risco"):
                if not l.get(k): e.append(f"(g) rotas_preventivas: linha {l.get('id')} sem {k}")
            if l.get("objeto") not in {"preventivo", "resposta", "livre"}: e.append(f"(g) rotas_preventivas: objeto inválido em {l.get('id')}")
            h = _hl.sha256(json.dumps({k: v for k, v in l.items() if k != "hash"}, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]
            if h != l.get("hash"): e.append(f"(g) rotas_preventivas: hash não confere em {l.get('id')} — conteúdo alterado sem recalcular")
        riscos = {l.get("risco") for l in rp.get("rotas", []) if l.get("objeto") == "preventivo"}
        if riscos != set(rp.get("riscos_com_rota_preventiva", [])): e.append(f"(g) rotas_preventivas: riscos_com_rota_preventiva={rp.get('riscos_com_rota_preventiva')} ≠ riscos das linhas preventivas {sorted(riscos)}")
    except FileNotFoundError:
        e.append("(g) rotas_preventivas.json ausente")
    # 15/09/2026 (correção do portão): o texto do motor vem do parâmetro `motor` — reler do disco aqui anulava o teste negativo "motor lendo financiamento"
    if "rotas_preventivas" in motor or "financiamento/fogo" in motor: e.append("(h) motor do índice lê dados da rota preventiva do fogo")
    if re.search(r"financiamento/", motor): e.append("(f) recalcular_mare.py referencia data/financiamento/")
    # 15/09/2026 (handover "dinheiro preventivo por setor"): (i) preventivo_setores.json — toda rota com base_legal, chave, destino e objeto válidos;
    # fonte/hash obrigatórios quando verificado_em está preenchido; (j) zero <table> em financiamento.html; (k) alternativa <dl> da figura;
    # (l) nó de ausência da seca presente e com o enunciado restrito; (m) o motor nunca lê preventivo_setores.
    try:
        ps = json.loads((FIN / "preventivo_setores.json").read_text(encoding="utf-8"))
        for st in ps.get("setores", []):
            for r in st.get("rotas", []):
                for k in ("id", "nome", "origem", "destino", "chave", "objeto", "base_legal", "defeso"):
                    if not r.get(k): e.append(f"(i) preventivo_setores: rota {r.get('id')} sem {k}")
                if r.get("chave") not in {"regra", "decreto", "discricionaria", "direta"}: e.append(f"(i) preventivo_setores: chave inválida em {r.get('id')}")
                if r.get("objeto") not in {"preventivo", "resposta"}: e.append(f"(i) preventivo_setores: objeto inválido em {r.get('id')}")
                if r.get("verificado_em") and not (r.get("fonte") and r.get("hash_evidencia")): e.append(f"(i) preventivo_setores: {r.get('id')} verificada sem fonte/hash")
                for g in r.get("glifos", []):
                    if g not in ps.get("glifos", {}): e.append(f"(i) preventivo_setores: glifo desconhecido {g} em {r.get('id')}")
        seca = next((st for st in ps.get("setores", []) if st.get("id") == "seca"), {})
        aus = (seca.get("ausencia") or {}).get("rotulo", "")
        if "rota ao município ligada a plano e a nível de risco" not in aus: e.append("(l) preventivo_setores: nó de ausência da seca ausente ou com enunciado diferente do restrito")
    except FileNotFoundError:
        e.append("(i) preventivo_setores.json ausente")
    if re.search(r"<table\b", html): e.append("(j) financiamento.html contém <table> — a página não tem tabelas (decisão editorial de 15/09/2026)")
    if 'id="dlPreventivoSetor"' not in html: e.append("(k) figura do dinheiro preventivo sem alternativa <dl>")
    if "preventivo_setores" in motor: e.append("(m) motor do índice lê preventivo_setores.json")
    d = serie.get("defeso", {})
    if not (d.get("inicio") == "2026-07-04" and d.get("fim") == "2026-10-25" and "73" in str(d.get("base", ""))): e.append("(g) faixa do defeso ausente ou incompleta na série")
    for nome, t in arquivos_fin.items():
        m = AUTOR.search(t)
        if m: e.append(f"(h) E10: campo de autor em {nome}: {m.group(1)}")
    return e


def carregar():
    j = lambda p: json.load(open(p, encoding="utf-8"))
    arqs = {p.name: p.read_text(encoding="utf-8") for p in FIN.glob("*.json")}
    return (ler_pagina(RAIZ / "financiamento.html"), j(FIN / "rotas.json"), j(FIN / "serie_nacional.json"), j(FIN / "por_uf.json"),
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
        "figura sem crédito": lambda: checar(html.replace("fonteFigura('boxRede'", "fonteFigura('boxX'"), rotas, serie, poruf, motor, arqs),
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
