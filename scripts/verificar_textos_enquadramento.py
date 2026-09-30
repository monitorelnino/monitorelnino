#!/usr/bin/env python3
"""Portão: o bloco de enquadramento federal diz só as quatro frases aprovadas, e nada de dever.

PR 4 do handover do enquadramento federal de risco (editoria, 30/09/2026).

O QUE ELE EXISTE PARA BARRAR
----------------------------
Os quatro textos do bloco foram aprovados pela editoria em 30/09/2026 como **literais, sem
variação**. O risco não é alguém reescrevê-los de propósito: é a reescrita gentil — "deve elaborar
plano", "recomenda-se", "está obrigado a" — entrando num bloco que fala de listas federais. Duas
das três listas não criam dever nenhum para o município, e a que cria (o Cadastro Nacional do
art. 3º-A da Lei 12.340) não é nenhuma delas. Uma palavra de dever aqui viraria afirmação jurídica
falsa sobre 3.157 municípios.

Este portão confere as duas coisas: que as quatro frases estão lá, exatas, e que nenhuma palavra de
dever, obrigação ou recomendação aparece no bloco.

USO
    python3 scripts/verificar_textos_enquadramento.py
    python3 scripts/verificar_textos_enquadramento.py --autoteste
"""
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
ARQUIVO = RAIZ / "assets" / "js" / "index.js"

APROVADOS = {
    "chuva": ("Consta do cadastro federal de municípios suscetíveis a enxurradas e inundações "
              "(Casa Civil, 2025)."),
    "seca": ("Integra a delimitação oficial do Semiárido brasileiro, região sujeita a estiagens "
             "prolongadas (Sudene, 2024)."),
    "fogo": ("Consta da lista federal de municípios prioritários para controle do desmatamento e "
             "dos incêndios florestais na Amazônia (MMA, 2024)."),
    "nenhuma": ("Não consta de nenhuma das listas federais de risco por município: enxurradas e "
                "inundações (Casa Civil), Semiárido (Sudene) e prioritários para desmatamento e "
                "incêndios (MMA)."),
}
COMPLEMENTOS = ("inundação", "enxurrada", "inundação e enxurrada")

# Palavras de dever, obrigação e recomendação. `obrigat` cobre obrigatório e obrigatoriedade;
# `dever` cobre deveres. "deve" e "devem" entram como palavra inteira, para não pegar "devendo" de
# comentário nem "desenvolve".
RE_DEVER = re.compile(
    r"\b(deve|devem|deverá|deverão|dever|deveres|obrigad[oa]s?|obrigatóri[oa]s?|"
    r"obrigatoriedade|obriga|obrigação|obrigações|recomenda|recomenda-se|recomendável|"
    r"recomendação|recomendações|precisa|deveria|tem de|há de)\b",
    re.IGNORECASE)


def bloco_do_enquadramento(fonte: str) -> str:
    """O trecho do arquivo entre `const ENQ_TEXTO` e o fim de `enquadramentoBox`. Função pura.

    Confere o bloco, não o arquivo: o resto de `index.js` fala de outras coisas, e uma delas pode
    legitimamente usar a palavra "deve". Sem o bloco, devolve vazio — e a checagem reprova, porque
    bloco que não se acha é bloco que não se confere."""
    t = fonte or ""
    i = t.find("const ENQ_TEXTO")
    if i < 0:
        return ""
    j = t.find("\nfunction ", t.find("function enquadramentoBox", i) + 1)
    return t[i:j if j > i else len(t)]


def problemas(fonte: str) -> list:
    """As falhas do bloco. Função pura."""
    ruins = []
    bloco = bloco_do_enquadramento(fonte)
    if not bloco:
        return ["bloco do enquadramento não encontrado em assets/js/index.js — sem bloco não há "
                "o que conferir"]
    for familia, frase in APROVADOS.items():
        if frase not in bloco:
            ruins.append(f"texto de {familia} ausente ou alterado — ele é literal e aprovado: "
                         f"{frase[:60]}…")
    for c in COMPLEMENTOS:
        if f"'{c}'" not in bloco:
            ruins.append(f"complemento de risco '{c}' ausente do vocabulário fechado")
    for m in RE_DEVER.finditer(bloco):
        linha = bloco[:m.start()].count("\n") + 1
        ruins.append(f"palavra de dever/obrigação/recomendação no bloco, linha {linha} do trecho: "
                     f"'{m.group(0)}' — nenhuma destas listas cria dever de plano para o município")
    return ruins


def autoteste() -> int:
    bom = ("const ENQ_TEXTO = {\n"
           + "".join(f"  x: '{f}',\n" for f in APROVADOS.values())
           + "};\nconst ENQ_RISCO = {i: 'inundação', e: 'enxurrada', ie: 'inundação e enxurrada'};\n"
             "function enquadramentoBox(uf, nome){ return ''; }\n"
             "function outra(){ /* aqui o texto deve poder dizer deve */ }\n")
    casos = [
        ("bloco correto passa", problemas(bom) == []),
        ("arquivo sem o bloco reprova", any("não encontrado" in p for p in problemas("var x = 1;"))),
        ("texto alterado reprova",
         any("texto de seca" in p for p in problemas(bom.replace("estiagens", "secas")))),
        ("texto ausente reprova",
         any("texto de fogo" in p for p in problemas(bom.replace(APROVADOS["fogo"], "")))),
        ("complemento removido reprova",
         any("'enxurrada' ausente" in p
             for p in problemas(bom.replace("e: 'enxurrada'", "e: 'x'")))),
        ("'deve' dentro do bloco reprova",
         any("palavra de dever" in p
             for p in problemas(bom.replace("return '';", "// o município deve elaborar plano")))),
        ("'recomenda-se' reprova",
         any("recomenda" in p
             for p in problemas(bom.replace("return '';", "// recomenda-se o plano")))),
        ("'obrigatório' reprova",
         any("obrigatóri" in p
             for p in problemas(bom.replace("return '';", "// plano obrigatório")))),
        ("'deve' FORA do bloco não reprova", problemas(bom) == []),
        ("'desenvolve' não é 'deve'",
         problemas(bom.replace("return '';", "// desenvolve a lista")) == []),
        ("a falha diz a linha do trecho",
         any("linha" in p for p in problemas(bom.replace("return '';", "// deve")))),
        ("fonte vazia reprova", len(problemas("")) == 1),
        ("fonte nula não quebra", len(problemas(None)) == 1),
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
    ruins = problemas(ARQUIVO.read_text(encoding="utf-8"))
    if ruins:
        print("✗ TEXTOS DO ENQUADRAMENTO:")
        for r in ruins:
            print("   -", r)
        return 1
    print("✓ ENQUADRAMENTO OK — as quatro frases aprovadas estão literais, o vocabulário de risco "
          "é fechado e não há palavra de dever, obrigação ou recomendação no bloco.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
