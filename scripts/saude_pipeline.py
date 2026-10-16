#!/usr/bin/env python3
"""
saude_pipeline.py
=================
Uma linha de saúde por script da rodada: quando rodou, quanto durou, quantos itens, status, erro.

Handover `HANDOVER_desacoplar_pipeline_e_emagrecer_repositorio_27-09-2026.md`, itens 1 e 2. O item 1
exige que **cada coletor grave sua linha de saúde**; o item 2 constrói o painel sobre essas linhas.

POR QUE ISTO EXISTE
-------------------
A queixa da editoria era "lentidão, quebras, excesso de erros", e a resposta exigia cavar log do
Actions. Um job monolítico com trinta scripts em sequência não diz qual deles demorou nem qual
quebrou: diz só que a rodada morreu. Com uma linha por script, a pergunta "o que quebrou hoje?" se
responde abrindo um arquivo.

Medir não decide nada: este arquivo nunca é lido pelo cálculo do índice.

MODO INVÓLUCRO
--------------
    python3 scripts/saude_pipeline.py --rodar coletar_doe.py --limite 27

Roda o comando, cronometra, captura a saída e o código de saída, grava a linha e **devolve o mesmo
código de saída** — quem chama decide se aquilo é fatal. A saída do comando passa para a saída padrão
sem alteração, para que o log do Actions continue legível.

`itens` sai da própria saída do comando quando ela traz um número reconhecível (o padrão dos
coletores: "N consultados", "N pistas novas", "N municípios"); quando não traz, fica nulo — nulo é
"não medido", nunca zero.

PRAZO DO ELO (11/10/2026, F38 do catálogo)
--------------------------------------------
    python3 scripts/saude_pipeline.py --prazo <epoch> --rodar coletar_x.py

O teto do job do GitHub mata o job inteiro, e com ele o commit: em 04/10 e três vezes em 11/10 a
rotina semanal de sinais coletou duas horas e meia e não gravou nada, porque o último comando da
fila ainda rodava quando o teto chegou. Com `--prazo`, o comando que COMEÇARIA depois do prazo é
pulado (linha `pulado`), e o que ainda roda no prazo é interrompido (SIGINT ao grupo, 60 s de
cortesia, SIGKILL) — o job chega vivo ao commit e grava o que os outros comandos acharam. JSON
de `data/` que a interrupção deixe ilegível volta à versão do git: dado pela metade não sobe.

USO
  python3 scripts/saude_pipeline.py [--prazo <epoch>] --rodar [prazo=Nmin] <script> [args...]
  python3 scripts/saude_pipeline.py --listar
  python3 scripts/saude_pipeline.py --autoteste
"""
import datetime
import json
import pathlib
import os
import re
import signal
import subprocess
import sys
import time

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

ARQUIVO = RAIZ / "data" / "saude_pipeline.json"
DIAS_DE_HISTORICO = 7
FORMATO_VERSAO = 1

# Padrões de contagem que os coletores já imprimem. Ordem importa: o primeiro que casar vale.
PADROES_DE_ITENS = (
    r"(\d+)\s+munic[íi]pios?\s+consultados?",
    r"(\d+)\s+consultados?",
    r"(\d+)\s+pistas?\s+novas?",
    r"(\d+)\s+entradas?",
    r"(\d+)\s+it(?:em|ens)",
    r"(\d+)\s+registros?",
    r"(\d+)\s+decretos?\s+novos?",
)


def contar_itens(saida: str):
    """O número que o próprio script relatou, ou None. None é "não medido", não zero."""
    for padrao in PADROES_DE_ITENS:
        m = re.search(padrao, saida or "", re.I)
        if m:
            return int(m.group(1))
    return None


def resumir_erro(saida: str, limite: int = 300) -> str:
    """A linha decisiva, não o log inteiro.

    Procura a última linha que se parece com erro; se não achar nenhuma, devolve a última linha
    não vazia — que é onde um script bem-comportado diz o que houve."""
    linhas = [l.strip() for l in (saida or "").splitlines() if l.strip()]
    if not linhas:
        return ""
    candidatas = [l for l in linhas
                  if re.search(r"erro|error|traceback|exception|✗|falh|timeout|refus", l, re.I)]
    return (candidatas[-1] if candidatas else linhas[-1])[:limite]


def ler() -> dict:
    if not ARQUIVO.exists():
        return {"formato_versao": FORMATO_VERSAO, "execucoes": []}
    try:
        d = json.loads(ARQUIVO.read_text(encoding="utf-8"))
        d.setdefault("execucoes", [])
        return d
    except (OSError, json.JSONDecodeError):
        return {"formato_versao": FORMATO_VERSAO, "execucoes": []}


def podar(execucoes: list, hoje: datetime.date) -> list:
    """Mantém os últimos 7 dias. O histórico longo vive no log do Actions, não aqui."""
    corte = (hoje - datetime.timedelta(days=DIAS_DE_HISTORICO)).isoformat()
    return [e for e in execucoes if str(e.get("data") or "") >= corte]


def registrar(script: str, inicio: str, duracao_s: float, itens, status: str, erro: str = "",
              hoje: datetime.date = None, gravar=True) -> dict:
    """Acrescenta a linha e devolve o documento. `status`: ok | erro | pulado."""
    from coletores_base import hoje_editorial
    hoje = hoje or hoje_editorial()
    doc = ler()
    doc["formato_versao"] = FORMATO_VERSAO
    doc["execucoes"] = podar(doc["execucoes"], hoje) + [{
        "data": hoje.isoformat(), "script": script, "inicio": inicio,
        "duracao_s": round(float(duracao_s), 1), "itens": itens, "status": status,
        "erro": (erro or "")[:300],
    }]
    # 08/10/2026 (A2-02): o carimbo DERIVA da ultima execucao registrada, nao do relogio.
    # Com o relogio, dois elos da mesma noite gravavam carimbos diferentes e o resolvedor
    # recusava todo conflito deste arquivo -- que todo elo commita. A noite de 07->08/10
    # perdeu diarios, descoberta, juiz e sinais por isso.
    ultima = doc["execucoes"][-1] if doc["execucoes"] else {}
    doc["atualizado_em"] = str(ultima.get("inicio") or ultima.get("data") or hoje.isoformat())
    if gravar:
        from coletores_base import gravar_em
        ARQUIVO.parent.mkdir(parents=True, exist_ok=True)
        gravar_em(ARQUIVO, doc)
    return doc


# Comando que começaria com menos de um minuto até o prazo não começa: não chegaria a fazer nada
# útil, e a interrupção dele só custaria a cortesia de 60 s ao commit.
MINIMO_PARA_COMECAR_S = 60
CORTESIA_S = 60
CODIGO_PRAZO = 124   # o mesmo do `timeout` do coreutils


def decidir_prazo(prazo, agora: float, minimo: float = MINIMO_PARA_COMECAR_S):
    """('pular', 0) | ('rodar', segundos ou None). Função pura."""
    if prazo is None:
        return "rodar", None
    resta = float(prazo) - float(agora)
    if resta < minimo:
        return "pular", 0
    return "rodar", resta


def prazo_proprio(alvo: list, prazo, agora: float):
    """`prazo=12min coletor.py …` na linha do elo dá ao comando um prazo PRÓPRIO, o menor entre ele
    e o do elo, para que um canal não coma o tempo dos que vêm depois; o comando recebe o mesmo
    SIGINT e grava o que achou (16/10/2026, HANDOVER_FONTES item 3). Devolve (prazo, comando)."""
    proprio = re.fullmatch(r"prazo=(\d+)min", alvo[0]) if alvo else None
    if not proprio or not alvo[1:]:
        return prazo, alvo
    fim = agora + int(proprio.group(1)) * 60
    return min(prazo or fim, fim), alvo[1:]


def json_ilegiveis(caminhos, ler_texto) -> list:
    """Os `.json` da lista que não se leem mais. Função pura: `ler_texto` é injetada."""
    ruins = []
    for c in caminhos:
        if not str(c).endswith(".json"):
            continue
        try:
            json.loads(ler_texto(c))
        except (OSError, ValueError):
            ruins.append(c)
    return ruins


def _restaurar_json_quebrado() -> list:
    """Depois de uma interrupção: devolve ao git todo JSON de `data/` que ficou ilegível."""
    try:
        mudados = subprocess.run(["git", "diff", "--name-only", "--", "data/"], cwd=RAIZ,
                                 capture_output=True, text=True, check=False).stdout.split()
    except OSError:
        return []
    ruins = json_ilegiveis(mudados, lambda c: (RAIZ / c).read_text(encoding="utf-8"))
    for c in ruins:
        subprocess.run(["git", "checkout", "--", c], cwd=RAIZ, check=False)
        print(f"[saude] {c}: ilegível depois da interrupção — volta à versão do git", flush=True)
    return ruins


def rodar(argv: list, prazo=None, minimo: float = MINIMO_PARA_COMECAR_S,
          restaurar: bool = True) -> int:
    """Invólucro: cronometra, registra e devolve o MESMO código de saída do comando.

    Com `prazo` (epoch): pula o comando que começaria tarde demais e interrompe o que passa dele.
    """
    inicio_dt = datetime.datetime.now().replace(microsecond=0)
    decisao, resta = decidir_prazo(prazo, time.time(), minimo)
    if decisao == "pular":
        registrar(script=argv[0], inicio=inicio_dt.isoformat(), duracao_s=0, itens=None,
                  status="pulado", erro="prazo do elo esgotado antes de começar")
        print(f"[saude] {argv[0]}: pulado — prazo do elo esgotado antes de começar", flush=True)
        return 0
    # script .py roda com o mesmo interpretador; qualquer outro comando roda como está
    comando = ([sys.executable] + argv) if argv[0].endswith(".py") else list(argv)
    proc = subprocess.Popen(comando, cwd=RAIZ, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace",
                            start_new_session=True)
    interrompido = False
    try:
        saida, _ = proc.communicate(timeout=resta)
    except subprocess.TimeoutExpired:
        interrompido = True
        os.killpg(proc.pid, signal.SIGINT)
        try:
            saida, _ = proc.communicate(timeout=CORTESIA_S)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            saida, _ = proc.communicate()
    saida = saida or ""
    print(saida, end="" if saida.endswith("\n") else "\n")
    duracao = (datetime.datetime.now() - inicio_dt).total_seconds()
    codigo = CODIGO_PRAZO if interrompido else proc.returncode
    if interrompido and restaurar:
        _restaurar_json_quebrado()
    registrar(script=argv[0], inicio=inicio_dt.isoformat(), duracao_s=duracao,
              itens=contar_itens(saida), status="ok" if codigo == 0 else "erro",
              erro=("interrompido pelo prazo do elo" if interrompido
                    else "" if codigo == 0 else resumir_erro(saida)))
    print(f"[saude] {argv[0]}: {duracao:.0f}s, status "
          f"{'ok' if codigo == 0 else ('interrompido pelo prazo' if interrompido else 'erro')}",
          flush=True)
    return codigo


def listar() -> int:
    doc = ler()
    if not doc["execucoes"]:
        print("sem linhas de saúde ainda")
        return 0
    print(f"{'script':38} {'data':11} {'dur(s)':>7} {'itens':>6}  status")
    for e in doc["execucoes"][-40:]:
        itens = "—" if e.get("itens") is None else e["itens"]
        print(f"{str(e.get('script'))[:38]:38} {e.get('data'):11} {e.get('duracao_s'):>7} "
              f"{itens:>6}  {e.get('status')}"
              + (f"  {e.get('erro')[:60]}" if e.get("erro") else ""))
    return 0


def autoteste() -> int:
    casos = []
    hoje = datetime.date(2026, 9, 28)

    casos.append(("conta itens do padrão dos coletores",
                  contar_itens("lote 3/38: 60 municípios consultados, 0 lacunas, 2 pistas novas") == 60))
    casos.append(("conta pistas quando não há 'consultados'",
                  contar_itens("total: 7 pistas novas") == 7))
    casos.append(("saída sem número devolve None (não medido, não zero)",
                  contar_itens("pronto") is None))
    casos.append(("saída vazia devolve None", contar_itens("") is None))

    casos.append(("o resumo do erro pega a linha decisiva",
                  resumir_erro("linha um\nTraceback (most recent call last):\nValueError: x")
                  .startswith(("Traceback", "ValueError"))))
    casos.append(("sem linha de erro, devolve a última não vazia",
                  resumir_erro("primeira\nultima\n\n") == "ultima"))
    casos.append(("resumo nunca passa de 300 caracteres",
                  len(resumir_erro("erro " + "x" * 5000)) <= 300))

    # poda: 7 dias
    velhas = [{"data": (hoje - datetime.timedelta(days=d)).isoformat(), "script": "x"} for d in (0, 3, 7, 8, 30)]
    mantidas = podar(velhas, hoje)
    casos.append(("poda mantém os últimos 7 dias", len(mantidas) == 3))

    # registrar sem gravar em disco
    doc = registrar("coletar_doe.py", "2026-09-28T01:00:00", 12.4, 27, "ok", hoje=hoje, gravar=False)
    linha = doc["execucoes"][-1]
    casos.append(("a linha traz script, início, duração, itens e status",
                  linha["script"] == "coletar_doe.py" and linha["itens"] == 27
                  and linha["duracao_s"] == 12.4 and linha["status"] == "ok"))
    casos.append(("status de erro carrega o resumo",
                  registrar("x.py", "i", 1, None, "erro", "ValueError: y", hoje=hoje,
                            gravar=False)["execucoes"][-1]["erro"] == "ValueError: y"))
    casos.append(("o autoteste não escreveu em data/",
                  not (ARQUIVO.exists() and json.loads(ARQUIVO.read_text(encoding="utf-8"))
                       .get("execucoes", [{}])[-1].get("script") == "x.py")))

    # prazo do elo (F38)
    casos.append(("sem prazo, roda sem teto", decidir_prazo(None, 100.0) == ("rodar", None)))
    casos.append(("prazo distante, roda com o que resta",
                  decidir_prazo(1000.0, 100.0) == ("rodar", 900.0)))
    casos.append(("menos de um minuto até o prazo, pula",
                  decidir_prazo(150.0, 100.0) == ("pular", 0)))
    casos.append(("prazo vencido, pula", decidir_prazo(50.0, 100.0) == ("pular", 0)))
    casos.append(("prazo=Nmin dá prazo próprio e sai do comando",
                  prazo_proprio(["prazo=12min", "x.py", "-a"], None, 100.0) == (820.0, ["x.py", "-a"])))
    casos.append(("prazo próprio nunca passa do prazo do elo",
                  prazo_proprio(["prazo=12min", "x.py"], 500.0, 100.0) == (500.0, ["x.py"])))
    casos.append(("linha sem prazo=Nmin fica como está",
                  prazo_proprio(["x.py", "prazo=1min"], 9.0, 0.0) == (9.0, ["x.py", "prazo=1min"])))
    textos = {"data/a.json": '{"x": 1}', "data/b.json": '{"x": ', "data/c.txt": "{"}
    casos.append(("JSON pela metade é achado; texto e JSON inteiro não",
                  json_ilegiveis(list(textos), textos.__getitem__) == ["data/b.json"]))
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        lento = pathlib.Path(tmp) / "lento.py"
        lento.write_text("import time\nprint('3 itens')\ntime.sleep(30)\n", encoding="utf-8", newline="\n")
        original = globals()["registrar"]
        linhas = []
        globals()["registrar"] = lambda **k: linhas.append(k)
        try:
            t0 = time.time()
            rc = rodar([str(lento)], prazo=time.time() + 2, minimo=0, restaurar=False)
            dur = time.time() - t0
            rc_pulado = rodar([str(lento)], prazo=time.time())
        finally:
            globals()["registrar"] = original
        casos.append(("comando que passa do prazo é interrompido e sai com 124",
                      rc == CODIGO_PRAZO and dur < 20))
        casos.append(("a interrupção fica registrada como erro de prazo",
                      linhas and linhas[0]["erro"] == "interrompido pelo prazo do elo"))
        casos.append(("comando sem tempo para começar é pulado, não falha",
                      rc_pulado == 0 and linhas[-1]["status"] == "pulado"))

    ruins = [n for n, ok in casos if not ok]
    for n, ok in casos:
        print(f"  {'OK  ' if ok else 'FALHA'} {n}")
    if ruins:
        print(f"X AUTOTESTE: {len(ruins)} caso(s) reprovado(s).")
        return 1
    print(f"OK AUTOTESTE — {len(casos)} casos, sem escrita em data/.")
    return 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    if "--listar" in sys.argv:
        return listar()
    if "--rodar" in sys.argv:
        i = sys.argv.index("--rodar")
        alvo = sys.argv[i + 1:]
        if not alvo:
            print("✗ --rodar exige o comando a rodar")
            return 1
        prazo = None
        antes = sys.argv[1:i]
        if "--prazo" in antes:
            bruto = (antes[antes.index("--prazo") + 1:] or [""])[0]
            try:
                prazo = float(bruto) if bruto else None
            except ValueError:
                print(f"[saude] --prazo ilegível ({bruto!r}); rodando sem prazo", flush=True)
        prazo, alvo = prazo_proprio(alvo, prazo, time.time())
        return rodar(alvo, prazo=prazo)
    print(__doc__.strip().split("USO")[-1].strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
