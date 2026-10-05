#!/usr/bin/env python3
"""
scripts/orcamento_da_noite.py — abertura tardia não desperdiça a noite
=======================================================================
Item 3, fase 1, do `HANDOVER_garantia_dos_temporizadores_04-10-2026.md` (rev. 2).

A REGRA DA EDITORIA, E O QUE ELA REALMENTE EXIGE
------------------------------------------------
"22h às 06h" é decisão de 27/09 e tem **uma razão só**: nenhum commit automático na `main` durante
o dia, para não colidir com o trabalho da editoria no código. O prazo das 06:00 **não** é
necessidade técnica — e tratá-lo como se fosse custou noites inteiras: a abertura atrasada rodava
com o teto do job inteiro e morria no limite, jogando fora o que já havia colhido.

A fase 1 é esta: **abertura tardia é aceita**. Quem abre entre 22:00 e 03:00 roda com um orçamento
de tempo até **05:30**, grava o cursor e continua na noite seguinte **do ponto exato**, sem
recomeçar e sem cancelar o que fez. A publicação das 06:05 publica o que estiver pronto, e o painel
diz o que ficou.

Três funções puras, e é delas que o resto depende:
  `minutos_de_orcamento` — quanto tempo ainda cabe nesta noite;
  `cabe_no_orcamento`    — este lote ainda cabe, ou é hora de gravar o cursor e parar;
  `proximo_do_cursor`    — de onde a noite seguinte começa.

USO
  python3 scripts/orcamento_da_noite.py --autoteste
  python3 scripts/orcamento_da_noite.py --orcamento      # minutos restantes agora
  python3 scripts/orcamento_da_noite.py --cursor diarios # onde o elo parou
"""
import datetime as dt
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

ARQUIVO_DO_CURSOR = "cursor_da_noite.json"
FIM_DO_ORCAMENTO_UTC = "08:30"   # 05:30 de Brasília
JANELA_UTC = (1, 9)              # 01:00–09:00 UTC = 22h–06h de Brasília
ABERTURA_TARDIA_ATE_UTC = "06:00"  # 03:00 de Brasília


def minutos_de_orcamento(agora: dt.datetime, fim=FIM_DO_ORCAMENTO_UTC) -> int:
    """Minutos até o fim do orçamento desta noite. Função pura.

    Depois do fim, devolve 0 — e zero significa "grave o cursor e pare", não "rode mais rápido".
    """
    h, m = (int(x) for x in fim.split(":"))
    alvo = agora.replace(hour=h, minute=m, second=0, microsecond=0)
    if agora.hour >= JANELA_UTC[1]:
        # Já passou das 09:00 UTC: o orçamento desta noite acabou.
        return 0
    if alvo < agora:
        return 0
    return int((alvo - agora).total_seconds() // 60)


def abertura_tardia(agora: dt.datetime, limite=ABERTURA_TARDIA_ATE_UTC) -> bool:
    """A abertura ainda é aceita, mesmo atrasada? Função pura.

    Entre 01:00 e 06:00 UTC (22h e 03h de Brasília) a noite abre com orçamento. Depois disso não:
    o que sobra de janela não paga o custo de subir a corrente, e o cursor leva o trabalho para a
    noite seguinte sem perda.
    """
    h, m = (int(x) for x in limite.split(":"))
    return JANELA_UTC[0] <= agora.hour and (agora.hour, agora.minute) < (h, m)


def cabe_no_orcamento(agora: dt.datetime, minutos_do_lote: int, reserva: int = 10) -> bool:
    """O próximo lote cabe antes do fim do orçamento? Função pura.

    A `reserva` existe para o que vem DEPOIS do lote: gravar o cursor, commitar e deixar o elo
    seguinte começar. Sem ela, o último lote caberia e o commit não — o pior dos dois mundos,
    porque o trabalho estaria feito e não registrado.
    """
    return minutos_de_orcamento(agora) >= (int(minutos_do_lote) + int(reserva))


def cursor_novo(elo: str, posicao, total=None, noite: str = None) -> dict:
    """A marca de onde o elo parou. Função pura."""
    return {"elo": elo, "posicao": posicao, "total": total, "noite": noite,
            "motivo": "orçamento da noite esgotado"}


def proximo_do_cursor(cursores: dict, elo: str, padrao=0):
    """De onde o elo deve continuar. Função pura.

    Sem cursor, começa do princípio — e começar do princípio é o comportamento certo na primeira
    noite e depois de uma noite completa, porque cursor esgotado é cursor apagado.
    """
    c = (cursores or {}).get(elo) or {}
    pos = c.get("posicao")
    return padrao if pos is None else pos


def guardar(cursores: dict, cursor: dict) -> dict:
    """Os cursores com este elo atualizado. Função pura — não escreve."""
    fora = dict(cursores or {})
    fora[cursor["elo"]] = cursor
    return fora


def limpar(cursores: dict, elo: str) -> dict:
    """Apaga o cursor do elo: ele terminou a fila. Função pura."""
    fora = dict(cursores or {})
    fora.pop(elo, None)
    return fora


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
    ok("à 01:30 UTC há sete horas de orçamento",
       minutos_de_orcamento(d(2026, 10, 4, 1, 30)) == 420)
    ok("às 08:00 UTC sobram trinta minutos",
       minutos_de_orcamento(d(2026, 10, 4, 8, 0)) == 30)
    ok("depois do fim do orçamento, zero",
       minutos_de_orcamento(d(2026, 10, 4, 8, 45)) == 0)
    ok("fora da janela, zero", minutos_de_orcamento(d(2026, 10, 4, 14, 0)) == 0)

    ok("abertura às 02:40 é tardia e ACEITA", abertura_tardia(d(2026, 10, 4, 2, 40)))
    ok("abertura às 05:59 ainda é aceita", abertura_tardia(d(2026, 10, 4, 5, 59)))
    ok("às 06:00 não abre mais", not abertura_tardia(d(2026, 10, 4, 6, 0)))
    ok("ao meio-dia não abre", not abertura_tardia(d(2026, 10, 4, 12, 0)))

    ok("lote de 60 min cabe às 02:00", cabe_no_orcamento(d(2026, 10, 4, 2, 0), 60))
    ok("lote de 60 min NÃO cabe às 08:00", not cabe_no_orcamento(d(2026, 10, 4, 8, 0), 60))
    ok("a reserva impede o lote que caberia justo",
       not cabe_no_orcamento(d(2026, 10, 4, 8, 15), 15))
    ok("sem reserva, o mesmo lote caberia — é a reserva que decide",
       cabe_no_orcamento(d(2026, 10, 4, 8, 15), 15, reserva=0))

    c = cursor_novo("diarios", 1200, 5571, "2026-10-04")
    ok("o cursor guarda onde parou e de quanto", c["posicao"] == 1200 and c["total"] == 5571)
    ok("o cursor diz por que parou", "orçamento" in c["motivo"])

    cs = guardar({}, c)
    ok("o cursor é guardado pelo elo", cs["diarios"]["posicao"] == 1200)
    ok("a noite seguinte continua do ponto exato", proximo_do_cursor(cs, "diarios") == 1200)
    ok("elo sem cursor começa do princípio", proximo_do_cursor(cs, "juiz") == 0)
    ok("posição zero é posição, não ausência",
       proximo_do_cursor(guardar({}, cursor_novo("x", 0)), "x") == 0)
    ok("fila terminada apaga o cursor", "diarios" not in limpar(cs, "diarios"))
    ok("apagar cursor que não existe não quebra", limpar({}, "nada") == {})
    ok("guardar não altera o dicionário original",
       (lambda base: (guardar(base, cursor_novo("y", 1)), base == {})[1])({}))

    import dis
    nomes = set()
    for nome_obj, obj in list(globals().items()):
        if nome_obj in ("_autoteste", "main", "ler_cursores", "gravar_cursores"):
            continue
        codigo = getattr(obj, "__code__", None)
        if codigo is not None:
            nomes |= {i.argval for i in dis.get_instructions(codigo) if isinstance(i.argval, str)}
    ok("trava estrutural: as funções puras não escrevem",
       not ({"gravar", "write_text", "write_bytes"} & nomes))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else f"✓ AUTOTESTE OK — {len(_casos_contados)} casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def ler_cursores() -> dict:
    from coletores_base import ler
    return (ler(ARQUIVO_DO_CURSOR) or {}).get("cursores") or {}


def main() -> int:
    argv = sys.argv[1:]
    if "--autoteste" in argv:
        return _autoteste()
    agora = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    if "--orcamento" in argv:
        print(minutos_de_orcamento(agora))
        return 0
    if "--cursor" in argv:
        elo = argv[argv.index("--cursor") + 1]
        print(proximo_do_cursor(ler_cursores(), elo))
        return 0
    print(f"orçamento da noite: {minutos_de_orcamento(agora)} min restantes · "
          f"abertura tardia {'aceita' if abertura_tardia(agora) else 'fora da hora'} · "
          f"cursores: {sorted(ler_cursores()) or 'nenhum'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
