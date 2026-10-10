#!/usr/bin/env python3
"""
scripts/despachar_temporizadores.py — dispara o que está DEVIDO, venha o relógio de onde vier
==============================================================================================
Item 2 do `HANDOVER_garantia_dos_temporizadores_04-10-2026.md` (rev. 2).

O PRINCÍPIO, QUE É DA EDITORIA
------------------------------
*Nada roda "às 22h07". Tudo roda quando está DEVIDO, e quem confere são vários observadores
independentes.* O cron do GitHub é de melhor esforço — a abertura da noite falhou três vezes em
cinco dias —, e o #544 pôs minuto fora do pico, reserva e vigia **dentro do mesmo agendador**. Este
arquivo é o que torna os relógios substituíveis: ele lê `config/temporizadores.json`, pergunta à API
o que já rodou na janela de hoje, e dispara o que falta.

OS QUATRO OBSERVADORES, E POR QUE SÃO QUATRO
--------------------------------------------
  (a) cron do GitHub a cada 20 min, em minutos fora do pico;
  (b) **relógio da nuvem do Claude** — uma rotina que escreve `tick.txt` no ramo `relogio`, e o
      push dispara o despachante por evento `push`, NÃO por cron. É o relógio que não depende do
      agendador do GitHub;
  (c) oportunista: todo workflow agendado chama o despachante no primeiro passo — cada execução de
      qualquer coisa vira um tique;
  (d) vigia da abertura, que já existia.

Cada um chama a mesma função. Ela é idempotente por construção: só dispara o que não tem execução
na janela, e o `concurrency` por temporizador impede dois disparos simultâneos do mesmo.

A REGRA DE 27/09 CONTINUA VALENDO: nenhum commit automático na `main` durante o dia. O despachante
não dispara fora da janela declarada de cada temporizador, e as janelas respeitam isso.

USO
  python3 scripts/despachar_temporizadores.py --autoteste
  python3 scripts/despachar_temporizadores.py --origem github-cron
  python3 scripts/despachar_temporizadores.py --origem relogio-claude
  python3 scripts/despachar_temporizadores.py --so-ler-e-despachar   # modo oportunista, silencioso
  python3 scripts/despachar_temporizadores.py --relatorio            # não dispara nada
"""
import datetime as dt
import json
import pathlib
import subprocess
import time
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

REGISTRO = RAIZ / "config" / "temporizadores.json"
ORIGENS = ("github-cron", "relogio-claude", "oportunista", "vigia", "manual")
SILENCIO_DO_RELOGIO_MIN = 130
REPOSITORIO_PRIVADO = "monitorelnino/robo-registro"


# ---------------------------------------------------------------- funções puras
def hora_utc(agora: dt.datetime) -> str:
    """"HH:MM" em UTC. Função pura."""
    return agora.strftime("%H:%M")


def na_janela(agora: dt.datetime, janela: dict) -> bool:
    """O instante está na janela do temporizador? Função pura.

    Janela que atravessa a meia-noite é aceita (início maior que fim), porque a janela noturna do
    projeto faz exatamente isso em horário de Brasília.
    """
    inicio = str((janela or {}).get("inicio_utc") or "")
    fim = str((janela or {}).get("fim_utc") or "")
    if not (inicio and fim):
        return False
    h = hora_utc(agora)
    return (inicio <= h < fim) if inicio <= fim else (h >= inicio or h < fim)


def inicio_da_janela(agora: dt.datetime, janela: dict) -> str:
    """O instante ISO em que a janela corrente começou. Função pura.

    É o que se passa à API para perguntar "houve execução NESTA janela?". Numa janela que atravessa
    a meia-noite e com o relógio já do outro lado, o início é de ontem.
    """
    inicio = str((janela or {}).get("inicio_utc") or "00:00")
    h, m = (int(x) for x in inicio.split(":")[:2])
    alvo = agora.replace(hour=h, minute=m, second=0, microsecond=0)
    if alvo > agora:
        alvo -= dt.timedelta(days=1)
    return alvo.isoformat() + "Z"


def e_dia_previsto(cron: str, agora: dt.datetime) -> bool:
    """Hoje é um dos dias em que este cron roda? Função pura.

    Sem isto, o despachante julgava "devido" tudo o que não tivesse rodado HOJE — e passava a
    querer disparar, num domingo, a auditoria que é de segunda. Medido na primeira execução real.
    Campos 3 e 5 do cron (dia do mês e dia da semana), com `*`, listas e intervalos; passo (`*/n`)
    e nomes de mês não aparecem nos nossos crons e, se aparecerem, a função devolve True — não
    disparar à toa é melhor que não disparar nunca, mas deixar de reconhecer um campo não pode
    virar silêncio: o portão do registro cobra o cron declarado, e ele é lido daqui.
    """
    partes = str(cron or "").split()
    if len(partes) < 5:
        return True

    def casa(campo: str, valor: int, domingo_zero_e_sete: bool = False) -> bool:
        if campo.strip() == "*":
            return True
        for pedaco in campo.split(","):
            pedaco = pedaco.strip()
            if "/" in pedaco:
                return True
            if "-" in pedaco:
                try:
                    a, b = (int(x) for x in pedaco.split("-"))
                except ValueError:
                    return True
                faixa = set(range(a, b + 1))
            else:
                try:
                    faixa = {int(pedaco)}
                except ValueError:
                    return True
            if domingo_zero_e_sete and (0 in faixa or 7 in faixa):
                faixa |= {0, 7}
            if valor in faixa:
                return True
        return False

    dia_do_mes = casa(partes[2], agora.day)
    # No cron, domingo é 0 e também 7; `weekday()` do Python dá 0 para segunda.
    dia_da_semana = casa(partes[4], (agora.weekday() + 1) % 7, domingo_zero_e_sete=True)
    # A regra do cron: com os dois campos restritos, basta UM casar.
    if partes[2].strip() != "*" and partes[4].strip() != "*":
        return dia_do_mes or dia_da_semana
    return dia_do_mes and dia_da_semana


def esta_devido(temporizador: dict, execucoes: list, agora: dt.datetime) -> bool:
    """O temporizador está devido AGORA? Função pura.

    `execucoes` são as execuções do workflow com `createdAt` em ISO. Devido = está na janela e não
    há execução criada depois do início desta janela. Execução em andamento CONTA — é o que impede
    o segundo observador de disparar o que o primeiro acabou de começar.
    """
    janela = temporizador.get("janela") or {}
    if not na_janela(agora, janela):
        return False
    if not e_dia_previsto(temporizador.get("cron_primario"), agora):
        return False
    desde = inicio_da_janela(agora, janela)
    # 10/10/2026: execução cancelada, pulada ou estourada NÃO conta (regra 3 do CLAUDE.md). Na
    # abertura de 10/10 o `diarios / coletar` foi cancelado na fila às 01:14, sem passo executado,
    # e o despachante das 02:26 viu "houve execução na janela" e não redisparou: os diários só
    # rodaram às 07:42, pelo cron do próprio elo, e entraram na `main` às 09:11.
    return not any(str(e.get("createdAt") or "") >= desde and not nao_trabalhou(e)
                   for e in (execucoes or []))


NAO_TRABALHARAM = ("cancelled", "skipped", "timed_out", "startup_failure")


def nao_trabalhou(execucao: dict) -> bool:
    """A execução terminou sem trabalhar (cancelada, pulada, estourada)? Função pura."""
    return (str(execucao.get("status") or "").lower() == "completed"
            and str(execucao.get("conclusion") or "").lower() in NAO_TRABALHARAM)


# 10/10/2026 (janela A, item 2): A RESERVA DOS ELOS. O temporizador só conhece o elo que tem cron;
# descoberta, evidências e juiz são acionados pelo término do anterior, e quando o run deles é
# cancelado na fila ou pulado (porque o anterior não terminou em sucesso) ninguém os refazia.
# Elo, workflow, e o elo que precisa ter trabalhado antes dele.
ELOS_DA_RESERVA = (
    ("diarios", "noturno_diarios.yml", None),
    ("descoberta", "noturno_descoberta.yml", "diarios"),
    ("evidencias", "noturno_evidencias.yml", "descoberta"),
    ("juiz", "noturno_juiz.yml", "evidencias"),
    ("triagem", "noturno_triagem.yml", None),
)
TENTATIVAS_DA_RESERVA = 3
ULTIMO_DISPARO_DA_RESERVA = "08:00"   # depois disso o elo não termina antes das 09:00 UTC
ABERTOS = ("queued", "requested", "waiting", "pending", "in_progress")


def plano_da_reserva(execucoes_por_workflow: dict, feitos: set, agora: dt.datetime,
                     ja_no_plano=(), elos=ELOS_DA_RESERVA) -> list:
    """No máximo UM elo da corrente a refazer agora. Função pura.

    Refaz o primeiro elo, na ordem da corrente, que: não tem marcador `.feito` nesta noite; já foi
    tentado na janela e nenhuma tentativa está aberta (na fila ou rodando); tem o elo anterior
    feito; e ainda não gastou as tentativas. Um por vez, porque o seguinte depende do anterior —
    e o próprio término do refeito aciona o seguinte pela corrente.
    """
    if not na_janela(agora, {"inicio_utc": "01:00", "fim_utc": ULTIMO_DISPARO_DA_RESERVA}):
        return []
    desde = inicio_da_janela(agora, {"inicio_utc": "01:00", "fim_utc": "09:00"})
    for elo, workflow, anterior in elos:
        if elo in feitos or workflow in set(ja_no_plano):
            continue
        if anterior and anterior not in feitos:
            continue
        na_noite = [e for e in (execucoes_por_workflow or {}).get(workflow) or []
                    if str(e.get("createdAt") or "") >= desde]
        if not na_noite:
            continue          # nunca tentado: é do temporizador ou da corrente, não da reserva
        if any(str(e.get("status") or "").lower() in ABERTOS for e in na_noite):
            continue
        if len(na_noite) >= TENTATIVAS_DA_RESERVA:
            continue
        return [{"id": f"reserva-{elo}", "workflow": workflow, "entradas": {},
                 "chave": f"reserva-{elo}@{desde}", "atraso_min": 0,
                 "alem_da_tolerancia": False, "gravidade": "alta", "elo": elo}]
    return []


def atraso_min(temporizador: dict, agora: dt.datetime) -> int:
    """Minutos desde o horário primário previsto, dentro da janela. Função pura."""
    cron = str(temporizador.get("cron_primario") or "")
    partes = cron.split()
    if len(partes) < 2 or not partes[0].isdigit() or not partes[1].isdigit():
        return 0
    alvo = agora.replace(hour=int(partes[1]), minute=int(partes[0]), second=0, microsecond=0)
    # Horário previsto que ainda não chegou hoje significa atraso ZERO: o temporizador não está
    # atrasado, está por vir. Recuar um dia aqui transformava "faltam sete minutos" em "atrasado
    # 1.433 minutos", e com isso o alarme dispararia na janela inteira, todas as noites.
    if alvo > agora:
        return 0
    return int((agora - alvo).total_seconds() // 60)


def passou_da_tolerancia(temporizador: dict, agora: dt.datetime) -> bool:
    """O atraso passou da tolerância declarada? Função pura."""
    tol = temporizador.get("tolerancia_atraso_min")
    return bool(tol) and atraso_min(temporizador, agora) > int(tol)


def relogio_silencioso(ultimo_tique_iso: str, agora: dt.datetime,
                       limite_min=SILENCIO_DO_RELOGIO_MIN) -> bool:
    """O relógio da nuvem do Claude está silencioso? Função pura.

    Sem nenhum tique conhecido, responde True: rotina que nunca tiquetaqueou é indistinguível de
    rotina desligada, e a editoria precisa saber nos dois casos.
    """
    if not ultimo_tique_iso:
        return True
    try:
        quando = dt.datetime.fromisoformat(str(ultimo_tique_iso).replace("Z", ""))
    except ValueError:
        return True
    return (agora - quando).total_seconds() / 60 > limite_min


def chave_de_idempotencia(temporizador: dict, agora: dt.datetime) -> str:
    """A chave da janela, para o disparo não se repetir dentro dela. Função pura."""
    return f"{temporizador.get('id')}@{inicio_da_janela(agora, temporizador.get('janela') or {})}"


def plano_de_disparo(registro: dict, execucoes_por_workflow: dict, agora: dt.datetime) -> list:
    """O que disparar agora, na ordem do registro. Função pura.

    Dois temporizadores podem apontar para o MESMO workflow (a publicação da manhã e a da noite): a
    janela é que os distingue, e por isso a pergunta é por janela, não por workflow.
    """
    fora = []
    for t in (registro or {}).get("temporizadores") or []:
        execucoes = (execucoes_por_workflow or {}).get(t.get("workflow")) or []
        if esta_devido(t, execucoes, agora):
            fora.append({"id": t.get("id"), "workflow": t.get("workflow"),
                         "entradas": ((t.get("recuperacao") or {}).get("entradas") or {}),
                         "chave": chave_de_idempotencia(t, agora),
                         "atraso_min": atraso_min(t, agora),
                         "alem_da_tolerancia": passou_da_tolerancia(t, agora),
                         "gravidade": t.get("gravidade")})
    return fora


def workflow_rejeitado(execucoes: list) -> bool:
    """O GitHub rejeitou o arquivo deste workflow? Função pura.

    04/10/2026 (20:30): `busca_web_cadencia.yml` e `auditoria_seguranca.yml` ficaram cinco horas
    rejeitados, e o despachante não tinha como saber — ele disparava, o GitHub criava um run de
    ZERO jobs com `failure`, e para o despachante aquilo era "rodou". O sintoma é observável: run
    `failure` sem job nenhum. Rejeição é defeito de ARQUIVO, não de horário, e nenhum disparo a
    conserta: por isso ela vira alarme de gravidade alta, sempre.
    """
    for e in (execucoes or [])[:1]:
        if e.get("conclusion") == "failure" and int(e.get("jobs") or 0) == 0:
            return True
    return False


def precisa_alarmar(item: dict, tentou_recuperar: bool) -> bool:
    """Abre-se Issue para a editoria? Função pura.

    Gravidade alta alarma na primeira falha de recuperação; as outras, só além da tolerância. O
    alarme é sobre a RECUPERAÇÃO ter falhado — temporizador atrasado que o despachante conseguiu
    disparar não é problema, é o sistema funcionando.

    A exceção é o workflow REJEITADO pelo GitHub: ali o disparo "funciona" e não produz nada, então
    disparar não é recuperar. Alarma sempre, com gravidade alta.
    """
    if item.get("rejeitado"):
        return True
    if tentou_recuperar:
        return False
    if item.get("gravidade") == "alta":
        return True
    return bool(item.get("alem_da_tolerancia"))


# ---------------------------------------------------------------- portas de I/O
def _gh(args: list) -> str:
    try:
        r = subprocess.run(["gh"] + args, cwd=RAIZ, capture_output=True, text=True, timeout=120)
        return r.stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def execucoes_de(workflow: str, limite: int = 20) -> list:
    """As execuções recentes do workflow, pela API."""
    # 08/10/2026 (A2-17): `--branch main`. Sem isso, um disparo de ensaio contava como execução
    # da rotina e o despachante não recuperava o temporizador que de fato não rodou.
    saida = _gh(["run", "list", "--workflow", workflow, "--branch", "main", "--limit", str(limite),
                 "--json", "databaseId,createdAt,status,conclusion,event,workflowDatabaseId"])
    try:
        bruto = json.loads(saida) if saida.strip() else []
    except json.JSONDecodeError:
        return []
    # A contagem de jobs só é consultada na execução MAIS RECENTE e só quando ela falhou: é o que
    # distingue "o GitHub rejeitou o arquivo" (zero jobs) de "o teste reprovou" (jobs > 0). Uma
    # chamada por workflow, não vinte.
    if bruto and bruto[0].get("conclusion") == "failure":
        jb = _gh(["api", f"repos/{{owner}}/{{repo}}/actions/runs/{bruto[0]['databaseId']}/jobs",
                  "--jq", ".total_count"])
        bruto[0]["jobs"] = int(jb.strip()) if jb.strip().isdigit() else 1
    return bruto


def elos_feitos(agora: dt.datetime) -> set:
    """Os elos com marcador nesta noite — na árvore ou no artefato (`marcador_de_elo.py`)."""
    sys.path.insert(0, str(RAIZ / "scripts"))
    from janela_da_noite import noite_de
    from marcador_de_elo import artefatos_do_repositorio, trabalhou
    noite = noite_de(agora)
    artefatos = artefatos_do_repositorio()
    return {elo for elo, _, _ in ELOS_DA_RESERVA
            if trabalhou(elo, noite, lambda c: (RAIZ / c).is_file(), artefatos)[0]}


def disparar(item: dict, origem: str) -> bool:
    """Dispara o workflow por workflow_dispatch. Devolve se o comando foi aceito."""
    args = ["workflow", "run", item["workflow"]]
    for k, v in (item.get("entradas") or {}).items():
        args += ["-f", f"{k}={v}"]
    # 08/10/2026 (A2-07): "aceito" era uma corrida. O GitHub leva alguns segundos para registrar
    # o run novo, então comparar a lista imediatamente depois do disparo dizia "não produziu
    # execução" para disparo que tinha funcionado — e o despachante abria Issue à toa, ou tentava
    # de novo e duplicava trabalho. Agora espera o id MUDAR, até 30 segundos.
    antes = _gh(["run", "list", "--workflow", item["workflow"], "--branch", "main", "--limit", "1",
                 "--json", "databaseId"])
    _gh(args)
    aceito = False
    for _ in range(10):
        depois = _gh(["run", "list", "--workflow", item["workflow"], "--branch", "main",
                      "--limit", "1", "--json", "databaseId"])
        if depois and depois != antes:
            aceito = True
            break
        time.sleep(3)
    print(f"  {'→' if aceito else '✗'} {item['id']} ({item['workflow']}) · atraso "
          f"{item['atraso_min']} min · origem {origem}"
          + ("" if aceito else " · o disparo não produziu execução nova"))
    return aceito


def abrir_issue(item: dict) -> None:
    """Abre Issue no repositório privado — o GitHub avisa a editoria por e-mail, sem credencial
    nova. A Issue é sobre a RECUPERAÇÃO ter falhado, não sobre o atraso."""
    titulo = f"Temporizador atrasado: {item['id']}"
    corpo = (f"O temporizador `{item['id']}` ({item['workflow']}) está atrasado "
             f"{item['atraso_min']} minutos e a recuperação automática não produziu execução.\n\n"
             f"- gravidade: {item.get('gravidade')}\n"
             f"- janela: {item.get('chave')}\n\n"
             f"Recuperação à mão: `gh workflow run {item['workflow']}`.\n")
    existentes = _gh(["issue", "list", "--repo", REPOSITORIO_PRIVADO, "--label", "temporizador",
                      "--state", "open", "--search", item["id"], "--json", "number"])
    if existentes.strip() and existentes.strip() != "[]":
        print(f"  [alarme] Issue já aberta para {item['id']}")
        return
    _gh(["issue", "create", "--repo", REPOSITORIO_PRIVADO, "--title", titulo, "--body", corpo,
         "--label", "temporizador"])
    print(f"  [alarme] Issue aberta: {titulo}")


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

    d = dt.datetime
    noturna = {"inicio_utc": "01:00", "fim_utc": "09:00"}
    atravessa = {"inicio_utc": "22:00", "fim_utc": "06:00"}

    ok("dentro da janela simples", na_janela(d(2026, 10, 4, 2, 40), noturna))
    ok("fora da janela simples", not na_janela(d(2026, 10, 4, 12, 0), noturna))
    ok("janela que atravessa a meia-noite vale dos dois lados",
       na_janela(d(2026, 10, 4, 23, 0), atravessa) and na_janela(d(2026, 10, 4, 3, 0), atravessa))
    ok("janela sem início não vale", not na_janela(d(2026, 10, 4, 2, 0), {}))

    ok("o início da janela é de hoje quando já passou",
       inicio_da_janela(d(2026, 10, 4, 2, 40), noturna) == "2026-10-04T01:00:00Z")
    ok("o início da janela é de ontem quando ainda não chegou",
       inicio_da_janela(d(2026, 10, 4, 0, 30), noturna) == "2026-10-03T01:00:00Z")

    t = {"id": "abertura", "workflow": "a.yml", "janela": noturna, "cron_primario": "7 1 * * *",
         "tolerancia_atraso_min": 60, "gravidade": "alta",
         "recuperacao": {"entradas": {}}}
    agora = d(2026, 10, 4, 2, 40)
    ok("sem execução na janela, está devido", esta_devido(t, [], agora))
    ok("com execução na janela, NÃO está devido",
       not esta_devido(t, [{"createdAt": "2026-10-04T01:10:00Z"}], agora))
    ok("execução de ontem não conta",
       esta_devido(t, [{"createdAt": "2026-10-03T01:10:00Z"}], agora))
    ok("execução EM ANDAMENTO conta, e é isso que impede o disparo duplo",
       not esta_devido(t, [{"createdAt": "2026-10-04T02:30:00Z", "status": "in_progress"}], agora))
    ok("fora da janela nunca está devido", not esta_devido(t, [], d(2026, 10, 4, 12, 0)))

    # 2026-10-04 é um domingo; 2026-10-05, uma segunda.
    semanal = dict(t, id="segunda", cron_primario="0 8 * * 1",
                   janela={"inicio_utc": "08:00", "fim_utc": "20:00"})
    ok("temporizador de segunda NÃO está devido no domingo",
       not esta_devido(semanal, [], d(2026, 10, 4, 15, 0)))
    ok("temporizador de segunda está devido na segunda",
       esta_devido(semanal, [], d(2026, 10, 5, 15, 0)))
    ok("domingo é 0 e também 7 no cron",
       e_dia_previsto("10 3 * * 0", d(2026, 10, 4, 3, 30))
       and e_dia_previsto("10 3 * * 7", d(2026, 10, 4, 3, 30)))
    ok("dia do mês é respeitado",
       e_dia_previsto("40 3 1,15 * *", d(2026, 10, 15, 3, 45))
       and not e_dia_previsto("40 3 1,15 * *", d(2026, 10, 4, 3, 45)))
    ok("cron diário vale todo dia", e_dia_previsto("7 1 * * *", d(2026, 10, 4, 1, 10)))
    ok("cron ilegível não vira silêncio: vale hoje", e_dia_previsto("", d(2026, 10, 4, 1, 10)))

    ok("o atraso é contado do horário primário", atraso_min(t, agora) == 93)
    ok("antes do horário primário o atraso é zero", atraso_min(t, d(2026, 10, 4, 1, 0)) == 0)
    ok("93 minutos passam da tolerância de 60", passou_da_tolerancia(t, agora))
    ok("30 minutos não passam", not passou_da_tolerancia(t, d(2026, 10, 4, 1, 37)))

    ok("a chave de idempotência é por janela",
       chave_de_idempotencia(t, agora) == "abertura@2026-10-04T01:00:00Z"
       and chave_de_idempotencia(t, d(2026, 10, 5, 2, 0)) != chave_de_idempotencia(t, agora))

    reg = {"temporizadores": [t, dict(t, id="outro", workflow="b.yml")]}
    plano = plano_de_disparo(reg, {"a.yml": [{"createdAt": "2026-10-04T01:10:00Z"}]}, agora)
    ok("o plano traz só o que está devido",
       [x["id"] for x in plano] == ["outro"])
    ok("o plano carrega o atraso e a gravidade",
       plano[0]["atraso_min"] == 93 and plano[0]["gravidade"] == "alta")
    dois_no_mesmo = {"temporizadores": [
        dict(t, id="manha", workflow="p.yml", janela={"inicio_utc": "09:00", "fim_utc": "11:00"}),
        dict(t, id="noite", workflow="p.yml", janela=noturna)]}
    plano2 = plano_de_disparo(dois_no_mesmo, {"p.yml": []}, agora)
    ok("dois temporizadores no mesmo workflow se distinguem pela janela",
       [x["id"] for x in plano2] == ["noite"])

    ok("execução CANCELADA na janela não conta: o temporizador volta a estar devido",
       esta_devido(t, [{"createdAt": "2026-10-04T01:10:00Z", "status": "completed",
                        "conclusion": "cancelled"}], agora))
    ok("execução pulada também não conta",
       esta_devido(t, [{"createdAt": "2026-10-04T01:10:00Z", "status": "completed",
                        "conclusion": "skipped"}], agora))
    ok("execução que falhou conta (pode ter coletado; o marcador decide na reserva)",
       not esta_devido(t, [{"createdAt": "2026-10-04T01:10:00Z", "status": "completed",
                            "conclusion": "failure"}], agora))
    canc = {"createdAt": "2026-10-10T01:10:45Z", "status": "completed", "conclusion": "cancelled"}
    aberto = {"createdAt": "2026-10-10T02:00:00Z", "status": "queued", "conclusion": ""}
    t_r = d(2026, 10, 10, 2, 26)    # a hora real do despachante que não refez os diários
    r1 = plano_da_reserva({"noturno_diarios.yml": [canc]}, set(), t_r)
    ok("pendente cancelado pela fila é refeito pela reserva (abertura de 10/10)",
       [x["elo"] for x in r1] == ["diarios"])
    ok("a reserva não duplica o que o temporizador já vai disparar",
       plano_da_reserva({"noturno_diarios.yml": [canc]}, set(), t_r,
                        ja_no_plano=["noturno_diarios.yml"]) == [])
    ok("elo com marcador não é refeito",
       plano_da_reserva({"noturno_diarios.yml": [canc]}, {"diarios"}, t_r) == [])
    ok("elo com tentativa aberta (na fila) não é refeito por cima",
       plano_da_reserva({"noturno_diarios.yml": [canc, aberto]}, set(), t_r) == [])
    pulada = {"createdAt": "2026-10-10T01:14:46Z", "status": "completed", "conclusion": "skipped"}
    ok("elo da corrente pulado só é refeito depois de o anterior ter trabalhado",
       plano_da_reserva({"noturno_descoberta.yml": [pulada]}, set(), t_r) == []
       and [x["elo"] for x in plano_da_reserva({"noturno_descoberta.yml": [pulada]},
                                               {"diarios"}, t_r)] == ["descoberta"])
    ok("um elo por vez, na ordem da corrente",
       [x["elo"] for x in plano_da_reserva({"noturno_diarios.yml": [canc],
                                            "noturno_triagem.yml": [canc]}, set(), t_r)]
       == ["diarios"])
    ok("a reserva desiste depois de três tentativas",
       plano_da_reserva({"noturno_diarios.yml": [canc] * 3}, set(), t_r) == [])
    ok("a reserva não dispara depois das 08:00 UTC (não terminaria na janela)",
       plano_da_reserva({"noturno_diarios.yml": [canc]}, set(), d(2026, 10, 10, 8, 30)) == [])
    ok("elo nunca tentado não é da reserva",
       plano_da_reserva({}, {"diarios"}, t_r) == [])

    ok("relógio sem tique é silencioso", relogio_silencioso("", agora))
    ok("tique de 10 minutos não é silêncio",
       not relogio_silencioso("2026-10-04T02:30:00", agora))
    ok("tique de três horas é silêncio", relogio_silencioso("2026-10-03T23:00:00", agora))
    ok("tique ilegível é tratado como silêncio", relogio_silencioso("ontem", agora))

    ok("última execução com falha e zero jobs é rejeição",
       workflow_rejeitado([{"conclusion": "failure", "jobs": 0}]))
    ok("falha com jobs não é rejeição",
       not workflow_rejeitado([{"conclusion": "failure", "jobs": 2}]))
    ok("rejeição no histórico não conta; só a última",
       not workflow_rejeitado([{"conclusion": "success", "jobs": 1},
                               {"conclusion": "failure", "jobs": 0}]))
    ok("workflow rejeitado alarma mesmo com o disparo aceito",
       precisa_alarmar({"rejeitado": True, "gravidade": "baixa"}, True))
    ok("recuperação que funcionou NÃO alarma",
       not precisa_alarmar({"gravidade": "alta", "alem_da_tolerancia": True}, True))
    ok("gravidade alta sem recuperação alarma na primeira",
       precisa_alarmar({"gravidade": "alta", "alem_da_tolerancia": False}, False))
    ok("gravidade baixa só alarma além da tolerância",
       not precisa_alarmar({"gravidade": "baixa", "alem_da_tolerancia": False}, False)
       and precisa_alarmar({"gravidade": "baixa", "alem_da_tolerancia": True}, False))

    ok("as origens declaradas são as cinco do handover",
       set(ORIGENS) == {"github-cron", "relogio-claude", "oportunista", "vigia", "manual"})

    import dis
    nomes = set()
    for nome_obj, obj in list(globals().items()):
        if nome_obj in ("_autoteste", "main", "disparar", "abrir_issue", "execucoes_de", "_gh",
                        "despachar", "elos_feitos"):
            continue
        codigo = getattr(obj, "__code__", None)
        if codigo is not None:
            nomes |= {i.argval for i in dis.get_instructions(codigo) if isinstance(i.argval, str)}
    ok("trava estrutural: as funções puras não disparam nada",
       not ({"run", "disparar", "abrir_issue", "write_text"} & nomes))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else f"✓ AUTOTESTE OK — {len(_casos_contados)} casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def despachar(origem: str, relatorio: bool = False, silencioso: bool = False) -> int:
    agora = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    reg = json.loads(REGISTRO.read_text(encoding="utf-8"))
    workflows = sorted({t.get("workflow") for t in reg.get("temporizadores") or []}
                       | {w for _, w, _ in ELOS_DA_RESERVA})
    execucoes = {w: execucoes_de(w) for w in workflows if w}
    plano = plano_de_disparo(reg, execucoes, agora)
    plano += plano_da_reserva(execucoes, elos_feitos(agora), agora,
                              ja_no_plano=[x["workflow"] for x in plano])

    if not silencioso:
        print(f"despachante · {hora_utc(agora)} UTC · origem {origem} · "
              f"{len(plano)} temporizador(es) devido(s)")
    if relatorio:
        for x in plano:
            print(f"  devido: {x['id']} ({x['workflow']}) · atraso {x['atraso_min']} min")
        return 0

    for item in plano:
        item["rejeitado"] = workflow_rejeitado(execucoes.get(item["workflow"]) or [])
        if item["rejeitado"]:
            print(f"  ✗ {item['id']} ({item['workflow']}): o GitHub REJEITOU o arquivo — a última "
                  f"execução falhou com zero jobs. Disparar não conserta isto.")
        aceito = disparar(item, origem) and not item["rejeitado"]
        if precisa_alarmar(item, aceito):
            abrir_issue(item)
    return 0


def main() -> int:
    argv = sys.argv[1:]
    if "--autoteste" in argv:
        return _autoteste()
    origem = argv[argv.index("--origem") + 1] if "--origem" in argv else "manual"
    if origem not in ORIGENS:
        print(f"✗ origem {origem!r} fora de {list(ORIGENS)}")
        return 1
    return despachar(origem, relatorio="--relatorio" in argv,
                     silencioso="--so-ler-e-despachar" in argv)


if __name__ == "__main__":
    sys.exit(main())
