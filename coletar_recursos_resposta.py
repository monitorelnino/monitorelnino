#!/usr/bin/env python3
"""Recursos federais de defesa civil liberados por município — portarias da SEDEC/MIDR no DOU.

Item 7 do handover de 02/10/2026. O MARÉ já registrava o RECONHECIMENTO federal de emergência
(`coletar_s2id.py`) e as transferências constitucionais e legais pagas (Portal da Transparência).
Faltava o elo do meio, que é o que a editoria pediu: **quanto a União autorizou a transferir para
cada município**, por ato, com data e valor.

A FONTE, MEDIDA EM 02/10 E EM 25/11/2026
----------------------------------------
A busca do DOU por `"Autoriza a transferência de recursos"` devolve as portarias da Secretaria
Nacional de Proteção e Defesa Civil — 77 atos entre 20/09 e 02/10/2026. Em 25/11 a auditoria do
relatório do RS mediu a outra redação, `"Autoriza o empenho e a transferência de recursos"`, que a
frase exata não casa: 745 atos de 26/04 a 23/11/2026 contra 624 da primeira, todos de RESPOSTA
(R$ 356 milhões que o arquivo não tinha). As duas consultas são lidas. Cada ato traz, no texto
integral, tudo o que o registro precisa:

    Órgão: Ministério da Integração e do Desenvolvimento Regional/Secretaria Nacional de
    Proteção e Defesa Civil
    PORTARIA Nº 3.181, DE 24 DE SETEMBRO DE 2026
    Art. 1º Autorizar a transferência de recursos ao município de Joaíma/MG para a execução de
    ações de Recuperação … no valor de R$ 416.281,64 …

"LIBERADO" NÃO É "TRANSFERIDO", E "RESPOSTA" NÃO É "RECUPERAÇÃO"
---------------------------------------------------------------
Duas distinções que o vocabulário da METODOLOGIA exige e que este coletor mantém separadas:

1. A portaria **autoriza**; o dinheiro sai depois, e quem registra a saída é o Portal da
   Transparência. O que se guarda aqui é `valor_autorizado`, e a página diz "liberado" — nunca
   "pago" nem "transferido".
2. A mesma rota autoriza ações de **Resposta** e de **Recuperação**, e o próprio art. 1º diz qual é.
   Resposta é o socorro imediato; recuperação é a obra depois. Somar as duas num cartão de
   "recursos de resposta" seria inflar o número com dinheiro de outra finalidade, e por isso o
   arquivo guarda as duas com o rótulo que o ato deu (`acao`), separadas.

MUNICÍPIO QUE NÃO CASA NÃO SOME
-------------------------------
O nome vem do ART. 1º do ato (a ementa erra: "São Luiz Gonzaga/AM" na epígrafe, "/RS" no artigo),
no formato `Joaíma/MG`, e é pareado com a referência do IBGE. O que não casar fica em
`atos_nao_casados`, uma vez por ato, com o nome como o ato o escreveu — ninguém descarta ato por
falha de pareamento nossa. Ato a ESTADO fica em `atos_a_estados`. A RETIFICAÇÃO ("onde se lê…
leia-se…") corrige o ato que ela cita e não soma como ato novo.

USO
  python3 coletar_recursos_resposta.py --autoteste
  python3 coletar_recursos_resposta.py --relatorio            # o que a busca devolve, sem abrir atos
  python3 coletar_recursos_resposta.py [--desde 2026-06-29]
"""
import datetime
import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

import funil  # noqa: E402
from coletores_base import (NUM_ATO, buscar, fonte_do_coletor, grava_no_banco, gravar, hoje_editorial, ler,  # noqa: E402
                            log_busca, normalizar_nome,
                            preservar_evidencia, referencia_ibge, registrar_lacuna,
                            rodar_autoteste, varrer_busca_dou)

SAIDA = "resposta/recursos_liberados.json"
ORIGEM = "coletar_recursos_resposta"
CONSULTAS = ('"Autoriza a transferência de recursos"', '"Autoriza o empenho e a transferência de recursos"')
JANELA_DA_BUSCA = 10   # dias por consulta: a janela de sete meses devolveu 502 em 25/11/2026
CICLO = datetime.date(2026, 6, 29)
# A primeira carga NÃO varre o ciclo inteiro. Medido em 02/10/2026: a janela de 29/06 a 02/10 tem
# centenas de atos, e cada um exige abrir o texto integral com o ritmo de 2 s por domínio — horas de
# rede para um arquivo que a rodada diária preenche sozinha, dia a dia. A primeira carga lê 30 dias,
# a janela lida fica DECLARADA no arquivo (`janela_lida`), e a cadência diária estende a cobertura
# para frente. Nada aqui apresenta recorte como varredura.
PRIMEIRA_CARGA_DIAS = 30

# O órgão que autoriza transferência de recursos de defesa civil é a Secretaria Nacional de Proteção
# e Defesa Civil, e o DOU declara o órgão no cabeçalho do ato. Ato de outro órgão que apenas casa
# com a mesma expressão não entra — e não é descartado em silêncio: entra em `fora_do_orgao`.
RE_ORGAO = re.compile(r"Prote[çc][ãa]o e Defesa Civil", re.I)
# "PORTARIA Nº 3.181, DE 24 DE SETEMBRO DE 2026" — o número com ou sem ponto de milhar.
RE_PORTARIA = re.compile(r"PORTARIA\s+(?:" + NUM_ATO + r")?\s*([\d.]+),?\s+DE\s+(\d{1,2})\s+DE\s+([A-Za-zÇç]+)\s+DE\s+(\d{4})",
                         re.I)
# "ao município de Joaíma/MG" — a UF vem junto, e é isso que permite parear sem adivinhar. Medido em 25/11/2026:
# "Bossoroca - RS", "General Câmara/RSpara" e "município Campo Grande/MS" também são grafias do DOU.
_DESTINO = r"([^,/()]+?)\s*(?:/|\s[-–]\s|\()\s*([A-Z]{2})(?![A-Z])"
RE_MUNICIPIO = re.compile(r"(?i:munic[íi]pio\s+(?:d[eoa]s?\s+)?)" + _DESTINO)
RE_ESTADO = re.compile(r"(?i:\bao\s+estado\s+d[eoa]s?\s+)" + _DESTINO)
# O art. 1º é a parte que autoriza; a ementa só o resume, e é nela que o DOU erra o município.
RE_ARTIGO_1 = re.compile(r"Art\.\s*1\s*[º°o]?(.{0,1500}?)(?=Art\.\s*2\s*[º°o]?|$)", re.S)
# "no valor de R$ 416.281,64" (e "RS 467.563,80", erro de digitação do próprio DOU)
RE_VALOR = re.compile(r"no valor de\s+R[$S]\s*([\d.]+,\d{2})", re.I)
# Retificação: "Na Portaria SEDEC/MIDR n° 3971, de 12 de novembro de 2026, … onde se lê: … leia-se: …"
RE_RETIFICACAO = re.compile(r"\bonde\s+se\s+l[êe]\b(.*?)\bleia\s*-?\s*se\b(.*)", re.I | re.S)
RE_PORTARIA_CITADA = re.compile(r"portaria(?:\s+SEDEC/MIDR)?\s+n[°º.o]*\s*([\d.]+)\s*,?\s+de\s+(\d{1,2})[º°]?\s+de\s+"
                                r"([A-Za-zÇç]+)\s+de\s+(\d{4})", re.I)
# "para a execução de ações de Recuperação" | "de Resposta" | "de Proteção e Defesa Civil"
RE_ACAO = re.compile(r"execu[çc][ãa]o de a[çc][õo]es de\s+([A-Za-zÀ-ú ]+?)(?:\s+descritas|\s*[,.;]|\s+contid)",
                     re.I)
RE_SEI = re.compile(r"processo\s+SEI\s+n[.º°o]*\s*([\d./-]+)", re.I)
# MEDIDO em 02/10/2026: dois terços dos atos que casam com a consulta são PRORROGAÇÕES DE
# PRAZO ("Art. 1° Prorrogar o prazo de execução das ações … até 19/05/2027"), que alteram o
# prazo de uma portaria anterior e não autorizam dinheiro nenhum. Eles não têm valor porque
# não há valor — e chamá-los de "sem valor declarado" convidaria alguém, depois, a "consertar"
# o regex do valor e passar a somar dinheiro que o ato não autorizou.
RE_PRORROGACAO = re.compile(r"Prorrogar\s+o\s+prazo", re.I)

MESES = {m: i + 1 for i, m in enumerate(
    "janeiro fevereiro março abril maio junho julho agosto setembro outubro novembro dezembro".split())}
# Os rótulos que o próprio ato usa, normalizados para o arquivo. Nada além disto é inventado:
# ação que o ato chame de outra coisa fica como `outra`, com o texto original guardado.
ACOES = {"resposta": "resposta", "recuperação": "recuperacao", "recuperacao": "recuperacao"}


# =============================================================================================
# Leitura do ato — funções puras sobre o texto
# =============================================================================================
def texto_limpo(bruto) -> str:
    """O ato como texto corrido. Função pura."""
    t = bruto.decode("utf-8", "replace") if isinstance(bruto, bytes) else str(bruto or "")
    t = re.sub(r"<(script|style)\b.*?</\1>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def valor_de(texto: str):
    """O valor em reais, como número. Função pura; None quando o ato não declara valor.

    Ato sem valor declarado NÃO vira zero: zero diria que a União autorizou nada, e o que houve foi
    um ato que não diz quanto."""
    m = RE_VALOR.search(texto or "")
    if not m:
        return None
    return float(m.group(1).replace(".", "").replace(",", "."))


def acao_de(texto: str) -> tuple:
    """(chave, rótulo como o ato escreveu). Função pura.

    MEDIDO em 02/10/2026: o ato diz "ações de" DUAS vezes, e as duas dizem coisas diferentes. A
    ementa usa o rótulo guarda-chuva da rota ("ações de Proteção e Defesa Civil") e o **art. 1º**
    diz a finalidade de verdade ("ações de Recuperação"). Pegar a primeira ocorrência classificava
    todo ato como `outra` — foi o que a primeira versão desta função fez.

    A regra: entre as ocorrências, vale a primeira que seja uma FINALIDADE (resposta, recuperação);
    o guarda-chuva só vale quando não houver finalidade declarada, e aí o rótulo original fica
    guardado, porque reclassificar o que o ato chamou de outra coisa seria decidir no lugar dele."""
    achados = [re.sub(r"\s+", " ", m.group(1)).strip() for m in RE_ACAO.finditer(texto or "")]
    if not achados:
        return "nao_declarada", None
    for rotulo in achados:
        if rotulo.lower() in ACOES:
            return ACOES[rotulo.lower()], rotulo
    return "outra", achados[0]


def titulo_da_url(url: str) -> str:
    """O título que o DOU põe no endereço do ato ("portaria-n-2.108-de-1-de-julho-de-2026-716723949"),
    para quando o texto lido não traz o cabeçalho. Função pura."""
    slug = re.sub(r"-\d+$", "", (url or "").rstrip("/").rsplit("/", 1)[-1])
    return slug.replace("-", " ")


def portaria_e_data(texto: str, url: str = ""):
    """(número, data) da portaria: do cabeçalho do texto; sem ele, do título no endereço. Função pura."""
    mp = RE_PORTARIA.search(texto or "")
    if mp:
        return mp.group(1), data_do_ato(texto)
    mp = RE_PORTARIA.search(titulo_da_url(url))
    if not mp:
        return None, None
    n = mp.group(1).replace(".", "")
    return (f"{int(n):,}".replace(",", ".") if n.isdigit() else mp.group(1)), data_do_ato(titulo_da_url(url))


def data_do_ato(texto: str):
    """A data da portaria, do próprio título. Função pura."""
    m = RE_PORTARIA.search(texto or "")
    if not m:
        return None
    mes = MESES.get(m.group(3).lower())
    if not mes:
        return None
    try:
        return datetime.date(int(m.group(4)), mes, int(m.group(2)))
    except ValueError:
        return None


def artigo_1(texto: str) -> str:
    """O art. 1º do ato, até o art. 2º; "" quando o texto não o traz. Função pura."""
    m = RE_ARTIGO_1.search(texto or "")
    return m.group(1) if m else ""


def numero_de_portaria(n) -> str:
    """"3971" e "3.971" são a mesma portaria: o número sai com ponto de milhar. Função pura."""
    d = re.sub(r"\D", "", str(n or ""))
    return f"{int(d):,}".replace(",", ".") if d else None


def ler_retificacao(texto: str, url: str = ""):
    """A retificação lida como correção do ato que ela cita, com None no que o "leia-se" não traz; None quando o
    texto não é retificação. Função pura.

    25/11/2026: a retificação entrava como ato novo e somava de novo. A Portaria 2.232 autorizava R$ 6.029.740,61
    a Juiz de Fora/MG por erro de cópia; a retificação diz Mogeiro/PB, R$ 437.707,00."""
    m = RE_RETIFICACAO.search(texto or "")
    if not m:
        return None
    citada = RE_PORTARIA_CITADA.search(texto[:m.start()]) or RE_PORTARIA_CITADA.search(texto)
    errado, certo = m.group(1), m.group(2)
    de, mm, sei = RE_MUNICIPIO.search(errado), RE_MUNICIPIO.search(certo), RE_SEI.search(texto)
    chave, rotulo = acao_de(certo)
    finalidade = chave in ACOES.values()   # o guarda-chuva da ementa não corrige a finalidade do art. 1º
    return {"retifica": numero_de_portaria(citada.group(1)) if citada else None,
            "ano": citada.group(4) if citada else None,
            "processo_sei": sei.group(1) if sei else None,
            "onde_se_le": [re.sub(r"\s+", " ", de.group(1)).strip(), de.group(2)] if de else None,
            "municipio": re.sub(r"\s+", " ", mm.group(1)).strip() if mm else None,
            "uf": mm.group(2) if mm else None,
            "valor_autorizado": valor_de(certo),
            "acao": chave if finalidade else None, "acao_no_ato": rotulo if finalidade else None,
            "url": url}


def ler_ato(texto: str, url: str = "") -> dict:
    """O registro do ato, ou um dicionário com `motivo` quando ele não serve. Função pura.

    As recusas são declaradas em vez de virar silêncio: órgão que não é a defesa civil nacional, retificação (que
    corrige outro ato), ato sem destinatário legível, prorrogação de prazo e ato sem valor. O destinatário e o
    valor vêm do art. 1º; a ementa só serve quando o texto não traz o artigo."""
    if not RE_ORGAO.search(texto or ""):
        return {"motivo": "fora_do_orgao"}
    retificacao = ler_retificacao(texto, url)
    if retificacao:
        return {"motivo": "retificacao", "retificacao": retificacao}
    art = artigo_1(texto)
    mm = RE_MUNICIPIO.search(art)
    estado = None if mm else RE_ESTADO.search(art)
    if not mm and not estado:
        mm = RE_MUNICIPIO.search(texto or "")
        estado = None if mm else RE_ESTADO.search(texto or "")
    if not mm and not estado:
        return {"motivo": "sem_municipio_legivel"}
    if RE_PRORROGACAO.search(texto or ""):
        return {"motivo": "prorrogacao_de_prazo"}
    portaria, d = portaria_e_data(texto, url)
    chave, rotulo = acao_de(texto)
    valor = valor_de(art) if valor_de(art) is not None else valor_de(texto)
    if valor is None:
        return {"motivo": "sem_valor_declarado"}
    sei = RE_SEI.search(texto or "")
    nome = re.sub(r"\s+", " ", (mm or estado).group(1)).strip()
    return {
        "municipio": nome if mm else None,
        **({} if mm else {"estado": nome}),
        "uf": (mm or estado).group(2),
        "portaria": numero_de_portaria(portaria),
        "data": d.isoformat() if d else None,
        "acao": chave,
        "acao_no_ato": rotulo,
        "valor_autorizado": valor,
        "processo_sei": sei.group(1) if sei else None,
        "url": url,
    }


def so_digitos(s) -> str:
    return re.sub(r"\D", "", str(s or ""))


def chave_do_ato(a: dict) -> tuple:
    """O ato é a portaria no seu processo, seja qual for o município que a leitura lhe deu: (número, ano, processo
    SEI). O número sozinho não basta: em 2026 a 3.307 de 29/09 autoriza Barra do Corda/MA num processo e
    Colinas/RS em outro, e a 2.879 de 02/09, Sarandi/RS e Guariba/SP. Sem processo, o endereço. Função pura."""
    n = numero_de_portaria(a.get("portaria"))
    return (n, str(a.get("data") or "")[:4], so_digitos(a.get("processo_sei")) or a.get("url")) if n else ("url", a.get("url"))


def fundir(anterior: dict, registros: list, retificacoes: list, janela: dict, recusas: dict,
           codigo_de=None) -> dict:
    """O arquivo com os atos lidos, as retificações aplicadas e os totais refeitos. Função pura.

    Um ato por portaria: reler a janela não duplica, e a leitura nova substitui a antiga (em 25/11/2026 a
    leitura pelo art. 1º corrigiu o município que a ementa errava). A retificação muda o ato que ela cita.
    Totais, `nao_casados` e `municipios` são derivados dos atos a cada rodada: nada se acumula.
    `codigo_de(município, UF)` devolve o código do IBGE ou None."""
    anterior = anterior or {}
    codigo_de = codigo_de or (lambda municipio, uf: None)
    atos = {}
    for cod, m in (anterior.get("municipios") or {}).items():
        for a in m.get("atos") or []:
            if not a.get("portaria") or not a.get("data"):
                n, d = portaria_e_data("", a.get("url"))
                a = {**a, "portaria": a.get("portaria") or n, "data": a.get("data") or (d.isoformat() if d else None)}
            atos[chave_do_ato(a)] = {**a, "ibge": cod}
    for a in (anterior.get("atos_nao_casados") or []) + (anterior.get("atos_a_estados") or []):
        atos[chave_do_ato(a)] = {**a, "ibge": None}
    antes = set(atos)
    for r in registros:
        atos[chave_do_ato(r)] = dict(r)
    vistas = {x.get("url"): x for x in (anterior.get("retificacoes") or [])}
    vistas.update({x.get("url"): {k: v for k, v in x.items() if k != "aplicada"} for x in retificacoes})
    for x in vistas.values():
        # A portaria citada; se o número serve a mais de um ato, o do mesmo processo ou o do município corrigido.
        mesmas = [a for k, a in atos.items() if k[:2] == (x.get("retifica"), x.get("ano"))]
        do_caso = [a for a in mesmas if (so_digitos(x.get("processo_sei")) and so_digitos(a.get("processo_sei")) == so_digitos(x["processo_sei"]))
                   or [a.get("municipio"), a.get("uf")] in (x.get("onde_se_le"), [x.get("municipio"), x.get("uf")])]
        alvo = mesmas[0] if len(mesmas) == 1 else do_caso[0] if len(do_caso) == 1 else None
        x["aplicada"] = bool(alvo)
        if not alvo:
            continue
        if x.get("municipio") and (x["municipio"], x["uf"]) != (alvo.get("municipio"), alvo.get("uf")):
            alvo.update(municipio=x["municipio"], uf=x["uf"], ibge=codigo_de(x["municipio"], x["uf"]))
            alvo.pop("estado", None)
        for campo in ("valor_autorizado", "acao", "acao_no_ato"):
            if x.get(campo) is not None:
                alvo[campo] = x[campo]
        alvo["retificado_por"] = x.get("url")
    mun, soltos, estados = {}, [], []
    for _, a in sorted(atos.items(), key=lambda kv: (str(kv[1].get("data") or ""), str(kv[0]))):
        ato = {k: v for k, v in a.items() if k != "ibge"}
        if a.get("estado"):
            estados.append(ato)
        elif not a.get("ibge"):
            soltos.append(ato)
        else:
            alvo = mun.setdefault(a["ibge"], {"nome": a["municipio"], "uf": a["uf"], "por_acao": {}, "atos": []})
            alvo["por_acao"][a["acao"]] = round(alvo["por_acao"].get(a["acao"], 0.0) + a["valor_autorizado"], 2)
            alvo["atos"].append(ato)
            alvo["total_autorizado"] = round(sum(alvo["por_acao"].values()), 2)
    pend, tot = {}, {}
    for a in soltos:
        k = f"{a['uf']}|{a['municipio']}"
        pend[k] = round(pend.get(k, 0.0) + a["valor_autorizado"], 2)
    for m in mun.values():
        for acao, v in m["por_acao"].items():
            tot[acao] = round(tot.get(acao, 0.0) + v, 2)
    cob = anterior.get("cobertura") or {}
    mesma = cob.get("consultas") == list(CONSULTAS) and janela.get("desde") and cob.get("desde")
    from gerar_resposta import FRASE_C18  # noqa: PLC0415 — a frase é de quem a define; cópia divergiria
    return {
        "municipios": {k: mun[k] for k in sorted(mun)},
        "atos_nao_casados": soltos,
        "nao_casados": {k: pend[k] for k in sorted(pend)},
        "atos_a_estados": estados,
        "retificacoes": sorted(vistas.values(), key=lambda x: str(x.get("url"))),
        "janela_lida": janela,
        # A cobertura só soma janelas lidas com as MESMAS consultas: a redação nova começa onde foi lida.
        "cobertura": {"desde": min(cob["desde"], janela["desde"]) if mesma else janela.get("desde"),
                      "ate": janela.get("ate"), "consultas": list(CONSULTAS),
                      # O que falhou nesta rodada (janela da busca ou ato) é devido à próxima; o que ela devia, releu.
                      "a_reler": [dict(t) for t in sorted({(("de", j["de"]), ("ate", j["ate"]), ("consulta", j.get("consulta")))
                                                           for j in janela.get("janelas_incompletas") or [] if j.get("erro")},
                                                          key=str)]},
        "recusas": recusas,
        "atos_novos_nesta_rodada": len(set(atos) - antes),
        "atualizado_em": hoje_editorial().strftime("%d/%m/%Y"),
        "total_por_acao": tot,
        "municipios_com_ato": len(mun),
        # A frase C18 viaja com TODO arquivo de `data/resposta/` (`verificar_resposta.py` reprova a ausência): no
        # período eleitoral as transferências voluntárias param e as abertas por decreto continuam.
        "frase_c18": FRASE_C18,
        "_governanca": (
            "Recursos federais de defesa civil AUTORIZADOS por município, lidos das portarias da "
            "Secretaria Nacional de Proteção e Defesa Civil no DOU (consultas "
            f"{' e '.join(CONSULTAS)}). `valor_autorizado` é o que a portaria autoriza transferir — a saída do "
            "dinheiro é outro fato, e quem o registra é o Portal da Transparência: a página diz "
            "'liberado', nunca 'pago'. As ações de RESPOSTA e de RECUPERAÇÃO ficam separadas em "
            "`por_acao`, com o rótulo que o próprio ato usou, porque somá-las num cartão de resposta "
            "inflaria o número com dinheiro de outra finalidade. Ato sem valor declarado não vira zero: "
            "entra em `recusas.sem_valor_declarado`. O município vem do art. 1º do ato; o que não casa com a "
            "referência do IBGE fica em `atos_nao_casados` (resumo em `nao_casados`), com o nome como o ato o "
            "escreveu; ato a estado fica em `atos_a_estados`; a retificação corrige o ato que cita "
            "(`retificacoes`). `cobertura` diz desde quando as consultas foram lidas. Derivado de "
            "coletar_recursos_resposta.py — não se edita à mão."),
    }


# =============================================================================================
# A rodada
# =============================================================================================
def a_reler_de(anterior: dict, desde: datetime.date) -> list:
    """[(consulta ou None, de, até)] que o arquivo ainda deve: janela ou ato que falhou em rodada anterior e, se o
    arquivo veio de outras consultas, o ciclo até a véspera de `desde` pelas consultas de hoje. Função pura."""
    cob = anterior.get("cobertura") or {}
    devidas = [(p.get("consulta"), datetime.date.fromisoformat(p["de"]), datetime.date.fromisoformat(p["ate"]))
               for p in cob.get("a_reler") or []]
    if anterior.get("municipios") and cob.get("consultas") != list(CONSULTAS) and desde > CICLO:
        devidas.append((None, CICLO, desde - datetime.timedelta(days=1)))
    return devidas


def varrer(desde: datetime.date, ate: datetime.date, buscar_fn, a_reler=()) -> tuple:
    """(itens, janelas incompletas) das duas consultas, em janelas de `JANELA_DA_BUSCA` dias: primeiro o que ficou
    devido (`a_reler`), depois de `desde` a `ate`. Janela que a busca não entrega fica declarada com a causa; as
    outras seguem."""
    itens, incompletas, vistos, feitas = [], [], set(), set()
    pedidos = [(q, de, fim) for q0, de, fim in a_reler for q in ([q0] if q0 else CONSULTAS)]
    for q, de, fim in pedidos + [(q, desde, ate) for q in CONSULTAS]:
        a = de
        while a <= fim:
            b = min(a + datetime.timedelta(days=JANELA_DA_BUSCA - 1), fim)
            if (q, a, b) not in feitas:
                feitas.add((q, a, b))
                try:
                    achados, inc = varrer_busca_dou(q, a, b, buscar_fn=buscar_fn)
                except Exception as e:  # noqa: BLE001 — janela que não veio é lacuna declarada, não fim da rodada
                    achados, inc = [], [{"de": a.isoformat(), "ate": b.isoformat(), "erro": f"{type(e).__name__}: {str(e)[:120]}"}]
                    registrar_lacuna("recursos_resposta", f"busca {q} de {a} a {b}: {type(e).__name__}: {e}",
                                     canal="DOU", camada=1, nivel="nacional", strings=[q])
                incompletas += [{**j, "consulta": q} for j in (inc or [])]
                itens += [it for it in achados if it.get("url") not in vistos]
                vistos.update(it.get("url") for it in achados)
            a = b + datetime.timedelta(days=1)
    return itens, incompletas


def coletar(desde: datetime.date, ate: datetime.date = None, buscar_fn=None) -> dict:
    _buscar = buscar_fn or buscar
    ate = ate or hoje_editorial()
    anterior = ler(SAIDA) or {}
    itens, incompletas = varrer(desde, ate, _buscar, a_reler_de(anterior, desde))
    _, por_nome = referencia_ibge()
    por_nome_solto = {(normalizar_nome(n), uf): cod for (n, uf), cod in por_nome.items()}

    def codigo_de(municipio, uf):
        cod = por_nome.get((municipio, uf)) or por_nome_solto.get((normalizar_nome(municipio or ""), uf))
        return str(cod).zfill(7) if cod else None

    registros, retificacoes = [], []
    recusas = {"fora_do_orgao": 0, "prorrogacao_de_prazo": 0, "sem_municipio_legivel": 0,
               "sem_valor_declarado": 0, "retificacao": 0, "ato_nao_lido": 0}
    for it in itens:
        url = it.get("url") or ""
        try:
            bruto = _buscar(url, timeout=90, origem=ORIGEM)
        except Exception as e:  # noqa: BLE001 — ato que não abre é lacuna de um ato
            recusas["ato_nao_lido"] += 1
            dia = re.search(r"(\d{2})/(\d{2})/(\d{4})", str(it.get("data") or ""))   # o ato que não abriu volta pelo dia dele
            dia = "-".join(reversed(dia.groups())) if dia else None
            incompletas.append({"de": dia or desde.isoformat(), "ate": dia or ate.isoformat(),
                                "erro": f"ato não lido: {type(e).__name__}", "url": url})
            registrar_lacuna("recursos_resposta", f"{url}: {type(e).__name__}: {e}",
                             canal="DOU", camada=1, nivel="nacional", strings=[url])
            continue
        r = ler_ato(texto_limpo(bruto), url)
        if r.get("motivo"):
            recusas[r["motivo"]] = recusas.get(r["motivo"], 0) + 1
            retificacoes += [r["retificacao"]] if r.get("retificacao") else []
            continue
        registros.append({**r, "ibge": None if r.get("estado") else codigo_de(r["municipio"], r["uf"])})

    janela = {"desde": desde.isoformat(), "ate": ate.isoformat(),
              "atos_na_busca": len(itens), "janelas_incompletas": incompletas}
    dados = fundir(anterior, registros, retificacoes, janela, recusas, codigo_de)
    corpo = json.dumps({"consultas": CONSULTAS, "janela": janela, "recusas": recusas, "atos": registros,
                        "retificacoes": retificacoes}, ensure_ascii=False, indent=1).encode("utf-8")
    h = preservar_evidencia(corpo, "https://www.in.gov.br/consulta/-/buscar/dou", "json", ORIGEM)
    gravar(SAIDA, dados)
    decisao = "registro" if registros else ("consultado sem achado" if itens else "erro")
    log_busca("DOU", 1, list(CONSULTAS), decisao, nivel="nacional", n_resultados=len(itens),
              resultados=(f"recursos_resposta: {len(itens)} ato(s) na busca, {len(registros)} "
                          f"lido(s), {len(dados['atos_nao_casados'])} sem pareamento no arquivo, "
                          f"{dados['atos_novos_nesta_rodada']} novo(s) no arquivo · recusas "
                          f"{recusas}"), hash_evidencia=h)
    funil.registrar("funil_recursos_resposta", consultas=len(CONSULTAS),
                    com_resultado_bruto=1 if itens else 0, pistas=len(registros))
    return {"atos_na_busca": len(itens), "lidos": len(registros), "novos": dados["atos_novos_nesta_rodada"],
            "nao_casados": len(dados["atos_nao_casados"]), "retificacoes": len(retificacoes), "recusas": recusas,
            "janelas_incompletas": len(incompletas), "total_por_acao": dados["total_por_acao"]}


# =============================================================================================
# Autoteste — offline, sem rede e sem escrever em data/
# =============================================================================================
# Recorte REAL do ato lido em 02/10/2026 (texto encurtado; a estrutura é a que veio).
FIXTURE = (
    "09/2026 | Edição: 182 | Seção: 1 | Página: 39 Órgão: Ministério da Integração e do "
    "Desenvolvimento Regional/Secretaria Nacional de Proteção e Defesa Civil PORTARIA Nº 3.181, "
    "DE 24 DE SETEMBRO DE 2026 Autoriza a transferência de recursos ao município de Joaíma/MG, "
    "para execução de ações de Proteção e Defesa Civil. A UNIÃO, por intermédio do MINISTÉRIO DA "
    "INTEGRAÇÃO E DO DESENVOLVIMENTO REGIONAL, … resolve: Art. 1º Autorizar a transferência de "
    "recursos ao município de Joaíma/MG para a execução de ações de Recuperação descritas no Plano "
    "de Trabalho aprovado no Sistema Integrado de Informações sobre Desastres (S2iD) e contido no "
    "processo SEI n.º 59053.024553/2026-22, no valor de R$ 416.281,64 (quatrocentos e dezesseis mil "
    "duzentos e oitenta e um reais e sessenta e quatro centavos). Art. 2º Os recursos financeiros "
    "serão transferidos, a título de Transferência Legal …")
# O segundo recorte é OUTRA portaria: a chave do ato é (portaria, município, UF), e usar o mesmo
# número para simular duas finalidades testaria o dedup, não a soma — foi o que a primeira versão
# destes casos fez, e os três que falharam estavam certos em falhar.
FIXTURE_RESPOSTA = (FIXTURE.replace("ações de Recuperação", "ações de Resposta")
                    .replace("R$ 416.281,64", "R$ 1.000.000,00")
                    .replace("PORTARIA Nº 3.181", "PORTARIA Nº 3.182"))


# 25/11/2026: os recortes abaixo são dos atos que a leitura antiga perdia ou atribuía errado.
FIXTURE_EMPENHO = (
    "Órgão: Ministério da Integração e do Desenvolvimento Regional/Secretaria Nacional de Proteção e Defesa Civil "
    "PORTARIA Nº 3.734, DE 26 DE OUTUBRO DE 2026 Autoriza a transferência de recursos ao Município de São Luiz "
    "Gonzaga/AM, para execução de ações de Proteção e Defesa Civil. A UNIÃO … resolve: Art. 1º Autorizar o empenho e a "
    "transferência de recursos ao município de São Luiz Gonzaga/RSpara a execução de ações de Resposta, conforme o "
    "protocolo de solicitação registrado no Sistema Integrado de Informações sobre Desastres (S2iD) e contido no "
    "processo SEI n.º 59052.040567/2026-01, no valor de R$ 135.630,00 (cento e trinta e cinco mil seiscentos e trinta "
    "reais). Art. 2º Os recursos financeiros serão empenhados …")
FIXTURE_ERRADA = (FIXTURE_EMPENHO.replace("PORTARIA Nº 3.734, DE 26 DE OUTUBRO", "PORTARIA Nº 2.232, DE 7 DE JULHO")
                  .replace("São Luiz Gonzaga/AM", "Mogeiro/PB").replace("São Luiz Gonzaga/RSpara", "Juiz de Fora/MG para")
                  .replace("R$ 135.630,00", "R$ 6.029.740,61"))
FIXTURE_RETIFICACAO = (
    "Órgão: Ministério da Integração e do Desenvolvimento Regional/Secretaria Nacional de Proteção e Defesa Civil "
    "RETIFICAÇÃO Na Portaria SEDEC/MIDR n° 2232, de 07 de julho de 2026, publicada no Diário Oficial da União em 09 de "
    "julho de 2026, Edição 127, Seção 1, pág. 63, no artigo 1º onde se lê: Autorizar o empenho e a transferência de "
    "recursos ao município de Juiz de Fora/MG para a execução de ações de Resposta, no valor de R$ 6.029.740,61 "
    "Leia-se: Autorizar o empenho e a transferência de recursos ao município de Mogeiro/PB para a execução de ações "
    "de Resposta, conforme o protocolo … no valor de R$ 437.707,00 (quatrocentos e trinta e sete mil setecentos e sete reais).")


def autoteste() -> int:
    lido = ler_ato(FIXTURE, "https://x/ato")
    resp = ler_ato(FIXTURE_RESPOSTA, "https://x/ato2")
    sem_valor = ler_ato(FIXTURE.replace("no valor de R$ 416.281,64", "sem valor"), "u")
    outro_orgao = ler_ato(FIXTURE.replace("Proteção e Defesa Civil", "Cultura"), "u")
    sem_mun = ler_ato(FIXTURE.replace("município de Joaíma/MG", "órgão central"), "u")
    codigos = {("Joaíma", "MG"): "3135605", ("Mogeiro", "PB"): "2509503", ("Juiz de Fora", "MG"): "3136702",
               ("São Luiz Gonzaga", "RS"): "4318903"}

    def codigo_de(municipio, uf):
        return codigos.get((municipio, uf))

    r1 = {**lido, "ibge": "3135605"}
    r2 = {**resp, "ibge": "3135605"}
    um = fundir({}, [r1], [], {"desde": "2026-10-01", "ate": "2026-10-02"}, {})
    dois = fundir(um, [r1, r2], [], {"desde": "2026-09-25", "ate": "2026-10-03"}, {})

    sem_cab = ler_ato(FIXTURE.replace("PORTARIA Nº 3.181, DE 24 DE SETEMBRO DE 2026", "SEM CABEÇALHO"),
                      "https://www.in.gov.br/web/dou/-/portaria-n.-3307-de-29-de-setembro-de-2026-735709410")
    velho = {"municipios": {"3135605": {"nome": "Joaíma", "uf": "MG", "por_acao": {}, "atos": [
        {"municipio": "Joaíma", "uf": "MG", "portaria": None, "data": None, "acao": "resposta", "valor_autorizado": 1.0,
         "url": "https://www.in.gov.br/web/dou/-/portaria-n-2.108-de-1-de-julho-de-2026-716723949"}]}}}
    curado = fundir(velho, [], [], {}, {})["municipios"]["3135605"]["atos"][0]

    empenho = ler_ato(FIXTURE_EMPENHO, "https://x/3734")
    errada = ler_ato(FIXTURE_ERRADA, "https://x/2232")
    retif = ler_ato(FIXTURE_RETIFICACAO, "https://x/retificacao")
    estadual = ler_ato(FIXTURE_EMPENHO.replace("ao município de São Luiz Gonzaga/RSpara", "ao Estado de Pernambuco/PE para"), "u")
    # A leitura antiga (pela ementa) tinha gravado a 3.734 sem casar; a nova a relê pelo art. 1º.
    antigo = {"municipios": {}, "nao_casados": {"AM|São Luiz Gonzaga": 1085040.0}}
    relido = fundir(antigo, [{**empenho, "ibge": codigo_de(empenho["municipio"], empenho["uf"])}], [], {}, {}, codigo_de)
    com_erro = fundir({}, [{**errada, "ibge": codigo_de(errada["municipio"], errada["uf"])}], [], {}, {}, codigo_de)
    corrigido = fundir(com_erro, [], [retif["retificacao"]], {}, {}, codigo_de)
    de_novo = fundir(corrigido, [], [retif["retificacao"]], {}, {}, codigo_de)
    solto = {**errada, "municipio": "Quevedo", "uf": "RS", "ibge": None}
    pendente = fundir(fundir({}, [solto], [], {}, {}), [solto], [], {}, {})
    devido = fundir({}, [], [], {"desde": "2026-06-29", "ate": "2026-11-25", "janelas_incompletas": [
        {"de": "2026-07-09", "ate": "2026-07-18", "erro": "HTTPError: 502", "consulta": CONSULTAS[1]},
        {"de": "2026-07-09", "ate": "2026-07-09", "erro": "ato não lido: HTTPError", "url": "https://x/ato"},
        {"de": "2026-08-03", "ate": "2026-08-03", "lidos": 50, "total": 61, "consulta": CONSULTAS[0]}]}, {})
    chamadas = []

    def busca_falsa(q, de, ate, buscar_fn=None):
        chamadas.append((q, de, ate))
        if q == CONSULTAS[1] and de == datetime.date(2026, 5, 6):
            raise OSError("HTTP Error 502")
        return [{"url": f"https://x/{de}"}], []

    # O autoteste troca a busca e o registro de lacuna DESTE módulo por falsos: nada vai à rede nem ao log.
    global varrer_busca_dou, registrar_lacuna
    originais = varrer_busca_dou, registrar_lacuna
    lacunas = []
    varrer_busca_dou, registrar_lacuna = busca_falsa, lambda *a, **k: lacunas.append(a)
    try:
        varridos, incompletas = varrer(datetime.date(2026, 4, 26), datetime.date(2026, 5, 20), None)
        feitas = len(chamadas)
        varrer(datetime.date(2026, 11, 18), datetime.date(2026, 11, 25), None, a_reler_de(devido, datetime.date(2026, 11, 18)))
        relidas, chamadas = chamadas[feitas:], chamadas[:feitas]
    finally:
        varrer_busca_dou, registrar_lacuna = originais

    casos = {
        "sem cabeçalho no texto, número e data vêm do título no endereço":
            lambda: sem_cab["portaria"] == "3.307" and sem_cab["data"] == "2026-09-29",
        "ato antigo sem número ganha número e data do endereço, sem duplicar":
            lambda: curado["portaria"] == "2.108" and curado["data"] == "2026-07-01",
        "o ato real é lido: município, UF, portaria e data":
            lambda: (lido["municipio"] == "Joaíma" and lido["uf"] == "MG"
                     and lido["portaria"] == "3.181" and lido["data"] == "2026-09-24"),
        "o valor sai do ato, em número":
            lambda: lido["valor_autorizado"] == 416281.64,
        "a ação vem do próprio ato, e recuperação não é resposta":
            lambda: lido["acao"] == "recuperacao" and resp["acao"] == "resposta",
        "o rótulo original da ação é guardado":
            lambda: lido["acao_no_ato"] == "Recuperação",
        "o processo é guardado para conferência":
            lambda: lido["processo_sei"] == "59053.024553/2026-22",
        # As recusas, cada uma declarada.
        "prorrogação de prazo não é dinheiro, e é recusada com o nome certo":
            lambda: ler_ato(FIXTURE.replace(
                "Art. 1º Autorizar a transferência de recursos ao município de Joaíma/MG para a "
                "execução de ações de Recuperação",
                "Art. 1° Prorrogar o prazo de execução das ações de Proteção e Defesa Civil no "
                "Município de Joaíma/MG até 19/05/2027"), "u") == {"motivo": "prorrogacao_de_prazo"},
        "ato sem valor declarado não vira zero: é recusa com motivo":
            lambda: sem_valor == {"motivo": "sem_valor_declarado"},
        "ato de outro órgão não entra, e diz por quê":
            lambda: outro_orgao == {"motivo": "fora_do_orgao"},
        "ato sem município legível não entra, e diz por quê":
            lambda: sem_mun == {"motivo": "sem_municipio_legivel"},
        "valor ausente devolve None, nunca 0.0":
            lambda: valor_de("texto sem valor") is None,
        "ação não declarada é dita, não adivinhada":
            lambda: acao_de("texto qualquer") == ("nao_declarada", None),
        # 25/11/2026: a redação de resposta, o município do art. 1º, o ato a estado e a retificação.
        "a redação 'empenho e a transferência' é consultada":
            lambda: any("empenho e a transferência" in q for q in CONSULTAS) and len(CONSULTAS) == 2,
        "o município vem do art. 1º quando a ementa diz outra UF, mesmo colado à palavra seguinte":
            lambda: (empenho["municipio"], empenho["uf"], empenho["acao"], empenho["valor_autorizado"])
                    == ("São Luiz Gonzaga", "RS", "resposta", 135630.0),
        "município escrito com hífen e sem 'de' também é lido":
            lambda: (ler_ato(FIXTURE_EMPENHO.replace("São Luiz Gonzaga/RSpara", "Bossoroca - RS para"), "u")["municipio"] == "Bossoroca"
                     and ler_ato(FIXTURE_EMPENHO.replace("município de São Luiz Gonzaga/RSpara", "município Campo Grande/MS para"), "u")["uf"] == "MS"),
        "ato a estado não é município ilegível: fica à parte, com o valor":
            lambda: (estadual.get("estado"), estadual["uf"], estadual["municipio"]) == ("Pernambuco", "PE", None)
                    and fundir({}, [{**estadual, "ibge": None}], [], {}, {})["atos_a_estados"][0]["valor_autorizado"] == 135630.0
                    and fundir({}, [{**estadual, "ibge": None}], [], {}, {})["municipios"] == {},
        "retificação não é ato novo: é lida como correção da portaria que cita":
            lambda: retif["motivo"] == "retificacao" and retif["retificacao"]["retifica"] == "2.232"
                    and (retif["retificacao"]["municipio"], retif["retificacao"]["valor_autorizado"]) == ("Mogeiro", 437707.0),
        "a retificação muda município e valor do ato, e aplicá-la de novo não muda nada":
            lambda: (list(com_erro["municipios"]) == ["3136702"] and list(corrigido["municipios"]) == ["2509503"]
                     and corrigido["total_por_acao"] == {"resposta": 437707.0} and corrigido["retificacoes"][0]["aplicada"]
                     and {k: v for k, v in de_novo.items() if k != "atualizado_em"}
                     == {k: v for k, v in corrigido.items() if k != "atualizado_em"}),
        "retificação de portaria que não está no arquivo fica guardada, sem efeito":
            lambda: fundir({}, [], [retif["retificacao"]], {}, {})["retificacoes"][0]["aplicada"] is False,
        "a leitura nova substitui a antiga da mesma portaria, e a soma velha dos não casados some":
            lambda: (list(relido["municipios"]) == ["4318903"] and relido["nao_casados"] == {}
                     and relido["atos_novos_nesta_rodada"] == 1),
        "ato não casado conta uma vez, por mais que a janela seja relida":
            lambda: pendente["nao_casados"] == {"RS|Quevedo": 6029740.61} and len(pendente["atos_nao_casados"]) == 1,
        "a busca vai em janelas curtas, pelas duas redações, e a janela que falha fica declarada":
            lambda: (len(chamadas) == 6 and all((ate - de).days < JANELA_DA_BUSCA for _, de, ate in chamadas)
                     and len(varridos) == 3 and len(incompletas) == 1 and incompletas[0]["consulta"] == CONSULTAS[1]
                     and "502" in incompletas[0]["erro"] and len(lacunas) == 1),
        "a cobertura declarada cresce com a janela lida pelas mesmas consultas":
            lambda: (um["cobertura"]["desde"] == "2026-10-01" and dois["cobertura"] == {
                "desde": "2026-09-25", "ate": "2026-10-03", "consultas": list(CONSULTAS), "a_reler": []}),
        "a janela e o ato que falham ficam devidos, e a rodada seguinte os relê antes da janela do dia":
            lambda: (devido["cobertura"]["a_reler"] == [
                         {"de": "2026-07-09", "ate": "2026-07-09", "consulta": None},
                         {"de": "2026-07-09", "ate": "2026-07-18", "consulta": CONSULTAS[1]}]
                     and a_reler_de(devido, datetime.date(2026, 11, 18))
                     == [(None, datetime.date(2026, 7, 9), datetime.date(2026, 7, 9)),
                         (CONSULTAS[1], datetime.date(2026, 7, 9), datetime.date(2026, 7, 18))]
                     and relidas == [(CONSULTAS[0], datetime.date(2026, 7, 9), datetime.date(2026, 7, 9)),
                                     (CONSULTAS[1], datetime.date(2026, 7, 9), datetime.date(2026, 7, 9)),
                                     (CONSULTAS[1], datetime.date(2026, 7, 9), datetime.date(2026, 7, 18)),
                                     (CONSULTAS[0], datetime.date(2026, 11, 18), datetime.date(2026, 11, 25)),
                                     (CONSULTAS[1], datetime.date(2026, 11, 18), datetime.date(2026, 11, 25))]
                     and fundir(devido, [], [], {"desde": "2026-11-18", "ate": "2026-11-25"}, {})["cobertura"]["a_reler"] == []),
        "arquivo lido só pela redação antiga deve o ciclo pelas consultas de hoje":
            lambda: (a_reler_de({"municipios": {"1": {}}, "janela_lida": {"ate": "2026-11-24"}}, datetime.date(2026, 11, 17))
                     == [(None, CICLO, datetime.date(2026, 11, 16))] and a_reler_de({}, datetime.date(2026, 11, 17)) == []),
        # O arquivo: um ato por portaria, e as duas finalidades separadas.
        "o mesmo ato lido duas vezes entra uma vez":
            lambda: (dois["municipios"]["3135605"]["atos"].__len__() == 2
                     and dois["atos_novos_nesta_rodada"] == 1),
        "resposta e recuperação somam separadas":
            lambda: dois["total_por_acao"] == {"recuperacao": 416281.64, "resposta": 1000000.0},
        "o total do município é a soma das duas":
            lambda: dois["municipios"]["3135605"]["total_autorizado"] == 1416281.64,
        # A trava de vocabulário: o arquivo não pode chamar autorização de pagamento.
        "a governança diz 'liberado', e nunca 'pago'":
            lambda: ("'liberado', nunca 'pago'" in um["_governanca"]
                     and "valor_autorizado" in um["_governanca"]),
        "a frase C18 viaja com o arquivo, como em todo arquivo de resposta":
            lambda: "art. 73, VI, a" in um.get("frase_c18", ""),
        # TRAVA ESTRUTURAL: nenhuma escrita no banco, nem numa edição futura.
        "o fonte não grava em nenhum arquivo do banco":
            lambda: not grava_no_banco(fonte_do_coletor(__file__)),
        "o fonte grava só no próprio arquivo":
            lambda: sorted(set(re.findall(r"gravar\((SAIDA|\"[^\"]+\")", fonte_do_coletor(__file__)))) == ["SAIDA"],
    }
    return rodar_autoteste(casos)


def main() -> int:
    args = sys.argv[1:]
    if "--autoteste" in args:
        return autoteste()
    desde = max(CICLO, hoje_editorial() - datetime.timedelta(days=PRIMEIRA_CARGA_DIAS))
    if "--desde" in args:
        desde = datetime.date.fromisoformat(args[args.index("--desde") + 1])
    else:
        # Incremental: relê os sete dias anteriores à última janela, para pegar ato publicado com
        # atraso ou retificado. Reler é barato; perder ato publicado fora de ordem não é.
        anterior = (ler(SAIDA) or {}).get("janela_lida") or {}
        if anterior.get("ate"):
            desde = max(CICLO, datetime.date.fromisoformat(anterior["ate"])
                        - datetime.timedelta(days=7))
    if "--relatorio" in args:
        itens, inc = varrer(desde, hoje_editorial(), buscar)
        print(json.dumps({"consultas": CONSULTAS, "desde": desde.isoformat(),
                          "atos_na_busca": len(itens),
                          "janelas_incompletas": len(inc or [])}, ensure_ascii=False, indent=1))
        return 0
    print(json.dumps(coletar(desde), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
