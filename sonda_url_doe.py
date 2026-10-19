#!/usr/bin/env python3
"""Sonda de ramo da válvula (não vai à main): imprime o que cada URL pública responde ao runner."""
import re, sys, urllib.error, urllib.parse
import coletores_base as cb

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
