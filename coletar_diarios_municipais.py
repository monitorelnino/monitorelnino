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
from coletores_base import (buscar, preservar_evidencia, log_busca, registrar_lacuna,
                            marcar_fonte_consultada, referencia_ibge, ler, gravar, rodar_autoteste)
from classificar_pista_civil import triagem_completa

FONTE_QD = "Querido Diário (diário municipal)"
PAUSA_ENTRE_CONSULTAS = 0.25   # segundos; cortesia com a API pública

QD_API = "https://queridodiario.ok.org.br/api/gazettes?{params}"
TERMOS_RESPOSTA = ['"situação de emergência"', '"estado de calamidade pública"']
TERMOS_PISTA = ['"plano de contingência"', '"El Niño"', '"plano de ação"']
PAD_DECRETO = re.compile(r"decreto\s+(?:municipal\s+)?n[ºo°\.]?\s*([\d\.\/-]+)[^.]{0,200}?(situa[çc][ãa]o de emerg[êe]ncia|estado de calamidade p[úu]blica)", re.I)
PAD_PLANO = re.compile(r"plano\s+(?:municipal\s+)?de\s+conting[êe]ncia[^.]{0,160}", re.I)


def ordem_prioridade(por_cod: dict, cadastro: dict, pop: dict) -> list:
    ufs = cadastro.get("ordem_prioridade_uf_por_percentual") or sorted({r["uf"] for r in por_cod.values()})
    rank_uf = {uf: i for i, uf in enumerate(ufs)}
    return sorted(por_cod, key=lambda c: (rank_uf.get(por_cod[c]["uf"], 99), -int(pop.get(c, 0) or 0)))


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


def buscar_com_espera(url: str, timeout: int = 30) -> bytes:
    """Uma nova tentativa após 30 s se a API limitar (HTTP 429); outros erros sobem."""
    try:
        return buscar(url, timeout=timeout)
    except urllib.error.HTTPError as e:
        if e.code == 429:
            time.sleep(30)
            return buscar(url, timeout=timeout)
        raise


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
    n_ok = n_lac = novos = npist = 0
    for cod in alvo:
        ref = por_cod[cod]
        params = urllib.parse.urlencode({"territory_ids": cod, "published_since": desde,
                                         "querystring": " OR ".join(TERMOS_RESPOSTA + TERMOS_PISTA), "size": 50})
        url = QD_API.format(params=params)
        time.sleep(PAUSA_ENTRE_CONSULTAS)
        try:
            bruto = buscar_com_espera(url, timeout=30)
            dados = json.loads(bruto.decode("utf-8", "replace"))
        except Exception as e:  # noqa: BLE001
            registrar_lacuna(f"Querido Diário/{ref['nome']}-{ref['uf']}", f"{type(e).__name__}", canal="DOM", camada=1,
                             uf=ref["uf"], municipio=ref["nome"], ibge=cod, strings=[url]); n_lac += 1
            continue
        if dados.get("total_gazettes", 0) == 0 and not dados.get("gazettes"):
            # município não indexado OU sem menção: não é "nada localizado" (exige bateria completa)
            marcar_fonte_consultada([cod], FONTE_QD, "nao_verificado",
                                    resultado="sem edições/menções no período (cobertura a confirmar)")
            log_busca("DOM", 1, TERMOS_RESPOSTA + TERMOS_PISTA, "pista", uf=ref["uf"], municipio=ref["nome"], ibge=cod,
                      n_resultados=0, resultados="Querido Diário: 0 resultados (não indexado ou sem menção)")
            n_ok += 1; continue
        h = preservar_evidencia(bruto, url, "json", "coletar_diarios_municipais")
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
            pistas["pistas"].append({"municipio": ref["nome"], "uf": ref["uf"], "ibge": cod, "origem": "querido_diario",
                                    "data": iso_para_br(p["data"]), "url": p["url"], "trecho": p["trecho"],
                                    "hash_evidencia": h, "registrado_em": date.today().isoformat(),
                                    # 03/09/2026: triagem/autoridade/objeto/destino só ORDENAM a fila; nunca decidem sozinhos (§3.2, §5.2.1-bis)
                                    **triagem_completa(p["trecho"]),
                                    "status": "pista — promover a registro exige documento primário lido por humano"}); npist += 1
        marcar_fonte_consultada([cod], FONTE_QD, "nao_verificado",
                                resultado=f"{len(decretos)} decreto(s), {len(pist)} pista(s)")
        log_busca("DOM", 1, TERMOS_RESPOSTA + TERMOS_PISTA, "registro" if decretos else "pista", uf=ref["uf"],
                  municipio=ref["nome"], ibge=cod, n_resultados=dados.get("total_gazettes"), hash_evidencia=h,
                  resultados=f"{len(decretos)} decretos, {len(pist)} pistas")
        n_ok += 1
    gravar("atos_resposta.json", atos); gravar("pistas_imprensa.json", pistas)
    print(f"lote {lote}: {n_ok} consultados, {n_lac} lacunas, {novos} decretos novos, {npist} pistas")
    return 0


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
    def t7():  # --tudo: alvo é a fila inteira de pendentes, sem fatiar por tamanho/dias restantes
        livro = {"municipios": {"1": {"fontes": [{"fonte": FONTE_QD, "data": "2026-08-20"}]}}}  # fora da janela: pendente
        pend = pendentes_na_janela(["1", "2", "3"], livro, "2026-09-03")
        return pend == ["1", "2", "3"]  # os três pendentes; --tudo (testado no fluxo real) os consultaria todos, não só um fatiamento
    return rodar_autoteste({"classifica decreto com nº e pista de plano": t1, "negativo: decreto sem número": t2,
                            "prioridade: UF do cadastro, depois população": t3, "negativo: resposta nula": t4,
                            "varredura integral: fila de pendentes na janela": t5,
                            "varredura integral: tamanho para cobrir até a data-fim": t6,
                            "--tudo: fila completa de pendentes (não fatiada)": t7})


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
