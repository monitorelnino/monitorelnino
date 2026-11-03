"""Sonda descartável (ramo coleta-dia/*, nunca mesclada). Só leitura; não grava dado e não afrouxa verificação.
O servidor do DOE-MG envia o intermediário errado; baixa o intermediário público da AIA do certificado e
prova que a validação COMPLETA (certifi + esse intermediário) passa."""
import hashlib, re, ssl, urllib.request

import certifi

H = "www.jornalminasgerais.mg.gov.br"
AIA = "http://crt.sectigo.com/SectigoPublicServerAuthenticationCADVR36.crt"
der = urllib.request.urlopen(urllib.request.Request(AIA, headers={"User-Agent": "MARE-monitor-el-nino (sonda TLS; contato: monitorelnino.com.br)"}), timeout=30).read()
pem = ssl.DER_cert_to_PEM_cert(der)
print("AIA> bytes", len(der), "sha256", hashlib.sha256(der).hexdigest())
print("PEM>BEGIN")
for ln in pem.strip().splitlines():
    print("PEM>", ln)
print("PEM>END")
ctx = ssl.create_default_context(cafile=certifi.where())
ctx.load_verify_locations(cadata=pem)
try:
    r = urllib.request.urlopen(f"https://{H}/", timeout=30, context=ctx)
    print("PROVA> validação completa ok, HTTP", r.status)
except Exception as e:  # noqa: BLE001
    print("PROVA>", type(e).__name__, str(e)[:200])
try:
    r = urllib.request.urlopen(f"https://{H}/api/v1/Jornal/ObterEdicaoPorDataPublicacao?dataPublicacao=2026-10-16", timeout=60, context=ctx)
    print("PROVA> API HTTP", r.status, "bytes", len(r.read()))
except Exception as e:  # noqa: BLE001
    print("PROVA> API", type(e).__name__, str(e)[:200])
