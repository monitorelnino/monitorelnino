#!/usr/bin/env python3
"""
coletar_saude_estadual.py — o funil de PLANOS DE SAÚDE dos 27 estados
======================================================================
Bloco A do handover do MARÉ Saúde (editoria, 01/10/2026). Mesma arquitetura do MARÉ Legal — busca
com cascata e disjuntor, busca dirigida nas fontes declaradas, juiz que só promove com documento
primário oficial lido — mas com as **fontes e os termos da saúde**, que são outros.

POR QUE UM COLETOR NOVO, E NÃO UM PARÂMETRO NO QUE EXISTE
---------------------------------------------------------
`monitorar_busca_web.py` pergunta por MUNICÍPIO e peneira pelo nome do município; o plano de saúde
que interessa aqui é ESTADUAL, e quem o publica é a secretaria estadual de saúde, o diário oficial
do estado, o centro de vigilância ou a sala de situação. Peneirar por nome de município descartaria
exatamente o documento certo. `coletar_doe.py` lê os 27 diários, mas com os termos da defesa civil.

O QUE ELE FAZ, E O QUE ELE NÃO FAZ
----------------------------------
Ele **agrupa candidatos**: toda saída deste coletor é PISTA, em `data/pistas_imprensa_saude.json`,
com `origem: "funil_saude_estadual"`. Nenhuma pista entra em `saude_uf.json` ou em
`monitor_saude.json` por aqui — quem promove é `juiz.py`, com o documento primário lido, e a trava
está declarada na governança do próprio arquivo de pistas.

Ele **registra a bateria**: cada UF tentada vira execução logada com `nivel="estadual"`, e é essa
execução que autoriza a página a dizer "não localizado" em vez de "não verificado". Sem bateria
logada, "não localizado" é afirmação sem lastro — a regra é a mesma do MARÉ Legal (§4.1.2), e vale
aqui pela mesma razão.

Ele **não** apresenta zero resultado como ausência. Motor doente, timeout e corpo vazio servido com
200 são `motor_sem_resposta`, e a UF continua não verificada. Recusa servida com 200 é recusa
(§186).

ONDE A BUSCA ABERTA RODA
-----------------------
Contra a instância efêmera de SearXNG que a Action sobe no próprio job (Docker, sem chave, sem
cadastro). Fora da Action ela não existe, e `--bateria` diz isso em voz alta em vez de gravar
silêncio como ausência. O modo `--fontes` não depende dela: lê as fontes declaradas por UF, e roda
em qualquer máquina.

USO
  python coletar_saude_estadual.py --autoteste
  python coletar_saude_estadual.py --fontes            # fontes declaradas (sem SearXNG)
  python coletar_saude_estadual.py --fontes --uf MT
  python coletar_saude_estadual.py --bateria           # busca aberta (precisa de SearXNG)
  python coletar_saude_estadual.py --bateria --uf RR
  python coletar_saude_estadual.py --doe --desde 2026-06-29    # canal 2: diário oficial do estado
  python coletar_saude_estadual.py --canais                    # canal 3: CIEVS, sala de situação, COE

OS QUATRO CANAIS
----------------
A editoria exige quatro canais antes de qualquer "não localizado" (handover de 01/10/2026):
busca aberta (`--bateria`), diário oficial do estado com os termos da SAÚDE (`--doe`), páginas do
CIEVS e da sala de situação/COE de cada secretaria (`--canais`) e o juiz (`julgar_saude.py`). Um
canal que não rodou não é um canal que não achou: a UF segue não verificada por ele, e é por isso
que cada modo registra a sua própria decisão no log.
"""
import json
import pathlib
import re
import sys
import urllib.parse
import urllib.request

import funil
import motores_busca
from coletores_base import (buscar, gravar, hoje_editorial, ler, log_busca, preservar_evidencia,
                            registrar_lacuna, rodar_autoteste, ua_de)

UFS = ("AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO").split()
UF_NOME = {
    "AC": "Acre", "AL": "Alagoas", "AM": "Amazonas", "AP": "Amapá", "BA": "Bahia", "CE": "Ceará",
    "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás", "MA": "Maranhão",
    "MG": "Minas Gerais", "MS": "Mato Grosso do Sul", "MT": "Mato Grosso", "PA": "Pará",
    "PB": "Paraíba", "PE": "Pernambuco", "PI": "Piauí", "PR": "Paraná", "RJ": "Rio de Janeiro",
    "RN": "Rio Grande do Norte", "RO": "Rondônia", "RR": "Roraima", "RS": "Rio Grande do Sul",
    "SC": "Santa Catarina", "SE": "Sergipe", "SP": "São Paulo", "TO": "Tocantins",
}

SEARXNG_URL = "http://127.0.0.1:8080/search"
PISTAS = "pistas_imprensa_saude.json"
ORIGEM = "funil_saude_estadual"

# As consultas, uma linha por pergunta que se faz à fonte. São as do handover, e cada uma existe
# porque o documento pode se chamar de um jeito diferente em cada estado: o que em MT é "processo de
# preparação e resposta a emergências em saúde pública" em outro estado é "plano de contingência de
# arboviroses". Pedir uma só string é o defeito que a busca municipal já pagou (46% de consultas com
# zero resultado, medido em 21–27/09/2026).
CONSULTAS = (
    ("plancon_elnino", '"plano de contingência" "El Niño" secretaria de saúde {nome}'),
    ("preparacao", '"plano" "preparação e resposta" "emergências em saúde pública" {nome}'),
    ("enfrentamento", '"plano estadual de enfrentamento" El Niño saúde {nome}'),
    ("arbovirose", '"plano de contingência" arboviroses secretaria estadual de saúde {nome}'),
    ("calor", '"plano" OR "protocolo" "onda de calor" OR "excesso de calor" saúde {nome}'),
    ("sala_situacao", '"sala de situação" saúde clima OR El Niño {nome} secretaria de saúde'),
    ("coe", '"centro de operações de emergência" OR COES saúde {nome}'),
    ("doe_saude", '"diário oficial" {nome} saúde "plano de contingência" 2026'),
)

# Termos que fazem um resultado valer como CANDIDATO. Literal, sem inferência semântica: a peneira
# agrupa, o juiz decide.
TERMOS_INSTRUMENTO = ("plano de conting", "plano estadual", "plano de preparação", "plano de ação",
                      "preparação e resposta", "enfrentamento", "sala de situação",
                      "centro de operações de emergência", "coes", "portaria", "resolução")
TERMOS_RISCO = ("el niño", "el nino", "arbovirose", "dengue", "chikungunya", "calor",
                "estiagem", "seca", "queimada", "fumaça", "qualidade do ar",
                "emergência em saúde pública", "emergências em saúde pública", "clima")

# Domínios que fazem o resultado ser FONTE OFICIAL, e não notícia sobre ela. A lista é por sufixo e
# curta de propósito: imprensa descobre, nunca registra (Errata C29, 01/10/2026). Uma pista de
# notícia continua entrando na fila — com `oficial: false`, para que a triagem veja a diferença.
SUFIXOS_OFICIAIS = (".gov.br", ".leg.br", ".jus.br")

# CANAL 2 — os termos da SAÚDE no diário oficial do estado. Os da defesa civil (coletar_doe.py)
# procuram homologação de decreto municipal e não casariam com instrumento de saúde; estes quatro
# são os nomes com que o ato de saúde aparece no diário. "plano de contingência" sozinho casaria
# plano de greve, e é por isso que a peneira `relevante` continua cobrando termo de risco.
TERMOS_DOE_SAUDE = ("plano de contingência", "emergência em saúde pública",
                    "sala de situação", "centro de operações de emergência")

# CANAL 3 — o que faz um link da página da secretaria valer como candidato.
TERMOS_CANAL = ("cievs", "sala de situação", "centro de operações de emergência", "coes",
                "plano de contingência", "plano estadual")

# O endereço RAIZ da secretaria de cada UF vive no arquivo de fontes, não aqui: é dado, e dado
# sondado um a um. `null` naquele arquivo é lacuna declarada e impede "não localizado" por este
# canal.
ARQUIVO_CANAIS = "saude_desfechos/fontes_uf.json"
RE_LINK = re.compile(r"""<a\b[^>]*href=["']([^"'#]+)["'][^>]*>(.*?)</a>""", re.I | re.S)
RE_TAG = re.compile(r"<[^>]+>")

# Fontes declaradas por UF, lidas no modo `--fontes` (canal 4).
#
# REGRA MÍNIMA, fechada pela editoria em 02/10/2026 e válida para os 27: a lista de cada unidade
# contém, no mínimo, **(a) a raiz do domínio oficial da secretaria estadual de saúde** — de onde o
# coletor segue os links de planos, vigilância, emergências e CIEVS que o próprio sítio declara — e
# **(b) o diário oficial do estado**, pelo localizador de edições. Com isso o canal 4 existe para
# todas as unidades desde já, e página específica (plano, CIEVS, guias) é acréscimo, não requisito.
#
# A raiz NÃO é digitada aqui: ela vem de `canais_instrumento`, em `saude_desfechos/fontes_uf.json`,
# onde cada endereço foi confirmado respondendo ao cliente do projeto. Unidade cuja raiz não
# respondeu entra com a lacuna medida daquele arquivo, e o diário sustenta o canal 4 sozinho.
# `ACRESCIMOS_DE_CANAL4` é só para o que a editoria citou nominalmente.
ACRESCIMOS_DE_CANAL4 = {
    # Documentos e páginas conferidos pela central em fonte oficial (02/10/2026).
    "MT": ["https://www.saude.mt.gov.br/storage/files/MmMbtQx9n43VPO23mMookK6LdUyD6h4QfMOvqx44.pdf",
           "https://www.saude.mt.gov.br/storage/files/RDtdQBfGbCiRYiJ1BIRtq6KUg32oNI4cKBWaQaiS.pdf"],
    "PA": ["https://www.saude.pa.gov.br/wp-content/uploads/2026/02/plano-emergencias-_26.02.pdf"],
}
# Raiz alternativa, quando a raiz padrão da SES não respondeu e a editoria indicou outra. O modo de
# acesso fica declarado: `humano` quer dizer que o sítio serve muro de robô ao cliente do projeto, e
# que a verificação daquela rota é humana — não que o endereço seja secreto.
RAIZ_ALTERNATIVA = {
    "PB": {"url": "https://paraiba.pb.gov.br/diretas/saude", "modo_acesso": "humano",
           "motivo": "saude.pb.gov.br redireciona para este endereço, que serve muro de robô ao "
                     "cliente do projeto (desafio no corpo, HTTP 200) — recusa respeitada"},
}


def fontes_de(uf: str, canais=None, acrescimos=None, alternativas=None) -> dict:
    """{'enderecos': [...], 'notas': [...]} do canal 4 desta UF, pela regra mínima. Função pura.

    Devolve também as notas do que ficou de fora e por quê, para o log dizer a verdade sobre o
    canal: endereço que não entra tem motivo escrito, e não desaparece em silêncio.
    """
    cfg = ((canais or {}).get("uf") or {}).get(uf) or {}
    alternativa = (alternativas if alternativas is not None else RAIZ_ALTERNATIVA).get(uf) or {}
    enderecos, notas = [], []
    raiz = cfg.get("canais_instrumento")
    if raiz:
        enderecos.append(raiz)
    elif alternativa.get("url") and alternativa.get("modo_acesso") != "humano":
        enderecos.append(alternativa["url"])
    elif alternativa.get("url"):
        notas.append(f"raiz da secretaria por verificação humana: {alternativa['url']} — "
                     + str(alternativa.get("motivo") or ""))
    else:
        notas.append("raiz da secretaria sem endereço confirmado: "
                     + str(cfg.get("canais_instrumento_lacuna") or "não verificada"))
    # (b) o diário do estado entra SEMPRE, pelo localizador — e é por isso que o canal 4 existe
    # para as 27 desde já.
    notas.append("diário oficial do estado pelo localizador de edições (coletar_edicoes_doe.py)")
    for u in (acrescimos if acrescimos is not None else ACRESCIMOS_DE_CANAL4).get(uf) or []:
        if u not in enderecos:
            enderecos.append(u)
    return {"enderecos": enderecos, "notas": notas}


# =============================================================================================
# Peneira e decisão — funções puras, testáveis sem rede
# =============================================================================================
def oficial(url: str) -> bool:
    """O endereço é de fonte oficial? Função pura."""
    host = urllib.parse.urlparse(url or "").netloc.lower()
    return bool(host) and host.endswith(SUFIXOS_OFICIAIS)


def relevante(resultado: dict, uf: str) -> bool:
    """O resultado vale como candidato? Função pura, literal, sem inferência.

    Três condições: o estado tem de aparecer (nome ou sigla), um termo de INSTRUMENTO e um termo de
    RISCO. As duas últimas separadas de propósito — "plano de contingência" sozinho casa plano de
    greve, e "dengue" sozinho casa boletim semanal. O instrumento diz que há documento; o risco diz
    que é deste assunto."""
    campos = " ".join([(resultado.get("title") or ""), (resultado.get("url") or ""),
                       (resultado.get("content") or "")]).lower()
    nome = UF_NOME.get(uf, uf).lower()
    tem_estado = nome in campos or re.search(r"[/\.\-\s]" + uf.lower() + r"[/\.\-\s]", campos) is not None
    return (tem_estado
            and any(t in campos for t in TERMOS_INSTRUMENTO)
            and any(t in campos for t in TERMOS_RISCO))


def decidir(n_brutos: int, n_pistas: int) -> str:
    """A decisão da rodada para uma UF. Função pura.

    Zero resultado bruto NUNCA é ausência: é motor doente, e a UF segue não verificada. Com
    resultado bruto e nenhuma pista, a bateria rodou e nada foi localizado até o corte — que é
    afirmação diferente de "não existe" e é assim que a página a diz."""
    if n_pistas > 0:
        return "pista"
    if n_brutos <= 0:
        return "motor_sem_resposta"
    return "bateria_sem_pista"


# A decisão interna → o vocabulário fechado do log v2. "nada localizado" NÃO entra aqui: aquele
# valor é da bateria municipal completa, lido por `recalcular_mare.py` para elevar o nível de
# verificação, e `verificar_consistencia.py` reprova se ele aparecer sem `nivel="municipal_completo"`.
# A bateria estadual que consultou e não achou é "consultado sem achado" (§184).
DECISAO_NO_LOG = {"pista": "pista",
                  "bateria_sem_pista": "consultado sem achado",
                  "motor_sem_resposta": "erro",
                  "fontes_lidas": "consultado sem achado",
                  "fonte_fora_do_ar": "erro",
                  "fonte_nao_declarada": "erro",
                  "doe_sem_pista": "consultado sem achado",
                  "canais_sem_pista": "consultado sem achado",
                  "canal_nao_disponivel": "erro",
                  "canal_nao_declarado": "erro",
                  "canal_fora_do_ar": "erro"}


def links_de_interesse(corpo: str, base: str) -> list:
    """Os links que o PRÓPRIO sítio declara e cujo texto ou endereço casa termo de canal. Pura.

    A regra que esta função existe para manter: caminho de arquivo nunca se adivinha. O coletor lê a
    página raiz da secretaria e segue o que ela aponta — tentar `/cievs` porque o nome é plausível
    produziria 404 com cara de busca feita, que é o defeito nomeado no §231 e pago pela PB em
    11/09/2026, quando o nome do arquivo não garantiu a edição."""
    saida, vistos = [], set()
    for href, bruto in RE_LINK.findall(corpo or ""):
        alvo = urllib.parse.urljoin(base, href.strip())
        if not alvo.lower().startswith(("http://", "https://")) or alvo in vistos:
            continue
        texto = re.sub(r"\s+", " ", RE_TAG.sub(" ", bruto)).strip()
        if not any(t in (texto + " " + alvo).lower() for t in TERMOS_CANAL):
            continue
        vistos.add(alvo)
        saida.append((texto, alvo))
    return saida


def chave_da_pista(p: dict) -> tuple:
    """Dedup por (uf, url, trecho) — mesmo padrão dos outros coletores de pista. Função pura."""
    return (p.get("uf"), p.get("url"), (p.get("trecho") or "")[:160])


def fundir_pistas(fila: dict, novas: list) -> tuple:
    """(fila, quantas entraram). Append-only, sem duplicar. Função pura.

    A fila de pistas só cresce: uma pista descartada pela triagem humana continua no arquivo, com o
    seu status, porque o descarte é informação. Dedup por chave, nunca por conteúdo inteiro."""
    fila = dict(fila or {})
    atuais = list(fila.get("pistas") or [])
    vistas = {chave_da_pista(p) for p in atuais}
    entraram = 0
    for p in novas:
        if chave_da_pista(p) in vistas:
            continue
        atuais.append(p)
        vistas.add(chave_da_pista(p))
        entraram += 1
    fila["pistas"] = atuais
    return fila, entraram


# =============================================================================================
# Busca aberta (SearXNG) e leitura direta
# =============================================================================================
def consultas_de(uf: str) -> list:
    nome = UF_NOME.get(uf, uf)
    return [(ident, molde.format(nome=nome)) for ident, molde in CONSULTAS]


def buscar_searxng(query: str, timeout: int = 25, motores: list = None) -> dict:
    parametros = {"q": query, "format": "json"}
    if motores:
        parametros["engines"] = ",".join(motores)
    req = urllib.request.Request(SEARXNG_URL + "?" + urllib.parse.urlencode(parametros),
                                 headers={"User-Agent": ua_de("funil de saúde estadual")})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def pista_de(resultado: dict, uf: str, ident: str, query: str) -> dict:
    """A pista como ela NASCE: não confirmada, não promovível. Função pura.

    Os três últimos campos são a TRAVA DE NASCENÇA da fila, e não enfeite.
    `data/pistas_imprensa_saude.json` é compartilhado com `monitorar_imprensa_saude.py`, e quem
    tria lê `documento_oficial_confirmado` para decidir — `scripts/preparar_fila_revisao.py` faz
    exatamente isso. Pista sem os campos passa pela triagem por AUSÊNCIA de chave (`dict.get`
    devolve `None` de qualquer jeito), o que é passar por acidente em vez de por regra. Eles
    existem para que a trava seja declarada e testável, não presumida."""
    return {"alvo": f"funil-saude/{uf}", "uf": uf, "consulta": ident, "query": query,
            "titulo": resultado.get("title"), "url": resultado.get("url"),
            "trecho": (resultado.get("content") or "")[:400],
            "oficial": oficial(resultado.get("url")),
            "origem": ORIGEM, "registrado_em": hoje_editorial().strftime("%d/%m/%Y"),
            "documento_oficial_confirmado": None,
            "promovivel": False,
            "status": "pendente_confirmacao_documento"}


def bateria(uf: str) -> dict:
    """Roda a busca aberta para uma UF e devolve o resumo. Precisa de SearXNG."""
    estado = motores_busca.ler_estado(ler)
    ativos = motores_busca.ativos(estado, motores_busca.agora_iso())
    brutos, achadas = 0, []
    for ident, query in consultas_de(uf):
        try:
            dados = buscar_searxng(query, motores=ativos or None)
        except Exception as e:
            registrar_lacuna(f"funil_saude/{uf}", f"{type(e).__name__}: {e}",
                             canal="orgao_estadual", camada=4, uf=uf, nivel="estadual",
                             strings=[query])
            continue
        resultados = dados.get("results") or []
        brutos += len(resultados)
        for r in resultados:
            if relevante(r, uf):
                achadas.append(pista_de(r, uf, ident, query))
    decisao = decidir(brutos, len(achadas))
    fila, entraram = fundir_pistas(ler(PISTAS) or {}, achadas)
    if entraram:
        gravar(PISTAS, fila)
    log_busca("orgao_estadual", 4, [q for _, q in consultas_de(uf)], DECISAO_NO_LOG[decisao],
              uf=uf, nivel="estadual", n_resultados=brutos,
              resultados=(f"funil_saude/{uf}: {brutos} resultado(s) bruto(s), {len(achadas)} pista(s), "
                          f"{entraram} nova(s) na fila · decisão interna: {decisao}"))
    funil.registrar("funil_saude_estadual", consultas=len(CONSULTAS),
                    com_resultado_bruto=1 if brutos else 0, pistas=len(achadas))
    return {"uf": uf, "brutos": brutos, "pistas": len(achadas), "novas": entraram, "decisao": decisao}


def doe_saude(uf: str, desde: str) -> dict:
    """CANAL 2: os termos da saúde na busca do diário oficial do estado.

    Reaproveita o adaptador que o `coletar_doe.py` já confirmou host a host contra produção — e só
    ele: UF cujo diário não tem rota de busca confirmada sai como `canal_nao_disponivel`, que é
    lacuna declarada, e não como estado sem instrumento."""
    import coletar_doe
    # Todo adaptador DIRETO do diário serve a este canal, não só o da plataforma comum: quem decide
    # é o `fontes_doe.json`, que é onde a cobertura de diário está declarada e medida.
    cfg = ((ler("fontes_doe.json") or {}).get("ufs") or {}).get(uf) or {}
    adaptador = cfg.get("adaptador")
    base = cfg.get("url") or coletar_doe.HOSTS_APIFRONT.get(uf)
    if adaptador not in ("apifront", "dodf", "busca_to") or not base:
        registrar_lacuna(f"funil_saude/{uf}", "diário estadual sem rota de busca confirmada",
                         canal="repositorio_estadual", camada=1, uf=uf, nivel="estadual")
        log_busca("repositorio_estadual", 1, list(TERMOS_DOE_SAUDE),
                  DECISAO_NO_LOG["canal_nao_disponivel"], uf=uf, nivel="estadual", n_resultados=0,
                  resultados=f"funil_saude/{uf}: diário estadual sem rota de busca confirmada")
        return {"uf": uf, "brutos": 0, "pistas": 0, "novas": 0, "decisao": "canal_nao_disponivel"}
    ate = hoje_editorial().isoformat()
    brutos, achadas = 0, []
    if adaptador in ("dodf", "busca_to"):
        try:
            if adaptador == "dodf":
                itens, _totais = coletar_doe.itens_dodf(uf, desde, ate,
                                                        termos=TERMOS_DOE_SAUDE)
            else:
                itens, _totais = coletar_doe.itens_busca_to(uf, desde, ate,
                                                            termos=TERMOS_DOE_SAUDE)
        except Exception as e:  # noqa: BLE001
            registrar_lacuna(f"funil_saude/{uf}", f"{type(e).__name__}: {e}",
                             canal="repositorio_estadual", camada=1, uf=uf, nivel="estadual",
                             strings=[base])
            itens = []
        brutos += len(itens)
        for it in itens:
            r = {"title": f"DOE-{uf} {it.get('data')}", "url": it.get("url"),
                 "content": (it.get("trechos") or [""])[0][:400]}
            if relevante(r, uf):
                achadas.append(pista_de(r, uf, f"doe:{adaptador}", base))
    else:
        for termo in TERMOS_DOE_SAUDE:
            try:
                _total, acertos = coletar_doe.varrer_busca_apifront(base, termo, desde, ate)
            except Exception as e:  # noqa: BLE001
                registrar_lacuna(f"funil_saude/{uf}", f"{termo}: {type(e).__name__}: {e}",
                                 canal="repositorio_estadual", camada=1, uf=uf, nivel="estadual",
                                 strings=[termo])
                continue
            brutos += len(acertos)
            for a in acertos:
                r = {"title": f"DOE-{uf} {a['data']} p.{a['pagina']}",
                     "url": coletar_doe.PDF_APIFRONT.format(base=base.rstrip("/"),
                                                            diario_id=a["diario_id"]),
                     "content": (a.get("conteudo") or "")[:400]}
                if relevante(r, uf):
                    achadas.append(pista_de(r, uf, f"doe:{termo}", termo))
    decisao = "pista" if achadas else ("doe_sem_pista" if brutos else "motor_sem_resposta")
    fila, entraram = fundir_pistas(ler(PISTAS) or {}, achadas)
    if entraram:
        gravar(PISTAS, fila)
    log_busca("repositorio_estadual", 1, list(TERMOS_DOE_SAUDE), DECISAO_NO_LOG[decisao],
              uf=uf, nivel="estadual", n_resultados=brutos,
              resultados=(f"funil_saude/{uf}: DOE de {desde} a {ate}, {brutos} acerto(s), "
                          f"{len(achadas)} pista(s), {entraram} nova(s) · decisão: {decisao}"))
    funil.registrar("funil_saude_estadual", consultas=len(TERMOS_DOE_SAUDE),
                    com_resultado_bruto=1 if brutos else 0, pistas=len(achadas))
    return {"uf": uf, "brutos": brutos, "pistas": len(achadas), "novas": entraram,
            "decisao": decisao}


def canais_ses(uf: str) -> dict:
    """CANAL 3: a página da secretaria estadual, e os links de CIEVS, sala de situação e COE que ela
    declara. Não precisa de SearXNG."""
    cfg = ((ler(ARQUIVO_CANAIS) or {}).get("uf") or {}).get(uf) or {}
    raiz = cfg.get("canais_instrumento")
    if not raiz:
        motivo = cfg.get("canais_instrumento_lacuna") or "endereço da secretaria não confirmado"
        # Regra do canal 3 (02/10/2026): quando a raiz da secretaria não pode ser visitada pelo
        # cliente do projeto, mas a editoria indicou o endereço e o modo de acesso é HUMANO, o
        # canal conta como CONSULTADO, com o motivo técnico gravado — é a regra da Paraíba. Nenhuma
        # unidade fica sem canal 3 por limitação documentada de terceiro. Sem endereço nenhum, a
        # decisão continua sendo "canal não declarado": aí ninguém procurou.
        humana = RAIZ_ALTERNATIVA.get(uf) or {}
        if humana.get("url") and humana.get("modo_acesso") == "humano":
            registrar_lacuna(f"funil_saude/{uf}",
                             f"canal 3 por verificação humana: {humana['url']} — "
                             + str(humana.get("motivo") or motivo),
                             canal="orgao_estadual", camada=1, uf=uf, nivel="estadual",
                             strings=[humana["url"]])
            log_busca("orgao_estadual", 1, [humana["url"]],
                      DECISAO_NO_LOG["canais_sem_pista"], uf=uf, nivel="estadual", n_resultados=0,
                      resultados=(f"canal 3 · funil_saude/{uf}: link(s) de canal por verificação humana em "
                                  f"{humana['url']} · modo de acesso humano · "
                                  + str(humana.get("motivo") or motivo)))
            return {"uf": uf, "links": 0, "pistas": 0, "novas": 0,
                    "decisao": "canais_sem_pista", "modo_acesso": "humano"}
        registrar_lacuna(f"funil_saude/{uf}", motivo, canal="orgao_estadual", camada=1, uf=uf,
                         nivel="estadual")
        log_busca("orgao_estadual", 1, [ARQUIVO_CANAIS], DECISAO_NO_LOG["canal_nao_declarado"],
                  uf=uf, nivel="estadual", n_resultados=0,
                  resultados=f"funil_saude/{uf}: {motivo}")
        return {"uf": uf, "links": 0, "pistas": 0, "novas": 0, "decisao": "canal_nao_declarado"}
    try:
        corpo = buscar(raiz, timeout=120, origem=ORIGEM)
    except Exception as e:  # noqa: BLE001
        registrar_lacuna(f"funil_saude/{uf}", f"{raiz}: {type(e).__name__}: {e}",
                         canal="orgao_estadual", camada=1, uf=uf, nivel="estadual", strings=[raiz])
        log_busca("orgao_estadual", 1, [raiz], DECISAO_NO_LOG["canal_fora_do_ar"], uf=uf,
                  nivel="estadual", n_resultados=0,
                  resultados=f"funil_saude/{uf}: {type(e).__name__}: {e}")
        return {"uf": uf, "links": 0, "pistas": 0, "novas": 0, "decisao": "canal_fora_do_ar"}
    # A evidência é o CORPO como a fonte o serviu — bytes. O texto decodificado serve para ler os
    # links, e só: preservar o decodificado mudaria o hash do que se afirma ter lido.
    preservar_evidencia(corpo if isinstance(corpo, bytes) else corpo.encode("utf-8"),
                        raiz, "html", ORIGEM)
    texto = corpo if isinstance(corpo, str) else corpo.decode("utf-8", "replace")
    achados = links_de_interesse(texto, raiz)
    achadas = [pista_de({"title": t or u, "url": u, "content": f"link declarado em {raiz}: {t}"},
                        uf, "canal_ses", raiz) for t, u in achados]
    decisao = "pista" if achadas else "canais_sem_pista"
    # Regra do canal 3: a página própria do CIEVS, da sala de situação ou do COE quando existir;
    # na falta dela, a visita à raiz COM OS TERMOS cumpre o canal — e fica dito que a secretaria
    # não tem página própria desses órgãos, em vez de o canal parecer não executado.
    tem_pagina_propria = bool(cfg.get("cievs")) or bool(achados)
    sem_pagina = "" if tem_pagina_propria else (
        " · a secretaria não declara página própria de CIEVS, sala de situação ou COE: o canal 3 "
        "foi cumprido pela visita à raiz com os termos")
    fila, entraram = fundir_pistas(ler(PISTAS) or {}, achadas)
    if entraram:
        gravar(PISTAS, fila)
    log_busca("orgao_estadual", 1, [raiz], DECISAO_NO_LOG[decisao], uf=uf, nivel="estadual",
              n_resultados=len(achados),
              resultados=(f"canal 3 · funil_saude/{uf}: {len(achados)} link(s) de canal em {raiz}, "
                          f"{entraram} nova(s) na fila · decisão: {decisao}" + sem_pagina))
    funil.registrar("funil_saude_estadual", consultas=1, com_resultado_bruto=1,
                    pistas=len(achadas))
    return {"uf": uf, "links": len(achados), "pistas": len(achadas), "novas": entraram,
            "decisao": decisao}


def ler_fontes(uf: str) -> dict:
    """Lê as fontes declaradas de uma UF, preservando evidência. Não precisa de SearXNG."""
    plano = fontes_de(uf, ler(ARQUIVO_CANAIS) or {})
    enderecos, notas = plano["enderecos"], plano["notas"]
    if not enderecos:
        # Pela regra mínima isto não é "nenhuma fonte declarada": o diário do estado é fonte
        # declarada de todas as unidades, e quem o lê é o localizador. O que falta aqui é a RAIZ
        # da secretaria, e a razão está escrita.
        for nota in notas:
            registrar_lacuna(f"funil_saude/{uf}", nota, canal="orgao_estadual", camada=1,
                             uf=uf, nivel="estadual")
        log_busca("orgao_estadual", 1, [ARQUIVO_CANAIS], DECISAO_NO_LOG["fontes_lidas"],
                  uf=uf, nivel="estadual", n_resultados=0,
                  resultados=(f"canal 4 · funil_saude/{uf}: 0 fonte(s) lida(s) nesta rota; o canal 4 desta "
                              f"unidade é o diário oficial, pelo localizador · "
                              + " · ".join(notas)))
        return {"uf": uf, "lidos": 0, "falhas": 0, "decisao": "fontes_lidas",
                "notas": notas}
    lidos, falhas = 0, 0
    for u in enderecos:
        try:
            corpo = buscar(u, timeout=150, origem=ORIGEM)
            preservar_evidencia(corpo, u, "pdf" if u.lower().endswith(".pdf") else "html", ORIGEM)
            lidos += 1
        except Exception as e:
            falhas += 1
            registrar_lacuna(f"funil_saude/{uf}", f"{u}: {type(e).__name__}: {e}",
                             canal="orgao_estadual", camada=1, uf=uf, nivel="estadual",
                             strings=[u])
    decisao = "fontes_lidas" if lidos else "fonte_fora_do_ar"
    log_busca("orgao_estadual", 1, enderecos, DECISAO_NO_LOG[decisao], uf=uf, nivel="estadual",
              n_resultados=lidos,
              resultados=(f"canal 4 · funil_saude/{uf}: {lidos} fonte(s) lida(s), {falhas} falha(s) · "
                          + " · ".join(notas)))
    funil.registrar("funil_saude_estadual", consultas=len(enderecos),
                    com_resultado_bruto=1 if lidos else 0)
    return {"uf": uf, "lidos": lidos, "falhas": falhas, "decisao": decisao}


# =============================================================================================
# Autoteste — offline, sem rede e sem escrever em data/
# =============================================================================================
def fonte_do_coletor() -> str:
    """O código OPERACIONAL deste arquivo, como texto — tudo o que vem antes do autoteste.

    É o que permite ao autoteste cobrar a trava estrutural: conferir o que o coletor PODE fazer,
    não só o que ele fez nesta versão. O corte no `def autoteste` não é detalhe: sem ele, os nomes
    de arquivo proibidos que o próprio teste procura aparecem no texto procurado, e o teste reprova
    por se encontrar — foi o que aconteceu na primeira versão desta trava."""
    texto = pathlib.Path(__file__).read_text(encoding="utf-8")
    corte = texto.find("def autoteste")
    return texto[:corte] if corte > 0 else texto


def autoteste() -> int:
    nascida = pista_de({"title": "t", "url": "https://saude.ac.gov.br/p.pdf", "content": "c"},
                       "AC", "plancon_elnino", "q")
    r_ok = {"title": "Plano de Contingência para Arboviroses - Secretaria de Saúde do Acre",
            "url": "https://saude.ac.gov.br/plano.pdf", "content": "dengue e chikungunya"}
    r_greve = {"title": "Plano de contingência de greve", "url": "https://saude.ac.gov.br/g",
               "content": "Acre servidores"}
    r_boletim = {"title": "Boletim semanal de dengue", "url": "https://saude.ac.gov.br/b",
                 "content": "Acre casos"}
    r_outra = {"title": "Plano de contingência arboviroses Bahia",
               "url": "https://saude.ba.gov.br/p", "content": "dengue"}
    p1 = {"uf": "AC", "url": "https://saude.ac.gov.br/p.pdf", "trecho": "a"}
    p2 = dict(p1)
    p3 = {"uf": "AC", "url": "https://saude.ac.gov.br/outro.pdf", "trecho": "b"}
    fila_uma, n_uma = fundir_pistas({"pistas": [p1]}, [p2, p3])
    fila_duas, n_duas = fundir_pistas(fila_uma, [p1, p2, p3])

    pagina = ("<html><body>"
              "<a href='/cievs'>CIEVS - Centro de Informações Estratégicas</a>"
              "<a href=\"https://saude.ac.gov.br/plano-de-contingencia.pdf\">Plano de contingência</a>"
              "<a href='/cievs'>CIEVS de novo</a>"
              "<a href='/transparencia'>Transparência</a>"
              "<a href='mailto:sala@y'>sala de situação</a>"
              "</body></html>")
    achados = links_de_interesse(pagina, "https://saude.ac.gov.br/")
    casos = {
        "domínio oficial reconhecido":
            lambda: oficial("https://www.saude.mt.gov.br/x.pdf") and oficial("https://doe.pb.gov.br/a"),
        "domínio de notícia não é oficial":
            lambda: not oficial("https://g1.globo.com/mt/noticia") and not oficial(""),
        "resultado com estado, instrumento e risco é candidato":
            lambda: relevante(r_ok, "AC"),
        "instrumento sem risco não é candidato":
            lambda: not relevante(r_greve, "AC"),
        "risco sem instrumento não é candidato":
            lambda: not relevante(r_boletim, "AC"),
        "resultado de outro estado não é candidato":
            lambda: not relevante(r_outra, "AC"),
        "zero bruto é motor doente, nunca ausência":
            lambda: decidir(0, 0) == "motor_sem_resposta",
        # A trava que importa: zero resultado NUNCA pode produzir a decisão que autoriza a página a
        # dizer "não localizado". É o defeito que a camada 4 municipal já pagou, em 27/09/2026.
        "zero bruto não produz bateria_sem_pista":
            lambda: decidir(0, 0) != "bateria_sem_pista",
        "bruto sem pista é bateria sem pista":
            lambda: decidir(12, 0) == "bateria_sem_pista",
        "uma pista basta para 'pista'":
            lambda: decidir(12, 1) == "pista",
        "fila não duplica a mesma pista":
            lambda: n_uma == 1 and len(fila_uma["pistas"]) == 2,
        "fila é append-only e idempotente":
            lambda: n_duas == 0 and len(fila_duas["pistas"]) == 2,
        "fila vazia não quebra":
            lambda: fundir_pistas({}, [p1])[1] == 1,
        "as 27 UFs têm nome":
            lambda: len(UFS) == 27 and all(uf in UF_NOME for uf in UFS),
        "toda consulta tem identificador único":
            lambda: len({i for i, _ in CONSULTAS}) == len(CONSULTAS),
        "toda consulta nomeia o estado":
            lambda: all("{nome}" in molde for _, molde in CONSULTAS),
        "consultas de uma UF saem formatadas":
            lambda: all(UF_NOME["MT"] in q for _, q in consultas_de("MT")),
        "acréscimo de canal 4 só existe onde foi confirmado":
            lambda: all(isinstance(v, list) and v for v in ACRESCIMOS_DE_CANAL4.values()),
        # Regra mínima (02/10/2026): o canal 4 de QUALQUER unidade tem o diário, e tem a raiz da
        # secretaria quando ela responde.
        "regra mínima: a raiz confirmada entra como endereço":
            lambda: fontes_de("GO", {"uf": {"GO": {"canais_instrumento": "https://saude.go.gov.br/"}}})
                    ["enderecos"] == ["https://saude.go.gov.br/"],
        "regra mínima: o diário entra como nota em toda unidade":
            lambda: any("diário oficial do estado" in n
                        for n in fontes_de("XX", {})["notas"]),
        "regra mínima: raiz sem endereço confirmado declara o motivo medido":
            lambda: any("não resolve" in n for n in fontes_de(
                "RO", {"uf": {"RO": {"canais_instrumento": None,
                                     "canais_instrumento_lacuna": "não resolve no DNS"}}})["notas"]),
        "raiz de acesso humano não é visitada pelo robô, e fica declarada":
            lambda: (fontes_de("PB", {"uf": {"PB": {"canais_instrumento": None}}})["enderecos"] == []
                     and any("verificação humana" in n for n in fontes_de(
                         "PB", {"uf": {"PB": {"canais_instrumento": None}}})["notas"])),
        "acréscimo nominal entra depois da raiz":
            lambda: fontes_de("PA", {"uf": {"PA": {"canais_instrumento": "https://www.saude.pa.gov.br/"}}})
                    ["enderecos"][0] == "https://www.saude.pa.gov.br/",
        # Decisão fora do vocabulário fechado do log faz o portão de consistência reprovar a
        # rodada inteira, e "nada localizado" em particular tem dono: a bateria MUNICIPAL.
        "toda decisão interna tem tradução no vocabulário do log":
            lambda: set(DECISAO_NO_LOG) >= {"pista", "bateria_sem_pista", "motor_sem_resposta",
                                            "fontes_lidas", "fonte_fora_do_ar", "fonte_nao_declarada"},
        "nenhuma decisão vira 'nada localizado', que é da bateria municipal":
            lambda: "nada localizado" not in DECISAO_NO_LOG.values(),
        # TRAVA DE NASCENÇA, no mesmo formato que o outro coletor da mesma fila cobra por assert.
        "pista nasce não confirmada":
            lambda: nascida["documento_oficial_confirmado"] is None,
        "pista nasce não promovível":
            lambda: nascida["promovivel"] is False,
        "pista nasce pendente de confirmação":
            lambda: nascida["status"] == "pendente_confirmacao_documento",
        # TRAVA ESTRUTURAL, conferida no próprio fonte: este coletor não pode ganhar, numa edição
        # futura, uma escrita no banco. Não basta "hoje não escrevo" — o portão tem de perceber.
        "o fonte não grava em nenhum arquivo do banco":
            lambda: not any(destino in fonte_do_coletor()
                            for destino in ('gravar("saude_uf', 'gravar("monitor_saude',
                                            'gravar("indice', 'gravar("estados',
                                            'gravar("municipios')),
        # CANAL 3: o coletor segue o que o sítio declara, e não um caminho plausível.
        "link declarado pelo sítio é seguido, com endereço absoluto":
            lambda: ("https://saude.ac.gov.br/cievs" in [u for _, u in achados]
                     and "https://saude.ac.gov.br/plano-de-contingencia.pdf"
                     in [u for _, u in achados]),
        "link fora dos termos de canal não entra":
            lambda: all("transparencia" not in u for _, u in achados),
        "link repetido entra uma vez":
            lambda: len([u for _, u in achados if u.endswith("/cievs")]) == 1,
        "esquema que não é http não entra":
            lambda: all(u.lower().startswith("http") for _, u in achados),
        "página vazia não produz link, e não quebra":
            lambda: links_de_interesse("", "https://saude.ac.gov.br/") == []
                    and links_de_interesse(None, "https://saude.ac.gov.br/") == [],
        # CANAL 2: a trava é a mesma do canal 1 — zero acerto nunca é ausência de instrumento.
        "termo de saúde no DOE é outro conjunto, não o da defesa civil":
            lambda: "homologa situação de emergência" not in TERMOS_DOE_SAUDE
                    and "plano de contingência" in TERMOS_DOE_SAUDE,
        # O canal 2 reconhece TODO adaptador direto declarado, e não só o da plataforma comum:
        # foi o que limitou a primeira varredura a cinco UFs.
        "o canal 2 reconhece os três adaptadores diretos do diário":
            lambda: all(f'"{a}"' in fonte_do_coletor()
                        for a in ("apifront", "dodf", "busca_to")),
        "todo canal novo tem tradução no vocabulário do log":
            lambda: set(DECISAO_NO_LOG) >= {"doe_sem_pista", "canais_sem_pista",
                                            "canal_nao_disponivel", "canal_nao_declarado",
                                            "canal_fora_do_ar"},
        # Canal que não rodou não pode virar "consultado sem achado": é erro, e a UF segue
        # não verificada por ele.
        "canal indisponível, não declarado ou fora do ar é erro, nunca 'consultado sem achado'":
            lambda: all(DECISAO_NO_LOG[d] == "erro" for d in ("canal_nao_disponivel",
                                                              "canal_nao_declarado",
                                                              "canal_fora_do_ar")),
        "o fonte grava só na fila de pistas":
            lambda: sorted(set(re.findall(r'gravar\((PISTAS|"[^"]+")', fonte_do_coletor()))) == ["PISTAS"],
    }
    return rodar_autoteste(casos)


def main() -> int:
    args = sys.argv[1:]
    if "--autoteste" in args:
        return autoteste()
    alvo = None
    if "--uf" in args:
        alvo = args[args.index("--uf") + 1].upper()
    ufs = [alvo] if alvo else list(UFS)

    if "--canais" in args:
        for uf in ufs:
            print(canais_ses(uf))
        return 0
    if "--doe" in args:
        desde = args[args.index("--desde") + 1] if "--desde" in args else "2026-06-29"
        for uf in ufs:
            print(doe_saude(uf, desde))
        return 0
    if "--fontes" in args:
        for uf in ufs:
            print(ler_fontes(uf))
        return 0
    if "--bateria" in args:
        try:
            buscar_searxng("teste", timeout=8)
        except Exception as e:
            print(f"✗ SearXNG indisponível em {SEARXNG_URL} ({type(e).__name__}). A busca aberta roda "
                  f"na Action, que sobe a instância no próprio job. Nada foi gravado — silêncio de "
                  f"motor ausente não entra no banco como ausência de plano.")
            return 1
        for uf in ufs:
            print(bateria(uf))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
