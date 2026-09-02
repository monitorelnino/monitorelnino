#!/usr/bin/env python3
"""
verificar_painel.py — portão 15 (v2.3, §10-bis / E11)
=======================================================
 (a) lista IMUTÁVEL: hash publicado == hash recomputado da lista de códigos; semente registrada;
 (b) 313 municípios: 12 por UF, DF = 1 (exceção declarada); nenhuma capital fora da exceção;
 (c) Ponte Serrada/SC (4213401) presente (decisão registrada);
 (d) toda ficha com fontes e data; mesmas colunas nas 313; nenhum valor de rota imputado
     (rotas_status aguardando_coleta ⇒ valores nulos);
 (e) marcadores: lista arquivada com hash e fonte para cada marcador declarado disponível;
     indisponíveis declarados, não imputados;
 (f) nada de data/painel/ lido por recalcular_mare.py;
 (g) agregados = contagem das fichas (paridade).
Uso: python3 verificar_painel.py [--negativos]
"""
import hashlib, json, pathlib, re, sys

RAIZ = pathlib.Path(__file__).parent; D = RAIZ / "data"; P = D / "painel"
UFS = "AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO".split()


def checar(lista, fichas, agregados, motor, marcadores: dict, caps: set) -> list:
    e = []
    ibges = [m["ibge"] for m in lista["municipios"]]
    if hashlib.sha256(json.dumps(ibges).encode()).hexdigest() != lista.get("hash_lista"): e.append("(a) hash da lista não confere com os códigos publicados")
    if not lista.get("semente") or not lista.get("lista_publicada_em"): e.append("(a) semente ou data de publicação ausentes")
    if len(ibges) != len(set(ibges)): e.append("(b) códigos repetidos na lista")
    for uf in UFS:
        n = sum(1 for m in lista["municipios"] if m["uf"] == uf); esp = 1 if uf == "DF" else 12
        if n != esp: e.append(f"(b) {uf}: {n} municípios (esperado {esp})")
    for m in lista["municipios"]:
        if (m["nome"], m["uf"]) in caps and not m.get("excecao"): e.append(f"(b) capital no painel sem exceção declarada: {m['nome']}/{m['uf']}")
    if "4213401" not in ibges: e.append("(c) Ponte Serrada/SC ausente")
    fs = fichas["fichas"]; cols = None
    if len(fs) != len(ibges) or {f["ibge"] for f in fs} != set(ibges): e.append("(d) fichas não cobrem exatamente a lista")
    for f in fs:
        c = tuple(sorted(f.keys()))
        if cols is None: cols = c
        elif c != cols: e.append(f"(d) colunas diferentes na ficha de {f['nome']}/{f['uf']}"); break
        if not f.get("fontes") or not f.get("data_ficha"): e.append(f"(d) ficha sem fonte/data: {f['nome']}/{f['uf']}"); break
        if f.get("rotas_status") == "aguardando_coleta" and any(v is not None for v in list(f["rotas_2025"].values()) + list(f["rotas_2026"].values())): e.append(f"(d) valor de rota imputado: {f['nome']}/{f['uf']}"); break
    for m in lista.get("marcadores_disponiveis", []):
        a = marcadores.get(m)
        if not a or not a.get("hash_lista") or not a.get("fonte", {}).get("sha256_documento"): e.append(f"(e) marcador '{m}' sem lista arquivada com hash e fonte")
        elif hashlib.sha256(json.dumps(sorted(a["ibge"])).encode()).hexdigest() != a["hash_lista"]: e.append(f"(e) marcador '{m}': hash da lista arquivada não confere")
    if re.search(r"painel/", motor): e.append("(f) recalcular_mare.py referencia data/painel/")
    if agregados.get("hash_lista") != lista.get("hash_lista"): e.append("(g) agregados de outra lista")
    if sum(a["n"] for a in agregados["agregados"]) != len(fs): e.append("(g) soma dos agregados ≠ nº de fichas")
    return e


def carregar():
    j = lambda p: json.load(open(p, encoding="utf-8"))
    marc = {p.stem.replace("marcador_", ""): j(p) for p in P.glob("marcador_*.json")}
    est = j(D / "estados.json")["ufs"]; caps = {(u["capital"]["nome"] if isinstance(u.get("capital"), dict) else u.get("capital"), u["uf"]) for u in est}
    return j(P / "lista.json"), j(P / "fichas.json"), j(P / "agregados.json"), open(RAIZ / "recalcular_mare.py", encoding="utf-8").read(), marc, caps


def negativos():
    import copy
    lista, fichas, ag, motor, marc, caps = carregar()
    def troca():
        l = copy.deepcopy(lista); l["municipios"][0]["ibge"] = "9999999"; return checar(l, fichas, ag, motor, marc, caps)
    def capital():
        l = copy.deepcopy(lista); l["municipios"][0].update({"nome": "Florianópolis", "uf": "SC"}); l["municipios"][0].pop("excecao", None); return checar(l, fichas, ag, motor, marc, caps)
    def motor_le(): return checar(lista, fichas, ag, motor + "\nx='data/painel/lista.json'", marc, caps)
    def imputado():
        f = copy.deepcopy(fichas); f["fichas"][0]["rotas_2026"]["r1"] = 100; return checar(lista, f, ag, motor, marc, caps)
    def marcador_adulterado():
        m = copy.deepcopy(marc); m["geo_hidrologico"]["ibge"] = m["geo_hidrologico"]["ibge"][:-1]; return checar(lista, fichas, ag, motor, m, caps)
    f = 0
    for n, fn in {"lista alterada (hash)": troca, "capital sem exceção": capital, "motor lendo painel": motor_le, "valor de rota imputado": imputado, "lista de marcador adulterada": marcador_adulterado}.items():
        ok = bool(fn()); print(("  ✓ " if ok else "  ✗ ") + "negativo acusado: " + n); f += (not ok)
    return 1 if f else 0


if __name__ == "__main__":
    if "--negativos" in sys.argv: sys.exit(negativos())
    e = checar(*carregar())
    if e:
        print("✗ PAINEL: publicação bloqueada:"); [print("   ", x) for x in e]; sys.exit(1)
    print("✓ PAINEL OK — lista imutável (hash), 313 municípios (12 por UF, DF = 1), sem capitais, Ponte Serrada presente, fichas com fonte e data, marcadores arquivados, motor intacto, agregados em paridade.")
