#!/usr/bin/env python3
"""
verificar_resposta.py — portão do contador de resposta (v3.1 §3.3, 06/09/2026)
(a) recalcular_mare.py não lê data/resposta/;
(b) estresse: com data/resposta/ inteiro ausente, o índice recomputado é idêntico (nenhuma nota, nenhuma faixa);
(c) nenhum campo composto antecipação×resposta em data/ ou nas páginas;
(d) fatia em_classificacao nunca imputada (sem adaptador: apos/antes = 0 e em_classificacao = n);
(e) frase C18 presente em toda superfície do contador (arquivos de resposta e páginas que o exibem);
(f) frações de municípios e população recomputadas = publicadas;
(g) todo evento com fonte, data e hash/URL.
"""
import json, pathlib, re, shutil, subprocess, sys, tempfile
RAIZ = pathlib.Path(__file__).parent; D = RAIZ / "data"
erros = []
def erro(m): erros.append(m)
try:
    motor = (RAIZ / "recalcular_mare.py").read_text(encoding="utf-8")
    if re.search(r"resposta/|data/resposta|por_uf\.json", motor): erro("(a) recalcular_mare.py referencia data/resposta")
    # (b) estresse
    with tempfile.TemporaryDirectory() as tmp:
        T = pathlib.Path(tmp) / "repo"
        shutil.copytree(RAIZ, T, ignore=shutil.ignore_patterns("node_modules", ".git", "evidencias"))
        shutil.rmtree(T / "data" / "resposta", ignore_errors=True)
        antes = json.load(open(D / "indice.json", encoding="utf-8"))
        r = subprocess.run([sys.executable, "recalcular_mare.py", "--write"], cwd=T, capture_output=True, text=True)
        if r.returncode != 0: erro(f"(b) recalcular falhou sem data/resposta: {r.stderr[-200:]}")
        depois = json.load(open(T / "data" / "indice.json", encoding="utf-8"))
        dif = [uf for uf in antes if antes[uf].get("total") != depois.get(uf, {}).get("total") or antes[uf].get("estado") != depois.get(uf, {}).get("estado")]
        if dif: erro(f"(b) estresse: notas mudaram sem data/resposta: {dif}")
    # (c) composto
    PAD = re.compile(r"nota_menos_decreto|indice_de_contradicao|contradicao_antecipacao|antecipacao_x_resposta|resposta_x_antecipacao|composto_resposta|nota_ajustada_resposta", re.I)
    for p in list(D.rglob("*.json")) + list(RAIZ.glob("*.html")):
        t = p.read_text(encoding="utf-8", errors="replace")
        if PAD.search(t): erro(f"(c) campo composto antecipação×resposta em {p.relative_to(RAIZ)}")
    por = json.load(open(D / "resposta" / "por_uf.json", encoding="utf-8")); mun = json.load(open(D / "resposta" / "municipios.json", encoding="utf-8"))["municipios"]
    frase = por.get("frase_c18", "")
    # (d)
    for uf, v in por["uf"].items():
        f = v["fatias"]
        if f["apos_evento"] or f["antes_com_previsao"]: erro(f"(d) {uf}: fatia de evento observado imputada sem adaptador")
        if f["em_classificacao"] != v["n_municipios"]: erro(f"(d) {uf}: em_classificacao ≠ n_municipios")
    # (e) frase C18: arquivos e páginas com superfície do contador
    for p in (D / "resposta").glob("*.json"):
        if "art. 73, VI, a" not in p.read_text(encoding="utf-8"): erro(f"(e) frase C18 ausente em {p.name}")
    for pg in ("index.html", "defesa-civil.html"):
        f = RAIZ / pg
        if f.exists():
            t = f.read_text(encoding="utf-8")
            if ("contadorResposta" in t or "resposta/por_uf" in t) and "art. 73, VI" not in t: erro(f"(e) {pg} exibe o contador sem a frase C18")
    # (f) frações
    pop = json.load(open(D / "populacao_censo2022.json", encoding="utf-8"))
    for uf, v in por["uf"].items():
        ms = [m for m in mun.values() if m["uf"] == uf]; com = [m for m in ms if m["decreto"]]
        fm = round(len(com) / len(ms), 4) if ms else 0
        pu = sum(float(pop.get(m["ibge"], 0) or 0) for m in ms); pd = sum(float(pop.get(m["ibge"], 0) or 0) for m in com)
        fp = round(pd / pu, 4) if pu else 0
        if fm != v["fracao_municipios"] or fp != v["fracao_populacao"]: erro(f"(f) {uf}: fração publicada ≠ recomputada ({v['fracao_municipios']}/{fm}, {v['fracao_populacao']}/{fp})")
    # (g)
    atos = json.load(open(D / "atos_resposta.json", encoding="utf-8"))["eventos"]
    sem = [e for e in atos if not (e.get("fonte") and e.get("data") and (e.get("url") or e.get("hash_evidencia")))]
    if sem: erro(f"(g) {len(sem)} evento(s) sem fonte/data/URL-ou-hash")
except Exception as e:  # noqa: BLE001
    erro(f"portão falhou ao executar: {e}")
if erros:
    print("✗ RESPOSTA:"); [print("   -", e) for e in erros]; sys.exit(1)
print("✓ RESPOSTA OK — peso zero provado por estresse, sem composto, fatias não imputadas, frações reproduzidas, eventos com fonte.")
