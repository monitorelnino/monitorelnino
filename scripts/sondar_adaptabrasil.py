#!/usr/bin/env python3
"""Sonda do AdaptaBrasil (ramo de válvula, nunca mesclado). Só leitura, cliente identificado.

Uso: sondar_adaptabrasil.py lista            -> id, nível, setor, nome, anos, cenários
     sondar_adaptabrasil.py total ID ANO     -> UM GET /total/BR/municipio/ID/null/ANO/csv (cabeçalho e 12 linhas)
"""
import json
import sys

BASE = "https://sistema.adaptabrasil.mcti.gov.br/api"


def main(argv):
    from coletores_base import buscar
    if argv[0] == "lista":
        for n in json.loads(buscar(BASE + "/hierarquia", timeout=120)):
            anos = ",".join(str(a.get("year")) for a in (n.get("years_description") or []))
            cen = ",".join(f'{c.get("value")}={c.get("label")}' for c in (n.get("scenarios") or []))
            print(f'IND> {n.get("id")}|n{n.get("level")}|sep{n.get("sep_id")}|{n.get("shortname")}|{anos}|{cen}|mestre={n.get("indicator_id_master")}')
        return 0
    corpo = buscar(f"{BASE}/total/BR/municipio/{argv[1]}/null/{argv[2]}/csv", timeout=120)
    linhas = corpo.decode("utf-8", "replace").splitlines()
    print(f"TOTAL> {len(corpo)} bytes, {len(linhas)} linhas")
    for ln in linhas[:12]:
        print("TOTAL>", ln[:300])
    return 0


if __name__ == "__main__":
    sys.path.insert(0, __file__.rsplit("/", 2)[0])
    sys.exit(main(sys.argv[1:]))
