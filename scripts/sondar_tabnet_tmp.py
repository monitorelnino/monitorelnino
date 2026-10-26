"""Sonda TabNet (E1, 4ª). Só mede: GET sem seguir redirecionamento. Imprime no log; não grava nada.
Sem POST. Mede: robots (http e https), a página do DDA (http e https), com timeout de 120 s."""
import re
import urllib.error
import urllib.request

UA = {"User-Agent": "MARE-monitorelnino/1.0 (sonda de rota TabNet; monitorelnino.com.br)"}
ALVOS = [
    "http://tabnet.datasus.gov.br/robots.txt",
    "https://tabnet.datasus.gov.br/robots.txt",
    "http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sinannet/cnv/dengbr.def",
    "https://tabnet.datasus.gov.br/cgi/deftohtm.exe?sinannet/cnv/dengbr.def",
]


class SemRedirecionamento(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


opener = urllib.request.build_opener(SemRedirecionamento)

for url in ALVOS:
    print("ALVO", url, flush=True)
    try:
        req = urllib.request.Request(url, headers=UA)
        with opener.open(req, timeout=120) as r:
            corpo = r.read(60000)
            print("  status", r.status, "bytes", len(corpo), "location", r.headers.get("Location"),
                  "ctype", r.headers.get("Content-Type"), flush=True)
            print("  campos_name", sorted({c.decode("latin-1") for c in re.findall(rb'name="([^"]{1,40})"', corpo)})[:60], flush=True)
            print("  corpo_inicio", corpo[:700].decode("latin-1", "replace").replace("\n", " | "), flush=True)
    except urllib.error.HTTPError as e:
        print("  http_erro", e.code, "location", e.headers.get("Location"), flush=True)
        print("  corpo_inicio", (e.read(700) or b"").decode("latin-1", "replace").replace("\n", " | "), flush=True)
    except Exception as e:
        print("  erro_de_rede", type(e).__name__, str(e)[:200], flush=True)
