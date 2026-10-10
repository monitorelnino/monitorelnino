#!/usr/bin/env python3
"""
amostra_auditoria_semanal.py
============================
Etapa 8 do codebook do juiz: a amostra que a editoria confere toda semana.

Handover `HANDOVER_juiz_automatico_e_busca_web_27-09-2026.md` (PR 2, Etapa 8): "Toda semana, 10%
das promoções (mínimo 10) e 10% das recusas vão para
`notas/preprint/testes/e1_auditoria_semanal_<data>.csv`, com o pacote cego do E1. A editoria
confere; desacordo vira errata e, se for regra, vira caso de teste."

POR QUE ISTO EXISTE
-------------------
O juiz decide sozinho, e é isso que a regra R7 revisada autoriza. O que impede o erro de virar
permanente não é a confiança no juiz: é esta amostra. Desacordo humano vira errata; se o desacordo
for de REGRA, vira canário em `juiz.py` — e aí o mesmo erro não volta.

CEGO
----
A planilha não mostra o que o juiz decidiu. Traz o município, a URL, o trecho de cada critério e
colunas vazias para a leitura humana. A decisão do juiz fica num arquivo IRMÃO
(`..._gabarito.csv`), que a editoria abre **depois** de preencher. Sem isso a auditoria mede
concordância com um rótulo já visto, que é outra coisa — e é o E1 do preprint que depende disso.

A amostra é **reprodutível**: semente derivada da data da amostra, para que a mesma semana sorteie
a mesma amostra em qualquer máquina.

USO
  python3 scripts/amostra_auditoria_semanal.py --autoteste
  python3 scripts/amostra_auditoria_semanal.py                       # imprime o resumo
  python3 scripts/amostra_auditoria_semanal.py --saida <dir>         # grava os dois CSV
"""
import csv
import io
import json
import pathlib
import random
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

MINIMO = 10
FRACAO = 0.10

COLUNAS_CEGAS = ["pista_id", "municipio", "uf", "ibge", "url", "codebook",
                 "trecho_1_identidade", "trecho_2_citacao", "trecho_3_autoridade",
                 "trecho_4_natureza", "trecho_5_familia", "trecho_6_categoria",
                 "errata_promove", "errata_categoria", "errata_motivo", "errata_observacao"]
COLUNAS_GABARITO = ["pista_id", "juiz_promove", "juiz_categoria", "juiz_motivo", "juiz_data",
                    "juiz_natureza", "juiz_familia", "hash_evidencia"]


def semente_da_data(data_iso: str) -> int:
    """Semente reprodutível a partir da data: a mesma semana sorteia a mesma amostra."""
    return int("".join(c for c in str(data_iso) if c.isdigit()) or "0")


def tamanho_da_amostra(n: int) -> int:
    """10%, com mínimo de 10 — e nunca mais do que existe."""
    if n <= 0:
        return 0
    return min(n, max(MINIMO, int(round(n * FRACAO))))


def sortear(decisoes: list, data_iso: str) -> dict:
    """Devolve {'promocoes': [...], 'recusas': [...]}, sorteadas de forma reprodutível.

    Ordena por `pista_id` antes de sortear: a ordem do arquivo de decisões cresce a cada rodada, e
    sem a ordenação a mesma semente devolveria amostras diferentes."""
    promovidas = sorted((d for d in decisoes if d.get("promove")), key=lambda d: str(d.get("pista_id")))
    recusadas = sorted((d for d in decisoes if not d.get("promove")), key=lambda d: str(d.get("pista_id")))
    r = random.Random(semente_da_data(data_iso))
    return {"promocoes": r.sample(promovidas, tamanho_da_amostra(len(promovidas))),
            "recusas": r.sample(recusadas, tamanho_da_amostra(len(recusadas)))}


def linha_cega(d: dict) -> dict:
    c = d.get("criterios") or {}
    def tr(k):
        return (c.get(k) or {}).get("trecho") or ""
    return {"pista_id": d.get("pista_id"), "municipio": d.get("municipio"), "uf": d.get("uf"),
            "ibge": d.get("ibge"), "url": d.get("url"), "codebook": d.get("codebook"),
            "trecho_1_identidade": tr("1_identidade"), "trecho_2_citacao": tr("2_citacao"),
            "trecho_3_autoridade": tr("3_autoridade"), "trecho_4_natureza": tr("4_natureza"),
            "trecho_5_familia": tr("5_familia_de_risco"), "trecho_6_categoria": tr("6_categoria"),
            "errata_promove": "", "errata_categoria": "", "errata_motivo": "", "errata_observacao": ""}


def linha_gabarito(d: dict) -> dict:
    return {"pista_id": d.get("pista_id"), "juiz_promove": "sim" if d.get("promove") else "nao",
            "juiz_categoria": d.get("categoria") or "", "juiz_motivo": d.get("motivo") or "",
            "juiz_data": d.get("data") or "", "juiz_natureza": d.get("natureza") or "",
            "juiz_familia": d.get("familia_de_risco") or "",
            "hash_evidencia": d.get("hash_evidencia") or ""}


def escrever_csv(caminho: pathlib.Path, colunas: list, linhas: list) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with io.open(caminho, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=colunas, lineterminator="\n")
        w.writeheader()
        for linha in linhas:
            w.writerow(linha)


def autoteste() -> int:
    casos = []
    decisoes = ([{"pista_id": f"p{i}", "promove": True, "categoria": "plano", "municipio": f"M{i}",
                  "uf": "SP", "criterios": {"1_identidade": {"trecho": f"nomeia M{i}"}}}
                 for i in range(40)]
                + [{"pista_id": f"r{i}", "promove": False, "motivo": "citacao_incompleta",
                    "municipio": f"N{i}", "uf": "MG", "criterios": {}} for i in range(200)])

    a = sortear(decisoes, "2026-09-27")
    casos.append(("10% das promoções, respeitando o mínimo", len(a["promocoes"]) == 10))
    casos.append(("10% das recusas", len(a["recusas"]) == 20))
    casos.append(("promoções e recusas não se misturam",
                  all(d["promove"] for d in a["promocoes"]) and all(not d["promove"] for d in a["recusas"])))

    b = sortear(list(reversed(decisoes)), "2026-09-27")
    casos.append(("reprodutível e indiferente à ordem do arquivo",
                  [d["pista_id"] for d in a["promocoes"]] == [d["pista_id"] for d in b["promocoes"]]))
    c = sortear(decisoes, "2026-10-04")
    casos.append(("semana diferente, amostra diferente",
                  [d["pista_id"] for d in a["recusas"]] != [d["pista_id"] for d in c["recusas"]]))

    casos.append(("mínimo de 10 quando 10% dá menos", tamanho_da_amostra(12) == 10))
    casos.append(("nunca pede mais do que existe", tamanho_da_amostra(3) == 3))
    casos.append(("nada a auditar devolve zero", tamanho_da_amostra(0) == 0))

    l = linha_cega(decisoes[0])
    casos.append(("a planilha é CEGA: nenhuma coluna revela a decisão do juiz",
                  not any(k.startswith("juiz") for k in l)
                  and "promove" not in l and "categoria" not in l and "motivo" not in l))
    casos.append(("as colunas de errata vêm vazias",
                  all(l[k] == "" for k in ("errata_promove", "errata_categoria", "errata_motivo"))))
    casos.append(("o trecho de cada critério viaja para a planilha",
                  l["trecho_1_identidade"] == "nomeia M0"))
    g = linha_gabarito(decisoes[0])
    casos.append(("o gabarito é arquivo irmão e traz a decisão", g["juiz_promove"] == "sim"))
    casos.append(("gabarito e planilha cega casam pela pista_id",
                  g["pista_id"] == l["pista_id"]))
    casos.append(("as colunas cegas e do gabarito não se sobrepõem além da chave",
                  set(COLUNAS_CEGAS) & set(COLUNAS_GABARITO) == {"pista_id"}))

    ruins = [n for n, ok in casos if not ok]
    for n, ok in casos:
        print(f"  {'OK  ' if ok else 'FALHA'} {n}")
    if ruins:
        print(f"X AUTOTESTE: {len(ruins)} caso(s) reprovado(s).")
        return 1
    print(f"OK AUTOTESTE — {len(casos)} casos.")
    return 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()

    from coletores_base import hoje_editorial

    caminho = RAIZ / "data" / "promocoes_automaticas.json"
    if not caminho.exists():
        print("✓ sem decisões do juiz ainda (data/promocoes_automaticas.json não existe) — nada a amostrar.")
        return 0
    decisoes = json.loads(caminho.read_text(encoding="utf-8")).get("decisoes") or []
    data_iso = hoje_editorial().isoformat()
    a = sortear(decisoes, data_iso)
    print(f"{len(decisoes)} decisão(ões) do juiz; amostra de {len(a['promocoes'])} promoção(ões) "
          f"e {len(a['recusas'])} recusa(s) (semana de {data_iso})")

    if "--saida" not in sys.argv:
        print("sem --saida: nada gravado. A planilha vive no repositório privado, em notas/preprint/testes/.")
        return 0
    destino = pathlib.Path(sys.argv[sys.argv.index("--saida") + 1])
    cega = destino / f"e1_auditoria_semanal_{data_iso}.csv"
    gabarito = destino / f"e1_auditoria_semanal_{data_iso}_gabarito.csv"
    escrever_csv(cega, COLUNAS_CEGAS, [linha_cega(d) for d in a["promocoes"] + a["recusas"]])
    escrever_csv(gabarito, COLUNAS_GABARITO, [linha_gabarito(d) for d in a["promocoes"] + a["recusas"]])
    print(f"planilha cega:  {cega}")
    print(f"gabarito:       {gabarito}  (abrir DEPOIS de preencher a cega)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
