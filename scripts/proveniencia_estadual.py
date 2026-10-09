#!/usr/bin/env python3
"""proveniencia_estadual.py — o endereço do documento de cada instrumento estadual (ajuste 2 de 09/10/2026).

Medido em 09/10/2026: 0 de 54 instrumentos estaduais em `data/estados.json` tinham endereço. O cartão
do estado mostrava o nome e a data do documento, e o leitor não tinha como conferir nada.

Este script preenche o endereço PELO CÓDIGO, sem pessoa, e só com prova:

  1. o instrumento cita um ato com tipo e número ("Decreto nº 11.899");
  2. há evidência PRESERVADA (`data/evidencias.json`, arquivo no disco) servida por domínio do
     próprio estado (`<uf>.gov.br` ou subdomínio dele), cujo texto contém o mesmo tipo e número e o
     nome do estado.

Achou → `url` (o endereço da evidência), `consultado_em` (a data da preservação) e `hash_evidencia`.
Não achou → `endereco_lacuna` com o motivo e a data, e o cartão diz "endereço do documento não
localizado até o corte" (teto de ausência). Nunca se inventa endereço, nunca se usa a raiz de um
portal, e o que já tem `url` não é tocado. Instrumento em lacuna (`LAC`) não tem documento a apontar.

Não muda nota: endereço é proveniência, não régua.

USO
    python3 scripts/proveniencia_estadual.py --autoteste
    python3 scripts/proveniencia_estadual.py            # relatório, sem escrever
    python3 scripts/proveniencia_estadual.py --aplicar  # grava em data/estados.json
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
import unicodedata
from urllib.parse import urlsplit

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

LACUNA = "endereço do documento não localizado até o corte"
RE_ATO = re.compile(r"\b(decreto|portaria|lei|resolu[cç][aã]o|instru[cç][aã]o normativa)"
                    r"(?:\s+(?:estadual|complementar|conjunta))?\s+n?[º°o.]*\s*([\d][\d.]*\d|\d)", re.I)


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", s).lower()


def atos_citados(texto: str) -> set:
    """{(tipo, numero_sem_ponto)} citados num texto. Função pura."""
    out = set()
    for m in RE_ATO.finditer(_norm(texto)):
        out.add((m.group(1).split()[0][:6], m.group(2).replace(".", "")))
    return out


def dominio_do_estado(url: str, uf: str) -> bool:
    """O host é do estado (`<uf>.gov.br` ou subdomínio) e o endereço tem caminho. Função pura."""
    partes = urlsplit(str(url or ""))
    host = (partes.hostname or "").lower()
    alvo = f"{uf.lower()}.gov.br"
    return bool(partes.path.strip("/")) and (host == alvo or host.endswith("." + alvo))


def casa(instrumento: dict, uf: str, nome_uf: str, evidencia_url: str, texto: str) -> bool:
    """A evidência é o documento do instrumento? Função pura."""
    if not dominio_do_estado(evidencia_url, uf):
        return False
    pedidos = atos_citados(instrumento.get("doc") or "")
    if not pedidos:
        return False
    achados = atos_citados(texto)
    return bool(pedidos & achados) and _norm(nome_uf) in _norm(texto)


def texto_da_evidencia(arquivo: str) -> str:
    p = RAIZ / arquivo
    for cand in (p.with_suffix(".txt"), p):
        if cand.exists() and cand.suffix in (".txt", ".html", ".json"):
            try:
                t = cand.read_text(encoding="utf-8", errors="replace")[:3_000_000]
            except OSError:
                continue
            return re.sub(r"<[^>]+>", " ", t) if cand.suffix == ".html" else t
    return ""


def candidatas(itens: dict, uf: str) -> list:
    out = []
    for h, x in itens.items():
        if x.get("arquivo") and dominio_do_estado(x.get("url"), uf):
            out.append((h, x))
    return out


def preencher(estados: dict, itens: dict, hoje: str, ler_texto=texto_da_evidencia) -> dict:
    """Preenche no próprio dict. Devolve a contagem. `ler_texto` é injetável (autoteste)."""
    cont = {"ja_tinha": 0, "achado": 0, "lacuna": 0, "lac": 0}
    for u in estados.get("ufs") or []:
        uf, nome = u["uf"], u["nome"]
        cands = None
        for ins in u.get("instrumentos") or []:
            if ins.get("status") == "LAC":
                cont["lac"] += 1
                continue
            if ins.get("url") or ins.get("urls"):
                cont["ja_tinha"] += 1
                continue
            if cands is None:
                cands = [(h, x, ler_texto(x["arquivo"])) for h, x in candidatas(itens, uf)]
            achado = next(((h, x) for h, x, t in cands if casa(ins, uf, nome, x["url"], t)), None)
            if achado:
                h, x = achado
                ins["url"] = x["url"]
                ins["consultado_em"] = x.get("preservado_em")
                ins["hash_evidencia"] = h
                ins.pop("endereco_lacuna", None)
                cont["achado"] += 1
            else:
                ins["endereco_lacuna"] = {"motivo": LACUNA, "verificado_em": hoje}
                cont["lacuna"] += 1
        # o cartão lê os campos do topo (instrumento) e de `estrutura`: mesma proveniência
        por_tipo = {i.get("tipo"): i for i in u.get("instrumentos") or []}
        for tipo, alvo in (("instrumento_operacional", u), ("estrutura_coordenacao", u.get("estrutura"))):
            i = por_tipo.get(tipo)
            if not i or not isinstance(alvo, dict):
                continue
            for k in ("url", "consultado_em", "hash_evidencia", "endereco_lacuna"):
                if k in i:
                    alvo[k] = i[k]
                else:
                    alvo.pop(k, None)
    return cont


def autoteste() -> int:
    est = {"ufs": [{"uf": "PB", "nome": "Paraíba", "estrutura": {}, "instrumentos": [
        {"tipo": "estrutura_coordenacao", "status": "READ", "doc": "Gabinete (Decreto nº 11.899, DOE 01/06/2026)"},
        {"tipo": "instrumento_operacional", "status": "ELAB", "doc": "Plano nomeado, sem ato"}]},
        {"uf": "AL", "nome": "Alagoas", "instrumentos": [{"tipo": "instrumento_operacional", "status": "LAC", "doc": "x"}]}]}
    itens = {"h1": {"url": "https://defesacivil.pb.gov.br/decreto-11899.pdf", "arquivo": "a.pdf", "preservado_em": "2026-09-01"},
             "h2": {"url": "https://pb.gov.br/", "arquivo": "b.pdf"},
             "h3": {"url": "https://g1.globo.com/pb/x", "arquivo": "c.pdf"}}
    textos = {"a.pdf": "ESTADO DA PARAÍBA DECRETO Nº 11.899, DE 1º DE JUNHO DE 2026", "b.pdf": "Decreto 11.899 Paraíba",
              "c.pdf": "Decreto nº 11.899 Paraíba"}
    c = preencher(est, itens, "2026-10-09", ler_texto=lambda a: textos[a])
    pb = est["ufs"][0]
    casos = [
        ("ato citado e achado em domínio do estado vira endereço",
         pb["instrumentos"][0].get("url") == "https://defesacivil.pb.gov.br/decreto-11899.pdf"),
        ("o endereço vai também para o campo que o cartão lê", pb["estrutura"].get("url", "").endswith("11899.pdf")),
        ("sem ato citado: lacuna declarada, nunca endereço inventado",
         pb["instrumentos"][1].get("endereco_lacuna", {}).get("motivo") == LACUNA and "url" not in pb["instrumentos"][1]),
        ("instrumento em LAC não ganha nada", "endereco_lacuna" not in est["ufs"][1]["instrumentos"][0]),
        ("raiz de portal não é endereço", not dominio_do_estado("https://pb.gov.br/", "PB")),
        ("imprensa não é domínio do estado", not dominio_do_estado("https://g1.globo.com/pb/x", "PB")),
        ("subdomínio do estado é", dominio_do_estado("https://doe.pb.gov.br/a.pdf", "PB")),
        ("contagem", c == {"ja_tinha": 0, "achado": 1, "lacuna": 1, "lac": 1}),
        ("idempotente: o que já tem url não é tocado",
         preencher(est, itens, "2026-10-10", ler_texto=lambda a: textos[a])["ja_tinha"] == 1),
    ]
    for n, ok in casos:
        print(f"  {'OK  ' if ok else 'FALHA'} {n}")
    falhas = [n for n, ok in casos if not ok]
    print(f"{'X' if falhas else 'OK'} AUTOTESTE — {len(casos)} casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def main() -> int:
    from coletores_base import ler, gravar, hoje_editorial
    estados = ler("estados.json")
    itens = (ler("evidencias.json") or {}).get("itens") or {}
    cont = preencher(estados, itens, hoje_editorial().isoformat())
    print(f"proveniência estadual: {cont}")
    if "--aplicar" in sys.argv:
        gravar("estados.json", estados)
        print("data/estados.json gravado")
    return 0


if __name__ == "__main__":
    sys.exit(autoteste() if "--autoteste" in sys.argv else main())
