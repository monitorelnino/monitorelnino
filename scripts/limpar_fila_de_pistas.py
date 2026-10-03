#!/usr/bin/env python3
"""Limpeza única da fila de pistas (item C.1 do handover da corrente noturna, 03/10/2026).

O RETRATO QUE A CENTRAL MEDIU em 03/10/2026, e que este script atende:

    8.681 pistas em `pistas_imprensa.json`
    6.456 "pendente de confirmação de documento", 96% em nível C
    6.455 URLs são REDIRECIONAMENTO do Google News, não o endereço do veículo
    2.549 URLs repetidas
    4.455 pendentes são sobre RESPOSTA (decretos), que não pontuam e já vêm de fonte oficial
      756 "exige documento primário lido por humano"
      746 de rede social

O que a limpeza faz, e o que ela deliberadamente NÃO faz:

**Artigo genérico distribuído por muitos municípios.** O mesmo identificador de artigo aparece
atribuído a vários municípios — "El Niño coloca municípios em alerta e Prefeitura de Vitória…"
está em Camaçari/BA e em Juazeiro/BA ao mesmo tempo. A pista não nasceu porque a notícia é
daquela cidade: nasceu porque a busca rodou o nome da cidade. Acima do teto de municípios, o
artigo é notícia genérica e as pistas dele fecham com esse motivo. É o mesmo defeito de
atribuição que o garimpo de 03/10 achou nos documentos oficiais, em outra fonte.

**Pista de decreto não ocupa a fila de planos.** Decreto é resposta, não pontua no índice e já
vem de fonte oficial (defesa civil nacional, diários). Se o município já consta da base oficial
de decretos, a pista fecha como "coberta pela fonte oficial"; se não consta, vira pista de
decreto para a coleta oficial — e sai da fila de planos nos dois casos.

**Prazo de vida.** Duas tentativas de busca dirigida sem documento, ou 21 dias na fila, fecham a
pista como "sem documento oficial localizado". Ela reabre sozinha se surgir evidência nova para o
mesmo município e assunto — fechar não é apagar: o registro fica.

**Teto por município e assunto.** No máximo cinco pistas abertas; a sexta só entra se for de
nível superior. Aqui a limpeza fecha o excedente, mantendo as de nível mais alto e mais novas.

**O que NÃO faz:** resolver o redirecionamento do Google News. O identificador novo (`AU_yq…`) é
opaco e só se resolve seguindo o redirecionamento, o que é rede — e a decisão da editoria para
esta rodada é "só código agora". A resolução entra na triagem de cada rodada, que já tem rede; a
regra de entrada (URL final obrigatória) impede que novas pistas cheguem assim.

USO
    python3 scripts/limpar_fila_de_pistas.py --relatorio
    python3 scripts/limpar_fila_de_pistas.py --aplicar
    python3 scripts/limpar_fila_de_pistas.py --autoteste
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

FILA = "pistas_imprensa.json"
TETO_POR_MUNICIPIO = 5
DIAS_DE_VIDA = 21
TENTATIVAS_MAXIMAS = 2
# Acima disto, o mesmo artigo atribuído a N municípios é notícia genérica, e não notícia da cidade.
TETO_DE_MUNICIPIOS_POR_ARTIGO = 3
NIVEIS = {"A": 3, "B": 2, "C": 1}

FECHA_GENERICA = ("fechada — notícia genérica: o mesmo artigo foi atribuído a vários municípios "
                  "pela busca, e não trata de nenhum deles em particular")
FECHA_COBERTA = ("fechada — coberta pela fonte oficial: o decreto do município já consta da base "
                 "oficial de resposta")
VIRA_DECRETO = ("pista de decreto — vai para a conferência da base oficial de resposta; não ocupa "
                "a fila de planos")
FECHA_PRAZO = ("fechada — sem documento oficial localizado no prazo da fila; reabre se surgir "
               "evidência nova para o mesmo município e assunto")
FECHA_SEM_ALVO = ("fechada — sem município nem UF identificável na pista: a regra de entrada "
                  "passa a descartar; reabre se a busca dirigida achar o alvo")
# 6.462 das 8.678 pistas abertas não têm município nem UF — nasceram de busca por termo, sem
# alvo. Sem município elas cairiam todas no MESMO balde do teto, e o teto fecharia 6.457
# por uma razão que não é a verdadeira. O motivo próprio diz o que de fato falta.
FECHA_TETO = ("fechada — acima do teto de pistas abertas para o município e o assunto; as de "
              "nível mais alto e mais recentes seguem na fila")


def identificador_do_artigo(url: str) -> str:
    """O identificador do artigo no redirecionador, ou a própria URL. Função pura.

    Duas pistas com o mesmo identificador são a mesma notícia, ainda que o endereço final seja
    desconhecido — e é por isso que a deduplicação funciona sem resolver o redirecionamento.
    """
    u = str(url or "")
    m = re.search(r"news\.google\.com/rss/articles/([^?/]+)", u)
    if m:
        return "gnews:" + m.group(1)
    return u.split("?")[0].rstrip("/")


def e_de_resposta(pista: dict) -> bool:
    """A pista é sobre decreto de emergência (resposta), e não sobre plano? Função pura."""
    campos = " ".join(str(pista.get(k) or "") for k in ("titulo", "trecho", "objeto", "assunto"))
    baixo = campos.lower()
    # Busca por PREFIXO: "plano de conting" não fecha em `\b`, que exige fronteira de palavra no
    # fim. E quando as duas coisas aparecem, vence o PLANO — "com plano de contingência aprovado, a
    # cidade decreta emergência" é notícia de plano com um decreto ao lado, e a fila de planos é
    # onde ela tem de ficar. Preferência declarada, não ordem no texto.
    # E quando os DOIS aparecem, vence o PLANO: "com plano de contingencia aprovado, a cidade
    # decreta emergencia" e noticia de plano com um decreto ao lado, e a fila de planos e onde
    # ela tem de ficar. Preferencia declarada, nao ordem no texto.
    if re.search(r"plano\s+de\s+conting|plancon|plamcon|plano\s+(?:municipal|estadual)", baixo):
        return False
    return bool(re.search(r"\b(decret(?:a|ou|o|os)\s|situa[çc][ãa]o de emerg[êe]ncia|"
                          r"calamidade p[úu]blica|reconhec(?:e|imento) (?:federal|de emerg)|"
                          r"homologa[çc][ãa]o)\b", baixo))


def chave_de_teto(pista: dict) -> tuple:
    """(município, assunto) para o teto por município. Função pura."""
    mun = str(pista.get("ibge") or pista.get("municipio") or "").strip().lower()
    assunto = "resposta" if e_de_resposta(pista) else "plano"
    return mun, assunto


def peso_da_pista(pista: dict) -> tuple:
    """Ordem de permanência no teto: nível, depois data. Função pura (maior fica)."""
    nivel = NIVEIS.get(str(pista.get("nivel_confianca") or "C").upper(), 1)
    return nivel, str(pista.get("registrado_em") or pista.get("data") or "")


def dias_na_fila(pista: dict, hoje_iso: str):
    """Dias desde o registro. Função pura; None sem data legível."""
    bruto = str(pista.get("registrado_em") or "")[:10]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            d = dt.datetime.strptime(bruto, fmt).date()
            break
        except ValueError:
            d = None
    if d is None:
        return None
    return (dt.date.fromisoformat(hoje_iso) - d).days


def aberta(pista: dict) -> bool:
    """A pista ainda ocupa a fila? Função pura."""
    status = str(pista.get("status") or "")
    return not status.startswith(("fechada", "aplicada", "rejeitada", "pista de decreto"))


def decidir(pistas: list, decretados: set, hoje_iso: str) -> list:
    """(pista, novo_status, motivo_curto) para cada pista que muda. FUNÇÃO PURA.

    A ordem das regras é a da decisão: artigo genérico primeiro (ele infla tudo), depois resposta,
    depois prazo de vida, depois teto. Uma pista fecha por um motivo só — o primeiro que se aplica,
    que é o que explica melhor por que ela não deveria estar ali.
    """
    por_artigo = {}
    for p in pistas:
        if not aberta(p):
            continue
        por_artigo.setdefault(identificador_do_artigo(p.get("url")), set()).add(
            str(p.get("ibge") or p.get("municipio") or ""))
    genericos = {k for k, v in por_artigo.items() if len(v) >= TETO_DE_MUNICIPIOS_POR_ARTIGO}

    mudancas = []
    abertas_por_chave = {}
    for p in pistas:
        if not aberta(p):
            continue
        ident = identificador_do_artigo(p.get("url"))
        if ident in genericos:
            mudancas.append((p, FECHA_GENERICA, "generica"))
            continue
        if e_de_resposta(p):
            mun = str(p.get("ibge") or "")
            if mun and mun in decretados:
                mudancas.append((p, FECHA_COBERTA, "coberta"))
            else:
                mudancas.append((p, VIRA_DECRETO, "decreto"))
            continue
        if not str(p.get("ibge") or p.get("municipio") or "").strip():
            mudancas.append((p, FECHA_SEM_ALVO, "sem_alvo"))
            continue
        d = dias_na_fila(p, hoje_iso)
        tentativas = int(p.get("tentativas_de_busca_dirigida") or 0)
        if (d is not None and d > DIAS_DE_VIDA) or tentativas >= TENTATIVAS_MAXIMAS:
            mudancas.append((p, FECHA_PRAZO, "prazo"))
            continue
        abertas_por_chave.setdefault(chave_de_teto(p), []).append(p)

    for chave, lista in abertas_por_chave.items():
        if len(lista) <= TETO_POR_MUNICIPIO:
            continue
        ordenada = sorted(lista, key=peso_da_pista, reverse=True)
        for p in ordenada[TETO_POR_MUNICIPIO:]:
            mudancas.append((p, FECHA_TETO, "teto"))
    return mudancas


def _autoteste() -> int:
    falhas = []

    def ok(nome, cond):
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    ok("identificador do Google News sai do caminho do artigo",
       identificador_do_artigo("https://news.google.com/rss/articles/ABC123?oc=5") == "gnews:ABC123")
    ok("mesmo artigo, parâmetros diferentes, mesmo identificador",
       identificador_do_artigo("https://news.google.com/rss/articles/X?a=1")
       == identificador_do_artigo("https://news.google.com/rss/articles/X?b=2"))
    ok("URL comum é o próprio endereço, sem barra final",
       identificador_do_artigo("https://x.gov.br/a/") == "https://x.gov.br/a")

    plano = {"titulo": "Prefeitura publica Plano de Contingência para o El Niño"}
    decreto = {"titulo": "Município decreta situação de emergência por estiagem"}
    ok("pista de plano não é de resposta", not e_de_resposta(plano))
    ok("pista de decreto é de resposta", e_de_resposta(decreto))
    ok("o plano vence o decreto quando os dois aparecem",
       not e_de_resposta({"titulo": "Com plano de contingência aprovado, cidade decreta emergência"}))

    ok("dias na fila em ISO", dias_na_fila({"registrado_em": "2026-09-01"}, "2026-10-03") == 32)
    ok("dias na fila em data brasileira",
       dias_na_fila({"registrado_em": "01/09/2026"}, "2026-10-03") == 32)
    ok("sem data, sem dias", dias_na_fila({}, "2026-10-03") is None)
    ok("pista fechada não está aberta", not aberta({"status": "fechada — x"}))
    ok("pista de decreto não está aberta", not aberta({"status": "pista de decreto — y"}))
    ok("pista pendente está aberta", aberta({"status": "pista — pendente"}))

    # artigo genérico: o mesmo id em três municípios
    generico = [{"url": "https://news.google.com/rss/articles/G1", "ibge": str(i),
                 "status": "pista", "registrado_em": "2026-10-02",
                 "titulo": "El Niño coloca municípios em alerta"} for i in (1, 2, 3)]
    m = decidir(generico, set(), "2026-10-03")
    ok("artigo em três municípios fecha as três pistas como genérica",
       len(m) == 3 and all(x[2] == "generica" for x in m))
    dois = generico[:2]
    ok("o mesmo artigo em dois municípios NÃO fecha por genérica",
       all(x[2] != "generica" for x in decidir(dois, set(), "2026-10-03")))

    # resposta
    resp = [{"url": "https://u/1", "ibge": "3550308", "status": "pista",
             "registrado_em": "2026-10-02", "titulo": "Cidade decreta emergência"}]
    ok("decreto já registrado fecha como coberta pela fonte oficial",
       decidir(resp, {"3550308"}, "2026-10-03")[0][2] == "coberta")
    ok("decreto não registrado vira pista de decreto",
       decidir(resp, set(), "2026-10-03")[0][2] == "decreto")
    ok("pista de decreto sai da fila de planos",
       decidir(resp, set(), "2026-10-03")[0][1].startswith("pista de decreto"))

    # prazo de vida
    velha = [{"url": "https://u/2", "ibge": "1", "status": "pista",
              "registrado_em": "2026-09-01", "titulo": "Plano de contingência publicado"}]
    ok("pista de 32 dias fecha pelo prazo", decidir(velha, set(), "2026-10-03")[0][2] == "prazo")
    tentou = [dict(velha[0], registrado_em="2026-10-02", tentativas_de_busca_dirigida=2)]
    ok("duas tentativas sem documento fecham",
       decidir(tentou, set(), "2026-10-03")[0][2] == "prazo")
    nova = [dict(velha[0], registrado_em="2026-10-02")]
    ok("pista nova e sem tentativa fica na fila", decidir(nova, set(), "2026-10-03") == [])
    sem_alvo = [{"url": "https://u/3", "status": "pista", "registrado_em": "2026-10-02",
                 "titulo": "Bahia articula plano contra o El Nino"}]
    ok("pista sem município fecha com o motivo dela, e não pelo teto",
       decidir(sem_alvo, set(), "2026-10-03")[0][2] == "sem_alvo")

    # teto por município
    seis = [{"url": f"https://u/{i}", "ibge": "9", "status": "pista",
             "registrado_em": "2026-10-02", "nivel_confianca": "C",
             "titulo": "Plano de contingência"} for i in range(6)]
    m = decidir(seis, set(), "2026-10-03")
    ok("a sexta pista do mesmo município fecha pelo teto",
       len(m) == 1 and m[0][2] == "teto")
    com_a = seis[:5] + [dict(seis[5], nivel_confianca="A")]
    fechadas = [x for x in decidir(com_a, set(), "2026-10-03")]
    ok("o teto mantém a de nível mais alto",
       len(fechadas) == 1 and fechadas[0][0].get("nivel_confianca") == "C")
    ok("cinco pistas do mesmo município não disparam o teto",
       decidir(seis[:5], set(), "2026-10-03") == [])
    ok("pista já fechada não é julgada de novo",
       decidir([{"url": "https://u/x", "status": "fechada — já"}], set(), "2026-10-03") == [])

    import dis
    nomes = set()
    for nome_obj, obj in list(globals().items()):
        if nome_obj in ("_autoteste", "main"):
            continue
        codigo = getattr(obj, "__code__", None)
        if codigo is not None:
            nomes |= {i.argval for i in dis.get_instructions(codigo) if isinstance(i.argval, str)}
    ok("trava estrutural: as funções puras não escrevem",
       not ({"gravar", "gravar_em", "write_text", "write_bytes"} & nomes))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else "✓ AUTOTESTE OK — 25 casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return _autoteste()
    aplicar = "--aplicar" in sys.argv
    from coletores_base import DATA, gravar, ler, hoje_editorial

    doc = ler(FILA) or {}
    pistas = doc.get("pistas") or []
    decretados = set((ler("resposta/municipios_decretados.json") or {}).get("municipios") or {})
    hoje = hoje_editorial().isoformat()

    mudancas = decidir(pistas, decretados, hoje)
    por_motivo = {}
    for _p, _status, motivo in mudancas:
        por_motivo[motivo] = por_motivo.get(motivo, 0) + 1

    abertas_antes = sum(1 for p in pistas if aberta(p))
    print(f"fila: {len(pistas)} pista(s), {abertas_antes} aberta(s)")
    for motivo, n in sorted(por_motivo.items(), key=lambda x: -x[1]):
        print(f"   {motivo:10s} {n}")
    print(f"   total a mudar: {len(mudancas)} · ficam abertas: {abertas_antes - len(mudancas)}")

    if not aplicar:
        print("\nrelatório apenas; nada escrito (use --aplicar)")
        return 0

    for p, status, motivo in mudancas:
        p["status_anterior"] = p.get("status")
        p["status"] = status
        p["limpeza"] = {"em": hoje, "motivo": motivo, "regra": "C.1 do handover de 03/10/2026"}
    gravar(FILA, doc)
    print(f"\n{len(mudancas)} pista(s) atualizada(s) em data/{FILA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
