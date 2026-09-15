#!/usr/bin/env python3
"""
gerar_prioritarios.py — municípios prioritários (proxy populacional), fonte única
==================================================================================
"Municípios prioritários" é o rótulo que o Cadastro Nacional de Municípios com
Áreas Suscetíveis a Desastres (Lei 12.608/2012; MIDR/SEDEC) usa para os
municípios que o órgão federal aponta com maior risco de desastre — histórico
de decretos, população exposta, vulnerabilidade. A lista nome a nome não é
pública sem acesso autenticado: o Monitor usa uma APROXIMAÇÃO declarada — para
cada UF, os N municípios mais populosos, onde N é a contagem por UF do
Cadastro (Tabela 2, pública) — e rotula essa aproximação como tal em toda
superfície (mapa, busca, tooltip). Nunca apresentada como a lista oficial.

Esta função (`municipios_prioritarios()`) é a FONTE ÚNICA da aproximação:
antes cada consumidor (mapa em defesa-civil.js) recomputava do zero, no
cliente; agora um só cálculo, aqui, grava `data/municipios_prioritarios.json`,
e tanto o mapa quanto a busca em prefeituras.html leem o mesmo arquivo — nunca
podem divergir um do outro.

python gerar_prioritarios.py            # grava data/municipios_prioritarios.json
python gerar_prioritarios.py --autoteste
"""
import sys
from pathlib import Path
from coletores_base import ler, gravar, rodar_autoteste

RAIZ = Path(__file__).resolve().parent

# Cadastro Nacional de Municípios com Áreas Suscetíveis a Desastres, contagem por UF
# (Tabela 2, pública, MIDR — aproximação por população dentro de cada UF; ver docstring).
CADASTRO_UF_N = {"AC": 20, "AL": 47, "AM": 59, "AP": 14, "BA": 144, "CE": 80, "DF": 1, "ES": 71, "GO": 25, "MA": 113,
                 "MG": 306, "MS": 33, "MT": 40, "PA": 97, "PB": 43, "PE": 108, "PI": 47, "PR": 84, "RJ": 76, "RN": 32,
                 "RO": 14, "RR": 5, "RS": 206, "SC": 218, "SE": 17, "SP": 177, "TO": 18}
CATS_PUBLICADO = {"plano", "plano_antigo", "plano_elaboracao", "estrutura", "decreto", "coberto_estadual"}


def municipios_prioritarios(referencia: list, populacao: dict, pontos_mapa: list) -> list:
    """Para cada UF, os N municípios mais populosos entre os que têm coordenada na malha de
    referência (N = CADASTRO_UF_N[uf]); marca 'publicado' quando o município já tem instrumento
    localizado (categoria em CATS_PUBLICADO) em pontos_mapa. Devolve lista ordenada por UF, nome.
    Função pura — nada de rede, nada de estimativa fora da regra declarada."""
    por_uf = {}
    for m in referencia:
        por_uf.setdefault(m["uf"], []).append(m)
    publicados = {(p["uf"], p["nome"]) for p in pontos_mapa if p.get("categoria") in CATS_PUBLICADO}
    saida = []
    for uf, n in CADASTRO_UF_N.items():
        candidatos = sorted(
            por_uf.get(uf, []),
            key=lambda m: populacao.get(f"{int(m['codigo_ibge']):07d}", 0),
            reverse=True,
        )[:n]
        for m in candidatos:
            saida.append({
                "nome": m["nome"], "uf": uf,
                "codigo_ibge": int(m["codigo_ibge"]),
                "lat": m["lat"], "lon": m["lon"],
                "publicado": (uf, m["nome"]) in publicados,
            })
    saida.sort(key=lambda x: (x["uf"], x["nome"]))
    return saida


def gerar() -> int:
    referencia = ler("municipios_ibge_referencia.json", []) or []
    populacao = ler("populacao_censo2022.json", {}) or {}
    pontos_mapa = ler("pontos_mapa.json", []) or []
    lista = municipios_prioritarios(referencia, populacao, pontos_mapa)
    publicados = sum(1 for x in lista if x["publicado"])
    saida = {
        "_governanca": ("Municípios prioritários — aproximação populacional do Cadastro Nacional de Municípios "
                         "com Áreas Suscetíveis a Desastres (MIDR/SEDEC, Lei 12.608/2012). A lista nome a nome do "
                         "Cadastro não é pública sem acesso autenticado; para cada UF, esta lista toma os N "
                         "municípios mais populosos (N = contagem pública do Cadastro por UF), rotulada em toda "
                         "superfície como aproximação, nunca como a lista oficial. 'publicado' = já tem instrumento "
                         "(plano, decreto ou estrutura) localizado até o corte. Fonte única de gerar_prioritarios.py; "
                         "mapa (defesa-civil.html) e busca (prefeituras.html) leem este arquivo — nunca recomputam."),
        "cadastro_uf_n": CADASTRO_UF_N, "total": len(lista), "publicados": publicados,
        "municipios": lista,
    }
    gravar("municipios_prioritarios.json", saida)
    print(f"prioritarios: {len(lista)} municípios (aproximação), {publicados} com instrumento publicado")
    return 0


def autoteste() -> int:
    def t1():
        ref = [{"nome": "A", "uf": "XX", "codigo_ibge": 1, "lat": -1, "lon": -1},
               {"nome": "B", "uf": "XX", "codigo_ibge": 2, "lat": -2, "lon": -2},
               {"nome": "C", "uf": "XX", "codigo_ibge": 3, "lat": -3, "lon": -3}]
        pop = {"0000001": 100, "0000002": 300, "0000003": 200}
        pontos = [{"uf": "XX", "nome": "B", "categoria": "plano"}]
        global CADASTRO_UF_N
        antigo = dict(CADASTRO_UF_N); CADASTRO_UF_N.clear(); CADASTRO_UF_N["XX"] = 2
        r = municipios_prioritarios(ref, pop, pontos)
        CADASTRO_UF_N.clear(); CADASTRO_UF_N.update(antigo)
        nomes = sorted(x["nome"] for x in r)
        return nomes == ["B", "C"] and next(x for x in r if x["nome"] == "B")["publicado"] is True \
            and next(x for x in r if x["nome"] == "C")["publicado"] is False

    def t2():  # UF sem municípios de referência não quebra
        return municipios_prioritarios([], {}, []) is not None

    return rodar_autoteste({
        "toma os N mais populosos por UF; marca 'publicado' pelo mapa de pontos": t1,
        "negativo: UF sem municípios não quebra": t2,
    })


if __name__ == "__main__":
    sys.exit(autoteste() if "--autoteste" in sys.argv else gerar())
