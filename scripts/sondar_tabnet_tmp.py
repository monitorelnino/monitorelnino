"""Sonda de rota TabNet (E1). Só mede: GET de robots.txt e da página do formulário.
Não envia POST. O resultado vai para data/saude_desfechos/sonda_tabnet_tmp.json SÓ neste ramo
(nunca mesclado): a leitura do log do job não está disponível pelo conector."""
import json
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
resultado = []
for url in ALVOS:
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=60) as r:
            corpo = r.read(300000)
            campos = sorted({c.decode("latin-1") for c in re.findall(rb'name="([^"]{1,40})"', corpo)})[:60]
            resultado.append({"url": url, "situacao": "http_ok", "status": r.status,
                              "bytes": len(corpo), "campos_name": campos,
                              "inicio": corpo[:160].decode("latin-1", "replace")})
    except urllib.error.HTTPError as e:
        resultado.append({"url": url, "situacao": "http_erro", "status": e.code,
                          "nota": "recusa do servidor (não é ausência)"})
    except Exception as e:
        resultado.append({"url": url, "situacao": "erro_de_rede", "erro": type(e).__name__, "detalhe": str(e)[:200]})

with open("data/saude_desfechos/sonda_tabnet_tmp.json", "w", encoding="utf-8") as f:
    json.dump({"sonda": "tabnet_rota_e1", "resultados": resultado}, f, ensure_ascii=False, indent=1)
print(json.dumps(resultado, ensure_ascii=False)[:4000])
