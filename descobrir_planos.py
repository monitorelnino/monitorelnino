#!/usr/bin/env python3
"""Descoberta automática de planos de contingência/enfrentamento, via API WordPress dos
sítios oficiais — fonte 1 de 6 especificadas em INSTRUCOES_diarios_defeso_LAI_06-09-2026.md
§11 ("achar o plano de SC e todos os demais, sem verificação humana"), a primeira a
implementar. Estendido desde o início a saúde (handover "ponto cego saúde", 18/09/2026,
§3.4) — o mesmo documento que motivou este script (§11 é de 07/09/2026) só cobria defesa
civil; o caso Bahia (18/09) mostrou que saúde tem exatamente o mesmo ponto cego.

O QUE ESTE SCRIPT FAZ (100% máquina, por decisão editorial de 07/09/2026): descobrir a
URL de um PDF candidato, baixar, hashear, preservar como evidência. NUNCA decide sozinho
que um documento é um novo instrumento pontuável — isso é promoção (regra R7), sempre
humana, sempre pela fila. Ver TRAVA ABSOLUTA abaixo.

MECANISMO: API WordPress padrão (`/wp-json/wp/v2/posts?search=...` para notícias/atos, e
`/wp-json/wp/v2/media?search=...&mime_type=application/pdf` para PDFs anexados) — devolve
JSON com título, data e URL, sem raspagem de HTML. Muitos sítios estaduais são WordPress
(SC, SE, ES, PA, RJ, entre outros — §11); onde não é, a API simplesmente não responde como
esperado, e o alvo vira `documento_nao_lido` — perda de recall, nunca invenção.

===========================================================================
TRAVA ABSOLUTA (mesma trava de monitorar_imprensa_regional.py e monitorar_imprensa_saude.py)
— três camadas independentes, cada uma suficiente sozinha:
  1. ESTRUTURAL: nunca escreve em estados.json, saude_uf.json, municipios.json ou
     indice.json/monitor_saude.json (garantia verificada por self-test).
  2. DE CAMPO: todo achado nasce com "documento_oficial_confirmado": null e
     "promovivel": false — só um humano muda isso.
  3. DE PROCESSO: achados vão para data/pistas_descobertas.json (fila própria) e para
     data/evidencias.json (origem="descobrir_planos", via coletores_base.preservar_evidencia,
     que já é o índice único de evidência do projeto) — nunca direto no banco.
===========================================================================

DOMÍNIOS-ALVO: lista curada por UF/setor abaixo (DOMINIOS_CONHECIDOS) — alguns confirmados
nesta sessão (ex.: saude.ba.gov.br), a maioria ainda não verificada individualmente.
Declarado, não escondido: esta lista precisa de curadoria contínua; um domínio ausente ou
errado só reduz recall (o alvo não é buscado), nunca produz um resultado inventado.

REGRAS (§11): cliente identificado (coletores_base.UA); nunca mais de 1 requisição por
domínio a cada 2s (backoff simples — o universo por rodada é pequeno, um por domínio já
respeita "nunca mais de N/min"); toda URL descoberta vira item em data/evidencias.json;
sítio que recusa ou não responde = acesso_recusado (nunca 'nada localizado'); período
eleitoral detectado pelo cliente comum (coletores_base.buscar) = fonte suspensa (defeso).

Uso: python3 descobrir_planos.py [--limite N] [--setor saude|defesa_civil]
     python3 descobrir_planos.py --autoteste    (offline)
"""
import json
import re
import sys
import time
import urllib.parse

import funil
from coletores_base import (RAIZ, buscar, buscar_uma_vez, preservar_evidencia, ler, gravar,
                             log_busca, registrar_lacuna, registrar_acesso_contra_robots, robots_permite,
                             rodar_autoteste, hoje_editorial, referencia_ibge, MuroDeRobo)
from scripts.pistas import sincronizar as sincronizar_pistas  # 05/10/2026: a fila tem UMA porta

FILA = RAIZ / "data" / "pistas_descobertas.json"

# 18/09/2026: alguns domínios confirmados nesta sessão ou em rodadas anteriores; os demais
# são o padrão mais comum observado (saude.<uf>.gov.br / defesacivil.<uf>.gov.br) como
# primeira tentativa — precisa de curadoria contínua (ver docstring acima).
DOMINIOS_CONHECIDOS = {
    "saude": {
        "BA": "saude.ba.gov.br",
        "SC": "saude.sc.gov.br",
        "PR": "saude.pr.gov.br",
        "RO": "sesau.ro.gov.br",
    },
    "defesa_civil": {
        "SC": "defesacivil.sc.gov.br",   # §11: robô recusado nas rodadas de 07/09/2026 — mantido para nova tentativa
        "SE": "defesacivil.se.gov.br",   # §11: idem
        # 23/09/2026 (§179; o commit dizia "§164", número que já era de outra entrada): na primeira
        # rodada real da sonda de camada, 13 das 27
        # UFs não responderam a NADA — o palpite `defesacivil.<uf>.gov.br` estava errado para
        # elas, que é a lacuna de curadoria declarada acima. Sondados seis padrões por UF;
        # estes sete responderam HTTP 200 e passam a ser conhecidos. Conferidos um a um.
        "AL": "defesacivil.al.gov.br",
        "CE": "www.defesacivil.ce.gov.br",
        "MS": "www.defesacivil.ms.gov.br",
        "PB": "bombeiros.pb.gov.br",     # a Defesa Civil da PB fica sob o Corpo de Bombeiros
        "PE": "www.pe.gov.br",           # sem domínio próprio: portal do estado
        "PI": "www.pi.gov.br",           # idem
        "SP": "defesacivil.sp.gov.br",
        # Seguem sem domínio localizado (nenhum dos seis padrões respondeu), e por isso
        # seguem como lacuna declarada, nunca como ausência de plano:
        # AP, DF, RN, RO, TO — e SE, acima, que responde mas recusa o robô.
    },
}

UFS = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
       "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"]

TERMOS_BUSCA = {
    "saude": ["plano de ações de saúde", "plano estadual de enfrentamento", "plano de contingência arboviroses"],
    "defesa_civil": ["plano de contingência", "PLANCON", "plano de enfrentamento"],
}


def dominio_por_busca_ativa(uf: str, setor: str):
    """(dominio, confianca) achados por `descobrir_dominios.py` (§184), ou (None, None).

    Lê `data/dominios_oficiais.json`, que guarda a trilha das tentativas e só registra endereço que
    se identificou como a instituição procurada. Nunca levanta: arquivo ausente é o caso normal em
    cópia parcial do repositório."""
    alvo = (ler("dominios_oficiais.json", {"alvos": {}}) or {}).get("alvos", {}).get(f"{uf}/{setor}") or {}
    return alvo.get("dominio"), alvo.get("confianca")


def dominio_para(uf: str, setor: str) -> str:
    """Endereço do órgão, na ordem de quem prova mais (§184, 23/09/2026).

    1. busca ativa com identidade no TÍTULO da página (confiança alta) — é a prova mais forte;
    2. curadoria humana (DOMINIOS_CONHECIDOS, §179), que conferiu caso a caso;
    3. busca ativa com identidade só no corpo (confiança média);
    4. o padrão mais comum como último recurso, declarado como palpite.

    O palpite fica por último porque erra de três maneiras conhecidas — subdomínio inexistente (a
    Defesa Civil da PB fica sob o Corpo de Bombeiros), endereço que só responde com `www.` (o caso
    do PR) e endereço que responde sendo outra coisa —, e cada erro vira lacuna falsa: ausência de
    busca publicada como ausência de plano."""
    ativo, confianca = dominio_por_busca_ativa(uf, setor)
    if ativo and confianca == "alta":
        return ativo
    conhecido = DOMINIOS_CONHECIDOS.get(setor, {}).get(uf)
    if conhecido:
        return conhecido
    if ativo:
        return ativo
    prefixo = "saude" if setor == "saude" else "defesacivil"
    return f"{prefixo}.{uf.lower()}.gov.br"


def consultar_wp_json(dominio: str, termo: str) -> list:
    """Consulta /wp-json/wp/v2/media (PDFs) do domínio. Devolve (achados, respondeu): `respondeu`
    só quando a API devolveu a lista dela — muro, 403, timeout ou "não é WordPress" é ([], False),
    alvo NÃO verificado (HANDOVER_FONTES 16/10, item 3). Nunca levanta exceção.

    14/10/2026: UMA tentativa, 15 s. Não ser WordPress é o caso comum, e a repetição de `buscar`
    (30 s + 5 s + 30 s por host mudo) levava 47–58 s por alvo: 20 alvos comiam o elo e o
    `seguir_pistas`/`verificar_pista_imprensa` eram pulados pelo prazo."""
    q = urllib.parse.quote(termo)
    url = f"https://{dominio}/wp-json/wp/v2/media?search={q}&mime_type=application/pdf&per_page=10"
    try:
        corpo = buscar_uma_vez(url, timeout=15)
        dados = json.loads(corpo)
        if not isinstance(dados, list):
            return [], False
        achados = []
        for item in dados:
            src = (item.get("source_url") or "").strip()
            titulo = ((item.get("title") or {}).get("rendered") or "").strip()
            data_pub = (item.get("date") or "").strip()
            if src.lower().endswith(".pdf"):
                achados.append({"url": src, "titulo": titulo, "data_publicacao": data_pub})
        return achados, True
    except Exception as e:  # noqa: BLE001 — tolerante por design (ver docstring)
        print(f"[aviso] {dominio}: {type(e).__name__} ({e})")
        return [], False


def _hash_pista(p: dict) -> str:
    import hashlib
    return hashlib.sha256(f"{p['uf']}|{p['setor']}|{p['url']}".encode()).hexdigest()[:16]


def carregar_fila():
    return ler("pistas_descobertas.json", {"_governanca": (
        "Fila de DESCOBERTA automática (via API WordPress, §11) para o juiz automático. "
        "TRAVA ABSOLUTA: nenhum item entra no banco (estados.json/saude_uf.json/"
        "municipios.json/indice.json/monitor_saude.json) sem o juiz automático ler o "
        "documento primário (promoção = regra R7, §106; na dúvida, abstenção). Criado "
        "18/09/2026 (handover ponto cego saúde, §3.4; especificado em "
        "INSTRUCOES_diarios_defeso_LAI_06-09-2026.md §11)."),
        "itens": []})


def registrar(fila: dict, achados: list) -> list:
    vistos = {i["hash"] for i in fila["itens"]}
    ineditos = []
    for a in achados:
        a["hash"] = _hash_pista(a)
        if a["hash"] in vistos:
            continue
        a["documento_oficial_confirmado"] = None
        a["promovivel"] = False
        a["status"] = "pendente_confirmacao_documento"
        a["descoberto_em"] = time.strftime("%Y-%m-%d")
        fila["itens"].append(a)
        vistos.add(a["hash"])
        ineditos.append(a)
    return ineditos


def descobrir(uf: str, setor: str, fila: dict) -> tuple:
    """Consulta um alvo (UF + setor), preserva PDFs achados como evidência, registra na fila.
    Nunca levanta — falha vira `[]` (documento_nao_lido / acesso_recusado, sem distinção
    fina nesta primeira versão; o hash_evidencia ausente já sinaliza 'não lido' a jusante).
    Devolve (novos, respondeu): o alvo conta como verificado só se a API respondeu a um termo."""
    dominio = dominio_para(uf, setor)
    achados_brutos, respondeu = [], False
    for termo in TERMOS_BUSCA[setor][:2]:   # 2 termos por alvo, mesma disciplina de custo dos monitores de imprensa
        achados, ok = consultar_wp_json(dominio, termo)
        achados_brutos.extend(achados)
        respondeu = respondeu or ok
        time.sleep(2.0)   # backoff: nunca mais de 1 req/2s por domínio (§11)
    achados = []
    for a in achados_brutos:
        item = {"uf": uf, "setor": setor, "url": a["url"], "titulo": a["titulo"],
                "data_publicacao": a["data_publicacao"], "dominio": dominio, "hash_evidencia": None}
        try:
            pdf = buscar(a["url"], timeout=40)
            item["hash_evidencia"] = preservar_evidencia(pdf, a["url"], "pdf", "descobrir_planos")
        except Exception as e:  # noqa: BLE001
            item["status_leitura"] = f"acesso_recusado ({type(e).__name__})"
        achados.append(item)
    return registrar(fila, achados), respondeu


def fatia_da_noite(alvos: list, limite: int, dia: int) -> list:
    """Os `limite` alvos desta noite. A fatia anda `limite` a cada dia: os 54 alvos (27 UFs × 2
    setores) passam todos em três noites, e o verificado há mais tempo vem primeiro.

    16/10/2026: a fatia girava por HORA desde o #731. O elo roda numa hora quase fixa, 24 h × 20
    ≡ 48 (mód 54): a janela recuava 6 alvos por noite e cobria os 54 em 9 noites, revendo os
    mesmos 14 por noite."""
    if not alvos:
        return []
    inicio = (dia * limite) % len(alvos)
    return (alvos[inicio:] + alvos[:inicio])[:min(limite, len(alvos))]


def autoteste() -> int:
    def t_dominio_conhecido():
        return dominio_para("BA", "saude") == "saude.ba.gov.br"

    def t_dominio_padrao():
        return dominio_para("XX", "saude") == "saude.xx.gov.br" and dominio_para("XX", "defesa_civil") == "defesacivil.xx.gov.br"

    def t_wp_json_parse():
        # fixture: resposta típica da API WordPress /wp-json/wp/v2/media
        fx = json.dumps([
            {"source_url": "https://saude.xx.gov.br/wp-content/uploads/2026/plano.pdf",
             "title": {"rendered": "Plano de Ações de Saúde 2026"}, "date": "2026-08-15T10:00:00"},
            {"source_url": "https://saude.xx.gov.br/imagem.png",
             "title": {"rendered": "não é PDF"}, "date": "2026-08-15T10:00:00"},
        ])
        import unittest.mock as mock
        with mock.patch(f"{__name__}.buscar_uma_vez", return_value=fx.encode()):
            achados, respondeu = consultar_wp_json("saude.xx.gov.br", "plano")
        return respondeu and len(achados) == 1 and achados[0]["url"].endswith(".pdf")

    def t_wp_json_tolerante_a_falha():
        import unittest.mock as mock
        with mock.patch(f"{__name__}.buscar_uma_vez", side_effect=RuntimeError("timeout")):
            achados = consultar_wp_json("naoexiste.xx.gov.br", "plano")
        with mock.patch(f"{__name__}.buscar_uma_vez", return_value=b"<html>muro</html>"):
            nao_wp = consultar_wp_json("naoexiste.xx.gov.br", "plano")
        return achados == ([], False) and nao_wp == ([], False)

    def t_dedup_e_trava():
        fila = {"_governanca": "x", "itens": []}
        item = {"uf": "XX", "setor": "saude", "url": "https://x.pdf", "titulo": "t", "data_publicacao": "", "dominio": "x", "hash_evidencia": None}
        a = registrar(fila, [dict(item)])
        b = registrar(fila, [dict(item)])
        if not (len(a) == 1 and len(b) == 0):
            return False
        i = fila["itens"][0]
        return i["documento_oficial_confirmado"] is None and i["promovivel"] is False and i["status"] == "pendente_confirmacao_documento"

    def t_trava_estrutural():
        fonte = (RAIZ / "descobrir_planos.py").read_text(encoding="utf-8")
        for proibido in ["estados.json", "saude_uf.json", "municipios.json", "indice.json", "monitor_saude.json"]:
            for _ in re.finditer(r'open\([^)]*' + re.escape(proibido) + r'[^)]*,\s*["\']([wa])', fonte):
                return False
            for _ in re.finditer(r'json\.dump\([^,]*,\s*open\([^)]*' + re.escape(proibido), fonte):
                return False
        return True

    def t_filtro_de_link_aceita_documento_e_recusa_navegacao():
        """Os casos reais da rodada de 23/09, nos dois sentidos."""
        aceita = [
            ("https://x.gov.br/uploads/PES-SE-2024-2027.pdf", "Plano Estadual de Saúde vigência 2024-2027"),
            ("https://x.gov.br/doc/nota_tecnica05.pdf", "EL NIÑO - NOTA TÉCNICA 005/2026"),
            ("https://x.gov.br/Pagina/NOTAS-TECNICA-CONJUNTA-EL-NINO-ENOS-2026", ""),
            ("https://x.gov.br/plancon-municipal", "PLANCON"),
        ]
        aceita += [
            # §186: o ato que APROVA o plano é achado relevante (é ele que decide `documentado`, §180)
            ("https://cides.se.gov.br/uploads/RESOLUCAO-No-08_2024-APROVAR-O-PES-2024-2027.pdf",
             "Resolução de Aprovação do PES 2024-2027"),
        ]
        recusa = [
            ("https://x.gov.br/servicos/Emergencia/Acionar-Corpo-de-Bombeiros", "Acionar Corpo de Bombeiros"),
            # ato que não tem nada com plano: nomeação e portaria de sistema de relatório
            ("https://x.gov.br/uploads/PORTARIA_No_575-SARGSUS.pdf", "PORTARIA_No_575 – SARGSUS"),
            ("https://x.gov.br/Pagina/Plano-Estadual#addtoany", "Mais…"),
            ("https://x.gov.br/Pagina/Portaria-de-Nomeacao-COMPEDC-Modelo", ""),
            ("https://x.gov.br/Pagina/O-que-e-a-rede-de-radioamadores", "Rede Estadual de Emergência de Radioamadores"),
            ("javascript:void(0)", "Plano"),
            ("https://www.facebook.com/sharer?u=plano", "Plano"),
        ]
        return (all(link_e_candidato(u, t) for u, t in aceita)
                and not any(link_e_candidato(u, t) for u, t in recusa))

    def t_purga_tira_ruido_e_preserva_pagina_e_canal_1():
        fila = {"itens": [
            {"uf": "PR", "setor": "defesa_civil", "canal": "renderizado", "url": "https://x/pagina", "titulo": "p"},
            {"uf": "PR", "setor": "defesa_civil", "canal": "renderizado/link", "titulo": "Mais…",
             "url": "https://x/Pagina/Plano#addtoany"},
            {"uf": "PR", "setor": "defesa_civil", "canal": "renderizado/link", "titulo": "NOTA TÉCNICA 005/2026",
             "url": "https://x/doc/nota_tecnica05.pdf"},
            {"uf": "SE", "setor": "saude", "url": "https://y/plano.pdf", "titulo": "wp-json"},
        ]}
        fora = purgar_ruido_renderizado(fila)
        urls = [i["url"] for i in fila["itens"]]
        return (len(fora) == 1 and "addtoany" in fora[0]["url"]
                and "https://x/pagina" in urls and "https://y/plano.pdf" in urls
                and "https://x/doc/nota_tecnica05.pdf" in urls)

    def t_fatia_da_noite():
        alvos = list(range(54))
        tres = [x for d in (100, 101, 102) for x in fatia_da_noite(alvos, 20, d)]
        return set(tres) == set(alvos) and fatia_da_noite([], 20, 1) == [] and len(fatia_da_noite(alvos, 99, 3)) == 54

    def t_dominios_e_identidade_do_portal():
        d = dominios_do_municipio("São João d'Aliança", "GO")
        pref = "<title>Prefeitura Municipal de Santana do Ipanema</title><body>Gabinete</body>"
        return (d == ["saojoaodalianca.go.gov.br", "www.saojoaodalianca.go.gov.br"]
                and identifica_prefeitura(pref, "Santana do Ipanema")
                and not identifica_prefeitura(pref, "Palmeira dos Índios")
                and not identifica_prefeitura("<title>Santana do Ipanema, turismo</title>", "Santana do Ipanema"))

    def t_links_da_home_so_candidatos_e_absolutos():
        html = ('<a href="/uploads/plano-de-contingencia.pdf">Plano de Contingência 2024</a>'
                '<a href="/fale-conosco">Fale conosco</a><a href="/uploads/plano-de-contingencia.pdf">de novo</a>')
        return links_da_pagina(html, "https://x.al.gov.br/") == [
            ("https://x.al.gov.br/uploads/plano-de-contingencia.pdf", "Plano de Contingência 2024")]

    def t_pista_do_portal_passa_pela_porta():
        from scripts.pistas import motivo_de_recusa, normalizar
        pl = pistas_do_portal("Bonito", "MS", "5002209", "bonito.ms.gov.br",
                              [("https://bonito.ms.gov.br/plano.pdf", "Plano Municipal de Contingência", "2023-05-02", "h1")],
                              "2026-10-22")[0]
        return (pl["origem"] == "descoberta" and pl["ibge"] == "5002209"
                and motivo_de_recusa(normalizar(pl)) == "")

    def t_portal_recusa_e_ausencia_nao_viram_plano():
        import unittest.mock as mock
        import urllib.error
        e403 = urllib.error.HTTPError("https://x", 403, "Forbidden", {}, None)
        with mock.patch(f"{__name__}.buscar_uma_vez", side_effect=e403):
            recusa = descobrir_no_portal("Bonito", "MS", "5002209", "2026-10-22")
        with mock.patch(f"{__name__}.buscar_uma_vez", side_effect=OSError("dns")):
            mudo = descobrir_no_portal("Bonito", "MS", "5002209", "2026-10-22")
        return (recusa["situacao"] == "recusa_de_fonte" and recusa["pistas"] == []
                and mudo["situacao"] == "portal_nao_localizado" and mudo["pistas"] == [])

    def t_portal_le_wp_json_e_links_sem_escrever():
        import unittest.mock as mock
        home = ('<title>Prefeitura de Bonito</title>'
                '<a href="/doc/plancon-2024.pdf">PLANCON 2024</a>').encode()
        wp = ([{"url": "https://bonito.ms.gov.br/wp/plano.pdf", "titulo": "Plano de contingência",
                "data_publicacao": "2024-03-01T10:00:00"}], True)
        with mock.patch(f"{__name__}.buscar_uma_vez", return_value=home), \
             mock.patch(f"{__name__}.consultar_wp_json", return_value=wp), \
             mock.patch(f"{__name__}.buscar", return_value=b"%PDF"), \
             mock.patch(f"{__name__}.preservar_evidencia", return_value="h-falso"):
            r = descobrir_no_portal("Bonito", "MS", "5002209", "2026-10-22")
        urls = [p["url"] for p in r["pistas"]]
        return (r["situacao"] == "lido" and "https://bonito.ms.gov.br/wp/plano.pdf" in urls
                and "https://bonito.ms.gov.br/doc/plancon-2024.pdf" in urls
                and r["pistas"][0]["hash_evidencia"] == "h-falso" and r["pistas"][0]["data_publicacao"] == "2024-03-01")

    def t_rodada_de_municipios_retoma_e_grava_no_prazo():
        import unittest.mock as mock
        import tempfile
        gravados, lotes = {}, []
        livro = {"municipios": {"2": {"consultado_em": "2026-10-22"}}}   # o 2 já foi lido hoje

        def lido(nome, uf, cod, hoje):
            if cod == "3":
                raise KeyboardInterrupt()
            return {"dominio": "x", "situacao": "lido", "pistas": []}
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump({"fila": ["1", "2", "3", "4"]}, f)
        ref = {c: {"nome": f"M{c}", "uf": "XX"} for c in "1234"}
        with mock.patch(f"{__name__}.referencia_ibge", return_value=(ref, None)), \
             mock.patch(f"{__name__}.hoje_editorial", return_value=__import__("datetime").date(2026, 10, 22)), \
             mock.patch(f"{__name__}.ler", return_value=livro), \
             mock.patch(f"{__name__}.gravar", side_effect=lambda n, o, compacto=False: gravados.update({n: o})), \
             mock.patch(f"{__name__}.log_busca"), \
             mock.patch(f"{__name__}.descobrir_no_portal", side_effect=lido), \
             mock.patch("scripts.pistas.gravar_lote", side_effect=lambda p, origem="": lotes.append(p) or {"gravadas": 0, "recusadas": 0}):
            rodar_municipios(f.name)
        import os
        os.unlink(f.name)
        feitos = gravados.get(RESULTADO_DA_RODADA, {}).get("municipios", {})
        return set(feitos) == {"1", "2"} and len(lotes) == 1   # 2 pulado (já lido), 3 interrompeu, 4 ficou para depois

    return rodar_autoteste({
        "§186 filtro de link aceita documento e recusa navegação": t_filtro_de_link_aceita_documento_e_recusa_navegacao,
        "§186 purga tira o ruído e preserva página e canal 1": t_purga_tira_ruido_e_preserva_pagina_e_canal_1,
        "domínio conhecido (BA/saúde)": t_dominio_conhecido,
        "domínio padrão (fallback declarado)": t_dominio_padrao,
        "wp-json: extrai só PDFs, com título e data": t_wp_json_parse,
        "wp-json: falha, muro ou não-WordPress = vazio e NÃO verificado": t_wp_json_tolerante_a_falha,
        "fatia anda por noite e cobre os 54 alvos em 3 noites": t_fatia_da_noite,
        "dedup por hash + trava absoluta (campos de nascença)": t_dedup_e_trava,
        "garantia estrutural: nunca escreve nos bancos": t_trava_estrutural,
        "portal da prefeitura: endereço padrão e identidade da página": t_dominios_e_identidade_do_portal,
        "portal da prefeitura: links da home, só candidatos e absolutos": t_links_da_home_so_candidatos_e_absolutos,
        "portal da prefeitura: a pista passa pela porta única": t_pista_do_portal_passa_pela_porta,
        "portal da prefeitura: recusa e endereço mudo não viram plano nem ausência de plano": t_portal_recusa_e_ausencia_nao_viram_plano,
        "portal da prefeitura: wp-json e links, sem escrever em data/": t_portal_le_wp_json_e_links_sem_escrever,
        "rodada de municípios: retoma no dia e grava o lido no prazo": t_rodada_de_municipios_retoma_e_grava_no_prazo,
    })


RENDERIZADOR = RAIZ / "scripts" / "renderizar_pagina.js"

# Termos que fazem um link virar candidato na página renderizada (§185, apertado no §186).
#
# A primeira versão aceitava "emerg", "decreto", "portaria", "resolu" e "document", e a rodada real
# de 23/09 mostrou o preço: entraram na fila humana "Acionar Corpo de Bombeiros", "Portaria de
# Nomeação COMPDEC — Modelo", "Rede de Radioamadores" e até a âncora de compartilhamento "Mais…".
# Fila de triagem com ruído é pior que fila curta: ela gasta o tempo humano que devia julgar
# documento. Termo que falta reduz recall; termo largo demais destrói a utilidade da fila.
TERMOS_NO_LINK = ("plano", "plancon", "conting", "nota tecnica", "nota técnica", "el nino",
                  "el niño", "enos", "seca", "estiagem", "incend", "queimad", "arbovir", "dengue")

# Endereços que nunca são documento, por mais que o texto casse: navegação, âncora e compartilhamento.
LINKS_QUE_NAO_SAO_DOCUMENTO = ("addtoany", "javascript:", "/servicos/", "facebook.com", "twitter.com",
                               "x.com/intent", "whatsapp", "linkedin.com", "/imprimir", "mailto:",
                               "#content", "#main")
MAXIMO_LINKS_POR_PAGINA = 25   # teto por página: a fila é para leitura humana, não para despejo


# O ato que APROVA um plano é achado tão relevante quanto o plano (§180: é ele que decide se o
# registro é `documentado`). Mas "Portaria de Nomeação COMPDEC — Modelo" não é nada disso. A
# diferença está na companhia: ato + verbo de aprovação, ou ato + nome/sigla de plano.
RE_ATO_DE_PLANO = re.compile(
    r"(resolu[çc]|decreto|portaria|lei)[^|]{0,80}?"
    r"(aprova|institui|homologa|adota|plano|plancon|\bpes\b|\bpas\b)",
    re.IGNORECASE)


def link_e_candidato(href: str, texto: str) -> bool:
    """O link merece entrar na fila de triagem humana? Função pura, testável (§186)."""
    u = (href or "").lower()
    alvo = f"{u} {(texto or '').lower()}"
    if not u.startswith("http") or u.rstrip("/").endswith("#") or any(x in u for x in LINKS_QUE_NAO_SAO_DOCUMENTO):
        return False
    if "#" in u and not u.lower().endswith(".pdf"):
        return False
    if any(termo in alvo for termo in TERMOS_NO_LINK):
        return True
    return bool(RE_ATO_DE_PLANO.search(alvo))


def purgar_ruido_renderizado(fila: dict) -> list:
    """Tira da fila os links do canal renderizado que o filtro apertado do §186 não aceita mais.

    Nunca mexe em item do canal 1 (wp-json), nem na PÁGINA registrada — só nos links que ela gerou,
    que são os que entraram por filtro largo. Devolve o que saiu, para o relatório."""
    fora, ficam = [], []
    for i in fila.get("itens", []):
        if i.get("canal") == "renderizado/link" and not link_e_candidato(i.get("url", ""), i.get("titulo") or ""):
            fora.append(i)
        else:
            ficam.append(i)
    fila["itens"] = ficam
    return fora


def descobrir_renderizado(uf: str, setor: str, url: str, fila: dict, rodar=None) -> list:
    """Canal 2 da descoberta (§185, 23/09/2026): a página como o navegador a vê.

    POR QUE EXISTE. O canal 1 é a API do WordPress, e ela não responde em boa parte dos portais:
    na releitura de 23/09, oito alvos devolveram 404, 410, JSON inválido ou 401. Pior, o portal da
    Defesa Civil do MT é Liferay e diz, em texto, "este site precisa que o seu navegador tenha
    JAVASCRIPT ativo": o conteúdo existe, os links existem, e o cliente HTTP recebe o esqueleto. Foi
    assim que o Planejamento Estratégico 2026 do MT — que anuncia o "inédito Plano Estadual de
    Defesa Civil" e o suporte a 20 PLANCONs municipais — ficou invisível para toda rodada anterior.

    O QUE FAZ: renderiza a página com navegador real (scripts/renderizar_pagina.js, cliente
    identificado), preserva o HTML renderizado como evidência, e registra na MESMA fila do canal 1
    o texto visível e cada link candidato. O que NÃO faz: decidir que existe plano. As três travas
    do módulo continuam valendo — nada entra no banco, todo item nasce `promovivel: false`, e a
    promoção só pelo juiz automático, com documento oficial (D7)."""
    import json as _json
    import subprocess as _sub
    rodar = rodar or (lambda cmd: _sub.run(cmd, capture_output=True, text=True, timeout=180, encoding="utf-8"))
    # §185: o navegador não passa por buscar(), então o rastro do robots tem de ser deixado aqui —
    # e são exatamente estes os acessos que contrariam o pedido do sítio. Sem esta chamada, a
    # política teria rastro só do canal HTTP, que é o que menos precisa dele.
    host = url.split("//", 1)[-1].split("/", 1)[0].lower()
    if robots_permite(host, url) is False:
        try:
            registrar_acesso_contra_robots(host, url, "descobrir_planos/renderizado")
        except Exception:  # noqa: BLE001
            pass
    r = rodar(["node", str(RENDERIZADOR), url])
    try:
        render = _json.loads(r.stdout or "{}")
    except Exception:  # noqa: BLE001
        render = {"ok": False, "erro": "saída do renderizador não é JSON"}
    if not render.get("ok"):
        registrar_lacuna(f"render de {url[:60]}", str(render.get("erro"))[:120],
                         canal="descoberta renderizada", camada=1, uf=uf)
        return []

    hash_pagina = None
    try:
        hash_pagina = preservar_evidencia((render.get("texto") or "").encode("utf-8"), url, "txt",
                                          "descobrir_planos/renderizado")
    except Exception:  # noqa: BLE001 — sem evidência o achado ainda vale como pista, declarada
        pass

    achados = [{"uf": uf, "setor": setor, "url": url, "titulo": render.get("titulo"),
                "data_publicacao": None, "dominio": (url.split("//", 1)[-1].split("/", 1)[0]),
                "canal": "renderizado", "texto_visivel": (render.get("texto") or "")[:4000],
                "hash_evidencia": hash_pagina}]
    candidatos = 0
    for l in render.get("links") or []:
        if candidatos >= MAXIMO_LINKS_POR_PAGINA:
            break
        if link_e_candidato(l.get("href", ""), l.get("texto", "")):
            candidatos += 1
            achados.append({"uf": uf, "setor": setor, "url": l["href"], "titulo": l.get("texto"),
                            "data_publicacao": None, "dominio": (l["href"].split("//", 1)[-1].split("/", 1)[0]),
                            "canal": "renderizado/link", "achado_em": url, "hash_evidencia": None})
    novos = registrar(fila, achados)
    log_busca("descoberta renderizada", 1, [url], "pista" if novos else "consultado sem achado",
              uf=uf, n_resultados=len(novos),
              resultados=f"{render.get('n_links')} link(s) na página; {len(novos)} pista(s) inédita(s)")
    return novos


# ---------------------------------------------------------------------------------------------
# Busca dirigida por município (22/10/2026, HANDOVER_REPOSITORIOS_DE_PLANOS_MUNICIPAIS §1.8).
# Canal "portal da prefeitura" da rodada dirigida pela relação do S2iD (`data/s2id_plancon.json`).
# O endereço é o padrão `<município>.<uf>.gov.br` e só vale se a página SE IDENTIFICA como a prefeitura
# do município (mesma disciplina de `descobrir_dominios.py`): endereço que não responde assim é busca
# não feita, nunca "sem plano". Acha-se por wp-json (PDF anexado) ou pelos links da home em HTML
# estático; site que só monta a página por JavaScript fica "não verificado" (o renderizador grava na
# fila por UF e setor, que não tem município). A pista entra pela porta única e segue ao juiz.
# ---------------------------------------------------------------------------------------------
TERMOS_MUNICIPIO = ("plano de contingência", "defesa civil")
LIMITE_PDF_POR_MUNICIPIO = 3
RECUSAS_DE_FONTE = (401, 403, 429, 451)
RESULTADO_DA_RODADA = "s2id_busca_dirigida.json"


def _so_letras(texto: str) -> str:
    import unicodedata
    base = unicodedata.normalize("NFKD", str(texto or "").lower())
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in base if not unicodedata.combining(c)))


def dominios_do_municipio(nome: str, uf: str) -> list:
    """Os endereços padrão a tentar, em ordem. Função pura."""
    base = f"{_so_letras(nome)}.{uf.lower()}.gov.br"
    return [base, f"www.{base}"]


def identifica_prefeitura(html: str, nome: str) -> bool:
    """A página diz ser a prefeitura do município (nome e a palavra "prefeitura" ou "município"). Pura."""
    t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", str(html or "")[:300000]))
    alvo = _so_letras(t)
    return _so_letras(nome) in alvo and ("prefeitura" in alvo or "municipio" in alvo)


def links_da_pagina(html: str, base: str) -> list:
    """[(href, texto)] dos links candidatos a plano na página, no teto da página. Função pura."""
    achados = []
    for m in re.finditer(r'<a\s[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', str(html or ""), re.I | re.S):
        href = urllib.parse.urljoin(base, m.group(1).strip())
        texto = " ".join(re.sub(r"<[^>]+>", " ", m.group(2)).split())
        if link_e_candidato(href, texto) and href not in [h for h, _ in achados]:
            achados.append((href, texto))
        if len(achados) >= MAXIMO_LINKS_POR_PAGINA:
            break
    return achados


def pistas_do_portal(nome: str, uf: str, ibge: str, dominio: str, itens: list, hoje: str) -> list:
    """Pistas no esquema da porta única, a partir de [(url, titulo, data, hash)]. Função pura."""
    from consultar_querido_diario import STATUS_DA_PISTA
    return [{"municipio": nome, "uf": uf, "ibge": str(ibge).zfill(7), "url": url,
             "titulo": f"Portal da prefeitura de {nome}/{uf} ({dominio}): {titulo}"[:300],
             "trecho": " ".join(str(titulo or "").split())[:500], "data_publicacao": data or None,
             "origem": "descoberta", "hash_evidencia": h, "status": STATUS_DA_PISTA,
             "data": hoje, "registrado_em": hoje}
            for url, titulo, data, h in itens]


def descobrir_no_portal(nome: str, uf: str, ibge: str, hoje: str) -> dict:
    """Um município, um canal. Devolve {dominio, situacao, pistas}; nunca levanta.

    `situacao`: `recusa_de_fonte` (401/403/429/451 ou muro de robô: respeita-se e registra-se),
    `portal_nao_localizado` (o endereço padrão não respondeu como a prefeitura) ou `lido`."""
    import urllib.error
    dominio = home = None
    for d in dominios_do_municipio(nome, uf):
        try:
            corpo = buscar_uma_vez(f"https://{d}/", timeout=15)
        except urllib.error.HTTPError as e:
            if e.code in RECUSAS_DE_FONTE:
                return {"dominio": d, "situacao": "recusa_de_fonte", "motivo": f"HTTP {e.code}", "pistas": []}
            continue
        except MuroDeRobo as e:
            return {"dominio": d, "situacao": "recusa_de_fonte", "motivo": f"muro de robô ({e})", "pistas": []}
        except Exception:  # noqa: BLE001 — DNS, timeout e TLS: o endereço não serve, tenta o próximo
            continue
        texto = corpo[:300000].decode("utf-8", "replace")
        if identifica_prefeitura(texto, nome):
            dominio, home = d, texto
            break
    if not dominio:
        return {"dominio": None, "situacao": "portal_nao_localizado", "pistas": []}
    itens, vistos = [], set()
    for termo in TERMOS_MUNICIPIO:
        achados, _ = consultar_wp_json(dominio, termo)
        for a in achados:
            if a["url"] in vistos or len(vistos) >= LIMITE_PDF_POR_MUNICIPIO:
                continue
            vistos.add(a["url"])
            h = None
            try:
                h = preservar_evidencia(buscar(a["url"], timeout=40), a["url"], "pdf", "descobrir_planos")
            except Exception:  # noqa: BLE001 — sem a cópia a pista vale, declarada sem hash
                pass
            itens.append((a["url"], a["titulo"], (a["data_publicacao"] or "")[:10], h))
    for href, texto in links_da_pagina(home, f"https://{dominio}/"):
        if href not in vistos:
            vistos.add(href)
            itens.append((href, texto, None, None))
    return {"dominio": dominio, "situacao": "lido", "pistas": pistas_do_portal(nome, uf, ibge, dominio, itens, hoje)}


def rodar_municipios(caminho: str, limite: int = None) -> int:
    """A fila da relação do S2iD pelo portal da prefeitura. Retomável no mesmo dia; o prazo do elo
    (`prazo=Nmin`) chega como SIGINT e o que foi lido é gravado."""
    from scripts.pistas import gravar_lote
    doc = json.load(open(caminho, encoding="utf-8"))
    por_cod, _ = referencia_ibge()
    hoje = hoje_editorial().isoformat()
    feitos = ler(RESULTADO_DA_RODADA, {"municipios": {}})
    feitos.setdefault("municipios", {})
    fila = [c for c in doc.get("fila", []) if c in por_cod and feitos["municipios"].get(c, {}).get("consultado_em") != hoje]
    pistas, lidos = [], 0
    try:
        for cod in fila[:limite] if limite else fila:
            ref = por_cod[cod]
            r = descobrir_no_portal(ref["nome"], ref["uf"], cod, hoje)
            pistas.extend(r["pistas"])
            feitos["municipios"][cod] = {"consultado_em": hoje, "dominio": r["dominio"], "situacao": r["situacao"],
                                         "motivo": r.get("motivo"), "pistas": len(r["pistas"])}
            lidos += 1
    except KeyboardInterrupt:
        print(f"[prazo] interrompido depois de {lidos} município(s); gravando o que foi lido.")
    balanco = gravar_lote(pistas, origem="descoberta")
    feitos["gerado_em"] = hoje
    gravar(RESULTADO_DA_RODADA, feitos)
    por_situacao = {}
    for v in feitos["municipios"].values():
        sit = v.get("situacao") or "sem_situacao"
        por_situacao[sit] = por_situacao.get(sit, 0) + 1
    log_busca("descobrir_planos", 3, [caminho], "pista" if pistas else "consultado sem achado",
              n_resultados=len(pistas),
              resultados=f"{lidos} município(s) pelo portal da prefeitura; {por_situacao}; "
                         f"fila: {balanco.get('gravadas')} gravada(s), {balanco.get('recusadas')} recusada(s)")
    print(f"Portal da prefeitura: {lidos} município(s); {por_situacao}; porta única: "
          f"{balanco.get('gravadas')} gravada(s), {balanco.get('recusadas')} recusada(s) {balanco.get('motivos') or ''}")
    return 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()

    limite = 10
    if "--limite" in sys.argv:
        limite = int(sys.argv[sys.argv.index("--limite") + 1])
    if "--municipios" in sys.argv:   # busca dirigida pela relação do S2iD, canal do portal da prefeitura
        return rodar_municipios(sys.argv[sys.argv.index("--municipios") + 1],
                                int(sys.argv[sys.argv.index("--limite") + 1]) if "--limite" in sys.argv else None)
    setores = ["saude", "defesa_civil"]
    if "--setor" in sys.argv:
        setores = [sys.argv[sys.argv.index("--setor") + 1]]
    # §185: alvo por UF. A releitura das fontes que o §182 mostrou falsamente suspensas precisa
    # bater em quatro UFs específicas, não na lista inteira em ordem alfabética.
    ufs = UFS
    if "--uf" in sys.argv:
        ufs = [u.strip().upper() for u in sys.argv[sys.argv.index("--uf") + 1].split(",") if u.strip()]

    fila = carregar_fila()
    # §185: canal renderizado, dirigido a uma página. Exige --uf e --setor, porque a pista nasce
    # atribuída a um alvo — pista sem UF não serve para nada a jusante.
    if "--limpar-ruido" in sys.argv:
        fora = purgar_ruido_renderizado(fila)
        sincronizar_pistas("pistas_descobertas.json", fila, origem="descoberta", ler_fn=ler, gravar_fn=gravar)
        print(f"{len(fora)} link(s) do canal renderizado saíram da fila pelo filtro do §186:")
        for i in fora[:20]:
            print(f"  − [{i['uf']}/{i['setor']}] {str(i.get('titulo'))[:46]:46s} {i['url'][:70]}")
        if len(fora) > 20:
            print(f"  … e mais {len(fora) - 20}")
        print(f"fila fica com {len(fila['itens'])} item(ns).")
        return 0
    if "--renderizar" in sys.argv:
        url = sys.argv[sys.argv.index("--renderizar") + 1]
        if "--uf" not in sys.argv or "--setor" not in sys.argv:
            print("--renderizar exige --uf e --setor"); return 1
        uf = sys.argv[sys.argv.index("--uf") + 1].upper()
        setor = sys.argv[sys.argv.index("--setor") + 1]
        novos = descobrir_renderizado(uf, setor, url, fila)
        sincronizar_pistas("pistas_descobertas.json", fila, origem="descoberta", ler_fn=ler, gravar_fn=gravar)
        print(f"Canal renderizado: {len(novos)} pista(s) inédita(s) de {url}")
        for n in novos:
            print(f"  · [{n['uf']}/{n['setor']}] {str(n.get('titulo'))[:70]} — {n['url'][:80]}")
        print("  → NENHUMA é promovível — trava absoluta (R7).")
        return 0
    alvos = [(uf, setor) for setor in setores for uf in ufs]
    total_novos = consultas = responderam = 0
    try:
        for uf, setor in fatia_da_noite(alvos, limite, int(time.time() // 86400)):
            novos, respondeu = descobrir(uf, setor, fila)
            consultas += 1
            responderam += respondeu
            total_novos += len(novos)
    except KeyboardInterrupt:
        # Prazo próprio do comando (`prazo=Nmin` no elo, saude_pipeline): o SIGINT chega aqui, e o
        # que já foi achado é gravado em vez de perdido (salvamento parcial, item 3 de 16/10).
        print(f"[prazo] interrompido depois de {consultas} alvo(s); gravando o que foi achado.")

    sincronizar_pistas("pistas_descobertas.json", fila, origem="descoberta", ler_fn=ler, gravar_fn=gravar)
    # Item B do handover da auditoria do funil (27/09/2026): a rodada conta por etapa, para que
    # "está encontrando?" se responda sem abrir o código. Contagem não decide nada.
    # Defeito 3 da auditoria: este coletor está agendado 4x ao dia e tinha UMA execução em todo o
    # log_buscas.json — rodava e não registrava o que fazia, o que o tornava invisível ao
    # instrumento pelo qual se responde "está encontrando?".
    funil.registrar("descobrir_planos", alvos_consultados=consultas, alvos_verificados=responderam,
                    achados_novos=total_novos,
                    fila_acumulada=len(fila["itens"]))
    log_busca("descobrir_planos", 3, [f"{len(setores)} setor(es)"],
              "pista" if total_novos else "consultado sem achado",
              n_resultados=total_novos,
              resultados=f"{consultas} alvo(s) consultado(s), {responderam} com resposta da API; "
                         f"{total_novos} achado(s) inédito(s); "
                         f"fila com {len(fila['itens'])} item(ns)")
    print(f"Descoberta via wp-json: {consultas} alvo(s) consultado(s), {responderam} verificado(s) "
          f"— a API respondeu ({'/'.join(setores)}).")
    if total_novos:
        print(f"[ACHADOS NOVOS] {total_novos} para o juiz automático (status pendente_confirmacao_documento):")
        for p in fila["itens"][-total_novos:]:
            print(f"  · [{p['uf']}/{p['setor']}] {p['titulo'][:80] or p['url']}")
        print("  → NENHUM foi confirmado nem é promovível — trava absoluta. Ver data/pistas_descobertas.json.")
    else:
        print(f"Nenhum achado inédito (fila com {len(fila['itens'])} itens acumulados).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
