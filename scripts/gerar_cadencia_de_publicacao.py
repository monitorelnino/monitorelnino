#!/usr/bin/env python3
"""
scripts/gerar_cadencia_de_publicacao.py — quantas vezes por dia o site publica
===============================================================================
Item 7-C do `HANDOVER_preparacao_programatica_seca_05-10-2026.md`: a resposta "Com que frequência
o site é atualizado?" traz a cadência como **molde gerado**, "se a cadência mudar, muda sozinha".

A cadência não é um número para escrever na página: ela é o que está no gatilho do publicador.
Este gerador lê os `cron` de `.github/workflows/publicar_dados.yml` e escreve
`data/cadencia_publicacao.json`, que a página lê. Trocar um horário no workflow muda a frase
sozinho; escrever "duas vezes por dia" à mão deixaria a página afirmando o que o sistema deixou de
fazer, que é o defeito que esta rotina existe para não ter.

Conta só gatilho de RELÓGIO. `workflow_dispatch` e `workflow_run` existem e não são cadência: eles
dizem que alguém ou outro workflow pode disparar, não com que frequência o site publica.

USO
  python3 scripts/gerar_cadencia_de_publicacao.py --autoteste
  python3 scripts/gerar_cadencia_de_publicacao.py
"""
import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
WORKFLOW = RAIZ / ".github" / "workflows" / "publicar_dados.yml"
SAIDA = RAIZ / "data" / "cadencia_publicacao.json"

_RE_CRON = re.compile(r'^\s*-\s*cron:\s*["\']?([^"\'#]+)["\']?', re.M)


def disparos_por_dia(cron: str) -> int:
    """Quantas vezes por dia este cron dispara, ou 0 quando não é diário. Função pura.

    Só os casos que o projeto usa, e nenhum palpite nos outros: minuto fixo com hora fixa é um
    disparo por dia; minuto fixo com `*/N` nas horas é 24/N. Dia do mês ou dia da semana restritos
    tiram o cron da conta diária — ele não dispara todo dia, e somá-lo diria mais do que acontece.
    """
    partes = str(cron or "").split()
    if len(partes) != 5:
        return 0
    minuto, hora, dia_do_mes, mes, dia_da_semana = partes
    if dia_do_mes != "*" or mes != "*" or dia_da_semana != "*":
        return 0
    if "*" in minuto or "/" in minuto or "," in minuto or "-" in minuto:
        return 0
    if hora == "*":
        return 24
    if hora.startswith("*/") and hora[2:].isdigit() and int(hora[2:]) > 0:
        return 24 // int(hora[2:])
    if hora.isdigit():
        return 1
    if all(h.isdigit() for h in hora.split(",")):
        return len(hora.split(","))
    return 0


def crons_do_texto(texto: str) -> list:
    """Os `cron` declarados no workflow. Função pura."""
    return [c.strip() for c in _RE_CRON.findall(texto or "") if c.strip()]


def cadencia(texto: str) -> dict:
    """{publicacoes_por_dia, horarios}, do texto do workflow. Função pura."""
    crons = crons_do_texto(texto)
    return {
        "publicacoes_por_dia": sum(disparos_por_dia(c) for c in crons),
        "gatilhos_de_relogio": crons,
        "_fonte": ".github/workflows/publicar_dados.yml",
        "_nota": "Gerado por scripts/gerar_cadencia_de_publicacao.py. Só gatilho de relógio entra; "
                 "disparo manual e disparo por outro workflow não são cadência.",
    }


def _autoteste() -> int:
    falhas, contados = [], []

    def ok(nome, cond):
        contados.append(nome)
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    ok("hora fixa é um disparo por dia", disparos_por_dia("5 9 * * *") == 1)
    ok("duas horas fixas na mesma linha contam duas", disparos_por_dia("0 1,13 * * *") == 2)
    ok("de duas em duas horas dá doze", disparos_por_dia("0 */2 * * *") == 12)
    ok("toda hora dá vinte e quatro", disparos_por_dia("0 * * * *") == 24)
    ok("dia da semana restrito sai da conta diária", disparos_por_dia("0 9 * * 1") == 0)
    ok("dia do mês restrito sai da conta diária", disparos_por_dia("0 9 1 * *") == 0)
    ok("minuto com intervalo não é contado", disparos_por_dia("*/30 * * * *") == 0)
    ok("cron malformado devolve zero", disparos_por_dia("nao e cron") == 0)
    ok("vazio devolve zero", disparos_por_dia("") == 0)

    yml = ('on:\n  schedule:\n    - cron: "5 9 * * *"    # fecha a noite\n'
           '    - cron: "5 1 * * *"\n  workflow_dispatch:\n')
    ok("os dois gatilhos do publicador são lidos", len(crons_do_texto(yml)) == 2)
    ok("o comentário não entra no cron", crons_do_texto(yml)[0] == "5 9 * * *")
    ok("duas vezes por dia", cadencia(yml)["publicacoes_por_dia"] == 2)
    ok("workflow_dispatch não vira cadência", cadencia("on:\n  workflow_dispatch:\n")
       ["publicacoes_por_dia"] == 0)
    ok("a saída diz de onde veio", cadencia(yml)["_fonte"].endswith("publicar_dados.yml"))

    import dis
    nomes = set()
    for nome_obj, obj in list(globals().items()):
        if nome_obj in ("_autoteste", "main"):
            continue
        codigo = getattr(obj, "__code__", None)
        if codigo is not None:
            nomes |= {i.argval for i in dis.get_instructions(codigo) if isinstance(i.argval, str)}
    ok("trava estrutural: as funções puras não escrevem nem leem disco",
       not ({"write_text", "read_text", "urlopen"} & nomes))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else f"✓ AUTOTESTE OK — {len(contados)} casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def main(argv: list) -> int:
    if "--autoteste" in argv:
        return _autoteste()
    if not WORKFLOW.exists():
        print(f"✗ {WORKFLOW.relative_to(RAIZ)} não existe")
        return 1
    dados = cadencia(WORKFLOW.read_text(encoding="utf-8"))
    SAIDA.write_text(json.dumps(dados, ensure_ascii=False, indent=1) + "\n",
                     encoding="utf-8", newline="\n")
    print(f"cadência: {dados['publicacoes_por_dia']} publicação(ões) por dia "
          f"({len(dados['gatilhos_de_relogio'])} gatilho(s) de relógio) → "
          f"{SAIDA.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
