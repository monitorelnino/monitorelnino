#!/usr/bin/env python3
"""
scripts/lembrete_de_renovacao_lai.py — o que precisa ser pedido de novo, e até quando
=====================================================================================
Item 4 do `HANDOVER_preparacao_programatica_seca_05-10-2026.md`.

O dado que chega por pedido de acesso à informação tem período fechado e demora. O da Operação
Carro-Pipa cobre janeiro a agosto de 2026 e chegou em 05/10: daqui a três meses ele estará velho, e
o pedido novo precisa sair **antes** disso, não depois. A regra que a editoria fixou é pedido novo a
cada trimestre, pelo menos 15 dias antes de o dado em uso completar 90 — `recebido_em + 75 dias`,
que é o campo `proximo_pedido_ate`.

Prazo não se lembra: ele se lê de um arquivo e aparece sozinho. Este script é a leitura.

**Ele não manda e-mail e não abre issue.** Fazer qualquer das duas exige credencial que alcance o
repositório privado, e a editoria decidiu em 05/10/2026 não dar esse acesso à chave de publicação.
O que ele faz é imprimir, e é o painel e a pessoa que leem.

A fila de pedidos vive no repositório PRIVADO da editoria. Quando ela não está ao alcance — a CI do
repositório público não a clona —, o script diz isso e sai em zero: lembrete que não pôde ser lido
não é lembrete vencido.

USO
  python3 scripts/lembrete_de_renovacao_lai.py --autoteste
  python3 scripts/lembrete_de_renovacao_lai.py
  python3 scripts/lembrete_de_renovacao_lai.py --em 2026-12-10
"""
import datetime as dt
import json
import os
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
PEDIDOS = pathlib.Path(os.environ.get(
    "MARE_LAI_PEDIDOS",
    str(RAIZ.parent / "robo-registro" / "notas" / "lai" / "lai_pedidos.json")))

# O aviso começa 15 dias antes do prazo: é o tempo que a editoria pediu para preparar e enviar.
AVISO_ANTES = 15


def dias_ate(prazo: str, hoje: dt.date) -> int | None:
    """Dias de hoje até o prazo, ou None quando o prazo não é data. Função pura."""
    try:
        return (dt.date.fromisoformat(str(prazo)) - hoje).days
    except (TypeError, ValueError):
        return None


def situacao(dias: int | None, aviso_antes: int = AVISO_ANTES) -> str:
    """"vencido" · "avisar" · "em dia" · "sem prazo". Função pura."""
    if dias is None:
        return "sem prazo"
    if dias < 0:
        return "vencido"
    if dias <= aviso_antes:
        return "avisar"
    return "em dia"


def lembretes(pedidos: dict, hoje: dt.date, aviso_antes: int = AVISO_ANTES) -> list:
    """Os pedidos com `proximo_pedido_ate`, com a situação de cada um. Função pura.

    Pedido sem `proximo_pedido_ate` não entra: ausência de prazo não é prazo em dia nem vencido, e
    inventar um prazo para quem não declarou seria o Monitor afirmando o que ninguém disse.
    """
    fora = []
    for p in (pedidos or {}).get("federais") or []:
        if not isinstance(p, dict):
            continue
        prazo = p.get("proximo_pedido_ate")
        if not prazo:
            continue
        d = dias_ate(prazo, hoje)
        fora.append({
            "id": p.get("id") or p.get("orgao") or "?",
            "orgao": p.get("orgao") or "",
            "assunto": p.get("assunto") or "",
            "proximo_pedido_ate": prazo,
            "dias": d,
            "situacao": situacao(d, aviso_antes),
            "texto_do_pedido": p.get("texto_do_pedido") or "",
            "pendencias": list(p.get("pendencias") or []),
        })
    ordem = {"vencido": 0, "avisar": 1, "sem prazo": 2, "em dia": 3}
    return sorted(fora, key=lambda x: (ordem[x["situacao"]],
                                       x["dias"] if x["dias"] is not None else 10**6))


def linha(lem: dict) -> str:
    """Uma linha legível para o painel. Função pura."""
    marca = {"vencido": "✗", "avisar": "⚠", "em dia": "·", "sem prazo": "·"}[lem["situacao"]]
    quando = (f"vencido há {-lem['dias']} dia(s)" if lem["situacao"] == "vencido"
              else f"em {lem['dias']} dia(s)" if lem["dias"] is not None else "sem prazo")
    return (f"  {marca} renovar pedido de {lem['id']} até {lem['proximo_pedido_ate']} "
            f"({quando})")


def _autoteste() -> int:
    falhas, contados = [], []

    def ok(nome, cond):
        contados.append(nome)
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    hoje = dt.date(2026, 12, 10)
    ok("prazo no futuro conta os dias", dias_ate("2026-12-19", hoje) == 9)
    ok("prazo passado conta negativo", dias_ate("2026-12-01", hoje) == -9)
    ok("o que não é data devolve None", dias_ate("em breve", hoje) is None)
    ok("prazo ausente devolve None", dias_ate(None, hoje) is None)

    ok("nove dias é avisar", situacao(9) == "avisar")
    ok("quinze dias ainda é avisar", situacao(15) == "avisar")
    ok("dezesseis dias é em dia", situacao(16) == "em dia")
    ok("negativo é vencido", situacao(-1) == "vencido")
    ok("sem prazo não é vencido nem em dia", situacao(None) == "sem prazo")

    base = {"federais": [
        {"id": "ocp_midr", "proximo_pedido_ate": "2026-12-19", "orgao": "MIDR"},
        {"id": "outro", "proximo_pedido_ate": "2027-03-01"},
        {"id": "sem_prazo", "orgao": "X"},
    ]}
    l = lembretes(base, hoje)
    ok("pedido sem prazo não entra na lista", len(l) == 2)
    ok("o mais urgente vem primeiro", l[0]["id"] == "ocp_midr")
    ok("o prazo distante fica em dia", l[1]["situacao"] == "em dia")
    ok("a linha diz o identificador e a data",
       "ocp_midr" in linha(l[0]) and "2026-12-19" in linha(l[0]))
    ok("vencido aparece como vencido",
       lembretes(base, dt.date(2027, 1, 1))[0]["situacao"] == "vencido")
    ok("arquivo vazio não produz lembrete", lembretes({}, hoje) == [])
    ok("entrada que não é dicionário é ignorada",
       lembretes({"federais": ["x"]}, hoje) == [])

    import dis
    nomes = set()
    for nome_obj, obj in list(globals().items()):
        if nome_obj in ("_autoteste", "main"):
            continue
        codigo = getattr(obj, "__code__", None)
        if codigo is not None:
            nomes |= {i.argval for i in dis.get_instructions(codigo) if isinstance(i.argval, str)}
    ok("trava estrutural: as funções puras não leem disco, não escrevem e não vão à rede",
       not ({"read_text", "write_text", "urlopen", "requests"} & nomes))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else f"✓ AUTOTESTE OK — {len(contados)} casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def main(argv: list) -> int:
    if "--autoteste" in argv:
        return _autoteste()
    hoje = dt.date.today()
    if "--em" in argv:
        hoje = dt.date.fromisoformat(argv[argv.index("--em") + 1])
    if not PEDIDOS.exists():
        print(f"· LEMBRETE LAI: {PEDIDOS} fora de alcance nesta árvore — a fila de pedidos vive no "
              f"repositório privado da editoria, e nada foi conferido.")
        return 0
    lista = lembretes(json.loads(PEDIDOS.read_text(encoding="utf-8")), hoje)
    if not lista:
        print("· LEMBRETE LAI: nenhum pedido com prazo de renovação declarado.")
        return 0
    print(f"LEMBRETE LAI — {hoje.isoformat()}")
    for lem in lista:
        print(linha(lem))
        for p in lem["pendencias"] if lem["situacao"] in ("vencido", "avisar") else []:
            print(f"      · pendência do pedido anterior: {p}")
        if lem["texto_do_pedido"] and lem["situacao"] in ("vencido", "avisar"):
            print(f"      · texto pronto: {lem['texto_do_pedido']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
