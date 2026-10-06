#!/usr/bin/env python3
"""
scripts/verificar_relogio_dos_derivados.py — derivado não carimba pelo relógio da parede
=========================================================================================
Item 2 do `HANDOVER_noite_confiavel_parte2_06-10-2026.md`: "se um derivado depende de relógio
(data/hora), torná-lo determinístico pela data do dado".

POR QUE ESTE PORTÃO EXISTE
---------------------------
`scripts/verificar_derivados.sh` fixa `SOURCE_DATE_EPOCH` no corte da edição para que a cadeia seja
reproduzível. Gerador que carimba com a data da PAREDE escapa disso: na virada do dia o runner
regenera com a data seguinte, o portão 12 acusa derivado obsoleto, e a publicação para por uma
diferença que não é de dado nenhum.

Aconteceu duas vezes, pelo mesmo motivo:

  §193, 24/09/2026  `gerar_card_municipios.py` — o CI rodou 01:21 UTC com o Brasil ainda em 23/09.
  06/10/2026        `scripts/gerar_codemap.py` — entrou na cadeia em 05/10 carimbando
                    "Atualizado em {hoje}", e derrubou NOVE publicações seguidas, das 23:53 às
                    06:09, com a noite inteira de dado coletado parada atrás.

A correção da primeira vez ficou escrita DENTRO do arquivo que a sofreu. Por isso o gerador
seguinte não a herdou. A regra agora tem dono (`coletores_base.data_do_corte`) e tem portão: este.

O QUE ELE COBRA
----------------
Todo script da cadeia canônica que leia a data de hoje tem de honrar `SOURCE_DATE_EPOCH` — na
prática, usar `data_do_corte`, ou ler a variável ele mesmo. Script da cadeia que chame
`hoje_editorial`, `date.today` ou `datetime.now` **sem** nenhuma menção a `SOURCE_DATE_EPOCH` é
reprovado, com o nome e a linha.

O que ele NÃO cobra: script fora da cadeia. Coletor que registra "consultado_em" tem de usar a data
da parede mesmo — é quando a consulta aconteceu, e fixá-la seria mentira.

USO
  python3 scripts/verificar_relogio_dos_derivados.py --autoteste
  python3 scripts/verificar_relogio_dos_derivados.py
"""
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
CADEIA = RAIZ / "scripts" / "verificar_derivados.sh"

# As formas de perguntar as horas à parede.
_RE_RELOGIO = re.compile(r"\b(hoje_editorial|date\.today|datetime\.now|time\.time)\s*\(")
# A forma de honrar o relógio fixado — direta ou pela função que a encapsula.
_RE_FIXADO = re.compile(r"SOURCE_DATE_EPOCH|data_do_corte")
# Um passo da cadeia: `python3 <script> …`, com ou sem comentário depois.
_RE_PASSO = re.compile(r"^\s*python3\s+(\S+\.py)", re.M)


def scripts_da_cadeia(texto: str) -> list:
    """Os `.py` que a cadeia canônica executa, na ordem. Função pura.

    Lê o shell em vez de manter uma segunda lista: lista paralela sai de sincronia, e foi
    exatamente assim que `CADEIA_DERIVADOS` divergiu em 22/09 e em 05/10.
    """
    vistos, fora = set(), []
    for m in _RE_PASSO.finditer(texto or ""):
        caminho = m.group(1)
        if caminho not in vistos:
            vistos.add(caminho)
            fora.append(caminho)
    return fora


def usa_relogio_da_parede(fonte: str) -> list:
    """As linhas que perguntam as horas à parede, se o arquivo não honra o relógio fixado.

    Função pura. Devolve [] quando o arquivo menciona `SOURCE_DATE_EPOCH` ou `data_do_corte`: aí a
    decisão está tomada no próprio arquivo, e é ela que vale.
    """
    if _RE_FIXADO.search(fonte or ""):
        return []
    fora = []
    for n, linha in enumerate(str(fonte or "").splitlines(), start=1):
        sem_comentario = linha.split("#")[0]
        m = _RE_RELOGIO.search(sem_comentario)
        if m:
            fora.append((n, m.group(1), linha.strip()[:90]))
    return fora


def problemas(cadeia_txt: str, fontes: dict) -> list:
    """Os scripts da cadeia que carimbam pela parede. Função pura.

    `fontes` é {caminho: texto}; caminho da cadeia que não esteja em `fontes` é ignorado — quem
    reclama de script ausente é a própria cadeia, ao não rodar.
    """
    fora = []
    for caminho in scripts_da_cadeia(cadeia_txt):
        fonte = (fontes or {}).get(caminho)
        if fonte is None:
            continue
        for n, chamada, trecho in usa_relogio_da_parede(fonte):
            fora.append(f"{caminho}:{n}: `{chamada}()` sem honrar SOURCE_DATE_EPOCH — "
                        f"o derivado muda sozinho na virada do dia · {trecho}")
    return fora


def _autoteste() -> int:
    falhas, contados = [], []

    def ok(nome, cond):
        contados.append(nome)
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    sh = ("export SOURCE_DATE_EPOCH=...\n"
          "python3 recalcular_mare.py --write >/dev/null\n"
          "python3 scripts/gerar_codemap.py >/dev/null   # comentário\n"
          "python3 recalcular_mare.py --write >/dev/null\n")
    ok("os passos da cadeia saem do shell", scripts_da_cadeia(sh)
       == ["recalcular_mare.py", "scripts/gerar_codemap.py"])
    ok("passo repetido entra uma vez só", scripts_da_cadeia(sh).count("recalcular_mare.py") == 1)
    ok("shell vazio não tem passo", scripts_da_cadeia("") == [])

    ok("relógio da parede é acusado", usa_relogio_da_parede("x = hoje_editorial()") != [])
    ok("`date.today` é acusado", usa_relogio_da_parede("d = date.today()") != [])
    ok("quem honra o relógio fixado passa",
       usa_relogio_da_parede("epoch = os.environ['SOURCE_DATE_EPOCH']\nx = hoje_editorial()") == [])
    ok("quem usa `data_do_corte` passa", usa_relogio_da_parede("x = data_do_corte()") == [])
    ok("chamada só em comentário não é acusada",
       usa_relogio_da_parede("# nunca use hoje_editorial() aqui") == [])
    ok("arquivo sem relógio passa", usa_relogio_da_parede("x = 1") == [])

    ok("o defeito de 06/10 seria pego",
       problemas("python3 scripts/gerar_codemap.py\n",
                 {"scripts/gerar_codemap.py": "novo = markdown(hoje_editorial())"}) != [])
    ok("o conserto de 06/10 passa",
       problemas("python3 scripts/gerar_codemap.py\n",
                 {"scripts/gerar_codemap.py": "novo = markdown(data_do_corte())"}) == [])
    ok("script fora da cadeia não é cobrado",
       problemas("python3 a.py\n", {"b.py": "hoje_editorial()"}) == [])
    ok("script da cadeia ausente do disco não quebra o portão",
       problemas("python3 sumiu.py\n", {}) == [])
    ok("a mensagem diz o arquivo e a linha",
       "gerar_codemap.py:1:" in problemas("python3 scripts/gerar_codemap.py\n",
                                          {"scripts/gerar_codemap.py": "x = date.today()"})[0])

    import dis
    nomes = set()
    for nome_obj, obj in list(globals().items()):
        if nome_obj in ("_autoteste", "main"):
            continue
        if getattr(obj, "__module__", None) not in (__name__, None):
            continue
        codigo = getattr(obj, "__code__", None)
        if codigo is not None:
            nomes |= {i.argval for i in dis.get_instructions(codigo) if isinstance(i.argval, str)}
    ok("trava estrutural: as funções puras não leem disco nem escrevem",
       not ({"read_text", "write_text", "urlopen"} & nomes))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else f"✓ AUTOTESTE OK — {len(contados)} casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def main(argv: list) -> int:
    if "--autoteste" in argv:
        return _autoteste()
    if not CADEIA.exists():
        print(f"✗ {CADEIA.relative_to(RAIZ)} não existe")
        return 1
    cadeia_txt = CADEIA.read_text(encoding="utf-8")
    fontes = {}
    for caminho in scripts_da_cadeia(cadeia_txt):
        arq = RAIZ / caminho
        if arq.exists():
            fontes[caminho] = arq.read_text(encoding="utf-8")
    fora = problemas(cadeia_txt, fontes)
    if fora:
        print(f"✗ RELÓGIO DOS DERIVADOS: {len(fora)} carimbo(s) pela parede:")
        for x in fora:
            print("   - " + x)
        print("   Use `coletores_base.data_do_corte()`: ela devolve a data do corte quando a "
              "cadeia fixa SOURCE_DATE_EPOCH, e a data editorial fora dela.")
        return 1
    print(f"✓ RELÓGIO DOS DERIVADOS OK — {len(fontes)} script(s) da cadeia canônica, nenhum "
          f"carimbando pelo relógio da parede.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
