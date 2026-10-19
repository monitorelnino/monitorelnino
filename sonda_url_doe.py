#!/usr/bin/env python3
"""Sonda de ramo da válvula (não vai à main): imprime o que cada URL pública responde ao runner."""
import re, sys, urllib.error, urllib.parse
import coletores_base as cb


def _rj(dia):
    import base64, re
    b = "https://www.ioerj.com.br/portal/modules/conteudoonline/"
    t = cb.buscar_uma_vez(b + "do_seleciona_edicao.php?data=" + base64.b64encode(dia.encode()).decode(), timeout=30, origem="sonda_doe").decode("utf-8", "replace")
    ses = re.findall(r'mostra_edicao\.php\?session=([A-Za-z0-9+/=]+)"[^>]*>([^<]+)<', t)
    print("RJ cadernos:", [(n.strip(), s[:20]) for s, n in ses])
    if not ses: return
    pag = cb.buscar_uma_vez(b + "mostra_edicao.php?session=" + ses[0][0], timeout=30, origem="sonda_doe").decode("utf-8", "replace")
    m = re.search(r'var pd = "([^"]+)"', pag)
    print("RJ pd:", m.group(1) if m else None)
    if not m: return
    pd = m.group(1)
    for url in (b + "mostra_edicao.php?k=" + pd[:12] + "P" + pd[12:], b + "mostra_edicao.php?session=" + ses[0][0] + "&k=" + pd[:12] + "P" + pd[12:]):
        try:
            r = cb.buscar_uma_vez(url, timeout=60, origem="sonda_doe")
            print("RJ pdf:", url[-60:], len(r), r[:8])
        except Exception as e:
            print("RJ pdf falhou:", url[-60:], type(e).__name__, str(e)[:120])

for _u in list(sys.argv[1:]):
    if _u.startswith("rj:"):
        _rj(_u[3:]); sys.argv.remove(_u)

for url in sys.argv[1:]:
    print(f"=== {url}")
    ctx = None
    if "#ctx=" in url:
        url, ctx = url.split("#ctx=", 1)
    try:
        b = cb.buscar_uma_vez(url, timeout=12, origem="sonda_doe")
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code} {e.reason}"); continue
    except Exception as e:
        print(f"{type(e).__name__}: {str(e)[:200]}"); continue
    t = b.decode("utf-8", "replace")
    import pathlib, hashlib
    pasta = pathlib.Path("data/sonda_doe"); pasta.mkdir(parents=True, exist_ok=True)
    (pasta / (hashlib.sha1(url.encode()).hexdigest()[:10] + ".txt")).write_text(url + "\n" + t[:3_000_000], encoding="utf-8")
    if ctx:
        for m in list(re.finditer(re.escape(ctx), t))[:6]:
            print("  ctx·", re.sub(r"\s+", " ", t[max(0, m.start() - 350):m.end() + 450]))
        continue
    if b[:5] == b"%PDF-":
        print(f"  PDF · {len(b)} bytes"); continue
    print(f"200 · {len(b)} bytes · início: {re.sub(chr(10)+'|'+chr(13)+'|\\s+', ' ', t[:300])}")
    if url.split("?")[0].endswith(".js"):
        for m in sorted(set(re.findall(r'["\']([^"\'\s]{0,60}(?:public/|api/|/diarios?/|consultar|download|Pesquisa|pesquisa|Norma|norma|Diario|diario|ashx|recaptcha|Captcha)[^"\'\s]{0,100})["\']', t)))[:60]:
            print("  js·", m)
        continue
    achados = re.findall(r'''(?:href|src|action|file|url|data-url)\s*[=:]\s*["']([^"'<>\s]{4,200})["']''', t)
    vistos = []
    for a in achados:
        a = urllib.parse.urljoin(url, a)
        if a not in vistos and not re.search(r'\.(css|png|jpg|gif|svg|ico|woff2?)(\?|$)', a):
            vistos.append(a)
    for a in vistos[:45]:
        print("  ·", a)
