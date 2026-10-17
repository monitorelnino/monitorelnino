#!/usr/bin/env python3
"""Óbitos: série por UF e mês na estrutura comum de desfechos (faixa E2).

Duas pernas, como decidido em 29/09/2026: o Registro Civil (óbito REGISTRADO, dias de atraso, sem
causa) como sinal, e o SIM (óbito por causa básica, meses de atraso) como série. A leitura do
Registro Civil é a de `coletar_obitos_registro_civil.py` (importada, nunca copiada); este arquivo
só estende o período até a base da faixa habitual e escreve no arquivo novo.

USO
  python3 coletar_obitos.py --autoteste
  python3 coletar_obitos.py --sondar      # só mede e imprime; não grava nada
"""
import datetime
import ftplib
import io
import json
import pathlib
import re
import sys
import time

RAIZ = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

from coletar_obitos_registro_civil import API, meses, serie_de  # noqa: E402

RC_BASE = "https://transparencia.registrocivil.org.br"
LOCAIS = "places[]=HOSPITAL&places[]=DOMICILIO&places[]=VIA_PUBLICA&places[]=OUTROS"
# Painéis por causa que o portal publicou (especial covid e cardíaco); a sonda diz se respondem.
RC_CAUSAS = {
    "respiratorias": "/api/covid-covid-registral?start_date={ini}&end_date={fim}&state=Todos"
                     "&city_id=Todos&chart=chart5&" + LOCAIS + "&diffCity=false&cor_pele=I",
    "cardiacas": "/api/covid-cardiaco?start_date={ini}&end_date={fim}&state=Todos&city_id=Todos"
                 "&chart=chartCardiac1&" + LOCAIS + "&diffCity=false&cor_pele=I",
}
FTP_HOST = "ftp.datasus.gov.br"
FTP_SENHA = "monitorelnino.com.br"
FTP_SIM = ["/dissemin/publicos/SIM/PRELIM/DORES", "/dissemin/publicos/SIM/CID10/DORES"]
PORTAL_CONJUNTO = "https://dadosabertos.saude.gov.br/dataset/sim"
PORTAL_BUSCA = "https://dadosabertos.saude.gov.br/dataset?q={q}"
RE_DO = re.compile(r"^DO([A-Z]{2})(\d{4})\.DBC$", re.I)
INICIO_FAIXA = datetime.date(2019, 1, 1)


def meses_desde(inicio: datetime.date, ate: datetime.date) -> list:
    """Janelas mensais de `inicio` até o mês de `ate`, reaproveitando `meses`. Função pura."""
    n = (ate.year - inicio.year) * 12 + ate.month - inicio.month + 1
    return meses(ate, max(n, 0)) if n > 0 else []


def ultimo_ano_por_uf(nomes) -> dict:
    """{UF: ano} do arquivo DO mais recente por UF na listagem do SIM. Função pura."""
    out = {}
    for n in nomes:
        m = RE_DO.match(n.strip())
        if m:
            uf, ano = m.group(1).upper(), int(m.group(2))
            out[uf] = max(ano, out.get(uf, 0))
    return out


def sondar() -> int:
    from coletores_base import buscar, robots_de
    from coletar_sg_esus import payload_do_portal
    hoje = datetime.date.today()
    print(f"== Registro Civil · {RC_BASE} · {hoje}")
    try:
        r = robots_de("transparencia.registrocivil.org.br")
        print(f"robots: {r.get('status')} · crawl-delay {r.get('crawl_delay')}")
    except Exception as e:  # noqa: BLE001
        print(f"robots: falhou ({type(e).__name__})")
    for ini, fim in [(datetime.date(2019, 1, 1), datetime.date(2019, 1, 31)),
                     (datetime.date(2026, 9, 1), datetime.date(2026, 9, 30))]:
        url = f"{API}?start_date={ini}&end_date={fim}"
        try:
            s = serie_de({(ini, fim): json.loads(buscar(url, timeout=60))})
            print(f"  óbitos registrados {ini:%Y-%m}: BR {s.get('BR')} · UFs {len(s) - 1}")
        except Exception as e:  # noqa: BLE001
            print(f"  óbitos registrados {ini:%Y-%m}: falhou ({type(e).__name__}: {str(e)[:120]})")
    for nome, caminho in RC_CAUSAS.items():
        url = RC_BASE + caminho.format(ini="2026-08-01", fim="2026-08-31")
        try:
            corpo = buscar(url, timeout=60)
            print(f"  causa {nome}: {len(corpo)} bytes · {corpo[:400]!r}")
        except Exception as e:  # noqa: BLE001
            print(f"  causa {nome}: falhou ({type(e).__name__}: {str(e)[:160]})")

    print(f"== SIM · FTP {FTP_HOST}")
    try:
        f = ftplib.FTP(FTP_HOST, timeout=60)
        f.login("anonymous", FTP_SENHA)
        for d in FTP_SIM:
            try:
                f.cwd(d)
                nomes = f.nlst()
                ult = ultimo_ano_por_uf(nomes)
                anos = sorted(set(ult.values()))
                print(f"  {d}: {len(nomes)} nomes · anos mais recentes {anos[-3:]} · "
                      f"UFs no último: {sorted(u for u, a in ult.items() if anos and a == anos[-1])}")
                print(f"    amostra: {sorted(nomes)[-6:]}")
                if ult and "PRELIM" in d:
                    from coletar_sih import ler_dbc
                    for n in sorted(x for x in nomes if x.upper().startswith("DOAC"))[-1:]:
                        print(f"    {n}: {f.sendcmd(f'MDTM {n}')} · {f.size(n)} bytes")
                        buf = io.BytesIO()
                        f.retrbinary(f"RETR {n}", buf.write)
                        regs = ler_dbc(buf.getvalue())
                        por_mes = {}
                        for r in regs:
                            dt = str(r.get("DTOBITO") or "")
                            por_mes[dt[4:8] + "-" + dt[2:4]] = por_mes.get(dt[4:8] + "-" + dt[2:4], 0) + 1
                        print(f"    registros {len(regs)} · colunas {list(regs[0])[:40] if regs else []}")
                        print(f"    óbitos por mês de ocorrência (DTOBITO): {dict(sorted(por_mes.items()))}")
            except Exception as e:  # noqa: BLE001
                print(f"  {d}: falhou ({type(e).__name__}: {e})")
        f.quit()
    except Exception as e:  # noqa: BLE001
        print(f"FTP: falhou ({type(e).__name__}: {e})")

    print("== Registro Civil · endereços /api/ que o próprio portal chama")
    try:
        pag = buscar(RC_BASE + "/especial-covid", timeout=60).decode("utf-8", "replace")
        js = sorted(set(re.findall(r'src="([^"]+\.js)"', pag)))
        print(f"  scripts: {js[:8]}")
        apis = set()
        for s_ in js[:8]:
            u = s_ if s_.startswith("http") else RC_BASE + "/" + s_.lstrip("/")
            apis |= set(re.findall(r'["\'`](/api/[A-Za-z0-9_\-/]+)', buscar(u, timeout=60).decode("utf-8", "replace")))
        print(f"  /api/ no código do portal: {sorted(apis)}")
    except Exception as e:  # noqa: BLE001
        print(f"  falhou ({type(e).__name__}: {str(e)[:160]})")

    print("== SIM · conjunto 'sim' no portal")
    try:
        p = payload_do_portal(buscar(PORTAL_CONJUNTO, timeout=60).decode("utf-8", "replace"))
        pp = ((p.get("props") or {}).get("pageProps") or {})
        pac = pp.get("package") or pp
        print(f"  modificado {pac.get('metadata_modified')} · recursos:")
        for r in (pac.get("resources") or [])[:40]:
            print(f"    {r.get('format')} · {r.get('name')} · {r.get('url') or ''} · "
                  f"{(r.get('description') or '')[:200]!r}")
    except Exception as e:  # noqa: BLE001
        print(f"  falhou ({type(e).__name__}: {str(e)[:160]})")

    print("== SIM · Portal de Dados Abertos do SUS")
    for q in ("mortalidade", "sim", "obitos"):
        try:
            p = payload_do_portal(buscar(PORTAL_BUSCA.format(q=q), timeout=60).decode("utf-8", "replace"))
            pacotes = ((p.get("props") or {}).get("pageProps") or {}).get("packages") or []
            print(f"  q={q}: {[(x.get('name'), x.get('metadata_modified', '')[:10]) for x in pacotes][:12]}")
        except Exception as e:  # noqa: BLE001
            print(f"  q={q}: falhou ({type(e).__name__}: {str(e)[:160]})")
        time.sleep(2)
    return 0


def autoteste() -> int:
    d = datetime.date
    casos = []
    j = meses_desde(INICIO_FAIXA, d(2026, 10, 17))
    casos.append(("de jan/2019 a out/2026 são 94 meses", len(j) == 94))
    casos.append(("começa em jan/2019 e termina no mês corrente",
                  j[0] == (d(2019, 1, 1), d(2019, 1, 31)) and j[-1][0] == d(2026, 10, 1)))
    casos.append(("início depois do fim não dá janela", meses_desde(d(2027, 1, 1), d(2026, 1, 1)) == []))
    casos.append(("a série é a do coletor existente (importada)",
                  serie_de({(d(2019, 1, 1), d(2019, 1, 31)): {"data": [{"name": "AC", "total": 3}]}})
                  == {"AC": {"2019-01": 3}, "BR": {"2019-01": 3}}))
    casos.append(("último ano do SIM por UF",
                  ultimo_ano_por_uf(["DOAC2024.dbc", "DOAC2025.DBC", "DOSP2024.dbc", "x.txt"])
                  == {"AC": 2025, "SP": 2024}))
    fonte = pathlib.Path(__file__).read_text(encoding="utf-8").split("def autoteste")[0]
    proibidos = ("estados.json", "saude_uf.json", "municipios.json", "indice.json", "monitor_saude.json",
                 "obitos_registro_civil.json")
    casos.append(("trava estrutural: não escreve no índice nem no arquivo da página atual",
                  not any(p in fonte for p in proibidos)))
    casos.append(("trava estrutural: a sondagem não grava", "gravar" not in fonte.split("def sondar")[1]))
    ruins = [n for n, ok in casos if not ok]
    for n, ok in casos:
        print(f"  {'OK  ' if ok else 'FALHA'} {n}")
    if ruins:
        print(f"X AUTOTESTE: {len(ruins)} caso(s) reprovado(s).")
        return 1
    print(f"OK AUTOTESTE — {len(casos)} casos, sem rede e sem escrita.")
    return 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    if "--sondar" in sys.argv:
        return sondar()
    print("coletar_obitos: a série espera a estrutura comum de desfechos (E1); use --sondar ou --autoteste")
    return 0


if __name__ == "__main__":
    sys.exit(main())
