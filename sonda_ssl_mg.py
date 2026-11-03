"""Sonda descartável (ramo coleta-dia/*, nunca mesclada): mostra a cadeia TLS que o DOE-MG apresenta.
Só leitura; não grava dado e não afrouxa verificação."""
import re, ssl, subprocess, urllib.request

H = "www.jornalminasgerais.mg.gov.br"
p = subprocess.run(["openssl", "s_client", "-showcerts", "-servername", H, "-connect", f"{H}:443"],
                   input="", capture_output=True, text=True, timeout=60)
out = p.stdout + p.stderr
for ln in out.splitlines():
    if re.match(r"^\s*\d+ s:|^\s+i:|Verif|verify|Certificate chain|depth=|issuer", ln):
        print("TLS>", ln)
pems = re.findall(r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", out, re.S)
print("TLS> certificados apresentados:", len(pems))
if pems:
    t = subprocess.run(["openssl", "x509", "-noout", "-text"], input=pems[0], capture_output=True, text=True).stdout
    for ln in t.splitlines():
        if "CA Issuers" in ln or "Issuer:" in ln or "Not After" in ln or "Subject:" in ln:
            print("LEAF>", ln.strip())
try:
    import certifi
    ctx = ssl.create_default_context(cafile=certifi.where())
    urllib.request.urlopen(f"https://{H}/", timeout=30, context=ctx)
    print("CERTIFI> ok")
except Exception as e:  # noqa: BLE001
    print("CERTIFI>", type(e).__name__, str(e)[:160])
try:
    urllib.request.urlopen(f"https://{H}/", timeout=30)
    print("SISTEMA> ok")
except Exception as e:  # noqa: BLE001
    print("SISTEMA>", type(e).__name__, str(e)[:160])
