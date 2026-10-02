#!/usr/bin/env python3
"""Troca o MARÉ Saúde da v0.3 para a v0.4, sozinho, quando a condição se cumprir.

A editoria autorizou a troca em 01/10/2026 e fixou UMA condição: as 27 UFs verificadas **no plano
e na coordenação**. Enquanto ela não se cumpre, este script não muda nada — e é por isso que ele
pode rodar em toda publicação sem pedir licença a ninguém. Quem mede a condição é
`scripts/fechar_saude.py`, que grava `data/saude_troca_v04.json`; aqui só se lê o pedido.

O QUE A TROCA FAZ, E O QUE ELA NÃO FAZ
--------------------------------------
Faz: substitui, em `data/monitor_saude.json`, a prontidão e a faixa de cada UF pelas da v0.4,
carimba `versao: "0.4"`, guarda a comparação (quantas UFs mudam de faixa e quanto a média muda) e
**emite a errata pública** em `data/congelamento_defeso.json`, encadeada pelo hash como as
anteriores.

Não faz: não recalcula nada por conta própria (quem calcula é `gerar_monitor_saude_v04.py`), não
mexe no MARÉ Legal, não toca texto de página — a página lê o mesmo arquivo de sempre e passa a
mostrar o número novo porque o arquivo mudou, não porque alguém editou HTML.

A ERRATA DIZ DE ONDE VEM A QUEDA
--------------------------------
A editoria pediu isso explicitamente: a errata declara que a diferença vem dos estados que passaram
a entrar com zero após verificação completa, e não de uma mudança de régua aplicada ao mesmo
conjunto. Sem essa frase, o leitor atribuiria a queda a piora dos estados.

USO
    python3 trocar_para_v04.py                 # lê o pedido; sem condição cumprida, não faz nada
    python3 trocar_para_v04.py --ensaio        # prova o caminho da troca sobre dado fabricado
    python3 trocar_para_v04.py --autoteste
"""
import datetime
import hashlib
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent
DATA = RAIZ / "data"
PEDIDO = DATA / "saude_troca_v04.json"
MONITOR = DATA / "monitor_saude.json"
V04 = DATA / "monitor_saude_v04.json"
CONGELAMENTO = DATA / "congelamento_defeso.json"

FAIXAS = ("estágio inicial", "em construção", "consolidado", "avançado")


def ler(p, padrao=None):
    try:
        return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return padrao


def comparar(monitor: dict, v04: dict) -> dict:
    """O que a troca muda, medido. Função pura.

    Devolve as UFs que mudam de faixa (com a faixa velha e a nova), a média antes e depois, e a
    diferença. É isto que a errata publica — e é por isso que ele não pode ser calculado na hora de
    escrever o texto: o texto cita estes números."""
    velhos, novos, mudam = {}, {}, []
    for uf, v in (v04.get("uf") or {}).items():
        antes = ((monitor.get("ufs") or {}).get(uf) or {})
        a_val, n_val = antes.get("prontidao"), v.get("prontidao")
        a_fx, n_fx = antes.get("faixa"), v.get("faixa")
        if a_val is not None:
            velhos[uf] = a_val
        if n_val is not None:
            novos[uf] = n_val
        if a_fx and n_fx and a_fx != n_fx:
            mudam.append({"uf": uf, "de": a_fx, "para": n_fx})
    media = lambda d: round(sum(d.values()) / len(d), 1) if d else None  # noqa: E731
    m_antes, m_depois = media(velhos), media(novos)
    return {
        "ufs_que_mudam_de_faixa": sorted(mudam, key=lambda x: x["uf"]),
        "media_v03": m_antes,
        "media_v04": m_depois,
        "variacao_da_media": (None if m_antes is None or m_depois is None
                              else round(m_depois - m_antes, 1)),
        "ufs_com_numero_v03": len(velhos),
        "ufs_com_numero_v04": len(novos),
    }


def aplicar_v04(monitor: dict, v04: dict) -> dict:
    """O `monitor_saude.json` com a prontidão e a faixa da v0.4. Função pura.

    Só os campos que a v0.4 redefine são tocados; instrumento, cobertura e antecipação continuam
    como o gerador da rodada os escreveu. Substituir o arquivo inteiro apagaria o que a v0.4 não
    calcula."""
    saida = json.loads(json.dumps(monitor))  # cópia profunda, sem efeito no original
    for uf, v in (v04.get("uf") or {}).items():
        alvo = (saida.setdefault("ufs", {}).setdefault(uf, {}))
        alvo["prontidao"] = v.get("prontidao")
        alvo["faixa"] = v.get("faixa")
        alvo["verificado"] = v.get("prontidao") is not None
        if v.get("coordenacao"):
            alvo["coordenacao"] = v["coordenacao"]
        if v.get("sem_numero_porque"):
            alvo["sem_numero_porque"] = v["sem_numero_porque"]
    saida["versao"] = "0.4"
    com_numero = [v.get("prontidao") for v in saida["ufs"].values() if v.get("prontidao") is not None]
    resumo = saida.setdefault("resumo", {})
    resumo["verificadas"] = len(com_numero)
    resumo["nao_verificadas"] = len(saida["ufs"]) - len(com_numero)
    resumo["media_das_verificadas"] = (round(sum(com_numero) / len(com_numero), 1)
                                       if com_numero else None)
    return saida


def texto_da_errata(comp: dict, hoje: datetime.date) -> dict:
    """A errata pública da troca. Função pura.

    A frase sobre a origem da queda é obrigatória: foi pedido expresso da editoria em 01/10/2026,
    e sem ela a variação da média seria lida como piora dos estados."""
    mudam = comp["ufs_que_mudam_de_faixa"]
    quais = ("; ".join(f"{m['uf']}: {m['de']} → {m['para']}" for m in mudam)
             if mudam else "nenhuma UF muda de faixa")
    return {
        "codigo": "C30",
        "data": hoje.isoformat(),
        "classe": ("troca de VERSÃO do índice MARÉ Saúde (v0.3 → v0.4): pesos e componentes "
                   "mudaram, com autorização da editoria de 01/10/2026"),
        "o_que_mudou":
            (f"O MARÉ Saúde passa a ser calculado pela v0.4, em três terços — instrumento, "
             f"coordenação e cobertura —, com o tempo fora da nota. A média das UFs com número vai "
             f"de {comp['media_v03']} para {comp['media_v04']} "
             f"({comp['variacao_da_media']:+}). Mudam de faixa: {quais}. "
             f"A diferença vem, sobretudo, dos estados que passaram a entrar com zero depois de "
             f"verificação completa — e não de piora do que já estava medido: a régua nova não "
             f"rebaixa quem tinha documento lido, ela deixa de premiar o que não foi verificado."),
        "onde": "data/monitor_saude.json, saude.html, imprensa.html",
    }


def encadear(congelamento: dict, errata: dict) -> dict:
    """A errata no fim da corrente, com `hash_anterior` e `hash_novo`. Função pura."""
    saida = json.loads(json.dumps(congelamento))
    erratas = saida.setdefault("erratas", [])
    anterior = erratas[-1].get("hash_novo") if erratas else saida.get("hash_original_05_09")
    corpo = json.dumps(errata, ensure_ascii=False, sort_keys=True).encode("utf-8")
    novo = hashlib.sha256((str(anterior or "") + corpo.decode("utf-8")).encode("utf-8")).hexdigest()
    erratas.append({**errata, "hash_anterior": anterior, "hash_novo": novo})
    return saida


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    pedido = ler(PEDIDO, {}) or {}
    monitor, v04 = ler(MONITOR, {}) or {}, ler(V04, {}) or {}
    ensaio = "--ensaio" in sys.argv
    if not pedido.get("trocar") and not ensaio:
        print(f"MARÉ Saúde segue na v{monitor.get('versao', '0.3')}: a condição das 27 UFs "
              f"verificadas no plano e na coordenação ainda não se cumpriu "
              f"({pedido.get('com_plano', '—')} com plano, "
              f"{pedido.get('com_coordenacao', '—')} com coordenação). Nada foi alterado.")
        return 0
    comp = comparar(monitor, v04)
    print(f"Troca v0.3 → v0.4 · média {comp['media_v03']} → {comp['media_v04']} "
          f"({comp['variacao_da_media']:+}) · {len(comp['ufs_que_mudam_de_faixa'])} UF(s) mudam de "
          f"faixa")
    if ensaio:
        print("(ensaio: nada foi gravado)")
        return 0
    sys.path.insert(0, str(RAIZ))
    from coletores_base import gravar_em  # noqa: PLC0415 — §229
    novo_monitor = aplicar_v04(monitor, v04)
    novo_monitor["comparacao_da_troca"] = comp
    gravar_em(MONITOR, novo_monitor)
    gravar_em(CONGELAMENTO, encadear(ler(CONGELAMENTO, {}) or {},
                                     texto_da_errata(comp, datetime.date.today())))
    print("→ data/monitor_saude.json na v0.4 e errata C30 publicada.")
    return 0


def autoteste() -> int:
    falhas = []

    def checar(nome, cond):
        print(("  OK   " if cond else "  FALHA ") + nome)
        if not cond:
            falhas.append(nome)

    monitor = {"versao": "0.3", "ufs": {
        "AC": {"verificado": True, "prontidao": 30.0, "faixa": "em construção",
               "instrumento": {"status": "VIG"}, "cobertura": {"pontos": 10}},
        "AL": {"verificado": False, "prontidao": None, "faixa": "não verificado"},
    }, "resumo": {"verificadas": 1}}
    v04 = {"uf": {
        "AC": {"prontidao": 20.0, "faixa": "estágio inicial",
               "coordenacao": {"degrau": "PERMANENTE", "doc": "ato"}},
        "AL": {"prontidao": 40.0, "faixa": "em construção", "coordenacao": {"degrau": "NAO"}},
    }}
    comp = comparar(monitor, v04)
    checar("a comparação mede média antes e depois",
           comp["media_v03"] == 30.0 and comp["media_v04"] == 30.0)
    # AL entra na lista também, e deve: sair de "não verificado" para uma faixa é mudança que a
    # errata precisa nomear — foi o que a primeira versão deste caso deixou de fora.
    checar("a comparação lista quem muda de faixa, inclusive quem sai de 'não verificado'",
           comp["ufs_que_mudam_de_faixa"] == [
               {"uf": "AC", "de": "em construção", "para": "estágio inicial"},
               {"uf": "AL", "de": "não verificado", "para": "em construção"}])
    checar("UF sem número na v0.3 não entra na média velha", comp["ufs_com_numero_v03"] == 1)

    novo = aplicar_v04(monitor, v04)
    checar("a troca escreve prontidão e faixa da v0.4",
           novo["ufs"]["AC"]["prontidao"] == 20.0
           and novo["ufs"]["AC"]["faixa"] == "estágio inicial")
    checar("a troca carimba a versão", novo["versao"] == "0.4")
    checar("a troca NÃO apaga o que a v0.4 não calcula",
           novo["ufs"]["AC"]["instrumento"] == {"status": "VIG"}
           and novo["ufs"]["AC"]["cobertura"] == {"pontos": 10})
    checar("a troca traz a coordenação para o arquivo da página",
           novo["ufs"]["AC"]["coordenacao"]["doc"] == "ato")
    checar("o resumo é recontado do próprio arquivo",
           novo["resumo"]["verificadas"] == 2 and novo["resumo"]["media_das_verificadas"] == 30.0)
    checar("a função é pura: o arquivo original não muda",
           monitor["versao"] == "0.3" and monitor["ufs"]["AC"]["prontidao"] == 30.0)

    errata = texto_da_errata(comp, datetime.date(2026, 10, 2))
    checar("a errata diz de onde vem a diferença (pedido da editoria)",
           "passaram a entrar com zero" in errata["o_que_mudou"])
    checar("a errata cita as duas médias e a variação",
           "30.0" in errata["o_que_mudou"] and "+0.0" in errata["o_que_mudou"])
    checar("a errata nomeia quem muda de faixa", "AC: em construção" in errata["o_que_mudou"])
    checar("a errata declara que é troca de versão", "v0.3 → v0.4" in errata["classe"])

    corrente = encadear({"hash_original_05_09": "zero"}, errata)
    checar("a errata entra encadeada pelo hash",
           corrente["erratas"][-1]["hash_anterior"] == "zero"
           and len(corrente["erratas"][-1]["hash_novo"]) == 64)
    segunda = encadear(corrente, {**errata, "codigo": "C31"})
    checar("a corrente continua da errata anterior",
           segunda["erratas"][-1]["hash_anterior"] == corrente["erratas"][-1]["hash_novo"])

    # A TRAVA: sem pedido, nada acontece. É o que permite rodar isto em toda publicação.
    fonte = pathlib.Path(__file__).read_text(encoding="utf-8")
    corte = fonte.find("def autoteste")
    operacional = fonte[:corte]
    checar("sem `trocar: true` o script não grava nada",
           'if not pedido.get("trocar") and not ensaio:' in operacional
           and operacional.count("gravar_em(") == 2)
    checar("a gravação acontece depois da guarda",
           operacional.index('if not pedido.get("trocar")') < operacional.index("gravar_em("))

    if falhas:
        print(f"X AUTOTESTE: {len(falhas)} caso(s) reprovado(s).")
        return 1
    print("OK AUTOTESTE — 16 casos, sem rede e sem escrita.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
