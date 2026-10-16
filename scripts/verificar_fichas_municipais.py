#!/usr/bin/env python3
"""Portão das fichas municipais: `data/municipios.json` lido uma vez, quatro réguas.

16/10/2026 (consolidação item 6): `verificar_documento_de_plano.py`, `verificar_documento_publicado.py`,
`verificar_datas_de_instrumento.py` e `verificar_capital.py` abriam o mesmo banco com quatro leitores
e quatro `main`. Aqui cada régua é uma função pura, com os mesmos casos de autoteste; o veredito é um.

AS RÉGUAS (HANDOVER_CORRECAO_DEFINITIVA_08-10-2026, itens 1.9 a 1.12)
- **D1 — nada pontua sem documento lido e preservado** (A4-05, A4-09): categoria com crédito (`plano`,
  `plano_antigo`, `plano_elaboracao`, `plano_novo`, `plano_readaptado`, `plano_recorrente`, `estrutura`)
  exige `url` de documento (não notícia, não raiz de portal) **e** `hash_evidencia`; quem não tem é
  `plano_nomeado` (crédito 0) com `por_que_nomeado`. Em 08/10 havia 47 registros pontuando sem documento.
- **`documento` é título, não sobra de página** (A1-06, A4-08): sem marcador de paginação, frase interna
  do juiz, reticências de corte, texto de painel, nem inicial minúscula ("tanhaém Secretaria…").
- **A data do instrumento é a do DOCUMENTO, nunca a da consulta** (A3-09, A3-30): no canal
  `repositorio_estadual`, `plano_antigo` com ano ≥ 2024 e `plano` com ano < 2024 reprovam; `localizado_em`
  guarda a consulta; o ano de `data` aparece em `documento`. Em 08/10 havia 83 registros com `data: hoje`.
- **A capital tem UMA fonte, o banco** (A3-11, A4-03): `estados.json › capital` guarda só `nome`, a capital
  tem registro em `municipios.json`, e `assets/js/index.js` não lê `capital.status`/`capital.info`.

`--autoteste` é puro: não lê `data/`, não escreve nada; roda antes da conferência em todo uso.
"""
import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
MUNICIPIOS = RAIZ / "data" / "municipios.json"
ESTADOS = RAIZ / "data" / "estados.json"
JS = RAIZ / "assets" / "js" / "index.js"

PONTUAM = ("plano", "plano_antigo", "plano_elaboracao", "plano_novo", "plano_readaptado",
           "plano_recorrente", "estrutura")
RE_NOTICIA = re.compile(r"/notici|/imprensa|/news|/sala-de-imprensa|/blog", re.I)
RE_RAIZ = re.compile(r"^https?://[^/]+/?$")
PROIBIDOS_NO_TITULO = (
    (re.compile(r"P[áa]gina\s+\d+\s+de\s+\d+", re.I), "marcador de paginação do PDF"),
    (re.compile(r"o documento [ÉE] o instrumento", re.I), "frase interna do juiz"),
    (re.compile(r"……|\.\.\.\."), "reticências de corte de trecho"),
    (re.compile(r"Estado das fontes|em verifica[çc][ãa]o|em classifica[çc][ãa]o", re.I),
     "texto interno de painel"),
)
ANO_LIMIAR_VIGENTE = 2024  # a mesma régua de `atualizar_instrumentos_estaduais.categoria_por_ano`
CANAL_ESTADUAL = "repositorio_estadual"
RE_ANO = re.compile(r"(19|20)\d{2}")
CAPITAL_PERMITIDO = {"nome"}

_etq = lambda m: f"{m.get('nome')}/{m.get('uf')}"


def problemas_de_documento(municipios) -> list:
    """D1: documento lido e preservado para tudo o que pontua. Função pura."""
    fora = []
    for m in municipios:
        cat = m.get("categoria")
        if cat == "plano_nomeado":
            if not str(m.get("por_que_nomeado") or "").strip():
                fora.append(f"{_etq(m)}: plano_nomeado sem `por_que_nomeado` — a razão da "
                            f"ausência do documento se declara, não se presume")
            continue
        if cat not in PONTUAM:
            continue
        url = str(m.get("url") or "")
        if not url:
            fora.append(f"{_etq(m)}: {cat} sem endereço de documento (D1); use plano_nomeado")
            continue
        if RE_NOTICIA.search(url):
            fora.append(f"{_etq(m)}: {cat} com endereço de notícia, não de documento ({url})")
        elif RE_RAIZ.match(url):
            fora.append(f"{_etq(m)}: {cat} com raiz de portal no lugar do documento ({url})")
        if not str(m.get("hash_evidencia") or "").strip():
            fora.append(f"{_etq(m)}: {cat} sem `hash_evidencia` — documento que pontua fica "
                        f"preservado e conferível")
    return fora


def problemas_de_titulo(municipios) -> list:
    """`documento` em forma de título. Função pura."""
    fora = []
    for m in municipios:
        doc = str(m.get("documento") or "").strip()
        if not doc:
            continue
        for regex, por_que in PROIBIDOS_NO_TITULO:
            achado = regex.search(doc)
            if achado:
                fora.append(f"{_etq(m)}: `documento` traz {por_que} ({achado.group(0)!r})")
        if doc[:1].islower():
            fora.append(f"{_etq(m)}: `documento` começa em minúscula ({doc[:40]!r}) — título de "
                        f"documento não começa em minúscula")
    return fora


def ano_de(valor):
    """O ano de 'AAAA', 'dd/mm/aaaa' ou '2025-2026' (o último do intervalo: a edição em vigor)."""
    anos = [int(x.group(0)) for x in RE_ANO.finditer(str(valor or ""))]
    return anos[-1] if anos else None


def problemas_de_data(municipios) -> list:
    """A data do instrumento é a do documento (canal `repositorio_estadual`). Função pura."""
    fora = []
    for m in municipios:
        if m.get("canal") != CANAL_ESTADUAL:
            continue
        cat, ano = m.get("categoria"), ano_de(m.get("data"))
        if ano is None:
            fora.append(f"{_etq(m)}: data sem ano reconhecível ({m.get('data')!r})")
            continue
        if cat == "plano_antigo" and ano >= ANO_LIMIAR_VIGENTE:
            fora.append(f"{_etq(m)}: plano_antigo com data de {ano} — a categoria diz antigo e a "
                        f"data diz deste ciclo")
        if cat == "plano" and ano < ANO_LIMIAR_VIGENTE:
            fora.append(f"{_etq(m)}: plano (vigente) com data de {ano}, anterior ao limiar "
                        f"{ANO_LIMIAR_VIGENTE}")
        if not m.get("localizado_em"):
            fora.append(f"{_etq(m)}: sem `localizado_em` — a data da consulta tem campo próprio")
        doc = str(m.get("documento") or "")
        if str(ano) not in doc:
            fora.append(f"{_etq(m)}: o ano da data ({ano}) não aparece em `documento` ({doc!r}); "
                        f"a data do instrumento sai do documento, não do relógio")
    return fora


def problemas_de_capital(ufs, categorias, fonte_js="") -> list:
    """A capital tem uma fonte: o banco. Função pura."""
    fora = []
    for x in ufs:
        c, uf = x.get("capital"), x.get("uf")
        if not c:
            continue
        sobrando = sorted(set(c) - CAPITAL_PERMITIDO)
        if sobrando:
            fora.append(f"{uf}: `capital` guarda {', '.join(sobrando)} — a capital tem uma fonte "
                        f"só, o banco; campo de texto aqui é segunda fonte (A3-11)")
        if not str(c.get("nome") or "").strip():
            fora.append(f"{uf}: `capital` sem nome")
            continue
        if (uf, c["nome"]) not in categorias:
            fora.append(f"{uf}: a capital {c['nome']} não tem registro em municipios.json — sem "
                        f"registro não há o que publicar sobre ela")
    for proibido in ("d.capital.status", "d.capital.info"):
        if fonte_js and proibido in fonte_js:
            fora.append(f"assets/js/index.js ainda lê {proibido}; o estado da capital sai do "
                        f"banco (textoDaCapital)")
    return fora


def autoteste() -> int:
    bom = {"nome": "Linhares", "uf": "ES", "categoria": "plano",
           "url": "https://linhares.es.gov.br/wp-content/plancon-2025.pdf",
           "hash_evidencia": "a" * 64, "fonte": "Prefeitura de Linhares"}
    tit = {"nome": "Serra", "uf": "ES", "documento": "Fica instituído o Plano Municipal de Proteção e Defesa Civil"}
    es_bom = {"nome": "Linhares", "uf": "ES", "categoria": "plano", "canal": CANAL_ESTADUAL,
              "documento": "PLANCON edição 2025 (repositório estadual)", "data": "2025", "localizado_em": "26/08/2026"}
    se_antigo = {"nome": "Poço Redondo", "uf": "SE", "categoria": "plano_antigo", "canal": CANAL_ESTADUAL,
                 "documento": "PLANCON edição 2019 (repositório estadual)", "data": "2019", "localizado_em": "26/08/2026"}
    cats = {("AC", "Rio Branco"): "nao_verificado", ("PR", "Curitiba"): "estrutura"}
    cap = lambda ufs, js="": problemas_de_capital(ufs, cats, js)
    casos = [
        # D1
        ("plano com documento e hash passa", problemas_de_documento([bom]), 0),
        ("plano sem url reprova", problemas_de_documento([{k: v for k, v in bom.items() if k != "url"}]), 1),
        ("plano com url de notícia reprova", problemas_de_documento([{**bom, "url": "https://x.es.gov.br/noticias/plano-apresentado"}]), 1),
        ("plano com raiz de portal reprova", problemas_de_documento([{**bom, "url": "https://x.es.gov.br/"}]), 1),
        ("plano sem hash reprova", problemas_de_documento([{k: v for k, v in bom.items() if k != "hash_evidencia"}]), 1),
        ("plano_nomeado com razão declarada passa", problemas_de_documento(
            [{"nome": "Maruim", "uf": "SE", "categoria": "plano_nomeado", "por_que_nomeado": "D1: sem endereço de documento"}]), 0),
        ("plano_nomeado sem razão reprova", problemas_de_documento([{"nome": "Maruim", "uf": "SE", "categoria": "plano_nomeado"}]), 1),
        ("nao_localizado é ignorado", problemas_de_documento([{"nome": "X", "uf": "BA", "categoria": "nao_localizado"}]), 0),
        ("decreto é ignorado (não pontua no índice)", problemas_de_documento([{"nome": "Y", "uf": "BA", "categoria": "decreto"}]), 0),
        # título
        ("ementa limpa passa", problemas_de_titulo([tit]), 0),
        ("título com órgão e ano passa", problemas_de_titulo(
            [{**tit, "documento": "PLANCON PLANO DE CONTIGÊNCIA 2024-2025 — Prefeitura de Itanhaém, 2024"}]), 0),
        ("marcador de página reprova", problemas_de_titulo(
            [{**tit, "documento": "neste Plano. 11/08/2026 Página 3 de 72 Plano de contingência"}]), 2),
        ("frase interna do juiz reprova", problemas_de_titulo(
            [{**tit, "documento": "o documento É o instrumento nomeado: tanhaém Secretaria"}]), 2),
        ("minúscula inicial reprova", problemas_de_titulo([{**tit, "documento": "a Católica 8 1.5. INSTRUÇÕES PARA USO"}]), 1),
        ("reticências de corte reprovam", problemas_de_titulo([{**tit, "documento": "Plano de contingência do município ……"}]), 1),
        ("texto de painel reprova", problemas_de_titulo([{**tit, "documento": "Estado das fontes"}]), 1),
        ("documento ausente é ignorado", problemas_de_titulo([{"nome": "X", "uf": "BA"}]), 0),
        # datas
        ("ES vigente com ano da edição passa", problemas_de_data([es_bom]), 0),
        ("SE antigo com ano da edição passa", problemas_de_data([se_antigo]), 0),
        ("intervalo 2025-2026 passa", problemas_de_data(
            [{**es_bom, "data": "2025-2026", "documento": "PLANCON edição 2025-2026 (repositório estadual)"}]), 0),
        ("data da consulta no lugar da data do documento reprova", problemas_de_data([{**es_bom, "data": "26/08/2026"}]), 1),
        ("plano_antigo com data de 2026 reprova", problemas_de_data(
            [{**se_antigo, "data": "2026", "documento": "PLANCON edição 2026 (repositório estadual)"}]), 1),
        ("plano vigente com data de 2019 reprova", problemas_de_data(
            [{**es_bom, "data": "2019", "documento": "PLANCON edição 2019 (repositório estadual)"}]), 1),
        ("sem localizado_em reprova", problemas_de_data([{k: v for k, v in es_bom.items() if k != "localizado_em"}]), 1),
        ("data sem ano reprova", problemas_de_data([{**es_bom, "data": "sem data"}]), 1),
        ("edição antiga com atualização recente passa pela data da atualização", problemas_de_data(
            [{**es_bom, "data": "2025", "documento": "PLANCON ed. 2023, atualizado 31/01/2025 (repositório estadual)"}]), 0),
        ("outro canal é ignorado", problemas_de_data([{**es_bom, "canal": "DOM", "data": "26/08/2026"}]), 0),
        # capital
        ("capital só com nome passa", cap([{"uf": "AC", "capital": {"nome": "Rio Branco"}}]), 0),
        ("capital com status reprova", cap([{"uf": "AC", "capital": {"nome": "Rio Branco", "status": "Novo"}}]), 1),
        ("capital com info reprova", cap([{"uf": "PR", "capital": {"nome": "Curitiba", "info": "caso mais avançado"}}]), 1),
        ("capital sem registro no banco reprova", cap([{"uf": "SP", "capital": {"nome": "São Paulo"}}]), 1),
        ("UF sem capital é ignorada", cap([{"uf": "DF"}]), 0),
        ("JS que lê o status reprova", cap([{"uf": "AC", "capital": {"nome": "Rio Branco"}}], "item('Capital: ' + d.capital.status)"), 1),
        ("JS que lê o banco passa", cap([{"uf": "AC", "capital": {"nome": "Rio Branco"}}], "item(textoDaCapital(regCap))"), 0),
    ]
    falhas = 0
    for nome, achados, esperado in casos:
        ok = len(achados) == esperado
        print(f"  {'ok ' if ok else 'FALHA'} {nome}: {len(achados)} problema(s)")
        if not ok:
            falhas += 1
            for a in achados:
                print(f"        {a}")
    print(f"autoteste: {len(casos) - falhas}/{len(casos)}")
    return 1 if falhas else 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    if autoteste() != 0:
        return 1
    doc = json.loads(MUNICIPIOS.read_text(encoding="utf-8"))
    bruto = doc["municipios"] if isinstance(doc, dict) else doc
    municipios = list(bruto.values()) if isinstance(bruto, dict) else bruto
    estados = json.loads(ESTADOS.read_text(encoding="utf-8"))
    categorias = {(m["uf"], m["nome"]): m.get("categoria") for m in municipios}
    reguas = [("documento lido e preservado (D1)", problemas_de_documento(municipios)),
              ("`documento` em forma de título", problemas_de_titulo(municipios)),
              ("data do instrumento", problemas_de_data(municipios)),
              ("capital com uma fonte", problemas_de_capital(estados["ufs"], categorias, JS.read_text(encoding="utf-8")))]
    total = sum(len(f) for _, f in reguas)
    for regua, fora in reguas:
        if fora:
            print(f"VERMELHO — {regua}: {len(fora)} problema(s)")
            for f in fora[:40]:
                print(f"  · {f}")
            if len(fora) > 40:
                print(f"  … e outros {len(fora) - 40}")
    if total:
        print(f"✗ FICHAS MUNICIPAIS: {total} problema(s) em data/municipios.json e data/estados.json.")
        return 1
    n = sum(1 for m in municipios if m.get("categoria") in PONTUAM)
    nom = sum(1 for m in municipios if m.get("categoria") == "plano_nomeado")
    est = sum(1 for m in municipios if m.get("canal") == CANAL_ESTADUAL)
    print(f"✓ FICHAS MUNICIPAIS OK — {n} registros com crédito têm documento e evidência ({nom} em plano_nomeado); "
          f"`documento` em forma de título; {est} de repositório estadual com data do documento e da consulta separadas; "
          f"{sum(1 for x in estados['ufs'] if x.get('capital'))} capitais com uma fonte só.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
