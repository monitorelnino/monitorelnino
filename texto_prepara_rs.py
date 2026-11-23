"""Texto integral dos planos do Prepara RS para a leitura plano a plano (23/11/2026, pedido da editoria; não vai
à main). Redige CPF, telefone e e-mail pessoal antes de gravar. Uso: python3 texto_prepara_rs.py <k> <n>."""
import json, re, sys, time, pathlib
sys.path.insert(0, "scripts")
import julgar_e_aplicar_descobertas as j
j.PAGINAS_DE_OCR = 80
k, n = int(sys.argv[1]), int(sys.argv[2])
d = json.load(open("data/pistas_imprensa.json"))["pistas"]
rs = sorted([p for p in d if "casa-militar_casamilitar_rs_gov_br" in str(p.get("url_final") or p.get("url"))],
            key=lambda p: str(p.get("id")))[k - 1::n]
CPF = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}[-\s.]?\d{2}\b")
FONE = re.compile(r"(?:\(?\b\d{2}\)?[\s.-]?)?\b9?\d{4}[\s.-]?\d{4}\b")
MAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
def redigir(t):
    t = CPF.sub("[CPF]", t)
    t = MAIL.sub(lambda m: m.group(0) if m.group(0).lower().endswith(".gov.br") else "[E-MAIL]", t)
    return FONE.sub("[TEL]", t)
out = []
for p in rs:
    url = p.get("url_final") or p.get("url")
    reg = {"pista_id": p.get("id"), "municipio": p.get("municipio"), "ibge": p.get("ibge") or p.get("alvo"),
           "crepdec": (re.search(r"CREPDEC%20(\d+)", url) or [None, None])[1], "url": url}
    t0 = time.time()
    try:
        raw = j.obter_documento(url, 120, "leitura dos planos do Prepara RS")
        texto = j.com_ocr(raw, j.texto_do_documento(raw, url))
        reg["paginas"] = len(re.findall(rb"/Type\s*/Page[^s]", raw)) if raw[:5] == b"%PDF-" else None
    except Exception as e:
        reg["erro"] = f"{type(e).__name__}: {str(e)[:160]}"
        texto = ""
    reg["texto"] = redigir(re.sub(r"[ \t]+", " ", texto or "")).strip()
    reg["segundos"] = round(time.time() - t0, 1)
    out.append(reg)
    print(f"{len(out):3}/{len(rs)} {reg['municipio']}: {len(reg['texto'])} car. {reg.get('erro') or ''}", flush=True)
pathlib.Path("data/textos_prepara_rs").mkdir(exist_ok=True)
json.dump(out, open(f"data/textos_prepara_rs/{k}.json", "w"), ensure_ascii=False)
print("RESUMO", sum(1 for r in out if r["texto"]), "com texto de", len(out))
