#!/usr/bin/env python3
"""
gerar_card_municipios.py — o card de cada município (§155, 22/09/2026)
======================================================================
Derivado compacto, data/municipios_card.json, lido pela consulta "seu município" em
prefeituras.html. Um objeto por código IBGE, SÓ para municípios com algo a dizer
(prioritário, ou registro no MARÉ, ou pista de imprensa) — os demais são "nada
localizado, não prioritário" por ausência, sem inflar o arquivo.

Campos: nome, uf, prioritario (aproximação populacional do Cadastro Nacional — mesmo
proxy de gerar_prioritarios.py), categoria no MARÉ (municipios.json; ausente = nao_verificado — A3-13),
documento/url/data quando há registro, e `imprensa`: até 3 pistas pendentes de nível A/B
(título, url, data, veículo = host), mais novas primeiro.

Decisão editorial de 22/09/2026: pista de imprensa NÃO pontua — nem "em elaboração". Ela
entra no card como link, rotulada como pista sem verificação, para que o leitor peça o
documento ao gestor público (o card diz como). Quando o documento oficial aparece e o juiz
aplica, a categoria sobe e a pista fica como proveniência.
"""
import json, os, sys
from datetime import date, datetime, timezone


def data_de_geracao() -> str:
    """Data do carimbo do derivado, do RELÓGIO FIXADO — nunca do relógio da parede.

    A regra e o seu porquê vivem em `coletores_base.data_do_corte`. Ela estava escrita aqui, e por
    estar só aqui não foi herdada pelo gerador seguinte: em 06/10/2026 o `CODEMAP.md` repetiu o
    mesmo defeito e derrubou nove publicações.
    """
    return data_do_corte().isoformat()


from urllib.parse import urlparse
from coletores_base import ler, gravar, rodar_autoteste, hoje_editorial, data_do_corte
from monitorar_imprensa_regional import parece_fonte_oficial

NIVEIS_NO_CARD = ("A", "B")
MAX_IMPRENSA = 3


def _host(u):
    try:
        return (urlparse(u or "").hostname or "").lower().removeprefix("www.")
    except Exception:  # noqa: BLE001
        return ""


def _corte(texto, limite):
    """O texto até `limite` caracteres, cortado na última palavra inteira e com reticências.
    Corte cego no meio da palavra (\"cobertura populaciona\") era o defeito. Função pura."""
    s = (texto or "").strip()
    if len(s) <= limite:
        return s
    return s[:limite].rsplit(" ", 1)[0].rstrip(" ,;:.-") + "…"


def _data_key(d):
    # "dd/mm/aaaa" → ordenável; ausente vai pro fim
    try:
        dd, mm, aa = (d or "").split("/"); return f"{aa}{mm}{dd}"
    except ValueError:
        return "0"


def planos_sem_contar(pistas) -> dict:
    """Pura. codigo_ibge → {motivo, url, fonte} do plano que o MARÉ localizou e que não entra no índice:
    `sem_data` (o juiz leu o plano e não achou data no texto) ou `nao_aberto` (o repositório estadual o
    indica, e o documento não foi lido). Lido sem data vence não aberto."""
    from atualizar_instrumentos_estaduais import REPOSITORIOS, repositorio_do_documento
    achados = {}
    for p in pistas:
        j, url = p.get("juiz") or {}, p.get("url_final") or p.get("url") or ""
        try:
            cod = int(p.get("ibge") or p.get("alvo") or 0)
        except (TypeError, ValueError):
            continue
        if not cod or j.get("promove"):
            continue
        uf_rep = repositorio_do_documento(url)
        if j.get("motivo") == "data_nao_confirmada" and j.get("leu_documento"):
            motivo = "sem_data"
        elif uf_rep and p.get("tipo") == "plano" and not j.get("leu_documento"):
            motivo = "nao_aberto"
        else:
            continue
        # 23/11/2026: o endereço que a fonte oficial indica não existe mais (DNS); a data é a da primeira constatação.
        fora = [t["em"] for t in p.get("juiz_tentativas") or [] if t.get("causa") == "destino_fora_do_ar"]
        if motivo == "nao_aberto" and fora and (p.get("juiz_tentativas") or [{}])[-1].get("causa") == "destino_fora_do_ar":
            motivo = "fora_do_ar"
        if cod not in achados or (achados[cod]["motivo"] != "sem_data" and motivo == "sem_data"):
            achados[cod] = {"motivo": motivo, "url": url, "fonte": REPOSITORIOS[uf_rep]["fonte"] if uf_rep else _host(url),
                            "nome": p.get("municipio"), "uf": p.get("uf"),
                            **({"desde": "/".join(reversed(fora[0].split("-")))} if motivo == "fora_do_ar" else {})}
    return achados


def montar(referencia, prioritarios, municipios, pistas, despesa_182=None, verificacao=None):
    """Pura. Devolve dict codigo_ibge(str) → card.

    `despesa_182` é a camada A do dinheiro próprio do município (§207): peso ZERO, uma linha só,
    com a classe quando não há valor. Ausente, o card simplesmente não tem a linha — e não tem
    zero, que é o que um leitor leria como "não gasta nada".

    `verificacao` é o livro de varredura (`verificacao_municipal.json`). Todo município varrido ganha
    `varredura: {nivel, data}` (a `ultima_verificacao` dele, não a da rodada) e, se nada foi
    localizado, a categoria `nao_localizado`; sem varredura no livro, segue `nao_verificado`
    (editoria, 19/10/2026: o cartão diz o que foi feito e o que falta)."""
    por_nome = {(m["nome"], m["uf"]): int(m["codigo_ibge"]) for m in referencia}
    prior = {int(m["codigo_ibge"]) for m in prioritarios}
    cards = {}
    for m in referencia:
        cod = int(m["codigo_ibge"])
        if cod in prior:
            cards[cod] = {"nome": m["nome"], "uf": m["uf"], "prioritario": True}
    for r in municipios:
        cod = por_nome.get((r.get("nome"), r.get("uf")))
        if cod is None:
            continue
        c = cards.setdefault(cod, {"nome": r["nome"], "uf": r["uf"], "prioritario": cod in prior})
        c.update({"categoria": r.get("categoria"), "documento": _corte(r.get("documento"), 220),
                  "url": r.get("url"), "data": r.get("data"), "fonte": _corte(r.get("fonte"), 120)})
        # DECISÃO DA EDITORIA, 03/10/2026: o plano publicado sem ato de aprovação localizado conta
        # no degrau da leitura, e a ficha diz isso. A marca viaja do registro para o card, que é o
        # que a página lê — sem ela, o leitor veria "plano localizado" sem saber que o ato que o
        # aprova não foi achado.
        if r.get("sem_ato_de_aprovacao"):
            c["sem_ato_de_aprovacao"] = True
    for p in pistas:
        st = p.get("status") or ""
        if not st.startswith("pista") or p.get("nivel_confianca") not in NIVEIS_NO_CARD:
            continue
        # §159: documento oficial candidato (cascata ou host oficial) não é "publicação na imprensa" — não entra aqui
        if (p.get("origem") or "").startswith("seguimento") or parece_fonte_oficial(p.get("url") or ""):
            continue
        try:
            cod = int(p.get("ibge") or 0)
        except (TypeError, ValueError):
            continue
        if not cod:
            continue
        c = cards.setdefault(cod, {"nome": p.get("municipio"), "uf": p.get("uf"), "prioritario": cod in prior})
        c.setdefault("imprensa", []).append({"titulo": _corte(p.get("titulo") or p.get("trecho"), 140),
                                             "url": p.get("url"), "data": p.get("data"), "veiculo": _host(p.get("url")),
                                             "nivel": p.get("nivel_confianca")})
    # §207: a linha do dinheiro próprio. Peso zero, e as três classes de ausência viajam como
    # classe, nunca como número — "sem lançamento na subfunção 182" NÃO é "não gasta em defesa
    # civil", porque muitos municípios lançam defesa civil em drenagem, urbanismo ou segurança.
    for cod, d in ((despesa_182 or {}).get("municipios") or {}).items():
        try:
            chave = int(cod)
        except (TypeError, ValueError):
            continue
        c = cards.get(chave)
        if c is None:
            continue                     # só municípios que já têm card; a linha não cria card
        c["defesa_civil_orcamento"] = {
            "exercicio": d.get("exercicio"),
            "classe": d.get("classe"),
            "rs_hab": d.get("rs_hab"),
            "liquidada": (d.get("valores") or {}).get("liquidada"),
            "fonte": "SICONFI (Tesouro Nacional)",
            "ressalva": "inclui preparação e resposta",
            "peso_no_indice": "nenhum",
        }
    for r in verificacao or []:
        try:
            cod = int(r.get("ibge"))
        except (TypeError, ValueError):
            continue
        if not r.get("nivel_verificacao") or not r.get("ultima_verificacao"):
            continue
        c = cards.setdefault(cod, {"nome": r.get("nome"), "uf": r.get("uf"), "prioritario": cod in prior})
        c["varredura"] = {"nivel": r["nivel_verificacao"], "data": r["ultima_verificacao"]}
        if c.get("categoria") in (None, "nao_verificado"):
            c["categoria"] = "nao_localizado"
    # 23/11/2026 (editoria): plano localizado que não entra no índice — lido e sem data no texto, ou
    # indicado no repositório estadual e não aberto até o corte — não é "não localizado". O cartão diz
    # o que foi achado e por que não conta; a categoria (o que conta no índice) não muda.
    for cod, info in planos_sem_contar(pistas).items():
        nome, uf = info.pop("nome"), info.pop("uf")
        c = cards.setdefault(cod, {"nome": nome, "uf": uf, "prioritario": cod in prior})
        if c.get("categoria") in (None, "nao_verificado", "nao_localizado"):
            c["plano_sem_contar"] = info
    for c in cards.values():
        if "imprensa" in c:
            c["imprensa"].sort(key=lambda x: _data_key(x.get("data")), reverse=True)
            c["imprensa"] = c["imprensa"][:MAX_IMPRENSA]
        # Sem registro e sem varredura no livro, é "nao_verificado"; com varredura, o laço acima já
        # pôs "nao_localizado" (editoria, 19/10/2026, HANDOVER_PROTEJA_SE_E_COLETA_MUNICIPAL §3.3).
        c.setdefault("categoria", "nao_verificado")
    return {str(k): v for k, v in sorted(cards.items())}


def gerar():
    ref = ler("municipios_ibge_referencia.json") or []
    prior = (ler("municipios_prioritarios.json") or {}).get("municipios", [])
    mun = ler("municipios.json") or []
    pis = (ler("pistas_imprensa.json") or {}).get("pistas", [])
    dsp = ler("financiamento/municipios/despesa_182.json") or {}
    cards = montar(ref, prior, mun, pis, dsp, ler("verificacao_municipal.json") or [])
    out = {"_governanca": ("Card por município (§155). DERIVADO — regenerado a cada rodada por gerar_card_municipios.py. "
                           "`prioritario` = aproximação populacional do Cadastro Nacional (não a lista oficial). "
                           "`imprensa` = pistas pendentes de nível A/B: NÃO pontuam no MARÉ; entram como link para que o "
                           "leitor peça o documento ao gestor. Só municípios com algo a dizer; sem registro e sem varredura = não verificado; "
                           "`varredura` = nível e data da última varredura do município. "
                           "`defesa_civil_orcamento` (§207) = despesa liquidada na subfunção 06.182 declarada ao SICONFI, "
                           "peso ZERO; classe de ausência nunca vira zero."),
           "gerado_em": data_de_geracao(), "total": len(cards),
           "com_registro": sum(1 for c in cards.values()
                               if c.get("categoria") not in ("nao_localizado", "nao_verificado")),
           "com_imprensa": sum(1 for c in cards.values() if c.get("imprensa")),
           "prioritarios": sum(1 for c in cards.values() if c.get("prioritario")),
           "com_despesa_182": sum(1 for c in cards.values() if c.get("defesa_civil_orcamento")),
           "municipios": cards}
    gravar("municipios_card.json", out, compacto=True)   # a página o carrega inteiro (§221)
    return out


def autoteste():
    ref = [{"nome": "Bagé", "uf": "RS", "codigo_ibge": 4301602}, {"nome": "Ipixuna", "uf": "AM", "codigo_ibge": 1301803},
           {"nome": "Marília", "uf": "SP", "codigo_ibge": 3529005}, {"nome": "Sem Nada", "uf": "SP", "codigo_ibge": 3500001}]
    prior = [{"codigo_ibge": 1301803}]
    dsp = {"municipios": {
        "4301602": {"exercicio": 2025, "classe": "com_lancamento", "rs_hab": 1.23,
                    "valores": {"liquidada": 100000.0}},
        "1301803": {"exercicio": 2025, "classe": "sem_lancamento_182", "rs_hab": None, "valores": {}},
        "9999999": {"exercicio": 2025, "classe": "com_lancamento", "rs_hab": 9.9, "valores": {"liquidada": 1.0}},
    }}
    mun = [{"nome": "Bagé", "uf": "RS", "categoria": "plano", "documento": "Decreto x", "url": "https://bage.rs.gov.br/d", "data": "10/07/2026"},
           {"nome": "Taió", "uf": "SC", "categoria": "plano", "documento": "Plano publicado",
            "url": "https://defesacivil.taio.sc.gov.br/p.pdf", "data": "2026",
            "sem_ato_de_aprovacao": True}]
    pis = [{"ibge": "3529005", "municipio": "Marília", "uf": "SP", "status": "pista — promover…", "nivel_confianca": "B", "titulo": "Marília prepara plano", "url": "https://www.marilianoticia.com.br/a", "data": "15/09/2026"},
           {"ibge": "3529005", "municipio": "Marília", "uf": "SP", "status": "pista — promover…", "nivel_confianca": "C", "titulo": "ruído", "url": "https://x", "data": "16/09/2026"},
           {"ibge": "3529005", "municipio": "Marília", "uf": "SP", "status": "rejeitada_pelo_juiz", "nivel_confianca": "A", "titulo": "rejeitada", "url": "https://y", "data": "17/09/2026"},
           {"ibge": "4301602", "municipio": "Bagé", "uf": "RS", "status": "pista — promover…", "nivel_confianca": "A", "titulo": "Bagé lança plano", "url": "https://g1.globo.com/b", "data": "01/09/2026"}]
    rs_pasta = ("https://rsgovbr-my.sharepoint.com/personal/casa-militar_casamilitar_rs_gov_br/Documents/Casa%20Militar/"
                "SUBCHEFIAS/SUBCHEFIA%20DE%20PROTE%C3%87%C3%83O%20E%20DEFESA%20CIVIL/3.%20Departamento%20de%20Gest%C3%A3o"
                "%20de%20Riscos/Divis%C3%A3o%20T%C3%A9cnica%20de%20Riscos/Planos%20de%20conting%C3%AAncia/"
                "TODOS%20PLANCONS%20RECEBIDOS/CREPDEC%2007/")
    pis += [{"ibge": "1301803", "municipio": "Ipixuna", "uf": "AM", "tipo": "plano", "status": "pista — recusada pelo juiz: data_nao_confirmada",
             "url": "https://ipixuna.am.gov.br/plancon.pdf", "juiz": {"promove": False, "motivo": "data_nao_confirmada", "leu_documento": True}},
            {"alvo": "4300001", "municipio": "Aratiba", "uf": "RS", "tipo": "plano", "status": "pista — na fila, aguardando busca dirigida e juiz",
             "url": rs_pasta + "PLANO%20Aratiba.url"},
            {"alvo": "4300002", "municipio": "Palmitinho", "uf": "RS", "tipo": "plano", "status": "pista — na fila, aguardando busca dirigida e juiz",
             "url": rs_pasta + "PLANO%20Palmitinho.url", "juiz_tentativas": [
                 {"em": "2026-11-19", "classe": "tecnica", "motivo": "documento_inacessivel"},
                 {"em": "2026-11-24", "classe": "tecnica", "motivo": "documento_inacessivel", "causa": "destino_fora_do_ar"}]},
            {"ibge": "4301602", "municipio": "Bagé", "uf": "RS", "tipo": "plano", "status": "pista — recusada pelo juiz: data_nao_confirmada",
             "url": "https://bage.rs.gov.br/p.pdf", "juiz": {"promove": False, "motivo": "data_nao_confirmada", "leu_documento": True}},
            {"ibge": "3500003", "municipio": "Recusado", "uf": "SP", "tipo": "plano", "status": "pista — recusada pelo juiz: minuta_ou_rascunho",
             "url": "https://recusado.sp.gov.br/p.pdf", "juiz": {"promove": False, "motivo": "minuta_ou_rascunho", "leu_documento": True}}]
    ver = [{"ibge": "1301803", "nome": "Ipixuna", "uf": "AM", "nivel_verificacao": "nacional", "ultima_verificacao": "2026-10-18"},
           {"ibge": "4301602", "nome": "Bagé", "uf": "RS", "nivel_verificacao": "estadual", "ultima_verificacao": "2026-10-19"},
           {"ibge": "3500002", "nome": "Só Varrido", "uf": "SP", "nivel_verificacao": "estadual", "ultima_verificacao": "2026-10-18"},
           {"ibge": "3529005", "nome": "Marília", "uf": "SP", "nivel_verificacao": None, "ultima_verificacao": None}]
    c = montar(ref, prior, mun, pis, dsp, ver)

    def t_plano_sem_data_nao_e_nao_localizado():
        a = c["1301803"]
        return (a["categoria"] == "nao_localizado" and a["plano_sem_contar"]["motivo"] == "sem_data"
                and a["plano_sem_contar"]["fonte"] == "ipixuna.am.gov.br")
    def t_repositorio_nao_aberto():
        a = c["4300001"]
        return (a["plano_sem_contar"]["motivo"] == "nao_aberto" and "Prepara RS" in a["plano_sem_contar"]["fonte"]
                and a["categoria"] == "nao_verificado" and (a["nome"], a["uf"]) == ("Aratiba", "RS"))
    def t_destino_fora_do_ar():
        a = c["4300002"]["plano_sem_contar"]
        return a["motivo"] == "fora_do_ar" and a["desde"] == "24/11/2026" and "desde" not in c["4300001"]["plano_sem_contar"]
    def t_plano_que_conta_nao_ganha_a_marca(): return "plano_sem_contar" not in c["4301602"]
    def t_outra_recusa_nao_vira_plano(): return "3500003" not in c

    def t_prioritario_sozinho_entra(): return c["1301803"]["prioritario"] is True and "varredura" in c["1301803"]
    def t_sem_nada_nao_entra(): return "3500001" not in c

    def t_corte_em_palavra_inteira():
        longo = "cobertura populacional " * 20
        r = _corte(longo, 220)
        return len(r) <= 221 and r.endswith("…") and r[:-1].split()[-1] in ("cobertura", "populacional") and _corte("curto", 220) == "curto" and _corte(None, 5) == ""

    def t_despesa_182_entra_com_a_ressalva():
        d = c["4301602"]["defesa_civil_orcamento"]
        return (d["rs_hab"] == 1.23 and d["liquidada"] == 100000.0 and d["exercicio"] == 2025
                and d["peso_no_indice"] == "nenhum" and "preparação e resposta" in d["ressalva"])

    def t_despesa_182_ausencia_nao_vira_zero():
        """Classe de ausência viaja como CLASSE, nunca como número. Um zero aqui seria lido como
        'este município não gasta nada em defesa civil', que é conclusão que o dado não autoriza."""
        d = c["1301803"]["defesa_civil_orcamento"]
        return d["classe"] == "sem_lancamento_182" and d["rs_hab"] is None and d["liquidada"] is None

    def t_despesa_182_nao_cria_card():
        """Município que só tem despesa e nada mais não passa a existir no card por causa dela."""
        return "9999999" not in c
    def t_varredura_sem_achado_vira_nao_localizado():
        a = c["1301803"]
        return a["categoria"] == "nao_localizado" and a["varredura"] == {"nivel": "nacional", "data": "2026-10-18"}
    def t_varredura_nao_apaga_registro():
        b = c["4301602"]
        return b["categoria"] == "plano" and b["varredura"] == {"nivel": "estadual", "data": "2026-10-19"}
    def t_varrido_sem_card_ganha_card():
        return c["3500002"]["categoria"] == "nao_localizado" and c["3500002"]["varredura"]["nivel"] == "estadual"
    def t_sem_varredura_segue_nao_verificado():
        return "varredura" not in c["3529005"] and c["3529005"]["categoria"] == "nao_verificado"
    def t_registro_e_tag(): return c["4301602"]["categoria"] == "plano" and c["4301602"]["prioritario"] is False and c["4301602"]["url"]
    def t_imprensa_so_A_B_pendentes(): return [x["titulo"] for x in c["3529005"]["imprensa"]] == ["Marília prepara plano"] and c["3529005"]["categoria"] == "nao_verificado"
    def t_imprensa_nao_vira_categoria(): return c["3529005"].get("categoria") == "nao_verificado"   # peso zero, por construção
    def t_veiculo_sem_www(): return c["3529005"]["imprensa"][0]["veiculo"] == "marilianoticia.com.br"
    def t_registro_mantem_imprensa_como_proveniencia(): return c["4301602"]["imprensa"][0]["veiculo"] == "g1.globo.com"
    def t_carimbo_segue_o_relogio_fixado():
        """§193: o carimbo do derivado não pode depender do relógio da parede. Com SOURCE_DATE_EPOCH
        posto, a data sai dele; sem ele, cai no dia de hoje. Foi a falta disso que fez o CI reprovar
        na virada da data em UTC, num ramo que não tinha nada a ver com o assunto."""
        anterior = os.environ.get("SOURCE_DATE_EPOCH")
        try:
            ep = lambda a, m, d: str(int(datetime(a, m, d, tzinfo=timezone.utc).timestamp()))
            os.environ["SOURCE_DATE_EPOCH"] = ep(2026, 9, 10)   # o corte desta edição
            fixo = data_de_geracao()
            os.environ["SOURCE_DATE_EPOCH"] = ep(2026, 9, 21)
            outro = data_de_geracao()
            os.environ.pop("SOURCE_DATE_EPOCH")
            livre = data_de_geracao()
        finally:
            if anterior is None: os.environ.pop("SOURCE_DATE_EPOCH", None)
            else: os.environ["SOURCE_DATE_EPOCH"] = anterior
        return fixo == "2026-09-10" and outro == "2026-09-21" and livre == hoje_editorial().isoformat()

    return rodar_autoteste({
        "§193 carimbo do derivado segue o relógio fixado, não o da parede": t_carimbo_segue_o_relogio_fixado,
        "23/11: plano lido sem data não é 'não localizado' (a categoria não muda)": t_plano_sem_data_nao_e_nao_localizado,
        "23/11: plano indicado no repositório estadual e não aberto ganha card": t_repositorio_nao_aberto,
        "23/11: município com plano que conta não ganha a marca": t_plano_que_conta_nao_ganha_a_marca,
        "23/11: destino que não existe vira fora_do_ar, com a data da primeira constatação": t_destino_fora_do_ar,
        "23/11: outra recusa do juiz não vira plano localizado": t_outra_recusa_nao_vira_plano,
        "prioritário sem registro entra, com a varredura do livro": t_prioritario_sozinho_entra,
        "varredura sem achado: nao_localizado com nível e data do município": t_varredura_sem_achado_vira_nao_localizado,
        "varredura não apaga o registro que existe": t_varredura_nao_apaga_registro,
        "município varrido sem card ganha card": t_varrido_sem_card_ganha_card,
        "sem varredura no livro segue nao_verificado, sem data": t_sem_varredura_segue_nao_verificado,
        "município sem nada não entra (ausência = nada localizado)": t_sem_nada_nao_entra,
        "corte do texto em palavra inteira, com reticências": t_corte_em_palavra_inteira,
        "registro no MARÉ + tag prioritário false": t_registro_e_tag,
        "imprensa: só pistas pendentes de nível A/B (C e rejeitadas ficam fora)": t_imprensa_so_A_B_pendentes,
        "imprensa nunca vira categoria (peso zero por construção)": t_imprensa_nao_vira_categoria,
        "veículo = host sem www": t_veiculo_sem_www,
        "município com registro mantém a pista como proveniência": t_registro_mantem_imprensa_como_proveniencia,
        "§207 despesa na 182 entra no card com a ressalva e peso zero": t_despesa_182_entra_com_a_ressalva,
        "§207 classe de ausência nunca vira zero no card": t_despesa_182_ausencia_nao_vira_zero,
        "§207 despesa sozinha não cria card de município": t_despesa_182_nao_cria_card,
    })


if __name__ == "__main__":
    if "--autoteste" in sys.argv:
        sys.exit(autoteste())
    o = gerar()
    print(f"✓ data/municipios_card.json: {o['total']} municípios · {o['com_registro']} com registro · {o['com_imprensa']} com pista de imprensa · {o['prioritarios']} prioritários")
