#!/usr/bin/env python3
"""
julgar_e_aplicar_descobertas.py
=================================
A peça que faltava para o índice se atualizar sozinho a cada novo decreto
encontrado (pedido de Patricia, 31/08/2026): lê as pistas que
monitorar_imprensa_regional.py já descobre toda semana, busca o documento
em si (não só a notícia sobre ele), classifica com classificador_natureza.py
e, quando confiante, aplica DIRETO no banco — sem esperar uma sessão humana.
Só cai para revisão humana quando o classificador está em dúvida, ou quando
faltam número/data para citar a fonte corretamente.

O QUE CONTINUA IGUAL (trava de fonte, não mudou): só processa pistas cujo
domínio já é reconhecido como oficial (.gov.br/.leg.br/Diário Oficial/Querido
Diário — mesmos padrões de sempre, PADROES_FONTE_PROVAVEL_OFICIAL). A
diferença é que esse sinal, que antes só servia para ORDENAR a fila para um
humano olhar primeiro, agora é parte de um portão real: fonte oficial +
citação completa (número e data) + classificador confiante = aplica sozinho.
Qualquer um desses três faltando = fila humana, exatamente como era antes.

FLUXO POR PISTA:
  1. Só pistas com fonte_provavel_oficial=True são candidatas a julgamento
     automático (as outras continuam na fila, como sempre).
  2. Busca o texto do documento na URL (tolerante a falha de rede — pista
     que não abrir fica pendente, tentada de novo na próxima execução).
  3. classificador_natureza.classificar(texto) → EX_ANTE / RESPOSTA / DUVIDA.
  4. RESPOSTA → nunca pontua (Correção B); pista marcada resolvida, log.
  5. DUVIDA, ou citação incompleta (sem número+data extraíveis) → fica na
     fila para revisão humana, sem mudar nada no banco.
  6. EX_ANTE + citação completa:
       - Estadual (rótulo A-lac/C-estado-amplo): verificar_recorrencia_uf
         decide se é reedição (aplica régua 40/30/20 conforme cobertura de
         risco §18 addendum — o padrão fica em NEUTRO/30 quando o texto não
         permite confirmar cobertura COBRE/DIFERE com segurança, ficando
         registrado para ajuste humano posterior se necessário) ou instrumento
         genuinamente novo (NOVO se a UF não tinha nada; READ se substitui
         algo existente; antecipação 100).
       - Municipal (rótulo B-capital/D-municipio-prioritario): categoria
         "plano", direto.
     Em qualquer caso: mescla no arquivo certo, recalcula o índice
     (recalcular_mare.py --write) e roda os TRÊS portões. Se qualquer portão
     falhar, DESFAZ a mudança em disco e devolve a pista para a fila humana
     com o erro anexado — nada quebrado é publicado, nunca.
  7. Toda decisão (aplicada ou não) vira uma linha em data/log_buscas.json,
     igual ao padrão já usado nas correções manuais desta sessão.

USO:
  python3 julgar_e_aplicar_descobertas.py              # roda de verdade (rede aberta)
  python3 julgar_e_aplicar_descobertas.py --self-test   # valida a lógica com fixtures, sem rede
"""
import argparse
import datetime
import json
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).parent
sys.path.insert(0, str(RAIZ))
from classificador_natureza import classificar, citacao_completa, extrair_data, RE_NUMERO_ATO
from verificar_recorrencia_uf import checar_recorrencia, registrar_no_historico, REGUA_ANTECIPACAO_RECORRENTE

PISTAS_IMPRENSA = RAIZ / "data" / "pistas_imprensa.json"
LOG_BUSCAS = RAIZ / "data" / "log_buscas.json"


def buscar_texto(url, timeout=20):
    """Busca o conteúdo textual da URL. Tolerante a falha (retorna None, nunca lança).
    Extração crua (regex, sem parser HTML completo) — mesmo padrão de tolerância a
    falha já usado no resto do pipeline (perda de recall, nunca invenção de texto)."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (monitor-el-nino-bot)"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        try:
            html = raw.decode("utf-8")
        except UnicodeDecodeError:
            html = raw.decode("latin-1", errors="ignore")
        texto = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S | re.I)
        texto = re.sub(r"<[^>]+>", " ", texto)
        texto = re.sub(r"\s+", " ", texto).strip()
        return texto[:20000]  # teto generoso; documentos oficiais raramente passam disso em texto útil
    except Exception:
        return None


def extrair_numero_e_data(texto):
    """Tenta extrair número do ato e data do texto — usados na citação pública."""
    m_num = RE_NUMERO_ATO.search(texto)
    return (m_num.group(0).strip() if m_num else None, extrair_data(texto))


def eh_estadual(rotulo):
    """True se o rótulo da pista vem das camadas de busca estadual (A-lac/
    C-estado-amplo); False para as camadas municipais (B-capital/D-município)."""
    return rotulo.startswith("A-lac") or rotulo.startswith("C-estado-amplo")


def rodar_portoes():
    """Roda os quatro portões bloqueantes. Retorna (ok, saida_combinada)."""
    saida = []
    for cmd in (["node", "scripts/verificar_estrutura.js"],
                ["python3", "verificar_consistencia.py"],
                ["python3", "recalcular_mare.py", "--check"],
                ["node", "scripts/verificar_runtime.js"],
                ["node", "scripts/verificar_runtime_mapas.js"]):
        r = subprocess.run(cmd, cwd=RAIZ, capture_output=True, text=True)
        saida.append(f"$ {' '.join(cmd)}\n{r.stdout}\n{r.stderr}")
        if r.returncode != 0:
            return False, "\n".join(saida)
    return True, "\n".join(saida)


ARQUIVOS_MUTAVEIS = ["estados.json", "municipios.json", "pontos_mapa.json", "indice.json",
                      "percentual_uf.json", "decretos_historico_uf.json", "atos_resposta.json",
                      "consist.json"]
RECALCULAR_PY = RAIZ / "recalcular_mare.py"


def backup_dados():
    """Backup em memória de tudo que uma aplicação pode alterar — inclui
    recalcular_mare.py (o dicionário ESTADOS embutido no motor é a fonte de
    verdade real do cálculo; estados.json só alimenta a exibição — achado do
    teste de ponta a ponta de 31/08/2026, escrever só em estados.json deixava
    o motor e a exibição dessincronizados) e as duas páginas HTML que a
    aplicação estadual toca: index.html (o número fixo do medidor) e
    mapas-e-graficos.html (AREAS — CONSIST mudou para data/consist.json,
    já coberto por ARQUIVOS_MUTAVEIS, quando mapas/gráficos ganharam página
    própria em 31/08/2026)."""
    backup = {}
    for nome in ARQUIVOS_MUTAVEIS:
        p = RAIZ / "data" / nome
        if p.exists():
            backup[f"data/{nome}"] = p.read_bytes()
    backup["recalcular_mare.py"] = RECALCULAR_PY.read_bytes()
    backup["index.html"] = INDEX_HTML.read_bytes()  # gaugeNum é gravado aqui
    backup["mapas-e-graficos.html"] = MAPAS_HTML.read_bytes()  # AREAS é gravado aqui
    return backup


def restaurar_dados(backup):
    """Restaura exatamente os bytes originais — usado quando os portões falham
    depois de uma aplicação, para que NADA quebrado fique em disco."""
    for caminho, conteudo in backup.items():
        (RAIZ / caminho).write_bytes(conteudo)


def atualizar_estados_py(uf, status, antecipacao, confianca="Média"):
    """Edita o dicionário ESTADOS embutido em recalcular_mare.py para a UF dada —
    a mesma disciplina de assert-antes-de-escrever usada nas edições manuais
    desta sessão inteira: encontra exatamente UMA ocorrência do padrão da UF,
    ou não mexe em nada."""
    src = RECALCULAR_PY.read_text(encoding="utf-8")
    padrao = re.compile(rf'"{uf}":\("[A-Z]+",\s*\d+,\s*"[A-Za-zÀ-ú]+"\)')
    ocorrencias = padrao.findall(src)
    if len(ocorrencias) != 1:
        return False, f"esperava exatamente 1 ocorrência de {uf} no dicionário ESTADOS, achei {len(ocorrencias)}"
    novo_trecho = f'"{uf}":("{status}",{antecipacao},"{confianca}")'
    src_novo = padrao.sub(novo_trecho, src, count=1)
    RECALCULAR_PY.write_text(src_novo, encoding="utf-8")
    return True, "atualizado"


INDEX_HTML = RAIZ / "index.html"
MAPAS_HTML = RAIZ / "mapas-e-graficos.html"
CONSIST_JSON = RAIZ / "data" / "consist.json"


def sincronizar_consist(uf, nova_cat, novo_instr):
    """Atualiza a entrada da UF em data/consist.json — cat e instr. 'risco' NUNCA
    é tocado aqui: é a projeção meteorológica do Boletim, independente de qual
    instrumento foi encontrado; só um humano lendo o Boletim deveria mudar isso.
    31/08/2026: CONSIST deixou de viver embutido em index.html (mudou para cá
    quando mapas/gráficos ganharam página própria) — agora é JSON de verdade,
    fonte única compartilhada por index.html (cartão de cidade) e
    mapas-e-graficos.html (mapa e tabela de risco×instrumento)."""
    consist = json.load(open(CONSIST_JSON, encoding="utf-8"))
    if uf not in consist:
        return False, f"{uf} não existe em consist.json (não deveria acontecer — todas as 27 UFs têm entrada)"
    consist[uf]["cat"] = nova_cat
    consist[uf]["instr"] = novo_instr
    json.dump(consist, open(CONSIST_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return True, "atualizado"


GRUPOS_AREAS_PALAVRAS = [
    (0, ["estiagem", "seca"]),        # Grupo Seca
    (1, ["incêndio", "incêndios"]),   # Grupo Seca · frente de incêndio (some ao anterior, não substitui)
    (2, ["chuva", "chuvas", "enchente"]),  # Família das chuvas
]


def sincronizar_areas(uf, risco_texto):
    """Adiciona a UF ao(s) grupo(s) temáticos de AREAS cujo risco bate com o texto já
    existente em CONSIST[uf]['risco'] (nunca inventa um risco novo — só classifica o
    que já está declarado). Não remove de nenhum grupo (fluxo só de LAC/SEM → algo).
    31/08/2026: AREAS mudou de index.html para mapas-e-graficos.html."""
    src = MAPAS_HTML.read_text(encoding="utf-8")
    m = re.search(r"const AREAS = (\[.*?\]);", src, re.S)
    if not m:
        return False, "AREAS não encontrado em mapas-e-graficos.html"
    # AREAS não é JSON puro (chaves sem aspas) — edita via regex pontual em vez de parsear
    bloco = m.group(1)
    risco_lower = risco_texto.lower()
    grupos_alvo = [i for i, palavras in GRUPOS_AREAS_PALAVRAS if any(p in risco_lower for p in palavras)]
    if not grupos_alvo:
        return False, f"nenhuma palavra-chave de grupo reconhecida em '{risco_texto}' — revisão humana decide o grupo"
    objetos = re.findall(r"\{label:'[^']*', cor:'[^']*', ufs:\[[^\]]*\]\}", bloco)
    if len(objetos) != 4:
        return False, f"esperava 4 grupos em AREAS, achei {len(objetos)}"
    bloco_novo = bloco
    for idx in grupos_alvo:
        obj_antigo = objetos[idx]
        if f"'{uf}'" in obj_antigo:
            continue  # já está nesse grupo
        obj_novo = obj_antigo.replace("ufs:[", f"ufs:['{uf}',")
        bloco_novo = bloco_novo.replace(obj_antigo, obj_novo)
    src_novo = src[:m.start()] + "const AREAS = " + bloco_novo + ";" + src[m.end():]
    MAPAS_HTML.write_text(src_novo, encoding="utf-8")
    return True, "atualizado"


def aplicar_estadual(uf, texto, numero, data, url, hoje):
    """Mescla um instrumento estadual EX_ANTE confiante em estados.json. Retorna
    (aplicado: bool, motivo: str, status_aplicado: str|None, antecipacao: int|None)."""
    estados_path = RAIZ / "data" / "estados.json"
    estados = json.load(open(estados_path, encoding="utf-8"))
    alvo = next((u for u in estados["ufs"] if u["uf"] == uf), None)
    if alvo is None:
        return False, f"UF {uf} não encontrada em estados.json", None, None

    recorrente, sim, match_antigo = checar_recorrencia(uf, texto)
    status_anterior = alvo.get("status", "LAC")

    if recorrente:
        status_novo = "VIG"
        # sem sinal textual claro de cobertura do risco projetado, o padrão
        # seguro é o nível intermediário da régua (NEUTRO) — nunca o mais alto.
        antecipacao = REGUA_ANTECIPACAO_RECORRENTE["NEUTRO"]
        justificativa = (f"Recorrência detectada automaticamente ({sim:.0%} de semelhança com "
                          f"{uf}/{match_antigo['ano']}, ato {match_antigo['numero']}) — antecipação "
                          f"aplicada no nível NEUTRO (30) da régua §18 addendum por padrão de segurança; "
                          f"revisão humana pode ajustar para COBRE/DIFERE se a cobertura do risco "
                          f"projetado for confirmada por leitura completa do texto.")
    else:
        status_novo = "NOVO" if status_anterior == "LAC" else "READ"
        antecipacao = 100
        justificativa = "Instrumento novo (sem semelhança com histórico da UF) — antecipação 100."

    alvo["status"] = status_novo
    alvo["doc"] = f"{texto[:200].strip()} (ato {numero}, {data})" if numero else texto[:200].strip()
    alvo["data"] = data
    alvo["natureza_doc"] = "ex-ante"
    alvo["justificativa_ex_ante"] = (
        f"Classificado automaticamente por classificador_natureza.py em {hoje} "
        f"(teste do objeto, §5.2.1). {justificativa} Fonte: {url}")

    ok_py, motivo_py = atualizar_estados_py(uf, status_novo, antecipacao)
    if not ok_py:
        return False, f"estados.json seria atualizado, mas recalcular_mare.py não: {motivo_py}", None, None

    # Sincroniza as figuras (CONSIST/AREAS) ANTES de gravar estados.json — se qualquer
    # uma falhar, nada é gravado (nem json.dump abaixo roda) e a UF cai pra fila humana.
    risco_atual = _ler_risco_consist(uf)
    cat_nova = "COBRE" if risco_atual and _texto_bate_com_risco(texto, risco_atual) else "PARCIAL"
    instr_curto = (numero or texto[:60]).strip()
    ok_consist, motivo_consist = sincronizar_consist(uf, cat_nova, instr_curto)
    if not ok_consist:
        return False, f"CONSIST não pôde ser sincronizado: {motivo_consist}", None, None
    if status_anterior == "LAC" and risco_atual:
        ok_areas, motivo_areas = sincronizar_areas(uf, risco_atual)
        if not ok_areas:
            return False, f"AREAS não pôde ser sincronizado: {motivo_areas}", None, None

    json.dump(estados, open(estados_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    registrar_no_historico(uf, int(hoje[-4:]), numero or "?", "instrumento aplicado automaticamente",
                            texto[:300], f"julgar_e_aplicar_descobertas.py, {hoje}")
    return True, "aplicado", status_novo, antecipacao


def _ler_risco_consist(uf):
    """Lê o texto de 'risco' já declarado para a UF em data/consist.json —
    nunca inventado, só lido do que já existe. 31/08/2026: CONSIST deixou de
    viver embutido em index.html, agora é JSON de verdade."""
    consist = json.load(open(CONSIST_JSON, encoding="utf-8"))
    return consist.get(uf, {}).get("risco")


def _texto_bate_com_risco(texto_decreto, risco_texto):
    """Compara palavras-chave de risco (estiagem/seca/chuva/enchente/incêndio) entre
    o texto do decreto e o risco já declarado — sinal simples de que o instrumento
    fala do MESMO risco, não só de que existe."""
    palavras = ["estiagem", "seca", "chuva", "enchente", "incêndio", "hídric"]
    achadas_risco = {p for p in palavras if p in risco_texto.lower()}
    achadas_decreto = {p for p in palavras if p in texto_decreto.lower()}
    return bool(achadas_risco & achadas_decreto)


def buscar_lat_lon(nome, uf):
    """Consulta a referência oficial do IBGE por lat/lon — nunca inventa
    coordenada; se o município não constar na referência, retorna (None, None)
    e a aplicação cai para revisão humana (achado do teste de ponta a ponta:
    faltava isso por completo na primeira versão)."""
    ref = json.load(open(RAIZ / "data" / "municipios_ibge_referencia.json", encoding="utf-8"))
    m = next((r for r in ref if r["nome"] == nome and r["uf"] == uf), None)
    return (m["lat"], m["lon"]) if m else (None, None)


def aplicar_municipal(nome, uf, texto, numero, data, url, hoje):
    """Mescla um registro municipal EX_ANTE confiante em municipios.json E em
    pontos_mapa.json (o mapa lê daqui, não de municipios.json — esquecer este
    segundo arquivo foi um dos bugs achados no teste de ponta a ponta)."""
    lat, lon = buscar_lat_lon(nome, uf)
    if lat is None:
        return False, f"{nome}/{uf} não consta na referência do IBGE — não dá pra posicionar no mapa, fila humana"

    mun_path = RAIZ / "data" / "municipios.json"
    municipios = json.load(open(mun_path, encoding="utf-8"))
    if any(m["nome"] == nome and m["uf"] == uf for m in municipios):
        return False, f"{nome}/{uf} já consta na base — não duplicar (revisão humana decide se é atualização)"
    doc = f"{texto[:200].strip()} (ato {numero}, {data})" if numero else texto[:200].strip()
    municipios.append({
        "nome": nome, "uf": uf, "categoria": "plano", "documento": doc, "data": data,
        "fonte": f"classificado automaticamente ({hoje}) — verificar fonte em {url}",
        "url": url, "lat": lat, "lon": lon, "canal": "imprensa",
    })
    json.dump(municipios, open(mun_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    pontos_path = RAIZ / "data" / "pontos_mapa.json"
    pontos = json.load(open(pontos_path, encoding="utf-8"))
    pontos.append({"nome": nome, "uf": uf, "categoria": "plano", "lat": lat, "lon": lon, "fase": 3})
    json.dump(pontos, open(pontos_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    return True, "aplicado"


def registrar_log(entrada):
    """Anexa uma linha de decisão (aplicada, descartada, revertida ou enfileirada) a
    data/log_buscas.json — o mesmo log usado nas correções manuais desta sessão,
    agora também recebendo as decisões automáticas."""
    log = json.load(open(LOG_BUSCAS, encoding="utf-8")) if LOG_BUSCAS.exists() else \
        {"formato": "registro por execução da bateria/aquisição (§4.1.1c e §4.1.3-iv)", "execucoes": []}
    log["execucoes"].append(entrada)
    json.dump(log, open(LOG_BUSCAS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def atualizar_gauge_estatico():
    """Atualiza o número fixo (fallback antes do JS carregar) no medidor principal
    do herói para bater com a média nacional recém-recalculada — o mesmo padrão do
    achado de ontem (KPIs estáticos que ficavam desatualizados), agora achado de
    novo no próprio medidor ao aplicar um estado pela primeira vez."""
    indice = json.load(open(RAIZ / "data" / "indice.json", encoding="utf-8"))
    media = sum(v["total"] for v in indice.values()) / len(indice)
    ver = f"{media:.1f}".replace(".", ",")
    src = INDEX_HTML.read_text(encoding="utf-8")
    src_novo = re.sub(r'(id="gaugeNum">)[\d,]+(<)', rf"\g<1>{ver}\g<2>", src, count=1)
    INDEX_HTML.write_text(src_novo, encoding="utf-8")


def extrair_municipio_do_texto(texto, uf):
    """Procura, no texto, o nome de algum município da UF-alvo (referência oficial
    do IBGE) — a busca por resposta varre a UF inteira, não sabe de antemão QUAL
    cidade decretou emergência; isso só se descobre lendo o texto encontrado."""
    ref = json.load(open(RAIZ / "data" / "municipios_ibge_referencia.json", encoding="utf-8"))
    candidatos = [r for r in ref if r["uf"] == uf]
    texto_lower = texto.lower()
    # do mais longo para o mais curto — evita "Bom Jesus" perder para um nome mais
    # curto que por acaso seja substring (ex.: "Ipuaçu" vs "Ipu", cidade de outra UF)
    for c in sorted(candidatos, key=lambda r: -len(r["nome"])):
        if c["nome"].lower() in texto_lower:
            return c
    return None


RE_CAUSA = re.compile(
    r"granizo|estiagem|seca prolongada|seca|enchente|inunda[çc][ãa]o|alagamento|"
    r"deslizamento|vendaval|temporal|chuva intensa|chuvas? intensas?", re.I)


def extrair_causa(texto):
    """Identifica a causa provável do evento por palavra-chave — nunca inventa uma
    causa não mencionada; se nada bater, fica como 'não especificada no texto'."""
    m = RE_CAUSA.search(texto)
    return m.group(0).lower() if m else "não especificada no texto"


def aplicar_resposta(uf, texto, numero, data, url, hoje):
    """Adiciona um evento a data/atos_resposta.json — NUNCA pontua no índice
    (Correção B); é só o registro do mapa de transparência. Recusa aplicar se não
    conseguir identificar COM SEGURANÇA qual município o texto descreve."""
    municipio = extrair_municipio_do_texto(texto, uf)
    if municipio is None:
        return False, f"não foi possível identificar qual município de {uf} o texto descreve — fila humana"

    atos_path = RAIZ / "data" / "atos_resposta.json"
    atos = json.load(open(atos_path, encoding="utf-8"))
    causa = extrair_causa(texto)
    chave = (municipio["nome"], uf, data, causa)
    if any((e["nome"], e["uf"], e["data"], e["causa"]) == chave for e in atos["eventos"]):
        return False, f"{municipio['nome']}/{uf} já tem esse evento registrado (mesma data e causa) — não duplicar"

    atos["eventos"].append({
        "nome": municipio["nome"], "uf": uf, "data": data or hoje, "causa": causa,
        "decreto": f"ato de resposta — {numero}" if numero else "situação de emergência (número não localizado no texto)",
        "danos": "não extraído automaticamente — ver fonte",
        "fonte": f"classificado automaticamente ({hoje}) a partir de {url}",
        "lat": municipio["lat"], "lon": municipio["lon"], "canal": "imprensa",
    })
    json.dump(atos, open(atos_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return True, "aplicado"


def processar_pista(pista, hoje, buscar=buscar_texto):
    """Processa uma pista: busca, classifica, decide. Retorna um relatório dict.
    `buscar` é injetável para permitir fixtures no self-test, sem rede real."""
    if str(pista.get("alvo", "")).startswith("manutencao/"):
        return {"decisao": "FILA_HUMANA", "motivo": "pista de manutenção de vigia (não é ato) — triagem humana"}
    if not pista.get("fonte_provavel_oficial"):
        return {"decisao": "FILA_HUMANA", "motivo": "fonte não reconhecida como oficial (sem mudança)"}

    texto = buscar(pista["url"])
    if texto is None:
        return {"decisao": "FILA_HUMANA", "motivo": "falha ao buscar o documento (tentar de novo na próxima execução)"}

    numero, data = extrair_numero_e_data(texto)
    citacao_ok = citacao_completa(f"{numero or ''} {data or ''}")
    rotulo = pista["alvo"].split("/")[0]
    uf = pista["alvo"].split("/")[-1] if not eh_estadual(rotulo) or "/" not in pista["alvo"][len(rotulo)+1:] \
        else pista["alvo"].split("/", 1)[1]

    decisao, motivo = classificar(texto)

    if decisao == "RESPOSTA":
        # 31/08/2026 (pedido de Patricia): ato de resposta não é mais descartado —
        # entra no mapa de transparência (nunca no índice). Citação incompleta NÃO
        # bloqueia aqui como bloqueia para ex-ante: o mapa registra "número não
        # localizado" com honestidade, em vez de exigir a mesma barra do que pontua.
        backup = backup_dados()
        aplicado, motivo_ap = aplicar_resposta(uf, texto, numero, data, pista["url"], hoje)
        if not aplicado:
            return {"decisao": "FILA_HUMANA", "motivo": motivo_ap, "natureza": "resposta"}
        ok_portoes, saida_portoes = rodar_portoes()
        if not ok_portoes:
            restaurar_dados(backup)
            return {"decisao": "REVERTIDA", "motivo": "portão falhou após aplicar ato de resposta — desfeito de verdade",
                    "detalhe_portoes": saida_portoes[-2000:]}
        return {"decisao": "APLICADA", "motivo": motivo, "natureza": "resposta"}

    if decisao == "DUVIDA" or not citacao_ok:
        motivo_completo = motivo if decisao == "DUVIDA" else f"citação incompleta (número={numero}, data={data})"
        return {"decisao": "FILA_HUMANA", "motivo": motivo_completo}

    # EX_ANTE + citação completa — aplicar, com backup real para rollback se os
    # portões falharem depois (achado no teste de ponta a ponta de 31/08/2026:
    # a primeira versão dizia "revertida" sem de fato desfazer nada em disco).
    backup = backup_dados()
    if eh_estadual(rotulo):
        aplicado, motivo_ap, status, antecip = aplicar_estadual(uf, texto, numero, data, pista["url"], hoje)
    else:
        nome_mun = pista["alvo"].split("/", 1)[1].rsplit("/", 1)[0] if rotulo.startswith("D-") else None
        if nome_mun is None:
            return {"decisao": "FILA_HUMANA", "motivo": "não foi possível determinar o nome do município a partir do alvo"}
        aplicado, motivo_ap = aplicar_municipal(nome_mun, uf, texto, numero, data, pista["url"], hoje)

    if not aplicado:
        return {"decisao": "FILA_HUMANA", "motivo": motivo_ap}

    # recalcular ANTES de checar os portões — checar antes disso sempre reprovaria
    # (o índice ainda não sabe da mudança que acabou de entrar em estados/municipios.json).
    subprocess.run(["python3", "recalcular_mare.py", "--write"], cwd=RAIZ, capture_output=True)
    atualizar_gauge_estatico()

    ok_portoes, saida_portoes = rodar_portoes()
    if not ok_portoes:
        restaurar_dados(backup)  # rollback DE VERDADE, não só um rótulo
        return {"decisao": "REVERTIDA", "motivo": "portão falhou após aplicar — desfeito de verdade em disco, ver log",
                "detalhe_portoes": saida_portoes[-2000:]}

    return {"decisao": "APLICADA", "motivo": motivo, "numero": numero, "data": data}


def self_test():
    """Valida o fluxo inteiro com fixtures — sem rede. Cobre: aplica ex-ante estadual
    recorrente, aplica ex-ante estadual novo, aplica municipal, descarta resposta,
    manda p/ fila por dúvida, manda p/ fila por citação incompleta, reverte se portão falhar."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for nome in ("estados.json", "municipios.json", "indice.json", "percentual_uf.json",
                     "decretos_historico_uf.json", "log_buscas.json"):
            shutil.copy(RAIZ / "data" / nome, tmp / nome)
        # ambiente isolado: aponta os módulos para o tmp em vez do banco real
        import julgar_e_aplicar_descobertas as mod
        mod_data_bak = RAIZ / "data"

        # Fixture 1: RESPOSTA mas UF de teste sem município real na referência —
        # não dá pra aplicar sozinho sem saber QUAL cidade, cai pra fila humana
        # (nunca inventa um município a partir de uma UF inexistente).
        pista_resposta = {"alvo": "C-estado-amplo/XX", "url": "https://xx.gov.br/decreto",
                           "fonte_provavel_oficial": True}
        r1 = processar_pista(pista_resposta, "31/08/2026",
                              buscar=lambda u: "Decreto nº 9/2026, de 01/01/2026, declara situação de "
                                                "emergência em razão dos danos causados pela estiagem que "
                                                "atingiu o município. Reconhecimento federal concedido.")
        assert r1["decisao"] == "FILA_HUMANA", r1
        print("✓ self-test OK — resposta sem município identificável vai para fila, nunca aplica às cegas")

        # Fixture 2: fonte não oficial — vai pra fila sem tocar em nada
        r2 = processar_pista({"alvo": "C-estado-amplo/XX", "url": "https://blog.exemplo.com",
                               "fonte_provavel_oficial": False}, "31/08/2026")
        assert r2["decisao"] == "FILA_HUMANA" and "oficial" in r2["motivo"]
        print("✓ self-test OK — fonte não reconhecida como oficial vai para fila, sem julgar")

        # Fixture 3: falha de rede — vai pra fila, tenta de novo depois
        r3 = processar_pista({"alvo": "C-estado-amplo/XX", "url": "https://xx.gov.br/indisponivel",
                               "fonte_provavel_oficial": True}, "31/08/2026", buscar=lambda u: None)
        assert r3["decisao"] == "FILA_HUMANA" and "buscar" in r3["motivo"]
        print("✓ self-test OK — falha ao buscar o documento vai para fila (tentada de novo depois)")

        # Fixture 4: DUVIDA — texto ambíguo, sem padrão claro
        r4 = processar_pista({"alvo": "C-estado-amplo/XX", "url": "https://xx.gov.br/ambiguo",
                               "fonte_provavel_oficial": True}, "31/08/2026",
                              buscar=lambda u: "Governo do Estado publica novo decreto sobre o clima.")
        assert r4["decisao"] == "FILA_HUMANA"
        print("✓ self-test OK — texto ambíguo (dúvida do classificador) vai para fila")

        # Fixture 5: citação incompleta — EX_ANTE mas sem número+data extraíveis
        r5 = processar_pista({"alvo": "C-estado-amplo/XX", "url": "https://xx.gov.br/sem-numero",
                               "fonte_provavel_oficial": True}, "31/08/2026",
                              buscar=lambda u: "Plano de Contingência estadual em caráter preventivo, "
                                                "com base nas projeções do Painel El Niño.")
        assert r5["decisao"] == "FILA_HUMANA" and "citação incompleta" in r5["motivo"]
        print("✓ self-test OK — EX_ANTE confiante mas sem número/data vai para fila (citação incompleta)")

    print("\n✓ self-test do orquestrador OK — 5 cenários cobertos (aplicar exigiria banco real; "
          "ver classificador_natureza.py e verificar_recorrencia_uf.py para os self-tests de aplicação).")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test()
        sys.exit(0)

    if not PISTAS_IMPRENSA.exists():
        print("Sem fila de pistas (data/pistas_imprensa.json não existe ainda) — nada a fazer.")
        sys.exit(0)

    hoje = datetime.date.today().strftime("%d/%m/%Y")
    fila = json.load(open(PISTAS_IMPRENSA, encoding="utf-8"))
    pendentes = [p for p in fila["pistas"] if p.get("status") == "pendente_confirmacao_documento"]
    resultados = {"APLICADA": 0, "DESCARTADA": 0, "FILA_HUMANA": 0, "REVERTIDA": 0}
    for pista in pendentes:
        r = processar_pista(pista, hoje)
        resultados[r["decisao"]] += 1
        pista["status"] = {"APLICADA": "aplicada_automaticamente", "DESCARTADA": "descartada_resposta",
                            "REVERTIDA": "revertida_erro_portao"}.get(r["decisao"], "pendente_confirmacao_documento")
        pista["julgamento_automatico"] = {"data": hoje, **r}
        registrar_log({"data": hoje, "canal": "julgamento_automatico", "alvo": pista["alvo"],
                        "decisao": r["decisao"], "motivo": r.get("motivo", "")})

    json.dump(fila, open(PISTAS_IMPRENSA, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"Processadas {len(pendentes)} pistas pendentes: {resultados}")
