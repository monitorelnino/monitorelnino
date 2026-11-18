"""Sonda 2 de alcance (ramo de válvula, nunca mesclado): por que o TLS falha para o robô em hosts que
respondem ao Brasil. Só aperto de mão e /robots.txt; não grava nada."""
import sys, ssl, socket, subprocess, tempfile, os, re, urllib.request, urllib.error
sys.path[:0] = ["scripts", "."]
import coletores_base as cb
import certifi

UA = cb.ua_de("sonda de alcance")
HOSTS = ["www.saude.df.gov.br", "www.portal.ap.gov.br", "www.srh.ce.gov.br", "www.pmsg.rj.gov.br", "saude.df.gov.br", "saude.portal.ap.gov.br", "editor.amapa.gov.br", "www.casacivil.ac.gov.br", "www.legis.ac.gov.br", "sead.portal.ap.gov.br", "www.transparencia.ap.gov.br", "rbsp.sesab.ba.gov.br", "casacivil.ac.gov.br", "www.ce.gov.br", "www.cagepa.pb.gov.br", "www.mogimirim.sp.gov.br", "pncp.gov.br", "www.fortaleza.ce.gov.br", "iranduba.am.gov.br", "trezetilias.sc.gov.br", "buerarema.ba.gov.br", "borba.am.gov.br", "codajas.am.gov.br", "gravatal.sc.gov.br", "luizalves.sc.gov.br", "chorrocho.ba.gov.br"]


def aperto(host, ctx, t=20):
    s = socket.create_connection((host, 443), timeout=t)
    try:
        return ctx.wrap_socket(s, server_hostname=host)
    except Exception:
        s.close()
        raise


def pem_de(der):
    return ssl.DER_cert_to_PEM_cert(der)


def aia_e_dados(der):
    from cryptography import x509
    from cryptography.x509.oid import ExtensionOID, AuthorityInformationAccessOID
    c = x509.load_der_x509_certificate(der)
    urls = []
    try:
        for d in c.extensions.get_extension_for_oid(ExtensionOID.AUTHORITY_INFORMATION_ACCESS).value:
            if d.access_method == AuthorityInformationAccessOID.CA_ISSUERS:
                urls.append(d.access_location.value)
    except Exception:  # noqa: BLE001
        pass
    emissor = c.issuer.rfc4514_string()
    return urls, re.sub(r".*?(CN=[^,]+).*", r"\1", emissor)[:60], c.not_valid_after_utc.date().isoformat(), c.subject == c.issuer


def baixar(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=20) as r:
        b = r.read(200000)
    if b.lstrip().startswith(b"-----BEGIN"):
        return ssl.PEM_cert_to_DER_cert(b.decode("ascii", "ignore"))
    return b


for h in HOSTS:
    linha = [h]
    try:
        ss = aperto(h, cb.contexto_tls())
        linha.append(f"verificado OK {ss.version()}")
        ss.close()
        try:
            with urllib.request.urlopen(urllib.request.Request(f"https://{h}/robots.txt", headers={"User-Agent": UA}), timeout=20, context=cb.contexto_tls()) as r:
                linha.append(f"robots HTTP {r.status}")
        except urllib.error.HTTPError as e:
            linha.append(f"robots HTTP {e.code} servidor={e.headers.get('Server')}")
        except Exception as e:  # noqa: BLE001
            linha.append(f"robots {type(e).__name__}: {str(e)[:90]}")
    except ssl.SSLCertVerificationError as e:
        linha.append(f"CERTIFICADO: {e.verify_message}")
        try:
            u = ssl._create_unverified_context()
            ss = aperto(h, u)
            der = ss.getpeercert(binary_form=True)
            ss.close()
            urls, emissor, validade, autoassinado = aia_e_dados(der)
            linha.append(f"emissor {emissor} · vence {validade} · AIA {'sim' if urls else 'não'}" + (" · autoassinado" if autoassinado else ""))
            cadeia, atual, erro = [], der, ""
            for _ in range(3):
                us, _, _, auto = aia_e_dados(atual)
                if auto or not us:
                    break
                try:
                    atual = baixar(us[0])
                    if atual[:1] != b"0":
                        erro = "emissor em formato não lido"
                        break
                    cadeia.append(atual)
                except Exception as ex:  # noqa: BLE001
                    erro = f"emissor não baixado ({type(ex).__name__})"
                    break
            with tempfile.TemporaryDirectory() as tmp:
                folha, inter = os.path.join(tmp, "f.pem"), os.path.join(tmp, "i.pem")
                open(folha, "w").write(pem_de(der))
                open(inter, "w").write("".join(pem_de(c) for c in cadeia))
                cmd = ["openssl", "verify", "-CAfile", certifi.where()] + (["-untrusted", inter] if cadeia else []) + ["-verify_hostname", h, folha]
                p = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                saida = (p.stdout + p.stderr).strip().splitlines()
                linha.append(f"com {len(cadeia)} intermediário(s) do próprio certificado: " + ("CADEIA OK" if p.returncode == 0 else (erro or saida[-1][-80:] if saida else "erro")))
        except Exception as ex:  # noqa: BLE001
            linha.append(f"diagnóstico falhou: {type(ex).__name__}: {str(ex)[:80]}")
    except ssl.SSLError as e:
        linha.append(f"TLS: {e.reason or str(e)[:60]}")
        for nome, prep in [("TLS1.2 nível 1", lambda c: (setattr(c, "maximum_version", ssl.TLSVersion.TLSv1_2), c.set_ciphers("DEFAULT:@SECLEVEL=1"))),
                           ("TLS1.2 nível 0", lambda c: (setattr(c, "maximum_version", ssl.TLSVersion.TLSv1_2), c.set_ciphers("ALL:@SECLEVEL=0")))]:
            try:
                c = cb.contexto_tls()
                prep(c)
                ss = aperto(h, c)
                linha.append(f"{nome}: OK {ss.version()} {ss.cipher()[0]} (certificado verificado)")
                ss.close()
                break
            except Exception as ex:  # noqa: BLE001
                linha.append(f"{nome}: {type(ex).__name__} {str(ex)[:50]}")
    except Exception as e:  # noqa: BLE001
        linha.append(f"REDE: {type(e).__name__}: {str(e)[:80]}")
    print("TLS | " + " | ".join(linha), flush=True)
