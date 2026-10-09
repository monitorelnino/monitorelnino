#!/usr/bin/env python3
"""A pista de documento oficial pertence a quem é o DOMÍNIO, não a quem o texto menciona.

ACHADO DE 03/10/2026, no garimpo que a editoria pediu. Treze documentos de plano em domínio oficial
foram ao juiz e **nenhum** foi promovido. O relatório mostrou a razão, e ela não era do juiz:

    documento                                       pista atribuída a    dono do domínio
    celsoramos.sc.gov.br/.../plano.pdf              Salete/SC            Celso Ramos/SC
    defesacivil.taio.sc.gov.br/.../PLANO-TAIO.pdf   Rio do Oeste/SC      Taió/SC
    tubarao.sc.gov.br/.../PLANO_2025.pdf            Monte Castelo/SC     Tubarão/SC
    encantado.rs.gov.br/.../plano-encantado.html    Porto Alegre/RS      Encantado/RS

A pista vinha da busca web, e o município era atribuído pelo **trecho**: o nome de cidade que
aparecia perto do termo achado. Num plano municipal, os nomes no texto são os das comunidades, dos
vizinhos e dos consórcios — o plano de Celso Ramos lista as capelas de Salete, e a pista virou de
Salete. O juiz então recusava por identidade, por citação ou por autoridade, julgando um par que
nunca existiu.

O que este script faz: para cada pista cuja URL está em domínio oficial de um município,
**reatribui a pista ao dono do domínio** e a devolve à fila do juiz. O veredito anterior é apagado
de propósito — ele julgou outro par —, e tudo fica registrado na própria pista:
`municipio_atribuido_antes`, `atribuicao_corrigida_em` e `atribuicao_corrigida_por`.

O que ele NÃO faz:
- não promove nada (quem promove é o juiz, no documento primário);
- não inventa: host que não resolve município com certeza fica como está (ver
  `scripts/municipio_do_dominio.py`, que exige nome exato ou prefixo único na UF);
- não toca pista cuja atribuição já é a do dono do domínio.

USO
    python3 scripts/corrigir_atribuicao_por_dominio.py --relatorio
    python3 scripts/corrigir_atribuicao_por_dominio.py --aplicar
    python3 scripts/corrigir_atribuicao_por_dominio.py --aplicar --urls-de alvos.txt
    python3 scripts/corrigir_atribuicao_por_dominio.py --autoteste
"""
from __future__ import annotations

import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "scripts"))

FILAS = ("pistas_imprensa.json", "pistas_descobertas.json", "pistas_doe.json",
         "pistas_querido_diario.json")
STATUS_DE_VOLTA = ("pista — atribuição corrigida pelo domínio oficial do documento; "
                   "volta ao juiz com o ente dono do domínio")


def pistas_da_fila(doc: dict) -> list:
    for chave in ("pistas", "itens"):
        if isinstance(doc.get(chave), list):
            return doc[chave]
    return []


def precisa_corrigir(pista: dict, dono: dict) -> bool:
    """A pista está atribuída a outro ente que não o dono do domínio? Função pura."""
    if not dono:
        return False
    atual = str(pista.get("ibge") or "").zfill(7) if pista.get("ibge") else ""
    if atual and atual == dono["ibge"]:
        return False
    if not atual and str(pista.get("municipio") or "") == dono["nome"]:
        return False
    return True


def corrigir(pista: dict, dono: dict, hoje_iso: str) -> dict:
    """Devolve a pista reatribuída ao dono do domínio. Função pura (não escreve em disco).

    O veredito do juiz é removido porque ele julgou OUTRO par município-documento; manter o
    veredito deixaria a pista fora da fila para sempre, com uma recusa que não se aplica mais.
    """
    nova = dict(pista)
    nova["municipio_atribuido_antes"] = {
        "municipio": pista.get("municipio"), "uf": pista.get("uf"), "ibge": pista.get("ibge"),
        "veredito_do_juiz": (pista.get("juiz") or {}).get("motivo"),
    }
    nova["municipio"] = dono["nome"]
    nova["uf"] = dono["uf"]
    nova["ibge"] = dono["ibge"]
    nova["atribuicao_corrigida_em"] = hoje_iso
    nova["atribuicao_corrigida_por"] = "dominio_oficial_do_documento"
    nova.pop("juiz", None)
    nova.pop("proxima_tentativa_em", None)
    nova["status"] = STATUS_DE_VOLTA
    return nova


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

    dono = {"nome": "Celso Ramos", "uf": "SC", "ibge": "4204152"}
    pista = {"id": "x1", "municipio": "Salete", "uf": "SC", "ibge": "4215307",
             "url": "https://celsoramos.sc.gov.br/u/x.pdf",
             "status": "pista — recusada pelo juiz: ente_nao_confirmado",
             "juiz": {"motivo": "ente_nao_confirmado", "codebook": "1.2"},
             "proxima_tentativa_em": "2026-10-06"}
    ok("pista de outro ente precisa de correção", precisa_corrigir(pista, dono))
    ok("pista já do dono não precisa",
       not precisa_corrigir(dict(pista, ibge="4204152"), dono))
    ok("sem dono não se mexe", not precisa_corrigir(pista, None))
    ok("sem ibge, o nome igual ao dono basta",
       not precisa_corrigir({"municipio": "Celso Ramos"}, dono))

    nova = corrigir(pista, dono, "2026-10-03")
    ok("reatribui o município", nova["municipio"] == "Celso Ramos" and nova["ibge"] == "4204152")
    ok("guarda a atribuição anterior",
       nova["municipio_atribuido_antes"]["municipio"] == "Salete"
       and nova["municipio_atribuido_antes"]["ibge"] == "4215307")
    ok("guarda o veredito que não se aplica mais",
       nova["municipio_atribuido_antes"]["veredito_do_juiz"] == "ente_nao_confirmado")
    ok("apaga o veredito do juiz", "juiz" not in nova)
    ok("apaga o back-off, para voltar à fila já", "proxima_tentativa_em" not in nova)
    ok("o status diz o que aconteceu", nova["status"].startswith("pista — atribuição corrigida"))
    ok("registra quando e por quê",
       nova["atribuicao_corrigida_em"] == "2026-10-03"
       and nova["atribuicao_corrigida_por"] == "dominio_oficial_do_documento")
    ok("não promove nada: o status continua sendo de pista", nova["status"].startswith("pista"))
    ok("a pista original não é mutada", pista["municipio"] == "Salete" and "juiz" in pista)

    from municipio_do_dominio import municipio_de
    REF = [{"nome": "Taió", "uf": "SC", "codigo_ibge": 4217808}]
    ok("integra com o resolvedor de domínio",
       (municipio_de("https://defesacivil.taio.sc.gov.br/p.pdf", REF) or {}).get("nome") == "Taió")

    import dis
    nomes = set()
    for nome_obj, obj in list(globals().items()):
        if nome_obj in ("_autoteste", "main"):
            continue
        codigo = getattr(obj, "__code__", None)
        if codigo is not None:
            nomes |= {i.argval for i in dis.get_instructions(codigo) if isinstance(i.argval, str)}
    ok("trava estrutural: as funções puras não escrevem",
       not ({"gravar", "gravar_em", "write_text", "write_bytes"} & nomes))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else f"✓ AUTOTESTE OK — {len(_casos_contados)} casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return _autoteste()
    aplicar = "--aplicar" in sys.argv
    urls = None
    if "--urls-de" in sys.argv:
        alvo = pathlib.Path(sys.argv[sys.argv.index("--urls-de") + 1])
        urls = [l.strip() for l in alvo.read_text(encoding="utf-8").splitlines() if l.strip()]

    from coletores_base import DATA, gravar_em, ler, hoje_editorial
    from municipio_do_dominio import municipio_de
    hoje = hoje_editorial().isoformat()

    total, corrigidas = 0, []
    for nome_fila in FILAS:
        doc = ler(nome_fila)
        if not doc:
            continue
        lista = pistas_da_fila(doc)
        mudou = False
        for i, p in enumerate(lista):
            url = str(p.get("url") or "")
            if urls and not any(x in url for x in urls):
                continue
            total += 1
            dono = municipio_de(url)
            if not precisa_corrigir(p, dono):
                continue
            nova = corrigir(p, dono, hoje)
            corrigidas.append((nome_fila, p.get("id"), p.get("municipio"), p.get("uf"),
                               dono["nome"], dono["uf"], url))
            if aplicar:
                lista[i] = nova
                mudou = True
        if aplicar and mudou:
            gravar_em(DATA / nome_fila, doc)

    print(f"{total} pista(s) examinada(s); {len(corrigidas)} com atribuição a corrigir:")
    for fila, ident, antes_m, antes_uf, depois_m, depois_uf, url in corrigidas[:60]:
        print(f"   {str(ident)[:10]:10s} {antes_m or '—'}/{antes_uf or '—'} → "
              f"{depois_m}/{depois_uf}   {url[-60:]}")
    if len(corrigidas) > 60:
        print(f"   … e mais {len(corrigidas) - 60}")
    if aplicar:
        print(f"\n{len(corrigidas)} pista(s) reatribuída(s) e devolvida(s) à fila do juiz.")
    else:
        print("\nrelatório apenas; nada escrito (use --aplicar)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
