#!/usr/bin/env python3
"""Sonda A3, tarde de 17/10 (ramo diag, nunca mesclado): MG por data, RS, RJ, BA, MA, SE, PE."""
import base64, io, json, re, subprocess, sys, tempfile, urllib.parse
sys.path.insert(0, ".")
from coletores_base import buscar  # noqa: E402

RE_HREF = re.compile(r'(?:href|src|action|content|data-src|file)=["\']([^"\']+)["\']', re.I)
FILTRO = re.compile(r"pdf|edic|diar|caderno|busca|pesquis|api|consulta|download|visualiz|jornal|URL=|\.php", re.I)


def pega(url, t=60):
    try:
        return buscar(url, timeout=t, origem="sonda_a3")
    except Exception as e:  # noqa: BLE001
        print(f"  {url} -> ERRO {type(e).__name__} {getattr(e, 'code', '') or ''} {str(e)[:140]}")
        return None


def corpo(url, n=1200, t=60):
    b = pega(url, t)
    if b is None:
        return None
    if b[:5] == b"%PDF-":
        import pypdf
        r = pypdf.PdfReader(io.BytesIO(b))
        tx = r.pages[0].extract_text() or ""
        print(f"  {url} -> PDF {len(b)} B, {len(r.pages)} p., p1: {re.sub(r'\s+', ' ', tx)[:160]}")
        return b
    s = b.decode("utf-8", "replace")
    print(f"  {url} -> 200 {len(b)} B")
    print("    corpo:", re.sub(r"\s+", " ", re.sub(r"<style.*?</style>|<script.*?</script>", " ", s, flags=re.S))[:n])
    links = [h for h in dict.fromkeys(RE_HREF.findall(s)) if FILTRO.search(h)]
    print(f"    links({len(links)}):", links[:50])
    return b


def ctx(b, regex, largura=150, maximo=15):
    s = b.decode("utf-8", "replace")
    vistos = 0
    for m in re.finditer(regex, s):
        print("    …", s[max(0, m.start() - largura):m.end() + largura].replace("\n", " "))
        vistos += 1
        if vistos >= maximo:
            break


def mg(data):
    url = f"https://www.jornalminasgerais.mg.gov.br/api/v1/Jornal/ObterEdicaoPorDataPublicacao?dataPublicacao={data}"
    b = pega(url, 90)
    if b is None:
        return
    try:
        o = json.loads(b)
    except Exception:
        print(f"  MG {data}: não-JSON {b[:200]!r}")
        return
    d = o.get("dados") if isinstance(o, dict) else None
    print(f"  MG {data}: chaves {list(o)[:8]}; dados: {list(d)[:20] if isinstance(d, dict) else type(d).__name__}")
    if not isinstance(d, dict):
        print("   ", json.dumps(o, ensure_ascii=False)[:600])
        return
    for k, v in d.items():
        if isinstance(v, dict):
            print(f"    {k}: {[(kk, (str(vv)[:60] if kk != 'arquivo' else f'<{len(str(vv))} chars>')) for kk, vv in v.items()]}")
        elif isinstance(v, list):
            print(f"    {k}: lista {len(v)}: {json.dumps(v, ensure_ascii=False)[:300]}")
        else:
            print(f"    {k}: {str(v)[:100]}")
    arq = ((d.get("arquivoCadernoPrincipal") or {}).get("arquivo")) or ""
    if arq:
        der = base64.b64decode(arq)
        with tempfile.NamedTemporaryFile(suffix=".p7", delete=False) as f:
            f.write(der)
        r = subprocess.run(["openssl", "cms", "-verify", "-noverify", "-inform", "DER", "-in", f.name, "-out", f.name + ".pdf"],
                           capture_output=True)
        print(f"    openssl: rc {r.returncode} {r.stderr[:160]!r}")
        try:
            pdf = open(f.name + ".pdf", "rb").read()
            import pypdf
            rr = pypdf.PdfReader(io.BytesIO(pdf))
            print(f"    PDF {len(pdf)} B, {len(rr.pages)} p., p1: {re.sub(r'\s+', ' ', rr.pages[0].extract_text() or '')[:160]}")
        except Exception as e:  # noqa: BLE001
            print(f"    PDF falhou: {type(e).__name__} {e}")
        print(f"    der[:24] {der[:24].hex()}")


def mg_bruto(data):
    url = f"https://www.jornalminasgerais.mg.gov.br/api/v1/Jornal/ObterEdicaoPorDataPublicacao?dataPublicacao={data}"
    b = pega(url, 90)
    if b is None:
        return
    o = json.loads(b)
    d = o.get("dados")
    if isinstance(d, dict) and (d.get("arquivoCadernoPrincipal") or {}).get("arquivo"):
        print(f"  MG {data}: edição, {d['arquivoCadernoPrincipal'].get('totalPaginas')} p., erros={o.get('erros')}")
    else:
        print(f"  MG {data}: SEM arquivo: {json.dumps(o, ensure_ascii=False)[:500]}")


if __name__ == "__main__":
    print("=== MG fim de semana, feriado e borda da janela ===")
    for d in ["2026-10-10", "2026-10-11", "2026-10-12", "2026-10-17", "2026-09-30", "2026-09-22", "2026-09-18", "2026-09-17", "2026-09-16", "2026-09-15", "2026-09-11"]:
        mg_bruto(d)
    print("=== RJ edição ===")
    b = corpo("https://www.ioerj.com.br/portal/modules/conteudoonline/do_seleciona_edicao.php?data=MjAyNjEwMTY=", 1500)
    if b:
        t = b.decode("utf-8", "replace")
        ctx(b, r"mostra_edicao|session=|\.pdf|caderno|Parte", 120, 15)
        m = re.search(r'(mostra_edicao\.php\?session=[^"\']+)', t)
        if m:
            u = urllib.parse.urljoin("https://www.ioerj.com.br/portal/modules/conteudoonline/", m.group(1))
            print("  sessão:", m.group(1)[:200])
            try:
                print("  sessão decodificada:", base64.b64decode(m.group(1).split("session=")[1] + "==")[:300])
            except Exception as e:  # noqa: BLE001
                print("  b64 falhou", e)
            b2 = pega(u)
            if b2:
                t2 = b2.decode("utf-8", "replace")
                print("  mostra_edicao", len(b2), "B")
                print("   ", re.sub(r"\s+", " ", t2)[:4000])
    print("=== RS secweb ===")
    b = pega("https://secweb.procergs.com.br/doe/")
    if b:
        t = b.decode("utf-8", "replace")
        print(re.sub(r"\s+", " ", re.sub(r"<style.*?</style>|<link[^>]*>", " ", t, flags=re.S))[:6000])
