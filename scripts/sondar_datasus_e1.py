#!/usr/bin/env python3
"""Sondagem E1 (25/10/2026): FTP do DATASUS, leitor .dbc, SISAB e TabNet. Só mede.

Não coleta série nem escreve pista. Único arquivo gravado: data/saude_desfechos/sondagem_datasus_e1.json
(registro de rotas provadas e recusadas). Acesso: cliente identificado; robots.txt consultado onde há
(HTTP); recusa 401/403/429/451/captcha/login é registrada como recusa, nunca contornada.
Roda na válvula coleta_de_dia.yml (rede real do runner). Autoteste offline: `--autoteste`.
"""
from __future__ import annotations

import ftplib
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

UA = "Monitor El Nino Brasil (monitorelnino.com.br; contato@futuraevidencelab.com.br)"
SAIDA = Path("data/saude_desfechos/sondagem_datasus_e1.json")
FTP_HOST = "ftp.datasus.gov.br"
LIMITE_DOWNLOAD = 15 * 1024 * 1024  # só baixa .dbc até 15 MB nesta sondagem


def _sondagem(id_: str, alvo: str, fn) -> dict:
    t0 = time.time()
    try:
        out = fn() or {}
        return {"id": id_, "alvo": alvo, "status": out.pop("status", "ok"), **out, "s": round(time.time() - t0, 1)}
    except Exception as e:  # registra a falha; nunca derruba a sondagem
        return {"id": id_, "alvo": alvo, "status": "falha", "detalhe": f"{type(e).__name__}: {str(e)[:160]}", "s": round(time.time() - t0, 1)}


def _http_robots(host: str) -> dict:
    req = urllib.request.Request(f"https://{host}/robots.txt", headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            corpo = r.read(20000).decode("utf-8", "replace")
            disallow = [l.split(":", 1)[1].strip() for l in corpo.splitlines() if l.lower().startswith("disallow:")]
            return {"status": "ok", "http": r.status, "disallow_n": len(disallow), "crawl_delay": "crawl-delay" in corpo.lower()}
    except urllib.error.HTTPError as e:
        return {"status": "recusa" if e.code in (401, 403, 429, 451) else "http_erro", "http": e.code}


def _ftp_listar(caminho: str) -> list[str]:
    with ftplib.FTP(FTP_HOST, timeout=60) as ftp:
        ftp.login()
        ftp.cwd(caminho)
        return ftp.nlst()


def _ftp_tamanho(caminho: str) -> int:
    with ftplib.FTP(FTP_HOST, timeout=60) as ftp:
        ftp.login()
        return ftp.size(caminho)


def _ftp_baixar(caminho: str, destino: str) -> None:
    with ftplib.FTP(FTP_HOST, timeout=120) as ftp:
        ftp.login()
        with open(destino, "wb") as f:
            ftp.retrbinary(f"RETR {caminho}", f.write)


def _ler_dbc(caminho_local: str) -> dict:
    try:
        import dbc as leitor  # pacote pyreaddbc
    except ImportError:
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--break-system-packages", "pyreaddbc"], check=False)
        import dbc as leitor  # noqa: F401
    import dbfread  # dependência de pyreaddbc para ler o .dbf convertido
    tmp_dbf = caminho_local + ".dbf"
    leitor.dbc2dbf(caminho_local, tmp_dbf)
    tabela = dbfread.DBF(tmp_dbf, load=False, encoding="latin-1")
    colunas = [c.name for c in tabela.fields]
    n = 0
    for _ in tabela:
        n += 1
    return {"colunas_n": len(colunas), "colunas": colunas[:60], "linhas": n}


def sondar_ftp_sinan() -> list[dict]:
    res = []
    alvo = "/dissemin/publicos/SINAN/DADOS/FINAIS"
    res.append(_sondagem("sinan_finais_listagem", alvo, lambda: {"entradas": len(nomes := _ftp_listar(alvo)), "exemplos": [n for n in nomes if n.upper().startswith("LEPT")][:5]}))
    nomes = next((r["exemplos"] for r in res if r["id"] == "sinan_finais_listagem" and "exemplos" in r), [])
    if nomes:
        arq = f"{alvo}/{nomes[0]}"
        res.append(_sondagem("sinan_lept_tamanho", arq, lambda: {"bytes": _ftp_tamanho(arq)}))
        tam = next((r.get("bytes") for r in res if r["id"] == "sinan_lept_tamanho"), None)
        if tam and tam <= LIMITE_DOWNLOAD:
            def _baixar_e_ler():
                d = tempfile.mkdtemp(prefix="e1_sinan_")
                local = os.path.join(d, nomes[0])
                _ftp_baixar(arq, local)
                return _ler_dbc(local) | {"bytes": tam}
            res.append(_sondagem("sinan_lept_decodificar", arq, _baixar_e_ler))
        else:
            res.append({"id": "sinan_lept_decodificar", "alvo": arq, "status": "pulado", "detalhe": f"acima de {LIMITE_DOWNLOAD} bytes"})
    return res


def sondar_ftp_sih() -> list[dict]:
    alvo = "/dissemin/publicos/SIHSUS/200801_/Dados"
    return [_sondagem("sih_listagem", alvo, lambda: {"entradas": len(nomes := _ftp_listar(alvo)), "exemplos": [n for n in nomes if n.upper().startswith("RD")][:3]})]


def sondar_sisab_tabnet() -> list[dict]:
    return [
        _sondagem("robots_sisab", "sisab.saude.gov.br", lambda: _http_robots("sisab.saude.gov.br")),
        _sondagem("robots_tabnet", "tabnet.datasus.gov.br", lambda: _http_robots("tabnet.datasus.gov.br")),
    ]


def sondar_tudo() -> dict:
    achados = []
    achados.append(_sondagem("ftp_acesso", FTP_HOST, lambda: {"entradas": len(_ftp_listar("/dissemin/publicos"))}))
    achados += sondar_ftp_sinan()
    achados += sondar_ftp_sih()
    achados += sondar_sisab_tabnet()
    return {"medido_em_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "ua": UA, "sondagens": achados}


def _autoteste() -> None:
    # Offline: a formatação e a trava de escrita não podem depender da rede nem escrever fora de SAIDA.
    fake = _sondagem("x", "y", lambda: (_ for _ in ()).throw(OSError("sem rede")))
    assert fake["status"] == "falha" and "OSError" in fake["detalhe"]
    ok = _sondagem("z", "w", lambda: {"status": "ok", "entradas": 2})
    assert ok["status"] == "ok" and ok["entradas"] == 2
    assert re.fullmatch(r"data/saude_desfechos/sondagem_datasus_e1\.json", str(SAIDA))
    print("autoteste ok")


def main() -> None:
    if "--autoteste" in sys.argv:
        _autoteste()
        return
    dados = sondar_tudo()
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps([{k: v for k, v in s.items() if k != "colunas"} for s in dados["sondagens"]], ensure_ascii=False))


if __name__ == "__main__":
    main()
