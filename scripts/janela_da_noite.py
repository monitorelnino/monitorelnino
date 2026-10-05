#!/usr/bin/env python3
"""
scripts/janela_da_noite.py — a noite abre uma vez, mesmo que o cron falhe ou dispare duas
==========================================================================================
MEDIDO (central, 03/10/2026 02:30 UTC, e de novo em 04/10 02:40 UTC)
--------------------------------------------------------------------
A corrente não abriu. `noturno_diarios` tinha cron de 01:00 UTC e, às 02:40, não havia rodado: 1h40
de atraso e contando. Não é a primeira vez — em 30/09 o mesmo cron começou às 06:59, com 5h30 de
atraso, e morreu no teto. O cron do GitHub é de **melhor esforço**: sob carga ele atrasa e descarta,
e `:00`, `:10` e `:30` são justamente os minutos de pico, porque é onde todo mundo agenda.

A RESPOSTA, EM TRÊS PARTES, E POR QUE ELA PRECISA DESTE ARQUIVO
---------------------------------------------------------------
1. **Minuto fora do pico**: os crons passam a `:07`, `:23`, `:41`, `:53`.
2. **Cron de reserva**: a abertura ganha um segundo disparo meia hora depois do primeiro.
3. **Vigia**: às 02:07 UTC (23h07 de Brasília) um workflow leve confere se a noite abriu e, se não,
   dispara a corrente.

Dois disparos e um vigia só são seguros se a abertura for **idempotente** — e é isso que este
arquivo decide, com uma pergunta pura: "esta noite já abriu?". A resposta vem do painel da noite,
que é append-only e já registra elo por elo. Sem isso, a reserva duplicaria a coleta: dois lotes de
diários na mesma noite, dois commits competindo, e a fila andando duas vezes para a mesma janela.

A NOITE é a data em que a janela ABRIU, não a data do relógio: um elo que roda às 03h UTC pertence à
noite que começou no dia anterior, em Brasília. É a mesma convenção do painel, e está aqui como
função para que o vigia e o coletor não a reimplementem cada um à sua maneira.

USO
  python3 scripts/janela_da_noite.py --autoteste
  python3 scripts/janela_da_noite.py --noite            # a data da janela corrente
  python3 scripts/janela_da_noite.py --precisa-abrir    # "sim"/"nao" + código de saída
  python3 scripts/janela_da_noite.py --atraso           # minutos desde a hora prevista
"""
import datetime as dt
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

JANELA_UTC = (1, 9)        # 01:00 às 09:00 UTC = 22h às 06h de Brasília
ABERTURA_PREVISTA = "01:07"  # o cron principal da corrente, fora do minuto de pico
ELO_DE_ABERTURA = "diarios"


def noite_de(agora: dt.datetime, janela=JANELA_UTC) -> str:
    """A data da janela a que este instante pertence. Função pura."""
    inicio = janela[0]
    base = agora.date() if agora.hour >= inicio else agora.date() - dt.timedelta(days=1)
    return base.isoformat()


def inicio_da_janela(agora: dt.datetime, janela=JANELA_UTC) -> str:
    """O instante UTC em que a janela corrente abriu, em ISO 8601. Função pura.

    É o que o vigia e a reserva passam à API do GitHub para perguntar "já houve execução NESTA
    noite?". Perguntar pelo painel não basta na primeira meia hora: a linha do painel só é escrita
    quando o elo TERMINA, e a reserva dispara meia hora depois da abertura — quando os diários
    costumam estar no meio do lote. Sem este critério, a reserva duplicaria a coleta.
    """
    return dt.datetime.combine(dt.date.fromisoformat(noite_de(agora, janela)),
                               dt.time(hour=janela[0])).isoformat() + "Z"


def dentro_da_janela(agora: dt.datetime, janela=JANELA_UTC) -> bool:
    """O instante está na janela noturna? Função pura."""
    inicio, fim = janela
    return inicio <= agora.hour < fim if inicio < fim else (agora.hour >= inicio
                                                            or agora.hour < fim)


def ja_abriu(linhas: list, noite: str, elo: str = ELO_DE_ABERTURA) -> bool:
    """Esta noite já tem registro de TRABALHO do elo de abertura? Função pura.

    05/10/2026 (item 3.1 do handover da noite confiável) — CANCELADO NÃO É FEITO.
    Esta função contava QUALQUER registro da noite. Medido na noite de 04→05/10: o job
    `diarios / coletar` foi cancelado às 01:14:09 UTC, dois minutos depois de começar, e a reserva e
    o despachante leram aquele registro como "a noite abriu" — **ninguém refez a coleta perdida**, e
    as tentativas das 03:56 e 04:38 saíram sem trabalhar.

    O comentário anterior defendia contar a falha, e tinha razão no caso dele: um elo que coletou e
    falhou no push trabalhou, e refazê-lo duplicaria lote e commit. A distinção certa não é a
    conclusão, é o TRABALHO — e é `painel_da_noite.trabalhou` quem a faz, pelo marcador que o elo
    grava ao terminar os comandos, antes do commit. Falha com trabalho feito continua contando;
    cancelado antes de coletar passa a NÃO contar.
    """
    import sys as _s
    _s.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    from painel_da_noite import trabalhou
    for l in (linhas or []):
        if l.get("noite") != noite or l.get("elo") != elo:
            continue
        # `trabalhou` já gravado na linha (desde 05/10) vence; linha antiga cai na conclusão.
        if l.get("trabalhou") if l.get("trabalhou") is not None else trabalhou(l.get("conclusao")):
            return True
    return False


def atraso_minutos(agora: dt.datetime, prevista: str = ABERTURA_PREVISTA) -> int:
    """Minutos entre a hora prevista da abertura e agora, dentro da mesma noite. Função pura."""
    h, m = (int(x) for x in prevista.split(":"))
    alvo = agora.replace(hour=h, minute=m, second=0, microsecond=0)
    if agora.hour < JANELA_UTC[0]:
        alvo -= dt.timedelta(days=1)
    return max(0, int((agora - alvo).total_seconds() // 60))


def precisa_abrir(linhas: list, agora: dt.datetime) -> bool:
    """O vigia deve disparar a corrente agora? Função pura.

    Só dentro da janela: fora dela, disparar levaria coleta e commit para o horário de trabalho da
    editoria, que é exatamente o que a janela existe para evitar.
    """
    return dentro_da_janela(agora) and not ja_abriu(linhas, noite_de(agora))


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
    # A noite é nomeada pela data UTC em que a JANELA abriu, que é a convenção que o painel já
    # usa: a janela que abre às 01:00 UTC de 04/10 é "2026-10-04", embora em Brasília seja a noite
    # de 03 para 04. Duas convenções para a mesma noite seria o começo de um erro silencioso.
    ok("02h40 UTC pertence à janela que abriu às 01h do mesmo dia UTC",
       noite_de(d(2026, 10, 4, 2, 40)) == "2026-10-04")
    ok("elo às 01h UTC já é da noite nova",
       noite_de(d(2026, 10, 4, 1, 7)) == "2026-10-04")
    ok("meio-dia pertence à noite anterior, não inventa noite nova",
       noite_de(d(2026, 10, 4, 12, 0)) == "2026-10-04")
    ok("00:30 UTC ainda é a noite do dia anterior",
       noite_de(d(2026, 10, 4, 0, 30)) == "2026-10-03")

    ok("o início da janela é 01:00 UTC da data da noite",
       inicio_da_janela(d(2026, 10, 4, 2, 40)) == "2026-10-04T01:00:00Z")
    ok("antes de 01:00 o início da janela é o do dia anterior",
       inicio_da_janela(d(2026, 10, 4, 0, 30)) == "2026-10-03T01:00:00Z")

    ok("01:07 está na janela", dentro_da_janela(d(2026, 10, 4, 1, 7)))
    ok("08:59 ainda está na janela", dentro_da_janela(d(2026, 10, 4, 8, 59)))
    ok("09:00 já saiu", not dentro_da_janela(d(2026, 10, 4, 9, 0)))
    ok("meio-dia está fora", not dentro_da_janela(d(2026, 10, 4, 12, 0)))

    linhas = [{"noite": "2026-10-03", "elo": "diarios", "conclusao": "success"}]
    ok("noite com os diários registrados já abriu", ja_abriu(linhas, "2026-10-03"))
    ok("outra noite não conta", not ja_abriu(linhas, "2026-10-04"))
    ok("diários que FALHARAM ainda contam como abertura",
       ja_abriu([{"noite": "n", "elo": "diarios", "conclusao": "failure"}], "n"))
    ok("outro elo não faz a noite abrir",
       not ja_abriu([{"noite": "n", "elo": "sinais"}], "n"))
    ok("painel vazio não quebra", not ja_abriu([], "n") and not ja_abriu(None, "n"))

    ok("o atraso é contado da hora prevista",
       atraso_minutos(d(2026, 10, 4, 2, 40)) == 93)
    ok("antes da hora prevista o atraso é zero",
       atraso_minutos(d(2026, 10, 4, 1, 0)) == 0)
    ok("depois da meia-noite o atraso não vira negativo nem gigante",
       atraso_minutos(d(2026, 10, 4, 0, 30)) == 1403)

    ok("noite não aberta, dentro da janela: o vigia dispara",
       precisa_abrir(linhas, d(2026, 10, 4, 2, 7)))
    ok("noite já aberta com trabalho feito: o vigia NÃO dispara",
       not precisa_abrir([{"noite": "2026-10-04", "elo": "diarios",
                           "conclusao": "success"}], d(2026, 10, 4, 2, 7)))

    # 05/10/2026 (item 3.1) — o que a noite de 04→05/10 provou que faltava.
    ok("elo CANCELADO não abriu a noite: o vigia DISPARA e a coleta é refeita",
       precisa_abrir([{"noite": "2026-10-04", "elo": "diarios",
                       "conclusao": "cancelled"}], d(2026, 10, 4, 2, 7)))
    ok("elo que estourou o tempo não abriu a noite",
       precisa_abrir([{"noite": "2026-10-04", "elo": "diarios",
                       "conclusao": "timed_out"}], d(2026, 10, 4, 2, 7)))
    ok("elo PULADO não abriu a noite",
       precisa_abrir([{"noite": "2026-10-04", "elo": "diarios",
                       "conclusao": "skipped"}], d(2026, 10, 4, 2, 7)))
    ok("elo que coletou e FALHOU no push abriu a noite — refazer duplicaria lote",
       not precisa_abrir([{"noite": "2026-10-04", "elo": "diarios",
                           "conclusao": "failure"}], d(2026, 10, 4, 2, 7)))
    ok("linha sem conclusão não abriu a noite",
       precisa_abrir([{"noite": "2026-10-04", "elo": "diarios"}], d(2026, 10, 4, 2, 7)))
    ok("o marcador `trabalhou` vence a conclusão: cancelado COM trabalho abriu",
       not precisa_abrir([{"noite": "2026-10-04", "elo": "diarios",
                           "conclusao": "cancelled", "trabalhou": True}],
                         d(2026, 10, 4, 2, 7)))
    ok("o marcador `trabalhou` vence a conclusão: success SEM trabalho não abriu",
       precisa_abrir([{"noite": "2026-10-04", "elo": "diarios",
                       "conclusao": "success", "trabalhou": False}], d(2026, 10, 4, 2, 7)))
    ok("elo de outra noite não abre esta",
       precisa_abrir([{"noite": "2026-10-03", "elo": "diarios",
                       "conclusao": "success"}], d(2026, 10, 4, 2, 7)))
    ok("outro elo com trabalho não conta como abertura dos diários",
       precisa_abrir([{"noite": "2026-10-04", "elo": "triagem",
                       "conclusao": "success"}], d(2026, 10, 4, 2, 7)))
    ok("fora da janela o vigia nunca dispara, mesmo sem abertura",
       not precisa_abrir([], d(2026, 10, 4, 14, 0)))

    import dis
    nomes = set()
    for nome_obj, obj in list(globals().items()):
        if nome_obj in ("_autoteste", "main"):
            continue
        codigo = getattr(obj, "__code__", None)
        if codigo is not None:
            nomes |= {i.argval for i in dis.get_instructions(codigo) if isinstance(i.argval, str)}
    ok("trava estrutural: nenhuma função escreve",
       not ({"gravar", "write_text", "write_bytes"} & nomes))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else f"✓ AUTOTESTE OK — {len(_casos_contados)} casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def main() -> int:
    argv = sys.argv[1:]
    if "--autoteste" in argv:
        return _autoteste()
    agora = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    if "--noite" in argv:
        print(noite_de(agora))
        return 0
    if "--inicio-da-janela" in argv:
        print(inicio_da_janela(agora))
        return 0
    from coletores_base import ler
    linhas = (ler("painel_da_noite.json") or {}).get("noites") or []
    if "--atraso" in argv:
        print(atraso_minutos(agora))
        return 0
    if "--precisa-abrir" in argv:
        precisa = precisa_abrir(linhas, agora)
        print("sim" if precisa else "nao")
        return 0 if precisa else 1
    noite = noite_de(agora)
    print(f"noite de {noite} · abriu: {'sim' if ja_abriu(linhas, noite) else 'NÃO'} · "
          f"atraso da abertura: {atraso_minutos(agora)} min · "
          f"{'dentro' if dentro_da_janela(agora) else 'fora'} da janela")
    return 0


if __name__ == "__main__":
    sys.exit(main())
