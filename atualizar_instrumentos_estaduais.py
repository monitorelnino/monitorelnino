#!/usr/bin/env python3
"""
atualizar_instrumentos_estaduais.py
=====================================
Camada 1 do Protocolo de Busca v2 (Metodologia §4.1.1): verifica repositórios
estaduais ESTRUTURADOS que listam publicamente os planos de contingência
municipais recebidos das coordenadorias, e propõe atualizações a
data/municipios.json quando encontra município novo ou edição mais recente
do que a registrada na base.

REGRA DE OURO (igual a atualizar_transferencias.py): este script NUNCA escreve
diretamente em municipios.json. Ele gera data/instrumentos_revisar.json — você
(ou eu, quando instruído) revisa, remove o que não deve entrar, e só então roda:

    python3 aplicar_revisao.py --arquivo data/instrumentos_revisar.json

REGISTRO DE REPOSITÓRIOS (extensível):
  Cada UF mapeada tem uma função de parser própria, porque cada site estadual
  publica a lista em formato diferente. Adicionar uma UF = escrever um parser
  novo e registrá-lo em REPOSITORIOS; nada mais muda.
  Implementadas: SE, ES, RS (pasta pública do SharePoint). Mapeadas mas SEM parser ainda (grafado no protocolo de
  busca como pendência): PR (SISDC), ES, AM — ver Metodologia §4.1.1(d).

LIMITAÇÃO DE AMBIENTE (declarada, não escondida): o sandbox onde este projeto
é normalmente editado tem a rede restrita a um allowlist de domínios de
pacotes (pypi/npm/github); domínios .gov.br NÃO estão liberados. Este script
portanto não pode ser executado ao vivo dali — ele roda no ambiente real de
publicação (a Action semanal do GitHub, ou a máquina de quem publica), que tem
acesso normal à internet. Por isso o parser é testado à parte, contra uma
cópia salva (fixture) de uma captura real da página — ver tests/.

Uso:
  python3 atualizar_instrumentos_estaduais.py                 # roda todas as UFs implementadas
  python3 atualizar_instrumentos_estaduais.py --uf SE          # só uma UF
  python3 atualizar_instrumentos_estaduais.py --uf SE --fixture tests/fixtures/se_planos_20260826.md
                                                                # modo offline/teste, sem rede
"""
import argparse
import datetime
import json
import re
import sys
import unicodedata
from pathlib import Path
from coletores_base import ua_de, hoje_editorial, gravar_em  # noqa: E402  (§228: um cliente só, com propósito)

RAIZ = Path(__file__).parent
DATA = RAIZ / "data"

ANO_LIMIAR_VIGENTE = 2024  # edição >= este ano => "plano"; menor => "plano_antigo" (mesma régua já usada na edição de 26/08/2026)


def norm(s: str) -> str:
    """Normaliza nome de município (minúsculas, sem acento, sem pontuação) para comparação robusta contra a base IBGE."""
    return unicodedata.normalize("NFD", s.upper()).encode("ascii", "ignore").decode()


def categoria_por_ano(ano: int) -> str:
    """Deriva a categoria do registro (plano vigente, plano de ciclo anterior etc.) a partir do ano do documento encontrado no repositório estadual."""
    return "plano" if ano >= ANO_LIMIAR_VIGENTE else "plano_antigo"


# ---------------------------------------------------------------------------
# Parsers por UF — cada um recebe o texto bruto da página (markdown ou html
# já extraído) e devolve uma lista de {nome, ano_edicao, url}.
# ---------------------------------------------------------------------------

def parse_es(texto: str):
    """CEPDEC/ES — tabela cujo título de linha traz o município e o ano:
    '| [<NOME> - PLANO DE CONTINGÊNCIA - <ANO>](<url>) | ... |'

    O repositório capixaba usa SEIS grafias diferentes do mesmo termo
    (CONTINGÊNCIA, CONTIGÊNCIA, CONTINGENCIA, CONTIGENCIA, COMTINGÊNCIA,
    'PLANO CONTINGENCIA'), com e sem hífen antes do ano, e ainda erra nomes
    de município (ITAGUAÇUÍ→Itaguaçu, VILA PAVAO→Vila Pavão). Por isso o
    padrão é deliberadamente frouxo no meio e o nome é validado depois
    contra a malha IBGE — exatamente a lição que motivou o dicionário de
    recuperação com variantes erradas (Metodologia §4.1.1).
    """
    padrao = re.compile(
        r"\|\s*\[\s*(.+?)\s*[-–]?\s*PLANO\s+(?:DE\s+)?(?:CON|COM)T[IY]?N?G[ÊE]NCIA\s*[-–]?\s*"
        r"((?:\d{4})(?:\s*[-–]\s*\d{4})?)(?:\s*-\s*\d)?\s*\]\((https?://[^)]+)\)",
        re.IGNORECASE,
    )
    achados = []
    for m in padrao.finditer(texto):
        nome_bruto, anos, url = m.groups()
        nome = nome_bruto.strip(" -–").title()
        for prep in [" Da ", " De ", " Do ", " Das ", " Dos "]:
            nome = nome.replace(prep, prep.lower())
        # intervalo (ex.: 2025-2026, 2022-2025): usa o ano final = vigência declarada
        anos_encontrados = [int(a) for a in re.findall(r"\d{4}", anos)]
        achados.append({"nome": nome, "ano_edicao": max(anos_encontrados),
                        "rotulo_ano": anos.strip(), "url": url})
    return achados


def parse_se(texto: str):
    """Defesa Civil de Sergipe (DEPEC/SUPDEC) — lista em bullets:
    'PLANO DE CONTINGÊNCIA MUNICIPAL DE <NOME> – EDIÇÃO <ANO> [Clique aqui](<url>)'
    """
    padrao = re.compile(
        r"PLANO DE CONTING[ÊE]NCIA MUNICIPAL DE\s+(.+?)\s*[–-]\s*EDI[ÇC][ÃA]O\s*(\d{4})\s*"
        r"\[[^\]]*\]\((https?://\S+?)\)",
        re.IGNORECASE,
    )
    achados = []
    for m in padrao.finditer(texto):
        nome_bruto, ano, url = m.groups()
        nome = nome_bruto.strip().title()
        # correções de capitalização de conectivos comuns em nomes de município
        for prep in [" Da ", " De ", " Do ", " Das ", " Dos "]:
            nome = nome.replace(prep, prep.lower())
        achados.append({"nome": nome, "ano_edicao": int(ano), "url": url})
    return achados

def parse_rs(texto: str):
    """Casa Militar/RS — pasta pública de PLANCONs (SharePoint, sem login). `texto` é o JSON da listagem
    (`listar_sharepoint`): [{name, webUrl}]. O nome do arquivo não tem padrão (535 arquivos: 'PLANCON - X.pdf',
    'PlanCon_X_2025.pdf', 'Plano de Contingência Municipal 2025_X.pdf', só 'X.pdf'): tira-se o ruído e o
    resto é o candidato a município, que `casar_com_ibge` confirma ou devolve como órfão. Sem ano no nome,
    a categoria é `plano_nomeado` (existe, edição não lida); o juiz lê o documento. Por município vale o ano
    mais recente; PDF antes de DOCX."""
    ruido = re.compile(r"PLANO DE CONTING\w*(?: DE\b)?|PLAN ?CON\b|DEFESA CIVIL|MUNICIPAL|VERSAO\s*[\d.]+|\bRASCUNHO\b|\bCOMDEC\b")
    melhor = {}
    for it in json.loads(texto):
        nome_arq, ext = it["name"].rsplit(".", 1) if "." in it["name"] else (it["name"], "")
        if ext.lower() not in ("pdf", "doc", "docx", "url") or re.search(r"laudo|parecer|anexo", nome_arq, re.I):
            continue
        t = norm(re.sub(r"([a-zà-ÿ])([A-ZÀ-Ý])", r"\1 \2", nome_arq).replace("_", " "))
        ano = re.search(r"\b(19|20)\d{2}\b", t)
        nome = re.sub(r"[-–\d]+", " ", ruido.sub(" ", t)).strip()
        if not nome:
            continue
        a = {"nome": nome.title(), "url": it["webUrl"],
             **({"ano_edicao": int(ano.group(0))} if ano else
                {"ano_edicao": 0, "rotulo_ano": "s/d", "categoria": "plano_nomeado"})}
        k, peso = norm(nome), (a["ano_edicao"], ext.lower() == "pdf")
        if k not in melhor or peso > melhor[k][0]:
            melhor[k] = (peso, a)
    return [a for _, a in melhor.values()]


def listar_sharepoint(link: str, pausa: float = 2.0):
    """Lista, sem login, os arquivos da pasta pública do SharePoint do link de compartilhamento: o GET do
    link entrega os cookies da sessão anônima (a API anônima do OneDrive não os usa e devolve 0 filhos), e com
    eles a REST do SharePoint lista cada pasta. Cliente identificado; 401/403/429/451 é recusa e para
    (`raise_for_status`, sem nova via). Rodada na Action, não no sandbox."""
    import time
    from urllib.parse import quote, urlparse
    from coletores_base import sessao_sharepoint
    s = sessao_sharepoint(link, "repositórios estaduais de planos")
    host, raiz = "https://" + urlparse(link).netloc, REPOSITORIOS["RS"]["pasta"]
    site, pastas, achados = "/".join(raiz.split("/")[:3]), [raiz], []
    while pastas:
        pasta = pastas.pop()
        time.sleep(pausa)
        r = s.get(f"{host}{site}/_api/web/GetFolderByServerRelativeUrl('{quote(pasta.replace(chr(39), chr(39) * 2))}')",
                  params={"$expand": "Folders,Files"}, headers={"Accept": "application/json;odata=verbose"}, timeout=30)
        r.raise_for_status()
        d = r.json()["d"]
        pastas += [f["ServerRelativeUrl"] for f in d["Folders"]["results"] if f["Name"] != "Forms"]
        achados += [{"name": f["Name"], "webUrl": host + quote(f["ServerRelativeUrl"])} for f in d["Files"]["results"]]
    print(f"  [sharepoint] {len(achados)} arquivo(s)", file=sys.stderr)
    return json.dumps(achados)


REPOSITORIOS = {
    "SE": {
        "url": "https://defesacivil.se.gov.br/planos-de-contigencia/",
        "fonte": "Defesa Civil SE (DEPEC/SUPDEC) — repositório estadual de PLANCONs",
        "canal": "repositorio_estadual",
        "parser": parse_se,
    },
    "ES": {
        "url": "https://defesacivil.es.gov.br/planos-de-contigencia",
        "fonte": "CEPDEC/ES — repositório estadual de planos de contingência municipais",
        "canal": "repositorio_estadual",
        "parser": parse_es,
    },
    "RS": {
        "url": "https://rsgovbr-my.sharepoint.com/:f:/g/personal/casa-militar_casamilitar_rs_gov_br/IgDtPUo8By2jT7gAi9XGU-uQAeJRsR-iSsJyprJYV8Wb-mo?e=crxaoy",
        "fonte": "Defesa Civil RS (Casa Militar/SUBPDEC) — pasta pública de PLANCONs recebidos, via Prepara RS (22/10/2026)",
        "canal": "repositorio_estadual",
        "parser": parse_rs,
        "pasta": "/personal/casa-militar_casamilitar_rs_gov_br/Documents/Casa Militar/SUBCHEFIAS/SUBCHEFIA DE PROTEÇÃO E DEFESA CIVIL/3. Departamento de Gestão de Riscos/Divisão Técnica de Riscos/Planos de contingência/TODOS PLANCONS RECEBIDOS",
        "carregar": listar_sharepoint,
    },
    "PR": {"parser": None, "nota": "SISDC/CEPDEC-PR — planos gerados no sistema, sem lista pública de PDFs para parser (Protocolo de Busca v2, decisão pendente ii)"},
    "AM": {"parser": None, "nota": "repositório estadual conhecido, parser não implementado"},
    # Ausências VERIFICADAS em 26/08/2026 (registradas para não repetir a busca):
    # o estado publica material de orientação/modelo, mas NÃO um repositório dos
    # planos municipais recebidos. Rever se a página mudar.
    "SC": {"parser": None, "nota": "VERIFICADO 26/08/2026 — defesacivil.sc.gov.br/municipios/ publica apenas pacotes-modelo (PlanCon AS, PlanCon EduAgravi); sem repositório de planos municipais. Cobertura de SC vem do levantamento declarado do TCE-SC (Painel Farol)"},

    # ---- Sondagem de 24/09/2026 (§195), pedido editorial de estender o canal ----------------
    # SE e ES são as duas UFs com repositório de PLANCONs municipais e parser, e juntas já deram 84
    # dos planos do banco — o dobro do que o canal inteiro de diários municipais produziu. O pedido
    # foi estender às outras. O QUE FOI FEITO, e o seu limite, declarado: as 23 UFs restantes foram
    # sondadas nos três caminhos que SE e ES usam (/planos-de-contigencia — com a grafia sem o
    # segundo "n" que os dois adotam —, /planos-de-contingencia e /plancon), com o cliente
    # identificado e respeitando robots (§185). Seis responderam; nenhuma é repositório municipal.
    # ISSO NÃO PROVA QUE NÃO EXISTE: prova que não está nesses três caminhos. Um repositório sob
    # outro endereço, ou atrás de JavaScript, escapa desta sondagem — a descoberta renderizada
    # (descobrir_planos.py --renderizar) é o passo seguinte, e está declarado como pendente.
    "MS": {"parser": None, "nota": "SONDADO 24/09/2026 — defesacivil.ms.gov.br/planos-de-contingencia responde 293 kB com o título 'Planos de Contingência (PLANCON)', mas a página não lista plano municipal nenhum: só a Comissão Estadual e botões de compartilhamento. Página informativa, não repositório"},
    "MG": {"parser": None, "nota": "SONDADO 24/09/2026 — defesacivil.mg.gov.br/planos-de-contigencia responde com aviso de período eleitoral (padrão do §182: o que está suspenso é a seção, não o sítio). Reconferir depois de 25/10"},
    "TO": {"parser": None, "nota": "SONDADO 24/09/2026 — bombeiros.to.gov.br/planos-de-contigencia responde 'Aviso de Suspensão' do período eleitoral. Reconferir depois de 25/10"},
    "PI": {"parser": None, "nota": "SONDADO 24/09/2026 — www.pi.gov.br/planos-de-contigencia responde sob aviso de período eleitoral, com 5 PDFs na página; conteúdo não conferido. Reconferir depois de 25/10"},
    "SP": {"parser": None, "nota": "SONDADO 24/09/2026 — defesacivil.sp.gov.br/planos-de-contigencia devolve a página institucional, sem lista de planos municipais. Ver também o muro de robô do §186 neste domínio"},
    "AL": {"parser": None, "nota": "SONDADO 24/09/2026 — defesacivil.al.gov.br/planos-de-contigencia responde 349 bytes (página vazia)"},
    # ---- Descoberta RENDERIZADA de 24/09/2026 (§197), o passo que a sonda por caminho não alcança --
    # As 21 UFs sem parser tiveram a home aberta em navegador real e a navegação lida em busca de
    # seção de planos MUNICIPAIS. Três candidatos, e os três dizem coisas diferentes:
    "PA": {"parser": None, "nota": "DESCOBERTO 24/09/2026 — plancon.defesacivilpa.com.br é o SISTEMA PLANCON do CBMPA/CEPDEC: 'Gestão municipal de planos de contingência — cadastro, revisão, aprovação e exportação'. Fica ATRÁS DE LOGIN, e login é recusa que se respeita (§170). Os planos municipais do PA existem e não são públicos: é a mesma forma do SISDC do PR. Via de cobertura por LAI, decisão da editoria"},
    "RJ": {"parser": None, "nota": "DESCOBERTO 24/09/2026 — defesacivil.rj.gov.br/index.php/para-municipios/plano-de-contingencias-dc reúne 38 PDFs, mas são do ESTADO, não dos municípios: PLACON 2025/2026 (preservado, hash eefffe3f449f8cb5…, 45 MB) e planos setoriais de CGE, DRM, GSI, INEA e PGE. Não é repositório municipal; é instrumento estadual, e entra na fila R7 como candidato a reclassificação de RJ, hoje VIG"},
    # PR já estava mapeado acima e a descoberta renderizada confirmou o mesmo desenho do PA: sistema,
    # não repositório. Dois estados guardando plano municipal atrás de autenticação é padrão, não
    # acaso, e é matéria para pedido de LAI — não para raspagem.
    #
    # As demais não responderam em nenhum dos três caminhos (404 ou sem resposta) em 24/09/2026:
    # AC, BA, CE, DF, GO, MA, MT, PB, PE, RN, RR. Ausência NOS CAMINHOS SONDADOS, não
    # ausência de repositório — a distinção é a mesma do §194 entre "procuramos e não há" e "não
    # havia onde procurar", e ela vale também para o que o Monitor ainda não procurou direito.
}


def casar_com_ibge(achados: list[dict], uf: str, ref: list[dict]):
    """Valida cada nome achado contra a malha IBGE da UF, devolve o nome oficial
    e anexa as coordenadas da referência (que traz lat/lon desde 26/08/2026, o
    que dispensa geocodificação externa no pipeline).
    O repositório do órgão pode grafar errado (ITAGUAÇUÍ→Itaguaçu, VILA PAVAO→
    Vila Pavão); nenhum registro entra na base com nome que não exista na malha —
    os não casados são devolvidos à parte para conferência humana, jamais
    descartados em silêncio."""
    oficiais = {norm(r["nome"]): r for r in ref if r["uf"] == uf}
    casados, orfaos = [], []
    for a in achados:
        chave = norm(a["nome"])
        oficial = oficiais.get(chave)
        if oficial is None:   # o nome do arquivo traz o município e mais ruído: vale o maior nome oficial contido, por palavra inteira
            dentro = [k for k in oficiais if re.search(rf"\b{re.escape(k)}\b", chave)]
            junto = chave.replace(" ", "")   # 'TRESPALMEIRAS': espaço comido; só nomes longos, para não casar por acaso
            dentro = dentro or [k for k in oficiais if len(k) > 9 and k.replace(" ", "") in junto]
            oficial = oficiais[max(dentro, key=len)] if dentro else None
        if oficial is None:
            # tolerância a erro de grafia do órgão: similaridade alta e ÚNICA
            import difflib
            proximos = difflib.get_close_matches(chave, list(oficiais.keys()), n=2, cutoff=0.88)
            if len(proximos) == 1:
                oficial = oficiais[proximos[0]]
                a["nome_no_repositorio"] = a["nome"]
            else:
                orfaos.append(a)
                continue
        a["nome"] = oficial["nome"]
        if "lat" in oficial and "lon" in oficial:
            a["lat"], a["lon"] = oficial["lat"], oficial["lon"]
        casados.append(a)
    melhor = {}   # dois arquivos do mesmo município: fica o de edição mais recente
    for a in casados:
        if a["nome"] not in melhor or a["ano_edicao"] > melhor[a["nome"]]["ano_edicao"]:
            melhor[a["nome"]] = a
    return list(melhor.values()), orfaos


def carregar_texto(uf: str, fixture: str | None) -> str:
    """Baixa e extrai o texto de uma página ou documento do repositório estadual, com tratamento de encoding e timeout."""
    if fixture:
        return Path(fixture).read_text(encoding="utf-8")
    try:
        import requests
    except ImportError:
        sys.exit("Erro: pacote 'requests' ausente (deveria estar em requirements.txt).")
    url = REPOSITORIOS[uf]["url"]
    if "carregar" in REPOSITORIOS[uf]:
        return REPOSITORIOS[uf]["carregar"](url)
    resp = requests.get(url, timeout=30, headers={"User-Agent": ua_de("repositórios estaduais de planos")})
    resp.raise_for_status()
    return html_para_texto(resp.text, url)


def html_para_texto(html: str, base: str) -> str:
    """Os parsers de SE e ES leem texto com link em markdown e célula de tabela entre barras (a captura que
    os motivou); a página chega em HTML. Sem esta ponte `parse_es` lia 0 instrumentos (22/10/2026)."""
    from html import unescape
    from urllib.parse import urljoin
    html = re.sub(r"(?is)<(script|style)\b.*?</\1>", "", html)
    html = re.sub(r"(?is)<a\b[^>]*?href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>",
                  lambda m: "[%s](%s)" % (re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", unescape(m.group(2)))).strip(),
                                         urljoin(base, unescape(m.group(1)).strip().replace(" ", "%20"))), html)
    return unescape(re.sub(r"<[^>]+>", " ", re.sub(r"(?i)<t[dh]\b[^>]*>", " | ", html)))


def diagnosticar(uf: str, achados: list[dict], municipios: list[dict]) -> list[dict]:
    """Compara os achados do repositório contra a base e devolve propostas."""
    cfg = REPOSITORIOS[uf]
    base_uf = {norm(m["nome"]): m for m in municipios if m["uf"] == uf}
    hoje = hoje_editorial().strftime("%d/%m/%Y")
    propostas = []
    for a in achados:
        chave = norm(a["nome"])
        categoria_proposta = a.get("categoria") or categoria_por_ano(a["ano_edicao"])
        atual = base_uf.get(chave)
        registro_base = {
            "nome": a["nome"], "uf": uf, "categoria": categoria_proposta,
            **({"lat": a["lat"], "lon": a["lon"]} if "lat" in a else {}),
            "documento": f"PLANCON edição {a.get('rotulo_ano', a['ano_edicao'])} (repositório estadual)",
            # 08/10/2026 (A3-09): `data` era HOJE -- o dia em que o Monitor consultou o
            # repositorio --, e a ficha publicava isso como se fosse a data do plano. Em 83
            # registros de ES e SE a ficha dizia 26/08/2026, e 9 deles sao `plano_antigo`: um
            # plano antigo com data de 2026 e contradicao publicada. `data` passa a ser o ano da
            # EDICAO do documento; a data da consulta tem campo proprio, `localizado_em`.
            "data": str(a.get("rotulo_ano", a["ano_edicao"])),
            "localizado_em": hoje,
            "fonte": cfg["fonte"], "url": a["url"], "canal": cfg["canal"],
        }
        if atual is None:
            propostas.append({"acao": "novo", "uf": uf, **registro_base})
        elif atual["categoria"] == "nao_localizado":
            propostas.append({"acao": "atualizar", "uf": uf, "de_categoria": atual["categoria"], **registro_base})
        elif atual["categoria"] != categoria_proposta and atual.get("url") != a["url"]:
            # o repositório mostra edição de categoria diferente da já registrada
            # (ex.: base tinha plano_antigo e o repositório agora lista edição vigente)
            ordem = {"nao_localizado": 0, "plano_nomeado": 0, "plano_antigo": 1, "decreto": 1, "plano_elaboracao": 1, "plano": 2}
            if ordem.get(categoria_proposta, 0) > ordem.get(atual["categoria"], 0):
                propostas.append({"acao": "atualizar", "uf": uf, "de_categoria": atual["categoria"], **registro_base})
        # se já é 'plano' ou 'plano_antigo' e a URL bate: nada a propor (já sincronizado)
    return propostas


def pistas_das_propostas(propostas: list[dict], ref: list[dict]) -> list[dict]:
    """Cada instrumento listado por repositório estadual vira PISTA na porta única: o documento só pontua
    depois que o juiz o lê e o preserva (D1, hash); `aplicar_revisao` põe `plano` sem hash e o portão de
    fichas reprova. Função pura. A pista nasce sem confirmação de documento oficial (trava de campo R7)."""
    ibge = {(r["uf"], norm(r["nome"])): str(r["codigo_ibge"]).zfill(7) for r in ref}
    hoje = hoje_editorial().isoformat()
    return [{"documento_oficial_confirmado": None, "promovivel": False, "municipio": p["nome"], "uf": p["uf"],
             "ibge": ibge[(p["uf"], norm(p["nome"]))], "url": p["url"], "tipo": "plano", "nivel": "A",
             "titulo": f"{p['fonte']} · {p['nome']}/{p['uf']}: plano de contingência, {p['documento']}"[:300],
             "trecho": p["documento"], "data_publicacao": None, "origem": "descoberta", "hash_evidencia": None,
             "data": hoje, "registrado_em": hoje} for p in propostas if (p["uf"], norm(p["nome"])) in ibge]


def autoteste() -> int:
    """Autoteste PURO (A3-30, A6-26, 08/10/2026): sem rede, sem ler `data/`, sem escrever nada.

    O script não tinha autoteste, e é ele que propõe mudança de categoria a partir do que o
    repositório estadual lista. Os fixtures são os dois casos reais: ES publica PLANCON por edição
    anual; SE mantém, no mesmo repositório, edição de 2026 ao lado de planos de 2018 e 2019.
    """
    casos = [
        ("edição deste ciclo é plano vigente", categoria_por_ano(2026) == "plano"),
        ("edição do limiar é plano vigente", categoria_por_ano(ANO_LIMIAR_VIGENTE) == "plano"),
        ("edição anterior ao limiar é plano de ciclo anterior",
         categoria_por_ano(ANO_LIMIAR_VIGENTE - 1) == "plano_antigo"),
        ("edição de 2018 é plano de ciclo anterior", categoria_por_ano(2018) == "plano_antigo"),
    ]
    achados_es = [{"nome": "Linhares", "ano_edicao": 2025, "rotulo_ano": "2025",
                   "url": "https://x.es.gov.br/plancon-2025.pdf", "lat": -19.4, "lon": -40.1}]
    base = [{"nome": "Linhares", "uf": "ES", "categoria": "nao_localizado"},
            {"nome": "Poço Redondo", "uf": "SE", "categoria": "plano"}]
    props = diagnosticar("ES", achados_es, base)
    casos.append(("quem estava sem registro recebe proposta de atualização",
                  len(props) == 1 and props[0]["acao"] == "atualizar"))
    casos.append(("a proposta leva a data do DOCUMENTO, não a da consulta (A3-09)",
                  props and props[0]["data"] == "2025"))
    casos.append(("a proposta declara quando foi localizada",
                  props and bool(props[0].get("localizado_em"))))
    novos = diagnosticar("ES", [{**achados_es[0], "nome": "Cidade Nova"}], base)
    casos.append(("município fora da base vira proposta nova",
                  len(novos) == 1 and novos[0]["acao"] == "novo"))
    iguais = diagnosticar("SE", [{"nome": "Poço Redondo", "ano_edicao": 2026,
                                  "rotulo_ano": "2026", "url": "https://y.se.gov.br/p.pdf"}], base)
    casos.append(("plano já registrado com categoria igual não gera proposta", iguais == []))
    nomes = ["PLANCON - CERRO GRANDE DO SUL.pdf", "PlanCon_MORMAÇO_2025.pdf", "Saldanha Marinho.pdf",
             "Plano de Contingência Municipal 2025_CachoeiraDoSul.pdf", "BRAGA_PLANCON.pdf",
             "Plano de Contingencia de Nova Roma do Sul - Versão 1.0.pdf", "ITATI - PLANCON 2025.pdf",
             "PLANCON - DOIS IRMÃOS.docx", "PLANCON - DOIS IRMÃOS.pdf", "PlanCon CAMPOS BORGES_2025.pdf",
             "Plano de Contingência - Defesa Civil Farroupilha.docx", "anexo.xlsx"]
    rs = parse_rs(json.dumps([{"name": n, "webUrl": "https://x/" + n} for n in nomes]))
    por = {a["nome"]: a for a in rs}
    casos.append(("RS: xlsx não é plano; um achado por município", len(rs) == 10))
    casos.append(("RS: ruído do nome sai (PLANCON, plano de contingência, versão, defesa civil)",
                  {"Cerro Grande Do Sul", "Nova Roma Do Sul", "Farroupilha", "Braga"} <= set(por)))
    casos.append(("RS: camelCase e underscore viram nome", "Cachoeira Do Sul" in por and "Mormaco" in por))
    casos.append(("RS: ano do nome vale; sem ano é plano nomeado, edição não lida",
                  por["Itati"]["ano_edicao"] == 2025 and por["Braga"]["categoria"] == "plano_nomeado"
                  and por["Braga"]["rotulo_ano"] == "s/d"))
    casos.append(("RS: PDF vence DOCX do mesmo município", por["Dois Irmaos"]["url"].endswith(".pdf")))
    ok_ibge, orf = casar_com_ibge([dict(a) for a in rs], "RS", [{"nome": n, "uf": "RS"} for n in
                                  ["Mormaço", "Cerro Grande do Sul", "Itati"]])
    casos.append(("RS: nome não casado na malha IBGE volta como órfão, não entra", len(ok_ibge) == 3 and len(orf) == 7))
    es_html = html_para_texto('<table><tr><td><a href="/media/p.pdf">LINHARES - PLANO DE CONTINGÊNCIA - 2025</a></td></tr></table>',
                              "https://defesacivil.es.gov.br/planos")
    se_html = html_para_texto('<li>PLANO DE CONTINGÊNCIA MUNICIPAL DE POÇO REDONDO – EDIÇÃO 2026 <a href="https://s/p.pdf"><b>Clique</b> aqui</a></li>',
                              "https://defesacivil.se.gov.br/")
    casos.append(("HTML da página alimenta o parser de ES (link relativo vira absoluto)",
                  [(a["nome"], a["ano_edicao"], a["url"]) for a in parse_es(es_html)]
                  == [("Linhares", 2025, "https://defesacivil.es.gov.br/media/p.pdf")]))
    casos.append(("HTML da página alimenta o parser de SE",
                  [(a["nome"], a["ano_edicao"]) for a in parse_se(se_html)] == [("Poço Redondo", 2026)]))
    pi = pistas_das_propostas(novos, [{"nome": "Cidade Nova", "uf": "ES", "codigo_ibge": 3201234}])
    casos.append(("proposta vira pista na porta única, sem hash e sem confirmação de documento",
                  len(pi) == 1 and pi[0]["ibge"] == "3201234" and pi[0]["hash_evidencia"] is None
                  and pi[0]["documento_oficial_confirmado"] is None and pi[0]["origem"] == "descoberta"))
    ruins = [n for n, ok in casos if not ok]
    for n, ok in casos:
        print(f"  {'✓' if ok else '✗'} {n}")
    print(f"{'✓ AUTOTESTE OK' if not ruins else f'✗ AUTOTESTE: {len(ruins)} falha(s)'} — "
          f"{len(casos)} casos, sem rede e sem escrita.")
    return 1 if ruins else 0


def main():
    """Percorre os repositórios estaduais com parser implementado, compara com o banco atual e grava as propostas em data/instrumentos_revisar.json para aprovação humana."""
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--uf", help="Rodar só esta UF (padrão: todas as implementadas)")
    ap.add_argument("--fixture", help="Arquivo local para testar sem rede (uso com --uf)")
    ap.add_argument("--pistas", action="store_true", help="Grava as propostas como pistas (porta única) para o juiz ler, em vez de gravar data/instrumentos_revisar.json")
    args = ap.parse_args()

    ufs = [args.uf] if args.uf else [u for u, c in REPOSITORIOS.items() if c["parser"]]
    municipios = json.load(open(DATA / "municipios.json", encoding="utf-8"))

    ref = json.load(open(DATA / "municipios_ibge_referencia.json", encoding="utf-8"))
    todas_propostas, falhas = [], []
    for uf in ufs:
        cfg = REPOSITORIOS.get(uf)
        if not cfg:
            print(f"[erro] UF não registrada: {uf}"); continue
        if not cfg["parser"]:
            print(f"[pulado] {uf}: {cfg.get('nota', 'sem parser implementado')}")
            continue
        print(f"[{uf}] verificando {cfg['url']} ...")
        try:
            texto = carregar_texto(uf, args.fixture)
        except Exception as e:
            print(f"  [FALHA] não foi possível verificar {uf}: {e}")
            falhas.append(uf)
            continue
        achados = cfg["parser"](texto)
        print(f"  {len(achados)} instrumento(s) listado(s) no repositório")
        achados, orfaos = casar_com_ibge(achados, uf, ref)
        if orfaos:
            print(f"  [atenção] {len(orfaos)} nome(s) não casaram com a malha IBGE — NÃO entram, conferir à mão:")
            for o in orfaos: print(f"      · '{o['nome']}' ({o['url'][:80]})")
        renomeados = [a for a in achados if "nome_no_repositorio" in a]
        if renomeados:
            print(f"  [nota] {len(renomeados)} grafia(s) corrigida(s) pela malha IBGE:")
            for r in renomeados: print(f"      · '{r['nome_no_repositorio']}' → {r['nome']}")
        propostas = diagnosticar(uf, achados, municipios)
        todas_propostas.extend(propostas)
        if propostas:
            for p in propostas:
                print(f"  → {p['acao'].upper()}: {p['nome']}/{p['uf']} ({p['documento']})")
        else:
            print(f"  ✓ nenhuma diferença — base já reflete o repositório")

    if args.pistas:
        from scripts.pistas import gravar_lote
        from coletores_base import ler, gravar
        balanco = gravar_lote(pistas_das_propostas(todas_propostas, ref), origem="descoberta", ler_fn=ler, gravar_fn=gravar)
        print(f"\n[pistas] {balanco['gravadas']} gravada(s), {balanco['recusadas']} recusada(s): {balanco['motivos']}")
        return 1 if falhas else 0
    saida = DATA / "instrumentos_revisar.json"
    if todas_propostas:
        gravar_em(saida, todas_propostas)   # §229
        print(f"\n{len(todas_propostas)} proposta(s) salvas em {saida.relative_to(RAIZ)}")
        print("PRÓXIMO PASSO (manual, obrigatório):")
        print("  Revise o arquivo, apague o que não deve entrar, e então rode:")
        print(f"    python3 aplicar_revisao.py --arquivo {saida.relative_to(RAIZ)}")
    else:
        if saida.exists():
            saida.unlink()
        verificadas = [u for u in ufs if u not in falhas]
        print(f"\nNenhuma proposta pendente nas UFs efetivamente verificadas: {', '.join(verificadas) or 'nenhuma'}.")

    if falhas:
        # Falha de rede NÃO pode ser lida como 'nada mudou' — sai com código != 0
        # para que o pipeline registre que a verificação ficou incompleta.
        print(f"\n[ATENÇÃO] {len(falhas)} UF(s) NÃO puderam ser verificadas: {', '.join(falhas)}.")
        print("          Isto não significa 'sem novidades' — significa verificação incompleta.")
        return 1
    return 0


if __name__ == "__main__":
    if "--autoteste" in sys.argv or "--self-test" in sys.argv:
        sys.exit(autoteste())
    sys.exit(main() or 0)
