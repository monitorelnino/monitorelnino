#!/usr/bin/env python3
"""Reaplica o trabalho que a noite perdeu — pela porta de cada arquivo (08/10/2026, A2-19).

Quando o push de um elo falha, o `_coletor.yml` sobe o que ele coletou como artefato
`coleta-perdida-<elo>-<run>` e sai. Até aqui nada reaplicava aquilo: os seis artefatos da noite de
07→08/10 (18 MB cada: diários com 2h23 de coleta, uma descoberta, um juiz e dois sinais) ficaram
no GitHub, e a guarda, contando run `failure` como "trabalhou", impediu que alguém refizesse a
coleta. Catorze dias depois eles expiram.

POR QUE NÃO É `git checkout` do artefato
    O artefato traz `data/` inteiro como estava no runner. Copiar por cima apagaria o que a `main`
    recebeu depois. Cada arquivo entra pela SUA porta:

      · `data/pistas_*.json`      → `pistas.sincronizar` (a porta da fila; idempotente)
      · `data/log_buscas/*.jsonl` → união pela base comum, linha a linha
      · log e painel em JSON      → `unir_conflito_de_rodada.unir_log` (carimbo vence pelo maior)
      · `data/funil/*.json`       → união de contadores
      · `data/evidencias.json`    → união por `sha256`, SÓ para item cujo arquivo exista em
                                    `evidencias/` — índice que cita arquivo ausente mente
      · `data/noite/<n>/<elo>.feito` → cópia
      · o resto                   → NÃO reaplica, e sai nomeado no relatório

MARCADOR
    Cada artefato reaplicado deixa `data/noite/<noite>/<elo>.reaplicado` com o `run_id`. Sem isso,
    o elo seguinte reaplica os mesmos artefatos a cada noite — foi o defeito do `--reaplicar` do
    PR #572.

USO
    python3 scripts/reaplicar_noite.py --noite 2026-10-08 --conferir
    python3 scripts/reaplicar_noite.py --noite 2026-10-08 --aplicar
    python3 scripts/reaplicar_noite.py --autoteste
"""
import json
import pathlib
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "scripts"))

PREFIXO = "coleta-perdida-"


# ----------------------------------------------------------------- funções puras
def elo_e_run(nome_do_artefato: str) -> tuple:
    """(elo, run) de `coleta-perdida-<elo>-<run>`. Função pura.

    O elo pode ter hífen (`sinais-fisicos`), então o run é o ÚLTIMO pedaço, e só quando é número.
    """
    nome = str(nome_do_artefato or "")
    if not nome.startswith(PREFIXO):
        return ("", "")
    resto = nome[len(PREFIXO):]
    if "-" not in resto:
        return ("", "")
    elo, numero = resto.rsplit("-", 1)
    if not numero.isdigit() or not elo:
        return ("", "")
    return (elo, numero)


def porta_de(caminho: str) -> str:
    """Por qual porta este arquivo do artefato entra. Função pura.

    "fila" · "jsonl" · "log" · "contador" · "evidencias" · "feito" · "" (não reaplica).
    """
    c = str(caminho or "").replace("\\", "/")
    if c.startswith("data/pistas_") and c.endswith(".json"):
        return "" if c == "data/pistas_rejeitadas.json" else "fila"
    if c.startswith("data/log_buscas/") and c.endswith(".jsonl"):
        return "jsonl"
    if c in ("data/log_buscas.json", "data/historico_mudancas.json",
             "data/saude_pipeline.json", "data/painel_da_noite.json"):
        return "log"
    if c.startswith("data/funil/") and c.endswith(".json"):
        return "contador"
    if c == "data/evidencias.json":
        return "evidencias"
    if c.startswith("data/noite/") and c.endswith(".feito"):
        return "feito"
    return ""


def unir_por_sha(da_arvore: list, do_artefato: list, existe) -> tuple:
    """União do índice de evidências por `sha256`, só para arquivo que EXISTE. Função pura.

    `existe(caminho)` é injetado: o índice que cita arquivo ausente mente, e preferir mentir a
    perder é a troca que este projeto não faz. Devolve (união, quantos_entraram, quantos_sem_arquivo).
    """
    por_sha, ordem = {}, []
    for item in list(da_arvore or []):
        k = str((item or {}).get("sha256") or "")
        if k and k not in por_sha:
            por_sha[k] = dict(item)
            ordem.append(k)
    novos, sem_arquivo = 0, 0
    for item in list(do_artefato or []):
        k = str((item or {}).get("sha256") or "")
        if not k or k in por_sha:
            continue
        caminho = str((item or {}).get("arquivo") or (item or {}).get("caminho") or "")
        if caminho and not existe(caminho):
            sem_arquivo += 1
            continue
        por_sha[k] = dict(item)
        ordem.append(k)
        novos += 1
    return ([por_sha[k] for k in ordem], novos, sem_arquivo)


def unir_linhas(da_arvore: list, do_artefato: list) -> list:
    """Linhas de `.jsonl` pela base comum: prefixo comum + o que cada lado acrescentou. Pura."""
    a = list(da_arvore or [])
    b = list(do_artefato or [])
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    uniao = a[:n] + a[n:] + b[n:]
    assert len(uniao) >= max(len(a), len(b)), "união menor que um dos lados"
    return uniao


def nome_da_fila_de(caminho: str) -> str:
    """O nome que a porta da fila espera: `pistas_imprensa.json`, com extensao. Funcao pura."""
    return pathlib.Path(str(caminho or "")).name


def caminho_do_reaplicado(noite: str, elo: str) -> str:
    """Onde fica o marcador de reaplicado. Função pura."""
    return f"data/noite/{noite}/{elo}.reaplicado"


# ----------------------------------------------------------------- portas de I/O
def _gh(args: list) -> str:
    try:
        r = subprocess.run(["gh"] + args, cwd=RAIZ, capture_output=True, text=True, timeout=600)
        return r.stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def artefatos_da_noite(noite: str) -> list:
    """Os artefatos `coleta-perdida-*` não expirados, mais novos que a abertura da noite. ESCREVE
    nada; só lê a API."""
    saida = _gh(["api", "repos/{owner}/{repo}/actions/artifacts?per_page=100",
                 "--jq", '.artifacts[] | select(.expired == false) '
                         '| select(.name | startswith("' + PREFIXO + '")) '
                         '| [.name, (.id|tostring), .created_at] | @tsv'])
    fora = []
    for linha in saida.splitlines():
        partes = linha.split("\t")
        if len(partes) != 3:
            continue
        nome, ident, criado = partes
        elo, run = elo_e_run(nome)
        if not elo:
            continue
        if noite and criado[:10] < noite:
            continue
        fora.append({"nome": nome, "id": ident, "criado_em": criado, "elo": elo, "run": run})
    return sorted(fora, key=lambda x: x["criado_em"])


def main(argv: list) -> int:
    if "--autoteste" in argv:
        return _autoteste()
    noite = ""
    if "--noite" in argv:
        i = argv.index("--noite")
        noite = argv[i + 1] if i + 1 < len(argv) else ""
    if not noite:
        from janela_da_noite import noite_de
        import datetime as dt
        noite = noite_de(dt.datetime.now(dt.timezone.utc).replace(tzinfo=None))
    aplicar = "--aplicar" in argv

    artefatos = artefatos_da_noite(noite)
    if not artefatos:
        print(f"· nenhum artefato `{PREFIXO}*` para a noite de {noite}")
        return 0
    print(f"· {len(artefatos)} artefato(s) da noite de {noite}:")
    feitos, recusados = [], []
    for a in artefatos:
        marcador = RAIZ / caminho_do_reaplicado(noite, a["elo"])
        ja = marcador.exists() and a["run"] in marcador.read_text(encoding="utf-8")
        print(f"   · {a['nome']} ({a['criado_em']})" + (" — já reaplicado" if ja else ""))
        if ja:
            continue
        if not aplicar:
            continue
        destino = pathlib.Path(RAIZ / ".cache" / "reaplicar" / a["nome"])
        destino.mkdir(parents=True, exist_ok=True)
        baixou = _gh(["run", "download", a["run"], "--name", a["nome"], "--dir", str(destino)])
        arquivos = sorted(q for q in destino.rglob("*") if q.is_file())
        if not arquivos:
            recusados.append(f"{a['nome']}: não baixou (artefato expirado ou acesso recusado)")
            continue
        n_portas = {}
        for q in arquivos:
            rel = str(q.relative_to(destino)).replace("\\", "/")
            porta = porta_de(rel)
            n_portas[porta or "(não reaplica)"] = n_portas.get(porta or "(não reaplica)", 0) + 1
            if not porta:
                continue
            aplicado = _aplicar_um(rel, q, porta)
            if aplicado is False:
                recusados.append(f"{a['nome']} → {rel}: a porta recusou")
        print(f"     portas: " + ", ".join(f"{k}={v}" for k, v in sorted(n_portas.items())))
        marcador.parent.mkdir(parents=True, exist_ok=True)
        # §229: todo JSON de `data/` passa pela porta atomica — escrita direta deixa arquivo
        # truncado quando o processo morre no meio, e `testar_escrita_atomica.py` cobra isso.
        from coletores_base import gravar_em
        gravar_em(marcador, {"run": a["run"], "artefato": a["nome"]})
        feitos.append(a["nome"])

    if not aplicar:
        print("  (--conferir: nada foi gravado. Use --aplicar para reaplicar.)")
        return 0
    print(f"· reaplicados: {len(feitos)}")
    for r in recusados:
        print(f"  ⚠ {r}")
    return 0


def _aplicar_um(rel: str, origem: pathlib.Path, porta: str):
    """Aplica UM arquivo pela porta dele. ESCREVE. Devolve True/False/None."""
    destino = RAIZ / rel
    try:
        if porta == "fila":
            from pistas import sincronizar
            doc = json.loads(origem.read_text(encoding="utf-8"))
            sincronizar(nome_da_fila_de(rel), {"pistas": doc.get("pistas") or []},
                        origem="reaplicacao da noite")
            return True
        if porta == "jsonl":
            a = destino.read_text(encoding="utf-8").splitlines() if destino.exists() else []
            b = origem.read_text(encoding="utf-8").splitlines()
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text("\n".join(unir_linhas(a, b)) + "\n",
                               encoding="utf-8", newline="\n")
            return True
        if porta in ("log", "contador"):
            from unir_conflito_de_rodada import unir_log, CHAVES_DE_LOG
            chave = CHAVES_DE_LOG.get(rel) if "CHAVES_DE_LOG" in dir() else None
            base = destino.read_text(encoding="utf-8") if destino.exists() else origem.read_text(encoding="utf-8")
            fundido, *_ = unir_log(rel, chave or _chave_de(rel), base,
                                   base, origem.read_text(encoding="utf-8"))
            from coletores_base import gravar_em
            gravar_em(destino, fundido)
            return True
        if porta == "evidencias":
            doc = json.loads(destino.read_text(encoding="utf-8")) if destino.exists() else {}
            novo = json.loads(origem.read_text(encoding="utf-8"))
            lista = doc.get("evidencias") if isinstance(doc.get("evidencias"), list) else []
            entrando = novo.get("evidencias") if isinstance(novo.get("evidencias"), list) else []
            uniao, n, sem = unir_por_sha(lista, entrando,
                                         lambda c: (RAIZ / c).exists())
            doc["evidencias"] = uniao
            from coletores_base import gravar_em
            gravar_em(destino, doc)
            print(f"     evidencias: +{n} no índice, {sem} sem arquivo preservado (fora)")
            return True
        if porta == "feito":
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(origem.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
            return True
    except Exception as erro:            # a recusa é dado: sai nomeada no relatório
        print(f"     ⚠ {rel}: {type(erro).__name__}: {str(erro)[:120]}")
        return False
    return None


def _chave_de(rel: str) -> str:
    """A lista que só cresce dentro daquele JSON. Função pura."""
    return {"data/log_buscas.json": "execucoes",
            "data/historico_mudancas.json": "eventos",
            "data/saude_pipeline.json": "execucoes",
            "data/painel_da_noite.json": "noites"}.get(rel, "execucoes")


def _autoteste() -> int:
    casos = []

    def ok(nome, cond):
        casos.append((nome, bool(cond)))

    ok("elo e run saem do nome", elo_e_run("coleta-perdida-diarios-37711273308")
       == ("diarios", "37711273308"))
    ok("elo com hífen não se parte", elo_e_run("coleta-perdida-sinais-fisicos-37711285165")
       == ("sinais-fisicos", "37711285165"))
    ok("nome fora do padrão devolve vazio", elo_e_run("saida-diarios-2026-10-08") == ("", ""))
    ok("run que não é número devolve vazio", elo_e_run("coleta-perdida-diarios-abc") == ("", ""))
    ok("nome nulo não quebra", elo_e_run(None) == ("", ""))

    ok("fila de pista entra pela porta da fila", porta_de("data/pistas_imprensa.json") == "fila")
    ok("recusas NÃO se reaplicam", porta_de("data/pistas_rejeitadas.json") == "")
    ok("log mensal é jsonl", porta_de("data/log_buscas/2026-10.jsonl") == "jsonl")
    ok("painel e saúde são log", porta_de("data/painel_da_noite.json") == "log"
       and porta_de("data/saude_pipeline.json") == "log")
    ok("funil é contador", porta_de("data/funil/2026-10-08.json") == "contador")
    ok("índice de evidências tem porta própria",
       porta_de("data/evidencias.json") == "evidencias")
    ok("marcador de trabalho se copia", porta_de("data/noite/2026-10-08/diarios.feito") == "feito")
    ok("o resto não se reaplica", porta_de("data/municipios.json") == ""
       and porta_de("docs/MANIFEST_SHA256.txt") == "")

    uniao, n, sem = unir_por_sha(
        [{"sha256": "a", "arquivo": "evidencias/a.pdf"}],
        [{"sha256": "b", "arquivo": "evidencias/b.pdf"},
         {"sha256": "c", "arquivo": "evidencias/sumiu.pdf"}],
        lambda c: c != "evidencias/sumiu.pdf")
    ok("evidência com arquivo entra", n == 1 and len(uniao) == 2)
    ok("evidência sem arquivo fica fora — índice não mente", sem == 1)
    ok("evidência repetida por sha não duplica",
       unir_por_sha([{"sha256": "a"}], [{"sha256": "a"}], lambda c: True)[0] == [{"sha256": "a"}])

    ok("linhas unem pela base comum",
       unir_linhas(["1", "2", "3"], ["1", "2", "4"]) == ["1", "2", "3", "4"])
    ok("a união de linhas nunca encolhe",
       len(unir_linhas(["1", "2"], ["1", "2", "3", "4"])) >= 4)
    ok("lado vazio não quebra", unir_linhas([], ["1"]) == ["1"])
    # 08/10/2026: a primeira versao passava `Path(rel).stem` para a porta da fila, e a porta
    # gravou `data/pistas_imprensa` SEM extensao -- arquivo novo, invisivel para todo portao e
    # para todo leitor. O mesmo defeito estava em `consolidar_noite.py`, e os avisos de "caminho
    # sem escritor declarado: data/pistas_imprensa" das rodadas de 07/10 eram ele.
    ok("o nome da fila leva a extensao, nao o radical",
       nome_da_fila_de("data/pistas_imprensa.json") == "pistas_imprensa.json")
    ok("o radical sozinho nao serve de nome de fila",
       nome_da_fila_de("data/pistas_doe.json").endswith(".json"))
    ok("o marcador tem caminho previsível",
       caminho_do_reaplicado("2026-10-08", "diarios") == "data/noite/2026-10-08/diarios.reaplicado")

    import dis
    nomes = set()
    for fn in (elo_e_run, porta_de, unir_por_sha, unir_linhas, caminho_do_reaplicado):
        nomes |= {i.argval for i in dis.get_instructions(fn.__code__) if isinstance(i.argval, str)}
    ok("trava estrutural: as funções puras não leem disco, não escrevem e não vão à rede",
       not ({"read_text", "write_text", "open", "urlopen", "exists", "subprocess"} & nomes))

    ruins = [n for n, bom in casos if not bom]
    for n, bom in casos:
        print(f"  {'✓' if bom else '✗'} {n}")
    if ruins:
        print(f"✗ AUTOTESTE: {len(ruins)} caso(s) reprovado(s).")
        return 1
    print(f"✓ AUTOTESTE OK — {len(casos)} casos, sem rede e sem escrita.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
