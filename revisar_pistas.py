#!/usr/bin/env python3
"""
revisar_pistas.py — a fila de revisão humana das pistas (§153, 22/09/2026)
==========================================================================
Adaptador entre a fila unificada de pistas (data/pistas_imprensa.json — busca web,
Querido Diário, imprensa) e o caminho testado de promoção a registro
(julgar_e_aplicar_descobertas.py: busca o documento, classifica ex-ante/resposta,
extrai número e data, aplica com backup + portões + rollback). Até aqui as duas
esteiras eram disjuntas: pistas da busca web nunca entravam no juiz (status e
campos de outro esquema), mesmo as de nível A com decreto nº e data.

Três funções, nenhuma apaga nada:

  --preparar    LEITURA ASSISTIDA. Para toda pista ainda sem decisão, de nível A ou B:
                busca o texto da URL (tolerante a falha), extrai número/data do ato,
                classifica natureza (EX_ANTE / RESPOSTA / DUVIDA) e grava tudo em
                `preparacao` na própria pista. Se a fonte é oficial, delega ao juiz
                (processar_pista) — que pode APLICAR sozinho quando ex-ante + citação
                completa + classificador confiante, exatamente como já faz para o vigia
                de imprensa. Roda na rodada de cadência (tem rede). NUNCA rebaixa nem
                descarta: só enriquece.

  --aceitar / --rejeitar / --adiar   DECISÃO HUMANA, por id de pista. Grava
                `decisao_humana` {decisao, motivo, ato, data, categoria, decidido_em}
                e muda o status. --aceitar promove pelo mesmo aplicar_municipal() do
                juiz (backup + portões + rollback). A rejeição é DA PISTA, não do
                município: outra pista do mesmo lugar continua entrando normalmente.

  --relatorio   Renderiza docs/FILA_PISTAS.md — legível, por município, nível A/B/C,
                com número/data/natureza pré-extraídos; decididas no fim, nunca fora.

Ids: sha1(ibge|url|trecho)[:10], estáveis entre rodadas (gravados na triagem).
Regra de ouro (§3.2, C10; decisão editorial de 22/09/2026 — "cuidado com falsos
negativos"): a máquina prepara e ordena; quem decide é a pessoa, pista a pista.
"""
import argparse, datetime, hashlib, json, sys
from collections import defaultdict
from coletores_base import ler, gravar, rodar_autoteste
from classificador_natureza import classificar, citacao_completa
from monitorar_imprensa_regional import parece_fonte_oficial
import julgar_e_aplicar_descobertas as juiz

STATUS_PENDENTE = "pista — promover a registro exige documento primário lido por humano"
DECIDIDAS = ("aceita_humana", "rejeitada_humana", "adiada_humana", "aplicada_automaticamente",
             "descartada_resposta", "revertida_erro_portao")


def id_pista(p: dict) -> str:
    base = f"{p.get('ibge') or ''}|{p.get('url') or ''}|{(p.get('trecho') or '')[:500]}"
    return hashlib.sha1(base.encode("utf-8")).hexdigest()[:10]


def garantir_ids(fila: dict) -> int:
    n = 0
    for p in fila["pistas"]:
        if not p.get("id"):
            p["id"] = id_pista(p); n += 1
    return n


def pendente(p: dict) -> bool:
    return p.get("status", "").startswith("pista") and p.get("status") not in DECIDIDAS


def citacao_do_trecho(p: dict):
    """Número e data extraídos do título+trecho da própria pista — sem rede. Fallback honesto
    quando o documento não é obtido (PDFs do Querido Diário: o buscador do juiz lê HTML) ou não
    traz o ato no texto. Caso real: Feira de Santana/BA trazia "DECRETO Nº 14.665 DE 21 DE AGOSTO
    DE 2026" no trecho e aparecia como "citação não extraída"."""
    return juiz.extrair_numero_e_data(f"{p.get('titulo') or ''} {p.get('trecho') or ''}")


# ---------------------------------------------------------------- preparação (leitura assistida)
def preparar(fila: dict, hoje: str, buscar=juiz.buscar_texto, processar=juiz.processar_pista,
             niveis=("A", "B"), limite=60) -> dict:
    """Enriquece pistas pendentes de nível A/B. Devolve contagem por resultado.
    `buscar`/`processar` injetáveis para o autoteste (sem rede)."""
    res = defaultdict(int)
    feitas = 0
    for p in fila["pistas"]:
        if feitas >= limite: break
        if not pendente(p) or p.get("nivel_confianca") not in niveis or p.get("preparacao"): continue
        feitas += 1
        prep = {"data": hoje, "fonte_oficial": bool(parece_fonte_oficial(p.get("url") or ""))}
        n_t, d_t = citacao_do_trecho(p)
        if n_t or d_t:
            prep["citacao_do_trecho"] = {"numero": n_t, "data_ato": d_t}
        texto = buscar(p.get("url") or "")
        if texto is None:
            prep.update({"resultado": "documento_nao_obtido", "numero": n_t, "data_ato": d_t,
                         "citacao_completa": citacao_completa(f"{n_t or ''} {d_t or ''}")})
            p["preparacao"] = prep; res["nao_obtido"] += 1; continue
        numero, data = juiz.extrair_numero_e_data(texto)
        numero, data = numero or n_t, data or d_t   # documento manda; trecho completa o que faltar
        natureza, motivo = classificar(texto)
        prep.update({"numero": numero, "data_ato": data, "citacao_completa": citacao_completa(f"{numero or ''} {data or ''}"),
                     "natureza": natureza, "motivo_natureza": motivo, "trecho_documento": texto[:600]})
        if prep["fonte_oficial"]:
            # delega ao juiz com o esquema que ele espera; ele pode aplicar sozinho (backup + portões + rollback)
            pj = {**p, "alvo": f"D-municipal/{p.get('municipio')}/{p.get('uf')}", "fonte_provavel_oficial": True}
            r = processar(pj, hoje)
            prep["juiz"] = r
            if r.get("decisao") == "APLICADA":
                p["status"] = "aplicada_automaticamente"; res["aplicada"] += 1
            elif r.get("decisao") == "REVERTIDA":
                p["status"] = "revertida_erro_portao"; res["revertida"] += 1
            else:
                res["fila_humana"] += 1
        else:
            prep["juiz"] = {"decisao": "FILA_HUMANA", "motivo": "fonte não oficial: só leitura assistida, decisão humana"}
            res["fila_humana"] += 1
        prep["resultado"] = "preparada"; p["preparacao"] = prep
    res["preparadas"] = feitas
    return dict(res)


# ---------------------------------------------------------------- decisões humanas
def decidir(fila: dict, pid: str, decisao: str, motivo: str = "", ato: str = "", data_ato: str = "",
            categoria: str = "plano", url_documento: str = "", hoje: str = "", aplicar=juiz.aplicar_municipal,
            backup=juiz.backup_dados, portoes=juiz.rodar_portoes, restaurar=juiz.restaurar_dados) -> dict:
    p = next((x for x in fila["pistas"] if x.get("id") == pid), None)
    if p is None: return {"ok": False, "motivo": f"id {pid} não encontrado"}
    reg = {"decisao": decisao, "motivo": motivo, "decidido_em": hoje or datetime.date.today().strftime("%d/%m/%Y")}
    if decisao == "rejeitar":
        p["status"] = "rejeitada_humana"; p["decisao_humana"] = reg
        return {"ok": True, "status": p["status"]}
    if decisao == "adiar":
        p["status"] = "adiada_humana"; p["decisao_humana"] = reg
        return {"ok": True, "status": p["status"]}
    if decisao == "aceitar":
        if not (ato and data_ato):
            return {"ok": False, "motivo": "aceitar exige --ato e --data (citação completa, §3.2) — nada aplicado"}
        if categoria != "plano":
            # aplicar_municipal() só cria registro 'plano'; outras categorias e atualizações de registro
            # existente ficam para edição direta em municipios.json pela editoria (§3.2) — registra a decisão.
            p["status"] = "aceita_humana"; p["decisao_humana"] = {**reg, "ato": ato, "data": data_ato, "categoria": categoria,
                                                                   "url_documento": url_documento, "aplicado": False,
                                                                   "nota": "categoria fora do caminho automático; aplicar manualmente"}
            return {"ok": True, "status": p["status"], "aplicado": False}
        texto = (p.get("preparacao") or {}).get("trecho_documento") or p.get("trecho") or ""
        bkp = backup()
        aplicado, msg = aplicar(p.get("municipio"), p.get("uf"), texto, ato, data_ato, url_documento or p.get("url"), reg["decidido_em"])
        if not aplicado:
            return {"ok": False, "motivo": msg}
        ok_p, saida = portoes()
        if not ok_p:
            restaurar(bkp)
            return {"ok": False, "motivo": "portão falhou após aplicar — desfeito", "detalhe": (saida or "")[-1500:]}
        p["status"] = "aceita_humana"; p["decisao_humana"] = {**reg, "ato": ato, "data": data_ato, "categoria": categoria,
                                                               "url_documento": url_documento, "aplicado": True}
        return {"ok": True, "status": p["status"], "aplicado": True}
    return {"ok": False, "motivo": f"decisão desconhecida: {decisao}"}


# ---------------------------------------------------------------- relatório legível
def relatorio(fila: dict) -> str:
    ordem = {"A": 0, "B": 1, "C": 2, None: 3}
    grupos = defaultdict(list)
    for p in fila["pistas"]:
        grupos[(p.get("uf"), p.get("municipio"))].append(p)
    def melhor(ps): return min((ordem.get(p.get("nivel_confianca"), 3) for p in ps if pendente(p)), default=9)
    chaves = sorted(grupos, key=lambda k: (melhor(grupos[k]), k[0] or "", k[1] or ""))
    pend = [p for p in fila["pistas"] if pendente(p)]
    dec = [p for p in fila["pistas"] if not pendente(p)]
    L = [f"# Fila de pistas — revisão humana", "",
         f"Gerado em {datetime.date.today().strftime('%d/%m/%Y')} · {len(pend)} pendente(s) · {len(dec)} decidida(s) · "
         f"A={sum(1 for p in pend if p.get('nivel_confianca')=='A')} B={sum(1 for p in pend if p.get('nivel_confianca')=='B')} "
         f"C={sum(1 for p in pend if p.get('nivel_confianca')=='C')}", "",
         "Como decidir: `python3 revisar_pistas.py --aceitar ID --ato \"Decreto nº X\" --data dd/mm/aaaa [--url-documento …]` · "
         "`--rejeitar ID --motivo \"…\"` · `--adiar ID`. Nada some: C fica no fim, decididas abaixo. Registro exige documento primário lido por pessoa (§3.2).", ""]
    for uf, mun in chaves:
        ps = sorted(grupos[(uf, mun)], key=lambda p: (0 if pendente(p) else 1, ordem.get(p.get("nivel_confianca"), 3), -(p.get("pontos_confianca") or 0)))
        if not any(pendente(p) for p in ps): continue
        L.append(f"## {mun}/{uf} — {sum(1 for p in ps if pendente(p))} pendente(s)")
        for p in ps:
            if not pendente(p): continue
            pr = p.get("preparacao") or {}
            if pr.get("numero"):
                cit = f"**{pr.get('numero')}**, {pr.get('data_ato')}"
            else:
                n_t, d_t = citacao_do_trecho(p)
                cit = f"**{n_t}**, {d_t} (do trecho)" if n_t else ("data " + d_t + " (do trecho)" if d_t else "citação não extraída")
            nat = pr.get("natureza") or "—"
            L.append(f"- `{p.get('id')}` · nível **{p.get('nivel_confianca')}** ({p.get('pontos_confianca')} pts) · {p.get('origem')} · {nat} · {cit}")
            if p.get("titulo"): L.append(f"  - título: {p['titulo'][:160]}")
            L.append(f"  - url: {p.get('url')}")
            L.append(f"  - trecho: {(p.get('trecho') or '')[:220].replace(chr(10),' ')}")
            if p.get("alertas"): L.append(f"  - ⚠ {', '.join(p['alertas'])}")
            if pr.get("juiz", {}).get("motivo"): L.append(f"  - juiz: {pr['juiz']['motivo'][:160]}")
        L.append("")
    if dec:
        L += ["---", f"## Decididas ({len(dec)}) — registro permanente, nunca apagadas", ""]
        for p in sorted(dec, key=lambda p: (p.get("uf") or "", p.get("municipio") or "")):
            d = p.get("decisao_humana") or p.get("julgamento_automatico") or {}
            L.append(f"- `{p.get('id')}` {p.get('municipio')}/{p.get('uf')} · {p.get('status')} · {d.get('motivo') or d.get('decisao') or ''}"[:220])
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- autoteste (hermético)
def autoteste():
    def fila_falsa():
        return {"pistas": [
            {"municipio": "Bagé", "uf": "RS", "ibge": "4301602", "url": "https://bage.rs.gov.br/d/1", "trecho": "x", "status": STATUS_PENDENTE, "nivel_confianca": "A", "origem": "busca_web"},
            {"municipio": "Marília", "uf": "SP", "ibge": "3529005", "url": "https://marilianoticia.com.br/a", "trecho": "y", "status": STATUS_PENDENTE, "nivel_confianca": "B", "origem": "busca_web"},
            {"municipio": "Ipixuna", "uf": "AM", "ibge": "1301803", "url": "https://x.pdf", "trecho": "z", "status": STATUS_PENDENTE, "nivel_confianca": "C", "origem": "busca_web"},
        ]}

    def t_ids_estaveis():
        f = fila_falsa(); garantir_ids(f); a = [p["id"] for p in f["pistas"]]
        g = fila_falsa(); garantir_ids(g); b = [p["id"] for p in g["pistas"]]
        return a == b and len(set(a)) == 3 and all(len(i) == 10 for i in a)

    def t_preparar_so_A_e_B_e_nunca_descarta():
        f = fila_falsa(); garantir_ids(f)
        r = preparar(f, "22/09/2026", buscar=lambda u: "DECRETO Nº 12, DE 10 DE JULHO DE 2026. Fica instituído o Plano de Contingência",
                     processar=lambda pj, h: {"decisao": "FILA_HUMANA", "motivo": "teste"})
        c = [p for p in f["pistas"] if p["nivel_confianca"] == "C"][0]
        return r["preparadas"] == 2 and "preparacao" not in c and all(pendente(p) for p in f["pistas"])

    def t_preparar_oficial_delega_e_nao_oficial_nao():
        f = fila_falsa(); garantir_ids(f); chamadas = []
        preparar(f, "22/09/2026", buscar=lambda u: "Decreto nº 1 de 01/01/2026 institui o plano",
                 processar=lambda pj, h: (chamadas.append(pj["alvo"]) or {"decisao": "FILA_HUMANA", "motivo": "m"}))
        return chamadas == ["D-municipal/Bagé/RS"]   # só a fonte oficial (.gov.br) chega ao juiz

    def t_preparar_documento_nao_obtido_nao_quebra():
        f = fila_falsa(); garantir_ids(f)
        r = preparar(f, "22/09/2026", buscar=lambda u: None, processar=lambda pj, h: {"decisao": "FILA_HUMANA"})
        return r["nao_obtido"] == 2 and all(pendente(p) for p in f["pistas"])

    def t_rejeitar_e_adiar_so_registram():
        f = fila_falsa(); garantir_ids(f); i = f["pistas"][1]["id"]
        r = decidir(f, i, "rejeitar", motivo="não é plano de contingência")
        r2 = decidir(f, f["pistas"][2]["id"], "adiar")
        return r["ok"] and f["pistas"][1]["status"] == "rejeitada_humana" and f["pistas"][1]["decisao_humana"]["motivo"] and \
               r2["ok"] and f["pistas"][2]["status"] == "adiada_humana" and len(f["pistas"]) == 3

    def t_aceitar_exige_citacao():
        f = fila_falsa(); garantir_ids(f)
        return decidir(f, f["pistas"][0]["id"], "aceitar")["ok"] is False

    def t_aceitar_aplica_com_portoes_e_desfaz_se_falhar():
        f = fila_falsa(); garantir_ids(f); i = f["pistas"][0]["id"]; log = []
        ok = decidir(f, i, "aceitar", ato="Decreto nº 12/2026", data_ato="10/07/2026", hoje="22/09/2026",
                     aplicar=lambda *a: (log.append("aplicou") or (True, "ok")), backup=lambda: "bkp",
                     portoes=lambda: (True, ""), restaurar=lambda b: log.append("restaurou"))
        g = fila_falsa(); garantir_ids(g)
        falha = decidir(g, i, "aceitar", ato="Decreto nº 12/2026", data_ato="10/07/2026", hoje="22/09/2026",
                        aplicar=lambda *a: (True, "ok"), backup=lambda: "bkp",
                        portoes=lambda: (False, "portão x"), restaurar=lambda b: log.append("restaurou"))
        return ok["ok"] and ok["aplicado"] and f["pistas"][0]["status"] == "aceita_humana" \
               and falha["ok"] is False and "restaurou" in log and pendente(g["pistas"][0])

    def t_relatorio_lista_pendentes_e_decididas():
        f = fila_falsa(); garantir_ids(f); decidir(f, f["pistas"][2]["id"], "rejeitar", motivo="ruído")
        md = relatorio(f)
        return "Bagé/RS" in md and "Marília/SP" in md and "Decididas (1)" in md and "rejeitada_humana" in md

    def t_citacao_do_trecho_sem_rede():
        # caso real: Feira de Santana/BA — decreto no trecho, documento é PDF (não lido)
        p = {"trecho": "www.diariooficial.feiradesantana.ba.gov.br 3 DECRETO Nº 14.665 DE 21 DE AGOSTO DE 2026"}
        n, d = citacao_do_trecho(p)
        f = {"pistas": [{**p, "municipio": "Feira de Santana", "uf": "BA", "ibge": "2910800", "url": "https://x.pdf",
                         "status": STATUS_PENDENTE, "nivel_confianca": "A", "origem": "querido_diario"}]}
        garantir_ids(f); preparar(f, "22/09/2026", buscar=lambda u: None, processar=lambda pj, h: {})
        pr = f["pistas"][0]["preparacao"]
        return bool(n) and "14.665" in n and pr["resultado"] == "documento_nao_obtido" and pr["numero"] == n and "14.665" in relatorio(f)

    return rodar_autoteste({
        "citação do trecho sem rede (caso Feira de Santana, PDF)": t_citacao_do_trecho_sem_rede,
        "ids estáveis entre rodadas": t_ids_estaveis,
        "preparar: só A e B, nunca descarta, C intocada": t_preparar_so_A_e_B_e_nunca_descarta,
        "preparar: fonte oficial delega ao juiz; não oficial só lê": t_preparar_oficial_delega_e_nao_oficial_nao,
        "preparar: documento não obtido não quebra nem rebaixa": t_preparar_documento_nao_obtido_nao_quebra,
        "rejeitar/adiar só registram (nada some)": t_rejeitar_e_adiar_so_registram,
        "aceitar exige citação completa": t_aceitar_exige_citacao,
        "aceitar aplica com portões e desfaz se falhar": t_aceitar_aplica_com_portoes_e_desfaz_se_falhar,
        "relatório lista pendentes por município e decididas no fim": t_relatorio_lista_pendentes_e_decididas,
    })


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--autoteste", action="store_true")
    ap.add_argument("--preparar", action="store_true")
    ap.add_argument("--limite", type=int, default=60)
    ap.add_argument("--relatorio", action="store_true")
    ap.add_argument("--aceitar", metavar="ID"); ap.add_argument("--rejeitar", metavar="ID"); ap.add_argument("--adiar", metavar="ID")
    ap.add_argument("--motivo", default=""); ap.add_argument("--ato", default=""); ap.add_argument("--data", default="")
    ap.add_argument("--categoria", default="plano"); ap.add_argument("--url-documento", default="")
    a = ap.parse_args()
    if a.autoteste: sys.exit(autoteste())
    fila = ler("pistas_imprensa.json") or {"pistas": []}
    hoje = datetime.date.today().strftime("%d/%m/%Y")
    novos = garantir_ids(fila)
    if a.preparar:
        print("preparação:", preparar(fila, hoje, limite=a.limite))
    for pid, dec in ((a.aceitar, "aceitar"), (a.rejeitar, "rejeitar"), (a.adiar, "adiar")):
        if pid:
            print(dec, pid, "→", decidir(fila, pid, dec, a.motivo, a.ato, a.data, a.categoria, a.url_documento, hoje))
    gravar("pistas_imprensa.json", fila)
    if a.relatorio or a.preparar or a.aceitar or a.rejeitar or a.adiar:
        md = relatorio(fila)
        open("docs/FILA_PISTAS.md", "w", encoding="utf-8").write(md)
        print(f"docs/FILA_PISTAS.md regravado ({novos} id(s) novo(s))")
