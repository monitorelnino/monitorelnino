#!/usr/bin/env python3
"""
scripts/ensaio_real_da_noite.py — a noite inteira, de dia, com os workflows de verdade
=======================================================================================
Item 5 do `HANDOVER_noite_confiavel_parte2_06-10-2026.md`.

POR QUE O ENSAIO SIMULADO NÃO BASTOU
-------------------------------------
`scripts/ensaio_da_noite.py` ficou verde em #556 e a noite de 05→06/10 falhou mesmo assim. Ele
prova os MECANISMOS num repositório de brinquedo: conflito de fila, disparo duplicado, elo
cancelado, pista fora do esquema. Nenhum desses exercícios passa pelo **passo de commit real de
cada elo** — e foi exatamente ali que a noite se perdeu, num `git add` de pasta inteira que levava
arquivo de outro elo junto. O teste verde era verdadeiro e insuficiente.

Este ensaio dispara os workflows REAIS, num ramo próprio, de dia.

AS QUATRO CONDIÇÕES PARA FICAR VERDE (item 5, literal)
-------------------------------------------------------
  1. zero conflito nos passos de commit;
  2. zero trabalho descartado — artefato reaplicado, se houver;
  3. publicação verde no ramo;
  4. marcador `.feito` em todos os elos que rodaram.

O QUE ELE NUNCA FAZ
--------------------
Rodar na `main`. A regra de 27/09 é que o teste roda no ramo `ensaio`, e esta é a aplicação dela:
se o ramo não for o declarado, o ensaio **recusa antes de disparar qualquer coisa**. A trava está
aqui e não na cabeça de ninguém.

USO
  python3 scripts/ensaio_real_da_noite.py --autoteste
  python3 scripts/ensaio_real_da_noite.py --ramo ensaio --disparar
  python3 scripts/ensaio_real_da_noite.py --ramo ensaio --julgar --runs 123,456
"""
import json
import os
import pathlib
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
RAMO_PERMITIDO = "ensaio"

# Os elos que o ensaio dispara, e a ordem em que a noite os roda. Dois deles saem JUNTOS, de
# propósito: é o paralelo que o item 5 exige, e é onde a corrida aparece.
ELOS = (
    {"workflow": "noturno_sinais.yml", "elo": "sinais-fisicos", "paralelo": True},
    {"workflow": "noturno_descoberta.yml", "elo": "descoberta", "paralelo": True},
    {"workflow": "noturno_triagem.yml", "elo": "triagem", "paralelo": False},
)
PUBLICADOR = "Publicar dados"


def ramo_proibido(ramo: str) -> str | None:
    """Motivo para não disparar, ou None. Função pura.

    A pergunta é só uma, e ela vale mais que todas as outras deste arquivo: **não é a `main`?**
    """
    r = str(ramo or "").strip()
    if not r:
        return "nenhum ramo informado"
    if r != RAMO_PERMITIDO:
        return (f"o ensaio real roda só no ramo `{RAMO_PERMITIDO}`, e foi pedido em `{r}`. "
                f"A regra é de 27/09/2026: o teste nunca comita na `main` de dia.")
    return None


def conflito_no_commit(log: str) -> list:
    """As marcas de conflito no passo de commit. Função pura — condição 1.

    Procura o que a noite de 05→06 imprimiu: `CONFLICT (content)`, a recusa do resolvedor e a
    desistência do push. Qualquer uma delas reprova.
    """
    marcas = (
        ("CONFLICT (content)", "conflito de conteúdo no rebase do elo"),
        ("sem resolução conhecida", "o resolvedor recusou um caminho"),
        ("commit perdido para", "o elo desistiu do push"),
    )
    return [motivo for marca, motivo in marcas if marca in str(log or "")]


def trabalho_descartado(log: str) -> list:
    """Sinais de trabalho que não voltou. Função pura — condição 2."""
    fora = []
    texto = str(log or "")
    if "ainda pendente:" in texto:
        fora.append("a reaplicação deixou caminho pendente")
    if "TRABALHO PENDENTE" in texto and "reaplicado" not in texto:
        fora.append("houve pendência e nada foi reaplicado")
    return fora


def elos_sem_feito(marcadores: list, elos_que_rodaram: list) -> list:
    """Quais elos rodaram e não deixaram `.feito`. Função pura — condição 4."""
    tem = {str(m).rsplit("/", 1)[-1].removesuffix(".feito") for m in (marcadores or [])}
    return sorted(e for e in (elos_que_rodaram or []) if e not in tem)


def veredito(logs: dict, publicacao: str, marcadores: list, elos_que_rodaram: list) -> dict:
    """O veredito das quatro condições. Função pura — é ela que o autoteste exercita."""
    conflitos, descartes = [], []
    for elo, log in (logs or {}).items():
        conflitos += [f"{elo}: {x}" for x in conflito_no_commit(log)]
        descartes += [f"{elo}: {x}" for x in trabalho_descartado(log)]
    sem_feito = elos_sem_feito(marcadores, elos_que_rodaram)
    publicou = str(publicacao or "").lower() == "success"
    return {
        "conflitos_no_commit": conflitos,
        "trabalho_descartado": descartes,
        "publicacao_verde": publicou,
        "elos_sem_marcador": sem_feito,
        "verde": not conflitos and not descartes and publicou and not sem_feito,
    }


def _gh(*args, timeout=120):
    try:
        return subprocess.run(["gh", *args], capture_output=True, text=True,
                              timeout=timeout, cwd=str(RAIZ))
    except Exception as erro:          # pragma: no cover
        class _Falha:
            returncode, stdout, stderr = 1, "", str(erro)
        return _Falha()


def _autoteste() -> int:
    falhas, contados = [], []

    def ok(nome, cond):
        contados.append(nome)
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    ok("a `main` é recusada antes de disparar", ramo_proibido("main") is not None)
    ok("ramo vazio é recusado", ramo_proibido("") is not None)
    ok("o ramo `ensaio` passa", ramo_proibido("ensaio") is None)
    ok("qualquer outro ramo é recusado", ramo_proibido("edicao/x") is not None)
    ok("a recusa diz o porquê", "27/09" in (ramo_proibido("main") or ""))

    ok("conflito de conteúdo reprova",
       conflito_no_commit("CONFLICT (content): Merge conflict in data/saude_pipeline.json") != [])
    ok("recusa do resolvedor reprova",
       conflito_no_commit("1 caminho(s) sem resolução conhecida") != [])
    ok("desistência do push reprova",
       conflito_no_commit("::error::commit perdido para main em movimento") != [])
    ok("log limpo passa", conflito_no_commit("tudo certo, empurrado na tentativa 1") == [])

    ok("pendência sem reaplicação reprova",
       trabalho_descartado("⚠ TRABALHO PENDENTE: data/noite/x.pendente") != [])
    ok("pendência reaplicada passa",
       trabalho_descartado("TRABALHO PENDENTE ... 3 arquivo(s) reaplicado(s)") == [])
    ok("caminho que ficou pendente reprova",
       trabalho_descartado("· ainda pendente: data/x.json") != [])
    ok("log sem pendência passa", trabalho_descartado("coletado e empurrado") == [])

    ok("elo sem marcador é nomeado",
       elos_sem_feito(["data/noite/2026-10-06/triagem.feito"], ["triagem", "descoberta"])
       == ["descoberta"])
    ok("todos com marcador não acusa nada",
       elos_sem_feito(["a/b/triagem.feito"], ["triagem"]) == [])

    v = veredito({"sinais": "empurrado na tentativa 1"}, "success",
                 ["data/noite/x/sinais.feito"], ["sinais"])
    ok("as quatro condições juntas dão verde", v["verde"])
    ok("publicação vermelha derruba o verde",
       not veredito({"a": "ok"}, "failure", ["x/a.feito"], ["a"])["verde"])
    ok("conflito derruba o verde",
       not veredito({"a": "CONFLICT (content)"}, "success", ["x/a.feito"], ["a"])["verde"])
    ok("marcador ausente derruba o verde",
       not veredito({"a": "ok"}, "success", [], ["a"])["verde"])
    ok("o veredito diz qual condição caiu",
       veredito({"a": "CONFLICT (content)"}, "success", ["x/a.feito"], ["a"])
       ["conflitos_no_commit"] != [])

    import dis
    nomes = set()
    for nome_obj, obj in list(globals().items()):
        if nome_obj in ("_autoteste", "main", "_gh", "_disparar", "_julgar"):
            continue
        if getattr(obj, "__module__", None) not in (__name__, None):
            continue
        codigo = getattr(obj, "__code__", None)
        if codigo is not None:
            nomes |= {i.argval for i in dis.get_instructions(codigo) if isinstance(i.argval, str)}
    ok("trava estrutural: as funções puras não disparam nada nem escrevem",
       not ({"subprocess", "write_text", "urlopen"} & nomes))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else f"✓ AUTOTESTE OK — {len(contados)} casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def _opcao(argv, nome, padrao=None):
    return argv[argv.index(nome) + 1] if nome in argv and len(argv) > argv.index(nome) + 1 else padrao


def _disparar(ramo: str, limite: str) -> int:
    """Dispara os elos reais no ramo. Escreve nada na árvore; só chama a API."""
    ids = []
    for e in ELOS:
        r = _gh("workflow", "run", e["workflow"], "--ref", ramo, "-f", f"limite={limite}")
        if r.returncode != 0:
            # Elo sem o input `limite` é disparado sem ele: o que importa é que ele rode.
            r = _gh("workflow", "run", e["workflow"], "--ref", ramo)
        print(f"  · {e['workflow']}: {'disparado' if r.returncode == 0 else 'NAO disparou'}"
              f"{'' if r.returncode == 0 else ' — ' + (r.stderr or '').strip()[:120]}")
        ids.append(e["workflow"])
    print("  · os dois primeiros saem juntos, de propósito: é o paralelo que o item 5 exige.")
    return 0


def main(argv: list) -> int:
    if "--autoteste" in argv:
        return _autoteste()
    ramo = _opcao(argv, "--ramo", os.environ.get("GITHUB_REF_NAME", ""))
    motivo = ramo_proibido(ramo)
    if motivo:
        print(f"✗ ENSAIO REAL RECUSADO: {motivo}")
        return 1
    if "--disparar" in argv:
        print(f"ENSAIO REAL no ramo `{ramo}`:")
        return _disparar(ramo, _opcao(argv, "--limite", "2"))
    if "--julgar" in argv:
        logs = json.loads(pathlib.Path(_opcao(argv, "--logs", "/dev/null")).read_text(
            encoding="utf-8")) if _opcao(argv, "--logs") else {}
        marcadores = [str(q) for q in (RAIZ / "data" / "noite").rglob("*.feito")]
        v = veredito(logs, _opcao(argv, "--publicacao", ""), marcadores,
                     [e["elo"] for e in ELOS])
        print(json.dumps(v, ensure_ascii=False, indent=1))
        return 0 if v["verde"] else 1
    print(__doc__.strip().split("USO")[-1].strip())
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
