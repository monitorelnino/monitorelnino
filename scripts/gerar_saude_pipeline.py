#!/usr/bin/env python3
"""
gerar_saude_pipeline.py
=======================
Painel de saúde do pipeline: `docs/SAUDE_PIPELINE.md` a partir de `data/saude_pipeline.json`.

Handover `HANDOVER_desacoplar_pipeline_e_emagrecer_repositorio_27-09-2026.md`, item 2 — "para a
editoria ver erro sem cavar log".

A queixa era "lentidão, quebras, excesso de erros", e responder exigia abrir o log do Actions de um
job monolítico com trinta scripts em sequência. Com uma linha por script (§265) e este painel, a
pergunta "o que quebrou hoje?" se responde abrindo uma tabela.

DUAS CLASSES DE SCRIPT, E A DIFERENÇA IMPORTA
---------------------------------------------
**Essencial** — `recalcular_mare.py` e os `gerar_*.py`: se um deles erra, o site publica um estado
que não corresponde ao dado. **Reprova.**

**Coletor** — todo o resto: fonte fora do ar é rotina, e uma falha isolada não é defeito do
pipeline. Erro em **duas rodadas seguidas** vira **alerta** — aí não é a fonte, é o coletor.

O painel mede; não pontua. Nenhum arquivo daqui é lido pelo cálculo do índice.

USO
  python3 scripts/gerar_saude_pipeline.py            # gera o painel
  python3 scripts/gerar_saude_pipeline.py --check    # portão: reprova essencial com erro
  python3 scripts/gerar_saude_pipeline.py --autoteste
"""
import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

ENTRADA = RAIZ / "data" / "saude_pipeline.json"
SAIDA = RAIZ / "docs" / "SAUDE_PIPELINE.md"

# Essencial: o que, errando, publica um estado que não corresponde ao dado.
RE_ESSENCIAL = re.compile(r"^(recalcular_mare\.py|gerar_[\w-]+\.py|scripts/gerar_[\w-]+\.py)$")
ERROS_SEGUIDOS_PARA_ALERTAR = 2


def essencial(script: str) -> bool:
    return bool(RE_ESSENCIAL.match(str(script or "").strip()))


def ler(caminho: pathlib.Path = None) -> dict:
    caminho = caminho or ENTRADA
    if not caminho.exists():
        return {"execucoes": []}
    try:
        d = json.loads(caminho.read_text(encoding="utf-8"))
        d.setdefault("execucoes", [])
        return d
    except (OSError, json.JSONDecodeError):
        return {"execucoes": []}


def por_script(execucoes: list) -> dict:
    """Agrupa por script preservando a ordem cronológica dentro de cada um."""
    grupos = {}
    for e in execucoes:
        grupos.setdefault(str(e.get("script")), []).append(e)
    return grupos


def erros_seguidos(linhas: list) -> int:
    """Quantas execuções MAIS RECENTES terminaram em erro, em sequência."""
    n = 0
    for e in reversed(linhas):
        if str(e.get("status")) == "erro":
            n += 1
        else:
            break
    return n


def conferir(doc: dict) -> tuple:
    """(falhas, alertas). Função pura — o autoteste a exercita sem tocar em disco."""
    falhas, alertas = [], []
    grupos = por_script(doc.get("execucoes") or [])
    for script, linhas in sorted(grupos.items()):
        ultima = linhas[-1]
        if essencial(script) and str(ultima.get("status")) == "erro":
            falhas.append(f"{script}: essencial com erro na última execução "
                          f"({ultima.get('data')}) — {ultima.get('erro') or 'sem resumo'}")
            continue
        seguidos = erros_seguidos(linhas)
        if not essencial(script) and seguidos >= ERROS_SEGUIDOS_PARA_ALERTAR:
            alertas.append(f"{script}: erro em {seguidos} rodadas seguidas — "
                           f"{ultima.get('erro') or 'sem resumo'}")
    return falhas, alertas


def tabela(doc: dict) -> str:
    grupos = por_script(doc.get("execucoes") or [])
    if not grupos:
        return ("Sem linhas de saúde ainda. O arquivo é escrito pelos jobs noturnos e pelo "
                "publicador, a partir de `scripts/saude_pipeline.py --rodar`.\n")
    linhas = ["| script | papel | última execução | duração | itens | status | erro |",
              "|---|---|---|---|---:|---|---|"]
    for script, execs in sorted(grupos.items(), key=lambda kv: (not essencial(kv[0]), kv[0])):
        u = execs[-1]
        itens = "—" if u.get("itens") is None else u["itens"]
        dur = f"{u.get('duracao_s', 0):.0f} s"
        estado = {"ok": "ok", "erro": "**erro**", "pulado": "pulado"}.get(str(u.get("status")), "?")
        seguidos = erros_seguidos(execs)
        if seguidos >= ERROS_SEGUIDOS_PARA_ALERTAR:
            estado += f" ({seguidos} seguidas)"
        erro = (u.get("erro") or "").replace("|", "\\|")[:120] or "—"
        linhas.append(f"| `{script}` | {'essencial' if essencial(script) else 'coletor'} "
                      f"| {u.get('data')} {str(u.get('inicio') or '')[11:16]} | {dur} | {itens} "
                      f"| {estado} | {erro} |")
    return "\n".join(linhas) + "\n"


def documento(doc: dict) -> str:
    falhas, alertas = conferir(doc)
    execucoes = doc.get("execucoes") or []
    dias = sorted({str(e.get("data")) for e in execucoes})
    partes = [
        "# Saúde do pipeline",
        "",
        "Gerado por `scripts/gerar_saude_pipeline.py` a partir de `data/saude_pipeline.json`, que os",
        "jobs escrevem com `scripts/saude_pipeline.py --rodar`. Item 2 do handover de desacoplamento",
        "(27/09/2026). **Arquivo derivado: não se edita à mão.**",
        "",
        "Duas classes, e a diferença importa. **Essencial** (`recalcular_mare.py`, `gerar_*.py`): se",
        "erra, o site publica um estado que não corresponde ao dado — reprova o portão. **Coletor**:",
        "fonte fora do ar é rotina, e uma falha isolada não é defeito do pipeline; erro em duas",
        "rodadas seguidas vira alerta, porque aí não é a fonte, é o coletor.",
        "",
        f"Janela: {dias[0] if dias else '—'} a {dias[-1] if dias else '—'} "
        f"({len(execucoes)} execução(ões) registrada(s), 7 dias de histórico).",
        "",
    ]
    if falhas:
        partes += ["## Reprovando", ""] + [f"- {f}" for f in falhas] + [""]
    if alertas:
        partes += ["## Alertas", ""] + [f"- {a}" for a in alertas] + [""]
    if not falhas and not alertas:
        partes += ["Nenhum script essencial com erro e nenhum coletor errando duas rodadas seguidas.",
                   ""]
    partes += ["## Última execução de cada script", "", tabela(doc)]
    return "\n".join(partes)


def autoteste() -> int:
    casos = []

    def linha(script, status, data="2026-09-28", itens=1, erro="", dur=10.0):
        return {"script": script, "status": status, "data": data, "itens": itens,
                "erro": erro, "duracao_s": dur, "inicio": f"{data}T01:00:00"}

    casos.append(("recalcular_mare.py é essencial", essencial("recalcular_mare.py")))
    casos.append(("gerar_feeds.py é essencial", essencial("gerar_feeds.py")))
    casos.append(("scripts/gerar_manifesto.py é essencial", essencial("scripts/gerar_manifesto.py")))
    casos.append(("coletar_doe.py não é essencial", not essencial("coletar_doe.py")))
    casos.append(("monitorar_busca_web.py não é essencial", not essencial("monitorar_busca_web.py")))
    # nome parecido não engana: `gerar` tem de ser o começo do nome
    casos.append(("regerar_algo.py não é essencial", not essencial("regerar_algo.py")))

    f, a = conferir({"execucoes": [linha("recalcular_mare.py", "erro", erro="ValueError: x")]})
    casos.append(("essencial com erro reprova", len(f) == 1 and not a))

    f, a = conferir({"execucoes": [linha("coletar_doe.py", "erro")]})
    casos.append(("coletor com UMA falha não reprova nem alerta", not f and not a))

    f, a = conferir({"execucoes": [linha("coletar_doe.py", "erro", "2026-09-27"),
                                   linha("coletar_doe.py", "erro", "2026-09-28")]})
    casos.append(("coletor com duas falhas seguidas alerta, não reprova", not f and len(a) == 1))

    f, a = conferir({"execucoes": [linha("coletar_doe.py", "erro", "2026-09-26"),
                                   linha("coletar_doe.py", "ok", "2026-09-27"),
                                   linha("coletar_doe.py", "erro", "2026-09-28")]})
    casos.append(("falhas alternadas não alertam (a sequência zera no ok)", not f and not a))

    f, a = conferir({"execucoes": [linha("recalcular_mare.py", "erro", "2026-09-27"),
                                   linha("recalcular_mare.py", "ok", "2026-09-28")]})
    casos.append(("essencial que voltou a passar não reprova", not f))

    casos.append(("arquivo vazio não reprova", conferir({"execucoes": []}) == ([], [])))

    doc = {"execucoes": [linha("recalcular_mare.py", "ok"), linha("coletar_doe.py", "erro", erro="a|b")]}
    texto = documento(doc)
    casos.append(("o painel traz uma linha por script", texto.count("| `") == 2))
    casos.append(("o essencial vem primeiro na tabela",
                  texto.index("recalcular_mare.py") < texto.index("coletar_doe.py")))
    casos.append(("barra vertical no erro não quebra a tabela", "a\\|b" in texto))
    casos.append(("itens nulo aparece como travessão, não como zero",
                  "| — |" in documento({"execucoes": [linha("coletar_doe.py", "ok", itens=None)]})))
    casos.append(("o painel diz que é derivado", "não se edita à mão" in texto))

    ruins = [n for n, ok in casos if not ok]
    for n, ok in casos:
        print(f"  {'OK  ' if ok else 'FALHA'} {n}")
    if ruins:
        print(f"X AUTOTESTE: {len(ruins)} caso(s) reprovado(s).")
        return 1
    print(f"OK AUTOTESTE — {len(casos)} casos, sem escrita em disco.")
    return 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    doc = ler()
    falhas, alertas = conferir(doc)

    if "--check" in sys.argv:
        for a in alertas:
            print(f"  ! {a}")
        if falhas:
            print("✗ SAÚDE DO PIPELINE: script essencial com erro:")
            for f in falhas:
                print(f"   - {f}")
            return 1
        n = len(doc.get("execucoes") or [])
        print(f"✓ SAÚDE DO PIPELINE OK — {n} execução(ões) na janela; nenhum essencial com erro."
              + (f" {len(alertas)} alerta(s)." if alertas else ""))
        return 0

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    texto = documento(doc)
    tmp = SAIDA.with_suffix(".md.tmp")
    tmp.write_text(texto, encoding="utf-8", newline="\n")
    tmp.replace(SAIDA)
    print(f"✓ {SAIDA.relative_to(RAIZ)} gerado — {len(doc.get('execucoes') or [])} execução(ões), "
          f"{len(falhas)} reprovando, {len(alertas)} alerta(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
