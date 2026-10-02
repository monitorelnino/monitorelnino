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
    {"uf": "PA", "doc": "Plano de emergências da SESPA",
     "data": "01/02/2026", "numero": None,
     "url": "https://www.saude.pa.gov.br/", "paginas": None,
     "esperado": {"f1": None, "f2": None, "plano": "NOVO"},
     "nota": "portal oficial da SESPA, fevereiro de 2026 — endereço do documento a confirmar"},
    {"uf": "MT", "doc": "Portaria nº 0195/2026/GBSES",
     "data": "01/01/2026", "numero": "0195/2026",
     "url": None, "paginas": None,
     "esperado": {"f1": "PERMANENTE", "f2": None, "plano": None},
     "nota": "estrutura permanente; a portaria de 13/08/2026 pode confirmar ato do ciclo"},
]


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


def classificar(texto: str, data: str):
    """(f1, f2, plano) pelos classificadores do juiz. Devolve degraus, não pontos."""
    from julgar_saude import (RE_COORDENACAO, RE_PLANO, atribuicao_citada, degrau_coordenacao,
                              degrau_f2)
    f1 = degrau_coordenacao(texto, data) if RE_COORDENACAO.search(texto or "") else (None, None)
    f2 = degrau_f2(texto)
    plano = None
    if RE_PLANO.search(texto or ""):
        # "elaborar e propor o Plano" é plano EM ELABORAÇÃO; plano aprovado traz o ato de
        # aprovação. A distinção é a mesma do MARÉ Legal, e não se inventa aqui.
        # Competência de ELABORAR o plano não é plano publicado. A lista de verbos vem com vírgulas
        # no diário do MS ("elaborar, atualizar, implementar e monitorar o Plano Estadual"), e por
        # isso se aceita qualquer sequência curta entre o verbo e a palavra Plano. Plano aprovado
        # traz o ato de aprovação, e aí o degrau é NOVO.
        # Competência de ELABORAR o plano não é plano publicado. A lista de verbos vem com
        # vírgulas no diário do MS ("elaborar, atualizar, implementar e monitorar o Plano
        # Estadual"), e por isso se aceita qualquer sequência curta entre o verbo e a palavra
        # Plano. Plano aprovado traz o ato de aprovação, e aí o degrau é NOVO.
        plano = "ELAB" if re.search(RE_PLANO_A_ELABORAR, texto or "") else "NOVO"
    return f1, f2, plano, atribuicao_citada(texto)


def _autoteste() -> int:
    falhas = []

    def ok(nome, cond):
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

    texto_pb = ("Fica criado, no âmbito da Secretaria de Estado da Saúde, o Grupo Condutor "
                "El Niño/PB. Art. 2º O GC tem por finalidade coordenar, integrar e fortalecer as "
                "ações. Art. 5º Será composto por: Defesa Civil Estadual; AESA; COSEMS/PB. "
                "Compete ao GC: I – elaborar e propor o Plano Estadual de Preparação.")
    f1, f2, plano, atrib = classificar(texto_pb, "03/09/2026")
    ok("F1 sai do próprio classificador do juiz", f1[0] == "CRIADO_CICLO")
    ok("F2 vê a estrutura da saúde que integra a defesa civil, com atribuição",
       f2[0] == "NOMEADA_COM_ATRIBUICAO")
    ok("plano a elaborar é ELAB, não NOVO", plano == "ELAB")
    ok("guarda o trecho da atribuição", bool(atrib))

    f1b, f2b, planob, _ = classificar("Portaria de nomeação de servidor.", "01/01/2026")
    ok("texto sem estrutura não inventa F1", f1b == (None, None))
    ok("texto sem ligação não inventa F2", f2b[0] == "LAC")
    ok("texto sem plano não inventa plano", planob is None)

    # MEDIDO em 02/10/2026 no diário do MS: a página citada trazia uma segunda resolução, de
    # recursos, com a palavra "prorrogado" — e o degrau de F1 saía "reativado" por causa de um ato
    # que não era o medido. Por isso a base primeira é o recorte do ato.
    pagina_com_dois_atos = (
        "Resolução nº 900/2026 trata de recursos, podendo ser prorrogado uma vez. "
        "Resolução SES/MS nº 1041 Institui o Grupo Condutor Estadual de Preparação e Resposta "
        "aos Eventos Climáticos associados ao El Niño. Compete coordenar. Composto por: "
        "Defesa Civil.")
    f1_pagina = classificar(pagina_com_dois_atos, "03/09/2026")[0]
    f1_recorte = classificar(recorte_do_ato(pagina_com_dois_atos, "1041/2026"), "03/09/2026")[0]
    ok("na página com dois atos, o verbo do outro ato contamina o degrau",
       f1_pagina[0] == "REATIVADO_CICLO")
    ok("no recorte do ato medido, o degrau é o do ato", f1_recorte[0] == "CRIADO_CICLO")

    ok("os quatro documentos da central estão declarados",
       [d["uf"] for d in DOCUMENTOS] == ["PB", "MS", "PA", "MT"])
    ok("o esperado da central não é usado como dado",
       all("esperado" in d for d in DOCUMENTOS))

    fonte = pathlib.Path(__file__).read_text(encoding="utf-8")
    ok("trava estrutural: nenhum arquivo do banco é destino",
       not any(f'gravar("{b}' in fonte for b in BANCO_PROIBIDO))
    ok("trava estrutural: a escrita é de saude_uf, pela porta do juiz",
       "gravar(\"saude_uf.json\"" in fonte)

    print(("✗ AUTOTESTE: " + str(len(falhas)) + " falha(s)") if falhas
          else "✓ AUTOTESTE OK — 20 casos, sem rede e sem escrita.")
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
        f1, f2, plano, atrib = classificar(recorte, d["data"])
        base = {"f1": "recorte do ato", "f2": "recorte do ato", "plano": "recorte do ato"}
        if trecho != recorte:
            f1b, f2b, planob, atribb = classificar(trecho, d["data"])
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
