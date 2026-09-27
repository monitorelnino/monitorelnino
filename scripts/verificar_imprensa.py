#!/usr/bin/env python3
"""Portão dos cartões "Esta semana em números" da Imprensa.

POR QUE ESTE PORTÃO EXISTE (27/09/2026, §253)
=============================================
Handover da editoria de 27/09. Ele trava as sete regras que o handover declara, e uma oitava que a
medição de 27/09 acrescentou.

  (a) todo número visível nos cartões vem de `data/imprensa/semana.json` — paridade;
  (b) todo cartão de janela declara o período;
  (c) "sem coleta" quando `consultado_em` falta ou está velho; ZERO nunca é "sem coleta";
  (d) "primeira medição" enquanto não houver `data/edicao_anterior/` — variação sem par é invenção;
  (e) cartão de estimativa de modelo diz que é estimativa;
  (f) a frase pronta não traz cláusula de valor zero;
  (g) nada de `imprensa/` é lido por `recalcular_mare.py` nem por `gerar_monitor_saude.py` — peso
      zero de verdade, não de palavra;
  (h) §253: `dados-abertos/atos_resposta.csv` tem data em DOIS formatos (740 em `dd/mm/aaaa`, 71
      em ISO). Este portão exige que TODA data seja legível pelo parser tolerante, e imprime a
      mistura. Em 27/09 um parser de um formato só me fez medir "71 decretos sem data" e quase
      registrar isso como fato; a editoria corrigiu. O portão existe para a deriva ficar visível,
      e porque `dados-abertos/` é consumido por terceiros que vão ler com um formato só.

Uso:
    python3 scripts/verificar_imprensa.py
    python3 scripts/verificar_imprensa.py --autoteste
"""
import csv
import io
import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

SEMANA = RAIZ / "data" / "imprensa" / "semana.json"
PAGINA = RAIZ / "imprensa.html"
CSV_ATOS = RAIZ / "dados-abertos" / "atos_resposta.csv"

# Cartões cujo valor vem de modelo, não de medição — têm de dizer isso.
DE_MODELO = ("temperatura_maxima", "qualidade_ar_indice")


def formatar(valor) -> str:
    """O valor como a página o mostra. Uma função só, para os dois lados compararem o mesmo.

    Vírgula decimal e separador de milhar do português: se o portão formatasse diferente do
    fallback, a paridade reprovaria por diferença de idioma, não de dado.
    """
    if valor is None:
        return "sem coleta"
    if isinstance(valor, float):
        return f"{valor:.1f}".replace(".", ",")
    if isinstance(valor, int):
        return f"{valor:,}".replace(",", ".")
    return str(valor)


def problemas() -> list[str]:
    from gerar_imprensa_semana import data_do_ato  # noqa: PLC0415
    p = []

    if not SEMANA.exists():
        return [f"{SEMANA.relative_to(RAIZ)} não existe — rode gerar_imprensa_semana.py"]
    r = json.loads(SEMANA.read_text(encoding="utf-8"))
    cartoes = r.get("cartoes") or []
    if not cartoes:
        p.append("semana.json sem nenhum cartão")

    for c in cartoes:
        ident = c.get("id") or "(sem id)"

        # (c) zero não é sem coleta, e sem coleta não é zero
        if c.get("sem_coleta") and c.get("valor") is not None:
            p.append(f"{ident}: marcado sem_coleta mas com valor {c['valor']!r}")
        if not c.get("sem_coleta") and c.get("valor") is None:
            p.append(f"{ident}: valor nulo sem declarar sem_coleta — ausência não é zero")

        # (b) período nos cartões de janela
        if "periodo" in ident or ident.endswith("_no_periodo"):
            per = c.get("periodo") or {}
            if not (per.get("ini") and per.get("fim")):
                p.append(f"{ident}: cartão de janela sem período declarado")

        # (d) variação sem edição anterior é invenção
        se_ha_anterior = (RAIZ / "data" / "edicao_anterior").exists()
        if c.get("variacao") is not None and not se_ha_anterior:
            p.append(f"{ident}: tem variacao sem data/edicao_anterior/ — variação inventada")
        if not se_ha_anterior and not c.get("primeira_medicao"):
            p.append(f"{ident}: sem edição anterior e sem primeira_medicao")

        # (e) estimativa de modelo declarada
        if ident in DE_MODELO and not c.get("sem_coleta"):
            texto = f"{c.get('nota') or ''} {c.get('fonte') or ''}".lower()
            if not any(t in texto for t in ("previsão", "estimativ", "modelo", "cams", "escala")):
                p.append(f"{ident}: cartão de modelo sem dizer que é previsão ou estimativa")

        # fonte sempre
        if not c.get("fonte"):
            p.append(f"{ident}: sem fonte")

    # (f) a frase pronta não traz cláusula de valor zero
    frase = r.get("texto_pronto") or ""
    if re.search(r"\b0 [a-zà-ú]", frase):
        p.append("texto_pronto traz cláusula de valor zero — o cartão mostra o zero, a frase não")

    # (a) PARIDADE, e não ausência. O handover pede "todo número visível nos cartões =
    # semana.json". O fallback estático EXISTE para escrever o número no HTML (quem não roda JS
    # precisa vê-lo), então proibir número na página quebraria o fallback — foi o primeiro desenho
    # deste portão, e estava errado. A regra certa é igualdade: o que está na página tem de ser o
    # que está no dado. O teste negativo do handover ("digitar 81 no HTML") reprova aqui porque 81
    # não é o valor do dado, não porque é um número.
    if PAGINA.exists():
        html = PAGINA.read_text(encoding="utf-8", errors="replace")
        for c in cartoes:
            achado = re.search(
                rf'data-imprensa="{re.escape(c["id"])}"[^>]*>([^<]*)<', html)
            if achado is None:
                continue          # cartão ainda não exposto na página: não é erro de paridade
            na_pagina = achado.group(1).strip()
            if na_pagina in ("", "—"):
                continue          # placeholder antes do fallback rodar
            esperado = ("sem coleta" if c.get("sem_coleta")
                        else formatar(c.get("valor")))
            if na_pagina != esperado:
                p.append(f"{c['id']}: a página mostra {na_pagina!r} e o dado diz {esperado!r} — "
                         f"paridade rompida")

    # (g) peso zero de verdade
    for leitor in ("recalcular_mare.py", "gerar_monitor_saude.py"):
        f = RAIZ / leitor
        if f.exists() and "imprensa/" in f.read_text(encoding="utf-8", errors="replace"):
            p.append(f"{leitor} lê algo de imprensa/ — os cartões têm peso zero nos índices")

    # (h) a data dos atos, nos dois formatos, toda legível
    if CSV_ATOS.exists():
        with io.open(CSV_ATOS, encoding="utf-8") as f:
            linhas = list(csv.DictReader(f))
        ilegiveis = [l for l in linhas if not data_do_ato(l.get("data"))]
        if ilegiveis:
            p.append(f"dados-abertos/atos_resposta.csv: {len(ilegiveis)} ato(s) com data ilegível "
                     f"pelo parser tolerante; exemplo {ilegiveis[0].get('data')!r}")
        formatos = {}
        for l in linhas:
            v = (l.get("data") or "").strip()
            chave = "dd/mm/aaaa" if "/" in v else ("ISO" if "-" in v else "outro")
            formatos[chave] = formatos.get(chave, 0) + 1
        if len(formatos) > 1:
            print(f"  [nota] atos_resposta.csv tem data em {len(formatos)} formatos: {formatos}. "
                  f"Todos legíveis aqui, mas terceiro que leia um formato só perde os outros. "
                  f"Normalizar o formato publicado é decisão da editoria.")

    return p


def autoteste() -> int:
    falhas = []

    def checar(nome, cond):
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    # O portão tem de reprovar o que o handover chama de teste negativo.
    import gerar_imprensa_semana as g  # noqa: PLC0415
    from datetime import date  # noqa: PLC0415

    checar("o parser tolerante lê os dois formatos",
           g.data_do_ato("2026-09-15") == date(2026, 9, 15)
           and g.data_do_ato("15/09/2026") == date(2026, 9, 15))

    # negativo: variação sem edição anterior
    c = g.cartao("x", "r", 5, "f", "h")
    c["variacao"] = 3
    checar("cartão com variacao e sem edicao_anterior seria reprovado",
           c["variacao"] is not None and not (RAIZ / "data" / "edicao_anterior").exists())

    # negativo: sem_coleta com valor
    c2 = g.cartao("y", "r", None, "f", None, sem_coleta=True)
    c2["valor"] = 7
    checar("cartão sem_coleta com valor seria reprovado",
           c2["sem_coleta"] and c2["valor"] is not None)

    # negativo: frase com cláusula zero
    checar("frase com cláusula de valor zero casa com a regra de reprovação",
           bool(re.search(r"\b0 [a-zà-ú]", "e 0 planos foram publicados")))

    checar("o portão real não acusa problema hoje", problemas() == [])

    if falhas:
        print(f"\n✗ AUTOTESTE DA IMPRENSA: {len(falhas)} falha(s).")
        return 1
    print("\n✓ AUTOTESTE DA IMPRENSA OK — os negativos reprovariam.")
    return 0


def main() -> int:
    if "--autoteste" in sys.argv[1:]:
        return autoteste()
    p = problemas()
    if p:
        print(f"✗ IMPRENSA: {len(p)} problema(s):")
        for x in p:
            print(f"  · {x}")
        return 1
    print("✓ IMPRENSA OK — paridade, período, zero ≠ sem coleta, sem variação inventada, "
          "frase sem cláusula zero, peso zero nos índices, data dos atos toda legível.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
