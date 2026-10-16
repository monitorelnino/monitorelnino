#!/usr/bin/env python3
"""Portão: a versão do índice é uma só, e tem dono.

Item 1.15 do HANDOVER_CORRECAO_DEFINITIVA_08-10-2026 (achados A3-16 e A3-12). Em 08/10/2026 o
cabeçalho da METODOLOGIA, a tabela §5.2, o `CITATION.cff`, o `datapackage.json` e o PDF público
diziam coisas diferentes: **dois métodos diferentes chamados "v3.1"** — o narrativo de 06/09 e a
troca de componentes de 30/09 — e um dataset citável como **"2.3"**. O §12 exige versão maior para
mudança de componente, e a troca de 30/09 entrou como `.1`; essa decisão é da editoria e está
nomeada no relatório.

A régua que este portão cobra:

1. `data/meta.json` tem `versao_indice`, escrito por `recalcular_mare.py --write`;
2. a versão do `datapackage.json` e do `CITATION.cff` é a mesma, derivada dele — nenhuma delas
   escrita à mão;
3. nenhuma régua extinta volta à tabela normativa: a tabela §5.2 não nomeia "Antecipação" como
   componente, e o §5.3 não grafa o crédito antigo do plano de ciclo anterior;
4. o cálculo paralelo da v3.2 existe, é derivado e **não é lido por página nenhuma**;
5. (16/10/2026) o texto público sobre o índice não nomeia o que `meta.json` › `definicao_indice`
   não tem: com a antecedência fora da nota, nenhuma página do MARÉ Legal a apresenta como
   medida da nota, e "pesam igual" só entra por molde (`{n_componentes}`), nunca escrito à mão.
   Lê o catálogo (todo texto público vive nele — regra (f) do `verificar_catalogo.py`); a
   página do MARÉ Saúde fica fora, porque é outro índice, com a sua própria definição.
   Dispensa só por `layout/excecoes.json`, regra `versao_do_indice.texto`.

`--autoteste` é puro: não lê `data/`, não escreve nada.
"""
import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
PAGINAS = sorted(RAIZ.glob("*.html"))
JS = sorted((RAIZ / "assets").rglob("*.js"))


def problemas(meta: dict, datapackage: dict, citation: str, metodologia: str,
              paralelo_existe: bool, lido_por_pagina: bool) -> list:
    fora = []
    versao = str(meta.get("versao_indice") or "")
    if not versao:
        fora.append("data/meta.json sem `versao_indice` — a versão do índice tem de ter dono, e o "
                    "dono é o motor (`recalcular_mare.py --write`)")
    else:
        curta = versao.split(" ")[0].lstrip("v")
        if str(datapackage.get("version") or "") != curta:
            fora.append(f"datapackage.json diz versão {datapackage.get('version')!r} e o índice "
                        f"está em {curta!r}")
        m = re.search(r'(?m)^version:\s*"?([^"\n]+)"?', citation)
        if not m or m.group(1).strip() != curta:
            fora.append(f"CITATION.cff diz versão {m.group(1) if m else None!r} e o índice está "
                        f"em {curta!r}")
    if re.search(r"(?m)^  Antecipação\s{2,}100 = instrumento", metodologia):
        fora.append("a tabela §5.2 da METODOLOGIA ainda nomeia 'Antecipação' como componente; ela "
                    "saiu do índice em 30/09/2026")
    if re.search(r"crédito: plano 1,0 · plano_antigo 0,6", metodologia):
        fora.append("o §5.3 da METODOLOGIA ainda grafa o crédito antigo do plano de ciclo anterior "
                    "(0,6), revogado pelo §196 em 24/09/2026")
    if not paralelo_existe:
        fora.append("data/paralelo_v32.json não existe — a v3.2 está decidida desde 05/10/2026 e o "
                    "cálculo paralelo é o que a sustenta (A3-12)")
    if lido_por_pagina:
        fora.append("alguma página ou script de página lê data/paralelo_v32.json; a v3.2 roda em "
                    "paralelo e não publica nada")
    return fora


# O que a definição do índice torna falso quando a antecedência está fora da nota.
TEMPO_NA_NOTA = re.compile(r"quando o plano foi publicado em rela[çc][ãa]o ao primeiro boletim", re.I)
PESO_A_MAO = re.compile(r"pesam igual", re.I)
PAGINAS_DO_SAUDE = {"saude"}


def problemas_de_texto(meta: dict, catalogos: dict, dispensadas: set) -> list:
    """Texto público que contradiz a definição do índice. Função pura.

    `catalogos` é {pagina: {identificador: texto}}; `dispensadas` são as páginas com exceção
    registrada para `versao_do_indice.texto`."""
    definicao = (meta or {}).get("definicao_indice") or {}
    if not definicao:
        return ["data/meta.json sem `definicao_indice` — a definição do índice tem dono, e é o motor "
                "(`recalcular_mare.py --write`)"]
    fora = []
    for pagina, textos in sorted((catalogos or {}).items()):
        if pagina in PAGINAS_DO_SAUDE or f"{pagina}.html" in dispensadas:
            continue
        for ident, texto in sorted((textos or {}).items()):
            t = str(texto or "")
            if definicao.get("antecipacao_fora_da_nota") and TEMPO_NA_NOTA.search(t):
                fora.append(f"{ident}: apresenta a antecedência como medida da nota; ela saiu da "
                            f"nota na v3.1 (meta.json › definicao_indice)")
            if PESO_A_MAO.search(t) and "{n_componentes}" not in t:
                fora.append(f"{ident}: \"pesam igual\" escrito à mão; o número de componentes vem de "
                            f"meta.json pelo molde {{n_componentes}}")
    return fora


def autoteste() -> int:
    meta = {"versao_indice": "v3.1 (30/09/2026)"}
    dp = {"version": "3.1"}
    cff = 'cff-version: 1.2.0\nversion: "3.1"\n'
    met = "tabela limpa"
    casos = [
        ("tudo alinhado passa", (meta, dp, cff, met, True, False), 0),
        ("meta sem versao_indice reprova", ({}, dp, cff, met, True, False), 1),
        ("datapackage desalinhado reprova", (meta, {"version": "2.3"}, cff, met, True, False), 1),
        ("CITATION desalinhado reprova",
         (meta, dp, 'version: "2.3"\n', met, True, False), 1),
        ("Antecipação na tabela 5.2 reprova",
         (meta, dp, cff, "  Antecipação                  100 = instrumento anterior ao Boletim",
          True, False), 1),
        ("crédito antigo no 5.3 reprova",
         (meta, dp, cff, "crédito: plano 1,0 · plano_antigo 0,6 · plano_elaboracao 0,45", True,
          False), 1),
        ("paralelo ausente reprova", (meta, dp, cff, met, False, False), 1),
        ("paralelo lido por página reprova", (meta, dp, cff, met, True, True), 1),
    ]
    md = {"definicao_indice": {"antecipacao_fora_da_nota": True, "componentes": [1, 2, 3]}}
    casos_texto = [
        ("texto limpo passa", (md, {"index": {"i.a": "Três componentes."}}, set()), 0),
        ("antecedência como medida da nota reprova",
         (md, {"index": {"i.a": "e quando o plano foi publicado em relação ao primeiro boletim"}}, set()), 1),
        ("'pesam igual' à mão reprova; por molde passa",
         (md, {"index": {"i.a": "Os três pesam igual.", "i.b": "Os {n_componentes} pesam igual."}}, set()), 1),
        ("a página do MARÉ Saúde é outro índice", (md, {"saude": {"s.a": "Os três pesam igual."}}, set()), 0),
        ("exceção registrada dispensa a página", (md, {"index": {"i.a": "Os três pesam igual."}}, {"index.html"}), 0),
        ("meta sem definição reprova", ({}, {}, set()), 1),
    ]
    falhas = 0
    for nome, args, esperado in casos + [(n, a, e) for n, a, e in casos_texto]:
        achados = (problemas_de_texto if len(args) == 3 else problemas)(*args)
        ok = len(achados) == esperado
        print(f"  {'ok ' if ok else 'FALHA'} {nome}: {len(achados)} problema(s)")
        if not ok:
            falhas += 1
            for a in achados:
                print(f"        {a}")
    casos = casos + casos_texto
    print(f"autoteste: {len(casos) - falhas}/{len(casos)}")
    return 1 if falhas else 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    meta = json.loads((RAIZ / "data" / "meta.json").read_text(encoding="utf-8"))
    dp_path = RAIZ / "dados-abertos" / "datapackage.json"
    dp = json.loads(dp_path.read_text(encoding="utf-8")) if dp_path.exists() else {}
    cff_path = RAIZ / "CITATION.cff"
    cff = cff_path.read_text(encoding="utf-8") if cff_path.exists() else ""
    met = (RAIZ / "METODOLOGIA.md").read_text(encoding="utf-8")
    paralelo = (RAIZ / "data" / "paralelo_v32.json").exists()
    lido = any("paralelo_v32" in p.read_text(encoding="utf-8", errors="ignore")
               for p in PAGINAS + JS)
    fora = problemas(meta, dp, cff, met, paralelo, lido)
    catalogos = {a.stem: (json.loads(a.read_text(encoding="utf-8")).get("textos") or {})
                 for a in sorted((RAIZ / "conteudo").glob("*.json")) if not a.name.startswith("_")}
    sys.path.insert(0, str(RAIZ / "scripts"))
    from verificar_conformidade import excecoes_de  # noqa: PLC0415 — a mesma leitura de exceção
    exc_arq = RAIZ / "layout" / "excecoes.json"
    exc = json.loads(exc_arq.read_text(encoding="utf-8")) if exc_arq.exists() else {}
    dispensadas = {f"{p}.html" for p in catalogos
                   if "versao_do_indice.texto" in excecoes_de(f"{p}.html", exc)}
    fora += problemas_de_texto(meta, catalogos, dispensadas)
    if fora:
        print(f"VERMELHO: {len(fora)} problema(s) de versão do índice")
        for f in fora:
            print(f"  · {f}")
        return 1
    print(f"ok: versão {meta.get('versao_indice')} em meta.json, datapackage e CITATION; v3.2 "
          f"calculada em paralelo e fora das páginas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
