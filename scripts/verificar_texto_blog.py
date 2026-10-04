#!/usr/bin/env python3
"""
scripts/verificar_texto_blog.py — o portão do texto do blog, antes de publicar
===============================================================================
`HANDOVER_blog_rotina_semanal_04-10-2026.md`, item 2.

O QUE ELE É, E O QUE ELE NUNCA FAZ
-----------------------------------
Roda sobre cada texto com `aprovado: sim` e responde uma pergunta: **este texto pode ir ao ar?**
Falha **bloqueia só aquele texto** — nunca a publicação do site. Um texto reprovado fica fora do
índice e o motivo vai ao relatório; o resto do site publica.

Ele **nunca altera o texto** e **nunca muda a marca de aprovação**. Quem escreve é a central, quem
aprova é a editoria; este arquivo só confere.

A trava que importa é a (b): **todo número e toda data do corpo tem de estar no pacote**. É ela que
impede o texto de afirmar o que o dado não sustenta — e, quando ela reprova um texto correto, a
conclusão é que **o pacote está incompleto**, e se corrige o gerador do pacote, não o texto.

USO
  python3 scripts/verificar_texto_blog.py --autoteste
  python3 scripts/verificar_texto_blog.py                 # todos os textos aprovados
  python3 scripts/verificar_texto_blog.py --texto blog/posts/2026-10-04-....md
"""
import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

DIR_POSTS = RAIZ / "blog" / "posts"
DIR_PACOTES = RAIZ.parent / "robo-registro" / "blog" / "pacotes"
CABECALHO = ("titulo", "abertura", "etiqueta", "data", "fontes", "aprovado")
ETIQUETAS = ("Legal e financiamento", "Saúde", "Acontecimento")
PALAVRAS_MIN, PALAVRAS_MAX = 250, 450

# O vocabulário proibido do guia de redação. `nota` e `apenas` entram como palavra inteira: "notas"
# e "apenasado" não existem, mas "anotação" e "apenas" sim, e o teste de substring pegaria a
# primeira. Medido no primeiro texto aprovado, que diz "anotação" em nenhum lugar mas diz
# "apenas" em nenhum — o cuidado é para o próximo.
PROIBIDAS = ("desastre", "pago", "pagos", "pagamento", "apenas", "graças a",
             "obrigatório", "deve", "dever")
TERMOS_TECNICOS = ("reconhecimento", "homologação", "decreto", "aviso", "alerta",
                   "semana epidemiológica", "faixa esperada", "S2iD", "Sinan")
FRASES_DE_SAUDE = ("parciais", "não indica")
MARCAS_DE_LISTA = ("\n- ", "\n* ", "\n1. ", "\n#", "<ul", "<ol", "<table", "cartao")


def ler_cabecalho(texto: str) -> tuple:
    """(meta, corpo) do arquivo .md. Função pura."""
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", texto or "", re.S)
    if not m:
        return {}, (texto or "")
    meta = {}
    for linha in m.group(1).splitlines():
        if ":" not in linha:
            continue
        k, v = linha.split(":", 1)
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        meta[k.strip().lower()] = v
    return meta, m.group(2).strip()


def numeros_do_corpo(corpo: str) -> list:
    """Os números e as datas que o corpo escreve, nas grafias em que aparecem. Função pura.

    Pega inteiro com e sem ponto de milhar, decimal com vírgula, data em dd/mm/aaaa e em ISO. O
    dia-por-extenso ("3 de outubro de 2026") sai como o número do dia e o ano, que é como ele
    aparece — a data completa por extenso é conferida pela presença dos dois.
    """
    achados = re.findall(r"\d{1,3}(?:\.\d{3})+|\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2}|"
                         r"\d+(?:,\d+)?", corpo or "")
    return [a for a in achados]


def fora_do_pacote(corpo: str, permitidos: list) -> list:
    """Os números do corpo que o pacote não autoriza. Função pura."""
    ok = {str(x).strip() for x in (permitidos or [])}
    return sorted({n for n in numeros_do_corpo(corpo) if n not in ok})


def vocabulario_proibido(corpo: str, proibidas=PROIBIDAS) -> list:
    """As palavras proibidas que o corpo usa, fora de citação entre aspas. Função pura."""
    # O que está entre aspas é citação de lei ou de ato, e o guia permite: tira-se antes de olhar.
    sem_citacao = re.sub(r"[\"“][^\"”]{0,400}[\"”]", " ", corpo or "")
    fora = []
    for p in proibidas:
        if re.search(r"(?i)(?<![a-zà-ú])" + re.escape(p) + r"(?![a-zà-ú])", sem_citacao):
            fora.append(p)
    return fora


def problemas_de_prosa(corpo: str) -> list:
    """Marcadores que o blog não aceita no corpo. Função pura."""
    fora = []
    for marca in MARCAS_DE_LISTA:
        if marca in (corpo or ""):
            fora.append(marca.strip() or marca)
    return fora


def contar_palavras(corpo: str) -> int:
    """Palavras do corpo. Função pura."""
    return len(re.sub(r"<[^>]+>", " ", corpo or "").split())


def avisos(corpo: str, etiqueta: str) -> list:
    """O que merece um olhar, sem bloquear. Função pura."""
    fora = []
    # O guia avisa a partir de SEIS nomes de cidade; o padrão pega "em/de/no/na" seguido de nome
    # próprio, que é como o texto os escreve. É aviso, nunca bloqueio: contar nomes é indício de
    # lista decorativa, e indício não reprova texto.
    LIMITE_DE_CIDADES = 6
    cidades = re.findall(r"\b(?:em|de|no|na)\s+[A-ZÁ-Ú][a-zà-ú]+(?:\s+[a-zà-ú]+)?", corpo or "")
    if len(cidades) > LIMITE_DE_CIDADES:
        fora.append(f"{len(cidades)} menções a lugar, acima de {LIMITE_DE_CIDADES} — o guia pede "
                    f"nome de cidade só quando ele diz algo")
    for t in TERMOS_TECNICOS:
        if re.search(r"(?i)\b" + re.escape(t) + r"\b", corpo or ""):
            trecho = re.split(r"(?<=[.!?])\s", corpo or "")
            primeira = next((f for f in trecho if re.search(r"(?i)\b" + re.escape(t) + r"\b", f)), "")
            if len(primeira.split()) < 12:
                fora.append(f"termo técnico «{t}» na primeira ocorrência sem explicação na frase")
    return fora


def problemas(meta: dict, corpo: str, pacote: dict, exige_pacote: bool = True) -> list:
    """Os problemas BLOQUEANTES do texto. Função pura — é ela que o autoteste exercita."""
    fora = []
    faltam = [c for c in CABECALHO if not (meta or {}).get(c)]
    if faltam:
        fora.append(f"cabeçalho sem {', '.join(faltam)}")
    etiqueta = str((meta or {}).get("etiqueta") or "")
    if etiqueta and etiqueta not in ETIQUETAS:
        fora.append(f"etiqueta {etiqueta!r} fora de {list(ETIQUETAS)}")
    if exige_pacote and not (meta or {}).get("pacote"):
        fora.append("cabeçalho sem `pacote`: o texto só pode afirmar o que está no pacote da semana")

    n = contar_palavras(corpo)
    if not (PALAVRAS_MIN <= n <= PALAVRAS_MAX):
        fora.append(f"{n} palavras, fora de {PALAVRAS_MIN}–{PALAVRAS_MAX}")

    marcas = problemas_de_prosa(corpo)
    if marcas:
        fora.append(f"o corpo não é prosa corrida: {', '.join(marcas)}")

    proibidas = vocabulario_proibido(corpo)
    if proibidas:
        fora.append(f"vocabulário proibido pelo guia: {', '.join(proibidas)}")

    if pacote:
        sobrando = fora_do_pacote(corpo, (pacote or {}).get("numeros_permitidos"))
        if sobrando:
            fora.append("número fora do pacote: " + ", ".join(sobrando[:8])
                        + " — se o texto está certo, o PACOTE está incompleto")
    elif exige_pacote:
        fora.append(f"pacote {(meta or {}).get('pacote')!r} não encontrado para conferir os números")

    if etiqueta == "Saúde":
        faltando = [f for f in FRASES_DE_SAUDE if f not in (corpo or "")]
        if faltando:
            fora.append("texto de saúde sem a frase de parcialidade e/ou a de que os números não "
                        "indicam relação com o El Niño")
    return fora


def _autoteste() -> int:
    falhas = []

    def ok(nome, cond):
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    cab = ("---\ntitulo: \"T\"\nabertura: \"A\"\netiqueta: Acontecimento\ndata: 2026-10-04\n"
           "fontes: \"F\"\naprovado: sim\npacote: 2026-10-03_legal\n---\n")
    corpo_ok = ("Na semana houve 59 reconhecimentos. " + "palavra " * 260)
    meta, corpo = ler_cabecalho(cab + corpo_ok)
    ok("o cabeçalho é lido sem as aspas do YAML", meta["titulo"] == "T")
    ok("o corpo começa depois do cabeçalho", corpo.startswith("Na semana"))

    pac = {"numeros_permitidos": ["59"]}
    ok("texto com número do pacote passa", problemas(meta, corpo, pac) == [])
    ok("número fora do pacote bloqueia",
       any("fora do pacote" in x for x in problemas(meta, "Houve 77 atos. " + "p " * 260, pac)))
    ok("a mensagem diz que o pacote pode estar incompleto",
       "PACOTE está incompleto" in " ".join(problemas(meta, "Houve 77. " + "p " * 260, pac)))

    ok("cabeçalho incompleto bloqueia",
       any("cabeçalho sem" in x for x in problemas({"titulo": "T"}, corpo, pac)))
    ok("sem pacote declarado bloqueia",
       any("sem `pacote`" in x for x in problemas({k: v for k, v in meta.items()
                                                   if k != "pacote"}, corpo, pac)))
    ok("exceção declarada: texto anterior à rotina passa sem pacote",
       not any("sem `pacote`" in x for x in problemas({k: v for k, v in meta.items()
                                                       if k != "pacote"}, corpo, pac,
                                                      exige_pacote=False)))
    ok("etiqueta fora da lista bloqueia",
       any("etiqueta" in x for x in problemas(dict(meta, etiqueta="Boletim"), corpo, pac)))

    ok("texto curto bloqueia", any("palavras" in x for x in problemas(meta, "curto", pac)))
    ok("texto longo bloqueia",
       any("palavras" in x for x in problemas(meta, "palavra " * 500, pac)))

    ok("lista no corpo bloqueia", problemas_de_prosa("texto\n- item") == ["-"])
    ok("subtítulo no corpo bloqueia", "#" in str(problemas_de_prosa("texto\n## titulo")))
    ok("tabela no corpo bloqueia", problemas_de_prosa("<table>") == ["<table"])
    ok("prosa limpa passa", problemas_de_prosa("um texto corrido, com vírgulas.") == [])

    ok("palavra proibida bloqueia", vocabulario_proibido("houve um desastre") == ["desastre"])
    ok("palavra proibida DENTRO de citação não bloqueia",
       vocabulario_proibido('a lei diz "é obrigatório o plano"') == [])
    ok("palavra que só CONTÉM a proibida não bloqueia",
       vocabulario_proibido("a anotação do deveras pagador") == [])
    ok("'deve' solto bloqueia, porque o guia o proíbe fora de citação",
       "deve" in vocabulario_proibido("o município deve publicar"))

    saude = dict(meta, etiqueta="Saúde")
    ok("texto de saúde sem as duas frases bloqueia",
       any("não indicam relação" in x for x in problemas(saude, corpo, pac)))
    corpo_saude = ("As semanas recentes são parciais e sobem com notificações atrasadas; os "
                   "números não indicam relação com o El Niño. " + "palavra " * 250)
    ok("texto de saúde com as duas frases passa", problemas(saude, corpo_saude, pac) == [])

    ok("número com ponto de milhar é reconhecido", "8.146" in numeros_do_corpo("foram 8.146 casos"))
    ok("data em dd/mm/aaaa é reconhecida", "27/09/2026" in numeros_do_corpo("em 27/09/2026"))
    ok("decimal com vírgula é reconhecido", "45,3" in numeros_do_corpo("índice 45,3"))

    av = avisos("Em Turvo, em Canelinha, em Ibicaré, em Cerrito, em Rio Grande, em Braga, "
                "em Santiago, em Cordeiros, em Bom Jesus, em Cacimba, em Vilhena, em Ariquemes, "
                "em Porto Velho.", "Acontecimento")
    ok("muitas menções a lugar viram AVISO, não bloqueio", any("menções a lugar" in x for x in av))
    ok("aviso não é problema bloqueante",
       problemas(meta, "Em Turvo, em Canelinha. " + "palavra " * 260, {"numeros_permitidos": []})
       == [])

    import dis
    nomes = set()
    for nome_obj, obj in list(globals().items()):
        if nome_obj in ("_autoteste", "main", "conferir"):
            continue
        codigo = getattr(obj, "__code__", None)
        if codigo is not None:
            nomes |= {i.argval for i in dis.get_instructions(codigo) if isinstance(i.argval, str)}
    ok("trava estrutural: o verificador não escreve",
       not ({"gravar", "write_text", "write_bytes"} & nomes))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else "✓ AUTOTESTE OK — 28 casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def pacote_de(meta: dict) -> dict:
    """O pacote declarado no cabeçalho, se existir no disco."""
    ident = str((meta or {}).get("pacote") or "").strip()
    if not ident:
        return {}
    caminho = DIR_PACOTES / f"{ident}.json"
    if not caminho.exists():
        return {}
    return json.loads(caminho.read_text(encoding="utf-8"))


def conferir(caminhos: list) -> int:
    """Confere cada texto e imprime o veredito. Não escreve nada."""
    # Exceção declarada (04/10/2026): o primeiro texto aprovado foi escrito ANTES de a rotina de
    # pacotes existir, e o Code não altera texto aprovado para fazê-lo caber numa regra posterior.
    # Ele é conferido em tudo, menos na exigência de `pacote`. A exceção é desta data e deste
    # arquivo; o próximo texto já nasce com pacote.
    SEM_PACOTE_POR_DECISAO = {"2026-10-04-reconhecimentos-da-semana.md"}
    reprovados = 0
    for caminho in caminhos:
        meta, corpo = ler_cabecalho(pathlib.Path(caminho).read_text(encoding="utf-8"))
        if str(meta.get("aprovado") or "").lower() not in ("sim", "s", "true"):
            print(f"  [pulado] {pathlib.Path(caminho).name}: sem `aprovado: sim`")
            continue
        exige = pathlib.Path(caminho).name not in SEM_PACOTE_POR_DECISAO
        p = problemas(meta, corpo, pacote_de(meta), exige_pacote=exige)
        a = avisos(corpo, meta.get("etiqueta") or "")
        nome = pathlib.Path(caminho).name
        if p:
            reprovados += 1
            print(f"  ✗ {nome}: {len(p)} problema(s)")
            for x in p:
                print(f"      · {x}")
        else:
            extra = "" if exige else " (sem pacote, por exceção declarada de 04/10/2026)"
            print(f"  ✓ {nome}: {contar_palavras(corpo)} palavras, números conferidos{extra}")
        for x in a:
            print(f"      ⚠ {x}")
    if reprovados:
        print(f"✗ TEXTO DO BLOG: {reprovados} texto(s) não podem ir ao ar — o site publica, eles "
              f"não.")
        return 1
    print(f"✓ TEXTO DO BLOG OK — {len(caminhos)} texto(s) conferido(s).")
    return 0


def main() -> int:
    argv = sys.argv[1:]
    if "--autoteste" in argv:
        return _autoteste()
    if "--texto" in argv:
        alvos = [argv[argv.index("--texto") + 1]]
    else:
        alvos = sorted(str(p) for p in DIR_POSTS.glob("*.md")) if DIR_POSTS.exists() else []
    if not alvos:
        print("✓ TEXTO DO BLOG OK — nenhum texto a conferir.")
        return 0
    return conferir(alvos)


if __name__ == "__main__":
    sys.exit(main())
