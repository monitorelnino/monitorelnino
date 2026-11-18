"""Prova (ramo de válvula, nunca mesclado): a porta de rede completa a cadeia de certificado que o servidor não
envia e segue recusando certificado de outro nome ou vencido. Só /robots.txt; não grava nada."""
import sys, ssl, urllib.error
sys.path[:0] = ["scripts", "."]
import coletores_base as cb

INCOMPLETA = ["www.ce.gov.br", "www.cml.pe.gov.br", "legis.ac.gov.br", "www.saogoncalo.rj.gov.br", "www.cib.rj.gov.br",
              "www.pmsg.rj.gov.br", "www.casacivil.ac.gov.br", "www.aris.sc.gov.br", "www.srh.ce.gov.br", "www.cagepa.pb.gov.br",
              "www.mogimirim.sp.gov.br", "jornalminasgerais.mg.gov.br"]
ERRADO = ["cachoeirinha.rs.gov.br", "www2.sed.sc.gov.br", "www.brusque.sc.gov.br", "guaraciaba.sc.gov.br"]


def le(host):
    try:
        corpo = cb.buscar_uma_vez(f"https://{host}/robots.txt", timeout=25, origem="prova da cadeia")
        return f"LIDO com verificação plena ({len(corpo)} bytes)"
    except urllib.error.HTTPError as e:
        return f"LIDO com verificação plena (HTTP {e.code})"
    except cb.MuroDeRobo as e:
        return f"LIDO com verificação plena (muro: {e.marca[:30]})"
    except urllib.error.URLError as e:
        r = e.reason
        if isinstance(r, ssl.SSLCertVerificationError):
            return f"RECUSADO pelo certificado ({r.verify_code}: {r.verify_message})"
        return f"sem conexão ({type(r).__name__}: {str(r)[:60]})"
    except Exception as e:  # noqa: BLE001
        return f"outro ({type(e).__name__}: {str(e)[:60]})"


print("python", sys.version.split()[0], "· cadeia parcial desligada:", not cb.contexto_tls().verify_flags & ssl.VERIFY_X509_PARTIAL_CHAIN, flush=True)
ok = 0
for h in INCOMPLETA:
    antes = len(cb._INTERMEDIARIOS_APRENDIDOS)
    r = le(h)
    ok += r.startswith("LIDO")
    print(f"CADEIA | {h:32} | {r} | intermediários aprendidos nesta leitura: {len(cb._INTERMEDIARIOS_APRENDIDOS) - antes}", flush=True)
for h in ERRADO:
    print(f"ERRADO | {h:32} | {le(h)}", flush=True)
for u in cb._INTERMEDIARIOS_APRENDIDOS:
    der = ssl.PEM_cert_to_DER_cert(cb._INTERMEDIARIOS_APRENDIDOS[u])
    e, t = cb.emissor_e_titular(der)
    print(f"APRENDIDO | {u} | autoassinado: {e == t} | {len(der)} bytes", flush=True)
print(f"RESUMO: {ok} de {len(INCOMPLETA)} sites de cadeia incompleta lidos com verificação plena", flush=True)
