#!/usr/bin/env python3
"""Aplica no banco as promoções do juiz automático — Etapa 7, com rede de proteção.

Item 1 do bloco das 19:50 de 28/09/2026 (decisão da central). Não é decisão nova: é a Etapa 7 do
handover do juiz, decidida pela editoria em 27/09 — o juiz promove quando **todos** os critérios
passam sobre o documento primário.

O QUE FALTAVA
-------------
O juiz gravava `promove: true` em `data/promocoes_automaticas.json` e **nada lia aquele campo**.
Quem aplicava no banco era `julgar_e_aplicar_descobertas.py`, que só olha pistas de imprensa com
status `pendente_confirmacao_documento`. O veredito do codebook morria no arquivo.

A SEQUÊNCIA, E O QUE A PROTEGE
------------------------------
  backup em memória → aplica → `recalcular_mare.py --write` → suíte de portões
  portão vermelho → restaura os bytes originais e devolve a pista com o erro escrito

A rede de proteção é a mesma de `julgar_e_aplicar_descobertas.py`, testada desde 31/08/2026: ela
guarda também `recalcular_mare.py` e as páginas que a aplicação estadual toca, porque reverter pela
metade é pior que não aplicar.

SÓ A VERSÃO EM VIGOR DO CODEBOOK
--------------------------------
Aplica apenas vereditos cujo `codebook` é o em vigor e que não estejam superados. Em 28/09/2026 a
regra frouxa de objeto ex-ante promoveu **quatro registros falsos de cinco** (§286); eles ficaram no
arquivo, marcados como superados, e esta trava é o que impede que voltem pelo caminho novo.

PROVENIÊNCIA
------------
Cada registro aplicado carrega `hash_evidencia`, `url`, `data`, `categoria`, o `pista_id` e a versão
do codebook. Os critérios com trecho ficam em `promocoes_automaticas.json`, ligados pelo `pista_id`
— é esse par que a auditoria amostral semanal lê. Errata humana reverte com uma linha: basta apagar
o registro do banco; a decisão continua no registro, dizendo o que foi feito e por quê.

USO
  python3 aplicar_promocoes_do_juiz.py                 # relatório, nada escrito
  python3 aplicar_promocoes_do_juiz.py --aplicar
  python3 aplicar_promocoes_do_juiz.py --autoteste
"""
import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

REGISTRO = RAIZ / "data" / "promocoes_automaticas.json"
MUNICIPIOS = RAIZ / "data" / "municipios.json"
PONTOS = RAIZ / "data" / "pontos_mapa.json"


def dominio_divergente(veredito: dict, dono) -> bool:
    """O documento está em domínio oficial de OUTRO município? Função pura dado o dono.

    09/10/2026 (A1-01). Três dos trinta vereditos que promoveram no registro creditam município
    que não é o dono do domínio do documento:

        Candeias/MG     ← prefeitura.candeias.ba.gov.br   (outra UF)
        Rio do Oeste/SC ← defesacivil.taio.sc.gov.br      (o plano é de Taió)
        Santa Rosa/RS   ← trindadedosul.rs.gov.br         (o plano é de Trindade do Sul)

    O domínio é prova mais forte que um nome no meio do texto, e o corretor de atribuição já
    reatribui a pista antes de julgar. Esta é a rede: aplicar no banco um par que o próprio
    domínio contradiz grava registro falso, e registro falso pontua.

    Host que não resolve município nenhum (diário consorciado, domínio federal, armazenamento)
    devolve `None` e não decide nada aqui — quem cuida disso são as etapas 0 e 3 do codebook.
    """
    if not dono:
        return False
    nome = str(veredito.get("municipio") or "").strip().lower()
    uf = str(veredito.get("uf") or "").strip().upper()
    return (str(dono.get("uf") or "").upper() != uf
            or str(dono.get("nome") or "").strip().lower() != nome)


def data_da_edicao(data):
    """A data da edição do plano: dd/mm/aaaa exata; mm/aaaa, último dia do mês (convenção de
    `verificar_vigencia.parse_data_br`); só o ano, 31/12 desse ano. None se não há data. Função pura."""
    import datetime
    from verificar_vigencia import parse_data_br
    texto = str(data or "")
    iso = re.fullmatch(r"\s*(\d{4})-(\d{2})-(\d{2})\s*", texto)
    if iso:
        return datetime.date(*map(int, iso.groups()))
    d = parse_data_br(texto)
    anos = re.findall(r"(?<!\d)((?:19|20)\d{2})(?!\d)", texto) if d is None else []
    return d or (datetime.date(int(max(anos)), 12, 31) if anos else None)


def atualizacao_anual_localizada(data):
    """A edição datada é de 29/06/2025 em diante (12 meses antes do Boletim nº 1, `juiz.BOLETIM_1`)? True/False;
    None sem data. Campo DESCRITIVO (editoria, 10/11/2026): a Lei 12.340/2010, art. 3º-A, §6º, pede atualização
    anual, mas não diz que o plano perde validade — nada aqui grava "vencido". Função pura."""
    import datetime
    from juiz import BOLETIM_1
    d, inicio = data_da_edicao(data), datetime.datetime.strptime(BOLETIM_1, "%d/%m/%Y").date()
    return None if d is None else d >= inicio.replace(year=inicio.year - 1)


ROTULO_SEM_ATUALIZACAO = "sem atualização anual localizada (Lei 12.340, art. 3º-A, § 6º)"
# 17/11/2026 (editoria: "deixar indicado que é um plano desatualizado segundo a lei, valendo para todos os estados e
# municípios e pontuando zero"): a regra que era só do repositório estadual vale para todo plano de município
# indicado ao cadastro do art. 3º-A. O plano entra no banco, aparece na ficha com a marca e vale zero no índice.
PLANOS_DA_LEI = ("plano", "plano_antigo", "plano_nomeado")
# Na ficha, a lei por extenso: o "§" é marca de seção da Metodologia, e o portão de jargão o recusa em dado exibido.
# A mesma frase do MARÉ Saúde para o plano estadual com período encerrado.
MARCA_ENCERRADO = "último plano localizado com vigência encerrada"
MARCA_DESATUALIZADO = ("plano desatualizado segundo a lei: sem atualização anual localizada "
                       "(Lei 12.340/2010, art. 3º-A, parágrafo 6º)")


def desatualizado_pela_lei(categoria, data, ibge, cadastro) -> bool:
    """Plano de município indicado ao cadastro do art. 3º-A cuja edição é anterior a 29/06/2025? Sem data
    identificável, não (data insuficiente para o cômputo). Função pura dado o cadastro."""
    return (categoria in PLANOS_DA_LEI and str(ibge or "") in cadastro
            and atualizacao_anual_localizada(data) is False)


def vigencia_encerrada_no_ciclo(periodo, data) -> bool:
    """O período que o plano declara ("2024-2025") terminou antes do ciclo, e a edição não é do fim dele?
    Editoria, 15/11/2026 (vale zero) e 20/11/2026 (na dúvida, não encerra): a edição datada, com mês, no segundo
    semestre do último ano do período é a atualização para a estação seguinte (Vitória/ES, "Verão 2024/2025,
    1ª atualização", de 10/2025). Data só com o ano não mostra isso, e o plano fica encerrado. Função pura."""
    import datetime
    fim = int(str(periodo or "0")[-4:] or 0)
    if not fim:
        return False
    d = data_da_edicao(data) if re.search(r"\d{1,2}[/-]\d{4}|\d{4}-\d{2}", str(data or "")) else None
    return not (d and d >= datetime.date(fim, 7, 1))


def faixa_de_idade(categoria, data, ibge, cadastro, periodo=None):
    """A categoria que a idade do plano dá ao índice, ou None quando ele conta pela própria (editoria,
    20/11/2026; idade contada do Boletim nº 1). Vigência declarada encerrada: `plano_com_vigencia_encerrada`
    (zero). Município indicado ao cadastro do art. 3º-A com edição de mais de um ano: `plano_desatualizado`
    (zero, a regra de 17/11). Fora do cadastro, edição de mais de dois anos: `plano_de_mais_de_2_anos` (0,65).
    Sem data identificável, None. Função pura dado o cadastro."""
    import datetime
    from juiz import BOLETIM_1
    if categoria in ("plano", "plano_antigo") and vigencia_encerrada_no_ciclo(periodo, data):
        return "plano_com_vigencia_encerrada"
    if desatualizado_pela_lei(categoria, data, ibge, cadastro):
        return "plano_desatualizado"
    d = data_da_edicao(data) if categoria in ("plano", "plano_antigo") else None
    inicio = datetime.datetime.strptime(BOLETIM_1, "%d/%m/%Y").date()
    return "plano_de_mais_de_2_anos" if d and d < inicio.replace(year=inicio.year - 2) else None


def marcar_desatualizados(municipios: list, codigo_de, cadastro) -> int:
    """Põe ou tira a marca na ficha de cada registro, conforme a regra; devolve quantos mudaram. A marca de
    plano sem ato de aprovação, quando há, continua junto."""
    mudou = 0
    for m in municipios:
        marcas = [x for x in str(m.get("marca_na_ficha") or "").split(" · ") if x and x != MARCA_DESATUALIZADO]
        marcas = [x for x in marcas if not x.startswith(MARCA_ENCERRADO)]
        if m.get("categoria") in ("plano", "plano_antigo") and vigencia_encerrada_no_ciclo(
                m.get("vigencia_declarada_encerrada"), m.get("data")):
            marcas.append(f"{MARCA_ENCERRADO} ({m['vigencia_declarada_encerrada']})")
        elif desatualizado_pela_lei(m.get("categoria"), m.get("data"), codigo_de(m), cadastro):
            marcas.append(MARCA_DESATUALIZADO)
        nova = " · ".join(marcas) or None
        if nova != m.get("marca_na_ficha"):
            if nova:
                m["marca_na_ficha"] = nova
            else:
                m.pop("marca_na_ficha", None)
            mudou += 1
    return mudou


def marcar_planos_da_saude(municipios: list, texto_da_copia) -> int:
    """Marca `plano_da_saude` ({fonte}) no registro de plano cuja cópia preservada é um plano da saúde (`juiz.plano_da_saude`),
    e tira a marca de quem deixou de ser; devolve quantos mudaram. `texto_da_copia(hash)` dá o texto ou "". Não muda
    categoria nem índice (editoria, 23/11/2026): o cartão diz o que a fonte disponibilizou."""
    from atualizar_instrumentos_estaduais import REPOSITORIOS, repositorio_do_documento
    from juiz import plano_da_saude
    mudou = 0
    for m in municipios:
        h, url = m.get("hash_evidencia"), m.get("url") or ""
        uf_rep = repositorio_do_documento(url)
        nova = ({"fonte": REPOSITORIOS[uf_rep]["fonte"] if uf_rep else re.sub(r"^www\.", "", url.split("/")[2] if "//" in url else url)}
                if m.get("categoria") in CATEGORIAS_DE_PLANO + ("plano_novo", "plano_readaptado", "plano_recorrente")
                and h and plano_da_saude(texto_da_copia(h)) else None)
        if nova != m.get("plano_da_saude"):
            if nova:
                m["plano_da_saude"] = nova
            else:
                m.pop("plano_da_saude", None)
            mudou += 1
    return mudou


def texto_da_copia_preservada(h: str) -> str:
    """Texto da cópia preservada (camada de texto, ou o OCR), ou ""."""
    for nome in (f"{h}.txt", f"{h}.ocr.txt"):
        f = RAIZ / "evidencias" / nome
        if f.exists():
            return f.read_text(encoding="utf-8", errors="replace")
    return ""


def municipios_do_cadastro() -> set:
    """IBGE dos municípios INDICADOS pela União ao cadastro do art. 3º-A (`cadastro_casa_civil_2086`); a lista
    de inscritos não tem fonte pública (`cadastro_nacional_art3A` é null em todos)."""
    from coletores_base import ler
    return {str(m.get("codigo_ibge")) for m in ((ler("cadastro_prioritarios_federal.json") or {}).get("municipios")
                                                or {}).values() if m.get("cadastro_casa_civil_2086")}


def aplicaveis(decisoes: list, versao: str, resolver=None, cadastro=None) -> list:
    """Vereditos que promovem, na versão em vigor, ainda não aplicados nem superados.

    09/10/2026 (A1-29): `nao_aplicado` também exclui — a marca existe para dizer que a decisão
    não vai ao banco, e sem o filtro Taió tinha três decisões vivas para a mesma URL.
    09/10/2026 (A1-01): veredito cujo domínio aponta outro município não é aplicável.
    10/11/2026: no repositório estadual o veredito ganha três campos descritivos — `data_da_edicao`,
    `indicado_ao_cadastro_art3A`, `atualizacao_anual_localizada`. Dois sinais da editoria, desligados:
    `contar_so_com_atualizacao_anual` (indicado sem atualização anual localizada fica fora da contagem) e
    `aplicar_no_banco` (False retém o repositório inteiro, sem marca, até a editoria ver a simulação).
    """
    if resolver is None:
        from scripts.municipio_do_dominio import municipio_de as resolver
    from atualizar_instrumentos_estaduais import REPOSITORIOS, repositorio_do_documento
    fora, retidos, sem_atualizacao = [], 0, 0
    for v in decisoes:
        if not (v.get("promove") and v.get("codebook") == versao):
            continue
        # a abstenção da regra antiga ("atualização não se presume") volta uma vez, para a regra nova decidir
        if v.get("superada_por") or v.get("aplicado_em") or (
                v.get("nao_aplicado") and (v["nao_aplicado"] is True or not (
                    v["nao_aplicado"].get("motivo") == ABSTENCAO_ANTIGA
                    or str(v["nao_aplicado"].get("motivo") or "").startswith(LIMITE_NOSSO)))):
            continue
        if cadastro is None:
            cadastro = municipios_do_cadastro()
        v["data_da_edicao"] = str(data_da_edicao(v.get("data")) or "") or None
        v["indicado_ao_cadastro_art3A"] = str(v.get("ibge")) in cadastro
        v["atualizacao_anual_localizada"] = atualizacao_anual_localizada(v.get("data"))
        if desatualizado_pela_lei(v.get("categoria"), v.get("data"), v.get("ibge"), cadastro):
            v["rotulo_contagem"] = ROTULO_SEM_ATUALIZACAO   # entra no banco com a marca e vale zero no índice
            sem_atualizacao += 1
        repo = repositorio_do_documento(v.get("url") or "")
        if repo:
            if REPOSITORIOS[repo].get("aplicar_no_banco") is False:
                retidos += 1
                continue
        if dominio_divergente(v, resolver(v.get("url") or "")):
            print(f"   ! nao aplicado: {v.get('municipio')}/{v.get('uf')} — o documento esta em "
                  f"dominio oficial de outro municipio")
            continue
        fora.append(v)
    if retidos or sem_atualizacao:
        print(f"   {sem_atualizacao} plano(s) de município indicado ao cadastro sem atualização anual localizada "
              f"(entram com a marca e valem zero); {retidos} retida(s) pelo sinal `aplicar_no_banco`")
    return fora


def no_banco(municipios: list, nome: str, uf: str):
    """O registro do município no banco, ou None. Um município tem um registro só."""
    n, u = str(nome or "").strip().lower(), str(uf or "").strip().upper()
    return next((m for m in municipios if str(m.get("nome", "")).strip().lower() == n
                 and str(m.get("uf", "")).strip().upper() == u), None)


def ja_no_banco(municipios: list, nome: str, uf: str) -> bool:
    return no_banco(municipios, nome, uf) is not None


# 15/11/2026 (editoria: "decida você"): até aqui, município com registro nunca era atualizado ("atualização
# não se presume") — 172 municípios com documento aprovado pelo juiz e não aplicado, entre eles Rio das
# Ostras/RJ, com plano para o El Niño de 10/2026 e o registro parado num plano de 2024. A regra passa a
# ser a da não-regressão que a contribuição já usa (`processar_contribuicoes.FORCA`): entra o que é mais
# forte; na mesma categoria de plano, entra o documento POSTERIOR. O registro que sai fica em
# `registro_anterior`. Igual, mais fraco ou sem data comparável: nada muda.
JA_CONSTA = "já consta no banco — "
ABSTENCAO_ANTIGA = JA_CONSTA + "abstenção registrada (atualização não se presume)"
# 17/11/2026: "acima do limite de evidência" é limite da nossa guarda (o arquivo passa de 5 MB e o Wayback não
# lê pasta privada), não decisão sobre o caso; a marca enterrava 40 promoções. Como a falha de acesso, não marca,
# e a marca antiga volta para ser aplicada agora que a camada de texto é guardada.
LIMITE_NOSSO = ("documento não pôde ser preservado", "documento acima do limite de evidência")
CATEGORIAS_DE_PLANO = ("plano", "plano_antigo", "plano_elaboracao")
RE_MES_NO_ENDERECO = re.compile(r"/((?:19|20)\d{2})/(0[1-9]|1[0-2])/")


def quando(data, url=None) -> tuple:
    """(ano, mês, dia) do que a data diz, com 0 no que ela não diz; o mês do endereço (`/AAAA/MM/`)
    completa a data que só traz o ano, quando o ano é o mesmo. () quando não há ano. Função pura."""
    s = str(data or "")
    m = re.search(r"(?:(\d{1,2})[/-])?(?:(\d{1,2})[/-])?((?:19|20)\d{2})", s)
    if not m:
        return ()
    dia, mes, ano = (int(x) if x else 0 for x in m.groups())
    if not m.group(2) and m.group(1):       # "10/2025": o único número antes do ano é o mês
        dia, mes = 0, dia
    if not mes:
        e = RE_MES_NO_ENDERECO.search(str(url or ""))
        if e and int(e.group(1)) == ano:
            mes = int(e.group(2))
    return (ano, mes, dia)


def atualiza(existente: dict, v: dict) -> str:
    """Por que o veredito substitui o registro, ou '' quando não substitui. Função pura."""
    from processar_contribuicoes import FORCA
    atual, nova = existente.get("categoria"), v.get("categoria")
    if (existente.get("url") == v.get("url") and v.get("reabertura") and v.get("data") and nova in CATEGORIAS_DE_PLANO
            and atual in CATEGORIAS_DE_PLANO and (str(existente.get("data") or ""), atual) != (str(v["data"]), nova)):
        # 26/11/2026: o mesmo documento, relido a pedido, corrige a data (e a categoria que dela decorre) do registro.
        return f"data relida no documento ({existente.get('data')} → {v.get('data')})"
    if existente.get("url") == v.get("url") or nova not in FORCA or atual not in {**FORCA, "nao_verificado": 0}:
        return ""
    if FORCA[nova] > FORCA.get(atual, 0):
        return f"categoria mais forte ({atual} → {nova})"
    # 16/11/2026: registro que o juiz nunca julgou (sem `codebook`, anterior a 27/09; 84 planos) não segura o documento julgado de
    # força igual. Rio de Janeiro/RJ tinha "plano" apontando a página estadual, sem data comparável, e
    # a correção do leitor com o plano municipal nunca entraria.
    a, n = quando(existente.get("data"), existente.get("url")), quando(v.get("data"), v.get("url"))
    ate = min(len([x for x in a if x]), len([x for x in n if x])) if a and n else 0   # compara até onde as duas datas dizem
    # 18/11/2026: documento de força igual e edição ANTERIOR nunca substitui (Cachoeiro de Itapemirim e Pancas/ES:
    # PLANCON 2025 trocado pelo de 2023 e o índice do ES caiu de 58,3 para 56,6).
    if FORCA[nova] == FORCA.get(atual, 0) and ate and n[:ate] < a[:ate]:
        return ""
    if "codebook" not in existente and FORCA[nova] >= FORCA.get(atual, 0) and nova in CATEGORIAS_DE_PLANO:
        return "registro anterior sem julgamento do juiz"
    # 16/11/2026: o ato de aprovação achado depois completa o plano que entrou sem ele (Taió/SC).
    if atual == nova and nova in CATEGORIAS_DE_PLANO and existente.get("sem_ato_de_aprovacao") and not v.get("sem_ato_de_aprovacao"):
        return "ato de aprovação localizado"
    if atual == nova and nova in CATEGORIAS_DE_PLANO and ate and n[:ate] > a[:ate]:
        return f"documento posterior ({existente.get('data')} → {v.get('data')})"
    return ""


def a_retirar(decisoes: list, municipios: list, versao: str) -> list:
    """[(decisão, registro)] dos planos sem ato que saem do banco: o mesmo documento, relido a pedido (`reabertura`)
    pelo codebook em vigor, não informa a data (`data_nao_confirmada`). O plano continua no cartão como localizado
    e sem data (`gerar_card_municipios.planos_sem_contar`); o que sai é o registro que pontuava com um ano que o
    documento não diz (26/11/2026: 35 na medição nacional, 30 no RS). Função pura."""
    por_url = {m.get("url"): m for m in municipios
               if m.get("categoria") in CATEGORIAS_DE_PLANO and m.get("sem_ato_de_aprovacao") and m.get("url")}
    return [(v, por_url[v["url"]]) for v in decisoes
            if v.get("reabertura") and not v.get("promove") and v.get("motivo") == "data_nao_confirmada"
            and v.get("leu_documento") and v.get("codebook") == versao and not v.get("retirou")
            and v.get("url") in por_url and (por_url[v["url"]].get("nome"), por_url[v["url"]].get("uf")) == (v.get("municipio"), v.get("uf"))]


def preservar_o_documento(url: str, origem: str = "juiz_automatico"):
    """Preserva o documento do registro pela porta canônica e devolve o hash. None se não der.

    03/10/2026: o portão de evidências reprovou a primeira promoção do caminho novo — "1 de 93
    registro(s) pontuável(is) com URL sem evidência preservada — BLOQUEANTE". Estava certo: o juiz
    calcula o hash do TEXTO que julgou e, de propósito, **não preserva** (§: duas portas gravando a
    mesma chave é como se perde prova). Quem preserva é quem aplica — e no caminho do plano sem ato
    não havia ninguém antes, porque o documento não vinha de um coletor que já o tivesse baixado.

    A porta é `coletores_base.preservar_evidencia`, a mesma de todos os coletores: ela guarda o
    binário, indexa por sha256 em `data/evidencias.json` e pede snapshot ao Wayback acima do teto.
    Falha de rede devolve None, e aí a promoção não é aplicada — registro pontuável sem evidência
    é exatamente o que o portão existe para impedir.
    """
    if not url:
        return None
    try:
        from coletores_base import ler, preservar_evidencia
        # 24/10/2026: já preservado (índice + arquivo em disco) não se baixa de novo; sem isso a
        # passada interrompida pelo prazo refazia do zero os PDFs que já tinha guardado.
        for h, it in (ler("evidencias.json", {"itens": {}}).get("itens") or {}).items():
            if it.get("url") == url and prova_do_item(it):
                return h
        from julgar_e_aplicar_descobertas import obter_documento
        corpo = obter_documento(url, 60)   # o que o juiz leu: a fonte ou, se ela caiu, a cópia pública
        # o atalho `.url` do RS entrega o PDF de destino: a extensão vem dos bytes, não do nome
        ext = "pdf" if corpo[:5] == b"%PDF-" else (str(url).lower().split("?")[0].rsplit(".", 1)[-1] or "html")[:5]
        if ext not in ("pdf", "doc", "docx", "odt", "rtf", "html", "htm", "txt"):
            ext = "html"
        return preservar_evidencia(corpo, url, ext, origem)
    except Exception as e:  # noqa: BLE001
        print(f"   ! evidência não preservada ({type(e).__name__}): {str(e)[:90]}")
        return None


def prova_do_item(it: dict) -> bool:
    """Há prova preservada do documento? A mesma régua do portão 26 (`prova_preservada`): cópia binária,
    texto extraído ou captura datada do Wayback; a cópia binária indexada tem de existir em disco.
    24/10/2026: a régua própria daqui só via binário e snapshot, então o PDF do RS acima de 5 MB,
    já com texto preservado, seguia recusado."""
    from coletores_base import RAIZ
    from verificar_evidencias import prova_preservada
    return prova_preservada(it) and (not it.get("arquivo") or (RAIZ / it["arquivo"]).exists())


def tem_copia(h: str) -> bool:
    from coletores_base import ler
    return prova_do_item((ler("evidencias.json", {"itens": {}}).get("itens") or {}).get(h) or {})


def registro_do_veredito(v: dict, lat, lon, canal: str, fonte_base: str, hoje: str) -> dict:
    """O registro do banco, com a proveniência que permite conferir a decisão depois.

    `categoria` vem do veredito — não é fixa. A versão anterior deste caminho, em
    `julgar_e_aplicar_descobertas.py`, gravava sempre "plano", e um `plano_antigo` entraria como
    plano novo, mudando o que o índice conta."""
    registro = {
        "nome": v["municipio"], "uf": v["uf"], "categoria": v["categoria"],
        "documento": documento_do_veredito(v),
        "data": v.get("data"),
        # 08/11/2026: `fonte` é texto PÚBLICO (o cartão do município o exibe em "Onde o documento foi
        # localizado"). A proveniência interna — juiz, codebook, arquivo de critérios — vive nos campos
        # estruturados ao lado (`julgado_em`, `codebook`, `criterios`), nunca na frase.
        "fonte": f"{fonte_base} — ato lido em {hoje}",
        "url": v.get("url"), "lat": lat, "lon": lon, "canal": canal,
        "hash_evidencia": v.get("hash_evidencia"),
        "pista_id": v.get("pista_id"), "codebook": v.get("codebook"),
        "julgado_em": hoje, "criterios": "promocoes_automaticas.json",
    }
    # DECISÃO DA EDITORIA, 03/10/2026: o plano publicado sem ato de aprovação localizado conta no
    # degrau da leitura, **com a marca visível na ficha**. A marca é do REGISTRO, e não do texto da
    # fonte: quem lê a ficha precisa saber que o documento é o plano publicado e que o ato que o
    # aprova não foi localizado — e a marca sai quando o ato aparecer, numa rodada seguinte.
    if v.get("sem_ato_de_aprovacao"):
        registro["sem_ato_de_aprovacao"] = True
        registro["marca_na_ficha"] = "sem ato de aprovação localizado"
        registro["fonte"] = (f"{fonte_base} — plano publicado em domínio oficial do ente, lido em {hoje}; "
                             "ato de aprovação não localizado até o corte")
    # O registro diz, com a edição datada que a regra leu, se o plano está em dia com a lei (17/11/2026: todos).
    for campo in ("data_da_edicao", "indicado_ao_cadastro_art3A", "atualizacao_anual_localizada",
                  "vigencia_declarada_encerrada"):
        if campo in v:   # anotados por `aplicaveis`
            registro[campo] = v[campo]
    if v.get("rotulo_contagem") == ROTULO_SEM_ATUALIZACAO:
        registro["marca_na_ficha"] = " · ".join(x for x in (registro.get("marca_na_ficha"), MARCA_DESATUALIZADO) if x)
    return registro


RE_PROVENIENCIA_NA_FONTE = re.compile(
    r"lido e classificado (?:pelo juiz automático|automaticamente) em (\d{2}/\d{2}/\d{4}) \((?:codebook|§)[^)]*\)+"
    r"|;?\s*critérios em promocoes_automaticas\.json"
    r"|\s*—\s*revisar\b"
    r"|;\s*achado pela bateria negativa[^—]*?(\d{2}/\d{2}/\d{4})\s*—\s*julgamento.*$")
RE_FONTE_DE_PROCESSO = re.compile(r"^classificado automaticamente \((\d{2}/\d{2}/\d{4})\) a partir de (\S+)$")


def fonte_publica(fonte: str) -> str:
    """A frase pública de um registro antigo, sem a proveniência interna que o cartão e o PDF exibiam
    (08/11/2026: 'juiz automático', 'codebook', '§158', nome de arquivo, 'revisar'; e em
    atos_resposta.json 'classificado automaticamente (data) a partir de <url>'). Função pura."""
    m = RE_FONTE_DE_PROCESSO.match(fonte or "")
    if m:
        from julgar_e_aplicar_descobertas import canal_e_fonte
        return f"{canal_e_fonte(m.group(2))[1]} — lido em {m.group(1)}"
    def _troca(m):
        data = m.group(1) or m.group(2)
        return (f"lido em {data}" if m.group(1) else f", lido em {data}") if data else ""
    return RE_PROVENIENCIA_NA_FONTE.sub(_troca, fonte or "").strip()


RE_SUJEIRA = re.compile(r"P[áa]gina\s+\d+\s+de\s+\d+|o documento [ÉE] o instrumento|\.\.\.\.|……", re.IGNORECASE)
RE_FIM_DE_TITULO = re.compile(
    r"^(.*?(?:\d{4}(?:\s*[-/]\s*\d{2,4})?|-\s*[A-Z]{2}\b))", re.DOTALL)
RE_TITULO_DE_PLANO = re.compile(
    r"(PLANCON[^\n\r.;]{0,90}|PLANO\s+(?:MUNICIPAL\s+)?DE\s+CONTING[ÊE]NCIA[^\n\r.;]{0,90})",
    re.IGNORECASE)

def titulo_de_plano(texto: str) -> str:
    """O TÍTULO do plano, achado no texto — ou vazio.

    08/10/2026 (A1-06, A4-08). O campo `documento` da ficha vinha do trecho do objeto, e no
    caminho do "plano publicado em domínio oficial" não existe objeto nenhum: o trecho era sobra
    de página. A ficha publicou "o documento É o instrumento nomeado: tanhaém…", "neste Plano.
    11/08/2026 Página 3 de 72…" e "a Católica 8 1.5. INSTRUÇÕES PARA USO…".
    """
    m = RE_TITULO_DE_PLANO.search(" ".join(str(texto or "").split()))
    if not m:
        return ""
    titulo = " ".join(m.group(1).split()).strip(" -–:;,")
    # O título termina onde o documento o termina: no ano (ou no biênio) ou na sigla da UF. O que
    # vem depois é o texto da página seguinte — nome de assinante, número de item, cabeçalho — e
    # entrava no campo porque a janela do casamento é fixa.
    corte = RE_FIM_DE_TITULO.match(titulo)
    if not corte:
        # Sem ano e sem sigla de UF, não há onde o título termine: o que a janela pegou é meio de
        # frase ("Plano de Contingência decorre da operacionalização…"). Devolver isso seria
        # trocar uma sobra de página por outra. Quem chama cai na forma genérica, que é verdadeira.
        return ""
    titulo = corte.group(1).strip(" -–:;,")
    return titulo if len(titulo) >= 12 else ""


def documento_do_veredito(v: dict) -> str:
    """A ementa curta do ato — ou, no caminho do plano sem ato, o TÍTULO do documento.

    A ementa sai do trecho do objeto ex-ante (Etapa 4), que desde o §286 mostra o verbo e o
    instrumento juntos. Quando esse trecho não existe ou vem com sobra de página — marcador
    "Página N de M", frase interna do juiz, reticências de corte, minúscula inicial —, o campo
    passa a ser o título do documento, na forma aprovada "{Título} — {órgão}, {ano}".
    """
    objeto = ((v.get("criterios") or {}).get("4_natureza") or {}).get("objeto") or ""
    objeto = " ".join(str(objeto).split())
    if objeto and not RE_SUJEIRA.search(objeto) and not objeto[:1].islower():
        return objeto[:177] + "…" if len(objeto) > 180 else objeto
    for f in (objeto, v.get("trecho") or "", v.get("titulo") or ""):
        titulo = titulo_de_plano(f)
        if titulo:
            orgao = v.get("orgao") or (f"Prefeitura de {v['municipio']}" if v.get("municipio")
                                       else "")
            ano = str(v.get("data") or "")[-4:]
            cabeca = " — ".join([titulo] + ([orgao] if orgao else []))
            return f"{cabeca}, {ano}" if ano.isdigit() else cabeca
    # A forma genérica só vale quando o próprio texto PROVA que o documento é um plano de
    # contingência. Sem essa prova, nada de nome: vale a frase que diz o que se tem, que é a
    # classificação — inventar título é pior que não ter título.
    prova_de_plano = re.search(r"plano\s+de\s+conting[êe]ncia|PLANCON", objeto, re.IGNORECASE)
    if prova_de_plano and v.get("municipio"):
        ano = str(v.get("data") or "")[-4:]
        cauda = f", {ano}" if ano.isdigit() else ""
        return f"Plano de contingência municipal — Prefeitura de {v['municipio']}{cauda}"
    return documento_generico(v.get("categoria"), v.get("sem_ato_de_aprovacao"))


# 08/11/2026: `documento` também é texto público do cartão ("Localizamos …"). O rótulo da categoria é o
# mesmo da página inicial (CAT_ROTULO em assets/js/index.js); "juiz automático" e a chave interna da
# categoria não entram.
ROTULO_PUBLICO = {"plano": "plano de contingência", "plano_novo": "plano de contingência do ciclo",
                  "plano_readaptado": "plano de contingência readaptado", "plano_recorrente": "plano recorrente",
                  "plano_antigo": "plano de contingência vigente de ciclo anterior",
                  "plano_elaboracao": "plano em elaboração", "estrutura": "estrutura de coordenação"}


def documento_generico(categoria, sem_ato=False) -> str:
    """A frase pública quando o documento não tem título legível: diz o que foi localizado. Função pura.
    23/11/2026 (editoria): o plano publicado sem ato de aprovação localizado é plano, não "ato oficial"."""
    rotulo = ROTULO_PUBLICO.get(str(categoria), "documento de preparação")
    return rotulo[:1].upper() + rotulo[1:] if sem_ato else f"Ato oficial localizado: {rotulo}"


def autoteste() -> int:
    casos = []
    V = "1.1 (28/09/2026)"
    base = {"promove": True, "codebook": V, "municipio": "Serra", "uf": "ES",
            "categoria": "plano_antigo", "data": "30/12/2025", "url": "https://x.gov.br/a.pdf",
            "hash_evidencia": "h" * 64, "pista_id": "abc",
            "criterios": {"4_natureza": {"objeto": "Fica instituído o Plano Municipal de Proteção"}}}

    # 08/10/2026 (A1-06, A4-08): o campo `documento` é o título do documento, nunca sobra de
    # página. Os quatro casos abaixo são os quatro registros reais que a ficha publicou errado.
    _reg = [{"categoria": "plano_antigo", "hash_evidencia": "s", "url": ("https://rsgovbr-my.sharepoint.com/personal/casa-militar_casamilitar_rs_gov_br/Documents/Casa%20Militar/"
             "SUBCHEFIAS/SUBCHEFIA%20DE%20PROTE%C3%87%C3%83O%20E%20DEFESA%20CIVIL/3.%20Departamento%20de%20Gest%C3%A3o%20de"
             "%20Riscos/Divis%C3%A3o%20T%C3%A9cnica%20de%20Riscos/Planos%20de%20conting%C3%AAncia/TODOS%20PLANCONS%20RECEBIDOS"
             "/CREPDEC%2003/a.pdf")},
            {"categoria": "plano", "hash_evidencia": "d", "url": "https://www.x.gov.br/p.pdf", "plano_da_saude": {"fonte": "x"}},
            {"categoria": "decreto", "hash_evidencia": "s", "url": "https://y.gov.br/d.pdf"}]
    _txt = {"s": "Secretaria Municipal de Saúde PLANO DE CONTINGÊNCIA PARA CHUVAS INTENSAS",
            "d": "PLANO DE CONTINGÊNCIA. Coordenadoria Municipal de Defesa Civil aciona."}
    _n = marcar_planos_da_saude(_reg, lambda h: _txt.get(h, ""))
    casos.append(("plano da saúde ganha a marca com a fonte; quem deixou de ser perde; decreto não entra",
                  _n == 2 and "Prepara RS" in _reg[0]["plano_da_saude"]["fonte"] and "plano_da_saude" not in _reg[1]
                  and "plano_da_saude" not in _reg[2] and marcar_planos_da_saude(_reg, lambda h: _txt.get(h, "")) == 0))
    casos.append(("ementa limpa continua sendo a ementa",
                  documento_do_veredito(base) == "Fica instituído o Plano Municipal de Proteção"))
    casos.append(("marcador de página vira título com órgão e ano",
                  documento_do_veredito({"municipio": "Umuarama", "data": "2026", "criterios": {
                      "4_natureza": {"objeto": "neste Plano. 11/08/2026 Página 3 de 72 Plano de "
                                               "contingência do município de Umuarama - PR 1.2."}}})
                  == "Plano de contingência do município de Umuarama - PR — Prefeitura de "
                     "Umuarama, 2026"))
    casos.append(("frase interna do juiz vira o PLANCON do documento",
                  documento_do_veredito({"municipio": "Itanhaém", "data": "2024", "criterios": {
                      "4_natureza": {"objeto": "o documento É o instrumento nomeado: tanhaém "
                                               "Secretaria Municipal PLANCON PLANO DE CONTIGÊNCIA "
                                               "2024-2025 Tiago"}}})
                  == "PLANCON PLANO DE CONTIGÊNCIA 2024-2025 — Prefeitura de Itanhaém, 2024"))
    casos.append(("meio de frase sem ano nem UF cai na forma genérica, não em outra sobra",
                  documento_do_veredito({"municipio": "Celso Ramos", "data": "2022", "criterios": {
                      "4_natureza": {"objeto": "a Católica 8 1.5. INSTRUÇÕES PARA USO E "
                                               "ATUALIZAÇÃO DO PLANO A efetiva aplicação do "
                                               "Plano de Contingência decorre"}}})
                  == "Plano de contingência municipal — Prefeitura de Celso Ramos, 2022"))
    # 15/10/2026: a forma sem título começava em minúscula, e `verificar_documento_publicado.py`
    # barrou a publicação (Cubatão/SP, prova = relatório do BNDES).
    casos.append(("sem título nem prova de plano: a classificação, começando em maiúscula",
                  documento_do_veredito({"categoria": "plano_elaboracao", "criterios": {}})[:1]
                  == "A"))
    sem_dono = lambda _u: None            # noqa: E731 — resolvedor nulo, para as travas puras
    _plano = {"nome": "Serra", "uf": "ES", "categoria": "plano_antigo", "data": "2017", "url": "https://x.gov.br/a.pdf",
              "sem_ato_de_aprovacao": True}
    _rel = dict(base, reabertura="2026-11-26", sem_ato_de_aprovacao=True)
    casos.append(("o mesmo documento, relido a pedido, corrige a data do registro; sem o pedido, ou com a mesma data, não",
                  atualiza(_plano, dict(_rel, data="23/10/2025")) == "data relida no documento (2017 → 23/10/2025)"
                  and atualiza(_plano, dict(base, data="23/10/2025")) == ""
                  and atualiza(_plano, dict(_rel, data="2017")) == ""
                  and atualiza(_plano, dict(_rel, data=None)) == ""))
    _sem = {"reabertura": "2026-11-26", "promove": False, "motivo": "data_nao_confirmada", "leu_documento": True,
            "codebook": V, "url": "https://x.gov.br/a.pdf", "municipio": "Serra", "uf": "ES"}
    casos.append(("plano relido a pedido que não informa a data sai do banco; recusa antiga, outro motivo, outro município ou já retirado, não",
                  [r for _, r in a_retirar([_sem], [_plano], V)] == [_plano]
                  and a_retirar([{k: x for k, x in _sem.items() if k != "reabertura"}], [_plano], V) == []
                  and a_retirar([dict(_sem, motivo="fora_do_objeto")], [_plano], V) == []
                  and a_retirar([dict(_sem, municipio="Vitória")], [_plano], V) == []
                  and a_retirar([dict(_sem, retirou={"em": "x"})], [_plano], V) == []
                  and a_retirar([_sem], [dict(_plano, sem_ato_de_aprovacao=False)], V) == []))
    casos.append(("veredito da versão em vigor é aplicável",
                  len(aplicaveis([base], V, resolver=sem_dono)) == 1))
    # 09/10/2026 (A1-01): domínio de outro município derruba a aplicação.
    taio = {"nome": "Taió", "uf": "SC", "ibge": "4217808"}
    casos.append(("domínio de outro município não é aplicável",
                  aplicaveis([dict(base, municipio="Rio do Oeste", uf="SC")], V,
                             resolver=lambda _u: taio) == []))
    casos.append(("domínio do próprio município é aplicável",
                  len(aplicaveis([dict(base, municipio="Taió", uf="SC")], V,
                                 resolver=lambda _u: taio)) == 1))
    casos.append(("domínio que não resolve município não decide nada",
                  len(aplicaveis([base], V, resolver=sem_dono)) == 1))
    casos.append(("UF divergente com mesmo nome não é aplicável",
                  aplicaveis([dict(base, municipio="Candeias", uf="MG")], V,
                             resolver=lambda _u: {"nome": "Candeias", "uf": "BA"}) == []))
    # 09/10/2026 (A1-29): `nao_aplicado` exclui.
    casos.append(("veredito marcado nao_aplicado não volta ao banco",
                  aplicaveis([dict(base, nao_aplicado=True)], V, resolver=sem_dono) == []))
    casos.append(("veredito de versão anterior NÃO é aplicável",
                  aplicaveis([dict(base, codebook="1.0 (27/09/2026)")], V) == []))
    casos.append(("veredito superado NÃO é aplicável",
                  aplicaveis([dict(base, superada_por={"codebook": V})], V) == []))
    casos.append(("veredito já aplicado NÃO volta",
                  aplicaveis([dict(base, aplicado_em="2026-09-28")], V) == []))
    import atualizar_instrumentos_estaduais as _aie
    _rs = dict(base, data="05/2026", ibge="4300001",
               url="https://rsgovbr-my.sharepoint.com" + _aie.REPOSITORIOS["RS"]["pasta"] + "/CREPDEC 01/P.pdf")
    _cad, _fora = {"4300001"}, set()
    _sinais = dict(_aie.REPOSITORIOS["RS"])
    try:
        _aie.REPOSITORIOS["RS"]["aplicar_no_banco"] = False
        _retido = aplicaveis([dict(_rs)], V, resolver=sem_dono, cadastro=_cad) == []
        _aie.REPOSITORIOS["RS"]["aplicar_no_banco"] = True
        _velho = dict(_rs, data="05/2025")
        _entra = aplicaveis([_velho], V, resolver=sem_dono, cadastro=_cad)
        _livre = dict(_rs, data="2012")
        aplicaveis([_livre], V, resolver=sem_dono, cadastro=_fora)
        _sem_data = dict(_rs, data=None)
        aplicaveis([_sem_data], V, resolver=sem_dono, cadastro=_cad)
        _fora_do_repo = dict(base, data="2023", ibge="4300001", url="https://x.rs.gov.br/p.pdf")
        aplicaveis([_fora_do_repo], V, resolver=sem_dono, cadastro=_cad)
        _ok = aplicaveis([dict(_rs)], V, resolver=sem_dono, cadastro=_cad)
    finally:
        _aie.REPOSITORIOS["RS"].clear(); _aie.REPOSITORIOS["RS"].update(_sinais)
    casos.append(("repositório com aplicar_no_banco desligado fica retido, sem marca", _retido))
    casos.append(("vigência declarada encerrada vale zero; a edição datada no fim do período não encerra; só ano encerra",
                  faixa_de_idade("plano", "2025", "2", {"1"}, "2024-2025") == "plano_com_vigencia_encerrada"
                  and faixa_de_idade("plano", "10/2025", "2", {"1"}, "2024-2025") is None
                  and faixa_de_idade("plano", "10/12/2025", "2", {"1"}, "2024-2025") is None
                  and faixa_de_idade("plano_antigo", "15/03/2025", "2", {"1"}, "2024-2025") == "plano_com_vigencia_encerrada"
                  and faixa_de_idade("plano", "2026", "2", {"1"}, None) is None))
    _enc = [{"categoria": "plano", "data": "2025", "vigencia_declarada_encerrada": "2024-2025"}]
    casos.append(("vigência encerrada aparece na ficha com o período, e a marca não se repete",
                  marcar_desatualizados(_enc, lambda m: "9", set()) == 1
                  and _enc[0]["marca_na_ficha"] == MARCA_ENCERRADO + " (2024-2025)"
                  and marcar_desatualizados(_enc, lambda m: "9", set()) == 0))
    casos.append(("idade do plano: com risco e mais de 1 ano, desatualizado (zero); sem risco, só mais de 2 anos reduz; "
                  "sem data e até 1 ano contam pela categoria",
                  faixa_de_idade("plano_antigo", "30/06/2025", "1", {"1"}) is None
                  and faixa_de_idade("plano_antigo", "28/06/2025", "1", {"1"}) == "plano_desatualizado"
                  and faixa_de_idade("plano_antigo", "2020", "1", {"1"}) == "plano_desatualizado"
                  and faixa_de_idade("plano_antigo", "28/06/2025", "2", {"1"}) is None
                  and faixa_de_idade("plano", "2023", "2", {"1"}) == "plano_de_mais_de_2_anos"
                  and faixa_de_idade("plano_antigo", "2024", "2", {"1"}) is None
                  and faixa_de_idade("plano_antigo", None, "2", {"1"}) is None
                  and faixa_de_idade("estrutura", "2020", "2", {"1"}) is None))
    casos.append(("atualização anual localizada: de 29/06/2025 em diante (só ano = 31/12; mm/aaaa = último dia); "
                  "sem data, None",
                  atualizacao_anual_localizada("2025") is True and atualizacao_anual_localizada("2024") is False
                  and atualizacao_anual_localizada(None) is None and atualizacao_anual_localizada("28/06/2025") is False
                  and atualizacao_anual_localizada("29/06/2025") and atualizacao_anual_localizada("06/2025")
                  and atualizacao_anual_localizada("05/2025") is False and atualizacao_anual_localizada("2026-05-13")))
    casos.append(("17/11: indicado ao cadastro sem atualização ENTRA com o rótulo (vale zero no índice), em qualquer "
                  "canal; não indicado e sem data, sem rótulo; nada diz 'vencido'",
                  len(_entra) == 1 and _velho.get("rotulo_contagem") == ROTULO_SEM_ATUALIZACAO
                  and _velho.get("data_da_edicao") == "2025-05-31"
                  and _fora_do_repo.get("rotulo_contagem") == ROTULO_SEM_ATUALIZACAO
                  and "rotulo_contagem" not in _livre and "rotulo_contagem" not in _sem_data
                  and "vencido" not in json.dumps(_velho)))
    _marcados = [{"nome": "A", "uf": "RS", "categoria": "plano_antigo", "data": "2023"},
                 {"nome": "B", "uf": "RS", "categoria": "plano", "data": "2024", "marca_na_ficha": "sem ato de aprovação localizado"},
                 {"nome": "C", "uf": "RS", "categoria": "plano", "data": "2026"},
                 {"nome": "D", "uf": "RS", "categoria": "decreto", "data": "2020"}]
    _n = marcar_desatualizados(_marcados, lambda m: "4300001", _cad)
    casos.append(("a marca na ficha: só plano fora da atualização; junta-se à marca do ato; idempotente",
                  _n == 2 and _marcados[0]["marca_na_ficha"] == MARCA_DESATUALIZADO
                  and _marcados[1]["marca_na_ficha"] == "sem ato de aprovação localizado · " + MARCA_DESATUALIZADO
                  and "marca_na_ficha" not in _marcados[2] and "marca_na_ficha" not in _marcados[3]
                  and marcar_desatualizados(_marcados, lambda m: "4300001", _cad) == 0))
    _reg = registro_do_veredito(_ok[0], 0, 0, "orgao_estadual", "F", "10/11/2026") if _ok else {}
    _r_velho = registro_do_veredito(_velho, 0, 0, "orgao_estadual", "F", "17/11/2026")
    casos.append(("o registro leva os três campos descritivos que `aplicaveis` anotou, e a marca quando fora da lei",
                  _reg.get("data_da_edicao") == "2026-05-31" and _reg.get("indicado_ao_cadastro_art3A") is True
                  and _reg.get("atualizacao_anual_localizada") is True and "marca_na_ficha" not in _reg
                  and MARCA_DESATUALIZADO in str(_r_velho.get("marca_na_ficha"))
                  and "indicado_ao_cadastro_art3A" not in registro_do_veredito(
                      {k: v for k, v in base.items() if k not in ("data_da_edicao", "indicado_ao_cadastro_art3A",
                                                                  "atualizacao_anual_localizada")},
                      0, 0, "x", "F", "10/11/2026")))
    casos.append(("recusa nunca é aplicável",
                  aplicaveis([dict(base, promove=False)], V) == []))

    mun = [{"nome": "Serra", "uf": "ES"}]
    casos.append(("município já no banco é reconhecido", ja_no_banco(mun, "serra", "es")))
    _reg = {"categoria": "plano_antigo", "data": "2024", "url": "https://x.rj.gov.br/wp-content/uploads/2024/10/a.pdf", "codebook": V}
    casos.append(("registro atualiza por categoria mais forte, e nunca por mais fraca ou pelo mesmo documento",
                  atualiza(_reg, {"categoria": "plano", "data": "2026", "url": "https://x.rj.gov.br/b.pdf"}).startswith("categoria")
                  and atualiza(dict(_reg, categoria="plano"), {"categoria": "plano_antigo", "data": "2026", "url": "u"}) == ""
                  and atualiza(_reg, {"categoria": "plano", "data": "2026", "url": _reg["url"]}) == ""
                  and atualiza(dict(_reg, categoria="decreto"), {"categoria": "plano_antigo", "data": "2026", "url": "u"}) == ""))
    casos.append(("na mesma categoria de plano entra o documento posterior; data igual ou não comparável não troca",
                  atualiza(_reg, {"categoria": "plano_antigo", "data": "24/10/2025", "url": "u"}).startswith("documento posterior")
                  and atualiza(dict(_reg, data="02/07/2026"), {"categoria": "plano_antigo", "data": "2026", "url": "u"}) == ""
                  and atualiza(dict(_reg, data="2026"), {"categoria": "plano_antigo", "data": "EL NIÑO", "url": "u"}) == ""
                  and atualiza(dict(_reg, categoria="decreto", data="2025"), {"categoria": "decreto", "data": "2026", "url": "u"}) == ""))
    _jan, _ago = "https://d.sc.gov.br/wp-content/uploads/2026/01/p.pdf", "https://d.sc.gov.br/wp-content/uploads/2026/08/p.pdf"
    casos.append(("o mês do endereço completa a data que só traz o ano (Taió/SC: janeiro → agosto de 2026)",
                  quando("2026", _ago) == (2026, 8, 0) and quando("10/2025") == (2025, 10, 0) and quando("EL NIÑO") == ()
                  and atualiza({"categoria": "plano", "data": "2026", "url": _jan, "codebook": V}, {"categoria": "plano", "data": "2026", "url": _ago}) != ""
                  and atualiza({"categoria": "plano", "data": "2026", "url": _ago, "codebook": V}, {"categoria": "plano", "data": "2026", "url": _jan}) == ""))
    casos.append(("registro nunca julgado cede ao plano julgado de força igual; julgado não cede",
                  atualiza({"categoria": "plano", "data": "vigente", "url": "https://rj.gov.br/p"},
                           {"categoria": "plano", "data": "2025", "url": "https://rio/p.pdf"}) == "registro anterior sem julgamento do juiz"
                  and atualiza({"categoria": "plano", "data": "vigente", "url": "https://rj.gov.br/p", "codebook": V},
                               {"categoria": "plano", "data": "2025", "url": "https://rio/p.pdf"}) == ""
                  and atualiza({"categoria": "plano", "data": "vigente", "url": "u1"}, {"categoria": "plano_antigo", "data": "2024", "url": "u2"}) == ""))
    casos.append(("o ato de aprovação achado completa o plano que entrou sem ele; sem ato, não troca",
                  atualiza({"categoria": "plano", "data": "2026", "url": "u1", "codebook": V, "sem_ato_de_aprovacao": True},
                           {"categoria": "plano", "data": "2026", "url": "u2"}) == "ato de aprovação localizado"
                  and atualiza({"categoria": "plano", "data": "2026", "url": "u1", "codebook": V, "sem_ato_de_aprovacao": True},
                               {"categoria": "plano", "data": "2026", "url": "u2", "sem_ato_de_aprovacao": True}) == ""))
    casos.append(("limite da nossa guarda (acima de 5 MB) não enterra a promoção: ela volta",
                  len(aplicaveis([dict(base, nao_aplicado={"motivo": "documento acima do limite de evidência e sem cópia "
                                                                     "externa — registro pontuável exige evidência guardada (portão 26)"})],
                                 V, resolver=sem_dono)) == 1))
    def guarda_do_escaneado():
        """18/11/2026: PDF escaneado acima do limite, já no índice com texto de 0 caractere. O documento em mãos
        tem de chegar ao OCR; com prova de verdade, não se refaz nada."""
        import tempfile
        import coletores_base as cb
        corpo = b"%PDF-1.4 " + b"x" * 64
        h, lidos = cb.sha256(corpo), []
        banco = {"evidencias.json": {"itens": {h: {"url": "https://x.gov.br/a.pdf", "tamanho": len(corpo), "arquivo": None,
                                                   "wayback": "tentativa falhou (URLError)",
                                                   "texto_arquivo": f"evidencias/{h}.txt", "caracteres": 0}}}}
        salvo = cb.LIMITE_EVIDENCIA, cb.ler, cb.gravar, cb._texto_de_evidencia
        with tempfile.TemporaryDirectory():
            try:
                cb.LIMITE_EVIDENCIA = 16
                cb.ler = lambda nome, padrao=None: banco.get(nome, padrao)
                cb.gravar = lambda nome, obj, **k: banco.__setitem__(nome, obj)
                cb._texto_de_evidencia = lambda c, u, hh: (lidos.append(hh), {"ocr_arquivo": f"evidencias/{hh}.ocr.txt",
                                                                               "ocr_hash": "0" * 64, "ocr_caracteres": 900})[1]
                sem_prova = prova_do_item(banco["evidencias.json"]["itens"][h])
                cb.preservar_evidencia(corpo, "https://x.gov.br/a.pdf", "pdf", "autoteste")
                com_prova = prova_do_item(banco["evidencias.json"]["itens"][h])
                cb.preservar_evidencia(corpo, "https://x.gov.br/a.pdf", "pdf", "autoteste")
                return (sem_prova, com_prova, lidos)
            finally:
                cb.LIMITE_EVIDENCIA, cb.ler, cb.gravar, cb._texto_de_evidencia = salvo
    casos.append(("texto de 0 caractere não é prova: o escaneado acima do limite vai ao OCR, uma vez só",
                  (lambda r: r[0] is False and r[1] is True and len(r[2]) == 1)(guarda_do_escaneado())))
    def prova_pela_copia_publica():
        """18/11/2026: sete promoções lidas pela cópia pública (o endereço original dava 404) nunca entravam no
        banco: a guarda da prova só tentava o endereço original."""
        import urllib.error
        import coletores_base as cb
        import julgar_e_aplicar_descobertas as jd
        salvo, guardados = (cb.ler, cb.preservar_evidencia, jd.ler_documento, jd.copia_arquivada), []

        def caiu(url, timeout=40, origem=None):
            raise urllib.error.HTTPError(url, 404, "Not Found", None, None)
        try:
            cb.ler = lambda nome, padrao=None: padrao
            cb.preservar_evidencia = lambda corpo, url, ext, origem: (guardados.append((corpo, ext)), "h" * 64)[1]
            jd.ler_documento = caiu
            jd.copia_arquivada = lambda url: (b"%PDF-1.4 copia publica", "20261101")
            com = preservar_o_documento("https://x.gov.br/a.pdf")
            jd.copia_arquivada = lambda url: (None, None)
            return com, preservar_o_documento("https://x.gov.br/b.pdf"), guardados
        finally:
            cb.ler, cb.preservar_evidencia, jd.ler_documento, jd.copia_arquivada = salvo
    casos.append(("endereço que caiu: a prova é a cópia pública que o juiz leu; sem cópia pública, não há prova",
                  (lambda r: r[0] == "h" * 64 and r[1] is None and r[2] == [(b"%PDF-1.4 copia publica", "pdf")])(prova_pela_copia_publica())))
    casos.append(("plano de edição anterior nunca substitui o de força igual, nem o registro sem julgamento do juiz",
                  atualiza({"categoria": "plano", "data": "2025", "url": "u1"}, {"categoria": "plano", "data": "2023", "url": "u2"}) == ""
                  and atualiza({"categoria": "plano", "data": "2025", "url": "u1", "codebook": V},
                               {"categoria": "plano", "data": "2023", "url": "u2"}) == ""
                  and atualiza({"categoria": "plano", "url": "u1"}, {"categoria": "plano", "data": "2023", "url": "u2"})
                  == "registro anterior sem julgamento do juiz"))
    casos.append(("a abstenção da regra antiga volta uma vez; a da regra nova, não",
                  len(aplicaveis([dict(base, nao_aplicado={"motivo": ABSTENCAO_ANTIGA})], V, resolver=sem_dono)) == 1
                  and aplicaveis([dict(base, nao_aplicado={"motivo": JA_CONSTA + "mesmo documento, ou registro igual ou mais forte"})],
                                 V, resolver=sem_dono) == []))
    casos.append(("município ausente não é falso positivo", not ja_no_banco(mun, "Vitória", "ES")))

    r = registro_do_veredito(base, -20.1, -40.3, "DOM", "Diário oficial municipal", "28/09/2026")
    casos.append(("a categoria vem do veredito, não é fixa em 'plano'",
                  r["categoria"] == "plano_antigo"))
    casos.append(("o registro carrega hash, url e data",
                  r["hash_evidencia"] == "h" * 64 and r["url"].endswith("a.pdf")
                  and r["data"] == "30/12/2025"))
    casos.append(("o registro liga à decisão pelo pista_id e pelo codebook",
                  r["pista_id"] == "abc" and r["codebook"] == V))
    # 03/10/2026: a marca da decisão da editoria viaja do veredito para o registro, e é ela que a
    # ficha mostra. Registro sem a marca não pode ganhá-la por descuido, e com a marca não pode
    # perdê-la — os dois casos abaixo guardam as duas metades.
    r_marca = registro_do_veredito(dict(base, sem_ato_de_aprovacao=True), -1, -2, "c", "f", "01/01/2026")
    casos.append(("plano sem ato: o registro leva a marca para a ficha",
                  r_marca.get("sem_ato_de_aprovacao") is True
                  and r_marca.get("marca_na_ficha") == "sem ato de aprovação localizado"))
    casos.append(("plano sem ato: a fonte do registro diz que o ato não foi localizado",
                  "ato de aprovação não localizado até o corte" in r_marca["fonte"]))
    casos.append(("preservar_o_documento sem URL devolve None, e não quebra",
                  preservar_o_documento("") is None))
    casos.append(("plano COM ato não ganha a marca",
                  "sem_ato_de_aprovacao" not in r and "marca_na_ficha" not in r))
    # 08/11/2026: `fonte` é texto público do cartão; a proveniência fica nos campos estruturados.
    casos.append(("a fonte é pública: sem juiz, codebook ou nome de arquivo; a proveniência vai nos campos",
                  "juiz" not in r["fonte"] and ".json" not in r["fonte"] and "codebook" not in r["fonte"]
                  and r["julgado_em"] == "28/09/2026" and r["codebook"] == V and r["criterios"].endswith(".json")))
    casos.append(("fonte_publica limpa o registro antigo e mantém a data e a lacuna do ato",
                  fonte_publica("P (h) — plano publicado em domínio oficial do ente, lido e classificado pelo juiz "
                                "automático em 04/11/2026 (codebook 1.8 (30/10/2026)); ato de aprovação não "
                                "localizado até o corte; critérios em promocoes_automaticas.json")
                  == "P (h) — plano publicado em domínio oficial do ente, lido em 04/11/2026; ato de aprovação não localizado até o corte"
                  and fonte_publica("D (x) — ato lido e classificado pelo juiz automático em 03/10/2026 (codebook 1.3 (03/10/2026)); "
                                    "critérios em promocoes_automaticas.json") == "D (x) — ato lido em 03/10/2026"
                  and fonte_publica("Portal oficial (a) — plano") == "Portal oficial (a) — plano"
                  and fonte_publica("D (via Querido Diário) — ato lido e classificado automaticamente em 22/09/2026 (§158)")
                  == "D (via Querido Diário) — ato lido em 22/09/2026"
                  and fonte_publica("classificado automaticamente (13/10/2026) a partir de https://www.gov.br/mdr/x")
                  == "Portal oficial (www.gov.br) — lido em 13/10/2026"
                  and fonte_publica("Fonte não oficial (g1.globo.com) — revisar") == "Fonte não oficial (g1.globo.com)"
                  and fonte_publica("Fonte não oficial (x.sharepoint.com) — revisar — plano publicado em domínio oficial do ente, lido em 01/11/2026")
                  == "Fonte não oficial (x.sharepoint.com) — plano publicado em domínio oficial do ente, lido em 01/11/2026"
                  and fonte_publica("Agência Belém reproduzida por O Liberal; achado pela bateria negativa padronizada (§4.1.2) em 27/08/2026 — julgamento pelas regras (R7)")
                  == "Agência Belém reproduzida por O Liberal, lido em 27/08/2026"))
    casos.append(("sem título legível, o documento diz o que foi localizado, sem jargão nem chave interna",
                  documento_generico("plano_antigo") == "Ato oficial localizado: plano de contingência vigente de ciclo anterior"
                  and "juiz" not in documento_generico("plano") and "_" not in documento_generico("plano_novo")
                  and documento_generico("plano_antigo", True) == "Plano de contingência vigente de ciclo anterior"))
    casos.append(("a ementa sai do objeto ex-ante",
                  r["documento"].startswith("Fica instituído o Plano Municipal")))
    sem_objeto = registro_do_veredito(dict(base, criterios={}), 0, 0, "DOM", "x", "28/09/2026")
    # 09/10/2026 (A1-02): trava ESTRUTURAL do desempacotamento. `rodar_portoes()` devolve
    # `(ok, saida)`; atribuir a tupla inteira a `ok` torna a rede de protecao morta, porque tupla
    # de dois elementos e sempre verdadeira. A trava le o proprio fonte: foi assim que o defeito
    # passou em revisao, e ler o fonte e o unico jeito de pegar o mesmo erro de novo sem rodar a
    # aplicacao de verdade.
    fonte_deste = pathlib.Path(__file__).read_text(encoding="utf-8")
    atribuicoes = [l.strip() for l in fonte_deste.splitlines()
                   if l.strip().endswith("= rodar_portoes()")]
    casos.append(("o retorno de rodar_portoes e desempacotado em (ok, saida)",
                  atribuicoes == ["ok, saida_portoes = rodar_portoes()"]))
    import inspect
    from julgar_e_aplicar_descobertas import rodar_portoes as _rp
    casos.append(("rodar_portoes continua devolvendo dois valores",
                  "return True," in inspect.getsource(_rp)
                  and "return False," in inspect.getsource(_rp)))
    casos.append(("sem objeto, a ementa diz o que é sem inventar texto",
                  sem_objeto["documento"] == "Ato oficial localizado: plano de contingência vigente de ciclo anterior"))

    ruins = [n for n, ok in casos if not ok]
    for n, ok in casos:
        print(f"  {'OK  ' if ok else 'FALHA'} {n}")
    if ruins:
        print(f"X AUTOTESTE: {len(ruins)} caso(s) reprovado(s).")
        return 1
    print(f"OK AUTOTESTE — {len(casos)} casos, sem rede e sem escrita.")
    return 0


def marcar_o_banco() -> int:
    """A marca de plano desatualizado segundo a lei em todo o banco, a cada passada: a data do plano não muda, mas
    o cadastro e o registro mudam."""
    from coletores_base import gravar_em
    municipios = json.loads(MUNICIPIOS.read_text(encoding="utf-8"))
    ref = {(r["nome"], r["uf"]): str(r["codigo_ibge"]).zfill(7)
           for r in json.loads((MUNICIPIOS.parent / "municipios_ibge_referencia.json").read_text(encoding="utf-8"))}
    n = marcar_desatualizados(municipios, lambda m: ref.get((m.get("nome"), m.get("uf"))), municipios_do_cadastro())
    s = marcar_planos_da_saude(municipios, texto_da_copia_preservada)
    if n or s:
        gravar_em(MUNICIPIOS, municipios)
    print(f"marca de plano desatualizado segundo a lei: {n} registro(s) mudaram; plano da saúde: {s}")
    return n + s


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()

    from coletores_base import gravar_em, hoje_editorial
    from scripts.verificar_fichas_municipais import problemas_de_documento
    from juiz import CODEBOOK_VERSAO
    from julgar_e_aplicar_descobertas import (backup_dados, buscar_lat_lon, canal_e_fonte,
                                              restaurar_dados, rodar_portoes)

    doc = json.loads(REGISTRO.read_text(encoding="utf-8"))
    decisoes = doc.get("decisoes") or []
    alvo = aplicaveis(decisoes, CODEBOOK_VERSAO)
    saem = a_retirar(decisoes, json.loads(MUNICIPIOS.read_text(encoding="utf-8")), CODEBOOK_VERSAO)
    print(f"{len(alvo)} promoção(ões) na versão em vigor do codebook ({CODEBOOK_VERSAO}), "
          f"de {len(decisoes)} decisão(ões) no registro; {len(saem)} registro(s) a retirar por releitura sem data")
    for v in alvo:
        print(f"  {v['municipio']}/{v['uf']} · {v['categoria']} · {v.get('data')} · {v.get('url')}")
    if "--aplicar" in sys.argv:
        marcar_o_banco()
    if not alvo and not saem:
        print("nada a aplicar")
        if "--aplicar" in sys.argv and any("indicado_ao_cadastro_art3A" in v for v in decisoes):  # e o rótulo
            gravar_em(REGISTRO, doc)   # os campos descritivos ficam registrados no veredito
        return 0

    if "--aplicar" not in sys.argv:
        print("relatório apenas; nada escrito (use --aplicar)")
        return 0

    hoje = hoje_editorial()
    backup = backup_dados()
    municipios = json.loads(MUNICIPIOS.read_text(encoding="utf-8"))
    pontos = json.loads(PONTOS.read_text(encoding="utf-8"))
    aplicados, recusados = [], []

    for v, registro in a_retirar(decisoes, municipios, CODEBOOK_VERSAO):
        municipios.remove(registro)
        pontos[:] = [x for x in pontos if (x.get("nome"), x.get("uf")) != (registro.get("nome"), registro.get("uf"))]
        v["retirou"] = {"em": hoje.isoformat(), **{k: registro.get(k) for k in ("categoria", "documento", "data", "hash_evidencia")}}
        aplicados.append(v)
        print(f"  retirado: {v['municipio']}/{v['uf']} — o documento relido não informa a data (constava {registro.get('data')})")

    for v in alvo:
        if not v.get("ibge") and not v.get("municipio"):
            recusados.append((v, "veredito sem território — não dá para posicionar"))
            continue
        existente = no_banco(municipios, v["municipio"], v["uf"])
        motivo_da_troca = atualiza(existente, v) if existente else ""
        if existente and not motivo_da_troca:
            recusados.append((v, JA_CONSTA + "mesmo documento, ou registro igual ou mais forte"))
            continue
        if (nao_documento := problemas_de_documento([{**v, "nome": v["municipio"], "hash_evidencia": "-"}])):
            recusados.append((v, nao_documento[0].split(": ", 1)[1] + " (D1: o ato é o documento, não a notícia)"))
            continue
        lat, lon = buscar_lat_lon(v["municipio"], v["uf"])
        if lat is None:
            recusados.append((v, "não consta na referência do IBGE — sem posição no mapa"))
            continue
        canal, fonte_base = canal_e_fonte(v.get("url") or "")
        # A EVIDÊNCIA vem antes do registro: registro pontuável com URL e sem evidência preservada
        # é vermelho no portão 26, e com razão — a prova é o que permite conferir a decisão depois.
        # O hash do documento preservado substitui o hash do texto julgado no registro: o primeiro
        # é do arquivo que ficou guardado, e é esse que a auditoria vai abrir.
        hash_preservado = preservar_o_documento(v.get("url") or "")
        if not hash_preservado:
            recusados.append((v, "documento não pôde ser preservado — registro pontuável exige "
                                 "evidência guardada (portão 26)"))
            continue
        if not tem_copia(hash_preservado):
            # 24/10/2026: acima do limite de evidência a porta só pede o Wayback, que não lê pasta
            # privada; 16 do RS entraram sem arquivo e o portão 26 barrou o PR de dado.
            recusados.append((v, "documento acima do limite de evidência e sem cópia externa — "
                                 "registro pontuável exige evidência guardada (portão 26)"))
            continue
        v["hash_evidencia"] = hash_preservado
        novo = registro_do_veredito(v, lat, lon, canal, fonte_base, hoje.strftime("%d/%m/%Y"))
        if existente:
            novo["registro_anterior"] = {k: existente.get(k) for k in
                                         ("categoria", "documento", "url", "fonte", "data", "hash_evidencia")}
            municipios[municipios.index(existente)] = novo
            for ponto in pontos:
                if (ponto.get("nome"), ponto.get("uf")) == (existente.get("nome"), existente.get("uf")):
                    ponto["categoria"] = v["categoria"]
            v["substituiu"] = motivo_da_troca
            print(f"  atualizado: {v['municipio']}/{v['uf']} — {motivo_da_troca}")
        else:
            municipios.append(novo)
            pontos.append({"nome": v["municipio"], "uf": v["uf"], "categoria": v["categoria"],
                           "lat": lat, "lon": lon, "fase": 3})
        aplicados.append(v)

    for v, motivo in recusados:
        print(f"  não aplicado: {v['municipio']}/{v['uf']} — {motivo}")
        if motivo.startswith(LIMITE_NOSSO):
            continue  # falha do nosso acesso ou da nossa guarda, não decisão sobre o caso (24/10 e 17/11/2026)
        v["nao_aplicado"] = {"em": hoje.isoformat(), "motivo": motivo}

    if not aplicados:
        print("nenhuma promoção aplicável nesta passada; banco intacto")
        gravar_em(REGISTRO, doc)
        return 0

    gravar_em(MUNICIPIOS, municipios)
    gravar_em(PONTOS, pontos)
    print(f"{len(aplicados)} registro(s) escrito(s); rodando recálculo e portões antes de confirmar")

    # 09/10/2026 (A1-02): `rodar_portoes()` devolve a TUPLA `(ok, saida)`, e aqui ela era atribuida
    # inteira a `ok`. Tupla de dois elementos e sempre verdadeira — a rede de protecao descrita no
    # cabecalho deste arquivo NUNCA disparou: portao vermelho confirmava a aplicacao em vez de
    # desfaze-la. O motivo agora guarda a saida do portao que reprovou, porque reverter sem dizer o
    # que reprovou obriga a repetir a rodada para descobrir.
    ok, saida_portoes = rodar_portoes()
    if not ok:
        restaurar_dados(backup)
        ultima = [l for l in (saida_portoes or "").splitlines() if l.strip()][-6:]
        for v in aplicados:
            v.pop("retirou", None)
            v["revertido_por_portao"] = {"em": hoje.isoformat(),
                                         "motivo": "portão vermelho depois da aplicação",
                                         "saida": chr(10).join(ultima)}
        gravar_em(REGISTRO, doc)
        print("X portão vermelho — tudo restaurado em disco; as decisões guardam o erro")
        for l in ultima:
            print(f"   | {l}")
        return 1

    for v in aplicados:
        if v.get("promove"):
            v["aplicado_em"] = hoje.isoformat()
    gravar_em(REGISTRO, doc)
    print(f"OK {len(aplicados)} promoção(ões) aplicada(s) e confirmada(s) pelos portões")
    return 0


if __name__ == "__main__":
    sys.exit(main())
