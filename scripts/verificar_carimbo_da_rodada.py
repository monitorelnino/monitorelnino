#!/usr/bin/env python3
"""Portão do carimbo da rodada: o corte é a data da rodada, e é escrito antes dos portões.

16/10/2026 (consolidação item 6): `verificar_corte_sincronizado.py` e `verificar_ordem_do_carimbo.py`
eram as duas metades da mesma regra — o que o carimbo DIZ e QUANDO ele é escrito — e viviam em dois
scripts. Aqui são duas funções puras com os mesmos casos.

O QUE ELE EXISTE PARA BARRAR
- 30/09/2026 (item 2 do handover dos textos da inicial): `meta["corte"]` só avançava quando o hash do
  arquivo de transferências mudava; o arquivo parou em 10/09 (período eleitoral) e o site passou a
  dizer "dados até 10/09" com o índice recebendo planos todo dia. Carimbo velho não quebra nada — só
  mente devagar. Regra: depois da rodada, `corte` e `atualizado_em` são a mesma data; "rodou e não achou
  nada novo" é informação, diferente de "parou de rodar".
- 01/10/2026: a publicação parou duas vezes porque o `atualizar.py` escrevia o `corte` DEPOIS dos 149
  portões — no meio da rodada `meta.json` ficava com `atualizado_em` de hoje e `corte` de ontem, e o
  portão de cima, certo, parava tudo. Regra: em `atualizar.py`, `meta["corte"] = hoje` vem antes da
  primeira chamada de verificação. `verificar_vigencia.py` é COLETOR (roda antes do carimbo) e não conta
  como verificação — a primeira versão do portão errou nisso.

USO
    python3 scripts/verificar_carimbo_da_rodada.py            # o autoteste roda antes da conferência
    python3 scripts/verificar_carimbo_da_rodada.py --autoteste
"""
import datetime
import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
META = RAIZ / "data" / "meta.json"
ATUALIZAR = RAIZ / "atualizar.py"

RE_DATA = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")
RE_CARIMBO = re.compile(r'meta\["corte"\]\s*=\s*hoje')
RE_PORTAO = re.compile(r'rodar\(\[(?:sys\.executable|"node"|"bash"),\s*"'
                       r'(?:scripts/verificar_|verificar_consistencia\.py)')


def data_de(texto: str):
    """A data do carimbo `dd/mm/aaaa`. None quando ilegível. Função pura."""
    m = RE_DATA.match(str(texto or "").strip())
    if not m:
        return None
    try:
        return datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None


def problemas(meta: dict) -> list:
    """O que o carimbo diz: `corte` == `atualizado_em`. Função pura."""
    ruins = []
    corte, atualizado = data_de((meta or {}).get("corte")), data_de((meta or {}).get("atualizado_em"))
    if corte is None:
        ruins.append(f"`corte` ilegível ou ausente: {(meta or {}).get('corte')!r}")
    if atualizado is None:
        ruins.append(f"`atualizado_em` ilegível ou ausente: {(meta or {}).get('atualizado_em')!r}")
    if corte and atualizado:
        if corte != atualizado:
            ruins.append(f"`corte` ({corte.strftime('%d/%m/%Y')}) ≠ `atualizado_em` "
                         f"({atualizado.strftime('%d/%m/%Y')}) — o corte é a data da rodada, e a "
                         f"rodada aconteceu. Diferença de {(atualizado - corte).days} dia(s).")
        if corte > atualizado:
            ruins.append("`corte` é posterior a `atualizado_em`: dado com data futura em relação "
                         "à própria rodada")
    return ruins


def problemas_de_ordem(fonte: str) -> list:
    """Quando o carimbo é escrito: antes da primeira verificação em `atualizar.py`. Função pura.
    Carimbo ausente é falha por si: sem ele o corte congela, que foi o defeito de 30/09."""
    carimbo = RE_CARIMBO.search(fonte or "")
    primeiro_portao = RE_PORTAO.search(fonte or "")
    if carimbo is None:
        return ['`meta["corte"] = hoje` não aparece em atualizar.py: sem o carimbo da rodada, '
                "o corte congela e o site passa a dizer uma data que não é a da coleta"]
    if primeiro_portao is None:
        return ["nenhuma chamada de verificação encontrada em atualizar.py: a bateria de portões "
                "saiu da rodada"]
    if carimbo.start() > primeiro_portao.start():
        return [f"o carimbo da rodada (`meta[\"corte\"] = hoje`, posição {carimbo.start()}) vem "
                f"DEPOIS da primeira verificação (posição {primeiro_portao.start()}): no meio da "
                f"rodada `meta.json` fica com `atualizado_em` de hoje e `corte` de ontem, e a "
                f"publicação para no portão do corte sincronizado"]
    return []


def autoteste() -> int:
    antes = 'meta["corte"] = hoje\nrodar([sys.executable, "verificar_consistencia.py"], obrigatorio=True)\n'
    depois = 'rodar([sys.executable, "verificar_consistencia.py"], obrigatorio=True)\nmeta["corte"] = hoje\n'
    com_node = 'meta["corte"] = hoje\nrodar(["node", "scripts/verificar_runtime.js"], obrigatorio=True)\n'
    node_antes = 'rodar(["node", "scripts/verificar_runtime.js"], obrigatorio=True)\nmeta["corte"] = hoje\n'
    casos = [
        # o que o carimbo diz
        ("iguais passam", problemas({"corte": "30/09/2026", "atualizado_em": "30/09/2026"}) == []),
        ("corte atrasado reprova", len(problemas({"corte": "10/09/2026", "atualizado_em": "30/09/2026"})) == 1),
        ("a falha diz de quantos dias é o atraso",
         "20 dia(s)" in problemas({"corte": "10/09/2026", "atualizado_em": "30/09/2026"})[0]),
        ("corte no futuro reprova duas vezes (diferente e posterior)",
         len(problemas({"corte": "30/09/2026", "atualizado_em": "10/09/2026"})) == 2),
        ("corte ausente reprova", any("corte` ilegível" in x for x in problemas({"atualizado_em": "30/09/2026"}))),
        ("atualizado ausente reprova", any("atualizado_em` ilegível" in x for x in problemas({"corte": "30/09/2026"}))),
        ("data impossível é ilegível",
         any("ilegível" in x for x in problemas({"corte": "31/02/2026", "atualizado_em": "30/09/2026"}))),
        ("formato ISO não passa por carimbo",
         any("ilegível" in x for x in problemas({"corte": "2026-09-30", "atualizado_em": "30/09/2026"}))),
        ("meta vazio reprova", len(problemas({})) == 2),
        ("meta nulo não quebra", len(problemas(None)) == 2),
        ("lê a data do carimbo", data_de("30/09/2026") == datetime.date(2026, 9, 30)),
        ("texto que não é data devolve None", data_de("ontem") is None),
        # quando o carimbo é escrito
        ("carimbo antes da verificação passa", problemas_de_ordem(antes) == []),
        ("carimbo depois da verificação reprova", len(problemas_de_ordem(depois)) == 1),
        ("a falha diz o que acontece na publicação", "corte sincronizado" in problemas_de_ordem(depois)[0]),
        ("portão de node também conta como verificação", problemas_de_ordem(com_node) == []),
        ("coletor com nome de verificação não conta como portão",
         problemas_de_ordem('rodar([sys.executable, "verificar_vigencia.py"])\nmeta["corte"] = hoje\n'
                            'rodar([sys.executable, "verificar_consistencia.py"])\n') == []),
        ("portão de node depois do carimbo reprova", len(problemas_de_ordem(node_antes)) == 1),
        ("carimbo ausente reprova",
         any("não aparece" in x for x in problemas_de_ordem('rodar([sys.executable, "verificar_x.py"])'))),
        ("bateria ausente reprova", any("saiu da rodada" in x for x in problemas_de_ordem('meta["corte"] = hoje'))),
        ("fonte vazia não quebra", len(problemas_de_ordem("")) == 1),
        ("fonte nula não quebra", len(problemas_de_ordem(None)) == 1),
        # O fonte REAL do projeto, que é o que o portão cobra todo dia.
        ("o atualizar.py em vigor passa", problemas_de_ordem(ATUALIZAR.read_text(encoding="utf-8")) == []),
    ]
    ruins = [n for n, ok in casos if not ok]
    for n, ok in casos:
        print(f"  {'OK  ' if ok else 'FALHA'} {n}")
    if ruins:
        print(f"X AUTOTESTE: {len(ruins)} caso(s) reprovado(s).")
        return 1
    print(f"OK AUTOTESTE — {len(casos)} casos, sem rede e sem escrita.")
    return 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    if autoteste() != 0:
        return 1
    meta = json.loads(META.read_text(encoding="utf-8"))
    ruins = problemas(meta) + problemas_de_ordem(ATUALIZAR.read_text(encoding="utf-8"))
    if ruins:
        print("✗ CARIMBO DA RODADA:")
        for r in ruins:
            print("   -", r)
        return 1
    print(f"✓ CARIMBO DA RODADA OK — `corte` e `atualizado_em` na mesma data ({meta.get('corte')}), e o "
          "carimbo é escrito antes da bateria de portões.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
