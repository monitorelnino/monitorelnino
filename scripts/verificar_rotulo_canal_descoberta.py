#!/usr/bin/env python3
"""Portão — canal de DESCOBERTA não pode ser exibido como canal de registro.

Criado em 28/09/2026 (§281), defeito 6 do relatório da auditoria do funil.

O `canal` de um registro diz por onde o documento chegou. A maioria dos canais é de
**registro**: diário oficial, repositório estadual, site do município — o documento veio
de onde o ato é publicado. `imprensa` não: a matéria serve para **achar** o documento, e a
prova continua sendo o ato na fonte oficial (§5.2.1). Treze registros traziam "via
imprensa" ao lado de uma fonte descrita como oficial, e nada no que o leitor via dizia que
aquele canal é de descoberta.

Nenhum dos treze pontua — o rótulo era o problema inteiro, e por isso o conserto é de
texto. Este portão existe para que o texto não volte atrás: onde uma página exibe o canal
`imprensa`, a palavra "descoberta" tem de estar junto.

O que ele NÃO faz: não mexe no valor gravado. `imprensa` continua sendo a chave no dado e
no vocabulário fechado de canais (`coletores_base`), porque renomear a chave quebraria o
vocabulário e o histórico do log sem melhorar nada para quem lê.

Uso: python3 scripts/verificar_rotulo_canal_descoberta.py
     python3 scripts/verificar_rotulo_canal_descoberta.py --autoteste
"""
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
# Canais de descoberta, e a palavra que precisa acompanhar cada um quando ele é exibido.
DESCOBERTA = {"imprensa": "descoberta"}
# Onde o rótulo é montado. Arquivo que deixar de existir reprova: o portão não pode virar
# verde por olhar para o vazio.
ARQUIVOS = ["assets/js/index.js", "assets/js/proveniencia.js"]


def falhas_no_texto(nome: str, texto: str) -> list:
    """Toda atribuição de rótulo ao canal de descoberta tem de trazer a palavra exigida."""
    p = []
    for canal, palavra in DESCOBERTA.items():
        # Formas em que um rótulo é escrito no projeto: `imprensa:'...'` e `imprensa: '...'`,
        # com aspas simples ou duplas.
        for m in re.finditer(rf"""\b{canal}\s*:\s*(['"])(.*?)\1""", texto):
            rotulo = m.group(2)
            if palavra not in rotulo.lower():
                p.append(f"{nome}: o canal {canal!r} recebe o rótulo {rotulo!r}, sem a palavra "
                         f"{palavra!r} — canal de descoberta exibido como canal de registro faz o "
                         f"leitor tomar a matéria por prova do ato (§5.2.1)")
    return p


def autoteste() -> int:
    casos = []
    casos.append(("rótulo com a palavra passa",
                  falhas_no_texto("x", "imprensa:'imprensa (descoberta)'") == []))
    casos.append(("rótulo sem a palavra reprova",
                  falhas_no_texto("x", "imprensa:'imprensa'") != []))
    casos.append(("aspas duplas e espaço também são vistos",
                  falhas_no_texto("x", 'imprensa: "imprensa"') != []))
    casos.append(("maiúscula na palavra conta",
                  falhas_no_texto("x", "imprensa:'Imprensa (Descoberta)'") == []))
    casos.append(("canal de registro não é assunto deste portão",
                  falhas_no_texto("x", "site_municipal:'site oficial do município'") == []))
    casos.append(("rótulo vazio reprova",
                  falhas_no_texto("x", "imprensa:''") != []))

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

    falhas, vistos = [], 0
    for nome in ARQUIVOS:
        p = RAIZ / nome
        if not p.exists():
            falhas.append(f"{nome} não existe — este portão confere o rótulo do canal de "
                          f"descoberta ali e não pode ficar verde olhando para o vazio")
            continue
        texto = p.read_text(encoding="utf-8")
        falhas += falhas_no_texto(nome, texto)
        for canal, palavra in DESCOBERTA.items():
            if re.search(rf"\b{canal}\b", texto) and palavra in texto.lower():
                vistos += 1

    if falhas:
        for f in falhas:
            print(f"X {f}")
        return 1
    print(f"OK ROTULO DE CANAL DE DESCOBERTA — {', '.join(sorted(DESCOBERTA))} exibido com a "
          f"palavra que diz o que é, em {vistos} de {len(ARQUIVOS)} arquivo(s) de rótulo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
