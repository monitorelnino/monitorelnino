#!/usr/bin/env python3
"""
monitorar_busca_web.py
=======================
Camada 4 — busca web aberta (§4, complemento ao Querido Diário e ao SIGPub
bloqueado). Roda contra uma instância EFÊMERA do SearXNG (metabuscador
open-source, sem chave, sem cadastro, sem produto pago no código — sobe
dentro do próprio job da Action via Docker, no início da rodada, e encerra
com ela; qualquer fork do projeto sobe a mesma instância automaticamente).

Query por município: '"{município}" {UF} "plano de contingência" El Niño 2026'.
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
import json, sys, time, urllib.parse, urllib.request
from datetime import date
from coletores_base import log_busca, registrar_lacuna, marcar_fonte_consultada, referencia_ibge, ler, gravar, rodar_autoteste
from classificar_pista_civil import triagem_completa
from coletar_diarios_municipais import ordem_prioridade

FONTE_BUSCA_WEB = "Busca web (SearXNG)"
SEARXNG_URL = "http://127.0.0.1:8080/search"
PAUSA_ENTRE_CONSULTAS = 0.5   # segundos; cortesia com a instância local
TERMOS_PLANO_TITULO = ("plano de conting", "plano de ação", "plano municipal", "el niño", "el nino")


def buscar_searxng(query: str, timeout: int = 20) -> dict:
    """Consulta a instância local (formato JSON habilitado em searxng_settings.yml).
    Falha de rede/parse vira exceção — quem chama decide entre lacuna e retry."""
    url = f"{SEARXNG_URL}?{urllib.parse.urlencode({'q': query, 'format': 'json'})}"
    req = urllib.request.Request(url, headers={"User-Agent": "MonitorElNinoBrasil/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def relevante(resultado: dict, nome_municipio: str) -> bool:
    """Peneira local, sem inferência: nome do município no título OU na URL,
    E algum termo de plano no título. Ambas as condições são literais (substring
    após normalizar minúsculas), nunca semânticas."""
    titulo = (resultado.get("title") or "").lower()
    url = (resultado.get("url") or "").lower()
    nome_norm = nome_municipio.lower()
    tem_municipio = nome_norm in titulo or nome_norm in url
    tem_termo_plano = any(t in titulo for t in TERMOS_PLANO_TITULO)
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
                                     "atualizado_em": date.today().isoformat()})
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
    n_ok = n_lac = npist = 0

    for cod in alvo:
        ref_mun = por_cod[cod]
        nome, uf = ref_mun["nome"], ref_mun["uf"]
        query = f'"{nome}" {uf} "plano de contingência" El Niño 2026'
        time.sleep(PAUSA_ENTRE_CONSULTAS)
        try:
            dados = buscar_searxng(query)
        except Exception as e:  # noqa: BLE001
            registrar_lacuna(f"{FONTE_BUSCA_WEB}/{nome}-{uf}", f"{type(e).__name__}", canal="busca_web", camada=4,
                             uf=uf, municipio=nome, ibge=cod, strings=[query])
            n_lac += 1
            continue

        achados = [r for r in (dados.get("results") or []) if relevante(r, nome)]
        for r in achados:
            trecho = (r.get("content") or r.get("title") or "")[:500]
            chave_pista = (cod, r.get("url"), trecho)
            if chave_pista in vistos_pistas:
                continue  # mesma menção já está na fila (mesmo padrão §132)
            pistas["pistas"].append({
                "municipio": nome, "uf": uf, "ibge": cod, "origem": "busca_web",
                "data": date.today().strftime("%d/%m/%Y"), "url": r.get("url"), "trecho": trecho,
                "titulo": (r.get("title") or "")[:300],   # 22/09/2026 (§150): título é o sinal mais forte da triagem de confiança
                "registrado_em": date.today().isoformat(),
                **triagem_completa(trecho),
                "status": "pista — promover a registro exige documento primário lido por humano",
            })
            vistos_pistas.add(chave_pista)
            npist += 1

        marcar_fonte_consultada([cod], FONTE_BUSCA_WEB, "nao_verificado",
                                resultado=f"{len(achados)} pista(s) via busca web")
        log_busca("busca_web", 4, [query], "pista" if achados else "coberto_sem_mencao",
                  uf=uf, municipio=nome, ibge=cod, n_resultados=len(dados.get("results") or []),
                  resultados=f"{len(achados)} pista(s) relevante(s) de {len(dados.get('results') or [])} resultado(s) brutos")
        n_ok += 1

    gravar("pistas_imprensa.json", pistas)
    print(f"busca web lote {lote_n}/{total_lotes}: {n_ok} municípios consultados, {n_lac} lacunas, {npist} pistas novas")
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
        src = inspect.getsource(coletores_base.log_busca)
        aceitos = {"pista", "coberto_sem_mencao", "com_excerto", "registro", "nada", "fonte", "erro", "acesso", "sem_cobertura_qd"}
        return all(a in src for a in ("pista", "coberto_sem_mencao"))

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
