#!/usr/bin/env python3
"""Fecha o MARÉ Saúde sem depender de nova instrução — bloco da editoria de 01/10/2026 (23h10).

O QUE ESTE SCRIPT RESPONDE, TODA RODADA
---------------------------------------
1. **Quais UFs podem ser marcadas "não localizado"**, e quais seguem "não verificado". A regra é a
   da editoria: só nas UFs em que **os quatro canais rodaram sem motor doente** e nada qualificou.
   Canal que não rodou, ou que rodou com erro, mantém a UF **não verificada** — e a diferença entre
   as duas afirmações é a diferença entre "procuramos e não achamos" e "ainda não procuramos".

2. **Quantas UFs faltam, e por quê.** É o relatório diário que o publicador imprime (item 4 do
   bloco): não basta dizer "21 de 27"; tem de dizer o que falta em cada uma das seis restantes.

3. **Se já é hora de trocar para a v0.4.** A troca foi autorizada em 01/10 e tem condição única:
   as 27 verificadas **no plano e na coordenação**. Enquanto a condição não se cumpre, este script
   não muda nada na página — só relata. Quando ela se cumprir, ele grava o pedido de troca
   (`data/saude_troca_v04.json`), que é o que o publicador lê para trocar e emitir a errata.

POR QUE LER O LOG, E NÃO UM CAMPO DE CONTROLE
---------------------------------------------
Quem sabe se um canal rodou é o log v2, que é append-only e tem a execução de cada canal por UF,
com a decisão no vocabulário fechado. Um campo "canais_ok: true" num arquivo de estado seria uma
afirmação sobre o passado que ninguém confere; o log é o passado. `canais_por_uf` abaixo lê as
execuções do funil de saúde e devolve, por UF, qual canal rodou e com que decisão.

USO
    python3 scripts/fechar_saude.py                 # relatório, sem escrever
    python3 scripts/fechar_saude.py --aplicar       # grava o pedido de troca, se for o caso
    python3 scripts/fechar_saude.py --autoteste
"""
import datetime
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
DATA = RAIZ / "data"
SAIDA = DATA / "saude_troca_v04.json"
UFS = ("AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO").split()

# Os quatro canais da bateria, e como cada um se reconhece no texto de `resultados` do log. O
# vocabulário é o que os coletores escrevem — não se adivinha aqui.
CANAIS = {
    "aberta": ("resultado(s) bruto(s)",),
    # 02/10/2026 (diretriz da central): o canal 2 NÃO é "busca no diário" — é "baixar a edição".
    # O localizador (`coletar_edicoes_doe.py`) escreve "canal 2 em <UF>: n edição(ões) lida(s)", e
    # a busca no sítio, onde existir, continua valendo. Sondar rota de busca está encerrado.
    "doe": ("DOE de", "rota de busca confirmada", "canal 2 em"),
    "canais": ("link(s) de canal", "fontes_uf.json", "secretaria"),
    "fontes": ("fonte(s) lida(s)", "nenhuma fonte"),
}
# Canal 2 por VERIFICAÇÃO HUMANA: quando a edição não pode ser baixada por limitação técnica de
# terceiro documentada (401, 403, captcha, muro de robô), o localizador grava
# `canal2.modo = "verificacao_humana"` com o motivo, e isso CONTA como canal consultado. É a regra
# da Paraíba, generalizada pela editoria em 02/10/2026: nenhuma unidade da federação fica "não
# verificada" para sempre por causa de uma limitação que não é nossa e que está escrita.
MODOS_DE_CANAL2_QUE_CONTAM = ("padrao_por_data", "listagem", "verificacao_humana")
# Decisões que contam como "o canal rodou e a fonte respondeu". `erro` nunca conta: é motor doente,
# fonte fora do ar ou canal indisponível, e nenhuma das três autoriza falar de ausência.
DECISOES_SAUDAVEIS = ("consultado sem achado", "pista", "registro")


def ler(p, padrao=None):
    try:
        return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return padrao


def canal_do_texto(resultados: str):
    """Qual canal escreveu esta linha do log. Função pura; None quando não é da bateria."""
    t = str(resultados or "")
    if "funil_saude/" not in t:
        return None
    for canal, marcas in CANAIS.items():
        if any(m in t for m in marcas):
            return canal
    return None


def canais_por_uf(linhas) -> dict:
    """{uf: {canal: decisao}} a partir das linhas do log v2. Função pura.

    Fica a decisão MAIS RECENTE de cada canal: a bateria roda toda noite, e o que vale é a última
    execução — não a primeira que apareceu no mês."""
    saida = {}
    for e in linhas:
        canal = canal_do_texto(e.get("resultados"))
        uf = e.get("uf")
        if not canal or uf not in UFS:
            continue
        saida.setdefault(uf, {})[canal] = e.get("decisao") or e.get("decisão")
    return saida


def canal2_do_localizador(registros: dict) -> dict:
    """{uf: decisão do canal 2} a partir dos registros do localizador de edições. Função pura.

    `registros` é {uf: conteúdo de data/doe_edicoes/<UF>.json}. Uma UF entra como consultada
    quando o localizador leu edição no período **ou** quando gravou verificação humana com motivo.
    Edição baixada e sem o termo é "consultado sem achado" — que é consulta, e não ausência de
    documento.
    """
    fora = {}
    for uf, r in (registros or {}).items():
        if not isinstance(r, dict):
            continue
        c2 = r.get("canal2") or {}
        modo = c2.get("modo")
        if modo == "verificacao_humana" and c2.get("motivo"):
            fora[uf] = "consultado sem achado"
            continue
        edicoes = (r.get("edicoes") or {}).values()
        lidas = [e for e in edicoes if isinstance(e, dict) and e.get("decisao") == "lida"]
        if not lidas:
            continue
        com_termo = any(e.get("termos_achados") for e in lidas)
        fora[uf] = "registro" if com_termo else "consultado sem achado"
    return fora


def pode_dizer_nao_localizado(canais: dict) -> bool:
    """A UF pode ser marcada "não localizado"? Função pura.

    Exige os QUATRO canais com decisão saudável. Um canal ausente, ou com `erro`, derruba — e é
    assim que "não procuramos ainda" deixa de virar "não existe"."""
    if not canais:
        return False
    return all(canais.get(c) in DECISOES_SAUDAVEIS for c in CANAIS)


def unir_canais(do_log: dict, do_localizador: dict) -> dict:
    """Une o que o log diz com o que o localizador diz, para o canal 2. Função pura.

    A união é por UF e **não rebaixa**: canal 2 com registro no localizador vale mesmo que a linha
    do log daquela noite tenha ficado em `erro` — o que importa é se a edição foi lida, e ela foi.
    """
    ordem = {"erro": 0, "consultado sem achado": 1, "pista": 2, "registro": 3}
    fora = {uf: dict(v) for uf, v in (do_log or {}).items()}
    for uf, decisao in (do_localizador or {}).items():
        atual = (fora.setdefault(uf, {})).get("doe")
        if ordem.get(decisao, 0) >= ordem.get(atual, -1):
            fora[uf]["doe"] = decisao
    return fora


def estado_das_ufs(monitor: dict, v04: dict, canais: dict) -> dict:
    """{uf: {plano, coordenacao, canais_ok, falta}} — o quadro da rodada. Função pura."""
    quadro = {}
    for uf in UFS:
        m = (monitor.get("ufs") or {}).get(uf) or {}
        v = (v04.get("uf") or {}).get(uf) or {}
        plano = bool((m.get("instrumento") or {}).get("doc"))
        coord = bool((v.get("coordenacao") or {}).get("doc"))
        ok = pode_dizer_nao_localizado(canais.get(uf) or {})
        falta = []
        if not plano:
            falta.append("plano não localizado" if ok else "plano não verificado")
        if not coord:
            falta.append("coordenação não localizada" if ok else "coordenação não verificada")
        quadro[uf] = {"plano": plano, "coordenacao": coord, "canais_ok": ok, "falta": falta}
    return quadro


def hora_de_trocar(quadro: dict) -> bool:
    """As 27 verificadas no plano E na coordenação? Função pura.

    "Verificada" aqui é o que a editoria exigiu: documento lido nas duas dimensões. Canal incompleto
    não basta nem para o lado negativo — e por isso a troca espera o quadro inteiro."""
    return len(quadro) == len(UFS) and all(v["plano"] and v["coordenacao"] for v in quadro.values())


def relatorio(quadro: dict) -> list:
    """As linhas do relatório diário do publicador. Função pura."""
    com_plano = sum(1 for v in quadro.values() if v["plano"])
    com_coord = sum(1 for v in quadro.values() if v["coordenacao"])
    completas = sum(1 for v in quadro.values() if v["canais_ok"])
    linhas = [f"MARÉ Saúde: {com_plano} de 27 com plano localizado, {com_coord} de 27 com "
              f"coordenação localizada, {completas} de 27 com os quatro canais rodados."]
    faltam = {uf: v for uf, v in quadro.items() if v["falta"]}
    if not faltam:
        linhas.append("Nenhuma UF pendente: a troca para a v0.4 está liberada.")
        return linhas
    linhas.append(f"Faltam {len(faltam)} UF(s):")
    for uf, v in sorted(faltam.items()):
        linhas.append(f"  · {uf}: " + "; ".join(v["falta"])
                      + ("" if v["canais_ok"] else " (bateria incompleta nesta UF)"))
    return linhas


def mes_do_log(hoje: datetime.date) -> pathlib.Path:
    return DATA / "log_buscas" / f"{hoje.year}-{hoje.month:02d}.jsonl"


def linhas_do_log(caminho: pathlib.Path):
    if not caminho.exists():
        return []
    saida = []
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha:
            continue
        try:
            saida.append(json.loads(linha))
        except json.JSONDecodeError:
            continue
    return saida


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    monitor = ler(DATA / "monitor_saude.json", {}) or {}
    v04 = ler(DATA / "monitor_saude_v04.json", {}) or {}
    sys.path.insert(0, str(RAIZ))
    from coletores_base import hoje_editorial  # noqa: PLC0415 — data editorial, não UTC
    hoje = hoje_editorial()
    # O canal 2 tem duas fontes de verdade: a linha do log da bateria e o registro do localizador
    # de edições. A segunda é a que vale desde 02/10/2026, e as duas se unem sem rebaixar.
    registros = {}
    for f in sorted((DATA / "doe_edicoes").glob("*.json")) if (DATA / "doe_edicoes").exists() else []:
        registros[f.stem] = ler(f, {}) or {}
    canais = unir_canais(canais_por_uf(linhas_do_log(mes_do_log(hoje))),
                         canal2_do_localizador(registros))
    quadro = estado_das_ufs(monitor, v04, canais)
    for linha in relatorio(quadro):
        print(linha)
    trocar = hora_de_trocar(quadro)
    if "--aplicar" in sys.argv:
        pedido = {
            "_governanca":
                "Pedido de troca do MARÉ Saúde para a v0.4. Escrito por scripts/fechar_saude.py e "
                "lido pelo publicador. `trocar: true` só quando as 27 UFs tiverem documento lido "
                "no plano E na coordenação — a condição que a editoria fixou em 01/10/2026. "
                "Enquanto for false, nada muda na página além da contagem de verificadas.",
            "trocar": trocar,
            "medido_em": hoje.isoformat(),
            "com_plano": sum(1 for v in quadro.values() if v["plano"]),
            "com_coordenacao": sum(1 for v in quadro.values() if v["coordenacao"]),
            "com_quatro_canais": sum(1 for v in quadro.values() if v["canais_ok"]),
            "pendencias": {uf: v["falta"] for uf, v in sorted(quadro.items()) if v["falta"]},
        }
        from coletores_base import gravar_em  # noqa: PLC0415 — §229: escrita atômica
        gravar_em(SAIDA, pedido)
        print(f"→ {SAIDA.relative_to(RAIZ)} gravado · trocar={trocar}")
    return 0


def autoteste() -> int:
    falhas = []

    def checar(nome, cond):
        print(("  OK   " if cond else "  FALHA ") + nome)
        if not cond:
            falhas.append(nome)

    log = [
        {"uf": "AC", "decisao": "consultado sem achado",
         "resultados": "funil_saude/AC: 80 resultado(s) bruto(s), 0 pista(s)"},
        {"uf": "AC", "decisao": "consultado sem achado",
         "resultados": "funil_saude/AC: DOE de 2026-06-29 a 2026-10-01, 3 acerto(s)"},
        {"uf": "AC", "decisao": "consultado sem achado",
         "resultados": "funil_saude/AC: 0 link(s) de canal em https://saude.ac.gov.br/"},
        {"uf": "AC", "decisao": "consultado sem achado",
         "resultados": "funil_saude/AC: 1 fonte(s) lida(s), 0 falha(s)"},
        {"uf": "AL", "decisao": "erro",
         "resultados": "funil_saude/AL: 0 resultado(s) bruto(s), 0 pista(s)"},
        {"uf": "AL", "decisao": "consultado sem achado",
         "resultados": "funil_saude/AL: 2 link(s) de canal em https://www.saude.al.gov.br/"},
        {"uf": "ZZ", "decisao": "pista", "resultados": "funil_saude/ZZ: 1 link(s) de canal"},
        {"uf": "MT", "decisao": "registro", "resultados": "outra coisa qualquer"},
    ]
    canais = canais_por_uf(log)
    checar("o canal de cada linha sai do texto que o coletor escreveu",
           canais["AC"] == {"aberta": "consultado sem achado", "doe": "consultado sem achado",
                            "canais": "consultado sem achado", "fontes": "consultado sem achado"})
    checar("linha fora da bateria não entra", "MT" not in canais)
    checar("UF que não existe não entra", "ZZ" not in canais)
    checar("quatro canais saudáveis autorizam 'não localizado'",
           pode_dizer_nao_localizado(canais["AC"]))
    checar("canal com erro derruba a autorização", not pode_dizer_nao_localizado(canais["AL"]))
    checar("canal ausente derruba a autorização",
           not pode_dizer_nao_localizado({"aberta": "consultado sem achado"}))
    checar("UF sem nenhuma execução não autoriza nada", not pode_dizer_nao_localizado({}))
    # O ponto central: o lado negativo exige MAIS prova, não menos.
    checar("decisão de erro nunca conta como canal rodado",
           "erro" not in DECISOES_SAUDAVEIS)

    monitor = {"ufs": {uf: {"instrumento": {"doc": "x"}} for uf in UFS}}
    v04 = {"uf": {uf: {"coordenacao": {"doc": "y"}} for uf in UFS}}
    quadro_cheio = estado_das_ufs(monitor, v04, {uf: canais["AC"] for uf in UFS})
    checar("com as 27 nas duas dimensões, a troca está liberada", hora_de_trocar(quadro_cheio))
    checar("quadro cheio não lista pendência",
           all(not v["falta"] for v in quadro_cheio.values()))

    parcial = estado_das_ufs({"ufs": {"AC": {"instrumento": {"doc": "x"}}}}, {}, {})
    checar("sem coordenação, a troca não acontece", not hora_de_trocar(parcial))
    checar("UF sem bateria completa aparece como 'não verificado', não 'não localizado'",
           "plano não verificado" in parcial["AL"]["falta"]
           and "coordenação não verificada" in parcial["AL"]["falta"])
    completo = estado_das_ufs({"ufs": {}}, {}, {uf: canais["AC"] for uf in UFS})
    checar("com os quatro canais e nada achado, a UF vira 'não localizado'",
           "plano não localizado" in completo["AC"]["falta"])
    linhas = relatorio(parcial)
    checar("o relatório diz quantas faltam e por quê",
           any("Faltam" in x for x in linhas) and any("AC:" in x for x in linhas))
    checar("o relatório abre pela contagem das três dimensões",
           "de 27 com plano localizado" in linhas[0] and "quatro canais" in linhas[0])

    if falhas:
        print(f"X AUTOTESTE: {len(falhas)} caso(s) reprovado(s).")
        return 1
    print(f"OK AUTOTESTE — {13 + len(UFS) * 0} casos, sem rede e sem escrita.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
