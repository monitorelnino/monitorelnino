#!/usr/bin/env python3
"""
scripts/migrar_sobras_do_doe.py — as sobras do DOE já gravadas passam para o esquema
=====================================================================================
MEDIDO PELA CENTRAL (04/10/2026, 06h20 UTC)
-------------------------------------------
`Publicar dados` falhou duas vezes na noite de 03→04 (04:51 e 05:16 UTC) no portão
`verificar_esquema_de_pista.py`: "10 pista(s) nova(s) fora do esquema". Efeito: **nenhum dado novo
publicado nessa noite**. As dez eram homologações estaduais achadas por `coletar_doe.py` e gravadas
na forma antiga (`municipio`/`uf`/`url`/`trecho`), anterior ao `schemas/pista.json` de 03/10.

A causa raiz está corrigida na gravação (`coletar_doe.sobra_de_homologacao`). Este script trata o que
já está no disco, e **não descarta nada**: cada sobra é uma homologação de emergência achada no
Diário Oficial do Estado, com página, excerto e hash de evidência. Ela não é pista de plano — o
esquema manda pista de decreto para a conferência da base oficial de resposta —, e é isso que a
migração passa a dizer no dado, no campo `destino`.

Quarentena, no sentido que a editoria pediu, é exatamente isto: sair da fila ativa (nenhum juiz a
promove, porque `tipo: decreto` não entra na fila de planos) e ficar legível, com motivo e coletor
de origem. Descartar seria perder dez atos de resposta que ninguém mais vai achar.

Idempotente: sobra já migrada não é tocada.

  python3 scripts/migrar_sobras_do_doe.py --autoteste
  python3 scripts/migrar_sobras_do_doe.py --dry-run
  python3 scripts/migrar_sobras_do_doe.py
"""
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

ARQUIVO = "pistas_doe.json"
OBRIGATORIOS = ("url_final", "tipo", "alvo", "nivel", "data", "origem")


def precisa_migrar(pista: dict) -> bool:
    """A sobra está na forma antiga? Função pura."""
    p = pista or {}
    return bool(p.get("url")) and not all(p.get(c) for c in OBRIGATORIOS)


def alvo_de(pista: dict, por_nome: dict) -> str:
    """Código IBGE quando o município casa com a base; a UF quando não. Função pura.

    A UF não é um alvo de segunda classe: é a verdade do que se sabe. O ato é daquele estado, e o
    município ainda não foi identificado — foi por isso que a sobra virou sobra.
    """
    p = pista or {}
    cod = (por_nome or {}).get((p.get("municipio"), p.get("uf")))
    return str(cod or p.get("uf") or "")


def migrada(pista: dict, por_nome: dict) -> dict:
    """A sobra na forma do esquema, preservando tudo o que ela já carregava. Função pura."""
    from coletar_doe import sobra_de_homologacao
    p = dict(pista or {})
    nova = sobra_de_homologacao(p, p.get("hash_evidencia"),
                                str(p.get("registrado_em") or "")[:10],
                                alvo_de(p, por_nome))
    # Nada do registro antigo se perde: o que a função do coletor não nomeia volta por cima.
    for k, v in p.items():
        nova.setdefault(k, v)
    return nova


def _base_do_ibge() -> dict:
    ref = json.loads((RAIZ / "data" / "municipios_ibge_referencia.json").read_text(encoding="utf-8"))
    return {(m["nome"], m["uf"]): str(m["codigo_ibge"]) for m in ref}


def aplicar(dry_run: bool = False) -> int:
    from coletores_base import gravar, ler
    doc = ler(ARQUIVO) or {}
    itens = doc.get("itens") or []
    por_nome = _base_do_ibge()
    alvos = [i for i, p in enumerate(itens) if precisa_migrar(p)]
    print(f"  {len(alvos)} sobra(s) na forma antiga de {len(itens)}")
    com_ibge = 0
    for i in alvos:
        nova = migrada(itens[i], por_nome)
        if nova["alvo"] and nova["alvo"].isdigit():
            com_ibge += 1
        print(f"   · {nova.get('municipio')}/{nova.get('uf')} → alvo {nova['alvo']} "
              f"· destino {nova['destino']}")
        itens[i] = nova
    print(f"  {com_ibge} com código IBGE; {len(alvos) - com_ibge} com a UF como alvo")
    if dry_run:
        print("(dry-run) nada gravado")
        return 0
    if alvos:
        doc["itens"] = itens
        gravar(ARQUIVO, doc)
    return 0


def _autoteste() -> int:
    falhas = []
    # O total era um literal e envelhecia calado: dizia cobrir mais casos do que
    # cobre, ou menos. Agora e contado.
    _casos_contados = []

    def ok(nome, cond):
        _casos_contados.append(nome)
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    antiga = {"municipio": "Barra do Bugres", "uf": "MT", "data": "2026-09-30",
              "url": "https://www.iomat.mt.gov.br/portal/edicoes/download/19356",
              "decreto_estadual": "2.273", "decreto_municipal": None, "trecho": "DECRETO Nº 2.273",
              "pagina": 1, "paginas": 176, "hash_evidencia": "abc",
              "registrado_em": "2026-10-04",
              "motivo": "sem número do decreto ou município não casou com IBGE"}
    base = {("Barra do Bugres", "MT"): "5101407"}

    ok("sobra na forma antiga é reconhecida", precisa_migrar(antiga))
    nova = migrada(antiga, base)
    ok("a migrada cumpre os seis obrigatórios", all(nova.get(c) for c in OBRIGATORIOS))
    ok("a migrada NÃO precisa migrar de novo", not precisa_migrar(nova))
    ok("o alvo é o IBGE quando o município casa", nova["alvo"] == "5101407")
    ok("sem casar, o alvo é a UF", alvo_de(antiga, {}) == "MT")
    ok("o destino declara que não é pista de plano",
       nova["destino"] == "conferencia_resposta" and nova["tipo"] == "decreto")
    ok("o nível é A, porque a fonte é o Diário Oficial do Estado", nova["nivel"] == "A")
    ok("o excerto, a página e o hash sobrevivem",
       nova["trecho"] == "DECRETO Nº 2.273" and nova["pagina"] == 1
       and nova["hash_evidencia"] == "abc")
    ok("o motivo da sobra sobrevive", "não casou com IBGE" in nova["motivo"])
    ok("a data do achado é preservada, não trocada por hoje", nova["data"] == "2026-09-30")

    from scripts.verificar_esquema_de_pista import (fora_da_fila_ativa, ler_esquema,
                                                    problemas_de_esquema)
    esquema = ler_esquema()
    ok("a migrada está fora da fila ativa, por declaração", fora_da_fila_ativa(nova))
    ok("na lista que BLOQUEIA ela não aparece",
       problemas_de_esquema([nova], esquema, so_fila_ativa=True) == [])
    ok("na lista de aviso ela aparece, porque decreto não é pista de plano",
       len(problemas_de_esquema([nova], esquema)) == 1)
    ok("sobra ANTIGA, sem destino, continua bloqueando",
       len(problemas_de_esquema([antiga], esquema, so_fila_ativa=True)) == 1)

    import dis
    nomes = set()
    for nome_obj, obj in list(globals().items()):
        if nome_obj in ("_autoteste", "aplicar", "main", "_base_do_ibge"):
            continue
        codigo = getattr(obj, "__code__", None)
        if codigo is not None:
            nomes |= {i.argval for i in dis.get_instructions(codigo) if isinstance(i.argval, str)}
    ok("trava estrutural: as funções puras não escrevem",
       not ({"gravar", "write_text"} & nomes))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else f"✓ AUTOTESTE OK — {len(_casos_contados)} casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def main() -> int:
    if "--autoteste" in sys.argv[1:]:
        return _autoteste()
    return aplicar(dry_run="--dry-run" in sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
