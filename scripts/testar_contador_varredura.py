#!/usr/bin/env python3
"""Portão — o contador da varredura precisa classificar pelos prefixos REAIS.

Criado em 20/09/2026 (§121). Até aqui `recalcular_mare.py` contava como "sem menção"
o município cujo resultado começasse com a string `"sem edições"` — string que
`coletar_diarios_municipais.py` nunca gravou. Efeito: nenhum município caía em
`sem_mencao`, `com_mencao` igualava `consultados`, e o número publicado na cortina
do domínio afirmava que **3.180 municípios tinham menção a El Niño** quando eram
**153**. Vinte vezes mais. A Action ficava verde: nada falhava, a conta só media
outra coisa.

Os quatro estados que o coletor grava são distintos e não podem ser colapsados:

  sem_cobertura_qd      o município NÃO tem diário indexado — não há o que ler
  coberto_sem_mencao    indexado e lido; nenhum excerto sobre o tema
  (conteúdo)            indexado, lido, com decreto ou pista localizada
  cobertura a confirmar o teste de cobertura falhou; estado desconhecido

A distinção que mais importa é a primeira. **Não indexado não é sem menção.** Somar
os dois faria o site afirmar ausência de plano onde há apenas ausência de fonte —
exatamente o que §4.1.2 proíbe, e o que destrói a credibilidade de um índice cuja
promessa é nunca dizer "não existe" quando só sabe "não localizamos".

Uso: python3 scripts/testar_contador_varredura.py
"""
import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
FONTE = RAIZ / "recalcular_mare.py"
RESUMO = RAIZ / "data" / "verificacao_resumo.json"

# Prefixos que coletar_diarios_municipais.py realmente grava.
PREFIXOS = ("sem_cobertura_qd", "coberto_sem_mencao", "cobertura a confirmar")


def main() -> int:
    falhas = []
    fonte = FONTE.read_text(encoding="utf-8")
    # Só o CÓDIGO conta: o comentário que documenta o defeito cita a string fantasma
    # de propósito, e o portão não pode cair por causa da própria explicação.
    codigo = "\n".join(l.split("#", 1)[0] for l in fonte.splitlines())

    # 1. A string fantasma não pode voltar (no código, não no comentário).
    if "sem edições" in codigo:
        falhas.append('recalcular_mare.py voltou a classificar por "sem edições" — prefixo que '
                      'o coletor nunca grava; a conta mediria outra coisa em silêncio')

    # 2. Os prefixos reais precisam estar sendo usados na classificação.
    for p in PREFIXOS[:2]:
        if p not in codigo:
            falhas.append(f"recalcular_mare.py não menciona o prefixo real {p!r}")

    # 3. O resumo derivado precisa trazer as classes separadas e somar os consultados.
    if not RESUMO.exists():
        print("✗ data/verificacao_resumo.json não existe")
        return 1
    v = json.loads(RESUMO.read_text(encoding="utf-8")).get("varredura_diarios") or {}
    if not v:
        print("✗ verificacao_resumo.json sem varredura_diarios")
        return 1

    obrigatorios = ["consultados", "total", "com_mencao", "coberto_sem_mencao",
                    "sem_cobertura_qd", "cobertura_indefinida", "indexados", "sem_mencao"]
    faltando = [c for c in obrigatorios if c not in v]
    if faltando:
        falhas.append(f"varredura_diarios sem os campos {faltando} — as classes precisam ser "
                      f"publicáveis separadamente")
    else:
        soma = (v["com_mencao"] + v["coberto_sem_mencao"]
                + v["sem_cobertura_qd"] + v["cobertura_indefinida"])
        if soma != v["consultados"]:
            falhas.append(f"as classes somam {soma} mas consultados = {v['consultados']} — "
                          f"algum município está fora de classificação ou contado duas vezes")

        # 4. A confusão que destrói a credibilidade: sem_mencao não pode absorver os não indexados.
        if v["sem_mencao"] != v["coberto_sem_mencao"]:
            falhas.append(f"sem_mencao ({v['sem_mencao']}) difere de coberto_sem_mencao "
                          f"({v['coberto_sem_mencao']}) — 'sem menção' só vale para diário "
                          f"efetivamente lido; incluir não indexado afirma ausência de plano "
                          f"onde há ausência de fonte (§4.1.2)")

        # 5. com_mencao igual a consultados é a assinatura exata do defeito antigo.
        if v["consultados"] and v["com_mencao"] == v["consultados"]:
            falhas.append("com_mencao == consultados: assinatura do defeito de §121 (todo "
                          "município consultado contado como tendo menção)")

        if v["indexados"] != v["com_mencao"] + v["coberto_sem_mencao"]:
            falhas.append("indexados deve ser com_mencao + coberto_sem_mencao")

    if falhas:
        for f in falhas:
            print(f"✗ {f}")
        return 1

    print(f"✓ contador da varredura: {v['consultados']} consultados = {v['com_mencao']} com menção "
          f"+ {v['coberto_sem_mencao']} lidos sem menção + {v['sem_cobertura_qd']} sem diário "
          f"indexado + {v['cobertura_indefinida']} indefinidos; não indexado não é contado "
          f"como sem menção")
    return 0


if __name__ == "__main__":
    sys.exit(main())
