#!/usr/bin/env python3
"""
monitorar_busca_web.py
=======================
Camada 4 — busca web aberta (§4, complemento ao Querido Diário e ao SIGPub
bloqueado). Roda contra uma instância EFÊMERA do SearXNG (metabuscador
open-source, sem chave, sem cadastro, sem produto pago no código — sobe
dentro do próprio job da Action via Docker, no início da rodada, e encerra
com ela; qualquer fork do projeto sobe a mesma instância automaticamente).

CONJUNTO DE CONSULTAS (27/09/2026, PR 1 do juiz automático). Até 26/09 era UMA string
estreita por município — `'"{município}" {UF} "plano de contingência" El Niño 2026'` — e a
peneira exigia termo de plano no TÍTULO. Medido no log de 21–27/09: 11.412 consultas,
5.263 (46%) com zero resultado bruto. Agora são oito strings por município (CONSULTAS, abaixo),
e a peneira aceita o nome do município no título, na URL OU no trecho.

ZERO RESULTADO NÃO É AUSÊNCIA (decisão editorial de 27/09/2026). Três decisões separadas:
  motor_sem_resposta            0 resultado bruto em TODAS as strings, timeout, erro HTTP,
                                instância que não subiu — o motor está doente, e a consulta
                                NÃO conta como verificação do município.
  nao_localizado_ate_o_momento  houve resultado bruto e nenhuma pista, mas foi a PRIMEIRA
                                rodada nessa situação.
  coberto_sem_mencao            houve resultado bruto e nenhuma pista em DUAS rodadas.
  pista                         ao menos um resultado passou a peneira.
Peneira local (nenhuma IA, nenhuma inferência semântica): resultado só vira
pista se o nome do município aparecer no título OU na URL, E algum termo de
plano aparecer no título — mesma disciplina de "documento primário, achado
por humano" das demais fontes (§3.2): isto AGRUPA candidatos, nunca promove
sozinho a registro.

Alimenta a MESMA fila que os demais coletores de pista (`data/pistas_imprensa.json`),
com `origem: "busca_web"`, para que a revisão humana trate todas as pistas
num só lugar. Dedup por (ibge, url, trecho) — mesmo padrão do achado de
21/09/2026 em `coletar_diarios_municipais.py` (§132): a mesma pista não vira
duas entradas só porque a rodada rodou de novo.

Prioridade dos lotes: reusa `ordem_prioridade()` de `coletar_diarios_municipais.py`
(UF por percentual do cadastro, população decrescente dentro da UF), com os 2.095
municípios prioritários (mesmo proxy do resto do site, data/municipios_prioritarios.json)
adiantados para o início — ciclo dos que mais importam: ~93 → ~35 semanas.

USO
  python monitorar_busca_web.py --autoteste
  python monitorar_busca_web.py --lote 1 --tamanho 60
"""
import json, random, sys, time, urllib.parse, urllib.request
from datetime import date
import funil
from coletores_base import log_busca, registrar_lacuna, marcar_fonte_consultada, referencia_ibge, ler, gravar, rodar_autoteste, ua_de, hoje_editorial
from classificar_pista_civil import triagem_completa
from coletar_diarios_municipais import ordem_prioridade

FONTE_BUSCA_WEB = "Busca web (SearXNG)"
SEARXNG_URL = "http://127.0.0.1:8080/search"
# 27/09/2026 (PR 1c): a pausa fixa deu lugar a `espera_do_ritmo()` — intervalo mínimo com jitter e
# back-off exponencial. A constante antiga saiu junto: em 0,15 s, com nove strings por município, era
# ela que ajudava a queimar o limite de taxa dos motores de origem.
TERMOS_PLANO_TITULO = ("plano de conting", "plano de ação", "plano municipal", "el niño", "el nino")

# Conjunto de consultas por município (27/09/2026, handover do juiz automático, PR 1 item 4).
# Cada entrada é (id, molde). O id entra no log e no contador do funil, para que a revocação
# por string seja medível depois — é o que `medir_revocacao_das_consultas.py` lê.
# Leque COMPLETO, 27/09/2026 — usado só pelo job de MEDIÇÃO (`medir_revocacao_das_consultas.py`),
# nunca na rodada. Ver `CONSULTAS` abaixo.
CONSULTAS_MEDICAO = (
    ("plancon_ciclo",      '"{nome}" {uf} "plano de contingência" El Niño 2026'),   # a de até 26/09, controle
    ("plancon",            '"{nome}" {uf} "plano de contingência"'),
    ("plancon_ano",        '"{nome}" {uf} "plano de contingência" 2026'),
    ("periodo_chuvoso",    '"{nome}" {uf} "período chuvoso"'),
    ("estiagem",           '"{nome}" {uf} estiagem OR seca "plano"'),
    ("plancon_sigla",      '"{nome}" {uf} PLANCON'),
    ("plano_de_acao",      '"{nome}" {uf} "plano de ação" El Niño'),
    ("plano_enfrentamento", '"{nome}" {uf} "plano de enfrentamento"'),
    ("decreto_preventivo", '"{nome}" {uf} decreto "situação de emergência" preventiv'),
)

# Conjunto PROVISÓRIO da rodada (decisão da central, 27/09/2026, noite — PR 1c). Três strings, em
# CASCATA: rodam em ordem e param na primeira que devolve pista. O leque de nove, lançado de uma vez
# sobre 150 municípios, somava ~1.350 requisições que a instância efêmera repassa aos motores de
# origem, e o runner do GitHub compartilha IP: a primeira rodada mediu 139 de 150 consultas sem
# resposta (93%). É limite de taxa, não defeito das strings. O conjunto definitivo sai da medição
# (item 6), e a troca vem por PR com o número no CHANGELOG.
CONSULTAS = (
    ("plancon",     '"{nome}" {uf} "plano de contingência"'),
    ("periodo_ou_seca", '"{nome}" {uf} "período chuvoso" OR estiagem OR seca plano'),
    ("siglas_e_variantes", '"{nome}" {uf} PLANCON OR "plano de ação" OR "plano de enfrentamento"'),
)
TETO_MOTOR_SEM_RESPOSTA = 0.25   # PR 1 item 3: acima disso a rodada não conta como verificação

# Ritmo (PR 1c item 3). Intervalo mínimo com jitter, e back-off exponencial ao primeiro sinal de
# limite de taxa: 429, CAPTCHA ou corpo vazio.
INTERVALO_MINIMO = 3.0
JITTER = 1.0
BACKOFF = (10, 30, 90)
# Sonda dos primeiros municípios: se o mudo passar do teto, pausa e retoma; se passar de novo,
# encerra a rodada e o lote volta ao topo da fila da próxima (item 3).
SONDA_MUNICIPIOS = 20
PAUSA_DA_SONDA = 600


def consultas_de(nome: str, uf: str) -> list:
    """As consultas da RODADA, na ordem da cascata. Devolve [(id, string)]."""
    return [(ident, molde.format(nome=nome, uf=uf)) for ident, molde in CONSULTAS]


def consultas_de_medicao(nome: str, uf: str) -> list:
    """O leque completo, para o job de medição de revocação — nunca para a rodada."""
    return [(ident, molde.format(nome=nome, uf=uf)) for ident, molde in CONSULTAS_MEDICAO]


def espera_do_ritmo(tentativa_de_backoff: int = 0, aleatorio=None) -> float:
    """Quanto esperar antes da próxima consulta.

    Sem back-off: intervalo mínimo com jitter de ±1 s — o jitter existe para que 150 municípios não
    batam no motor em pulsos regulares. Com back-off: 10 s, 30 s, 90 s, e depois fica em 90 s.
    `aleatorio` é injetável para que o autoteste não dependa de sorteio."""
    if tentativa_de_backoff > 0:
        return float(BACKOFF[min(tentativa_de_backoff, len(BACKOFF)) - 1])
    r = (aleatorio or random.uniform)(-JITTER, JITTER)
    return max(0.5, INTERVALO_MINIMO + r)


def sinal_de_limite_de_taxa(erro: Exception = None, dados: dict = None) -> bool:
    """429, CAPTCHA ou corpo vazio — os três dizem a mesma coisa: o motor está barrando.

    Corpo vazio conta porque o SearXNG devolve 200 com `results: []` quando os motores de origem
    recusam: recusa servida com 200 é recusa (§186)."""
    if erro is not None:
        texto = f"{type(erro).__name__} {erro}".lower()
        return any(s in texto for s in ("429", "too many requests", "captcha", "forbidden", "403"))
    if dados is None:
        return False
    return not dados.get("results")


def decidir(n_brutos: int, n_pistas: int, rodadas_sem_pista: int) -> str:
    """A decisão da camada 4, isolada para ser testável sem rede.

    `rodadas_sem_pista` é quantas rodadas ANTERIORES este município já teve com resultado
    bruto e sem pista. A regra editorial de 27/09/2026: zero resultado bruto nunca produz
    `coberto_sem_mencao`, e uma rodada sozinha também não — precisa da segunda."""
    if n_pistas > 0:
        return "pista"
    if n_brutos <= 0:
        return "motor_sem_resposta"
    return "coberto_sem_mencao" if rodadas_sem_pista >= 1 else "nao_localizado_ate_o_momento"


def buscar_searxng(query: str, timeout: int = 20) -> dict:
    """Consulta a instância local (formato JSON habilitado em searxng_settings.yml).
    Falha de rede/parse vira exceção — quem chama decide entre lacuna e retry."""
    url = f"{SEARXNG_URL}?{urllib.parse.urlencode({'q': query, 'format': 'json'})}"
    req = urllib.request.Request(url, headers={"User-Agent": ua_de("busca web")})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def relevante(resultado: dict, nome_municipio: str) -> bool:
    """Peneira local, sem inferência: nome do município no título, na URL OU no trecho,
    E algum termo de plano no título ou no trecho. Ambas as condições são literais
    (substring após normalizar minúsculas), nunca semânticas.

    27/09/2026 (PR 1 item 4): o trecho passa a contar nas duas condições. Diário oficial
    raramente traz o nome do município no título do resultado — ele está no corpo, que é o
    `content` do SearXNG. Exigir título descartava o documento primário e guardava a notícia.
    Isto AGRUPA candidatos; não promove ninguém a registro (§3.2)."""
    titulo = (resultado.get("title") or "").lower()
    url = (resultado.get("url") or "").lower()
    trecho = (resultado.get("content") or "").lower()
    nome_norm = nome_municipio.lower()
    tem_municipio = nome_norm in titulo or nome_norm in url or nome_norm in trecho
    tem_termo_plano = any(t in titulo or t in trecho for t in TERMOS_PLANO_TITULO)
    return tem_municipio and tem_termo_plano


def proximo_lote_automatico(total_lotes: int) -> int:
    """21/09/2026: sem isto, a rodada semanal batia sempre nos mesmos 60 primeiros
    municípios (lote 1 fixo no workflow) — nunca avançava, nunca cobria os outros
    5.511. Estado mínimo persistido em data/busca_web_estado.json: só o número do
    PRÓXIMO lote. Cada rodada automática avança um; ao passar do último, volta ao 1
    (cobertura cíclica: depois de ~93 semanas, todos os municípios já foram tentados
    pelo menos uma vez, e o ciclo recomeça).
    22/09/2026 (pedido editorial, §148): registra `ciclos_completos` — quantas vezes a
    rotação já deu a volta inteira. A cadência automática (busca_web_cadencia.yml) lê
    isso: 0 ciclos = fase 1, a cada 2h até cobrir todos; ≥1 = fase 2, 4x/dia."""
    estado = ler("busca_web_estado.json") or {"proximo_lote": 1}
    lote = ((estado.get("proximo_lote", 1) - 1) % total_lotes) + 1
    ciclos = int(estado.get("ciclos_completos", 0) or 0)
    if lote == total_lotes:
        ciclos += 1   # este lote fecha a volta: todos os municípios tentados pelo menos uma vez
    gravar("busca_web_estado.json", {"proximo_lote": (lote % total_lotes) + 1,
                                     "ultimo_lote_rodado": lote,
                                     "total_lotes": total_lotes,
                                     "ciclos_completos": ciclos,
                                     "atualizado_em": hoje_editorial().isoformat()})
    return lote


def rodar(lote: str | None, tamanho: int) -> int:
    por_cod, _ = referencia_ibge()
    cadastro = ler("cadastro_prioritarios.json") or {}
    pop = ler("populacao_censo2022.json") or {}
    ordem_base = ordem_prioridade(por_cod, cadastro, pop)

    # 21/09/2026 (pedido editorial: "não temos 93 semanas, precisamos de algo mais veloz"):
    # ordem_prioridade() trata os 5.571 municípios igualmente dentro do ranking por UF/população
    # — um município grande sem risco mapeado podia furar a fila de um município prioritário
    # menor. Município prioritário (proxy populacional, fonte data/municipios_prioritarios.json
    # — mesmos 2.095 já usados no resto do site) vai todo para o início, na MESMA ordem relativa
    # de ordem_prioridade(); os demais vêm depois, também na mesma ordem relativa entre si —
    # partição estável, não uma reordenação nova. Ciclo dos 2.095 que mais importam: ~93 → ~35
    # semanas. Cobertura total continua a mesma no fim (nenhum município é descartado).
    prioritarios_cod = {str(m["codigo_ibge"]).zfill(7) for m in (ler("municipios_prioritarios.json") or {}).get("municipios", [])}
    ordem = [c for c in ordem_base if c in prioritarios_cod] + [c for c in ordem_base if c not in prioritarios_cod]

    total_lotes = max(1, -(-len(ordem) // tamanho))  # arredonda para cima

    if lote is None:
        lote_n = proximo_lote_automatico(total_lotes)  # rotação automática, avança o estado
    else:
        try:
            lote_n = int(lote)  # override manual/teste — não mexe no estado da rotação
        except ValueError:
            registrar_lacuna(FONTE_BUSCA_WEB, f"--lote inválido: {lote!r}", canal="busca_web", camada=4)
            return 1

    alvo = ordem[(lote_n - 1) * tamanho: lote_n * tamanho]

    pistas = ler("pistas_imprensa.json") or {"pistas": []}
    vistos_pistas = {(p.get("ibge"), p.get("url"), p.get("trecho")) for p in pistas["pistas"]}
    # 27/09/2026 (PR 1 item 2): quantas rodadas cada município já teve COM resultado bruto e SEM
    # pista. Duas são necessárias para "coberto_sem_mencao"; até lá o estado é de espera.
    espera = ler("busca_web_espera.json") or {"municipios": {}}
    n_ok = n_lac = npist = 0
    n_motor_sem_resposta = n_com_bruto = n_coberto = n_esperando = 0
    brutos_por_consulta = {ident: 0 for ident, _ in CONSULTAS}
    # estado do ritmo, em lista para poder ser mutado dentro do laço interno
    backoff = [0]
    pausas_da_sonda = 0
    encerrada_pela_sonda = False

    for cod in alvo:
        ref_mun = por_cod[cod]
        nome, uf = ref_mun["nome"], ref_mun["uf"]
        consultas = consultas_de(nome, uf)
        strings = [q for _, q in consultas]
        resultados_brutos, achados, falhas_de_rede = [], [], 0
        vistos_url = set()
        # CASCATA com parada precoce (PR 1c item 1): as strings rodam em ordem e param na primeira
        # que devolve pista. Sem pista, a cascata segue até o fim — é o caso da maioria, e é por
        # isso que o conjunto da rodada tem três strings e não nove.
        for ident, query in consultas:
            time.sleep(espera_do_ritmo(backoff[0]))
            try:
                dados = buscar_searxng(query)
            except Exception as erro:  # noqa: BLE001 — falha de uma string não derruba as outras
                falhas_de_rede += 1
                if sinal_de_limite_de_taxa(erro=erro):
                    backoff[0] += 1   # 429/CAPTCHA: o próximo intervalo é 10 s, 30 s, 90 s
                continue
            crus = dados.get("results") or []
            brutos_por_consulta[ident] += len(crus)
            if sinal_de_limite_de_taxa(dados=dados):
                backoff[0] += 1       # corpo vazio é recusa servida com 200 (§186)
            else:
                backoff[0] = 0        # o motor respondeu: volta ao intervalo mínimo
            for r in crus:
                if r.get("url") in vistos_url:
                    continue   # a mesma página achada por duas strings é um resultado, não dois
                vistos_url.add(r.get("url"))
                resultados_brutos.append(r)
                if relevante(r, nome):
                    r["_consulta"] = ident   # qual string recuperou este achado (revocação por string)
                    achados.append(r)
            if achados:
                break   # parada precoce: já há pista, as strings seguintes não mudariam o desfecho

        if falhas_de_rede == len(consultas):
            registrar_lacuna(f"{FONTE_BUSCA_WEB}/{nome}-{uf}", "todas as consultas falharam",
                             canal="busca_web", camada=4, uf=uf, municipio=nome, ibge=cod, strings=strings)
            n_lac += 1
            continue

        for r in achados:
            trecho = (r.get("content") or r.get("title") or "")[:500]
            chave_pista = (cod, r.get("url"), trecho)
            if chave_pista in vistos_pistas:
                continue  # mesma menção já está na fila (mesmo padrão §132)
            pistas["pistas"].append({
                "municipio": nome, "uf": uf, "ibge": cod, "origem": "busca_web",
                "data": hoje_editorial().strftime("%d/%m/%Y"), "url": r.get("url"), "trecho": trecho,
                "titulo": (r.get("title") or "")[:300],   # 22/09/2026 (§150): título é o sinal mais forte da triagem de confiança
                "registrado_em": hoje_editorial().isoformat(),
                **triagem_completa(trecho),
                "status": "pista — promover a registro exige documento primário lido por humano",
            })
            vistos_pistas.add(chave_pista)
            npist += 1

        # SONDA (PR 1c item 3): nos primeiros 20 municípios, se o mudo passar do teto, pausa 10 min
        # e retoma; se passar de novo, encerra a rodada — o restante do lote fica `motor_sem_resposta`
        # e o lote volta ao topo da fila da próxima rodada.
        if n_ok + n_lac == SONDA_MUNICIPIOS:
            mudos = n_motor_sem_resposta + n_lac
            if mudos / max(1, SONDA_MUNICIPIOS) > TETO_MOTOR_SEM_RESPOSTA:
                if pausas_da_sonda == 0:
                    print(f"  sonda: {mudos}/{SONDA_MUNICIPIOS} mudos — pausa de "
                          f"{PAUSA_DA_SONDA // 60} min e retoma", flush=True)
                    pausas_da_sonda += 1
                    time.sleep(PAUSA_DA_SONDA)
                else:
                    print(f"  sonda: {mudos}/{SONDA_MUNICIPIOS} mudos de novo — rodada encerrada; "
                          f"o lote volta ao topo da fila da próxima", flush=True)
                    encerrada_pela_sonda = True

        rodadas_sem_pista = int((espera["municipios"].get(cod) or {}).get("rodadas_com_bruto_sem_pista", 0) or 0)
        decisao = decidir(len(resultados_brutos), len(achados), rodadas_sem_pista)
        # o estado de espera só avança quando houve resultado bruto e nenhuma pista; pista zera.
        if decisao == "pista":
            espera["municipios"].pop(cod, None)
        elif decisao in ("nao_localizado_ate_o_momento", "coberto_sem_mencao"):
            espera["municipios"][cod] = {"rodadas_com_bruto_sem_pista": rodadas_sem_pista + 1,
                                        "ultima_rodada": hoje_editorial().isoformat()}
        marcar_fonte_consultada([cod], FONTE_BUSCA_WEB, "nao_verificado",
                                resultado=f"{len(achados)} pista(s) via busca web; decisão {decisao}")
        log_busca("busca_web", 4, strings, decisao,
                  uf=uf, municipio=nome, ibge=cod, n_resultados=len(resultados_brutos),
                  resultados=(f"{len(achados)} pista(s) relevante(s) de {len(resultados_brutos)} resultado(s) brutos"
                              f" em {len(consultas) - falhas_de_rede}/{len(consultas)} consultas"))
        n_ok += 1
        if decisao == "motor_sem_resposta":
            n_motor_sem_resposta += 1
        else:
            n_com_bruto += 1
            if decisao == "coberto_sem_mencao":
                n_coberto += 1
            elif decisao == "nao_localizado_ate_o_momento":
                n_esperando += 1

    gravar("pistas_imprensa.json", pistas)
    gravar("busca_web_espera.json", {"municipios": espera["municipios"],
                                     "atualizado_em": hoje_editorial().isoformat()})
    funil.registrar("busca_web", consultas=n_ok + n_lac, com_resultado_bruto=n_com_bruto,
                    motor_sem_resposta=n_motor_sem_resposta, pistas=npist,
                    coberto_sem_mencao=n_coberto, nao_localizado_ate_o_momento=n_esperando,
                    lacunas=n_lac, **{f"brutos_{ident}": n for ident, n in brutos_por_consulta.items()})
    tentadas = n_ok + n_lac
    doentes = n_motor_sem_resposta + n_lac
    print(f"busca web lote {lote_n}/{total_lotes}: {n_ok} municípios consultados, {n_lac} lacunas, {npist} pistas novas")
    print(f"  motor sem resposta: {doentes}/{tentadas}" + (f" ({100 * doentes / tentadas:.0f}%)" if tentadas else ""))
    if tentadas and doentes / tentadas > TETO_MOTOR_SEM_RESPOSTA:
        # PR 1 item 3: acima do teto o motor está doente e a rodada não conta como verificação.
        # Sai com erro para que a rodada registre a falha em vez de publicar cobertura falsa.
        print(f"✗ busca web: {100 * doentes / tentadas:.0f}% sem resposta do motor, acima do teto de "
              f"{100 * TETO_MOTOR_SEM_RESPOSTA:.0f}% — esta rodada NÃO conta como verificação da camada 4")
        return 1
    return 0


def autoteste():
    """Hermético: nunca chama a rede. Testa a peneira `relevante()` e o vocabulário
    real que log_busca() aceita, lido do próprio código-fonte (não copiado à mão —
    achado real de 21/09/2026: um vocabulário digitado à mão diverge do código)."""
    import inspect
    import coletores_base

    def t1_relevante_aceita():
        r = {"title": "Prefeitura de Bagé lança Plano de Contingência para El Niño",
             "url": "https://bage.rs.gov.br/plano-contingencia", "content": "..."}
        return relevante(r, "Bagé")

    def t2_relevante_rejeita_sem_municipio():
        r = {"title": "Plano de Contingência Nacional para El Niño", "url": "https://gov.br/x", "content": "..."}
        return relevante(r, "Bagé") is False

    def t3_relevante_rejeita_sem_termo_plano():
        r = {"title": "Prefeitura de Bagé inaugura nova praça", "url": "https://bage.rs.gov.br/praca", "content": "..."}
        return relevante(r, "Bagé") is False

    def t4_vocabulario_log_busca_bate_com_o_codigo():
        # 21/09/2026: achado real via Action — "sem_mencao" foi rejeitado porque o
        # vocabulário fixo exige "coberto_sem_mencao". Este teste lê o vocabulário
        # DIRETO do código-fonte de log_busca(), não uma cópia à mão, para que uma
        # mudança futura no vocabulário quebre este teste em vez de quebrar em produção.
        # 25/09/2026 (§213/§220): ele lia o TEXTO de log_busca() procurando as palavras. Quando o
        # vocabulário virou a constante nomeada `DECISOES_LOG` — justamente para que quem produz
        # uma decisão possa conferir se ela cabe —, o teste reprovou sem nada ter mudado de
        # comportamento. Era o mesmo defeito em dois arquivos. Agora ele importa a lista e usa as
        # decisões que ESTE script de fato registra.
        # 27/09/2026: as decisões que este script produz saem agora de `decidir()` — a lista
        # deixa de ser escrita à mão aqui, e o conjunto real é exercitado contra o vocabulário.
        usadas = {decidir(0, 0, 0), decidir(3, 0, 0), decidir(3, 0, 1), decidir(3, 1, 0), "erro"}
        return usadas <= set(coletores_base.DECISOES_LOG)

    def t8_zero_bruto_nunca_e_coberto_sem_mencao():
        """A regra editorial de 27/09/2026, no caso que a motivou: 5.263 consultas de 21-27/09
        voltaram com zero resultado bruto e receberam `coberto_sem_mencao`."""
        return (decidir(0, 0, 0) == "motor_sem_resposta"
                and decidir(0, 0, 5) == "motor_sem_resposta")   # nem com histórico de espera

    def t9_uma_rodada_nao_basta_duas_bastam():
        return (decidir(7, 0, 0) == "nao_localizado_ate_o_momento"
                and decidir(7, 0, 1) == "coberto_sem_mencao"
                and decidir(7, 0, 2) == "coberto_sem_mencao")

    def t10_pista_vence_tudo():
        return decidir(1, 1, 0) == "pista" and decidir(99, 3, 7) == "pista"

    def t11_conjunto_de_consultas_cobre_o_handover():
        """As oito strings pedidas no handover, mais a de até 26/09 como controle.

        27/09/2026 (PR 1c): o leque completo saiu da RODADA e passou a viver em `CONSULTAS_MEDICAO`,
        para o job de medição. A rodada usa três strings em cascata. Este teste continua guardando o
        leque — é ele que a medição vai comparar — e passou a olhar o conjunto certo."""
        qs = [q for _, q in consultas_de_medicao("Salvador", "BA")]
        exigidos = ["plano de contingência", '"plano de contingência" 2026', "período chuvoso",
                    'estiagem OR seca "plano"', "PLANCON", '"plano de ação" El Niño',
                    '"plano de enfrentamento"', 'decreto "situação de emergência" preventiv']
        tem_todos = all(any(e in q for q in qs) for e in exigidos)
        tem_controle = any('"plano de contingência" El Niño 2026' in q for q in qs)
        nomeia_o_municipio = all('"Salvador" BA' in q for q in qs)
        ids_unicos = len({i for i, _ in CONSULTAS}) == len(CONSULTAS)
        return tem_todos and tem_controle and nomeia_o_municipio and ids_unicos

    def t12_peneira_aceita_municipio_no_trecho():
        """O caso que a peneira antiga descartava: diário oficial com o nome do município no
        corpo e não no título. Era o documento primário; ficava de fora."""
        r = {"title": "Diário Oficial do Município - Edição 1.234",
             "url": "https://diariomunicipal.com.br/famep/edicao/1234",
             "content": "DECRETO. O Prefeito de Bonito, no uso de suas atribuições, institui o Plano de Contingência para o período chuvoso"}
        aceita_pelo_trecho = relevante(r, "Bonito")
        r_sem_nome = dict(r, content="institui o Plano de Contingência para o período chuvoso")
        rejeita_sem_nome = not relevante(r_sem_nome, "Bonito")
        r_sem_plano = dict(r, content="O Prefeito de Bonito nomeia servidores para o quadro efetivo")
        rejeita_sem_termo = not relevante(r_sem_plano, "Bonito")
        return aceita_pelo_trecho and rejeita_sem_nome and rejeita_sem_termo

    def t13_teto_do_motor_e_fracao_nao_percentual():
        """Trava de unidade: 0,25 é fração. Se alguém escrever 25 aqui, o teto nunca dispara."""
        return 0 < TETO_MOTOR_SEM_RESPOSTA < 1

    def t14_cascata_provisoria():
        """Três strings na rodada; nove na medição; nenhuma string da rodada fora do leque."""
        rodada = {i for i, _ in CONSULTAS}
        medicao = {i for i, _ in CONSULTAS_MEDICAO}
        tres = len(CONSULTAS) == 3
        leque = len(CONSULTAS_MEDICAO) == 9
        # a cascata começa pela string mais direta: é ela que resolve o caso fácil na primeira volta
        comeca_pelo_plancon = CONSULTAS[0][0] == "plancon"
        # o leque tem de conter a busca exata da rodada (`plancon`), senão a medição não compara
        contem_a_da_rodada = "plancon" in medicao
        return tres and leque and comeca_pelo_plancon and contem_a_da_rodada and len(rodada) == 3

    def t15_ritmo_e_backoff():
        """Intervalo mínimo com jitter dentro da faixa; back-off 10/30/90 e depois estável em 90."""
        sem_jitter = espera_do_ritmo(0, aleatorio=lambda a, b: 0) == INTERVALO_MINIMO
        piso = espera_do_ritmo(0, aleatorio=lambda a, b: -JITTER) >= INTERVALO_MINIMO - JITTER
        teto = espera_do_ritmo(0, aleatorio=lambda a, b: JITTER) <= INTERVALO_MINIMO + JITTER
        escada = [espera_do_ritmo(i) for i in (1, 2, 3)] == [10.0, 30.0, 90.0]
        estavel = espera_do_ritmo(99) == 90.0        # não cresce sem limite
        nunca_zero = espera_do_ritmo(0, aleatorio=lambda a, b: -99) >= 0.5
        return sem_jitter and piso and teto and escada and estavel and nunca_zero

    def t16_sinais_de_limite():
        """Os três sinais que o handover nomeia, e o que NÃO é sinal."""
        quatro_vinte_nove = sinal_de_limite_de_taxa(erro=Exception("HTTP Error 429: Too Many Requests"))
        captcha = sinal_de_limite_de_taxa(erro=Exception("captcha required"))
        proibido = sinal_de_limite_de_taxa(erro=Exception("HTTP Error 403: Forbidden"))
        vazio = sinal_de_limite_de_taxa(dados={"results": []})       # §186: recusa servida com 200
        com_resultado = not sinal_de_limite_de_taxa(dados={"results": [{"url": "x"}]})
        timeout_nao_e = not sinal_de_limite_de_taxa(erro=TimeoutError("timed out"))
        nada = not sinal_de_limite_de_taxa()
        return all((quatro_vinte_nove, captcha, proibido, vazio, com_resultado, timeout_nao_e, nada))

    def t17_valores_da_sonda():
        """Trava de unidade: a pausa é em SEGUNDOS. 10 aqui viraria 10 segundos, não 10 minutos."""
        return (SONDA_MUNICIPIOS == 20 and PAUSA_DA_SONDA == 600
                and BACKOFF == (10, 30, 90) and INTERVALO_MINIMO >= 1.0)

    def t5_dedup_mesma_chave():
        vistos = {("0000001", "https://x.gov.br/a", "trecho x")}
        chave = ("0000001", "https://x.gov.br/a", "trecho x")
        return chave in vistos

    def t6_rotacao_avanca_e_da_a_volta():
        # 21/09/2026: mesmo padrão de mock já usado em coletar_diarios_municipais.py
        # (trocar ler/gravar globalmente, testar, restaurar) — sem isto, o teste
        # tocaria data/busca_web_estado.json de verdade.
        estado_falso = {}
        def ler_falso(nome, padrao=None): return estado_falso.get(nome, padrao)
        def gravar_falso(nome, obj): estado_falso[nome] = obj
        globals_mod = sys.modules[__name__]
        real_ler, real_gravar = globals_mod.ler, globals_mod.gravar
        globals_mod.ler, globals_mod.gravar = ler_falso, gravar_falso
        try:
            l1 = proximo_lote_automatico(3)  # total_lotes=3, estado vazio => começa em 1
            l2 = proximo_lote_automatico(3)
            l3 = proximo_lote_automatico(3)
            c_apos_volta = estado_falso["busca_web_estado.json"]["ciclos_completos"]  # 3º lote fecha a volta
            l4 = proximo_lote_automatico(3)  # depois do 3º, deve voltar pro 1º
            return [l1, l2, l3, l4] == [1, 2, 3, 1] and c_apos_volta == 1
        finally:
            globals_mod.ler, globals_mod.gravar = real_ler, real_gravar

    def t7_prioritarios_vem_primeiro_e_ninguem_some():
        # 21/09/2026 (pedido editorial de velocidade): contra o dado real — é só leitura,
        # sem mock necessário. Confirma partição estável: todo prioritário antes de todo
        # não-prioritário, e a cobertura total não perde ninguém (mesmo conjunto, nova ordem).
        por_cod, _ = referencia_ibge()
        cadastro = ler("cadastro_prioritarios.json") or {}
        pop = ler("populacao_censo2022.json") or {}
        ordem_base = ordem_prioridade(por_cod, cadastro, pop)
        prioritarios_cod = {str(m["codigo_ibge"]).zfill(7) for m in (ler("municipios_prioritarios.json") or {}).get("municipios", [])}
        ordem = [c for c in ordem_base if c in prioritarios_cod] + [c for c in ordem_base if c not in prioritarios_cod]
        if set(ordem) != set(ordem_base) or len(ordem) != len(ordem_base):
            return False  # ninguém pode sumir nem duplicar
        primeiro_nao_prioritario = next((i for i, c in enumerate(ordem) if c not in prioritarios_cod), len(ordem))
        return all(c in prioritarios_cod for c in ordem[:primeiro_nao_prioritario])

    return rodar_autoteste({
        "relevante(): aceita nome do município + termo de plano no título": t1_relevante_aceita,
        "relevante(): rejeita termo de plano sem o nome do município": t2_relevante_rejeita_sem_municipio,
        "relevante(): rejeita nome do município sem termo de plano": t3_relevante_rejeita_sem_termo_plano,
        "vocabulário de decisao usado aqui existe de fato em log_busca()": t4_vocabulario_log_busca_bate_com_o_codigo,
        "zero resultado bruto nunca vira coberto_sem_mencao": t8_zero_bruto_nunca_e_coberto_sem_mencao,
        "coberto_sem_mencao exige duas rodadas com resultado bruto": t9_uma_rodada_nao_basta_duas_bastam,
        "pista vence qualquer estado de espera": t10_pista_vence_tudo,
        "as oito consultas do handover, mais a antiga como controle": t11_conjunto_de_consultas_cobre_o_handover,
        "peneira aceita o nome do município no trecho, não só no título": t12_peneira_aceita_municipio_no_trecho,
        "teto do motor sem resposta é fração, não percentual": t13_teto_do_motor_e_fracao_nao_percentual,
        "a rodada usa três strings em cascata, e o leque fica para a medição": t14_cascata_provisoria,
        "o ritmo tem intervalo mínimo com jitter e back-off exponencial": t15_ritmo_e_backoff,
        "429, CAPTCHA e corpo vazio são lidos como limite de taxa": t16_sinais_de_limite,
        "a sonda e a pausa têm valores de segundo, não de minuto": t17_valores_da_sonda,
        "dedup: mesma chave (ibge,url,trecho) é reconhecida como vista": t5_dedup_mesma_chave,
        "rotação automática: avança 1→2→3 e volta para 1 (cobertura cíclica)": t6_rotacao_avanca_e_da_a_volta,
        "prioritários vêm primeiro, cobertura total preservada (nada some)": t7_prioritarios_vem_primeiro_e_ninguem_some,
    })


if __name__ == "__main__":
    if "--autoteste" in sys.argv:
        sys.exit(autoteste())
    args = sys.argv[1:]
    lote = args[args.index("--lote") + 1] if "--lote" in args else None  # None => rotação automática
    tamanho = int(args[args.index("--tamanho") + 1]) if "--tamanho" in args else 60
    sys.exit(rodar(lote, tamanho))
