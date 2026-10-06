#!/usr/bin/env python3
"""
scripts/guarda_da_janela.py — coleta na `main` só dentro da janela da noite
============================================================================
Causa F do `HANDOVER_noite_confiavel_parte3_causas_confirmadas_06-10-2026.md`.

A REGRA, QUE É DE 27/09/2026
-----------------------------
Nenhum commit automático na `main` de dia. Ela estava escrita e dependia de os `cron` estarem
certos — e `cron` certo não impede disparo manual, nem `workflow_run` em cadeia, nem reexecução de
um run antigo. Em 06/10 rodaram coletores na `main` fora da janela, disputando-a com o trabalho da
editoria, e o publicador falhou seis vezes no meio disso.

A guarda responde uma pergunta só, antes de o elo coletar qualquer coisa:

    **este elo vai gravar na `main`, agora, fora da janela da noite?**

Se sim, ele para — e para em SUCESSO, não em falha: não coletar fora da hora é o comportamento
certo, não um defeito. Fora da `main` (no ramo `ensaio`, por exemplo) a guarda nunca barra: é lá que
o ensaio roda de dia, de propósito.

A janela é a de `scripts/janela_da_noite.py`, 01:00–09:00 UTC (22h–06h de Brasília). Ela tem um
dono só, e esta guarda o consulta em vez de repetir os números.

USO
  python3 scripts/guarda_da_janela.py --autoteste
  python3 scripts/guarda_da_janela.py --ramo main --elo diarios
"""
import datetime as dt
import os
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))

# O publicador é a exceção única, e ela é da editoria: publicar é o que ela pede quando pede.
ELOS_SEM_JANELA = ("publicar", "publicar-dados")


def deve_parar(ramo: str, elo: str, agora: dt.datetime, dentro_da_janela) -> str | None:
    """Motivo para não coletar, ou None. Função pura — `dentro_da_janela` é injetada.

    Três perguntas, nesta ordem, e a primeira que responder decide:
      1. é a `main`?           fora dela, nada barra — o ensaio roda de dia por desenho;
      2. é elo sem janela?     o publicador, quando a editoria chama;
      3. está na janela?       se não, para.
    """
    if str(ramo or "").strip() != "main":
        return None
    if str(elo or "").strip().lower() in ELOS_SEM_JANELA:
        return None
    if dentro_da_janela(agora):
        return None
    return (f"`{elo}` grava na `main` e sao {agora.strftime('%H:%M')} UTC, fora da janela da noite "
            f"(01:00-09:00 UTC, 22h-06h de Brasilia). A regra e de 27/09/2026: nenhum commit "
            f"automatico na `main` de dia. De dia a coleta roda no ramo `ensaio`.")


def _autoteste() -> int:
    falhas, contados = [], []

    def ok(nome, cond):
        contados.append(nome)
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    from janela_da_noite import dentro_da_janela as real

    noite = dt.datetime(2026, 10, 6, 2, 0)      # 23h de Brasília
    dia = dt.datetime(2026, 10, 6, 14, 30)      # 11h30 de Brasília

    ok("a janela de verdade diz que 02:00 UTC é noite", real(noite))
    ok("e que 14:30 UTC é dia", not real(dia))

    ok("coletor na `main` de dia PARA", deve_parar("main", "diarios", dia, real) is not None)
    ok("coletor na `main` de noite segue", deve_parar("main", "diarios", noite, real) is None)
    ok("coletor no `ensaio` de dia segue", deve_parar("ensaio", "diarios", dia, real) is None)
    ok("coletor em ramo de edição de dia segue",
       deve_parar("edicao/x", "diarios", dia, real) is None)
    ok("o publicador na `main` de dia segue", deve_parar("main", "publicar", dia, real) is None)
    ok("o publicador pelo nome do workflow também",
       deve_parar("main", "publicar-dados", dia, real) is None)
    ok("maiúscula no nome do elo não burla", deve_parar("main", "PUBLICAR", dia, real) is None)
    ok("elo vazio na `main` de dia PARA", deve_parar("main", "", dia, real) is not None)
    ok("ramo vazio não é a `main`", deve_parar("", "diarios", dia, real) is None)
    ok("o motivo diz a hora e a regra",
       "27/09" in deve_parar("main", "diarios", dia, real))

    # As bordas da janela, que é onde o erro mora.
    ok("01:00 UTC em ponto já é janela", deve_parar("main", "x", dt.datetime(2026, 10, 6, 1, 0), real) is None)
    ok("08:59 UTC ainda é janela", deve_parar("main", "x", dt.datetime(2026, 10, 6, 8, 59), real) is None)
    ok("09:00 UTC já é dia", deve_parar("main", "x", dt.datetime(2026, 10, 6, 9, 0), real) is not None)
    ok("00:59 UTC ainda é dia", deve_parar("main", "x", dt.datetime(2026, 10, 6, 0, 59), real) is not None)

    import dis
    nomes = set()
    for nome_obj, obj in list(globals().items()):
        if nome_obj in ("_autoteste", "main"):
            continue
        if getattr(obj, "__module__", None) not in (__name__, None):
            continue
        codigo = getattr(obj, "__code__", None)
        if codigo is not None:
            nomes |= {i.argval for i in dis.get_instructions(codigo) if isinstance(i.argval, str)}
    ok("trava estrutural: a função pura não lê relógio, disco nem rede",
       not ({"now", "utcnow", "read_text", "write_text", "urlopen"} & nomes))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else f"✓ AUTOTESTE OK — {len(contados)} casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def main(argv: list) -> int:
    if "--autoteste" in argv:
        return _autoteste()
    from janela_da_noite import dentro_da_janela

    def opcao(nome, padrao=""):
        return argv[argv.index(nome) + 1] if nome in argv and len(argv) > argv.index(nome) + 1 \
            else padrao

    ramo = opcao("--ramo", os.environ.get("GITHUB_REF_NAME", ""))
    elo = opcao("--elo", os.environ.get("ELO", ""))
    motivo = deve_parar(ramo, elo, dt.datetime.utcnow(), dentro_da_janela)
    if motivo:
        print(f"· COLETA ADIADA: {motivo}")
        return 1
    print(f"· janela OK para `{elo}` em `{ramo}`.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
