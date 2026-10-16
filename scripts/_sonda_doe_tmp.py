"""Sonda temporária (ramo diag): página do MIDR do Cadastro Nacional (art. 3º-A) — links, data, Power BI."""
import hashlib, json, re, sys
sys.path.insert(0, ".")
from coletores_base import buscar_uma_vez  # noqa: E402
U = "https://www.gov.br/mdr/pt-br/assuntos/protecao-e-defesa-civil/cadastro-nacional-de-municipios"
b = buscar_uma_vez(U, timeout=60, origem="sonda cadastro")
t = b.decode("utf-8", "replace")
print(json.dumps({"bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()}))
for m in re.finditer(r'href="([^"]+)"', t):
    h = m.group(1)
    if re.search(r"\.pdf|powerbi|governa|nota|NT|casacivil|cadastro", h, re.I):
        print("HREF", h)
for pad in (r"[Aa]tualizado em[^<]{0,40}", r"[Pp]ublicado em[^<]{0,40}", r"2\.?095[^<]{0,80}", r"inscri[çc][ãa]o[^<]{0,120}", r"cadastrados[^<]{0,160}"):
    for m in re.finditer(pad, t):
        print("TXT", " ".join(m.group(0).split())[:200])
for h in re.findall(r'href="([^"]+\.pdf)"', t):
    u = h if h.startswith("http") else "https://www.gov.br" + h
    try:
        p = buscar_uma_vez(u, timeout=90, origem="sonda cadastro")
        print("PDF", u, len(p), hashlib.sha256(p).hexdigest())
    except Exception as e:  # noqa: BLE001
        print("PDF-ERRO", u, type(e).__name__, str(e)[:120])
