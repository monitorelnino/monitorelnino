#!/usr/bin/env python3
"""
coletar_diarios_municipais.py
=============================
Diários oficiais MUNICIPAIS via API do Querido Diário (municípios indexados),
em lotes por prioridade (§4, §13). O que produz:
  - decretos de emergência/calamidade NÃO homologados → `data/atos_resposta.json`
    (resposta, peso zero, fonte "querido_diario");
  - menções a plano de contingência / ativação preventiva → `data/pistas_imprensa.json`
    (fila de pista, com hash da evidência; promover a registro é HUMANO, §3.2).
  - livro de fontes consultadas: registra a consulta, mas NÃO eleva o nível a
    `municipal_completo` — isso exige a bateria inteira do §4.1.2 (diário + sítio
    da prefeitura + busca dirigida), executada e logada por município (pós-defeso).

Prioridade dos lotes: a lista NOMINAL do Cadastro Nacional de Municípios
Suscetíveis não é pública (limitação declarada em 31/08/2026); usa-se o proxy
declarado — UFs em ordem do percentual no cadastro (`cadastro_prioritarios.json`)
e, dentro da UF, população decrescente (Censo 2022).

USO
  python coletar_diarios_municipais.py --autoteste
  python coletar_diarios_municipais.py --lote 1 --tamanho 150 --desde 2026-06-29
"""
import json, math, re, sys, time, urllib.parse, urllib.error
from datetime import date
from coletores_base import (buscar, preservar_evidencia, preservar_texto_integral, log_busca,
                            registrar_lacuna, marcar_fonte_consultada, referencia_ibge, ler, gravar,
                            DECISOES_LOG,
                            abrir_lote_log, fechar_lote_log, descarregar_lote_log,
                            abrir_lote_livro, fechar_lote_livro, descarregar_lote_livro,
                            rodar_autoteste)
from classificar_pista_civil import triagem_completa

FONTE_QD = "Querido Diário (diário municipal)"
PAUSA_ENTRE_CONSULTAS = 0.25   # segundos; cortesia com a API pública

# 21/09/2026: o Querido Diário migrou de domínio. O host antigo (queridodiario.ok.org.br/api)
# ainda resolve, mas responde 302 para api.queridodiario.org.br a cada chamada — verificado nesta
# data, e confirmado pela configuração de produção do próprio projeto (okfn-brasil/querido-diario-
# deployment). Depender do redirect custa uma viagem extra em cada uma das 5.571 consultas da
# varredura e quebra no dia em que o host antigo deixar de redirecionar. Passamos a chamar o
# domínio novo direto, com o antigo como RESERVA: se o novo falhar por rede, a consulta é repetida
# no antigo antes de virar lacuna, para que uma troca de endereço nunca derrube a varredura inteira.
QD_API = "https://api.queridodiario.org.br/gazettes?{params}"
QD_API_RESERVA = "https://queridodiario.ok.org.br/api/gazettes?{params}"
TERMOS_RESPOSTA = ['"situação de emergência"', '"estado de calamidade pública"']
# 24/09/2026 (§194): a lista saiu de três para nove frases, e cada acréscimo veio do NOME REAL de um
# plano já no banco, nunca de palpite. Medido contra os 134 planos conhecidos: "plano de ação" casava
# com ZERO deles (Teresina publica "Planos de ação", e a frase exata não alcançava), enquanto ficavam
# de fora "Plano Operacional de Enfrentamento à Estiagem" (Manaus), "Plano Preventivo de Chuvas de
# Verão" (São Paulo) e as siglas PLANCON/PLAMCON/PLACON, que é como boa parte dos municípios nomeia o
# instrumento. Conferido na API em 24/09: o analisador do Querido Diário resolve plural — "planos de
# contingência" devolve o mesmo que "plano de contingência" —, então a lista não precisa das flexões.
# O limite conhecido, e o motivo de não alargar mais (§186): termo genérico enche a fila humana de
# ruído, e fila com ruído gasta o tempo de quem deveria julgar documento.
TERMOS_PISTA = ['"plano de contingência"', '"El Niño"', '"plano de ação"',
                '"PLANCON"', '"PLAMCON"', '"PLACON"',
                '"plano operacional"', '"plano preventivo"', '"plano de enfrentamento"']
PAD_DECRETO = re.compile(r"decreto\s+(?:municipal\s+)?n[ºo°\.]?\s*([\d\.\/-]+)[^.]{0,200}?(situa[çc][ãa]o de emerg[êe]ncia|estado de calamidade p[úu]blica)", re.I)
PAD_PLANO = re.compile(r"plano\s+(?:municipal\s+)?de\s+conting[êe]ncia[^.]{0,160}", re.I)


def ordem_prioridade(por_cod: dict, cadastro: dict, pop: dict) -> list:
    # 21/09/2026 (§123): a lista curada em data/cadastro_prioritarios.json pode omitir uma UF —
    # PI está em por_uf (pct 21,0) mas ficou fora de ordem_prioridade_uf_por_percentual. Com o
    # rank fixo 99, toda UF ausente empatava num balde único e a ordem entre elas ficava
    # indefinida (dependia da ordem de iteração do dict). Agora as ausentes entram logo após a
    # lista curada, entre si por percentual decrescente do próprio cadastro: posição
    # determinística e derivada do dado, sem reordenar as UFs que a lista já nomeia.
    ufs = list(cadastro.get("ordem_prioridade_uf_por_percentual") or sorted({r["uf"] for r in por_cod.values()}))
    por_uf = cadastro.get("por_uf") or {}
    ausentes = sorted((u for u in por_uf if u not in ufs), key=lambda u: -(por_uf[u].get("pct") or 0))
    ufs += ausentes
    rank_uf = {uf: i for i, uf in enumerate(ufs)}
    fim = len(ufs)
    return sorted(por_cod, key=lambda c: (rank_uf.get(por_cod[c]["uf"], fim), -int(pop.get(c, 0) or 0)))


def pendentes_na_janela(ordem: list, livro: dict, desde_janela: str) -> list:
    """Municípios, na ordem de prioridade, SEM consulta ao Querido Diário datada >= desde_janela.
    Varredura integral (03/09/2026): cada dia consome os próximos ainda não consultados —
    nunca repete quem já foi visto na janela e nunca pula ninguém."""
    mun = (livro or {}).get("municipios", {})
    def consultado(cod):
        return any(f.get("fonte") == FONTE_QD and (f.get("data") or "") >= desde_janela
                   for f in mun.get(str(cod).zfill(7), {}).get("fontes", []))
    return [c for c in ordem if not consultado(c)]


def tamanho_para_cobrir(n_pendentes: int, hoje_iso: str, ate_iso: str, minimo: int, maximo: int = 1500) -> int:
    """Quantos consultar hoje para que TODOS os pendentes caibam nos dias que restam
    (hoje inclusive) até `ate_iso`. Nunca abaixo de `minimo`; teto `maximo` por rodada."""
    try:
        dias = (date.fromisoformat(ate_iso) - date.fromisoformat(hoje_iso)).days + 1
    except ValueError:
        dias = 1
    dias = max(1, dias)
    return max(minimo, min(maximo, math.ceil(n_pendentes / dias)))


ESPERAS_429 = (30,)        # limite de taxa: a fonte manda esperar, e esperar é a resposta certa
ESPERAS_5XX = (5, 15)      # indisponibilidade temporária: "tente mais tarde", crescendo


# Decisões que ESTE canal produz. Existe nomeado por causa do §213: o §194 criou
# `sem_edicao_no_periodo` e a palavra ficou de fora de DUAS listas — a do `log_busca`, que matou a
# varredura, e a de `verificar_consistencia.py`, que reprovou o portão depois. Quem produz a
# decisão declara o conjunto; quem confere importa daqui. Assim as listas não podem divergir.
DECISOES_DOM = ("sem_cobertura_qd", "sem_edicao_no_periodo", "coberto_sem_mencao",
                "com_excerto", "registro", "erro")

def buscar_com_espera(url: str, timeout: int = 30, buscar_fn=None, dormir=None) -> bytes:
    """Repete com espera quando a fonte pede tempo; 4xx sobe na hora.

    25/09/2026, medido na varredura nacional: **63 dos 505 primeiros municípios** viraram lacuna
    por `HTTP 503 Service Unavailable` — 12 %. Não é bloqueio (403) nem limite de taxa (429): é
    indisponibilidade temporária, e a resposta certa a "tente mais tarde" é tentar mais tarde. A
    reserva de domínio não resolvia isto: ela cobre troca de endereço, e o endereço antigo serve o
    MESMO serviço — se a produção está fora, a reserva está fora junto.

    4xx (fora 429) continua subindo na hora: consulta errada não melhora com repetição, e repetir
    só dobraria a carga sobre uma API pública mantida por um projeto sem fins lucrativos."""
    buscar_fn = buscar_fn or buscar
    dormir = dormir or time.sleep
    restantes = None
    while True:
        try:
            return buscar_fn(url, timeout=timeout)
        except urllib.error.HTTPError as e:
            if restantes is None:
                restantes = list(ESPERAS_429 if e.code == 429 else
                                 ESPERAS_5XX if e.code >= 500 else ())
            if not restantes:
                raise
            dormir(restantes.pop(0))


def consultar_qd(params: str, timeout: int = 30) -> bytes:
    """Consulta a API do Querido Diário no domínio de produção; se ele falhar por rede ou por erro
    do servidor, repete no domínio antigo antes de desistir (21/09/2026 — ver nota em QD_API).

    A reserva cobre indisponibilidade e troca de endereço, não resposta ruim: 404 e 4xx em geral
    sobem na hora, porque significam que a consulta está errada, não que o host caiu — repetir só
    dobraria a carga sobre a API pública e mascararia o defeito."""
    try:
        return buscar_com_espera(QD_API.format(params=params), timeout=timeout)
    except urllib.error.HTTPError as e:
        if e.code < 500:
            raise
        motivo = f"HTTP {e.code}"
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        motivo = e.__class__.__name__
    print(f"[aviso] Querido Diário: domínio de produção indisponível ({motivo}) — repetindo no domínio de reserva.", flush=True)
    return buscar_com_espera(QD_API_RESERVA.format(params=params), timeout=timeout)


def edicoes_no_periodo(cod: str, desde: str):
    """True se o território tem ao menos uma edição publicada a partir de `desde`; False se não;
    None se o teste falhou. É a pergunta que a rodada precisa responder, e que o teste de cobertura
    (sem recorte de data) não responde — ver a nota em decisao_para_vazio (§194)."""
    try:
        time.sleep(PAUSA_ENTRE_CONSULTAS)
        d = json.loads(consultar_qd(urllib.parse.urlencode(
            {"territory_ids": cod, "published_since": desde, "size": 1}), timeout=30).decode("utf-8", "replace"))
        return (d.get("total_gazettes", 0) or 0) > 0
    except Exception:  # noqa: BLE001 — teste auxiliar nunca derruba a rodada
        return None


def decisao_para_vazio(coberto, edicoes_no_periodo=None) -> str:
    """Decisão do log para resposta sem achado. Função pura.

    §194 (24/09/2026), TRÊS estados onde antes havia dois. O teste de cobertura pergunta se o
    município tem diário indexado ALGUMA VEZ — sem recorte de data. Medido em 24/09: Manaus tem
    7.517 edições no Querido Diário e a mais recente é de **02/08/2016**; São Paulo tem 20, a mais
    recente de 07/02/2025; Aracaju, 4.582, a mais recente de 01/04/2025. Nenhum deles tem uma única
    edição dentro do ciclo. Pelo critério antigo os três saíam como "indexado; nenhuma menção aos
    termos no período" — frase que dá a entender que houve edição e nela não se falou do assunto.
    Não houve edição. É a diferença entre "procuramos e não há" e "não havia onde procurar", que é
    exatamente a distinção que este projeto não pode perder.
    """
    if coberto is None:
        return "erro"
    if coberto is False:
        return "sem_cobertura_qd"
    if edicoes_no_periodo is False:
        return "sem_edicao_no_periodo"
    return "coberto_sem_mencao"


def cobertura_qd(cod: str, desde: str, resposta_com_diario: bool = False):
    """PR-N0 §1.2: True se o território tem diário indexado no Querido Diário (total_gazettes>0 sem
    querystring), False se não, None se o teste falhou. Cache em data/cobertura_qd.json (uma vez por janela).
    Também grava cobertura_qd/data_teste_cobertura em verificacao_municipal.json."""
    cache = ler("cobertura_qd.json", {"_governanca": "Cobertura do Querido Diário por município (PR-N0 §1.2): true = diário indexado; false = não indexado; testado sem querystring, size=1. Uma vez por janela.", "janela": desde, "municipios": {}}) or {}
    if cache.get("janela") != desde:
        cache = {"_governanca": cache.get("_governanca", ""), "janela": desde, "municipios": {}}
    mun = cache.setdefault("municipios", {})
    hoje = date.today().isoformat()
    # 25/09/2026 (§212, terceiro arquivo): o acerto em cache NÃO pode gravar. Antes, toda chamada
    # regravava `cobertura_qd.json` (418 kB) e, pior, lia e regravava `verificacao_municipal.json`
    # (2 MB) — nos 3.428 municípios da varredura, cerca de 13 GB de entrada e saída para não mudar
    # nada. Agora só grava quem mudou.
    anterior = dict(mun.get(cod) or {})
    if resposta_com_diario:
        mun[cod] = {"cobertura_qd": True, "data_teste": hoje}
    elif cod in mun and mun[cod].get("cobertura_qd") is not None:
        pass
    else:
        try:
            time.sleep(PAUSA_ENTRE_CONSULTAS)
            d = json.loads(consultar_qd(urllib.parse.urlencode({"territory_ids": cod, "size": 1}), timeout=30).decode("utf-8", "replace"))
            mun[cod] = {"cobertura_qd": (d.get("total_gazettes", 0) or 0) > 0, "data_teste": hoje}
        except Exception:  # noqa: BLE001
            mun[cod] = {"cobertura_qd": None, "data_teste": hoje}
    if mun.get(cod) != anterior:
        gravar("cobertura_qd.json", cache)
    # Espelho em verificacao_municipal.json (campo público). A data que vai para lá é a do TESTE,
    # não a de hoje: num acerto em cache o teste não aconteceu hoje, e carimbá-lo com a data de
    # hoje afirmaria uma verificação que não houve. Grava só quando valor ou data mudam.
    try:
        valor, quando = mun[cod]["cobertura_qd"], mun[cod]["data_teste"]
        vm = ler("verificacao_municipal.json", []) or []
        if isinstance(vm, list):
            for reg in vm:
                if str(reg.get("ibge")).zfill(7) == str(cod).zfill(7):
                    if reg.get("cobertura_qd") != valor or reg.get("data_teste_cobertura") != quando:
                        reg["cobertura_qd"] = valor; reg["data_teste_cobertura"] = quando
                        gravar("verificacao_municipal.json", vm)
                    break
    except Exception:  # noqa: BLE001
        pass
    return mun[cod]["cobertura_qd"]


def parse_qd(dados) -> list:
    return [{"data": g.get("date", ""), "url": g.get("url") or g.get("txt_url", ""),
             "trechos": [t for t in g.get("excerpts", []) if t]} for g in (dados or {}).get("gazettes", [])]


def classificar_trechos(itens: list) -> tuple:
    """(decretos, pistas). Decreto só com número (citação completa); plano vira pista."""
    decretos, pistas = [], []
    for it in itens:
        for tr in it["trechos"]:
            for numero, tipo in PAD_DECRETO.findall(tr):
                decretos.append({"decreto": f"Decreto municipal nº {numero}", "tipo": tipo.lower(), "data": it["data"], "url": it["url"], "trecho": tr[:300]})
            if PAD_PLANO.search(tr):
                pistas.append({"data": it["data"], "url": it["url"], "trecho": tr[:300]})
    return decretos, pistas


def iso_para_br(s):
    try:
        y, m, d = s[:10].split("-"); return f"{d}/{m}/{y}"
    except ValueError:
        return s


def coletar_lote(lote: int, tamanho: int, desde: str, pendentes_desde: str = "", ate: str = "", tudo: bool = False) -> int:
    por_cod, _ = referencia_ibge()
    pop = ler("populacao_censo2022.json", {}) or {}
    cadastro = ler("cadastro_prioritarios.json", {}) or {}
    ordem = ordem_prioridade(por_cod, cadastro, pop)
    if pendentes_desde:
        pend = pendentes_na_janela(ordem, ler("fontes_consultadas.json", {}), pendentes_desde)
        if tudo:
            # 03/09/2026: pedido editorial de encerrar a varredura HOJE — consulta TODOS os
            # pendentes numa rodada só, ignorando o ritmo por dias restantes (só usado sob pedido
            # explícito; a pausa entre consultas (§ PAUSA_ENTRE_CONSULTAS) continua valendo).
            alvo = pend
            print(f"varredura integral (--tudo): {len(pend)} pendentes desde {pendentes_desde}; consultando todos nesta rodada")
        else:
            # varredura integral: próximos ainda não consultados na janela; tamanho dimensionado para cobrir todos até `ate`
            tamanho = tamanho_para_cobrir(len(pend), date.today().isoformat(), ate or date.today().isoformat(), tamanho)
            alvo = pend[:tamanho]
            print(f"varredura integral: {len(pend)} pendentes desde {pendentes_desde}; hoje {len(alvo)} (fim previsto {ate or 'hoje'})")
    else:
        alvo = ordem[(lote - 1) * tamanho: lote * tamanho]
    atos = ler("atos_resposta.json"); pistas = ler("pistas_imprensa.json", {"_governanca": "", "pistas": []})
    pistas.setdefault("pistas", [])
    vistos = {(e["nome"], e["uf"], e["data"], e.get("causa")) for e in atos["eventos"]}
    # 21/09/2026 (achado real, revisão da fila de pistas): pistas["pistas"].append() nunca teve
    # deduplicação — ao contrário de atos_resposta.json (dedup por `vistos` acima), a mesma
    # menção reaparecia como pista nova a cada rodada que tocasse a mesma janela de datas.
    # Achado concreto: Ouro Branco/AL, mesmo decreto 021/2026, mesmo hash_evidencia, mesmo trecho
    # — duas pistas idênticas na fila, a segunda registrada dois dias depois da primeira. Chave de
    # deduplicação: (ibge, url, trecho) — a mesma menção no mesmo documento não deveria virar duas
    # entradas na fila só porque a rodada rodou de novo sobre uma data já coberta.
    vistos_pistas = {(p.get("ibge"), p.get("url"), p.get("trecho")) for p in pistas["pistas"]}
    n_ok = n_lac = novos = npist = 0
    # 25/09/2026: varredura nacional. Sem lote, cada município lê e regrava o log de buscas
    # (20 MB) e o livro de fontes (12 MB) — nos 2.965 pendentes de hoje, dezenas de gigabytes de
    # entrada e saída e outras tantas janelas em que uma interrupção deixa o arquivo pela metade.
    # É o mesmo arquivo que foi corrompido assim em 21/09. Os dois lotes acumulam em memória e
    # descarregam de 250 em 250; o `finally` garante que o que sobrou chegue ao disco mesmo se a
    # rodada for interrompida, porque perder 2.900 registros por causa de um Ctrl-C seria pior
    # do que a E/S que o lote evita.
    abrir_lote_log()
    abrir_lote_livro()
    try:
        n_ok, n_lac, novos, npist = _varrer(alvo, por_cod, desde, atos, pistas, vistos, vistos_pistas)
    finally:
        fechar_lote_log()
        fechar_lote_livro()
    gravar("atos_resposta.json", atos); gravar("pistas_imprensa.json", pistas)
    print(f"lote {lote}: {n_ok} consultados, {n_lac} lacunas, {novos} decretos novos, {npist} pistas")
    return 0


def _varrer(alvo, por_cod, desde, atos, pistas, vistos, vistos_pistas):
    """O laço da varredura, separado só para que o chamador possa fechar os lotes num `finally`.
    Devolve (consultados, lacunas, decretos novos, pistas novas)."""
    n_ok = n_lac = novos = npist = 0
    for cod in alvo:
        ref = por_cod[cod]
        params = urllib.parse.urlencode({"territory_ids": cod, "published_since": desde,
                                         "querystring": " OR ".join(TERMOS_RESPOSTA + TERMOS_PISTA), "size": 50})
        url = QD_API.format(params=params)
        time.sleep(PAUSA_ENTRE_CONSULTAS)
        try:
            bruto = consultar_qd(params, timeout=30)
            dados = json.loads(bruto.decode("utf-8", "replace"))
        except Exception as e:  # noqa: BLE001
            registrar_lacuna(f"Querido Diário/{ref['nome']}-{ref['uf']}", f"{type(e).__name__}", canal="DOM", camada=1,
                             uf=ref["uf"], municipio=ref["nome"], ibge=cod, strings=[url]); n_lac += 1
            continue
        if dados.get("total_gazettes", 0) == 0 and not dados.get("gazettes"):
            # PR-N0 §1.2 (06/09/2026): distinguir "não indexado" de "sem menção". Teste de cobertura por
            # território (sem querystring, size=1), guardado em data/cobertura_qd.json (uma vez por janela).
            coberto = cobertura_qd(cod, desde)
            # §194 (24/09/2026): o teste acima não tem recorte de data, então um município cujo
            # diário está indexado mas PAROU de ser publicado no índice sai como "indexado". Este
            # segundo teste pergunta o que importa para a rodada: existe alguma edição DENTRO da
            # janela? Sem ele, "não havia onde procurar" era registrado como "procuramos e não há".
            edicoes = edicoes_no_periodo(cod, desde) if coberto is True else None
            decisao = decisao_para_vazio(coberto, edicoes)
            MOTIVO = {
                "sem_cobertura_qd": ("sem_cobertura_qd: diário não indexado no Querido Diário",
                                     "Querido Diário: território sem diário indexado (total_gazettes=0 sem querystring) — verificação por outro canal pendente"),
                "sem_edicao_no_periodo": ("sem_edicao_no_periodo: diário indexado, nenhuma edição dentro da janela",
                                          "Querido Diário: diário indexado, mas sem NENHUMA edição no período — a fonte não tem o que dizer sobre a janela; verificação por outro canal pendente"),
                "coberto_sem_mencao": ("coberto_sem_mencao: indexado, com edições no período; nenhum excerto com os termos",
                                       "Querido Diário: diário indexado e com edições no período, nenhuma menção aos termos (bateria negativa de camada 1)"),
                "erro": ("cobertura a confirmar (teste de cobertura falhou)",
                         "Querido Diário: 0 resultados e teste de cobertura sem resposta"),
            }[decisao]
            marcar_fonte_consultada([cod], FONTE_QD, "nao_verificado", resultado=MOTIVO[0])
            log_busca("DOM", 1, TERMOS_RESPOSTA + TERMOS_PISTA, decisao, uf=ref["uf"], municipio=ref["nome"], ibge=cod,
                      n_resultados=0, resultados=MOTIVO[1])
            n_ok += 1; continue
        h = preservar_evidencia(bruto, url, "json", "coletar_diarios_municipais")
        # 10/09/2026: além do excerto, o texto integral da edição — o julgamento humano lê o
        # documento inteiro offline, sem depender de portal que bloqueie acesso depois.
        preservar_texto_integral(h, (dados or {}).get("gazettes", []), "coletar_diarios_municipais")
        decretos, pist = classificar_trechos(parse_qd(dados))
        for d in decretos:
            dbr = iso_para_br(d["data"]); chave = (ref["nome"], ref["uf"], dbr, d["tipo"])
            if chave in vistos:
                continue
            atos["eventos"].append({"nome": ref["nome"], "uf": ref["uf"], "ibge": cod, "data": dbr, "causa": d["tipo"],
                                    "decreto": d["decreto"], "fonte": "Diário oficial municipal (via Querido Diário)",
                                    "url": d["url"], "lat": ref["lat"], "lon": ref["lon"], "canal": "DOM", "hash_evidencia": h})
            vistos.add(chave); novos += 1
        for p in pist:
            chave_pista = (cod, p["url"], p["trecho"])
            if chave_pista in vistos_pistas:
                continue  # mesma menção, mesmo documento — já está na fila (achado 21/09/2026)
            pistas["pistas"].append({"municipio": ref["nome"], "uf": ref["uf"], "ibge": cod, "origem": "querido_diario",
                                    "data": iso_para_br(p["data"]), "url": p["url"], "trecho": p["trecho"],
                                    "hash_evidencia": h, "registrado_em": date.today().isoformat(),
                                    # 03/09/2026: triagem/autoridade/objeto/destino só ORDENAM a fila; nunca decidem sozinhos (§3.2, §5.2.1-bis)
                                    **triagem_completa(p["trecho"]),
                                    "status": "pista — promover a registro exige documento primário lido por humano"})
            vistos_pistas.add(chave_pista); npist += 1
        marcar_fonte_consultada([cod], FONTE_QD, "nao_verificado",
                                resultado=f"{len(decretos)} decreto(s), {len(pist)} pista(s)")
        cobertura_qd(cod, desde, resposta_com_diario=True)   # com excertos = coberto, sem gastar outra chamada
        log_busca("DOM", 1, TERMOS_RESPOSTA + TERMOS_PISTA, "registro" if decretos else "com_excerto", uf=ref["uf"],
                  municipio=ref["nome"], ibge=cod, n_resultados=dados.get("total_gazettes"), hash_evidencia=h,
                  resultados=f"{len(decretos)} decretos, {len(pist)} pistas (com_excerto: pista para a fila humana; R7)")
        n_ok += 1
        if n_ok % 250 == 0:
            # Salvamento parcial: descarrega os lotes e grava o banco. Uma varredura nacional não
            # pode depender de terminar para que o que já foi lido conte.
            descarregar_lote_log(); descarregar_lote_livro()
            gravar("atos_resposta.json", atos); gravar("pistas_imprensa.json", pistas)
            print(f"  … {n_ok} consultados, {n_lac} lacunas, {novos} decretos, {npist} pistas", flush=True)
    return n_ok, n_lac, novos, npist


FIX = {"total_gazettes": 1, "gazettes": [{"date": "2026-08-30", "url": "https://x/d.pdf", "excerpts": [
    "DECRETO Nº 987/2026 — Declara situação de emergência nas áreas afetadas pelas chuvas.",
    "Fica instituído o Plano Municipal de Contingência para o período chuvoso 2026/2027."]}]}


def autoteste() -> int:
    def t1():
        d, p = classificar_trechos(parse_qd(FIX)); return len(d) == 1 and d[0]["decreto"] == "Decreto municipal nº 987/2026" and len(p) == 1
    def t2():  # negativo: decreto sem número não entra como ato
        d, _ = classificar_trechos([{"data": "2026-08-30", "url": "", "trechos": ["Decreta situação de emergência."]}]); return d == []
    def t3():
        por = {"1": {"uf": "SC"}, "2": {"uf": "RS"}, "3": {"uf": "SC"}}
        o = ordem_prioridade(por, {"ordem_prioridade_uf_por_percentual": ["SC", "RS"]}, {"1": 10, "3": 500})
        return o == ["3", "1", "2"]
    def t3b():  # negativo (§123): UF que está em por_uf mas fora da lista curada entra depois dela,
        # entre as ausentes por percentual decrescente — nunca num balde de ordem indefinida.
        # GO (10,2) entra no dict antes de PI (21,0): com o rank fixo antigo sairia GO, PI.
        por = {"1": {"uf": "SC"}, "2": {"uf": "GO"}, "3": {"uf": "PI"}, "4": {"uf": "RS"}}
        cad = {"ordem_prioridade_uf_por_percentual": ["SC", "RS"],
               "por_uf": {"SC": {"pct": 73.9}, "RS": {"pct": 41.4}, "GO": {"pct": 10.2}, "PI": {"pct": 21.0}}}
        return ordem_prioridade(por, cad, {}) == ["1", "4", "3", "2"]
    def t3c():  # §124: reserva de domínio do QD. 5xx/rede cai no domínio antigo; 4xx sobe na hora.
        import urllib.error as ue
        chamadas = []
        def falso(url, timeout=30):
            chamadas.append(url)
            if url.startswith("https://api.queridodiario.org.br") and modo[0] != "ok":
                if modo[0] == "http4":
                    raise ue.HTTPError(url, 404, "nao encontrado", None, None)
                raise ue.URLError("host caiu")
            return b'{"total_gazettes": 0}'
        real = globals()["buscar_com_espera"]
        globals()["buscar_com_espera"] = falso
        try:
            modo = ["ok"]; chamadas.clear(); consultar_qd("x=1")
            so_producao = len(chamadas) == 1 and chamadas[0].startswith("https://api.queridodiario.org.br")
            modo = ["rede"]; chamadas.clear(); consultar_qd("x=1")
            caiu_na_reserva = len(chamadas) == 2 and chamadas[1].startswith("https://queridodiario.ok.org.br")
            modo = ["http4"]; chamadas.clear()
            try:
                consultar_qd("x=1"); quatro_xx_sobe = False
            except ue.HTTPError:
                quatro_xx_sobe = len(chamadas) == 1   # não repetiu: 404 é consulta errada, não host caído
            return so_producao and caiu_na_reserva and quatro_xx_sobe
        finally:
            globals()["buscar_com_espera"] = real
    def t4(): return parse_qd(None) == [] and parse_qd({}) == []
    def t5():  # varredura integral: quem já foi consultado na janela sai da fila; quem foi antes da janela volta
        livro = {"municipios": {"0000001": {"fontes": [{"fonte": FONTE_QD, "data": "2026-09-03"}]},
                                "0000002": {"fontes": [{"fonte": FONTE_QD, "data": "2026-08-20"}]}}}
        return pendentes_na_janela(["1", "2", "3"], livro, "2026-09-03") == ["2", "3"]
    def t6():  # dimensionamento: 5.421 pendentes em 8 dias → 678/dia; nunca abaixo do mínimo; teto respeitado
        return (tamanho_para_cobrir(5421, "2026-09-03", "2026-09-10", 150) == 678
                and tamanho_para_cobrir(100, "2026-09-03", "2026-09-10", 150) == 150
                and tamanho_para_cobrir(100000, "2026-09-10", "2026-09-10", 150) == 1500
                and tamanho_para_cobrir(300, "2026-09-11", "2026-09-10", 150) == 300)  # data-fim passada: tudo hoje
    def t8():  # PR-N0 §1.2: resposta vazia nunca vira 'nada localizado' — só as três decisões (ou erro)
        # §194: o estado novo — indexado, porém sem nenhuma edição na janela.
        assert decisao_para_vazio(True, False) == "sem_edicao_no_periodo", "sem edição no período"
        assert decisao_para_vazio(True, None) == "coberto_sem_mencao", "teste de janela indisponível não inventa estado"
        return decisao_para_vazio(True, True) == "coberto_sem_mencao" and decisao_para_vazio(False) == "sem_cobertura_qd" and decisao_para_vazio(None) == "erro"
    def t7():  # --tudo: alvo é a fila inteira de pendentes, sem fatiar por tamanho/dias restantes
        livro = {"municipios": {"1": {"fontes": [{"fonte": FONTE_QD, "data": "2026-08-20"}]}}}  # fora da janela: pendente
        pend = pendentes_na_janela(["1", "2", "3"], livro, "2026-09-03")
        return pend == ["1", "2", "3"]  # os três pendentes; --tudo (testado no fluxo real) os consultaria todos, não só um fatiamento
    def t10():
        """25/09/2026: TODA decisão que este coletor inventa tem de caber no vocabulário fechado
        do log. O §194 criou `sem_edicao_no_periodo` e não a acrescentou lá: a varredura nacional
        morria com AssertionError no primeiro município indexado sem edição na janela, e ficou
        parada sem que isso aparecesse como problema de vocabulário. Este teste liga as duas
        pontas — inventar decisão nova sem registrá-la passa a reprovar aqui, não em produção."""
        possiveis = {decisao_para_vazio(c, e)
                     for c in (True, False, None) for e in (True, False, None)}
        return (possiveis and all(d.split(" ")[0] in DECISOES_LOG for d in possiveis)
                and possiveis <= set(DECISOES_DOM))

    def t11():
        """25/09/2026: acerto em cache não grava, e a data que vai ao espelho é a do TESTE.

        Antes, toda chamada regravava `cobertura_qd.json` e `verificacao_municipal.json` (2 MB) —
        13 GB de E/S na varredura para não mudar nada — e carimbava o espelho com a data de HOJE
        mesmo quando o teste tinha sido feito dias antes, afirmando uma verificação que não houve.
        """
        gravados = []
        vm = [{"ibge": "1100015", "cobertura_qd": True, "data_teste_cobertura": "2026-09-20"}]
        cache = {"janela": "2026-06-29",
                 "municipios": {"1100015": {"cobertura_qd": True, "data_teste": "2026-09-20"}}}

        def ler_falso(nome, padrao=None):
            if nome == "cobertura_qd.json":
                return cache
            if nome == "verificacao_municipal.json":
                return vm
            return padrao

        def consultar_proibido(*a, **kw):
            raise AssertionError("acerto em cache não pode consultar a rede")

        real = {n: globals()[n] for n in ("ler", "gravar", "consultar_qd")}
        globals()["ler"] = ler_falso
        globals()["gravar"] = lambda nome, obj: gravados.append(nome)
        globals()["consultar_qd"] = consultar_proibido
        try:
            r = cobertura_qd("1100015", "2026-06-29")
        finally:
            for n, f in real.items():
                globals()[n] = f
        return (r is True and gravados == []
                and vm[0]["data_teste_cobertura"] == "2026-09-20")

    def t12():
        """25/09/2026: 503 é "tente mais tarde", e a resposta certa é esperar — a reserva de
        domínio não resolve, porque serve o mesmo serviço. 4xx continua subindo na hora."""
        import urllib.error as ue

        def erro(code):
            return ue.HTTPError("u", code, "x", None, None)

        # 503 duas vezes e sucesso na terceira: duas esperas, crescendo.
        esperas, n = [], {"i": 0}

        def flaky(url, timeout=30):
            n["i"] += 1
            if n["i"] <= 2:
                raise erro(503)
            return b"ok"

        r = buscar_com_espera("u", buscar_fn=flaky, dormir=esperas.append)
        um = (r == b"ok" and esperas == [5, 15])

        # 503 sempre: desiste depois das esperas previstas, sem laço infinito.
        esperas2 = []

        def sempre(url, timeout=30):
            raise erro(503)

        try:
            buscar_com_espera("u", buscar_fn=sempre, dormir=esperas2.append)
            dois = False
        except ue.HTTPError:
            dois = esperas2 == [5, 15]

        # 404: sobe na hora, sem espera nenhuma.
        esperas3 = []

        def quatro04(url, timeout=30):
            raise erro(404)

        try:
            buscar_com_espera("u", buscar_fn=quatro04, dormir=esperas3.append)
            tres = False
        except ue.HTTPError:
            tres = esperas3 == []

        # 429: a espera longa da fonte, uma vez.
        esperas4, m = [], {"i": 0}

        def limitado(url, timeout=30):
            m["i"] += 1
            if m["i"] == 1:
                raise erro(429)
            return b"ok"

        quatro = buscar_com_espera("u", buscar_fn=limitado, dormir=esperas4.append) == b"ok" and esperas4 == [30]
        return um and dois and tres and quatro

    def t9():  # 21/09/2026: dedup de pistas — rodar coletar_lote DUAS VEZES sobre o mesmo achado
        # (mesmo padrão do achado real: Ouro Branco/AL apareceu duplicado por duas rodadas sobre a
        # mesma janela) deve produzir UMA pista na fila, não duas. Mocka toda a I/O: rede
        # (consultar_qd), arquivos (ler/gravar/preservar_evidencia/preservar_texto_integral/
        # marcar_fonte_consultada) — nunca toca dado real, e roda coletar_lote de verdade, não uma
        # simulação da lógica.
        estado = {"atos": {"eventos": []}, "pistas": {"pistas": []}}
        def ler_falso(nome, padrao=None):
            if nome == "atos_resposta.json":
                return estado["atos"]
            if nome == "pistas_imprensa.json":
                return estado["pistas"]
            if nome == "populacao_censo2022.json":
                return {"1100015": 100000}
            if nome == "cadastro_prioritarios.json":
                return {}
            return padrao
        def gravar_falso(nome, obj):
            if nome == "atos_resposta.json":
                estado["atos"] = obj
            elif nome == "pistas_imprensa.json":
                estado["pistas"] = obj
        def referencia_falsa():
            ref = {"1100015": {"nome": "Teste", "uf": "MG", "lat": 0, "lon": 0}}
            return ref, {}
        def consultar_falso(params, timeout=30):
            return json.dumps(FIX).encode()
        real = {n: globals()[n] for n in ("ler", "gravar", "referencia_ibge", "consultar_qd",
                                          "preservar_evidencia", "preservar_texto_integral",
                                          "marcar_fonte_consultada", "log_busca",
                                          "abrir_lote_log", "fechar_lote_log", "descarregar_lote_log",
                                          "abrir_lote_livro", "fechar_lote_livro", "descarregar_lote_livro")}
        globals()["ler"] = ler_falso; globals()["gravar"] = gravar_falso
        globals()["referencia_ibge"] = referencia_falsa; globals()["consultar_qd"] = consultar_falso
        globals()["preservar_evidencia"] = lambda *a, **kw: "hashfalso"
        globals()["preservar_texto_integral"] = lambda *a, **kw: None
        globals()["marcar_fonte_consultada"] = lambda *a, **kw: None
        globals()["log_busca"] = lambda *a, **kw: None
        for _n in ("abrir_lote_log", "fechar_lote_log", "descarregar_lote_log",
                   "abrir_lote_livro", "fechar_lote_livro", "descarregar_lote_livro"):
            globals()[_n] = lambda *a, **kw: 0
        try:
            coletar_lote(1, 150, "2026-08-01")   # 1ª rodada
            n_apos_primeira = len(estado["pistas"]["pistas"])
            coletar_lote(1, 150, "2026-08-01")   # 2ª rodada, mesmo achado
            n_apos_segunda = len(estado["pistas"]["pistas"])
            return n_apos_primeira == 1 and n_apos_segunda == 1
        finally:
            for n, f in real.items():
                globals()[n] = f
    return rodar_autoteste({"classifica decreto com nº e pista de plano": t1, "negativo: decreto sem número": t2,
                            "prioridade: UF do cadastro, depois população": t3,
                            "negativo: UF fora da lista curada entra por percentual, não em balde indefinido": t3b,
                            "negativo: resposta nula": t4,
                            "reserva de domínio do QD: 5xx/rede repete no antigo, 4xx sobe na hora": t3c,
                            "varredura integral: fila de pendentes na janela": t5,
                            "varredura integral: tamanho para cobrir até a data-fim": t6,
                            "--tudo: fila completa de pendentes (não fatiada)": t7,
                            "resposta vazia → sem_cobertura_qd / coberto_sem_mencao / erro (nunca 'nada localizado')": t8,
                            "regressão 21/09: rodar duas vezes sobre o mesmo achado não duplica a pista": t9,
                            "toda decisão deste coletor cabe no vocabulário fechado do log": t10,
                            "acerto em cache não grava, e o espelho leva a data do teste": t11,
                            "503 espera e repete; 429 espera uma vez; 4xx sobe na hora": t12})


if __name__ == "__main__":
    if "--autoteste" in sys.argv:
        sys.exit(autoteste())
    a = sys.argv
    lote = int(a[a.index("--lote") + 1]) if "--lote" in a else 1
    tam = int(a[a.index("--tamanho") + 1]) if "--tamanho" in a else 150
    desde = a[a.index("--desde") + 1] if "--desde" in a else "2026-06-29"
    pend = a[a.index("--pendentes-desde") + 1] if "--pendentes-desde" in a else ""
    ate = a[a.index("--ate") + 1] if "--ate" in a else ""
    tudo = "--tudo" in a
    sys.exit(coletar_lote(lote, tam, desde, pendentes_desde=pend, ate=ate, tudo=tudo))
