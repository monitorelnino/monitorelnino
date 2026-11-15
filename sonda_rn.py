import re, socket
import coletores_base as c
for h in ("webdisk.diariooficial.rn.gov.br", "www.diariooficial.rn.gov.br", "diariooficial.rn.gov.br", "deirn.sdoe.com.br"):
    try: print("DNS", h, socket.gethostbyname(h))
    except Exception as e: print("DNS", h, "FALHA", e)
for u in ("https://www.diariooficial.rn.gov.br", "https://www.diariooficial.rn.gov.br/dei/dorn3",
          "https://webdisk.diariooficial.rn.gov.br/Jornal/12026-11-12.pdf", "http://webdisk.diariooficial.rn.gov.br/Jornal/12026-11-12.pdf"):
    try:
        b = c.buscar(u, timeout=30, origem="sonda da rota do diário do RN"); t = b[:300000].decode("utf-8", "replace")
        print("OK", u, len(b), b[:5]); print(sorted(set(re.findall(r"""(?:https?:)?//[^"' <>]+|href="[^"]+""", t)))[:60])
    except Exception as e: print("ERRO", u, type(e).__name__, str(e)[:200])
