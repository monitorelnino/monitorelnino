#!/usr/bin/env python3
"""Confere no diário oficial cada emergência declarada por governo de estado (`data/resposta/emergencias_estaduais.json`).

O ato entra no arquivo por curadoria, com o endereço da edição; só vai ao mapa com `conferido: true`, que este
script grava depois de achar no texto da edição o número do decreto, a data por extenso e a palavra emergência,
com a cópia preservada em `evidencias/`. Não achou: fica `conferido: false`, com o motivo, e o mapa não o mostra.
`vigente_ate` = publicação + dias − 1 (vigor na data da publicação, dias corridos).

USO
  python3 conferir_emergencias_estaduais.py --autoteste
  python3 conferir_emergencias_estaduais.py [--forcar]
"""
import datetime
import re
import sys

from coletores_base import RAIZ, gravar_em, ler, rodar_autoteste

ARQUIVO = RAIZ / "data" / "resposta" / "emergencias_estaduais.json"
MESES = "janeiro fevereiro março abril maio junho julho agosto setembro outubro novembro dezembro".split()


def confere(ato: dict, texto: str) -> str:
    """'' quando o texto traz o decreto; senão, o que faltou. Pura."""
    t = " ".join(str(texto or "").split())
    d = datetime.date.fromisoformat(ato["data_ato"])
    faltou = []
    if not re.search(r"DECRETO\s+N[ºo°.]*\s*" + re.escape(ato["numero"]) + r"\b", t, re.I):
        faltou.append(f"Decreto nº {ato['numero']}")
    if not re.search(rf"\b0?{d.day}º?\s+de\s+{MESES[d.month - 1]}\s+de\s+{d.year}", t, re.I):
        faltou.append(f"a data {d.day} de {MESES[d.month - 1]} de {d.year}")
    if not re.search(r"emerg[êe]ncia", t, re.I):
        faltou.append("a palavra emergência")
    return "não achados no texto da edição: " + ", ".join(faltou) if faltou else ""


def vigente_ate(ato: dict) -> str:
    return (datetime.date.fromisoformat(ato["data_publicacao"]) + datetime.timedelta(days=ato["dias"] - 1)).isoformat()


def autoteste() -> int:
    ato = {"numero": "5.767", "data_ato": "2026-11-11", "data_publicacao": "2026-11-12", "dias": 120}
    bom = "DECRETO Nº 5.767, DE 11 DE NOVEMBRO DE 2026 Declara situação de emergência ambiental e climática"
    return rodar_autoteste({
        "edição com número, data por extenso e emergência confere": lambda: confere(ato, bom) == "",
        "outro número não confere (5.7670 nem 5.76)": lambda: "5.767" in confere(ato, bom.replace("5.767", "5.7670"))
            and "Decreto nº 5.76" in confere({**ato, "numero": "5.76"}, bom.replace("5.767", "5.769")),
        "data ausente e sem emergência são nomeadas": lambda: confere(ato, "DECRETO Nº 5.767 Dispõe sobre férias")
            == "não achados no texto da edição: a data 11 de novembro de 2026, a palavra emergência",
        "vigência: 120 dias corridos a partir da publicação": lambda: vigente_ate(ato) == "2027-03-11",
        "garantia estrutural: só grava o próprio arquivo": lambda: re.findall(
            r"gravar_em\(([^,)]+)", open(__file__, encoding="utf-8").read()) == ["ARQUIVO"],
    })


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    from coletores_base import buscar, preservar_evidencia
    from julgar_e_aplicar_descobertas import extrair_texto_pdf
    doc = ler("resposta/emergencias_estaduais.json", {"atos": []})
    for ato in doc["atos"]:
        if ato.get("conferido") and "--forcar" not in sys.argv:
            continue
        try:
            corpo = buscar(ato["url"], timeout=180, origem="conferir_emergencias_estaduais")
        except Exception as e:  # noqa: BLE001 — fonte externa: fica não conferido, com o motivo
            ato.update(conferido=False, motivo=f"edição não lida: {type(e).__name__}: {str(e)[:80]}")
            continue
        motivo = confere(ato, extrair_texto_pdf(corpo))
        ato.update(conferido=not motivo, motivo=motivo or None, vigente_ate=vigente_ate(ato),
                   hash_evidencia=preservar_evidencia(corpo, ato["url"], "pdf", "conferir_emergencias_estaduais") if not motivo else None,
                   conferido_em=datetime.date.today().isoformat())
        print(f"[{ato['uf']}] Decreto nº {ato['numero']}: {'conferido' if not motivo else motivo}")
    gravar_em(ARQUIVO, doc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
