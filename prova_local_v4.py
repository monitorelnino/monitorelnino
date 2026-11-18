"""Prova (ramo de válvula, nunca mesclado): o programa local da ponte (v4) completa a cadeia de certificado e
segue recusando certificado de outro nome. Só /robots.txt; não grava nada."""
import ssl, sys, urllib.error
import ponte_local_v4 as p

def le(host):
    try:
        r = p.baixar(f"https://{host}/robots.txt", tempo=25, teto=200_000)
        return f"LIDO (HTTP {r['status']}, {len(r['corpo'])} bytes)"
    except urllib.error.HTTPError as e:
        return f"LIDO (HTTP {e.code})"
    except urllib.error.URLError as e:
        m = e.reason
        return f"RECUSADO pelo certificado ({m.verify_code}: {m.verify_message})" if isinstance(m, ssl.SSLCertVerificationError) else f"sem conexão ({type(m).__name__}: {str(m)[:50]})"
    except Exception as e:  # noqa: BLE001
        return f"outro ({type(e).__name__}: {str(e)[:60]})"

print("python", sys.version.split()[0], "· programa local v" + p.VERSAO, flush=True)
for h in ["legis.ac.gov.br", "www.aris.sc.gov.br", "www.mogimirim.sp.gov.br", "www.casacivil.ac.gov.br", "www.cml.pe.gov.br", "www.gov.br", "cachoeirinha.rs.gov.br", "www.brusque.sc.gov.br"]:
    print(f"V4 | {h:28} | {le(h)} | pelo abridor estrito: {h in p._ESTRITOS}", flush=True)
for u, pem in p._APRENDIDOS.items():
    e, t = p.emissor_e_titular(ssl.PEM_cert_to_DER_cert(pem))
    print(f"APRENDIDO | {u} | autoassinado: {e == t}", flush=True)
