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
  e são gravados como `verificacao_humana`, com o motivo técnico — e, pela regra da Paraíba, isso
  **conta como canal 2 consultado** no fechamento: limitação documentada de terceiro não deixa um
  estado "não verificado" para sempre;
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

RAIZ = pathlib.Path(__file__).resolve().parent
PASTA = "doe_edicoes"
INDICE = "doe_ocorrencias.json"
INICIO_DO_CICLO = "2026-06-29"
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
CONTEXTO_DE_SIGLA = {t: re.compile(r, re.I) for t, r in CONTEXTO_POR_TERMO.items()}
JANELA_DE_CONTEXTO = 300

# ── Padrões de endereço por data ───────────────────────────────────────────────────────────────
# Cada padrão foi CONFERIDO contra uma edição real antes de entrar aqui; a conferência está na
# nota de cada um. Padrão que depende do NÚMERO da edição (e não da data) precisa da listagem, e
# por isso vive com `listagem` em vez de `padrao`.
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
    # PDF baixável, visto pela central. O portal serve por data.
    # MEDIDO em 02/10/2026 e RETIRADO: o endereço por data respondia 200 em todas as 70 datas,
    # sempre com o mesmo arquivo de 2.016 bytes e uma página — página de erro servida como PDF. O
    # portal do Amapá serve a edição por ID (`/portal/edicoes/download/{id}`), e a listagem que
    # liga data a ID é montada por JavaScript. Entra quando a listagem for lida; até então o canal
    # 2 do AP é verificação humana, com este motivo gravado.
    "AP": {"listagem": "https://diofe.portal.ap.gov.br/portal/edicoes",
           "nota": "edição por ID; a listagem que liga data a ID exige leitura da página"},
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
            fora.append({"termo": termo, "trecho": t[ini:m.end() + 220].strip()})
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


def situacao_do_canal2(uf: str, padroes=None, adaptadores=None, registro=None) -> dict:
    """Como o canal 2 é feito nesta UF. Função pura.

    Quatro modos, na ordem em que valem: `padrao_por_data` (baixa a edição pelo endereço),
    `listagem` (o número ou o id da edição vem de uma página de listagem), `busca_no_diario` (a
    UF é uma das que oferecem busca, e o adaptador já existia) e `verificacao_humana` (limitação
    técnica de terceiro documentada — conta como consultado, regra da Paraíba). Sem nenhum deles,
    `a_descobrir`: é ausência de **rota**, não ausência de diário.
    """
    p = (padroes if padroes is not None else PADROES).get(uf)
    reg = (registro or {}).get("canal2") or {}
    if reg.get("modo") == "verificacao_humana" and reg.get("motivo"):
        return {"uf": uf, "modo": "verificacao_humana", "detalhe": reg["motivo"],
                "nota": "conta como canal consultado"}
    if p and p.get("padrao"):
        return {"uf": uf, "modo": "padrao_por_data", "detalhe": p["padrao"], "nota": p.get("nota")}
    if p and p.get("listagem"):
        return {"uf": uf, "modo": "listagem", "detalhe": p["listagem"], "nota": p.get("nota")}
    adaptador = ((adaptadores or {}).get(uf) or {}).get("adaptador")
    if adaptador:
        return {"uf": uf, "modo": "busca_no_diario", "detalhe": f"adaptador {adaptador}",
                "nota": "a busca no sítio continua valendo onde existe"}
    return {"uf": uf, "modo": "a_descobrir",
            "detalhe": "sem rota de edição conferida para esta UF",
            "nota": "a listagem de edições precisa ser lida para derivar o padrão"}


# ── execução ───────────────────────────────────────────────────────────────────────────────────
def _texto_paginas(bruto: bytes) -> list:
    """Texto por página, pela porta canônica do projeto."""
    try:
        import io as _io

        import pdfplumber
        with pdfplumber.open(_io.BytesIO(bruto)) as pdf:
            pgs = [(pg.extract_text() or "") for pg in pdf.pages]
        if sum(len(t) for t in pgs) > 200:
            return pgs
    except Exception:  # noqa: BLE001
        pass
    try:
        from preservar_evidencias import extrair_texto_por_pagina
        return extrair_texto_por_pagina(bruto)
    except Exception:  # noqa: BLE001
        return []


def coletar_uf(uf: str, desde: str, ate: str) -> dict:
    """Baixa, lê e indexa as edições de uma UF no período. Devolve o resumo da execução."""
    from coletores_base import (MuroDeRobo, buscar, gravar, hoje_editorial, ler, log_busca,
                                preservar_evidencia, registrar_lacuna)

    p = PADROES.get(uf)
    if not p or not p.get("padrao"):
        s = situacao_do_canal2(uf)
        registrar_lacuna(f"DOE-{uf} (canal 2)", "sem padrão de endereço de edição conferido",
                         canal="DOE", camada=1)
        print(f"  {uf}: {s['modo']} — {s['detalhe']}")
        return {"uf": uf, "modo": s["modo"], "lidas": 0, "decisao": "sem_padrao"}

    arquivo = f"{PASTA}/{uf}.json"
    (RAIZ / "data" / PASTA).mkdir(parents=True, exist_ok=True)
    registro = ler(arquivo, {}) or {}
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

    # Quando o nome do arquivo pede o NÚMERO da edição, lê-se a listagem uma vez (ela cobre as
    # últimas) e o resto sai das âncoras, com a fonte confirmando pelo nome do arquivo.
    listagem = {}
    if "{edicao}" in p["padrao"] and p.get("listagem"):
        try:
            listagem = edicoes_da_listagem(buscar(p["listagem"], timeout=60).decode("utf-8", "replace"))
            print(f"  {uf}: listagem com {len(listagem)} edição(ões) datadas")
        except Exception as e:  # noqa: BLE001
            print(f"  {uf}: listagem não lida ({type(e).__name__}) — segue pelas âncoras")

    # As âncoras começam nas conferidas e crescem a cada acerto: a data seguinte estima a partir da
    # vizinha, e não a partir de setembro.
    ancoras_vivas = dict(p.get("ancoras") or {})
    for data_lida, item in (edicoes or {}).items():
        achado = re.search(r"DO(\d{4,6})_", str((item or {}).get("url") or ""))
        if achado and (item or {}).get("decisao") == "lida":
            ancoras_vivas[data_lida] = int(achado.group(1))
    datas = [d for d in datas_do_periodo(desde, ate) if d not in edicoes][:TETO_EDICOES]
    # Quando o nome do arquivo pede o NÚMERO da edição, percorre-se do mais novo para o mais velho:
    # a âncora de cada data passa a ser a vizinha, e a deriva por passo é de uma ou duas edições.
    # Da outra ordem, a janela de oito não alcançava dois meses de deriva e tudo dava 404.
    if "{edicao}" in p["padrao"]:
        datas = sorted(datas, reverse=True)
    lidas = com_termo = 0
    vistos = {e.get("impressao") for e in edicoes.values()
              if isinstance(e, dict) and e.get("impressao")}
    hoje = hoje_editorial().strftime("%d/%m/%Y")
    for data in datas:
        if "{edicao}" in p["padrao"]:
            numeros = numeros_a_tentar(data, listagem, ancoras_vivas, p.get("janela", 8))
            tentativas = [endereco_da_data(p["padrao"], data, str(n)) for n in numeros]
        else:
            tentativas = [endereco_da_data(p["padrao"], data)]
        if not tentativas:
            edicoes[data] = {"decisao": "sem_numero_de_edicao", "em": hoje,
                             "motivo": "o padrão pede o número da edição e não há âncora nem listagem"}
            continue
        url, bruto, status, erro = tentativas[0], None, 0, None
        try:
            for candidato in tentativas:
                url = candidato
                try:
                    bruto = buscar(candidato, timeout=120)
                    status = 200
                    break
                except MuroDeRobo:
                    raise
                except Exception as e:  # noqa: BLE001
                    codigo = getattr(e, "code", None) or 0
                    if codigo in (401, 403, 429, 451):
                        raise
                    erro, status = e, codigo
            if bruto is None:
                raise erro if erro else FileNotFoundError(url)
        except MuroDeRobo as e:
            registro["canal2"] = {"modo": "verificacao_humana", "motivo": f"muro de robô: {str(e)[:140]}",
                                  "em": hoje, "conta_como_consultado": True}
            registrar_lacuna(f"DOE-{uf} (canal 2)", f"muro de robô em {url[:90]}", canal="DOE", camada=1)
            print(f"  {uf}: muro de robô — canal 2 por verificação humana, e conta como consultado")
            break
        except Exception as e:  # noqa: BLE001
            status = getattr(e, "code", None) or 0
            if status in (401, 403, 429, 451):
                registro["canal2"] = {"modo": "verificacao_humana",
                                      "motivo": f"HTTP {status} na edição de {data} — recusa respeitada",
                                      "em": hoje, "conta_como_consultado": True}
                registrar_lacuna(f"DOE-{uf} (canal 2)", f"HTTP {status} — recusa respeitada",
                                 canal="DOE", camada=1)
                print(f"  {uf}: HTTP {status} — canal 2 por verificação humana, e conta como consultado")
                break
            edicoes[data] = {"decisao": decidir_edicao(status, 0, 0), "em": hoje,
                             "motivo": f"{type(e).__name__}: {str(e)[:90]}"}
            continue

        # Repetição pelo hash do conteúdo: o mesmo arquivo em duas datas não são duas edições.
        impressao = hashlib.sha256(bruto).hexdigest()
        repetido = impressao in vistos
        vistos.add(impressao)
        paginas = [] if repetido else _texto_paginas(bruto)
        com_texto = sum(1 for x in paginas if (x or "").strip())
        decisao = decidir_edicao(status, len(bruto), com_texto, len(paginas) or None, repetido)
        item = {"decisao": decisao, "em": hoje, "bytes": len(bruto), "paginas": len(paginas),
                "paginas_com_texto": com_texto, "url": url, "impressao": impressao}
        if decisao == "nao_e_edicao":
            item["motivo"] = ("mesmo arquivo de outra data" if repetido else
                              f"{len(bruto)} bytes e {len(paginas)} página(s) — não é uma edição")
        if decisao == "lida":
            achados = ocorrencias_no_texto("\n".join(paginas))
            if achados:
                item["hash_evidencia"] = preservar_evidencia(bruto, url, "pdf", "coletar_edicoes_doe")
                for a in achados:
                    a["pagina"] = pagina_do_trecho(paginas, a["trecho"])
                ocorrencias[data] = {"url": url, "hash_evidencia": item["hash_evidencia"],
                                     "paginas": len(paginas), "achados": achados}
                com_termo += 1
            item["termos_achados"] = [a["termo"] for a in achados]
            lidas += 1
        edicoes[data] = item
        achado = re.search(r"DO(\d{4,6})_", url or "")
        if achado and decisao == "lida":
            ancoras_vivas[data] = int(achado.group(1))

    registro.setdefault("canal2", {"modo": "padrao_por_data", "em": hoje,
                                   "conta_como_consultado": True})
    registro["atualizado_em"] = hoje
    gravar(arquivo, registro)
    indice["atualizado_em"] = hoje
    gravar(INDICE, indice)
    log_busca("DOE", 1, [p["padrao"]], "registro" if com_termo else "consultado sem achado",
              nivel="estadual", uf=uf, n_resultados=com_termo,
              resultados=f"canal 2 em {uf}: {lidas} edição(ões) lida(s), {com_termo} com termo de saúde")
    print(f"  {uf}: {lidas} edição(ões) lida(s), {com_termo} com termo de saúde")
    return {"uf": uf, "modo": "padrao_por_data", "lidas": lidas, "com_termo": com_termo,
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


def veredito_da_descoberta(achou_padrao: bool, achou_listagem: bool, motivo: str) -> dict:
    """O que registrar depois das duas tentativas. Funcao pura.

    Sem padrao e sem listagem legivel, o canal 2 passa a ser verificacao humana — e isso CONTA como
    consultado, pela definicao fechada de 02/10/2026. O motivo medido vai junto, sempre: sem ele,
    "verificacao humana" seria desculpa, e nao medicao.
    """
    if achou_padrao:
        return {"modo": "padrao_por_data", "conta_como_consultado": True}
    if achou_listagem:
        return {"modo": "listagem", "conta_como_consultado": True}
    return {"modo": "verificacao_humana", "conta_como_consultado": True,
            "motivo": motivo or "duas tentativas sem padrão de endereço nem listagem legível"}


def descobrir_rota(uf: str, buscar_fn=None, data_de_prova: str = None) -> dict:
    """Duas tentativas de achar a rota de edicao desta UF, e o veredito.

    Tentativa 1: os moldes conhecidos, com uma data de prova em que houve edicao.
    Tentativa 2: a pagina de listagem, lida como pagina publica.
    """
    from coletores_base import MuroDeRobo, buscar, ler
    buscar_fn = buscar_fn or buscar
    registro = ler("fontes_doe.json", {}) or {}
    cfg = ((registro.get("ufs") or {}).get(uf) or {})
    base = cfg.get("url") or ""
    data = data_de_prova or "2026-09-10"
    if not base:
        return {"uf": uf, "tentativas": 0,
                "veredito": veredito_da_descoberta(False, False, "nenhum endereço de diário registrado")}

    motivos = []
    # ── tentativa 1 · os moldes conhecidos ────────────────────────────────────────────────────
    for molde in moldes_para(base):
        url = endereco_da_data(molde, data)
        try:
            bruto = buscar_fn(url, timeout=90)
        except MuroDeRobo as e:
            motivos.append(f"muro de robô em {url[:70]}: {str(e)[:60]}")
            break
        except Exception as e:  # noqa: BLE001
            codigo = getattr(e, "code", None) or 0
            if codigo in (401, 403, 429, 451):
                motivos.append(f"HTTP {codigo} em {url[:70]} — recusa respeitada")
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
    # ── tentativa 2 · a pagina de listagem ────────────────────────────────────────────────────
    for caminho in ("", "/edicoes", "/diarios", "/busca"):
        try:
            html = buscar_fn(base.rstrip("/") + caminho, timeout=90).decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001
            motivos.append(f"{caminho or '/'}: {type(e).__name__}")
            continue
        if edicoes_da_listagem(html):
            return {"uf": uf, "tentativas": 2, "listagem": base.rstrip("/") + caminho,
                     "veredito": veredito_da_descoberta(False, True, "")}
    motivos.append("listagem sem data e número de edição no HTML")
    return {"uf": uf, "tentativas": TENTATIVAS_POR_UF,
            "veredito": veredito_da_descoberta(False, False, " · ".join(motivos[:3]))}


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
    ok("sem rota, o canal 2 é verificação humana E conta como consultado",
       veredito_da_descoberta(False, False, "404 em tudo") == {
           "modo": "verificacao_humana", "conta_como_consultado": True, "motivo": "404 em tudo"})
    ok("verificação humana sem motivo recebe o motivo padrão",
       "duas tentativas" in veredito_da_descoberta(False, False, "")["motivo"])
    ok("UF sem rota fica 'a descobrir', e não 'sem diário'",
       situacao_do_canal2("XX")["modo"] == "a_descobrir")
    ok("UF com adaptador de busca entra como busca no diário",
       situacao_do_canal2("XX", {}, {"XX": {"adaptador": "apifront"}})["modo"] == "busca_no_diario")
    ok("verificação humana registrada vence, e conta como consultado",
       situacao_do_canal2("XX", {}, {"XX": {"adaptador": "apifront"}},
                          {"canal2": {"modo": "verificacao_humana", "motivo": "HTTP 401"}})["modo"]
       == "verificacao_humana")

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
                "Canal 2 desta unidade. Quando a rota de edição não foi achada em duas tentativas, "
                "o canal 2 passa a ser verificação humana registrada, com o motivo medido — e isso "
                "conta como consultado (definição fechada de 02/10/2026)."))
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
        ufs = ("AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO").split()
        contagem = {}
        for uf in ufs:
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
        alvos = [uf for uf, p in PADROES.items() if p.get("padrao")]
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
