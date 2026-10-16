"""Sonda temporária 4 (ramo diag, não vai à main): PI (diario.pi.gov.br/doe) e RR (_visualizar-mes, _buscar)."""
import io, json, re, sys, time, urllib.error, urllib.parse
sys.path.insert(0, ".")
from coletores_base import buscar_uma_vez, enviar_uma_vez  # noqa: E402


def pdf_info(b):
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(b)) as pdf:
            n = len(pdf.pages)
            txt = "\n".join((pdf.pages[i].extract_text() or "") for i in range(min(n, 4)))
        return {"paginas": n, "texto_4pg": len(txt), "inicio": " ".join(txt.split())[:300]}
    except Exception as e:  # noqa: BLE001
        return {"pdf_erro": f"{type(e).__name__}: {str(e)[:80]}"}


def get(uf, u, padrao=None, timeout=40, data=None, cab=None):
    t0 = time.time()
    try:
        b = enviar_uma_vez(u, data, timeout=timeout, origem="sonda DOE") if data is not None else buscar_uma_vez(u, timeout=timeout, origem="sonda DOE")
    except urllib.error.HTTPError as e:
        print(json.dumps({"uf": uf, "url": u, "http": e.code}, ensure_ascii=False), flush=True); return None
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"uf": uf, "url": u, "erro": f"{type(e).__name__}: {str(e)[:200]}"}, ensure_ascii=False), flush=True); return None
    s = {"uf": uf, "url": u, "bytes": len(b), "ms": int((time.time() - t0) * 1000)}
    if b[:5] == b"%PDF-":
        s.update(pdf_info(b))
    else:
        t = b.decode("utf-8", "replace")
        if padrao:
            s["trechos"] = [" ".join(t[max(0, m.start() - 160):m.end() + 200].split()) for m in re.finditer(padrao, t, re.I)][:25]
        else:
            s["inicio"] = t[:3000]
    print(json.dumps(s, ensure_ascii=False), flush=True)
    return b


# RR: o formulário do mês posta o caminho do PDF em _visualizar-doe/ — o que ele devolve?
R = "https://www.imprensaoficial.rr.gov.br"
get("RR", R + "/_visualizar-doe/", r"\.pdf|iframe|src=|embed|object|location", data={"doe": "2026/10/doe-20261014.pdf", "dia": "16"}, timeout=60)
for cam in ("/_docs/", "/_arquivos/", "/arquivos/", "/doe/", "/_doe/", "/docs/", "/pdf/", "/_visualizar-doe/"):
    get("RR", R + cam + "2026/10/doe-20261014.pdf", timeout=40)
get("RR", R + "/_visualizar-mes/?ano=2026&mes=10", r"<form|<input|name=|ipconexao|dia")
# PI: os campos do formulário e da tabela; a API que o JS chama
P = "https://www.diario.pi.gov.br"
get("PI", P + "/doe/busca", r"name=\"[a-z_]+\"|data\.[a-z_]+\s*=|frm-busca-avancada")
get("PI", P + "/doe/", r"data\.[a-z_]+\s*=|name=\"[a-z_]+\"|columns|render")
get("PI", P + "/Api/listardiarios.json", None, data={"draw": "1", "start": "0", "length": "3"})
get("PI", P + "/doe/Api/listardiarios.json", None, data={"draw": "1", "start": "0", "length": "3"})
