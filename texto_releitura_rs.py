"""Releitura de planos do Prepara RS com OCR página a página e correção de orientação (23/11/2026; não vai à
main). Página sem camada de texto vai ao OCR mesmo quando o resto do PDF tem texto. Redige CPF, telefone e
e-mail pessoal antes de gravar. Uso: python3 texto_releitura_rs.py <id> [<id> ...]."""
import io, json, re, sys, time, pathlib
sys.path.insert(0, "scripts")
import julgar_e_aplicar_descobertas as j
import preservar_evidencias as pe
ids = set(sys.argv[1:])
d = json.load(open("data/pistas_imprensa.json"))["pistas"]
alvo = [p for p in d if str(p.get("id")) in ids]
CPF = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}[-\s.]?\d{2}\b")
FONE = re.compile(r"(?:\(?\b\d{2}\)?[\s.-]?)?\b9\d{4}[\s.-]?\d{4}\b|\(\d{2}\)\s?\d{4}[\s.-]?\d{4}\b|\b\d{4}-\d{4}\b")
MAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
def redigir(t):
    t = CPF.sub("[CPF]", t)
    t = MAIL.sub(lambda m: m.group(0) if m.group(0).lower().endswith(".gov.br") else "[E-MAIL]", t)
    return FONE.sub("[TEL]", t)
exe = pe.tesseract_disponivel(); _, idioma = pe.motor_ocr(exe)
def paginas_pdf(raw):
    import pdfplumber, pypdfium2 as pdfium
    doc = pdfium.PdfDocument(io.BytesIO(raw))
    with pdfplumber.open(io.BytesIO(raw)) as pdf:
        for i, pg in enumerate(pdf.pages):
            t = pg.extract_text() or ""
            ocr = len(re.findall(r"[A-Za-zÀ-ú]", t)) < 200 or pe.legibilidade(t) < pe.LEGIBILIDADE_MINIMA
            if ocr and i < 150:
                buf = io.BytesIO(); doc[i].render(scale=pe.OCR_DPI / 72).to_pil().save(buf, format="PNG")
                t2 = pe.ocr_pagina(buf.getvalue(), exe, idioma)
                if len(t2) > len(t): t = t2
            yield i + 1, ocr, t
out = []
for p in alvo:
    url = p.get("url_final") or p.get("url")
    reg = {"pista_id": p.get("id"), "municipio": p.get("municipio"), "url": url}
    t0 = time.time()
    try:
        raw = j.obter_documento(url, 120, "releitura dos planos do Prepara RS")
        reg["bytes"] = len(raw); reg["magica"] = raw[:8].hex()
        if raw[:5] == b"%PDF-":
            pags = list(paginas_pdf(raw))
            reg["paginas"] = len(pags); reg["paginas_ocr"] = [n for n, o, _ in pags if o]
            texto = "\n".join(f"[página {n}] {t}" for n, _, t in pags)
        else:
            texto = j.com_ocr(raw, j.texto_do_documento(raw, url))
    except Exception as e:
        reg["erro"] = f"{type(e).__name__}: {str(e)[:160]}"; texto = ""
    reg["texto"] = redigir(re.sub(r"[ \t]+", " ", texto or "")).strip()
    reg["segundos"] = round(time.time() - t0, 1)
    out.append(reg)
    print(f"{reg['municipio']}: {len(reg['texto'])} car., {reg.get('paginas')} pág., OCR em {len(reg.get('paginas_ocr') or [])} {reg.get('erro') or ''}", flush=True)
# O texto não vai em claro para o ramo (repositório público): sai cifrado com a chave pública da sessão.
import os, subprocess, tempfile
pasta = pathlib.Path("data/textos_prepara_rs"); pasta.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory() as tmp:
    k = pathlib.Path(tmp, "k"); k.write_bytes(os.urandom(32).hex().encode())
    claro = pathlib.Path(tmp, "c"); claro.write_text(json.dumps(out, ensure_ascii=False))
    subprocess.run(["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-salt", "-in", claro, "-out", pasta / "releitura.enc",
                    "-pass", f"file:{k}"], check=True)
    subprocess.run(["openssl", "pkeyutl", "-encrypt", "-pubin", "-inkey", "releitura_pub.txt", "-in", k,
                    "-out", pasta / "releitura.chave"], check=True)
print("CIFRADO", (pasta / "releitura.enc").stat().st_size, "bytes")
