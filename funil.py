#!/usr/bin/env python3
"""
funil.py
========
Contagem por etapa do funil de coleta, uma linha por rodada.

Handover `HANDOVER_auditoria_funil_de_coleta_27-09-2026.md`, item B, e
`HANDOVER_juiz_automatico_e_busca_web_27-09-2026.md`, PR 1 item 3 e PR 3.

A pergunta da editoria — "os coletores estão de fato encontrando os planos?" — não se
responde lendo o código. Responde-se contando o que cada etapa recebeu e o que cada etapa
devolveu, a cada rodada, num arquivo que qualquer pessoa abre sem abrir o código.

Formato de `data/funil/<AAAA-MM-DD>.json`:

    {"data": "2026-09-27", "formato_versao": 1,
     "etapas": {"busca_web": {"consultas": 60, "com_resultado_bruto": 41, ...}},
     "atualizado_em": "2026-09-27T21:10:00"}

Cada etapa acumula dentro da rodada: duas chamadas de `registrar("busca_web", consultas=30)`
somam 60. Isso é o que permite que a etapa seja contada por lote, por UF ou por coletor, e o
total do dia continue correto — a rodada completa chama o mesmo coletor várias vezes.

Contagem não é prova: este arquivo mede o funil, nunca decide categoria nem pontua.
"""
import datetime
import json
import pathlib

from coletores_base import DATA, gravar_em, hoje_editorial

FUNIL = DATA / "funil"
FORMATO_VERSAO = 1


def caminho_do_dia(dia=None) -> pathlib.Path:
    """O arquivo da rodada. `dia` aceita date ou string ISO; o padrão é o corte editorial."""
    if dia is None:
        dia = hoje_editorial()
    if isinstance(dia, (datetime.date, datetime.datetime)):
        dia = dia.strftime("%Y-%m-%d")
    return FUNIL / f"{dia}.json"


def ler_do_dia(dia=None) -> dict:
    p = caminho_do_dia(dia)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def registrar(etapa: str, dia=None, **contagens) -> dict:
    """Soma `contagens` na `etapa` do arquivo da rodada e devolve o arquivo inteiro.

    Escreve pela porta atômica (`gravar_em`, §229). Valor não inteiro é recusado: o funil
    conta coisas, e um float aqui seria uma taxa disfarçada de contagem."""
    for chave, valor in contagens.items():
        if not isinstance(valor, int) or isinstance(valor, bool):
            raise TypeError(f"funil: {etapa}.{chave} precisa ser int, veio {type(valor).__name__}")
    atual = ler_do_dia(dia)
    dia_iso = caminho_do_dia(dia).stem
    doc = {"data": dia_iso, "formato_versao": FORMATO_VERSAO, "etapas": atual.get("etapas") or {}}
    alvo = doc["etapas"].setdefault(etapa, {})
    for chave, valor in contagens.items():
        alvo[chave] = int(alvo.get(chave, 0)) + valor
    doc["atualizado_em"] = datetime.datetime.now().replace(microsecond=0).isoformat()
    FUNIL.mkdir(parents=True, exist_ok=True)
    gravar_em(caminho_do_dia(dia), doc)
    return doc


def autoteste() -> int:
    """Autoteste offline: não escreve em data/ — usa um diretório temporário."""
    import tempfile
    global FUNIL
    falhas = []
    with tempfile.TemporaryDirectory() as tmp:
        FUNIL = pathlib.Path(tmp) / "funil"

        registrar("busca_web", dia="2026-09-27", consultas=30, pistas=2)
        registrar("busca_web", dia="2026-09-27", consultas=30, motor_sem_resposta=5)
        d = ler_do_dia("2026-09-27")
        if d["etapas"]["busca_web"] != {"consultas": 60, "pistas": 2, "motor_sem_resposta": 5}:
            falhas.append(f"acumulação por etapa: {d['etapas']['busca_web']}")
        if d["data"] != "2026-09-27" or d["formato_versao"] != FORMATO_VERSAO:
            falhas.append("cabeçalho do arquivo do dia")

        registrar("juiz", dia="2026-09-27", promovidas=1)
        if set(ler_do_dia("2026-09-27")["etapas"]) != {"busca_web", "juiz"}:
            falhas.append("etapas convivem no mesmo dia")
        if ler_do_dia("2026-09-28") != {}:
            falhas.append("dia sem arquivo devolve vazio")

        try:
            registrar("busca_web", dia="2026-09-27", taxa=0.5)
            falhas.append("float aceito como contagem")
        except TypeError:
            pass
        try:
            registrar("busca_web", dia="2026-09-27", ok=True)
            falhas.append("bool aceito como contagem")
        except TypeError:
            pass

    if falhas:
        print("✗ FUNIL")
        for f in falhas:
            print(f"   - {f}")
        return 1
    print("✓ funil.py OK — acumula por etapa, isola por dia, recusa contagem que não é inteiro.")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(autoteste() if "--autoteste" in sys.argv else 0)
