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

from coletores_base import (RAIZ, buscar, preservar_evidencia, ler, gravar,
                             log_busca, registrar_lacuna, registrar_acesso_contra_robots, robots_permite,
                             rodar_autoteste, setor_da_url)

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
    """Consulta /wp-json/wp/v2/media (PDFs) do domínio. Devolve [] em qualquer falha
    (site fora do ar, não é WordPress, API desabilitada) — nunca levanta exceção."""
    q = urllib.parse.quote(termo)
    url = f"https://{dominio}/wp-json/wp/v2/media?search={q}&mime_type=application/pdf&per_page=10"
    try:
        corpo = buscar(url, timeout=30)
        dados = json.loads(corpo)
        if not isinstance(dados, list):
            return []
        achados = []
        for item in dados:
            src = (item.get("source_url") or "").strip()
            titulo = ((item.get("title") or {}).get("rendered") or "").strip()
            data_pub = (item.get("date") or "").strip()
            if src.lower().endswith(".pdf"):
                achados.append({"url": src, "titulo": titulo, "data_publicacao": data_pub})
        return achados
    except Exception as e:  # noqa: BLE001 — tolerante por design (ver docstring)
        print(f"[aviso] {dominio}: {type(e).__name__} ({e})")
        return []


def _hash_pista(p: dict) -> str:
    import hashlib
    return hashlib.sha256(f"{p['uf']}|{p['setor']}|{p['url']}".encode()).hexdigest()[:16]


def carregar_fila():
    return ler("pistas_descobertas.json", {"_governanca": (
        "Fila de DESCOBERTA automática (via API WordPress, §11) para triagem humana. "
        "TRAVA ABSOLUTA: nenhum item entra no banco (estados.json/saude_uf.json/"
        "municipios.json/indice.json/monitor_saude.json) sem confirmação humana do "
        "documento primário, pelo fluxo manual normal (promoção = regra R7). Criado "
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


def descobrir(uf: str, setor: str, fila: dict) -> list:
    """Consulta um alvo (UF + setor), preserva PDFs achados como evidência, registra na fila.
    Nunca levanta — falha vira `[]` (documento_nao_lido / acesso_recusado, sem distinção
    fina nesta primeira versão; o hash_evidencia ausente já sinaliza 'não lido' a jusante)."""
    dominio = dominio_para(uf, setor)
    achados_brutos = []
    for termo in TERMOS_BUSCA[setor][:2]:   # 2 termos por alvo, mesma disciplina de custo dos monitores de imprensa
        achados_brutos.extend(consultar_wp_json(dominio, termo))
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
    novos = registrar(fila, achados)
    return novos


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
        with mock.patch(f"{__name__}.buscar", return_value=fx.encode()):
            achados = consultar_wp_json("saude.xx.gov.br", "plano")
        return len(achados) == 1 and achados[0]["url"].endswith(".pdf")

    def t_wp_json_tolerante_a_falha():
        import unittest.mock as mock
        with mock.patch(f"{__name__}.buscar", side_effect=RuntimeError("timeout")):
            achados = consultar_wp_json("naoexiste.xx.gov.br", "plano")
        return achados == []

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

    return rodar_autoteste({
        "domínio conhecido (BA/saúde)": t_dominio_conhecido,
        "domínio padrão (fallback declarado)": t_dominio_padrao,
        "wp-json: extrai só PDFs, com título e data": t_wp_json_parse,
        "wp-json: falha de rede vira lista vazia, nunca exceção": t_wp_json_tolerante_a_falha,
        "dedup por hash + trava absoluta (campos de nascença)": t_dedup_e_trava,
        "garantia estrutural: nunca escreve nos bancos": t_trava_estrutural,
    })


RENDERIZADOR = RAIZ / "scripts" / "renderizar_pagina.js"

# Termos que fazem um link virar candidato na página renderizada. Lista declarada e certamente
# incompleta — termo que falta reduz recall, nunca inventa achado (mesma disciplina do §11).
TERMOS_NO_LINK = ("plano", "conting", "plancon", "seca", "estiagem", "incend", "queimad",
                  "decreto", "portaria", "resolu", "arbovir", "dengue", "emerg")


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
    promoção é humana (R7)."""
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
    for l in render.get("links") or []:
        alvo = f"{l.get('href','')} {l.get('texto','')}".lower()
        if any(termo in alvo for termo in TERMOS_NO_LINK) and "#" not in l.get("href", "")[-2:]:
            achados.append({"uf": uf, "setor": setor, "url": l["href"], "titulo": l.get("texto"),
                            "data_publicacao": None, "dominio": (l["href"].split("//", 1)[-1].split("/", 1)[0]),
                            "canal": "renderizado/link", "achado_em": url, "hash_evidencia": None})
    novos = registrar(fila, achados)
    log_busca("descoberta renderizada", 1, [url], "pista" if novos else "consultado sem achado",
              uf=uf, n_resultados=len(novos),
              resultados=f"{render.get('n_links')} link(s) na página; {len(novos)} pista(s) inédita(s)")
    return novos


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()

    limite = 10
    if "--limite" in sys.argv:
        limite = int(sys.argv[sys.argv.index("--limite") + 1])
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
    if "--renderizar" in sys.argv:
        url = sys.argv[sys.argv.index("--renderizar") + 1]
        if "--uf" not in sys.argv or "--setor" not in sys.argv:
            print("--renderizar exige --uf e --setor"); return 1
        uf = sys.argv[sys.argv.index("--uf") + 1].upper()
        setor = sys.argv[sys.argv.index("--setor") + 1]
        novos = descobrir_renderizado(uf, setor, url, fila)
        gravar("pistas_descobertas.json", fila)
        print(f"Canal renderizado: {len(novos)} pista(s) inédita(s) de {url}")
        for n in novos:
            print(f"  · [{n['uf']}/{n['setor']}] {str(n.get('titulo'))[:70]} — {n['url'][:80]}")
        print("  → NENHUMA é promovível — trava absoluta (R7).")
        return 0
    total_novos = 0
    consultas = 0
    for setor in setores:
        for uf in ufs:
            if consultas >= limite:
                break
            novos = descobrir(uf, setor, fila)
            total_novos += len(novos)
            consultas += 1
        if consultas >= limite:
            break

    gravar("pistas_descobertas.json", fila)
    print(f"Descoberta via wp-json: {consultas} alvo(s) consultado(s) ({'/'.join(setores)}).")
    if total_novos:
        print(f"[ACHADOS NOVOS] {total_novos} para triagem humana (status pendente_confirmacao_documento):")
        for p in fila["itens"][-total_novos:]:
            print(f"  · [{p['uf']}/{p['setor']}] {p['titulo'][:80] or p['url']}")
        print("  → NENHUM foi confirmado nem é promovível — trava absoluta. Ver data/pistas_descobertas.json.")
    else:
        print(f"Nenhum achado inédito (fila com {len(fila['itens'])} itens acumulados).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
