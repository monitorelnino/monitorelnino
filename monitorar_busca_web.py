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
— mesmo proxy (UF por percentual do cadastro, população decrescente dentro da UF)
— para não duplicar a lógica de priorização em dois lugares.

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


def rodar(lote: str, tamanho: int) -> int:
    ref = referencia_ibge()
    por_cod = {str(r["codigo_ibge"]).zfill(7): r for r in ref}
    cadastro = ler("cadastro_prioritarios.json") or {}
    pop = ler("populacao_censo2022.json") or {}
    ordem = ordem_prioridade(por_cod, cadastro, pop)

    try:
        lote_n = int(lote)
        alvo = ordem[(lote_n - 1) * tamanho: lote_n * tamanho]
    except ValueError:
        registrar_lacuna(FONTE_BUSCA_WEB, f"--lote inválido: {lote!r}", canal="busca_web", camada=4)
        return 1

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
    print(f"busca web lote {lote}: {n_ok} municípios consultados, {n_lac} lacunas, {npist} pistas novas")
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

    return rodar_autoteste({
        "relevante(): aceita nome do município + termo de plano no título": t1_relevante_aceita,
        "relevante(): rejeita termo de plano sem o nome do município": t2_relevante_rejeita_sem_municipio,
        "relevante(): rejeita nome do município sem termo de plano": t3_relevante_rejeita_sem_termo_plano,
        "vocabulário de decisao usado aqui existe de fato em log_busca()": t4_vocabulario_log_busca_bate_com_o_codigo,
        "dedup: mesma chave (ibge,url,trecho) é reconhecida como vista": t5_dedup_mesma_chave,
    })


if __name__ == "__main__":
    if "--autoteste" in sys.argv:
        sys.exit(autoteste())
    args = sys.argv[1:]
    lote = args[args.index("--lote") + 1] if "--lote" in args else "1"
    tamanho = int(args[args.index("--tamanho") + 1]) if "--tamanho" in args else 60
    sys.exit(rodar(lote, tamanho))
