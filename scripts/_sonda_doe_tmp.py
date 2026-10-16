"""Sonda temporária 4 (ramo diag, não vai à main): PI (diario.pi.gov.br/doe) e RR (_visualizar-mes, _buscar)."""
import io, json, re, sys, time, urllib.error, urllib.parse
sys.path.insert(0, ".")
from coletores_base import buscar_uma_vez  # noqa: E402


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
        b = buscar_uma_vez(u, timeout=timeout, origem="sonda DOE", **({"dados": data} if data else {}))
    except TypeError:
        b = buscar_uma_vez(u, timeout=timeout, origem="sonda DOE")
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
            s["inicio"] = t[:1500]
    print(json.dumps(s, ensure_ascii=False), flush=True)
    return b


# RR: a página do mês — onde estão as edições (link de PDF, id, onclick)?
get("RR", "https://www.imprensaoficial.rr.gov.br/_visualizar-mes/?ano=2026&mes=10", r"\.pdf|_visualizar-doe|onclick|data-|edi[cç][aã]o")
get("RR", "https://www.imprensaoficial.rr.gov.br/_buscar/?termos=decreto&ano_pesquisa=2026&mes_pesquisa=10", r"\.pdf|_visualizar|resultado|decreto")
get("RR", "https://www.imprensaoficial.rr.gov.br/_visualizar/?ano=2026", r"\.pdf|_visualizar-mes|_visualizar-doe")
# PI: a página de busca e o JavaScript que alimenta a tabela
get("PI", "https://www.diario.pi.gov.br/doe/busca", r"ajax|url\s*:|\.pdf|fetch\(|\$\.(get|post)|action=")
get("PI", "https://www.diario.pi.gov.br/doe/", r"ajax|url\s*:|\.pdf|fetch\(|\$\.(get|post)|/doe/[a-z_]+")
