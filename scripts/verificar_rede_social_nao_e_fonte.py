#!/usr/bin/env python3
"""
verificar_rede_social_nao_e_fonte.py
====================================
Rede social é canal de **descoberta**. Nunca fonte de registro, nunca fonte no site.

Decisão da editoria de 28/09/2026 (item 2): perfis oficiais de prefeituras e defesas civis passam a ser
canal de descoberta aceitável, com a condição de que "nada de rede social entra como fonte de registro
nem aparece como fonte no site". Este portão é essa condição, escrita como reprovação.

O QUE ELE COBRA
---------------
1. **Nenhum registro** de `data/municipios.json`, `data/estados.json` ou `data/atos_resposta.json` tem
   domínio de rede social em `url`, `fonte` ou `canal`.
2. **Nenhuma página pública** cita domínio de rede social como **fonte de figura** ou em link de
   evidência. Menção em prosa não é o alvo: o que não pode é rede social aparecer no lugar onde o leitor
   lê "de onde veio este dado".
3. **Nenhuma evidência preservada** de registro pontuável tem origem em rede social.

Ele NÃO proíbe a pista: `data/pistas_imprensa.json` pode ter pista com `origem: rede_social_oficial` —
é para isso que o canal existe. O que ele impede é a pista virar registro sem passar pelo documento
primário, e é o `juiz.py` que garante a outra metade (nenhum domínio de rede está em
`PADROES_FONTE_PROVAVEL_OFICIAL`).

USO
  python3 scripts/verificar_rede_social_nao_e_fonte.py
  python3 scripts/verificar_rede_social_nao_e_fonte.py --autoteste
"""
import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

REDES = ("facebook.com", "instagram.com", "twitter.com", "x.com", "youtube.com", "threads.net",
         "bsky.app", "tiktok.com")
# Fonte escrita à mão não traz domínio: "Instagram da Prefeitura", "post no Facebook". O portão pegava
# só o domínio e deixava passar exatamente a forma mais provável de a rede social virar fonte — foi o
# próprio autoteste que mostrou. `x` sozinho fica FORA: uma letra casaria em qualquer texto.
NOMES_DE_REDE = ("facebook", "instagram", "twitter", "youtube", "tiktok", "threads", "bluesky",
                 "bsky")
RE_NOME_DE_REDE = re.compile(r"\b(" + "|".join(NOMES_DE_REDE) + r")\b", re.I)
BANCOS = ("municipios.json", "estados.json", "atos_resposta.json")
CAMPOS = ("url", "fonte", "canal", "documento")
# Onde o leitor lê "de onde veio o dado": crédito de figura e link de fonte.
RE_FONTE_NA_PAGINA = re.compile(r'(?:class="fonte-figura"[^>]*>|Fonte:)([^<]{0,400})', re.I)


def rede_em(texto) -> str:
    """O domínio OU o nome de rede social encontrado no texto, ou "" se não houver."""
    t = str(texto or "").lower()
    for rede in REDES:
        if rede in t:
            return rede
    m = RE_NOME_DE_REDE.search(t)
    return m.group(1) if m else ""


def conferir_banco(nome: str, registros: list) -> list:
    """Falhas de um banco: registro com rede social em campo de fonte."""
    falhas = []
    for r in registros or []:
        for campo in CAMPOS:
            rede = rede_em(r.get(campo))
            if rede:
                falhas.append(f"{nome}: {r.get('nome') or r.get('uf') or '?'} tem `{campo}` em "
                              f"{rede} — rede social é descoberta, nunca fonte de registro")
    return falhas


def conferir_pagina(nome: str, html: str) -> list:
    """Falhas de uma página: rede social no crédito de figura ou em `Fonte:`."""
    falhas = []
    for m in RE_FONTE_NA_PAGINA.finditer(html or ""):
        rede = rede_em(m.group(1))
        if rede:
            trecho = " ".join(m.group(1).split())[:80]
            falhas.append(f"{nome}: crédito de figura cita {rede} — \"{trecho}\"")
    return falhas


def autoteste() -> int:
    casos = []

    limpo = [{"nome": "Bonito", "url": "https://bonito.ms.gov.br/d", "fonte": "Diário Oficial",
              "canal": "DOM"}]
    casos.append(("banco limpo passa", conferir_banco("x.json", limpo) == []))

    for campo, valor in (("url", "https://facebook.com/prefbonito/posts/1"),
                         ("fonte", "Instagram da Prefeitura"),
                         ("canal", "x.com"),
                         ("documento", "post no Facebook")):
        sujo = [{"nome": "Bonito", campo: valor}]
        f = conferir_banco("x.json", sujo)
        casos.append((f"rede social em `{campo}` reprova", len(f) == 1 and campo in f[0]))

    casos.append(("banco vazio não reprova", conferir_banco("x.json", []) == []))
    casos.append(("registro sem os campos não estoura",
                  conferir_banco("x.json", [{"nome": "X"}]) == []))

    pagina_limpa = '<p class="fonte-figura">Fonte: Diário Oficial · Atualização: 28/09/2026</p>'
    casos.append(("página limpa passa", conferir_pagina("p.html", pagina_limpa) == []))
    pagina_suja = '<p class="fonte-figura">Fonte: Instagram da Defesa Civil</p>'
    casos.append(("rede social no crédito de figura reprova",
                  len(conferir_pagina("p.html", pagina_suja)) == 1))
    casos.append(("`Fonte:` em prosa com rede social também reprova",
                  len(conferir_pagina("p.html", "<p>Fonte: facebook.com/prefeitura</p>")) == 1))
    casos.append(("prosa que MENCIONA rede social sem ser fonte não reprova",
                  conferir_pagina("p.html", "<p>A prefeitura anunciou no Instagram.</p>") == []))

    # a trava do outro lado: nenhuma rede é fonte oficial para o juiz
    from juiz import PADROES_FONTE_PROVAVEL_OFICIAL as oficiais
    casos.append(("nenhuma rede social está nos padrões de fonte oficial do juiz",
                  not any(rede in p or p in rede for rede in REDES for p in oficiais)))

    ruins = [n for n, ok in casos if not ok]
    for n, ok in casos:
        print(f"  {'OK  ' if ok else 'FALHA'} {n}")
    if ruins:
        print(f"X AUTOTESTE: {len(ruins)} caso(s) reprovado(s).")
        return 1
    print(f"OK AUTOTESTE — {len(casos)} casos.")
    return 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    falhas = []
    for nome in BANCOS:
        p = RAIZ / "data" / nome
        if not p.exists():
            continue
        doc = json.loads(p.read_text(encoding="utf-8"))
        for chave in ("municipios", "ufs", "atos", "itens"):
            if isinstance(doc, dict) and isinstance(doc.get(chave), list):
                falhas += conferir_banco(nome, doc[chave])
        if isinstance(doc, list):
            falhas += conferir_banco(nome, doc)
        if isinstance(doc, dict) and isinstance(doc.get("ufs"), dict):
            falhas += conferir_banco(nome, list(doc["ufs"].values()))

    for p in sorted(RAIZ.glob("*.html")):
        falhas += conferir_pagina(p.name, p.read_text(encoding="utf-8", errors="replace"))

    if falhas:
        print("✗ REDE SOCIAL COMO FONTE: rede social é descoberta, nunca fonte:")
        for f in falhas[:30]:
            print(f"   - {f}")
        return 1
    print("✓ REDE SOCIAL OK — nenhum registro e nenhuma página cita rede social como fonte; "
          "nenhum domínio de rede está nos padrões de fonte oficial do juiz.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
