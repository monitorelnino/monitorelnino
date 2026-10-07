#!/usr/bin/env python3
"""
scripts/pendente_do_elo.py — trabalho que o push perdeu volta, em vez de sumir
===============================================================================
Item 1.3 do `HANDOVER_noite_confiavel_parte2_06-10-2026.md`: "se o push falhar após 3 tentativas, o
elo sobe os seus arquivos como artefato do run e grava `data/noite/<data>/<elo>.pendente`; o elo
seguinte (ou a triagem) **reaplica** o artefato".

O MECANISMO QUE NÃO AGIA
-------------------------
O artefato já era subido desde o item 1a — e ninguém o baixava. Na noite de 05→06/10 o resultado
foi exato: 364 minutos de coleta viraram artefato e morreram ali, porque nada no sistema sabia que
havia o que reaplicar. "Conflito nunca descarta trabalho" era uma frase; isto é o mecanismo.

Duas metades:

  **marcar**   o elo que perdeu o push grava `data/noite/<noite>/<elo>.pendente` com o run, a hora
               e os caminhos que ficaram de fora. O marcador é o que o elo seguinte procura — e ele
               fica no mesmo lugar do `.feito`, que é onde a guarda da noite já olha.

  **reaplicar** o elo seguinte baixa o artefato daquele run e aplica os arquivos SOBRE a árvore,
               pela mesma política de mesclagem do resolvedor: nada é sobrescrito às cegas. O que
               reaplica com sucesso vira `.reaplicado`; o que não, continua `.pendente` e aparece no
               relatório da manhã.

A REGRA QUE ESTE ARQUIVO NÃO QUEBRA
------------------------------------
Reaplicar NÃO é adivinhar mesclagem. Arquivo com classe declarada em
`scripts/unir_conflito_de_rodada.py` se une por ela; arquivo sem classe **não** é reaplicado — ele
continua pendente e nomeado. Reaplicar sem política seria o mesmo erro que apagou 3.000 execuções
em 23/09, com outro nome.

USO
  python3 scripts/pendente_do_elo.py --autoteste
  python3 scripts/pendente_do_elo.py --marcar <elo> --run <id> --caminhos a.json b.json
  python3 scripts/pendente_do_elo.py --listar
"""
import datetime as dt
import json
import os
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
NOVA_LINHA = chr(10)
DIR_NOITE = RAIZ / "data" / "noite"


def noite_de(agora: dt.datetime) -> str:
    """A noite a que este instante pertence, em ISO. Função pura.

    A noite abre às 22h de Brasília e fecha às 6h: o que acontece depois da meia-noite pertence à
    noite que começou na véspera. É a mesma conta de `scripts/janela_da_noite.py`, e ela importa
    aqui porque o elo que perdeu o push às 01:13 tem de deixar o marcador onde o elo seguinte, às
    02:00, vai procurar.
    """
    d = agora.date()
    return (d - dt.timedelta(days=1)).isoformat() if agora.hour < 12 else d.isoformat()


def caminho_do_marcador(elo: str, noite: str, sufixo: str = "pendente") -> str:
    """Onde mora o marcador deste elo nesta noite. Função pura."""
    return f"data/noite/{noite}/{elo}.{sufixo}"


def conteudo_do_marcador(elo: str, run: str, caminhos: list, quando: str) -> dict:
    """O que o marcador guarda. Função pura.

    Guarda o RUN porque é dele que o artefato se baixa, e os CAMINHOS porque o elo seguinte precisa
    saber o que procurar sem abrir o artefato inteiro.
    """
    return {
        "elo": str(elo),
        "run": str(run),
        "quando": str(quando),
        "caminhos": sorted(str(c).replace("\\", "/") for c in (caminhos or [])),
        "estado": "pendente",
        "_governanca": ("Trabalho que o push perdeu. O artefato do run guarda os arquivos; o elo "
                        "seguinte reaplica o que tem classe de mesclagem declarada. Sem classe, "
                        "continua pendente e nomeado — reaplicar sem política apagaria dado."),
    }


def e_derivado(caminho: str, classes: dict) -> bool:
    """O caminho é função de outro dado? Função pura.

    Derivado NÃO se reaplica: ele se regenera. Reaplicar é, na melhor hipótese, inútil — a cadeia o
    reescreve logo depois — e na pior, estrago: em 06/10/2026 a reaplicação levou
    `data/pistas_revisao.json` de 9,9 MB para 87 MB, +775% numa execução, e o portão de tamanho
    pegou. Ele é derivado da fila, e a fila já tinha voltado inteira pelo caminho dela.
    """
    c = str(caminho).replace("\\", "/")
    return (c in set((classes or {}).get("regeneraveis") or ())
            or any(c.startswith(p) for p in (classes or {}).get("prefixos_regeneraveis") or ()))


def pode_reaplicar(caminho: str, classes: dict) -> bool:
    """Este caminho tem política de mesclagem declarada? Função pura.

    `classes` é o que `unir_conflito_de_rodada` sabe resolver: {"exatos": [...], "prefixos": [...]}.
    """
    c = str(caminho).replace("\\", "/")
    if c in set((classes or {}).get("exatos") or ()):
        return True
    return any(c.startswith(p) for p in (classes or {}).get("prefixos") or ())


def separar_para_reaplicar(caminhos: list, classes: dict) -> tuple:
    """(reaplicaveis, sem_politica). Função pura."""
    pode, nao = [], []
    for c in sorted(set(caminhos or [])):
        if e_derivado(c, classes):
            continue                    # regenera-se, não se reaplica
        (pode if pode_reaplicar(c, classes) else nao).append(c)
    return pode, nao


def base_comum(a: list, b: list) -> list:
    """O prefixo comum de duas listas que só crescem. Função pura.

    A união pela base comum precisa da base, e no artefato ela não vem junto. Para dado
    append-only ela é DERIVÁVEL: é o prefixo em que os dois lados ainda concordam. Não é um palpite
    — é a definição de "até onde os dois eram o mesmo arquivo".
    """
    fora = []
    for x, y in zip(a or [], b or []):
        if x != y:
            break
        fora.append(x)
    return fora


def unir_listas_que_so_crescem(da_arvore: list, do_artefato: list) -> list:
    """base + o que cada lado acrescentou. Função pura.

    Mesma conta do resolvedor, com a base derivada. A trava é a mesma de 23/09: o resultado nunca
    pode ser menor que qualquer um dos lados.
    """
    base = base_comum(da_arvore, do_artefato)
    if not base and da_arvore and do_artefato:
        # SEM BASE COMUM nao se soma. Dado que so cresce tem base por definicao; nao ter base e a
        # prova de que a premissa nao vale ali, e somar os dois lados seria CONCATENAR. Foi assim
        # que `data/pistas_imprensa.json` foi de 28 MB a 187,53 MB em meia hora, em 06/10/2026, e
        # passou do limite de 100 MB do GitHub: 28, 56, 112, 187, dobrando a cada reaplicacao.
        raise ValueError("os dois lados nao tem comeco em comum: nao e o mesmo arquivo em dois "
                         "momentos, e soma-los seria concatenar")
    n = len(base)
    uniao = base + list(da_arvore or [])[n:] + list(do_artefato or [])[n:]
    if len(uniao) < max(len(da_arvore or []), len(do_artefato or [])):
        raise ValueError("a união ficou menor que um dos lados")
    return uniao


def classes_conhecidas() -> dict:
    """O que o resolvedor sabe unir, lido dele. Importa; não escreve."""
    sys.path.insert(0, str(RAIZ / "scripts"))
    import unir_conflito_de_rodada as u
    exatos = list(u.LOGS_QUE_SO_CRESCEM) + list(u.REGENERAVEIS) + list(u.FILAS_DE_PISTA)
    regeneraveis = list(u.REGENERAVEIS)
    prefixos_regeneraveis = list(u.PREFIXOS_REGENERAVEIS)
    prefixos = (list(u.PREFIXOS_REGENERAVEIS) + list(u.PREFIXOS_JSONL_QUE_SO_CRESCEM)
                + list(u.PREFIXOS_CONTADORES_QUE_SO_CRESCEM))
    return {"exatos": exatos, "prefixos": prefixos,
            "regeneraveis": regeneraveis,
            "prefixos_regeneraveis": prefixos_regeneraveis}


def runs_com_pendencia(artefatos: list, noite: str) -> list:
    """Os runs desta noite que deixaram trabalho por reaplicar. Função pura.

    `artefatos` é o que a API devolve: [{"name": ..., "created_at": ..., "expired": ...}]. O nome
    traz o elo e o run, no formato `coleta-perdida-<elo>-<run>`, porque é esse nome que o passo de
    artefato do `_coletor.yml` monta.
    """
    fora = []
    for a in artefatos or []:
        nome = str((a or {}).get("name") or "")
        if not nome.startswith("coleta-perdida-") or (a or {}).get("expired"):
            continue
        criado = str((a or {}).get("created_at") or "")[:10]
        if noite and criado and not (criado == noite or criado == _dia_seguinte(noite)):
            continue
        pedacos = nome[len("coleta-perdida-"):].rsplit("-", 1)
        if len(pedacos) != 2 or not pedacos[1].isdigit():
            continue
        fora.append({"elo": pedacos[0], "run": pedacos[1], "artefato": nome,
                     "quando": str((a or {}).get("created_at") or "")})
    # Em ordem CRONOLOGICA: reaplicar na ordem em que o trabalho aconteceu e o que
    # mantem o log coerente. Ordenar pelo numero do run so parece a mesma coisa.
    return sorted(fora, key=lambda x: x["quando"])


def _dia_seguinte(iso: str) -> str:
    """A data seguinte, em ISO. Função pura — a noite atravessa a meia-noite."""
    try:
        return (dt.date.fromisoformat(iso) + dt.timedelta(days=1)).isoformat()
    except (TypeError, ValueError):
        return ""


def _autoteste() -> int:
    falhas, contados = [], []

    def ok(nome, cond):
        contados.append(nome)
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    ok("01:13 pertence à noite da véspera",
       noite_de(dt.datetime(2026, 10, 6, 1, 13)) == "2026-10-05")
    ok("22:10 pertence à noite do próprio dia",
       noite_de(dt.datetime(2026, 10, 5, 22, 10)) == "2026-10-05")
    ok("06:09 ainda é a noite da véspera",
       noite_de(dt.datetime(2026, 10, 6, 6, 9)) == "2026-10-05")

    ok("o marcador fica junto do `.feito`",
       caminho_do_marcador("diarios", "2026-10-05")
       == "data/noite/2026-10-05/diarios.pendente")
    ok("o `.reaplicado` fica no mesmo lugar",
       caminho_do_marcador("diarios", "2026-10-05", "reaplicado").endswith(".reaplicado"))

    m = conteudo_do_marcador("diarios", "37397775612", ["b.json", "a.json"], "2026-10-06T01:13")
    ok("o marcador guarda o run", m["run"] == "37397775612")
    ok("os caminhos ficam ordenados", m["caminhos"] == ["a.json", "b.json"])
    ok("o marcador nasce pendente", m["estado"] == "pendente")

    C = {"exatos": ["data/log_buscas.json", "data/pistas_imprensa.json"],
         "prefixos": ["dados-abertos/", "data/funil/"]}
    ok("arquivo com classe exata é reaplicável", pode_reaplicar("data/log_buscas.json", C))
    ok("arquivo com classe por prefixo é reaplicável", pode_reaplicar("data/funil/2026-10-05.json", C))
    ok("arquivo sem classe NÃO é reaplicável", pode_reaplicar("data/fontes_consultadas.json", C) is False)

    pode, nao = separar_para_reaplicar(
        ["data/log_buscas.json", "data/fontes_consultadas.json", "dados-abertos/x.csv"], C)
    ok("o que tem política entra", pode == ["dados-abertos/x.csv", "data/log_buscas.json"])
    ok("o que não tem fica nomeado", nao == ["data/fontes_consultadas.json"])

    D = dict(C, regeneraveis=["data/pistas_revisao.json"], prefixos_regeneraveis=["feeds/"])
    ok("derivado é reconhecido", e_derivado("data/pistas_revisao.json", D))
    ok("derivado por prefixo também", e_derivado("feeds/blog.xml", D))
    ok("o que não é derivado passa", not e_derivado("data/log_buscas.json", D))
    p2, n2 = separar_para_reaplicar(
        ["data/pistas_revisao.json", "feeds/x.xml", "data/log_buscas.json"], D)
    ok("derivado NÃO entra na reaplicação", p2 == ["data/log_buscas.json"])
    ok("e nem fica como pendente", n2 == [])
    ok("nada se perde da conta", len(pode) + len(nao) == 3)
    ok("lista vazia não produz nada", separar_para_reaplicar([], C) == ([], []))

    ok("a base comum é o prefixo em que os dois concordam",
       base_comum([1, 2, 3], [1, 2, 9]) == [1, 2])
    ok("sem nada em comum, a base é vazia", base_comum([1], [9]) == [])
    ok("união traz o que cada lado acrescentou",
       unir_listas_que_so_crescem([1, 2, 3], [1, 2, 9]) == [1, 2, 3, 9])
    ok("união nunca fica menor que um lado",
       len(unir_listas_que_so_crescem([1, 2, 3], [1, 2])) >= 3)
    ok("lado vazio devolve o outro inteiro",
       unir_listas_que_so_crescem([], [1, 2]) == [1, 2])
    ok("lados iguais não duplicam", unir_listas_que_so_crescem([1, 2], [1, 2]) == [1, 2])
    try:
        unir_listas_que_so_crescem([1, 2], [8, 9])
        ok("concatenacao disfarcada de uniao e RECUSADA", False)
    except ValueError:
        ok("concatenacao disfarcada de uniao e RECUSADA", True)
    ok("lado vazio nao dispara a recusa", unir_listas_que_so_crescem([], [1, 2]) == [1, 2])

    ART = [
        {"name": "coleta-perdida-diarios-37397775612", "created_at": "2026-10-06T01:13:00Z"},
        {"name": "coleta-perdida-busca_web-37430988356", "created_at": "2026-10-05T22:10:00Z"},
        {"name": "capturas-ci-123", "created_at": "2026-10-06T01:13:00Z"},
        {"name": "coleta-perdida-velho-1", "created_at": "2026-09-01T01:13:00Z"},
        {"name": "coleta-perdida-expirado-9", "created_at": "2026-10-06T01:13:00Z", "expired": True},
    ]
    r = runs_com_pendencia(ART, "2026-10-05")
    ok("so os artefatos de coleta perdida entram", [x["elo"] for x in r]
       == ["busca_web", "diarios"])
    ok("o run sai do nome do artefato", r[1]["run"] == "37397775612")
    ok("a ordem e cronologica, nao pelo numero do run", r[0]["quando"] < r[1]["quando"])
    ok("artefato de outra noite fica de fora", all(x["elo"] != "velho" for x in r))
    ok("artefato expirado fica de fora", all(x["elo"] != "expirado" for x in r))
    ok("a noite atravessa a meia-noite", _dia_seguinte("2026-10-05") == "2026-10-06")
    ok("sem artefato nenhum, lista vazia", runs_com_pendencia([], "2026-10-05") == [])

    import dis
    nomes = set()
    for nome_obj, obj in list(globals().items()):
        # `_reaplicar` entra na lista de LEITORES-ESCRITORES, com `main`: o trabalho dele
        # e justamente baixar e escrever, e o docstring dele diz isso.
        if nome_obj in ("_autoteste", "main", "classes_conhecidas", "_reaplicar",
                        "_unir_arquivo"):
            continue
        if getattr(obj, "__module__", None) not in (__name__, None):
            continue
        codigo = getattr(obj, "__code__", None)
        if codigo is not None:
            nomes |= {i.argval for i in dis.get_instructions(codigo) if isinstance(i.argval, str)}
    ok("trava estrutural: as funções puras não escrevem nem vão à rede",
       not ({"write_text", "urlopen", "subprocess"} & nomes))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else f"✓ AUTOTESTE OK — {len(contados)} casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def _unir_arquivo(da_arvore: pathlib.Path, do_artefato: pathlib.Path):
    """Une dois JSON que só crescem, ou devolve None. Lê disco; não escreve.

    Só as formas que o projeto declara append-only: `{chave: [...]}` com uma única lista no topo, e
    JSONL. Qualquer outra forma devolve None — e o arquivo continua pendente, nomeado.
    """
    bruto_a = da_arvore.read_text(encoding="utf-8")
    bruto_b = do_artefato.read_text(encoding="utf-8")
    if da_arvore.suffix == ".jsonl":
        linhas = unir_listas_que_so_crescem(
            [x for x in bruto_a.splitlines() if x.strip()],
            [x for x in bruto_b.splitlines() if x.strip()])
        return "\n".join(linhas) + "\n"
    try:
        a, b = json.loads(bruto_a), json.loads(bruto_b)
    except json.JSONDecodeError:
        return None
    if not isinstance(a, dict) or not isinstance(b, dict):
        return None

    # FILA DE PISTA tem politica PROPRIA, e nao e a do prefixo: ela e identificada por CHAVE, e a
    # ordem muda porque `scripts/pistas.py` reescreve o arquivo inteiro. Trata-la como lista que so
    # cresce foi o que a inflou. Aqui vale a porta: pista nova entra, pista repetida tem os campos
    # mesclados, nada duplica.
    if isinstance(a.get("pistas"), list) and isinstance(b.get("pistas"), list):
        sys.path.insert(0, str(RAIZ / "scripts"))
        from pistas import chave_da_pista
        por_chave = {}
        for pista in list(b["pistas"]) + list(a["pistas"]):
            k = chave_da_pista(pista)
            if k in por_chave:
                for campo, valor in (pista or {}).items():
                    if campo not in por_chave[k] or por_chave[k][campo] in (None, "", [], {}):
                        por_chave[k][campo] = valor
            else:
                por_chave[k] = dict(pista)
        fundido = dict(b)
        fundido["pistas"] = list(por_chave.values())
        return json.dumps(fundido, ensure_ascii=False, indent=1) + NOVA_LINHA
    listas = [k for k in a if isinstance(a.get(k), list) and isinstance(b.get(k), list)]
    if len(listas) != 1:
        return None                     # duas listas: qual cresce? Não se adivinha.
    chave = listas[0]
    fundido = dict(b)
    fundido[chave] = unir_listas_que_so_crescem(a[chave], b[chave])
    for carimbo in ("atualizado_em", "gerado_em"):
        valores = [d.get(carimbo) for d in (a, b) if d.get(carimbo)]
        if valores:
            fundido[carimbo] = max(valores)
    return json.dumps(fundido, ensure_ascii=False, indent=1) + "\n"


def _reaplicar(argv: list) -> int:
    """Baixa os artefatos de trabalho perdido desta noite e aplica o que tem política.

    Lê a API (`gh`), escreve na árvore. Nunca derruba o elo: trabalho que não volta continua
    pendente e nomeado, e é o relatório da manhã que cobra.
    """
    import subprocess
    import tempfile

    noite = _opcao(argv, "--noite", noite_de(dt.datetime.now()))
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    cmd = ["gh", "api", f"repos/{repo}/actions/artifacts?per_page=100",
           "--jq", ".artifacts[] | {name, created_at, expired, id}"]
    try:
        bruto = subprocess.run(cmd, capture_output=True, text=True, timeout=60).stdout
    except Exception as erro:          # pragma: no cover — API fora do ar não é falha do elo
        print(f"· pendências não conferidas ({erro})")
        return 0
    artefatos = []
    for linha in (bruto or "").splitlines():
        if linha.strip():
            try:
                artefatos.append(json.loads(linha))
            except json.JSONDecodeError:
                continue
    pendentes = runs_com_pendencia(artefatos, noite)
    if not pendentes:
        print(f"· nenhuma pendência da noite {noite} para reaplicar.")
        return 0

    classes = classes_conhecidas()
    voltou, ficou = 0, []
    for p in pendentes:
        with tempfile.TemporaryDirectory() as tmp:
            baixar = subprocess.run(["gh", "run", "download", p["run"], "--name", p["artefato"],
                                     "--dir", tmp], capture_output=True, text=True, timeout=300)
            if baixar.returncode != 0:
                ficou.append(f"{p['elo']} (run {p['run']}): artefato não baixou")
                continue
            raiz_tmp = pathlib.Path(tmp)
            achados = [q for q in raiz_tmp.rglob("*") if q.is_file()]
            pode, sem = separar_para_reaplicar(
                [str(q.relative_to(raiz_tmp)).replace(chr(92), "/") for q in achados], classes)
            for rel in pode:
                destino = RAIZ / rel
                destino.parent.mkdir(parents=True, exist_ok=True)
                # O conteúdo do artefato entra como "deles" numa união pela base comum feita pelo
                # resolvedor no próximo conflito. Aqui só se copia o que NÃO existe na árvore ou o
                # que é idêntico: sobrescrever conteúdo divergente seria adivinhar mesclagem.
                origem = raiz_tmp / rel
                if not destino.exists():
                    destino.write_bytes(origem.read_bytes())
                    voltou += 1
                elif destino.read_bytes() != origem.read_bytes():
                    # DIFERE: é aqui que o trabalho volta ou se perde. Desistir deixaria o artefato
                    # intacto e o trabalho fora — foi o que o ensaio real de 06/10 mostrou na
                    # primeira execução deste mecanismo. Para o dado que só cresce, a união pela
                    # base DERIVADA (o prefixo em que os dois lados ainda concordam) traz os dois
                    # acréscimos sem adivinhar nada. O que não é lista que só cresce continua
                    # pendente e nomeado.
                    try:
                        unido = _unir_arquivo(destino, origem)
                    except Exception as erro:
                        unido = None
                        motivo = str(erro)[:80]
                    if unido is not None:
                        destino.write_text(unido, encoding="utf-8", newline="\n")
                        voltou += 1
                    else:
                        ficou.append(f"{rel} (run {p['run']}): difere e não é lista que só cresce "
                                     f"({motivo if 'motivo' in dir() else 'sem união possível'})")
            for rel in sem:
                ficou.append(f"{rel} (run {p['run']}): sem política de mesclagem")

    print(f"· pendências da noite {noite}: {voltou} arquivo(s) reaplicado(s)")
    for x in ficou[:12]:
        print(f"      · ainda pendente: {x}")
    return 0


def _opcao(argv: list, nome: str, padrao=None):
    return argv[argv.index(nome) + 1] if nome in argv and len(argv) > argv.index(nome) + 1 else padrao


def main(argv: list) -> int:
    if "--autoteste" in argv:
        return _autoteste()

    if "--listar" in argv:
        achados = sorted(DIR_NOITE.glob("*/*.pendente")) if DIR_NOITE.exists() else []
        if not achados:
            print("· nenhum trabalho pendente de reaplicação.")
            return 0
        for arq in achados:
            doc = json.loads(arq.read_text(encoding="utf-8"))
            print(f"  ⚠ {arq.relative_to(RAIZ)}: elo `{doc.get('elo')}`, run {doc.get('run')}, "
                  f"{len(doc.get('caminhos') or [])} caminho(s)")
        return 1

    if "--marcar" in argv:
        elo = _opcao(argv, "--marcar")
        if not elo:
            print("uso: --marcar <elo> --run <id> [--caminhos a.json b.json]")
            return 2
        run = _opcao(argv, "--run", os.environ.get("GITHUB_RUN_ID", "?"))
        caminhos = []
        if "--caminhos" in argv:
            caminhos = [a for a in argv[argv.index("--caminhos") + 1:] if not a.startswith("--")]
        agora = dt.datetime.now()
        noite = _opcao(argv, "--noite", noite_de(agora))
        alvo = RAIZ / caminho_do_marcador(elo, noite)
        alvo.parent.mkdir(parents=True, exist_ok=True)
        doc = conteudo_do_marcador(elo, run, caminhos, agora.isoformat(timespec="minutes"))
        # §229: porta atômica. O marcador de pendência é a prova de que houve trabalho a recuperar
        # — marcador pela metade é pior que marcador nenhum, porque ninguém o lê e ninguém o
        # procura.
        from coletores_base import gravar_em
        gravar_em(alvo, doc)
        pode, nao = separar_para_reaplicar(caminhos, classes_conhecidas())
        print(f"⚠ TRABALHO PENDENTE: {alvo.relative_to(RAIZ)} — run {run}, "
              f"{len(pode)} caminho(s) reaplicável(eis), {len(nao)} sem política")
        for c in nao:
            print(f"      · sem política de mesclagem, não será reaplicado: {c}")
        return 0

    if "--reaplicar" in argv:
        return _reaplicar(argv)

    print(__doc__.strip().split("USO")[-1].strip())
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
