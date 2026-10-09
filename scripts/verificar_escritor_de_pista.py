#!/usr/bin/env python3
"""
scripts/verificar_escritor_de_pista.py — a fila de pistas tem UMA porta
========================================================================
Item 1.2 do `HANDOVER_noite_confiavel_05-10-2026.md`.

POR QUE ELE EXISTE. Em 03/10/2026 o esquema da pista passou a valer e
`coletores_base.gravar_pista` passou a recusar o que não o cumprisse. Em 04/10 a publicação
reprovou **oito vezes** por **655 pistas** sem `url_final`, `tipo`, `alvo` nem `nivel` — porque os
coletores que as gravaram **nunca usaram aquela porta**: montavam o dicionário e chamavam
`gravar("pistas_imprensa.json", doc)` direto.

"Migrar todos os coletores" é um estado, e estado se perde: basta um coletor novo escrever o
arquivo por conta própria para a validação voltar a ser opcional. Então a regra passa a ser
estrutural e conferida no PR: **só `scripts/pistas.py` abre `data/pistas_*.json` para escrita.**

O que o portão procura, no fonte dos `.py` da árvore:

  · `gravar("pistas_*.json", ...)` e `gravar_em(... "pistas_*.json" ...)`;
  · `open(... "pistas_*.json" ..., "w")` e `write_text` sobre um caminho de pista.

Quem pode escrever: `scripts/pistas.py` (a porta), `scripts/verificar_esquema_de_pista.py` (a
quarentena, que é a rede de segurança da própria fila) e os utilitários de manutenção declarados
em `MANUTENCAO` — limpeza, triagem, união de conflito e migração, que são operações sobre a fila
inteira e não entrada de pista nova.

USO
    python3 scripts/verificar_escritor_de_pista.py --autoteste
    python3 scripts/verificar_escritor_de_pista.py
"""
from __future__ import annotations

import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent

# A porta, e a rede de segurança da porta.
ESCRITORES = (
    "scripts/pistas.py",
    "scripts/verificar_esquema_de_pista.py",
)

# Operações sobre a fila INTEIRA, não entrada de pista nova: elas reescrevem o que já está lá
# (limpa, tria, une conflito, migra esquema). Cada uma aqui é uma decisão, não um esquecimento —
# acrescentar à lista é dizer, por escrito, que aquele arquivo mexe na fila e não a alimenta.
MANUTENCAO = (
    "scripts/limpar_fila_de_pistas.py",
    "scripts/triar_fila.py",
    "scripts/unir_conflito_de_rodada.py",
    "scripts/rejulgar_decisoes_do_juiz.py",
    "scripts/corrigir_atribuicao_por_dominio.py",
    "scripts/fila_do_juiz_querido_diario.py",
    "scripts/migrar_pistas_para_o_esquema.py",
    "scripts/migrar_fim_da_etapa_humana.py",
    "revisar_pistas.py",
    "julgar_filas.py",
    "julgar_e_aplicar_descobertas.py",
    "classificar_pista_civil.py",
    "aplicar_c10_imprensa.py",
    "triar_confianca_pistas.py",
)

PASTAS_IGNORADAS = ("arquivo/", ".git/", "node_modules/", "scripts/testar_", "scripts/verificar_")

ALVO = r"pistas_[a-z_]*\.json"
PADROES = (
    (re.compile(r'\bgravar\s*\(\s*["\'](?:data/)?' + ALVO), "gravar() direto no arquivo da fila"),
    (re.compile(r'\bgravar_em\s*\([^)\n]*' + ALVO), "gravar_em() direto no arquivo da fila"),
    (re.compile(r'\bopen\s*\([^)\n]*' + ALVO + r'[^)\n]*["\'][wa]'), "open() em modo de escrita"),
    (re.compile(r'' + ALVO + r'[^\n]{0,80}\.write_text'), "write_text() no arquivo da fila"),
)


def relativo(caminho, raiz=None) -> str:
    """O caminho como o portão o nomeia, com barra para frente. Função pura."""
    try:
        return pathlib.Path(caminho).resolve().relative_to(
            (raiz or RAIZ)).as_posix()
    except ValueError:
        return pathlib.Path(caminho).as_posix()


LEGADOS = RAIZ / "config" / "escritores_legados.json"


def legados(caminho=LEGADOS) -> dict:
    """{arquivo: linha} da dívida nomeada. Linha sem `falta` NÃO vale e fica fora.

    09/10/2026 (A7-19). Quando o portão passou a ver escrita por variável e em linha lógica
    partida, apareceram 18 escritas que escapavam da regra 1 de 05/10. Quatro tocam fila que o
    juiz lê. Elas não viram verde por decreto: cada uma está em `config/escritores_legados.json`
    com a fila, o motivo e **o que falta fazer**, e o portão imprime a lista toda vez. Dívida sem
    `falta` é exceção disfarçada, e esta função a descarta — ela volta a reprovar.
    """
    try:
        import json
        dados = json.loads(pathlib.Path(caminho).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {str(x.get("arquivo")): x for x in (dados.get("legados") or [])
            if x.get("arquivo") and x.get("falta") and x.get("motivo")}


def pode_escrever(rel: str) -> bool:
    """Este arquivo tem licença para abrir a fila para escrita? Função pura."""
    rel = str(rel or "").replace("\\", "/")
    if rel in ESCRITORES or rel in MANUTENCAO:
        return True
    return any(rel.startswith(x) for x in PASTAS_IGNORADAS)


RE_ATRIBUI_FILA = re.compile(
    r"^\s*([A-Za-z_][A-Za-z_0-9]*)\s*=\s*[^\n]*[\"\'](?:data/)?" + ALVO)
RE_ESCRITA_GENERICA = re.compile(
    r"\b(?:gravar|gravar_em)\s*\(\s*([A-Za-z_][A-Za-z_0-9]*)\b|"
    r"\b([A-Za-z_][A-Za-z_0-9]*)\s*\.\s*write_text\s*\(")


def logicas(fonte: str) -> list:
    """(primeira_linha, texto) de cada LINHA LÓGICA do fonte. Função pura.

    09/10/2026 (A7-19). Os padrões exigiam o nome do arquivo e a chamada de escrita na MESMA
    linha física: `[^)\n]` e `{0,80}` param na quebra. Uma escrita partida em duas linhas — que é
    como ela sai de qualquer formatador com limite de coluna — passava inteira pelo portão. Juntar
    as linhas lógicas antes de procurar fecha isso sem tocar nos padrões.

    O critério é o do parêntese aberto: enquanto a linha tiver mais `(`, `[` ou `{` abertos que
    fechados, a seguinte faz parte dela. É aproximado — parêntese dentro de texto entre aspas
    conta errado —, e aproximado basta: o erro possível é juntar linha demais, o que faz o portão
    ver MAIS, nunca menos.
    """
    fora = []
    buffer_, inicio, saldo = "", 0, 0
    for n, linha in enumerate(str(fonte or "").splitlines(), start=1):
        if not buffer_ and linha.lstrip().startswith("#"):
            continue
        if not buffer_:
            inicio = n
        buffer_ += (" " if buffer_ else "") + linha.strip()
        saldo += sum(linha.count(c) for c in "([{") - sum(linha.count(c) for c in ")]}")
        if saldo <= 0:
            fora.append((inicio, buffer_))
            buffer_, saldo = "", 0
    if buffer_:
        fora.append((inicio, buffer_))
    return fora


def nomes_de_fila(fonte: str) -> set:
    """As variáveis que recebem o nome de um arquivo de fila. Função pura.

    09/10/2026 (A7-19). `FILA = "data/pistas_imprensa.json"` seguido de `gravar_em(FILA, doc)` não
    tem o literal na linha da escrita, e nenhum padrão o alcançava — bastava uma variável para
    abrir a fila por fora da porta. Aqui o portão aprende o nome, e a escrita por variável conta
    como escrita no arquivo.
    """
    fora = set()
    for _n, texto in logicas(fonte):
        m = RE_ATRIBUI_FILA.match(texto)
        if m:
            fora.add(m.group(1))
    return fora


def escritas_no_fonte(fonte: str) -> list:
    """As escritas na fila que este fonte contém, como lista de (linha, motivo). Função pura.

    Linha comentada não conta: o comentário que explica a regra não é violação dela — e a
    explicação é obrigatória neste projeto, de modo que cobrá-la seria cobrar a documentação.

    09/10/2026 (A7-19): procura na LINHA LÓGICA, não na física, e conhece as variáveis que guardam
    o nome da fila.
    """
    fora = []
    variaveis = nomes_de_fila(fonte)
    for n, texto in logicas(fonte):
        achou = ""
        for padrao, motivo in PADROES:
            if padrao.search(texto):
                achou = motivo
                break
        if not achou and variaveis:
            m = RE_ESCRITA_GENERICA.search(texto)
            if m and (m.group(1) or m.group(2)) in variaveis:
                achou = (f"escrita na fila por variável ({m.group(1) or m.group(2)}) — "
                         f"o nome do arquivo está noutra linha")
        if achou:
            fora.append((n, achou))
    return fora


def problemas(fontes: dict, divida: dict = None) -> list:
    """`{caminho_relativo: fonte}` → a lista de violações. Função pura dado `divida`.

    `divida` é o mapa de `legados()`: arquivo nomeado ali não reprova, porque já está registrado
    com o que falta. Tudo o que não está nem na porta, nem em MANUTENCAO, nem na dívida, reprova.
    """
    divida = divida if divida is not None else {}
    fora = []
    for rel in sorted(fontes):
        if pode_escrever(rel) or rel in divida:
            continue
        for n, motivo in escritas_no_fonte(fontes[rel]):
            fora.append(f"{rel}:{n}: {motivo} — use scripts/pistas.gravar() ou gravar_lote()")
    return fora


def _autoteste() -> int:
    falhas = []
    # O total era um literal e envelhecia calado: dizia cobrir mais casos do que
    # cobre, ou menos. Agora e contado.
    _casos_contados = []

    def ok(nome, cond):
        _casos_contados.append(nome)
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    ok("gravar() direto é violação",
       len(escritas_no_fonte('    gravar("pistas_imprensa.json", doc)')) == 1)
    ok("gravar_em() direto é violação",
       len(escritas_no_fonte('    gravar_em(RAIZ / "data" / "pistas_doe.json", doc)')) == 1)
    ok("open() em escrita é violação",
       len(escritas_no_fonte('    open("data/pistas_revisao.json", "w")')) == 1)
    ok("write_text é violação",
       len(escritas_no_fonte('    (R / "data/pistas_imprensa.json").write_text(x)')) == 1)
    ok("leitura NÃO é violação",
       escritas_no_fonte('    doc = ler("pistas_imprensa.json")') == [])
    ok("open() em leitura NÃO é violação",
       escritas_no_fonte('    open("data/pistas_imprensa.json")') == [])
    ok("comentário que cita a regra não é violação",
       escritas_no_fonte('    # nunca: gravar("pistas_imprensa.json", doc)') == [])
    ok("outro arquivo de data/ não é alcançado",
       escritas_no_fonte('    gravar("municipios.json", doc)') == [])
    ok("gravar_lote é o caminho certo e não é violação",
       escritas_no_fonte('    gravar_lote(novas, origem="busca_web")') == [])
    ok("a porta pode escrever", pode_escrever("scripts/pistas.py"))
    ok("a quarentena pode escrever", pode_escrever("scripts/verificar_esquema_de_pista.py"))
    ok("a manutenção declarada pode escrever", pode_escrever("scripts/triar_fila.py"))
    ok("coletor comum NÃO pode escrever", not pode_escrever("monitorar_redes_oficiais.py"))
    ok("coletor novo e desconhecido NÃO pode escrever",
       not pode_escrever("coletar_coisa_nova.py"))
    ok("o arquivo morto não é cobrado", pode_escrever("arquivo/scripts/caderno_de_pistas.py"))
    ok("barra invertida do Windows não escapa da regra",
       pode_escrever("scripts\\pistas.py"))
    ok("um coletor em falta é nomeado com linha e motivo",
       problemas({"meu_coletor.py": '\n\ngravar("pistas_imprensa.json", d)'})
       == ["meu_coletor.py:3: gravar() direto no arquivo da fila — "
           "use scripts/pistas.gravar() ou gravar_lote()"])
    ok("a porta não é nomeada",
       problemas({"scripts/pistas.py": 'gravar("pistas_imprensa.json", d)'}) == [])
    # 09/10/2026 (A7-19): escrita por VARIAVEL e em linha logica PARTIDA.
    por_variavel = "FILA = " + repr("data/pistas_imprensa.json") + chr(10) + "gravar_em(FILA, doc)"
    ok("escrita por variavel e vista",
       any("por variável" in x for x in problemas({"c.py": por_variavel})))
    nao_fila = "OUTRO = " + repr("data/estados.json") + chr(10) + "gravar_em(OUTRO, doc)"
    ok("variavel que nao e fila nao acusa", problemas({"c.py": nao_fila}) == [])
    partida = "gravar_em(" + chr(10) + "    " + repr("data/pistas_imprensa.json") + ", doc)"
    ok("escrita partida em duas linhas e vista", problemas({"c.py": partida}) != [])
    ok("linha logica junta o que o parentese abriu",
       len(logicas("f(" + chr(10) + "  1," + chr(10) + "  2)" + chr(10) + "g()")) == 2)
    ok("comentario segue nao contando",
       problemas({"c.py": "# gravar(" + repr("pistas_imprensa.json") + ", d)"}) == [])
    por_write = "P = " + repr("data/pistas_doe.json") + chr(10) + "P.write_text(x)"
    ok("write_text por variavel e visto",
       any("por variável" in x for x in problemas({"c.py": por_write})))
    # a divida nomeada
    ok("fonte na divida nao reprova",
       problemas({"c.py": por_variavel},
                 {"c.py": {"arquivo": "c.py", "falta": "migrar", "motivo": "x"}}) == [])
    ok("divida que nao existe em disco devolve vazio",
       legados(caminho="/caminho/que/nao/existe.json") == {})
    ok("a divida real esta declarada, e toda linha diz o que falta",
       bool(legados()) and all(x.get("falta") and x.get("motivo")
                               for x in legados().values()))
    ok("árvore limpa devolve lista vazia", problemas({}) == [])

    import dis
    nomes = set()
    for nome_obj in ("relativo", "pode_escrever", "escritas_no_fonte", "problemas"):
        codigo = getattr(globals()[nome_obj], "__code__", None)
        if codigo is not None:
            nomes |= {i.argval for i in dis.get_instructions(codigo) if isinstance(i.argval, str)}
    ok("trava estrutural: as funções puras não leem o disco nem escrevem",
       not ({"read_text", "write_text", "open", "rglob", "gravar"} & nomes))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else f"✓ AUTOTESTE OK — {len(_casos_contados)} casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def main() -> int:
    if "--autoteste" in sys.argv[1:]:
        return _autoteste()
    fontes = {}
    for caminho in RAIZ.rglob("*.py"):
        rel = relativo(caminho)
        if rel.startswith((".git/", "node_modules/")):
            continue
        try:
            fontes[rel] = caminho.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
    divida = legados()
    if divida:
        do_juiz = [x for x in divida.values() if x.get("le_o_juiz")]
        print(f"⚠ dívida nomeada: {len(divida)} fonte(s) ainda escrevem a fila por fora da porta, "
              f"{len(do_juiz)} em fila que o juiz lê (config/escritores_legados.json):")
        for x in sorted(divida.values(), key=lambda y: (not y.get("le_o_juiz"), y["arquivo"])):
            marca = "juiz" if x.get("le_o_juiz") else "auxiliar"
            print(f"   - [{marca}] {x['arquivo']} → {x['fila']}; falta: {x['falta']}")
    p = problemas(fontes, divida)
    if p:
        print(f"✗ ESCRITOR DE PISTA: {len(p)} escrita(s) na fila fora de scripts/pistas.py:")
        for x in p:
            print("   - " + x)
        print("   A fila tem UMA porta. Entrada de pista nova vai por scripts/pistas.gravar() ou")
        print("   gravar_lote(); operação sobre a fila inteira declara-se em MANUTENCAO, ali.")
        return 1
    print(f"✓ ESCRITOR DE PISTA OK — {len(fontes)} fonte(s) conferido(s); só scripts/pistas.py "
          f"e a manutenção declarada abrem a fila para escrita.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
