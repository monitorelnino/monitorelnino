#!/usr/bin/env python3
"""Risco de base do município (AdaptaBrasil, MCTI/INPE/RNP): etapa 1, o catálogo de indicadores.

Handover `HANDOVER_RISCO_DE_BASE_ADAPTABRASIL_03-11-2026` §3; coleta por válvula `coleta-dia/*`
(dado de base, sem elo na noite; central, 05/11/2026). Crédito: "Fonte: AdaptaBrasil, MCTI" + data
da consulta. PESO ZERO: não escreve em `indice.json`, `estados.json`, `saude_uf.json`,
`municipios.json` nem `monitor_saude.json`; não é "risco projetado do ciclo".

ETAPA 1 (esta): `GET {API}/hierarquia` (público, 200, provado em 04/11) vira `data/risco_base/
catalogo.json`: id, nome, setor, anos, cenários e resolução padrão de cada indicador, com hash e data.
Sem valor por município: a rota `/total` devolveu erro do servidor da fonte (04/11) e a de mapa não
foi lida; valor ausente é lacuna declarada, nunca zero. Recusa (401/403/429/451) = parar e registrar.

USO
  python3 coletar_risco_base.py --autoteste
  python3 coletar_risco_base.py            # só pela válvula coleta-dia/*
"""
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

API = "https://sistema.adaptabrasil.mcti.gov.br/api"
SAIDA = RAIZ / "data" / "risco_base" / "catalogo.json"
ORIGEM = "coletar_risco_base"


def nos_de(corpo) -> list:
    """Lista de nós da hierarquia, ou []. Função pura; aceita lista ou dict com uma lista."""
    dado = json.loads(corpo) if isinstance(corpo, (bytes, str)) else corpo
    if isinstance(dado, dict):
        dado = next((v for v in dado.values() if isinstance(v, list)), [])
    return dado if isinstance(dado, list) else []


def catalogo_de(nos: list) -> list:
    """Campos do nó que o cartão vai precisar; o que a fonte não traz fica None. Função pura."""
    fora = []
    for n in nos:
        if not isinstance(n, dict) or n.get("id") is None:
            continue
        res = (n.get("menu_structure") or {}).get("defaultclippingresolution")
        fora.append({"id": n["id"], "nome": n.get("nome"), "level": n.get("level"),
                     "sep_id": n.get("sep_id"), "anos": n.get("years_description"),
                     "cenarios": n.get("scenarios"), "resolucao_padrao": res})
    return sorted(fora, key=lambda x: str(x["id"]))


def problemas(catalogo: list) -> list:
    """Falhas que impedem a gravação. Função pura."""
    if not catalogo:
        return ["hierarquia vazia ou em formato inesperado"]
    return [f"{len(catalogo)} nós sem nome" for _ in [0] if all(c["nome"] is None for c in catalogo)]


def autoteste() -> int:
    nos = [{"id": 22, "nome": "Balanço hídrico", "level": 5, "sep_id": 1,
            "years_description": [{"year": 2020}], "scenarios": [49, 50],
            "menu_structure": {"defaultclippingresolution": {"clipping": "BR", "resolution": "municipio"}}},
           {"id": 7}, {"nome": "sem id"}, "lixo"]
    c = catalogo_de(nos_de(json.dumps(nos)))
    casos = [
        ("ignora nó sem id e lixo", sorted(x["id"] for x in c) == [7, 22]),
        ("campo ausente fica None, não zero", {x["id"]: x for x in c}[7]["nome"] is None),
        ("resolução padrão lida", {x["id"]: x for x in c}[22]["resolucao_padrao"]["resolution"] == "municipio"),
        ("dict com lista também vale", len(nos_de({"nodes": nos})) == 4),
        ("formato estranho vira lista vazia", nos_de("3") == [] and nos_de({"a": 1}) == []),
        ("vazio reprova", problemas([]) != []),
        ("bom passa", problemas(c) == []),
        ("sem nenhum nome reprova", problemas([{"nome": None}]) != []),
    ]
    ruins = [n for n, ok in casos if not ok]
    for n, ok in casos:
        print(f"  {'OK  ' if ok else 'FALHA'} {n}")
    print(f"{'X AUTOTESTE: ' + str(len(ruins)) + ' reprovado(s)' if ruins else 'OK AUTOTESTE — ' + str(len(casos)) + ' casos, sem rede e sem escrita em data/.'}")
    return 1 if ruins else 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    from coletores_base import buscar, gravar_em, hoje_editorial, preservar_evidencia, sha256
    url = f"{API}/hierarquia"
    corpo = buscar(url, timeout=120, origem=ORIGEM)
    cat = catalogo_de(nos_de(corpo))
    ruins = problemas(cat)
    if ruins:
        print("X VALIDAÇÃO — nada foi gravado:", *ruins, sep="\n   - ")
        return 1
    preservar_evidencia(corpo, url, "json", ORIGEM)
    gravar_em(SAIDA, {
        "_governanca": ("Catálogo de indicadores do AdaptaBrasil (MCTI/INPE/RNP). Peso zero; não é "
                        "risco do ciclo. Sem valor por município nesta etapa: ausência é lacuna "
                        "declarada. Fonte: AdaptaBrasil, MCTI."),
        "fonte": {"url": url, "consultado_em": hoje_editorial().isoformat(), "hash": sha256(corpo),
                  "edicao_da_fonte": None,
                  "lacuna_edicao": "edição não datada pela fonte até a consulta"},
        "indicadores": cat})
    print(f"{SAIDA.relative_to(RAIZ)} gravado · {len(cat)} nós")
    return 0


if __name__ == "__main__":
    sys.exit(main())
