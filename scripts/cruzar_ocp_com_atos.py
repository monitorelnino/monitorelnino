#!/usr/bin/env python3
"""Cruza a planilha oficial da Operação Carro-Pipa com `data/atos_resposta.json`.

Item 1.6 do HANDOVER_CORRECAO_DEFINITIVA_08-10-2026 (achado A3-06), e o §2.4 do
HANDOVER_preparacao_programatica_seca_05-10-2026, que mandava o cruzamento e não foi feito.

A planilha que o MIDR enviou em resposta a pedido de acesso à informação (05/10/2026) lista, por
município, as portarias de reconhecimento com data e DOU. Medido em 08/10/2026: **71 portarias
com data ≥ 29/06/2026 não têm par em `atos_resposta.json`**, e **70 municípios não têm evento
nenhum** — 68 deles em Pernambuco, 69 na MESMA portaria, a nº 2.203 (DOU de 06/07/2026), vizinha
das nº 2.200 e nº 2.212, que o banco tem. É lote inteiro perdido pelo coletor do DOU.

O que este script faz, e o que NÃO faz: ele grava o evento de reconhecimento com
`documento_nao_localizado: true`, porque a prova que se tem é a planilha oficial do órgão, não o
texto do DOU. O texto é anexado depois, pela busca dirigida; até lá o evento diz, no próprio campo,
que o documento não foi lido. Nada é inventado: a portaria, a data, o número do DOU e o processo
vêm da resposta ao pedido de acesso.

Saídas:
- `data/atos_resposta.json` — os eventos novos (com `--aplicar`);
- `data/programas_federais/ocp_x_s2id.json` — o relatório de coincidências e divergências por UF.

`--autoteste` é puro: fixture de duas portarias, uma presente e uma ausente, sem ler `data/`.
"""
import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
OCP = RAIZ / "data" / "programas_federais" / "ocp_2026.json"
ATOS = RAIZ / "data" / "atos_resposta.json"
RELATORIO = RAIZ / "data" / "programas_federais" / "ocp_x_s2id.json"
INICIO_DO_CICLO = "2026-06-29"  # o Boletim nº 1; antes dele o ato não é resposta a este ciclo
FONTE = ("resposta do MIDR a pedido de acesso à informação (05/10/2026), portaria no DOU")


def numeros(s) -> set:
    """TODOS os números de portaria do campo, não só o primeiro.

    Os reconhecimentos em lote guardam várias portarias numa string: "Portaria SEDEC/MIDR
    (lote: nº 2.793, nº 2.794, nº 2.795, nº 2.796)". Lendo só o primeiro número, o par de
    todas as outras se perde e o cruzamento as declara ausentes — foi assim que Santa
    Brígida/BA ganhou um evento duplicado na primeira aplicação. O desmembramento próprio
    desses lotes é o item 1.7; aqui basta não contá-los como faltantes.
    """
    return {m.group(0).replace(".", "") for m in
            re.finditer(r"\d[\d.]*\d|\d", str(s or ""))}


def numero(s) -> "str | None":
    ns = numeros(s)
    return sorted(ns)[0] if ns else None


def data_br(iso: str) -> str:
    a, m, d = str(iso).split("-")
    return f"{d}/{m}/{a}"


def faltantes(municipios_ocp, eventos) -> list:
    """As portarias da OCP com data ≥ início do ciclo sem par (ibge + número) no banco."""
    tem = set()
    for e in eventos:
        ib = str(e.get("ibge") or "")
        for n in numeros(e.get("portaria") or e.get("decreto")):
            tem.add((ib, n))
    fora = []
    for m in municipios_ocp:
        for p in m.get("portarias") or []:
            if str(p.get("data") or "") < INICIO_DO_CICLO:
                continue
            if (str(m.get("ibge") or ""), numero(p.get("numero"))) in tem:
                continue
            fora.append({"ibge": str(m["ibge"]), "uf": m["uf"], "nome_na_fonte": m["nome_na_fonte"],
                         "portaria": p["numero"], "data": p["data"],
                         "dou_numero": p.get("dou_numero"), "dou_data": p.get("dou_data"),
                         "processo": p.get("processo"),
                         "situacao_na_fonte": p.get("situacao_na_fonte")})
    return fora


def evento_de(f: dict, referencia: dict) -> dict:
    ref = referencia.get(f["ibge"]) or {}
    return {
        "nome": ref.get("nome") or f["nome_na_fonte"].title(),
        "uf": f["uf"], "ibge": f["ibge"],
        "data": data_br(f["data"]),
        "causa": "reconhecimento federal",
        "decreto": f"Portaria SEDEC/MIDR nº {f['portaria']}",
        "portaria": f"Portaria SEDEC/MIDR nº {f['portaria']}",
        "data_reconhecimento": data_br(f["data"]),
        "data_publicacao": data_br(f["dou_data"]) if f.get("dou_data") else data_br(f["data"]),
        "fonte": FONTE,
        "url": "",
        "lat": ref.get("lat"), "lon": ref.get("lon"),
        "canal": "DOU",
        "tipo_evento": "outro_declarado",
        "documento_nao_localizado": True,
        "por_que_documento_nao_localizado": (
            "A3-06: a portaria está na planilha oficial do MIDR (resposta a pedido de acesso de "
            "05/10/2026), com número, data e edição do DOU; o texto da portaria ainda não foi "
            "lido. A busca dirigida anexa o documento e este campo sai."),
        "dou": {"numero": f.get("dou_numero"), "data": f.get("dou_data"),
                "processo": f.get("processo")},
    }


def relatorio_por_uf(municipios_ocp, eventos, fora) -> dict:
    por_uf = {}
    for m in municipios_ocp:
        u = por_uf.setdefault(m["uf"], {"municipios_na_ocp": 0, "portarias_na_ocp": 0,
                                        "portarias_do_ciclo": 0, "sem_par_no_banco": 0,
                                        "municipios_sem_evento": 0})
        u["municipios_na_ocp"] += 1
        u["portarias_na_ocp"] += len(m.get("portarias") or [])
        u["portarias_do_ciclo"] += sum(1 for p in (m.get("portarias") or [])
                                       if str(p.get("data") or "") >= INICIO_DO_CICLO)
    com_evento = {str(e.get("ibge") or "") for e in eventos}
    for f in fora:
        por_uf[f["uf"]]["sem_par_no_banco"] += 1
        if f["ibge"] not in com_evento:
            por_uf[f["uf"]]["municipios_sem_evento"] += 1
    return por_uf


def autoteste() -> int:
    ocp = [{"ibge": "2611606", "uf": "PE", "nome_na_fonte": "RECIFE",
            "portarias": [{"numero": "2.203", "data": "2026-07-03", "dou_numero": "126",
                           "dou_data": "2026-07-06", "processo": "x"}]},
           {"ibge": "2704302", "uf": "AL", "nome_na_fonte": "MACEIÓ",
            "portarias": [{"numero": "2.200", "data": "2026-07-01"},
                          {"numero": "900", "data": "2026-03-01"}]}]
    eventos = [{"ibge": "2704302", "portaria": "Portaria SEDEC/MIDR nº 2.200"}]
    fora = faltantes(ocp, eventos)
    casos = [
        ("portaria presente no banco não entra",
         not any(f["portaria"] == "2.200" for f in fora)),
        ("portaria ausente entra", [f["portaria"] for f in fora] == ["2.203"]),
        ("portaria anterior ao ciclo não entra", all(f["data"] >= INICIO_DO_CICLO for f in fora)),
        ("o evento sai com documento não localizado",
         evento_de(fora[0], {})["documento_nao_localizado"] is True),
        ("o evento sai com a data em dd/mm/aaaa",
         evento_de(fora[0], {})["data"] == "03/07/2026"),
        ("a data de publicação é a do DOU",
         evento_de(fora[0], {})["data_publicacao"] == "06/07/2026"),
        ("o nome vem da referência do IBGE quando ela existe",
         evento_de(fora[0], {"2611606": {"nome": "Recife", "lat": -8.0, "lon": -34.9}})["nome"]
         == "Recife"),
        ("sem referência, o nome da planilha entra capitalizado",
         evento_de(fora[0], {})["nome"] == "Recife"),
        ("o relatório conta uma portaria do ciclo sem par em PE",
         relatorio_por_uf(ocp, eventos, fora)["PE"]["sem_par_no_banco"] == 1),
        ("o relatório conta o município sem evento nenhum",
         relatorio_por_uf(ocp, eventos, fora)["PE"]["municipios_sem_evento"] == 1),
    ]
    ruins = [n for n, ok in casos if not ok]
    for n, ok in casos:
        print(f"  {'ok ' if ok else 'FALHA'} {n}")
    print(f"autoteste: {len(casos) - len(ruins)}/{len(casos)}")
    return 1 if ruins else 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    ocp = json.loads(OCP.read_text(encoding="utf-8"))["municipios"]
    doc = json.loads(ATOS.read_text(encoding="utf-8"))
    eventos = doc["eventos"]
    fora = faltantes(ocp, eventos)
    com_evento = {str(e.get("ibge") or "") for e in eventos}
    sem_nada = {f["ibge"] for f in fora if f["ibge"] not in com_evento}
    print(f"portarias da OCP ≥ {data_br(INICIO_DO_CICLO)} sem par no banco: {len(fora)}")
    print(f"municípios sem evento nenhum: {len(sem_nada)}")

    rel = {"_governanca": ("Cruzamento da planilha oficial da Operação Carro-Pipa (resposta do "
                           "MIDR a pedido de acesso, 05/10/2026) com data/atos_resposta.json. "
                           "Item 1.6 / achado A3-06. Gerado por "
                           "scripts/cruzar_ocp_com_atos.py."),
           "inicio_do_ciclo": INICIO_DO_CICLO,
           "portarias_sem_par": len(fora),
           "municipios_sem_evento": len(sem_nada),
           "por_uf": relatorio_por_uf(ocp, eventos, fora),
           "faltantes": fora}
    RELATORIO.write_text(json.dumps(rel, ensure_ascii=False, indent=1) + "\n",
                         encoding="utf-8", newline="\n")
    print(f"relatório: {RELATORIO.relative_to(RAIZ)}")

    if "--aplicar" not in sys.argv:
        print("(sem --aplicar: nada foi gravado em data/atos_resposta.json)")
        return 0

    sys.path.insert(0, str(RAIZ))
    from coletores_base import referencia_ibge  # noqa: PLC0415
    por_cod, _ = referencia_ibge()
    ref = {c: {"nome": r["nome"], "lat": r.get("lat"), "lon": r.get("lon")}
           for c, r in por_cod.items()}
    novos = [evento_de(f, ref) for f in fora]
    doc["eventos"] = eventos + novos
    ATOS.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n",
                    encoding="utf-8", newline="\n")
    print(f"eventos gravados: {len(novos)} (todos com documento_nao_localizado)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
