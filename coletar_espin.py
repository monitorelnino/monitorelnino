#!/usr/bin/env python3
"""
coletar_espin.py — emergência em saúde pública declarada, no DOU (§209)
======================================================================
ESTATUTO: peso ZERO no MARÉ e no MARÉ Saúde. É **resposta**, não preparação — declarar
emergência é ato posterior ao dano, e o índice mede o que se publicou antes. O registro
existe para transparência, com órgão, ato, data e link, como todo ato de resposta.

POR QUE ESTE ARQUIVO EXISTE
`data/saude_sinais.json` tinha a fonte `espin` em `aguardando_primeira_coleta` desde
02/09/2026, com a coleta automática declarada como pendente: o zero exibido na página vinha
de busca manual de 05/09. Zero verificado à mão é dado, mas não se sustenta sozinho por um
ciclo inteiro — uma ESPIN declarada em novembro passaria despercebida até alguém procurar.

O QUE ELE FAZ, E O QUE NÃO FAZ
Busca no DOU os atos que **declaram** emergência em saúde pública, pelo vocabulário do
próprio ato (ESPIN é o nome técnico; a portaria costuma dizer "declara Emergência em Saúde
Pública de Importância Nacional"). Usa o leitor único da página de consulta do DOU que vive
em `coletores_base` — o mesmo do `coletar_s2id` —, de modo que uma mudança na página quebra
os dois no mesmo lugar, e de um jeito só.

NÃO classifica e NÃO promove: o que ele encontra entra como **registro de resposta** com o
link do ato, e o que ele não reconhece com segurança vira pista para leitura humana (R7).
Ato que só *cita* uma emergência — prorrogação de prazo, nota técnica, ato de outro tema que
menciona a expressão — não é declaração, e o teste do verbo existe para separar os dois.

ZERO É RESPOSTA, AUSÊNCIA NÃO É
Busca que roda e não acha nada grava `nenhuma_declaracao_localizada` COM a data e as strings
buscadas: isso é "procuramos e não há", diferente de "não procuramos". Busca que falha por
rede, ou página que volta sem a estrutura de resultados, não escreve nada e vira lacuna
declarada.

USO
  python coletar_espin.py --autoteste     # prova os parsers, sem rede
  python coletar_espin.py                 # busca no DOU desde o início do ciclo
  python coletar_espin.py --desde 2026-01-01
"""
import json
import re
import sys
import time
from datetime import date

from coletores_base import (buscar, ler, gravar, log_busca, registrar_lacuna, rodar_autoteste,
                            preservar_evidencia, parse_busca_dou, varrer_busca_dou,
                            FormatoDoDOUMudou, RAIZ, hoje_editorial)

INICIO_CICLO = "2026-06-29"          # primeiro boletim do Painel El Niño; o ciclo começa aqui
RITMO_S = 2.0                        # §11: no máximo uma requisição a cada 2 s por domínio

# O vocabulário é o DO ATO, e foi MEDIDO em 24/09/2026 contra a busca real, não escolhido de
# cabeça. A expressão por extenso devolve 2 resultados na janela do ciclo; a forma curta
# devolve 26, que é o palheiro certo (as portarias do Gabinete do Ministro estão nele). A sigla
# "ESPIN", com ou sem aspas, devolve 37 atos sem relação nenhuma — o buscador do DOU não a trata
# como sigla —, e por isso ficou de fora: ruído não é cobertura.
TERMOS = [
    '"Emergência em Saúde Pública de Importância Nacional"',
    '"emergência em saúde pública"',
]
# ESPIN é declarada pelo Ministro da Saúde (Decreto 7.616/2011, art. 2º). O órgão vem declarado
# pela própria busca, então só os atos DELE são abertos para leitura integral: os outros — TCU,
# Poder Legislativo — ficam com a classificação do excerto, que para eles basta, porque nenhum
# deles poderia declarar. O filtro é de competência, não de palpite.
ORGAO_QUE_DECLARA = re.compile(r"Minist[ée]rio da Sa[úu]de", re.I)
# O ato que DECLARA diz que declara. Prorrogação, encerramento e menção de passagem usam
# outros verbos — e por isso não casam aqui.
PADRAO_DECLARA = re.compile(r"\bdeclara(?:m|r|ção)?\b[^.]{0,160}\bemerg[êe]ncia em sa[úu]de p[úu]blica\b", re.I)
PADRAO_ENCERRA = re.compile(r"\b(encerra|declara o encerramento|revoga|torna sem efeito)\b", re.I)
PADRAO_PRORROGA = re.compile(r"\bprorroga\b", re.I)
PADRAO_ATO = re.compile(r"(PORTARIA|DECRETO)\s+(?:[A-ZÇ/\.]+\s+)?N[ºo°]\s*([\d\.]+)", re.I)


def deve_abrir_o_ato(item: dict) -> bool:
    """O ato vale a leitura integral? Só se o órgão que o assina puder declarar. Função pura.

    Abrir todos custaria uma requisição por resultado a cada rodada, para classificar ato de
    quem não tem competência nenhuma sobre ESPIN. Órgão ausente é lido, e não descartado:
    silêncio da fonte não pode virar filtro."""
    orgao = (item.get("orgao") or "").strip()
    return (not orgao) or bool(ORGAO_QUE_DECLARA.search(orgao))


def parse_dou_html(texto: str) -> list:
    """Resultados da consulta do DOU. Casca do leitor único de `coletores_base`, que levanta
    quando a página não traz a estrutura de resultados — lista vazia mentiria. Função pura."""
    return parse_busca_dou(texto)


def classificar_ato(item: dict, texto_do_ato: str = "", falhou_ao_abrir: bool = False) -> dict:
    """Diz o que o ato É, pelo texto dele: declaração, prorrogação, encerramento, menção — ou
    **incerto**, que é a resposta honesta na dúvida. Função pura.

    24/09/2026 (medido): o trecho que a busca devolve tem ~235 caracteres e corta o verbo —
    classificar por ele erraria em silêncio. O ato inteiro decide; o campo `lido` registra o que
    decidiu, e distingue três coisas que não são a mesma: `ato` (aberto e lido),
    `trecho_da_busca` (não foi aberto de propósito, porque o órgão não tem competência para
    declarar) e `falha_ao_abrir` (tentou-se e não deu — que NÃO é ausência de declaração).

    As três regras de incerteza, todas na mesma direção — "na dúvida, o classificador não
    classifica" (regra editorial do projeto):
      · mais de um verbo casa no mesmo texto → incerto (declara e prorroga, por exemplo);
      · o ato não pôde ser aberto → incerto, sempre;
      · o verbo apareceu só no excerto, num ato que não foi aberto → incerto, porque órgão sem
        competência que *parece* declarar é justamente o caso que merece olho humano.

    Só `declaracao` vira registro automático, e mesmo ela não vai sozinha ao banco: promoção é
    humana (R7). Prorrogação, encerramento e incerto vão à fila de leitura."""
    titulo = (item.get("titulo") or "").strip()
    corpo = texto_do_ato or item.get("trecho") or item.get("conteudo") or ""
    texto = titulo + " " + corpo
    ato = PADRAO_ATO.search(titulo)
    lido = "falha_ao_abrir" if falhou_ao_abrir else ("ato" if texto_do_ato else "trecho_da_busca")
    base = {"titulo": titulo[:200], "url": item.get("url"), "data": item.get("data"),
            "orgao": item.get("orgao") or None,
            "ato": (ato.group(0).strip() if ato else None), "lido": lido}
    # Os verbos são testados em ordem de especificidade, e o que decide se há AMBIGUIDADE é a
    # POSIÇÃO. "Declara o encerramento da Emergência em Saúde Pública" casa com encerramento e
    # com declaração — mas é o MESMO trecho, uma frase só, e não uma dúvida: o casamento mais
    # específico absorve o que se sobrepõe a ele. Dois verbos em trechos DIFERENTES, aí sim, é
    # ato que faz duas coisas, e isso é caso de olho humano.
    casou, tomados = [], []
    for nome, padrao in (("encerramento", PADRAO_ENCERRA), ("prorrogacao", PADRAO_PRORROGA),
                         ("declaracao", PADRAO_DECLARA)):
        m = padrao.search(texto)
        if not m:
            continue
        if any(m.start() < fim and ini < m.end() for ini, fim in tomados):
            continue
        casou.append(nome); tomados.append((m.start(), m.end()))
    if lido == "falha_ao_abrir":
        return {**base, "classe": "incerto", "motivo": "o ato não pôde ser aberto"}
    if len(casou) > 1:
        return {**base, "classe": "incerto", "motivo": "mais de um verbo no mesmo ato: " + ", ".join(casou)}
    if not casou:
        return {**base, "classe": "mencao"}
    if lido != "ato":
        return {**base, "classe": "incerto",
                "motivo": "o excerto sugere '" + casou[0] + "' num ato que não foi aberto"}
    return {**base, "classe": casou[0]}


def montar_registro(itens: list, desde: str, ate: str, strings: list,
                    ler_ato=None, incompletas=None) -> dict:
    """Monta o bloco que vai para `saude_sinais.json`. Pura quando `ler_ato` é puro.

    Sem nenhuma declaração, grava `nenhuma_declaracao_localizada` COM data e strings buscadas:
    procurar e não achar é resultado; não procurar é outra coisa. Janela que a página não
    entregou inteira entra em `leitura_parcial`, e ato que não pôde ser aberto entra em
    `nao_lidos` — recorte e falha nunca se apresentam como varredura.

    `ler_ato(url)` devolve o texto do ato, `""` quando o ato não precisa ser aberto, e
    **levanta** quando a leitura falhou: a diferença entre as duas últimas é o que separa
    "não precisou" de "não deu"."""
    classificados = []
    for i in itens:
        corpo, falhou = "", False
        if ler_ato:
            try:
                corpo = ler_ato(i["url"])
            except Exception:  # noqa: BLE001 — falha de rede não decide o que o ato é
                falhou = True
        classificados.append(classificar_ato(i, corpo, falhou_ao_abrir=falhou))
    declaracoes = [c for c in classificados if c["classe"] == "declaracao"]
    fila = [c for c in classificados if c["classe"] in ("prorrogacao", "encerramento", "incerto")]
    nao_lidos = [c for c in classificados if c["lido"] == "falha_ao_abrir"]
    return {
        "fonte": "espin",
        "orgao": "Ministério da Saúde (DOU, seção 1)",
        "janela": {"de": desde, "ate": ate},
        "strings_buscadas": strings,
        "consultado_em": hoje_editorial().strftime("%d/%m/%Y"),
        "resultados_lidos": len(itens),
        "declaracoes": declaracoes,
        "para_leitura_humana": fila,
        "nao_lidos": nao_lidos,
        "leitura_parcial": list(incompletas or []),
        "situacao": ("declaracao_localizada" if declaracoes
                     else "leitura_incompleta" if nao_lidos
                     else "nenhuma_declaracao_localizada"),
        "peso_no_indice": "nenhum",
        "nota": ("Ato de RESPOSTA: declarar emergência é posterior ao dano e não entra na nota. "
                 "Nada aqui entra no banco sozinho: a promoção é humana (R7), e o que está em "
                 "dúvida vai à fila de leitura, não ao registro."),
    }


def coletar(args) -> int:
    desde = args[args.index("--desde") + 1] if "--desde" in args else INICIO_CICLO
    ate = hoje_editorial().isoformat()
    d0, d1 = date.fromisoformat(desde), date.fromisoformat(ate)
    sinais = ler("saude_sinais.json")
    itens, falhas, incompletas = [], [], []
    for termo in TERMOS:
        paginas = []

        def _buscar_pagina(u, _p=paginas):
            b = buscar(u, timeout=45, origem="coletar_espin")
            _p.append((b, u))
            return b

        try:
            achados, faltando = varrer_busca_dou(termo, d0, d1, buscar_fn=_buscar_pagina)
        except FormatoDoDOUMudou as e:
            falhas.append(f"{termo}: estrutura de resultados ausente")
            registrar_lacuna(f"DOU/ESPIN {termo}", f"página sem a estrutura de resultados ({e})",
                             canal="DOU", camada=1, strings=[termo])
            continue
        except Exception as e:  # noqa: BLE001
            falhas.append(f"{termo}: {type(e).__name__}")
            registrar_lacuna(f"DOU/ESPIN {termo}", type(e).__name__, canal="DOU", camada=1, strings=[termo])
            continue
        h = None
        for bruto, u in paginas:
            h = preservar_evidencia(bruto, u, "html", "coletar_espin") or h
        incompletas += faltando
        for a in achados:
            if not any(a["url"] == b["url"] for b in itens):
                itens.append(a)
        log_busca("DOU", 1, [termo], "registro" if achados else "consultado sem achado",
                  n_resultados=len(achados), resultados=f"ESPIN: {len(achados)} resultado(s)",
                  hash_evidencia=h)
    if falhas and not itens:
        # Nenhuma busca completou: isso é lacuna, e NÃO pode virar "procuramos e não há".
        print(f"[aviso] ESPIN: nenhuma busca completou ({'; '.join(falhas)}) — registro anterior mantido.")
        return 0

    por_url = {i["url"]: i for i in itens}

    def _ler_ato(u):
        if not deve_abrir_o_ato(por_url.get(u) or {}):
            return ""          # órgão sem competência para declarar: o excerto basta
        time.sleep(RITMO_S)    # §11: no máximo uma requisição a cada 2 s por domínio
        b = buscar(u, timeout=45, origem="coletar_espin")
        preservar_evidencia(b, u, "html", "coletar_espin")
        return b.decode("utf-8", "replace")

    bloco = montar_registro(itens, desde, ate, TERMOS, ler_ato=_ler_ato, incompletas=incompletas)
    sinais["espin_busca"] = bloco
    f = sinais["fontes"]["espin"]
    f.update({"status": "coletado", "consultado_em": bloco["consultado_em"],
              "documento": f"DOU seção 1, {desde} a {ate}"})
    sinais["gerado_em"] = hoje_editorial().strftime("%d/%m/%Y")
    gravar("saude_sinais.json", sinais)
    # R7: nada entra no banco por classificação automática. O que o coletor achou — declaração
    # inclusive — vai para a fila de leitura humana, que é o veículo do projeto para isso.
    if bloco["declaracoes"] or bloco["para_leitura_humana"]:
        gravar("espin_revisar.json", {
            "_governanca": ("Fila de leitura humana (R7). Saída de classificação automática do "
                            "coletar_espin.py: nada aqui é registro, e nada entra em "
                            "data/saude_sinais.json['emergencias'] sem conferência de uma pessoa."),
            "gerado_em": bloco["consultado_em"],
            "janela": bloco["janela"],
            "candidatos_a_declaracao": bloco["declaracoes"],
            "em_duvida_ou_outro_ato": bloco["para_leitura_humana"],
        })
    for c in bloco["nao_lidos"]:
        registrar_lacuna("DOU/ESPIN — ato não aberto",
                         c["titulo"][:80] + ": leitura do ato falhou; classificação ficou incerta",
                         canal="DOU", camada=1, strings=[c["url"]])
    for j in incompletas:
        registrar_lacuna("DOU/ESPIN", f"janela {j['de']} a {j['ate']} declara {j['total']} resultados e a página entrega {j['lidos']}",
                         canal="DOU", camada=1, strings=TERMOS)
    print(f"ESPIN: {bloco['resultados_lidos']} resultado(s) lidos · "
          f"{len(bloco['declaracoes'])} declaração(ões) · "
          f"{len(bloco['para_leitura_humana'])} para leitura humana · {bloco['situacao']}")
    return 0


# Fixture na forma que o DOU serve HOJE: <script type="application/json">, título embrulhado
# em marcação de destaque e trecho curto — o mesmo formato provado em `coletar_s2id`.
FIX_DOU = ('<script id="_br_com_seatecnologia_in_buscadou_BuscaDouPortlet_params" type="application/json">'
           + json.dumps({"jsonArray": [
               {"title": "<span class='highlight'>PORTARIA</span> GM/MS Nº 1.000, DE 1 DE AGOSTO DE 2026",
                "urlTitle": "portaria-1000", "pubDate": "01/08/2026",
                "content": "Declara Emergência em Saúde Pública de Importância Nacional em razão de arboviroses."},
               {"title": "PORTARIA GM/MS Nº 1.100, DE 2 DE SETEMBRO DE 2026", "urlTitle": "portaria-1100",
                "pubDate": "02/09/2026",
                "content": "Prorroga a Emergência em Saúde Pública de Importância Nacional declarada pela Portaria nº 1.000."},
               {"title": "PORTARIA GM/MS Nº 1.200, DE 3 DE SETEMBRO DE 2026", "urlTitle": "portaria-1200",
                "pubDate": "03/09/2026",
                "content": "Declara o encerramento da Emergência em Saúde Pública de Importância Nacional."},
               {"title": "NOTA TÉCNICA Nº 9", "urlTitle": "nota-9", "pubDate": "04/09/2026",
                "content": "Orienta estados sobre a Emergência em Saúde Pública de Importância Nacional vigente.",
                "hierarchyStr": "Ministério da Saúde/Gabinete do Ministro"},
           ]}) + '</script><p>4 resultados</p>')

# O mesmo ato como o DOU o entrega hoje na busca: o trecho corta ANTES do verbo.
FIX_TRECHO_CURTO = {"titulo": "PORTARIA GM/MS Nº 1.000, DE 1 DE AGOSTO DE 2026", "url": "u", "data": "01/08/2026",
                    "trecho": "considerando o disposto na Lei nº 8.080, de 19 de setembro de 1990, e na Portaria de Consolidação nº 4, resolve:"}
FIX_ATO = "<p>Art. 1º Declarar Emergência em Saúde Pública de Importância Nacional em razão de arboviroses.</p>"


def autoteste() -> int:
    # Quando o ato é aberto de verdade, o texto dele é o que decide. Nos testes, o "ato" é o
    # próprio trecho da fixture — é o que o DOU traria na página do ato.
    def _abre(u, _por_url=None):
        return {i["url"]: i["trecho"] for i in parse_dou_html(FIX_DOU)}[u]

    def t1():
        itens = parse_dou_html(FIX_DOU)
        return len(itens) == 4 and itens[0]["url"].endswith("portaria-1000")

    def t2():  # negativo: página sem a estrutura de resultados LEVANTA, nunca devolve zero
        for pagina in ("<html>nada aqui</html>", ""):
            try:
                parse_dou_html(pagina)
                return False
            except FormatoDoDOUMudou:
                pass
        return True

    def t3():  # lido o ato, cada um é o que o texto dele diz que é
        cls = [classificar_ato(i, i["trecho"])["classe"] for i in parse_dou_html(FIX_DOU)]
        return cls == ["declaracao", "prorrogacao", "encerramento", "mencao"]

    def t4():  # SEM abrir o ato, verbo no excerto é INCERTO — nunca declaração
        cls = [classificar_ato(i)["classe"] for i in parse_dou_html(FIX_DOU)]
        return cls == ["incerto", "incerto", "incerto", "mencao"]

    def t5():  # prorrogação e encerramento NÃO viram declaração automática
        r = montar_registro(parse_dou_html(FIX_DOU), "2026-06-29", "2026-09-24", TERMOS, ler_ato=_abre)
        return (len(r["declaracoes"]) == 1 and len(r["para_leitura_humana"]) == 2
                and r["situacao"] == "declaracao_localizada" and r["peso_no_indice"] == "nenhum")

    def t6():  # menção de passagem não entra em lugar nenhum
        r = montar_registro(parse_dou_html(FIX_DOU), "2026-06-29", "2026-09-24", TERMOS, ler_ato=_abre)
        todos = r["declaracoes"] + r["para_leitura_humana"]
        return all("NOTA TÉCNICA" not in c["titulo"] for c in todos)

    def t7():  # busca sem achado é RESULTADO, com data e strings — não é ausência de busca
        r = montar_registro([], "2026-06-29", "2026-09-24", TERMOS)
        return (r["situacao"] == "nenhuma_declaracao_localizada" and r["consultado_em"]
                and r["strings_buscadas"] == TERMOS and r["declaracoes"] == [])

    def t8():  # o número do ato é extraído do título, mesmo com a marcação de destaque
        c = classificar_ato(parse_dou_html(FIX_DOU)[0])
        return c["ato"] and "1.000" in c["ato"]

    def t9():  # o trecho da busca corta o verbo: sem ler o ato, não vira declaração
        return classificar_ato(FIX_TRECHO_CURTO)["classe"] == "mencao"

    def t10():  # lendo o ato, a mesma entrada é declaração — e o registro diz o que leu
        c = classificar_ato(FIX_TRECHO_CURTO, FIX_ATO)
        return c["classe"] == "declaracao" and c["lido"] == "ato"

    def t11():  # só o órgão com competência é aberto — e órgão ausente não vira filtro
        return (deve_abrir_o_ato({"orgao": "Ministério da Saúde/Gabinete do Ministro"})
                and deve_abrir_o_ato({"orgao": "Ministério da Saúde/Secretaria Executiva"})
                and not deve_abrir_o_ato({"orgao": "Tribunal de Contas da União/2ª Câmara"})
                and not deve_abrir_o_ato({"orgao": "Atos do Poder Legislativo"})
                and deve_abrir_o_ato({}) and deve_abrir_o_ato({"orgao": ""}))

    def t12():  # leitura parcial da janela viaja com o registro, nunca fica implícita
        r = montar_registro([], "2026-06-29", "2026-09-24", TERMOS,
                            incompletas=[{"de": "2026-08-01", "ate": "2026-08-01", "lidos": 50, "total": 61}])
        return bool(r["leitura_parcial"]) and r["leitura_parcial"][0]["total"] == 61

    def t13():
        """Falha ao abrir o ato NÃO some: vira incerto, entra em `nao_lidos` e muda a situação.
        Sem isso, uma rodada com a rede ruim se pareceria com 'procuramos e não há'."""
        def cai(u):
            raise TimeoutError("rede")

        r = montar_registro(parse_dou_html(FIX_DOU), "2026-06-29", "2026-09-24", TERMOS, ler_ato=cai)
        return (r["declaracoes"] == [] and len(r["nao_lidos"]) == 4
                and r["situacao"] == "leitura_incompleta"
                and all(c["classe"] == "incerto" for c in r["para_leitura_humana"]))

    def t16():
        """'Declara o encerramento' é UMA frase, não duas decisões: o casamento mais específico
        absorve o que se sobrepõe a ele, senão todo encerramento viraria dúvida."""
        c = classificar_ato({"titulo": "PORTARIA GM/MS Nº 1.200", "url": "u"},
                            "Declara o encerramento da Emergência em Saúde Pública de Importância Nacional.")
        return c["classe"] == "encerramento"

    def t14():  # dois verbos em trechos diferentes: o classificador não escolhe, declara a dúvida
        c = classificar_ato({"titulo": "PORTARIA GM/MS Nº 1", "url": "u"},
                            "Art. 1º Prorroga o prazo do plano. Art. 2º Declara Emergência em "
                            "Saúde Pública de Importância Nacional em razão de arboviroses.")
        return c["classe"] == "incerto" and "mais de um verbo" in c["motivo"]

    def t15():
        """Trava estrutural: este coletor não escreve em arquivo do banco, nem por `open()`,
        nem por `json.dump()`, nem pela via que ele de fato usa, que é `gravar()`."""
        fonte = (RAIZ / "coletar_espin.py").read_text(encoding="utf-8")
        for proibido in ["estados.json", "saude_uf.json", "municipios.json", "indice.json",
                         "monitor_saude.json", "atos_resposta.json"]:
            for padrao in (r'open\([^)]*' + re.escape(proibido) + r'[^)]*,\s*["\']([wa])',
                           r'json\.dump\([^,]*,\s*open\([^)]*' + re.escape(proibido),
                           r'gravar\(\s*["\'][^"\']*' + re.escape(proibido)):
                if re.search(padrao, fonte):
                    return False
        return True

    return rodar_autoteste({
        "DOU: lê os resultados da página de consulta": t1,
        "negativo: página sem a estrutura de resultados levanta, não devolve zero": t2,
        "lido o ato, classifica: declara, prorroga, encerra, menciona": t3,
        "sem abrir o ato, verbo no excerto é incerto — nunca declaração": t4,
        "prorrogação e encerramento vão à leitura humana, não ao banco": t5,
        "menção de passagem não vira ato": t6,
        "busca sem achado é resultado datado, não ausência de busca": t7,
        "número do ato extraído do título": t8,
        "negativo: trecho da busca corta o verbo e não basta para classificar": t9,
        "lendo o ato, a classificação muda e o registro diz o que leu": t10,
        "só o órgão com competência para declarar é aberto; órgão ausente é lido": t11,
        "janela lida pela metade viaja declarada no registro": t12,
        "falha ao abrir o ato vira incerto e leitura incompleta, não ausência": t13,
        "dois verbos em trechos diferentes: o classificador declara a dúvida": t14,
        "'declara o encerramento' é uma frase só, e é encerramento": t16,
        "trava estrutural: não escreve em arquivo do banco (nem via gravar)": t15,
    })


if __name__ == "__main__":
    sys.exit(autoteste() if "--autoteste" in sys.argv else coletar(sys.argv[1:]))
