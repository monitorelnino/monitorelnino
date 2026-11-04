"""Sonda descartável (ramo coleta-dia/*, nunca mesclada). Só leitura; não grava dado e não afrouxa verificação.
Por que o runner não baixa o plano do PI (URLError em 03/11): DNS, TCP, TLS e HTTP, cada um separado."""
import socket, ssl, subprocess, urllib.request

import certifi
import coletores_base as cb

H = "portal.pi.gov.br"
U = f"https://{H}/sesapi/wp-content/uploads/sites/101/2026/09/PLANO-DE-ENFRENTAMENTO-DOS-EFEITOS-DO-EL-NINO_SESAPI_2026.pdf"
try:
    print("PI> DNS", sorted({a[4][0] for a in socket.getaddrinfo(H, 443)}))
except Exception as e:  # noqa: BLE001
    print("PI> DNS", type(e).__name__, e)
try:
    socket.create_connection((H, 443), timeout=20).close()
    print("PI> TCP 443 ok")
except Exception as e:  # noqa: BLE001
    print("PI> TCP", type(e).__name__, e)
for nome, ctx in (("certifi+intermediarios", cb.contexto_tls()), ("padrao do sistema", ssl.create_default_context())):
    try:
        r = urllib.request.urlopen(urllib.request.Request(U, headers={"User-Agent": "MARE-monitor-el-nino (sonda TLS; contato: monitorelnino.com.br)"}), timeout=60, context=ctx)
        corpo = r.read()
        print("PI>", nome, "HTTP", r.status, "bytes", len(corpo), r.headers.get("content-type"))
    except Exception as e:  # noqa: BLE001
        print("PI>", nome, type(e).__name__, str(e)[:300], "| reason:", repr(getattr(e, "reason", ""))[:200])
try:
    out = subprocess.run(["openssl", "s_client", "-showcerts", "-connect", f"{H}:443", "-servername", H],
                         input=b"", capture_output=True, timeout=40).stdout.decode("utf-8", "replace")
    for ln in out.splitlines():
        if ln.startswith((" ", "Certificate chain", "Verify", "verify", "---")) and ("s:" in ln or "i:" in ln or "erify" in ln or "chain" in ln):
            print("PI> openssl", ln.strip())
except Exception as e:  # noqa: BLE001
    print("PI> openssl", type(e).__name__, e)
