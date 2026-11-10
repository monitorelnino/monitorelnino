#!/usr/bin/env python3
"""Diagnóstico descartável (ramo diag/*, nunca mesclado): a pasta pública de PLANCONs do RS vista do runner.
Lista as pastas, casa os nomes com a malha IBGE e, para cada arquivo, mede o que cada extrator tira. Não grava nada."""
import collections, io, json, re, sys, zipfile
from pathlib import Path
from urllib.parse import unquote
sys.path.insert(0, str(Path(__file__).parent))
import atualizar_instrumentos_estaduais as aie
from julgar_e_aplicar_descobertas import _ler_sharepoint_rs, extrair_texto_pdf
from coletores_base import sessao_sharepoint

LIM = 30
s = sessao_sharepoint(aie.REPOSITORIOS["RS"]["url"], "diagnostico do repositorio estadual")
print("cookies da sessão:", sorted(c.name for c in s.cookies))
lst = json.loads(aie.listar_sharepoint(aie.REPOSITORIOS["RS"]["url"]))
pastas = collections.Counter(unquote(i["webUrl"]).split("TODOS PLANCONS RECEBIDOS/")[-1].split("/")[0] for i in lst)
print("PASTAS:", dict(sorted(pastas.items())), "total", len(lst))
ref = json.load(open("data/municipios_ibge_referencia.json", encoding="utf-8"))
ach = aie.parse_rs(json.dumps(lst)); cas, orf = aie.casar_com_ibge([dict(a) for a in ach], "RS", ref)
print(f"CASAMENTO: {len(ach)} candidatos, {len(cas)} municípios casados, {len(orf)} órfãos")
for o in orf: print("   órfão:", o["nome"], "·", unquote(o["url"]).rsplit("/", 1)[-1])
pend = {}
for p in json.load(open("data/pistas_imprensa.json", encoding="utf-8"))["pistas"]:
    if "rsgovbr" in str(p.get("url_final")):
        pend[p["url_final"]] = ",".join(sorted({t.get("motivo") or "promocao" for t in p.get("juiz_tentativas") or []}))

def chars_plumber(raw):
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            return sum(len((pg.extract_text() or "").strip()) for pg in pdf.pages[:LIM]), ""
    except Exception as e: return -1, f"{type(e).__name__}: {str(e)[:80]}"
def info_pypdf(raw):
    try:
        from pypdf import PdfReader
        r = PdfReader(io.BytesIO(raw)); enc = r.is_encrypted
        if enc:
            try: r.decrypt("")
            except Exception: pass
        n = len(r.pages); ch = 0; imgs = 0
        for pg in r.pages[:LIM]:
            try: ch += len((pg.extract_text() or "").strip())
            except Exception: pass
        try: imgs = len(r.pages[0].images)
        except Exception: imgs = -1
        return enc, n, ch, imgs, ""
    except Exception as e: return None, -1, -1, -1, f"{type(e).__name__}: {str(e)[:80]}"
def chars_pdfium(raw):
    try:
        import pypdfium2
        d = pypdfium2.PdfDocument(raw)
        return sum(len((d[i].get_textpage().get_text_range() or "").strip()) for i in range(min(len(d), LIM)))
    except Exception as e: return -1

tot = collections.Counter()
for it in lst:
    url, nome = it["webUrl"], it["name"]; ext = nome.rsplit(".", 1)[-1].lower()
    marca = pend.get(url, "—")
    try:
        raw = _ler_sharepoint_rs(url, 60)
    except Exception as e:
        tot[f"{ext}: não obtido"] += 1
        print(f"NAOOBTIDO\t{type(e).__name__}: {str(e)[:90]}\t{marca}\t{nome}"); continue
    if ext == "pdf":
        atual = extrair_texto_pdf(raw)
        pl, ple = chars_plumber(raw); enc, n, py, imgs, pye = info_pypdf(raw); pf = chars_pdfium(raw)
        k = "com texto (atual)" if atual and len(atual) >= 400 else ("sem texto atual, outro extrator lê" if max(py, pf) >= 400 else "sem texto em nenhum extrator")
        tot[f"pdf: {k}"] += 1
        if k != "com texto (atual)":
            print(f"PDF\t{k}\tbytes={len(raw)} inicio={raw[:8]!r} cifrado={enc} pags={n} img_p1={imgs} plumber={pl} {ple} pypdf={py} {pye} pdfium={pf}\t{marca}\t{nome}")
    elif ext == "url":
        alvo = re.search(rb"URL=(\S+)", raw); tot["url: atalho" + (" com alvo" if alvo else " sem alvo")] += 1
        print(f"URL\t{alvo.group(1).decode('latin-1') if alvo else raw[:120]!r}\t{marca}\t{nome}")
    elif ext == "docx":
        try:
            xml = zipfile.ZipFile(io.BytesIO(raw)).read("word/document.xml").decode("utf-8", "ignore")
            n = len(re.sub(r"<[^>]+>", "", xml).strip()); tot["docx: " + ("com texto" if n >= 400 else "sem texto")] += 1
            print(f"DOCX\tchars={n}\t{marca}\t{nome}")
        except Exception as e:
            tot["docx: ilegível"] += 1; print(f"DOCX\t{type(e).__name__}\t{marca}\t{nome}")
    else:
        tot[f"{ext}: bytes={'ok' if raw else 'vazio'}"] += 1
        print(f"{ext.upper()}\tbytes={len(raw)} inicio={raw[:8]!r}\t{marca}\t{nome}")
print("RESUMO:", json.dumps(dict(sorted(tot.items())), ensure_ascii=False))
