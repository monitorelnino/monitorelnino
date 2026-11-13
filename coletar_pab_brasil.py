#!/usr/bin/env python3
"""Municípios das Áreas Suscetíveis à Desertificação (ASD) e Entorno — PAB-Brasil, Apêndice B, Tabela B.1.

A lista nominal está no próprio plano do MMA (PDF), com código IBGE, clima e classificação. O plano separa
ASD (pelo menos 1% do território com índice de aridez abaixo de 0,65; Cemaden/MCTI, 1990–2020) de Entorno
(Semiárido da Sudene, PAN-Brasil 2004 ou contiguidade), e o dado guarda a separação: Entorno não é ASD.

Camada de contexto, PESO ZERO: escreve só as chaves `pab_*` de `data/enquadramento_federal.json` e não
toca índice nenhum. Trava de leitura: os totais da Tabela 1 do plano (1.389 ASD + 260 Entorno = 1.649) e
todo código na base do projeto, com a UF da tabela igual à da base; se algo não fecha, nada é gravado.

USO
  python3 coletar_pab_brasil.py --autoteste
  python3 coletar_pab_brasil.py [--forcar]
"""
import io
import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))
from coletar_semiarido_sudene import precisa_reprocessar, SAIDA, MUNICIPIOS

FONTE = "https://www.gov.br/mma/pt-br/centrais-de-conteudo/publicacoes/povos-e-comunidades-tradicionais/pab-brasil.pdf"
INSTRUMENTO = ("Plano de Ação Brasileiro de Combate à Desertificação e Mitigação dos Efeitos da Seca (PAB-Brasil), "
               "Ministério do Meio Ambiente e Mudança do Clima; Apêndice B, Tabela B.1 — municípios das Áreas "
               "Suscetíveis à Desertificação e Entorno (índice de aridez: Cemaden/MCTI, 1990–2020)")
TOTAIS = {"ASD": 1389, "Entorno": 260}
UFS_ESPERADAS = {"AL", "BA", "CE", "ES", "MA", "MG", "MS", "PB", "PE", "PI", "RJ", "RN", "SE"}
# O texto do PDF quebra a célula em duas linhas ("Subúmido / Seco", "CIRCUNS- / CRITO") e nem sempre traz a
# letra acentuada inteira: o clima casa pelo radical e a classificação pelo começo.
LINHA = re.compile(r"\b(\d{7})\s+([A-Z]{2})\s+([^\d]{2,60}?)\s+(?<!\S)(Sub\S{1,2}mido(?:\s+Seco)?|Semi\S{1,2}rido|\S{1,2}rido|\S{1,2}mido)"
                   r"(?!\S)\s+(ASD|Entorno\s*\((SAB;\s*PAN|SAB|PAN|CIRCUNS))", re.I)
CODIGO = re.compile(r"\b(\d{7})\s+([A-Z]{2})\s")


def _clima(s: str) -> str:
    c = _chave(s)
    return "Subúmido seco" if c.startswith("sub") else "Semiárido" if c.startswith("semi") else "Árido" if c.endswith("rido") else "Úmido"


def _chave(s: str) -> str:
    import unicodedata
    return " ".join(unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().split())


def linhas_da_tabela(texto: str) -> dict:
    """{codigo: registro} da Tabela B.1. Código repetido com classificação diferente levanta. Pura."""
    fora = {}
    for m in LINHA.finditer(" ".join(str(texto or "").split())):
        r = {"codigo_ibge": m.group(1), "uf": m.group(2).upper(), "pab_brasil": "Entorno" if m.group(6) else "ASD",
             "pab_clima": _clima(m.group(4))}
        if m.group(6):
            r["pab_criterio_entorno"] = "; ".join(x.strip().upper() for x in m.group(6).split(";")).replace("CIRCUNS", "CIRCUNSCRITO")
        if fora.setdefault(r["codigo_ibge"], r) != r:
            raise ValueError(f"{r['codigo_ibge']} aparece duas vezes com leituras diferentes")
    return fora


def problemas(registros: dict, base: dict) -> list:
    """O que impede a gravação. Pura."""
    ruins = []
    for classe, esperado in TOTAIS.items():
        n = sum(1 for r in registros.values() if r["pab_brasil"] == classe)
        if n != esperado:
            ruins.append(f"{classe}: {n} municípios lidos, {esperado} na Tabela 1 do plano")
    fora_da_base = [c for c, r in registros.items() if (base.get(c) or {}).get("uf") != r["uf"]]
    if fora_da_base:
        ruins.append(f"{len(fora_da_base)} código(s) fora da base ou com UF diferente: {', '.join(fora_da_base[:8])}")
    estranhas = sorted({r["uf"] for r in registros.values()} - UFS_ESPERADAS)
    if estranhas:
        ruins.append(f"UF fora da área do plano: {', '.join(estranhas)}")
    return ruins


def fundir(anterior: dict, registros: dict, base: dict) -> dict:
    """Troca só as chaves `pab_*`; as outras famílias do arquivo ficam como estão. Pura."""
    municipios = {c: {k: v for k, v in r.items() if not k.startswith("pab_")}
                  for c, r in ((anterior or {}).get("municipios") or {}).items()}
    for c, r in registros.items():
        municipios[c] = {**{"codigo_ibge": c, "uf": r["uf"], "municipio": (base.get(c) or {}).get("nome")},
                         **(municipios.get(c) or {}), **{k: v for k, v in r.items() if k.startswith("pab_")}}
    return {**(anterior or {}), "municipios": dict(sorted(municipios.items()))}


def texto_das_paginas(corpo: bytes) -> str:
    """Só as páginas que trazem linha da tabela: o plano tem centenas de páginas e a tabela, dezenas."""
    import pdfplumber
    with pdfplumber.open(io.BytesIO(corpo)) as pdf:
        return "\n".join(t for t in ((pg.extract_text() or "") for pg in pdf.pages) if LINHA.search(" ".join(t.split())))


def autoteste() -> int:
    from coletores_base import rodar_autoteste
    texto = ("2100154 MA Água Doce do Maranhão Úmido Entorno (SAB; PAN)\n2100907 MA Araioses Subúmido Seco ASD "
             "2304202 CE Crato Semiárido ASD\n3160207 MG Santo Antônio do\nItambé Úmido Entorno (CIRCUNSCRITO) "
             "Tabela 1 – 1.649 municípios 2611101 PE Petrolina A´rido ASD 2101509 MA Barão de Grajaú Subúmido ASD Seco "
             "3116803 MG Coluna Úmido Entorno (CIRCUNS- CRITO)")
    regs = linhas_da_tabela(texto)
    base = {"2100154": {"uf": "MA", "nome": "Água Doce do Maranhão"}, "2100907": {"uf": "MA", "nome": "Araioses"},
            "2304202": {"uf": "CE", "nome": "Crato"}, "3160207": {"uf": "MG", "nome": "Santo Antônio do Itambé"}, "2101509": {"uf": "MA", "nome": "Barão de Grajaú"}, "3116803": {"uf": "MG", "nome": "Coluna"},
            "2611101": {"uf": "PE", "nome": "Petrolina"}}
    antes = {"municipios": {"2304202": {"codigo_ibge": "2304202", "uf": "CE", "municipio": "Crato", "semiarido": True},
                            "1100205": {"codigo_ibge": "1100205", "mma_prioritario_desmatamento": True, "pab_brasil": "ASD"}},
             "fontes": {"semiarido": {"hash": "x"}}}
    junto = fundir(antes, regs, base)
    cheio = {str(2300000 + i): {"uf": "CE", "pab_brasil": "ASD" if i < 1389 else "Entorno"} for i in range(1649)}
    return rodar_autoteste({
        "célula quebrada em duas linhas e acento solto são lidos: subúmido seco, árido e circunscrito":
            lambda: regs["2101509"]["pab_clima"] == "Subúmido seco" and regs["2611101"]["pab_clima"] == "Árido"
            and regs["3116803"]["pab_criterio_entorno"] == "CIRCUNSCRITO",
        "lê sete linhas, com nome quebrado em duas e texto solto no meio":
            lambda: len(regs) == 7 and regs["3160207"]["pab_criterio_entorno"] == "CIRCUNSCRITO",
        "ASD e Entorno ficam separados, com o clima e o critério do Entorno como a tabela escreve":
            lambda: regs["2100907"] == {"codigo_ibge": "2100907", "uf": "MA", "pab_brasil": "ASD", "pab_clima": "Subúmido seco"}
            and regs["2100154"]["pab_brasil"] == "Entorno" and regs["2100154"]["pab_criterio_entorno"] == "SAB; PAN"
            and regs["2611101"]["pab_clima"] == "Árido" and regs["2304202"]["pab_clima"] == "Semiárido",
        "mesmo código com leituras diferentes levanta":
            lambda: _levanta(lambda: linhas_da_tabela("2304202 CE Crato Semiárido ASD 2304202 CE Crato Úmido Entorno (PAN)")),
        "total diferente da Tabela 1 reprova; total certo com base certa passa":
            lambda: any("1389" in p for p in problemas(regs, base))
            and problemas(cheio, {c: {"uf": "CE"} for c in cheio}) == [],
        "código fora da base, UF trocada e UF fora do plano reprovam":
            lambda: any("fora da base" in p for p in problemas({"2304202": {"uf": "PE", "pab_brasil": "ASD"}}, base))
            and any("fora da área" in p for p in problemas({"4300000": {"uf": "RS", "pab_brasil": "ASD"}}, {})),
        "fusão: as outras famílias ficam; quem saiu da tabela perde só a marca do plano; o nome vem da base":
            lambda: junto["municipios"]["2304202"]["semiarido"] is True and junto["municipios"]["2304202"]["pab_brasil"] == "ASD"
            and "pab_brasil" not in junto["municipios"]["1100205"] and junto["municipios"]["1100205"]["mma_prioritario_desmatamento"]
            and junto["municipios"]["2611101"]["municipio"] == "Petrolina" and junto["fontes"] == antes["fontes"],
        "garantia estrutural: só escreve o arquivo do enquadramento":
            lambda: re.findall(r"gravar_em\(([^,)]+)", open(__file__, encoding="utf-8").read().split("def main")[-1]) == ["SAIDA"],
    })


def _levanta(f) -> bool:
    try:
        f()
    except ValueError:
        return True
    return False


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    from coletores_base import buscar, gravar_em, hoje_editorial, preservar_evidencia, sha256
    hoje = hoje_editorial()
    corpo = buscar(FONTE, timeout=180, origem="coletar_pab_brasil")
    impressao = sha256(corpo)
    anterior = json.loads(SAIDA.read_text(encoding="utf-8")) if SAIDA.exists() else {}
    if not precisa_reprocessar(anterior, impressao, hoje, familia="pab_brasil") and "--forcar" not in sys.argv:
        print("documento igual e conferido há menos de 7 dias: nada a reprocessar.")
        return 0
    base = {str(m["ibge"]).zfill(7): {"uf": m.get("uf"), "nome": m.get("nome")}
            for m in json.loads(MUNICIPIOS.read_text(encoding="utf-8")) if m.get("ibge")}
    texto = texto_das_paginas(corpo)
    registros = linhas_da_tabela(texto)
    conta = lambda campo: {v: sum(1 for r in registros.values() if r.get(campo) == v)
                           for v in sorted({r.get(campo) for r in registros.values()} - {None})}
    print(f"tabela: {len(registros)} municípios · {conta('pab_brasil')} · clima {conta('pab_clima')} · "
          f"entorno {conta('pab_criterio_entorno')} · UF {conta('uf')} · evidência {impressao[:12]}")
    ruins = problemas(registros, base)
    if ruins:
        print("X VALIDAÇÃO — nada foi gravado:")
        for r in ruins:
            print("   -", r)
        plano = " ".join(texto.split())
        soltas = [plano[m.start():m.start() + 90] for m in CODIGO.finditer(plano) if m.group(1) not in registros]
        print(f"   linhas com código e sem leitura: {len(soltas)}; primeiras: {soltas[:12]}")
        return 1
    preservar_evidencia(corpo, FONTE, "pdf", "coletar_pab_brasil")
    saida = fundir(anterior, registros, base)
    saida["fontes"] = {**(saida.get("fontes") or {}),
                       "pab_brasil": {"instrumento": INSTRUMENTO, "url": FONTE, "consultado_em": hoje.isoformat(),
                                      "hash": impressao, "total_asd": TOTAIS["ASD"], "total_entorno": TOTAIS["Entorno"]}}
    saida["atualizado_em"] = hoje.isoformat()
    gravar_em(SAIDA, saida)
    print(f"{SAIDA.relative_to(RAIZ)} gravado · {len(registros)} municípios do PAB-Brasil")
    return 0


if __name__ == "__main__":
    sys.exit(main())
