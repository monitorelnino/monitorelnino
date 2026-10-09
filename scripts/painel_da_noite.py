#!/usr/bin/env python3
"""Painel da noite: cada elo da corrente, com início, fim e se terminou dentro da janela.

Item A.5 do handover da corrente noturna (03/10/2026). O diagnóstico que o motivou: na noite de
02→03/10 o elo das **evidências e OCR não rodou**, e ninguém viu — a corrente terminou, os dados
foram publicados, e a falta só apareceu quando a central foi conferir à mão. Elo que não roda não
deixa buraco visível: deixa um arquivo com a data de ontem, que se parece com um arquivo normal.

O painel é append-only, uma linha por elo por noite:

    {"noite": "2026-10-04", "elo": "diarios", "inicio": "01:02", "fim": "04:49",
     "minutos": 227, "dentro_da_janela": true, "conclusao": "success"}

A JANELA é 22h–06h de Brasília (01:00–09:00 UTC). "Dentro da janela" é o que a editoria pediu para
ver de relance: um elo que termina às 7h da manhã roubou a manhã da redação, e isso não aparece no
log do GitHub sem abrir cada run.

O portão (`--portao`) reprova quando um elo da corrente **não tem linha na noite anterior**: é a
forma de a ausência virar vermelho em vez de silêncio.

USO (no fim de cada elo, dentro do workflow)
    python3 scripts/painel_da_noite.py --registrar diarios --inicio 01:02 --conclusao success
    python3 scripts/painel_da_noite.py --relatorio
    python3 scripts/painel_da_noite.py --portao
    python3 scripts/painel_da_noite.py --autoteste
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

ARQUIVO = "painel_da_noite.json"
# Os elos da corrente, na ordem do handover. A busca web não é elo: ela roda em paralelo, com os
# seus cinco horários próprios — e por isso entra no painel como rotina à parte, sem exigência de
# estar na corrente.
ELOS = ("diarios", "descoberta", "evidencias", "juiz", "sinais", "triagem", "publicar")
PARALELAS = ("busca_web",)
JANELA_UTC = (1, 9)   # 01:00 às 09:00 UTC = 22h às 06h de Brasília
GOV = ("Painel da noite (item A.5 do handover de 03/10/2026): uma linha por elo por noite, com "
       "início, fim e se terminou dentro da janela de 22h às 06h. Append-only. Serve para que elo "
       "que NÃO rodou apareça — foi o que faltou na noite de 02→03/10, quando as evidências não "
       "rodaram e nada acusou.")


def minutos_entre(inicio: str, fim: str):
    """Minutos entre dois HH:MM, virando a meia-noite quando preciso. Função pura."""
    def em_minutos(hhmm):
        try:
            h, m = (int(x) for x in str(hhmm).split(":")[:2])
            return h * 60 + m
        except (ValueError, TypeError):
            return None
    a, b = em_minutos(inicio), em_minutos(fim)
    if a is None or b is None:
        return None
    return (b - a) if b >= a else (b + 24 * 60 - a)


def dentro_da_janela(fim_utc: str, janela=JANELA_UTC) -> bool:
    """O elo terminou dentro da janela noturna? Função pura."""
    try:
        h = int(str(fim_utc).split(":")[0])
    except (ValueError, TypeError):
        return False
    inicio, fim = janela
    return inicio <= h < fim if inicio < fim else (h >= inicio or h < fim)


def trabalhou(conclusao: str, feito: bool = None) -> bool:
    """O elo realmente TRABALHOU nesta noite? Função pura.

    05/10/2026 (item 3.1 do handover da noite confiável) — CANCELADO NÃO É FEITO.
    Medido na noite de 04→05/10: o job `diarios / coletar` foi cancelado às 01:14:09 UTC, dois
    minutos depois de começar, e a guarda "esta noite já abriu?" contou aquele run como abertura.
    A reserva e o despachante acharam que a noite tinha aberto, e **ninguém refez a coleta
    perdida**. As tentativas das 03:56 e 04:38 saíram sem trabalhar.

    A distinção que importa não é a conclusão do run, é se houve trabalho: um elo que coletou e
    falhou no PUSH trabalhou — refazê-lo duplicaria lote e commit, que é o que o comentário
    anterior desta função temia, com razão. Um elo cancelado antes de coletar não trabalhou.

    Quem sabe a diferença é o próprio elo, que grava o marcador `feito` ao terminar os comandos de
    coleta, ANTES do commit. Por isso `feito` vence a conclusão sempre que está declarado; sem
    marcador, cai-se no que a conclusão permite dizer.
    """
    if feito is not None:
        return bool(feito)
    # 09/10/2026: `queued`, `requested`, `waiting` e `pending` entram na lista. Um run criado e à
    # espera de runner não falhou — e tratá-lo como "não trabalhou" fez o vigia disparar a corrente
    # por cima de si mesma na noite de 08→09, derrubando dois elos pendentes.
    return str(conclusao or "").strip().lower() in (
        "success", "in_progress", "failure", "queued", "requested", "waiting", "pending")


NAO_CONTAM = ("cancelled", "skipped", "timed_out", "desconhecida", "")


def linha(elo: str, noite: str, inicio: str, fim: str, conclusao: str,
          feito: bool = None) -> dict:
    """A linha do painel. Função pura — é ela que o autoteste exercita."""
    return {"noite": noite, "elo": elo, "inicio": inicio, "fim": fim,
            "minutos": minutos_entre(inicio, fim),
            "dentro_da_janela": dentro_da_janela(fim),
            "conclusao": conclusao or "desconhecida",
            "trabalhou": trabalhou(conclusao, feito)}


# 04/10/2026: o horário PREVISTO de cada elo. Só a abertura tem cron; os outros são acionados pelo
# término do anterior, e o previsto deles é uma estimativa de ordem, não um compromisso de relógio.
# Está aqui para o painel poder dizer "previsto × iniciado", que é o que mostra a noite ESCORREGANDO
# antes de ela acabar — um elo que começa 3h depois do previsto ainda roda, e ninguém via.
PREVISTO_UTC = {"diarios": "01:07", "descoberta": "05:00", "evidencias": "06:00",
                "juiz": "07:00", "sinais": "08:00", "triagem": "08:30", "publicar": "09:05"}


def previsto_x_iniciado(linhas: list, noite: str, elos=ELOS) -> list:
    """Uma linha por elo: previsto, iniciado e a diferença. Função pura.

    Elo sem registro aparece com `iniciado: None` — e é esse o caso que importa: o painel existe
    para que o elo que NÃO rodou apareça, e não só o que rodou devagar.
    """
    por_elo = {l.get("elo"): l for l in (linhas or []) if l.get("noite") == noite}
    fora = []
    for elo in elos:
        l = por_elo.get(elo)
        iniciado = l.get("inicio") if l else None
        previsto = PREVISTO_UTC.get(elo)
        fora.append({"elo": elo, "previsto": previsto, "iniciado": iniciado,
                     "atraso_min": minutos_entre(previsto, iniciado) if (previsto and iniciado)
                     else None})
    return fora


def estado_do_blog(pacotes: list, textos: list, hoje: str) -> dict:
    """A linha "Blog" do painel: pacote pronto e texto da semana, por linha. Função pura.

    04/10/2026, item 4 do handover da rotina semanal. Não bloqueia nada — é acompanhamento: sem
    texto aprovado e publicado de uma linha até a quinta-feira, o painel avisa, e a publicação do
    site segue. `pacotes` são os nomes dos arquivos em `blog/pacotes/`; `textos` são os posts
    publicados, com etiqueta e data.
    """
    fora = {}
    for linha, etiqueta in (("legal", "Legal e financiamento"), ("saude", "Saúde")):
        tem_pacote = any(str(n).endswith(f"_{linha}.json") for n in (pacotes or []))
        posts = [t for t in (textos or []) if (t.get("etiqueta") or "") == etiqueta]
        fora[linha] = {"pacote": "pronto" if tem_pacote else "atrasado",
                       "texto": "publicado" if posts else "sem texto",
                       "ultimo": (posts[0].get("data") if posts else None)}
    return fora


def noite_abriu(linhas: list, noite: str) -> bool:
    """A noite abriu, isto é: o elo de abertura tem linha nesta noite? Função pura."""
    return any(l.get("noite") == noite and l.get("elo") == ELOS[0] for l in (linhas or []))


def elos_que_faltaram(linhas: list, noite: str, elos=ELOS) -> list:
    """Os elos da corrente sem linha nesta noite. Função pura."""
    presentes = {l.get("elo") for l in linhas if l.get("noite") == noite}
    return [e for e in elos if e not in presentes]


def _autoteste() -> int:
    falhas = []
    # O total era um literal e envelhecia calado: dizia cobrir mais casos do que
    # cobre, ou menos. Agora e contado.
    _casos_contados = []

    def ok(nome, cond):
        _casos_contados.append(nome)
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    ok("minutos no mesmo dia", minutos_entre("01:00", "04:47") == 227)
    ok("minutos virando a meia-noite", minutos_entre("23:30", "00:15") == 45)
    ok("hora ilegível não quebra", minutos_entre("x", "01:00") is None)
    ok("fim dentro da janela", dentro_da_janela("04:49"))
    ok("fim na borda de abertura conta", dentro_da_janela("01:00"))
    ok("fim na borda de fechamento não conta", not dentro_da_janela("09:00"))
    ok("fim de manhã está fora", not dentro_da_janela("11:20"))
    ok("hora ilegível está fora", not dentro_da_janela("—"))

    l = linha("diarios", "2026-10-04", "01:02", "04:49", "success")
    ok("a linha traz os minutos", l["minutos"] == 227)
    ok("a linha diz se ficou na janela", l["dentro_da_janela"] is True)
    ok("a linha guarda a conclusão", l["conclusao"] == "success")

    # ---- cancelado não é feito (05/10/2026, item 3.1) ----
    ok("success conta como trabalho", trabalhou("success"))
    ok("em execução conta como trabalho", trabalhou("in_progress"))
    # 09/10/2026: a fila de runner conta como trabalho — é a lição da noite de 08→09.
    for estado in ("queued", "requested", "waiting", "pending"):
        ok(f"na fila de runner ({estado}) conta como trabalho", trabalhou(estado))
    ok("cancelado segue não contando", not trabalhou("cancelled"))
    ok("pulado segue não contando", not trabalhou("skipped"))
    ok("o marcador do elo vence a conclusão", trabalhou("cancelled", feito=True))
    ok("falha conta: o elo coletou e perdeu o push — refazer duplicaria lote",
       trabalhou("failure"))
    ok("CANCELADO não conta", not trabalhou("cancelled"))
    ok("pulado não conta", not trabalhou("skipped"))
    ok("estourou o tempo não conta", not trabalhou("timed_out"))
    ok("conclusão desconhecida não conta", not trabalhou(""))
    ok("o marcador `feito` vence a conclusão: cancelado com trabalho feito CONTA",
       trabalhou("cancelled", feito=True))
    ok("o marcador `feito` vence a conclusão: success sem trabalho NÃO conta",
       not trabalhou("success", feito=False))
    ok("a linha registra se o elo trabalhou",
       linha("x", "n", "01:00", "02:00", "cancelled")["trabalhou"] is False
       and linha("x", "n", "01:00", "02:00", "success")["trabalhou"] is True)
    ok("a caixa da conclusão não muda a resposta", trabalhou("SUCCESS"))

    ok("sem conclusão, fica declarado",
       linha("x", "n", "01:00", "02:00", "")["conclusao"] == "desconhecida")

    linhas = [{"noite": "2026-10-04", "elo": "diarios"},
              {"noite": "2026-10-04", "elo": "descoberta"},
              {"noite": "2026-10-03", "elo": "evidencias"}]
    faltam = elos_que_faltaram(linhas, "2026-10-04")
    ok("elo que não rodou aparece", "evidencias" in faltam and "juiz" in faltam)
    ok("elo de outra noite não conta como presente", "evidencias" in faltam)
    ok("noite completa não acusa nada",
       elos_que_faltaram([{"noite": "n", "elo": e} for e in ELOS], "n") == [])
    ok("a busca web não é elo da corrente", "busca_web" not in ELOS)

    px = previsto_x_iniciado([{"noite": "n", "elo": "diarios", "inicio": "02:40"}], "n")
    ok("previsto × iniciado cobre todos os elos", len(px) == len(ELOS))
    ok("o atraso do elo é medido do previsto",
       px[0]["atraso_min"] == 93 and px[0]["previsto"] == "01:07")
    ok("elo sem registro aparece como não iniciado",
       px[1]["iniciado"] is None and px[1]["atraso_min"] is None)
    ok("noite com o elo de abertura registrado abriu",
       noite_abriu([{"noite": "n", "elo": "diarios"}], "n"))
    ok("noite só com elos posteriores NÃO abriu",
       not noite_abriu([{"noite": "n", "elo": "juiz"}], "n"))
    ok("painel vazio não diz que abriu", not noite_abriu([], "n"))

    eb = estado_do_blog(["2026-10-03_legal.json"],
                        [{"etiqueta": "Legal e financiamento", "data": "2026-10-04"}],
                        "2026-10-04")
    ok("pacote presente é 'pronto'", eb["legal"]["pacote"] == "pronto")
    ok("pacote ausente é 'atrasado'", eb["saude"]["pacote"] == "atrasado")
    ok("texto publicado aparece com a data", eb["legal"]["ultimo"] == "2026-10-04")
    ok("linha sem texto é nomeada, não zerada", eb["saude"]["texto"] == "sem texto")
    ok("a linha do blog não bloqueia nada: ela só descreve",
       set(eb) == {"legal", "saude"})
    ok("a governança diz por que o painel existe", "não rodou" in GOV or "NÃO rodou" in GOV)

    # A2-26: a linha que falta é recuperável — conclusão real da API, trabalho pelo marcador.
    execs = [{"elo": "diarios", "noite": "2026-10-08", "inicio": "01:09", "fim": "03:32",
              "conclusao": "failure"},
             {"elo": "juiz", "noite": "2026-10-08", "inicio": "05:27", "fim": "05:30",
              "conclusao": "failure"}]
    faltam = linhas_que_faltam(execs, {("juiz", "2026-10-08", "05:27")},
                               lambda elo, n: elo == "diarios")
    ok("só a linha que falta entra", len(faltam) == 1 and faltam[0]["elo"] == "diarios")
    ok("falha COM marcador conta como trabalho feito", faltam[0].get("trabalhou") is True)
    faltam2 = linhas_que_faltam(
        [{"elo": "sinais", "noite": "2026-10-08", "inicio": "01:12", "fim": "01:13",
          "conclusao": "cancelled"}], set(), lambda elo, n: False)
    ok("cancelado sem marcador NÃO conta como trabalho",
       faltam2 and faltam2[0].get("trabalhou") is False)
    ok("as chaves do painel saem do documento",
       chaves_do_painel({"noites": [{"elo": "juiz", "noite": "2026-10-08", "inicio": "05:27"}]})
       == {("juiz", "2026-10-08", "05:27")})
    ok("documento vazio não quebra", chaves_do_painel({}) == set()
       and linhas_que_faltam([], set(), lambda e, n: False) == [])

    import dis
    nomes = set()
    for nome_obj, obj in list(globals().items()):
        # `recuperar_da_api` e `_execucoes_da_api` são portas de I/O declaradas, como
        # `registrar`: a trava vale para as funções PURAS.
        if nome_obj in ("_autoteste", "main", "registrar", "recuperar_da_api",
                        "_execucoes_da_api"):
            continue
        codigo = getattr(obj, "__code__", None)
        if codigo is not None:
            nomes |= {i.argval for i in dis.get_instructions(codigo) if isinstance(i.argval, str)}
    ok("trava estrutural: as funções puras não escrevem",
       not ({"gravar", "gravar_em", "write_text"} & nomes))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else f"✓ AUTOTESTE OK — {len(_casos_contados)} casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def linhas_que_faltam(execucoes: list, ja_no_painel: set, tem_marcador) -> list:
    """As linhas que o painel não tem e a API sabe. Função pura.

    `execucoes` é [{"elo","noite","inicio","fim","conclusao"}] como a API as devolve;
    `ja_no_painel` é o conjunto de (elo, noite, inicio) já registrado; `tem_marcador(elo, noite)`
    diz se o elo gravou `.feito` — é ele que distingue "falhou depois de trabalhar" de "foi
    cancelado antes de coletar", e a distinção é o que a regra 3 exige.

    08/10/2026 (A2-26): a linha era gravada pelo PRÓPRIO elo, antes do push, com `job.status`
    ainda `success`. O painel da `main` ficou com 138 linhas, todas `success`, e os seis elos que
    perderam o commit de 07→08 não têm linha — ela estava no commit perdido.
    """
    fora = []
    for e in execucoes or []:
        elo = str((e or {}).get("elo") or "")
        noite = str((e or {}).get("noite") or "")
        inicio = str((e or {}).get("inicio") or "")
        if not elo or not noite:
            continue
        if (elo, noite, inicio) in (ja_no_painel or set()):
            continue
        fora.append(linha(elo, noite, inicio, str((e or {}).get("fim") or inicio),
                          str((e or {}).get("conclusao") or "desconhecida"),
                          bool(tem_marcador(elo, noite))))
    return fora


def chaves_do_painel(doc: dict) -> set:
    """(elo, noite, inicio) de tudo o que já está no painel. Função pura."""
    fora = set()
    for l in (doc or {}).get("noites") or []:
        fora.add((str((l or {}).get("elo") or ""), str((l or {}).get("noite") or ""),
                  str((l or {}).get("inicio") or "")))
    return fora


def recuperar_da_api(noite: str = "", listar=None) -> dict:
    """Escreve no painel as linhas que faltam, lendo a API. ESCREVE.

    `listar` é injetável para teste; em uso real é `_execucoes_da_api`.
    """
    from coletores_base import gravar, ler
    doc = ler(ARQUIVO) or {"_governanca": GOV, "noites": []}
    execucoes = (listar or _execucoes_da_api)(noite)
    faltam = linhas_que_faltam(execucoes, chaves_do_painel(doc),
                              lambda elo, n: (RAIZ / f"data/noite/{n}/{elo}.feito").exists())
    if not faltam:
        print(f"· painel em dia para a noite de {noite or 'corrente'}")
        return doc
    doc.setdefault("noites", []).extend(faltam)
    doc["noites"] = doc["noites"][-400:]
    gravar(ARQUIVO, doc)
    for l in faltam:
        print(f"  + {l['elo']} · {l['noite']} · {l['conclusao']} · trabalhou={l.get('trabalhou')}")
    print(f"· {len(faltam)} linha(s) recuperada(s) da API")
    return doc


def _execucoes_da_api(noite: str = "") -> list:
    """As execuções dos elos na janela, pela API do GitHub. Só lê."""
    import json as _json
    import subprocess
    fora = []
    for elo in ELOS:
        if elo == "publicar":
            wf = "publicar_dados.yml"
        elif elo == "sinais":
            wf = "noturno_sinais.yml"
        else:
            wf = f"noturno_{elo}.yml"
        try:
            saida = subprocess.run(
                ["gh", "run", "list", "--workflow", wf, "--branch", "main", "--limit", "12",
                 "--json", "createdAt,updatedAt,conclusion,status"],
                cwd=RAIZ, capture_output=True, text=True, timeout=120).stdout
            bruto = _json.loads(saida) if saida.strip() else []
        except Exception:
            bruto = []
        for r in bruto:
            criado = str(r.get("createdAt") or "")
            if not criado:
                continue
            n = criado[:10] if criado[11:13] >= f"{JANELA_UTC[0]:02d}" else ""
            if not n:
                continue
            if noite and n != noite:
                continue
            fora.append({"elo": elo, "noite": n, "inicio": criado[11:16],
                         "fim": str(r.get("updatedAt") or criado)[11:16],
                         "conclusao": str(r.get("conclusion") or r.get("status") or "")})
    return fora


def registrar(elo: str, inicio: str, conclusao: str, feito: bool = None) -> dict:
    """Acrescenta a linha desta execução ao painel. Escreve."""
    from coletores_base import gravar, ler, hoje_editorial
    agora = dt.datetime.utcnow()
    fim = agora.strftime("%H:%M")
    # A NOITE é a data de abertura da janela: um elo que termina às 03h UTC pertence à noite que
    # começou no dia anterior, em Brasília. Sem isso, a mesma noite apareceria partida em dois dias.
    noite = (agora.date() if agora.hour >= JANELA_UTC[0] else
             agora.date() - dt.timedelta(days=1)).isoformat()
    doc = ler(ARQUIVO) or {"_governanca": GOV, "noites": []}
    doc.setdefault("_governanca", GOV)
    nova = linha(elo, noite, inicio or fim, fim, conclusao, feito)
    doc.setdefault("noites", []).append(nova)
    doc["noites"] = doc["noites"][-400:]
    gravar(ARQUIVO, doc)
    return nova


def main() -> int:
    if "--autoteste" in sys.argv:
        return _autoteste()
    from coletores_base import ler
    if "--registrar" in sys.argv:
        i = sys.argv.index("--registrar")
        elo = sys.argv[i + 1]
        inicio = sys.argv[sys.argv.index("--inicio") + 1] if "--inicio" in sys.argv else None
        conclusao = sys.argv[sys.argv.index("--conclusao") + 1] if "--conclusao" in sys.argv else ""
        # `--feito` é o elo dizendo "eu coletei", gravado antes do commit. Ele vence a conclusão.
        feito = True if "--feito" in sys.argv else (False if "--nao-feito" in sys.argv else None)
        nova = registrar(elo, inicio, conclusao, feito)
        print(f"painel da noite: {nova['elo']} {nova['inicio']}→{nova['fim']} "
              f"({nova['minutos']} min) · dentro da janela: "
              f"{'sim' if nova['dentro_da_janela'] else 'NÃO'}")
        return 0

    doc = ler(ARQUIVO) or {}
    linhas = doc.get("noites") or []
    if not linhas:
        print("painel da noite: sem linha registrada ainda (vale a partir da próxima corrente)")
        return 0
    ultima = max(l.get("noite", "") for l in linhas)
    desta = [l for l in linhas if l.get("noite") == ultima]
    print(f"noite de {ultima}:")
    for l in desta:
        print(f"   {l['elo']:12s} {l['inicio']}→{l['fim']}  {str(l['minutos']) + ' min':>8s}  "
              f"{'na janela' if l['dentro_da_janela'] else 'FORA DA JANELA':14s}  {l['conclusao']}")
    print("   previsto × iniciado:")
    for x in previsto_x_iniciado(linhas, ultima):
        quando = x["iniciado"] or "não iniciou"
        atraso = f"+{x['atraso_min']} min" if x["atraso_min"] is not None else ""
        print(f"     {x['elo']:12s} {x['previsto']} → {quando:12s} {atraso}")
    faltaram = elos_que_faltaram(linhas, ultima)
    fora = [l["elo"] for l in desta if not l["dentro_da_janela"]]
    if faltaram:
        print(f"   elo(s) que não rodaram: {', '.join(faltaram)}")
    if "--recuperar-da-api" in sys.argv:
        n = ""
        if "--noite" in sys.argv:
            i = sys.argv.index("--noite")
            n = sys.argv[i + 1] if i + 1 < len(sys.argv) else ""
        recuperar_da_api(n)
        return 0

    if "--portao" in sys.argv:
        # 04/10/2026: a noite que NÃO ABRIU é um caso à parte, e mais grave que elo faltando. Nas
        # noites de 02→03 e 03→04 o cron não disparou e nada acusou: o painel não tinha linha
        # nenhuma, então "elos que faltaram" seria a lista inteira, sem dizer que o problema foi a
        # abertura. Aqui ela é nomeada, porque é ela que tem conserto próprio (reserva e vigia).
        if not noite_abriu(linhas, ultima):
            print(f"✗ PAINEL DA NOITE: a noite de {ultima} não abriu — o elo "
                  f"`{ELOS[0]}` não tem registro. Ver o vigia da abertura "
                  f"(.github/workflows/vigia_da_abertura.yml).")
            return 1
        if faltaram:
            print(f"✗ PAINEL DA NOITE: {len(faltaram)} elo(s) sem registro na noite de {ultima}: "
                  f"{', '.join(faltaram)}")
            return 1
        if fora:
            print(f"⚠ PAINEL DA NOITE: {len(fora)} elo(s) terminaram fora da janela: "
                  f"{', '.join(fora)}")
        print(f"✓ PAINEL DA NOITE OK — os {len(ELOS)} elos da corrente rodaram na noite de {ultima}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
