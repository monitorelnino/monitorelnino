#!/usr/bin/env python3
"""Manutenção: põe a ORIGEM das pistas já existentes no vocabulário do esquema.

Declarado em `MANUTENCAO` (portão `verificar_escritor_de_pista.py`) desde 06/10/2026 — e o arquivo
não existia. Este é ele.

O QUE ELE CORRIGE
-----------------
Medição de 09/10/2026, pista por pista, nas cinco filas ativas (13.503 pistas):

    10.018  (sem origem nenhuma)        fora do esquema
     1.733  rede_social_oficial         fora do esquema
       888  busca_web                   ok
       419  seguimento_busca_oficial    fora do esquema
       185  diario_consorciado          ok
        59  seguimento                  fora do esquema
        55  doe                         ok
        54  querido_diario              ok
        52  seguimento_querido_diario   fora do esquema
        15  seguimento_link_noticia     fora do esquema
        12  rebaixamento C10            fora do esquema
         6  imprensa                    ok
         5  diario                      ok
         1  agencia_oficial             fora do esquema
         1  rede_social                 ok

`schemas/pista.json` declara as origens válidas desde 03/10, e nada conferia isso na gravação: as
pistas que entraram antes da porta ficaram com o nome que o coletor usava, e quem lê a fila por
origem lê nove nomes e vê catorze.

O QUE ELE FAZ, E O QUE NÃO FAZ
------------------------------
- traduz a origem do coletor para a canônica, pelo mesmo mapa da porta (`pistas.ORIGEM_CANONICA`),
  guardando o nome anterior em `origem_do_coletor` — corrigir sem registrar é perder a trilha;
- pista sem origem recebe `desconhecida`, que o esquema declara: a origem dela NÃO se adivinha
  pela fila em que mora, e inventar proveniência é pior que declarar a lacuna;
- não apaga pista, não muda status, não decide, não julga e não toca URL, alvo, tipo nem nível;
- não grava pista nova — entrada de pista continua sendo só pela porta.

USO
    python3 scripts/migrar_pistas_para_o_esquema.py              # relatório, nada escrito
    python3 scripts/migrar_pistas_para_o_esquema.py --aplicar
    python3 scripts/migrar_pistas_para_o_esquema.py --autoteste
"""
from __future__ import annotations

import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "scripts"))

FILAS = ("pistas_imprensa.json", "pistas_descobertas.json", "pistas_doe.json",
         "pistas_querido_diario.json")


def origem_nova(pista: dict, mapa: dict, validas: set, desconhecida: str):
    """A origem canônica desta pista, ou None quando nada muda. Função pura."""
    atual = str(pista.get("origem") or "").strip()
    if not atual:
        return desconhecida
    if atual in validas:
        return None
    traduzida = mapa.get(atual)
    return traduzida if traduzida and traduzida != atual else None


def migrar(pistas: list, mapa: dict, validas: set, desconhecida: str) -> dict:
    """Aplica a tradução na lista, no lugar. Devolve a contagem por origem resultante."""
    contagem = {}
    for p in pistas:
        nova = origem_nova(p, mapa, validas, desconhecida)
        if nova:
            anterior = str(p.get("origem") or "")
            if anterior and not p.get("origem_do_coletor"):
                p["origem_do_coletor"] = anterior
            p["origem"] = nova
            contagem[nova] = contagem.get(nova, 0) + 1
    return contagem


def autoteste() -> int:
    falhas = []

    def ok(nome, cond):
        print(("  ok " if cond else "  FALHA ") + nome)
        if not cond:
            falhas.append(nome)

    MAPA = {"rede_social_oficial": "rede_social", "seguimento": "imprensa"}
    VAL = {"rede_social", "imprensa", "busca_web", "desconhecida"}

    ok("origem do coletor vira a canônica",
       origem_nova({"origem": "rede_social_oficial"}, MAPA, VAL, "desconhecida") == "rede_social")
    ok("origem já canônica não muda",
       origem_nova({"origem": "busca_web"}, MAPA, VAL, "desconhecida") is None)
    ok("sem origem recebe a lacuna declarada",
       origem_nova({}, MAPA, VAL, "desconhecida") == "desconhecida")
    ok("origem desconhecida e sem mapa fica como está (o portão a verá)",
       origem_nova({"origem": "inventada"}, MAPA, VAL, "desconhecida") is None)

    lista = [{"origem": "rede_social_oficial", "url": "u1"}, {"url": "u2"},
             {"origem": "busca_web", "url": "u3"}]
    contagem = migrar(lista, MAPA, VAL, "desconhecida")
    ok("a migração guarda o nome anterior", lista[0]["origem_do_coletor"] == "rede_social_oficial")
    ok("a migração traduz e declara a lacuna",
       lista[0]["origem"] == "rede_social" and lista[1]["origem"] == "desconhecida")
    ok("a pista já canônica não é tocada", "origem_do_coletor" not in lista[2])
    ok("nada mais da pista muda", lista[0]["url"] == "u1" and lista[1]["url"] == "u2")
    ok("a contagem diz o que mudou", contagem == {"rede_social": 1, "desconhecida": 1})

    import inspect
    fonte = inspect.getsource(sys.modules[__name__])
    ok("trava estrutural: as funções puras não escrevem",
       "write_text" not in inspect.getsource(migrar)
       and "write_text" not in inspect.getsource(origem_nova))
    ok("trava estrutural: a escrita é pela porta canônica",
       "from coletores_base import gravar_em" in fonte)
    print(f"autoteste: {11 - len(falhas)}/11")
    return 1 if falhas else 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    from pistas import ORIGEM_CANONICA, ORIGEM_DESCONHECIDA, origens_validas
    from coletores_base import gravar_em

    validas = origens_validas()
    aplicar = "--aplicar" in sys.argv
    total_mudadas = 0
    for nome in FILAS:
        caminho = RAIZ / "data" / nome
        if not caminho.exists():
            continue
        doc = json.loads(caminho.read_text(encoding="utf-8"))
        lista = doc.get("pistas") if isinstance(doc.get("pistas"), list) else doc.get("itens")
        if not isinstance(lista, list):
            print(f"  {nome}: sem lista de pistas legível — nada a fazer")
            continue
        contagem = migrar(lista, ORIGEM_CANONICA, validas, ORIGEM_DESCONHECIDA)
        mudadas = sum(contagem.values())
        total_mudadas += mudadas
        print(f"  {nome}: {mudadas} de {len(lista)} pista(s) com origem a normalizar"
              + (f" → {contagem}" if contagem else ""))
        if aplicar and mudadas:
            gravar_em(caminho, doc)
    if not aplicar:
        print(f"relatório apenas; {total_mudadas} pista(s) a normalizar (use --aplicar)")
        return 0
    print(f"OK {total_mudadas} pista(s) com origem no vocabulário do esquema")
    return 0


if __name__ == "__main__":
    sys.exit(main())
