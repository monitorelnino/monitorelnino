#!/usr/bin/env python3
"""
scripts/verificar_temporizadores.py — todo workflow agendado está no registro
==============================================================================
Item 1 do `HANDOVER_garantia_dos_temporizadores_04-10-2026.md` (rev. 2).

O PROBLEMA, MEDIDO
------------------
O gatilho `schedule` do GitHub é de melhor esforço, e o próprio GitHub avisa que o início de cada
hora é o horário mais sobrecarregado. A abertura da noite falhou **três vezes em cinco dias**: 30/09
com 5h30 de atraso, 03/10 com 4h05, 04/10 sem disparar — aberta à mão às 02:40 UTC.

O #544 pôs minuto fora do pico, reserva e vigia. Todos os três vivem **dentro do mesmo agendador**:
se ele falha, caem juntos. O que resolve é outra coisa — **nada roda "às 22h07"; tudo roda quando
está DEVIDO**, e quem confere são vários observadores independentes. Para isso é preciso saber, de
cada temporizador, quando ele está devido e se repetir o disparo é seguro. Esse é o registro, e este
portão é o que impede o registro de envelhecer em silêncio.

O QUE ELE REPROVA
-----------------
  · workflow com `schedule:` que não esteja em `config/temporizadores.json`;
  · entrada sem `devido_quando` — sem isso o despachante não sabe se está devido, e passaria a
    disparar por horário, que é o problema que se quer resolver;
  · entrada sem `idempotencia` — sem isso o disparo repetido duplicaria coleta e commit;
  · entrada que aponte para um workflow que não existe mais;
  · cron declarado no registro que não exista no workflow (o registro mentindo sobre o horário).

USO
  python3 scripts/verificar_temporizadores.py --autoteste
  python3 scripts/verificar_temporizadores.py
"""
import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

REGISTRO = RAIZ / "config" / "temporizadores.json"
WORKFLOWS = RAIZ / ".github" / "workflows"
OBRIGATORIOS = ("id", "workflow", "finalidade", "cron_primario", "janela", "devido_quando",
                "tolerancia_atraso_min", "idempotencia", "orcamento_min", "recuperacao",
                "quem_depende", "gravidade")
GRAVIDADES = ("alta", "media", "baixa")


def crons_do_workflow(texto: str) -> list:
    """Os crons declarados no workflow. Função pura."""
    if not re.search(r"^on:", texto or "", re.M) and "on:" not in (texto or ""):
        return []
    return [m.group(1).strip() for m in re.finditer(r"-\s*cron:\s*[\"']([^\"']+)[\"']",
                                                    texto or "")]


def tem_agendamento(texto: str) -> bool:
    """O workflow tem gatilho de horário? Função pura."""
    return bool(re.search(r"^\s*schedule:\s*$", texto or "", re.M))


def problemas(registro: dict, workflows: dict) -> list:
    """Os problemas do registro contra os workflows do disco. Função pura.

    `workflows` é {nome do arquivo: texto}. Função pura para que o autoteste exercite os casos sem
    precisar de um repositório de mentira no disco.
    """
    fora = []
    entradas = (registro or {}).get("temporizadores") or []
    por_workflow = {}
    for t in entradas:
        por_workflow.setdefault(t.get("workflow"), []).append(t)

    for nome, texto in sorted((workflows or {}).items()):
        if not tem_agendamento(texto):
            continue
        if nome not in por_workflow:
            fora.append(f"{nome} tem `schedule:` e não está em config/temporizadores.json — "
                        f"temporizador fora do registro é temporizador que ninguém recupera")

    for t in entradas:
        ident = t.get("id") or "(sem id)"
        faltam = [c for c in OBRIGATORIOS if not t.get(c)]
        if faltam:
            fora.append(f"{ident}: sem {', '.join(faltam)}")
        if t.get("gravidade") and t["gravidade"] not in GRAVIDADES:
            fora.append(f"{ident}: gravidade {t['gravidade']!r} fora de {list(GRAVIDADES)}")
        nome = t.get("workflow")
        if nome and nome not in (workflows or {}):
            fora.append(f"{ident}: aponta para {nome}, que não existe em .github/workflows/")
            continue
        if nome:
            declarados = crons_do_workflow(workflows[nome])
            for chave in ("cron_primario", "cron_reserva"):
                c = t.get(chave)
                if c and c not in declarados:
                    fora.append(f"{ident}: {chave} {c!r} não existe em {nome} — o registro está "
                                f"mentindo sobre o horário")
        janela = t.get("janela") or {}
        if not (janela.get("inicio_utc") and janela.get("fim_utc")):
            fora.append(f"{ident}: janela sem início e fim em UTC")
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

    wf_com = ("name: x\non:\n  schedule:\n    - cron: \"7 1 * * *\"\n  workflow_dispatch:\n")
    wf_sem = "name: y\non:\n  workflow_dispatch:\n"
    ok("cron é lido do workflow", crons_do_workflow(wf_com) == ["7 1 * * *"])
    ok("workflow sem schedule não tem cron", crons_do_workflow(wf_sem) == [])
    ok("schedule é reconhecido", tem_agendamento(wf_com) and not tem_agendamento(wf_sem))
    ok("a palavra 'schedule' no meio de um comentário não conta como gatilho",
       not tem_agendamento("# o schedule: do GitHub é de melhor esforço\non:\n  push:\n"))

    bom = {"id": "x", "workflow": "a.yml", "finalidade": "f", "cron_primario": "7 1 * * *",
           "janela": {"inicio_utc": "01:00", "fim_utc": "09:00"}, "devido_quando": "d",
           "tolerancia_atraso_min": 60, "idempotencia": "i", "orcamento_min": 10,
           "recuperacao": {"workflow_dispatch": True}, "quem_depende": ["z"],
           "gravidade": "alta"}
    wfs = {"a.yml": wf_com, "b.yml": wf_sem}
    ok("registro completo passa", problemas({"temporizadores": [bom]}, wfs) == [])

    ok("workflow agendado fora do registro REPROVA",
       any("fora do registro" in x for x in problemas({"temporizadores": []}, wfs)))
    ok("workflow sem schedule não precisa estar no registro",
       not any("b.yml" in x for x in problemas({"temporizadores": [bom]}, wfs)))

    for campo in ("devido_quando", "idempotencia", "orcamento_min"):
        sem = {k: v for k, v in bom.items() if k != campo}
        ok(f"entrada sem `{campo}` REPROVA",
           any(campo in x for x in problemas({"temporizadores": [sem]}, wfs)))

    ok("entrada apontando para workflow inexistente REPROVA",
       any("não existe em" in x for x in problemas(
           {"temporizadores": [dict(bom, workflow="nao_existe.yml")]}, wfs)))
    ok("cron do registro que não está no workflow REPROVA",
       any("mentindo sobre o horário" in x for x in problemas(
           {"temporizadores": [dict(bom, cron_primario="0 0 * * *")]}, wfs)))
    ok("cron de reserva também é conferido",
       any("cron_reserva" in x for x in problemas(
           {"temporizadores": [dict(bom, cron_reserva="9 9 * * *")]}, wfs)))
    ok("gravidade fora da lista REPROVA",
       any("gravidade" in x for x in problemas(
           {"temporizadores": [dict(bom, gravidade="urgentíssima")]}, wfs)))
    ok("janela sem fim REPROVA",
       any("janela sem" in x for x in problemas(
           {"temporizadores": [dict(bom, janela={"inicio_utc": "01:00"})]}, wfs)))

    # O estado real do repositório tem de passar.
    reg = json.loads(REGISTRO.read_text(encoding="utf-8")) if REGISTRO.exists() else {}
    reais = {p.name: p.read_text(encoding="utf-8", errors="replace")
             for p in WORKFLOWS.glob("*.yml")}
    p_reais = problemas(reg, reais)
    ok("o estado atual do repositório passa", p_reais == [])
    if p_reais:
        for x in p_reais[:6]:
            print("      ·", x)

    import dis
    nomes = set()
    for nome_obj, obj in list(globals().items()):
        if nome_obj in ("_autoteste", "main"):
            continue
        codigo = getattr(obj, "__code__", None)
        if codigo is not None:
            nomes |= {i.argval for i in dis.get_instructions(codigo) if isinstance(i.argval, str)}
    ok("trava estrutural: o portão não escreve",
       not ({"gravar", "write_text", "write_bytes"} & nomes))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else f"✓ AUTOTESTE OK — {len(_casos_contados)} casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def main() -> int:
    if "--autoteste" in sys.argv[1:]:
        return _autoteste()
    if not REGISTRO.exists():
        print("✗ TEMPORIZADORES: config/temporizadores.json não existe")
        return 1
    reg = json.loads(REGISTRO.read_text(encoding="utf-8"))
    wfs = {p.name: p.read_text(encoding="utf-8", errors="replace")
           for p in WORKFLOWS.glob("*.yml")}
    p = problemas(reg, wfs)
    if p:
        print(f"✗ TEMPORIZADORES: {len(p)} problema(s):")
        for x in p:
            print("  ·", x)
        return 1
    agendados = sum(1 for t in wfs.values() if tem_agendamento(t))
    print(f"✓ TEMPORIZADORES OK — {len(reg.get('temporizadores') or [])} entrada(s) para "
          f"{agendados} workflow(s) agendado(s); cada uma com quando está devido e por que o "
          f"disparo repetido é seguro.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
