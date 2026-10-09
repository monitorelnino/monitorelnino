#!/usr/bin/env python3
"""Portão do esquema da pista, e da saúde da fila (item C.3 do handover de 03/10/2026).

POR QUE ELE EXISTE. A fila de pistas chegou a **8.681** itens, e o retrato que a central mediu em
03/10/2026 diz o que estava errado — não na saída, na ENTRADA:

    6.462 sem município nem UF identificável   (busca por termo, sem alvo)
    6.455 em redirecionamento do Google News   (não o endereço do veículo)
    2.549 URLs repetidas
    4.455 sobre decreto (resposta), que não pontua e já vem de fonte oficial

Filtrar na saída não dá conta: a cada rodada entra mais do mesmo. Então a regra passa a valer na
gravação — `coletores_base.gravar_pista` recusa pista fora do esquema — e este portão confere duas
coisas:

  (a) **esquema**: as pistas ABERTAS da fila trazem os campos obrigatórios de `schemas/pista.json`;
  (b) **saúde da fila**: alerta quando ela cresce três rodadas seguidas, quando a idade mediana
      passa de 14 dias, ou quando a fração de nível C passa de 70%.

A alínea (a) é medida só nas pistas abertas DEPOIS da data em que a regra passou a valer: exigir o
esquema de quem entrou antes dele produziria 8 mil vermelhos que ninguém pode apagar, e vermelho
que não se apaga deixa de ser sinal. As antigas são tratadas pela limpeza e pela triagem.

USO
    python3 scripts/verificar_esquema_de_pista.py
    python3 scripts/verificar_esquema_de_pista.py --autoteste
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import re
import statistics
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

ESQUEMA = RAIZ / "schemas" / "pista.json"
FILAS = ("pistas_imprensa.json", "pistas_descobertas.json", "pistas_doe.json")
# A regra do esquema passou a valer nesta data (handover da corrente noturna).
VALE_A_PARTIR_DE = "2026-10-04"
# A FORMA tem data propria, e por uma razao medida. Quando o portao passou a conferir forma em
# todas as pistas (A7-08), a CI acusou 988 pistas REGISTRADAS DEPOIS DE 04/10 com alvo vazio — o
# passivo nao esta so no que e antigo, porque parte dele entrou pelas escritas que fugiam da porta
# (A7-19, as 18 do `config/escritores_legados.json`). Bloquear hoje seria reprovar a `main` por
# divida que ja existia, e parar a noite por isso e desproporcional: o lugar de fechar a entrada e
# a porta, nao o portao. Entao a forma vale a partir de AMANHA — a pista que entrar sob a porta
# corrigida reprova; o que ja esta la e contado, nomeado e cobravel.
FORMA_VALE_A_PARTIR_DE = "2026-10-10"
IDADE_MEDIANA_MAXIMA = 14
FRACAO_C_MAXIMA = 0.70
RODADAS_DE_CRESCIMENTO = 3


def ler_esquema(caminho=ESQUEMA) -> dict:
    try:
        return json.loads(pathlib.Path(caminho).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


# 04/10/2026 — O QUE BLOQUEIA E O QUE AVISA.
#
# Medido pela central: a publicação da noite de 03→04 falhou duas vezes por 10 pistas fora do
# esquema, e **nenhum dado novo foi ao ar**. O portão acusou o certo — pista malformada não pode
# entrar —, mas parar o site inteiro por dez sobras de Diário Oficial é desproporcional, e a
# editoria mandou rebaixar.
#
# A linha nova é esta: pista que está na FILA ATIVA (vai ao juiz, pode virar registro) e está fora do
# esquema **bloqueia**; pista já tirada da fila — em quarentena, ou com `destino` declarado para
# outro lugar, como a conferência da base de resposta — **avisa**. A diferença é de consequência: a
# primeira pode entrar no índice errada, a segunda já não vai a lugar nenhum sem alguém olhar.
DESTINOS_FORA_DA_FILA = ("conferencia_resposta", "quarentena", "rejeitada")

# 05/10/2026 — O PORTÃO QUARENTENA; ELE NÃO BLOQUEIA MAIS A PUBLICAÇÃO.
#
# Medido na noite de 04→05/10: a publicação reprovou OITO vezes entre 21:23 e 03:57 BRT, e o site
# ficou com dado de 04/10. A causa foram 655 pistas novas sem `url_final`, `tipo`, `alvo` nem
# `nivel`, de coletores que nunca foram migrados para o esquema de 03/10 (654 de
# `rede_social_oficial`). O portão acusou o certo — pista malformada não pode ir ao juiz —, mas a
# consequência era desproporcional: seiscentas sobras de coletor paravam o site inteiro.
#
# A regra passa a ser esta: **pista fora do esquema sai da fila ativa, e a publicação segue**. Quem
# a tira é `quarentenar()`, aqui, e ela fica contável por origem no painel. Bloqueio só quando a
# quarentena FALHA — aí sim o dado malformado continuaria na fila ativa, a caminho do juiz, e
# publicar seria publicar o errado.
#
# A porta de entrada é consertada em outro lugar, e é lá que ela tem de ser consertada:
# `scripts/pistas.py` é o único escritor da fila, e `scripts/verificar_escritor_de_pista.py`
# reprova no PR quem abrir o arquivo por fora. Este portão é a rede de segurança, não a regra.
MOTIVO_DA_QUARENTENA = "fora do esquema de schemas/pista.json"


def fora_da_fila_ativa(pista: dict) -> bool:
    """A pista já foi tirada da fila ativa, e portanto não pode virar registro? Função pura."""
    p = pista or {}
    if p.get("quarentena") or p.get("rejeitada"):
        return True
    return str(p.get("destino") or "") in DESTINOS_FORA_DA_FILA


def problemas_de_esquema(pistas: list, esquema: dict, vale_a_partir_de=VALE_A_PARTIR_DE,
                         so_fila_ativa: bool = False) -> list:
    """As pistas novas que não cumprem o esquema. Função pura.

    Com `so_fila_ativa=True`, ignora o que já saiu da fila: é a lista que BLOQUEIA. Sem o
    parâmetro, devolve tudo — é a lista que vira aviso no painel.
    """
    obrigatorios = list((esquema.get("obrigatorios") or {}).keys())
    tipos = set(esquema.get("tipos_validos") or [])
    niveis = set(esquema.get("niveis_validos") or [])
    origens = set(esquema.get("origens_validas") or [])
    ruins = []
    for p in pistas or []:
        # Só `registrado_em`: é a data em que a pista ENTROU na fila. `data` é a data do item na
        # fonte (a notícia pode ser de ontem ou de amanhã), e usá-la cobrava o esquema de pistas
        # antigas cuja notícia tinha data recente — vermelho em quem a regra não alcança.
        registrado = str(p.get("registrado_em") or "")[:10]
        if not registrado or registrado < vale_a_partir_de:
            continue
        if so_fila_ativa and fora_da_fila_ativa(p):
            continue
        ident = str(p.get("id") or p.get("url_final") or p.get("url") or "?")[:12]
        faltam = [c for c in obrigatorios if not p.get(c)]
        if faltam:
            ruins.append(f"{ident}: sem {', '.join(faltam)}")
            continue
        if tipos and p.get("tipo") not in tipos:
            ruins.append(f"{ident}: tipo {p.get('tipo')!r} fora de {sorted(tipos)}")
        if niveis and str(p.get("nivel") or "").upper() not in niveis:
            ruins.append(f"{ident}: nível {p.get('nivel')!r} fora de {sorted(niveis)}")
        if origens and p.get("origem") not in origens:
            ruins.append(f"{ident}: origem {p.get('origem')!r} fora de {sorted(origens)}")
        if "news.google.com" in str(p.get("url_final") or ""):
            ruins.append(f"{ident}: url_final é redirecionamento, não o endereço do veículo")
        if p.get("tipo") == "decreto":
            ruins.append(f"{ident}: pista de decreto na fila de planos — vai para a base oficial")
    return ruins


RE_DATA_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
RE_DATA_BR = re.compile(r"^\d{2}/\d{2}/\d{4}$")


def _e_nova(pista: dict, vale_a_partir_de=VALE_A_PARTIR_DE) -> bool:
    """A pista entrou na fila depois de a regra valer? Lê as duas grafias de `registrado_em`.

    09/10/2026: as pistas antigas gravam `registrado_em` em dd/mm/aaaa, e a comparação de texto
    com AAAA-MM-DD acertava por acidente (toda data br é menor que "2026-"). Ler as duas grafias
    torna o critério explícito — e mostrou que o portão cobria 1.064 das 13.406 pistas, não 4.
    """
    v = str(pista.get("registrado_em") or "").strip()
    m = RE_DATA_BR.match(v)
    iso = f"{m.group(0)[6:10]}-{m.group(0)[3:5]}-{m.group(0)[0:2]}" if m else v[:10]
    return bool(iso) and iso >= vale_a_partir_de


def problemas_de_forma(pistas: list) -> list:
    """Defeitos de FORMA em qualquer pista, nova ou antiga. Função pura.

    09/10/2026 (A7-08). O portão só olhava pista com `registrado_em` a partir de 04/10 — 1.064 das
    13.406 da fila, medido. O corte existe por uma razão boa: EXIGIR campo novo de pista antiga
    reprovaria quem a regra não alcança. Mas forma de campo que a pista JÁ TEM não é exigência
    nova, e nada a conferia: 13.330 pistas sem `url_final` (as antigas guardam o endereço em
    `url`), 3.354 com `alvo` vazio, 3.177 com `data` fora de AAAA-MM-DD.

    Por isso dois regimes, e não um corte: forma se confere em todas, e o que reprova é a pista
    NOVA (ali o bloqueio é devido); na antiga, o defeito é contado e nomeado por fila, como alerta
    de saúde — visível, sem parar a noite por um passivo que já existia.
    """
    ruins = []
    for p in pistas or []:
        ident = str(p.get("id") or p.get("url_final") or p.get("url") or "?")[:12]
        endereco = str(p.get("url_final") or p.get("url") or "")
        if not endereco.startswith(("http://", "https://")):
            ruins.append(f"{ident}: sem endereço http em url_final nem em url")
        if not str(p.get("alvo") or "").strip():
            ruins.append(f"{ident}: alvo vazio — a pista não diz de quem é")
        for campo in ("data", "registrado_em"):
            v = str(p.get(campo) or "").strip()
            if v and not (RE_DATA_ISO.match(v) or RE_DATA_BR.match(v)):
                ruins.append(f"{ident}: {campo} {v!r} não é AAAA-MM-DD nem dd/mm/aaaa")
    return ruins


def quarentenar(pistas: list, esquema: dict, vale_a_partir_de=VALE_A_PARTIR_DE,
                hoje_iso: str = "") -> tuple:
    """(pistas, movidas) — tira da fila ativa o que está fora do esquema. FUNÇÃO PURA.

    Devolve uma lista NOVA; nada do original se perde. A pista movida ganha `quarentena: True`,
    `destino: "quarentena"`, o motivo e o campo que faltou — ela continua no arquivo, contável e
    legível, e `fora_da_fila_ativa()` passa a dizer que ela não vai ao juiz.

    `movidas` é {origem_do_coletor: contagem}, que é o que o painel precisa: "quem está gravando
    errado" responde-se por coletor, não por pista.
    """
    obrigatorios = list((esquema.get("obrigatorios") or {}).keys())
    ruins = {x.split(":", 1)[0] for x in problemas_de_esquema(pistas, esquema, vale_a_partir_de,
                                                              so_fila_ativa=True)}
    fora = []
    movidas = {}
    for p in pistas or []:
        ident = str(p.get("id") or p.get("url_final") or p.get("url") or "?")[:12]
        registrado = str(p.get("registrado_em") or "")[:10]
        alcancada = bool(registrado) and registrado >= vale_a_partir_de
        if not alcancada or fora_da_fila_ativa(p) or ident not in ruins:
            fora.append(p)
            continue
        faltam = [c for c in obrigatorios if not p.get(c)]
        nova_pista = dict(p)
        nova_pista["quarentena"] = True
        nova_pista["destino"] = "quarentena"
        nova_pista["motivo_da_quarentena"] = (
            MOTIVO_DA_QUARENTENA + (f": sem {', '.join(faltam)}" if faltam else ""))
        if hoje_iso:
            nova_pista["quarentenada_em"] = hoje_iso
        chave = str(p.get("origem_do_coletor") or p.get("origem") or "?")
        movidas[chave] = movidas.get(chave, 0) + 1
        fora.append(nova_pista)
    return fora, movidas


def saude_da_fila(pistas: list, historico: list, hoje_iso: str) -> dict:
    """{tamanho, idade_mediana, fracao_c, crescendo, alertas}. Função pura."""
    import sys as _s
    _s.path.insert(0, str(RAIZ / "scripts"))
    from limpar_fila_de_pistas import aberta
    abertas = [p for p in (pistas or []) if aberta(p)]
    idades = []
    for p in abertas:
        bruto = str(p.get("registrado_em") or "")[:10]
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                d = dt.datetime.strptime(bruto, fmt).date()
                idades.append((dt.date.fromisoformat(hoje_iso) - d).days)
                break
            except ValueError:
                continue
    niveis_c = sum(1 for p in abertas
                   if str(p.get("nivel") or p.get("nivel_confianca") or "").upper() == "C")
    tamanhos = [h.get("tamanho") for h in (historico or []) if isinstance(h.get("tamanho"), int)]
    crescendo = (len(tamanhos) >= RODADAS_DE_CRESCIMENTO
                 and all(tamanhos[-i] > tamanhos[-i - 1]
                         for i in range(1, RODADAS_DE_CRESCIMENTO)))
    fora = {
        "tamanho": len(abertas),
        "idade_mediana": round(statistics.median(idades), 1) if idades else None,
        "fracao_c": round(niveis_c / len(abertas), 2) if abertas else 0.0,
        "crescendo": bool(crescendo),
        "alertas": [],
    }
    if fora["idade_mediana"] is not None and fora["idade_mediana"] > IDADE_MEDIANA_MAXIMA:
        fora["alertas"].append(f"idade mediana de {fora['idade_mediana']} dias "
                               f"(limite {IDADE_MEDIANA_MAXIMA})")
    if fora["fracao_c"] > FRACAO_C_MAXIMA:
        fora["alertas"].append(f"{fora['fracao_c']:.0%} das pistas abertas em nível C "
                               f"(limite {FRACAO_C_MAXIMA:.0%})")
    if crescendo:
        fora["alertas"].append(f"a fila cresceu {RODADAS_DE_CRESCIMENTO} rodadas seguidas")
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

    esquema = ler_esquema()
    ok("o esquema existe e declara os obrigatórios",
       set(esquema.get("obrigatorios") or {}) >= {"url_final", "tipo", "alvo", "nivel", "data", "origem"})
    ok("o esquema declara o teto por município",
       (esquema.get("regras") or {}).get("teto_por_municipio_e_assunto") == 5)

    boa = {"id": "n1", "url_final": "https://x.com.br/a", "tipo": "plano", "alvo": "4217808",
           "nivel": "A", "data": "2026-10-05", "origem": "busca_web",
           "registrado_em": "2026-10-05"}
    ok("pista completa passa", problemas_de_esquema([boa], esquema) == [])
    ok("pista antiga não é cobrada",
       problemas_de_esquema([dict(boa, registrado_em="2026-09-01", tipo=None)], esquema) == [])
    ok("pista sem registrado_em não é cobrada, mesmo com data recente",
       problemas_de_esquema([{"id": "x", "data": "2026-10-09"}], esquema) == [])
    ok("falta de alvo reprova",
       any("alvo" in x for x in problemas_de_esquema([dict(boa, alvo=None)], esquema)))
    ok("falta de url_final reprova",
       any("url_final" in x for x in problemas_de_esquema([dict(boa, url_final=None)], esquema)))
    ok("tipo inválido reprova",
       any("tipo" in x for x in problemas_de_esquema([dict(boa, tipo="qualquer")], esquema)))
    ok("nível inválido reprova",
       any("nível" in x for x in problemas_de_esquema([dict(boa, nivel="Z")], esquema)))
    ok("origem inválida reprova",
       any("origem" in x for x in problemas_de_esquema([dict(boa, origem="telepatia")], esquema)))
    ok("redirecionamento na url_final reprova",
       any("redirecionamento" in x for x in problemas_de_esquema(
           [dict(boa, url_final="https://news.google.com/rss/articles/X")], esquema)))
    ok("pista de decreto na fila de planos reprova",
       any("base oficial" in x for x in problemas_de_esquema([dict(boa, tipo="decreto")], esquema)))

    abertas = [{"status": "pista", "registrado_em": "2026-09-20", "nivel": "C"},
               {"status": "pista", "registrado_em": "2026-10-01", "nivel": "A"},
               {"status": "fechada — x", "registrado_em": "2026-01-01", "nivel": "C"}]
    s = saude_da_fila(abertas, [], "2026-10-03")
    ok("a saúde conta só as pistas abertas", s["tamanho"] == 2)
    ok("a idade mediana sai das datas", s["idade_mediana"] == 7.5)
    ok("a fração de nível C é das abertas", s["fracao_c"] == 0.5)
    velhas = [{"status": "pista", "registrado_em": "2026-09-01", "nivel": "C"}] * 3
    ok("idade mediana acima do limite alerta",
       any("idade mediana" in a for a in saude_da_fila(velhas, [], "2026-10-03")["alertas"]))
    ok("fração de C acima do limite alerta",
       any("nível C" in a for a in saude_da_fila(velhas, [], "2026-10-03")["alertas"]))
    ok("três rodadas de crescimento alertam",
       any("rodadas seguidas" in a for a in
           saude_da_fila(abertas, [{"tamanho": 1}, {"tamanho": 2}, {"tamanho": 3}], "2026-10-03")["alertas"]))
    ok("fila estável não alerta por crescimento",
       not any("rodadas seguidas" in a for a in
               saude_da_fila(abertas, [{"tamanho": 3}, {"tamanho": 2}, {"tamanho": 1}], "2026-10-03")["alertas"]))
    ok("fila vazia não quebra", saude_da_fila([], [], "2026-10-03")["tamanho"] == 0)

    # ---- a quarentena (05/10/2026) ----
    ruim = {"id": "r1", "registrado_em": "2026-10-05", "origem_do_coletor": "rede_social_oficial",
            "url": "https://x.ms.gov.br/a"}
    nova, movidas = quarentenar([boa, ruim], esquema, hoje_iso="2026-10-05")
    ok("a quarentena tira da fila ativa só o que está fora do esquema",
       problemas_de_esquema(nova, esquema, so_fila_ativa=True) == [])
    ok("a quarentena não perde pista: as duas continuam no arquivo", len(nova) == 2)
    ok("a pista boa passa intacta pela quarentena", nova[0] == boa)
    ok("a pista movida fica marcada", nova[1]["quarentena"] is True
       and nova[1]["destino"] == "quarentena")
    ok("o motivo nomeia o campo que faltou", "url_final" in nova[1]["motivo_da_quarentena"])
    ok("a data da quarentena fica registrada", nova[1]["quarentenada_em"] == "2026-10-05")
    ok("a contagem é por coletor, que é quem grava errado",
       movidas == {"rede_social_oficial": 1})
    ok("pista antiga não é quarentenada — a regra não a alcança",
       quarentenar([dict(ruim, registrado_em="2026-09-01")], esquema)[1] == {})
    ok("pista já fora da fila ativa não é quarentenada de novo",
       quarentenar([dict(ruim, quarentena=True)], esquema)[1] == {})
    ok("fila só de pistas boas não move nada", quarentenar([boa], esquema) == ([boa], {}))
    ok("fila vazia não quebra a quarentena", quarentenar([], esquema) == ([], {}))
    ok("a quarentena é idempotente: a segunda passada não move nada",
       quarentenar(nova, esquema)[1] == {})

    import dis
    nomes = set()
    for nome_obj, obj in list(globals().items()):
        # `main` escreve de propósito desde 05/10: é ela que aplica a quarentena. A trava passa a
        # valer para as funções PURAS, que é onde ela sempre importou — as que o resto do projeto
        # chama para decidir sem efeito colateral.
        if nome_obj in ("_autoteste", "main"):
            continue
        codigo = getattr(obj, "__code__", None)
        if codigo is not None:
            nomes |= {i.argval for i in dis.get_instructions(codigo) if isinstance(i.argval, str)}
    # 09/10/2026 (A7-08): forma de pista, e o critério de pista nova nas duas grafias de data.
    ok("endereço em `url` serve quando `url_final` não existe",
       problemas_de_forma([{"id": "a", "url": "https://x/1", "alvo": "Taió/SC",
                            "data": "2026-10-09"}]) == [])
    ok("sem endereço http nenhum reprova",
       any("endereço http" in m for m in problemas_de_forma([{"id": "b", "url": "None"}])))
    ok("alvo vazio reprova",
       any("alvo vazio" in m for m in problemas_de_forma(
           [{"id": "c", "url": "https://x/1", "alvo": "  "}])))
    ok("data ilegível reprova, e diz qual campo",
       any("data 'ontem'" in m for m in problemas_de_forma(
           [{"id": "d", "url": "https://x/1", "alvo": "Taió/SC", "data": "ontem"}])))
    ok("as duas grafias de data passam",
       problemas_de_forma([{"id": "e", "url": "https://x/1", "alvo": "T", "data": "09/10/2026",
                            "registrado_em": "2026-10-09"}]) == [])
    ok("pista registrada depois do corte é nova",
       _e_nova({"registrado_em": "2026-10-09"}) is True
       and _e_nova({"registrado_em": "09/10/2026"}) is True)
    ok("pista registrada antes do corte não é nova",
       _e_nova({"registrado_em": "02/09/2026"}) is False
       and _e_nova({"registrado_em": "2026-09-02"}) is False)
    ok("a forma tem data própria, e ela é posterior à do esquema",
       FORMA_VALE_A_PARTIR_DE > VALE_A_PARTIR_DE)
    ok("a data da forma decide o regime, não a do esquema",
       _e_nova({"registrado_em": "2026-10-05"}, FORMA_VALE_A_PARTIR_DE) is False
       and _e_nova({"registrado_em": "2026-10-05"}, VALE_A_PARTIR_DE) is True)
    ok("pista sem `registrado_em` não é nova (a regra não a alcança)",
       _e_nova({}) is False)
    ok("trava estrutural: as funções puras do portão não escrevem",
       not ({"gravar", "gravar_em", "write_text", "write_bytes"} & nomes))
    ok("trava estrutural: quarentenar devolve lista nova, não altera a de entrada",
       (lambda orig: (quarentenar(orig, esquema), orig == [dict(ruim)])[1])([dict(ruim)]))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else f"✓ AUTOTESTE OK — {len(_casos_contados)} casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return _autoteste()
    from coletores_base import ler, gravar, hoje_editorial
    esquema = ler_esquema()
    hoje = hoje_editorial().isoformat()
    so_conferir = "--sem-quarentenar" in sys.argv
    bloqueios, alertas, quarentenadas = [], [], {}

    for nome in FILAS:
        doc = ler(nome)
        if not doc:
            continue
        pistas = doc.get("pistas") or doc.get("itens") or []
        ativas = problemas_de_esquema(pistas, esquema, so_fila_ativa=True)

        if ativas and not so_conferir:
            # A QUARENTENA, e a prova de que ela funcionou. A escrita só acontece se a conferência
            # na lista nova vier limpa: gravar primeiro e conferir depois deixaria o arquivo pior
            # do que estava se a função tivesse defeito.
            novas, movidas = quarentenar(pistas, esquema, hoje_iso=hoje)
            if problemas_de_esquema(novas, esquema, so_fila_ativa=True):
                bloqueios.append(f"{nome}: a quarentena NÃO limpou a fila ativa — "
                                 f"{len(ativas)} pista(s) seguem a caminho do juiz")
                continue
            chave = "pistas" if doc.get("pistas") is not None else "itens"
            doc[chave] = novas
            doc["quarentena"] = {"em": hoje, "motivo": MOTIVO_DA_QUARENTENA, "por_origem": movidas}
            gravar(nome, doc)
            for origem, n in sorted(movidas.items()):
                quarentenadas[origem] = quarentenadas.get(origem, 0) + n
            pistas = novas
        elif ativas:
            bloqueios.append(f"{nome}: {len(ativas)} pista(s) nova(s) da fila ativa fora do "
                             f"esquema (--sem-quarentenar: nada foi movido)")

        # 09/10/2026 (A7-08): FORMA em todas as pistas, nos dois regimes. Nova reprova; antiga
        # conta e fica nomeada. A pista nova é a que `problemas_de_esquema` já alcança, e usar o
        # mesmo critério nos dois lugares evita um terceiro corte de data vivendo por aqui.
        forma_novas = problemas_de_forma(
            [x for x in pistas if _e_nova(x, FORMA_VALE_A_PARTIR_DE)])
        forma_antigas = problemas_de_forma(
            [x for x in pistas if not _e_nova(x, FORMA_VALE_A_PARTIR_DE)])
        if forma_novas and not so_conferir:
            bloqueios.append(f"{nome}: {len(forma_novas)} pista(s) nova(s) com defeito de forma "
                             f"(endereço, alvo ou data) — ex.: {forma_novas[0]}")
        if forma_antigas:
            alertas.append(f"{nome}: {len(forma_antigas)} defeito(s) de forma em pista anterior a "
                           f"{FORMA_VALE_A_PARTIR_DE} — não bloqueia; a porta e a migração de "
                           f"esquema os fecham")

        declaradas = [x for x in problemas_de_esquema(pistas, esquema)
                      if x not in problemas_de_esquema(pistas, esquema, so_fila_ativa=True)]
        if declaradas:
            alertas.append(f"{nome}: {len(declaradas)} pista(s) fora do esquema já tirada(s) da "
                           f"fila (conferência ou quarentena) — não bloqueia, mas fica visível")
        if nome == "pistas_imprensa.json":
            s_fila = saude_da_fila(pistas, (ler("saude_da_fila.json") or {}).get("rodadas") or [],
                                   hoje)
            print(f"fila de planos: {s_fila['tamanho']} aberta(s) · idade mediana "
                  f"{s_fila['idade_mediana']} dia(s) · nível C {s_fila['fracao_c']:.0%}")
            alertas += s_fila["alertas"]

    if quarentenadas:
        total = sum(quarentenadas.values())
        print(f"⚠ quarentena: {total} pista(s) fora do esquema saíram da fila ativa — "
              "a publicação SEGUE. Por coletor:")
        for origem, n in sorted(quarentenadas.items(), key=lambda kv: -kv[1]):
            print(f"   - {origem}: {n}")
        print("   Conserto da porta de entrada: scripts/pistas.py é o único escritor da fila.")
    for a in alertas:
        print(f"⚠ saúde da fila: {a}")
    if bloqueios:
        print(f"✗ ESQUEMA DA PISTA: {len(bloqueios)} fila(s) que a quarentena não resolveu:")
        for b in bloqueios:
            print("   - " + b)
        return 1
    print("✓ ESQUEMA DA PISTA OK — nenhuma pista fora de schemas/pista.json na fila ativa"
          + (f"; {sum(quarentenadas.values())} quarentenada(s)" if quarentenadas else "")
          + (f"; {len(alertas)} alerta(s) de saúde da fila" if alertas else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
