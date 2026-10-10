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
PONTUADOS = ("NOVO", "READ", "VIG")
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


# 10/10/2026 (item 2b): imprensa oficial com domínio próprio, fora de `<uf>.gov.br`. O critério
# "só `<uf>.gov.br`" era o errado, não o mundo (central, 09/10 19:20).
IMPRENSAS_OFICIAIS = {"PA": ("ioepa.com.br",)}


def dominio_oficial(url: str, uf: str) -> bool:
    """Domínio do estado, imprensa oficial do estado ou `gov.br` — com caminho. Função pura."""
    if dominio_do_estado(url, uf):
        return True
    partes = urlsplit(str(url or ""))
    host = (partes.hostname or "").lower()
    if not partes.path.strip("/"):
        return False
    oficiais = IMPRENSAS_OFICIAIS.get(uf.upper(), ()) + ("gov.br",)
    return any(host == d or host.endswith("." + d) for d in oficiais)


def casa(instrumento: dict, uf: str, nome_uf: str, evidencia_url: str, texto: str) -> bool:
    """A evidência é o documento do instrumento? Função pura."""
    if not dominio_oficial(evidencia_url, uf):
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
        if x.get("arquivo") and dominio_oficial(x.get("url"), uf):
            out.append((h, x))
    return out


ESPELHO = ("url", "consultado_em", "hash_evidencia", "endereco_lacuna", "proveniencia",
           "defeito_de_prova")


def preencher(estados: dict, itens: dict, hoje: str, ler_texto=texto_da_evidencia,
              registro: dict = None) -> dict:
    """Preenche no próprio dict. Devolve a contagem. `ler_texto` é injetável (autoteste).

    10/10/2026 (item 2b): antes da evidência preservada, o REGISTRO de proveniência
    (`data/proveniencia_estadual.json`): o endereço oficial achado por busca dirigida, com o grau de
    conferência. Endereço fora de domínio oficial é recusado aqui, mesmo que esteja no registro.
    Instrumento listado em `defeitos_de_prova` mantém a lacuna e ganha a marca — sem mudar nota.
    """
    cont = {"ja_tinha": 0, "achado": 0, "registro": 0, "lacuna": 0, "lac": 0, "defeito": 0}
    reg = {(a.get("uf"), a.get("tipo")): a for a in (registro or {}).get("achados") or []}
    defe = {(d.get("uf"), d.get("tipo")): d for d in (registro or {}).get("defeitos_de_prova") or []}
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
            r = reg.get((uf, ins.get("tipo")))
            if r and dominio_oficial(r.get("url"), uf):
                ins["url"] = r["url"]
                ins["consultado_em"] = r.get("consultado_em")
                ins["proveniencia"] = {k: r[k] for k in ("tipo_fonte", "verificacao", "como_achou")
                                       if r.get(k)}
                ins.pop("endereco_lacuna", None)
                ins.pop("defeito_de_prova", None)
                cont["registro"] += 1
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
                d = defe.get((uf, ins.get("tipo")))
                if d and ins.get("status") in PONTUADOS:
                    ins["defeito_de_prova"] = {"motivo": d.get("motivo"),
                                               "registrado_em": d.get("registrado_em")}
                    cont["defeito"] += 1
        # o cartão lê os campos do topo (instrumento) e de `estrutura`: mesma proveniência
        por_tipo = {i.get("tipo"): i for i in u.get("instrumentos") or []}
        for tipo, alvo in (("instrumento_operacional", u), ("estrutura_coordenacao", u.get("estrutura"))):
            i = por_tipo.get(tipo)
            if not i or not isinstance(alvo, dict):
                continue
            for k in ESPELHO:
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
        ("contagem", c == {"ja_tinha": 0, "achado": 1, "registro": 0, "lacuna": 1, "lac": 1, "defeito": 0}),
        ("idempotente: o que já tem url não é tocado",
         preencher(est, itens, "2026-10-10", ler_texto=lambda a: textos[a])["ja_tinha"] == 1),
    ]
    est2 = {"ufs": [{"uf": "PA", "nome": "Pará", "estrutura": {}, "instrumentos": [
        {"tipo": "estrutura_coordenacao", "status": "READ", "doc": "Alerta (Decreto nº 5.606/2026)"},
        {"tipo": "instrumento_operacional", "status": "NOVO", "doc": "Plano sem ato"}]},
        {"uf": "GO", "nome": "Goiás", "instrumentos": [{"tipo": "instrumento_operacional", "status": "NOVO", "doc": "PLANCON"}]}]}
    reg = {"achados": [{"uf": "PA", "tipo": "estrutura_coordenacao", "url": "https://ioepa.com.br/pages/2026/2026.08.25.DOE.pdf",
                        "consultado_em": "2026-10-10", "tipo_fonte": "diario_oficial", "verificacao": "conteudo_conferido"},
                       {"uf": "PA", "tipo": "instrumento_operacional", "url": "https://g1.globo.com/pa/plano",
                        "consultado_em": "2026-10-10"}],
           "defeitos_de_prova": [{"uf": "GO", "tipo": "instrumento_operacional", "motivo": "m", "registrado_em": "2026-10-10"}]}
    c2 = preencher(est2, {}, "2026-10-10", ler_texto=lambda a: "", registro=reg)
    pa, go = est2["ufs"][0], est2["ufs"][1]
    casos += [
        ("registro: endereço de imprensa oficial do estado entra, com o grau de conferência",
         pa["estrutura"].get("url", "").startswith("https://ioepa.com.br/")
         and pa["instrumentos"][0]["proveniencia"]["verificacao"] == "conteudo_conferido"),
        ("registro: endereço de imprensa privada é recusado mesmo estando no registro",
         "url" not in pa["instrumentos"][1] and "endereco_lacuna" in pa["instrumentos"][1]),
        ("defeito de prova marcado no pontuado sem documento, com a lacuna mantida",
         go["instrumentos"][0].get("defeito_de_prova", {}).get("motivo") == "m"
         and "endereco_lacuna" in go["instrumentos"][0]),
        ("contagem com registro", c2["registro"] == 1 and c2["defeito"] == 1),
        ("gov.br federal é domínio oficial; raiz não", dominio_oficial("https://www.gov.br/mdr/x", "SC")
         and not dominio_oficial("https://www.gov.br/", "SC")),
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
    registro = ler("proveniencia_estadual.json") or {}
    cont = preencher(estados, itens, hoje_editorial().isoformat(), registro=registro)
    print(f"proveniência estadual: {cont}")
    if "--aplicar" in sys.argv:
        gravar("estados.json", estados)
        print("data/estados.json gravado")
    return 0


if __name__ == "__main__":
    sys.exit(autoteste() if "--autoteste" in sys.argv else main())
