#!/usr/bin/env python3
"""Resolve o conflito de rebase da rodada de atualização — só onde a resolução é conhecida.

POR QUE ESTE ARQUIVO EXISTE (27/09/2026, §246)
==============================================
O passo de commit da rodada tenta `git rebase` seis vezes e desiste. Medido nas rodadas de
24 e 25/09: seis tentativas, seis conflitos idênticos, nestes arquivos —

    data/log_buscas.json  data/fontes_consultadas.json  data/pistas_imprensa.json
    data/pistas_revisao.json  docs/FILA_PISTAS.md  docs/MANIFEST_SHA256.txt

A causa estrutural: `data/log_buscas.json` tem 20,7 MB em UMA ÚNICA LINHA. Qualquer mudança
dos dois lados é conflito textual garantido, porque não existe linha para o git casar. E
`busca_web_cadencia.yml` commita esse arquivo a cada 2 horas, enquanto a rodada leva mais que
isso. O laço aborta e repete com o mesmo conteúdo: repetir só resolve *push recusado*, nunca
conflito.

O QUE ESTE SCRIPT RESOLVE, E O QUE ELE RECUSA
=============================================
Ele resolve DUAS classes, e recusa todo o resto. Recusar é o comportamento correto: arbitrar
uma mesclagem que ninguém decidiu é como se apagam evidências sem aviso. Em 23/09/2026 uma
união por CONTEÚDO produziu um log menor que cada um dos lados — quase 3.000 execuções
sumiram caladas. A regra do projeto nasceu daí: une-se pela BASE COMUM, nunca por conteúdo.

1. LOG QUE SÓ CRESCE (`data/log_buscas.json`, `data/historico_mudancas.json`)
   Formato: escalares no topo mais UMA lista que só recebe itens no fim.
   Resolução: `base + nossos_novos + deles_novos`, onde "novos" é o que vem depois dos
   `n` itens da base. Antes de unir, confere que os dois lados realmente COMEÇAM com a base
   item a item; se não começarem, o arquivo não se comportou como append-only nesta ocasião
   e o script RECUSA em vez de adivinhar. Depois de unir, confere que o total é maior ou
   igual a cada lado — a trava que faltava em 23/09.

2. ARQUIVO REGENERÁVEL (`docs/MANIFEST_SHA256.txt`, `docs/FILA_PISTAS.md`,
   `data/pistas_revisao.json`)
   São função de outros dados, não fonte. Casar linha a linha não faz sentido: resolve-se
   com a versão de cima (a `main`) e a cadeia canônica regenera depois. O script os NOMEIA na
   saída, em `REGENERAR=`, para que quem chamou saiba que precisa regenerar.

Tudo o mais é recusado com o nome do arquivo e o motivo. Hoje isso inclui, de propósito,
`data/pistas_imprensa.json` e `data/fontes_consultadas.json`: os dois lados alteram os MESMOS
registros (status de triagem num, `ultima_verificacao` e `fontes` por município no outro), e
escolher qual vence é política de mesclagem — decisão da editoria, não deste script.

ESTÁGIOS DO GIT, E A ARMADILHA QUE NÃO SE APLICA AQUI
=====================================================
Num conflito, `git show :1:arquivo` é a BASE comum, `:2:` é "nosso" e `:3:` é "deles".
Durante um REBASE os dois últimos vêm invertidos em relação à intuição: "nosso" é o upstream
em que se está reaplicando, e "deles" é o commit da rodada sendo reaplicado. Para a classe 1
isso não importa — a união é simétrica. Para a classe 2 importa, e o script toma o `:2:`
justamente porque o derivado será regenerado de todo modo.

Uso:
    python3 scripts/unir_conflito_de_rodada.py            # resolve o que sabe, recusa o resto
    python3 scripts/unir_conflito_de_rodada.py --autoteste # prova, sem rede e sem tocar no repo

Saída: 0 se TODOS os caminhos em conflito foram resolvidos; 2 se algum foi recusado.
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

RAIZ = pathlib.Path(__file__).resolve().parent.parent

# Chave da lista que só cresce, por arquivo. Só entra aqui o que a regra do projeto declara
# append-only — nada de inferir pelo formato, porque "tem uma lista" não é "só cresce".
LOGS_QUE_SO_CRESCEM = {
    "data/log_buscas.json": "execucoes",
    "data/historico_mudancas.json": "eventos",
}

# Função de outros dados. Resolve-se com a versão de cima e regenera-se depois.
REGENERAVEIS = (
    "docs/MANIFEST_SHA256.txt",
    "docs/FILA_PISTAS.md",
    "data/pistas_revisao.json",
)

# §252 (27/09/2026): prefixos que o PRÓPRIO projeto já declara derivados, em
# `.claude/hooks/bloquear_derivados.py`: `dados-abertos/.+`, `feeds/.+\.xml`, `selos/.+\.svg`.
# Medido na rodada de 27/09 às 08h29: o resolvedor recusou
# `dados-abertos/verificacao_municipal.csv` por "política de mesclagem não decidida" — mas a
# política DELE está decidida desde sempre: é derivado, logo resolve com a versão de cima e a
# cadeia canônica regenera. Recusar derivado era conservadorismo sem razão, e custou a rodada.
# Fica como PREFIXO, não nome exato, porque o conjunto cresce com o dado (um CSV novo em
# dados-abertos/ nasce derivado, e não deve precisar de PR para ser resolvido).
PREFIXOS_REGENERAVEIS = ("dados-abertos/", "feeds/", "selos/")


def e_regeneravel(caminho: str) -> bool:
    """O caminho é função de outros dados, e portanto resolve com a versão de cima?"""
    return caminho in REGENERAVEIS or caminho.startswith(PREFIXOS_REGENERAVEIS)


class Recusa(Exception):
    """O script não sabe resolver este caminho, e adivinhar apagaria dado."""


def git(*args, repo=None, binario=False):
    """Roda o git no repositório e devolve a saída; levanta se o git reprovar."""
    r = subprocess.run(["git", *args], cwd=str(repo or RAIZ), capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.decode('utf-8', 'replace').strip()}")
    return r.stdout if binario else r.stdout.decode("utf-8")


def em_conflito(repo=None):
    """Os caminhos que o git deixou sem resolver."""
    saida = git("diff", "--name-only", "--diff-filter=U", repo=repo)
    return [l.strip() for l in saida.splitlines() if l.strip()]


def estagio(caminho, n, repo=None):
    """O conteúdo do estágio n (1=base, 2=nosso, 3=deles), ou None se o estágio não existe."""
    try:
        return git("show", f":{n}:{caminho}", repo=repo, binario=True).decode("utf-8")
    except RuntimeError:
        return None


def unir_log(caminho, chave, base_txt, nosso_txt, deles_txt):
    """Une pela base comum: base + nossos_novos + deles_novos. Recusa se não for append-only."""
    if nosso_txt is None or deles_txt is None:
        raise Recusa("um dos lados não tem o arquivo; isto não é acréscimo dos dois lados")

    nosso, deles = json.loads(nosso_txt), json.loads(deles_txt)
    base = json.loads(base_txt) if base_txt is not None else {chave: []}
    for nome, d in (("nosso", nosso), ("deles", deles), ("base", base)):
        if not isinstance(d, dict) or not isinstance(d.get(chave), list):
            raise Recusa(f"o lado {nome} não tem a lista '{chave}' no formato esperado")

    lb, ln, ld = base[chave], nosso[chave], deles[chave]
    n = len(lb)

    # A trava que importa: os dois lados PRECISAM começar com a base, item a item. Se não
    # começarem, alguém reescreveu ou removeu histórico, e unir aqui esconderia isso.
    for nome, lado in (("nosso", ln), ("deles", ld)):
        if len(lado) < n:
            raise Recusa(f"o lado {nome} tem {len(lado)} itens, menos que a base ({n}) — "
                         f"houve remoção, e isto não é acréscimo")
        if lado[:n] != lb:
            raise Recusa(f"o lado {nome} não começa com a base item a item — o arquivo não se "
                         f"comportou como append-only nesta ocasião")

    uniao = lb + ln[n:] + ld[n:]

    # A trava de 23/09: o total NUNCA pode ser menor que qualquer um dos lados.
    if len(uniao) < max(len(ln), len(ld)):
        raise Recusa(f"a união deu {len(uniao)}, menor que um dos lados "
                     f"({len(ln)} e {len(ld)}) — recusado")

    # Os escalares do topo: vêm do lado de quem reaplica (deles), que é a rodada. Se algum
    # divergir, é mudança de formato no meio de um conflito — para isso o script não serve.
    escalares_n = {k: v for k, v in nosso.items() if k != chave}
    escalares_d = {k: v for k, v in deles.items() if k != chave}
    if escalares_n != escalares_d:
        raise Recusa(f"os campos fora de '{chave}' divergem entre os lados "
                     f"({sorted(escalares_n)} vs {sorted(escalares_d)}) — mudança de formato")

    fundido = dict(deles)
    fundido[chave] = uniao
    return fundido, len(ln), len(ld), len(uniao)


def resolver(repo=None, escrever=True):
    """Resolve o que sabe. Devolve (resolvidos, regenerar, recusados)."""
    raiz = pathlib.Path(repo or RAIZ)
    resolvidos, regenerar, recusados = [], [], []

    for caminho in em_conflito(repo=repo):
        norm = caminho.replace("\\", "/")
        try:
            if norm in LOGS_QUE_SO_CRESCEM:
                chave = LOGS_QUE_SO_CRESCEM[norm]
                fundido, a, b, t = unir_log(
                    norm, chave,
                    estagio(norm, 1, repo=repo), estagio(norm, 2, repo=repo),
                    estagio(norm, 3, repo=repo))
                if escrever:
                    # Compacto e sem espaço, como o produtor grava — o formato do arquivo não
                    # é assunto deste script, e reescrevê-lo mudaria 20 MB de diff.
                    (raiz / norm).write_text(
                        json.dumps(fundido, ensure_ascii=False, separators=(",", ":")),
                        encoding="utf-8", newline="")
                    git("add", "--", norm, repo=repo)
                resolvidos.append(f"{norm}: {a} + {b} → {t} (união pela base comum)")

            elif e_regeneravel(norm):
                de_cima = estagio(norm, 2, repo=repo)
                if de_cima is None:
                    raise Recusa("o lado de cima não tem o arquivo")
                if escrever:
                    (raiz / norm).write_text(de_cima, encoding="utf-8", newline="\n")
                    git("add", "--", norm, repo=repo)
                resolvidos.append(f"{norm}: versão de cima (derivado, será regenerado)")
                regenerar.append(norm)

            else:
                raise Recusa("caminho sem resolução conhecida; a política de mesclagem dele "
                             "não está decidida")
        except Recusa as e:
            recusados.append(f"{norm}: {e}")
        except (json.JSONDecodeError, RuntimeError) as e:
            recusados.append(f"{norm}: {type(e).__name__}: {e}")

    return resolvidos, regenerar, recusados


# ─────────────────────────── autoteste, sem rede e fora do repositório ───────────────────────

def _repo_com_conflito(tmp, caminho, base, nosso, deles):
    """Monta um repositório de verdade e provoca um conflito de verdade no caminho pedido."""
    r = pathlib.Path(tmp)
    amb = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}

    def g(*a, ok_falhar=False):
        p = subprocess.run(["git", *a], cwd=str(r), capture_output=True, env=amb)
        if p.returncode != 0 and not ok_falhar:
            raise RuntimeError(f"git {' '.join(a)}: {p.stderr.decode('utf-8','replace')}")
        return p.returncode

    def escrever(texto):
        alvo = r / caminho
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(texto, encoding="utf-8", newline="")

    g("init", "-q", "-b", "principal")
    if base is not None:
        escrever(base)
        g("add", "-A"); g("commit", "-qm", "base")
    else:
        (r / "semente.txt").write_text("x", encoding="utf-8", newline="\n")
        g("add", "-A"); g("commit", "-qm", "base")

    g("checkout", "-qb", "lado")
    escrever(deles)
    g("add", "-A"); g("commit", "-qm", "deles")

    g("checkout", "-q", "principal")
    escrever(nosso)
    g("add", "-A"); g("commit", "-qm", "nosso")

    # merge (não rebase) porque os estágios 1/2/3 são os mesmos e o teste fica legível
    g("merge", "lado", "-m", "colisao", ok_falhar=True)
    return r


def _log(chave, itens, **escalares):
    d = dict(escalares)
    d[chave] = itens
    return json.dumps(d, ensure_ascii=False, separators=(",", ":"))


def autoteste() -> int:
    falhas = []

    def checar(nome, cond):
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    E = {"formato_versao": 2, "formato": "v2"}
    P = "data/log_buscas.json"

    # 1. o caso que acontece toda rodada: os dois lados acrescentaram
    with tempfile.TemporaryDirectory() as t:
        r = _repo_com_conflito(
            t, P,
            _log("execucoes", [{"i": 1}, {"i": 2}], **E),
            _log("execucoes", [{"i": 1}, {"i": 2}, {"i": 3}], **E),          # nosso: +1
            _log("execucoes", [{"i": 1}, {"i": 2}, {"i": 4}, {"i": 5}], **E))  # deles: +2
        res, reg, rec = resolver(repo=r)
        checar("conflito de acréscimo mútuo é resolvido", not rec and len(res) == 1)
        d = json.loads((r / P).read_text(encoding="utf-8"))
        checar("a união é base + nossos_novos + deles_novos, na ordem",
               [x["i"] for x in d["execucoes"]] == [1, 2, 3, 4, 5])
        checar("o total é maior ou igual a cada lado", len(d["execucoes"]) >= 4)
        checar("os escalares do topo sobrevivem",
               d.get("formato_versao") == 2 and d.get("formato") == "v2")
        checar("o caminho resolvido foi adicionado ao índice",
               not em_conflito(repo=r))

    # 2. NEGATIVO: um lado ENCURTOU a lista — é o estrago de 23/09, tem de recusar
    with tempfile.TemporaryDirectory() as t:
        r = _repo_com_conflito(
            t, P,
            _log("execucoes", [{"i": 1}, {"i": 2}, {"i": 3}], **E),
            _log("execucoes", [{"i": 1}], **E),                       # nosso: PERDEU dois
            _log("execucoes", [{"i": 1}, {"i": 2}, {"i": 3}, {"i": 9}], **E))
        res, reg, rec = resolver(repo=r)
        checar("lado que encurtou a lista é RECUSADO, não unido",
               not res and len(rec) == 1 and "menos que a base" in rec[0])

    # 3. NEGATIVO: um lado reescreveu item da base — não é append-only, tem de recusar
    with tempfile.TemporaryDirectory() as t:
        r = _repo_com_conflito(
            t, P,
            _log("execucoes", [{"i": 1}, {"i": 2}], **E),
            _log("execucoes", [{"i": 1}, {"i": 99}, {"i": 3}], **E),   # reescreveu o 2
            _log("execucoes", [{"i": 1}, {"i": 2}, {"i": 4}], **E))
        res, reg, rec = resolver(repo=r)
        checar("lado que reescreveu item da base é RECUSADO",
               not res and len(rec) == 1 and "append-only" in rec[0])

    # 4. NEGATIVO: caminho sem política decidida NÃO é adivinhado
    with tempfile.TemporaryDirectory() as t:
        r = _repo_com_conflito(t, "data/pistas_imprensa.json",
                               '{"pistas":[{"a":1}]}', '{"pistas":[{"a":2}]}',
                               '{"pistas":[{"a":3}]}')
        res, reg, rec = resolver(repo=r)
        checar("caminho sem resolução conhecida é RECUSADO",
               not res and len(rec) == 1 and "não está decidida" in rec[0])

    # 5. NEGATIVO: mudança de formato no meio do conflito não passa
    with tempfile.TemporaryDirectory() as t:
        r = _repo_com_conflito(
            t, P,
            _log("execucoes", [{"i": 1}], formato_versao=2, formato="v2"),
            _log("execucoes", [{"i": 1}, {"i": 2}], formato_versao=2, formato="v2"),
            _log("execucoes", [{"i": 1}, {"i": 3}], formato_versao=3, formato="v3"))
        res, reg, rec = resolver(repo=r)
        checar("divergência nos campos fora da lista é RECUSADA",
               not res and len(rec) == 1 and "mudança de formato" in rec[0])

    # 6. derivado resolve com a versão de cima e é NOMEADO para regeneração
    with tempfile.TemporaryDirectory() as t:
        r = _repo_com_conflito(t, "docs/MANIFEST_SHA256.txt",
                               "a\nb\n", "a\nDE_CIMA\n", "a\nDA_RODADA\n")
        res, reg, rec = resolver(repo=r)
        checar("derivado é resolvido com a versão de cima",
               not rec and (r / "docs/MANIFEST_SHA256.txt").read_text(encoding="utf-8")
               == "a\nDE_CIMA\n")
        checar("derivado é nomeado para regeneração",
               reg == ["docs/MANIFEST_SHA256.txt"])

    # 7. a base pode não existir (arquivo criado dos dois lados) e ainda assim unir
    with tempfile.TemporaryDirectory() as t:
        r = _repo_com_conflito(
            t, P, None,
            _log("execucoes", [{"i": 1}], **E),
            _log("execucoes", [{"i": 2}], **E))
        res, reg, rec = resolver(repo=r)
        d = json.loads((r / P).read_text(encoding="utf-8")) if not rec else {}
        checar("sem base comum, a união é nosso + deles",
               not rec and [x["i"] for x in d["execucoes"]] == [1, 2])

    # 9. §252: derivado sob prefixo declarado resolve, em vez de ser recusado. O caso real da
    #    rodada de 27/09 às 08h29, que recusou dados-abertos/verificacao_municipal.csv.
    with tempfile.TemporaryDirectory() as t:
        r = _repo_com_conflito(t, "dados-abertos/verificacao_municipal.csv",
                               "a\nb\n", "a\nDE_CIMA\n", "a\nDA_RODADA\n")
        res, reg, rec = resolver(repo=r)
        checar("derivado sob dados-abertos/ é RESOLVIDO, não recusado",
               not rec and reg == ["dados-abertos/verificacao_municipal.csv"])
        checar("e resolve com a versão de cima",
               (r / "dados-abertos/verificacao_municipal.csv").read_text(encoding="utf-8")
               == "a\nDE_CIMA\n")

    # 10. NEGATIVO: caminho que NÃO é derivado nem log declarado segue recusado. O prefixo novo
    #     não pode ter virado uma porta larga.
    with tempfile.TemporaryDirectory() as t:
        r = _repo_com_conflito(t, "data/fontes_consultadas.json",
                               '{"municipios":{}}', '{"municipios":{"1":1}}',
                               '{"municipios":{"2":2}}')
        res, reg, rec = resolver(repo=r)
        checar("data/fontes_consultadas.json segue RECUSADO (política não decidida)",
               not res and len(rec) == 1 and "não está decidida" in rec[0])

    # 8. O CASO DE 23/09, e o único que separa união-pela-base de dedução-por-conteúdo.
    #    Execuções IDÊNTICAS no log v2 são tentativas reais distintas e CONTAM. Uma dedução
    #    por conteúdo colapsaria as duas em uma e apagaria uma tentativa sem aviso — foi assim
    #    que quase 3.000 execuções sumiram. Sem esta asserção o autoteste passa com o defeito
    #    dentro: descoberto ao restaurar o defeito de propósito, em 27/09/2026.
    #    Os dois lados precisam DIFERIR em algo, senão o git mescla limpo e não há conflito
    #    para resolver — por isso cada um traz também uma execução só sua.
    with tempfile.TemporaryDirectory() as t:
        igual = {"municipio": "Recife", "consulta": "plano de contingência", "achou": 0}
        r = _repo_com_conflito(
            t, P,
            _log("execucoes", [], **E),
            _log("execucoes", [dict(igual), {"i": "nosso"}], **E),
            _log("execucoes", [dict(igual), {"i": "deles"}], **E))
        res, reg, rec = resolver(repo=r)
        d = json.loads((r / P).read_text(encoding="utf-8")) if not rec else {"execucoes": []}
        iguais = sum(1 for x in d["execucoes"] if x.get("municipio") == "Recife")
        checar("duas execuções idênticas são DUAS tentativas, não uma "
               "(nunca deduzir por conteúdo)", len(d["execucoes"]) == 4 and iguais == 2)

    if falhas:
        print(f"\n✗ UNIÃO DE CONFLITO: {len(falhas)} falha(s).")
        return 1
    print("\n✓ UNIÃO DE CONFLITO OK — une o que sabe pela base comum, recusa o resto.")
    return 0


def main() -> int:
    if "--autoteste" in sys.argv[1:]:
        return autoteste()

    resolvidos, regenerar, recusados = resolver()
    if not resolvidos and not recusados:
        print("Nada em conflito.")
        return 0
    for r in resolvidos:
        print(f"  resolvido  {r}")
    for r in recusados:
        print(f"  RECUSADO   {r}")
    if regenerar:
        print("REGENERAR=" + " ".join(regenerar))
    if recusados:
        print(f"::error::{len(recusados)} caminho(s) sem resolução conhecida; a rodada não "
              f"comita. Adivinhar a mesclagem apagaria dado sem aviso.")
        return 2
    print(f"{len(resolvidos)} caminho(s) resolvido(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
