#!/usr/bin/env python3
"""Portão — cadência de publicação semanal declarada em um lugar só, e coerente
com o texto público.

Criado em 20/09/2026, quando a editoria moveu a publicação semanal de segunda-feira
para sábado. O dia da rodada é compromisso declarado ao leitor (obrigado.html diz a
quem envia documento quando eles entram no ar; pesquisadores.html declara a cadência
do banco), então uma divergência entre o código e o texto público não é detalhe
interno: é o site prometendo uma coisa e fazendo outra.

Verifica três coisas:
  1. `atualizar.py` decide a cadência pela constante DIA_PUBLICACAO, nunca por um
     literal solto — se alguém voltar a escrever `dia_semana != 0` o portão cai.
  2. DIA_PUBLICACAO e NOME_DIA_PUBLICACAO concordam entre si.
  3. O texto público (obrigado.html, pesquisadores.html) nomeia o MESMO dia que o
     código executa.

Uso: python3 scripts/testar_cadencia_publicacao.py
"""
import ast
import datetime
import pathlib
import re
import sys
from zoneinfo import ZoneInfo

RAIZ = pathlib.Path(__file__).parent.parent

NOMES_POR_INDICE = {
    0: "segunda", 1: "terça", 2: "quarta", 3: "quinta",
    4: "sexta", 5: "sábado", 6: "domingo",
}

# Onde o dia aparece para o leitor. Cada par: arquivo e o trecho que cita a cadência.
TEXTOS_PUBLICOS = [
    ("obrigado.html", r"entra na atualização seguinte do mapa e do índice — normalmente (?:na|no) (\w+)"),
    ("pesquisadores.html", r"Atualização automática semanal \((\w+)s?,"),
]

falhas = []


def _constantes():
    """Lê DIA_PUBLICACAO e NOME_DIA_PUBLICACAO de atualizar.py por AST (sem importar,
    para não disparar o pipeline)."""
    fonte = (RAIZ / "atualizar.py").read_text(encoding="utf-8")
    arvore = ast.parse(fonte)
    achados = {}
    for no in arvore.body:
        if isinstance(no, ast.Assign):
            for alvo in no.targets:
                if isinstance(alvo, ast.Name) and alvo.id in ("DIA_PUBLICACAO", "NOME_DIA_PUBLICACAO"):
                    achados[alvo.id] = ast.literal_eval(no.value)
    return achados, fonte


def main():
    achados, fonte = _constantes()

    # 1. As constantes existem no nível do módulo.
    for nome in ("DIA_PUBLICACAO", "NOME_DIA_PUBLICACAO"):
        if nome not in achados:
            falhas.append(f"{nome} não encontrada no nível do módulo em atualizar.py")
    if falhas:
        for f in falhas:
            print(f"✗ {f}")
        return 1

    dia = achados["DIA_PUBLICACAO"]
    nome_dia = achados["NOME_DIA_PUBLICACAO"]

    if not isinstance(dia, int) or not 0 <= dia <= 6:
        falhas.append(f"DIA_PUBLICACAO deve ser inteiro de 0 a 6 (weekday); veio {dia!r}")

    # 2. O portão de cadência usa a constante, não um literal.
    if re.search(r"dia_semana\s*!=\s*\d", fonte):
        falhas.append("o portão de cadência compara dia_semana com um literal — "
                      "deve usar DIA_PUBLICACAO, senão o dia passa a viver em dois lugares")
    if not re.search(r"dia_semana\s*!=\s*DIA_PUBLICACAO", fonte):
        falhas.append("não encontrei `dia_semana != DIA_PUBLICACAO` em atualizar.py")

    # 3. Nome e índice concordam.
    esperado = NOMES_POR_INDICE.get(dia)
    if esperado and esperado not in nome_dia.lower():
        falhas.append(f"DIA_PUBLICACAO={dia} é {esperado}, mas NOME_DIA_PUBLICACAO diz {nome_dia!r}")

    # 4. O texto público nomeia o mesmo dia.
    for arquivo, padrao in TEXTOS_PUBLICOS:
        caminho = RAIZ / arquivo
        if not caminho.exists():
            falhas.append(f"{arquivo} não encontrado — o portão precisa saber onde o dia é prometido")
            continue
        m = re.search(padrao, caminho.read_text(encoding="utf-8"))
        if not m:
            falhas.append(f"{arquivo}: não localizei a frase de cadência (o padrão do portão "
                          f"precisa acompanhar a reescrita do texto)")
            continue
        dito = m.group(1).lower().rstrip("s")
        if esperado and not dito.startswith(esperado[:5]):
            falhas.append(f"{arquivo} promete '{dito}' ao leitor, mas o código publica em "
                          f"'{esperado}' — texto público divergente do comportamento real")

    # 5. A cadência é medida no fuso da redação, nunca no do runner (UTC).
    if "hoje_editorial()" not in fonte:
        falhas.append("o portão de cadência não usa hoje_editorial() — medir o dia em UTC faz a "
                      "rodada noturna de sábado cair na sexta para o leitor brasileiro")
    if re.search(r"dia_semana\s*=\s*datetime\.date\.today\(\)", fonte):
        falhas.append("dia_semana ainda vem de datetime.date.today() (UTC no runner) — use hoje_editorial()")

    # 5b. Nenhuma data do pipeline pode vir de UTC: a rodada de sábado 22h40 começa
    #     no domingo em UTC e cruza a meia-noite, então date.today() erra dia em dois
    #     lugares — a data da edição (atualizado_em/corte) e o lote da varredura.
    for linha_n, linha in enumerate(fonte.splitlines(), 1):
        codigo = linha.split("#", 1)[0]
        if "datetime.date.today()" in codigo:
            falhas.append(f"atualizar.py:{linha_n} usa datetime.date.today() (UTC no runner) "
                          f"fora de comentário — use hoje_editorial(): {codigo.strip()[:70]}")

    # 6. O cron semanal do workflow cai no dia prometido, convertido para o fuso da redação.
    wf = RAIZ / ".github" / "workflows" / "atualizar.yml"
    if not wf.exists():
        falhas.append("workflow atualizar.yml não encontrado")
    else:
        crons = re.findall(r'cron:\s*"([^"]+)"', wf.read_text(encoding="utf-8"))
        semanais = [c for c in crons if c.split()[-1] != "*"]
        if not semanais:
            falhas.append("nenhum cron semanal (campo de dia da semana fixo) em atualizar.yml")
        for c in semanais:
            minuto, hora, _, _, dia_cron = c.split()
            # cron: 0 = domingo … 6 = sábado. Converter uma ocorrência real para o fuso editorial.
            base = datetime.date(2026, 9, 27)  # um domingo; cron: 0 = domingo … 6 = sábado
            alvo = base + datetime.timedelta(days=int(dia_cron))
            em_utc = datetime.datetime(alvo.year, alvo.month, alvo.day,
                                       int(hora), int(minuto), tzinfo=ZoneInfo("UTC"))
            local = em_utc.astimezone(ZoneInfo("America/Sao_Paulo"))
            if local.weekday() != dia:
                falhas.append(
                    f"cron semanal '{c}' cai em {NOMES_POR_INDICE[local.weekday()]} "
                    f"{local:%H:%M} no fuso da redação, mas DIA_PUBLICACAO={dia} "
                    f"({esperado}) — o portão encerraria a rodada sem publicar")

    if falhas:
        for f in falhas:
            print(f"✗ {f}")
        return 1

    print(f"✓ cadência coerente: DIA_PUBLICACAO={dia} ({nome_dia}) medido no fuso da redação; "
          f"portão usa a constante; cron semanal cai no dia certo em Brasília; "
          f"obrigado.html e pesquisadores.html prometem o mesmo dia ao leitor")
    return 0


if __name__ == "__main__":
    sys.exit(main())
