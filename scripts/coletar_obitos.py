#!/usr/bin/env python3
"""Óbitos com causa: SIM preliminar (DATASUS) e Registro Civil por causa — sondagem (janela E2).

A perna rápida sem causa já existe e não muda: `coletar_obitos_registro_civil.py` (óbitos
registrados por UF e mês, `data/saude_desfechos/obitos_registro_civil.json`). Este arquivo é a
outra perna que a decisão de 29/09/2026 pediu: óbito com causa. Duas rotas a medir:

- SIM preliminar no FTP do DATASUS (`DO<UF><AAAA>.dbc`, causa básica codificada; defasagem de
  meses). O `.dbc` se lê com o leitor de `coletar_sih.py` — importado, nunca copiado.
- Registro Civil por causa (painel "registral" da Arpen): óbito REGISTRADO, sem causa básica
  codificada; serve de sinal se a API responder por causa sem chave (HANDOVER_SUS_DESFECHOS §2.5).
- OpenDataSUS: o que o portal publica do SIM, com a data de cada recurso.

`--sondar` só mede e imprime (o rastro de robots é o da porta comum); nenhuma série vai a `data/` até a estrutura comum da E1 estar na `main`.

TRAVAS: estrutural (nunca escreve em estados/saude_uf/municipios/indice/monitor_saude; o autoteste
lê o fonte); de campo (não produz pista nem registro promovível); de processo (a sondagem não grava).

USO
  python3 scripts/coletar_obitos.py --autoteste
  python3 scripts/coletar_obitos.py --sondar [--uf AC]
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
import time

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "scripts"))

from coletar_sih import PAUSA, UFS, baixar_ftp, ler_dbc, listar_ftp  # noqa: E402
from coletar_obitos_registro_civil import API as API_REGISTRO  # noqa: E402

BANCO_PROIBIDO = ("estados.json", "saude_uf.json", "municipios.json", "indice.json",
                  "monitor_saude.json")
FTP_SIM = {"preliminar": "/dissemin/publicos/SIM/PRELIM/DORES",
           "consolidado": "/dissemin/publicos/SIM/CID10/DORES"}
CKAN = "https://opendatasus.saude.gov.br/api/3/action/package_search"
REGISTRO = "https://transparencia.registrocivil.org.br"
# Rotas do painel por causa a sondar (não adivinhadas: as que o JavaScript do painel declara são
# impressas antes, e só estas duas, do painel especial público, são pedidas diretamente).
ROTAS_CAUSA = ("/api/covid-covid-registral", "/api/covid-cardiaco")
GRAFICOS = ("chart1", "chart2", "chart3", "chart4")


def ultimo_ano_por_uf(itens: list) -> dict:
    """{UF: (AAAA, tamanho, data_do_arquivo)} do `DO<UF><AAAA>.dbc` mais novo. Função pura."""
    out = {}
    for nome, tam, data in itens:
        m = re.fullmatch(r"DO([A-Z]{2})(\d{4})\.DBC", nome.upper())
        if m and m.group(1) in UFS and (m.group(1) not in out or m.group(2) > out[m.group(1)][0]):
            out[m.group(1)] = (m.group(2), tam, data)
    return out


def obitos_por_mes(registros) -> dict:
    """{'AAAA-MM': n} pela data do óbito (DTOBITO, ddmmaaaa). Data ilegível conta em '?'."""
    out = {}
    for r in registros:
        d = r.get("DTOBITO", "")
        k = f"{d[4:8]}-{d[2:4]}" if re.fullmatch(r"\d{8}", d) else "?"
        out[k] = out.get(k, 0) + 1
    return dict(sorted(out.items()))


def rotas_api_no_js(js: str) -> list:
    """Rotas '/api/...' citadas no JavaScript de uma página. Função pura."""
    return sorted(set(re.findall(r"/api/[A-Za-z0-9_\-/]+", js)))


def sondar(uf: str = "AC") -> int:
    from coletores_base import buscar_uma_vez as _uma_vez

    def buscar_uma_vez(url, timeout=60):  # pausa de §11 entre pedidos; o resto é a porta comum
        time.sleep(PAUSA)
        return _uma_vez(url, timeout=timeout)
    for rotulo, d in FTP_SIM.items():
        try:
            itens = listar_ftp(d)
            ult = ultimo_ano_por_uf(itens)
            print(f"[obitos] SIM {rotulo} {d}: {len(itens)} arquivos; último por UF: "
                  + "; ".join(f"{u} {ult.get(u)}" for u in UFS))
        except Exception as e:  # noqa: BLE001
            print(f"[obitos] SIM {rotulo} {d}: falhou ({type(e).__name__}: {str(e)[:160]})")
            continue
        if rotulo == "preliminar" and uf in ult:
            nome = f"DO{uf}{ult[uf][0]}.dbc"
            t = time.time()
            try:
                regs = list(ler_dbc(baixar_ftp(f"{d}/{nome}"), ["DTOBITO", "CAUSABAS", "CODMUNRES"]))
                print(f"[obitos] {nome}: {len(regs)} óbitos em {time.time() - t:.1f}s; por mês: "
                      f"{obitos_por_mes(regs)}; causas J: {sum(r['CAUSABAS'].startswith('J') for r in regs)}; "
                      f"causas I: {sum(r['CAUSABAS'].startswith('I') for r in regs)}")
            except Exception as e:  # noqa: BLE001
                print(f"[obitos] {nome}: falhou ({type(e).__name__}: {str(e)[:200]})")
    for q in ("SIM", "mortalidade"):
        try:
            b = buscar_uma_vez(f"{CKAN}?q={q}&rows=15", timeout=60)
            if not b.lstrip().startswith(b"{"):
                print(f"[obitos] OpenDataSUS q={q}: não é JSON ({len(b)} bytes): {b[:300]!r}")
                continue
            r = json.loads(b)
            for p in r.get("result", {}).get("results", []):
                recs = [(x.get("name"), x.get("url"), x.get("last_modified") or x.get("created"))
                        for x in p.get("resources", [])][-6:]
                print(f"[obitos] OpenDataSUS q={q}: {p.get('name')} · {p.get('metadata_modified')} · {recs}")
        except Exception as e:  # noqa: BLE001
            print(f"[obitos] OpenDataSUS q={q}: falhou ({type(e).__name__}: {str(e)[:160]})")
    try:
        print(f"[obitos] Registro Civil base: {buscar_uma_vez(API_REGISTRO + '?start_date=2026-09-01&end_date=2026-09-30', timeout=60)[:300]!r}")
    except Exception as e:  # noqa: BLE001
        print(f"[obitos] Registro Civil base: falhou ({type(e).__name__}: {str(e)[:160]})")
    try:
        html = buscar_uma_vez(REGISTRO + "/especial-covid", timeout=60).decode("utf-8", "replace")
        print(f"[obitos] Registro Civil página: rotas no HTML {rotas_api_no_js(html)[:20]}; scripts "
              f"{re.findall(r'src=.([^\"\' >]+)', html)[:12]}")
        for src in re.findall(r'src="([^"]+\.js[^"]*)"', html)[:8]:
            url = src if src.startswith("http") else REGISTRO + "/" + src.lstrip("/")
            try:
                rotas = rotas_api_no_js(buscar_uma_vez(url, timeout=60).decode("utf-8", "replace"))
                print(f"[obitos] Registro Civil JS {src}: {rotas[:40]}")
            except Exception as e:  # noqa: BLE001
                print(f"[obitos] Registro Civil JS {src}: falhou ({type(e).__name__})")
    except Exception as e:  # noqa: BLE001
        print(f"[obitos] Registro Civil página: falhou ({type(e).__name__}: {str(e)[:160]})")
    for rota, (ini, fim) in [(r, p) for r in ROTAS_CAUSA for p in (("2026-09-01", "2026-09-30"), ("2021-04-01", "2021-04-30"))]:
        for g in GRAFICOS[:2]:
            url = (f"{REGISTRO}{rota}?start_date={ini}&end_date={fim}&state=CE&city_id=Todos"
                   f"&chart={g}&places[]=HOSPITAL&places[]=DOMICILIO&places[]=VIA_PUBLICA&places[]=OUTROS")
            try:
                print(f"[obitos] Registro Civil {rota} {ini} {g}: {buscar_uma_vez(url, timeout=60)[:500]!r}")
            except Exception as e:  # noqa: BLE001
                print(f"[obitos] Registro Civil {rota} {ini} {g}: falhou ({type(e).__name__}: {str(e)[:200]})")
    return 0


def autoteste() -> int:
    erros = []
    ult = ultimo_ano_por_uf([("DOAC2025.dbc", 5, "20260901"), ("DOAC2026.DBC", 6, "20261001"),
                             ("DOXX2026.dbc", 1, ""), ("DOEXT26.dbc", 1, "")])
    if ult != {"AC": ("2026", 6, "20261001")}:
        erros.append(f"ultimo_ano_por_uf: {ult}")
    m = obitos_por_mes([{"DTOBITO": "15082026"}, {"DTOBITO": "01082026"}, {"DTOBITO": ""}])
    if m != {"2026-08": 2, "?": 1}:
        erros.append(f"obitos_por_mes: {m}")
    if rotas_api_no_js('a("/api/record/death?x");b="/api/covid-cardiaco"') != ["/api/covid-cardiaco", "/api/record/death"]:
        erros.append("rotas_api_no_js")
    fonte = pathlib.Path(__file__).read_text(encoding="utf-8")
    corpo = fonte.split("BANCO_PROIBIDO = (", 1)[1].split(")", 1)[1]
    for arq in BANCO_PROIBIDO:
        if re.search(r"(gravar|gravar_em|open)\([^)]*" + re.escape(arq), corpo):
            erros.append(f"trava estrutural: escrita em {arq}")
    if re.search(r"\bgravar(_em|_lote|_pista)?\(", corpo.split("def autoteste", 1)[0]):
        erros.append("trava de processo: a sondagem não pode gravar")
    print("autoteste coletar_obitos:", "OK" if not erros else "FALHOU")
    for e in erros:
        print("  -", e)
    return 1 if erros else 0


def main() -> int:
    a = sys.argv[1:]
    if "--autoteste" in a:
        return autoteste()
    if "--sondar" in a:
        return sondar(a[a.index("--uf") + 1].upper() if "--uf" in a else "AC")
    print("coletar_obitos: só --sondar e --autoteste até a estrutura comum da E1 estar na main")
    return 2


if __name__ == "__main__":
    sys.exit(main())
