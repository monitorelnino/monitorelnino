#!/usr/bin/env python3
"""
scripts/tipo_de_evento_dos_atos.py — o tipo de evento de cada ato de resposta
=============================================================================
Dependência declarada no `HANDOVER_blog_e_imprensa_definitivo_03-10-2026.md` (item 3): "o campo
**tipo de evento** dos decretos é necessário para os textos do blog; garantir que exista". Não
existia: os 929 eventos de `data/atos_resposta.json` tinham `causa` em texto livre e nada mais.

O QUE ELE FAZ, E O QUE ELE SE RECUSA A FAZER
--------------------------------------------
Deriva `tipo_evento` do campo `desastre` — que é a COBRADE do S2iD, o nome oficial do evento, e
está em 674 dos 929 registros — e, onde ele falta, da `causa`. A ordem importa: a `causa` dos
registros federais diz "reconhecimento federal", que é o CANAL do ato e não o evento que o motivou;
classificar por ela devolveria 923 "outro_declarado" e um campo inútil. Em ambos os casos, **só
quando o termo é inequívoco**:

    chuva · seca · fogo · vendaval · outro-declarado

Causa que não casa com nenhuma família, ou que casa com DUAS, fica com `tipo_evento: null`. Isso é
deliberado e é o ponto do script: o blog vai escrever frases a partir deste campo, e um tipo
adivinhado produziria uma frase errada com cara de fato. "Não classificado" é um resultado, e a
regra do projeto já diz que na dúvida o classificador não classifica.

O campo não entra em conta nenhuma do índice — ato de resposta não pontua. Ele existe para o texto.

USO
  python3 scripts/tipo_de_evento_dos_atos.py --autoteste
  python3 scripts/tipo_de_evento_dos_atos.py --relatorio
  python3 scripts/tipo_de_evento_dos_atos.py
"""
import collections
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

# 04/10/2026 (bloco da editoria): as famílias são estas cinco, e `granizo` passa a pertencer a
# VENDAVAL, não a chuva. A COBRADE separa "Granizo - 1.3.2.1.3" de "Vendaval - 1.3.2.1.5" dentro do
# mesmo grupo de tempestade, e é assim que a editoria as nomeia — o texto do blog diz "oito
# reconhecidas por vendaval e quatro por granizo" porque são eventos de tempestade, não de chuva
# acumulada. Granizo em "chuva" misturava enchente com temporal de vento.
FAMILIAS = {
    "chuva": re.compile(r"(?i)chuva|enchent|inunda|alagam|precipita|deslizam|hidrol|enxurrada"),
    "seca": re.compile(r"(?i)\bseca\b|estiagem|escassez h|d[eé]ficit h[íi]dric|desabastec"),
    "fogo": re.compile(r"(?i)inc[êe]ndi|queimad|fuma[çc]a|focos de calor"),
    "vendaval": re.compile(r"(?i)vendaval|tornado|ciclone|ventos? forte|microexplos|granizo"),
}
TIPOS = tuple(FAMILIAS) + ("outro_declarado", "sem_tipo_informado")


def familia_do_texto(texto: str) -> str | None:
    """A família do evento no texto, ou None quando o texto não decide. Função pura.

    Duas famílias ao mesmo tempo devolvem None de propósito: "chuva e vendaval" é um evento que o
    blog tem de descrever com as duas palavras, e escolher uma delas aqui esconderia a outra.
    """
    texto = texto or ""
    casam = [nome for nome, padrao in FAMILIAS.items() if padrao.search(texto)]
    if len(casam) == 1:
        return casam[0]
    if not casam and texto.strip():
        return "outro_declarado"
    return None


def tipo_de_evento(evento) -> str | None:
    """A família do evento, da COBRADE quando há, da causa quando não. Função pura.

    Aceita o evento inteiro, ou só um texto — chamar com texto é o que os casos de teste fazem, e
    é o que mantém a função verificável sem montar um registro completo a cada caso.
    """
    if isinstance(evento, str) or evento is None:
        return familia_do_texto(evento)
    pela_cobrade = familia_do_texto(evento.get("desastre"))
    if pela_cobrade and pela_cobrade != "outro_declarado":
        return pela_cobrade
    pela_causa = familia_do_texto(evento.get("causa"))
    if pela_causa and pela_causa != "outro_declarado":
        return pela_causa
    return pela_cobrade or pela_causa


def tipo_ou_sem_informacao(evento) -> str:
    """O tipo, ou `sem_tipo_informado` quando a fonte não diz. Função pura.

    04/10/2026: o blog e o painel precisam CONTAR à parte os atos cujo registro federal não informa
    o evento — são 255 dos 929, e 16 na semana de 27/09 a 03/10. `None` servia ao código e não
    servia ao texto: "sem tipo informado" é um desfecho, e desfecho tem nome.
    """
    return tipo_de_evento(evento) or "sem_tipo_informado"


def contagem(eventos: list) -> dict:
    """Quantos eventos por tipo, incluindo os não classificados. Função pura."""
    c = collections.Counter(tipo_ou_sem_informacao(e) for e in eventos)
    return {k: v for k, v in sorted(
        c.items(), key=lambda kv: (kv[0] is None, str(kv[0])))}


def _autoteste() -> int:
    falhas = []

    def ok(nome, cond):
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    ok("chuva intensa é chuva", tipo_de_evento("Chuvas Intensas - 1.3.2.1.4") == "chuva")
    # "chuva intensa COM granizo" é o caso de duas famílias, e devolve None de propósito: o texto
    # tem de dizer as duas palavras. São 5 eventos de SC, e eles ficam como não classificados.
    ok("chuva com granizo é o caso de duas famílias, e não escolhe uma",
       tipo_de_evento("chuva intensa com granizo") is None)
    ok("enchente é chuva", tipo_de_evento("enchente do rio") == "chuva")
    ok("estiagem é seca", tipo_de_evento("estiagem prolongada") == "seca")
    ok("incêndio é fogo", tipo_de_evento("incêndio em vegetação") == "fogo")
    ok("vendaval é vendaval", tipo_de_evento("vendaval com destelhamentos") == "vendaval")
    ok("granizo é tempestade, não chuva acumulada",
       tipo_de_evento("Granizo - 1.3.2.1.3") == "vendaval")
    ok("enxurrada é chuva", tipo_de_evento("Enxurradas - 1.2.2.0.0") == "chuva")
    ok("sem informação da fonte tem nome próprio",
       tipo_ou_sem_informacao({"desastre": None, "causa": None}) == "sem_tipo_informado")
    ok("duas famílias não escolhem uma",
       tipo_de_evento("chuva intensa e vendaval") is None)
    ok("causa vazia não vira tipo", tipo_de_evento("") is None and tipo_de_evento(None) is None)
    ok("causa que não casa fica declarada como outra",
       tipo_de_evento("colapso de ponte") == "outro_declarado")
    ok("'seca' dentro de outra palavra não casa",
       tipo_de_evento("ressecamento de pastagem") == "outro_declarado")

    ok("a COBRADE vence a causa, que é o canal do ato",
       tipo_de_evento({"desastre": "Estiagem - 1.4.1.1.0",
                       "causa": "reconhecimento federal"}) == "seca")
    ok("sem COBRADE, vale a causa",
       tipo_de_evento({"desastre": None, "causa": "estiagem prolongada"}) == "seca")
    ok("COBRADE que não casa não apaga a causa que casa",
       tipo_de_evento({"desastre": "Subsidências e colapsos - 1.1.3.4.0",
                       "causa": "estiagem"}) == "seca")
    ok("sem nada que decida, fica sem tipo",
       tipo_de_evento({"desastre": None, "causa": None}) is None)

    eventos = [{"causa": "chuva intensa"}, {"causa": "estiagem"}, {"causa": ""},
               {"causa": "chuva e vendaval"}]
    c = contagem(eventos)
    ok("a contagem separa quem a fonte não informou",
       c.get("sem_tipo_informado") == 2)
    ok("a contagem não perde evento", sum(c.values()) == len(eventos))
    ok("todo tipo devolvido está na lista declarada",
       all(t in TIPOS for t in (tipo_de_evento(x) for x in eventos) if t))

    import dis
    nomes = set()
    for nome_obj, obj in list(globals().items()):
        if nome_obj in ("_autoteste", "aplicar", "main"):
            continue
        codigo = getattr(obj, "__code__", None)
        if codigo is not None:
            nomes |= {i.argval for i in dis.get_instructions(codigo) if isinstance(i.argval, str)}
    ok("trava estrutural: as funções puras não escrevem",
       not ({"gravar", "write_text"} & nomes))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else "✓ AUTOTESTE OK — 21 casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def aplicar(relatorio: bool = False) -> int:
    from coletores_base import gravar, ler
    atos = ler("atos_resposta.json", {"eventos": []})
    eventos = atos.get("eventos", [])
    print("  " + " · ".join(f"{k}: {v}" for k, v in contagem(eventos).items()))
    if relatorio:
        return 0
    for e in eventos:
        # 04/10/2026: era `tipo_de_evento(e.get("causa"))` — a gravação passava só a CAUSA, de modo
        # que a COBRADE do campo `desastre` nunca era lida e 923 dos 929 eventos ficavam
        # "outro_declarado", exatamente o defeito que a editoria mediu. O relatório, que já passava
        # o evento inteiro, mostrava os números certos; a gravação, não. Função certa, argumento
        # errado — e a diferença só apareceu ao conferir o arquivo depois de gravar.
        e["tipo_evento"] = tipo_ou_sem_informacao(e)
    gravar("atos_resposta.json", atos)
    print(f"  {len(eventos)} evento(s) com `tipo_evento` gravado")
    return 0


def main() -> int:
    if "--autoteste" in sys.argv[1:]:
        return _autoteste()
    return aplicar(relatorio="--relatorio" in sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
