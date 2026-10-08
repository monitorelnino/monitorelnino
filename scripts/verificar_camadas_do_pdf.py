#!/usr/bin/env python3
"""Portão: a análise de sensibilidade e o PDF público usam a conta do MOTOR.

Item 1.14 do HANDOVER_CORRECAO_DEFINITIVA_08-10-2026 (achado A3-05). O PDF público "Documentação
do Índice" é regenerado a cada rodada e selado no manifesto. Ele saía com:

- a tabela "transparência de camadas" dizendo, por exemplo, DF 100 % documentado, quando o motor
  tem 38 % documentado e 62 % declarado — a cópia da conta em `analise_sensibilidade.py` ignorava
  a camada declarada nacional (MUNIC/ICM, ativa desde 21/09) e aplicava 0,3 ao plano desatualizado
  onde o motor aplica 0,5;
- a cobertura recalculada escrita na coluna 1 do vetor de componentes, que desde a v3.1 é a
  ESTRUTURA, não a cobertura;
- "Antecipação" como terceiro componente e "plano_antigo 0,6" na tabela de crédito, duas coisas
  extintas (a régua de antecipação em 30/09/2026, o 0,6 em 24/09/2026).

O que este portão cobra:

1. a cobertura que a análise calcula é IGUAL, UF por UF, à que o índice publica;
2. a soma das três camadas de cada UF reproduz a cobertura publicada;
3. nem o gerador do PDF nem a análise trazem número de peso escrito à mão nem componente extinto.

`--autoteste` é puro: não lê `data/`, não escreve nada.
"""
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
PROIBIDOS_NO_PDF = (
    (re.compile(r"plano_antigo 0,6"), "crédito de plano_antigo extinto em 24/09/2026 (hoje 1,0)"),
    (re.compile(r'"Antecipação"'), "antecipação como componente, extinta em 30/09/2026 (v3.1)"),
    (re.compile(r"Valores de antecipação em uso"), "régua de antecipação como componente"),
    (re.compile(r"explica 55% da variância"), "número de variância escrito à mão"),
    (re.compile(r"com 44% da variância"), "número de contribuição escrito à mão"),
    (re.compile(r"\+0,66"), "correlação escrita à mão"),
)
COLUNA_ERRADA = re.compile(r"Xv\[i,\s*1\]\s*=\s*round\(cobertura")


def sem_comentarios(fonte: str) -> str:
    """O código sem as linhas de comentário.

    O comentário que EXPLICA o defeito corrigido cita o defeito — e o portão o acusaria. Ele olha
    o que pode virar texto do PDF, não o histórico escrito ao lado.
    """
    return chr(10).join(l for l in fonte.split(chr(10))
                        if not l.strip().startswith("#"))


def problemas_de_texto(pdf_py: str, analise_py: str) -> list:
    fora = []
    pdf_py = sem_comentarios(pdf_py)
    analise_py = sem_comentarios(analise_py)
    for regex, por_que in PROIBIDOS_NO_PDF:
        if regex.search(pdf_py):
            fora.append(f"gerar_pdf_indice.py traz {por_que}")
    if COLUNA_ERRADA.search(analise_py):
        fora.append("analise_sensibilidade.py escreve a cobertura na coluna 1, que na v3.1 é a "
                    "estrutura (A3-05)")
    if "rm.cobertura_de_uf" not in analise_py:
        fora.append("analise_sensibilidade.py não usa `recalcular_mare.cobertura_de_uf` — a conta "
                    "da cobertura tem um dono só")
    return fora


def problemas_de_numero(cobertura_da_analise: dict, cobertura_publicada: dict,
                        camadas: dict) -> list:
    fora = []
    for uf, valor in sorted(cobertura_da_analise.items()):
        publicado = cobertura_publicada.get(uf)
        if publicado is None:
            fora.append(f"{uf}: a análise calcula cobertura para uma UF que o índice não tem")
            continue
        if abs(valor - publicado) > 0.05:
            fora.append(f"{uf}: a análise calcula cobertura {valor:.1f} e o índice publica "
                        f"{publicado:.1f}")
    for uf, (doc, agr, dec) in sorted(camadas.items()):
        soma = doc + agr + dec
        publicado = cobertura_publicada.get(uf)
        if publicado is not None and abs(soma - publicado) > 0.15:
            fora.append(f"{uf}: as três camadas somam {soma:.1f} e a cobertura publicada é "
                        f"{publicado:.1f}")
    return fora


def autoteste() -> int:
    casos = [
        ("texto limpo passa", ("CREDITO_EM_USO", "rm.cobertura_de_uf(uf, c, w)"), 0),
        ("crédito à mão reprova", ("plano 1,0 · plano_antigo 0,6 ·", "rm.cobertura_de_uf()"), 1),
        ("antecipação como componente reprova",
         ('["Antecipação", "Tempestividade"]', "rm.cobertura_de_uf()"), 1),
        ("coluna 1 reprova",
         ("CREDITO_EM_USO", "Xv[i, 1] = round(cobertura(u))\nrm.cobertura_de_uf()"), 1),
        ("análise sem a porta do motor reprova", ("CREDITO_EM_USO", "def cobertura(uf): ..."), 1),
    ]
    falhas = 0
    for nome, (pdf, analise), esperado in casos:
        achados = problemas_de_texto(pdf, analise)
        ok = len(achados) == esperado
        print(f"  {'ok ' if ok else 'FALHA'} {nome}: {len(achados)} problema(s)")
        if not ok:
            falhas += 1
            for a in achados:
                print(f"        {a}")
    numericos = [
        ("cobertura igual à publicada passa", {"SE": 14.5}, {"SE": 14.5}, {"SE": (10.0, 0.0, 4.5)},
         0),
        ("cobertura divergente reprova", {"DF": 80.0}, {"DF": 30.0}, {}, 1),
        ("camadas que não somam a cobertura reprovam", {}, {"PR": 29.4},
         {"PR": (13.0, 0.0, 3.0)}, 1),
    ]
    for nome, a, b, c, esperado in numericos:
        achados = problemas_de_numero(a, b, c)
        ok = len(achados) == esperado
        print(f"  {'ok ' if ok else 'FALHA'} {nome}: {len(achados)} problema(s)")
        if not ok:
            falhas += 1
    total = len(casos) + len(numericos)
    print(f"autoteste: {total - falhas}/{total}")
    return 1 if falhas else 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    sys.path.insert(0, str(RAIZ))
    import json  # noqa: PLC0415
    import analise_sensibilidade as asens  # noqa: PLC0415

    fora = problemas_de_texto((RAIZ / "gerar_pdf_indice.py").read_text(encoding="utf-8"),
                              (RAIZ / "analise_sensibilidade.py").read_text(encoding="utf-8"))
    R = asens.rodar() if hasattr(asens, "rodar") else asens.analisar()
    indice = json.loads((RAIZ / "data" / "indice.json").read_text(encoding="utf-8"))
    publicada = {uf: v["cobertura_pop"] for uf, v in indice.items()}
    coberturas = R.get("cobertura_por_uf") or {}
    camadas = R.get("camadas_absolutas") or {}
    fora += problemas_de_numero(coberturas, publicada, camadas)
    if fora:
        print(f"VERMELHO: {len(fora)} problema(s) entre a análise, o PDF e o motor")
        for f in fora[:40]:
            print(f"  · {f}")
        return 1
    print(f"ok: a análise e o PDF usam a conta do motor; {len(coberturas)} UFs conferidas e "
          f"{len(camadas)} decomposições somam a cobertura publicada")
    return 0


if __name__ == "__main__":
    sys.exit(main())
