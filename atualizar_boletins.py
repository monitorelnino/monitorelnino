#!/usr/bin/env python3
"""Vigia de boletins do Painel El Niño 2026-2027: só avisa, nunca grava.

Lê o índice mensal dos boletins na ANA com o mesmo leitor do coletor de sinais
(`coletar_sinais_risco.parse_indice_boletins`) e compara com `data/boletins.json`.
Quem grava o boletim e o aviso de leitura pendente é o coletor de sinais; aqui, um
número novo só aparece no log. Falha de rede é aviso e saída 0.
"""
import json, sys
from coletar_sinais_risco import BOLETINS, FONTES, _buscar, parse_indice_boletins


def main() -> int:
    """Consulta o índice da ANA e diz no log se há boletim mais novo que o registrado."""
    registrado = json.loads(BOLETINS.read_text(encoding="utf-8")).get("ultimo_boletim") or 0
    url = FONTES["painel_el_nino"]["endpoint"]
    try:
        indice = parse_indice_boletins(_buscar(url), url)
    except Exception as e:  # noqa: BLE001 — a vigia nunca derruba a rotina
        print(f"[aviso] não foi possível consultar {url}: {e}")
        return 0
    if indice.get("numero", 0) > registrado:
        print(f"[NOVO BOLETIM] nº {indice['numero']} publicado ({indice['url']}); "
              f"o risco por UF registrado é o do nº {registrado}.")
    else:
        print(f"Nenhum boletim novo (último conhecido: nº {registrado}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
