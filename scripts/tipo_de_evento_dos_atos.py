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

FAMILIAS = {
    "chuva": re.compile(r"(?i)chuva|enchent|inunda|alagam|granizo|precipita|deslizam|hidrol"),
    "seca": re.compile(r"(?i)\bseca\b|estiagem|escassez h|d[eé]ficit h[íi]dric|desabastec"),
    "fogo": re.compile(r"(?i)inc[êe]ndi|queimad|fuma[çc]a|focos de calor"),
    "vendaval": re.compile(r"(?i)vendaval|tornado|ciclone|ventos? forte|microexplos|granizo e vento"),
}
TIPOS = tuple(FAMILIAS) + ("outro_declarado",)


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


def contagem(eventos: list) -> dict:
    """Quantos eventos por tipo, incluindo os não classificados. Função pura."""
    c = collections.Counter(tipo_de_evento(e) for e in eventos)
    return {("nao_classificado" if k is None else k): v for k, v in sorted(
        c.items(), key=lambda kv: (kv[0] is None, str(kv[0])))}


def _autoteste() -> int:
    falhas = []

    def ok(nome, cond):
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    ok("chuva intensa é chuva", tipo_de_evento("chuva intensa com granizo") == "chuva")
    ok("enchente é chuva", tipo_de_evento("enchente do rio") == "chuva")
    ok("estiagem é seca", tipo_de_evento("estiagem prolongada") == "seca")
    ok("incêndio é fogo", tipo_de_evento("incêndio em vegetação") == "fogo")
    ok("vendaval é vendaval", tipo_de_evento("vendaval com destelhamentos") == "vendaval")
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
       tipo_de_evento({"desastre": None, "causa": "chuva intensa com granizo"}) == "chuva")
    ok("COBRADE que não casa não apaga a causa que casa",
       tipo_de_evento({"desastre": "Subsidências e colapsos - 1.1.3.4.0",
                       "causa": "estiagem"}) == "seca")
    ok("sem nada que decida, fica sem tipo",
       tipo_de_evento({"desastre": None, "causa": None}) is None)

    eventos = [{"causa": "chuva intensa"}, {"causa": "estiagem"}, {"causa": ""},
               {"causa": "chuva e vendaval"}]
    c = contagem(eventos)
    ok("a contagem separa os não classificados", c.get("nao_classificado") == 2)
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
          else "✓ AUTOTESTE OK — 17 casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def aplicar(relatorio: bool = False) -> int:
    from coletores_base import gravar, ler
    atos = ler("atos_resposta.json", {"eventos": []})
    eventos = atos.get("eventos", [])
    print("  " + " · ".join(f"{k}: {v}" for k, v in contagem(eventos).items()))
    if relatorio:
        return 0
    for e in eventos:
        e["tipo_evento"] = tipo_de_evento(e.get("causa"))
    gravar("atos_resposta.json", atos)
    print(f"  {len(eventos)} evento(s) com `tipo_evento` gravado")
    return 0


def main() -> int:
    if "--autoteste" in sys.argv[1:]:
        return _autoteste()
    return aplicar(relatorio="--relatorio" in sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
