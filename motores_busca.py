#!/usr/bin/env python3
"""
motores_busca.py
================
Disjuntor por motor de origem da camada 4: desliga por **evidência**, nunca por adivinhação.

Item 7b do handover `HANDOVER_juiz_automatico_e_busca_web_27-09-2026.md` (decisão da central,
28/09/2026), em resposta ao que o §264 mediu: 139 de 150 consultas sem resposta do motor. O SearXNG
é um metabuscador — ele repassa a consulta a dezenas de motores de origem, e são eles que limitam por
endereço. Sem saber QUAL barrou, desligar motor é chute; com a contagem por motor, é decisão.

COMO FUNCIONA
-------------
1. **Sentinela.** No início da rodada, uma consulta fixa por motor —
   `"Brasil" "defesa civil" plano de contingência`. É uma busca que tem resposta em qualquer motor
   que esteja funcionando: se vier vazia, o motor está mudo, e isso não se confunde com "o município
   não tem plano".
2. **Contagem durante a rodada.** Por motor: 429, CAPTCHA, timeout e corpo vazio. O SearXNG informa
   quem não respondeu no campo `unresponsive_engines` de cada resposta.
3. **Disjuntor.** Motor com **mais de 50% de falhas** numa rodada, ou **sentinela muda em duas
   rodadas seguidas**, fica **desligado por 24 h** e volta sozinho, com nova sentinela.
4. **Piso de dois.** Nunca se desligam todos: no mínimo **dois** motores ficam ativos. Se sobrar
   menos de dois, a rodada encerra e registra `motor_sem_resposta` — dizer "não localizamos" com um
   motor só seria afirmar ausência sem ter perguntado.

O desligamento é por REQUISIÇÃO (o parâmetro `engines` da consulta), não por edição de
`scripts/searxng_settings.yml`: nada fica desligado em disco, e a volta é automática.

Estado em `data/busca_web_motores.json`. Ele não pontua nada e não é lido pelo cálculo do índice.

USO
  python3 motores_busca.py --autoteste
  python3 motores_busca.py --estado        # lista ativos e desligados, com as contagens
"""
import datetime
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

ARQUIVO = "busca_web_motores.json"
SENTINELA = '"Brasil" "defesa civil" plano de contingência'
TETO_DE_FALHAS = 0.50          # acima disso, numa rodada, o motor cai
SENTINELAS_MUDAS_PARA_CAIR = 2
HORAS_DESLIGADO = 24
MINIMO_ATIVOS = 2

# Motores pedidos na consulta. Lista curta e declarada: o SearXNG traz dezenas por padrão, e a
# maioria não serve para diário oficial brasileiro. Cada entrada é um motor que já devolveu documento
# oficial em rodada real; a adição de motor é decisão de configuração, registrada no CHANGELOG.
MOTORES = ("duckduckgo", "bing", "brave", "mojeek", "startpage", "qwant")


def agora_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def estado_vazio() -> dict:
    return {"_governanca": ("Disjuntor por motor de origem da camada 4 (item 7b, 28/09/2026). "
                            "Desligamento por requisição, nunca por edição de settings.yml; volta "
                            "automática depois de 24 h, com nova sentinela. Nunca menos de dois "
                            "motores ativos."),
            "motores": {}, "atualizado_em": None}


def ler_estado(ler=None) -> dict:
    if ler is None:
        from coletores_base import ler as ler_padrao
        ler = ler_padrao
    return ler(ARQUIVO) or estado_vazio()


def desligado(info: dict, agora: str) -> bool:
    """Está dentro da janela de 24 h? Sem `desligado_ate`, está ativo."""
    ate = (info or {}).get("desligado_ate")
    return bool(ate) and str(agora) < str(ate)


def livres(estado: dict, agora: str) -> list:
    """Os motores fora da janela de desligamento — sem o complemento do piso."""
    return [m for m in MOTORES if not desligado((estado.get("motores") or {}).get(m), agora)]


def ativos(estado: dict, agora: str) -> list:
    """Os motores que a rodada vai pedir, na ordem de MOTORES.

    Se o disjuntor deixaria menos de dois ativos, devolve os dois que caíram há mais tempo — o piso
    de dois existe para que a rodada nunca afirme ausência tendo perguntado a um motor só."""
    livres = [m for m in MOTORES if not desligado((estado.get("motores") or {}).get(m), agora)]
    if len(livres) >= MINIMO_ATIVOS:
        return livres
    caidos = sorted(((estado.get("motores") or {}).get(m, {}).get("desligado_ate", ""), m)
                    for m in MOTORES if m not in livres)
    return livres + [m for _, m in caidos[:MINIMO_ATIVOS - len(livres)]]


def contabilizar(estado: dict, motor: str, consultas: int = 0, falhas: int = 0,
                 sentinela_muda: bool = None) -> dict:
    """Soma as contagens da rodada para um motor. Devolve o estado (mutado)."""
    m = estado.setdefault("motores", {}).setdefault(motor, {})
    m["consultas_na_rodada"] = int(m.get("consultas_na_rodada", 0)) + consultas
    m["falhas_na_rodada"] = int(m.get("falhas_na_rodada", 0)) + falhas
    if sentinela_muda is True:
        m["sentinelas_mudas_seguidas"] = int(m.get("sentinelas_mudas_seguidas", 0)) + 1
    elif sentinela_muda is False:
        m["sentinelas_mudas_seguidas"] = 0
    return estado


def aplicar_disjuntor(estado: dict, agora: str) -> tuple:
    """Fecha a rodada: decide quem cai, zera as contagens e devolve (estado, caidos, motivos).

    Nunca deixa menos de `MINIMO_ATIVOS` ativos: se as quedas levariam a isso, as de MENOR taxa de
    falha são poupadas — e o fato de terem sido poupadas fica registrado."""
    volta = (datetime.datetime.fromisoformat(agora) + datetime.timedelta(hours=HORAS_DESLIGADO))
    candidatos, motivos = [], {}
    for motor in MOTORES:
        info = (estado.get("motores") or {}).get(motor) or {}
        if desligado(info, agora):
            continue
        consultas = int(info.get("consultas_na_rodada", 0))
        falhas = int(info.get("falhas_na_rodada", 0))
        taxa = (falhas / consultas) if consultas else 0.0
        if consultas and taxa > TETO_DE_FALHAS:
            candidatos.append((taxa, motor))
            motivos[motor] = f"{falhas}/{consultas} falhas ({100 * taxa:.0f}%) acima do teto de 50%"
        elif int(info.get("sentinelas_mudas_seguidas", 0)) >= SENTINELAS_MUDAS_PARA_CAIR:
            candidatos.append((1.0, motor))
            motivos[motor] = (f"sentinela muda em {info['sentinelas_mudas_seguidas']} rodadas "
                              f"seguidas")

    ativos_agora = [m for m in MOTORES if not desligado((estado.get("motores") or {}).get(m), agora)]
    podem_cair = max(0, len(ativos_agora) - MINIMO_ATIVOS)
    # os piores caem primeiro; os poupados ficam com o motivo registrado
    candidatos.sort(reverse=True)
    # 09/10/2026 (lote 2.7, A1-11): motor com 100 % de falhas cai sempre — o piso poupava o bing
    # morto, e a rodada seguia "perguntando" a quem não responde. Sem dois motores livres, quem
    # chama encerra a rodada (`monitorar_busca_web`), em vez de afirmar ausência.
    mortos = [m for t, m in candidatos if t >= 1.0 and m in motivos and "falhas" in motivos[m]]
    vivos = [(t, m) for t, m in candidatos if m not in mortos]
    podem_cair = max(0, podem_cair - len(mortos))
    caidos = mortos + [m for _, m in vivos[:podem_cair]]
    poupados = [m for _, m in vivos[podem_cair:]]

    for motor in caidos:
        info = estado["motores"].setdefault(motor, {})
        info["desligado_ate"] = volta.replace(microsecond=0).isoformat()
        info["motivo"] = motivos[motor]
        info["desligado_em"] = agora
    for motor in poupados:
        info = estado["motores"].setdefault(motor, {})
        info["poupado_pelo_piso"] = (f"{motivos[motor]}, mas seria o {MINIMO_ATIVOS}º a cair e o "
                                     f"piso de {MINIMO_ATIVOS} motores ativos venceu")
    # contagens são da rodada: zeram ao fim dela
    for motor in MOTORES:
        info = (estado.get("motores") or {}).get(motor)
        if info:
            info["consultas_na_rodada"] = 0
            info["falhas_na_rodada"] = 0
    estado["atualizado_em"] = agora
    return estado, caidos, motivos


def resumo(estado: dict, agora: str) -> str:
    """Uma linha por motor, para o MANIFESTO da rodada e o resumo do job."""
    linhas = ["| motor | situação | motivo |", "|---|---|---|"]
    for motor in MOTORES:
        info = (estado.get("motores") or {}).get(motor) or {}
        if desligado(info, agora):
            situacao = f"desligado até {info.get('desligado_ate', '?')[:16].replace('T', ' ')} UTC"
        else:
            situacao = "ativo"
        motivo = info.get("motivo") if desligado(info, agora) else info.get("poupado_pelo_piso", "")
        linhas.append(f"| `{motor}` | {situacao} | {motivo or '—'} |")
    return "\n".join(linhas)


def falhas_por_motor(dados: dict) -> set:
    """Quem não respondeu, segundo o próprio SearXNG.

    `unresponsive_engines` vem como lista de pares [motor, razão] — em algumas versões como lista de
    listas, em outras de tuplas; aceita as duas, e ignora entrada fora de forma em vez de estourar."""
    fora = set()
    for item in (dados or {}).get("unresponsive_engines") or []:
        if isinstance(item, (list, tuple)) and item:
            fora.add(str(item[0]))
        elif isinstance(item, str):
            fora.add(item)
    return fora


def autoteste() -> int:
    casos = []
    agora = "2026-09-28T02:00:00+00:00"
    depois = "2026-09-29T03:00:00+00:00"

    # 1. estado limpo: todos ativos
    e = estado_vazio()
    casos.append(("estado limpo deixa todos ativos", ativos(e, agora) == list(MOTORES)))

    # 2. mais de 50% de falhas derruba
    e = estado_vazio()
    contabilizar(e, "bing", consultas=10, falhas=6)
    e, caidos, _ = aplicar_disjuntor(e, agora)
    casos.append(("acima de 50% de falhas o motor cai", caidos == ["bing"]))
    casos.append(("o caído sai da lista de ativos", "bing" not in ativos(e, agora)))
    casos.append(("e volta sozinho depois de 24 h", "bing" in ativos(e, depois)))

    # 2b. 09/10/2026 (lote 2.7, A1-11): 100 % de falhas cai mesmo contra o piso
    e = estado_vazio()
    for m in MOTORES:
        contabilizar(e, m, consultas=10, falhas=10 if m == MOTORES[0] else 0)
    for m in MOTORES[1:-1]:
        e["motores"][m]["desligado_ate"] = "2026-09-29T00:00:00+00:00"
    e, caidos, _ = aplicar_disjuntor(e, agora)
    casos.append(("motor com 100% de falhas não é poupado pelo piso", MOTORES[0] in caidos))
    casos.append(("e sai da lista dos livres", MOTORES[0] not in livres(e, agora)))

    # 3. exatamente 50% NÃO derruba (o teto é "acima de")
    e = estado_vazio()
    contabilizar(e, "bing", consultas=10, falhas=5)
    _, caidos, _ = aplicar_disjuntor(e, agora)
    casos.append(("exatamente 50% não derruba", caidos == []))

    # 4. sentinela muda: uma não derruba, duas derrubam
    e = estado_vazio()
    contabilizar(e, "qwant", sentinela_muda=True)
    _, caidos, _ = aplicar_disjuntor(dict(e, motores=dict(e["motores"])), agora)
    casos.append(("uma sentinela muda não derruba", caidos == []))
    contabilizar(e, "qwant", sentinela_muda=True)
    e2, caidos, motivos = aplicar_disjuntor(e, agora)
    casos.append(("duas sentinelas mudas seguidas derrubam", caidos == ["qwant"]))
    casos.append(("o motivo da queda fica escrito", "sentinela muda" in motivos["qwant"]))

    # 5. sucesso zera a sequência de sentinelas mudas
    e = estado_vazio()
    contabilizar(e, "brave", sentinela_muda=True)
    contabilizar(e, "brave", sentinela_muda=False)
    contabilizar(e, "brave", sentinela_muda=True)
    _, caidos, _ = aplicar_disjuntor(e, agora)
    casos.append(("sentinela que responde zera a sequência", caidos == []))

    # 6. o piso de dois: com todos falhando MUITO (mas não 100 %), dois sobrevivem
    e = estado_vazio()
    for m in MOTORES:
        contabilizar(e, m, consultas=10, falhas=9)
    e, caidos, _ = aplicar_disjuntor(e, agora)
    restantes = ativos(e, agora)
    casos.append(("nunca sobram menos de dois ativos", len(restantes) >= MINIMO_ATIVOS))
    casos.append(("os demais caem", len(caidos) == len(MOTORES) - MINIMO_ATIVOS))
    casos.append(("o poupado registra por que sobreviveu",
                  any("piso de" in ((e["motores"].get(m) or {}).get("poupado_pelo_piso") or "")
                      for m in restantes)))

    # 6b. 09/10/2026: todos com 100 % de falhas — todos caem; nenhum livre (a rodada encerra)
    e = estado_vazio()
    for m in MOTORES:
        contabilizar(e, m, consultas=10, falhas=10)
    e, caidos, _ = aplicar_disjuntor(e, agora)
    casos.append(("todos mortos: todos caem e nenhum fica livre",
                  len(caidos) == len(MOTORES) and livres(e, agora) == []))

    # 7. as contagens são da rodada e zeram no fim dela
    e = estado_vazio()
    contabilizar(e, "mojeek", consultas=5, falhas=1)
    e, _, _ = aplicar_disjuntor(e, agora)
    casos.append(("as contagens da rodada zeram no fim",
                  e["motores"]["mojeek"]["consultas_na_rodada"] == 0
                  and e["motores"]["mojeek"]["falhas_na_rodada"] == 0))

    # 8. leitura do unresponsive_engines nas duas formas
    casos.append(("lê unresponsive_engines como lista de pares",
                  falhas_por_motor({"unresponsive_engines": [["bing", "timeout"]]}) == {"bing"}))
    casos.append(("lê unresponsive_engines como lista de strings",
                  falhas_por_motor({"unresponsive_engines": ["bing"]}) == {"bing"}))
    casos.append(("ausência do campo não estoura", falhas_por_motor({}) == set()))
    casos.append(("entrada fora de forma é ignorada, não estoura",
                  falhas_por_motor({"unresponsive_engines": [None, 42, []]}) == set()))

    # 9. a sentinela é uma busca que qualquer motor vivo responde
    casos.append(("a sentinela não nomeia município nenhum",
                  "Brasil" in SENTINELA and "{" not in SENTINELA))

    # 10. o resumo traz uma linha por motor
    texto = resumo(e, agora)
    casos.append(("o resumo traz uma linha por motor", texto.count("| `") == len(MOTORES)))

    ruins = [n for n, ok in casos if not ok]
    for n, ok in casos:
        print(f"  {'OK  ' if ok else 'FALHA'} {n}")
    if ruins:
        print(f"X AUTOTESTE: {len(ruins)} caso(s) reprovado(s).")
        return 1
    print(f"OK AUTOTESTE — {len(casos)} casos, sem rede e sem escrita.")
    return 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    if "--estado" in sys.argv:
        e = ler_estado()
        print(resumo(e, agora_iso()))
        return 0
    print(__doc__.strip().split("USO")[-1].strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
