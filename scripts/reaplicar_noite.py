#!/usr/bin/env python3
"""Reaplica o trabalho que a noite perdeu (08/10/2026, A2-19; pela união do resolvedor desde 15/10).

Quando o push de um elo falha, o `_coletor.yml` sobe o que ele coletou como artefato
`coleta-perdida-<elo>-<run>`, com o manifesto da perda (`data/coleta_perdida.json`: a base do elo
e os arquivos que ele alterou). O elo seguinte reaplica, antes de coletar.

TRÊS VIAS, A MESMA UNIÃO DO REBASE
    Para cada arquivo que o elo alterou: base = o arquivo no commit de onde o elo partiu; nosso = a
    árvore (que andou); deles = o artefato. Árvore igual à base → copia o do artefato; senão a
    união é `unir_conflito_de_rodada.unir_e_gravar` — a mesma do conflito de rebase, classe por
    classe (log, fila, contador, índice, livro). O que o resolvedor recusa sai nomeado. Derivado
    não se copia: a cadeia o regera. Até 15/10 este arquivo tinha portas próprias (união de linhas,
    contador pelo maior, união por chave, dono único) que repetiam o resolvedor com outra regra, e
    recusavam o livro de fontes que o resolvedor já sabia unir.

    `data/evidencias.json` tem uma regra a mais: o artefato não leva `evidencias/`, então entrada
    nova cujo arquivo (binário, texto ou OCR) não está na árvore fica fora, e entrada antiga que
    ganhou um texto ausente volta ao que era — índice que cita arquivo ausente mente.

MARCADOR
    Cada artefato reaplicado deixa `data/noite/<noite>/<elo>.reaplicado` com o `run_id`.

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
from despachar_temporizadores import _gh  # noqa: E402

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


MANIFESTO_DA_PERDA = "data/coleta_perdida.json"


SEM_BASE = object()   # o commit-base do elo não está nesta árvore (≠ arquivo ausente na base: None)
CAMPOS_DE_ARQUIVO = ("arquivo", "texto_arquivo", "texto_integral", "ocr_arquivo")


def reaplicar_arquivo(rel: str, alterados, base, arvore, artefato, destino, existe=None) -> str:
    """Reaplica UM arquivo do artefato em `destino`, por três vias. Devolve o que fez.

    "fora" (o elo não o alterou, ou é derivado) · "igual" · "copiado" · a descrição da união ·
    "recusa: …". `base`, `arvore`, `artefato` em texto (None = ausente). `existe(caminho)` filtra o
    índice de evidências."""
    import unir_conflito_de_rodada as u
    if (rel == MANIFESTO_DA_PERDA or rel not in set(alterados or ()) or u.e_regeneravel(rel)
            or rel in u.DERIVADOS_COM_GERADOR):
        return "fora"
    if arvore == artefato:
        return "igual"
    if arvore == base:
        pathlib.Path(destino).parent.mkdir(parents=True, exist_ok=True)
        u._escrever(destino, artefato)
        feito = "copiado"
    elif base is SEM_BASE:
        return "recusa: a base do elo não está no histórico desta árvore"
    else:
        try:
            feito = u.unir_e_gravar(rel, base, arvore, artefato, destino)
        except (u.Recusa, ValueError) as e:
            return f"recusa: {e}"
    if rel == "data/evidencias.json" and existe:
        doc = json.loads(pathlib.Path(destino).read_text(encoding="utf-8"))
        ja = (json.loads(arvore) if arvore else {}).get("itens") or {}
        inteiro = lambda v: all(existe(str(v.get(c))) for c in CAMPOS_DE_ARQUIVO if v.get(c))
        doc["itens"] = {k: (v if inteiro(v or {}) else ja[k]) for k, v in (doc.get("itens") or {}).items()
                        if (k in ja or (existe(str((v or {}).get("arquivo") or "")) and inteiro(v)))}
        u.gravar_no_formato_do_produtor(destino, doc)
    return feito


def _na_base(base: str, rel: str):
    """Conteúdo de `rel` no commit `base`; None se o arquivo não existia lá; SEM_BASE sem o commit. Só lê.
    24/11/2026: `data/funil/<dia>.json` novo dos dois lados era recusado como "base fora do histórico"."""
    tem = lambda: not subprocess.run(["git", "cat-file", "-e", f"{base}^{{commit}}"], cwd=RAIZ,  # noqa: E731
                                     capture_output=True).returncode
    # 25/11/2026: o clone do runner é raso; a base de uma noite antiga vem pelo sha, sem o histórico.
    if base and not tem():
        subprocess.run(["git", "fetch", "-q", "--depth=1", "origin", base], cwd=RAIZ, capture_output=True)
    if not base or not tem():
        return SEM_BASE
    r = subprocess.run(["git", "show", f"{base}:{rel}"], cwd=RAIZ, capture_output=True)
    return r.stdout.decode("utf-8") if r.returncode == 0 else None


def caminho_do_reaplicado(noite: str, elo: str) -> str:
    """Onde fica o marcador de reaplicado. Função pura."""
    return f"data/noite/{noite}/{elo}.reaplicado"


# ----------------------------------------------------------------- portas de I/O
def artefatos_da_noite(noite: str) -> list:
    """Os artefatos `coleta-perdida-*` não expirados, mais novos que a abertura da noite. ESCREVE
    nada; só lê a API."""
    # 24/11/2026: a API devolve do mais novo para o mais velho, 100 por página; só a primeira página
    # deixava de fora o artefato de 22/11 (coleta-perdida-atualizar-44980777132) num dia de 100+
    # artefatos. Lê página a página até passar da abertura da noite.
    linhas, pagina = [], 1
    while True:
        saida = _gh(["api", f"repos/{{owner}}/{{repo}}/actions/artifacts?per_page=100&page={pagina}",
                     "--jq", '.artifacts[] | [.name, (.id|tostring), .created_at, (.expired|tostring)] | @tsv'],
                    timeout=600)
        pag = [l.split("\t") for l in saida.splitlines() if l.count("\t") == 3]
        linhas += [p[:3] for p in pag if p[3] == "false" and p[0].startswith(PREFIXO)]
        if len(pag) < 100 or not noite or min(p[2] for p in pag)[:10] < noite:
            break
        pagina += 1
    fora = []
    for partes in linhas:
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
    # 09/10/2026: `--artefato` escolhe UM artefato pelo nome, e pode repetir. A reaplicacao da
    # noite inteira e o caminho normal; escolher nasceu de um pedido da editoria por dois
    # artefatos nomeados, e e tambem o que permite reaplicar um elo cuja porta ja foi corrigida
    # sem arrastar os outros.
    escolhidos = [argv[i + 1] for i, a in enumerate(argv)
                  if a == "--artefato" and i + 1 < len(argv)]
    # 24/11/2026 (D3): `--caminho` (com `--artefato`) refaz só os caminhos que a união recusou da
    # primeira vez, depois que a regra deles chegou. Ignora o marcador: os outros caminhos já
    # voltaram, e reaplicá-los dobraria as linhas novas dos logs.
    caminhos = {argv[i + 1] for i, a in enumerate(argv) if a == "--caminho" and i + 1 < len(argv)}
    if caminhos and not escolhidos:
        print("X --caminho exige --artefato")
        return 2

    artefatos = artefatos_da_noite(noite)
    if escolhidos:
        pedidos = set(escolhidos)
        achados = {a["nome"] for a in artefatos}
        for nome in sorted(pedidos - achados):
            print(f"  ⚠ {nome}: nao esta entre os artefatos da noite de {noite}")
        artefatos = [a for a in artefatos if a["nome"] in pedidos]
    if not artefatos:
        print(f"· nenhum artefato `{PREFIXO}*` para a noite de {noite}")
        return 0
    print(f"· {len(artefatos)} artefato(s) da noite de {noite}:")
    feitos, recusados = [], []
    for a in artefatos:
        marcador = RAIZ / caminho_do_reaplicado(noite, a["elo"])
        ja = marcador.exists() and a["run"] in marcador.read_text(encoding="utf-8")
        print(f"   · {a['nome']} ({a['criado_em']})" + (" — já reaplicado" if ja else ""))
        if ja and not caminhos:
            continue
        if not aplicar:
            continue
        destino = pathlib.Path(RAIZ / ".cache" / "reaplicar" / a["nome"])
        destino.mkdir(parents=True, exist_ok=True)
        baixou = _gh(["run", "download", a["run"], "--name", a["nome"], "--dir", str(destino)], timeout=600)
        arquivos = sorted(q for q in destino.rglob("*") if q.is_file())
        if not arquivos:
            recusados.append(f"{a['nome']}: não baixou (artefato expirado ou acesso recusado)")
            continue
        perda = {}
        _m = destino / MANIFESTO_DA_PERDA
        if _m.exists():
            try:
                perda = json.loads(_m.read_text(encoding="utf-8"))
            except ValueError:
                perda = {}
        n_portas = {}
        for q in arquivos:
            rel = str(q.relative_to(destino)).replace("\\", "/")
            if caminhos and rel not in caminhos:
                continue
            arv = (RAIZ / rel).read_text(encoding="utf-8") if (RAIZ / rel).exists() else None
            try:
                art = q.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            feito = reaplicar_arquivo(rel, perda.get("alterados"), _na_base(perda.get("base", ""), rel),
                                      arv, art, RAIZ / rel, lambda c: bool(c) and (RAIZ / c).exists())
            classe = feito.split(":")[0] if feito.startswith("recusa") else feito.split(" ")[0]
            n_portas[classe] = n_portas.get(classe, 0) + 1
            if feito.startswith("recusa"):
                recusados.append(f"{a['nome']} → {rel}: {feito}")
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


def _autoteste() -> int:
    import tempfile
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
    ok("o marcador tem caminho previsível",
       caminho_do_reaplicado("2026-10-08", "diarios") == "data/noite/2026-10-08/diarios.reaplicado")

    with tempfile.TemporaryDirectory() as t:
        d = pathlib.Path(t) / "x"

        def r(rel, alt, base, arv, art, existe=None):
            return reaplicar_arquivo(rel, alt, base, arv, art, d, existe)

        def lido():
            return d.read_text(encoding="utf-8")

        ok("arquivo que o elo não alterou fica fora", r("data/x.json", [], "1", "1", "2") == "fora")
        ok("derivado nunca vem do artefato",
           r("docs/MANIFEST_SHA256.txt", ["docs/MANIFEST_SHA256.txt"], "a", "a", "b") == "fora")
        ok("F45: árvore como na base → copia o do artefato",
           r("data/clima.json", ["data/clima.json"], "v1", "v1", "v2") == "copiado" and lido() == "v2")
        ok("arquivo novo do elo entra", r("data/novo.json", ["data/novo.json"], None, None, "n") == "copiado")
        ok("F45: outro escritor sem classe de união → recusa nomeada",
           r("data/clima.json", ["data/clima.json"], "v1", "v3", "v2").startswith("recusa"))
        ok("sem a base no histórico → recusa nomeada",
           r("data/log_buscas/2026-10.jsonl", ["data/log_buscas/2026-10.jsonl"], SEM_BASE, "a\n", "b\n")
           .startswith("recusa"))
        _fn = lambda n: json.dumps({"data": "2026-11-22", "etapas": {"e": {"contagem": n}}})
        ok("funil do dia novo dos dois lados (ausente na base) une pela base vazia, não recusa",
           not r("data/funil/2026-11-22.json", ["data/funil/2026-11-22.json"], None, _fn(2), _fn(3)).startswith("recusa")
           and json.loads(lido())["etapas"]["e"]["contagem"] == 5)
        ok("log mensal une pela base comum (a do resolvedor)",
           not r("data/log_buscas/2026-10.jsonl", ["data/log_buscas/2026-10.jsonl"],
                 "a\n", "a\nb\n", "a\nc\n").startswith("recusa")
           and sorted(lido().split()) == ["a", "b", "c"])
        livro = lambda *f: json.dumps({"municipios": {"1": {"nivel_verificacao": "nacional",
                                       "ultima_verificacao": "2026-10-15", "fontes": [
                                           {"fonte": x, "data": "2026-10-15"} for x in f]}}})
        r("data/fontes_consultadas.json", ["data/fontes_consultadas.json"],
          livro("DOU"), livro("DOU", "Busca web"), livro("DOU", "QD"))
        ok("F58: o livro de fontes volta com as consultas dos dois lados",
           sorted(x["fonte"] for x in json.loads(lido())["municipios"]["1"]["fontes"])
           == ["Busca web", "DOU", "QD"])
        ev = lambda **i: json.dumps({"itens": {k: {"arquivo": v} for k, v in i.items()}})
        r("data/evidencias.json", ["data/evidencias.json"], ev(a="e/a"), ev(a="e/a", b="e/b"),
          ev(a="e/a", c="e/c", z="e/sumiu"), existe=lambda c: c != "e/sumiu")
        ok("F55: evidência nova entra; sem arquivo preservado fica fora — índice não mente",
           sorted(json.loads(lido())["itens"]) == ["a", "b", "c"])
        ev2 = lambda **i: json.dumps({"itens": {k: dict(v) for k, v in i.items()}})
        r("data/evidencias.json", ["data/evidencias.json"], ev2(a={"arquivo": "e/a"}),
          ev2(a={"arquivo": "e/a"}), ev2(a={"arquivo": "e/a", "texto_arquivo": "e/a.txt"}),
          existe=lambda c: c != "e/a.txt")
        ok("texto prometido e ausente: a entrada antiga volta ao que era",
           json.loads(lido())["itens"] == {"a": {"arquivo": "e/a"}})

    ruins = [n for n, bom in casos if not bom]
    for n, bom in casos:
        print(f"  {'✓' if bom else '✗'} {n}")
    if ruins:
        print(f"✗ AUTOTESTE: {len(ruins)} caso(s) reprovado(s).")
        return 1
    print(f"✓ AUTOTESTE OK — {len(casos)} casos, sem rede.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
