#!/usr/bin/env python3
"""
revisar_pistas.py — leitura assistida das pistas (§153, 22/09/2026; 09/10/2026, lote 2.9)
=========================================================================================

09/10/2026 (lote 2.9, A1-17): a etapa humana acabou. Saíram `--aceitar/--rejeitar/--adiar`,
`decisao_humana` e o relatório `docs/FILA_PISTAS.md`: não há pessoa lendo a fila, e o que decide é
o juiz automático (`julgar_filas.py`) sobre documento oficial lido pela máquina. O que fica é a
leitura assistida (`--preparar`). O texto abaixo é o histórico do desenho de 22/09.
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

Ids: sha1(ibge|url|trecho)[:10], estáveis entre rodadas (gravados na triagem).
A máquina prepara, e o juiz automático decide (`julgar_filas.py`, codebook versionado).
"""
import argparse, datetime, hashlib, json, re, sys, unicodedata
from urllib.parse import urlparse
from collections import defaultdict
from coletores_base import ler, gravar, rodar_autoteste, hoje_editorial
from classificador_natureza import classificar, citacao_completa
from classificar_pista_civil import triagem_completa
from monitorar_imprensa_regional import parece_fonte_oficial
import julgar_e_aplicar_descobertas as juiz

STATUS_PENDENTE = "pista — na fila, aguardando busca dirigida e juiz"
DECIDIDAS = ("aplicada_automaticamente", "descartada_resposta", "revertida_erro_portao")
DECIDIDAS_FINAIS = tuple(d for d in DECIDIDAS if d != "revertida_erro_portao")


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
    # 22/09/2026 (§156): "revertida_erro_portao" não é decisão — o juiz aplicou e um portão falhou por
    # causa alheia ao dado (rodada #6: node_modules ausente). Continua pendente e é refeita na próxima.
    st = p.get("status", "")
    return (st.startswith("pista") or st == "revertida_erro_portao") and st not in DECIDIDAS_FINAIS


def citacao_do_trecho(p: dict):
    """Número e data extraídos do título+trecho da própria pista — sem rede. Fallback honesto
    quando o documento não é obtido (PDFs do Querido Diário: o buscador do juiz lê HTML) ou não
    traz o ato no texto. Caso real: Feira de Santana/BA trazia "DECRETO Nº 14.665 DE 21 DE AGOSTO
    DE 2026" no trecho e aparecia como "citação não extraída"."""
    return juiz.extrair_numero_e_data(f"{p.get('titulo') or ''} {p.get('trecho') or ''}")


# ---------------------------------------------------------------- portão automático (§156)
# Decisão editorial de 22/09/2026: a máquina só pontua com o ATO publicado, lido e verificado — nunca notícia,
# nem notícia em portal oficial. Condições CUMULATIVAS; falhou uma, abstenção registrada (nada é descartado).
# Calibrado contra casos reais da rodada #6 e da preparação local de 22/09: "Lei nº 14.133" (lei federal de
# licitações citada no texto) em Sátiro Dias/BA e Itapirapuã Paulista/SP; decreto de 2021 em Andradina/SP; lei
# municipal de 2021 em Guaraniaçu/PR; "Lei 17 · 2026" sem data completa; PDF de 2024 em Nova Iguaçu/RJ.
HOST_DIARIO = re.compile(r"queridodiario|diario|imprensaoficial|\bdom\.|\bdoe\.", re.I)
LEIS_FEDERAIS_CITADAS = {"14133", "12608", "8666", "10520", "13019", "8080", "12527", "12340", "13709", "9784",
                         "6938", "12651", "14944", "10257", "11445", "12305", "14026", "4320", "101"}
RE_TEXTO_NORMATIVO = re.compile(r"\bart\.?\s*1\s*[º°o]?\b|\bfica(?:m)?\s+(?:institu|aprovad|criad)", re.I)
RE_DATA_PLENA = re.compile(r"^(\d{1,2})[/.](\d{1,2})[/.](\d{4})$")
PREP_VERSAO = 2   # §156: foco na janela do ato + portão automático; preparação de versão anterior é refeita uma vez
ANO_MIN_AUTOMATICO = 2026   # ato anterior pode ser edição anterior (plano_antigo, 0,6): quem decide é a pessoa
# alertas da triagem de confiança que, sozinhos, tiram a pista do caminho automático (homônimo MG/BA etc.)
ALERTAS_BLOQUEIAM = {"uf_divergente_na_url", "municipio_citado_de_passagem", "risco_errado_no_titulo", "ano_anterior_ao_ciclo"}


def _sem_acento(t):
    return unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().lower()


def portao_automatico(p: dict, prep: dict, janela: str):
    """(ok, motivo). Só com ok=True a pista é entregue ao juiz, que ainda aplica com backup + portões + rollback."""
    url = p.get("url") or ""
    host = (urlparse(url).hostname or "").lower()
    if not prep.get("fonte_oficial"):
        return False, "fonte não oficial"
    if not (HOST_DIARIO.search(host) or url.lower().split("?")[0].endswith(".pdf")):
        return False, "página oficial que não é o ato publicado (notícia em portal) — exige diário oficial ou PDF do ato"
    if prep.get("natureza") != "EX_ANTE":
        return False, f"natureza {prep.get('natureza')} — só ex-ante é aplicado sozinho"
    al = ALERTAS_BLOQUEIAM & set(p.get("alertas") or [])
    if al:
        return False, "alerta da triagem de confiança: " + ", ".join(sorted(al))
    m = RE_DATA_PLENA.match((prep.get("data_ato") or "").strip())
    if not m:
        return False, f"data do ato incompleta ({prep.get('data_ato')})"
    try:
        d_ato = datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return False, f"data do ato inválida ({prep.get('data_ato')})"
    if d_ato.year < ANO_MIN_AUTOMATICO:
        return False, f"ato de {m.group(3)} — pode ser edição anterior; abstenção registrada"
    hoje_d = hoje_editorial()
    if d_ato > hoje_d:
        return False, f"data do ato no futuro ({prep.get('data_ato')}) — leitura errada provável"
    digs = re.sub(r"\D", "", prep.get("numero") or "")
    eh_lei = re.search(r"\blei\b", _sem_acento(prep.get("numero")))
    # só LEI pode ser a federal citada: "Decreto nº 101" municipal não é a LC 101 (achado ao revisar o portão, 22/09)
    if eh_lei and (digs in LEIS_FEDERAIS_CITADAS or not re.search(r"municipal", _sem_acento(janela[:200]))):
        return False, f"número extraído parece lei citada, não o ato instituinte ({prep.get('numero')})"
    if not RE_TEXTO_NORMATIVO.search(janela or ""):
        return False, "sem texto normativo articulado (Art. 1º / fica instituído)"
    tri = triagem_completa(janela or "")
    if tri.get("destino") != "registro_defesa_civil":
        return False, f"triagem do ato: destino={tri.get('destino')} (autoridade={tri.get('autoridade')}, objeto={tri.get('objeto')})"
    if _sem_acento(p.get("municipio")) not in _sem_acento(janela):
        return False, "município não nomeado no texto do ato"
    return True, "ato publicado, ex-ante, citação completa de 2026, executivo, família do ciclo, município nomeado"


# ---------------------------------------------------------------- preparação (leitura assistida)
def focar(texto: str, pista: dict, antes=150, depois=3500) -> str:
    """22/09/2026 (§156, achado real — Feira de Santana/BA): um diário oficial traz dezenas de atos; classificar
    o documento inteiro devolvia DUVIDA e extraía o número do PRIMEIRO ato da edição (e "4574", nº de lei, como
    ano). Recorta a janela ao redor da âncora da pista (início do trecho; senão o termo de plano; senão o nome do
    município) — o mesmo recorte que, feito à mão no teste de 22/09, deu EX_ANTE + 21/08/2026. Sem âncora, texto todo."""
    if not texto:
        return texto
    import re, unicodedata
    # normalização que PRESERVA o comprimento (1 char → 1 char): os índices achados em T valem em `texto`.
    # (encode("ascii","ignore") encurta — "Nº"→"N" — e a janela recortada derrapa alguns caracteres.)
    def norm(t):
        out = []
        for ch in (t or ""):
            d = unicodedata.normalize("NFKD", ch)
            out.append((d[0] if d and d[0].isascii() else "_").lower())
        return "".join(out)
    T = norm(texto)
    assert len(T) == len(texto)
    ancoras = []
    # 1º: o número do ato citado no trecho da pista ("14.665") — único no diário; o cabeçalho corrido da página
    # ("garante a autenticidade deste documento…") repete em toda página e, como âncora, caía na 1ª página (14.664).
    n_t, _ = juiz.extrair_numero_e_data(f"{pista.get('titulo') or ''} {pista.get('trecho') or ''}")
    if n_t:
        digs = re.sub(r"\D", "", n_t.split("º")[-1].split("°")[-1].split("n")[-1]) if n_t else ""
        m_d = re.search(r"\d[\d\.]{2,}", n_t)
        if m_d:
            ancoras.append(norm(m_d.group(0)))
    tr = norm(pista.get("trecho") or "").strip()
    ancoras += ["plano de contingencia", "plano municipal de protecao", "plancon", "plano preventivo"]
    if len(tr) >= 30:
        ancoras += [tr[i:i+40] for i in (0, 40, 80) if len(tr) > i + 30]
    if pista.get("municipio"):
        ancoras.append(norm(pista["municipio"]))
    for a in ancoras:
        i = T.find(a)
        if i >= 0:
            # começa no cabeçalho do próprio ato ("DECRETO Nº …") se ele estiver logo antes da âncora — assim um
            # ato anterior encostado (dentro de `antes`) não entra e não vira o "primeiro número" da janela
            cab = None
            for m in re.finditer(r"\b(decreto|lei|portaria|resolu[cç][aã]o)\b", T[max(0, i - antes): i]):
                cab = max(0, i - antes) + m.start()
            ini = cab if cab is not None else max(0, i - antes)
            return texto[ini: i + depois]
    return texto


def preparar(fila: dict, hoje: str, buscar=juiz.buscar_texto, processar=juiz.processar_pista,
             niveis=("A", "B"), limite=60) -> dict:
    """Enriquece pistas pendentes de nível A/B. Devolve contagem por resultado.
    `buscar`/`processar` injetáveis para o autoteste (sem rede)."""
    res = defaultdict(int)
    feitas = 0
    # §159: candidatos da cascata notícia→documento (origem "seguimento_*") vêm primeiro e não dependem do nível
    # de confiança — o título deles costuma ser o nome do arquivo; quem decide é o portão automático.
    eh_seg = lambda x: (x.get("origem") or "").startswith("seguimento")
    for p in sorted(fila["pistas"], key=lambda x: 0 if eh_seg(x) else 1):
        if feitas >= limite: break
        if not pendente(p) or (p.get("nivel_confianca") not in niveis and not eh_seg(p)): continue
        ja = p.get("preparacao") or {}
        if ja and ja.get("versao") == PREP_VERSAO and (ja.get("juiz") or {}).get("decisao") != "REVERTIDA":
            continue   # refaz: revertidas por portão e preparações de versão anterior (sem foco/portão)
        feitas += 1
        prep = {"data": hoje, "versao": PREP_VERSAO, "fonte_oficial": bool(parece_fonte_oficial(p.get("url") or ""))}
        n_t, d_t = citacao_do_trecho(p)
        if n_t or d_t:
            prep["citacao_do_trecho"] = {"numero": n_t, "data_ato": d_t}
        texto = buscar(p.get("url") or "")
        if texto is not None:
            texto = focar(texto, p)   # §156: janela ao redor da âncora, não o diário inteiro
        if texto is None:
            prep.update({"resultado": "documento_nao_obtido", "numero": n_t, "data_ato": d_t,
                         "citacao_completa": citacao_completa(f"{n_t or ''} {d_t or ''}")})
            p["preparacao"] = prep; res["nao_obtido"] += 1; continue
        numero, data = juiz.extrair_numero_e_data(texto)
        numero, data = numero or n_t, data or d_t   # documento manda; trecho completa o que faltar
        natureza, motivo = classificar(texto)
        prep.update({"numero": numero, "data_ato": data, "citacao_completa": citacao_completa(f"{numero or ''} {data or ''}"),
                     "natureza": natureza, "motivo_natureza": motivo, "trecho_documento": texto[:600]})
        ok_auto, motivo_auto = portao_automatico(p, prep, texto)
        prep["portao_automatico"] = {"ok": ok_auto, "motivo": motivo_auto}
        if ok_auto:
            # delega ao juiz com o esquema que ele espera; ele pode aplicar sozinho (backup + portões + rollback)
            pj = {**p, "alvo": f"D-municipal/{p.get('municipio')}/{p.get('uf')}", "fonte_provavel_oficial": True}
            r = processar(pj, hoje, buscar=lambda _u, _t=texto: _t)   # §156: o juiz recebe o texto já focado, não rebaixa nem refaz o download
            prep["juiz"] = r
            if r.get("decisao") == "APLICADA":
                p["status"] = "aplicada_automaticamente"; res["aplicada"] += 1
            elif r.get("decisao") == "REVERTIDA":
                p["status"] = "revertida_erro_portao"; res["revertida"] += 1
            else:
                res["abstencao"] += 1
        else:
            prep["juiz"] = {"decisao": "ABSTENCAO", "motivo": f"portão automático: {motivo_auto}"}
            res["abstencao"] += 1
        prep["resultado"] = "preparada"; p["preparacao"] = prep
    res["preparadas"] = feitas
    return dict(res)


# ---------------------------------------------------------------- autoteste (hermético)
def autoteste():
    def fila_falsa():
        return {"pistas": [
            {"municipio": "Bagé", "uf": "RS", "ibge": "4301602", "url": "https://data.queridodiario.ok.org.br/4301602/2026-07-10/a.pdf", "trecho": "x", "status": STATUS_PENDENTE, "nivel_confianca": "A", "origem": "busca_web"},
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
                     processar=lambda pj, h, **kw: {"decisao": "ABSTENCAO", "motivo": "teste"})
        c = [p for p in f["pistas"] if p["nivel_confianca"] == "C"][0]
        return r["preparadas"] == 2 and "preparacao" not in c and all(pendente(p) for p in f["pistas"])

    def t_preparar_oficial_delega_e_nao_oficial_nao():
        f = fila_falsa(); garantir_ids(f); chamadas = []
        preparar(f, "22/09/2026", buscar=lambda u: "DECRETO Nº 12, DE 10 DE JULHO DE 2026. Institui o Plano de Contingência de Proteção e Defesa Civil do Município de Bagé para chuvas e enchentes. O Prefeito Municipal de Bagé, no uso de suas atribuições, DECRETA: Art. 1º Fica instituído o Plano de Contingência.",
                 processar=lambda pj, h, **kw: (chamadas.append(pj["alvo"]) or {"decisao": "ABSTENCAO", "motivo": "m"}))
        return chamadas == ["D-municipal/Bagé/RS"]   # só a fonte oficial (.gov.br) chega ao juiz

    def t_preparar_documento_nao_obtido_nao_quebra():
        f = fila_falsa(); garantir_ids(f)
        r = preparar(f, "22/09/2026", buscar=lambda u: None, processar=lambda pj, h, **kw: {"decisao": "ABSTENCAO"})
        return r["nao_obtido"] == 2 and all(pendente(p) for p in f["pistas"])

    def t_citacao_do_trecho_sem_rede():
        # caso real: Feira de Santana/BA — decreto no trecho, documento é PDF (não lido)
        p = {"trecho": "www.diariooficial.feiradesantana.ba.gov.br 3 DECRETO Nº 14.665 DE 21 DE AGOSTO DE 2026"}
        n, d = citacao_do_trecho(p)
        f = {"pistas": [{**p, "municipio": "Feira de Santana", "uf": "BA", "ibge": "2910800", "url": "https://x.pdf",
                         "status": STATUS_PENDENTE, "nivel_confianca": "A", "origem": "querido_diario"}]}
        garantir_ids(f); preparar(f, "22/09/2026", buscar=lambda u: None, processar=lambda pj, h, **kw: {})
        pr = f["pistas"][0]["preparacao"]
        return bool(n) and "14.665" in n and pr["resultado"] == "documento_nao_obtido" and pr["numero"] == n

    def t_focar_diario_com_varios_atos():
        # caso real (rodada #6): diário inteiro → primeiro ato ("Lei nº 4.574") e "4574" como ano; focado → o decreto do plano
        diario = ("ANO XII EDIÇÃO 3605 DATA 22/08/2026 LEI Nº 4.574 DE 10 DE MAIO DE 2026 dispõe sobre feriados. " * 3
                  + "PORTARIA Nº 77 nomeia servidor. " * 5
                  + "DECRETO Nº 14.665 DE 21 DE AGOSTO DE 2026 Institui o Plano de Contingência do Município de Feira de Santana, "
                    "e dá outras providencias. O Prefeito Municipal, no uso de suas atribuições ... Art. 1º Fica instituído o Plano de Contingência ... ")
        pista = {"municipio": "Feira de Santana", "trecho": "DECRETO Nº 14.665 DE 21 DE AGOSTO DE 2026 Institui o Plano de Contingência do Município"}
        foco = focar(diario, pista)
        n, d = juiz.extrair_numero_e_data(foco)
        return "14.665" in (n or "") and d == "21/08/2026" and "LEI Nº 4.574" not in foco[:60]

    def t_revertida_por_portao_e_refeita():
        f = fila_falsa(); garantir_ids(f)
        f["pistas"][0]["status"] = "revertida_erro_portao"
        f["pistas"][0]["preparacao"] = {"juiz": {"decisao": "REVERTIDA"}}
        vistos = []
        preparar(f, "22/09/2026", buscar=lambda u: "DECRETO Nº 12, DE 10 DE JULHO DE 2026. Institui o Plano de Contingência de Proteção e Defesa Civil do Município de Bagé para chuvas e enchentes. O Prefeito Municipal de Bagé, no uso de suas atribuições, DECRETA: Art. 1º Fica instituído o Plano de Contingência.",
                 processar=lambda pj, h, **kw: (vistos.append(pj["municipio"]) or {"decisao": "APLICADA"}))
        return vistos == ["Bagé"] and f["pistas"][0]["status"] == "aplicada_automaticamente"

    def _gate(url, texto, municipio="Bagé"):
        p = {"municipio": municipio, "url": url, "trecho": ""}
        n, d = juiz.extrair_numero_e_data(texto)
        nat, _ = classificar(texto)
        return portao_automatico(p, {"fonte_oficial": parece_fonte_oficial(url), "numero": n, "data_ato": d, "natureza": nat}, texto)

    QD = "https://data.queridodiario.ok.org.br/4301602/2026-07-10/a.pdf"
    def t_portao_passa_ato_real(): return _gate(QD, "DECRETO Nº 12, DE 10 DE JULHO DE 2026. Institui o Plano de Contingência de Proteção e Defesa Civil do Município de Bagé para chuvas e enchentes. O Prefeito Municipal de Bagé, no uso de suas atribuições, DECRETA: Art. 1º Fica instituído o Plano de Contingência.")[0] is True
    def t_portao_barra_lei_federal_citada():   # caso real Sátiro Dias/BA, Itapirapuã Paulista/SP
        return _gate(QD, "Lei nº 14.133, de 01/04/2021, e o Plano de Contingência do Município de Bagé. Art. 1º Fica instituído")[0] is False
    def t_portao_barra_ato_antigo():            # caso real Andradina/SP, Guaraniaçu/PR
        return _gate(QD, "DECRETO Nº 7.123, DE 10 DE MARÇO DE 2021. Institui o Plano de Contingência de Bagé. Art. 1º Fica instituído o Plano de Contingência para chuvas.")[0] is False
    def t_portao_barra_noticia_em_portal_oficial():   # notícia em .gov.br não é o ato
        return _gate("https://bage.rs.gov.br/noticias/prefeito-assina-plano", "DECRETO Nº 12, DE 10 DE JULHO DE 2026. Institui o Plano de Contingência de Proteção e Defesa Civil do Município de Bagé para chuvas e enchentes. O Prefeito Municipal de Bagé, no uso de suas atribuições, DECRETA: Art. 1º Fica instituído o Plano de Contingência.")[0] is False
    def t_portao_barra_municipio_errado():      # ato de outro município no mesmo diário
        return _gate(QD, "DECRETO Nº 12, DE 10 DE JULHO DE 2026. Institui o Plano de Contingência de Proteção e Defesa Civil do Município de Bagé para chuvas e enchentes. O Prefeito Municipal de Bagé, no uso de suas atribuições, DECRETA: Art. 1º Fica instituído o Plano de Contingência.", municipio="Pelotas")[0] is False
    def t_portao_barra_frio():                  # fora do objeto (Decisão 2)
        return _gate(QD, "DECRETO Nº 10, DE 14 DE JULHO DE 2026. Institui o Plano de Contingência para Ondas de Frio e Geadas de Bagé. Art. 1º Fica instituído")[0] is False

    def t_portao_lacunas_fechadas():
        ato = ("DECRETO Nº 101, DE 10 DE JULHO DE 2026. Institui o Plano de Contingência de Proteção e Defesa Civil do "
               "Município de Bagé para chuvas e enchentes. DECRETA: Art. 1º Fica instituído o Plano de Contingência.")
        base = {"municipio": "Bagé", "uf": "RS", "url": "https://data.queridodiario.ok.org.br/4301602/x.pdf"}
        prep = {"fonte_oficial": True, "natureza": "EX_ANTE", "numero": "DECRETO Nº 101", "data_ato": "10/07/2026"}
        ok_decreto_101, _ = portao_automatico(base, prep, ato)                                   # decreto municipal nº 101 ≠ LC 101
        homonimo, m1 = portao_automatico({**base, "alertas": ["uf_divergente_na_url"]}, prep, ato)
        invalida, m2 = portao_automatico(base, {**prep, "data_ato": "31/02/2026"}, ato)
        futura, m3 = portao_automatico(base, {**prep, "data_ato": "10/12/2099"}, ato)
        lei_fed, m4 = portao_automatico(base, {**prep, "numero": "Lei nº 14.133", "data_ato": "01/04/2026"}, ato)
        return ok_decreto_101 and not homonimo and "uf_divergente" in m1 and not invalida and "inválida" in m2 \
               and not futura and not lei_fed

    def t_preparacao_antiga_e_refeita_uma_vez():
        f = fila_falsa(); garantir_ids(f)
        f["pistas"][0]["preparacao"] = {"natureza": "DUVIDA", "juiz": {"decisao": "ABSTENCAO"}}   # versão 1, sem foco
        n1 = preparar(f, "22/09/2026", buscar=lambda u: "x", processar=lambda pj, h, **kw: {"decisao": "ABSTENCAO"})["preparadas"]
        n2 = preparar(f, "22/09/2026", buscar=lambda u: "x", processar=lambda pj, h, **kw: {"decisao": "ABSTENCAO"})["preparadas"]
        return n1 == 2 and n2 == 0 and f["pistas"][0]["preparacao"]["versao"] == PREP_VERSAO

    return rodar_autoteste({
        "preparação de versão anterior é refeita uma vez (e só uma)": t_preparacao_antiga_e_refeita_uma_vez,
        "portão: decreto nº 101 passa; homônimo, data inválida/futura e Lei 14.133 barram": t_portao_lacunas_fechadas,
        "portão automático: ato real publicado passa": t_portao_passa_ato_real,
        "portão automático: lei federal citada não vira ato (caso Sátiro Dias)": t_portao_barra_lei_federal_citada,
        "portão automático: ato de 2021 vai à pessoa (caso Andradina/Guaraniaçu)": t_portao_barra_ato_antigo,
        "portão automático: notícia em portal oficial não é o ato": t_portao_barra_noticia_em_portal_oficial,
        "portão automático: município não nomeado no ato": t_portao_barra_municipio_errado,
        "portão automático: plano de frio fica fora (Decisão 2)": t_portao_barra_frio,
        "focar: diário com vários atos → janela do decreto do plano (caso real Feira de Santana)": t_focar_diario_com_varios_atos,
        "revertida por portão continua pendente e é refeita": t_revertida_por_portao_e_refeita,
        "citação do trecho sem rede (caso Feira de Santana, PDF)": t_citacao_do_trecho_sem_rede,
        "ids estáveis entre rodadas": t_ids_estaveis,
        "preparar: só A e B, nunca descarta, C intocada": t_preparar_so_A_e_B_e_nunca_descarta,
        "preparar: fonte oficial delega ao juiz; não oficial só lê": t_preparar_oficial_delega_e_nao_oficial_nao,
        "preparar: documento não obtido não quebra nem rebaixa": t_preparar_documento_nao_obtido_nao_quebra,
    })


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--autoteste", action="store_true")
    ap.add_argument("--preparar", action="store_true")
    ap.add_argument("--limite", type=int, default=60)
    a = ap.parse_args()
    if a.autoteste: sys.exit(autoteste())
    fila = ler("pistas_imprensa.json") or {"pistas": []}
    hoje = hoje_editorial().strftime("%d/%m/%Y")
    novos = garantir_ids(fila)
    if a.preparar:
        print("preparação:", preparar(fila, hoje, limite=a.limite))
    gravar("pistas_imprensa.json", fila)
