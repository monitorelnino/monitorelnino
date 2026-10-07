#!/usr/bin/env python3
"""
scripts/pistas.py — o ÚNICO ponto de entrada da fila de pistas
==============================================================
Item 1 do `HANDOVER_noite_confiavel_05-10-2026.md`.

O QUE ACONTECEU, E POR QUE ESTE MÓDULO EXISTE
---------------------------------------------
Em 03/10/2026 o esquema da pista passou a valer (`schemas/pista.json`): `url_final`, `tipo`,
`alvo`, `nivel`, `data` e `origem` obrigatórios. `coletores_base.gravar_pista` passou a recusar o
que não cumprisse. Só que **a maioria dos coletores nunca foi migrada para ela** — eles montam o
dicionário e chamam `gravar("pistas_imprensa.json", doc)` direto, por fora de qualquer validação.

O resultado, medido na noite de 04→05/10: **655 pistas novas** sem `url_final`, `tipo`, `alvo` nem
`nivel` (654 de `rede_social_oficial`, 1 de `busca_web`), e a publicação reprovada **oito vezes**
entre 21:23 e 03:57 BRT. O site ficou com dado de 04/10 porque dez — depois seiscentas — sobras de
coletor não migrado paravam o site inteiro.

A causa não é o portão: é haver mais de uma porta. Enquanto cada coletor escreve o arquivo
consolidado por conta própria, a validação é opcional por construção, e "migrar todos" é um estado
que se perde no próximo coletor novo. Então a porta passa a ser uma só, e um portão de PR reprova
quem abrir o arquivo por fora (`scripts/verificar_escritor_de_pista.py`).

O QUE ESTE MÓDULO FAZ
---------------------
`gravar(pista, origem)` recebe o dicionário **como o coletor o monta hoje** — com `url`, `ibge`,
`nivel_confianca`, data em dd/mm/aaaa — e faz, em ordem:

  1. **normaliza** para o esquema: `url_final` (resolvendo o redirecionador), `alvo` (IBGE ou UF),
     `nivel` (de `nivel_confianca`), `data` em AAAA-MM-DD, `origem` canônica;
  2. **classifica `tipo`** pelos sinais do título e do trecho: plano · estrutura · decreto · outro;
  3. **valida** por `coletores_base.validar_pista` — que já traz a deduplicação (url_final + alvo +
     tipo), o teto por município e a regra de que decreto não entra na fila de planos;
  4. **recusa com motivo**, gravando em `data/pistas_rejeitadas.json` a pista, a origem e o campo
     ausente. Recusa registrada é lacuna declarada; recusa silenciosa é dado perdido.

A normalização é **função pura** (`normalizar`), e é por ela que o teste de fixtures passa. A
escrita vive só em `gravar` e em `rejeitar`.

USO
    from scripts.pistas import gravar
    gravou, motivo = gravar(pista, origem="rede_social_oficial")

    python3 scripts/pistas.py --autoteste
"""
from __future__ import annotations

import datetime as dt
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

FILA_PADRAO = "pistas_imprensa.json"
ARQUIVO_DE_REJEITADAS = "pistas_rejeitadas.json"

# A origem que o coletor usa não é sempre a do esquema: `rede_social_oficial` é o nome do coletor,
# `rede_social` é o nome do canal em `schemas/pista.json`. Mapear aqui, num lugar, em vez de pedir
# que cada coletor saiba o nome canônico — pedir isso foi o que produziu as 654.
ORIGEM_CANONICA = {
    "rede_social_oficial": "rede_social",
    "seguimento_link_noticia": "imprensa",
    "seguimento_busca_oficial": "busca_web",
    "seguimento_querido_diario": "querido_diario",
    "imprensa_regional": "imprensa",
    "politica_por_inteiro": "descoberta",
    "diarios_municipais": "diario",
    "diarios_consorciados": "diario",
}

REDIRECIONADORES = ("news.google.com", "/rss/articles/", "news.url.google.com")

# Os sinais do `tipo`. A ordem importa: decreto primeiro, porque um decreto que *menciona* o plano
# continua sendo decreto, e decreto não pontua (METODOLOGIA §12) nem entra na fila de planos.
SINAIS_DE_DECRETO = (
    "decreto", "situacao de emergencia", "situação de emergência", "estado de calamidade",
    "calamidade publica", "calamidade pública", "homologa", "reconhece a situacao",
    "reconhece a situação", "portaria de reconhecimento",
)
SINAIS_DE_PLANO = (
    "plano de contingencia", "plano de contingência", "plano municipal", "plano de resposta",
    "plano diretor de defesa", "plano de acao", "plano de ação", "plancon",
)
SINAIS_DE_ESTRUTURA = (
    "coordenadoria municipal de protecao", "coordenadoria municipal de proteção", "compdec",
    "defesa civil municipal", "sala de situacao", "sala de situação", "nucleo de defesa civil",
    "núcleo de defesa civil", "nudec", "secretaria de protecao e defesa civil",
    "secretaria de proteção e defesa civil", "orgao municipal de defesa civil",
    "órgão municipal de defesa civil",
)


def _sem_acento(s: str) -> str:
    """Minúsculas e sem acento, para casar sinal com texto. Função pura."""
    import unicodedata
    bruto = unicodedata.normalize("NFKD", str(s or "").lower())
    return "".join(c for c in bruto if not unicodedata.combining(c))


def classificar_tipo(pista: dict) -> str:
    """plano | estrutura | decreto | outro, pelos sinais do título e do trecho. Função pura.

    Na dúvida devolve `outro`, e `outro` é recusado com motivo — o classificador que não sabe não
    classifica (regra editorial permanente). Chutar `plano` encheria a fila com o que a busca
    devolveu por acaso, que é exatamente o que produziu as 8.681 de 03/10.
    """
    p = pista or {}
    # `tipo` já declarado pelo coletor é respeitado: ele sabe mais do que o texto.
    declarado = str(p.get("tipo") or "").strip().lower()
    if declarado in ("plano", "estrutura", "decreto", "outro"):
        return declarado
    texto = _sem_acento(" ".join(str(p.get(c) or "") for c in ("titulo", "trecho", "url_final",
                                                               "url", "assunto")))
    for sinal in SINAIS_DE_DECRETO:
        if _sem_acento(sinal) in texto:
            return "decreto"
    for sinal in SINAIS_DE_PLANO:
        if _sem_acento(sinal) in texto:
            return "plano"
    for sinal in SINAIS_DE_ESTRUTURA:
        if _sem_acento(sinal) in texto:
            return "estrutura"
    return "outro"


def resolver_url_final(pista: dict) -> str:
    """O endereço do veículo, já resolvido — ou "" quando só há redirecionador. Função pura.

    Não busca na rede: resolver redirecionador de verdade é trabalho do coletor, que tem a resposta
    HTTP em mão. Aqui só se aproveita o que já veio (`url_final`, ou `url` quando ela não é
    redirecionador) e se recusa o resto com motivo.
    """
    p = pista or {}
    for campo in ("url_final", "url_veiculo", "url"):
        url = str(p.get(campo) or "").strip()
        if not url:
            continue
        if any(r in url for r in REDIRECIONADORES):
            continue
        return url
    return ""


def resolver_alvo(pista: dict) -> str:
    """Código IBGE do município, ou sigla da UF. Função pura.

    IBGE antes de UF: a UF é o alvo mais grosso que o esquema aceita, e usá-la quando o município é
    conhecido faria a pista do município virar pista do estado.
    """
    p = pista or {}
    for campo in ("alvo", "ibge", "codigo_ibge", "municipio_ibge"):
        v = str(p.get(campo) or "").strip()
        if v and v.isdigit() and len(v) == 7:
            return v
    for campo in ("alvo", "uf", "sigla_uf"):
        v = str(p.get(campo) or "").strip().upper()
        if len(v) == 2 and v.isalpha():
            return v
    return ""


def resolver_nivel(pista: dict) -> str:
    """A | B | C. Função pura. Sem sinal, C — o nível mais baixo, nunca o mais alto."""
    p = pista or {}
    for campo in ("nivel", "nivel_confianca"):
        v = str(p.get(campo) or "").strip().upper()
        if v in ("A", "B", "C"):
            return v
    return "C"


def resolver_data(pista: dict) -> str:
    """A data do achado em AAAA-MM-DD. Função pura.

    Aceita dd/mm/aaaa, que é o formato que a maioria dos coletores grava, e AAAA-MM-DD, que é o do
    esquema. Data ilegível devolve "" e a pista é recusada: data errada no achado desalinha o corte
    editorial, e corte desalinhado é pior do que pista perdida.
    """
    p = pista or {}
    for campo in ("data", "data_achado", "registrado_em"):
        bruto = str(p.get(campo) or "").strip()
        if not bruto:
            continue
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", bruto[:10]) and len(bruto) >= 10:
            return bruto[:10]
        m = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", bruto)
        if m:
            d, mes, a = m.groups()
            try:
                return dt.date(int(a), int(mes), int(d)).isoformat()
            except ValueError:
                continue
    return ""


def normalizar(pista: dict, origem: str = "") -> dict:
    """A pista no esquema de `schemas/pista.json`, preservando tudo o que o coletor pôs. Função pura.

    Nada do original se perde: os campos do coletor (`municipio`, `uf`, `trecho`, `sinais`, a
    verificação de fonte) continuam ali. O que esta função faz é **acrescentar** os seis campos que
    o esquema cobra, derivados do que já veio.
    """
    p = dict(pista or {})
    bruta = str(origem or p.get("origem") or p.get("rota") or "").strip()
    p["origem"] = ORIGEM_CANONICA.get(bruta, bruta)
    p["origem_do_coletor"] = bruta
    p["url_final"] = resolver_url_final(p)
    p["alvo"] = resolver_alvo(p)
    p["nivel"] = resolver_nivel(p)
    # Data ilegível vira "" DE PROPÓSITO: manter o original deixaria passar "4 de outubro",
    # e `validar_pista` só recusa o campo vazio. Corte desalinhado é pior que pista perdida.
    p["data"] = resolver_data(p)
    p["tipo"] = classificar_tipo(p)
    return p


def motivo_de_recusa(pista: dict, existentes: list = None) -> str:
    """"" quando a pista pode entrar, ou o motivo da recusa. Função pura.

    Delega a `coletores_base.validar_pista`, que é onde a regra vive desde 03/10 — duplicar a regra
    aqui criaria duas verdades, que é o defeito que este módulo existe para fechar.
    """
    from coletores_base import validar_pista
    ok, motivo = validar_pista(pista, existentes or [])
    return "" if ok else motivo


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

    # ---- fixtures: as formas reais que os coletores gravam hoje ----
    REDE = {"municipio": "Bonito", "uf": "MS", "origem": "rede_social_oficial",
            "url": "https://bonito.ms.gov.br/noticia/plano-de-contingencia",
            "titulo": "Prefeitura apresenta Plano de Contingência para a estiagem",
            "trecho": "O documento foi assinado nesta segunda", "data": "04/10/2026",
            "ibge": "5002209"}
    BUSCA = {"municipio": "Tocantínia", "uf": "TO", "ibge": "1721109", "origem": "busca_web",
             "data": "04/10/2026", "url": "https://x.to.gov.br/plano-municipal",
             "titulo": "Plano municipal de contingência", "nivel_confianca": "B"}

    n = normalizar(REDE)
    ok("a origem do coletor vira a origem canônica do esquema", n["origem"] == "rede_social")
    ok("a origem do coletor fica registrada", n["origem_do_coletor"] == "rede_social_oficial")
    ok("url_final sai da url quando ela não é redirecionador",
       n["url_final"] == REDE["url"])
    ok("o alvo sai do código IBGE", n["alvo"] == "5002209")
    ok("sem sinal de nível, o nível é C", n["nivel"] == "C")
    ok("nivel_confianca vira nivel", normalizar(BUSCA)["nivel"] == "B")
    ok("a data dd/mm/aaaa vira AAAA-MM-DD", n["data"] == "2026-10-04")
    ok("o tipo sai dos sinais do título", n["tipo"] == "plano")
    ok("nada do que o coletor pôs se perde", n["municipio"] == "Bonito" and n["uf"] == "MS")
    ok("a fixture de rede social passa a valer no esquema", motivo_de_recusa(n) == "")
    ok("a fixture de busca web passa a valer no esquema",
       motivo_de_recusa(normalizar(BUSCA)) == "")

    # ---- classificação ----
    ok("decreto é reconhecido",
       classificar_tipo({"titulo": "Decreto declara situação de emergência"}) == "decreto")
    ok("decreto vence plano no mesmo texto",
       classificar_tipo({"titulo": "Decreto de emergência cita o plano de contingência"})
       == "decreto")
    ok("estrutura é reconhecida",
       classificar_tipo({"titulo": "Município cria a COMPDEC"}) == "estrutura")
    ok("sem sinal nenhum o tipo é 'outro' — o classificador que não sabe não classifica",
       classificar_tipo({"titulo": "Prefeitura inaugura creche"}) == "outro")
    ok("o tipo que o coletor declarou é respeitado",
       classificar_tipo({"tipo": "estrutura", "titulo": "Plano de contingência"}) == "estrutura")
    ok("o acento não muda a classificação",
       classificar_tipo({"titulo": "PLANO DE CONTINGÊNCIA"}) == "plano")

    # ---- recusas, cada uma com motivo ----
    ok("sem url_final recusa",
       "url_final" in motivo_de_recusa(normalizar(dict(REDE, url=None))))
    ok("redirecionador do Google News não serve de url_final",
       "url_final" in motivo_de_recusa(normalizar(
           dict(REDE, url="https://news.google.com/rss/articles/CBMi"))))
    ok("sem alvo recusa",
       "alvo" in motivo_de_recusa(normalizar(dict(REDE, ibge=None, uf=None))))
    ok("tipo 'outro' é recusado com motivo",
       "outro" in motivo_de_recusa(normalizar(
           dict(REDE, titulo="Prefeitura inaugura creche", trecho=""))))
    ok("pista de decreto não entra na fila de planos",
       "base oficial" in motivo_de_recusa(normalizar(
           dict(REDE, titulo="Decreto declara situação de emergência"))))
    ok("data ilegível recusa",
       "data" in motivo_de_recusa(normalizar(
           {k: v for k, v in dict(REDE, data="4 de outubro").items()
            if k != "registrado_em"})))
    ok("repetida recusa", "repetida" in motivo_de_recusa(n, [n]))
    # URLs distintas: com a mesma, a recusa que chega primeiro é a de repetida, não a do teto.
    cheias = [dict(n, url_final=f"https://bonito.ms.gov.br/n/{i}", nivel="A") for i in range(5)]
    ok("acima do teto recusa", "teto" in motivo_de_recusa(n, cheias))
    ok("a UF serve de alvo quando o município não é conhecido",
       normalizar(dict(REDE, ibge=None))["alvo"] == "MS")

    # ---- a chave da pista ----
    ok("a chave usa o id quando ele existe", chave_da_pista({"id": "a1"}) == "id:a1")
    ok("sem id, a chave é url_final + alvo",
       chave_da_pista({"url_final": "https://x/1", "alvo": "9"}) == "url:https://x/1|9")
    ok("sem id, a url crua serve de chave",
       chave_da_pista({"url": "https://x/1", "ibge": "9"}) == "url:https://x/1|9")
    ok("pistas iguais têm a mesma chave",
       chave_da_pista(dict(n)) == chave_da_pista(dict(n)))

    # ---- gravar_lote e sincronizar, com disco de mentira ----
    import tempfile, json as _json, os as _os
    import coletores_base as cb
    with tempfile.TemporaryDirectory() as t:
        falso = {}

        def ler_falso(nome, padrao=None):
            return _json.loads(_json.dumps(falso.get(nome))) if nome in falso else padrao

        def gravar_falso(nome, obj, compacto=False):
            falso[nome] = _json.loads(_json.dumps(obj))

        real_ler, real_gravar = cb.ler, cb.gravar
        cb.ler, cb.gravar = ler_falso, gravar_falso
        try:
            b = gravar_lote([REDE, BUSCA], origem="")
            ok("gravar_lote grava as duas boas", b["gravadas"] == 2)
            ok("gravar_lote não recusa o que é válido", b["recusadas"] == 0)
            ok("a fila no disco tem as duas", len(falso[FILA_PADRAO]["pistas"]) == 2)
            ok("a pista gravada está no esquema",
               all(p.get("url_final") and p.get("tipo") and p.get("alvo") and p.get("nivel")
                   for p in falso[FILA_PADRAO]["pistas"]))

            b2 = gravar_lote([REDE], origem="")
            ok("gravar_lote não duplica: a repetida incrementa repeticoes",
               b2["gravadas"] == 0 and len(falso[FILA_PADRAO]["pistas"]) == 2)
            ok("o contador de repetições subiu",
               any(p.get("repeticoes") == 1 for p in falso[FILA_PADRAO]["pistas"]))

            ruim_sem_alvo = dict(REDE, url="https://y.ms.gov.br/z", ibge=None, uf=None)
            b3 = gravar_lote([ruim_sem_alvo], origem="rede_social_oficial")
            ok("gravar_lote recusa a pista sem alvo", b3["gravadas"] == 0 and b3["recusadas"] == 1)
            ok("a recusa fica registrada com origem e motivo",
               falso[ARQUIVO_DE_REJEITADAS]["rejeitadas"][0]["origem"] == "rede_social_oficial"
               and "alvo" in falso[ARQUIVO_DE_REJEITADAS]["rejeitadas"][0]["motivo"])
            ok("as rejeitadas trazem o total", falso[ARQUIVO_DE_REJEITADAS]["total"] == 1)

            gravar_lote([ruim_sem_alvo], origem="rede_social_oficial")
            rej = falso[ARQUIVO_DE_REJEITADAS]["rejeitadas"]
            ok("a MESMA recusa nao empilha copia identica", len(rej) == 1)
            ok("a repeticao da recusa fica contavel em vezes", rej[0].get("vezes") == 2)

            outro_motivo = dict(REDE, url="https://y.ms.gov.br/z", tipo="outro")
            gravar_lote([outro_motivo], origem="rede_social_oficial")
            ok("mesma url com OUTRO motivo e outra recusa",
               len(falso[ARQUIVO_DE_REJEITADAS]["rejeitadas"]) == 2)

            # sincronizar: salvamento parcial de varredura longa
            memoria = {"pistas": list(falso[FILA_PADRAO]["pistas"])}
            memoria["pistas"].append(dict(REDE, url="https://w.ms.gov.br/plano-municipal",
                                          id="novo1"))
            s1 = sincronizar(FILA_PADRAO, memoria, origem="diarios_municipais")
            ok("sincronizar acrescenta só o que é novo",
               s1["gravadas"] == 1 and s1["mescladas"] == 2)
            ok("sincronizar é idempotente: a segunda passada não grava nada",
               sincronizar(FILA_PADRAO, memoria, origem="diarios_municipais")["gravadas"] == 0)
            ok("sincronizar não perde o que está só no disco",
               len(falso[FILA_PADRAO]["pistas"]) == 3)
            ok("sincronizar mescla o estado que a memória tocou",
               (memoria["pistas"][0].__setitem__("triagem", "humana"),
                sincronizar(FILA_PADRAO, memoria),
                falso[FILA_PADRAO]["pistas"][0].get("triagem") == "humana")[2])
            ok("sincronizar deixa a memória igual ao disco",
               memoria["pistas"] is falso[FILA_PADRAO]["pistas"]
               or len(memoria["pistas"]) == len(falso[FILA_PADRAO]["pistas"]))
            ok("sincronizar em fila vazia não quebra",
               sincronizar("pistas_vazia.json", {"pistas": []})["gravadas"] == 0)
        finally:
            cb.ler, cb.gravar = real_ler, real_gravar

    # ---- travas estruturais ----
    import dis
    puras = ("classificar_tipo", "resolver_url_final", "resolver_alvo", "resolver_nivel",
             "resolver_data", "normalizar", "motivo_de_recusa", "_sem_acento")
    nomes = set()
    for nome_obj in puras:
        codigo = getattr(globals()[nome_obj], "__code__", None)
        if codigo is not None:
            nomes |= {i.argval for i in dis.get_instructions(codigo) if isinstance(i.argval, str)}
    ok("trava estrutural: as funções puras não escrevem",
       not ({"gravar", "gravar_em", "write_text", "write_bytes", "rejeitar"} & nomes))
    ok("trava estrutural: as funções puras não vão à rede",
       not ({"buscar", "urlopen", "buscar_searxng"} & nomes))

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else f"✓ AUTOTESTE OK — {len(_casos_contados)} casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def rejeitar(pista: dict, origem: str, motivo: str, ler_fn=None, gravar_fn=None) -> None:
    """Registra a recusa em `data/pistas_rejeitadas.json`. ESCREVE.

    Recusa sem registro é dado perdido sem rastro: pela regra editoriall de ausência, o que não
    entrou tem de ficar contável, com origem e campo ausente, para que "a fila encolheu" se
    distinga de "o coletor parou de achar".
    """
    from coletores_base import ler as ler_base, gravar as gravar_base, hoje_editorial
    ler, gravar = (ler_fn or ler_base), (gravar_fn or gravar_base)
    doc = ler(ARQUIVO_DE_REJEITADAS) or {"rejeitadas": []}
    lista = doc.setdefault("rejeitadas", [])
    registro = {
        "origem": origem, "origem_canonica": (pista or {}).get("origem"),
        "motivo": motivo,
        "url": str((pista or {}).get("url_final") or (pista or {}).get("url") or "")[:400],
        "alvo": (pista or {}).get("alvo"), "tipo": (pista or {}).get("tipo"),
        "municipio": (pista or {}).get("municipio"), "uf": (pista or {}).get("uf"),
        "rejeitada_em": hoje_editorial().isoformat(),
    }
    # A MESMA recusa chega quantas vezes o coletor reencontra o alvo, e a reaplicacao de artefato a
    # traz de novo. Empilhar copia identica nao acrescenta rastro e dobra o arquivo: em 07/10/2026
    # `data/pistas_rejeitadas.json` foi de 4,8 MB a 9,0 MB numa execucao, 7.778 copias exatas de
    # 9.708 registros. Conta-se em `vezes`, que e o que a regra de ausencia pede: contavel.
    k = chave_da_rejeicao(registro)
    for anterior in lista:
        if chave_da_rejeicao(anterior) == k:
            anterior["vezes"] = int(anterior.get("vezes") or 1) + 1
            anterior["rejeitada_em"] = registro["rejeitada_em"]
            break
    else:
        lista.append(registro)
    doc["atualizado_em"] = hoje_editorial().isoformat()
    doc["total"] = len(lista)
    gravar(ARQUIVO_DE_REJEITADAS, doc)


def gravar(pista: dict, origem: str = "", nome_da_fila: str = FILA_PADRAO) -> tuple:
    """A ÚNICA porta da fila de pistas. Devolve (gravada, motivo). ESCREVE.

    Nenhum coletor abre `data/pistas_*.json` para escrita: quem tenta é reprovado por
    `scripts/verificar_escritor_de_pista.py` no PR.
    """
    from coletores_base import ler, gravar as gravar_arquivo, hoje_editorial
    normal = normalizar(pista, origem)
    doc = ler(nome_da_fila) or {"pistas": []}
    lista = doc.get("pistas") if isinstance(doc.get("pistas"), list) else doc.setdefault("pistas", [])
    motivo = motivo_de_recusa(normal, lista)
    if motivo:
        if motivo.startswith("repetida"):
            url = str(normal.get("url_final") or "")
            for p in lista:
                if str(p.get("url_final") or p.get("url") or "") == url:
                    p["repeticoes"] = int(p.get("repeticoes") or 0) + 1
                    break
            gravar_arquivo(nome_da_fila, doc)
        else:
            rejeitar(normal, origem or normal.get("origem_do_coletor") or "", motivo)
        return False, motivo
    normal.setdefault("registrado_em", hoje_editorial().isoformat())
    normal.setdefault("status", "pista — na fila, aguardando busca dirigida e juiz")
    lista.append(normal)
    gravar_arquivo(nome_da_fila, doc)
    return True, ""


def gravar_lote(novas: list, origem: str = "", nome_da_fila: str = FILA_PADRAO,
                ler_fn=None, gravar_fn=None) -> dict:
    """Grava várias pistas numa leitura e numa escrita. Devolve {gravadas, recusadas, motivos}.

    Existe porque `data/pistas_imprensa.json` tem 25 MB: chamar `gravar()` por pista faria uma
    leitura e uma escrita do arquivo inteiro para cada achado — centenas de vezes por rodada. O
    coletor junta os achados da rodada e entrega aqui, e a validação é a mesma, pista por pista,
    inclusive a deduplicação contra o que a PRÓPRIA rodada acabou de acrescentar.
    """
    # `ler_fn`/`gravar_fn`: a mesma lição de isolamento descrita em `sincronizar`.
    from coletores_base import ler as ler_base, gravar as gravar_base, hoje_editorial
    ler = ler_fn or ler_base
    gravar_arquivo = gravar_fn or gravar_base
    doc = ler(nome_da_fila) or {"pistas": []}
    lista = doc.get("pistas") if isinstance(doc.get("pistas"), list) else doc.setdefault("pistas", [])
    hoje = hoje_editorial().isoformat()
    recusadas, motivos = [], {}
    gravadas = 0
    for bruta in novas or []:
        normal = normalizar(bruta, origem)
        motivo = motivo_de_recusa(normal, lista)
        if motivo:
            if motivo.startswith("repetida"):
                url = str(normal.get("url_final") or "")
                for p in lista:
                    if str(p.get("url_final") or p.get("url") or "") == url:
                        p["repeticoes"] = int(p.get("repeticoes") or 0) + 1
                        break
            else:
                recusadas.append((normal, motivo))
            motivos[motivo.split(":")[0]] = motivos.get(motivo.split(":")[0], 0) + 1
            continue
        normal.setdefault("registrado_em", hoje)
        normal.setdefault("status", "pista — na fila, aguardando busca dirigida e juiz")
        lista.append(normal)
        gravadas += 1
    gravar_arquivo(nome_da_fila, doc)
    for normal, motivo in recusadas:
        rejeitar(normal, origem or normal.get("origem_do_coletor") or "", motivo,
                 ler_fn=ler_fn, gravar_fn=gravar_fn)
    return {"gravadas": gravadas, "recusadas": len(recusadas), "motivos": motivos}


def chave_da_rejeicao(registro: dict) -> str:
    """A identidade de uma RECUSA: alvo da recusa mais o motivo. Funcao pura.

    Duas recusas com a mesma url, o mesmo alvo e o mesmo motivo sao a mesma recusa reencontrada —
    nao duas. O que muda entre elas e a data, e essa fica no registro como a ultima vez.
    """
    r = registro or {}
    return "|".join([str(r.get("url") or ""), str(r.get("alvo") or ""),
                     str(r.get("origem_canonica") or ""), str(r.get("motivo") or "")])


def chave_da_pista(pista: dict) -> str:
    """A identidade da pista, para casar memória com disco. Função pura.

    `id` quando o coletor o calcula (a maioria calcula), senão url_final + alvo — que é a mesma
    chave da deduplicação do esquema.
    """
    p = pista or {}
    ident = str(p.get("id") or "").strip()
    if ident:
        return "id:" + ident
    url = str(p.get("url_final") or p.get("url") or "").strip()
    return "url:" + url + "|" + str(p.get("alvo") or p.get("ibge") or p.get("uf") or "")


def sincronizar(nome_da_fila: str, fila_em_memoria: dict, origem: str = "",
                ler_fn=None, gravar_fn=None) -> dict:
    """Leva ao disco a fila que o coletor montou em memória, pela porta. ESCREVE.

    Existe para os coletores que varrem por horas e fazem **salvamento parcial** — diários
    municipais e consorciados, Diário Oficial estadual, descoberta. Eles leem a fila, acrescentam
    ao longo da varredura e gravam várias vezes; chamar `gravar_lote` com "o que é novo" exigiria
    que cada um soubesse onde parou, e a conta errada perderia ou duplicaria trabalho.

    Aqui a conta é feita no único lugar: o que está em memória e não está no disco é **pista nova**
    e passa pela validação; o que está nos dois tem os campos da memória **mesclados** sobre o do
    disco (é como o estado de `seguimento`, `triagem` e contadores volta ao arquivo); o que está só
    no disco **fica** — outro elo pode tê-lo acrescentado em paralelo, e descartá-lo seria a perda
    silenciosa que o log append-only proíbe.

    `ler_fn`/`gravar_fn` existem por uma lição que este projeto já pagou (ver `carimbar_atos` em
    `coletores_base.py`): o autoteste do coletor troca o `ler` e o `gravar` DO PRÓPRIO MÓDULO por
    falsos, e um ajudante que chamasse `coletores_base.gravar` passaria por fora da troca e gravaria
    a fixture no arquivo real. Já aconteceu, e levou 907 atos a 1. Cada coletor passa o seu par —
    `ler_fn=ler, gravar_fn=gravar` — e a escrita volta a acontecer onde o teste a intercepta.

    Devolve {gravadas, recusadas, mescladas, motivos}.
    """
    from coletores_base import ler as ler_base, gravar as gravar_base, hoje_editorial
    ler = ler_fn or ler_base
    gravar_arquivo = gravar_fn or gravar_base
    em_disco = ler(nome_da_fila) or {"pistas": []}
    chave_lista = "pistas" if em_disco.get("pistas") is not None else (
        "itens" if em_disco.get("itens") is not None else "pistas")
    no_disco = em_disco.get(chave_lista)
    if not isinstance(no_disco, list):
        no_disco = []
        em_disco[chave_lista] = no_disco
    por_chave = {chave_da_pista(p): p for p in no_disco}

    da_memoria = (fila_em_memoria or {}).get("pistas")
    if not isinstance(da_memoria, list):
        da_memoria = (fila_em_memoria or {}).get("itens") or []

    hoje = hoje_editorial().isoformat()
    recusadas, motivos = [], {}
    gravadas = mescladas = 0
    for bruta in da_memoria:
        k = chave_da_pista(bruta)
        antiga = por_chave.get(k)
        if antiga is not None:
            # Mescla: a memória tem o estado mais novo dos campos que ela tocou. Nada se apaga —
            # campo que só existe no disco permanece.
            for campo, valor in (bruta or {}).items():
                if valor not in (None, "", [], {}):
                    antiga[campo] = valor
            mescladas += 1
            continue
        normal = normalizar(bruta, origem)
        motivo = motivo_de_recusa(normal, no_disco)
        if motivo:
            chave_motivo = motivo.split(":")[0]
            motivos[chave_motivo] = motivos.get(chave_motivo, 0) + 1
            if not motivo.startswith("repetida"):
                recusadas.append((normal, motivo))
            continue
        normal.setdefault("registrado_em", hoje)
        normal.setdefault("status", "pista — na fila, aguardando busca dirigida e juiz")
        no_disco.append(normal)
        por_chave[k] = normal
        gravadas += 1
    gravar_arquivo(nome_da_fila, em_disco)
    for normal, motivo in recusadas:
        rejeitar(normal, origem or normal.get("origem_do_coletor") or "", motivo,
                 ler_fn=ler_fn, gravar_fn=gravar_fn)
    # A memória passa a refletir o disco, para que o próximo salvamento parcial da mesma rodada
    # não reapresente o que já entrou nem perca o que outro elo acrescentou.
    if isinstance((fila_em_memoria or {}).get("pistas"), list):
        fila_em_memoria["pistas"] = no_disco
    elif isinstance((fila_em_memoria or {}).get("itens"), list):
        fila_em_memoria["itens"] = no_disco
    return {"gravadas": gravadas, "recusadas": len(recusadas), "mescladas": mescladas,
            "motivos": motivos}


def main() -> int:
    if "--autoteste" in sys.argv[1:]:
        return _autoteste()
    print(__doc__.strip().splitlines()[1])
    return 0


if __name__ == "__main__":
    sys.exit(main())
