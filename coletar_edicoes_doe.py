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
    python3 coletar_edicoes_doe.py --recuperacao            # todas as UFs com rota, desde 29/06
    python3 coletar_edicoes_doe.py --relatorio              # a tabela 27 × situação do canal 2
    python3 coletar_edicoes_doe.py --autoteste              # sem rede, sem escrita
"""
from __future__ import annotations

import datetime as dt
import hashlib
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
    # 17/10/2026 (A3): o padrão foi LIDO nos links reais da página inicial (DOE-16-10-2026.pdf …
    # DOE-29-09-2026.pdf) e a edição de 10/09/2026 baixou do runner (3,7 MB, PDF). A edição
    # extraordinária e a suplementar têm outro nome (DOE-EXTRAORDINARIO-…, …-SUPLEMENTAR-1) e não
    # entram por data: a leitura cobre a edição regular, e só ela.
    "RO": {"padrao": "https://diof.ro.gov.br/data/uploads/{ano}/{mm}/DOE-{dd}-{mm}-{ano}.pdf",
           "fora_da_leitura": "edições extraordinária e suplementar (outro nome de arquivo)",
           "nota": "edição regular por data, lida na página inicial em 17/10/2026"},
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


# Vocabulário da ROTA do canal 2 (17/10/2026, HANDOVER_ROTAS_DOE §0.1). `sem_acesso_automatico` é só
# a recusa real, medida na leitura (401, 403, 429, 451, captcha, muro de robô); endereço que dá 404 é
# palpite errado, não recusa, e a UF fica `rota_nao_descoberta`. As duas são lacuna declarada, e
# nenhuma conta como canal consultado (A5-08, 10/10/2026). A rota de cada UF é a de `fontes_doe.json`,
# medida pela sondagem e pelos adaptadores do canal 1 — um registro só, sem palpite de endereço aqui.
MODO_SEM_ACESSO = "sem_acesso_automatico"
MODO_SEM_ROTA = "rota_nao_descoberta"
MODOS_DE_ROTA = ("padrao_por_data", "edicao_por_adaptador", "busca_no_diario")
GOVERNANCA_CANAL2 = ("Canal 2 desta unidade. Recusa real de acesso (401, 403, 429, 451, captcha, muro de "
                     "robô) é rota sem acesso automático; rota não achada é rota não descoberta. As duas "
                     "são lacuna declarada, que não conta como consultado (A5-08, 10/10/2026).")


def situacao_do_canal2(uf: str, padroes=None, adaptadores=None, registro=None) -> dict:
    """Como o canal 2 é feito nesta UF. Função pura (dado `adaptadores`, o `fontes_doe.json`).

    Na ordem em que valem: recusa medida (`sem_acesso_automatico`), `padrao_por_data` (endereço da
    edição conferido aqui), `edicao_por_adaptador` (a edição do dia pelo adaptador do canal 1),
    `busca_no_diario` (a busca do próprio diário, pelo adaptador do canal 1) e, sem nenhum,
    `rota_nao_descoberta` com o motivo medido: ausência de ROTA, não de diário, nem recusa.
    """
    from coletar_doe import ADAPTADORES_DE_BUSCA
    p = (padroes if padroes is not None else PADROES).get(uf) or {}
    reg = (registro or {}).get("canal2") or {}
    cfg = (adaptadores or {}).get(uf) or {}
    ad = cfg.get("adaptador") or ""
    if reg.get("modo") == MODO_SEM_ACESSO and reg.get("motivo"):
        return {"uf": uf, "modo": MODO_SEM_ACESSO, "detalhe": reg["motivo"],
                "nota": "recusa real — lacuna declarada, não conta como canal consultado"}
    if p.get("padrao"):
        return {"uf": uf, "modo": "padrao_por_data", "detalhe": p["padrao"], "nota": p.get("nota")}
    if ad.startswith("edicao_"):
        return {"uf": uf, "modo": "edicao_por_adaptador", "detalhe": f"adaptador {ad}", "nota": cfg.get("caminho")}
    if ad in ADAPTADORES_DE_BUSCA:
        return {"uf": uf, "modo": "busca_no_diario", "detalhe": f"adaptador {ad}", "nota": cfg.get("caminho")}
    if reg.get("modo") in MODOS_DE_ROTA:
        return {"uf": uf, "modo": reg["modo"], "detalhe": reg.get("detalhe") or reg["modo"], "nota": None}
    return {"uf": uf, "modo": MODO_SEM_ROTA,
            "detalhe": cfg.get("motivo") or reg.get("motivo") or "sem rota de edição conferida para esta UF",
            "nota": "rota não descoberta — lacuna declarada, não recusa"}


def a_reler(item) -> bool:
    """Edição lida antes dos termos de declaração tem de ser relida. Função pura."""
    return isinstance(item, dict) and item.get("decisao") == "lida" and item.get("termos_versao") != VERSAO_DOS_TERMOS


def busca_de_declaracao(uf: str, registro: dict, adaptadores=None) -> dict:
    """A metade estadual da resposta sanitária nesta UF: `consultado_em` só quando as edições lidas
    do ciclo foram todas lidas com os termos de declaração, ou a busca do diário rodou com eles desde
    o início do ciclo, sem erro e sem teto; senão `lacuna` com o motivo. Pura dado `adaptadores`."""
    if adaptadores is None:
        from coletores_base import ler
        adaptadores = (ler("fontes_doe.json", {}) or {}).get("ufs") or {}
    sit = situacao_do_canal2(uf, None, adaptadores, registro)
    if sit["modo"] not in MODOS_DE_ROTA:
        return {"lacuna": f"{sit['modo']}: {sit['detalhe']}"}
    if sit["modo"] == "busca_no_diario":
        b = registro.get("busca_declaracao") or {}
        falta = ("a busca do diário não rodou com os termos de declaração" if b.get("termos_versao") != VERSAO_DOS_TERMOS
                 else f"a busca começou em {b.get('desde')}, depois do início do ciclo" if (b.get("desde") or "9") > INICIO_DO_CICLO
                 else b.get("erro") or b.get("parcial"))
        if not falta and (b.get("ate") or "") < dt.datetime.strptime(b["em"], "%d/%m/%Y").date().isoformat():
            falta = f"a busca terminou em {b.get('ate')}, antes do dia em que rodou"
        return {"lacuna": falta} if falta else {"consultado_em": b["em"], "acertos": b["acertos_de_declaracao"]}
    todas = [e for e in (registro.get("edicoes") or {}).values() if isinstance(e, dict)]
    lidas = [e for e in todas if e.get("decisao") == "lida"]
    velhas = sum(1 for e in lidas if a_reler(e))
    falhas = sum(1 for e in todas if e.get("decisao") in ("recusa", "vazio", "sem_texto_extraivel", "sem_numero_de_edicao"))
    if velhas or falhas or not lidas:
        return {"lacuna": (f"{velhas} edição(ões) ainda não relida(s) com os termos de declaração" if velhas
                           else f"{falhas} edição(ões) do ciclo não lida(s)" if falhas
                           else f"nenhuma edição lida por data ({sit['modo']})")}
    if (PADROES.get(uf) or {}).get("fora_da_leitura"):   # edição que o padrão não alcança: a metade não fecha
        return {"lacuna": f"{len(lidas)} edição(ões) lida(s); fora da leitura: {PADROES[uf]['fora_da_leitura']}"}
    em = max(dt.datetime.strptime(e["em"], "%d/%m/%Y").date() for e in lidas)
    return {"consultado_em": em.strftime("%d/%m/%Y"), "edicoes_lidas": len(lidas)}


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

    arquivo = f"{PASTA}/{uf}.json"
    registro = ler(arquivo, {}) or {}
    cfg = ((ler("fontes_doe.json", {}) or {}).get("ufs") or {}).get(uf) or {}
    sit = situacao_do_canal2(uf, None, {uf: cfg}, registro)
    if sit["modo"] == "busca_no_diario":
        return coletar_por_busca(uf, desde, ate, cfg, registro)
    if sit["modo"] not in MODOS_DE_ROTA:
        registrar_lacuna(f"DOE-{uf} (canal 2)", f"{sit['modo']}: {sit['detalhe'][:140]}", canal="DOE", camada=1)
        print(f"  {uf}: {sit['modo']} — {sit['detalhe'][:140]}")
        return {"uf": uf, "modo": sit["modo"], "lidas": 0, "decisao": sit["modo"]}
    p = PADROES.get(uf) or {}
    if not p.get("padrao"):
        import coletar_doe
        edicoes_da_data = coletar_doe.EDICOES_POR_DATA[cfg["adaptador"]](buscar, cfg.get("url"))
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

    # Quando o nome do arquivo pede o NÚMERO da edição, lê-se a listagem uma vez (ela cobre as
    # últimas) e o resto sai das âncoras, com a fonte confirmando pelo nome do arquivo.
    listagem = {}
    if "{edicao}" in p.get("padrao", "") and p.get("listagem"):
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
    datas = [d for d in datas_do_periodo(desde, ate) if d not in edicoes or a_reler(edicoes[d])][:TETO_EDICOES]
    # Quando o nome do arquivo pede o NÚMERO da edição, percorre-se do mais novo para o mais velho:
    # a âncora de cada data passa a ser a vizinha, e a deriva por passo é de uma ou duas edições.
    # Da outra ordem, a janela de oito não alcançava dois meses de deriva e tudo dava 404.
    if "{edicao}" in p.get("padrao", ""):
        datas = sorted(datas, reverse=True)
    lidas = com_termo = 0
    vistos = {e.get("impressao") for d, e in edicoes.items()
              if isinstance(e, dict) and e.get("impressao") and d.split("#")[0] not in datas}
    hoje = hoje_editorial().strftime("%d/%m/%Y")
    for n_data, data in enumerate(datas):
        if n_data and not n_data % 10:
            gravar(arquivo, registro)       # recuperação longa: o prazo do elo não leva o já lido
            gravar(INDICE, indice)
        try:
            if p.get("padrao"):
                if "{edicao}" in p["padrao"]:
                    numeros = numeros_a_tentar(data, listagem, ancoras_vivas, p.get("janela", 8))
                    tentativas = [endereco_da_data(p["padrao"], data, str(n)) for n in numeros]
                else:
                    tentativas = [endereco_da_data(p["padrao"], data)]
                if not tentativas:
                    edicoes[data] = {"decisao": "sem_numero_de_edicao", "em": hoje,
                                     "motivo": "o padrão pede o número da edição e não há âncora nem listagem"}
                    continue
                grupos = [[(u, None) for u in tentativas]]
            else:
                # A edição do dia pelo adaptador do canal 1: vários PDFs (cadernos, suplemento) numa data.
                grupos = [[(e["url"], e.get("pdf"))] for e in edicoes_da_data(data)]
                if not grupos:
                    edicoes[data] = {"decisao": "sem_edicao_na_data", "em": hoje,
                                     "motivo": "a listagem da fonte não traz edição nesta data"}
                    continue
            baixadas = [_baixar(g, buscar, MuroDeRobo) for g in grupos]
        except MuroDeRobo as e:
            registro["canal2"] = {"modo": MODO_SEM_ACESSO, "motivo": f"muro de robô: {str(e)[:140]}",
                                  "em": hoje, "conta_como_consultado": False}
            registrar_lacuna(f"DOE-{uf} (canal 2)", f"muro de robô em {data}", canal="DOE", camada=1)
            print(f"  {uf}: muro de robô — canal 2 sem acesso automático, lacuna declarada (não conta como consultado)")
            break
        except Exception as e:  # noqa: BLE001
            status = getattr(e, "code", None) or 0
            if status in (401, 403, 429, 451):
                registro["canal2"] = {"modo": MODO_SEM_ACESSO,
                                      "motivo": f"HTTP {status} na edição de {data} — recusa respeitada",
                                      "em": hoje, "conta_como_consultado": False}
                registrar_lacuna(f"DOE-{uf} (canal 2)", f"HTTP {status} — recusa respeitada",
                                 canal="DOE", camada=1)
                print(f"  {uf}: HTTP {status} — canal 2 sem acesso automático, lacuna declarada (não conta como consultado)")
                break
            # 404 num endereço que a própria fonte listou não é "sem edição": é edição não lida.
            decisao = decidir_edicao(status, 0, 0)
            edicoes[data] = {"decisao": "vazio" if decisao == "sem_edicao_na_data" and not p.get("padrao") else decisao,
                             "em": hoje, "motivo": f"{type(e).__name__}: {str(e)[:90]}"}
            continue

        for n_ed, (url, bruto) in enumerate(baixadas):
            chave = data if not n_ed else f"{data}#{n_ed + 1}"
            # Repetição pelo hash do conteúdo: o mesmo arquivo em duas datas não são duas edições.
            impressao = hashlib.sha256(bruto).hexdigest()
            repetido = impressao in vistos
            vistos.add(impressao)
            paginas = [] if repetido else _texto_paginas(bruto)
            com_texto = sum(1 for x in paginas if (x or "").strip())
            decisao = decidir_edicao(200, len(bruto), com_texto, len(paginas) or None, repetido)
            item = {"decisao": decisao, "em": hoje, "bytes": len(bruto), "paginas": len(paginas),
                    "paginas_com_texto": com_texto, "url": url, "impressao": impressao,
                    "termos_versao": VERSAO_DOS_TERMOS}
            if decisao == "nao_e_edicao":
                item["motivo"] = ("mesmo arquivo de outra data" if repetido else
                                  f"{len(bruto)} bytes e {len(paginas)} página(s) — não é uma edição")
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

    if lidas:
        # 14/10/2026 (ciclo de 15 dias): o diário da UF foi LIDO, edição por edição — é verificação
        # real por DOE, e o livro de fontes a registra como o canal 1 já registra (`DOE/<UF>`).
        from coletores_base import marcar_fonte_consultada, referencia_ibge
        por_cod, _ = referencia_ibge()
        marcar_fonte_consultada([c for c, r in por_cod.items() if r["uf"] == uf], f"DOE/{uf}", "estadual",
                                resultado=f"{lidas} edição(ões) lida(s) por data (canal 2)")
    if (registro.get("canal2") or {}).get("modo") != MODO_SEM_ACESSO:
        registro["canal2"] = {"modo": sit["modo"], "em": hoje, "conta_como_consultado": bool(lidas)}
    registro["atualizado_em"] = hoje
    gravar(arquivo, registro)
    indice["atualizado_em"] = hoje
    gravar(INDICE, indice)
    log_busca("DOE", 1, [sit["detalhe"]], "registro" if com_termo else "consultado sem achado" if lidas else "sem_edicao_no_periodo",
              nivel="estadual", uf=uf, n_resultados=com_termo,
              resultados=f"canal 2 em {uf}: {lidas} edição(ões) lida(s), {com_termo} com termo de saúde")
    print(f"  {uf}: {lidas} edição(ões) lida(s), {com_termo} com termo de saúde")
    return {"uf": uf, "modo": sit["modo"], "lidas": lidas, "com_termo": com_termo,
            "decisao": "registro" if com_termo else "consultado sem achado" if lidas else "sem_edicao_no_periodo"}


def _baixar(tentativas: list, buscar_fn, muro) -> tuple:
    """(url, bytes) da primeira alternativa que a fonte serve. Recusa real e muro levantam; 404 e
    outro erro passam à seguinte, e sem nenhuma levanta o último erro."""
    erro = None
    for url, pronto in tentativas:
        if pronto:
            return url, pronto
        try:
            return url, buscar_fn(url, timeout=120)
        except muro:
            raise
        except Exception as e:  # noqa: BLE001
            if (getattr(e, "code", None) or 0) in (401, 403, 429, 451):
                raise
            erro = e
    raise erro if erro else FileNotFoundError(tentativas[0][0] if tentativas else "sem endereço")


def ocorrencias_da_busca(itens: list) -> dict:
    """{chave por data: ocorrência} das páginas que a busca do diário devolveu e que trazem termo de
    DECLARAÇÃO no contexto exigido. Função pura. A busca acha; o juiz abre o documento e decide."""
    fora = {}
    for it in itens or []:
        achados = ocorrencias_no_texto(" ".join(it.get("trechos") or []))
        if not it.get("data") or not any(a.get("classe") == "declaracao" for a in achados):
            continue
        chave, n = it["data"], 2
        while chave in fora and fora[chave]["url"] != it.get("url"):
            chave, n = f"{it['data']}#{n}", n + 1
        for a in achados:
            a["pagina"] = it.get("pagina")        # a mesma edição casa em mais de uma página
        fora.setdefault(chave, {"url": it.get("url"), "achados": []})["achados"] += achados
    return fora


def coletar_por_busca(uf: str, desde: str, ate: str, cfg: dict, registro: dict) -> dict:
    """Canal 2 onde o diário tem busca e não edição por data (HANDOVER_ROTAS_DOE §0.2): os termos de
    declaração na busca do próprio diário, pelo adaptador do canal 1 (`coletar_doe.itens_da_busca`)."""
    import coletar_doe
    from coletores_base import MuroDeRobo, gravar, hoje_editorial, ler, log_busca, registrar_lacuna
    hoje = hoje_editorial().strftime("%d/%m/%Y")
    ad, base = cfg["adaptador"], cfg.get("url") or coletar_doe.HOSTS_APIFRONT.get(uf)
    termos = tuple(TERMOS_DE_DECLARACAO)
    busca = {"adaptador": ad, "desde": desde, "ate": ate, "em": hoje, "termos_versao": VERSAO_DOS_TERMOS}
    itens = []
    try:
        itens, busca["totais"] = coletar_doe.itens_da_busca(uf, ad, base, desde, ate, termos=termos)
    except Exception as e:  # noqa: BLE001 — falha da busca é lacuna desta UF, nunca "sem achado"
        codigo = getattr(e, "code", None) or 0
        if isinstance(e, MuroDeRobo) or codigo in (401, 403, 429, 451):
            registro["canal2"] = {"modo": MODO_SEM_ACESSO, "em": hoje, "conta_como_consultado": False,
                                  "motivo": f"{'muro de robô' if isinstance(e, MuroDeRobo) else f'HTTP {codigo}'} na busca do diário — recusa respeitada"}
        busca["erro"] = f"busca do diário falhou: {type(e).__name__}: {str(e)[:120]}"
        registrar_lacuna(f"DOE-{uf} (canal 2)", busca["erro"], canal="DOE", camada=1)
    t = busca.get("totais") or {}
    if t.get("_truncado") or t.get("_nao_baixadas"):
        busca["parcial"] = (f"leitura parcial: teto da busca em {', '.join(t.get('_truncado') or [])}" if t.get("_truncado")
                            else f"{t['_nao_baixadas']} edição(ões) apontada(s) pela busca não baixada(s)")
    sem_data = sum(1 for it in itens if not it.get("data"))
    if sem_data:
        busca["parcial"] = f"{sem_data} página(s) da busca sem data"
    indice = ler(INDICE, {}) or {}
    novas = ocorrencias_da_busca(itens)
    indice.setdefault("ufs", {}).setdefault(uf, {}).update(novas)
    busca["acertos_de_declaracao"] = len(novas)
    registro["busca_declaracao"] = busca
    registro.setdefault("_governanca", GOVERNANCA_CANAL2)
    if (registro.get("canal2") or {}).get("modo") != MODO_SEM_ACESSO:
        registro["canal2"] = {"modo": "busca_no_diario", "em": hoje,
                              "conta_como_consultado": not (busca.get("erro") or busca.get("parcial"))}
    registro["atualizado_em"] = indice["atualizado_em"] = hoje
    (RAIZ / "data" / PASTA).mkdir(parents=True, exist_ok=True)
    arquivo = f"{PASTA}/{uf}.json"
    gravar(arquivo, registro)
    gravar(INDICE, indice)
    decisao = "erro" if busca.get("erro") else ("pista" if novas else "consultado sem achado")
    log_busca("DOE", 1, list(termos), decisao, nivel="estadual", uf=uf, n_resultados=len(novas),
              resultados=f"canal 2 em {uf}: busca do diário ({ad}) de {desde} a {ate}, "
                         f"{len(itens)} página(s), {len(novas)} com termo de declaração")
    print(f"  {uf}: busca {ad} · {len(itens)} página(s), {len(novas)} com declaração"
          + (f" · {busca.get('erro') or busca.get('parcial')}" if busca.get("erro") or busca.get("parcial") else ""))
    return {"uf": uf, "modo": "busca_no_diario", "lidas": len(itens), "com_termo": len(novas), "decisao": decisao}


def _levanta(fn) -> bool:
    try:
        fn()
    except Exception:  # noqa: BLE001
        return True
    return False


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
    ok("o padrão de RO é o nome lido na página inicial",
       endereco_da_data(PADROES["RO"]["padrao"], "2026-09-10")
       == "https://diof.ro.gov.br/data/uploads/2026/09/DOE-10-09-2026.pdf")
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
    sem = {"canal2": {"modo": MODO_SEM_ACESSO, "motivo": "HTTP 403 na edição — recusa respeitada"}}
    ok("UF sem rota é 'rota não descoberta' com o motivo medido, e não recusa",
       situacao_do_canal2("XX", {}, {"XX": {"motivo": "SPA sem API"}}) ["modo"] == MODO_SEM_ROTA
       and situacao_do_canal2("XX", {}, {"XX": {"motivo": "SPA sem API"}})["detalhe"] == "SPA sem API")
    ok("adaptador de edição do canal 1 dá edição por data no canal 2",
       situacao_do_canal2("XX", {}, {"XX": {"adaptador": "edicao_ce"}})["modo"] == "edicao_por_adaptador")
    ok("todo adaptador de busca do canal 1 dá busca no diário",
       all(situacao_do_canal2("XX", {}, {"XX": {"adaptador": a}})["modo"] == "busca_no_diario"
           for a in ("apifront", "dodf", "busca_sp", "busca_to", "busca_ac")))
    ok("recusa medida vence o adaptador, e não conta como consultado",
       situacao_do_canal2("XX", {}, {"XX": {"adaptador": "apifront"}}, sem)["modo"] == MODO_SEM_ACESSO)
    ok("rota não descoberta registrada não esconde o adaptador que existe",
       situacao_do_canal2("XX", {}, {"XX": {"adaptador": "dodf"}},
                          {"canal2": {"modo": MODO_SEM_ROTA, "motivo": "404"}})["modo"] == "busca_no_diario")

    class _Muro(Exception):
        pass

    def _erro(codigo):
        e = Exception(f"HTTP {codigo}")
        e.code = codigo
        return e

    def _fonte(respostas):
        def fn(url, timeout=None):
            r = respostas[url]
            if isinstance(r, Exception):
                raise r
            return r
        return fn
    ok("404 passa à alternativa seguinte",
       _baixar([("a", None), ("b", None)], _fonte({"a": _erro(404), "b": b"pdf"}), _Muro) == ("b", b"pdf"))
    ok("403 levanta: recusa não se contorna com a alternativa seguinte",
       _levanta(lambda: _baixar([("a", None), ("b", None)], _fonte({"a": _erro(403), "b": b"pdf"}), _Muro)))
    ok("PDF já baixado pelo adaptador não se baixa de novo",
       _baixar([("a", b"pronto")], _fonte({}), _Muro) == ("a", b"pronto"))
    ok("sem alternativa que responda, levanta (nunca devolve vazio)",
       _levanta(lambda: _baixar([("a", None)], _fonte({"a": _erro(404)}), _Muro)))

    paginas_busca = [
        {"data": "2026-09-10", "url": "u1", "pagina": 3, "trechos": [
            "DECRETO Nº 9, DE 9 DE SETEMBRO DE 2026. O GOVERNADOR DO ESTADO declara situação de "
            "emergência em saúde pública em razão da epidemia de dengue."]},
        {"data": "2026-09-10", "url": "u2", "trechos": ["Institui o COE de Emergência em Saúde Pública."]},
        {"data": "2026-09-11", "url": "u3", "trechos": ["Declara situação de emergência em saúde pública."]}]
    oc_busca = ocorrencias_da_busca(paginas_busca)
    ok("a busca indexa só a página com declaração no contexto exigido",
       sorted(oc_busca) == ["2026-09-10", "2026-09-11"] and oc_busca["2026-09-10"]["url"] == "u1"
       and oc_busca["2026-09-10"]["achados"][0]["pagina"] == 3)
    ok("duas páginas com declaração na mesma data viram duas chaves, e nenhuma se perde",
       sorted(ocorrencias_da_busca(paginas_busca[:1] + [dict(paginas_busca[0], url="u9")])) == ["2026-09-10", "2026-09-10#2"])
    b_ok = {"canal2": {"modo": "busca_no_diario"}, "busca_declaracao": {
        "desde": INICIO_DO_CICLO, "ate": "2026-10-17", "em": "17/10/2026", "termos_versao": VERSAO_DOS_TERMOS, "acertos_de_declaracao": 0}}
    ad = {"XX": {"adaptador": "dodf"}}
    ok("busca do diário com os termos desde o início do ciclo conta como consultada",
       busca_de_declaracao("XX", b_ok, ad) == {"consultado_em": "17/10/2026", "acertos": 0})
    ok("busca que não rodou, que falhou, começou tarde, parou antes do dia ou bateu no teto é lacuna",
       all("lacuna" in busca_de_declaracao("XX", r, ad) for r in (
           {}, {"busca_declaracao": dict(b_ok["busca_declaracao"], erro="falhou")},
           {"busca_declaracao": dict(b_ok["busca_declaracao"], ate="2026-09-30")},
           {"busca_declaracao": dict(b_ok["busca_declaracao"], desde="2026-09-01")},
           {"busca_declaracao": dict(b_ok["busca_declaracao"], parcial="teto")})))
    ok("a lacuna diz se é recusa ou rota não descoberta",
       busca_de_declaracao("XX", sem, {})["lacuna"].startswith(MODO_SEM_ACESSO)
       and busca_de_declaracao("XX", {}, {})["lacuna"].startswith(MODO_SEM_ROTA))

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
    ok("metade estadual só conta com todas as edições relidas",
       "lacuna" in busca_de_declaracao("PB", {"edicoes": {"d": lida}}, {})
       and busca_de_declaracao("PB", {"edicoes": {"d": dict(lida, termos_versao=VERSAO_DOS_TERMOS)}}, {})
       == {"consultado_em": "02/10/2026", "edicoes_lidas": 1})
    ok("UF sem rota é lacuna da metade estadual", "lacuna" in busca_de_declaracao("XX", {}, {}))

    fonte = pathlib.Path(__file__).read_text(encoding="utf-8")
    escritas = [l.strip() for l in fonte.splitlines() if l.strip().startswith("gravar(")]
    # A edição por data e a busca escrevem o mesmo registro por UF, e por isso a conta é "toda
    # escrita é do registro da UF ou do índice" — e não um número fixo de linhas.
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

    if "--relatorio" in sys.argv:
        from coletores_base import ler
        adaptadores = (ler("fontes_doe.json", {}) or {}).get("ufs") or {}
        from coletar_saude_estadual import UFS
        contagem = {}
        for uf in UFS:
            reg = ler(f"{PASTA}/{uf}.json", {}) or {}
            sit = situacao_do_canal2(uf, None, adaptadores, reg)
            lidas = sum(1 for e in (reg.get("edicoes") or {}).values()
                        if isinstance(e, dict) and e.get("decisao") == "lida")
            com_termo = sum(1 for e in (reg.get("edicoes") or {}).values()
                            if isinstance(e, dict) and e.get("termos_achados"))
            contagem[sit["modo"]] = contagem.get(sit["modo"], 0) + 1
            dec = busca_de_declaracao(uf, reg, adaptadores)
            print(f"  {uf}: {sit['modo']} · {sit['detalhe'][:70]}"
                  + (f" · {lidas} edição(ões) lida(s), {com_termo} com termo" if lidas else "")
                  + f" · declaração: {dec.get('consultado_em') or dec.get('lacuna', '')[:80]}")
        print("  —")
        for modo, n in sorted(contagem.items(), key=lambda x: -x[1]):
            print(f"  {modo}: {n} unidade(s)")
        return 0

    def arg(nome, padrao=None):
        return sys.argv[sys.argv.index(nome) + 1] if nome in sys.argv else padrao

    desde = arg("--desde", INICIO_DO_CICLO)
    ate = arg("--ate", hoje_editorial().isoformat())
    if "--recuperacao" in sys.argv:
        # Toda UF com rota; a busca (barata) antes da edição inteira por data.
        from coletores_base import ler
        from coletar_saude_estadual import UFS
        adaptadores = (ler("fontes_doe.json", {}) or {}).get("ufs") or {}
        sits = [situacao_do_canal2(uf, None, adaptadores, ler(f"{PASTA}/{uf}.json", {}) or {}) for uf in UFS]
        alvos = [s["uf"] for m in ("busca_no_diario", "padrao_por_data", "edicao_por_adaptador")
                 for s in sits if s["modo"] == m]
    else:
        uf = arg("--uf")
        if not uf:
            print("uso: --uf <UF>[,<UF>] | --recuperacao | --relatorio | --autoteste")
            return 2
        alvos = uf.upper().split(",")

    print(f"canal 2 · {len(alvos)} UF(s) de {desde} a {ate}")
    for uf in alvos:
        try:
            coletar_uf(uf, desde, ate)
        except Exception as e:  # noqa: BLE001 — uma UF que cai não leva as seguintes; o registro dela fica como estava
            print(f"  {uf}: ✗ {type(e).__name__}: {str(e)[:160]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
