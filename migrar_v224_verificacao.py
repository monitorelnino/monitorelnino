#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Migração v2.2.3 → v2.2.4 (documento de redesenho de 02/09/2026, §2–§3).

Executada UMA vez na sessão de 02/09/2026 e mantida no repositório para
auditoria. Idempotente: rodar de novo não altera nada.

O que faz:
1. `data/log_buscas.json` → esquema v2 (§3.1), preservando as 15 execuções
   existentes (campos novos com null/derivados; nada inventado).
2. `data/municipios.json`: registros `nao_localizado` SEM entrada de log com
   `nivel="municipal_completo"` e `decisao="nada localizado"` para o mesmo
   município são reclassificados `nao_verificado` (crédito 0,0 → 0,0; nenhuma
   nota muda). Errata em `data/erratas_v224.json`.
3. `data/verificacao_municipal.json` (§3.3): 5.571 municípios inicializados
   a partir de `municipios_ibge_referencia.json`; `plano_localizado` preenchido
   onde há registro; `nivel_verificacao` só sobe com log estruturado (hoje:
   nenhum) — os buracos ficam visíveis (premissa E7).
4. `data/citacao_incompleta.json` (§11.3, decisão C11): fila pública de
   registros pontuáveis sem número de ato OU com data fora do padrão, com
   prazo de saneamento 25/10/2026; saída da pontuação em 26/10/2026 por regra
   declarada em 02/09/2026.
"""
import json, re, sys, datetime

PONTUAVEIS = {"plano", "plano_antigo", "plano_elaboracao", "coberto_estadual"}
HOJE = "2026-09-02"

def j(p):
    with open(p, encoding="utf-8") as f: return json.load(f)
def w(p, d):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1); f.write("\n")

def migrar_log():
    lg = j("data/log_buscas.json")
    if lg.get("formato_versao") == 2: return lg, False
    novas = []
    for e in lg["execucoes"]:
        novas.append({
            "data": e["data"], "canal": e.get("canal"), "camada": None,
            "uf": None, "municipio": None, "ibge": None,
            "nivel": None,  # execuções v1 não distinguem nível; não imputar
            "strings": e.get("strings", []), "n_resultados": None,
            "resultados": e.get("resultados", ""), "decisao": e.get("decisao", ""),
            "fonte_suspensa_defeso": False, "executor": "claude",
            "hash_evidencia": None, "alvo_v1": e.get("alvo"),
        })
    lg2 = {"formato_versao": 2,
           "formato": "esquema v2 (§3.1 do doc de redesenho 02/09/2026); "
                      "entradas v1 migradas com campos estruturais null (não imputados), alvo original em alvo_v1",
           "execucoes": novas}
    w("data/log_buscas.json", lg2); return lg2, True

def completos(lg):
    s = set()
    for e in lg["execucoes"]:
        if e.get("nivel") == "municipal_completo" and str(e.get("decisao","")).strip().lower().startswith("nada localizado") and e.get("municipio") and e.get("uf"):
            s.add((e["municipio"], e["uf"]))
    return s

def reclassificar(lg):
    mun = j("data/municipios.json"); com_log = completos(lg); erratas = []
    for m in mun:
        if m["categoria"] == "nao_localizado" and (m["nome"], m["uf"]) not in com_log:
            erratas.append({"data": HOJE, "municipio": m["nome"], "uf": m["uf"],
                "de": "nao_localizado", "para": "nao_verificado",
                "efeito_na_nota": "nenhum (crédito 0,0 nas duas categorias)",
                "motivo": "regra §2.1 (02/09/2026): 'nada localizado' exige bateria municipal completa logada; o log de buscas não contém bateria para este município"})
            m["categoria"] = "nao_verificado"
    if erratas:
        w("data/municipios.json", mun)
        try:
            pontos = j("data/pontos_mapa.json")
            porm = {(m["nome"], m["uf"]): m["categoria"] for m in mun}
            alt = 0
            for p in pontos:
                ch = (p.get("nome"), p.get("uf"))
                if ch in porm and p.get("categoria") != porm[ch]:
                    p["categoria"] = porm[ch]; alt += 1
            if alt: w("data/pontos_mapa.json", pontos)
        except FileNotFoundError:
            pass
        try: base = j("data/erratas_v224.json")
        except FileNotFoundError: base = []
        w("data/erratas_v224.json", base + erratas)
    return mun, erratas

def construir_verificacao(mun, lg):
    import recalcular_mare
    return recalcular_mare.regravar_verificacao_municipal()

def fila_citacao(mun):
    fila = []
    pad_num = re.compile(r"(n[ºo°\.]\s*\d)|((decreto|portaria|lei|resolu[çc][ãa]o|instru[çc][ãa]o normativa|of[íi]cio)\s*(municipal|estadual|conjunta?)?\s*n?[ºo°\.]?\s*\d)", re.I)  # número formal do ato
    pad_data = re.compile(r"^\d{2}/\d{2}/\d{4}$")
    for m in mun:
        if m["categoria"] not in PONTUAVEIS: continue
        problemas = []
        if not pad_num.search(m.get("documento") or ""): problemas.append("sem_numero_de_ato")
        if not pad_data.match((m.get("data") or "").strip()): problemas.append("data_fora_do_padrao")
        if not (m.get("url") or "").startswith("http"): problemas.append("sem_url")
        if problemas:
            fila.append({"nome": m["nome"], "uf": m["uf"], "categoria": m["categoria"],
                         "problemas": problemas, "prazo_saneamento": "2026-10-25"})
    w("data/citacao_incompleta.json", {
        "regra": "declarada em 02/09/2026 (C11): a partir de 26/10/2026, registro pontuável sem número de ato OU sem data no padrão dd/mm/aaaa sai da pontuação; até lá permanece, com fila pública",
        "prazo_saneamento": "2026-10-25", "vigencia_da_saida": "2026-10-26",
        "fila": fila})
    return fila

if __name__ == "__main__":
    lg, mudou_log = migrar_log()
    mun, erratas = reclassificar(lg)
    vm = construir_verificacao(mun, lg)
    fila = fila_citacao(mun)
    niveis = {}
    for v in vm: niveis[v["nivel_verificacao"]] = niveis.get(v["nivel_verificacao"], 0) + 1
    print(f"log v2: {'migrado' if mudou_log else 'já estava'} · reclassificados: {len(erratas)} · "
          f"verificacao_municipal: {len(vm)} ({niveis}) · fila de citação: {len(fila)}")
