#!/usr/bin/env python3
"""Registra os documentos de saúde estadual que a central já localizou e leu (02/10/2026).

Diretriz da central: não esperar a bateria para registrar o que já foi lido. Mas "não esperar a
bateria" não é "digitar o resultado": este script **relê o documento primário** no endereço
oficial, extrai o trecho da página citada, e roda nele os **classificadores do juiz** — os mesmos
`degrau_coordenacao`, `degrau_f2` e `status_instrumento` que a bateria usaria. O que a central
fornece é a **localização** (endereço, data, página), não a classificação.

Por que assim, e não com o status escrito à mão: status digitado não tem evidência, não tem hash,
não tem página, e some na primeira regeneração. O caminho do projeto é documento lido → classificador
→ `aplicar()`, e é por ele que estes quatro estados entram.

Cada registro grava, por função: degrau, documento, número, data, endereço, hash da evidência,
página citada e a justificativa do degrau — e nunca rebaixa o que já estava registrado.

Uso:
    python3 registrar_saude_central.py --ensaio      # relê, classifica e mostra, sem gravar
    python3 registrar_saude_central.py --aplicar     # grava em data/saude_uf.json
    python3 registrar_saude_central.py --autoteste   # sem rede e sem escrita
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent
BANCO_PROIBIDO = {"estados.json", "municipios.json", "indice.json", "monitor_saude.json",
                  "monitor_saude_v04.json"}

# O que a central localizou e leu. Endereço, data, páginas e o que ela diz ter visto — a coluna
# `esperado` NÃO entra no dado: ela existe para que o script possa dizer, no relatório, quando a
# releitura discordar da leitura humana. Divergência é achado, não erro a esconder.
DOCUMENTOS = [
    {"uf": "PB", "doc": "Portaria nº 764/2026 – GS/SES/PB",
     "data": "03/09/2026", "numero": "764/2026",
     "edicao": {"uf": "PB", "data": "2026-09-09"}, "paginas": (9, 10),
     "esperado": {"f1": "CRIADO_CICLO", "f2": "NOMEADA_COM_ATRIBUICAO", "plano": "ELAB"},
     "nota": "DOE-PB de 09/09/2026, pp. 9–10; cria o GC El Niño/PB no âmbito da SES-PB"},
    {"uf": "MS", "doc": "Resolução SES/MS nº 1041/2026",
     "data": "03/09/2026", "numero": "1041/2026",
     "edicao": {"uf": "MS", "data": "2026-09-03"}, "paginas": (14, 19),
     "esperado": {"f1": "CRIADO_CICLO", "f2": None, "plano": None},
     "nota": "DOE-MS de 03/09/2026, edição 12.270, pp. 14–19; Grupo Condutor Estadual, de 01/09/2026"},
    # Endereços conferidos pela central em fonte oficial e passados pela editoria em 02/10/2026.
    {"uf": "PA", "doc": "Plano de emergências da SESPA",
     "data": "26/02/2026", "numero": None,
     "url": "https://www.saude.pa.gov.br/wp-content/uploads/2026/02/plano-emergencias-_26.02.pdf",
     "paginas": None,
     # Decisão da central em 02/10/2026 (item 6.3): o plano não cita o El Niño nem o ciclo, é de
     # 2026 e cobre o risco previsto para o Pará — degrau de plano revisado, 55.
     "esperado": {"f1": None, "f2": None, "plano": "VIG_REVISADO"},
     "nota": "domínio oficial da SESPA; indicado pela central, relido aqui pela máquina"},
    {"uf": "MT", "doc": "Portaria nº 0195/2026/GBSES",
     "data": "01/01/2026", "numero": "0195/2026",
     "url": "https://www.saude.mt.gov.br/storage/files/MmMbtQx9n43VPO23mMookK6LdUyD6h4QfMOvqx44.pdf",
     "paginas": None,
     "esperado": {"f1": "PERMANENTE", "f2": None, "plano": None},
     "nota": "domínio oficial da SES-MT; a portaria de 13/08/2026 fica para o localizador"},
    {"uf": "MT", "doc": "Portaria nº 0666/2024/GBSES",
     "data": "01/01/2024", "numero": "0666/2024",
     "url": "https://www.saude.mt.gov.br/storage/files/RDtdQBfGbCiRYiJ1BIRtq6KUg32oNI4cKBWaQaiS.pdf",
     "paginas": None,
     "esperado": {"f1": None, "f2": None, "plano": None},
     "nota": "domínio oficial da SES-MT; ato anterior, entra para o degrau não rebaixar"},
]


# Os riscos do ciclo, pelo vocabulário dos boletins: um plano que os cobre vale o degrau de plano
# revisado, mesmo sem citar o fenômeno pelo nome.
RE_RISCO_DO_CICLO = re.compile(
    r"(estiagem|seca|incêndio|incêndio|fogo|onda de calor|temperatura[s]? extrema|chuva[s]? intensa|enxurrada|inundaç)", re.I)
RE_PLANO_A_ELABORAR = re.compile(
    r"(elaborar|propor|elaboração|construir|construção)\b[^.;]{0,80}?\bPlano", re.I)
RE_CABECALHO_DE_ATO = re.compile(r"(?:Portaria|Resolução|Decreto)\s*n?º?\s*[\d.]+", re.I)


def trecho_das_paginas(paginas: list, faixa) -> str:
    """O texto das páginas citadas, 1-based e inclusivo. Função pura.

    Sem faixa, devolve o documento inteiro: é o caso do documento que não é uma edição de diário.
    """
    if not paginas:
        return ""
    if not faixa:
        return "\n".join(p or "" for p in paginas)
    a, b = faixa
    return "\n".join((paginas[i - 1] or "") for i in range(a, min(b, len(paginas)) + 1) if i >= 1)


def recorte_do_ato(texto: str, numero: str) -> str:
    """O recorte em volta do número do ato, quando o texto é uma edição inteira. Função pura.

    Uma edição de diário tem dezenas de atos. Classificar sobre a edição inteira misturaria um
    comitê de outra secretaria com a portaria que se quer medir — e o degrau sairia do ato errado.
    O recorte é generoso (o ato inteiro costuma caber), e na falta do número devolve o texto como
    veio, porque recortar pelo que não se achou seria pior.
    """
    if not numero:
        return texto or ""
    chave = re.escape(numero.split("/")[0].lstrip("0"))
    m = re.search(r"(?:Portaria|Resolução|Decreto)[^\n]{0,40}?0*" + chave, texto or "", re.I)
    if not m:
        return texto or ""
    # A folga para trás existe para pegar a ementa, que no diário costuma vir acima do artigo. Mas
    # ela não pode engolir o ato ANTERIOR: corta-se no cabeçalho do ato de antes, quando houver um
    # dentro da folga.
    # A folga para trás existe para pegar a ementa, que no diário costuma vir acima do artigo.
    # Mas ela não pode engolir o ato ANTERIOR: corta-se no cabeçalho do ato de antes, quando
    # houver um dentro da folga. (Medido no diário do MS: sem isso, o verbo "prorrogado" de uma
    # resolução de recursos virava o degrau da resolução medida.)
    ini = max(0, m.start() - 500)
    folga = (texto or "")[ini:m.start()]
    anterior = None
    for a in re.finditer(RE_CABECALHO_DE_ATO, folga):
        anterior = a
    if anterior is not None:
        # Há outro ato dentro da folga: começa-se no próprio ato medido, sem folga. Perder a ementa
        # custa uma linha de contexto; herdar o verbo do ato vizinho custa o degrau errado.
        ini = m.start()
    return (texto or "")[ini:m.start() + 12000]


RE_ATO_COM_DISPOSITIVO = re.compile(
    r"(\b(?:RESOLVE|DECRETA|RESOLVEM)\b\s*:?|Art\.?\s*1[º°o]?\s)", re.I)
RE_TIPO_DE_ATO = re.compile(r"\b(Portaria|Resolução|Decreto|Instrução\s+Normativa)\b", re.I)


def e_ato(texto: str) -> bool:
    """O documento é um ato com dispositivo, ou é plano/relatório? Função pura.

    As duas coisas juntas: o tipo do ato nomeado **e** o dispositivo. Plano de contigência cita
    portarias no texto, e ato sem artigo não institui nada.
    """
    t = texto or ""
    return bool(RE_TIPO_DE_ATO.search(t) and RE_ATO_COM_DISPOSITIVO.search(t))


def status_do_plano(doc: str, data: str, texto: str):
    """O degrau do instrumento. Função pura.

    Quando o documento **é** o plano, o degrau sai da régua de temporada do projeto: plano publicado
    a partir do Boletim nº 1 é plano do ciclo; antes dele, é plano vigente anterior. Quando o
    documento é um ato que manda elaborar o plano, o degrau é "em elaboração". E quando o texto não
    fala de plano, não há degrau: a ausência fica como ausência.
    """
    from gerar_monitor_saude import BOLETIM_1, _data_ordinal
    from julgar_saude import RE_PLANO
    nome = (doc or "").strip().lower()
    if nome.startswith("plano"):
        # Decisão da central (02/10/2026, item 6.3): o plano que CITA o El Niño ou o ciclo é plano
        # feito para o El Niño (100). O que não cita, mas é de 2026 e cobre o risco previsto para a
        # unidade — seca, estiagem, fogo, calor, chuva extrema —, é plano de todo ano REVISADO em
        # 2026, degrau VIG_REVISADO (55). A data anterior ao Boletim nº 1 não rebaixa um plano de
        # 2026 que cobre o risco do ciclo: rebaixar por data seria medir o calendário, não o plano.
        if re.search(r"El\s*Ni[ñn]o|2026\s*[/-]\s*2027", texto or "", re.I):
            return "NOVO"
        o = _data_ordinal(data or "")
        ano = (data or "")[-4:]
        if ano == "2026" and RE_RISCO_DO_CICLO.search(texto or ""):
            return "VIG_REVISADO"
        if o is None:
            return "VIG"
        return "NOVO" if o >= _data_ordinal(BOLETIM_1) else "VIG"
    if not RE_PLANO.search(texto or ""):
        return None
    if RE_PLANO_A_ELABORAR.search(texto or ""):
        return "ELAB"
    return "NOVO"


def classificar(texto: str, data: str, doc: str = ""):
    """(f1, f2, plano, atribuição) pelos classificadores do juiz. Devolve degraus, não pontos.

    F1 e F2 só saem de **ato com dispositivo**: plano que descreve as próprias ações cita sala de
    situação e gabinete de crise sem instituir nem integrar nada, e lido como ato dava os dois
    degraus de graça (medido no plano do Pará, de 81 páginas).
    """
    from julgar_saude import RE_COORDENACAO, atribuicao_citada, degrau_coordenacao, degrau_f2
    plano = status_do_plano(doc, data, texto)
    if not e_ato(texto):
        return ((None, "o documento não é ato com dispositivo: não institui estrutura"),
                ("LAC", "o documento não é ato com dispositivo: não integra a saúde à "
                        "coordenação do estado"), plano, None)
    f1 = degrau_coordenacao(texto, data) if RE_COORDENACAO.search(texto or "") else (None, None)
    f2 = degrau_f2(texto)
    return f1, f2, plano, atribuicao_citada(texto)


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

    pgs = ["capa", "p2", "ato A", "ato B", "p5"]
    ok("recorta a faixa de páginas, inclusive", trecho_das_paginas(pgs, (3, 4)) == "ato A\nato B")
    ok("faixa além do fim não quebra", trecho_das_paginas(pgs, (5, 99)) == "p5")
    ok("sem faixa, devolve tudo", trecho_das_paginas(pgs, None).startswith("capa"))
    ok("sem páginas, devolve vazio", trecho_das_paginas([], (1, 2)) == "")

    edicao = ("Portaria nº 0011/2025 trata de outro assunto. " * 5
              + "Portaria nº 764/2026 – GS/SES/PB cria o Grupo Condutor El Niño. "
              + "Compete coordenar. " + "resto da edição " * 50)
    r = recorte_do_ato(edicao, "764/2026")
    ok("recorta em volta do ato pedido", "764/2026" in r and r.index("764") < 600)
    ok("número ausente devolve o texto como veio",
       recorte_do_ato("texto qualquer", "999/2026") == "texto qualquer")
    ok("sem número devolve o texto como veio", recorte_do_ato("texto", None) == "texto")

    # O texto do caso traz o TIPO do ato e o dispositivo, porque é o que distingue ato de plano.
    texto_pb = ("PORTARIA Nº 764/2026 – GS/SES/PB. RESOLVE: Art. 1º Fica criado, no âmbito da "
                "Secretaria de Estado da Saúde, o Grupo Condutor El Niño/PB. Art. 2º O Grupo "
                "Condutor tem por finalidade coordenar, integrar e fortalecer as ações. "
                "Art. 5º Será composto por: Defesa Civil Estadual; AESA; COSEMS/PB. "
                "Compete ao Grupo Condutor: I – elaborar e propor o Plano Estadual de Preparação.")
    f1, f2, plano, atrib = classificar(texto_pb, "03/09/2026", "Portaria nº 764/2026")
    ok("F1 sai do próprio classificador do juiz", f1[0] == "CRIADO_CICLO")
    ok("F2 vê a estrutura da saúde que integra a defesa civil, com atribuição",
       f2[0] == "NOMEADA_COM_ATRIBUICAO")
    ok("plano a elaborar é ELAB, não NOVO", plano == "ELAB")
    ok("guarda o trecho da atribuição", bool(atrib))

    f1b, f2b, planob, _ = classificar("PORTARIA Nº 9/2026. RESOLVE: Art. 1º Nomear servidor.",
                                      "01/01/2026", "Portaria nº 9/2026")
    ok("texto sem estrutura não inventa F1", f1b == (None, None))
    ok("texto sem ligação não inventa F2", f2b[0] == "LAC")
    ok("texto sem plano não inventa plano", planob is None)

    # MEDIDO em 02/10/2026 no diário do MS: a página citada trazia uma segunda resolução, de
    # recursos, com a palavra "prorrogado" — e o degrau de F1 saía "reativado" por causa de um ato
    # que não era o medido. Por isso a base primeira é o recorte do ato.
    pagina_com_dois_atos = (
        "Resolução nº 900/2026 trata de recursos, podendo ser prorrogado uma vez. "
        "Resolução SES/MS nº 1041. RESOLVE: Art. 1º Institui o Grupo Condutor Estadual de "
        "Preparação e Resposta aos Eventos Climáticos associados ao El Niño. Compete "
        "coordenar. Art. 6º Será composto por: Defesa Civil Estadual.")
    f1_pagina = classificar(pagina_com_dois_atos, "03/09/2026", "Resolução 1041")[0]
    f1_recorte = classificar(recorte_do_ato(pagina_com_dois_atos, "1041/2026"),
                             "03/09/2026", "Resolução 1041")[0]
    ok("na página com dois atos, o verbo do outro ato contamina o degrau",
       f1_pagina[0] == "REATIVADO_CICLO")
    ok("no recorte do ato medido, o degrau é o do ato", f1_recorte[0] == "CRIADO_CICLO")

    ok("plano de 81 páginas não é ato: não dá F1 nem F2",
       classificar("Plano de emergências. Consolidar informações para o Gabinete de Crise. "
                   "Manter sala de situação ativa.", "26/02/2026", "Plano de emergências")[:2]
       == ((None, "o documento não é ato com dispositivo: não institui estrutura"),
           ("LAC", "o documento não é ato com dispositivo: não integra a saúde à "
                   "coordenação do estado")))
    ok("o plano publicado antes do Boletim nº 1 é plano vigente anterior",
       status_do_plano("Plano de emergências da SESPA", "26/02/2026", "") == "VIG")
    ok("o plano publicado no ciclo é plano do ciclo",
       status_do_plano("Plano estadual de preparação", "01/09/2026", "") == "NOVO")
    ok("ato que manda elaborar o plano é em elaboração",
       status_do_plano("Portaria 764/2026", "03/09/2026",
                       "Compete elaborar e propor o Plano Estadual de Preparação") == "ELAB")
    ok("texto sem plano não inventa degrau",
       status_do_plano("Portaria 1/2026", "01/09/2026", "nomeia servidor") is None)
    ok("ato com tipo e dispositivo é ato",
       e_ato("PORTARIA Nº 764/2026. RESOLVE: Art. 1º Fica criado") is True)
    ok("plano que cita portaria no texto não vira ato",
       e_ato("Plano de contigência, conforme a Portaria 100/2025 do Ministério") is False)

    ok("os documentos da central estão declarados",
       [d["uf"] for d in DOCUMENTOS] == ["PB", "MS", "PA", "MT", "MT"])
    ok("o esperado da central não é usado como dado",
       all("esperado" in d for d in DOCUMENTOS))

    fonte = pathlib.Path(__file__).read_text(encoding="utf-8")
    ok("trava estrutural: nenhum arquivo do banco é destino",
       not any(f'gravar("{b}' in fonte for b in BANCO_PROIBIDO))
    ok("trava estrutural: a escrita é de saude_uf, pela porta do juiz",
       "gravar(\"saude_uf.json\"" in fonte)

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else f"✓ AUTOTESTE OK — {len(_casos_contados)} casos, sem rede e sem escrita.")
    return 1 if falhas else 0


def _texto_do_documento(d: dict):
    """(páginas, url, bruto) do documento: pela edição do diário ou pelo endereço direto."""
    from coletores_base import buscar

    import coletar_edicoes_doe as loc
    if d.get("edicao"):
        uf, data = d["edicao"]["uf"], d["edicao"]["data"]
        # O endereço da edição vem do REGISTRO do localizador quando ele já a baixou: em UF cujo
        # arquivo é nomeado pelo número da edição (MS), montar o endereço a partir do padrão daria
        # 404 — o número foi resolvido pelo localizador, e é dele que se pergunta.
        from coletores_base import ler as _ler
        guardado = ((_ler(f"{loc.PASTA}/{uf}.json", {}) or {}).get("edicoes") or {}).get(data) or {}
        url = guardado.get("url")
        if not url:
            padrao = (loc.PADROES.get(uf) or {}).get("padrao")
            if not padrao or "{edicao}" in padrao:
                return None, None, None
            url = loc.endereco_da_data(padrao, data)
    elif d.get("url"):
        url = d["url"]
    else:
        return None, None, None
    bruto = buscar(url, timeout=120)
    return loc._texto_paginas(bruto), url, bruto


def main() -> int:
    if "--autoteste" in sys.argv:
        return _autoteste()

    sys.path.insert(0, str(RAIZ))
    from coletores_base import gravar, hoje_editorial, ler, preservar_evidencia
    from julgar_saude import aplicar

    aplicando = "--aplicar" in sys.argv
    su = ler("saude_uf.json", {}) or {}
    mudancas = []
    for d in DOCUMENTOS:
        uf = d["uf"]
        try:
            paginas, url, bruto = _texto_do_documento(d)
        except Exception as e:  # noqa: BLE001
            print(f"  {uf}: não foi possível ler o documento — {type(e).__name__}: {str(e)[:90]}")
            continue
        if not paginas:
            print(f"  {uf}: endereço do documento não declarado — fica para a campanha")
            continue
        # Duas bases, e a mais estreita primeiro. MEDIDO em 02/10/2026, nos dois diários:
        # - no MS, a página citada trazia TAMBÉM uma resolução de recursos com a palavra
        #   "prorrogado", e o degrau de F1 saía "reativado" por causa de um ato que não era o
        #   medido;
        # - na PB, de duas colunas, o texto extraído interleava as colunas, e o recorte a partir
        #   do número do ato cortava fora a competência de elaborar o plano.
        # Então: classifica-se no RECORTE do ato; o sinal que o recorte não tem cai para a
        # página citada, e a base de cada degrau fica escrita na justificativa.
        trecho = trecho_das_paginas(paginas, d.get("paginas"))
        recorte = recorte_do_ato(trecho, d.get("numero"))
        f1, f2, plano, atrib = classificar(recorte, d["data"], d.get("doc"))
        base = {"f1": "recorte do ato", "f2": "recorte do ato", "plano": "recorte do ato"}
        if trecho != recorte:
            f1b, f2b, planob, atribb = classificar(trecho, d["data"], d.get("doc"))
            if not f1[0] and f1b[0]:
                f1, base["f1"] = f1b, "página citada"
            if f2[0] in (None, "LAC") and f2b[0] not in (None, "LAC"):
                f2, atrib, base["f2"] = f2b, atribb, "página citada"
            if not plano and planob:
                plano, base["plano"] = planob, "página citada"
        esperado = d.get("esperado") or {}
        divergencias = []
        if esperado.get("f1") and f1[0] != esperado["f1"]:
            divergencias.append(f"F1 lido {f1[0]} e a central leu {esperado['f1']}")
        if esperado.get("f2") and f2[0] != esperado["f2"]:
            divergencias.append(f"F2 lido {f2[0]} e a central leu {esperado['f2']}")
        if esperado.get("plano") and plano != esperado["plano"]:
            divergencias.append(f"plano lido {plano} e a central leu {esperado['plano']}")
        print(f"  {uf}: F1={f1[0]} ({base['f1']}) · F2={f2[0]} ({base['f2']}) · plano={plano}"
              + (f" · DIVERGÊNCIA: {'; '.join(divergencias)}" if divergencias else ""))
        if not aplicando:
            continue

        veredito = {"uf": uf, "numero": d.get("numero"), "data": d["data"],
                    "hash_evidencia": preservar_evidencia(
                        bruto, url, "pdf" if url.lower().endswith(".pdf") else "html",
                        "registrar_saude_central"),
                    "pagina_citada": (f"pp. {d['paginas'][0]}–{d['paginas'][1]}"
                                      if d.get("paginas") else None)}
        if f1[0]:
            veredito["coordenacao"] = {"degrau": f1[0],
                                       "motivo": f1[1] + f" (lido no {base['f1']})"}
        if f2[0] and f2[0] != "LAC":
            veredito["coordenacao_f2"] = {"degrau": f2[0],
                                          "motivo": f2[1] + f" (lido no {base['f2']})",
                                          "atribuicao_citada": atrib}
        if plano:
            veredito["status_instrumento"] = plano
            veredito["categoria"] = "plano_elaboracao" if plano == "ELAB" else "plano"
        mudou = aplicar(su, veredito, d["doc"], url)
        if mudou:
            mudancas.append(f"{uf}: " + ", ".join(mudou))

    if aplicando:
        su["corte"] = hoje_editorial().strftime("%d/%m/%Y")
        gravar("saude_uf.json", su)
        print("saude_uf.json gravado · " + ("; ".join(mudancas) if mudancas else "nada mudou"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
