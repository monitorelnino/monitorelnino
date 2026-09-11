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
import hashlib, io, mimetypes, re, sys, urllib.error
from pathlib import Path
from coletores_base import buscar, preservar_evidencia, ler, gravar, registrar_lacuna, log_busca, EVID

LIMITE_PDF_COPIA = 5 * 1024 * 1024   # cópia do binário só até 5 MB; o TEXTO extraído é guardado sempre


def extrair_texto_por_pagina(pdf_bytes: bytes) -> list:
    """Lista de textos, um por página (pypdf; pdfplumber como reserva na página vazia). Função pura."""
    paginas = []
    try:
        from pypdf import PdfReader
        rd = PdfReader(io.BytesIO(pdf_bytes))
        for pg in rd.pages:
            try: paginas.append((pg.extract_text() or "").strip())
            except Exception: paginas.append("")  # noqa: BLE001
    except Exception:  # noqa: BLE001
        return []
    if paginas and sum(len(t) for t in paginas) < 200:
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                paginas = [(pg.extract_text() or "").strip() for pg in pdf.pages]
        except Exception:  # noqa: BLE001
            pass
    return paginas


def gravar_texto(h: str, paginas: list) -> str:
    """evidencias/<sha256>.txt com marcador de página; devolve o hash do texto."""
    EVID.mkdir(exist_ok=True)
    txt = "".join(f"\n=== página {i+1} ===\n{t}\n" for i, t in enumerate(paginas))
    (EVID / f"{h}.txt").write_text(txt, encoding="utf-8")
    return hashlib.sha256(txt.encode("utf-8")).hexdigest()


def ler_pdfs(limite: int = 40) -> int:
    """§10.1 peça 1: para todo item do índice com URL de PDF sem texto (e para registros com URL de PDF ainda sem hash),
    baixa com o UA do Monitor, extrai o texto por página, grava evidencias/<sha>.txt e indexa (texto_arquivo, paginas, texto_hash).
    Sítio que recusa (401/403) → decisão 'acesso recusado' no log (candidato a pedido de LAI)."""
    idx = ler("evidencias.json", {"itens": {}}); itens = idx.setdefault("itens", {})
    # 11/09/2026: `not it.get("texto_arquivo")` já exclui itens de texto manual (texto_manual), que registram
    # texto_arquivo apontando para o próprio arquivo preservado — reextrair sobrescreveria evidencias/<h>.txt sob
    # o mesmo nome e violaria o portão de integridade (sha256(arquivo) == chave). Explicitado por segurança.
    alvos = [(h, it) for h, it in itens.items() if str(it.get("url", "")).lower().split("?")[0].endswith(".pdf") and not it.get("texto_arquivo") and not it.get("texto_manual")]
    # registros estaduais/municipais com URL .pdf ainda sem hash
    for reg, fonte in ((ler("estados.json", {}).get("ufs") or [], "estados"), (ler("municipios.json", []) or [], "municipios")):
        for r in reg:
            u = str(r.get("url") or ""); 
            if u.lower().split("?")[0].endswith(".pdf") and not r.get("hash_evidencia") and all(it.get("url") != u for it in itens.values()):
                alvos.append((None, {"url": u, "origem": f"ler_pdfs/{fonte}", "_reg": r}))
    lidos = recusados = falhas = 0
    for h, it in alvos[:limite]:
        u = it["url"]
        try:
            bruto = buscar(u, timeout=90)
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                recusados += 1; log_busca("site_municipal", 2, [u], "acesso recusado", resultados=f"HTTP {e.code} ao ler PDF — candidato a pedido de LAI")
            else:
                falhas += 1; registrar_lacuna(f"leitura de PDF {u[:60]}", f"HTTP {e.code}", canal="DOM", camada=2, strings=[u])
            continue
        except Exception as e:  # noqa: BLE001
            falhas += 1; registrar_lacuna(f"leitura de PDF {u[:60]}", type(e).__name__, canal="DOM", camada=2, strings=[u]); continue
        if bruto[:4] != b"%PDF":
            falhas += 1; registrar_lacuna(f"leitura de PDF {u[:60]}", "resposta não é PDF", canal="DOM", camada=2, strings=[u]); continue
        h_novo = hashlib.sha256(bruto).hexdigest()
        if h is None:
            h = preservar_evidencia(bruto, u, "pdf", it["origem"]); it = itens.get(h, it)
            if it.get("_reg") is not None: it["_reg"]["hash_evidencia"] = h
        elif h_novo != h:
            registrar_lacuna(f"leitura de PDF {u[:60]}", f"documento mudou desde o hash registrado ({h[:12]}… → {h_novo[:12]}…)", canal="DOM", camada=2, strings=[u])
        paginas = extrair_texto_por_pagina(bruto)
        if not paginas:
            falhas += 1; registrar_lacuna(f"leitura de PDF {u[:60]}", "PDF sem texto extraível (imagem?)", canal="DOM", camada=2, strings=[u]); continue
        th = gravar_texto(h, paginas)
        item = itens.setdefault(h, {"url": u, "origem": it.get("origem"), "preservado_em": None, "tamanho": len(bruto), "arquivo": None, "wayback": None})
        item.update({"texto_arquivo": f"evidencias/{h}.txt", "paginas": len(paginas), "texto_hash": th, "lido_em": __import__("datetime").date.today().isoformat(), "caracteres": sum(len(t) for t in paginas)})
        if len(bruto) <= LIMITE_PDF_COPIA and not item.get("arquivo"):
            (EVID / f"{h}.pdf").write_bytes(bruto); item["arquivo"] = f"evidencias/{h}.pdf"
        lidos += 1
    for it in itens.values(): it.pop("_reg", None)
    gravar("evidencias.json", idx)
    print(f"leitura de PDFs: {lidos} lido(s) com texto, {recusados} acesso recusado (LAI), {falhas} falha(s); {len(alvos)} alvo(s) na fila")
    return 0


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
        if (idx.get("itens") or {}).get(h, {}).get("texto_manual"):
            # 11/09/2026: item cuja chave é o sha256 do TEXTO preservado (extração manual), não do binário de origem.
            # Comparar com o hash do PDF rebaixado divergiria SEMPRE e publicaria um evento falso de
            # "documento-fonte alterado". Alteração desses itens é reconferida por leitura humana.
            continue
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
    sys.exit(ler_pdfs(lim) if "--ler" in sys.argv else reconferir(lim) if "--reconferir" in sys.argv else main(lim))
