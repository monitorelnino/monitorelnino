#!/usr/bin/env python3
"""Sonda pontual (14/09/2026): o CSV do InfoGripe no GitLab da Fiocruz está
atrás de login (confirmado por dois caminhos de rede independentes). Os
"Resumos do Boletim InfoGripe" semanais em PDF (agencia.fiocruz.br) são
públicos, mas não têm série numérica por UF — só texto categórico (nível de
alerta/risco/alto risco) e gráficos como imagem. Não sabemos ainda onde o
site da Fiocruz lista/aponta para o boletim da semana mais recente — sem
isso, um coletor teria que adivinhar o número da SE no nome do arquivo
(mesmo erro do PB, proibido pela casa). Esta sonda não coleta nem grava nada
em data/: só mostra o que existe, para decidir o mecanismo de descoberta com
prova. Roda do runner do Actions (rede real, sem as restrições do sandbox de
edição).
"""
from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from datetime import date, timedelta

# §228 (26/09/2026): havia aqui um `UA_NAVEGADOR` com o User-Agent completo de um Chrome no
# Windows. Não era usado por nenhuma chamada — código morto —, e sai de todo modo: deixar um
# disfarce pronto no arquivo é convite para a próxima pessoa usá-lo. O cliente é um só, com o
# propósito declarado. Nunca disfarçar o cliente.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from coletores_base import ua_de  # noqa: E402

UA_MONITOR = ua_de("sonda do boletim InfoGripe")

# Páginas candidatas a listagem/apontador para o boletim mais recente —
# nenhuma foi confirmada ainda; testamos todas e registramos o que cada
# uma devolve.
CANDIDATOS_LISTAGEM = [
    "https://agencia.fiocruz.br/infogripe",
    "https://agencia.fiocruz.br/tema/infogripe",
    "https://agencia.fiocruz.br/boletim-infogripe",
    "https://agencia.fiocruz.br/search/node/infogripe",
    "https://portal.fiocruz.br/infogripe",
    "http://info.gripe.fiocruz.br/",
    "http://info.gripe.fiocruz.br/help",
]


def _get(url: str, ua: str, timeout: int = 30) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": ua})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            corpo = resp.read()
            return {
                "status": resp.status,
                "tipo": resp.headers.get("Content-Type", ""),
                "bytes": len(corpo),
                "inicio": corpo[:300].decode("utf-8", "replace"),
                "_corpo": corpo,
            }
    except urllib.error.HTTPError as e:
        return {"erro": "HTTPError", "status": e.code, "motivo": str(e)}
    except urllib.error.URLError as e:
        return {"erro": "URLError", "motivo": str(e.reason)}
    except Exception as e:  # noqa: BLE001 — sonda: qualquer falha é resultado a registrar
        return {"erro": type(e).__name__, "motivo": str(e)}


def semana_epidemiologica(d: date) -> tuple[int, int]:
    """Aproximação de SE (padrão ISO, não o cálculo exato do SIVEP — só para
    delimitar a faixa de números a testar na sonda, nunca para produção."""
    iso = d.isocalendar()
    return iso[0], iso[1]


def main() -> int:
    print("=" * 70)
    print("=== Páginas candidatas a listagem/apontador do InfoGripe ===")
    print("=" * 70)
    encontrou_link_pdf = False
    for url in CANDIDATOS_LISTAGEM:
        print(f"\n-- {url}")
        r = _get(url, UA_MONITOR)
        if "erro" in r:
            print(f"   {r['erro']}: {r.get('motivo')} (status={r.get('status')})")
            continue
        print(f"   status={r['status']} tipo={r['tipo']} bytes={r['bytes']}")
        html = r["_corpo"].decode("utf-8", "replace")
        links_pdf = sorted(set(re.findall(r'href="([^"]*Resumo_InfoGripe[^"]*\.pdf)"', html, re.I)))
        if links_pdf:
            encontrou_link_pdf = True
            print(f"   links Resumo_InfoGripe*.pdf encontrados ({len(links_pdf)}): {links_pdf[:5]}")
        else:
            print("   nenhum link Resumo_InfoGripe*.pdf no HTML")

    print()
    print("=" * 70)
    print("=== Faixa de nomes de arquivo plausível para a semana atual (sonda, não produção) ===")
    print("=" * 70)
    hoje = date.today()
    ano_iso, se_iso = semana_epidemiologica(hoje)
    print(f"data de hoje (UTC do runner): {hoje.isoformat()} | aproximação ISO: ano={ano_iso} SE~={se_iso}")
    # Testa uma janela pequena ao redor da aproximação, nos dois padrões de nome
    # observados (com e sem sufixo _0) — só para ver quais existem de fato.
    achados = []
    for delta in range(-2, 3):
        se = se_iso + delta
        if se < 1:
            continue
        for sufixo in ("", "_0"):
            nome = f"Resumo_InfoGripe_{ano_iso}_{se:02d}{sufixo}.pdf"
            url = f"https://agencia.fiocruz.br/sites/agencia.fiocruz.br/files/{nome}"
            r = _get(url, UA_MONITOR, timeout=15)
            status = r.get("status", r.get("erro"))
            print(f"   SE {se:02d}{sufixo or ''}: {url} -> {status}")
            if r.get("status") == 200:
                achados.append((se, sufixo, url, r.get("bytes")))

    print()
    print("=" * 70)
    print("=== Resumo ===")
    print("=" * 70)
    print(f"listagem com link direto encontrada: {encontrou_link_pdf}")
    if achados:
        mais_recente = max(achados, key=lambda a: a[0])
        print(f"boletim mais recente que respondeu 200 na janela testada: SE {mais_recente[0]:02d}{mais_recente[1]} ({mais_recente[2]}, {mais_recente[3]} bytes)")
    else:
        print("nenhum boletim respondeu 200 na janela testada — pode indicar atraso de publicação real, "
              "problema na aproximação de SE usada pela sonda, ou bloqueio do runner.")
    print(json.dumps({"achados": achados, "listagem_com_link": encontrou_link_pdf}, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
