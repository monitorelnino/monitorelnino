#!/usr/bin/env python3
"""Prova que a fila de pistas em imprensa aguenta DOIS produtores no mesmo arquivo.

Por que este teste existe (27/09/2026). `data/pistas_imprensa.json` é escrito por dois
caminhos diferentes: `monitorar_imprensa_regional.registrar()`, que grava pistas de descoberta
com `alvo`, `titulo`, `url` e `hash`; e a esteira de triagem, que grava registros de outro tipo
(rebaixamento C10 e afins) com `id`, `municipio` e `documento` — sem `hash` e sem os campos de
que `_hash` precisa.

`registrar()` montava o conjunto de vistos exigindo `hash` de TODOS e quebrava com
`KeyError: 'hash'` na primeira pista do outro produtor. Isso acontecia três vezes por rodada,
nos três passos que chamam a função. Como cada passo tem `continue-on-error: true`, a rodada
seguia e commitava: o que se perdia era a descoberta dessas três camadas, calada, porque o erro
aparecia no meio de um log de milhares de linhas.

O teste roda sem rede e sem tocar em `data/`.

Uso: python3 scripts/testar_fila_de_pistas.py
"""
import importlib.util
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))


def carregar_monitor():
    spec = importlib.util.spec_from_file_location("mir", RAIZ / "monitorar_imprensa_regional.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def main() -> int:
    m = carregar_monitor()
    falhas = []

    def checar(nome, condicao):
        print(("  ✓ " if condicao else "  ✗ ") + nome)
        if not condicao:
            falhas.append(nome)

    # Uma fila como a real: registros do outro produtor, sem hash e com outro esquema.
    alheia = [
        {"id": "x1", "municipio": "Rio Branco", "uf": "AC", "origem": "rebaixamento C10",
         "documento": "Plano de Ação", "url": "https://rio-branco.ac.gov.br/a"},
        {"id": "x2", "municipio": "Natal", "uf": "RN", "origem": "triagem",
         "documento": "Decreto", "url": "https://natal.rn.gov.br/b"},
    ]
    fila = {"pistas": [dict(p) for p in alheia]}

    nova = {"alvo": "Recife", "titulo": "Prefeitura publica plano",
            "url": "https://recife.pe.gov.br/plano", "data": "27/09/2026"}

    # 1. não quebra diante do esquema alheio
    try:
        m.registrar(fila, [dict(nova)])
        quebrou = False
    except KeyError as e:
        quebrou = True
        print("      KeyError:", e)
    checar("fila com registro de outro produtor não quebra o registrar()", not quebrou)

    # 2. a pista nova entrou
    checar("pista inédita é acrescentada", len(fila["pistas"]) == len(alheia) + 1)

    # 3. a mesma pista de novo NÃO duplica — a dedução continua valendo
    m.registrar(fila, [dict(nova)])
    checar("pista repetida não duplica (dedução preservada)", len(fila["pistas"]) == len(alheia) + 1)

    # 4. nada do outro produtor foi apagado nem reescrito
    sobreviventes = [p for p in fila["pistas"] if p.get("id") in {"x1", "x2"}]
    checar("os registros do outro produtor sobrevivem intactos",
           len(sobreviventes) == 2 and all("hash" not in p for p in sobreviventes))

    # 5. uma segunda pista inédita ainda entra
    outra = {"alvo": "Belém", "titulo": "Decreto de emergência",
             "url": "https://belem.pa.gov.br/decreto", "data": "27/09/2026"}
    m.registrar(fila, [outra])
    checar("segunda pista inédita também entra", len(fila["pistas"]) == len(alheia) + 2)

    if falhas:
        print(f"\n✗ FILA DE PISTAS: {len(falhas)} falha(s).")
        return 1
    print("\n✓ FILA DE PISTAS OK — dois produtores no mesmo arquivo, sem perda e sem quebra.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
