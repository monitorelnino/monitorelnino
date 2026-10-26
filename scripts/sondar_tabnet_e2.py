#!/usr/bin/env python3
"""Sonda do TabNet/DATASUS para a conferência de saúde mental e ICSAP (faixa E2, decisão central 26/10 10:45).

Só mede: pede a página de entrada do TabNet, o relatório do SIH e a página do SIH no DATASUS, e
registra status, tamanho, tempo e a estrutura do formulário (ações e campos de seleção). Não envia
formulário, não grava em data/, não contorna recusa: 401/403/429/451 e muro de robô saem com o
código e não são repetidos. O resultado sai no log do run da válvula (coleta_de_dia.yml).

Uso: python3 scripts/sondar_tabnet_e2.py [--rodar] | --autoteste
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
import time
import urllib.error
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from coletores_base import buscar, detectar_muro_de_robo  # noqa: E402

ORIGEM = "sondar_tabnet_e2"
RECUSAS = (401, 403, 429, 451)
URLS = (
    ("tabnet_entrada", "https://tabnet.datasus.gov.br/"),
    ("tabnet_sih", "http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sih/cnv/niuf.def"),
    ("datasus_sih", "https://datasus.saude.gov.br/acesso-a-informacao/producao-hospitalar-sih-sus/"),
)


def formularios(html: str) -> dict:
    """Ações de formulário e campos de seleção da página. Função pura: página sem formulário = listas vazias."""
    acoes = re.findall(r'<form[^>]*\baction="([^"]*)"', html, re.I)
    campos = re.findall(r'<select[^>]*\bname="([^"]*)"', html, re.I)
    return {"acoes": acoes[:10], "selects": campos[:40], "n_selects": len(campos)}


def sondar(nome: str, url: str, buscar_fn=buscar) -> dict:
    t0 = time.time()
    base = {"nome": nome, "url": url}
    try:
        corpo = buscar_fn(url, origem=ORIGEM)
    except urllib.error.HTTPError as e:
        resultado = "recusa_nomeada" if e.code in RECUSAS else "erro_http"
        return {**base, "status": e.code, "resultado": resultado, "segundos": round(time.time() - t0, 1)}
    except Exception as e:  # sem resposta: registra só o tipo do erro
        return {**base, "status": None, "resultado": "sem_resposta", "motivo": type(e).__name__,
                "segundos": round(time.time() - t0, 1)}
    muro = detectar_muro_de_robo(corpo)
    if muro:
        return {**base, "status": 200, "resultado": "muro_de_robo", "motivo": muro,
                "segundos": round(time.time() - t0, 1)}
    html = corpo.decode("latin-1", "replace")
    return {**base, "status": 200, "resultado": "medido", "bytes": len(corpo),
            "segundos": round(time.time() - t0, 1), **formularios(html)}


def rodar(sondar_fn=sondar) -> int:
    agora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    resultados = [sondar_fn(nome, url) for nome, url in URLS]
    print(json.dumps({"sonda": "tabnet_e2", "medido_em": agora, "resultados": resultados},
                     ensure_ascii=False, indent=1))
    return 0


def autoteste() -> int:
    falhas = []

    def ok(cond, nome):
        if not cond:
            falhas.append(nome)

    html = ('<html><form action="/cgi/tabcgi.exe?sih/cnv/niuf.def" method="post">'
            '<select name="Linha"><option>UF</option></select>'
            '<select name="Coluna"><option>Mês</option></select></form></html>')
    f = formularios(html)
    ok(f["acoes"] == ["/cgi/tabcgi.exe?sih/cnv/niuf.def"], "acao_do_formulario")
    ok(f["selects"] == ["Linha", "Coluna"] and f["n_selects"] == 2, "selects")
    ok(formularios("<p>sem form</p>") == {"acoes": [], "selects": [], "n_selects": 0}, "pagina_sem_form")

    def recusa(url, origem=None):
        raise urllib.error.HTTPError(url, 403, "Forbidden", None, None)

    r = sondar("x", "https://exemplo.invalido/", recusa)
    ok(r["resultado"] == "recusa_nomeada" and r["status"] == 403, "recusa_403_nomeada")

    def rede(url, origem=None):
        raise urllib.error.URLError("sem rota")

    r = sondar("x", "https://exemplo.invalido/", rede)
    ok(r["resultado"] == "sem_resposta" and r["motivo"] == "URLError", "rede_sem_resposta")

    def pagina(url, origem=None):
        return html.encode("latin-1")

    r = sondar("x", "https://exemplo.invalido/", pagina)
    ok(r["resultado"] == "medido" and r["n_selects"] == 2, "pagina_medida")

    if falhas:
        print("FALHOU:", ", ".join(falhas))
        return 1
    print("autoteste ok (4 casos, sem rede)")
    return 0


if __name__ == "__main__":
    if "--autoteste" in sys.argv:
        sys.exit(autoteste())
    sys.exit(rodar())
