#!/usr/bin/env python3
"""Instantâneo dos cartões do topo de cada página, para a Imprensa LER em vez de recalcular.

Item 1 do handover "Imprensa — redesenho definitivo" (02/10/2026). O defeito medido naquele dia:

- a Imprensa dizia "sem dado" no dinheiro, com dado publicado no Financiamento;
- a Imprensa dizia 482 casos de dengue na semana 37, lendo o InfoDengue, enquanto o MARÉ Saúde
  dizia 8.146 na semana 33, lendo o Sinan — duas fontes, duas semanas e dois números para a mesma
  pergunta, em páginas vizinhas;
- a temperatura era a máxima ABSOLUTA prevista, e o recorte aprovado é o maior **desvio em relação
  ao normal**.

A raiz é uma só: a Imprensa recalculava. Cada número existia duas vezes, em dois lugares, com duas
definições — e nada obrigava as duas a concordarem. Este arquivo é a correção: ele escreve, a partir
das MESMAS fontes que cada página lê, um instantâneo com o valor, a referência (semana, mês, janela),
o rótulo e a fonte de cada cartão do topo. A Imprensa passa a ler o instantâneo.

Um número só vive num lugar; quem quiser o mesmo número, lê.

    data/saude_desfechos/topo_saude.json      · MARÉ Saúde
    data/resposta/topo_defesa_civil.json      · Defesa civil
    data/financiamento/semana.json            · Financiamento (já existia, por gerar_financiamento_semana.py)

Uso:
    python3 scripts/gerar_topo_das_paginas.py
    python3 scripts/gerar_topo_das_paginas.py --autoteste
"""
from __future__ import annotations

import json
import re
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

GOV_SAUDE = ("INSTANTÂNEO dos cartões do topo do MARÉ Saúde, para a Imprensa ler em vez de "
             "recalcular (handover de 02/10/2026, item 1). Não é fonte de nada: nasce das mesmas "
             "séries que a página lê. A semana fechada é a última com valor na "
             "série — nunca a última do calendário, porque semana recente existe no arquivo com "
             "valor nulo e tratar nulo como zero publicaria uma queda que é só atraso de "
             "notificação.")
GOV_DC = ("INSTANTÂNEO dos cartões do topo da Defesa civil, para a Imprensa ler em vez de "
          "recalcular (handover de 02/10/2026, item 1). Não é fonte de nada: nasce dos mesmos "
          "arquivos que a página lê. Os três cartões de AGORA trazem a hora da consulta; os três "
          "do ciclo trazem a contagem desde 29/06 e quantos entraram nos últimos sete dias.")


LIMITE_ALERTA_HORAS = 24   # a mesma regra de `assets/js/defesa-civil.js`


def alertas_pararam(marca, agora=None) -> "str | None":
    """A frase da parada quando o carimbo dos alertas passou das 24 horas — ou `None`.

    O carimbo vem no fuso da redação (-03:00), escrito por `coletar_sinais_risco.agora()`; a
    comparação é em UTC, para a resposta não depender de onde o código roda. `agora` existe para
    o autoteste poder provar os dois lados da fronteira sem esperar o relógio.
    """
    from datetime import datetime, timedelta, timezone
    marca = str(marca or "")
    if not marca:
        return "a coleta de avisos e alertas não tem carimbo de data"
    for formato, reserva in (("%d/%m/%Y %H:%M", timedelta()),
                             ("%d/%m/%Y", timedelta(hours=23, minutes=59))):
        try:
            d = datetime.strptime(marca[:len("01/01/2026 00:00") if " " in formato else 10],
                                  formato) + reserva
            break
        except ValueError:
            d = None
    if d is None:
        return f"a coleta de avisos e alertas tem carimbo ilegível ({marca})"
    d = d.replace(tzinfo=timezone(timedelta(hours=-3)))
    agora = agora or datetime.now(timezone.utc)
    if (agora - d).total_seconds() / 3600.0 > LIMITE_ALERTA_HORAS:
        return f"sem atualização desde {marca}: a coleta de avisos e alertas passou das 24 horas"
    return None


def ultima_fechada(serie: dict, ano: str):
    """(semana, valor) da última semana COM valor, no ano dado. Função pura."""
    ses = sorted(k for k, v in (serie or {}).items() if v is not None and str(k).startswith(ano))
    return (ses[-1], (serie or {})[ses[-1]]) if ses else (None, None)


def nacional_da_serie(serie_por_uf: dict, ano: str):
    """A série do país. Função pura.

    02/10/2026 — defeito medido: o arquivo do SIVEP-Gripe traz a linha `BR` **junto** das 27 UFs, e
    somar `serie.values()` somava o país duas vezes. O número publicado era o dobro (8.534 em vez
    de 4.267). Quando existe a linha `BR`, ela é o país; só na falta dela o país é a soma das UFs.
    """
    if not serie_por_uf:
        return {}
    if isinstance(serie_por_uf.get("BR"), dict):
        return {k: v for k, v in serie_por_uf["BR"].items() if str(k).startswith(ano)}
    total = {}
    for uf, semanas in serie_por_uf.items():
        if uf == "BR" or not isinstance(semanas, dict):
            continue
        for se, v in semanas.items():
            if str(se).startswith(ano) and isinstance(v, (int, float)):
                total[se] = total.get(se, 0) + v
    return total


def _na_semana(referencia) -> str:
    """' na semana de 30 de agosto a 5 de setembro de 2026' para '2026-35'; vazio sem semana."""
    from coletores_base import semana_do_rotulo
    quando = semana_do_rotulo(referencia)
    return f" na semana {quando}" if quando else ""


def posicao_na_faixa(valor, faixa) -> str | None:
    """'acima' | 'dentro' | 'abaixo' do valor na faixa habitual da MESMA semana; None sem os dois.
    Mesma regra de `assets/js/saude.js` (acima do p90 de 2019 a 2025). Função pura."""
    if not isinstance(valor, (int, float)) or not isinstance(faixa, dict) or faixa.get("p90") is None:
        return None
    return "acima" if valor > faixa["p90"] else ("dentro" if valor >= faixa.get("mediana", valor) else "abaixo")


def posicoes_das_ufs(desfecho: dict) -> dict:
    """{UF: posição} pela última semana CONSOLIDADA de cada UF contra a faixa da semana do valor
    (nunca de outra). É a única conta de 'estados acima da faixa'; a página lê o resultado."""
    out = {}
    for uf, u in ((desfecho or {}).get("ultimo") or {}).items():
        c = (u or {}).get("consolidado") or {}
        sem = str(c.get("periodo") or "").split("-")[-1]
        if uf != "BR" and sem:
            out[uf] = posicao_na_faixa(c.get("por_100mil"), (((desfecho or {}).get("faixa_habitual") or {}).get(uf) or {}).get(sem))
    return out


def resumo_do_desfecho(desfecho: dict) -> dict:
    """Linha do topo para um desfecho: estados acima da faixa, semana consolidada e consulta. Função pura."""
    from coletores_base import semana_intervalo
    pos = posicoes_das_ufs(desfecho)
    per = {(((u or {}).get("consolidado") or {}).get("periodo")) for uf, u in ((desfecho or {}).get("ultimo") or {}).items() if uf != "BR"}
    per.discard(None)
    unico = next(iter(per)) if len(per) == 1 else None
    ini = fim = None
    if unico:
        a, n = unico.split("-")
        ini, fim = (d.isoformat() for d in semana_intervalo(int(a), int(n)))
    br = (((desfecho or {}).get("ultimo") or {}).get("BR") or {}).get("consolidado") or {}
    comparavel = pos and all(v is not None for v in pos.values())
    return {"ufs_acima_faixa": sum(v == "acima" for v in pos.values()) if comparavel else None,
            "ufs_comparadas": sum(v is not None for v in pos.values()),
            "periodo": unico, "semana_inicio": ini, "semana_fim": fim,
            "valor_br": br.get("valor") if unico and br.get("periodo") == unico else None,
            "consultado_em": (desfecho or {}).get("coletado_em")}


def cartoes_da_saude(dengue: dict, srag: dict, painel: dict, sinais: dict, monitor: dict) -> list:
    """Os seis cartões do topo do MARÉ Saúde. Função pura — é ela que o autoteste exercita."""
    cartoes = []
    ano_d = str((dengue or {}).get("ano_corrente") or "")
    se_d, v_d = ultima_fechada(((dengue or {}).get("serie") or {}).get("BR") or {}, ano_d)
    cartoes.append({
        "id": "dengue_casos_se", "valor": v_d, "referencia": se_d,
        "rotulo": "notificações de dengue" + _na_semana(se_d),
        "fonte": "Ministério da Saúde (Sinan)", "sem_coleta": se_d is None,
        "nota": "notificações, não casos confirmados; as últimas semanas são parciais e sobem com "
                "as notificações atrasadas; este número não indica relação com o El Niño",
    })
    ano_s = str((srag or {}).get("ano_corrente") or "")
    nac = nacional_da_serie((srag or {}).get("serie") or {}, ano_s)
    se_s, v_s = ultima_fechada(nac, ano_s)
    cartoes.append({
        "id": "srag_internacoes_se", "valor": v_s, "referencia": se_s,
        "rotulo": "internações por síndrome respiratória grave" + _na_semana(se_s),
        "fonte": "Ministério da Saúde (SIVEP-Gripe)", "sem_coleta": se_s is None,
        "nota": "as últimas semanas são parciais e sobem com as notificações atrasadas; este "
                "número não indica relação com o El Niño",
    })
    M = (painel or {}).get("municipios") or {}
    ufs = sorted({m.get("uf") for m in M.values()
                  if (m.get("nivel_ultima_se") or 0) >= 3 and m.get("uf")})
    cartoes.append({
        "id": "uf_dengue_alerta", "valor": len(ufs) if M else None, "referencia": "nível atual",
        "rotulo": "estados com dengue em nível de alerta", "fonte": "InfoDengue (Fiocruz e FGV)",
        "sem_coleta": not M, "lista": ufs,
        "nota": "nível calculado pelo InfoDengue; o estado entra quando ao menos um município "
                "acompanhado está em nível 3 ou 4",
    })
    # O arquivo traz `calor_excesso.por_uf`, uma linha por estado com os quatro níveis do painel.
    # O cartão conta MUNICÍPIOS em nível severo ou extremo, que é o recorte da página.
    calor = ((sinais or {}).get("calor_excesso") or {})
    por_uf = calor.get("por_uf") or {}
    acima = None
    if por_uf:
        acima = int(sum((v.get("severo") or 0) + (v.get("extremo") or 0) for v in por_uf.values()))
    cartoes.append({
        "id": "calor_municipios_severo", "valor": acima, "referencia": calor.get("data"),
        "rotulo": "municípios em nível severo ou extremo de calor",
        "fonte": "Ministério da Saúde (Painel Nacional de Excesso de Calor)",
        "sem_coleta": acima is None,
    })
    resp = (monitor or {}).get("resposta") or {}
    cartoes.append({
        "id": "emergencias_saude_ciclo", "valor": resp.get("emergencias"),
        "referencia": resp.get("desde"),
        "rotulo": "emergências em saúde declaradas no ciclo",
        "fonte": "atos federais e estaduais lidos pelo MARÉ",
        "sem_coleta": resp.get("emergencias") is None,
    })
    # 21/10/2026 (editoria): o índice do MARÉ Saúde é NACIONAL, sobre as 27 UFs, pela regra do MARÉ
    # Legal, e o rótulo conta o estatuto em vez de dizer sobre quantas UFs a média foi tirada — é a
    # régua que a página usa, e a Imprensa lê a mesma (o portão de coerência compara as duas).
    res = (monitor or {}).get("resumo") or {}
    verificadas = res.get("verificadas")
    com_plano = res.get("ufs_com_plano_localizado")
    cartoes.append({
        "id": "mare_saude_indice", "valor": res.get("indice_nacional"),
        "referencia": (monitor or {}).get("gerado_em"),
        "rotulo": "MARÉ Saúde",
        "unidades_verificadas": verificadas,
        "fonte": "MARÉ (verificação própria)",
        "sem_coleta": res.get("indice_nacional") is None,
        "nota": (None if com_plano is None
                 else f"{com_plano} de {res.get('denominador') or 27} estados com plano localizado"),
    })
    return cartoes


# Como o leitor lê cada componente. Chave = nome no dado (`meta.json` para o MARÉ Legal,
# `monitor_saude.json` para o MARÉ Saúde); componente que não está aqui deixa o texto em lacuna.
PARTES_LEGAL = {
    "instrumento operacional estadual": "o plano estadual para o risco previsto (vale mais quando "
        "feito para este El Niño, menos quando é o plano de todo ano revisado, zero quando não "
        "localizamos)",
    "estrutura de coordenação": "a estrutura de coordenação (quem foi designado para conduzir a "
        "resposta)",
    "cobertura populacional": "a cobertura (quanta gente do estado vive em município com plano "
        "localizado)"}
PARTES_SAUDE = {   # na ordem em que o leitor as lê
    "instrumento": "o plano para os riscos deste El Niño (arboviroses, calor, água, fumaça)",
    "coordenacao": "quem coordena a resposta na saúde, sala de situação ou centro de operações",
    "cobertura": "quanta gente vive em município cujo plano trata a saúde"}
NUMERO_POR_EXTENSO = {2: "duas", 3: "três", 4: "quatro", 5: "cinco"}


def _lista(partes: list) -> str:
    return partes[0] if len(partes) == 1 else ", ".join(partes[:-1]) + " e " + partes[-1]


def definicao_dos_indices(meta: dict, monitor: dict) -> dict:
    """O parágrafo "como o índice funciona" do MARÉ Legal e do MARÉ Saúde. Função pura.

    UMA função para a Imprensa e para a abertura da Saúde (HANDOVER_IMPRENSA §4.2): o texto nasce
    dos componentes e pesos que o dado declara, e as duas páginas leem o mesmo campo. Mudou o dado,
    mudaram os dois textos. Nenhum número de versão chega ao leitor. Componente que a função não
    sabe dizer, peso desigual ou escala que não é a do Legal deixa o texto `None`: lacuna, nunca
    texto que descreva outra coisa.
    """
    d = (meta or {}).get("definicao_indice") or {}
    comp = d.get("componentes") or []
    faixas = d.get("faixas") or []
    legal = None
    if (comp and faixas and all(c.get("nome") in PARTES_LEGAL for c in comp)
            and len({c.get("peso") for c in comp}) == 1 and len(comp) in NUMERO_POR_EXTENSO):
        legal = (f"Cada estado recebe uma nota de {faixas[0][0]} a {faixas[-1][1]}, com "
                 f"{NUMERO_POR_EXTENSO[len(comp)]} partes de mesmo peso: "
                 f"{_lista([PARTES_LEGAL[c['nome']] for c in comp])}. A nota do Brasil é a média "
                 "dos estados. Decretos não entram.")
    pesos = ((monitor or {}).get("metodo") or {}).get("pesos") or {}
    partes = [PARTES_SAUDE[k] for k in PARTES_SAUDE if k in pesos]
    mesma_escala = [str(f[0]) + "–" + str(f[1]) for f in faixas] == list(
        (((monitor or {}).get("metodo") or {}).get("faixas") or {}).values())
    saude = None
    if (partes and len(partes) == len(pesos) and len(set(pesos.values())) == 1
            and mesma_escala):
        ponderada = (((monitor or {}).get("metodo") or {}).get("agregacao_nacional") or {}).get("ponderacao") == "populacao"
        saude = ("A mesma escala, para o que a secretaria estadual de saúde publicou: "
                 f"{_lista(partes)}. A nota nacional é a média dos estados"
                 + (", ponderada pela população." if ponderada else "."))
    return {"legal": legal, "saude": saude, "saude_partes": partes if saude else None}


def cartoes_da_defesa_civil(alertas: dict, decretados: dict, por_uf: dict, hoje_iso: str,
                            populacao: dict = None) -> list:
    """Os seis cartões do topo da Defesa civil. Função pura.

    A variação dos três cartões do ciclo é a contagem dos que entraram nos últimos sete dias, pela
    data do próprio ato. Os três de AGORA não têm variação: não há retrato guardado de sete dias
    atrás, e comparar com o que não foi medido seria inventar.
    """
    import datetime as dt
    res = (alertas or {}).get("resumo") or {}
    # 08/10/2026: a página Defesa civil PARA de publicar contagem de alerta depois de 24 horas sem
    # coleta ("desenhar o retrato de ontem como em vigor é o único erro desta página que pode
    # machucar alguém"), e o instantâneo do topo seguia publicando o número — de onde a Imprensa o
    # copiava. A regra passa a estar no instantâneo, que é a fonte das duas superfícies.
    if alertas_pararam((alertas or {}).get("gerado_em")):
        res = {}
    quando = (alertas or {}).get("gerado_em")
    decret = {k: v for k, v in ((decretados or {}).get("municipios") or {}).items() if v.get("decreto")}
    reconhecidos = {k: v for k, v in decret.items() if v.get("reconhecido")}
    limite = (dt.date.fromisoformat(hoje_iso) - dt.timedelta(days=7)).isoformat()

    def iso(v):
        s = str(v or "")
        return (s[6:10] + "-" + s[3:5] + "-" + s[0:2]) if len(s) >= 10 and s[2] == "/" else None

    recentes = [k for k, v in decret.items() if (iso(v.get("primeiro_decreto")) or "") >= limite]
    novos = len(recentes)
    # A população de quem entrou na semana sai do Censo 2022 pelo código IBGE. Sem o arquivo, o
    # cartão fica sem variação — e não com uma variação estimada.
    pop_nova = (sum(int((populacao or {}).get(k) or 0) for k in recentes)
                if populacao else None) or None
    novos_rec = sum(1 for v in reconhecidos.values()
                    if (iso(((v.get("fontes") or [{}])[0]).get("data")) or "") >= limite)
    nacional = (por_uf or {}).get("nacional") or {}
    # Sexto cartão: decreto sem reconhecimento há mais de 30 dias (mesma régua da página). Os dias
    # são campo do consolidado; sem eles em nenhum município o cartão é "sem coleta", nunca zero.
    # A variação são os que cruzaram os 30 dias na semana (de 31 a 37 dias), contagem bruta como
    # a dos cartões do ciclo.
    dias = [v["dias_sem_reconhecimento"] for v in decret.values()
            if not v.get("reconhecido") and v.get("dias_sem_reconhecimento") is not None]
    return [
        {"id": "municipios_alerta_cemaden", "valor": res.get("municipios_cemaden"),
         "referencia": quando, "rotulo": "municípios sob alerta do Cemaden",
         "fonte": "Cemaden", "sem_coleta": not res},
        {"id": "municipios_aviso_inmet", "valor": res.get("municipios_inmet"),
         "referencia": quando, "rotulo": "municípios sob aviso do Inmet",
         "fonte": "Inmet", "sem_coleta": not res},
        {"id": "municipios_decretaram", "valor": len(decret) or nacional.get("n_municipios"),
         "referencia": "desde 29/06/2026", "variacao": novos,
         "rotulo": "municípios que decretaram emergência ou calamidade",
         "fonte": "Defesa Civil nacional, no Diário Oficial da União",
         "sem_coleta": not decret and nacional.get("n_municipios") is None},
        {"id": "populacao_sob_decreto", "valor": nacional.get("pop_sob_decreto"),
         "referencia": "desde 29/06/2026", "variacao": pop_nova,
         "rotulo": "pessoas que vivem nos municípios que decretaram",
         "fonte": "Censo 2022, do IBGE",
         "sem_coleta": nacional.get("pop_sob_decreto") is None},
        {"id": "reconhecidos_pelo_governo_federal",
         "valor": len(reconhecidos) or nacional.get("reconhecidos"),
         "referencia": "desde 29/06/2026", "variacao": novos_rec,
         "rotulo": "municípios com a emergência reconhecida pelo governo federal",
         "fonte": "Defesa Civil nacional, no Diário Oficial da União",
         "sem_coleta": not reconhecidos and nacional.get("reconhecidos") is None},
        {"id": "decreto_sem_reconhecimento_30_dias", "valor": sum(d > 30 for d in dias) if dias else None,
         "referencia": "desde 29/06/2026", "variacao": sum(30 < d <= 37 for d in dias) if dias else None,
         "rotulo": "municípios com decreto há mais de 30 dias sem reconhecimento federal",
         "fonte": "Defesa Civil nacional, no Diário Oficial da União", "sem_coleta": not dias},
    ]


GOV_RISCOS = ("INSTANTÂNEO dos números de agora do Monitor de riscos, para a Imprensa e a página "
              "lerem em vez de recalcular (handover de 02/10/2026, item 1; HANDOVER_TEXTOS_B §10.3). "
              "Não é fonte de nada. Cada cartão guarda em `anterior` o valor e a referência da leitura "
              "anterior; sem leitura anterior, o campo não existe. Avisos: avisos distintos no país. O de "
              "temperatura é o maior DESVIO em relação à normal 1991–2020 do Inmet, e não a máxima "
              "absoluta: 35 °C é normal em Cuiabá e muito quente em Porto Alegre, e publicar a "
              "máxima absoluta era publicar geografia como se fosse notícia — mesma régua do mapa "
              "de calor da página.")


TRIMESTRES = {"DJF": 1, "JFM": 2, "FMA": 3, "MAM": 4, "AMJ": 5, "MJJ": 6, "JJA": 7, "JAS": 8,
              "ASO": 9, "SON": 10, "OND": 11, "NDJ": 12}


def cartoes_de_agora(sinais: dict, vigentes: dict) -> list:
    """Os números de agora do Monitor de riscos que ainda não tinham instantâneo (HANDOVER_TEXTOS_B
    §10.3): fogo, seca, avisos e probabilidade. Mesmas regras da faixa da página. Função pura.

    Avisos: a contagem NACIONAL é de avisos DISTINTOS (um aviso que cobre três UFs conta um), lida
    de `alertas/vigentes.json` pelo identificador do aviso; "perigo ou maior" é Perigo e Grande
    Perigo, no vocabulário do INMET."""
    ufs = (sinais or {}).get("uf") or {}
    fontes = (sinais or {}).get("fontes") or {}
    cartoes = []
    focos = {uf: (u.get("fogo") or {}).get("focos_24h") for uf, u in ufs.items()}
    focos = {uf: n for uf, n in focos.items() if isinstance(n, (int, float))}
    ufmax = max(focos, key=lambda k: focos[k]) if focos else None
    cartoes.append({"id": "fogo_focos_24h", "valor": sum(focos.values()) if focos else None,
                    "referencia": (fontes.get("inpe_fogo") or {}).get("documento"),
                    "uf_com_mais_focos": ufmax if ufmax and focos[ufmax] > 0 else None,
                    "fonte": "Inpe", "sem_coleta": not focos})
    secas = {uf: (u.get("secas") or {}) for uf, u in ufs.items() if (u.get("secas") or {}).get("categoria_mediana")}
    cartoes.append({"id": "seca_estados_grave_ou_pior",
                    "valor": sum(1 for v in secas.values() if v["categoria_mediana"] in ("S2", "S3", "S4")) if secas else None,
                    "referencia": next((v.get("mapa") for v in secas.values() if v.get("mapa")), None),
                    "fonte": "Monitor de Secas (ANA)", "sem_coleta": not secas})
    avisos, perigo = set(), set()
    for m in ((vigentes or {}).get("municipios") or {}).values():
        for a in m.get("inmet") or []:
            if a.get("id"):
                avisos.add(a["id"])
                if a.get("severidade") in ("Perigo", "Grande Perigo"):
                    perigo.add(a["id"])
    tem_avisos = bool((vigentes or {}).get("municipios"))
    cartoes.append({"id": "avisos_inmet_distintos", "valor": len(avisos) if tem_avisos else None,
                    "perigo_ou_maior": len(perigo) if tem_avisos else None,
                    "referencia": (vigentes or {}).get("gerado_em"), "fonte": "Inmet",
                    "sem_coleta": not tem_avisos})
    trims = []
    for t in (((sinais or {}).get("enos") or {}).get("probabilidades") or {}).get("trimestres") or []:
        m = re.match(r"^([A-Z]{3})\s*(\d{4})$", str(t.get("trimestre") or "").strip().upper())
        if m and m.group(1) in TRIMESTRES and t.get("el_nino") is not None:
            trims.append((int(m.group(2)) * 12 + TRIMESTRES[m.group(1)], f"{m.group(1)} {m.group(2)}", t["el_nino"]))
    trims.sort()
    altos = [t for t in trims if t[2] >= 90]
    marco = (altos[-1] if altos else trims[0]) if trims else None
    cartoes.append({"id": "probabilidade_el_nino", "valor": round(marco[2]) if marco else None,
                    "trimestre": marco[1] if marco else None,
                    "referencia": (fontes.get("iri_plume") or {}).get("consultado_em"),
                    "fonte": "IRI/CPC", "sem_coleta": marco is None})
    return cartoes


def com_anterior(novos: list, antigos: list) -> list:
    """Põe em cada cartão o valor da leitura ANTERIOR, com a referência dela. Função pura.

    Mesma referência que a gravada: é a mesma leitura, e o `anterior` que ela já tinha fica.
    Referência nova: o valor gravado vira `anterior`. Sem leitura anterior, o campo não existe —
    e a página diz "primeira leitura", nunca uma variação inventada."""
    velhos = {c.get("id"): c for c in antigos or [] if isinstance(c, dict)}
    for c in novos:
        v = velhos.get(c["id"])
        if not v or c.get("valor") is None:
            continue
        if v.get("referencia") == c.get("referencia"):
            if v.get("anterior"):
                c["anterior"] = v["anterior"]
        elif v.get("valor") is not None:
            c["anterior"] = {"valor": v["valor"], "referencia": v.get("referencia")}
    return novos


def cartoes_do_monitor_de_riscos(sinais: dict, normais: dict) -> list:
    """Os dois números do Monitor de riscos que a Imprensa publica. Função pura.

    Capital sem normal publicada fica SEM desvio — nunca com desvio estimado. Zero significaria
    "está na média", que é uma afirmação que o dado não sustenta.
    """
    ufs = (sinais or {}).get("uf") or {}
    caps = (normais or {}).get("capitais") or {}
    melhor = None
    com_normal = 0
    for uf, u in ufs.items():
        t = (u.get("temperatura") or {})
        tmax = t.get("tmax")
        serie = (caps.get(uf) or {}).get("tmax")
        if tmax is None or not isinstance(serie, list):
            continue
        data = str(t.get("data") or "")
        mes = int(data[3:5]) if len(data) >= 10 and data[2] == "/" else None
        normal = serie[mes - 1] if mes and len(serie) >= mes else None
        if not isinstance(normal, (int, float)):
            continue
        com_normal += 1
        desvio = round(tmax - normal, 1)
        if melhor is None or desvio > melhor["desvio"]:
            melhor = {"uf": uf, "capital": t.get("capital"), "desvio": desvio, "tmax": tmax,
                      "normal": normal, "data": t.get("data")}
    cartoes = [{
        "id": "temperatura_desvio_capital",
        "valor": melhor["desvio"] if melhor else None,
        "referencia": melhor["data"] if melhor else None,
        "rotulo": ("a maior diferença de temperatura máxima em relação ao normal, em "
                   + (melhor["capital"] or melhor["uf"]) if melhor
                   else "a maior diferença de temperatura máxima em relação ao normal"),
        "capital": melhor["capital"] if melhor else None,
        "uf": melhor["uf"] if melhor else None,
        "fonte": "Inmet (previsão para as capitais e normal de 1991 a 2020)",
        "sem_coleta": melhor is None,
        "nota": (f"máxima prevista de {melhor['tmax']} °C contra a média de {melhor['normal']} °C "
                 f"do mês; {com_normal} capital(is) com normal publicada" if melhor else None),
    }]
    return cartoes


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

    ok("última fechada ignora semana com valor nulo",
       ultima_fechada({"2026-33": 10, "2026-34": None}, "2026") == ("2026-33", 10))
    ok("última fechada ignora outro ano",
       ultima_fechada({"2025-50": 9, "2026-02": 3}, "2026") == ("2026-02", 3))
    ok("série vazia devolve nada", ultima_fechada({}, "2026") == (None, None))
    D = {"coletado_em": "2026-10-18",
         "ultimo": {"AC": {"consolidado": {"periodo": "2026-35", "por_100mil": 20.0}},
                    "AL": {"consolidado": {"periodo": "2026-35", "por_100mil": 5.0}},
                    "AM": {"consolidado": {"periodo": "2026-35", "por_100mil": 1.0}},
                    "BR": {"consolidado": {"periodo": "2026-35", "valor": 99}}},
         "faixa_habitual": {u: {"35": {"mediana": 4.0, "p90": 10.0}, "09": {"mediana": 0.0, "p90": 0.1}} for u in ("AC", "AL", "AM")}}
    r = resumo_do_desfecho(D)
    ok("estados acima da faixa: acima do p90 da semana do valor, dentro e abaixo não contam",
       posicoes_das_ufs(D) == {"AC": "acima", "AL": "dentro", "AM": "abaixo"} and r["ufs_acima_faixa"] == 1 and r["ufs_comparadas"] == 3)
    ok("semana consolidada em datas ISO (domingo a sábado) e BR só se for da mesma semana",
       (r["semana_inicio"], r["semana_fim"]) == ("2026-08-30", "2026-09-05") and r["valor_br"] == 99)
    D["ultimo"]["BR"]["consolidado"]["periodo"] = "2026-09"
    ok("BR de outra semana não vira número do topo", resumo_do_desfecho(D)["valor_br"] is None)
    del D["faixa_habitual"]["AC"]["35"]
    ok("UF sem faixa na semana: o total vira lacuna, não zero", resumo_do_desfecho(D)["ufs_acima_faixa"] is None)

    com_br = {"BR": {"2026-35": 4267}, "SP": {"2026-35": 1000}, "RJ": {"2026-35": 500}}
    ok("com linha BR o país é a linha BR, e não a soma",
       nacional_da_serie(com_br, "2026") == {"2026-35": 4267})
    sem_br = {"SP": {"2026-35": 1000}, "RJ": {"2026-35": 500}}
    ok("sem linha BR o país é a soma das UFs",
       nacional_da_serie(sem_br, "2026") == {"2026-35": 1500})
    ok("série ausente não quebra", nacional_da_serie({}, "2026") == {})

    saude = cartoes_da_saude(
        {"ano_corrente": 2026, "serie": {"BR": {"2026-33": 8146, "2026-34": None}}},
        {"ano_corrente": 2026, "serie": com_br},
        {"municipios": {"1": {"uf": "SP", "nivel_ultima_se": 3}, "2": {"uf": "RJ", "nivel_ultima_se": 1}}},
        {"calor_excesso": {"data": "2026-09-25",
                           "por_uf": {"PA": {"severo": 4, "extremo": 1}, "MG": {"severo": 0}}}},
        {"resumo": {"indice_nacional": 24.8, "verificadas": 21,
                    "denominador": 27, "ufs_com_plano_localizado": 21},
         "resposta": {"emergencias": 2, "desde": "29/06/2026"}})
    por_id = {c["id"]: c for c in saude}
    ok("dengue sai do Sinan, pela última semana fechada",
       por_id["dengue_casos_se"]["valor"] == 8146 and por_id["dengue_casos_se"]["referencia"] == "2026-33")
    ok("dengue declara que são notificações", "notificações" in por_id["dengue_casos_se"]["nota"])
    ok("respiratórias não dobram o país", por_id["srag_internacoes_se"]["valor"] == 4267)
    ok("estados em alerta contam estado, não município", por_id["uf_dengue_alerta"]["valor"] == 1)
    ok("calor soma severo e extremo", por_id["calor_municipios_severo"]["valor"] == 5)
    # 21/10/2026: o cartão é o índice NACIONAL. O caso guarda os dois campos de propósito — o antigo
    # ainda existe no arquivo, e o cartão não pode voltar a ele.
    ok("o índice é o nacional, não a média das verificadas",
       por_id["mare_saude_indice"]["valor"] == 24.8)
    ok("emergência sem busca é sem coleta, não zero", next(c for c in cartoes_da_saude(
        {}, {}, {}, {}, {"resposta": {"situacao": "nao_coletado", "emergencias": None}})
        if c["id"] == "emergencias_saude_ciclo")["sem_coleta"])
    ok("o índice conta o estatuto, sobre as 27",
       por_id["mare_saude_indice"]["unidades_verificadas"] == 21
       and por_id["mare_saude_indice"]["nota"] == "21 de 27 estados com plano localizado")
    ok("o rótulo diz as datas da semana, nunca 'semana epidemiológica'",
       por_id["dengue_casos_se"]["rotulo"] == "notificações de dengue na semana de 16 a 22 de "
       "agosto de 2026" and not any("epidemiol" in c["rotulo"] for c in saude))
    meta = {"definicao_indice": {"componentes": [
        {"nome": n, "peso": "1/3"} for n in PARTES_LEGAL],
        "faixas": [[0, 25, "a"], [25, 50, "b"], [50, 70, "c"], [70, 100, "d"]]}}
    mon = {"metodo": {"pesos": {"instrumento": 1.0}, "agregacao_nacional": {"ponderacao": "populacao"},
                      "faixas": {"a": "0–25", "b": "25–50", "c": "50–70", "d": "70–100"}}}
    df = definicao_dos_indices(meta, mon)
    ok("a definição do Legal sai do dado, com três partes de mesmo peso",
       df["legal"].startswith("Cada estado recebe uma nota de 0 a 100, com três partes de mesmo "
                              "peso: o plano estadual") and "versão" not in df["legal"])
    ok("a definição da Saúde tem uma parte, o instrumento, sem data, e o nacional pesa a população",
       "publicou: o plano para os riscos deste El Niño (arboviroses, calor, água, fumaça). A nota nacional é a média dos estados, ponderada pela população." in df["saude"]
       and "boletim" not in df["saude"] and "já verificados" not in df["saude"])
    mon["metodo"]["pesos"] = {"instrumento": 0.5, "coordenacao": 0.5}
    ok("mudar o componente no dado muda o texto da Saúde",
       "quem coordena a resposta na saúde" in definicao_dos_indices(meta, mon)["saude"]
       and "boletim" not in definicao_dos_indices(meta, mon)["saude"])
    mon["metodo"]["agregacao_nacional"] = {}
    ok("sem a ponderação no dado, o texto não a afirma",
       definicao_dos_indices(meta, mon)["saude"].endswith("A nota nacional é a média dos estados."))
    ok("componente que a função não conhece deixa lacuna, não texto",
       definicao_dos_indices({"definicao_indice": {"componentes": [{"nome": "novo", "peso": "1"}],
                                                   "faixas": [[0, 100, "x"]]}}, mon)["legal"] is None
       and definicao_dos_indices(meta, {})["saude"] is None)
    ok("série ausente vira sem_coleta, nunca zero",
       cartoes_da_saude({}, {}, {}, {}, {})[0]["sem_coleta"] is True
       and cartoes_da_saude({}, {}, {}, {}, {})[0]["valor"] is None)

    # 08/10/2026: o carimbo do fixture passa a ser RELATIVO ao relógio do teste. Com data fixa, a
    # regra das 24 horas zeraria o resumo e os três casos abaixo reprovariam por envelhecimento do
    # fixture, não por defeito do código.
    from datetime import datetime as _dt, timedelta as _td, timezone as _tz
    _fresco = (_dt.now(_tz(_td(hours=-3))) - _td(hours=1)).strftime("%d/%m/%Y %H:%M")
    _velho = (_dt.now(_tz(_td(hours=-3))) - _td(hours=30)).strftime("%d/%m/%Y %H:%M")
    ok("carimbo de uma hora não para a contagem", alertas_pararam(_fresco) is None)
    ok("carimbo de trinta horas para a contagem", bool(alertas_pararam(_velho)))
    ok("carimbo ausente para a contagem", bool(alertas_pararam("")))
    _parado = cartoes_da_defesa_civil(
        {"gerado_em": _velho, "resumo": {"municipios_cemaden": 13, "municipios_inmet": 2886},
         "municipios": {"3550308": {}}},
        {"municipios": {}}, {"nacional": {}}, "2026-10-02", {})
    _pp = {c["id"]: c for c in _parado}
    ok("alerta velho não publica contagem, e declara a parada",
       _pp["municipios_alerta_cemaden"]["valor"] is None
       and _pp["municipios_alerta_cemaden"]["sem_coleta"] is True)

    dc = cartoes_da_defesa_civil(
        {"gerado_em": _fresco, "resumo": {"municipios_cemaden": 13, "municipios_inmet": 2886},
         "municipios": {"3550308": {}, "9999999": {}}},
        {"municipios": {"3550308": {"decreto": True, "primeiro_decreto": "01/10/2026",
                                    "reconhecido": True, "fontes": [{"data": "01/10/2026"}]},
                        "2900207": {"decreto": True, "primeiro_decreto": "09/08/2026",
                                    "reconhecido": False, "fontes": [{"data": "09/08/2026"}]}}},
        {"nacional": {"n_municipios": 736, "pop_sob_decreto": 21262196, "reconhecidos": 656}},
        "2026-10-02", {"3550308": 11451245, "2900207": 17000})
    pid = {c["id"]: c for c in dc}
    ok("alerta do Cemaden vem do resumo", pid["municipios_alerta_cemaden"]["valor"] == 13)
    ok("aviso do Inmet vem do resumo", pid["municipios_aviso_inmet"]["valor"] == 2886)
    ok("quem decretou conta o conjunto do consolidado", pid["municipios_decretaram"]["valor"] == 2)
    ok("a variação da semana conta o ato dos últimos sete dias",
       pid["municipios_decretaram"]["variacao"] == 1)
    ok("a população da semana é a de quem entrou na semana",
       pid["populacao_sob_decreto"]["variacao"] == 11451245)
    ok("sem arquivo de população o cartão fica sem variação",
       cartoes_da_defesa_civil(
           {"gerado_em": "x", "resumo": {"municipios_cemaden": 1}, "municipios": {}},
           {"municipios": {"1": {"decreto": True, "primeiro_decreto": "01/10/2026"}}},
           {"nacional": {"pop_sob_decreto": 10}}, "2026-10-02")[3]["variacao"] is None)
    ok("o sexto cartão conta decreto sem reconhecimento há mais de 30 dias e quem cruzou na semana",
       cartoes_da_defesa_civil({}, {"municipios": {
           "1": {"decreto": True, "dias_sem_reconhecimento": 45}, "2": {"decreto": True, "dias_sem_reconhecimento": 33},
           "3": {"decreto": True, "dias_sem_reconhecimento": 10},
           "4": {"decreto": True, "reconhecido": True, "dias_sem_reconhecimento": 90}}}, {}, "2026-10-02")[5]
       ["valor"] == 2 and cartoes_da_defesa_civil({}, {"municipios": {"1": {"decreto": True}}}, {},
                                                  "2026-10-02")[5]["sem_coleta"] is True)
    ok("os cartões de agora não trazem variação",
       all("variacao" not in pid[i] for i in ("municipios_alerta_cemaden", "municipios_aviso_inmet")))
    ok("sem alerta coletado o cartão é sem_coleta",
       cartoes_da_defesa_civil({}, {}, {}, "2026-10-02")[0]["sem_coleta"] is True)

    riscos = cartoes_do_monitor_de_riscos(
        {"uf": {"SP": {"temperatura": {"capital": "São Paulo", "tmax": 30.0, "data": "02/10/2026"}},
                "MT": {"temperatura": {"capital": "Cuiabá", "tmax": 35.0, "data": "02/10/2026"}}}},
        {"capitais": {"SP": {"tmax": [0] * 9 + [26.5, 0, 0]},
                      "MT": {"tmax": [0] * 9 + [34.0, 0, 0]}}})
    rid = {c["id"]: c for c in riscos}
    ok("o calor é o maior DESVIO, não a maior máxima",
       rid["temperatura_desvio_capital"]["capital"] == "São Paulo"
       and rid["temperatura_desvio_capital"]["valor"] == 3.5)
    ok("capital sem normal publicada não entra",
       cartoes_do_monitor_de_riscos(
           {"uf": {"RR": {"temperatura": {"tmax": 38.0, "data": "02/10/2026"}}}},
           {"capitais": {}})[0]["sem_coleta"] is True)
    ok("o índice europeu de ar saiu com a fonte (16/10/2026)", "capitais_ar_ruim_ou_pior" not in rid)

    agora = {c["id"]: c for c in cartoes_de_agora(
        {"uf": {"PA": {"fogo": {"focos_24h": 163}, "secas": {"categoria_mediana": "S2", "mapa": "Setembro/2026"}},
                "AM": {"fogo": {"focos_24h": 188}, "secas": {"categoria_mediana": "S1"}}},
         "fontes": {"inpe_fogo": {"documento": "focos_diario_br_20261015.csv"}},
         "enos": {"probabilidades": {"trimestres": [{"trimestre": "OND 2026", "el_nino": 99},
                                                    {"trimestre": "JFM 2027", "el_nino": 92},
                                                    {"trimestre": "AMJ 2027", "el_nino": 60}]}}},
        {"gerado_em": "16/10/2026 15:46", "municipios": {
            "1": {"inmet": [{"id": "a", "severidade": "Perigo"}, {"id": "b", "severidade": "Perigo Potencial"}]},
            "2": {"inmet": [{"id": "a", "severidade": "Perigo"}]}}})}
    ok("fogo soma os focos e diz o estado com mais focos no dia",
       agora["fogo_focos_24h"]["valor"] == 351 and agora["fogo_focos_24h"]["uf_com_mais_focos"] == "AM")
    ok("seca conta estados com mediana S2 ou pior", agora["seca_estados_grave_ou_pior"]["valor"] == 1)
    ok("avisos: o mesmo aviso em dois municípios conta um no país",
       agora["avisos_inmet_distintos"]["valor"] == 2 and agora["avisos_inmet_distintos"]["perigo_ou_maior"] == 1)
    ok("probabilidade: último trimestre com 90% ou mais", agora["probabilidade_el_nino"]["valor"] == 92
       and agora["probabilidade_el_nino"]["trimestre"] == "JFM 2027")
    ok("sem dado o cartão é sem_coleta, nunca zero",
       all(c["sem_coleta"] and c["valor"] is None for c in cartoes_de_agora({}, {})))
    v1 = com_anterior([{"id": "x", "valor": 5, "referencia": "d2"}], [{"id": "x", "valor": 3, "referencia": "d1"}])
    v2 = com_anterior([{"id": "x", "valor": 5, "referencia": "d2"}], v1)
    ok("leitura nova guarda a anterior com a referência dela; a mesma leitura mantém o anterior",
       v1[0]["anterior"] == {"valor": 3, "referencia": "d1"} and v2[0]["anterior"] == {"valor": 3, "referencia": "d1"})
    ok("sem leitura anterior não há campo anterior", "anterior" not in com_anterior([{"id": "x", "valor": 1}], [])[0])

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else f"✓ AUTOTESTE OK — {len(_casos_contados)} casos, sem rede e sem escrita em data/.")
    return 1 if falhas else 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return _autoteste()
    from coletores_base import gravar, hoje_editorial

    def ler(rel, padrao=None):
        p = RAIZ / "data" / rel
        if not p.exists():
            return padrao
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            return padrao

    hoje = hoje_editorial()
    saude = cartoes_da_saude(
        ler("saude_desfechos/dengue_sinan_serie.json", {}) or {},
        ler("saude_desfechos/srag_serie.json", {}) or {},
        ler("saude_desfechos/serie_painel.json", {}) or {},
        ler("saude_sinais.json", {}) or {},
        ler("monitor_saude.json", {}) or {})
    gravar("saude_desfechos/topo_saude.json",
           {"_governanca": GOV_SAUDE, "gerado_em": hoje.strftime("%d/%m/%Y"), "cartoes": saude,
            "desfechos": {n: resumo_do_desfecho(ler(f"saude_desfechos/{n}.json", {}) or {})
                          for n in ("dengue", "chikungunya", "srag")},
            "definicao_dos_indices": definicao_dos_indices(ler("meta.json", {}) or {},
                                                           ler("monitor_saude.json", {}) or {})})
    dc = cartoes_da_defesa_civil(
        ler("alertas/vigentes.json", {}) or {},
        ler("resposta/municipios_decretados.json", {}) or {},
        ler("resposta/por_uf.json", {}) or {},
        hoje.isoformat(), ler("populacao_censo2022.json", {}) or {})
    # Todo arquivo de `data/resposta/` carrega a frase do C18 (§32): é o portão da resposta que a
    # cobra, e com razão — quem abre um arquivo daquela pasta tem de ler, ali, o que o período
    # eleitoral deixa aberto. Ela vem do arquivo de origem, nunca escrita aqui.
    por_uf_arq = ler("resposta/por_uf.json", {}) or {}
    gravar("resposta/topo_defesa_civil.json",
           {"_governanca": GOV_DC, "gerado_em": hoje.strftime("%d/%m/%Y"),
            "frase_c18": por_uf_arq.get("frase_c18"), "cartoes": dc})
    sinais = ler("sinais_risco.json", {}) or {}
    riscos = com_anterior(
        cartoes_do_monitor_de_riscos(sinais, ler("normais_capitais.json", {}) or {})
        + cartoes_de_agora(sinais, ler("alertas/vigentes.json", {}) or {}),
        (ler("topo_monitor_riscos.json", {}) or {}).get("cartoes"))
    gravar("topo_monitor_riscos.json",
           {"_governanca": GOV_RISCOS, "gerado_em": hoje.strftime("%d/%m/%Y"), "cartoes": riscos})
    for nome, cartoes in (("MARÉ Saúde", saude), ("Defesa civil", dc), ("Monitor de riscos", riscos)):
        vazios = [c["id"] for c in cartoes if c.get("sem_coleta")]
        print(f"→ {nome}: {len(cartoes)} cartão(ões)"
              + (f" · sem coleta: {', '.join(vazios)}" if vazios else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
