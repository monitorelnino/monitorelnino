#!/usr/bin/env python3
"""Sonda de rotas SUS para desfechos notificáveis (E1, 26/10/2026). SÓ MEDE.

Não grava nada em data/ nem em pistas: imprime no log do Actions o que cada rota
devolve, para decidir a rota com prova (HANDOVER_SUS_DESFECHOS §5, passo 1).
Roda como válvula `coleta_de_dia.yml` (rede real do runner).

Regras: cliente identificado (ua_de), robots.txt lido e registrado por host,
401/403/429/451 param a rota (nunca se contorna), arquivo baixado tem teto de 15 MB.
"""
from __future__ import annotations

import pathlib
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from coletores_base import ua_de  # noqa: E402

UA = ua_de("sonda das rotas SUS dos desfechos")
TETO_BYTES = 15 * 1024 * 1024
BLOQUEIOS = {401, 403, 429, 451}

ROTAS = [
    ("FTP DATASUS · SINAN PRELIM", "https://ftp.datasus.gov.br/dissemin/publicos/SINAN/DADOS/PRELIM/"),
    ("FTP DATASUS · SIH RD 2025", "https://ftp.datasus.gov.br/dissemin/publicos/SIHSUS/202501_/Dados/"),
    ("FTP DATASUS · SIM PRELIM", "https://ftp.datasus.gov.br/dissemin/publicos/SIM/PRELIM/DORES/"),
    ("SISAB · relatório de produção", "https://sisab.saude.gov.br/paginas/acessoRestrito/relatorio/federal/saude/RelSauProducao.xhtml"),
    ("TabNet · SINAN leptospirose", "https://tabnet.datasus.gov.br/cgi/deftohtm.exe?sinannet/cnv/leptbr.def"),
    ("OpenDataSUS · portal", "https://opendatasus.saude.gov.br/"),
]


def robots_de(url: str) -> str:
    base = urllib.parse.urljoin(url, "/robots.txt")
    rp = urllib.robotparser.RobotFileParser()
    try:
        req = urllib.request.Request(base, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=20) as r:
            rp.parse(r.read().decode("utf-8", "replace").splitlines())
    except urllib.error.HTTPError as e:
        return f"robots HTTP {e.code}"
    except Exception as e:  # rede, TLS, timeout
        return f"robots erro {type(e).__name__}"
    permitido = rp.can_fetch(UA, url)
    return f"robots ok, permitido={permitido}, crawl_delay={rp.crawl_delay(UA)}"


def sondar(nome: str, url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            corpo = r.read(TETO_BYTES + 1)
            return f"HTTP {r.status}, {len(corpo)} bytes, tipo {r.headers.get('Content-Type', '?')}"
    except urllib.error.HTTPError as e:
        marca = " (bloqueio real: não se contorna)" if e.code in BLOQUEIOS else ""
        return f"HTTP {e.code}{marca}"
    except Exception as e:
        return f"erro de rede {type(e).__name__}: {str(e)[:120]}"


def listar_arquivos(url: str, padrao: str) -> list[str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=40) as r:
        html = r.read().decode("utf-8", "replace")
    nomes = re.findall(r'href="([^"?/]+\.dbc)"', html, flags=re.I)
    return [n for n in nomes if re.search(padrao, n, flags=re.I)]


def main() -> int:
    for nome, url in ROTAS:
        print(f"== {nome}\n   {url}\n   {robots_de(url)}\n   {sondar(nome, url)}")
    # Amostra de SINAN leptospirose, se a listagem responder: mede tamanho e nomes, não decodifica aqui.
    try:
        arquivos = listar_arquivos(ROTAS[0][1], r"LEPT")
        print(f"== SINAN LEPT na listagem PRELIM: {len(arquivos)} arquivo(s): {arquivos[:6]}")
    except Exception as e:
        print(f"== SINAN LEPT na listagem PRELIM: indisponível ({type(e).__name__})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
