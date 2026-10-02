#!/usr/bin/env python3
"""Portão: âncora interna citada por uma página existe na página citada.

Regra de sincronia do handover "Para gestores" (editoria, 01/10/2026), item 3: a seção "Como os
recursos chegam" é **só ponteiro** — nenhum conteúdo de financiamento é repetido em "Para gestores".
Ponteiro é mais barato que cópia e não divergir dela; o que ele tem de pior é quebrar em silêncio
quando a página de destino muda, e é isso que este portão existe para impedir.

O QUE ELE EXISTE PARA BARRAR
----------------------------
Já aconteceu duas vezes neste site, nas duas direções:

  - A página "Para gestores" tinha uma seção inteira sobre o período eleitoral apontando para
    `calendario-eleitoral.html`, **que havia sido apagado**. A seção ficou no ar com um link morto.
  - A página de imprensa prometia "o modelo de pedido de acesso à informação" em "Para gestores",
    e o gerador de pedido tinha saído da parte visível do site em 13/09/2026. A promessa ficou.

Link para arquivo que não existe um navegador acusa; **âncora para `id` que não existe, não**: o
navegador abre a página no topo e ninguém percebe. Daí o portão.

O QUE ELE CONFERE
-----------------
Para cada `href="pagina.html#ancora"` no HTML das páginas publicadas: o arquivo existe e tem um
elemento com aquele `id`. Âncora para a própria página (`href="#x"`) também conta — é o mesmo
defeito dentro de um arquivo só.

Uso: python3 scripts/verificar_ancoras_internas.py
"""
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent

# A varredura é GLOBAL: toda página publicada, por `glob`. Uma lista literal aqui duplicaria o
# glob e envelheceria na primeira página nova.
#
# `PADRAO` é outra coisa, e existe para o CODEMAP: é o PAR cuja sincronia dá razão a este portão —
# "Para gestores" aponta para "Financiamento" e não repete nada dele. O gerador do CODEMAP lê esta
# constante para dizer, na tabela, que as duas páginas são cobertas por esta regra; sem ela, o mapa
# diria que a regra não existe. Ela não restringe a varredura.
PADRAO = ["prefeituras.html", "financiamento.html"]

# `arquivo/` e `notas/` ficam fora: são histórico, não superfície.
PAGINAS = sorted(p for p in RAIZ.glob("*.html"))

RE_LINK = re.compile(r'href="([^"#]*)#([^"]+)"')
RE_ID = re.compile(r'\sid="([^"]+)"')

# `id`s que o JavaScript cria em tempo de execução e que, por isso, não estão no HTML. Cada linha é
# uma exceção NOMEADA: a lista existe para ser curta e conferível, não para crescer por conveniência.
IDS_EM_TEMPO_DE_EXECUCAO = {
    # (nenhuma até agora — toda âncora citada vive no HTML)
}


def ids_de(caminho: pathlib.Path) -> set:
    return set(RE_ID.findall(caminho.read_text(encoding="utf-8")))


def conferir() -> list:
    falhas = []
    cache = {}
    for pagina in PAGINAS:
        texto = pagina.read_text(encoding="utf-8")
        for arquivo, ancora in RE_LINK.findall(texto):
            if ancora.startswith(("/", "http")) or ":" in ancora:
                continue
            destino = pagina if not arquivo else (RAIZ / arquivo)
            if not destino.exists():
                falhas.append(f"{pagina.name}: aponta para '{arquivo}#{ancora}' e o arquivo "
                              f"'{arquivo}' não existe")
                continue
            if destino not in cache:
                cache[destino] = ids_de(destino)
            if ancora not in cache[destino] and ancora not in IDS_EM_TEMPO_DE_EXECUCAO:
                falhas.append(f"{pagina.name}: aponta para '{arquivo or pagina.name}#{ancora}' e "
                              f"não existe id='{ancora}' lá")
    return falhas


def autoteste() -> int:
    from coletores_base import rodar_autoteste
    casos = {
        # O portão tem de achar as âncoras que ele mesmo protege: as do "Para gestores" para a
        # página de financiamento.
        #
        # 01/10/2026: este caso trazia os nomes ESCRITOS À MÃO — `antes-do-desastre`,
        # `depois-do-desastre`, `preventivo`. O bloco C do handover renomeou as âncoras para
        # `antes`, `depois` e `setores`; a página e o `prefeituras.html` acompanharam, e o caso de
        # teste não. Resultado: a varredura passava (as âncoras citadas existem de verdade) e o
        # autoteste reprovava, cobrando três nomes que ninguém mais usa. Teste com nome fixo
        # envelhece em silêncio e depois reprova sozinho.
        #
        # Agora ele LÊ do `prefeituras.html` quais âncoras de financiamento são citadas e confere
        # que existem lá. Renomear uma âncora nos dois lugares continua passando; renomear num só
        # continua reprovando — que é a única coisa que este caso precisa saber.
        "as âncoras que o Para gestores cita existem em financiamento.html":
            lambda: (lambda citadas: bool(citadas) and citadas <= ids_de(RAIZ / "financiamento.html"))(
                {a for arq, a in RE_LINK.findall((RAIZ / "prefeituras.html").read_text(encoding="utf-8"))
                 if arq == "financiamento.html"}),
        # 02/10/2026 (item 2 do Financiamento minimalista): a editoria trocou a terceira âncora.
        # Era "#setores" (por setor), e passou a ser "#caminhos" — "os caminhos do dinheiro" —, que
        # é o bloco recolhido inteiro. O caso cobra as três que o handover novo nomeou.
        "o Para gestores cita as três âncoras que o handover nomeou":
            lambda: {a for arq, a in RE_LINK.findall((RAIZ / "prefeituras.html").read_text(encoding="utf-8"))
                     if arq == "financiamento.html"} == {"antes", "depois", "caminhos"},
        "o portão lê links com âncora":
            lambda: RE_LINK.findall('href="financiamento.html#preventivo"') == [("financiamento.html", "preventivo")],
        "o portão lê âncora da própria página":
            lambda: RE_LINK.findall('href="#caminho"') == [("", "caminho")],
        "o portão lê id":
            lambda: RE_ID.findall('<div class="x" id="caminho">') == ["caminho"],
        "link externo com fragmento não é cobrado":
            lambda: not conferir() or all("http" not in f for f in conferir()),
        "o par da regra de sincronia está declarado para o CODEMAP":
            lambda: PADRAO == ["prefeituras.html", "financiamento.html"],
        "a varredura é global, não só o par":
            lambda: len(PAGINAS) > len(PADRAO),
    }
    return rodar_autoteste(casos)


def main() -> int:
    if "--autoteste" in sys.argv[1:]:
        sys.path.insert(0, str(RAIZ))
        return autoteste()
    falhas = conferir()
    if falhas:
        print("✗ ÂNCORAS INTERNAS:")
        for f in falhas:
            print("   -", f)
        return 1
    print(f"✓ ÂNCORAS INTERNAS OK — toda âncora citada nas {len(PAGINAS)} páginas existe na página citada.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
