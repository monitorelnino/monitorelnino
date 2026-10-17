#!/usr/bin/env python3
"""Canal 2 do MARÉ Saúde: **baixar a edição** do diário oficial do estado, não buscar no sítio.

Diretriz da central, 02/10/2026. A sondagem de rotas de busca está encerrada, e o motivo é de
método: um diário oficial pode não ter busca e ainda assim publicar todas as suas edições em PDF,
por data. Quem tem a edição tem o texto; quem depende da busca do sítio depende de uma função que
dois terços dos estados não oferecem. Então o canal 2 passa a ser:

    padrão de endereço por data → baixa o PDF da edição → extrai o texto → indexa no nosso lado

e a campanha "imprensa → documento oficial" consome esse índice: a notícia cita a data, e o
localizador entrega a edição daquela data.

**O que este coletor faz e o que não faz.** Ele baixa edição por data, extrai o texto, guarda o
texto extraído e um resumo por edição em `data/doe_edicoes/<UF>.json`, e registra as ocorrências dos
termos de saúde em `data/doe_ocorrencias.json` — que é o índice que o juiz consome. Ele **não**
promove nada a registro: promoção é do `julgar_saude.py`, com documento primário lido, como sempre.

**Travas.** As três do projeto, mais a regra da recusa:
- o cliente é o do projeto, declarado, e o robots.txt é lido e respeitado com o rastro do §185;
- recusa de acesso real (401, 403, 429, 451), captcha e muro de robô servido com 200 **param** a UF
  e são gravados como `sem_acesso_automatico`, com o motivo técnico — lacuna declarada que **não
  conta como canal 2 consultado** no fechamento (A5-08, 10/10/2026; até 09/10 a regra da Paraíba
  contava essa rota como consultada);
- nada é escrito no banco (`BANCO_PROIBIDO`), e o autoteste offline confere isso lendo o próprio
  código-fonte.

**PDF sem texto.** Edição digitalizada como imagem sai como `sem_texto_extraivel`, com o número de
páginas e o tamanho — nunca como "edição sem o termo". A diferença entre "não achei" e "não pude
ler" é a primeira regra editorial do projeto.

Uso:
    python3 coletar_edicoes_doe.py --uf PB --desde 2026-06-29
    python3 coletar_edicoes_doe.py --uf MS --desde 2026-09-01 --ate 2026-09-30
    python3 coletar_edicoes_doe.py --recuperacao            # todas as UFs com padrão, desde 29/06
    python3 coletar_edicoes_doe.py --relatorio              # a tabela 27 × situação do canal 2
    python3 coletar_edicoes_doe.py --autoteste              # sem rede, sem escrita
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import pathlib
import re
import sys
import time

RAIZ = pathlib.Path(__file__).resolve().parent
PASTA = "doe_edicoes"
INDICE = "doe_ocorrencias.json"
INICIO_DO_CICLO = "2026-06-29"
# Em ordem de população (Censo 2022): a recuperação lê primeiro onde mora mais gente (handover §2).
UFS = "SP MG RJ BA PR RS PE CE PA SC GO MA AM ES PB MT RN AL PI DF MS SE RO TO AC AP RR".split()
# Teto por execução, para que uma recuperação não vire uma rodada de doze horas sem aviso.
TETO_EDICOES = 400
BANCO_PROIBIDO = {"estados.json", "saude_uf.json", "municipios.json", "indice.json",
                  "monitor_saude.json", "monitor_saude_v04.json"}

MESES = {1: "janeiro", 2: "fevereiro", 3: "março", 4: "abril", 5: "maio", 6: "junho",
         7: "julho", 8: "agosto", 9: "setembro", 10: "outubro", 11: "novembro", 12: "dezembro"}

# Os termos da saúde. Mesma lista do funil (coletar_saude_estadual), para que o índice do canal 2
# e a busca aberta do canal 1 procurem a MESMA coisa — dois vocabulários produziriam dois
# resultados sobre o mesmo estado.
TERMOS = ("grupo condutor", "sala de situação", "centro de operações", "COES", "COE estadual",
          "plano de contingência", "plano estadual de preparação", "emergência climática",
          "El Niño", "comitê intersetorial", "vigilância em saúde ambiental")
# Sigla curta exige CONTEXTO de saude na vizinhanca. MEDIDO em 02/10/2026 no diario da Paraiba:
# a extracao de texto perde a ligadura "CO" de "COES" dentro de palavras como "SOLUCOES" e
# "CONSTRUCOES", que saem partidas ("SOLU COES"), e ai a sigla vira palavra solta no meio de uma
# tabela de licitacao. Fronteira de palavra nao resolve; contexto resolve, e sem inventar nada:
# um centro de operacoes de emergencia em saude e citado ao lado de saude, emergencia ou situacao.
# Termo que serve a muitos assuntos exige CONTEXTO, pela mesma razão da sigla. MEDIDO em
# 02/10/2026 no diário do Mato Grosso do Sul: "Plano de Contingência do Sistema E-TFD" (um sistema
# de tratamento fora do domicílio) e "Comitê Intersetorial de Acompanhamento" de outro assunto
# entraram no índice como pista do ciclo. O índice é de PISTA, e pista que leva a um sistema de
# informática gasta a campanha. Termo específico — grupo condutor, sala de situação, plano estadual
# de preparação, emergência climática, El Niño — passa sem contexto, porque ele já é o contexto.
CONTEXTO_POR_TERMO = {
    "COES": r"(sa[úu]de|emerg[êe]ncia|situa[çc][ãa]o|epidemi|vigil[âa]ncia)",
    "COE estadual": r"(sa[úu]de|emerg[êe]ncia|situa[çc][ãa]o)",
    "centro de operações": r"(sa[úu]de|emerg[êe]ncia|clim|desastre)",
    "plano de contingência": r"(El\s*Ni[ñn]o|clim|estiagem|seca|chuva|arbovir|dengue|calor|desastre|sa[úu]de p[úu]blica)",
    "comitê intersetorial": r"(El\s*Ni[ñn]o|clim|estiagem|seca|chuva|desastre|emerg[êe]ncia)",
    "vigilância em saúde ambiental": r"(El\s*Ni[ñn]o|clim|estiagem|seca|chuva|calor|desastre)",
}
# 17/10/2026 (HANDOVER_RESPOSTA_SANITARIA §1.3): DECLARAÇÃO de emergência em saúde pública por
# decreto do governador. Expressão com "saúde" exige "declar" em volta (o COE "de Emergência em Saúde
# Pública" é citado sem declarar nada); a com "declara" exige saúde em volta (a seca também se declara).
TERMOS_DE_DECLARACAO = {"situação de emergência em saúde pública": r"declar",
                        "emergência em saúde pública": r"declar",
                        "estado de emergência em saúde": r"declar",
                        "declara situação de emergência": r"(sa[úu]de|epidemi|dengue|arbovir)"}
CONTEXTO_POR_TERMO.update(TERMOS_DE_DECLARACAO)
TERMOS = TERMOS + tuple(TERMOS_DE_DECLARACAO)
# Edição lida com vocabulário anterior a esta data não procurou declaração: é relida.
VERSAO_DOS_TERMOS = "2026-10-17"
CONTEXTO_DE_SIGLA = {t: re.compile(r, re.I) for t, r in CONTEXTO_POR_TERMO.items()}
JANELA_DE_CONTEXTO = 300

# ── Padrões de endereço por data ───────────────────────────────────────────────────────────────
# Cada padrão foi CONFERIDO contra uma edição real antes de entrar aqui; a conferência está na
# nota de cada um. Padrão que depende do NÚMERO da edição (e não da data) leva a listagem junto. O AP
# (edição por id, medido em 02/10/2026) sai pela busca da plataforma comum, declarada no fontes_doe.
PADROES = {
    # Conferido pela central: abre sem bloqueio.
    "PB": {"padrao": "https://auniao.pb.gov.br/servicos/doe/{ano}/{mes_nome}/diario-oficial-{dd}-{mm}-{ano}-portal.pdf",
           "nota": "padrão por data, conferido pela central em 02/10/2026"},
    # Conferido pela central na edição 12.270, de 03/09/2026. O número da edição entra pela
    # listagem; o padrão por data cobre o caso em que o nome do arquivo dispensa o número.
    # MEDIDO em 02/10/2026: o arquivo do MS é nomeado pelo NÚMERO da edição, e o endereço por data
    # sozinho dá 404. O número vem da listagem quando ela o traz, e das âncoras quando não: duas
    # edições conferidas, estimativa por dia útil e uma janela de tentativas. O nome do arquivo
    # carrega a data, então número errado dá 404 — quem confirma é a fonte, não a estimativa.
    "MS": {"padrao": "https://assets.imprensaoficial.ms.gov.br/public/prd/Diario%20Oficial/{ano}/{mm}/{dd}/DO{edicao}_{dd}_{mm}_{ano}.pdf",
           "listagem": "https://www.spdo.ms.gov.br/diariodoe/",
           "ancoras": {"2026-09-03": 12270, "2026-10-02": 12293},
           "janela": 12,
           "nota": "nome do arquivo pelo número da edição; âncoras conferidas em 02/10/2026"},
    # 17/10/2026 (janela A3, run 39019929474): a edição de 10/09/2026 abre por data, 209 páginas com texto.
    "PA": {"padrao": "https://www.ioepa.com.br/pages/{ano}/{ano}.{mm}.{dd}.DOE.pdf",
           "nota": "padrão por data, medido do runner em 17/10/2026"},
    # 17/10/2026 (run 39022687465): 01/07 (399 p.) e 10/09/2026 (488 p.) abrem por data, com texto. A
    # página inicial lista também DOE-EXTRAORDINARIO-<data> e <data>-SUPLEMENTAR-<n>, fora do padrão.
    "RO": {"padrao": "https://diof.ro.gov.br/data/uploads/{ano}/{mm}/DOE-{dd}-{mm}-{ano}.pdf",
           "nota": "padrão por data da edição ordinária, medido do runner em 17/10/2026"},
    # 17/10/2026 (runs 39023131710 e 39023721853): 01/07 (52 p.) e 10/09/2026 (43 p.) abrem por data, com
    # texto. A edição extra sai como <data>E.pdf, fora do padrão.
    "RN": {"padrao": "https://webdisk.diariooficial.rn.gov.br/Jornal/1{ano}-{mm}-{dd}.pdf",
           "nota": "padrão por data da edição ordinária, medido do runner em 17/10/2026"},
    # 17/10/2026 (run 39024168986): 10/09/2026 abre por data (170 p., texto); a listagem do mês
    # (_visualizar-mes) nomeia toda edição do mesmo jeito (doe-AAAAMMDD.pdf).
    "RR": {"padrao": "https://www.imprensaoficial.rr.gov.br/_edicoes/{ano}/{mm}/doe-{ano}{mm}{dd}.pdf",
           "nota": "padrão por data, medido do runner em 17/10/2026"},
}


def datas_do_periodo(desde: str, ate: str) -> list:
    """As datas do período, inclusive, sem fim de semana. Função pura.

    Diário oficial de estado não publica sábado e domingo como regra; incluir os dois dobraria as
    tentativas e encheria o log de 404 que não são ausência de edição, e sim ausência de dia útil.
    Edição extra de fim de semana existe, e aparece pela listagem — não por tentativa cega.
    """
    a = dt.date.fromisoformat(desde)
    b = dt.date.fromisoformat(ate)
    fora, d = [], a
    while d <= b:
        if d.weekday() < 5:
            fora.append(d.isoformat())
        d += dt.timedelta(days=1)
    return fora


def endereco_da_data(padrao: str, data: str, edicao: str = None) -> str:
    """Preenche o padrão com a data. Função pura."""
    d = dt.date.fromisoformat(data)
    return padrao.format(ano=d.year, mm=f"{d.month:02d}", dd=f"{d.day:02d}",
                         mes_nome=MESES[d.month], edicao=edicao or "")


def edicoes_da_listagem(html: str) -> dict:
    """{data ISO: numero da edicao} lidos da listagem. Funcao pura.

    O proprio nome do arquivo na listagem carrega numero E data (DO12270_03_09_2026), e e dai que
    o par sai — nao de posicao na tabela, que muda com o tema do portal.
    """
    fora = {}
    for num, dd, mm, aaaa in re.findall(r"DO(\d{4,6})_(\d{2})_(\d{2})_(\d{4})", html or ""):
        fora[f"{aaaa}-{mm}-{dd}"] = int(num)
    return fora


def estimar_edicao(data: str, ancoras: dict) -> int:
    """O número provável da edição naquela data, por dia útil desde a âncora mais PRÓXIMA.

    Função pura. Devolve `None` sem âncoras. A estimativa não é a resposta: ela é o centro da
    janela de tentativas, e a fonte confirma ou nega pelo nome do arquivo, que carrega a data.

    A âncora mais próxima importa porque o erro cresce com a distância: edição extra e feriado
    deslocam a numeração, e contar dia útil desde setembro para estimar junho acumula o deslocamento
    de três meses. Com a âncora vizinha, a janela fecha em uma ou duas tentativas.
    """
    if not ancoras:
        return None
    alvo = dt.date.fromisoformat(data)
    base_data, base_num = min(ancoras.items(),
                              key=lambda kv: abs((dt.date.fromisoformat(kv[0]) - alvo).days))
    base = dt.date.fromisoformat(base_data)
    passo = 1 if alvo >= base else -1
    dias, d = 0, base
    while d != alvo:
        d += dt.timedelta(days=passo)
        if d.weekday() < 5:
            dias += passo
    return base_num + dias


def numeros_a_tentar(data: str, listagem: dict, ancoras: dict, janela: int = 8) -> list:
    """Os numeros de edicao a tentar para a data, em ordem de probabilidade. Funcao pura.

    A listagem, quando tem a data, e a resposta — uma tentativa. Sem ela, a estimativa no centro e
    a janela em volta, alternando para os dois lados (feriado atrasa a numeracao; edicao extra a
    adianta).
    """
    if listagem and data in listagem:
        return [listagem[data]]
    centro = estimar_edicao(data, ancoras)
    if centro is None:
        return []
    fora = [centro]
    for i in range(1, janela + 1):
        fora += [centro - i, centro + i]
    return fora


def ocorrencias_no_texto(texto: str, termos=TERMOS) -> list:
    """Os termos achados, com o trecho em volta. Função pura.

    Guarda o trecho porque classificação sem trecho não se confere sem reabrir o PDF — e reabrir
    um diário de 80 páginas para checar uma linha é o atrito que faz ninguém checar.
    """
    t = re.sub(r"\s+", " ", texto or "")
    fora = []
    for termo in termos:
        # Sigla curta (COES, COE) casa em QUALQUER lugar sem fronteira: na primeira execução ela
        # apareceu dentro de tabelas de licitação ("PAULO CESA L R T D D A E"), e tabela de pregão
        # não é sala de situação. Sigla exige fronteira de palavra e caixa alta; termo em palavras
        # segue sem distinção de caixa.
        if termo.isupper() or (len(termo) <= 12 and termo.upper() == termo):
            padrao, bandeiras = r"\b" + re.escape(termo) + r"\b", 0
        else:
            padrao, bandeiras = re.escape(termo), re.I
        contexto = CONTEXTO_DE_SIGLA.get(termo)
        for m in re.finditer(padrao, t, bandeiras):
            ini = max(0, m.start() - 160)
            if contexto is not None:
                perto = t[max(0, m.start() - JANELA_DE_CONTEXTO):m.end() + JANELA_DE_CONTEXTO]
                if not contexto.search(perto):
                    continue
            fora.append({"termo": termo, "trecho": t[ini:m.end() + 220].strip(),
                         **({"classe": "declaracao"} if termo in TERMOS_DE_DECLARACAO else {})})
            break   # um trecho por termo por edição: o que importa é a edição ter o termo
    return fora


def pagina_do_trecho(paginas: list, trecho: str) -> int:
    """Em que página o trecho está (1-based), ou `None`. Função pura.

    A página é exigência editorial da citação: "DOE-PB de 09/09/2026, pp. 9–10" é prova; "DOE-PB de
    09/09/2026" é indicação.
    """
    chave = re.sub(r"\s+", " ", (trecho or ""))[:60].strip().lower()
    if not chave:
        return None
    for i, p in enumerate(paginas or [], start=1):
        if chave in re.sub(r"\s+", " ", p or "").lower():
            return i
    return None


# Uma edição de diário estadual tem dezenas de páginas e centenas de quilobytes. MEDIDO em
# 02/10/2026 no Amapá: o endereço por data respondia 200 em TODAS as 70 datas, sempre com o MESMO
# arquivo de 2.016 bytes e uma página — uma página de erro servida como PDF. Sem esta régua, o
# localizador registrava 70 "edições lidas" e 0 com o termo, e isso viraria "consultado sem achado"
# em 70 datas: prova falsa, do pior tipo, porque parece trabalho feito.
MINIMO_BYTES_DE_EDICAO = 20_000
MINIMO_PAGINAS_DE_EDICAO = 2


def decidir_edicao(status: int, bytes_lidos: int, paginas_com_texto: int,
                   paginas: int = None, repetido: bool = False) -> str:
    """O vocabulário fechado do canal 2 para uma edição. Função pura.

    `sem_texto_extraivel` existe para a edição digitalizada como imagem: ela não é "edição sem o
    termo". `nao_e_edicao` existe para o arquivo servido com 200 que não é um diário — tamanho de
    página de erro, uma página só, ou o mesmo arquivo repetido em várias datas. Chamar qualquer um
    desses de "lida" produziria "consultado sem achado" sem nada consultado.
    """
    if status == 404:
        return "sem_edicao_na_data"
    if status and status >= 400:
        return "recusa"
    if not bytes_lidos:
        return "vazio"
    if repetido:
        return "nao_e_edicao"
    if bytes_lidos < MINIMO_BYTES_DE_EDICAO:
        return "nao_e_edicao"
    if paginas is not None and paginas < MINIMO_PAGINAS_DE_EDICAO:
        return "nao_e_edicao"
    if paginas_com_texto == 0:
        return "sem_texto_extraivel"
    return "lida"


# Recusa REAL da fonte (muro de robô, 401/403/429/451, captcha, login): lacuna declarada com o motivo
# medido, que NÃO conta como canal consultado (A5-08, 10/10/2026), e que nunca se contorna.
MODO_SEM_ACESSO = "sem_acesso_automatico"
# 17/10/2026 (HANDOVER_ROTAS_DOE §0.1): 404 e endereço que não abre são palpite ERRADO de endereço, não
# recusa. Até aqui viravam `sem_acesso_automatico`, e 17 diários sem recusa nenhuma pareciam fechados.
MODO_SEM_ROTA = "rota_nao_descoberta"
RECUSAS_HTTP = (401, 403, 429, 451)
# Busca que só lê a primeira página: página cheia é resultado que pode continuar (AC, 10 por página).
PAGINA_CHEIA = {"busca_ac": 10}
# §11: ritmo de 2 s entre pedidos ao mesmo diário (o `Crawl-delay` do robots, quando há, é da base).
RITMO_S = 2.0
GOVERNANCA_CANAL2 = ("Canal 2 desta unidade. Rota de edição não achada é `rota_nao_descoberta` (palpite "
                     "de endereço errado, a descobrir); só recusa real da fonte (401, 403, 429, 451, muro "
                     "de robô) é `sem_acesso_automatico`. As duas são lacuna declarada, que não conta como "
                     "consultado (A5-08, 10/10/2026; 17/10/2026).")


def rota_da_uf(uf: str, adaptadores=None, padroes=None) -> dict:
    """De onde sai a edição da UF. Função pura. Três rotas, na ordem em que valem: o padrão de
    endereço deste arquivo; o adaptador de edição por data do `coletar_doe` (`edicao_<uf>`); a busca
    do diário (`apifront`, `dodf`, `busca_<uf>`), que procura os termos de declaração. Os adaptadores
    vêm do `fontes_doe.json`, onde cada um foi medido; não se copiam para cá."""
    p = (padroes if padroes is not None else PADROES).get(uf) or {}
    cfg = (adaptadores or {}).get(uf) or {}
    ad = cfg.get("adaptador")
    if p.get("padrao"):
        return {"tipo": "padrao", "detalhe": p["padrao"]}
    if ad:
        return {"tipo": "edicao" if ad.startswith("edicao_") else "busca", "adaptador": ad,
                "url": cfg.get("url"), "detalhe": f"adaptador {ad}"}
    return {"tipo": None}


def situacao_do_canal2(uf: str, padroes=None, adaptadores=None, registro=None) -> dict:
    """Como o canal 2 é feito nesta UF. Função pura.

    `sem_acesso_automatico` (recusa real registrada) vale primeiro; depois a rota da UF —
    `padrao_por_data` (padrão de endereço ou adaptador de edição por data) ou `busca_no_diario`.
    Sem nenhuma, `rota_nao_descoberta`: ausência de **rota**, não de diário, e não recusa.
    """
    reg = (registro or {}).get("canal2") or {}
    if reg.get("modo") == MODO_SEM_ACESSO and reg.get("motivo"):
        return {"uf": uf, "modo": MODO_SEM_ACESSO, "detalhe": reg["motivo"],
                "nota": "recusa da fonte — lacuna declarada, não conta como canal consultado"}
    # O registro da UF guarda o adaptador com que foi lido: a situação se responde sem o fontes_doe.
    rota = rota_da_uf(uf, adaptadores or {uf: {"adaptador": reg.get("adaptador")}}, padroes)
    if rota["tipo"]:
        return {"uf": uf, "modo": "busca_no_diario" if rota["tipo"] == "busca" else "padrao_por_data",
                "detalhe": rota["detalhe"]}
    return {"uf": uf, "modo": MODO_SEM_ROTA,
            "detalhe": reg.get("motivo") or "sem rota de edição conferida para esta UF",
            "nota": "palpite de endereço errado não é recusa: a rota segue a descobrir"}


def a_reler(item) -> bool:
    """Edição lida antes dos termos de declaração tem de ser relida. Função pura."""
    return isinstance(item, dict) and item.get("decisao") == "lida" and item.get("termos_versao") != VERSAO_DOS_TERMOS


def datas_sem_cobertura(edicoes: dict, ate: str) -> list:
    """Datas úteis de 29/06 até `ate` (e cadernos `data#n`) sem edição lida com os termos de hoje nem
    ausência de edição medida. Função pura. Data não tentada, edição que não é edição, sem texto ou
    recusada: tudo isso é falta de cobertura, nunca "consultado"."""
    def coberta(e):
        return isinstance(e, dict) and e.get("decisao") in ("lida", "sem_edicao_na_data") and not a_reler(e)
    return ([d for d in datas_do_periodo(INICIO_DO_CICLO, ate) if not coberta(edicoes.get(d))]
            + sorted(k for k, e in edicoes.items() if "#" in k and k <= ate + "~" and not coberta(e)))


def busca_de_declaracao(uf: str, registro: dict) -> dict:
    """A metade estadual da resposta sanitária nesta UF: `consultado_em` só quando o ciclo foi lido
    com os termos de declaração — edição por edição, ou pela busca do diário desde o início do ciclo;
    senão `lacuna`, com o motivo que distingue recusa de rota não descoberta. Função pura."""
    sit = situacao_do_canal2(uf, registro=registro)
    if sit["modo"] == MODO_SEM_ACESSO:
        return {"lacuna": f"recusa da fonte, respeitada: {sit['detalhe']}"}
    if sit["modo"] == MODO_SEM_ROTA:
        return {"lacuna": f"rota do diário não descoberta (nenhuma recusa medida): {sit['detalhe']}"}
    if sit["modo"] == "busca_no_diario":
        b = (registro.get("canal2") or {}).get("busca_declaracao") or {}
        fresca = b.get("consultado_em") and (b.get("ate") or "") >= "-".join(reversed(b["consultado_em"].split("/")))
        if fresca and b.get("termos_versao") == VERSAO_DOS_TERMOS and (b.get("desde") or "~") <= INICIO_DO_CICLO:
            return {"consultado_em": b["consultado_em"], "via": f"busca do diário ({sit['detalhe']})"}
        return {"lacuna": b.get("lacuna") or "a busca do diário ainda não rodou com os termos de declaração desde o início do ciclo"}
    edicoes = registro.get("edicoes") or {}
    em = registro.get("atualizado_em")
    lidas = sum(1 for e in edicoes.values() if isinstance(e, dict) and e.get("decisao") == "lida")
    if not em or not lidas:
        return {"lacuna": f"nenhuma edição lida por data ({sit['modo']})"}
    # Cobertura, não contagem (auditoria de 17/10): toda data útil do ciclo até a véspera da última
    # leitura tem de ter a edição lida com os termos de hoje, ou a ausência de edição medida (404).
    ate = (dt.datetime.strptime(em, "%d/%m/%Y").date() - dt.timedelta(days=1)).isoformat()
    faltam = datas_sem_cobertura(edicoes, ate)
    if faltam:
        return {"lacuna": f"{len(faltam)} data(s) útil(eis) do ciclo sem edição lida com os termos de declaração "
                          f"(a primeira: {faltam[0]})"}
    return {"consultado_em": em, "edicoes_lidas": lidas, "ate": ate}


# ── execução ───────────────────────────────────────────────────────────────────────────────────
def _texto_paginas(bruto: bytes) -> list:
    """Texto por página, pela porta canônica do projeto (pypdf, pdfplumber de reserva). 17/10/2026: a
    ordem inversa (pdfplumber primeiro) era cópia da porta, e o pdfplumber, o mais lento dos dois,
    lendo toda página das edições de 200 a 500 páginas (PA, RO) não cabe no prazo do elo."""
    try:
        from preservar_evidencias import extrair_texto_por_pagina
        return extrair_texto_por_pagina(bruto)
    except Exception:  # noqa: BLE001
        return []


def _recusa(e, url: str):
    """O motivo, se a exceção é recusa real da fonte (muro, 401/403/429/451); senão None. Pura."""
    if type(e).__name__ == "MuroDeRobo":
        return f"muro de robô em {url[:90]}: {str(e)[:120]}"
    codigo = getattr(e, "code", None) or 0
    return f"HTTP {codigo} em {url[:90]} — recusa respeitada" if codigo in RECUSAS_HTTP else None


def _pela_busca(uf: str, rota: dict, desde: str, ate: str, ocorrencias: dict, hoje: str,
                busca_fn=None, preservar_fn=None) -> tuple:
    """A busca do diário com os termos de DECLARAÇÃO (17/10/2026, HANDOVER_ROTAS_DOE §0.2), pela porta
    única do `coletar_doe` (`itens_da_busca`). Acerto que passa o contexto entra no índice, e o juiz
    abre o documento como abre a edição. Devolve (resumo da busca, recusa ou None)."""
    if busca_fn is None:
        import coletar_doe
        busca_fn = coletar_doe.itens_da_busca
    if preservar_fn is None:
        from coletores_base import preservar_evidencia as preservar_fn
    # A busca indexa palavra, não contexto: perguntam-se as expressões com "saúde" (as outras casariam
    # todo decreto de seca); o contexto de "declar" se confere no trecho, como na edição inteira.
    termos = [t for t in TERMOS_DE_DECLARACAO if "saúde" in t and not any(u != t and u in t for u in TERMOS_DE_DECLARACAO)]
    # Um termo por vez, para conferir o lido contra o que a fonte declara: busca que para no teto de
    # páginas ou de edições, ou edição que não baixou, é busca TRUNCADA — lacuna, nunca "consultado".
    itens, totais, truncada = [], {}, []
    for termo in termos:
        try:
            achados_t, tot = busca_fn(uf, rota["adaptador"], rota["url"], desde, ate, termos=[termo])
        except Exception as e:  # noqa: BLE001
            recusa = _recusa(e, rota.get("url") or "")
            return {"lacuna": f"busca do diário falhou em {hoje}: {type(e).__name__}: {str(e)[:120]}"}, recusa
        declarado = int((tot or {}).get(termo) or 0)
        # TO e AC apontam EDIÇÕES (uma linha por página achada); as outras buscas, acertos.
        lido = len({x.get("url") for x in achados_t}) if rota["adaptador"].startswith("busca_") and rota["adaptador"] != "busca_sp" else len(achados_t)
        if lido < declarado or declarado >= PAGINA_CHEIA.get(rota["adaptador"], 10 ** 9):
            truncada.append(f"{termo}: lidos {lido} de {declarado}")
        itens += achados_t
        totais[termo] = declarado
    declaracoes = 0
    for it in itens:
        achados = ocorrencias_no_texto(" ".join(it.get("trechos") or []), tuple(TERMOS_DE_DECLARACAO))
        if not achados:
            continue
        for a in achados:
            a["pagina"] = it.get("pagina")
        corpo = json.dumps(it, ensure_ascii=False).encode("utf-8")
        chave = it.get("data") or hoje
        while chave in ocorrencias and ocorrencias[chave].get("url") != it.get("url"):
            chave = chave.split("#")[0] + f"#{int((chave.split('#') + ['1'])[1]) + 1}"
        ocorrencias[chave] = {"url": it.get("url"), "via": f"busca {rota['adaptador']}",
                              "hash_evidencia": preservar_fn(corpo, it.get("url") or "", "json", "coletar_edicoes_doe"),
                              "paginas": it.get("paginas"), "achados": achados}
        declaracoes += 1
    if truncada:
        return {"lacuna": f"busca do diário truncada em {hoje} ({'; '.join(truncada)})", "com_declaracao": declaracoes}, None
    return {"consultado_em": hoje, "desde": desde, "ate": ate, "termos": termos,
            "termos_versao": VERSAO_DOS_TERMOS, "acertos": len(itens), "com_declaracao": declaracoes,
            "totais_por_termo": totais}, None


def _edicoes_da_data(rota: dict, padrao: dict, data: str, listagem: dict, ancoras: dict, edicoes_fn) -> list:
    """As edições da data, cada uma como a lista de endereços alternativos a tentar (o primeiro que
    abre vale). Padrão por número tenta a janela de números; adaptador devolve uma por caderno."""
    if rota["tipo"] == "edicao":
        return [[e] for e in edicoes_fn(data)]
    if "{edicao}" in padrao["padrao"]:
        numeros = numeros_a_tentar(data, listagem, ancoras, padrao.get("janela", 8))
        return [[{"url": endereco_da_data(padrao["padrao"], data, str(n))} for n in numeros]] if numeros else []
    return [[{"url": endereco_da_data(padrao["padrao"], data)}]]


def coletar_uf(uf: str, desde: str, ate: str) -> dict:
    """Baixa, lê e indexa as edições de uma UF no período (ou pergunta à busca do diário). Devolve o resumo."""
    from coletores_base import buscar, gravar, hoje_editorial, ler, log_busca, preservar_evidencia, registrar_lacuna

    arquivo = f"{PASTA}/{uf}.json"
    registro = ler(arquivo, {}) or {}
    rota = rota_da_uf(uf, (ler("fontes_doe.json", {}) or {}).get("ufs"))
    if not rota["tipo"]:
        s = situacao_do_canal2(uf, registro=registro)
        registrar_lacuna(f"DOE-{uf} (canal 2)", f"{s['modo']}: {s['detalhe'][:90]}", canal="DOE", camada=1)
        print(f"  {uf}: {s['modo']} — {s['detalhe']}")
        return {"uf": uf, "modo": s["modo"], "lidas": 0, "decisao": "sem_rota"}

    (RAIZ / "data" / PASTA).mkdir(parents=True, exist_ok=True)
    registro.setdefault("_governanca", (
        "Edições do diário oficial deste estado baixadas por DATA (canal 2 do MARÉ Saúde, diretriz "
        "de 02/10/2026). Guarda-se o resumo de cada edição e as ocorrências dos termos de saúde, "
        "com o trecho e a página; o PDF vive em evidencias/, pelo hash. Edição digitalizada como "
        "imagem sai como 'sem_texto_extraivel', que NÃO é 'edição sem o termo'."))
    edicoes = registro.setdefault("edicoes", {})

    indice = ler(INDICE, {}) or {}
    indice.setdefault("_governanca", (
        "Índice de ocorrências dos termos de saúde nas edições dos diários oficiais estaduais, "
        "produzido pelo canal 2. É o que a campanha 'imprensa → documento oficial' consome: a "
        "notícia cita a data, e o índice entrega a edição daquela data. Não promove nada a "
        "registro — promoção é do juiz, com documento primário lido."))
    ocorrencias = indice.setdefault("ufs", {}).setdefault(uf, {})
    hoje = hoje_editorial().strftime("%d/%m/%Y")
    lidas = com_termo = 0
    recusa, interrompido = None, False

    if rota["tipo"] == "busca":
        busca, recusa = _pela_busca(uf, rota, desde, ate, ocorrencias, hoje)
        com_termo = busca.get("com_declaracao", 0)
        anterior = (registro.get("canal2") or {}).get("busca_declaracao") or {}
        if "consultado_em" not in busca:
            registrar_lacuna(f"DOE-{uf} (canal 2)", busca["lacuna"][:160], canal="DOE", camada=1)
            if "consultado_em" in anterior:   # a leitura completa anterior segue datada; a falha fica ao lado
                busca = dict(anterior, ultima_falha=busca["lacuna"])
        if not recusa:
            registro["canal2"] = {"modo": "busca_no_diario", "adaptador": rota["adaptador"], "em": hoje,
                                  "conta_como_consultado": "consultado_em" in busca, "busca_declaracao": busca}
        print(f"  {uf}: busca {rota['adaptador']} — " + (f"{busca['acertos']} acerto(s), {com_termo} com declaração"
                                                          if "consultado_em" in busca else busca["lacuna"]))
    else:
        padrao = PADROES.get(uf) or {}
        edicoes_fn = None
        if rota["tipo"] == "edicao":
            import coletar_doe
            edicoes_fn = coletar_doe.EDICOES_POR_DATA[rota["adaptador"]](buscar, rota["url"])
        # Quando o nome do arquivo pede o NÚMERO da edição, lê-se a listagem uma vez (ela cobre as
        # últimas) e o resto sai das âncoras, com a fonte confirmando pelo nome do arquivo.
        listagem = {}
        if "{edicao}" in padrao.get("padrao", "") and padrao.get("listagem"):
            try:
                listagem = edicoes_da_listagem(buscar(padrao["listagem"], timeout=60).decode("utf-8", "replace"))
                print(f"  {uf}: listagem com {len(listagem)} edição(ões) datadas")
            except Exception as e:  # noqa: BLE001
                print(f"  {uf}: listagem não lida ({type(e).__name__}) — segue pelas âncoras")
        # As âncoras começam nas conferidas e crescem a cada acerto: a data seguinte estima a partir da
        # vizinha, e não a partir de setembro.
        ancoras_vivas = dict(padrao.get("ancoras") or {})
        for data_lida, item in (edicoes or {}).items():
            achado = re.search(r"DO(\d{4,6})_", str((item or {}).get("url") or ""))
            if achado and (item or {}).get("decisao") == "lida":
                ancoras_vivas[data_lida] = int(achado.group(1))
        # Data recente "sem edição" se tenta de novo: a edição do dia pode sair depois da leitura.
        recente = (dt.date.fromisoformat(ate) - dt.timedelta(days=3)).isoformat()
        datas = [d for d in datas_do_periodo(desde, ate) if d not in edicoes or a_reler(edicoes[d])
                 or (d >= recente and edicoes[d].get("decisao") == "sem_edicao_na_data")][:TETO_EDICOES]
        # Quando o nome do arquivo pede o NÚMERO da edição, percorre-se do mais novo para o mais velho:
        # a âncora de cada data passa a ser a vizinha, e a deriva por passo é de uma ou duas edições.
        # Da outra ordem, a janela de oito não alcançava dois meses de deriva e tudo dava 404.
        if "{edicao}" in padrao.get("padrao", ""):
            datas = sorted(datas, reverse=True)
        vistos = {e.get("impressao") for d, e in edicoes.items()
                  if isinstance(e, dict) and e.get("impressao") and d.split("#")[0] not in datas}
        try:
            for data in datas:
                try:
                    grupos = _edicoes_da_data(rota, padrao, data, listagem, ancoras_vivas, edicoes_fn)
                except Exception as e:  # noqa: BLE001
                    recusa = _recusa(e, rota.get("url") or "")
                    if recusa:
                        break
                    edicoes[data] = {"decisao": "vazio", "em": hoje, "motivo": f"listagem da data: {type(e).__name__}: {str(e)[:90]}"}
                    continue
                if not grupos:
                    edicoes[data] = ({"decisao": "sem_numero_de_edicao", "em": hoje,
                                      "motivo": "o padrão pede o número da edição e não há âncora nem listagem"}
                                     if rota["tipo"] == "padrao" else {"decisao": "sem_edicao_na_data", "em": hoje})
                    continue
                # Edição em vários cadernos (CE) ou com suplemento: um registro por caderno, a data na chave.
                for k, alternativas in enumerate(grupos, start=1):
                    chave = data if k == 1 else f"{data}#{k}"
                    url, bruto, status, erro = alternativas[0]["url"], None, 0, None
                    for candidato in alternativas:
                        url = candidato["url"]
                        time.sleep(0 if candidato.get("pdf") else RITMO_S)
                        try:
                            bruto = candidato.get("pdf") or buscar(url, timeout=120)
                            status = 200
                            break
                        except Exception as e:  # noqa: BLE001
                            recusa = _recusa(e, url)
                            if recusa:
                                break
                            erro, status = e, getattr(e, "code", None) or 0
                    if recusa:
                        break
                    if bruto is None:
                        edicoes[chave] = {"decisao": decidir_edicao(status, 0, 0), "em": hoje,
                                          "motivo": f"{type(erro).__name__}: {str(erro)[:90]}"}
                        continue
                    # Repetição pelo hash do conteúdo: o mesmo arquivo em duas datas não são duas edições.
                    impressao = hashlib.sha256(bruto).hexdigest()
                    repetido = impressao in vistos
                    vistos.add(impressao)
                    paginas = [] if repetido else _texto_paginas(bruto)
                    com_texto = sum(1 for x in paginas if (x or "").strip())
                    decisao = decidir_edicao(status, len(bruto), com_texto, len(paginas) or None, repetido)
                    item = {"decisao": decisao, "em": hoje, "bytes": len(bruto), "paginas": len(paginas),
                            "paginas_com_texto": com_texto, "url": url, "impressao": impressao,
                            "termos_versao": VERSAO_DOS_TERMOS}
                    if decisao == "nao_e_edicao":
                        item["motivo"] = ("mesmo arquivo de outra data" if repetido else
                                          f"{len(bruto)} bytes e {len(paginas)} página(s) — não é uma edição")
                    if decisao == "sem_texto_extraivel":
                        # PDF digitalizado vai à fila de OCR que já existe (`preservar_evidencias.alvos_ocr`
                        # pega PDF preservado sem camada de texto). A cópia por OCR é PROVA (§177), não
                        # insumo de classificação: a edição segue "não lida" até a fonte servir texto.
                        item["hash_evidencia"] = preservar_evidencia(bruto, url, "pdf", "coletar_edicoes_doe")
                    if decisao == "lida":
                        achados = ocorrencias_no_texto("\n".join(paginas))
                        if achados:
                            item["hash_evidencia"] = preservar_evidencia(bruto, url, "pdf", "coletar_edicoes_doe")
                            for a in achados:
                                a["pagina"] = pagina_do_trecho(paginas, a["trecho"])
                            ocorrencias[chave] = {"url": url, "hash_evidencia": item["hash_evidencia"],
                                                  "paginas": len(paginas), "achados": achados}
                            com_termo += 1
                        item["termos_achados"] = [a["termo"] for a in achados]
                        lidas += 1
                    edicoes[chave] = item
                    achado = re.search(r"DO(\d{4,6})_", url or "")
                    if achado and decisao == "lida":
                        ancoras_vivas[data] = int(achado.group(1))
                if recusa:
                    break
        except KeyboardInterrupt:
            # O prazo do elo interrompe com SIGINT (saude_pipeline): grava-se o que já foi lido, e para.
            print(f"  {uf}: interrompido pelo prazo do elo — grava o lido até aqui")
            interrompido = True
        if not recusa:
            registro["canal2"] = {"modo": "padrao_por_data", "em": hoje, "conta_como_consultado": True,
                                  **({"adaptador": rota["adaptador"]} if rota["tipo"] == "edicao" else {})}

    if recusa:
        registro["canal2"] = {"modo": MODO_SEM_ACESSO, "motivo": recusa, "em": hoje, "conta_como_consultado": False}
        registrar_lacuna(f"DOE-{uf} (canal 2)", recusa, canal="DOE", camada=1)
        print(f"  {uf}: {recusa} — canal 2 sem acesso automático, lacuna declarada (não conta como consultado)")
    if lidas:
        # 14/10/2026 (ciclo de 15 dias): o diário da UF foi LIDO, edição por edição — é verificação
        # real por DOE, e o livro de fontes a registra como o canal 1 já registra (`DOE/<UF>`).
        from coletores_base import marcar_fonte_consultada, referencia_ibge
        por_cod, _ = referencia_ibge()
        marcar_fonte_consultada([c for c, r in por_cod.items() if r["uf"] == uf], f"DOE/{uf}", "estadual",
                                resultado=f"{lidas} edição(ões) lida(s) por data (canal 2)")
    registro["atualizado_em"] = hoje
    gravar(arquivo, registro)
    indice["atualizado_em"] = hoje
    gravar(INDICE, indice)
    log_busca("DOE", 1, [rota["detalhe"]], "registro" if com_termo else "consultado sem achado",
              nivel="estadual", uf=uf, n_resultados=com_termo,
              resultados=f"canal 2 em {uf} ({rota['tipo']}): {lidas} edição(ões) lida(s), {com_termo} com termo de saúde")
    print(f"  {uf}: {lidas} edição(ões) lida(s), {com_termo} com termo de saúde")
    if interrompido:
        raise KeyboardInterrupt
    return {"uf": uf, "modo": registro["canal2"]["modo"], "lidas": lidas, "com_termo": com_termo,
            "decisao": "registro" if com_termo else "consultado sem achado"}


# Padroes de endereco que as plataformas de diario costumam usar, para a PRIMEIRA tentativa. Cada
# um e um palpite de ENGENHARIA, nao um dado: ele e confirmado pela propria fonte, porque o nome do
# arquivo carrega a data e numero errado da 404.
MOLDES_CONHECIDOS = (
    "{base}/portal/download/{ano}/{mm}/{dd}.pdf",
    "{base}/arquivos/{ano}/{mm}/{dd}.pdf",
    "{base}/diario/{ano}{mm}{dd}.pdf",
    "{base}/edicoes/{ano}-{mm}-{dd}.pdf",
    "{base}/doe/{ano}/{mm}/doe-{dd}-{mm}-{ano}.pdf",
)
TENTATIVAS_POR_UF = 2


def moldes_para(base: str) -> list:
    """Os moldes de endereco a tentar para esta base. Funcao pura."""
    base = (base or "").rstrip("/")
    return [m.format(base=base, ano="{ano}", mm="{mm}", dd="{dd}") for m in MOLDES_CONHECIDOS]


def veredito_da_descoberta(achou_padrao: bool, achou_listagem: bool, motivo: str, recusa: bool = False) -> dict:
    """O que registrar depois das duas tentativas. Funcao pura.

    Sem padrao e sem listagem legivel, o canal 2 fica `rota_nao_descoberta` — palpite de endereco
    errado (404) nao e recusa (17/10/2026). So recusa real da fonte e `sem_acesso_automatico`. As duas
    sao lacuna declarada que NAO conta como consultado (A5-08), e o motivo medido vai junto, sempre.
    """
    if achou_padrao:
        return {"modo": "padrao_por_data", "conta_como_consultado": True}
    if achou_listagem:
        return {"modo": "listagem", "conta_como_consultado": True}
    return {"modo": MODO_SEM_ACESSO if recusa else MODO_SEM_ROTA, "conta_como_consultado": False,
            "motivo": motivo or "duas tentativas sem padrão de endereço nem listagem legível"}


def descobrir_rota(uf: str, buscar_fn=None, data_de_prova: str = None) -> dict:
    """Duas tentativas de achar a rota de edicao desta UF, e o veredito.

    Tentativa 1: os moldes conhecidos, com uma data de prova em que houve edicao.
    Tentativa 2: a pagina de listagem, lida como pagina publica.
    """
    from coletores_base import buscar, ler
    buscar_fn = buscar_fn or buscar
    registro = ler("fontes_doe.json", {}) or {}
    cfg = ((registro.get("ufs") or {}).get(uf) or {})
    base = cfg.get("url") or ""
    data = data_de_prova or "2026-09-10"
    if not base:
        return {"uf": uf, "tentativas": 0,
                "veredito": veredito_da_descoberta(False, False, "nenhum endereço de diário registrado")}

    motivos, recusa = [], False
    # ── tentativa 1 · os moldes conhecidos ────────────────────────────────────────────────────
    for molde in moldes_para(base):
        url = endereco_da_data(molde, data)
        try:
            bruto = buscar_fn(url, timeout=90)
        except Exception as e:  # noqa: BLE001
            if _recusa(e, url):
                motivos.append(_recusa(e, url))
                recusa = True
                break
            continue
        impressao = hashlib.sha256(bruto).hexdigest()
        paginas = _texto_paginas(bruto)
        decisao = decidir_edicao(200, len(bruto), sum(1 for x in paginas if (x or "").strip()),
                                 len(paginas) or None, False)
        if decisao == "lida":
            return {"uf": uf, "tentativas": 1, "molde": molde, "impressao": impressao,
                     "veredito": veredito_da_descoberta(True, False, "")}
        motivos.append(f"{url[:70]}: {decisao}")
    # ── tentativa 2 · a pagina de listagem ── nunca depois de uma recusa: recusa se respeita ────
    for caminho in (() if recusa else ("", "/edicoes", "/diarios", "/busca")):
        try:
            html = buscar_fn(base.rstrip("/") + caminho, timeout=90).decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001
            motivos.append(_recusa(e, base + caminho) or f"{caminho or '/'}: {type(e).__name__}")
            if _recusa(e, base):
                recusa = True
                break
            continue
        if edicoes_da_listagem(html):
            return {"uf": uf, "tentativas": 2, "listagem": base.rstrip("/") + caminho,
                     "veredito": veredito_da_descoberta(False, True, "")}
    motivos.append("listagem sem data e número de edição no HTML")
    return {"uf": uf, "tentativas": TENTATIVAS_POR_UF,
            "veredito": veredito_da_descoberta(False, False, " · ".join(motivos[:3]), recusa)}


def _autoteste() -> int:
    falhas = []
    # O total era um literal e envelhecia calado: dizia cobrir mais casos do que
    # cobre, ou menos. Agora e contado.
    _casos_contados = []

    def ok(nome, cond):
        _casos_contados.append(nome)
        print(("  ✓ " if cond else "  ✗ ") + nome)
        if not cond:
            falhas.append(nome)

    d = datas_do_periodo("2026-06-29", "2026-07-05")
    ok("o período é por dia útil", d == ["2026-06-29", "2026-06-30", "2026-07-01",
                                             "2026-07-02", "2026-07-03"])
    ok("o período sai em ordem crescente, e quem precisa do número inverte no laço",
       datas_do_periodo("2026-09-28", "2026-10-02")[0] == "2026-09-28")
    ok("período de um dia útil devolve um dia", datas_do_periodo("2026-06-29", "2026-06-29") == ["2026-06-29"])
    ok("sábado sozinho devolve vazio", datas_do_periodo("2026-07-04", "2026-07-04") == [])

    ok("a estimativa usa a âncora mais próxima",
       estimar_edicao("2026-10-01", {"2026-09-03": 12270, "2026-10-02": 12293}) == 12292)
    ok("o padrão da PB é preenchido com mês por nome",
       endereco_da_data(PADROES["PB"]["padrao"], "2026-09-09")
       == "https://auniao.pb.gov.br/servicos/doe/2026/setembro/diario-oficial-09-09-2026-portal.pdf")
    ok("o padrão do PA é preenchido com ano, mês e dia",
       endereco_da_data(PADROES["PA"]["padrao"], "2026-09-10") == "https://www.ioepa.com.br/pages/2026/2026.09.10.DOE.pdf")
    ok("o padrão do MS é preenchido com mês por número",
       endereco_da_data(PADROES["MS"]["padrao"], "2026-09-03").endswith("/2026/09/03/DO_03_09_2026.pdf"))

    oc = ocorrencias_no_texto("Institui o Grupo Condutor estadual. Trata do El Niño 2026/2027.")
    ok("acha os termos, sem repetir o mesmo termo",
       sorted(x["termo"] for x in oc) == ["El Niño", "grupo condutor"])
    ok("guarda o trecho em volta", all(len(x["trecho"]) > 20 for x in oc))
    ok("texto sem termo devolve vazio", ocorrencias_no_texto("Portaria de nomeação de servidor.") == [])
    ok("sigla curta não casa dentro de tabela de licitação",
       ocorrencias_no_texto("PAULO CESA L R T D D A E MENDONCA COESTE 53777136000179") == [])
    ok("sigla curta casa quando é palavra, COM contexto de saúde",
       [x["termo"] for x in ocorrencias_no_texto(
           "Institui o COES, centro de operações de emergência em saúde, para o ciclo")]
       == ["centro de operações", "COES"])
    ok("plano de contingência de um sistema de informática não é pista do ciclo",
       ocorrencias_no_texto("será adotado o Plano de Contingência do Sistema E-TFD, "
                            "para tramitação de processos administrativos") == [])
    ok("plano de contingência com o risco do ciclo é pista",
       [x["termo"] for x in ocorrencias_no_texto(
           "Aprova o Plano de Contingência para a estiagem e as ondas de calor")]
       == ["plano de contingência"])
    ok("sigla solta por artefato de extração, sem contexto de saúde, não conta",
       ocorrencias_no_texto("SOLU COES EM LICITA- Conforme Parecer nº 366 da Assessoria") == [])
    ok("texto vazio não quebra", ocorrencias_no_texto("") == [] and ocorrencias_no_texto(None) == [])

    pgs = ["capa", "sumário", "Institui a Sala de Situação do El Niño", "anúncios"]
    ok("acha a página do trecho", pagina_do_trecho(pgs, "Institui a Sala de Situação") == 3)
    ok("trecho fora das páginas devolve None", pagina_do_trecho(pgs, "texto que não existe") is None)
    ok("páginas vazias não quebram", pagina_do_trecho([], "x") is None)

    ok("404 é ausência de edição na data", decidir_edicao(404, 0, 0) == "sem_edicao_na_data")
    ok("403 é recusa", decidir_edicao(403, 0, 0) == "recusa")
    ok("PDF sem texto não é edição sem o termo",
       decidir_edicao(200, 50000, 0) == "sem_texto_extraivel")
    ok("edição com texto é lida", decidir_edicao(200, 50000, 12) == "lida")
    ok("arquivo de 2 KB servido com 200 não é edição",
       decidir_edicao(200, 2016, 1, 1) == "nao_e_edicao")
    ok("uma página só não é edição de diário",
       decidir_edicao(200, 500000, 1, 1) == "nao_e_edicao")
    ok("o mesmo arquivo em outra data não é edição",
       decidir_edicao(200, 500000, 40, 40, repetido=True) == "nao_e_edicao")

    s = situacao_do_canal2("PB")
    ok("PB tem padrão por data", s["modo"] == "padrao_por_data")
    ok("os moldes conhecidos saem com a base preenchida",
       moldes_para("https://x.gov.br/")[0].startswith("https://x.gov.br/portal/download/"))
    ok("padrão achado conta como consultado",
       veredito_da_descoberta(True, False, "")["modo"] == "padrao_por_data")
    ok("listagem achada conta como consultado",
       veredito_da_descoberta(False, True, "")["modo"] == "listagem")
    ok("404 é palpite de endereço errado: rota não descoberta, nunca recusa, e NÃO conta como consultado",
       veredito_da_descoberta(False, False, "404 em tudo") == {
           "modo": MODO_SEM_ROTA, "conta_como_consultado": False, "motivo": "404 em tudo"})
    ok("só recusa real (403, muro) é sem acesso automático",
       veredito_da_descoberta(False, False, "HTTP 403", recusa=True)["modo"] == MODO_SEM_ACESSO)

    class _Http(Exception):
        def __init__(self, code):
            self.code = code

    class MuroDeRobo(Exception):
        pass
    ok("_recusa nomeia 401/403/429/451 e muro; 404 e erro de rede não são recusa",
       all(_recusa(_Http(c), "u") for c in RECUSAS_HTTP) and _recusa(MuroDeRobo("x"), "u")
       and not _recusa(_Http(404), "u") and not _recusa(OSError("dns"), "u"))
    fontes = {"CE": {"adaptador": "edicao_ce", "url": "c"}, "ES": {"adaptador": "apifront", "url": "e"}}
    ok("a rota da UF: padrão, adaptador de edição por data, busca do diário, nenhuma",
       [rota_da_uf(u, fontes)["tipo"] for u in ("PB", "CE", "ES", "RJ")] == ["padrao", "edicao", "busca", None])
    ok("o registro guarda o adaptador, e a situação se responde sem o fontes_doe",
       situacao_do_canal2("CE", registro={"canal2": {"adaptador": "edicao_ce"}})["modo"] == "padrao_por_data"
       and situacao_do_canal2("ES", registro={"canal2": {"adaptador": "apifront"}})["modo"] == "busca_no_diario")
    ok("lacuna da declaração distingue recusa de rota não descoberta",
       busca_de_declaracao("PE", {"canal2": {"modo": MODO_SEM_ACESSO, "motivo": "HTTP 403"}})["lacuna"].startswith("recusa")
       and "nenhuma recusa" in busca_de_declaracao("RJ", {"canal2": {"modo": MODO_SEM_ROTA, "motivo": "404"}})["lacuna"])
    bd = {"consultado_em": "17/10/2026", "desde": INICIO_DO_CICLO, "ate": "2026-10-17", "termos_versao": VERSAO_DOS_TERMOS}
    ok("busca do diário desde o início do ciclo, com os termos de hoje, conta como consultada",
       busca_de_declaracao("ES", {"canal2": {"adaptador": "apifront", "busca_declaracao": bd}})
       == {"consultado_em": "17/10/2026", "via": "busca do diário (adaptador apifront)"})
    ok("busca que acabou antes do dia em que diz ter consultado é lacuna",
       "lacuna" in busca_de_declaracao("ES", {"canal2": {"adaptador": "apifront", "busca_declaracao": dict(bd, ate="2026-09-30")}}))
    ok("busca que começou depois do ciclo, ou com termos velhos, é lacuna",
       "lacuna" in busca_de_declaracao("ES", {"canal2": {"adaptador": "apifront", "busca_declaracao": dict(bd, desde="2026-10-01")}})
       and "lacuna" in busca_de_declaracao("ES", {"canal2": {"adaptador": "apifront", "busca_declaracao": dict(bd, termos_versao="x")}}))
    pedidos = []

    def _busca(uf, ad, url, de, ate, termos):
        pedidos.append(termos)
        if termos != ["emergência em saúde pública"]:
            return [], {termos[0]: 0}
        return ([{"data": "2026-09-10", "url": "doc1", "pagina": 3, "trechos": [
                    "DECRETO Nº 9. O GOVERNADOR declara situação de emergência em saúde pública pela dengue"]},
                 {"data": "2026-09-10", "url": "doc2", "pagina": 1, "trechos": ["o COE de emergência em saúde pública reuniu-se"]},
                 {"data": "2026-09-11", "url": "doc3", "pagina": 2, "trechos": ["Fica declarada emergência em saúde pública"]}],
                {"emergência em saúde pública": 3})
    oc = {}
    resumo, rec = _pela_busca("ES", {"adaptador": "apifront", "url": "e"}, INICIO_DO_CICLO, "2026-10-17", oc,
                              "17/10/2026", busca_fn=_busca, preservar_fn=lambda *a: "h")
    ok("a busca pergunta só as expressões com saúde, sem a contida em outra",
       pedidos == [["emergência em saúde pública"], ["estado de emergência em saúde"]])
    ok("acerto com declaração entra no índice com a classe; menção sem 'declar' fica fora; mesma data não colide",
       sorted(oc) == ["2026-09-10", "2026-09-11"] and oc["2026-09-10"]["url"] == "doc1"
       and all(a.get("classe") == "declaracao" for a in oc["2026-09-10"]["achados"]) and rec is None
       and resumo["acertos"] == 3 and resumo["com_declaracao"] == 2 and resumo["termos_versao"] == VERSAO_DOS_TERMOS)

    r3, _ = _pela_busca("AC", {"adaptador": "busca_ac", "url": "a"}, INICIO_DO_CICLO, "2026-10-17", {}, "17/10/2026",
                        busca_fn=lambda *a, termos: ([{"url": f"e{i}", "trechos": [""]} for i in range(10)], {termos[0]: 10}),
                        preservar_fn=lambda *a: "h")
    r4, _ = _pela_busca("ES", {"adaptador": "apifront", "url": "e"}, INICIO_DO_CICLO, "2026-10-17", {}, "17/10/2026",
                        busca_fn=lambda *a, termos: ([{"url": "x", "trechos": [""]}], {termos[0]: 600}),
                        preservar_fn=lambda *a: "h")
    ok("busca truncada (lido < declarado, ou página única cheia) é lacuna, nunca consultado",
       "truncada" in r3.get("lacuna", "") and "truncada" in r4.get("lacuna", ""))

    def _recusa_busca(*a, **k):
        raise _Http(403)
    r2, rec2 = _pela_busca("ES", {"adaptador": "apifront", "url": "e"}, INICIO_DO_CICLO, "2026-10-17", {},
                           "17/10/2026", busca_fn=_recusa_busca, preservar_fn=lambda *a: "h")
    ok("403 na busca é recusa nomeada e lacuna, nunca consultado", rec2 and "lacuna" in r2)
    ok("o adaptador de edição devolve uma edição por caderno",
       _edicoes_da_data({"tipo": "edicao"}, {}, "2026-10-14", {}, {},
                        lambda d: [{"url": "p01"}, {"url": "p02"}]) == [[{"url": "p01"}], [{"url": "p02"}]])
    ok("o padrão por data devolve uma edição com um endereço",
       _edicoes_da_data({"tipo": "padrao"}, PADROES["PB"], "2026-09-09", {}, {}, None)[0][0]["url"].endswith("09-09-2026-portal.pdf"))
    ok("lacuna sem motivo recebe o motivo padrão",
       "duas tentativas" in veredito_da_descoberta(False, False, "")["motivo"])
    ok("UF sem rota fica 'rota não descoberta', e não 'sem diário' nem recusa",
       situacao_do_canal2("XX")["modo"] == MODO_SEM_ROTA)
    ok("UF com adaptador de busca entra como busca no diário",
       situacao_do_canal2("XX", {}, {"XX": {"adaptador": "apifront"}})["modo"] == "busca_no_diario")
    ok("rota sem acesso automático registrada vence, e não conta como consultado",
       situacao_do_canal2("XX", {}, {"XX": {"adaptador": "apifront"}},
                          {"canal2": {"modo": MODO_SEM_ACESSO, "motivo": "HTTP 401"}})["modo"]
       == MODO_SEM_ACESSO)

    dec = ocorrencias_no_texto("DECRETO Nº 1, DE 2026. O GOVERNADOR DO ESTADO declara situação de "
                               "emergência em saúde pública em razão da epidemia de dengue.")
    ok("declaração em saúde é indexada e marcada como declaração",
       any(x.get("classe") == "declaracao" for x in dec))
    ok("termo de declaração sem contexto de saúde não indexa",
       ocorrencias_no_texto("O Governador declara situação de emergência em razão da estiagem prolongada.") == [])
    ok("COE de emergência em saúde pública, sem declarar, não é declaração",
       not any(x.get("classe") for x in ocorrencias_no_texto(
           "Institui o Centro de Operações de Emergência em Saúde Pública para o ciclo")))
    lida = {"decisao": "lida", "em": "02/10/2026"}
    ok("edição lida antes dos termos de declaração é relida",
       a_reler(lida) and not a_reler(dict(lida, termos_versao=VERSAO_DOS_TERMOS)))
    nova = dict(lida, termos_versao=VERSAO_DOS_TERMOS)
    ciclo = {d: nova for d in datas_do_periodo(INICIO_DO_CICLO, "2026-10-01")}
    ok("metade estadual só conta com o ciclo inteiro coberto e relido",
       "lacuna" in busca_de_declaracao("PB", {"edicoes": dict(ciclo, **{"2026-09-10": lida}), "atualizado_em": "02/10/2026"})
       and busca_de_declaracao("PB", {"edicoes": ciclo, "atualizado_em": "02/10/2026"})
       == {"consultado_em": "02/10/2026", "edicoes_lidas": len(ciclo), "ate": "2026-10-01"})
    ok("data do ciclo não tentada, ou que não é edição, é falta de cobertura",
       "2026-07-01" in datas_sem_cobertura({d: e for d, e in ciclo.items() if d != "2026-07-01"}, "2026-10-01")
       and datas_sem_cobertura(dict(ciclo, **{"2026-07-02": {"decisao": "nao_e_edicao"}}), "2026-10-01") == ["2026-07-02"]
       and datas_sem_cobertura(dict(ciclo, **{"2026-07-03": {"decisao": "sem_edicao_na_data"}}), "2026-10-01") == []
       and datas_sem_cobertura(dict(ciclo, **{"2026-07-03#2": {"decisao": "vazio"}}), "2026-10-01") == ["2026-07-03#2"])
    ok("leitura pela metade (uma edição só) não é consultado",
       "lacuna" in busca_de_declaracao("PB", {"edicoes": {"2026-10-01": nova}, "atualizado_em": "02/10/2026"}))
    ok("UF sem rota é lacuna da metade estadual", "lacuna" in busca_de_declaracao("XX", {}))

    fonte = pathlib.Path(__file__).read_text(encoding="utf-8")
    escritas = [l.strip() for l in fonte.splitlines() if l.strip().startswith("gravar(")]
    # O modo --descobrir escreve o mesmo registro por UF, e por isso a conta é "toda escrita é do
    # registro da UF ou do índice" — e não um número fixo de linhas.
    ok("trava estrutural: as escritas são o registro da UF e o índice",
       escritas and all(e.startswith(("gravar(arquivo", "gravar(INDICE")) for e in escritas))
    ok("trava estrutural: nenhum arquivo do banco é destino",
       not any(f'gravar("{b}' in fonte for b in BANCO_PROIBIDO))
    # Promover a registro é do juiz. A trava confere no código COMPILADO: nenhuma função deste
    # módulo chama `aplicar` nem importa o juiz — e olhar o bytecode evita o laço em que a própria
    # linha do teste, por citar o nome, fazia o teste reprovar.
    import dis
    nomes = set()
    for nome_obj, obj in list(globals().items()):
        # o próprio autoteste cita os nomes proibidos, e por isso fica de fora da varredura
        if nome_obj == "_autoteste":
            continue
        codigo = getattr(obj, "__code__", None)
        if codigo is not None:
            nomes |= {i.argval for i in dis.get_instructions(codigo) if isinstance(i.argval, str)}
    ok("trava estrutural: o coletor não chama a aplicação do veredito",
       "aplicar" not in nomes and "julgar_saude" not in nomes)

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else f"✓ AUTOTESTE OK — {len(_casos_contados)} casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return _autoteste()

    sys.path.insert(0, str(RAIZ))
    from coletores_base import hoje_editorial

    if "--descobrir" in sys.argv:
        from coletores_base import gravar, hoje_editorial, ler
        registro = ler("fontes_doe.json", {}) or {}
        ufs = registro.get("ufs") or {}
        hoje = hoje_editorial().strftime("%d/%m/%Y")
        alvos = [uf for uf, v in sorted(ufs.items())
                 if not (v or {}).get("adaptador") and uf not in PADROES]
        print(f"{len(alvos)} unidade(s) sem rota de edição a descobrir, "
              f"{TENTATIVAS_POR_UF} tentativa(s) cada")
        for uf in alvos:
            r = descobrir_rota(uf)
            v = r["veredito"]
            arquivo = f"{PASTA}/{uf}.json"
            (RAIZ / "data" / PASTA).mkdir(parents=True, exist_ok=True)
            reg = ler(arquivo, {}) or {}
            reg.setdefault("_governanca", (
                GOVERNANCA_CANAL2))
            reg["canal2"] = dict(v, em=hoje, tentativas=r.get("tentativas"))
            if r.get("molde"):
                reg["canal2"]["molde_descoberto"] = r["molde"]
            if r.get("listagem"):
                reg["canal2"]["listagem"] = r["listagem"]
            reg.setdefault("edicoes", {})
            gravar(arquivo, reg)
            print(f"  {uf}: {v['modo']}" + (f" · {v.get('motivo', '')[:90]}" if v.get("motivo") else "")
                  + (f" · molde {r['molde']}" if r.get("molde") else ""))
        return 0

    if "--relatorio" in sys.argv:
        from coletores_base import ler
        adaptadores = (ler("fontes_doe.json", {}) or {}).get("ufs") or {}
        contagem = {}
        for uf in UFS:
            reg = ler(f"{PASTA}/{uf}.json", {}) or {}
            sit = situacao_do_canal2(uf, None, adaptadores, reg)
            lidas = sum(1 for e in (reg.get("edicoes") or {}).values()
                        if isinstance(e, dict) and e.get("decisao") == "lida")
            com_termo = sum(1 for e in (reg.get("edicoes") or {}).values()
                            if isinstance(e, dict) and e.get("termos_achados"))
            contagem[sit["modo"]] = contagem.get(sit["modo"], 0) + 1
            print(f"  {uf}: {sit['modo']} · {sit['detalhe'][:70]}"
                  + (f" · {lidas} edição(ões) lida(s), {com_termo} com termo" if lidas else ""))
        print("  —")
        for modo, n in sorted(contagem.items(), key=lambda x: -x[1]):
            print(f"  {modo}: {n} unidade(s)")
        return 0

    def arg(nome, padrao=None):
        return sys.argv[sys.argv.index(nome) + 1] if nome in sys.argv else padrao

    desde = arg("--desde", INICIO_DO_CICLO)
    ate = arg("--ate", hoje_editorial().isoformat())
    if "--recuperacao" in sys.argv:
        # Toda UF com rota: a busca primeiro (minutos), as edições inteiras depois (o grosso do tempo).
        from coletores_base import ler
        fontes = (ler("fontes_doe.json", {}) or {}).get("ufs") or {}
        alvos = sorted((uf for uf in UFS if rota_da_uf(uf, fontes)["tipo"]),
                       key=lambda uf: rota_da_uf(uf, fontes)["tipo"] != "busca")
    else:
        uf = arg("--uf")
        if not uf:
            print("uso: --uf <UF> | --recuperacao | --relatorio | --autoteste")
            return 2
        alvos = [uf.upper()]

    print(f"canal 2 · {len(alvos)} UF(s) de {desde} a {ate}")
    for uf in alvos:
        coletar_uf(uf, desde, ate)
    return 0


if __name__ == "__main__":
    sys.exit(main())
