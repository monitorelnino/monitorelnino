#!/usr/bin/env python3
"""
fila_do_juiz_querido_diario.py
==============================
Gera `data/fila_qd_169.json`: os municípios com excerto reconhecido no diário e **sem registro e sem
pista** em lugar nenhum — a primeira fila do juiz para o Querido Diário.

Decisão da editoria de 28/09/2026 (item 1): o QD volta ao funil, `pistas_querido_diario.json` é
reativado, toda pista do QD passa pelo juiz (etapas 0–7) e **nunca entra direto**; os 169 municípios que
a auditoria do funil encontrou são a primeira fila.

ELE GERA ALVOS, NÃO PISTAS — E A RAZÃO FOI MEDIDA
-------------------------------------------------
A primeira versão montava as pistas a partir da **evidência preservada** de cada município: o índice
guarda, sob o `hash_evidencia` da execução, o registro da edição devolvido pela API, com a URL do PDF, a
do texto e um excerto. Parecia suficiente. Não era, e a medição mostrou por quê: **o excerto guardado não
é a menção ao plano.** A preservação manteve uma gazeta por consulta e o primeiro excerto dela — que nos
casos examinados falava de hectares de um evento, de adjudicação de licitação e de objetivos de escola.
Sem o excerto certo, o juiz não consegue recortar o ato de dentro de uma edição de vinte mil caracteres,
e as 168 pistas que eu havia escrito cairiam todas em dúvida.

Então este script gera a **lista de alvos**, e a pista vem de consulta NOVA ao Querido Diário, por
município e por termo de plano — que é o que `consultar_querido_diario.py --alvos` faz. O excerto sai da
própria consulta e aponta a menção, que é o que o recorte do ato precisa.

O QUE ELE NÃO FAZ
-----------------
Não consulta rede, não escreve pista, não promove nada, não decide categoria.

USO
  python3 scripts/fila_do_juiz_querido_diario.py --relatorio
  python3 scripts/fila_do_juiz_querido_diario.py --escrever
  python3 scripts/fila_do_juiz_querido_diario.py --autoteste
"""
import json
import pathlib
import sys
import unicodedata

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

DESTINO = RAIZ / "data" / "fila_qd_169.json"


def norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode("ascii")
    return " ".join(s.split()).lower()


def alvos(execucoes: list, no_banco: set, em_fila: set) -> dict:
    """{ibge: {codigo_ibge, nome, uf, excerto_visto_em}} dos municípios com excerto e sem destino.

    Guarda a execução MAIS RECENTE de cada município: a data serve para dizer quando o excerto foi
    visto, e o diário mais novo é o que interessa."""
    fora = {}
    for e in execucoes:
        if e.get("canal") != "DOM" or not str(e.get("decisao") or "").startswith("com_excerto"):
            continue
        cod = str(e.get("ibge") or "").zfill(7)
        if not cod or cod == "0000000":
            continue
        chave = (norm(e.get("municipio")), str(e.get("uf") or "").upper())
        if chave in no_banco or cod in em_fila or chave in em_fila:
            continue
        atual = fora.get(cod)
        if atual is None or str(e.get("data") or "") > str(atual.get("excerto_visto_em") or ""):
            fora[cod] = {"codigo_ibge": cod, "nome": e.get("municipio"), "uf": e.get("uf"),
                         "excerto_visto_em": e.get("data")}
    return fora


def documento(alvos_por_cod: dict, data: str) -> dict:
    """O arquivo de alvos, ordenado por UF e nome para ser reproduzível."""
    return {
        "_governanca": (
            "Primeira fila do juiz para o Querido Diário (decisão da editoria, 28/09/2026, item 1). São "
            "os municípios em que a varredura do diário reconheceu EXCERTO com termo do dicionário e "
            "que não estão no banco nem em fila nenhuma — o achado do item C da auditoria do funil. A "
            "lista é de ALVOS, não de pistas: `consultar_querido_diario.py --alvos` consulta cada um "
            "por termo de plano e produz a pista com o excerto CERTO, que é o que permite ao juiz "
            "recortar o ato de dentro da edição. Nada aqui pontua nem promove."),
        "gerado_em": data, "total": len(alvos_por_cod),
        "alvos": sorted(alvos_por_cod.values(), key=lambda a: (a["uf"] or "", a["nome"] or "")),
    }


def autoteste() -> int:
    casos = []
    execucoes = [
        {"canal": "DOM", "decisao": "com_excerto", "ibge": "3205002", "municipio": "Serra",
         "uf": "ES", "data": "2026-09-07"},
        {"canal": "DOM", "decisao": "com_excerto", "ibge": "3205002", "municipio": "Serra",
         "uf": "ES", "data": "2026-09-20"},                                  # mais recente
        {"canal": "DOM", "decisao": "com_excerto", "ibge": "9999999", "municipio": "NoBanco",
         "uf": "SP", "data": "2026-09-01"},
        {"canal": "DOM", "decisao": "com_excerto", "ibge": "8888888", "municipio": "EmFila",
         "uf": "SP", "data": "2026-09-01"},
        {"canal": "DOM", "decisao": "coberto_sem_mencao", "ibge": "7777777", "municipio": "SemMencao",
         "uf": "SP", "data": "2026-09-01"},
        {"canal": "busca_web", "decisao": "com_excerto", "ibge": "6666666", "municipio": "OutroCanal",
         "uf": "SP", "data": "2026-09-01"},
        {"canal": "DOM", "decisao": "com_excerto", "ibge": "1111111", "municipio": "Acre Um",
         "uf": "AC", "data": "2026-09-02"},
    ]
    fora = alvos(execucoes, no_banco={("nobanco", "SP")}, em_fila={"8888888"})
    casos.append(("só os sem registro e sem pista", sorted(fora) == ["1111111", "3205002"]))
    casos.append(("guarda a data do excerto mais recente",
                  fora["3205002"]["excerto_visto_em"] == "2026-09-20"))
    casos.append(("quem está no banco fica fora", "9999999" not in fora))
    casos.append(("quem está em fila fica fora", "8888888" not in fora))
    casos.append(("decisão que não é com_excerto fica fora", "7777777" not in fora))
    casos.append(("canal que não é DOM fica fora", "6666666" not in fora))
    casos.append(("o ibge vem com sete dígitos", all(len(c) == 7 for c in fora)))

    doc = documento(fora, "2026-09-28")
    casos.append(("o total confere com a lista", doc["total"] == len(doc["alvos"]) == 2))
    casos.append(("a ordem é por UF e nome, para ser reproduzível",
                  [a["uf"] for a in doc["alvos"]] == ["AC", "ES"]))
    casos.append(("o arquivo diz que é lista de ALVOS, não de pistas",
                  "ALVOS, não de pistas" in doc["_governanca"]))
    casos.append(("nenhum alvo carrega url, trecho ou categoria",
                  not any(k in a for a in doc["alvos"] for k in ("url", "trecho", "categoria"))))

    ruins = [n for n, ok in casos if not ok]
    for n, ok in casos:
        print(f"  {'OK  ' if ok else 'FALHA'} {n}")
    if ruins:
        print(f"X AUTOTESTE: {len(ruins)} caso(s) reprovado(s).")
        return 1
    print(f"OK AUTOTESTE — {len(casos)} casos, sem rede e sem escrita.")
    return 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()

    from coletores_base import gravar_em, hoje_editorial, ler_log

    def ler(nome):
        p = RAIZ / "data" / nome
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

    def lista(d, *chaves):
        if isinstance(d, list):
            return d
        for k in chaves:
            if isinstance((d or {}).get(k), list):
                return d[k]
        return []

    municipios = lista(ler("municipios.json"), "municipios")
    no_banco = {(norm(m.get("nome")), str(m.get("uf") or "").upper()) for m in municipios}
    em_fila = set()
    for nome in ("pistas_imprensa.json", "pistas_descobertas.json", "pistas_doe.json",
                 "pistas_querido_diario.json"):
        for p in lista(ler(nome), "pistas", "itens"):
            cod = str(p.get("ibge") or p.get("codigo_ibge") or "").zfill(7)
            if cod and cod != "0000000":
                em_fila.add(cod)
            chave = (norm(p.get("municipio") or p.get("nome")), str(p.get("uf") or "").upper())
            if chave[0]:
                em_fila.add(chave)

    fora = alvos(ler_log()["execucoes"], no_banco, em_fila)
    doc = documento(fora, hoje_editorial().isoformat())
    import collections
    print(f"{doc['total']} alvo(s): município com excerto no diário, sem registro e sem pista")
    print(f"  por UF: {sorted(collections.Counter(a['uf'] for a in doc['alvos']).items())}")

    if "--escrever" not in sys.argv:
        print("relatório apenas; nada escrito (use --escrever)")
        return 0
    gravar_em(DESTINO, doc)
    print(f"✓ data/{DESTINO.name} com {doc['total']} alvo(s). A pista sai da consulta ao QD "
          f"(`consultar_querido_diario.py --alvos`), não daqui.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
