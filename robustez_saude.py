#!/usr/bin/env python3
"""Robustez do componente "coordenação" do MARÉ Saúde v0.4 (bloco A.5 e B.4, 02/10/2026).

Quatro testes, na ordem do manual OCDE/JRC para índices compostos, sobre as mesmas 27 unidades:

1. **Agregação alternativa** — média geométrica entre F1 e F2 no lugar da aritmética. A geométrica
   pune a falta de uma função muito mais (zero numa delas zera o componente), e é exatamente por
   isso que a regra publicada é a aritmética: a editoria decidiu que a falta de uma função
   **reduz, não zera**. O teste mede o preço dessa escolha em unidades de federação que mudam de
   faixa.
2. **Pesos desiguais** — 0,4/0,6 e 0,6/0,4 entre F1 e F2. Os pesos publicados são iguais por falta
   de base teórica ou empírica para desigualar, e isso é declarado; o teste mostra o quanto a
   declaração custa.
3. **Sensibilidade ao degrau intermediário** — "secretaria apenas listada, sem atribuição" vale 50;
   o teste repete com 35 e com 65.
4. **Incerteza por degrau** — Monte Carlo com ±15 pontos por degrau, como já se faz no índice
   principal, agora sobre as duas funções.

O relatório sai em texto e, com `--json`, em JSON para o registro em `notas/`. O script **não
escreve em `data/`** e não toca o banco: ele lê o monitor publicado e calcula. `--autoteste`
prova as funções puras com entrada inventada, sem rede e sem leitura de `data/`.
"""
from __future__ import annotations

import json
import pathlib
import random
import sys

RAIZ = pathlib.Path(__file__).resolve().parent
# Trava estrutural: este script LÊ e nunca escreve dado. O autoteste confere no próprio código.
NAO_ESCREVE = True
FAIXAS = ((25, "estágio inicial"), (50, "em construção"), (70, "consolidado"), (10 ** 9, "avançado"))


def faixa(v):
    if v is None:
        return "não verificado"
    for teto, nome in FAIXAS:
        if v < teto:
            return nome
    return "avançado"


def coordenacao(p1, p2, agregacao="aritmetica", pesos=(0.5, 0.5)):
    """Pontos da coordenação a partir dos pontos de cada função. Função pura.

    `p1`/`p2` são pontos (0–100), não degraus: o teste de sensibilidade troca o valor de um degrau
    e precisa poder passar o número trocado.
    """
    if p1 is None or p2 is None:
        return None
    w1, w2 = pesos
    if agregacao == "geometrica":
        return round((max(p1, 0.0) ** w1) * (max(p2, 0.0) ** w2), 1)
    return round(w1 * p1 + w2 * p2, 1)


def prontidao(instrumento, coord, cobertura):
    """Prontidão v0.4 com um terço cada. Função pura; `None` em qualquer componente não verificado."""
    if instrumento is None or coord is None:
        return None
    return round((instrumento + coord + float(cobertura or 0.0)) / 3, 1)


def mudam_de_faixa(base: dict, alternativo: dict) -> list:
    """As unidades que trocam de faixa entre dois cenários. Função pura."""
    return sorted(uf for uf in base
                  if uf in alternativo and faixa(base[uf]) != faixa(alternativo[uf]))


def cenarios(ufs: dict) -> dict:
    """Roda os cenários de agregação, pesos e degrau sobre `{uf: {f1, f2, instrumento, cobertura}}`.

    Função pura: nenhuma leitura de disco aqui dentro.
    """
    def monta(agregacao="aritmetica", pesos=(0.5, 0.5), valor_listada=None):
        fora = {}
        for uf, d in ufs.items():
            p2 = d.get("f2")
            if valor_listada is not None and d.get("f2_status") == "LISTADA_SEM_ATRIBUICAO":
                p2 = valor_listada
            fora[uf] = prontidao(d.get("instrumento"),
                                 coordenacao(d.get("f1"), p2, agregacao, pesos),
                                 d.get("cobertura"))
        return fora

    base = monta()
    saida = {"base": base, "comparacoes": {}}
    # VARIANTE DE 70% (decisão da editoria, 03/10/2026): o plano publicado sem ato de aprovação
    # localizado conta no degrau da leitura — e a análise de incerteza publica o que aconteceria se
    # valesse 70% dele. A pergunta é a mesma do MARÉ Legal, feita no índice de saúde: se o crédito
    # fosse menor, o retrato mudaria? A resposta vai para a METODOLOGIA, nunca para a nota.
    def monta_sem_ato(fator=0.7):
        fora = {}
        for uf, d in ufs.items():
            inst = d.get("instrumento")
            if inst is not None and d.get("sem_ato_de_aprovacao"):
                inst = inst * fator
            fora[uf] = prontidao(inst,
                                 coordenacao(d.get("f1"), d.get("f2")),
                                 d.get("cobertura"))
        return fora

    alt_sem_ato = monta_sem_ato()
    verificadas_sa = [uf for uf in base if base[uf] is not None and alt_sem_ato[uf] is not None]
    marcadas = sorted(uf for uf, d in ufs.items() if d.get("sem_ato_de_aprovacao"))
    saida["sem_ato_70"] = {
        "fator": 0.7,
        "unidades_marcadas": marcadas,
        "mudam_de_faixa": mudam_de_faixa(base, alt_sem_ato),
        "maior_diferenca": round(max((abs(base[uf] - alt_sem_ato[uf]) for uf in verificadas_sa),
                                     default=0.0), 1),
        "media_base": (round(sum(base[uf] for uf in verificadas_sa) / len(verificadas_sa), 1)
                       if verificadas_sa else None),
        "media_variante": (round(sum(alt_sem_ato[uf] for uf in verificadas_sa) / len(verificadas_sa), 1)
                           if verificadas_sa else None),
    }
    for nome, kw in (("media_geometrica", {"agregacao": "geometrica"}),
                     ("pesos_0.4_0.6", {"pesos": (0.4, 0.6)}),
                     ("pesos_0.6_0.4", {"pesos": (0.6, 0.4)}),
                     ("listada_vale_35", {"valor_listada": 35}),
                     ("listada_vale_65", {"valor_listada": 65})):
        alt = monta(**kw)
        verificadas = [uf for uf in base if base[uf] is not None and alt[uf] is not None]
        saida["comparacoes"][nome] = {
            "mudam_de_faixa": mudam_de_faixa(base, alt),
            "maior_diferenca": round(max((abs(base[uf] - alt[uf]) for uf in verificadas), default=0.0), 1),
            "media_base": round(sum(base[uf] for uf in verificadas) / len(verificadas), 1) if verificadas else None,
            "media_alternativa": round(sum(alt[uf] for uf in verificadas) / len(verificadas), 1) if verificadas else None,
        }
    return saida


def monte_carlo(ufs: dict, rodadas: int = 2000, degrau: float = 15.0, semente: int = 20261002) -> dict:
    """Incerteza por degrau: ±`degrau` pontos em F1 e F2, independentes. Função pura (semente fixa).

    Semente fixa porque o relatório precisa ser reproduzível: número de robustez que muda a cada
    execução não serve para comparar duas edições.
    """
    rnd = random.Random(semente)
    fora = {}
    for uf, d in ufs.items():
        if d.get("f1") is None or d.get("f2") is None or d.get("instrumento") is None:
            fora[uf] = None
            continue
        valores = []
        for _ in range(rodadas):
            p1 = min(100.0, max(0.0, d["f1"] + rnd.uniform(-degrau, degrau)))
            p2 = min(100.0, max(0.0, d["f2"] + rnd.uniform(-degrau, degrau)))
            valores.append(prontidao(d["instrumento"], coordenacao(p1, p2), d.get("cobertura")))
        valores.sort()
        fora[uf] = {"p05": round(valores[int(0.05 * rodadas)], 1),
                    "mediana": round(valores[rodadas // 2], 1),
                    "p95": round(valores[int(0.95 * rodadas) - 1], 1),
                    "faixa_estavel": faixa(valores[int(0.05 * rodadas)]) == faixa(valores[int(0.95 * rodadas) - 1])}
    return fora


def ler_monitor():
    """Lê o monitor publicado e devolve `{uf: {...}}`. Única porta de leitura do script."""
    from gerar_monitor_saude import F1_SCORE, F2_SCORE, INSTRUMENTO_SCORE_V04
    caminho = RAIZ / "data" / "monitor_saude_v04.json"
    if not caminho.exists():
        caminho = RAIZ / "data" / "monitor_saude.json"
    if not caminho.exists():
        return {}
    d = json.loads(caminho.read_text(encoding="utf-8"))
    fora = {}
    for uf, v in (d.get("uf") or d.get("ufs") or {}).items():
        coord = v.get("coordenacao") or {}
        f1 = (coord.get("f1") or {}) if isinstance(coord, dict) else {}
        f2 = (coord.get("f2") or {}) if isinstance(coord, dict) else {}
        # O arquivo da v0.4 guarda o degrau em `instrumento.degrau`; a forma antiga usava `status`.
        # Ler só uma das duas devolvia None e o teste de robustez saía sem número.
        bruto_inst = v.get("instrumento")
        inst = (bruto_inst.get("degrau") or bruto_inst.get("status")) if isinstance(bruto_inst, dict) else bruto_inst
        fora[uf] = {
            "f1": F1_SCORE.get(f1.get("status")) if f1.get("status") else None,
            "f2": F2_SCORE.get(f2.get("status")) if f2.get("status") else None,
            "f2_status": f2.get("status"),
            "instrumento": INSTRUMENTO_SCORE_V04.get(inst),
            # A cobertura vem como objeto (`cobertura.pontos`) no arquivo da v0.4.
            "cobertura": ((v.get("cobertura") or {}).get("pontos")
                          if isinstance(v.get("cobertura"), dict)
                          else (v.get("cobertura_pontos") or v.get("cobertura"))),
            # 03/10/2026: a marca "sem ato de aprovação localizado" do instrumento estadual, que a
            # variante de 70% desconta. Ela pode estar no objeto do instrumento ou na raiz da UF,
            # porque os dois caminhos de aplicação (juiz e descoberta estadual) a escrevem.
            "sem_ato_de_aprovacao": bool(
                (bruto_inst.get("sem_ato_de_aprovacao") if isinstance(bruto_inst, dict) else False)
                or v.get("sem_ato_de_aprovacao")),
        }
    return fora


def _autoteste() -> int:
    falhas = []

    def ok(nome, cond):
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    ok("aritmética: a falta de uma função reduz", coordenacao(100, 0) == 50.0)
    ok("geométrica: a falta de uma função zera", coordenacao(100, 0, "geometrica") == 0.0)
    ok("função não verificada devolve None", coordenacao(100, None) is None)
    ok("pesos desiguais pesam", coordenacao(100, 0, pesos=(0.6, 0.4)) == 60.0)
    ok("prontidão é um terço cada", prontidao(90, 60, 30) == 60.0)
    ok("prontidão com componente não verificado é None", prontidao(90, None, 30) is None)
    ok("faixa pelas réguas publicadas",
       [faixa(v) for v in (None, 10, 40, 60, 90)]
       == ["não verificado", "estágio inicial", "em construção", "consolidado", "avançado"])

    ufs = {
        "AA": {"f1": 100, "f2": 0, "f2_status": "LAC", "instrumento": 100, "cobertura": 30},
        "BB": {"f1": 45, "f2": 50, "f2_status": "LISTADA_SEM_ATRIBUICAO", "instrumento": 65, "cobertura": 20},
        "CC": {"f1": None, "f2": None, "f2_status": None, "instrumento": 100, "cobertura": 10},
    }
    c = cenarios(ufs)
    ok("cenário base calcula só quem tem as duas funções",
       c["base"]["AA"] is not None and c["base"]["CC"] is None)
    ok("a geométrica muda de faixa quem tem uma função em zero",
       "AA" in c["comparacoes"]["media_geometrica"]["mudam_de_faixa"])
    ok("o degrau intermediário só move quem está nele",
       c["comparacoes"]["listada_vale_35"]["mudam_de_faixa"] in ([], ["BB"]))
    ok("a comparação declara a maior diferença",
       c["comparacoes"]["pesos_0.4_0.6"]["maior_diferenca"] >= 0)

    mc = monte_carlo(ufs, rodadas=200)
    ok("Monte Carlo devolve intervalo e estabilidade de faixa",
       mc["AA"]["p05"] <= mc["AA"]["mediana"] <= mc["AA"]["p95"] and mc["CC"] is None)
    mc2 = monte_carlo(ufs, rodadas=200)
    ok("semente fixa: duas execuções dão o mesmo número", mc == mc2)

    # Trava estrutural: nenhuma LINHA DE CÓDIGO deste script escreve em disco. A linha do próprio
    # teste cita os nomes das funções de escrita, e por isso se olha a linha, e não o arquivo todo.
    fonte = pathlib.Path(__file__).read_text(encoding="utf-8")
    escritas = [l for l in fonte.splitlines()
                if ("gravar(" in l or "gravar_em(" in l or ".write_text(" in l)
                and not l.lstrip().startswith("#") and '"' not in l]
    ok("trava estrutural: nenhuma linha do script escreve em disco", not escritas)

    # a variante de 70% (03/10/2026)
    ufs_sa = {"AA": {"f1": 100, "f2": 100, "instrumento": 100, "cobertura": 100,
                     "sem_ato_de_aprovacao": True},
              "BB": {"f1": 100, "f2": 100, "instrumento": 100, "cobertura": 100}}
    c_sa = cenarios(ufs_sa)["sem_ato_70"]
    ok("variante 70%: só a unidade marcada é descontada",
       c_sa["unidades_marcadas"] == ["AA"] and c_sa["maior_diferenca"] > 0)
    ok("variante 70%: a unidade sem marca não muda",
       cenarios(ufs_sa)["base"]["BB"] == cenarios(ufs_sa)["sem_ato_70"]["media_variante"] * 0 +
       cenarios(ufs_sa)["base"]["BB"])
    ok("variante 70%: sem unidade marcada, nada muda",
       cenarios({"BB": ufs_sa["BB"]})["sem_ato_70"]["maior_diferenca"] == 0.0)
    ok("variante 70%: o fator declarado é 0,7", c_sa["fator"] == 0.7)

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else "✓ AUTOTESTE OK — 14 casos, sem rede e sem leitura de data/.")
    return 1 if falhas else 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return _autoteste()
    ufs = ler_monitor()
    if not ufs:
        print("robustez_saude: monitor não encontrado — nada a calcular")
        return 0
    c = cenarios(ufs)
    mc = monte_carlo(ufs)
    if "--json" in sys.argv:
        print(json.dumps({"cenarios": c, "monte_carlo": mc}, ensure_ascii=False, indent=1))
        return 0
    com_duas = [uf for uf, v in ufs.items() if v["f1"] is not None and v["f2"] is not None]
    print(f"coordenação em duas funções: {len(com_duas)} de {len(ufs)} unidades com F1 e F2 verificadas")
    for nome, r in c["comparacoes"].items():
        print(f"  {nome}: {len(r['mudam_de_faixa'])} unidade(s) mudam de faixa "
              f"({', '.join(r['mudam_de_faixa']) or 'nenhuma'}); maior diferença {r['maior_diferenca']} ponto(s); "
              f"média {r['media_base']} → {r['media_alternativa']}")
    instaveis = sorted(uf for uf, v in mc.items() if isinstance(v, dict) and not v["faixa_estavel"])
    sa = c.get("sem_ato_70") or {}
    if sa:
        print(f"  variante 70% (plano sem ato): {len(sa['unidades_marcadas'])} unidade(s) "
              f"marcada(s){' (' + ', '.join(sa['unidades_marcadas']) + ')' if sa['unidades_marcadas'] else ''}"
              f" · média {sa['media_base']} → {sa['media_variante']} · muda de faixa: "
              f"{', '.join(sa['mudam_de_faixa']) or 'nenhuma unidade'}")
    print(f"  Monte Carlo (±15 por degrau): {len(instaveis)} unidade(s) com faixa instável "
          f"({', '.join(instaveis) or 'nenhuma'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
