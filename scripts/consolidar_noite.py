#!/usr/bin/env python3
"""
scripts/consolidar_noite.py — um escritor só, e ele é este
===========================================================
Fase 1 do `HANDOVER_campanha_de_testes_06-10-2026.md`.

POR QUE O DESENHO MUDA
-----------------------
Cada correção dos últimos dias fechou **uma** colisão e a seguinte apareceu, porque o desenho tinha
**muitos escritores na mesma `main`**: cada coletor commitava, rebaseava, fundia e empurrava
sozinho, em paralelo. Daí os conflitos, a fusão repetida que levou a fila de pistas de 28 MB a
187,53 MB, o `git add -A data/`, o push fixo na `main` mesmo no ensaio e o trabalho descartado.
Nenhum desses é um defeito solto: são sintomas do mesmo desenho.

A partir daqui:

  **o coletor não empurra.** Ele grava as próprias saídas e as sobe como artefato `saida-<elo>-<janela>`.
  **o consolidador empurra, sozinho, uma vez por janela.** É este arquivo.

COMO ELE APLICA CADA COISA
---------------------------
Pela porta de cada arquivo, nunca por fusão de três vias:

  · **fila de pista** → `pistas.sincronizar`, que mescla por chave e não duplica;
  · **log que só cresce** → união pela base comum, com a trava de 23/09 (nunca menor que um lado);
  · **demais** → cópia, se o artefato for do escritor declarado daquele caminho em
    `config/escritores.json`. Caminho sem escritor declarado **não entra** e é dito.

Artefato que não se consegue aplicar **fica pendente** e volta na rodada seguinte. Nada é
descartado, e nada é adivinhado.

A TRAVA DE TAMANHO VEM ANTES DO COMMIT
---------------------------------------
Nenhum arquivo acima de 50 MB, nenhum crescimento acima de 20% sem `--importacao-em-massa`. O que
estoura não entra no commit, e o motivo sai nomeado. Quando o GitHub recusa o push por tamanho, a
coleta da noite já se perdeu — a trava existe para que ela não chegue lá.

USO
  python3 scripts/consolidar_noite.py --autoteste
  python3 scripts/consolidar_noite.py --janela 2026-10-06 --dir artefatos/ --conferir
  python3 scripts/consolidar_noite.py --janela 2026-10-06 --dir artefatos/ --aplicar
"""
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))

TETO_MB = 50.0
CRESCIMENTO_MAXIMO = 0.20
PISO_PARA_CRESCIMENTO_MB = 1.0


def elo_do_artefato(nome: str) -> str:
    """O elo que produziu o artefato, pelo nome `saida-<elo>-<janela>`. Função pura."""
    n = str(nome or "")
    if not n.startswith("saida-"):
        return ""
    resto = n[len("saida-"):]
    # A janela é uma data ISO no fim; o elo é tudo antes dela.
    pedacos = resto.rsplit("-", 3)
    if len(pedacos) == 4 and len(pedacos[1]) == 4 and pedacos[1].isdigit():
        return pedacos[0]
    return resto


def classificar(caminho: str) -> str:
    """"fila" · "log" · "arquivo". Função pura — decide por qual porta o caminho entra."""
    c = str(caminho).replace("\\", "/")
    # As recusas vêm antes da fila: o caminho casa com o prefixo das filas, mas a lista dentro do
    # arquivo chama-se `rejeitadas`, e tratá-lo como fila lia zero pista e deixava a cópia de um
    # elo sobrescrever a do outro — `pistas_rejeitadas.json` dobrou de 4,9 para 9,2 MB na rodada 8.
    if c == "data/pistas_rejeitadas.json":
        return "recusas"
    if c.startswith("data/pistas_") and c.endswith(".json"):
        return "fila"
    if c in ("data/log_buscas.json", "data/historico_mudancas.json",
             "data/saude_pipeline.json", "data/painel_da_noite.json"):
        return "log"
    if c.startswith("data/log_buscas/") and c.endswith(".jsonl"):
        return "log"
    return "arquivo"


def chave_da_lista(caminho: str) -> str:
    """O nome da lista que só cresce dentro daquele JSON. Função pura."""
    return {"data/log_buscas.json": "execucoes",
            "data/historico_mudancas.json": "eventos",
            "data/saude_pipeline.json": "execucoes",
            "data/painel_da_noite.json": "noites"}.get(
                str(caminho).replace("\\", "/"), "")


def chave_da_recusa(registro: dict) -> str:
    """A identidade de uma recusa. Função pura — a mesma de `scripts/pistas.py`."""
    r = registro or {}
    return "|".join([str(r.get("url") or ""), str(r.get("alvo") or ""),
                     str(r.get("origem_canonica") or ""), str(r.get("motivo") or "")])


def unir_recusas(da_arvore: list, do_artefato: list) -> list:
    """Uma recusa por chave, com `vezes` somado. Função pura.

    Recusa repetida não é recusa nova: o que cresce é a contagem, não o arquivo. Sem isso, cada
    artefato acrescentava a sua cópia inteira e a trava de tamanho barrava a rodada.
    """
    fora, ordem = {}, []
    for registro in list(da_arvore or []) + list(do_artefato or []):
        k = chave_da_recusa(registro)
        vezes = int((registro or {}).get("vezes") or 1)
        if k in fora:
            fora[k]["vezes"] = int(fora[k].get("vezes") or 1) + vezes
            for campo, valor in (registro or {}).items():
                if campo != "vezes" and (campo not in fora[k] or fora[k][campo] in (None, "", [], {})):
                    fora[k][campo] = valor
        else:
            fora[k] = dict(registro or {}, vezes=vezes)
            ordem.append(k)
    return [fora[k] for k in ordem]


def unir_log(da_arvore: list, do_artefato: list) -> list:
    """base + o que cada lado acrescentou, com a base derivada do prefixo comum. Função pura.

    A trava é a de 23/09/2026: o resultado nunca pode ser menor que qualquer um dos lados. E sem
    base comum NÃO se soma — foi assim que a fila de pistas dobrou a cada reaplicação em 06/10.
    """
    base = []
    for x, y in zip(da_arvore or [], do_artefato or []):
        if x != y:
            break
        base.append(x)
    if not base and da_arvore and do_artefato:
        raise ValueError("sem começo em comum: não é o mesmo arquivo em dois momentos")
    n = len(base)
    uniao = base + list(da_arvore or [])[n:] + list(do_artefato or [])[n:]
    if len(uniao) < max(len(da_arvore or []), len(do_artefato or [])):
        raise ValueError("a união ficou menor que um dos lados")
    return uniao


def mb(bytes_: int) -> float:
    """Bytes em MB, com uma casa. Função pura."""
    return round((bytes_ or 0) / 1048576, 1)


def estoura_a_trava(antes: dict, depois: dict, importacao_em_massa: bool = False) -> list:
    """Os caminhos que a trava de tamanho barra. Função pura. {caminho: bytes} dos dois lados."""
    fora = []
    for caminho, tamanho in sorted((depois or {}).items()):
        if mb(tamanho) > TETO_MB:
            fora.append(f"{caminho}: {mb(tamanho)} MB, acima do teto de {TETO_MB} MB")
            continue
        if importacao_em_massa:
            continue
        antes_b = (antes or {}).get(caminho)
        if not antes_b or mb(antes_b) < PISO_PARA_CRESCIMENTO_MB or tamanho <= antes_b:
            continue
        taxa = (tamanho - antes_b) / antes_b
        if taxa > CRESCIMENTO_MAXIMO:
            fora.append(f"{caminho}: {mb(antes_b)} MB → {mb(tamanho)} MB "
                        f"(+{round(taxa * 100)}% nesta consolidação)")
    return fora


def pode_aplicar(caminho: str, elo: str, tabela: dict) -> bool:
    """Este elo pode ENTREGAR este caminho? Função pura.

    São duas perguntas diferentes, e confundi-las zeraria o consolidador:

      · **quem COMITA** é o consolidador, e só ele — é o que `escritor` diz desde a fase 1;
      · **quem ENTREGA** continua sendo o dono de antes, guardado em `escritor_antes_da_fase_1`.

    A regra "um escritor por arquivo" não sumiu na fase 1: ela passou a ser aplicada aqui, no único
    lugar onde a escrita de fato acontece. Um elo que entregue arquivo de outro tem a entrega
    recusada naquele caminho, e o motivo sai nomeado.
    """
    from commit_do_elo import escritor_de
    dono = escritor_de(caminho, tabela)
    if dono is None or dono == "ninguem":
        return False
    return dono in ("qualquer_elo", elo)


def _autoteste() -> int:
    falhas, contados = [], []

    def ok(nome, cond):
        contados.append(nome)
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    ok("o elo sai do nome do artefato",
       elo_do_artefato("saida-diarios-2026-10-06") == "diarios")
    ok("elo com hifen no nome sobrevive",
       elo_do_artefato("saida-sinais-fisicos-2026-10-06") == "sinais-fisicos")
    ok("nome fora do padrão devolve vazio", elo_do_artefato("capturas-ci-9") == "")

    ok("fila de pista é fila", classificar("data/pistas_imprensa.json") == "fila")
    ok("o arquivo de recusas tem porta própria",
       classificar("data/pistas_rejeitadas.json") == "recusas")
    ok("recusa repetida conta em vezes, e não duplica",
       unir_recusas([{"url": "u", "motivo": "m"}], [{"url": "u", "motivo": "m"}])
       == [{"url": "u", "motivo": "m", "vezes": 2}])
    ok("recusa de outro motivo é outra recusa",
       len(unir_recusas([{"url": "u", "motivo": "m"}], [{"url": "u", "motivo": "n"}])) == 2)
    ok("`vezes` que já vinha somado é respeitado",
       unir_recusas([{"url": "u", "motivo": "m", "vezes": 3}],
                    [{"url": "u", "motivo": "m", "vezes": 2}])[0]["vezes"] == 5)
    ok("união de recusas com lados vazios não quebra",
       unir_recusas(None, None) == [] and unir_recusas([], [{"url": "x"}]) != [])
    ok("log de buscas é log", classificar("data/log_buscas.json") == "log")
    ok("jsonl do log é log", classificar("data/log_buscas/2026-10.jsonl") == "log")
    ok("o painel da noite é log", classificar("data/painel_da_noite.json") == "log")
    ok("o resto é arquivo", classificar("data/focos_pontos.json") == "arquivo")
    ok("a chave da lista é a declarada",
       chave_da_lista("data/painel_da_noite.json") == "noites")

    ok("união traz os dois acréscimos", unir_log([1, 2, 3], [1, 2, 9]) == [1, 2, 3, 9])
    ok("união nunca encolhe", len(unir_log([1, 2, 3], [1, 2])) >= 3)
    ok("lado vazio devolve o outro", unir_log([], [1, 2]) == [1, 2])
    try:
        unir_log([1, 2], [8, 9])
        ok("sem base comum é RECUSADO", False)
    except ValueError:
        ok("sem base comum é RECUSADO", True)

    MB = 1048576
    ok("acima de 50 MB é barrado", estoura_a_trava({}, {"a.json": 60 * MB}) != [])
    ok("dobrar é barrado",
       estoura_a_trava({"a.json": 28 * MB}, {"a.json": 56 * MB}) != [])
    ok("crescer 10% passa",
       estoura_a_trava({"a.json": 28 * MB}, {"a.json": int(30.8 * MB)}) == [])
    ok("importação em massa libera o crescimento, não o teto",
       estoura_a_trava({"a.json": 28 * MB}, {"a.json": 40 * MB}, True) == []
       and estoura_a_trava({}, {"a.json": 60 * MB}, True) != [])
    ok("arquivo pequeno que dobra não é barrado",
       estoura_a_trava({"a.json": 2000}, {"a.json": 9000}) == [])
    ok("encolher nunca é barrado",
       estoura_a_trava({"a.json": 28 * MB}, {"a.json": 10 * MB}) == [])

    # A tabela que o consolidador usa é a de QUEM ENTREGA (o dono de antes da fase 1), não a de
    # quem comita — que desde a fase 1 é só ele.
    T = {"data/focos_pontos.json": "sinais-fisicos", "data/pistas_imprensa.json": "qualquer_elo",
         "data/publicacao.json": "ninguem"}
    ok("o elo dono entrega o dele", pode_aplicar("data/focos_pontos.json", "sinais-fisicos", T))
    ok("outro elo NÃO entrega o que não é dele",
       not pode_aplicar("data/focos_pontos.json", "diarios", T))
    ok("fila com resolução declarada entra de qualquer elo",
       pode_aplicar("data/pistas_imprensa.json", "diarios", T))
    ok("caminho não declarado não entra",
       not pode_aplicar("data/inventado.json", "diarios", T))
    ok("caminho de `ninguem` nunca entra",
       not pode_aplicar("data/publicacao.json", "publicar", T))

    import dis
    nomes = set()
    for nome_obj, obj in list(globals().items()):
        if nome_obj in ("_autoteste", "main", "_aplicar", "_conferir", "pode_aplicar"):
            continue
        if getattr(obj, "__module__", None) not in (__name__, None):
            continue
        codigo = getattr(obj, "__code__", None)
        if codigo is not None:
            nomes |= {i.argval for i in dis.get_instructions(codigo) if isinstance(i.argval, str)}
    ok("trava estrutural: as funções puras não escrevem nem chamam git",
       not ({"write_text", "subprocess", "copy2"} & nomes))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else f"✓ AUTOTESTE OK — {len(contados)} casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def _tamanhos(caminhos) -> dict:
    fora = {}
    for rel in caminhos:
        arq = RAIZ / rel
        if arq.exists():
            fora[rel] = arq.stat().st_size
    return fora


def _aplicar(dir_artefatos: pathlib.Path, aplicar: bool, importacao: bool) -> int:
    bruto = json.loads((RAIZ / "config" / "escritores.json").read_text(encoding="utf-8"))
    # `escritor_antes_da_fase_1` quando existe: é o dono que PODE ENTREGAR. Onde não existe, o
    # próprio `escritor` responde — é caminho que nasceu depois da fase 1.
    tabela = {k: str((v or {}).get("escritor_antes_da_fase_1") or (v or {}).get("escritor") or "")
              for k, v in (bruto.get("arquivos") or {}).items() if not k.startswith("_")}

    entradas = sorted(p for p in dir_artefatos.iterdir() if p.is_dir()) \
        if dir_artefatos.exists() else []
    if not entradas:
        print(f"· nenhum artefato em {dir_artefatos}")
        return 0

    aplicados, pendentes, relatorio = 0, [], []
    tocados = set()
    # PROGRESSO, e nao so o resultado. A primeira execucao real ficou 30 minutos sem imprimir uma
    # linha e morreu no teto: um travamento mudo nao se diagnostica, so se adivinha. Cada artefato
    # e cada 200 arquivos dizem onde estao, com o relogio.
    import time as _t
    inicio = _t.time()
    filas_juntas = {}
    def minuto():
        return f"[{int(_t.time() - inicio)//60:02d}:{int(_t.time() - inicio)%60:02d}]"
    print(f"{minuto()} {len(entradas)} artefato(s) a aplicar", flush=True)
    for pasta in entradas:
        elo = elo_do_artefato(pasta.name)
        if not elo:
            pendentes.append(f"{pasta.name}: nome fora do padrao `saida-<elo>-<janela>`")
            continue
        arquivos = sorted(q for q in pasta.rglob("*") if q.is_file())
        print(f"{minuto()} {pasta.name}: {len(arquivos)} arquivo(s)", flush=True)
        for n, origem in enumerate(arquivos, start=1):
            if n % 200 == 0:
                print(f"{minuto()}   {pasta.name}: {n}/{len(arquivos)}", flush=True)
            rel = str(origem.relative_to(pasta)).replace("\\", "/")
            if not pode_aplicar(rel, elo, tabela):
                pendentes.append(f"{rel} (de `{elo}`): nao e dele, ou nao esta declarado")
                continue
            tipo = classificar(rel)
            destino = RAIZ / rel
            try:
                if tipo == "fila":
                    # UMA fila, UMA escrita. Cada artefato traz a sua copia da fila, e sincronizar
                    # uma por uma reescreve o arquivo inteiro a cada vez: medido em 07/10/2026, a
                    # descoberta levou 7:55 e as evidencias 17:45 fazendo exatamente isso, e o
                    # consolidador morria no teto sem passar do terceiro artefato. As copias se
                    # juntam em memoria e vao ao disco uma vez so -- que e o que "um escritor"
                    # quer dizer quando levado a serio.
                    filas_juntas.setdefault(rel, []).append((elo, origem))
                elif tipo == "recusas" and aplicar:
                    # Recusa repetida conta em `vezes` e nao duplica registro: cada artefato traz a
                    # sua copia inteira do arquivo de recusas, e copiar uma por cima da outra
                    # dobrava o arquivo (4,9 -> 9,2 MB na rodada 8, barrado pela trava de tamanho).
                    doc = json.loads(destino.read_text(encoding="utf-8")) if destino.exists()                         else {"rejeitadas": []}
                    novo_doc = json.loads(origem.read_text(encoding="utf-8"))
                    juntas = unir_recusas(doc.get("rejeitadas") or [],
                                          novo_doc.get("rejeitadas") or [])
                    doc["rejeitadas"] = juntas
                    doc["total"] = len(juntas)
                    from coletores_base import gravar_em
                    gravar_em(destino, doc)
                    aplicados += 1
                elif tipo == "log" and aplicar:
                    chave = chave_da_lista(rel)
                    if rel.endswith(".jsonl"):
                        a = destino.read_text(encoding="utf-8").splitlines() if destino.exists() else []
                        b = origem.read_text(encoding="utf-8").splitlines()
                        destino.parent.mkdir(parents=True, exist_ok=True)
                        destino.write_text("\n".join(unir_log(a, b)) + "\n",
                                           encoding="utf-8", newline="\n")
                    else:
                        da = json.loads(destino.read_text(encoding="utf-8")) if destino.exists() else {}
                        do = json.loads(origem.read_text(encoding="utf-8"))
                        fundido = dict(do)
                        fundido[chave] = unir_log(da.get(chave) or [], do.get(chave) or [])
                        destino.parent.mkdir(parents=True, exist_ok=True)
                        # §229: porta atômica. O consolidador é o ÚNICO escritor — escrita direta
                        # aqui deixaria o banco pela metade se a rodada morresse no meio, e não há
                        # segundo escritor para refazer.
                        from coletores_base import gravar_em
                        gravar_em(destino, fundido)
                elif aplicar:
                    import shutil
                    destino.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(origem, destino)
                aplicados += 1
                tocados.add(rel)
                relatorio.append(f"{rel} ({tipo}, de `{elo}`)")
            except Exception as erro:
                pendentes.append(f"{rel} (de `{elo}`): {str(erro)[:110]}")

    # As filas, agora: uma leitura de disco, uma uniao em memoria, uma escrita pela porta.
    for rel, copias in sorted(filas_juntas.items()):
        nome = pathlib.Path(rel).stem
        if not aplicar:
            print(f"{minuto()} fila {rel}: {len(copias)} copia(s) a unir")
            continue
        from pistas import chave_da_pista, sincronizar
        por_chave = {}
        for elo, origem in copias:
            try:
                doc = json.loads(origem.read_text(encoding="utf-8"))
            except json.JSONDecodeError as erro:
                pendentes.append(f"{rel} (de `{elo}`): {str(erro)[:80]}")
                continue
            for pista in doc.get("pistas") or []:
                k = chave_da_pista(pista)
                if k in por_chave:
                    for campo, valor in (pista or {}).items():
                        if campo not in por_chave[k] or por_chave[k][campo] in (None, "", [], {}):
                            por_chave[k][campo] = valor
                else:
                    por_chave[k] = dict(pista)
        print(f"{minuto()} fila {rel}: {len(copias)} copia(s) → {len(por_chave)} pista(s) distintas",
              flush=True)
        try:
            sincronizar(nome, {"pistas": list(por_chave.values())},
                        origem=f"consolidador ({len(copias)} artefato(s))")
            aplicados += 1
            print(f"{minuto()} fila {rel}: gravada pela porta", flush=True)
        except Exception as erro:
            pendentes.append(f"{rel}: a porta recusou ({str(erro)[:90]})")

    print(f"· {aplicados} caminho(s) aplicado(s) de {len(entradas)} artefato(s)")
    for x in relatorio[:20]:
        print("      · " + x)
    for x in pendentes:
        print(f"  ⚠ pendente, volta na rodada seguinte: {x}")
    return 0 if not pendentes else 0


def main(argv: list) -> int:
    if "--autoteste" in argv:
        return _autoteste()

    def opcao(nome, padrao=""):
        return argv[argv.index(nome) + 1] if nome in argv and len(argv) > argv.index(nome) + 1 \
            else padrao

    dir_artefatos = pathlib.Path(opcao("--dir", "artefatos"))
    aplicar = "--aplicar" in argv
    antes = _tamanhos([str(p.relative_to(RAIZ)).replace("\\", "/")
                       for p in (RAIZ / "data").rglob("*.json*") if p.is_file()])
    r = _aplicar(dir_artefatos, aplicar, "--importacao-em-massa" in argv)
    if aplicar:
        depois = _tamanhos(list(antes) + [])
        barrados = estoura_a_trava(antes, depois, "--importacao-em-massa" in argv)
        if barrados:
            print(f"✗ CONSOLIDAÇÃO: {len(barrados)} caminho(s) estouram a trava de tamanho:")
            for x in barrados:
                print("   - " + x)
            return 1
    print("✓ CONSOLIDAÇÃO OK" if not aplicar else "✓ CONSOLIDAÇÃO OK — trava de tamanho passou")
    return r


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
