#!/usr/bin/env python3
"""Portão: o carimbo da rodada é escrito ANTES da bateria de portões, nunca depois.

O DEFEITO QUE ELE EXISTE PARA BARRAR
------------------------------------
Em 01/10/2026 a publicação de dados parou duas vezes (runs 36920129893 e 36929825343) e o site
ficou sem dado novo por um dia. A causa não era o dado: os coletores gravam `atualizado_em = hoje`
ao longo da rodada, e o `atualizar.py` só escrevia o `corte` **depois** de rodar os 149 portões. No
meio do caminho, `data/meta.json` ficava com `atualizado_em` de hoje e `corte` de ontem — que é
exatamente o que o `verificar_corte_sincronizado.py` existe para barrar. O portão estava certo em
parar; a ORDEM estava errada.

Corrigir a ordem conserta aquela noite. Este portão impede que ela volte: numa edição futura,
mover o carimbo para depois dos portões voltaria a parar a publicação, e o sintoma apareceria
como "portão vermelho", longe da causa.

A REGRA
-------
No `atualizar.py`, a escrita de `meta["corte"]` aparece antes da primeira chamada de verificação.

USO
    python3 scripts/verificar_ordem_do_carimbo.py
    python3 scripts/verificar_ordem_do_carimbo.py --autoteste
"""
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
ATUALIZAR = RAIZ / "atualizar.py"

# A escrita do carimbo, e o começo da bateria. Os dois padrões são do fonte real.
#
# A bateria começa em `verificar_consistencia.py` ou em qualquer coisa sob `scripts/`. O recorte
# não é cosmético: `verificar_vigencia.py` é COLETOR (confere a vigência dos atos na fonte) e roda
# junto dos outros coletores, antes do carimbo — casar com ele reprovaria a ordem correta, e foi o
# que a primeira versão deste portão fez.
RE_CARIMBO = re.compile(r'meta\["corte"\]\s*=\s*hoje')
RE_PORTAO = re.compile(r'rodar\(\[(?:sys\.executable|"node"|"bash"),\s*"'
                       r'(?:scripts/verificar_|verificar_consistencia\.py)')


def problemas(fonte: str) -> list:
    """As falhas de ordem. Função pura.

    Devolve lista vazia quando o carimbo vem antes da primeira verificação. Carimbo ausente é
    falha por si: sem ele o corte congela, que foi o defeito de 30/09."""
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
    antes = ('meta["corte"] = hoje\n'
             'rodar([sys.executable, "verificar_consistencia.py"], obrigatorio=True)\n')
    depois = ('rodar([sys.executable, "verificar_consistencia.py"], obrigatorio=True)\n'
              'meta["corte"] = hoje\n')
    com_node = ('meta["corte"] = hoje\n'
                'rodar(["node", "scripts/verificar_runtime.js"], obrigatorio=True)\n')
    node_antes = ('rodar(["node", "scripts/verificar_runtime.js"], obrigatorio=True)\n'
                  'meta["corte"] = hoje\n')
    casos = [
        ("carimbo antes da verificação passa", problemas(antes) == []),
        ("carimbo depois da verificação reprova", len(problemas(depois)) == 1),
        ("a falha diz o que acontece na publicação",
         "corte sincronizado" in problemas(depois)[0]),
        ("portão de node também conta como verificação", problemas(com_node) == []),
        # `verificar_vigencia.py` é coletor, roda antes do carimbo, e não pode reprovar a ordem.
        ("coletor com nome de verificação não conta como portão",
         problemas('rodar([sys.executable, "verificar_vigencia.py"])\n'
                   'meta["corte"] = hoje\n'
                   'rodar([sys.executable, "verificar_consistencia.py"])\n') == []),
        ("portão de node depois do carimbo reprova", len(problemas(node_antes)) == 1),
        ("carimbo ausente reprova",
         any("não aparece" in x for x in problemas('rodar([sys.executable, "verificar_x.py"])'))),
        ("bateria ausente reprova",
         any("saiu da rodada" in x for x in problemas('meta["corte"] = hoje'))),
        ("fonte vazia não quebra", len(problemas("")) == 1),
        ("fonte nula não quebra", len(problemas(None)) == 1),
        # O fonte REAL do projeto, que é o que o portão cobra todo dia.
        ("o atualizar.py em vigor passa",
         problemas(ATUALIZAR.read_text(encoding="utf-8")) == []),
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
    ruins = problemas(ATUALIZAR.read_text(encoding="utf-8"))
    if ruins:
        print("✗ ORDEM DO CARIMBO:")
        for r in ruins:
            print("   -", r)
        return 1
    print("✓ ORDEM DO CARIMBO OK — `corte` da rodada é escrito antes da bateria de portões.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
