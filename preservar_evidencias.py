#!/usr/bin/env python3
"""
preservar_evidencias.py (v2.2.4, §3.8)
======================================
Para cada registro PONTUÁVEL de data/municipios.json com URL e sem
`hash_evidencia`, baixa o documento, guarda em evidencias/<sha256>.<ext> (ou só
o hash + Wayback se > 5 MB), indexa em data/evidencias.json e grava o hash no
registro. Idempotente: quem já tem hash é pulado. Falha de rede = lacuna
declarada (o portão verificar_evidencias.py cobra depois). É a ÚNICA edição
programática permitida em municipios.json fora de aplicar_revisao.py, porque
não altera nenhum campo de julgamento — só acrescenta prova.
"""
import mimetypes, sys
from coletores_base import buscar, preservar_evidencia, ler, gravar, registrar_lacuna

PONT = {"plano", "plano_antigo", "plano_elaboracao", "coberto_estadual"}


def reconferir(limite: int = 200) -> int:
    """§3.8-bis: a rodada semanal REBAIXA e COMPARA o hash dos documentos-fonte já preservados.
    Hash diferente = 'documento-fonte alterado em dd/mm': entrada no log, marca em
    data/evidencias.json (alterado_em, hash_novo) e evento no feed (tipo documento_alterado).
    Nunca altera a categoria do registro — isso é julgamento humano."""
    from datetime import date
    mun = ler("municipios.json"); idx = ler("evidencias.json", {"itens": {}}); n = alt = falhas = 0
    for m in mun:
        h = m.get("hash_evidencia")
        if not h or not str(m.get("url", "")).startswith("http") or n + falhas >= limite: continue
        try:
            bruto = buscar(m["url"], timeout=45)
        except Exception as e:  # noqa: BLE001
            falhas += 1; continue
        n += 1; h2 = __import__("hashlib").sha256(bruto).hexdigest()
        if h2 != h:
            alt += 1; hoje = date.today().strftime("%d/%m/%Y")
            it = idx["itens"].setdefault(h, {}); it["alterado_em"] = hoje; it["hash_novo"] = h2; it["municipio"] = f"{m['nome']}/{m['uf']}"
            log_busca(m.get("canal") or "DOM", 2, [m["url"]], "pista", uf=m["uf"], municipio=m["nome"],
                      resultados=f"documento-fonte alterado em {hoje}: hash {h[:12]}… → {h2[:12]}… (categoria mantida; julgamento humano)")
    gravar("evidencias.json", idx)
    print(f"reconferência: {n} documento(s) rebaixado(s) e comparado(s), {alt} alterado(s), {falhas} inacessível(is)")
    return 0


def main(limite: int = 200) -> int:
    mun = ler("municipios.json"); feitos = pulados = falhas = 0
    for m in mun:
        if m.get("categoria") not in PONT or not str(m.get("url", "")).startswith("http"):
            continue
        h_ex = m.get("hash_evidencia")
        if h_ex:
            it = (ler("evidencias.json", {"itens": {}}).get("itens") or {}).get(h_ex, {})
            if it.get("arquivo") or it.get("wayback"):
                pulados += 1; continue
            # 03/09/2026: hash registrado mas cópia perdida (não comitada) → re-preserva
        if feitos + falhas >= limite:
            break
        try:
            bruto = buscar(m["url"], timeout=45)
        except Exception as e:  # noqa: BLE001
            registrar_lacuna(f"evidência {m['nome']}/{m['uf']}", f"{type(e).__name__}", canal=m.get("canal") or "DOM",
                             camada=2, uf=m["uf"], municipio=m["nome"], strings=[m["url"]]); falhas += 1
            continue
        ext = (mimetypes.guess_extension(("application/pdf" if bruto[:4] == b"%PDF" else "text/html")) or ".bin").lstrip(".")
        h_novo = __import__("hashlib").sha256(bruto).hexdigest()
        if h_ex and h_novo != h_ex:
            registrar_lacuna(f"evidência {m['nome']}/{m['uf']}", f"documento mudou desde o hash registrado ({h_ex[:12]}… → {h_novo[:12]}…)", canal=m.get("canal") or "DOM", camada=2, uf=m["uf"], municipio=m["nome"], strings=[m["url"]])
        idx = ler("evidencias.json", {"itens": {}}); idx["itens"].pop(h_ex, None) if h_ex and h_novo != h_ex else None; gravar("evidencias.json", idx)
        m["hash_evidencia"] = preservar_evidencia(bruto, m["url"], ext, "preservar_evidencias")
        feitos += 1
    gravar("municipios.json", mun)
    print(f"evidências: {feitos} preservada(s), {pulados} já tinham hash, {falhas} falha(s) de rede (lacunas no log)")
    return 0


if __name__ == "__main__":
    lim = int(sys.argv[sys.argv.index("--limite") + 1]) if "--limite" in sys.argv else 200
    sys.exit(reconferir(lim) if "--reconferir" in sys.argv else main(lim))
