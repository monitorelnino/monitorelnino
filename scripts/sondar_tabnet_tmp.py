"""Sonda de rota TabNet (E1). Só mede: GET de robots.txt e da página do formulário.
Não envia POST e não grava em data/. Cliente identificado; erro por URL não interrompe as demais."""
import re
import urllib.error
import urllib.request

UA = {"User-Agent": "MARE-monitorelnino/1.0 (sonda de rota TabNet; monitorelnino.com.br)"}
ALVOS = [
    "http://tabnet.datasus.gov.br/robots.txt",
    "https://tabnet.datasus.gov.br/robots.txt",
    "http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sinannet/cnv/dengbr.def",
    "https://tabnet.datasus.gov.br/cgi/deftohtm.exe?sinannet/cnv/dengbr.def",
    "https://datasus.saude.gov.br/",
]

for url in ALVOS:
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=60) as r:
            corpo = r.read(300000)
            campos = sorted(set(re.findall(rb'name="([^"]{1,40})"', corpo)))[:60]
            print(url, "HTTP", r.status, "bytes", len(corpo), "campos", [c.decode("latin-1") for c in campos])
    except urllib.error.HTTPError as e:
        print(url, "HTTP_ERRO", e.code, "(recusa, não ausência)")
    except Exception as e:
        print(url, "ERRO_REDE", type(e).__name__, str(e)[:160])
