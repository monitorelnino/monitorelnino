#!/usr/bin/env python3
"""
verificar_saude.py — portão 5 (v2.2.4, §9.6)
============================================
Prova, bloqueando a publicação se falhar:
 (a) toda figura de saude.html tem crédito com órgão+documento+data (via fonteFigura);
 (b) nenhuma chave de saude_* é lida por recalcular_mare.py nem aparece em indice.json;
 (c) vocabulário fechado em saude_uf.json (status e consist);
 (d) nenhuma frase preditiva em primeira pessoa na página;
 (e) "não localizamos" em saude_uf só com bateria estadual datada (LAC exige data_verificacao e log_ref);
 (f) lacunas exibidas como ausência declarada (fontes não coletadas têm status de lacuna, não valores);
 (g) registros de emergência nunca em categoria pontuável;
 (h) crédito InfoDengue presente onde a fonte é usada.
Uso: python verificar_saude.py [--negativos] (os testes negativos quebram cópias em memória e exigem falha).
"""
import json, pathlib, re, sys

RAIZ = pathlib.Path(__file__).parent
D = RAIZ / "data"
VOCAB = {"NOVO", "READ", "VIG", "ELAB", "LAC", "NAO_VERIFICADO"}
CONSIST = {"COBRE", "PARCIAL", "DIFERE", "SEM", "NEUTRO"}
PREDITIVAS = re.compile(r"\b(prevemos|projetamos|estimamos|acreditamos que (?:haver|vai)|vai haver|haverá surto|epidemia (?:vai|deve))\b", re.I)


def checar(html: str, suf: dict, ssin: dict, sfed: dict, motor: str, indice: dict, atos: dict) -> list:
    erros = []
    # (a) crédito por figura: cada cartão com svg/canvas precisa de chamada fonteFigura(id)
    caixas = re.findall(r'<div class="(?:map-box|chart-box)[^"]*" id="([^"]+)"', html)
    for cid in caixas:
        if f"fonteFigura('{cid}'" not in html:
            erros.append(f"(a) figura sem crédito de fonte: #{cid}")
    # (b) peso zero
    if re.search(r"saude_(uf|sinais|federal)", motor):
        erros.append("(b) recalcular_mare.py referencia saude_*")
    if re.search(r"saude", json.dumps(indice, ensure_ascii=False), re.I):
        erros.append("(b) indice.json contém chave/valor de saúde")
    # (c) vocabulário
    for uf, u in suf.get("uf", {}).items():
        if u.get("status") not in VOCAB: erros.append(f"(c) status fora do vocabulário em {uf}: {u.get('status')}")
    # (m) Monitor Saúde v0.1 (§31): número só para UF verificada; prontidão = média dos dois sub-elementos; motor não o lê
    try:
        _ms = json.load(open(RAIZ / "data" / "monitor_saude.json", encoding="utf-8"))
        for uf, m in (_ms.get("ufs") or {}).items():
            st = (m.get("instrumento") or {}).get("status")
            if st == "NAO_VERIFICADO" and m.get("prontidao") is not None: erros.append(f"(m) monitor_saude: {uf} não verificada com número")
            if st != "NAO_VERIFICADO" and m.get("prontidao") is not None:
                pi = (m.get("instrumento") or {}).get("pontos"); pa = (m.get("antecipacao") or {}).get("pontos")
                if pi is None or pa is None or abs(m["prontidao"] - round(0.5 * pi + 0.5 * pa, 1)) > 0.05: erros.append(f"(m) monitor_saude: {uf} prontidão não é a média dos sub-elementos")
        if "monitor_saude" in motor: erros.append("(m) recalcular_mare.py referencia monitor_saude (proibido)")
    except FileNotFoundError:
        erros.append("(m) data/monitor_saude.json ausente")
        if u.get("consist") not in CONSIST: erros.append(f"(c) consist fora do vocabulário em {uf}: {u.get('consist')}")
        # (e) LAC exige bateria datada e referência de log
        if u.get("status") == "LAC" and not (u.get("data_verificacao") and u.get("log_ref")):
            erros.append(f"(e) {uf} está LAC sem bateria estadual datada (data_verificacao + log_ref)")
        # (g) natureza_doc 'resposta_registro' nunca com status pontuável-like (NOVO/READ/VIG)
        if u.get("natureza_doc") == "resposta_registro" and u.get("status") in ("NOVO", "READ", "VIG"):
            erros.append(f"(g) {uf}: registro de resposta classificado como instrumento ex-ante")
    if len(suf.get("uf", {})) != 27: erros.append("(c) saude_uf.json não tem 27 UFs")
    # (d) preditivas
    texto = re.sub(r"<script.*?</script>", "", html, flags=re.S)
    if PREDITIVAS.search(texto): erros.append("(d) frase preditiva em primeira pessoa na página")
    # (f) lacunas: fonte não coletada não pode ter valores
    for k, f in ssin.get("fontes", {}).items():
        if f.get("status") in ("a_verificar", "aguardando_primeira_coleta") and f.get("valores"):
            erros.append(f"(f) fonte {k} em lacuna com valores preenchidos")
    for c in sfed.get("cartoes", []):
        if c.get("status") == "anunciado_nao_localizado" and c.get("url"):
            erros.append(f"(f) cartão federal 'não localizado' com URL: {c.get('titulo')[:40]}")
    # (h) crédito InfoDengue
    if ssin.get("dengue_capitais"):
        for uf, d in ssin["dengue_capitais"].items():
            if "InfoDengue" not in str(d.get("fonte", "")): erros.append(f"(h) dengue {uf} sem crédito InfoDengue")
    if "InfoDengue (Fiocruz/FGV)" not in html: erros.append("(h) página sem o crédito 'InfoDengue (Fiocruz/FGV)'")
    # (g) atos de resposta sanitários nunca em municipios.json pontuável — checado por causa
    for e in atos.get("eventos", []):
        if re.search(r"espin|dengue|calor", str(e.get("causa", "")), re.I) and e.get("categoria") in ("plano", "plano_antigo", "plano_elaboracao", "coberto_estadual"):
            erros.append(f"(g) ato sanitário de resposta com categoria pontuável: {e.get('nome')}/{e.get('uf')}")
    return erros


def carregar():
    j = lambda n: json.load(open(D / n, encoding="utf-8"))
    return (open(RAIZ / "saude.html", encoding="utf-8").read(), j("saude_uf.json"), j("saude_sinais.json"),
            j("saude_federal.json"), open(RAIZ / "recalcular_mare.py", encoding="utf-8").read(), j("indice.json"), j("atos_resposta.json"))


def negativos() -> int:
    import copy
    html, suf, ssin, sfed, motor, idx, atos = carregar()
    casos = {
        "status fora do vocabulário": lambda: checar(html, {**suf, "uf": {**suf["uf"], "SC": {**suf["uf"]["SC"], "status": "TALVEZ"}}}, ssin, sfed, motor, idx, atos),
        "LAC sem bateria datada": lambda: checar(html, {**suf, "uf": {**suf["uf"], "SC": {**suf["uf"]["SC"], "status": "LAC"}}}, ssin, sfed, motor, idx, atos),
        "motor lendo saude_uf": lambda: checar(html, suf, ssin, sfed, motor + "\nx = 'saude_uf.json'", idx, atos),
        "frase preditiva": lambda: checar(html.replace("</main>", "<p>Prevemos surto em outubro.</p></main>"), suf, ssin, sfed, motor, idx, atos),
        "cartão não localizado com URL": lambda: checar(html, suf, ssin, {"cartoes": [{"titulo": "X", "status": "anunciado_nao_localizado", "url": "https://x"}]}, motor, idx, atos),
        "figura sem crédito": lambda: checar(html.replace("fonteFigura('boxStatus'", "fonteFigura('boxOutro'"), suf, ssin, sfed, motor, idx, atos),
    }
    falhas = 0
    for nome, fn in casos.items():
        ok = bool(fn()); print(("  ✓ " if ok else "  ✗ ") + f"negativo acusado: {nome}"); falhas += (not ok)
    return 1 if falhas else 0


if __name__ == "__main__":
    if "--negativos" in sys.argv:
        sys.exit(negativos())
    e = checar(*carregar())
    if e:
        print("✗ SAÚDE: publicação bloqueada:"); [print("   ", x) for x in e]; sys.exit(1)
    print("✓ SAÚDE OK — 27 UFs no vocabulário, peso zero provado no motor e no índice, créditos por figura, lacunas declaradas.")
