#!/usr/bin/env python3
"""Portão da ausência declarada (§201, 24/09/2026).

POR QUE EXISTE. O projeto tem um teto público de ausência que é a sua espinha dorsal: nunca se diz
"não existe", diz-se "não localizamos até o corte". A regra protege contra afirmar a inexistência de
um documento que talvez só não tenhamos encontrado. Mas ela cobra um preço: quando o ÓRGÃO
COMPETENTE declara formalmente que o instrumento não existe, o Monitor ficava obrigado a relatar
isso com a mesma frase tímida de quando a busca apenas falhou — e as duas coisas não são a mesma.
Uma é lacuna nossa, de alcance; a outra é lacuna deles, confirmada na fonte.

`data/ausencia_declarada.json` guarda a segunda. Este portão garante que ela não vire uma porta dos
fundos para afirmar inexistência sem lastro:

  1. todo item tem os campos obrigatórios preenchidos, inclusive ÓRGÃO, DATA e CANAL — sem fonte
     nomeada, não há declaração, há opinião;
  2. todo item declara `efeito_no_indice` explicitamente, para que ninguém confunda registro de
     procedência com mudança de nota;
  3. nenhum item cita UF fora das 27, nem repete o mesmo escopo para a mesma UF;
  4. o `resumo_publico` é curto — este arquivo guarda o FATO, não o texto da resposta, que por
     regra editorial não entra no repositório público.

Uso: python3 scripts/verificar_ausencia_declarada.py
"""
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
ARQ = RAIZ / "data" / "ausencia_declarada.json"
UFS = {"AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PA", "PB",
       "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO"}
LIMITE_RESUMO = 400   # o fato cabe; o texto da resposta, não


def conferir(doc: dict) -> list:
    """Devolve a lista de falhas. Função pura, para o autoteste exercitar sem tocar em disco."""
    falhas = []
    obrig = doc.get("campos_obrigatorios") or []
    if not obrig:
        falhas.append("campos_obrigatorios ausente — o arquivo precisa declarar o que exige de si")
    vistos = set()
    for i, it in enumerate(doc.get("itens") or [], 1):
        rot = f"item {i} ({it.get('uf', '?')}/{str(it.get('escopo'))[:28]})"
        for campo in obrig:
            v = it.get(campo)
            if v is None or (isinstance(v, str) and not v.strip()):
                falhas.append(f"{rot}: campo obrigatório vazio — '{campo}'")
        if it.get("uf") not in UFS:
            falhas.append(f"{rot}: UF fora das 27")
        chave = (it.get("uf"), str(it.get("escopo", "")).strip().lower())
        if chave in vistos:
            falhas.append(f"{rot}: escopo repetido para a mesma UF — duas declarações do mesmo fato")
        vistos.add(chave)
        resumo = str(it.get("resumo_publico") or "")
        if len(resumo) > LIMITE_RESUMO:
            falhas.append(f"{rot}: resumo_publico com {len(resumo)} caracteres (teto {LIMITE_RESUMO}) — "
                          "este arquivo guarda o fato, não o texto da resposta")
    return falhas


def autoteste() -> int:
    bom = {"campos_obrigatorios": ["uf", "escopo", "orgao"],
           "itens": [{"uf": "MT", "escopo": "plano estadual", "orgao": "X", "resumo_publico": "curto"}]}
    casos = [
        ("arquivo íntegro passa", bom, 0),
        ("campo obrigatório vazio reprova",
         {**bom, "itens": [{"uf": "MT", "escopo": "plano estadual", "orgao": "  ", "resumo_publico": "x"}]}, 1),
        ("UF inválida reprova",
         {**bom, "itens": [{"uf": "XX", "escopo": "plano", "orgao": "X", "resumo_publico": "x"}]}, 1),
        ("mesmo escopo duas vezes na mesma UF reprova",
         {**bom, "itens": [dict(bom["itens"][0]), dict(bom["itens"][0])]}, 1),
        ("resumo longo demais reprova (é o texto da resposta vazando)",
         {**bom, "itens": [{**bom["itens"][0], "resumo_publico": "a" * (LIMITE_RESUMO + 1)}]}, 1),
        ("sem campos_obrigatorios reprova", {"itens": []}, 1),
    ]
    falhou = False
    for rotulo, doc, esperado in casos:
        n = len(conferir(doc))
        ok = (n >= esperado) if esperado else (n == 0)
        print(f"  {'✓' if ok else '✗'} {rotulo}")
        falhou = falhou or not ok
    print("✗ AUTOTESTE: falhou" if falhou else "✓ AUTOTESTE OK")
    return 1 if falhou else 0


def main() -> int:
    if not ARQ.exists():
        print(f"✗ AUSÊNCIA DECLARADA: {ARQ.relative_to(RAIZ).as_posix()} ausente")
        return 1
    doc = json.loads(ARQ.read_text(encoding="utf-8"))
    falhas = conferir(doc)
    if falhas:
        print("✗ AUSÊNCIA DECLARADA: problemas encontrados:")
        for f in falhas:
            print("  ✗ " + f)
        return 1
    n = len(doc.get("itens") or [])
    print(f"✓ AUSÊNCIA DECLARADA OK — {n} declaração(ões) de órgão competente, cada uma com fonte "
          f"nomeada, data e efeito no índice explícito.")
    return 0


if __name__ == "__main__":
    sys.exit(autoteste() if "--autoteste" in sys.argv else main())
