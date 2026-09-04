#!/usr/bin/env python3
"""
sondar_portal_transparencia.py
===============================
Sonda de UMA VEZ: a chave PORTAL_TRANSPARENCIA_API_KEY existe como segredo
desde 31/08/2026 e o workflow a repassa corretamente, mas todas as consultas
voltaram HTTP 403. Esta sonda descobre POR QUÊ, imprimindo o corpo da resposta
do Portal (que costuma explicar o motivo) para alguns endpoints.

NUNCA imprime a chave: só o comprimento, os 4 primeiros caracteres e se há
espaços em volta (erro de colagem é a causa mais comum de 403).
"""
import json, os, urllib.error, urllib.parse, urllib.request

API = "https://api.portaldatransparencia.gov.br/api-de-dados"


def diagnosticar_chave(chave: str) -> None:
    print("=== a chave, sem revelá-la ===")
    print(f"  presente: {bool(chave)}")
    print(f"  comprimento: {len(chave)}")
    print(f"  4 primeiros: {chave[:4]!r}")
    print(f"  tem espaço/quebra nas pontas: {chave != chave.strip()}")
    print(f"  só hexadecimal (formato usual do Portal): {all(c in '0123456789abcdefABCDEF' for c in chave.strip())}")


def testar(caminho: str, chave: str, params: dict) -> None:
    url = f"{API}{caminho}?{urllib.parse.urlencode(params)}"
    print(f"\n-- {caminho}\n   {url}")
    req = urllib.request.Request(url, headers={"chave-api-dados": chave.strip(),
                                                "User-Agent": "MonitorElNinoBrasil/3.0",
                                                "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            corpo = r.read(400)
            print(f"   -> HTTP {r.status} | {r.headers.get('Content-Type','?')} | {corpo[:300]!r}")
    except urllib.error.HTTPError as e:
        corpo = e.read(600)
        print(f"   -> HTTPError {e.code} {e.reason}")
        print(f"      corpo: {corpo[:500]!r}")
    except Exception as e:  # noqa: BLE001
        print(f"   -> {type(e).__name__}: {e}")


def main() -> None:
    chave = os.environ.get("PORTAL_TRANSPARENCIA_API_KEY", "")
    diagnosticar_chave(chave)
    if not chave:
        print("\n!! sem chave no ambiente — nada a testar."); return
    # endpoint mais simples primeiro: se este passar, a chave é válida e o problema é o outro endpoint
    testar("/despesas/por-orgao", chave, {"ano": 2026, "pagina": 1})
    testar("/transferencias-voluntarias", chave, {"codigoIBGE": "5200050", "ano": 2026, "pagina": 1, "itens": 100})
    testar("/transferencias", chave, {"codigoIbge": "5200050", "mesAnoInicio": "01/2026", "mesAnoFim": "08/2026", "pagina": 1})
    # sem o parâmetro 'itens' (pode não existir mais)
    testar("/transferencias-voluntarias", chave, {"codigoIBGE": "5200050", "ano": 2026, "pagina": 1})


if __name__ == "__main__":
    main()
