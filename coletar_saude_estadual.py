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
"""
import json
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

# Fontes declaradas por UF, lidas direto no modo `--fontes`. `null` é LACUNA DECLARADA: endereço
# não confirmado, e por isso nada se afirma sobre a UF por esta rota. A lista cresce com o que for
# confirmado sítio a sítio; inventar endereço aqui produziria 404 com cara de busca feita.
FONTES_SAUDE = {
    "MT": ["https://www.saude.mt.gov.br/storage/files/MmMbtQx9n43VPO23mMookK6LdUyD6h4QfMOvqx44.pdf",
           "https://www.saude.mt.gov.br/storage/files/RDtdQBfGbCiRYiJ1BIRtq6KUg32oNI4cKBWaQaiS.pdf"],
}


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
                  "fonte_nao_declarada": "erro"}


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
    return {"alvo": f"funil-saude/{uf}", "uf": uf, "consulta": ident, "query": query,
            "titulo": resultado.get("title"), "url": resultado.get("url"),
            "trecho": (resultado.get("content") or "")[:400],
            "oficial": oficial(resultado.get("url")),
            "origem": ORIGEM, "registrado_em": hoje_editorial().strftime("%d/%m/%Y"),
            "status": "pista — promoção exige documento primário lido pelo juiz (§3.2)"}


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


def ler_fontes(uf: str) -> dict:
    """Lê as fontes declaradas de uma UF, preservando evidência. Não precisa de SearXNG."""
    enderecos = FONTES_SAUDE.get(uf) or []
    if not enderecos:
        registrar_lacuna(f"funil_saude/{uf}", "nenhuma fonte de saúde declarada para a UF",
                         canal="orgao_estadual", camada=1, uf=uf, nivel="estadual")
        return {"uf": uf, "lidos": 0, "falhas": 0, "decisao": "fonte_nao_declarada"}
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
              resultados=f"funil_saude/{uf}: {lidos} fonte(s) lida(s), {falhas} falha(s)")
    funil.registrar("funil_saude_estadual", consultas=len(enderecos),
                    com_resultado_bruto=1 if lidos else 0)
    return {"uf": uf, "lidos": lidos, "falhas": falhas, "decisao": decisao}


# =============================================================================================
# Autoteste — offline, sem rede e sem escrever em data/
# =============================================================================================
def autoteste() -> int:
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
        "fonte declarada só existe onde foi confirmada":
            lambda: all(isinstance(v, list) and v for v in FONTES_SAUDE.values()),
        # Decisão fora do vocabulário fechado do log faz o portão de consistência reprovar a
        # rodada inteira, e "nada localizado" em particular tem dono: a bateria MUNICIPAL.
        "toda decisão interna tem tradução no vocabulário do log":
            lambda: set(DECISAO_NO_LOG) >= {"pista", "bateria_sem_pista", "motor_sem_resposta",
                                            "fontes_lidas", "fonte_fora_do_ar", "fonte_nao_declarada"},
        "nenhuma decisão vira 'nada localizado', que é da bateria municipal":
            lambda: "nada localizado" not in DECISAO_NO_LOG.values(),
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
